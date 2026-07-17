#!/usr/bin/env python3
"""Public-surface tests for the Python FrameForge SDK."""
from __future__ import annotations

import importlib
import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (
    Chart,
    Box,
    DocumentBuilder,
    ExpandOptions,
    Frame,
    Material,
    Mat3,
    Path,
    Scene3D,
    Vec2,
    Vec3,
    column,
    greeble,
    expand,
    grid,
    grid_lines,
    hatch_fill,
    inset,
    lorem,
    lorem_paragraphs,
    md,
    paragraph,
    parse,
    row,
    serialize,
    sparkline,
    theme,
)
from frameforge.sdk import (
    appearance,
    blur_filter,
    conic_gradient,
    diffuse_lighting,
    displacement_map,
    dots,
    effect,
    effect_stack,
    effects,
    fill_stroke,
    filter_chain,
    grid_pattern,
    glow,
    hatch,
    linear_gradient,
    neon,
    pattern,
    radial_gradient,
    rgba,
    shadow,
    soft_shadow,
    stroke,
    style_effects,
    specular_lighting,
    text_style,
    turbulence,
)
from frameforge.sdk import (
    Panel,
    avatar,
    badge,
    badge_width,
    button,
    card,
    default_theme,
    divider,
    field,
    kpi,
    pill,
    progress,
    register_theme,
    table,
    tabs,
    toggle,
)
from frameforge.sdk.conform import page_hashes, render_page_svgs
from frameforge.sdk.geometry import CubicBezier, Mat4, quarter_circle_kappa
from frameforge.sdk.validate import validate_static_rules


def test_top_level_sdk_reexports_module_public_surface():
    import frameforge.sdk as sdk

    modules = [
        "author",
        "chart",
        "clip",
        "conform",
        "draw",
        "expand",
        "fields",
        "figure",
        "flow",
        "geometry",
        "io",
        "lattices",
        "layout",
        "macros",
        "manifold",
        "metrics",
        "model",
        "paint",
        "topology",
        "validate",
        "widgets",
    ]
    missing: list[str] = []
    for module_name in modules:
        module = importlib.import_module(f"frameforge.sdk.{module_name}")
        for name in getattr(module, "__all__", ()):
            if name not in sdk.__all__ or not hasattr(sdk, name):
                missing.append(f"{module_name}.{name}")

    assert missing == []


def test_group_a_paint_helpers_expose_model_native_filters_and_appearance():
    conic = conic_gradient([("#111111", 0), ("#eeeeee", "75%")], at=[50, 50], from_angle=45)
    assert conic == {
        "kind": "conic",
        "stops": [{"color": "#111111", "position": "0%"}, {"color": "#eeeeee", "position": "75%"}],
        "at": [50, 50],
        "from": 45,
    }

    filters = filter_chain(
        blur_filter("3px"),
        turbulence(base_frequency=[0.03, 0.08], num_octaves=3, seed=7, type="fractalNoise"),
        displacement_map(scale=12, x_channel="R", y_channel="G"),
        diffuse_lighting(surface_scale=2, lighting_color="#ffeeaa", azimuth=45, elevation=60),
        specular_lighting(surface_scale=3, specular_constant=0.8, specular_exponent=12),
    )
    assert filters[0] == {"fn": "blur", "value": "3px"}
    assert filters[1]["fn"] == "turbulence"
    assert filters[1]["seed"] == 7
    assert filters[2]["fn"] == "displacement_map"
    assert filters[3]["fn"] == "diffuse_lighting"
    assert filters[4]["fn"] == "specular_lighting"

    assert style_effects(
        filter=filters,
        backdrop_filter=filter_chain(blur_filter(8)),
        mix_blend_mode="multiply",
        isolation="isolate",
    ) == {
        "style": {
            "filter": filters,
            "backdrop_filter": [{"fn": "blur", "value": 8}],
            "mix_blend_mode": "multiply",
            "isolation": "isolate",
        }
    }

    assert effect_stack(effect("shadow", dx=2, dy=4), effect("glow", blur=9)) == {
        "effects": [{"kind": "shadow", "dx": 2, "dy": 4}, {"kind": "glow", "blur": 9}]
    }
    assert appearance({"fill": "#111111"}, {"stroke": "#eeeeee", "opacity": 0.5}) == {
        "appearance": [{"fill": "#111111"}, {"stroke": "#eeeeee", "opacity": 0.5}]
    }


def test_text_style_exposes_variable_font_and_opentype_fields():
    assert text_style(
        16,
        family="Inter Variable",
        feature_settings='"liga" 1, "kern" 1',
        variation_settings='"wght" 650, "opsz" 18',
        variant_caps="small-caps",
        variant_numeric="tabular-nums",
        variant_ligatures="common-ligatures",
        font_variant="small-caps tabular-nums",
    ) == {
        "font_size": 16,
        "font_family": "Inter Variable",
        "font_feature_settings": '"liga" 1, "kern" 1',
        "font_variation_settings": '"wght" 650, "opsz" 18',
        "font_variant_caps": "small-caps",
        "font_variant_numeric": "tabular-nums",
        "font_variant_ligatures": "common-ligatures",
        "font_variant": "small-caps tabular-nums",
    }


def test_page_builder_curve_exposes_cubic_bezier_without_path_detour():
    builder = DocumentBuilder(title="curve", profile="diagram")
    page = builder.page("p", canvas={"size": [160, 120], "units": "px"}).layer("main")
    page.curve([10, 20], [120, 80], control1=[40, 0], control2=[90, 110], stroke="#111111")
    doc = builder.build_dict(expand_reuse=False)
    obj = doc["pages"][0]["layers"][0]["objects"][0]
    assert obj == {
        "type": "curve",
        "from": [10.0, 20.0],
        "to": [120.0, 80.0],
        "control1": [40.0, 0.0],
        "control2": [90.0, 110.0],
        "stroke": "#111111",
    }


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
    assert doc.dsl == "FrameForge"
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


def test_builder_write_serializes_and_returns_static_report(tmp_path):
    builder = DocumentBuilder(title="write helper", profile="deck")
    builder.page("p", canvas={"size": [120, 80], "units": "px"}).layer("main").text(
        [10, 10, 60, 20],
        "Hi",
        id="t",
    )
    out = tmp_path / "nested" / "doc.fg.yaml"

    report = builder.write(out)

    assert out.exists()
    parsed = parse(out.read_text(encoding="utf-8"))
    assert parsed.title == "write helper"
    assert report is not None and report.ok


