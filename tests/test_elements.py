#!/usr/bin/env python3
"""
test_elements.py — model-level coverage of EVERY element the grammar permits.

Two guarantees:
  1. COMPLETENESS — the sample set is asserted equal to the model's discriminator
     literals, so adding a `VisualObject`/`Flowable` type (or removing one) fails
     this test until a sample is added. "Unit tests on all elements" stays true by
     construction, not by hand.
  2. VALIDATION — a minimal instance of each visual object / flowable / inline
     validates against `Document` (the source of truth).

Plus a Hypothesis property: a fuzzed rect+text document round-trips through
model_dump -> model_validate unchanged (catches alias/serialisation asymmetries,
e.g. `from`/`class`).

Models-only (no renderer import) so the `frameforge` *package* never shadows the
`frameforge` *models* module in the shared pytest process — see test_head.py.
"""
import os
import sys
import typing

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "docs"))
import models.frameforge as fg  # noqa: E402  (package-qualified: the real frameforge package stays importable)
import pytest  # noqa: E402
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


# --- minimal valid samples, one per discriminator literal --------------------- #
OBJECT_SAMPLES = {
    "rect": {"type": "rect", "box": [0, 0, 10, 10]},
    "ellipse": {"type": "ellipse", "center": [5, 5], "rx": 4, "ry": 3},
    "circle": {"type": "circle", "center": [5, 5], "r": 4},
    "line": {"type": "line", "from": [0, 0], "to": [10, 10]},
    "polyline": {"type": "polyline", "points": [[0, 0], [10, 10]]},
    "polygon": {"type": "polygon", "points": [[0, 0], [10, 0], [5, 10]]},
    "path": {"type": "path", "d": "M0 0 L10 10"},
    "curve": {"type": "curve", "from": [0, 0], "to": [10, 10]},
    "bezier": {"type": "bezier", "from": [0, 0], "to": [10, 10]},
    "text": {"type": "text", "box": [0, 0, 100, 20], "text": "hi"},
    "image": {"type": "image", "src": "x.png", "box": [0, 0, 10, 10]},
    "icon": {"type": "icon", "glyph": "★", "box": [0, 0, 10, 10]},
    "bullet_list": {"type": "bullet_list", "items": ["a", "b"], "box": [0, 0, 100, 40]},
    "dimension": {"type": "dimension", "kind": "linear", "from": [0, 0], "to": [10, 0]},
    "connector": {"type": "connector", "from": [0, 0], "to": [10, 10]},
    "table": {"type": "table", "rows": [["a", "b"]], "box": [0, 0, 100, 40]},
    "group": {"type": "group", "children": [{"type": "rect", "box": [0, 0, 5, 5]}]},
}

FLOW_SAMPLES = {
    "paragraph": {"type": "paragraph", "text": "hi"},
    "heading": {"type": "heading", "level": 1, "text": "H"},
    "list": {"type": "list", "items": ["a"]},
    "spacer": {"type": "spacer"},
    "page_break": {"type": "page_break"},
    "column_break": {"type": "column_break"},
    "table": {"type": "table", "rows": [["a"]]},
    "image": {"type": "image", "src": "x.png"},
    "figure": {"type": "figure", "object": {"type": "rect", "box": [0, 0, 5, 5]}},
    "block": {"type": "block", "children": [{"type": "paragraph", "text": "x"}]},
    "keep_together": {"type": "keep_together", "children": [{"type": "paragraph", "text": "x"}]},
    "code": {"type": "code", "source": "x = 1"},
    "math": {"type": "math", "tex": "x^2"},
    "toc": {"type": "toc"},
    "bibliography": {"type": "bibliography"},
}

INLINE_SAMPLES = {
    "ref": {"kind": "ref", "target": "h-1"},
    "cite": {"kind": "cite", "key": "smith2020"},
    "math": {"kind": "math", "tex": "x"},
    "code": {"kind": "code", "text": "x = 1"},
    "link": {"kind": "link", "href": "https://example.com", "content": ["example"]},
    "footnote": {"kind": "footnote", "content": [{"type": "paragraph", "text": "n"}]},
}


# --- helpers ------------------------------------------------------------------ #
def _page_doc(objects):
    return {"dsl": "FrameForge", "version": "2.2.0",
            "pages": [{"mode": "page", "id": "p", "layers": [{"id": "l", "objects": objects}]}]}


def _flow_doc(flow):
    return {"dsl": "FrameForge", "version": "2.2.0",
            "pages": [{"mode": "flow", "id": "f", "master": "m", "story": [flow]}]}


