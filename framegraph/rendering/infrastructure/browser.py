"""Headless browser rasterization for FrameGraph page SVGs.

This adapter deliberately sits after the existing SVG renderer: FrameGraph is
still solved into ordinary SVG, then Chromium handles browser-native paint
semantics such as CSS filters, blend modes, backdrop filters and masks when a
PNG is needed.
"""
from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
from typing import Iterable, Sequence


# Chromium's setuid sandbox usually cannot initialize inside a container (no
# user namespaces / running as root), so ``launch()`` fails there unless
# ``--no-sandbox`` is passed. Local runs must be unchanged, so the flags are
# opt-in via environment: ``FRAMEGRAPH_CHROMIUM_NO_SANDBOX=1`` adds the two
# container-safe flags below (the Docker image sets it), or pass an explicit
# space-separated ``FRAMEGRAPH_CHROMIUM_ARGS`` to override entirely.
_CONTAINER_CHROMIUM_ARGS = ("--no-sandbox", "--disable-dev-shm-usage")
_TRUTHY = {"1", "true", "yes", "on"}


_SVG_OPEN_RE = re.compile(r"<svg\b(?P<attrs>[^>]*)>", re.IGNORECASE)
_ATTR_RE = re.compile(r"""\b(?P<name>width|height)=["'](?P<value>[^"']+)["']""", re.IGNORECASE)
_VIEWBOX_RE = re.compile(
    r"""\bviewBox=["'][\s,]*(?P<x>-?\d+(?:\.\d+)?)[\s,]+(?P<y>-?\d+(?:\.\d+)?)[\s,]+"""
    r"""(?P<w>\d+(?:\.\d+)?)[\s,]+(?P<h>\d+(?:\.\d+)?)[\s,]*["']""",
    re.IGNORECASE,
)


class BrowserRendererUnavailable(RuntimeError):
    """Raised when the optional Playwright/Chromium renderer is unavailable."""


def svg_size(svg: str) -> tuple[int, int]:
    """Return the root SVG's pixel size, falling back to viewBox dimensions."""
    match = _SVG_OPEN_RE.search(svg)
    if not match:
        raise ValueError("SVG document has no root <svg> element")
    attrs = match.group("attrs")
    found = {m.group("name").lower(): _css_px(m.group("value")) for m in _ATTR_RE.finditer(attrs)}
    if found.get("width") and found.get("height"):
        return max(1, round(found["width"])), max(1, round(found["height"]))
    vb = _VIEWBOX_RE.search(attrs)
    if vb:
        return max(1, round(float(vb.group("w")))), max(1, round(float(vb.group("h"))))
    raise ValueError("SVG root needs width/height or viewBox")


def rasterize_svg(
    svg: str,
    out_path: str | Path,
    *,
    base_dir: str | Path | None = None,
    scale: float = 1.0,
    playwright_module=None,
) -> Path:
    """Rasterize one SVG string to PNG with headless Chromium."""
    if _in_running_event_loop():
        return _rasterize_svg_in_worker(
            svg,
            out_path,
            base_dir=base_dir,
            scale=scale,
            playwright_module=playwright_module,
        )
    return _rasterize_svg_sync(
        svg,
        out_path,
        base_dir=base_dir,
        scale=scale,
        playwright_module=playwright_module,
    )


def _rasterize_svg_sync(
    svg: str,
    out_path: str | Path,
    *,
    base_dir: str | Path | None = None,
    scale: float = 1.0,
    playwright_module=None,
) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = svg_size(svg)
    html = _html(svg, base_dir=base_dir)
    browser_mod = playwright_module or _load_playwright()
    with browser_mod.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(args=_chromium_launch_args())
        except Exception as exc:  # pragma: no cover - depends on local browser install state
            raise BrowserRendererUnavailable(
                "Headless Chromium could not launch. Run `uv run playwright install chromium` "
                "after installing the optional browser dependency group."
            ) from exc
        try:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=max(0.1, float(scale)),
            )
            page.set_content(html, wait_until="networkidle")
            page.screenshot(path=str(out), type="png", full_page=False)
        finally:
            browser.close()
    return out


