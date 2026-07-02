#!/usr/bin/env python3
"""Regression coverage for LaTeX/TikZ fill-rule parity."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig():
    color = ColorResolver({"panel": "#123456"})
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


def test_path_fill_rule_evenodd_maps_to_tikz_even_odd_rule():
    tex = _fig().render({
        "type": "path",
        "d": "M 0 0 L 40 0 L 40 40 L 0 40 Z M 10 10 L 30 10 L 30 30 L 10 30 Z",
        "fill": "panel",
        "fill_rule": "evenodd",
    })

    assert "fill={rgb,255:red,18;green,52;blue,86}" in tex
    assert "even odd rule" in tex
    assert tex.index("fill={rgb,255:red,18;green,52;blue,86}") < tex.index("even odd rule")


def test_style_fill_rule_even_odd_maps_to_tikz_even_odd_rule():
    tex = _fig().render({
        "type": "path",
        "d": "M 0 0 L 40 0 L 40 40 L 0 40 Z M 10 10 L 30 10 L 30 30 L 10 30 Z",
        "fill": "#abcdef",
        "style": {"fill_rule": "even odd"},
    })

    assert "fill={rgb,255:red,171;green,205;blue,239}" in tex
    assert "even odd rule" in tex


def test_nonzero_fill_rule_uses_tikz_default():
    tex = _fig().render({
        "type": "path",
        "d": "M 0 0 L 40 0 L 40 40 L 0 40 Z",
        "fill": "panel",
        "fill_rule": "nonzero",
    })

    assert "fill={rgb,255:red,18;green,52;blue,86}" in tex
    assert "even odd rule" not in tex
