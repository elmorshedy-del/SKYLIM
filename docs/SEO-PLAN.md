# SEO, Local Search and Measurement Plan

Every rule below cites Google's own documentation; every keyword cites measured volume. Where data is
missing, it says so. Keyword research: owner's *Search demand and SEO launch plan* (Ubersuggest US English,
2026-11-21) — volumes are national estimates of overlapping variants, not additive demand or bookings.

## 1. Google's rules, and how the site follows them

| Google says (Search Central) | What the site does |
|---|---|
| A good title is "unique to the page, clear and concise, and accurately describes the contents"; avoid keyword stuffing; "brand your titles concisely" with a delimiter — *SEO Starter Guide*, *Influencing title links* | One distinct title per page, search phrase first, brand as a short ` \| Celeste` suffix. Tested: unique, 30–70 chars |
| Google uses "the main visual title, heading elements" for title links; make the main title "the first visible `<h1>`" — *Influencing title links* | Exactly one H1 per page, containing the page's search phrase. Home: the H1's small line reads "Chauffeur service · New York City & New Jersey" above the large brand line "Arrive composed." |
| Meta descriptions: "unique to one particular page"; "long strings of keywords… are less likely to be displayed" — *Meta descriptions* | A written summary per page, 90–170 chars, with real facts (met inside, flight followed, tolls and gratuity included) |
| Keyword stuffing includes "blocks of text that list cities and regions" and "repeating the same words… so often that it sounds unnatural" — *Spam policies* | No city lists. Each page's phrase appears in title, H1, description and a few natural places; density is tested ≤ 3 % (actual 0.4–2.3 %) |
| Doorway abuse: "pages targeted at specific regions or cities that funnel users to one page"; "substantially similar pages" — *Spam policies* | Seven pages, each for a different search intent, each with its own prices, pickup procedure, FAQs and booking form. No county or town pages |
| "Google Search doesn't use the keywords meta tag"; URL keywords have "hardly any effect" — *SEO Starter Guide* | No meta keywords. Short readable URLs chosen for people |
| Anchor text should be "descriptive, reasonably concise"; "every page you care about should have a link from at least one other page" — *Link best practices* | Header "Airports", an in-copy line on the home page ("See how pickups work at Newark, JFK, LaGuardia and Teterboro"), footer columns, breadcrumbs and "Where else we can take you" links. Tested: every page linked from another; every internal link resolves |
| Sitemaps: "Google ignores `<priority>` and `<changefreq>`"; uses `<lastmod>` only if "consistently and verifiably accurate" — *Build a sitemap*. "Changing the date of pages to make them seem fresh" is a warning sign — *Helpful content* | `changefreq` removed. Each URL's `lastmod` moves only when its content fingerprint changes (`seo_lastmod.json`) |
| LocalBusiness requires `name` and `address`; use the most specific subtype — *Local business structured data* | `LocalBusiness` with a region-only address (NJ, US) — a service-area business never publishes an invented street address. No ratings or reviews until real ones exist |
| WebSite structured data (`name`, `url`, `alternateName`) on the home page sets the site name — *Site names* | Home page: Organization (logo 512 × 512), WebSite, LocalBusiness, FAQPage. Landing pages: WebPage, BreadcrumbList, Service (with `Airport` + IATA code), FAQPage |
| People-first content: "original information", "first-hand expertise", content "useful… if they came directly to you" — *Helpful content* | Pages lead with what only we know: our live prices per journey, how our pickup works, what fits in the car. Prices come from the booking engine itself, so copy can never contradict checkout |

FAQ rich results are limited to government and health sites (Google, Aug 2023): FAQPage markup is kept for
understanding and AI answers, with no expectation of FAQ snippets.

## 2. Keyword map (what each page answers)

