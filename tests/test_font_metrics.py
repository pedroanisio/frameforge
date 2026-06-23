"""Tests for real-font text measurement and its byte-neutral renderer wiring.

Covers three things:

* the pure :class:`FontMetrics` width arithmetic (synthetic, no fontTools);
* the public SDK author helpers (:func:`measure_text` / :func:`wrap_text` /
  :func:`text_height`) — both their backend-agnostic invariants and their exact
  per-character fallback when real metrics are unavailable;
* the renderer opt-in: ``real_metrics=False`` (the default, and what golden uses)
  is byte-identical to the legacy estimate, while ``real_metrics=True`` routes
  width through real glyph advances.

A final, ``importorskip``-gated test exercises the real fontTools path (mirroring
the PyMuPDF-gated PDF e2e test), so it runs only where the ``metrics`` group is
installed.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.rendering.infrastructure import font_metrics as fmmod
from framegraph.rendering.infrastructure.font_metrics import (
    FontMetrics,
    get_font_metrics,
    measure_text as fm_measure,
)
from framegraph.sdk import measure_text, text_height, wrap_text
from tooling.render_fixtures import Renderer


# --------------------------------------------------------------------------- #
# FontMetrics arithmetic (pure)                                               #
# --------------------------------------------------------------------------- #

def _synthetic() -> FontMetrics:
    # 'a' is half an em wide, 'b' a full em; unknown codepoints fall back to 0.5.
    return FontMetrics({ord("a"): 0.5, ord("b"): 1.0}, default_em=0.5, source_path="synthetic")


def test_fontmetrics_width_sums_advances():
    fm = _synthetic()
    assert fm.width("", 10) == 0.0
    assert fm.width("a", 10) == 5.0
    assert fm.width("ab", 10) == 15.0          # (0.5 + 1.0) * 10
    assert fm.width("?", 10) == 5.0            # missing glyph → default_em


def test_fontmetrics_width_scales_with_size():
    fm = _synthetic()
    assert fm.width("ab", 20) == 2 * fm.width("ab", 10)


# --------------------------------------------------------------------------- #
# SDK author helpers — backend-agnostic invariants                            #
# --------------------------------------------------------------------------- #

SANS = ["Fira Sans", "DejaVu Sans", "sans-serif"]


def test_measure_text_nonneg_and_monotone():
    assert measure_text("", font_family=SANS, font_size=12) == 0.0
    w1 = measure_text("a", font_family=SANS, font_size=12)
    w2 = measure_text("aa", font_family=SANS, font_size=12)
    assert 0 < w1 <= w2                         # advances are non-negative


def test_wrap_text_splits_and_respects_width():
    text = "the quick brown fox jumps over the lazy dog again and again"
    lines = wrap_text(text, width=120, font_family=SANS, font_size=12)
    assert len(lines) >= 2
    assert all(lines)                           # no empty lines
    # every line fits the box under the same metric used to wrap it
    for ln in lines:
        assert measure_text(ln, font_family=SANS, font_size=12) <= 120 + 1e-6
    assert " ".join(lines).split() == text.split()   # no words lost


def test_wrap_text_hard_breaks_overlong_token():
    lines = wrap_text("supercalifragilistic", width=30, font_family=SANS, font_size=12)
    assert len(lines) >= 2                       # a single long token is broken


def test_text_height_counts_lines():
    kw = dict(font_family=SANS, font_size=10, line_height=1.5)
    one = text_height("short", width=10_000, **kw)
    many = text_height("the quick brown fox jumps over the lazy dog", width=80, **kw)
    assert one == 1 * 10 * 1.5
    assert many == len(wrap_text("the quick brown fox jumps over the lazy dog",
                                 width=80, font_family=SANS, font_size=10)) * 10 * 1.5


# --------------------------------------------------------------------------- #
# SDK author helpers — exact per-character fallback (force estimate path)      #
# --------------------------------------------------------------------------- #

def test_measure_text_fallback_estimate(monkeypatch):
    """With real metrics unavailable, width is len * size * avg (0.52 / 0.60)."""
    monkeypatch.setattr(fmmod, "measure_text", lambda *a, **k: None)
    assert measure_text("abcd", font_family=["Helvetica"], font_size=10) == 4 * 10 * 0.52
    assert measure_text("abcd", font_family=["Fira Mono"], font_size=10) == 4 * 10 * 0.60
    assert measure_text("abcd", font_family=["Fira Mono"], font_size=10, bold=True) == \
        pytest.approx(4 * 10 * 0.60 * 1.04)


# --------------------------------------------------------------------------- #
# Renderer wiring — default is byte-identical; opt-in routes to real metrics   #
# --------------------------------------------------------------------------- #

def test_renderer_defaults_to_estimate():
    r = Renderer({}, ".")
    assert r.real_metrics is False
    assert r.measure("abcde", 10, 0.5) == 25.0            # len * size * avg
    assert r.wrap_words("a a a a a", 100, 10, 0.5) == ["a a a a a"]
    assert r.measure("abcde", 10, 0.5, {"family": "X", "bold": False}) == 25.0  # st ignored when off


def test_renderer_opt_in_uses_metrics(monkeypatch):
    synth = _synthetic()
    monkeypatch.setattr(fmmod, "get_font_metrics", lambda fam, bold: synth)
    r = Renderer({}, ".", real_metrics=True)
    st = {"family": "X", "bold": False}
    assert r.measure("ab", 10, 0.5, st) == 15.0           # real advances, not 2*10*0.5
    assert r.measure("ab", 10, 0.5, None) == 10.0         # no style → estimate even when on


def test_renderer_opt_in_falls_back_when_unresolved(monkeypatch):
    monkeypatch.setattr(fmmod, "get_font_metrics", lambda fam, bold: None)
    r = Renderer({}, ".", real_metrics=True)
    assert r.measure("abcde", 10, 0.5, {"family": "X", "bold": False}) == 25.0


# --------------------------------------------------------------------------- #
# Real fontTools path (only where the `metrics` group is installed)           #
# --------------------------------------------------------------------------- #

def test_real_font_metrics_when_available():
    pytest.importorskip("fontTools", reason="metrics group (fontTools) not installed")
    fmmod.clear_cache()
    fm = get_font_metrics("DejaVu Sans", False)
    if fm is None:
        pytest.skip("fontconfig could not resolve a concrete font file")
    # proportional font: narrow glyphs really are narrower than wide ones
    assert fm.width("iiii", 12) < fm.width("MMMM", 12)
    w = fm_measure("Av", "DejaVu Sans", 12, False)
    assert isinstance(w, float) and w > 0
