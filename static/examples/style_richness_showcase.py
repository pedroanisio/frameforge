#!/usr/bin/env python3
"""Style & colour richness — effect stack, appearance stack, recolor, guide.

The W4 (#48) surface end to end: an ORDERED effect stack (two shadows + a
glow on one card — the old single fields cannot repeat a kind), a
multi-pass appearance stack (fill + double stroke outline on one geometry),
a `recolor()` before/after pair, and the `chevreul.color_guide()` harmonies
rendered as swatch rows. Writes ``_tmp/style-richness/`` (YAML + SVG). The
MCP run contract is ``build()``; the canonical fixture
``tests/fixtures/style-richness.fg.yaml`` is this document verbatim.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import (  # noqa: E402
    chevreul,
    measure_text,
    recolor,
    render_page_svgs,
    serialize,
)
from frameforge.sdk.model import HEAD_VERSION, validate_document  # noqa: E402

_SANS = ["DejaVu Sans", "Arial", "sans-serif"]


def _label(x, y, text, size=13, weight=400):
    # size the box to the measured single line so nothing wraps/clips — and
    # cover BOTH measurers: real glyph advances (measure_text with fontTools)
    # and the proxy renderer's per-char estimate (0.52·size, ×1.04 bold),
    # which can disagree by a few percent (ADR-0004's measure==render gap)
    est = len(text) * 0.52 * size * (1.04 if weight >= 700 else 1.0)
    w = max(measure_text(text, font_family=_SANS, font_size=size,
                         bold=weight >= 700), est) + 8
    return {"type": "text", "box": [x, y, w, size * 1.4], "text": text,
            "style": {"font_family": _SANS, "font_size": size,
                      "font_weight": weight, "color": "ink",
                      "white_space": "nowrap"}}


def build():
    """MCP contract: the style-richness showcase page."""
    objects = [
        {"type": "rect", "box": [0, 0, 960, 540], "fill": "paper",
         "decorative": True},
        _label(40, 24, "W4 — effect stack · appearance stack · recolor · colour guide",
               18, 700),

        # AI-30: the ORDERED effect stack — two shadows and a glow, repeated
        _label(40, 70, "effects: ordered stack, kinds repeat"),
        {"type": "rect", "id": "fx", "box": [40, 96, 180, 90], "fill": "#dbeafe",
         "radius": 10,
         "effects": [{"kind": "shadow", "dx": 6, "dy": 6, "blur": 8,
                      "opacity": 0.35},
                     {"kind": "glow", "color": "#00b8a9", "blur": 12},
                     {"kind": "shadow", "dx": -3, "dy": -3, "blur": 3,
                      "color": "#7c3aed", "opacity": 0.4}]},

        # AI-32: appearance stack — one geometry, three paint passes
        _label(300, 70, "appearance: three paint passes"),
        {"type": "rect", "id": "passes", "box": [300, 96, 180, 90],
         "radius": 10,
         "appearance": [{"fill": "#dbeafe"},
                        {"stroke": "#1d4ed8",
                         "stroke_style": {"stroke_width": 8}},
                        {"stroke": "#ffffff",
                         "stroke_style": {"stroke_width": 3}}]},

        # AI-16: recolor() — swatches drawn below after the remap
        _label(560, 70, "recolor: rust → violet (tokens + stops)"),

        # AI-18: colour guide harmonies as swatch rows
        _label(40, 240, "chevreul.color_guide('#0f7d88') — the six harmonies",
               13, 700),
    ]
    guide = chevreul.color_guide("#0f7d88")
    y = 266
    for name in sorted(guide):
        objects.append(_label(40, y, name, 11))
        for i, color in enumerate(guide[name]):
            objects.append({"type": "rect", "decorative": True,
                            "box": [190 + i * 44, y - 3, 38, 22],
                            "fill": color, "radius": 4})
        y += 34
    doc = {"dsl": "FrameForge", "version": HEAD_VERSION,
           "title": "style & colour richness showcase", "profile": "diagram",
           "defs": {"tokens": {"colors": {"paper": "#fcfbf8",
                                          "ink": "#1d1e22",
                                          "rust": "#b5642c"}}},
           "pages": [{"mode": "page", "id": "style-richness",
                      "canvas": {"size": [960, 540], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "main", "objects": objects}]}]}
    # the recolor() demo: a rust swatch pair, the right one remapped to violet
    before = [{"type": "rect", "box": [560, 96, 86, 56], "fill": "#b5642c",
               "radius": 6},
              {"type": "rect", "box": [560, 158, 86, 24],
               "fill": {"kind": "linear", "stops": [
                   {"color": "#b5642c", "position": "0%"},
                   {"color": "#fcfbf8", "position": "100%"}]}}]
    probe = recolor(
        {**doc, "pages": [{**doc["pages"][0],
                           "layers": [{"id": "m", "objects": before}]}]},
        {"#b5642c": "#7c3aed"})
    after = probe["pages"][0]["layers"][0]["objects"]
    for obj in after:
        obj["box"] = [obj["box"][0] + 110, *obj["box"][1:]]
    objects.extend(before + after)
    objects.append(_label(560, 196, "before                    after", 11))
    validate_document(doc)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "style-richness")
    os.makedirs(out, exist_ok=True)
    doc = build()
    with open(os.path.join(out, "style-richness.fg.yaml"), "w",
              encoding="utf-8") as fh:
        fh.write(serialize(doc))
    svg = render_page_svgs(doc, base_dir=out)[0]
    with open(os.path.join(out, "style-richness.svg"), "w",
              encoding="utf-8") as fh:
        fh.write(svg)
    print(f"Wrote showcase to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
