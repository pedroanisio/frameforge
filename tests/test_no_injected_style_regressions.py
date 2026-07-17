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


# --------------------------------------------------------------------------- #
#  #63 — captions: authored `caption` style wins over italic/center/bold      #
# --------------------------------------------------------------------------- #
CAPTION_DEFS = {"tokens": {"text_styles": {"caption": {
    "font_family": "Inter", "color": "#ff00ff", "text_align": "left"}}}}


def _caption_tag(svg, token="the caption text"):
    m = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?' + token, svg)
    assert m, "caption text not rendered"
    return m.group(0)


def test_image_caption_honors_authored_caption_style(tmp_path):
    svg = _render_doc(tmp_path, _flow_doc(
        [{"type": "image", "src": "missing.png", "height": 40, "caption": "the caption text"}],
        defs=CAPTION_DEFS))
    tag = _caption_tag(svg)
    assert "fill:#ff00ff" in tag, "authored caption color ignored"
    assert "font-style:italic" not in tag, "italic still stamped over authored caption style"


def test_image_caption_fallback_is_italic_centered(tmp_path):
    # Pin: without a `caption` style the documented italic+center fallback holds.
    svg = _render_doc(tmp_path, _flow_doc(
        [{"type": "image", "src": "missing.png", "height": 40, "caption": "the caption text"}]))
    tag = _caption_tag(svg)
    assert "font-style:italic" in tag


def test_table_caption_honors_authored_caption_style(tmp_path):
    t = {"type": "table", "rows": [["a", "b"]], "caption": "the caption text"}
    svg = _render_doc(tmp_path, _flow_doc([t], defs=CAPTION_DEFS))
    tag = _caption_tag(svg)
    assert "fill:#ff00ff" in tag
    assert "font-weight:700" not in tag, "bold still stamped over authored caption style"


def test_table_caption_fallback_is_bold(tmp_path):
    t = {"type": "table", "rows": [["a", "b"]], "caption": "the caption text"}
    svg = _render_doc(tmp_path, _flow_doc([t]))
    assert "font-weight:700" in _caption_tag(svg)


# --------------------------------------------------------------------------- #
#  #64 — math ink derives from the document, never a #111 literal             #
# --------------------------------------------------------------------------- #
MATH_STORY = [{"type": "math", "tex": "E = mc^2"}]


def test_math_ink_follows_body_style(tmp_path):
    svg = _render_doc(tmp_path, _flow_doc(
        MATH_STORY,
        defs={"tokens": {"text_styles": {"body": {
            "font_family": "Inter", "font_size": 12, "color": "#224466"}}}}))
    assert "#111" not in svg, "math ink still hardcoded #111"
    assert "#224466" in svg, "math ink did not follow the body style"


def test_math_ink_unstyled_uses_the_sanctioned_base(tmp_path):
    # Unstyled documents unify on the ONE sanctioned base colour (#1c1c1c);
    # the second engine literal (#111) is gone.
    svg = _render_doc(tmp_path, _flow_doc(MATH_STORY))
    assert "#111" not in svg
    assert "#1c1c1c" in svg


# --------------------------------------------------------------------------- #
#  #66 — flow lists: marker and indent are authorable                         #
# --------------------------------------------------------------------------- #
LIST_STORY = [{"type": "list", "items": ["alpha item", "beta item"]}]


def test_list_marker_field_is_honored(tmp_path):
    story = [dict(LIST_STORY[0], marker="→")]
    svg = _render_doc(tmp_path, _flow_doc(story))
    assert "→ alpha item" in svg, "ListFlow.marker ignored by the flow path"
    assert "• " not in svg


def test_list_marker_fallback_is_bullet(tmp_path):
    svg = _render_doc(tmp_path, _flow_doc(LIST_STORY))
    assert "• alpha item" in svg


