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


def test_dashoffset_maps_to_tikz_dash_phase():
    tex = _fig().render({
        "type": "line",
        "from": [0, 0],
        "to": [60, 0],
        "stroke": "ink",
        "stroke_style": {"stroke_width": 2, "stroke_dasharray": [10, 8], "stroke_dashoffset": 9},
    })

    assert "dash pattern=on 10pt off 8pt" in tex
    assert "dash phase=9pt" in tex


def test_stroke_miterlimit_maps_to_tikz_miter_limit():
    tex = _fig().render({
        "type": "polyline",
        "points": [[0, 30], [20, 0], [40, 30]],
        "stroke": "ink",
        "stroke_style": {"stroke_width": 6, "stroke_linejoin": "miter", "stroke_miterlimit": 6},
    })

    assert "line join=miter" in tex
    assert "miter limit=6" in tex


def test_legacy_inline_stroke_bundle_maps_to_tikz_stroke_options():
    tex = _fig().render({
        "type": "line",
        "from": [0, 0],
        "to": [50, 0],
        "stroke": {"color": "ink", "width": 4, "dash": [6, 3], "stroke_dashoffset": 2},
    })

    assert "draw={rgb,255:red,18;green,52;blue,86}" in tex
    assert "line width=4pt" in tex
    assert "dash pattern=on 6pt off 3pt" in tex
    assert "dash phase=2pt" in tex


def test_stroke_style_geometry_overrides_legacy_inline_stroke_bundle():
    tex = _fig().render({
        "type": "line",
        "from": [0, 0],
        "to": [50, 0],
        "stroke": {"color": "ink", "width": 4, "dash": [6, 3]},
        "stroke_style": {"stroke_width": 2, "stroke_dasharray": [1, 2]},
    })

    assert "draw={rgb,255:red,18;green,52;blue,86}" in tex
    assert "line width=2pt" in tex
    assert "dash pattern=on 1pt off 2pt" in tex
    assert "line width=4pt" not in tex
    assert "dash pattern=on 6pt off 3pt" not in tex


def test_svg_quadratic_path_commands_convert_to_tikz_cubic_controls():
    tex = _fig().render({
        "type": "path",
        "d": "M 0 0 Q 30 60 60 0 T 120 0",
        "stroke": "ink",
        "fill": "none",
        "stroke_style": {"stroke_width": 2},
    })

    assert "(0,0)" in tex
    assert ".. controls (20,40) and (40,40) .. (60,0)" in tex
    assert ".. controls (80,-40) and (100,-40) .. (120,0)" in tex


def test_svg_smooth_cubic_path_reflects_previous_control_point():
    tex = _fig().render({
        "type": "path",
        "d": "M 0 0 C 10 20 30 20 40 0 S 70 -20 80 0",
        "stroke": "ink",
        "fill": "none",
        "stroke_style": {"stroke_width": 2},
    })

    assert ".. controls (10,20) and (30,20) .. (40,0)" in tex
    assert ".. controls (50,-20) and (70,-20) .. (80,0)" in tex


def test_list_form_quadratic_path_segments_convert_to_tikz_cubic_controls():
    tex = _fig().render({
        "type": "path",
        "d": [["M", 0, 0], ["Q", 30, 60, 60, 0], ["T", 120, 0]],
        "stroke": "ink",
        "fill": "none",
        "stroke_style": {"stroke_width": 2},
    })

    assert ".. controls (20,40) and (40,40) .. (60,0)" in tex
    assert ".. controls (80,-40) and (100,-40) .. (120,0)" in tex


def test_svg_arc_path_command_converts_to_tikz_cubic_controls():
    tex = _fig().render({
        "type": "path",
        "d": "M 0 0 A 50 50 0 0 1 50 50",
        "stroke": "ink",
        "fill": "none",
        "stroke_style": {"stroke_width": 2},
    })

    assert "(0,0)" in tex
    assert ".. controls (27.614,0) and (50,22.386) .. (50,50)" in tex
    assert "-- (50,50)" not in tex


def test_list_form_arc_path_segments_convert_to_tikz_cubic_controls():
    tex = _fig().render({
        "type": "path",
        "d": [["M", 0, 40], ["A", 40, 20, 0, 0, 1, 80, 40], ["Z"]],
        "stroke": "ink",
        "fill": "none",
        "stroke_style": {"stroke_width": 2},
    })

    assert ".. controls (0,28.954) and (17.909,20) .. (40,20)" in tex
    assert ".. controls (62.091,20) and (80,28.954) .. (80,40)" in tex
    assert "-- cycle" in tex
