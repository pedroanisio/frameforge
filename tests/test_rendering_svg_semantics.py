"""Regression tests for SVG rendering semantics."""

from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MODELS = os.path.join(ROOT, "models")
if MODELS in sys.path:
    sys.path.remove(MODELS)
shadow = sys.modules.get("framegraph")
if shadow is not None and not hasattr(shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from tooling.render_fixtures import Renderer


def _svg_for(objects: list[dict], defs: dict | None = None) -> str:
    doc = {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "defs": defs or {"tokens": {"colors": {"panel": "#ffeecc", "hairline": "#123456"}}},
        "pages": [{
            "mode": "page",
            "id": "p1",
            "canvas": {"size": [200, 120]},
            "layers": [{"id": "l1", "objects": objects}],
        }],
    }
    rendered = Renderer(doc, ".").render_page(doc["pages"][0])
    return "".join(rendered) if isinstance(rendered, list) else rendered


def test_fill_only_path_has_no_implicit_stroke() -> None:
    svg = _svg_for([
        {"type": "path", "id": "filled", "d": "M 10 10 L 40 10 L 25 35 Z", "fill": "panel"},
    ])

    path = svg.split("<path", 1)[1].split("/>", 1)[0]
    assert ' fill="#ffeecc"' in path
    assert " stroke=" not in path


def test_vector_fill_and_stroke_opacity_are_emitted() -> None:
    svg = _svg_for([
        {
            "type": "path",
            "d": "M 10 10 L 40 10 L 25 35 Z",
            "fill": "panel",
            "fill_opacity": 0.4,
            "fill_rule": "evenodd",
        },
        {
            "type": "line",
            "from": [10, 60],
            "to": [90, 60],
            "stroke": {"color": "hairline", "width": 4},
            "stroke_opacity": 0.35,
        },
    ])

    assert 'fill-opacity="0.4"' in svg
    assert 'fill-rule="evenodd"' in svg
    assert 'stroke="#123456"' in svg
    assert 'stroke-width="4"' in svg
    assert 'stroke-opacity="0.35"' in svg


def test_curve_aliases_emit_cubic_paths() -> None:
    svg = _svg_for([
        {
            "type": "curve",
            "from": [10, 10],
            "control1": [20, 5],
            "control2": [30, 35],
            "to": [40, 20],
            "fill": "none",
            "stroke": "hairline",
        },
        {
            "type": "bezier",
            "from": [60, 10],
            "c1": [70, 5],
            "c2": [80, 35],
            "to": [90, 20],
            "stroke": {"color": "hairline", "width": 2},
        },
    ])

    assert '<path d="M 10 10 C 20 5 30 35 40 20"' in svg
    assert '<path d="M 60 10 C 70 5 80 35 90 20"' in svg
    assert 'fill="none"' in svg
    assert 'stroke="#123456"' in svg
    assert 'stroke-width="2"' in svg


def test_point_dimension_decomposes_to_lines_arrows_and_label() -> None:
    svg = _svg_for(
        [{
            "type": "dimension",
            "kind": "linear",
            "from": [10, 30],
            "to": [70, 30],
            "value": "auto",
            "suffix": " mm",
            "offset": 10,
            "arrows": "both",
            "stroke": "hairline",
            "stroke_style": {"stroke_width": 2},
            "text_style": "dim_label",
        }],
        {
            "tokens": {
                "colors": {"hairline": "#123456", "label": "#654321"},
                "text_styles": {"dim_label": {"size": 10, "color": "label"}},
            },
        },
    )

    assert '<line x1="10" y1="30" x2="10" y2="40" stroke="#123456" stroke-width="2"/>' in svg
    assert '<line x1="70" y1="30" x2="70" y2="40" stroke="#123456" stroke-width="2"/>' in svg
    assert 'marker-start="url(#ah1)" marker-end="url(#ah1)"' in svg
    assert ">60 mm</text>" in svg
    assert "fill:#654321" in svg


def test_radial_and_diameter_dimensions_compute_labels() -> None:
    svg = _svg_for([
        {
            "type": "dimension",
            "kind": "radial",
            "from": [70, 60],
            "to": [50, 60],
            "prefix": "R",
        },
        {
            "type": "dimension",
            "kind": "diameter",
            "from": [110, 60],
            "to": [100, 60],
            "prefix": "D",
            "arrows": "both",
        },
    ])

    assert ">R20</text>" in svg
    assert ">D20</text>" in svg
    assert '<line x1="50" y1="60" x2="70" y2="60"' in svg
    assert '<line x1="90" y1="60" x2="110" y2="60"' in svg


def test_image_ellipse_clip_and_slice_aspect_ratio_are_emitted() -> None:
    svg = _svg_for(
        [{
            "type": "image",
            "box": [20, 10, 64, 48],
            "src": "avatar",
            "clip": {"shape": "ellipse"},
            "preserve_aspect_ratio": "xMidYMid slice",
        }],
        {
            "assets": {
                "avatar": {"data": "data:image/png;base64,iVBORw0KGgo="},
            },
            "tokens": {"colors": {"panel": "#ffeecc", "hairline": "#123456"}},
        },
    )

    assert "<clipPath" in svg
    assert '<ellipse cx="52" cy="34" rx="32" ry="24"/>' in svg
    assert '<g clip-path="url(#clip1)">' in svg
    assert 'href="data:image/png;base64,iVBORw0KGgo="' in svg
    assert 'preserveAspectRatio="xMidYMid slice"' in svg


def test_text_style_css_surface_is_emitted() -> None:
    svg = _svg_for(
        [{
            "type": "text",
            "box": [10, 10, 180, 50],
            "text": "styled text",
            "style": {
                "class": ["base_text"],
                "bold": True,
                "letter_spacing": "2px",
                "word_spacing": 3,
                "text_decoration": {
                    "line": "underline",
                    "style": "wavy",
                    "color": "hairline",
                    "thickness": "1px",
                },
                "text_transform": "uppercase",
                "text_shadow": [{"offset_x": 1, "offset_y": 2, "blur": 3, "color": "hairline"}],
                "white_space": "pre-wrap",
                "word_break": "break-word",
                "overflow_wrap": "anywhere",
                "hyphens": "auto",
                "hanging_punctuation": "allow-end",
                "hyphenate_character": "-",
                "hyphenate_limit_chars": [6, 3, 2],
                "tab_size": 4,
                "font_variant_caps": "small-caps",
                "font_variant_numeric": "tabular-nums",
                "font_variant_ligatures": "none",
                "font_feature_settings": '"kern" 1',
                "font_variation_settings": '"wght" 650',
                "font_kerning": "normal",
                "text_align_last": "center",
                "text_indent": "12px",
                "writing_mode": "horizontal-tb",
                "direction": "ltr",
                "unicode_bidi": "isolate",
                "css": "font-stretch:condensed;",
            },
        }],
        {
            "tokens": {
                "colors": {"panel": "#ffeecc", "hairline": "#123456", "ink": "#111111"},
                "styles": {"base_text": {"font_size": 18, "color": "ink"}},
            },
        },
    )

    text = svg.split("<text", 1)[1].split("</text>", 1)[0]
    assert "STYLED TEXT" in text
    assert "font-size:18px" in text
    assert "font-weight:700" in text
    assert "letter-spacing:2px" in text
    assert "word-spacing:3px" in text
    assert "text-decoration:underline wavy #123456 1px" in text
    assert "text-transform:uppercase" in text
    assert "text-shadow:1px 2px 3px #123456" in text
    assert "white-space:pre-wrap" in text
    assert "word-break:break-word" in text
    assert "overflow-wrap:anywhere" in text
    assert "hyphens:auto" in text
    assert "hanging-punctuation:allow-end" in text
    assert "hyphenate-character:-" in text
    assert "hyphenate-limit-chars:6 3 2" in text
    assert "tab-size:4px" in text
    assert "font-variant-caps:small-caps" in text
    assert "font-variant-numeric:tabular-nums" in text
    assert "font-variant-ligatures:none" in text
    assert "font-feature-settings:&quot;kern&quot; 1" in text
    assert "font-variation-settings:&quot;wght&quot; 650" in text
    assert "font-kerning:normal" in text
    assert "text-align-last:center" in text
    assert "text-indent:12px" in text
    assert "writing-mode:horizontal-tb" in text
    assert "direction:ltr" in text
    assert "unicode-bidi:isolate" in text
    assert "font-stretch:condensed" in text


def test_rect_uses_style_fill_border_radius_and_opacity() -> None:
    svg = _svg_for(
        [{
            "type": "rect",
            "box": [10, 20, 80, 40],
            "opacity": 0.6,
            "style": {
                "class": "panel_style",
                "border": {"width": 2, "style": "dashed", "color": "hairline"},
                "outline": {"width": 3, "style": "dotted", "color": "outline"},
                "outline_offset": 4,
            },
        }],
        {
            "tokens": {
                "colors": {"panel": "#ffeecc", "hairline": "#123456", "outline": "#654321"},
                "styles": {
                    "panel_style": {
                        "background_color": "panel",
                        "border_radius": 6,
                    },
                },
            },
        },
    )

    assert '<g opacity="0.6">' in svg
    rect = svg.split("<rect", 2)[2].split("/>", 1)[0]
    assert ' fill="#ffeecc"' in rect
    assert ' rx="6"' in rect
    assert ' stroke="#123456"' in rect
    assert ' stroke-width="2"' in rect
    assert ' stroke-dasharray="4 4"' in rect
    outline = svg.split("<rect", 3)[3].split("/>", 1)[0]
    assert ' x="6" y="16" width="88" height="48"' in outline
    assert ' fill="none"' in outline
    assert ' rx="10"' in outline
    assert ' stroke="#654321"' in outline
    assert ' stroke-width="3"' in outline
    assert ' stroke-dasharray="1 3"' in outline


def test_named_style_token_composes_class_styles() -> None:
    svg = _svg_for(
        [{
            "type": "rect",
            "box": [20, 20, 80, 40],
            "style": "panel_variant",
        }],
        {
            "tokens": {
                "colors": {"panel": "#ffeecc", "hairline": "#123456"},
                "styles": {
                    "panel_base": {"background_color": "panel", "border": {"width": 2, "color": "hairline"}},
                    "panel_variant": {"class": "panel_base", "border_radius": 8},
                },
            },
        },
    )

    rect = svg.split("<rect", 2)[2].split("/>", 1)[0]
    assert ' fill="#ffeecc"' in rect
    assert ' stroke="#123456"' in rect
    assert ' stroke-width="2"' in rect
    assert ' rx="8"' in rect


def test_border_shorthand_string_is_emitted() -> None:
    svg = _svg_for(
        [{
            "type": "rect",
            "box": [20, 20, 90, 45],
            "fill": "panel",
            "style": {"border": "3px dotted hairline"},
        }],
    )

    rect = svg.split("<rect", 2)[2].split("/>", 1)[0]
    assert ' stroke="#123456"' in rect
    assert ' stroke-width="3"' in rect
    assert ' stroke-dasharray="1 3"' in rect


def test_box_side_borders_are_emitted() -> None:
    svg = _svg_for(
        [{
            "type": "text",
            "box": [20, 30, 100, 40],
            "text": "side borders",
            "style": {
                "border_top": {"width": 1, "style": "solid", "color": "top"},
                "border_right": {"width": 2, "style": "dashed", "color": "right"},
                "border_bottom": {"width": 3, "style": "dotted", "color": "bottom"},
                "border_left": {"width": 4, "style": "solid", "color": "left"},
            },
        }],
        {
            "tokens": {
                "colors": {
                    "top": "#111111",
                    "right": "#222222",
                    "bottom": "#333333",
                    "left": "#444444",
                },
            },
        },
    )

    assert '<line x1="20" y1="30" x2="120" y2="30" stroke="#111111" stroke-width="1"/>' in svg
    assert '<line x1="120" y1="30" x2="120" y2="70" stroke="#222222" stroke-width="2" stroke-dasharray="4 4"/>' in svg
    assert '<line x1="20" y1="70" x2="120" y2="70" stroke="#333333" stroke-width="3" stroke-dasharray="1 3"/>' in svg
    assert '<line x1="20" y1="30" x2="20" y2="70" stroke="#444444" stroke-width="4"/>' in svg


def test_style_background_image_gradient_is_emitted_as_fill() -> None:
    svg = _svg_for(
        [{
            "type": "rect",
            "box": [20, 20, 90, 45],
            "style": {
                "background_color": "panel",
                "background_image": {
                    "kind": "linear",
                    "stops": [
                        {"color": "panel", "position": 0},
                        {"color": "hairline", "position": "100%"},
                    ],
                },
            },
        }],
    )

    assert '<linearGradient id="g1">' in svg
    assert '<stop offset="0%" stop-color="#ffeecc"/>' in svg
    assert '<stop offset="100%" stop-color="#123456"/>' in svg
    rect = svg.split("<rect", 2)[2].split("/>", 1)[0]
    assert ' fill="url(#g1)"' in rect


def test_style_background_layers_use_first_renderable_paint() -> None:
    svg = _svg_for(
        [{
            "type": "circle",
            "center": [50, 50],
            "r": 24,
            "style": {
                "background": [
                    {"image": {"url": "missing.png"}},
                    {"color": "hairline"},
                ],
            },
        }],
    )

    circle = svg.split("<circle", 1)[1].split("/>", 1)[0]
    assert ' fill="#123456"' in circle


def test_style_background_image_url_is_emitted_as_pattern_fill() -> None:
    svg = _svg_for([
        {
            "type": "rect",
            "box": [20, 20, 90, 45],
            "style": {
                "background_image": {"url": "data:image/png;base64,iVBORw0KGgo="},
                "background_size": "contain",
            },
        },
    ])

    assert '<pattern id="pat1" patternUnits="userSpaceOnUse" x="20" y="20" width="90" height="45">' in svg
    assert 'href="data:image/png;base64,iVBORw0KGgo="' in svg
    assert 'preserveAspectRatio="xMidYMid meet"' in svg
    rect = svg.split("<rect", 2)[2].split("/>", 1)[0]
    assert ' fill="url(#pat1)"' in rect


def test_style_background_image_asset_token_is_emitted_as_pattern_fill() -> None:
    svg = _svg_for(
        [{
            "type": "rect",
            "box": [12, 16, 40, 30],
            "style": {
                "background_image": "avatar",
                "background_size": "cover",
            },
        }],
        {
            "assets": {
                "avatar": {"data": "data:image/png;base64,AAAA"},
            },
            "tokens": {"colors": {"panel": "#ffeecc", "hairline": "#123456"}},
        },
    )

    assert '<pattern id="pat1" patternUnits="userSpaceOnUse" x="12" y="16" width="40" height="30">' in svg
    assert 'href="data:image/png;base64,AAAA"' in svg
    assert 'preserveAspectRatio="xMidYMid slice"' in svg
    rect = svg.split("<rect", 2)[2].split("/>", 1)[0]
    assert ' fill="url(#pat1)"' in rect


def test_style_transform_wraps_svg_objects() -> None:
    svg = _svg_for(
        [
            {
                "type": "rect",
                "box": [10, 20, 80, 40],
                "fill": "panel",
                "style": {
                    "transform": [{"fn": "rotate", "args": ["12deg"]}],
                    "transform_origin": [50, 40],
                },
            },
            {
                "type": "rect",
                "box": [100, 20, 40, 20],
                "fill": "panel",
                "style": {
                    "transform": [
                        {"fn": "translate_x", "args": [8]},
                        {"fn": "scale", "args": [1.2, 0.8]},
                    ],
                },
            },
        ],
    )

    assert '<g transform="rotate(12 50 40)">' in svg
    assert '<g transform="translate(8 0) translate(120 30) scale(1.2 0.8) translate(-120 -30)">' in svg


def test_style_compositing_wraps_svg_objects() -> None:
    svg = _svg_for([
        {
            "type": "rect",
            "box": [20, 20, 80, 40],
            "fill": "panel",
            "style": {
                "opacity": 0.45,
                "visibility": "hidden",
                "mix_blend_mode": "multiply",
                "isolation": "isolate",
                "backdrop_filter": [
                    {"fn": "blur", "value": 4},
                    {"fn": "drop_shadow", "shadow": {"offset_x": 1, "offset_y": 2, "blur": 3, "color": "hairline"}},
                ],
                "background_position": "10px 20px",
                "background_repeat": "no-repeat",
                "background_clip": "text",
                "background_origin": "content-box",
                "background_blend_mode": "screen",
                "mask": "url(#mask1)",
                "z_index": 7,
                "transform_box": "fill-box",
                "perspective": "120px",
            },
        }
    ])

    assert '<g style="' in svg
    assert "visibility:hidden" in svg
    assert "mix-blend-mode:multiply" in svg
    assert "isolation:isolate" in svg
    assert "opacity:0.45" in svg
    assert "backdrop-filter:blur(4px) drop-shadow(1px 2px 3px #123456)" in svg
    assert "background-position:10px 20px" in svg
    assert "background-repeat:no-repeat" in svg
    assert "background-clip:text" in svg
    assert "background-origin:content-box" in svg
    assert "background-blend-mode:screen" in svg
    assert "mask:url(#mask1)" in svg
    assert "z-index:7" in svg
    assert "transform-box:fill-box" in svg
    assert "perspective:120px" in svg
    assert '<rect x="20" y="20" width="80" height="40"' in svg


def test_group_layout_repositions_children_in_svg() -> None:
    svg = _svg_for([
        {
            "type": "group",
            "box": [10, 10, 80, 30],
            "layout": {"kind": "row", "gap": 6},
            "children": [
                {"type": "rect", "id": "a", "box": [0, 0, 20, 12], "fill": "panel"},
                {"type": "rect", "id": "b", "box": [0, 0, 20, 12], "fill": "hairline"},
            ],
        }
    ])

    assert '<g transform="translate(10,10)">' in svg
    assert '<rect x="0" y="0" width="20" height="12"' in svg
    assert '<g transform="translate(26,0)">' in svg


def test_style_clip_path_shapes_are_emitted() -> None:
    svg = _svg_for([
        {
            "type": "rect",
            "box": [10, 10, 80, 60],
            "fill": "panel",
            "style": {"clip_path": {"shape": "inset", "args": {"top": 5, "right": 10, "bottom": 15, "left": 20}}},
        },
        {
            "type": "circle",
            "center": [130, 40],
            "r": 30,
            "fill": "panel",
            "style": {"clip_path": {"shape": "polygon", "args": {"points": [[100, 10], [160, 10], [130, 70]]}}},
        },
        {
            "type": "path",
            "d": "M 10 90 L 80 90 L 45 115 Z",
            "fill": "panel",
            "style": {"clip_path": {"shape": "path", "args": {"d": "M 10 85 L 90 85 L 50 120 Z"}}},
        },
    ])

    assert '<clipPath id="clip1"><rect x="30" y="15" width="50" height="40"/></clipPath>' in svg
    assert '<g clip-path="url(#clip1)"><rect x="10" y="10" width="80" height="60"' in svg
    assert '<clipPath id="clip2"><polygon points="100,10 160,10 130,70"/></clipPath>' in svg
    assert '<g clip-path="url(#clip2)"><circle cx="130" cy="40" r="30"' in svg
    assert '<clipPath id="clip3"><path d="M 10 85 L 90 85 L 50 120 Z"/></clipPath>' in svg
    assert '<g clip-path="url(#clip3)"><path d="M 10 90 L 80 90 L 45 115 Z"' in svg


def test_vector_uses_style_fill_and_stroke_geometry() -> None:
    svg = _svg_for(
        [{
            "type": "path",
            "d": "M 10 10 L 80 10",
            "style": "vector_style",
        }],
        {
            "tokens": {
                "colors": {"panel": "#ffeecc", "hairline": "#123456"},
                "styles": {
                    "vector_style": {
                        "fill": "none",
                        "fill_rule": "evenodd",
                        "stroke": "hairline",
                        "stroke_width": 3,
                        "stroke_dasharray": [5, 2],
                        "stroke_dashoffset": 1.5,
                        "stroke_linecap": "round",
                        "stroke_linejoin": "bevel",
                        "stroke_miterlimit": 6,
                        "paint_order": "stroke fill markers",
                        "vector_effect": "non-scaling-stroke",
                    },
                },
            },
        },
    )

    path = svg.split("<path", 1)[1].split("/>", 1)[0]
    assert ' fill="none"' in path
    assert ' fill-rule="evenodd"' in path
    assert ' stroke="#123456"' in path
    assert ' stroke-width="3"' in path
    assert ' stroke-dasharray="5 2"' in path
    assert ' stroke-dashoffset="1.5"' in path
    assert ' stroke-linecap="round"' in path
    assert ' stroke-linejoin="bevel"' in path
    assert ' stroke-miterlimit="6"' in path
    assert ' paint-order="stroke fill markers"' in path
    assert ' vector-effect="non-scaling-stroke"' in path


def test_table_style_surface_is_emitted() -> None:
    svg = _svg_for(
        [{
            "type": "table",
            "box": [10, 10, 160, 80],
            "columns": [{"width": 90, "align": "left"}, {"width": 70, "align": "right"}],
            "header": ["Metric", "Value"],
            "rows": [["Coverage", "21"], ["Pages", "231"]],
            "cell_padding": 6,
            "stroke_style": {"color": "hairline", "width": 2},
            "style": {
                "header_fill": "brand",
                "header_text": "tbl_head",
                "cell_text": "tbl_cell",
            },
            "zebra": True,
        }],
        {
            "tokens": {
                "colors": {
                    "brand": "#005c46",
                    "hairline": "#123456",
                    "white": "#ffffff",
                    "ink": "#202020",
                },
                "text_styles": {
                    "tbl_head": {"color": "white", "font_size": 12, "font_weight": 700},
                    "tbl_cell": {"color": "ink", "font_size": 10},
                },
            },
        },
    )

    assert ' fill="#005c46"' in svg
    assert ' stroke="#123456"' in svg
    assert ' stroke-width="2"' in svg
    assert "font-size:12px" in svg
    assert "fill:#ffffff" in svg
    assert "font-weight:700" in svg
    assert "font-size:10px" in svg
    assert "fill:#202020" in svg
    assert 'x="164" y="76.667" text-anchor="end"' in svg
    assert "Coverage" in svg
    assert "231" in svg


def test_table_column_width_lengths_are_resolved() -> None:
    svg = _svg_for(
        [{
            "type": "table",
            "box": [10, 10, 160, 80],
            "columns": [
                {"width": "40%"},
                {"width": 30},
                {"width": "1fr"},
                {"width": "auto"},
            ],
            "header": ["A", "B", "C", "D"],
            "rows": [["a", "b", "c", "d"]],
            "stroke_style": {"color": "hairline", "width": 1},
        }],
    )

    assert 'x1="74" y1="10" x2="74" y2="90"' in svg
    assert 'x1="104" y1="10" x2="104" y2="90"' in svg
    assert 'x1="137" y1="10" x2="137" y2="90"' in svg


def test_shadow_and_glow_effect_filters_are_emitted() -> None:
    svg = _svg_for(
        [
            {
                "type": "rect",
                "box": [10, 10, 60, 35],
                "fill": "panel",
                "shadow": {"color": "hairline", "blur": 6, "dx": 2, "dy": 3, "opacity": 0.3},
            },
            {
                "type": "ellipse",
                "center": [120, 30],
                "rx": 28,
                "ry": 18,
                "fill": "brand",
                "glow": True,
            },
            {
                "type": "circle",
                "center": [175, 30],
                "r": 16,
                "fill": "brand",
                "shadow": "small",
                "glow": {"color": "brand", "blur": 5, "opacity": 0.5},
            },
        ],
        {
            "tokens": {
                "colors": {
                    "panel": "#ffeecc",
                    "hairline": "#123456",
                    "brand": "#005c46",
                },
            },
        },
    )

    assert '<filter id="fx1"' in svg
    assert '<filter id="fx2"' in svg
    assert '<filter id="fx3"' in svg
    assert '<filter id="fx4"' in svg
    assert 'filter="url(#fx1)"' in svg
    assert 'filter="url(#fx2)"' in svg
    assert 'filter="url(#fx3)"' in svg
    assert 'filter="url(#fx4)"' in svg
    assert 'stdDeviation="6"' in svg
    assert 'dx="2" dy="3"' in svg
    assert 'flood-color="#123456" flood-opacity="0.3"' in svg
    assert 'flood-color="#FFD700" flood-opacity="0.55"' in svg
    assert 'flood-color="#005c46" flood-opacity="0.5"' in svg


def test_style_effect_filters_are_emitted() -> None:
    svg = _svg_for(
        [
            {
                "type": "rect",
                "box": [10, 10, 60, 35],
                "fill": "panel",
                "style": "card_effects",
            },
            {
                "type": "rect",
                "box": [90, 10, 60, 35],
                "fill": "panel",
                "style": {
                    "filter": [
                        {"fn": "blur", "value": "2px"},
                        {
                            "fn": "drop_shadow",
                            "shadow": {
                                "offset_x": 3,
                                "offset_y": 4,
                                "blur": 5,
                                "color": "brand",
                            },
                        },
                    ],
                },
            },
        ],
        {
            "tokens": {
                "colors": {
                    "panel": "#ffeecc",
                    "hairline": "#123456",
                    "brand": "#005c46",
                },
                "styles": {
                    "card_effects": {
                        "box_shadow": [
                            {
                                "offset_x": 1,
                                "offset_y": 2,
                                "blur": 6,
                                "color": "hairline",
                            }
                        ],
                    }
                },
            },
        },
    )

    assert svg.count("<filter ") == 3
    assert svg.count('<g filter="url(#fx') == 3
    assert 'stdDeviation="6"' in svg
    assert 'dx="1" dy="2"' in svg
    assert 'flood-color="#123456" flood-opacity="0.25"' in svg
    assert '<feGaussianBlur in="SourceGraphic" stdDeviation="2"/>' in svg
    assert 'dx="3" dy="4"' in svg
    assert 'flood-color="#005c46" flood-opacity="0.25"' in svg


def test_style_svg_lighting_and_procedural_filters_are_emitted() -> None:
    svg = _svg_for(
        [
            {
                "type": "rect",
                "box": [10, 10, 64, 44],
                "fill": "panel",
                "style": {
                    "filter": [
                        {
                            "fn": "turbulence",
                            "base_frequency": [0.03, 0.08],
                            "num_octaves": 3,
                            "seed": 7,
                            "type": "fractalNoise",
                            "opacity": 0.4,
                        },
                        {
                            "fn": "displacement_map",
                            "base_frequency": 0.05,
                            "scale": 9,
                            "seed": 2,
                        },
                        {
                            "fn": "diffuse_lighting",
                            "surface_scale": 3,
                            "lighting_color": "brand",
                            "azimuth": 210,
                            "elevation": 35,
                        },
                        {
                            "fn": "specular_lighting",
                            "surface_scale": 2,
                            "lighting_color": "#ffffff",
                            "x": 20,
                            "y": 30,
                            "z": 80,
                            "specular_constant": 0.7,
                            "specular_exponent": 18,
                        },
                    ],
                },
            },
        ],
        {"tokens": {"colors": {"panel": "#ffeecc", "brand": "#88ccff"}}},
    )

    assert svg.count("<filter ") == 4
    assert svg.count('<g filter="url(#fx') == 4
    assert '<feTurbulence type="fractalNoise" baseFrequency="0.03 0.08" numOctaves="3" seed="7"' in svg
    assert '<feDisplacementMap in="SourceGraphic" in2="noise" scale="9"' in svg
    assert '<feDiffuseLighting in="SourceAlpha" surfaceScale="3"' in svg
    assert 'lighting-color="#88ccff"' in svg
    assert '<feDistantLight azimuth="210" elevation="35"/>' in svg
    assert '<feSpecularLighting in="SourceAlpha" surfaceScale="2"' in svg
    assert '<fePointLight x="20" y="30" z="80"/>' in svg


def test_css_filter_functions_remain_in_style_for_browser_rasterization() -> None:
    svg = _svg_for([
        {
            "type": "rect",
            "box": [10, 10, 80, 40],
            "fill": "panel",
            "style": {
                "filter": [
                    {"fn": "blur", "value": "2px"},
                    {"fn": "brightness", "value": "1.3"},
                    {"fn": "contrast", "value": "1.8"},
                    {"fn": "hue_rotate", "value": "90deg"},
                    {"fn": "turbulence", "base_frequency": 0.04},
                ],
            },
        }
    ])

    assert '<feGaussianBlur in="SourceGraphic" stdDeviation="2"/>' in svg
    assert '<feTurbulence' in svg
    assert "filter:brightness(1.3) contrast(1.8) hue-rotate(90deg)" in svg
