#!/usr/bin/env python3
"""render_pdf --impose: uniform presentation sheets, zero hash impact.

A document may legitimately mix canvases (Letter book pages beside a 16:9
slide beside a portrait story — the capability tour does exactly this), which
makes the assembled PDF disorienting to page through. ``--impose letter|a4``
frames every page onto one uniform sheet at assembly time: pages that fit are
centred 1:1, oversized pages are contain-scaled with a hairline frame.

The contract under test: imposition is a PRESENTATION transform. It happens
downstream of ``render_page_svgs``, so ``page_hashes`` — SHA-256 over those
SVG strings — must be byte-for-byte identical whether or not the PDF is
imposed. Uniformity lives in the PDF; the canonical document never changes.

Subprocess (not in-process import) for the CLI, mirroring test_pdf_export.py:
the rendering package is named `framegraph` and would shadow the models
module in a shared pytest process.
"""
import os
import subprocess
import sys
import tempfile

import pytest

pytest.importorskip("cairosvg")
pypdf = pytest.importorskip("pypdf")
yaml = pytest.importorskip("yaml")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER_PDF = os.path.join(ROOT, "tooling", "render_pdf.py")

_DOC = {
    "dsl": "FrameGraph", "version": "2.2.0", "profile": "mixed",
    "title": "impose fixture", "lang": "en",
    "pages": [
        {"mode": "page", "id": "book", "canvas": {"size": [816, 1056], "units": "px"},
         "layers": [{"id": "l", "objects": [
             {"type": "rect", "box": [40, 40, 736, 976], "fill": "#EEF1F5"}]}]},
        {"mode": "page", "id": "slide", "canvas": {"size": [1920, 1080], "units": "px"},
         "layers": [{"id": "l", "objects": [
             {"type": "rect", "box": [0, 0, 1920, 1080], "fill": "#0B1020"}]}]},
        {"mode": "page", "id": "story", "canvas": {"size": [1080, 1920], "units": "px"},
         "layers": [{"id": "l", "objects": [
             {"type": "rect", "box": [0, 0, 1080, 1920], "fill": "#1D3A6E"}]}]},
    ],
}

# Letter at the SVG user-unit scale (96/in); cairosvg emits 72/in PDF points.
LETTER_PT = (612.0, 792.0)


def _run(doc_path, out_dir, *extra):
    subprocess.run(
        [sys.executable, RENDER_PDF, doc_path, "--out", out_dir, "-q", *extra],
        check=True, cwd=ROOT)
    pdfs = [f for f in os.listdir(out_dir) if f.endswith(".pdf")]
    assert len(pdfs) == 1, pdfs
    return os.path.join(out_dir, pdfs[0])


def _mediaboxes(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    return [(round(float(p.mediabox.width), 1), round(float(p.mediabox.height), 1))
            for p in reader.pages]


def test_impose_letter_makes_every_pdf_page_uniform_without_touching_hashes():
    sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
    from framegraph.sdk import page_hashes, validate_document

    model = validate_document(_DOC)
    before = page_hashes(model)

    with tempfile.TemporaryDirectory() as tmp:
        doc_path = os.path.join(tmp, "impose-fixture.fg.yaml")
        with open(doc_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(_DOC, fh, sort_keys=False)

        raw = _mediaboxes(_run(doc_path, os.path.join(tmp, "raw")))
        imposed = _mediaboxes(_run(doc_path, os.path.join(tmp, "imp"),
                                   "--impose", "letter"))

    # raw assembly preserves the mixed canvases (three different sheets)
    assert len(set(raw)) == 3
    # imposed assembly is one uniform Letter sheet throughout
    assert imposed == [LETTER_PT] * 3
    # and the canonical document's proxy hashes are untouched by presentation
    assert page_hashes(model) == before
