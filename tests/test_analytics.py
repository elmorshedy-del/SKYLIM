"""Conversion tracking: one server-side purchase per paid reservation, safe tag injection."""
from __future__ import annotations

from dataclasses import replace

from app.db import tx
from app.web.site import analytics_snippet
from tests.test_payments import approved_booking, session_event, signed, status_of


def test_purchase_recorded_once_with_attribution(now, gw):
    b, _, _ = approved_booking(now, gw)
    with tx() as conn:
        conn.execute("""UPDATE bookings SET attribution = '{"ga_client_id": "123.456", "utm_source": "google"}'
                        WHERE id = %s""", (b["id"],))
    event = session_event("cs_test_1", status_of(b["id"]))
    from app.services import payments
    payments.handle_event(*signed(event), now=now)
    event["id"] = "evt_retry_other_id"
    payments.handle_event(*signed(event), now=now)
    with tx() as conn:
        rows = conn.execute("SELECT payload FROM analytics_outbox").fetchall()
    assert len(rows) == 1
    payload = rows[0]["payload"]
    assert payload["client_id"] == "123.456"
    purchase = payload["events"][0]
    assert purchase["name"] == "purchase" and purchase["params"]["transaction_id"] == b["ref"]
    assert purchase["params"]["value"] == b["amount_cents"] / 100
    assert purchase["params"]["campaign_source"] == "google"


def test_tag_ids_are_validated_before_injection(settings):
    assert analytics_snippet(replace(settings, gtm_container_id="", ga4_measurement_id="")) == ""
    evil = replace(settings, gtm_container_id="GTM-ABC'</script><script>alert(1)//")
    assert analytics_snippet(evil) == ""
    gtm = analytics_snippet(replace(settings, gtm_container_id="GTM-ABC1234"))
    assert "GTM-ABC1234" in gtm and "consent" in gtm and "globalPrivacyControl" in gtm
    ga4 = analytics_snippet(replace(settings, gtm_container_id="", ga4_measurement_id="G-XYZ12345"))
    assert "gtag/js?id=G-XYZ12345" in ga4 and "__mrDirectGA" in ga4


def test_homepage_served_compressed(client):
    r = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200 and r.headers.get("content-encoding") == "gzip"
    assert "<!--ANALYTICS-->" not in r.text
