#!/usr/bin/env python3
"""Flow tables use content-proportional, wrapping ``p{}`` columns.

The old emitter used non-wrapping ``l`` columns (and a whole-table
``\\resizebox``), so a cell of long text ran into the margin. Columns are now
``>{\\raggedright\\arraybackslash}p{f\\textwidth}`` with ``f`` tracking the
column's longest cell.

Renderer-only import — evict a models-module shadow first, per test_render_cli.py.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402


def _doc(header, rows):
    return {
        "dsl": "FrameGraph", "version": "2.2.0", "profile": "book", "title": "t",
        "pages": [{"mode": "flow", "id": "p", "story": [
            {"type": "table", "header": header, "rows": rows}]}],
    }


def _fractions(tex):
    return [float(x) for x in re.findall(r"p\{([0-9.]+)\\textwidth\}", tex)]


def test_columns_are_wrapping_p_not_l():
    tex = transpile(_doc(["A", "B"], [["x", "y"]]))
    assert ">{\\raggedright\\arraybackslash}p{" in tex
    assert "\\begin{tabular}{l" not in tex          # no bare left columns
    assert "\\resizebox" not in tex                  # no whole-table shrink


def test_wide_column_gets_more_width():
    tex = transpile(_doc(
        ["Key", "Description"],
        [["a", "a thoroughly long-winded explanatory cell that must wrap nicely"],
         ["b", "another long descriptive sentence that also needs room to breathe"]]))
    fr = _fractions(tex)
    assert len(fr) == 2
    assert fr[1] > fr[0] * 1.5                       # description column dominates


def test_total_width_leaves_room_for_padding():
    tex = transpile(_doc(["a", "b", "c"], [["1", "2", "3"]]))
    fr = _fractions(tex)
    assert len(fr) == 3
    assert sum(fr) <= 0.95                            # never claims the full measure
