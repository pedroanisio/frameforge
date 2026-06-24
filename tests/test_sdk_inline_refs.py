#!/usr/bin/env python3
"""SDK cross-reference + citation inline authoring.

`md()` gained a FrameGraph extension — ``{ref:id}`` / ``{pageref:id}`` /
``{nameref:id}`` / ``{cite:key}`` — and explicit ``ref()`` / ``cite()`` builders,
so a flow author can reference figures/sections/pages and cite a bibliography
inline. The LaTeX backend already lowers these to ``\\ref`` / ``\\pageref`` /
``\\nameref`` / ``\\cite``; this pins the authoring surface and the round trip.

Renderer-only import (the `framegraph` package must win) — evict a models-module
shadow first, per test_render_cli.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.sdk import cite, md, ref  # noqa: E402
from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402


# -- the builders --------------------------------------------------------- #
def test_ref_builder_show_modes():
    assert ref("fig-1") == {"kind": "ref", "target": "fig-1"}
    assert ref("fig-1", show="page") == {"kind": "ref", "target": "fig-1", "show": "page"}
    assert ref("sec-2", show="title")["show"] == "title"


def test_cite_builder_with_locator():
    assert cite("knuth1981") == {"kind": "cite", "key": "knuth1981"}
    assert cite("k", locator="p. 12")["locator"] == "p. 12"


# -- the md() extension --------------------------------------------------- #
def test_md_parses_ref_pageref_nameref_cite():
    out = md("see {ref:fig-1} on {pageref:fig-1}, {nameref:sec-2}, and {cite:knuth1981}")
    kinds = [p.get("kind") if isinstance(p, dict) else "str" for p in out]
    assert kinds == ["str", "ref", "str", "ref", "str", "ref", "str", "cite"]
    assert out[1] == {"kind": "ref", "target": "fig-1"}
    assert out[3] == {"kind": "ref", "target": "fig-1", "show": "page"}
    assert out[5] == {"kind": "ref", "target": "sec-2", "show": "title"}
    assert out[7] == {"kind": "cite", "key": "knuth1981"}


def test_md_still_handles_code_math_link_and_plain():
    assert md("plain only") == ["plain only"]
    out = md("a `x` $y$ [L](http://h)")
    assert {"kind": "code", "text": "x"} in out
    assert {"kind": "math", "tex": "y"} in out
    assert any(isinstance(p, dict) and p.get("kind") == "link" for p in out)


# -- the LaTeX round trip ------------------------------------------------- #
def test_backend_lowers_refs_and_cite():
    doc = {"dsl": "FrameGraph", "version": "2.2.0", "profile": "book", "title": "r",
           "pages": [{"mode": "flow", "id": "p", "story": [
               {"type": "paragraph", "spans": md(
                   "Fig {ref:fig-x} p {pageref:fig-x}, {nameref:sec-y} {cite:k1}")}]}]}
    tex = transpile(doc)
    assert "\\ref{fg:fig-x}" in tex
    assert "\\pageref{fg:fig-x}" in tex
    assert "\\nameref{fg:sec-y}" in tex
    assert "\\cite{k1}" in tex
