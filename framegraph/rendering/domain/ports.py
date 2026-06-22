"""Ports — the interfaces the rendering domain depends on (hexagonal seams).

Infrastructure adapters implement these; the domain/builder code targets the
abstraction. Today there is one painter port, implemented by the SVG adapter
(framegraph.rendering.infrastructure.painters.svg.SvgPainter). A future
MatplotlibPainter implementing the same surface is what lets the matplotlib
proxy reuse the builder instead of duplicating it.

`ScenePainter` is an *immediate-mode* display list: the builder walks the
document in z-order and calls these methods; each primitive method returns the
backend's representation of that primitive (an SVG string fragment for the SVG
adapter), and the stateful methods manage per-page backend resources (the
gradient/clip id counter and the <defs> registry). A later step may introduce a
*retained-mode* Scene (a materialised list of primitive value objects) on top of
this same seam.
"""
from __future__ import annotations

from typing import Optional, Protocol


class ScenePainter(Protocol):
    # ---- per-page backend state ----
    def new_page(self) -> None:
        """Reset per-page resources (e.g. the <defs> registry / id counter)."""

    # ---- paint registry (allocate ids in document order) ----
    def gradient(self, g: dict) -> str:
        """Register a gradient paint and return a backend paint reference."""

    def clip_rect(self, x, y, w, h) -> str:
        """Register a rectangular clip and return its id."""

    def clip_ellipse(self, cx, cy, rx, ry) -> str:
        """Register an elliptical clip and return its id."""

    def clip_wrap(self, inner: str, clip_id: str) -> str:
        """Wrap already-emitted content in the given clip."""

    def marker(self, color: str, kind: str = "filled_triangle") -> str:
        """Register an arrowhead marker for (kind, colour); return its id."""

    def filter_effect(self, kind: str, params: dict) -> str:
        """Register a shadow/glow filter for params; return its id."""

    def filter_wrap(self, inner: str, filter_id: str) -> str:
        """Wrap already-emitted content in the given filter."""

    def transform_group(self, inner: str, transform: str) -> str:
        """Wrap already-emitted content in a backend transform group."""

    # ---- primitives ----
    def rect(self, x, y, w, h, fill, stroke, radius=0, fill_opacity=None) -> str: ...
    def ellipse(self, cx, cy, rx, ry, fill, stroke, fill_opacity=None) -> str: ...
    def circle(self, cx, cy, r, fill, stroke, fill_opacity=None) -> str: ...
    def line(self, x1, y1, x2, y2, stroke) -> str: ...
    def poly(self, tag: str, points: str, fill, stroke, fill_opacity=None, fill_rule=None) -> str: ...
    def path(self, d: str, fill, stroke, fill_opacity=None, fill_rule=None) -> str: ...
    def image(self, x, y, w, h, href: str, preserve_aspect_ratio="xMidYMid meet") -> str: ...
    def text_tag(self, x, y, w, h, content, st, vcenter: Optional[bool] = None) -> str: ...
    def text_block(self, base_y, anchor, style, lines, tx, line_dy) -> str: ...
    def text_runs(self, base_y, anchor, tx, base_style, runs) -> str: ...

    # ---- grouping / document ----
    def group(self, inner: str, translate=None) -> str: ...
    def opacity_group(self, inner: str, opacity) -> str: ...
    def document(self, w, h, body: str) -> str:
        """Assemble a full page document from accumulated <defs> + body."""
