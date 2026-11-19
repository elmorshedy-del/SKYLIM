#!/usr/bin/env python3
"""Generate the marketing site and SEO files from data.py.

    python3 build.py

Writes index.html, pricing.md, robots.txt and sitemap.xml. Never hand-edit those
outputs: change data.py (content, rates) or marketing/ (layout), then rebuild.
"""
from __future__ import annotations

import sys
from pathlib import Path

import data
from marketing import page, seo

ROOT = Path(__file__).resolve().parent


def warnings() -> list[str]:
    out = []
    if data.BRAND.get("placeholder"):
        out.append("BRAND contains placeholder contact details (data.py) — not launch-ready")
    if not data.PRICING["approved"]:
        out.append("PRICING['approved'] is False — prices are shown as estimates")
    if not data.POLICY.get("approved"):
        out.append("POLICY not approved — payments stay off in production")
    return out


def main() -> int:
    outputs = {"index.html": page.render(), "pricing.md": seo.pricing_md(),
               "robots.txt": seo.robots_txt(), "sitemap.xml": seo.sitemap_xml()}
    for name, content in outputs.items():
        (ROOT / name).write_text(content, encoding="utf-8")
        print(f"wrote {name:<12} {len(content.encode()) / 1024:6.1f} KB")
    for w in warnings():
        print("warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
