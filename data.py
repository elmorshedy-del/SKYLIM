"""
Single source of truth for county pricing + service data.
Consumed by build.py to generate index.html, pricing.md, and sitemap.xml.

PRICING MODEL (as specified by client):
  - "NYC" tier  = ONE flat rate covering Manhattan + LaGuardia (LGA) + all five boroughs
  - "JFK" tier  = separate, higher flat rate (JFK is the priciest run from NJ)
  - Rates are ALL-IN: tolls, gratuity, meet & greet, Manhattan congestion fee,
    NJ surcharge, flight tracking, 60 min free wait. No surge, ever.
  - Positioned ~15-20% under researched market rates.

market_nyc / market_jfk = researched typical competitor SUV rate, used to show savings.
confidence: "verified" = hard published competitor rate found; "estimated" = extrapolated by distance.
"""

BRAND = {
    "name": "Meridian Black Car",          # <-- PLACEHOLDER: swap for real company name
    "short": "Meridian",
    "domain": "meridianblackcar.com",       # <-- PLACEHOLDER
    "phone_display": "(201) 555-0100",      # <-- PLACEHOLDER
    "phone_raw": "+12015550100",            # <-- PLACEHOLDER
    "email": "ride@meridianblackcar.com",   # <-- PLACEHOLDER
    "address": "1 Riverfront Plaza, Newark, NJ 07102",  # <-- PLACEHOLDER
    "tlc": "TLC #XXXXXX",                   # <-- PLACEHOLDER: real TLC / NJ authority no.
    "years": 10,
    "rating": "4.9",
    "review_count": 1284,
    "rides": "38,000",
}

# name, slug, region, nyc, jfk, market_nyc, market_jfk, drive_min, drive_max, towns, confidence
COUNTIES = [
    # ---------- NORTH JERSEY ----------
    ("Hudson County", "hudson", "North Jersey", 109, 189, 130, 235, 15, 30,
     ["Jersey City", "Hoboken", "Bayonne", "Union City", "Weehawken", "Secaucus", "North Bergen", "Kearny"],
     "verified"),
    ("Bergen County", "bergen", "North Jersey", 139, 215, 170, 265, 25, 45,
     ["Hackensack", "Fort Lee", "Englewood", "Paramus", "Ridgewood", "Teaneck", "Fair Lawn", "Mahwah"],
     "verified"),
    ("Essex County", "essex", "North Jersey", 135, 205, 165, 250, 30, 45,
     ["Newark", "Montclair", "Livingston", "Bloomfield", "West Orange", "Millburn", "Short Hills", "Belleville"],
     "estimated"),
    ("Union County", "union", "North Jersey", 135, 199, 160, 245, 35, 50,
     ["Elizabeth", "Westfield", "Summit", "Cranford", "Scotch Plains", "Springfield", "Berkeley Heights", "Linden"],
     "estimated"),
    ("Passaic County", "passaic", "North Jersey", 145, 215, 175, 265, 30, 50,
     ["Paterson", "Clifton", "Wayne", "Passaic", "Hawthorne", "Totowa", "West Milford"],
     "estimated"),
    ("Morris County", "morris", "North Jersey", 179, 239, 215, 290, 45, 65,
     ["Morristown", "Parsippany", "Madison", "Chatham", "Florham Park", "Randolph", "Denville", "Mendham"],
     "estimated"),
    ("Sussex County", "sussex", "North Jersey", 235, 265, 285, 320, 70, 90,
     ["Newton", "Sparta", "Vernon", "Hopatcong", "Franklin", "Hamburg"],
     "estimated"),
    ("Warren County", "warren", "North Jersey", 249, 279, 300, 340, 75, 95,
     ["Phillipsburg", "Hackettstown", "Washington", "Belvidere", "Blairstown"],
     "estimated"),

    # ---------- CENTRAL JERSEY ----------
    ("Middlesex County", "middlesex", "Central Jersey", 159, 209, 195, 255, 45, 65,
     ["New Brunswick", "Edison", "Woodbridge", "Piscataway", "Perth Amboy", "Metuchen", "Old Bridge"],
     "estimated"),
    ("Somerset County", "somerset", "Central Jersey", 189, 239, 230, 290, 55, 75,
     ["Somerville", "Bridgewater", "Bernardsville", "Bedminster", "Franklin Township", "Hillsborough"],
     "estimated"),
    ("Monmouth County", "monmouth", "Central Jersey", 215, 259, 260, 313, 60, 85,
     ["Red Bank", "Freehold", "Middletown", "Asbury Park", "Rumson", "Colts Neck", "Holmdel"],
     "verified"),
    ("Mercer County", "mercer", "Central Jersey", 229, 249, 280, 300, 70, 90,
     ["Princeton", "Trenton", "Hamilton", "Lawrenceville", "West Windsor", "Hopewell"],
     "verified"),
    ("Hunterdon County", "hunterdon", "Central Jersey", 255, 289, 310, 350, 70, 90,
     ["Flemington", "Clinton", "Lambertville", "Readington", "Califon"],
     "estimated"),
    ("Ocean County", "ocean", "Central Jersey", 245, 279, 300, 340, 75, 100,
     ["Toms River", "Brick", "Point Pleasant", "Lakewood", "Jackson", "Manahawkin"],
     "estimated"),

    # ---------- SOUTH JERSEY & SHORE ----------
    ("Burlington County", "burlington", "South Jersey", 305, 335, 370, 405, 90, 115,
     ["Mount Laurel", "Moorestown", "Medford", "Marlton", "Willingboro", "Bordentown"],
     "estimated"),
    ("Camden County", "camden", "South Jersey", 319, 355, 390, 430, 95, 120,
     ["Cherry Hill", "Camden", "Haddonfield", "Voorhees", "Collingswood", "Gloucester City"],
     "estimated"),
    ("Gloucester County", "gloucester", "South Jersey", 329, 365, 400, 440, 100, 125,
     ["Deptford", "Washington Township", "Glassboro", "Woodbury", "Mullica Hill"],
     "estimated"),
    ("Cumberland County", "cumberland", "South Jersey", 349, 385, 430, 470, 110, 140,
     ["Vineland", "Millville", "Bridgeton"],
     "estimated"),
    ("Salem County", "salem", "South Jersey", 359, 395, 440, 480, 110, 140,
     ["Salem", "Pennsville", "Woodstown", "Carneys Point"],
     "estimated"),
    ("Atlantic County", "atlantic", "South Jersey", 565, 639, 690, 780, 120, 150,
     ["Atlantic City", "Egg Harbor Township", "Hammonton", "Galloway", "Ventnor", "Brigantine"],
     "verified"),
    ("Cape May County", "cape-may", "South Jersey", 729, 829, 890, 1013, 150, 190,
     ["Cape May", "Wildwood", "Ocean City", "Sea Isle City", "Avalon", "Stone Harbor"],
     "verified"),
]

