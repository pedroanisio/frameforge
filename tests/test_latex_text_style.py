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


def test_text_decoration_double_underline_uses_ulem_double_rule():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "double",
        "style": {"text_decoration": {"line": "underline", "style": "double"}},
    })

    assert "{\\uuline{double}}" in tex
    assert "\\underline{double}" not in tex


def test_text_decoration_overline_wraps_text_content():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "over",
        "style": {"text_decoration": {"line": ["overline", "line-through"], "style": "double"}},
    })

    assert "{\\sout{\\overline{\\mbox{over}}}}" in tex


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


def test_font_variant_numeric_maps_combined_number_features():
    tex = _fig({"metric": {"font_variant_numeric": "lining-nums proportional-nums slashed-zero"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "0123456789",
        "style": "metric",
    })

    assert "\\addfontfeatures{Numbers=Lining}" in tex
    assert "\\addfontfeatures{Numbers=Proportional}" in tex
    assert "\\addfontfeatures{Numbers=SlashedZero}" in tex


def test_font_variant_ligatures_none_maps_to_fontspec_feature():
    tex = _fig({"label": {"font_variant_ligatures": "none"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "office",
        "style": "label",
    })

    assert "\\addfontfeatures{Ligatures=NoCommon}" in tex
    assert "{office}" in tex


def test_font_variant_ligatures_maps_combined_fontspec_features():
    tex = _fig({
        "label": {
            "font_variant_ligatures": (
                "common-ligatures discretionary-ligatures historical-ligatures no-contextual"
            ),
        },
    }).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "office",
        "style": "label",
    })

    assert "\\addfontfeatures{Ligatures=Common}" in tex
    assert "\\addfontfeatures{Ligatures=Rare}" in tex
    assert "\\addfontfeatures{Ligatures=Historic}" in tex
    assert "\\addfontfeatures{Ligatures=NoContextual}" in tex


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


def test_font_feature_settings_map_to_fontspec_raw_features():
    enabled = _fig({"label": {"font_feature_settings": '"dlig" 1, "liga" 1, "calt" 1'}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "office",
        "style": "label",
    })
    disabled = _fig({"label": {"font_feature_settings": '"liga" 0'}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "office",
        "style": "label",
    })

    assert "\\addfontfeatures{RawFeature={+dlig,+liga,+calt}}" in enabled
    assert "\\addfontfeatures{RawFeature={-liga}}" in disabled


def test_font_variation_settings_map_to_fontspec_axis_features():
    tex = _fig({"label": {"font_variation_settings": '"wght" 350, "slnt" -6, "opsz" 28'}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Variable",
        "style": "label",
    })

    assert "\\addfontfeatures{RawFeature={+axis={wght=350,slnt=-6,opsz=28}}}" in tex
    assert "{Variable}" in tex


def test_font_variation_settings_ignore_malformed_axes():
    tex = _fig({"label": {"font_variation_settings": '"wght" 650, invalid, "opsz" 12.5'}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Variable",
        "style": "label",
    })

    assert "\\addfontfeatures{RawFeature={+axis={wght=650,opsz=12.5}}}" in tex
    assert "invalid" not in tex


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


def test_letter_spacing_maps_to_fontspec_letterspace():
    tracked = _fig({"label": {"letter_spacing": 4}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Tracked",
        "style": "label",
    })
    tightened = _fig({"label": {"letter_spacing": "-0.2px"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "Tight",
        "style": "label",
    })

    assert "\\addfontfeatures{LetterSpace=4}" in tracked
    assert "\\addfontfeatures{LetterSpace=-0.2}" in tightened


def test_word_spacing_maps_to_tex_spaceskip():
    tex = _fig({"label": {"word_spacing": 12}}).render({
        "type": "text",
        "box": [10, 20, 160, 30],
        "text": "wide words",
        "style": "label",
    })

    assert "{\\spaceskip=12pt wide words}" in tex


def test_text_indent_maps_to_initial_hspace():
    tex = _fig({"label": {"text_indent": "12px"}}).render({
        "type": "text",
        "box": [10, 20, 160, 30],
        "text": "indented",
        "style": "label",
    })

    assert "{\\hspace*{12pt}indented}" in tex


def test_preformatted_white_space_preserves_newlines():
    tex = _fig({"label": {"white_space": "pre-wrap"}}).render({
        "type": "text",
        "box": [10, 20, 160, 40],
        "text": "Line 1\nLine 2",
        "style": "label",
    })

    assert "{Line 1\\\\Line 2}" in tex


def test_word_break_break_all_inserts_discretionary_breaks():
    tex = _fig({"label": {"word_break": "break-all"}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "Long",
        "style": "label",
    })

    assert r"L\allowbreak{}o\allowbreak{}n\allowbreak{}g" in tex


def test_overflow_wrap_anywhere_inserts_discretionary_breaks():
    tex = _fig({"label": {"overflow_wrap": "anywhere"}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "AB",
        "style": "label",
    })

    assert r"A\allowbreak{}B" in tex


def test_word_break_preserves_escaped_special_character_sequences():
    tex = _fig({"label": {"word_break": "break-word"}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "a_b",
        "style": "label",
    })

    assert r"a\allowbreak{}\_\allowbreak{}b" in tex
    assert r"\\allowbreak{}_" not in tex


def test_tab_size_maps_to_explicit_horizontal_skip():
    tex = _fig({"label": {"size": 10, "tab_size": 4}}).render({
        "type": "text",
        "box": [10, 20, 160, 30],
        "text": "A\tB",
        "style": "label",
    })

    assert "{A\\hspace*{20.8pt}B}" in tex
    assert "\t" not in tex


def test_tab_size_applies_to_spans():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 160, 30],
        "spans": [
            {"text": "A\tB", "style": {"size": 10, "tab_size": 2}},
        ],
    })

    assert "{A\\hspace*{10.4pt}B}" in tex


