#!/usr/bin/env python3
"""RenderContext (ADR 0001 slice 3a) — the sub-renderers depend on the contract.

Drives DimensionRenderer/UmlRenderer through a hand-written fake context with a
stub painter — no Renderer involved — proving the sub-renderers were decoupled
from the concrete Renderer onto the named RenderContext primitives surface.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.application.dimension_renderer import DimensionRenderer  # noqa: E402
from framegraph.rendering.application.uml_renderer import UmlRenderer  # noqa: E402


class FakePainter:
    def line(self, *a, **k):
        return "<line/>"

    def text_tag(self, *a, **k):
        return "<text/>"

    def group(self, inner, *a, **k):
        return f"<g>{inner}</g>"

    def rect(self, *a, **k):
        return "<rect/>"


class FakeContext:
    """A minimal stand-in implementing the RenderContext surface."""

    def __init__(self):
        self.painter = FakePainter()
        self.stroke_styles = {}
        self.skipped = 0

    def color(self, c, depth=0):
        return c

    def text_style(self, ref):
        return {"size": 10, "align": "center", "color": "#000"}

    def render_text(self, *a, **k):
        return "<text/>"

    def measure(self, s, size, avg, st=None):
        return len(s) * size * avg

    def ellipsize(self, s, w, size, avg, st=None):
        return s

    def shape_fill(self, o, style):
        return "#fff"

    def shape_stroke(self, o, style):
        return ' stroke="#000"'

    def shape_radius(self, o, style):
        return 0

    def arrow_attrs(self, o):
        return ""

    def obj(self, o):
        return "<g/>"

    def note_skip(self):
        self.skipped += 1


def test_dimension_renderer_runs_on_fake_context():
    ctx = FakeContext()
    svg = DimensionRenderer(ctx).draw(
        {"kind": "linear", "from": [0, 0], "to": [100, 0], "value": 100}, {}
    )
    # three extension/measure lines + the label, composed via the fake painter
    assert svg == "<g><line/><line/><line/><text/></g>"
    assert ctx.skipped == 0


def test_dimension_note_skip_on_bad_anchor():
    ctx = FakeContext()
    out = DimensionRenderer(ctx).draw({"kind": "linear", "from": "bad", "to": "bad"}, {})
    assert out == "" and ctx.skipped == 1   # context records the skip, no Renderer needed


def test_uml_renderer_runs_on_fake_context():
    ctx = FakeContext()
    svg = UmlRenderer(ctx).activation_bar(
        {"box": [10, 10, 20, 100]}, {}, "#fff"
    )
    assert svg and "<rect/>" in svg          # drew via the fake painter
    assert ctx.skipped == 0
