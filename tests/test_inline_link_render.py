#!/usr/bin/env python3
"""
test_inline_link_render.py — the SVG proxy renders a LinkInline span as a real
SVG hyperlink: the visible content text is wrapped in an ``<a href="...">``
anchor, so the link is clickable in the emitted SVG while the href never leaks
into the visible body text.

Renderer-only import (the `framegraph` package must win) — evict a models-module
shadow first, per test_render_cli.py.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # the models module
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

import yaml  # noqa: E402

from tooling import render_fixtures as R  # noqa: E402

DOC = {
    "dsl": "FrameGraph",
    "version": "2.2.0",
    "profile": "report",
    "title": "inline link render",
    "pages": [{
        "mode": "flow",
        "id": "p",
        "story": [{
            "type": "paragraph",
            "spans": [
                "work by ",
                {"kind": "link", "href": "https://example.org/fermi", "content": ["Enrico Fermi"]},
                " and others",
            ],
        }],
    }],
}


def test_link_inline_renders_anchor_with_visible_text(tmp_path):
    src = tmp_path / "link.fg.yaml"
    src.write_text(yaml.safe_dump(DOC), encoding="utf-8")
    assert R.main([str(src), "--out", str(tmp_path / "out"), "-q"]) == 0
    svg = (tmp_path / "out" / R.stem_of(str(src)) / "p001.svg").read_text(encoding="utf-8")

    # the link becomes a real <a href> wrapper carrying the target...
    anchor = re.search(r'<a href="https://example\.org/fermi">(.*?)</a>', svg, re.DOTALL)
    assert anchor, "LinkInline must emit an <a href=...> wrapper in the flow output"
    # ...with the link's visible content INSIDE the anchor,
    assert "Enrico Fermi" in anchor.group(1)
    # the surrounding spans staying in reading order around it,
    assert re.search(r"work by\s*</tspan><a href=", svg)
    assert re.search(r"</a><tspan>\s*and others", svg)
    # and the href appearing only as the attribute — never as visible body text.
    assert ">https://example.org/fermi<" not in svg
