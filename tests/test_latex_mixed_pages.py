#!/usr/bin/env python3
"""LaTeX transpiler: mixed page-mode + flow documents (books).

Regression net for the bug where ``build()`` was binary — if any page had
``mode: flow`` it emitted only the first flow story and silently dropped every
``mode: page`` page (a book lost its cover / colophon / contents / plates). The
transpiler now walks every page in order, full-bleeding page-mode sheets via a
per-page ``\\newgeometry`` margin toggle while the flow chapters keep the body
margins.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402

A4 = {"size": [595, 842], "units": "pt"}


def _page_mode(pid, marker):
    return {"id": pid, "mode": "page", "canvas": A4, "layers": [{"id": "main", "objects": [
        {"type": "rect", "box": [0, 0, 595, 842], "fill": "#111111"},
        {"type": "text", "box": [40, 40, 500, 40], "text": marker,
         "style": {"font_size": 24, "color": "#ffffff"}}]}]}


def _flow_page(pid, heading, body):
    return {"id": pid, "mode": "flow", "canvas": A4, "story": [
        {"type": "heading", "level": 1, "text": heading},
        {"type": "paragraph", "text": body}]}


def _doc(pages, **extra):
    return {"dsl": "FrameGraph", "version": "2.2.0", "profile": "book",
            "title": "T", "pages": pages, **extra}


# ─────────────────────────────────────────────────────────────
# the fix: a mixed book renders page-mode front/back matter AND flow
# ─────────────────────────────────────────────────────────────
def test_mixed_book_renders_all_pages_not_just_the_flow():
    tex = transpile(_doc([
        _page_mode("cover", "COVERMARKER"),
        _flow_page("ch1", "Chapter Alpha", "The body of the first chapter."),
        _page_mode("back", "BACKMARKER"),
    ]))
    # every page's content is present — the old code dropped the two page-mode pages
    assert "COVERMARKER" in tex
    assert "Chapter Alpha" in tex
    assert "BACKMARKER" in tex
    # page-mode sheets inside a margined doc toggle to full-bleed then restore
    assert tex.count("\\newgeometry") == 2          # one per page-mode page
    assert "\\restoregeometry" in tex
    assert "\\thispagestyle{empty}" in tex
    # the document base geometry keeps the body margins (flow present)
    assert "margin=56pt" in tex


def test_multiple_flow_chapters_all_render():
    # regression on the old `next(p for ... mode=='flow')` picking only the FIRST flow
    tex = transpile(_doc([
        _flow_page("ch1", "Chapter Alpha", "First."),
        _flow_page("ch2", "Chapter Beta", "Second."),
    ]))
    assert "Chapter Alpha" in tex
    assert "Chapter Beta" in tex
    assert "\\clearpage" in tex                      # a page break between the chapters


def test_pure_flow_doc_uses_body_margins_and_no_newgeometry():
    tex = transpile(_doc([_flow_page("ch1", "Only Chapter", "Body.")]))
    assert "Only Chapter" in tex
    assert "margin=56pt" in tex
    assert "\\newgeometry" not in tex                # nothing to toggle


def test_pure_page_mode_doc_is_full_bleed_and_unchanged():
    tex = transpile(_doc([_page_mode("p1", "ONE"), _page_mode("p2", "TWO")]))
    assert "ONE" in tex and "TWO" in tex
    assert "margin=0pt" in tex                       # base geometry is full-bleed
    assert "\\newgeometry" not in tex                # no per-page toggle needed


def test_oversized_page_sheet_is_contain_scaled_to_the_flow_paper():
    """A page-mode sheet larger than the flow paper (geometry cannot change
    paper size per page) must be contain-scaled via \\resizebox — not deferred
    to a blank leaf and clipped, which is what an oversized box does raw.
    Found by the capability tour: US-Letter-px sheets inside an A4 flow book."""
    letter_px = {"id": "big", "mode": "page",
                 "canvas": {"size": [816, 1056], "units": "px"},
                 "layers": [{"id": "main", "objects": [
                     {"type": "rect", "box": [0, 0, 816, 1056], "fill": "#eee"}]}]}
    tex = transpile(_doc([_flow_page("f", "H", "B"), letter_px]))
    assert "\\resizebox{" in tex
    # a sheet that already fits must NOT be scaled
    tex2 = transpile(_doc([_flow_page("f", "H", "B"), _page_mode("p", "M")]))
    assert "\\resizebox{" not in tex2
