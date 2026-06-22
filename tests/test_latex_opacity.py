#!/usr/bin/env python3
"""Regression coverage for explicit paint opacity in TikZ output."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig():
    color = ColorResolver({"panel": "#ffeecc", "rule": "#123456"})
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


def test_fill_and_stroke_opacity_fields_emit_tikz_opacity_options():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 40, 20],
        "fill": "panel",
        "fill_opacity": 0.4,
        "stroke": "rule",
        "stroke_opacity": 0.35,
        "stroke_style": {"stroke_width": 2},
    })
    assert "fill opacity=0.4" in tex
    assert "draw opacity=0.35" in tex
    assert "line width=2pt" in tex


def test_style_opacity_fields_apply_to_tikz_paint_options():
    tex = _fig().render({
        "type": "circle",
        "center": [10, 10],
        "r": 5,
        "fill": "#ff0000",
        "stroke": "#0000ff",
        "style": {"fill_opacity": 0.25, "stroke_opacity": 0.75},
    })
    assert "fill opacity=0.25" in tex
    assert "draw opacity=0.75" in tex
