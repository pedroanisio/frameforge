#!/usr/bin/env python3
"""test_geometry_obb.py — B10 residual: oriented bounding box + 3D AABB.

Completes B10's documented residual with the minimum-area oriented bounding box
(`obb`, rotating calipers on the convex hull — the min-area rectangle shares an
edge with the hull) and a 3D axis-aligned box (`aabb3`). The OBB is never looser
than the axis-aligned box and is strictly tighter for a rotated shape.
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import Vec3, aabb, aabb3, obb, polygon_area  # noqa: E402


def _aabb_area(points):
    lo, hi = aabb(points)
    return (hi.x - lo.x) * (hi.y - lo.y)


def test_obb_returns_four_corners():
    box = obb([(0, 0), (4, 0), (4, 2), (0, 2), (2, 1)])
    assert len(box) == 4


def test_obb_of_axis_aligned_rect_matches_the_rect():
    rect = [(0, 0), (4, 0), (4, 2), (0, 2)]
    assert math.isclose(abs(polygon_area(obb(rect))), 8.0, abs_tol=1e-6)


def test_obb_is_tighter_than_aabb_for_a_rotated_square():
    # a unit-ish square rotated 45° (a diamond), side √2 → true area 2.
    diamond = [(1, 0), (2, 1), (1, 2), (0, 1)]
    obb_area = abs(polygon_area(obb(diamond)))
    assert math.isclose(obb_area, 2.0, abs_tol=1e-6), obb_area
    assert obb_area < _aabb_area(diamond) - 1e-6  # AABB is 2×2 = 4


def test_obb_is_never_looser_than_the_aabb():
    pts = [(0, 0), (5, 1), (4, 4), (1, 3), (2, 2)]
    assert abs(polygon_area(obb(pts))) <= _aabb_area(pts) + 1e-6


def test_aabb3_bounds_3d_points():
    lo, hi = aabb3([Vec3(1, 5, -2), Vec3(-3, 2, 4), Vec3(0, -1, 1)])
    assert lo.tuple() == (-3.0, -1.0, -2.0)
    assert hi.tuple() == (1.0, 5.0, 4.0)
