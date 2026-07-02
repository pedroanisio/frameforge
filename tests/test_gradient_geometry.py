#!/usr/bin/env python3
"""
test_gradient_geometry.py — the SVG backend must honour Gradient geometry:

* ``angle``     -> linear x1/y1/x2/y2 (CSS convention: 0 = up, 90 = right,
                   180 = down; the gradient line runs through the box centre),
* ``at``        -> radial cx/cy + fx/fy (keywords, "x% y%", or a point),
* ``repeating`` -> spreadMethod="repeat",
* ``conic``     -> still a radial fallback, but with a STRUCTURED render
                   warning (renderer.diagnostics), never silence.

Angle-less gradients keep emitting no geometry attributes so their output is
byte-identical to the previous renderer (golden protection for documents that
never declared geometry).

Renderer-only (no models import): evict a models-module shadow first — mirror of
the guard in test_element_render.py.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # a non-package (the models module)
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling.render_fixtures import Renderer  # noqa: E402

_STOPS = [{"color": "#000000", "position": "0%"}, {"color": "#ffffff", "position": "100%"}]


def _render(fill):
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [200, 120]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "rect", "box": [0, 0, 100, 60], "fill": fill}]}]}]}
    r = Renderer(doc, ".")
    return r.render_page(doc["pages"][0])[0], r


def _grad_tag(svg, kind="linearGradient"):
    m = re.search(rf"<{kind}[^>]*>", svg)
    assert m, f"no <{kind}> in {svg[:400]}"
    return m.group(0)


def test_linear_without_angle_keeps_legacy_bytes():
    svg, _ = _render({"kind": "linear", "stops": _STOPS})
    assert '<linearGradient id="g1">' in svg  # no geometry attrs: byte-stable


def test_linear_angle_90_runs_left_to_right():
    svg, _ = _render({"kind": "linear", "stops": _STOPS, "angle": 90})
    tag = _grad_tag(svg)
    assert 'x1="0%"' in tag and 'y1="50%"' in tag
    assert 'x2="100%"' in tag and 'y2="50%"' in tag


def test_linear_angle_180deg_runs_top_to_bottom():
    svg, _ = _render({"kind": "linear", "stops": _STOPS, "angle": "180deg"})
    tag = _grad_tag(svg)
    assert 'x1="50%"' in tag and 'y1="0%"' in tag
    assert 'x2="50%"' in tag and 'y2="100%"' in tag


def test_linear_angle_turn_units():
    svg, _ = _render({"kind": "linear", "stops": _STOPS, "angle": "0.25turn"})
    tag = _grad_tag(svg)
    assert 'x1="0%"' in tag and 'x2="100%"' in tag  # 0.25turn == 90deg


def test_repeating_linear_sets_spread_method():
    svg, _ = _render({"kind": "linear", "stops": _STOPS, "angle": 90, "repeating": True})
    assert 'spreadMethod="repeat"' in _grad_tag(svg)


def test_radial_at_keywords_and_percent():
    svg, _ = _render({"kind": "radial", "stops": _STOPS, "at": "top left"})
    tag = _grad_tag(svg, "radialGradient")
    assert 'cx="0%"' in tag and 'cy="0%"' in tag
    assert 'fx="0%"' in tag and 'fy="0%"' in tag

    svg, _ = _render({"kind": "radial", "stops": _STOPS, "at": "25% 75%"})
    tag = _grad_tag(svg, "radialGradient")
    assert 'cx="25%"' in tag and 'cy="75%"' in tag


def test_radial_at_point_fractions():
    svg, _ = _render({"kind": "radial", "stops": _STOPS, "at": [0.5, 0.25]})
    tag = _grad_tag(svg, "radialGradient")
    assert 'cx="50%"' in tag and 'cy="25%"' in tag


def test_radial_without_at_keeps_legacy_bytes():
    svg, _ = _render({"kind": "radial", "stops": _STOPS})
    assert '<radialGradient id="g1">' in svg


def test_conic_fallback_emits_structured_warning():
    svg, r = _render({"kind": "conic", "stops": _STOPS})
    assert "<radialGradient" in svg  # documented approximation
    warns = [w for w in r.diagnostics["warnings"] if w["kind"] == "gradient_conic_fallback"]
    assert warns, f"no structured conic warning: {r.diagnostics['warnings']}"
    assert "radial" in warns[0]["message"]


if __name__ == "__main__":
    test_linear_angle_90_runs_left_to_right()
    print("OK")
