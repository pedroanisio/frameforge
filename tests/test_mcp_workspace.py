#!/usr/bin/env python3
"""The coordinate workspace, vector construction, and 2D/3D mapping.

These pin the stateful behaviour (pins persist across calls, nudge/move/multi-adjust,
viewport pan/zoom with fixed aim), the anchor→vector construction (shapes render), and
the coordinate transposition math (homography / plane lift / projection).
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from framegraph.mcp.server import (  # noqa: E402
    construct_vectors,
    map_coordinates,
    workspace,
)


def _png(path, color=(140, 150, 160), size=(200, 100)):
    Image.new("RGB", size, color).save(path, format="PNG")
    return str(path)


def _pin_by_id(result, pid):
    return next(p for p in result["spatial"]["pins"] if p["id"] == pid)


# ─────────────────────────────────────────────────────────────
# workspace — stateful pins
# ─────────────────────────────────────────────────────────────
def test_workspace_open_then_pin_persists_across_calls(tmp_path):
    img = _png(tmp_path / "src.png")
    assert workspace("open", image=img, session_id="w", session_root=tmp_path)["ok"] is True
    workspace("pin", points=[{"norm": [0.5, 0.5], "label": "nose"}],
              session_id="w", session_root=tmp_path)
    # a fresh call in the same session still sees the pin (persisted to workspace.json)
    r = workspace("render", session_id="w", session_root=tmp_path)
    assert r["spatial"]["pin_count"] == 1
    assert _pin_by_id(r, "P1")["image_px"] == [100.0, 50.0]


def test_workspace_open_requires_image(tmp_path):
    r = workspace("pin", points=[{"norm": [0.5, 0.5]}], session_id="none", session_root=tmp_path)
    assert r["ok"] is False and "open" in r["error"]


def test_workspace_state_is_readable_as_a_resource(tmp_path):
    """The persisted pins are exposed at framegraph://session/<id>/workspace.json."""
    import json

    from framegraph.mcp.sessions import read_session_resource

    img = _png(tmp_path / "src.png")
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [12, 34], "id": "a"}], session_id="w", session_root=tmp_path)
    payload = read_session_resource("framegraph://session/w/workspace.json", session_root=tmp_path)
    assert payload["mimeType"] == "application/json"
    state = json.loads(payload["text"])
    assert state["image_ref"] == img
    assert [(p["id"], p["x"], p["y"]) for p in state["pins"]] == [("a", 12.0, 34.0)]


def test_workspace_nudge_is_the_ai_mouse(tmp_path):
    img = _png(tmp_path / "src.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"norm": [0.5, 0.5]}], session_id="w", session_root=tmp_path)
    # 0.01 norm left on a 200px-wide image = -2px
    r = workspace("nudge", select={"ids": ["P1"]}, dx=-0.01, dy=0.0, unit="norm",
                  session_id="w", session_root=tmp_path)
    assert _pin_by_id(r, "P1")["image_px"] == [98.0, 50.0]


def test_workspace_multi_pin_and_group_adjust(tmp_path):
    img = _png(tmp_path / "src.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[
        {"px": [10, 10], "group": "eyes"},
        {"px": [30, 10], "group": "eyes"},
        {"px": [20, 40], "group": "mouth"},
    ], session_id="w", session_root=tmp_path)
    # nudge only the "eyes" group by +5px x
    r = workspace("nudge", select={"group": "eyes"}, dx=5, dy=0, unit="px",
                  session_id="w", session_root=tmp_path)
    assert _pin_by_id(r, "P1")["image_px"] == [15.0, 10.0]
    assert _pin_by_id(r, "P2")["image_px"] == [35.0, 10.0]
    assert _pin_by_id(r, "P3")["image_px"] == [20.0, 40.0]   # mouth untouched


