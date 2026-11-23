#!/usr/bin/env python3
"""Pricing plan for owner review — generated from the same code that prices live quotes and the website.

    python3 tools/rate_model.py            # print the plan
    python3 tools/rate_model.py --write    # write pricing-proposal.md

Change inputs in data.PRICING (rules), benchmarks/uber_routes.json (Uber's published averages) and
data.BENCHMARKS / data.COMPETITOR_NOTES (chauffeur competitors); this plan, the website and live quotes update
together. tests/test_pricing_benchmark.py fails if any Uber-published route leaves the gap.
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
REGIONS = ["New Jersey", "Long Island", "Westchester & Hudson Valley", "Connecticut"]
MARK = {"uber": "*", "formula": "", "by_time": "†", "cost_floor": "‡", "min_fare": "§"}


def money(c: int | float | None) -> str:
    return "on request" if c is None else f"${c / 100:,.0f}"


def pct(a: float, b: float) -> str:
    return f"{(a - b) / b * 100:+.0f}%"


def plan() -> str:
    cat = Catalog.from_module(data)
    p, t, ua = cat.params, cat.params["tariff"], cat.params["uber_anchor"]
    bench, places = cat.uber, cat.places
    limit = p["max_committed_min_for_instant_price"]
    offer = p["introductory"]
    during = dt.datetime(2026, 12, 1, 12, tzinfo=LOCAL_TZ)
    ends = dt.datetime.strptime(offer["ends_local"], "%Y-%m-%dT%H:%M")
    prem = ua["premium"] * 100
    suburb = ua.get("side") == "suburb"

    def est(a: str, b: str):
        e = rates.journey(cat, places[a], places[b])
        return e, (None if e.committed_minutes > limit else e.cents)

    def intro(c):
        return None if c is None else rates.introductory(cat, c, during)[0]

    def name(code: str) -> str:
        return places[code].short

    pairs = sorted({tuple(sorted(k)) for k in bench.anchors}, key=lambda k: (places[k[0]].group, k))
    gaps = []
    for a, b in pairs:
        e, _ = est(a, b)
        gaps.append(e.cents / (bench.anchors[(a, b)] * 100) - 1)
    rows = {(r["from"], r["to"]): r for r in bench.rows}
    pr_out, pr_back = rows.get(("princeton-nj", "jfk")), rows.get(("jfk", "princeton-nj"))

    status = ("**Approved** — prices are firm." if p["approved"] else
              "**Awaiting owner approval** — the site shows prices as estimates until `PRICING['approved']` is True.")
    out = [
        "# Pricing plan — Celeste Luxury Limo", "",
        f"Version `{p['version']}`. {status}", "",
        "## 1. How every price is set — the same gap to Uber Black SUV in every county", "",
        f"**The anchor is Uber Black SUV.** Uber publishes, for popular routes, the average price of each ride "
        f"option over the past month (checked {bench.checked}; {len(bench.rows)} route-directions with prices, "
        "file `benchmarks/uber_routes.json`). Uber's prices are not the same in both directions: a trip that "
        f"starts in New York City costs about **{bench.nyc_origin_factor:.2f}×** the same trip starting in the "
        "suburbs (NYC rates and airport fees), and from most suburbs Uber shows no Black SUV at all.", "",
        (f"1. **Where Uber publishes the route: our price = the Uber Black SUV price for the trip starting "
         f"outside New York City — what a client sees in the app when booking from home — plus a "
         f"{ua['tip'] * 100:.0f}% tip (ours includes gratuity), plus {prem:.0f}%.** From the airport or Manhattan "
         f"side Uber charges about {bench.nyc_origin_factor:.2f}× more, so there we sit well under it. "
         if suburb else
         f"1. **Where Uber publishes the route: our price = Uber Black SUV averaged over both directions, plus "
         f"a {ua['tip'] * 100:.0f}% tip (ours includes gratuity), plus {prem:.0f}%.** ")
        + f"Where Uber shows no Black SUV price it uses the average route price × {bench.suv_per_route_avg:.2f} "
        "(Black SUV ÷ average on the routes that show both); a direction Uber does not publish is inferred from "
        "the other with the NYC-origin ratio. Routes between Manhattan and the airports use Uber's own figures "
        "both ways. Marked * below.",
        f"2. **Where Uber publishes nothing:** ${t['base_cents'] / 100:.0f} + ${t['per_mile_cents'] / 100:.2f} "
        "per road mile — the line fitted to all the Uber-anchored routes — times the county's own Uber factor "
        "where it has anchored routes (so its LaGuardia price matches its JFK and Manhattan prices).",
        f"3. **Long journeys:** never more than the round trip at the hourly rate (${p['hourly_cents'] / 100:.0f}/h) "
        f"+ {t['turnaround_min']} minutes' turnaround + tolls. Marked †.",
        f"4. **Never below cost:** the journey plus the empty drive back at "
        f"${p['floor_hourly_cents'] / 100:.0f} per committed hour + running cost + tolls + fixed costs + card "
        "fees. Marked ‡ (it lifts a short airport hop above the gap where Uber's suburban fares are very low).",
        f"5. **Hourly:** {money(p['hourly_cents'])}/hour all-in, {p['hourly_min_hours']}-hour minimum.",
        f"6. **{offer['label']}:** {offer['percent_off']}% off every regular price (rounded down to $5) until "
        f"{ends:%B %-d, %Y}; then the regular price for at least 30 days (NYC rule 6 RCNY § 5-95). "
        + ("Active." if offer["active"] else "Not active."), "",
        f"**Result:** on the {len(pairs)} routes Uber publishes, our regular price is "
        f"{min(gaps) * 100:+.0f}% to {max(gaps) * 100:+.0f}% from Uber Black SUV with tip "
        f"(median {statistics.median(gaps) * 100:+.0f}%). All prices are one fixed price, all-in, the same "
        f"either way. Journeys committing the vehicle for more than {limit / 60:.0f} hours are quoted individually.", "",
    ]
    if pr_out and pr_back:
        e, c = est("mercer", "jfk")
        out += [
            "**Why the gap to Uber looks different depending on where you stand — Princeton ↔ JFK:** Uber's "
            f"average UberX is ${pr_out['uberx']} from Princeton but ${pr_back['uberx']} from JFK. From Princeton "
            "Uber shows no Black SUV, only sedans (Premier ≈ $300 in the app, ≈ $360 with tip); from JFK the "
            f"Black SUV equivalent is ≈ {money(pr_back['route_avg'] * bench.suv_per_route_avg * 120)} with tip. "
            f"Our price is {money(c)} ({money(intro(c))} introductory) in either direction: "
            f"{pct(c, bench.anchors[('mercer', 'jfk')] * 100)} against Uber's Black SUV equivalent from Princeton "
            f"(≈ {money(bench.anchors[('mercer', 'jfk')] * 100)} with tip) and "
            f"{pct(c, pr_back['route_avg'] * bench.suv_per_route_avg * 120)} against it from JFK.", "",
        ]
    out += ["## 2. Against Uber Black SUV, route by route", "",
            "| Journey | Uber data | Uber Black SUV + tip" + (" (trip from the suburb)" if suburb else " (both ways averaged)")
            + " | Our regular price | Gap | "
            f"{offer['label']} |", "|---|---|---|---|---|---|"]
    for a, b in pairs:
        e, c = est(a, b)
        u = bench.anchors[(a, b)] * 100
        out.append(f"| {name(a)} ↔ {name(b)} | {bench.basis[(a, b)]} | {money(u)} | {money(c)}{MARK[e.rule]} | "
                   f"{pct(e.cents, u)} | {money(intro(c))} |")

    out += ["", "## 3. Against chauffeur services on the same journeys", "",
            "All-in = what the client pays door to door: fare + tolls + fees + a 20% gratuity where the operator "
            "does not include one.", "",
            "| Journey | Competitor | Their all-in | Our regular price | Gap | Source, checked |",
            "|---|---|---|---|---|---|"]
    for bm in data.BENCHMARKS:
        if not bm["route"]:
            continue
        a, b = bm["route"]
        e, c = est(a, b)
        theirs = money(bm["all_in_cents"]) + (f" {bm['plus']}" if bm.get("plus") else "")
        at = f" ({bm['at']})" if bm.get("at") else ""
        out.append(f"| {name(a)} ↔ {name(b)}{at} | {bm['who']} | {theirs} | {money(c)} | "
                   f"{pct(e.cents, bm['all_in_cents'])} | {bm['source']}, {bm['checked']} |")
    for bm in data.BENCHMARKS:
        if bm.get("unit") == "hour":
            out.append(f"| By the hour | {bm['who']} | {money(bm['all_in_cents'])}/h | {money(p['hourly_cents'])}/h"
                       f" | {pct(p['hourly_cents'], bm['all_in_cents'])} | {bm['source']}, {bm['checked']} |")
    out += ["", "**Competitors that publish no prices** (quote or account only):", ""]
    out += [f"- **{n['who']}** — {n['how']} ({n['source']})" for n in data.COMPETITOR_NOTES]
    out += ["", "Both bill the vehicle's time from and back to their garage and add surcharges, fees, tolls and "
            "(for EmpireCLS) gratuity on top, so on suburban journeys they price above an all-in fixed fare.", ""]

    out += ["## 4. Every commuter county to and from the city", "",
            f"Regular price, with the {offer['label'].lower()} in brackets. The same price in either direction; "
            "all of these book online (the TLC licence covers trips into New York City and pickups in it). "
            "Miles are road miles to Manhattan (Midtown).", ""]
    for group in REGIONS:
        out += [f"### {group}", "", "| County | Miles to Manhattan | Manhattan | JFK | LaGuardia |",
                "|---|---|---|---|---|"]
        for pl in places.values():
            if pl.kind != "area" or pl.group != group:
                continue
            cells = []
            for d in CITY:
                e, c = est(pl.code, d)
                cells.append(f"{money(c)}{MARK[e.rule]} ({money(intro(c))})" if c else "on request")
            out.append(f"| {pl.name} | {rates.road_miles(cat, pl, places['manhattan']):.0f} | " + " | ".join(cells) + " |")
        out.append("")
    out += ["\\* Uber Black SUV + " + f"{prem:.0f}% (Uber publishes this route) · no mark: formula fitted to Uber × "
            "county factor · † round trip by the hour · ‡ cost floor", ""]

    out += ["## 5. Airports and the city", "",
            "| Journey | Regular price | " + offer["label"] + " | Road miles | Vehicle committed |",
            "|---|---|---|---|---|"]
    for a, b in data.POPULAR_JOURNEYS:
        e, c = est(a, b)
        out.append(f"| {name(a)} → {name(b)} | {money(c)}{MARK[e.rule]} | {money(intro(c))} | "
                   f"{e.road_miles:.0f} | {e.committed_minutes // 60}h{e.committed_minutes % 60:02d} |")

    out += ["", "## 6. What it earns", "",
            "Per hour of the car's time for the journey and the drive back, after card fees, tolls and running "
            "costs (fuel, tyres, servicing); what is left pays the chauffeur, the vehicle and the business.", "",
            "| Journey | Regular price | Round trip | Per hour |", "|---|---|---|---|"]
    for a, b in data.POPULAR_JOURNEYS + [("mercer", "jfk"), ("nassau", "jfk"), ("monmouth", "manhattan")]:
        e, c = est(a, b)
        if not c:
            continue
        A, B = places[a], places[b]
        loaded = rates._leg(cat, A, B, max(A.crossing_min, B.crossing_min))[1]
        hours = (loaded * (p["traffic_allowance"] + p["return_traffic_allowance"]) + 30) / 60
        net = c * (1 - p["card_fee_rate"]) - rates.tolls_cents(cat, A, B, 2 * e.road_miles) \
            - 2 * e.road_miles * p["running_cents_per_mile"]
        out.append(f"| {name(a)} → {name(b)} | {money(c)} | {hours:.1f}h | {money(net / hours)} |")

    out += ["", "## 7. Keeping it current", "",
            "- Each quarter, re-read Uber's route pages listed in `benchmarks/uber_routes.json` (both directions), "
            "update the file and run `python3 tools/rate_model.py --write`; prices follow automatically and the "
            "tests check every route keeps the gap.",
            "- Re-check the chauffeur competitors in `data.BENCHMARKS` at the same time.",
            "- Raise prices once a year in January, by a small step tied to real costs, with 30 days' notice. "
            "Never change a booked trip. No surge pricing.", ""]
    return "\n".join(out)


if __name__ == "__main__":
    text = plan()
    if "--write" in sys.argv:
        (ROOT / "pricing-proposal.md").write_text(text)
        print("pricing-proposal.md written")
    else:
        print(text)
