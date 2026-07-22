"""Parsing and serialization helpers for the Python SDK."""
from __future__ import annotations

import copy
import itertools
import json
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from frameforge.sdk.model import to_plain_dict, validate_document

Format = Literal["json", "yaml"]


def parse(text: str, *, validate: bool = True, forgiving: bool = True):
    """Parse JSON or YAML text.

    Valid current FrameForge text returns a Pydantic ``Document``. By default,
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
    """Ingest an existing SVG into FrameForge object dicts (vector import).

    ``svg`` is SVG text, a ``.svg`` path, or a ``data:image/svg+xml`` URI
    (plain, URL-encoded, or base64); the result is a list of primitive
    object dicts (``rect``/``ellipse``/``line``/``polyline``/``polygon``/
    ``path``) for :meth:`~frameforge.sdk.PageBuilder.extend`. ``box``
    (``[x, y, w, h]``) fits the SVG's viewBox into that box via a
    ``style.transform`` on every object; ``data_attrs=True`` carries ``data-*``
    attributes onto ``meta['data']``.

    This is the SDK-visible entry to
    :func:`frameforge.vision.infrastructure.svg_import.svg_to_objects`
    (imported lazily so the SDK stays light). Honest limits: solid paints with
    group inheritance and transform passthrough; no gradients-by-reference,
    ``<use>``, ``clipPath``/``mask``, CSS ``<style>`` rules, or ``<text>``.

    Gotcha: if you group the ingested objects and clip them, put the clip on a
    *static* parent group — the renderer nests ``style.clip_path`` INSIDE a
    group's ``style.transform``, so a clip on the transformed group rides along
    with the transform instead of masking in page coordinates.
    """
    from frameforge.vision.infrastructure.svg_import import svg_to_objects as _ingest

    return _ingest(svg, box=box, data_attrs=data_attrs)


_SVG_DATA_URI = "data:image/svg+xml"
# ObjBase fields an image shares with the group that replaces it — carried 1:1
# so placement, stacking, styling and semantics survive the lowering.
_CARRY_FIELDS = ("box", "z", "opacity", "rotation", "style", "bind",
                 "decorative", "construction", "shadow", "glow")


def _resolve_image_src(src: Any, assets: dict[str, Any]) -> str:
    """Literal src, or one defs.assets indirection (§9.3), as a string."""
    if not isinstance(src, str):
        return ""
    entry = assets.get(src)
    if isinstance(entry, dict):
        return str(entry.get("src") or "")
    return src


def lower_embedded_svg(doc: dict[str, Any], *, data_attrs: bool = False) -> dict[str, Any]:
    """Lower embedded-SVG image objects into native FrameForge objects.

    Walks a document dict (``pages`` → ``layers`` → objects, recursing through
    ``group`` children) and replaces every ``type: image`` object whose source —
    literal or via a ``defs.assets`` key — is a ``data:image/svg+xml`` URI with
    a ``group`` of native primitives ingested by :func:`svg_to_objects`:

    * the group keeps the image's ``id`` (or gets a stable ``region.<n>``),
      ``box``, and shared ObjBase fields (``z``, ``opacity``, ``style``, …);
    * children are fitted parent-relative into ``[0, 0, w, h]`` (the group box
      supplies the translation), ids are ``<group-id>.<index>``;
    * provenance rides on ``meta.region`` — the group records
      ``{source: 'image', id, alt, objects}``, each child records
      ``{id, source_layer, source_index}``.

    Detail trapped inside an embedded image is invisible to every object-level
    tool (recolor, design_audit, planar, effects); lowering unlocks all of it.
    Untouched: non-SVG images, ``placeholder`` images, file-path sources, and
    SVGs with no drawable elements. Pure: the input document is not mutated.
    """
    out = copy.deepcopy(doc)
    assets = ((out.get("defs") or {}).get("assets")) or {}
    fresh = itertools.count()

    def lower_obj(obj: Any) -> Any:
        if not isinstance(obj, dict):
            return obj
        if obj.get("type") == "group":
            kids = obj.get("children")
            if isinstance(kids, list):
                obj["children"] = [lower_obj(ch) for ch in kids]
            return obj
        if obj.get("type") != "image" or obj.get("placeholder"):
            return obj
        src = _resolve_image_src(obj.get("src"), assets)
        if not src.startswith(_SVG_DATA_URI):
            return obj
        box = obj.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return obj
        children = svg_to_objects(src, box=[0, 0, box[2], box[3]],
                                  data_attrs=data_attrs)
        if not children:
            return obj
        gid = obj.get("id") or f"region.{next(fresh)}"
        for i, child in enumerate(children):
            child["id"] = f"{gid}.{i}"
            meta = dict(child.get("meta") or {})
            meta["region"] = {"id": child["id"], "source_layer": gid,
                              "source_index": i}
            child["meta"] = meta
        group: dict[str, Any] = {"type": "group", "id": gid, "children": children}
        for field in _CARRY_FIELDS:
            if obj.get(field) is not None:
                group[field] = obj[field]
        meta = dict(obj.get("meta") or {})
        region = {"source": "image", "id": gid, "objects": len(children)}
        if obj.get("alt") is not None:
            region["alt"] = obj["alt"]
        meta["region"] = region
        group["meta"] = meta
        return group

    for page in out.get("pages") or []:
        if not isinstance(page, dict) or page.get("mode") != "page":
            continue
        for layer in page.get("layers") or []:
            if isinstance(layer, dict) and isinstance(layer.get("objects"), list):
                layer["objects"] = [lower_obj(o) for o in layer["objects"]]
    return out


__all__ = ["parse", "serialize", "svg_to_objects", "lower_embedded_svg"]
