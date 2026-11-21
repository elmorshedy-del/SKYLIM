"""The owner's $1 test trip: one real booking, paid for real, to prove the whole payment path.

Switched on and off in data.TEST_TRIP. When on, /admin shows "Start a $1 test trip", which books a
real trip through the normal path — quote, booking, hold, Stripe Checkout, webhook, confirmation,
trip page — with three explicit differences:

  1. the price is TEST_TRIP["amount_cents"]: the trip is quoted normally, then marked down;
  2. the hold sits on a hidden test vehicle and chauffeur, so it can never block a client's time;
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
from ..domain.pricing import TripRequest
from ..errors import NotFound, Unavailable
from . import bookings, quotes

SOURCE = "test_trip"


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
    """Book the test trip and hold it on the test vehicle. Returns (booking, trip token)."""
    if not enabled():
        raise NotFound("Test trips are switched off (data.TEST_TRIP).")
    ok, why = readiness(settings)
    if not ok:
        raise Unavailable(f"Test trip not available: {why}.")
    cfg = data.TEST_TRIP
    origin, destination = cfg["route"]
    pickup = (now + timedelta(hours=cfg["lead_hours"])).astimezone(LOCAL_TZ).replace(minute=0, second=0, microsecond=0)
    req = TripRequest(service="transfer", origin=origin, destination=destination, pickup_at=pickup,
                      passengers=1, large_bags=0)
    q = quotes.create_quote(conn, req, cat=cat, settings=settings, now=now, attribution={"source": SOURCE})
    conn.execute("UPDATE quotes SET amount_cents = %s, eligible = true, needs_review = false WHERE id = %s",
                 (cfg["amount_cents"], q["quote_id"]))
    booking, token = bookings.create(
        conn, quote_id=q["quote_id"],
        contact=bookings.Contact("Owner (test trip)", settings.owner_email, data.BRAND["phone_raw"]),
        trip=bookings.TripDetails("Test trip — no pickup", "Test trip — no drop-off",
                                  notes="The owner's check of the payment path. Not a real ride."),
        preferences=JourneyPreferences(), remember=False, accepted_policy_version=cat.policy["version"],
        source=SOURCE, cat=cat, now=now, settings=settings, is_test=True)
    booking = bookings.approve(conn, booking["id"], now=now, settings=settings, vehicle_id=TEST_VEHICLE_ID,
                               driver_id=TEST_DRIVER_ID, hold_minutes=cfg["hold_minutes"])
    return booking, token