| Page | Primary phrase (title, H1, description) | Variants used naturally | Measured US searches/mo |
|---|---|---|---|
| `/` | private chauffeur service, New York & New Jersey | black car service (FAQ), Escalade | brand + broad |
| `/nyc-chauffeur-service` | chauffeur service NYC | car service NYC, black car service, limo service, executive | 8,100 · 6,600 · 6,600 · 5,400 · 4,400 · 1,300 |
| `/nj-limo-service` | limo service NJ | car service New Jersey, Jersey City, Hoboken, Princeton, "not a stretch" | 1,600 · 1,300 · 1,300 · 1,000 · 720 |
| `/airport-transfers/newark` | Newark Airport car service | car service from Newark Airport, EWR, to Manhattan, town car, limo | 2,400 · 1,900 · 1,600 · 1,300 · 1,000 · 1,000 · 880 |
| `/airport-transfers/jfk` | JFK airport car service | car service New Jersey to JFK, limousine | 880 · 720 · 720 · 590 |
| `/airport-transfers/laguardia` | LaGuardia Airport car service | car service from LaGuardia, LGA | 1,900 · 1,600 · 1,300 |
| `/airport-transfers/teterboro` | Teterboro car service | private aviation, FBO, tail number | volume gated (autocomplete-confirmed) |
| `/airport-transfers` | airport car service | Newark, JFK, LaGuardia, Teterboro, Morristown, Westchester, Philadelphia | hub for the hierarchy |

Copy and targets live in `landing_pages.py` (`searches` records the volumes; they never appear on the page).

### Where the research plan was adjusted, and why

1. **Trips the business can legally sell.** Manhattan ↔ JFK/LGA and any trip that starts and ends in New York
   need NYC TLC base affiliation (`data.OPERATIONS`). So the JFK and LaGuardia pages target New Jersey and
   Connecticut travellers and say plainly that in-state New York trips are arranged personally. Tests fail if
   any page advertises a journey the authority rules would turn into a request.
2. **Biggest sellable opportunity: Newark ↔ Manhattan** (interstate, allowed). The Newark page answers it now;
   a full guide is first in the content calendar (§4) — 8,100 + 5,400 + 3,600 + 1,600 searches/mo.
3. **No "luxury".** It is on the brand's banned-word list. Google matches meaning, not exact strings, and the
   720-search "luxury chauffeur service NYC" is served by "executive", "Cadillac Escalade" and the page itself.
4. **No corporate page yet** — corporate accounts are a later phase; "executive" is covered on the NYC page.
5. **Teterboro brought forward** from days 15–45: it is already served and is the highest-value segment.
6. **Airport hub added** (`/airport-transfers`) so breadcrumbs reflect a real, browsable hierarchy.

## 3. Indexing: staging now, the real domain at launch

- **Staging is `noindex`** (`X-Robots-Tag` on every response unless `APP_ENV=production`). Google must not index
  the onrender.com copy or the placeholder phone number — inconsistent contact details hurt local ranking.
- **At launch:** set the real domain in `data.BRAND["domain"]` and `PUBLIC_BASE_URL` (a launch gate checks they
  match, because canonical tags and the sitemap use it), set `APP_ENV=production`, then in Google Search
  Console: verify the domain, submit `/sitemap.xml`, and request indexing for the eight pages via URL Inspection.
