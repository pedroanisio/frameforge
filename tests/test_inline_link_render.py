#!/usr/bin/env python3
"""
test_inline_link_render.py — the SVG proxy flattens a LinkInline span to its
visible content text (render_fixtures.text_of), so an inline hyperlink renders as
readable text rather than vanishing or leaking its href.

Renderer-only import (the `framegraph` package must win) — evict a models-module
shadow first, per test_render_cli.py.
"""
import os
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


def test_link_inline_renders_visible_text_not_href(tmp_path):
    src = tmp_path / "link.fg.yaml"
    src.write_text(yaml.safe_dump(DOC), encoding="utf-8")
    assert R.main([str(src), "--out", str(tmp_path / "out"), "-q"]) == 0
    svg = (tmp_path / "out" / R.stem_of(str(src)) / "p001.svg").read_text(encoding="utf-8")
    assert "work by Enrico Fermi and others" in svg   # content flattened in order
    assert "https://example.org/fermi" not in svg     # the href is not leaked as body text
