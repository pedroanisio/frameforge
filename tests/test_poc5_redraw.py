#!/usr/bin/env python3
"""POC-05 — redrawing over a trace (rough polygons -> clean smooth/primitive art).

The geometry (simplify / redraw_smooth / snap_primitives / is_circular /
is_rectangular) is pure and OpenCV-free, so it unit-tests directly; only the
raster ``trace`` needs the vision group.
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, os.path.join(ROOT, "static", "examples"))

from poc5_redraw import (  # noqa: E402
    build_redraw,
    curve_count,
    is_circular,
    is_rectangular,
    redraw_smooth,
    simplify,
    snap_primitives,
)


def _circle(n=16, r=10.0, cx=20.0, cy=20.0):
    return [[cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)]
            for i in range(n)]


def _square(side=20.0):
    s = side
    return [[0.0, 0.0], [s / 2, 0.0], [s, 0.0], [s, s / 2], [s, s],
            [s / 2, s], [0.0, s], [0.0, s / 2]]


def test_simplify_drops_collinear_and_keeps_endpoints():
    line = [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]]   # all collinear
    out = simplify(line, 0.5)
    assert out == [[0.0, 0.0], [3.0, 0.0]]                     # endpoints only
    zig = [[0.0, 0.0], [1.0, 5.0], [2.0, 0.0]]                 # a real corner is kept
    assert len(simplify(zig, 0.5)) == 3
    assert simplify(zig, 0.0) == [[0.0, 0.0], [1.0, 5.0], [2.0, 0.0]]   # tol<=0 -> unchanged


def test_redraw_smooth_emits_curved_path_for_a_polyline():
    objs = [{"type": "polyline", "points": _circle(), "stroke": "#111"}]
    out = redraw_smooth(objs, simplify_tol=1.0, width=2.0)
    assert out[0]["type"] == "path"
    assert "C" in out[0]["d"]                                  # cubic Bézier segments
    assert out[0]["stroke"] == "#111" and out[0]["fill"] == "none"
    assert out[0]["stroke_style"]["stroke_width"] == 2.0
    assert curve_count(out) == 1


def test_redraw_smooth_keeps_polygon_fill_and_closes():
    objs = [{"type": "polygon", "points": _square(), "fill": "#3366CC"}]
    out = redraw_smooth(objs)
    assert out[0]["type"] == "path" and out[0]["fill"] == "#3366CC"
    assert out[0]["d"].rstrip().endswith("Z")                  # closed path


def test_redraw_smooth_passes_through_short_runs_untouched():
    objs = [{"type": "line", "from": [0.0, 0.0], "to": [1.0, 1.0], "stroke": "#000"}]
    out = redraw_smooth(objs)
    assert out[0]["type"] == "line"                            # not a polyline/polygon -> as-is


def test_is_circular_and_is_rectangular_discriminate():
    assert is_circular(_circle()) is True
    assert is_circular(_square()) is False
    assert is_rectangular(_square()) is True
    assert is_rectangular(_circle()) is False


def test_snap_primitives_recovers_clean_shapes():
    objs = [
        {"type": "polygon", "points": _circle(), "fill": "#10B020"},
        {"type": "polygon", "points": _square(), "fill": "#CC3333"},
        {"type": "polygon", "points": [[0.0, 0.0], [10.0, 1.0], [3.0, 9.0]], "fill": "#222"},  # triangle
    ]
    out = snap_primitives(objs)
    assert out[0]["type"] == "ellipse" and out[0]["fill"] == "#10B020"
    assert out[1]["type"] == "rect" and out[1]["fill"] == "#CC3333"
    assert out[2]["type"] == "polygon"                        # not circle/rect -> unchanged
    assert objs[0]["type"] == "polygon"                       # input not mutated


def test_build_redraw_renders_curved_paths():
    from framegraph.sdk import render_page_svgs
    outline = [{"type": "polyline", "points": _circle(n=24, r=8, cx=12, cy=12), "stroke": "#111"}] * 5
    b = build_redraw(outline, (24, 24))
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg")
    assert "C" in svg                                          # curves reached the SVG
    assert svg.count("<text") >= 4                            # four panel labels
