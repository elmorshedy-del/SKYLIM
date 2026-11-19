"""Runtime configuration, read once from environment variables.

Nothing secret has a default. Production-only checks live in `launch_gates()`:
if a gate fails, the site keeps running as a truthful quote-request service and
online payment stays off — it never pretends to be live.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/New_York")


def _bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    v = os.environ.get(name)
    return int(v) if v not in (None, "") else default


def _str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _list(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(x.strip().lower() for x in _str(name, default).split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    app_env: str                      # development | staging | production
    database_url: str
    public_base_url: str              # https://example.com — used in emails and Stripe return URLs
    secret_key: str                   # signs the admin session cookie
    admin_password_hash: str          # scrypt$... from `python -m app.security hash-password`
    owner_email: str                  # where new-request alerts go

    # payments
    payments_enabled: bool
    stripe_secret_key: str
    stripe_webhook_secret: str
    # Checkout uses Stripe's *dynamic* payment methods: whatever is switched on in the
    # Dashboard (cards, Apple Pay, Google Pay, Link; Affirm/Klarna/Afterpay or PayPal once
    # approved) appears with no code change. Optionally pin a payment method configuration.
    stripe_payment_method_configuration: str
    stripe_excluded_methods: tuple[str, ...]   # delayed bank debits don't suit a short hold
    payment_methods_display: tuple[str, ...]   # what the website may mention — keep in sync with Dashboard
    hold_minutes: int                 # how long an owner-approved slot waits for payment
    instant_hold_minutes: int         # how long an instant reservation holds the slot during checkout
    min_notice_minutes: int           # earliest pickup accepted as a request
    instant_min_notice_minutes: int   # earliest pickup that can be reserved instantly (no approval)
    max_daily_minutes: int            # cap on committed vehicle time per local day (one chauffeur)
    max_advance_days: int
    quote_ttl_minutes: int
    free_cancel_hours: int            # customer cancellation with automatic full refund

    # tracking
    tracking_enabled: bool
    tracker_phone_id: str             # Traccar Client "device identifier" on the chauffeur's phone (secret)
    tracker_vehicle_id: str           # uniqueId of an in-car tracker forwarded by a Traccar server (secret)
    traccar_forward_token: str        # shared secret the Traccar server sends with forwarded positions
    stale_after_seconds: int
    tracking_retention_hours: int     # 0 = delete positions as soon as the trip ends
    map_tile_url: str
    map_attribution: str


    # email
    postmark_token: str
    email_from: str
    email_allowlist: tuple[str, ...]  # staging: only these addresses ever receive mail

    legal_pages_approved: bool
    trust_proxy_headers: bool
    extra: dict = field(default_factory=dict)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def stripe_live(self) -> bool:
        return self.stripe_secret_key.startswith(("sk_live_", "rk_live_"))

    @property
    def cookie_secure(self) -> bool:
        return self.public_base_url.startswith("https://")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env = _str("APP_ENV", "development")
    return Settings(
        app_env=env,
        database_url=_str("DATABASE_URL", "postgresql://meridian:meridian@localhost/meridian_dev"),
        public_base_url=_str("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
        secret_key=_str("SECRET_KEY", "dev-only-not-secret" if env == "development" else ""),
        admin_password_hash=_str("ADMIN_PASSWORD_HASH"),
        owner_email=_str("OWNER_EMAIL"),
        payments_enabled=_bool("PAYMENTS_ENABLED", False),
        stripe_secret_key=_str("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=_str("STRIPE_WEBHOOK_SECRET"),
        stripe_payment_method_configuration=_str("STRIPE_PAYMENT_METHOD_CONFIGURATION"),
        stripe_excluded_methods=_list("STRIPE_EXCLUDED_METHODS", "us_bank_account"),
        payment_methods_display=_list("PAYMENT_METHODS_DISPLAY", "card,apple_pay,google_pay,link"),
        hold_minutes=_int("HOLD_MINUTES", 360),
        instant_hold_minutes=_int("INSTANT_HOLD_MINUTES", 35),
        min_notice_minutes=_int("MIN_NOTICE_MINUTES", 180),
        instant_min_notice_minutes=_int("INSTANT_MIN_NOTICE_MINUTES", 480),
        max_daily_minutes=_int("MAX_DAILY_MINUTES", 660),
        max_advance_days=_int("MAX_ADVANCE_DAYS", 180),
        quote_ttl_minutes=_int("QUOTE_TTL_MINUTES", 45),
        free_cancel_hours=_int("FREE_CANCEL_HOURS", 24),
        tracking_enabled=_bool("TRACKING_ENABLED", False),
        tracker_phone_id=_str("TRACKER_PHONE_ID"),
        tracker_vehicle_id=_str("TRACKER_VEHICLE_ID"),
        traccar_forward_token=_str("TRACCAR_FORWARD_TOKEN"),
        stale_after_seconds=_int("STALE_AFTER_SECONDS", 60),
        tracking_retention_hours=_int("TRACKING_RETENTION_HOURS", 0),
        map_tile_url=_str("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
        map_attribution=_str("MAP_ATTRIBUTION", "&copy; OpenStreetMap contributors"),
        postmark_token=_str("POSTMARK_SERVER_TOKEN"),
        email_from=_str("EMAIL_FROM"),
        email_allowlist=_list("EMAIL_ALLOWLIST"),
        legal_pages_approved=_bool("LEGAL_PAGES_APPROVED", False),
        trust_proxy_headers=_bool("TRUST_PROXY_HEADERS", True),
    )


def launch_gates(s: Settings | None = None) -> list[tuple[str, bool, str]]:
    """Every check that must pass before real money is taken.

    Returns (name, passed, detail). The admin dashboard shows this list;
    `payments_live()` refuses to take payment while any gate fails in production.
    """
    import data  # local import: data.py lives at the repository root

    s = s or get_settings()
    brand_blob = " ".join(str(v) for v in data.BRAND.values())
    placeholders = [m for m in ("555-0100", "XXXX", "PLACEHOLDER", "TO CONFIRM") if m in brand_blob]
    gates = [
        ("Business contact details are real",
         not placeholders and not data.BRAND.get("placeholder", False),
         "data.py BRAND still contains: " + ", ".join(placeholders) if placeholders else "ok"),
        ("Operating authority and insurance confirmed by owner",
         bool(data.OPERATIONS.get("authority_confirmed")),
         "Set OPERATIONS['authority_confirmed'] only after the municipal limousine licence, "
         "N.J.S.A. 48:16 insurance filing and any federal registration are in hand"),
        ("Vehicle capacity tested",
         bool(data.VEHICLE.get("capacity_tested")),
         "Run the luggage test and set VEHICLE['capacity_tested'] = True"),
        ("Cancellation policy approved", bool(data.POLICY.get("approved")), data.POLICY["version"]),
        ("Legal pages approved", s.legal_pages_approved, "LEGAL_PAGES_APPROVED"),
        ("Stripe live key configured", s.stripe_live, "STRIPE_SECRET_KEY must be sk_live_/rk_live_"),
        ("Stripe webhook secret configured", s.stripe_webhook_secret.startswith("whsec_"), "STRIPE_WEBHOOK_SECRET"),
        ("HTTPS public URL", s.public_base_url.startswith("https://"), s.public_base_url),
        ("Admin password set", s.admin_password_hash.startswith("scrypt$"), "ADMIN_PASSWORD_HASH"),
        ("Secret key set", len(s.secret_key) >= 32 and s.secret_key != "dev-only-not-secret", "SECRET_KEY >= 32 chars"),
        ("Transactional email configured", bool(s.postmark_token and s.email_from), "POSTMARK_SERVER_TOKEN / EMAIL_FROM"),
    ]
    return [(n, bool(ok), d) for (n, ok, d) in gates]


def payments_live(s: Settings | None = None) -> bool:
    """Online payment is offered only when explicitly enabled, keys exist, and —
    in production — every launch gate passes. Staging must use test keys."""
    s = s or get_settings()
    if not s.payments_enabled or not s.stripe_secret_key or not s.stripe_webhook_secret:
        return False
    if s.is_production:
        return all(ok for (_, ok, _) in launch_gates(s))
    # Outside production a live key is refused outright: staging can never take real money.
    return not s.stripe_live
