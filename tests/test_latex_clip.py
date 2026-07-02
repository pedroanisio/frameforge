#!/usr/bin/env python3
"""Regression coverage for TikZ clipping parity with SVG clip paths."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

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


def test_raw_css_circle_clip_path_uses_box_percentages():
    tex = _fig().render({
        "type": "rect",
        "box": [24, 56, 110, 120],
        "fill": "#ffffff",
        "style": {"css": "clip-path: circle(50% at 50% 50%)"},
    })

    assert "\\clip (79,116) circle (55pt);" in tex
    assert tex.index("\\clip") < tex.index("(24,56) rectangle (134,176)")


def test_raw_css_ellipse_clip_path_uses_box_percentages():
    tex = _fig().render({
        "type": "rect",
        "box": [152, 56, 110, 120],
        "fill": "#ffffff",
        "style": {"css": "clip-path: ellipse(48% 32% at 50% 50%)"},
    })

    assert "\\clip (207,116) ellipse (52.8pt and 38.4pt);" in tex


def test_raw_css_inset_clip_path_uses_css_edge_shorthand():
    tex = _fig().render({
        "type": "rect",
        "box": [280, 56, 110, 120],
        "fill": "#ffffff",
        "style": {"css": "clip-path: inset(12% round 16px)"},
    })

    assert "\\clip (293.2,70.4) rectangle (376.8,161.6);" in tex


def test_raw_css_polygon_clip_path_uses_box_percentages():
    tex = _fig().render({
        "type": "rect",
        "box": [408, 56, 110, 120],
        "fill": "#ffffff",
        "style": {"css": "clip-path: polygon(50% 0%, 100% 100%, 0% 100%)"},
    })

    assert "\\clip (463,56) -- (518,176) -- (408,176) -- cycle;" in tex


def test_normalized_clip_path_wins_over_raw_css_clip_path():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 100, 80],
        "fill": "#ffffff",
        "style": {
            "clip_path": {"shape": "inset", "args": {"top": 5, "right": 10, "bottom": 15, "left": 20}},
            "css": "clip-path: circle(50% at 50% 50%)",
        },
    })

    assert "\\clip (20,5) rectangle (90,65);" in tex
    assert "circle" not in tex.split("\\clip", 1)[1].split(";", 1)[0]


def test_path_clip_accepts_svg_quadratic_commands():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 120, 80],
        "fill": "#ffffff",
        "style": {"clip_path": {"shape": "path", "args": {"d": "M 0 80 Q 60 0 120 80 Z"}}},
    })

    assert "\\clip (0,80) .. controls (40,26.667) and (80,26.667) .. (120,80) -- cycle;" in tex
    assert tex.index("\\clip") < tex.index("(0,0) rectangle (120,80)")


def test_path_clip_accepts_svg_arc_commands():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 80, 40],
        "fill": "#ffffff",
        "style": {"clip_path": {"shape": "path", "args": {"d": "M 0 40 A 40 20 0 0 1 80 40 Z"}}},
    })

    assert "\\clip (0,40) .. controls (0,28.954) and (17.909,20) .. (40,20)" in tex
    assert ".. controls (62.091,20) and (80,28.954) .. (80,40) -- cycle;" in tex
    assert tex.index("\\clip") < tex.index("(0,0) rectangle (80,40)")
