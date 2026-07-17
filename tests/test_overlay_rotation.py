#!/usr/bin/env python3
"""overlay_images rotation fit — opt-in contract extension (recon gap F6b).

The similarity fit deliberately excluded rotation (see
frameforge.vision.domain.fitting's scope note); tilted-scan references
therefore surfaced as unexplainable residuals. This adds rotation as an
explicitly opt-in second model — the default contract stays rotation-free
and byte-stable.
"""
from __future__ import annotations

import base64
import io
import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from frameforge.vision.domain.fitting import (  # noqa: E402
    fit_similarity, fit_similarity_rotation)

PIL = pytest.importorskip("PIL.Image")


def _apply_true(o, *, s, theta_deg, t):
    th = math.radians(theta_deg)
    return (s * (math.cos(th) * o[0] - math.sin(th) * o[1]) + t[0],
            s * (math.sin(th) * o[0] + math.cos(th) * o[1]) + t[1])


TRUE = {"s": 1.3, "theta_deg": 12.0, "t": (5.0, -8.0)}


def _pairs():
    pts = [(0.0, 0.0), (100.0, 0.0), (100.0, 80.0), (0.0, 80.0), (37.0, 21.0)]
    return [(_apply_true(o, **TRUE), o) for o in pts]


def test_rotation_fit_recovers_known_transform():
    fit = fit_similarity_rotation(_pairs())
    assert fit.scale == pytest.approx(1.3, abs=1e-6)
    assert fit.rotation_deg == pytest.approx(12.0, abs=1e-6)
    assert fit.tx == pytest.approx(5.0, abs=1e-6)
    assert fit.ty == pytest.approx(-8.0, abs=1e-6)
    bx, by = fit.apply(37.0, 21.0)
    tx, ty = _apply_true((37.0, 21.0), **TRUE)
    assert (bx, by) == (pytest.approx(tx), pytest.approx(ty))


def test_rotation_fit_needs_two_pairs():
    with pytest.raises(ValueError, match="rotation"):
        fit_similarity_rotation(_pairs()[:1])


def test_default_similarity_contract_unchanged():
    fit = fit_similarity(_pairs())
    assert "no rotation" in fit.to_dict()["model"]


def _data_uri(size, color):
    buf = io.BytesIO()
    PIL.new("RGB", size, color).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_usecase_opt_in_rotation_reports_angle(tmp_path):
    from frameforge.mcp.usecases import overlay_images
    landmarks = [{"base": list(b), "overlay": list(o)} for b, o in _pairs()]
    out = overlay_images(
        base=_data_uri((200, 160), (240, 240, 240)),
        overlay=_data_uri((160, 120), (20, 20, 20)),
        landmarks=landmarks, rotation=True,
        session_id="rot-test", session_root=str(tmp_path))
    assert out["ok"] is True
    align = out["spatial"]["alignment"]
    assert "rotation" in align["model"]
    assert align["rotation_deg"] == pytest.approx(12.0, abs=0.01)
    assert out["spatial"]["rms_residual_px"] < 0.01


def test_usecase_default_stays_rotation_free(tmp_path):
    from frameforge.mcp.usecases import overlay_images
    landmarks = [{"base": list(b), "overlay": list(o)} for b, o in _pairs()]
    out = overlay_images(
        base=_data_uri((200, 160), (240, 240, 240)),
        overlay=_data_uri((160, 120), (20, 20, 20)),
        landmarks=landmarks,
        session_id="rot-test2", session_root=str(tmp_path))
    assert out["ok"] is True
    assert "no rotation" in out["spatial"]["alignment"]["model"]
    assert out["spatial"]["rms_residual_px"] > 1.0   # the tilt shows up honestly
