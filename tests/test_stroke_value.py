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
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge.rendering.domain.services.stroke_resolver import Markers, Stroke, StrokeResolver  # noqa: E402
from frameforge.rendering.infrastructure.painters.svg import SvgPainter  # noqa: E402


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


def test_width_none_omits_attr():
    # Bare-colour strokes (e.g. ' stroke="#bbb"') carry no width — format_attr
    # must omit stroke-width so such literals round-trip byte-for-byte.
    assert StrokeResolver.format_attr(Stroke(color="#bbb")) == ' stroke="#bbb"'
    assert StrokeResolver.format_attr(Stroke(color="#ccc", dash="3 3")) == (
        ' stroke="#ccc" stroke-dasharray="3 3"')


def test_resolver_strokes_always_have_width():
    sr = _resolver()
    assert sr.fields({"stroke": "ink"}).width == 1.0


def test_format_attr_attribute_order():
    s = Stroke(color="#000", width=1, dash="2 2", linecap="round",
               linejoin="bevel", opacity=0.5)
    out = StrokeResolver.format_attr(s)
    assert out == (' stroke="#000" stroke-width="1" stroke-dasharray="2 2"'
                   ' stroke-linecap="round" stroke-linejoin="bevel"'
                   ' stroke-opacity="0.5"')


def test_marker_attrs_formats_and_registers():
    # The neutral Markers value object formats to SVG marker refs and registers
    # one <marker> def per (kind, colour), deduped — reproducing the old inline
    # _arrow_attrs output.
    p = SvgPainter(ColorResolver({}))
    p.new_page()
    out = p._marker_attrs(Markers(color="#000", start=True, end=True))
    assert out == ' marker-start="url(#ah1)" marker-end="url(#ah1)"'  # deduped to one id
    assert p._marker_attrs(None) == ""


def test_markers_none_when_no_arrow():
    sr = _resolver()
    assert sr.arrow_spec({"stroke": "ink"}) is None
