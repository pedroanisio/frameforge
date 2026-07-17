#!/usr/bin/env python3
"""test_manifold_patch.py — B5: curved-surface patches (CG-canon backlog).

A bicubic Bézier surface patch (Harrington Ch11): 16 control points, evaluated by
the Bernstein tensor product and tessellated into a `Scene3D`. The surface
interpolates its four corner control points exactly; a coplanar control net gives
a planar surface; the tessellation is steps_u × steps_v quads.
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
from frameforge.sdk.manifold import bezier_patch, bezier_patch_point  # noqa: E402


def _grid(zfn):
    """A 4×4 control net on the unit square with heights from zfn(i, j)."""
    return [[(i / 3.0, j / 3.0, zfn(i, j)) for j in range(4)] for i in range(4)]


def _close(p, q, tol=1e-9):
    return abs(p.x - q.x) < tol and abs(p.y - q.y) < tol and abs(p.z - q.z) < tol


def test_patch_interpolates_the_four_corners():
    c = _grid(lambda i, j: 1.0 if (i in (1, 2) and j in (1, 2)) else 0.0)
    assert _close(bezier_patch_point(c, 0.0, 0.0), Vec3(*c[0][0]))
    assert _close(bezier_patch_point(c, 1.0, 1.0), Vec3(*c[3][3]))
    assert _close(bezier_patch_point(c, 0.0, 1.0), Vec3(*c[0][3]))
    assert _close(bezier_patch_point(c, 1.0, 0.0), Vec3(*c[3][0]))


def test_flat_control_net_gives_a_planar_surface():
    c = _grid(lambda i, j: 0.0)  # all controls in the z = 0 plane
    for u in (0.2, 0.5, 0.83):
        for v in (0.3, 0.71):
            assert abs(bezier_patch_point(c, u, v).z) < 1e-9


def test_interior_of_a_raised_net_bulges_off_the_corner_plane():
    # inner controls lifted to z=1 → the middle of the surface rises above z=0.
    c = _grid(lambda i, j: 1.0 if (i in (1, 2) and j in (1, 2)) else 0.0)
    assert bezier_patch_point(c, 0.5, 0.5).z > 0.2


def test_bezier_patch_tessellates_into_a_scene():
    c = _grid(lambda i, j: 0.4 * (i == j))
    scene = bezier_patch(c, steps_u=8, steps_v=6)
    assert len(scene.faces) == 8 * 6
    # the very first tessellation vertex is the (0,0) corner control point.
    first = scene.faces[0][0][0]
    assert _close(first, Vec3(*c[0][0]))


def test_bezier_patch_rejects_a_bad_control_net():
    import pytest
    with pytest.raises(ValueError):
        bezier_patch([[(0, 0, 0)] * 3] * 4)  # 4×3, not 4×4
