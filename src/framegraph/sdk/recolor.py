"""recolor() — one-call palette remap over a whole document (AI-16, W4/#48).

The declarative Recolor Artwork: a mapping of old→new colours is applied to
``defs.tokens.colors`` (by token NAME or by current value), to every paint
literal on objects/styles, and to gradient stops — in one pass, returning a
NEW document (the input is never mutated). Hex matching is
case-insensitive; unmapped colours are untouched.

Paint-carrying positions are matched by key, not by value shape, so a hex
string inside text content is never rewritten: a string is replaced only
under a known paint key (``fill``/``stroke``/``background``/…), a key named
``color``, or a key ending in ``_color``.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

__all__ = ["recolor"]

_PAINT_KEYS = {"fill", "stroke", "background", "background_color", "color"}


def _is_paint_key(key: str) -> bool:
    return key in _PAINT_KEYS or key.endswith("_color")


def _normalize(mapping: Mapping[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Split the mapping into hex-valued keys and token-name keys."""
    by_hex, by_name = {}, {}
    for key, new in mapping.items():
        if isinstance(key, str) and key.startswith("#"):
            by_hex[key.lower()] = new
        else:
            by_name[key] = new
    return by_hex, by_name


def _swap(value: Any, by_hex: dict[str, str]) -> Any:
    if isinstance(value, str):
        return by_hex.get(value.lower(), value)
    return value


def _walk(node: Any, by_hex: dict[str, str]) -> None:
    if isinstance(node, list):
        for item in node:
            _walk(item, by_hex)
        return
    if not isinstance(node, dict):
        return
    for key, value in list(node.items()):
        if isinstance(value, str) and _is_paint_key(key):
            node[key] = _swap(value, by_hex)
        else:
            _walk(value, by_hex)


def recolor(doc: dict[str, Any], mapping: Mapping[str, str]) -> dict[str, Any]:
    """A deep copy of ``doc`` with the palette remapped.

    ``mapping`` keys are hex colours (matched case-insensitively wherever a
    paint key carries them, including gradient stops and token values) or
    ``defs.tokens.colors`` names (remapped in place, so every token
    reference follows automatically).
    """
    by_hex, by_name = _normalize(mapping)
    out = copy.deepcopy(doc)
    colors = (((out.get("defs") or {}).get("tokens") or {}).get("colors")) or {}
    for name in list(colors):
        if name in by_name:
            colors[name] = by_name[name]
        else:
            colors[name] = _swap(colors[name], by_hex)
    _walk(out.get("pages"), by_hex)
    _walk((out.get("defs") or {}).get("symbols"), by_hex)
    _walk((out.get("defs") or {}).get("components"), by_hex)
    tokens = (out.get("defs") or {}).get("tokens") or {}
    for section in ("text_styles", "stroke_styles", "styles", "fill_styles"):
        _walk(tokens.get(section), by_hex)
    return out