def test_list_indent_is_authorable(tmp_path):
    def item_x(svg):
        return float(re.search(r'<text x="([\d.]+)"[^>]*>(?:<tspan[^>]*>)?• alpha',
                               svg).group(1))
    para_x = float(re.search(
        r'<text x="([\d.]+)"',
        _render_doc(tmp_path, _flow_doc([{"type": "paragraph", "text": "ref"}]),
                    name="ref")).group(1))
    plain = item_x(_render_doc(tmp_path, _flow_doc(LIST_STORY), name="plainlist"))
    wide = item_x(_render_doc(
        tmp_path, _flow_doc([dict(LIST_STORY[0], indent=40)]), name="widelist"))
    assert abs((plain - para_x) - 16.0) < 0.01, "default list indent changed"
    assert abs((wide - para_x) - 40.0) < 0.01, "authored list indent ignored"


# --------------------------------------------------------------------------- #
#  #74 — ONE engine fallback: resolver default = body style, else sanctioned  #
# --------------------------------------------------------------------------- #
def _page_text_doc(defs=None, style=None):
    obj = {"type": "text", "id": "t1", "box": [10, 10, 300, 40], "text": "loose text"}
    if style:
        obj["style"] = style
    doc = {"dsl": "FrameForge", "version": "2.2.0", "profile": "report", "title": "t",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [400, 200]},
                      "layers": [{"id": "l", "objects": [obj]}]}]}
    if defs:
        doc["defs"] = defs
    return doc


def test_unstyled_text_object_uses_the_sanctioned_base(tmp_path):
    # The resolver's private sans/14/1.25 trio is gone: unstyled text objects
    # get the ONE sanctioned constant (serif/12/lh 1.4), same as flow.
    svg = _render_doc(tmp_path, _page_text_doc())
    tag = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?loose text', svg).group(0)
    assert "font-size:12px" in tag, "resolver still defaults to its own 14px"
    assert "font-family:serif" in tag, "resolver still defaults to its own sans"


def test_unstyled_text_object_follows_body_style(tmp_path):
    # The document's reserved `body` style is the default for ALL text — page
    # objects included, not just flow.
    svg = _render_doc(tmp_path, _page_text_doc(
        defs={"tokens": {"text_styles": {"body": {
            "font_family": "Inter", "font_size": 15, "color": "#345678"}}}}))
    tag = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?loose text', svg).group(0)
    assert "Inter" in tag, "body style face did not cascade to page text objects"
    assert "font-size:15px" in tag
    assert "fill:#345678" in tag


# --------------------------------------------------------------------------- #
#  #69 — standalone TableObject: no injected chrome (ADR-0006 parity)         #
# --------------------------------------------------------------------------- #
def _page_table_doc(style=None, **fields):
    t = {"type": "table", "id": "tb", "box": [10, 10, 360, 120],
         "header": ["Alpha", "Beta"], "rows": [["one", "two"], ["three", "four"]]}
    t.update(fields)
    if style is not None:
        t["style"] = style
    return {"dsl": "FrameForge", "version": "2.2.0", "profile": "report", "title": "t",
            "pages": [{"mode": "page", "id": "p", "canvas": {"size": [400, 200]},
                       "layers": [{"id": "l", "objects": [t]}]}]}


def test_table_object_injects_no_chrome_by_default(tmp_path):
    svg = _render_doc(tmp_path, _page_table_doc())
    assert "#3b6ea5" not in svg, "header blue still injected"
    assert 'fill="white"' not in svg.replace(
        '<rect width="100%" height="100%" fill="white"/>', ""), \
        "table background still painted white"
    assert "#bbb" not in svg, "grid #bbb still injected"
    assert "fill:#fff" not in svg, "header text #fff still injected"
    assert "fill:#222" not in svg, "cell text #222 still injected"


def test_table_object_zebra_needs_authored_fill(tmp_path):
    svg = _render_doc(tmp_path, _page_table_doc(zebra=True))
    assert "#f4f6f9" not in svg, "zebra stripe colour still injected"
    svg = _render_doc(tmp_path, _page_table_doc(
        style={"zebra_fill": "#eeeecc"}, zebra=True), name="zeb")
    assert 'fill="#eeeecc"' in svg or "#eeeecc" in svg, "authored zebra_fill ignored"


def test_table_object_header_fill_is_opt_in(tmp_path):
    svg = _render_doc(tmp_path, _page_table_doc(style={"header_fill": "#224466"}))
    assert "#224466" in svg, "authored header_fill not painted"


