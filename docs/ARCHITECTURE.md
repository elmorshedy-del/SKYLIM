# Architecture

```
data.py                 business source of truth (brand, places, services, pricing inputs, voice, FAQs)
landing_pages.py        copy and search targets for the landing pages (prices filled from the cost model)
build.py + marketing/   static site generator → index.html, pages/**.html, pricing.md, robots.txt,
                        sitemap.xml, seo_lastmod.json, static/favicon.svg (seo.py: titles, JSON-LD,
                        sitemap; landing.py: pages; brand.py: the logo — wordmark, lockup, animation)
static/                 tokens.css (design tokens) · site.css/js (homepage) · app.css · trip.js · fonts
app/
  main.py               app factory: middleware (security headers, gzip), error mapping, background sweeper
  config.py             settings from environment + launch gates + payments_live()
  db.py                 connection pool, transactions, migrations, fleet seed
  security.py           opaque tokens, scrypt admin password, signed admin and API-scoped mock sessions
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
tests/                  pytest against real PostgreSQL (68 tests, incl. SEO guardrails)
tools/rate_model.py     pricing proposal for owner review
tools/make_brand.py     outlines the logo lettering (Pinyon Script, Jost; SIL OFL) → static/brand/*.svg
tools/make_images.py    renders static/og.png (share image) and static/logo.png from the logo
```

## Invariants and where they are enforced

| Invariant | Enforcement |
|---|---|
| A vehicle or chauffeur never holds two overlapping reservations | GiST exclusion constraints on `reservations` |
| A trip is offered only if the chauffeur can get there from the previous drop-off (and on to the next pickup) | `availability.fit`, re-run by `bookings.approve` under a per-chauffeur advisory lock |
| A time inside the buffer for the unpredictable is never charged instantly — the owner confirms it | `fit` → "tight"; instant path refuses it (`needs_owner`) and falls back to a request |
| The browser never sets a price | Request models reject unknown fields; amount comes from the stored quote |
| Payment confirmed only by a verified, matching, first-seen Stripe event | `services/payments.py`, `stripe_events` primary key |
| Test events never confirm production bookings (and vice versa) | livemode check in `handle_event` |
| One email / analytics event per business event | transactional outboxes with unique dedupe keys |
| Location only during an active trip, never before En route, deleted after | `services/tracking.py`, `bookings.advance/cancel` |
| Customer links are unguessable and stored only as hashes | `security.trip_token`, `token_hash` |
| Payments off in production until launch gates pass | `config.payments_live()` |
| A landing page never advertises a journey we cannot sell online | `tests/test_seo.py` (authority check on every listed route and price token) |
| The owner's mock never blocks a client or counts as revenue | hidden test vehicle/driver; `quotes.is_test` / `bookings.is_test` excluded from analytics, Ads export and funnel |
| Only the authenticated owner can use a $1 mock quote | `/api`-scoped mock cookie, same-origin validation, stored quote mode, owner/allowlisted email |
| A real trip always wins over an active mock for the owner's tracker | `services/tracking.py` chooses the registered device's real active booking first; only the isolated owner test resources are eligible as a fallback |
| Staging is never indexed by search engines | `X-Robots-Tag: noindex` unless production on the brand's own domain (`main.py`) |

## Request lifecycle

`POST /api/quotes` → `domain.pricing.decide_quote` (+ `availability.check`) → stored quote →
`POST /api/bookings` → `services.bookings.create` → instant: hold + `payments.start_checkout` → Stripe →
`POST /api/webhooks/stripe` → `confirm_paid` (receipt email + GA4 purchase via outboxes) →
`/admin` status taps → `/trip/{token}` live view → completed (location deleted, review request).

The website's mock checkbox selects the same lifecycle. The quote persists the owner-only mock mode and
server-set amount; approval uses the existing test resources. Confirmation and status emails use the normal
outbox, and the real registered tracker feeds the mock only while no real trip is active. The admin's mock
email status view reports provider acceptance/failure; it does not simulate delivery.

## Extending

- **Second vehicle/chauffeur**: insert rows in `vehicles`/`drivers`; extend `approve()` to pick a free
  resource (the exclusion constraints already work per resource).
- **New service area**: add a place to `data.PLACES`; authority rules apply automatically.
- **New landing page**: add a dict to `landing_pages.py` and to `PAGES`, link it from a related page or the
  footer (`sections.FOOTER_GROUPS`), run `python3 build.py && pytest tests/test_seo.py`. The route, sitemap
  entry, breadcrumbs and structured data follow automatically.
- **Corporate accounts** (later): `inquiries.kind = 'corporate'` exists; add an `accounts` table and invoicing.
- **Address autocomplete / exact routing**: add a provider behind `domain/geo.py`'s interface.
