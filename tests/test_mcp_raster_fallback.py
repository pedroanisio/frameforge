#!/usr/bin/env python3
"""The MCP raster lane falls back to CairoSVG when headless Chromium is absent.

A vision model can only verify a render it can *see* (a PNG). The server must
therefore produce PNGs without a browser when CairoSVG is available, and only
report "unavailable" when neither backend can run.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import frameforge.mcp.pipeline as pipeline  # noqa: E402

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _pairs(session_dir, pages=(1, 2)):
    pairs = []
    for page in pages:
        svg = session_dir / f"page-{page:03d}.svg"
        svg.write_text("<svg/>", encoding="utf-8")
        pairs.append((page, svg))
    return pairs


def _browser_unavailable(*_a, **_k):
    from frameforge.rendering.infrastructure.browser import BrowserRendererUnavailable
    raise BrowserRendererUnavailable("no chromium in this environment")


def test_raster_falls_back_to_cairo_when_browser_unavailable(tmp_path, monkeypatch):
    """Chromium unavailable + CairoSVG present -> PNGs are still produced via Cairo."""
    monkeypatch.setattr(
        "frameforge.rendering.infrastructure.browser.rasterize_svg", _browser_unavailable
    )

    def _fake_cairo(svg, out_path, *, base_dir=None, scale=1.0):
        from pathlib import Path
        Path(out_path).write_bytes(_PNG_1X1)
        return Path(out_path)

    monkeypatch.setattr(
        "frameforge.rendering.infrastructure.cairo.rasterize_svg_cairo", _fake_cairo
    )

    renders, warning = pipeline._try_rasterize_pngs(_pairs(tmp_path), tmp_path, "fb")

    assert warning is None
    assert [r["page"] for r in renders] == [1, 2]
    assert all(r["mimeType"] == "image/png" for r in renders)
    assert all(r.get("backend") == "cairo" for r in renders)
    assert (tmp_path / "p001.png").exists() and (tmp_path / "p002.png").exists()


def test_raster_prefers_chromium_when_available(tmp_path, monkeypatch):
    """When Chromium works, it is used and Cairo is not consulted."""
    def _fake_browser(svg, out_path, *, base_dir=None, scale=1.0, playwright_module=None):
        from pathlib import Path
        Path(out_path).write_bytes(_PNG_1X1)
        return Path(out_path)

    def _explode_cairo(*_a, **_k):
        raise AssertionError("Cairo must not be used when Chromium is available")

    monkeypatch.setattr(
        "frameforge.rendering.infrastructure.browser.rasterize_svg", _fake_browser
    )
    monkeypatch.setattr(
        "frameforge.rendering.infrastructure.cairo.rasterize_svg_cairo", _explode_cairo
    )

    renders, warning = pipeline._try_rasterize_pngs(_pairs(tmp_path), tmp_path, "ch")

    assert warning is None
    assert [r.get("backend") for r in renders] == ["chromium", "chromium"]


def test_raster_reports_when_no_backend_available(tmp_path, monkeypatch):
    """Neither backend -> no renders and a warning naming both, so the gap is loud."""
    from frameforge.rendering.infrastructure.cairo import CairoRendererUnavailable

    def _cairo_unavailable(*_a, **_k):
        raise CairoRendererUnavailable("CairoSVG is not installed")

    monkeypatch.setattr(
        "frameforge.rendering.infrastructure.browser.rasterize_svg", _browser_unavailable
    )
    monkeypatch.setattr(
        "frameforge.rendering.infrastructure.cairo.rasterize_svg_cairo", _cairo_unavailable
    )

    renders, warning = pipeline._try_rasterize_pngs(_pairs(tmp_path), tmp_path, "none")

    assert renders == []
    assert warning is not None
    assert "Chromium" in warning and "CairoSVG" in warning


def test_cairo_rasterizer_writes_a_real_png(tmp_path):
    """The CairoSVG backend itself produces a PNG (skipped if CairoSVG absent)."""
    import pytest

    cairo = pytest.importorskip("frameforge.rendering.infrastructure.cairo")
    if not cairo.available():
        pytest.skip("cairosvg not installed")
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="#f2a81c"/></svg>'
    out = cairo.rasterize_svg_cairo(svg, tmp_path / "x.png")
    data = out.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
