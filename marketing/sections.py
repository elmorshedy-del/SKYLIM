"""Homepage sections, top to bottom. Each function returns one self-contained block.

Content comes from data.py (brand, services, places, vehicle, amenities, voice,
FAQs, pricing); layout lives here; styling in static/site.css; behaviour in
static/site.js.
"""
from __future__ import annotations

from html import escape as e

import data
import landing_pages
from . import brand
from .icons import AMENITY_ICONS, FEATURE_ICONS, cabin_plan, icon
from .seo import journey_price

V = data.VOICE
P = data.PRICING
SERVICE_ICONS = {"airport": "plane", "hourly": "clock", "transfer": "route", "events": "star",
                 "corporate": "briefcase", "long": "road"}
HOME_IDS = frozenset({"services", "cabin", "pricing", "faq", "bespoke", "reserve"})


def _to(anchor: str, local: frozenset) -> str:
    """In-page link when the section is on this page, otherwise the home page's section."""
    return f"#{anchor}" if anchor in local else f"/#{anchor}"


def _money(cents: int) -> str:
    return f"${cents / 100:,.0f}"


def header(local: frozenset = HOME_IDS) -> str:
    b = data.BRAND
    return f"""
<header class="nav" id="top">
  <div class="wrap nav-in">
    <a class="brand" href="/" aria-label="{e(b['name'])} home">{brand.wordmark()}</a>
    <nav class="links" aria-label="Primary">
      <a href="{_to('services', local)}">Services</a><a href="/airport-transfers">Airports</a>
<a href="{_to('cabin', local)}">The Escalade</a><a href="{_to('pricing', local)}">Pricing</a><a href="{_to('faq', local)}">FAQ</a>
    </nav>
    <a class="btn btn-light btn-sm" href="#reserve" data-track="nav_cta">Reserve</a>
  </div>
</header>"""


def _place_options(placeholder: str, selected: str = "") -> str:
    out = [f'<option value="">{e(placeholder)}</option>']
    for group in data.PLACE_GROUPS:
        out.append(f'<optgroup label="{e(group)}">')
        out += [f'<option value="{p["code"]}"{" selected" if p["code"] == selected else ""}>{e(p["name"])}</option>'
                for p in data.PLACES if p["group"] == group]
        out.append("</optgroup>")
    return "".join(out)


def _stepper(name: str, label: str, value: int, lo: int, hi: int) -> str:
    return f"""<div class="stepper" data-stepper>
      <span class="stepper-l" id="{name}-l">{label}</span>
      <button type="button" class="step-b" data-step="-1" aria-label="Fewer {label.lower()}">{icon('minus', 18)}</button>
      <output class="num" id="{name}" data-min="{lo}" data-max="{hi}" aria-labelledby="{name}-l" aria-live="polite">{value}</output>
      <button type="button" class="step-b" data-step="1" aria-label="More {label.lower()}">{icon('plus', 18)}</button>
    </div>"""


def pay_trust() -> str:
    """One line of reassurance at the moment of decision, worded the way checkout pages are."""
    p = data.PAYMENT
    return (f'<p class="pay-trust">{icon("lock", 14)}<span>Secure checkout powered by {e(p["processor"])}'
            f'<small>{e(" · ".join(p["wallets"] + ["cards"]))}</small></span></p>')


def luggage_guide() -> str:
    rows = "".join(f'<li><b>{e(g)}</b><span>{e(f)}</span><small>{e(n)}</small></li>'
                   for g, f, n in data.VEHICLE["luggage_guide"])
    return (f'<ul class="guide-list">{rows}</ul>'
            '<p class="guide-note">Large = checked suitcase up to about 28 in. Carry-on = cabin-size roll-aboard '
            'or holdall. Golf bags, skis or a stroller? Add them in your notes.</p>')


