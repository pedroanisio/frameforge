"""Model access for the Python SDK.

The repository intentionally has both a package named ``framegraph`` and an
authoritative model module at ``models/framegraph.py``. SDK code imports the
model through the ``models`` namespace so the package is not shadowed.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any

from pydantic import ValidationError

_MODEL = import_module("models.framegraph")

Document = _MODEL.Document
HEAD_VERSION: str = _MODEL.HEAD_VERSION


def model_module() -> ModuleType:
    """Return the authoritative model module used by the SDK."""
    return _MODEL


def validate_document(value: Any):
    """Validate ``value`` as a FrameGraph document and return a model instance."""
    return Document.model_validate(value)


def to_plain_dict(value: Any) -> dict[str, Any]:
    """Return a JSON-compatible document dict after model validation."""
    model = validate_document(value)
    return model.model_dump(by_alias=True, exclude_none=True)


__all__ = [
    "Document",
    "HEAD_VERSION",
    "ValidationError",
    "model_module",
    "to_plain_dict",
    "validate_document",
]
