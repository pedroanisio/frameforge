#!/usr/bin/env python3
"""
test_flow_figure_render.py — regression for flow-mode figure rendering in the
SVG proxy (tooling/render_fixtures.py).

Bug: `_render_flow` only drew heading/paragraph/list and stubbed everything else
(figure/table/math/...) as dashed `[type]` placeholders — so the *drawings* and
structured flow content of a `mode: flow` document (e.g.
fixtures/standard-model.fg.yaml) never rendered. The fix draws figures, tables,
math/code, and nested blocks as real SVG/text content.

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

STANDARD_MODEL = os.path.join(R.FIXTURES, "standard-model.fg.yaml")

# A minimal flow doc whose single figure draws a rect + a symbol `use` (which the
# normaliser must expand to an ellipse) and carries a caption.
SYNTH = {
    "dsl": "FrameGraph",
    "version": "2.2.0",
    "profile": "report",
    "title": "flow figure regression",
    "defs": {
        "symbols": {
            "dot": {
                "box": [0, 0, 20, 20],
                "objects": [
                    {"type": "ellipse", "center": [10, 10], "rx": 6, "ry": 6, "fill": "#e8302a"}
                ],
            }
        }
    },
    "pages": [
        {
            "mode": "flow",
            "id": "p",
            "story": [
                {"type": "heading", "level": 1, "text": "Heading"},
                {
                    "type": "figure",
                    "id": "fig",
                    "size": [200, 80],
                    "object": {
                        "type": "group",
                        "box": [0, 0, 200, 80],
                        "children": [
                            {"type": "rect", "box": [0, 0, 200, 80], "fill": "#3498db"},
                            {"type": "use", "symbol": "dot", "box": [40, 30, 20, 20]},
                        ],
                    },
                    "caption": "regression caption",
                },
            ],
        }
    ],
}


def _render_to_svg(tmp_path, doc, name):
    src = tmp_path / name
    src.write_text(yaml.safe_dump(doc), encoding="utf-8")
    rc = R.main([str(src), "--out", str(tmp_path / "out"), "-q"])
    assert rc == 0
    return (tmp_path / "out" / R.stem_of(str(src)) / "p001.svg").read_text(encoding="utf-8")


def test_flow_figure_draws_geometry_not_placeholder(tmp_path):
    svg = _render_to_svg(tmp_path, SYNTH, "synth.fg.yaml")
    # the figure rect and the expanded symbol ellipse are drawn ...
    assert 'fill="#3498db"' in svg
    assert "<ellipse" in svg and 'fill="#e8302a"' in svg
    # ... the caption is emitted ...
    assert "regression caption" in svg
    # ... and NO figure stub remains (dashed placeholder box + "[figure]" label).
    assert "[figure]" not in svg
    assert 'stroke-dasharray="3 3"' not in svg


def test_standard_model_figures_all_render(tmp_path):
    """The checked-in fixture that surfaced the bug: every figure must draw, so
    no flow placeholder may survive and real geometry/content appears."""
    rc = R.main([STANDARD_MODEL, "--out", str(tmp_path), "-q"])
    assert rc == 0
    pages_dir = tmp_path / R.stem_of(STANDARD_MODEL)
    combined = "".join(
        (pages_dir / f).read_text(encoding="utf-8")
        for f in sorted(os.listdir(pages_dir))
        if f.endswith(".svg")
    )
    for placeholder in ("[figure]", "[table]", "[math]", "[block]"):
        assert placeholder not in combined
    assert combined.count("<ellipse") > 50     # the SM-grid quark/colour dots drew
    assert "standard model particles" in combined
    assert "S = [ s(s + 1) ]¹/² ℏ" in combined
    for raw_tex in ("\\left", "\\right", "\\tfrac", "\\frac", "\\sqrt", "\\hbar"):
        assert raw_tex not in combined
    assert "Masses as reported by the Particle Data Group" in combined
