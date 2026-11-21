"""
Single source of truth for the business. Edit here; code and pages follow.

Consumed by:
  * build.py / marketing/  -> index.html, pricing.md, robots.txt, sitemap.xml
  * app/                   -> server-side quotes, eligibility, launch gates
  * tools/rate_model.py    -> the pricing proposal for owner review

TRUTH RULES (enforced by app/config.py launch gates before payments go live):
  * no placeholder contact details, invented reviews, ratings, ride counts,
    experience claims, licence numbers or amenities that are not in the car
  * prices are shown as *estimates confirmed before payment* until the owner
    sets PRICING["approved"] = True
"""

# ----------------------------------------------------------------- business
BRAND = {
    "name": "Celeste Luxury Limo",            # the business name (logo: static/brand, tools/make_brand.py)
    "short": "Celeste",                       # the wordmark; also the title suffix " | Celeste"
    "tagline": "Luxury Limo",                 # set under the wordmark in the logo
    "descriptor": "Private chauffeur service",
    "domain": "celesteluxurylimo.com",        # chosen 2026-11-21; register it, then point it at Render
    "phone_display": "(732) 666-7539",        # reservations line, answered or texted back
    "phone_raw": "+17326667539",
    "email": "reservations@celesteluxurylimo.com",  # PLACEHOLDER — the real reservations inbox
    "base_town": "Essex County, New Jersey",  # PLACEHOLDER — public town shown as a service-area business
    "authority_display": "",                  # e.g. "NJ limousine licence #… · USDOT #…" — only once issued
    "review_url": "",                         # Google Business Profile "Ask for reviews" link (g.page/r/...)
    "same_as": [],                            # official profile URLs once live: Google Business Profile, Yelp, LinkedIn…
    "placeholder": True,                      # set False once every field above is real
}

OPERATIONS = {
    # Flip once the owner confirms the licences and insurance behind every class switched on below:
    # NYC TLC vehicle + driver licences and base affiliation, TLC-minimum insurance for the vehicle's
    # class, and — for into_nyc trips from New Jersey — the base's interstate (FMCSA) authority.
    "authority_confirmed": False,
    "home_base": "essex",                     # place code the car starts and ends its day — CONFIRM
    "hours_label": "Reservations 24/7",
    # Pickup times offered in the booking form, like appointment slots (New York time).
    "slots": {"first": "04:00", "last": "23:30", "step_minutes": 30},
    "availability_note": "Limited availability during our launch — reserve early to secure your time.",
    # Which trips may be booked online (instantly or on approval). Every other route becomes a
    # "we'll arrange it" request — never refused. Classes are defined in domain/pricing.route_class.
    #   nyc_pickup        starts in NYC — covered by the owner's NYC TLC licence (dispatched via the TLC base)
    #   into_nyc          starts outside NYC, ends in it — owner reports this is covered. Crossing a state line
    #                     (e.g. Newark -> Manhattan) is interstate: FMCSA requires interstate operating authority
    #                     (USDOT/MC) for for-hire passenger carriers. CONFIRM the base holds it.
    #   nj_intrastate     both ends in NJ — needs an NJ municipal limousine licence (not held)
    #   interstate        crosses a state line without NYC — needs FMCSA interstate authority
    #   other_intrastate  both ends in one other state, outside NYC
    "authority": {"nyc_pickup": True, "into_nyc": True, "nj_intrastate": False, "interstate": False,
                  "other_intrastate": False},
}

