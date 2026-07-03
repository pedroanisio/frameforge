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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Optional, Protocol, Union

if TYPE_CHECKING:
    from framegraph.rendering.domain.services.stroke_resolver import Markers, Stroke


class RenderContext(Protocol):
    """The minimal rendering-primitives contract a drawing sub-renderer needs.

    Sub-renderers (UML, dimensions) draw within the builder's context — they need
    the painter plus the builder's shape/text resolution primitives. Depending on
    this Protocol instead of the concrete `Renderer` inverts that dependency
    (codebase-standards.md §13, ADR 0001 slice 3a): the contract is named,
    mockable, and is exactly the primitive surface a future backend-neutral
    builder must supply. `painter` is a `ScenePainter`; `note_skip()` records that
    one object was skipped (the builder's resilience counter).
    """
    @property
    def painter(self) -> "ScenePainter": ...
    @property
    def stroke_styles(self) -> dict: ...
    def color(self, c, depth: int = 0) -> Any: ...
    def paint(self, p, depth: int = 0) -> Any: ...
    def text_style(self, ref) -> Any: ...
    def style_dict(self, ref) -> dict: ...
    def render_text(self, *args, **kwargs) -> Any: ...
    def measure(self, s, size, avg, st=None) -> float: ...
    def ellipsize(self, s, w, size, avg, st=None) -> str: ...
    def wrap_words(self, text, w, size, avg, st=None) -> list: ...
    def shape_fill(self, o, style) -> Any: ...
    def shape_stroke(self, o, style) -> "Stroke | None": ...
    def shape_radius(self, o, style) -> Any: ...
    def arrow_markers(self, o) -> "Markers | None": ...
    def obj(self, o) -> str: ...
    def note_skip(self) -> None: ...


class ScenePainter(Protocol):
    # ---- per-page backend state ----
    def new_page(self) -> None:
        """Reset per-page resources (e.g. the <defs> registry / id counter)."""

    # ---- paint / clip / filter registry (allocate ids in document order) ----
    # These return an OPAQUE BACKEND HANDLE (an id/reference, not a neutral value):
    # the `*_wrap`/paint methods take a handle a prior call returned and the backend
    # is free to choose its representation. They are inherently backend-specific —
    # a non-SVG adapter reimplements them rather than formatting a shared value.
    def gradient(self, g: dict) -> str:
        """Register a gradient paint and return a backend paint reference."""

    def image_pattern(self, href: str, x, y, w, h,
                      preserve_aspect_ratio: str = "xMidYMid slice") -> str:
        """Register an image fill pattern and return a backend paint reference."""

    def clip_rect(self, x, y, w, h) -> str:
        """Register a rectangular clip and return its handle."""

    def clip_ellipse(self, cx, cy, rx, ry) -> str:
        """Register an elliptical clip and return its handle."""

    def clip_polygon(self, points: str) -> str:
        """Register a polygonal clip and return its handle."""

    def clip_path_d(self, d: str) -> str:
        """Register a path-data clip and return its handle."""

    def clip_wrap(self, inner: str, clip_id: str) -> str:
        """Wrap already-emitted content in the given clip handle."""

    def marker(self, color: str, kind: str = "filled_triangle") -> str:
        """Register an arrowhead marker for (kind, colour); return its handle."""

    def filter_effect(self, kind: str, params: dict) -> str:
        """Register a shadow/glow filter for params; return its handle."""

    def filter_wrap(self, inner: str, filter_id: str) -> str:
        """Wrap already-emitted content in the given filter handle."""

    def transform_group(self, inner: str, transform) -> str:
        """Wrap already-emitted content in a backend transform group. `transform` is
        a neutral op list (StyleValues.transform_ops) the backend formats."""

    def embedded_svg(self, x, y, w, h, *, viewbox, color, title, body) -> str:
        """Embed a foreign SVG fragment (e.g. a MathJax render). Backend-specific:
        a non-SVG backend implements this differently or falls back."""

    # ---- primitives ----
    # `stroke` is a backend-neutral Stroke value object (or None for no stroke) and
    # `markers` a neutral Markers value object (or None) for arrowheads on open
    # shapes; the backend formats both. `extra` is a residual escape hatch for
    # backend-specific trailing attributes (the SVG backend uses it only for an
    # inert fill="none" on a few lines); prefer the neutral params.
    def rect(self, x, y, w, h, fill, stroke, radius=0, fill_opacity=None) -> str: ...
    def ellipse(self, cx, cy, rx, ry, fill, stroke, fill_opacity=None) -> str: ...
    def circle(self, cx, cy, r, fill, stroke, fill_opacity=None) -> str: ...
    def line(self, x1, y1, x2, y2, stroke, markers=None, extra="") -> str: ...
    def poly(self, tag: str, points: str, fill, stroke, fill_opacity=None, fill_rule=None, markers=None, extra="") -> str: ...
    def path(self, d: str, fill, stroke, fill_opacity=None, fill_rule=None, markers=None, extra="") -> str: ...
    def image(self, x, y, w, h, href: str, preserve_aspect_ratio="xMidYMid meet") -> str: ...
    def text_tag(self, x, y, w, h, content, st, vcenter: Optional[bool] = None) -> str: ...
    # text_block/text_runs take the neutral style dict(s) + fitted size; the
    # backend formats the font (runs is a list of (text, run_style_dict) pairs).
    # `baseline` (set for a centred single line) requests vertical centring on the
    # box centre via the backend's own metrics rather than the baseline grid.
    def text_block(self, base_y, anchor, st, size, lines, tx, line_dy, *, baseline=None) -> str: ...
    def text_runs(self, base_y, anchor, tx, base_st, size, runs, *, baseline=None) -> str: ...

    # ---- grouping / document ----
    def group(self, inner: str, translate=None) -> str: ...
    def opacity_group(self, inner: str, opacity) -> str: ...
    def document(self, w, h, body: str, lang=None, title=None, desc=None) -> str:
        """Assemble a full page document from accumulated defs + body. `lang`/`title`/
        `desc` are root accessibility attributes a backend may use or ignore."""


