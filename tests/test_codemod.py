#!/usr/bin/env python3
"""
test_codemod.py — coverage for tooling/codemod.py (the HEAD migration), which the
suite only exercised indirectly (~40%). Drives every migration branch directly:

  * gradient `offset` -> `position` (numeric <=1 -> %, >1 / string left as-is)
  * P3 stroke single-form split (new bundle / merge dict / string-style -> meta /
    colour-string left alone)
  * P4 `size` -> `sizing` (dict on non-icon, dict on icon, numeric icon size kept)
  * alias normalisation circle->ellipse, polygon->polyline, curve/bezier->path
  * migrate_stroke_bundles + _pct
  * main() across --in-place / --bump / --normalize-aliases and JSON vs YAML output

Models-side import (codemod puts models/ on sys.path) — evict a package shadow
first, per test_head.py.
"""
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))

import codemod as C  # noqa: E402
import yaml  # noqa: E402


def _mig(node, normalize_aliases=False):
    st = C.Stats()
    return C.migrate(node, st, normalize_aliases), st


# --- gradient offset -> position --------------------------------------------- #
def test_gradient_offset_to_percent():
    out, st = _mig({"color": "#000", "offset": 0.5})
    assert out["position"] == "50%" and "offset" not in out and st.grad == 1


def test_gradient_offset_gt1_left_as_is():
    out, _ = _mig({"color": "#000", "offset": 12})
    assert out["position"] == 12


def test_offset_without_color_untouched():
    out, st = _mig({"offset": 0.5})
    assert "offset" in out and "position" not in out and st.grad == 0


# --- P3 stroke single-form --------------------------------------------------- #
def test_stroke_split_into_new_style():
    out, st = _mig({"type": "rect", "stroke": {"color": "#111", "width": 2, "dash": [3, 2]}})
    assert out["stroke"] == "#111"
    assert out["stroke_style"] == {"stroke_width": 2, "stroke_dasharray": [3, 2]}
    assert st.stroke == 1


def test_stroke_split_merges_existing_dict_style():
    out, _ = _mig({"type": "rect", "stroke": {"color": "#111", "width": 2},
                   "stroke_style": {"stroke_linecap": "round"}})
    assert out["stroke_style"] == {"stroke_linecap": "round", "stroke_width": 2}


def test_stroke_split_string_style_goes_to_meta():
    out, _ = _mig({"type": "rect", "stroke": {"color": "#111", "width": 2}, "stroke_style": "rule"})
    assert out["stroke_style"] == "rule"
    assert out["meta"]["_codemod_stroke_geometry"] == {"stroke_width": 2}


def test_stroke_colour_string_untouched():
    out, st = _mig({"type": "rect", "stroke": "#111"})
    assert out["stroke"] == "#111" and st.stroke == 0 and "stroke_style" not in out


# --- P4 size -> sizing ------------------------------------------------------- #
def test_size_dict_renamed_on_shape():
    out, st = _mig({"type": "rect", "size": {"width": "fill"}})
    assert out["sizing"] == {"width": "fill"} and "size" not in out and st.size == 1


def test_size_dict_renamed_on_icon():
    out, st = _mig({"type": "icon", "size": {"width": "hug"}})
    assert out["sizing"] == {"width": "hug"} and st.size == 1


def test_numeric_icon_size_kept():
    out, st = _mig({"type": "icon", "size": 14})
    assert out["size"] == 14 and "sizing" not in out and st.size == 0


# --- alias normalisation ----------------------------------------------------- #
def test_normalize_circle_to_ellipse():
    out, st = _mig({"type": "circle", "center": [5, 5], "r": 4}, normalize_aliases=True)
    assert out["type"] == "ellipse" and out["rx"] == 4 and out["ry"] == 4 and st.alias == 1


def test_normalize_polygon_to_polyline():
    out, st = _mig({"type": "polygon", "points": [[0, 0], [1, 0], [0, 1]]}, normalize_aliases=True)
    assert out["type"] == "polyline" and out["closed"] is True and st.alias == 1