# Launch fleet. Seeded into the database on boot; later vehicles and chauffeurs are added as rows
# (vehicles/drivers tables) without code changes. Nothing here is advertised until it is true.
VEHICLE = {
    "code": "escalade-2021",
    "display_name": "2021 Cadillac Escalade",
    "class_name": "Cadillac Escalade",
    "color": None,                            # e.g. "Black" — CONFIRM
    "trim": None,                             # Luxury / Premium Luxury / Sport / Platinum — CONFIRM
    "wheelbase": None,                        # "standard" or "ESV" — CONFIRM (changes luggage space a lot)
    "max_passengers": 6,                      # second-row captain's chairs + third row
    # Signature features of the actual vehicle (shown large on the site).
    "features": [
        ("captains", "Captain's chairs", "Two individual second-row seats with an aisle between them. Your own "
                                         "space to work, take a call or close your eyes."),
        ("sunroof", "Panoramic sunroof", "Open sky over the rear cabin — or the shade drawn for privacy and rest."),
        ("wifi", "Onboard Wi-Fi", "Connected from the moment the door closes. Network details are on the "
                                  "card beside your seat."),
    ],
    "child_seats": [{"type": "TO CONFIRM (e.g. convertible / booster)", "count": 1}],
    # What fits, in luggage "units": a large checked bag = 2, a carry-on = 1.
    # Basis (standard wheelbase): 25.5 cu ft behind the third row — Edmunds' load test of the same GM
    # platform with that exact volume fit two 26-inch checked bags, three carry-on roll-aboards and a
    # duffel (8 units). Third row folded: 72.6 cu ft. If the car is an ESV (41.5 / 94.1 cu ft), use
    # [(3, 22), (4, 18), (6, 13)]. Anything beyond capacity is confirmed with the client, never refused.
    "luggage_capacity": [(3, 16), (4, 12), (6, 8)],      # (up to N guests, units available)
    "luggage_guide": [
        ("Up to 6 guests", "2 large + 3 carry-ons", "All three rows in use"),
        ("4 guests", "4 large + 4 carry-ons", "Part of the third row folded"),
        ("Up to 3 guests", "6 large + 4 carry-ons", "Third row folded"),
    ],
    "capacity_tested": False,                 # set True after a real loading test confirms the guide
}

DRIVER = {"code": "ahmed", "display_name": "Ahmed"}     # first chauffeur; name shown to confirmed riders

# Everything on board, grouped the way executives think about a ride. Only available=True is shown.
AMENITY_GROUPS = ["Work", "Comfort", "Refreshment", "Care"]
AMENITIES = {
    "wifi":     {"group": "Work", "label": "Onboard Wi-Fi", "available": True},   # test with two devices
    "charging": {"group": "Work", "label": "Fast charging — USB-C and Lightning", "available": True},
    "quiet":    {"group": "Work", "label": "A quiet cabin for calls, on request", "available": True},
    "captains": {"group": "Comfort", "label": "Second-row captain's chairs", "available": True},
    "sunroof":  {"group": "Comfort", "label": "Panoramic sunroof", "available": True},
    "climate":  {"group": "Comfort", "label": "Cabin set to your temperature before pickup", "available": True},
    "water":    {"group": "Refreshment", "label": "Chilled still water", "available": True},
    "mints":    {"group": "Refreshment", "label": "Mints", "available": True},
    "towels":   {"group": "Refreshment", "label": "Unscented refresh towels", "available": True},
    "umbrella": {"group": "Care", "label": "Umbrella at the door", "available": True},
    "luggage":  {"group": "Care", "label": "Every bag handled for you", "available": True},
    "child_seat": {"group": "Care", "label": "Child seat on request", "available": True},
    "tissues":  {"group": "Care", "label": "Tissues", "available": True},
}

POLICY = {
    "version": "2026-11-v1-draft",            # bump on any change; each booking stores the version accepted
    "approved": False,                        # owner sign-off required before payments go live
    "free_cancel_hours": 24,
    "summary": "Complimentary cancellation up to 24 hours before pickup. Within 24 hours, refunds are reviewed "
               "individually. Payment is taken only once your reservation is confirmed.",
    "wait_included_min": 15,
}

# ---------------------------------------------------------------- services
# Service lines shown on the site. "booking" says how each is reserved online.
# Later phase (not offered yet): ("corporate", "Corporate accounts", "...", "inquiry").
SERVICES = [
    ("airport", "Airports & private aviation",
     "Newark, JFK and LaGuardia — and Teterboro, Morristown and Westchester for private flights. "
     "Met at the terminal or planeside, bags handled.", "transfer"),
    ("hourly", "By the hour",
     "A car and chauffeur at your disposal for meetings, roadshows and the in-between. "
     "Plans change; your chauffeur waits.", "hourly"),
    ("transfer", "Point to point",
     "Office to dinner, home to the city, hotel to the next appointment — any address across the region.",
     "transfer"),
    ("events", "Evenings & occasions",
     "Galas, Broadway, the Garden, weddings. Dropped at the door, collected when you are ready.", "hourly"),
    ("long", "Long distance",
     "Philadelphia, the Hamptons, the Shore and Connecticut — door to door, in comfort.", "transfer"),
]

