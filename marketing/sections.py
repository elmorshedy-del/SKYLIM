"""Homepage sections, top to bottom. Each function returns one self-contained block.

Content comes from data.py (brand, services, places, vehicle, amenities, voice,
FAQs, pricing); layout lives here; styling in static/site.css; behaviour in
static/site.js.
"""
from __future__ import annotations

from html import escape as e

import data
from .icons import AMENITY_ICONS, FEATURE_ICONS, cabin_plan, icon
from .seo import journey_price

V = data.VOICE
P = data.PRICING
SERVICE_ICONS = {"airport": "plane", "hourly": "clock", "transfer": "route", "events": "star",
                 "corporate": "briefcase", "long": "road"}


def _money(cents: int) -> str:
    return f"${cents / 100:,.0f}"


def header() -> str:
    b = data.BRAND
    return f"""
<header class="nav" id="top">
  <div class="wrap nav-in">
    <a class="brand" href="/" aria-label="{e(b['name'])} home"><span class="mark" aria-hidden="true">M</span>{e(b['short'])}</a>
    <nav class="links" aria-label="Primary">
      <a href="#services">Services</a><a href="#cabin">The Escalade</a><a href="#pricing">Pricing</a>
      <a href="#corporate">Corporate</a><a href="#faq">FAQ</a>
    </nav>
    <a class="btn btn-light btn-sm" href="#reserve" data-track="nav_cta">Reserve</a>
  </div>
</header>"""


def _place_options(placeholder: str) -> str:
    out = [f'<option value="">{e(placeholder)}</option>']
    for group in data.PLACE_GROUPS:
        out.append(f'<optgroup label="{e(group)}">')
        out += [f'<option value="{p["code"]}">{e(p["name"])}</option>' for p in data.PLACES if p["group"] == group]
        out.append("</optgroup>")
    return "".join(out)


def _stepper(name: str, label: str, value: int, lo: int, hi: int) -> str:
    return f"""<div class="stepper" data-stepper>
      <span class="stepper-l" id="{name}-l">{label}</span>
      <button type="button" class="step-b" data-step="-1" aria-label="Fewer {label.lower()}">{icon('minus', 18)}</button>
      <output class="num" id="{name}" data-min="{lo}" data-max="{hi}" aria-labelledby="{name}-l" aria-live="polite">{value}</output>
      <button type="button" class="step-b" data-step="1" aria-label="More {label.lower()}">{icon('plus', 18)}</button>
    </div>"""


def hero() -> str:
    hours = "".join(f'<option value="{h}"{" selected" if h == 4 else ""}>{h} hours</option>'
                    for h in range(P["hourly_min_hours"], P["hourly_max_hours"] + 1))
    return f"""
<section class="hero" aria-labelledby="hero-h">
  <div class="wrap hero-in">
    <div class="hero-copy">
      <p class="eyebrow">{e(data.BRAND['descriptor'])} · New York &amp; New Jersey</p>
      <h1 id="hero-h">Arrive composed.</h1>
      <p class="lede">A Cadillac Escalade and a professional chauffeur for airports, private aviation, meetings
        and evenings. All-inclusive pricing, reserved in under a minute.</p>
      <ul class="hero-points">
        <li>{icon('seat', 18)}Captain's chairs</li><li>{icon('wifi', 18)}Onboard Wi-Fi</li>
        <li>{icon('sun', 18)}Panoramic sunroof</li>
      </ul>
    </div>

    <div class="quote" id="reserve">
      <form id="quote-form" class="quote-form" novalidate aria-labelledby="quote-h">
        <h2 id="quote-h" class="quote-h">Reserve your chauffeur</h2>
        <div class="mode-tabs" role="tablist" aria-label="Type of reservation">
          <button type="button" role="tab" class="mt on" aria-selected="true" data-service="transfer">One way</button>
          <button type="button" role="tab" class="mt" aria-selected="false" data-service="hourly">By the hour</button>
        </div>
        <label class="field"><span class="sr">Pickup</span>{icon('pin', 20)}
          <select id="q-from" required aria-describedby="q-err">{_place_options('Pickup area or airport')}</select></label>
        <label class="field" data-for="transfer"><span class="sr">Destination</span>{icon('flag', 20)}
          <select id="q-to">{_place_options('Destination')}</select></label>
        <label class="field" data-for="hourly" hidden><span class="sr">Duration</span>{icon('clock', 20)}
          <select id="q-hours">{hours}</select></label>
        <label class="field"><span class="sr">Pickup date and time (Eastern)</span>{icon('calendar', 20)}
          <input id="q-when" type="datetime-local" required></label>
        <div class="steppers">{_stepper('q-pax', 'Guests', 1, 1, 6)}{_stepper('q-bags', 'Bags', 1, 0, 8)}</div>
        <p class="err" id="q-err" role="alert" hidden></p>
        <button class="btn btn-dark btn-block btn-lg" type="submit" data-track="quote_submit">See price</button>
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
      </div>
    </div>
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


def pricing() -> str:
    places = {p["code"]: p for p in data.PLACES}
    cards = []
    for a, b in data.POPULAR_JOURNEYS:
        list_cents, today, offer = journey_price(a, b)
        if not list_cents:
            continue
        price = (f'<b class="num">{_money(today)}</b><s class="num">{_money(list_cents)}</s>' if offer
                 else f'<b class="num">{_money(list_cents)}</b>')
        cards.append(f'<li><a class="jr" href="#reserve" data-from="{a}" data-to="{b}">'
                     f'<span>{e(places[a]["short"])} <i aria-hidden="true">→</i> {e(places[b]["short"])}</span>'
                     f'<span class="jr-p"><small>from</small>{price}</span></a></li>')
    note = ("" if P["approved"] else
            " Prices shown are estimates until our rates are finalised; your price is confirmed before you pay.")
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


def corporate() -> str:
    points = [("briefcase", "One account, every traveller", "Book for executives, guests and roadshows from one place."),
              ("card", "Consolidated monthly invoicing", "One invoice, itemised by traveller and journey."),
              ("shield", "Discretion and duty of care", "Real-time trip status for assistants and travel managers.")]
    items = "".join(f'<li>{icon(i, 24)}<div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>' for i, t, d in points)
    return f"""
