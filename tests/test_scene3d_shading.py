#!/usr/bin/env python3
"""test_scene3d_shading.py — B6: shading completion (CG-canon backlog).

`Scene3D` already had flat (`lambert`) and smooth (`gouraud`) diffuse shading;
B6 adds a `phong` mode with a **Blinn-Phong specular** highlight (a view-dependent
term over the diffuse base). It is opt-in — the default `shading="none"` is
unchanged, so existing renders (goldens) are untouched.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_sdk import Camera, Scene3D, Vec3  # noqa: E402
from frameforge_sdk.draw import _collapse, _face_vertex_lighting  # noqa: E402

# a single face in the plane z=1, wound so its normal is +z (toward light & view).
_FACE = [([Vec3(0, 0, 1), Vec3(1, 0, 1), Vec3(1, 1, 1)], {})]
_LIGHT = Vec3(0, 0, 1)


def _intensity(**kw):
    """The one per-face intensity for `_FACE`.

    `_face_vertex_lighting` is per-VERTEX (one list per face); the per-face modes
    exercised here repeat a single value, which `_collapse` folds back to the
    scalar the pre-v1.1 per-face path returned.
    """
    return _collapse(_face_vertex_lighting(_FACE, _LIGHT, **kw)[0])


def _lam():
    return _intensity(ambient=0.2, diffuse=0.5, shading="lambert")


def test_phong_adds_a_specular_highlight_over_lambert():
    phong = _intensity(
        ambient=0.2, diffuse=0.5, shading="phong",
        view=Vec3(0, 0, 1), specular=0.3, shininess=16.0,
    )
    assert phong > _lam(), "specular must brighten a face facing the light and viewer"


def test_phong_with_zero_specular_equals_lambert():
    phong0 = _intensity(
        ambient=0.2, diffuse=0.5, shading="phong",
        view=Vec3(0, 0, 1), specular=0.0, shininess=16.0,
    )
    assert abs(phong0 - _lam()) < 1e-9


def test_phong_specular_is_view_dependent():
    kw = dict(ambient=0.2, diffuse=0.5, shading="phong", specular=0.4, shininess=16.0)
    facing = _intensity(view=Vec3(0, 0, 1), **kw)
    grazing = _intensity(view=Vec3(1, 0, 0), **kw)
    assert facing > grazing, "the highlight must weaken as the viewer moves off-axis"


def test_scene3d_render_phong_mode_runs():
    scene = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=0.5)
    group = scene.render(camera=Camera(), box=[0, 0, 100, 100], shading="phong")
    assert group["type"] == "group" and group["children"]


def test_default_shading_is_still_none_unshaded():
    # output-preserving: the default keeps every intensity at 1.0 (no shading).
    per_vertex = _face_vertex_lighting(_FACE, _LIGHT, ambient=0.2, diffuse=0.5, shading="none")
    assert per_vertex == [[1.0] * len(_FACE[0][0])]
