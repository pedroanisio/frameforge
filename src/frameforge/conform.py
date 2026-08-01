"""Conformance helpers for SDK users and tests."""
from __future__ import annotations

import copy
from hashlib import sha256
from pathlib import Path
from typing import Any

from frameforge.rendering.application.normalize import normalize_doc
from frameforge.rendering.application import renderer as _renderer_module
from frameforge.rendering.application.renderer import Renderer  # noqa: F401 — re-export compat
from frameforge.rendering.domain.services.legibility import (
    LegibilityPolicy,
    LegibilitySignal,
    assess_pages,
)
from frameforge.rendering.domain.services.overflow import OverflowSignal
from frameforge.rendering.domain.services.paint_intent import PaintSignal

from frameforge_sdk.model import validate_document


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
    ``FRAMEFORGE_REAL_METRICS`` environment variable; an explicit bool always wins
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
        diags = copy.deepcopy(renderer.diagnostics)
        # Human-legibility signals read the FINISHED SVG (type below the legible
        # floor, WCAG contrast against the ink actually painted behind the text,
        # measure, leading), so they are assessed here rather than inside the
        # renderer. The channel always exists — an empty list means the pages
        # passed, never that the check did not run.
        try:
            diags["legibility"] = [s.to_dict() for s in assess_pages(svgs)]
        except Exception as exc:  # noqa: BLE001 — advisory: never break a render
            diags["legibility"] = []
            diags["warnings"].append(f"legibility assessment failed: {exc}")
        return svgs, dict(renderer.tstats), diags
    return svgs, dict(renderer.tstats)


def render_html(
    model: Any,
    *,
    base_dir: str | None = None,
    real_metrics: bool | None = None,
) -> str:
    """Render a document to one self-contained HTML page.

    The in-process equivalent of ``ff-render <doc> --to html``: a validated model
    (or a plain document dict) in, the whole HTML file out as a string. Before
    this, HTML was the one shipped output with no SDK entry point, so an
    application holding a document in memory had to write it to disk and shell
    out to obtain it.

    The result is a complete document — ``<!DOCTYPE html>`` through ``</html>``
    — with the artwork as inline SVG, one hoisted stylesheet carrying the
    document's own palette (``:root`` custom properties) and named text styles
    (``.fg-ts-<name>``), a screen-reader landmark, and one ``<figure>`` per page.
    It needs no assets, no network and no optional dependency, so it can be
    written straight to a file or served as-is.

    Object-type coverage equals ``--to svg``: since the DRY/SOLID port the HTML
    target is painted by the same ``Renderer`` (see
    ``rendering/infrastructure/painters/html.py``), so tables, UML, connectors,
    dimensions and ``mode: flow`` documents all render rather than degrading to
    placeholders.

    ``real_metrics`` threads the renderer's glyph-advance text measurement
    exactly as ``render_pages_with_stats`` does: ``None`` (the default) consults
    ``FRAMEFORGE_REAL_METRICS``; an explicit bool always wins over the env var.

    Example::

        from frameforge_sdk import DocumentBuilder
        from frameforge.conform import render_html

        b = DocumentBuilder(title="Report")
        page = b.page("p1", size=(800, 600))
        page.text("h", box=(40, 40, 720, 40), text="Q3 results")
        open("report.html", "w").write(render_html(b.build()))
    """
    from frameforge.rendering.infrastructure.backends.html import (
        render_document as _render_html_document)
    data = validate_document(model).model_dump(by_alias=True, exclude_none=True)
    return _render_html_document(data, base_dir, real_metrics=real_metrics)


def overflow_report(
    model: Any,
    *,
    base_dir: str | None = None,
    real_metrics: bool | None = None,
) -> list[OverflowSignal]:
    """Render through the proxy and return the typed layout-overflow signals.

    Convenience over ``render_pages_with_stats(diagnostics=True)``: runs the
    measure/layout pass and lifts ``diagnostics["overflow"]`` back into
    :class:`OverflowSignal` values — every text object whose content provably
    exceeds its box (clipped, shrunk, or spilling ``visible``) and every
    flow-mode line the Knuth–Plass engine had to emit wider than its column.
    An empty list means the document lays out clean. ``real_metrics`` threads
    the renderer's glyph-advance measurement exactly as in
    :func:`render_pages_with_stats`.
    """
    _svgs, _tstats, diags = render_pages_with_stats(
        model, base_dir=base_dir, real_metrics=real_metrics, diagnostics=True)
    return [OverflowSignal.from_dict(d) for d in diags.get("overflow", [])]


