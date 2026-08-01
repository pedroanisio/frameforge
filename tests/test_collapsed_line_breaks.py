"""Authored `\\n` under a collapsing `white_space` must be REPORTED, not silent.

The spec (docs/spec/frameforge-v2-spec.md §"Authored line breaks and spacing")
makes `white_space: normal` collapse authored newlines and space runs, CSS-style.
That is conformant — but it is also invisible: a monospace ledger authored with
`\\n` reflows into one paragraph and nothing anywhere says so. Silent failure is
the exact class CLAUDE.md's core principles ban, so the renderer emits a typed
`collapsed_line_breaks` warning and the author can act on it.
"""
from __future__ import annotations

from frameforge_render.application.renderer import Renderer


LEDGER = "DS   892bdce5  Design Systems\nHX   ee74dc0b  Human-Centric AI"


def _doc(style):
    return {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [400, 200], "units": "px"},
        "layers": [{"id": "l", "objects": [
            {"type": "text", "id": "ledger", "box": [10, 10, 380, 80],
             "text": LEDGER, "style": style}]}],
    }]}


def _warnings(style):
    doc = _doc(style)
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    return [w for w in r.diagnostics["warnings"] if w["kind"] == "collapsed_line_breaks"]


def test_collapsing_white_space_reports_the_lost_line_breaks():
    warned = _warnings({"font_size": 9})
    assert len(warned) == 1
    assert warned[0]["object"] == "ledger"
    assert warned[0]["line_breaks"] == 1
    assert "white_space" in warned[0]["message"]


def test_preserving_white_space_is_silent():
    assert _warnings({"font_size": 9, "white_space": "pre-wrap"}) == []


def test_text_without_newlines_is_silent():
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [400, 200], "units": "px"},
        "layers": [{"id": "l", "objects": [
            {"type": "text", "box": [10, 10, 380, 80], "text": "one line",
             "style": {"font_size": 9}}]}],
    }]}
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert [w for w in r.diagnostics["warnings"] if w["kind"] == "collapsed_line_breaks"] == []


def test_preserved_newlines_still_lay_out_as_separate_lines():
    """Guard the conformant behaviour the warning points at: `pre-wrap` keeps
    both rows and the collapsing default merges them."""
    doc = _doc({"font_size": 9, "white_space": "pre-wrap"})
    r = Renderer(doc, ".")
    svg = "".join(r.render_page(doc["pages"][0]))
    assert svg.count("<tspan") >= 2

    doc = _doc({"font_size": 9})
    r = Renderer(doc, ".")
    svg = "".join(r.render_page(doc["pages"][0]))
    assert "892bdce5  Design" not in svg          # the space run collapsed too
