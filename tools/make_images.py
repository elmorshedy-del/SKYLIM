#!/usr/bin/env python3
"""Render the social share image and the logo from the brand in data.py.

    python3 tools/make_images.py

Writes static/og.png (1200x630, link previews) and static/logo.png (512x512, the
Organization logo Google may show; it asks for at least 112x112). Re-run after any
change to the brand name. Uses the Playwright Chromium already installed on the machine.
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
*{{margin:0;box-sizing:border-box}}body{{font-family:I,sans-serif;background:#000;color:#fff}}</style>"""


def og_html() -> str:
    b = data.BRAND
    return BASE + f"""<div style="width:1200px;height:630px;padding:72px 80px;display:flex;flex-direction:column;
  justify-content:space-between;background:radial-gradient(120% 90% at 85% 10%,#1f1f1f 0,#000 60%)">
  <div style="display:flex;align-items:center;gap:18px;font-size:34px;font-weight:700;letter-spacing:-.02em">
    <span style="width:60px;height:60px;border-radius:14px;background:#fff;color:#000;display:grid;place-items:center;
      font-size:34px;font-weight:800">{e(b['short'][:1])}</span>{e(b['short'])}</div>
  <div>
    <div style="font-size:22px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#AFAFAF;margin-bottom:24px">
      Chauffeur service · New York City &amp; New Jersey</div>
    <div style="font-size:112px;font-weight:800;letter-spacing:-.05em;line-height:.95">Arrive composed.</div>
  </div>
  <div style="display:flex;gap:36px;font-size:24px;color:#CBCBCB">
    <span>Cadillac Escalade</span><span style="color:#C8B48A">·</span><span>Captain's chairs</span>
    <span style="color:#C8B48A">·</span><span>Onboard Wi-Fi</span><span style="color:#C8B48A">·</span><span>All-inclusive</span>
  </div>
</div>"""


def logo_html() -> str:
    return BASE + f"""<div style="width:512px;height:512px;background:#000;display:grid;place-items:center;
  font-size:300px;font-weight:800;letter-spacing:-.04em">{e(data.BRAND['short'][:1])}</div>"""


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
