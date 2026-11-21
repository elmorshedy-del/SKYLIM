#!/usr/bin/env python3
"""Render the social share image and the logo from the brand in data.py.

    python3 tools/make_images.py

Writes static/og.png (1200x630, link previews) and static/logo.png (512x512, the
Organization logo Google may show; it asks for at least 112x112), both from the logo in
marketing/brand.py. Re-run after any change to the logo. Uses the Node Playwright and
Chromium already installed on the machine.
"""
from __future__ import annotations

import sys
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import data  # noqa: E402

FONT = (ROOT / "static/fonts/inter-tight-latin-wght-normal.woff2").as_uri()
BASE = f"""<style>@font-face{{font-family:I;src:url({FONT}) format('woff2');font-weight:100 900}}
*{{margin:0;box-sizing:border-box}}body{{font-family:I,sans-serif;background:#0A0E1C;color:#F4F1EA}}
.lk svg{{display:block;width:100%;height:auto}}</style>"""


def og_html() -> str:
    """Link preview: the logo, centred on the logo's navy, with one line of what we do."""
    from marketing.brand import lockup
    return BASE + f"""<div style="width:1200px;height:630px;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:40px;background:radial-gradient(90% 80% at 50% 40%,#141a2e 0,#0A0E1C 70%)">
  <div class="lk" style="width:430px">{lockup(cls="og", pad=0)}</div>
  <div style="font-size:21px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#AFAFAF">
    Chauffeur service · New York City &amp; New Jersey</div>
</div>"""


def logo_html() -> str:
    """Organization logo for Google: the full lockup on its own navy, so it reads on any background."""
    from marketing.brand import lockup
    return BASE + f"""<div style="width:512px;height:512px;display:grid;place-items:center;background:#0A0E1C">
  <div class="lk" style="width:384px">{lockup(cls="logo", pad=0)}</div></div>"""


NODE = """
const { chromium } = require('playwright');
(async () => {
  const jobs = JSON.parse(process.argv[1]);
  const browser = await chromium.launch();
  for (const j of jobs) {
    const page = await browser.newPage({ viewport: { width: j.w, height: j.h }, deviceScaleFactor: 1 });
    await page.goto('file://' + j.html);
    await page.waitForTimeout(300);
    await page.screenshot({ path: j.out });
  }
  await browser.close();
})();
"""


def main() -> int:
    """Renders with the Node Playwright that ships with the machine (require('playwright'))."""
    import json
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        jobs = []
        for name, html, (w, h) in [("og.png", og_html(), (1200, 630)), ("logo.png", logo_html(), (512, 512))]:
            src = Path(tmp) / (name + ".html")
            src.write_text("<!DOCTYPE html><meta charset=utf-8>" + html)
            jobs.append({"html": str(src), "out": str(ROOT / "static" / name), "w": w, "h": h})
        subprocess.run(["node", "-e", NODE, json.dumps(jobs)], check=True, cwd=tmp)
    for j in jobs:
        print("wrote", Path(j["out"]).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
