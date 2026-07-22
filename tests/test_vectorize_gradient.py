#!/usr/bin/env python3
"""RED → integration contract for gradient paint extraction in vectorize (Gap 1).

`vectorize_image` gains `fill_mode='gradient'` (fit per-shape gradient fills
from the source raster; default 'flat' is byte-compatible with the old
behaviour) and, for trace mode, `thresholds=[...]` (multi-level potrace
layering in one call — the technique that reconstructed the lotus emblem).
Covers: the region and trace lanes, precise colour/angle recovery on a
single-shape trace, the layered-thresholds composite, structured errors for
unsupported combinations, the flat-default regression pin, and the MCP tool
registration surface.
"""
from __future__ import annotations

import os
import shutil
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

pytest.importorskip("PIL")
yaml = pytest.importorskip("yaml")

from PIL import Image, ImageDraw  # noqa: E402

_HAS_POTRACE = shutil.which("potrace") is not None
try:
    import cv2  # noqa: F401
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False


def _ramp_rect_png(tmp_path, name="ramp.png"):
    """A horizontal blue→cyan ramp rectangle on black — one linear-fit target."""
    img = Image.new("RGB", (240, 160), "black")
    for i in range(160):
        t = i / 159.0
        col = (int(30 + 50 * t), int(60 + 170 * t), int(220 + 20 * t))
        ImageDraw.Draw(img).line([(40 + i, 40), (40 + i, 120)], fill=col)
    p = tmp_path / name
    img.save(p)
    return str(p)


def _radial_disc_png(tmp_path, name="disc.png"):
    """A bright-core → magenta-rim disc on black — one radial-fit target."""
    img = Image.new("RGB", (200, 200), "black")
    px = img.load()
    for y in range(200):
        for x in range(200):
            r = ((x - 100) ** 2 + (y - 100) ** 2) ** 0.5
            if r <= 70:
                t = r / 70.0
                px[x, y] = (int(250 - 60 * t), int(245 - 200 * t), int(250 - 40 * t))
    p = tmp_path / name
    img.save(p)
    return str(p)


def _two_level_png(tmp_path, name="levels.png"):
    """A dim outer square + bright inner square — the thresholds layering target."""
    img = Image.new("RGB", (160, 160), "black")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 140, 140], fill=(70, 70, 90))
    d.rectangle([55, 55, 105, 105], fill=(230, 230, 240))
    p = tmp_path / name
    img.save(p)
    return str(p)


def _doc_fills(session_root, sid):
    doc = yaml.safe_load(
        (session_root / sid / "generated.fg.yaml").read_text(encoding="utf-8"))
    fills = []
    for layer in doc["pages"][0]["layers"]:
        for obj in layer["objects"]:
            if "fill" in obj and obj.get("type") != "rect":
                fills.append(obj["fill"])
    return fills


