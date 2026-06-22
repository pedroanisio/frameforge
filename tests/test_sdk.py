#!/usr/bin/env python3
"""Public-surface tests for the Python FrameGraph SDK."""
from __future__ import annotations

import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (
    DocumentBuilder,
    ExpandOptions,
    Frame,
    Mat3,
    Path,
    Scene3D,
    Vec2,
    expand,
    md,
    paragraph,
    parse,
    serialize,
    theme,
)
from framegraph.sdk.conform import page_hashes
from framegraph.sdk.geometry import CubicBezier, Mat4, quarter_circle_kappa
from framegraph.sdk.validate import validate_static_rules


def _minimal_doc():
    builder = DocumentBuilder(title="SDK smoke", profile="deck")
    red = builder.define_color("brand_red", "#c00")
    body = builder.define_text_style("body", font_family="sans", font_size=16, color=red)
    page = builder.page("p1", canvas={"size": [320, 180], "units": "px"}, reading_order=["title"])
    page.layer("main").rect([0, 0, 320, 180], fill="#fff").text(
        [24, 24, 180, 32],
        "Hello SDK",
        id="title",
        style=body,
    )
    return builder.build()


def test_builder_lowers_to_authoritative_model():
    doc = _minimal_doc()
    assert doc.dsl == "FrameGraph"
    assert doc.pages[0].layers[0].objects[1].text == "Hello SDK"


def test_parse_serialize_roundtrip_validates():
    doc = _minimal_doc()
    yaml_text = serialize(doc, format="yaml")
    parsed = parse(yaml_text)
    assert parsed.model_dump(by_alias=True, exclude_none=True) == doc.model_dump(
        by_alias=True, exclude_none=True
    )
    json_text = serialize(parsed, format="json")
    assert parse(json_text).title == "SDK smoke"


def test_parse_is_forgiving_by_default_for_future_documents():
    text = """
dsl: FrameGraph
version: 2.2.0
pages:
  - mode: page
    id: p
    layers:
      - id: l
        objects:
          - type: future-node
            box: [0, 0, 10, 10]
"""
    assert isinstance(parse(text), dict)
    with pytest.raises(Exception):
        parse(text, forgiving=False)


def test_validate_static_rules_reports_tooling_warnings():
    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [100, 100], "units": "px"}).layer("main").add(
        {"type": "circle", "center": [10, 10], "r": 5}
    )
    report = validate_static_rules(builder.build())
    assert report.ok
    assert any(issue.rule_id == "deprecated-alias" and issue.path.endswith("/objects/0") for issue in report.issues)


def test_validate_static_rules_reports_structure_errors():
    report = validate_static_rules(
        {
            "dsl": "FrameGraph",
            "version": "2.2.0",
            "pages": [
                {
                    "mode": "page",
                    "id": "p",
                    "layers": [{"id": "l", "objects": [{"type": "text", "box": [0, 0, 10, 10]}]}],
                }
            ],
        }
    )
    assert not report.ok
    assert any(issue.rule_id == "structure" for issue in report.issues)


def test_validate_static_rules_reports_sdk_reference_and_path_errors():
    report = validate_static_rules(
        {
            "dsl": "FrameGraph",
            "version": "2.2.0",
            "targets": [
                {
                    "name": "screen",
                    "canvas": {"size": [100, 100], "units": "px"},
                    "adjustments": {"hide": ["missing"]},
                }
            ],
            "pages": [
                {
                    "mode": "page",
                    "id": "p",
                    "master": "missing-master",
                    "reading_order": ["missing"],
                    "layers": [
                        {
                            "id": "l",
                            "objects": [
                                {"type": "path", "id": "shape", "d": "M 0", "stroke": "#000"},
                                {"type": "image", "box": [0, 0, 10, 10], "src": "missing_asset", "alt": "x"},
                            ],
                        }
                    ],
                }
            ],
        },
        targets=["print"],
    )
    assert not report.ok
    assert {issue.rule_id for issue in report.issues} >= {"reference", "path-data", "target"}


def test_expand_pins_local_assets(tmp_path):
    asset = tmp_path / "asset.txt"
    asset.write_text("payload", encoding="utf-8")
    builder = DocumentBuilder()
    src = builder.define_asset("payload", "asset.txt", kind="data")
    builder.page("p", canvas={"size": [100, 100], "units": "px"}).layer("main").image(
        [0, 0, 10, 10],
        src,
        alt="payload",
    )
    result = expand(builder.build(), opts=ExpandOptions(base_dir=tmp_path))
    data = result.document.model_dump(by_alias=True, exclude_none=True)
    assert result.pinned == ("defs.assets.payload",)
    assert data["defs"]["assets"]["payload"]["hash"].startswith("sha256:")


