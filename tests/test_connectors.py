"""Connector anchors and routes.

fixtures/connectors.fg.yaml is the oracle for connector rendering in the SVG
proxy. It covers object ports, object sides, explicit point targets, orthogonal
route points, arrow markers, and labels.

Connector is TYPED at HEAD (§3.11): the model half of this file asserts that
`Document.model_validate` accepts exactly what the renderer renders (the fixture
surface), and that the validator no longer reports connectors as out-of-profile.
"""
import glob
import os
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER = os.path.join(ROOT, "tooling", "render_fixtures.py")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "connectors.fg.yaml")

sys.path[:0] = [os.path.join(ROOT, "tooling")]

import frameforge.model as fg  # noqa: E402
import validate as V  # noqa: E402


def _render_fixture(name):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "tests", "fixtures", name),
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


# --- the typed model accepts what the renderer renders (§3.11) ---------------- #
def test_connector_fixture_validates_against_the_models():
    doc = yaml.safe_load(open(FIXTURE, encoding="utf-8"))
    model = fg.Document.model_validate(doc)  # must not raise
    conns = [o for o in model.pages[0].layers[1].objects]
    assert [c.type for c in conns] == ["connector", "connector"]
    # normalisation: fixture `object:`/route `type:` land on the canonical keys
    assert conns[0].from_.ref == "left" and conns[0].from_.port == "east"
    assert conns[0].to.side == "west" and conns[0].route.kind == "straight"
    assert conns[1].to.point == [300.0, 140.0]
    assert conns[1].route.points == [[80.0, 130.0], [300.0, 130.0]]
    assert conns[0].label.text == "port to side"


def test_connector_fixture_is_no_longer_out_of_profile():
    _, findings, code = V.validate_doc(FIXTURE)
    assert code == 0
    assert not [f for f in findings if f.code == "out-of-profile"], \
        "typed connectors must not be reported out-of-profile"
