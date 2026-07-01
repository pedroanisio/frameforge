#!/usr/bin/env python3
"""Regression net for the coordinate-aware vision workspace, mapped to the 9 goal
requirements. Where test_mcp_measure.py / test_mcp_workspace.py pin the unit-level
geometry, this file guards the *feature surface* end to end — every shape kind, every
nudge direction/unit, grid configurability, the fixed-aim coordinate-continuity
invariant, overlay opacity/offsets, and the 2D/3D transforms — so a change that
silently drops or breaks a capability fails here.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

pytest.importorskip("PIL")

from PIL import Image, ImageDraw  # noqa: E402

from framegraph.mcp.server import (  # noqa: E402
    construct_vectors,
    create_server,
    map_coordinates,
    mark_points,
    measure_image,
    mcp_content_blocks,
    overlay_images,
    score_reconstruction,
    workspace,
)
from framegraph.vision.infrastructure.mapping3d import apply_homography  # noqa: E402
from framegraph.vision.infrastructure.measure import (  # noqa: E402
    CoordinateSystem,
    detected_landmarks,
)
from framegraph.vision.infrastructure.overlay_align import (  # noqa: E402
    fit_similarity,
    landmark_offsets,
    rms_residual,
)


def _png(path, color=(140, 150, 160), size=(200, 100)):
    Image.new("RGB", size, color).save(path, format="PNG")
    return str(path)


def _two_color_png_bytes(size=(200, 120)) -> bytes:
    from io import BytesIO

    im = Image.new("RGB", size, (240, 240, 235))
    d = ImageDraw.Draw(im)
    d.rectangle([20, 20, 120, 90], fill=(40, 90, 200))
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _pin(result, pid):
    return next(p for p in result["spatial"]["pins"] if p["id"] == pid)


# ══════════════════════════════════════════════════════════════
# Feature-surface guard: every tool stays registered
# ══════════════════════════════════════════════════════════════
def test_all_vision_tools_are_registered():
    tools = {t.name for t in asyncio.run(create_server().list_tools())}
    for name in ("measure_image", "mark_points", "overlay_images",
                 "workspace", "construct_vectors", "score_reconstruction",
                 "vectorize_image", "map_coordinates"):
        assert name in tools, f"{name} is not registered"


def _edge_png(path, size=(240, 180)):
    im = Image.new("RGB", size, (245, 245, 245))
    ImageDraw.Draw(im).line([(0, 90), (size[0], 90)], fill=(0, 0, 0), width=2)
    im.save(path, format="PNG")
    return str(path)


def test_score_reconstruction_is_the_numeric_convergence_signal(tmp_path):
    """Shapes ON the source's edges score a higher on_edge_frac than shapes OFF —
    a numeric signal to drive the raster→vector loop, over a rendered match overlay
    whose score is surfaced in the model-facing summary."""
    p = _edge_png(tmp_path / "edge.png")
    on = score_reconstruction(p, [{"kind": "line", "points": [[20, 90], [220, 90]]}],
                              session_id="scon", session_root=tmp_path)
    off = score_reconstruction(p, [{"kind": "line", "points": [[20, 20], [220, 20]]}],
                               session_id="scoff", session_root=tmp_path)
    assert on["ok"] is True and on["score"]["on_edge_frac"] > 0.9
    assert off["score"]["on_edge_frac"] < 0.2
    assert on["score"]["on_edge_frac"] > off["score"]["on_edge_frac"]
    # a match overlay PNG is written and the score rides the model-facing summary
    assert on["renders"] and os.path.isfile(on["renders"][0]["path"])
    summary = json.loads(mcp_content_blocks(on)[0]["text"])
    assert summary["score"]["on_edge_frac"] > 0.9
    # error contract
    assert score_reconstruction(p, [], session_id="e", session_root=tmp_path)["ok"] is False


def test_score_reconstruction_resolves_pins_from_workspace(tmp_path):
    p = _edge_png(tmp_path / "edge.png")
    workspace("open", image=p, session_id="wsp", session_root=tmp_path)
    workspace("pin", points=[{"px": [20, 90], "id": "a"}, {"px": [220, 90], "id": "b"}],
              session_id="wsp", session_root=tmp_path)
    r = score_reconstruction(p, [{"kind": "line", "pins": ["a", "b"]}],
                             from_workspace="wsp", session_id="sc", session_root=tmp_path)
    assert r["ok"] is True and r["score"]["on_edge_frac"] > 0.9


def test_score_reconstruction_same_session_after_construct_does_not_crash(tmp_path):
    """The documented loop shares one session_id across construct_vectors → score.
    construct creates a session dir with no workspace.json; score must NOT crash on it."""
    p = _edge_png(tmp_path / "edge.png")
    construct_vectors([{"kind": "line", "points": [[20, 90], [220, 90]]}],
                      image=p, session_id="loop", session_root=tmp_path)
    r = score_reconstruction(p, [{"kind": "line", "points": [[20, 90], [220, 90]]}],
                             session_id="loop", session_root=tmp_path)
    assert r["ok"] is True and r["score"]["on_edge_frac"] > 0.9


def test_score_reconstruction_unknown_pin_is_a_structured_error(tmp_path):
    p = _edge_png(tmp_path / "edge.png")
    workspace("open", image=p, session_id="wu", session_root=tmp_path)
    workspace("pin", points=[{"px": [20, 90], "id": "a"}], session_id="wu", session_root=tmp_path)
    r = score_reconstruction(p, [{"kind": "line", "pins": ["a", "zzz"]}],
                             from_workspace="wu", session_id="sc2", session_root=tmp_path)
    assert r["ok"] is False and "unknown pin" in r["error"]


def test_score_reconstruction_scoring_error_matches_sibling_envelope(tmp_path):
    """A no-edge image is a scoring error; the envelope must match the sibling tools:
    a top-level `error` string and empty renders/resources (not a nested-only error)."""
    blank = str(tmp_path / "blank.png")
    Image.new("RGB", (240, 180), (245, 245, 245)).save(blank, format="PNG")
    r = score_reconstruction(blank, [{"kind": "line", "points": [[20, 90], [220, 90]]}],
                             session_id="se", session_root=tmp_path)
    assert r["ok"] is False
    assert isinstance(r.get("error"), str) and r["error"]
    assert r["renders"] == [] and r["resources"] == []


# ══════════════════════════════════════════════════════════════
# REQ 1 — Coordinate grid + measurement layer (configurable)
# ══════════════════════════════════════════════════════════════
def test_req1_grid_step_is_configurable(tmp_path):
    img = _png(tmp_path / "s.png")
    r = measure_image(img, grid_step=25, detect_landmarks=False,
                      session_id="g", session_root=tmp_path)
    assert r["spatial"]["grid"]["step_px"] == 25
    assert r["spatial"]["rulers"]["step_px"] == 25


def test_req1_grid_and_rulers_can_be_disabled(tmp_path):
    img = _png(tmp_path / "s.png")
    r = measure_image(img, grid=False, rulers=False, detect_landmarks=False,
                      session_id="g", session_root=tmp_path)
    assert r["spatial"]["grid"] is None
    assert r["spatial"]["rulers"] is None


def test_req1_region_grid_segments_the_image(tmp_path):
    img = _png(tmp_path / "s.png")
    r = measure_image(img, region_grid=[2, 2], detect_landmarks=False,
                      session_id="g", session_root=tmp_path)
    ids = [reg["id"] for reg in r["spatial"]["regions"]]
    assert ids == ["R1", "R2", "R3", "R4"]


def test_req1_multiple_zoom_segments_each_expose_coordinates(tmp_path):
    img = _png(tmp_path / "s.png")
    r = measure_image(
        img, detect_landmarks=False,
        zooms=[{"name": "a", "box": [0.0, 0.0, 0.5, 0.5]},
               {"name": "b", "box": [0.5, 0.5, 0.5, 0.5]}],
        session_id="g", session_root=tmp_path)
    assert [c["name"] for c in r["spatial"]["crops"]] == ["a", "b"]
    assert len(r["renders"]) == 3  # overlay + 2 crops


@pytest.mark.parametrize("origin,y_axis", [
    ("top-left", "down"), ("bottom-left", "up"), ("center", "up"),
])
def test_req1_coordinate_system_origin_through_tool(tmp_path, origin, y_axis):
    img = _png(tmp_path / "s.png")
    r = measure_image(img, origin=origin, detect_landmarks=False,
                      session_id="g", session_root=tmp_path)
    cs = r["spatial"]["coordinate_system"]
    assert cs["origin"] == origin and cs["y_axis"] == y_axis


def test_req1_detected_landmarks_found_on_structured_image():
    pytest.importorskip("numpy")
    cs = CoordinateSystem("top-left", 200, 120)
    lms = detected_landmarks(_two_color_png_bytes(), cs)
    assert isinstance(lms, list) and len(lms) >= 1
    assert all(lm.source != "structural" for lm in lms)


# ══════════════════════════════════════════════════════════════
# REQ 2 — Image overlay + landmark offset system
# ══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("opacity", [0.0, 0.5, 1.0, 2.0])
def test_req2_overlay_opacity_is_accepted_and_clamped(tmp_path, opacity):
    base = _png(tmp_path / "b.png", (30, 30, 30), size=(160, 160))
    over = _png(tmp_path / "o.png", (220, 220, 220), size=(80, 80))
    r = overlay_images(base, over, opacity=opacity,
                       landmarks=[{"base": [40, 40], "overlay": [0, 0]},
                                  {"base": [120, 120], "overlay": [80, 80]}],
                       session_id="o", session_root=tmp_path)
    assert r["ok"] is True


def test_req2_normalized_landmark_pairs(tmp_path):
    base = _png(tmp_path / "b.png", (30, 30, 30), size=(200, 200))
    over = _png(tmp_path / "o.png", (220, 220, 220), size=(100, 100))
    r = overlay_images(
        base, over,
        landmarks=[{"base": [0.25, 0.25], "overlay": [0.0, 0.0], "norm": True},
                   {"base": [0.75, 0.75], "overlay": [1.0, 1.0], "norm": True}],
        session_id="o", session_root=tmp_path)
    assert r["ok"] is True
    # base 0.25*200=50, overlay 0 → offset 50
    assert r["spatial"]["landmark_offsets"][0]["offset_px"] == [50.0, 50.0]


def test_req2_rotation_shows_up_as_large_residual_not_silent_fix():
    # overlay rotated 90° about origin — a similarity-without-rotation fit cannot
    # absorb it, so the residual must be large (honest, not silently corrected).
    pairs = [((0, 0), (0, 0)), ((0, 1), (1, 0)), ((-1, 0), (0, 1)), ((-1, 1), (1, 1))]
    t = fit_similarity(pairs)
    offs = landmark_offsets(pairs, t)
    assert rms_residual(offs) > 0.5


def test_req2_overlay_requires_landmarks(tmp_path):
    base = _png(tmp_path / "b.png")
    over = _png(tmp_path / "o.png")
    r = overlay_images(base, over, landmarks=[], session_id="o", session_root=tmp_path)
    assert r["ok"] is False


# ══════════════════════════════════════════════════════════════
# REQ 3 — Coordinate marking in every frame
# ══════════════════════════════════════════════════════════════
def test_req3_mark_points_resolves_all_frames(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 100))
    r = mark_points(
        img,
        points=[{"norm": [0.5, 0.5]}, {"px": [10, 20]}, {"cs": [10, 20]},
                {"landmark": "A1", "dx": 3, "dy": 4}, {"viewport_px": [500, 250]}],
        viewport={"name": "v", "box": [0.5, 0.0, 0.5, 0.5]},  # scale 10 (render 1000x500)
        session_id="m", session_root=tmp_path)
    assert r["ok"] is True
    pts = r["spatial"]["points"]
    assert pts[0]["image_px"] == [100.0, 50.0]        # norm 0.5,0.5
    assert pts[1]["image_px"] == [10.0, 20.0]         # px
    assert pts[2]["image_px"] == [10.0, 20.0]         # cs (top-left → identity)
    assert pts[3]["image_px"] == [3.0, 4.0]           # landmark A1 (0,0) + (3,4)
    # a point given in viewport pixels round-trips back to the same viewport pixels
    assert pts[4]["viewport"]["viewport_px"] == pytest.approx([500.0, 250.0], abs=0.5)
    assert all("viewport" in p for p in pts)          # every point in the viewport frame


def test_req3_pins_are_reusable_in_later_operations(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [40, 40], "id": "a"}], session_id="w", session_root=tmp_path)
    # a later, independent call reuses the pin as an anchor for a new one
    r = workspace("pin", points=[{"landmark": "a", "dx": 10, "dy": 0, "id": "b"}],
                  session_id="w", session_root=tmp_path)
    assert _pin(r, "b")["image_px"] == [50.0, 40.0]


# ══════════════════════════════════════════════════════════════
# REQ 4 — Viewport movement with FIXED AIM (coordinate continuity)
# ══════════════════════════════════════════════════════════════
def test_req4_pin_coordinates_survive_pan_and_zoom(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [100, 50], "id": "aim"}], session_id="w", session_root=tmp_path)
    workspace("viewport", viewport={"box": [0.0, 0.0, 1.0, 1.0]}, session_id="w", session_root=tmp_path)
    before = _pin(workspace("render", session_id="w", session_root=tmp_path), "aim")

    after_pan = _pin(workspace("pan", dx=0.1, dy=0.1, session_id="w", session_root=tmp_path), "aim")
    after_zoom = _pin(workspace("zoom", factor=2.0, session_id="w", session_root=tmp_path), "aim")
    # image coordinates are invariant to viewport motion (fixed aim / continuity)
    assert before["image_px"] == after_pan["image_px"] == after_zoom["image_px"] == [100.0, 50.0]
    # but the *viewport* coordinates change as the view moves
    assert after_pan["viewport"]["viewport_px"] != before["viewport"]["viewport_px"]


def test_req4_pan_and_zoom_need_a_viewport(tmp_path):
    img = _png(tmp_path / "s.png")
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    assert workspace("pan", dx=0.1, session_id="w", session_root=tmp_path)["ok"] is False
    assert workspace("zoom", factor=2, session_id="w", session_root=tmp_path)["ok"] is False


def test_req4_viewport_can_be_cleared(tmp_path):
    img = _png(tmp_path / "s.png")
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("viewport", viewport={"box": [0.1, 0.1, 0.2, 0.2]}, session_id="w", session_root=tmp_path)
    r = workspace("viewport", viewport=None, session_id="w", session_root=tmp_path)
    assert r["spatial"]["viewport"] is None
    assert len(r["renders"]) == 1  # no crop when no viewport


# ══════════════════════════════════════════════════════════════
# REQ 5 — AI mouse: pointer increments in every direction / unit
# ══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("unit,dx,dy,expected", [
    ("norm", 0.01, 0.0, [102.0, 50.0]),
    ("norm", -0.01, 0.0, [98.0, 50.0]),
    ("norm", 0.0, 0.01, [100.0, 51.0]),
    ("norm", 0.0, -0.01, [100.0, 49.0]),
    ("px", 5.0, -5.0, [105.0, 45.0]),
])
def test_req5_nudge_increments(tmp_path, unit, dx, dy, expected):
    img = _png(tmp_path / "s.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [100, 50], "id": "p"}], session_id="w", session_root=tmp_path)
    r = workspace("nudge", select={"ids": ["p"]}, dx=dx, dy=dy, unit=unit,
                  session_id="w", session_root=tmp_path)
    assert _pin(r, "p")["image_px"] == expected


def test_req5_viewport_unit_nudge(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [100, 50], "id": "p"}], session_id="w", session_root=tmp_path)
    workspace("viewport", viewport={"box": [0.25, 0.25, 0.5, 0.5]}, session_id="w", session_root=tmp_path)
    # viewport size = 100x50 px; 0.1 viewport-x = 10px
    r = workspace("nudge", select={"ids": ["p"]}, dx=0.1, dy=0.0, unit="viewport",
                  session_id="w", session_root=tmp_path)
    assert _pin(r, "p")["image_px"] == [110.0, 50.0]


# ══════════════════════════════════════════════════════════════
# REQ 6 — Multi-pass refinement (accumulates across rounds)
# ══════════════════════════════════════════════════════════════
def test_req6_iterative_nudges_accumulate(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [100, 50], "id": "p"}], session_id="w", session_root=tmp_path)
    for _ in range(3):
        workspace("nudge", select={"ids": ["p"]}, dx=2, dy=1, unit="px",
                  session_id="w", session_root=tmp_path)
    r = workspace("render", session_id="w", session_root=tmp_path)
    assert _pin(r, "p")["image_px"] == [106.0, 53.0]   # 3 passes of (+2, +1)


# ══════════════════════════════════════════════════════════════
# REQ 7 — Multi-pinning and multi-adjustment
# ══════════════════════════════════════════════════════════════
def test_req7_adjust_all_vs_group_vs_single(tmp_path):
    img = _png(tmp_path / "s.png", size=(200, 100))
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[
        {"px": [10, 10], "id": "a", "group": "g1"},
        {"px": [20, 20], "id": "b", "group": "g1"},
        {"px": [30, 30], "id": "c", "group": "g2"},
    ], session_id="w", session_root=tmp_path)
    # move only group g1
    r = workspace("nudge", select={"group": "g1"}, dx=100, dy=0, unit="px",
                  session_id="w", session_root=tmp_path)
    assert _pin(r, "a")["image_px"] == [110.0, 10.0]
    assert _pin(r, "b")["image_px"] == [120.0, 20.0]
    assert _pin(r, "c")["image_px"] == [30.0, 30.0]     # g2 untouched
    # move ALL (no selector)
    r = workspace("nudge", dx=0, dy=5, unit="px", session_id="w", session_root=tmp_path)
    assert _pin(r, "c")["image_px"] == [30.0, 35.0]


def test_req7_unpin_subset_keeps_the_rest(tmp_path):
    img = _png(tmp_path / "s.png")
    workspace("open", image=img, session_id="w", session_root=tmp_path)
    workspace("pin", points=[{"px": [1, 1], "id": "a"}, {"px": [2, 2], "id": "b"}],
              session_id="w", session_root=tmp_path)
    r = workspace("unpin", select={"ids": ["a"]}, session_id="w", session_root=tmp_path)
    assert [p["id"] for p in r["spatial"]["pins"]] == ["b"]


# ══════════════════════════════════════════════════════════════
# REQ 8 — Vector construction: EVERY shape kind
# ══════════════════════════════════════════════════════════════
_SHAPE_CASES = [
    ("line", [[10, 10], [90, 60]], {}),
    ("path", [[10, 10], [50, 20], [90, 60]], {}),
    ("trace", [[10, 10], [50, 20], [90, 60]], {}),
    ("polyline", [[10, 10], [50, 20], [90, 60]], {}),
    ("curve", [[10, 10], [50, 20], [90, 60]], {}),
    ("spline", [[10, 10], [50, 20], [90, 60]], {}),
    ("triangle", [[10, 10], [90, 10], [50, 80]], {}),
    ("polygon", [[10, 10], [90, 10], [90, 80], [10, 80]], {}),
    ("closed", [[10, 10], [90, 10], [90, 80], [10, 80]], {}),
    ("rect", [[10, 10], [90, 60]], {}),
    ("ellipse", [[10, 10], [90, 60]], {}),
    ("circle", [[50, 50], [70, 50]], {}),
    ("star", [[50, 50], [80, 50]], {"points_count": 5, "inner_ratio": 0.5}),
]


@pytest.mark.parametrize("kind,points,extra", _SHAPE_CASES, ids=[c[0] for c in _SHAPE_CASES])
def test_req8_every_shape_kind_builds_a_valid_document(tmp_path, kind, points, extra):
    shape = {"kind": kind, "points": points, **extra}
    r = construct_vectors([shape], width=120, height=100, raster_png=False,
                          session_id="c", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["shape_count"] == 1
    assert r["construction"][0]["kind"] == kind


def test_req8_circle_from_center_and_radius(tmp_path):
    r = construct_vectors([{"kind": "circle", "points": [[50, 50]], "r": 20}],
                          width=120, height=100, raster_png=False,
                          session_id="c", session_root=tmp_path)
    assert r["ok"] is True
    assert r["construction"][0]["r"] == 20


def test_req8_custom_style_stroke_width_is_lowered(tmp_path):
    # stroke_width is not a direct field (P3); construction must lower it into stroke_style
    r = construct_vectors(
        [{"kind": "rect", "points": [[0, 0], [50, 50]], "style": {"stroke": "#123456", "stroke_width": 4}}],
        width=80, height=80, raster_png=False, session_id="c", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")


def test_req8_background_is_painted_as_a_full_page_rect(tmp_path):
    # regression: `background` must not go on the CanvasObject (it has no such field);
    # it is lowered to a full-canvas fill rect so a white-on-dark mark is visible.
    r = construct_vectors(
        [{"kind": "closed", "points": [[10, 10], [90, 10], [50, 80]],
          "style": {"stroke": "#f2f2f0", "stroke_width": 6}}],
        width=200, height=120, background="#2e3238", raster_png=False,
        session_id="bg", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["shape_count"] == 1


def test_req8_multiple_shapes_in_one_document(tmp_path):
    r = construct_vectors(
        [{"kind": "rect", "points": [[0, 0], [40, 40]]},
         {"kind": "line", "points": [[0, 0], [80, 80]]},
         {"kind": "star", "points": [[60, 60], [75, 60]]}],
        width=100, height=100, raster_png=False, session_id="c", session_root=tmp_path)
    assert r["ok"] is True and r["shape_count"] == 3


# ══════════════════════════════════════════════════════════════
# REQ 9 — 2D / 3D mapping
# ══════════════════════════════════════════════════════════════
def test_req9_homography_recovers_a_projective_transform():
    H = [[1.0, 0.1, 0.0], [0.0, 1.0, 0.0], [0.001, 0.0005, 1.0]]  # has perspective terms
    corners = [[0, 0], [100, 0], [100, 100], [0, 100]]
    pairs = [{"src": c, "dst": list(apply_homography(H, c[0], c[1]))} for c in corners]
    truth = apply_homography(H, 50, 50)
    r = map_coordinates("homography", pairs=pairs, points=[[50, 50]])
    assert r["ok"] is True
    mx, my = r["spatial"]["mapped_points"][0]
    assert abs(mx - truth[0]) < 1e-2 and abs(my - truth[1]) < 1e-2
    assert r["spatial"]["rms_residual_px"] < 1e-3


def test_req9_homography_needs_four_pairs():
    r = map_coordinates("homography",
                        pairs=[{"src": [0, 0], "dst": [0, 0]}, {"src": [1, 0], "dst": [1, 0]},
                               {"src": [1, 1], "dst": [1, 1]}],
                        points=[[0.5, 0.5]])
    assert r["ok"] is False and "4 pairs" in r["error"]


def test_req9_project_pixels_only_with_dimensions():
    with_dims = map_coordinates("project", points=[[0, 0, 0]], camera={"eye": [0, 0, 5]},
                                width=200, height=100)
    without = map_coordinates("project", points=[[0, 0, 0]], camera={"eye": [0, 0, 5]})
    assert "points_px" in with_dims["spatial"]
    assert "points_px" not in without["spatial"]


def test_req9_to_3d_preserves_point_count():
    r = map_coordinates("to_3d", points=[[1, 2], [3, 4], [5, 6]])
    assert len(r["spatial"]["points_3d"]) == 3
    assert r["spatial"]["points_3d"][0] == [1.0, 2.0, 0.0]


# ══════════════════════════════════════════════════════════════
# Geometry-constrained refinement (P1–P4): constraint actions + score.geometry
# ══════════════════════════════════════════════════════════════
_EDGE_X, _EDGE_Y = 80.4, 120.6


def _corner_png(path, size=(200, 200)):
    """Bright quadrant x>_EDGE_X ∧ y<_EDGE_Y — one vertical + one horizontal sub-pixel edge."""
    import numpy as np

    xs = np.arange(size[0])[None, :]
    ys = np.arange(size[1])[:, None]
    sx = 1.0 / (1.0 + np.exp(-(xs - _EDGE_X) / 0.8))
    sy = 1.0 / (1.0 + np.exp((ys - _EDGE_Y) / 0.8))
    img = (255.0 * sx * sy).astype("uint8")
    Image.fromarray(img, "L").convert("RGB").save(path, format="PNG")
    return str(path)


def test_geom_collinear_projects_pins_onto_one_line(tmp_path):
    img = _png(tmp_path / "s.png", size=(120, 160))
    workspace("open", image=img, session_id="gc", session_root=tmp_path)
    workspace("pin", points=[{"px": [10, 10], "id": "a"}, {"px": [20, 60], "id": "b"},
                             {"px": [30, 100], "id": "c"}], session_id="gc", session_root=tmp_path)
    res = workspace("collinear", select={"ids": ["a", "b", "c"]},
                    session_id="gc", session_root=tmp_path)
    assert res["action_info"]["collinear"]["residual_before"]["max_dist_px"] > 0.3
    (ax, ay) = _pin(res, "a")["image_px"]
    (bx, by) = _pin(res, "b")["image_px"]
    (cx, cy) = _pin(res, "c")["image_px"]
    # perpendicular distance of the middle pin from the a–c line (was ~1.08px pre-projection)
    base = ((cx - ax) ** 2 + (cy - ay) ** 2) ** 0.5
    perp = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / base
    assert perp < 0.05


def test_geom_symmetrize_enforces_axis_and_flags_outlier(tmp_path):
    img = _png(tmp_path / "s.png", size=(400, 300))
    workspace("open", image=img, session_id="gs", session_root=tmp_path)
    workspace("pin", points=[
        {"px": [100, 250], "id": "l1"}, {"px": [300, 250], "id": "r1"},
        {"px": [110, 180], "id": "l2"}, {"px": [290, 180], "id": "r2"},
        {"px": [130, 100], "id": "l3"}, {"px": [290, 100], "id": "r3"},  # mid 210 — the outlier
    ], session_id="gs", session_root=tmp_path)
    res = workspace("symmetrize", geometry={"pairs": [["l1", "r1"], ["l2", "r2"], ["l3", "r3"]]},
                    session_id="gs", session_root=tmp_path)
    info = res["action_info"]["symmetrize"]
    assert info["axis_x"] == pytest.approx(200.0, abs=1.0)
    assert info["report"]["n_outliers"] == 1
    mid3 = (_pin(res, "l3")["image_px"][0] + _pin(res, "r3")["image_px"][0]) / 2.0
    assert mid3 == pytest.approx(200.0, abs=0.5)   # outlier pair now symmetric


def test_geom_fit_edge_snaps_pins_to_subpixel_edge(tmp_path):
    pytest.importorskip("numpy")
    img = _corner_png(tmp_path / "corner.png")
    workspace("open", image=img, session_id="gf", session_root=tmp_path)
    workspace("pin", points=[{"px": [78, 40], "id": "e1"}, {"px": [82, 95], "id": "e2"}],
              session_id="gf", session_root=tmp_path)
    res = workspace("fit_edge", select={"ids": ["e1", "e2"]},
                    geometry={"band": 8, "step": 4}, session_id="gf", session_root=tmp_path)
    assert res["action_info"]["fit_edge"]["source"] == "subpixel-edge"
    assert _pin(res, "e1")["image_px"][0] == pytest.approx(_EDGE_X, abs=0.6)
    assert _pin(res, "e2")["image_px"][0] == pytest.approx(_EDGE_X, abs=0.6)


def test_geom_intersect_sets_corner_pin(tmp_path):
    pytest.importorskip("numpy")
    img = _corner_png(tmp_path / "corner.png")
    workspace("open", image=img, session_id="gi", session_root=tmp_path)
    workspace("pin", points=[
        {"px": [80, 40], "id": "v1"}, {"px": [80, 90], "id": "v2"},      # vertical edge
        {"px": [100, 120], "id": "h1"}, {"px": [160, 120], "id": "h2"},  # horizontal edge
    ], session_id="gi", session_root=tmp_path)
    res = workspace("intersect", geometry={"edge1": ["v1", "v2"], "edge2": ["h1", "h2"],
                                           "target": "corner", "band": 8, "step": 4},
                    session_id="gi", session_root=tmp_path)
    assert res["action_info"]["intersect"]["target"] == "corner"
    cx, cy = _pin(res, "corner")["image_px"]
    assert cx == pytest.approx(_EDGE_X, abs=0.8)
    assert cy == pytest.approx(_EDGE_Y, abs=0.8)


def test_geom_snap_subpixel_slides_pin_onto_edge(tmp_path):
    pytest.importorskip("numpy")
    img = _corner_png(tmp_path / "corner.png")
    workspace("open", image=img, session_id="gsub", session_root=tmp_path)
    workspace("pin", points=[{"px": [75, 70], "id": "p"}], session_id="gsub", session_root=tmp_path)
    res = workspace("snap", snap_to="edge_subpixel", select={"ids": ["p"]},
                    geometry={"band": 10}, session_id="gsub", session_root=tmp_path)
    assert res["action_info"]["snapped"][0]["ok"] is True
    assert _pin(res, "p")["image_px"][0] == pytest.approx(_EDGE_X, abs=0.6)


def test_score_reconstruction_geometry_flags_shifted_pair(tmp_path):
    p = _edge_png(tmp_path / "edge.png")
    res = score_reconstruction(
        p, [{"kind": "line", "points": [[20, 90], [220, 90]]}],
        symmetry_pairs=[[[100, 90], [140, 90]], [[105, 70], [135, 70]], [[100, 50], [160, 50]]],
        collinear_groups=[[[10, 10], [20, 30], [30, 60]]],
        session_id="sg", session_root=tmp_path)
    geom = res["score"]["geometry"]
    assert geom["symmetry"]["n_outliers"] == 1
    assert geom["worst_dev_px"] >= 8.0
    assert geom["within_tol"] is False


def test_score_reconstruction_without_pairs_has_no_geometry_key(tmp_path):
    p = _edge_png(tmp_path / "edge.png")
    res = score_reconstruction(p, [{"kind": "line", "points": [[20, 90], [220, 90]]}],
                               session_id="sng", session_root=tmp_path)
    assert "geometry" not in res["score"]
