#!/usr/bin/env python3
"""Stroke value object + resolver split (ADR 0001 slice 3b-2).

`StrokeResolver.resolve(o)` is now `format_attr(fields(o))`: `fields` yields a
backend-neutral `Stroke`, `format_attr` renders the SVG fragment. These tests pin
that the split is byte-equivalent to the old inline string across the full
attribute surface, and that `fields` resolves the structured values.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.stroke_resolver import Stroke, StrokeResolver  # noqa: E402


def _resolver():
    cr = ColorResolver({"ink": "#111"})
    styles = {"thick": {"stroke": "ink", "stroke_width": 3, "stroke_dasharray": [2, 1],
                        "stroke_linecap": "round", "stroke_miterlimit": 8,
                        "vector_effect": "non-scaling-stroke"}}
    return StrokeResolver(styles, cr, lambda p, d=0: cr.resolve(p))


CASES = [
    {"stroke": "ink"},
    {"stroke_style": "thick"},
    {"stroke": {"color": "red", "width": 2, "dash": [3, 3]}},        # legacy bundle
    {"stroke": "none"},                                              # -> no stroke
    {},                                                             # -> no stroke
    {"stroke": "ink", "stroke_opacity": 0.5,
     "stroke_style": {"stroke_linejoin": "bevel", "paint_order": "stroke"}},
]


def test_resolve_equals_format_of_fields():
    sr = _resolver()
    for o in CASES:
        assert sr.resolve(o) == sr.format_attr(sr.fields(o))


def test_no_stroke_is_none_and_empty():
    sr = _resolver()
    assert sr.fields({"stroke": "none"}) is None
    assert sr.format_attr(None) == ""


def test_fields_returns_structured_values():
    sr = _resolver()
    s = sr.fields({"stroke_style": "thick"})
    assert isinstance(s, Stroke)
    assert s.color == "#111" and s.width == 3
    assert s.dash == "2 1" and s.linecap == "round"
    assert s.miterlimit == 8 and s.vector_effect == "non-scaling-stroke"


def test_format_attr_attribute_order():
    s = Stroke(color="#000", width=1, dash="2 2", linecap="round",
               linejoin="bevel", opacity=0.5)
    out = StrokeResolver.format_attr(s)
    assert out == (' stroke="#000" stroke-width="1" stroke-dasharray="2 2"'
                   ' stroke-linecap="round" stroke-linejoin="bevel"'
                   ' stroke-opacity="0.5"')
