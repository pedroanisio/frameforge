#!/usr/bin/env python3
"""
test_flow_figure_render.py — regression for flow-mode figure rendering in the
SVG proxy (tooling/render_fixtures.py).

Bug: `_render_flow` only drew heading/paragraph/list and stubbed everything else
(figure/table/math/...) as dashed `[type]` placeholders — so the *drawings* and
structured flow content of a `mode: flow` document (e.g.
fixtures/standard-model.fg.yaml) never rendered. The fix draws figures, tables,
math/code, and nested blocks as real SVG/text content.

Renderer-only import (the `frameforge` package must win) — evict a models-module
shadow first, per test_render_cli.py.
"""
import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # the models module
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import yaml  # noqa: E402

from tooling import render_fixtures as R  # noqa: E402

STANDARD_MODEL = os.path.join(R.FIXTURES, "standard-model.fg.yaml")
if not os.path.exists(STANDARD_MODEL):
    STANDARD_MODEL = os.path.join(ROOT, "static", "examples", "fixtures", "standard-model.fg.yaml")

# A minimal flow doc whose single figure draws a rect + a symbol `use` (which the
# normaliser must expand to an ellipse) and carries a caption.
SYNTH = {
    "dsl": "FrameForge",
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

MATHML_DOC = {
    "dsl": "FrameForge",
    "version": "2.2.0",
    "profile": "report",
    "title": "mathml render",
    "pages": [
        {
            "mode": "flow",
            "id": "p",
            "story": [
                {"type": "heading", "level": 1, "text": "MathML"},
                {
                    "type": "math",
                    "mathml": "<math><mi>x</mi><mo>=</mo><msqrt><mn>2</mn></msqrt></math>",
                    "alt": "x equals square root of two",
                },
            ],
        }
    ],
}

INLINE_MATH_DOC = {
    "dsl": "FrameForge",
    "version": "2.2.0",
    "profile": "report",
    "title": "inline math render",
    "pages": [
        {
            "mode": "flow",
            "id": "p",
            "story": [
                {
                    "type": "paragraph",
                    "spans": [
                        "Exactness means ",
                        {"kind": "math", "tex": "E_n(f) = 0"},
                        " for every ",
                        {"kind": "math", "tex": "f \\in \\mathbb{P}_{2n-1}"},
                        ".",
                    ],
                }
            ],
        }
    ],
}


def _render_to_svg(tmp_path, doc, name):
    # The math->SVG cache is now per-MathSvgRenderer instance (one per render),
    # so no cross-render class state needs resetting here.
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


def test_flow_mathml_renders_as_mathjax_svg_not_raw_xml(tmp_path):
    svg = _render_to_svg(tmp_path, MATHML_DOC, "mathml.fg.yaml")
    assert 'data-frameforge-math="true"' in svg
    assert 'data-mml-node="math"' in svg
    assert "<path" in svg
    # Math ink derives from the document (GH #64): no body style here, so the
    # sanctioned base colour applies — never the old engine literal #111.
    assert 'fill="#1c1c1c"' in svg
    assert 'stroke="#1c1c1c"' in svg
    assert 'fill="#111"' not in svg
    assert "currentColor" not in svg
    assert "<math><mi>x</mi>" not in svg
    assert "&lt;math&gt;" not in svg
    assert "x equals square root of two" in svg


def test_math_svg_conversion_failure_does_not_disable_later_math(monkeypatch):
    # The math->SVG path is now the MathSvgRenderer infrastructure adapter.
    from frameforge.rendering.domain.services.math_text import math_text
    from frameforge.rendering.infrastructure.math_svg import MathSvgRenderer

    m = MathSvgRenderer(math_text)
    calls = []

    def fake_run(_cmd, input=None, **_kwargs):
        calls.append(input)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, _cmd, stderr="bad expression")

        class Proc:
            stdout = '[{"body":"<g data-mml-node=\\"math\\"></g>","viewBox":"0 0 10 10","width":10,"height":10}]'

        return Proc()

    # Patch the shared stdlib `subprocess` module object the adapter calls through.
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert m.render("bad") is None             # one conversion failure...
    rendered = m.render(r"E = mc^2")           # ...does not disable later math

    assert rendered["body"] == '<g data-mml-node="math"></g>'
    assert m._failed is False
    assert len(calls) == 2


def test_flow_inline_math_spans_do_not_leak_raw_tex(tmp_path):
    svg = _render_to_svg(tmp_path, INLINE_MATH_DOC, "inline-math.fg.yaml")
    assert "Eₙ(f) = 0" in svg
    assert "f ∈ ℙ₂ₙ₋₁" in svg
    for raw_tex in ("\\in", "\\mathbb", "_{2n-1}", "E_n"):
        assert raw_tex not in svg


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
    assert combined.count('data-frameforge-math="true"') == 10
    assert 'data-frameforge-math="true"' in combined
    assert 'data-mml-node="math"' in combined
    assert "<path" in combined
    assert "S = [ s(s + 1) ]¹/² ℏ" not in combined
    for raw_tex in ("\\left", "\\right", "\\tfrac", "\\frac", "\\sqrt", "\\hbar"):
        assert raw_tex not in combined
    assert "Masses as reported by the Particle Data Group" in combined
