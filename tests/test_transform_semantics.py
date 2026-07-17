#!/usr/bin/env python3
"""
test_transform_semantics.py — transform semantics before pixels (BHAG C1).

Covers the Pass-1 confirmed transform defects:

* TX-1  ObjBase.rotation was silently ignored by the SVG path: it must emit a
        rotate() about the box centre (or the geometry centre for box-less
        objects, or an explicit {angle, center}), composed AFTER style.transform.
* TX-2  A STRING-form style.transform with no transform_origin pivoted on the
        local origin (0,0) while the dict form defaults to the box centre
        (spec §3.6b: "transform_origin defaults to the box centre").
* TX-5  Dict-form rotate/scale/skew on box-less geometry (center / from+to /
        points) got no default origin and orbited the local origin.
* TX-3  transform_arg quantized MULTIPLICATIVE args (scale/skew/matrix) to
        3 decimals; the error is amplified by coordinate extent (~1.9 px at 4K).
        Additive/near-additive args (translate, rotate angle) stay at fnum.

Renderer-only import (the `frameforge` package must win) — evict a models-module
shadow first, per test_element_render.py.
"""
import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # the models module
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling.render_fixtures import Renderer  # noqa: E402
from frameforge.rendering.domain.services.style_values import StyleValues  # noqa: E402


def _page_svg(objects):
    doc = {
        "dsl": "FrameForge",
        "version": "2.4.0",
        "pages": [{"id": "p", "mode": "page", "canvas": {"size": [3840, 2160]},
                   "layers": [{"id": "l", "objects": objects}]}],
    }
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


CSS = StyleValues()


def _flat(ops):
    """Format a neutral op list the way the SVG painter does."""
    parts = []
    for fn, args in ops:
        parts.append((args[0] if args else "") if fn == "raw" else f"{fn}({' '.join(args)})")
    return " ".join(p for p in parts if p)


# --------------------------------------------------------------------------- #
#  TX-1 — ObjBase.rotation reaches the SVG output                             #
# --------------------------------------------------------------------------- #

def test_tx1_rotation_number_pivots_box_center():
    svg = _page_svg([{"type": "rect", "box": [1600, 900, 400, 300],
                      "fill": "#123456", "rotation": 30}])
    assert "rotate(30 1800 1050)" in svg


def test_tx1_rotation_dict_uses_explicit_center():
    svg = _page_svg([{"type": "rect", "box": [0, 0, 100, 100], "fill": "#123456",
                      "rotation": {"angle": 45, "center": [100, 200]}}])
    assert "rotate(45 100 200)" in svg


def test_tx1_rotation_composes_after_style_transform():
    # rotation must wrap OUTSIDE the style.transform group (applied after it)
    svg = _page_svg([{"type": "rect", "box": [100, 100, 200, 100], "fill": "#123456",
                      "rotation": 90,
                      "style": {"transform": [{"fn": "translate", "args": [50, 0]}]}}])
    i_rot = svg.find("rotate(90 200 150)")
    i_tr = svg.find("translate(50 0)")
    assert i_rot != -1 and i_tr != -1
    assert i_rot < i_tr, "rotation group must nest outside the style.transform group"


def test_tx1_rotation_boxless_uses_geometry_center():
    svg = _page_svg([{"type": "circle", "center": [500, 400], "r": 50,
                      "fill": "#123456", "rotation": 30}])
    assert "rotate(30 500 400)" in svg


def test_tx1_zero_rotation_emits_nothing():
    svg = _page_svg([{"type": "rect", "box": [0, 0, 10, 10], "fill": "#123456",
                      "rotation": 0}])
    assert "rotate(" not in svg


# --------------------------------------------------------------------------- #
#  TX-2 — string transform defaults its origin to the box centre              #
# --------------------------------------------------------------------------- #

def test_tx2_string_transform_defaults_to_box_center():
    ops = CSS.transform_ops("rotate(2deg)", None, [1600, 900, 400, 300])
    flat = _flat(ops)
    assert "translate(1800,1050)" in flat and "rotate(2)" in flat \
        and "translate(-1800,-1050)" in flat


def test_tx2_string_transform_explicit_origin_unchanged():
    ops = CSS.transform_ops("rotate(2deg)", [10, 20], [1600, 900, 400, 300])
    flat = _flat(ops)
    assert "translate(10,20)" in flat and "translate(-10,-20)" in flat


def test_tx2_string_transform_no_box_no_origin_stays_raw():
    ops = CSS.transform_ops("rotate(2deg)", None, None)
    assert ops == [("raw", ["rotate(2)"])]


def test_tx2_dict_and_string_forms_agree():
    box = [1600, 900, 400, 300]
    d = _flat(CSS.transform_ops([{"fn": "rotate", "args": [2]}], None, box))
    s = _flat(CSS.transform_ops("rotate(2deg)", None, box))
    # dict form bakes the pivot into rotate(a cx cy); string form sandwiches —
    # both must pivot on (1800, 1050)
    assert "1800" in d and "1050" in d
    assert "1800" in s and "1050" in s


# --------------------------------------------------------------------------- #
#  TX-5 — dict ops on box-less geometry default to the geometry centre        #
# --------------------------------------------------------------------------- #

