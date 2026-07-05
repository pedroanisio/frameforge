#!/usr/bin/env python3
"""test_geometry_hull_3d.py — B10 residual: the 3D convex hull.

`convex_hull_3d(points)` returns the hull as outward-oriented triangular faces
(each a tuple of three Vec3). Verified on a tetrahedron and a cube, with interior
points correctly excluded and every face oriented outward (its normal points away
from the hull centroid).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import Vec3, convex_hull_3d  # noqa: E402


def _tetra():
    return [Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)]


def _cube():
    return [Vec3(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]


def _verts(faces):
    return {(round(p.x, 6), round(p.y, 6), round(p.z, 6)) for tri in faces for p in tri}


def _cross(a, b):
    return Vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)


def _center(pts):
    n = len(pts)
    return Vec3(sum(p.x for p in pts) / n, sum(p.y for p in pts) / n, sum(p.z for p in pts) / n)


def test_tetrahedron_has_four_triangular_faces():
    faces = convex_hull_3d(_tetra())
    assert len(faces) == 4
    assert _verts(faces) == {(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)}


def test_interior_point_is_not_a_hull_vertex():
    faces = convex_hull_3d(_tetra() + [Vec3(0.2, 0.2, 0.2)])
    assert (0.2, 0.2, 0.2) not in _verts(faces)
    assert _verts(faces) == {(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)}


def test_every_face_is_oriented_outward():
    pts = _tetra()
    ctr = _center(pts)
    for a, b, c in convex_hull_3d(pts):
        normal = _cross(Vec3(b.x - a.x, b.y - a.y, b.z - a.z),
                        Vec3(c.x - a.x, c.y - a.y, c.z - a.z))
        fc = Vec3((a.x + b.x + c.x) / 3, (a.y + b.y + c.y) / 3, (a.z + b.z + c.z) / 3)
        out = (fc.x - ctr.x) * normal.x + (fc.y - ctr.y) * normal.y + (fc.z - ctr.z) * normal.z
        assert out > 0, "face normal must point away from the hull centroid"


def test_cube_keeps_all_eight_corners_drops_the_centre():
    faces = convex_hull_3d(_cube() + [Vec3(0.5, 0.5, 0.5)])
    assert _verts(faces) == {(x, y, z) for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)}
    assert (0.5, 0.5, 0.5) not in _verts(faces)
    assert len(faces) >= 12   # 6 quad faces, triangulated


def test_fewer_than_four_points_has_no_faces():
    assert convex_hull_3d([Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(0, 1, 0)]) == []
