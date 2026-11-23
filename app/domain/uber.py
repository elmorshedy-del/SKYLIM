"""Uber Black SUV benchmark per route, from Uber's own published route averages (benchmarks/uber_routes.json).

Uber publishes, for popular routes, the average price of each ride option over the past month (tip not
included). Our price is one price in both directions; Uber's is not — a trip starting in New York City
costs ~1.5x the same trip starting in the suburbs (NYC rates, airport and congestion fees). So the
benchmark for a route is the Uber Black SUV price averaged over both directions, plus a 20% tip:

  * a direction's Black SUV average where Uber shows one; otherwise the direction's average route price x
    the Black SUV / average-route-price ratio measured on the routes that show both (median);
  * a direction Uber does not publish is inferred from the other with the measured NYC-origin / suburb-
    origin ratio (median over routes with both directions).

Everything is derived from the file at load time; nothing is typed in by hand except the file itself.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

NYC_ENDS = {"manhattan-ny", "jfk", "ewr", "lga"}


@dataclass(frozen=True)
class UberBenchmark:
    anchors: Mapping[tuple[str, str], float]   # (place, place) -> Black SUV all-in dollars, both orders
    basis: Mapping[tuple[str, str], str]       # "both directions" | "one direction" | source note
    suv_per_route_avg: float
    nyc_origin_factor: float
    tip: float
    checked: str
    source: str
    rows: tuple[dict, ...]


def load(path: Path, tip: float, exclude: set[tuple[str, str]], extra: list[dict],
         side: str = "average") -> UberBenchmark:
    """side: "average" — both directions averaged; "suburb" — the direction starting outside New York City
    (what a client sees in the app when booking from home), the cheaper side."""
    doc = json.loads(path.read_text())
    rows = [dict(zip(doc["columns"], r)) for r in doc["rows"]]
    town = doc["towns"]
    by = {(r["from"], r["to"]): r for r in rows}
    suv_ratio = statistics.median(r["black_suv"] / r["route_avg"] for r in rows if r["black_suv"] and r["route_avg"])
    pairs = [by[(b, a)]["route_avg"] / r["route_avg"] for (a, b), r in by.items()
             if a not in NYC_ENDS and (b, a) in by and r["route_avg"] and by[(b, a)]["route_avg"]]
    nyc_factor = statistics.median(pairs)

    def direction(a: str, b: str):
        r = by.get((a, b))
        if not r:
            return None
        return r["black_suv"] or (r["route_avg"] * suv_ratio if r["route_avg"] else None)

    anchors: dict[tuple[str, str], float] = {}
    basis: dict[tuple[str, str], str] = {}
    slugs = {s for pair in by for s in pair}
    for s in slugs:
        for d in ("manhattan-ny", "jfk", "ewr"):
            if s == d or (s in NYC_ENDS and d not in NYC_ENDS):
                continue
            out, back = direction(s, d), direction(d, s)
            if out is None and back is None:
                continue
            a, b = town[s], town[d]
            if (a, b) in exclude or (b, a) in exclude or (a, b) in anchors:
                continue
            both_nyc = s in NYC_ENDS and d in NYC_ENDS
            if side == "suburb" and not both_nyc:
                if out is not None:
                    value, how = out, "from the suburb"
                else:
                    value, how = back / nyc_factor, "from the suburb, inferred"
            elif out is not None and back is not None:
                value, how = (out + back) / 2, "both directions"
            else:
                known = out if out is not None else back
                if both_nyc:
                    other = known
                elif out is not None:                 # only the suburb-origin direction is published
                    other = known * nyc_factor
                else:                                 # only the NYC-origin direction is published
                    other = known / nyc_factor
                value, how = (known + other) / 2, "one direction"
            anchors[(a, b)] = anchors[(b, a)] = value * (1 + tip)
            basis[(a, b)] = basis[(b, a)] = how
    for e in extra:                                   # published elsewhere (e.g. Uber's own average via a third party)
        a, b = e["route"]
        anchors[(a, b)] = anchors[(b, a)] = e["black_suv"] * (1 + tip)
        basis[(a, b)] = basis[(b, a)] = e["source"]
    return UberBenchmark(anchors=anchors, basis=basis, suv_per_route_avg=suv_ratio, nyc_origin_factor=nyc_factor,
                         tip=tip, checked=doc["checked"], source=doc["source"], rows=tuple(rows))