def test_normalize_curve_to_path():
    out, st = _mig({"type": "curve", "from": [0, 0], "to": [10, 10],
                    "control1": [2, 2], "control2": [8, 8]}, normalize_aliases=True)
    assert out["type"] == "path"
    assert out["d"] == [["M", 0, 0], ["C", 2, 2, 8, 8, 10, 10]] and st.alias == 1


def test_normalize_bezier_default_controls():
    out, _ = _mig({"type": "bezier", "from": [0, 0], "to": [10, 10]}, normalize_aliases=True)
    assert out["type"] == "path" and out["d"][0] == ["M", 0, 0]


def test_aliases_untouched_without_flag():
    out, st = _mig({"type": "circle", "center": [5, 5], "r": 4}, normalize_aliases=False)
    assert out["type"] == "circle" and st.alias == 0


# --- stroke bundles + helpers ------------------------------------------------ #
def test_migrate_stroke_bundles_rewrites_legacy():
    doc = {"defs": {"tokens": {"stroke_styles": {"rule": {"color": "#888", "width": 0.5, "dash": [2, 2]}}}}}
    st = C.Stats()
    C.migrate_stroke_bundles(doc, st)
    assert doc["defs"]["tokens"]["stroke_styles"]["rule"] == {
        "stroke": "#888", "stroke_width": 0.5, "stroke_dasharray": [2, 2]}
    assert st.stroke == 1


def test_migrate_stroke_bundles_skips_css_named():
    doc = {"defs": {"tokens": {"stroke_styles": {"r": {"stroke": "#000", "stroke_width": 1}}}}}
    st = C.Stats()
    C.migrate_stroke_bundles(doc, st)
    assert st.stroke == 0


def test_pct():
    assert C._pct("50%") == 0.5
    assert C._pct(0.5) == 0.5
    assert C._pct("nope") == "nope"


# --- main() CLI -------------------------------------------------------------- #
def _legacy_stroke_doc():
    return {"dsl": "FrameForge", "version": "2.0.0", "pages": [{"mode": "page", "id": "p", "layers": [
        {"id": "l", "objects": [{"type": "line", "from": [0, 0], "to": [1, 0],
                                 "stroke": {"color": "#000", "width": 2}}]}]}]}


def test_main_writes_head_yaml(tmp_path):
    src = tmp_path / "doc.fg.yaml"
    src.write_text(yaml.safe_dump(_legacy_stroke_doc()), encoding="utf-8")
    assert C.main([str(src)]) == 0
    out = tmp_path / "doc.fg.head.yaml"
    assert out.exists()
    obj = yaml.safe_load(out.read_text())["pages"][0]["layers"][0]["objects"][0]
    assert obj["stroke"] == "#000" and obj["stroke_style"] == {"stroke_width": 2}


def test_main_in_place_bump_json(tmp_path):
    src = tmp_path / "doc.fg.json"
    src.write_text(json.dumps(_legacy_stroke_doc()), encoding="utf-8")
    assert C.main([str(src), "--in-place", "--bump"]) == 0
    doc = json.loads(src.read_text())
    assert doc["version"] == C.HEAD_VERSION
    assert doc["pages"][0]["layers"][0]["objects"][0]["stroke"] == "#000"


def test_main_normalize_aliases(tmp_path):
    doc = {"dsl": "FrameForge", "version": "2.2.0", "pages": [{"mode": "page", "id": "p", "layers": [
        {"id": "l", "objects": [{"type": "circle", "center": [5, 5], "r": 4}]}]}]}
    src = tmp_path / "doc.fg.yaml"
    src.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert C.main([str(src), "--in-place", "--normalize-aliases"]) == 0
    assert yaml.safe_load(src.read_text())["pages"][0]["layers"][0]["objects"][0]["type"] == "ellipse"
