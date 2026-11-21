"""Instant reservation, availability, alternatives, daily cap, owner blocks and the launch offer."""
from __future__ import annotations

from dataclasses import replace

from app.db import tx
from app.domain import rates
from app.domain.catalog import get_catalog
from app.domain.pricing import TripRequest, parse_local_pickup
from app.services import quotes as quotes_service
from tests.test_api import booking_body, quote_body


def test_clean_trip_is_reserved_and_sent_to_payment(client, gw):
    q = client.post("/api/quotes", json=quote_body()).json()
    assert q["bookable"] and q["instant"]
    r = client.post("/api/bookings", json=booking_body(q["quote_id"])).json()
    assert r["instant"] and r["status"] == "payment_pending"
    assert r["checkout_url"] == "https://checkout.stripe.test/cs_test_1"
    with tx() as conn:
        hold = conn.execute("SELECT kind, expires_at FROM reservations WHERE released_at IS NULL").fetchone()
    assert hold["kind"] == "hold"


def test_short_notice_or_luggage_review_goes_to_approval(client):
    soon = client.post("/api/quotes", json=quote_body(pickup_local="2026-11-20T16:00")).json()
    heavy = client.post("/api/quotes", json=quote_body(passengers=6, large_bags=3, carry_ons=3)).json()
    assert soon["bookable"] and not soon["instant"]
    assert heavy["bookable"] and not heavy["instant"]
    r = client.post("/api/bookings", json=booking_body(soon["quote_id"])).json()
    assert r["status"] == "requested" and r["checkout_url"] is None


def test_paused_instant_booking_routes_everything_to_approval(admin):
    admin.post("/admin/instant", data={"enabled": "off"})
    q = admin.post("/api/quotes", json=quote_body()).json()
    assert q["bookable"] and not q["instant"]
    admin.post("/admin/instant", data={"enabled": "on"})
    assert admin.post("/api/quotes", json=quote_body()).json()["instant"]


def test_taken_slot_offers_open_alternatives(client):
    first = client.post("/api/quotes", json=quote_body()).json()
    client.post("/api/bookings", json=booking_body(first["quote_id"]))
    clash = client.post("/api/quotes", json=quote_body(pickup_local="2026-11-25T07:00")).json()
    assert not clash["bookable"] and clash["availability"] == "unavailable"
    assert clash["alternatives"], "a busy slot must never be a dead end"
    alt = clash["alternatives"][0]["pickup_local"]
    retry = client.post("/api/quotes", json=quote_body(pickup_local=alt)).json()
    assert retry["bookable"]


def test_two_clients_racing_for_one_slot_only_one_holds_it(client):
    a = client.post("/api/quotes", json=quote_body()).json()
    b = client.post("/api/quotes", json=quote_body(pickup_local="2026-11-25T06:45")).json()
    assert a["bookable"] and b["bookable"]                              # both looked free when priced
    assert client.post("/api/bookings", json=booking_body(a["quote_id"])).status_code == 201
    r = client.post("/api/bookings", json=booking_body(b["quote_id"]))
    assert r.status_code == 409 and r.json()["error"] == "slot_taken"


def test_daily_cap_protects_the_chauffeur(now, settings):
    tight = replace(settings, max_daily_minutes=60)        # less than one Bergen -> JFK trip's own time
    req = TripRequest(service="transfer", origin="bergen", destination="jfk",
                      pickup_at=parse_local_pickup("2026-11-25T06:30"), passengers=2, large_bags=2)
    with tx() as conn:
        q = quotes_service.create_quote(conn, req, cat=get_catalog(), settings=tight, now=now)
    assert q["availability"] == "day_full" and not q["bookable"]


def test_owner_block_hides_time_and_cannot_cover_a_trip(admin):
    r = admin.post("/admin/blocks", data={"starts": "2026-11-25T05:00", "ends": "2026-11-25T10:00",
                                          "note": "personal"}, follow_redirects=False)
    assert r.status_code == 303 and "msg=" in r.headers["location"]
    q = admin.post("/api/quotes", json=quote_body()).json()
    assert not q["bookable"] and q["availability"] == "unavailable"
    q2 = admin.post("/api/quotes", json=quote_body(pickup_local="2026-11-26T15:00")).json()
    admin.post("/api/bookings", json=booking_body(q2["quote_id"]))
    clash = admin.post("/admin/blocks", data={"starts": "2026-11-26T14:00", "ends": "2026-11-26T18:00"},
                       follow_redirects=False)
    assert "err=" in clash.headers["location"]


def test_introductory_offer_discounts_from_list_price(now):
    cat = get_catalog()
    params = dict(cat.params)
    params["introductory"] = {"active": True, "label": "Founding client rate", "percent_off": 15,
                              "ends_local": "2027-02-28T23:59"}
    promo = replace(cat, params=params)
    amount, offer = rates.introductory(promo, 37000, now)
    assert amount == 31400 and offer["label"] == "Founding client rate"
    later = now.replace(year=2027, month=3, day=2)
    assert rates.introductory(promo, 37000, later) == (37000, None)


def test_attribution_is_stored_without_personal_data(client):
    attribution = {"utm_source": "google", "utm_medium": "cpc", "gclid": "abc123", "email": "x@y.z"}
    q = client.post("/api/quotes", json=quote_body(attribution=attribution, session_id="s-1")).json()
    body = booking_body(q["quote_id"], attribution=attribution)
    client.post("/api/bookings", json=body)
    with tx() as conn:
        b = conn.execute("SELECT attribution FROM bookings").fetchone()["attribution"]
        qa = conn.execute("SELECT attribution, session_id FROM quotes").fetchone()
    assert b == {"utm_source": "google", "utm_medium": "cpc", "gclid": "abc123"}
    assert qa["session_id"] == "s-1" and "email" not in qa["attribution"]
