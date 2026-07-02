#!/usr/bin/env python3
"""
test_head.py — assertions that pin HEAD 2.3.0 to the authoritative batch.

Runnable two ways:
    python3 tests/test_head.py        # self-contained runner, prints PASS/FAIL counts
    pytest tests/test_head.py         # standard pytest

What it asserts:
  * the models are at 2.3.0 and the committed schema is generated-in-sync;
  * the authoritative style module's surface is accepted (box_shadow / filter /
    mix_blend_mode / hyphens / text_wrap enum / vertical_align / Angle strings),
    StrokeStyle-as-Style, Paint = colour|gradient|pattern, gradient `position`,
    `class` composition and the `css` escape, and legacy shorthand sugar;
  * the P3 stroke single-form still rejects inline-geometry `stroke`;
  * EVERY authoritative bundle-1 fixture validates at HEAD — directly, or, where it
    carries legacy inline strokes, fails ONLY on stroke-single-form and validates
    cleanly after the codemod;
  * the previously-migrated fixtures still validate.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "models"))
sys.path.insert(0, os.path.join(ROOT, "tooling"))
sys.path.insert(0, os.path.join(ROOT, "docs", "schema"))
shadow = sys.modules.get("framegraph")
if shadow is not None and hasattr(shadow, "__path__"):
    del sys.modules["framegraph"]

import yaml  # noqa: E402
import framegraph as fg  # noqa: E402
from pydantic import ValidationError  # noqa: E402
import validate as V  # noqa: E402
import codemod as C  # noqa: E402
import build_schema as B  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")
B1 = os.path.join(FIX, "b1")
AUTHORITATIVE = [
    "amazon-proxy-2026", "chroma-styling-showcase", "docusign-deck-v2",
    "ieee-reference-guide", "mckinsey-7s", "neutron-stars",
    "spectral-methods", "wireframing-guide",
]


def _doc(name, ext="fg.json", base=B1):
    return yaml.safe_load(open(os.path.join(base, f"{name}.{ext}"), encoding="utf-8"))


def _errors(doc_dict):
    """Validate an in-memory doc; return the list of ERROR findings."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".fg.json", delete=False) as fh:
        json.dump(doc_dict, fh)
        p = fh.name
    try:
        _, findings, _ = V.validate_doc(p)
    finally:
        os.unlink(p)
    return [f for f in findings if f.severity == "ERROR"]


def _migrate(doc_dict):
    d = copy.deepcopy(doc_dict)
    st = C.Stats()
    C.migrate_stroke_bundles(d, st)
    return C.migrate(d, st, normalize_aliases=False)


# --------------------------------------------------------------------------- #
def test_version_is_2_3_0():
    assert fg.HEAD_VERSION == "2.3.0"


def test_schema_in_sync_with_models():
    built = json.dumps(B.build(), indent=2, ensure_ascii=False) + "\n"
    on_disk = open(os.path.join(ROOT, "docs", "schema", "framegraph-v2.schema.json"), encoding="utf-8").read()
    assert built == on_disk, "docs/schema/framegraph-v2.schema.json is stale; run build_schema.py"


def test_style_module_surface_accepted():
    # properties HEAD's *drafted* Style lacked or mis-typed before 2.2.0
    s = fg.Style.model_validate({
        "box_shadow": [{"offset_x": 0, "offset_y": "2px", "blur": "6px", "color": "rgba(0,0,0,.3)"}],
        "filter": [{"fn": "blur", "value": "4px"}],
        "backdrop_filter": "blur(8px)",
        "mix_blend_mode": "multiply",
        "hyphens": "auto",
        "text_wrap": "balance",              # enum, not boolean
        "hanging_punctuation": "first",      # enum, not boolean
        "vertical_align": "super",
        "clip_path": {"shape": "circle"},
        "transform": [{"fn": "rotate", "args": ["12deg"]}],
        "letter_spacing": "0.04em",
    })
    assert s.mix_blend_mode == "multiply" and s.text_wrap == "balance"


