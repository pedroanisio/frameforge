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

Renderer-only (no models import): the `framegraph` package must resolve to the
rendering package here, so we evict a models-module shadow first — mirror of the
guard in test_head.py / test_rendering_svg_semantics.py.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # a non-package (the models module)
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

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
    "component": {"type": "component", "box": [0, 0, 110, 50], "title": "Card", "body": "Body", "fill": "#fff"},
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
}

# the SVG primitive each painted element must emit
EXPECT = {
    "rect": "<rect", "ellipse": "<ellipse", "circle": "<circle", "line": "<line",
    "polyline": "<polyline", "polygon": "<polygon", "path": "<path",
    "curve": "<path", "bezier": "<path", "text": "<text",
    "icon": "<text", "bullet_list": "<text", "dimension": "<g",
    "image": "<rect", "table": "<rect", "group": "<g", "component": "<rect",
    "chip_row": "<rect", "uml.marker_glyph": "<polygon",
    "uml.classifier_box": "<rect", "uml.component_box": "<rect",
    "uml.state_box": "<rect", "uml.action": "<rect", "uml.artifact_box": "<rect",
    "uml.node_box": "<rect",
}

# documented silent-ignore set. Any change here must be deliberate (this is the gate).
UNRENDERED = set()


def _render_body(obj):
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
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
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
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
