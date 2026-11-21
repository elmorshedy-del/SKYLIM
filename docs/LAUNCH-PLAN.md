# Celeste Luxury Limo — Launch Plan (revised 19 Nov 2026; renamed 21 Nov 2026)

This supersedes the draft plan of 19 November. It keeps its non-negotiables — server-owned prices,
verified payments, honest tracking, no invented claims — and changes the business model, booking flow
and pricing approach based on the evidence below.

## 1. Positioning

**A private chauffeur service for executives and discerning travellers across New York and New Jersey.**
Every journey is in a Cadillac Escalade with second-row captain's chairs, a panoramic sunroof and onboard
Wi-Fi, prepared to the client's preferences before pickup. The brand is built to scale from one vehicle to a
fleet: the promise is the **Celeste Standard**, not "one car".

| | |
|---|---|
| Internal mantra | *No surprises.* — test every decision against it (price, time, vehicle, location) |
| Public line | *Arrive composed.* (hero) · tagline option *Expect exactly.* |
| Voice | Five-star hospitality: composed, precise, warm, discreet. No "luxury/VIP/elevate/seamless". |
| Proof points | All-inclusive price · real-time position · only times we can keep · cabin set before you sit |

All copy lives in `data.py` (`VOICE`, `SERVICES`, `FAQS`, `AMENITIES`) — edit once, the site follows.

## 2. Services at launch

| Service | How it is booked |
|---|---|
| Airports & private aviation (EWR, JFK, LGA, **Teterboro**, Morristown, Westchester, PHL) | Instant |
| By the hour (3-hour minimum) | Instant |
| Point to point, anywhere in the region | Instant |
| Evenings & occasions | Hourly, or bespoke request |
| Long distance (Philadelphia, Hamptons, Shore, Connecticut) | Instant up to 8 committed hours, then bespoke |
| Corporate accounts | **Later phase** (code path dormant, hidden from the site) |

Teterboro is the region's main business-jet airport and sits in Bergen County — an ideal fit for an
executive Escalade service and a strong differentiator from mass-market black-car apps.

## 3. Operating authority (launch gate)

Trips are classified by their two ends and only authorised classes book online (`OPERATIONS["authority"]`):

| Class | Example | Requirement (verify with a transportation attorney / insurer) |
|---|---|---|
| NJ intrastate | Hudson → EWR | Municipal limousine licence under N.J.S.A. 48:16-13 et seq.; $1.5M liability policy filed per N.J.S.A. 48:16-14 (as adopted in municipal ordinances, e.g. Union Twp. ch. 356) |
| Interstate | Teterboro → Manhattan | 49 U.S.C. 14501(d): pre-arranged interstate trips are protected from local licence requirements **if** the carrier meets federal registration requirements and its home-state licensing |
| Other-state intrastate | Manhattan → JFK | Needs NYC TLC base affiliation or a licensed partner — **off** at launch; shown as "we arrange by request" |

Payments stay off in production until `OPERATIONS["authority_confirmed"]` and the other launch gates pass
(visible in `/admin`).

## 4. Booking flow — instant by default

1. Client chooses one-way or by-the-hour, places, time, guests and luggage → **price and live availability**.
2. If the time is taken, the nearest open times are offered as one-tap alternatives (never a dead end).
3. **Reserve** → three short steps (details → cabin preferences, skippable → review) → Stripe Checkout
   (Apple Pay, Google Pay, Link, card). The slot is held for 35 minutes during payment.
4. Stripe's verified webhook confirms the reservation; receipt and trip page follow automatically.

Owner approval is required only for exceptions: luggage beyond the guide, notice under 8 hours (but over 3),
or routes "arranged by request". Approval is one tap in `/admin`.

## 5. Capacity plan for one chauffeur

| Protection | Default | Where |
|---|---|---|
| No double booking, ever | PostgreSQL exclusion constraints on vehicle and driver | `migrations/001_booking.sql` |
| Real service window | Drive out + journey at that hour's traffic + curbside + drive back + 20 min buffer | `app/domain/pricing.py` |
| Daily cap | 660 committed minutes per day | `MAX_DAILY_MINUTES` |
| Instant-booking notice | 8 hours | `INSTANT_MIN_NOTICE_MINUTES` |
| Owner time blocks | Personal time, servicing | `/admin` → Block time |
| Peak-week control | Pause instant booking (everything becomes approval) | `/admin` switch |

**When to add capacity.** The system records every quote that met a full calendar ("lost — calendar full"
in the admin funnel). Add a second vehicle and chauffeur when either holds for four consecutive weeks:
committed utilisation above 60–70% of operating hours, or lost demand exceeding ~3 bookable trips a week.
Before that, overflow can go to one vetted, licensed and insured affiliate under a written agreement. The
calendar already supports multiple vehicles and drivers.