def quote_panel(preset: tuple[str, str] = ("", "")) -> str:
    """The reservation form. `preset` pre-selects (pickup, destination) for a landing page."""
    origin, destination = preset
    hours = "".join(f'<option value="{h}"{" selected" if h == 4 else ""}>{h} hours</option>'
                    for h in range(P["hourly_min_hours"], P["hourly_max_hours"] + 1))
    return f"""<div class="quote" id="reserve">
      <form id="quote-form" class="quote-form" novalidate aria-labelledby="quote-h">
        <h2 id="quote-h" class="quote-h">Reserve your chauffeur</h2>
        <div class="mode-tabs" role="tablist" aria-label="Type of reservation">
          <button type="button" role="tab" class="mt on" aria-selected="true" data-service="transfer">One way</button>
          <button type="button" role="tab" class="mt" aria-selected="false" data-service="hourly">By the hour</button>
        </div>
        <label class="field"><span class="sr">Pickup</span>{icon('pin', 20)}
          <select id="q-from" required aria-describedby="q-err">{_place_options('Pickup area or airport', origin)}</select></label>
        <label class="field" data-for="transfer"><span class="sr">Destination</span>{icon('flag', 20)}
          <select id="q-to">{_place_options('Destination', destination)}</select></label>
        <label class="field" data-for="hourly" hidden><span class="sr">Duration</span>{icon('clock', 20)}
          <select id="q-hours">{hours}</select></label>
        <label class="field"><span class="sr">Pickup date</span>{icon('calendar', 20)}
          <input id="q-date" type="date" required></label>
        <input type="hidden" id="q-when">
        <div class="slots">
          <p class="slots-msg" id="q-slots-msg" aria-live="polite">Choose your journey and date to see available pickup times.</p>
          <div class="slot-grid" id="q-slot-grid" role="group" aria-label="Available pickup times, New York time"></div>
          <p class="limited">{icon('clock', 14)}{e(data.OPERATIONS['availability_note'])}</p>
        </div>
        <div class="steppers three">{_stepper('q-pax', 'Guests', 1, 1, data.VEHICLE['max_passengers'])}
          {_stepper('q-bags', 'Large', 1, 0, 8)}{_stepper('q-carry', 'Carry-on', 1, 0, 8)}</div>
        <div class="fit" id="q-fit" aria-live="polite">
          <div class="fit-bar"><i id="q-fit-bar"></i></div>
          <p class="fit-tx"><span id="q-fit-tx">Fits comfortably</span>
            <button type="button" class="link" id="q-fit-help" aria-expanded="false" aria-controls="q-guide">What fits?</button></p>
          <div class="guide" id="q-guide" hidden>{luggage_guide()}</div>
        </div>
        <p class="err" id="q-err" role="alert" hidden></p>
        <button class="btn btn-dark btn-block btn-lg" type="submit" data-track="quote_submit">See price</button>
        {pay_trust()}
      </form>

      <div class="result" id="quote-result" hidden aria-live="polite">
        <p class="result-route" id="r-route"></p>
        <p class="result-price num"><span id="r-price"></span> <s class="was" id="r-was"></s></p>
        <p class="offer" id="r-offer" hidden></p>
        <p class="result-meta" id="r-meta"></p>
        <ul class="result-msgs" id="r-msgs"></ul>
        <div class="alts" id="r-alts"></div>
        <button class="btn btn-dark btn-block btn-lg" id="r-book" type="button" data-track="reserve_start">Reserve</button>
        <button class="btn btn-ghost btn-block" id="r-edit" type="button">Change details</button>
        {pay_trust()}
      </div>
    </div>"""


def hero() -> str:
    # The H1 carries the descriptive phrase (small line) and the brand line (large): Google reads both,
    # the reader sees the same composition as before.
    return f"""
<section class="hero" aria-labelledby="hero-h">
  <div class="wrap hero-in">
    <div class="hero-copy">
      <div class="hero-logo">{brand.lockup(mode="loop", ids="ch-", pad=0)}</div>
      <h1 id="hero-h"><span class="eyebrow">Chauffeur service · New York City &amp; New Jersey</span>Arrive composed.</h1>
      <p class="lede">A Cadillac Escalade and a professional chauffeur for Newark, JFK and LaGuardia, Teterboro's
        private terminals, meetings across Manhattan and evenings out. All-inclusive pricing, reserved in under a
        minute.</p>
      <ul class="hero-points">
        <li>{icon('seat', 18)}Captain's chairs</li><li>{icon('wifi', 18)}Onboard Wi-Fi</li>
        <li>{icon('sun', 18)}Panoramic sunroof</li>
      </ul>
    </div>

    {quote_panel()}
  </div>
</section>"""


