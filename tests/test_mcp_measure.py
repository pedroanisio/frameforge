#!/usr/bin/env python3
"""The measurement layer must turn a raster into a reliable coordinate reference.

These tests pin the exact geometry (coordinate systems, region metrics, structural
landmarks, the zoom-aware crop transform, multi-frame point resolution, and
landmark-driven overlay alignment) and the three MCP tools' end-to-end result shape
(image content blocks + a `spatial` payload surfaced in the model-facing summary).
"""
from __future__ import annotations

import json
import math
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
    mark_points,
    mcp_content_blocks,
    measure_image,
    overlay_images,
)
from framegraph.vision.infrastructure.image_compare import Region  # noqa: E402
from framegraph.vision.infrastructure.measure import (  # noqa: E402
    CoordinateSystem,
    build_marks,
    build_measurement,
    crop_transform,
    measured_regions,
    nice_step,
    point_frames,
    resolve_point_spec,
    structural_landmarks,
)
from framegraph.vision.infrastructure.overlay_align import (  # noqa: E402
    build_overlay,
    fit_similarity,
)


def _png(path, color, size=(240, 180)):
    Image.new("RGB", size, color).save(path, format="PNG")
    return str(path)


# ─────────────────────────────────────────────────────────────
# coordinate system
# ─────────────────────────────────────────────────────────────
def test_coordinate_system_top_left_is_identity():
    cs = CoordinateSystem("top-left", 200, 100)
    assert cs.to_cs(30, 40) == (30, 40)
    assert cs.from_cs(30, 40) == (30, 40)


def test_coordinate_system_bottom_left_flips_y():
    cs = CoordinateSystem("bottom-left", 200, 100)
    assert cs.to_cs(30, 40) == (30, 60)      # y up: 100 - 40
    assert cs.from_cs(30, 60) == (30, 40)     # round trip


def test_coordinate_system_center_origin():
    cs = CoordinateSystem("center", 200, 100)
    assert cs.to_cs(100, 50) == (0, 0)        # centre → origin
    assert cs.to_cs(200, 0) == (100, 50)      # top-right → (+x, +y)
    assert cs.from_cs(*cs.to_cs(37, 12)) == (37, 12)


def test_nice_step_is_round_and_scales():
    assert nice_step(1200) in (100, 200, 250)  # ~1/12 of the extent, rounded up
    assert nice_step(10) >= 5


# ─────────────────────────────────────────────────────────────
# regions + landmarks
# ─────────────────────────────────────────────────────────────
def test_measured_region_geometry_is_exact():
    cs = CoordinateSystem("top-left", 200, 100)
    (r,) = measured_regions([Region("mid", (0.25, 0.25, 0.5, 0.5))], cs)
    assert r.id == "R1"
    assert r.bbox_px == (50.0, 25.0, 100.0, 50.0)
    assert r.offset_px == (50.0, 25.0)
    assert r.centroid_px == (100.0, 50.0)
    assert r.area_px == 5000.0


def test_structural_landmarks_are_nine_exact_anchors():
    cs = CoordinateSystem("top-left", 200, 100)
    lms = structural_landmarks(cs)
    assert len(lms) == 9
    by_kind = {lm.kind: (lm.x_px, lm.y_px) for lm in lms}
    assert by_kind["center"] == (100.0, 50.0)
    assert by_kind["corner-tl"] == (0.0, 0.0)
    assert by_kind["corner-br"] == (200.0, 100.0)
    assert all(lm.source == "structural" and lm.confidence == 1.0 for lm in lms)


# ─────────────────────────────────────────────────────────────
# zoom-aware crop transform
# ─────────────────────────────────────────────────────────────
def test_crop_transform_offset_scale_and_inverse():
    cs = CoordinateSystem("top-left", 200, 100)
    xf = crop_transform("q", (0.5, 0.0, 0.5, 0.5), cs, render_long_edge=1000)
    assert xf.origin_px == (100.0, 0.0)
    assert xf.size_px == (100.0, 50.0)
    assert xf.scale == 10.0                      # 1000 / max(100, 50)
    assert xf.render_px == (1000, 500)
    # a source point maps to render px and back exactly (zoom-aware)
    rx, ry = (150 - 100) * xf.scale, (25 - 0) * xf.scale
    assert xf.to_source_px(rx, ry) == (150.0, 25.0)


