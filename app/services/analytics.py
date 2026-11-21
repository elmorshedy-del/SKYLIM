"""Server-side conversion tracking.

The browser reports the funnel up to the payment page; the *purchase* is
recorded here, from the verified Stripe webhook, so it is never lost to an
ad-blocker, a closed tab or a double-counted reload. Events go to the GA4
Measurement Protocol with the visitor's GA client id (captured at reservation),
which ties revenue back to the ad, search or referral that produced it.
"""
from __future__ import annotations

import logging
import uuid

import httpx
import psycopg
from psycopg.types.json import Jsonb

from ..config import Settings, get_settings

log = logging.getLogger("celeste.analytics")
MP_URL = "https://www.google-analytics.com/mp/collect"


def _client_id(booking: dict) -> str:
    """GA client id from the reservation, or a stable synthetic one (revenue still counts, unattributed)."""
    cid = (booking.get("attribution") or {}).get("ga_client_id")
    return cid or f"{uuid.UUID(str(booking['id'])).int % 10**10}.{int(booking['created_at'].timestamp())}"


def _item(booking: dict, value: float) -> dict:
    return {"item_id": f"{booking['service']}", "item_name": "Chauffeured journey" if booking["service"] == "transfer"
            else f"Chauffeur by the hour ({booking['hours']} h)", "price": value, "quantity": 1}


def enqueue_purchase(conn: psycopg.Connection, booking: dict, paid_cents: int) -> None:
    if booking.get("is_test"):                 # the owner's test trip is never revenue
        return
    value = paid_cents / 100
    attribution = booking.get("attribution") or {}
    payload = {"client_id": _client_id(booking), "events": [{"name": "purchase", "params": {
        "transaction_id": booking["ref"], "currency": "USD", "value": value, "items": [_item(booking, value)],
        "booking_type": "instant" if booking.get("instant") else "approved",
        "campaign_source": attribution.get("utm_source"), "campaign_medium": attribution.get("utm_medium"),
        "campaign_name": attribution.get("utm_campaign")}}]}
    _enqueue(conn, f"purchase:{booking['id']}", payload)


def enqueue_refund(conn: psycopg.Connection, booking: dict, payment_id, refunded_total_cents: int,
                   delta_cents: int) -> None:
    if booking.get("is_test"):
        return
    payload = {"client_id": _client_id(booking), "events": [{"name": "refund", "params": {
        "transaction_id": booking["ref"], "currency": "USD", "value": delta_cents / 100}}]}
    _enqueue(conn, f"refund:{payment_id}:{refunded_total_cents}", payload)


def _enqueue(conn: psycopg.Connection, key: str, payload: dict) -> None:
    conn.execute("""INSERT INTO analytics_outbox (dedupe_key, destination, payload) VALUES (%s, 'ga4', %s)
                    ON CONFLICT (dedupe_key) DO NOTHING""", (key, Jsonb(payload)))


def deliver_pending(conn_factory, s: Settings | None = None, limit: int = 50) -> int:
    s = s or get_settings()
    sent = 0
    with conn_factory() as conn:
        rows = conn.execute("""SELECT * FROM analytics_outbox WHERE status = 'pending' AND attempts < 5
                               ORDER BY created_at LIMIT %s FOR UPDATE SKIP LOCKED""", (limit,)).fetchall()
        for row in rows:
            status, error = _send(row, s)
            conn.execute("""UPDATE analytics_outbox SET status = %s, attempts = attempts + 1, last_error = %s,
                                sent_at = CASE WHEN %s = 'sent' THEN now() ELSE sent_at END WHERE id = %s""",
                         (status, error, status, row["id"]))
            sent += status == "sent"
    return sent


def _send(row: dict, s: Settings) -> tuple[str, str | None]:
    if not (s.ga4_measurement_id and s.ga4_api_secret):
        return "skipped", "GA4 Measurement Protocol not configured"
    if not s.is_production:
        return "skipped", "server-side analytics only sent in production"
    try:
        r = httpx.post(MP_URL, params={"measurement_id": s.ga4_measurement_id, "api_secret": s.ga4_api_secret},
                       json=row["payload"], timeout=10)
        return ("sent", None) if r.status_code < 300 else ("pending", f"GA4 {r.status_code}")
    except httpx.HTTPError as e:
        return "pending", f"network: {e}"[:300]
