"""Table row heights + cell wrapping.

Backs the reused row-height / cell-wrap component (codebase-standards §6/§16 +
the standing fixture rule). The proxy ignored the v2 `row_height` /
`header_height` fields (rows were split evenly) and never wrapped cell text.
fixtures/table-rows.fg.yaml is the oracle: header_height 30 + row_height 44 (so
the frame is 30+44+44 = 118, not the box's 150), and a long note that wraps to
multiple lines clipped to its cell.

Subprocess render (not an in-process import) to avoid the frameforge-package vs
models-module name clash in the shared pytest process.
"""
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER = os.path.join(ROOT, "tooling", "render_fixtures.py")


def _render_fixture(name):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "tests", "fixtures", name),
                        "--out", out, "--quiet"], check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def test_explicit_row_heights_are_honored():
    svg = _render_fixture("table-rows.fg.yaml")
    assert 'height="30"' in svg          # header_height
    assert 'height="44"' in svg          # row_height
    assert 'height="118"' in svg         # frame = 30 + 44 + 44 (heights honored)
    assert 'height="150"' not in svg     # NOT the old even-split (box height 150)


def test_long_cell_wraps_and_is_clipped():
    svg = _render_fixture("table-rows.fg.yaml")
    assert 'clip-path="url(#clip' in svg          # wrapped cell is clipped to its box
    assert "must wrap</text>" in svg              # line 1 ends mid-sentence (wrapped)
    assert "narrow" in svg                        # a later wrapped line is present
