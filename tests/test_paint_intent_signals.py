#!/usr/bin/env python3
"""test_paint_intent_signals.py — PAINT-INTENT signals (the silent-ink gate).

The three existing render channels report what a render *lost* (``truncations``,
``overflow``), what it *collided* (``collisions``), and what it *kept but made
unreadable* (``legibility``). This channel reports the fourth failure mode:
**the author asked for ink and the engine painted something else, or nothing.**

The defect this gate exists to catch, found in the wild (2026-07-31, the
tile-object concept spec):

    {type: line,     style: {color: '#d5d0c6', width: 1}}   -> stroke="#000" width=1
    {type: polyline, style: {color: '#6b757e', width: 1}}   -> fill="none", NO STROKE

Both are schema-legal: :class:`Style` really does have ``color`` and ``width``
fields. But on a stroke-painted shape ``Style.color`` is *text* colour and
``Style.width`` is *box* width — neither is stroke paint. So the authored
appearance is discarded, and then:

  * ``line`` falls back to the engine's ``Stroke("#000", 1)`` — the wrong
    colour AND the wrong weight, but visible, so it survives review;
  * ``polyline``/``path`` have no fallback at all — ``fill="none"`` with no
    stroke paints **zero ink**. The object is in the model, passes validation,
    reaches the SVG, and is invisible.

Neither was reported by any surface. That silence is the architectural
omission (PALS's Law: an engine substitution the author never asked for must be
observable), and it is what these tests pin.

The contract:

  * TYPED — every signal is the dict form of the frozen ``PaintSignal``
    (rendering.domain.services.paint_intent): id, page, type, code, level,
    declared, substituted, remedy, detail.
  * TWO SURFACES, HONEST SPLIT — the *static* check (``inert_stroke_keys``) is
    exact and runs in ``validate.py`` with no render; the *resolved* checks
    (``invisible-shape``, ``injected-stroke-default``) can only be decided once
    fill and stroke are resolved, so they are render-time diagnostics. Measured
    on the committed corpus: the static rule has zero false positives, a static
    guess at invisibility had 124.
  * NO GUESSING — ``dimension`` reads its own ``style`` as a text style
    (dimension_renderer draws the measurement label from it), so ``color`` is
    NOT inert there and the object is excluded rather than misreported.
  * BYTE-IDENTICAL — the channel observes; it never changes a rendered byte.
  * QUIET WHEN CLEAN — a correctly painted document emits nothing; the channel
    always exists, so consumers never branch on key presence.
  * PROPAGATED — the channel rides ``render_pages_with_stats(diagnostics=True)``
    and ``sdk.paint_report()``, the MCP render warning names it, the design
    audit lifts it into health, and ``tooling/codemod.py --fix-inert-stroke``
    migrates it mechanically.

Runs under pytest or standalone
(``uv run python tests/test_paint_intent_signals.py``).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frameforge.rendering.domain.services.paint_intent import (  # noqa: E402
    INERT_STROKE_KEYS,
    PaintSignal,
    STROKE_PAINTED_TYPES,
    inert_stroke_keys,
)

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


# --------------------------------------------------------------------------- #
#  helpers                                                                    #
# --------------------------------------------------------------------------- #
def doc_with(*objects, canvas=(400, 200)):
    """A minimal one-page document carrying `objects` on a single layer."""
    return {
        "dsl": "FrameForge",
        "version": "2.8.1",
        "title": "paint intent",
        "pages": [{
            "mode": "page",
            "id": "p1",
            "canvas": {"size": list(canvas), "units": "px"},
            "layers": [{"id": "l1", "objects": list(objects)}],
        }],
    }


INERT_LINE = {"type": "line", "id": "rule", "from": [10, 20], "to": [390, 20],
              "style": {"color": "#d5d0c6", "width": 1}}
INERT_POLYLINE = {"type": "polyline", "id": "chevron",
                  "points": [[20, 60], [26, 64], [20, 68]],
                  "style": {"color": "#6b757e", "width": 1}}
CORRECT_LINE = {"type": "line", "id": "ok_rule", "from": [10, 100], "to": [390, 100],
                "stroke": "#d5d0c6", "stroke_style": {"stroke_width": 1}}
CORRECT_POLYLINE = {"type": "polyline", "id": "ok_chevron",
                    "points": [[20, 140], [26, 144], [20, 148]],
                    "style": {"stroke": "#6b757e", "stroke_width": 1}}


def render_diags(doc):
    """Render through the SVG proxy and return (svgs, diagnostics)."""
    from frameforge.sdk.conform import render_pages_with_stats
    svgs, _stats, diags = render_pages_with_stats(doc, diagnostics=True)
    return svgs, diags


def paint_signals(doc, code=None):
    _svgs, diags = render_diags(doc)
    sigs = diags.get("paint") or []
    return [s for s in sigs if code is None or s.get("code") == code]


# --------------------------------------------------------------------------- #
#  1. the value object                                                        #
# --------------------------------------------------------------------------- #
def test_signal_is_frozen_and_round_trips():
    sig = PaintSignal(
        id="rule", page="p1", type="line", code="inert-stroke-declaration",
        level="warn", declared={"color": "#d5d0c6", "width": 1},
        substituted={"stroke": "#000", "stroke_width": 1.0},
        remedy="stroke: '#d5d0c6' + stroke_style: {stroke_width: 1}",
        detail="style.color/style.width are not stroke paint",
    )
    with pytest.raises(Exception):
        sig.code = "other"                      # frozen
    wire = sig.to_dict()
    assert json.loads(json.dumps(wire)) == wire   # JSON-safe on the wire
    assert PaintSignal.from_dict(wire) == sig     # lossless restore


def test_inert_key_set_is_the_legacy_bundle_minus_the_keys_that_are_read():
    # The legacy pre-P3 stroke bundle was {color, width, dash, linecap, ...}.
    # Style accepts color/width/dash (they mean unrelated CSS things) and rejects
    # linecap/linejoin outright, so only the first three can silently appear.
    assert set(INERT_STROKE_KEYS) == {"color", "width", "dash"}
    # `opacity` is a real, read Style key — never call it inert.
    assert "opacity" not in INERT_STROKE_KEYS


# --------------------------------------------------------------------------- #
#  2. the static rule — exact, render-free, used by validate.py               #
# --------------------------------------------------------------------------- #
def test_inert_keys_detected_on_a_stroke_painted_shape():
    assert inert_stroke_keys(INERT_LINE, INERT_LINE["style"]) == ("color", "width")
    assert inert_stroke_keys(INERT_POLYLINE, INERT_POLYLINE["style"]) == ("color", "width")


@pytest.mark.parametrize("obj", [
    CORRECT_LINE,
    CORRECT_POLYLINE,
    {"type": "line", "from": [0, 0], "to": [1, 1], "stroke_style": "hairline"},
    {"type": "line", "from": [0, 0], "to": [1, 1], "style": {"border": "1px solid #000"}},
])
def test_a_declared_stroke_silences_the_rule(obj):
    """Paint declared in ANY read form means the author's intent is honoured."""
    style = obj.get("style") if isinstance(obj.get("style"), dict) else {}
    assert inert_stroke_keys(obj, style) == ()


