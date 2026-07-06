#!/usr/bin/env python3
"""Captioned figures, images and tables become real, numbered LaTeX floats.

The flow backend used to emit figures/tables as centred inline blocks with a
hand-styled caption line — so they carried no float number, were not reachable
by ``\\ref``, and never reached ``\\listoffigures``. They are now ``figure`` /
``table`` floats whose ``\\caption`` auto-numbers them and whose ``\\label``
follows the caption (capturing the float number, not the section's).

Renderer-only import — evict a models-module shadow first, per test_render_cli.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402

RECT = {"type": "rect", "box": [0, 0, 100, 50], "fill": "#cccccc"}


def _doc(*story):
    return {"dsl": "FrameGraph", "version": "2.2.0", "profile": "book", "title": "f",
            "pages": [{"mode": "flow", "id": "p", "story": list(story)}]}


def test_captioned_figure_is_a_numbered_float_with_label_after_caption():
    tex = transpile(_doc(
        {"type": "figure", "object": RECT, "size": [100, 50],
         "caption": "a drawing", "id": "fig-x"}))
    assert "\\begin{figure}[H]" in tex and "\\end{figure}" in tex
    assert "\\caption{a drawing}\\label{fg:fig-x}" in tex     # label AFTER caption
    assert "\\begin{tikzpicture}" in tex


def test_captioned_table_float_puts_caption_above():
    tex = transpile(_doc(
        {"type": "table", "header": ["A", "B"], "rows": [["1", "2"]],
         "caption": "tab cap", "id": "tab-x"}))
    fig = tex.index("\\begin{table}[H]")
    cap = tex.index("\\caption{tab cap}")
    tab = tex.index("\\begin{tabular}")
    assert fig < cap < tab                                    # caption above tabular
    assert "\\label{fg:tab-x}" in tex


def test_captioned_image_is_a_figure_float():
    tex = transpile({
        "dsl": "FrameGraph", "version": "2.2.0", "profile": "book", "title": "i",
        "defs": {"assets": {"logo": {"src": "logo.png"}}},
        "pages": [{"mode": "flow", "id": "p", "story": [
            {"type": "image", "src": "logo", "caption": "shot", "credit": "me"}]}]})
    assert "\\begin{figure}[H]" in tex
    assert "\\caption{shot}" in tex
    assert "\\includegraphics" in tex
    assert "me" in tex                                        # credit kept


def test_uncaptioned_figure_stays_inline_not_a_float():
    tex = transpile(_doc({"type": "figure", "object": RECT, "size": [100, 50]}))
    assert "\\begin{figure}" not in tex
    assert "\\begin{center}" in tex


def test_toc_of_selects_list_of_figures_or_tables():
    assert "\\listoffigures" in transpile(_doc({"type": "toc", "of": "figures"}))
    assert "\\listoftables" in transpile(_doc({"type": "toc", "of": "tables"}))
    assert "\\tableofcontents" in transpile(_doc({"type": "toc"}))
