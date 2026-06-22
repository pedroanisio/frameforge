#!/usr/bin/env python3
"""Regression coverage for LaTeX/TikZ stroke geometry parity."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(stroke_styles=None):
    color = ColorResolver({"ink": "#123456"})
    return FigureTikz(color, TextStyleResolver({}, {}, color), stroke_styles or {})


def test_inline_stroke_linejoin_maps_to_tikz_option():
    tex = _fig().render({
        "type": "polyline",
        "points": [[10, 10], [30, 40], [50, 10]],
        "stroke": "ink",
        "stroke_style": {"stroke_width": 4, "stroke_linejoin": "bevel"},
    })

    assert "line join=bevel" in tex
    assert "(10,10) -- (30,40) -- (50,10)" in tex


def test_named_stroke_linejoin_maps_all_supported_values():
    fig = _fig({
        "miter": {"stroke": "ink", "stroke_width": 3, "stroke_linejoin": "miter"},
        "round": {"stroke": "ink", "stroke_width": 3, "stroke_linejoin": "round"},
    })

    miter = fig.render({"type": "polygon", "points": [[0, 0], [20, 30], [40, 0]], "stroke_style": "miter"})
    rounded = fig.render({"type": "polygon", "points": [[0, 0], [20, 30], [40, 0]], "stroke_style": "round"})

    assert "line join=miter" in miter
    assert "line join=round" in rounded
    assert "-- cycle" in miter and "-- cycle" in rounded
