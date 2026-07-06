#!/usr/bin/env python3
"""Regression coverage for named style paint in TikZ output."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(styles):
    color = ColorResolver({"panel": "#ffeecc", "hairline": "#123456", "accent": "#abcdef"})
    return FigureTikz(color, TextStyleResolver({}, styles, color), {})


def test_named_style_supplies_vector_fill_and_stroke_geometry():
    tex = _fig({
        "vector_style": {
            "fill": "panel",
            "fill_rule": "evenodd",
            "stroke": "hairline",
            "stroke_width": 3,
            "stroke_dasharray": [5, 2],
            "stroke_dashoffset": 1.5,
            "stroke_linecap": "round",
            "stroke_linejoin": "bevel",
            "stroke_miterlimit": 6,
        },
    }).render({
        "type": "path",
        "d": "M 10 10 L 80 10 L 80 40 L 10 40 Z M 20 20 L 70 20 L 70 30 L 20 30 Z",
        "style": "vector_style",
    })

    assert "fill={rgb,255:red,255;green,238;blue,204}" in tex
    assert "even odd rule" in tex
    assert "draw={rgb,255:red,18;green,52;blue,86}" in tex
    assert "line width=3pt" in tex
    assert "dash pattern=on 5pt off 2pt" in tex
    assert "dash phase=1.5pt" in tex
    assert "line cap=round" in tex
    assert "line join=bevel" in tex
    assert "miter limit=6" in tex


def test_object_paint_overrides_named_style_paint():
    tex = _fig({
        "vector_style": {
            "fill": "panel",
            "stroke": "hairline",
            "stroke_width": 2,
        },
    }).render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "accent",
        "stroke": "#000000",
        "style": "vector_style",
    })

    assert "fill={rgb,255:red,171;green,205;blue,239}" in tex
    assert "fill={rgb,255:red,255;green,238;blue,204}" not in tex
    assert "draw={rgb,255:red,0;green,0;blue,0}" in tex
    assert "line width=2pt" in tex


def test_paint_order_stroke_fill_draws_stroke_before_fill():
    tex = _fig({
        "vector_style": {
            "fill": "panel",
            "stroke": "hairline",
            "stroke_width": 6,
            "paint_order": "stroke fill markers",
        },
    }).render({
        "type": "path",
        "d": "M 10 10 L 80 10 L 80 40 L 10 40 Z",
        "style": "vector_style",
    })

    stroke = "\\path[draw={rgb,255:red,18;green,52;blue,86},line width=6pt]"
    fill = "\\path[fill={rgb,255:red,255;green,238;blue,204}]"
    assert stroke in tex
    assert fill in tex
    assert tex.index(stroke) < tex.index(fill)


def test_default_paint_order_uses_single_fill_and_stroke_path():
    tex = _fig({
        "vector_style": {
            "fill": "panel",
            "stroke": "hairline",
            "stroke_width": 6,
        },
    }).render({
        "type": "path",
        "d": "M 10 10 L 80 10 L 80 40 L 10 40 Z",
        "style": "vector_style",
    })

    combined = (
        "\\path[fill={rgb,255:red,255;green,238;blue,204},"
        "draw={rgb,255:red,18;green,52;blue,86},line width=6pt]"
    )
    assert combined in tex
    assert tex.count("\\path[") == 1


def test_css_rgb_and_rgba_paints_lower_to_xcolor_with_opacity():
    """CSS functional paints (the SDK's rgba() helper emits them) must lower
    like their hex equivalents: inline xcolor expr + decoded fill opacity."""
    from framegraph.rendering.infrastructure.latex.tikz import color_expr

    assert color_expr("rgba(63, 65, 104, 0.45)") == (
        "{rgb,255:red,63;green,65;blue,104}", 0.45)
    assert color_expr("rgb(12, 34, 56)") == (
        "{rgb,255:red,12;green,34;blue,56}", None)

    tex = _fig({}).render({"type": "rect", "box": [0, 0, 10, 10],
                           "fill": "rgba(63,65,104,0.45)"})
    assert "fill={rgb,255:red,63;green,65;blue,104}" in tex
    assert "fill opacity=0.45" in tex
