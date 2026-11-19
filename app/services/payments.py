"""Stripe-hosted Checkout, verified webhooks and refunds.

Rules this module enforces:
  * the amount charged is the booking's approved amount from the database —
    the browser never supplies a price
  * a booking is confirmed only by a signature-verified webhook whose session,
    amount, currency and booking metadata all match what we created; the
    success redirect confirms nothing
  * every Stripe event id is recorded once, so duplicates and retries are no-ops
  * test-mode events can never confirm a production booking, and vice versa

Payment methods are *dynamic*: Checkout shows whatever is enabled in the Stripe
Dashboard and eligible for the rider (cards, Apple Pay, Google Pay, Link, and
Affirm / Klarna / Afterpay or PayPal once approved). No code change is needed
to add one.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Protocol

import stripe

from ..config import Settings, get_settings, payments_live
from ..db import tx
from ..domain.status import Status
from ..errors import Conflict, Forbidden, Unavailable
from ..security import trip_token
from . import analytics, bookings, notifications

log = logging.getLogger("meridian.payments")
STRIPE_MIN_SESSION = timedelta(minutes=31)      # Stripe minimum is 30 minutes; keep a margin
REUSE_IF_VALID_FOR = timedelta(minutes=10)


# ------------------------------------------------------------------ gateway
class PaymentGateway(Protocol):
    def create_checkout(self, params: dict, idempotency_key: str) -> dict: ...
    def refund(self, payment_intent_id: str, amount_cents: int, idempotency_key: str) -> dict: ...


class StripeGateway:
    def __init__(self, secret_key: str):
        self._client = stripe.StripeClient(secret_key)

    def create_checkout(self, params: dict, idempotency_key: str) -> dict:
        s = self._client.v1.checkout.sessions.create(params=params,
                                                     options={"idempotency_key": idempotency_key})
        return {"id": s.id, "url": s.url, "livemode": bool(s.livemode)}

    def refund(self, payment_intent_id: str, amount_cents: int, idempotency_key: str) -> dict:
        r = self._client.v1.refunds.create(
            params={"payment_intent": payment_intent_id, "amount": amount_cents,
                    "reason": "requested_by_customer"},
            options={"idempotency_key": idempotency_key})
        return {"id": r.id, "status": r.status}


_gateway: PaymentGateway | None = None


def gateway() -> PaymentGateway:
    global _gateway
    if _gateway is None:
        _gateway = StripeGateway(get_settings().stripe_secret_key)
    return _gateway


def set_gateway(g: PaymentGateway | None) -> None:
    """Tests inject a fake; production uses StripeGateway."""
    global _gateway
    _gateway = g


# ----------------------------------------------------------------- checkout
def checkout_params(b: dict, *, expires_at: datetime, s: Settings) -> dict:
    import data

    token = trip_token(b["id"])
    base = s.public_base_url
    when = notifications.local_time(b["pickup_at"])
    params = {
        "mode": "payment",
        "submit_type": "book",
        "client_reference_id": str(b["id"]),
        "customer_email": b["contact_email"],
        "line_items": [{
            "quantity": 1,
            "price_data": {
                "currency": "usd",
                "unit_amount": b["amount_cents"],
                "product_data": {
                    "name": f"Chauffeured trip {b['ref']} — {when}",
                    "description": f"All-in price: tolls, congestion charges and gratuity included. "
                                   f"{data.VEHICLE['display_name']} with a professional chauffeur.",
                },
            },
        }],
        "metadata": {"booking_id": str(b["id"]), "booking_ref": b["ref"]},
        "payment_intent_data": {"description": f"{data.BRAND['short']} trip {b['ref']}",
                                "metadata": {"booking_id": str(b["id"]), "booking_ref": b["ref"]}},
        "expires_at": int(expires_at.timestamp()),
        "success_url": f"{base}/trip/{token}?checkout=returned",
        "cancel_url": f"{base}/trip/{token}?checkout=cancelled",
    }
    if s.stripe_excluded_methods:
        params["excluded_payment_method_types"] = list(s.stripe_excluded_methods)
    if s.stripe_payment_method_configuration:
        params["payment_method_configuration"] = s.stripe_payment_method_configuration
    return params


def start_checkout(token: str, *, now: datetime | None = None, s: Settings | None = None) -> str:
    """Return a Stripe Checkout URL for an approved booking (reusing a live session)."""
    s = s or get_settings()
    now = now or datetime.now(timezone.utc)
    if not payments_live(s):
        raise Unavailable("Online payment is not switched on yet. We will contact you to arrange payment.")
    with tx() as conn:
        b = bookings.by_token(conn, token, lock=True)
        if b["status"] != Status.PAYMENT_PENDING:
            raise Conflict("This trip is not awaiting payment.", code="not_payable")
        hold = conn.execute("SELECT * FROM reservations WHERE booking_id = %s AND released_at IS NULL",
                            (b["id"],)).fetchone()
        if not hold or hold["kind"] != "hold" or hold["expires_at"] <= now:
            raise Conflict("The hold on this trip has lapsed. Please request it again.", code="hold_lapsed")

        existing = conn.execute(
            """SELECT * FROM payments WHERE booking_id = %s AND status = 'open'
               AND amount_cents = %s AND expires_at > %s ORDER BY created_at DESC LIMIT 1""",
            (b["id"], b["amount_cents"], now + REUSE_IF_VALID_FOR)).fetchone()
        if existing:
            return existing["checkout_url"]

        # Stripe sessions live >= 30 min. Extend a nearly-lapsed hold to cover that, but
        # never past the moment the car has to leave.
        expires_at = hold["expires_at"]
        if expires_at < now + STRIPE_MIN_SESSION:
            expires_at = now + STRIPE_MIN_SESSION
            if expires_at > b["service_start"]:
                raise Conflict("Too close to the trip to pay online — please call us.", code="too_late_for_payment")
            conn.execute("UPDATE reservations SET expires_at = %s WHERE id = %s", (expires_at, hold["id"]))

        attempt = conn.execute("SELECT count(*) AS n FROM payments WHERE booking_id = %s",
                               (b["id"],)).fetchone()["n"]
        try:
            session = gateway().create_checkout(checkout_params(b, expires_at=expires_at, s=s),
                                                idempotency_key=f"checkout:{b['id']}:{attempt}")
        except stripe.StripeError:
            log.exception("could not create checkout session for %s", b["ref"])
            raise Unavailable("We couldn't open the secure payment page. Please try again in a moment.",
                              code="payment_provider_unavailable")
        conn.execute(
            """INSERT INTO payments (booking_id, livemode, checkout_session_id, amount_cents, currency,
                   status, checkout_url, expires_at)
               VALUES (%s, %s, %s, %s, 'usd', 'open', %s, %s)""",
            (b["id"], session["livemode"], session["id"], b["amount_cents"], session["url"], expires_at))
        return session["url"]


# ------------------------------------------------------------------ webhook
def verify_and_parse(raw_body: bytes, signature: str | None, s: Settings | None = None) -> dict:
    s = s or get_settings()
    if not s.stripe_webhook_secret:
        raise Unavailable("Webhook secret not configured.")
    try:
        stripe.WebhookSignature.verify_header(raw_body.decode("utf-8"), signature, s.stripe_webhook_secret,
                                              tolerance=300)
    except (stripe.SignatureVerificationError, ValueError, UnicodeDecodeError):
        raise Forbidden("Invalid Stripe signature.")
    return json.loads(raw_body)


def handle_event(raw_body: bytes, signature: str | None, *, now: datetime | None = None,
                 s: Settings | None = None) -> str:
    """Process one webhook delivery. Returns a short outcome string for logs/tests."""
    s = s or get_settings()
    now = now or datetime.now(timezone.utc)
    event = verify_and_parse(raw_body, signature, s)
    with tx() as conn:
        fresh = conn.execute(
            """INSERT INTO stripe_events (id, type, livemode) VALUES (%s, %s, %s)
               ON CONFLICT (id) DO NOTHING RETURNING id""",
            (event["id"], event["type"], bool(event.get("livemode")))).fetchone()
        if not fresh:
            return "duplicate"
        if bool(event.get("livemode")) != s.is_production:
            outcome = "ignored_mode_mismatch"
        else:
            outcome = _dispatch(conn, event, now)
        conn.execute("UPDATE stripe_events SET outcome = %s WHERE id = %s", (outcome, event["id"]))
        return outcome


def _dispatch(conn, event: dict, now: datetime) -> str:
    obj = event["data"]["object"]
    etype = event["type"]
    if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status") != "paid":
            return "awaiting_async_payment"
        return _session_paid(conn, obj, now)
    if etype == "checkout.session.async_payment_failed":
        conn.execute("UPDATE payments SET status = 'failed', updated_at = %s WHERE checkout_session_id = %s "
                     "AND status = 'open'", (now, obj["id"]))
        return "payment_failed"
    if etype == "checkout.session.expired":
        conn.execute("UPDATE payments SET status = 'expired', updated_at = %s WHERE checkout_session_id = %s "
                     "AND status = 'open'", (now, obj["id"]))
        return "session_expired"
    if etype == "charge.refunded":
        return _charge_refunded(conn, obj, now)
    return "ignored_type"


def _flag(conn, booking_id, flag: str, note: str, now: datetime) -> None:
    conn.execute("UPDATE bookings SET review_flag = %s, updated_at = %s WHERE id = %s", (flag, now, booking_id))
    bookings.log_event(conn, booking_id, "stripe", None, None, note)


def _session_paid(conn, session: dict, now: datetime) -> str:
    pay = conn.execute("SELECT * FROM payments WHERE checkout_session_id = %s FOR UPDATE",
                       (session["id"],)).fetchone()
    if not pay:
        ref = (session.get("metadata") or {}).get("booking_id")
        log.error("paid session %s has no payment record (booking %s)", session["id"], ref)
        return "unknown_session"
    meta_booking = (session.get("metadata") or {}).get("booking_id")
    if (session.get("amount_total") != pay["amount_cents"] or session.get("currency") != "usd"
            or meta_booking != str(pay["booking_id"])):
        _flag(conn, pay["booking_id"], "payment_mismatch",
              f"session {session['id']} amount/currency/metadata did not match — not confirmed", now)
        return "mismatch_flagged"
    if pay["status"] in ("paid", "partially_refunded", "refunded"):
        return "already_paid"
    conn.execute(
        """UPDATE payments SET status = 'paid', payment_intent_id = %s, paid_at = %s, updated_at = %s
           WHERE id = %s""", (session.get("payment_intent"), now, now, pay["id"]))
    b = bookings.get(conn, pay["booking_id"], lock=True)
    after = bookings.confirm_paid(conn, b, paid_cents=pay["amount_cents"], now=now)
    return "confirmed" if after["status"] == Status.CONFIRMED else "paid_flagged_for_review"


def _charge_refunded(conn, charge: dict, now: datetime) -> str:
    pay = conn.execute("SELECT * FROM payments WHERE payment_intent_id = %s FOR UPDATE",
                       (charge.get("payment_intent"),)).fetchone()
    if not pay:
        return "unknown_payment"
    refunded = int(charge.get("amount_refunded") or 0)
    if refunded <= pay["refunded_cents"]:
        return "refund_already_recorded"
    status = "refunded" if refunded >= pay["amount_cents"] else "partially_refunded"
    conn.execute("UPDATE payments SET refunded_cents = %s, status = %s, updated_at = %s WHERE id = %s",
                 (refunded, status, now, pay["id"]))
    b = bookings.get(conn, pay["booking_id"], lock=True)
    bookings.log_event(conn, b["id"], "stripe", None, None, f"refund recorded: {refunded} cents total")
    if b["status"] not in (Status.CANCELLED, Status.COMPLETED):
        _flag(conn, b["id"], "refunded_outside_cancellation",
              "refund issued while trip still active — cancel it in admin if the trip is off", now)
    notifications.enqueue(conn, "refunded", b, dedupe=f"refunded:{pay['id']}:{refunded}",
                          refund_cents=refunded - pay["refunded_cents"])
    analytics.enqueue_refund(conn, b, pay["id"], refunded, refunded - pay["refunded_cents"])
    return "refund_recorded"


# ------------------------------------------------------------------- refund
def refund(payment_id, amount_cents: int) -> bool:
    """Create a refund with Stripe after the cancellation has committed. The
    charge.refunded webhook records it. On failure the booking is flagged."""
    with tx() as conn:
        pay = conn.execute("SELECT * FROM payments WHERE id = %s", (payment_id,)).fetchone()
    if not pay or not pay["payment_intent_id"] or amount_cents <= 0:
        return False
    try:
        gateway().refund(pay["payment_intent_id"], amount_cents,
                         idempotency_key=f"refund:{payment_id}:{pay['refunded_cents'] + amount_cents}")
        return True
    except Exception as e:  # network or Stripe error: never lose track of money owed
        log.exception("refund failed for payment %s", payment_id)
        with tx() as conn:
            _flag(conn, pay["booking_id"], "refund_failed", f"automatic refund failed: {e}"[:300],
                  datetime.now(timezone.utc))
        return False