<section class="sec dark" id="corporate" aria-labelledby="corp-h">
  <div class="wrap band-in">
    <div>
      <p class="eyebrow">Corporate accounts</p>
      <h2 id="corp-h" class="h2">Ground transportation your executives won't think about.</h2>
      <ul class="features">{items}</ul>
    </div>
    {bespoke_form()}
  </div>
</section>"""


def bespoke_form() -> str:
    return """<form class="custom" id="bespoke" novalidate aria-label="Arrange something bespoke">
      <h3 class="custom-h">Arrange something bespoke</h3>
      <label>I'd like to<select name="kind">
        <option value="corporate">Open a corporate account</option>
        <option value="custom_quote">Arrange an event or occasion</option>
        <option value="custom_quote">Plan a long-distance journey</option>
        <option value="custom_quote">Something else</option></select></label>
      <label>Name<input name="name" autocomplete="name" maxlength="100"></label>
      <label>Email<input name="email" type="email" autocomplete="email" required maxlength="254"></label>
      <label>Phone<input name="phone" type="tel" autocomplete="tel" maxlength="25"></label>
      <label>Details<textarea name="message" rows="3" maxlength="1500" required
        placeholder="Dates, times, places, number of guests"></textarea></label>
      <input name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
      <button class="btn btn-light btn-block" type="submit">Send</button>
      <p class="form-out" role="status"></p>
    </form>"""


def faq() -> str:
    items = "".join(f'<details{" open" if i == 0 else ""}><summary>{e(q)}</summary><p>{e(a)}</p></details>'
                    for i, (q, a) in enumerate(data.FAQS))
    return f"""
<section class="sec" id="faq" aria-labelledby="faq-h">
  <div class="wrap faq-in">
    <div><p class="eyebrow">Questions</p><h2 id="faq-h" class="h2">Before you reserve.</h2>
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


def footer() -> str:
    b = data.BRAND
    authority = f'<p>{e(b["authority_display"])}</p>' if b.get("authority_display") else ""
    return f"""
<footer class="foot">
  <div class="wrap">
    <div class="foot-top">
      <a class="brand" href="/"><span class="mark" aria-hidden="true">M</span>{e(b['short'])}</a>
      <nav aria-label="Footer"><a href="#services">Services</a><a href="#pricing">Pricing</a><a href="#corporate">Corporate</a>
        <a href="#faq">FAQ</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="/accessibility">Accessibility</a></nav>
    </div>
    <address><a href="tel:{e(b['phone_raw'])}">{e(b['phone_display'])}</a> · <a href="mailto:{e(b['email'])}">{e(b['email'])}</a> · {e(b['base_town'])}</address>
    {authority}
    <p class="areas">{e(b['descriptor'])} across New Jersey, New York City, Westchester, Long Island, Fairfield County
      and Philadelphia — Newark, JFK, LaGuardia, Teterboro, Morristown and Westchester airports.</p>
    <p class="fine">© <span data-year></span> {e(b['name'])}. {e(data.OPERATIONS['hours_label'])}.</p>
  </div>
</footer>
<div class="mbar" id="mbar"><a class="btn btn-dark btn-block" href="#reserve" data-track="mobile_cta">Reserve</a></div>"""
