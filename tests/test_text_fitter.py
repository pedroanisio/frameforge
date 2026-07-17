#!/usr/bin/env python3
"""Unit tests for the TextFitter domain service (measure / wrap / ellipsize).

Covers both modes directly on the service: the character-count estimate (no
provider) and real glyph advances (an injected fake metrics provider), so the
extracted logic is verified independently of the Renderer that delegates to it.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.text_fitter import TextFitter  # noqa: E402


class _FakeMetrics:
    """Fixed-advance metrics: every glyph is 6px wide at size 10 (0.6/size unit)."""

    def width(self, s, size):
        return len(s) * size * 0.6


def _provider(_family, _bold):
    return _FakeMetrics()


# ---- estimate mode (no provider) ----
def test_measure_estimate():
    fit = TextFitter(None)
    assert fit.measure("abcde", 10, 0.5) == 25.0          # len * size * avg
    # a style is ignored when no provider is injected
    assert fit.measure("abcde", 10, 0.5, {"family": "X"}) == 25.0


def test_wrap_estimate_breaks_long_token():
    fit = TextFitter(None)
    assert fit.wrap_words("a a a a a", 100, 10, 0.5) == ["a a a a a"]
    # maxc = 100/(10*0.5) = 20; a 30-char token hard-breaks
    out = fit.wrap_words("x" * 30, 100, 10, 0.5)
    assert "".join(out) == "x" * 30 and all(len(line) <= 20 for line in out)


def test_ellipsize_estimate():
    fit = TextFitter(None)
    assert fit.ellipsize("short", 100, 10, 0.5) == "short"   # fits
    assert fit.ellipsize("abcdefgh", 30, 10, 0.5).endswith("…")  # maxc=6 -> trimmed


# ---- real-metrics mode (injected provider) ----
def test_measure_real_metrics():
    fit = TextFitter(_provider)
    st = {"family": "X", "bold": False}
    assert fit.measure("ab", 10, 0.5, st) == 12.0           # real: 2 * 10 * 0.6
    assert fit.measure("ab", 10, 0.5, None) == 10.0         # no style -> estimate even when on


def test_wrap_real_metrics():
    fit = TextFitter(_provider)
    st = {"family": "X"}
    # width budget 36px at size 10 (6px/glyph) -> 6 glyphs incl. spaces per line
    out = fit.wrap_words("aa bb cc dd", 36, 10, 0.5, st)
    assert out == ["aa bb", "cc dd"]