def test_builder_write_can_fail_on_static_errors(tmp_path):
    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [100, 100], "units": "px"}).layer("main").add(
        {"type": "path", "d": "M 0", "stroke": "#000"}
    )

    with pytest.raises(ValueError):
        builder.write(tmp_path / "bad.fg.yaml", fail_on_error=True)

    assert not (tmp_path / "bad.fg.yaml").exists()


def test_parse_is_forgiving_by_default_for_future_documents():
    text = """
dsl: FrameForge
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
            "dsl": "FrameForge",
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
            "dsl": "FrameForge",
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
        "dsl": "FrameForge",
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
    # The group carries the placement box; its children are LOCAL to that box
    # (origin 0,0), scaled from the symbol's 10x10 frame to the 100x50 use box,
    # so the renderer's box-origin translate places them once (cf. Scene3D).
    assert group.box == [10, 20, 100, 50]
    assert group.children[0].type == "rect"
    assert group.children[0].box == [0, 0, 100, 50]
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
    # Component children are LOCAL to the group box (origin 0,0), like symbol
    # expansion: a group carrying a box is translated to that box origin by the
    # renderer, so absolute children here would be offset twice.
    comp = doc.pages[0].layers[0].objects[1]
    assert comp.box == [0, 24, 80, 40]
    assert comp.children[0].type == "rect"
    assert comp.children[0].box == [0, 0, 80, 40]
    assert comp.children[1].type == "text"
    assert comp.children[1].box[:2] == [4, 4]

    color = builder.define_color("brand", "#c00")
    with pytest.raises(TypeError):
        builder.page("bad", master=color)


def test_symbol_context_use_at_and_local_panel_lower_to_groups():
    builder = DocumentBuilder()
    with builder.symbol("status_badge", [0, 0, 100, 32]) as sym:
        sym.rect([0, 0, 100, 32], fill="$fill", radius=8)
        sym.text([12, 7, 76, 18], "$label")

    layer = builder.page("p", canvas={"size": [320, 180], "units": "px"}).layer("main")
    layer.use_at("status_badge", 20, 20, 150, 48,
                 params={"fill": "#dbeafe", "label": "Cached"})
    with layer.local([20, 84, 150, 64], id="local_panel") as panel:
        panel.rect([0, 0, 150, 64], fill="#f8fafc", radius=6)
        panel.text([12, 12, 126, 20], "Local")

    doc = builder.build()
    badge_group, panel_group = doc.pages[0].layers[0].objects
    assert badge_group.type == "group"
    assert badge_group.box == [20, 20, 150, 48]
    assert badge_group.children[0].fill == "#dbeafe"
    assert badge_group.children[1].text == "Cached"
    assert panel_group.type == "group" and panel_group.id == "local_panel"
    assert panel_group.box == [20, 84, 150, 64]
    assert panel_group.children[0].box == [0, 0, 150, 64]


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


def test_pagebuilder_geometry_helpers_lower_to_existing_primitives():
    """Higher-level geometry helpers stay SDK-side and emit path/polyline objects."""
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [300, 220], "units": "px"},
                         coordinate_mode="absolute").layer("art")
    layer.arc([60, 60], 32, 0, 180, stroke="#111", fill="none")
    layer.sector([140, 60], 36, -90, 60, fill="#fed7aa")
    layer.ring([220, 60], 38, 22, fill="#bae6fd")
    layer.regular_polygon([80, 150], 34, 6, rotation=-90, fill="#bbf7d0")
    layer.star([170, 150], 38, 16, 5, fill="#fde68a")
    layer.polyline([(220, 130), (245, 155), (280, 130)], smooth=True,
                   stroke="#111", fill="none")

    doc = builder.build()
    objs = doc.pages[0].layers[0].objects
    assert [obj.type for obj in objs] == [
        "path", "path", "path", "polyline", "polyline", "path",
    ]
    assert objs[2].style.fill_rule == "evenodd"
    assert objs[3].closed is True and len(objs[3].points) == 6
    assert objs[4].closed is True and len(objs[4].points) == 10
    assert " A " in objs[0].d and "C " in objs[5].d
    assert validate_static_rules(doc).ok


def test_sdk_geometry_patterns_fixture_exercises_public_helpers():
    """The checked-in fixture is the oracle for pattern + geometry helper output."""
    path = os.path.join(ROOT, "tests", "fixtures", "sdk-geometry-patterns.fg.yaml")
    doc = parse(open(path, encoding="utf-8").read(), forgiving=False)
    data = doc.model_dump(by_alias=True, exclude_none=True)
    objects = data["pages"][0]["layers"][0]["objects"]

    assert any(
        isinstance(obj.get("fill"), dict) and obj["fill"].get("kind") == "pattern"
        for obj in objects
    )
    assert any(obj["type"] == "path" and " A " in obj.get("d", "") for obj in objects)
    assert any(obj["type"] == "path" and "C " in obj.get("d", "") for obj in objects)
    assert any(obj["type"] == "path" and obj.get("style", {}).get("fill_rule") == "evenodd"
               for obj in objects)
    assert any(obj["type"] == "polyline" and obj.get("closed") for obj in objects)
    assert validate_static_rules(doc).ok


def test_sdk_ergonomics_showcase_fixture_exercises_high_level_helpers():
    """The fixture pins symbol context, local panels, paint wrappers and macros."""
    path = os.path.join(ROOT, "tests", "fixtures", "sdk-ergonomics-showcase.fg.yaml")
    doc = parse(open(path, encoding="utf-8").read(), forgiving=False)
    data = doc.model_dump(by_alias=True, exclude_none=True)

    def walk(objects):
        for obj in objects:
            yield obj
            yield from walk(obj.get("children", []))

    objects = list(walk(data["pages"][0]["layers"][0]["objects"]))
    assert any(obj["type"] == "group" and obj.get("meta", {}).get("source_symbol") == "metric_badge"
               for obj in objects)
    assert any(isinstance(obj.get("fill"), dict) and obj["fill"].get("kind") == "pattern"
               for obj in objects)
    assert any(obj["type"] == "line" for obj in objects)
    assert any(obj["type"] == "path" and "C " in obj.get("d", "") for obj in objects)
    assert validate_static_rules(doc).ok


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


def test_pagebuilder_grouped_collects_children_into_one_group():
    builder = DocumentBuilder()
    page = builder.page("p", canvas={"size": [200, 100], "units": "px"}).layer("main")
    with page.grouped(meta={"role": "labels"}) as labels:
        labels.text([10, 10, 80, 20], "A")
        labels.text([10, 36, 80, 20], "B")

    group = builder.build().pages[0].layers[0].objects[0]
    assert group.type == "group"
    assert group.meta == {"role": "labels"}
    assert [child.text for child in group.children] == ["A", "B"]


def test_paint_rgba_and_gradient_constructors_lower_to_valid_paint():
    """rgba()/gradient()/pattern() constructors build the model's Paint forms."""
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
    # exercise the hatch() helper (previously shadowed by a local of the same
    # name, so it went untested); it is defined as pattern("hatch", ...).
    hatch_paint = hatch(fg="#334155", bg="#f8fafc", scale=8, angle=45)
    assert hatch_paint == {
        "kind": "pattern",
        "pattern": "hatch",
        "angle": 45,
        "spacing": 8,
        "stroke": "#334155",
        "background": "#f8fafc",
    }
    assert hatch_paint == pattern("hatch", fg="#334155", bg="#f8fafc", scale=8, angle=45)
    assert dots(fg="#111", scale=6) == {"kind": "pattern", "pattern": "dots",
                                        "spacing": 6, "stroke": "#111"}
    assert grid_pattern(fg="#111", bg="#fff", scale=12)["pattern"] == "grid"

    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [200, 200], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    layer.rect([0, 0, 200, 200], fill=lg)
    layer.ellipse([100, 100], 60, 60, fill=rg)
    layer.rect([20, 20, 40, 40], fill=hatch_paint)
    doc = builder.build()
    assert doc.pages[0].layers[0].objects[0].fill.kind == "linear"
    assert doc.pages[0].layers[0].objects[1].fill.kind == "radial"
    assert doc.pages[0].layers[0].objects[2].fill.pattern == "hatch"


