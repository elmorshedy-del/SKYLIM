#!/usr/bin/env python3
"""Generate the marketing site and SEO files from data.py and landing_pages.py.

    python3 build.py

Writes index.html, pages/**.html (search landing pages), pricing.md, robots.txt,
sitemap.xml, seo_lastmod.json and static/favicon.svg (from the logo). Never hand-edit
those outputs: change data.py (facts, rates), landing_pages.py (landing copy) or
marketing/ (layout), then rebuild.
"""
from __future__ import annotations

import sys
from pathlib import Path

import data
import landing_pages
from marketing import brand, page, seo

ROOT = Path(__file__).resolve().parent
LEGAL = ["terms", "privacy", "accessibility"]


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
    pages = {"/": ("index.html", page.render())}
    for p in landing_pages.PAGES:
        pages[p["path"]] = (page.landing_file(p), page.render_landing(p))
    outputs = {name: html for name, html in pages.values()}
    outputs.update({"pricing.md": seo.pricing_md(), "robots.txt": seo.robots_txt(),
                    "static/favicon.svg": brand.monogram_svg()})

    # sitemap dates follow content, not the build date
    contents = {path: html for path, (_, html) in pages.items()}
    contents["/pricing.md"] = outputs["pricing.md"]
    for name in LEGAL:
        contents[f"/{name}"] = (ROOT / "app" / "templates" / "legal" / f"{name}.html").read_text()
    outputs["sitemap.xml"] = seo.sitemap_xml(seo.update_lastmod(contents))

    for name, content in outputs.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {name:<40} {len(content.encode()) / 1024:6.1f} KB")
    for w in warnings():
        print("warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
