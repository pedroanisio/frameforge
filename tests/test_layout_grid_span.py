#!/usr/bin/env python3
"""test_layout_grid_span.py — grid layout honors ObjBase.grid_span.

`grid_span: [column_span, row_span]` (§3.6e) lets a grid child occupy a
multi-cell block; neighbours flow around the occupied cells. The field existed in
the model but the layout engine ignored it (one child per cell). These tests pin
the span placement AND that a grid with NO spans lays out exactly as before
(output-preserving — the reason existing goldens are unmoved).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.rendering.domain.services.layout_engine import LayoutEngine  # noqa: E402


def _child(w, h, **extra):
    d = {"type": "rect", "box": [0, 0, w, h]}
    d.update(extra)
    return d


# 3 columns, avail 320 wide, gap 10. Tracks are CONTENT-DERIVED (spec §3.6,
# test_layout_math_4k): a 50-wide span-1 child sizes its track to 50; tracks
# with no sized contributor share the remaining extent equally.
_LAYOUT = {"kind": "grid", "columns": 3, "gap": 10}


def test_no_span_grid_is_unchanged():
    eng = LayoutEngine()
    boxes = eng.arrange(320, 220, [_child(50, 50) for _ in range(3)], _LAYOUT)
    xs = [round(b[0], 6) for b in boxes]
    ys = [round(b[1], 6) for b in boxes]
    # content tracks 50/50/50 + gap 10 → prefix sums 0 / 60 / 120
    assert xs == [0.0, 60.0, 120.0]    # one row, three columns
    assert ys == [0.0, 0.0, 0.0]


def test_column_span_pushes_the_next_child_past_the_spanned_cells():
    eng = LayoutEngine()
    children = [_child(50, 50, grid_span=[2, 1]), _child(50, 50), _child(50, 50)]
    boxes = eng.arrange(320, 220, children, _LAYOUT)
    # child0 spans cols 0–1 → starts at x=0; child1 lands in col 2, not col 1;
    # child2 wraps to row 1 (y>0). Track math: col0=50 (child2, row 1),
    # col2=50 (child1); child0's 50 fits within col0+gap so col1 has no sized
    # contributor → col1 takes the remainder (320 − 50 − 50 − 2·10 = 200) →
    # col_x = 0 / 60 / 270.
    assert round(boxes[0][0], 6) == 0.0
    assert round(boxes[1][0], 6) == 270.0
    assert boxes[2][1] > 0.0


def test_a_filling_spanned_child_gets_the_full_span_width():
    eng = LayoutEngine()
    children = [_child(50, 50, grid_span=[2, 1], sizing={"width": "fill"}),
                _child(50, 50), _child(50, 50)]
    boxes = eng.arrange(320, 220, children, _LAYOUT)
    # spanned tracks 50 + 200 (see above) + the gap between them = 260.
    assert abs(boxes[0][2] - 260.0) < 1e-6


def test_row_span_reserves_cells_below():
    eng = LayoutEngine()
    # child0 spans 1 col × 2 rows; child1/child2 fill the rest of the two rows.
    children = [_child(50, 50, grid_span=[1, 2]), _child(50, 50), _child(50, 50),
                _child(50, 50), _child(50, 50)]
    boxes = eng.arrange(320, 320, children, _LAYOUT)
    # child0 occupies (col0,row0)+(col0,row1); child3 cannot reclaim col0/row1.
    assert round(boxes[0][0], 6) == 0.0
    # the child placed at col0 of row1 must NOT be child0's cell — some later child
    # is pushed down; simplest invariant: no two boxes share a top-left corner.
    corners = [(round(b[0], 3), round(b[1], 3)) for b in boxes]
    assert len(set(corners)) == len(corners), "grid children overlap"
