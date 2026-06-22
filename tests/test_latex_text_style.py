#!/usr/bin/env python3
"""Regression coverage for text style parity in TikZ output."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(styles=None):
    color = ColorResolver({})
    return FigureTikz(color, TextStyleResolver({}, styles or {}, color), {})


def test_text_transform_uppercase_applies_before_tikz_escape():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "styled_text",
        "style": {"text_transform": "uppercase"},
    })

    assert "{STYLED\\_TEXT}" in tex
    assert "{styled\\_text}" not in tex


def test_text_transform_lowercase_uses_named_style():
    tex = _fig({"caption": {"text_transform": "lowercase"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "MiXeD",
        "style": "caption",
    })

    assert "{mixed}" in tex
    assert "{MiXeD}" not in tex


def test_text_transform_capitalize_applies_to_spans():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 160, 30],
        "spans": [
            {"text": "first run", "style": {"text_transform": "capitalize"}},
            {"text": " SECOND", "style": {"text_transform": "lowercase"}},
        ],
    })

    assert "{First Run}" in tex
    assert "{ second}" in tex
    assert "{first run}" not in tex


def test_text_decoration_underline_wraps_tikz_text_content():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "under_score",
        "style": {"text_decoration": {"line": "underline"}},
    })

    assert "{\\underline{under\\_score}}" in tex


def test_font_variant_small_caps_maps_to_tikz_font_shape():
    tex = _fig({"label": {"font_variant_caps": "small-caps"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Caps",
        "style": "label",
    })

    assert "\\scshape" in tex
    assert "{Caps}" in tex


def test_alpha_text_color_maps_to_tikz_text_opacity():
    tex = _fig({"muted": {"color": "#12345680"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Muted",
        "style": "muted",
    })

    assert "text={rgb,255:red,18;green,52;blue,86}" in tex
    assert "text opacity=0.502" in tex


def test_alpha_text_color_applies_to_spans():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "spans": [
            {"text": "Run", "style": {"color": "#abcdef40"}},
        ],
    })

    assert "text={rgb,255:red,171;green,205;blue,239}" in tex
    assert "text opacity=0.251" in tex
