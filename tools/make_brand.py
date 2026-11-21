#!/usr/bin/env python3
"""Outline the logo lettering into SVG paths (no web fonts needed on the site).

    pip install fonttools uharfbuzz
    python3 tools/make_brand.py

Downloads the two open-licence (SIL OFL) fonts named in the logo design — Pinyon Script
for the wordmark, Jost Medium for the tagline — shapes the text with HarfBuzz exactly as
a browser would, and writes:

    static/brand/wordmark.svg   the wordmark, one path, fill = currentColor
    static/brand/tagline.svg    the tagline (letter-spacing 0.46em), one path
    static/brand/monogram.svg   the wordmark's first letter (browser-tab icon)

marketing/brand.py composes these with the SUV drawing into the header mark, the full
lockup (static and animated), and tools/make_images.py into the share image and logo.
Re-run only if the name or tagline lettering changes.
"""
from __future__ import annotations

import re
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import data  # noqa: E402

OUT = ROOT / "static" / "brand"
CSS_API = "https://fonts.googleapis.com/css2?family=Pinyon+Script&family=Jost:wght@500"
WORD_SIZE, TAG_SIZE, TAG_TRACKING = 112.0, 20.0, 0.46     # px and em, from the design file


def fetch_fonts(tmp: Path) -> dict[str, Path]:
    """TrueType files via the Google Fonts CSS API (an old user agent gets .ttf URLs)."""
    req = urllib.request.Request(CSS_API, headers={"User-Agent": "Mozilla/4.0"})
    css = urllib.request.urlopen(req, timeout=30).read().decode()
    out = {}
    for family, url in re.findall(r"font-family: '([^']+)';.*?src: url\((https://[^)]+\.ttf)\)", css, re.S):
        path = tmp / (family.replace(" ", "") + ".ttf")
        path.write_bytes(urllib.request.urlopen(url, timeout=30).read())
        out[family] = path
    return out


def outline(font_path: Path, text: str, size: float, tracking_em: float = 0.0) -> tuple[str, dict]:
    """SVG path data for `text` at `size` px, baseline at y=0, plus metrics (advance, ascent, descent)."""
    import uharfbuzz as hb
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    blob = hb.Blob.from_file_path(str(font_path))
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})

    tt = TTFont(str(font_path))
    upm = tt["head"].unitsPerEm
    scale = size / upm
    glyphs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))   # 0.1 px is plenty
    box = BoundsPen(glyphs)
    x = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        # font units -> px, y flipped (SVG y grows downward)
        matrix = (scale, 0, 0, -scale, x + pos.x_offset * scale, -pos.y_offset * scale)
        glyphs[name].draw(TransformPen(pen, matrix))
        glyphs[name].draw(TransformPen(box, matrix))
        x += pos.x_advance * scale + tracking_em * size
    hhea = tt["hhea"]
    x0, y0, x1, y1 = box.bounds
    return pen.getCommands(), {"advance": round(x, 3), "ascent": hhea.ascent * scale,
                               "descent": -hhea.descent * scale, "size": size,
                               "x0": x0, "y0": y0, "x1": x1, "y1": y1}


def write(name: str, d: str, meta: dict) -> None:
    x0, y0, x1, y1 = meta["x0"], meta["y0"], meta["x1"], meta["y1"]
    meta_attr = " ".join(f'data-{k}="{v:.3f}"' for k, v in meta.items())
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.2f} {y0:.2f} {x1 - x0:.2f} {y1 - y0:.2f}" '
           f'{meta_attr}><path fill="currentColor" d="{d}"/></svg>\n')
    (OUT / name).write_text(svg)
    print(f"wrote static/brand/{name}  {len(svg) / 1024:.1f} KB")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        fonts = fetch_fonts(Path(tmp))
        word, wmeta = outline(fonts["Pinyon Script"], data.BRAND["short"], WORD_SIZE)
        tag, tmeta = outline(fonts["Jost"], data.BRAND["tagline"].upper(), TAG_SIZE, TAG_TRACKING)
        mono, mmeta = outline(fonts["Pinyon Script"], data.BRAND["short"][:1], WORD_SIZE)
    write("wordmark.svg", word, wmeta)
    write("tagline.svg", tag, tmeta)
    write("monogram.svg", mono, mmeta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