def services() -> str:
    cards = "".join(
        f'<li><a class="svc" href="{"#bespoke" if how == "inquiry" else "#reserve"}" data-service="{how}" '
        f'data-kind="{code}">{icon(SERVICE_ICONS[code], 28)}<h3>{e(title)}</h3><p>{e(text)}</p>'
        f'<span class="more">{"Open an account" if how == "inquiry" else "Reserve"} {icon("arrow", 16)}</span></a></li>'
        for code, title, text, how in data.SERVICES)
    return f"""
<section class="sec" id="services" aria-labelledby="svc-h">
  <div class="wrap">
    <p class="eyebrow">Services</p>
    <h2 id="svc-h" class="h2">Wherever the day takes you.</h2>
    <ul class="services">{cards}</ul>
    <p class="svc-links">Flying? See how pickups work at <a href="/airport-transfers/newark">Newark</a>,
      <a href="/airport-transfers/jfk">JFK</a>, <a href="/airport-transfers/laguardia">LaGuardia</a> and
      <a href="/airport-transfers/teterboro">Teterboro</a>.</p>
  </div>
</section>"""


def cabin() -> str:
    feats = "".join(f'<li>{icon(FEATURE_ICONS.get(k, "check"), 26)}<div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>'
                    for k, t, d in data.VEHICLE["features"])
    groups = []
    for g in data.AMENITY_GROUPS:
        items = "".join(f'<li>{icon(AMENITY_ICONS.get(k, "check"), 18)}{e(a["label"])}</li>'
                        for k, a in data.AMENITIES.items() if a["available"] and a["group"] == g)
        if items:
            groups.append(f'<div class="amen"><h4>{e(g)}</h4><ul>{items}</ul></div>')
    return f"""
<section class="sec dark" id="cabin" aria-labelledby="cabin-h">
  <div class="wrap">
    <div class="cabin-in">
      <div class="cabin-art">{cabin_plan()}</div>
      <div>
        <p class="eyebrow">The Cadillac Escalade</p>
        <h2 id="cabin-h" class="h2">Your office. Your lounge. Between appointments.</h2>
        <p class="lede">Every journey is in a Cadillac Escalade, prepared to your preferences before you open
          the door — temperature, music, conversation, a quiet cabin for calls.</p>
        <ul class="features">{feats}</ul>
        <div class="fits-card">
          <p class="eyebrow">What fits</p>
          {luggage_guide()}
        </div>
      </div>
    </div>
    <div class="amenities">{''.join(groups)}</div>
  </div>
</section>"""


def standard() -> str:
    icons_ = ["car", "tag", "shield", "lock", "pin"]
    items = "".join(f'<li>{icon(i, 28)}<h3>{e(t)}</h3><p>{e(d)}</p></li>' for i, (t, d) in zip(icons_, V["standard"]))
    return f"""
<section class="sec" id="standard" aria-labelledby="std-h">
  <div class="wrap">
    <p class="eyebrow">The {e(data.BRAND['short'])} Standard</p>
    <h2 id="std-h" class="h2">{e(V['promise'])}</h2>
    <ul class="pillars">{items}</ul>
  </div>
</section>"""


