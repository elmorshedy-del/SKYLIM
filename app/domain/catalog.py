"""Typed, validated view of data.py.

Business data is edited in data.py; this module turns it into immutable objects
once at startup and fails loudly on malformed entries, so a typo never reaches
a client as a wrong price.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from types import ModuleType
from typing import Mapping

KINDS = {"airport", "aviation", "city", "area"}
STATES = {"NJ", "NY", "PA", "CT"}


# Route classes, by who licenses the trip (see domain/pricing.route_class and data.OPERATIONS).
ROUTE_CLASSES = ("nyc_pickup", "into_nyc", "nj_intrastate", "interstate", "other_intrastate")

@dataclass(frozen=True)
class Place:
    code: str
    name: str
    short: str
    kind: str              # airport | aviation | city | area
    state: str             # NJ | NY | PA | CT
    group: str
    lat: float
    lon: float
    crossing_min: float = 0
    mta: int = 0           # MTA bridge/tunnel crossings each way from New Jersey
    towns: tuple[str, ...] = field(default_factory=tuple)
    region: str = ""
    nyc: bool = False      # inside New York City (the five boroughs, JFK, LaGuardia): TLC jurisdiction

    @property
    def point(self) -> tuple[float, float]:
        return (self.lat, self.lon)

    @property
    def is_airport(self) -> bool:
        return self.kind in ("airport", "aviation")


@dataclass(frozen=True)
class Catalog:
    places: Mapping[str, Place]
    params: Mapping[str, float]
    authority: Mapping[str, bool]
    vehicle: Mapping
    driver: Mapping
    policy: Mapping
    amenities: Mapping
    home_base: str
    pricing_approved: bool
    pricing_version: str

    @property
    def base(self) -> Place:
        return self.places[self.home_base]

    @classmethod
    def from_module(cls, mod: ModuleType) -> "Catalog":
        places: dict[str, Place] = {}
        for p in mod.PLACES:
            if p["code"] in places:
                raise ValueError(f"duplicate place code {p['code']!r}")
            if p["kind"] not in KINDS or p["state"] not in STATES:
                raise ValueError(f"place {p['code']!r} has bad kind/state")
            places[p["code"]] = Place(
                code=p["code"], name=p["name"], short=p["short"], kind=p["kind"], state=p["state"],
                group=p["group"], lat=float(p["lat"]), lon=float(p["lon"]),
                crossing_min=float(p.get("crossing_min", 0)), mta=int(p.get("mta", 0)),
                towns=tuple(p.get("towns", ())), region=p.get("region", ""), nyc=bool(p.get("nyc", False)))
        home = mod.OPERATIONS["home_base"]
        if home not in places:
            raise ValueError(f"OPERATIONS['home_base'] {home!r} is not a place code")
        for a, b in getattr(mod, "POPULAR_JOURNEYS", []):
            if a not in places or b not in places:
                raise ValueError(f"POPULAR_JOURNEYS has unknown place in {(a, b)!r}")
        unknown = set(mod.OPERATIONS["authority"]) - set(ROUTE_CLASSES)
        if unknown:
            raise ValueError(f"OPERATIONS['authority'] has unknown route classes: {sorted(unknown)}")
        pricing = dict(mod.PRICING)
        return cls(places=places, params=pricing, authority=dict(mod.OPERATIONS["authority"]),
                   vehicle=dict(mod.VEHICLE), driver=dict(mod.DRIVER), policy=dict(mod.POLICY),
                   amenities=dict(mod.AMENITIES), home_base=home,
                   pricing_approved=bool(pricing["approved"]), pricing_version=str(pricing["version"]))


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    import data
    return Catalog.from_module(data)
