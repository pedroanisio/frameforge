#!/usr/bin/env python3
"""Coach redraw layer — rough traced contours → clean Bézier strokes / primitives.

redraw_smooth re-emits polylines/polygons as Catmull-Rom cubic paths;
snap_primitives recognises near-circular/near-rectangular polygons and replaces
them with clean ellipse/rect. Pure geometry over the SDK Path builder — no
OpenCV; boundary-clean (sdk + intra-package only).
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.coach import (  # noqa: E402
    curve_count,
    is_circular,
    is_rectangular,
    redraw,
    redraw_smooth,
    snap_primitives,
)


def _circle(n=16, r=10.0, cx=20.0, cy=20.0):
    return [[cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)]
            for i in range(n)]


def _square(side=20.0):
    s = side
    return [[0.0, 0.0], [s / 2, 0.0], [s, 0.0], [s, s / 2], [s, s],
            [s / 2, s], [0.0, s], [0.0, s / 2]]


def _arc(n=40, r=50.0):
    """A smooth half-circle arc — keeps >=3 points under coarse simplification."""
    return [[r * math.cos(math.pi * i / (n - 1)), r * math.sin(math.pi * i / (n - 1))]
            for i in range(n)]


def test_redraw_smooth_emits_curved_path_for_a_polyline():
    objs = [{"type": "polyline", "points": _circle(), "stroke": "#111"}]
    out = redraw_smooth(objs, simplify_tol=1.0, width=2.0)
    assert out[0]["type"] == "path" and "C" in out[0]["d"]      # cubic Béziers
    assert out[0]["stroke"] == "#111" and out[0]["fill"] == "none"
    assert out[0]["stroke_style"]["stroke_width"] == 2.0
    assert out[0]["stroke_style"]["stroke_linecap"] == "round"
    assert curve_count(out) == 1


def test_redraw_smooth_keeps_polygon_fill_and_closes():
    out = redraw_smooth([{"type": "polygon", "points": _square(), "fill": "#3366CC"}])
    assert out[0]["type"] == "path" and out[0]["fill"] == "#3366CC"
    assert out[0]["d"].rstrip().endswith("Z")


def test_redraw_smooth_simplify_reduces_geometry_then_curves():
    """A noisy polyline simplifies (fewer control points) before being curved."""
    objs = [{"type": "polyline", "points": _arc(), "stroke": "#000"}]
    coarse = redraw_smooth(objs, simplify_tol=8.0)
    fine = redraw_smooth(objs, simplify_tol=0.2)
    # coarser tolerance -> fewer cubic segments in the path data
    assert coarse[0]["d"].count("C") <= fine[0]["d"].count("C")
    assert curve_count(coarse) == 1


def test_non_point_objects_pass_through():
    out = redraw_smooth([{"type": "line", "from": [0.0, 0.0], "to": [1.0, 1.0], "stroke": "#000"}])
    assert out[0]["type"] == "line"


def test_is_circular_and_is_rectangular_discriminate():
    assert is_circular(_circle()) is True
    assert is_circular(_square()) is False
    assert is_rectangular(_square()) is True
    assert is_rectangular(_circle()) is False


def test_snap_primitives_recovers_clean_shapes_and_preserves_others():
    objs = [
        {"type": "polygon", "points": _circle(), "fill": "#10B020"},
        {"type": "polygon", "points": _square(), "fill": "#CC3333"},
        {"type": "polygon", "points": [[0.0, 0.0], [10.0, 1.0], [3.0, 9.0]], "fill": "#222"},  # triangle
    ]
    out = snap_primitives(objs)
    assert out[0]["type"] == "ellipse" and out[0]["fill"] == "#10B020"
    assert out[1]["type"] == "rect" and out[1]["fill"] == "#CC3333"
    assert out[2]["type"] == "polygon"                          # neither -> unchanged
    assert objs[0]["type"] == "polygon"                        # input not mutated


def test_redraw_one_call_snaps_then_smooths():
    objs = [
        {"type": "polygon", "points": _circle(), "fill": "#0AF"},        # -> ellipse (snapped)
        {"type": "polyline", "points": _arc(), "stroke": "#000"},  # -> smooth path
    ]
    out = redraw(objs, simplify_tol=2.0, snap=True)
    assert any(o["type"] == "ellipse" for o in out)            # the circle was snapped
    assert curve_count(out) == 1                               # the polyline was curved


def test_redraw_output_renders_through_framegraph():
    from framegraph.sdk import DocumentBuilder, render_page_svgs
    objs = [{"type": "polyline", "points": _circle(n=24, r=8, cx=12, cy=12), "stroke": "#111"}] * 4
    out = redraw_smooth(objs, simplify_tol=1.0)
    b = DocumentBuilder(title="redraw")
    p = b.page("p", canvas={"size": [24, 24], "units": "px"}, coordinate_mode="absolute")
    layer = p.layer("06_line_art")
    for o in out:
        layer.add(o)
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg") and "C" in svg              # curves reached the SVG
