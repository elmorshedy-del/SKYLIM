"""Runtime configuration, read once from environment variables.

Nothing secret has a default. Production-only checks live in `launch_gates()`:
if a gate fails, the site keeps running as a truthful quote-request service and
online payment stays off — it never pretends to be live.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlparse
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

    # analytics (all optional; nothing loads unless set)
    gtm_container_id: str             # GTM-XXXXXXX — loads Google Tag Manager on the marketing site
    ga4_measurement_id: str           # G-XXXXXXX — direct GA4 (if no GTM) and server-side Measurement Protocol
    ga4_api_secret: str               # Measurement Protocol secret for server-side purchase/refund events

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
        gtm_container_id=_str("GTM_CONTAINER_ID"),
        ga4_measurement_id=_str("GA4_MEASUREMENT_ID"),
        ga4_api_secret=_str("GA4_API_SECRET"),
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
        ("Stripe webhook connected", webhook_secret(s).startswith("whsec_"),
         "Automatic a minute after STRIPE_SECRET_KEY is set (or set STRIPE_WEBHOOK_SECRET by hand)"),
        ("HTTPS public URL", s.public_base_url.startswith("https://"), s.public_base_url),
        ("Public URL is the canonical domain", on_canonical_domain(s),
         f"PUBLIC_BASE_URL must be https://{data.BRAND['domain']} — canonical tags and the sitemap use it"),
        ("Admin password set", s.admin_password_hash.startswith("scrypt$"), "ADMIN_PASSWORD_HASH"),
        ("Secret key set", len(s.secret_key) >= 32 and s.secret_key != "dev-only-not-secret", "SECRET_KEY >= 32 chars"),
        ("Owner test trip switched off", not data.TEST_TRIP.get("enabled"),
         "Set TEST_TRIP['enabled'] = False in data.py once the $1 test has passed"),
        ("Transactional email configured", bool(s.postmark_token and s.email_from),
         "Recommended, not required: until POSTMARK_SERVER_TOKEN / EMAIL_FROM are set, clients get Stripe's "
         "receipt and their on-screen trip page, and trip emails wait in /admin to be sent by hand"),
    ]
    return [(n, bool(ok), d) for (n, ok, d) in gates]


# Webhook signing secrets the site provisioned itself (services/stripe_setup.py), one per key mode and URL.
_WEBHOOK_SECRETS: dict[str, str] = {}


def webhook_secret_slot(s: Settings) -> str:
    return ("live" if s.stripe_live else "test") + ":" + s.public_base_url.rstrip("/")


def register_webhook_secret(s: Settings, secret: str) -> None:
    _WEBHOOK_SECRETS[webhook_secret_slot(s)] = secret


def webhook_secret(s: Settings | None = None) -> str:
    """STRIPE_WEBHOOK_SECRET if set, otherwise the secret the site obtained when it registered its endpoint."""
    s = s or get_settings()
    return s.stripe_webhook_secret or _WEBHOOK_SECRETS.get(webhook_secret_slot(s), "")


# Shown in /admin but not required to take payment: without them the site degrades gracefully.
RECOMMENDED_GATES = frozenset({"Transactional email configured", "Owner test trip switched off"})


def payments_possible(s: Settings | None = None) -> bool:
    """Payment can technically be taken: switched on, key and webhook in place — and a live key is
    refused outright outside production, so staging can never take real money. Launch gates are not
    considered here; the owner's test trip relies on exactly this."""
    s = s or get_settings()
    if not s.payments_enabled or not s.stripe_secret_key or not webhook_secret(s):
        return False
    return s.is_production or not s.stripe_live


def payments_live(s: Settings | None = None) -> bool:
    """Clients may pay online: payment is possible and, in production, every required launch gate passes."""
    s = s or get_settings()
    if not payments_possible(s):
        return False
    return not s.is_production or all(ok for (name, ok, _) in launch_gates(s) if name not in RECOMMENDED_GATES)


def on_canonical_domain(s: Settings) -> bool:
    """PUBLIC_BASE_URL is the brand's own domain (canonical tags and the sitemap point there)."""
    import data
    return (urlparse(s.public_base_url).hostname or "").removeprefix("www.") == data.BRAND["domain"].removeprefix("www.")
