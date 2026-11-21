"""The logo, composed from outlined lettering (static/brand/*.svg, made by tools/make_brand.py)
and the SUV line drawing from the logo design file.

Geometry reproduces the design's layout exactly: wordmark 112 px with line-height 1.05 and
14 px top padding; the SUV artwork (viewBox 420 x 104) stretched to the lockup width and
pulled up 6 px; tagline row 24 px below, 20 px Jost tracked 0.46em between two 1 px rules
with 14 px gaps. Colours are the design's: navy #0A0E1C, ice #9FD8E6, cream #F4F1EA.
"""
from __future__ import annotations

import re
from functools import lru_cache
from html import escape as e
from pathlib import Path

import data

BRAND_DIR = Path(__file__).resolve().parent.parent / "static" / "brand"
NAVY, ICE, CREAM = "#0A0E1C", "#9FD8E6", "#F4F1EA"


@lru_cache(maxsize=None)
def art(name: str) -> dict:
    svg = (BRAND_DIR / f"{name}.svg").read_text()
    meta = {k: float(v) for k, v in re.findall(r'data-([a-z0-9]+)="([-\d.]+)"', svg)}
    meta["d"] = re.search(r' d="([^"]+)"', svg).group(1)
    meta["viewBox"] = re.search(r'viewBox="([^"]+)"', svg).group(1)
    return meta


def wordmark(cls: str = "wm") -> str:
    """The wordmark alone, inheriting the text colour (header, app pages)."""
    w = art("wordmark")
    return (f'<svg class="{cls}" viewBox="{w["viewBox"]}" aria-hidden="true" focusable="false">'
            f'<path fill="currentColor" d="{w["d"]}"/></svg>')


def _suv(p: str) -> str:
    """The SUV drawing, verbatim from the design (viewBox 0 0 420 104). `p` prefixes ids and classes."""
    return f"""<defs>
<linearGradient id="{p}gg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="420" y2="0"><stop offset="0" stop-color="{ICE}" stop-opacity="0"/><stop offset=".5" stop-color="{ICE}" stop-opacity=".5"/><stop offset="1" stop-color="{ICE}" stop-opacity="0"/></linearGradient>
<linearGradient id="{p}bg" gradientUnits="userSpaceOnUse" x1="366" y1="0" x2="418" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<filter id="{p}glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4"/></filter>
<filter id="{p}soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="1.3"/></filter>
</defs>
<g fill="none" stroke="{ICE}" stroke-linecap="round" stroke-linejoin="round">
<path class="{p}ground" d="M0 97H420" stroke="url(#{p}gg)" stroke-width="1.2"/>
<path class="{p}fade" d="M98 12L102 8H230L234 12" stroke-opacity=".65" stroke-width="1.3"/>
<path class="{p}body" d="M72 84C66 84 63 81 63 76V58L67 22C68 16 72 13 78 13L252 12C258 12 262 14 266 18L294 44C296 46 299 47 303 47L352 49C358 49 362 52 363 57L365 74C365 80 362 84 356 84H330A24 24 0 0 0 282 84H142A24 24 0 0 0 94 84Z" stroke-width="2"/>
<path class="{p}window" d="M88 20L254 19C257 19 259 20 261 22L281 45L84 46Z" stroke-opacity=".65" stroke-width="1.3"/>
<path class="{p}fade" d="M196 19.5V45.6M128 19.8V45.8" stroke-opacity=".65" stroke-width="1.3"/>
<path class="{p}fade" d="M150 89H276" stroke-opacity=".65" stroke-width="1.6"/>
<circle class="{p}wheel" cx="118" cy="80" r="16" fill="{NAVY}" stroke-width="2"/>
<circle class="{p}fade" cx="118" cy="80" r="5.5" stroke-opacity=".65" stroke-width="1.3"/>
<circle class="{p}wheel" cx="306" cy="80" r="16" fill="{NAVY}" stroke-width="2"/>
<circle class="{p}fade" cx="306" cy="80" r="5.5" stroke-opacity=".65" stroke-width="1.3"/>
<path class="{p}glint" d="M63 58L67 22C68 16 72 13 78 13L252 12C258 12 262 14 266 18L294 44C296 46 299 47 303 47L352 49C358 49 362 52 363 57" stroke="#fff" stroke-width="3" filter="url(#{p}soft)"/>
<path class="{p}beam" d="M368 54L418 51" stroke="url(#{p}bg)" stroke-width="3"/>
</g>
<g transform="translate(361 54)"><g class="{p}star"><circle r="10" fill="{ICE}" opacity=".5" filter="url(#{p}glow)"/>
<path d="M0-9C.81-2.52 2.52-.81 9 0 2.52.81.81 2.52 0 9-.81 2.52-2.52.81-9 0-2.52-.81-.81-2.52 0-9Z" fill="#fff"/></g></g>"""


