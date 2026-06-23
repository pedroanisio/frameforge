"""Conformance helpers for SDK users and tests."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from tooling.render_fixtures import Renderer, normalize_doc

from framegraph.sdk.model import validate_document


def render_page_svgs(model: Any, *, base_dir: str | None = None) -> list[str]:
    """Render a document through the repository SVG proxy and return page SVGs."""
    data = validate_document(model).model_dump(by_alias=True, exclude_none=True)
    doc = normalize_doc(data)
    root = base_dir or "."
    renderer = Renderer(doc, root)
    svgs: list[str] = []
    for page in doc.get("pages", []):
        if isinstance(page, dict):
            svgs.extend(renderer.render_page(page))
    return svgs


def page_hashes(model: Any, *, base_dir: str | None = None) -> tuple[str, ...]:
    """Return SHA-256 hashes for the proxy SVG render of each page."""
    return tuple(sha256(svg.encode("utf-8")).hexdigest() for svg in render_page_svgs(model, base_dir=base_dir))


def assert_golden(model: Any, expected: list[str] | tuple[str, ...], *, base_dir: str | None = None) -> None:
    """Assert that a document's proxy-render page hashes match ``expected``."""
    got = page_hashes(model, base_dir=base_dir)
    want = tuple(expected)
    if got != want:
        raise AssertionError(f"golden mismatch: expected {want!r}, got {got!r}")


def write_golden(path: str | Path, hashes: list[str] | tuple[str, ...]) -> None:
    """Write one page hash per line for a small SDK-level golden file."""
    Path(path).write_text("\n".join(hashes) + "\n", encoding="utf-8")


__all__ = ["assert_golden", "page_hashes", "render_page_svgs", "write_golden"]