def test_expand_lowers_symbol_use_to_valid_group():
    doc = {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "defs": {
            "symbols": {
                "card": {
                    "box": [0, 0, 10, 10],
                    "objects": [{"type": "rect", "box": [0, 0, 10, 10], "fill": "$fill"}],
                }
            }
        },
        "pages": [
            {
                "mode": "page",
                "id": "p",
                "layers": [
                    {
                        "id": "l",
                        "objects": [
                            {
                                "type": "use",
                                "symbol": "card",
                                "box": [10, 20, 100, 50],
                                "params": {"fill": "#f00"},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    group = expand(doc, opts=ExpandOptions(pin_assets=False)).document.pages[0].layers[0].objects[0]
    assert group.type == "group"
    assert group.children[0].type == "rect"
    assert group.children[0].box == [10, 20, 100, 50]
    assert group.children[0].fill == "#f00"


def test_builder_symbols_components_and_handle_kind_checks():
    builder = DocumentBuilder()
    symbol = builder.define_symbol(
        "badge",
        box=[0, 0, 10, 10],
        objects=[{"type": "text", "box": [0, 0, 10, 10], "text": "$label"}],
    )
    component = builder.define_component(
        "panel",
        {"fill": "#eee", "internal_layout": {"title": {"box_offset": [4, 4, "100%", 16]}}},
    )
    page = builder.page("p", canvas={"size": [120, 80], "units": "px"})
    page.layer("main").use(symbol, [0, 0, 40, 20], params={"label": "A"}).component(
        component,
        [0, 24, 80, 40],
        title="Title",
    )
    doc = builder.build()
    assert [obj.type for obj in doc.pages[0].layers[0].objects] == ["group", "group"]

    color = builder.define_color("brand", "#c00")
    with pytest.raises(TypeError):
        builder.page("bad", master=color)


def test_geometry_matrix_inverse_and_projection():
    matrix = Mat3.translate(10, 5) @ Mat3.rotate(90) @ Mat3.scale(2)
    point = Vec2(3, 4)
    roundtrip = matrix.inverse().apply(matrix.apply(point))
    assert roundtrip.x == pytest.approx(point.x)
    assert roundtrip.y == pytest.approx(point.y)
    projected = Mat4.isometric().project((1, 1, 1))
    assert math.isfinite(projected.x) and math.isfinite(projected.y)


def test_geometry_bezier_and_path_builder():
    curve = CubicBezier(Vec2(0, 0), Vec2(1, 0), Vec2(1, 1), Vec2(2, 1))
    assert curve.point(0) == Vec2(0, 0)
    assert curve.point(1) == Vec2(2, 1)
    assert quarter_circle_kappa() == pytest.approx(0.5522847498)
    obj = Path().move_to(0, 0).through([(10, 10), (20, 0)]).close().object(stroke="#000")
    assert obj["type"] == "path" and "C " in obj["d"] and obj["d"].endswith("Z")


def test_draw_frame_and_scene3d_lower_to_valid_objects():
    frame = Frame(domain=(1, 0, 100, 10), box=(0, 0, 200, 100), x_scale="log")
    line = frame.polyline([(1, 0), (10, 5), (100, 10)], stroke="#000")
    scene = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=0.5)
    group = scene.render(box=[10, 10, 80, 80])
    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [220, 120], "units": "px"}).layer("main").add(line).add(group)
    doc = builder.build()
    assert doc.pages[0].layers[0].objects[0].type == "polyline"
    assert doc.pages[0].layers[0].objects[1].type == "group"


def test_scene3d_render_children_are_box_local():
    """Regression: Scene3D.render must emit children LOCAL to the group box.

    A renderer translates a group's children by the group box origin, so render()
    must position faces relative to (0,0)-(bw,bh). A prior version baked the box
    origin into the points as well, double-offsetting the projection off-canvas
    (the isometric block rendered blank). It also emitted the deprecated 'polygon'
    alias instead of a canonical closed polyline.
    """
    scene = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=0.5)
    bx, by, bw, bh = 680, 250, 500, 350
    group = scene.render(box=[bx, by, bw, bh])

    assert group["type"] == "group"
    assert group["box"] == [bx, by, bw, bh]

    children = group["children"]
    assert children, "scene produced no faces"
    # canonical closed-polyline form, never the deprecated 'polygon' alias
    assert all(c["type"] == "polyline" and c.get("closed") is True for c in children)

    pts = [p for c in children for p in c["points"]]
    eps = 1e-6
    assert all(-eps <= x <= bw + eps and -eps <= y <= bh + eps for x, y in pts), (
        "Scene3D.render leaked the box origin into child coordinates"
    )
    # the fit must actually consume the box: at least one edge touches a bound
    assert min(x for x, _ in pts) <= eps or min(y for _, y in pts) <= eps


def test_scene3d_render_empty_scene_is_safe():
    """An empty scene still returns a well-formed, validatable group."""
    group = Scene3D().render(box=[10, 20, 100, 80], id="empty")
    assert group["children"] == []
    assert group["box"] == [10, 20, 100, 80]
    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [200, 200], "units": "px"}).layer("main").add(group)
    builder.build()  # must validate


def test_macros_theme_markdown_and_paragraph():
    builder = DocumentBuilder()
    handles = theme(
        builder,
        colors={"ink": "#111"},
        text_styles={"body": {"font_family": "sans", "font_size": 12, "color": "#111"}},
    )
    assert str(handles["ink"]) == "ink"
    spans = md("See [docs](https://example.test), `code`, and $x^2$")
    assert any(isinstance(item, dict) and item.get("kind") == "link" for item in spans)
    flow = paragraph("Use `code` here", style=handles["body"])
    master = builder.define_master(
        "m",
        {"canvas": {"size": [200, 200], "units": "px"}, "regions": [{"id": "body", "box": [0, 0, 200, 200]}]},
    )
    builder.flow("story", master=master, story=[flow])
    assert builder.build().pages[0].story[0].type == "paragraph"


def test_conformance_page_hashes_are_stable():
    hashes = page_hashes(_minimal_doc())
    assert len(hashes) == 1
    assert len(hashes[0]) == 64
