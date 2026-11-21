"""The site connects itself to Stripe: endpoint registration, encrypted secret, verification."""
from __future__ import annotations

import dataclasses
import hashlib
import hmac
import json
import time

import psycopg
import pytest

from app import config
from app.services import payments, stripe_setup
from app.services.stripe_setup import EVENTS, MANAGER


class FakeEndpoints:
    def __init__(self, existing=None):
        self.items = list(existing or [])
        self.calls = []
        self.n = 0

    def list(self):
        self.calls.append("list")
        return [dict(e) for e in self.items]

    def create(self, url, events, metadata, description):
        self.calls.append("create")
        self.n += 1
        e = {"id": f"we_{self.n}", "url": url, "status": "enabled", "events": sorted(events),
             "metadata": metadata, "secret": f"whsec_fake_{self.n}"}
        self.items.append(e)
        return {"id": e["id"], "secret": e["secret"]}

    def update(self, endpoint_id, events):
        self.calls.append("update")
        next(e for e in self.items if e["id"] == endpoint_id)["events"] = sorted(events)

    def delete(self, endpoint_id):
        self.calls.append(f"delete:{endpoint_id}")
        self.items = [e for e in self.items if e["id"] != endpoint_id]


@pytest.fixture(autouse=True)
def _fresh_memory():
    config._WEBHOOK_SECRETS.clear()
    yield
    config._WEBHOOK_SECRETS.clear()


@pytest.fixture
def auto(settings):
    """Settings as the owner leaves them: a key, no webhook secret."""
    return dataclasses.replace(settings, stripe_webhook_secret="")


def signed(secret: str, event: dict) -> tuple[bytes, str]:
    body = json.dumps(event).encode()
    t = int(time.time())
    sig = hmac.new(secret.encode(), f"{t}.{body.decode()}".encode(), hashlib.sha256).hexdigest()
    return body, f"t={t},v1={sig}"


def test_creates_endpoint_stores_secret_encrypted_and_verifies_webhooks(auto):
    api = FakeEndpoints()
    assert not config.payments_live(auto)                       # no secret yet: no online payment
    assert stripe_setup.connect(auto, api) == "created"
    ep = api.items[0]
    assert ep["url"] == "https://test.example/api/webhooks/stripe"
    assert ep["events"] == EVENTS and ep["metadata"] == {"managed_by": MANAGER}
    assert config.webhook_secret(auto) == ep["secret"] and config.payments_live(auto)

    with psycopg.connect(auto.database_url) as conn:
        stored = conn.execute("SELECT ciphertext FROM app_secrets").fetchone()[0]
    assert ep["secret"] not in stored                           # encrypted at rest

    body, header = signed(ep["secret"], {"id": "evt_1", "type": "ping"})
    assert payments.verify_and_parse(body, header, auto)["id"] == "evt_1"


def test_second_run_reuses_endpoint_and_restores_secret_after_restart(auto):
    api = FakeEndpoints()
    stripe_setup.connect(auto, api)
    config._WEBHOOK_SECRETS.clear()                             # a restart forgets memory...
    assert stripe_setup.load(auto)                              # ...start-up reloads it from the database
    assert config.webhook_secret(auto) == "whsec_fake_1"
    assert stripe_setup.connect(auto, api) == "ok"
    assert api.calls.count("create") == 1


def test_event_list_kept_in_sync(auto):
    api = FakeEndpoints()
    stripe_setup.connect(auto, api)
    api.items[0]["events"] = ["checkout.session.completed"]
    assert stripe_setup.connect(auto, api) == "ok"
    assert "update" in api.calls and api.items[0]["events"] == EVENTS


def test_only_its_own_endpoint_for_its_own_url_is_ever_replaced(auto):
    url = "https://test.example/api/webhooks/stripe"
    api = FakeEndpoints([
        {"id": "we_lost", "url": url, "status": "enabled", "events": EVENTS, "metadata": {"managed_by": MANAGER}},
        {"id": "we_owner", "url": url, "status": "enabled", "events": EVENTS, "metadata": {}},
        {"id": "we_prod", "url": "https://other.example/api/webhooks/stripe", "status": "enabled",
         "events": EVENTS, "metadata": {"managed_by": MANAGER}},
    ])
    assert stripe_setup.connect(auto, api) == "created"         # its secret is unknown: replace it
    assert "delete:we_lost" in api.calls
    assert {e["id"] for e in api.items} >= {"we_owner", "we_prod"}  # untouched


def test_manual_secret_wins_and_live_key_never_used_outside_production(settings, auto):
    api = FakeEndpoints()
    assert stripe_setup.connect(settings, api) == "manual" and api.calls == []
    live_staging = dataclasses.replace(auto, stripe_secret_key="rk_live_dummy", app_env="staging")
    assert stripe_setup.connect(live_staging, api) == "live_key_outside_production" and api.calls == []
    off = dataclasses.replace(auto, payments_enabled=False)
    assert stripe_setup.connect(off, api) == "off"


def test_live_and_test_keys_keep_separate_secrets(auto):
    live = dataclasses.replace(auto, stripe_secret_key="rk_live_dummy", app_env="production")
    stripe_setup.connect(auto, FakeEndpoints())
    assert config.webhook_secret(auto) and not config.webhook_secret(live)


def test_receipt_email_requested_from_stripe(settings):
    from datetime import datetime, timezone
    b = {"id": 1, "ref": "CL-TEST7K", "contact_email": "client@test.example", "amount_cents": 31500,
         "pickup_at": datetime(2026, 11, 25, 15, tzinfo=timezone.utc)}
    params = payments.checkout_params(b, expires_at=datetime(2026, 11, 22, tzinfo=timezone.utc), s=settings)
    assert params["payment_intent_data"]["receipt_email"] == "client@test.example"
    assert params["payment_intent_data"]["statement_descriptor_suffix"] == "CL-TEST7K"
    assert params["customer_creation"] == "always"
    assert params["managed_payments"] == {"enabled": False}
    assert "24 hours" in params["custom_text"]["submit"]["message"]
    assert params["branding_settings"]["icon"]["url"].endswith("/static/logo.png")


def test_email_gate_is_recommended_not_blocking(settings):
    names = {n for n, _, _ in config.launch_gates(settings)}
    assert config.RECOMMENDED_GATES <= names
