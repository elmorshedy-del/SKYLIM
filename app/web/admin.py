"""Owner dashboard: one password, phone-first, every action a POST with CSRF checks.

Designed to be used before driving, never while moving: each trip shows exactly
one big "next step" button.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import psycopg
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

import data

from ..config import LOCAL_TZ, get_settings, launch_gates, payments_live
from ..db import DRIVER_ID, VEHICLE_ID, tx
from ..domain.catalog import get_catalog
from ..domain.preferences import JourneyPreferences
from ..domain.status import OPERATIONAL_NEXT, Status
from ..errors import AppError
from ..security import ADMIN_COOKIE, ADMIN_SESSION_SECONDS, make_admin_session, verify_password
from ..services import bookings, flags, insights, payments, test_trip
from ..services.notifications import trip_url
from .deps import TEMPLATES, clock, is_admin, rate_limit, require_admin, same_origin

router = APIRouter(prefix="/admin", tags=["admin"])
NO_STORE = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow", "Referrer-Policy": "same-origin"}


def _back(msg: str = "", error: bool = False) -> RedirectResponse:
    q = f"?{'err' if error else 'msg'}={quote(msg)}" if msg else ""
    return RedirectResponse("/admin" + q, status_code=303, headers=NO_STORE)


# --------------------------------------------------------------------- auth
@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if is_admin(request):
        return RedirectResponse("/admin", status_code=303)
    return TEMPLATES.TemplateResponse(request, "admin_login.html", {"error": None}, headers=NO_STORE)


@router.post("/login", dependencies=[rate_limit("admin_login", 5)])
def login(request: Request, password: str = Form(...)):
    s = get_settings()
    if not same_origin(request) or not s.admin_password_hash or not verify_password(password, s.admin_password_hash):
        return TEMPLATES.TemplateResponse(request, "admin_login.html", {"error": "That password didn't work."},
                                          status_code=401, headers=NO_STORE)
    resp = RedirectResponse("/admin", status_code=303, headers=NO_STORE)
    resp.set_cookie(ADMIN_COOKIE, make_admin_session(), max_age=ADMIN_SESSION_SECONDS, httponly=True,
                    secure=s.cookie_secure, samesite="strict", path="/admin")
    return resp


@router.post("/logout", dependencies=[Depends(require_admin)])
def logout():
    resp = RedirectResponse("/admin/login", status_code=303, headers=NO_STORE)
    resp.delete_cookie(ADMIN_COOKIE, path="/admin")
    return resp


# ---------------------------------------------------------------- dashboard
@router.get("", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard(request: Request, now: datetime = Depends(clock)):
    s = get_settings()
    with tx() as conn:
        bookings.release_expired_holds(conn, now)
        rows = conn.execute(
            """SELECT b.*, r.expires_at AS hold_until FROM bookings b
               LEFT JOIN reservations r ON r.booking_id = b.id AND r.released_at IS NULL
               WHERE b.status NOT IN ('completed', 'cancelled', 'declined', 'expired')
                  OR b.review_flag IS NOT NULL
                  OR b.updated_at > %s
               ORDER BY b.pickup_at""", (now - timedelta(days=3),)).fetchall()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE active ORDER BY created_at LIMIT 1").fetchone()
        driver = conn.execute("SELECT * FROM drivers WHERE active ORDER BY created_at LIMIT 1").fetchone()
        trackers = conn.execute("SELECT * FROM trackers ORDER BY kind").fetchall()
        outbox = conn.execute("SELECT * FROM outbox WHERE status IN ('manual', 'failed') ORDER BY created_at DESC "
                              "LIMIT 30").fetchall()
        inquiries = conn.execute("SELECT * FROM inquiries WHERE handled_at IS NULL ORDER BY created_at DESC "
                                 "LIMIT 30").fetchall()
        blocks = conn.execute("""SELECT id, lower(during) AS starts, upper(during) AS ends, note FROM reservations
                                 WHERE kind = 'block' AND released_at IS NULL AND upper(during) > %s
                                 ORDER BY lower(during)""", (now,)).fetchall()
        instant_on = flags.enabled(conn, flags.INSTANT_BOOKING, default=True)
        stats = insights.funnel(conn, now)
    for b in rows:
        b["next"] = OPERATIONAL_NEXT.get(Status(b["status"]))
        b["checklist"] = JourneyPreferences(**b["preferences"]).checklist() if b["preferences"] else []
        b["trip_url"] = trip_url(b["id"])
    groups = {
        "attention": [b for b in rows if b["review_flag"]],
        "requests": [b for b in rows if b["status"] == Status.REQUESTED],
        "awaiting": [b for b in rows if b["status"] == Status.PAYMENT_PENDING],
        "upcoming": [b for b in rows if b["status"] in (Status.CONFIRMED, Status.EN_ROUTE, Status.ARRIVED,
                                                         Status.IN_VEHICLE)],
        "recent": [b for b in rows if b["status"] in (Status.COMPLETED, Status.CANCELLED, Status.DECLINED,
                                                       Status.EXPIRED)][-10:],
    }
    return TEMPLATES.TemplateResponse(request, "admin.html", {
        "g": groups, "now": now, "vehicle": vehicle, "driver": driver, "trackers": trackers,
        "outbox": outbox, "inquiries": inquiries, "gates": launch_gates(s), "payments_live": payments_live(s),
        "test_trip": {"enabled": test_trip.enabled(), "ready": test_trip.readiness(s)[0],
                      "reason": test_trip.readiness(s)[1], "amount_cents": data.TEST_TRIP["amount_cents"]},
        "blocks": blocks, "instant_on": instant_on, "stats": stats,
        "settings": s, "msg": request.query_params.get("msg"), "err": request.query_params.get("err"),
    }, headers=NO_STORE)


# ------------------------------------------------------------------ actions
@router.post("/bookings/{booking_id}/approve", dependencies=[Depends(require_admin)])
def approve(booking_id: uuid.UUID, amount: Optional[str] = Form(None), reason: Optional[str] = Form(None),
            now: datetime = Depends(clock)):
    s = get_settings()
    if not payments_live(s):
        return _back("Online payment isn't live yet — finish the launch gates first.", error=True)
    try:
        cents = round(float(amount) * 100) if amount and amount.strip() else None
        with tx() as conn:
            b = bookings.approve(conn, booking_id, now=now, settings=s, amount_cents=cents, adjust_reason=reason)
    except (AppError, ValueError) as e:
        return _back(getattr(e, "message", str(e)), error=True)
    return _back(f"{b['ref']} approved — payment link emailed.")


@router.post("/bookings/{booking_id}/decline", dependencies=[Depends(require_admin)])
def decline(booking_id: uuid.UUID, reason: Optional[str] = Form(None), now: datetime = Depends(clock)):
    try:
        with tx() as conn:
            b = bookings.decline(conn, booking_id, reason=(reason or "").strip() or None, now=now)
    except AppError as e:
        return _back(e.message, error=True)
    return _back(f"{b['ref']} declined — rider notified.")


@router.post("/bookings/{booking_id}/advance", dependencies=[Depends(require_admin)])
def advance(booking_id: uuid.UUID, target: str = Form(...), now: datetime = Depends(clock)):
    try:
        with tx() as conn:
            b = bookings.advance(conn, booking_id, Status(target), now=now,
                                 retention_hours=get_settings().tracking_retention_hours)
    except (AppError, ValueError) as e:
        return _back(getattr(e, "message", str(e)), error=True)
    return _back(f"{b['ref']}: {b['status'].replace('_', ' ')}.")


@router.post("/bookings/{booking_id}/cancel", dependencies=[Depends(require_admin)])
def cancel(booking_id: uuid.UUID, reason: Optional[str] = Form(None), refund: str = Form("full"),
           now: datetime = Depends(clock)):
    try:
        with tx() as conn:
            b, outcome = bookings.cancel(conn, booking_id, actor="admin", reason=reason, now=now,
                                         free_cancel_hours=get_settings().free_cancel_hours)
    except AppError as e:
        return _back(e.message, error=True)
    note = ""
    if outcome["refund_due"] and refund == "full":
        ok = payments.refund(outcome["payment_id"], outcome["refund_cents"])
        note = " Refund sent to Stripe." if ok else " Refund FAILED — see flag."
    return _back(f"{b['ref']} cancelled.{note}")


@router.post("/bookings/{booking_id}/clear-flag", dependencies=[Depends(require_admin)])
def clear_flag(booking_id: uuid.UUID, now: datetime = Depends(clock)):
    with tx() as conn:
        conn.execute("UPDATE bookings SET review_flag = NULL, updated_at = %s WHERE id = %s", (now, booking_id))
        bookings.log_event(conn, booking_id, "admin", None, None, "review flag cleared")
    return _back("Flag cleared.")


@router.post("/fleet", dependencies=[Depends(require_admin)])
def update_fleet(plate: str = Form(""), color: str = Form(""), photo_url: str = Form("")):
    photo = photo_url.strip()
    if photo and not photo.startswith("https://"):
        return _back("Photo URL must start with https://", error=True)
    with tx() as conn:
        conn.execute("UPDATE vehicles SET plate = %s, color = %s WHERE active",
                     (plate.strip().upper()[:12] or None, color.strip()[:30] or None))
        conn.execute("UPDATE drivers SET photo_url = %s WHERE active", (photo or None,))
    return _back("Vehicle and chauffeur details saved.")


@router.post("/outbox/{message_id}/sent", dependencies=[Depends(require_admin)])
def outbox_sent(message_id: int):
    with tx() as conn:
        conn.execute("UPDATE outbox SET status = 'sent', sent_at = now(), last_error = 'sent by hand' "
                     "WHERE id = %s", (message_id,))
    return _back("Marked as sent.")


@router.post("/inquiries/{inquiry_id}/handled", dependencies=[Depends(require_admin)])
def inquiry_handled(inquiry_id: uuid.UUID, now: datetime = Depends(clock)):
    with tx() as conn:
        conn.execute("UPDATE inquiries SET handled_at = %s WHERE id = %s", (now, inquiry_id))
    return _back("Inquiry marked handled.")


@router.post("/instant", dependencies=[Depends(require_admin)])
def toggle_instant(enabled: str = Form(...)):
    on = enabled == "on"
    with tx() as conn:
        flags.set_flag(conn, flags.INSTANT_BOOKING, on)
    return _back("Instant booking is on." if on else "Instant booking paused — new reservations come to you for approval.")


@router.post("/blocks", dependencies=[Depends(require_admin)])
def add_block(starts: str = Form(...), ends: str = Form(...), note: str = Form("")):
    try:
        start = datetime.strptime(starts, "%Y-%m-%dT%H:%M").replace(tzinfo=LOCAL_TZ)
        end = datetime.strptime(ends, "%Y-%m-%dT%H:%M").replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return _back("Use the date and time pickers for the block.", error=True)
    if end <= start:
        return _back("The block must end after it starts.", error=True)
    try:
        with tx() as conn:
            conn.execute("""INSERT INTO reservations (vehicle_id, driver_id, during, kind, note)
                            VALUES (%s, %s, tstzrange(%s, %s, '[)'), 'block', %s)""",
                         (VEHICLE_ID, DRIVER_ID, start, end, note.strip()[:120] or None))
    except psycopg.errors.ExclusionViolation:
        return _back("That time overlaps a reservation — move or cancel the trip first.", error=True)
    return _back("Time blocked. Clients won't be offered it.")


@router.post("/blocks/{block_id}/remove", dependencies=[Depends(require_admin)])
def remove_block(block_id: uuid.UUID, now: datetime = Depends(clock)):
    with tx() as conn:
        conn.execute("""UPDATE reservations SET released_at = %s, release_reason = 'unblocked'
                        WHERE id = %s AND kind = 'block'""", (now, block_id))
    return _back("Block removed.")


@router.post("/test-trip", dependencies=[Depends(require_admin)])
def start_test_trip(now: datetime = Depends(clock)):
    """The owner's $1 test trip: book it on the hidden test calendar and go straight to Stripe Checkout."""
    s = get_settings()
    try:
        with tx() as conn:
            _, token = test_trip.start(conn, now=now, settings=s, cat=get_catalog())
        url = payments.start_checkout(token, now=now, s=s)
    except AppError as e:
        return _back(e.message, error=True)
    return RedirectResponse(url, status_code=303)


@router.get("/exports/google-ads-conversions.csv", dependencies=[Depends(require_admin)])
def google_ads_conversions(now: datetime = Depends(clock)):
    """Paid reservations that came from a Google Ads click, in Google's offline-conversion
    upload format (Google Ads > Goals > Conversions > Uploads). Conversion name must match
    the offline conversion action created in Google Ads."""
    with tx() as conn:
        rows = conn.execute(
            """SELECT b.attribution->>'gclid' AS gclid, p.paid_at, p.amount_cents - p.refunded_cents AS cents
               FROM bookings b JOIN payments p ON p.booking_id = b.id
               WHERE p.status IN ('paid', 'partially_refunded') AND b.attribution ? 'gclid' AND NOT b.is_test
                 AND p.paid_at > %s ORDER BY p.paid_at""", (now - timedelta(days=89),)).fetchall()
    lines = ["Parameters:TimeZone=America/New_York",
             "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency"]
    for r in rows:
        when = r["paid_at"].astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{r['gclid']},Paid reservation,{when},{r['cents'] / 100:.2f},USD")
    return Response("\n".join(lines) + "\n", media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="google-ads-conversions.csv"',
                             **NO_STORE})