# ------------------------------------------------------------------ places
# Bookable pickup and destination areas. Exact addresses are taken at booking; these
# drive price, timing and authority. mta = MTA bridge/tunnel crossings each way from NJ.
PLACE_GROUPS = ["Airports & private aviation", "New York City", "New Jersey", "Beyond"]
PLACES = [
    {"code": "ewr", "name": "Newark Liberty International (EWR)", "short": "Newark (EWR)", "kind": "airport",
     "state": "NJ", "group": "Airports & private aviation", "lat": 40.6895, "lon": -74.1745, "crossing_min": 10},
    {"code": "jfk", "name": "JFK International", "short": "JFK", "kind": "airport", "state": "NY", "nyc": True,
     "group": "Airports & private aviation", "lat": 40.6413, "lon": -73.7781, "crossing_min": 25, "mta": 1},
    {"code": "lga", "name": "LaGuardia (LGA)", "short": "LaGuardia", "kind": "airport", "state": "NY", "nyc": True,
     "group": "Airports & private aviation", "lat": 40.7769, "lon": -73.8740, "crossing_min": 20, "mta": 1},
    {"code": "teb", "name": "Teterboro (TEB) — private aviation", "short": "Teterboro", "kind": "aviation",
     "state": "NJ", "group": "Airports & private aviation", "lat": 40.8501, "lon": -74.0608, "crossing_min": 5},
    {"code": "mmu", "name": "Morristown (MMU) — private aviation", "short": "Morristown", "kind": "aviation",
     "state": "NJ", "group": "Airports & private aviation", "lat": 40.7994, "lon": -74.4149, "crossing_min": 5},
    {"code": "hpn", "name": "Westchester County (HPN)", "short": "Westchester (HPN)", "kind": "airport",
     "state": "NY", "group": "Airports & private aviation", "lat": 41.0670, "lon": -73.7076, "crossing_min": 10},
    {"code": "phl", "name": "Philadelphia International (PHL)", "short": "Philadelphia (PHL)", "kind": "airport",
     "state": "PA", "group": "Airports & private aviation", "lat": 39.8744, "lon": -75.2424, "crossing_min": 15},
    {"code": "manhattan", "name": "Manhattan", "short": "Manhattan", "kind": "city", "state": "NY", "nyc": True,
     "group": "New York City", "lat": 40.7549, "lon": -73.9840, "crossing_min": 20,
     "towns": ["Midtown", "Downtown", "Upper East Side", "Upper West Side", "Tribeca", "Financial District"]},
    {"code": "brooklyn", "name": "Brooklyn", "short": "Brooklyn", "kind": "city", "state": "NY", "nyc": True,
     "group": "New York City", "lat": 40.6782, "lon": -73.9442, "crossing_min": 20, "mta": 1},
    {"code": "queens", "name": "Queens", "short": "Queens", "kind": "city", "state": "NY", "nyc": True,
     "group": "New York City", "lat": 40.7282, "lon": -73.7949, "crossing_min": 20, "mta": 1},
    {"code": "bronx", "name": "The Bronx", "short": "Bronx", "kind": "city", "state": "NY", "nyc": True,
     "group": "New York City", "lat": 40.8448, "lon": -73.8648, "crossing_min": 15},
    {"code": "staten", "name": "Staten Island", "short": "Staten Island", "kind": "city", "state": "NY", "nyc": True,
     "group": "New York City", "lat": 40.5795, "lon": -74.1502, "crossing_min": 10},
    {"code": "hudson", "name": "Hudson County", "short": "Hudson", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 40.728, "lon": -74.078, "towns": ["Jersey City", "Hoboken", "Bayonne", "Union City", "Weehawken", "Secaucus", "North Bergen", "Kearny"]},
    {"code": "bergen", "name": "Bergen County", "short": "Bergen", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 40.886, "lon": -74.043, "towns": ["Hackensack", "Fort Lee", "Englewood", "Paramus", "Ridgewood", "Teaneck", "Fair Lawn", "Mahwah"]},
    {"code": "essex", "name": "Essex County", "short": "Essex", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 40.79, "lon": -74.23, "towns": ["Newark", "Montclair", "Livingston", "Bloomfield", "West Orange", "Millburn", "Short Hills", "Belleville"]},
    {"code": "union", "name": "Union County", "short": "Union", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 40.66, "lon": -74.3, "towns": ["Elizabeth", "Westfield", "Summit", "Cranford", "Scotch Plains", "Springfield", "Berkeley Heights", "Linden"]},
    {"code": "passaic", "name": "Passaic County", "short": "Passaic", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 40.9, "lon": -74.2, "towns": ["Paterson", "Clifton", "Wayne", "Passaic", "Hawthorne", "Totowa", "West Milford"]},
    {"code": "morris", "name": "Morris County", "short": "Morris", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 40.797, "lon": -74.481, "towns": ["Morristown", "Parsippany", "Madison", "Chatham", "Florham Park", "Randolph", "Denville", "Mendham"]},
    {"code": "sussex", "name": "Sussex County", "short": "Sussex", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 41.058, "lon": -74.753, "towns": ["Newton", "Sparta", "Vernon", "Hopatcong", "Franklin", "Hamburg"]},
    {"code": "warren", "name": "Warren County", "short": "Warren", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "North Jersey", "lat": 40.76, "lon": -74.98, "towns": ["Phillipsburg", "Hackettstown", "Washington", "Belvidere", "Blairstown"]},
    {"code": "middlesex", "name": "Middlesex County", "short": "Middlesex", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "Central Jersey", "lat": 40.5, "lon": -74.4, "towns": ["New Brunswick", "Edison", "Woodbridge", "Piscataway", "Perth Amboy", "Metuchen", "Old Bridge"]},
    {"code": "somerset", "name": "Somerset County", "short": "Somerset", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "Central Jersey", "lat": 40.59, "lon": -74.62, "towns": ["Somerville", "Bridgewater", "Bernardsville", "Bedminster", "Franklin Township", "Hillsborough"]},
    {"code": "monmouth", "name": "Monmouth County", "short": "Monmouth", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "Central Jersey", "lat": 40.3, "lon": -74.15, "towns": ["Red Bank", "Freehold", "Middletown", "Asbury Park", "Rumson", "Colts Neck", "Holmdel"]},
    {"code": "mercer", "name": "Mercer County", "short": "Mercer", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "Central Jersey", "lat": 40.3, "lon": -74.67, "towns": ["Princeton", "Trenton", "Hamilton", "Lawrenceville", "West Windsor", "Hopewell"]},
    {"code": "hunterdon", "name": "Hunterdon County", "short": "Hunterdon", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "Central Jersey", "lat": 40.51, "lon": -74.86, "towns": ["Flemington", "Clinton", "Lambertville", "Readington", "Califon"]},
    {"code": "ocean", "name": "Ocean County", "short": "Ocean", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "Central Jersey", "lat": 39.95, "lon": -74.2, "towns": ["Toms River", "Brick", "Point Pleasant", "Lakewood", "Jackson", "Manahawkin"]},
    {"code": "burlington", "name": "Burlington County", "short": "Burlington", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "South Jersey", "lat": 39.95, "lon": -74.9, "towns": ["Mount Laurel", "Moorestown", "Medford", "Marlton", "Willingboro", "Bordentown"]},
    {"code": "camden", "name": "Camden County", "short": "Camden", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "South Jersey", "lat": 39.93, "lon": -75.03, "towns": ["Cherry Hill", "Camden", "Haddonfield", "Voorhees", "Collingswood", "Gloucester City"]},
    {"code": "gloucester", "name": "Gloucester County", "short": "Gloucester", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "South Jersey", "lat": 39.78, "lon": -75.12, "towns": ["Deptford", "Washington Township", "Glassboro", "Woodbury", "Mullica Hill"]},
    {"code": "cumberland", "name": "Cumberland County", "short": "Cumberland", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "South Jersey", "lat": 39.49, "lon": -75.03, "towns": ["Vineland", "Millville", "Bridgeton"]},
    {"code": "salem", "name": "Salem County", "short": "Salem", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "South Jersey", "lat": 39.62, "lon": -75.4, "towns": ["Salem", "Pennsville", "Woodstown", "Carneys Point"]},
    {"code": "atlantic", "name": "Atlantic County", "short": "Atlantic", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "South Jersey", "lat": 39.43, "lon": -74.55, "towns": ["Atlantic City", "Egg Harbor Township", "Hammonton", "Galloway", "Ventnor", "Brigantine"]},
    {"code": "cape-may", "name": "Cape May County", "short": "Cape May", "kind": "area", "state": "NJ",
     "group": "New Jersey", "region": "South Jersey", "lat": 39.08, "lon": -74.82, "towns": ["Cape May", "Wildwood", "Ocean City", "Sea Isle City", "Avalon", "Stone Harbor"]},
    {"code": "westchester", "name": "Westchester County, NY", "short": "Westchester", "kind": "area", "state": "NY",
     "group": "Beyond", "lat": 41.0340, "lon": -73.7629, "crossing_min": 10,
     "towns": ["White Plains", "Scarsdale", "Rye", "Bronxville", "Chappaqua", "Purchase"]},
    {"code": "nassau", "name": "Nassau County (Long Island), NY", "short": "Long Island", "kind": "area",
     "state": "NY", "group": "Beyond", "lat": 40.7400, "lon": -73.5900, "crossing_min": 20, "mta": 1,
     "towns": ["Garden City", "Great Neck", "Manhasset", "Oyster Bay", "Roslyn"]},
    {"code": "hamptons", "name": "The Hamptons, NY", "short": "The Hamptons", "kind": "area", "state": "NY",
     "group": "Beyond", "lat": 40.9634, "lon": -72.1848, "crossing_min": 20, "mta": 1,
     "towns": ["Southampton", "East Hampton", "Bridgehampton", "Sag Harbor", "Montauk"]},
    {"code": "fairfield", "name": "Fairfield County, CT", "short": "Fairfield County", "kind": "area",
     "state": "CT", "group": "Beyond", "lat": 41.0534, "lon": -73.5387, "crossing_min": 10, "mta": 1,
     "towns": ["Greenwich", "Stamford", "Darien", "New Canaan", "Westport"]},
    {"code": "philadelphia", "name": "Philadelphia, PA", "short": "Philadelphia", "kind": "city", "state": "PA",
     "group": "Beyond", "lat": 39.9526, "lon": -75.1652, "crossing_min": 15},
]

