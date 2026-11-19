# SEO, Local Search and Measurement Plan

Every recommendation cites its source. Where data is missing, it says so and names the step that fills it.

## 1. What the evidence says

| Finding | Source | What we do |
|---|---|---|
| Local results are ranked on **relevance, distance and prominence**; prominence includes links and the number and rating of reviews | Google Business Profile Help, "Tips to improve your local ranking" (support.google.com/business/answer/7091) | Complete Business Profile; reviews programme; local links |
| The Business Profile **primary category ranks #1 of 187 factors**, then proximity and keywords | Whitespark, *2026 Local Search Ranking Factors* (47 experts) | Pick the primary category deliberately (see §2) |
| **Review recency** is an underrated ranking factor | Whitespark, "The Most Underrated Local Ranking Factor in 2025" | Automatic review request after every completed trip (built: `review_request` email) |
| **97%** of consumers read reviews for local businesses; **31%** only use businesses rated 4.5★+ | BrightLocal, *Local Consumer Review Survey 2026* | Ask every satisfied client; reply to every review |
| Page experience: Core Web Vitals "good" = LCP ≤ 2.5 s, CLS ≤ 0.1, INP ≤ 200 ms | Google Search Central / web.dev | Measured: **LCP 0.55 s, CLS 0** on throttled mobile (local server) |
| FAQ rich results are limited to authoritative government and health sites (since Aug 2023) | Google Search Central blog | FAQPage markup kept only for AI/answer engines; no expectation of FAQ rich results |

Keyword volumes: the connected Semrush account had no API units, so **no volumes are quoted here**. Validate
the clusters in §3 in Google Ads Keyword Planner (free with an Ads account) before writing new pages.

## 2. Google Business Profile (highest-leverage, do first)

1. **Service-area business**: hide the street address; set service areas (Bergen, Hudson, Essex, Morris,
   Union, Passaic counties first; add NYC boroughs and Westchester). Verification can take days — apply now.
2. **Primary category**: choose the closest available among *Chauffeur service*, *Limousine service* or
   *Car service* (check the exact list in the GBP editor); add *Airport shuttle service* only if it is true.
3. Name = the real business name only (keyword-stuffing the name violates GBP guidelines).
4. NAP (name, address/area, phone) identical everywhere: site footer, `data.BRAND`, GBP, directories.
5. Services and prices in GBP matching the site; real photos of the Escalade and cabin (min. 10).
6. Paste the GBP review link into `data.BRAND["review_url"]` — post-trip review emails then start.
7. Weekly GBP post (seasonal lines in `data.VOICE["seasonal"]`).

## 3. On-site architecture (current and next)

**Now (built):** one fast, crawlable homepage with services, pricing (popular journeys + hourly), FAQs,
`pricing.md` for AI assistants, JSON-LD (Organization, WebSite, LocalBusiness, FAQPage; price offers only
once `PRICING["approved"]`), sitemap, robots (private routes disallowed).

**Next — one strong page per real intent, only with unique, first-hand content:**

| Page | Intent cluster (validate volumes first) |
|---|---|
| `/teterboro-car-service` | Teterboro / TEB car service, private jet ground transportation NJ |
| `/newark-airport-car-service` | EWR car service, Newark airport black car |
| `/jfk-car-service-from-new-jersey` | NJ to JFK car service |
| `/chauffeur-by-the-hour` | hourly chauffeur NYC/NJ, driver for the day |
| `/escalade-car-service` | Escalade car service, Cadillac Escalade chauffeur |

Each page: real pickup notes (terminals, FBO procedures), real photos, its own FAQ, a live quote widget
pre-filled for the route, and internal links. Avoid 21 near-identical county pages (thin content).

## 4. Prominence: links and citations

Consistent NAP listings: Apple Business Connect, Bing Places, Yelp, BBB, local Chamber of Commerce.
Relationship links that also bring bookings: Teterboro and Morristown FBOs' ground-transport lists, boutique
hotels' concierge desks, event venues and wedding planners. No paid link schemes.

## 5. Measurement (built in)

**Browser events** (`window.dataLayer`, GA4 recommended names; read by Google Tag Manager):

| Event | When | Key parameters |
|---|---|---|
| `quote_start` | first interaction with the reservation form | — |
| `view_item` | a price is shown | ecommerce items, value, `bookable`, `instant`, `availability` |
| `alternative_time_selected` | a suggested open time is tapped | — |
| `begin_checkout` | the reservation sheet opens | ecommerce |
| `reservation_step` | each step of the sheet | `step` |
| `add_payment_info` | handed to Stripe Checkout | `reservation_ref` |
| `generate_lead` | request (approval path) or bespoke enquiry sent | value / `lead_type` |
| `luggage_guide_opened`, `popular_journey_selected`, `cta_click`, `phone_click`, `email_click` | engagement | — |

**Server events** (GA4 Measurement Protocol, sent from the verified Stripe webhook, never double-counted):
`purchase` (transaction id = reservation reference, value, campaign source) and `refund`.

**First-party attribution** on every quote and reservation: UTM parameters, gclid/gbraid/wbraid, fbclid,
msclkid, referrer, landing page, GA client id — stored in PostgreSQL (`quotes.attribution`,
`bookings.attribution`), so the funnel survives cookie loss and becomes the owner's own analytics platform
(`/admin` 30-day funnel: prices shown → bookable → reservations → paid → revenue, lost demand, by channel).

**Google Ads**: `/admin/exports/google-ads-conversions.csv` produces offline conversions (gclid, time, value)
for paid reservations — upload weekly so Smart Bidding optimises for revenue, not clicks.

**Setup checklist**
1. Create GA4 property → `GA4_MEASUREMENT_ID`; create a Measurement Protocol secret → `GA4_API_SECRET`.
2. Create a GTM web container → `GTM_CONTAINER_ID`. In GTM: GA4 Configuration tag; GA4 Event tags on the
   events above with "Send ecommerce data" enabled; Google Ads conversion linker.
3. Mark `purchase` as the key event in GA4; `generate_lead` as secondary.
4. Google Search Console: verify the domain, submit `sitemap.xml`.
5. Staging uses a separate GTM container / GA4 property (or none).
6. Consent Mode v2 defaults are injected automatically; Global Privacy Control turns off ad signals.

## 6. 90-day targets

| By | Target |
|---|---|
| Day 7 | GBP submitted; Search Console verified; GA4 receiving `view_item` and `purchase` |
| Day 30 | 10+ Google reviews averaging 4.8★+; first two intent pages live; Ads conversions uploading |
| Day 90 | Map-pack presence for "Teterboro car service" and the home-county "chauffeur service" queries; organic + GBP ≥ 30% of reservations |
