"""Prices keep the same gap to Uber Black SUV in every county (benchmarks/uber_routes.json, data.PRICING)."""
from __future__ import annotations

from datetime import datetime

import data
from app.config import LOCAL_TZ
from app.domain import geo, rates
from app.domain.catalog import Catalog
from app.domain.pricing import route_class

CAT = Catalog.from_module(data)
P = CAT.places
COUNTIES = [p for p in P.values() if p.kind == "area"]
NYC_ENDS = ("manhattan", "jfk", "lga")
PREMIUM = CAT.params["uber_anchor"]["premium"]


def price(a: str, b: str) -> int:
    return rates.journey(CAT, P[a], P[b]).cents


def test_uber_benchmark_is_derived_from_the_published_file():
    bench = CAT.uber
    assert bench.checked and len(bench.rows) >= 50
    assert 1.5 < bench.suv_per_route_avg < 3 and 1.1 < bench.nyc_origin_factor < 2
    regions = {P[c].group for pair in bench.anchors for c in pair}
    assert {"New Jersey", "Long Island", "Westchester & Hudson Valley", "Connecticut"} <= regions


def test_same_gap_to_uber_black_suv_on_every_route_uber_publishes():
    at_gap = floors = 0
    for (a, b), uber_dollars in CAT.uber.anchors.items():
        e = rates.journey(CAT, P[a], P[b])
        gap = e.cents / (uber_dollars * 100) - 1
        if e.rule == "cost_floor":                 # the floor may lift a short hop above the gap, never below it
            floors += 1
            assert gap > PREMIUM
            continue
        assert e.rule == "uber" and abs(gap - PREMIUM) <= 0.02, (a, b, e.cents, uber_dollars)
        at_gap += 1
    assert at_gap >= 3 * floors


def test_routes_uber_does_not_publish_use_the_formula_fitted_to_uber():
    e = rates.journey(CAT, P["sussex"], P["manhattan"])
    assert e.rule in ("formula", "by_time")
    t = CAT.params["tariff"]
    assert e.cents <= round((t["base_cents"] + t["per_mile_cents"] * e.road_miles) / 500 + 1) * 500


def test_every_commuter_county_is_priced_to_and_from_the_city_the_same_both_ways():
    for c in COUNTIES:
        for d in NYC_ENDS:
            assert price(c.code, d) == price(d, c.code) and price(c.code, d) % 500 == 0
            # into the city and out of it are both covered by the TLC licence, so all of these book online
            assert route_class(CAT, c.code, d) == "into_nyc" and route_class(CAT, d, c.code) == "nyc_pickup"


def test_further_is_never_cheaper_within_a_region():
    """Within one corridor a county further out never costs less to reach Manhattan."""
    for chain in (["hudson", "essex", "morris", "sussex"], ["nassau", "suffolk", "hamptons"],
                  ["westchester", "putnam", "dutchess"], ["fairfield", "new-haven"], ["middlesex", "mercer"]):
        prices = [price(c, "manhattan") for c in chain]
        assert prices == sorted(prices), (chain, prices)


def test_long_journeys_never_cost_more_than_the_round_trip_by_the_hour():
    p, t = CAT.params, CAT.params["tariff"]
    for c in ("cape-may", "salem", "litchfield", "ulster", "hamptons"):
        a, b = P[c], P["manhattan"]
        e = rates.journey(CAT, a, b)
        loaded = rates._leg(CAT, a, b, max(a.crossing_min, b.crossing_min))[1]
        by_time = (p["hourly_cents"] * (2 * loaded + t["turnaround_min"]) / 60
                   + rates.tolls_cents(CAT, a, b, 2 * e.road_miles))
        assert e.cents <= round(by_time / 500 + 0.5) * 500 or e.rule == "cost_floor", (c, e.cents, by_time)


def test_jersey_shore_distances_go_around_the_bay():
    straight = geo.haversine_mi(P["monmouth"].point, P["jfk"].point)
    assert rates.road_miles(CAT, P["monmouth"], P["jfk"]) > 1.4 * straight


def test_never_below_the_round_trip_cost():
    for c in COUNTIES:
        for d in NYC_ENDS:
            e = rates.journey(CAT, P[c.code], P[d])
            assert e.cents >= e.cost_cents == rates.round_trip_cost(CAT, P[c.code], P[d])


def test_introductory_offer_is_at_least_its_percentage_and_ends():
    offer = CAT.params["introductory"]
    during = datetime(2026, 11, 26, 12, tzinfo=LOCAL_TZ)
    after = datetime(2027, 2, 1, 0, 1, tzinfo=LOCAL_TZ)
    for c in COUNTIES:
        list_cents = price(c.code, "manhattan")
        amount, shown = rates.introductory(CAT, list_cents, during)
        if offer["active"]:
            assert shown and amount <= list_cents * (100 - offer["percent_off"]) / 100 and amount % 500 == 0
        assert rates.introductory(CAT, list_cents, after) == (list_cents, None)
