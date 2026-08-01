"""Portable closure metrics reach every public rendering entry point.

These tests deliberately use a deterministic provider double.  Loading and
shaping a real ``.fp`` is owned by frameforge-fonts; this suite proves that the
engine neither drops nor replaces that provider once it crosses the public API.
"""
from __future__ import annotations

from pathlib import Path

import tomllib
from frameforge_render.application.renderer import Renderer
from frameforge_sdk import DocumentBuilder

from frameforge import conform


class _WideMetrics:
    def width(self, text: str, font_size: float) -> float:
        return len(text) * font_size * 2.0


def _document():
    builder = DocumentBuilder(title="closure", profile="diagram")
    layer = builder.page(
        "p1", canvas={"size": [180, 100], "units": "px"}, coordinate_mode="absolute"
    ).layer("content")
    layer.text(
        [10, 10, 90, 50],
        "portable measurement changes this wrap",
        id="copy",
        style={"font_family": ["Pinned Sans", "sans-serif"], "font_size": 12},
    )
    return builder.build()


def test_renderer_prefers_closure_provider_and_names_the_evidence():
    calls: list[tuple[str, bool]] = []

    def provider(family: str, bold: bool):
        calls.append((family, bold))
        return _WideMetrics()

    renderer = Renderer({}, ".", real_metrics=False, metrics_provider=provider)

    assert renderer.metrics_mode == "closure"
    assert renderer.real_metrics is True
    assert renderer.measure(
        "ab", 10, 0.5, {"family": "Pinned Sans, sans-serif", "bold": False}
    ) == 40.0
    assert calls == [("Pinned Sans, sans-serif", False)]


def test_svg_and_html_entry_points_use_the_same_provider():
    calls: list[tuple[str, bool]] = []

    def provider(family: str, bold: bool):
        calls.append((family, bold))
        return _WideMetrics()

    svgs, stats, diagnostics = conform.render_pages_with_stats(
        _document(), metrics_provider=provider, diagnostics=True
    )
    html = conform.render_html(_document(), metrics_provider=provider)

    assert svgs and stats["total"] == 1
    assert diagnostics["metrics_mode"] == "closure"
    assert "<!DOCTYPE html>" in html
    assert calls


def test_reports_and_golden_helpers_preserve_the_provider():
    provider = lambda _family, _bold: _WideMetrics()
    model = _document()

    svgs = conform.render_page_svgs(model, metrics_provider=provider)
    hashes = conform.page_hashes(model, metrics_provider=provider)
    conform.assert_golden(model, hashes, metrics_provider=provider)

    assert svgs and hashes
    assert isinstance(conform.overflow_report(model, metrics_provider=provider), list)
    assert isinstance(conform.paint_report(model, metrics_provider=provider), list)
    assert isinstance(conform.legibility_report(model, metrics_provider=provider), list)
    assert isinstance(conform.collision_report(model, metrics_provider=provider), list)


def test_unresolved_permissive_provider_falls_back_to_estimate():
    renderer = Renderer({}, ".", metrics_provider=lambda _family, _bold: None)

    assert renderer.metrics_mode == "closure"
    assert renderer.measure(
        "abc", 10, 0.5, {"family": "Not Pinned", "bold": False}
    ) == 15.0


def test_frameforge_metrics_extra_installs_sdk_and_renderer_closure_support():
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    metrics = project["dependency-groups"]["metrics"]

    assert any(item.startswith("frameforge-sdk[metrics]") for item in metrics)
    assert any(item.startswith("frameforge-render[fonts,metrics]") for item in metrics)
