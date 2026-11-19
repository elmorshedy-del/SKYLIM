"""Location privacy: stored only during an active trip, visible only to that trip,
never presented as live once it is stale, and gone when the trip ends."""
from __future__ import annotations

from datetime import timedelta

from app.db import tx
from app.domain.status import Status
from app.services import bookings
from tests.helpers import approve, request

PHONE = "phone-device-secret-123"
CAR = "car-tracker-secret-456"


def confirmed_trip(now, **kw):
    b, token = request(now, **kw)
    approve(b["id"], now)
    with tx() as conn:
        row = bookings.get(conn, b["id"], lock=True)
        bookings.confirm_paid(conn, row, paid_cents=row["amount_cents"], now=now)
    return b, token


def advance(booking_id, target, now):
    with tx() as conn:
        return bookings.advance(conn, booking_id, target, now=now)


def report(client, lat=40.8859, lon=-74.0435, ts=None, device=PHONE, as_json=False):
    if as_json:
        return client.post("/api/tracking/osmand", json={"device_id": device, "location": {
            "timestamp": ts, "coords": {"latitude": lat, "longitude": lon, "accuracy": 8, "speed": 12.5}}})
    return client.post("/api/tracking/osmand", data={"id": device, "lat": lat, "lon": lon,
                                                     "timestamp": ts, "speed": 20, "accuracy": 8})


def positions_count():
    with tx() as conn:
        return conn.execute("SELECT count(*) AS n FROM positions").fetchone()["n"]


def test_position_only_for_active_trip(client, now):
    b, token = confirmed_trip(now)
    assert report(client, ts=int(now.timestamp())).status_code == 200
    assert positions_count() == 0                                    # confirmed but not en route: discarded
    assert client.get(f"/api/trips/{token}/position").json()["available"] is False
    advance(b["id"], Status.EN_ROUTE, now)
    assert report(client, ts=int(now.timestamp())).text == "ok"
    pos = client.get(f"/api/trips/{token}/position").json()
    assert pos["available"] and not pos["stale"] and pos["age_seconds"] == 0
    assert abs(pos["lat"] - 40.8859) < 1e-4


def test_unknown_device_and_bad_reports_rejected(client, now):
    assert report(client, device="someone-else").status_code == 403
    assert client.post("/api/tracking/osmand", data={"id": PHONE, "lat": "abc", "lon": "1"}).status_code == 400
    assert client.post("/api/tracking/osmand", data={"id": PHONE, "lat": "0", "lon": "0"}).status_code == 400


def test_json_format_and_fixes_before_trip_start_ignored(client, now):
    b, token = confirmed_trip(now)
    advance(b["id"], Status.EN_ROUTE, now)
    old = (now - timedelta(minutes=30)).isoformat()
    report(client, ts=old, as_json=True)
    assert positions_count() == 0                                    # taken before En route
    report(client, ts=now.isoformat(), as_json=True)
    assert positions_count() == 1


def test_other_trip_token_cannot_access_location(client, now):
    a, token_a = confirmed_trip(now, pickup="2026-11-25T06:30")
    _, token_b = request(now, pickup="2026-11-26T15:00")
    advance(a["id"], Status.EN_ROUTE, now)
    report(client, ts=int(now.timestamp()))
    assert client.get(f"/api/trips/{token_a}/position").json()["available"] is True
    assert client.get(f"/api/trips/{token_b}/position").json()["available"] is False
    assert client.get("/api/trips/forged-token/position").status_code == 404


def test_stale_position_not_presented_as_live(client, now):
    b, token = confirmed_trip(now)
    advance(b["id"], Status.EN_ROUTE, now)
    report(client, ts=int(now.timestamp()))
    later = now + timedelta(seconds=150)
    client.app.dependency_overrides[next(iter(client.app.dependency_overrides))] = lambda: later
    pos = client.get(f"/api/trips/{token}/position").json()
    assert pos["available"] and pos["stale"] and pos["age_seconds"] == 150
    assert "last known position" in pos["message"]


def test_completed_trip_token_expires_and_locations_deleted(client, now):
    b, token = confirmed_trip(now)
    advance(b["id"], Status.EN_ROUTE, now)
    report(client, ts=int(now.timestamp()))
    share = client.post(f"/api/trips/{token}/share", json={"hours": 2}).json()
    share_token = share["share_url"].rsplit("/", 1)[1]
    for target in (Status.ARRIVED, Status.IN_VEHICLE, Status.COMPLETED):
        advance(b["id"], target, now)
    assert positions_count() == 0
    assert client.get(f"/api/trips/{token}/position").json()["available"] is False
    assert client.get(f"/api/share/{share_token}/position").status_code == 404
    report(client, ts=int(now.timestamp()))
    assert positions_count() == 0                                    # nothing kept after the trip


def test_share_view_omits_personal_data(client, now):
    b, token = confirmed_trip(now)
    advance(b["id"], Status.EN_ROUTE, now)
    report(client, ts=int(now.timestamp()))
    share = client.post(f"/api/trips/{token}/share", json={"hours": 2}).json()
    view = client.get("/api/share/" + share["share_url"].rsplit("/", 1)[1] + "/position").json()
    text = str(view).lower()
    assert view["available"] and "lat" in view
    for secret in ("jordan", "example.com", "555", "prospect", "terminal", b["ref"].lower(), "amount"):
        assert secret not in text


def test_in_car_tracker_forwarded_by_traccar(client, now):
    b, token = confirmed_trip(now)
    advance(b["id"], Status.EN_ROUTE, now)
    payload = {"position": {"latitude": 40.81, "longitude": -73.95, "fixTime": now.isoformat(), "speed": 30,
                            "valid": True, "accuracy": 5}, "device": {"uniqueId": CAR}}
    assert client.post("/api/tracking/traccar", json=payload).status_code == 403          # no token
    r = client.post("/api/tracking/traccar", json=payload, headers={"Authorization": "Bearer forward-token-789"})
    assert r.json() == {"ok": True, "outcome": "stored"}
    pos = client.get(f"/api/trips/{token}/position").json()
    assert abs(pos["lat"] - 40.81) < 1e-4