def test_bare_shape_is_not_an_inert_declaration():
    """Declaring nothing is a different (render-time) question — not this rule."""
    assert inert_stroke_keys({"type": "line", "from": [0, 0], "to": [1, 1]}, {}) == ()


@pytest.mark.parametrize("t", ["text", "rect", "ellipse", "image", "table", "group"])
def test_non_stroke_painted_types_are_untouched(t):
    """`style.color` on text is THE way to colour text; `style.width` on a rect
    is a real box width. The rule must not fire on types where the keys work."""
    assert inert_stroke_keys({"type": t}, {"color": "#111", "width": 20}) == ()


def test_dimension_is_excluded_because_it_reads_style_as_a_text_style():
    """dimension_renderer draws the measurement label from `style` — so `color`
    genuinely applies there. Excluded rather than misreported (no guessing)."""
    assert "dimension" not in STROKE_PAINTED_TYPES
    assert inert_stroke_keys({"type": "dimension"}, {"color": "#111", "width": 2}) == ()


def test_rule_reports_only_the_keys_actually_present():
    assert inert_stroke_keys({"type": "path", "d": "M0 0 L1 1"}, {"color": "#111"}) == ("color",)
    assert inert_stroke_keys({"type": "path", "d": "M0 0 L1 1"}, {"width": 2}) == ("width",)


# --------------------------------------------------------------------------- #
#  3. render-time — the two resolved codes                                    #
# --------------------------------------------------------------------------- #
def test_channel_always_exists_and_is_quiet_when_clean():
    _svgs, diags = render_diags(doc_with(CORRECT_LINE, CORRECT_POLYLINE))
    assert "paint" in diags, "the channel must always exist (no key-presence branching)"
    assert diags["paint"] == []


