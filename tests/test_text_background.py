#!/usr/bin/env python3
"""test_text_background.py — Style.background* paints behind absolute text.

Regression for a silent style loss found while authoring the declutter
example (2026-07-22): every CLOSED SHAPE resolves ``style.background`` /
``background_color`` / ``background_image`` through the ``_shape_fill``
fallback chain, and the flow renderer paints block backgrounds — but the
absolute TEXT branch never consulted the chain, so a model-declared,
schema-documented background on a text object rendered in ZERO bytes of
SVG output (while the html backend mapped it to CSS — backend drift).

The contract pinned here:

  * ``style.background`` (colour), ``style.background_color``, and a
    gradient ``style.background`` on a text object paint a rect exactly
    covering the text box, BEHIND the glyphs.
  * ``style.fill`` on text is NOT a box background — in SVG semantics,
    text fill is glyph paint; the background chain must not swallow it.
  * ABSENCE IS IDENTITY — text without background keys emits byte-identical
    markup to before the fix (no extra rect, golden locks cannot move).

Runs under pytest or standalone
(``uv run python tests/test_text_background.py``).
"""
from __future__ import annotations

import os
import re
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling"), os.path.join(ROOT, "src"), ROOT]

from render_fixtures import Renderer  # noqa: E402


def _doc(text_obj):
    return {"dsl": "FrameForge", "version": "2.3.0", "title": "t",
            "pages": [{"mode": "page", "id": "p1",
                       "canvas": {"size": [400, 300], "units": "px"},
                       "layers": [{"id": "l1", "objects": [text_obj]}]}]}


def _svg(text_obj):
    doc = _doc(text_obj)
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


BOX = [20, 30, 160, 24]


def _text(style):
    return {"id": "chip", "type": "text", "box": list(BOX), "text": "Intake",
            "style": {"font_size": 11, "color": "#1c2733", **style}}


# ── the background paints, behind the glyphs, exactly on the box ─────────


def test_background_colour_paints_a_rect_behind_the_glyphs():
    svg = _svg(_text({"background": "#eef3f9"}))
    assert "#eef3f9" in svg                          # the fill exists at all
    rect_at = svg.index("#eef3f9")
    text_at = svg.index("Intake")
    assert rect_at < text_at                         # painted BEHIND the glyphs
    # the rect covers exactly the authored box
    m = re.search(r'<rect x="20" y="30" width="160" height="24"[^>]*fill="#eef3f9"', svg)
    assert m, f"no box-covering background rect in: {svg[:400]}"


def test_background_color_key_is_honoured_too():
    svg = _svg(_text({"background_color": "#ffe9dc"}))
    assert "#ffe9dc" in svg


def test_background_gradient_allocates_defs_and_paints():
    grad = {"kind": "linear", "angle": 90,
            "stops": [{"color": "#eef3f9", "position": "0%"},
                      {"color": "#c5d2e0", "position": "100%"}]}
    svg = _svg(_text({"background": grad}))
    assert "linearGradient" in svg
    assert re.search(r'fill="url\(#[^"]+\)"', svg)


# ── semantics guards ─────────────────────────────────────────────────────


def test_style_fill_on_text_is_not_a_box_background():
    # SVG text `fill` is glyph paint; the background chain must not turn it
    # into a rect behind the text.
    svg = _svg(_text({"fill": "#ff0000"}))
    assert not re.search(r'<rect[^>]*fill="#ff0000"', svg)


def test_background_clip_text_is_glyph_paint_not_a_box():
    # The CSS glyph-clipped-gradient idiom (`background_clip: "text"`) asks
    # for the background INSIDE the glyphs — a box rect behind the text would
    # deface the design (and moved the chroma-styling-showcase golden). The
    # box-background paint must skip it; proper glyph-clipped gradient fill
    # is a separate engine feature.
    grad = {"kind": "linear", "angle": 90,
            "stops": [{"color": "#ff0080", "position": "0%"},
                      {"color": "#8000ff", "position": "100%"}]}
    svg = _svg(_text({"background_image": grad, "background_clip": "text"}))
    rects = re.findall(r"<rect[^>]*>", svg)
    assert rects == ['<rect width="100%" height="100%" fill="white"/>']


def test_absence_is_identity_no_extra_rect():
    plain = _svg(_text({}))
    # the only rect is the page-canvas wash the document wrapper always emits
    rects = re.findall(r"<rect[^>]*>", plain)
    assert rects == ['<rect width="100%" height="100%" fill="white"/>']


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
