"""Search and AI-discoverability outputs: meta, JSON-LD, pricing.md, robots.txt, sitemap.xml.

Rules: structured data describes only what is visible on the page and true —
no ratings, reviews, fake address or unapproved price offers.
"""
from __future__ import annotations

import datetime
import json

import data
from app.domain import rates
from app.domain.catalog import get_catalog

SITE = "https://" + data.BRAND["domain"]
TODAY = datetime.date.today().isoformat()
TITLE = f"Private Chauffeur Service New York & New Jersey | {data.BRAND['short']}"
DESCRIPTION = ("Cadillac Escalade chauffeur service for executives across New York and New Jersey — airports, "
               "Teterboro, hourly and long distance. All-inclusive pricing, reserved in moments.")
OG_IMAGE = SITE + "/static/og.png"


def journey_price(origin: str, destination: str) -> tuple[int | None, int | None, dict | None]:
    """(list cents, price today, offer) for a popular journey, from the live cost model."""
    cat = get_catalog()
    est = rates.transfer(cat, cat.places[origin], cat.places[destination])
    if est.committed_minutes > cat.params["max_committed_min_for_instant_price"]:
        return None, None, None
    amount, offer = rates.introductory(cat, est.cents, datetime.datetime.now(datetime.timezone.utc))
    return est.cents, amount, offer


def jsonld() -> str:
    b = data.BRAND
    business = {
        "@type": "LocalBusiness",
        "@id": SITE + "/#business",
        "name": b["name"],
        "url": SITE + "/",
        "image": OG_IMAGE,
        "telephone": b["phone_raw"],
        "email": b["email"],
        "priceRange": "$$$",
        "description": DESCRIPTION,
        "areaServed": [{"@type": "State", "name": n} for n in ("New Jersey", "New York", "Connecticut", "Pennsylvania")]
                      + [{"@type": "City", "name": "New York City"}],
        "knowsAbout": ["Chauffeured car service", "Executive transportation", "Airport transfers",
                       "Private aviation ground transportation", "Hourly chauffeur service"],
    }
    graph = [
        {"@type": "Organization", "@id": SITE + "/#org", "name": b["name"], "url": SITE + "/", "logo": OG_IMAGE,
         "contactPoint": {"@type": "ContactPoint", "telephone": b["phone_raw"], "email": b["email"],
                          "contactType": "reservations", "areaServed": "US-NJ", "availableLanguage": "en"}},
        {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": b["name"],
         "publisher": {"@id": SITE + "/#org"}, "inLanguage": "en-US"},
        business,
        {"@type": "FAQPage", "@id": SITE + "/#faq",
         "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                        for q, a in data.FAQS]},
    ]
    if data.PRICING["approved"]:   # publish machine-readable offers only once the owner has approved them
        cat = get_catalog()
        offers = []
        for a, b in data.POPULAR_JOURNEYS:
            list_cents, _, _ = journey_price(a, b)
            if list_cents:
                offers.append({"@type": "Offer", "name": f"{cat.places[a].name} to {cat.places[b].name}",
                               "price": f"{list_cents / 100:.2f}", "priceCurrency": "USD"})
        offers.append({"@type": "Offer", "name": "Chauffeur by the hour",
                       "priceSpecification": {"@type": "UnitPriceSpecification",
                                              "price": f"{data.PRICING['hourly_cents'] / 100:.2f}",
                                              "priceCurrency": "USD", "unitCode": "HUR"}})
        graph.append({"@type": "Service", "@id": SITE + "/#service", "serviceType": "Private chauffeur service",
                      "provider": {"@id": SITE + "/#business"},
                      "hasOfferCatalog": {"@type": "OfferCatalog", "name": "All-inclusive rates",
                                          "itemListElement": offers}})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, separators=(",", ":"))


def head_meta() -> str:
    return f"""<title>{TITLE}</title>
<meta name="description" content="{DESCRIPTION}">
<link rel="canonical" href="{SITE}/">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{data.BRAND['name']}">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{SITE}/">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{jsonld()}</script>"""


def pricing_md() -> str:
    cat = get_catalog()
    status = "approved" if data.PRICING["approved"] else "estimates, confirmed before payment"
    lines = [
        f"# {data.BRAND['name']} — {data.BRAND['descriptor']}", "",
        f"> Machine-readable rates. Status: {status}. Updated {TODAY}.", "",
        "All prices are per vehicle, in USD, and include tolls, congestion charges and gratuity. Vehicle: "
        "Cadillac Escalade with second-row captain's chairs, panoramic sunroof and onboard Wi-Fi; up to 6 guests.",
        "", f"- **By the hour:** ${data.PRICING['hourly_cents'] // 100} per hour, "
        f"{data.PRICING['hourly_min_hours']}-hour minimum.",
        "- **Point to point:** priced on time and distance for the specific journey; instant quote at "
        f"{SITE}/#reserve", "", "## Popular journeys (one way)", "", "| Journey | From |", "|---|---|"]
    for a, b in data.POPULAR_JOURNEYS:
        list_cents, _, _ = journey_price(a, b)
        lines.append(f"| {cat.places[a].name} → {cat.places[b].name} | "
                     f"{'$' + str(list_cents // 100) if list_cents else 'on request'} |")
    lines += ["", "Service area: New Jersey, New York City, Westchester, Long Island, Fairfield County (CT) and "
              "Philadelphia, including EWR, JFK, LGA, Teterboro, Morristown and Westchester airports.", "",
              f"Contact: {data.BRAND['email']} · {data.BRAND['phone_display']}"]
    return "\n".join(lines) + "\n"


def robots_txt() -> str:
    return f"""# {data.BRAND['name']}
User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/
Disallow: /trip/
Disallow: /s/

# AI assistants may read and cite our published prices.
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: Applebot-Extended
Allow: /

Sitemap: {SITE}/sitemap.xml
"""


def sitemap_xml() -> str:
    urls = [("/", "weekly"), ("/pricing.md", "monthly"), ("/terms", "yearly"), ("/privacy", "yearly"),
            ("/accessibility", "yearly")]
    body = "\n".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><changefreq>{f}</changefreq></url>"
                     for u, f in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n")
