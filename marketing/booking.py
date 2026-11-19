"""The reservation sheet: a native <dialog> with three short steps.

Details -> Cabin (optional) -> Review & pay. The browser only returns the
server's quote id; the server owns the amount and decides instant vs request.
"""
from __future__ import annotations

from html import escape as e

import data
from .icons import icon

MODES = [("quiet", "Quiet", "Calls and focus"),
         ("work", "Work", "Cool, steady, chargers out"),
         ("relax", "Relax", "Soft music, blanket"),
         ("family", "Family", "Time for bags and little ones")]


def _seg(name: str, options: list[tuple[str, str]], checked: str) -> str:
    return "".join(f'<input type="radio" name="{name}" id="{name}-{v}" value="{v}"{" checked" if v == checked else ""}>'
                   f'<label for="{name}-{v}">{e(lbl)}</label>' for v, lbl in options)


def dialog() -> str:
    modes = "".join(
        f'<input type="radio" name="mode" id="mode-{v}" value="{v}"{" checked" if v == "quiet" else ""}>'
        f'<label for="mode-{v}" class="mode"><b>{e(t)}</b><small>{e(d)}</small></label>' for v, t, d in MODES)
    return f"""
<dialog class="sheet" id="book" aria-labelledby="book-h">
  <form method="dialog" class="sheet-in" id="book-form" novalidate>
    <header class="sheet-hd">
      <div><p class="sheet-step" id="book-step">Step 1 of 3</p><h2 id="book-h">Your details</h2></div>
      <button class="x" value="close" aria-label="Close" formnovalidate>{icon('plus', 22, 'ic x-ic')}</button>
    </header>
    <div class="sheet-sum" id="book-sum"></div>

    <section class="pane" data-pane="1">
      <label>Pickup address<input name="pickup_address" required minlength="5" maxlength="300"
        autocomplete="street-address" placeholder="Street and town, or terminal"></label>
      <label data-transfer>Drop-off address<input name="dropoff_address" required minlength="3" maxlength="300"
        placeholder="Street and town, or terminal"></label>
      <label data-airport>Flight or tail number <span class="opt">optional</span><input name="flight_number"
        maxlength="12" placeholder="e.g. UA 1234 or N123AB" pattern="[A-Za-z0-9 ]*"></label>
      <div class="two">
        <label>Full name<input name="name" required minlength="2" maxlength="100" autocomplete="name"></label>
        <label>Mobile<input name="phone" type="tel" required autocomplete="tel" maxlength="25"></label>
      </div>
      <label>Email<input name="email" type="email" required autocomplete="email" maxlength="254"></label>
      <label>Notes for your chauffeur <span class="opt">optional</span><textarea name="notes" rows="2" maxlength="500"
        placeholder="Itinerary, gate code, an extra stop…"></textarea></label>
    </section>

    <section class="pane" data-pane="2" hidden>
      <p class="pane-lede">Optional — set the cabin before you sit.</p>
      <fieldset><legend>The ride</legend><div class="modes">{modes}</div></fieldset>
      <fieldset><legend>Temperature</legend><div class="seg sm">{_seg('temperature', [('cool', 'Cool'), ('normal', 'Comfortable'), ('warm', 'Warm')], 'normal')}</div></fieldset>
      <fieldset><legend>Music</legend><div class="seg sm">{_seg('music', [('off', 'Off'), ('soft', 'Soft'), ('guest_choice', 'My own')], 'off')}</div></fieldset>
      <fieldset><legend>Conversation</legend><div class="seg sm">{_seg('conversation', [('minimal', 'Minimal'), ('normal', 'Welcome')], 'minimal')}</div></fieldset>
      <label class="check"><input type="checkbox" name="still_water" checked> Chilled still water</label>
      <label>Child seat <span class="opt">optional</span><select name="child_seat">
        <option value="none">Not needed</option><option value="infant">Infant (rear-facing)</option>
        <option value="toddler">Toddler (forward-facing)</option><option value="booster">Booster</option></select></label>
      <label data-child hidden>Child's age and weight<input name="child_details" maxlength="120" placeholder="e.g. 3 years, 32 lb"></label>
      <label>Anything else <span class="opt">optional</span><textarea name="requests" rows="2" maxlength="500"></textarea></label>
      <label class="check"><input type="checkbox" name="remember_preferences"> Remember my preferences</label>
    </section>

    <section class="pane" data-pane="3" hidden>
      <dl class="review" id="book-review"></dl>
      <p class="fine" id="book-terms-note">{e(data.POLICY['summary'])}</p>
      <label class="check"><input type="checkbox" name="accept" required> I agree to the <a href="/terms" target="_blank" rel="noopener">terms</a></label>
      <p class="fine secure">{icon('lock', 14)} Secure payment by Stripe — Apple Pay, Google Pay, Link or card.</p>
    </section>

    <section class="pane done" data-pane="4" hidden>
      {icon('check', 40, 'ic done-ic')}
      <h3 id="done-h">Request received</h3>
      <p id="done-text"></p>
      <a class="btn btn-dark btn-block btn-lg" id="done-link" href="#">View your trip</a>
    </section>

    <input name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
    <p class="err" id="book-err" role="alert" hidden></p>
    <footer class="sheet-ft" id="book-ft">
      <button type="button" class="btn btn-ghost" id="book-back">Back</button>
      <button type="button" class="btn btn-ghost" id="book-skip" hidden>Skip</button>
      <button type="button" class="btn btn-dark btn-lg" id="book-next">Continue</button>
    </footer>
  </form>
</dialog>"""
