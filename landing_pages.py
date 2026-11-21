"""
Copy for the search landing pages — one page per real search intent.

Business facts (places, prices, policy, vehicle) still come from data.py; this file
holds only the words on each page and the searches it answers.

Price tokens are filled from the live cost model at build time, so copy can never
drift from what the booking engine charges:
    {ewr>manhattan}   "from" price for that journey ("a price on request" if not instantly priced)
    {hourly}          hourly rate          {hourly_min}  minimum hours
    {airport_wait}    minutes of waiting included at airport pickups

Rules (tested in tests/test_seo.py):
  * every journey listed in "routes" must be one the authority rules let us sell online
  * the primary search phrase appears in the title, the H1 and the description —
    and is never repeated so often that it reads unnaturally (Google spam policies)
  * brand voice: none of data.VOICE's banned words
  * "searches" records the target queries and their measured US monthly volume
    (Ubersuggest, 2026-11-21) for docs/SEO-PLAN.md; it is never written into the page
"""

AIRPORTS = {
    "path": "/airport-transfers",
    "parent": None,
    "crumb": "Airport transfers",
    "link": "Airport car service",
    "title": "Airport Car Service — Newark, JFK, LaGuardia & Teterboro",
    "description": "Airport car service in a Cadillac Escalade for Newark, JFK, LaGuardia, Teterboro and four more "
                   "airports. Met inside, flight followed, tolls and gratuity included.",
    "primary": "airport car service",
    "serves": ["ewr", "jfk", "lga", "teb", "mmu", "hpn", "phl"],
    "searches": [("airport car service newark airport", 1600), ("car service at jfk airport", 880),
                 ("laguardia airport car service", 1300)],
    "eyebrow": "Airports & private aviation",
    "h1": "Airport car service for New York and New Jersey.",
    "lede": "Seven airports, one standard. Your chauffeur follows your flight, meets you inside and carries "
            "every bag to a Cadillac Escalade — with tolls, parking and gratuity already in the price.",
    "points": ["{airport_wait} minutes of waiting included", "Flight or tail number followed",
               "Met inside, not at the curb"],
    "preset": ("", "ewr"),
    "airports": [
        ("ewr", "/airport-transfers/newark", "Terminals A, B and C. The closest major airport for most of New Jersey.",
         ("hudson", "ewr")),
        ("jfk", "/airport-transfers/jfk", "Every terminal. The region's main international gateway.",
         ("bergen", "jfk")),
        ("lga", "/airport-transfers/laguardia", "Terminals A, B and C. Mostly domestic, closest to Midtown.",
         ("bergen", "lga")),
        ("teb", "/airport-transfers/teterboro", "Private aviation, about twelve miles from Midtown.",
         ("teb", "manhattan")),
        ("mmu", None, "Private aviation in the heart of Morris County.", ("hudson", "mmu")),
        ("hpn", None, "Westchester County Airport, for commercial and private flights.", ("bergen", "hpn")),
        ("phl", None, "Philadelphia International, for South Jersey and beyond.", ("mercer", "phl")),
    ],
    "routes": [],
    "sections": [
        ("What every airport journey includes", [
            "Your flight number tells your chauffeur when you actually land, not when you were scheduled to. "
            "{airport_wait} minutes of waiting are part of every airport pickup — time for the aircraft, passport "
            "control and baggage — and the airport parking is ours to pay.",
            "Departures are planned the other way round: we work back from your flight and the traffic at that hour, "
            "and offer only times we can keep.",
        ]),
    ],
    "steps": [],
    "faqs": [
        ("Which airports do you serve?",
         "Newark, JFK and LaGuardia; Teterboro, Morristown and Westchester for private and business aviation; and "
         "Philadelphia International. The form above prices your exact journey."),
        ("Is waiting time included at the airport?",
         "Yes. {airport_wait} minutes of waiting and the airport parking are included in every airport pickup."),
        ("Do you meet me inside the terminal?",
         "Yes. Your chauffeur waits in the arrivals hall near baggage claim, or at your FBO for private flights. "
         "Your trip page shows their name, the vehicle and its plate."),
    ],
    "related": ["/airport-transfers/newark", "/airport-transfers/jfk", "/airport-transfers/laguardia",
                "/airport-transfers/teterboro"],
}

