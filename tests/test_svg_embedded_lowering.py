#!/usr/bin/env python3
"""Embedded-SVG ingestion + document-level lowering (promoted from tooling).

Two promoted capabilities, pinned here:

  1. ``svg_to_objects`` accepts ``data:image/svg+xml`` URIs (plain, URL-encoded,
     and base64 payloads) in addition to SVG text and ``.svg`` paths, so any
     embedded asset is ingestible without hand-decoding.
  2. ``lower_embedded_svg`` walks a document and replaces each ``type: image``
     object whose source is an embedded SVG with a ``group`` of native objects
     fitted into the image's box — stable ids, ``meta.region`` provenance —
     unlocking the whole native surface (recolor, design_audit, planar,
     effects) for detail previously trapped inside opaque image blobs.

Why: detail inside embedded images is invisible to every object-level tool;
tooling/hyperrealistic_canvas.py hand-rolled both halves as a workaround.
"""
from __future__ import annotations

import base64
import copy
import os
import sys
import urllib.parse

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.model import Document  # noqa: E402
from frameforge.sdk import lower_embedded_svg, svg_to_objects  # noqa: E402


SVG = '<svg viewBox="0 0 10 10"><circle cx="5" cy="6" r="3" fill="#abc"/></svg>'
SVG_TWO = ('<svg viewBox="0 0 10 10">'
           '<rect x="1" y="2" width="4" height="6" fill="#0f0"/>'
           '<polygon points="0,0 5,0 5,5" fill="#222"/></svg>')


def _uri_plain(svg: str) -> str:
    return "data:image/svg+xml," + svg


def _uri_quoted(svg: str) -> str:
    return "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg)


