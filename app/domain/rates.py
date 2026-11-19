"""The pricing cost model — one implementation shared by live quotes and tools/rate_model.py.

A chauffeured vehicle sells *committed time*: the drive out to the pickup, the
journey at the traffic of that hour, curbside time and the drive back to base.
Price = committed hours x target rate + running cost per mile + tolls + a share
of fixed costs, grossed up for card fees and rounded up to the next $5.
Hourly service is a published all-inclusive rate with a minimum.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from ..config import LOCAL_TZ
from . import geo
from .catalog import Catalog, Place

NY_EAST = {"NY", "CT"}


@dataclass(frozen=True)
class Estimate:
    cents: int
    loaded_minutes: int        # the client's journey, off-peak
    committed_minutes: int     # everything the vehicle is unavailable for
    miles: int
    tolls_cents: int


def _leg(cat: Catalog, a: Place, b: Place, crossing: float = 0) -> tuple[float, float]:
    return geo.leg(a.point, b.point, cat.params, crossing)


def tolls_cents(cat: Catalog, origin: Place, dest: Place, total_miles: float) -> int:
    """Round-trip toll estimate for base -> origin -> destination -> base."""
    p = cat.params
    ends = (origin, dest)
    t = 0.0
    if cat.base.state == "NJ" and any(x.state in NY_EAST for x in ends):
        t += p["panynj_crossing_cents"]                   # one eastbound Hudson crossing per round trip
    if any(x.code == "manhattan" for x in ends):
        t += p["cbd_net_cents"]
    t += 2 * p["mta_bridge_cents"] * max(x.mta for x in ends)
    if any(x.state == "PA" for x in ends):
        t += p["delaware_bridge_cents"]
    t += max(0.0, total_miles - 20) * p["nj_toll_cents_per_mile"]
    return round(t)


def _price(cat: Catalog, committed_min: float, miles: float, extras_cents: float) -> int:
    p = cat.params
    cost = (committed_min / 60 * p["target_hourly_cents"] + miles * p["running_cents_per_mile"]
            + extras_cents + p["fixed_cents_per_trip"])
    gross = (cost + p["card_fee_fixed_cents"]) / (1 - p["card_fee_rate"])
    return int(max(p["min_fare_cents"], math.ceil(gross / 500) * 500))


def transfer(cat: Catalog, origin: Place, dest: Place) -> Estimate:
    p = cat.params
    base = cat.base
    app_mi, app_min = _leg(cat, base, origin, origin.crossing_min * 0.5)
    load_mi, load_min = _leg(cat, origin, dest, max(origin.crossing_min, dest.crossing_min))
    ret_mi, ret_min = _leg(cat, dest, base, dest.crossing_min * 0.5)
    wait = p["airport_wait_min"] if origin.is_airport else p["early_arrival_min"]
    parking = p["airport_parking_cents"] if origin.is_airport else 0
    committed = (max(p["min_approach_min"], app_min) + wait + load_min * p["traffic_allowance"]
                 + p["curbside_min"] + ret_min * p["return_traffic_allowance"])
    miles = app_mi + load_mi + ret_mi
    tolls = tolls_cents(cat, origin, dest, miles)
    return Estimate(cents=_price(cat, committed, miles, tolls + parking), loaded_minutes=round(load_min),
                    committed_minutes=round(committed), miles=round(miles), tolls_cents=tolls)


def hourly(cat: Catalog, hours: float) -> int:
    p = cat.params
    return int(round(max(p["hourly_min_hours"], hours) * p["hourly_cents"]))


def approach_minutes(cat: Catalog, place: Place) -> float:
    return max(cat.params["min_approach_min"], _leg(cat, cat.base, place, place.crossing_min * 0.5)[1])


def return_minutes(cat: Catalog, place: Place) -> float:
    return _leg(cat, place, cat.base, place.crossing_min * 0.5)[1]


def introductory(cat: Catalog, list_cents: int, now: datetime) -> tuple[int, dict | None]:
    """Apply the time-boxed launch offer, if active, to a list price. Returns (amount, offer)."""
    offer = cat.params.get("introductory") or {}
    if not offer.get("active"):
        return list_cents, None
    ends = datetime.strptime(offer["ends_local"], "%Y-%m-%dT%H:%M").replace(tzinfo=LOCAL_TZ)
    if now > ends:
        return list_cents, None
    amount = int(list_cents * (100 - offer["percent_off"]) / 100) // 100 * 100   # whole dollars
    return amount, {"label": offer["label"], "percent_off": offer["percent_off"], "ends": ends.isoformat()}
