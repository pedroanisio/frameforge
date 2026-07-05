#!/usr/bin/env python3
"""test_geometry_intersect_curve.py — B8 residual: line/segment × cubic Bézier.

`segment_curve_intersections` and `line_curve_intersections` intersect a query
line/segment with a cubic Bézier by recursive de Casteljau subdivision (prune by
the control-polygon's side of the query line, flatten to the chord at the leaf).
Verified on a straight cubic (exact crossing), a symmetric arch (two crossings),
a miss, and the bounded-vs-infinite distinction.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    CubicBezier,
    Vec2,
    line_curve_intersections,
    segment_curve_intersections,
)


def _arch():
    # p0=(0,0) p1=(1,3) p2=(2,3) p3=(3,0): x(t)=3t, y(t)=9t(1-t) — a symmetric
    # hump peaking at (1.5, 2.25). y=1 is crossed at x≈0.382 and x≈2.618.
    return CubicBezier(Vec2(0, 0), Vec2(1, 3), Vec2(2, 3), Vec2(3, 0))


def test_straight_cubic_gives_the_exact_crossing():
    line_shaped = CubicBezier(Vec2(0, 0), Vec2(1, 1), Vec2(2, 2), Vec2(3, 3))
    hits = segment_curve_intersections(Vec2(0, 3), Vec2(3, 0), line_shaped)
    assert len(hits) == 1
    assert abs(hits[0].x - 1.5) < 1e-6
    assert abs(hits[0].y - 1.5) < 1e-6


def test_arch_is_crossed_twice_by_a_horizontal_line():
    hits = segment_curve_intersections(Vec2(-1, 1), Vec2(4, 1), _arch())
    assert len(hits) == 2
    for h in hits:
        assert abs(h.y - 1.0) < 1e-3        # every hit sits on the query line y=1
    xs = sorted(h.x for h in hits)
    assert abs(xs[0] - 0.38197) < 1e-3
    assert abs(xs[1] - 2.61803) < 1e-3
    assert abs((xs[0] + xs[1]) - 3.0) < 1e-3  # symmetric about x=1.5


def test_line_above_the_arch_misses():
    assert segment_curve_intersections(Vec2(-1, 5), Vec2(4, 5), _arch()) == []


def test_bounded_segment_drops_a_crossing_the_infinite_line_keeps():
    # query covers only x∈[-1, 1.5]: the left crossing (x≈0.382) is inside it,
    # the right crossing (x≈2.618) is not.
    seg = segment_curve_intersections(Vec2(-1, 1), Vec2(1.5, 1), _arch())
    assert len(seg) == 1
    assert seg[0].x < 1.5
    line = line_curve_intersections(Vec2(-1, 1), Vec2(1.5, 1), _arch())
    assert len(line) == 2


def test_degenerate_query_point_has_no_hits():
    assert segment_curve_intersections(Vec2(1, 1), Vec2(1, 1), _arch()) == []