@lru_cache(maxsize=None)
def layout() -> dict:
    """Positions in the design's pixel space (origin: top-left of the lockup)."""
    w, t = art("wordmark"), art("tagline")
    tag_w = t["advance"] + 0.46 * t["size"]                          # tracking + text-indent
    width = max(w["advance"], tag_w + 60)                           # 16 px rule + 14 px gap, both sides
    line = 1.05 * w["size"]
    word_base = 14 + (line - (w["ascent"] + w["descent"])) / 2 + w["ascent"]
    suv_top, suv_h = 14 + line - 6, width * 0.2476
    s = min(width / 420, suv_h / 104)
    row_top = suv_top + suv_h + 24
    rule = (width - 28 - tag_w) / 2
    tag_base = row_top + (20 - (t["ascent"] + t["descent"])) / 2 + t["ascent"]
    top = min(0.0, word_base + w["y0"])
    return {"width": width, "top": top, "height": row_top + 20 - top, "word_x": (width - w["advance"]) / 2,
            "word_base": word_base, "suv": (round((width - 420 * s) / 2, 3), round(suv_top + (suv_h - 104 * s) / 2, 3),
                                            round(s, 5)),
            "rule_y": row_top + 9.5, "rule": rule, "tag_x": rule + 14 + 0.46 * t["size"], "tag_base": tag_base,
            "tag_w": tag_w}


def lockup(cls: str = "lockup", animated: bool = False, pad: float = 8) -> str:
    """Full logo: wordmark, SUV, rules and tagline. `animated` draws it once when scrolled into view."""
    L, w, t = layout(), art("wordmark"), art("tagline")
    p = "cl-"
    a = (lambda c: f' class="{p}{c}"') if animated else (lambda c: "")
    x0, y0, width, height = -pad, L["top"] - pad, L["width"] + 2 * pad, L["height"] + 2 * pad
    sx, sy, s = L["suv"]
    right = L["rule"] + 28 + L["tag_w"]
    suv = _suv(p) if animated else re.sub(r' class="cl-[a-z]+"', "", _suv(p))
    if not animated:
        suv = re.sub(r'<path d="M63 58L67 22[^>]*/>\n', "", suv)    # the glint only exists while animating
    return (f'<svg class="{cls}{" brand-anim" if animated else ""}" viewBox="{x0:.2f} {y0:.2f} {width:.2f} {height:.2f}" '
            f'role="img" aria-label="{e(data.BRAND["name"])}">'
            f'<g transform="translate({L["word_x"]:.2f} {L["word_base"]:.2f})"><g{a("word")}><path fill="{CREAM}" d="{w["d"]}"/></g></g>'
            f'<g transform="translate({sx} {sy}) scale({s})">{suv}</g>'
            f'<g fill="{ICE}" opacity=".7"><rect{a("rulel")} x="0" y="{L["rule_y"]:.2f}" width="{L["rule"]:.2f}" height="1"/>'
            f'<rect{a("ruler")} x="{right:.2f}" y="{L["rule_y"]:.2f}" width="{L["width"] - right:.2f}" height="1"/></g>'
            f'<g transform="translate({L["tag_x"]:.2f} {L["tag_base"]:.2f})"><g{a("tag")}><path fill="{CREAM}" d="{t["d"]}"/></g></g>'
            f'</svg>')


def monogram_svg(size: int = 64) -> str:
    """Browser-tab icon: the script initial in cream on a navy tile."""
    m = art("monogram")
    vx, vy, vw, vh = (float(v) for v in m["viewBox"].split())
    k = 0.72 * size / max(vw, vh)
    tx, ty = (size - vw * k) / 2 - vx * k, (size - vh * k) / 2 - vy * k
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" rx="{size * 0.22:.0f}" fill="{NAVY}"/>'
            f'<path transform="translate({tx:.2f} {ty:.2f}) scale({k:.4f})" fill="{CREAM}" d="{m["d"]}"/></svg>\n')