def how() -> str:
    steps = [
        ("route", "Choose your journey", "One way or by the hour — airports, addresses, private aviation."),
        ("tag", "See your price", "All-inclusive: tolls, congestion charges and gratuity. No surprises later."),
        ("card", "Reserve and pay", "Apple Pay, Google Pay, Link or card, through Stripe. Confirmed in moments."),
        ("pin", "Meet your chauffeur", "Your trip page shows your chauffeur, the vehicle, its plate — and its live position."),
    ]
    items = "".join(f'<li><span class="n num">{i}</span>{icon(ic, 26)}<h3>{e(t)}</h3><p>{e(d)}</p></li>'
                    for i, (ic, t, d) in enumerate(steps, 1))
    return f"""
<section class="sec tint" id="how" aria-labelledby="how-h">
  <div class="wrap">
    <p class="eyebrow">How it works</p>
    <h2 id="how-h" class="h2">Reserved in under a minute.</h2>
    <ol class="steps">{items}</ol>
  </div>
</section>"""


ESTIMATE_NOTE = ("" if P["approved"] else
                 " Prices shown are estimates until our rates are finalised; your price is confirmed before you pay.")


def price_tag(origin: str, destination: str) -> str:
    """'from $X' markup for a journey, with the launch offer if one is running; '' if not instantly priced."""
    list_cents, today, offer = journey_price(origin, destination)
    if not list_cents:
        return ""
    price = (f'<b class="num">{_money(today)}</b><s class="num">{_money(list_cents)}</s>' if offer
             else f'<b class="num">{_money(list_cents)}</b>')
    return f'<span class="jr-p"><small>from</small>{price}</span>'


def journey_items(pairs) -> str:
    """Tappable journeys: each pre-fills the form and shows the live price."""
    places = {p["code"]: p for p in data.PLACES}
    out = []
    for a, b in pairs:
        tag = price_tag(a, b)
        if tag:
            out.append(f'<li><a class="jr" href="#reserve" data-from="{a}" data-to="{b}">'
                       f'<span>{e(places[a]["short"])} <i aria-hidden="true">→</i> {e(places[b]["short"])}</span>'
                       f'{tag}</a></li>')
    return "".join(out)


def pricing() -> str:
    cards = [journey_items(data.POPULAR_JOURNEYS)]
    note = ESTIMATE_NOTE
    return f"""
<section class="sec" id="pricing" aria-labelledby="pricing-h">
  <div class="wrap">
    <p class="eyebrow">Pricing</p>
    <h2 id="pricing-h" class="h2">The quote is the receipt.</h2>
    <p class="lede">Every price includes tolls, congestion charges and gratuity.{e(note)}</p>
    <div class="pricing-in">
      <div class="hourly-card">
        <p class="eyebrow">By the hour</p>
        <p class="hourly-price num">{_money(P['hourly_cents'])}<span>/hour</span></p>
        <p>All-inclusive, {P['hourly_min_hours']}-hour minimum. Your chauffeur stays with you between appointments.</p>
        <a class="btn btn-light" href="#reserve" data-service="hourly" data-track="hourly_cta">Reserve by the hour</a>
      </div>
      <ul class="journeys">{''.join(cards)}</ul>
    </div>
  </div>
</section>"""


def secure() -> str:
    """Book with confidence: how payment is protected, in the words clients know from checkout pages."""
    p, hours = data.PAYMENT, data.POLICY["free_cancel_hours"]
    later = f" — or pay over time with {p['pay_later']}" if p.get("pay_later") else ""
    items = [
        ("shield", f"Secure checkout, powered by {p['processor']}",
         f"Payments are processed by {p['processor']}, certified to PCI DSS Level 1 — the highest standard in "
         "the payments industry. Your card details are encrypted and never reach our servers."),
        ("card", "Pay your way",
         f"{', '.join(p['wallets'])} and all major cards{later}. With Apple Pay and Google Pay, your card "
         "number is never shared at all."),
        ("calendar", "Free cancellation",
         f"Cancel free of charge up to {hours} hours before pickup. Refunds go straight back to your original "
         "payment method."),
        ("tag", "Price locked. Receipt instantly.",
         "The price you see is the price you pay — tolls, congestion charges and gratuity included. Your "
         "receipt arrives by email the moment you book, and your statement shows your trip reference."),
    ]
    cards = "".join(f'<li>{icon(i, 26)}<h3>{e(t)}</h3><p>{e(d)}</p></li>' for i, t, d in items)
    marks = "".join(f"<li>{e(m)}</li>" for m in p["wallets"] + p["cards"] + ([p["pay_later"]] if p.get("pay_later") else []))
    return f"""
<section class="sec" id="secure" aria-labelledby="secure-h">
  <div class="wrap">
    <p class="eyebrow">Book with confidence</p>
    <h2 id="secure-h" class="h2">Secure from the first tap.</h2>
    <p class="lede">Every payment is handled by {e(p['processor'])}, the payment platform trusted by millions of
      businesses worldwide.</p>
    <ul class="pillars secure-list">{cards}</ul>
    <ul class="pay-marks" aria-label="Accepted payment methods">{marks}</ul>
  </div>
</section>"""