def _discriminator_literals(union_alias, field):
    members = typing.get_args(typing.get_args(union_alias)[0])
    out = set()
    for m in members:
        out |= set(typing.get_args(m.model_fields[field].annotation))
    return out


# --- completeness gates (the "all elements" guarantee) ------------------------ #
def test_object_samples_cover_every_visual_type():
    assert set(OBJECT_SAMPLES) == _discriminator_literals(fg.VisualObject, "type"), \
        "OBJECT_SAMPLES is out of sync with the model's VisualObject types"


def test_flow_samples_cover_every_flowable_type():
    assert set(FLOW_SAMPLES) == _discriminator_literals(fg.Flowable, "type"), \
        "FLOW_SAMPLES is out of sync with the model's Flowable types"


def test_inline_samples_cover_every_inline_kind():
    kinds = set()
    for m in typing.get_args(fg.Inline):
        f = getattr(m, "model_fields", {}).get("kind") if hasattr(m, "model_fields") else None
        if f is not None:
            kinds |= set(typing.get_args(f.annotation))
    assert set(INLINE_SAMPLES) == kinds, "INLINE_SAMPLES is out of sync with the Inline kinds"


# --- per-element validation --------------------------------------------------- #
@pytest.mark.parametrize("t,obj", sorted(OBJECT_SAMPLES.items()))
def test_visual_object_validates(t, obj):
    fg.Document.model_validate(_page_doc([obj]))


@pytest.mark.parametrize("t,flow", sorted(FLOW_SAMPLES.items()))
def test_flowable_validates(t, flow):
    fg.Document.model_validate(_flow_doc(flow))


def test_images_and_figures_accept_accessibility_text():
    fg.Document.model_validate(_page_doc([
        {
            "type": "image",
            "src": "chart.png",
            "box": [0, 0, 100, 80],
            "alt": "Quarterly revenue chart",
            "actual_text": "Revenue rose from Q1 to Q4.",
        }
    ]))
    fg.Document.model_validate(_flow_doc({
        "type": "image",
        "src": "diagram.png",
        "alt": "System boundary diagram",
        "actual_text": "The service boundary surrounds the API and worker.",
    }))
    fg.Document.model_validate(_flow_doc({
        "type": "figure",
        "object": {"type": "rect", "box": [0, 0, 5, 5]},
        "alt": "Legend swatch",
        "actual_text": "A colored swatch representing the legend.",
    }))


def test_page_accepts_logical_reading_order():
    fg.Document.model_validate({
        "dsl": "FrameForge",
        "version": "2.2.0",
        "pages": [{
            "mode": "page",
            "id": "p",
            "reading_order": ["title", "chart"],
            "layers": [{"id": "l", "objects": [
                {"type": "image", "id": "chart", "src": "chart.png", "box": [0, 0, 100, 80], "alt": "Revenue chart"},
                {"type": "text", "id": "title", "box": [0, 90, 100, 20], "text": "Revenue"},
            ]}],
        }],
    })


@pytest.mark.parametrize("kind,inline", sorted(INLINE_SAMPLES.items()))
def test_inline_validates(kind, inline):
    fg.Document.model_validate(_page_doc([{"type": "text", "box": [0, 0, 50, 10], "spans": [inline]}]))


# --- Curve control-point hygiene (c1/c2 legacy aliases) ----------------------- #
def test_curve_c1_c2_normalise_to_control1_control2():
    doc = fg.Document.model_validate(_page_doc([
        {"type": "curve", "from": [0, 0], "to": [10, 10], "c1": [2, 2], "c2": [8, 8]}]))
    cu = doc.pages[0].layers[0].objects[0]
    assert cu.control1 == [2.0, 2.0] and cu.control2 == [8.0, 8.0]
    assert "c1" not in type(cu).model_fields  # legacy keys are accepted, not modelled


def test_curve_contradictory_control_aliases_rejected():
    with pytest.raises(Exception, match="aliases and disagree"):
        fg.Document.model_validate(_page_doc([
            {"type": "curve", "from": [0, 0], "to": [10, 10],
             "c1": [2, 2], "control1": [3, 3]}]))


def test_curve_equal_control_aliases_accepted():
    doc = fg.Document.model_validate(_page_doc([
        {"type": "curve", "from": [0, 0], "to": [10, 10],
         "c1": [2, 2], "control1": [2, 2]}]))
    assert doc.pages[0].layers[0].objects[0].control1 == [2.0, 2.0]