# ─────────────────────────────────────────────────────────────
# build_measurement
# ─────────────────────────────────────────────────────────────
def _png_bytes(color, size=(240, 180)) -> bytes:
    from io import BytesIO

    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_build_measurement_overlay_keeps_source_size_and_reports_spatial():
    data = _png_bytes((120, 140, 160), size=(240, 180))
    m = build_measurement(
        data,
        regions=[Region("head", (0.1, 0.1, 0.3, 0.3))],
        zooms=[Region("z", (0.0, 0.0, 0.5, 0.5))],
        detect_landmarks=False,
    )
    # coordinate identity: the overlay is exactly the source's pixel size
    assert m.overlay.size == (240, 180)
    assert m.spatial["image"] == {"width_px": 240, "height_px": 180}
    assert m.spatial["regions"][0]["id"] == "R1"
    assert len(m.spatial["landmarks"]) == 9          # structural only
    assert m.spatial["crops"][0]["scale"] >= 1.0
    assert len(m.crops) == 1                          # one zoom crop image


# ─────────────────────────────────────────────────────────────
# point marking — every frame
# ─────────────────────────────────────────────────────────────
def test_resolve_point_spec_across_frames():
    cs = CoordinateSystem("top-left", 200, 100)
    lms = {lm.id: lm for lm in structural_landmarks(cs)}
    assert resolve_point_spec({"px": [10, 20]}, cs, lms, None) == (10.0, 20.0)
    assert resolve_point_spec({"norm": [0.5, 0.5]}, cs, lms, None) == (100.0, 50.0)
    assert resolve_point_spec({"landmark": "A9"}, cs, lms, None) == (100.0, 50.0)
    assert resolve_point_spec({"landmark": "A1", "dx": 5, "dy": 7}, cs, lms, None) == (5.0, 7.0)


def test_resolve_point_spec_viewport_pixels():
    cs = CoordinateSystem("top-left", 200, 100)
    xf = crop_transform("v", (0.5, 0.0, 0.5, 0.5), cs, render_long_edge=1000)  # scale 10
    # viewport px (500, 250) → source (100 + 50, 0 + 25) = (150, 25)
    assert resolve_point_spec({"viewport_px": [500, 250]}, cs, {}, xf) == (150.0, 25.0)


def test_point_frames_reports_image_and_viewport():
    cs = CoordinateSystem("top-left", 200, 100)
    xf = crop_transform("v", (0.5, 0.0, 0.5, 0.5), cs, render_long_edge=1000)
    frames = point_frames(150, 25, cs, xf)
    assert frames["image_px"] == [150.0, 25.0]
    assert frames["normalized"] == [0.75, 0.25]
    assert frames["viewport"]["viewport_px"] == [500.0, 250.0]
    assert frames["viewport"]["inside"] is True


def test_build_marks_resolves_and_draws():
    data = _png_bytes((200, 200, 200), size=(200, 100))
    m = build_marks(
        data,
        [{"norm": [0.5, 0.5], "label": "nose"}, {"landmark": "A1"}],
        viewport_box=Region("v", (0.4, 0.4, 0.2, 0.2)),
        connect=True,
    )
    assert m.overlay.size == (200, 100)
    assert [p["label"] for p in m.spatial["points"]] == ["nose", "P2"]
    assert m.spatial["points"][0]["image_px"] == [100.0, 50.0]
    assert m.spatial["viewport"]["name"] == "v"
    assert len(m.crops) == 1                          # the zoomed viewport render


# ─────────────────────────────────────────────────────────────
# overlay alignment
# ─────────────────────────────────────────────────────────────
def test_fit_similarity_single_pair_is_translation():
    t = fit_similarity([((10, 20), (0, 0))])
    assert t.scale == 1.0
    assert (round(t.tx), round(t.ty)) == (10, 20)


def test_fit_similarity_recovers_scale_and_translation():
    # base = 2 * overlay + (5, 5)
    pairs = [((5, 5), (0, 0)), ((25, 25), (10, 10)), ((5, 25), (0, 10))]
    t = fit_similarity(pairs)
    assert round(t.scale, 6) == 2.0
    assert (round(t.tx, 6), round(t.ty, 6)) == (5.0, 5.0)
    for (b, o) in pairs:
        mx, my = t.apply(*o)
        assert math.hypot(mx - b[0], my - b[1]) < 1e-6