def test_tx5_rotate_on_circle_pivots_center():
    svg = _page_svg([{"type": "circle", "center": [1900, 1000], "r": 40,
                      "fill": "#123456",
                      "style": {"transform": [{"fn": "rotate", "args": [5]}]}}])
    assert "rotate(5 1900 1000)" in svg


def test_tx5_scale_on_ellipse_gets_origin_sandwich():
    svg = _page_svg([{"type": "ellipse", "center": [500, 500], "rx": 40, "ry": 20,
                      "fill": "#123456",
                      "style": {"transform": [{"fn": "scale", "args": [1.1]}]}}])
    assert "translate(500 500)" in svg and "translate(-500 -500)" in svg


def test_tx5_rotate_on_line_pivots_midpoint():
    svg = _page_svg([{"type": "line", "from": [100, 100], "to": [300, 200],
                      "stroke": "#123456",
                      "style": {"transform": [{"fn": "rotate", "args": [10]}]}}])
    assert "rotate(10 200 150)" in svg


def test_tx5_rotate_on_polygon_pivots_points_bbox_center():
    svg = _page_svg([{"type": "polygon", "points": [[0, 0], [100, 0], [100, 60]],
                      "fill": "#123456",
                      "style": {"transform": [{"fn": "rotate", "args": [10]}]}}])
    assert "rotate(10 50 30)" in svg


# --------------------------------------------------------------------------- #
#  TX-3 — multiplicative transform args keep high precision                   #
# --------------------------------------------------------------------------- #

def test_tx3_matrix_args_are_precise():
    s, c = math.sin(math.radians(1)), math.cos(math.radians(1))
    ops = CSS.transform_ops([{"fn": "matrix", "args": [c, s, -s, c, 0, 0]}], None, None)
    (fn, args), = ops
    assert fn == "matrix"
    # sin(1°) = 0.0174524064... must NOT collapse to "0.017"
    assert args[1] == "0.0174524064"
    assert args[0] == "0.999847695"


def test_tx3_scale_arg_is_precise():
    ops = CSS.transform_ops([{"fn": "scale", "args": [0.99949]}], None, None)
    assert any("0.99949" in a for _, args in ops for a in args), ops


def test_tx3_skew_arg_is_precise():
    ops = CSS.transform_ops([{"fn": "skew_x", "args": [10.00049]}], None, None)
    assert any(a == "10.00049" for _, args in ops for a in args), ops


def test_tx3_translate_args_stay_compact():
    ops = CSS.transform_ops([{"fn": "translate", "args": [1.23456, 2]}], None, None)
    assert ops == [("translate", ["1.235", "2"])]


def test_tx3_rotate_angle_stays_compact():
    # rotate-angle quantization displaces ≤ r·δθ ≈ 0.04 px at the 4K diagonal —
    # deliberately kept at fnum (byte-stable output)
    ops = CSS.transform_ops([{"fn": "rotate", "args": [1.23456]}], None, None)
    assert ops == [("rotate", ["1.235"])]


# --------------------------------------------------------------------------- #
#  TX-8 — clip-inside-transform is LOAD-BEARING (documented, locked)          #
# --------------------------------------------------------------------------- #

def test_tx8_clip_nests_inside_transform():
    # CSS local-clip composition: the clip group nests INSIDE the transform
    # group, so the clip window rides along with the object's transform.
    # Committed examples rely on this (ski_rebuilt_composition.py builds
    # page-space masks by nesting the clip on a static parent instead) —
    # this test locks the order so it cannot be silently "fixed".
    svg = _page_svg([{"type": "rect", "box": [0, 0, 100, 100], "fill": "#123456",
                      "style": {"transform": [{"fn": "translate", "args": [200, 0]}],
                                "clip_path": {"shape": "inset",
                                              "args": {"top": 10}}}}])
    i_tr = svg.find("translate(200 0)")
    i_clip = svg.find("clip-path=")
    assert i_tr != -1 and i_clip != -1
    assert i_tr < i_clip, "clip group must nest inside the transform group"


# --------------------------------------------------------------------------- #
#  TX-4 / NUMFMT-1 — emit_figure fit scale at emitted precision               #
# --------------------------------------------------------------------------- #

def test_tx4_flow_figure_scale_emitted_precise():
    doc = {
        "dsl": "FrameForge",
        "version": "2.4.0",
        "pages": [{
            "id": "p", "mode": "flow", "canvas": {"size": [3840, 2160]},
            "story": [{
                "type": "figure", "id": "fig", "size": [6100, 1000],
                "object": {"type": "rect", "box": [0, 0, 6100, 1000],
                           "fill": "#123456"},
            }],
        }],
    }
    svg = Renderer(doc, ".").render_page(doc["pages"][0])[0]
    m = re.search(r"scale\(([0-9.]+)\)", svg)
    assert m, "flow figure must emit a fit scale"
    emitted = m.group(1)
    # 3-decimal quantization (e.g. "0.488") costs up to fw·5e-4 ≈ 3 px at
    # fw=6100; the emitted scale must carry fnum_precise's 9 significant digits
    frac = emitted.split(".", 1)[1] if "." in emitted else ""
    assert len(frac) > 3, f"fit scale still 3-decimal quantized: {emitted}"
    # and it must round-trip to the exact value the layout used
    from frameforge.rendering.domain.geometry import fnum_precise
    assert emitted == fnum_precise(float(emitted))