# --- Connector endpoints / route (typed at HEAD, §3.11) ------------------------ #
def test_connector_accepts_the_fixture_surface():
    """The exact shapes fixtures/connectors.fg.yaml uses (which the renderer
    renders) must validate: object/port, object/side, point target, route with
    legacy `type` key + points, boxed label."""
    fg.Document.model_validate(_page_doc([
        {"type": "connector", "from": {"object": "left", "port": "east"},
         "to": {"object": "right", "side": "west"}, "route": {"type": "straight"},
         "label": {"text": "port to side", "box": [130, 60, 100, 18], "style": "label"}},
        {"type": "connector", "from": {"object": "left", "side": "south"},
         "to": {"point": [300, 140]},
         "route": {"type": "orthogonal", "points": [[80, 130], [300, 130]]}},
    ]))


def test_connector_endpoint_object_key_normalises_to_ref():
    doc = fg.Document.model_validate(_page_doc([
        {"type": "connector", "from": {"object": "a"}, "to": {"ref": "b", "offset": 4}}]))
    conn = doc.pages[0].layers[0].objects[0]
    assert conn.from_.ref == "a" and conn.to.ref == "b" and conn.to.offset == 4


def test_connector_route_type_key_normalises_to_kind():
    doc = fg.Document.model_validate(_page_doc([
        {"type": "connector", "from": [0, 0], "to": [1, 1],
         "route": {"type": "curved", "points": [[5, 5]]}}]))
    route = doc.pages[0].layers[0].objects[0].route
    assert route.kind == "curved" and route.points == [[5.0, 5.0]]


def test_connector_endpoint_needs_ref_or_point():
    with pytest.raises(Exception, match="`ref`.*or `point`"):
        fg.Document.model_validate(_page_doc([
            {"type": "connector", "from": {"side": "north"}, "to": [1, 1]}]))


def test_connector_bare_string_label_is_rejected():
    """The renderer only draws boxed labels; a bare-string label would be a
    silent drop, so the model rejects it."""
    with pytest.raises(Exception):
        fg.Document.model_validate(_page_doc([
            {"type": "connector", "from": [0, 0], "to": [1, 1], "label": "nope"}]))


# --- Length/Angle string patterns (schema-time unit gating) -------------------- #
@pytest.mark.parametrize("value", ["12pt", "12px", "1.5em", "-4mm", "50%", "1fr", ".5rem"])
def test_length_string_units_accepted(value):
    fg.Document.model_validate(_page_doc([{"type": "rect", "box": [0, 0, value, 10]}]))


@pytest.mark.parametrize("value", ["12ptx", "12 pt", "vw", "5vw", "px", "vh12"])
def test_length_string_typos_rejected(value):
    with pytest.raises(Exception):
        fg.Document.model_validate(_page_doc([{"type": "rect", "box": [0, 0, value, 10]}]))


def test_angle_string_units():
    fg.Document.model_validate(_page_doc([
        {"type": "rect", "box": [0, 0, 5, 5],
         "fill": {"kind": "linear", "angle": "45deg", "stops": [{"color": "#000"}]}}]))
    with pytest.raises(Exception):
        fg.Document.model_validate(_page_doc([
            {"type": "rect", "box": [0, 0, 5, 5],
             "fill": {"kind": "linear", "angle": "45degg", "stops": [{"color": "#000"}]}}]))


# --- Hypothesis: serialisation round-trip is identity ------------------------- #
@settings(max_examples=60, deadline=None)
@given(
    box=st.lists(st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
                 min_size=4, max_size=4),
    text=st.text(max_size=64),
)
def test_fuzzed_document_roundtrips(box, text):
    doc = _page_doc([{"type": "rect", "box": box}, {"type": "text", "box": box, "text": text}])
    d1 = fg.Document.model_validate(doc).model_dump(by_alias=True, exclude_none=True)
    d2 = fg.Document.model_validate(d1).model_dump(by_alias=True, exclude_none=True)
    assert d1 == d2


if __name__ == "__main__":
    import json
    for name in ("test_object_samples_cover_every_visual_type",
                 "test_flow_samples_cover_every_flowable_type",
                 "test_inline_samples_cover_every_inline_kind"):
        globals()[name]()
    for t, o in OBJECT_SAMPLES.items():
        fg.Document.model_validate(_page_doc([o]))
    for t, f in FLOW_SAMPLES.items():
        fg.Document.model_validate(_flow_doc(f))
    print(json.dumps({"visual": len(OBJECT_SAMPLES), "flow": len(FLOW_SAMPLES),
                      "inline": len(INLINE_SAMPLES)}))
    print("OK")
