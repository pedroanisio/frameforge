#!/usr/bin/env python3
"""array — the CAD pattern operator (linear / polar / along-path).

Instances are real objects: geometry-translated where the object carries
box/center/from-to (the place_stamp fast paths), style-transform groups where
rotation is involved (the renderer's one supported transform channel).
"""
from __future__ import annotations

import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from frameforge.sdk.macros import array  # noqa: E402

RECT = {"type": "rect", "box": [10.0, 10.0, 20.0, 12.0], "fill": "#AA3311"}


def test_linear_array_translates_geometry():
    out = array(RECT, linear=(30, 0, 4))
    assert len(out) == 4
    assert [o["box"][0] for o in out] == [10.0, 40.0, 70.0, 100.0]
    assert all(o["type"] == "rect" for o in out)
    assert RECT["box"] == [10.0, 10.0, 20.0, 12.0]      # source untouched


def test_polar_array_rotates_about_pivot():
    out = array(RECT, polar=(100, 100, 6))
    assert len(out) == 6
    assert all(o["type"] == "group" for o in out)
    angles = []
    for o in out:
        tf = o["style"]["transform"]
        rots = [fn for fn in tf if fn["fn"] == "rotate"]
        assert len(rots) == 1
        angles.append(rots[0]["args"][0] % 360)
    assert angles == pytest.approx([0.0, 60.0, 120.0, 180.0, 240.0, 300.0])


def test_polar_without_item_rotation_orbits_positions_only():
    out = array(RECT, polar=(100, 100, 4), rotate_items=False)
    assert all(o["type"] == "rect" for o in out)
    # bbox centre starts at (20, 16); orbit radius stays constant about (100, 100)
    r0 = math.hypot(20 - 100, 16 - 100)
    for o in out:
        cx = o["box"][0] + o["box"][2] / 2
        cy = o["box"][1] + o["box"][3] / 2
        assert math.hypot(cx - 100, cy - 100) == pytest.approx(r0, abs=1e-6)
    centres = {(round(o["box"][0], 3), round(o["box"][1], 3)) for o in out}
    assert len(centres) == 4


def test_along_array_follows_tangent():
    stamp = {"type": "rect", "box": [-4.0, -2.0, 8.0, 4.0], "fill": "#2255AA"}
    out = array(stamp, along=[(0, 0), (100, 100)], spacing=(100 * math.sqrt(2)) / 4)
    assert len(out) == 5
    assert all(o["type"] == "group" for o in out)
    tf = out[2]["style"]["transform"]
    rot = [fn for fn in tf if fn["fn"] == "rotate"][0]
    assert rot["args"][0] == pytest.approx(45.0, abs=0.5)


def test_arrays_validate_and_render():
    from frameforge.sdk import DocumentBuilder, validate_static_rules
    from frameforge.sdk.conform import render_page_svgs
    b = DocumentBuilder(title="arr", profile="diagram")
    pg = b.page("p1", canvas={"size": [400, 300], "units": "px"})
    pg.layer("main")
    pg.rect([0, 0, 400, 300], fill="#FFFFFF")
    pg.extend(array({"type": "rect", "box": [20.0, 20.0, 30.0, 18.0], "fill": "#AA3311"},
                    linear=(40, 20, 3)))
    pg.extend(array({"type": "rect", "box": [180.0, 130.0, 24.0, 10.0], "fill": "#11AA33"},
                    polar=(250, 150, 5)))
    doc = b.build()
    report = validate_static_rules(doc)
    assert report.ok, [i.message for i in report.issues]
    svg = render_page_svgs(doc)[0]
    assert svg.count("#AA3311") == 3
    assert svg.count("#11AA33") == 5
    assert "rotate(" in svg


def test_mode_exclusivity():
    with pytest.raises(ValueError):
        array(RECT, linear=(1, 1, 2), polar=(0, 0, 3))
    with pytest.raises(ValueError):
        array(RECT)
