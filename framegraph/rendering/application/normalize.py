"""Legacy-document normalization for the rendering pipeline.

Expands legacy ``use``/symbol references and the older ``presentation-deck``
shape into the canonical FrameGraph document the ``Renderer`` consumes. Relocated
verbatim from ``tooling/render_fixtures.py`` so the rendering bounded context no
longer imports *up* into the tooling scripts — the ``framegraph`` package stays
import-self-contained (see codebase-standards §2/§13). ``tooling.render_fixtures``
re-exports ``normalize_doc`` from here for its CLI and backward compatibility.
"""
from __future__ import annotations

import copy

USE_KEYS = {"type", "id", "symbol", "box", "params", "decorative"}


def _subst_legacy_value(value, context):
    if isinstance(value, str) and value.startswith("$"):
        key = value[1:]
        return copy.deepcopy(context.get(key, value))
    if isinstance(value, list):
        return [_subst_legacy_value(item, context) for item in value]
    if isinstance(value, dict):
        return {k: _subst_legacy_value(v, context) for k, v in value.items()}
    return value


def _expand_legacy_use(obj, symbols):
    if not isinstance(obj, dict):
        return obj
    if obj.get("type") != "use":
        out = copy.deepcopy(obj)
        for key in ("children", "content", "items"):
            if isinstance(out.get(key), list):
                out[key] = [_expand_legacy_use(child, symbols) for child in out[key]]
        if isinstance(out.get("object"), dict):
            out["object"] = _expand_legacy_use(out["object"], symbols)
        return out

    symbol = symbols.get(obj.get("symbol")) or {}
    params = obj.get("params") if isinstance(obj.get("params"), dict) else {}
    slots = {k: v for k, v in obj.items() if k not in USE_KEYS}
    context = {**params, **slots}
    children = [
        _expand_legacy_use(_subst_legacy_value(copy.deepcopy(child), context), symbols)
        for child in symbol.get("objects", [])
    ]
    return {
        "type": "group",
        "id": obj.get("id"),
        "box": obj.get("box") or symbol.get("box"),
        "decorative": obj.get("decorative"),
        "children": children,
        "meta": {"source_symbol": obj.get("symbol")},
    }


def normalize_doc(doc):
    if not isinstance(doc, dict) or doc.get("dsl") != "FrameGraph":
        return doc
    if isinstance(doc.get("pages"), list):
        symbols = ((doc.get("defs") or {}).get("symbols") or {})
        if not symbols:
            return doc
        out = copy.deepcopy(doc)
        for page in out.get("pages") or []:
            for layer in page.get("layers") or []:
                layer["objects"] = [_expand_legacy_use(obj, symbols) for obj in layer.get("objects") or []]
            for key in ("story", "sections"):
                if isinstance(page.get(key), list):
                    page[key] = [_expand_legacy_use(block, symbols) for block in page[key]]
        return out
    if isinstance(doc.get("pages"), list):
        return doc
    if doc.get("kind") != "presentation-deck" or not isinstance(doc.get("slides"), list):
        return doc

    deck = doc.get("deck") or {}
    symbols = deck.get("symbols") or {}
    tokens = {**(((doc.get("defs") or {}).get("tokens")) or {}), **(deck.get("tokens") or {})}
    pages = []
    for index, slide in enumerate(doc.get("slides") or []):
        visual = slide.get("visual") or {}
        layers = []
        for layer in visual.get("layers") or []:
            layer_out = copy.deepcopy(layer)
            layer_out["objects"] = [_expand_legacy_use(obj, symbols) for obj in layer.get("objects") or []]
            layers.append(layer_out)
        pages.append({
            "mode": "page",
            "id": slide.get("id") or f"slide_{index + 1}",
            "title": slide.get("title"),
            "canvas": slide.get("canvas") or deck.get("canvas"),
            "layers": layers,
            "meta": {
                **(slide.get("meta") or {}),
                "source_kind": doc.get("kind"),
                "slide": slide.get("slide"),
                "description": slide.get("description"),
                "notes": slide.get("notes"),
            },
        })
    return {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "profile": "deck",
        "title": doc.get("title") or deck.get("title") or "FrameGraph presentation deck",
        "description": doc.get("description"),
        "defs": {**(doc.get("defs") or {}), "tokens": tokens},
        "pages": pages,
        "meta": {**(doc.get("meta") or {}), "source_kind": doc.get("kind")},
    }


__all__ = ["normalize_doc"]