def test_workspace_pin_can_reference_existing_pin(tmp_path):
    img = _png(tmp_path / "src.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [50, 50], "id": "base"}], session_id="w", session_root=tmp_path)
    r = workspace("pin", points=[{"landmark": "base", "dx": 10, "dy": -5, "id": "rel"}],
                  session_id="w", session_root=tmp_path)
    assert _pin_by_id(r, "rel")["image_px"] == [60.0, 45.0]


def test_workspace_viewport_sets_and_reports_viewport_frame(tmp_path):
    img = _png(tmp_path / "src.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"norm": [0.5, 0.5]}], session_id="w", session_root=tmp_path)
    r = workspace("viewport", viewport={"name": "eye", "box": [0.4, 0.4, 0.2, 0.2]},
                  session_id="w", session_root=tmp_path)
    assert r["spatial"]["viewport"]["name"] == "eye"
    # overlay + viewport crop are both rendered
    assert len(r["renders"]) == 2
    assert "viewport" in _pin_by_id(r, "P1")


def test_workspace_snap_to_bright(tmp_path):
    """snap moves a pin onto the nearest bright pixel within radius."""
    from PIL import ImageDraw  # noqa: F401
    im = Image.new("RGB", (100, 100), (10, 10, 10))
    im.putpixel((60, 40), (255, 255, 255))
    p = str(tmp_path / "dot.png")
    im.save(p)
    workspace("open", image=p, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [58, 42], "id": "a"}], session_id="w", session_root=tmp_path)
    r = workspace("snap", select={"ids": ["a"]}, snap_to="bright", radius=5,
                  session_id="w", session_root=tmp_path)
    assert r["ok"] is True
    assert _pin_by_id(r, "a")["image_px"] == [60.0, 40.0]


def test_workspace_transform_rotates_group_about_pivot(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 200))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [110, 100], "id": "a"}, {"px": [100, 110], "id": "b"}],
              session_id="w", session_root=tmp_path)
    # +90° about (100,100), image coords (y down): (110,100)->(100,110); (100,110)->(90,100)
    r = workspace("transform", select={"ids": ["a", "b"]}, rotate=90, aim={"px": [100, 100]},
                  session_id="w", session_root=tmp_path)
    assert _pin_by_id(r, "a")["image_px"] == [100.0, 110.0]
    assert _pin_by_id(r, "b")["image_px"] == [90.0, 100.0]


def test_workspace_transform_scales_group_about_pivot(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 200))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [110, 100], "id": "a"}], session_id="w", session_root=tmp_path)
    r = workspace("transform", select={"ids": ["a"]}, scale=2.0, aim={"px": [100, 100]},
                  session_id="w", session_root=tmp_path)
    assert _pin_by_id(r, "a")["image_px"] == [120.0, 100.0]


def test_workspace_checkpoint_then_revert(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [50, 50], "id": "a"}], session_id="w", session_root=tmp_path)
    c = workspace("checkpoint", tag="base", session_id="w", session_root=tmp_path)
    assert c["action_info"]["checkpoint_index"] == 0 and c["checkpoint_count"] == 1
    moved = workspace("nudge", select={"ids": ["a"]}, dx=10, dy=0, unit="px",
                      session_id="w", session_root=tmp_path)
    assert _pin_by_id(moved, "a")["image_px"] == [60.0, 50.0]
    r = workspace("revert", session_id="w", session_root=tmp_path)
    assert _pin_by_id(r, "a")["image_px"] == [50.0, 50.0]      # restored
    assert r["action_info"]["reverted_to"] == 0
    assert r["checkpoint_count"] == 0                           # checkpoint consumed


def test_workspace_revert_without_checkpoint_is_error(tmp_path):
    img = _png(tmp_path / "s.png")
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    r = workspace("revert", session_id="w", session_root=tmp_path)
    assert r["ok"] is False and "checkpoint" in r["error"]


