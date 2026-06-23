"""Parsing and serialization helpers for the Python SDK."""
from __future__ import annotations

import json
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from framegraph.sdk.model import to_plain_dict, validate_document

Format = Literal["json", "yaml"]


def parse(text: str, *, validate: bool = True, forgiving: bool = True):
    """Parse JSON or YAML text.

    Valid current FrameGraph text returns a Pydantic ``Document``. By default,
    text that is syntactically valid YAML/JSON but ahead of the SDK's model is
    returned as raw data for inspection. Pass ``forgiving=False`` to require a
    current-schema document.
    """
    data = yaml.safe_load(text)
    if validate:
        try:
            return validate_document(data)
        except ValidationError:
            if forgiving:
                return data
            raise
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