def test_line_with_inert_style_reports_the_injected_black_default():
    sigs = paint_signals(doc_with(INERT_LINE))
    codes = {s["code"] for s in sigs}
    assert "inert-stroke-declaration" in codes
    assert "injected-stroke-default" in codes
    inert = next(s for s in sigs if s["code"] == "inert-stroke-declaration")
    assert inert["id"] == "rule" and inert["page"] == "p1" and inert["type"] == "line"
    assert inert["level"] == "warn"
    # the evidence: what the author wrote vs what the engine actually painted
    assert inert["declared"] == {"color": "#d5d0c6", "width": 1}
    assert inert["substituted"] == {"stroke": "#000", "stroke_width": 1.0}
    assert "stroke_style" in inert["remedy"] and "#d5d0c6" in inert["remedy"]


def test_polyline_with_inert_style_reports_an_invisible_shape():
    """The worse half: no fallback, so the object paints nothing at all."""
    sigs = paint_signals(doc_with(INERT_POLYLINE))
    codes = {s["code"] for s in sigs}
    assert "invisible-shape" in codes, "an unfilled, unstroked shape paints zero ink"
    inv = next(s for s in sigs if s["code"] == "invisible-shape")
    assert inv["id"] == "chevron" and inv["type"] == "polyline"
    assert inv["level"] == "warn"
    assert inv["substituted"] == {"fill": "none", "stroke": None}


def test_bare_unfilled_shape_is_reported_invisible_even_with_no_inert_keys():
    """Declaring nothing at all is still zero ink — the render-time check does
    not depend on the author having mis-spelled anything."""
    bare = {"type": "polyline", "id": "ghost", "points": [[0, 0], [10, 10]]}
    sigs = paint_signals(doc_with(bare), code="invisible-shape")
    assert [s["id"] for s in sigs] == ["ghost"]


def test_filled_shape_without_stroke_is_not_invisible():
    """A filled closed shape paints ink; only the stroke is absent. Not a defect."""
    filled = {"type": "polygon", "id": "solid", "points": [[0, 0], [10, 0], [10, 10]],
              "fill": "#333333"}
    assert paint_signals(doc_with(filled), code="invisible-shape") == []


def test_signals_are_locatable_by_page_and_id():
    doc = doc_with(INERT_LINE, INERT_POLYLINE)
    for s in paint_signals(doc):
        assert s["page"] == "p1"
        assert s["id"] in {"rule", "chevron"}


# --------------------------------------------------------------------------- #
#  4. the channel must not change a single rendered byte                      #
# --------------------------------------------------------------------------- #
def test_diagnostics_do_not_alter_the_rendered_svg():
    from frameforge.sdk.conform import render_pages_with_stats
    doc = doc_with(INERT_LINE, INERT_POLYLINE, CORRECT_LINE)
    without = render_pages_with_stats(doc)[0]
    with_diags = render_pages_with_stats(doc, diagnostics=True)[0]
    assert without == with_diags, "observing paint intent must be byte-neutral"


def test_the_documented_substitutions_still_happen():
    """This gate REPORTS the engine's behaviour; it must not silently change it
    (the b1 golden and every committed render depend on these exact bytes)."""
    svgs, _ = render_diags(doc_with(INERT_LINE, INERT_POLYLINE))
    body = svgs[0]
    assert 'stroke="#000"' in body and 'stroke-width="1"' in body
    assert '<polyline points="20,60 26,64 20,68" fill="none"/>' in body


# --------------------------------------------------------------------------- #
#  5. validate.py — the cheap, render-free gate                               #
# --------------------------------------------------------------------------- #
def _validate(tmp_path, doc, *extra):
    import yaml
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "tooling", "validate.py"), str(p), *extra],
        capture_output=True, text=True)
    return r


def test_validator_warns_on_an_inert_stroke_declaration(tmp_path):
    r = _validate(tmp_path, doc_with(INERT_LINE))
    assert "inert-stroke-declaration" in r.stdout
    assert "WARN" in r.stdout and r.returncode == 0     # a warning, not an error
    assert "stroke_style" in r.stdout                   # actionable remedy
    assert "layers[0].objects[0]" in r.stdout           # locatable path