def realtime() -> str:
    return f"""
<section class="sec tint" id="realtime" aria-labelledby="rt-h">
  <div class="wrap trip-in">
    <div>
      <p class="eyebrow">On the day</p>
      <h2 id="rt-h" class="h2">Know exactly where your car is.</h2>
      <p class="lede">Your private trip page shows your chauffeur, the vehicle and its plate. Once your chauffeur
        sets off, you see the car's actual position and exactly when it was last reported — never a guess.</p>
      <ul class="ticks">
        <li>{icon('check', 18)}Share a location-only link with an assistant or whoever is meeting you</li>
        <li>{icon('check', 18)}Add the pickup to your calendar in one tap</li>
        <li>{icon('check', 18)}Location is visible only during your journey, then deleted</li>
      </ul>
    </div>
    <figure class="phone" aria-label="Example of a trip page">
      <span class="example">Example</span>
      <div class="ph-top"><b>Chauffeur on the way</b><span class="live"><i></i>Live</span></div>
      <svg class="ph-map" viewBox="0 0 300 200" aria-hidden="true">
        <path class="road" d="M-10 150 C 60 140, 90 90, 150 95 S 250 60, 310 40"/>
        <path class="road thin" d="M40 -10 C 60 60, 80 120, 70 210"/><path class="road thin" d="M200 -10 C 210 70, 230 140, 260 210"/>
        <circle class="me" cx="232" cy="66" r="7"/>
        <g class="carpin" transform="translate(132 98)"><circle r="15"/><path d="M-7 3h14M-8 0l1.5-4.5h13L8 0v4h-16z"/></g>
      </svg>
      <div class="ph-meta"><span>Updated 6 s ago</span><span>Cadillac Escalade</span></div>
      <div class="ph-card"><span class="av">A</span><div><b>Your chauffeur</b><small>Arriving at your door</small></div>
        <span class="plate">ABC·123</span></div>
    </figure>
  </div>
</section>"""


def bespoke() -> str:
    points = [("star", "Evenings & occasions", "Galas, theatre, weddings — dropped at the door, collected when ready."),
              ("road", "Long distance", "Philadelphia, the Hamptons, the Shore, Connecticut and beyond."),
              ("route", "Multi-stop days", "Several appointments, one chauffeur, one all-inclusive price.")]
    items = "".join(f'<li>{icon(i, 24)}<div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>' for i, t, d in points)
    return f"""
<section class="sec dark" id="bespoke-sec" aria-labelledby="bespoke-h">
  <div class="wrap band-in">
    <div>
      <p class="eyebrow">Bespoke</p>
      <h2 id="bespoke-h" class="h2">Something less ordinary?</h2>
      <p class="lede">Tell us the occasion. We will plan the timing, the route and the details, and reply
        personally with a firm price.</p>
      <ul class="features">{items}</ul>
    </div>
    {bespoke_form()}
  </div>
</section>"""


