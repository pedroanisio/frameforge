#!/usr/bin/env python3
"""RED → contract for shape-conforming banded shading (Gap A2).

One gradient per shape cannot express the measured residual of glossy-emblem
reconstruction: a dark contour-following rim plus a bright interior. SVG has
no mesh gradient, so A2 decomposes the shading by DISTANCE-TO-BOUNDARY bands:

* a chamfer distance field over the shape mask;
* band thresholds at interior-distance quantiles;
* the CORE band re-fits the object's own fill;
* each RIM band becomes an overlay of the SAME geometry — fill-less, painted
  by an inner stroke (width = 2·threshold, self-clipped via style.clip_path)
  carrying that band's fitted user-space paint. Strokes follow the contour by
  construction, so the banding is shape-conforming with zero new geometry.

Acceptance: on a rim-shaded synthetic, the banded decomposition must beat the
single-gradient fit by a wide margin under an analytic per-pixel evaluation.
``bands=1`` is byte-identical to the previous behaviour.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

pytest.importorskip("PIL")
np = pytest.importorskip("numpy")
from PIL import Image  # noqa: E402

RIM = (20.0, 24.0, 60.0)
CORE = (200.0, 180.0, 240.0)
RECT = (40, 30, 160, 90)          # x0, y0, x1, y1 on a 200x120 canvas


def _rect_dist(x, y):
    """Exact distance to the rect border for interior pixels (0 outside)."""
    x0, y0, x1, y1 = RECT
    if not (x0 <= x < x1 and y0 <= y < y1):
        return 0.0
    return min(x - x0 + 1, x1 - x, y - y0 + 1, y1 - y)


def _shaded_image():
    """Dark rim → bright core, plus an along-x drift the core fit must carry."""
    img = Image.new("RGB", (200, 120), (0, 0, 0))
    px = img.load()
    x0, y0, x1, y1 = RECT
    for y in range(y0, y1):
        for x in range(x0, x1):
            t = min(_rect_dist(x, y) / 12.0, 1.0)
            drift = 40.0 * (x - x0) / (x1 - x0)
            px[x, y] = tuple(int(round(r + (c - r) * t + (drift if i == 0 else 0.0)))
                             for i, (r, c) in enumerate(zip(RIM, CORE)))
    return img


def _poly_obj():
    x0, y0, x1, y1 = RECT
    return {"type": "polygon", "fill": "#808080",
            "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


# ------------------------------------------------------------------ dist field
def test_chamfer_distance_rect():
    from frameforge.vision.infrastructure.vectorize import _chamfer_distance

    mask = np.zeros((120, 200), dtype=np.uint8)
    mask[30:90, 40:160] = 1
    dist = _chamfer_distance(mask)
    assert dist[60, 100] == pytest.approx(30.0, abs=1.5)     # centre: half-height
    assert dist[31, 100] == pytest.approx(2.0, abs=1.0)      # one in from the edge
    assert dist[10, 10] == 0.0                               # outside


# ------------------------------------------------------------ band emission
def test_bands_emit_selfclipped_inner_strokes():
    from frameforge.vision.infrastructure.vectorize import apply_gradient_fills

    objs = [_poly_obj()]
    summary = apply_gradient_fills(objs, _shaded_image(), min_pixels=200, bands=3)
    assert summary["banded"] == 1 and summary["bands"] == 3
    assert len(objs) == 3, "base + one overlay per rim band"
    base, wide, narrow = objs
    assert "fill" in base and isinstance(base["fill"], (dict, str))
    for overlay in (wide, narrow):
        assert "fill" not in overlay, "band overlays are stroke-only"
        assert overlay.get("stroke") is not None
        clip = (overlay.get("style") or {}).get("clip_path")
        assert clip and clip.get("shape") == "polygon", "inner stroke needs the self-clip"
        assert overlay["points"] == base["points"]
    w_wide = float(wide["stroke_style"]["stroke_width"])
    w_narrow = float(narrow["stroke_style"]["stroke_width"])
    assert w_wide > w_narrow > 0, "outer rims paint later with narrower strokes"


def test_bands_1_is_identity_with_previous_behaviour():
    from frameforge.vision.infrastructure.vectorize import apply_gradient_fills

    img = _shaded_image()
    single = [_poly_obj()]
    s1 = apply_gradient_fills(single, img, min_pixels=200)
    banded_off = [_poly_obj()]
    s2 = apply_gradient_fills(banded_off, img, min_pixels=200, bands=1)
    assert single == banded_off
    assert "banded" not in s1 and "banded" not in s2


def test_thin_shapes_are_not_banded():
    from frameforge.vision.infrastructure.vectorize import apply_gradient_fills

    img = Image.new("RGB", (200, 120), (0, 0, 0))
    px = img.load()
    for y in range(50, 53):
        for x in range(20, 180):
            px[x, y] = (120, 40, 200)
    sliver = {"type": "polygon", "fill": "#808080",
              "points": [[20, 50], [180, 50], [180, 53], [20, 53]]}
    objs = [sliver]
    summary = apply_gradient_fills(objs, img, min_pixels=50, bands=3)
    assert len(objs) == 1, "a 3px sliver has no room for rim bands"
    assert summary.get("banded", 0) == 0


# ------------------------------------------------------------------ acceptance
def _eval_paint(paint, x, y):
    """Analytically evaluate a fitted paint at a pixel (test-side oracle)."""
    if isinstance(paint, str):
        h = paint.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    stops = [(float(s["position"].rstrip("%")) / 100.0,
              tuple(int(s["color"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)))
             for s in paint["stops"]]
    if paint["kind"] == "linear":
        (x1, y1), (x2, y2) = paint["line"]
        dx, dy = x2 - x1, y2 - y1
        denom = dx * dx + dy * dy or 1.0
        t = ((x - x1) * dx + (y - y1) * dy) / denom
    else:
        cx, cy = paint["at"]
        t = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / float(paint["radius"])
    t = min(1.0, max(0.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1 or (p1 == stops[-1][0]):
            if p1 == p0:
                return c1
            u = min(1.0, max(0.0, (t - p0) / (p1 - p0)))
            return tuple(c0[i] + (c1[i] - c0[i]) * u for i in range(3))
    return stops[-1][1]


def _stack_rms(objs, img):
    """rms of the emitted paint stack vs the source, using exact rect distance."""
    base = objs[0]
    overlays = objs[1:]
    # each overlay's stroke covers dist < width/2; narrower ones paint later
    rings = sorted(((float(o["stroke_style"]["stroke_width"]) / 2.0, o["stroke"])
                    for o in overlays), key=lambda t: t[0])
    px = img.load()
    x0, y0, x1, y1 = RECT
    total, n = 0.0, 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = _rect_dist(x, y)
            paint = base["fill"]
            for t, ring_paint in rings:
                if d < t:
                    paint = ring_paint
                    break
            pred = _eval_paint(paint, x, y)
            src = px[x, y]
            total += sum((float(pred[i]) - src[i]) ** 2 for i in range(3))
            n += 3
    return (total / n) ** 0.5


def test_banded_beats_single_gradient():
    from frameforge.vision.infrastructure.vectorize import apply_gradient_fills

    img = _shaded_image()
    single = [_poly_obj()]
    apply_gradient_fills(single, img, min_pixels=200)
    banded = [_poly_obj()]
    apply_gradient_fills(banded, img, min_pixels=200, bands=3)

    rms_single = _stack_rms(single, img)
    rms_banded = _stack_rms(banded, img)
    assert rms_banded < 0.6 * rms_single, (rms_banded, rms_single)


# ------------------------------------------------------------------- mcp lane
def test_mcp_fill_mode_shading(tmp_path):
    pytest.importorskip("cv2")
    from frameforge.mcp.usecases import vectorize_image

    p = tmp_path / "shaded.png"
    _shaded_image().save(p)
    res = vectorize_image(image=str(p), mode="region", fill_mode="shading",
                          colors=5, raster_png=False, session_id="shade",
                          session_root=tmp_path)
    assert res.get("ok") is True, res.get("error")
    paint = res["vectorize"]["paint"]
    assert paint["fill_mode"] == "shading"
    assert paint["bands"] == 3


def test_mcp_shading_on_outline_is_a_structured_error(tmp_path):
    from frameforge.mcp.usecases import vectorize_image

    p = tmp_path / "shaded.png"
    _shaded_image().save(p)
    res = vectorize_image(image=str(p), mode="outline", fill_mode="shading",
                          raster_png=False, session_id="shade-err",
                          session_root=tmp_path)
    assert res.get("ok") is False
    msg = str(res.get("error", "")).lower()
    assert "outline" in msg
