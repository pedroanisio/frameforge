"""pdf-tex fidelity: transforms reach text; effect stack renders (issue #53).

Two operator-reported gaps from the book PDF review, both on the real
`--to pdf-tex` path (the ``latex.tikz.FigureTikz`` transpiler):

1. a group ``style.transform`` scaled shape geometry but NOT child text —
   a TikZ scope transform moves ``\\node`` anchors but leaves glyphs at
   their original size/orientation unless the scope carries
   ``transform shape``;
2. the ordered 2.4.0 ``effects`` stack was dropped silently — only the
   legacy ``shadow``/``glow`` fields got the flat approximation.

The injectable ``TikzPainter`` (ScenePainter port) shares fix 1 and, since
it has no filter primitive at all, warns per dropped effect (#44).

Runs under pytest or standalone (``uv run python tests/test_tikz_fidelity.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.rendering.application.normalize import normalize_doc  # noqa: E402
from frameforge.rendering.application.renderer import Renderer  # noqa: E402
from frameforge.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge.rendering.domain.services.text_style_resolver import (  # noqa: E402
    TextStyleResolver,
)
from frameforge.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402
from frameforge.rendering.infrastructure.painters.tikz import TikzPainter  # noqa: E402


def _figtikz():
    cr = ColorResolver({})
    return FigureTikz(cr, TextStyleResolver({}, {}, cr))


# ── the real pdf-tex path: the FigureTikz transpiler ────────────────────


def test_transpiler_scope_carries_transform_shape():
    """The #53 repro on the actual `--to pdf-tex` path: a scaled group's
    scope must carry `transform shape` so its text scales too."""
    tex = _figtikz().render(
        {"type": "group", "style": {"transform": "scale(0.5)"},
         "children": [
             {"type": "rect", "box": [20, 20, 300, 100], "fill": "#dbeafe"},
             {"type": "text", "box": [30, 40, 280, 60], "text": "SCALED?",
              "style": {"font_family": ["DejaVu Sans"], "font_size": 48,
                        "font_weight": 700, "color": "#1d1e22"}}]})
    scope = tex[tex.index("\\begin{scope}"):].split("\n", 1)[0]
    assert "transform shape" in scope
    assert "xscale=0.5" in scope and "yscale=0.5" in scope


def test_transpiler_untransformed_group_has_no_transform_shape():
    """A plain group must not gain a transform scope (byte-stability guard)."""
    tex = _figtikz().render(
        {"type": "group", "children": [
            {"type": "rect", "box": [10, 10, 40, 40], "fill": "#111111"}]})
    assert "transform shape" not in tex


def test_transpiler_renders_the_effects_stack():
    """The 2.4.0 ordered `effects` stack must render on pdf-tex (flat shadow
    / spread glow), not vanish — one shadow entry adds one effect path."""
    ft = _figtikz()
    plain = ft.render({"type": "rect", "box": [20, 20, 200, 90],
                       "fill": "#dbeafe"})
    stacked = ft.render({"type": "rect", "box": [20, 20, 200, 90],
                         "fill": "#dbeafe",
                         "effects": [{"kind": "shadow", "dx": 4, "dy": 4,
                                      "blur": 6}]})
    assert stacked.count("\\path") == plain.count("\\path") + 1, (
        "the effects-stack shadow must emit its own approximation path")


def test_transpiler_effect_stack_matches_legacy_shadow():
    """An `effects: [{kind: shadow}]` and a legacy `shadow: {...}` with the
    same params render the same approximation."""
    ft = _figtikz()
    params = {"dx": 4, "dy": 4, "blur": 6, "color": "#000000"}
    legacy = ft.render({"type": "rect", "box": [20, 20, 200, 90],
                        "fill": "#dbeafe", "shadow": params})
    stacked = ft.render({"type": "rect", "box": [20, 20, 200, 90],
                         "fill": "#dbeafe",
                         "effects": [{"kind": "shadow", **params}]})
    assert legacy.count("\\path") == stacked.count("\\path")


def test_transpiler_effect_absence_is_stable():
    ft = _figtikz()
    a = ft.render({"type": "rect", "box": [20, 20, 200, 90], "fill": "#dbeafe"})
    b = ft.render({"type": "rect", "box": [20, 20, 200, 90], "fill": "#dbeafe",
                   "effects": []})
    assert a == b


def test_transpiler_renders_the_appearance_stack():
    """The 2.4.0 `appearance` stack (multiple paint passes) must render on
    pdf-tex — one path per pass — not collapse to a bare geometry (#53
    sibling: silent-drop of W4 richness)."""
    ft = _figtikz()
    tex = ft.render({"type": "rect", "box": [0, 0, 120, 80], "radius": 10,
                     "appearance": [
                         {"fill": "#dbeafe"},
                         {"stroke": "#1d4ed8",
                          "stroke_style": {"stroke_width": 8}},
                         {"stroke": "#ffffff",
                          "stroke_style": {"stroke_width": 3}}]})
    assert tex.count("\\path") == 3, "one path per appearance pass"
    assert tex.count("draw=") == 2, "the two stroke passes both draw"


def test_transpiler_appearance_absence_is_stable():
    ft = _figtikz()
    a = ft.render({"type": "ellipse", "center": [40, 40], "rx": 30, "ry": 20,
                   "fill": "#111111"})
    b = ft.render({"type": "ellipse", "center": [40, 40], "rx": 30, "ry": 20,
                   "fill": "#111111", "appearance": []})
    assert a == b


# ── the ScenePainter port: transform shape + effect warning ─────────────


def _painter_tex(objects):
    doc = {"dsl": "FrameForge", "version": "2.4.1", "title": "t",
           "profile": "diagram",
           "pages": [{"mode": "page", "id": "p",
                      "canvas": {"size": [400, 200], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "m", "objects": objects}]}]}
    nd = normalize_doc(doc)
    r = Renderer(nd, str(ROOT),
                 painter_factory=lambda color: TikzPainter(color))
    out = []
    for page in nd.get("pages", []):
        out.extend(r.render_page(page))
    return "\n".join(out), r


def test_painter_scope_transforms_reach_text_and_are_valid_tikz():
    tex, _ = _painter_tex(
        [{"type": "group", "style": {"transform": "scale(0.5)"},
          "children": [{"type": "text", "box": [30, 40, 280, 60],
                        "text": "SCALED?",
                        "style": {"font_size": 48, "color": "#1d1e22"}}]}])
    scope = tex[tex.index("\\begin{scope}"):].split("\n", 1)[0]
    assert "transform shape" in scope
    assert "xscale=0.5" in scope         # not the invalid SVG-syntax scale(0.5)
    assert "scale(0.5)" not in scope


def test_painter_warns_per_dropped_effect():
    """The ScenePainter port has no filter primitive; dropping an effect
    silently is the #44 class — warn per kind."""
    _, r = _painter_tex(
        [{"type": "rect", "box": [20, 20, 200, 90], "fill": "#dbeafe",
          "effects": [{"kind": "shadow", "dx": 4}, {"kind": "glow"}]}])
    warnings = [w for w in r.diagnostics.get("warnings", [])
                if "effect" in str(w).lower()]
    joined = str(warnings).lower()
    assert warnings and "shadow" in joined and "glow" in joined


def test_svg_backend_composites_effects_without_warning():
    """The warning is backend-specific: SVG really renders the filters, so it
    must NOT emit the unsupported-effect warning."""
    from frameforge.sdk import render_pages_with_stats
    doc = {"dsl": "FrameForge", "version": "2.4.1", "title": "t",
           "profile": "diagram",
           "pages": [{"mode": "page", "id": "p",
                      "canvas": {"size": [400, 200], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "m", "objects": [
                          {"type": "rect", "box": [20, 20, 200, 90],
                           "fill": "#dbeafe",
                           "effects": [{"kind": "shadow", "dx": 4}]}]}]}]}
    svgs, _stats, diag = render_pages_with_stats(
        doc, base_dir=str(ROOT), diagnostics=True)
    assert "<filter" in svgs[0]
    assert not any("effect" in str(w).lower()
                   for w in diag.get("warnings", []))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
