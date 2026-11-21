"""Search landing pages: one per real search intent (copy in landing_pages.py).

Each page answers its own question first — prices for its journeys, how the pickup works,
its own FAQs — and reuses the site's shared sections for the car, bespoke requests and
reservations, so every page looks and books exactly like the home page.
"""
from __future__ import annotations

from html import escape as e

import data
import landing_pages
from . import booking, sections, seo
from .icons import icon

# Sections present on every landing page (in-page links); others link to the home page.
LOCAL_IDS = frozenset({"reserve", "cabin", "faq", "bespoke"})


def _t(text: str) -> str:
    """Copy with live prices filled, HTML-escaped."""
    return e(seo.fill(text))


def faqs(page: dict) -> list[tuple[str, str]]:
    return [(seo.fill(q), seo.fill(a)) for q, a in page["faqs"]]


def _crumbs(page: dict) -> str:
    trail = seo.breadcrumbs(page)
    items = "".join(f'<li><a href="{path}">{e(name)}</a></li>' for name, path in trail[:-1])
    return (f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}'
            f'<li aria-current="page">{e(trail[-1][0])}</li></ol></nav>')


def hero(page: dict) -> str:
    points = "".join(f"<li>{icon('check', 18)}{_t(p)}</li>" for p in page["points"])
    return f"""
<section class="hero" aria-labelledby="hero-h">
  <div class="wrap hero-in">
    <div class="hero-copy">
      {_crumbs(page)}
      <p class="eyebrow">{e(page['eyebrow'])}</p>
      <h1 id="hero-h" class="h1-page">{e(page['h1'])}</h1>
      <p class="lede">{_t(page['lede'])}</p>
      <ul class="hero-points">{points}</ul>
    </div>
    {sections.quote_panel(page['preset'])}
  </div>
</section>"""


def routes(page: dict) -> str:
    items = sections.journey_items(page["routes"])
    if not items:
        return ""
    return f"""
<section class="sec" id="prices" aria-labelledby="prices-h">
  <div class="wrap">
    <p class="eyebrow">Prices</p>
    <h2 id="prices-h" class="h2">{e(page['routes_h2'])}</h2>
    <p class="lede">Tolls, congestion charges, airport parking and gratuity included. Tap a journey to see your
      price for a specific time.{e(sections.ESTIMATE_NOTE)}</p>
    <ul class="journeys">{items}</ul>
  </div>
</section>"""


def airports(page: dict) -> str:
    """Hub page: every airport we serve, linked to its own page where one exists."""
    if not page.get("airports"):
        return ""
    places = {p["code"]: p for p in data.PLACES}
    cards = []
    for code, path, note, (a, b) in page["airports"]:
        tag = sections.price_tag(a, b)
        sample = (f'<span class="port-p">{tag}<small>{e(places[a]["short"])} → {e(places[b]["short"])}</small></span>'
                  if tag else "")
        if path:
            open_, more = f'<a class="port" href="{path}">', "Pickup details"
        else:
            open_, more = f'<a class="port jr" href="#reserve" data-from="{a}" data-to="{b}">', "See your price"
        cards.append(f'<li>{open_}{icon("plane", 24)}<h3>{e(places[code]["name"])}</h3><p>{e(note)}</p>'
                     f'{sample}<span class="more">{more} {icon("arrow", 16)}</span></a></li>')
    return f"""
<section class="sec" id="airports" aria-labelledby="ports-h">
  <div class="wrap">
    <p class="eyebrow">Airports</p>
    <h2 id="ports-h" class="h2">Seven airports, one standard.</h2>
    <ul class="ports">{''.join(cards)}</ul>
  </div>
</section>"""


def prose(page: dict) -> str:
    if not page["sections"]:
        return ""
    blocks = "".join(f'<div class="prose"><h2 class="h2">{e(h)}</h2><div class="prose-tx">'
                     + "".join(f"<p>{_t(para)}</p>" for para in paras) + "</div></div>"
                     for h, paras in page["sections"])
    return f'\n<section class="sec tint" aria-label="Details"><div class="wrap prose-grid">{blocks}</div></section>'


def steps(page: dict) -> str:
    if not page["steps"]:
        return ""
    items = "".join(f'<li><span class="n num">{i}</span>{icon(ic, 26)}<h3>{e(t)}</h3><p>{_t(d)}</p></li>'
                    for i, (ic, t, d) in enumerate(page["steps"], 1))
    return f"""
<section class="sec" id="how" aria-labelledby="how-h">
  <div class="wrap">
    <p class="eyebrow">How it works</p>
    <h2 id="how-h" class="h2">{e(page['steps_h2'])}</h2>
    <ol class="steps">{items}</ol>
  </div>
</section>"""


def related(page: dict) -> str:
    links = "".join(f'<li><a href="{path}">{e(landing_pages.BY_PATH[path]["link"])}{icon("arrow", 18)}</a></li>'
                    for path in page["related"])
    return f"""
<section class="sec" aria-labelledby="rel-h">
  <div class="wrap">
    <p class="eyebrow">Also</p>
    <h2 id="rel-h" class="h2">Where else we can take you.</h2>
    <ul class="related">{links}<li><a href="/">The full service{icon("arrow", 18)}</a></li></ul>
  </div>
</section>"""


def body(page: dict) -> str:
    return "".join([
        sections.header(LOCAL_IDS),
        '<main id="main">',
        hero(page), airports(page), routes(page), prose(page), steps(page), sections.cabin(),
        sections.faq(faqs(page)), related(page), sections.bespoke(), sections.closing(),
        "</main>",
        sections.footer(LOCAL_IDS),
        booking.dialog(),
    ])


def head(page: dict) -> str:
    return seo.head_meta(seo.page_title(page), page["description"], page["path"],
                         seo.jsonld_page(page, faqs(page)))
