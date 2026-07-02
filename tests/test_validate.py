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


def test_r1_gradient_stroke_paint_is_allowed():
    codes = _codes(_doc([{
        "type": "line",
        "from": [0, 0],
        "to": [1, 0],
        "stroke": {"kind": "linear", "stops": [{"color": "#000", "position": "0%"}]},
        "stroke_style": {"stroke_width": 2},
    }]))
    assert "stroke-single-form" not in codes


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


def test_tabular_box_model_ignores_scattered_text():
    """Many text objects at *unique* positions are not a table.

    Regression: the heuristic fired whenever len(distinct_x)*len(distinct_y) >=
    count, which is trivially true for scattered (non-aligned) text — so a cover or
    contact page full of free-placed labels was wrongly flagged. A real table
    *reuses* column/row positions; scattered text does not.
    """
    scattered = [
        {"type": "text", "box": [12, 30, 200, 40], "text": "Big Title"},
        {"type": "text", "box": [40, 110, 160, 24], "text": "subtitle here"},
        {"type": "text", "box": [300, 70, 120, 20], "text": "a label"},
        {"type": "text", "box": [88, 250, 240, 60], "text": "a paragraph block"},
        {"type": "text", "box": [420, 360, 90, 18], "text": "footer-ish"},
        {"type": "text", "box": [150, 420, 300, 30], "text": "tagline"},
        {"type": "text", "box": [24, 520, 110, 22], "text": "page 1"},
    ]
    canvas = {"size": [600, 700], "units": "px"}
    assert "tabular-box-model" not in _codes(_doc(scattered, canvas))


def test_tabular_box_model_exempts_lettering():
    """Text the author has declared as lettering (``meta.role``) is not counted as
    an accidental table — the escape hatch the SDK's ``page.lettering()`` sets."""
    texts = []
    for r in range(3):
        for c in range(2):
            texts.append({"type": "text", "box": [c * 120 + 10, r * 30 + 10, 80, 20],
                          "text": "t"})
    canvas = {"size": [400, 200], "units": "px"}
    assert "tabular-box-model" in _codes(_doc(texts, canvas))
    lettered = [{**o, "meta": {"role": "lettering"}} for o in texts]
    assert "tabular-box-model" not in _codes(_doc(lettered, canvas))


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


# --- canvas presets: sourced from the renderer, covering every model preset --- #
def _renderer_presets():
    """CanvasResolver.PRESETS/DEFAULT_WH read straight from the source file (AST),
    so this gate holds without importing the rendering package."""
    import ast
    src = os.path.join(ROOT, "framegraph", "rendering", "domain", "services",
                       "canvas_resolver.py")
    presets = default = None
    for node in ast.parse(open(src, encoding="utf-8").read()).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if getattr(t, "id", None) == "PRESETS":
                    presets = ast.literal_eval(node.value)
                elif getattr(t, "id", None) == "DEFAULT_WH":
                    default = tuple(ast.literal_eval(node.value))
    return presets, default


def test_preset_table_matches_the_renderer():
    presets, default = _renderer_presets()
    assert V.PRESETS == presets, "validate.py preset table drifted from CanvasResolver.PRESETS"
    assert V.DEFAULT_WH == default
    assert V._FALLBACK_PRESETS == presets, "the standalone fallback copy drifted"
    assert V._FALLBACK_DEFAULT_WH == default


def test_every_model_preset_resolves():
    import typing
    sys.path.insert(0, os.path.join(ROOT, "models"))
    shadow = sys.modules.get("framegraph")
    if shadow is not None and hasattr(shadow, "__path__"):  # rendering package shadows the models
        del sys.modules["framegraph"]
    import framegraph as fg
    for preset in typing.get_args(fg.PagePreset):
        assert V._canvas_wh(preset), f"PagePreset {preset!r} has no size in the validator table"


def test_social_preset_containment_is_not_spurious():
    # regression: instagram-story used to fall back to A4 and warn on everything
    doc = _doc([{"type": "rect", "box": [0, 0, 1080, 1900]}], canvas="instagram-story")
    assert "containment" not in _codes(doc)
    doc = _doc([{"type": "rect", "box": [0, 0, 1080, 2500]}], canvas="instagram-story")
    assert "containment" in _codes(doc)


def test_canvasless_page_resolves_master_then_renderer_default():
    # master canvas wins …
    doc = _doc([{"type": "rect", "box": [0, 0, 900, 500]}])
    doc["defs"] = {"masters": {"m": {"canvas": {"size": [400, 400], "units": "px"}}}}
    doc["pages"][0]["master"] = "m"
    assert "containment" in _codes(doc)
    # … else the renderer default (1280×800), not A4
    doc = _doc([{"type": "rect", "box": [700, 0, 400, 100]}])  # inside 1280, outside A4's 595
    assert "containment" not in _codes(doc)
    doc = _doc([{"type": "rect", "box": [0, 0, 2000, 100]}])
    assert "containment" in _codes(doc)


# --- masters' fixed/running objects go through the same static rules ----------- #
def test_master_fixed_objects_are_rule_checked():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5]}])
    doc["defs"] = {"masters": {"body": {"canvas": "A4", "fixed": [
        {"type": "circle", "center": [5, 5], "r": 4}]}}}
    findings, _ = _findings(doc)
    hits = [f for f in findings if f.code == "deprecated-alias"]
    assert hits and hits[0].path.startswith("defs.masters.body.fixed[0]")


def test_master_running_objects_are_rule_checked():
    doc = _doc([{"type": "rect", "box": [0, 0, 5, 5]}])
    doc["defs"] = {"masters": {"body": {"canvas": "A4", "running": {"footer": [
        {"type": "line", "from": [0, 800], "to": [500, 800],
         "stroke": {"color": "#000", "width": 2}}]}}}}
    findings, _ = _findings(doc)
    hits = [f for f in findings if f.code == "stroke-single-form"]
    assert hits and hits[0].path.startswith("defs.masters.body.running.footer[0]")


# --- R11 non-conformant 3D (G-2): perspective is declared but never rendered --- #
def test_r11_perspective_is_flagged_non_conformant():
    """`perspective` passes through inert — no target renders 3D. G-2 flags it."""
    codes = _codes(_doc([
        {"type": "rect", "box": [0, 0, 10, 10], "style": {"perspective": "800px"}}]))
    assert "non-conformant-3d" in codes


def test_r11_perspective_none_is_not_flagged():
    """`perspective: none` (the inert default) is not flagged."""
    codes = _codes(_doc([
        {"type": "rect", "box": [0, 0, 10, 10], "style": {"perspective": "none"}}]))
    assert "non-conformant-3d" not in codes


def test_r11_no_perspective_is_not_flagged():
    codes = _codes(_doc([{"type": "rect", "box": [0, 0, 10, 10]}]))
    assert "non-conformant-3d" not in codes