- Brand: **Celeste Luxury Limo** (`data.BRAND`). The name is used verbatim everywhere — Google Business
  Profile, directories and structured data must match it exactly. The logo is inline outlined SVG (no web-font
  request); `static/og.png` (link previews) and `static/logo.png` (Organization logo, on its own navy so it reads
  on Google's white background) are rendered from it by `tools/make_images.py`.

## 4. Content calendar (only what can be fulfilled)

| When | Page | Why |
|---|---|---|
| Days 15–45 | **Newark Airport to Manhattan guide** — honest train / taxi / private comparison, our price and timing | Largest measured demand, and a journey we sell |
| Days 15–45 | **What a chauffeur costs** — what's included, tolls, waiting, cancellation, luggage | "how much is chauffeur service" 480/mo; trust |
| Days 15–45 | **Cape Liberty cruise port** (Bayonne) from Newark and New Jersey | NJ–NJ and NJ–NY trips are sellable; strong luggage use case |
| Days 46–90 | **MetLife Stadium** event transport, **Hamptons from New Jersey**, **NJ wedding chauffeur** (couple/family only) | Sellable routes with clear intent |
| After TLC affiliation | JFK and LaGuardia to Manhattan guides (4,400 · 2,400 searches/mo) | Only once those trips can be booked |

Rank each new page by demand × booking intent × margin × whether we can fulfil it — never volume alone.

## 5. Google Business Profile (highest leverage, do first)

1. **Service-area business**: hide the street address; set service areas (Essex, Hudson, Bergen, Morris, Union,
   Passaic first; add Manhattan and Westchester). Verification takes days — apply now.
2. **Primary category** is the single strongest local factor (Whitespark 2026): choose the closest of
   *Chauffeur service*, *Limousine service* or *Car service* in the editor.
3. Name = **Celeste Luxury Limo**, exactly — the registered name only (adding keywords violates GBP guidelines).
4. Name, phone and service area identical everywhere: site footer, `data.BRAND`, GBP, directories.
5. Services and prices matching the site; at least ten real photos of the Escalade and cabin.
6. Paste the GBP review link into `data.BRAND["review_url"]` (post-trip review emails start automatically) and
   the profile URL into `data.BRAND["same_as"]` (added to structured data).
7. A weekly GBP post (seasonal lines in `data.VOICE["seasonal"]`).

## 6. Prominence: links and citations

Consistent listings: Apple Business Connect, Bing Places, Yelp, BBB, local Chamber of Commerce. Relationship
links that also bring bookings: Teterboro and Morristown FBO ground-transport lists, boutique-hotel concierges,
event venues, wedding planners. No paid link schemes.

## 7. Measurement (built in)

**Browser events** (`window.dataLayer`, GA4 recommended names, read by Google Tag Manager): `quote_start`,
`view_item` (a price is shown), `alternative_time_selected`, `begin_checkout`, `reservation_step`,
`add_payment_info`, `generate_lead`, `popular_journey_selected`, `luggage_guide_opened`, `cta_click`,
`phone_click`, `email_click`.

**Server events** (GA4 Measurement Protocol from the verified Stripe webhook, never double-counted): `purchase`
(transaction id = reservation reference) and `refund`.

**First-party attribution** on every quote and reservation — UTM, gclid/gbraid/wbraid, fbclid, msclkid,
referrer, **landing page**, GA client id — stored in PostgreSQL, so revenue by landing page is visible in
`/admin` even without cookies. Google Ads offline conversions: `/admin/exports/google-ads-conversions.csv`.

**Weekly in Search Console:** impressions, clicks and position by page and query; pages with impressions but
low click-through (rewrite their title and description first).

Setup: GA4 property → `GA4_MEASUREMENT_ID` + Measurement Protocol secret → `GA4_API_SECRET`; GTM container →
`GTM_CONTAINER_ID`; mark `purchase` as the key event. Consent Mode v2 defaults are injected automatically and
Global Privacy Control turns off ad signals. Staging uses no tags or a separate property.

## 8. Guardrails (tests/test_seo.py — the build fails if any breaks)

Unique titles and descriptions within length · one H1 · canonical = own URL · primary phrase in title, H1 and
description, density ≤ 3 % · valid JSON-LD with ordered breadcrumbs, no ratings, no offers before prices are
approved · every advertised journey sellable online · no unfilled price tokens or banned brand words · every page
linked from another and every internal link resolves · sitemap dates follow content · staging sends `noindex`.

## 9. 90-day targets

| By | Target |
|---|---|
| Launch day | Real domain live; Search Console verified; sitemap submitted; GBP submitted |
| Day 30 | All eight pages indexed; 10+ Google reviews at 4.8★+; Newark-to-Manhattan guide live |
| Day 90 | Map-pack presence for "Teterboro car service" and home-county "chauffeur service"; Newark page on page one for at least one EWR query; organic + GBP ≥ 30 % of reservations |
