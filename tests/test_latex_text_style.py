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
