#!/usr/bin/env python3
"""Headless Chromium raster adapter tests.

These use a fake Playwright module so the default test suite does not need a
downloaded browser. The optional end-to-end path is exercised by running
``tooling/render_chromium.py`` after installing the ``browser`` dependency group.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.rendering.infrastructure.browser import rasterize_svg, svg_size  # noqa: E402
from tooling import render_chromium  # noqa: E402


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

    def launch(self):
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
        self.html = ""

    def set_content(self, html, wait_until=None):
        self.html = html
        self.wait_until = wait_until

    def screenshot(self, path, type=None, full_page=None):
        self.screenshot_args = {"path": path, "type": type, "full_page": full_page}
        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\nfake")


def test_svg_size_reads_width_height_and_units():
    assert svg_size('<svg width="320" height="180" viewBox="0 0 1 1"></svg>') == (320, 180)
    assert svg_size('<svg width="72pt" height="1in"></svg>') == (96, 96)


def test_svg_size_falls_back_to_viewbox():
    assert svg_size('<svg viewBox="0 0 640 360"></svg>') == (640, 360)


def test_rasterize_svg_uses_headless_browser(tmp_path):
    fake = FakePlaywrightModule()
    out = rasterize_svg(
        '<svg width="120" height="80"><rect width="120" height="80" fill="red"/></svg>',
        tmp_path / "page.png",
        base_dir=tmp_path,
        scale=2,
        playwright_module=fake,
    )

    page = fake.manager.chromium.browser.pages[0]
    assert out.exists()
    assert page.kwargs["viewport"] == {"width": 120, "height": 80}
    assert page.kwargs["device_scale_factor"] == 2
    assert "<base href=" in page.html
    assert page.screenshot_args["type"] == "png"
    assert fake.manager.chromium.browser.closed is True


def test_render_chromium_list_mode(capsys):
    assert render_chromium.main(["fixtures/calendar-3day.fg.yaml", "--list"]) == 0
    out = capsys.readouterr().out
    assert "fixtures/calendar-3day.fg.yaml" in out
    assert "1 document(s)." in out


def test_render_chromium_no_documents(tmp_path):
    assert render_chromium.main(["/no/such/file.fg.yaml", "--out", str(tmp_path)]) == 1
