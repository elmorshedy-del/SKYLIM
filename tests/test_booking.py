"""Quotes, eligibility, the calendar guarantee and the booking lifecycle."""
from __future__ import annotations

import threading
from datetime import datetime, timezone

import pytest

from app.db import tx
from app.domain import rates
from app.domain.catalog import get_catalog
from app.domain.pricing import QuoteInputError, parse_local_pickup
from app.domain.status import Status, TransitionError
from app.errors import Conflict
from app.services import bookings
from tests.helpers import approve, later, quote, request


def test_server_calculates_amount_from_cost_model(now):
    cat = get_catalog()
    q = quote(now, origin="bergen", destination="jfk")
    assert q["amount_cents"] == rates.transfer(cat, cat.places["bergen"], cat.places["jfk"]).cents
    assert q["currency"] == "usd"
    assert q["price_status"] == ("firm" if cat.pricing_approved else "estimate")


def test_hourly_priced_at_published_rate_with_minimum(now):
    cat = get_catalog()
    q = quote(now, service="hourly", origin="manhattan", hours=4)
    assert q["amount_cents"] == 4 * cat.params["hourly_cents"]
    short = quote(now, service="hourly", origin="essex", hours=2)
    assert not short["bookable"] and any(m["code"] == "hours_range" for m in short["messages"])


def test_authority_rules_follow_the_licence(now):
    """TLC licence: trips that start in NYC or end in it are booked online; others are arranged by request."""
    from app.domain import pricing
    cat = get_catalog()
    assert pricing.route_class(cat, "manhattan", "jfk") == "nyc_pickup"
    assert pricing.route_class(cat, "manhattan", "ewr") == "nyc_pickup"
    assert pricing.route_class(cat, "teb", "manhattan") == "into_nyc"
    assert pricing.route_class(cat, "hudson", "ewr") == "nj_intrastate"
    assert pricing.route_class(cat, "bergen", "westchester") == "interstate"
    assert pricing.route_class(cat, "westchester", "hpn") == "other_intrastate"
    assert pricing.route_class(cat, "manhattan", None) == "nyc_pickup"          # hourly: where it starts

    for origin, destination in [("manhattan", "jfk"), ("teb", "manhattan"), ("bergen", "jfk")]:
        assert quote(now, origin=origin, destination=destination)["bookable"], (origin, destination)
    nj_only = quote(now, origin="hudson", destination="ewr")
    assert not nj_only["bookable"] and nj_only["amount_cents"]          # priced, but arranged by request
    assert any(m["code"] == "authority_arranged" for m in nj_only["messages"])


def test_booking_amount_comes_from_quote_not_input(now):
    b, _ = request(now)
    with tx() as conn:
        stored = conn.execute("SELECT amount_cents FROM quotes WHERE id = %s", (b["quote_id"],)).fetchone()
    assert b["amount_cents"] == stored["amount_cents"]


def test_unsupported_route_or_vehicle_rejected(now):
    with pytest.raises(QuoteInputError):
        quote(now, origin="atlantis")
    with pytest.raises(QuoteInputError):
        quote(now, destination="mars")
    custom = quote(now, origin="cape-may", destination="hamptons")
    assert not custom["bookable"] and custom["price_status"] == "custom"
    too_many = quote(now, passengers=9, bags=0)
    assert not too_many["bookable"]


def test_non_bookable_quote_cannot_become_a_booking(now):
    q = quote(now, origin="cape-may", destination="hamptons")
    with tx() as conn, pytest.raises(Conflict):
        from app.domain.catalog import get_catalog
        from app.domain.preferences import JourneyPreferences
        bookings.create(conn, quote_id=q["quote_id"], contact=bookings.Contact("A B", "a@b.co", "2015550147"),
                        trip=bookings.TripDetails("x street 1", "y street 2"), preferences=JourneyPreferences(),
                        remember=False, accepted_policy_version=get_catalog().policy["version"], source=None,
                        cat=get_catalog(), now=now)


def test_luggage_beyond_tested_capacity_needs_review(now):
    q = quote(now, passengers=6, bags=3, carry_ons=3)
    assert q["bookable"] and q["needs_review"]
    b, _ = request(now, passengers=6, bags=3, carry_ons=3, pickup="2026-11-27T09:00")
    assert b["review_flag"] == "capacity_review"


def test_notice_and_horizon_enforced(now):
    soon = quote(now, pickup="2026-11-20T12:00")          # two hours from NOW (10:00 ET)
    assert not soon["bookable"] and any(m["code"] == "too_soon" for m in soon["messages"])
    far = quote(now, pickup="2027-12-01T09:00")
    assert not far["bookable"] and any(m["code"] == "too_far" for m in far["messages"])


def test_timezone_near_midnight():
    assert parse_local_pickup("2026-11-25T23:45") == datetime(2026, 11, 26, 4, 45, tzinfo=timezone.utc)
    assert parse_local_pickup("2026-07-04T00:15") == datetime(2026, 7, 4, 4, 15, tzinfo=timezone.utc)
    with pytest.raises(QuoteInputError):
        parse_local_pickup("2027-03-14T02:30")           # skipped by the spring DST change
    with pytest.raises(QuoteInputError):
        parse_local_pickup("tomorrow-ish")


