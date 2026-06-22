"""Arrowhead-marker rendering for line / polyline / path objects.

Exercises the additive `arrow_start` / `arrow_end` support (codebase-standards
§6/§16: new code ships with a test). v2 puts stroke geometry — including arrows —
in `stroke_style` (paint stays in `stroke`); `arrow_*` is `bool | str` where True
is the default filled triangle and a string is a marker-kind ref (grammar L631).

Why subprocess instead of importing the Renderer: the rendering package is named
`framegraph`, which in a shared pytest process would shadow the `framegraph`
*models module* that tests/test_head.py imports (one name, two targets — resolved
later by the DDD migration folding the models into the package). Rendering in a
subprocess isolates that and tests the real end-to-end SVG.

Asserts: a marker is emitted only when an arrow is requested, the kind is
honoured, the marker takes the stroke colour, and identical (kind, colour)
markers are deduped into a single `<defs>` entry.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER = os.path.join(ROOT, "tooling", "render_fixtures.py")


def _svg(obj, defs=None):
    """Render a one-object page via the renderer subprocess; return the SVG text."""
    doc = {
        "dsl": "FrameGraph", "version": "2.2.0",
        "defs": defs or {},
        "pages": [{"mode": "page", "id": "p", "canvas": {"size": [100, 100]},
                   "layers": [{"id": "l", "objects": [obj]}]}],
    }
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "doc.fg.json")
        out = os.path.join(td, "out")
        with open(src, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        subprocess.run([sys.executable, RENDER, src, "--out", out, "--quiet"],
                       check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def test_arrow_end_emits_marker():
    svg = _svg({"type": "line", "from": [0, 0], "to": [80, 0],
                "stroke": "#112233", "stroke_style": {"arrow_end": True}})
    assert 'marker-end="url(#ah1)"' in svg
    assert "<marker " in svg and 'orient="auto-start-reverse"' in svg
    assert 'fill="#112233"' in svg            # default filled triangle uses the stroke colour


def test_arrow_start_only():
    svg = _svg({"type": "line", "from": [0, 0], "to": [80, 0],
                "stroke": "#111", "stroke_style": {"arrow_start": True}})
    assert 'marker-start="url(#ah1)"' in svg
    assert "marker-end" not in svg


def test_arrow_kind_open_arrow_is_a_stroked_v():
    svg = _svg({"type": "line", "from": [0, 0], "to": [80, 0],
                "stroke": "#111", "stroke_style": {"arrow_end": "open_arrow"}})
    assert "marker-end" in svg
    assert 'fill="none"' in svg and 'stroke-width="1.5"' in svg   # open V, no fill


def test_no_arrow_emits_no_marker():
    svg = _svg({"type": "line", "from": [0, 0], "to": [80, 0], "stroke": "#111"})
    assert "marker" not in svg                 # additive: arrow-free strokes are untouched


def test_markers_dedupe_by_kind_and_colour():
    grp = {"type": "group", "children": [
        {"type": "line", "from": [0, 0], "to": [9, 0], "stroke": "#111",
         "stroke_style": {"arrow_end": True}},
        {"type": "line", "from": [0, 9], "to": [9, 9], "stroke": "#111",
         "stroke_style": {"arrow_end": True}},
    ]}
    svg = _svg(grp)
    assert svg.count("<marker ") == 1                  # one shared <defs> entry
    assert svg.count('marker-end="url(#ah1)"') == 2    # both lines reference it


def test_named_stroke_style_arrow_on_path():
    svg = _svg(
        {"type": "path", "d": "M0,0 L80,0", "stroke": "#cc0000", "stroke_style": "edge"},
        defs={"tokens": {"stroke_styles": {
            "edge": {"stroke_width": 2, "arrow_end": "filled_diamond"}}}},
    )
    assert "marker-end" in svg and "<marker " in svg
