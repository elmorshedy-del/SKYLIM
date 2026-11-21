"""The owner's $1 test trip: a real booking and payment that never blocks a client and never counts as revenue."""
from __future__ import annotations

import dataclasses

import data
from app import config
from app.db import TEST_VEHICLE_ID, tx
from app.services import insights, payments, test_trip
from tests.helpers import quote
from tests.test_payments import session_event, signed


def start(admin):
    r = admin.post("/admin/test-trip", follow_redirects=False)
    assert r.status_code == 303, r.text
    return r


def the_test_booking():
    with tx() as conn:
        return conn.execute("SELECT * FROM bookings WHERE is_test").fetchone()


def test_books_one_dollar_on_the_hidden_calendar_and_goes_straight_to_checkout(admin, gw):
    r = start(admin)
    assert r.headers["location"] == "https://checkout.stripe.test/cs_test_1"
    b = the_test_booking()
    assert b["amount_cents"] == data.TEST_TRIP["amount_cents"] == 100 and b["status"] == "payment_pending"
    with tx() as conn:
        hold = conn.execute("SELECT * FROM reservations WHERE booking_id = %s", (b["id"],)).fetchone()
    assert hold["vehicle_id"] == TEST_VEHICLE_ID
    product = gw.sessions[0]["params"]["line_items"][0]["price_data"]["product_data"]
    assert product["name"].startswith("Test trip") and gw.sessions[0]["params"]["metadata"]["test_trip"] == "true"


def test_never_blocks_a_client(admin, gw, now):
    start(admin)
    b = the_test_booking()
    pickup = b["pickup_at"].astimezone(config.LOCAL_TZ).strftime("%Y-%m-%dT%H:%M")
    origin, destination = data.TEST_TRIP["route"]
    client_quote = quote(now, origin=origin, destination=destination, pickup=pickup)
    assert client_quote["bookable"] and client_quote["availability"] == "available"


def test_paid_test_trip_confirms_but_is_never_revenue_or_demand(admin, gw, now):
    start(admin)
    b = the_test_booking()
    body, sig = signed(session_event("cs_test_1", b))
    payments.handle_event(body, sig, now=now)
    b = the_test_booking()
    assert b["status"] == "confirmed"
    with tx() as conn:
        assert conn.execute("SELECT count(*) AS n FROM analytics_outbox").fetchone()["n"] == 0   # no GA4 purchase
        f = insights.funnel(conn, now)
    assert f["reservations"] == 0 and f["paid"] == 0 and f["revenue_cents"] == 0               # not in the funnel
    csv = admin.get("/admin/exports/google-ads-conversions.csv").text
    assert b["ref"] not in csv


def test_switched_off_it_disappears_and_refuses(admin, gw, monkeypatch):
    monkeypatch.setitem(data.TEST_TRIP, "enabled", False)
    assert "Start a $1.00 test trip" not in admin.get("/admin").text
    r = admin.post("/admin/test-trip", follow_redirects=False)
    assert r.status_code == 303 and "checkout.stripe" not in r.headers["location"]
    assert the_test_booking() is None


def test_skips_launch_gates_but_never_uses_a_live_key_outside_production(settings):
    prod_live = dataclasses.replace(settings, app_env="production", stripe_secret_key="sk_live_x")
    assert config.payments_possible(prod_live) and not config.payments_live(prod_live)   # gates still open
    assert test_trip.readiness(prod_live)[0]
    staging_live = dataclasses.replace(settings, app_env="staging", stripe_secret_key="sk_live_x")
    assert not config.payments_possible(staging_live)
    ok, why = test_trip.readiness(staging_live)
    assert not ok and "production" in why
