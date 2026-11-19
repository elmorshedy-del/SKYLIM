/* Trip and shared-location pages.
   Shows only real location reports: the marker sits at the last fix, the age is
   always visible, and the view turns "stale" instead of guessing when reports stop. */
(function () {
  'use strict';
  var cfgEl = document.getElementById('trip-config');
  if (!cfgEl) return;
  var cfg = JSON.parse(cfgEl.textContent);
  var ET = 'America/New_York';
  var $ = function (s) { return document.querySelector(s); };

  /* ------------------------------------------------ local times (always ET) */
  function fmt(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString('en-US', { timeZone: ET, weekday: 'short', month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit' }) + ' ET';
  }
  document.querySelectorAll('[data-local-time]').forEach(function (el) {
    var v = el.getAttribute('data-local-time');
    if (v && v !== 'None') el.textContent = (el.getAttribute('data-prefix') || '') + fmt(v);
  });

  function api(method, url, body) {
    return fetch(url, {
      method: method, headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: body ? JSON.stringify(body) : undefined, credentials: 'omit', cache: 'no-store'
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) throw new Error(j.message || j.detail || 'Something went wrong.');
        return j;
      });
    });
  }

  /* ------------------------------------------- status: refresh on change */
  if (cfg.mode !== 'share') {
    var fast = /checkout=returned/.test(location.search) && cfg.status === 'payment_pending';
    setInterval(function () {
      api('GET', '/api/trips/' + cfg.token).then(function (t) {
        if (t.status !== cfg.status) location.replace(location.pathname);
      }).catch(function () {});
    }, fast ? 5000 : 30000);
  }

  /* ------------------------------------------------------------ live map */
  if (cfg.tracking && window.L && document.getElementById('map')) {
    var map = L.map('map', { zoomControl: false, attributionControl: true, scrollWheelZoom: false })
      .setView([40.75, -74.05], 11);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.tileLayer(cfg.tiles, { maxZoom: 19, attribution: cfg.attribution }).addTo(map);
    var marker = null, accuracy = null, lastFix = null, centred = false;
    var carIcon = function (stale) {
      return L.divIcon({ className: '', iconSize: [40, 40], iconAnchor: [20, 20],
        html: '<div class="car-mk' + (stale ? ' stale' : '') + '"><svg width="18" height="18" viewBox="0 0 24 24" ' +
          'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M5 17h14M3 13l1.6-5A2 ' +
          '2 0 016.5 6.5h11a2 2 0 011.9 1.5L21 13v4H3v-4z"/></svg></div>' });
    };
    var url = cfg.mode === 'share' ? '/api/share/' + cfg.shareToken + '/position' : '/api/trips/' + cfg.token + '/position';

    function paint(p) {
      var status = $('#pos-status'), note = $('#pos-note');
      if (p.status_label && $('#share-status')) $('#share-status').textContent = p.status_label;
      if (!p.available) {
        status.innerHTML = '<span class="dot"></span> ' + (p.message ? 'Waiting for location' : p.status_label);
        if (note) { note.hidden = !p.message; note.textContent = p.message || ''; }
        return;
      }
      lastFix = new Date(p.reported_at);
      var ll = [p.lat, p.lon];
      if (!marker) {
        marker = L.marker(ll, { icon: carIcon(p.stale), keyboard: false }).addTo(map);
        accuracy = L.circle(ll, { radius: p.accuracy_m || 0, weight: 0, fillOpacity: 0.08, fillColor: '#000' }).addTo(map);
      } else {
        marker.setLatLng(ll); marker.setIcon(carIcon(p.stale));
        accuracy.setLatLng(ll); accuracy.setRadius(p.accuracy_m || 0);
      }
      if (!centred) { map.setView(ll, 14); centred = true; } else if (!map.getBounds().pad(-0.2).contains(ll)) { map.panTo(ll); }
      status.innerHTML = p.stale ? '<span class="dot stale"></span> Last known position'
                                 : '<span class="dot live"></span> Live';
      if (note) { note.hidden = !p.stale; note.className = 'notice warn'; note.textContent = p.message || ''; }
      tickAge();
    }
    function tickAge() {
      var el = $('#pos-age'); if (!el || !lastFix) return;
      var s = Math.max(0, Math.round((Date.now() - lastFix.getTime()) / 1000));
      el.textContent = 'Updated ' + (s < 60 ? s + 's' : Math.floor(s / 60) + 'm ' + (s % 60) + 's') + ' ago';
    }
    function poll() {
      api('GET', url).then(paint).catch(function (e) {
        var st = $('#pos-status'); if (st) st.innerHTML = '<span class="dot stale"></span> ' + e.message;
      });
    }
    poll();
    setInterval(poll, 8000);
    setInterval(tickAge, 1000);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
  }

  /* -------------------------------------------------------------- actions */
  var share = $('#share-btn');
  if (share) share.addEventListener('click', function () {
    share.disabled = true;
    api('POST', '/api/trips/' + cfg.token + '/share', { hours: 4 }).then(function (r) {
      var out = $('#share-out');
      out.innerHTML = '';
      var a = document.createElement('a'); a.href = r.share_url; a.textContent = r.share_url; out.appendChild(a);
      if (navigator.share) { navigator.share({ title: 'Follow my car', url: r.share_url }).catch(function () {}); }
      else if (navigator.clipboard) { navigator.clipboard.writeText(r.share_url).then(function () {
        out.appendChild(document.createTextNode(' — copied.')); }); }
    }).catch(function (e) { $('#share-out').textContent = e.message; })
      .then(function () { share.disabled = false; });
  });
  var unshare = $('#unshare-btn');
  if (unshare) unshare.addEventListener('click', function () {
    api('DELETE', '/api/trips/' + cfg.token + '/share').then(function () { location.reload(); });
  });
  var cancel = $('#cancel-btn');
  if (cancel) cancel.addEventListener('click', function () {
    if (!window.confirm('Cancel this trip? This cannot be undone.')) return;
    cancel.disabled = true;
    api('POST', '/api/trips/' + cfg.token + '/cancel', {}).then(function (r) {
      $('#cancel-out').textContent = r.refund_cents ? 'Cancelled. Your refund is on its way.'
        : r.review ? 'Cancelled. The owner will review any refund and email you.' : 'Cancelled.';
      setTimeout(function () { location.reload(); }, 1600);
    }).catch(function (e) { $('#cancel-out').textContent = e.message; cancel.disabled = false; });
  });
})();
