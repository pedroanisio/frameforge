"""Unified per-object stacking: ObjBase.z ⇄ Style.z_index contract (one key).

The drift these pin (found 2026-07-27): the model declares TWO per-object
stacking controls — `ObjBase.z` ("Stacking order within the layer") and
`Style.z_index` ("Stacking order within the parent") — and each backend honored
a different one: the SVG renderer sorted siblings only by `style.z_index`
(`ObjBase.z` was dead), the pdf-tex `FigureTikz` walker sorted only by `o["z"]`
(masked because "document order already matches z in the fixtures"), and the
HTML backend emitted objects in raw document order.

Contract now: ONE effective key, `effective_z` — object `z` wins over
`style.z_index`, default 0.0, stable sort (equal keys keep document order) —
honored at every paint-order site in every backend; declaring both with
different values SCREAMS (`z_conflict` warning), never silently prefers.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # evict a models-module shadow
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.stacking import effective_z  # noqa: E402
from frameforge.rendering.infrastructure.backends import html as html_backend  # noqa: E402
from frameforge.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402
from tooling.render_fixtures import Renderer  # noqa: E402

RED, BLUE = "#ff0000", "#0000ff"


# --------------------------------------------------------------------------- #
#  The shared key (pure domain function)                                       #
# --------------------------------------------------------------------------- #
def test_effective_z_object_field_alone():
    assert effective_z({"z": 3}, {}) == 3.0


def test_effective_z_style_zindex_alone():
    assert effective_z({}, {"z_index": 2}) == 2.0


def test_effective_z_object_wins_over_style():
    assert effective_z({"z": 1}, {"z_index": 5}) == 1.0


def test_effective_z_defaults_to_zero():
    assert effective_z({}, {}) == 0.0
    assert effective_z({"z": None}, {"z_index": None}) == 0.0


def test_effective_z_coerces_numeric_strings():
    # raw-dict path: YAML/JSON hand-edits may stringify numbers
    assert effective_z({"z": "2"}, {}) == 2.0


# --------------------------------------------------------------------------- #
#  SVG renderer (the primary backend — ObjBase.z was dead here)                #
# --------------------------------------------------------------------------- #
def _svg(objects):
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [100, 100], "units": "px"},
        "layers": [{"id": "l", "objects": objects}],
    }]}
    r = Renderer(doc, ".")
    return "".join(r.render_page(doc["pages"][0])), r.diagnostics


def _rect(oid, fill, **extra):
    return {"type": "rect", "id": oid, "box": [10, 10, 50, 50], "fill": fill, **extra}


def test_svg_object_z_inverts_document_order():
    svg, _ = _svg([_rect("r1", RED, z=2), _rect("r2", BLUE, z=1)])
    assert svg.index(BLUE) < svg.index(RED)          # lower z paints first


def test_svg_style_zindex_still_inverts_document_order():
    svg, _ = _svg([_rect("r1", RED, style={"z_index": 2}),
                   _rect("r2", BLUE, style={"z_index": 1})])
    assert svg.index(BLUE) < svg.index(RED)


def test_svg_no_stacking_fields_keeps_document_order_bytes():
    a, _ = _svg([_rect("r1", RED), _rect("r2", BLUE)])
    assert a.index(RED) < a.index(BLUE)


def test_svg_conflict_object_z_wins_and_screams():
    svg, diags = _svg([_rect("r1", RED, z=1, style={"z_index": 5}),
                       _rect("r2", BLUE, z=2)])
    assert svg.index(RED) < svg.index(BLUE)          # z=1 vs z=2 — z_index=5 ignored
    conflicts = [w for w in diags["warnings"] if w["kind"] == "z_conflict"]
    assert len(conflicts) == 1
    assert conflicts[0]["id"] == "r1"
    assert conflicts[0]["z"] == 1 and conflicts[0]["z_index"] == 5


def test_svg_equal_z_and_zindex_is_not_a_conflict():
    _, diags = _svg([_rect("r1", RED, z=2, style={"z_index": 2})])
    assert not [w for w in diags["warnings"] if w["kind"] == "z_conflict"]


def test_svg_group_children_honor_object_z():
    group = {"type": "group", "id": "g", "box": [0, 0, 100, 100], "children": [
        _rect("c1", RED, z=2), _rect("c2", BLUE, z=1)]}
    svg, _ = _svg([group])
    assert svg.index(BLUE) < svg.index(RED)


# --------------------------------------------------------------------------- #
#  pdf-tex FigureTikz walker (honored only `z`; gains the z_index fallback)    #
# --------------------------------------------------------------------------- #
def test_figuretikz_children_honor_style_zindex_fallback():
    ft = FigureTikz(lambda v: v, None)
    kids = ft._children([{"id": "a", "style": {"z_index": 5}}, {"id": "b"}])
    assert [k["id"] for k in kids] == ["b", "a"]


def test_figuretikz_children_object_z_still_wins():
    ft = FigureTikz(lambda v: v, None)
    kids = ft._children([{"id": "a", "z": 1, "style": {"z_index": 9}},
                        {"id": "b", "z": 0}])
    assert [k["id"] for k in kids] == ["b", "a"]


def test_figuretikz_children_stable_without_fields():
    ft = FigureTikz(lambda v: v, None)
    kids = ft._children([{"id": "a"}, {"id": "b"}, {"id": "c"}])
    assert [k["id"] for k in kids] == ["a", "b", "c"]


# --------------------------------------------------------------------------- #
#  HTML backend (emitted raw document order — FR4 audit says: fix emission)    #
# --------------------------------------------------------------------------- #
def _html(objects):
    page = {"mode": "page", "id": "p", "canvas": {"size": [100, 100], "units": "px"},
            "layers": [{"id": "l", "objects": objects}]}
    return html_backend.render_page(page, html_backend.Tokens({}), 0)


def test_html_object_z_inverts_document_order():
    out = _html([_rect("r1", RED, z=2), _rect("r2", BLUE, z=1)])
    assert out.index(BLUE) < out.index(RED)


def test_html_style_zindex_inverts_document_order():
    out = _html([_rect("r1", RED, style={"z_index": 2}),
                 _rect("r2", BLUE, style={"z_index": 1})])
    assert out.index(BLUE) < out.index(RED)


def test_html_no_fields_keeps_document_order():
    out = _html([_rect("r1", RED), _rect("r2", BLUE)])
    assert out.index(RED) < out.index(BLUE)


def test_html_group_children_honor_object_z():
    group = {"type": "group", "id": "g", "box": [0, 0, 100, 100], "children": [
        _rect("c1", RED, z=2), _rect("c2", BLUE, z=1)]}
    out = _html([group])
    assert out.index(BLUE) < out.index(RED)
