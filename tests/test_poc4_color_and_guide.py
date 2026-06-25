#!/usr/bin/env python3
"""POC-04 — colour/gradient a trace, or use it as a guide to draw on top.

The colour transforms (recolor_cycle / gradient_fills / as_guide / hexshift) and
the page builder are deterministic and OpenCV-free, so they unit-test directly;
only the raster ``trace`` needs the vision group.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "examples"))

from poc4_color_and_guide import (  # noqa: E402
    as_guide,
    author_overlay,
    build_color_and_guide,
    gradient_count,
    gradient_fills,
    hexshift,
    recolor_cycle,
)


def _regions():
    return [
        {"type": "polygon", "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]], "fill": "#3366CC"},
        {"type": "polygon", "points": [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0]], "fill": "#CC3333"},
        {"type": "rect", "box": [1.0, 1.0, 4.0, 4.0], "fill": "#10B020"},
    ]


def _lines():
    return [
        {"type": "polyline", "points": [[0.0, 0.0], [9.0, 9.0]], "stroke": "#000",
         "stroke_style": {"stroke_width": 1.0}},
        {"type": "polyline", "points": [[2.0, 8.0], [8.0, 2.0]], "stroke": "#000"},
    ]


def test_hexshift_lightens_and_darkens():
    assert hexshift("#808080", 0.5).upper() == "#C0C0C0"     # toward white (128+63.5 -> 192)
    assert hexshift("#808080", -0.5).upper() == "#404040"    # toward black
    assert hexshift("#000000", 0.0) == "#000000"


def test_gradient_fills_lifts_flat_fill_to_gradient_dict():
    out = gradient_fills(_regions(), angle="90deg")
    for o in out:
        assert isinstance(o["fill"], dict)
        assert o["fill"]["kind"] == "linear" and o["fill"]["angle"] == "90deg"
        assert len(o["fill"]["stops"]) == 2
        assert all(s["color"].startswith("#") and "position" in s for s in o["fill"]["stops"])
    # geometry preserved; input not mutated
    assert [o.get("points") or o.get("box") for o in out] == \
           [o.get("points") or o.get("box") for o in _regions()]
    assert _regions()[0]["fill"] == "#3366CC"


def test_gradient_count_counts_only_gradient_fills():
    assert gradient_count(_regions()) == 0
    assert gradient_count(gradient_fills(_regions())) == 3


def test_recolor_cycle_assigns_palette_by_order():
    pal = ["#111111", "#222222"]
    out = recolor_cycle(_regions(), pal)
    assert [o["fill"] for o in out] == ["#111111", "#222222", "#111111"]
    assert [o.get("points") or o.get("box") for o in out] == \
           [o.get("points") or o.get("box") for o in _regions()]   # geometry intact
    assert _regions()[1]["fill"] == "#CC3333"                       # input not mutated


def test_as_guide_is_low_opacity_and_keeps_geometry():
    out = as_guide(_lines(), opacity=0.2, ink="#445566")
    assert all(o["style"]["opacity"] == 0.2 for o in out)
    assert all(o["stroke"] == "#445566" for o in out)
    assert [o["points"] for o in out] == [o["points"] for o in _lines()]


def test_author_overlay_contributes_real_colour_including_a_gradient():
    objs = author_overlay((1000, 600))
    assert objs and gradient_count(objs) >= 1            # at least one gradient block
    assert any(isinstance(o.get("fill"), str) and o["fill"].startswith("#") for o in objs)


def test_build_color_and_guide_renders_with_gradients():
    from framegraph.sdk import render_page_svgs
    b = build_color_and_guide(_regions(), _lines(), (10, 10))
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg")
    assert "gradient" in svg.lower()                     # gradients reach the SVG
    assert svg.count("<text") >= 4                       # the four panel labels