NEWARK = {
    "path": "/airport-transfers/newark",
    "parent": "/airport-transfers",
    "crumb": "Newark (EWR)",
    "link": "Newark Airport car service",
    "title": "Newark Airport Car Service — EWR to NYC & New Jersey",
    "description": "Newark Airport car service in a Cadillac Escalade. Met at baggage claim, flight followed, "
                   "tolls and gratuity included — to Manhattan or anywhere in New Jersey.",
    "primary": "newark airport car service",
    "serves": ["ewr"],
    "searches": [("car service nyc to ewr", 2400), ("car service at newark airport", 1900),
                 ("airport car service newark airport", 1600), ("nj car service to newark airport", 1300),
                 ("newark airport town car service", 1000), ("ewr limo service nj", 1000),
                 ("car service from newark airport", 880), ("newark airport limo service nj", 720),
                 ("car service from newark airport to manhattan", 210), ("newark airport to manhattan", 5400)],
    "eyebrow": "Newark Liberty International · EWR",
    "h1": "Newark Airport car service, met at baggage claim.",
    "lede": "Your chauffeur follows your flight, waits in the arrivals hall at Terminal A, B or C and carries your "
            "bags to a Cadillac Escalade. Manhattan or anywhere in New Jersey, with tolls and gratuity already "
            "in the price.",
    "points": ["{airport_wait} minutes of waiting included", "Flight followed, early or late",
               "Up to 6 guests and their luggage"],
    "preset": ("ewr", ""),
    "routes": [("ewr", "manhattan"), ("manhattan", "ewr"), ("hudson", "ewr"), ("essex", "ewr"), ("union", "ewr"),
               ("bergen", "ewr"), ("morris", "ewr"), ("somerset", "ewr"), ("monmouth", "ewr"),
               ("brooklyn", "ewr"), ("westchester", "ewr"), ("mercer", "ewr")],
    "routes_h2": "All-inclusive prices, to and from Newark.",
    "sections": [
        ("Newark Airport to Manhattan", [
            "Newark is often the quickest way into Manhattan from the air, but the Hudson decides the journey. By "
            "car it is typically 30 to 60 minutes to Midtown, longer at the evening peak. Your price already "
            "includes the tunnel toll and Manhattan's congestion charge, so the traffic is our concern, not "
            "your bill.",
            "The honest comparison: AirTrain and a train to Penn Station costs least, with a change and your bags "
            "to manage. A taxi or ride-hail from the curb varies with the hour and the queue. A private chauffeur "
            "makes sense when you have luggage, are travelling together, land late, or want to work on the way — "
            "booked ahead, met inside, one price, door to door.",
        ]),
    ],
    "steps_h2": "How your Newark pickup works.",
    "steps": [
        ("plane", "We follow your flight", "Add your flight number when you reserve. Your chauffeur watches it "
                                           "on the day and times the pickup to your actual landing."),
        ("pin", "Met in arrivals", "Your chauffeur waits near baggage claim in your terminal. Your trip page shows "
                                   "when they are in position."),
        ("bag", "Bags handled", "Every bag carried to the car, parked a short walk away."),
        ("route", "Straight to your door", "Tolls, tunnel and congestion charge are already in your price."),
    ],
    "faqs": [
        ("How much is a car service from Newark Airport to Manhattan?",
         "From {ewr>manhattan} one way, all-inclusive: tolls, Manhattan's congestion charge, airport parking and "
         "gratuity. Manhattan to Newark is from {manhattan>ewr}. The form above shows the exact price for your "
         "address and time before you pay."),
        ("How long will my chauffeur wait if my flight is late?",
         "{airport_wait} minutes of waiting are included at the airport. Because we follow your flight number, a "
         "delay moves your pickup with it whenever the calendar allows, and your trip page always shows the "
         "current plan."),
        ("Where exactly do we meet at Newark?",
         "Inside the arrivals hall of your terminal — A, B or C — near baggage claim. Before pickup, your trip page "
         "shows your chauffeur's name, the vehicle and its plate."),
        ("Do you serve Newark Airport from all of New Jersey?",
         "Yes — from Hudson and Essex County, from {hudson>ewr} and {essex>ewr}, to Morris, Somerset, Monmouth and "
         "Mercer, and from Manhattan, Brooklyn and Westchester. The form above prices your exact area."),
        ("Is it a town car or a limousine?",
         "Neither. Every journey is in a Cadillac Escalade with second-row captain's chairs, a panoramic sunroof "
         "and onboard Wi-Fi — the room of an SUV with the composure of a town car."),
    ],
    "related": ["/airport-transfers/jfk", "/airport-transfers/laguardia", "/airport-transfers/teterboro",
                "/nj-limo-service", "/nyc-chauffeur-service"],
}

