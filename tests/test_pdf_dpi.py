#!/usr/bin/env python3
"""
test_pdf_dpi.py — DIM-7: both svg2pdf call sites (mcp/pipeline._export_pdf and
cli r_pdf) must pass dpi=96 explicitly so the CSS px→pt conversion
(1 px unit = 0.75 pt) is pinned, never the library default. The page MediaBox
is asserted at size*0.75 pt against a known canvas.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

cairosvg = pytest.importorskip("cairosvg")
pypdf = pytest.importorskip("pypdf")

# import at collection time, before tooling/validate.py can re-shadow the
# `frameforge` package with the models module (repo test convention)
from frameforge import cli  # noqa: E402
from frameforge.mcp.pipeline import _export_pdf  # noqa: E402

SVG_800x600 = ('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" '
               'viewBox="0 0 800 600"><rect width="800" height="600" fill="#fff"/></svg>')

DOC_800x600 = """\
dsl: FrameForge
version: 2.2.0
title: dpi fixture
pages:
  - id: p1
    canvas:
      size: [800, 600]
    layers:
      - id: L1
        objects:
          - type: rect
            box: [0, 0, 800, 600]
            style:
              fill: "#204060"
"""


def _mediabox(pdf_path: Path):
    page = pypdf.PdfReader(str(pdf_path)).pages[0]
    return float(page.mediabox.width), float(page.mediabox.height)


def _recording_svg2pdf(calls):
    real = cairosvg.svg2pdf

    def wrapper(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)

    return wrapper


# --- mcp/pipeline._export_pdf --------------------------------------------------- #
def test_pipeline_export_pdf_passes_explicit_dpi_and_mediabox(tmp_path, monkeypatch):
    calls: list = []
    monkeypatch.setattr(cairosvg, "svg2pdf", _recording_svg2pdf(calls))
    svg_path = tmp_path / "p001.svg"
    svg_path.write_text(SVG_800x600, encoding="utf-8")
    session = tmp_path / "session"
    session.mkdir()
    entry, summary, warning = _export_pdf([(1, svg_path)], session, "s1", tmp_path)
    assert warning is None and summary["ok"] is True and entry is not None
    assert calls and calls[0].get("dpi") == 96, "svg2pdf must pin dpi=96 explicitly"
    # 1 px unit = 0.75 pt at CSS 96 dpi: 800x600 px page -> 600x450 pt MediaBox
    assert _mediabox(session / "document.pdf") == (600.0, 450.0)


# --- cli --to pdf ---------------------------------------------------------------- #
def test_cli_pdf_passes_explicit_dpi_and_mediabox(tmp_path, monkeypatch):
    calls: list = []
    monkeypatch.setattr(cairosvg, "svg2pdf", _recording_svg2pdf(calls))
    doc = tmp_path / "dpi-fixture.fg.yaml"
    doc.write_text(DOC_800x600, encoding="utf-8")
    out_dir = tmp_path / "out"
    assert cli.main([str(doc), "--to", "pdf", "--out", str(out_dir)]) == 0
    assert calls and all(kw.get("dpi") == 96 for kw in calls), \
        "svg2pdf must pin dpi=96 explicitly"
    # cli stems on splitext, so `dpi-fixture.fg.yaml` writes `dpi-fixture.fg.pdf`
    assert _mediabox(out_dir / "dpi-fixture.fg.pdf") == (600.0, 450.0)


# --- library sanity: what dpi=96 means ------------------------------------------- #
def test_svg2pdf_dpi96_is_the_075_scaling():
    pdf = cairosvg.svg2pdf(bytestring=SVG_800x600.encode("utf-8"), dpi=96)
    page = pypdf.PdfReader(io.BytesIO(pdf)).pages[0]
    assert (float(page.mediabox.width), float(page.mediabox.height)) == (600.0, 450.0)