def bespoke_form() -> str:
    return """<form class="custom" id="bespoke" novalidate aria-label="Arrange something bespoke">
      <h3 class="custom-h">Arrange something bespoke</h3>
      <label>Occasion<select name="topic">
        <option>An event or occasion</option>
        <option>A long-distance journey</option>
        <option>A multi-stop day</option>
        <option>Something else</option></select></label>
      <label>Name<input name="name" autocomplete="name" maxlength="100"></label>
      <label>Email<input name="email" type="email" autocomplete="email" required maxlength="254"></label>
      <label>Phone<input name="phone" type="tel" autocomplete="tel" maxlength="25"></label>
      <label>Details<textarea name="message" rows="3" maxlength="1500" required
        placeholder="Dates, times, places, number of guests"></textarea></label>
      <input name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
      <button class="btn btn-light btn-block" type="submit">Send</button>
      <p class="form-out" role="status"></p>
    </form>"""


def faq(items_: list[tuple[str, str]] | None = None, heading: str = "Before you reserve.") -> str:
    items = "".join(f'<details{" open" if i == 0 else ""}><summary>{e(q)}</summary><p>{e(a)}</p></details>'
                    for i, (q, a) in enumerate(items_ if items_ is not None else data.FAQS))
    return f"""
<section class="sec" id="faq" aria-labelledby="faq-h">
  <div class="wrap faq-in">
    <div><p class="eyebrow">Questions</p><h2 id="faq-h" class="h2">{e(heading)}</h2>
      <p class="lede">Anything else? <a href="mailto:{e(data.BRAND['email'])}">{e(data.BRAND['email'])}</a></p></div>
    <div class="faq">{items}</div>
  </div>
</section>"""


def closing() -> str:
    return f"""
<section class="sec band-cta" aria-labelledby="cta-h">
  <div class="wrap cta-in">
    <h2 id="cta-h" class="h2">Your chauffeur is a minute away from confirmed.</h2>
    <a class="btn btn-dark btn-lg" href="#reserve" data-track="closing_cta">Reserve now</a>
  </div>
</section>"""


FOOTER_GROUPS = [
    ("Airports", ["/airport-transfers/newark", "/airport-transfers/jfk", "/airport-transfers/laguardia",
                  "/airport-transfers/teterboro"]),
    ("Chauffeur service", ["/nyc-chauffeur-service", "/nj-limo-service", "/airport-transfers"]),
]


def footer(local: frozenset = HOME_IDS) -> str:
    b = data.BRAND
    authority = f'<p>{e(b["authority_display"])}</p>' if b.get("authority_display") else ""
    groups = "".join(
        f'<div><p class="foot-h">{e(title)}</p><ul>'
        + "".join(f'<li><a href="{path}">{e(landing_pages.BY_PATH[path]["link"])}</a></li>' for path in paths)
        + "</ul></div>" for title, paths in FOOTER_GROUPS)
    return f"""
<footer class="foot">
  <div class="wrap">
    <div class="foot-top">
      <a class="foot-logo" href="/" aria-label="{e(b['name'])} home">{brand.lockup(mode="once", ids="cf-")}</a>
      <nav aria-label="Footer"><a href="{_to('services', local)}">Services</a><a href="{_to('pricing', local)}">Pricing</a>
<a href="{_to('bespoke', local)}">Bespoke</a>
        <a href="{_to('faq', local)}">FAQ</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="/accessibility">Accessibility</a></nav>
    </div>
    <div class="foot-links">{groups}</div>
    <address><a href="tel:{e(b['phone_raw'])}">{e(b['phone_display'])}</a> · <a href="mailto:{e(b['email'])}">{e(b['email'])}</a> · {e(b['base_town'])}</address>
    {authority}
    <p class="areas">{e(b['descriptor'])} across New Jersey, New York City, Westchester, Long Island, Fairfield County
      and Philadelphia.</p>
    <p class="fine">© <span data-year></span> {e(b['name'])}. {e(data.OPERATIONS['hours_label'])}.</p>
  </div>
</footer>
<div class="mbar" id="mbar"><a class="btn btn-dark btn-block" href="#reserve" data-track="mobile_cta">Reserve</a></div>"""