def test_paint_stroke_and_effect_constructors_lower_to_model_fields():
    """stroke()/shadow()/glow() and the latent opacity/rotation fields lower cleanly."""
    assert stroke(3, color="#E8743B", cap="round", dash=[4, 8]) == {
        "stroke": "#E8743B",
        "stroke_style": {"stroke_width": 3, "stroke_linecap": "round",
                         "stroke_dasharray": [4, 8]},
    }
    assert "stroke" not in stroke(2, cap="round")             # geometry-only is valid (P3)
    assert effects(glow=glow(blur=4), shadow=shadow(dy=2)) == {
        "glow": {"blur": 4},
        "shadow": {"dx": 0.0, "dy": 2, "blur": 0.0},
    }
    assert fill_stroke("#fff", "#111", 2)["stroke_style"]["stroke_width"] == 2
    assert soft_shadow() == {"dx": 0.0, "dy": 6.0, "blur": 14.0,
                             "color": "#000000", "opacity": 0.18}
    assert neon("#22d3ee") == {
        "stroke": "#22d3ee",
        "stroke_style": {"stroke_width": 2.0},
        "glow": {"blur": 10.0, "color": "#22d3ee", "opacity": 0.7},
    }

    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [200, 200], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    layer.path(Path().move_to(0, 0).line_to(10, 10), **stroke(2, color="#000", cap="round"))
    layer.rect([10, 10, 50, 50], fill="#eee", opacity=0.8, rotation=12,
               **effects(
                   shadow=shadow(dy=4, blur=6, color="#06243C", opacity=0.5),
                   glow=glow(blur=8, color="#9DE9FF"),
               ))
    doc = builder.build()
    rect = doc.pages[0].layers[0].objects[1]
    assert rect.opacity == 0.8 and rect.rotation == 12
    assert rect.shadow.dy == 4 and rect.shadow.blur == 6
    assert rect.glow.blur == 8 and rect.glow.dx is None       # a glow is a blur, not offset


def test_paint_text_style_constructor_lowers_to_canonical_style_fields():
    """text_style() names the text subset of Style and emits its canonical fields."""
    assert text_style(24, weight=700, color="#0F172A", align="center") == {
        "font_size": 24,
        "font_weight": 700,
        "color": "#0F172A",
        "text_align": "center",
    }
    # ergonomic names map to canonical CSS fields; italic selects the font_style arm
    assert text_style(italic=True, transform="uppercase",
                      family=["Inter", "sans-serif"]) == {
        "font_style": "italic",
        "text_transform": "uppercase",
        "font_family": ["Inter", "sans-serif"],
    }
    assert text_style(italic=False) == {"font_style": "normal"}
    assert text_style() == {}                                 # all-None composes to nothing

    # Lowers into the model both as a named token and as an inline text style.
    builder = DocumentBuilder()
    h1 = builder.define_text_style("h1", **text_style(32, family="Inter", weight=800))
    layer = builder.page("p", canvas={"size": [320, 120], "units": "px"},
                         coordinate_mode="absolute").layer("a")
    layer.text([10, 10, 300, 40], "Title", style=h1)
    layer.text([10, 60, 300, 40], "Sub",
               style=text_style(14, color="#64748B", line_height=1.4))
    doc = builder.build()                                     # validates against the model
    inline = doc.pages[0].layers[0].objects[1].style
    assert inline.font_size == 14 and inline.color == "#64748B"


def test_procedural_texture_macros_lower_to_valid_objects():
    objects = []
    objects.extend(hatch_fill([10, 10, 120, 60], fg="#334155", bg="#f8fafc", scale=10))
    objects.extend(grid_lines([10, 10, 120, 60], cols=4, rows=3, color="#cbd5e1"))
    objects.extend(greeble([160, 10, 110, 60], seed=7, density=0.6, fill="#94a3b8"))
    objects.append(sparkline([(0, 1), (1, 3), (2, 2), (3, 5)], [160, 100, 110, 40]))

    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [300, 180], "units": "px"}).layer("main").extend(objects)
    doc = builder.build()
    data = doc.model_dump(by_alias=True, exclude_none=True)
    lowered = data["pages"][0]["layers"][0]["objects"]

    assert lowered[0]["fill"]["kind"] == "pattern"
    assert any(obj["type"] == "line" for obj in lowered)
    assert any(obj["type"] == "rect" and obj["fill"] == "#94a3b8" for obj in lowered)
    assert lowered[-1]["type"] == "path" and "C " in lowered[-1]["d"]
    assert validate_static_rules(doc).ok


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