def test_hyphens_none_disables_automatic_and_explicit_hyphen_breaks():
    tex = _fig({"label": {"hyphens": "none"}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "well-known hyphenation",
        "style": "label",
    })

    assert "\\hyphenpenalty=10000\\relax" in tex
    assert "\\exhyphenpenalty=10000\\relax" in tex
    assert "well-known hyphenation" in tex


def test_hyphens_manual_disables_automatic_hyphen_breaks_only():
    tex = _fig({"label": {"hyphens": "manual"}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "well-known hyphenation",
        "style": "label",
    })

    assert "\\hyphenpenalty=10000\\relax" in tex
    assert "\\exhyphenpenalty=10000\\relax" not in tex


def test_hyphenate_limit_chars_maps_to_tex_hyphen_minima():
    tex = _fig({"label": {"hyphenate_limit_chars": [6, 3, 2]}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "hyphenation",
        "style": "label",
    })

    assert "\\lefthyphenmin=3\\relax" in tex
    assert "\\righthyphenmin=2\\relax" in tex


def test_hyphenate_character_maps_to_tex_font_hyphenchar():
    tex = _fig({"label": {"hyphenate_character": "~"}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "hyphenation",
        "style": "label",
    })

    assert "\\hyphenchar\\font=126\\relax" in tex
    assert "hyphenation" in tex


def test_hyphenate_character_uses_first_character():
    tex = _fig({"label": {"hyphenate_character": "->"}}).render({
        "type": "text",
        "box": [10, 20, 80, 30],
        "text": "hyphenation",
        "style": "label",
    })

    assert "\\hyphenchar\\font=45\\relax" in tex


def test_vertical_align_places_text_within_box():
    top = _fig({"label": {"size": 10, "vertical_align": "top"}}).render({
        "type": "text",
        "box": [10, 20, 120, 40],
        "text": "Top",
        "style": "label",
    })
    middle = _fig({"label": {"size": 10, "vertical_align": "middle"}}).render({
        "type": "text",
        "box": [10, 20, 120, 40],
        "text": "Middle",
        "style": "label",
    })
    bottom = _fig({"label": {"size": 10, "vertical_align": "bottom"}}).render({
        "type": "text",
        "box": [10, 20, 120, 40],
        "text": "Bottom",
        "style": "label",
    })

    assert "at (10,25) {Top}" in top
    assert "at (10,40) {Middle}" in middle
    assert "at (10,55) {Bottom}" in bottom


def test_writing_mode_maps_to_tikz_node_rotation():
    vertical_rl = _fig({"label": {"writing_mode": "vertical-rl"}}).render({
        "type": "text",
        "box": [10, 20, 120, 40],
        "text": "Vertical",
        "style": "label",
    })
    vertical_lr = _fig({"label": {"writing_mode": "vertical-lr"}}).render({
        "type": "text",
        "box": [10, 20, 120, 40],
        "text": "Vertical",
        "style": "label",
    })

    assert "rotate=-90" in vertical_rl
    assert "rotate=90" in vertical_lr


def test_writing_mode_applies_to_spans():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 160, 30],
        "spans": [
            {"text": "Side", "style": {"writing_mode": "vertical-lr"}},
        ],
    })

    assert "rotate=90" in tex
    assert "{Side}" in tex


def test_direction_maps_to_guarded_tex_textdir():
    rtl = _fig({"label": {"direction": "rtl"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "rtl text",
        "style": "label",
    })
    ltr = _fig({"label": {"direction": "ltr"}}).render({
        "type": "text",
        "box": [10, 20, 120, 30],
        "text": "hello",
        "style": "label",
    })

    assert "{\\ifdefined\\textdir\\textdir TRT\\fi rtl text}" in rtl
    assert "{\\ifdefined\\textdir\\textdir TLT\\fi hello}" in ltr


def test_direction_applies_to_spans():
    tex = _fig().render({
        "type": "text",
        "box": [10, 20, 160, 30],
        "spans": [
            {"text": "span rtl", "style": {"direction": "rtl"}},
        ],
    })

    assert "{\\ifdefined\\textdir\\textdir TRT\\fi span rtl}" in tex


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