def test_validator_is_silent_on_correctly_painted_shapes(tmp_path):
    r = _validate(tmp_path, doc_with(CORRECT_LINE, CORRECT_POLYLINE))
    assert "inert-stroke-declaration" not in r.stdout
    assert r.returncode == 0


def test_strict_promotes_the_warning_to_an_error(tmp_path):
    r = _validate(tmp_path, doc_with(INERT_LINE), "--strict")
    assert "ERROR" in r.stdout and r.returncode == 1


def test_committed_fixture_corpus_stays_clean():
    """Measured before the rule shipped: 0 inert declarations across the corpus.
    If this ever fails, a fixture regressed — fix the fixture, not the rule."""
    import glob
    sys.path.insert(0, os.path.join(REPO, "tooling"))
    import yaml
    hits = []
    for path in sorted(glob.glob(os.path.join(REPO, "tests", "fixtures", "**", "*.fg.yaml"),
                                 recursive=True)):
        try:
            doc = yaml.safe_load(open(path, encoding="utf-8"))
        except Exception:                                     # noqa: BLE001
            continue
        styles = (((doc or {}).get("defs") or {}).get("tokens") or {}).get("styles") or {}

        def walk(node):
            if isinstance(node, dict):
                if node.get("type"):
                    st = node.get("style")
                    st = styles.get(st, {}) if isinstance(st, str) else (st or {})
                    if isinstance(st, dict) and inert_stroke_keys(node, st):
                        hits.append(f"{os.path.basename(path)}:{node.get('id') or node['type']}")
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(doc)
    assert hits == [], f"fixtures gained inert stroke declarations: {hits[:10]}"


# --------------------------------------------------------------------------- #
#  6. SDK surface                                                             #
# --------------------------------------------------------------------------- #
def test_sdk_paint_report_returns_typed_signals():
    from frameforge.sdk.conform import paint_report
    sigs = paint_report(doc_with(INERT_LINE, INERT_POLYLINE))
    assert sigs and all(isinstance(s, PaintSignal) for s in sigs)
    assert {s.code for s in sigs} >= {"inert-stroke-declaration", "invisible-shape"}


def test_sdk_paint_report_is_empty_for_a_clean_document():
    from frameforge.sdk.conform import paint_report
    assert paint_report(doc_with(CORRECT_LINE, CORRECT_POLYLINE)) == []


def test_paint_report_is_exported_from_the_sdk_package():
    import frameforge.sdk as sdk
    assert hasattr(sdk, "paint_report")


# --------------------------------------------------------------------------- #
#  7. design audit — lifted into health                                       #
# --------------------------------------------------------------------------- #
def _audit(doc):
    """Audit a document exactly as the render front door does: the paint channel
    is render-time evidence, so it is threaded in like `collisions` rather than
    re-derived (the audit never re-renders)."""
    from frameforge.rendering.application.audit import audit_document
    svgs, diags = render_diags(doc)
    return audit_document(doc, svgs, collisions=diags.get("collisions"),
                          paint=diags.get("paint"))


def test_audit_lifts_paint_signals_into_health():
    report = _audit(doc_with(INERT_LINE, INERT_POLYLINE))
    assert "paint" in report, "the channel is always present (clean = empty list)"
    codes = {f["code"] for f in report["health"]}
    assert "invisible-shape" in codes
    assert "inert-stroke-declaration" in codes


def test_audit_paint_channel_is_present_and_empty_when_clean():
    report = _audit(doc_with(CORRECT_LINE, CORRECT_POLYLINE))
    assert report["paint"] == []
    assert not [f for f in report["health"] if f["code"].endswith("-shape")]


def test_audit_info_level_signals_do_not_become_health_flags():
    """`injected-stroke-default` is informational — it must ride the channel
    without nagging in health, exactly as `contrast-unverified` does."""
    report = _audit(doc_with(INERT_LINE))
    assert any(s["code"] == "injected-stroke-default" for s in report["paint"])
    assert "injected-stroke-default" not in {f["code"] for f in report["health"]}


def test_audit_summary_counts_unpainted_objects():
    from frameforge.rendering.application.audit import compact_census
    report = _audit(doc_with(INERT_POLYLINE))
    assert compact_census(report)["unpainted"] == 1


# --------------------------------------------------------------------------- #
#  8. codemod — the mechanical migration                                      #
# --------------------------------------------------------------------------- #
def _codemod(tmp_path, doc, *extra):
    import yaml
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "tooling", "codemod.py"), str(p),
         "--in-place", *extra],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return yaml.safe_load(p.read_text(encoding="utf-8")), r.stdout


