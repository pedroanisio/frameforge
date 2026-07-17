#!/usr/bin/env python3
"""End-to-end wire-up: the SAME Renderer/builder drives the TikZ backend (ADR 0001
3b-5c). The painter is injectable (`painter_factory`), so swapping SvgPainter ->
TikzPainter makes the builder emit a TikZ picture from the neutral value objects —
no SVG. This proves the seam is genuinely backend-neutral; the LaTeX-document
scaffold + FigureTikz deletion are the remaining LaTeX-toolchain-gated step."""
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.application.renderer import Renderer  # noqa: E402
from frameforge.rendering.infrastructure.painters.tikz import TikzPainter  # noqa: E402

# a real page-mode oracle fixture exercising fills, gradients, strokes, and text
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "b1", "chroma-styling-showcase.fg.json")


def _doc():
    with open(FIXTURE) as fh:
        return json.load(fh)


def test_renderer_drives_tikz_backend_end_to_end():
    doc = _doc()
    r = Renderer(doc, ".", painter_factory=lambda color: TikzPainter(color))
    out = "".join(r.render_page(doc["pages"][0]))
    assert r.skipped == 0, "no object should be skipped when driving TikZ"
    # a TikZ picture, not SVG
    assert "\\begin{tikzpicture}[x=1pt,y=-1pt]" in out and "\\end{tikzpicture}" in out
    assert "<svg" not in out and "<rect" not in out and "<text" not in out and "<path" not in out
    # the neutral value objects became TikZ: shapes, gradient shades, and text nodes
    assert "\\path[" in out and "\\shade[" in out and "\\node[" in out


def test_svg_backend_remains_the_default():
    doc = _doc()
    out = "".join(Renderer(doc, ".").render_page(doc["pages"][0]))
    assert out.startswith("<svg") and "<rect" in out          # default unchanged
