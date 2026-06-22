#!/usr/bin/env python3
"""Regression: LaTeX tables must render structured cell *content*, not dict reprs.

A table `CellValue` may be a scalar, a `Cell` (`{content, style}`), or a rich
`Span` (`{text/spans}`). The flow tabular emitter used to escape the raw value,
so a structured cell leaked its Python dict repr into the PDF
(`{'content': 'Thickness (nm)', 'style': 'th'}`). These tests pin the fix: the
cell text is pulled out the way the SVG painter does it.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402


def _flow(*story):
    return {
        "dsl": "FrameGraph", "version": "2.2.0", "profile": "report",
        "title": "table cells", "lang": "en",
        "pages": [{"mode": "flow", "id": "p", "story": list(story)}],
    }


def test_structured_cells_render_text_not_dict_repr():
    tex = transpile(_flow({
        "type": "table",
        "header": [{"content": "Thickness (nm)", "style": "th"},
                   {"content": "Reflected hue", "style": "th"}],
        "rows": [
            ["plain", {"content": "violet", "style": "cell"}],
            [{"content": "~250", "style": "cellHi"}, {"text": "green"}],
            [42, None],
        ],
    }))
    # the bug: the dict repr leaking into the tabular
    assert "'content'" not in tex
    assert "'style'" not in tex
    # header Cell content, bolded
    assert r"\textbf{Thickness (nm)}" in tex
    assert r"\textbf{Reflected hue}" in tex
    # body cells: scalar, Cell.content, Span.text, numeric, and a None -> blank
    assert "plain" in tex
    assert "violet" in tex
    assert "green" in tex                      # Span {text: ...}
    assert "42" in tex                         # numeric scalar
    assert r"\textasciitilde{}250" in tex      # Cell.content, escaped


def test_b1_chroma_table_renders_cleanly():
    doc = json.load(open(os.path.join(ROOT, "fixtures", "b1",
                                      "chroma-styling-showcase.fg.json"), encoding="utf-8"))
    tex = transpile(doc)
    assert "'content'" not in tex
    assert r"\textbf{Thickness (nm)}" in tex
    assert "peacock barbule" in tex
