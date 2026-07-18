#!/usr/bin/env python3
"""Layout arithmetic — pixel-perfect BHAG Pass 2 Track D1 (ledger LAY-1..7).

Spec anchors (docs/spec/frameforge-v2-spec.md):
- §3.4: '%' on a child box dimension resolves against the CONTAINER CONTENT-BOX
  on the same axis; 'fr' is a free-space share, valid only inside a layout
  container (row/column fill weight where 1fr ≡ fill grow:1; grid track sizing).
- §3.6 grid: "column width = max child width per column, row height = max child
  height per row" (content-derived tracks, not uniform splits).
- §3.6g sizing: free_main split across fill children by grow, CLAMPED to
  min/max.
Composition invariant: adjacent children derive their shared edge from ONE
cumulative position — positions are prefix sums, so widths sum exactly.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.layout_engine import LayoutEngine  # noqa: E402

E = LayoutEngine()


def _rects(n, **common):
    return [{"type": "rect", "box": [0, 0, 10, 10], **common} for _ in range(n)]


# --------------------------------------------------------------------------- #
#  LAY-1 — percent / fr child dimensions resolve, never collapse to 0          #
# --------------------------------------------------------------------------- #
def test_percent_width_resolves_against_container_content_box():
    children = [{"type": "rect", "box": [0, 0, "50%", 40]},
                {"type": "rect", "box": [0, 0, "25%", 40]}]
    boxes = E.arrange(400, 100, children, {"kind": "row"})
    assert [b[2] for b in boxes] == [200.0, 100.0]
    assert boxes[1][0] == 200.0                      # packed after the first


def test_percent_height_resolves_in_a_column():
    children = [{"type": "rect", "box": [0, 0, 40, "50%"]}]
    boxes = E.arrange(100, 300, children, {"kind": "column"})
    assert boxes[0][3] == 150.0


def test_fr_width_is_a_free_space_share():
    # spec §3.4: 1fr ≡ fill grow:1 on the row main axis
    children = [{"type": "rect", "box": [0, 0, 100, 40]},
                {"type": "rect", "box": [0, 0, "1fr", 40]},
                {"type": "rect", "box": [0, 0, "3fr", 40]}]
    boxes = E.arrange(500, 100, children, {"kind": "row"})
    assert [b[2] for b in boxes] == [100.0, 100.0, 300.0]


def test_percent_respects_container_padding():
    # content box = 400 - 2*20 = 360
    children = [{"type": "rect", "box": [0, 0, "50%", 40]}]
    boxes = E.arrange(400, 100, children, {"kind": "row", "padding": 20})
    assert boxes[0][2] == 180.0


# --------------------------------------------------------------------------- #
#  LAY-5 — min/max clamps on the fill split                                    #
# --------------------------------------------------------------------------- #
def test_fill_split_clamps_to_max_and_redistributes():
    children = [
        {"type": "rect", "box": [0, 0, 0, 40], "sizing": {"width": "fill", "max": 200}},
        {"type": "rect", "box": [0, 0, 0, 40], "sizing": {"width": "fill"}},
    ]
    boxes = E.arrange(1000, 100, children, {"kind": "row"})
    assert boxes[0][2] == 200.0                      # clamped
    assert boxes[1][2] == 800.0                      # freed space redistributed


def test_fill_split_clamps_to_min():
    children = [
        {"type": "rect", "box": [0, 0, 0, 40], "sizing": {"width": "fill", "grow": 1, "min": 300}},
        {"type": "rect", "box": [0, 0, 0, 40], "sizing": {"width": "fill", "grow": 9}},
    ]
    boxes = E.arrange(1000, 100, children, {"kind": "row"})
    assert boxes[0][2] == 300.0                      # raised to min (share was 100)
    assert boxes[1][2] == 700.0


# --------------------------------------------------------------------------- #
#  LAY-4 — grid tracks are content-derived (spec §3.6), edges single-derived   #
# --------------------------------------------------------------------------- #
def test_grid_column_width_is_max_child_width_per_column():
    children = [{"type": "rect", "box": [0, 0, w, 50]} for w in (100, 300, 100, 300)]
    boxes = E.arrange(1000, 400, children, {"kind": "grid", "columns": 2, "gap": 10})
    # col 0 track = max(100, 100) = 100; col 1 track = max(300, 300) = 300
    assert boxes[0][0] == 0.0 and boxes[1][0] == 110.0     # 100 + gap
    assert boxes[2][0] == 0.0 and boxes[3][0] == 110.0     # SAME derivation both rows


def test_grid_row_height_is_max_child_height_per_row():
    children = [{"type": "rect", "box": [0, 0, 50, h]} for h in (30, 80, 20, 20)]
    boxes = E.arrange(400, 1000, children, {"kind": "grid", "columns": 2, "gap": 10})
    assert boxes[2][1] == 90.0 and boxes[3][1] == 90.0     # row0 track = max(30,80)


def test_grid_positions_are_prefix_sums_no_remainder_drop():
    widths = (70, 110, 45)
    children = [{"type": "rect", "box": [0, 0, w, 20]} for w in widths]
    boxes = E.arrange(1000, 100, children, {"kind": "grid", "columns": 3, "gap": 7})
    assert boxes[1][0] == 70 + 7
    assert boxes[2][0] == 70 + 7 + 110 + 7


# --------------------------------------------------------------------------- #
#  LAY-2 / LAY-3 — flow table columns honour %/fr and keep fixed px fixed      #
# --------------------------------------------------------------------------- #
def _table_cell_geometry(columns, usable_hint=600):
    """Render a one-table flow doc; return the first body row's rect x/width."""
    from frameforge.sdk import parse, render_page_svgs

    doc = {
        "dsl": "FrameForge", "version": "2.5.0",
        "defs": {"masters": {"m": {
            "canvas": {"size": [usable_hint, 400], "units": "px"},
            "margin": [0, 0, 0, 0],
            "regions": [{"id": "r", "box": [0, 0, usable_hint, 400]}],
        }}},
        "pages": [{"mode": "flow", "id": "s", "master": "m", "story": [
            {"type": "table", "columns": columns,
             "rows": [["a", "b", "c"]]},
        ]}],
    }
    svg = render_page_svgs(parse(__import__("json").dumps(doc), forgiving=False))[0]
    rects = re.findall(r'<rect x="([0-9.]+)" y="[0-9.]+" width="([0-9.]+)"', svg)
    cells = [(float(x), float(w)) for x, w in rects]
    return sorted(set(cells))[:3] if cells else []


