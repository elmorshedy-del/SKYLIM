# Go-Live Integration Guide

Everything on this site works in the browser today. Four things need a back end before
you take real money and dispatch real cars. Each hook is marked in `index.html` with
`// >>> HOOK:` and configured from the `CFG` object at the top of the `<script>` block.

Nothing here is presented to a customer as working when it isn't — the payment step and
the tracking panel both carry visible "demo mode" notices. **Remove those two notices
only once the corresponding integration is live.** Search for `class="hook"` to find them.

---

## 0. Before anything: replace the placeholders

Open `data.py` and edit the `BRAND` dictionary, then re-run `python3 build.py`.

| Field | Currently | Needs to be |
|---|---|---|
| `name` / `short` | Meridian Black Car | Your real company name |
| `domain` | meridianblackcar.com | Your real domain |
| `phone_display` / `phone_raw` | (201) 555-0100 | Your real dispatch number |
| `email` | ride@meridianblackcar.com | Your real booking inbox |
| `address` | 1 Riverfront Plaza, Newark | Your real registered address |
| `tlc` | TLC #XXXXXX | Your real TLC / NJ operating authority number |
| `rating` / `review_count` / `rides` | 4.9 / 1,284 / 38,000 | **Real numbers only** |

> **Do not ship invented review counts or ratings.** Fake `AggregateRating` in structured
> data violates Google's guidelines and can earn a manual action. The four testimonials in
> `data.py` are illustrative — replace them with real, attributed quotes or delete the section.

Also required before launch: a real privacy policy, terms, and accessibility statement.
The footer currently points these at `#faq`. Your NAP (name, address, phone) must match
**exactly** across the site, your Google Business Profile, and every directory listing —
inconsistent NAP is the most common local-SEO failure.

---

## 1. Payments — Stripe or Square

**Current behaviour:** `doPayment()` waits 1.5s and fabricates a booking reference.
No card data leaves the page and nothing is charged.

**To go live:**

1. Set `CFG.stripePublishableKey = 'pk_live_...'`.
2. Add the Stripe script to `<head>`: `<script src="https://js.stripe.com/v3/"></script>`
3. Replace the raw card inputs (`#p-card`, `#p-exp`, `#p-cvc`) with a **Stripe Elements**
   card element. This matters — it keeps card data off your servers and reduces your PCI
   scope to SAQ-A. Do not collect raw PAN into your own form in production.
4. Server side: create a PaymentIntent for the quoted amount, return the `client_secret`,
   and confirm with `stripe.confirmCardPayment(client_secret, {...})`.
5. On success, POST the booking to `CFG.bookingEndpoint` and render step 5.

**Authorise vs. capture.** You advertise free cancellation up to 60 minutes before pickup,
so use `capture_method: 'manual'` to place a hold, and capture at pickup. Cancelling a hold
is cleaner than refunding a charge, and avoids card-network refund fees.

**Remove** the demo-mode `.hook` notice in the payment step once this is done.

---

## 2. Driver messaging — Twilio

**Current behaviour:** `sendMsg()` renders your message, then plays a canned reply from
`CHAT_REPLIES` after a simulated typing delay.

**To go live:**

1. Buy a Twilio number and set `CFG.smsEndpoint = 'https://api.yourdomain.com/sms/send'`.
2. **Outbound** — in `sendMsg()`, POST `{ bookingId, body }` to that endpoint. Your server
   looks up the assigned driver's number and calls the Twilio Messages API. Never put the
   driver's phone number in the browser.
3. **Inbound** — configure your Twilio number's webhook to `POST /sms/incoming`. Match the
   sender to an active booking, store the message, and push it to the rider's open page
   over a WebSocket or SSE. Call `addMsg(text, 'them')` on arrival.
4. Delete the `CHAT_REPLIES` array and the `driverReply()` call.

