#!/usr/bin/env python3
"""
test_no_injected_style_regressions.py — regression gates for the first three
no-injected-style residuals (ADR-0006; GH #60/#61/#62):

  #60  the SVG painter hardcoded the page background (`fill="white"`) and the
       model had no way to author one → `CanvasObject.background` now exists,
       resolves page > master, and reaches the painter. The unauthored default
       stays the byte-identical `white` rect (documented fallback).
  #61  flow-table chrome *geometry* was hardcoded even though the colours were
       style-driven → `grid_width` / `cell_padding` / `header_weight` /
       `cell_line_height` now read from the table `style`, defaulting to the
       previous constants (0.5 / 4.0 / 700 / 1.25) so existing renders are
       byte-stable.
  #62  flow `code` blocks read no style → a document-defined reserved `code`
       style is honored via the same `named()` mechanism as `caption`; the
       monospace/10/#333 trio remains only as the documented fallback.

Renderer-only import (the `frameforge` package must win) — evict a
models-module shadow first, per test_flow_figure_render.py.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # the models module
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import yaml  # noqa: E402

from tooling import render_fixtures as R  # noqa: E402

BG_RECT = re.compile(r'<rect width="100%" height="100%" fill="([^"]+)"/>')


def _render_doc(tmp_path, doc, name="doc", page="p001.svg"):
    src = tmp_path / f"{name}.fg.yaml"
    src.write_text(yaml.safe_dump(doc), encoding="utf-8")
    rc = R.main([str(src), "--out", str(tmp_path / "out"), "-q"])
    assert rc == 0
    return (tmp_path / "out" / R.stem_of(str(src)) / page).read_text(encoding="utf-8")


def _flow_doc(story, defs=None):
    doc = {"dsl": "FrameForge", "version": "2.2.0", "profile": "report",
           "title": "t", "pages": [{"mode": "flow", "id": "p", "story": story}]}
    if defs:
        doc["defs"] = defs
    return doc


# --------------------------------------------------------------------------- #
#  #60 — page background honors CanvasObject.background                       #
# --------------------------------------------------------------------------- #
def test_page_mode_canvas_background_is_honored(tmp_path):
    svg = _render_doc(tmp_path, {
        "dsl": "FrameForge", "version": "2.2.0", "profile": "report", "title": "t",
        "pages": [{"mode": "page", "id": "p",
                   "canvas": {"size": [240, 120], "background": "#123456"},
                   "layers": [{"id": "l", "objects": [
                       {"type": "text", "id": "t1", "box": [10, 10, 100, 20],
                        "content": "hello"}]}]}]})
    m = BG_RECT.search(svg)
    assert m, "page background rect missing"
    assert m.group(1) == "#123456", f"authored canvas background ignored (got {m.group(1)})"
    assert 'fill="white"' not in svg


def test_flow_mode_inherits_master_canvas_background(tmp_path):
    svg = _render_doc(tmp_path, _flow_doc(
        [{"type": "paragraph", "text": "flow over a tinted page"}],
        defs={"masters": {"m": {"canvas": {"size": [400, 300],
                                           "background": "#0e0f10"}}}},
    ) | {"pages": [{"mode": "flow", "id": "p", "master": "m",
                    "story": [{"type": "paragraph", "text": "flow over a tinted page"}]}]})
    m = BG_RECT.search(svg)
    assert m and m.group(1) == "#0e0f10", "master canvas background not inherited by flow pages"


def test_unauthored_background_stays_byte_identical_white(tmp_path):
    # The documented fallback: no authored background → the exact legacy rect,
    # so goldens and downstream byte-diffs are unaffected.
    svg = _render_doc(tmp_path, _flow_doc([{"type": "paragraph", "text": "plain"}]))
    assert '<rect width="100%" height="100%" fill="white"/>' in svg


def test_canvas_background_accepts_token_colors(tmp_path):
    # Colour tokens resolve through the normal token cascade.
    svg = _render_doc(tmp_path, {
        "dsl": "FrameForge", "version": "2.2.0", "profile": "report", "title": "t",
        "defs": {"tokens": {"colors": {"paper": "#fafaf0"}}},
        "pages": [{"mode": "page", "id": "p",
                   "canvas": {"size": [200, 100], "background": "paper"},
                   "layers": []}]})
    m = BG_RECT.search(svg)
    assert m and m.group(1) == "#fafaf0", "canvas background did not resolve colour token"


# --------------------------------------------------------------------------- #
#  #61 — table chrome geometry reads from the table style                     #
# --------------------------------------------------------------------------- #
TABLE = {"type": "table",
         "header": ["Alpha", "Beta"],
         "rows": [["one", "two"], ["three", "four"]]}


def _table_doc(style=None):
    t = dict(TABLE)
    if style:
        t["style"] = style
    return _flow_doc([t])


def test_grid_width_reads_from_table_style(tmp_path):
    svg = _render_doc(tmp_path, _table_doc(
        {"grid_color": "#e5e7eb", "grid_width": 1.5}))
    assert 'stroke-width="1.5"' in svg, "authored grid_width ignored"
    assert 'stroke-width="0.5"' not in svg, "hardcoded 0.5 grid width still injected"


def test_grid_width_default_is_unchanged(tmp_path):
    # Regression pin: colour-only chrome keeps the documented 0.5 fallback.
    svg = _render_doc(tmp_path, _table_doc({"grid_color": "#e5e7eb"}))
    assert 'stroke-width="0.5"' in svg


def test_header_weight_reads_from_table_style(tmp_path):
    # 400 = CSS normal: the painter rightly emits no font-weight at all.
    svg = _render_doc(tmp_path, _table_doc(
        {"header_weight": 400, "cell_size": 9}))
    assert "font-weight" not in svg, "hardcoded header weight 700 still injected"
    # A non-normal weight must flow through to the header cells.
    svg = _render_doc(tmp_path, _table_doc(
        {"header_weight": 300, "cell_size": 9}), name="w300")
    heads = re.findall(r'<text[^>]*font-weight:300[^>]*>Alpha', svg)
    assert heads, "authored header_weight not applied to header cells"
    assert "font-weight:700" not in svg


def test_header_weight_default_is_unchanged(tmp_path):
    svg = _render_doc(tmp_path, _table_doc())
    assert "font-weight:700" in svg


def _first_cell_x(svg, token="Alpha"):
    m = re.search(r'<text x="([\d.]+)"[^>]*>(?:<tspan[^>]*>)?' + token, svg)
    assert m, f"cell text {token!r} not found"
    return float(m.group(1))


def test_cell_padding_reads_from_table_style(tmp_path):
    default = _first_cell_x(_render_doc(tmp_path, _table_doc(), page="p001.svg"))
    padded = _first_cell_x(_render_doc(
        tmp_path, _table_doc({"cell_padding": 12}), name="padded"))
    assert abs((padded - default) - 8.0) < 0.01, (
        f"cell_padding not honored (default x={default}, padded x={padded}; "
        f"expected +8 over the documented 4.0 fallback)")


def test_cell_padding_element_field_wins_over_style(tmp_path):
    # TableFlow.cell_padding (the model's own field, previously ignored by the
    # flow path) takes precedence over the style key.
    t = dict(TABLE)
    t["cell_padding"] = 10
    t["style"] = {"cell_padding": 2}
    doc = _flow_doc([t])
    field = _first_cell_x(_render_doc(tmp_path, doc, name="field"))
    default = _first_cell_x(_render_doc(tmp_path, _table_doc(), name="plain"))
    assert abs((field - default) - 6.0) < 0.01, (
        f"element cell_padding did not win (default x={default}, field x={field})")


def test_cell_line_height_reads_from_table_style(tmp_path):
    def table_extent(svg):
        ys = [float(y) + float(h) for y, h in
              re.findall(r'<rect x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)"', svg)]
        assert ys, "no table cell rects found"
        return max(ys) - min(float(y) for y, _ in
                             re.findall(r'<rect x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)"', svg))
    tight = table_extent(_render_doc(tmp_path, _table_doc({"grid_color": "#eee"})))
    airy = table_extent(_render_doc(
        tmp_path, _table_doc({"grid_color": "#eee", "cell_line_height": 2.5}),
        name="airy"))
    assert airy > tight * 1.5, (
        f"cell_line_height not honored (extent {tight} -> {airy})")


# --------------------------------------------------------------------------- #
#  #62 — reserved `code` style resolves via named()                           #
# --------------------------------------------------------------------------- #
CODE_STORY = [{"type": "code", "code": "print('hi')"}]


def test_code_block_honors_reserved_code_style(tmp_path):
    svg = _render_doc(tmp_path, _flow_doc(
        CODE_STORY,
        defs={"tokens": {"text_styles": {"code": {
            "font_family": "IBM Plex Mono", "font_size": 11, "color": "#ff0000"}}}}))
    line = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?print', svg)
    assert line, "code line not rendered"
    tag = line.group(0)
    assert "IBM Plex Mono" in tag, "code style font_family ignored"
    assert "font-size:11px" in tag, "code style font_size ignored"
    assert "fill:#ff0000" in tag, "code style color ignored"
    assert "fill:#333" not in svg, "hardcoded #333 still injected despite code style"


def test_code_block_fallback_is_unchanged(tmp_path):
    # Regression pin: without a `code` style the documented fallback holds.
    svg = _render_doc(tmp_path, _flow_doc(CODE_STORY))
    line = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?print', svg)
    assert line, "code line not rendered"
    tag = line.group(0)
    assert "monospace" in tag
    assert "font-size:10px" in tag
    assert "fill:#333" in tag