def _near_far_scene():
    """Two full-frame quads: a NEAR one at +z (green) and a FAR one at -z (red)."""
    scene = Scene3D()
    scene.mesh([(-1, -1, 0.6), (1, -1, 0.6), (1, 1, 0.6), (-1, 1, 0.6)],
               [[0, 1, 2, 3]], fill="#00ff00")   # NEAR (+z, toward the eye)
    scene.mesh([(-1, -1, -0.6), (1, -1, -0.6), (1, 1, -0.6), (-1, 1, -0.6)],
               [[0, 1, 2, 3]], fill="#ff0000")   # FAR
    return scene


def test_scene3d_perspective_paints_near_over_far():
    """A near face must occlude a far one under a perspective Camera.

    Regression: Scene3D.render() sorted faces by NDC depth ascending, which for a
    perspective projection (near -> -1, far -> +1) painted FAR faces LAST, i.e.
    on top — backwards. Invisible on a lone heightfield (it barely self-overlaps),
    but wrong for any solid or separated geometry. The last child is drawn on top
    and must be the NEAR (green) face.
    """
    from frameforge.sdk import Camera

    cam = Camera(eye=Vec3(0, 0, 3), target=Vec3(0, 0, 0), fov=45, aspect=1.0)
    group = _near_far_scene().render(box=[0, 0, 100, 100], camera=cam)
    assert group["children"][-1]["fill"] == "#00ff00", "near face must be on top"
    assert group["children"][0]["fill"] == "#ff0000", "far face must be at the back"


def test_scene3d_isometric_paints_near_over_far_unchanged():
    """The isometric/orthographic default already ordered near-over-far — keep it.

    The fix negates the depth key only for perspective matrices, so the
    orthographic path (and every isometric golden) is byte-for-byte untouched.
    """
    group = _near_far_scene().render(box=[0, 0, 100, 100])  # isometric default
    assert group["children"][-1]["fill"] == "#00ff00", "near face must be on top"


def test_material_helper_expands_to_plain_frameforge_fields():
    material = Material(
        fill="#88ccff",
        stroke="#123456",
        opacity=0.7,
        mix_blend_mode="multiply",
        filter=[{"fn": "blur", "value": "2px"}],
    )

    assert material.style() == {
        "fill": "#88ccff",
        "stroke": "#123456",
        "opacity": 0.7,
        "style": {
            "mix_blend_mode": "multiply",
            "filter": [{"fn": "blur", "value": "2px"}],
        },
    }
    assert material.shaded(0.5)["fill"] == "#446680"


def test_scene3d_lambert_shading_bakes_distinct_face_fills():
    scene = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=0.5)
    group = scene.render(
        box=[0, 0, 120, 100],
        material=Material(fill="#80c0ff", stroke="#0f172a"),
        light=Vec3(0, 0, 1),
        ambient=0.25,
        diffuse=0.75,
        shading="lambert",
    )

    fills = {child["fill"] for child in group["children"]}
    assert "#80c0ff" in fills
    assert "#203040" in fills
    assert len(fills) >= 2


def test_scene3d_gouraud_shading_bakes_vertex_normal_average():
    scene = Scene3D().extrude([(0, 0), (1, 0), (1, 1), (0, 1)], depth=0.5)
    group = scene.render(
        box=[0, 0, 120, 100],
        fill="#80c0ff",
        light=Vec3(0, 0, 1),
        ambient=0.25,
        diffuse=0.75,
        shading="gouraud",
    )

    fills = {child["fill"] for child in group["children"]}
    assert "#80c0ff" not in fills
    assert len(fills) >= 2


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


def test_layout_box_is_sequence_compatible_and_has_geometry_helpers():
    box = Box(10, 20, 100, 50)
    assert list(box) == [10, 20, 100, 50]
    assert box.right == 110
    assert box.bottom == 70
    assert box.center == [60, 45]
    assert box.inset(10).list() == [20, 30, 80, 30]
    assert box.move(5, -5).list() == [15, 15, 100, 50]
    assert box.resize(h=20).list() == [10, 20, 100, 20]

    cols = box.row(2, gap=10)
    assert all(isinstance(col, Box) for col in cols)
    assert cols[0].list() == [10, 20, 45, 50]
    assert cols[1].right == 110

    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [160, 100], "units": "px"}).layer("main").rect(
        box.inset(10),
        fill="#fff",
    )
    rect = builder.build().pages[0].layers[0].objects[0]
    assert rect.box == [20.0, 30.0, 80.0, 30.0]


def test_layout_input_validation():
    with pytest.raises(ValueError):
        row([0, 0, 10, 10])  # neither count nor weights
    with pytest.raises(ValueError):
        grid([0, 0, 10, 10], cols=2)  # neither rows nor count
    with pytest.raises(ValueError):
        grid([0, 0, 10, 10], cols=0, count=1)


