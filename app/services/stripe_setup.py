"""The site connects itself to Stripe: it registers its own webhook endpoint and keeps the secret.

The owner sets only STRIPE_SECRET_KEY (with PAYMENTS_ENABLED=true). On start-up the site creates its
endpoint at PUBLIC_BASE_URL/api/webhooks/stripe for exactly the events it handles, stores the signing
secret encrypted in PostgreSQL (key derived from SECRET_KEY) and loads it into memory, so payment
confirmations verify from the first booking. If Stripe is unreachable at boot, the background sweep
retries every few minutes.

Rules:
  * STRIPE_WEBHOOK_SECRET, if set, always wins (manual setup keeps working) and nothing is created.
  * Only endpoints tagged metadata.managed_by = MANAGER are ever changed or deleted — and only the
    ones for this site's own URL, so staging and production can share a Stripe account.
  * Live and test keys, and each public URL, have their own endpoint and secret.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import time

import stripe
from cryptography.fernet import Fernet, InvalidToken

from .. import db
from ..config import Settings, get_settings, register_webhook_secret, webhook_secret, webhook_secret_slot

log = logging.getLogger("celeste.stripe")

EVENTS = sorted(["checkout.session.completed", "checkout.session.async_payment_succeeded",
                 "checkout.session.async_payment_failed", "checkout.session.expired", "charge.refunded"])
MANAGER = "celeste-site"
PATH = "/api/webhooks/stripe"
RETRY_SECONDS = 600


def webhook_url(s: Settings) -> str:
    return s.public_base_url.rstrip("/") + PATH


def _box(s: Settings) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"app-secrets|" + s.secret_key.encode()).digest()))


def _name(s: Settings) -> str:
    return "stripe_webhook:" + webhook_secret_slot(s)


def _load(conn, s: Settings) -> dict | None:
    row = conn.execute("SELECT ciphertext FROM app_secrets WHERE name = %s", (_name(s),)).fetchone()
    if not row:
        return None
    try:
        return json.loads(_box(s).decrypt(row["ciphertext"].encode()))
    except (InvalidToken, ValueError):     # SECRET_KEY changed or data damaged: provision afresh
        return None


def _save(conn, s: Settings, record: dict) -> None:
    conn.execute("INSERT INTO app_secrets (name, ciphertext, updated_at) VALUES (%s, %s, now()) "
                 "ON CONFLICT (name) DO UPDATE SET ciphertext = EXCLUDED.ciphertext, updated_at = now()",
                 (_name(s), _box(s).encrypt(json.dumps(record).encode()).decode()))


class StripeEndpoints:
    """The four webhook-endpoint calls the site needs (replaced by a fake in tests)."""

    def __init__(self, secret_key: str):
        self._api = stripe.StripeClient(secret_key).v1.webhook_endpoints

    def list(self) -> list[dict]:
        return [{"id": e.id, "url": e.url, "status": e.status, "events": sorted(e.enabled_events),
                 "metadata": dict(e.metadata or {})}
                for e in self._api.list(params={"limit": 100}).auto_paging_iter()]

    def create(self, url: str, events: list[str], metadata: dict, description: str) -> dict:
        e = self._api.create(params={"url": url, "enabled_events": events, "metadata": metadata,
                                     "description": description})
        return {"id": e.id, "secret": e.secret}

    def update(self, endpoint_id: str, events: list[str]) -> None:
        self._api.update(endpoint_id, params={"enabled_events": events})

    def delete(self, endpoint_id: str) -> None:
        self._api.delete(endpoint_id)


endpoints_factory = StripeEndpoints


def connect(s: Settings | None = None, api=None) -> str:
    """Make sure this site's endpoint exists, is enabled, has the right events and a known secret.

    Returns "manual", "off", "live_key_outside_production", "needs_https", "ok" or "created".
    """
    s = s or get_settings()
    if s.stripe_webhook_secret:
        return "manual"
    if not (s.payments_enabled and s.stripe_secret_key):
        return "off"
    if s.stripe_live and not s.is_production:
        return "live_key_outside_production"     # staging never touches the live account
    if not s.public_base_url.startswith("https://"):
        return "needs_https"
    url = webhook_url(s)
    with db.tx() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('stripe_webhook_setup'))")
        record = _load(conn, s)
        api = api or endpoints_factory(s.stripe_secret_key)
        mine = [e for e in api.list() if e["metadata"].get("managed_by") == MANAGER and e["url"] == url]
        current = next((e for e in mine if record and e["id"] == record["id"]), None)
        if current and current["status"] == "enabled":
            if current["events"] != EVENTS:
                api.update(current["id"], EVENTS)
            register_webhook_secret(s, record["secret"])
            return "ok"
        for e in mine:                       # ours, but disabled or its secret is unknown: replace it
            api.delete(e["id"])
        created = api.create(url, EVENTS, {"managed_by": MANAGER},
                             "Website payment confirmations (managed by the site; do not edit)")
        _save(conn, s, created)
    register_webhook_secret(s, created["secret"])
    log.info("stripe webhook endpoint created for %s", url)
    return "created"


def load(s: Settings | None = None) -> bool:
    """At start-up: put a previously stored secret in memory (no network), so webhooks verify at once."""
    s = s or get_settings()
    if s.stripe_webhook_secret or not s.stripe_secret_key:
        return False
    with db.tx() as conn:
        record = _load(conn, s)
    if record:
        register_webhook_secret(s, record["secret"])
    return bool(record)


_state = {"checked": False, "last_attempt": 0.0}


def maintain() -> None:
    """Called by the background sweep: verify once per process, then retry only while unconnected."""
    s = get_settings()
    if not (s.payments_enabled and s.stripe_secret_key) or s.stripe_webhook_secret:
        return
    if s.stripe_live and not s.is_production:
        return
    if _state["checked"] and webhook_secret(s):
        return
    if _state["last_attempt"] and time.monotonic() - _state["last_attempt"] < RETRY_SECONDS:
        return
    _state["last_attempt"] = time.monotonic()
    try:
        log.info("stripe webhook: %s", connect(s))
        _state["checked"] = True
    except Exception:                        # Stripe or network down: the next window retries
        log.exception("stripe webhook setup failed")