# Shown on the site as "from" prices. Each must be a route the authority rules allow.
POPULAR_JOURNEYS = [("manhattan", "jfk"), ("manhattan", "ewr"), ("teb", "manhattan"), ("manhattan", "lga"),
                    ("bergen", "jfk"), ("ewr", "manhattan"), ("hudson", "manhattan"), ("brooklyn", "ewr"),
                    ("essex", "lga"), ("manhattan", "philadelphia")]

# ----------------------------------------------------------------- pricing
# Inputs to the cost model in app/domain/rates.py. Every number is the owner's to confirm.
PRICING = {
    "approved": False,                    # owner flips to True; until then prices are "estimates"
    "version": "2026-11-19-proposal",
    # by the hour, all-in (gratuity included)
    "hourly_cents": 14500,                # benchmark: Escalade hourly published ~$125/h + gratuity in NYC
    "hourly_min_hours": 3,
    "hourly_max_hours": 12,
    # point to point: price = committed time x rate + running cost + tolls + fixed share, grossed up for card fees
    "target_hourly_cents": 7500,          # chauffeur pay + vehicle margin per committed hour
    "running_cents_per_mile": 60,         # fuel (~15 mpg at ~$3.30) + tyres, service, depreciation
    "fixed_cents_per_trip": 2200,         # livery insurance, licences, phone, hosting / expected trips
    "card_fee_rate": 0.029, "card_fee_fixed_cents": 30,
    "min_fare_cents": 12500,
    "max_committed_min_for_instant_price": 480,
    # drive-time planning model (straight line x detour, distance-dependent speed, crossing penalty)
    "detour_factor": 1.3, "base_mph": 30, "max_extra_mph": 25, "mph_per_mile": 0.25,
    "early_arrival_min": 10, "curbside_min": 10, "min_approach_min": 15,
    "airport_wait_min": 45, "airport_parking_cents": 1200,
    "traffic_allowance": 1.2, "return_traffic_allowance": 1.1,
    # tolls — PANYNJ E-ZPass peak, class 1, 2026 table ($16.79, collected entering NY only);
    # Manhattan CBD charge $9 peak less up to $3 tunnel credit.
    "panynj_crossing_cents": 1679, "cbd_net_cents": 600,
    "mta_bridge_cents": 750,              # VERIFY current MTA E-ZPass bridge/tunnel toll
    "delaware_bridge_cents": 500,         # VERIFY Delaware River crossing into Pennsylvania
    "nj_toll_cents_per_mile": 6,          # Turnpike / Parkway approximation
    "service_buffer_min": 20,             # padding after the empty return before the next job
    # Launch offer. List prices stay at the long-run level (the reference price clients remember);
    # the introductory offer is shown as a time-boxed discount from them. Ending a discount meets far
    # less resistance than raising a posted price (Kahneman, Knetsch & Thaler, AER 1986, Proposition 4).
    "introductory": {"active": False, "label": "Founding client rate", "percent_off": 15,
                     "ends_local": "2027-02-28T23:59"},
}

