"""Render-time collision detector (O1) — same-layer ink overlaps that were not
declared with `overlap: allowed`.

Design of record: ``docs/decisions/collision-gate/collision-gate-decision.md``
(rev 2), recommendation P0 + O1.

Why RENDER-TIME and not static (the finding the doc reconfirms):

    A static box check floods — boxes are layout regions, routinely larger than
    their ink, and blind to wrap and real glyph width (617–1090 false positives
    on the corpus). Reliable overlap needs rendered INK; ink needs layout +
    metrics; therefore the check lives in `render_text`.

Contract:

* it compares INK rectangles (the drawn extent: anchor-placed width × line-box
  height), not authoring boxes;
* it is SAME-LAYER only — cross-layer overlap is a legitimate z-order effect and
  is exempt by construction;
* an overlap where BOTH parties declare `overlap: allowed` is a consented effect,
  not a collision;
* it scopes to top-level layer text objects — table/flow cells lay out through
  their own engines and are excluded (Follow-Up #4);
* every collision names the mode that produced it (estimate vs real metrics),
  because an estimate verdict is unverified by default (PALS's Law / B4).
"""

from __future__ import annotations

import sys

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.rendering.application.renderer import Renderer  # noqa: E402

BIGFONT = {"font_family": ["DejaVu Sans", "sans-serif"], "font_size": 20}


def _doc(objects, layers=None):
    page = {"mode": "page", "id": "p1",
            "canvas": {"size": [400, 200], "units": "px"},
            "rendering": {"coordinate_mode": "absolute"},
            "layers": layers or [{"id": "main", "z": 0, "objects": objects}]}
    return {"dsl": "FrameForge", "version": "2.0.0", "title": "t",
            "defs": {"tokens": {}}, "pages": [page]}


def _collisions(doc, real_metrics=False):
    r = Renderer(doc, ".", real_metrics=real_metrics)
    r.render_page(doc["pages"][0])
    return r.diagnostics.get("collisions", [])


def _txt(oid, box, text="OVERLAPPING WIDE TEXT", **extra):
    return {"type": "text", "id": oid, "box": box, "text": text,
            "style": BIGFONT, **extra}


# two wide texts whose INK overlaps (same layer): boxes chosen so the drawn
# glyphs, not just the boxes, intersect.
OVERLAP = [_txt("a", [10, 40, 380, 30]), _txt("b", [200, 40, 190, 30])]


def test_ink_overlap_same_layer_is_a_collision():
    cols = _collisions(_doc(OVERLAP))
    assert cols, "an unconsented same-layer ink overlap must be reported"
    ids = {frozenset(c["ids"]) for c in cols}
    assert frozenset({"a", "b"}) in ids


def test_consent_on_both_parties_suppresses_the_collision():
    objs = [_txt("a", [10, 40, 380, 30], overlap="allowed"),
            _txt("b", [200, 40, 190, 30], overlap="allowed")]
    assert _collisions(_doc(objs)) == []


def test_consent_on_only_one_party_is_not_enough():
    objs = [_txt("a", [10, 40, 380, 30], overlap="allowed"),
            _txt("b", [200, 40, 190, 30])]
    assert _collisions(_doc(objs)), "consent must be unanimous to suppress"


def test_cross_layer_overlap_is_exempt():
    layers = [{"id": "back", "z": 0, "objects": [_txt("a", [10, 40, 380, 30])]},
              {"id": "front", "z": 1, "objects": [_txt("b", [200, 40, 190, 30])]}]
    assert _collisions(_doc(None, layers=layers)) == []


def test_decorative_object_never_collides():
    objs = [_txt("a", [10, 40, 380, 30]),
            _txt("b", [200, 40, 190, 30], decorative=True)]
    assert _collisions(_doc(objs)) == []


def test_boxes_that_overlap_but_ink_does_not_are_not_a_collision():
    """The whole point of render-time: big boxes, short ink, no touch."""
    objs = [_txt("a", [10, 40, 180, 30], text="Age:"),
            _txt("b", [120, 40, 180, 30], text="62")]
    # boxes overlap 60px; the words "Age:" and "62" are nowhere near each other
    assert _collisions(_doc(objs)) == []


def test_separated_text_is_clean():
    objs = [_txt("a", [10, 40, 180, 30], text="left"),
            _txt("b", [210, 40, 180, 30], text="right")]
    assert _collisions(_doc(objs)) == []


def test_collision_names_the_metrics_mode():
    c = _collisions(_doc(OVERLAP))[0]
    assert c["metrics"] in ("estimate", "real")


def test_collision_reports_the_ink_overlap_area():
    c = _collisions(_doc(OVERLAP))[0]
    assert c["area"] > 0


def test_table_cells_do_not_self_collide():
    """A table lays out its own cells; its grid must not read as collisions."""
    table = {"type": "table", "id": "t", "box": [10, 20, 380, 120],
             "rows": [["Alpha", "Beta"], ["Gamma", "Delta"]],
             "style": BIGFONT}
    assert _collisions(_doc([table])) == []


def test_collisions_ride_on_the_sdk_collision_report():
    from frameforge.sdk import collision_report
    rep = collision_report(_doc(OVERLAP))
    assert any(frozenset(c["ids"]) == frozenset({"a", "b"}) for c in rep)