def _uri_b64(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _doc(objects, defs=None) -> dict:
    doc = {
        "dsl": "FrameForge",
        "version": "2.3.0",
        "pages": [{
            "mode": "page", "id": "p1",
            "layers": [{"id": "art", "objects": objects}],
        }],
    }
    if defs:
        doc["defs"] = defs
    return doc


# --- 1. svg_to_objects accepts data:image/svg+xml URIs ------------------- #
def test_data_uri_plain_ingests():
    objs = svg_to_objects(_uri_plain(SVG))
    assert len(objs) == 1
    o = objs[0]
    assert o["type"] == "ellipse" and o["center"] == [5.0, 6.0] and o["fill"] == "#abc"


def test_data_uri_urlencoded_ingests():
    objs = svg_to_objects(_uri_quoted(SVG))
    assert objs[0]["type"] == "ellipse" and objs[0]["fill"] == "#abc"


def test_data_uri_base64_ingests():
    objs = svg_to_objects(_uri_b64(SVG))
    assert objs[0]["type"] == "ellipse" and objs[0]["fill"] == "#abc"


def test_data_uri_boxfit_transform_applies():
    objs = svg_to_objects(_uri_plain(SVG), box=[100, 200, 20, 20])
    tr = objs[0].get("style", {}).get("transform", "")
    assert "translate(100" in tr and "scale(2" in tr


def test_data_uri_bad_payload_raises_actionable():
    with pytest.raises(ValueError, match="data:image/svg\\+xml"):
        svg_to_objects("data:image/svg+xml;base64,@@not-base64@@")


def test_non_svg_data_uri_raises_actionable():
    with pytest.raises(ValueError, match="image/svg\\+xml"):
        svg_to_objects("data:image/png;base64,iVBORw0KGgo=")


# --- 2. lower_embedded_svg: document-level lowering ----------------------- #
def test_lower_replaces_image_with_fitted_group():
    img = {"type": "image", "id": "hero", "box": [50, 60, 20, 20],
           "src": _uri_plain(SVG), "alt": "a circle"}
    out = lower_embedded_svg(_doc([img]))
    (obj,) = out["pages"][0]["layers"][0]["objects"]
    assert obj["type"] == "group"
    assert obj["id"] == "hero"                       # id is stable
    assert obj["box"] == [50, 60, 20, 20]            # placement is preserved
    (child,) = obj["children"]
    assert child["type"] == "ellipse"
    assert child["id"] == "hero.0"
    # children are fitted PARENT-RELATIVE ([0,0,w,h]); the group box translates
    tr = child.get("style", {}).get("transform", "")
    assert "translate(0" in tr and "scale(2" in tr
    # provenance rides on meta.region
    assert obj["meta"]["region"]["source"] == "image"
    assert obj["meta"]["region"]["alt"] == "a circle"
    assert child["meta"]["region"]["source_layer"] == "hero"
    assert child["meta"]["region"]["source_index"] == 0


def test_lower_carries_obj_base_fields_onto_group():
    img = {"type": "image", "id": "hero", "box": [0, 0, 10, 10],
           "src": _uri_plain(SVG), "z": 7, "opacity": 0.5}
    (obj,) = lower_embedded_svg(_doc([img]))["pages"][0]["layers"][0]["objects"]
    assert obj["z"] == 7 and obj["opacity"] == 0.5


def test_lower_generates_stable_id_when_missing():
    imgs = [{"type": "image", "box": [0, 0, 10, 10], "src": _uri_plain(SVG)},
            {"type": "image", "box": [10, 0, 10, 10], "src": _uri_b64(SVG)}]
    objs = lower_embedded_svg(_doc(imgs))["pages"][0]["layers"][0]["objects"]
    assert [o["id"] for o in objs] == ["region.0", "region.1"]
    assert objs[0]["children"][0]["id"] == "region.0.0"


def test_lower_leaves_non_svg_images_untouched():
    keep = [
        {"type": "image", "id": "png", "box": [0, 0, 5, 5],
         "src": "data:image/png;base64,iVBORw0KGgo="},
        {"type": "image", "id": "file", "box": [0, 0, 5, 5], "src": "logo.svg"},
        {"type": "image", "id": "ph", "box": [0, 0, 5, 5],
         "src": _uri_plain(SVG), "placeholder": True},
    ]
    out = lower_embedded_svg(_doc(copy.deepcopy(keep)))
    assert out["pages"][0]["layers"][0]["objects"] == keep


def test_lower_leaves_undrawable_svg_untouched():
    empty = {"type": "image", "id": "e", "box": [0, 0, 5, 5],
             "src": _uri_plain('<svg viewBox="0 0 10 10"><defs/></svg>')}
    (obj,) = lower_embedded_svg(_doc([empty]))["pages"][0]["layers"][0]["objects"]
    assert obj["type"] == "image"


def test_lower_resolves_defs_assets_indirection():
    defs = {"assets": {"art": {"src": _uri_b64(SVG), "kind": "image",
                               "media_type": "image/svg+xml"}}}
    img = {"type": "image", "id": "hero", "box": [0, 0, 10, 10], "src": "art"}
    (obj,) = lower_embedded_svg(_doc([img], defs=defs))["pages"][0]["layers"][0]["objects"]
    assert obj["type"] == "group" and obj["children"][0]["type"] == "ellipse"


def test_lower_walks_nested_groups():
    img = {"type": "image", "id": "deep", "box": [0, 0, 10, 10], "src": _uri_plain(SVG)}
    grp = {"type": "group", "id": "wrap", "box": [5, 5, 40, 40], "children": [img]}
    out = lower_embedded_svg(_doc([grp]))
    inner = out["pages"][0]["layers"][0]["objects"][0]["children"][0]
    assert inner["type"] == "group" and inner["id"] == "deep"


def test_lower_is_pure():
    img = {"type": "image", "id": "hero", "box": [0, 0, 10, 10], "src": _uri_plain(SVG)}
    doc = _doc([img])
    before = copy.deepcopy(doc)
    lower_embedded_svg(doc)
    assert doc == before


def test_lower_multi_object_svg_keeps_paint_order():
    img = {"type": "image", "id": "multi", "box": [0, 0, 20, 20], "src": _uri_plain(SVG_TWO)}
    (obj,) = lower_embedded_svg(_doc([img]))["pages"][0]["layers"][0]["objects"]
    kinds = [c["type"] for c in obj["children"]]
    assert kinds == ["rect", "polygon"]
    assert [c["id"] for c in obj["children"]] == ["multi.0", "multi.1"]


# --- integration: the lowered document is a valid, renderable Document ----- #
def test_lowered_document_validates():
    img = {"type": "image", "id": "hero", "box": [50, 60, 20, 20],
           "src": _uri_plain(SVG_TWO), "alt": "art"}
    out = lower_embedded_svg(_doc([img]))
    Document.model_validate(out)  # must not raise


def test_lowered_document_renders_native_objects():
    from tooling.render_fixtures import Renderer
    img = {"type": "image", "id": "hero", "box": [50, 60, 20, 20],
           "src": _uri_plain(SVG), "alt": "art"}
    out = lower_embedded_svg(_doc([img]))
    svg = "".join(Renderer(out, ROOT).render_page(out["pages"][0]))
    assert "<ellipse" in svg and "image/svg+xml" not in svg


# --- integration: the capability is reachable through the MCP surface ------ #
MCP_SCRIPT = """
import yaml
from frameforge.sdk import DocumentBuilder, lower_embedded_svg, serialize

doc = DocumentBuilder(title="Lowering Probe", profile="diagram")
page = doc.page("p1", canvas={"size": [320, 180], "units": "px"})
page.layer("main").image(
    [40, 30, 100, 100],
    "%s",
    id="hero", alt="embedded circle")
lowered = lower_embedded_svg(yaml.safe_load(serialize(doc.build())))
with open(OUTPUT_YAML_PATH, "w", encoding="utf-8") as fh:
    fh.write(serialize(lowered))
""" % _uri_quoted(SVG)  # URL-encoded payload: no quote chars inside the literal


def test_lowering_reachable_via_mcp_run_sdk_code(tmp_path):
    from frameforge.mcp.server import run_sdk_code
    result = run_sdk_code(MCP_SCRIPT, session_id="lower1",
                          session_root=tmp_path, raster_png=False)
    assert result["ok"] is True
    svg_text = (tmp_path / "lower1" / "page-001.svg").read_text(encoding="utf-8")
    assert "<ellipse" in svg_text and "image/svg+xml" not in svg_text
