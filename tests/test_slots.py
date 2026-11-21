"""Appointment-style pickup times: only times that can really be reserved online are offered."""
from __future__ import annotations

from datetime import timedelta

from app.config import get_settings
from app.domain.pricing import parse_local_pickup

from tests.helpers import approve, request

DAY = "2026-11-25"          # the Wednesday before Thanksgiving; NOW is Fri 20 Nov, 10:00 New York


def slots(client, **kw) -> dict:
    body = {"origin": "manhattan", "destination": "jfk", "date": DAY, "passengers": 2, "large_bags": 2} | kw
    r = client.post("/api/slots", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_offers_half_hourly_times_on_the_chosen_day_with_the_launch_note(client):
    out = slots(client)
    times = [s["pickup_local"] for s in out["slots"]]
    assert times and all(t.startswith(DAY) for t in times)
    assert "2026-11-25T04:00" in times and "2026-11-25T23:30" in times
    assert all(t[-2:] in ("00", "30") for t in times)
    assert out["note"].startswith("Limited availability") and out["phone"]
    assert out["slots"][0]["label"] == "4:00 am"


def test_times_the_chauffeur_is_already_booked_are_not_offered(client, now):
    b, _ = request(now, origin="manhattan", destination="jfk", pickup=f"{DAY}T10:00")
    approve(b["id"], now)
    times = {s["pickup_local"] for s in slots(client)["slots"]}
    # the held trip and the times whose own journey would run into it are gone...
    assert not {f"{DAY}T09:30", f"{DAY}T10:00", f"{DAY}T10:30", f"{DAY}T11:00"} & times
    # ...and the rest of the day stays open
    assert f"{DAY}T04:00" in times and f"{DAY}T23:30" in times


def test_no_times_inside_the_online_notice_period(client, now):
    today = slots(client, date="2026-11-20")["slots"]
    earliest = now + timedelta(minutes=get_settings().instant_min_notice_minutes)
    assert all(parse_local_pickup(s["pickup_local"]) >= earliest for s in today)


def test_routes_that_are_arranged_personally_explain_why_instead_of_listing_times(client):
    out = slots(client, origin="hudson", destination="ewr")          # NJ to NJ: not covered by the TLC licence
    assert out["slots"] == []
    assert any(m["code"] == "authority_arranged" for m in out["messages"])


def test_bad_input_is_rejected(client):
    assert client.post("/api/slots", json={"origin": "manhattan", "destination": "jfk", "date": "25-11-2026"}).status_code == 422
    assert client.post("/api/slots", json={"origin": "nowhere", "destination": "jfk", "date": DAY}).status_code in (400, 422)
