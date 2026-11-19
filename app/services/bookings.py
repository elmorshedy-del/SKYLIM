"""Booking lifecycle: request -> approve (hold) -> confirm -> trip statuses -> done.

Every public function takes an open connection and runs inside the caller's
transaction, so a state change, its audit event, its calendar row and its
email are committed together or not at all.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import psycopg
from psycopg.types.json import Jsonb

from ..config import Settings
from ..db import DRIVER_ID, VEHICLE_ID
from ..domain.catalog import Catalog
from ..domain.preferences import JourneyPreferences
from ..domain.status import ACTIVE_TRIP, Status, assert_transition
from ..errors import Conflict, Invalid, NotFound
from ..security import booking_ref, token_hash, trip_token
from . import analytics, notifications

MIN_PAYMENT_WINDOW = timedelta(minutes=35)   # Stripe Checkout sessions must live >= 30 minutes


@dataclass(frozen=True)
class Contact:
    name: str
    email: str
    phone: str


@dataclass(frozen=True)
class TripDetails:
    pickup_address: str
    dropoff_address: str
    flight_number: Optional[str] = None
    notes: Optional[str] = None


# ------------------------------------------------------------------ helpers
def get(conn: psycopg.Connection, booking_id, *, lock: bool = False) -> dict:
    row = conn.execute("SELECT * FROM bookings WHERE id = %s" + (" FOR UPDATE" if lock else ""),
                       (booking_id,)).fetchone()
    if not row:
        raise NotFound("Booking not found.")
    return row


def by_token(conn: psycopg.Connection, token: str, *, lock: bool = False) -> dict:
    row = conn.execute("SELECT * FROM bookings WHERE access_token_hash = %s" + (" FOR UPDATE" if lock else ""),
                       (token_hash(token),)).fetchone()
    if not row:
        raise NotFound("This trip link is not valid.")
    return row


def log_event(conn, booking_id, actor: str, from_status, to_status, note: str | None = None) -> None:
    conn.execute("""INSERT INTO booking_events (booking_id, actor, from_status, to_status, note)
                    VALUES (%s, %s, %s, %s, %s)""",
                 (booking_id, actor, str(from_status) if from_status else None,
                  str(to_status) if to_status else None, note))


def _set_status(conn, b: dict, target: Status, actor: str, now: datetime, note: str | None = None,
                **columns) -> dict:
    assert_transition(b["status"], target)
    sets = ", ".join(f"{k} = %({k})s" for k in columns)
    params = {"id": b["id"], "status": str(target), "now": now, **columns}
    row = conn.execute(
        f"UPDATE bookings SET status = %(status)s, updated_at = %(now)s{', ' + sets if sets else ''} "
        f"WHERE id = %(id)s RETURNING *", params).fetchone()
    log_event(conn, b["id"], actor, b["status"], target, note)
    return row


def release_reservation(conn, booking_id, now: datetime, reason: str) -> None:
    conn.execute("""UPDATE reservations SET released_at = %s, release_reason = %s
                    WHERE booking_id = %s AND released_at IS NULL""", (now, reason, booking_id))


# ------------------------------------------------------------------ request
def _review_flag(quote: dict, prefs: JourneyPreferences) -> Optional[str]:
    """Anything the owner must check before approving, beyond the calendar."""
    if quote["needs_review"]:
        return "capacity_review"
    if prefs.wants_child_seat:
        return "child_seat_check"
    return None


def create(conn: psycopg.Connection, *, quote_id, contact: Contact, trip: TripDetails,
           preferences: JourneyPreferences, remember: bool, accepted_policy_version: str,
           source: Optional[str], cat: Catalog, now: datetime, attribution: Optional[dict] = None,
           instant: bool = False, settings: Optional[Settings] = None) -> tuple[dict, str]:
    """Turn a quote into a reservation. Returns (booking, trip_token).

    instant=True (decided by the caller from quotes.instant_allowed) holds the slot
    straight away and moves to payment, with no owner approval in between.
    """
    q = conn.execute("SELECT * FROM quotes WHERE id = %s FOR UPDATE", (quote_id,)).fetchone()
    if not q:
        raise NotFound("Quote not found — please price the trip again.")
    if q["expires_at"] <= now:
        raise Conflict("This price has expired. Please price the trip again.", code="quote_expired")
    if not q["eligible"] or q["amount_cents"] is None:
        raise Conflict("This trip can't be requested online. Please send a custom request.",
                       code="not_bookable")
    if accepted_policy_version != cat.policy["version"]:
        raise Conflict("Our booking terms have changed. Please review them and try again.",
                       code="policy_changed")
    if conn.execute("SELECT 1 FROM bookings WHERE quote_id = %s", (quote_id,)).fetchone():
        raise Conflict("This quote has already been used for a request.", code="quote_used")

    email = contact.email.strip().lower()
    customer = conn.execute(
        """INSERT INTO customers (email, full_name, phone) VALUES (%s, %s, %s)
           ON CONFLICT (email) DO UPDATE SET updated_at = customers.updated_at
           RETURNING id""", (email, contact.name, contact.phone)).fetchone()

    # Retry on the (astronomically unlikely) reference collision.
    for _ in range(5):
        ref = booking_ref()
        if not conn.execute("SELECT 1 FROM bookings WHERE ref = %s", (ref,)).fetchone():
            break
    booking_id = uuid.uuid4()
    token = trip_token(booking_id)
    booking = conn.execute(
        """INSERT INTO bookings (id, ref, quote_id, customer_id, contact_name, contact_email, contact_phone,
               status, service, hours, pickup_at, service_start, service_end, pickup_address, dropoff_address,
               flight_number, passengers, large_bags, notes, preferences, remember_preferences,
               policy_version, amount_cents, access_token_hash, review_flag, source, attribution, instant,
               created_at, updated_at)
           VALUES (%(id)s, %(ref)s, %(quote)s, %(customer)s, %(name)s, %(email)s, %(phone)s, 'requested',
               %(service)s, %(hours)s, %(pickup_at)s, %(start)s, %(end)s, %(pickup)s, %(drop)s, %(flight)s,
               %(pax)s, %(bags)s,
               %(notes)s, %(prefs)s, %(remember)s, %(policy)s, %(amount)s, %(token_hash)s, %(flag)s,
               %(source)s, %(attribution)s, %(instant)s, %(now)s, %(now)s)
           RETURNING *""",
        {"id": booking_id, "token_hash": token_hash(token), "ref": ref, "quote": q["id"],
         "customer": customer["id"], "name": contact.name, "email": email, "phone": contact.phone,
         "service": q["service"], "hours": q["hours"], "pickup_at": q["pickup_at"], "start": q["service_start"],
         "end": q["service_end"], "pickup": trip.pickup_address, "drop": trip.dropoff_address,
         "flight": trip.flight_number, "pax": q["passengers"], "bags": q["large_bags"], "notes": trip.notes,
         "prefs": Jsonb(preferences.model_dump()), "remember": remember, "policy": cat.policy["version"],
         "amount": q["amount_cents"], "flag": _review_flag(q, preferences),
         "source": (source or "")[:120] or None, "attribution": Jsonb(attribution) if attribution else None,
         "instant": instant, "now": now}).fetchone()
    log_event(conn, booking["id"], "customer", None, Status.REQUESTED)
    if instant:
        booking = approve(conn, booking["id"], now=now, settings=settings, actor="system",
                          hold_minutes=settings.instant_hold_minutes)
    else:
        notifications.enqueue(conn, "request_received", booking)
    notifications.enqueue(conn, "owner_new_request", booking)
    return booking, token


# ------------------------------------------------------------------ calendar
def release_expired_holds(conn: psycopg.Connection, now: datetime) -> list[dict]:
    """Release lapsed payment holds and mark their bookings expired.
    Runs at the start of every approval and from the background sweeper."""
    rows = conn.execute(
        """WITH released AS (
               UPDATE reservations SET released_at = %(now)s, release_reason = 'hold_expired'
               WHERE kind = 'hold' AND released_at IS NULL AND expires_at <= %(now)s
               RETURNING booking_id)
           UPDATE bookings b SET status = 'expired', updated_at = %(now)s
           FROM released r WHERE b.id = r.booking_id AND b.status = 'payment_pending'
           RETURNING b.*""", {"now": now}).fetchall()
    for b in rows:
        log_event(conn, b["id"], "system", Status.PAYMENT_PENDING, Status.EXPIRED, "payment hold lapsed")
        notifications.enqueue(conn, "expired", b)
    return rows


def approve(conn: psycopg.Connection, booking_id, *, now: datetime, settings: Settings,
            amount_cents: Optional[int] = None, adjust_reason: Optional[str] = None,
            vehicle_id=VEHICLE_ID, driver_id=DRIVER_ID, actor: str = "admin",
            hold_minutes: Optional[int] = None) -> dict:
    """Owner accepts a request: hold the vehicle and driver, then offer payment.

    Overlap safety comes from the reservations exclusion constraints: if two
    approvals race for overlapping windows, PostgreSQL lets exactly one commit.
    """
    b = get(conn, booking_id, lock=True)
    assert_transition(b["status"], Status.PAYMENT_PENDING)
    amount = b["amount_cents"] if amount_cents is None else amount_cents
    if amount <= 0:
        raise Invalid("Price must be positive.")
    if amount != b["amount_cents"] and not (adjust_reason or "").strip():
        raise Invalid("Give a reason when changing the quoted price — the rider will see the new total.")

    release_expired_holds(conn, now)
    hold_until = min(now + timedelta(minutes=hold_minutes or settings.hold_minutes), b["service_start"])
    if hold_until - now < MIN_PAYMENT_WINDOW:
        raise Conflict("Too close to the trip to take online payment. Decline, or call the rider.",
                       code="too_late_for_payment")
    try:
        with conn.transaction():  # savepoint: an overlap must not poison the outer transaction
            conn.execute(
                """INSERT INTO reservations (booking_id, vehicle_id, driver_id, during, kind, expires_at)
                   VALUES (%s, %s, %s, tstzrange(%s, %s, '[)'), 'hold', %s)""",
                (b["id"], vehicle_id, driver_id, b["service_start"], b["service_end"], hold_until))
    except psycopg.errors.ExclusionViolation:
        raise Conflict("The car or driver is already reserved for an overlapping time.", code="slot_taken")

    row = _set_status(conn, b, Status.PAYMENT_PENDING, actor, now, note=adjust_reason or (
                          "instant reservation" if actor == "system" else None),
                      vehicle_id=vehicle_id, driver_id=driver_id, amount_cents=amount,
                      price_adjust_reason=(adjust_reason or None), approved_at=now)
    # For instant reservations this doubles as an abandoned-checkout recovery email.
    notifications.enqueue(conn, "payment_link", row, hold_until=hold_until)
    return row


def decline(conn: psycopg.Connection, booking_id, *, reason: str | None, now: datetime) -> dict:
    b = get(conn, booking_id, lock=True)
    row = _set_status(conn, b, Status.DECLINED, "admin", now, note=reason, cancelled_at=now,
                      cancel_reason=reason)
    notifications.enqueue(conn, "declined", row, reason=reason)
    return row


def confirm_paid(conn: psycopg.Connection, b: dict, *, paid_cents: int, now: datetime) -> dict:
    """Called by the payment webhook with the booking row locked. Converts the
    hold into a confirmed reservation; if the hold is gone, flags for review."""
    if b["status"] != Status.PAYMENT_PENDING:
        flag = "late_payment" if b["status"] in (Status.EXPIRED, Status.CANCELLED, Status.DECLINED) else None
        if flag:
            conn.execute("UPDATE bookings SET review_flag = %s, updated_at = %s WHERE id = %s",
                         (flag, now, b["id"]))
            log_event(conn, b["id"], "stripe", b["status"], None, "payment received after hold ended — refund or reinstate")
        return b
    held = conn.execute(
        """UPDATE reservations SET kind = 'confirmed', expires_at = NULL
           WHERE booking_id = %s AND released_at IS NULL RETURNING id""", (b["id"],)).fetchone()
    if not held:
        conn.execute("UPDATE bookings SET review_flag = 'late_payment', updated_at = %s WHERE id = %s",
                     (now, b["id"]))
        log_event(conn, b["id"], "stripe", b["status"], None, "payment received but hold already released")
        return get(conn, b["id"])
    row = _set_status(conn, b, Status.CONFIRMED, "stripe", now, confirmed_at=now)
    if row["remember_preferences"]:
        conn.execute("UPDATE customers SET saved_preferences = %s, updated_at = %s WHERE id = %s",
                     (Jsonb(row["preferences"]), now, row["customer_id"]))
    notifications.enqueue(conn, "confirmed", row, paid_cents=paid_cents)
    analytics.enqueue_purchase(conn, row, paid_cents)
    return row


# --------------------------------------------------------------- operations
def advance(conn: psycopg.Connection, booking_id, target: Status, *, now: datetime, actor: str = "admin",
            note: str | None = None, retention_hours: int = 0) -> dict:
    """Owner taps En route / Arrived / In vehicle / Completed."""
    b = get(conn, booking_id, lock=True)
    extra = {}
    if target == Status.COMPLETED:
        extra["completed_at"] = now
    if target == Status.EN_ROUTE:
        # one active trip per driver: tracking must never attach to the wrong booking
        busy = conn.execute(
            """SELECT ref FROM bookings WHERE driver_id = %s AND id <> %s
               AND status IN ('en_route', 'arrived', 'in_vehicle')""", (b["driver_id"], b["id"])).fetchone()
        if busy:
            raise Conflict(f"Finish trip {busy['ref']} before starting another.", code="driver_busy")
        extra["trip_started_at"] = now
    row = _set_status(conn, b, target, actor, now, note, **extra)
    if target == Status.CONFIRMED:   # "En route" was undone: discard any location taken
        conn.execute("DELETE FROM positions WHERE booking_id = %s", (b["id"],))
    if target in (Status.EN_ROUTE, Status.ARRIVED):
        v = conn.execute("SELECT display_name, color, plate FROM vehicles WHERE id = %s",
                         (row["vehicle_id"],)).fetchone()
        d = conn.execute("SELECT display_name FROM drivers WHERE id = %s", (row["driver_id"],)).fetchone()
        line = " ".join(x for x in ((v or {}).get("color"), (v or {}).get("display_name")) if x)
        if v and v.get("plate"):
            line += f", plate {v['plate']}"
        notifications.enqueue(conn, str(target), row, dedupe=f"{target}:{row['id']}:{now:%Y%m%d%H%M}",
                              vehicle_line=f"Look for: {line}." if line else "",
                              driver_name=(d or {}).get("display_name"))
    if target == Status.COMPLETED:
        release_reservation(conn, b["id"], now, "completed")
        if retention_hours <= 0:
            conn.execute("DELETE FROM positions WHERE booking_id = %s", (b["id"],))
    return row


def cancel(conn: psycopg.Connection, booking_id, *, actor: str, reason: str | None, now: datetime,
           free_cancel_hours: int) -> tuple[dict, dict]:
    """Cancel and release the calendar. Returns (booking, outcome) where outcome
    says whether an automatic full refund is due. The refund itself is created
    with Stripe after this transaction commits (see services/payments.py)."""
    b = get(conn, booking_id, lock=True)
    paid = b["status"] in (Status.CONFIRMED,) or Status(b["status"]) in ACTIVE_TRIP
    if actor == "customer" and Status(b["status"]) in ACTIVE_TRIP:
        raise Conflict("Your chauffeur is already on the way — please call to cancel.", code="trip_active")
    refund_due = paid and (actor == "admin" or b["pickup_at"] - now >= timedelta(hours=free_cancel_hours))
    row = _set_status(conn, b, Status.CANCELLED, actor, now, reason, cancelled_at=now,
                      cancel_reason=reason, review_flag=None if refund_due or not paid else "late_cancellation")
    release_reservation(conn, b["id"], now, "cancelled")
    conn.execute("DELETE FROM positions WHERE booking_id = %s", (b["id"],))
    payment = conn.execute(
        """SELECT * FROM payments WHERE booking_id = %s AND status IN ('paid', 'partially_refunded')""",
        (b["id"],)).fetchone()
    refund_cents = (payment["amount_cents"] - payment["refunded_cents"]) if (payment and refund_due) else 0
    notifications.enqueue(conn, "cancelled", row, refund_cents=refund_cents, was_paid=paid)
    return row, {"refund_due": bool(refund_cents), "refund_cents": refund_cents,
                 "payment_id": payment["id"] if payment else None}
