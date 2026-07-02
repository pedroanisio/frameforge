"""Conformance helpers for SDK users and tests."""
from __future__ import annotations

import copy
from hashlib import sha256
from pathlib import Path
from typing import Any

from framegraph.rendering.application.normalize import normalize_doc
from framegraph.rendering.application import renderer as _renderer_module
from framegraph.rendering.application.renderer import Renderer  # noqa: F401 — re-export compat

from framegraph.sdk.model import validate_document


def render_pages_with_stats(
    model: Any,
    *,
    base_dir: str | None = None,
    real_metrics: bool | None = None,
    layout_report: bool = False,
    diagnostics: bool = False,
):
    """Render a document through the SVG proxy, returning the page SVGs and the
    renderer's text-fit telemetry.

    The stats dict is the renderer's per-document ``tstats`` (``total``, ``wrapped``,
    ``shrunk``, ``clipped``, ``contained``, ``naive_overflow``, ``visible_overflow``,
    ``uncontained``). A non-zero ``clipped`` means text exceeded its box and was
    clipped/ellipsized — some intentional (``text_overflow: ellipsis``,
    ``line_clamp``), some lossy — so callers should surface it for verification, not
    treat it as a hard error.

    ``real_metrics`` threads the renderer's glyph-advance text measurement: ``None``
    (the default) keeps the renderer's behaviour of consulting the
    ``FRAMEGRAPH_REAL_METRICS`` environment variable; an explicit bool always wins
    over the env var. ``layout_report=True`` additionally collects per-object final
    boxes + fitted font sizes in the diagnostics ``layout`` list.

    With ``diagnostics=True`` a third element is returned — the renderer's
    structured feedback dict (``warnings``, ``skipped_objects``,
    ``skipped_flowables``, ``font_fallbacks``, ``layout``) — so callers such as the
    MCP pipeline can surface render-side signals without replicating the render
    loop. The default return stays the historical ``(svgs, tstats)`` 2-tuple.
    """
    data = validate_document(model).model_dump(by_alias=True, exclude_none=True)
    doc = normalize_doc(data)
    root = base_dir or "."
    # Resolve the class through the module at call time (not the import-time
    # binding) so tests/tools that monkeypatch `renderer.Renderer` are honored —
    # the contract the MCP pipeline's real-metrics wiring is verified against.
    renderer = _renderer_module.Renderer(
        doc, root, real_metrics=real_metrics, layout_report=layout_report)
    svgs: list[str] = []
    for page in doc.get("pages", []):
        if isinstance(page, dict):
            svgs.extend(renderer.render_page(page))
    if diagnostics:
        # font_fallbacks is only populated by font_report() (fc-match probe);
        # without this call the advertised substitution signal can never fire.
        try:
            renderer.font_report()
        except Exception as exc:  # fc-match absent/broken must not kill the render
            renderer.diagnostics["warnings"].append(f"font_report failed: {exc}")
        return svgs, dict(renderer.tstats), copy.deepcopy(renderer.diagnostics)
    return svgs, dict(renderer.tstats)


def render_page_svgs(model: Any, *, base_dir: str | None = None) -> list[str]:
    """Render a document through the repository SVG proxy and return page SVGs."""
    svgs, _ = render_pages_with_stats(model, base_dir=base_dir)
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


__all__ = [
    "assert_golden",
    "page_hashes",
    "render_page_svgs",
    "render_pages_with_stats",
    "write_golden",
]