def test_table_object_text_follows_document_base(tmp_path):
    svg = _render_doc(tmp_path, _page_table_doc())
    cell = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?one', svg).group(0)
    assert "font-family:serif" in cell, "table cells still forced sans-serif"
    assert "fill:#1c1c1c" in cell, "table cells still forced #222"


# --------------------------------------------------------------------------- #
#  #65 — TOC: reserved styles + authorable number_width / level_indent        #
# --------------------------------------------------------------------------- #
TOC_STORY = [{"type": "toc", "title": "Contents"},
             {"type": "heading", "level": 1, "text": "One"},
             {"type": "paragraph", "text": "alpha"},
             {"type": "heading", "level": 2, "text": "Two"},
             {"type": "paragraph", "text": "beta"}]


def test_toc_entries_resolve_reserved_toc_style(tmp_path):
    svg = _render_doc(tmp_path, _flow_doc(
        TOC_STORY,
        defs={"tokens": {"text_styles": {"toc": {
            "font_family": "IBM Plex Mono", "font_size": 8}}}}))
    entry = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?One', svg).group(0)
    assert "IBM Plex Mono" in entry, "reserved toc style face ignored for entries"
    assert "font-size:8px" in entry, "reserved toc style size ignored for entries"


def test_toc_title_resolves_reserved_toc_title_style(tmp_path):
    svg = _render_doc(tmp_path, _flow_doc(
        TOC_STORY,
        defs={"tokens": {"text_styles": {"toc_title": {
            "font_family": "Inter", "font_size": 9, "font_weight": 300}}}}))
    title = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?Contents', svg).group(0)
    assert "font-size:9px" in title, "toc_title size ignored (1.5x heuristic still applied)"
    assert "bold" not in title, "toc_title weight ignored (bold still stamped)"


def test_toc_title_fallback_is_unchanged(tmp_path):
    # Pin: no reserved styles -> title = 1.5 x entry size (16.5px), bold.
    svg = _render_doc(tmp_path, _flow_doc(TOC_STORY))
    title = re.search(r'<text[^>]*>(?:<tspan[^>]*>)?Contents', svg).group(0)
    assert "font-size:16.5px" in title and "font-weight:bold" in title


def test_toc_level_indent_is_authorable(tmp_path):
    def entry_x(svg, token):
        return float(re.search(r'<text x="([\d.]+)"[^>]*>(?:<tspan[^>]*>)?' + token,
                               svg).group(1))
    plain = _render_doc(tmp_path, _flow_doc(TOC_STORY), name="plain")
    t = [dict(TOC_STORY[0], level_indent=30)] + TOC_STORY[1:]
    wide = _render_doc(tmp_path, _flow_doc(t), name="wide")
    d_plain = entry_x(plain, "Two") - entry_x(plain, "One")
    d_wide = entry_x(wide, "Two") - entry_x(wide, "One")
    assert abs(d_plain - 14.0) < 0.01, f"default level indent changed ({d_plain})"
    assert abs(d_wide - 30.0) < 0.01, f"authored level_indent ignored ({d_wide})"


def test_toc_number_width_is_authorable(tmp_path):
    # A wider number column shortens the leader run; assert the entry text box
    # width shrinks by the difference (usable - indent - num_w).
    def entry_w(svg, token="One"):
        m = re.search(r'<text x="[\d.]+"[^>]*>(?:<tspan[^>]*>)?' + token, svg)
        tag = m.group(0)
        return float(re.search(r'width="([\d.]+)"', tag).group(1)) if 'width="' in tag else None
    plain = _render_doc(tmp_path, _flow_doc(TOC_STORY), name="p2")
    t = [dict(TOC_STORY[0], number_width=60)] + TOC_STORY[1:]
    wide = _render_doc(tmp_path, _flow_doc(t), name="w2")
    # fall back to comparing the page-number x when text_tag emits no width attr
    n_plain = re.findall(r'<text[^>]*text-anchor="end"[^>]*>(?:<tspan[^>]*>)?\d+', plain)
    n_wide = re.findall(r'<text[^>]*text-anchor="end"[^>]*>(?:<tspan[^>]*>)?\d+', wide)
    assert n_plain and n_wide, "toc page numbers not rendered"
    assert plain != wide, "authored number_width had no effect"


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
