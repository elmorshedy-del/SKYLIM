"""Prices follow the market benchmark consistently in every region (data.BENCHMARKS, data.PRICING)."""
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


def price(a: str, b: str) -> int:
    return rates.journey(CAT, P[a], P[b]).cents


def test_regular_price_tracks_the_benchmark_on_every_published_route():
    anchors = [bm for bm in data.BENCHMARKS if bm["role"] == "anchor" and bm["route"]]
    assert len(anchors) >= 15 and {P[c].group for bm in anchors for c in bm["route"]} >= {
        "Long Island", "Westchester & Hudson Valley", "Connecticut", "New Jersey", "New York City"}
    for bm in anchors:
        ours = price(*bm["route"])
        assert abs(ours / bm["all_in_cents"] - 1) <= 0.07, (bm["route"], ours, bm["all_in_cents"])


def test_the_tariff_is_base_plus_per_mile_rounded_to_5():
    t = CAT.params["tariff"]
    e = rates.journey(CAT, P["manhattan"], P["jfk"])
    assert e.rule == "tariff" and e.road_miles == 17.7
    assert e.cents == round((t["base_cents"] + t["per_mile_cents"] * 17.7) / 500) * 500
    assert all(price(c.code, d) % 500 == 0 for c in COUNTIES for d in NYC_ENDS)


def test_every_commuter_county_is_priced_to_and_from_the_city_the_same_both_ways():
    for c in COUNTIES:
        for d in NYC_ENDS:
            assert price(c.code, d) == price(d, c.code)
            # into the city and out of it are both covered by the TLC licence, so all of these book online
            assert route_class(CAT, c.code, d) == "into_nyc" and route_class(CAT, d, c.code) == "nyc_pickup"


def test_further_is_never_cheaper_within_a_region():
    """Within one corridor a county further out never costs less to reach Manhattan."""
    for chain in (["hudson", "essex", "morris", "sussex"], ["nassau", "suffolk", "hamptons"],
                  ["westchester", "putnam", "dutchess"], ["fairfield", "new-haven"], ["middlesex", "mercer"]):
        prices = [price(c, "manhattan") for c in chain]
        assert prices == sorted(prices), (chain, prices)


def test_long_journeys_are_capped_at_the_round_trip_by_the_hour():
    e = rates.journey(CAT, P["cape-may"], P["manhattan"])
    assert e.rule == "by_time"
    t = CAT.params["tariff"]
    assert e.cents < t["base_cents"] + t["per_mile_cents"] * e.road_miles


def test_jersey_shore_distances_go_around_the_bay():
    straight = geo.haversine_mi(P["monmouth"].point, P["jfk"].point)
    assert rates.road_miles(CAT, P["monmouth"], P["jfk"]) > 1.4 * straight


def test_never_below_cost():
    for c in COUNTIES:
        for d in NYC_ENDS:
            e = rates.journey(CAT, P[c.code], P[d])
            assert e.cents >= e.cost_cents


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
