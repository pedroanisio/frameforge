"""Preserved space runs must survive into SVG-1.1 consumers, not just browsers.

`white_space: pre` / `pre-wrap` / `break-spaces` keep authored space runs, and the
SVG painter emits them verbatim plus a CSS `white-space` declaration. CSS
`white-space` is an SVG2/CSS-Text feature: Chromium honours it, but SVG 1.1
renderers (cairosvg — the `--to pdf` backend) do not, and XML whitespace
processing then collapses every run to a single space.

Measured on a real 17-page spec: a monospace pattern-inventory table rendered
with perfect columns through `--to png` (Chromium) and with every column
collapsed through `--to pdf` (cairosvg), from the identical SVG.

`xml:space="preserve"` is the SVG 1.1 mechanism every consumer implements, so
the painter emits it alongside the CSS whenever the mode preserves spaces.
"""
from __future__ import annotations

import pytest

from frameforge.rendering.application.renderer import Renderer


ROWS = "PATTERN        PURPOSE                GROUNDED IN\nTile           Scan state             DS:492"


def _svg(style):
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [500, 200], "units": "px"},
        "layers": [{"id": "l", "objects": [
            {"type": "text", "id": "inv", "box": [10, 10, 480, 80],
             "text": ROWS, "style": {"font_family": ["monospace"],
                                     "font_size": 10, **style}}]}],
    }]}
    r = Renderer(doc, ".")
    return "".join(r.render_page(doc["pages"][0]))


@pytest.mark.parametrize("mode", ["pre", "pre-wrap", "break-spaces"])
def test_preserving_modes_emit_xml_space_preserve(mode):
    svg = _svg({"white_space": mode})
    assert 'xml:space="preserve"' in svg, f"{mode} lost its SVG-1.1 whitespace guarantee"
    # the authored run itself must still be there verbatim
    assert "PATTERN        PURPOSE" in svg


def test_collapsing_modes_do_not_claim_to_preserve():
    for mode in ({}, {"white_space": "normal"}, {"white_space": "nowrap"}):
        assert 'xml:space="preserve"' not in _svg(mode)


def test_preserve_is_scoped_to_the_text_element():
    """The attribute belongs on the <text> that owns the run, not the root <svg>
    — a document-wide preserve would change every other text element's layout."""
    svg = _svg({"white_space": "pre"})
    root = svg[:svg.index(">") + 1]
    assert "xml:space" not in root
    assert svg.count('xml:space="preserve"') == 1
