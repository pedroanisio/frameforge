#!/usr/bin/env python3
"""
test_pattern_render.py — Pattern paints (hatch/cross_hatch/dots/grid) must emit
real SVG <pattern> defs, not silently degrade to a flat colour.

The SDK builds ``{"kind": "pattern", "pattern": ..., "angle"/"spacing"/
"stroke"/"background"}`` paints (framegraph/sdk/paint.py) and the model declares
them (models/framegraph.py Pattern). The renderer routes them to
``SvgPainter.pattern`` which registers a ``<pattern>`` tile in <defs> and
returns a ``url(#...)`` fill reference.

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
sys.path.insert(0, ROOT)

from tooling.render_fixtures import Renderer  # noqa: E402


def _render_rect_with_fill(fill):
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [200, 120]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "rect", "box": [10, 10, 100, 60], "fill": fill}]}]}]}
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


def test_hatch_emits_pattern_def_and_url_fill():
    svg = _render_rect_with_fill({"kind": "pattern", "pattern": "hatch",
                                  "stroke": "#ff0000", "background": "#00ff00",
                                  "angle": 45, "spacing": 6})
    m = re.search(r'fill="url\(#(pat\d+)\)"', svg)
    assert m, f"rect fill is not a pattern url: {svg[:400]}"
    pid = m.group(1)
    assert f'<pattern id="{pid}"' in svg
    assert 'patternUnits="userSpaceOnUse"' in svg
    # tile honours the model fields: spacing sizes the tile, angle rotates it
    assert 'width="6" height="6"' in svg
    assert 'patternTransform="rotate(45)"' in svg
    # stroke colour draws the hatch line; background fills the tile
    assert 'stroke="#ff0000"' in svg
    assert 'fill="#00ff00"' in svg


def test_hatch_is_no_longer_flattened_to_background_colour():
    svg = _render_rect_with_fill({"kind": "pattern", "pattern": "hatch",
                                  "stroke": "#ff0000", "background": "#00ff00"})
    assert '<rect x="10" y="10" width="100" height="60" fill="#00ff00"' not in svg


def test_cross_hatch_emits_two_line_directions():
    svg = _render_rect_with_fill({"kind": "pattern", "pattern": "cross_hatch",
                                  "stroke": "#333333", "spacing": 8})
    pat = re.search(r"<pattern .*?</pattern>", svg)
    assert pat, "no <pattern> def emitted"
    assert pat.group(0).count("<line") == 2


def test_dots_emits_circle_tile():
    svg = _render_rect_with_fill({"kind": "pattern", "pattern": "dots",
                                  "stroke": "#112233", "spacing": 10})
    pat = re.search(r"<pattern .*?</pattern>", svg)
    assert pat, "no <pattern> def emitted"
    assert "<circle" in pat.group(0)
    assert 'fill="#112233"' in pat.group(0)


def test_grid_emits_unrotated_lines():
    svg = _render_rect_with_fill({"kind": "pattern", "pattern": "grid",
                                  "stroke": "#444444", "spacing": 12})
    pat = re.search(r"<pattern .*?</pattern>", svg)
    assert pat, "no <pattern> def emitted"
    assert pat.group(0).count("<line") == 2
    assert "patternTransform" not in pat.group(0)


def test_pattern_defaults_are_renderable():
    """A bare pattern paint (no optional fields) still produces a visible tile."""
    svg = _render_rect_with_fill({"kind": "pattern", "pattern": "hatch"})
    assert "<pattern" in svg
    assert 'fill="url(#' in svg


def test_pattern_colour_tokens_resolve():
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "defs": {"tokens": {"colors": {"ink": "#101820", "paper": "#fffff0"}}},
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [200, 120]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "rect", "box": [0, 0, 50, 50],
                           "fill": {"kind": "pattern", "pattern": "grid",
                                    "stroke": "ink", "background": "paper"}}]}]}]}
    svg = Renderer(doc, ".").render_page(doc["pages"][0])[0]
    assert 'stroke="#101820"' in svg
    assert 'fill="#fffff0"' in svg


if __name__ == "__main__":
    test_hatch_emits_pattern_def_and_url_fill()
    print("OK")
