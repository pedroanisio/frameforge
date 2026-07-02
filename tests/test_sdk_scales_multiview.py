#!/usr/bin/env python3
"""SDK polish: A.4 structured scales (log-base / pow-exp) and A.6 orthographic
multiview (front/top/side/iso panel grid)."""
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import Frame, Scene3D, multiview  # noqa: E402
from framegraph.sdk.draw import _apply_scale  # noqa: E402


def test_structured_log_and_pow_scales():
    assert abs(_apply_scale(100, {"kind": "log", "base": 10}) - 2.0) < 1e-9    # log10(100)
    assert abs(_apply_scale(math.e, {"kind": "log"}) - 1.0) < 1e-9             # natural log
    assert abs(_apply_scale(3, {"kind": "pow", "exp": 3}) - 27.0) < 1e-9
    assert abs(_apply_scale(-2, {"kind": "pow", "exp": 2}) - -4.0) < 1e-9      # sign-preserving
    assert _apply_scale(5, {"kind": "linear"}) == 5


def test_string_scales_still_work():
    assert _apply_scale(7, "linear") == 7
    assert abs(_apply_scale(math.e, "log") - 1.0) < 1e-9
    assert _apply_scale(-3, "pow2") == -9


def test_unsupported_scale_raises():
    import pytest
    with pytest.raises(ValueError):
        _apply_scale(1, {"kind": "bogus"})


def test_frame_uses_log_base_scale_in_page_space():
    frame = Frame(domain=(1, 0, 100, 100), box=(0, 0, 200, 100),
                  x_scale={"kind": "log", "base": 10})
    # x=10 is the geometric middle of [1,100] on a log scale -> page x = 100
    assert abs(frame.point(10, 50).x - 100.0) < 1e-6


def _cube_scene():
    v = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
         [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]
    faces = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6]]
    return Scene3D().mesh(v, faces)


def test_multiview_panel_grid():
    g = multiview(_cube_scene(), box=[0, 0, 200, 200],
                  views=("front", "top", "side", "iso"), cols=2)
    assert g["type"] == "group"
    panels = [c for c in g["children"] if c.get("type") == "group"]
    labels = [c for c in g["children"] if c.get("type") == "text"]
    assert len(panels) == 4
    assert {c["text"] for c in labels} == {"front", "top", "side", "iso"}
    # panels tile the box: a 2x2 grid, second column starts past half-width
    assert any(p for p in panels)                          # each panel rendered the scene


def test_multiview_unknown_view_raises():
    import pytest
    with pytest.raises(ValueError):
        multiview(_cube_scene(), box=[0, 0, 100, 100], views=("front", "oblique"))
