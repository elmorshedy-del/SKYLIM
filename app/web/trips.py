"""Rider-facing trip pages. The opaque token in the URL is the only credential;
pages are never indexed, cached or leaked through the Referer header."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

import data
from ..config import get_settings, payments_live
from ..db import tx
from ..domain.preferences import JourneyPreferences
from ..domain.status import ACTIVE_TRIP, LABELS, Status
from ..errors import AppError, Unavailable
from ..services import bookings, payments, tracking
from ..services.notifications import trip_url
from .deps import TEMPLATES, clock, rate_limit

router = APIRouter(tags=["trips"])

PRIVATE_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
    "Referrer-Policy": "strict-origin",     # map tiles get our origin, never the token in the path
}
SHOW_CHAUFFEUR = {Status.CONFIRMED} | ACTIVE_TRIP | {Status.COMPLETED}
METHOD_LABELS = {"card": "Card", "apple_pay": "Apple Pay", "google_pay": "Google Pay", "link": "Link",
                 "affirm": "Affirm", "klarna": "Klarna", "afterpay_clearpay": "Afterpay", "paypal": "PayPal",
                 "cashapp": "Cash App Pay", "amazon_pay": "Amazon Pay"}
TIMELINE = [Status.REQUESTED, Status.PAYMENT_PENDING, Status.CONFIRMED, Status.EN_ROUTE, Status.ARRIVED,
            Status.IN_VEHICLE, Status.COMPLETED]


def _view(conn, b: dict, now: datetime) -> dict:
    s = get_settings()
    status = Status(b["status"])
    events = conn.execute(
        """SELECT to_status, min(at) AS at FROM booking_events
           WHERE booking_id = %s AND to_status IS NOT NULL GROUP BY to_status""", (b["id"],)).fetchall()
    reached = {e["to_status"]: e["at"] for e in events}
    hold = conn.execute("SELECT expires_at FROM reservations WHERE booking_id = %s AND released_at IS NULL "
                        "AND kind = 'hold'", (b["id"],)).fetchone()
    chauffeur = None
    if status in SHOW_CHAUFFEUR and b["vehicle_id"]:
        v = conn.execute("SELECT display_name, color, plate FROM vehicles WHERE id = %s", (b["vehicle_id"],)).fetchone()
        d = conn.execute("SELECT display_name, photo_url FROM drivers WHERE id = %s", (b["driver_id"],)).fetchone()
        chauffeur = {"name": d["display_name"], "photo_url": d["photo_url"], "vehicle": v["display_name"],
                     "color": v["color"], "plate": v["plate"]}
    prefs = JourneyPreferences(**b["preferences"]) if b["preferences"] else JourneyPreferences()
    hours_left = (b["pickup_at"] - now).total_seconds() / 3600
    paid = status in SHOW_CHAUFFEUR
    return {
        "ref": b["ref"], "status": status.value, "status_label": LABELS[status],
        "pickup_at": b["pickup_at"].isoformat(), "pickup_address": b["pickup_address"],
        "dropoff_address": b["dropoff_address"], "passengers": b["passengers"], "large_bags": b["large_bags"],
        "flight_number": b["flight_number"], "amount_cents": b["amount_cents"],
        "price_adjust_reason": b["price_adjust_reason"],
        "timeline": [{"status": t.value, "label": LABELS[t],
                      "at": reached[t.value].isoformat() if t.value in reached else None} for t in TIMELINE],
        "chauffeur": chauffeur,
        "cabin": prefs.checklist(),
        "payable": status == Status.PAYMENT_PENDING and payments_live(s),
        "hold_until": hold["expires_at"].isoformat() if hold else None,
        "can_cancel": status in (Status.REQUESTED, Status.PAYMENT_PENDING, Status.CONFIRMED),
        "free_cancellation": (not paid) or hours_left >= s.free_cancel_hours,
        "can_share": s.tracking_enabled and status in ({Status.CONFIRMED} | ACTIVE_TRIP),
        "share_active": bool(b["share_expires_at"] and b["share_expires_at"] > now),
        "tracking": s.tracking_enabled and status in ACTIVE_TRIP,
    }


def _private(resp: Response) -> Response:
    resp.headers.update(PRIVATE_HEADERS)
    return resp


def _private_json(payload: dict) -> Response:
    return _private(JSONResponse(payload))


# --------------------------------------------------------------------- pages
@router.get("/trip/{token}", response_class=HTMLResponse)
def trip_page(request: Request, token: str, now: datetime = Depends(clock)):
    with tx() as conn:
        try:
            b = bookings.by_token(conn, token)
        except AppError:
            return _private(TEMPLATES.TemplateResponse(request, "error.html", {"message": "This trip link isn't valid."},
                                                       status_code=404))
        view = _view(conn, b, now)
    s = get_settings()
    return _private(TEMPLATES.TemplateResponse(request, "trip.html", {
        "trip": view, "token": token, "tiles": s.map_tile_url, "attribution": s.map_attribution,
        "stale_after": s.stale_after_seconds, "notice": request.query_params.get("checkout"),
        "methods": [METHOD_LABELS.get(m, m.replace("_", " ").title()) for m in s.payment_methods_display],
        "pay_error": request.query_params.get("pay_error")}))


@router.get("/trip/{token}/pay", dependencies=[rate_limit("pay", 10)])
def pay(token: str, now: datetime = Depends(clock)):
    try:
        url = payments.start_checkout(token, now=now)
    except AppError as e:
        return _private(RedirectResponse(f"/trip/{token}?pay_error={e.code}", status_code=303))
    return _private(RedirectResponse(url, status_code=303))


@router.get("/trip/{token}/calendar.ics")
def calendar(token: str):
    with tx() as conn:
        b = bookings.by_token(conn, token)

    def esc(v: str) -> str:
        return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    fmt = "%Y%m%dT%H%M%SZ"
    start = b["pickup_at"].astimezone(timezone.utc)
    body = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{data.BRAND['short']}//Trip//EN", "BEGIN:VEVENT",
        f"UID:{b['ref']}@{data.BRAND['domain']}", f"DTSTAMP:{b['created_at'].strftime(fmt)}",
        f"DTSTART:{start.strftime(fmt)}", f"DTEND:{(start + timedelta(minutes=30)).strftime(fmt)}",
        f"SUMMARY:{esc(data.BRAND['short'] + ' pickup — ' + b['ref'])}",
        f"LOCATION:{esc(b['pickup_address'])}",
        f"DESCRIPTION:{esc('Your private trip page: ' + trip_url(b['id']))}",
        "BEGIN:VALARM", "TRIGGER:-PT60M", "ACTION:DISPLAY", "DESCRIPTION:Pickup in one hour", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR", ""])
    return _private(Response(body, media_type="text/calendar",
                             headers={"Content-Disposition": f'attachment; filename="{b["ref"]}.ics"'}))


@router.get("/s/{share_token}", response_class=HTMLResponse)
def share_page(request: Request, share_token: str):
    s = get_settings()
    return _private(TEMPLATES.TemplateResponse(request, "share.html", {
        "share_token": share_token, "tiles": s.map_tile_url, "attribution": s.map_attribution}))


# ----------------------------------------------------------------------- API
class CancelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Optional[str] = Field(default=None, max_length=300)


class ShareIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: int = Field(default=4, ge=1, le=tracking.SHARE_MAX_HOURS)


@router.get("/api/trips/{token}")
def trip_json(token: str, now: datetime = Depends(clock)):
    with tx() as conn:
        return _private_json(_view(conn, bookings.by_token(conn, token), now))


@router.get("/api/trips/{token}/position", dependencies=[rate_limit("position", 40)])
def trip_position(token: str, now: datetime = Depends(clock)):
    s = get_settings()
    if not s.tracking_enabled:
        raise Unavailable("Live tracking is not switched on.")
    with tx() as conn:
        b = bookings.by_token(conn, token)
        return _private_json(tracking.position_view(conn, b, now, s.stale_after_seconds))


@router.post("/api/trips/{token}/cancel", dependencies=[rate_limit("cancel", 5)])
def cancel_trip(token: str, body: CancelIn, now: datetime = Depends(clock)):
    with tx() as conn:
        b = bookings.by_token(conn, token)
        row, outcome = bookings.cancel(conn, b["id"], actor="customer", reason=body.reason, now=now,
                                       free_cancel_hours=get_settings().free_cancel_hours)
    refunded = payments.refund(outcome["payment_id"], outcome["refund_cents"]) if outcome["refund_due"] else False
    return _private_json({"status": row["status"], "refund_cents": outcome["refund_cents"] if refunded else 0,
                          "review": row["review_flag"] == "late_cancellation"})


@router.post("/api/trips/{token}/share", dependencies=[rate_limit("share", 10)])
def share_trip(token: str, body: ShareIn, now: datetime = Depends(clock)):
    if not get_settings().tracking_enabled:
        raise Unavailable("Live tracking is not switched on.")
    with tx() as conn:
        b = bookings.by_token(conn, token, lock=True)
        share, expires = tracking.create_share(conn, b, now, body.hours)
    return _private_json({"share_url": f"{get_settings().public_base_url}/s/{share}",
                          "expires_at": expires.isoformat()})


@router.delete("/api/trips/{token}/share")
def unshare_trip(token: str, now: datetime = Depends(clock)):
    with tx() as conn:
        tracking.revoke_share(conn, bookings.by_token(conn, token, lock=True), now)
    return _private_json({"ok": True})


@router.get("/api/share/{share_token}/position", dependencies=[rate_limit("position", 40)])
def shared_position(share_token: str, now: datetime = Depends(clock)):
    s = get_settings()
    with tx() as conn:
        return _private_json(tracking.share_view(conn, share_token, now, s.stale_after_seconds))