JFK = {
    "path": "/airport-transfers/jfk",
    "parent": "/airport-transfers",
    "crumb": "JFK",
    "link": "JFK airport car service",
    "title": "JFK Airport Car Service — To and From New Jersey",
    "description": "JFK airport car service in a Cadillac Escalade between JFK and New Jersey or Connecticut. Met "
                   "in arrivals, flight followed, tolls and gratuity included.",
    "primary": "jfk airport car service",
    "serves": ["jfk"],
    "searches": [("car service at jfk airport", 880), ("jfk airport car service", 720),
                 ("car service nyc to jfk", 720), ("jfk airport limousine service", 590)],
    "eyebrow": "John F. Kennedy International · JFK",
    "h1": "JFK airport car service for New Jersey.",
    "lede": "From Bergen, Hudson, Essex or Morris County to any JFK terminal and back. It is the longest airport "
            "journey in the region, so the cabin matters: captain's chairs, Wi-Fi and quiet for calls, with "
            "every toll and the gratuity in the price.",
    "points": ["Every JFK terminal", "Flight followed on arrival", "{airport_wait} minutes of waiting included"],
    "preset": ("", "jfk"),
    "routes": [("bergen", "jfk"), ("hudson", "jfk"), ("essex", "jfk"), ("morris", "jfk"), ("monmouth", "jfk"),
               ("fairfield", "jfk"), ("jfk", "bergen"), ("jfk", "hudson")],
    "routes_h2": "All-inclusive prices, New Jersey and Connecticut to JFK.",
    "sections": [
        ("Planning the drive to JFK", [
            "From North Jersey, allow 60 to 90 minutes outside rush hour, and more on Friday afternoons or the day "
            "before a holiday. We build that margin into the pickup time we offer — and into the price, which "
            "does not change if the Van Wyck does.",
            "From Manhattan or Long Island? Journeys that begin and end in New York State are arranged personally "
            "rather than booked instantly. Choose the route above and send it to us; we reply with a firm price.",
        ]),
    ],
    "steps_h2": "How your JFK journey works.",
    "steps": [
        ("calendar", "Timed to your flight", "Tell us your flight; we suggest a pickup time with the traffic "
                                             "built in, or follow your arrival on the day."),
        ("pin", "Met in arrivals", "Your chauffeur waits in the arrivals hall of your terminal, near baggage claim."),
        ("wifi", "Work on the way", "Captain's chairs, Wi-Fi and fast charging for the longest airport run in "
                                    "the region."),
        ("tag", "One price", "Bridges, tolls and gratuity included. The quote is the receipt."),
    ],
    "faqs": [
        ("How much is a car service from New Jersey to JFK?",
         "From {hudson>jfk} from Hudson County and {bergen>jfk} from Bergen County, one way and all-inclusive: "
         "tolls, airport parking and gratuity. The form above prices your exact address and time."),
        ("Can you take me from Manhattan to JFK?",
         "Journeys that start and end in New York are arranged personally rather than booked online. Send us the "
         "details through the form and we will reply with a firm price."),
        ("Which JFK terminals do you serve?",
         "All of them. Add your airline and flight number when you reserve and your chauffeur meets you at the "
         "right terminal."),
        ("How early should I leave for JFK?",
         "Your airline's guidance comes first; many travellers aim to arrive two hours before a domestic flight "
         "and three before an international one. Tell us your flight and we will suggest a pickup time with the "
         "traffic built in."),
    ],
    "related": ["/airport-transfers/newark", "/airport-transfers/laguardia", "/airport-transfers/teterboro",
                "/nj-limo-service"],
}