def test_layout_native_stacks_emit_layout_groups_with_intrinsic_widgets():
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [420, 180], "units": "px"}).layer("main")
    with layer.hstack([20, 20, 300, 52], gap=12, pad=8, align="center") as actions:
        actions.add(button("Cancel", kind="ghost"))
        actions.spacer(h=36, grow=1)
        actions.add(button("Deploy", grow=2))
    with layer.wrap([20, 92, 260, 70], gap=8, pad=8) as chips:
        chips.add(badge("api", tone="accent"))
        chips.add(badge("renderer", tone="good"))
        chips.add(badge("layout-native", tone="warn"))
    with layer.vstack([300, 92, 100, 70], gap=6) as status:
        status.avatar("Ada Lovelace", size=28)
        status.toggle(on=True)
        status.progress(0.65, w=90)
        status.divider(w=90)
    with layer.vstack([20, 168, 360, 120], gap=8) as controls:
        controls.tabs(["One", "Two"])
        controls.field("Owner", value="Ada")
        controls.kpi("Latency", "42 ms")

    doc = builder.build()
    row_group, wrap_group, status_group, controls_group = doc.pages[0].layers[0].objects
    assert row_group.type == "group"
    assert row_group.layout.kind == "row"
    assert row_group.layout.padding == 8
    assert row_group.children[0].box[:2] == [0, 0]
    assert row_group.children[2].sizing.width == "fill"
    assert row_group.children[2].sizing.grow == 2
    assert wrap_group.layout.kind == "wrap"
    assert [child.meta["widget"] for child in wrap_group.children] == ["badge", "badge", "badge"]
    assert [child.meta["widget"] for child in status_group.children] == [
        "avatar", "toggle", "progress", "divider",
    ]
    assert [child.meta["widget"] for child in controls_group.children] == [
        "tabs", "field", "kpi",
    ]
    assert validate_static_rules(doc).ok


def test_page_widget_helpers_accept_intrinsic_layout_native_forms():
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [520, 220], "units": "px"}).layer("main")

    layer.button("Save", grow=1)
    layer.badge("api", tone="accent")
    layer.pill("Open")
    layer.avatar("Ada Lovelace")
    layer.field("Owner", value="Ada")
    layer.toggle(on=True)
    layer.tabs(["One", "Two"])
    layer.progress(0.5)
    layer.divider()
    layer.kpi("Latency", "42 ms")

    objects = builder.build().pages[0].layers[0].objects
    assert [obj.meta["widget"] for obj in objects] == [
        "button", "badge", "pill", "avatar", "field", "toggle", "tabs",
        "progress", "divider", "kpi",
    ]
    assert objects[0].box[:2] == [0, 0]
    assert objects[0].sizing.width == "fill"
    assert objects[0].sizing.grow == 1


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


def test_chart_can_attach_to_page_from_page_factory():
    builder = DocumentBuilder()
    page = builder.page("p", canvas={"size": [640, 440], "units": "px"}).layer("main")
    returned = (
        page.chart([100, 100, 400, 200], domain=(0, 0, 10, 100))
        .axes(x_ticks=[0, 10], y_ticks=[0, 100])
        .line([(0, 0), (10, 100)], label="series")
        .legend()
        .add_to(page)
    )

    doc = builder.build()
    assert returned is page
    assert {"line", "polyline", "text", "rect"} <= {
        obj.type for obj in doc.pages[0].layers[0].objects
    }


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


# --------------------------------------------------------------------------- #
#  widgets (frameforge.sdk.widgets)
# --------------------------------------------------------------------------- #
def _widgets_doc():
    """A page exercising every widget, for validation + render assertions."""
    b = DocumentBuilder(title="widgets", profile="deck", lang="en")
    th = default_theme()
    page = b.page("w", canvas={"size": [1200, 800], "units": "px"},
                  coordinate_mode="absolute").layer("main")
    page.rect([0, 0, 1200, 800], fill="#F4F6F9")
    for spec, bx in zip(
        [("Open", "248", "+12", False), ("CSAT", "94%", "+2", False),
         ("Reply", "1h 42m", "-8%", False), ("Backlog", "31", "+5", True)],
        row([24, 24, 1152, 104], count=4, gap=18),
    ):
        page.add(kpi(bx, spec[0], spec[1], delta=spec[2], down=spec[3], theme=th))
    page.add(badge([24, 150, 90, 24], "Urgent", tone="bad", theme=th))
    page.add(pill([130, 150, 120, 28], "Filter", stroke=th.line, theme=th))
    page.add(button([260, 148, 120, 32], "New", kind="primary", theme=th))
    page.add(button([390, 148, 100, 32], "Export", kind="ghost", theme=th))
    page.add(avatar([500, 146, 36, 36], "Jane Cooper", theme=th))
    page.add(toggle([560, 156, 40, 22], on=True, theme=th))
    page.add(tabs([24, 200, 480, 36], ["One", "Two", "Three"], active=0, theme=th))
    page.add(progress([24, 248, 300, 8], 0.62, tone="good", theme=th))
    page.add(field([24, 272, 260, 58], "Status", value="Open", kind="select", theme=th))
    page.add(divider([24, 344, 1152, 1], theme=th))
    panel = card([24, 360, 1152, 360], title="Tickets", action="All", theme=th)
    page.add(panel.object)
    page.add(table(
        panel.content,
        [{"label": "ID", "width": "10%"}, {"label": "Subject", "width": "60%"},
         {"label": "Priority", "width": "30%", "align": "center"}],
        [["#1", "Refund not received", "Urgent"], ["#2", "Reset link", "High"]],
        theme=th))
    return b, panel


def test_widgets_validate_with_zero_warnings():
    """The central claim: a full widget-built page lowers to groups + a
    TableObject and validates with no errors AND no tabular/overlap warnings."""
    b, _ = _widgets_doc()
    report = validate_static_rules(b.build())
    assert report.ok
    rule_ids = {i.rule_id for i in report.issues}
    assert "tabular-box-model" not in rule_ids
    assert "overlap" not in rule_ids
    assert not [i for i in report.issues if i.severity == "error"]


def test_pagebuilder_widget_methods_add_common_widgets():
    b = DocumentBuilder(title="page widgets", profile="deck", lang="en")
    th = default_theme()
    page = b.page("w", canvas={"size": [600, 420], "units": "px"},
                  coordinate_mode="absolute").layer("main")
    page.rect([0, 0, 600, 420], fill=th.surface_alt)
    page.kpi([24, 24, 180, 92], "Open", "248", delta="+12", theme=th)
    page.badge([224, 32, 88, 24], "Urgent", tone="bad", theme=th)
    page.pill([324, 30, 120, 28], "Filter", stroke=th.line, theme=th)
    page.button([24, 136, 120, 34], "New", theme=th)
    page.avatar([160, 135, 36, 36], "Jane Cooper", theme=th)
    page.toggle([214, 142, 40, 22], on=True, theme=th)
    page.tabs([24, 192, 260, 36], ["One", "Two"], theme=th)
    page.progress([24, 248, 220, 8], 0.62, theme=th)
    page.field([24, 280, 240, 58], "Status", value="Open", kind="select", theme=th)
    page.divider([24, 356, 552, 1], theme=th)
    panel = page.card([300, 136, 260, 160], title="Tickets", theme=th)
    page.table(
        panel.content,
        [{"label": "ID", "width": "25%"}, {"label": "Subject", "width": "75%"}],
        [["#1", "Refund"]],
        theme=th,
    )

    doc = b.build()
    types = [obj.type for obj in doc.pages[0].layers[0].objects]
    assert types.count("group") >= 10
    assert "table" in types
    assert validate_static_rules(doc).ok


