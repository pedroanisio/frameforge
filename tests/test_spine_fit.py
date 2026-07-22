#!/usr/bin/env python3
"""RED → contract for inverse primitive fitting (Gap G1: skeleton → spine).

The authored-primitives lane stalls because nothing on the surface fits a
STRUCTURED primitive to an observed region: petal spines had to be guessed by
hand (clone-v2 plateaued at NCC 0.49 — silhouette-bounded). G1 adds the
inverse of ``sdk.outline.stroke_outline``:

    fit_spine(mask) → {spine, cubic, cubic_rms, width_max, profile, peak,
                       length, elongation}

* the SPINE is extracted by topological thinning + longest skeleton path,
  extended to the region's tips, arc-length resampled (tip-to-tip);
* WIDTH is the distance field sampled along the spine (max + a normalized
  profile with its peak position) — exactly ``stroke_outline``'s vocabulary;
* a single least-squares CUBIC (endpoints anchored) gives the compact
  4-control-point form the authored spec tables hold, with its rms reported;
* the contract is a ROUND TRIP: re-authoring ``stroke_outline(spine,
  width_max, profile)`` from a fit must reproduce the source region at
  IoU ≥ 0.90.

MCP surface: ``detect_regions(fit_spines=True)`` attaches the fit to every
big-enough region — one call from reference image to authorable spec table.
Deterministic throughout; spine direction (which tip is first) is free.
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
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

np = pytest.importorskip("numpy")
pytest.importorskip("PIL")


# --------------------------------------------------------------- test helpers
def _petal_mask(size=(600, 800)):
    """Ground-truth mask from a KNOWN stroke_outline (the round-trip oracle)."""
    from frameforge.sdk.outline import stroke_outline
    from frameforge.vision.infrastructure.vectorize import _shape_mask

    spine = _true_spine()
    obj = stroke_outline(spine, 110, profile=_true_profile, cap="round",
                         join="round", fill="#fff")
    shaped = _shape_mask(obj, size)
    assert shaped is not None
    return np.asarray(shaped[0]) > 0, obj


def _true_spine(n=64):
    b, c1, c2, e = (150, 700), (180, 420), (390, 180), (520, 120)
    pts = []
    for i in range(n + 1):
        s = i / n
        u = 1.0 - s
        pts.append((
            u**3 * b[0] + 3 * u * u * s * c1[0] + 3 * u * s * s * c2[0] + s**3 * e[0],
            u**3 * b[1] + 3 * u * u * s * c1[1] + 3 * u * s * s * c2[1] + s**3 * e[1],
        ))
    return pts


def _true_profile(t):
    peak = 0.4
    if t <= peak:
        return math.sin(min(max(t / peak, 0.0), 1.0) * math.pi / 2.0) ** 0.7
    x = min(max((t - peak) / (1.0 - peak), 0.0), 1.0)
    return math.cos(x * math.pi / 2.0) ** 0.9


def _spine_distance(fit_spine_pts, true_pts):
    """Mean nearest-point distance from fitted spine samples to the true spine."""
    ts = np.asarray(true_pts, dtype=np.float64)
    total = 0.0
    for x, y in fit_spine_pts:
        total += float(np.min(np.hypot(ts[:, 0] - x, ts[:, 1] - y)))
    return total / len(fit_spine_pts)


def _iou(a, b):
    return float((a & b).sum()) / float((a | b).sum())


# ----------------------------------------------------------------- domain lane
def test_chamfer_distance_is_domain_owned():
    from frameforge.vision.domain.spine_fit import chamfer_distance
    from frameforge.vision.infrastructure.vectorize import _chamfer_distance

    assert _chamfer_distance is chamfer_distance, \
        "one distance transform, owned by the domain (vectorize keeps the alias)"


def test_straight_bar_recovers_axis_and_width():
    from frameforge.vision.domain.spine_fit import fit_spine

    mask = np.zeros((260, 400), dtype=bool)
    mask[100:160, 50:350] = True                    # 300×60 horizontal bar
    fit = fit_spine(mask)
    mid = [p for p in fit["spine"] if 120 <= p[0] <= 280]
    assert mid, fit["spine"]
    assert all(abs(y - 130) <= 3.0 for _, y in mid), "spine must ride the bar axis"
    assert fit["width_max"] == pytest.approx(60, abs=8)
    assert fit["length"] == pytest.approx(300, abs=25)
    assert fit["elongation"] > 3.0
    middle = fit["profile"][len(fit["profile"]) // 4: -len(fit["profile"]) // 4]
    assert min(middle) > 0.8, "a bar's width profile is flat through the middle"


def test_round_trip_recovers_the_authored_petal():
    from frameforge.vision.domain.spine_fit import fit_spine

    mask, _ = _petal_mask()
    fit = fit_spine(mask)
    true_pts = _true_spine(n=256)
    d = min(_spine_distance(fit["spine"], true_pts),
            _spine_distance(list(reversed(fit["spine"])), true_pts))
    assert d < 4.0, f"fitted spine strays {d:.2f}px from the authored spine"
    assert fit["width_max"] == pytest.approx(110, rel=0.12)
    assert min(abs(fit["peak"] - 0.4), abs((1.0 - fit["peak"]) - 0.4)) < 0.15
    assert fit["cubic_rms"] < 6.0, "one cubic must describe a flame spine"
    assert len(fit["cubic"]) == 4


def test_round_trip_reconstruction_iou():
    from frameforge.sdk.outline import stroke_outline
    from frameforge.vision.domain.spine_fit import fit_spine, spine_profile
    from frameforge.vision.infrastructure.vectorize import _shape_mask

    mask, _ = _petal_mask()
    fit = fit_spine(mask)
    rebuilt = stroke_outline(fit["spine"], fit["width_max"],
                             profile=spine_profile(fit["profile"]),
                             cap="round", join="round", fill="#fff")
    shaped = _shape_mask(rebuilt, (600, 800))
    assert shaped is not None
    assert _iou(np.asarray(shaped[0]) > 0, mask) >= 0.90


def test_disk_does_not_crash_and_reports_low_elongation():
    from frameforge.vision.domain.spine_fit import fit_spine

    yy, xx = np.mgrid[0:300, 0:300]
    mask = (xx - 150) ** 2 + (yy - 150) ** 2 <= 80 * 80
    fit = fit_spine(mask)
    assert fit["elongation"] < 2.0, "a disk is not spine-like; the ratio must say so"
    assert fit["width_max"] == pytest.approx(160, rel=0.2)


def test_tiny_masks_are_loud():
    from frameforge.vision.domain.spine_fit import fit_spine

    mask = np.zeros((40, 40), dtype=bool)
    mask[10:14, 10:20] = True
    with pytest.raises(ValueError, match="pixels"):
        fit_spine(mask)


def test_fit_is_deterministic():
    from frameforge.vision.domain.spine_fit import fit_spine

    mask, _ = _petal_mask()
    assert fit_spine(mask) == fit_spine(mask)


# ------------------------------------------------------------------- mcp lane
def _two_petal_image(tmp_path):
    from PIL import Image

    from frameforge.sdk.outline import stroke_outline
    from frameforge.vision.infrastructure.vectorize import _shape_mask

    img = np.zeros((800, 600, 3), dtype=np.uint8)
    for spine, col in ((_true_spine(), (60, 160, 250)),
                       ([(430, 700), (445, 500), (460, 320), (470, 180)],
                        (240, 80, 200))):
        obj = stroke_outline(spine, 100, profile=_true_profile, cap="round",
                             join="round", fill="#fff")
        m = np.asarray(_shape_mask(obj, (600, 800))[0]) > 0
        img[m] = col
    p = tmp_path / "petals.png"
    Image.fromarray(img).save(p)
    return str(p)


def test_detect_regions_fit_spines_payload(tmp_path):
    pytest.importorskip("cv2")
    from frameforge.mcp.usecases import detect_regions

    src = _two_petal_image(tmp_path)
    res = detect_regions(image=src, method="flat", fit_spines=True,
                         overlay=False, session_id="sp", session_root=tmp_path)
    assert res.get("ok") is True, res.get("error")
    fitted = [r for r in res["spatial"]["regions"] if r.get("spine")]
    assert len(fitted) >= 2, "both petals must carry a spine fit"
    sp = fitted[0]["spine"]
    for key in ("spine", "cubic", "cubic_rms", "width_max", "profile", "peak",
                "length", "elongation"):
        assert key in sp, f"missing {key!r} in the spine payload"
    assert len(sp["cubic"]) == 4 and sp["width_max"] > 40

    off = detect_regions(image=src, method="flat", overlay=False,
                         session_id="sp0", session_root=tmp_path)
    assert off.get("ok") is True
    assert all("spine" not in r for r in off["spatial"]["regions"]), \
        "fit_spines defaults OFF — the payload must be byte-compatible"


def test_mcp_tool_exposes_fit_spines(tmp_path):
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

    srv = create_server(fastmcp_cls=FakeFastMCP, session_root=tmp_path)
    params = inspect.signature(srv.tools["detect_regions"]).parameters
    assert "fit_spines" in params
    assert params["fit_spines"].default is False