def test_workspace_zoom_keeps_aim_centred(tmp_path):
    img = _png(tmp_path / "src.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [100, 50], "id": "aim"}], session_id="w", session_root=tmp_path)
    workspace("viewport", viewport={"box": [0.0, 0.0, 1.0, 1.0]}, session_id="w", session_root=tmp_path)
    r = workspace("zoom", factor=2.0, aim={"landmark": "aim"}, session_id="w", session_root=tmp_path)
    vp = r["spatial"]["viewport"]["box_norm"]
    # aim (0.5, 0.5) stays centred: box centre == 0.5
    assert round(vp[0] + vp[2] / 2, 6) == 0.5
    assert round(vp[1] + vp[3] / 2, 6) == 0.5


# ─────────────────────────────────────────────────────────────
# vector construction
# ─────────────────────────────────────────────────────────────
def test_construct_vectors_from_explicit_points(tmp_path):
    r = construct_vectors(
        [{"kind": "rect", "points": [[10, 10], [90, 60]]},
         {"kind": "circle", "points": [[50, 50], [70, 50]]},
         {"kind": "line", "points": [[0, 0], [100, 100]]}],
        width=200, height=120, session_id="c", session_root=tmp_path,
    )
    assert r["ok"] is True, r.get("error")
    assert r["shape_count"] == 3
    assert [s["kind"] for s in r["construction"]] == ["rect", "circle", "line"]
    assert r["renders"] and os.path.isfile(r["renders"][0]["path"])


def test_construct_vectors_from_workspace_pins(tmp_path):
    img = _png(tmp_path / "src.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [20, 20]}, {"px": [180, 20]}, {"px": [100, 90]}],
              session_id="w", session_root=tmp_path)
    r = construct_vectors(
        [{"kind": "triangle", "pins": ["P1", "P2", "P3"], "style": {"stroke": "#0a7", "fill": "#dfe"}}],
        from_workspace="w", session_id="c", session_root=tmp_path,
    )
    assert r["ok"] is True, r.get("error")
    assert r["shape_count"] == 1
    # canvas inherited the workspace image dimensions
    assert r["renders"]


def test_construct_vectors_unknown_kind_is_structured_error(tmp_path):
    r = construct_vectors([{"kind": "banana", "points": [[0, 0]]}],
                          width=100, height=100, session_id="c", session_root=tmp_path)
    assert r["ok"] is False and "banana" in r["error"]


def test_construct_vectors_empty_is_error(tmp_path):
    r = construct_vectors([], width=100, height=100, session_id="c", session_root=tmp_path)
    assert r["ok"] is False


# ─────────────────────────────────────────────────────────────
# 2D / 3D mapping
# ─────────────────────────────────────────────────────────────
def test_map_homography_recovers_scale():
    r = map_coordinates(
        "homography",
        pairs=[{"src": [0, 0], "dst": [0, 0]}, {"src": [1, 0], "dst": [2, 0]},
               {"src": [1, 1], "dst": [2, 2]}, {"src": [0, 1], "dst": [0, 2]}],
        points=[[0.5, 0.5]],
    )
    assert r["ok"] is True
    assert r["spatial"]["mapped_points"][0] == [1.0, 1.0]
    assert r["spatial"]["rms_residual_px"] == 0.0


def test_map_to_3d_default_plane_is_z0():
    r = map_coordinates("to_3d", points=[[10, 20], [0, 0]])
    assert r["ok"] is True
    assert r["spatial"]["points_3d"] == [[10.0, 20.0, 0.0], [0.0, 0.0, 0.0]]


def test_map_to_3d_custom_plane():
    r = map_coordinates("to_3d", points=[[1, 1]],
                        plane={"origin": [0, 0, 5], "u": [2, 0, 0], "v": [0, 0, 1]})
    # P = (0,0,5) + 1*(2,0,0) + 1*(0,0,1) = (2, 0, 6)
    assert r["spatial"]["points_3d"][0] == [2.0, 0.0, 6.0]


def test_map_project_is_deterministic_and_returns_pixels():
    args = dict(points=[[0.0, 0.0, 0.0]], camera={"eye": [0, 0, 5]}, width=200, height=100)
    a = map_coordinates("project", **args)
    b = map_coordinates("project", **args)
    assert a["ok"] is True
    assert len(a["spatial"]["points_ndc"][0]) == 2
    assert len(a["spatial"]["points_px"][0]) == 2
    assert a["spatial"] == b["spatial"]   # deterministic


def test_map_unknown_mode_is_error():
    r = map_coordinates("teleport", points=[[0, 0]])
    assert r["ok"] is False and "unknown mode" in r["error"]


def test_map_warp_rectifies_an_image(tmp_path):
    try:
        import cv2  # noqa: F401
    except Exception:
        pytest.skip("OpenCV not installed")
    img = _png(tmp_path / "s.png", size=(100, 100))
    pairs = [{"src": [0, 0], "dst": [0, 0]}, {"src": [100, 0], "dst": [100, 0]},
             {"src": [100, 100], "dst": [100, 100]}, {"src": [0, 100], "dst": [0, 100]}]
    r = map_coordinates("warp", pairs=pairs, image=img, out_size=[100, 100],
                        session_id="warp", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["renders"] and os.path.isfile(r["renders"][0]["path"])
    assert r["spatial"]["out_size"] == [100, 100]


def test_map_warp_needs_image_and_pairs(tmp_path):
    r = map_coordinates("warp", pairs=[{"src": [0, 0], "dst": [0, 0]}],
                        session_id="warp2", session_root=tmp_path)
    assert r["ok"] is False and "4 pairs" in r["error"]
