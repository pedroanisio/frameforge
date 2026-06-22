#!/usr/bin/env python3
"""
test_validate.py — coverage for tooling/validate.py (the HEAD validator), which the
suite only ran over already-clean fixtures (~75%). Each static/geometric rule is
tripped with a minimal document and the emitted finding-code is asserted, plus the
CLI (`main`), strict mode, and the load-failure path.
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


def _doc(objects, canvas=None):
    page = {"mode": "page", "id": "p", "layers": [{"id": "l", "objects": objects}]}
    if canvas:
        page["canvas"] = canvas
    return {"dsl": "FrameGraph", "version": "2.2.0", "pages": [page]}


def _findings(doc, strict=False):
    with tempfile.NamedTemporaryFile("w", suffix=".fg.json", delete=False) as fh:
        json.dump(doc, fh)
        path = fh.name
    try:
        _, findings, code = V.validate_doc(path, strict=strict)
    finally:
        os.unlink(path)
    return findings, code


def _codes(doc, strict=False):
    return {f.code for f in _findings(doc, strict)[0]}


# --- per-object static rules -------------------------------------------------- #
def test_r1_stroke_single_form():
    assert "stroke-single-form" in _codes(_doc([
        {"type": "line", "from": [0, 0], "to": [1, 0], "stroke": {"color": "#000", "width": 2}}]))


def test_r2_size_renamed():
    assert "size-renamed" in _codes(_doc([{"type": "rect", "box": [0, 0, 5, 5], "size": {"width": "fill"}}]))


def test_r3_hug_on_shape():
    assert "hug-on-shape" in _codes(_doc([{"type": "rect", "box": [0, 0, 5, 5], "sizing": {"width": "hug"}}]))


def test_r4_fill_under_free():
    assert "fill-under-free" in _codes(_doc([{"type": "rect", "box": [0, 0, 5, 5], "sizing": {"width": "fill"}}]))


def test_r4_fr_under_free():
    assert "fr-under-free" in _codes(_doc([{"type": "rect", "box": [0, 0, "1fr", 10]}]))


def test_r5_grid_span_non_grid_parent():
    assert "grid_span-parent" in _codes(_doc([{"type": "rect", "box": [0, 0, 5, 5], "grid_span": [1, 2]}]))


def test_r6_boxless_under_layout():
    grp = {"type": "group", "layout": {"kind": "row"},
           "children": [{"type": "line", "from": [0, 0], "to": [5, 0]}]}
    assert "boxless-under-layout" in _codes(_doc([grp]))


def test_r7_unpinned_font():
    doc = _doc([{"type": "text", "box": [0, 0, 50, 12], "text": "hi",
                 "sizing": {"width": "hug"}, "style": {"font_family": "sans"}}])
    assert "unpinned-font" in _codes(doc)


def test_r10_deprecated_alias():
    assert "deprecated-alias" in _codes(_doc([{"type": "circle", "center": [5, 5], "r": 4}]))


def test_out_of_profile_object_type():
    assert "out-of-profile" in _codes(_doc([{"type": "uml_class", "box": [0, 0, 5, 5]}]))


# --- document-level rules ----------------------------------------------------- #
def test_out_of_profile_defs_key():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5]}])
    doc["defs"] = {"symbols": {"x": {}}}
    assert "out-of-profile" in _codes(doc)


def test_top_level_text_contract_placement():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5]}])
    doc["text_contract"] = {"overflow": "clip"}
    assert "text_contract-placement" in _codes(doc)


# --- geometric audit ---------------------------------------------------------- #
def test_containment_outside_canvas():
    doc = _doc([{"type": "rect", "box": [0, 0, 999, 999]}], canvas={"size": [100, 100], "units": "px"})
    assert "containment" in _codes(doc)


def test_free_group_overlap():
    grp = {"type": "group", "layout": {"kind": "free"}, "children": [
        {"type": "rect", "box": [0, 0, 80, 80]},
        {"type": "rect", "box": [10, 10, 80, 80]}]}
    assert "overlap" in _codes(_doc([grp]))


def test_tabular_box_model():
    texts = []
    for r in range(3):
        for c in range(3):
            texts.append({"type": "text", "box": [c * 100, r * 40, 90, 30], "text": f"{r},{c}"})
    doc = _doc(texts, canvas={"size": [400, 200], "units": "px"})
    assert "tabular-box-model" in _codes(doc)


# --- CLI / strict / load failure ---------------------------------------------- #
def test_strict_promotes_warnings_to_errors():
    doc = _doc([{"type": "circle", "center": [5, 5], "r": 4}])  # deprecated-alias = WARN
    _, code = _findings(doc, strict=False)
    assert code == 0
    _, code_strict = _findings(doc, strict=True)
    assert code_strict == 1  # warning promoted to error under --strict


def test_main_on_clean_fixture(capsys):
    rc = V.main([os.path.join(ROOT, "fixtures", "calendar-3day.fg.yaml"), "--quiet"])
    assert rc == 0


def test_main_strict_on_warned_fixture():
    rc = V.main([os.path.join(ROOT, "fixtures", "wordle-how-to-play.fg.yaml"), "--strict", "--quiet"])
    assert rc == 1  # has advisory warnings -> errors under --strict


def test_load_failure_returns_code_2():
    with tempfile.NamedTemporaryFile("w", suffix=".fg.yaml", delete=False) as fh:
        fh.write("{ this: is: not: valid: yaml")
        path = fh.name
    try:
        _, findings, code = V.validate_doc(path)
    finally:
        os.unlink(path)
    assert code == 2 and any(f.code == "load" for f in findings)


def test_main_verbose_prints_findings(capsys):
    # non-quiet path exercises Finding.__str__ and the per-finding print loop
    rc = V.main([os.path.join(ROOT, "fixtures", "wordle-how-to-play.fg.yaml")])
    out = capsys.readouterr().out
    assert rc == 0 and ("WARN" in out or "PASS" in out)


def test_preset_canvas_containment():
    # canvas given as a {preset} object -> _canvas_wh preset branch
    doc = _doc([{"type": "rect", "box": [0, 0, 5000, 5000]}], canvas={"preset": "A4"})
    assert "containment" in _codes(doc)


def test_flow_section_figure_object_is_walked():
    # a figure in a flow story carries a visual object -> _walk_flow recursion
    flow = {"mode": "flow", "id": "f", "master": "m", "story": [
        {"type": "figure", "object": {"type": "circle", "center": [5, 5], "r": 4}}]}
    doc = {"dsl": "FrameGraph", "version": "2.2.0", "pages": [flow]}
    assert "deprecated-alias" in _codes(doc)