def _rasterize_svg_in_worker(
    svg: str,
    out_path: str | Path,
    *,
    base_dir: str | Path | None,
    scale: float,
    playwright_module=None,
) -> Path:
    # Playwright's sync API refuses to run in a thread that already owns an
    # asyncio loop. MCP tools are often invoked from such a loop, so isolate the
    # browser work in a short-lived worker thread while preserving this sync API.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _rasterize_svg_sync,
            svg,
            out_path,
            base_dir=base_dir,
            scale=scale,
            playwright_module=playwright_module,
        )
        return future.result()


def rasterize_svgs(
    svgs: Sequence[str] | Iterable[str],
    out_dir: str | Path,
    *,
    base_dir: str | Path | None = None,
    prefix: str = "p",
    scale: float = 1.0,
    playwright_module=None,
) -> list[Path]:
    """Rasterize page SVGs to ``out_dir/p001.png``, ``p002.png`` and so on."""
    out = Path(out_dir)
    paths = []
    for index, svg in enumerate(svgs, 1):
        paths.append(
            rasterize_svg(
                svg,
                out / f"{prefix}{index:03d}.png",
                base_dir=base_dir,
                scale=scale,
                playwright_module=playwright_module,
            )
        )
    return paths


def _chromium_launch_args() -> list[str]:
    """Return the Chromium launch flags, opt-in via environment.

    Empty by default so local (non-container) runs behave exactly as before.
    ``FRAMEGRAPH_CHROMIUM_ARGS`` (space-separated) takes precedence and replaces
    the flags entirely; otherwise a truthy ``FRAMEGRAPH_CHROMIUM_NO_SANDBOX``
    yields the container-safe defaults.
    """
    explicit = os.environ.get("FRAMEGRAPH_CHROMIUM_ARGS", "").strip()
    if explicit:
        return explicit.split()
    if os.environ.get("FRAMEGRAPH_CHROMIUM_NO_SANDBOX", "").strip().lower() in _TRUTHY:
        return list(_CONTAINER_CHROMIUM_ARGS)
    return []


def _load_playwright():
    try:
        from playwright import sync_api
    except Exception as exc:  # pragma: no cover - exact import error is environment-specific
        raise BrowserRendererUnavailable(
            "Headless Chromium rendering needs the optional browser dependency group: "
            "`uv sync --group browser`, then `uv run playwright install chromium`."
        ) from exc
    return sync_api


def _in_running_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _html(svg: str, *, base_dir: str | Path | None) -> str:
    base = ""
    if base_dir is not None:
        uri = Path(base_dir).resolve().as_uri().rstrip("/") + "/"
        base = f'<base href="{_esc(uri)}">'
    return (
        "<!doctype html><meta charset=\"utf-8\">"
        f"{base}<style>html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:white}}"
        "svg{display:block}</style>"
        f"{svg}"
    )


def _css_px(value: str) -> float:
    raw = value.strip()
    match = re.match(r"^-?\d+(?:\.\d+)?", raw)
    if not match:
        raise ValueError(f"unsupported SVG length: {value!r}")
    number = float(match.group(0))
    unit = raw[match.end():].strip().lower()
    if unit in ("", "px"):
        return number
    if unit == "pt":
        return number * 96.0 / 72.0
    if unit == "in":
        return number * 96.0
    if unit == "cm":
        return number * 96.0 / 2.54
    if unit == "mm":
        return number * 96.0 / 25.4
    raise ValueError(f"unsupported SVG length unit: {value!r}")


def _esc(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


__all__ = [
    "BrowserRendererUnavailable",
    "rasterize_svg",
    "rasterize_svgs",
    "svg_size",
]
