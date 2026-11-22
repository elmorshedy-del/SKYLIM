"""Persisted quote snapshots with live availability, alternatives and instant eligibility."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import psycopg
from psycopg.types.json import Jsonb

import data
from ..config import Settings, payments_live, payments_possible
from ..db import TEST_DRIVER_ID, TEST_VEHICLE_ID
from ..domain.catalog import Catalog
from ..domain.pricing import QuoteDecision, TripRequest, decide_quote, explain
from . import availability, flags

AVAILABILITY_MESSAGES = {
    "unavailable": "We are already reserved around that time.",
    "day_full": "That day is fully committed.",
    "tight": "That time sits close to another trip, so we confirm it personally — usually within the hour.",
}


def instant_allowed(conn: psycopg.Connection, *, eligible: bool, needs_review: bool, pickup_at: datetime,
                    now: datetime, s: Settings, is_test: bool = False) -> bool:
    """Reserve-and-pay without owner approval: clean trips, enough notice, payments live, not paused."""
    return (eligible and not needs_review and (payments_possible(s) if is_test else payments_live(s))
            and pickup_at >= now + timedelta(minutes=s.instant_min_notice_minutes)
            and flags.enabled(conn, flags.INSTANT_BOOKING, default=True))


def create_quote(conn: psycopg.Connection, req: TripRequest, *, cat: Catalog, settings: Settings, now: datetime,
                 session_id: Optional[str] = None, attribution: Optional[dict] = None, is_test: bool = False) -> dict:
    d: QuoteDecision = decide_quote(cat, req, now=now, min_notice_minutes=settings.min_notice_minutes,
                                    max_advance_days=settings.max_advance_days)
    resources = {"vehicle_id": TEST_VEHICLE_ID, "driver_id": TEST_DRIVER_ID} if is_test else {}
    avail = (availability.fit(conn, cat, availability.job_from_decision(cat, req, d), now, settings, **resources)
             if d.eligible else None)
    bookable = d.eligible and avail in availability.BOOKABLE        # tight: bookable as a request
    reasons = list(d.reasons) + ([avail] if avail and avail != "available" else [])
    expires = now + timedelta(minutes=settings.quote_ttl_minutes)
    destination = req.destination if req.service == "transfer" else None
    amount_cents = data.TEST_TRIP["amount_cents"] if is_test and d.amount_cents is not None else d.amount_cents
    price_status = "firm" if is_test and amount_cents is not None else d.price_status
    row = conn.execute(
        """INSERT INTO quotes (expires_at, service, origin, destination, hours, route_class, pickup_at,
               passengers, large_bags, carry_ons, vehicle_code, amount_cents, price_status, service_start, service_end,
               eligible, needs_review, decision_reasons, pricing_version, availability, session_id,
               attribution, snapshot, created_at, is_test)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           RETURNING id""",
        (expires, req.service, req.origin, destination, req.hours, d.route_class, req.pickup_at,
         req.passengers, req.large_bags, req.carry_ons, cat.vehicle["code"], amount_cents, price_status, d.service_start,
         d.service_end, bookable, d.needs_review, reasons, cat.pricing_version, avail, session_id,
         Jsonb(attribution) if attribution else None, Jsonb(d.snapshot), now, is_test)).fetchone()

    messages = explain(d.reasons, cat, min_notice_minutes=settings.min_notice_minutes,
                       max_advance_days=settings.max_advance_days)
    alts: list[dict] = []
    if avail in AVAILABILITY_MESSAGES:
        alts = availability.alternatives(conn, cat, req, d.loaded_minutes, now, settings, **resources)
        if avail == "tight":
            suffix = " Or reserve instantly at:" if alts else ""
        else:
            suffix = " These times are open:" if alts else " Send a request and we will suggest an alternative."
        messages.append({"code": avail, "message": AVAILABILITY_MESSAGES[avail] + suffix})
    return {
        "quote_id": str(row["id"]),
        "amount_cents": amount_cents,
        "list_amount_cents": amount_cents if is_test else d.list_cents,
        "offer": None if is_test else d.offer,
        "mock": is_test,
        "currency": "usd",
        "price_status": price_status,
        "expires_at": expires.isoformat(),
        "bookable": bookable,
        "instant": bookable and avail == "available" and instant_allowed(conn, eligible=True,
                                                                          needs_review=d.needs_review,
                                                pickup_at=req.pickup_at, now=now, s=settings, is_test=is_test),
        "needs_review": d.needs_review,
        "availability": avail,
        "alternatives": alts,
        "messages": messages,
        "route": {"service": req.service, "origin": cat.places[req.origin].short,
                  "destination": cat.places[destination].short if destination else None, "hours": req.hours},
        "pickup_at": req.pickup_at.isoformat(),
    }
