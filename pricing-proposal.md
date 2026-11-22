# Pricing proposal — for owner review (not yet approved)

Inputs (data.PRICING): **$65 per committed vehicle-hour**, running cost **$0.60/mile**, fixed costs **$22/trip**, card fee 2.9% + $0.30, minimum fare **$125**, repositioning priced from **Manhattan**.

Hourly: **$145/hour all-inclusive**, 3-hour minimum.

Each direction's committed time = drive from the price reference to the pickup + waiting (45 min at an airport pickup, with parking) + the journey with a traffic allowance + curbside + the drive back. A journey's price is the average of both directions, so it costs the same either way — as the market quotes airport transfers. All prices include tolls, congestion charges and gratuity. Journeys committing more than 8 hours are quoted individually.

## Against the market

| Journey | Ours | Competitor (all-in) | Difference | Source, checked |
|---|---|---|---|---|
| Manhattan ↔ LaGuardia | $195 | Uber Black SUV (avg fare, Midtown West): $195 | +0% | gothamride.com/blog/black-car-vs-uber-black-nyc: $162 + 20% tip, 2026-11-22 |
| Manhattan ↔ Newark (EWR) | $230 | Uber Black SUV (avg fare, Midtown West): $262 | -12% | gothamride.com/blog/black-car-vs-uber-black-nyc: $218 + 20% tip, 2026-11-22 |
| Manhattan ↔ LaGuardia | $195 | NYC Lux Ride (Escalade): $228 | -14% | nycluxride.com/rates: $190 incl. tolls, fees, taxes + 20% tip, 2026-11-22 |
| Manhattan ↔ JFK | $255 | NYC Lux Ride (Escalade): $264 | -3% | nycluxride.com/rates: $220 incl. tolls, fees, taxes + 20% tip, 2026-11-22 |
| Manhattan ↔ Newark (EWR) | $230 | NYC Lux Ride (Escalade): $264 | -13% | nycluxride.com/rates: $220 incl. tolls, fees, taxes + 20% tip, 2026-11-22 |
| Manhattan ↔ LaGuardia | $195 | LS Black Cars (Escalade ESV, from): $210 | -7% | lsblackcars.com: from $169.05 incl. STC + fuel; tolls + 20% tip added, 2026-11-22 |
| Manhattan ↔ LaGuardia | $195 | Gotham Ride (Escalade, all-in): $332 | -41% | gothamride.com: from $332 incl. tolls and tip (premium end), 2026-11-22 |
| Manhattan ↔ JFK | $255 | Gotham Ride (Escalade, all-in): $337 | -24% | gothamride.com: from $337 incl. tolls and tip (premium end), 2026-11-22 |
| Bergen ↔ JFK | $315 | Air Brook (SUV): $355 | -11% | airbrook.com: from $284.40 + tolls + >=15% gratuity, 2026-11-19 |
| By the hour | $145/h | NYC Executive Car (Escalade ESV) hourly: $144/h | +1% | nycexecutivecar.com: $120/h, 2-hour minimum, + 20% tip, 2026-11-22 |

## Popular journeys

| Journey | Price | Vehicle committed | Route class |
|---|---|---|---|
| Manhattan → JFK | $255 | 2h42 | nyc_pickup |
| Manhattan → Newark (EWR) | $230 | 2h17 | nyc_pickup |
| Teterboro → Manhattan | $200 | 1h58 | into_nyc |
| Manhattan → LaGuardia | $195 | 1h58 | nyc_pickup |
| Bergen → JFK | $315 | 3h12 | into_nyc |
| Newark (EWR) → Manhattan | $230 | 2h17 | into_nyc |
| Hudson → Manhattan | $155 | 1h28 | into_nyc |
| Brooklyn → Newark (EWR) | $260 | 2h32 | nyc_pickup |
| Essex → LaGuardia | $285 | 2h47 | into_nyc |
| Manhattan → Philadelphia | $555 | 5h30 | nyc_pickup |

## New Jersey counties to airports

| County | Newark (EWR) | JFK | LaGuardia | Teterboro |
|---|---|---|---|---|
| Hudson County | $195 | $290 | $230 | $185 |
| Bergen County | $240 | $315 | $245 | $175 |
| Essex County | $225 | $340 | $285 | $215 |
| Union County | $240 | $360 | $315 | $260 |
| Passaic County | $260 | $355 | $290 | $215 |
| Morris County | $305 | $415 | $365 | $295 |
| Sussex County | $415 | $510 | $455 | $390 |
| Warren County | $435 | $535 | $490 | $430 |
| Middlesex County | $310 | $410 | $375 | $325 |
| Somerset County | $350 | $455 | $410 | $355 |
| Monmouth County | $350 | $410 | $390 | $360 |
| Mercer County | $415 | $505 | $470 | $425 |
| Hunterdon County | $420 | $515 | $475 | $420 |
| Ocean County | $465 | $525 | $500 | $470 |
| Burlington County | $525 | $605 | $575 | $530 |
| Camden County | $550 | $630 | $605 | $555 |
| Gloucester County | $600 | $690 | $660 | $615 |
| Cumberland County | $675 | $755 | $730 | $690 |
| Salem County | $700 | $785 | $760 | $715 |
| Atlantic County | $645 | $705 | $690 | $655 |
| Cape May County | $790 | custom | custom | $800 |

Which routes are booked online follows the operating authority (data.OPERATIONS['authority']); others are priced the same way but arranged personally.
