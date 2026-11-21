"""Transactional email via a transactional outbox.

Messages are written to `outbox` inside the same database transaction as the
state change that caused them, keyed by a dedupe key — so a retried webhook or
a double-clicked button can never send a second receipt. A background loop
delivers pending rows through Postmark. With no Postmark token configured,
rows wait in the admin panel to be sent by hand ("manual" mode), so nothing is
silently lost before email is set up.

Staging can never email real riders: outside production only addresses in
EMAIL_ALLOWLIST receive mail; everything else is marked "suppressed".
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx
import psycopg

import data
from ..config import LOCAL_TZ, Settings, get_settings
from ..security import trip_token

log = logging.getLogger("celeste.email")
POSTMARK_URL = "https://api.postmarkapp.com/email"


# ----------------------------------------------------------------- helpers
def money(cents: int | None) -> str:
    return "—" if cents is None else f"${cents / 100:,.2f}"


def local_time(at: datetime) -> str:
    return at.astimezone(LOCAL_TZ).strftime("%a %b %-d, %Y at %-I:%M %p ET")


def trip_url(booking_id) -> str:
    return f"{get_settings().public_base_url}/trip/{trip_token(booking_id)}"


def _signature() -> str:
    b = data.BRAND
    return f"\n\n— The {b['name']} team\n{b['phone_display']} · {b['email']}\n"


def _summary(b: dict) -> str:
    return (f"Reference: {b['ref']}\n"
            f"Pickup:    {local_time(b['pickup_at'])}\n"
            f"From:      {b['pickup_address']}\n"
            f"To:        {b['dropoff_address']}\n"
            f"Guests:    {b['passengers']} · {b['large_bags']} large bags · {b.get('carry_ons', 0)} carry-ons\n"
            f"Price:     {money(b['amount_cents'])} all-in")


# ---------------------------------------------------------------- messages
def _compose(kind: str, b: dict, extra: dict) -> tuple[str, str, str]:
    """Return (to, subject, body) for a booking message."""
    url = trip_url(b["id"])
    policy = data.POLICY["summary"]
    rider = b["contact_email"]
    first = b["contact_name"].split()[0]
    if kind == "request_received":
        return rider, f"We received your request — {b['ref']}", (
            f"Hi {first},\n\nThank you. Your trip request is in, and no payment has been taken.\n\n"
            f"{_summary(b)}\n\nNext: we check the calendar for your trip — including the drive to you "
            f"and back — and replies with a secure payment link, usually within a few hours. The time is "
            f"reserved for you once you are approved and is confirmed when payment clears.\n\n"
            f"Your private trip page: {url}\n\n{policy}" + _signature())
    if kind == "owner_new_request":
        return get_settings().owner_email, f"New request {b['ref']} — {local_time(b['pickup_at'])}", (
            f"{_summary(b)}\n\nRider: {b['contact_name']} · {b['contact_phone']} · {b['contact_email']}\n"
            f"Flight: {b.get('flight_number') or '—'}\nNotes: {b.get('notes') or '—'}\n"
            f"Review flag: {b.get('review_flag') or '—'}\n\nApprove or decline: "
            f"{get_settings().public_base_url}/admin\n")
    if kind == "payment_link":
        return rider, f"Your trip is approved — complete payment ({b['ref']})", (
            f"Hi {first},\n\nGood news: the car is available and held for you until "
            f"{local_time(extra['hold_until'])}.\n\n{_summary(b)}\n\n"
            f"Pay securely with Stripe here: {url}\n\nYour trip is confirmed the moment payment clears. "
            f"If the hold lapses first, the time is released.\n\n{policy}" + _signature())
    if kind == "confirmed":
        return rider, f"Confirmed: {local_time(b['pickup_at'])} — receipt {b['ref']}", (
            f"Hi {first},\n\nYou're confirmed. This email is your receipt.\n\n{_summary(b)}\n"
            f"Paid:      {money(extra['paid_cents'])} (card via Stripe)\n\n"
            f"Your trip page shows your chauffeur, the car and plate, and — once your chauffeur sets off — "
            f"the car's live position: {url}\n\n{policy}" + _signature())
    if kind == "en_route":
        return rider, f"Your chauffeur is on the way — {b['ref']}", (
            f"Hi {first},\n\n{extra.get('driver_name') or 'Your chauffeur'} has set off for your {local_time(b['pickup_at'])} "
            f"pickup. Follow the car on your trip page: {url}\n\n"
            f"{extra.get('vehicle_line', '')}" + _signature())
    if kind == "arrived":
        return rider, f"Your car is outside — {b['ref']}", (
            f"Hi {first},\n\n{extra.get('driver_name') or 'Your chauffeur'} has arrived at {b['pickup_address']}.\n"
            f"{extra.get('vehicle_line', '')}\nYour price includes {data.POLICY['wait_included_min']} minutes "
            f"of waiting.\n\nTrip page: {url}" + _signature())
    if kind == "review_request":
        return rider, "How was your journey?", (
            f"Hi {first},\n\nThank you for travelling with us. If everything was as it should be, a short Google "
            f"review helps others find us — it takes a minute:\n{data.BRAND['review_url']}\n\n"
            f"If anything fell short, simply reply to this email. It comes straight to us." + _signature())
    if kind == "declined":
        return rider, f"About your request {b['ref']}", (
            f"Hi {first},\n\nWe're sorry — we can't take this trip"
            f"{': ' + extra['reason'] if extra.get('reason') else ''}. No payment was taken.\n\n"
            f"{_summary(b)}\n\nIf another time works, reply to this email and we'll check it for you." + _signature())
    if kind == "expired":
        return rider, f"Your hold has lapsed — {b['ref']}", (
            f"Hi {first},\n\nThe time held for your trip has been released because payment wasn't completed. "
            f"No payment was taken. If you still need the ride, request it again and we'll check the calendar.\n\n"
            f"{_summary(b)}" + _signature())
    if kind == "cancelled":
        refund = extra.get("refund_cents")
        refund_line = (f"A refund of {money(refund)} is on its way to your card (usually 5–10 business days)."
                       if refund else "No charge was made." if not extra.get("was_paid") else
                       "Because this was within the late-cancellation window, we will review any refund and email you.")
        return rider, f"Cancelled: {b['ref']}", (
            f"Hi {first},\n\nYour trip has been cancelled.\n\n{_summary(b)}\n\n{refund_line}" + _signature())
    if kind == "refunded":
        return rider, f"Refund issued — {b['ref']}", (
            f"Hi {first},\n\nA refund of {money(extra['refund_cents'])} has been issued to your card. It usually "
            f"appears within 5–10 business days.\n\n{_summary(b)}" + _signature())
    raise ValueError(f"unknown email kind {kind}")


def enqueue(conn: psycopg.Connection, kind: str, booking: dict, *, dedupe: str | None = None,
            **extra) -> None:
    to, subject, body = _compose(kind, booking, extra)
    if not to:
        log.warning("no recipient for %s on %s", kind, booking.get("ref"))
        return
    s = get_settings()
    if s.app_env != "production":
        subject = f"[{s.app_env.upper()}] {subject}"
    conn.execute(
        """INSERT INTO outbox (dedupe_key, booking_id, kind, to_email, subject, body_text)
           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (dedupe_key) DO NOTHING""",
        (dedupe or f"{kind}:{booking['id']}", booking["id"], kind, to, subject, body),
    )


# ---------------------------------------------------------------- delivery
def deliver_pending(conn_factory, settings: Settings | None = None, limit: int = 20) -> int:
    """Send pending outbox rows. Returns how many were sent."""
    s = settings or get_settings()
    sent = 0
    with conn_factory() as conn:
        rows = conn.execute(
            """SELECT * FROM outbox WHERE status = 'pending' AND attempts < 5
               ORDER BY created_at LIMIT %s FOR UPDATE SKIP LOCKED""", (limit,)).fetchall()
        for row in rows:
            status, error = _send(row, s)
            conn.execute(
                """UPDATE outbox SET status = %s, attempts = attempts + 1, last_error = %s,
                       sent_at = CASE WHEN %s = 'sent' THEN now() ELSE sent_at END
                   WHERE id = %s""", (status, error, status, row["id"]))
            sent += status == "sent"
    return sent


def _send(row: dict, s: Settings) -> tuple[str, str | None]:
    if s.app_env != "production" and row["to_email"].lower() not in s.email_allowlist:
        return "suppressed", "not in EMAIL_ALLOWLIST outside production"
    if not (s.postmark_token and s.email_from):
        return "manual", "email provider not configured — send by hand from admin"
    try:
        r = httpx.post(POSTMARK_URL, timeout=10, headers={
            "X-Postmark-Server-Token": s.postmark_token, "Accept": "application/json"},
            json={"From": s.email_from, "To": row["to_email"], "Subject": row["subject"],
                  "TextBody": row["body_text"], "MessageStream": "outbound",
                  "ReplyTo": data.BRAND["email"]})
        if r.status_code == 200:
            return "sent", None
        return ("pending" if r.status_code >= 500 else "failed"), f"postmark {r.status_code}: {r.text[:200]}"
    except httpx.HTTPError as e:
        return "pending", f"network: {e}"[:300]
