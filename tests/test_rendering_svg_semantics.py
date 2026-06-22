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
    assert 'stroke="#123456"' in svg
    assert 'stroke-width="4"' in svg
    assert 'stroke-opacity="0.35"' in svg


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
                "font_variant_caps": "small-caps",
                "font_kerning": "normal",
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
    assert "font-variant-caps:small-caps" in text
    assert "font-kerning:normal" in text
    assert "font-stretch:condensed" in text
