#!/usr/bin/env python3
"""The table() widget themes its header through ``theme=``.

The widget lowers to a TableObject whose header the renderer styled with a fixed
blue (``#3b6ea5``), so ``theme=`` was silently ignored for the most visible part
of a table. The widget now carries a theme-derived ``style`` (header fill + text)
so a custom theme actually reaches the rendered header.
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import table  # noqa: E402
from framegraph.sdk.widgets import default_theme  # noqa: E402


def test_table_header_fill_follows_the_theme():
    th = replace(default_theme(), ink="#112233", surface="#FAFAFA")
    obj = table([0, 0, 200, 120], ["A", "B"], [["1", "2"], ["3", "4"]], theme=th)

    style = obj["style"]
    assert style["header_fill"] == "#112233"          # theme ink, not the fixed blue
    assert style["header_text"]["color"] == "#FAFAFA"  # readable on the dark header


def test_table_default_theme_is_not_the_hardcoded_blue():
    obj = table([0, 0, 200, 120], ["A", "B"], [["1", "2"]])
    assert obj["style"]["header_fill"] == default_theme().ink
    assert obj["style"]["header_fill"] != "#3b6ea5"


def test_table_header_renders_in_the_theme_colour():
    """End-to-end: the themed header fill reaches the rendered SVG."""
    from framegraph.sdk import DocumentBuilder, render_page_svgs

    th = replace(default_theme(), ink="#0A7E33")
    builder = DocumentBuilder(title="Themed table", profile="deck")
    page = builder.page("p", canvas={"size": [320, 200], "units": "px"},
                        coordinate_mode="absolute")
    page.layer("main").add(
        table([20, 20, 280, 150], ["Name", "Value"], [["a", "1"], ["b", "2"]], theme=th)
    )
    svg = render_page_svgs(builder.build())[0]
    assert "#0A7E33" in svg
