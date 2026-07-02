"""Rich inline text spans — per-run typography.

Backs the reused spans renderer (codebase-standards §6/§16 + the standing
fixture rule). v2 `text.spans` is a list of styled runs; the proxy previously
flattened them to a single style. For a single, untruncated line the renderer
now emits one `<text>` with a styled `<tspan>` per run. fixtures/text-spans.fg.yaml
is the oracle: a "Shipping FREE on orders over $35." label whose `FREE` run is
bold + accent-coloured.

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
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "tests", "fixtures", name),
                        "--out", out, "--quiet"], check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def test_spans_render_per_run_styles():
    svg = _render_fixture("text-spans.fg.yaml")
    # one <text> with a styled <tspan> per span (3 runs), not a single flattened run
    assert svg.count("<tspan") >= 3
    # the `FREE` run keeps its own bold + accent-colour style
    assert "font-weight:700" in svg
    assert "fill:#c0392b" in svg
    # the runs flow inline within one element: only the first carries an x
    assert svg.count('<text ') == 1
