#!/usr/bin/env python3
"""The vectorize_image tool: raster → editable FrameGraph objects, then render.

Covers the object-translation helper, the potrace `trace` backend (skipped when the
binary is absent), the OpenCV `region` backend (skipped without cv2), and the tool's
end-to-end result shape + structured errors.
"""
from __future__ import annotations

import os
import shutil
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

pytest.importorskip("PIL")

from PIL import Image, ImageDraw  # noqa: E402

from framegraph.mcp.server import vectorize_image  # noqa: E402
from framegraph.mcp.usecases import _translate_objects  # noqa: E402

_HAS_POTRACE = shutil.which("potrace") is not None
try:
    import cv2  # noqa: F401
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False


def _mark_png(path, size=(120, 120), dark_bg=True):
    """A crisp bi-level mark: a light diamond outline on dark (or inverse)."""
    bg, fg = ((30, 33, 38), (240, 240, 236)) if dark_bg else ((240, 240, 236), (20, 20, 20))
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    cx, cy = size[0] // 2, size[1] // 2
    d.polygon([(cx, 20), (size[0] - 20, cy), (cx, size[1] - 20), (20, cy)], outline=fg, width=6)
    im.save(path, format="PNG")
    return str(path)


# ─────────────────────────────────────────────────────────────
# helper
# ─────────────────────────────────────────────────────────────
def test_translate_objects_shifts_all_geometry():
    objs = [
        {"type": "polygon", "points": [[1, 2], [3, 4]]},
        {"type": "text", "box": [10, 20, 5, 5]},
        {"type": "ellipse", "center": [7, 8], "rx": 2, "ry": 2},
    ]
    _translate_objects(objs, 100, 200)
    assert objs[0]["points"] == [[101.0, 202.0], [103.0, 204.0]]
    assert objs[1]["box"] == [110.0, 220.0, 5, 5]
    assert objs[2]["center"] == [107.0, 208.0]


def test_translate_objects_noop_on_zero():
    objs = [{"type": "polygon", "points": [[1, 2]]}]
    _translate_objects(objs, 0, 0)
    assert objs[0]["points"] == [[1, 2]]


# ─────────────────────────────────────────────────────────────
# potrace trace backend
# ─────────────────────────────────────────────────────────────
@pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")
def test_trace_to_svg_produces_paths(tmp_path):
    from framegraph.vision.infrastructure.vectorize import trace_to_svg

    src = _mark_png(tmp_path / "mark.png")
    svg, meta = trace_to_svg(src, fill="#f2f2f0")
    assert "<path" in svg
    assert meta["backend"] == "potrace" and meta["path_count"] >= 1
    assert meta["inverted"] is True   # light mark on dark ground → auto-invert


@pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")
def test_vectorize_trace_mode_end_to_end(tmp_path):
    src = _mark_png(tmp_path / "mark.png")
    r = vectorize_image(src, mode="trace", fill="#f2f2f0", background="#1e2126",
                        raster_png=False, session_id="vt", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["vectorize"]["backend"] == "potrace"
    assert r["vectorize"]["object_count"] >= 1
    assert r["renders"]


@pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")
def test_vectorize_trace_region_box_places_in_full_image(tmp_path):
    # a mark in the top-left quadrant, traced via a region crop, must land there
    im = Image.new("RGB", (240, 200), (30, 33, 38))
    ImageDraw.Draw(im).polygon([(60, 20), (100, 60), (60, 100), (20, 60)],
                               outline=(240, 240, 236), width=6)
    src = str(tmp_path / "q.png")
    im.save(src)
    r = vectorize_image(src, mode="trace", region_box=[0.0, 0.0, 0.5, 0.6], fill="#eee",
                        raster_png=False, session_id="vr", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["vectorize"]["page_px"] == [240, 200]        # full image size
    assert r["vectorize"]["region_px"] == [0.0, 0.0]      # crop origin reported


# ─────────────────────────────────────────────────────────────
# opencv region backend
# ─────────────────────────────────────────────────────────────
@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_vectorize_region_mode_end_to_end(tmp_path):
    src = _mark_png(tmp_path / "mark.png", dark_bg=False)
    r = vectorize_image(src, mode="region", colors=3, min_area=20, raster_png=False,
                        session_id="vg", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["vectorize"]["backend"] == "opencv:region"
    assert r["vectorize"]["object_count"] >= 1


# ─────────────────────────────────────────────────────────────
# errors
# ─────────────────────────────────────────────────────────────
def test_vectorize_unknown_mode_is_structured_error(tmp_path):
    src = _mark_png(tmp_path / "mark.png")
    r = vectorize_image(src, mode="quantum", session_id="ve", session_root=tmp_path)
    assert r["ok"] is False and "unknown mode" in r["error"]


def test_vectorize_missing_file_is_structured_error(tmp_path):
    r = vectorize_image(str(tmp_path / "nope.png"), session_id="vm", session_root=tmp_path)
    assert r["ok"] is False and r["renders"] == []
