#!/usr/bin/env python3
"""Stroke-outline engine — filled outlines, brushes, kerning (issue #46, W2).

The `sdk.outline` emitter end to end: a constant-width outline with round
joins/caps (AI-48 Outline Stroke), a tapered width profile (AI-12 Width
tool), a calligraphic smooth swash — Catmull-Rom centre-line with pen-angle
width modulation (AI-49, calligraphic half), a scatter brush stamped by arc
length (AI-49, repeat-along-path half), and a headline kerned with explicit
pairs as grammar-native spans (AI-24). Everything lowers to plain ``path``/
``ellipse``/``text`` objects — nothing new enters the schema.

Writes ``_tmp/stroke-outline/`` (YAML + SVG). The MCP run contract is
``build()``; the canonical fixture ``tests/fixtures/stroke-outline.fg.yaml``
is this document verbatim — regenerate it from here, never hand-edit.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import (  # noqa: E402
    kerned_spans,
    render_page_svgs,
    repeat_along_path,
    serialize,
    stroke_outline,
)
from frameforge.sdk.model import HEAD_VERSION, validate_document  # noqa: E402

_SANS = ["DejaVu Sans", "Arial", "sans-serif"]


def build():
    """MCP contract: the outline-engine showcase page."""
    objects = [
        {"type": "rect", "box": [0, 0, 960, 540], "fill": "paper",
         "decorative": True},
        {"type": "text", "box": [40, 24, 880, 30], "text":
         "stroke_outline — one filled-outline emitter: AI-12 · AI-48 · AI-49",
         "style": {"font_family": _SANS, "font_size": 20, "font_weight": 700,
                   "color": "ink"}},
        # AI-48: constant-width outline of a zigzag, round joins + caps
        stroke_outline([(60, 150), (180, 90), (300, 150), (420, 90)],
                       width=18, join="round", cap="round", fill="teal",
                       id="outline-const"),
        # AI-12: width profile — full width tapering to a point
        stroke_outline([(60, 240), (420, 200)], width=26,
                       profile=lambda t: 1.0 - 0.9 * t, fill="rust",
                       id="outline-taper"),
        # AI-49 calligraphic: smooth swash through knots, broad nib at 35°
        stroke_outline([(540, 120), (640, 200), (760, 110), (880, 190)],
                       width=22, pen_angle=35, pen_thin=0.18, smooth=True,
                       join="round", cap="round", fill="ink",
                       id="calligraphic"),
        # AI-49 scatter brush: dots stamped by arc length along a smooth arc
        *repeat_along_path([(60, 340), (240, 300), (420, 360), (600, 310)],
                           spacing=28, smooth=True,
                           stamp={"type": "ellipse", "center": [0, 0],
                                  "rx": 5, "ry": 5, "fill": "teal",
                                  "decorative": True}),
        # AI-24: explicit kern pairs ride in grammar-native span styles
        {"type": "text", "box": [60, 420, 840, 60], "id": "kerned",
         "style": {"font_family": _SANS, "font_size": 44, "font_weight": 700,
                   "color": "ink"},
         "spans": kerned_spans("WAVY TAVERN",
                               pairs={("W", "A"): -3.2, ("A", "V"): -3.0,
                                      ("V", "Y"): -2.4, ("V", "E"): -1.6})},
    ]
    doc = {"dsl": "FrameForge", "version": HEAD_VERSION,
           "title": "stroke-outline engine showcase", "profile": "diagram",
           "defs": {"tokens": {"colors": {"paper": "#fcfbf8",
                                          "ink": "#1d1e22",
                                          "teal": "#0f7d88",
                                          "rust": "#b5642c"}}},
           "pages": [{"mode": "page", "id": "outline-showcase",
                      "canvas": {"size": [960, 540], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "main", "objects": objects}]}]}
    validate_document(doc)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "stroke-outline")
    os.makedirs(out, exist_ok=True)
    doc = build()
    with open(os.path.join(out, "stroke-outline.fg.yaml"), "w",
              encoding="utf-8") as fh:
        fh.write(serialize(doc))
    svg = render_page_svgs(doc, base_dir=out)[0]
    with open(os.path.join(out, "stroke-outline.svg"), "w",
              encoding="utf-8") as fh:
        fh.write(svg)
    print(f"Wrote showcase to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
