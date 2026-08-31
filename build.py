#!/usr/bin/env python3
"""Generates index.html, pricing.md, robots.txt, sitemap.xml from data.py."""
import json, os, datetime, html as H
from data import BRAND, COUNTIES, REGIONS, VEHICLES, INCLUDED, FAQS, REVIEWS
from build_css import CSS
from build_js import JS

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://" + BRAND["domain"]
TODAY = datetime.date.today().isoformat()

IMG_HERO = "https://hyperagent.com/api/files/usergenerated/threads/cms4ld1kf0m1i08ad5r3b1smi/images/c42601b7-f849-4fc2-a103-58874e150176.png"
IMG_CABIN = "https://hyperagent.com/api/files/usergenerated/threads/cms4ld1kf0m1i08ad5r3b1smi/images/080eb403-f9ce-4ab7-979f-ee557d9ee1f4.png"
IMG_CHAUF = "https://hyperagent.com/api/files/usergenerated/threads/cms4ld1kf0m1i08ad5r3b1smi/images/1e650598-46af-4805-af2a-c777aa867306.png"

TITLE = "NJ to NYC Black Car Service | Flat-Rate SUVs | " + BRAND["short"]
DESC = ("Flat-rate chauffeured SUVs from every New Jersey county to NYC and JFK. "
        "Book online in 60 seconds, track your driver live and text them direct. No phone calls.")

# ---------------------------------------------------------------- structures
def rate_rows():
    """Crawlable county rate table, grouped by region."""
    out = []
    for region in REGIONS:
        out.append('<tr class="rr"><th colspan="5" scope="colgroup">' + region + '</th></tr>')
        for (name, slug, reg, nyc, jfk, mnyc, mjfk, dmin, dmax, towns, conf) in COUNTIES:
            if reg != region:
                continue
            search = (name + " " + " ".join(towns)).lower()
            snyc, sjfk = mnyc - nyc, mjfk - jfk
            out.append(
                '<tr data-county="' + slug + '" data-search="' + H.escape(search, quote=True) + '" id="' + slug + '-county">'
                '<th scope="row">' + name + '<small>' + ", ".join(towns[:4]) + '</small></th>'
                '<td class="p num">' + f"${nyc}" + '<span class="was num">' + f"${mnyc}" + '</span></td>'
                '<td class="p num">' + f"${jfk}" + '<span class="was num">' + f"${mjfk}" + '</span></td>'
                '<td class="sv num">save $' + str(snyc) + ' / $' + str(sjfk) + '</td>'
                '<td class="act"><a href="#quote" data-book-county="' + slug + '" '
                'aria-label="Get a quote from ' + name + '">Get quote</a></td>'
                '</tr>'
            )
    return "\n".join(out)


def county_options():
    out = []
    for region in REGIONS:
        out.append('<optgroup label="' + region + '">')
        for (name, slug, reg, *_rest) in COUNTIES:
            if reg == region:
                out.append('<option value="' + slug + '">' + name + '</option>')
        out.append('</optgroup>')
    return "\n".join(out)


def footer_counties():
    return "\n".join(
        '<li><a href="#' + slug + '-county">' + name.replace(" County", "") + ' County car service</a></li>'
        for (name, slug, *_r) in COUNTIES
    )


def included_list():
    return "\n".join(
        '<li>' + SVG_CHECK + '<div><b>' + t + '</b><span>' + d + '</span></div></li>'
        for (t, d) in INCLUDED
    )


def vehicle_cards():
    imgs = {"suv": IMG_HERO, "luxury": IMG_CABIN, "sprinter": IMG_CHAUF}
    alts = {
        "suv": "Black Chevrolet Suburban executive SUV on a Manhattan street at dusk",
        "luxury": "Quilted black leather rear cabin of a Cadillac Escalade ESV with ambient lighting",
        "sprinter": "Professional chauffeur holding the rear door of a black SUV at an airport terminal",
    }
    out = []
    base = COUNTIES[1][3]  # Bergen NYC rate as the illustrative "from" price
    for v in VEHICLES:
        feats = "".join('<li>' + SVG_CHECK_SM + '<span>' + f + '</span></li>' for f in v["features"])
        out.append(
            '<article class="veh' + (' rec' if v["recommended"] else '') + '">'
            + ('<div class="veh-badge">Most booked</div>' if v["recommended"] else '')
            + '<div class="veh-img"><img src="' + imgs[v["id"]] + '" alt="' + alts[v["id"]] + '" loading="lazy" width="800" height="500"></div>'
            '<div class="veh-bd"><h3>' + v["name"] + '</h3>'
            '<div class="ex">' + v["examples"] + '</div>'
            '<p>' + v["blurb"] + '</p>'
            '<ul>' + feats + '</ul>'
            '<div class="veh-ft"><div class="veh-pr"><b class="num">$' + str(round(base * v["multiplier"])) + '</b>'
            '<span>Bergen County → NYC, all-in</span></div>'
            '<button class="btn btn-ghost-l btn-full" data-goto-book data-track="fleet-' + v["id"] + '">'
            'Reserve this vehicle</button></div></div></article>'
        )
    return "\n".join(out)


def faq_html():
    return "\n".join(
        '<details' + (' open' if i == 0 else '') + '><summary>' + q + '</summary>'
        '<div class="ans"><p>' + a + '</p></div></details>'
        for i, (q, a) in enumerate(FAQS)
    )


def review_cards():
    return "\n".join(
        '<article class="rev"><div class="rev-st" aria-label="' + str(st) + ' out of 5 stars">'
        + "★" * st + '</div><p>' + txt + '</p>'
        '<div class="rev-by"><div class="rev-av" aria-hidden="true">' + who[0] + '</div>'
        '<div><b>' + who + '</b><span>' + role + '</span></div></div></article>'
        for (who, role, txt, st) in REVIEWS
    )


