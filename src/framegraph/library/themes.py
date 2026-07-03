"""Consulting themes — v2 ``defs.tokens`` fragments (issue #32).

Seven token packs absorbed from the predecessor project's ``lib/tokens/``
(McKinsey, BCG, Bain, Deloitte, EY, KPMG, PwC — house-style *homages*, per
the packs' own ``_meta``). Each theme file under ``data/themes/`` is already
translated to the v2 tokens shape: ``colors``, ``fonts``, ``text_styles``
(``font_family`` lists, ``font_size``/``font_weight``, ``vertical_align``),
``stroke_styles``, plus ``fill_styles``/``glyph_map`` where the pack ships
them. ``load_theme`` returns a fresh copy suitable for direct use as (or
merging into) a document's ``defs.tokens``.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

THEMES_DIR = Path(__file__).resolve().parent / "data" / "themes"


def list_themes() -> list[str]:
    """Names of the committed themes, sorted."""
    return sorted(p.stem for p in THEMES_DIR.glob("*.yml"))


@lru_cache(maxsize=None)
def _load_raw(name: str) -> dict[str, Any]:
    path = THEMES_DIR / f"{name}.yml"
    if not path.is_file():
        raise KeyError(f"unknown theme {name!r}; available: {list_themes()}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("colors"):
        raise ValueError(f"theme {name!r} is not a v2 tokens fragment")
    return data


def load_theme(name: str) -> dict[str, Any]:
    """One theme as a v2 ``defs.tokens`` fragment (a fresh, mutable copy)."""
    return copy.deepcopy(_load_raw(name))


__all__ = ["THEMES_DIR", "list_themes", "load_theme"]