LAGUARDIA = {
    "path": "/airport-transfers/laguardia",
    "parent": "/airport-transfers",
    "crumb": "LaGuardia",
    "link": "LaGuardia Airport car service",
    "title": "LaGuardia Airport Car Service — LGA to New Jersey",
    "description": "LaGuardia Airport car service in a Cadillac Escalade, between LGA and New Jersey or "
                   "Connecticut. Met inside Terminal A, B or C; tolls and gratuity included.",
    "primary": "laguardia airport car service",
    "serves": ["lga"],
    "searches": [("car service nyc laguardia airport", 1900), ("car service from laguardia airport", 1600),
                 ("laguardia airport car service", 1300)],
    "eyebrow": "LaGuardia · LGA",
    "h1": "LaGuardia Airport car service, from New Jersey and back.",
    "lede": "The closest airport to Midtown is the hardest to reach from New Jersey — two river crossings and the "
            "Grand Central Parkway. We plan the route and the timing; you have a captain's chair and Wi-Fi for "
            "the length of it.",
    "points": ["Terminals A, B and C", "Flight followed on arrival", "{airport_wait} minutes of waiting included"],
    "preset": ("", "lga"),
    "routes": [("hudson", "lga"), ("bergen", "lga"), ("essex", "lga"), ("morris", "lga"), ("fairfield", "lga"),
               ("lga", "bergen"), ("lga", "hudson")],
    "routes_h2": "All-inclusive prices, New Jersey and Connecticut to LaGuardia.",
    "sections": [
        ("From the city or Queens?", [
            "Journeys that begin and end in New York — Manhattan to LaGuardia, for example — are arranged "
            "personally rather than booked online. Send us the route and we reply with a firm price.",
            "From New Jersey or Fairfield County, the price above is the price you pay: both crossings, airport "
            "parking and gratuity included.",
        ]),
    ],
    "steps_h2": "How your LaGuardia pickup works.",
    "steps": [
        ("plane", "We follow your flight", "Add your flight number; your pickup is timed to your actual landing."),
        ("pin", "Met inside", "Your chauffeur waits in the arrivals area of Terminal A, B or C, near baggage "
                              "claim."),
        ("bag", "Bags handled", "Every bag carried to the car."),
        ("route", "Home across the river", "Both crossings and the gratuity are already in your price."),
    ],
    "faqs": [
        ("How much is a car service from LaGuardia to New Jersey?",
         "From {lga>hudson} to Hudson County and {lga>bergen} to Bergen County, one way and all-inclusive. New "
         "Jersey to LaGuardia is from {hudson>lga}. The form above prices your exact address."),
        ("Where do you meet me at LaGuardia?",
         "In the arrivals area of your terminal, near baggage claim. Your trip page shows your chauffeur's name, "
         "the vehicle and its plate, and when they are in position."),
        ("Can you take me from Manhattan to LaGuardia?",
         "Journeys that start and end in New York are arranged personally. Send us the details through the form "
         "and we reply with a firm price."),
    ],
    "related": ["/airport-transfers/newark", "/airport-transfers/jfk", "/airport-transfers/teterboro",
                "/nj-limo-service"],
}

TETERBORO = {
    "path": "/airport-transfers/teterboro",
    "parent": "/airport-transfers",
    "crumb": "Teterboro (TEB)",
    "link": "Teterboro car service",
    "title": "Teterboro Car Service — Private Aviation Chauffeur",
    "description": "Teterboro car service for private flights: a Cadillac Escalade at your FBO, timed to your tail "
                   "number, to Manhattan, New Jersey or Connecticut. All-inclusive.",
    "primary": "teterboro car service",
    "serves": ["teb"],
    "searches": [("teterboro airport car service", None), ("car service teterboro airport", None),
                 ("teterboro car service", None)],          # autocomplete-confirmed; volume not available
    "eyebrow": "Teterboro · TEB",
    "h1": "Teterboro car service, timed to your tail number.",
    "lede": "Private flights keep their own schedule. Give us your tail number and FBO; your chauffeur follows "
            "the flight and is waiting when the door opens. Midtown is about twelve miles away, and your price "
            "already includes the tunnel and the congestion charge.",
    "points": ["Any Teterboro FBO", "Tail number followed", "Manhattan, New Jersey and Connecticut"],
    "preset": ("teb", "manhattan"),
    "routes": [("teb", "manhattan"), ("manhattan", "teb"), ("teb", "bergen"), ("teb", "morris"),
               ("teb", "westchester"), ("teb", "fairfield"), ("teb", "brooklyn"), ("morris", "teb")],
    "routes_h2": "All-inclusive prices, to and from Teterboro.",
    "sections": [
        ("Also Morristown and Westchester", [
            "The same service runs from Morristown (MMU) and Westchester County (HPN). Choose either airport in "
            "the form above and add your tail number when you reserve.",
        ]),
    ],
    "steps_h2": "How your Teterboro pickup works.",
    "steps": [
        ("plane", "Send the tail number", "Add your tail number and FBO when you reserve."),
        ("clock", "We follow the flight", "Your chauffeur watches the flight and adjusts to your actual arrival."),
        ("car", "Waiting at the FBO", "At the FBO's door — or planeside, where the FBO permits it."),
        ("route", "Straight to Manhattan", "Tunnel, tolls and congestion charge already in your price."),
    ],
    "faqs": [
        ("How much is a car service from Teterboro to Manhattan?",
         "From {teb>manhattan} one way, all-inclusive: tunnel toll, Manhattan's congestion charge and gratuity. "
         "Manhattan to Teterboro is from {manhattan>teb}."),
        ("Do you meet the aircraft planeside?",
         "Where the FBO permits it, yes. Otherwise your chauffeur waits at the FBO's front door."),
        ("What if our departure time changes?",
         "Private schedules move. Tell us as soon as it changes; we adjust whenever the calendar allows, and your "
         "trip page always shows the current plan."),
        ("Can you collect us from Morristown or Westchester instead?",
         "Yes. Both are in the booking form, with the same service and all-inclusive pricing."),
    ],
    "related": ["/airport-transfers/newark", "/nyc-chauffeur-service", "/nj-limo-service",
                "/airport-transfers"],
}

