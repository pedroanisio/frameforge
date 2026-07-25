#!/usr/bin/env python3
"""test_scene3d_pipeline.py — B2: 3D pipeline correctness (CG-canon backlog).

Fixes the canon gaps the operator's `cg-canon-3d-alignment.md` catalogues:

* **G1** — `Mat4.project` raised on `w≈0` and inverted on `w<0`; `Scene3D.render`
  projected every vertex, so a vertex crossing behind the eye crashed / mirror-
  flipped. `Mat4.try_project` returns ``None`` at/behind the near plane, and the
  renderer drops faces that straddle it (near-plane **culling**, G2).
* **G3** — opt-in back-face removal (`cull_backfaces=True`, default off).

Output-preserving: a scene fully in front of the camera renders unchanged (the
existing goldens prove no fixture straddles the near plane). Full Sutherland–
Hodgman near-plane *clipping* and the depth-strategy option (G4) are the residual.
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


def test_mat4_try_project_none_behind_near_and_equal_in_front():
    m = Camera(eye=Vec3(0, 0, 5), target=Vec3(0, 0, 0)).matrix()
    # in front of the camera → same result as the (raising) project().
    front = m.try_project(Vec3(0.2, 0.1, 0))
    assert front is not None
    ref = m.project(Vec3(0.2, 0.1, 0))
    assert abs(front.x - ref.x) < 1e-9 and abs(front.y - ref.y) < 1e-9
    # far behind the camera → clipped, no exception.
    assert m.try_project(Vec3(0, 0, 100)) is None


def _two_face_scene():
    # face A in front of the camera (z≈0), face B pushed far behind it (z=+100).
    scene = Scene3D()
    scene.mesh(
        [Vec3(-1, -1, 0), Vec3(1, -1, 0), Vec3(1, 1, 0), Vec3(-1, 1, 0),
         Vec3(-1, -1, 100), Vec3(1, -1, 100), Vec3(1, 1, 100)],
        [[0, 1, 2, 3], [4, 5, 6]],
    )
    return scene


def test_scene3d_drops_faces_behind_the_near_plane_without_crashing():
    scene = _two_face_scene()
    cam = Camera(eye=Vec3(0, 0, 5), target=Vec3(0, 0, 0))
    group = scene.render(camera=cam, box=[0, 0, 100, 100])  # must not raise
    # only the in-front face survives; the behind-camera face is culled.
    assert len(group["children"]) == 1


def test_scene3d_front_scene_keeps_every_face_output_preserving():
    # a fully in-front mesh must not lose any face (no spurious near-plane drop).
    scene = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=0.5)
    n_faces = len(scene.faces)
    group = scene.render(camera=Camera(), box=[0, 0, 100, 100])
    assert len(group["children"]) == n_faces


def test_scene3d_cull_backfaces_is_opt_in():
    scene = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=0.5)
    default = scene.render(camera=Camera(), box=[0, 0, 100, 100])
    culled = scene.render(camera=Camera(), box=[0, 0, 100, 100], cull_backfaces=True)
    # default keeps all faces; culling removes the ones facing away → strictly fewer.
    assert len(culled["children"]) < len(default["children"])
    assert len(culled["children"]) >= 1
