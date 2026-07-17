#!/usr/bin/env python3
"""text_block/text_runs take the neutral style dict, not a pre-formatted SVG style
string (ADR 0001 3b-5c — the last painter-parameter neutralization). Pins that
SvgPainter formats the font internally and produces the same SVG it did before."""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge.rendering.infrastructure.painters.svg import SvgPainter  # noqa: E402

ST = {"family": "serif", "size": 12, "weight": "bold", "italic": False,
      "color": "#222222", "align": "start"}


def test_text_block_formats_st_dict_internally():
    p = SvgPainter(ColorResolver({}))
    out = p.text_block(40, "start", ST, 12, ["one", "two"], 10, 14.4)
    # font formatted from the dict at the given size; weight emitted, two lines
    assert 'font-family:serif;font-size:12px;fill:#222222;font-weight:bold' in out
    assert out.count("<tspan") == 2 and 'dy="14.4"' in out
    assert out.startswith('<text y="40" text-anchor="start"')


def test_text_runs_formats_each_run_dict():
    p = SvgPainter(ColorResolver({}))
    em = {**ST, "italic": True}
    out = p.text_runs(40, "start", 10, ST, 12, [("a", ST), ("b", em)])
    assert out.count("<tspan") == 2
    assert "font-style:italic" in out          # the second run's dict formatted
    assert 'x="10"' in out                     # first run carries the anchor x
