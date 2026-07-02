#!/usr/bin/env python3
"""A titled bibliography prints its heading exactly once.

`\\begin{thebibliography}` already prints `\\section*{\\refname}`, so emitting a
separate styled title above it wrote the word twice ("References / References").
The backend now points `\\refname` at the title and registers it in the TOC.

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


def _doc(bib):
    return {"dsl": "FrameGraph", "version": "2.2.0", "profile": "book", "title": "b",
            "pages": [{"mode": "flow", "id": "p", "story": [bib]}]}


def test_titled_bibliography_heading_is_not_duplicated():
    tex = transpile(_doc({
        "type": "bibliography", "title": "References",
        "entries": [{"id": "k", "text": "An entry."}]}))
    assert "\\renewcommand{\\refname}{References}" in tex
    assert "\\addcontentsline{toc}{section}{References}" in tex
    assert "\\begin{thebibliography}{99}" in tex
    # the title must NOT also be emitted as a separate styled heading line
    assert tex.count("References") == 2          # \refname + \addcontentsline only
    assert "\\bibitem{k}An entry." in tex


def test_untitled_bibliography_keeps_default_heading():
    tex = transpile(_doc({"type": "bibliography",
                          "entries": [{"id": "k", "text": "x"}]}))
    assert "\\renewcommand{\\refname}" not in tex
    assert "\\begin{thebibliography}{99}" in tex
