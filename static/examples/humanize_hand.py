#!/usr/bin/env python3
"""Hand-drawn diagram via the seeded humanize 'hand' (roughen + drift + weight + ink).

Renders a small "reColher — cinco gestos" flow the way `build_a6.py` draws by hand,
but reproducibly: the wobble is a document-level `humanize` spec resolved
deterministically at expand() time (same seed → identical output), not a one-off
random pass. Geometry (boxes, connectors, ellipse, triangle, baseline) is converted
to endpoint-anchored hand-drawn polylines; the text stays crisp. One box carries its
own `humanize=` override to show the cascade.

Run from the repository root::

    uv run python static/examples/humanize_hand.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder  # noqa: E402

# The recolher palette (honouring build_a6.py).
BG, INK, MUT, RED, FILL = "#F3EEE4", "#211C16", "#6E6656", "#A6442E", "#E7DFCF"
GESTS = [("01", "Notar"), ("02", "Extrair"), ("03", "Nomear"), ("04", "Aparar")]


def build() -> DocumentBuilder:
    builder = DocumentBuilder(title="reColher — cinco gestos (humanized)",
                              profile="diagram", lang="pt-BR")
    # One seeded hand for the whole page: coherent geometry wobble + a hint of tilt,
    # stroke-weight and ink variation. Deterministic — bump `seed` to re-perform.
    builder.humanize(seed=7, roughen=1.1, drift_deg=0.7, weight=0.16,
                     opacity=0.10, grain=0.5)
    builder.define_text_style("h", font_family=["EB Garamond", "Georgia", "serif"],
                              font_size=22, font_weight=700, color=INK)
    builder.define_text_style("lede", font_family=["EB Garamond", "Georgia", "serif"],
                              font_size=12, italic=True, color=MUT)
    builder.define_text_style("lab", font_family=["EB Garamond", "Georgia", "serif"],
                              font_size=14, color=INK, text_align="center")
    builder.define_text_style("num", font_family=["Inter", "Arial", "sans-serif"],
                              font_size=11, font_weight=700, color=RED)

    W, H = 520, 360
    page = builder.page("gestos", canvas={"size": [W, H], "units": "px"},
                        coordinate_mode="absolute",
                        reading_order=["title", "lede"]).layer("main")
    page.rect([0, 0, W, H], fill=BG, humanize={"enabled": False})  # paper stays crisp
    page.text([36, 30, 448, 28], "Cinco gestos", id="title", style="h")
    page.text([36, 52, 448, 20], "Recolher não é uma fase; é um modo de terminar.",
              id="lede", style="lede")
    page.line([36, 82], [484, 82], stroke=MUT, stroke_style={"stroke_width": 0.9})

    # A row of hand-drawn boxes joined by red connector strokes.
    bw, bh, y = 96, 58, 120
    xs = [36 + i * 118 for i in range(len(GESTS))]
    for i, (num, name) in enumerate(GESTS):
        x = xs[i]
        crisp = name == "Nomear"  # object-level override: draw this one heavier
        page.rect([x, y, bw, bh], id=f"b{i}", fill=FILL, stroke=INK,
                  stroke_style={"stroke_width": 2.4 if crisp else 1.8,
                                "stroke_linejoin": "round"},
                  **({"humanize": {"seed": 7, "roughen": 1.6, "drift_deg": 1.2}}
                     if crisp else {}))
        page.text([x, y + 24, bw, 18], num, style="num")
        page.text([x, y + 40, bw, 18], name, style="lab")
        if i < len(GESTS) - 1:
            page.line([x + bw, y + bh / 2], [x + 118, y + bh / 2], stroke=RED,
                      stroke_style={"stroke_width": 1.8, "stroke_linecap": "round"})

    # The cycle: an organic ring + a returning arrow-ish triangle, a wobbly baseline.
    page.ellipse([150, 250], 84, 46, fill="none", stroke=RED,
                 stroke_style={"stroke_width": 1.8})
    page.text([150 - 84, 244, 168, 18], "um ciclo por obra", style="lede")
    page.polyline([(350, 300), (430, 300), (390, 232), (350, 300)], closed=True,
                  fill=FILL, stroke=INK, stroke_style={"stroke_width": 1.8,
                                                       "stroke_linejoin": "round"})
    page.text([300, 316, 180, 18], "sempre o mesmo, nunca igual", style="lede")
    page.line([36, 332], [230, 332], stroke=INK, stroke_style={"stroke_width": 1.0})
    return builder


def main() -> int:
    from framegraph.sdk import render_page_svgs

    doc = build().build()
    svgs = render_page_svgs(doc)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "humanize_hand.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svgs[0])
    print(f"wrote {out} ({len(svgs)} page)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
