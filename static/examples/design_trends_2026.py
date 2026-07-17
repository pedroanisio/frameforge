#!/usr/bin/env python3
"""Compose ONE FrameForge document with the Python SDK that exercises the
document-styling concepts surfaced from current design research:

  type-collage hero (overlapping oversized ghost numerals + a layered display
  headline), a modular bento grid, real gradient paints (linear / radial /
  conic), drop-shadow elevation, a rotate transform, negative letter-spacing
  display type, an italic serif pull-quote, opacity layering, and a full-bleed
  accent strip.

Everything is built through the SDK: DocumentBuilder + PageBuilder primitives,
the layout helpers (row / column / grid / inset), define_color / define_text_style,
then validate_static_rules and serialize().

Run from the repository root::

    uv run python examples/design_trends_2026.py   # build, validate, write the fixture
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
    DocumentBuilder,
    column,
    grid,
    inset,
    row,
    serialize,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

W, H = 900, 1100
CANVAS = {"size": [W, H], "units": "px"}
M = 56  # page margin

COLORS = {
    "ink": "#0b1020", "ink2": "#141a36", "faint": "#1b2347", "line": "#2a325c",
    "sub": "#9aa3c7", "white": "#ffffff",
    "a1": "#ff5e7e", "a2": "#7c5cff", "a3": "#22d3ee", "a4": "#fde047",
}

SANS = ["Inter", "Arial", "sans-serif"]
SERIF = ["Charter", "Georgia", "serif"]

STYLES = {
    # letter-spaced uppercase label
    "kicker":    dict(font_family=SANS, font_size=14, font_weight=700, color="a3",
                      letter_spacing=4, text_transform="uppercase"),
    # oversized display, negative tracking
    "hero":      dict(font_family=SANS, font_size=96, font_weight=800, color="white",
                      letter_spacing=-3, line_height=0.95),
    "heroPink":  dict(font_family=SANS, font_size=96, font_weight=800, color="a1",
                      letter_spacing=-3, line_height=0.95),
    # type-collage ghost layer
    "ghost":     dict(font_family=SANS, font_size=210, font_weight=800, color="faint",
                      line_height=0.9),
    "subdeck":   dict(font_family=SANS, font_size=16, color="sub", line_height=1.55),
    "h":         dict(font_family=SANS, font_size=22, font_weight=800, color="white"),
    "p":         dict(font_family=SANS, font_size=14, color="sub", line_height=1.5),
    # top-line stat number
    "stat":      dict(font_family=SANS, font_size=84, font_weight=800, color="white",
                      letter_spacing=-3),
    "statlabel": dict(font_family=SANS, font_size=13, font_weight=700, color="a3",
                      letter_spacing=2, text_transform="uppercase"),
    "tag":       dict(font_family=SANS, font_size=15, font_weight=600, color="white"),
    "quoteMark": dict(font_family=SERIF, font_size=150, font_weight=800, color="white"),
    "quote":     dict(font_family=SERIF, font_size=21, font_weight=600, color="white",
                      italic=True, line_height=1.3),
    "cite":      dict(font_family=SANS, font_size=13, font_weight=700, color="white",
                      letter_spacing=1),
    "pill":      dict(font_family=SANS, font_size=14, font_weight=800, color="ink",
                      align="center"),
    "swatchcap": dict(font_family=SANS, font_size=12, font_weight=600, color="sub",
                      align="center"),
    "foot":      dict(font_family=SANS, font_size=12, color="sub", letter_spacing=1),
}


def lin(angle, *stops):
    return {"kind": "linear", "angle": angle,
            "stops": [{"color": c, "position": p} for c, p in stops]}


def radial(at, *stops):
    return {"kind": "radial", "at": at,
            "stops": [{"color": c, "position": p} for c, p in stops]}


def conic(*stops):
    return {"kind": "conic",
            "stops": [{"color": c, "position": p} for c, p in stops]}


SHADOW = {"css": "filter: drop-shadow(0 18px 40px rgba(0,0,0,.45))"}


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Document Design Trends 2026", profile="deck", lang="en")
    for name, value in COLORS.items():
        b.define_color(name, value)
    for name, style in STYLES.items():
        b.define_text_style(name, **style)

    page = b.page("design_trends_2026", canvas=CANVAS, coordinate_mode="absolute")

    # ---- background + full-bleed accent strip ---------------------------- #
    page.layer("bg")
    page.rect([0, 0, W, H], fill="ink")
    page.rect([0, 0, 10, H], fill=lin(180, ("a1", "0%"), ("a2", "50%"), ("a3", "100%")))

    # ---- hero: type-collage + layered display headline ------------------- #
    page.layer("hero")
    page.text([470, 56, 720, 260], "2026", style="ghost")               # bleeds off right edge
    page.text([M, 60, 760, 22], "FrameForge · Document Design Trends · 2026",
              style="kicker")
    page.text([M, 150, 800, 120], "Type is the", style="hero")
    page.text([M, 238, 800, 120], "hero.", style="heroPink")
    page.rect([M, 350, 280, 12], radius=6,
              fill=lin(90, ("a1", "0%"), ("a4", "50%"), ("a3", "100%")))
    page.text([M, 384, 720, 70],
              "Letterforms collide, stretch and fill the canvas. Modular bento grids "
              "keep it readable; gradients, glow and a little motion bring the joy.",
              style="subdeck")

    # ---- bento grid ------------------------------------------------------ #
    page.layer("bento")
    region = [M, 470, W - 2 * M, 554]
    left_col, right_col = row(region, gap=28, weights=[1, 1])
    tile_a, tile_b = column(left_col, gap=28, weights=[196, 330])
    tile_c, tile_d = column(right_col, gap=24, weights=[250, 276])

    # Tile A — top-line stat, elevated with a drop-shadow
    page.rect(tile_a, radius=22, fill="ink2", style=SHADOW)
    ax, ay, aw, ah = inset(tile_a, [28])
    page.text([ax, ay, aw, 18], "Modular / Bento", style="statlabel")
    page.text([ax - 4, ay + 18, aw + 4, 110], "73%", style="stat")
    page.text([ax, ay + 128, aw, 40],
              "of new editorial layouts use a modular grid.", style="p")

    # Tile B — "on the rise" trend list with gradient dots
    page.rect(tile_b, radius=22, fill="ink2")
    bx, by, bw, bh = inset(tile_b, [28])
    page.text([bx, by, bw, 28], "On the rise", style="h")
    rows = column([bx, by + 48, bw, bh - 48], count=5, gap=10)
    trends = [("a1", "Type collage"), ("a2", "Anti-design / raw"),
              ("a3", "Oversized display type"), ("a4", "Active white space"),
              ("a1", "Bento modular grids")]
    for (dot, label), rbox in zip(trends, rows):
        rx, ry, rw, rh = rbox
        cy = ry + rh / 2
        page.rect([rx, cy - 7, 14, 14], radius=7, fill=dot)
        page.text([rx + 26, cy - 11, rw - 26, 22], label, style="tag")

    # Tile C — pull-quote on a gradient fill + rotated "NEW" pill
    page.rect(tile_c, radius=22, fill=lin(135, ("a2", "0%"), ("a1", "100%")), style=SHADOW)
    cx, cy, cw, ch = inset(tile_c, [30, 30])
    page.text([cx, cy - 18, 140, 160], "“", style="quoteMark", opacity=0.35)
    page.text([cx, cy + 62, cw - 6, 150],
              "Design feels less concerned with perfection and more interested in presence.",
              style="quote")
    page.text([cx, cy + 208, cw - 10, 20], "— IT'S NICE THAT · TRENDS 2026",
              style="cite")
    pill_cx, pill_cy = tile_c[0] + tile_c[2] - 67, tile_c[1] + 32
    page.rect([pill_cx - 37, pill_cy - 16, 74, 32], radius=16, fill="a4",
              style={"transform": [{"fn": "rotate", "args": [-8]}]})
    page.text([pill_cx - 37, pill_cy - 9, 74, 18], "NEW", style="pill",
              rotation={"angle": -8, "center": [pill_cx, pill_cy]})

    # Tile D — gradient paints: linear / radial / conic
    page.rect(tile_d, radius=22, fill="ink2")
    dx, dy, dw, dh = inset(tile_d, [28])
    page.text([dx, dy, dw, 28], "Gradients & glow", style="h")
    sw = grid([dx, dy + 40, dw, 120], cols=3, count=3, gap=12)
    fills = [lin(90, ("a1", "0%"), ("a2", "100%")),
             radial([50, 40], ("a3", "0%"), ("a2", "100%")),
             conic(("a4", "0%"), ("a1", "100%"))]
    caps = ["linear", "radial", "conic"]
    for box, fill, cap in zip(sw, fills, caps):
        page.rect(box, radius=14, fill=fill)
        page.text([box[0], box[1] + box[3] + 8, box[2], 18], cap, style="swatchcap")
    page.text([dx, dy + 200, dw, 40],
              "Real gradient paints render in the SVG proxy; glow via filters.", style="p")

    # ---- footer ---------------------------------------------------------- #
    page.layer("footer")
    page.rect([M, 1046, W - 2 * M, 2], fill="line")
    page.text([M, 1060, 760, 18],
              "Built with the FrameForge SDK · one composed document · rendered to SVG",
              style="foot")
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "design-trends-2026.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
