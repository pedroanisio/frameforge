"""Page-mode text boxes with `align: justify` must justify through the flow
engine — Knuth–Plass line breaks + Liang hyphenation, flushed via SVG
`textLength` — instead of silently rendering ragged-left (the old path mapped
`justify` to the `start` anchor and had no justification primitive).

ADR-0003 follow-up: the page-mode `render_text` path is unified onto
`flow_layout`, so justification finally exists document-wide (page mode + flow
mode), not only in flow sections.
"""
from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tooling.render_fixtures import Renderer  # noqa: E402

PROSE = ("A star many times heavier than the Sun does not end its life gently. "
         "For millions of years it fuses hydrogen into helium and onward through "
         "ever heavier elements, wrapping itself in concentric shells like an onion.")


def _svg(align, *, width=300, text=PROSE):
    doc = {"pages": [{
        "mode": "page", "id": "p",
        "canvas": {"size": [width + 80, 420], "units": "px"},
        "layers": [{"id": "l", "objects": [
            {"type": "text", "box": [40, 40, width, 340], "text": text,
             "style": {"align": align, "size": 13}},
        ]}],
    }]}
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


def test_justify_emits_textlength_on_wrapped_lines():
    svg = _svg("justify")
    assert "textLength=" in svg
    assert 'lengthAdjust="spacing"' in svg


def test_left_align_is_unchanged_no_justification():
    svg = _svg("left")
    assert "textLength=" not in svg


def test_justify_hyphenates_a_narrow_column():
    pytest.importorskip("pyphen")
    svg = _svg("justify", width=150)
    line_texts = re.findall(r">([^<]*)</tspan>", svg)
    assert any(t.endswith("-") for t in line_texts), "expected a hyphen break in a tight column"


def test_last_line_is_not_justified():
    svg = _svg("justify")
    # the final wrapped tspan must not carry textLength (last line sets ragged)
    tspans = re.findall(r"<tspan\b[^>]*>[^<]*</tspan>", svg)
    assert len(tspans) >= 2
    assert "textLength=" not in tspans[-1]
