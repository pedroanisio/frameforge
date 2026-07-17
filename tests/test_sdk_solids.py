#!/usr/bin/env python3
"""Solid generators + section views — the CAD kernel's missing operators.

Scene3D already carries mesh/extrude/revolve; this pins the module-level
solids API (discoverable, exported) plus the genuinely new generators —
partial revolve, sweep along a 3D path, loft between profiles — and the
engineering section cut (plane ∩ scene → closed, hatchable loops), whose
kernel mathematics (segment_plane_intersection) predates it.
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from frameforge.sdk.solids import (  # noqa: E402
    extrude, loft, revolve, section_loops, section_object, sweep)

SQUARE = [(0, 0), (1, 0), (1, 1), (0, 1)]


def _verts(scene):
    return [p for face, _style in scene.faces for p in face]


def _area2(loop):
    s = 0.0
    for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def test_extrude_square_is_a_box():
    sc = extrude(SQUARE, 5.0)
    assert len(sc.faces) == 6            # two caps + four sides
    zs = {round(p.z, 6) for p in _verts(sc)}
    assert zs == {0.0, 5.0}


def test_revolve_full_circle_ring_counts():
    sc = revolve([(1.0, 0.0), (1.0, 2.0)], segments=8)
    assert len(sc.faces) == 8
    xs = [p.x for p in _verts(sc)]
    assert max(xs) <= 1.0 + 1e-9 and min(xs) >= -1.0 - 1e-9


def test_partial_revolve_has_end_caps():
    full = revolve([(1.0, 0.0), (1.0, 1.0), (0.5, 1.0)], segments=8)
    half = revolve([(1.0, 0.0), (1.0, 1.0), (0.5, 1.0)], segments=8, angle=180.0)
    assert len(half.faces) == len(full.faces) + 2    # same quads/turn + 2 caps
    xs = [p.x for p in _verts(half)]
    zs = [p.z for p in _verts(half)]
    assert min(zs) >= -1e-9                          # half revolution stays z >= 0
    assert max(xs) <= 1.0 + 1e-9


def test_sweep_along_straight_path_matches_extrude():
    swept = sweep(SQUARE, [(0, 0, 0), (0, 0, 5)])
    box = extrude(SQUARE, 5.0)
    assert len(swept.faces) == len(box.faces)
    sv = sorted((round(p.x, 4), round(p.y, 4), round(p.z, 4)) for p in _verts(swept))
    bv = sorted((round(p.x, 4), round(p.y, 4), round(p.z, 4)) for p in _verts(box))
    assert sv == bv


def test_sweep_ring_centres_follow_the_path():
    centred = [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]
    path = [(0, 0, 0), (0, 0, 4), (3, 0, 4)]
    sc = sweep(centred, path, caps=False)
    assert len(sc.faces) == 4 * (len(path) - 1)
    # the far edge of the final quads is the end ring — for a centred profile
    # its centroid sits exactly on the path's end point
    end_ring = [p for face, _s in sc.faces[-4:] for p in face[2:4]]
    cx = sum(p.x for p in end_ring) / len(end_ring)
    cz = sum(p.z for p in end_ring) / len(end_ring)
    assert abs(cx - 3.0) < 1e-6 and abs(cz - 4.0) < 1e-6


def test_loft_between_scaled_squares_is_a_frustum():
    top = [(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)]
    sc = loft([SQUARE, top], heights=[0.0, 2.0])
    assert len(sc.faces) == 6
    top_pts = {(round(p.x, 3), round(p.y, 3)) for p in _verts(sc) if abs(p.z - 2.0) < 1e-9}
    assert (0.25, 0.25) in top_pts and (0.75, 0.75) in top_pts


def test_section_of_box_is_the_profile():
    sc = extrude(SQUARE, 5.0)
    loops = section_loops(sc, plane_point=(0, 0, 2.5), plane_normal=(0, 0, 1))
    assert len(loops) == 1
    assert abs(_area2(loops[0]) - 1.0) < 0.02


def test_section_of_torus_through_axis_gives_two_loops():
    from frameforge.sdk.manifold import torus
    sc = torus(1.0, 0.3, steps_u=48, steps_v=24)
    loops = section_loops(sc, plane_point=(0, 0, 0), plane_normal=(0, 0, 1))
    assert len(loops) == 2
    areas = sorted(_area2(lp) for lp in loops)
    assert all(a > 0.05 for a in areas)


def test_section_object_emits_a_valid_hatched_path():
    from frameforge.sdk import DocumentBuilder, validate_static_rules
    sc = extrude(SQUARE, 5.0)
    obj = section_object(sc, plane_point=(0, 0, 2.5), plane_normal=(0, 0, 1),
                        frame=[100, 100, 200, 200], hatch_color="#888888")
    b = DocumentBuilder(title="sect", profile="diagram")
    pg = b.page("p1", canvas={"size": [400, 400], "units": "px"})
    pg.layer("main")
    pg.rect([0, 0, 400, 400], fill="#FFFFFF")
    pg.add(obj)
    report = validate_static_rules(b.build())
    assert report.ok, [i.message for i in report.issues]
