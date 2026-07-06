"""The validate-and-render pipeline shared by every document source.

Validation gates rendering; the pure-Python renderer runs in a bounded daemon
thread; page selection, provenance signing, PNG rasterization (with a raster
``scale``), and the optional PDF export lane (``to='pdf'``) follow.
"""
from __future__ import annotations

import importlib.util
import io
import os
import threading
import time
from pathlib import Path
from typing import Any

from framegraph.rendering.provenance import sign_svg, utc_now_iso
from framegraph.sdk.conform import render_pages_with_stats
from framegraph.sdk.io import parse
from framegraph.sdk.validate import validate_static_rules

from framegraph.mcp.config import (
    DEFAULT_RASTER_MAX_PAGES,
    DEFAULT_RASTER_TIMEOUT_SECONDS,
    DEFAULT_RENDER_MAX_OBJECTS,
    DEFAULT_RENDER_MAX_PAGES_HARD,
    DEFAULT_RENDER_TIMEOUT_SECONDS,
    _positive_env,
)
from framegraph.mcp.results import _render_failure, _resource_links, _validation_payload
from framegraph.mcp.util import _page_svg_name, _sha256_text


class RenderTimeoutError(RuntimeError):
    """Raised when in-process SVG rendering exceeds the soft time budget."""


def _validate_and_render_yaml(
    yaml_text: str,
    *,
    session_id: str,
    session_dir: Path,
    base_dir: Path,
    max_pages: int,
    raster_png: bool,
    pages: str | list[int] | None = None,
    sign: bool = False,
    signed_at: str | None = None,
    silhouette: bool = False,
    to: str = "png",
    scale: float = 1.0,
    real_metrics: bool | str = "auto",
) -> dict[str, Any]:
    if to not in ("png", "pdf"):
        return {
            "ok": False,
            "error": f"unknown export target to={to!r}",
            "hint": "use to='png' (default; the raster feedback loop) or to='pdf' "
                    "(additionally assemble the rendered pages into document.pdf)",
            "validation": {"ok": False, "issues": []},
            "renders": [],
            "resources": _resource_links(session_id, renders=[]),
        }
    metrics_on = _resolve_real_metrics(real_metrics)
    try:
        document = parse(yaml_text, forgiving=False)
        if silhouette:
            # The silhouette gate (framegraph.coach): flatten to black-on-white so
            # construction readability is judged BEFORE detail. Reuses this whole
            # render path; the judgement itself is the caller's (advisory).
            from framegraph.coach import to_silhouette
            document = to_silhouette(document)
        report = validate_static_rules(document)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"FrameGraph YAML validation failed: {exc}",
            "validation": {"ok": False, "issues": [{"severity": "error", "message": str(exc)}]},
            "renders": [],
            "resources": _resource_links(session_id, renders=[]),
        }

    renders: list[dict[str, Any]] = []
    render_warning: str | None = None
    text_fit: dict[str, int] | None = None
    render_diagnostics: dict[str, Any] | None = None
    pdf_summary: dict[str, Any] | None = None
    if report.ok:
        oversized = _render_size_guard(document)
        if oversized:
            return _render_failure(session_id, report, oversized, warning=oversized)
        try:
            svgs, text_stats, render_diagnostics = _render_page_svgs_bounded(
                document, base_dir, real_metrics=metrics_on)
        except RenderTimeoutError as exc:
            return _render_failure(session_id, report, str(exc), warning=str(exc))
        except Exception as exc:  # noqa: BLE001 — render is third-party-ish; surface it structured
            return _render_failure(session_id, report, f"FrameGraph render failed: {exc}")

        try:
            selected = _select_pages(pages, max_pages, len(svgs))
        except ValueError as exc:
            return _render_failure(session_id, report, f"invalid 'pages' selector: {exc}")

        # One sign timestamp per run so every page shares it (mirrors
        # tooling/render_fixtures.py): render-time when `sign` is on and no
        # explicit `signed_at` is given; an empty `signed_at` means
        # fingerprint-only (deterministic, no timestamp).
        sign_ts = (signed_at if signed_at is not None else utc_now_iso()) if sign else None
        for page_no in selected:
            svg = svgs[page_no - 1]
            if sign:
                svg = sign_svg(svg, timestamp=sign_ts or None)
            path = session_dir / _page_svg_name(page_no)
            path.write_text(svg, encoding="utf-8")
            renders.append(
                {
                    "page": page_no,
                    "path": str(path),
                    "uri": f"framegraph://session/{session_id}/page/{page_no}.svg",
                    "mimeType": "image/svg+xml",
                    "sha256": _sha256_text(svg),
                    "bytes": len(svg.encode("utf-8")),
                }
            )
        if pages is not None and not selected:
            render_warning = (
                f"no pages matched the 'pages' selector {pages!r}; the document has "
                f"{len(svgs)} page(s)"
            )
        if raster_png and renders:
            pngs, raster_warning = _try_rasterize_pngs(
                [(item["page"], Path(item["path"])) for item in renders],
                session_dir,
                session_id,
                scale=scale,
            )
            renders.extend(pngs)
            if raster_warning:
                render_warning = raster_warning

        if to == "pdf" and renders:
            svg_pages = [
                (item["page"], Path(item["path"]))
                for item in renders
                if item["mimeType"] == "image/svg+xml"
            ]
            pdf_entry, pdf_summary, pdf_warning = _export_pdf(
                svg_pages, session_dir, session_id, base_dir
            )
            if pdf_entry:
                renders.append(pdf_entry)
            if pdf_warning:
                render_warning = f"{render_warning}; {pdf_warning}" if render_warning else pdf_warning

        # Surface the renderer's text-fit telemetry. A non-zero `clipped` means text
        # exceeded its box and was clipped/ellipsized — the render returns ok:true, so
        # without this the truncation is invisible to the author (PALS's Law: make the
        # render's own signal visible). Advisory, not an error: some clips are the
        # author's intent (text_overflow: ellipsis / line_clamp).
        text_fit = {
            k: int(text_stats.get(k, 0))
            for k in ("total", "wrapped", "shrunk", "clipped", "contained")
        }
        if text_fit["clipped"]:
            # Name the losses (issue #44): the per-object records ride on
            # result["diagnostics"]["truncations"]; the warning quotes the
            # first silent ids so an authoring agent cannot miss them.
            records = (render_diagnostics or {}).get("truncations") or []
            silent = [r for r in records if not r.get("acknowledged")]
            named = ", ".join(f"#{r.get('id') or '<anonymous>'} (p[{r.get('page')}])"
                              for r in silent[:3])
            more = f" and {len(silent) - 3} more" if len(silent) > 3 else ""
            note = (
                f"{text_fit['clipped']} text object(s) were clipped to their box"
                + (f" — {len(silent)} SILENTLY, losing content: {named}{more}; "
                   "see diagnostics.truncations" if silent
                   else " (all explicitly authored via overflow/ellipsis/max_lines)")
            )
            render_warning = f"{render_warning}; {note}" if render_warning else note

    result = {
        "ok": report.ok and bool(renders),
        "validation": _validation_payload(report),
        "renders": renders,
        "resources": _resource_links(session_id, renders=renders),
        "real_metrics": metrics_on,
    }
    if text_fit is not None:
        result["text_fit"] = text_fit
    if render_diagnostics is not None:
        # The renderer's structured feedback (warnings, skipped objects/flowables,
        # font fallbacks, opt-in layout report): surfaced on the result and — via
        # `_write_diagnostics` — persisted into the session's diagnostics.json, so
        # a silent render-side degradation is observable by the caller.
        result["diagnostics"] = render_diagnostics
    if pdf_summary is not None:
        result["pdf"] = pdf_summary
    if sign and renders:
        # Record the provenance stamp applied to every rendered SVG so the caller
        # can confirm the artifacts are signed (and with which timestamp).
        result["signed"] = {"applied": True, "timestamp": (sign_ts or None)}
    if silhouette:
        from framegraph.coach import stage_rubric
        result["silhouette"] = {"applied": True, "rubric": stage_rubric("silhouette")}
    if render_warning:
        result["render_warning"] = render_warning
    if not result["ok"] and "error" not in result:
        # ok:false must always carry an actionable `error` — a warning-only failure
        # (e.g. a pages selector that matched nothing, or static validation issues)
        # left the caller with nothing machine-readable to act on.
        if not report.ok:
            issue_count = len(result["validation"]["issues"])
            result["error"] = (
                f"FrameGraph validation failed with {issue_count} issue(s) — see validation.issues"
            )
            result["hint"] = (
                "each entry in validation.issues carries rule_id, path (a JSON pointer into the "
                "document), and message; describe_capabilities(topic=<type>) shows the expected fields"
            )
        else:
            result["error"] = render_warning or "render produced no pages"
    return result


