#!/usr/bin/env python3
"""fit_primitives — measured region points → parametric primitives (recon gap F1).

The bridge a primitives-first reconstruction needs: detect_regions hands back
boundary polygons/pixel samples, and the author needs {line | circular arc |
elliptical arc} parameters — centre, radii, angular span, stroke thickness,
angle — not paths. Ground truth here is synthetic bands with known parameters,
including the exact elliptical bowl geometry recovered by hand (cv2 in a shell)
during the poster reconstruction session.
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
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

np = pytest.importorskip("numpy")

from frameforge.vision.domain.primitives_fit import (  # noqa: E402
    fit_circle_arc, fit_ellipse_arc, fit_line, fit_primitive)


def band_line(p0, p1, width, n=400, seed=7):
    rng = np.random.default_rng(seed)
    t = rng.uniform(0, 1, n)
    d = np.array([p1[0] - p0[0], p1[1] - p0[1]], float)
    nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    off = rng.uniform(-width / 2, width / 2, n)
    return np.array(p0) + t[:, None] * d + off[:, None] * nrm


def band_arc(c, r, a0, a1, thickness, n=600, seed=7, b=None):
    rng = np.random.default_rng(seed)
    th = np.radians(rng.uniform(a0, a1, n))
    rr = rng.uniform(-thickness / 2, thickness / 2, n)
    a_ax, b_ax = r, (b if b is not None else r)
    return np.c_[c[0] + (a_ax + rr) * np.cos(th), c[1] + (b_ax + rr) * np.sin(th)]


def test_line_band_recovery():
    pts = band_line((10, 20), (200, 150), width=8)
    fit = fit_line(pts)
    assert fit["kind"] == "line"
    assert abs(fit["angle_deg"] - math.degrees(math.atan2(130, 190))) < 1.5
    assert abs(fit["length"] - math.hypot(190, 130)) < 8
    assert 5 <= fit["width"] <= 11
    best = fit_primitive(pts)
    assert best["kind"] == "line"


def test_circle_arc_band_recovery():
    pts = band_arc((300, 200), 120, -140, 100, thickness=20)
    fit = fit_circle_arc(pts)
    assert np.hypot(fit["center"][0] - 300, fit["center"][1] - 200) < 3
    assert abs(fit["radius"] - 120) < 3
    assert 14 <= fit["thickness"] <= 26
    a0, a1 = fit["span_deg"]
    assert abs(a0 - (-140)) < 7 and abs(a1 - 100) < 7
    assert fit_primitive(pts)["kind"] == "arc"


def test_ellipse_arc_recovery_poster_bowl():
    # the lower bowl measured from the stage-poster reference
    pts = band_arc((253, 393), 112, -139, 103, thickness=34, b=124)
    fit = fit_ellipse_arc(pts)
    assert np.hypot(fit["center"][0] - 253, fit["center"][1] - 393) < 5
    assert abs(fit["radii"][0] - 112) < 6 and abs(fit["radii"][1] - 124) < 6
    assert 26 <= fit["thickness"] <= 42
    best = fit_primitive(pts)
    assert best["kind"] == "ellipse-arc"
    assert best["rms"] < fit_circle_arc(pts)["rms"]


def test_wraparound_span():
    pts = band_arc((0, 0), 100, 150, 210, thickness=10)
    fit = fit_circle_arc(pts)
    a0, a1 = fit["span_deg"]
    length = (a1 - a0) % 360
    assert 48 <= length <= 72


def test_fit_primitive_reports_ranked_candidates():
    pts = band_arc((50, 60), 80, -90, 90, thickness=12)
    best = fit_primitive(pts)
    kinds = [c["kind"] for c in best["candidates"]]
    assert set(kinds) == {"line", "arc", "ellipse-arc"}
    rmss = [c["rms"] for c in best["candidates"]]
    assert rmss == sorted(rmss)


def test_usecase_accepts_plain_shape_dicts(tmp_path):
    from frameforge.mcp import usecases
    pts = band_arc((300, 200), 120, -120, 80, thickness=18).tolist()
    out = usecases.fit_primitives(
        shapes=[{"name": "bowl", "points": pts}],
        session_id="fit-test", session_root=str(tmp_path))
    assert out["ok"] is True
    fit = out["fits"][0]
    assert fit["name"] == "bowl"
    assert fit["best"]["kind"] == "arc"
    assert abs(fit["best"]["radius"] - 120) < 3
    assert any(c["kind"] == "ellipse-arc" for c in fit["candidates"])


class _FakeFastMCP:
    def __init__(self, name, **kwargs):
        self.tools, self.resources, self.prompts = {}, {}, {}

    def tool(self, **_kw):
        def dec(fn):
            self.tools[fn.__name__] = fn
            return fn
        return dec

    def resource(self, uri, **_kw):
        def dec(fn):
            self.resources[uri] = fn
            return fn
        return dec

    def prompt(self, **_kw):
        def dec(fn):
            self.prompts[fn.__name__] = fn
            return fn
        return dec


def test_server_registers_and_dispatches_fit_primitives(tmp_path):
    from frameforge.mcp.server import create_server
    server = create_server(session_root=tmp_path, fastmcp_cls=_FakeFastMCP)
    assert "fit_primitives" in server.tools
    pts = band_arc((100, 90), 60, -90, 90, thickness=10).tolist()
    out = server.tools["fit_primitives"](shapes=[{"points": pts}])
    payload = getattr(out, "structuredContent", out)
    assert payload["ok"] is True
    assert payload["fits"][0]["best"]["kind"] == "arc"