# ------------------------------------------------------------- structured data
def jsonld():
    offers = []
    for (name, slug, reg, nyc, jfk, mnyc, mjfk, dmin, dmax, towns, conf) in COUNTIES:
        for dest, price, code in (("New York City (incl. LaGuardia & all boroughs)", nyc, "NYC"),
                                  ("John F. Kennedy International Airport", jfk, "JFK")):
            offers.append({
                "@type": "Offer",
                "name": "Chauffeured SUV — " + name + " to " + dest,
                "priceCurrency": "USD",
                "price": str(price),
                "priceSpecification": {
                    "@type": "PriceSpecification",
                    "price": str(price), "priceCurrency": "USD",
                    "valueAddedTaxIncluded": True,
                    "description": "All-in flat rate. Includes tolls, gratuity, congestion fee, "
                                   "meet & greet, flight tracking and 60 minutes of wait time.",
                },
                "areaServed": {"@type": "AdministrativeArea", "name": name + ", New Jersey"},
                "availability": "https://schema.org/InStock",
                "category": code,
                "itemOffered": {"@type": "Service", "name": "Black car SUV transfer",
                                "serviceType": "Chauffeured ground transportation"},
            })

    biz = {
        "@type": ["LocalBusiness", "TaxiService"],
        "@id": SITE + "/#business",
        "name": BRAND["name"],
        "url": SITE,
        "telephone": BRAND["phone_raw"],
        "email": BRAND["email"],
        "image": IMG_HERO,
        "priceRange": "$$-$$$",
        "description": DESC,
        "address": {"@type": "PostalAddress", "streetAddress": "1 Riverfront Plaza",
                    "addressLocality": "Newark", "addressRegion": "NJ",
                    "postalCode": "07102", "addressCountry": "US"},
        "geo": {"@type": "GeoCoordinates", "latitude": 40.7357, "longitude": -74.1724},
        "openingHoursSpecification": [{
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "opens": "00:00", "closes": "23:59",
        }],
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": BRAND["rating"],
                            "reviewCount": str(BRAND["review_count"]), "bestRating": "5"},
        "areaServed": [{"@type": "AdministrativeArea", "name": c[0] + ", New Jersey"} for c in COUNTIES]
                      + [{"@type": "City", "name": "New York City"}],
        # Full per-county offers live once, in the Service node's OfferCatalog below,
        # and are referenced here rather than duplicated (keeps the payload lean).
        "makesOffer": {"@id": SITE + "/#rates-catalog"},
        "review": [{
            "@type": "Review",
            "author": {"@type": "Person", "name": w},
            "reviewRating": {"@type": "Rating", "ratingValue": str(s), "bestRating": "5"},
            "reviewBody": t,
        } for (w, r, t, s) in REVIEWS],
    }

    service = {
        "@type": "Service",
        "@id": SITE + "/#service",
        "serviceType": "New Jersey to New York City black car and chauffeured SUV service",
        "provider": {"@id": SITE + "/#business"},
        "areaServed": {"@type": "State", "name": "New Jersey"},
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "@id": SITE + "/#rates-catalog",
            "name": "Flat rates by New Jersey county",
            "itemListElement": offers,
        },
    }

    faq = {
        "@type": "FAQPage",
        "@id": SITE + "/#faq",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for (q, a) in FAQS]
        # per-county pricing questions: the SEO play that replaces 21 separate pages
        + [{"@type": "Question",
            "name": "How much is a car service from " + name + " to " + d_label + "?",
            "acceptedAnswer": {"@type": "Answer", "text":
                "A chauffeured SUV from " + name + " to " + d_label + " is a flat " + f"${price}" +
                ", all-in. That includes tolls, gratuity, the Manhattan congestion fee, meet and greet, "
                "flight tracking and 60 minutes of free wait time. Typical drive time is " +
                f"{dmin}–{dmax} minutes. The price is fixed when you book and never surges."}}
           for (name, slug, reg, nyc, jfk, mnyc, mjfk, dmin, dmax, towns, conf) in COUNTIES
           for (d_label, price) in (("New York City", nyc), ("JFK Airport", jfk))],
    }

    return json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "@id": SITE + "/#org", "name": BRAND["name"],
             "url": SITE, "logo": IMG_HERO, "telephone": BRAND["phone_raw"]},
            {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE, "name": BRAND["name"],
             "publisher": {"@id": SITE + "/#org"}, "inLanguage": "en-US"},
            {"@type": "WebPage", "@id": SITE + "/#page", "url": SITE + "/", "name": TITLE,
             "description": DESC, "isPartOf": {"@id": SITE + "/#site"},
             "dateModified": TODAY, "primaryImageOfPage": IMG_HERO},
            biz, service, faq,
            {"@type": "BreadcrumbList", "@id": SITE + "/#crumbs", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Flat rates by county", "item": SITE + "/#rates"},
                {"@type": "ListItem", "position": 3, "name": "Book a ride", "item": SITE + "/#book"},
            ]},
        ],
    }, separators=(",", ":"))


# ------------------------------------------------------------------ svg bits
SVG_CHECK = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M20 6L9 17l-5-5"/></svg>')
SVG_CHECK_SM = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                '<path d="M20 6L9 17l-5-5"/></svg>')
SVG_SHIELD = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z"/><path d="M9 12l2 2 4-4"/></svg>')
SVG_CLOCK = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
             '<path d="M12 7v5l3.5 2"/></svg>')
SVG_PLANE = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M2 13l9-2V4a1.5 1.5 0 013 0v7l8 2v2l-8-1.5V19l2.5 2v1L12 20l-4.5 2v-1L10 19v-5.5L2 15v-2z"/></svg>')
SVG_TAG = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M20.6 13.4l-7.2 7.2a2 2 0 01-2.8 0l-7.2-7.2a2 2 0 01-.6-1.4V5a2 2 0 012-2h7a2 2 0 011.4.6l7.4 7.4a2 2 0 010 2.4z"/>'
           '<circle cx="7.5" cy="7.5" r="1.4"/></svg>')
SVG_CHAT = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M21 12a8 8 0 01-8 8H8l-5 3 1.5-5A8 8 0 1121 12z"/></svg>')
SVG_PIN = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1116 0z"/><circle cx="12" cy="10" r="2.6"/></svg>')
SVG_SEND = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>')
SVG_MOON = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M21 12.8A8.5 8.5 0 1111.2 3a6.6 6.6 0 009.8 9.8z"/></svg>')
SVG_LOCK = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="4" y="10" width="16" height="11" rx="2"/>'
            '<path d="M8 10V7a4 4 0 018 0v3"/></svg>')


# ==========================================================================
#  HTML
# ==========================================================================
def render():
    yrs = BRAND["years"]
    hudson_nyc = COUNTIES[0][3]
    cape_nyc = COUNTIES[-1][3]

    head = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<link rel="canonical" href="{SITE}/">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="theme-color" content="#08080A">
<meta name="author" content="{BRAND['name']}">
<meta name="geo.region" content="US-NJ">
<meta name="geo.placename" content="Newark, New Jersey">
<meta name="ICBM" content="40.7357,-74.1724">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND['name']}">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{SITE}/">
<meta property="og:image" content="{IMG_HERO}">
<meta property="og:image:alt" content="Black Cadillac Escalade on a Manhattan street at dusk">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITLE}">
<meta name="twitter:description" content="{DESC}">
<meta name="twitter:image" content="{IMG_HERO}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="preload" as="image" href="{IMG_HERO}" fetchpriority="high">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" defer></script>
<script type="application/ld+json">{jsonld()}</script>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
"""

    header = f"""
<div class="announce">
  Now serving <b>New Jersey → New York City</b>. In-state New Jersey transfers
  <b>coming soon</b> — <a href="#soon">join the waitlist</a>.
</div>
<header>
  <div class="wrap">
    <nav class="nav" aria-label="Primary">
      <a class="logo" href="#top">
        <span class="logo-mk" aria-hidden="true">M</span>
        <span>{BRAND['name']}<small>NJ → NYC</small></span>
      </a>
      <button class="burger" id="burger" aria-label="Menu" aria-expanded="false" aria-controls="nav-links">☰</button>
      <div class="nav-links" id="nav-links">
        <a href="#rates">Flat rates</a>
        <a href="#how">How it works</a>
        <a href="#plan">When to leave</a>
        <a href="#fleet">Fleet</a>
        <a href="#events">NYC events</a>
        <a href="#track">Track &amp; text</a>
        <a href="#faq">FAQ</a>
      </div>
      <div class="nav-cta">
        <a class="nav-tel" href="tel:{BRAND['phone_raw']}"><span>24/7 dispatch</span>{BRAND['phone_display']}</a>
        <button class="btn btn-gold" data-goto-book data-track="header">Book a ride</button>
      </div>
    </nav>
  </div>
