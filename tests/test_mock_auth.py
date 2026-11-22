"""Owner-only mock capability, without requiring a database connection."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.security import hash_password, make_admin_session, make_mock_session, read_admin_session, read_mock_session


@pytest.fixture
def web_only(monkeypatch):
    for key, value in {
        "APP_ENV": "test", "PUBLIC_BASE_URL": "https://test.example",
        "SECRET_KEY": "mock-capability-test-secret-not-for-production",
        "ADMIN_PASSWORD_HASH": hash_password("test owner password", n=2**10),
        "OWNER_EMAIL": "owner@test.example", "PAYMENTS_ENABLED": "true",
        "STRIPE_SECRET_KEY": "sk_test_dummy", "STRIPE_WEBHOOK_SECRET": "whsec_test_dummy",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    from app.main import create_app
    from app.web.deps import limiter
    limiter.reset()
    client = TestClient(create_app(), base_url="https://test.example")
    yield client
    client.close()
    get_settings.cache_clear()


def test_mock_option_is_owner_only_and_revoked_on_logout(web_only):
    assert web_only.get("/api/config").json()["mock_enabled"] is False
    r = web_only.post("/admin/login", data={"password": "test owner password"},
                      headers={"Origin": "https://test.example"}, follow_redirects=False)
    assert r.status_code == 303
    cfg = web_only.get("/api/config")
    assert cfg.json()["mock_enabled"] is True
    assert cfg.headers["cache-control"] == "no-store"
    web_only.post("/admin/logout", headers={"Origin": "https://test.example"}, follow_redirects=False)
    assert web_only.get("/api/config").json()["mock_enabled"] is False


def test_mock_capability_is_not_an_admin_session(web_only):
    assert not read_admin_session(make_mock_session())
    assert not read_mock_session(make_admin_session())


def test_mock_quote_rejects_cross_origin_even_when_owner_is_signed_in(web_only):
    web_only.post("/admin/login", data={"password": "test owner password"},
                  headers={"Origin": "https://test.example"}, follow_redirects=False)
    r = web_only.post("/api/quotes", headers={"Origin": "https://elsewhere.example"}, json={
        "origin": "bergen", "destination": "jfk", "pickup_local": "2026-11-25T06:30",
        "passengers": 1, "large_bags": 0, "mock": True})
    assert r.status_code == 403


def test_anonymous_mock_quote_is_rejected_before_any_database_access(web_only):
    r = web_only.post("/api/quotes", json={"origin": "bergen", "destination": "jfk",
        "pickup_local": "2026-11-25T06:30", "passengers": 1, "large_bags": 0, "mock": True})
    assert r.status_code == 403
