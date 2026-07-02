#!/usr/bin/env python3
"""Nine slides, one identity, nine DIAGRAMMATIONS.

The previous decks varied skin (palette / type / shape) but kept a single
composition. This deck pins ONE identity (same paper, ink, accent, fonts) and
varies the *structure* of each slide, so composition is the only variable:

  1. Centered / symmetric        — everything on the vertical axis
  2. Left rail + content         — asymmetric sidebar carries the title
  3. Full-bleed split            — 50/50 colour field vs text
  4. Bento / modular             — tiles of deliberately unequal size
  5. Big-number focal            — one figure dominates, notes orbit it
  6. Three columns               — equal thirds (row of columns)
  7. Timeline band               — a horizontal spine with nodes
  8. Corner-anchored / diagonal  — tension, off-canvas bleed, no centre
  9. Quadrants (2x2)             — a balanced grid of four

Composition is computed with the SDK layout helpers (row / column / grid /
inset) plus explicit boxes where a pattern wants exact tension.

Run from the repository root::

    uv run python examples/slide_diagrammation.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder, column, grid, inset, lorem, row, serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
M = 64

SANS = ["DejaVu Sans", "Arial", "sans-serif"]
SERIF = ["Bitstream Charter", "Noto Serif", "Georgia", "serif"]
MONO = ["DejaVu Sans Mono", "Fira Mono", "monospace"]

COLORS = {
    "paper": "#f7f4ee", "ink": "#17181c", "sub": "#6b6f76", "accent": "#2f5bea",
    "accent2": "#ff5a3c", "panel": "#e7e3d8", "dark": "#14151c", "white": "#ffffff",
}
STYLES = {
    "tag":     dict(font_family=MONO, font_size=12, font_weight=700, color="sub",
                    letter_spacing=1, text_transform="uppercase"),
    "kicker":  dict(font_family=SANS, font_size=14, font_weight=700, color="accent",
                    letter_spacing=3, text_transform="uppercase"),
    "kickerC": dict(font_family=SANS, font_size=14, font_weight=700, color="accent",
                    letter_spacing=3, text_transform="uppercase", align="center"),
    "h1":      dict(font_family=SERIF, font_size=60, font_weight=800, color="ink",
                    letter_spacing=-1, line_height=1.0),
    "h1C":     dict(font_family=SERIF, font_size=60, font_weight=800, color="ink",
                    letter_spacing=-1, line_height=1.0, align="center"),
    "h2":      dict(font_family=SERIF, font_size=30, font_weight=800, color="ink"),
    "h2w":     dict(font_family=SERIF, font_size=40, font_weight=800, color="white"),
    "big":     dict(font_family=SANS, font_size=240, font_weight=800, color="ink",
                    letter_spacing=-8, line_height=0.9),
    "idx":     dict(font_family=SANS, font_size=170, font_weight=800, color="panel",
                    line_height=0.9),
    "lead":    dict(font_family=SANS, font_size=20, color="ink", line_height=1.45),
    "leadC":   dict(font_family=SANS, font_size=19, color="sub", line_height=1.5,
                    align="center"),
    "body":    dict(font_family=SANS, font_size=16, color="sub", line_height=1.5),
    "bodyw":   dict(font_family=SANS, font_size=17, color="white", line_height=1.5),
    "num":     dict(font_family=SANS, font_size=20, font_weight=800, color="accent"),
    "chip":    dict(font_family=SANS, font_size=14, font_weight=700, color="white",
                    align="center"),
}

# Neutral filler from the SDK helper, so structure (not copy) is what varies.
LOREM = lorem(sentences=2)


def slide(b, sid, pattern, bg="paper"):
    page = b.page(sid, canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill=bg)
    page.layer("body")
    page.text([M, H - 44, W - 2 * M, 16], f"DIAGRAMMATION — {pattern}", style="tag")
    return page


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Nine Diagrammations", profile="deck", lang="en")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)

    # 1 — CENTERED / SYMMETRIC
    p = slide(b, "d1-centered", "centered / symmetric")
    p.text([0, 210, W, 22], "Pattern 01", style="kickerC")
    p.text([0, 248, W, 80], "On the axis.", style="h1C")
    p.rect([W / 2 - 60, 360, 120, 4], fill="accent")
    p.text([W / 2 - 320, 392, 640, 80], LOREM, style="leadC")

    # 2 — LEFT RAIL + CONTENT
    p = slide(b, "d2-rail", "left rail + content")
    p.rect([0, 0, 440, H], fill="dark")
    p.text([M, 150, 312, 20], "Pattern 02", style="kicker")
    p.text([M, 188, 312, 200], "A sidebar carries the frame.", style="h2w")
    p.text([M, 470, 312, 120], LOREM, style="bodyw")
    items = column([504, 150, 712, 420], count=4, gap=18)
    for i, bx in enumerate(items, 1):
        x, y, w, h = bx
        p.rect([x, y, w, h], fill="panel", radius=10)
        p.text([x + 22, y + h / 2 - 16, 40, 24], f"0{i}", style="num")
        p.text([x + 80, y + h / 2 - 14, w - 110, 24],
               "A content row placed by column() — equal, rhythmic.", style="body")

    # 3 — FULL-BLEED SPLIT
    p = slide(b, "d3-split", "full-bleed split")
    p.rect([0, 0, 600, H], fill="accent")
    p.text([M, 120, 480, 18], "Pattern 03", style="kicker")
    p.text([M, 300, 480, 160], "Half colour,\nhalf argument.", style="h2w")
    p.rect([640, 0, W - 640, H], fill="paper")
    p.text([700, 150, 500, 20], "THE RIGHT FIELD", style="kicker")
    p.text([700, 188, 500, 300],
           LOREM + " " + LOREM, style="lead")

    # 4 — BENTO / MODULAR (deliberately unequal tiles)
    p = slide(b, "d4-bento", "bento / modular")
    p.text([M, 90, 600, 20], "Pattern 04 — unequal tiles", style="kicker")
    p.rect([M, 140, 560, 500], fill="dark", radius=18)
    p.text([M + 32, 180, 480, 40], "Feature", style="h2w")
    p.text([M + 32, 560, 480, 60], LOREM, style="bodyw")
    p.rect([648, 140, 280, 240], fill="accent", radius=18)
    p.rect([944, 140, 272, 240], fill="panel", radius=18)
    p.rect([648, 400, 568, 240], fill="accent2", radius=18)
    p.text([680, 440, 500, 40], "A wide tile, a different weight", style="h2w")

    # 5 — BIG-NUMBER FOCAL
    p = slide(b, "d5-number", "big-number focal")
    p.text([M, 130, 600, 20], "Pattern 05", style="kicker")
    p.text([M - 8, 200, 720, 260], "87", style="big")
    p.rect([M, 470, 360, 4], fill="accent")
    p.text([M, 500, 420, 60], "of attention lands where the layout sends it.", style="lead")
    notes = column([820, 200, 396, 360], count=3, gap=24)
    for bx, t in zip(notes, ["Scale is hierarchy.", "Whitespace is emphasis.",
                             "Position is meaning."]):
        x, y, w, h = bx
        p.text([x, y, w, 26], t, style="h2")
        p.text([x, y + 34, w, 60], LOREM, style="body")

    # 6 — THREE COLUMNS (row of equal thirds)
    p = slide(b, "d6-thirds", "three columns")
    p.text([M, 110, 600, 20], "Pattern 06 — equal thirds", style="kicker")
    cols = row([M, 170, W - 2 * M, 460], count=3, gap=32)
    heads = ["First", "Second", "Third"]
    for bx, head in zip(cols, heads):
        x, y, w, h = bx
        p.rect([x, y, w, h], fill="panel", radius=14)
        ix, iy, iw, ih = inset(bx, [28])
        p.rect([ix, iy, 40, 6], fill="accent")
        p.text([ix, iy + 22, iw, 40], head, style="h2")
        p.text([ix, iy + 70, iw, 300], LOREM + " " + LOREM, style="body")

    # 7 — TIMELINE BAND
    p = slide(b, "d7-timeline", "timeline band")
    p.text([M, 120, 600, 20], "Pattern 07 — a horizontal spine", style="kicker")
    p.rect([M, 372, W - 2 * M, 3], fill="ink")
    nodes = row([M, 360, W - 2 * M, 28], count=5)
    for i, bx in enumerate(nodes):
        cx = bx[0] + bx[2] / 2
        p.rect([cx - 9, 363, 18, 18], radius=9, fill="accent")
        above = i % 2 == 0
        # title is 30px serif; give the caption ~46px of clearance so the title's
        # descenders never meet the caption's first line (was 30 -> overlap).
        ty = 236 if above else 410
        p.text([cx - 90, ty, 180, 34], f"Phase {i + 1}", style="h2")
        p.text([cx - 90, ty + 46, 180, 60], "A short beat on the spine.", style="body")

    # 8 — CORNER-ANCHORED / DIAGONAL
    p = slide(b, "d8-corner", "corner-anchored / diagonal", bg="dark")
    p.text([M, 70, 400, 180], "08", style="idx")
    p.rect([W - 360, -120, 520, 360], fill="accent",
           style={"transform": [{"fn": "rotate", "args": [18]}]})
    p.rect([W - 250, 300, 360, 360], radius=24, fill="accent2",
           style={"transform": [{"fn": "rotate", "args": [-10]}]})
    p.text([M, H - 250, 560, 60], "Tension over\nthe corner.", style="h2w")
    p.text([M, H - 120, 520, 60], LOREM, style="bodyw")

    # 9 — QUADRANTS (2x2)
    p = slide(b, "d9-quadrants", "quadrants / 2x2")
    p.text([M, 90, 600, 20], "Pattern 09 — four equal fields", style="kicker")
    quads = grid([M, 140, W - 2 * M, 500], cols=2, count=4, gap=24)
    labels = [("North", "accent"), ("East", "dark"), ("South", "accent2"), ("West", "ink")]
    for bx, (name, col) in zip(quads, labels):
        x, y, w, h = bx
        p.rect([x, y, w, h], fill="panel", radius=14)
        p.rect([x, y, 8, h], fill=col)
        p.text([x + 30, y + 26, w - 60, 32], name, style="h2")
        p.text([x + 30, y + 72, w - 60, 80], LOREM, style="body")

    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} slides — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "slide-diagrammation.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