def test_service_window_covers_drive_out_and_back(now):
    b, _ = request(now)
    assert b["service_start"] < b["pickup_at"] < b["service_end"]
    assert (b["service_end"] - b["service_start"]).total_seconds() / 3600 > 2.5   # Bergen -> JFK, empty return


def test_two_overlapping_approvals_only_one_succeeds(now):
    a, _ = request(now, pickup="2026-11-25T06:30")
    b, _ = request(now, pickup="2026-11-25T07:00")
    results: dict[str, str] = {}
    barrier = threading.Barrier(2)

    def run(name, booking_id):
        barrier.wait()
        try:
            approve(booking_id, now)
            results[name] = "ok"
        except Conflict as e:
            results[name] = e.code

    threads = [threading.Thread(target=run, args=(n, x["id"])) for n, x in (("a", a), ("b", b))]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results.values()) == ["ok", "slot_taken"]
    with tx() as conn:
        live = conn.execute("SELECT count(*) AS n FROM reservations WHERE released_at IS NULL").fetchone()["n"]
    assert live == 1


def test_non_overlapping_trips_both_approved(now):
    a, _ = request(now, pickup="2026-11-25T06:30")
    b, _ = request(now, pickup="2026-11-25T16:00")
    approve(a["id"], now)
    approve(b["id"], now)


def test_expired_hold_released(now):
    a, _ = request(now, pickup="2026-11-25T06:30")
    b, _ = request(now, pickup="2026-11-25T07:00")
    approve(a["id"], now)
    with pytest.raises(Conflict):
        approve(b["id"], later(now, 10))
    # after the hold lapses, the overlapping request can take the slot and A expires
    after_hold = later(now, 6 * 60 + 1)
    approve(b["id"], after_hold)
    with tx() as conn:
        assert bookings.get(conn, a["id"])["status"] == Status.EXPIRED
        assert bookings.get(conn, b["id"])["status"] == Status.PAYMENT_PENDING
        kinds = conn.execute("SELECT kind FROM outbox WHERE booking_id = %s", (a["id"],)).fetchall()
    assert "expired" in {k["kind"] for k in kinds}


def test_expired_quote_and_reused_quote_rejected(now):
    q = quote(now)
    from app.domain.catalog import get_catalog
    from app.domain.preferences import JourneyPreferences
    args = dict(contact=bookings.Contact("A B", "a@b.co", "2015550147"),
                trip=bookings.TripDetails("x street 1", "y street 2"), preferences=JourneyPreferences(),
                remember=False, accepted_policy_version=get_catalog().policy["version"], source=None,
                cat=get_catalog())
    with tx() as conn, pytest.raises(Conflict) as e:
        bookings.create(conn, quote_id=q["quote_id"], now=later(now, 120), **args)
    assert e.value.code == "quote_expired"
    with tx() as conn:
        bookings.create(conn, quote_id=q["quote_id"], now=now, **args)
    with tx() as conn, pytest.raises(Conflict) as e:
        bookings.create(conn, quote_id=q["quote_id"], now=now, **args)
    assert e.value.code == "quote_used"


def test_price_change_on_approval_requires_reason(now):
    b, _ = request(now)
    with pytest.raises(Exception):
        approve(b["id"], now, amount_cents=b["amount_cents"] + 2000)
    row = approve(b["id"], now, amount_cents=b["amount_cents"] + 2000, adjust_reason="Second pickup stop")
    assert row["amount_cents"] == b["amount_cents"] + 2000


def test_status_machine_blocks_skips(now):
    b, _ = request(now)
    with tx() as conn, pytest.raises(TransitionError):
        bookings.advance(conn, b["id"], Status.EN_ROUTE, now=now)


def test_request_emails_rider_and_owner_once(now):
    b, _ = request(now)
    with tx() as conn:
        rows = conn.execute("SELECT kind, to_email FROM outbox ORDER BY id").fetchall()
    assert [(r["kind"], r["to_email"]) for r in rows] == [
        ("request_received", "jordan@example.com"), ("owner_new_request", "owner@test.example")]


def test_published_luggage_guide_matches_capacity_rule():
    """Every line of the 'what fits' guide shown to clients must be accepted without review."""
    import re

    from app.domain.pricing import capacity_check
    vehicle = get_catalog().vehicle
    for guests_label, fits, _ in vehicle["luggage_guide"]:
        guests = int(re.search(r"\d+", guests_label).group())
        large, carry = (int(n) for n in re.findall(r"\d+", fits))
        assert capacity_check(vehicle, guests, large, carry) is None, (guests_label, fits)
        assert capacity_check(vehicle, guests, large + 1, carry) == "capacity_review", (guests_label, fits)
    assert capacity_check(vehicle, 7, 0, 0) == "over_capacity"