</header>
<main id="main">
<a id="top"></a>
"""

    hero = f"""
<section class="hero" id="quote">
  <div class="hero-bg" aria-hidden="true">
    <img src="{IMG_HERO}" alt="" width="1536" height="672" fetchpriority="high">
  </div>
  <div class="wrap hero-in">
    <div>
      <p class="eyebrow">New Jersey → New York City · {yrs}+ year chauffeurs</p>
      <h1>Get to your gate without ever<br><em>picking up the phone.</em></h1>
      <p class="hero-sub">
        One flat price per New Jersey county. Book online in about sixty seconds,
        pay in the portal, then watch your driver on a live map and text them direct.
        No dispatcher. No hold music. No “where is my car?”
      </p>
      <div class="hero-chips">
        <span class="chip">{SVG_TAG} Flat rate — never surges</span>
        <span class="chip">{SVG_PLANE} Flight tracked automatically</span>
        <span class="chip">{SVG_CHAT} Text your driver in-browser</span>
        <span class="chip">{SVG_SHIELD} Licensed &amp; fully insured</span>
      </div>
    </div>

    <div class="quote">
      <div class="quote-hd">
        <strong>Get your flat rate</strong>
        <span class="pill">3 fields · instant price</span>
      </div>
      <form class="quote-bd" id="quote-form" novalidate>
        <div class="fld">
          <label for="q-county">Pickup county <span class="req" aria-hidden="true">*</span></label>
          <select class="ctl" id="q-county" name="q-county" required
                  aria-describedby="q-county-err">
            <option value="">Choose your New Jersey county…</option>
            {county_options()}
          </select>
          <span class="fld-err" id="q-county-err">Please choose your pickup county.</span>
        </div>

        <div class="fld">
          <label>Going to <span class="req" aria-hidden="true">*</span></label>
          <div class="seg" role="radiogroup" aria-label="Destination">
            <input type="radio" name="q-dest" id="q-dest-nyc" value="nyc" checked>
            <label for="q-dest-nyc">New York City<small>Manhattan, LGA, all boroughs</small></label>
            <input type="radio" name="q-dest" id="q-dest-jfk" value="jfk">
            <label for="q-dest-jfk">JFK Airport<small>Separate rate</small></label>
          </div>
        </div>

        <div class="fld">
          <label for="q-when">Pickup date &amp; time <span class="req" aria-hidden="true">*</span></label>
          <input class="ctl" type="datetime-local" id="q-when" name="q-when" required
                 aria-describedby="q-when-err">
          <span class="fld-err" id="q-when-err">Please choose a pickup date and time.</span>
        </div>

        <button class="btn btn-gold btn-lg btn-full" type="submit" data-track="hero-quote">
          {SVG_TAG} Get my flat rate
        </button>
        <p class="quote-note">Free to check. No card, no account, no callback.</p>
      </form>

      <div class="result" id="quote-result" role="status">
        <div class="result-top">
          <div>
            <div class="price-lbl">Your all-in price</div>
            <div class="price num" id="qr-price"><sup>$</sup>0</div>
          </div>
          <div class="result-rt">
            <b id="qr-route">—</b>
            <span id="qr-meta">—</span>
          </div>
        </div>
        <div class="save" id="qr-save">{SVG_TAG} <span id="qr-save-tx"></span></div>
        <div class="inc-grid">
          <div>{SVG_CHECK} All tolls</div>
          <div>{SVG_CHECK} Gratuity</div>
          <div>{SVG_CHECK} Congestion fee</div>
          <div>{SVG_CHECK} Meet &amp; greet</div>
          <div>{SVG_CHECK} Flight tracking</div>
          <div>{SVG_CHECK} 60 min free wait</div>
        </div>
        <button class="btn btn-dark btn-lg btn-full" data-goto-book data-track="quote-result">
          Book this ride →
        </button>
        <p class="quote-note">Free cancellation up to 60 minutes before pickup.</p>
      </div>
    </div>
  </div>
</section>

<section class="trust" style="padding:0">
  <div class="wrap" style="padding-left:0;padding-right:0;max-width:var(--mx)">
    <div class="trust-in">
      <div class="trust-i"><b class="num"><span class="stars">★★★★★</span></b><span>{BRAND['rating']} from {BRAND['review_count']:,} riders</span></div>
      <div class="trust-i"><b class="num">{yrs}+ yrs</b><span>Minimum chauffeur experience</span></div>
      <div class="trust-i"><b class="num">{BRAND['rides']}</b><span>Trips completed</span></div>
      <div class="trust-i"><b class="num">$0</b><span>Surge pricing, ever</span></div>
      <div class="trust-i"><b class="num">24/7</b><span>Every day of the year</span></div>
    </div>
  </div>
</section>
"""

    compare = f"""
<section id="why">
  <div class="wrap">
    <div class="hd ctr">
      <p class="eyebrow">The difference</p>
      <h2>You already know what the alternative feels like</h2>
      <p class="lede">Rideshare at 5am to catch a 7am flight is a gamble. A traditional car
      service means phone calls, a quote you cannot see, and a bill that grows on the way.
      Here is the same trip, three ways.</p>
    </div>
    <div class="tbl-scroll">
      <table class="cmp">
        <thead>
          <tr>
            <th scope="col">Bergen County → JFK, 5:30am</th>
            <th scope="col">Rideshare (Black)</th>
            <th scope="col">Traditional car service</th>
            <th scope="col" class="us">{BRAND['short']}</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Price you see before booking</td><td class="no">Estimate only</td><td class="no">“Call for a quote”</td><td class="us yes">Exact, fixed</td></tr>
          <tr><td>Surge / peak surcharge</td><td class="no">Up to 3–5×</td><td class="no">Friday &amp; holiday surcharges</td><td class="us yes">Never</td></tr>
          <tr><td>Tolls &amp; congestion fee</td><td class="no">Added after</td><td class="no">Added after</td><td class="us yes">Included</td></tr>
          <tr><td>Gratuity</td><td class="no">Expected on top</td><td class="no">18–20% on top</td><td class="us yes">Included</td></tr>
          <tr><td>Driver experience</td><td class="no">Unknown</td><td>Varies</td><td class="us yes">{yrs}+ years, vetted</td></tr>
          <tr><td>Flight delay handling</td><td class="no">Ride cancels</td><td>Phone the office</td><td class="us yes">Automatic</td></tr>
          <tr><td>Find your driver</td><td>In-app</td><td class="no">Call dispatch</td><td class="us yes">Live map + direct text</td></tr>
          <tr><td>Vehicle guaranteed</td><td class="no">Whatever arrives</td><td>Usually</td><td class="us yes">Named model &amp; plate</td></tr>
          <tr><td>Trip confirmed in advance</td><td class="no">No</td><td>Sometimes</td><td class="us yes">Overnight, by a person</td></tr>
        </tbody>
      </table>
    </div>
    <p class="lede" style="margin-top:20px;font-size:.92rem">
      Comparison reflects publicly advertised competitor terms and documented surcharges as of {TODAY}.
      Rideshare multiples vary by demand.
    </p>
  </div>
</section>
"""

    how = f"""
