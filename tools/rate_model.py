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
        e = rates.transfer(cat, cat.places[a], cat.places[b])
        return e, (None if e.committed_minutes > limit else e.cents)

    out = [
        "# Pricing proposal — for owner review (not yet approved)", "",
        f"Inputs (data.PRICING): **${p['target_hourly_cents'] / 100:.0f} per committed vehicle-hour**, running cost "
        f"**${p['running_cents_per_mile'] / 100:.2f}/mile**, fixed costs **${p['fixed_cents_per_trip'] / 100:.0f}/trip**, "
        f"card fee {p['card_fee_rate'] * 100:.1f}% + ${p['card_fee_fixed_cents'] / 100:.2f}, minimum fare "
        f"**${p['min_fare_cents'] / 100:.0f}**, home base **{cat.base.name}**.", "",
        f"Hourly: **{money(p['hourly_cents'])}/hour all-inclusive**, {p['hourly_min_hours']}-hour minimum.", "",
        "Committed time = drive to the pickup + waiting + the journey with a traffic allowance + curbside + "
        "the empty drive back to base. Journeys committing more than "
        f"{limit / 60:.0f} hours are quoted individually.", "",
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
    out += ["", "Trips wholly inside New York (e.g. Manhattan → JFK) are priced by the same model but are "
            "taken by request until NYC TLC affiliation or a partner is in place (OPERATIONS['authority'])."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    text = proposal()
    if "--write" in sys.argv:
        (ROOT / "pricing-proposal.md").write_text(text)
        print("pricing-proposal.md written")
    else:
        print(text)
