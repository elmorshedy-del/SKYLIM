"""The owner's $1 test trip: readiness checks and the legacy admin quick-start.

Switched on and off in data.TEST_TRIP. The website reservation form is the primary mock entry point;
the legacy admin quick-start still books a trip through the normal path — quote, booking, hold, Stripe Checkout, webhook, confirmation,
trip page — with three explicit differences:

  1. the price is TEST_TRIP["amount_cents"]: the trip is quoted normally, then marked down;
  2. the hold sits on a hidden test vehicle and chauffeur, so it can never block a client's time
     (it takes the instant-booking path a client's reservation takes, held for INSTANT_HOLD_MINUTES);
  3. the booking is flagged is_test: no Google Analytics purchase, no Google Ads conversion, not in
     the funnel. It may be paid before the launch gates pass (the owner is paying the owner), but a
     live key is still never used outside production (config.payments_possible).

Cancel it from /admin afterwards to test the refund as well.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

import data
from ..config import LOCAL_TZ, Settings, payments_possible
from ..db import TEST_DRIVER_ID, TEST_VEHICLE_ID
from ..domain.catalog import Catalog
from ..domain.preferences import JourneyPreferences
from ..domain.pricing import TripRequest, decide_quote
from ..errors import Conflict, NotFound, Unavailable
from ..security import trip_token
from . import availability, bookings, quotes

SOURCE = "test_trip"
REOPEN_IF_HELD_FOR = timedelta(minutes=5)   # an unpaid test trip held at least this long is reopened, not duplicated


def enabled() -> bool:
    return bool(data.TEST_TRIP.get("enabled"))


def readiness(s: Settings) -> tuple[bool, str]:
    """Whether a test trip can be paid right now, and if not, what is missing — for /admin."""
    if not enabled():
        return False, "switched off in data.py (TEST_TRIP)"
    if not s.payments_enabled:
        return False, "PAYMENTS_ENABLED is not true"
    if not s.stripe_secret_key:
        return False, "STRIPE_SECRET_KEY is not set"
    if not payments_possible(s):
        return False, ("a live Stripe key is only used in production — set APP_ENV=production (clients stay on "
                       "requests until the launch gates pass)" if s.stripe_live
                       else "the Stripe webhook is still connecting — try again in a minute")
    return True, ""


def start(conn: psycopg.Connection, *, now: datetime, settings: Settings, cat: Catalog) -> tuple[dict, str]:
    """Reopen the unpaid test trip if one is still held; otherwise book a new one on the next free hour of
    the test calendar, through the same instant path a client's booking takes. Returns (booking, token).
    Tapping the button twice therefore never creates two trips or an overlap."""
    if not enabled():
        raise NotFound("Test trips are switched off (data.TEST_TRIP).")
    ok, why = readiness(settings)
    if not ok:
        raise Unavailable(f"Test trip not available: {why}.")
    open_trip = conn.execute(
        """SELECT b.* FROM bookings b JOIN reservations r ON r.booking_id = b.id
           WHERE b.is_test AND b.status = 'payment_pending' AND r.kind = 'hold' AND r.released_at IS NULL
             AND r.expires_at > %s
           ORDER BY b.created_at DESC LIMIT 1""", (now + REOPEN_IF_HELD_FOR,)).fetchone()
    if open_trip:
        return open_trip, trip_token(open_trip["id"])

    cfg = data.TEST_TRIP
    origin, destination = cfg["route"]
    first = (now + timedelta(hours=cfg["lead_hours"])).astimezone(LOCAL_TZ).replace(minute=0, second=0, microsecond=0)
    for hour in range(48):
        req = TripRequest(service="transfer", origin=origin, destination=destination,
                          pickup_at=first + timedelta(hours=hour), passengers=1, large_bags=0)
        d = decide_quote(cat, req, now=now, min_notice_minutes=0, max_advance_days=10_000)
        verdict = availability.fit(conn, cat, availability.job_from_decision(cat, req, d), now, settings,
                                   vehicle_id=TEST_VEHICLE_ID, driver_id=TEST_DRIVER_ID)
        if verdict == "available":         # the same rule a client's instant booking must pass
            break
    else:
        raise Conflict("The test calendar is full — cancel an earlier test trip in /admin.", code="test_calendar_full")

    q = quotes.create_quote(conn, req, cat=cat, settings=settings, now=now, is_test=True)
    conn.execute("UPDATE quotes SET amount_cents = %s, eligible = true, needs_review = false WHERE id = %s",
                 (cfg["amount_cents"], q["quote_id"]))
    return bookings.create(
        conn, quote_id=q["quote_id"],
        contact=bookings.Contact("Owner (test trip)", settings.owner_email, data.BRAND["phone_raw"]),
        trip=bookings.TripDetails("Test trip — no pickup", "Test trip — no drop-off",
                                  notes="The owner's check of the payment path. Not a real ride."),
        preferences=JourneyPreferences(), remember=False, accepted_policy_version=cat.policy["version"],
        source=SOURCE, cat=cat, now=now, settings=settings, is_test=True, instant=True,
        resources=(TEST_VEHICLE_ID, TEST_DRIVER_ID))
