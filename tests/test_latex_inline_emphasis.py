#!/usr/bin/env python3
"""A styled inline ``Span`` must carry its bold / italic emphasis into LaTeX.

Previously ``_inline_text`` escaped a ``Span``'s text and dropped its ``style``,
so emphasis silently vanished from flow documents. The backend now resolves the
span style (token name or inline dict) and emits ``\\textbf`` / ``\\textit``.

Renderer-only import (the ``framegraph`` package must win) — evict a
models-module shadow first, per test_render_cli.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402


def _doc(spans, text_styles=None):
    return {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "profile": "book",
        "title": "emphasis",
        "defs": {"tokens": {"text_styles": text_styles or {}}},
        "pages": [{"mode": "flow", "id": "p",
                   "story": [{"type": "paragraph", "spans": spans}]}],
    }


def test_inline_bold_and_italic_spans_render_emphasis():
    tex = transpile(_doc([
        "plain ",
        {"text": "bold", "style": {"font_weight": 700}},
        " and ",
        {"text": "slanted", "style": {"font_style": "italic"}},
    ]))
    assert "\\textbf{bold}" in tex
    assert "\\textit{slanted}" in tex


def test_named_strong_style_resolves_to_bold():
    tex = transpile(_doc(
        [{"text": "loud", "style": "strong"}],
        text_styles={"strong": {"font_weight": 800}},
    ))
    assert "\\textbf{loud}" in tex


def test_plain_and_unemphasised_spans_are_not_wrapped():
    tex = transpile(_doc([
        "ordinary ",
        {"text": "tinted", "style": {"color": "#2563EB"}},   # colour ≠ emphasis
    ]))
    assert "\\textbf{" not in tex
    assert "\\textit{" not in tex
    assert "tinted" in tex


def test_bold_italic_span_nests_both():
    tex = transpile(_doc(
        [{"text": "both", "style": {"font_weight": 700, "font_style": "italic"}}]))
    assert "\\textbf{\\textit{both}}" in tex
