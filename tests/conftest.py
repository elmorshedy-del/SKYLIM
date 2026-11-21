"""Shared fixtures. Tests run against a real PostgreSQL database (never SQLite):
the double-booking guarantee lives in PostgreSQL exclusion constraints, so it
can only be proven there.

    TEST_DATABASE_URL=postgresql://user:pass@localhost/meridian_test pytest
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("TEST_DATABASE_URL", "postgresql://meridian:meridian@localhost/meridian_test")
os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": os.environ["TEST_DATABASE_URL"],
    "PUBLIC_BASE_URL": "https://test.example",
    "SECRET_KEY": "test-secret-key-that-is-long-enough-0123456789",
    "OWNER_EMAIL": "owner@test.example",
    "PAYMENTS_ENABLED": "true",
    "STRIPE_SECRET_KEY": "sk_test_dummy",
    "STRIPE_WEBHOOK_SECRET": "whsec_test_secret",
    "TRACKING_ENABLED": "true",
    "TRACKER_PHONE_ID": "phone-device-secret-123",
    "TRACKER_VEHICLE_ID": "car-tracker-secret-456",
    "TRACCAR_FORWARD_TOKEN": "forward-token-789",
    "MIN_NOTICE_MINUTES": "360",
    "HOLD_MINUTES": "360",
    "AUTO_MIGRATE": "false",
    "BACKGROUND_JOBS": "false",
})
ADMIN_TEST_PASSWORD = "correct horse battery staple"

import psycopg  # noqa: E402
import pytest  # noqa: E402

from app import db  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.security import hash_password  # noqa: E402

os.environ["ADMIN_PASSWORD_HASH"] = hash_password(ADMIN_TEST_PASSWORD, n=2**10)  # low work factor: tests only
get_settings.cache_clear()

NOW = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)   # Fri Nov 20 2026, 10:00 ET

DATA_TABLES = ["positions", "outbox", "analytics_outbox", "stripe_events", "payments", "reservations",
               "booking_events", "bookings", "quotes", "customers", "inquiries", "app_secrets"]


@pytest.fixture(scope="session", autouse=True)
def _schema():
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    db.migrate(url)
    yield
    db.close_pool()


@pytest.fixture(autouse=True)
def _clean():
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute("TRUNCATE " + ", ".join(DATA_TABLES) + " RESTART IDENTITY CASCADE")
        conn.execute("UPDATE vehicles SET plate = NULL, color = NULL")
        conn.execute("UPDATE flags SET enabled = true WHERE key = 'instant_booking'")
    yield


@pytest.fixture(autouse=True)
def gw():
    """Every test talks to a fake payment gateway, never to Stripe."""
    from app.services import payments
    from tests.fakes import FakeGateway

    fake = FakeGateway()
    payments.set_gateway(fake)
    yield fake
    payments.set_gateway(None)


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def client(now):
    """HTTP client with the clock frozen at NOW and rate limits reset."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.web.deps import clock, limiter

    limiter.reset()
    app.dependency_overrides[clock] = lambda: now
    with TestClient(app, base_url="https://test.example") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin(client):
    r = client.post("/admin/login", data={"password": ADMIN_TEST_PASSWORD},
                    headers={"Origin": "https://test.example"}, follow_redirects=False)
    assert r.status_code == 303, r.text
    client.headers.update({"Origin": "https://test.example"})
    return client