def test_widget_table_lowers_to_table_object():
    b, _ = _widgets_doc()
    doc = b.build()
    types = [o.type for o in doc.pages[0].layers[0].objects]
    assert "table" in types          # a real TableObject, not positioned text
    tbl = next(o for o in doc.pages[0].layers[0].objects if o.type == "table")
    assert tbl.header == ["ID", "Subject", "Priority"]
    assert len(tbl.rows) == 2


def test_widget_is_a_single_tagged_group():
    obj = kpi([0, 0, 200, 100], "Open", "248", delta="+1", theme=default_theme())
    assert obj["type"] == "group"
    assert obj["box"] == [0.0, 0.0, 200.0, 100.0]
    assert obj["meta"]["widget"] == "kpi"
    # the background rect is decorative; the value text is real content
    rects = [c for c in obj["children"] if c["type"] == "rect"]
    texts = [c for c in obj["children"] if c["type"] == "text"]
    assert all(r.get("decorative") for r in rects)
    assert any(t["text"] == "248" for t in texts)
    assert not any(t.get("decorative") for t in texts)


def test_card_returns_panel_with_inner_content_box():
    panel = card([100, 50, 400, 300], title="Hi", pad=16, theme=default_theme())
    assert isinstance(panel, Panel)
    cx, cy, cw, ch = panel.content
    # content sits inside the card box, below the title row
    assert cx >= 100 and cy >= 50 + 16
    assert cx + cw <= 100 + 400 and cy + ch <= 50 + 300


def test_theme_restyle_flows_into_widget_output():
    from dataclasses import replace
    th = replace(default_theme(), accent="#16A34A")
    obj = button([0, 0, 100, 36], "Go", kind="primary", theme=th)
    bg = next(c for c in obj["children"] if c["type"] == "rect")
    assert bg["fill"] == "#16A34A"


def test_badge_width_uses_measurement():
    th = default_theme()
    assert badge_width("Urgent", theme=th) > badge_width("Hi", theme=th)


def test_register_theme_defines_tokens():
    b = DocumentBuilder(profile="deck")
    handles = register_theme(b)
    assert handles["accent"].kind == "color"
    assert handles["accent"].name == "accent"


def test_widgets_reach_the_svg_proxy():
    """Honest-scope: the widgets actually render through the proxy."""
    b, _ = _widgets_doc()
    svg = render_page_svgs(b.build(), base_dir=ROOT)[0]
    assert "248" in svg          # a KPI value
    assert "Urgent" in svg       # a badge label
    assert "Tickets" in svg      # a card title


# --------------------------------------------------------------------------- #
#  core-rendered object types now reachable from PageBuilder
# --------------------------------------------------------------------------- #
def test_pagebuilder_icon_bullet_list_dimension_lower_and_render():
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [320, 240], "units": "px"},
                         coordinate_mode="absolute").layer("main")
    layer.icon([10, 10, 24, 24], "★", color="#c00", size=20)
    layer.bullet_list([10, 44, 200, 60], ["alpha", "beta"], marker="•",
                      marker_color="#c00", gap=6)
    layer.dimension([10, 140], [210, 140], kind="linear", text="200 px",
                    offset=10, arrows="both")

    doc = builder.build()
    icon, bullets, dim = doc.pages[0].layers[0].objects
    assert icon.type == "icon" and icon.glyph == "★" and icon.color == "#c00"
    assert bullets.type == "bullet_list" and bullets.items == ["alpha", "beta"]
    assert bullets.marker == "•" and bullets.marker_color == "#c00"
    assert dim.type == "dimension" and dim.kind == "linear"
    assert dim.from_ == [10.0, 140.0] and dim.to == [210.0, 140.0]
    assert dim.text == "200 px"

    svg = render_page_svgs(doc)[0]
    assert "★" in svg and "alpha" in svg and "200 px" in svg


def test_dimension_accepts_id_and_ref_port_anchors():
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [320, 240], "units": "px"}).layer("main")
    layer.rect([10, 10, 60, 40], id="a", ports={"e": [70, 30]})
    layer.rect([200, 10, 60, 40], id="b")
    layer.dimension({"ref": "a", "port": "e"}, "b", kind="aligned", value="auto")
    doc = builder.build()
    dim = doc.pages[0].layers[0].objects[2]
    assert dim.from_.ref == "a" and dim.from_.port == "e"
    assert dim.to == "b" and dim.value == "auto"


# --------------------------------------------------------------------------- #
#  document-level exposure: targets, counters, description/meta/text_contract
# --------------------------------------------------------------------------- #
def test_document_targets_counters_description_meta_text_contract():
    builder = DocumentBuilder(title="doc surface")
    builder.describe("A test document.").meta(author="suite").text_contract(
        min_font_size=6, overflow="shrink_to_fit"
    )
    builder.define_counter("figure", start=1, format="decimal")
    builder.define_target("screen", {"size": [1280, 720], "units": "px"},
                          font_scale=1.2, hide=["hero"], padding_delta=-2)
    layer = builder.page("p", canvas={"size": [320, 240], "units": "px"}).layer("main")
    layer.rect([10, 10, 60, 40], id="hero", fill="#eee")

    doc = builder.build()
    assert doc.description == "A test document."
    assert doc.meta == {"author": "suite"}
    assert doc.text_contract.min_font_size == 6
    assert doc.defs.counters["figure"].start == 1
    target = doc.targets[0]
    assert target.name == "screen"
    assert target.adjustments.font_scale == 1.2
    assert target.adjustments.hide == ["hero"]
    assert target.adjustments.padding_delta == -2
    assert validate_static_rules(doc).ok


