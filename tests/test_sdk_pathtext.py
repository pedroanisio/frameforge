#!/usr/bin/env python3
"""text_on_path — per-glyph type along a polyline path (reconstruction gap F3).

Hand-rolled twice in real reconstruction sessions (arc captions, a poster
sweep); both times the same two bugs appeared: glyphs offset to the convex
side, and advances measured on the centreline instead of the offset path.
These tests pin the primitive that makes both impossible.
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

from frameforge.sdk import DocumentBuilder, validate_static_rules  # noqa: E402
from frameforge.sdk.pathtext import offset_path, path_length, text_on_path  # noqa: E402
from frameforge.sdk.metrics import measure_text  # noqa: E402

FAM = "DejaVu Sans"


def circle_path(cx, cy, r, a0, a1, n=64):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def test_path_length_straight():
    assert abs(path_length([(0, 0), (30, 40)]) - 50.0) < 1e-9


def test_offset_path_left_normal_convention():
    # straight left→right path: +offset is the left normal (−ty, tx) → +y (down)
    pts = offset_path([(0, 0), (100, 0)], 10)
    assert all(abs(y - 10) < 1e-6 for _x, y in pts)
    # and on a circle traversed with increasing angle, +offset moves toward centre
    ring = offset_path(circle_path(0, 0, 100, -90, 90), 15)
    radii = [math.hypot(x, y) for x, y in ring]
    assert all(abs(r - 85) < 1.5 for r in radii)


def test_glyphs_skip_spaces_and_rotate_with_tangent():
    objs = text_on_path(circle_path(200, 200, 150, -90, 0), "AB C",
                        size=20, family=FAM)
    assert [o["text"] for o in objs] == ["A", "B", "C"]
    assert all(o["type"] == "text" for o in objs)
    rots = [o["rotation"] for o in objs]
    assert rots == sorted(rots)          # tangent angle grows along this arc
    assert rots[0] >= -5 and rots[-1] <= 95


def test_advance_spacing_uses_real_metrics_on_the_offset_path():
    # straight path so spacing is directly measurable
    track = 3.0
    size = 24.0
    objs = text_on_path([(0, 100), (600, 100)], "HH", size=size, family=FAM,
                        track=track)
    (x0, y0) = objs[0]["box"][0], objs[0]["box"][1]
    (x1, y1) = objs[1]["box"][0], objs[1]["box"][1]
    w = measure_text("H", font_family=FAM, font_size=size)
    assert abs((x1 - x0) - (w + track)) < 0.75
    assert abs(y1 - y0) < 1e-6


def test_offset_glyphs_sit_on_the_concave_side():
    C, R, off = (300.0, 300.0), 200.0, 30.0
    objs = text_on_path(circle_path(*C, R, -120, 30), "MMMM", size=22, family=FAM,
                        offset=off)
    for o in objs:
        gx = o["box"][0] + o["box"][2] / 2.0
        gy = o["box"][1] + o["box"][3] * 0.55
        d = math.hypot(gx - C[0], gy - C[1])
        assert abs(d - (R - off)) < 6.0, f"glyph at radius {d:.1f}, expected ~{R - off}"


def test_objects_validate_in_a_document():
    b = DocumentBuilder(title="pathtext", profile="diagram")
    pg = b.page("p1", canvas={"size": [800, 600], "units": "px"}, coordinate_mode="absolute")
    pg.layer("main")
    pg.rect([0, 0, 800, 600], fill="#FFFFFF")
    with pg.lettering():
        pg.extend(text_on_path(circle_path(400, 300, 200, -160, -20), "CURVED TYPE",
                               size=28, family=FAM, color="#222222"))
    report = validate_static_rules(b.build())
    assert report.ok, [i.message for i in report.issues]