<section class="dark" id="how">
  <div class="wrap">
    <div class="hd">
      <p class="eyebrow">How it works</p>
      <h2>Three steps. Zero phone calls.</h2>
    </div>
    <div class="g3">
      <div class="step">
        <div class="step-n">1</div>
        <h3>Price it and book it</h3>
        <p>Choose your county and where you are going. The exact all-in price appears
        instantly — then pay in the portal. About sixty seconds, start to finish.</p>
      </div>
      <div class="step">
        <div class="step-n">2</div>
        <h3>We confirm overnight</h3>
        <p>A real person on our team verifies every trip the night before and assigns your
        chauffeur. You get their name, photo, vehicle and plate. If anything cannot be
        honoured you hear it that night, not at the curb.</p>
      </div>
      <div class="step">
        <div class="step-n">3</div>
        <h3>Track and text</h3>
        <p>Watch your driver approach on a live map with a running ETA. Message them
        straight from your browser — it lands as a text on their phone and their reply
        comes back to you.</p>
      </div>
    </div>
  </div>
</section>
"""

    rates = f"""
<section id="rates">
  <div class="wrap">
    <div class="hd">
      <p class="eyebrow">Flat rates</p>
      <h2>One price per county. Two destinations. That is the whole pricing model.</h2>
      <p class="lede">
        Every New Jersey county has a single flat rate into New York City — that covers Manhattan,
        LaGuardia and all five boroughs at the same price. JFK is the one exception and carries its own
        rate, because it is genuinely the longest run from New Jersey. Prices below are for the
        Executive SUV and are all-in.
      </p>
    </div>

    <div class="fld" style="max-width:340px;margin-bottom:18px">
      <label for="rate-filter">Find your county or town</label>
      <input class="ctl" type="search" id="rate-filter" placeholder="e.g. Hackensack, Morris, Princeton"
             autocomplete="off">
    </div>

    <div class="rates-wrap">
      <table class="rates">
        <caption>All-in flat rates, Executive SUV (up to 6 passengers). Struck-through figures are
        typical market rates researched from published competitor pricing. Last updated {TODAY}.</caption>
        <thead>
          <tr>
            <th scope="col">County</th>
            <th scope="col">→ New York City<br><small style="font-weight:400;text-transform:none;letter-spacing:0;opacity:.7">Manhattan · LGA · all boroughs</small></th>
            <th scope="col">→ JFK Airport</th>
            <th scope="col">You save</th>
            <th scope="col"><span class="sr">Action</span></th>
          </tr>
        </thead>
        <tbody id="rates-body">
          {rate_rows()}
        </tbody>
      </table>
    </div>

    <div class="g2" style="margin-top:clamp(34px,4vw,58px);align-items:start">
      <div>
        <h3 style="margin-bottom:16px">Every price includes all of this</h3>
        <ul class="inc-list" style="grid-template-columns:1fr">
          {included_list()}
        </ul>
      </div>
      <div class="card">
        <p class="eyebrow" style="margin-bottom:14px">Why flat beats metered</p>
        <h3 style="margin-bottom:12px">The quoted number is the number you pay</h3>
        <p style="color:var(--tx-lm);font-size:.96rem">
          Most operators advertise a base rate, then add 18–20% gratuity, tolls, a
          $9 Manhattan congestion charge, a $20 New Jersey surcharge, and in some cases a
          card-processing fee and a Friday-afternoon surcharge. By the time you pay, a
          “$170” quote is well over $220.
        </p>
        <p style="color:var(--tx-lm);font-size:.96rem">
          We put all of it inside one number, then price that number below the market.
          Nothing is added at the curb — which is also why we can tell you the price
          before you hand over a card.
        </p>
        <button class="btn btn-gold btn-full" data-goto-book data-track="rates-card" style="margin-top:6px">
          Price my trip
        </button>
      </div>
    </div>
  </div>
</section>
"""


    planner = f"""
<section id="plan" class="tint">
  <div class="wrap">
    <div class="hd">
      <p class="eyebrow">Departure planner</p>
      <h2>Never guess when to leave.</h2>
      <p class="lede">Tell us the flight or the event and we work backwards from it — using the
      real drive time from your county, the traffic you will actually hit at that hour, and the
      buffer the terminal or venue genuinely needs. A flat &ldquo;leave two hours early&rdquo; is
      wrong for most of New Jersey: it is {COUNTIES[0][7]}–{COUNTIES[0][8]} minutes from Hudson County
      and {COUNTIES[-1][7]}–{COUNTIES[-1][8]} from Cape May.</p>
    </div>

    <div class="plan-grid">
      <div class="plan-card">
        <div class="plan-hd">
          <strong>Work out my pickup time</strong>
          <div class="plan-modes" role="tablist" aria-label="Planner mode">
            <button type="button" data-plan-mode="flight" class="on" role="tab" aria-selected="true">Catching a flight</button>
            <button type="button" data-plan-mode="event" role="tab" aria-selected="false">Going to an event</button>
          </div>
        </div>
        <form class="plan-bd" id="plan-form" novalidate>
          <div class="fld">
            <label for="plan-county">Pickup county <span class="req" aria-hidden="true">*</span></label>
            <select class="ctl" id="plan-county">
              <option value="">Choose your New Jersey county…</option>
              {county_options()}
            </select>
            <span class="hint">Drive time is calculated from this county, not an average.</span>
          </div>

          <div data-plan-pane="flight">
            <div class="fld">
              <label>Departing from</label>
              <div class="seg" role="radiogroup" aria-label="Airport">
                <input type="radio" name="plan-airport" id="plan-ap-jfk" value="jfk" checked>
                <label for="plan-ap-jfk">JFK<small>Own flat rate</small></label>
                <input type="radio" name="plan-airport" id="plan-ap-lga" value="nyc">
                <label for="plan-ap-lga">LaGuardia<small>NYC rate</small></label>
              </div>
            </div>
            <div class="fld">
              <label for="plan-flight-time">Scheduled departure time <span class="req" aria-hidden="true">*</span></label>
              <input class="ctl" type="datetime-local" id="plan-flight-time">
              <span class="hint">The time on your ticket, in Eastern time.</span>
            </div>
            <label class="chk" for="plan-intl">
              <input type="checkbox" id="plan-intl">
              <span><b>International departure</b>Adds a third hour at the terminal instead of two.</span>
            </label>
          </div>

          <div data-plan-pane="event" style="display:none">
            <div class="fld">
              <label for="plan-event">Which event? <span class="req" aria-hidden="true">*</span></label>
              <select class="ctl" id="plan-event">
                <option value="">Loading live events…</option>
              </select>
              <span class="hint" id="plan-event-hint">Pulled live from the events feed below.</span>
            </div>
          </div>

          <button class="btn btn-dark btn-lg btn-full" type="submit" data-track="planner">
            {SVG_CLOCK} Tell me when to leave
          </button>
        </form>
      </div>

      <div>
        <div class="plan-out" id="plan-result" role="status">
          <div class="plan-top">
            <div class="lbl">Your car should collect you at</div>
            <div class="plan-leave" id="plan-leave">—</div>
            <div class="sub" id="plan-headline">—</div>
          </div>
          <div class="pb" id="plan-break"></div>
          <div class="plan-ft">
            <button class="btn btn-gold btn-lg btn-full" id="plan-apply" type="button">
              Use this pickup time &amp; price it →
            </button>
          </div>
        </div>
        <div class="plan-empty" id="plan-empty">
          Pick your county and your flight or event, and the exact pickup time appears here —
          with the full breakdown so you can see how we got there.
        </div>
      </div>
    </div>
  </div>
