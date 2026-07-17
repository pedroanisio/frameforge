#!/usr/bin/env python3
"""test_scene3d_near_clip.py — B2 residual: near-plane Sutherland–Hodgman clip.

`Scene3D.render(near_clip=True)` splits a face that straddles the near plane
(the ``w ≥ near_eps`` boundary the projection already uses) at that plane and
keeps its front portion, instead of the default behaviour of culling any face
with a vertex at/behind the plane. The flag is **opt-in and default-off**, so
existing renders (and goldens) are untouched; a fully-front face projects
identically with or without it.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import Camera, Scene3D, Vec3  # noqa: E402

CAM = Camera(eye=Vec3(0, 0, 5), target=Vec3(0, 0, 0), up=Vec3(0, 1, 0),
             fov=60, aspect=1.0, near=0.1, far=100.0)
BOX = [0, 0, 200, 200]

# w = [5, 5, -1]: the third vertex is behind the eye plane (w < 0).
STRADDLE = [Vec3(1, 0, 0), Vec3(-1, 0, 0), Vec3(0, 0, 6)]
# all w = 5: entirely in front.
FRONT = [Vec3(1, 0, 0), Vec3(-1, 0, 0), Vec3(0, 1, 0)]
# all w = -1: entirely behind.
BEHIND = [Vec3(0, 0, 6), Vec3(0.5, 0, 6), Vec3(0, 0.5, 6)]


def _scene(face):
    s = Scene3D()
    s.faces.append((list(face), {}))
    return s


def test_straddling_face_is_culled_by_default():
    g = _scene(STRADDLE).render(camera=CAM, box=BOX)
    assert g["children"] == []  # default: any behind-plane vertex drops the face


def test_near_clip_retains_the_front_portion_of_a_straddling_face():
    g = _scene(STRADDLE).render(camera=CAM, box=BOX, near_clip=True)
    assert len(g["children"]) == 1
    poly = g["children"][0]["points"]
    # a triangle clipped by one plane becomes a polygon with >= 3 vertices…
    assert len(poly) >= 3
    # …and every retained vertex is finite (no divide-by-w blow-up).
    for x, y in poly:
        assert isinstance(x, float) and isinstance(y, float)
        assert x == x and y == y  # not NaN


def test_fully_behind_face_is_dropped_even_with_near_clip():
    g = _scene(BEHIND).render(camera=CAM, box=BOX, near_clip=True)
    assert g["children"] == []


def test_fully_front_face_projects_identically_with_or_without_near_clip():
    off = _scene(FRONT).render(camera=CAM, box=BOX)
    on = _scene(FRONT).render(camera=CAM, box=BOX, near_clip=True)
    assert off["children"] and on["children"]
    assert off["children"][0]["points"] == on["children"][0]["points"]


def test_near_clip_defaults_to_false():
    # a plain render call must behave exactly as before (regression guard).
    g = _scene(STRADDLE).render(camera=CAM, box=BOX)
    assert g["children"] == []
