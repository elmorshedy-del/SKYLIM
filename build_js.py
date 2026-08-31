JS = r"""
/* =========================================================================
   MERIDIAN BLACK CAR — front-end application
   -------------------------------------------------------------------------
   GO-LIVE HOOKS are marked with  // >>> HOOK:  and documented in
   INTEGRATION-GUIDE.md. Everything else runs fully client-side today.
   ========================================================================= */
(function () {
  'use strict';

  /* ---------------------------------------------------------------- config */
  var CFG = {
    // >>> HOOK: PAYMENTS — replace with your Stripe publishable key, then
    //     swap fakeCharge() for stripe.confirmCardPayment(). See guide §1.
    stripePublishableKey: null,

    // >>> HOOK: SMS — your backend endpoint that relays to Twilio. See guide §2.
    smsEndpoint: null,

    // >>> HOOK: DRIVER GPS — polling endpoint fed by the driver app. See guide §3.
    gpsEndpoint: null,

    // >>> HOOK: BOOKINGS — where confirmed bookings are POSTed. See guide §4.
    bookingEndpoint: null,

    // LIVE EVENT FEEDS ------------------------------------------------------
    // MLB Stats API needs no key and is CORS-open. Yankees data is live now.
    mlbBase: 'https://statsapi.mlb.com/api/v1',
    yankeesTeamId: 147,
    // Ticketmaster Discovery API needs a free key from
    // https://developer.ticketmaster.com  (2 min signup, no card).
    tmBase: 'https://app.ticketmaster.com/discovery/v2',
    tmKey: null // loaded from storage at boot
  };

  var RATES = __RATES_JSON__;
  var VEHICLES = __VEHICLES_JSON__;

  // All NYC event times are displayed in Eastern, regardless of the visitor's
  // own timezone. A rider in London booking a Broadway show needs the NYC time.
  var ET = 'America/New_York';

  /* ------------------------------------------------------------- utilities */
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var money = function (n) { return '$' + Number(n).toLocaleString('en-US'); };

  // storage that degrades gracefully in sandboxed frames
  var mem = {};
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return mem[k] || null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { mem[k] = v; } }
  };

  function toast(msg) {
    var t = $('#toast');
    if (!t) return;
    $('#toast-msg').textContent = msg;
    t.classList.add('on');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.remove('on'); }, 3400);
  }

  /* ------------------------------------------------------------- analytics */
  // GA4 / GTM-ready. Push to dataLayer; no PII in payloads.
  window.dataLayer = window.dataLayer || [];
  function track(name, params) {
    var p = params || {};
    p.event = name;
    window.dataLayer.push(p);
    if (typeof window.gtag === 'function') window.gtag('event', name, params || {});
  }
  // instrument every CTA
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-track]');
    if (el) track('cta_clicked', { button_text: (el.textContent || '').trim().slice(0, 48), location: el.getAttribute('data-track') });
    var tel = e.target.closest('a[href^="tel:"]');
    if (tel) track('phone_call_clicked', { location: 'link' });
  });

  /* ------------------------------------------------------------ quote calc */
  function rateFor(slug, dest, vehicleId) {
    var r = RATES[slug];
    if (!r) return null;
    var base = dest === 'jfk' ? r.jfk : r.nyc;
    var mkt = dest === 'jfk' ? r.market_jfk : r.market_nyc;
    var v = VEHICLES.filter(function (x) { return x.id === (vehicleId || 'suv'); })[0] || VEHICLES[0];
    var price = Math.round(base * v.multiplier);
    return {
      county: r.name, slug: slug, dest: dest,
      destLabel: dest === 'jfk' ? 'JFK Airport' : 'New York City',
      price: price, base: base, market: mkt,
      save: Math.max(0, mkt - base),
      savePct: Math.round(((mkt - base) / mkt) * 100),
      vehicle: v, drive: r.drive_min + '–' + r.drive_max + ' min'
    };
  }

  /* ---------------------------------------------------------- state (trip) */
  var TRIP = { county: null, dest: null, when: null, vehicle: 'suv', quote: null, ref: null };

  /* ------------------------------------------------------- hero quote form */
  var qForm = $('#quote-form');
  if (qForm) {
    // default the datetime to tomorrow 08:00 (Default Effect — a sensible pre-fill)
    var d = new Date(); d.setDate(d.getDate() + 1); d.setHours(8, 0, 0, 0);
    var pad = function (n) { return String(n).padStart(2, '0'); };
    var el = $('#q-when');
    el.value = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    el.min = new Date().toISOString().slice(0, 16);

    var started = false;
    qForm.addEventListener('input', function () {
      if (!started) { started = true; track('quote_started', { page_location: location.href }); }
    });

    qForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var county = $('#q-county').value;
      var dest = (qForm.querySelector('input[name="q-dest"]:checked') || {}).value;
      var when = $('#q-when').value;
      var bad = false;

      function mark(id, on, msg) {
        var f = $(id), er = $(id + '-err');
        if (f) f.classList.toggle('err', on);
        if (er) { er.classList.toggle('on', on); if (msg) er.textContent = msg; }
        if (on) bad = true;
      }
      mark('#q-county', !county, 'Please choose your pickup county.');
      mark('#q-when', !when, 'Please choose a pickup date and time.');
      if (bad) { var f = $('.ctl.err'); if (f) f.focus(); return; }

      TRIP.county = county; TRIP.dest = dest; TRIP.when = when; TRIP.vehicle = 'suv';
      var q = rateFor(county, dest, 'suv');
      TRIP.quote = q;
      renderQuote(q);
      track('quote_completed', {
        pickup_county: county, dropoff: dest, vehicle_type: 'suv',
        quoted_price: q.price, is_airport: dest === 'jfk' ? 1 : 0,
        airport_code: dest === 'jfk' ? 'JFK' : null
      });
    });
  }

  function renderQuote(q) {
    var box = $('#quote-result');
    if (!box) return;
    $('#qr-price').innerHTML = '<sup>$</sup>' + q.price.toLocaleString('en-US');
    $('#qr-route').textContent = q.county + ' → ' + q.destLabel;
    $('#qr-meta').textContent = 'Executive SUV · up to 6 passengers · ' + q.drive + ' typical drive';
    var sv = $('#qr-save');
    if (q.save > 0) {
      sv.style.display = '';
      $('#qr-save-tx').textContent = 'You save ' + money(q.save) + ' vs. the ' + money(q.market) + ' typical rate';
    } else { sv.style.display = 'none'; }
    box.classList.add('on');
    box.setAttribute('aria-live', 'polite');
    // deep-link so the quote is shareable / ad-targetable
    try { history.replaceState(null, '', '?county=' + q.slug + '&to=' + q.dest + '#quote'); } catch (e) {}
  }

  // Pre-fill from ?county=bergen&to=jfk deep links
  (function () {
    var p = new URLSearchParams(location.search);
    var c = p.get('county'), t = p.get('to');
    if (c && RATES[c] && $('#q-county')) {
      $('#q-county').value = c;
      if (t === 'jfk') { var r = $('#q-dest-jfk'); if (r) r.checked = true; }
    }
  })();

  /* ------------------------------------------------------ rate table jumps */
  $$('[data-book-county]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var slug = a.getAttribute('data-book-county');
      var dest = a.getAttribute('data-book-dest') || 'nyc';
      if ($('#q-county')) {
        $('#q-county').value = slug;
        var r = $(dest === 'jfk' ? '#q-dest-jfk' : '#q-dest-nyc'); if (r) r.checked = true;
        $('#quote-form').dispatchEvent(new Event('submit'));
        document.getElementById('quote').scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  });

  /* ======================================================== BOOKING FLOW */
  var STEP = 1, MAXSTEP = 5;

  function showStep(n) {
    STEP = n;
    $$('.stepv').forEach(function (s) { s.classList.toggle('on', +s.dataset.step === n); });
    $$('.prog-i').forEach(function (p, i) {
      p.classList.toggle('on', i + 1 === n);
      p.classList.toggle('done', i + 1 < n);
    });
    var sh = $('#book-shell');
    if (sh) { var y = sh.getBoundingClientRect().top + window.scrollY - 90; window.scrollTo({ top: y, behavior: 'smooth' }); }
  }

  $$('[data-goto-book]').forEach(function (b) {
    b.addEventListener('click', function (e) {
      e.preventDefault();
      if (!TRIP.quote) {
        // no quote yet — send them to the hero widget instead of an empty flow
        document.getElementById('quote').scrollIntoView({ behavior: 'smooth', block: 'center' });
        var c = $('#q-county'); if (c) c.focus();
        toast('Pick your county first and we will price it instantly');
        return;
      }
      hydrateBooking();
      track('booking_started', { vehicle_type: TRIP.vehicle, price: TRIP.quote.price });
      showStep(1);
    });
  });

  function hydrateBooking() {
    var q = TRIP.quote; if (!q) return;
    $('#b-route').textContent = q.county + ' → ' + q.destLabel;
    var dt = new Date(TRIP.when);
    $('#b-when').textContent = dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) +
      ' at ' + dt.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    // airport-only fields
    $$('[data-airport-only]').forEach(function (n) { n.style.display = q.dest === 'jfk' ? '' : 'none'; });
    // vehicle rows priced off this county's base
    var wrap = $('#b-vehicles'); wrap.innerHTML = '';
    VEHICLES.forEach(function (v, i) {
      var p = Math.round(q.base * v.multiplier);
      var id = 'veh-' + v.id;
      var row = document.createElement('div');
      row.className = 'vrow';
      row.innerHTML =
        '<input type="radio" name="b-vehicle" id="' + id + '" value="' + v.id + '"' + (v.id === TRIP.vehicle ? ' checked' : '') + '>' +
        '<label for="' + id + '">' +
          '<span class="vrow-ic" aria-hidden="true">' + svgCar() + '</span>' +
          '<span class="vrow-tx"><b>' + v.name + (v.recommended ? ' · Recommended' : '') + '</b>' +
          '<span>' + v.examples + ' — up to ' + v.pax + ' passengers, ' + v.bags + ' bags</span></span>' +
          '<span class="vrow-pr"><b>' + money(p) + '</b><span>all-in</span></span>' +
        '</label>';
      wrap.appendChild(row);
    });
    wrap.addEventListener('change', function (e) {
      if (e.target.name !== 'b-vehicle') return;
      TRIP.vehicle = e.target.value;
      TRIP.quote = rateFor(TRIP.county, TRIP.dest, TRIP.vehicle);
      paintSummary();
      track('vehicle_selected', { vehicle_type: TRIP.vehicle, price: TRIP.quote.price });
    });
    paintSummary();
  }

  function paintSummary() {
    var q = TRIP.quote; if (!q) return;
    $$('[data-sum-route]').forEach(function (n) { n.textContent = q.county + ' → ' + q.destLabel; });
    $$('[data-sum-veh]').forEach(function (n) { n.textContent = q.vehicle.name; });
    $$('[data-sum-total]').forEach(function (n) { n.textContent = money(q.price); });
    $$('[data-sum-when]').forEach(function (n) {
      var dt = new Date(TRIP.when);
      n.textContent = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ', ' +
        dt.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    });
  }

  // validation per step — inline, never wipes entered data
  function validate(n) {
    var ok = true;
    var req = $$('.stepv[data-step="' + n + '"] [data-req]');
    req.forEach(function (f) {
      if (f.closest('[data-airport-only]') && f.closest('[data-airport-only]').style.display === 'none') return;
      var bad = !f.value.trim();
      if (!bad && f.type === 'email') bad = !/^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(f.value.trim());
      if (!bad && f.dataset.minlen) bad = f.value.replace(/\D/g, '').length < +f.dataset.minlen;
      f.classList.toggle('err', bad);
      var er = f.parentNode.querySelector('.fld-err');
      if (er) er.classList.toggle('on', bad);
      if (bad && ok) { f.focus(); }
      if (bad) ok = false;
    });
    return ok;
  }

  $$('[data-next]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (!validate(STEP)) return;
      if (STEP === 1) track('booking_details_completed', {
        passenger_count: $('#b-pax') ? $('#b-pax').value : null,
        has_flight: $('#b-flight') && $('#b-flight').value ? 1 : 0
      });
      if (STEP === 3) track('payment_info_entered', { payment_method: 'card' });
      if (STEP === 4) { doPayment(); return; }
      showStep(Math.min(STEP + 1, MAXSTEP));
    });
  });
  $$('[data-back]').forEach(function (b) {
    b.addEventListener('click', function () { showStep(Math.max(STEP - 1, 1)); });
  });

  // card input niceties
  var cc = $('#p-card');
  if (cc) cc.addEventListener('input', function () {
    var v = cc.value.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim();
    cc.value = v;
  });
  var ex = $('#p-exp');
  if (ex) ex.addEventListener('input', function () {
    var v = ex.value.replace(/\D/g, '').slice(0, 4);
    ex.value = v.length > 2 ? v.slice(0, 2) + '/' + v.slice(2) : v;
  });

  function doPayment() {
    var btn = $('#pay-btn');
    btn.disabled = true;
    btn.innerHTML = svgSpin() + ' Authorising…';
    // >>> HOOK: PAYMENTS — real implementation replaces this timeout with
    //     Stripe/Square confirmation, then POSTs to CFG.bookingEndpoint.
    setTimeout(function () {
      TRIP.ref = 'MBC-' + String(Date.now()).slice(-6);
      var q = TRIP.quote;
      $('#c-ref').textContent = TRIP.ref;
      $('#c-route').textContent = q.county + ' → ' + q.destLabel;
      $('#c-veh').textContent = q.vehicle.name;
      $('#c-total').textContent = money(q.price);
      var dt = new Date(TRIP.when);
      $('#c-when').textContent = dt.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }) +
        ' · ' + dt.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      btn.disabled = false;
      btn.innerHTML = 'Pay ' + money(q.price) + ' &amp; confirm booking';
      showStep(5);
      track('booking_completed', {
        booking_id: TRIP.ref, value: q.price, currency: 'USD',
        vehicle_type: TRIP.vehicle, pickup_county: TRIP.county,
        is_airport: TRIP.dest === 'jfk' ? 1 : 0, airport_code: TRIP.dest === 'jfk' ? 'JFK' : null
      });
    }, 1500);
  }

  /* ============================================================= TRACKING */
  var TRACK_ROUTE = [
    [40.8859, -74.0435], [40.8792, -74.0289], [40.8681, -74.0100], [40.8571, -73.9962],
    [40.8501, -73.9490], [40.8371, -73.9470], [40.8203, -73.9520], [40.8010, -73.9620],
    [40.7880, -73.9720], [40.7761, -73.9820], [40.7663, -73.9830], [40.7580, -73.9855]
  ];
  var carMarker = null, seg = 0, tMap = null;

  function initMap() {
    var host = $('#map');
    if (!host || typeof L === 'undefined') {
      if (host) host.outerHTML = '<div class="map-fb">Live map unavailable — the map library could not load in this frame. ' +
        'On your deployed site this shows your driver moving in real time.</div>';
      return;
    }
    tMap = L.map('map', { zoomControl: true, attributionControl: true, scrollWheelZoom: false })
      .setView([40.8200, -74.0000], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '&copy; OpenStreetMap'
    }).addTo(tMap);

    L.polyline(TRACK_ROUTE, { color: '#C9A961', weight: 4, opacity: .85 }).addTo(tMap);
    L.marker(TRACK_ROUTE[0], {
      icon: L.divIcon({ className: '', html: '<div class="pin-mk">A</div>', iconSize: [26, 26], iconAnchor: [13, 13] })
    }).addTo(tMap).bindPopup('Pickup — Hackensack, NJ');
    L.marker(TRACK_ROUTE[TRACK_ROUTE.length - 1], {
      icon: L.divIcon({ className: '', html: '<div class="pin-mk">B</div>', iconSize: [26, 26], iconAnchor: [13, 13] })
    }).addTo(tMap).bindPopup('Drop-off — Midtown Manhattan');

    carMarker = L.marker(TRACK_ROUTE[0], {
      icon: L.divIcon({ className: '', html: '<div class="car-mk">' + svgCarSm() + '</div>', iconSize: [38, 38], iconAnchor: [19, 19] })
    }).addTo(tMap);
    tMap.fitBounds(L.polyline(TRACK_ROUTE).getBounds(), { padding: [34, 34] });

    // >>> HOOK: DRIVER GPS — replace this interval with polling CFG.gpsEndpoint
    //     (or a websocket) and feed real lat/lng into carMarker.setLatLng().
    setInterval(function () {
      seg = (seg + 1) % TRACK_ROUTE.length;
      carMarker.setLatLng(TRACK_ROUTE[seg]);
      var left = TRACK_ROUTE.length - 1 - seg;
      var mins = Math.max(1, Math.round(left * 2.4));
      var e = $('#eta-min'); if (e) e.textContent = mins;
      var pr = $('#eta-prog'); if (pr) pr.textContent = Math.round((seg / (TRACK_ROUTE.length - 1)) * 100) + '%';
    }, 3000);
  }

  $$('[data-goto-track]').forEach(function (b) {
    b.addEventListener('click', function () {
      track('driver_tracking_viewed', { booking_id: TRIP.ref || 'demo' });
    });
  });

  /* ================================================================= CHAT */
  var CHAT_REPLIES = [
    "I'm about 8 minutes out — just came off Route 4. Black Suburban, plate M-4821.",
    "No problem at all, I'll wait. Take your time.",
    "I'm at the arrivals level now, pulled over by the second crosswalk. I have a name board.",
    "Traffic is light this morning, we're in good shape for your flight.",
    "Understood — I'll meet you inside at baggage claim instead.",
    "Water's in the console and the cabin is cooled down for you."
  ];
  var rIdx = 0;

  function addMsg(text, who) {
    var log = $('#chat-log'); if (!log) return;
    var m = document.createElement('div');
    m.className = 'msg ' + who;
    var t = new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    m.innerHTML = escapeHtml(text) + '<time>' + t + (who === 'me' ? ' · Delivered' : '') + '</time>';
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
  }

  function driverReply() {
    var log = $('#chat-log'); if (!log) return;
    var ty = document.createElement('div');
    ty.className = 'typing'; ty.id = 'typing';
    ty.innerHTML = '<i></i><i></i><i></i>';
    log.appendChild(ty); log.scrollTop = log.scrollHeight;
    setTimeout(function () {
      var t = $('#typing'); if (t) t.remove();
      addMsg(CHAT_REPLIES[rIdx % CHAT_REPLIES.length], 'them');
      rIdx++;
    }, 1500 + Math.random() * 1100);
  }

  function sendMsg(text) {
    if (!text.trim()) return;
    addMsg(text.trim(), 'me');
    track('driver_message_sent', { booking_id: TRIP.ref || 'demo' });
    // >>> HOOK: SMS — POST {to: driverPhone, body: text} to CFG.smsEndpoint,
    //     which relays via Twilio. Inbound replies arrive on your Twilio
    //     webhook and stream back here (websocket/SSE). See guide §2.
    driverReply();
  }

  var chatForm = $('#chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var i = $('#chat-input');
      sendMsg(i.value); i.value = ''; i.focus();
    });
    $$('.quick button').forEach(function (b) {
      b.addEventListener('click', function () { sendMsg(b.textContent); });
    });
  }

  /* =============================================== LIVE NYC EVENTS FEED */
  /* No hardcoded events anywhere. Two real sources:
     1. MLB Stats API  — keyless, CORS-open. Yankees home games. Live today.
     2. Ticketmaster Discovery — free key required for MSG / Barclays /
        Broadway / concerts. Venue IDs are resolved at RUNTIME so nothing
        is baked in and the feed self-corrects if TM changes an ID.        */

  var FEED = { yankees: [], msg: [], barclays: [], broadway: [], concerts: [] };
  var venueCache = {};
  var curTab = 'yankees';

  function ymd(dt) { return dt.toISOString().slice(0, 10); }

  function fetchJSON(url) {
    return fetch(url, { headers: { Accept: 'application/json' } }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  /* ---- source 1: MLB Stats API (keyless, verified live) ---- */
  function loadYankees() {
    var from = new Date(), to = new Date();
    to.setMonth(to.getMonth() + 3);
    var url = CFG.mlbBase + '/schedule?sportId=1&teamId=' + CFG.yankeesTeamId +
      '&startDate=' + ymd(from) + '&endDate=' + ymd(to) + '&hydrate=venue,team';
    return fetchJSON(url).then(function (d) {
      var out = [];
      (d.dates || []).forEach(function (day) {
        (day.games || []).forEach(function (g) {
          var v = (g.venue || {}).name || '';
          if (v.indexOf('Yankee Stadium') === -1) return; // home games only
          out.push({
            when: new Date(g.gameDate),
            title: ((g.teams.away.team.name) || 'TBD') + ' at New York Yankees',
            venue: 'Yankee Stadium, Bronx',
            meta: 'MLB'
          });
        });
      });
      FEED.yankees = out;
      return out;
    });
  }

  /* ---- source 2: Ticketmaster Discovery (free key) ---- */
  function tmVenueId(keyword) {
    if (venueCache[keyword]) return Promise.resolve(venueCache[keyword]);
    var url = CFG.tmBase + '/venues.json?keyword=' + encodeURIComponent(keyword) +
      '&stateCode=NY&size=5&apikey=' + CFG.tmKey;
    return fetchJSON(url).then(function (d) {
      var v = ((d._embedded || {}).venues || [])[0];
      if (!v) throw new Error('venue not found: ' + keyword);
      venueCache[keyword] = v.id;
      return v.id;
    });
  }

  function tmMap(d) {
    return (((d._embedded || {}).events) || []).map(function (e) {
      var dt = ((e.dates || {}).start || {});
      var ven = (((e._embedded || {}).venues) || [])[0] || {};
      return {
        when: new Date(dt.dateTime || (dt.localDate + 'T19:00:00')),
        title: e.name,
        venue: (ven.name || '') + (ven.city ? ', ' + ven.city.name : ''),
        meta: ((e.classifications || [])[0] || {}).genre ? e.classifications[0].genre.name : 'Event',
        url: e.url
      };
    });
  }

  function tmByVenue(keyword) {
    return tmVenueId(keyword).then(function (id) {
      return fetchJSON(CFG.tmBase + '/events.json?venueId=' + id +
        '&sort=date,asc&size=14&apikey=' + CFG.tmKey).then(tmMap);
    });
  }

  function tmBySegment(segment, city) {
    return fetchJSON(CFG.tmBase + '/events.json?segmentName=' + encodeURIComponent(segment) +
      '&city=' + encodeURIComponent(city || 'New York') +
      '&sort=date,asc&size=14&apikey=' + CFG.tmKey).then(tmMap);
  }

  function loadTicketmaster() {
    if (!CFG.tmKey) return Promise.resolve(false);
    return Promise.all([
      tmByVenue('Madison Square Garden').then(function (r) { FEED.msg = r; }).catch(function () {}),
      tmByVenue('Barclays Center').then(function (r) { FEED.barclays = r; }).catch(function () {}),
      tmBySegment('Arts & Theatre').then(function (r) { FEED.broadway = r; }).catch(function () {}),
      tmBySegment('Music').then(function (r) { FEED.concerts = r; }).catch(function () {})
    ]).then(function () { return true; });
  }

  function renderEvents(tab) {
    curTab = tab;
    var list = $('#ev-list'); if (!list) return;
    $$('.tab').forEach(function (t) { t.classList.toggle('on', t.dataset.tab === tab); });

    var items = (FEED[tab] || []).slice().sort(function (a, b) { return a.when - b.when; }).slice(0, 12);

    if (!items.length) {
      var needsKey = tab !== 'yankees' && !CFG.tmKey;
      list.innerHTML = '<div class="ev-empty">' + (needsKey
        ? '<b>Live feed not connected yet.</b><br>Add a free Ticketmaster API key below and this fills with real ' +
          'listings for Madison Square Garden, Barclays Center, Broadway and NYC concerts.'
        : 'No upcoming listings returned by the live feed for this venue right now.') + '</div>';
      return;
    }

    list.innerHTML = items.map(function (e) {
      var dt = e.when;
      // Always render in Eastern time. These are NYC events — a visitor booking
      // from London or Los Angeles must see the local NYC start time, not theirs.
      var day = dt.toLocaleDateString('en-US', { day: 'numeric', timeZone: ET });
      var mon = dt.toLocaleDateString('en-US', { month: 'short', timeZone: ET }).toUpperCase();
      var time = dt.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: ET }) + ' ET';
      var wd = dt.toLocaleDateString('en-US', { weekday: 'short', timeZone: ET });
      return '<article class="ev">' +
        '<div class="ev-dt" aria-hidden="true"><b>' + day + '</b><span>' + mon + '</span></div>' +
        '<div class="ev-tx"><b>' + escapeHtml(e.title) + '</b>' +
          '<span>' + wd + ' ' + time + ' <i>•</i> ' + escapeHtml(e.venue) +
          (e.meta ? ' <i>•</i> ' + escapeHtml(e.meta) : '') + '</span></div>' +
        '<div class="ev-cta"><button class="btn btn-gold" data-ev-book="' + dt.toISOString() + '">' +
          'Book an SUV</button></div>' +
      '</article>';
    }).join('');

    $$('[data-ev-book]').forEach(function (b) {
      b.addEventListener('click', function () {
        var iso = b.getAttribute('data-ev-book');
        track('event_ride_quote_requested', { venue_name: curTab, event_date: iso });

        // Send it through the departure planner rather than guessing a fixed offset.
        // Drive time ranges from 15 min (Hudson) to 190 (Cape May), so "two hours
        // before" is wrong for most of the state.
        var sel = $('#plan-event');
        if (sel) {
          planMode('event');
          var want = curTab + '|' + iso;
          var found = Array.prototype.some.call(sel.options, function (o) {
            if (o.value === want) { sel.value = want; return true; }
            return false;
          });
          if (!found) fillPlanEvents(), sel.value = want;
          var pc = $('#plan-county'), qc2 = $('#q-county');
          if (pc && qc2 && qc2.value) pc.value = qc2.value;
          document.getElementById('plan').scrollIntoView({ behavior: 'smooth', block: 'center' });
          if (pc && pc.value) { runPlan(); }
          else { if (pc) pc.focus(); toast('Pick your county and we will tell you when to leave'); }
        }
      });
    });
  }

  function setCounts() {
    $$('.tab').forEach(function (t) {
      var n = (FEED[t.dataset.tab] || []).length;
      var s = t.querySelector('.n');
      if (s) s.textContent = n ? n : '';
    });
  }

  function stampUpdated() {
    var u = $('#ev-updated');
    if (u) u.textContent = new Date().toLocaleTimeString('en-US',
      { hour: 'numeric', minute: '2-digit', timeZone: ET }) + ' ET';
  }

  function bootEvents() {
    var list = $('#ev-list');
    if (!list) return;
    CFG.tmKey = store.get('mbc_tm_key') || null;
    if (CFG.tmKey) showConnected();
    list.innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel"></div>';

    Promise.all([
      loadYankees().catch(function (e) { console.warn('MLB feed failed', e); }),
      loadTicketmaster().catch(function (e) { console.warn('TM feed failed', e); })
    ]).then(function () {
      setCounts();
      // land on a tab that actually has data
      var first = ['yankees', 'msg', 'barclays', 'broadway', 'concerts'].filter(function (k) { return FEED[k].length; })[0];
      renderEvents(first || 'yankees');
      fillPlanEvents();
      stampUpdated();
      track('events_calendar_viewed', { venue_name: first || 'yankees' });
    });

    $$('.tab').forEach(function (t) {
      t.addEventListener('click', function () { renderEvents(t.dataset.tab); });
    });

    // refresh every 10 minutes so listings stay current
    setInterval(function () {
      loadYankees().catch(function () {});
      loadTicketmaster().catch(function () {});
      setTimeout(function () { setCounts(); renderEvents(curTab); fillPlanEvents(); stampUpdated(); }, 2500);
    }, 600000);
  }

  function showConnected() {
    var c = $('#conn-form'), o = $('#conn-ok');
    if (c) c.style.display = 'none';
    if (o) o.style.display = 'flex';
  }

  var connForm = $('#conn-form');
  if (connForm) {
    connForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var k = $('#conn-key').value.trim();
      if (!k) return;
      CFG.tmKey = k; store.set('mbc_tm_key', k);
      showConnected();
      toast('Connecting live feed…');
      loadTicketmaster().then(function () {
        setCounts(); renderEvents(curTab); fillPlanEvents(); stampUpdated();
        var n = FEED.msg.length + FEED.barclays.length + FEED.broadway.length + FEED.concerts.length;
        toast(n ? 'Live feed connected — ' + n + ' events loaded' : 'Key accepted but no events returned');
      }).catch(function () { toast('That key was rejected by Ticketmaster'); });
    });
  }

  /* ====================================================== DEPARTURE PLANNER
     Works out when the car should collect you so you arrive on time, using:
       - the real upper-bound drive time for YOUR county (15 min from Hudson,
         190 from Cape May — a flat "2 hours before" is useless across that range)
       - a traffic multiplier for the actual day and hour of travel
       - the arrival buffer the destination genuinely needs
     Deliberately uses the SLOWER end of each drive-time range. Being 20 minutes
     early to a terminal costs nothing; being 10 late costs the flight.          */

  var VENUE_PROFILE = {
    arena:   { label: 'Stadium or arena',   arriveBefore: 45,
               why: 'bag check, concourse queues and the walk to your seats' },
    theatre: { label: 'Broadway or theatre', arriveBefore: 30,
               why: 'ticket scan and being seated before curtain' },
    concert: { label: 'Concert venue',      arriveBefore: 45,
               why: 'security screening and finding your section' }
  };

  function venueProfileFor(tab) {
    if (tab === 'broadway') return 'theatre';
    if (tab === 'concerts') return 'concert';
    return 'arena';
  }

  /* Traffic multipliers for the NJ→NYC crossings. These reflect the well-known
     peaks on the GWB / Lincoln / Holland approaches. Tune from your own trip data
     once you have it — see INTEGRATION-GUIDE.md §9. */
  function trafficFactor(dt, dest) {
    var day = dt.getDay(), h = dt.getHours() + dt.getMinutes() / 60;
    var weekday = day >= 1 && day <= 5;
    var f = 1.0, note = 'normal conditions';
    if (weekday && h >= 6.5 && h < 9.5)        { f = 1.45; note = 'weekday morning peak'; }
    else if (weekday && h >= 15.5 && h < 19)   { f = (day === 5 ? 1.70 : 1.50);
                                                 note = (day === 5 ? 'Friday evening peak — the worst crossing of the week'
                                                                   : 'weekday evening peak'); }
    else if (!weekday && h >= 11 && h < 18)    { f = 1.15; note = 'weekend midday traffic'; }
    else if (h >= 22 || h < 5)                 { f = 0.85; note = 'overnight, roads clear'; }
    if (dest === 'jfk') { f *= 1.10; note += ' · JFK adds cross-borough time'; }
    return { f: f, note: note };
  }

  function suggestDeparture(slug, arriveAt, mode, opts) {
    var r = RATES[slug];
    if (!r || !arriveAt || isNaN(arriveAt.getTime())) return null;
    var driveBase = r.drive_max;                       // slower end of the range, on purpose
    var buffer, bufferLabel, why;
    if (mode === 'flight') {
      buffer = opts.intl ? 180 : 120;
      bufferLabel = (opts.intl ? 'International' : 'Domestic') + ' check-in and security';
      why = opts.intl ? 'airlines advise three hours for international departures'
                      : 'airlines advise two hours for domestic departures';
    } else {
      var p = VENUE_PROFILE[opts.venue] || VENUE_PROFILE.arena;
      buffer = p.arriveBefore;
      bufferLabel = 'Arrive before start';
      why = p.why;
    }
    var cushion = mode === 'flight' ? 20 : 15;

    // The traffic you hit is the traffic during the DRIVE, not at the arrival
    // instant. A 7:30pm Friday game from Cape May departs mid-afternoon and sits
    // in the Friday peak the whole way. So converge: guess a departure, score the
    // midpoint of that drive window, and re-solve. Three passes is ample.
    var t = trafficFactor(arriveAt, opts.dest), driveAdj = Math.round(driveBase * t.f);
    for (var i = 0; i < 3; i++) {
      var departGuess = arriveAt.getTime() - (driveAdj + buffer + cushion) * 60000;
      var mid = new Date(departGuess + (driveAdj / 2) * 60000);
      var t2 = trafficFactor(mid, opts.dest);
      var next = Math.round(driveBase * t2.f);
      if (next === driveAdj) { t = t2; break; }
      t = t2; driveAdj = next;
    }

    var total = driveAdj + buffer + cushion;
    return {
      leave: new Date(arriveAt.getTime() - total * 60000),
      arriveAt: arriveAt, driveBase: driveBase, driveAdj: driveAdj,
      traffic: t, buffer: buffer, bufferLabel: bufferLabel, why: why,
      cushion: cushion, total: total, county: r.name, mode: mode
    };
  }

  function fmtET(dt, withDate) {
    var o = { hour: 'numeric', minute: '2-digit', timeZone: ET };
    if (withDate) { o.weekday = 'short'; o.month = 'short'; o.day = 'numeric'; }
    return dt.toLocaleString('en-US', o) + ' ET';
  }
  function mins(n) {
    if (n < 60) return n + ' min';
    var h = Math.floor(n / 60), m = n % 60;
    return h + 'h' + (m ? ' ' + m + 'm' : '');
  }

  var PLAN = { mode: 'flight', result: null };

  function planMode(m) {
    PLAN.mode = m;
    $$('[data-plan-pane]').forEach(function (p) {
      p.style.display = p.getAttribute('data-plan-pane') === m ? '' : 'none';
    });
    $$('[data-plan-mode]').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-plan-mode') === m);
      b.setAttribute('aria-selected', b.getAttribute('data-plan-mode') === m ? 'true' : 'false');
    });
    var r = $('#plan-result'); if (r) r.classList.remove('on');
  }

  /* Fills the event picker straight from the live feed — no separate data source */
  function fillPlanEvents() {
    var sel = $('#plan-event'); if (!sel) return;
    var groups = [
      ['yankees', 'Yankee Stadium'], ['msg', 'Madison Square Garden'],
      ['barclays', 'Barclays Center'], ['broadway', 'Broadway & theatre'], ['concerts', 'Concerts']
    ];
    var html = '<option value="">Choose an event…</option>';
    var any = false;
    groups.forEach(function (g) {
      var items = (FEED[g[0]] || []).slice().sort(function (a, b) { return a.when - b.when; }).slice(0, 12);
      if (!items.length) return;
      any = true;
      html += '<optgroup label="' + g[1] + '">';
      items.forEach(function (e, i) {
        html += '<option value="' + g[0] + '|' + e.when.toISOString() + '">' +
          escapeHtml(e.when.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: ET })) +
          ' — ' + escapeHtml(e.title.slice(0, 58)) + '</option>';
      });
      html += '</optgroup>';
    });
    sel.innerHTML = html;
    var hint = $('#plan-event-hint');
    if (hint) hint.textContent = any
      ? 'Pulled live from the events feed above.'
      : 'Connect the Ticketmaster feed above to list MSG, Barclays and Broadway events here. Yankees games load automatically.';
  }

  function runPlan() {
    var slug = $('#plan-county').value;
    if (!slug) { $('#plan-county').classList.add('err'); return; }
    $('#plan-county').classList.remove('err');

    var arriveAt, opts = {}, mode = PLAN.mode;

    if (mode === 'flight') {
      var v = $('#plan-flight-time').value;
      if (!v) { $('#plan-flight-time').classList.add('err'); return; }
      $('#plan-flight-time').classList.remove('err');
      arriveAt = new Date(v);
      opts.dest = (document.querySelector('input[name="plan-airport"]:checked') || {}).value || 'jfk';
      opts.intl = $('#plan-intl').checked;
    } else {
      var val = $('#plan-event').value;
      if (!val) { $('#plan-event').classList.add('err'); return; }
      $('#plan-event').classList.remove('err');
      var parts = val.split('|');
      arriveAt = new Date(parts[1]);
      opts.dest = 'nyc';                       // every venue sits in the NYC flat tier
      opts.venue = venueProfileFor(parts[0]);
    }

    var res = suggestDeparture(slug, arriveAt, mode, opts);
    if (!res) return;
    PLAN.result = res;
    PLAN.opts = opts;

    $('#plan-leave').textContent = fmtET(res.leave, true);
    $('#plan-headline').textContent = mode === 'flight'
      ? 'To make a ' + fmtET(res.arriveAt) + ' departure'
      : 'To make a ' + fmtET(res.arriveAt) + ' start';

    // Every value below adds up to the total — no mental arithmetic required.
    var delta = res.driveAdj - res.driveBase;
    var driveDetail = mins(res.driveBase) + ' typical, ' +
      (delta === 0 ? 'no traffic adjustment today' :
        (delta > 0 ? '+' + mins(delta) : '−' + mins(-delta)) +
        ' at ×' + res.traffic.f.toFixed(2) + ' for ' + res.traffic.note);

    $('#plan-break').innerHTML =
      row('Drive from ' + res.county, driveDetail, mins(res.driveAdj)) +
      row(res.bufferLabel, res.why, mins(res.buffer)) +
      row('Safety cushion', 'so a bad crossing does not cost you the trip', mins(res.cushion)) +
      '<div class="pb-row pb-tot"><div><b>Leave this much earlier</b></div><b>' + mins(res.total) + '</b></div>';

    $('#plan-result').classList.add('on');
    var pe = $('#plan-empty'); if (pe) pe.style.display = 'none';
    track('departure_planned', {
      mode: mode, pickup_county: slug, total_minutes: res.total,
      traffic_factor: +res.traffic.f.toFixed(2)
    });
  }

  function row(label, sub, val) {
    if (val === undefined) { val = sub; sub = null; }
    return '<div class="pb-row"><div><b>' + label + '</b>' +
      (sub ? '<span>' + sub + '</span>' : '') + '</div><span class="pb-v">' +
      (val || '') + '</span></div>';
  }

  var planForm = $('#plan-form');
  if (planForm) {
    planForm.addEventListener('submit', function (e) { e.preventDefault(); runPlan(); });
    $$('[data-plan-mode]').forEach(function (b) {
      b.addEventListener('click', function () { planMode(b.getAttribute('data-plan-mode')); });
    });
    // keep the planner's county in step with the hero quote, both directions
    var qc = $('#q-county'), pc = $('#plan-county');
    if (qc && pc) {
      qc.addEventListener('change', function () { if (!pc.value) pc.value = qc.value; });
      pc.addEventListener('change', function () { if (!qc.value) qc.value = pc.value; });
    }
    // apply the recommendation to the booking flow
    $('#plan-apply').addEventListener('click', function () {
      if (!PLAN.result) return;
      var slug = $('#plan-county').value;
      if (qc) qc.value = slug;
      var destRadio = $(PLAN.opts.dest === 'jfk' ? '#q-dest-jfk' : '#q-dest-nyc');
      if (destRadio) destRadio.checked = true;
      var el = $('#q-when');
      if (el) el.value = etLocalInputValue(PLAN.result.leave);
      $('#quote-form').dispatchEvent(new Event('submit'));
      document.getElementById('quote').scrollIntoView({ behavior: 'smooth', block: 'center' });
      toast('Pickup set for ' + fmtET(PLAN.result.leave) + ' — priced below');
    });
    var pf = $('#plan-flight-time');
    if (pf) {
      var d0 = new Date(); d0.setDate(d0.getDate() + 1); d0.setHours(18, 30, 0, 0);
      var pad2 = function (n) { return String(n).padStart(2, '0'); };
      pf.value = d0.getFullYear() + '-' + pad2(d0.getMonth() + 1) + '-' + pad2(d0.getDate()) + 'T18:30';
      pf.min = new Date().toISOString().slice(0, 16);
    }
  }

  /* Inline recommendation inside booking step 1 when a flight time is given */
  var bft = $('#b-flight-time');
  if (bft) bft.addEventListener('change', function () {
    var box = $('#b-flight-rec');
    if (!bft.value || !TRIP.county) { box.style.display = 'none'; return; }
    var res = suggestDeparture(TRIP.county, new Date(bft.value), 'flight',
      { dest: TRIP.dest, intl: $('#b-intl') && $('#b-intl').checked });
    if (!res) { box.style.display = 'none'; return; }
    box.style.display = '';
    $('#b-flight-rec-tx').innerHTML =
      'For that departure we recommend collecting you at <b>' + fmtET(res.leave, true) + '</b> — ' +
      mins(res.total) + ' earlier (' + mins(res.driveAdj) + ' drive in ' + res.traffic.note +
      ', plus ' + mins(res.buffer) + ' at the terminal and a ' + mins(res.cushion) + ' cushion).';
    $('#b-flight-apply').onclick = function () {
      TRIP.when = etLocalInputValue(res.leave);
      var el = $('#q-when'); if (el) el.value = TRIP.when;
      hydrateBooking();
      toast('Pickup moved to ' + fmtET(res.leave));
    };
  });

  /* ============================================================ waitlist */
  var wl = $('#waitlist');
  if (wl) wl.addEventListener('submit', function (e) {
    e.preventDefault();
    var i = $('#wl-email');
    if (!/^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(i.value.trim())) { i.classList.add('err'); return; }
    i.classList.remove('err');
    track('form_submitted', { form_type: 'nj_waitlist' });
    wl.innerHTML = '<div class="conn-ok">' + svgCheck() + ' You are on the list. We will email you when New Jersey transfers open.</div>';
  });

  /* ======================================================== exit popup */
  (function () {
    var pop = $('#pop'); if (!pop) return;
    var KEY = 'mbc_pop_seen';
    if (store.get(KEY)) return;
    var shown = false, armed = false;

    setTimeout(function () { armed = true; }, 30000); // never before 30s

    function open() {
      if (shown || !armed) return;
      // never interrupt someone mid-booking
      if (STEP > 1 || TRIP.ref) return;
      shown = true;
      store.set(KEY, '1');
      pop.classList.add('on');
      $('.pop-x', pop).focus();
      track('popup_shown', { popup_type: 'exit_intent_quote' });
    }
    function close() { pop.classList.remove('on'); }

    document.addEventListener('mouseout', function (e) {
      if (!e.relatedTarget && e.clientY <= 4) open();
    });
    // mobile has no exit intent — use fast scroll-up instead
    var lastY = window.scrollY;
    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      if (lastY - y > 190 && y > 700) open();
      lastY = y;
    }, { passive: true });

    $$('[data-pop-close]', pop).forEach(function (b) { b.addEventListener('click', close); });
    pop.addEventListener('click', function (e) { if (e.target === pop) close(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    $('#pop-cta').addEventListener('click', function () {
      close();
      document.getElementById('quote').scrollIntoView({ behavior: 'smooth', block: 'center' });
      var c = $('#q-county'); if (c) setTimeout(function () { c.focus(); }, 500);
    });
  })();

  /* ============================================================ nav / ui */
  var burger = $('#burger');
  if (burger) burger.addEventListener('click', function () {
    var n = $('#nav-links');
    var open = n.classList.toggle('open');
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  $$('#nav-links a').forEach(function (a) {
    a.addEventListener('click', function () { $('#nav-links').classList.remove('open'); });
  });

  // county filter on the rate table
  var rf = $('#rate-filter');
  if (rf) rf.addEventListener('input', function () {
    var q = rf.value.trim().toLowerCase();
    $$('#rates-body tr[data-county]').forEach(function (tr) {
      var hay = tr.getAttribute('data-search');
      tr.style.display = !q || hay.indexOf(q) > -1 ? '' : 'none';
    });
    $$('#rates-body tr.rr').forEach(function (tr) {
      var any = false, n = tr.nextElementSibling;
      while (n && !n.classList.contains('rr')) { if (n.style.display !== 'none') any = true; n = n.nextElementSibling; }
      tr.style.display = any ? '' : 'none';
    });
  });

  /* ------------------------------------------------------------- helpers */
  // Formats an instant as a "YYYY-MM-DDTHH:MM" wall-clock string in Eastern time,
  // which is what <input type="datetime-local"> expects for a New Jersey pickup.
  function etLocalInputValue(dt) {
    var p = {};
    new Intl.DateTimeFormat('en-US', {
      timeZone: ET, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false
    }).formatToParts(dt).forEach(function (x) { p[x.type] = x.value; });
    var hh = p.hour === '24' ? '00' : p.hour;
    return p.year + '-' + p.month + '-' + p.day + 'T' + hh + ':' + p.minute;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function svgCar() { return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M5 17h14M3 13l1.6-5A2 2 0 016.5 6.5h11a2 2 0 011.9 1.5L21 13v4H3v-4z"/><circle cx="7.5" cy="17" r="1.6"/><circle cx="16.5" cy="17" r="1.6"/></svg>'; }
  function svgCarSm() { return '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M5 17h14M3 13l1.6-5A2 2 0 016.5 6.5h11a2 2 0 011.9 1.5L21 13v4H3v-4z"/></svg>'; }
  function svgCheck() { return '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>'; }
  function svgSpin() { return '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 3a9 9 0 109 9" opacity=".9"><animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur=".8s" repeatCount="indefinite"/></path></svg>'; }

  /* ---------------------------------------------------------------- boot */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { initMap(); bootEvents(); });
  } else { initMap(); bootEvents(); }
})();
"""
