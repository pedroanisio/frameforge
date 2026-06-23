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
    Chart,
    DocumentBuilder,
    ExpandOptions,
    Frame,
    Mat3,
    Path,
    Scene3D,
    Vec2,
    column,
    expand,
    grid,
    inset,
    lorem,
    lorem_paragraphs,
    md,
    paragraph,
    parse,
    row,
    serialize,
    theme,
)
from framegraph.sdk import (
    glow,
    linear_gradient,
    radial_gradient,
    rgba,
    shadow,
    stroke,
)
from framegraph.sdk.conform import page_hashes, render_page_svgs
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


def test_pagebuilder_primitive_helpers_lower_to_canonical_objects():
    """ellipse/circle/polyline/polygon/path builders emit canonical model objects.

    These typed helpers replace the raw ``add({...})`` escape hatch for the
    illustration primitives. ``circle``/``polygon`` must lower to the canonical
    ``ellipse``/closed-``polyline`` forms (never the deprecated aliases), points
    and centres accept ``Vec2`` as well as ``[x, y]``, a ``Path`` builder is
    lowered for you, and ``Handle`` fills are coerced like every other field.
    """
    builder = DocumentBuilder()
    gold = builder.define_color("gold", "#FCC23D")
    page = builder.page("p", canvas={"size": [200, 200], "units": "px"},
                        coordinate_mode="absolute")
    layer = page.layer("art")
    layer.ellipse(Vec2(50, 60), 30, 20, fill=gold)            # Vec2 centre + Handle fill
    layer.circle([100, 100], 25, fill="#fff")                 # lowers to ellipse
    layer.polyline([Vec2(0, 0), (10, 10), (20, 0)], stroke="#000")
    layer.polygon([(0, 0), (40, 0), (20, 30)], fill="#abc")   # lowers to closed polyline
    layer.path("M 0 0 L 10 10", stroke="#000")
    layer.path(Path().move_to(0, 0).through([(5, 5), (10, 0)]), fill="none", stroke="#111")

    doc = builder.build()                                     # validates against the model
    objs = doc.pages[0].layers[0].objects
    assert [o.type for o in objs] == [
        "ellipse", "ellipse", "polyline", "polyline", "path", "path",
    ]
    # Vec2 centre coerced to a plain point; Handle fill coerced to its token name
    assert objs[0].center == [50.0, 60.0] and objs[0].fill == "gold"
    # circle() lowered to a canonical ellipse with rx == ry == r
    assert objs[1].rx == 25 and objs[1].ry == 25
    # Vec2/tuple points normalised; polygon() lowered to a *closed* polyline
    assert objs[2].points == [[0.0, 0.0], [10.0, 10.0], [20.0, 0.0]]
    assert objs[3].closed is True
    # a geometry.Path lowered to a real SVG path (cubic segments from Catmull-Rom)
    assert objs[5].type == "path" and "C " in objs[5].d

    # The canonical lowerings must NOT trip the deprecated-alias rule that raw
    # `circle`/`polygon`/`curve` object types do (cf.
    # test_validate_static_rules_reports_tooling_warnings).
    report = validate_static_rules(doc)
    assert report.ok
    assert not any(issue.rule_id == "deprecated-alias" for issue in report.issues)


def test_pagebuilder_arrow_lowers_to_shortened_shaft_and_head():
    """arrow() emits a shaft line + a filled closed-polyline head at the tip.

    Replaces the hand-rolled vline+triangle pattern (whose manual head placement
    produced the page-08 free-body bug). The shaft must stop short of the tip and
    the head must close on the end point, both in the arrow colour.
    """
    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [100, 100], "units": "px"}).layer("main").arrow(
        [10, 10], [10, 90], color="#cc0000", width=2, head=12)
    doc = builder.build()
    shaft, head = doc.pages[0].layers[0].objects
    dump = doc.model_dump(by_alias=True, exclude_none=True)
    shaft_d, head_d = dump["pages"][0]["layers"][0]["objects"]

    assert shaft.type == "line" and head.type == "polyline"
    assert head.closed is True and head.fill == "#cc0000"
    # the shaft stops at the arrowhead base, short of the 90px tip
    assert shaft_d["to"] == [10.0, 78.0]
    # the head's first vertex is the tip (the end point)
    assert head.points[0] == [10.0, 90.0]
    # the head is symmetric about the shaft (±head_width on the perpendicular)
    assert sorted(p[0] for p in head.points[1:]) == pytest.approx([10.0 - 7.2, 10.0 + 7.2])


