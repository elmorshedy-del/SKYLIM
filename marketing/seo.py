"""Search and AI-discoverability outputs: titles, meta, JSON-LD, pricing.md, robots.txt, sitemap.xml.

Rules (Google Search Central; see docs/SEO-PLAN.md for the sources):
  * structured data describes only what is visible on the page and true — no ratings,
    reviews, fake street address or unapproved price offers
  * every page has its own title and description; the brand is a short suffix
  * sitemap <lastmod> changes only when a page's content changes (Google uses lastmod
    only when it is "consistently and verifiably accurate"; it ignores changefreq/priority)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
from html import escape as e
from pathlib import Path

import data
import landing_pages
from app.domain import rates
from app.domain.catalog import get_catalog

ROOT = Path(__file__).resolve().parent.parent
LASTMOD_FILE = ROOT / "seo_lastmod.json"
SITE = "https://" + data.BRAND["domain"]
TODAY = datetime.date.today().isoformat()
TITLE = f"Private Chauffeur Service in New York & New Jersey | {data.BRAND['short']}"
DESCRIPTION = ("Cadillac Escalade chauffeur service across New York City and New Jersey: Newark, JFK, LaGuardia "
               "and Teterboro transfers, hourly and long distance. All-inclusive prices.")
OG_IMAGE = SITE + "/static/og.png"
LOGO = SITE + "/static/logo.png"
STATES = {"NJ": "New Jersey", "NY": "New York", "CT": "Connecticut", "PA": "Pennsylvania"}


# ------------------------------------------------------------------ prices in copy
def journey_price(origin: str, destination: str) -> tuple[int | None, int | None, dict | None]:
    """(list cents, price today, offer) for a journey, from the live cost model."""
    cat = get_catalog()
    est = rates.journey(cat, cat.places[origin], cat.places[destination])
    if est.committed_minutes > cat.params["max_committed_min_for_instant_price"]:
        return None, None, None
    amount, offer = rates.introductory(cat, est.cents, datetime.datetime.now(datetime.timezone.utc))
    return est.cents, amount, offer


def money(cents: int) -> str:
    return f"${cents / 100:,.0f}"


def fill(text: str) -> str:
    """Replace price tokens in copy with live figures (see landing_pages.py)."""
    def journey(m: re.Match) -> str:
        list_cents, today, _ = journey_price(m.group(1), m.group(2))
        return money(today) if list_cents else "a price on request"
    text = re.sub(r"\{([a-z-]+)>([a-z-]+)\}", journey, text)
    p = data.PRICING
    return (text.replace("{hourly}", money(p["hourly_cents"]))
                .replace("{hourly_min}", str(p["hourly_min_hours"]))
                .replace("{airport_wait}", str(p["airport_wait_min"])))


def page_title(page: dict) -> str:
    return f"{page['title']} | {data.BRAND['short']}"


# ------------------------------------------------------------------ structured data
def _business_node(full: bool) -> dict:
    b = data.BRAND
    node = {"@type": "LocalBusiness", "@id": SITE + "/#business", "name": b["name"], "url": SITE + "/",
            "telephone": b["phone_raw"], "image": OG_IMAGE,
            # service-area business: region only, never an invented street address
            "address": {"@type": "PostalAddress", "addressRegion": "NJ", "addressCountry": "US"}}
    if full:
        node.update({
            "email": b["email"], "logo": LOGO, "priceRange": "$$$", "description": DESCRIPTION,
            "areaServed": [{"@type": "State", "name": n} for n in STATES.values()]
                          + [{"@type": "City", "name": "New York City"}],
            "knowsAbout": ["Chauffeured car service", "Executive transportation", "Airport transfers",
                           "Private aviation ground transportation", "Hourly chauffeur service"],
        })
        if b.get("same_as"):
            node["sameAs"] = b["same_as"]
    return node


def _faq_node(page_url: str, faqs: list[tuple[str, str]]) -> dict:
    return {"@type": "FAQPage", "@id": page_url + "#faq",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                           for q, a in faqs]}


def _offers(pairs) -> list[dict]:
    cat = get_catalog()
    out = []
    for a, b in pairs:
        list_cents, _, _ = journey_price(a, b)
        if list_cents:
            out.append({"@type": "Offer", "name": f"{cat.places[a].name} to {cat.places[b].name}",
                        "price": f"{list_cents / 100:.2f}", "priceCurrency": "USD"})
    return out


def jsonld() -> str:
    """Home page: who we are (Organization, WebSite for the site name, LocalBusiness) and the FAQs."""
    b = data.BRAND
    graph = [
        {"@type": "Organization", "@id": SITE + "/#org", "name": b["name"], "url": SITE + "/", "logo": LOGO,
         "contactPoint": {"@type": "ContactPoint", "telephone": b["phone_raw"], "email": b["email"],
                          "contactType": "reservations", "areaServed": ["US-NJ", "US-NY"],
                          "availableLanguage": "en"}},
        {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": b["name"],
         "alternateName": b["short"], "publisher": {"@id": SITE + "/#org"}, "inLanguage": "en-US"},
        _business_node(full=True),
        _faq_node(SITE + "/", data.FAQS),
    ]
    if data.PRICING["approved"]:   # machine-readable offers only once the owner has approved the rates
        offers = _offers(data.POPULAR_JOURNEYS)
        offers.append({"@type": "Offer", "name": "Chauffeur by the hour",
                       "priceSpecification": {"@type": "UnitPriceSpecification",
                                              "price": f"{data.PRICING['hourly_cents'] / 100:.2f}",
                                              "priceCurrency": "USD", "unitCode": "HUR"}})
        graph.append({"@type": "Service", "@id": SITE + "/#service", "serviceType": "Private chauffeur service",
                      "provider": {"@id": SITE + "/#business"},
                      "hasOfferCatalog": {"@type": "OfferCatalog", "name": "All-inclusive rates",
                                          "itemListElement": offers}})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, separators=(",", ":"))


def breadcrumbs(page: dict) -> list[tuple[str, str]]:
    """[(name, path)] from the home page down to this page — a clearly defined hierarchy."""
    trail, p = [], page
    while p:
        trail.append((p["crumb"], p["path"]))
        p = landing_pages.BY_PATH.get(p["parent"]) if p["parent"] else None
    return [("Home", "/")] + trail[::-1]


def _served(page: dict) -> list[dict]:
    cat = get_catalog()
    out = []
    for s in page.get("serves", []):
        if s.startswith("state:"):
            out.append({"@type": "State", "name": s[6:]})
        elif s.startswith("city:"):
            out.append({"@type": "City", "name": s[5:]})
        else:
            out.append({"@type": "Airport", "name": cat.places[s].name, "iataCode": s.upper()})
    return out


def jsonld_page(page: dict, faqs: list[tuple[str, str]]) -> str:
    url = SITE + page["path"]
    service = {"@type": "Service", "@id": url + "#service", "name": page["link"],
               "serviceType": "Chauffeured car service", "provider": {"@id": SITE + "/#business"},
               "areaServed": _served(page), "url": url}
    if data.PRICING["approved"] and page["routes"]:
        service["offers"] = _offers(page["routes"])
    graph = [
        {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": page_title(page),
         "description": page["description"], "isPartOf": {"@id": SITE + "/#site"},
         "breadcrumb": {"@id": url + "#breadcrumb"}, "about": {"@id": url + "#service"}, "inLanguage": "en-US"},
        {"@type": "BreadcrumbList", "@id": url + "#breadcrumb",
         "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": SITE + p}
                             for i, (n, p) in enumerate(breadcrumbs(page), 1)]},
        service,
        _business_node(full=False),
    ]
    if faqs:
        graph.append(_faq_node(url, faqs))
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, separators=(",", ":"))


def head_meta(title: str = TITLE, description: str = DESCRIPTION, path: str = "/", ld: str | None = None) -> str:
    url = SITE + path
    t, d = e(title), e(description)
    return f"""<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(data.BRAND['name'])}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld or jsonld()}</script>"""


# ------------------------------------------------------------------ files for crawlers
def pricing_md() -> str:
    cat = get_catalog()
    status = "approved" if data.PRICING["approved"] else "estimates, confirmed before payment"
    lines = [
        f"# {data.BRAND['name']} — {data.BRAND['descriptor']}", "",
        f"> Machine-readable rates. Status: {status}. Updated {TODAY}.", "",
        "Point-to-point prices are per vehicle, in USD, and include tolls, congestion charges, airport parking "
        "and gratuity. Vehicle: Cadillac Escalade with second-row captain's chairs, panoramic sunroof and onboard "
        "Wi-Fi; up to 6 guests.",
        "", f"- **By the hour:** ${data.PRICING['hourly_cents'] // 100} per hour, gratuity included, "
        f"{data.PRICING['hourly_min_hours']}-hour minimum.",
        "- **Point to point:** priced on time and distance for the specific journey; instant quote at "
        f"{SITE}/#reserve", "", "## Popular journeys (one way)", "", "| Journey | From |", "|---|---|"]
    for a, b in data.POPULAR_JOURNEYS:
        list_cents, _, _ = journey_price(a, b)
        lines.append(f"| {cat.places[a].name} → {cat.places[b].name} | "
                     f"{money(list_cents) if list_cents else 'on request'} |")
    lines += ["", "## Pages", ""]
    lines += [f"- [{p['link']}]({SITE}{p['path']})" for p in landing_pages.PAGES]
    lines += ["", "Service area: New Jersey, New York City, Westchester, Long Island, Fairfield County (CT) and "
              "Philadelphia, including EWR, JFK, LGA, Teterboro, Morristown and Westchester airports. Journeys "
              "that begin and end within New York State are arranged on request.", "",
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


def content_hash(content: str) -> str:
    """Fingerprint of what a reader sees — ignoring the daily asset version and build date."""
    content = re.sub(r"\?v=\d{8}", "", content)
    content = re.sub(r"Updated \d{4}-\d{2}-\d{2}", "", content)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def update_lastmod(contents: dict[str, str], today: str = TODAY) -> dict[str, str]:
    """{path: content} -> {path: lastmod}. A page's date moves only when its content changes."""
    try:
        known = json.loads(LASTMOD_FILE.read_text())
    except (FileNotFoundError, ValueError):
        known = {}
    out = {}
    for path, content in contents.items():
        h = content_hash(content)
        if known.get(path, {}).get("hash") != h:
            known[path] = {"hash": h, "date": today}
        out[path] = known[path]["date"]
    LASTMOD_FILE.write_text(json.dumps({k: known[k] for k in sorted(contents)}, indent=1) + "\n")
    return out


def sitemap_xml(lastmod: dict[str, str]) -> str:
    body = "\n".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{d}</lastmod></url>" for u, d in lastmod.items())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n")