**Practical notes.** Use one Twilio number as a relay for every trip so neither party sees
the other's real number, and drop the pairing when the trip completes. US A2P 10DLC
registration is required for application-to-person SMS — start it early, it takes days, not
minutes. Log every message: it is your record if a pickup is disputed.

---

## 3. Live driver location

**Current behaviour:** the marker walks a fixed 12-point polyline from Hackensack to Midtown
on a 3-second interval, and the ETA counts down proportionally.

**To go live:**

1. The driver app (or a telematics provider) posts `{ bookingId, lat, lng, heading, speed }`
   every 5–10 seconds.
2. Set `CFG.gpsEndpoint` and replace the `setInterval` in `initMap()` with a poll of that
   endpoint — or better, a WebSocket subscription.
3. Feed positions in with `carMarker.setLatLng([lat, lng])`.
4. For a real ETA, call the Google Directions or Mapbox Directions API with live traffic
   rather than interpolating along a fixed line.

**Privacy.** Only expose a driver's position while a trip is active, and only to that
trip's rider. Stop the feed on drop-off.

**Tiles.** The map uses OpenStreetMap tiles, which are fine for development but whose
tile-usage policy is not intended for commercial production traffic. Move to Mapbox,
MapTiler, or Google Maps before you get real volume.

---

## 4. Bookings and the overnight confirmation

**Current behaviour:** nothing is persisted. The booking reference is generated from a
timestamp and the confirmation screen is rendered locally.

**To go live:**

1. `POST CFG.bookingEndpoint` with the trip, contact, vehicle, price and payment intent ID.
2. Send the confirmation email and SMS server-side (SendGrid/Postmark + Twilio).
3. **The overnight confirmation you promise on the site is a real operational commitment.**
   Run a nightly job that lists tomorrow's trips, requires a dispatcher to assign a
   chauffeur and vehicle to each, and then sends the rider the driver's name, photo,
   vehicle and plate. If a trip cannot be covered, that job must surface it that night —
   the site tells customers they will hear from you before the curb, so this has to be
   staffed, not just coded.
4. Honour the cancellation promise: cancelling more than 60 minutes out should release the
   card hold automatically.

---

## 5. Analytics

The full booking funnel already pushes to `window.dataLayer`. Add GA4 or GTM and the events
flow with no further work:

```
quote_started → quote_completed → vehicle_selected → booking_started
→ booking_details_completed → payment_info_entered → booking_completed
```

Also firing: `driver_tracking_viewed`, `driver_message_sent`, `events_calendar_viewed`,
`event_ride_quote_requested`, `cta_clicked`, `phone_call_clicked`, `form_submitted`,
`popup_shown`.

**Mark `booking_completed` as your GA4 conversion** and use the steps above it to find where
people drop. No PII is included in any payload — keep it that way.

---

## 6. Live events feed

**Yankee Stadium works right now.** It uses the official MLB Stats API, which needs no key
and sends `Access-Control-Allow-Origin: *`. Verified returning real home games.

**Madison Square Garden, Barclays Center, Broadway and concerts** need a free Ticketmaster
key from <https://developer.ticketmaster.com> (about two minutes, no card). Either:

- paste it into the connector on the page — it saves to `localStorage`; or
- for production, set `CFG.tmKey` at build time, or better, proxy the call through your
  own server so the key isn't in client-side source.

Venue IDs are resolved at runtime via the `/venues.json` endpoint, so no IDs are hardcoded
and the feed self-corrects if Ticketmaster changes one. Listings refresh every 10 minutes.
If the key is missing, the affected tabs say so honestly rather than showing invented events.

**Recommended:** add `Event` structured data for the fetched listings server-side. Client-side
JSON-LD is not reliably indexed, so rendering the events feed server-side would also make it
eligible for event rich results — a meaningful SEO win we can't get from a static page.

---

## 7. Deployment

Static files — host anywhere:

```bash
npx vercel deploy --prod        # or
netlify deploy --prod --dir=.   # or drop onto Cloudflare Pages / S3+CloudFront
```

