"""Assembles the homepage document from sections."""
from __future__ import annotations

import json
import re
from pathlib import Path

import data
from . import booking, sections, seo

STATIC = Path(__file__).resolve().parent.parent / "static"
ANALYTICS_SLOT = "<!--ANALYTICS-->"   # replaced at serve time (app/web/site.py) from environment settings

ASSET_VERSION = seo.TODAY.replace("-", "")   # cache-busts site.css / site.js on each build


def page_config() -> str:
    """Static facts the script needs before /api/config answers."""
    return json.dumps({
        "places": {p["code"]: p["short"] for p in data.PLACES},
        "airports": [p["code"] for p in data.PLACES if p["kind"] in ("airport", "aviation")],
        "policyVersion": data.POLICY["version"],
        "maxPassengers": data.VEHICLE["max_passengers"],
    }, separators=(",", ":"))


def inline_css() -> str:
    """Tokens + site styles inlined: no render-blocking stylesheet requests on first paint."""
    css = (STATIC / "tokens.css").read_text() + (STATIC / "site.css").read_text()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)                 # comments
    return re.sub(r"\s*\n\s*", "", css)                             # line breaks and indentation


def render() -> str:
    body = "".join([
        sections.header(),
        '<main id="main">',
        sections.hero(), sections.services(), sections.cabin(), sections.standard(), sections.how(),
        sections.pricing(), sections.realtime(), sections.bespoke(), sections.faq(), sections.closing(),
        "</main>",
        sections.footer(),
        booking.dialog(),
    ])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#000000">
{seo.head_meta()}
<link rel="preload" href="/static/fonts/inter-tight-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>{inline_css()}</style>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
{ANALYTICS_SLOT}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{body}
<script id="page-config" type="application/json">{page_config()}</script>
<script src="/static/site.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""
