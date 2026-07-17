#!/usr/bin/env python3
"""
test_element_render.py — render-side coverage of every visual element, and the
SILENT-IGNORE GATE.

For each visual object type we render a minimal sample and check its SVG
footprint. The key assertion is `test_no_unexpected_silent_ignores`: no visual
element in the local renderer's supported point-anchor profile renders to NOTHING.
So:
  * a new element type that the proxy silently drops -> FAILS (no silent ignore),
  * and if an element is intentionally outside this profile, it must be tracked by
    changing this gate deliberately.

Plus a Hypothesis property: the renderer never raises on fuzzed box coordinates
and arbitrary text.

Renderer-only (no models import): the `frameforge` package must resolve to the
rendering package here, so we evict a models-module shadow first — mirror of the
guard in test_head.py / test_rendering_svg_semantics.py.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # a non-package (the models module)
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling.render_fixtures import Renderer  # noqa: E402
import pytest  # noqa: E402
from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

# minimal renderable samples (paint set so primitives are emitted)
OBJECT_SAMPLES = {
    "rect": {"type": "rect", "box": [0, 0, 10, 10], "fill": "#111"},
    "ellipse": {"type": "ellipse", "center": [5, 5], "rx": 4, "ry": 3, "fill": "#111"},
    "circle": {"type": "circle", "center": [5, 5], "r": 4, "fill": "#111"},
    "line": {"type": "line", "from": [0, 0], "to": [10, 10], "stroke": "#111"},
    "polyline": {"type": "polyline", "points": [[0, 0], [10, 10]], "stroke": "#111"},
    "polygon": {"type": "polygon", "points": [[0, 0], [10, 0], [5, 10]], "fill": "#111"},
    "path": {"type": "path", "d": "M0 0 L10 10", "stroke": "#111"},
    "curve": {"type": "curve", "from": [0, 0], "to": [10, 10], "stroke": "#111"},
    "bezier": {"type": "bezier", "from": [0, 0], "to": [10, 10], "stroke": "#111"},
    "text": {"type": "text", "box": [0, 0, 100, 20], "text": "hi"},
    "image": {"type": "image", "src": "x.png", "box": [0, 0, 10, 10]},
    "icon": {"type": "icon", "glyph": "★", "box": [0, 0, 10, 10]},
    "bullet_list": {"type": "bullet_list", "items": ["a", "b"], "box": [0, 0, 100, 40]},
    "dimension": {"type": "dimension", "kind": "linear", "from": [0, 0], "to": [10, 0]},
    "table": {"type": "table", "rows": [["a", "b"]], "box": [0, 0, 100, 40]},
    "group": {"type": "group", "children": [{"type": "rect", "box": [0, 0, 5, 5], "fill": "#111"}]},
    "container": {"type": "container", "box": [0, 0, 100, 40],
                  "children": [{"type": "rect", "box": [0, 0, 20, 20], "fill": "#111"}]},
    "component": {"type": "component", "box": [0, 0, 110, 50], "title": "Card", "body": "Body", "fill": "#fff"},
    "legend": {"type": "legend", "box": [0, 0, 100, 20], "items": [{
        "sample": {"type": "line", "from": [0, 10], "to": [20, 10], "stroke": "#111"},
        "label": {"text": "edge", "box": [24, 2, 60, 16]},
    }]},
    "chip_row": {"type": "chip_row", "origin": [0, 0], "items": [{"text": "api", "width": 32}]},
    "uml.marker_glyph": {"type": "uml.marker_glyph", "position": [10, 10], "kind": "filled_diamond", "color": "#111"},
    "uml.classifier_box": {"type": "uml.classifier_box", "box": [0, 0, 100, 70], "name": "Order",
                           "stereotype": "entity", "attributes": [{"name": "id", "type": "UUID"}],
                           "operations": [{"name": "total", "return_type": "Money"}]},
    "uml.component_box": {"type": "uml.component_box", "box": [0, 0, 120, 50], "name": "API",
                          "provided_interfaces": ["IOrders"], "required_interfaces": ["IAuth"]},
    "uml.state_box": {"type": "uml.state_box", "box": [0, 0, 100, 55], "name": "Ready",
                      "entry": "start", "do": "wait"},
    "uml.action": {"type": "uml.action", "box": [0, 0, 80, 36], "name": "Submit"},
    "uml.artifact_box": {"type": "uml.artifact_box", "box": [0, 0, 100, 44], "name": "Report",
                         "stereotype": "artifact"},
    "uml.node_box": {"type": "uml.node_box", "box": [0, 0, 100, 44], "name": "Worker", "kind": "device"},
    "uml.lifeline": {"type": "uml.lifeline", "box": [0, 0, 100, 80], "name": "svc", "type_name": "Service",
                     "head_height": 30},
    "uml.activation_bar": {"type": "uml.activation_bar", "box": [45, 20, 10, 50]},
    "uml.actor": {"type": "uml.actor", "box": [0, 0, 60, 80], "name": "User"},
    "uml.socket": {"type": "uml.socket", "box": [0, 0, 32, 16], "name": "IFace"},
    "uml.lollipop": {"type": "uml.lollipop", "box": [0, 0, 32, 16], "name": "IFace"},
    "uml.activity_node": {"type": "uml.activity_node", "box": [0, 0, 50, 30], "kind": "decision", "name": "ok?"},
    "uml.pseudostate": {"type": "uml.pseudostate", "box": [0, 0, 22, 22], "kind": "final"},
}

# the SVG primitive each painted element must emit
EXPECT = {
    "rect": "<rect", "ellipse": "<ellipse", "circle": "<circle", "line": "<line",
    "polyline": "<polyline", "polygon": "<polygon", "path": "<path",
    "curve": "<path", "bezier": "<path", "text": "<text",
    "icon": "<text", "bullet_list": "<text", "dimension": "<g",
    "image": "<rect", "table": "<rect", "group": "<g", "container": "<rect",
    "component": "<rect", "legend": "<line", "chip_row": "<rect", "uml.marker_glyph": "<polygon",
    "uml.classifier_box": "<rect", "uml.component_box": "<rect",
    "uml.state_box": "<rect", "uml.action": "<rect", "uml.artifact_box": "<rect",
    "uml.node_box": "<rect", "uml.lifeline": "<line", "uml.activation_bar": "<rect",
    "uml.actor": "<circle", "uml.socket": "<path", "uml.lollipop": "<circle",
    "uml.activity_node": "<polygon", "uml.pseudostate": "<circle",
}

# documented silent-ignore set. Any change here must be deliberate (this is the gate).
UNRENDERED = set()


def _render_body(obj):
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [120, 80]},
                      "layers": [{"id": "l", "objects": [obj]}]}]}
    out = Renderer(doc, ".").render_page(doc["pages"][0])
    svg = "".join(out) if isinstance(out, list) else out
    return svg.split('fill="white"/>', 1)[-1].rsplit("</svg>", 1)[0]  # drop the bg rect


def _has_element(body):
    return re.search(r"<[a-zA-Z]", body) is not None


@pytest.mark.parametrize("t,obj", sorted(OBJECT_SAMPLES.items()))
def test_element_render_footprint(t, obj):
    body = _render_body(obj)
    if t in UNRENDERED:
        assert not _has_element(body), f"{t!r} now renders — remove it from UNRENDERED"
    else:
        assert _has_element(body), f"{t!r} produced NO SVG element (silent ignore!)"
        assert EXPECT[t] in body, f"{t!r} expected {EXPECT[t]!r} in its SVG, got: {body[:120]!r}"
        if t.startswith("uml.") and t != "uml.marker_glyph":
            assert f"?{t}" not in body


def test_no_unexpected_silent_ignores():
    """The whole point: the empirically-empty set must equal the declared allowlist."""
    empty = {t for t, o in OBJECT_SAMPLES.items() if not _has_element(_render_body(o))}
    assert empty == UNRENDERED, (
        f"silent-ignore set changed: rendered-empty={sorted(empty)}, declared={sorted(UNRENDERED)}. "
        "Implement a painter, or update UNRENDERED deliberately.")


def test_component_uses_definition_variant_and_slots():
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "defs": {"tokens": {"colors": {"panel": "#eef6ff", "border": "#335577"},
                               "text_styles": {
                                   "heading": {"size": 12, "weight": 700, "align": "center", "color": "#111"},
                                   "body": {"size": 10, "align": "center", "color": "#333"},
                               },
                               "stroke_styles": {"rule": {"stroke": "border", "stroke_width": 2}}},
                    "components": {
                        "card": {"geometry": {"radius": 7},
                                 "variants": {"selected": {"fill": "panel", "stroke_style": "rule"}},
                                 "internal_layout": {
                                     "title": {"box_offset": [0, 5, "100%", 16], "style": "heading"},
                                     "body": {"box_offset": [8, 24, "calc(100% - 16)", 22], "style": "body"},
                                 }}}},
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [140, 80]},
                      "layers": [{"id": "l", "objects": [{
                          "type": "component", "component": "card", "variant": "selected",
                          "box": [10, 10, 100, 50], "title": "Variant Card", "body": "Slot body",
                      }]}]}]}
    rendered = Renderer(doc, ".").render_page(doc["pages"][0])
    svg = "".join(rendered) if isinstance(rendered, list) else rendered
    assert "?component" not in svg
    assert 'fill="#eef6ff"' in svg
    assert 'stroke="#335577"' in svg
    assert 'rx="7"' in svg
    assert "Variant Card" in svg
    assert "Slot body" in svg


def test_z_index_orders_paint_within_a_layer():
    """style.z_index is a paint-order sort key (stable) — not inert CSS."""
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [120, 80]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "rect", "box": [0, 0, 60, 60], "fill": "#aaaaaa",
                           "style": {"z_index": 5}},
                          {"type": "rect", "box": [20, 20, 60, 60], "fill": "#bbbbbb"},
                      ]}]}]}
    svg = Renderer(doc, ".").render_page(doc["pages"][0])[0]
    # the z_index:5 rect must paint AFTER (above) the unindexed rect
    assert svg.index('fill="#bbbbbb"') < svg.index('fill="#aaaaaa"')


def test_z_index_absent_keeps_document_order():
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [120, 80]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "rect", "box": [0, 0, 60, 60], "fill": "#aaaaaa"},
                          {"type": "rect", "box": [20, 20, 60, 60], "fill": "#bbbbbb"},
                      ]}]}]}
    svg = Renderer(doc, ".").render_page(doc["pages"][0])[0]
    assert svg.index('fill="#aaaaaa"') < svg.index('fill="#bbbbbb"')


def test_angular_dimension_renders_arc_and_degree_label():
    """`kind: angular` is model-legal and must render: an arc between the two
    anchor rays (vertex = the object's box origin), arrowheads, and a degree
    label. Convention: `box[0], box[1]` is the vertex; `from`/`to` are points on
    the two rays."""
    body = _render_body({"type": "dimension", "kind": "angular",
                         "box": [40, 60, 0, 0],           # vertex at (40, 60)
                         "from": [100, 60], "to": [40, 10]})
    assert "<path" in body and " A " in body              # the measure arc
    assert "90°" in body                                  # auto-measured right angle
    assert "marker-" in body                              # arrowheads on the arc


def test_angular_dimension_without_vertex_is_reported_not_thrown():
    body = _render_body({"type": "dimension", "kind": "angular",
                         "from": [100, 60], "to": [40, 10]})
    assert not _has_element(body)                          # skipped, but see below
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [120, 80]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "dimension", "kind": "angular",
                           "from": [100, 60], "to": [40, 10]}]}]}]}
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert r.skipped == 1
    assert any(w["kind"] == "dimension_angular_vertex" for w in r.diagnostics["warnings"])


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    box=st.lists(st.floats(min_value=0, max_value=2000, allow_nan=False, allow_infinity=False),
                 min_size=4, max_size=4),
    text=st.text(max_size=80),
)
def test_renderer_never_raises_on_fuzzed_text(box, text):
    _render_body({"type": "text", "box": box, "text": text})  # must not raise


if __name__ == "__main__":
    empty = {t for t, o in OBJECT_SAMPLES.items() if not _has_element(_render_body(o))}
    print("rendered-empty (silent-ignore):", sorted(empty))
    assert empty == UNRENDERED
    print("OK")


def test_angular_dimension_offset_shifts_from_feature_and_zero_is_honored():
    """`offset` is a shift FROM the measured feature (the shorter ray's reach),
    not an absolute radius — and offset=0 must not silently fall back."""
    import re

    def arc_radius(offset):
        obj = {"type": "dimension", "kind": "angular",
               "box": [40, 60, 0, 0], "from": [100, 60], "to": [40, 10]}
        if offset is not None:
            obj["offset"] = offset
        body = _render_body(obj)
        m = re.search(r" A ([0-9.]+) ", body)
        assert m, body
        return float(m.group(1))

    base = arc_radius(None)          # shorter ray = 50 px
    assert abs(base - 50.0) < 1e-6
    assert abs(arc_radius(0) - base) < 1e-6          # falsy zero honored
    assert abs(arc_radius(10) - (base + 10)) < 1e-6  # shift, not absolute
    assert abs(arc_radius(-15) - (base - 15)) < 1e-6


def test_group_children_honor_z_index_paint_order():
    """z_index reorders group children (free placement) the same way it
    reorders a layer's top level — placement untouched, emission sorted."""
    body = _render_body({"type": "group", "box": [0, 0, 100, 100], "children": [
        {"type": "rect", "box": [0, 0, 40, 40], "fill": "#aaaaaa",
         "style": {"z_index": 5}},
        {"type": "rect", "box": [20, 20, 40, 40], "fill": "#bbbbbb"},
    ]})
    assert body.index('fill="#bbbbbb"') < body.index('fill="#aaaaaa"')
