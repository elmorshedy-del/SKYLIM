# Architecture

```
data.py                 business source of truth (brand, places, services, pricing inputs, voice, FAQs)
build.py + marketing/   static homepage generator → index.html, pricing.md, robots.txt, sitemap.xml
static/                 tokens.css (design tokens) · site.css/js (homepage) · app.css · trip.js · fonts
app/
  main.py               app factory: middleware (security headers, gzip), error mapping, background sweeper
  config.py             settings from environment + launch gates + payments_live()
  db.py                 connection pool, transactions, migrations, fleet seed
  security.py           opaque tokens, scrypt admin password, signed admin session
  errors.py             domain errors → HTTP status codes
  domain/               PURE business rules — no I/O, fully unit-testable
    catalog.py          typed, validated view of data.py
    geo.py, rates.py    drive-time model and the pricing cost model (shared with tools/rate_model.py)
    pricing.py          quote decisions: price, eligibility, authority class, capacity, service window
    status.py           booking state machine
    preferences.py      cabin preferences
    tracking.py         Traccar payload parsing
  services/             transactions and side effects, one module per concern
    quotes · bookings · availability · payments · tracking · notifications · analytics · insights · flags
  web/                  thin HTTP layer: public_api · trips · admin · integrations · site · deps
  templates/            server-rendered pages (trip, share, admin, policies)
migrations/             numbered SQL; guarantees live here (exclusion constraints, uniqueness)
tests/                  pytest against real PostgreSQL (59 tests)
tools/rate_model.py     pricing proposal for owner review
```

## Invariants and where they are enforced

| Invariant | Enforcement |
|---|---|
| A vehicle or chauffeur never holds two overlapping reservations | GiST exclusion constraints on `reservations` |
| The browser never sets a price | Request models reject unknown fields; amount comes from the stored quote |
| Payment confirmed only by a verified, matching, first-seen Stripe event | `services/payments.py`, `stripe_events` primary key |
| Test events never confirm production bookings (and vice versa) | livemode check in `handle_event` |
| One email / analytics event per business event | transactional outboxes with unique dedupe keys |
| Location only during an active trip, never before En route, deleted after | `services/tracking.py`, `bookings.advance/cancel` |
| Customer links are unguessable and stored only as hashes | `security.trip_token`, `token_hash` |
| Payments off in production until launch gates pass | `config.payments_live()` |

## Request lifecycle

`POST /api/quotes` → `domain.pricing.decide_quote` (+ `availability.check`) → stored quote →
`POST /api/bookings` → `services.bookings.create` → instant: hold + `payments.start_checkout` → Stripe →
`POST /api/webhooks/stripe` → `confirm_paid` (receipt email + GA4 purchase via outboxes) →
`/admin` status taps → `/trip/{token}` live view → completed (location deleted, review request).

## Extending

- **Second vehicle/chauffeur**: insert rows in `vehicles`/`drivers`; extend `approve()` to pick a free
  resource (the exclusion constraints already work per resource).
- **New service area**: add a place to `data.PLACES`; authority rules apply automatically.
- **Corporate accounts** (later): `inquiries.kind = 'corporate'` exists; add an `accounts` table and invoicing.
- **Address autocomplete / exact routing**: add a provider behind `domain/geo.py`'s interface.
