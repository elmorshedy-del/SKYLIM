"""Real-time availability for a sole operator: back-to-back trips with buffers for the unpredictable.

Each reservation covers only a trip's own time (on site before pickup until the drop-off). `fit` decides
whether a new trip can sit in the chauffeur's day, looking at its neighbours:

  * the drive from the previous drop-off to this pickup, and from this drop-off to the next pickup,
    at that time of day (heavy-traffic days included);
  * a buffer after each trip for what can make it run late — longer after an airport pickup, where a
    flight sets the start (data.SCHEDULING).

    available    fits with the buffers                    -> reserved and paid instantly
    tight        fits only if everything runs on time    -> "on request": the owner judges and approves
    unavailable  does not fit (overlap, or can't get there in time)
    day_full     the day's committed time would pass the cap

`fit` writes nothing. The binding guarantee against double-booking is still the reservations exclusion
constraint, and bookings.approve re-runs `fit` under a per-chauffeur lock before holding a slot.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import Optional

import psycopg

from ..config import LOCAL_TZ, Settings
from ..db import DRIVER_ID, VEHICLE_ID
from ..domain.catalog import Catalog
from ..domain.pricing import QuoteDecision, TripRequest, decide_quote, leg_minutes, risk_of, service_window

LIVE = "released_at IS NULL AND NOT (kind = 'hold' AND expires_at <= %(now)s)"
# Minutes either side of a busy time, nearest first; reaches 6 hours so heavy days still offer something.
ALTERNATIVE_OFFSETS = (-30, 30, -60, 60, -90, 90, 120, -120, 150, 180, -180, 210, 240, 270, 300, 330, 360)
BOOKABLE = ("available", "tight")


@dataclass(frozen=True)
class Job:
    """A trip's place in the chauffeur's day."""
    start: datetime          # on site, before pickup
    end: datetime            # drop-off done
    origin: str              # pickup place code
    end_place: str           # drop-off place code (the pickup place for hourly service)
    risk: str                # what could make it run late: sets the buffer after it

    @property
    def minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60


def job_for(cat: Catalog, req: TripRequest, start: datetime, end: datetime) -> Job:
    return Job(start, end, req.origin, req.destination or req.origin, risk_of(cat, req))


def job_from_decision(cat: Catalog, req: TripRequest, d: QuoteDecision) -> Job:
    return job_for(cat, req, d.service_start, d.service_end)


def overlaps(conn: psycopg.Connection, start: datetime, end: datetime, now: datetime,
             vehicle_id=VEHICLE_ID, driver_id=DRIVER_ID) -> bool:
    row = conn.execute(
        f"""SELECT 1 FROM reservations
            WHERE (vehicle_id = %(v)s OR driver_id = %(d)s) AND {LIVE}
              AND during && tstzrange(%(s)s, %(e)s, '[)') LIMIT 1""",
        {"v": vehicle_id, "d": driver_id, "s": start, "e": end, "now": now}).fetchone()
    return row is not None


def day_minutes(conn: psycopg.Connection, start: datetime, now: datetime, driver_id=DRIVER_ID) -> int:
    """Minutes already committed to trips on the chauffeur's local calendar day (blocks excluded)."""
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


def _neighbours(conn, job: Job, now: datetime, vehicle_id, driver_id) -> tuple[Optional[dict], Optional[dict]]:
    """The trip (or block) just before this one, and just after."""
    args = {"v": vehicle_id, "d": driver_id, "s": job.start, "e": job.end, "now": now}
    scope = f"(vehicle_id = %(v)s OR driver_id = %(d)s) AND {LIVE}"
    before = conn.execute(
        f"""SELECT upper(during) AS at, end_place AS place, COALESCE(risk, CASE WHEN kind = 'block'
                   THEN 'block' ELSE 'standard' END) AS risk
            FROM reservations WHERE {scope} AND upper(during) <= %(s)s
            ORDER BY upper(during) DESC LIMIT 1""", args).fetchone()
    after = conn.execute(
        f"""SELECT lower(during) AS at, start_place AS place
            FROM reservations WHERE {scope} AND lower(during) >= %(e)s
            ORDER BY lower(during) ASC LIMIT 1""", args).fetchone()
    return before, after


