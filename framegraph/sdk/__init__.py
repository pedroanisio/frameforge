"""Python SDK for authoring, validating, expanding, and serializing FrameGraph.

The SDK is a hand-written Python binding over the repository's authoritative
Pydantic model in :mod:`models.framegraph`. It deliberately does not duplicate
core schema types; builders and helpers lower into the model and validate there.
"""
from __future__ import annotations

from framegraph.sdk.author import DocumentBuilder, PageBuilder
from framegraph.sdk.chart import Chart
from framegraph.sdk.clip import (
    clip_circle,
    clip_ellipse,
    clip_inset,
    clip_path,
    clip_polygon,
    clip_rect,
)
from framegraph.sdk.draw import Frame, Scene3D
from framegraph.sdk.expand import ExpandOptions, ExpandedDocument, expand
from framegraph.sdk.geometry import CubicBezier, Mat3, Mat4, Path, Vec2, Vec3
from framegraph.sdk.io import parse, serialize
from framegraph.sdk.layout import Box, column, grid, inset, row
from framegraph.sdk.macros import lorem, lorem_paragraphs, md, paragraph, theme
from framegraph.sdk.metrics import measure_text, text_height, wrap_text
from framegraph.sdk.model import HEAD_VERSION, Document, model_module
from framegraph.sdk.paint import (
    effects,
    glow,
    linear_gradient,
    pattern,
    radial_gradient,
    rgba,
    shadow,
    stroke,
)
from framegraph.sdk.validate import Issue, ValidationReport, validate_static_rules
from framegraph.sdk.widgets import (
    Panel,
    Theme,
    avatar,
    badge,
    badge_width,
    button,
    card,
    default_theme,
    divider,
    field,
    kpi,
    pill,
    progress,
    register_theme,
    table,
    tabs,
    toggle,
)

__all__ = [
    "Chart",
    "Panel",
    "Theme",
    "avatar",
    "badge",
    "badge_width",
    "button",
    "card",
    "clip_circle",
    "clip_ellipse",
    "clip_inset",
    "clip_path",
    "clip_polygon",
    "clip_rect",
    "default_theme",
    "divider",
    "field",
    "kpi",
    "pill",
    "progress",
    "register_theme",
    "table",
    "tabs",
    "toggle",
    "CubicBezier",
    "Document",
    "DocumentBuilder",
    "ExpandOptions",
    "ExpandedDocument",
    "Frame",
    "HEAD_VERSION",
    "Issue",
    "Mat3",
    "Mat4",
    "PageBuilder",
    "Path",
    "Scene3D",
    "ValidationReport",
    "Vec2",
    "Vec3",
    "Box",
    "column",
    "effects",
    "expand",
    "glow",
    "grid",
    "inset",
    "linear_gradient",
    "lorem",
    "lorem_paragraphs",
    "md",
    "measure_text",
    "model_module",
    "paragraph",
    "pattern",
    "parse",
    "radial_gradient",
    "rgba",
    "row",
    "serialize",
    "shadow",
    "stroke",
    "text_height",
    "theme",
    "validate_static_rules",
    "wrap_text",
]
