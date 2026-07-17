"""frameforge.rendering.infrastructure.latex — the LaTeX/TikZ render engine.

A peer to the SVG proxy (`tooling/render_fixtures.py` + `painters.svg.SvgPainter`)
that produces *LaTeX-quality* output: the flow story becomes native LaTeX (TeX does
pagination, justification, hyphenation, microtype, and real math), and each figure's
FrameForge object graph becomes vector TikZ.

Two pieces:
  * `tikz.FigureTikz` — walks a (symbol-expanded) figure object graph and emits TikZ,
    reusing the pure domain resolvers (`ColorResolver`, `TextStyleResolver`). It is NOT
    a `ScenePainter`: the figures only use rect/ellipse/text/line/poly/group, and a
    direct walker avoids consuming the SVG-flavoured intermediates the proxy painter
    trades in (stroke-attribute strings, opaque font-style handoff).
  * `document.transpile` — walks `pages[].story`, builds the preamble from the design
    tokens + master canvas, and assembles a compilable `.tex` string.

The design tokens are honoured: token font sizes / weights / the `ink` colour drive
the LaTeX font commands and `\\definecolor`s; the body is a sans face via fontspec.
"""
from __future__ import annotations

from .document import transpile

__all__ = ["transpile"]
