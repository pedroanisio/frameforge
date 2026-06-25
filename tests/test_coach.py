"""Tests for the Vector Construction Coach POC (framegraph.coach).

The coach is a disciplined-process layer over the SDK: it does not draw for the
model, it provides the deterministic scaffold (style-as-grammar, layer-order
validation, the silhouette readability gate) the review identified as the
load-bearing, reusable pieces. These tests pin that deterministic behaviour;
the creative/aesthetic judgement stays with the model and is out of scope here.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder  # noqa: E402
from framegraph.sdk.conform import render_page_svgs
from framegraph.coach import (
    STYLES,
    DrawingIntent,
    LayerPlan,
    StyleProfile,
    create_plan,
    parse_intent,
    resolve_style,
    stage_rubric,
    to_silhouette,
)


# --- intent ---------------------------------------------------------------- #
def test_parse_intent_fills_defaults():
    di = parse_intent("a cybernetic crab, low-angle, clean line art")
    assert isinstance(di, DrawingIntent)
    assert di.subject
    assert di.width > 0 and di.height > 0
    assert di.detail_level  # a default was supplied, not left blank


def test_parse_intent_detects_known_style_and_perspective():
    di = parse_intent("draw a frog in blueprint style, isometric view")
    assert di.style == "blueprint"
    assert di.perspective == "isometric"


# --- style as grammar ------------------------------------------------------ #
def test_style_registry_is_executable_with_weight_hierarchy():
    for name, s in STYLES.items():
        assert isinstance(s, StyleProfile), name
        assert s.outer >= s.inner >= s.detail >= 0, name   # weights descend (0 == fill-only)
        assert s.palette                                    # a real palette, not empty


def test_resolve_single_style_returns_profile():
    assert resolve_style("flat_icon") is STYLES["flat_icon"]


def test_resolve_hybrid_merges_keeping_first_line_discipline():
    h = resolve_style("comic_ink", "blueprint")
    assert isinstance(h, StyleProfile)
    assert h.outer == STYLES["comic_ink"].outer          # line discipline from first
    # palette is the union of both, de-duplicated
    union = set(STYLES["comic_ink"].palette) | set(STYLES["blueprint"].palette)
    assert set(h.palette) == union


def test_resolve_unknown_style_falls_back_not_raises():
    s = resolve_style("ukiyo-e-cyberpunk-unknown")
    assert isinstance(s, StyleProfile)


# --- layer-order validation (silhouette before detail) --------------------- #
def test_canonical_plan_validates():
    plan = create_plan()
    assert isinstance(plan, LayerPlan)
    assert plan.layers
    from framegraph.coach import validate_order
    assert validate_order(plan.layers) == []


def test_detail_before_silhouette_is_flagged():
    from framegraph.coach import validate_order
    bad = ["00_canvas", "05_details", "03_silhouette", "04_forms"]
    issues = validate_order(bad)
    assert issues
    assert any("detail" in i.lower() and "silhouette" in i.lower() for i in issues)


def test_shadows_before_colors_is_flagged():
    from framegraph.coach import validate_order
    bad = ["00_canvas", "03_silhouette", "08_shadows", "07_flat_colors"]
    issues = validate_order(bad)
    assert any("shadow" in i.lower() for i in issues)


# --- the silhouette gate (the centerpiece) --------------------------------- #
def _subject_doc() -> DocumentBuilder:
    b = DocumentBuilder(title="t", profile="diagram")
    p = b.page("p", canvas={"size": [240, 240]}, coordinate_mode="absolute")
    L = p.layer("main")
    L.rect([0, 0, 240, 240], fill="#FFFFFF", decorative=True)            # background
    L.ellipse([120, 120], 70, 50, fill="#7C5CFC")                        # body (purple)
    L.rect([95, 60, 50, 50], fill="#22D3EE", stroke="#EC4899")           # head (cyan/pink)
    return b


def test_silhouette_flattens_to_black_on_white_and_still_renders():
    sil = to_silhouette(_subject_doc())
    svgs = render_page_svgs(sil)
    assert svgs, "silhouette doc must still render through the SDK proxy"
    svg = svgs[0].lower()
    # the subject's chromatic colours are gone
    assert "7c5cfc" not in svg
    assert "22d3ee" not in svg
    assert "ec4899" not in svg
    # and it is rendered as black ink
    assert "#000000" in svg or "black" in svg


def test_silhouette_keeps_a_white_ground():
    sil = to_silhouette(_subject_doc())
    svg = render_page_svgs(sil)[0].lower()
    assert "#ffffff" in svg or "white" in svg


# --- critique rubric (deterministic checklist; scoring is the VLM's) ------- #
def test_stage_rubric_returns_checklist():
    r = stage_rubric("silhouette")
    assert isinstance(r, list) and r
    assert all(isinstance(x, str) for x in r)


# --- ingest re-skin transforms (pure; no OpenCV) --------------------------- #
def test_recolor_to_style_preserves_geometry_and_maps_palette():
    from framegraph.coach import recolor_to_style
    objs = [{"type": "polygon", "points": [[0, 0], [10, 0], [10, 10]], "fill": "#777777"},
            {"type": "polygon", "points": [[1, 1], [5, 1], [5, 5]], "fill": "#222222"},
            {"type": "polyline", "points": [[0, 0], [9, 9]], "stroke": "#000000"}]
    out = recolor_to_style(objs, STYLES["comic_ink"])
    assert [o.get("points") for o in out] == [o.get("points") for o in objs]   # geometry intact
    fills = [o["fill"] for o in out if "fill" in o]
    assert all(f in STYLES["comic_ink"].palette for f in fills)                 # mapped to palette
    assert out[2]["stroke"] == STYLES["comic_ink"].palette[0]                   # stroke re-inked


def test_gradientize_lifts_flat_fills_to_gradients():
    from framegraph.coach import gradientize
    out = gradientize([{"type": "polygon", "points": [[0, 0]], "fill": "#445566"}])
    grad = out[0]["fill"]
    assert isinstance(grad, dict) and grad.get("stops") and grad["kind"] == "linear"


# --- image-agnostic line/contour cleanup ----------------------------------- #
def test_simplify_reduces_nodes_within_tolerance():
    from framegraph.coach import simplify_strokes, node_count
    # a near-straight noisy line: many points that RDP should collapse
    pts = [[i, (i % 2) * 0.4] for i in range(40)]            # tiny ±0.4 jitter on y=~0
    objs = [{"type": "polyline", "points": pts}]
    out = simplify_strokes(objs, eps=1.5)
    assert node_count(out) < node_count(objs)                # fewer vertices
    assert node_count(out) <= 4                              # collapses to near-straight
    assert out[0]["points"][0] == [0.0, 0.0] and out[0]["points"][-1] == [39.0, 0.4]  # endpoints kept


def test_denoise_drops_speckle_keeps_real_strokes():
    from framegraph.coach import denoise_strokes
    speck = {"type": "polyline", "points": [[0, 0], [1, 1], [2, 0]]}       # ~2px
    real = {"type": "polyline", "points": [[0, 0], [50, 10], [100, 0]]}    # ~100px
    out = denoise_strokes([speck, real], min_span=6.0)
    assert len(out) == 1 and out[0]["points"][-1] == [100, 0]


def test_clean_preserves_object_type_and_shape_endpoints():
    from framegraph.coach import clean
    poly = {"type": "polygon", "points": [[0, 0], [10, 0.3], [20, 0], [20, 20], [0, 20]]}
    out = clean([poly], eps=1.0)
    assert out[0]["type"] == "polygon"
    assert out[0]["points"][0] == [0.0, 0.0]                 # geometry anchored


# --- MCP integration: the silhouette flag on the render pipeline ----------- #
def test_mcp_pipeline_silhouette_flag(tmp_path):
    """The `silhouette=True` flag flattens the doc through the real render path
    and attaches the rubric — the gate any agent gets for free via the tools."""
    from pathlib import Path

    from framegraph.sdk import serialize
    from framegraph.mcp.pipeline import _validate_and_render_yaml

    yaml_text = serialize(_subject_doc().build(), format="yaml")
    res = _validate_and_render_yaml(
        yaml_text, session_id="t", session_dir=tmp_path, base_dir=tmp_path,
        max_pages=1, raster_png=False, silhouette=True,
    )
    assert res["ok"], res.get("error")
    assert res["silhouette"]["applied"] and res["silhouette"]["rubric"]
    svg = Path(res["renders"][0]["path"]).read_text(encoding="utf-8").lower()
    assert "7c5cfc" not in svg and "22d3ee" not in svg   # subject colours flattened
    assert "#000000" in svg or "black" in svg            # rendered as ink
