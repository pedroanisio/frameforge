#!/usr/bin/env python3
"""MCP render export options: `to='pdf'`, raster `scale`, and `real_metrics`.

The render tools must reach the same export surface the CLI has — a vector PDF
assembled from the rendered pages (reusing the `frameforge/cli.py r_pdf`
mechanism), a raster zoom/DPI control for the PNG lane, and the renderer's
real-glyph-metrics opt-in — all reported structured and degrading with hints.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.mcp.server import (  # noqa: E402
    read_session_resource,
    render_frameforge_yaml,
    run_sdk_code,
)

SDK_SCRIPT = """
from frameforge.sdk import DocumentBuilder

doc = DocumentBuilder(title="Export Probe", profile="deck")
page = doc.page("p1", canvas={"size": [320, 180], "units": "px"})
page.layer("main").rect([0, 0, 320, 180], fill="#f7f7f2")
page.text([28, 32, 220, 36], "exported", id="t")
doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
"""

_PDF_DEPS = bool(importlib.util.find_spec("cairosvg")) and bool(importlib.util.find_spec("pypdf"))

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


@pytest.mark.skipif(not _PDF_DEPS, reason="cairosvg/pypdf (pdfout group) not installed")
def test_run_sdk_code_to_pdf_assembles_document_pdf(tmp_path):
    result = run_sdk_code(
        SDK_SCRIPT, session_id="pdf1", session_root=tmp_path, raster_png=False, to="pdf"
    )

    assert result["ok"] is True
    pdf = result["pdf"]
    assert pdf["ok"] is True
    assert pdf["pages"] == 1
    assert pdf["uri"] == "frameforge://session/pdf1/document.pdf"
    pdf_path = tmp_path / "pdf1" / "document.pdf"
    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:5] == b"%PDF-"
    # the artifact is a render entry + resource link, not just a loose file
    assert any(r.get("mimeType") == "application/pdf" for r in result["renders"])
    assert any(link["uri"].endswith("document.pdf") for link in result["resources"])


@pytest.mark.skipif(not _PDF_DEPS, reason="cairosvg/pypdf (pdfout group) not installed")
def test_document_pdf_is_readable_as_a_session_resource(tmp_path):
    from frameforge.sdk import DocumentBuilder
    from frameforge.sdk.io import serialize

    builder = DocumentBuilder(title="PDF YAML", profile="deck")
    page = builder.page("p1", canvas={"size": [120, 80], "units": "px"})
    page.layer("main").rect([0, 0, 120, 80], fill="#ffffff")
    yaml_text = serialize(builder.build(), format="yaml")

    result = render_frameforge_yaml(
        yaml_text, session_id="pdfres", session_root=tmp_path, raster_png=False, to="pdf"
    )
    assert result["ok"] is True and result["pdf"]["ok"] is True

    payload = read_session_resource(
        "frameforge://session/pdfres/document.pdf", session_root=tmp_path
    )
    assert payload["mimeType"] == "application/pdf"
    assert "blob" not in payload, "binary resources ship by reference by default"
    assert payload["kind"] == "binary" and payload["bytes"] > 0
    assert payload["path"].endswith("document.pdf")

    blob_payload = read_session_resource(
        "frameforge://session/pdfres/document.pdf", session_root=tmp_path, mode="blob"
    )
    assert blob_payload["blob"], "small PDFs may still ship inline on explicit request"


def test_to_pdf_degrades_structured_when_pdfout_group_missing(tmp_path, monkeypatch):
    """Missing cairosvg/pypdf: the SVG render stays ok, the pdf block carries the hint."""
    monkeypatch.setitem(sys.modules, "pypdf", None)  # forces the in-function import to fail

    result = run_sdk_code(
        SDK_SCRIPT, session_id="nopdf", session_root=tmp_path, raster_png=False, to="pdf"
    )

    assert result["ok"] is True  # pages rendered; only the export lane failed
    assert result["pdf"]["ok"] is False
    assert "pdfout" in result["pdf"]["hint"]
    assert "PDF" in (result.get("render_warning") or "")


def test_unknown_export_target_is_a_structured_error(tmp_path):
    result = run_sdk_code(
        SDK_SCRIPT, session_id="badto", session_root=tmp_path, raster_png=False, to="docx"
    )

    assert result["ok"] is False
    assert "docx" in result["error"]
    assert "pdf" in result["hint"]


def test_scale_threads_to_the_raster_backend(tmp_path, monkeypatch):
    seen: list[float] = []

    def _fake_rasterize_svg(svg, out_path, *, base_dir=None, scale=1.0, playwright_module=None):
        from pathlib import Path

        seen.append(scale)
        Path(out_path).write_bytes(_PNG_1X1)
        return Path(out_path)

    monkeypatch.setattr(
        "frameforge.rendering.infrastructure.browser.rasterize_svg", _fake_rasterize_svg
    )

    result = run_sdk_code(
        SDK_SCRIPT, session_id="zoom", session_root=tmp_path, raster_png=True, scale=2.0
    )

    assert result["ok"] is True
    assert seen == [2.0]
    assert (tmp_path / "zoom" / "p001.png").exists()


def test_real_metrics_resolution_is_reported(tmp_path):
    off = run_sdk_code(
        SDK_SCRIPT, session_id="rm0", session_root=tmp_path, raster_png=False, real_metrics=False
    )
    on = run_sdk_code(
        SDK_SCRIPT, session_id="rm1", session_root=tmp_path, raster_png=False, real_metrics=True
    )
    auto = run_sdk_code(
        SDK_SCRIPT, session_id="rm2", session_root=tmp_path, raster_png=False, real_metrics="auto"
    )

    assert off["ok"] and on["ok"] and auto["ok"]
    assert off["real_metrics"] is False
    assert on["real_metrics"] is True
    assert auto["real_metrics"] is (importlib.util.find_spec("fontTools") is not None)


def test_real_metrics_true_reaches_the_renderer(tmp_path, monkeypatch):
    import frameforge.rendering.application.renderer as renderer_mod

    seen: list[bool] = []
    real_renderer = renderer_mod.Renderer

    class RecordingRenderer(real_renderer):
        def __init__(self, doc, base_dir, *, real_metrics=False, **kwargs):
            seen.append(real_metrics)
            super().__init__(doc, base_dir, real_metrics=real_metrics, **kwargs)

    monkeypatch.setattr(renderer_mod, "Renderer", RecordingRenderer)

    result = run_sdk_code(
        SDK_SCRIPT, session_id="rmwire", session_root=tmp_path, raster_png=False, real_metrics=True
    )

    assert result["ok"] is True
    assert True in seen, "real_metrics=True must reach the Renderer constructor"


def test_real_metrics_auto_honors_env_override(monkeypatch):
    """'auto' must not silently override an operator's FRAMEFORGE_REAL_METRICS
    (e.g. forcing the byte-stable estimator for golden reproduction)."""
    from frameforge.mcp.pipeline import _resolve_real_metrics

    monkeypatch.setenv("FRAMEFORGE_REAL_METRICS", "0")
    assert _resolve_real_metrics("auto") is False
    monkeypatch.setenv("FRAMEFORGE_REAL_METRICS", "true")
    assert _resolve_real_metrics("auto") is True
    # explicit bool still beats the env
    assert _resolve_real_metrics(False) is False
    monkeypatch.delenv("FRAMEFORGE_REAL_METRICS")
    assert isinstance(_resolve_real_metrics("auto"), bool)
