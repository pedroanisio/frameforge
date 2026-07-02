#!/usr/bin/env python3
"""
test_referential_integrity.py — coverage for validate.py's R12 rule set.

Spec §3.1/§3.3: references (anchor `ref`s, `use` symbols, style/stroke_style/
text_style tokens, master names, region chains, adjustment targets) MUST resolve
to a declared id/key. R12 turns each render-time silent failure (skipped
connector, empty symbol expansion, silently-unstyled object, invalid SVG colour)
into a coded finding with the offending path and a declared-candidates hint.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):  # the rendering package
    del sys.modules["framegraph"]

import validate as V  # noqa: E402


def _doc(objects, defs=None, targets=None, pages_extra=None):
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p",
                      "layers": [{"id": "l", "objects": objects}]}]}
    if defs:
        doc["defs"] = defs
    if targets:
        doc["targets"] = targets
    if pages_extra:
        doc["pages"] += pages_extra
    return doc


def _findings(doc):
    with tempfile.NamedTemporaryFile("w", suffix=".fg.json", delete=False) as fh:
        json.dump(doc, fh)
        path = fh.name
    try:
        _, findings, code = V.validate_doc(path)
    finally:
        os.unlink(path)
    return findings, code


def _by_code(doc, code):
    return [f for f in _findings(doc)[0] if f.code == code]


# --- dangling anchor refs (connector from/to, line/dimension anchors) --------- #
def test_connector_dangling_ref_is_an_error():
    doc = _doc([{"type": "connector", "from": {"ref": "ghost"}, "to": [10, 10]}])
    hits = _by_code(doc, "dangling-ref")
    assert hits and hits[0].severity == "ERROR" and "ghost" in hits[0].msg
    assert hits[0].path.endswith(".from")


def test_connector_object_key_and_resolvable_ref_pass():
    doc = _doc([
        {"type": "rect", "id": "a", "box": [0, 0, 10, 10]},
        {"type": "connector", "from": {"object": "a", "side": "east"}, "to": [50, 5]},
    ])
    assert not _by_code(doc, "dangling-ref")


def test_anchor_resolves_across_layers_and_group_children():
    doc = {"dsl": "FrameGraph", "version": "2.2.0", "pages": [{
        "mode": "page", "id": "p", "layers": [
            {"id": "nodes", "objects": [{"type": "group", "children": [
                {"type": "rect", "id": "nested", "box": [0, 0, 5, 5]}]}]},
            {"id": "wires", "objects": [
                {"type": "connector", "from": {"ref": "nested"}, "to": [9, 9]}]},
        ]}]}
    assert not _by_code(doc, "dangling-ref")


def test_anchor_namespace_is_per_page():
    doc = _doc([{"type": "rect", "id": "a", "box": [0, 0, 5, 5]}],
               pages_extra=[{"mode": "page", "id": "p2", "layers": [{"id": "l", "objects": [
                   {"type": "connector", "from": {"ref": "a"}, "to": [1, 1]}]}]}])
    hits = _by_code(doc, "dangling-ref")
    assert hits and hits[0].path.startswith("pages[1]")


def test_line_string_anchor_is_checked():
    doc = _doc([{"type": "line", "from": "nope", "to": [10, 10]}])
    assert _by_code(doc, "dangling-ref")


def test_dimension_anchor_object_is_checked():
    doc = _doc([{"type": "dimension", "kind": "linear",
                 "from": {"ref": "nope"}, "to": [10, 0]}])
    assert _by_code(doc, "dangling-ref")


# --- use → defs.symbols -------------------------------------------------------- #
def test_use_with_unknown_symbol_is_an_error():
    doc = _doc([{"type": "use", "symbol": "ghost", "box": [0, 0, 10, 10]}],
               defs={"symbols": {"real": {"box": [0, 0, 10, 10], "objects": []}}})
    hits = _by_code(doc, "dangling-ref")
    assert hits and hits[0].severity == "ERROR" and "ghost" in hits[0].msg


def test_use_with_known_symbol_passes():
    doc = _doc([{"type": "use", "symbol": "real", "box": [0, 0, 10, 10]}],
               defs={"symbols": {"real": {"box": [0, 0, 10, 10], "objects": []}}})
    assert not _by_code(doc, "dangling-ref")


# --- master names + region chains ---------------------------------------------- #
def test_flow_section_with_unknown_master_is_an_error():
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "defs": {"masters": {"body": {"canvas": "A4"}}},
           "pages": [{"mode": "flow", "id": "f", "master": "ghost",
                      "story": [{"type": "paragraph", "text": "x"}]}]}
    hits = _by_code(doc, "unknown-master")
    assert hits and hits[0].severity == "ERROR" and "body" in hits[0].msg  # hint


def test_page_master_and_master_next_are_checked():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5]}],
               defs={"masters": {"body": {"canvas": "A4", "next": "ghost"}}})
    doc["pages"][0]["master"] = "missing"
    codes = [f.path for f in _by_code(doc, "unknown-master")]
    assert any(p.endswith("pages[0].master") for p in codes)
    assert any(p.endswith("defs.masters.body.next") for p in codes)


def test_region_next_must_name_a_region_of_the_same_master():
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "defs": {"masters": {"body": {"canvas": "A4", "regions": [
               {"id": "main", "box": [0, 0, 500, 700], "next": "ghost"}]}}},
           "pages": [{"mode": "flow", "id": "f", "master": "body",
                      "story": [{"type": "paragraph", "text": "x"}]}]}
    hits = _by_code(doc, "dangling-ref")
    assert hits and "region" in hits[0].msg and hits[0].path.endswith("regions[0].next")


# --- adjustments hide targets --------------------------------------------------- #
def test_unknown_adjustment_hide_target_is_a_warning():
    doc = _doc([{"type": "rect", "id": "keep", "box": [0, 0, 5, 5]}],
               targets=[{"name": "story", "canvas": "instagram-story",
                         "adjustments": {"hide": ["keep", "ghost"]}}])
    hits = _by_code(doc, "unknown-adjustment-target")
    assert len(hits) == 1 and hits[0].severity == "WARN" and "ghost" in hits[0].msg


# --- token references ------------------------------------------------------------ #
def test_unknown_style_token_is_an_error():
    doc = _doc([{"type": "text", "box": [0, 0, 50, 10], "text": "x", "style": "ghost"}],
               defs={"tokens": {"styles": {"real": {"size": 10}}}})
    hits = _by_code(doc, "unknown-token")
    assert hits and hits[0].severity == "ERROR" and hits[0].path.endswith(".style")


def test_style_token_resolves_in_styles_or_text_styles():
    doc = _doc([
        {"type": "text", "box": [0, 0, 50, 10], "text": "x", "style": "a"},
        {"type": "text", "box": [0, 60, 50, 10], "text": "y", "style": "b"},
    ], defs={"tokens": {"styles": {"a": {"size": 10}}, "text_styles": {"b": {"size": 9}}}})
    assert not _by_code(doc, "unknown-token")


def test_unknown_stroke_style_token_is_an_error():
    doc = _doc([{"type": "line", "from": [0, 0], "to": [9, 0], "stroke_style": "ghost"}])
    hits = _by_code(doc, "unknown-token")
    assert hits and hits[0].severity == "ERROR" and hits[0].path.endswith(".stroke_style")


def test_span_and_cell_style_tokens_are_checked():
    doc = _doc([{"type": "text", "box": [0, 0, 50, 10],
                 "spans": [{"text": "x", "style": "ghost"}]}])
    assert _by_code(doc, "unknown-token")


def test_flowable_style_tokens_are_checked():
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "defs": {"masters": {"body": {"canvas": "A4"}}},
           "pages": [{"mode": "flow", "id": "f", "master": "body",
                      "story": [{"type": "paragraph", "text": "x", "style": "ghost"}]}]}
    assert _by_code(doc, "unknown-token")


def test_border_side_style_keyword_is_not_a_token_ref():
    # BorderSide/TextDecoration carry `style: solid|dashed|…` — CSS keywords,
    # not token references; they must not be flagged.
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5],
                 "style": {"border": {"style": "solid", "width": 1},
                           "text_decoration": {"style": "wavy"}}}])
    assert not _by_code(doc, "unknown-token")


def test_style_class_composition_is_checked():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5], "style": {"class": ["ghost"]}}])
    assert _by_code(doc, "unknown-token")


def test_unknown_colorish_string_is_a_warning():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5], "fill": "brand-blu"}],
               defs={"tokens": {"colors": {"brand-blue": "#004488"}}})
    hits = _by_code(doc, "unknown-token")
    assert len(hits) == 1 and hits[0].severity == "WARN" and "brand-blu" in hits[0].msg


def test_color_literals_and_tokens_pass():
    doc = _doc([
        {"type": "rect", "box": [0, 0, 5, 5], "fill": "#123456"},
        {"type": "rect", "box": [0, 10, 5, 5], "fill": "cornflowerblue"},
        {"type": "rect", "box": [0, 20, 5, 5], "fill": "none"},
        {"type": "rect", "box": [0, 30, 5, 5], "fill": "rgb(1, 2, 3)"},
        {"type": "rect", "box": [0, 40, 5, 5], "fill": "ink"},
    ], defs={"tokens": {"colors": {"ink": "#1f2937"}}})
    assert not _by_code(doc, "unknown-token")


def test_unknown_icon_font_is_a_warning():
    doc = _doc([{"type": "icon", "glyph": "★", "box": [0, 0, 10, 10], "font": "ghost"}])
    hits = _by_code(doc, "unknown-token")
    assert len(hits) == 1 and hits[0].severity == "WARN" and hits[0].path.endswith(".font")


def test_meta_bags_are_opaque_to_the_reference_walk():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5],
                 "meta": {"style": "not-a-token", "fill": "not-a-color"}}])
    assert not _by_code(doc, "unknown-token")


def test_masters_objects_are_reference_checked_too():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5]}],
               defs={"masters": {"body": {"canvas": "A4", "fixed": [
                   {"type": "text", "box": [0, 0, 50, 10], "text": "x", "style": "ghost"}]}}})
    hits = _by_code(doc, "unknown-token")
    assert hits and hits[0].path.startswith("defs.masters.body.fixed")


# --- the committed corpus stays referentially clean ------------------------------ #
def test_connectors_fixture_has_no_referential_findings():
    path = os.path.join(ROOT, "fixtures", "connectors.fg.yaml")
    _, findings, code = V.validate_doc(path)
    assert code == 0
    assert not [f for f in findings
                if f.code in ("dangling-ref", "unknown-token", "unknown-master",
                              "unknown-adjustment-target")]
