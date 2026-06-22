#!/usr/bin/env python3
"""Regression coverage for named style paint in TikZ output."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

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
