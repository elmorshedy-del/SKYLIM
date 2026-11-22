"""Quote decisions: price, eligibility and the calendar window a reservation occupies.

Pure functions only — no database, no clock reads, no environment. Everything a
decision depends on is passed in, so the same rules run in the API, the admin
panel and offline tools, and are trivially testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import LOCAL_TZ
from . import rates
from .catalog import Catalog

SERVICES = ("transfer", "hourly")

# Client-facing explanation for every reason code a quote can carry.
REASONS = {
    "custom_route": "This is a longer journey, so we prepare the price personally. Send the details and "
                    "you will have a firm quote shortly.",
    "authority_arranged": "We arrange journeys on this route by request. Send the details and we will "
                          "confirm availability and price personally.",
    "too_soon": "We ask for at least {notice_hours} hours' notice so every detail can be confirmed.",
    "too_far": "We accept reservations up to {max_days} days ahead.",
    "over_capacity": "The Escalade seats up to {max_pax} guests.",
    "capacity_review": "That is more luggage than our guide shows for this many guests, so we will confirm "
                       "the arrangement with you before payment.",
    "hours_range": "Hourly reservations run from {min_hours} to {max_hours} hours.",
    "estimate": "Estimated — confirmed before any payment.",
}
BLOCKING = {"custom_route", "authority_arranged", "too_soon", "too_far", "over_capacity", "hours_range"}
TIME_REASONS = {"too_soon", "too_far"}      # depend on the pickup time, not the route


class QuoteInputError(ValueError):
    """Input that can never produce a quote (unknown place, impossible time…)."""


@dataclass(frozen=True)
class TripRequest:
    service: str                  # "transfer" | "hourly"
    origin: str
    destination: Optional[str]    # None for hourly
    pickup_at: datetime           # timezone-aware
    passengers: int
    large_bags: int
    hours: Optional[float] = None
    carry_ons: int = 0


@dataclass(frozen=True)
class QuoteDecision:
    amount_cents: Optional[int]   # what the client pays
    list_cents: Optional[int]     # long-run list price (the reference price)
    offer: Optional[dict]         # introductory offer applied, if any
    price_status: str             # "firm" | "estimate" | "custom"
    eligible: bool
    needs_review: bool
    reasons: tuple[str, ...]
    service_start: datetime
    service_end: datetime
    loaded_minutes: int
    route_class: str
    snapshot: dict = field(default_factory=dict)


# ------------------------------------------------------------------- time
def parse_local_pickup(value: str) -> datetime:
    """Interpret 'YYYY-MM-DDTHH:MM' as New York wall-clock time; return UTC.

    The browser's timezone is irrelevant: a client in London booking a Newark
    pickup means Newark time. Times skipped by the spring DST change are
    rejected; for the repeated autumn hour the first occurrence is used.
    """
    try:
        naive = datetime.strptime(value.strip()[:16], "%Y-%m-%dT%H:%M")
    except (ValueError, AttributeError):
        raise QuoteInputError("Pickup time must look like 2026-11-25T06:30.")
    local = naive.replace(tzinfo=LOCAL_TZ, fold=0)
    if local.astimezone(timezone.utc).astimezone(LOCAL_TZ).replace(tzinfo=None) != naive:
        raise QuoteInputError("That time does not exist on the clock that day (daylight saving change).")
    return local.astimezone(timezone.utc)


def traffic_factor(at: datetime) -> float:
    """Conservative metro-area congestion multiplier for the local hour of travel."""
    local = at.astimezone(LOCAL_TZ)
    weekday = local.weekday() < 5
    h = local.hour + local.minute / 60
    if weekday and 6.5 <= h < 9.5:
        return 1.45
    if weekday and 15.5 <= h < 19:
        return 1.70 if local.weekday() == 4 else 1.50
    if not weekday and 11 <= h < 18:
        return 1.15
    if h >= 22 or h < 5:
        return 0.85
    return 1.0


# ------------------------------------------------------- authority, capacity
def route_class(cat: Catalog, origin: str, destination: Optional[str]) -> str:
    """Classify a trip by the licence that covers it (data.OPERATIONS['authority'] switches each on):

      nyc_pickup        starts in New York City                     (NYC TLC licence)
      into_nyc          starts outside NYC, ends in it              (e.g. Newark or Bergen -> Manhattan)
      nj_intrastate     both ends in New Jersey, NYC not involved   (NJ municipal limousine licence)
      interstate        crosses a state line without touching NYC   (e.g. Bergen -> Westchester)
      other_intrastate  both ends in one other state, outside NYC   (e.g. Westchester -> HPN)

    Hourly service is classified by where it starts.
    """
    o = cat.places[origin]
    d = cat.places[destination] if destination else o
    if o.nyc:
        return "nyc_pickup"
    if d.nyc:
        return "into_nyc"
    if o.state != d.state:
        return "interstate"
    return "nj_intrastate" if o.state == "NJ" else "other_intrastate"


LUGGAGE_UNITS = {"large": 2, "carry_on": 1}


def luggage_units(large_bags: int, carry_ons: int) -> int:
    return large_bags * LUGGAGE_UNITS["large"] + carry_ons * LUGGAGE_UNITS["carry_on"]


def luggage_capacity(vehicle: dict, passengers: int) -> int:
    """Luggage units available with this many guests seated (fewer guests -> third row folds)."""
    for max_guests, units in sorted(vehicle["luggage_capacity"]):
        if passengers <= max_guests:
            return units
    return 0


def capacity_check(vehicle: dict, passengers: int, large_bags: int, carry_ons: int = 0) -> Optional[str]:
    """None if it fits; 'capacity_review' if snug (confirmed with the client); 'over_capacity'."""
    if passengers < 1 or passengers > vehicle["max_passengers"]:
        return "over_capacity"
    fits = luggage_units(large_bags, carry_ons) <= luggage_capacity(vehicle, passengers)
    return None if fits else "capacity_review"


# ----------------------------------------------------------------- window
def heavy_day_factor(cat: Catalog, at: datetime) -> float:
    """Known heavy-traffic days (data.SCHEDULING['heavy_days']), by local date."""
    return float(cat.scheduling.get("heavy_days", {}).get(at.astimezone(LOCAL_TZ).date().isoformat(), 1.0))


def drive_factor(cat: Catalog, at: datetime) -> float:
    return traffic_factor(at) * heavy_day_factor(cat, at)


def service_window(cat: Catalog, req: TripRequest, loaded_minutes: int) -> tuple[datetime, datetime]:
    """The time the car is committed to this trip itself: on site before pickup until the drop-off is done.

    Getting there and moving on depend on the neighbouring trips, so availability.fit adds those drives
    (from the previous drop-off, to the next pickup) and the buffers — not this window.
    """
    p = cat.params
    origin = cat.places[req.origin]
    wait = p["airport_wait_min"] if origin.is_airport else cat.policy.get("wait_included_min", 15)
    if req.service == "hourly":
        on_job = (req.hours or p["hourly_min_hours"]) * 60
    else:
        on_job = wait + loaded_minutes * drive_factor(cat, req.pickup_at) + p["curbside_min"]
    return (req.pickup_at - timedelta(minutes=p["early_arrival_min"]),
            req.pickup_at + timedelta(minutes=round(on_job)))


def leg_minutes(cat: Catalog, a: Optional[str], b: Optional[str], at: datetime) -> float:
    """Drive between two place codes at that time of day; None means the chauffeur's home base."""
    pa = cat.places[a] if a else cat.base
    pb = cat.places[b] if b else cat.base
    return rates.drive_minutes(cat, pa, pb) * drive_factor(cat, at)


