"""Model access for the Python SDK.

The repository intentionally has both a package named ``frameforge`` and an
authoritative model module at ``docs/models/frameforge.py``. SDK code imports
the model through the ``models`` namespace so the package is not shadowed.

Callers inside the gates export ``PYTHONPATH=src:docs`` (the Makefile) or use
``conftest.py``; the CLI front door and bare ``uv run`` invocations do not —
so when ``models`` is not already importable, derive ``<repo>/docs`` from this
file's own location (``src/frameforge/sdk/model.py`` → three parents up) and
retry. The fallback only ever *appends* a path; a caller-provided ``models``
always wins (issue #35).
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import ValidationError

try:
    _MODEL = import_module("models.frameforge")
except ModuleNotFoundError:
    _docs = Path(__file__).resolve().parents[3] / "docs"
    if not (_docs / "models" / "frameforge.py").is_file():
        raise
    sys.path.append(str(_docs))
    _MODEL = import_module("models.frameforge")

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