def _resolve_real_metrics(value: bool | str | None) -> bool:
    """Resolve the ``real_metrics`` tri-state: True/False, or 'auto'.

    'auto' first honors the renderer's own ``FRAMEGRAPH_REAL_METRICS`` env
    override (an operator forcing the byte-stable estimator, e.g. for golden
    reproduction, must not be silently overridden by MCP), then falls back to
    "on when fontTools is importable". Real metrics measure text with real
    glyph advances (fontTools + the fontconfig-resolved face) instead of the
    per-character estimate, so wrap/shrink/ellipsis decisions match the
    rendered pixels. An explicit bool from the caller always wins.
    """
    if isinstance(value, bool):
        return value
    text = str(value if value is not None else "auto").strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    env = os.environ.get("FRAMEGRAPH_REAL_METRICS", "").strip().lower()
    if env:  # mirror the Renderer's own parsing: any set value decides
        return env in ("1", "true", "yes", "on")
    return importlib.util.find_spec("fontTools") is not None


def _export_pdf(
    pages_and_svgs: list[tuple[int, Path]], session_dir: Path, session_id: str, base_dir: Path
) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    """Assemble the rendered page SVGs into one vector ``document.pdf``.

    Reuses the CLI's ``--to pdf`` mechanism (see ``framegraph/cli.py`` ``r_pdf``):
    CairoSVG lowers each page SVG to PDF bytes and pypdf concatenates them.
    Returns ``(render_entry, pdf_summary, warning)`` — on missing dependencies or
    total failure the entry is ``None`` and the summary carries ``ok: false``
    plus an install hint, so the SVG/PNG render stays usable.
    """
    try:
        import cairosvg
        from pypdf import PdfWriter
    except ImportError as exc:
        summary = {
            "ok": False,
            "error": f"PDF export unavailable: {exc}",
            "hint": "install the `pdfout` dependency group (uv sync --group pdfout) for CairoSVG + pypdf",
        }
        return None, summary, str(summary["error"])
    writer = PdfWriter()
    appended = 0
    skipped: list[str] = []
    url_base = os.path.join(str(base_dir), "")
    for page_no, svg_path in pages_and_svgs:
        try:
            pdf_bytes = cairosvg.svg2pdf(
                bytestring=svg_path.read_text(encoding="utf-8").encode("utf-8"),
                url=url_base,
                unsafe=True,
            )
            writer.append(io.BytesIO(pdf_bytes))
            appended += 1
        except Exception as exc:  # noqa: BLE001 — one bad page must not kill the document
            skipped.append(f"page {page_no}: {exc}")
    if not appended:
        writer.close()
        summary = {
            "ok": False,
            "error": "PDF export produced no pages: " + "; ".join(skipped),
            "hint": "check the per-page errors; the SVG renders remain available as resources",
        }
        return None, summary, str(summary["error"])
    out_path = session_dir / "document.pdf"
    with out_path.open("wb") as fh:
        writer.write(fh)
    writer.close()
    entry = {
        "kind": "pdf",
        "path": str(out_path),
        "uri": f"framegraph://session/{session_id}/document.pdf",
        "mimeType": "application/pdf",
        "bytes": out_path.stat().st_size,
    }
    summary = {
        "ok": True,
        "path": entry["path"],
        "uri": entry["uri"],
        "bytes": entry["bytes"],
        "pages": appended,
    }
    warning = None
    if skipped:
        summary["skipped_pages"] = skipped
        warning = f"PDF export skipped {len(skipped)} page(s): " + "; ".join(skipped)
    return entry, summary, warning


