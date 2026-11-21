"""Real-time availability for a small fleet: overlap, daily load and alternatives.

`check` answers "can the vehicle and chauffeur take this window?" without
writing anything; the binding guarantee is still the reservations exclusion
constraints at the moment a slot is held.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta

import psycopg

from ..config import LOCAL_TZ, Settings
from ..db import DRIVER_ID, VEHICLE_ID
from ..domain.catalog import Catalog
from ..domain.pricing import TripRequest, decide_quote, service_window

LIVE = "released_at IS NULL AND NOT (kind = 'hold' AND expires_at <= %(now)s)"
ALTERNATIVE_OFFSETS = (-30, 30, -60, 60, -90, 90, 120, -120, 180, 240)


def overlaps(conn: psycopg.Connection, start: datetime, end: datetime, now: datetime,
             vehicle_id=VEHICLE_ID, driver_id=DRIVER_ID) -> bool:
    row = conn.execute(
        f"""SELECT 1 FROM reservations
            WHERE (vehicle_id = %(v)s OR driver_id = %(d)s) AND {LIVE}
              AND during && tstzrange(%(s)s, %(e)s, '[)') LIMIT 1""",
        {"v": vehicle_id, "d": driver_id, "s": start, "e": end, "now": now}).fetchone()
    return row is not None


def day_minutes(conn: psycopg.Connection, start: datetime, now: datetime, driver_id=DRIVER_ID) -> int:
    """Committed minutes already on the chauffeur's local calendar day (blocks excluded)."""
    local = start.astimezone(LOCAL_TZ)
    day0 = local.replace(hour=0, minute=0, second=0, microsecond=0)
    day1 = day0 + timedelta(days=1)
    row = conn.execute(
        f"""SELECT COALESCE(sum(EXTRACT(EPOCH FROM (LEAST(upper(during), %(d1)s) - GREATEST(lower(during), %(d0)s)))) / 60, 0)
                   AS minutes
            FROM reservations
            WHERE driver_id = %(d)s AND kind <> 'block' AND {LIVE}
              AND during && tstzrange(%(d0)s, %(d1)s, '[)')""",
        {"d": driver_id, "d0": day0, "d1": day1, "now": now}).fetchone()
    return int(row["minutes"])


def check(conn: psycopg.Connection, start: datetime, end: datetime, now: datetime, s: Settings) -> str:
    if overlaps(conn, start, end, now):
        return "unavailable"
    if day_minutes(conn, start, now) + (end - start).total_seconds() / 60 > s.max_daily_minutes:
        return "day_full"
    return "available"


def alternatives(conn: psycopg.Connection, cat: Catalog, req: TripRequest, loaded_minutes: int, now: datetime,
                 s: Settings, limit: int = 3) -> list[dict]:
    """Nearest pickup times that are free, so a busy slot is never a dead end."""
    found: list[dict] = []
    earliest = now + timedelta(minutes=s.min_notice_minutes)
    for offset in ALTERNATIVE_OFFSETS:
        at = req.pickup_at + timedelta(minutes=offset)
        if at < earliest:
            continue
        start, end = service_window(cat, replace(req, pickup_at=at), loaded_minutes)
        if check(conn, start, end, now, s) == "available":
            local = at.astimezone(LOCAL_TZ)
            found.append({"pickup_local": local.strftime("%Y-%m-%dT%H:%M"),
                          "label": local.strftime("%-I:%M %p").lower().replace(":00", "")})
        if len(found) >= limit:
            break
    return sorted(found, key=lambda x: x["pickup_local"])


def day_slots(conn: psycopg.Connection, cat: Catalog, req: TripRequest, day: date, now: datetime,
              s: Settings, slots: dict) -> list[dict]:
    """Every pickup time on `day` (New York) that can be reserved online now, appointment-style.

    A time is offered only if it passes the same rules as a quote — route, capacity, notice, advance
    limit (decide_quote) — and the calendar check (overlap with the chauffeur's trips and the daily
    load). Times inside the instant-booking notice are not offered online. `slots` is
    data.OPERATIONS["slots"]: {"first": "HH:MM", "last": "HH:MM", "step_minutes": int}.
    """
    earliest = now + timedelta(minutes=s.instant_min_notice_minutes)
    step = timedelta(minutes=int(slots["step_minutes"]))
    at = datetime.combine(day, time.fromisoformat(slots["first"]), LOCAL_TZ)
    last = datetime.combine(day, time.fromisoformat(slots["last"]), LOCAL_TZ)
    out: list[dict] = []
    while at <= last:
        if at >= earliest:
            d = decide_quote(cat, replace(req, pickup_at=at), now=now, min_notice_minutes=s.min_notice_minutes,
                             max_advance_days=s.max_advance_days)
            if d.eligible and check(conn, d.service_start, d.service_end, now, s) == "available":
                out.append({"pickup_local": at.strftime("%Y-%m-%dT%H:%M"),
                            "label": at.strftime("%-I:%M %p").lower()})
        at += step
    return out