def test_page_level_links_notes_meta_and_link_helper():
    builder = DocumentBuilder()
    builder.page("p1", canvas={"size": [100, 100], "units": "px"},
                 links=[{"to": "p2", "relation": "next"}], notes="speaker notes",
                 meta={"kind": "cover"}).layer("main").rect([0, 0, 10, 10])
    p2 = builder.page("p2", canvas={"size": [100, 100], "units": "px"})
    p2.layer("main").rect([0, 0, 10, 10])
    p2.link("p1", relation="prev", label="Back")

    doc = builder.build()
    assert doc.pages[0].links[0].to == "p2" and doc.pages[0].links[0].relation == "next"
    assert doc.pages[0].notes == "speaker notes"
    assert doc.pages[0].meta == {"kind": "cover"}
    assert doc.pages[1].links[0].to == "p1" and doc.pages[1].links[0].label == "Back"


# --------------------------------------------------------------------------- #
#  write(fail_on_error=True) surfaces the whole report
# --------------------------------------------------------------------------- #
def test_write_fail_on_error_raises_typed_error_with_all_errors(tmp_path):
    from frameforge.sdk import StaticValidationError, ValidationReport

    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [100, 100], "units": "px"}).layer("main")
    layer.add({"type": "path", "d": "M 0", "stroke": "#000"})
    layer.add({"type": "path", "d": "Q 1", "stroke": "#000"})

    with pytest.raises(StaticValidationError) as excinfo:
        builder.write(tmp_path / "bad.fg.yaml", fail_on_error=True)

    err = excinfo.value
    assert isinstance(err, ValueError)                     # backwards compatible
    assert isinstance(err.report, ValidationReport)
    assert len(err.errors) >= 2                            # not just the first error
    message = str(err)
    assert "/objects/0/d" in message and "/objects/1/d" in message
    assert not (tmp_path / "bad.fg.yaml").exists()


# --------------------------------------------------------------------------- #
#  validate_static_rules(targets=...) applies per-target adjustments
# --------------------------------------------------------------------------- #
def _doc_with_hiding_target() -> dict:
    return {
        "dsl": "FrameForge",
        "version": "2.2.0",
        "targets": [
            {
                "name": "screen",
                "canvas": {"size": [100, 100], "units": "px"},
                "adjustments": {"hide": ["hero"]},
            }
        ],
        "pages": [
            {
                "mode": "page",
                "id": "p",
                "reading_order": ["hero"],
                "layers": [
                    {
                        "id": "l",
                        "objects": [
                            {"type": "rect", "id": "hero", "box": [0, 0, 10, 10]},
                            {"type": "line", "from": "hero", "to": [50, 50],
                             "stroke": "#000"},
                        ],
                    }
                ],
            }
        ],
    }


def test_validate_static_rules_checks_post_adjustment_references_per_target():
    report = validate_static_rules(_doc_with_hiding_target(), targets=["screen"])
    assert not report.ok
    adjustment_issues = [i for i in report.issues if i.rule_id == "target-adjustment"]
    paths = {i.path for i in adjustment_issues}
    assert "/pages/0/reading_order/0" in paths             # hidden id in reading_order
    assert any(path.endswith("/from") for path in paths)   # hidden id as line anchor
    assert all("screen" in i.message and "hero" in i.message for i in adjustment_issues)


def test_validate_static_rules_without_targets_stays_clean():
    report = validate_static_rules(_doc_with_hiding_target())
    assert not any(i.rule_id == "target-adjustment" for i in report.issues)


# --------------------------------------------------------------------------- #
#  wireframe widget atoms
# --------------------------------------------------------------------------- #
def test_new_wireframe_atoms_lower_and_validate():
    from frameforge.sdk import (
        breadcrumb, checkbox, dropdown, image_placeholder, navbar, radio,
        slider, sticky_note,
    )

    builder = DocumentBuilder(profile="deck")
    layer = builder.page("p", canvas={"size": [640, 640], "units": "px"},
                         coordinate_mode="absolute").layer("main")
    layer.navbar([0, 0, 640, 56], ["Home", "Docs", "Pricing"], brand="Acme", active=1)
    layer.breadcrumb([24, 72, 300, 24], ["Home", "Docs", "SDK"])
    layer.checkbox([24, 112, 160, 20], checked=True, label="Remember me")
    layer.radio([24, 144, 160, 20], selected=True, label="Option A")
    layer.slider([24, 180, 200, 20], 0.4)
    layer.dropdown([24, 216, 200, 140], ["One", "Two", "Three"], selected=1)
    layer.image_placeholder([260, 112, 200, 140], label="Hero image")
    layer.sticky_note([480, 112, 140, 100], "Swap for final art", id="note-1")

    doc = builder.build()
    objects = doc.pages[0].layers[0].objects
    widgets = [obj.meta["widget"] for obj in objects]
    assert widgets == ["navbar", "breadcrumb", "checkbox", "radio", "slider",
                       "dropdown", "image_placeholder", "sticky_note"]
    report = validate_static_rules(doc)
    assert not [i for i in report.issues if i.severity == "error"]

    # atom-specific lowering contracts
    check = checkbox([0, 0, 18, 18], checked=True)
    assert any(c["type"] == "polyline" for c in check["children"])   # the check mark
    unchecked = checkbox([0, 0, 18, 18], checked=False)
    assert not any(c["type"] == "polyline" for c in unchecked["children"])
    dot = radio([0, 0, 18, 18], selected=True)
    assert sum(1 for c in dot["children"] if c["type"] == "ellipse") == 2
    placeholder = image_placeholder([0, 0, 100, 80])
    diagonals = [c for c in placeholder["children"] if c["type"] == "line"]
    assert len(diagonals) == 2                                        # the X cross
    note = sticky_note([0, 0, 120, 90], "hi", id="n")
    assert note["decorative"] is True and note["id"] == "n"           # non-print flag
    crumb = breadcrumb(["Home", "Docs"])
    assert crumb["box"][2] > 0                                        # auto-sized
    menu = dropdown([0, 0, 160, 120], ["a", "b"], selected=0)
    assert any(c.get("fill") for c in menu["children"] if c["type"] == "rect")
    track = slider(0.5)
    assert track["meta"]["widget"] == "slider"                        # auto-size form