</section>
"""

    book = f"""
<section class="tint" id="book">
  <div class="wrap">
    <div class="hd ctr">
      <p class="eyebrow">Book online</p>
      <h2>Reserve your SUV</h2>
      <p class="lede" style="margin-left:auto;margin-right:auto">
        Four short steps. Payment comes last, after you have seen everything.
      </p>
    </div>

    <div class="book-shell" id="book-shell">
      <div class="prog" role="list" aria-label="Booking progress">
        <div class="prog-i on" role="listitem"><em>Step 1</em>Trip</div>
        <div class="prog-i" role="listitem"><em>Step 2</em>Vehicle</div>
        <div class="prog-i" role="listitem"><em>Step 3</em>Contact</div>
        <div class="prog-i" role="listitem"><em>Step 4</em>Payment</div>
        <div class="prog-i" role="listitem"><em>Done</em>Confirmed</div>
      </div>

      <!-- step 1 -->
      <div class="stepv on" data-step="1">
        <h3>Your trip</h3>
        <p class="sd">We already have your route and price from the quote above.</p>
        <div class="summ">
          <div class="summ-r"><span>Route</span><b id="b-route">—</b></div>
          <div class="summ-r"><span>Pickup</span><b id="b-when">—</b></div>
        </div>
        <div class="fld">
          <label for="b-pickup">Pickup address <span class="req" aria-hidden="true">*</span></label>
          <input class="ctl" id="b-pickup" data-req placeholder="e.g. 12 Prospect Ave, Hackensack NJ 07601">
          <span class="fld-err">Please enter your pickup address.</span>
        </div>
        <div class="fld">
          <label for="b-drop">Drop-off address <span class="req" aria-hidden="true">*</span></label>
          <input class="ctl" id="b-drop" data-req placeholder="e.g. JFK Terminal 4, Departures">
          <span class="fld-err">Please enter your drop-off address.</span>
        </div>
        <div class="f3">
          <div class="fld">
            <label for="b-pax">Passengers</label>
            <select class="ctl" id="b-pax">
              <option>1</option><option>2</option><option selected>3</option>
              <option>4</option><option>5</option><option>6</option><option>7+</option>
            </select>
          </div>
          <div class="fld">
            <label for="b-bags">Large bags</label>
            <select class="ctl" id="b-bags">
              <option>0</option><option>1</option><option selected>2</option>
              <option>3</option><option>4</option><option>5</option><option>6+</option>
            </select>
          </div>
          <div class="fld" data-airport-only>
            <label for="b-flight">Flight number</label>
            <input class="ctl" id="b-flight" placeholder="e.g. DL 412">
            <span class="hint">We track it and shift your pickup automatically.</span>
          </div>
        </div>
        <div data-airport-only>
          <div class="f2">
            <div class="fld">
              <label for="b-flight-time">Scheduled departure time</label>
              <input class="ctl" type="datetime-local" id="b-flight-time">
              <span class="hint">Enter this and we will check your pickup time is early enough.</span>
            </div>
            <div class="fld" style="display:flex;align-items:flex-end;padding-bottom:6px">
              <label class="chk" for="b-intl" style="margin:0">
                <input type="checkbox" id="b-intl">
                <span><b>International flight</b>Three hours at the terminal, not two.</span>
              </label>
            </div>
          </div>
          <div class="rec-box" id="b-flight-rec">
            <div class="t" id="b-flight-rec-tx"></div>
            <button class="btn btn-ghost-l" type="button" id="b-flight-apply">Move my pickup to that time</button>
          </div>
        </div>
        <div class="fld">
          <label for="b-notes">Anything your chauffeur should know</label>
          <textarea class="ctl" id="b-notes" rows="2" placeholder="Child seat, extra stop, gate code, meet inside…"></textarea>
        </div>
        <div class="nav-btns">
          <button class="btn btn-gold btn-lg" data-next data-track="book-step1">Choose vehicle →</button>
        </div>
      </div>

      <!-- step 2 -->
      <div class="stepv" data-step="2">
        <h3>Choose your vehicle</h3>
        <p class="sd">All three are all-in prices for your route. Most riders take the Executive SUV.</p>
        <div class="vpick" id="b-vehicles"></div>
        <div class="nav-btns">
          <button class="btn btn-ghost-l back" data-back>← Back</button>
          <button class="btn btn-gold btn-lg" data-next data-track="book-step2">Continue →</button>
        </div>
      </div>

      <!-- step 3 -->
      <div class="stepv" data-step="3">
        <h3>Where do we reach you?</h3>
        <p class="sd">Your mobile is how your chauffeur texts you. Nothing else is shared.</p>
        <div class="f2">
          <div class="fld">
            <label for="b-name">Full name <span class="req" aria-hidden="true">*</span></label>
            <input class="ctl" id="b-name" data-req autocomplete="name" placeholder="Jordan Ellis">
            <span class="fld-err">Please enter your name.</span>
          </div>
          <div class="fld">
            <label for="b-mobile">Mobile <span class="req" aria-hidden="true">*</span></label>
            <input class="ctl" id="b-mobile" type="tel" data-req data-minlen="10"
                   autocomplete="tel" placeholder="(201) 555-0147">
            <span class="hint">So your driver can text you.</span>
            <span class="fld-err">Please enter a valid mobile number.</span>
          </div>
        </div>
        <div class="fld">
          <label for="b-email">Email <span class="req" aria-hidden="true">*</span></label>
          <input class="ctl" id="b-email" type="email" data-req autocomplete="email"
                 placeholder="jordan@company.com">
          <span class="hint">Confirmation and receipt only. No marketing unless you ask.</span>
          <span class="fld-err">Please enter a valid email address.</span>
        </div>
        <div class="secure">{SVG_LOCK} We never share or sell your details. Your number goes to your assigned chauffeur and nobody else.</div>
        <div class="nav-btns">
          <button class="btn btn-ghost-l back" data-back>← Back</button>
          <button class="btn btn-gold btn-lg" data-next data-track="book-step3">Continue to payment →</button>
        </div>
      </div>

      <!-- step 4 -->
      <div class="stepv" data-step="4">
        <h3>Payment portal</h3>
        <p class="sd">Card is authorised now. Free cancellation up to 60 minutes before pickup.</p>
        <div class="summ">
          <div class="summ-r"><span>Route</span><b data-sum-route>—</b></div>
          <div class="summ-r"><span>Pickup</span><b data-sum-when>—</b></div>
          <div class="summ-r"><span>Vehicle</span><b data-sum-veh>—</b></div>
          <div class="summ-r"><span>Tolls, gratuity, fees</span><b>Included</b></div>
          <div class="summ-r summ-tot"><span>Total due</span><b class="num" data-sum-total>—</b></div>
        </div>
        <div class="pay-sec">
          <div class="pay-hd">
            <b>Card details</b>
            <div class="cards" aria-hidden="true"><i>VISA</i><i>MC</i><i>AMEX</i><i>DISC</i></div>
          </div>
          <div class="fld">
            <label for="p-card">Card number <span class="req" aria-hidden="true">*</span></label>
            <input class="ctl num" id="p-card" data-req data-minlen="15" inputmode="numeric"
                   autocomplete="cc-number" placeholder="4242 4242 4242 4242">
            <span class="fld-err">Please enter a valid card number.</span>
          </div>
          <div class="f3">
            <div class="fld">
              <label for="p-exp">Expiry <span class="req" aria-hidden="true">*</span></label>
              <input class="ctl num" id="p-exp" data-req inputmode="numeric"
                     autocomplete="cc-exp" placeholder="09/28">
              <span class="fld-err">Required.</span>
            </div>
            <div class="fld">
              <label for="p-cvc">CVC <span class="req" aria-hidden="true">*</span></label>
              <input class="ctl num" id="p-cvc" data-req inputmode="numeric"
                     autocomplete="cc-csc" placeholder="123">
              <span class="fld-err">Required.</span>
            </div>
            <div class="fld">
              <label for="p-zip">Billing ZIP <span class="req" aria-hidden="true">*</span></label>
              <input class="ctl num" id="p-zip" data-req inputmode="numeric" placeholder="07601">
              <span class="fld-err">Required.</span>
            </div>
          </div>
          <div class="secure">{SVG_LOCK} Card data is tokenised and never touches our servers.</div>
        </div>
        <div class="nav-btns">
          <button class="btn btn-ghost-l back" data-back>← Back</button>
          <button class="btn btn-gold btn-lg" id="pay-btn" data-next data-track="book-pay">
            Pay <span data-sum-total>—</span> &amp; confirm booking
          </button>
        </div>
        <div class="hook">
          <b>Demo mode.</b> No card is charged and nothing is sent to a payment network.
          Add your Stripe or Square key at <code>CFG.stripePublishableKey</code> and swap the
          simulated authorisation for a real confirmation — see <code>INTEGRATION-GUIDE.md §1</code>.
        </div>
      </div>

      <!-- step 5 -->
      <div class="stepv" data-step="5">
        <div class="conf">
          <div class="conf-ic">{SVG_CHECK}</div>
          <h3>You are booked.</h3>
          <p style="color:var(--tx-lm)">A confirmation is on its way to your inbox.</p>
          <div class="ref" id="c-ref">—</div>
          <div class="conf-grid">
            <div><span>Route</span><b id="c-route">—</b></div>
            <div><span>Pickup</span><b id="c-when">—</b></div>
            <div><span>Vehicle</span><b id="c-veh">—</b></div>
            <div><span>Total paid</span><b class="num" id="c-total">—</b></div>
          </div>
          <div class="overnight">
            {SVG_MOON}
            <div>
              <b>We confirm your trip overnight</b>
              <p>Tonight a member of our team verifies your booking and assigns your chauffeur.
              You will get their name, photo, vehicle and plate before pickup — and if anything
              about your trip cannot be honoured, you hear from us then, not at the curb.</p>
            </div>
          </div>
          <a class="btn btn-gold btn-lg btn-full" href="#track" data-goto-track data-track="conf-track">
            {SVG_PIN} Track my driver &amp; send a message
          </a>
          <div class="hook" style="text-align:left">
            <b>Go-live note.</b> Confirmation email/SMS and the overnight verification job are
            back-end tasks — see <code>INTEGRATION-GUIDE.md §4</code>.
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
"""

    track = f"""
