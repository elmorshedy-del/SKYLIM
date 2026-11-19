"""Drive-time planning model shared by the server and tools/rate_model.py.

Straight-line distance x detour factor, a speed that rises with trip length
(local roads -> Parkway/Turnpike), plus a fixed crossing penalty for bridges,
tunnels and terminal loops. It is a planning estimate only; replace the inputs
with logged trip durations once real data exists.
"""
from __future__ import annotations

import math
from typing import Mapping

Point = tuple[float, float]


def haversine_mi(a: Point, b: Point) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def leg(a: Point, b: Point, params: Mapping[str, float], crossing_min: float = 0) -> tuple[float, float]:
    """Return (road miles, off-peak minutes) between two points."""
    miles = haversine_mi(a, b) * params["detour_factor"]
    mph = params["base_mph"] + min(params["max_extra_mph"], miles * params["mph_per_mile"])
    return miles, miles / mph * 60 + crossing_min
