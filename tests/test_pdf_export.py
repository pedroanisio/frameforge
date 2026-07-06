#!/usr/bin/env python3
"""
test_pdf_export.py — the `pdf` CLI target must carry document identity into the
PDF: Info-dictionary metadata (title/subject/producer), the catalog /Lang, and
an outline (bookmarks) built from the flow headings.

Subprocess (not an in-process import): the rendering package is named
`framegraph`, which would shadow the `framegraph` models module other tests
import in a shared pytest process. The PDF read-back (pypdf) is in-process.
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest

pytest.importorskip("cairosvg")
pypdf = pytest.importorskip("pypdf")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

_DOC = {
    "dsl": "FrameGraph", "version": "2.2.0",
    "title": "Spectral Notes",
    "description": "A tiny flow document for PDF metadata tests",
    "lang": "en",
    "pages": [{
        "mode": "flow", "id": "p", "canvas": {"size": [400, 300]},
        "story": [
            {"type": "heading", "level": 1, "text": "Introduction"},
            {"type": "paragraph", "text": "lorem ipsum " * 40},
            {"type": "heading", "level": 2, "text": "Background"},
            {"type": "paragraph", "text": "dolor sit amet " * 40},
            {"type": "heading", "level": 1, "text": "Methods"},
            {"type": "paragraph", "text": "consectetur " * 10},
        ],
    }],
}


def _export_pdf(doc):
    """Render via the CLI and hand the PDF back as an in-memory stream."""
    import io
    with tempfile.TemporaryDirectory(prefix="fg-pdf-test-") as td:
        src = os.path.join(td, "doc.fg.json")
        out = os.path.join(td, "doc.pdf")
        with open(src, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        subprocess.run([sys.executable, "-m", "framegraph.cli", src, "--to", "pdf",
                        "--out", td, "--single", out], check=True, cwd=ROOT,
                       env={**os.environ, "PYTHONPATH": os.pathsep.join(
                           [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")])})
        with open(out, "rb") as fh:
            return io.BytesIO(fh.read())


def _flatten_outline(outline):
    flat = []
    for item in outline:
        if isinstance(item, list):
            flat.extend(_flatten_outline(item))
        else:
            flat.append(item)
    return flat


def test_pdf_carries_document_metadata():
    reader = pypdf.PdfReader(_export_pdf(_DOC))
    meta = reader.metadata
    assert meta.title == "Spectral Notes"
    assert meta.subject == "A tiny flow document for PDF metadata tests"
    assert "FrameGraph" in (meta.producer or "")
    assert reader.trailer["/Root"].get("/Lang") == "en"


def test_pdf_outline_built_from_headings():
    reader = pypdf.PdfReader(_export_pdf(_DOC))
    flat = _flatten_outline(reader.outline)
    titles = [d.title for d in flat]
    assert titles == ["Introduction", "Background", "Methods"]
    # heading page targets are real pages inside the document
    pages = [reader.get_destination_page_number(d) for d in flat]
    assert all(0 <= p < len(reader.pages) for p in pages)
    assert pages == sorted(pages)


def test_pdf_without_headings_has_no_outline():
    doc = {"dsl": "FrameGraph", "version": "2.2.0", "title": "Plain",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [200, 100]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "rect", "box": [0, 0, 50, 50], "fill": "#123456"}]}]}]}
    reader = pypdf.PdfReader(_export_pdf(doc))
    assert _flatten_outline(reader.outline) == []
    assert reader.metadata.title == "Plain"


if __name__ == "__main__":
    test_pdf_carries_document_metadata()
    print("OK")
