#!/usr/bin/env python3
"""test_scene3d_viewport_fit.py — B1 residual: Scene3D.render adopts the named
viewing-pipeline primitive for its window→viewport fit.

This is an *output-preserving* consolidation, not a behaviour change: `render`
formerly hand-rolled `scale = min(bw/ww, bh/wh)`, a second copy of exactly the
mapping `sdk.geometry.window_to_viewport` computes. These tests lock the contract
that render's fit **is** the primitive's fit (so the two can never silently
diverge again) and pin the exact rendered coordinates so the adoption is proven
byte-for-byte stable. Byte-identity across the fixture corpus is the golden gate's
job; this is the focused unit guard.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import Scene3D, Vec3  # noqa: E402
from framegraph.sdk.geometry import Mat4, window_to_viewport  # noqa: E402


def _scene():
    s = Scene3D()
    s.faces.append(([Vec3(0, 0, 0), Vec3(2, 0, 0), Vec3(2, 2, 0), Vec3(0, 2, 0)], {}))
    s.faces.append(([Vec3(0, 0, 0), Vec3(0, 0, 2), Vec3(0, 2, 2), Vec3(0, 2, 0)], {}))
    return s


def test_render_output_is_byte_stable():
    # Characterization lock: the default isometric projection of the two quads
    # fitted into box [10,20,100,80]. If this moves, the fit changed.
    g = _scene().render(box=[10, 20, 100, 80])
    assert g["box"] == [10, 20, 100, 80]
    rounded = [[[round(x, 6) for x in p] for p in ch["points"]] for ch in g["children"]]
    assert rounded == [
        [[32.679492, 20.0], [67.320508, 40.0], [67.320508, 80.0], [32.679492, 60.0]],
        [[32.679492, 20.0], [67.320508, 0.0], [67.320508, 40.0], [32.679492, 60.0]],
    ]


def test_render_fit_is_exactly_the_window_to_viewport_primitive():
    # Independently reproduce the fit via the B1 primitive and require the rendered
    # coordinates to match it EXACTLY — this is the contract render now honours.
    box = [10, 20, 100, 80]
    bw, bh = float(box[2]), float(box[3])
    m = Mat4.isometric()
    faces = [[m.try_project(p) for p in face] for face, _s in _scene().faces]
    allp = [q for face in faces for q in face]
    min_x = min(q.x for q in allp)
    max_x = max(q.x for q in allp)
    min_y = min(q.y for q in allp)
    max_y = max(q.y for q in allp)
    window = [min_x, min_y, max(max_x - min_x, 1e-9), max(max_y - min_y, 1e-9)]
    scale = window_to_viewport(window, [0.0, 0.0, bw, bh], uniform=True).a
    ox = (bw - (max_x - min_x) * scale) / 2
    oy = (bh - (max_y - min_y) * scale) / 2
    expected = [[[ox + (q.x - min_x) * scale, oy + (q.y - min_y) * scale] for q in face]
                for face in faces]

    rendered = [ch["points"] for ch in _scene().render(box=box)["children"]]
    # render depth-sorts faces; compare as sets of face point-lists (order-free).
    assert sorted(map(repr, rendered)) == sorted(map(repr, expected))