def test_codemod_migrates_an_inert_declaration(tmp_path):
    out, log = _codemod(tmp_path, doc_with(INERT_LINE), "--fix-inert-stroke")
    obj = out["pages"][0]["layers"][0]["objects"][0]
    assert obj["stroke"] == "#d5d0c6"
    assert obj["stroke_style"] == {"stroke_width": 1}
    assert "color" not in (obj.get("style") or {})
    assert "width" not in (obj.get("style") or {})
    assert "inert:1" in log


def test_codemod_migration_makes_the_document_paint_what_was_authored(tmp_path):
    out, _ = _codemod(tmp_path, doc_with(INERT_LINE, INERT_POLYLINE), "--fix-inert-stroke")
    svgs, diags = render_diags(out)
    assert diags["paint"] == [], "migration must clear every paint signal"
    assert 'stroke="#d5d0c6"' in svgs[0]
    assert 'stroke="#6b757e"' in svgs[0]
    assert 'stroke="#000"' not in svgs[0]


def test_codemod_is_idempotent(tmp_path):
    once, _ = _codemod(tmp_path, doc_with(INERT_LINE), "--fix-inert-stroke")
    import yaml
    p = tmp_path / "again.fg.yaml"
    p.write_text(yaml.safe_dump(once, sort_keys=False), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "tooling", "codemod.py"), str(p),
         "--in-place", "--fix-inert-stroke"], capture_output=True, text=True)
    assert "inert:0" in r.stdout
    assert yaml.safe_load(p.read_text(encoding="utf-8")) == once


def test_codemod_leaves_text_colour_alone(tmp_path):
    """`style.color` on text is correct authoring — the migration must not eat it."""
    txt = {"type": "text", "id": "t", "box": [0, 0, 100, 20], "text": "hi",
           "style": {"color": "#111111", "font_size": 12}}
    out, _ = _codemod(tmp_path, doc_with(txt), "--fix-inert-stroke")
    assert out["pages"][0]["layers"][0]["objects"][0]["style"]["color"] == "#111111"


def test_codemod_does_not_run_the_migration_without_the_flag(tmp_path):
    out, _ = _codemod(tmp_path, doc_with(INERT_LINE))
    obj = out["pages"][0]["layers"][0]["objects"][0]
    assert "stroke" not in obj and obj["style"]["color"] == "#d5d0c6"


# --------------------------------------------------------------------------- #
#  9. MCP surface                                                             #
# --------------------------------------------------------------------------- #
def test_mcp_render_warning_names_the_paint_channel():
    from frameforge.mcp.pipeline import _paint_warning
    note = _paint_warning([
        {"code": "invisible-shape", "id": "chevron", "page": "p1", "type": "polyline",
         "level": "warn", "detail": "no fill and no stroke"},
    ])
    assert "invisible-shape" in note and "chevron" in note
    assert "diagnostics.paint" in note


def test_mcp_paint_warning_is_empty_when_clean():
    from frameforge.mcp.pipeline import _paint_warning
    assert _paint_warning([]) == ""


# --------------------------------------------------------------------------- #
#  10. regression — the exact document that exposed this                      #
# --------------------------------------------------------------------------- #
def test_regression_tile_object_spec_shapes():
    """The two authored shapes from the 2026-07-31 concept spec, verbatim.

    Before the fix both rendered silently wrong: 51 rules black-1px instead of
    the authored colour/width, and 11 chevrons invisible.
    """
    doc = doc_with(
        {"type": "line", "id": "hairline", "from": [64, 44], "to": [730, 44],
         "style": {"color": "#d5d0c6", "width": 1}},
        {"type": "polyline", "id": "caret", "points": [[218, 656], [224, 660], [218, 664]],
         "style": {"color": "#6b757e", "width": 1}},
        canvas=(794, 1123),
    )
    sigs = paint_signals(doc)
    by_id = {s["id"]: s for s in sigs if s["code"] != "injected-stroke-default"}
    assert by_id["hairline"]["code"] == "inert-stroke-declaration"
    assert by_id["hairline"]["declared"]["color"] == "#d5d0c6"
    assert by_id["caret"]["code"] in {"inert-stroke-declaration", "invisible-shape"}
    assert {s["code"] for s in sigs if s["id"] == "caret"} == {
        "inert-stroke-declaration", "invisible-shape"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
