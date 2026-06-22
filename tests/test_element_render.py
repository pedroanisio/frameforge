#!/usr/bin/env python3
"""
test_element_render.py — render-side coverage of every visual element, and the
SILENT-IGNORE GATE.

For each visual object type we render a minimal sample and check its SVG
footprint. The key assertion is `test_no_unexpected_silent_ignores`: the set of
elements that render to NOTHING must equal the documented `UNRENDERED` allowlist.
So:
  * a new element type that the proxy silently drops -> FAILS (no silent ignore),
  * and if `curve`/`bezier`/`dimension` ever gain a painter, the test forces us to
    remove them from the allowlist (the gap is tracked, never assumed-met).

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
}

# the SVG primitive each painted element must emit
EXPECT = {
    "rect": "<rect", "ellipse": "<ellipse", "circle": "<circle", "line": "<line",
    "polyline": "<polyline", "polygon": "<polygon", "path": "<path", "text": "<text",
    "icon": "<text", "bullet_list": "<text", "image": "<rect", "table": "<rect", "group": "<g",
}

# documented silent-ignore set: deprecated aliases + the composite dimension have no
# painter in the proxy yet. Any change here must be deliberate (this is the gate).
UNRENDERED = {"curve", "bezier", "dimension"}


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


def test_no_unexpected_silent_ignores():
    """The whole point: the empirically-empty set must equal the declared allowlist."""
    empty = {t for t, o in OBJECT_SAMPLES.items() if not _has_element(_render_body(o))}
    assert empty == UNRENDERED, (
        f"silent-ignore set changed: rendered-empty={sorted(empty)}, declared={sorted(UNRENDERED)}. "
        "Implement a painter, or update UNRENDERED deliberately.")


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