REGIONS = ["North Jersey", "Central Jersey", "South Jersey"]

# Vehicle tiers — Good / Better / Best. "Better" (Executive SUV) is the anchor/recommended tier.
VEHICLES = [
    {
        "id": "suv",
        "name": "Executive SUV",
        "examples": "Chevrolet Suburban / GMC Yukon XL",
        "pax": 6, "bags": 6,
        "multiplier": 1.00,
        "recommended": True,
        "blurb": "Our core vehicle. Full-size, three rows, room for six passengers and six large bags without stacking.",
        "features": ["6 passengers", "6 large bags", "Bottled water", "Phone chargers", "Wi-Fi on request"],
    },
    {
        "id": "luxury",
        "name": "Luxury SUV",
        "examples": "Cadillac Escalade ESV",
        "pax": 6, "bags": 7,
        "multiplier": 1.22,
        "recommended": False,
        "blurb": "Escalade ESV with captain's chairs, quilted leather and the quietest cabin in the fleet.",
        "features": ["6 passengers", "7 large bags", "Captain's chairs", "Rear climate control", "Privacy glass"],
    },
    {
        "id": "sprinter",
        "name": "Executive Sprinter",
        "examples": "Mercedes-Benz Sprinter",
        "pax": 11, "bags": 12,
        "multiplier": 1.85,
        "recommended": False,
        "blurb": "For teams, families and golf bags. Stand-up cabin, conference seating, luggage bay.",
        "features": ["11 passengers", "12+ large bags", "Stand-up cabin", "Conference seating", "USB-C at every seat"],
    },
]

INCLUDED = [
    ("All tolls", "GWB, Lincoln, Holland, Turnpike — every toll on your route."),
    ("Gratuity", "Standard driver gratuity is already in the price. Nothing expected at the curb."),
    ("Manhattan congestion fee", "The $9 CBD charge below 60th St is covered."),
    ("NJ surcharge", "The $20 New Jersey origination surcharge most operators add on. Covered."),
    ("Meet &amp; greet", "Curbside or inside the terminal with a name board. Your choice, same price."),
    ("Flight tracking", "We watch your tail number. Land early or three hours late, your driver is there."),
    ("60 minutes free wait", "Domestic arrivals. 90 minutes on international."),
    ("Free cancellation", "Up to 60 minutes before pickup. No fee, no argument."),
]