# Competitive calibration — what clients compare us with. Add real checks before launch
# (Uber app, 10 routes x 3 times of day). all_in = fare + tolls + typical gratuity.
BENCHMARKS = [
    {"route": ("bergen", "jfk"), "who": "Air Brook (SUV)", "all_in_cents": 35500, "checked": "2026-11-19",
     "source": "airbrook.com: from $284.40 + tolls + >=15% gratuity"},
    {"route": None, "who": "Escalade ESV hourly, NYC", "all_in_cents": 15000, "unit": "hour", "checked": "2026-10",
     "source": "blackcarservice.nyc published hourly rate incl. gratuity"},
    {"route": None, "who": "Uber Black SUV, NYC 5 mi / 16 min", "all_in_cents": 11000, "checked": "2026-10-11",
     "source": "fareestimate.com $75-107 excl. tolls, fees and tip (midpoint + 20% tip)"},
]

# ---------------------------------------------------------------- test trip
# The owner's $1 test trip (app/services/test_trip.py): /admin -> "Start a $1 test trip" books and pays
# a real trip to check booking, Stripe, confirmation and the trip page, then cancel it to test the
# refund. It never blocks a client's time and never counts as revenue. Set "enabled": False when done.
TEST_TRIP = {
    "enabled": True,
    "amount_cents": 100,                      # $1.00
    "route": ("manhattan", "jfk"),            # any route the booking rules allow
    "lead_hours": 48,                         # pickup time shown on the test trip
    "hold_minutes": 60,                       # time to complete Stripe Checkout
}

