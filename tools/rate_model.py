#!/usr/bin/env python3
"""Pricing plan for owner review — generated from the same code that prices live quotes and the website.

    python3 tools/rate_model.py            # print the plan
    python3 tools/rate_model.py --write    # write pricing-proposal.md

Change inputs in data.PRICING (rates) and data.BENCHMARKS (competitor evidence); this plan, the website and
live quotes update together. tests/test_pricing_benchmark.py fails if prices drift from the benchmark.
"""
from __future__ import annotations

import datetime as dt
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import data  # noqa: E402
from app.config import LOCAL_TZ  # noqa: E402
from app.domain import rates  # noqa: E402
from app.domain.catalog import Catalog  # noqa: E402

CITY = ["manhattan", "jfk", "lga"]
REGIONS = [("New Jersey", "New Jersey"), ("Long Island", "Long Island"),
           ("Westchester & Hudson Valley", "Westchester & Hudson Valley"), ("Connecticut", "Connecticut")]
RULES = {"tariff": "", "by_time": "†", "cost_floor": "‡", "min_fare": "§"}


def money(c: int | None) -> str:
    return "on request" if c is None else f"${c / 100:,.0f}"


def pct(a: int, b: int) -> str:
    return f"{(a - b) / b * 100:+.0f}%"


def plan() -> str:
    cat = Catalog.from_module(data)
    p, t = cat.params, cat.params["tariff"]
    places = cat.places
    limit = p["max_committed_min_for_instant_price"]
    offer = p["introductory"]
    during = dt.datetime(2026, 12, 1, 12, tzinfo=LOCAL_TZ)
    ends = dt.datetime.strptime(offer["ends_local"], "%Y-%m-%dT%H:%M")
    known = {frozenset(k) for k in p.get("road_miles", {})}

    def est(a: str, b: str):
        e = rates.journey(cat, places[a], places[b])
        return e, (None if e.committed_minutes > limit else e.cents)

    def intro(c: int | None) -> int | None:
        return None if c is None else rates.introductory(cat, c, during)[0]

    def name(code: str) -> str:
        return places[code].short

    anchors = [bm for bm in data.BENCHMARKS if bm["role"] == "anchor" and bm["route"]]
    gaps = [(est(*bm["route"])[0].cents - bm["all_in_cents"]) / bm["all_in_cents"] for bm in anchors]
    hourly_anchor = next(bm for bm in data.BENCHMARKS if bm.get("unit") == "hour" and bm["role"] == "anchor")

    status = ("**Approved** — prices are firm." if p["approved"] else
              "**Awaiting owner approval** — the site shows prices as estimates until `PRICING['approved']` is True.")
    out = [
        "# Pricing plan — Celeste Luxury Limo", "",
        f"Version `{p['version']}`. {status}", "",
        "## 1. How every price is set — one rule for every county", "",
        "**The benchmark.** Detailed Drivers publishes all-in prices (20% gratuity, tolls and tax included) for "
        "its Cadillac Escalade ESV class across Manhattan, Long Island, Westchester, Connecticut and New Jersey, "
        f"with the road miles of each route. Their {t['fitted_on_routes']} published journeys follow one line, "
        f"each within ±5%: **${t['base_cents'] / 100:.0f} + ${t['per_mile_cents'] / 100:.2f} per road mile** "
        f"({len(anchors)} of them are journeys we serve and are compared one by one in section 2). On the Manhattan "
        "airport routes that line sits with NYC Lux Ride's Escalade ESV and below Gotham Ride, so it is the "
        "market's Escalade price, measured the same way in every region.", "",
        "**Our regular price follows the same line**, so every county is priced exactly as the market prices "
        "an Escalade there:", "",
        f"1. **Regular price = ${t['base_cents'] / 100:.0f} + ${t['per_mile_cents'] / 100:.2f} × road miles** "
        "of the client's journey, rounded to the nearest $5. All-in: tolls, congestion charges and gratuity "
        "included. The same price in either direction.",
        f"2. **Long journeys:** if lower, the round trip at the hourly rate (${p['hourly_cents'] / 100:.0f}/h, "
        f"also the benchmark's hourly rate) + {t['turnaround_min']} minutes' turnaround + tolls — the market "
        "prices distance work by time. Marked † below.",
        f"3. **Never below cost:** committed vehicle time × ${p['target_hourly_cents'] / 100:.0f}/h + running "
        f"cost ${p['running_cents_per_mile'] / 100:.2f}/mile + tolls + fixed costs + card fees. Marked ‡ below "
        "(airport-to-suburb journeys where the car's empty drives make the trip longer than its miles).",
        "4. **Road miles:** the benchmark's published distance where it has one (marked *); otherwise "
        f"estimated from the map — straight line × a road factor fitted on the benchmark's {t['fitted_on_routes']} "
        "published routes (city trips wind more than highway runs). Jersey Shore counties are measured through the "
        "Parkway/Turnpike corridor at Woodbridge, the only way north around Raritan Bay. Each county is "
        "priced from one point where most trips start; tell me a real distance and it replaces the estimate.",
        f"5. **Hourly:** {money(p['hourly_cents'])}/hour all-in, {p['hourly_min_hours']}-hour minimum "
        f"(benchmark: {money(hourly_anchor['all_in_cents'])}/hour).",
        f"6. **{offer['label']}:** {offer['percent_off']}% off every regular price (rounded down to $5, so "
        f"never less than {offer['percent_off']}%) until {ends:%B %-d, %Y}. Then the regular price applies "
        "and must be kept for at least 30 days (NYC rule 6 RCNY § 5-95). "
        + ("Active." if offer["active"] else "Not active."), "",
        f"**Fit to the benchmark:** across its {len(anchors)} published journeys our regular price is within "
        f"{min(gaps) * 100:+.0f}% to {max(gaps) * 100:+.0f}% (median {statistics.median(gaps) * 100:+.0f}%). "
        "Journeys committing the vehicle for more than "
        f"{limit / 60:.0f} hours are quoted individually.", "",
        "## 2. Against the benchmark, journey by journey", "",
        "| Journey | Benchmark quotes for | Road miles | Benchmark (all-in) | Our regular price | Gap | "
        f"{offer['label']} |", "|---|---|---|---|---|---|---|",
    ]
    for bm in anchors:
        a, b = bm["route"]
        e, c = est(a, b)
        miles = f"{bm['miles']:g}" if bm.get("miles") else f"~{e.road_miles:.0f} (est.)"
        out.append(f"| {name(a)} ↔ {name(b)} | {bm.get('at', '')} | {miles} | {money(bm['all_in_cents'])} | "
                   f"{money(c)}{RULES[e.rule]} | {pct(e.cents, bm['all_in_cents'])} | {money(intro(c))} |")

    out += ["", "## 3. Where we sit against other competitors on the same journeys", "",
            "All-in = what the client pays door to door: fare + tolls + fees + a 20% gratuity where the operator "
            "does not include one.", "",
            "| Journey | Competitor | Their all-in | Our regular price | Gap | Source, checked |",
            "|---|---|---|---|---|---|"]
    for bm in data.BENCHMARKS:
        if bm["role"] != "check" or not bm["route"]:
            continue
        a, b = bm["route"]
        e, c = est(a, b)
        theirs = money(bm["all_in_cents"]) + (f" {bm['plus']}" if bm.get("plus") else "")
        at = f" ({bm['at']})" if bm.get("at") else ""
        gap = pct(e.cents, bm["all_in_cents"]) + (" before their extras" if bm.get("plus") else "")
        out.append(f"| {name(a)}{at} ↔ {name(b)} | {bm['who']} | {theirs} | {money(c)} | {gap} | "
                   f"{bm['source']}, {bm['checked']} |")
    for bm in data.BENCHMARKS:
        if bm.get("unit") == "hour":
            out.append(f"| By the hour | {bm['who']} | {money(bm['all_in_cents'])}/h | {money(p['hourly_cents'])}/h"
                       f" | {pct(p['hourly_cents'], bm['all_in_cents'])} | {bm['source']}, {bm['checked']} |")

    out += ["", "## 4. Every commuter county to and from the city", "",
            f"Regular price, with the {offer['label'].lower()} in brackets. The same price in either direction; "
            "all of these book online (the TLC licence covers trips into New York City and pickups in it). "
            "Miles are road miles to Manhattan (Midtown).", ""]
    for group, title in REGIONS:
        out += [f"### {title}", "", "| County | Miles to Manhattan | Manhattan | JFK | LaGuardia |",
                "|---|---|---|---|---|"]
        for pl in places.values():
            if pl.kind != "area" or pl.group != group:
                continue
            cells = []
            for d in CITY:
                e, c = est(pl.code, d)
                mark = RULES[e.rule] + ("*" if frozenset((pl.code, d)) in known else "")
                cells.append(f"{money(c)}{mark} ({money(intro(c))})" if c else "on request")
            miles = rates.road_miles(cat, pl, places["manhattan"])
            out.append(f"| {pl.name} | {miles:.0f} | " + " | ".join(cells) + " |")
        out.append("")
    out += ["\\* distance published by the benchmark · † round trip by the hour · ‡ cost floor", ""]

    out += ["## 5. Airports and the city", "",
            "| Journey | Regular price | " + offer["label"] + " | Road miles | Vehicle committed |",
            "|---|---|---|---|---|"]
    for a, b in data.POPULAR_JOURNEYS:
        e, c = est(a, b)
        out.append(f"| {name(a)} → {name(b)} | {money(c)}{RULES[e.rule]} | {money(intro(c))} | "
                   f"{e.road_miles:.0f} | {e.committed_minutes // 60}h{e.committed_minutes % 60:02d} |")

    out += ["", "## 6. What it earns", "",
            "Committed time is everything the car is unavailable for: the drive out, waiting, the journey and "
            "the drive back. Card fees, tolls and running costs (fuel, tyres, servicing) come off first; what is "
            "left pays the chauffeur, the vehicle and the business.", "",
            "| Journey | Regular price | Committed | Per committed hour |", "|---|---|---|---|"]
    for a, b in data.POPULAR_JOURNEYS:
        e, c = est(a, b)
        if not c:
            continue
        net = c * (1 - p["card_fee_rate"]) - e.tolls_cents - e.miles * p["running_cents_per_mile"]
        out.append(f"| {name(a)} → {name(b)} | {money(c)} | {e.committed_minutes // 60}h"
                   f"{e.committed_minutes % 60:02d} | {money(int(net / (e.committed_minutes / 60)))} |")

    out += ["", "## 7. Keeping it current", "",
            "- Re-check the benchmark and competitors each quarter; update `data.BENCHMARKS`, run "
            "`python3 tools/rate_model.py --write`. The tests fail if any published benchmark journey drifts "
            "more than 7% from our price.",
            "- Raise prices once a year in January, by a small step tied to real costs (tolls, insurance, fuel), "
            "with 30 days' notice. Never change a booked trip.",
            "- No surge pricing. Busy days are handled by limited time slots, not price.", ""]
    return "\n".join(out)


if __name__ == "__main__":
    text = plan()
    if "--write" in sys.argv:
        (ROOT / "pricing-proposal.md").write_text(text)
        print("pricing-proposal.md written")
    else:
        print(text)