def risk_of(cat: Catalog, req: TripRequest) -> str:
    """What could make this trip run late — sets the buffer after it (data.SCHEDULING)."""
    if req.service == "hourly":
        return "hourly"
    return "airport_arrival" if cat.places[req.origin].is_airport else "standard"


# ------------------------------------------------------------------ quote
def decide_quote(cat: Catalog, req: TripRequest, *, now: datetime, min_notice_minutes: int,
                 max_advance_days: int) -> QuoteDecision:
    if req.service not in SERVICES:
        raise QuoteInputError("Choose point to point or by the hour.")
    if req.origin not in cat.places:
        raise QuoteInputError("Unknown pickup area.")
    if req.service == "transfer":
        if not req.destination or req.destination not in cat.places:
            raise QuoteInputError("Unknown destination.")
        if req.destination == req.origin and not cat.places[req.origin].kind == "area":
            raise QuoteInputError("Pickup and destination are the same place.")
    if req.pickup_at.tzinfo is None:
        raise QuoteInputError("Pickup time must be timezone-aware.")

    p = cat.params
    reasons: list[str] = []
    destination = req.destination if req.service == "transfer" else None
    rclass = route_class(cat, req.origin, destination)
    if not cat.authority.get(rclass, False):
        reasons.append("authority_arranged")

    if req.service == "hourly":
        hours = req.hours or 0
        if not p["hourly_min_hours"] <= hours <= p["hourly_max_hours"]:
            reasons.append("hours_range")
        amount = rates.hourly(cat, hours)
        loaded = round(hours * 60)
        committed = None
    else:
        est = rates.journey(cat, cat.places[req.origin], cat.places[destination])
        amount, loaded, committed = est.cents, est.loaded_minutes, est.committed_minutes
        if committed > p["max_committed_min_for_instant_price"]:
            reasons.append("custom_route")
            amount = None

    if req.pickup_at < now + timedelta(minutes=min_notice_minutes):
        reasons.append("too_soon")
    if req.pickup_at > now + timedelta(days=max_advance_days):
        reasons.append("too_far")
    cap = capacity_check(cat.vehicle, req.passengers, req.large_bags, req.carry_ons)
    if cap:
        reasons.append(cap)

    if amount is None:
        status = "custom"
    elif cat.pricing_approved:
        status = "firm"
    else:
        status = "estimate"
        reasons.append("estimate")

    list_cents, offer = amount, None
    if amount is not None:
        amount, offer = rates.introductory(cat, amount, now)

    start, end = service_window(cat, req, loaded)
    snapshot = {
        "service": req.service, "origin": req.origin, "destination": destination, "hours": req.hours,
        "pickup_at": req.pickup_at.isoformat(), "passengers": req.passengers, "large_bags": req.large_bags,
        "carry_ons": req.carry_ons, "amount_cents": amount, "list_cents": list_cents, "offer": offer,
        "pricing_version": cat.pricing_version, "pricing_approved": cat.pricing_approved,
        "loaded_minutes": loaded, "committed_minutes": committed, "route_class": rclass,
        "traffic_factor": traffic_factor(req.pickup_at), "home_base": cat.home_base,
        "policy_version": cat.policy["version"],
    }
    return QuoteDecision(amount_cents=amount, list_cents=list_cents, offer=offer, price_status=status,
                         eligible=amount is not None and not (set(reasons) & BLOCKING),
                         needs_review="capacity_review" in reasons, reasons=tuple(reasons),
                         service_start=start, service_end=end, loaded_minutes=loaded, route_class=rclass,
                         snapshot=snapshot)


def explain(reasons, cat: Catalog, *, min_notice_minutes: int, max_advance_days: int) -> list[dict]:
    """Reason codes -> [{code, message}] for the browser."""
    p = cat.params
    ctx = {"notice_hours": max(1, round(min_notice_minutes / 60)), "max_days": max_advance_days,
           "max_pax": cat.vehicle["max_passengers"], "min_hours": p["hourly_min_hours"],
           "max_hours": p["hourly_max_hours"]}
    return [{"code": r, "message": REASONS[r].format(**ctx)} for r in reasons if r in REASONS]
