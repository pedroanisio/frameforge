#!/usr/bin/env python3
"""Regression: TikZ figures must render linear-gradient fills, not flat blocks.

`ColorResolver` collapses a paint object to its first stop, so a multi-stop
gradient rect used to fill as a single solid colour (the spectrum figure in
b1/chroma-styling-showcase rendered as a magenta block). The TikZ backend now
emits one two-color `\\shade` segment per consecutive stop pair along the
gradient axis.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fixture_path(*parts):
    root_path = os.path.join(ROOT, "fixtures", *parts)
    if os.path.exists(root_path):
        return root_path
    return os.path.join(ROOT, "examples", "fixtures", *parts)


def _fig():
    color = ColorResolver({})
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


def _rect(stops, angle="90deg"):
    return {"type": "rect", "box": [0, 0, 300, 100],
            "fill": {"kind": "linear", "angle": angle, "stops": stops}}


def test_horizontal_gradient_emits_piecewise_left_right_shades():
    tex = _fig().render(_rect([
        {"color": "#ff0000", "position": "0%"},
        {"color": "#00ff00", "position": "50%"},
        {"color": "#0000ff", "position": "100%"},
    ]))
    assert tex.count("\\shade[") == 2          # 3 stops -> 2 segments
    assert "left color=" in tex and "right color=" in tex
    assert "top color=" not in tex             # 90deg is horizontal
    assert "fill={rgb" not in tex              # not collapsed to a flat fill
    # endpoint colours are shared between adjacent segments (continuous)
    assert tex.count("green,255") >= 2         # the mid stop appears on both segments


def test_vertical_gradient_uses_top_bottom_shades():
    tex = _fig().render(_rect([
        {"color": "#000000", "position": "0%"},
        {"color": "#ffffff", "position": "100%"},
    ], angle="180deg"))
    assert tex.count("\\shade[") == 1
    assert "top color=" in tex and "bottom color=" in tex
    assert "left color=" not in tex


def test_style_background_image_gradient_emits_piecewise_shades():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 300, 100],
        "style": {
            "background_image": {
                "kind": "linear",
                "angle": "90deg",
                "stops": [
                    {"color": "#ff0000", "position": "0%"},
                    {"color": "#00ff00", "position": "50%"},
                    {"color": "#0000ff", "position": "100%"},
                ],
            },
        },
    })

    assert tex.count("\\shade[") == 2
    assert "left color=" in tex and "right color=" in tex
    assert "fill={rgb" not in tex


def test_radial_gradient_rect_emits_clipped_inner_outer_shade():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 300, 100],
        "fill": {
            "kind": "radial",
            "shape": "ellipse",
            "at": "center",
            "stops": [
                {"color": "#ff0000", "position": "0%"},
                {"color": "#0000ff", "position": "100%"},
            ],
        },
    })

    assert tex.count("\\shade[") == 1
    assert "\\clip (0,0) rectangle (300,100);" in tex
    assert "inner color={rgb,255:red,255;green,0;blue,0}" in tex
    assert "outer color={rgb,255:red,0;green,0;blue,255}" in tex
    assert "(150,50) ellipse (150pt and 50pt)" in tex
    assert "fill={rgb" not in tex


def test_radial_gradient_at_local_point_uses_box_relative_center():
    tex = _fig().render({
        "type": "rect",
        "box": [10, 20, 100, 80],
        "fill": {
            "kind": "radial",
            "shape": "circle",
            "at": [20, 20],
            "stops": [
                {"color": "#ffffff", "position": "0%"},
                {"color": "#000000", "position": "100%"},
            ],
        },
    })

    assert "\\clip (10,20) rectangle (110,100);" in tex
    assert "(30,40) ellipse (80pt and 80pt)" in tex


def test_style_background_image_radial_gradient_emits_shade():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 100, 100],
        "style": {
            "background_image": {
                "kind": "radial",
                "stops": [
                    {"color": "#ffffff", "position": "0%"},
                    {"color": "#000000", "position": "100%"},
                ],
            },
        },
    })

    assert "\\shade[inner color=" in tex
    assert "fill={rgb" not in tex


def test_object_fill_overrides_style_background_image_gradient():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 300, 100],
        "fill": "#123456",
        "style": {
            "background_image": {
                "kind": "linear",
                "stops": [
                    {"color": "#ff0000", "position": "0%"},
                    {"color": "#0000ff", "position": "100%"},
                ],
            },
        },
    })

    assert "\\shade[" not in tex
    assert "fill={rgb,255:red,18;green,52;blue,86}" in tex


def test_transparent_stop_falls_back_to_solid_fill():
    # an rgba(...,0) fade has no opaque hex: keep the old solid behavior, no crash
    tex = _fig().render(_rect([
        {"color": "#ff2d95", "position": "0%"},
        {"color": "rgba(255,45,149,0)", "position": "100%"},
    ]))
    assert "\\shade[" not in tex
    assert "fill={rgb,255:red,255;green,45;blue,149}" in tex   # first stop, solid


def test_axis_aligned_gradient_stroke_line_emits_shaded_stroke_rectangles():
    tex = _fig().render({
        "type": "line",
        "from": [10, 20],
        "to": [110, 20],
        "stroke": {
            "kind": "linear",
            "angle": "90deg",
            "stops": [
                {"color": "#ff0000", "position": "0%"},
                {"color": "#00ff00", "position": "50%"},
                {"color": "#0000ff", "position": "100%"},
            ],
        },
        "stroke_style": {"stroke_width": 10},
    })
    assert tex.count("\\shade[") == 2
    assert "(10,15) rectangle (60,25)" in tex
    assert "(60,15) rectangle (110,25)" in tex
    assert "\\draw[draw={rgb" not in tex


def test_diagonal_gradient_stroke_line_falls_back_to_solid_stroke():
    tex = _fig().render({
        "type": "line",
        "from": [10, 20],
        "to": [110, 80],
        "stroke": {
            "kind": "linear",
            "stops": [
                {"color": "#ff0000", "position": "0%"},
                {"color": "#0000ff", "position": "100%"},
            ],
        },
        "stroke_style": {"stroke_width": 4},
    })
    assert "\\shade[" not in tex
    assert "\\draw[draw={rgb,255:red,255;green,0;blue,0}" in tex


def test_b1_chroma_spectrum_renders_as_gradient():
    from framegraph.rendering.infrastructure.latex import transpile
    doc = json.load(open(_fixture_path("b1", "chroma-styling-showcase.fg.json"), encoding="utf-8"))
    tex = transpile(doc)
    # the 7-stop spectrum -> 6 horizontal segments (plus the other gradients)
    assert tex.count("\\shade[left color=") >= 6
