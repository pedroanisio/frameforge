#!/usr/bin/env python3
"""test_geometry_hull.py — B10: convex hull + computational-geometry primitives.

`framegraph.sdk.geometry` gains `convex_hull` (2D Andrew's monotone chain — the
Mortenson §21 primitive), `aabb` (axis-aligned bounds), `polygon_area` (signed
shoelace), and `point_in_polygon` (ray-crossing). The hull is verified against a
brute-force oracle; collinear and duplicate points are handled explicitly.
"""
from __future__ import annotations

import itertools
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    Vec2,
    aabb,
    convex_hull,
    point_in_polygon,
    polygon_area,
)


def _brute_hull_vertices(points):
    """A point is a hull vertex iff some directed line through it has all other
    points on one side (a straightforward O(n^3) oracle)."""
    pts = list({(p.x, p.y) for p in (Vec2(*q) if not isinstance(q, Vec2) else q for q in points)})
    if len(pts) <= 2:
        return set(pts)
    on_hull = set()
    for a, b in itertools.permutations(pts, 2):
        cr = [(b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
              for c in pts if c not in (a, b)]
        if all(v >= -1e-12 for v in cr):  # all others left of / on a->b
            on_hull.add(a)
            on_hull.add(b)
    return on_hull


def test_hull_of_a_square_with_interior_point():
    pts = [(0, 0), (2, 0), (2, 2), (0, 2), (1, 1)]
    hull = convex_hull(pts)
    verts = {p.tuple() for p in hull}
    assert verts == {(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)}
    assert (1.0, 1.0) not in verts  # interior point dropped


def test_hull_excludes_collinear_edge_points():
    # three collinear points on the bottom edge — the middle one is not a vertex.
    pts = [(0, 0), (1, 0), (2, 0), (2, 2), (0, 2)]
    verts = {p.tuple() for p in convex_hull(pts)}
    assert (1.0, 0.0) not in verts
    assert verts == {(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)}


def test_hull_matches_brute_force_oracle():
    # no three points collinear, so "strict hull vertices" (convex_hull) and the
    # boundary-inclusive brute-force oracle agree exactly. Collinear handling is
    # pinned separately by test_hull_excludes_collinear_edge_points.
    pts = [(0, 0), (4, 0), (5, 3), (2, 5), (-1, 2), (2, 2), (2.5, 2), (1.5, 2.5)]
    verts = {p.tuple() for p in convex_hull(pts)}
    assert verts == _brute_hull_vertices([Vec2(*p) for p in pts])


def test_hull_handles_duplicates_and_degenerate():
    assert {p.tuple() for p in convex_hull([(1, 1), (1, 1), (1, 1)])} == {(1.0, 1.0)}
    two = {p.tuple() for p in convex_hull([(0, 0), (1, 1), (0, 0)])}
    assert two == {(0.0, 0.0), (1.0, 1.0)}


def test_hull_is_a_closed_convex_ring():
    # every consecutive turn around the returned ring has the same sign (convex).
    hull = convex_hull([(0, 0), (4, 0), (5, 3), (3, 5), (0, 4), (2, 2)])
    n = len(hull)
    assert n >= 3
    signs = []
    for i in range(n):
        o, a, b = hull[i], hull[(i + 1) % n], hull[(i + 2) % n]
        signs.append((a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x))
    assert all(s > 0 for s in signs) or all(s < 0 for s in signs), "ring must be convex"


def test_aabb_bounds_the_points():
    lo, hi = aabb([(1, 5), (-2, 3), (4, -1)])
    assert lo.tuple() == (-2.0, -1.0) and hi.tuple() == (4.0, 5.0)


def test_polygon_area_signed_shoelace():
    square_ccw = [(0, 0), (2, 0), (2, 2), (0, 2)]
    assert math.isclose(polygon_area(square_ccw), 4.0)
    # reversed winding negates the signed area; |area| is orientation-free.
    assert math.isclose(polygon_area(list(reversed(square_ccw))), -4.0)


def test_point_in_polygon_inside_outside():
    square = [(0, 0), (4, 0), (4, 4), (0, 4)]
    assert point_in_polygon((2, 2), square) is True
    assert point_in_polygon((5, 2), square) is False
    assert point_in_polygon((-1, -1), square) is False
