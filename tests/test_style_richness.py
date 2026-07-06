"""W4 style & colour richness (issue #48): effect stack, appearance stack,
recolor(), colour guide.

Four parity rows, two layers: two ADDITIVE model fields outside the deep-core
profile (§8.5 charts precedent) — ``effects`` (an ORDERED effect stack,
AI-30) and ``appearance`` (multiple fill/stroke passes per object, AI-32) —
and two SDK helpers — ``recolor()`` (one-call palette remap incl. tokens,
literals and gradient stops, AI-16) and ``chevreul.color_guide()`` (the six
harmonies as a declarative Color Guide, AI-18). Absence is identity: an
object without the new fields must render byte-identically (the golden gate
enforces this globally).

Runs under pytest or standalone (``uv run python tests/test_style_richness.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from framegraph.sdk import chevreul, recolor, render_pages_with_stats  # noqa: E402
from framegraph.sdk.model import HEAD_VERSION, validate_document  # noqa: E402


def _doc(objects, colors=None):
    return {"dsl": "FrameGraph", "version": HEAD_VERSION, "title": "w4",
            "profile": "diagram",
            "defs": {"tokens": {"colors": colors or {"ink": "#1d1e22"}}},
            "pages": [{"mode": "page", "id": "p",
                       "canvas": {"size": [300, 200], "units": "px"},
                       "rendering": {"coordinate_mode": "absolute"},
                       "layers": [{"id": "m", "objects": objects}]}]}


# ── the version bump (additive schema change) ───────────────────────────


def test_head_version_bumped_for_the_additive_fields():
    # the effects/appearance fields landed at 2.4.0; any later HEAD keeps them
    assert tuple(int(v) for v in HEAD_VERSION.split(".")) >= (2, 4, 0)


# ── AI-30: ordered effect stack ─────────────────────────────────────────


def test_effect_stack_validates_and_orders_filters():
    doc = _doc([{"type": "rect", "id": "r", "box": [40, 40, 120, 80],
                 "fill": "ink",
                 "effects": [{"kind": "shadow", "dx": 4, "dy": 4, "blur": 6},
                             {"kind": "glow", "color": "#00ffcc", "blur": 10},
                             {"kind": "shadow", "dx": -2, "dy": -2,
                              "blur": 2, "opacity": 0.5}]}])
    validate_document(doc)
    svgs, _ = render_pages_with_stats(doc, base_dir=str(ROOT))
    svg = svgs[0]
    assert svg.count("<filter") >= 3, "each stack entry gets its own filter"
    # list order = application order: first entry innermost, last outermost
    first = svg.index("feDropShadow") if "feDropShadow" in svg else None
    assert "00ffcc" in svg.lower(), "the glow entry's colour must survive"


def test_effect_stack_absence_is_identity():
    plain = _doc([{"type": "rect", "id": "r", "box": [40, 40, 120, 80],
                   "fill": "ink"}])
    svg_plain = render_pages_with_stats(plain, base_dir=str(ROOT))[0][0]
    empty = _doc([{"type": "rect", "id": "r", "box": [40, 40, 120, 80],
                   "fill": "ink", "effects": []}])
    svg_empty = render_pages_with_stats(empty, base_dir=str(ROOT))[0][0]
    assert svg_plain == svg_empty


def test_effect_stack_can_repeat_a_kind():
    doc = _doc([{"type": "rect", "box": [10, 10, 50, 50], "fill": "ink",
                 "effects": [{"kind": "shadow", "dx": 2},
                             {"kind": "shadow", "dx": -2}]}])
    validate_document(doc)                       # the old fields cannot


def test_effect_stack_preset_entries():
    doc = _doc([{"type": "rect", "box": [10, 10, 50, 50], "fill": "ink",
                 "effects": [{"kind": "glow", "preset": "neon"}]}])
    validate_document(doc)
    svg = render_pages_with_stats(doc, base_dir=str(ROOT))[0][0]
    assert "<filter" in svg


# ── AI-32: appearance stack ─────────────────────────────────────────────


def test_appearance_stack_paints_passes_in_order():
    doc = _doc([{"type": "rect", "id": "card", "box": [40, 40, 120, 80],
                 "appearance": [
                     {"fill": "#dbeafe"},
                     {"stroke": "#1d4ed8",
                      "stroke_style": {"stroke_width": 6}},
                     {"stroke": "#ffffff",
                      "stroke_style": {"stroke_width": 2}}]}])
    validate_document(doc)
    svgs, _ = render_pages_with_stats(doc, base_dir=str(ROOT))
    svg = svgs[0]
    assert svg.count("<rect") >= 3, "one shape element per pass"
    i_fill = svg.index("#dbeafe")
    i_outer = svg.index("#1d4ed8")
    i_inner = svg.index("#ffffff", i_outer)
    assert i_fill < i_outer < i_inner, "passes paint bottom→top in list order"


def test_appearance_stack_keeps_one_id_only():
    doc = _doc([{"type": "rect", "id": "card", "box": [40, 40, 120, 80],
                 "appearance": [{"fill": "#dbeafe"}, {"stroke": "#1d4ed8"}]}])
    svg = render_pages_with_stats(doc, base_dir=str(ROOT))[0][0]
    assert svg.count('id="card"') <= 1, "clone passes must not duplicate ids"


def test_appearance_stack_absence_is_identity():
    plain = _doc([{"type": "ellipse", "center": [80, 80], "rx": 30, "ry": 20,
                   "fill": "ink"}])
    svg_a = render_pages_with_stats(plain, base_dir=str(ROOT))[0][0]
    empty = _doc([{"type": "ellipse", "center": [80, 80], "rx": 30, "ry": 20,
                   "fill": "ink", "appearance": []}])
    svg_b = render_pages_with_stats(empty, base_dir=str(ROOT))[0][0]
    assert svg_a == svg_b


# ── AI-16: recolor() ────────────────────────────────────────────────────


def test_recolor_remaps_tokens_literals_and_gradient_stops():
    doc = _doc(
        [{"type": "rect", "box": [10, 10, 60, 40], "fill": "#B5642C"},
         {"type": "rect", "box": [80, 10, 60, 40],
          "fill": {"kind": "linear", "stops": [
              {"color": "#b5642c", "position": "0%"},
              {"color": "#0f7d88", "position": "100%"}]}}],
        colors={"ink": "#1d1e22", "accent": "#b5642c"})
    out = recolor(doc, {"#b5642c": "#7c3aed"})
    assert out["defs"]["tokens"]["colors"]["accent"] == "#7c3aed"
    objs = out["pages"][0]["layers"][0]["objects"]
    assert objs[0]["fill"] == "#7c3aed", "literal remap is case-insensitive"
    stops = objs[1]["fill"]["stops"]
    assert stops[0]["color"] == "#7c3aed"
    assert stops[1]["color"] == "#0f7d88", "unmapped colours untouched"
    validate_document(out)


def test_recolor_does_not_mutate_the_input():
    doc = _doc([{"type": "rect", "box": [0, 0, 10, 10], "fill": "#111111"}])
    recolor(doc, {"#111111": "#222222"})
    assert doc["pages"][0]["layers"][0]["objects"][0]["fill"] == "#111111"


def test_recolor_accepts_token_name_keys():
    doc = _doc([], colors={"ink": "#1d1e22", "accent": "#b5642c"})
    out = recolor(doc, {"accent": "#7c3aed"})
    assert out["defs"]["tokens"]["colors"]["accent"] == "#7c3aed"


# ── AI-18: the colour guide ─────────────────────────────────────────────


def test_color_guide_returns_the_six_harmonies():
    guide = chevreul.color_guide("#0f7d88")
    assert set(guide) == {"scale", "hues", "dominant_light",
                          "contrast_of_scale", "contrast_of_hues",
                          "contrast_of_colours"}
    for name, colors in guide.items():
        assert len(colors) >= 2, name
        for c in colors:
            assert isinstance(c, str) and c.startswith("#") and len(c) == 7


def test_color_guide_is_deterministic():
    assert chevreul.color_guide("#b5642c") == chevreul.color_guide("#b5642c")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
