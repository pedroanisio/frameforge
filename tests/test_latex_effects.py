#!/usr/bin/env python3
"""Regression coverage for TikZ approximations of SVG effect surfaces."""
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
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


def test_rect_shadow_draws_translucent_offset_shape_before_rect():
    tex = _fig({"panel": "#ffeecc", "ink": "#123456"}).render({
        "type": "rect",
        "box": [10, 20, 60, 35],
        "radius": 4,
        "fill": "panel",
        "shadow": {"color": "ink", "dx": 2, "dy": 3, "opacity": 0.3, "blur": 6},
    })
    assert tex.index("(12,23) rectangle (72,58)") < tex.index("(10,20) rectangle (70,55)")
    assert "fill={rgb,255:red,18;green,52;blue,86}" in tex
    assert "fill opacity=0.3" in tex
    assert "rounded corners=4pt" in tex


def test_glow_expands_ellipse_behind_source_shape():
    tex = _fig({"brand": "#005c46"}).render({
        "type": "ellipse",
        "center": [120, 30],
        "rx": 28,
        "ry": 18,
        "fill": "brand",
        "glow": {"color": "brand", "blur": 6, "opacity": 0.5},
    })
    assert tex.index("ellipse (31pt and 21pt)") < tex.index("ellipse (28pt and 18pt)")
    assert "fill opacity=0.5" in tex


def test_style_box_shadow_maps_to_latex_shadow_shape():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {
            "box_shadow": [
                {"offset_x": 1, "offset_y": 2, "blur": 3, "color": "#111111", "opacity": 0.25}
            ],
        },
    })
    assert "(1,2) rectangle (21,12)" in tex
    assert "fill opacity=0.25" in tex


def test_text_shadow_draws_offset_text_before_source_text():
    tex = _fig({"ink": "#111111", "shade": "#123456"}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Shadow",
        "style": {
            "font_size": 16,
            "color": "ink",
            "text_shadow": [{"offset_x": 2, "offset_y": 3, "blur": 4, "color": "shade"}],
        },
    })

    shadow = "at (12,38) {Shadow}"
    source = "at (10,35) {Shadow}"
    assert tex.index(shadow) < tex.index(source)
    assert "text={rgb,255:red,18;green,52;blue,86}" in tex
    assert "text opacity=0.45" in tex
    assert "text={rgb,255:red,17;green,17;blue,17}" in tex


def test_text_shadow_applies_to_text_spans():
    tex = _fig({"shade": "#123456"}).render({
        "type": "text",
        "box": [0, 0, 120, 20],
        "spans": [
            {
                "text": "Run",
                "style": {
                    "font_size": 10,
                    "text_shadow": [{"offset_x": 1, "offset_y": 2, "color": "shade"}],
                },
            },
        ],
    })

    assert tex.index("at (1,12) {Run}") < tex.index("at (0,10) {Run}")
    assert "text={rgb,255:red,18;green,52;blue,86}" in tex


def test_text_shadow_uses_transformed_and_decorated_text():
    tex = _fig({"shade": "#123456"}).render({
        "type": "text",
        "box": [0, 0, 120, 20],
        "text": "shadow_text",
        "style": {
            "text_transform": "uppercase",
            "text_decoration": {"line": "underline"},
            "text_shadow": [{"offset_x": 1, "offset_y": 2, "color": "shade"}],
        },
    })

    shadow = "at (1,12) {\\underline{SHADOW\\_TEXT}}"
    source = "at (0,10) {\\underline{SHADOW\\_TEXT}}"
    assert shadow in tex
    assert source in tex
    assert tex.index(shadow) < tex.index(source)
    assert "shadow\\_text" not in tex
