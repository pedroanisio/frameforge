"""Vector Construction Coach — a disciplined-process layer over the SDK (POC).

This is the buildable, honest subset of the POC-01 "Vector Drawing Coach" idea:
it does NOT draw for the model and it does NOT manufacture curve quality (the
review's ceiling). It provides the deterministic scaffold that demonstrably
helps — style-as-grammar, layer-order discipline, and the silhouette readability
gate — by *reusing* the existing SDK (primitives, renderer, validator). The
creative work (decomposition, control points, aesthetic judgement) stays with
the model; the critique rubrics are advisory VLM prompts, never measurements.

Boundary: this package imports only ``framegraph.sdk`` + stdlib (no ``tooling``),
per the package-boundary gate.
"""
from __future__ import annotations

from framegraph.coach.clean import clean, denoise_strokes, node_count, simplify_strokes, smooth_strokes
from framegraph.coach.critique import RUBRICS, stage_rubric
from framegraph.coach.figures import (
    CANONS,
    FigureFrame,
    FigureModel,
    Landmark,
    ProportionSignature,
    analyze,
    blend_signatures,
    dominant_contour,
    find_landmarks,
    mirror_outer,
    plausibility,
    proportion_signature,
    remap_dy,
    retarget,
    to_polygon_obj,
    width_profile,
)
from framegraph.coach.ingest import gradientize, ingest, recolor_to_style
from framegraph.coach.intent import DrawingIntent, parse_intent
from framegraph.coach.layers import STAGES, LayerPlan, create_plan, validate_order
from framegraph.coach.paint import (
    atmosphere, darkest, fade, glow, haze, lightest, linear, radial, soft_shadow, stop, vignette, wash,
)
from framegraph.coach.redraw import (
    curve_count, is_circular, is_rectangular, redraw, redraw_smooth, snap_primitives,
)
from framegraph.coach.silhouette import to_silhouette
from framegraph.coach.style import (
    STYLES, StyleProfile, apply_to_layerplan, cleanup_params, redraw_params, resolve_style,
)

__all__ = [
    "DrawingIntent",
    "parse_intent",
    "StyleProfile",
    "STYLES",
    "resolve_style",
    "apply_to_layerplan",
    "cleanup_params",
    "redraw_params",
    "STAGES",
    "LayerPlan",
    "create_plan",
    "validate_order",
    "to_silhouette",
    "ingest",
    "recolor_to_style",
    "gradientize",
    "clean",
    "denoise_strokes",
    "simplify_strokes",
    "smooth_strokes",
    "node_count",
    "RUBRICS",
    "stage_rubric",
    # paint / atmosphere layer
    "atmosphere",
    "glow",
    "vignette",
    "haze",
    "wash",
    "soft_shadow",
    "fade",
    "stop",
    "linear",
    "radial",
    "lightest",
    "darkest",
    # redraw layer
    "redraw",
    "redraw_smooth",
    "snap_primitives",
    "is_circular",
    "is_rectangular",
    "curve_count",
    # proportion-aware figure layer
    "ProportionSignature",
    "Landmark",
    "FigureFrame",
    "FigureModel",
    "CANONS",
    "blend_signatures",
    "width_profile",
    "find_landmarks",
    "proportion_signature",
    "dominant_contour",
    "analyze",
    "to_polygon_obj",
    "remap_dy",
    "retarget",
    "mirror_outer",
    "plausibility",
]
