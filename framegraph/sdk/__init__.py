"""Python SDK for authoring, validating, expanding, and serializing FrameGraph.

The SDK is a hand-written Python binding over the repository's authoritative
Pydantic model in :mod:`models.framegraph`. It deliberately does not duplicate
core schema types; builders and helpers lower into the model and validate there.
"""
from __future__ import annotations

from framegraph.sdk.author import DocumentBuilder, PageBuilder
from framegraph.sdk.draw import Frame, Scene3D
from framegraph.sdk.expand import ExpandOptions, ExpandedDocument, expand
from framegraph.sdk.geometry import CubicBezier, Mat3, Mat4, Path, Vec2, Vec3
from framegraph.sdk.io import parse, serialize
from framegraph.sdk.macros import lorem, lorem_paragraphs, md, paragraph, theme
from framegraph.sdk.model import HEAD_VERSION, Document, model_module
from framegraph.sdk.validate import Issue, ValidationReport, validate_static_rules

__all__ = [
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
    "expand",
    "lorem",
    "lorem_paragraphs",
    "md",
    "model_module",
    "paragraph",
    "parse",
    "serialize",
    "theme",
    "validate_static_rules",
]
