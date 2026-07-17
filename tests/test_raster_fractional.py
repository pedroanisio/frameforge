#!/usr/bin/env python3
"""
test_raster_fractional.py — DIM-5/NUMFMT-3/TX-9: a fractional canvas must not
be rounded BEFORE the device scale is applied. The Chromium raster of a
793.7x1122.5 canvas at scale 2 must be exactly round(size*scale) device pixels
(1587x2245) with no cropped content and no background stripe on the last
row/column.

Unit tests drive a fake Playwright module (suite needs no browser); the
end-to-end proof runs real headless Chromium and skips when it is unavailable.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.infrastructure.browser import (  # noqa: E402
    BrowserRendererUnavailable,
    rasterize_svg,
    svg_size,
    svg_size_px,
)

FRACTIONAL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="793.7" height="1122.5" '
    'viewBox="0 0 793.7 1122.5">'
    '<rect x="0" y="0" width="100%" height="100%" fill="#204060"/></svg>'
)
FILL = (32, 64, 96)  # #204060


# --- fake Playwright plumbing (mirrors test_chromium_renderer.py) -------------- #
class FakePlaywrightModule:
    def __init__(self):
        self.manager = FakeManager()

    def sync_playwright(self):
        return self.manager


class FakeManager:
    def __init__(self):
        self.chromium = FakeChromium()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeChromium:
    def __init__(self):
        self.browser = FakeBrowser()

    def launch(self, **kwargs):
        return self.browser


class FakeBrowser:
    def __init__(self):
        self.pages = []
        self.closed = False

    def new_page(self, **kwargs):
        page = FakePage(kwargs)
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True


class FakePage:
    def __init__(self, kwargs):
        self.kwargs = kwargs

    def set_content(self, html, wait_until=None):
        self.html = html

    def screenshot(self, path, type=None, full_page=None):
        # emit a REAL solid PNG at viewport*dsf, like Chromium would
        self.screenshot_args = {"path": path, "type": type, "full_page": full_page}
        dsf = self.kwargs["device_scale_factor"]
        vp = self.kwargs["viewport"]
        with open(path, "wb") as fh:
            fh.write(_solid_png(round(vp["width"] * dsf), round(vp["height"] * dsf)))


def _solid_png(w, h, rgb=(32, 64, 96)):
    import struct
    import zlib

    def chunk(kind, body):
        return (len(body).to_bytes(4, "big") + kind + body
                + zlib.crc32(kind + body).to_bytes(4, "big"))

    raw = (b"\x00" + bytes(rgb) * w) * h
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _png_dims(path):
    head = open(path, "rb").read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


# --- unit: size parsing --------------------------------------------------------- #
def test_svg_size_px_is_fractional():
    assert svg_size_px(FRACTIONAL_SVG) == (793.7, 1122.5)
    assert svg_size_px('<svg viewBox="0 0 640.25 360.75"></svg>') == (640.25, 360.75)


def test_svg_size_keeps_legacy_int_semantics():
    assert svg_size('<svg width="320" height="180"></svg>') == (320, 180)
    assert svg_size('<svg width="72pt" height="1in"></svg>') == (96, 96)


# --- unit: viewport covers the page, PNG is cropped to the device-pixel target --- #
def test_fractional_canvas_viewport_ceils_and_png_hits_target(tmp_path):
    fake = FakePlaywrightModule()
    out = rasterize_svg(FRACTIONAL_SVG, tmp_path / "page.png", scale=2,
                        playwright_module=fake)
    page = fake.manager.chromium.browser.pages[0]
    # viewport never rounds the page down — the full canvas stays paintable
    assert page.kwargs["viewport"] == {"width": 794, "height": 1123}
    assert page.kwargs["device_scale_factor"] == 2
    # the 1588x2246 viewport raster is cropped to round(size*scale) exactly
    assert _png_dims(out) == (1587, 2245)


def test_integer_canvas_raster_bytes_untouched(tmp_path):
    fake = FakePlaywrightModule()
    out = rasterize_svg(
        '<svg width="120" height="80"><rect width="120" height="80" fill="red"/></svg>',
        tmp_path / "page.png", scale=2, playwright_module=fake,
    )
    page = fake.manager.chromium.browser.pages[0]
    assert page.kwargs["viewport"] == {"width": 120, "height": 80}
    # already exactly 120*2 x 80*2 — the crop pass must not rewrite the bytes
    assert open(out, "rb").read() == _solid_png(240, 160)


def test_fit_png_file_crop_preserves_pixels(tmp_path):
    """Cropping by scanline truncation must keep every surviving pixel intact
    across PNG filter types (Pillow picks adaptive filters when saving)."""
    PIL = pytest.importorskip("PIL.Image")
    from frameforge.rendering.infrastructure.browser import _fit_png_file
    src = PIL.new("RGBA", (23, 17))
    src.putdata([(x * 11 % 256, y * 13 % 256, (x + y) % 256, 255)
                 for y in range(17) for x in range(23)])
    p = tmp_path / "grad.png"
    src.save(p)
    _fit_png_file(p, 19, 11)
    got = PIL.open(p).convert("RGBA")
    assert got.size == (19, 11)
    assert got.tobytes() == src.crop((0, 0, 19, 11)).tobytes()


def test_fit_png_file_edge_extends_under_render(tmp_path):
    """A browser that under-renders a fractional canvas by a sub-pixel yields a
    raster smaller than the device-pixel target; `_fit_png_file` must extend it
    to the exact target by clamping the edge pixel (no background stripe, no
    raise) — the fix for real-Chromium fractional flakiness."""
    PIL = pytest.importorskip("PIL.Image")
    from frameforge.rendering.infrastructure.browser import _fit_png_file
    src = PIL.new("RGB", (10, 6))
    # distinct edge column/row so an extension is visible and checkable
    src.putdata([((x * 20) % 256, (y * 30) % 256, 40) for y in range(6) for x in range(10)])
    p = tmp_path / "under.png"
    src.save(p)
    _fit_png_file(p, 12, 8)                       # ask for 2 more px in each axis
    got = PIL.open(p).convert("RGB")
    assert got.size == (12, 8)                    # exact target, no raise
    px = got.load()
    # extended right columns clamp the last real column (x=9)
    assert px[10, 3] == px[9, 3] and px[11, 3] == px[9, 3]
    # extended bottom rows clamp the last real row (y=5)
    assert px[4, 6] == px[4, 5] and px[4, 7] == px[4, 5]


# --- end-to-end: real Chromium proof --------------------------------------------- #
def test_fractional_canvas_png_dims_and_no_edge_stripe(tmp_path):
    PIL = pytest.importorskip("PIL.Image")
    try:
        out = rasterize_svg(FRACTIONAL_SVG, tmp_path / "page.png", scale=2)
    except BrowserRendererUnavailable as exc:
        pytest.skip(f"headless Chromium unavailable: {exc}")
    img = PIL.open(out).convert("RGB")
    # exact device-pixel target: round(793.7*2), round(1122.5*2)
    assert img.size == (1587, 2245)
    px = img.load()
    w, h = img.size
    # every pixel of the last column and last row is canvas fill — no white
    # stripe, no cropped canvas (scan step keeps the check fast but dense)
    for y in range(0, h, 7):
        assert _near(px[w - 1, y], FILL), f"right edge not canvas at y={y}: {px[w - 1, y]}"
    for x in range(0, w, 7):
        assert _near(px[x, h - 1], FILL), f"bottom edge not canvas at x={x}: {px[x, h - 1]}"


def _near(rgb, want, tol=8):
    return all(abs(a - b) <= tol for a, b in zip(rgb, want))
