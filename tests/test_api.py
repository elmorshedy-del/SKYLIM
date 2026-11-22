"""HTTP contract: what browsers, Stripe and the admin can and cannot do."""
from __future__ import annotations

from app.domain import rates
from app.domain.catalog import get_catalog


def quote_body(**kw):
    body = {"service": "transfer", "origin": "bergen", "destination": "jfk", "pickup_local": "2026-11-25T06:30",
            "passengers": 2, "large_bags": 2}
    body.update(kw)
    return body


def booking_body(quote_id, **kw):
    body = {"quote_id": quote_id,
            "contact": {"name": "Jordan Ellis", "email": "jordan@example.com", "phone": "(201) 555-0147"},
            "trip": {"pickup_address": "12 Prospect Ave, Hackensack NJ", "dropoff_address": "JFK Terminal 4"},
            "preferences": {"mode": "work", "child_seat": "booster", "child_details": "6 years, 45 lb"},
            "accept_policy_version": get_catalog().policy["version"]}
    body.update(kw)
    return body


def test_quote_api_prices_on_server(client):
    r = client.post("/api/quotes", json=quote_body())
    assert r.status_code == 200
    q = r.json()
    cat = get_catalog()
    list_cents = rates.journey(cat, cat.places["bergen"], cat.places["jfk"]).cents
    assert q["list_amount_cents"] == list_cents
    # the introductory offer, while it runs, discounts from the list price (never less than its percentage)
    if q["offer"]:
        assert q["amount_cents"] <= list_cents * (100 - q["offer"]["percent_off"]) / 100
        assert q["amount_cents"] % 500 == 0
    else:
        assert q["amount_cents"] == list_cents
    assert q["bookable"] and q["availability"] == "available"


def test_server_calculates_amount_and_rejects_client_override(client):
    assert client.post("/api/quotes", json=quote_body(amount_cents=100)).status_code == 422
    assert client.post("/api/quotes", json=quote_body(vehicle="sprinter")).status_code == 422
    q = client.post("/api/quotes", json=quote_body()).json()
    r = client.post("/api/bookings", json=booking_body(q["quote_id"], amount_cents=100))
    assert r.status_code == 422
    r = client.post("/api/bookings", json=booking_body(q["quote_id"]))
    assert r.status_code == 201
    assert r.json()["amount_cents"] == q["amount_cents"]


def test_invalid_inputs_rejected(client):
    assert client.post("/api/quotes", json=quote_body(origin="nowhere")).status_code == 422
    assert client.post("/api/quotes", json=quote_body(pickup_local="soon")).status_code == 422
    q = client.post("/api/quotes", json=quote_body()).json()
    bad = booking_body(q["quote_id"])
    bad["contact"]["email"] = "not-an-email"
    assert client.post("/api/bookings", json=bad).status_code == 422
    bot = booking_body(q["quote_id"], website="http://spam")
    assert client.post("/api/bookings", json=bot).status_code == 422


def test_child_seat_request_flags_review_and_trip_page_renders(client):
    q = client.post("/api/quotes", json=quote_body()).json()
    b = client.post("/api/bookings", json=booking_body(q["quote_id"])).json()
    page = client.get(f"/trip/{b['trip_token']}")
    assert page.status_code == 200
    assert "noindex" in page.headers["x-robots-tag"] and page.headers["cache-control"] == "no-store"
    assert "Child seat: booster" in page.text and b["ref"] in page.text
    assert client.get("/trip/not-a-real-token").status_code == 404


def test_public_config_hides_inactive_features(client):
    cfg = client.get("/api/config").json()
    assert cfg["places"]["teb"]["airport"] is True
    assert cfg["hourly"]["min_hours"] == 3
    assert cfg["payment_methods"] == ["card", "apple_pay", "google_pay", "link"]


def test_admin_requires_login_and_same_origin(client):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin/login"
    bad = client.post("/admin/login", data={"password": "wrong"}, headers={"Origin": "https://test.example"})
    assert bad.status_code == 401


def test_admin_approves_and_rejects_cross_site_posts(admin):
    # six hours' notice: inside the instant window, so it needs the owner's approval
    q = admin.post("/api/quotes", json=quote_body(pickup_local="2026-11-20T16:00")).json()
    assert q["bookable"] and not q["instant"]
    b = admin.post("/api/bookings", json=booking_body(q["quote_id"])).json()
    page = admin.get("/admin")
    assert page.status_code == 200 and b["ref"] in page.text and "child seat check" in page.text
    cross = admin.post(f"/admin/bookings/{b['booking_id']}/approve", headers={"Origin": "https://evil.example"},
                       follow_redirects=False)
    assert cross.status_code == 403
    ok = admin.post(f"/admin/bookings/{b['booking_id']}/approve", follow_redirects=False)
    assert ok.status_code == 303
    trip = admin.get(f"/api/trips/{b['trip_token']}").json()
    assert trip["status"] == "payment_pending" and trip["payable"] is True


def test_stripe_webhook_rejects_unsigned(client):
    r = client.post("/api/webhooks/stripe", content=b'{"id":"evt_x","type":"checkout.session.completed"}',
                    headers={"stripe-signature": "t=1,v1=deadbeef"})
    assert r.status_code == 403


def test_marketing_and_policy_pages_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/pricing.md").status_code == 200
    assert client.get("/privacy").status_code == 200
    assert client.get("/nope").status_code == 404
    assert client.get("/healthz").json() == {"ok": True}
