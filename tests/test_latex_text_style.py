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


def test_text_decoration_wavy_underline_uses_ulem_wave():
    color = ColorResolver({"accent": "#123456"})
    fig = FigureTikz(color, TextStyleResolver({}, {}, color), {})
    tex = fig.render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "wavy",
        "style": {"text_decoration": {"line": "underline", "style": "wavy", "color": "accent", "thickness": 2}},
    })

    assert "{\\uwave{wavy}}" in tex
    assert "\\underline{wavy}" not in tex


def test_text_decoration_line_through_wraps_tikz_text_content():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "deleted",
        "style": {"text_decoration": {"line": "line-through"}},
    })

    assert "{\\sout{deleted}}" in tex


def test_text_decoration_combines_underline_and_line_through():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "marked",
        "style": {"text_decoration": {"line": ["underline", "line-through"]}},
    })

    assert "{\\sout{\\underline{marked}}}" in tex


def test_font_variant_small_caps_maps_to_tikz_font_shape():
    tex = _fig({"label": {"font_variant_caps": "small-caps"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Caps",
        "style": "label",
    })

    assert "\\scshape" in tex
    assert "{Caps}" in tex


def test_font_variant_numeric_maps_to_fontspec_feature():
    tabular = _fig({"metric": {"font_variant_numeric": "tabular-nums"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "0123456789",
        "style": "metric",
    })
    oldstyle = _fig({"metric": {"font_variant_numeric": "oldstyle-nums"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "0123456789",
        "style": "metric",
    })

    assert "\\addfontfeatures{Numbers=Monospaced}" in tabular
    assert "\\addfontfeatures{Numbers=OldStyle}" in oldstyle
    assert "{0123456789}" in tabular
    assert "{0123456789}" in oldstyle


def test_font_variant_ligatures_none_maps_to_fontspec_feature():
    tex = _fig({"label": {"font_variant_ligatures": "none"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "office",
        "style": "label",
    })

    assert "\\addfontfeatures{Ligatures=NoCommon}" in tex
    assert "{office}" in tex


def test_font_kerning_maps_to_fontspec_feature():
    disabled = _fig({"label": {"font_kerning": "none"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "AV",
        "style": "label",
    })
    enabled = _fig({"label": {"font_kerning": "normal"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "AV",
        "style": "label",
    })

    assert "\\addfontfeatures{Kerning=Off}" in disabled
    assert "\\addfontfeatures{Kerning=On}" in enabled


def test_font_stretch_maps_to_fontspec_fake_stretch():
    condensed = _fig({"label": {"font_stretch": "condensed"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Condensed",
        "style": "label",
    })
    expanded = _fig({"label": {"font_stretch": "expanded"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Expanded",
        "style": "label",
    })
    percent = _fig({"label": {"font_stretch": "125%"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Percent",
        "style": "label",
    })

    assert "\\addfontfeatures{FakeStretch=0.75}" in condensed
    assert "\\addfontfeatures{FakeStretch=1.25}" in expanded
    assert "\\addfontfeatures{FakeStretch=1.25}" in percent


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
