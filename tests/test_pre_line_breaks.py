#!/usr/bin/env python3
"""test_pre_line_breaks.py — authored newlines under ``white_space: pre-*``.

The model documents ``Style.white_space`` with the CSS value set
(``normal | nowrap | pre | pre-wrap | pre-line | break-spaces``), but the
page-mode text layout collapsed authored ``\\n`` unconditionally: every
pre-* mode rendered "A\\nB" as the single line "A B".  The contract these
tests pin:

  * ``pre-line`` / ``pre-wrap`` / ``break-spaces`` / ``pre`` — an authored
    ``\\n`` is a hard line break; wrapping still applies inside each segment.
  * default (``white_space`` unset / ``normal``) — unchanged: newlines are
    ordinary whitespace (regression guard for existing fixtures).
  * ``shrink_to_fit`` re-layout preserves the authored breaks.

Runs under pytest or standalone
(``uv run python tests/test_pre_line_breaks.py``).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling"), os.path.join(ROOT, "src"), ROOT]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from render_fixtures import Renderer                    # noqa: E402


def _svg(text_obj):
    doc = {"dsl": "FrameForge", "version": "2.3.0", "title": "t",
           "pages": [{"mode": "page", "id": "p1",
                      "canvas": {"size": [400, 300], "units": "px"},
                      "layers": [{"id": "l1", "objects": [text_obj]}]}]}
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


def test_pre_line_breaks_on_authored_newlines():
    svg = _svg({"id": "t", "type": "text", "box": [20, 20, 340, 100],
                "text": "Alpha Beta\nGamma Delta",
                "style": {"font_size": 14, "white_space": "pre-line"}})
    assert "Alpha Beta" in svg and "Gamma Delta" in svg
    assert "Alpha Beta Gamma Delta" not in svg          # the collapse bug


def test_pre_wrap_preserves_newline_and_still_wraps():
    long_seg = "one two three four five six seven eight nine ten"
    svg = _svg({"id": "t", "type": "text", "box": [20, 20, 120, 200],
                "text": "Head\n" + long_seg,
                "style": {"font_size": 14, "white_space": "pre-wrap"}})
    # the authored break holds…
    assert ">Head<" in svg or ">Head</" in svg or "Head" in svg
    assert "Head one" not in svg
    # …and the long segment still wraps inside the 120 px column
    assert long_seg not in svg


def test_default_normal_still_collapses_newlines():
    svg = _svg({"id": "t", "type": "text", "box": [20, 20, 340, 100],
                "text": "Alpha Beta\nGamma Delta",
                "style": {"font_size": 14}})
    assert "Alpha Beta Gamma Delta" in svg              # unchanged legacy layout


def test_shrink_to_fit_keeps_authored_breaks():
    svg = _svg({"id": "t", "type": "text", "box": [20, 20, 200, 60],
                "text": "First segment here\nSecond segment here",
                "style": {"font_size": 22, "white_space": "pre-line",
                          "overflow": "shrink_to_fit"}})
    assert "First segment here Second segment here" not in svg


if __name__ == "__main__":
    import pytest as _pytest
    raise SystemExit(_pytest.main([__file__, "-q"]))
