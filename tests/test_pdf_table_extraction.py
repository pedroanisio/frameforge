"""PDF table extraction → native FrameGraph table object.

Backs the reused table-detection front-end ported into
`tooling/pdf_to_framegraph_yml.py` (the standing fixture rule: a reused component
ships with a checked-in fixture, not just synthetic unit tests).

`fixtures/pdf_table_extraction.fg.yaml` is the transpiler's output for the small
ruled table in `fixtures/pdf_table_extraction.pdf` (3 cols × header+3 rows,
widths 150 / 140 / 90). It exercises the whole path: detect → emit a native
`type: table` with per-column widths recovered from the detected cell geometry →
render. The column separators are the oracle: x0(40) + 150 = 190, + 140 = 330.

Subprocess render (not an in-process import) to avoid the framegraph-package vs
models-module name clash in the shared pytest process — same pattern as
tests/test_table_widths.py.
"""
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER = os.path.join(ROOT, "tooling", "render_fixtures.py")
FIXTURE = "pdf_table_extraction.fg.yaml"


def _render_fixture(name):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "tests", "fixtures", name),
                        "--out", out, "--quiet"], check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def test_detected_table_renders_with_recovered_column_widths():
    svg = _render_fixture(FIXTURE)
    # per-column widths recovered from the PDF cell geometry (150 / 140 / 90),
    # so the column rules land at x = 190 and x = 330 (not an equal split).
    assert 'x1="190" y1="50"' in svg
    assert 'x1="330" y1="50"' in svg
    # an equal 3-way split of the 380px table would have put rules at ~166.7 / 293.3
    assert 'x1="166.667" y1="50"' not in svg


def test_detected_table_keeps_header_and_cell_text():
    svg = _render_fixture(FIXTURE)
    for word in ("Component", "Status", "Cells", "Detector", "Validator", "pass"):
        assert f">{word}<" in svg, f"missing extracted cell text: {word}"