Post-deploy checklist:

- [ ] HTTPS enforced, HSTS on
- [ ] `sitemap.xml` submitted in Google Search Console and Bing Webmaster Tools
- [ ] Rich Results Test passes: <https://search.google.com/test/rich-results>
- [ ] Google Business Profile created and NAP matched exactly
- [ ] Core Web Vitals checked on mobile (targets: LCP < 2.5s, INP < 200ms, CLS < 0.1)
- [ ] Real phone number tested end to end, including the click-to-call on mobile
- [ ] Rebuild after any rate change: `python3 build.py` regenerates the table, the 42
      schema offers, the per-county FAQ answers and `pricing.md` together, so they cannot
      drift apart

---

## 8. Where the county SEO lives

There are no separate per-county pages, by design — 21 near-identical pages is thin content
and Google penalises it. Instead the counties are embedded four ways:

1. **A crawlable rate table** — all 21 counties × both rates as real HTML text.
2. **`OfferCatalog` schema** with 42 priced `Offer` nodes.
3. **`FAQPage` schema** with a real priced answer for every county × destination (42 of the
   52 questions), which is what wins AI-search citations and "how much is…" rich results.
4. **`pricing.md`** at the site root, so AI agents can quote your actual prices instead of
   skipping you for a competitor who hides them behind "call for a quote."

Plus footer text links and `#bergen-county` anchors for internal linking, and `?county=bergen&to=jfk`
deep links for ads and Google Business Profile.

**If one county later proves high-volume** in Search Console, that is the moment to give it a
real dedicated page at `/service-areas/bergen-county/` with genuinely unique content — actual
towns, local pickup notes, drive times, testimonials from that county. One strong page beats
21 thin ones.

---

## 9. Tuning the departure planner

The planner (`suggestDeparture()`) is the one piece of business logic on the site that is
genuinely *yours* — it encodes what you know about getting from New Jersey into New York.
Right now it is built from public knowledge; it should be built from your trip data.

**How it works today**

```
pickup = arrival
       − (county drive time × traffic factor)   ← slower end of the range, deliberately
       − arrival buffer                         ← 120/180 min flights, 45 arena, 30 theatre
       − safety cushion                         ← 20 min flights, 15 events
```

Two design decisions worth keeping:

1. **It uses the upper bound of each county's drive range, not the average.** Being twenty
   minutes early to a terminal costs nothing. Being ten minutes late costs the flight.
2. **The traffic factor is scored across the drive window, not at the arrival time.** It
   guesses a departure, scores the midpoint of that drive, and re-solves — three passes.
   This is why two riders heading to the same 8pm show get different factors: a Hudson
   County pickup leaves after the peak eases, a Morris County pickup has to set off inside it.

**Current traffic factors** (in `trafficFactor()`):

| Window | Factor |
|---|---|
| Weekday 06:30–09:30 | 1.45 |
| Weekday 15:30–19:00 | 1.50 (Friday 1.70) |
| Weekend 11:00–18:00 | 1.15 |
| 22:00–05:00 | 0.85 |
| Otherwise | 1.00 |
| JFK destination | × 1.10 on top |

**Replace these with your own numbers as soon as you have fifty trips.** Log actual
`departure → arrival` durations against county, hour and day, then fit the factors. This is
the highest-value data you will collect: it is what lets you promise an on-time arrival and
actually keep it, and no competitor can copy it.

**Worth adding when you have the budget:** call the Google Directions API with
`departure_time` and `traffic_model=pessimistic` for a live-traffic duration, and keep the
static factors as the fallback when the API is unavailable or over quota. Layer weather on
top — snow and heavy rain on the Turnpike are worth another 15–25 percent, and the planner
has no notion of weather today.

**Also missing today:** the planner assumes the pickup is at the county's typical distance.
Once you geocode the actual pickup address you can compute a true per-address drive time and
drop the county approximation entirely.
