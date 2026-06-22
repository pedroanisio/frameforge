#!/usr/bin/env python3
"""Regression coverage for CSS box style fallbacks in TikZ output."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(styles=None):
    color = ColorResolver({"panel": "#ffeecc", "accent": "#abcdef"})
    return FigureTikz(color, TextStyleResolver({}, styles or {}, color), {})


def test_rect_style_background_color_and_border_radius_feed_tikz_shape():
    tex = _fig({"panel_style": {"background_color": "panel", "border_radius": 6}}).render({
        "type": "rect",
        "box": [10, 20, 80, 40],
        "style": "panel_style",
    })

    assert "fill={rgb,255:red,255;green,238;blue,204}" in tex
    assert "rounded corners=6pt" in tex
    assert "(10,20) rectangle (90,60)" in tex


def test_rect_object_fill_and_radius_override_style_box_fallbacks():
    tex = _fig({"panel_style": {"background_color": "panel", "border_radius": 6}}).render({
        "type": "rect",
        "box": [10, 20, 80, 40],
        "fill": "accent",
        "radius": 3,
        "style": "panel_style",
    })

    assert "fill={rgb,255:red,171;green,205;blue,239}" in tex
    assert "fill={rgb,255:red,255;green,238;blue,204}" not in tex
    assert "rounded corners=3pt" in tex
    assert "rounded corners=6pt" not in tex
