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


def svg_to_objects(svg: Any, *, box: Any = None, data_attrs: bool = False) -> list[dict[str, Any]]:
    """Ingest an existing SVG into FrameGraph object dicts (vector import).

    ``svg`` is SVG text or a ``.svg`` path; the result is a list of primitive
    object dicts (``rect``/``ellipse``/``line``/``polyline``/``polygon``/
    ``path``) for :meth:`~framegraph.sdk.PageBuilder.extend`. ``box``
    (``[x, y, w, h]``) fits the SVG's viewBox into that box via a
    ``style.transform`` on every object; ``data_attrs=True`` carries ``data-*``
    attributes onto ``meta['data']``.

    This is the SDK-visible entry to
    :func:`framegraph.vision.infrastructure.svg_import.svg_to_objects`
    (imported lazily so the SDK stays light). Honest limits: solid paints with
    group inheritance and transform passthrough; no gradients-by-reference,
    ``<use>``, ``clipPath``/``mask``, CSS ``<style>`` rules, or ``<text>``.

    Gotcha: if you group the ingested objects and clip them, put the clip on a
    *static* parent group — the renderer nests ``style.clip_path`` INSIDE a
    group's ``style.transform``, so a clip on the transformed group rides along
    with the transform instead of masking in page coordinates.
    """
    from framegraph.vision.infrastructure.svg_import import svg_to_objects as _ingest

    return _ingest(svg, box=box, data_attrs=data_attrs)


__all__ = ["parse", "serialize", "svg_to_objects"]
