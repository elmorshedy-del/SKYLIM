"""Assembles the homepage document from sections."""
from __future__ import annotations

import json

import data
from . import booking, sections, seo

ASSET_VERSION = seo.TODAY.replace("-", "")   # cache-busts site.css / site.js on each build


def page_config() -> str:
    """Static facts the script needs before /api/config answers."""
    return json.dumps({
        "places": {p["code"]: p["short"] for p in data.PLACES},
        "airports": [p["code"] for p in data.PLACES if p["kind"] in ("airport", "aviation")],
        "policyVersion": data.POLICY["version"],
        "maxPassengers": data.VEHICLE["max_passengers"],
    }, separators=(",", ":"))


def render() -> str:
    body = "".join([
        sections.header(),
        '<main id="main">',
        sections.hero(), sections.services(), sections.cabin(), sections.standard(), sections.how(),
        sections.pricing(), sections.realtime(), sections.corporate(), sections.faq(), sections.closing(),
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/tokens.css?v={ASSET_VERSION}">
<link rel="stylesheet" href="/static/site.css?v={ASSET_VERSION}">
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{body}
<script id="page-config" type="application/json">{page_config()}</script>
<script src="/static/site.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""