NYC = {
    "path": "/nyc-chauffeur-service",
    "parent": None,
    "crumb": "New York City",
    "link": "Chauffeur service in New York City",
    "title": "Chauffeur Service NYC — Executive Black Car",
    "description": "Chauffeur service between New York City and New Jersey in a Cadillac Escalade: Newark and "
                   "Teterboro transfers, and by the hour for meetings and evenings.",
    "primary": "chauffeur service",
    "serves": ["city:New York City", "state:New Jersey"],
    "searches": [("chauffeur service new york city", 8100), ("chauffeur service nyc", 6600),
                 ("car service nyc", 6600), ("limo service new york city", 5400), ("limo service nyc", 4400),
                 ("black car service nyc", 1300), ("luxury chauffeur service nyc", 720),
                 ("private chauffeur service nyc", 390), ("nyc executive limo service", 480)],
    "eyebrow": "New York City",
    "h1": "New York City chauffeur service, on your schedule.",
    "lede": "A Cadillac Escalade and a professional chauffeur for the city's long days — roadshows, client dinners, "
            "the run to Newark or Teterboro. Book by the hour and your chauffeur waits between appointments; book "
            "by the journey and the price is fixed before you go.",
    "points": ["By the hour, from {hourly}", "Manhattan to Newark and Teterboro", "Gratuity always included"],
    "preset": ("manhattan", "ewr"),
    "routes": [("manhattan", "ewr"), ("manhattan", "teb"), ("hudson", "manhattan"), ("bergen", "manhattan"),
               ("essex", "manhattan"), ("morris", "manhattan"), ("brooklyn", "ewr"), ("manhattan", "philadelphia")],
    "routes_h2": "All-inclusive prices, the city and beyond.",
    "sections": [
        ("How we serve the city", [
            "We are a New Jersey chauffeur service, and our New York work is built around the Hudson: Manhattan to "
            "Newark or Teterboro, a day of meetings that starts or ends in New Jersey, dinner in the city from home "
            "in Bergen or Essex County. Journeys that begin and end inside the five boroughs are arranged "
            "personally — send us the details and we reply with a firm price.",
            "Some call it a black car service, others a limo service. What arrives is the same every time: a "
            "Cadillac Escalade — never a downgrade — and an executive chauffeur who knows the difference between "
            "the Lincoln and the Holland at five o'clock.",
        ]),
    ],
    "steps_h2": "A chauffeur by the hour.",
    "steps": [
        ("clock", "Reserve the hours", "{hourly} per hour, {hourly_min}-hour minimum, gratuity included."),
        ("car", "Your chauffeur stays close", "Between meetings the car waits nearby, ready when you are."),
        ("route", "Change plans freely", "Add a stop or move a meeting within your hours — the price does not "
                                         "change."),
        ("briefcase", "Work in between", "Captain's chairs, Wi-Fi and a quiet cabin for calls."),
    ],
    "faqs": [
        ("How much is a chauffeur service in NYC by the hour?",
         "{hourly} per hour with a {hourly_min}-hour minimum, gratuity included. Your chauffeur stays with you "
         "between appointments."),
        ("Is this a black car service?",
         "Yes, in the sense most people mean: a professionally driven car reserved in advance, never a ride-hail. "
         "The vehicle is always a Cadillac Escalade."),
        ("Can you drive me around Manhattan all day?",
         "A day that begins or ends in New Jersey, yes — reserve by the hour. A day that stays entirely within New "
         "York City is arranged personally; send us the plan and we reply with a firm price."),
        ("How much is a car from Manhattan to Newark Airport?",
         "From {manhattan>ewr} one way, all-inclusive. To Teterboro, from {manhattan>teb}."),
    ],
    "related": ["/airport-transfers/newark", "/airport-transfers/teterboro", "/nj-limo-service",
                "/airport-transfers"],
}

