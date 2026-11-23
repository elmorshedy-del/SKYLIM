"""Pricing — one implementation shared by live quotes, the website and tools/rate_model.py.

A journey's regular price keeps the same gap to Uber Black SUV in every county (app/domain/uber.py,
PRICING["uber_anchor"]): where Uber publishes the route, its Black SUV benchmark + premium; elsewhere a base
plus a rate per road mile fitted to those anchors, times the county's own Uber factor. All-in, the same in
either direction. Long journeys never cost more than the round trip at the hourly rate. A cost floor (the
journey and the drive back at a minimum rate per committed hour + running cost + tolls + fixed share, grossed
up for card fees) guarantees a journey is never sold below what it costs. Hourly service is a published
all-inclusive rate with a minimum.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
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
    road_miles: float = 0.0    # the client's journey, as priced
    rule: str = "cost"         # what set the price: uber | formula | by_time | cost_floor | min_fare
    cost_cents: int = 0        # the cost floor for this journey


def _leg(cat: Catalog, a: Place, b: Place, crossing: float = 0) -> tuple[float, float]:
    return geo.leg(a.point, b.point, cat.params, crossing)


def price_reference(cat: Catalog) -> Place:
    """Where the car is assumed to come from and return to when a journey is priced.

    data.PRICING["price_reference"] (Midtown): the city's cars sit there, and with back-to-back trips ours
    often will too — so the price never depends on where the owner happens to garage the car. Scheduling
    still uses the real home base (data.OPERATIONS["home_base"]).
    """
    code = cat.params.get("price_reference")
    return cat.places[code] if code else cat.base


def tolls_cents(cat: Catalog, origin: Place, dest: Place, total_miles: float) -> int:
    """Round-trip toll estimate for reference -> origin -> destination -> reference."""
    p = cat.params
    ends = (origin, dest)
    loop = (price_reference(cat), origin, dest)
    t = 0.0
    if any(x.state == "NJ" for x in loop) and any(x.state in NY_EAST for x in loop):
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
    """What one direction costs in committed vehicle time, from and back to the price reference."""
    p = cat.params
    base = price_reference(cat)
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


def road_miles(cat: Catalog, a: Place, b: Place) -> float:
    """Driving distance of the client's journey: the benchmark's published route distance where one is
    recorded (PRICING["road_miles"]), otherwise straight line x a road factor fitted on published routes
    (short urban trips wind more than long highway runs)."""
    if a.code == b.code:
        return 0.0
    p = cat.params
    known = p.get("road_miles", {})
    for key in ((a.code, b.code), (b.code, a.code)):
        if key in known:
            return float(known[key])
    # places whose roads north all funnel through one corridor (the Jersey Shore around Raritan Bay)
    via = p.get("road_via", {})
    for here, there in ((a, b), (b, a)):
        if here.code in via and there.lat > via[here.code][0]:
            w = tuple(via[here.code])
            return _road(p, here.point, w) + _road(p, w, there.point)
    return _road(p, a.point, b.point)


def _road(p, x: tuple[float, float], y: tuple[float, float]) -> float:
    s = geo.haversine_mi(x, y)
    return s * (p["road_factor"] + p["road_factor_near"] * math.exp(-s / p["road_factor_scale_mi"]))


def _round5(cents: float) -> int:
    return int(math.floor(cents / 500 + 0.5) * 500)


def uber_anchor_cents(cat: Catalog, a: Place, b: Place) -> int | None:
    """Our price where Uber publishes the route: its Black SUV benchmark (both directions, tip added) plus
    our premium (PRICING["uber_anchor"]["premium"]), rounded to $5. None where Uber publishes nothing."""
    bench = cat.uber
    if bench is None or (a.code, b.code) not in bench.anchors:
        return None
    return _round5(bench.anchors[(a.code, b.code)] * 100 * (1 + cat.params["uber_anchor"]["premium"]))


def formula_cents(cat: Catalog, a: Place, b: Place, miles: float) -> float:
    """The tariff fitted to the Uber anchors (base + per road mile), for routes Uber does not publish."""
    t = cat.params["tariff"]
    return t["base_cents"] + t["per_mile_cents"] * miles


def county_factors(cat: Catalog) -> dict[str, float]:
    """For each county with Uber-anchored routes, how far its anchored prices sit from the formula (mean
    ratio). Its other routes (e.g. to LaGuardia) use the same factor, so a county is priced consistently."""
    ratios: dict[str, list[float]] = {}
    for (x, y) in cat.uber.anchors if cat.uber else ():
        for county, other in ((x, y), (y, x)):
            if cat.places[county].kind == "area":
                a, b = cat.places[county], cat.places[other]
                ratios.setdefault(county, []).append(uber_anchor_cents(cat, a, b)
                                                     / formula_cents(cat, a, b, road_miles(cat, a, b)))
    return {c: sum(r) / len(r) for c, r in ratios.items()}


def round_trip_cost(cat: Catalog, a: Place, b: Place) -> int:
    """The cost floor: the journey and the empty drive back (or on to the next pickup), at the target rate
    per committed hour + running cost + tolls + fixed share, grossed up for card fees. Waiting and parking
    at an airport pickup are shared between the two directions, as the price is."""
    p = cat.params
    miles = road_miles(cat, a, b)
    loaded = _leg(cat, a, b, max(a.crossing_min, b.crossing_min))[1]
    wait = sum(p["airport_wait_min"] if x.is_airport else p["early_arrival_min"] for x in (a, b)) / 2
    parking = sum(p["airport_parking_cents"] for x in (a, b) if x.is_airport) / 2
    committed = wait + loaded * p["traffic_allowance"] + p["curbside_min"] + loaded * p["return_traffic_allowance"]
    rate = dict(p, target_hourly_cents=p.get("floor_hourly_cents", p["target_hourly_cents"]))
    return _price(replace(cat, params=rate), committed, 2 * miles, tolls_cents(cat, a, b, 2 * miles) + parking)


def market_price(cat: Catalog, a: Place, b: Place, cost_cents: int) -> tuple[int, str, float]:
    """(regular price in cents, the rule that set it, road miles) for a journey between two places."""
    p, t = cat.params, cat.params["tariff"]
    miles = road_miles(cat, a, b)
    anchored = uber_anchor_cents(cat, a, b)
    if anchored is not None:
        rule, cents = "uber", anchored
    else:
        factors = [cat.county_factor[x.code] for x in (a, b) if x.code in cat.county_factor]
        factor = sum(factors) / len(factors) if factors else 1.0
        candidates = {"formula": formula_cents(cat, a, b, miles) * factor}
        # long journeys: the round trip at the hourly rate (the market prices distance work by time)
        loaded = _leg(cat, a, b, max(a.crossing_min, b.crossing_min))[1]
        candidates["by_time"] = (p["hourly_cents"] * (2 * loaded + t["turnaround_min"]) / 60
                                 + tolls_cents(cat, a, b, 2 * miles))
        rule = min(candidates, key=candidates.get)
        cents = _round5(candidates[rule])
    if cents < cost_cents:
        rule, cents = "cost_floor", cost_cents
    if cents < p["min_fare_cents"]:
        rule, cents = "min_fare", int(p["min_fare_cents"])
    return cents, rule, miles


def journey(cat: Catalog, a: Place, b: Place) -> Estimate:
    """The price of a journey between two places — the same in either direction, as the market quotes
    airport transfers. Committed time, miles and tolls average both directions (an airport pickup's waiting
    time and parking are shared with the drop-off); the price follows market_price."""
    there, back = transfer(cat, a, b), transfer(cat, b, a)
    cost = round_trip_cost(cat, a, b)
    cents, rule, miles = market_price(cat, a, b, cost)
    return Estimate(cents=cents, loaded_minutes=there.loaded_minutes,
                    committed_minutes=round((there.committed_minutes + back.committed_minutes) / 2),
                    miles=round((there.miles + back.miles) / 2),
                    tolls_cents=round((there.tolls_cents + back.tolls_cents) / 2),
                    road_miles=round(miles, 1), rule=rule, cost_cents=cost)


def hourly(cat: Catalog, hours: float) -> int:
    p = cat.params
    return int(round(max(p["hourly_min_hours"], hours) * p["hourly_cents"]))


def approach_minutes(cat: Catalog, place: Place) -> float:
    return max(cat.params["min_approach_min"], _leg(cat, cat.base, place, place.crossing_min * 0.5)[1])


def return_minutes(cat: Catalog, place: Place) -> float:
    return _leg(cat, place, cat.base, place.crossing_min * 0.5)[1]


def drive_minutes(cat: Catalog, a: Place, b: Place) -> float:
    """Free-flow drive between two places (never less than the minimum repositioning time)."""
    return max(cat.params["min_approach_min"], _leg(cat, a, b, max(a.crossing_min, b.crossing_min))[1])


def introductory(cat: Catalog, list_cents: int, now: datetime) -> tuple[int, dict | None]:
    """Apply the time-boxed launch offer, if active, to a list price. Returns (amount, offer)."""
    offer = cat.params.get("introductory") or {}
    if not offer.get("active"):
        return list_cents, None
    ends = datetime.strptime(offer["ends_local"], "%Y-%m-%dT%H:%M").replace(tzinfo=LOCAL_TZ)
    if now > ends:
        return list_cents, None
    # rounded down to $5, so the discount is never less than the percentage shown
    amount = int(list_cents * (100 - offer["percent_off"]) / 100) // 500 * 500
    return amount, {"label": offer["label"], "percent_off": offer["percent_off"], "ends": ends.isoformat()}
