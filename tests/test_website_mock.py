"""The public reservation form's owner mock exercises the same customer pipeline."""
from __future__ import annotations

import dataclasses

import httpx

from app.db import TEST_DRIVER_ID, TEST_VEHICLE_ID, tx
from app.services import insights, notifications, payments
from app.domain.status import Status
from tests.test_api import booking_body, quote_body
from tests.test_payments import session_event, signed
from tests.test_tracking import advance, confirmed_trip, report


def mock_quote(admin):
    r = admin.post("/api/quotes", json=quote_body(mock=True))
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["amount_cents"] == 100 and q["mock"] and q["instant"]
    return q


def mock_booking(admin, now):
    q = mock_quote(admin)
    body = booking_body(q["quote_id"], contact={"name": "Owner Test", "email": "owner@test.example",
                        "phone": "2015550147"}, preferences={"mode": "work"})
    r = admin.post("/api/bookings", json=body)
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["amount_cents"] == 100 and result["instant"] and result["mock"]
    assert result["checkout_url"] == "https://checkout.stripe.test/cs_test_1"
    with tx() as conn:
        b = conn.execute("SELECT * FROM bookings WHERE id = %s", (result["booking_id"],)).fetchone()
        assert b["is_test"] and b["pickup_address"] == "12 Prospect Ave, Hackensack NJ"
        assert b["driver_id"] == TEST_DRIVER_ID and b["vehicle_id"] == TEST_VEHICLE_ID
    payments.handle_event(*signed(session_event("cs_test_1", b)), now=now)
    return b, result


def test_website_mock_checkout_receipt_tracking_notification_and_calendar(admin, now):
    b, result = mock_booking(admin, now)
    token = result["trip_token"]
    view = admin.get(f"/api/trips/{token}").json()
    assert view["status"] == "confirmed"
    with tx() as conn:
        receipt = conn.execute("SELECT * FROM outbox WHERE booking_id = %s AND kind = 'confirmed'", (b["id"],)).fetchone()
        assert receipt["to_email"] == "owner@test.example" and result["trip_url"] in receipt["body_text"]
        assert insights.funnel(conn, now)["quotes"] == 0
        assert insights.funnel(conn, now)["paid"] == 0
    regular = admin.post("/api/quotes", json=quote_body()).json()
    assert regular["amount_cents"] > 100 and regular["availability"] == "available"
    advance(b["id"], Status.EN_ROUTE, now)
    with tx() as conn:
        en_route = conn.execute("SELECT * FROM outbox WHERE booking_id = %s AND kind = 'en_route'", (b["id"],)).fetchone()
        assert result["trip_url"] in en_route["body_text"]
    assert report(admin, ts=int(now.timestamp())).status_code == 200
    pos = admin.get(f"/api/trips/{token}/position").json()
    assert pos["available"] and abs(pos["lat"] - 40.8859) < 1e-4
    assert "Live location" in admin.get(f"/trip/{token}").text
    advance(b["id"], Status.ARRIVED, now)
    advance(b["id"], Status.IN_VEHICLE, now)
    advance(b["id"], Status.COMPLETED, now)
    assert not admin.get(f"/api/trips/{token}/position").json()["available"]


def test_mock_quote_cannot_be_booked_after_logout_or_to_unapproved_recipient(admin):
    q = mock_quote(admin)
    assert admin.post("/api/bookings", json=booking_body(q["quote_id"])).status_code == 403
    admin.post("/admin/logout", follow_redirects=False)
    body = booking_body(q["quote_id"], contact={"name": "Owner Test", "email": "owner@test.example",
                        "phone": "2015550147"}, preferences={})
    assert admin.post("/api/bookings", json=body).status_code == 403


def test_real_tracking_always_takes_precedence_over_mock(admin, now):
    mock, mock_result = mock_booking(admin, now)
    advance(mock["id"], Status.EN_ROUTE, now)
    real, real_token = confirmed_trip(now)
    advance(real["id"], Status.EN_ROUTE, now)
    report(admin, ts=int(now.timestamp()))
    assert admin.get(f"/api/trips/{real_token}/position").json()["available"]
    assert not admin.get(f"/api/trips/{mock_result['trip_token']}/position").json()["available"]


def test_mock_slots_are_available_even_when_the_real_calendar_is_occupied(admin, now):
    confirmed_trip(now)
    body = {"origin": "bergen", "destination": "jfk", "date": "2026-11-25",
            "passengers": 2, "large_bags": 2}
    real = admin.post("/api/slots", json=body).json()["slots"]
    mock = admin.post("/api/slots", json={**body, "mock": True}).json()["slots"]
    assert not any(s["pickup_local"] == "2026-11-25T06:30" for s in real)
    assert any(s["pickup_local"] == "2026-11-25T06:30" and s["mode"] == "instant" for s in mock)


def test_mock_approval_and_payment_recovery_use_same_trip_link(admin, now):
    q = admin.post("/api/quotes", json=quote_body(mock=True, pickup_local="2026-11-20T16:00")).json()
    assert q["bookable"] and not q["instant"] and q["amount_cents"] == 100
    body = booking_body(q["quote_id"], contact={"name": "Owner Test", "email": "owner@test.example",
                        "phone": "2015550147"}, preferences={})
    b = admin.post("/api/bookings", json=body).json()
    assert b["status"] == "requested" and b["checkout_url"] is None
    admin.post(f"/admin/bookings/{b['booking_id']}/approve", follow_redirects=False)
    trip = admin.get(f"/api/trips/{b['trip_token']}").json()
    assert trip["status"] == "payment_pending" and trip["payable"]
    with tx() as conn:
        booking = conn.execute("SELECT * FROM bookings WHERE id = %s", (b["booking_id"],)).fetchone()
        assert booking["driver_id"] == TEST_DRIVER_ID and booking["amount_cents"] == 100
        link = conn.execute("SELECT body_text FROM outbox WHERE booking_id = %s AND kind = 'payment_link'", (booking["id"],)).fetchone()
        assert b["trip_url"] in link["body_text"]


def test_provider_delivery_attempt_includes_confirmation_link(admin, now, settings, monkeypatch):
    b, result = mock_booking(admin, now)
    delivered = []

    def postmark_post(url, **kw):
        assert url == "https://api.postmarkapp.com/email"
        delivered.append(kw["json"])
        return httpx.Response(200, json={"MessageID": "test-provider-receipt"})

    monkeypatch.setattr(notifications.httpx, "post", postmark_post)
    s = dataclasses.replace(settings, postmark_token="test-token", email_from="reservations@test.example",
                            email_allowlist=("owner@test.example",))
    notifications.deliver_pending(tx, s)
    receipt = next(m for m in delivered if "Confirmed:" in m["Subject"])
    assert receipt["To"] == "owner@test.example" and result["trip_url"] in receipt["TextBody"]
    with tx() as conn:
        row = conn.execute("SELECT status, sent_at FROM outbox WHERE booking_id = %s AND kind = 'confirmed'", (b["id"],)).fetchone()
    assert row["status"] == "sent" and row["sent_at"] is not None
    assert "Mock trip email delivery" in admin.get("/admin").text
