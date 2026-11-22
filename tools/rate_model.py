#!/usr/bin/env python3
"""Pricing proposal for owner review — generated from the same cost model that prices live quotes.

    python3 tools/rate_model.py            # print the proposal
    python3 tools/rate_model.py --write    # write pricing-proposal.md

Change inputs in data.PRICING; this tool and the website update together.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import data  # noqa: E402
from app.domain import rates  # noqa: E402
from app.domain.catalog import Catalog  # noqa: E402
from app.domain.pricing import route_class  # noqa: E402

AIRPORTS = ["ewr", "jfk", "lga", "teb"]


def money(c: int | None) -> str:
    return "custom" if c is None else f"${c / 100:,.0f}"


def proposal() -> str:
    cat = Catalog.from_module(data)
    p = cat.params
    limit = p["max_committed_min_for_instant_price"]

    def est(a: str, b: str):
        e = rates.journey(cat, cat.places[a], cat.places[b])
        return e, (None if e.committed_minutes > limit else e.cents)

    out = [
        "# Pricing proposal — for owner review (not yet approved)", "",
        f"Inputs (data.PRICING): **${p['target_hourly_cents'] / 100:.0f} per committed vehicle-hour**, running cost "
        f"**${p['running_cents_per_mile'] / 100:.2f}/mile**, fixed costs **${p['fixed_cents_per_trip'] / 100:.0f}/trip**, "
        f"card fee {p['card_fee_rate'] * 100:.1f}% + ${p['card_fee_fixed_cents'] / 100:.2f}, minimum fare "
        f"**${p['min_fare_cents'] / 100:.0f}**, repositioning priced from **{rates.price_reference(cat).name}**.", "",
        f"Hourly: **{money(p['hourly_cents'])}/hour all-inclusive**, {p['hourly_min_hours']}-hour minimum.", "",
        "Each direction's committed time = drive from the price reference to the pickup + waiting (45 min at an "
        "airport pickup, with parking) + the journey with a traffic allowance + curbside + the drive back. A "
        "journey's price is the average of both directions, so it costs the same either way — as the market "
        "quotes airport transfers. All prices include tolls, congestion charges and gratuity. Journeys committing "
        f"more than {limit / 60:.0f} hours are quoted individually.", "",
        "## Against the market", "",
        "| Journey | Ours | Competitor (all-in) | Difference | Source, checked |", "|---|---|---|---|---|",
    ]
    for bm in data.BENCHMARKS:
        if not bm.get("route"):
            continue
        a, b = bm["route"]
        ours = est(a, b)[1]
        diff = f"{(ours - bm['all_in_cents']) / bm['all_in_cents'] * 100:+.0f}%" if ours else "—"
        out.append(f"| {cat.places[a].short} ↔ {cat.places[b].short} | {money(ours)} | {bm['who']}: "
                   f"{money(bm['all_in_cents'])} | {diff} | {bm['source']}, {bm['checked']} |")
    hourly_bm = [bm for bm in data.BENCHMARKS if bm.get("unit") == "hour"]
    for bm in hourly_bm:
        out.append(f"| By the hour | {money(p['hourly_cents'])}/h | {bm['who']}: {money(bm['all_in_cents'])}/h | "
                   f"{(p['hourly_cents'] - bm['all_in_cents']) / bm['all_in_cents'] * 100:+.0f}% | {bm['source']}, "
                   f"{bm['checked']} |")
    out += [
        "",
        "## Popular journeys", "",
        "| Journey | Price | Vehicle committed | Route class |", "|---|---|---|---|",
    ]
    for a, b in data.POPULAR_JOURNEYS:
        e, c = est(a, b)
        out.append(f"| {cat.places[a].short} → {cat.places[b].short} | {money(c)} | "
                   f"{e.committed_minutes // 60}h{e.committed_minutes % 60:02d} | {route_class(cat, a, b)} |")
    out += ["", "## New Jersey counties to airports", "",
            "| County | " + " | ".join(cat.places[x].short for x in AIRPORTS) + " |",
            "|---|" + "---|" * len(AIRPORTS)]
    for pl in cat.places.values():
        if pl.state == "NJ" and pl.kind == "area":
            out.append(f"| {pl.name} | " + " | ".join(money(est(pl.code, x)[1]) for x in AIRPORTS) + " |")
    out += ["", "Which routes are booked online follows the operating authority (data.OPERATIONS['authority']); "
            "others are priced the same way but arranged personally."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    text = proposal()
    if "--write" in sys.argv:
        (ROOT / "pricing-proposal.md").write_text(text)
        print("pricing-proposal.md written")
    else:
        print(text)
