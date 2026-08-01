#!/usr/bin/env python3
"""Regression tests for the FrameForge SDK.

These complement the public-surface assertions in ``test_sdk.py`` with a
regression guard the existing suite does not cover:

**3D projection determinism.** ``Scene3D`` + ``Camera`` is a software
projector; its output must be deterministic and bounded to the render box, so a
regression in the projection/painter's-sort math is caught here rather than only
showing up as a visually-wrong fixture.

The shipped-artifact regression that used to live here — the Esfera / Coopera
decks and the composed 3D scene, each rebuilt from source and revalidated —
moved out with the cookbook. It now lives beside the clients it guards, in
``frameforge-example/tests/test_example_parity.py``.

Per the repo standard (codebase-standards.md §6) the module is deterministic,
isolated, and runnable both under pytest and standalone (``python
tests/test_sdk_regression.py``).
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_sdk import Camera, Scene3D, Vec3, inset, linear_gradient, radial_gradient, rgba, row  # noqa: E402


# --------------------------------------------------------------------------- #
#  3D projection determinism (Scene3D + Camera)
# --------------------------------------------------------------------------- #
def _unit_cube():
    v = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
         (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    faces = [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7],
             [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]]
    return Scene3D().mesh(v, faces, fill="#888")


def _render_cube():
    cam = Camera(eye=Vec3(3.0, 2.5, 4.0), target=Vec3(0.5, 0.5, 0.5), fov=45)
    return _unit_cube().render(box=[0, 0, 400, 300], camera=cam,
                               fill="#888", stroke="#222")


def test_scene3d_render_is_a_group_of_polylines():
    g = _render_cube()
    assert g["type"] == "group"
    assert g["box"] == [0, 0, 400, 300]
    children = g["children"]
    assert len(children) == 6  # one polyline per cube face
    for child in children:
        assert child["type"] == "polyline"
        assert child.get("closed") is True
        assert len(child["points"]) == 4


def test_scene3d_projection_is_bounded_to_box():
    g = _render_cube()
    for child in g["children"]:
        for x, y in child["points"]:
            assert -0.01 <= x <= 400.01, f"x={x} out of box"
            assert -0.01 <= y <= 300.01, f"y={y} out of box"


def test_scene3d_render_is_deterministic():
    a = _render_cube()
    b = _render_cube()
    assert a == b, "Scene3D.render must be deterministic for a fixed scene+camera"


def test_scene3d_generators_produce_expected_face_counts():
    # parametric_surface: steps_u * steps_v quads
    surf = Scene3D().parametric_surface(
        lambda u, v: (u, 0.0, v), u=(0, 1), v=(0, 1), steps_u=4, steps_v=3)
    assert len(surf.faces) == 12
    # revolve: segments * (profile_points - 1) quads
    rev = Scene3D().revolve([(0.0, 0.0), (1.0, 0.0), (0.0, 2.0)], segments=8)
    assert len(rev.faces) == 8 * 2
    # extrude: 2 caps + n side quads
    ext = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=1.0)
    assert len(ext.faces) == 2 + 4


# --------------------------------------------------------------------------- #
#  paint helpers (translucency + gradients are part of the public contract)
# --------------------------------------------------------------------------- #
def test_rgba_clamps_alpha_and_expands_shorthand():
    assert rgba("#ff0000", 0.5) == "rgba(255,0,0,0.5)"
    assert rgba("#fff", 2.0) == "rgba(255,255,255,1)"     # clamped to 1
    assert rgba("#000", -1.0) == "rgba(0,0,0,0)"          # clamped to 0


def test_gradient_stop_positions_normalize():
    g = linear_gradient(["#000000", "#ffffff"], angle=180)
    assert g["kind"] == "linear" and g["angle"] == 180
    assert [s["position"] for s in g["stops"]] == ["0%", "100%"]
    r = radial_gradient([("#fff", 0.0), ("#fff", 1.0)])
    assert r["kind"] == "radial"
    assert [s["position"] for s in r["stops"]] == ["0%", "100%"]


# --------------------------------------------------------------------------- #
#  layout invariants
# --------------------------------------------------------------------------- #
def test_row_partition_tiles_the_container_exactly():
    boxes = row([0, 0, 300, 100], count=3, gap=10)
    assert len(boxes) == 3
    widths = sum(b[2] for b in boxes)
    assert abs(widths + 2 * 10 - 300) < 1e-9       # widths + gaps fill the box
    assert boxes[0][0] == 0
    assert abs((boxes[-1][0] + boxes[-1][2]) - 300) < 1e-9  # last edge == right
    for a, b in zip(boxes, boxes[1:]):              # no overlap, left→right
        assert a[0] + a[2] <= b[0] + 1e-9


def test_inset_shrinks_symmetrically():
    assert inset([0, 0, 100, 80], 10) == [10, 10, 80, 60]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
