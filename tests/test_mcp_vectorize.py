#!/usr/bin/env python3
"""The vectorize lane: raster → editable FrameGraph objects, then render.

Covers the object-translation helper, the potrace `trace` backend (skipped when the
binary is absent), the OpenCV `region` backend (skipped without cv2), and the tool's
end-to-end result shape + structured errors — plus the rest of the lane's
infrastructure surface: the auto-mode classifier/router, structured OCR status,
the construct text/arc shape kinds, matchscore's pin-id geometry resolution and
arc sampling, and the svg_import round-trip features (<use>, CSS <style>, <text>,
gradientTransform, clipPath).
"""
from __future__ import annotations

import math
import os
import shutil
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

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


def test_shift_path_d_absolute_and_bails_on_curves():
    from framegraph.mcp.usecases import _shift_path_d
    assert _shift_path_d("M 1 2 L 3 4 Z", 10, 20) == "M 11.00 22.00 L 13.00 24.00 Z"
    # unknown command (C) → returned unchanged rather than corrupted
    assert _shift_path_d("M 0 0 C 1 1 2 2 3 3", 5, 5) == "M 0 0 C 1 1 2 2 3 3"


def test_translate_objects_shifts_path_d():
    objs = [{"type": "path", "d": "M 1 1 L 2 2 Z"}]
    _translate_objects(objs, 100, 200)
    assert objs[0]["d"] == "M 101.00 201.00 L 102.00 202.00 Z"


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
def _ring_png(path, size=(120, 120)):
    """A white ring (filled disc with a hole) on a solid dark ground."""
    im = Image.new("RGB", size, (20, 20, 24))
    d = ImageDraw.Draw(im)
    d.ellipse([30, 30, 90, 90], fill=(240, 240, 240))
    d.ellipse([52, 52, 68, 68], fill=(20, 20, 24))     # the hole
    im.save(path, format="PNG")
    return str(path)


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_raster_to_layers_emits_evenodd_paths(tmp_path):
    from framegraph.vision.infrastructure.vectorize import raster_to_layers

    objs, w, h = raster_to_layers(_ring_png(tmp_path / "ring.png"), max_colors=2)
    assert (w, h) == (120, 120)
    assert objs and objs[0]["type"] == "path" and "d" in objs[0]
    assert objs[0]["style"]["fill_rule"] == "evenodd"   # holes via even-odd


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_vectorize_layers_mode_end_to_end(tmp_path):
    src = _ring_png(tmp_path / "ring.png")
    r = vectorize_image(src, mode="layers", colors=2, raster_png=False,
                        session_id="vlay", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["vectorize"]["backend"] == "opencv:layers"
    assert r["vectorize"]["object_count"] >= 1


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_vectorize_layers_region_box_places_in_full_image(tmp_path):
    # ring in the top-left quadrant of a larger image, traced via a region crop
    im = Image.new("RGB", (240, 200), (20, 20, 24))
    d = ImageDraw.Draw(im)
    d.ellipse([30, 30, 90, 90], fill=(240, 240, 240))
    d.ellipse([52, 52, 68, 68], fill=(20, 20, 24))
    src = str(tmp_path / "q.png")
    im.save(src)
    r = vectorize_image(src, mode="layers", colors=2, region_box=[0.0, 0.0, 0.5, 0.6],
                        raster_png=False, session_id="vlr", session_root=tmp_path)
    assert r["ok"] is True, r.get("error")
    assert r["vectorize"]["page_px"] == [240, 200]
    assert r["vectorize"]["object_count"] >= 1


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


# ─────────────────────────────────────────────────────────────
# auto-mode classifier / router
# ─────────────────────────────────────────────────────────────
def _flat_on_solid_png(path, size=(160, 120)):
    """Flat colour shapes on a solid dark ground (the `layers` habitat)."""
    im = Image.new("RGB", size, (28, 30, 36))
    d = ImageDraw.Draw(im)
    d.rectangle([20, 20, 60, 60], fill=(210, 60, 50))
    d.ellipse([90, 40, 140, 90], fill=(60, 110, 200))
    im.save(path, format="PNG")
    return str(path)


def _gradient_png(path, size=(160, 120)):
    """A colour gradient — no solid ground, thousands of colours."""
    im = Image.new("RGB", size)
    px = im.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = (x * 255 // size[0], y * 255 // size[1], (x + y) % 255)
    im.save(path, format="PNG")
    return str(path)


def _heavy_ink_png(path, size=(120, 120)):
    """A big solid black disc on white — bilevel, heavy ink (potrace's habitat)."""
    im = Image.new("RGB", size, (255, 255, 255))
    ImageDraw.Draw(im).ellipse([20, 20, 100, 100], fill=(0, 0, 0))
    im.save(path, format="PNG")
    return str(path)


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_classify_raster_reports_metrics_and_kind(tmp_path):
    from framegraph.vision.infrastructure.vectorize import classify_raster

    info = classify_raster(_mark_png(tmp_path / "line.png", dark_bg=False))
    assert info["kind"] == "lineart"
    for key in ("white_frac", "dark_frac", "mid_frac", "n_colors", "solid_bg"):
        assert key in info


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_auto_mode_routes_lineart_to_outline(tmp_path):
    from framegraph.vision.infrastructure.vectorize import resolve_auto_mode

    mode, meta = resolve_auto_mode(_mark_png(tmp_path / "line.png", dark_bg=False))
    assert mode == "outline"
    assert meta["resolved_mode"] == "outline"
    assert meta["classification"]["kind"] == "lineart"
    assert meta["presets"]["min_area"] == 22.0


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_auto_mode_routes_flat_solid_bg_to_layers(tmp_path):
    from framegraph.vision.infrastructure.vectorize import resolve_auto_mode

    mode, meta = resolve_auto_mode(_flat_on_solid_png(tmp_path / "flat.png"))
    assert mode == "layers"
    assert meta["classification"]["solid_bg"] is True


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_auto_mode_routes_gradient_to_region(tmp_path):
    from framegraph.vision.infrastructure.vectorize import resolve_auto_mode

    mode, _ = resolve_auto_mode(_gradient_png(tmp_path / "grad.png"))
    assert mode == "region"


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_auto_mode_routes_heavy_bilevel_ink_by_potrace_presence(tmp_path):
    from framegraph.vision.infrastructure.vectorize import resolve_auto_mode

    mode, meta = resolve_auto_mode(_heavy_ink_png(tmp_path / "ink.png"))
    assert mode == ("trace" if _HAS_POTRACE else "layers")
    assert meta["classification"]["kind"] == "illustration"


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_raster_to_objects_accepts_auto_mode(tmp_path):
    from framegraph.vision.infrastructure.vectorize import raster_to_objects

    objs, w, h = raster_to_objects(_mark_png(tmp_path / "line.png", dark_bg=False),
                                   mode="auto", min_area=10)
    assert objs and objs[0]["type"] == "polyline"           # lineart → outline route


# ─────────────────────────────────────────────────────────────
# crop maths route through the coordinate authority
# ─────────────────────────────────────────────────────────────
@pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")
def test_trace_region_px_agrees_with_domain_denorm_box(tmp_path):
    from framegraph.vision.domain.coordinates import denorm_box
    from framegraph.vision.infrastructure.vectorize import trace_to_svg

    src = _mark_png(tmp_path / "mark.png", size=(240, 200))
    box = [0.1, 0.2, 0.5, 0.9]                              # overruns the bottom → clamped
    _, meta = trace_to_svg(src, region_box=box, fill="#eee")
    ox, oy, cw, ch = denorm_box(box[0], box[1], box[2], box[3], 240, 200)
    assert meta["region_px"] == [round(ox, 2), round(oy, 2),
                                 round(max(1.0, cw), 2), round(max(1.0, ch), 2)]


def test_vectorize_has_no_private_clamp():
    """The norm→px clamp lives in domain.coordinates, not re-derived here."""
    from framegraph.vision.infrastructure import vectorize

    assert not hasattr(vectorize, "_clamp01")


# ─────────────────────────────────────────────────────────────
# OCR: structured status (no more silent [])
# ─────────────────────────────────────────────────────────────
def _fake_pytesseract(data):
    import types

    mod = types.ModuleType("pytesseract")

    class Output:
        DICT = "dict"

    mod.Output = Output
    mod.image_to_data = lambda img, output_type=None: data
    mod.get_tesseract_version = lambda: "9.9-fake"
    return mod


def test_ocr_status_reflects_this_environment(tmp_path):
    from framegraph.vision.infrastructure.vectorize import ocr_text_objects_status

    objs, status = ocr_text_objects_status(_mark_png(tmp_path / "m.png"))
    assert status["status"] in ("ok", "no_text", "unavailable", "error")
    assert status["n_words"] == len(objs)
    if not status["available"]:
        assert status["status"] == "unavailable" and status["reason"] and objs == []


@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV not installed")
def test_ocr_status_distinguishes_no_text_from_missing_backend(monkeypatch, tmp_path):
    from framegraph.vision.infrastructure.vectorize import ocr_text_objects_status

    src = _mark_png(tmp_path / "m.png")
    monkeypatch.setitem(sys.modules, "pytesseract",
                        _fake_pytesseract({"text": [], "conf": []}))
    objs, status = ocr_text_objects_status(src)
    assert (objs, status["status"], status["available"]) == ([], "no_text", True)

    monkeypatch.setitem(sys.modules, "pytesseract", _fake_pytesseract(
        {"text": ["Hi"], "conf": ["96"], "left": [4], "top": [5],
         "width": [30], "height": [12]}))
    objs, status = ocr_text_objects_status(src)
    assert status["status"] == "ok" and status["n_words"] == 1
    assert objs[0]["type"] == "text" and objs[0]["text"] == "Hi"


def test_ocr_status_reports_missing_dependency(monkeypatch, tmp_path):
    from framegraph.vision.infrastructure.vectorize import ocr_text_objects_status

    monkeypatch.setitem(sys.modules, "pytesseract", None)   # import → ImportError
    objs, status = ocr_text_objects_status(_mark_png(tmp_path / "m.png"))
    assert objs == [] and status["available"] is False
    assert status["status"] == "unavailable" and "pytesseract" in status["reason"]


def test_text_detector_availability_names_the_missing_piece(monkeypatch):
    from framegraph.vision.infrastructure.ocr_detector import TextDetector

    det = TextDetector()
    monkeypatch.setitem(sys.modules, "pytesseract", None)
    ok, reason = det.availability()
    assert ok is False and "pytesseract" in reason
    assert det.available() is False and det.unavailable_reason() == reason

    broken = _fake_pytesseract({})

    def _boom():
        raise OSError("tesseract not on PATH")

    broken.get_tesseract_version = _boom
    monkeypatch.setitem(sys.modules, "pytesseract", broken)
    ok, reason = det.availability()
    assert ok is False and "Tesseract" in reason


# ─────────────────────────────────────────────────────────────
# construct: text + arc shape kinds
# ─────────────────────────────────────────────────────────────
def test_construct_text_kind_anchors_content_at_a_point():
    from framegraph.vision.infrastructure.construct import build_document

    yaml_text, summaries = build_document(
        [{"kind": "text", "points": [[40, 60]], "text": "Hello", "size": 18}],
        width=200, height=120)
    s = summaries[0]
    assert s["kind"] == "text" and s["text"] == "Hello"
    assert s["box"][0] == 40.0 and s["box"][1] == 60.0 and s["box"][3] > 18
    assert "Hello" in yaml_text


def test_construct_text_requires_content_and_size():
    from framegraph.vision.infrastructure.construct import build_document

    with pytest.raises(ValueError, match="text"):
        build_document([{"kind": "text", "points": [[1, 2]], "size": 12}],
                       width=10, height=10)
    with pytest.raises(ValueError, match="size"):
        build_document([{"kind": "text", "points": [[1, 2]], "text": "x"}],
                       width=10, height=10)


def test_construct_arc_three_point_derives_the_circumcircle():
    from framegraph.vision.infrastructure.construct import build_document

    yaml_text, summaries = build_document(
        [{"kind": "arc", "points": [[0, 50], [50, 0], [100, 50]]}],
        width=120, height=120)
    s = summaries[0]
    assert s["kind"] == "arc"
    assert s["center"][0] == pytest.approx(50.0) and s["center"][1] == pytest.approx(50.0)
    assert s["r"] == pytest.approx(50.0)
    assert " A " in yaml_text or "A 50" in yaml_text        # an SVG arc path was authored


def test_construct_arc_center_radius_angles():
    from framegraph.vision.infrastructure.construct import build_document

    _, summaries = build_document(
        [{"kind": "arc", "points": [[50, 50]], "r": 20,
          "start_deg": 0, "end_deg": 90}],
        width=120, height=120)
    s = summaries[0]
    assert s["r"] == pytest.approx(20.0) and s["sweep_deg"] == pytest.approx(90.0)


def test_construct_arc_rejects_collinear_and_degenerate():
    from framegraph.vision.infrastructure.construct import build_document

    with pytest.raises(ValueError, match="collinear"):
        build_document([{"kind": "arc", "points": [[0, 0], [1, 1], [2, 2]]}],
                       width=10, height=10)
    with pytest.raises(ValueError, match="arc"):
        build_document([{"kind": "arc", "points": [[5, 5]], "r": 20}],
                       width=10, height=10)


def test_matchscore_samples_arc_along_the_circle():
    from framegraph.vision.infrastructure import matchscore as MS

    pts = MS.sample_shape({"kind": "arc", "points": [[0, 50], [50, 0], [100, 50]]},
                          spacing=2.0)
    assert len(pts) > 10
    for x, y in pts:
        assert math.hypot(x - 50, y - 50) == pytest.approx(50.0, abs=0.5)
        assert y <= 50.5                                    # stays on the top half
    assert pts[0] == pytest.approx((0.0, 50.0), abs=0.5)
    assert pts[-1] == pytest.approx((100.0, 50.0), abs=0.5)


def test_matchscore_text_contributes_no_edge_samples():
    from framegraph.vision.infrastructure import matchscore as MS

    assert MS.sample_shape({"kind": "text", "points": [[10, 10]],
                            "text": "x", "size": 12}) == []


# ─────────────────────────────────────────────────────────────
# matchscore: geometry args accept workspace pin ids
# ─────────────────────────────────────────────────────────────
def test_resolve_geometry_args_mixes_pin_ids_and_raw_points():
    from framegraph.vision.infrastructure import matchscore as MS

    anchors = {"P1": (10.0, 20.0), "A9": (50.0, 40.0)}
    pairs, groups = MS.resolve_geometry_args(
        [["P1", [30, 20]]], [["P1", "A9", [90, 60]]], anchors)
    assert pairs == [[[10.0, 20.0], [30.0, 20.0]]]
    assert groups == [[[10.0, 20.0], [50.0, 40.0], [90.0, 60.0]]]


def test_resolve_geometry_args_unknown_pin_is_loud():
    from framegraph.vision.infrastructure import matchscore as MS

    with pytest.raises(ValueError, match="unknown pin"):
        MS.resolve_geometry_args([["NOPE", [0, 0]]], None, {"P1": (1.0, 2.0)})


def test_resolve_geometry_args_passes_none_through():
    from framegraph.vision.infrastructure import matchscore as MS

    assert MS.resolve_geometry_args(None, None, {}) == (None, None)


# ─────────────────────────────────────────────────────────────
# svg_import: <use>, CSS <style>, <text>, gradientTransform, clipPath
# ─────────────────────────────────────────────────────────────
def test_svg_use_instances_a_defs_shape_once():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    objs = svg_to_objects(
        '<svg viewBox="0 0 100 100"><defs>'
        '<rect id="u" x="0" y="0" width="10" height="5" fill="#123456"/></defs>'
        '<use href="#u" x="20" y="30"/></svg>')
    assert len(objs) == 1                                   # defs content not double-emitted
    o = objs[0]
    assert o["type"] == "rect" and o["fill"] == "#123456"
    assert "translate(20" in o["style"]["transform"]


def test_svg_use_xlink_href_and_self_cycle_guard():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    objs = svg_to_objects(
        '<svg viewBox="0 0 10 10" xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<defs><circle id="c" cx="1" cy="2" r="3" fill="#0f0"/>'
        '<use id="loop" xlink:href="#loop"/></defs>'
        '<use xlink:href="#c"/><use xlink:href="#loop"/></svg>')
    assert len(objs) == 1 and objs[0]["type"] == "ellipse"


def test_svg_css_class_rule_resolves_paint():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    objs = svg_to_objects(
        '<svg viewBox="0 0 10 10">'
        "<style>.a{fill:#ff0000;stroke:#001122;stroke-width:3}</style>"
        '<rect class="a" x="0" y="0" width="4" height="4"/></svg>')
    o = objs[0]
    assert o["fill"] == "#ff0000" and o["stroke"] == "#001122"
    assert o["stroke_style"]["stroke_width"] == 3.0


def test_svg_inline_style_attribute_wins_over_presentation():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    o = svg_to_objects('<svg viewBox="0 0 10 10">'
                       '<rect x="0" y="0" width="4" height="4" fill="#000" '
                       'style="fill:#00ff00"/></svg>')[0]
    assert o["fill"] == "#00ff00"


def test_svg_text_lowers_to_text_object():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    o = svg_to_objects('<svg viewBox="0 0 100 40"><text x="10" y="30" font-size="20" '
                       'fill="#222" font-family="Inter, sans-serif">Hi</text></svg>')[0]
    assert o["type"] == "text" and o["text"] == "Hi"
    x, y, w, h = o["box"]
    assert y == pytest.approx(10.0) and x == pytest.approx(10.0)    # baseline − font-size
    assert h >= 20 and w > 0
    assert o["style"]["font_size"] == 20.0 and o["style"]["color"] == "#222"
    assert o["style"]["font_family"][0] == "Inter"


def test_svg_text_anchor_middle_shifts_the_box():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    left = svg_to_objects('<svg viewBox="0 0 100 40">'
                          '<text x="50" y="30" font-size="10">mm</text></svg>')[0]
    mid = svg_to_objects('<svg viewBox="0 0 100 40"><text x="50" y="30" font-size="10" '
                         'text-anchor="middle">mm</text></svg>')[0]
    assert mid["box"][0] < left["box"][0]


def test_svg_gradient_transform_rotates_the_angle():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    svg = ('<svg viewBox="0 0 10 10"><defs>'
           '<linearGradient id="g" x1="0" y1="0" x2="1" y2="0" '
           'gradientTransform="rotate(90)">'
           '<stop offset="0" stop-color="#f00"/><stop offset="1" stop-color="#00f"/>'
           '</linearGradient></defs>'
           '<rect width="10" height="10" fill="url(#g)"/></svg>')
    g = svg_to_objects(svg)[0]["fill"]
    assert isinstance(g, dict) and round(g["angle"]) == 180  # to-right rotated → to-bottom


def test_svg_gradient_href_inherits_stops():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    svg = ('<svg viewBox="0 0 10 10" xmlns:xlink="http://www.w3.org/1999/xlink"><defs>'
           '<linearGradient id="base">'
           '<stop offset="0" stop-color="#ff0000"/><stop offset="1" stop-color="#0000ff"/>'
           '</linearGradient>'
           '<linearGradient id="g" xlink:href="#base" x1="0" y1="0" x2="1" y2="0"/>'
           '</defs><rect width="10" height="10" fill="url(#g)"/></svg>')
    g = svg_to_objects(svg)[0]["fill"]
    assert isinstance(g, dict)
    assert [s["color"] for s in g["stops"]] == ["#ff0000", "#0000ff"]


def test_svg_clip_path_rect_lowers_to_style_clip():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    svg = ('<svg viewBox="0 0 10 10"><defs><clipPath id="c">'
           '<rect x="1" y="2" width="3" height="4"/></clipPath></defs>'
           '<rect x="0" y="0" width="10" height="10" fill="#123" clip-path="url(#c)"/></svg>')
    o = svg_to_objects(svg)[0]
    assert o["style"]["clip_path"] == {"shape": "inset", "args": {"box": [1.0, 2.0, 3.0, 4.0]}}


def test_svg_clip_path_circle_and_polygon_lower():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    svg = ('<svg viewBox="0 0 10 10"><defs>'
           '<clipPath id="c1"><circle cx="5" cy="5" r="2"/></clipPath>'
           '<clipPath id="c2"><polygon points="0,0 4,0 4,4"/></clipPath></defs>'
           '<rect width="10" height="10" fill="#123" clip-path="url(#c1)"/>'
           '<rect width="10" height="10" fill="#456" clip-path="url(#c2)"/></svg>')
    o1, o2 = svg_to_objects(svg)
    assert o1["style"]["clip_path"] == {"shape": "circle",
                                        "args": {"center": [5.0, 5.0], "r": 2.0}}
    assert o2["style"]["clip_path"]["shape"] == "polygon"
    assert o2["style"]["clip_path"]["args"]["points"] == [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0]]


def test_svg_unresolvable_clip_path_is_dropped_not_fatal():
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    o = svg_to_objects('<svg viewBox="0 0 10 10"><rect width="4" height="4" fill="#123" '
                       'clip-path="url(#missing)"/></svg>')[0]
    assert o["type"] == "rect" and "clip_path" not in o.get("style", {})


def test_svg_symbol_renders_only_when_instanced():
    """Per SVG spec a <symbol> paints only via <use>: the sprite convention
    (symbols as direct <svg> children) must not double-emit geometry."""
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    svg = ("<svg xmlns='http://www.w3.org/2000/svg' "
           "xmlns:xlink='http://www.w3.org/1999/xlink' width='200' height='40'>"
           "<symbol id='ic'><rect x='0' y='0' width='10' height='10' fill='#111'/></symbol>"
           "<use xlink:href='#ic' x='100'/></svg>")
    objects = svg_to_objects(svg)
    rects = [o for o in objects if o.get("type") == "rect"]
    assert len(rects) == 1, "symbol must emit exactly once (via its <use>)"

    orphan = ("<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40'>"
              "<symbol id='ic'><rect x='0' y='0' width='10' height='10'/></symbol></svg>")
    assert [o for o in svg_to_objects(orphan) if o.get("type") == "rect"] == []
