#!/usr/bin/env python3
"""Regression coverage for TikZ approximations of SVG effect surfaces."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(colors=None):
    color = ColorResolver(colors or {})
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


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
