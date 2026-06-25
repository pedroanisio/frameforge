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


# --- proportion-aware figure layer (coach.figures) ------------------------- #
#
# These pin the deterministic geometry ported from the sibling vela-nova
# pipeline (persistence landmarks, proportion signature, piecewise-affine
# retarget, mirror) and the *advisory* canon plausibility gate. Synthetic
# silhouettes only — no image, no anatomy oracle; the creative work stays the
# model's.
_FIGURE_CTRL = [
    (0.0, 0.06), (0.45, 0.46), (1.0, 0.16), (1.8, 1.05), (2.1, 0.95),
    (3.0, 0.50), (3.8, 0.86), (4.1, 0.80), (5.8, 0.42), (6.1, 0.38),
    (7.6, 0.26), (8.0, 0.34),
]


def _interp_hw(dy, ctrl):
    if dy <= ctrl[0][0]:
        return ctrl[0][1]
    if dy >= ctrl[-1][0]:
        return ctrl[-1][1]
    for (y0, w0), (y1, w1) in zip(ctrl, ctrl[1:]):
        if y0 <= dy <= y1:
            t = (dy - y0) / (y1 - y0) if y1 > y0 else 0.0
            return w0 + t * (w1 - w0)
    return ctrl[-1][1]


def _figure_points(*, head_count=8.0, fig_h=800.0, midline=400.0, top=40.0, n=90, ctrl=None):
    """A closed, bilaterally symmetric humanoid silhouette polygon (image px)."""
    ctrl = ctrl or _FIGURE_CTRL
    head_px = fig_h / 8.0          # anatomical span is 8 head-units of geometry
    right, left = [], []
    for i in range(n + 1):
        dy = 8.0 * i / n
        hw = _interp_hw(dy, ctrl)
        y = top + dy * head_px
        right.append([midline + hw * head_px, y])
        left.append([midline - hw * head_px, y])
    return right + list(reversed(left))


def test_canons_have_documented_head_counts():
    from framegraph.coach import CANONS
    assert abs(CANONS["vitruvian"].head_count() - 8.0) < 0.05
    assert abs(CANONS["polykleitos"].head_count() - 7.5) < 0.05
    assert abs(CANONS["fashion"].head_count() - 9.0) < 0.05
    # every canon names its landmarks and the segment ratios are a partition
    for name, sig in CANONS.items():
        assert sig.landmark_names, name
        assert abs(sum(sig.segment_ratios) - 1.0) < 1e-6, name


def test_blend_signatures_interpolates_head_count():
    from framegraph.coach import CANONS, blend_signatures
    lo, hi = CANONS["polykleitos"], CANONS["fashion"]
    assert abs(blend_signatures(lo, hi, 0.0).head_count() - lo.head_count()) < 0.05
    assert abs(blend_signatures(lo, hi, 1.0).head_count() - hi.head_count()) < 0.05
    mid = blend_signatures(lo, hi, 0.5).head_count()
    assert lo.head_count() < mid < hi.head_count()


def test_remap_dy_pins_landmarks_and_endpoints():
    from framegraph.coach import remap_dy
    src = [0.0, 1.0, 2.0, 3.0]
    tgt = [0.0, 0.5, 1.0, 3.0]        # last segment stretched
    assert remap_dy(0.0, src, tgt) == 0.0
    assert abs(remap_dy(2.0, src, tgt) - 1.0) < 1e-9      # landmark → landmark
    assert abs(remap_dy(2.5, src, tgt) - 2.0) < 1e-9      # midway in stretched seg
    assert abs(remap_dy(3.0, src, tgt) - 3.0) < 1e-9      # endpoint fixed


def test_dominant_contour_picks_largest_polygon():
    from framegraph.coach import dominant_contour
    objs = [
        {"type": "polyline", "points": [[0, 0], [1, 0], [1, 1]]},       # tiny
        {"type": "polygon", "points": _figure_points()},               # the figure
        {"type": "rect", "box": [0, 0, 5, 5]},                         # ignored
    ]
    pts = dominant_contour(objs)
    assert len(pts) == len(_figure_points())


def test_analyze_detects_ordered_anatomical_landmarks():
    from framegraph.coach import analyze
    fm = analyze(_figure_points())
    names = [lm.name for lm in fm.landmarks]
    # the structural majors are found, and in head-to-toe order
    assert "shoulder_peak" in names
    assert "hip_peak" in names
    assert "waist_valley" in names
    dys = [lm.dy for lm in fm.landmarks]
    assert dys == sorted(dys)
    # signature is a proper partition with a finite, positive head-count
    assert abs(sum(fm.signature.segment_ratios) - 1.0) < 1e-6
    assert 0.0 < fm.signature.head_count() < float("inf")


def test_plausibility_passes_canon_and_flags_degenerate():
    from framegraph.coach import CANONS, ProportionSignature, plausibility
    ok = plausibility(CANONS["vitruvian"])
    assert ok["plausible"] and not ok["issues"]
    # a 3-head squashed figure: head segment is a third of the body
    squashed = ProportionSignature([0.34, 0.33, 0.33], [0.3, 0.3, 0.2],
                                   ["a", "b", "c"], ["head_peak", "x", "y"])
    bad = plausibility(squashed)
    assert not bad["plausible"]
    assert any("head_count" in i.lower() for i in bad["issues"])
    # a collapsed (zero-length) segment from a missed landmark
    collapsed = ProportionSignature([0.001, 0.5, 0.499], [0.1, 0.2, 0.1],
                                    ["a", "b", "c"], ["head_peak", "x", "y"])
    assert not plausibility(collapsed)["plausible"]


def test_plausibility_distance_to_references_is_advisory_not_a_gate():
    from framegraph.coach import CANONS, plausibility
    # supplying references attaches a distance but never fabricates a hard verdict
    rep = plausibility(CANONS["vitruvian"], references=list(CANONS.values()))
    assert "reference_distance" in rep
    assert rep["reference_distance"] >= 0.0


def test_retarget_preserves_height_and_changes_geometry():
    from framegraph.coach import analyze, retarget
    fm = analyze(_figure_points())
    out = retarget(fm, "fashion")
    ys_in = [p[1] for p in fm.points]
    ys_out = [p[1] for p in out]
    h_in = max(ys_in) - min(ys_in)
    h_out = max(ys_out) - min(ys_out)
    assert abs(h_out - h_in) < 0.03 * h_in          # canon retarget keeps total height
    assert out != fm.points                          # but proportions moved
    assert len(out) == len(fm.points)                # geometry, point-for-point


def test_mirror_outer_is_symmetric_about_midline():
    from framegraph.coach import mirror_outer
    # an asymmetric right-leaning half-figure
    raw = [[400, 40], [470, 200], [430, 400], [500, 600], [400, 760]]
    full = mirror_outer(raw, midline=400.0)
    xs = [p[0] for p in full]
    left = min(xs) - 400.0
    right = max(xs) - 400.0
    assert abs(right + left) < 1e-6                  # widest left == widest right


def test_to_polygon_obj_emits_validatable_shape():
    from framegraph.coach import to_polygon_obj
    obj = to_polygon_obj(_figure_points(), fill="#101820", stroke="#FFFFFF", width=1.5)
    assert obj["type"] == "polygon"
    assert len(obj["points"]) == len(_figure_points())
    assert obj["fill"] == "#101820" and obj["stroke"] == "#FFFFFF"


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
