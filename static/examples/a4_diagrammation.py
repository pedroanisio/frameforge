#!/usr/bin/env python3
"""Eight A4 pages, one print identity, eight DIAGRAMMATIONS.

Same exercise as the 16:9 deck, but on portrait A4 (794 x 1123 px @ 96 dpi,
aspect 1 : 1.414). The point: composition variety is not a slide trick — it
re-derives for a tall page. A centered cover, a two-column article, a modular
report grid, a big-number page, a sidebar layout, an image gallery, a vertical
timeline and a data/table page — all the same identity, different structure.

Built with the SDK layout helpers (row / column / grid / inset) plus explicit
boxes; a shared chrome() draws the running footer on every page.

Run from the repository root::

    uv run python examples/a4_diagrammation.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder, column, grid, inset, lorem, row, serialize,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

W, H = 794, 1123  # A4 @ 96 dpi, portrait
CANVAS = {"size": [W, H], "units": "px"}
M = 64

SANS = ["DejaVu Sans", "Arial", "sans-serif"]
SERIF = ["Bitstream Charter", "Noto Serif", "Georgia", "serif"]
MONO = ["DejaVu Sans Mono", "Fira Mono", "monospace"]

COLORS = {
    "paper": "#fbfaf6", "ink": "#1d1e22", "sub": "#6c7077", "accent": "#b5402c",
    "panel": "#ece7dc", "dark": "#1d1e22", "white": "#ffffff", "hair": "#d8d2c4",
}
STYLES = {
    "foot":   dict(font_family=MONO, font_size=10, color="sub", letter_spacing=1),
    "kicker": dict(font_family=SANS, font_size=12, font_weight=700, color="accent",
                   letter_spacing=3, text_transform="uppercase"),
    "kickerC": dict(font_family=SANS, font_size=12, font_weight=700, color="accent",
                    letter_spacing=3, text_transform="uppercase", align="center"),
    "h1":     dict(font_family=SERIF, font_size=82, font_weight=800, color="ink",
                   letter_spacing=-1, line_height=0.98),
    "h1C":    dict(font_family=SERIF, font_size=64, font_weight=800, color="ink",
                   letter_spacing=-1, line_height=1.0, align="center"),
    "h2":     dict(font_family=SERIF, font_size=34, font_weight=800, color="ink",
                   line_height=1.05),
    "h3":     dict(font_family=SERIF, font_size=20, font_weight=800, color="ink"),
    "h3w":    dict(font_family=SERIF, font_size=20, font_weight=800, color="white"),
    "lead":   dict(font_family=SERIF, font_size=19, color="ink", line_height=1.4),
    "leadC":  dict(font_family=SERIF, font_size=18, color="sub", line_height=1.45,
                   align="center"),
    "body":   dict(font_family=SANS, font_size=13.5, color="ink", line_height=1.55),
    "bodysub": dict(font_family=SANS, font_size=13.5, color="sub", line_height=1.55),
    "bodyw":  dict(font_family=SANS, font_size=13.5, color="white", line_height=1.55),
    "big":    dict(font_family=SANS, font_size=230, font_weight=800, color="ink",
                   letter_spacing=-8, line_height=0.9),
    "stat":   dict(font_family=SANS, font_size=52, font_weight=800, color="ink",
                   letter_spacing=-2),
    "num":    dict(font_family=SANS, font_size=15, font_weight=800, color="accent"),
    "quote":  dict(font_family=SERIF, font_size=22, font_weight=600, color="ink",
                   italic=True, line_height=1.35),
    "cap":    dict(font_family=SANS, font_size=11, color="sub", letter_spacing=1),
    "meta":   dict(font_family=SANS, font_size=12, color="ink", line_height=1.5),
    "metah":  dict(font_family=SANS, font_size=10, font_weight=700, color="sub",
                   letter_spacing=2, text_transform="uppercase"),
    "th":     dict(font_family=SANS, font_size=13, font_weight=700, color="white"),
    "td":     dict(font_family=SANS, font_size=13, color="ink"),
}

# Filler text from the SDK's deterministic lorem helper (stable across renders).
LOREM = lorem(sentences=2)
PARA = lorem(sentences=11)


def chrome(b, pid, n, tag):
    page = b.page(pid, canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill="paper")
    page.layer("body")
    page.rect([M, H - 72, W - 2 * M, 1], fill="hair")
    page.text([M, H - 58, 400, 14], "Composition on A4 — a print specimen", style="foot")
    page.text([W - M - 120, H - 58, 120, 14], f"{tag}   ·   p.{n}", style="foot")
    return page


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Composition on A4", profile="report", lang="en")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)

    # 1 — COVER (asymmetric, title in the lower third)
    p = chrome(b, "a1-cover", 1, "COVER")
    p.text([M, 96, W - 2 * M, 18], "Quarterly Review · No. 12 · 2026", style="kicker")
    p.rect([M, 124, W - 2 * M, 2], fill="ink")
    p.rect([M, 678, 240, 12], fill="accent")
    p.text([M, 712, 660, 110], "Composition", style="h1")
    p.text([M, 800, 660, 110], "on A4.", style="h1")
    p.text([M, 944, 600, 90],
           "Eight pages, one identity, eight ways to arrange the same elements on "
           "a tall page.", style="lead")

    # 2 — TWO-COLUMN ARTICLE (heading spans, body in two measures, a pull-quote)
    p = chrome(b, "a2-article", 2, "ARTICLE")
    p.text([M, 96, W - 2 * M, 16], "Pattern 02 — the two-column article", style="kicker")
    p.text([M, 124, W - 2 * M, 48], "The measure of a column.", style="h2")
    p.rect([M, 182, W - 2 * M, 1], fill="hair")
    colw = (W - 2 * M - 42) / 2
    p.text([M, 210, colw, 760], PARA + PARA, style="body")
    p.text([M + colw + 42, 210, colw, 470], PARA, style="body")
    # pull-quote anchored in the lower right column
    p.rect([M + colw + 42, 700, colw, 270], fill="panel", radius=4)
    qx, qy, qw, qh = inset([M + colw + 42, 700, colw, 270], [26])
    p.rect([qx, qy, 40, 5], fill="accent")
    p.text([qx, qy + 22, qw, 200],
           "Set the measure for reading, not for filling the space.", style="quote")

    # 3 — MODULAR REPORT (a header band + a bento of stat tiles + a wide note)
    p = chrome(b, "a3-modular", 3, "REPORT")
    p.text([M, 96, W - 2 * M, 16], "Pattern 03 — modular report", style="kicker")
    p.text([M, 124, W - 2 * M, 48], "Numbers in tiles.", style="h2")
    tiles = grid([M, 210, W - 2 * M, 380], cols=2, count=4, gap=22)
    data = [("Revenue", "+18%"), ("Churn", "2.1%"), ("Margin", "41%"), ("NPS", "62")]
    for bx, (lab, val) in zip(tiles, data):
        x, y, w, h = bx
        p.rect([x, y, w, h], fill="panel", radius=10)
        ix, iy, iw, ih = inset(bx, [26])
        p.text([ix, iy, iw, 16], lab.upper(), style="metah")
        p.text([ix, iy + 26, iw, 70], val, style="stat")
    p.rect([M, 614, W - 2 * M, 356], fill="dark", radius=10)
    nx, ny, nw, nh = inset([M, 614, W - 2 * M, 356], [30])
    p.text([nx, ny, nw, 30], "What the quarter means", style="h3w")
    p.text([nx, ny + 44, nw, 250], PARA, style="bodyw")

    # 4 — BIG NUMBER (one figure dominates, supporting note + source)
    p = chrome(b, "a4-number", 4, "FIGURE")
    p.text([M, 120, W - 2 * M, 16], "Pattern 04 — the figure that leads", style="kicker")
    p.text([M - 10, 230, 720, 280], "42%", style="big")
    p.rect([M, 520, 360, 6], fill="accent")
    p.text([M, 556, 620, 120],
           "of readers never reach the second page — so the first number has to "
           "carry the argument by itself.", style="lead")
    p.text([M, 980, 620, 16], "Source: an illustrative figure for this specimen.",
           style="cap")

    # 5 — SIDEBAR LAYOUT (narrow meta rail + main column)
    p = chrome(b, "a5-sidebar", 5, "SIDEBAR")
    p.text([M, 96, W - 2 * M, 16], "Pattern 05 — sidebar + main", style="kicker")
    p.rect([M, 150, 188, 820], fill="panel", radius=8)
    rows = column([M, 178, 188, 760], count=5, gap=10)
    rail = [("SECTION", "05 / 08"), ("FORMAT", "A4 portrait"),
            ("GRID", "sidebar + col"), ("TYPE", "serif + sans"), ("INK", "1 accent")]
    for bx, (kk, vv) in zip(rows, rail):
        x, y, w, h = bx
        p.text([x + 22, y + 8, w - 36, 14], kk, style="metah")
        p.text([x + 22, y + 30, w - 36, 20], vv, style="meta")
    p.text([300, 150, W - M - 300, 50], "The main column reads beside a fixed rail.",
           style="h2")
    p.text([300, 240, W - M - 300, 730], PARA + PARA + PARA, style="body")

    # 6 — IMAGE GALLERY (a 2x3 grid of figure tiles with caption strips)
    p = chrome(b, "a6-gallery", 6, "GALLERY")
    p.text([M, 96, W - 2 * M, 16], "Pattern 06 — image gallery", style="kicker")
    p.text([M, 124, W - 2 * M, 48], "A grid of figures.", style="h2")
    cells = grid([M, 210, W - 2 * M, 760], cols=2, count=6, gap=20)
    for i, bx in enumerate(cells, 1):
        x, y, w, h = bx
        p.rect([x, y, w, h - 34], fill="panel", radius=8)
        p.rect([x + w / 2 - 18, y + (h - 34) / 2 - 18, 36, 36], radius=18, fill="accent")
        p.text([x, y + h - 26, w, 14], f"Fig. {i} — a placeholder figure.", style="cap")

    # 7 — VERTICAL TIMELINE (a left spine running down the page)
    p = chrome(b, "a7-timeline", 7, "TIMELINE")
    p.text([M, 96, W - 2 * M, 16], "Pattern 07 — vertical timeline", style="kicker")
    p.text([M, 124, W - 2 * M, 48], "A spine down the page.", style="h2")
    spine_x = M + 18
    p.rect([spine_x, 220, 2, 730], fill="ink")
    stops = column([spine_x - 8, 220, 18, 730], count=5)
    for i, bx in enumerate(stops, 1):
        cy = bx[1] + bx[3] / 2
        p.rect([spine_x - 8, cy - 9, 18, 18], radius=9, fill="accent")
        tx = spine_x + 44
        p.text([tx, cy - 30, W - M - tx, 26], f"Phase {i} — a step on the path",
               style="h3")
        p.text([tx, cy + 2, W - M - tx, 60], LOREM, style="bodysub")

    # 8 — DATA / TABLE PAGE
    p = chrome(b, "a8-table", 8, "DATA")
    p.text([M, 96, W - 2 * M, 16], "Pattern 08 — data table", style="kicker")
    p.text([M, 124, W - 2 * M, 48], "Rows and columns.", style="h2")
    b.define_stroke_style("grid", color="hair", width=1)
    p.add({
        "type": "table",
        "box": [M, 210, W - 2 * M, 520],
        "zebra": True, "stroke_style": "grid",
        "row_height": 44, "header_height": 50, "cell_padding": 12,
        "style": {"header_fill": "ink", "header_text": "th", "cell_text": "td"},
        "columns": [
            {"label": "Quarter", "width": "28%", "align": "left"},
            {"label": "Revenue", "width": "24%", "align": "right"},
            {"label": "Margin", "width": "24%", "align": "right"},
            {"label": "NPS", "width": "24%", "align": "right"},
        ],
        "header": ["Quarter", "Revenue", "Margin", "NPS"],
        "rows": [
            ["Q1 2026", "$4.2M", "38%", "54"],
            ["Q2 2026", "$4.8M", "39%", "58"],
            ["Q3 2026", "$5.3M", "40%", "60"],
            ["Q4 2026", "$6.1M", "41%", "62"],
        ],
    })
    p.text([M, 760, W - 2 * M, 16],
           "Table — illustrative quarterly figures for this specimen.", style="cap")
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} A4 pages — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "a4-diagrammation.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
