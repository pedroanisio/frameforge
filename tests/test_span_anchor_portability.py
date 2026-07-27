#!/usr/bin/env python3
"""test_span_anchor_portability.py — multi-run spans must not rely on chunk anchoring.

A centred (or right-aligned) `text.spans` line used to emit one
``text-anchor="middle"`` element whose first tspan carried the anchor x.
That is spec-valid SVG 1.1 (the anchor applies to the whole text chunk), and
Chromium/Firefox render it correctly — but several real consumers
(librsvg-family previews, some document viewers) apply the anchor per tspan,
centring every run independently so the runs overlap. The raster QA loop
(Chromium) can never catch that.

The contract these tests pin: when a single-line spans text has more than one
run and a non-start alignment, the renderer does the anchor arithmetic itself
and emits a start-anchored line at the measured start x — identical geometry
in every viewer, buggy or not.  Single-run spans keep the middle anchor
(byte-stability for the common case).

Runs under pytest or standalone
(``uv run python tests/test_span_anchor_portability.py``).
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling"), os.path.join(ROOT, "src"), ROOT]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from render_fixtures import Renderer                    # noqa: E402

RED = {"text": "RED ", "style": {"color": "#CC2200", "font_size": 20,
                                 "font_family": "Inter"}}
BLUE = {"text": "BLUE", "style": {"color": "#0033AA", "font_size": 20,
                                  "font_family": "Inter"}}


def _svg(text_obj):
    doc = {"dsl": "FrameForge", "version": "2.3.0", "title": "t",
           "pages": [{"mode": "page", "id": "p1",
                      "canvas": {"size": [400, 300], "units": "px"},
                      "layers": [{"id": "l1", "objects": [text_obj]}]}]}
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


def _runs_text(svg):
    """The <text> element that carries the RED/BLUE runs."""
    for m in re.finditer(r"<text[^>]*>.*?</text>", svg, re.S):
        if "RED" in m.group(0):
            return m.group(0)
    raise AssertionError("runs text element not found in SVG:\n" + svg)


def test_centred_multi_run_line_is_start_anchored():
    el = _runs_text(_svg({"id": "t", "type": "text", "box": [20, 20, 360, 60],
                          "spans": [RED, BLUE],
                          "style": {"font_size": 20, "align": "center"}}))
    assert 'text-anchor="middle"' not in el
    assert 'text-anchor="start"' in el
    # the anchor x moved from the box centre (200) to the measured line start
    x = float(re.search(r'<tspan x="([-\d.]+)"', el).group(1))
    assert x < 200.0


def test_right_aligned_multi_run_line_is_start_anchored():
    el = _runs_text(_svg({"id": "t", "type": "text", "box": [20, 20, 360, 60],
                          "spans": [RED, BLUE],
                          "style": {"font_size": 20, "align": "right"}}))
    assert 'text-anchor="end"' not in el
    assert 'text-anchor="start"' in el
    x = float(re.search(r'<tspan x="([-\d.]+)"', el).group(1))
    assert x < 380.0                                    # box right edge


def test_single_run_span_keeps_middle_anchor():
    el = _runs_text(_svg({"id": "t", "type": "text", "box": [20, 20, 360, 60],
                          "spans": [RED],
                          "style": {"font_size": 20, "align": "center"}}))
    assert 'text-anchor="middle"' in el                 # unchanged common case


if __name__ == "__main__":
    import pytest as _pytest
    raise SystemExit(_pytest.main([__file__, "-q"]))