def test_paint_rgba_and_gradient_constructors_lower_to_valid_paint():
    """rgba()/linear_gradient()/radial_gradient() build the model's Paint forms."""
    assert rgba("#9DE9FF", 0.4) == "rgba(157,233,255,0.4)"
    assert rgba("#fff", 1) == "rgba(255,255,255,1)"          # short hex expands
    assert rgba("#000000", 2) == "rgba(0,0,0,1)"             # alpha clamped to [0,1]

    lg = linear_gradient([("#1B1B3A", 0.0), ("#7C5C8E", 1.0)], angle=180)
    assert lg == {"kind": "linear", "angle": 180,
                  "stops": [{"color": "#1B1B3A", "position": "0%"},
                            {"color": "#7C5C8E", "position": "100%"}]}
    # bare colours auto-distribute their stop positions
    assert [s["position"] for s in linear_gradient(["#a", "#b", "#c"])["stops"]] == \
        ["0%", "50%", "100%"]
    rg = radial_gradient([("#FFF7D8", 0.0), (rgba("#FFF7D8", 0.0), 1.0)], at="50% 40%")
    assert rg["kind"] == "radial" and rg["at"] == "50% 40%"

    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [200, 200], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    layer.rect([0, 0, 200, 200], fill=lg)
    layer.ellipse([100, 100], 60, 60, fill=rg)
    doc = builder.build()
    assert doc.pages[0].layers[0].objects[0].fill.kind == "linear"
    assert doc.pages[0].layers[0].objects[1].fill.kind == "radial"


def test_paint_stroke_and_effect_constructors_lower_to_model_fields():
    """stroke()/shadow()/glow() and the latent opacity/rotation fields lower cleanly."""
    assert stroke(3, color="#E8743B", cap="round", dash=[4, 8]) == {
        "stroke": "#E8743B",
        "stroke_style": {"stroke_width": 3, "stroke_linecap": "round",
                         "stroke_dasharray": [4, 8]},
    }
    assert "stroke" not in stroke(2, cap="round")             # geometry-only is valid (P3)

    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [200, 200], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    layer.path(Path().move_to(0, 0).line_to(10, 10), **stroke(2, color="#000", cap="round"))
    layer.rect([10, 10, 50, 50], fill="#eee", opacity=0.8, rotation=12,
               shadow=shadow(dy=4, blur=6, color="#06243C", opacity=0.5),
               glow=glow(blur=8, color="#9DE9FF"))
    doc = builder.build()
    rect = doc.pages[0].layers[0].objects[1]
    assert rect.opacity == 0.8 and rect.rotation == 12
    assert rect.shadow.dy == 4 and rect.shadow.blur == 6
    assert rect.glow.blur == 8 and rect.glow.dx is None       # a glow is a blur, not offset


def test_pagebuilder_frame_emits_a_transformed_group_in_local_coordinates():
    """layer.frame() collects local-coordinate primitives into one transformed group."""
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [400, 400], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    with layer.frame(100, 50, scale=2.0, flip=-1) as f:
        f.circle([0, 0], 10, fill="#f00")                     # authored at the origin
        f.rect([5, 5, 20, 10], fill="#0f0")
    doc = builder.build()
    objs = doc.pages[0].layers[0].objects
    assert len(objs) == 1
    grp = objs[0]
    assert grp.type == "group" and grp.box is None            # no box → pure matrix origin
    # children are untouched local coordinates; the group transform places them
    assert grp.children[0].type == "ellipse" and grp.children[0].center == [0.0, 0.0]
    assert [c.type for c in grp.children] == ["ellipse", "rect"]
    fns = grp.style.transform
    assert len(fns) == 1 and fns[0].fn == "matrix"
    a_, b_, c_, d_, e_, f_ = fns[0].args
    # translate(100,50) ∘ scale(flip*2, 2): a=-2, d=2, e=100, f=50
    assert (a_, b_, c_, d_, e_, f_) == (-2.0, 0.0, 0.0, 2.0, 100.0, 50.0)


def test_frame_nests_composes_and_is_safe_when_empty():
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [200, 200], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    with layer.frame(10, 10) as f:
        with f.frame(5, 5, scale=2) as g:
            g.rect([0, 0, 4, 4], fill="#000")
    with layer.frame(0, 0):                                   # empty frame
        pass
    doc = builder.build()
    objs = doc.pages[0].layers[0].objects
    assert objs[0].type == "group" and objs[0].children[0].type == "group"
    assert objs[0].children[0].children[0].type == "rect"     # nested transform composes
    assert objs[1].children == []                             # empty frame → empty valid group


def test_frame_transform_renders_as_an_svg_matrix():
    """Honest-scope check: the transform actually reaches the proxy SVG output."""
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [200, 200], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    with layer.frame(100, 100, scale=1.5, rotate=30) as f:
        f.circle([0, 0], 20, fill="#abc")
    svg = render_page_svgs(builder.build(), base_dir=ROOT)[0]
    assert "matrix(" in svg


