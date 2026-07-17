#!/usr/bin/env python3
"""test_geometry_intersect_3d.py — B8 residual: 3D intersection primitives.

Completes B8's documented residual (the 3D-plane and curve intersections) with the
foundational 3D-plane/triangle cases in `frameforge.sdk.geometry`:

* `ray_plane_intersection` / `segment_plane_intersection` — a plane as
  ``(point, normal)``; parallel or one-sided misses return ``None``;
* `ray_triangle_intersection` — Möller–Trumbore ray/triangle test.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    Vec3,
    ray_plane_intersection,
    ray_triangle_intersection,
    segment_plane_intersection,
)


def _close3(p, q, tol=1e-9):
    return p is not None and abs(p.x - q.x) < tol and abs(p.y - q.y) < tol and abs(p.z - q.z) < tol


def test_ray_plane_hits_ahead():
    p = ray_plane_intersection((0, 0, 0), (0, 0, 1), (0, 0, 5), (0, 0, 1))
    assert _close3(p, Vec3(0, 0, 5))


def test_ray_plane_parallel_returns_none():
    assert ray_plane_intersection((0, 0, 0), (1, 0, 0), (0, 0, 5), (0, 0, 1)) is None


def test_ray_plane_behind_returns_none():
    # ray points away from the plane (−z) → no forward hit.
    assert ray_plane_intersection((0, 0, 0), (0, 0, -1), (0, 0, 5), (0, 0, 1)) is None


def test_segment_plane_within_and_beyond():
    hit = segment_plane_intersection((0, 0, 0), (0, 0, 10), (0, 0, 5), (0, 0, 1))
    assert _close3(hit, Vec3(0, 0, 5))
    # a segment that stops short of the plane does not reach it.
    assert segment_plane_intersection((0, 0, 0), (0, 0, 4), (0, 0, 5), (0, 0, 1)) is None


def test_ray_triangle_hit_inside():
    tri = (Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(0, 1, 0))
    hit = ray_triangle_intersection((0.25, 0.25, -1), (0, 0, 1), *tri)
    assert _close3(hit, Vec3(0.25, 0.25, 0))


def test_ray_triangle_miss_outside_barycentric():
    tri = (Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(0, 1, 0))
    # (0.9, 0.9) has u+v > 1 → outside the triangle.
    assert ray_triangle_intersection((0.9, 0.9, -1), (0, 0, 1), *tri) is None


def test_ray_triangle_parallel_and_behind_return_none():
    tri = (Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(0, 1, 0))
    assert ray_triangle_intersection((0.25, 0.25, -1), (1, 0, 0), *tri) is None  # parallel
    assert ray_triangle_intersection((0.25, 0.25, 1), (0, 0, 1), *tri) is None  # triangle behind