NEW_JERSEY = {
    "path": "/nj-limo-service",
    "parent": None,
    "crumb": "New Jersey",
    "link": "New Jersey limo service",
    "title": "Limo Service NJ — Cadillac Escalade Chauffeur",
    "description": "New Jersey limo service in a Cadillac Escalade, not a stretch. Airports, Manhattan, hourly and "
                   "long distance from every county. Tolls and gratuity included.",
    "primary": "limo service",
    "serves": ["state:New Jersey"],
    "searches": [("limo service in nj", 1600), ("limo service nj", 1300), ("limo service new jersey", 1300),
                 ("car service nj", 1000), ("car service new jersey", 720), ("car service jersey city nj", 170),
                 ("car service hoboken nj", 110), ("limo service in princeton nj", 110)],
    "eyebrow": "New Jersey",
    "h1": "New Jersey limo service, in a Cadillac Escalade.",
    "lede": "Not a stretch limousine — a Cadillac Escalade with captain's chairs, Wi-Fi and a panoramic sunroof, "
            "driven by a professional chauffeur. From every county to Newark, JFK, LaGuardia, Teterboro or "
            "Manhattan, with tolls and gratuity in the price.",
    "points": ["Every New Jersey county", "Airports, Manhattan and long distance", "Up to 6 guests"],
    "preset": ("", "ewr"),
    "routes": [("hudson", "ewr"), ("essex", "jfk"), ("bergen", "manhattan"), ("morris", "ewr"),
               ("bergen", "lga"), ("union", "ewr"), ("monmouth", "manhattan"), ("mercer", "ewr")],
    "routes_h2": "All-inclusive prices from across New Jersey.",
    "sections": [
        ("Car service across New Jersey", [
            "Whether you start in Jersey City or Hoboken, Montclair, Morristown, Summit or Princeton, each journey is "
            "priced for its own time and distance — so a short run to Newark costs what it should, and a long "
            "one to JFK is quoted before you go.",
            "In New Jersey, limo, car service and chauffeur are used interchangeably. What matters is what "
            "arrives: a Cadillac Escalade, a professional chauffeur and a price that already includes tolls and "
            "gratuity.",
        ]),
    ],
    "steps": [],
    "faqs": [
        ("Do you serve all of New Jersey?",
         "Yes, from Bergen to Cape May. Journeys are priced instantly wherever we can; the longest are confirmed "
         "personally, usually within the hour."),
        ("How much is a limo from North Jersey to Newark Airport?",
         "From {hudson>ewr} from Hudson County and {morris>ewr} from Morris County, one way and all-inclusive. The "
         "form above prices your exact address."),
        ("Do you offer stretch limousines or party buses?",
         "No. Every journey is in a Cadillac Escalade for up to six guests. For a larger party, ask — we will tell "
         "you honestly whether we can help."),
        ("Can I reserve for a wedding?",
         "Yes, for the couple or the family — reserve by the hour. We do not run guest shuttles."),
    ],
    "related": ["/airport-transfers/newark", "/airport-transfers/jfk", "/airport-transfers/laguardia",
                "/nyc-chauffeur-service"],
}

PAGES = [AIRPORTS, NEWARK, JFK, LAGUARDIA, TETERBORO, NYC, NEW_JERSEY]
BY_PATH = {p["path"]: p for p in PAGES}