def _render_page_svgs_bounded(
    document: Any, base_dir: Path, *, real_metrics: bool = False
) -> tuple[list[str], dict[str, int], dict[str, Any]]:
    """Render page SVGs (+ telemetry) under :data:`DEFAULT_RENDER_TIMEOUT_SECONDS`.

    Runs the pure-Python renderer in a daemon thread and joins with a timeout so a
    pathological document bounds the *response* latency. The work itself is not
    force-killed (Python cannot interrupt CPU-bound bytecode); a timed-out render
    keeps running detached until it completes, then is discarded. Returns the page
    SVGs, the renderer's ``tstats`` (so the caller can surface clipped/wrapped
    text), and the renderer's structured ``diagnostics`` feedback.
    """
    timeout = _render_timeout()
    box: dict[str, Any] = {}

    def _target() -> None:
        try:
            box["value"] = _render_pages_with_stats(document, base_dir, real_metrics=real_metrics)
        except BaseException as exc:  # noqa: BLE001 — re-raised on the calling thread
            box["error"] = exc

    worker = threading.Thread(target=_target, name="framegraph-render", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise RenderTimeoutError(
            f"FrameGraph render exceeded {timeout:g}s (FRAMEGRAPH_MCP_RENDER_TIMEOUT)"
        )
    if "error" in box:
        raise box["error"]
    return box.get("value", ([], {}, {}))


def _render_pages_with_stats(
    document: Any, base_dir: Path, *, real_metrics: bool
) -> tuple[list[str], dict[str, int], dict[str, Any]]:
    """Render page SVGs + telemetry through the SDK conformance path.

    ``framegraph.sdk.conform.render_pages_with_stats`` now threads the renderer's
    ``real_metrics`` flag and returns its structured ``diagnostics``, so the MCP
    pipeline no longer replicates the render loop. ``real_metrics`` arrives here
    already resolved to a bool by :func:`_resolve_real_metrics` (tool argument >
    'auto' fontTools probe) and an explicit bool always beats the renderer's
    ``FRAMEGRAPH_REAL_METRICS`` env fallback, so the env var cannot override the
    tool argument.
    """
    return render_pages_with_stats(
        document, base_dir=str(base_dir), real_metrics=real_metrics, diagnostics=True)


def _render_timeout() -> float:
    raw = os.environ.get("FRAMEGRAPH_MCP_RENDER_TIMEOUT")
    if raw:
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return float(DEFAULT_RENDER_TIMEOUT_SECONDS)


def _count_objects(node: Any) -> int:
    """Count object-like nodes (anything with a ``type``) anywhere in the tree."""
    if isinstance(node, dict):
        total = 1 if "type" in node else 0
        return total + sum(_count_objects(v) for v in node.values())
    if isinstance(node, list):
        return sum(_count_objects(v) for v in node)
    return 0


def _render_size_guard(document: Any) -> str | None:
    """Refuse an obviously-runaway document before the in-process render thread starts.

    Bounds the work the (un-killable) render daemon thread can do. Best-effort: any
    failure to introspect the document falls through to a normal render rather than
    blocking it.
    """
    try:
        data = (
            document.model_dump(by_alias=True, exclude_none=True)
            if hasattr(document, "model_dump")
            else dict(document)
        )
    except Exception:  # noqa: BLE001 — never let the guard itself block a valid render
        return None
    pages = data.get("pages")
    n_pages = len(pages) if isinstance(pages, list) else 0
    n_objects = _count_objects(pages)
    max_pages = _positive_env("FRAMEGRAPH_MCP_RENDER_MAX_PAGES", DEFAULT_RENDER_MAX_PAGES_HARD)
    max_objects = _positive_env("FRAMEGRAPH_MCP_RENDER_MAX_OBJECTS", DEFAULT_RENDER_MAX_OBJECTS)
    if n_pages > max_pages or n_objects > max_objects:
        return (
            f"document too large to render in-process ({n_pages} pages, {n_objects} "
            f"objects; caps {max_pages} pages / {max_objects} objects — override with "
            "FRAMEGRAPH_MCP_RENDER_MAX_PAGES / FRAMEGRAPH_MCP_RENDER_MAX_OBJECTS)"
        )
    return None


def _raster_timeout() -> float:
    """Soft wall-clock budget for the whole rasterization loop (env-overridable)."""
    raw = os.environ.get("FRAMEGRAPH_MCP_RASTER_TIMEOUT")
    if raw:
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return float(DEFAULT_RASTER_TIMEOUT_SECONDS)


def _raster_max_pages() -> int:
    """Cap on how many pages a single render call rasterizes to PNG (env-overridable)."""
    raw = os.environ.get("FRAMEGRAPH_MCP_RASTER_MAX_PAGES")
    if raw:
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return DEFAULT_RASTER_MAX_PAGES


def _parse_page_selector(pages: str | list[int] | tuple[int, ...]) -> set[int]:
    """Parse a ``pages`` selector into a set of 1-based page numbers.

    Accepts a list/tuple of ints, or a string of comma-separated singletons and
    ``lo-hi`` ranges, e.g. ``"6-10,15"``. Raises ``ValueError`` on a malformed
    token or a non-positive / descending range.
    """
    if isinstance(pages, (list, tuple)):
        out: set[int] = set()
        for value in pages:
            number = int(value)
            if number < 1:
                raise ValueError(f"page numbers are 1-based; got {number}")
            out.add(number)
        return out
    if isinstance(pages, str):
        out = set()
        for token in pages.replace(" ", "").split(","):
            if not token:
                continue
            if "-" in token:
                lo_text, hi_text = token.split("-", 1)
                lo, hi = int(lo_text), int(hi_text)
                if lo < 1 or hi < lo:
                    raise ValueError(f"invalid page range {token!r}")
                out.update(range(lo, hi + 1))
            else:
                number = int(token)
                if number < 1:
                    raise ValueError(f"page numbers are 1-based; got {number}")
                out.add(number)
        return out
    raise ValueError("pages must be a list of ints or a string like '6-10,15'")


def _select_pages(pages: str | list[int] | None, max_pages: int, total: int) -> list[int]:
    """Resolve the 1-based page numbers to render.

    ``pages`` (when given) selects exactly those in-range pages and overrides
    ``max_pages``; otherwise ``max_pages`` keeps its prefix semantics
    (``<= 0`` means all pages).
    """
    if total <= 0:
        return []
    if pages is not None:
        wanted = _parse_page_selector(pages)
        return sorted(p for p in wanted if 1 <= p <= total)
    limit = int(max_pages)
    if limit <= 0:
        return list(range(1, total + 1))
    return list(range(1, min(limit, total) + 1))


class _RasterBackendUnavailable(RuntimeError):
    """No raster backend could produce a PNG (Chromium and CairoSVG both absent)."""


def _raster_chromium(svg: str, out_path: Path, base_dir: Path, scale: float) -> None:
    """Rasterize via headless Chromium; mark the backend absent if it cannot run."""
    try:
        from framegraph.rendering.infrastructure.browser import (
            BrowserRendererUnavailable,
            rasterize_svg,
        )
    except ImportError as exc:
        raise _BackendAbsent(f"Headless Chromium: {exc}") from exc
    try:
        rasterize_svg(svg, out_path, base_dir=str(base_dir), scale=scale)
    except BrowserRendererUnavailable as exc:
        raise _BackendAbsent(f"Headless Chromium: {exc}") from exc


def _raster_cairo(svg: str, out_path: Path, base_dir: Path, scale: float) -> None:
    """Rasterize via CairoSVG (browser-free fallback); mark absent if unavailable."""
    try:
        from framegraph.rendering.infrastructure.cairo import (
            CairoRendererUnavailable,
            rasterize_svg_cairo,
        )
    except ImportError as exc:
        raise _BackendAbsent(f"CairoSVG: {exc}") from exc
    try:
        rasterize_svg_cairo(svg, out_path, base_dir=str(base_dir), scale=scale)
    except CairoRendererUnavailable as exc:
        raise _BackendAbsent(f"CairoSVG: {exc}") from exc


class _BackendAbsent(RuntimeError):
    """One raster backend is unavailable; try the next."""


_RASTER_BACKENDS = {"chromium": _raster_chromium, "cairo": _raster_cairo}
_RASTER_ORDER = ("chromium", "cairo")


def _rasterize_one(
    svg: str, out_path: Path, base_dir: Path, *, prefer: str | None, scale: float = 1.0
) -> str:
    """Rasterize one SVG, trying Chromium then CairoSVG. Return the backend used.

    ``prefer`` (a backend known to work this run) is tried first so a successful
    backend is not re-probed per page. Raises :class:`_RasterBackendUnavailable`
    with both backends' reasons when neither can run.
    """
    order = list(_RASTER_ORDER)
    if prefer in _RASTER_BACKENDS:
        order = [prefer] + [name for name in order if name != prefer]
    reasons: list[str] = []
    for name in order:
        try:
            _RASTER_BACKENDS[name](svg, out_path, base_dir, scale)
            return name
        except _BackendAbsent as exc:
            reasons.append(str(exc))
    raise _RasterBackendUnavailable(
        "PNG rasterization unavailable (" + " / ".join(reasons) + "). The model cannot see "
        "SVG, so this render was not visually verified — install the `browser` group and run "
        "`uv run playwright install chromium`, or the `mcp`/`pdfout` group for the CairoSVG "
        "fallback."
    )


def _try_rasterize_pngs(
    pages_and_svgs: list[tuple[int, Path]],
    session_dir: Path,
    session_id: str,
    *,
    scale: float = 1.0,
) -> tuple[list[dict[str, Any]], str | None]:
    """Rasterize selected page SVGs to PNG, bounded by a page cap and a soft time budget.

    Tries headless Chromium first and falls back to CairoSVG (browser-free) so a
    vision model can still *see* — and verify — a render without a browser.
    ``pages_and_svgs`` pairs each TRUE 1-based page number with its SVG file. Returns
    ``(renders, warning)``. A non-``None`` warning means either no viewable raster was
    produced (no backend available — the warning names both) or the lane was truncated
    by the cap/budget (the rasterized pages render; the rest keep their SVG resource
    link). PNGs carry the true page number in both the filename (``pNNN.png``) and the
    resource URI, so a selected subset stays addressable.
    """
    total = len(pages_and_svgs)
    cap = _raster_max_pages()
    budget = _raster_timeout()
    deadline = time.monotonic() + budget
    renders: list[dict[str, Any]] = []
    truncated = 0
    backend: str | None = None
    for index, (page_no, svg_path) in enumerate(pages_and_svgs):
        if index >= cap or time.monotonic() > deadline:
            truncated = total - index
            break
        out_path = session_dir / f"p{page_no:03d}.png"
        try:
            backend = _rasterize_one(
                svg_path.read_text(encoding="utf-8"),
                out_path,
                session_dir,
                prefer=backend,
                scale=scale,
            )
        except _RasterBackendUnavailable as exc:
            if not renders:
                return [], str(exc)
            truncated = total - index
            break
        renders.append(
            {
                "page": page_no,
                "path": str(out_path),
                "uri": f"framegraph://session/{session_id}/page/{page_no}.png",
                "mimeType": "image/png",
                "bytes": out_path.stat().st_size,
                "backend": backend,
            }
        )
    warning = None
    if truncated:
        warning = (
            f"rasterized {len(renders)} of {total} selected page(s) (raster cap {cap}, "
            f"budget {budget:g}s); the remaining {truncated} keep their SVG resource link — "
            "raise FRAMEGRAPH_MCP_RASTER_MAX_PAGES / FRAMEGRAPH_MCP_RASTER_TIMEOUT or select "
            "fewer pages."
        )
    return renders, warning
