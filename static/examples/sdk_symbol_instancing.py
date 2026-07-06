#!/usr/bin/env python3
"""Symbol instancing & object-level effects — the SDK affordances for repeated detail.

A small, self-contained reference for two SDK ergonomics:

* **Author a detailed motif once, instance it many times.** ``define_symbol``
  registers a motif in ``defs.symbols``; ``page.use(symbol, box, params=...)``
  stamps it at any box, substituting ``$param`` placeholders per instance. The
  emblem below is authored *once* and stamped eight times in eight colours — the
  geometry is not re-emitted per position, which is the cure for the
  "redraw the motif from N primitives every call" bloat.
* **Attach glows/shadows safely.** ``effects(glow=..., shadow=...)`` returns the
  object-level fields these belong on, so a glow can never be swallowed by a
  stroke helper that merges into ``stroke_style``.

Run from the repository root::

    uv run python examples/sdk_symbol_instancing.py            # build + validate + write YAML
    uv run python examples/sdk_symbol_instancing.py --render   # also rasterise to out/symbols/
"""
from __future__ import annotations

import argparse
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    effects,
    glow,
    grid,
    serialize,
    shadow,
    stroke,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 900, 540
CANVAS = {"size": [W, H], "units": "px"}

INK = "#0b1020"
PAPER = "#f6f7fb"
MUTE = "#5b6678"

# Eight accents the *single* emblem symbol is instanced in.
ACCENTS = ["#e8743b", "#3aa0d8", "#7c5c8e", "#2bb673",
           "#d83b6a", "#f2a73b", "#2563eb", "#0f766e"]


def _star_points(cx: float, cy: float, r_out: float, r_in: float, n: int,
                 rotation: float = -90.0) -> list[list[float]]:
    """Closed-polyline vertices for an ``n``-pointed star (first point at ``rotation``)."""
    pts: list[list[float]] = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rotation + i * 180.0 / n)
        pts.append([round(cx + r * math.cos(a), 2), round(cy + r * math.sin(a), 2)])
    return pts


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="SDK Symbol Instancing & Effects", profile="deck", lang="en")

    # --- the motif, authored exactly once ---------------------------------- #
    # Box-less primitives (ellipse/polyline) so each stamped instance is a clean
    # group with no internal box-overlap to police. ``$accent`` is substituted
    # per instance; the star carries an object-level glow (what effects() emits).
    emblem = b.define_symbol(
        "emblem",
        box=[0, 0, 100, 100],
        objects=[
            {"type": "ellipse", "center": [50, 50], "rx": 46, "ry": 46, "fill": "none",
             "stroke": "$accent", "stroke_style": {"stroke_width": 3}},
            {"type": "polyline", "points": _star_points(50, 50, 30, 13, 5), "closed": True,
             "fill": "$accent", "glow": {"blur": 4, "color": "#ffffff", "opacity": 0.5}},
            {"type": "ellipse", "center": [50, 50], "rx": 6, "ry": 6, "fill": PAPER},
        ],
    )

    page = b.page("main", canvas=CANVAS, coordinate_mode="absolute").layer("art")
    page.rect([0, 0, W, H], fill=PAPER)
    with page.grouped(meta={"role": "labels"}) as labels:
        labels.text([48, 36, W - 96, 30], "One symbol, eight instances",
                    style={"font_family": ["DejaVu Sans"], "font_size": 24,
                           "font_weight": 700, "color": INK})
        labels.text([48, 70, W - 96, 22],
                    "define_symbol(...) once → page.use(...) per cell, recoloured via params",
                    style={"font_family": ["DejaVu Sans Mono"], "font_size": 13, "color": MUTE})

    # --- stamp the one motif across a grid, recolouring per cell ----------- #
    cells = grid([48, 116, W - 96, 280], cols=4, rows=2, gap=18)
    for cell, accent in zip(cells, ACCENTS):
        x, y, cw, ch = cell
        side = min(cw, ch)
        box = [x + (cw - side) / 2, y + (ch - side) / 2, side, side]
        page.use(emblem, box, params={"accent": accent})

    # --- effects() splat point: glow + shadow on object-level fields -------- #
    with page.grouped(meta={"role": "labels"}) as labels:
        labels.text([48, 430, W - 96, 22], "effects(glow=…, shadow=…) — object-level, never lost in stroke_style",
                    style={"font_family": ["DejaVu Sans Mono"], "font_size": 13, "color": MUTE})
    swatch = grid([48, 462, 360, 56], cols=3, rows=1, gap=18)
    for (sx, sy, sw, sh), accent in zip(swatch, ACCENTS):
        cx, cy = sx + sw / 2, sy + sh / 2
        page.ellipse([cx, cy], 22, 22, fill=accent,
                     **stroke(2, color="#ffffff"),
                     **effects(glow=glow(blur=10, color=accent, opacity=0.6),
                               shadow=shadow(dy=3, blur=6, color=INK, opacity=0.35)))
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="rasterise to out/symbols/")
    args = ap.parse_args()

    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in report.issues[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    out = os.path.join(ROOT, "tests", "fixtures", "sdk-symbol-instancing.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")

    if args.render:
        os.system(f"cd {ROOT} && python3 tooling/render_fixtures.py "
                  f"tests/fixtures/sdk-symbol-instancing.fg.yaml --out out/symbols")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
