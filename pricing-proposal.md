# Pricing plan — Celeste Luxury Limo

Version `2026-11-23-uber-anchor`. **Awaiting owner approval** — the site shows prices as estimates until `PRICING['approved']` is True.

## 1. How every price is set — the same gap to Uber Black SUV in every county

**The anchor is Uber Black SUV.** Uber publishes, for popular routes, the average price of each ride option over the past month (checked 2026-11-23; 55 route-directions with prices, file `benchmarks/uber_routes.json`). Uber's prices are not the same in both directions: a trip that starts in New York City costs about **1.52×** the same trip starting in the suburbs (NYC rates and airport fees), and from most suburbs Uber shows no Black SUV at all.

1. **Where Uber publishes the route: our price = the Uber Black SUV price for the trip starting outside New York City — what a client sees in the app when booking from home — plus a 20% tip (ours includes gratuity), plus 5%.** From the airport or Manhattan side Uber charges about 1.52× more, so there we sit well under it. Where Uber shows no Black SUV price it uses the average route price × 2.16 (Black SUV ÷ average on the routes that show both); a direction Uber does not publish is inferred from the other with the NYC-origin ratio. Routes between Manhattan and the airports use Uber's own figures both ways. Marked * below.
2. **Where Uber publishes nothing:** $125 + $5.35 per road mile — the line fitted to all the Uber-anchored routes — times the county's own Uber factor where it has anchored routes (so its LaGuardia price matches its JFK and Manhattan prices).
3. **Long journeys:** never more than the round trip at the hourly rate ($150/h) + 30 minutes' turnaround + tolls. Marked †.
4. **Never below cost:** the journey plus the empty drive back at $50 per committed hour + running cost + tolls + fixed costs + card fees. Marked ‡ (it lifts a short airport hop above the gap where Uber's suburban fares are very low).
5. **Hourly:** $150/hour all-in, 3-hour minimum.
6. **Introductory rate:** 10% off every regular price (rounded down to $5) until January 31, 2027; then the regular price for at least 30 days (NYC rule 6 RCNY § 5-95). Active.

**Result:** on the 31 routes Uber publishes, our regular price is +4% to +27% from Uber Black SUV with tip (median +5%). All prices are one fixed price, all-in, the same either way. Journeys committing the vehicle for more than 8 hours are quoted individually.

**Why the gap to Uber looks different depending on where you stand — Princeton ↔ JFK:** Uber's average UberX is $191 from Princeton but $284 from JFK. From Princeton Uber shows no Black SUV, only sedans (Premier ≈ $300 in the app, ≈ $360 with tip); from JFK the Black SUV equivalent is ≈ $681 with tip. Our price is $470 ($420 introductory) in either direction: +5% against Uber's Black SUV equivalent from Princeton (≈ $448 with tip) and -31% against it from JFK.

## 2. Against Uber Black SUV, route by route

| Journey | Uber data | Uber Black SUV + tip (trip from the suburb) | Our regular price | Gap | Introductory rate |
|---|---|---|---|---|---|
| Newark (EWR) ↔ Manhattan | both directions | $270 | $285* | +6% | $255 |
| JFK ↔ Manhattan | one direction | $257 | $270* | +5% | $240 |
| JFK ↔ Mercer | from the suburb | $448 | $470* | +5% | $420 |
| JFK ↔ Middlesex | from the suburb | $378 | $395* | +4% | $355 |
| JFK ↔ Morris | from the suburb | $422 | $445* | +5% | $400 |
| JFK ↔ Nassau | from the suburb | $158 | $200‡ | +27% | $180 |
| JFK ↔ New Haven | from the suburb | $409 | $430* | +5% | $385 |
| JFK ↔ Rockland | from the suburb | $352 | $370* | +5% | $330 |
| JFK ↔ Somerset | from the suburb | $433 | $455* | +5% | $405 |
| JFK ↔ Suffolk | from the suburb, inferred | $293 | $315‡ | +7% | $280 |
| JFK ↔ Union | from the suburb | $350 | $365* | +4% | $325 |
| JFK ↔ Westchester | from the suburb | $311 | $325* | +5% | $290 |
| LaGuardia ↔ Manhattan | Uber average LGA to Midtown West (gothamride.com/blog/black-car-vs-uber-black-nyc) | $194 | $205* | +5% | $180 |
| Fairfield County ↔ JFK | from the suburb | $288 | $300* | +4% | $270 |
| Fairfield County ↔ Manhattan | from the suburb | $241 | $270‡ | +12% | $240 |
| Bergen ↔ JFK | from the suburb | $288 | $300* | +4% | $270 |
| Bergen ↔ Manhattan | from the suburb | $174 | $180* | +4% | $160 |
| Essex ↔ Manhattan | from the suburb | $155 | $190‡ | +22% | $170 |
| Hudson ↔ JFK | from the suburb | $293 | $305* | +4% | $270 |
| Hudson ↔ Manhattan | from the suburb | $128 | $145‡ | +13% | $130 |
| Manhattan ↔ Mercer | from the suburb | $389 | $410* | +5% | $365 |
| Manhattan ↔ Middlesex | from the suburb | $311 | $325* | +5% | $290 |
| Manhattan ↔ Monmouth | from the suburb, inferred | $414 | $435* | +5% | $390 |
| Manhattan ↔ Morris | from the suburb | $293 | $305* | +4% | $270 |
| Manhattan ↔ Nassau | from the suburb | $257 | $270* | +5% | $240 |
| Manhattan ↔ New Haven | from the suburb | $409 | $430* | +5% | $385 |
| Manhattan ↔ Rockland | from the suburb | $277 | $290* | +5% | $260 |
| Manhattan ↔ Suffolk | from the suburb | $365 | $385* | +5% | $345 |
| Manhattan ↔ Union | from the suburb | $264 | $280* | +6% | $250 |
| Manhattan ↔ Westchester | from the suburb | $228 | $240* | +5% | $215 |
| Dutchess ↔ JFK | from the suburb | $555 | $580* | +5% | $520 |

## 3. Against chauffeur services on the same journeys

All-in = what the client pays door to door: fare + tolls + fees + a 20% gratuity where the operator does not include one.

| Journey | Competitor | Their all-in | Our regular price | Gap | Source, checked |
|---|---|---|---|---|---|
| Manhattan ↔ LaGuardia (Midtown) | Detailed Drivers (Escalade ESV) | $210 | $205 | -2% | detaileddrivers.com/guides/nyc-car-service-cost, 2026-11-22 |
| Manhattan ↔ JFK (Midtown) | Detailed Drivers (Escalade ESV) | $270 | $270 | +0% | detaileddrivers.com/guides/nyc-car-service-cost, 2026-11-22 |
| Manhattan ↔ Newark (EWR) (Midtown) | Detailed Drivers (Escalade ESV) | $260 | $285 | +10% | detaileddrivers.com/guides/nyc-car-service-cost, 2026-11-22 |
| Manhattan ↔ Teterboro (Midtown) | Detailed Drivers (Escalade ESV) | $240 | $200 | -17% | detaileddrivers.com/guides/nyc-car-service-cost, 2026-11-22 |
| Manhattan ↔ Nassau (Garden City) | Detailed Drivers (Escalade ESV) | $300 | $270 | -10% | detaileddrivers.com/locations/long-island, 2026-11-22 |
| Nassau ↔ JFK (Garden City) | Detailed Drivers (Escalade ESV) | $290 | $200 | -31% | detaileddrivers.com/locations/long-island, 2026-11-22 |
| Nassau ↔ LaGuardia (Garden City) | Detailed Drivers (Escalade ESV) | $300 | $220 | -27% | detaileddrivers.com/locations/long-island/airport-transfer, 2026-11-22 |
| Manhattan ↔ Suffolk (Hauppauge) | Detailed Drivers (Escalade ESV) | $500 | $385 | -23% | detaileddrivers.com/locations/long-island, 2026-11-22 |
| Suffolk ↔ JFK (Hauppauge) | Detailed Drivers (Escalade ESV) | $460 | $315 | -32% | detaileddrivers.com/locations/long-island/airport-transfer, 2026-11-22 |
| Manhattan ↔ The Hamptons (the Hamptons) | Detailed Drivers (Escalade ESV) | $810 | $635 | -22% | detaileddrivers.com/locations/long-island, 2026-11-22 |
| The Hamptons ↔ JFK (Southampton to Montauk, from) | Detailed Drivers (Escalade ESV) | $750 | $570 | -24% | detaileddrivers.com/guides/jfk-car-service-cost, 2026-11-22 |
| Westchester ↔ LaGuardia (White Plains) | Detailed Drivers (Escalade ESV) | $290 | $230 | -21% | detaileddrivers.com/locations/westchester/airport-transfer, 2026-11-22 |
| Westchester ↔ JFK (White Plains) | Detailed Drivers (Escalade ESV) | $360 | $325 | -10% | detaileddrivers.com/locations/westchester/airport-transfer, 2026-11-22 |
| Westchester (HPN) ↔ Manhattan (Midtown) | Detailed Drivers (Escalade ESV) | $380 | $295 | -22% | detaileddrivers.com/locations/new-york/airport-transfer/hpn-westchester-county-airport, 2026-11-22 |
| Fairfield County ↔ JFK (Greenwich, from) | Detailed Drivers (Escalade ESV) | $430 | $300 | -30% | detaileddrivers.com/guides/jfk-car-service-cost, 2026-11-22 |
| New Haven ↔ Manhattan (New Haven) | Detailed Drivers (Escalade ESV) | $700 | $430 | -39% | detaileddrivers.com/locations/connecticut/new-haven, 2026-11-22 |
| New Haven ↔ JFK (New Haven) | Detailed Drivers (Escalade ESV) | $680 | $430 | -37% | detaileddrivers.com/locations/connecticut/new-haven, 2026-11-22 |
| New Haven ↔ LaGuardia (New Haven) | Detailed Drivers (Escalade ESV) | $650 | $410 | -37% | detaileddrivers.com/locations/connecticut/new-haven, 2026-11-22 |
| Hudson ↔ JFK (Jersey City / Newark, from) | Detailed Drivers (Escalade ESV) | $320 | $305 | -5% | detaileddrivers.com/guides/jfk-car-service-cost, 2026-11-22 |
| Manhattan ↔ LaGuardia | NYC Lux Ride (Escalade ESV) | $228 | $205 | -10% | nycluxride.com/rates: $190 incl. tolls, fees, taxes + 20% tip, 2026-11-22 |
| Manhattan ↔ JFK | NYC Lux Ride (Escalade ESV) | $264 | $270 | +2% | nycluxride.com/rates: $220 incl. tolls, fees, taxes + 20% tip, 2026-11-22 |
| Manhattan ↔ Newark (EWR) | NYC Lux Ride (Escalade ESV) | $264 | $285 | +8% | nycluxride.com/rates: $220 incl. tolls, fees, taxes + 20% tip, 2026-11-22 |
| Manhattan ↔ Teterboro | NYC Lux Ride (Escalade ESV) | $264 | $200 | -24% | nycluxride.com/rates: $220 incl. tolls, fees, taxes + 20% tip, 2026-11-22 |
| Manhattan ↔ LaGuardia | Gotham Ride (Business SUV) | $270 | $205 | -24% | gothamride.com/car-service-rates-nyc: incl. tolls and gratuity, 2026-11-22 |
| Manhattan ↔ JFK | Gotham Ride (Business SUV) | $286 | $270 | -6% | gothamride.com/car-service-rates-nyc: incl. tolls and gratuity, 2026-11-22 |
| Manhattan ↔ Newark (EWR) | Gotham Ride (Business SUV) | $296 | $285 | -4% | gothamride.com/car-service-rates-nyc: incl. tolls and gratuity, 2026-11-22 |
| Manhattan ↔ LaGuardia | Uber Black SUV (average) | $195 | $205 | +5% | gothamride.com/blog/black-car-vs-uber-black-nyc: $162 + 20% tip, 2026-11-22 |
| Manhattan ↔ Newark (EWR) | Uber Black SUV (average) | $262 | $285 | +9% | gothamride.com/blog/black-car-vs-uber-black-nyc: $218 + 20% tip, 2026-11-22 |
| Bergen ↔ JFK (Hackensack) | Air Brook (SUV) | $365 | $300 | -18% | airbrook.com/service-area/jfk-airport-car-service: from $284.40 + 20% + ~$24 tolls, 2026-11-22 |
| Bergen ↔ LaGuardia (Rochelle Park) | Air Brook (SUV) | $350 | $215 | -39% | airbrook.com: from $272.72 + 20% + ~$24 tolls, 2026-11-22 |
| Bergen ↔ Manhattan (Rochelle Park) | Air Brook (SUV) | $310 | $180 | -42% | airbrook.com: from $239.68 + 20% + ~$23 tolls and congestion charge, 2026-11-22 |
| Essex ↔ JFK (Newark) | Air Brook (SUV) | $345 | $290 | -16% | airbrook.com/service-area/jfk-airport-car-service: from $274.80 + 20% + ~$17 tolls, 2026-11-22 |
| Rockland ↔ JFK (Nanuet) | Air Brook (SUV) | $375 | $370 | -1% | airbrook.com/service-area/jfk-airport-car-service: from $302.25 + 20% + ~$13 tolls, 2026-11-22 |
| Mercer ↔ JFK (Princeton) | Princeton Car Service (Luxury SUV, from) | $413 + gratuity if not included | $470 | +14% | princetoncarservice.com/princeton-to-jfk-airport: Escalade / Denali / Suburban from $413, 2026-11-23 |
| Mercer ↔ JFK (Princeton) | Islip Limo (SUV) | $428 + extras marked * | $470 | +10% | isliplimocarservice.com/service-area/princeton-car-service: JFK to Princeton SUV $428*, 2026-11-23 |
| Mercer ↔ JFK (Princeton → JFK only) | Uber Premier (sedan, owner's app check) | $360 | $470 | +31% | Uber app, Princeton to JFK: Premier $300 + 20% tip; Uber shows no Black SUV from Princeton, 2026-11-23 |
| The Hamptons ↔ Manhattan | Wheely (Business SUV) | $700 + tolls, taxes, fees | $635 | -9% | wheely.com/en/essentials/the-hamptons-by-wheely: $700 excl. taxes, regulatory fees, tolls, 2026-11-22 |
| By the hour | Detailed Drivers (Escalade ESV) | $150/h | $150/h | +0% | detaileddrivers.com: $150/h all-in, 3-hour minimum, 2026-11-22 |
| By the hour | Gotham Ride (Business SUV) | $180/h | $150/h | -17% | gothamride.com: from $180/h incl. gratuity, 2-hour minimum, 2026-11-22 |
| By the hour | NYC Executive Car (Escalade ESV) | $144/h | $150/h | +4% | nycexecutivecar.com: $120/h + 20% tip, 2-hour minimum, 2026-11-22 |

**Competitors that publish no prices** (quote or account only):

- **EmpireCLS** — Quote or account only. A flat-rate transfer is billed for the time the vehicle leaves its facility until it returns, plus an $18 airport fee, a fuel surcharge, an administration fee, gratuity, tolls and parking; $20-30 per extra stop; $25 between midnight and 5am. (empirecls.com/faq)
- **Dav El | BostonCoach** — Quote or account only. Flat rates for selected destinations; otherwise billed in 30-minute increments plus a positioning charge at 1.5x the hourly rate, an operating-cost surcharge, an administrative fee, tolls, parking and taxes; waiting $8.25 per 5 minutes. (bostoncoach.com/faq)

Both bill the vehicle's time from and back to their garage and add surcharges, fees, tolls and (for EmpireCLS) gratuity on top, so on suburban journeys they price above an all-in fixed fare.

## 4. Every commuter county to and from the city

Regular price, with the introductory rate in brackets. The same price in either direction; all of these book online (the TLC licence covers trips into New York City and pickups in it). Miles are road miles to Manhattan (Midtown).

### New Jersey

| County | Miles to Manhattan | Manhattan | JFK | LaGuardia |
|---|---|---|---|---|
| Hudson County | 10 | $145‡ ($130) | $305* ($270) | $215 ($190) |
| Bergen County | 16 | $180* ($160) | $300* ($270) | $215 ($190) |
| Essex County | 20 | $190‡ ($170) | $290‡ ($260) | $250‡ ($225) |
| Union County | 24 | $280* ($250) | $365* ($325) | $325 ($290) |
| Passaic County | 22 | $240 ($215) | $310 ($275) | $260 ($230) |
| Morris County | 32 | $305* ($270) | $445* ($400) | $370 ($330) |
| Sussex County | 51 | $400 ($360) | $475 ($425) | $425 ($380) |
| Warren County | 59 | $440 ($395) | $505 ($450) | $475 ($425) |
| Middlesex County | 34 | $325* ($290) | $395* ($355) | $375 ($335) |
| Somerset County | 41 | $395 ($355) | $455* ($405) | $435 ($390) |
| Monmouth County | 53 | $435* ($390) | $465 ($415) | $465 ($415) |
| Mercer County | 54 | $410* ($365) | $470* ($420) | $460 ($410) |
| Hunterdon County | 55 | $420 ($375) | $470 ($420) | $455 ($405) |
| Ocean County | 75 | $525 ($470) | $555 ($495) | $555 ($495) |
| Burlington County | 83 | $565 ($505) | $580 ($520) | $595 ($535) |
| Camden County | 89 | $600 ($540) | $620 ($555) | $630 ($565) |
| Gloucester County | 101 | $665 ($595) | $680 ($610) | $695 ($625) |
| Cumberland County | 116 | $745 ($670) | $745 ($670) | $770 ($690) |
| Salem County | 121 | $775 ($695) | $790 ($710) | $805 ($720) |
| Atlantic County | 115 | $740 ($665) | $770 ($690) | $765 ($685) |
| Cape May County | 145 | $900 ($810) | on request | on request |

### Long Island

| County | Miles to Manhattan | Manhattan | JFK | LaGuardia |
|---|---|---|---|---|
| Nassau County (Long Island), NY | 22 | $270* ($240) | $200‡ ($180) | $220 ($195) |
| Suffolk County (Long Island), NY | 50 | $385* ($345) | $315‡ ($280) | $315 ($280) |
| The Hamptons & East End, NY | 95 | $635 ($570) | $570 ($510) | $590 ($530) |

### Westchester & Hudson Valley

| County | Miles to Manhattan | Manhattan | JFK | LaGuardia |
|---|---|---|---|---|
| Westchester County, NY | 29 | $240* ($215) | $325* ($290) | $230 ($205) |
| Rockland County, NY | 29 | $290* ($260) | $370* ($330) | $300 ($270) |
| Putnam County, NY | 56 | $425 ($380) | $455 ($405) | $405 ($360) |
| Orange County, NY | 54 | $415 ($370) | $485 ($435) | $420 ($375) |
| Dutchess County, NY | 73 | $530 ($475) | $580* ($520) | $520 ($465) |
| Ulster County, NY | 83 | $570 ($510) | $625 ($560) | $565 ($505) |

### Connecticut

| County | Miles to Manhattan | Manhattan | JFK | LaGuardia |
|---|---|---|---|---|
| Fairfield County, CT | 37 | $270‡ ($240) | $300* ($270) | $265‡ ($235) |
| New Haven County, CT | 79 | $430* ($385) | $430* ($385) | $410 ($365) |
| Litchfield County, CT | 90 | $605 ($540) | $620 ($555) | $580 ($520) |

\* Uber Black SUV + 5% (Uber publishes this route) · no mark: formula fitted to Uber × county factor · † round trip by the hour · ‡ cost floor

## 5. Airports and the city

| Journey | Regular price | Introductory rate | Road miles | Vehicle committed |
|---|---|---|---|---|
| Manhattan → JFK | $270* | $240 | 18 | 2h42 |
| Manhattan → Newark (EWR) | $285* | $255 | 16 | 2h17 |
| Teterboro → Manhattan | $200 | $180 | 14 | 1h58 |
| Manhattan → LaGuardia | $205* | $180 | 10 | 1h58 |
| Bergen → JFK | $300* | $270 | 28 | 3h12 |
| Newark (EWR) → Manhattan | $285* | $255 | 16 | 2h17 |
| Hudson → Manhattan | $145‡ | $130 | 10 | 1h28 |
| Brooklyn → Newark (EWR) | $225 | $200 | 19 | 2h32 |
| Essex → LaGuardia | $250‡ | $225 | 25 | 2h47 |
| Manhattan → Philadelphia | $625 | $560 | 93 | 5h30 |

## 6. What it earns

Per hour of the car's time for the journey and the drive back, after card fees, tolls and running costs (fuel, tyres, servicing); what is left pays the chauffeur, the vehicle and the business.

| Journey | Regular price | Round trip | Per hour |
|---|---|---|---|
| Manhattan → JFK | $270 | 2.6h | $84 |
| Manhattan → Newark (EWR) | $285 | 2.2h | $104 |
| Teterboro → Manhattan | $200 | 2.0h | $78 |
| Manhattan → LaGuardia | $205 | 1.8h | $91 |
| Bergen → JFK | $300 | 3.2h | $69 |
| Newark (EWR) → Manhattan | $285 | 2.2h | $104 |
| Hudson → Manhattan | $145 | 1.8h | $60 |
| Brooklyn → Newark (EWR) | $225 | 2.3h | $70 |
| Essex → LaGuardia | $250 | 2.8h | $64 |
| Manhattan → Philadelphia | $625 | 5.8h | $82 |
| Mercer → JFK | $470 | 4.8h | $73 |
| Nassau → JFK | $200 | 2.3h | $66 |
| Monmouth → Manhattan | $435 | 3.7h | $90 |

## 7. Keeping it current

- Each quarter, re-read Uber's route pages listed in `benchmarks/uber_routes.json` (both directions), update the file and run `python3 tools/rate_model.py --write`; prices follow automatically and the tests check every route keeps the gap.
- Re-check the chauffeur competitors in `data.BENCHMARKS` at the same time.
- Raise prices once a year in January, by a small step tied to real costs, with 30 days' notice. Never change a booked trip. No surge pricing.
