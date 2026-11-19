"""Builders that keep tests short and focused on the behaviour under test."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.config import get_settings
from app.db import tx
from app.domain.catalog import get_catalog
from app.domain.preferences import JourneyPreferences
from app.domain.pricing import TripRequest, parse_local_pickup
from app.services import bookings, quotes


def quote(now: datetime, *, origin="bergen", destination="jfk", service="transfer", hours=None,
          pickup="2026-11-25T06:30", passengers=2, bags=2, carry_ons=0) -> dict:
    req = TripRequest(service=service, origin=origin, destination=destination if service == "transfer" else None,
                      hours=hours, pickup_at=parse_local_pickup(pickup), passengers=passengers, large_bags=bags,
                      carry_ons=carry_ons)
    with tx() as conn:
        return quotes.create_quote(conn, req, cat=get_catalog(), settings=get_settings(), now=now)


def request(now: datetime, **kw) -> tuple[dict, str]:
    q = quote(now, **kw)
    assert q["bookable"], q
    with tx() as conn:
        return bookings.create(
            conn, quote_id=q["quote_id"],
            contact=bookings.Contact("Jordan Ellis", "Jordan@Example.com", "+1 201 555 0147"),
            trip=bookings.TripDetails("12 Prospect Ave, Hackensack NJ", "JFK Terminal 4"),
            preferences=JourneyPreferences(), remember=False,
            accepted_policy_version=get_catalog().policy["version"], source="test", cat=get_catalog(), now=now)


def approve(booking_id, now: datetime, **kw) -> dict:
    with tx() as conn:
        return bookings.approve(conn, booking_id, now=now, settings=get_settings(), **kw)


def later(now: datetime, minutes: int) -> datetime:
    return now + timedelta(minutes=minutes)
