#!/usr/bin/env python3
"""test_geometry_viewport.py — B1: the formal viewing pipeline (CG-canon backlog).

`frameforge.sdk.geometry` gains the named window→viewport transform (Harrington
Ch6/¶43) that was previously hand-rolled inside `Scene3D.render`:

* `window_to_viewport(window, viewport, uniform=…)` — the affine that maps a
  window rect onto a viewport rect (optionally aspect-preserving + centered);
* `ViewingPipeline(camera, box)` — world → project → clip(behind-near) → fit,
  reproducing exactly the projection-fit `Scene3D.render` computes.

The pipeline is **output-preserving**: it does not touch the renderer (goldens are
unmoved). The equivalence test proves it reproduces the existing fit math.
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import Camera, Vec2, Vec3, ViewingPipeline, window_to_viewport  # noqa: E402


def _close(p, q, tol=1e-6):
    return abs(p.x - q.x) < tol and abs(p.y - q.y) < tol


def test_window_to_viewport_non_uniform_maps_corners():
    m = window_to_viewport([0, 0, 10, 10], [0, 0, 100, 50])
    assert _close(m.apply((0, 0)), Vec2(0.0, 0.0))
    assert _close(m.apply((10, 10)), Vec2(100.0, 50.0))
    assert _close(m.apply((5, 5)), Vec2(50.0, 25.0))


def test_window_to_viewport_offset_window():
    m = window_to_viewport([2, 3, 4, 4], [0, 0, 8, 8])
    assert _close(m.apply((2, 3)), Vec2(0.0, 0.0))
    assert _close(m.apply((6, 7)), Vec2(8.0, 8.0))


def test_window_to_viewport_uniform_preserves_aspect_and_centers():
    m = window_to_viewport([0, 0, 10, 10], [0, 0, 100, 50], uniform=True)
    # scale = min(100/10, 50/10) = 5; the 50-wide fitted square is centred (ox=25).
    assert _close(m.apply((0, 0)), Vec2(25.0, 0.0))
    assert _close(m.apply((10, 10)), Vec2(75.0, 50.0))
    assert _close(m.apply((5, 5)), Vec2(50.0, 25.0))


def test_window_to_viewport_rejects_degenerate_window():
    import pytest
    with pytest.raises(ValueError):
        window_to_viewport([0, 0, 0, 10], [0, 0, 100, 50])


def test_viewing_pipeline_reproduces_the_scene3d_fit():
    """ViewingPipeline must reproduce the exact projection-fit Scene3D.render
    computes (bounds → uniform scale → centre), proving it is output-preserving."""
    camera = Camera(eye=Vec3(3, 2.5, 4), target=Vec3(0, 0, 0))
    box = [0.0, 0.0, 200.0, 120.0]
    world = [Vec3(-1, -1, -1), Vec3(1, -1, -1), Vec3(1, 1, 1), Vec3(-1, 1, 1), Vec3(0, 1, -1)]

    # the reference fit, exactly as draw.py does it:
    proj = [camera.project(p) for p in world]
    min_x = min(q.x for q in proj); max_x = max(q.x for q in proj)
    min_y = min(q.y for q in proj); max_y = max(q.y for q in proj)
    scale = min(box[2] / max(max_x - min_x, 1e-9), box[3] / max(max_y - min_y, 1e-9))
    ox = (box[2] - (max_x - min_x) * scale) / 2
    oy = (box[3] - (max_y - min_y) * scale) / 2
    expected = [Vec2(ox + (q.x - min_x) * scale, oy + (q.y - min_y) * scale) for q in proj]

    got = ViewingPipeline(camera, box).project(world)
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        assert _close(g, e), f"{g.tuple()} != {e.tuple()}"


def test_viewing_pipeline_clips_points_behind_the_camera():
    # camera at +z=5 looking at origin: a point far behind it (z=+100) is behind
    # the near plane and must be clipped out of the projected set.
    camera = Camera(eye=Vec3(0, 0, 5), target=Vec3(0, 0, 0))
    pipe = ViewingPipeline(camera, [0, 0, 100, 100])
    out = pipe.project([Vec3(0, 0, 0), Vec3(0.5, 0, 0), Vec3(0, 0, 100)])
    assert len(out) == 2  # the behind-camera point dropped


def test_viewing_pipeline_fits_inside_the_box():
    camera = Camera()
    box = [10.0, 20.0, 80.0, 60.0]
    cube = [Vec3(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    pts = ViewingPipeline(camera, box).project(cube)
    assert pts, "cube should project to points"
    assert all(box[0] - 1e-6 <= p.x <= box[0] + box[2] + 1e-6 for p in pts)
    assert all(box[1] - 1e-6 <= p.y <= box[1] + box[3] + 1e-6 for p in pts)