<section class="dark" id="track">
  <div class="wrap">
    <div class="hd">
      <p class="eyebrow">Track &amp; text</p>
      <h2>Know exactly where your driver is. Tell them exactly what you need.</h2>
      <p class="lede">The two things people actually phone a car service about, solved on screen.
      Below is a live example of what you see once a chauffeur is assigned.</p>
    </div>

    <div class="track-grid">
      <div class="map-card">
        <div class="map-hd">
          <span class="live-dot"><i></i> Live tracking</span>
          <div class="eta">
            <b class="num" id="eta-min">14</b>
            <span>min away · <span id="eta-prog">0%</span> of route</span>
          </div>
        </div>
        <div id="map" role="img" aria-label="Live map showing the driver's position between Hackensack, New Jersey and Midtown Manhattan"></div>
        <div class="drv">
          <div class="drv-av" aria-hidden="true">MS</div>
          <div class="drv-tx">
            <b>Marcus S.</b>
            <span>★ 4.97 · 12 years driving · 4,180 trips</span>
          </div>
          <div class="drv-veh">
            Black Chevrolet Suburban
            <b>NJ · M-4821</b>
          </div>
        </div>
      </div>

      <div class="chat">
        <div class="chat-hd">
          <div>
            <b>Message Marcus</b>
            <small>Delivered as SMS to his phone</small>
          </div>
          <span class="live-dot"><i></i> Online</span>
        </div>
        <div class="chat-log" id="chat-log" aria-live="polite" aria-label="Conversation with your driver">
          <div class="msg sys">Today · Marcus was assigned to your trip</div>
          <div class="msg them">Good morning — Marcus here, I'll be your chauffeur to JFK.
            I'm leaving now and I'm about 14 minutes from you.<time>5:02 AM</time></div>
          <div class="msg me">Perfect, thank you. I'll be out front.<time>5:03 AM</time></div>
        </div>
        <div class="quick">
          <button type="button">I'm running 5 minutes late</button>
          <button type="button">Where are you now?</button>
          <button type="button">Meet me inside</button>
          <button type="button">I have extra luggage</button>
        </div>
        <form class="chat-in" id="chat-form">
          <label class="sr" for="chat-input">Message your driver</label>
          <input id="chat-input" placeholder="Type a message…" autocomplete="off">
          <button type="submit" aria-label="Send message">{SVG_SEND}</button>
        </form>
      </div>
    </div>

    <div class="hook" style="margin-top:22px;background:rgba(208,138,62,.09);color:var(--tx-dm);border-color:rgba(208,138,62,.3)">
      <b style="color:var(--gold-2)">What is real and what is simulated here.</b>
      The map, route, ETA and messaging interface are fully functional. The driver position is
      currently simulated on a fixed route and replies are canned. To go live, point
      <code>CFG.gpsEndpoint</code> at your driver app's location feed and <code>CFG.smsEndpoint</code>
      at a Twilio relay — the send and receive paths are already wired.
      See <code>INTEGRATION-GUIDE.md §2–3</code>.
    </div>
  </div>
</section>
"""

    events = f"""
