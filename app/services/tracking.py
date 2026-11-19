"""Location ingest and the views riders are allowed to see.

Privacy rules:
  * a report is stored only if the reporting phone's driver has a trip that is
    en route / arrived / in vehicle, and only fixes taken after En route
  * riders see the latest fix for their own active trip — never history,
    never before the trip starts, never after it ends
  * the shareable view carries status and position only: no names, phone
    numbers, addresses or itinerary
  * nothing is interpolated: the page shows the fix time and goes "stale"
    when reports stop
"""
from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from ..domain.status import ACTIVE_TRIP, LABELS, Status
from ..domain.tracking import Fix
from ..errors import Conflict, NotFound
from ..security import hash_device_id, new_token, token_hash

MAX_FUTURE_SKEW = timedelta(minutes=2)
SHARE_MAX_HOURS = 12


def ingest(conn: psycopg.Connection, fix: Fix, now: datetime) -> str:
    """Store a fix if, and only if, its tracker belongs to a trip in progress."""
    tracker = conn.execute("SELECT * FROM trackers WHERE device_hash = %s AND active",
                           (hash_device_id(fix.device_id),)).fetchone()
    if not tracker:
        return "unknown_device"
    conn.execute("UPDATE trackers SET last_seen_at = %s WHERE id = %s", (now, tracker["id"]))
    trip = conn.execute(
        """SELECT id, trip_started_at FROM bookings
           WHERE status IN ('en_route', 'arrived', 'in_vehicle')
             AND ((%(kind)s = 'phone' AND driver_id = %(driver)s)
               OR (%(kind)s = 'vehicle' AND vehicle_id = %(vehicle)s))
           ORDER BY pickup_at LIMIT 1""",
        {"kind": tracker["kind"], "driver": tracker["driver_id"], "vehicle": tracker["vehicle_id"]}).fetchone()
    if not trip:
        return "no_active_trip"          # discarded: off-trip location is never kept
    if fix.reported_at > now + MAX_FUTURE_SKEW:
        return "rejected_future"
    if trip["trip_started_at"] and fix.reported_at < trip["trip_started_at"] - timedelta(minutes=1):
        return "rejected_before_trip"
    conn.execute(
        """INSERT INTO positions (booking_id, tracker_id, lat, lon, accuracy_m, speed_mps, heading,
               reported_at, received_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (trip["id"], tracker["id"], fix.lat, fix.lon, fix.accuracy_m, fix.speed_mps, fix.heading,
         fix.reported_at, now))
    return "stored"


def position_view(conn: psycopg.Connection, booking: dict, now: datetime, stale_after_seconds: int) -> dict:
    status = Status(booking["status"])
    view = {"status": status.value, "status_label": LABELS[status], "available": False}
    if status not in ACTIVE_TRIP:
        return view
    p = conn.execute(
        """SELECT lat, lon, accuracy_m, heading, reported_at FROM positions
           WHERE booking_id = %s ORDER BY reported_at DESC LIMIT 1""", (booking["id"],)).fetchone()
    if not p:
        view["message"] = "Waiting for the first location report from your chauffeur's phone."
        return view
    age = max(0, int((now - p["reported_at"]).total_seconds()))
    view.update({
        "available": True, "lat": round(p["lat"], 5), "lon": round(p["lon"], 5),
        "accuracy_m": round(p["accuracy_m"]) if p["accuracy_m"] is not None else None,
        "heading": p["heading"], "reported_at": p["reported_at"].isoformat(), "age_seconds": age,
        "stale": age > stale_after_seconds,
    })
    if view["stale"]:
        view["message"] = ("No new location for a little while — the phone may be in a tunnel or out of "
                           "signal. This is the last known position, not a live one.")
    return view


# -------------------------------------------------------------------- share
def create_share(conn: psycopg.Connection, booking: dict, now: datetime, hours: int = 4) -> tuple[str, datetime]:
    """Opt-in, location-only link for someone meeting the rider. One live link per
    trip: creating a new one revokes the old. Ends with the trip regardless."""
    status = Status(booking["status"])
    if status not in ({Status.CONFIRMED} | ACTIVE_TRIP):
        raise Conflict("A location link can be shared once the trip is confirmed.", code="not_shareable")
    hours = max(1, min(SHARE_MAX_HOURS, hours))
    expires = max(now, booking["pickup_at"]) + timedelta(hours=hours)
    token = new_token()
    conn.execute("UPDATE bookings SET share_token_hash = %s, share_expires_at = %s, updated_at = %s WHERE id = %s",
                 (token_hash(token), expires, now, booking["id"]))
    return token, expires


def revoke_share(conn: psycopg.Connection, booking: dict, now: datetime) -> None:
    conn.execute("UPDATE bookings SET share_token_hash = NULL, share_expires_at = NULL, updated_at = %s "
                 "WHERE id = %s", (now, booking["id"]))


def share_view(conn: psycopg.Connection, share_token: str, now: datetime, stale_after_seconds: int) -> dict:
    b = conn.execute("SELECT * FROM bookings WHERE share_token_hash = %s", (token_hash(share_token),)).fetchone()
    if not b or not b["share_expires_at"] or b["share_expires_at"] <= now or \
            Status(b["status"]) not in ({Status.CONFIRMED} | ACTIVE_TRIP):
        raise NotFound("This shared link has ended.")
    v = position_view(conn, b, now, stale_after_seconds)
    allowed = {"status", "status_label", "available", "lat", "lon", "accuracy_m", "heading", "reported_at",
               "age_seconds", "stale", "message"}
    return {k: v[k] for k in allowed if k in v}


def purge(conn: psycopg.Connection, now: datetime, retention_hours: int) -> int:
    """Delete positions of finished trips past the retention window."""
    cur = conn.execute(
        """DELETE FROM positions p USING bookings b
           WHERE p.booking_id = b.id AND b.status NOT IN ('en_route', 'arrived', 'in_vehicle')
             AND COALESCE(b.completed_at, b.cancelled_at, b.updated_at) <= %s""",
        (now - timedelta(hours=max(0, retention_hours)),))
    return cur.rowcount
