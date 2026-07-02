#!/usr/bin/env python3
"""Text-fit telemetry surfaced by ``conform.render_pages_with_stats``.

A non-zero ``clipped`` means the renderer truncated text to its box. The render
still succeeds (``ok:true``), so without this telemetry the truncation is invisible
to an author — these tests pin that the count is produced and reflects real clips.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder  # noqa: E402
from framegraph.sdk.conform import render_page_svgs, render_pages_with_stats  # noqa: E402


def _clipping_doc():
    """A long line that cannot fit a 16px-tall box — the renderer clips it."""
    builder = DocumentBuilder(title="clip", profile="diagram")
    layer = builder.page(
        "p", canvas={"size": [200, 120], "units": "px"}, coordinate_mode="absolute"
    ).layer("m")
    layer.text(
        [10, 10, 120, 16],
        "This is a long sentence that cannot fit inside a sixteen pixel tall box "
        "and will be clipped to a single line by the renderer.",
        style={"font_family": ["DejaVu Sans", "Arial"], "font_size": 14},
    )
    return builder.build()


def test_render_pages_with_stats_returns_text_fit_telemetry():
    svgs, stats = render_pages_with_stats(_clipping_doc())
    assert isinstance(svgs, list) and svgs
    assert {"total", "wrapped", "shrunk", "clipped", "contained"} <= set(stats)
    assert stats["total"] >= 1
    assert stats["clipped"] >= 1, stats


def test_render_page_svgs_delegates_to_stats_variant():
    doc = _clipping_doc()
    assert render_page_svgs(doc) == render_pages_with_stats(doc)[0]
