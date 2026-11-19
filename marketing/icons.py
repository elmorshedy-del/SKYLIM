"""Inline SVG: a consistent 24px, 1.75-stroke icon set and the cabin plan illustration."""
from __future__ import annotations

_PATHS = {
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "tag": '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "shield": '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3z"/><path d="m9 12 2 2 4-4"/>',
    "pin": '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "seat": '<path d="M7 4h7a2 2 0 0 1 2 2v7H7z"/><path d="M5 13h13l1 5H6z"/><path d="M8 18v3M17 18v3"/>',
    "sun": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18M8 5v14"/>',
    "wifi": '<path d="M2 9a15 15 0 0 1 20 0"/><path d="M5 12.5a10 10 0 0 1 14 0"/><path d="M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "card": '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
    "route": '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h7a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7"/>',
    "calendar": '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>',
    "sliders": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "car": '<path d="M5 17h14M3 13l1.6-5A2 2 0 0 1 6.5 6.5h11a2 2 0 0 1 1.9 1.5L21 13v4H3z"/><circle cx="7.5" cy="17" r="1.5"/><circle cx="16.5" cy="17" r="1.5"/>',
    "water": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "bolt": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "umbrella": '<path d="M3 12a9 9 0 0 1 18 0z"/><path d="M12 12v7a2 2 0 0 0 4 0"/>',
    "child": '<circle cx="12" cy="6" r="2.5"/><path d="M8 21v-6l-2-3 3-3h6l3 3-2 3v6"/>',
    "towel": '<path d="M6 4h12v16H6z"/><path d="M6 8h12"/>',
    "plane": '<path d="M10.5 13.5 3 11l1.5-1.5 7.5 1L16 6.5a2.1 2.1 0 0 1 3 3L15 13.5l1 7.5-1.5 1.5-2.5-7.5-3 3V21l-1.5 1-1-3.5L3 17.5 4 16h3l3-3z"/>',
    "star": '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/>',
    "road": '<path d="M5 21 9 3M19 21 15 3M12 5v2M12 11v2M12 17v2"/>',
    "flag": '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "volume": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M17 9a4 4 0 0 1 0 6"/>',
    "thermo": '<path d="M10 4a2 2 0 0 1 4 0v10a4 4 0 1 1-4 0z"/>',
    "dot": '<circle cx="12" cy="12" r="3"/>',
    "bag": '<rect x="5" y="7" width="14" height="13" rx="2"/><path d="M9 7V4h6v3M9 20v1M15 20v1"/>',
}


def icon(name: str, size: int = 24, cls: str = "ic") -> str:
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_PATHS[name]}</svg>')


AMENITY_ICONS = {"water": "water", "charging": "bolt", "wifi": "wifi", "towels": "towel",
                 "umbrella": "umbrella", "child_seat": "child", "quiet": "volume", "captains": "seat",
                 "sunroof": "sun", "climate": "thermo", "mints": "dot", "luggage": "bag", "tissues": "towel"}
FEATURE_ICONS = {"captains": "seat", "sunroof": "sun", "wifi": "wifi"}


def cabin_plan() -> str:
    """Top-down plan of the cabin: driver, front passenger, two second-row
    captain's chairs with an aisle, third-row bench, cargo area and the
    panoramic roof outline. Line art that inherits currentColor."""
    seat = lambda x, y, w=46, h=52, cls="": (  # noqa: E731
        f'<rect class="seat {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/>'
        f'<rect class="seat-back {cls}" x="{x + 4}" y="{y + h - 12}" width="{w - 8}" height="9" rx="4"/>')
    return f'''<svg class="cabin" viewBox="0 0 260 520" role="img" aria-labelledby="cabin-t cabin-d">
  <title id="cabin-t">Cabin plan of the Cadillac Escalade</title>
  <desc id="cabin-d">Top-down view: two front seats, two individual second-row captain's chairs with an aisle between them, a three-seat third row and a cargo area, under a panoramic roof.</desc>
  <rect class="body" x="20" y="10" width="220" height="500" rx="70"/>
  <path class="glass" d="M52 92 Q130 60 208 92 L200 128 Q130 108 60 128 Z"/>
  <rect class="roof" x="48" y="150" width="164" height="210" rx="20"/>
  {seat(62, 142)}{seat(152, 142)}
  {seat(62, 232, cls="hl")}{seat(152, 232, cls="hl")}
  <path class="aisle" d="M130 236 V 290"/>
  <rect class="seat" x="58" y="318" width="144" height="56" rx="14"/>
  <path class="seat-div" d="M106 324v44M154 324v44"/>
  <rect class="cargo" x="54" y="398" width="152" height="76" rx="14"/>
  <g class="callouts">
    <text x="130" y="306" text-anchor="middle">aisle</text>
    <text x="130" y="444" text-anchor="middle">cargo</text>
  </g>
</svg>'''