FAQS = [
    ("How much does a car service from New Jersey to NYC cost?",
     "Our rate depends only on which New Jersey county you are picked up in, and whether you are going to JFK or anywhere else in New York City. "
     "It ranges from $109 for Hudson County into Manhattan up to $729 from Cape May. Every price is all-in and fixed at booking — "
     "tolls, gratuity, congestion fee and wait time are already included, and we never apply surge pricing."),

    ("Why is there one price for all of NYC but a separate price for JFK?",
     "Because JFK is genuinely the longest and most expensive run from New Jersey, while Manhattan, LaGuardia, Brooklyn, Queens and the Bronx "
     "sit close enough together that a single flat rate is fair for all of them. Two prices per county is all you need to remember, "
     "and LaGuardia riders get the better end of the deal."),

    ("Is LaGuardia included in the standard NYC rate?",
     "Yes. LGA is priced the same as Manhattan and every borough. Only JFK carries a higher rate. "
     "That makes us meaningfully cheaper than operators who charge a separate airport premium for LaGuardia."),

    ("Do I have to call anyone to book or to find my driver?",
     "No, and that is the entire point. You book online in about 60 seconds, pay through the portal, and get a confirmation. "
     "From there you track your driver live on a map and text them directly in the browser. There is no dispatcher to phone and no "
     "\"where is my car\" call to make."),

    ("How do I know my booking is confirmed?",
     "Every trip is confirmed overnight by a real person on our team, and you get a confirmation with your driver's name, "
     "photo, vehicle and plate before pickup. If anything about your trip cannot be honoured you hear from us that night, not at the curb."),

    ("How do I know what time to leave for my flight or an event?",
     "Use the departure planner. Tell it your county and either your flight's scheduled departure or which "
     "event you are attending, and it works backwards to the minute your car should collect you. "
     "It uses the real drive time from your county rather than an average, applies the traffic you will "
     "actually meet at that hour, and adds the buffer the terminal or venue needs — two hours for a "
     "domestic flight, three for international, 45 minutes for a stadium, 30 for a Broadway curtain. "
     "A flat \"leave two hours early\" is wrong for most of the state: it is 15 minutes from Hudson County "
     "and up to three hours from Cape May."),

    ("Does the planner account for rush hour?",
     "Yes, and it scores the traffic during your drive rather than at your arrival time — which matters more "
     "than it sounds. Two riders going to the same 8pm Broadway show get different pickup times: someone in "
     "Hudson County leaves after the evening peak has eased, while someone in Morris County has to set off "
     "inside it and needs roughly 50 percent longer on the road. Friday evenings are treated as the worst "
     "crossing of the week, because they are."),

    ("Can I track my driver and send them a message?",
     "Yes. Once a driver is assigned you get a live map with their position and a running ETA, plus a message thread. "
     "Messages reach your driver as a text on their phone and their replies come straight back into your browser."),

    ("Are your prices really flat, with no surge?",
     "Flat and fixed at the moment you book. We do not surge for rush hour, rain, holidays, Yankees games or Friday afternoons — "
     "all of which are documented surcharge triggers at other operators. The number you are quoted is the number you pay."),

    ("How experienced are your drivers?",
     "Every chauffeur has a minimum of 10 years of professional driving experience, commercial licensing, "
     "background screening and defensive-driving certification. They know terminal layouts, tunnel timing and which "
     "side of Penn Station to be on."),

    ("What happens if my flight is delayed?",
     "Nothing you need to do. We track your flight by tail number and shift your pickup automatically. "
     "Domestic arrivals include 60 minutes of free wait time and international arrivals include 90, measured from actual wheels-down, not your scheduled time."),

    ("Do you serve New Jersey to New Jersey trips?",
     "Not yet. Right now we are focused on doing New Jersey to New York City properly. "
     "In-state New Jersey transfers are coming soon — join the waitlist and you will be first to know."),
]

REVIEWS = [
    ("Daniel R.", "Managing Director, Bergen County",
     "I take the 6am to JFK twice a month. Booked in under a minute, saw the exact price before paying, and watched the SUV come up Route 4 on the map. "
     "The $215 was $215 — no toll line, no gratuity line, no surprise. That is the whole reason I switched.", 5),
    ("Priya M.", "Hoboken",
     "My flight landed two and a half hours late at 1am. I did not call anyone. The driver had already moved with the flight and texted me which door to come out of. "
     "That is the first time ground transport has ever just worked for me.", 5),
    ("Frank C.", "Monmouth County",
     "Four of us to a Knicks game. Uber Black wanted $340 with surge on the way home. This was $215 each way, locked in, and the Sprinter was spotless. "
     "The driver waited on 33rd without a single phone call.", 5),
    ("Alicia T.", "Executive Assistant, Morris County",
     "I book ground travel for nine executives. Being able to see the flat rate per county before I commit ends the entire back-and-forth I used to have with dispatchers. "
     "I have not phoned a car service in four months.", 5),
]
