"""Parse location reports from the Traccar Client phone app.

Traccar Client speaks the OsmAnd protocol. Current releases POST form fields
(id, lat, lon, timestamp, speed in knots, bearing, accuracy, batt); older
releases POST JSON ({"device_id", "location": {"timestamp", "coords": {...}}}
with speed in m/s). Both are accepted. Point the app's server URL at
https://<domain>/api/tracking/osmand — no separate Traccar server is needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

KNOTS_TO_MPS = 0.514444


class BadReport(ValueError):
    pass


@dataclass(frozen=True)
class Fix:
    device_id: str
    lat: float
    lon: float
    reported_at: datetime
    accuracy_m: Optional[float] = None
    speed_mps: Optional[float] = None
    heading: Optional[float] = None


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def parse_timestamp(v: Any, now: datetime) -> datetime:
    if v in (None, ""):
        return now
    n = _num(v)
    if n is not None:
        return datetime.fromtimestamp(n / 1000 if n > 1e11 else n, tz=timezone.utc)
    s = str(v).strip().replace(" ", "T", 1)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        raise BadReport("unreadable timestamp")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_report(form: Mapping[str, Any], body: Optional[Mapping[str, Any]], now: datetime) -> Fix:
    if body and isinstance(body.get("location"), (dict, list)):
        loc = body["location"]
        if isinstance(loc, list):            # batched upload: the newest fix wins
            loc = loc[-1] if loc else {}
        coords = loc.get("coords") or loc
        device = body.get("device_id") or form.get("id") or form.get("deviceid")
        lat, lon = _num(coords.get("latitude")), _num(coords.get("longitude"))
        speed = _num(coords.get("speed"))
        heading = _num(coords.get("heading"))
        fix = dict(accuracy_m=_num(coords.get("accuracy")),
                   speed_mps=speed if speed is not None and speed >= 0 else None,
                   heading=heading if heading is not None and heading >= 0 else None)
        ts = loc.get("timestamp")
    else:
        device = form.get("id") or form.get("deviceid")
        if form.get("location") and not form.get("lat"):
            parts = str(form["location"]).split(",")
            lat, lon = (_num(parts[0]), _num(parts[1])) if len(parts) == 2 else (None, None)
        else:
            lat, lon = _num(form.get("lat")), _num(form.get("lon"))
        speed = _num(form.get("speed"))
        fix = dict(accuracy_m=_num(form.get("accuracy") or form.get("hacc")),
                   speed_mps=speed * KNOTS_TO_MPS if speed is not None else None,
                   heading=_num(form.get("bearing") or form.get("heading")))
        ts = form.get("timestamp")
    if not device:
        raise BadReport("missing device id")
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        raise BadReport("missing or invalid coordinates")
    return Fix(device_id=str(device), lat=lat, lon=lon, reported_at=parse_timestamp(ts, now), **fix)


def parse_traccar_forward(body: Mapping[str, Any], now: datetime) -> Fix:
    """Position forwarded by a Traccar server (forward.type=json) for an in-car
    tracker such as a Teltonika OBD unit: {"position": {...}, "device": {"uniqueId": ...}}.
    Speed arrives in knots; invalid (no GPS lock) fixes are rejected."""
    pos = body.get("position") or {}
    device = (body.get("device") or {}).get("uniqueId")
    if not device:
        raise BadReport("missing device uniqueId")
    if pos.get("valid") is False:
        raise BadReport("tracker reports no valid GPS fix")
    lat, lon = _num(pos.get("latitude")), _num(pos.get("longitude"))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        raise BadReport("missing or invalid coordinates")
    speed = _num(pos.get("speed"))
    return Fix(device_id=str(device), lat=lat, lon=lon,
               reported_at=parse_timestamp(pos.get("fixTime") or pos.get("deviceTime"), now),
               accuracy_m=_num(pos.get("accuracy")) or None,
               speed_mps=speed * KNOTS_TO_MPS if speed is not None else None,
               heading=_num(pos.get("course")))
