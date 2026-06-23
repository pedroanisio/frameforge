"""Headless browser rasterization for FrameGraph page SVGs.

This adapter deliberately sits after the existing SVG renderer: FrameGraph is
still solved into ordinary SVG, then Chromium handles browser-native paint
semantics such as CSS filters, blend modes, backdrop filters and masks when a
PNG is needed.
"""
from __future__ import annotations

import base64
from pathlib import Path
import re
from typing import Iterable, Sequence


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
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = svg_size(svg)
    html = _html(svg, base_dir=base_dir)
    browser_mod = playwright_module or _load_playwright()
    with browser_mod.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
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


def _load_playwright():
    try:
        from playwright import sync_api
    except Exception as exc:  # pragma: no cover - exact import error is environment-specific
        raise BrowserRendererUnavailable(
            "Headless Chromium rendering needs the optional browser dependency group: "
            "`uv sync --group browser`, then `uv run playwright install chromium`."
        ) from exc
    return sync_api


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