def test_build_overlay_reports_offsets_and_alignment():
    base = _png_bytes((30, 30, 30), size=(200, 200))
    over = _png_bytes((220, 220, 220), size=(100, 100))
    comp, spatial = build_overlay(
        base, over,
        landmarks=[{"base": [50, 50], "overlay": [0, 0]},
                   {"base": [150, 150], "overlay": [100, 100]}],
    )
    assert comp.size == (200, 200)
    assert round(spatial["alignment"]["scale"], 6) == 1.0
    assert spatial["landmark_offsets"][0]["offset_px"] == [50.0, 50.0]
    assert spatial["rms_residual_px"] == 0.0


# ─────────────────────────────────────────────────────────────
# MCP tools — end to end
# ─────────────────────────────────────────────────────────────
def test_measure_image_end_to_end(tmp_path):
    img = _png(tmp_path / "src.png", (120, 130, 140), size=(240, 180))
    result = measure_image(
        img,
        regions=[{"name": "logo", "box": [0.1, 0.1, 0.3, 0.2]}],
        zooms=[{"name": "corner", "box": [0.0, 0.0, 0.25, 0.25]}],
        detect_landmarks=False,
        session_id="meas", session_root=tmp_path,
    )
    assert result["ok"] is True
    assert len(result["renders"]) == 2               # overlay + one zoom crop
    for render in result["renders"]:
        assert render["mimeType"] == "image/png"
        assert os.path.isfile(render["path"])
    # overlay keeps source pixel size (coordinate identity)
    assert Image.open(result["renders"][0]["path"]).size == (240, 180)
    # spatial surfaced in the model-facing summary
    summary = json.loads(mcp_content_blocks(result)[0]["text"])
    assert summary["spatial"]["regions"][0]["id"] == "R1"
    assert summary["spatial"]["crops"][0]["name"] == "corner"
    image_blocks = [b for b in mcp_content_blocks(result) if b["type"] == "image"]
    assert len(image_blocks) == 2


def test_mark_points_end_to_end(tmp_path):
    img = _png(tmp_path / "src.png", (200, 200, 200), size=(200, 100))
    result = mark_points(
        img,
        points=[{"norm": [0.5, 0.5]}, {"landmark": "A2"}],
        viewport={"name": "eye", "box": [0.4, 0.4, 0.3, 0.3]},
        connect=True, session_id="marks", session_root=tmp_path,
    )
    assert result["ok"] is True
    assert len(result["renders"]) == 2               # marks overlay + viewport crop
    pts = result["spatial"]["points"]
    assert pts[0]["image_px"] == [100.0, 50.0]
    assert "viewport" in pts[0]
    summary = json.loads(mcp_content_blocks(result)[0]["text"])
    assert "spatial" in summary


def test_mark_points_bad_spec_is_structured_error(tmp_path):
    img = _png(tmp_path / "src.png", (0, 0, 0))
    result = mark_points(img, points=[{"nonsense": [1, 2]}],
                         session_id="bad", session_root=tmp_path)
    assert result["ok"] is False
    assert "point needs one of" in result["error"]
    assert result["renders"] == []


def test_overlay_images_end_to_end(tmp_path):
    base = _png(tmp_path / "base.png", (30, 30, 30), size=(200, 200))
    over = _png(tmp_path / "over.png", (220, 220, 220), size=(100, 100))
    result = overlay_images(
        base, over,
        landmarks=[{"base": [50, 50], "overlay": [0, 0]},
                   {"base": [150, 150], "overlay": [100, 100]}],
        session_id="ovl", session_root=tmp_path,
    )
    assert result["ok"] is True
    assert len(result["renders"]) == 1
    assert result["spatial"]["landmark_offsets"][0]["offset_px"] == [50.0, 50.0]
    summary = json.loads(mcp_content_blocks(result)[0]["text"])
    assert summary["spatial"]["alignment"]["scale"] == 1.0


def test_measure_image_missing_file_is_structured_error(tmp_path):
    result = measure_image(str(tmp_path / "nope.png"),
                           session_id="missing", session_root=tmp_path)
    assert result["ok"] is False
    assert "error" in result and result["renders"] == []


def test_measure_image_respects_input_root_confinement(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = _png(tmp_path / "outside.png", (0, 0, 0))
    monkeypatch.setenv("FRAMEGRAPH_MCP_INPUT_ROOTS", str(allowed))
    result = measure_image(outside, session_id="confine", session_root=tmp_path)
    assert result["ok"] is False
    assert "FRAMEGRAPH_MCP_INPUT_ROOTS" in result["error"]
