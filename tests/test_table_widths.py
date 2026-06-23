"""Table column-width resolution (percent / fixed / fr / auto).

Backs the reused width-resolution component (codebase-standards §6/§16 + the
standing fixture rule). The proxy previously resolved only numeric px widths —
`num("30%")` returns None — so percent / fr / auto columns collapsed to an equal
free-split. fixtures/tables.fg.yaml is the oracle: a 560px-wide table with columns
40% / 120px / 1fr / auto, so the column separators land at x = 264 / 384 / 492
(an equal split would have put the first near 187).

Subprocess render (not an in-process import) to avoid the framegraph-package vs
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
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "fixtures", name),
                        "--out", out, "--quiet"], check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def test_percent_fixed_fr_auto_column_widths_resolved():
    svg = _render_fixture("tables.fg.yaml")
    # 40% of 560 = 224 -> first vertical separator at x0(40)+224 = 264;
    # +120px -> 384; +1fr(108) -> 492. (y1="60" = the table top, i.e. a column rule.)
    assert 'x1="264" y1="60"' in svg
    assert 'x1="384" y1="60"' in svg
    assert 'x1="492" y1="60"' in svg
    # the old equal free-split would have placed the first separator near 187
    assert 'x1="186.667" y1="60"' not in svg
