"""Python SDK for authoring, validating, expanding, and serializing FrameGraph.

The SDK is a hand-written Python binding over the repository's authoritative
Pydantic model in :mod:`models.framegraph`. It deliberately does not duplicate
core schema types; builders and helpers lower into the model and validate there.
"""
from __future__ import annotations

from framegraph.sdk.author import DocumentBuilder, PageBuilder
from framegraph.sdk.chart import Chart
from framegraph.sdk.draw import Frame, Scene3D
from framegraph.sdk.expand import ExpandOptions, ExpandedDocument, expand
from framegraph.sdk.geometry import CubicBezier, Mat3, Mat4, Path, Vec2, Vec3
from framegraph.sdk.io import parse, serialize
from framegraph.sdk.layout import column, grid, inset, row
from framegraph.sdk.macros import lorem, lorem_paragraphs, md, paragraph, theme
from framegraph.sdk.metrics import measure_text, text_height, wrap_text
from framegraph.sdk.model import HEAD_VERSION, Document, model_module
from framegraph.sdk.paint import (
    glow,
    linear_gradient,
    radial_gradient,
    rgba,
    shadow,
    stroke,
)
from framegraph.sdk.validate import Issue, ValidationReport, validate_static_rules

__all__ = [
    "Chart",
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
    "column",
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
