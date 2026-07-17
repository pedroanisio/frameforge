#!/usr/bin/env python3
"""Regression coverage for CSS box style fallbacks in TikZ output."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from frameforge.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


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


def test_rect_style_border_dict_feeds_tikz_stroke():
    tex = _fig({
        "panel_style": {
            "background_color": "panel",
            "border": {"width": 2, "style": "dashed", "color": "accent"},
        },
    }).render({
        "type": "rect",
        "box": [10, 20, 80, 40],
        "style": "panel_style",
    })

    assert "draw={rgb,255:red,171;green,205;blue,239}" in tex
    assert "line width=2pt" in tex
    assert "dash pattern=on 4pt off 4pt" in tex


def test_rect_style_border_shorthand_feeds_tikz_stroke():
    tex = _fig().render({
        "type": "rect",
        "box": [10, 20, 80, 40],
        "fill": "panel",
        "style": {"border": "3px dotted accent"},
    })

    assert "draw={rgb,255:red,171;green,205;blue,239}" in tex
    assert "line width=3pt" in tex
    assert "dash pattern=on 1pt off 3pt" in tex


def test_explicit_rect_stroke_overrides_style_border():
    tex = _fig({"panel_style": {"border": {"width": 4, "style": "dashed", "color": "panel"}}}).render({
        "type": "rect",
        "box": [10, 20, 80, 40],
        "fill": "panel",
        "stroke": "accent",
        "stroke_style": {"stroke_width": 1},
        "style": "panel_style",
    })

    assert "draw={rgb,255:red,171;green,205;blue,239}" in tex
    assert "line width=1pt" in tex
    assert "dash pattern=on 4pt off 4pt" not in tex


def test_rect_style_outline_draws_offset_tikz_rect_after_source():
    tex = _fig({
        "panel_style": {
            "background_color": "panel",
            "border_radius": 6,
            "outline": {"width": 3, "style": "dotted", "color": "accent"},
            "outline_offset": 4,
        },
    }).render({
        "type": "rect",
        "box": [10, 20, 80, 40],
        "style": "panel_style",
    })

    source = "(10,20) rectangle (90,60)"
    outline = "(6,16) rectangle (94,64)"
    assert source in tex
    assert outline in tex
    assert tex.index(source) < tex.index(outline)
    assert "fill=none" in tex
    assert "draw={rgb,255:red,171;green,205;blue,239}" in tex
    assert "line width=3pt" in tex
    assert "dash pattern=on 1pt off 3pt" in tex
    assert "rounded corners=10pt" in tex


def test_rect_style_outline_none_does_not_draw_extra_path():
    tex = _fig({"panel_style": {"background_color": "panel", "outline": "none"}}).render({
        "type": "rect",
        "box": [10, 20, 80, 40],
        "style": "panel_style",
    })

    assert "(10,20) rectangle (90,60)" in tex
    assert "fill=none" not in tex
    assert tex.count("rectangle") == 1


def test_box_side_borders_draw_tikz_lines_after_text():
    tex = _fig().render({
        "type": "text",
        "box": [20, 30, 100, 40],
        "text": "side borders",
        "style": {
            "border_top": {"width": 1, "style": "solid", "color": "#111111"},
            "border_right": {"width": 2, "style": "dashed", "color": "#222222"},
            "border_bottom": {"width": 3, "style": "dotted", "color": "#333333"},
            "border_left": {"width": 4, "style": "solid", "color": "#444444"},
        },
    })

    assert "side borders" in tex
    assert "(20,30) -- (120,30)" in tex
    assert "(120,30) -- (120,70)" in tex
    assert "(20,70) -- (120,70)" in tex
    assert "(20,30) -- (20,70)" in tex
    assert "draw={rgb,255:red,17;green,17;blue,17}" in tex
    assert "draw={rgb,255:red,34;green,34;blue,34}" in tex
    assert "draw={rgb,255:red,51;green,51;blue,51}" in tex
    assert "draw={rgb,255:red,68;green,68;blue,68}" in tex
    assert "line width=4pt" in tex
    assert "dash pattern=on 4pt off 4pt" in tex
    assert "dash pattern=on 1pt off 3pt" in tex
