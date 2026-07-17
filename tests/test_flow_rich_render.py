#!/usr/bin/env python3
"""
test_flow_rich_render.py — regression for the rich flow-rendering capabilities
added so a single FrameForge model renders professional "spec cards" through the
default SVG/PDF proxy (was: the proxy dropped these, so a bespoke ReportLab
script out-rendered the model — frameforge-north-star).

The proxy `_render_flow` now:
  * paints `block`/`keep_together` container fill + border + padding (was a no-op)
  * honours per-span styles in `emit_para` (inline bold/colour survives the flow
    line-breaker instead of flattening to one style)
  * wraps table cells to their column width (was single-line clipped) and honours
    per-column `width`
  * makes `keep_together` atomic (measures fit; still paints when it must split)

Renderer-only import (the `frameforge` package must win) — evict a models-module
shadow first, per test_flow_figure_render.py.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # the models module
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling import render_fixtures as R  # noqa: E402


def _render(tmp_path, story, name="rich"):
    doc = {"dsl": "FrameForge", "version": "2.2.0", "profile": "report",
           "title": name, "pages": [{"mode": "flow", "id": "p", "story": story}]}
    src = tmp_path / f"{name}.fg.yaml"
    import yaml
    src.write_text(yaml.safe_dump(doc), encoding="utf-8")
    rc = R.main([str(src), "--out", str(tmp_path / "out"), "-q"])
    assert rc == 0
    return (tmp_path / "out" / R.stem_of(str(src)) / "p001.svg").read_text(encoding="utf-8")


def _rect_heights(svg):
    # \sheight — the real geometry attr, not `stroke-width`-style hyphenated ones
    return [float(h) for h in re.findall(r'<rect[^>]*\sheight="([\d.]+)"', svg)]


# --- 1. block/keep_together background + border + padding --------------------- #
def test_block_paints_fill_border_and_insets_children(tmp_path):
    svg = _render(tmp_path, [
        {"type": "block", "fill": "#654321",
         "stroke": "#abccde", "stroke_style": {"stroke_width": 1.0},
         "padding": [10, 12],
         "children": [{"type": "paragraph", "text": "inside the padded block"}]},
    ])
    # a background rect carries the block fill, and the border stroke is present
    assert re.search(r'<rect[^>]*fill="#654321"', svg), "block background not painted"
    assert "#abccde" in svg, "block border stroke not painted"
    # the child text still renders
    assert "inside the padded block" in svg
    # the child is inset by the left padding: its x is greater than the bare column x
    bare = _render(tmp_path, [{"type": "paragraph", "text": "inside the padded block"}],
                   name="bare")
    child_x = float(re.search(r'<text x="([\d.]+)"[^>]*>inside the padded block', svg).group(1))
    bare_x = float(re.search(r'<text x="([\d.]+)"[^>]*>inside the padded block', bare).group(1))
    assert child_x > bare_x + 5, "padding did not inset the child"


def test_keep_together_container_still_paints_background(tmp_path):
    svg = _render(tmp_path, [
        {"type": "keep_together", "children": [
            {"type": "block", "fill": "#0b0b0b", "padding": [6, 8],
             "children": [{"type": "paragraph", "text": "atomic card body"}]},
        ]},
    ])
    assert re.search(r'<rect[^>]*fill="#0b0b0b"', svg)
    assert "atomic card body" in svg


# --- 2. per-span inline styles survive the flow line-breaker ------------------ #
def test_paragraph_span_colour_survives_flow_layout(tmp_path):
    svg = _render(tmp_path, [
        {"type": "paragraph", "spans": [
            {"text": "COLOUREDRUN", "style": {"color": "#0aa0aa", "font_weight": 700}},
            " and then a long tail of plain body words that keeps flowing across the "
            "column so the line-breaker has real work to do here indeed yes.",
        ]},
    ])
    # the coloured run is emitted as its own styled tspan, not flattened away
    assert "COLOUREDRUN" in svg
    assert "#0aa0aa" in svg, "per-span colour was flattened"
    assert "<tspan" in svg


# --- 3. table cells wrap to the column (no single-line clip) ------------------ #
def test_table_cell_wraps_and_row_grows(tmp_path):
    long = "word " * 160          # long enough to wrap to ≥3 lines on any canvas
    svg = _render(tmp_path, [
        {"type": "table",
         "columns": [{"label": "K", "width": 60}, "V"],
         "header": ["K", "V"],
         "rows": [["k1", long.strip()]],
         "style": {"grid_color": "#dddddd", "cell_size": 9}},
    ])
    # a wrapping cell makes a row far taller than a single 9pt line (~19px)
    assert max(_rect_heights(svg), default=0) > 35, "table cell did not wrap"


def test_table_honours_explicit_column_width(tmp_path):
    svg = _render(tmp_path, [
        {"type": "table",
         "columns": [{"label": "K", "width": 60}, "V"],
         "header": ["K", "V"],
         "rows": [["k", "v"]],
         "style": {"grid_color": "#dddddd"}},
    ])
    widths = sorted(float(w) for w in re.findall(r'<rect[^>]*\swidth="([\d.]+)"', svg))
    # two distinct column widths (the 60px K column is much narrower than V)
    assert widths[0] < widths[-1] * 0.6, "explicit column width ignored (equal columns)"