def fit(conn: psycopg.Connection, cat: Catalog, job: Job, now: datetime, s: Settings,
        vehicle_id=VEHICLE_ID, driver_id=DRIVER_ID) -> str:
    """'available', 'tight', 'unavailable' or 'day_full' — see the module docstring."""
    if overlaps(conn, job.start, job.end, now, vehicle_id, driver_id):
        return "unavailable"
    if day_minutes(conn, job.start, now, driver_id) + job.minutes > s.max_daily_minutes:
        return "day_full"
    buffers = cat.scheduling["buffer_after_min"]
    before, after = _neighbours(conn, job, now, vehicle_id, driver_id)
    tight = False
    if before:   # can the chauffeur get here from the previous drop-off — with margin for it running late?
        arrive = before["at"] + timedelta(minutes=leg_minutes(cat, before["place"], job.origin, before["at"]))
        if arrive > job.start:
            return "unavailable"
        tight |= arrive + timedelta(minutes=buffers[before["risk"]]) > job.start
    if after:    # and from this drop-off to the next pickup?
        arrive = job.end + timedelta(minutes=leg_minutes(cat, job.end_place, after["place"], job.end))
        if arrive > after["at"]:
            return "unavailable"
        tight |= arrive + timedelta(minutes=buffers[job.risk]) > after["at"]
    return "tight" if tight else "available"


def alternatives(conn: psycopg.Connection, cat: Catalog, req: TripRequest, loaded_minutes: int, now: datetime,
                 s: Settings, limit: int = 3) -> list[dict]:
    """Nearest pickup times that can be reserved instantly, so a busy or tight time is never a dead end."""
    found: list[dict] = []
    earliest = now + timedelta(minutes=s.min_notice_minutes)
    for offset in ALTERNATIVE_OFFSETS:
        at = req.pickup_at + timedelta(minutes=offset)
        if at < earliest:
            continue
        alt = replace(req, pickup_at=at)
        start, end = service_window(cat, alt, loaded_minutes)
        if fit(conn, cat, job_for(cat, alt, start, end), now, s) == "available":
            local = at.astimezone(LOCAL_TZ)
            found.append({"pickup_local": local.strftime("%Y-%m-%dT%H:%M"),
                          "label": local.strftime("%-I:%M %p").lower().replace(":00", "")})
        if len(found) >= limit:
            break
    return sorted(found, key=lambda x: x["pickup_local"])


def day_slots(conn: psycopg.Connection, cat: Catalog, req: TripRequest, day: date, now: datetime,
              s: Settings, slots: dict) -> list[dict]:
    """Every pickup time on `day` (New York) that can be reserved online, appointment-style.

    A time is offered if it passes the same rules as a quote — route, capacity, notice, advance limit
    (decide_quote) — and fits the chauffeur's day (`fit`). Each slot says how it is reserved:
    "instant" (fits with buffers) or "request" (tight: the owner confirms). Times inside the online
    notice period are not offered. `slots` is data.OPERATIONS["slots"].
    """
    earliest = now + timedelta(minutes=s.instant_min_notice_minutes)
    step = timedelta(minutes=int(slots["step_minutes"]))
    at = datetime.combine(day, time.fromisoformat(slots["first"]), LOCAL_TZ)
    last = datetime.combine(day, time.fromisoformat(slots["last"]), LOCAL_TZ)
    out: list[dict] = []
    while at <= last:
        if at >= earliest:
            slot_req = replace(req, pickup_at=at)
            d = decide_quote(cat, slot_req, now=now, min_notice_minutes=s.min_notice_minutes,
                             max_advance_days=s.max_advance_days)
            verdict = fit(conn, cat, job_from_decision(cat, slot_req, d), now, s) if d.eligible else None
            if verdict in BOOKABLE:
                out.append({"pickup_local": at.strftime("%Y-%m-%dT%H:%M"), "label": at.strftime("%-I:%M %p").lower(),
                            "mode": "instant" if verdict == "available" else "request"})
        at += step
    return out
