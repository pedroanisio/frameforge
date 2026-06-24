"""RendererContext — adapts the `Renderer` to the `RenderContext` port.

Thin delegating adapter (ADR 0001 slice 3a) that exposes the named
rendering-primitives contract (`domain.ports.RenderContext`) over the concrete
`Renderer`. Sub-renderers depend on the Protocol and receive one of these, so
they no longer reach into the Renderer's private surface directly. Pure
indirection: every member forwards to the Renderer, so output is byte-identical.
"""
from __future__ import annotations


class RendererContext:
    """Expose the `RenderContext` contract over a `Renderer` instance."""

    __slots__ = ("_r",)

    def __init__(self, renderer):
        self._r = renderer

    @property
    def painter(self):
        return self._r._painter

    @property
    def stroke_styles(self):
        return self._r.stroke_styles

    def color(self, c, depth=0):
        return self._r.color(c, depth)

    def paint(self, p, depth=0):
        return self._r.paint(p, depth)

    def text_style(self, ref):
        return self._r.text_style(ref)

    def style_dict(self, ref):
        return self._r._style_dict(ref)

    def render_text(self, *args, **kwargs):
        return self._r.render_text(*args, **kwargs)

    def measure(self, s, size, avg, st=None):
        return self._r.measure(s, size, avg, st)

    def ellipsize(self, s, w, size, avg, st=None):
        return self._r.ellipsize(s, w, size, avg, st)

    def wrap_words(self, text, w, size, avg, st=None):
        return self._r.wrap_words(text, w, size, avg, st)

    def shape_fill(self, o, style):
        return self._r._shape_fill(o, style)

    def shape_stroke(self, o, style):
        return self._r._shape_stroke(o, style)

    def shape_radius(self, o, style):
        return self._r._shape_radius(o, style)

    def arrow_attrs(self, o):
        return self._r._arrow_attrs(o)

    def obj(self, o):
        return self._r.obj(o)

    def note_skip(self):
        self._r.skipped += 1