# ------------------------------------------------------------------ payment
# What clients see at Stripe Checkout (Dashboard -> Settings -> Payment methods). Keep in step with Stripe.
PAYMENT = {
    "processor": "Stripe",
    "wallets": ["Apple Pay", "Google Pay", "Link"],
    "cards": ["Visa", "Mastercard", "American Express", "Discover"],
    "pay_later": "Klarna",                     # instalments; None to hide
}

# ------------------------------------------------------------------- voice
VOICE = {
    "mantra": "No surprises.",                   # internal test for every decision
    "tagline": "Expect exactly.",
    "tagline_alternatives": ["Set before you sit.", "Your time, attended to."],
    "promise": "We would rather decline tonight than be late tomorrow.",
    "tone": "Five-star hospitality: composed, precise, warm, discreet. Short sentences. No exclamation marks. "
            "Never: cheap, deal, luxury, elevate, VIP, seamless, world-class. (The registered name "
            "Celeste Luxury Limo is the one exception.)",
    "standard": [
        ("A Cadillac Escalade, every time", "Second-row captain's chairs, a panoramic sunroof and onboard Wi-Fi. "
                                            "Never a downgrade."),
        ("All-inclusive pricing", "Tolls, congestion charges and gratuity included. The quote is the receipt."),
        ("Only times we can keep", "Every time offered is checked against the calendar — the drive to you, "
                                   "your journey and the drive back."),
        ("Discretion as standard", "Your itinerary, your calls and your conversations stay in the car."),
        ("Real-time, honestly", "Your chauffeur's actual position and when it was reported. Never a guess."),
    ],
    "lines": [
        "Your office between appointments.",
        "The only surge here is legroom.",
        "Tolls ride free. So does the gratuity.",
        "The quote is the receipt.",
        "Manhattan looks better through a panoramic roof.",
        "Your laptop opens before the door closes.",
        "Captain's chairs. Nobody climbs over anybody.",
    ],
    "seasonal": {
        "thanksgiving": [
            "Skip the airport parking. Not the pie.",
            "The day before Thanksgiving is one of the worst on the road. Reserve your Wednesday ride early.",
            "Grandma gets the captain's chair.",
        ],
    },
}