# --------------------------------------------------------------------------- #
#  group(style=<token>) composes via Style.class
# --------------------------------------------------------------------------- #
def test_group_composes_token_style_with_transform_and_clip():
    builder = DocumentBuilder()
    panel = builder.define_style("panel", fill="#eef2f7")
    layer = builder.page("p", canvas={"size": [200, 200], "units": "px"}).layer("main")
    layer.group([{"type": "rect", "box": [0, 0, 40, 40]}], style=panel,
                transform=Mat3.translate(20, 30), clip=[0, 0, 40, 40])

    doc = builder.build()
    group = doc.pages[0].layers[0].objects[0]
    assert group.style.class_ == "panel"
    assert group.style.transform[0].fn == "matrix"
    assert group.style.clip_path is not None
    assert render_page_svgs(doc)[0]                       # renders without crashing


# --------------------------------------------------------------------------- #
#  SVG ingest is visible on the SDK surface
# --------------------------------------------------------------------------- #
def test_svg_to_objects_is_reexported_through_the_sdk():
    from frameforge.sdk import svg_to_objects

    objects = svg_to_objects(
        '<svg viewBox="0 0 10 10">'
        '<rect x="1" y="1" width="4" height="4" fill="#f00"/>'
        '<circle cx="7" cy="7" r="2" fill="#00f"/>'
        "</svg>"
    )
    assert [obj["type"] for obj in objects] == ["rect", "ellipse"]
    assert objects[0]["fill"] == "#f00"

    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [10, 10], "units": "px"}).layer("main").extend(objects)
    assert builder.build().pages[0].layers[0].objects[0].type == "rect"


# --------------------------------------------------------------------------- #
#  conform: renderer diagnostics threaded through render_pages_with_stats
# --------------------------------------------------------------------------- #
def test_render_pages_with_stats_optionally_returns_renderer_diagnostics():
    """diagnostics=True adds the renderer's structured feedback as a third
    element; the default stays the frozen (svgs, tstats) 2-tuple contract."""
    from frameforge.sdk.conform import render_pages_with_stats

    builder = DocumentBuilder(title="diag", profile="diagram")
    layer = builder.page("p", canvas={"size": [100, 80], "units": "px"},
                         coordinate_mode="absolute").layer("m")
    layer.rect([0, 0, 100, 80], fill="#ffffff")
    doc = builder.build()

    default = render_pages_with_stats(doc, real_metrics=False)
    assert len(default) == 2                                  # frozen 2-tuple contract

    svgs, stats, diags = render_pages_with_stats(doc, real_metrics=False, diagnostics=True)
    assert svgs == default[0] and stats == default[1]
    assert {"warnings", "skipped_objects", "skipped_flowables",
            "font_fallbacks", "layout"} <= set(diags)
    assert diags["layout"] == []                              # layout_report defaults off

    _, _, with_layout = render_pages_with_stats(
        doc, real_metrics=False, diagnostics=True, layout_report=True)
    assert with_layout["layout"], "layout_report=True must emit per-object layout entries"


# --------------------------------------------------------------------------- #
#  Chart: pie / donut / scatter / area series
# --------------------------------------------------------------------------- #
def test_chart_scatter_and_area_lower_to_valid_objects():
    frame = Frame(domain=(0, 0, 10, 100), box=(0, 0, 200, 100))
    chart = (
        Chart(frame)
        .scatter([(1, 10), (5, 50)], r=3, fill="#112233", label="pts")
        .area([(0, 0), (5, 50), (10, 100)], fill="#EEF4FF", stroke="#3B6EA5", label="fill")
        .legend()
    )
    objs = chart.objects()
    dots = [o for o in objs if o["type"] == "ellipse"]
    assert len(dots) == 2 and dots[0]["rx"] == 3 and dots[0]["fill"] == "#112233"
    closed = [o for o in objs if o["type"] == "polyline" and o.get("closed")]
    assert len(closed) == 1 and closed[0]["fill"] == "#EEF4FF"
    # the area polygon returns to the baseline under the series' last/first x
    assert closed[0]["points"][-2:] == [[200.0, 100.0], [0.0, 100.0]]
    outline = [o for o in objs if o["type"] == "polyline" and not o.get("closed")]
    assert outline and outline[0]["stroke"] == "#3B6EA5"

    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [400, 300], "units": "px"}).layer("m").extend(objs)
    builder.build()                                           # validates green


def test_chart_pie_and_donut_lower_to_sector_paths():
    frame = Frame(domain=(0, 0, 1, 1), box=(0, 0, 200, 200))
    pie = Chart(frame).pie([1, 1, 2], colors=["#111111", "#222222", "#333333"],
                           labels=["a", "b", "c"])
    sectors = [o for o in pie.objects() if o["type"] == "path"]
    assert len(sectors) == 3
    assert [o["fill"] for o in sectors] == ["#111111", "#222222", "#333333"]
    assert all(o["d"].startswith("M ") and " A " in o["d"] and o["d"].rstrip().endswith("Z")
               for o in sectors)
    assert pie._legend == [("a", "#111111"), ("b", "#222222"), ("c", "#333333")]

    donut = Chart(frame).donut([3, 1], colors=["#445566", "#778899"])
    rings = [o for o in donut.objects() if o["type"] == "path"]
    assert len(rings) == 2
    # a donut slice traces the outer arc AND the inner return arc
    assert all(o["d"].count("A ") >= 2 for o in rings)

    # a single 100% value degenerates to a full disc, not a zero-sweep arc
    solo = Chart(frame).pie([5], colors=["#111111"])
    assert [o["type"] for o in solo.objects()] == ["ellipse"]

    builder = DocumentBuilder()
    builder.page("p", canvas={"size": [400, 400], "units": "px"}).layer("m").extend(
        sectors + rings)
    builder.build()                                           # validates green


def test_chart_pie_rejects_bad_input():
    frame = Frame(domain=(0, 0, 1, 1), box=(0, 0, 100, 100))
    with pytest.raises(ValueError):
        Chart(frame).pie([], colors=["#111111"])
    with pytest.raises(ValueError):
        Chart(frame).pie([1, -2], colors=["#111111"])
    with pytest.raises(ValueError):
        Chart(frame).pie([1], colors=["#111111"], inner_ratio=1.0)
    with pytest.raises(ValueError):
        Chart(frame).area([(0, 0)], fill="#eee")