## 6. Pricing strategy

**Evidence**
- Air Brook (established NJ operator): SUV Bergen/Hudson → JFK *from* $284.40 + tolls + ≥15% gratuity
  ≈ **$355 all-in** (airbrook.com, checked 19 Nov 2026).
- Uber Black SUV, NYC: **$75–107 for 5 mi / 16 min**, tolls, fees and tip extra (fareestimate.com, Oct 2026);
  scaled to Bergen → JFK ≈ $325 all-in before surge.
- Escalade ESV hourly, NYC: **$150/h incl. gratuity** (blackcarservice.nyc, 2026).
- Kahneman, Knetsch & Thaler (1986), *Fairness as a Constraint on Profit Seeking*, Proposition 4: discounts
  are withdrawn with far less resistance than posted prices are raised; cost-driven increases are judged fair,
  demand-driven surges unfair.

**Policy**
1. **List price = the long-run price**, from the cost model (`data.PRICING`, `app/domain/rates.py`):
   committed vehicle time × $75/h + $0.60/mile + tolls + fixed costs, grossed up for card fees.
   Examples: Bergen → JFK $370 · Teterboro → Manhattan $305 · Hudson → EWR $165 · hourly $145.
2. **Launch with a visible "Founding client rate"** (15% off, time-boxed to 28 Feb 2027) instead of lower list
   prices: clients see ~~$370~~ $314. Turn on with `PRICING["introductory"]["active"] = True`.
3. **Compete where Uber is weak**: fixed all-inclusive price (no tip, toll or surge add-ons), guaranteed
   Escalade, pre-set cabin, private aviation. Keep the $125 minimum; steer short hops to hourly.
4. **Raise prices without losing clients**: end the founding rate first; then small annual list increases
   (3–6%) each January when Port Authority tolls index upward; 30 days' notice; existing reservations always
   keep their booked price (quotes are stored).
5. **Let conversion set price**: per route, quote→reservation above ~60% means underpriced (+5%); below 20%,
   review price or channel. All data is in the `quotes` and `bookings` tables.
6. **Before launch**: check the Uber app on 10 routes at 3 times of day; add to `data.BENCHMARKS`; run
   `python3 tools/rate_model.py --write` and approve (`PRICING["approved"] = True`).

## 7. Tracking

| Phase | Source | Notes |
|---|---|---|
| Launch | Traccar Client on the chauffeur's phone → `/api/tracking/osmand` | Free, works with the phone locked, no Traccar server needed |
| First 30 days | OBD/hard-wired LTE unit (Teltonika FMC003-class, ~$100 + SIM) via a Traccar server → `/api/tracking/traccar` | Vehicle reports itself; phone becomes backup |
| Later | Traffic-aware ETA (Mapbox), geofenced auto-"Arrived", SMS once Twilio 10DLC is approved | |

Location is stored only during an active trip, shown with its age, marked stale after 60 s, and deleted when
the trip ends.

## 8. Week-one timeline (Eastern)

| Date | Owner (Ahmed) | Platform |
|---|---|---|
| Thu 19 – Fri 20 | Confirm authority/insurance path; domain, phone, inbox; Stripe account + identity; car trim/wheelbase; buy amenities | Done: platform, site, tests |
| Sat 21 | Stripe Dashboard: enable Apple Pay, Google Pay, Link; request Affirm/Klarna/Afterpay; request PayPal invite | Deploy **staging** (Railway + Postgres), Stripe test mode |
| Sun 22 | Uber price checks; approve rates & cancellation policy; Google Business Profile application (service-area business) | GTM + GA4 + Search Console; Postmark |
| Mon 23 | Install Traccar Client; luggage loading test; photograph the real car and cabin | Real photos into the site; end-to-end test with test cards |
| Tue 24 | Rehearse a full trip with a friend (test mode) | Production deploy behind launch gates |
| Wed 25 | Go live when gates pass; take only manageable trips | Monitor admin funnel, webhooks, email |

The day before Thanksgiving and the Sunday after are peak travel days: launch by Tuesday so Wednesday and
Sunday can be sold.

## 9. Launch gates (enforced in code — see `/admin`)

Real contact details · authority & insurance confirmed · luggage capacity tested · cancellation policy approved ·
legal pages approved · Stripe live key and webhook secret · HTTPS · admin password · secret key · email provider.
If any gate fails, the site still takes requests and payments stay off — it never pretends to be live.
