"""Persisted quote snapshots with live availability, alternatives and instant eligibility."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import psycopg
from psycopg.types.json import Jsonb

from ..config import Settings, payments_live
from ..domain.catalog import Catalog
from ..domain.pricing import QuoteDecision, TripRequest, decide_quote, explain
from . import availability, flags

AVAILABILITY_MESSAGES = {
    "unavailable": "We are already reserved around that time.",
    "day_full": "That day is fully committed.",
}


def instant_allowed(conn: psycopg.Connection, *, eligible: bool, needs_review: bool, pickup_at: datetime,
                    now: datetime, s: Settings) -> bool:
    """Reserve-and-pay without owner approval: clean trips, enough notice, payments live, not paused."""
    return (eligible and not needs_review and payments_live(s)
            and pickup_at >= now + timedelta(minutes=s.instant_min_notice_minutes)
            and flags.enabled(conn, flags.INSTANT_BOOKING, default=True))


def create_quote(conn: psycopg.Connection, req: TripRequest, *, cat: Catalog, settings: Settings, now: datetime,
                 session_id: Optional[str] = None, attribution: Optional[dict] = None) -> dict:
    d: QuoteDecision = decide_quote(cat, req, now=now, min_notice_minutes=settings.min_notice_minutes,
                                    max_advance_days=settings.max_advance_days)
    avail = availability.check(conn, d.service_start, d.service_end, now, settings) if d.eligible else None
    bookable = d.eligible and avail == "available"
    reasons = list(d.reasons) + ([avail] if avail and avail != "available" else [])
    expires = now + timedelta(minutes=settings.quote_ttl_minutes)
    destination = req.destination if req.service == "transfer" else None
    row = conn.execute(
        """INSERT INTO quotes (expires_at, service, origin, destination, hours, route_class, pickup_at,
               passengers, large_bags, carry_ons, vehicle_code, amount_cents, price_status, service_start, service_end,
               eligible, needs_review, decision_reasons, pricing_version, availability, session_id,
               attribution, snapshot, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           RETURNING id""",
        (expires, req.service, req.origin, destination, req.hours, d.route_class, req.pickup_at,
         req.passengers, req.large_bags, req.carry_ons, cat.vehicle["code"], d.amount_cents, d.price_status, d.service_start,
         d.service_end, bookable, d.needs_review, reasons, cat.pricing_version, avail, session_id,
         Jsonb(attribution) if attribution else None, Jsonb(d.snapshot), now)).fetchone()

    messages = explain(d.reasons, cat, min_notice_minutes=settings.min_notice_minutes,
                       max_advance_days=settings.max_advance_days)
    alts: list[dict] = []
    if avail in AVAILABILITY_MESSAGES:
        alts = availability.alternatives(conn, cat, req, d.loaded_minutes, now, settings)
        messages.append({"code": avail, "message": AVAILABILITY_MESSAGES[avail] +
                         (" These times are open:" if alts else " Send a request and we will suggest an alternative.")})
    return {
        "quote_id": str(row["id"]),
        "amount_cents": d.amount_cents,
        "list_amount_cents": d.list_cents,
        "offer": d.offer,
        "currency": "usd",
        "price_status": d.price_status,
        "expires_at": expires.isoformat(),
        "bookable": bookable,
        "instant": bookable and instant_allowed(conn, eligible=True, needs_review=d.needs_review,
                                                pickup_at=req.pickup_at, now=now, s=settings),
        "needs_review": d.needs_review,
        "availability": avail,
        "alternatives": alts,
        "messages": messages,
        "route": {"service": req.service, "origin": cat.places[req.origin].short,
                  "destination": cat.places[destination].short if destination else None, "hours": req.hours},
        "pickup_at": req.pickup_at.isoformat(),
    }
