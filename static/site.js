/* Marketing site behaviour.
   - The server owns every price: the browser sends the journey, receives a quote id,
     and returns that id when reserving.
   - Analytics: GA4-recommended ecommerce events in window.dataLayer (read by Google Tag
     Manager when installed) plus first-party attribution sent with quotes and reservations.
     The purchase itself is recorded server-side when Stripe confirms payment. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var PAGE = JSON.parse(($('#page-config') || {}).textContent || '{}');
  var ET = 'America/New_York';
  var S = { service: 'transfer', quote: null, trip: null, cfg: null };

  /* ============================================================ analytics */
  var store = {
    get: function (k, ses) { try { return JSON.parse((ses ? sessionStorage : localStorage).getItem(k)); } catch (e) { return null; } },
    set: function (k, v, ses) { try { (ses ? sessionStorage : localStorage).setItem(k, JSON.stringify(v)); } catch (e) {} }
  };
  window.dataLayer = window.dataLayer || [];
  function track(event, params) {
    var p = params || {}; p.event = event; window.dataLayer.push(p);
    // Direct GA4 (no Tag Manager) only understands gtag() calls, so mirror the event.
    if (window.__mrDirectGA && typeof window.gtag === 'function') {
      var g = {}; for (var k in p) { if (k !== 'event') g[k] = k === 'ecommerce' && p[k] ? undefined : p[k]; }
      if (p.ecommerce) { g.currency = p.ecommerce.currency; g.value = p.ecommerce.value; g.items = p.ecommerce.items; }
      window.gtag('event', event, g);
    }
  }
  function trackEcommerce(event, q, extra) {
    window.dataLayer.push({ ecommerce: null });
    var item = { item_id: q.route.service === 'hourly' ? 'hourly-' + q.route.hours + 'h' : S.trip.origin + '-' + S.trip.destination,
      item_name: routeLabel(q), item_category: q.route.service, price: (q.amount_cents || 0) / 100, quantity: 1 };
    var p = { ecommerce: { currency: 'USD', value: (q.amount_cents || 0) / 100, items: [item] } };
    for (var k in extra || {}) p[k] = extra[k];
    track(event, p);
  }
  var session = store.get('mr_session', true) || { id: (Math.random().toString(36).slice(2) + Date.now().toString(36)).slice(0, 24) };
  store.set('mr_session', session, true);

  /* Attribution: last non-direct touch wins; first visit date is kept. No personal data. */
  var KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'gclid', 'gbraid', 'wbraid', 'fbclid', 'msclkid'];
  (function captureAttribution() {
    var qs = new URLSearchParams(location.search), touch = {}, any = false;
    KEYS.forEach(function (k) { if (qs.get(k)) { touch[k] = qs.get(k).slice(0, 200); any = true; } });
    var ref = document.referrer && document.referrer.indexOf(location.host) < 0 ? document.referrer.split('?')[0] : '';
    if (!any && ref) { touch.referrer = ref; any = true; }
    var saved = store.get('mr_attr') || {};
    if (any) { touch.landing_page = location.pathname; saved = touch; }
    saved.first_seen = saved.first_seen || new Date().toISOString().slice(0, 10);
    store.set('mr_attr', saved);
  })();
  function attribution() {
    var a = store.get('mr_attr') || {};
    var ga = (document.cookie.match(/(?:^|; )_ga=GA\d\.\d\.(\d+\.\d+)/) || [])[1];
    if (ga) a.ga_client_id = ga;
    return a;
  }
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-track]');
    if (el) track('cta_click', { cta_location: el.getAttribute('data-track') });
    var tel = e.target.closest('a[href^="tel:"]'); if (tel) track('phone_click');
    var mail = e.target.closest('a[href^="mailto:"]'); if (mail) track('email_click');
  });

  /* ================================================================== api */
  function api(method, url, body) {
    return fetch(url, { method: method, headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: body ? JSON.stringify(body) : undefined, credentials: 'omit' }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) {
          var d = j.detail;
          var err = new Error(j.message || (Array.isArray(d) ? 'Please check the highlighted details.' : d) ||
            'Something went wrong. Please try again.');
          err.code = j.error; throw err;
        }
        return j;
      });
    });
  }
  api('GET', '/api/config').then(function (c) { S.cfg = c; }).catch(function () {});

  /* ================================================================ dates */
  function etParts(d) {
    var p = {};
    new Intl.DateTimeFormat('en-US', { timeZone: ET, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(d).forEach(function (x) { p[x.type] = x.value; });
    return p;
  }
  function etInput(d) { var p = etParts(d); return p.year + '-' + p.month + '-' + p.day + 'T' + (p.hour === '24' ? '00' : p.hour) + ':' + p.minute; }
  function fmtWhen(iso) {
    return new Date(iso).toLocaleString('en-US', { timeZone: ET, weekday: 'short', month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit' }) + ' ET';
  }
  function money(c) { return '$' + (c / 100).toLocaleString('en-US', { minimumFractionDigits: c % 100 ? 2 : 0 }); }
  function routeLabel(q) {
    return q.route.service === 'hourly' ? q.route.origin + ' · ' + q.route.hours + ' hours'
      : q.route.origin + ' → ' + q.route.destination;
  }

  var when = $('#q-when');
  if (when) {
    var p = etParts(new Date(Date.now() + 24 * 3600e3));
    when.value = p.year + '-' + p.month + '-' + p.day + 'T09:00';
    when.min = etInput(new Date());
  }

  /* ============================================================ steppers */
  $$('[data-stepper]').forEach(function (s) {
    var out = $('output', s);
    $$('.step-b', s).forEach(function (b) {
      b.addEventListener('click', function () {
        out.textContent = Math.max(+out.dataset.min, Math.min(+out.dataset.max, +out.textContent + +b.dataset.step));
        paintFit();
      });
    });
  });

  /* Live luggage fit: large bag = 2 units, carry-on = 1; space grows as fewer seats are needed. */
  function capacityFor(guests) {
    var caps = (PAGE.luggageCapacity || []).slice().sort(function (a, b) { return a[0] - b[0]; });
    for (var i = 0; i < caps.length; i++) if (guests <= caps[i][0]) return caps[i][1];
    return 0;
  }
  function paintFit() {
    var bar = $('#q-fit-bar'); if (!bar) return;
    var guests = +$('#q-pax').textContent, used = 2 * +$('#q-bags').textContent + +$('#q-carry').textContent;
    var cap = capacityFor(guests), pct = cap ? Math.min(100, Math.round(100 * used / cap)) : 100, ok = used <= cap;
    bar.style.width = Math.max(4, pct) + '%';
    $('#q-fit').classList.toggle('snug', !ok);
    $('#q-fit-tx').textContent = ok ? (pct > 85 ? 'Fits — a full load' : 'Fits comfortably')
      : 'More than our guide — we will confirm with you before payment';
  }
  paintFit();
  var fitHelp = $('#q-fit-help');
  if (fitHelp) fitHelp.addEventListener('click', function () {
    var g = $('#q-guide'); g.hidden = !g.hidden; fitHelp.setAttribute('aria-expanded', !g.hidden);
    if (!g.hidden) track('luggage_guide_opened');
  });

  /* ======================================================== service tabs */
  function setService(svc) {
    S.service = svc;
    $$('.mt').forEach(function (t) { var on = t.dataset.service === svc; t.classList.toggle('on', on); t.setAttribute('aria-selected', on); });
    $$('[data-for]').forEach(function (n) { n.hidden = n.getAttribute('data-for') !== svc; });
  }
  $$('.mt').forEach(function (t) { t.addEventListener('click', function () { setService(t.dataset.service); }); });

  /* ================================================================ quote */
  var form = $('#quote-form'), result = $('#quote-result');
  function showError(msg) { var e = $('#q-err'); e.textContent = msg; e.hidden = !msg; }
  var started = false;
  if (form) form.addEventListener('change', function () { if (!started) { started = true; track('quote_start'); } });

  function requestQuote() {
    var from = $('#q-from').value, to = $('#q-to').value;
    if (!from) { showError('Choose where we collect you.'); $('#q-from').focus(); return; }
    if (S.service === 'transfer' && !to) { showError('Choose your destination.'); $('#q-to').focus(); return; }
    if (!when.value) { showError('Choose a date and time.'); when.focus(); return; }
    showError('');
    var btn = $('button[type="submit"]', form); btn.disabled = true; btn.textContent = 'Checking availability…';
    var body = { service: S.service, origin: from, destination: S.service === 'transfer' ? to : null,
      hours: S.service === 'hourly' ? +$('#q-hours').value : null, pickup_local: when.value,
      passengers: +$('#q-pax').textContent, large_bags: +$('#q-bags').textContent,
      carry_ons: +$('#q-carry').textContent, session_id: session.id, attribution: attribution() };
    api('POST', '/api/quotes', body).then(function (q) {
      S.quote = q; S.trip = body;
      renderQuote(q);
      if (q.amount_cents) trackEcommerce('view_item', q, { bookable: q.bookable, instant: q.instant, availability: q.availability || 'n/a' });
    }).catch(function (e) { showError(e.message); })
      .then(function () { btn.disabled = false; btn.textContent = 'See price'; });
  }

  function renderQuote(q) {
    $('#r-route').textContent = routeLabel(q);
    $('#r-price').textContent = q.amount_cents ? money(q.amount_cents) : 'Priced personally';
    var was = $('#r-was'), offer = $('#r-offer');
    was.textContent = q.offer ? money(q.list_amount_cents) : '';
    offer.hidden = !q.offer; offer.textContent = q.offer ? q.offer.label + ' — ' + q.offer.percent_off + '% off' : '';
    $('#r-meta').textContent = fmtWhen(q.pickup_at) + ' · ' + (q.price_status === 'custom' ? 'We will confirm a price personally'
      : 'All-inclusive' + (q.price_status === 'estimate' ? ' · confirmed before payment' : ''));
    var msgs = $('#r-msgs'); msgs.innerHTML = '';
    q.messages.filter(function (m) { return m.code !== 'estimate'; }).forEach(function (m) {
      var li = document.createElement('li'); li.textContent = m.message; msgs.appendChild(li);
    });
    var alts = $('#r-alts'); alts.innerHTML = '';
    (q.alternatives || []).forEach(function (a) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.textContent = a.label;
      b.addEventListener('click', function () { when.value = a.pickup_local; track('alternative_time_selected'); requestQuote(); });
      alts.appendChild(b);
    });
    var book = $('#r-book');
    book.dataset.mode = q.bookable ? (q.instant ? 'instant' : 'request') : 'bespoke';
    book.textContent = q.bookable ? (q.instant ? 'Reserve' : 'Request this journey') : 'Arrange this journey';
    book.hidden = !q.bookable && (q.alternatives || []).length > 0;
    form.hidden = true; result.hidden = false;
  }

  if (form) {
    form.addEventListener('submit', function (e) { e.preventDefault(); requestQuote(); });
    $('#r-edit').addEventListener('click', function () { result.hidden = true; form.hidden = false; $('#q-from').focus(); });
    $('#r-book').addEventListener('click', function () {
      if (this.dataset.mode === 'bespoke') { prefillBespoke(); location.hash = '#bespoke'; return; }
      openSheet();
    });
    var qs = new URLSearchParams(location.search);
    if (qs.get('from')) $('#q-from').value = qs.get('from');
    if (qs.get('to')) $('#q-to').value = qs.get('to');
    if (qs.get('service') === 'hourly') setService('hourly');
  }

  /* Service cards and popular journeys pre-fill the form */
  $$('[data-service]').forEach(function (el) {
    if (el.classList.contains('mt')) return;
    el.addEventListener('click', function () {
      var svc = el.dataset.service;
      if (svc === 'transfer' || svc === 'hourly') { setService(svc); result.hidden = true; form.hidden = false; }
    });
  });
  $$('.jr').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault(); setService('transfer');
      $('#q-from').value = a.dataset.from; $('#q-to').value = a.dataset.to;
      result.hidden = true; form.hidden = false;
      document.getElementById('reserve').scrollIntoView({ behavior: 'smooth', block: 'center' });
      track('popular_journey_selected', { journey: a.dataset.from + '-' + a.dataset.to });
      requestQuote();
    });
  });

  /* ======================================================== reservation */
  var sheet = $('#book'), bform = $('#book-form'), step = 1;
  var TITLES = { 1: 'Your details', 2: 'Your cabin', 3: 'Review', 4: 'Done' };
  var MODE_DEFAULTS = { quiet: ['normal', 'off', 'minimal'], work: ['cool', 'off', 'minimal'],
    relax: ['cool', 'soft', 'minimal'], family: ['normal', 'soft', 'normal'] };
  function field(n) { return bform.elements[n]; }

  function openSheet() {
    var q = S.quote; if (!q || !sheet) return;
    $('#book-sum').innerHTML = '';
    var left = document.createElement('span'); left.textContent = routeLabel(q) + ' · ' + fmtWhen(q.pickup_at);
    var right = document.createElement('b'); right.className = 'num'; right.textContent = money(q.amount_cents);
    $('#book-sum').appendChild(left); $('#book-sum').appendChild(right);
    var isTransfer = S.trip.service === 'transfer';
    $$('[data-transfer]', bform).forEach(function (n) { n.hidden = !isTransfer; $('input', n).required = isTransfer; });
    var airport = (PAGE.airports || []).indexOf(S.trip.origin) >= 0 || (PAGE.airports || []).indexOf(S.trip.destination) >= 0;
    $$('[data-airport]', bform).forEach(function (n) { n.hidden = !airport; });
    if (isTransfer && !field('dropoff_address').value) field('dropoff_address').value = PAGE.places[S.trip.destination] || '';
    go(1);
    if (sheet.showModal) sheet.showModal(); else sheet.setAttribute('open', '');
    document.body.classList.add('sheet-open');
    trackEcommerce('begin_checkout', q, { instant: q.instant });
  }
  function go(n) {
    step = n;
    $$('.pane', bform).forEach(function (p) { p.hidden = +p.dataset.pane !== n; });
    $('#book-h').textContent = TITLES[n];
    $('#book-step').textContent = n <= 3 ? 'Step ' + n + ' of 3' : '';
    $('#book-back').style.visibility = n > 1 && n < 4 ? 'visible' : 'hidden';
    $('#book-skip').hidden = n !== 2;
    $('#book-next').textContent = n === 3 ? (S.quote.instant ? 'Reserve & pay ' + money(S.quote.amount_cents) : 'Send request') : 'Continue';
    $('#book-ft').hidden = n === 4; $('#book-sum').hidden = n === 4;
    bookError('');
    if (n === 3) buildReview();
    track('reservation_step', { step: n });
    var first = $('.pane[data-pane="' + n + '"] input:not([type=hidden]):not([type=radio]):not([type=checkbox])', bform);
    if (first && n === 1) setTimeout(function () { first.focus({ preventScroll: true }); }, 60);
  }
  function bookError(msg) { var e = $('#book-err'); e.textContent = msg; e.hidden = !msg; }
  function validPane(n) {
    var ok = true;
    $$('.pane[data-pane="' + n + '"] [required]', bform).forEach(function (el) {
      if (el.closest('[hidden]')) return;
      var bad = el.type === 'checkbox' ? !el.checked : !el.checkValidity() || !el.value.trim();
      if (el.type === 'tel') bad = bad || el.value.replace(/\D/g, '').length < 10;
      el.classList.toggle('bad', bad);
      if (bad && ok) { el.focus(); ok = false; }
    });
    if (!ok) bookError(n === 3 ? 'Please accept the terms to continue.' : 'Please complete the highlighted fields.');
    return ok;
  }
  function prefs() {
    var v = function (n) { var el = bform.querySelector('input[name="' + n + '"]:checked'); return el ? el.value : undefined; };
    return { mode: v('mode'), temperature: v('temperature'), music: v('music'), conversation: v('conversation'),
      still_water: field('still_water').checked, child_seat: field('child_seat').value,
      child_details: field('child_details').value.trim() || null, requests: field('requests').value.trim() || null };
  }
  function buildReview() {
    var q = S.quote, pr = prefs(), rows = [['When', fmtWhen(q.pickup_at)], ['From', field('pickup_address').value]];
    if (S.trip.service === 'transfer') rows.push(['To', field('dropoff_address').value]);
    else rows.push(['Duration', S.trip.hours + ' hours']);
    rows.push(['Guests', S.trip.passengers + ' · ' + S.trip.large_bags + ' large · ' + S.trip.carry_ons + ' carry-on'],
      ['Cabin', pr.mode + ' · ' + pr.temperature + (pr.child_seat !== 'none' ? ' · child seat' : '')],
      ['Contact', field('name').value], ['Total', money(q.amount_cents) + ' all-inclusive']);
    var dl = $('#book-review'); dl.innerHTML = '';
    rows.forEach(function (r) {
      var dt = document.createElement('dt'), dd = document.createElement('dd');
      dt.textContent = r[0]; dd.textContent = r[1]; dl.appendChild(dt); dl.appendChild(dd);
    });
  }
  function submit() {
    var btn = $('#book-next'); btn.disabled = true; btn.textContent = S.quote.instant ? 'Opening secure payment…' : 'Sending…';
    var body = {
      quote_id: S.quote.quote_id,
      contact: { name: field('name').value.trim(), email: field('email').value.trim(), phone: field('phone').value.trim() },
      trip: { pickup_address: field('pickup_address').value.trim(),
        dropoff_address: S.trip.service === 'transfer' ? field('dropoff_address').value.trim() : 'As directed (hourly)',
        flight_number: field('flight_number').value.trim() || null, notes: field('notes').value.trim() || null },
      preferences: prefs(), remember_preferences: field('remember_preferences').checked,
      accept_policy_version: (S.cfg && S.cfg.policy.version) || PAGE.policyVersion,
      source: (attribution().utm_source) || 'direct', attribution: attribution(), website: field('website').value
    };
    api('POST', '/api/bookings', body).then(function (r) {
      if (r.checkout_url) {
        trackEcommerce('add_payment_info', S.quote, { payment_type: 'stripe_checkout', reservation_ref: r.ref });
        window.location.assign(r.checkout_url);
        return;
      }
      trackEcommerce('generate_lead', S.quote, { reservation_ref: r.ref, instant: r.instant });
      $('#done-h').textContent = r.instant ? 'Reserved — payment pending' : 'Request received';
      $('#done-text').textContent = r.instant
        ? 'Reference ' + r.ref + '. Your time is held — complete payment from your trip page to confirm.'
        : 'Reference ' + r.ref + '. We are confirming the details and will email you shortly — no payment has been taken.';
      $('#done-link').href = r.trip_url;
      go(4);
    }).catch(function (e) {
      bookError(e.code === 'quote_expired' ? 'That price has expired. Close this and tap “See price” again.'
        : e.code === 'slot_taken' ? 'That time was just reserved by someone else. Close this to see the nearest open times.'
        : e.message);
      if (e.code === 'slot_taken') requestQuote();
    }).then(function () { btn.disabled = false; if (step === 3) go(3); });
  }
  if (bform) {
    $('#book-next').addEventListener('click', function () {
      if (!validPane(step)) return;
      if (step < 3) go(step + 1); else submit();
    });
    $('#book-skip').addEventListener('click', function () { go(3); });
    $('#book-back').addEventListener('click', function () { if (step > 1) go(step - 1); });
    bform.addEventListener('input', function (e) { if (e.target.classList) e.target.classList.remove('bad'); });
    $$('input[name="mode"]', bform).forEach(function (r) {
      r.addEventListener('change', function () {
        MODE_DEFAULTS[r.value].forEach(function (v, i) {
          var el = bform.querySelector('input[name="' + ['temperature', 'music', 'conversation'][i] + '"][value="' + v + '"]');
          if (el) el.checked = true;
        });
      });
    });
    field('child_seat').addEventListener('change', function () { $('[data-child]', bform).hidden = this.value === 'none'; });
    sheet.addEventListener('click', function (e) { if (e.target === sheet) sheet.close(); });
    sheet.addEventListener('close', function () { document.body.classList.remove('sheet-open'); });
  }

  /* ============================================================ bespoke */
  function prefillBespoke() {
    var f = $('#bespoke'); if (!f || !S.quote) return;
    f.elements.message.value = routeLabel(S.quote) + '\n' + fmtWhen(S.quote.pickup_at) + '\nGuests: ' + S.trip.passengers +
      ', large bags: ' + S.trip.large_bags + ', carry-ons: ' + S.trip.carry_ons;
    f.elements.topic.selectedIndex = 3;
  }
  var bf = $('#bespoke');
  if (bf) bf.addEventListener('submit', function (e) {
    e.preventDefault();
    var out = $('.form-out', bf), email = bf.elements.email.value.trim();
    if (!/^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(email) || !bf.elements.message.value.trim()) {
      out.textContent = 'Please add your email and a few details.'; return;
    }
    var btn = $('button', bf); btn.disabled = true;
    api('POST', '/api/inquiries', { kind: 'custom_quote', email: email, name: bf.elements.name.value.trim() || null,
      phone: bf.elements.phone.value.trim() || null,
      message: bf.elements.topic.value + '\n\n' + bf.elements.message.value.trim(),
      source: attribution().utm_source || null, website: bf.elements.website.value })
      .then(function () { bf.reset(); out.textContent = 'Thank you. We will be in touch personally.';
        track('generate_lead', { lead_type: 'bespoke', currency: 'USD', value: 0 }); })
      .catch(function (err) { out.textContent = err.message; })
      .then(function () { btn.disabled = false; });
  });

  /* ========================================================= page polish */
  $$('[data-year]').forEach(function (n) { n.textContent = new Date().getFullYear(); });
  var mbar = $('#mbar'), quoteBox = $('#reserve');
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  /* the logo draws itself once, the first time it scrolls into view */
  if ('IntersectionObserver' in window && !reduce) {
    var bio = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.replace('pre', 'play'); bio.unobserve(en.target); }
      });
    }, { threshold: 0.5 });
    $$('.brand-anim').forEach(function (el) { el.classList.add('pre'); bio.observe(el); });
  }
  /* the hero logo loops like the design and rests while out of view; the header wordmark takes over
     only once it has scrolled away, so the name never appears twice on screen */
  if ('IntersectionObserver' in window) {
    $$('.brand-loop').forEach(function (el) {
      document.body.classList.add('has-hero-logo');
      new IntersectionObserver(function (es) {
        var seen = es[0].isIntersecting;
        el.classList.toggle('off', !seen); document.body.classList.toggle('logo-away', !seen);
      }, { rootMargin: '-64px 0px 0px 0px' }).observe(el);
    });
  }
  if ('IntersectionObserver' in window) {
    if (mbar && quoteBox) new IntersectionObserver(function (es) { mbar.classList.toggle('show', !es[0].isIntersecting); }).observe(quoteBox);
    if (!reduce) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
      }, { rootMargin: '0px 0px -8% 0px' });
      $$('.sec .h2, .services li, .pillars li, .steps li, .features li, .amen, .cabin-art, .phone, .journeys li, .hourly-card')
        .forEach(function (el) { el.classList.add('reveal'); io.observe(el); });
    }
  }
})();
