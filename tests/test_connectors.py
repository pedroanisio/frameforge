"""Connector anchors and routes.

fixtures/connectors.fg.yaml is the oracle for out-of-profile connector rendering
in the SVG proxy. It covers object ports, object sides, explicit point targets,
orthogonal route points, arrow markers, and labels.
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


def test_connector_resolves_port_side_and_label():
    svg = _render_fixture("connectors.fg.yaml")
    assert '<line x1="120" y1="79" x2="240" y2="79"' in svg
    assert 'marker-end="url(#' in svg
    assert ">port to side</tspan>" in svg


def test_connector_resolves_orthogonal_route_to_point():
    svg = _render_fixture("connectors.fg.yaml")
    assert '<polyline points="80,104 80,130 300,130 300,140"' in svg
    assert 'stroke-dasharray="5 3"' in svg
