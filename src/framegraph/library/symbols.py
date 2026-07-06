"""Symbol packs — reusable ``defs.symbols`` bodies (issue #32).

Four packs absorbed from the predecessor project's ``lib/symbols/`` and
translated to v2 under ``data/symbols/``:

- ``covers`` — ``cover_minimal_sidebar`` (title slide, right accent pane);
- ``sections`` — ``agenda_left_pane`` (numbered agenda, left pane);
- ``shared`` — ``insight_box``, ``kpi_card``, ``two_by_two``, ``s_node``;
- ``hex`` — the honeycomb/module cells (``hex_header``, ``hex_leaf_*``,
  ``hex_node_*``) consumed by :mod:`framegraph.library.generators`.

Symbols are instantiated with grammar-level ``use`` objects and lowered by
:func:`framegraph.sdk.expand`. Their text objects reference style tokens by
name; ``shared`` relies on theme styles (``body``, ``callout``,
``exhibit_header`` …) while the other packs need the pack-scoped styles
served by :func:`support_text_styles` — merge those into the document's
``defs.tokens.text_styles`` alongside a theme.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SYMBOLS_DIR = Path(__file__).resolve().parent / "data" / "symbols"

_FONT = ["Arial", "Helvetica", "sans-serif"]

#: Pack-scoped text styles referenced by symbol bodies but intentionally not
#: baked into them (v0.1 left these to the consumer; defaults follow each
#: pack's documented reference design).
_SUPPORT_TEXT_STYLES: dict[str, dict[str, dict[str, Any]]] = {
    "covers": {
        "cover_minimal_title": {
            "font_family": _FONT, "font_size": 44, "font_weight": 700,
            "color": "#1A2B3E", "align": "left", "vertical_align": "middle",
            "line_height": 50},
        "cover_minimal_subtitle": {
            "font_family": _FONT, "font_size": 20, "font_weight": 400,
            "color": "#8A8A8A", "align": "left", "vertical_align": "top"},
        "cover_minimal_page_number": {
            "font_family": _FONT, "font_size": 13, "font_weight": 400,
            "color": "#8A8A8A", "align": "center", "vertical_align": "middle"},
    },
    "sections": {
        "agenda_section_label": {
            "font_family": _FONT, "font_size": 22, "font_weight": 700,
            "color": "#FFFFFF", "align": "left", "vertical_align": "top",
            "line_height": 28},
        "agenda_item_num": {
            "font_family": _FONT, "font_size": 15, "font_weight": 700,
            "color": "#1A2B3E", "align": "right", "vertical_align": "middle"},
        "agenda_item": {
            "font_family": _FONT, "font_size": 15, "font_weight": 400,
            "color": "#1A2B3E", "align": "left", "vertical_align": "middle"},
        "agenda_page_number": {
            "font_family": _FONT, "font_size": 13, "font_weight": 400,
            "color": "#9A9A9A", "align": "center", "vertical_align": "middle"},
    },
    "shared": {},  # theme text styles (body, callout, exhibit_* …) suffice
    "hex": {
        "honeycomb_header_text": {
            "font_family": _FONT, "font_size": 13, "font_weight": 700,
            "color": "#FFFFFF", "align": "center", "vertical_align": "middle",
            "line_height": 16},
        "honeycomb_leaf_text": {
            "font_family": _FONT, "font_size": 12, "font_weight": 400,
            "color": "#1A2B3E", "align": "center", "vertical_align": "middle",
            "line_height": 15},
        "module_icon_warning": {
            "font_family": _FONT, "font_size": 22, "font_weight": 700,
            "color": "#1A1A1A", "align": "center", "vertical_align": "middle"},
        "module_icon_excel": {
            "font_family": _FONT, "font_size": 24, "font_weight": 700,
            "color": "#FFFFFF", "align": "center", "vertical_align": "middle"},
        "module_icon_money": {
            "font_family": _FONT, "font_size": 22, "font_weight": 700,
            "color": "#1A2B3E", "align": "center", "vertical_align": "middle"},
    },
}


@lru_cache(maxsize=None)
def _load_pack(pack: str) -> dict[str, Any]:
    path = SYMBOLS_DIR / f"{pack}.yml"
    if not path.is_file():
        raise KeyError(f"unknown symbol pack {pack!r}; available: "
                       f"{sorted(p.stem for p in SYMBOLS_DIR.glob('*.yml'))}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    symbols = (data or {}).get("symbols")
    if not isinstance(symbols, dict) or not symbols:
        raise ValueError(f"symbol pack {pack!r} carries no symbols")
    return symbols


def list_symbols() -> dict[str, list[str]]:
    """``{pack: [symbol names]}`` for every committed pack."""
    return {p.stem: sorted(_load_pack(p.stem))
            for p in sorted(SYMBOLS_DIR.glob("*.yml"))}


def load_symbols(*packs: str) -> dict[str, Any]:
    """Merged symbol bodies for ``defs.symbols`` (all packs when none named)."""
    names = packs or tuple(sorted(p.stem for p in SYMBOLS_DIR.glob("*.yml")))
    merged: dict[str, Any] = {}
    for pack in names:
        merged.update(copy.deepcopy(_load_pack(pack)))
    return merged


def support_text_styles(*packs: str) -> dict[str, dict[str, Any]]:
    """Pack-scoped text styles the named packs' symbols reference by token.

    Merge into ``defs.tokens.text_styles`` (theme styles first, these after —
    or before, to let a theme override the pack defaults).
    """
    names = packs or tuple(_SUPPORT_TEXT_STYLES)
    merged: dict[str, dict[str, Any]] = {}
    for pack in names:
        if pack not in _SUPPORT_TEXT_STYLES:
            raise KeyError(f"unknown symbol pack {pack!r}")
        merged.update(copy.deepcopy(_SUPPORT_TEXT_STYLES[pack]))
    return merged


__all__ = ["SYMBOLS_DIR", "list_symbols", "load_symbols", "support_text_styles"]