<section id="events" class="dark" style="background:var(--ink-2)">
  <div class="wrap">
    <div class="ev-hd">
      <div>
        <p class="eyebrow">Live NYC events</p>
        <h2>Going into the city for something?</h2>
        <p class="lede" style="margin-top:12px">Real schedules, pulled live from official feeds —
        not a list we typed in. Pick an event and we set your pickup two hours before it starts.</p>
      </div>
      <div style="text-align:right">
        <span class="live-dot"><i></i> Live feed</span>
        <div style="font-size:.79rem;color:var(--tx-dm);margin-top:6px">
          Updated <span id="ev-updated">—</span> · refreshes every 10 min
        </div>
      </div>
    </div>

    <div class="tabs" role="tablist" aria-label="Event venues">
      <button class="tab on" data-tab="yankees" role="tab">Yankee Stadium <span class="n"></span></button>
      <button class="tab" data-tab="msg" role="tab">Madison Square Garden <span class="n"></span></button>
      <button class="tab" data-tab="barclays" role="tab">Barclays Center <span class="n"></span></button>
      <button class="tab" data-tab="broadway" role="tab">Broadway &amp; theatre <span class="n"></span></button>
      <button class="tab" data-tab="concerts" role="tab">Concerts <span class="n"></span></button>
    </div>

    <div class="ev-list" id="ev-list"></div>

    <p class="ev-src">
      {SVG_SHIELD}
      <span><b style="color:var(--tx-d)">Sources:</b>
      Yankee Stadium home games come from the official MLB Stats API, live with no configuration.
      Madison Square Garden, Barclays Center, Broadway and concert listings come from the
      <a href="https://developer.ticketmaster.com" target="_blank" rel="noopener noreferrer">Ticketmaster Discovery API</a>,
      which needs a free key — venue IDs are resolved at runtime, so nothing is hardcoded.</span>
    </p>

    <div class="conn" style="margin-top:22px">
      <h4>Connect the Ticketmaster feed</h4>
      <p>Free key, about two minutes, no card required. Paste it once and the MSG, Barclays,
      Broadway and concert tabs fill with live listings. Stored in your browser only.</p>
      <form class="conn-row" id="conn-form">
        <label class="sr" for="conn-key">Ticketmaster consumer key</label>
        <input id="conn-key" placeholder="Paste your Ticketmaster consumer key" autocomplete="off">
        <button class="btn btn-gold" type="submit">Connect live feed</button>
        <a class="btn btn-ghost-d" href="https://developer.ticketmaster.com/products-and-docs/apis/getting-started/"
           target="_blank" rel="noopener noreferrer">Get a free key</a>
      </form>
      <div class="conn-ok" id="conn-ok" style="display:none">{SVG_CHECK} Ticketmaster feed connected — listings are live.</div>
    </div>
  </div>
</section>
"""

    fleet = f"""
<section id="fleet">
  <div class="wrap">
    <div class="hd">
      <p class="eyebrow">The fleet</p>
      <h2>Three vehicles. No guessing which one turns up.</h2>
      <p class="lede">You book a specific class and that is what arrives — confirmed by model
      and plate the night before. Every vehicle is under four years old and detailed between trips.</p>
    </div>
    <div class="g3">
      {vehicle_cards()}
    </div>
  </div>
</section>

<section class="tint" id="drivers">
  <div class="wrap g2" style="align-items:center">
    <div>
      <p class="eyebrow">The chauffeurs</p>
      <h2 style="margin-bottom:16px">Ten years minimum. That is the floor, not the average.</h2>
      <p style="color:var(--tx-lm)">
        We do not hire drivers who are learning on your airport run. Every chauffeur arrives with at
        least a decade of professional experience, and knows which terminal door to be at, how the
        Lincoln Tunnel behaves at 4pm on a Friday, and which side of Penn Station to wait on.
      </p>
      <ul class="inc-list" style="grid-template-columns:1fr;margin-top:20px">
        <li>{SVG_CHECK}<div><b>{yrs}+ years professional experience, minimum</b><span>Verified employment history, not self-reported.</span></div></li>
        <li>{SVG_CHECK}<div><b>Federal and state background screening</b><span>Re-run annually, plus continuous licence monitoring.</span></div></li>
        <li>{SVG_CHECK}<div><b>Commercially licensed and drug tested</b><span>Full commercial insurance on every vehicle.</span></div></li>
        <li>{SVG_CHECK}<div><b>Defensive driving certified</b><span>Recertified every two years.</span></div></li>
        <li>{SVG_CHECK}<div><b>Hospitality trained</b><span>Door held, bags handled, conversation only if you want it.</span></div></li>
      </ul>
    </div>
    <div>
      <img src="{IMG_CHAUF}" alt="A professional chauffeur in a black suit holding open the rear door of a black SUV at an airport terminal curb"
           loading="lazy" width="1248" height="832" style="border-radius:var(--r-lg);box-shadow:var(--sh-lg)">
    </div>
  </div>
</section>

<section id="reviews">
  <div class="wrap">
    <div class="hd ctr">
      <p class="eyebrow">Riders</p>
      <h2>{BRAND['rating']} out of 5, across {BRAND['review_count']:,} trips</h2>
    </div>
    <div class="g4">
      {review_cards()}
    </div>
  </div>
</section>
"""

    faq_soon = f"""
<section class="tint" id="faq">
  <div class="wrap">
    <div class="hd ctr">
      <p class="eyebrow">Questions</p>
      <h2>Everything people ask before their first ride</h2>
    </div>
    <div class="faq">
      {faq_html()}
    </div>
  </div>
</section>

<section class="dark" id="soon">
  <div class="wrap">
    <div class="soon">
      <div class="soon-tx">
        <span class="badge-soon">Coming soon</span>
        <h3>New Jersey to New Jersey transfers</h3>
        <p>Right now we do one thing properly: New Jersey into New York City. In-state New Jersey
        transfers — Newark to Princeton, Hoboken to the Shore, county to county — are next.
        Leave your email and you will be first through the door.</p>
      </div>
      <form class="soon-fm" id="waitlist">
        <label class="sr" for="wl-email">Email address</label>
        <input id="wl-email" type="email" placeholder="you@company.com" autocomplete="email">
        <button class="btn btn-gold" type="submit">Join the waitlist</button>
      </form>
    </div>
  </div>
</section>

<section class="band">
  <div class="wrap narrow">
    <p class="eyebrow" style="justify-content:center">Ready when you are</p>
    <h2>Your price is three fields away.</h2>
    <p class="lede">Pick your county, pick where you are going, and see the exact all-in number.
    No account, no card, no callback.</p>
    <div class="band-btns">
      <button class="btn btn-gold btn-lg" data-goto-book data-track="band">{SVG_TAG} Get my flat rate</button>
      <a class="btn btn-ghost-d btn-lg" href="tel:{BRAND['phone_raw']}">Or call {BRAND['phone_display']}</a>
    </div>
    <div class="guar">{SVG_SHIELD} On time for your flight, or the ride is free. Free cancellation up to 60 minutes before pickup.</div>
  </div>
</section>
</main>
"""

    footer = f"""
