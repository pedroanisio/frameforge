#!/usr/bin/env python3
"""Unit tests for the StyleValues domain service (filter / shadow / transform).

Exercises the CSS/SVG value builders directly, including the injected colour
resolver for drop-shadows, so the logic extracted from the Renderer is verified
independently of it.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.style_values import StyleValues  # noqa: E402

SV = StyleValues(lambda c: {"ink": "#111"}.get(c, c))


def test_length():
    assert SV.length(12) == "12px"
    assert SV.length("auto") == "auto"


def test_filter_value_css_functions():
    out = SV.filter_value([{"fn": "blur", "value": 4}, {"fn": "hue_rotate", "value": 90}], svg_only=False)
    # blur is SVG-backed -> dropped in the CSS (svg_only=False) pass; hue_rotate maps to hue-rotate
    assert out == "hue-rotate(90)"
    svg = SV.filter_value([{"fn": "blur", "value": 4}], svg_only=True)
    assert svg == "blur(4px)"


def test_filter_value_passthrough_string():
    assert SV.filter_value("grayscale(50%)") == "grayscale(50%)"
    assert SV.filter_value("none") == ""


def test_shadow_value_resolves_color():
    s = SV.shadow_value({"offset_x": 2, "offset_y": 3, "blur": 1, "color": "ink"})
    assert s == "2px 3px 1px #111"     # token resolved via injected resolver


def test_drop_shadow_in_filter():
    out = SV.filter_value([{"fn": "drop_shadow", "shadow": {"x": 1, "y": 1, "color": "ink"}}])
    assert out == "drop-shadow(1px 1px 0px #111)"   # blur defaults to 0px


def test_transform_ops_rotate_with_origin():
    out = SV.transform_ops([{"fn": "rotate", "args": [45]}], None, [0, 0, 100, 100])
    assert out == [("rotate", ["45", "50", "50"])]   # origin = box centre


def test_transform_ops_scale_wraps_origin():
    out = SV.transform_ops([{"fn": "scale", "args": [2]}], [10, 20], None)
    assert out == [("translate", ["10", "20"]), ("scale", ["2"]), ("translate", ["-10", "-20"])]


def test_transform_ops_translate_and_string():
    assert SV.transform_ops([{"fn": "translate", "args": [5, 6]}], None, None) == [("translate", ["5", "6"])]
    assert SV.transform_ops("rotate(30deg)", None, None) == [("raw", ["rotate(30)"])]


def test_format_transform_svg_syntax():
    # the SVG backend formats the neutral ops; raw passes through, fns space-join
    from framegraph.rendering.infrastructure.painters.svg import SvgPainter
    assert SvgPainter.format_transform(
        [("translate", ["10", "20"]), ("scale", ["2"])]) == "translate(10 20) scale(2)"
    assert SvgPainter.format_transform([("raw", ["rotate(30)"])]) == "rotate(30)"