# --------------------------------------------------------------------------- #
# Document-level output port (the COARSE seam) — complements ScenePainter      #
# --------------------------------------------------------------------------- #
#
# `ScenePainter` above is the *fine-grained, per-primitive* seam the SVG builder
# drives in z-order (its primitives are SVG-shaped, returning string fragments).
# `DocumentRenderer` is the *coarse* seam at the whole-document boundary: one
# FrameGraph document in, one rendered artifact out. It is the right port for a
# backend whose output is a document-level transform rather than a display list
# of geometry — HTML (semantic figure/section/group tree, CSS hoisting, aria) and
# typeset PDF (TeX owns pagination) both are.
#
# A *driving* adapter (`framegraph.cli`) depends on this Protocol and reaches a
# renderer through it — never by shelling out to one of our own scripts. Each
# output backend is a *driven* adapter (`…infrastructure.backends.*`) implementing
# it in-process. An external *binary* a backend needs (a TeX engine) is that
# adapter's own concern; invoking it is a driven dependency, not a call back into
# `tooling/`.


@dataclass(frozen=True)
class RenderedArtifact:
    """The in-memory result of a `DocumentRenderer`.

    `pages` carries one payload per output file — text (`str`) for SVG/HTML,
    binary (`bytes`) for a compiled PDF — so the driving adapter owns *all* disk
    I/O and every backend returns through one value object. `media_type` is the
    RFC 2046 type (`text/html`, `application/pdf`); `extension` the file suffix
    without a leading dot. When `one_file_per_page` is True the driver writes
    `stem-<n>.<ext>` per page; when False it writes a single `stem.<ext>` from
    `pages[0]` (an HTML doc paginates internally; a typeset PDF is one file).
    """

    pages: list[Union[str, bytes]]
    media_type: str
    extension: str
    one_file_per_page: bool = False


class DocumentRenderer(Protocol):
    """Output port: a whole FrameGraph document → a `RenderedArtifact`.

    Implemented by infrastructure backends (`…infrastructure.backends.*`).
    `target` is the CLI `--to` name; `kind`/`blurb` describe it for `--list`;
    `available()` returns None when the backend can run right now, else a short
    human reason (a missing optional dependency or external binary). `render`
    takes the document dict, an optional `base_dir` for resolving document-
    relative assets, and an optional `options` map for per-invocation knobs a
    backend may read (e.g. the TeX engine); a backend ignores options it does
    not use.
    """

    target: str
    kind: str
    blurb: str

    def available(self) -> Optional[str]:
        """None if this backend can render now; else a short reason it cannot."""
        ...

    def render(self, document: Mapping[str, Any], *,
               base_dir: Optional[str] = None,
               options: Optional[Mapping[str, Any]] = None) -> RenderedArtifact:
        """Render `document` (a FrameGraph document dict) to a `RenderedArtifact`."""
        ...
