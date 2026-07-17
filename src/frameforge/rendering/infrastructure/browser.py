"""Headless browser rasterization for FrameForge page SVGs.

This adapter deliberately sits after the existing SVG renderer: FrameForge is
still solved into ordinary SVG, then Chromium handles browser-native paint
semantics such as CSS filters, blend modes, backdrop filters and masks when a
PNG is needed.
"""
from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
import math
import os
from pathlib import Path
import re
import struct
from typing import Iterable, Sequence
import zlib


# Chromium's setuid sandbox usually cannot initialize inside a container (no
# user namespaces / running as root), so ``launch()`` fails there unless
# ``--no-sandbox`` is passed. Local runs must be unchanged, so the flags are
# opt-in via environment: ``FRAMEFORGE_CHROMIUM_NO_SANDBOX=1`` adds the two
# container-safe flags below (the Docker image sets it), or pass an explicit
# space-separated ``FRAMEFORGE_CHROMIUM_ARGS`` to override entirely.
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


def svg_size_px(svg: str) -> tuple[float, float]:
    """Return the root SVG's CSS-pixel size UNROUNDED, falling back to viewBox.

    Fractional canvases (pt/mm-derived page sizes such as A5 = 419.5×595.3)
    must keep their fractional extent until the device scale is applied —
    rounding here is what cropped/padded their rasters (DIM-5/NUMFMT-3)."""
    match = _SVG_OPEN_RE.search(svg)
    if not match:
        raise ValueError("SVG document has no root <svg> element")
    attrs = match.group("attrs")
    found = {m.group("name").lower(): _css_px(m.group("value")) for m in _ATTR_RE.finditer(attrs)}
    if found.get("width") and found.get("height"):
        return found["width"], found["height"]
    vb = _VIEWBOX_RE.search(attrs)
    if vb:
        return float(vb.group("w")), float(vb.group("h"))
    raise ValueError("SVG root needs width/height or viewBox")


def svg_size(svg: str) -> tuple[int, int]:
    """Return the root SVG's pixel size rounded to ints (legacy callers)."""
    width, height = svg_size_px(svg)
    return max(1, round(width)), max(1, round(height))


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
    width, height = svg_size_px(svg)
    scale = max(0.1, float(scale))
    # Never round the page before the device scale is applied (DIM-5): the
    # viewport CEILS so the whole canvas stays paintable, then a fractional
    # canvas raster is cropped to the exact device-pixel target
    # round(size*scale) — no clipped content, no background stripe. (A
    # screenshot `clip` cannot do this: Chromium snaps fractional clip rects
    # to whole CSS px, so odd device-pixel targets are unreachable.) Integer
    # canvases keep the legacy screenshot bytes untouched.
    viewport_w, viewport_h = max(1, math.ceil(width)), max(1, math.ceil(height))
    fractional = (viewport_w, viewport_h) != (width, height)
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
                viewport={"width": viewport_w, "height": viewport_h},
                device_scale_factor=scale,
            )
            page.set_content(html, wait_until="networkidle")
            page.screenshot(path=str(out), type="png", full_page=False)
        finally:
            browser.close()
    if fractional:
        _fit_png_file(out, max(1, round(width * scale)), max(1, round(height * scale)))
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
    ``FRAMEFORGE_CHROMIUM_ARGS`` (space-separated) takes precedence and replaces
    the flags entirely; otherwise a truthy ``FRAMEFORGE_CHROMIUM_NO_SANDBOX``
    yields the container-safe defaults.
    """
    explicit = os.environ.get("FRAMEFORGE_CHROMIUM_ARGS", "").strip()
    if explicit:
        return explicit.split()
    if os.environ.get("FRAMEFORGE_CHROMIUM_NO_SANDBOX", "").strip().lower() in _TRUTHY:
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


def _fit_png_file(path: Path, target_w: int, target_h: int) -> None:
    """Force a non-interlaced 8-bit PNG in place to EXACTLY ``target_w x
    target_h`` (top-left anchored).

    Over-render is CROPPED by truncating scanlines: PNG filters 0-4 are
    byte-wise and reference only bytes at or before the same offset, so dropping
    trailing bytes/rows keeps kept pixels bit-identical without unfiltering (the
    fast path, byte-for-byte the old behaviour). When a browser UNDER-renders a
    fractional canvas by a sub-pixel, the raster is unfiltered and the missing
    edge row/column is filled by clamping the last real pixel (edge extend,
    never the background) so the device-pixel target is exact AND stripe-free
    regardless of the engine's rounding (DIM-5) — the previous code raised here,
    which made real-Chromium fractional rasters flaky. stdlib-only: this module
    ships in the ``browser`` group, which does not carry Pillow."""
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG file: {path}")
    chunks = []
    pos = 8
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        chunks.append((kind, data[pos + 8:pos + 8 + length]))
        pos += 12 + length
        if kind == b"IEND":
            break
    ihdr = next(body for kind, body in chunks if kind == b"IHDR")
    w, h, depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", ihdr)
    if (w, h) == (target_w, target_h):
        return
    if depth != 8 or interlace != 0:
        raise ValueError("PNG fit supports non-interlaced 8-bit images only")
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    raw = zlib.decompress(b"".join(body for kind, body in chunks if kind == b"IDAT"))
    if target_w <= w and target_h <= h:
        # fast crop — truncate trailing bytes/rows, no unfiltering (unchanged)
        stride, kept = 1 + w * bpp, 1 + target_w * bpp
        fitted = b"".join(raw[y * stride:y * stride + kept] for y in range(target_h))
    else:
        # under-render on some axis: unfilter, edge-clamp to the target, re-emit
        # with filter 0 so the extended pixels are exact.
        rows = _png_unfilter(raw, w, h, bpp)
        rows = rows[:target_h] + [rows[-1]] * max(0, target_h - h)
        out_rows = []
        for r in rows:
            if target_w <= w:
                out_rows.append(r[:target_w * bpp])
            else:
                edge = r[(w - 1) * bpp:w * bpp]
                out_rows.append(r + edge * (target_w - w))
        fitted = b"".join(b"\x00" + r for r in out_rows)     # filter 0 per scanline
    out = [b"\x89PNG\r\n\x1a\n"]
    for kind, body in chunks:
        if kind == b"IDAT":
            continue                     # replaced by the single fitted IDAT
        if kind == b"IHDR":
            body = struct.pack(">IIBBBBB", target_w, target_h,
                               depth, color_type, comp, filt, interlace)
        if kind == b"IEND":
            _png_chunk(out, b"IDAT", zlib.compress(fitted, 6))
        _png_chunk(out, kind, body)
    Path(path).write_bytes(b"".join(out))


def _png_unfilter(raw: bytes, w: int, h: int, bpp: int) -> list:
    """Reverse PNG scanline filters (types 0-4) → a list of ``h`` unfiltered
    rows of ``w*bpp`` bytes each. 8-bit, non-interlaced."""
    stride = w * bpp
    rows, prev, pos = [], bytearray(stride), 0
    for _ in range(h):
        ftype = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if ftype == 1:                                   # Sub
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:                                 # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:                                 # Average
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:                                 # Paeth
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        rows.append(bytes(line))
        prev = line
    return rows


def _png_chunk(out: list, kind: bytes, body: bytes) -> None:
    out.append(len(body).to_bytes(4, "big") + kind + body
               + zlib.crc32(kind + body).to_bytes(4, "big"))


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
    "svg_size_px",
]
