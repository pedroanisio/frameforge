#!/usr/bin/env python3
"""Regression coverage for TikZ clipping parity with SVG clip paths."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(colors=None):
    color = ColorResolver(colors or {})
    return FigureTikz(
        color,
        TextStyleResolver({}, {}, color),
        {},
        asset_path=lambda src: f"assets/{src}.png" if src else None,
    )


def test_image_ellipse_clip_wraps_includegraphics():
    tex = _fig().render({
        "type": "image",
        "box": [20, 10, 64, 48],
        "src": "avatar",
        "clip": {"shape": "ellipse"},
    })

    assert "\\clip (52,34) ellipse (32pt and 24pt);" in tex
    assert tex.index("\\clip") < tex.index("\\includegraphics")
    assert r"\includegraphics[width=64pt,height=48pt,keepaspectratio]{\detokenize{assets/avatar.png}}" in tex


def test_image_string_circle_clip_uses_box_center():
    tex = _fig().render({
        "type": "image",
        "box": [10, 20, 40, 60],
        "src": "avatar",
        "clip": "circle",
    })

    assert "\\clip (30,50) circle (20pt);" in tex


def test_style_clip_path_shapes_wrap_vector_objects():
    tex = _fig({"panel": "#ffeecc"}).render({
        "type": "group",
        "children": [
            {
                "type": "rect",
                "box": [10, 10, 80, 60],
                "fill": "panel",
                "style": {"clip_path": {"shape": "inset", "args": {"top": 5, "right": 10, "bottom": 15, "left": 20}}},
            },
            {
                "type": "circle",
                "center": [130, 40],
                "r": 30,
                "fill": "panel",
                "style": {"clip_path": {"shape": "polygon", "args": {"points": [[100, 10], [160, 10], [130, 70]]}}},
            },
            {
                "type": "path",
                "d": "M 10 90 L 80 90 L 45 115 Z",
                "fill": "panel",
                "style": {"clip_path": {"shape": "path", "args": {"d": "M 10 85 L 90 85 L 50 120 Z"}}},
            },
        ],
    })

    assert "\\clip (30,15) rectangle (80,55);" in tex
    assert "\\clip (100,10) -- (160,10) -- (130,70) -- cycle;" in tex
    assert "\\clip (10,85) -- (90,85) -- (50,120) -- cycle;" in tex
    assert tex.index("\\clip (30,15) rectangle (80,55);") < tex.index("(10,10) rectangle (90,70)")
    assert tex.index("\\clip (100,10) -- (160,10) -- (130,70) -- cycle;") < tex.index("(130,40) circle")
