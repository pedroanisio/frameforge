"""Model access for the Python SDK.

The authoritative Pydantic model lives inside the package at
``frameforge.model`` (moved from ``docs/models/frameforge.py`` in 2.5.0, when
the project became a real installable package). This module remains the SDK's
single accessor for it: callers that need the model programmatically use
``model_module()`` / ``validate_document()`` instead of importing the module
ad hoc, so the access pattern stays greppable and the model keeps one identity
in ``sys.modules``.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any

from pydantic import ValidationError

_MODEL = import_module("frameforge.model")

Document = _MODEL.Document
HEAD_VERSION: str = _MODEL.HEAD_VERSION


def model_module() -> ModuleType:
    """Return the authoritative model module used by the SDK."""
    return _MODEL


def validate_document(value: Any):
    """Validate ``value`` as a FrameForge document and return a model instance."""
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
