#!/usr/bin/env python3
"""Regression coverage for TikZ approximations of SVG effect surfaces."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge_render.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge_render.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from frameforge_render.infrastructure.latex import transpile  # noqa: E402
from frameforge_render.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(colors=None):
    color = ColorResolver(colors or {})
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


@pytest.mark.parametrize(
    ("obj", "source_fragment"),
    [
        (
            {"type": "line", "from": [0, 1], "to": [20, 1], "stroke": "#123456"},
            "draw={rgb,255:red,18;green,52;blue,86}",
        ),
        (
            {"type": "polyline", "points": [[0, 0], [10, 5], [20, 0]], "stroke": "#123456"},
            "draw={rgb,255:red,18;green,52;blue,86}",
        ),
        (
            {"type": "polygon", "points": [[0, 0], [20, 0], [10, 10]], "fill": "#123456"},
            "fill={rgb,255:red,18;green,52;blue,86}",
        ),
        (
            {"type": "path", "d": "M 0 0 L 20 0 L 10 10 Z", "fill": "#123456"},
            "fill={rgb,255:red,18;green,52;blue,86}",
        ),
        (
            {
                "type": "curve",
                "from": [0, 0],
                "control1": [5, 10],
                "control2": [15, 10],
                "to": [20, 0],
                "stroke": "#123456",
            },
            "draw={rgb,255:red,18;green,52;blue,86}",
        ),
        (
            {"type": "text", "box": [0, 0, 60, 20], "text": "Effect", "style": {"color": "#123456"}},
            "text={rgb,255:red,18;green,52;blue,86}",
        ),
        (
            {"type": "image", "box": [0, 0, 40, 20], "src": "missing.png", "alt": "Image"},
            "fill={rgb,255:red,245;green,245;blue,245}",
        ),
        (
            {"type": "table", "box": [0, 0, 40, 20], "rows": [["A", "B"]]},
            "\\draw (0,0) rectangle (40,20)",
        ),
    ],
)
def test_object_shadow_covers_every_pdf_tex_object_family(obj, source_fragment):
    obj = {
        **obj,
        "shadow": {"color": "#d946ef", "dx": 3, "dy": 4, "blur": 6, "opacity": 0.35},
    }

    tex = _fig().render(obj)

    marker = "% frameforge-effect:shadow"
    assert marker in tex
    assert "{rgb,255:red,217;green,70;blue,239}" in tex
    assert "shift={(3,4)},opacity=0.35" in tex
    assert tex.index(marker) < tex.index(source_fragment)


def test_object_effect_stack_preserves_authored_order_for_non_basic_shape():
    obj = {
        "type": "line",
        "from": [0, 0],
        "to": [20, 0],
        "stroke": "#123456",
        "effects": [
            {"kind": "shadow", "color": "#111111", "dx": 1, "dy": 2, "opacity": 0.2},
            {"kind": "glow", "color": "#22cc88", "blur": 8, "opacity": 0.4},
            {"kind": "shadow", "color": "#334455", "dx": 5, "dy": 6, "opacity": 0.6},
        ],
    }

    tex = _fig().render(obj)

    markers = [line for line in tex.splitlines() if line.startswith("% frameforge-effect:")]
    assert markers == [
        "% frameforge-effect:shadow",
        "% frameforge-effect:glow",
        "% frameforge-effect:shadow",
    ]
    assert tex.index("shift={(1,2)},opacity=0.2") < tex.index("opacity=0.4")
    assert tex.index("opacity=0.4") < tex.index("shift={(5,6)},opacity=0.6")


def test_text_glow_uses_deterministic_spread_underlay_before_source_text():
    obj = {
        "type": "text",
        "box": [10, 20, 80, 20],
        "text": "Glow",
        "style": {"color": "#123456"},
        "glow": {"color": "#22cc88", "blur": 8, "opacity": 0.4},
    }

    first = _fig().render(obj)
    second = _fig().render(obj)

    assert first == second
    assert first.count("% frameforge-effect:glow") == 1
    assert first.count("opacity=0.05") == 8
    assert first.index("% frameforge-effect:glow") < first.index("text={rgb,255:red,18;green,52;blue,86}")


def test_text_effect_silhouette_overrides_every_inline_span_colour():
    obj = {
        "type": "text",
        "box": [0, 0, 100, 20],
        "spans": [
            {"text": "Red", "style": {"color": "#ff0000", "bold": True}},
            {"text": "Blue", "style": {"color": "#0000ff", "italic": True}},
        ],
        "shadow": {"color": "#22cc88", "dx": 2, "dy": 3, "opacity": 0.4},
    }

    tex = _fig().render(obj)

    effect_start = tex.index("% frameforge-effect:shadow")
    effect_end = tex.index("\\end{scope}", effect_start)
    underlay = tex[effect_start:effect_end]
    assert "red,34;green,204;blue,136" in underlay
    assert "red,255;green,0;blue,0" not in underlay
    assert "red,0;green,0;blue,255" not in underlay
    assert "red,255;green,0;blue,0" in tex[effect_end:]
    assert "red,0;green,0;blue,255" in tex[effect_end:]


@pytest.mark.parametrize("object_type", ["image", "table"])
def test_compound_object_glow_expands_one_box_silhouette(object_type):
    obj = ({"type": "image", "box": [0, 0, 40, 20], "src": "missing.png"}
           if object_type == "image"
           else {"type": "table", "box": [0, 0, 40, 20], "rows": [["A"]]})
    obj["glow"] = {"color": "#22cc88", "blur": 6, "opacity": 0.5}

    tex = _fig().render(obj)

    effect_start = tex.index("% frameforge-effect:glow")
    source_start = tex.index("\\end{scope}", effect_start)
    underlay = tex[effect_start:source_start]
    assert "(-3,-3) rectangle (43,23)" in underlay
    assert underlay.count("opacity=0.5") == 1
    assert "fill opacity" not in underlay


def test_public_pdf_tex_transpiler_preserves_effects_through_page_rendering():
    doc = {
        "dsl": "FrameForge",
        "version": "2.7.1",
        "pages": [{
            "mode": "page",
            "id": "effects",
            "canvas": {"size": [120, 80]},
            "layers": [{
                "id": "main",
                "objects": [
                    {
                        "type": "line",
                        "from": [10, 20],
                        "to": [100, 20],
                        "stroke": "#123456",
                        "shadow": {"color": "#111111", "dx": 2, "dy": 3, "opacity": 0.25},
                    },
                    {
                        "type": "table",
                        "box": [10, 35, 100, 30],
                        "rows": [["A", "B"]],
                        "glow": {"color": "#22cc88", "blur": 4, "opacity": 0.4},
                    },
                ],
            }],
        }],
    }

    tex = transpile(doc)

    assert "\\begin{tikzpicture}[x=1pt,y=-1pt]" in tex
    assert "% frameforge-effect:shadow" in tex
    assert "% frameforge-effect:glow" in tex
    assert tex.index("% frameforge-effect:shadow") < tex.index("draw={rgb,255:red,18;green,52;blue,86}")
    assert "(8,33) rectangle (112,67)" in tex


def test_rect_shadow_draws_translucent_offset_shape_before_rect():
    tex = _fig({"panel": "#ffeecc", "ink": "#123456"}).render({
        "type": "rect",
        "box": [10, 20, 60, 35],
        "radius": 4,
        "fill": "panel",
        "shadow": {"color": "ink", "dx": 2, "dy": 3, "opacity": 0.3, "blur": 6},
    })
    assert tex.index("(12,23) rectangle (72,58)") < tex.index("(10,20) rectangle (70,55)")
    assert "fill={rgb,255:red,18;green,52;blue,86}" in tex
    assert "fill opacity=0.3" in tex
    assert "rounded corners=4pt" in tex


def test_glow_expands_ellipse_behind_source_shape():
    tex = _fig({"brand": "#005c46"}).render({
        "type": "ellipse",
        "center": [120, 30],
        "rx": 28,
        "ry": 18,
        "fill": "brand",
        "glow": {"color": "brand", "blur": 6, "opacity": 0.5},
    })
    assert tex.index("ellipse (31pt and 21pt)") < tex.index("ellipse (28pt and 18pt)")
    assert "fill opacity=0.5" in tex


def test_style_box_shadow_maps_to_latex_shadow_shape():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {
            "box_shadow": [
                {"offset_x": 1, "offset_y": 2, "blur": 3, "color": "#111111", "opacity": 0.25}
            ],
        },
    })
    assert "(1,2) rectangle (21,12)" in tex
    assert "fill opacity=0.25" in tex


def test_raw_css_drop_shadow_filter_maps_to_latex_shadow_shape():
    tex = _fig().render({
        "type": "rect",
        "box": [24, 86, 240, 222],
        "fill": "#ffffff",
        "style": {"css": "filter: drop-shadow(0 14px 22px rgba(2,6,23,.30))"},
    })

    assert "(24,100) rectangle (264,322)" in tex
    assert "(24,86) rectangle (264,308)" in tex
    assert tex.index("(24,100) rectangle (264,322)") < tex.index("(24,86) rectangle (264,308)")
    assert "fill={rgb,255:red,2;green,6;blue,23}" in tex
    assert "fill opacity=0.3" in tex


def test_raw_css_drop_shadow_filter_accepts_hex_color():
    tex = _fig().render({
        "type": "ellipse",
        "center": [40, 40],
        "rx": 20,
        "ry": 12,
        "fill": "#ffffff",
        "style": {"css": "filter: drop-shadow(3px 4px 5px #12345680)"},
    })

    assert "\\path[fill={rgb,255:red,18;green,52;blue,86},fill opacity=0.502] (43,44) ellipse" in tex


def test_raw_css_drop_shadow_filter_allows_multiple_shadows():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"css": "filter: drop-shadow(1px 2px 3px #111) drop-shadow(4px 5px 6px #222)"},
    })

    assert "(1,2) rectangle (21,12)" in tex
    assert "(4,5) rectangle (24,15)" in tex


def test_text_shadow_draws_offset_text_before_source_text():
    tex = _fig({"ink": "#111111", "shade": "#123456"}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Shadow",
        "style": {
            "font_size": 16,
            "color": "ink",
            "text_shadow": [{"offset_x": 2, "offset_y": 3, "blur": 4, "color": "shade"}],
        },
    })

    shadow = "at (12,38) {Shadow}"
    source = "at (10,35) {Shadow}"
    assert tex.index(shadow) < tex.index(source)
    assert "text={rgb,255:red,18;green,52;blue,86}" in tex
    assert "text opacity=0.45" in tex
    assert "text={rgb,255:red,17;green,17;blue,17}" in tex


def test_text_shadow_applies_to_text_spans():
    tex = _fig({"shade": "#123456"}).render({
        "type": "text",
        "box": [0, 0, 120, 20],
        "spans": [
            {
                "text": "Run",
                "style": {
                    "font_size": 10,
                    "text_shadow": [{"offset_x": 1, "offset_y": 2, "color": "shade"}],
                },
            },
        ],
    })

    assert tex.index("at (1,12) {Run}") < tex.index("at (0,10) {Run}")
    assert "text={rgb,255:red,18;green,52;blue,86}" in tex


def test_text_shadow_uses_transformed_and_decorated_text():
    tex = _fig({"shade": "#123456"}).render({
        "type": "text",
        "box": [0, 0, 120, 20],
        "text": "shadow_text",
        "style": {
            "text_transform": "uppercase",
            "text_decoration": {"line": "underline"},
            "text_shadow": [{"offset_x": 1, "offset_y": 2, "color": "shade"}],
        },
    })

    shadow = "at (1,12) {\\underline{SHADOW\\_TEXT}}"
    source = "at (0,10) {\\underline{SHADOW\\_TEXT}}"
    assert shadow in tex
    assert source in tex
    assert tex.index(shadow) < tex.index(source)
    assert "shadow\\_text" not in tex


def test_raw_css_text_shadow_draws_offset_text_before_source_text():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 180, 30],
        "text": "CSS Shadow",
        "style": {
            "css": "text-shadow: 1px 2px 3px rgba(15,23,42,.45)",
            "color": "#111111",
        },
    })

    shadow = "at (11,37) {CSS Shadow}"
    source = "at (10,35) {CSS Shadow}"
    assert tex.index(shadow) < tex.index(source)
    assert "text={rgb,255:red,15;green,23;blue,42}" in tex
    assert "text opacity=0.45" in tex


def test_raw_css_text_shadow_allows_multiple_color_function_shadows():
    tex = _fig().render({
        "type": "text",
        "box": [0, 0, 160, 20],
        "text": "Layered",
        "style": {
            "css": "text-shadow: 1px 2px 3px rgba(15,23,42,.45), 4px 5px 0 #12345680",
        },
    })

    assert "at (1,12) {Layered}" in tex
    assert "at (4,15) {Layered}" in tex
    assert "text={rgb,255:red,15;green,23;blue,42}" in tex
    assert "text={rgb,255:red,18;green,52;blue,86}" in tex
    assert "text opacity=0.502" in tex


def test_object_isolation_maps_to_tikz_transparency_group():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "isolation": "isolate",
    })

    assert "\\begin{scope}[transparency group]" in tex
    assert "(0,0) rectangle (20,10)" in tex


def test_style_isolation_maps_to_tikz_transparency_group():
    tex = _fig().render({
        "type": "ellipse",
        "center": [20, 20],
        "rx": 10,
        "ry": 8,
        "fill": "#111111",
        "style": {"isolation": "isolate"},
    })

    assert "\\begin{scope}[transparency group]" in tex
    assert "ellipse (10pt and 8pt)" in tex


def test_isolation_composes_with_opacity_scope_options():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "opacity": 0.5,
        "isolation": "isolate",
    })

    assert "\\begin{scope}[transparency group,opacity=0.5]" in tex


def test_style_mix_blend_mode_maps_to_tikz_blend_scope():
    tex = _fig().render({
        "type": "circle",
        "center": [20, 20],
        "r": 10,
        "fill": "#00aaff",
        "style": {"mix_blend_mode": "multiply"},
    })

    assert "\\begin{scope}[blend mode=multiply]" in tex
    assert "(20,20) circle (10pt)" in tex


def test_hyphenated_mix_blend_mode_maps_to_tikz_spaced_name():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"mix_blend_mode": "color-dodge"},
    })

    assert "\\begin{scope}[blend mode=color dodge]" in tex


def test_normal_mix_blend_mode_does_not_create_scope():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"mix_blend_mode": "normal"},
    })

    assert "\\begin{scope}" not in tex
    assert "(0,0) rectangle (20,10)" in tex


def test_mix_blend_mode_composes_with_isolation_and_opacity():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "opacity": 0.5,
        "style": {"mix_blend_mode": "screen", "isolation": "isolate"},
    })

    assert "\\begin{scope}[transparency group,blend mode=screen,opacity=0.5]" in tex


def test_raw_css_mix_blend_mode_maps_to_tikz_blend_scope():
    tex = _fig().render({
        "type": "circle",
        "center": [20, 20],
        "r": 10,
        "fill": "#00aaff",
        "style": {"css": "mix-blend-mode: multiply"},
    })

    assert "\\begin{scope}[blend mode=multiply]" in tex


def test_normalized_mix_blend_mode_wins_over_raw_css():
    tex = _fig().render({
        "type": "circle",
        "center": [20, 20],
        "r": 10,
        "fill": "#00aaff",
        "style": {"mix_blend_mode": "screen", "css": "mix-blend-mode: multiply"},
    })

    assert "\\begin{scope}[blend mode=screen]" in tex
    assert "blend mode=multiply" not in tex


def test_raw_css_opacity_maps_to_tikz_scope_opacity():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"css": "opacity: 0.45"},
    })

    assert "\\begin{scope}[opacity=0.45]" in tex


def test_raw_css_opacity_accepts_percent_values():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"css": "opacity: 45%"},
    })

    assert "\\begin{scope}[opacity=0.45]" in tex


def test_raw_css_filter_opacity_multiplies_existing_opacity():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "opacity": 0.5,
        "style": {"css": "filter: blur(2px) opacity(40%)"},
    })

    assert "\\begin{scope}[opacity=0.2]" in tex


def test_raw_css_opacity_resolves_custom_property_calc():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"css": "--a: 0.9; opacity: calc(var(--a) - 0.35)"},
    })

    assert "\\begin{scope}[opacity=0.55]" in tex


def test_raw_css_custom_property_resolves_after_use_site():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"css": "opacity: var(--a); --a: 0.35"},
    })

    assert "\\begin{scope}[opacity=0.35]" in tex


def test_raw_css_duplicate_declarations_use_last_value():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"css": "opacity: 0.1; opacity: 0.65"},
    })

    assert "\\begin{scope}[opacity=0.65]" in tex
    assert "opacity=0.1" not in tex


def test_raw_css_filter_opacity_resolves_custom_property():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "opacity": 0.5,
        "style": {"css": "--a: 40%; filter: blur(2px) opacity(var(--a))"},
    })

    assert "\\begin{scope}[opacity=0.2]" in tex


def test_style_opacity_filter_maps_to_tikz_scope_opacity():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"filter": [{"fn": "opacity", "value": 0.4}]},
    })

    assert "\\begin{scope}[opacity=0.4]" in tex
    assert "(0,0) rectangle (20,10)" in tex


def test_style_opacity_filter_accepts_percent_values():
    tex = _fig().render({
        "type": "ellipse",
        "center": [20, 20],
        "rx": 10,
        "ry": 8,
        "fill": "#111111",
        "style": {"filter": [{"fn": "opacity", "value": "35%"}]},
    })

    assert "\\begin{scope}[opacity=0.35]" in tex


def test_style_opacity_filter_string_maps_to_tikz_scope_opacity():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "style": {"filter": "blur(2px) opacity(45%)"},
    })

    assert "\\begin{scope}[opacity=0.45]" in tex


def test_style_opacity_filter_multiplies_existing_opacity():
    tex = _fig().render({
        "type": "rect",
        "box": [0, 0, 20, 10],
        "fill": "#ffffff",
        "opacity": 0.5,
        "style": {"filter": [{"fn": "opacity", "value": 0.4}]},
    })

    assert "\\begin{scope}[opacity=0.2]" in tex