# ------------------------------------------------------------------- trace lane
@pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")
def test_trace_gradient_recovers_ramp_endpoints_and_axis(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    res = vectorize_image(
        image=_ramp_rect_png(tmp_path), mode="trace", fill_mode="gradient",
        threshold=20, raster_png=False, session_id="t-ramp", session_root=tmp_path)
    assert res.get("ok") is True, res.get("error")
    paint = res["vectorize"]["paint"]
    assert paint["fill_mode"] == "gradient"
    assert paint["fitted"] >= 1

    grads = [f for f in _doc_fills(tmp_path, "t-ramp") if isinstance(f, dict)]
    assert grads, "the traced ramp must carry a fitted gradient fill"
    g = max(grads, key=lambda f: len(f.get("stops", [])))
    assert g["kind"] == "linear"
    # A1 upgrade: the pipeline emits the EXACT user-space `line` (object-local
    # coordinates), not the bbox-relative `angle` approximation this contract
    # originally pinned — direction must still be horizontal (|dx| ≫ |dy| holds
    # in any uniform frame, including through the potrace y-flip).
    (x1, y1), (x2, y2) = g["line"]
    assert abs(x2 - x1) > 5 * abs(y2 - y1), g["line"]
    greens = [int(s["color"].lstrip("#")[2:4], 16) for s in g["stops"]]
    assert max(greens) > 180 and min(greens) < 110, greens


@pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")
def test_trace_gradient_fits_radial_disc(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    res = vectorize_image(
        image=_radial_disc_png(tmp_path), mode="trace", fill_mode="gradient",
        threshold=20, raster_png=False, session_id="t-disc", session_root=tmp_path)
    assert res.get("ok") is True, res.get("error")
    grads = [f for f in _doc_fills(tmp_path, "t-disc") if isinstance(f, dict)]
    assert any(g["kind"] == "radial" for g in grads), \
        f"disc must fit radial, got kinds {[g['kind'] for g in grads]}"
    radial = next(g for g in grads if g["kind"] == "radial")
    # A1 upgrade: user-space radial — a px `radius` plus a numeric [x, y] `at`
    # in the object's local space (precise-placement guarantees are pinned at
    # the domain/painter level; here the family + user form is the contract).
    assert radial.get("radius", 0) > 0
    at = radial["at"]
    assert isinstance(at, list) and len(at) == 2


@pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")
def test_trace_thresholds_layering(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    single = vectorize_image(
        image=_two_level_png(tmp_path), mode="trace", threshold=40,
        raster_png=False, session_id="t-single", session_root=tmp_path)
    layered = vectorize_image(
        image=_two_level_png(tmp_path), mode="trace", thresholds=[40, 180],
        fill_mode="gradient", raster_png=False, session_id="t-multi",
        session_root=tmp_path)
    assert layered.get("ok") is True, layered.get("error")
    assert layered["vectorize"]["thresholds"] == [40, 180]
    assert layered["vectorize"]["object_count"] > single["vectorize"]["object_count"], \
        "each threshold level must contribute its own layer of objects"


# ------------------------------------------------------------------ region lane
@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV (vision group) not installed")
def test_region_gradient_fits_and_validates(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    res = vectorize_image(
        image=_ramp_rect_png(tmp_path), mode="region", fill_mode="gradient",
        colors=5, raster_png=False, session_id="r-grad", session_root=tmp_path)
    assert res.get("ok") is True, res.get("error")
    assert res["validation"]["ok"] is True
    paint = res["vectorize"]["paint"]
    assert paint["fitted"] >= 1
    assert paint["fitted"] + paint["flat"] == res["vectorize"]["object_count"]
    assert any(isinstance(f, dict) for f in _doc_fills(tmp_path, "r-grad"))


# ------------------------------------------------------- regression + errors
@pytest.mark.skipif(not _HAS_CV2, reason="OpenCV (vision group) not installed")
def test_default_fill_mode_flat_is_unchanged(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    res = vectorize_image(
        image=_ramp_rect_png(tmp_path), mode="region", colors=5,
        raster_png=False, session_id="r-flat", session_root=tmp_path)
    assert res.get("ok") is True
    assert "paint" not in res["vectorize"], \
        "default flat mode must not grow a paint summary (byte-compatible result)"
    fills = _doc_fills(tmp_path, "r-flat")
    assert fills and all(isinstance(f, str) for f in fills)


def test_gradient_on_outline_is_a_structured_error(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    res = vectorize_image(
        image=_ramp_rect_png(tmp_path), mode="outline", fill_mode="gradient",
        raster_png=False, session_id="o-err", session_root=tmp_path)
    assert res.get("ok") is False
    msg = str(res.get("error", "")).lower()
    assert "outline" in msg and "gradient" in msg


def test_unknown_fill_mode_is_a_structured_error(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    res = vectorize_image(
        image=_ramp_rect_png(tmp_path), mode="region", fill_mode="mesh",
        raster_png=False, session_id="m-err", session_root=tmp_path)
    assert res.get("ok") is False
    msg = str(res.get("error", "")).lower()
    assert "fill_mode" in msg and "gradient" in msg and "flat" in msg


def test_thresholds_outside_trace_is_a_structured_error(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    res = vectorize_image(
        image=_ramp_rect_png(tmp_path), mode="region", thresholds=[40, 160],
        raster_png=False, session_id="th-err", session_root=tmp_path)
    assert res.get("ok") is False
    assert "trace" in str(res.get("error", "")).lower()


# ------------------------------------------------------------------ MCP surface
def test_mcp_tool_exposes_fill_mode_and_thresholds(tmp_path):
    import inspect

    from frameforge.mcp.server import create_server

    class FakeFastMCP:
        def __init__(self, name, **kwargs):
            self.tools = {}

        def tool(self, **_kw):
            def decorate(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorate

        def resource(self, uri, **_kw):
            def decorate(fn):
                return fn
            return decorate

        def prompt(self, **_kw):
            def decorate(fn):
                return fn
            return decorate

    srv = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)
    params = inspect.signature(srv.tools["vectorize_image"]).parameters
    assert "fill_mode" in params and "thresholds" in params
    assert params["fill_mode"].default == "flat"
    assert params["thresholds"].default is None
    # B5: the AA-aware subpixel trace stage rides the same tool surface.
    assert "supersample" in params
    assert params["supersample"].default == 1
