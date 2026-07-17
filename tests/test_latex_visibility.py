#!/usr/bin/env python3
"""Regression coverage for visibility/display suppression in TikZ output."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from frameforge.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig(styles=None):
    color = ColorResolver({"panel": "#ffeecc", "ink": "#123456"})
    return FigureTikz(color, TextStyleResolver({}, styles or {}, color), {})


def test_direct_visibility_hidden_suppresses_tikz_object():
    tex = _fig().render({
        "type": "rect",
        "box": [10, 20, 30, 40],
        "fill": "panel",
        "visibility": "hidden",
    })

    assert tex == ""


def test_named_style_visibility_hidden_suppresses_tikz_object():
    tex = _fig({"hidden": {"visibility": "hidden"}}).render({
        "type": "circle",
        "center": [10, 10],
        "r": 5,
        "fill": "ink",
        "style": "hidden",
    })

    assert tex == ""


def test_display_none_suppresses_group_children():
    tex = _fig().render({
        "type": "group",
        "display": "none",
        "children": [
            {"type": "rect", "box": [0, 0, 10, 10], "fill": "panel"},
        ],
    })

    assert tex == ""
