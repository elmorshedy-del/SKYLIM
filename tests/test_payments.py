"""Checkout creation and webhook processing: only verified, matching, first-seen
payment events confirm a booking."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

import pytest

from app.db import tx
from app.domain.status import Status
from app.errors import Conflict, Forbidden
from app.security import trip_token
from app.services import bookings, payments
from tests.helpers import approve, later, request

SECRET = "whsec_test_secret"


def signed(event: dict, secret: str = SECRET) -> tuple[bytes, str]:
    body = json.dumps(event).encode()
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={ts},v1={sig}"


def session_event(session_id, booking, *, amount=None, etype="checkout.session.completed",
                  status="paid", event_id=None, currency="usd") -> dict:
    return {"id": event_id or f"evt_{uuid.uuid4().hex}", "type": etype, "livemode": False,
            "data": {"object": {"id": session_id, "object": "checkout.session", "payment_status": status,
                                "amount_total": booking["amount_cents"] if amount is None else amount,
                                "currency": currency, "payment_intent": "pi_test_1",
                                "metadata": {"booking_id": str(booking["id"])}}}}


def approved_booking(now, gw):
    b, token = request(now)
    approve(b["id"], now)
    url = payments.start_checkout(token, now=now)
    return b, token, url


def status_of(booking_id):
    with tx() as conn:
        return bookings.get(conn, booking_id)


def test_checkout_uses_approved_amount_and_dynamic_methods(now, gw):
    b, _, url = approved_booking(now, gw)
    params = gw.sessions[0]["params"]
    assert params["line_items"][0]["price_data"]["unit_amount"] == b["amount_cents"]
    assert params["line_items"][0]["price_data"]["currency"] == "usd"
    assert "payment_method_types" not in params          # Dashboard decides: cards, Apple Pay, Link, BNPL…
    assert params["excluded_payment_method_types"] == ["us_bank_account"]
    assert params["metadata"]["booking_id"] == str(b["id"])
    assert url.endswith("cs_test_1")


def test_checkout_session_reused_and_requires_approval(now, gw):
    b, token = request(now)
    with pytest.raises(Conflict):
        payments.start_checkout(token, now=now)           # not approved yet
    approve(b["id"], now)
    first = payments.start_checkout(token, now=now)
    again = payments.start_checkout(token, now=later(now, 2))
    assert first == again and len(gw.sessions) == 1


def test_invalid_signature_no_state_change(now, gw):
    b, _, _ = approved_booking(now, gw)
    body, _ = signed(session_event("cs_test_1", status_of(b["id"])))
    _, bad_sig = signed(session_event("cs_test_1", status_of(b["id"])), secret="whsec_wrong")
    with pytest.raises(Forbidden):
        payments.handle_event(body, bad_sig, now=now)
    with pytest.raises(Forbidden):
        payments.handle_event(body, None, now=now)
    assert status_of(b["id"])["status"] == Status.PAYMENT_PENDING


def test_duplicate_webhook_confirms_once(now, gw):
    b, _, _ = approved_booking(now, gw)
    event = session_event("cs_test_1", status_of(b["id"]), event_id="evt_dup")
    body, sig = signed(event)
    assert payments.handle_event(body, sig, now=now) == "confirmed"
    assert payments.handle_event(body, sig, now=now) == "duplicate"
    # same payment, different event id (Stripe retries can differ): still one confirmation
    body2, sig2 = signed(session_event("cs_test_1", status_of(b["id"]),
                                       etype="checkout.session.async_payment_succeeded"))
    assert payments.handle_event(body2, sig2, now=now) == "already_paid"
    with tx() as conn:
        receipts = conn.execute("SELECT count(*) AS n FROM outbox WHERE kind = 'confirmed'").fetchone()["n"]
        live = conn.execute("SELECT kind FROM reservations WHERE released_at IS NULL").fetchall()
    assert receipts == 1
    assert [r["kind"] for r in live] == ["confirmed"]
    assert status_of(b["id"])["status"] == Status.CONFIRMED


def test_success_redirect_alone_does_not_confirm(now, gw):
    b, _, _ = approved_booking(now, gw)
    # the browser coming back to ?checkout=returned changes nothing server-side
    assert status_of(b["id"])["status"] == Status.PAYMENT_PENDING


def test_failed_or_expired_checkout_not_confirmed(now, gw):
    b, _, _ = approved_booking(now, gw)
    cur = status_of(b["id"])
    for ev in (session_event("cs_test_1", cur, status="unpaid"),
               session_event("cs_test_1", cur, etype="checkout.session.async_payment_failed", status="unpaid"),
               session_event("cs_test_1", cur, etype="checkout.session.expired", status="unpaid")):
        payments.handle_event(*signed(ev), now=now)
    assert status_of(b["id"])["status"] == Status.PAYMENT_PENDING


def test_amount_or_metadata_mismatch_flags_review(now, gw):
    b, _, _ = approved_booking(now, gw)
    out = payments.handle_event(*signed(session_event("cs_test_1", status_of(b["id"]), amount=100)), now=now)
    assert out == "mismatch_flagged"
    after = status_of(b["id"])
    assert after["status"] == Status.PAYMENT_PENDING and after["review_flag"] == "payment_mismatch"


def test_live_event_ignored_outside_production(now, gw):
    b, _, _ = approved_booking(now, gw)
    ev = session_event("cs_test_1", status_of(b["id"]))
    ev["livemode"] = True
    assert payments.handle_event(*signed(ev), now=now) == "ignored_mode_mismatch"
    assert status_of(b["id"])["status"] == Status.PAYMENT_PENDING


def test_late_payment_for_expired_hold_flags_review(now, gw):
    b, _, _ = approved_booking(now, gw)
    with tx() as conn:
        bookings.release_expired_holds(conn, later(now, 6 * 60 + 5))
    assert status_of(b["id"])["status"] == Status.EXPIRED
    out = payments.handle_event(*signed(session_event("cs_test_1", status_of(b["id"]))), now=later(now, 400))
    assert out == "paid_flagged_for_review"
    after = status_of(b["id"])
    assert after["status"] == Status.EXPIRED and after["review_flag"] == "late_payment"


def test_customer_cancel_refund_recorded_once(now, gw):
    b, _, _ = approved_booking(now, gw)
    payments.handle_event(*signed(session_event("cs_test_1", status_of(b["id"]))), now=now)
    with tx() as conn:
        row, outcome = bookings.cancel(conn, b["id"], actor="customer", reason="plans changed", now=now,
                                       free_cancel_hours=24)
    assert outcome["refund_due"] and outcome["refund_cents"] == b["amount_cents"]
    assert payments.refund(outcome["payment_id"], outcome["refund_cents"])
    assert gw.refunds[0][1] == b["amount_cents"]
    refund_event = {"id": "evt_refund", "type": "charge.refunded", "livemode": False,
                    "data": {"object": {"id": "ch_1", "payment_intent": "pi_test_1",
                                        "amount_refunded": b["amount_cents"]}}}
    assert payments.handle_event(*signed(refund_event), now=now) == "refund_recorded"
    assert payments.handle_event(*signed(refund_event), now=now) == "duplicate"
    refund_event["id"] = "evt_refund_retry"
    assert payments.handle_event(*signed(refund_event), now=now) == "refund_already_recorded"
    with tx() as conn:
        pay = conn.execute("SELECT status, refunded_cents FROM payments").fetchone()
        mails = conn.execute("SELECT count(*) AS n FROM outbox WHERE kind = 'refunded'").fetchone()["n"]
    assert pay["status"] == "refunded" and pay["refunded_cents"] == b["amount_cents"] and mails == 1
    assert status_of(b["id"])["status"] == Status.CANCELLED


def test_late_customer_cancellation_is_reviewed_not_refunded(now, gw):
    b, _, _ = approved_booking(now, gw)
    payments.handle_event(*signed(session_event("cs_test_1", status_of(b["id"]))), now=now)
    pickup = status_of(b["id"])["pickup_at"]
    with tx() as conn:   # cancel 3 hours before pickup, inside the 24-hour window
        row, outcome = bookings.cancel(conn, b["id"], actor="customer", reason=None,
                                       now=pickup - (later(now, 180) - now), free_cancel_hours=24)
    assert not outcome["refund_due"] and row["review_flag"] == "late_cancellation"
    assert not gw.refunds


def test_trip_token_is_stable_and_hashed(now, gw):
    b, token = request(now)
    assert token == trip_token(b["id"])
    with tx() as conn:
        assert bookings.by_token(conn, token)["id"] == b["id"]
        assert token not in json.dumps(conn.execute("SELECT * FROM bookings").fetchone(), default=str)
