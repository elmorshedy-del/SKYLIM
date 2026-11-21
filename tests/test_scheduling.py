"""Back-to-back trips for a sole operator: drives from the previous drop-off, buffers for the unpredictable."""
from __future__ import annotations

from datetime import timedelta

from app.db import tx
from app.domain.catalog import get_catalog
from app.domain.pricing import TripRequest, leg_minutes
from app.services import availability
from tests.helpers import approve, quote, request
from tests.test_api import booking_body

DAY = "2026-11-24"          # an ordinary Tuesday (the 25th is configured as a heavy-traffic day)


def held(booking_id) -> dict:
    with tx() as conn:
        return conn.execute("SELECT * FROM reservations WHERE booking_id = %s", (booking_id,)).fetchone()


def job_after(cat, prev: dict, origin: str, destination: str, gap_minutes: float, minutes: int = 60):
    """A trip whose on-site time starts `gap_minutes` after the chauffeur could reach `origin`."""
    end = prev["during"].upper
    start = end + timedelta(minutes=leg_minutes(cat, prev["end_place"], origin, end) + gap_minutes)
    req = TripRequest(service="transfer", origin=origin, destination=destination, pickup_at=start, passengers=1,
                      large_bags=0)
    return availability.job_for(cat, req, start, start + timedelta(minutes=minutes))


def test_next_trip_starts_from_the_previous_drop_off(now, settings):
    b, _ = request(now, origin="manhattan", destination="jfk", pickup=f"{DAY}T10:00")
    approve(b["id"], now)
    prev, cat = held(b["id"]), get_catalog()
    assert (prev["start_place"], prev["end_place"], prev["risk"]) == ("manhattan", "jfk", "standard")
    with tx() as conn:
        # an hour after dropping at JFK, a JFK pickup fits — no drive back to base in between
        soon = job_after(cat, prev, "jfk", "manhattan", gap_minutes=45)
        assert availability.fit(conn, cat, soon, now, settings) == "available"
        # inside the 30-minute buffer: possible only if everything runs on time -> the owner decides
        close = job_after(cat, prev, "jfk", "manhattan", gap_minutes=10)
        assert availability.fit(conn, cat, close, now, settings) == "tight"
        # can't physically get there in time
        impossible = job_after(cat, prev, "jfk", "manhattan", gap_minutes=-5)
        assert availability.fit(conn, cat, impossible, now, settings) == "unavailable"


def test_airport_pickups_get_the_longer_buffer(now, settings):
    b, _ = request(now, origin="jfk", destination="manhattan", pickup=f"{DAY}T10:00")
    approve(b["id"], now)
    prev, cat = held(b["id"]), get_catalog()
    assert prev["risk"] == "airport_arrival"
    with tx() as conn:
        # 45 minutes of margin is enough after a normal trip, but not after a flight that may land late
        after_flight = job_after(cat, prev, "manhattan", "jfk", gap_minutes=45)
        assert availability.fit(conn, cat, after_flight, now, settings) == "tight"
        assert availability.fit(conn, cat, job_after(cat, prev, "manhattan", "jfk", gap_minutes=70), now,
                                settings) == "available"


def test_tight_time_is_a_request_never_an_instant_charge(client, now, settings, admin):
    b, _ = request(now, origin="manhattan", destination="jfk", pickup=f"{DAY}T10:00")
    approve(b["id"], now)
    slots = client.post("/api/slots", json={"origin": "jfk", "destination": "manhattan", "date": DAY}).json()["slots"]
    tight = [s for s in slots if s["mode"] == "request"]
    assert tight, "times inside the buffer are offered on request"
    assert any(s["mode"] == "instant" and s["pickup_local"] > tight[0]["pickup_local"] for s in slots)
    q = client.post("/api/quotes", json={"origin": "jfk", "destination": "manhattan", "pickup_local": tight[0]["pickup_local"],
                                         "passengers": 1, "large_bags": 0}).json()
    assert q["bookable"] and not q["instant"] and q["availability"] == "tight"
    assert any(m["code"] == "tight" for m in q["messages"])
    # the client's reservation becomes a request; the owner's approval then holds it
    r = client.post("/api/bookings", json=booking_body(q["quote_id"]))
    assert r.status_code == 201 and not r.json()["instant"] and r.json()["status"] == "requested"
    booking_id = r.json()["booking_id"]
    assert admin.post(f"/admin/bookings/{booking_id}/approve", follow_redirects=False).status_code == 303
    assert held(booking_id) and held(booking_id)["kind"] == "hold"


def test_heavy_traffic_days_lengthen_trips(now):
    cat = get_catalog()
    ordinary = quote(now, origin="manhattan", destination="jfk", pickup="2026-11-24T10:00")
    heavy = quote(now, origin="manhattan", destination="jfk", pickup="2026-11-25T10:00")
    with tx() as conn:
        windows = {r["pickup_at"].date().isoformat(): r["service_end"] - r["pickup_at"] for r in conn.execute(
            "SELECT pickup_at, service_end FROM quotes WHERE id IN (%s, %s)", (ordinary["quote_id"], heavy["quote_id"]))}
    assert windows["2026-11-25"] > windows["2026-11-24"]
    assert cat.scheduling["heavy_days"]["2026-11-25"] > 1
