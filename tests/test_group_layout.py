"""Group layout arrangement — row / column / grid.

Backs the reused layout engine (codebase-standards §6/§16 + the standing fixture
rule). v2 `Group.layout` arranges children; the proxy previously ignored it, so
children authored at (0,0) overlapped. fixtures/group-layout.fg.yaml is the
oracle: the layout engine repositions each child via a `translate(...)` group
(it does not resize), so the gap-spaced offsets below are deterministic.

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


def test_row_column_grid_children_are_arranged():
    svg = _render_fixture("group-layout.fg.yaml")
    # ROW: 60-wide tiles + gap 10 -> child offsets 0 / 70 / 140
    assert 'translate(70,0)' in svg and 'translate(140,0)' in svg
    # COLUMN: 60-tall tiles + gap 10 -> child offsets 0 / 70 / 140
    assert 'translate(0,70)' in svg and 'translate(0,140)' in svg
    # GRID: 2 cols, 90-wide tiles, gap 10 — content-derived tracks (spec §3.6)
    # -> pitch 100: (100,0) / (0,100) / (100,100)
    assert 'translate(100,0)' in svg
    assert 'translate(0,100)' in svg
    assert 'translate(100,100)' in svg
