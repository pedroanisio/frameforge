"""`DocumentRenderer` adapters — the coarse output-port backends.

These are the whole-document output backends (`…domain.ports.DocumentRenderer`),
kept distinct from the fine-grained per-primitive `ScenePainter` adapters in
`…painters`. The CLI resolves a backend here by its `--to` name and renders
through the port, in-process — no subprocess to a script in `tooling/`.
"""
from __future__ import annotations

from typing import Optional

from frameforge.rendering.domain.ports import DocumentRenderer
from frameforge.rendering.infrastructure.backends.html import HtmlDocumentRenderer
from frameforge.rendering.infrastructure.backends.pdf_tex import PdfTexDocumentRenderer

__all__ = [
    "HtmlDocumentRenderer",
    "PdfTexDocumentRenderer",
    "get_backend",
    "all_backends",
]

# One default instance per target. Adapters hold no per-run state (per-invocation
# knobs travel through `render(..., options=...)`), so sharing instances is safe.
_REGISTRY: dict[str, DocumentRenderer] = {
    b.target: b for b in (HtmlDocumentRenderer(), PdfTexDocumentRenderer())
}


def get_backend(target: str) -> Optional[DocumentRenderer]:
    """Return the `DocumentRenderer` for a `--to` target, or None if unknown."""
    return _REGISTRY.get(target)


def all_backends() -> dict[str, DocumentRenderer]:
    """Every registered backend, keyed by target (a copy of the registry)."""
    return dict(_REGISTRY)
