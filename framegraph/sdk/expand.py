"""Expansion helpers for deterministic FrameGraph documents."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
from typing import Any

from framegraph.sdk.model import validate_document


@dataclass(frozen=True)
class ExpandOptions:
    """Options for SDK expansion."""

    base_dir: str | os.PathLike[str] | None = None
    pin_assets: bool = True


@dataclass(frozen=True)
class ExpandedDocument:
    """Expanded document plus expansion metadata."""

    document: Any
    pinned: tuple[str, ...]


def expand(model: Any, opts: ExpandOptions | None = None) -> ExpandedDocument:
    """Expand deterministic SDK-resolvable pieces and return a validated model.

    Current expansion pins local asset and font hashes. Geometry helpers already
    emit concrete 2D FrameGraph primitives before documents reach this function;
    unsupported future computed nodes fail validation instead of leaking through.
    """
    options = opts or ExpandOptions()
    data = validate_document(model).model_dump(by_alias=True, exclude_none=True)
    base = Path(options.base_dir) if options.base_dir is not None else Path.cwd()
    pinned: list[str] = []
    if options.pin_assets:
        _pin_asset_defs(data, base, pinned)
        _pin_font_defs(data, base, pinned)
    expanded = validate_document(data)
    return ExpandedDocument(document=expanded, pinned=tuple(pinned))


def _pin_asset_defs(data: dict[str, Any], base: Path, pinned: list[str]) -> None:
    assets = (((data.get("defs") or {}).get("assets")) or {})
    for name, asset in assets.items():
        if not isinstance(asset, dict) or asset.get("hash"):
            continue
        src = asset.get("src")
        digest = _hash_local_src(src, base)
        if digest:
            asset["hash"] = digest
            pinned.append(f"defs.assets.{name}")


def _pin_font_defs(data: dict[str, Any], base: Path, pinned: list[str]) -> None:
    fonts = ((((data.get("defs") or {}).get("tokens") or {}).get("fonts")) or {})
    for name, font in fonts.items():
        if not isinstance(font, dict) or font.get("hash"):
            continue
        digest = _hash_local_src(font.get("src"), base)
        if digest:
            font["hash"] = digest
            pinned.append(f"defs.tokens.fonts.{name}")


def _hash_local_src(src: object, base: Path) -> str | None:
    if not isinstance(src, str) or _is_remote_or_data(src):
        return None
    path = Path(src)
    if not path.is_absolute():
        path = base / path
    if not path.is_file():
        return None
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _is_remote_or_data(src: str) -> bool:
    value = src.strip().lower()
    return value.startswith(("http://", "https://", "data:", "url("))


__all__ = ["ExpandOptions", "ExpandedDocument", "expand"]