def paint_report(
    model: Any,
    *,
    base_dir: str | None = None,
    real_metrics: bool | None = None,
) -> list[PaintSignal]:
    """Render through the proxy and return the typed PAINT-INTENT signals.

    The third member of the family: :func:`overflow_report` names what the
    layout could not fit and :func:`legibility_report` what it fitted and made
    unreadable — this one names ink the author asked for that the render did
    not produce:

      * ``inert-stroke-declaration`` — stroke intent written as
        ``style: {color, width, dash}`` (the pre-P3 bundle shape). Those keys
        validate as text colour / box width / an unrelated dash, so the authored
        appearance is discarded;
      * ``injected-stroke-default`` — the engine painted its own ``#000``/1px
        over that ignored declaration;
      * ``invisible-shape`` — the shape resolved to no fill and no stroke: it
        emits geometry and paints zero ink.

    An empty list means every shape painted what it declared. ``signal.remedy``
    carries the copy-pasteable P3 spelling, and
    ``tooling/codemod.py --fix-inert-stroke`` applies it across a document::

        >>> for s in paint_report(doc):
        ...     print(s.page, s.id, s.code, "->", s.remedy)
        p1 hairline inert-stroke-declaration -> stroke: '#d5d0c6' + stroke_style: {stroke_width: 1}
    """
    _svgs, _tstats, diags = render_pages_with_stats(
        model, base_dir=base_dir, real_metrics=real_metrics, diagnostics=True)
    return [PaintSignal.from_dict(d) for d in diags.get("paint", [])]


def legibility_report(
    model: Any,
    *,
    base_dir: str | None = None,
    real_metrics: bool | None = None,
    policy: LegibilityPolicy | None = None,
) -> list[LegibilitySignal]:
    """Render through the proxy and return the typed HUMAN-LEGIBILITY signals.

    The companion to :func:`overflow_report`: that one reports what the layout
    could not fit, this one reports what it fitted and made unreadable — type
    below the legible floor for the page, text failing WCAG 2.1 SC 1.4.3
    against the ink actually painted behind it, an untrackable measure, or
    leading too tight to separate the lines. An empty list means every check
    passed; an ``info``-level ``contrast-unverified`` signal means a backdrop
    could not be resolved and was deliberately NOT scored as a pass.

    ``policy`` overrides the default thresholds (house minimum type size, a
    stricter contrast target, a narrower measure); see
    :class:`~frameforge.rendering.domain.services.legibility.LegibilityPolicy`.
    """
    svgs, _tstats = render_pages_with_stats(
        model, base_dir=base_dir, real_metrics=real_metrics)
    return assess_pages(svgs, policy=policy)


def collision_report(
    model: Any,
    *,
    base_dir: str | None = None,
    real_metrics: bool | None = None,
) -> list[dict]:
    """Render through the proxy and return the same-layer ink COLLISIONS.

    A collision is an *unintended* same-layer overlap of drawn ink — two text
    objects whose glyphs intersect on the same layer without both declaring
    ``overlap: allowed`` (collision-gate/2026-07). Overlap is otherwise a
    first-class effect (watermarks, captions over images), so a consented or
    cross-layer overlap never appears here; an empty list means the page has no
    accidental text-on-text.

    Each record is ``{ids, page, layer, area, overlap: [dx, dy], metrics, boxes,
    texts}``. ``metrics`` is ``"estimate"`` or ``"real"`` — an estimate-mode
    verdict is unverified by default (PALS's Law); pass ``real_metrics=True`` (in
    the font-rich runtime) for a reproducible one.

    ``ids`` is ``[None, None]`` unless both objects were authored with an ``id``,
    so ``boxes`` (the two ink rectangles, ``[x0, y0, x1, y1]``) and ``texts`` (a
    bounded excerpt of each) are what make an id-less pair locatable — generated
    documents rarely carry ids, and a report that names neither is unactionable.

    Example — fail a build on unintended overlap::

        from frameforge.conform import collision_report
        hits = collision_report(doc)
        for c in hits:
            print(f"p{c['page']}: {c['texts'][0]!r} over {c['texts'][1]!r} "
                  f"({c['overlap'][0]}x{c['overlap'][1]} units)")
        assert not hits, f"{len(hits)} unintended text collision(s)"

    Overlap that IS the design (a watermark, a caption over an image) is declared
    with ``overlap: "allowed"`` on both objects and never appears here.
    """
    _svgs, _tstats, diags = render_pages_with_stats(
        model, base_dir=base_dir, real_metrics=real_metrics, diagnostics=True)
    return list(diags.get("collisions", []))


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
    "OverflowSignal",
    "assert_golden",
    "collision_report",
    "overflow_report",
    "page_hashes",
    "render_html",
    "render_page_svgs",
    "render_pages_with_stats",
    "write_golden",
]