# ----------------------------------------------------------------- content
INCLUDED = [
    ("Tolls and congestion charges", "Every bridge, tunnel and congestion charge on your route."),
    ("Gratuity", "Included. Nothing is expected at the door."),
    ("Meet and greet", "At the terminal, the FBO or your lobby."),
    ("Waiting time", "15 minutes at your door; 45 minutes at the airport, with your flight followed."),
    ("Your cabin, prepared", "Temperature, music and conversation set before you sit."),
]

FAQS = [
    ("Where do you operate?",
     "Across New Jersey, New York City, Westchester, Long Island, Fairfield County and Philadelphia — including "
     "Newark, JFK, LaGuardia, Teterboro, Morristown and Westchester airports. For anything further, ask; we "
     "arrange long-distance journeys regularly."),
    ("How is the price calculated?",
     "Point-to-point journeys are priced on the time and distance involved, including tolls, congestion charges "
     "and gratuity. Hourly service is a single all-inclusive hourly rate with a three-hour minimum. The price you "
     "confirm is the price you pay."),
    ("How quickly is my reservation confirmed?",
     "Usually the moment payment clears. Before a time is offered, our system checks the calendar — the drive to "
     "you, your journey and the drive back — so a confirmed reservation is one we can keep. Very short notice, "
     "unusual luggage or routes we arrange personally are confirmed by us first, typically within the hour."),
    ("Is it safe to pay online?",
     "Yes. Payment is taken on Stripe's secure checkout, certified to PCI DSS Level 1, the highest standard in the "
     "payments industry. Your card number is encrypted and never reaches our servers; with Apple Pay or Google "
     "Pay it is never shared at all. Your receipt arrives by email the moment you book."),
    ("Can I keep the car for the day?",
     "Yes. Book by the hour and your chauffeur stays with you between meetings — plans can change on the day. "
     "There is a three-hour minimum."),
    ("Is this a limousine or a black car service?",
     "A private chauffeur service — what many people call a black car service. Every journey is in a Cadillac "
     "Escalade rather than a stretch limousine, reserved in advance and driven by a professional chauffeur, with "
     "the price agreed before you travel."),
    ("Do you serve private aviation?",
     "Yes — Teterboro, Morristown and Westchester. Give us your tail number or FBO and we will meet you there."),
    ("What vehicle will arrive?",
     "A Cadillac Escalade with second-row captain's chairs, a panoramic sunroof and onboard Wi-Fi. Before pickup, "
     "your trip page shows your chauffeur's name, the vehicle and its plate."),
    ("Can I see where my car is?",
     "Yes. When your chauffeur sets off, your private trip page shows the vehicle's actual position and when it "
     "was last reported. If the signal drops, the page says so rather than guessing. Location is shown only "
     "during your journey and is deleted afterwards."),
    ("What is your cancellation policy?",
     "Complimentary cancellation up to 24 hours before pickup. Within 24 hours, refunds are reviewed individually, "
     "because the time was reserved for you."),
    ("How much luggage fits?",
     "Up to six guests. With every seat in use there is room for 2 large checked bags and 3 carry-ons. With four "
     "guests, part of the third row folds for 4 large bags and 4 carry-ons; with up to three guests, the third row "
     "folds for 6 large bags and 4 carry-ons. The booking form shows you instantly whether your luggage fits."),
    ("Is a child seat available?",
     "Yes, on request at no charge. Tell us the child's age and weight when you reserve and we will confirm the fit."),
    ("Is my information private?",
     "Your details are used only to provide your journey. Payment is handled by Stripe — we never see or store "
     "your card number. Trip links are private and expire."),
]

# Only real, attributable reviews, published with the client's permission. None yet.
REVIEWS = []
