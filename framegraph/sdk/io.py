"""Parsing and serialization helpers for the Python SDK."""
from __future__ import annotations

import json
from typing import Any, Literal

import yaml

from framegraph.sdk.model import to_plain_dict, validate_document

Format = Literal["json", "yaml"]


def parse(text: str, *, validate: bool = True):
    """Parse JSON or YAML text.

    By default this returns a validated Pydantic ``Document``. Set
    ``validate=False`` to get the raw mapping for forgiving inspection.
    """
    data = yaml.safe_load(text)
    if validate:
        return validate_document(data)
    return data


def serialize(model: Any, *, format: Format = "yaml") -> str:
    """Serialize a document as canonical JSON or YAML after model validation."""
    data = to_plain_dict(model)
    if format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if format == "yaml":
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    raise ValueError(f"unsupported format: {format!r}")


__all__ = ["parse", "serialize"]
