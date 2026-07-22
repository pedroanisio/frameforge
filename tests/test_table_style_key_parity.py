#!/usr/bin/env python3
"""`header_text` / `cell_text` mean the SAME thing in both table renderers.

Drift-risk-map CRITICAL #3: the flow table resolved these keys as COLOURS
while `TableObject` resolved them as STYLE REFS — the same document language
meant different things per table type, and the model docstrings described only
the colour semantics. The unified rule, pinned here:

  * a dict value        → inline text-style fragment (both paths, unchanged);
  * a string that names a defined `tokens.styles` / `tokens.text_styles` entry
    → style ref (the richer TableObject usage, preserved);
  * any other string    → a colour, exactly as the flow path always read it
    (hex / css name / tokens.colors key).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import render_page_svgs  # noqa: E402
from tooling import render_fixtures as R  # noqa: E402

HEAD_HEX = "#123456"
CELL_HEX = "#654321"
STYLE = {"header_text": HEAD_HEX, "cell_text": CELL_HEX}


def _doc(pages):
    return {"dsl": "FrameForge", "version": "2.3.0", "pages": pages}


def _object_table_page(style):
    return {"mode": "page", "id": "p", "canvas": {"size": [400, 300], "units": "px"},
            "layers": [{"id": "main", "objects": [
                {"type": "table", "id": "t", "box": [20, 20, 360, 200],
                 "header": ["Name", "Value"], "rows": [["a", "1"], ["b", "2"]],
                 "style": style}]}]}


def _flow_table_svg(tmp_path, style, defs=None):
    """Render a flow table through the same Renderer via the fixtures proxy."""
    import yaml
    doc = {"dsl": "FrameForge", "version": "2.3.0", "profile": "report",
           "pages": [{"mode": "flow", "id": "p", "story": [
               {"type": "table", "header": ["Name", "Value"],
                "rows": [["a", "1"], ["b", "2"]], "style": style}]}]}
    if defs:
        doc["defs"] = defs
    src = tmp_path / "flowtable.fg.yaml"
    src.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert R.main([str(src), "--out", str(tmp_path / "out"), "-q"]) == 0
    return (tmp_path / "out" / R.stem_of(str(src)) / "p001.svg").read_text(encoding="utf-8")


# --- the fork, both directions ------------------------------------------- #
def test_table_object_bare_colour_string_is_a_colour():
    """CRITICAL #3 regression: `TableObject` used to send "#123456" through
    `text_style()` (a token lookup that finds nothing) and silently drop it."""
    svg = render_page_svgs(_doc([_object_table_page(STYLE)]))[0]
    assert HEAD_HEX in svg and CELL_HEX in svg


def test_flow_table_bare_colour_string_is_a_colour(tmp_path):
    """Pins the flow semantics that were always colour-valued."""
    svg = _flow_table_svg(tmp_path, STYLE)
    assert HEAD_HEX in svg and CELL_HEX in svg


def test_both_paths_agree_on_the_same_document_style(tmp_path):
    """The parity assertion itself: one style dict, two table types, same fills."""
    obj_svg = render_page_svgs(_doc([_object_table_page(STYLE)]))[0]
    flow_svg = _flow_table_svg(tmp_path, STYLE)
    for hexval in (HEAD_HEX, CELL_HEX):
        assert (hexval in obj_svg) and (hexval in flow_svg)


# --- richer usages survive the unification --------------------------------- #
def test_table_object_style_ref_still_resolves():
    """A defined tokens.styles name keeps the richer style-ref semantics."""
    doc = _doc([_object_table_page({"header_text": "hdr", "cell_text": "cel"})])
    doc["defs"] = {"tokens": {"styles": {
        "hdr": {"color": "#0A7E33", "font_weight": 800},
        "cel": {"color": "#AA1122"},
    }}}
    svg = render_page_svgs(doc)[0]
    assert "#0A7E33" in svg and "#AA1122" in svg


def test_table_object_dict_value_still_inline_style():
    doc = _doc([_object_table_page({"header_text": {"color": "#0B5FFF"}})])
    svg = render_page_svgs(doc)[0]
    assert "#0B5FFF" in svg


def test_flow_table_style_ref_now_resolves(tmp_path):
    """Unification also grants the flow path the style-ref semantics."""
    defs = {"tokens": {"styles": {"hdr": {"color": "#0A7E33"}}}}
    svg = _flow_table_svg(tmp_path, {"header_text": "hdr"}, defs=defs)
    assert "#0A7E33" in svg


def test_tokens_colors_key_resolves_as_colour_in_both_paths(tmp_path):
    """A tokens.colors name (not a style name) is a colour in BOTH renderers."""
    defs = {"tokens": {"colors": {"brand": "#C0FFEE"}}}
    obj_doc = _doc([_object_table_page({"cell_text": "brand"})])
    obj_doc["defs"] = defs
    assert "#C0FFEE" in render_page_svgs(obj_doc)[0]
    assert "#C0FFEE" in _flow_table_svg(tmp_path, {"cell_text": "brand"}, defs=defs)