def test_strokestyle_is_a_style():
    # tokens.stroke_styles entries are Style projections with CSS-named geometry
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "defs": {"tokens": {"stroke_styles": {
               "rule_thin": {"stroke": "#888", "stroke_width": "0.5pt", "stroke_dasharray": [2, 2]}}}},
           "pages": [{"mode": "page", "id": "s", "layers": []}]}
    fg.Document.model_validate(doc)               # must not raise
    assert fg.StrokeStyle is fg.Style


def test_paint_accepts_gradient_and_pattern():
    fg.Style.model_validate({"fill": {"kind": "linear", "angle": "135deg",
                                      "stops": [{"color": "#111", "position": "0%"},
                                                {"color": "#222", "position": "100%"}]}})
    fg.Style.model_validate({"fill": {"kind": "pattern", "pattern": "hatch", "angle": 45}})


def test_gradient_position_is_canonical_and_offset_normalised():
    g1 = fg.Gradient.model_validate({"kind": "linear",
                                     "stops": [{"color": "#000", "position": "50%"}]})
    assert g1.stops[0].position == "50%"
    g2 = fg.Gradient.model_validate({"kind": "linear",
                                     "stops": [{"color": "#000", "offset": 0.5}]})  # legacy
    assert g2.stops[0].position == "50%"          # normalised to position


def test_class_and_css_escape():
    s = fg.Style.model_validate({"class": ["base", "accent"], "css": "mix-blend-mode: screen;"})
    assert s.class_ == ["base", "accent"] and s.css


def test_fg_text_fit_extensions_on_style():
    # P2 Part C: the style module MUST mirror the P1 text-fit fields. The delivered
    # CSS module carried line_clamp/text_overflow/max_lines but dropped shrink_to_fit
    # and min_font_size; HEAD restores them as FG extensions (the decks depend on them).
    s = fg.Style.model_validate({"overflow": "shrink_to_fit", "min_font_size": 7,
                                 "line_clamp": 3, "text_overflow": "ellipsis"})
    assert s.overflow == "shrink_to_fit" and s.min_font_size == 7


def test_legacy_shorthand_sugar_accepted():
    s = fg.Style.model_validate({"font": "serif", "size": 13, "weight": "bold", "italic": True})
    assert s.font == "serif" and s.weight == "bold"


def test_p3_inline_geometry_stroke_rejected():
    bad = {"dsl": "FrameGraph", "version": "2.2.0", "pages": [{"mode": "page", "id": "s",
           "layers": [{"id": "l", "objects": [
               {"type": "line", "from": [0, 0], "to": [1, 0],
                "stroke": {"color": "#000", "width": 2, "dash": [3, 2]}}]}]}]}
    try:
        fg.Document.model_validate(bad)
        assert False, "inline-geometry stroke should be rejected"
    except ValidationError as e:
        assert "codemod" in str(e)


def test_paint_gradient_stroke_is_allowed():
    # a gradient/url *paint* on stroke is fine; only geometry dicts are rejected
    fg.Document.model_validate({"dsl": "FrameGraph", "version": "2.2.0", "pages": [
        {"mode": "page", "id": "s", "layers": [{"id": "l", "objects": [
            {"type": "rect", "box": [0, 0, 10, 10],
             "stroke": {"kind": "linear", "stops": [{"color": "#111", "position": "0%"}]}}]}]}]})


def test_authoritative_fixtures_validate_at_head():
    """Each authoritative fixture validates — directly, or only-stroke then clean
    after the codemod."""
    for name in AUTHORITATIVE:
        doc = _doc(name)
        errs = _errors(doc)
        if errs:
            # the only tolerated pre-migration errors are the P3 stroke single-form
            assert all(e.code == "stroke-single-form" or "paint-only" in e.msg for e in errs), \
                f"{name}: unexpected non-stroke errors: {[e.code for e in errs][:5]}"
            migrated = _migrate(doc)
            assert _errors(migrated) == [], f"{name}: still has errors after codemod"


def test_migrated_original_fixtures_still_valid():
    for name in ("nyt-mideast-live", "wordle-how-to-play", "calendar-3day",
                 "edst1-flange", "myfiles-internal"):
        errs = _errors(_doc(name, ext="fg.yaml", base=FIX))
        assert errs == [], f"{name}: {[e.code for e in errs][:5]}"


# --------------------------------------------------------------------------- #
def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {t.__name__}: {exc}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