def test_group_accepts_a_mat3_transform_directly():
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [100, 100], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    layer.group([{"type": "rect", "box": [0, 0, 10, 10], "fill": "#000"}],
                transform=Mat3.rotate(90))
    grp = builder.build().pages[0].layers[0].objects[0]
    assert grp.style.transform[0].fn == "matrix"


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


def test_page_coordinate_mode_is_set_and_validated():
    builder = DocumentBuilder()
    builder.page(
        "p", canvas={"size": [100, 100], "units": "px"}, coordinate_mode="absolute"
    ).layer("main").rect([0, 0, 10, 10], fill="#fff")
    doc = builder.build()
    assert doc.pages[0].rendering.coordinate_mode == "absolute"

    bad = DocumentBuilder()
    bad.page(
        "p", canvas={"size": [100, 100], "units": "px"}, coordinate_mode="sideways"
    ).layer("main").rect([0, 0, 10, 10], fill="#fff")
    with pytest.raises(Exception):
        bad.build()


def test_layout_row_and_column_tile_the_box():
    boxes = row([0, 0, 100, 40], 4, gap=4)
    assert len(boxes) == 4
    assert all(b[2] == pytest.approx((100 - 3 * 4) / 4) for b in boxes)
    assert boxes[0][0] == 0
    assert boxes[-1][0] + boxes[-1][2] == pytest.approx(100)  # exact fill, no drift

    col = column([0, 0, 50, 90], weights=[2, 1])
    assert col[0][3] == pytest.approx(60)
    assert col[1][3] == pytest.approx(30)
    assert col[1][1] == pytest.approx(60)  # second box starts where the first ends


def test_layout_grid_wraps_and_inset_shrinks():
    cells = grid([0, 0, 100, 100], cols=2, count=3, gap=10)
    assert len(cells) == 3
    assert cells[0][2] == pytest.approx(45) and cells[0][3] == pytest.approx(45)
    assert cells[2][0] == pytest.approx(0) and cells[2][1] == pytest.approx(55)  # wraps to row 2

    assert inset([0, 0, 100, 100], [10, 20]) == [20, 10, 60, 80]  # [vertical, horizontal]


def test_layout_input_validation():
    with pytest.raises(ValueError):
        row([0, 0, 10, 10])  # neither count nor weights
    with pytest.raises(ValueError):
        grid([0, 0, 10, 10], cols=2)  # neither rows nor count
    with pytest.raises(ValueError):
        grid([0, 0, 10, 10], cols=0, count=1)


def test_chart_lowers_to_valid_objects():
    frame = Frame(domain=(0, 0, 10, 100), box=(100, 100, 400, 200))
    chart = (
        Chart(frame)
        .axes(x_ticks=[0, 5, 10], y_ticks=[0, 50, 100], grid=True)
        .line([(0, 0), (5, 50), (10, 100)], stroke="#1133AA", width=2, label="series")
        .bars([(2, 30), (8, 80)], fill="#AA1133")
        .marker(5, 50, fill="#11AA33")
        .legend()
    )
    objs = chart.objects()
    assert {"line", "polyline", "rect", "text", "ellipse"} <= {o["type"] for o in objs}
    # every emitted object lowers into a valid document via the new extend() helper
    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [640, 440], "units": "px"}).layer("main").extend(objs)
    builder.build()


def test_chart_smooth_series_emits_path_inside_plot():
    frame = Frame(domain=(0, 0, 10, 10), box=(0, 0, 100, 100))
    chart = Chart(frame).line([(0, 0), (5, 5), (10, 10)], smooth=True)
    paths = [o for o in chart.objects() if o["type"] == "path"]
    assert len(paths) == 1 and paths[0]["d"].startswith("M ")


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


def test_macros_lorem_is_deterministic_and_shaped():
    # default: canonical opening, deterministic, sentence-terminated
    text = lorem()
    assert text.startswith("Lorem ipsum dolor sit amet")
    assert text == lorem(), "lorem() must be deterministic (no RNG)"
    assert text.endswith(".")

    # words mode returns exactly N words as one capitalised sentence
    five = lorem(words=5)
    assert five == "Lorem ipsum dolor sit amet."
    assert len(lorem(words=12, start=False).rstrip(".").split()) == 12

    # sentence count is honoured
    assert lorem(sentences=3).count(".") == 3

    # offset rotates the stream; paragraphs differ but only the first opens canonically
    paras = lorem_paragraphs(3, sentences=2)
    assert len(paras) == 3
    assert paras[0].startswith("Lorem ipsum")
    assert not paras[1].startswith("Lorem ipsum")
    assert paras[1] != paras[2]

    # usable as flow paragraph text via the existing macro
    flow = paragraph(lorem(words=8))
    assert flow["type"] == "paragraph" and flow["text"].endswith(".")


def test_conformance_page_hashes_are_stable():
    hashes = page_hashes(_minimal_doc())
    assert len(hashes) == 1
    assert len(hashes[0]) == 64
