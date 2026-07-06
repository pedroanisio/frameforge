#!/usr/bin/env python3
"""test_geometry_intersect.py — B8: the 2D geometric-intersection primitives.

The CG-canon backlog's B8 (foundational for hit-testing / snapping / clipping)
lands its 2D primitive core in `framegraph.sdk.geometry`: line×line, segment×
segment, ray×segment, and segment×polygon. Each is parametric (a 2D cross-product
solve); parallel/collinear inputs return no crossing (None / []). The 3D
(plane) and curve intersections named in the backlog are the item's documented
expansion.
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
    Vec2,
    line_intersection,
    ray_segment_intersection,
    segment_intersection,
    segment_polygon_intersections,
)


def _close(p, q, tol=1e-9):
    return p is not None and abs(p.x - q.x) < tol and abs(p.y - q.y) < tol


def test_segment_intersection_crossing_diagonals():
    p = segment_intersection((0, 0), (4, 4), (0, 4), (4, 0))
    assert _close(p, Vec2(2.0, 2.0))


def test_segment_intersection_t_junction_at_a_point():
    p = segment_intersection((0, 0), (2, 0), (1, -1), (1, 1))
    assert _close(p, Vec2(1.0, 0.0))


def test_segment_intersection_none_when_segments_do_not_reach():
    # the infinite lines cross at (2,0) but segment A stops at x=1.
    assert segment_intersection((0, 0), (1, 0), (2, -1), (2, 1)) is None


def test_segment_intersection_none_when_parallel():
    assert segment_intersection((0, 0), (1, 1), (0, 1), (1, 2)) is None


def test_segment_intersection_none_when_collinear():
    assert segment_intersection((0, 0), (1, 0), (2, 0), (3, 0)) is None


def test_segment_intersection_shares_endpoint():
    p = segment_intersection((0, 0), (1, 1), (1, 1), (2, 0))
    assert _close(p, Vec2(1.0, 1.0))


def test_line_intersection_extends_beyond_segments():
    # same inputs as the "does not reach" segment case: the LINES do cross.
    p = line_intersection((0, 0), (1, 0), (2, -1), (2, 1))
    assert _close(p, Vec2(2.0, 0.0))


def test_line_intersection_none_when_parallel():
    assert line_intersection((0, 0), (1, 0), (0, 1), (1, 1)) is None


def test_ray_segment_hit_ahead():
    p = ray_segment_intersection((0, 0), (1, 0), (2, -1), (2, 1))
    assert _close(p, Vec2(2.0, 0.0))


def test_ray_segment_miss_when_pointing_away():
    assert ray_segment_intersection((0, 0), (-1, 0), (2, -1), (2, 1)) is None


def test_segment_polygon_crosses_two_edges():
    square = [(0, 0), (1, 0), (1, 1), (0, 1)]
    hits = segment_polygon_intersections((-1, 0.5), (2, 0.5), square)
    xs = sorted(round(h.x, 6) for h in hits)
    assert xs == [0.0, 1.0], f"expected entry at x=0 and exit at x=1, got {xs}"
    assert all(abs(h.y - 0.5) < 1e-9 for h in hits)


def test_segment_polygon_no_crossing_returns_empty():
    square = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert segment_polygon_intersections((2, 2), (3, 3), square) == []