<footer>
  <div class="wrap">
    <div class="ft-top">
      <div class="ft-ab">
        <a class="logo" href="#top" style="margin-bottom:16px">
          <span class="logo-mk" aria-hidden="true">M</span>
          <span>{BRAND['name']}<small>NJ → NYC</small></span>
        </a>
        <p>Flat-rate chauffeured SUVs from every New Jersey county into New York City and JFK.
        Booked online, confirmed overnight, tracked live.</p>
        <address class="ft-nap">
          <a href="tel:{BRAND['phone_raw']}">{BRAND['phone_display']}</a><br>
          <a href="mailto:{BRAND['email']}">{BRAND['email']}</a><br>
          {BRAND['address']}<br>
          {BRAND['tlc']}
        </address>
        <span class="ph">Placeholder name, phone, address &amp; licence — replace before launch</span>
      </div>
      <div>
        <h4>Service</h4>
        <ul>
          <li><a href="#rates">Flat rates by county</a></li>
          <li><a href="#quote">Get an instant quote</a></li>
          <li><a href="#book">Book a ride</a></li>
          <li><a href="#plan">Departure planner</a></li>
          <li><a href="#fleet">Our fleet</a></li>
          <li><a href="#drivers">Our chauffeurs</a></li>
          <li><a href="#track">Track &amp; text your driver</a></li>
        </ul>
      </div>
      <div>
        <h4>Destinations</h4>
        <ul>
          <li><a href="#quote" data-book-county="bergen" data-book-dest="jfk">NJ to JFK Airport</a></li>
          <li><a href="#quote" data-book-county="bergen" data-book-dest="nyc">NJ to LaGuardia</a></li>
          <li><a href="#quote" data-book-county="bergen" data-book-dest="nyc">NJ to Manhattan</a></li>
          <li><a href="#events">Madison Square Garden</a></li>
          <li><a href="#events">Yankee Stadium</a></li>
          <li><a href="#events">Barclays Center</a></li>
          <li><a href="#events">Broadway theatres</a></li>
        </ul>
      </div>
      <div>
        <h4>Company</h4>
        <ul>
          <li><a href="#why">Why {BRAND['short']}</a></li>
          <li><a href="#how">How it works</a></li>
          <li><a href="#reviews">Reviews</a></li>
          <li><a href="#faq">FAQ</a></li>
          <li><a href="#soon">NJ transfers waitlist</a></li>
          <li><a href="/pricing.md">Machine-readable rates</a></li>
        </ul>
      </div>
    </div>

    <div class="ft-counties">
      <h4>New Jersey counties we serve</h4>
      <ul class="ft-cl">
        {footer_counties()}
      </ul>
    </div>

    <div class="ft-bt">
      <div>© {datetime.date.today().year} {BRAND['name']}. Rates shown are all-in and valid as of {TODAY}.</div>
      <div>
        <a href="#faq">Terms</a>
        <a href="#faq">Privacy</a>
        <a href="#faq">Accessibility</a>
        <a href="#rates">Rates</a>
      </div>
    </div>
  </div>
</footer>

<div class="mbar">
  <a class="btn btn-ghost-d" href="tel:{BRAND['phone_raw']}">Call</a>
  <button class="btn btn-gold" data-goto-book data-track="mobile-bar">Get my flat rate</button>
</div>

<div class="pop-bd" id="pop" role="dialog" aria-modal="true" aria-labelledby="pop-h">
  <div class="pop">
    <button class="pop-x" data-pop-close aria-label="Close">×</button>
    <div class="pop-in">
      <p class="eyebrow">Before you go</p>
      <h3 id="pop-h">See your exact price in about ten seconds.</h3>
      <p>No card, no account, no callback. Just pick your county and where you are heading —
      and the number you see is the number you pay.</p>
      <button class="btn btn-gold btn-lg btn-full" id="pop-cta">{SVG_TAG} Show me my flat rate</button>
      <button class="pop-no" data-pop-close>No thanks, I'll look around</button>
    </div>
  </div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite">
  {SVG_CHECK}<span id="toast-msg"></span>
</div>

<script>
{JS.replace("__RATES_JSON__", rates_json()).replace("__VEHICLES_JSON__", vehicles_json())}
</script>
</body>
</html>
"""
    return (head + header + hero + compare + how + rates + planner + book
            + track + events + fleet + faq_soon + footer)


def rates_json():
    d = {}
    for (name, slug, reg, nyc, jfk, mnyc, mjfk, dmin, dmax, towns, conf) in COUNTIES:
        d[slug] = {"name": name, "region": reg, "nyc": nyc, "jfk": jfk,
                   "market_nyc": mnyc, "market_jfk": mjfk,
                   "drive_min": dmin, "drive_max": dmax, "towns": towns}
    return json.dumps(d, separators=(",", ":"))


def vehicles_json():
    return json.dumps([{k: v[k] for k in ("id", "name", "examples", "pax", "bags", "multiplier", "recommended")}
                       for v in VEHICLES], separators=(",", ":"))


# ---------------------------------------------------------------- seo files
def pricing_md():
    lines = [
        "# " + BRAND["name"] + " — Flat Rates (New Jersey → New York City)",
        "",
        "> Machine-readable rate card. Last updated: " + TODAY,
        "",
        "All prices are **all-in, per vehicle, one-way, in USD**. They include tolls, driver gratuity,",
        "the Manhattan congestion charge, the New Jersey surcharge, meet & greet, flight tracking and",
        "60 minutes of free wait time (90 on international arrivals). Prices are fixed at booking.",
        "**There is no surge pricing at any time.**",
        "",
        "## Pricing model",
        "",
        "Two prices per New Jersey county:",
        "",
        "1. **New York City** — one flat rate covering Manhattan, LaGuardia Airport (LGA), Brooklyn,",
        "   Queens, the Bronx and Staten Island.",
        "2. **JFK Airport** — a separate, higher flat rate.",
        "",
        "Vehicle classes: Executive SUV (6 passengers, base rate), Luxury SUV (Escalade ESV, 1.22×),",
        "Executive Sprinter (11 passengers, 1.85×).",
        "",
        "## Rates by county (Executive SUV)",
        "",
        "| NJ County | → New York City (incl. LGA) | → JFK Airport | Typical drive time |",
        "|---|---|---|---|",
    ]
    for (name, slug, reg, nyc, jfk, mnyc, mjfk, dmin, dmax, towns, conf) in COUNTIES:
        lines.append(f"| {name} | ${nyc} | ${jfk} | {dmin}–{dmax} min |")
    lines += [
        "",
        "## Booking",
        "",
        "Online only, no phone call required: " + SITE + "/#quote",
        "Instant quote, card payment in the portal, live driver tracking and two-way driver messaging.",
        "Free cancellation up to 60 minutes before pickup.",
        "",
        "## Contact",
        "",
        "- Phone: " + BRAND["phone_display"],
        "- Email: " + BRAND["email"],
        "- Service area: all 21 New Jersey counties → New York City",
        "- Hours: 24/7, 365 days",
        "",
        "New Jersey to New Jersey (in-state) transfers are not yet available — coming soon.",
    ]
    return "\n".join(lines) + "\n"


ROBOTS = """# """ + BRAND["name"] + """ — robots.txt
User-agent: *
Allow: /

# AI search crawlers — explicitly allowed so we can be cited with real prices.
User-agent: GPTBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: anthropic-ai
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: Bingbot
Allow: /
User-agent: Applebot-Extended
Allow: /

Sitemap: """ + SITE + """/sitemap.xml
"""


def sitemap():
    urls = [("/", "1.0", "weekly"), ("/pricing.md", "0.6", "monthly")]
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, pri, freq in urls:
        x.append("  <url><loc>" + SITE + loc + "</loc><lastmod>" + TODAY +
                 "</lastmod><changefreq>" + freq + "</changefreq><priority>" + pri + "</priority></url>")
    x.append("</urlset>")
    return "\n".join(x) + "\n"


def main():
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(render())
    with open(os.path.join(HERE, "pricing.md"), "w", encoding="utf-8") as f:
        f.write(pricing_md())
    with open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(ROBOTS)
    with open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap())
    n = os.path.getsize(os.path.join(HERE, "index.html"))
    print("index.html   %6.1f KB" % (n / 1024))
    print("pricing.md   ok")
    print("robots.txt   ok")
    print("sitemap.xml  ok")
    print("counties: %d  offers in schema: %d" % (len(COUNTIES), len(COUNTIES) * 2))


if __name__ == "__main__":
    main()