def test_flow_table_fixed_px_column_stays_fixed():
    cells = _table_cell_geometry(
        [{"label": "A", "width": 100}, {"label": "B"}, {"label": "C"}])
    widths = sorted(w for _, w in cells)
    assert 100.0 in widths, f"authored 100px column must render 100px, got {widths}"


def test_flow_table_percent_column_resolves():
    cells = _table_cell_geometry(
        [{"label": "A", "width": "50%"}, {"label": "B"}, {"label": "C"}])
    widths = [w for _, w in cells]
    assert any(abs(w - 300.0) < 0.51 for w in widths), (
        f"50% of the 600px column must be ~300px, got {widths}")


# --------------------------------------------------------------------------- #
#  LAY-7 — page-break admission uses the line BOX (size*lh), not bare size     #
# --------------------------------------------------------------------------- #
def test_last_line_cannot_overhang_the_region_bottom():
    from frameforge.sdk import parse, render_page_svgs

    doc = {
        "dsl": "FrameForge", "version": "2.5.0",
        "defs": {
            "tokens": {"styles": {"body": {
                "font_size": 20, "line_height": 2.0, "font_family": "sans"}}},
            "masters": {"m": {
                "canvas": {"size": [400, 300], "units": "px"},
                "margin": [0, 0, 0, 0],
                "regions": [{"id": "r", "box": [0, 0, 400, 100]}],
            }},
        },
        "pages": [{"mode": "flow", "id": "s", "master": "m", "story": [
            {"type": "paragraph", "style": "body",
             # three short lines via preserved breaks — line box = 40px each,
             # region height 100: line 3 fits by bare size (80+20<=100) but its
             # box (80+40=120) overflows — it must move to page 2
             "text": "aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa "
                     "aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa"},
        ]}],
    }
    svgs = render_page_svgs(parse(__import__("json").dumps(doc), forgiving=False))
    texts_p1 = re.findall(r'<text [^>]*y="([0-9.]+)"', svgs[0])
    for y in texts_p1:
        assert float(y) + 40 * 0.12 <= 100 + 1e-6, (
            f"a line box may not overhang the region bottom (line at y={y})")
    assert len(svgs) >= 2, "the overflowing line must paginate to page 2"
