#!/usr/bin/env python3
"""test_manifold_bspline.py — B5 residual: uniform bicubic B-spline surface patch.

A uniform (non-clamped) cubic B-spline surface over an m×n control net (m,n ≥ 4),
evaluated by the tensor product of the uniform cubic basis and tessellated into a
`Scene3D`. Unlike a Bézier patch it does NOT interpolate its corner controls — it
lies inside the control net's convex hull (partition of unity), which pins the
verifiable corner values below.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import Vec3  # noqa: E402
from frameforge.sdk.manifold import bspline_patch, bspline_patch_point  # noqa: E402


def _grid(m, n, zfn):
    """An m×n control net with P[i][j] = (i, j, zfn(i, j))."""
    return [[(float(i), float(j), zfn(i, j)) for j in range(n)] for i in range(m)]


def _close(p, q, tol=1e-9):
    return abs(p.x - q.x) < tol and abs(p.y - q.y) < tol and abs(p.z - q.z) < tol


def test_flat_control_net_gives_a_planar_surface():
    # every control z=0 → the surface stays in the z=0 plane (partition of unity).
    c = _grid(4, 4, lambda i, j: 0.0)
    for u in (0.0, 0.2, 0.5, 0.83, 1.0):
        for v in (0.0, 0.3, 0.71, 1.0):
            assert abs(bspline_patch_point(c, u, v).z) < 1e-9


def test_uniform_bspline_corner_pulls_inward_to_a_known_value():
    # For P[i][j]=(i,j,0) on a 4×4 net the uniform basis at (0,0) weights the first
    # three controls by (1,4,1)/6 → x=y=(0·1+1·4+2·1)/6 = 1.0 (not the (0,0) corner).
    c = _grid(4, 4, lambda i, j: 0.0)
    assert _close(bspline_patch_point(c, 0.0, 0.0), Vec3(1.0, 1.0, 0.0))
    # symmetrically the far corner pulls in to (2,2): weights (1,4,1)/6 on 1,2,3.
    assert _close(bspline_patch_point(c, 1.0, 1.0), Vec3(2.0, 2.0, 0.0))


def test_surface_lies_within_the_control_hull_bounding_box():
    # convex-hull property: every sample sits inside the control net's AABB.
    c = _grid(5, 4, lambda i, j: 1.0 if (1 <= i <= 3 and j == 2) else 0.0)
    flat = [pt for row in c for pt in row]
    lo = (min(p[0] for p in flat), min(p[1] for p in flat), min(p[2] for p in flat))
    hi = (max(p[0] for p in flat), max(p[1] for p in flat), max(p[2] for p in flat))
    for u in (0.0, 0.25, 0.5, 0.75, 1.0):
        for v in (0.0, 0.5, 1.0):
            p = bspline_patch_point(c, u, v)
            assert lo[0] - 1e-9 <= p.x <= hi[0] + 1e-9
            assert lo[1] - 1e-9 <= p.y <= hi[1] + 1e-9
            assert lo[2] - 1e-9 <= p.z <= hi[2] + 1e-9


def test_raised_interior_bulges_off_the_base_plane():
    # a lifted interior control makes the surface rise above z=0 somewhere.
    c = _grid(5, 5, lambda i, j: 3.0 if (i == 2 and j == 2) else 0.0)
    assert bspline_patch_point(c, 0.5, 0.5).z > 0.2


def test_bspline_patch_tessellates_into_a_scene():
    c = _grid(4, 4, lambda i, j: 0.4 * (i == j))
    scene = bspline_patch(c, steps_u=8, steps_v=6)
    assert len(scene.faces) == 8 * 6


def test_bspline_patch_rejects_a_too_small_or_ragged_net():
    import pytest
    with pytest.raises(ValueError):
        bspline_patch(_grid(3, 4, lambda i, j: 0.0))   # only 3 rows
    with pytest.raises(ValueError):
        bspline_patch(_grid(4, 3, lambda i, j: 0.0))   # only 3 columns
    with pytest.raises(ValueError):
        bspline_patch([[(0, 0, 0)] * 4, [(0, 0, 0)] * 3, [(0, 0, 0)] * 4, [(0, 0, 0)] * 4])  # ragged
