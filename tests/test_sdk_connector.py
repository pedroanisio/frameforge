#!/usr/bin/env python3
"""PageBuilder.connector — the SDK lowering for the typed Connector object (§3.11).

The model half asserts the builder emits exactly the shape ``Document.model_validate``
accepts (endpoint ref/port/side/offset/point forms, route waypoints, boxed label,
arrow markers in ``stroke_style``); the render half smoke-tests that the connector
actually paints through the SVG proxy (same geometry as ``fixtures/connectors.fg.yaml``,
the renderer's oracle). Path bootstrap comes from the root ``conftest.py``.
"""
from __future__ import annotations

import pytest

from framegraph.sdk import DocumentBuilder
from framegraph.sdk.conform import render_page_svgs


def _diagram():
    """Two anchored rects (the connectors.fg.yaml node geometry) + a label style."""
    builder = DocumentBuilder(title="connector sdk", profile="diagram")
    label = builder.define_text_style(
        "label", font_family=["DejaVu Sans", "Arial"], font_size=12, color="#1f2937")
    page = builder.page("p", canvas={"size": [360, 180], "units": "px"})
    nodes = page.layer("nodes")
    nodes.rect([40, 54, 80, 50], id="left", fill="#eef4ff",
               stroke="#1f2937", stroke_style={"stroke_width": 1},
               ports={"east": [120, 79]})
    nodes.rect([240, 54, 80, 50], id="right", fill="#eef4ff",
               stroke="#1f2937", stroke_style={"stroke_width": 1})
    return builder, page, label


def test_connector_lowers_every_endpoint_form_and_validates():
    builder, page, label = _diagram()
    wires = page.layer("wires")
    wires.connector({"ref": "left", "port": "east"}, {"ref": "right", "side": "west"},
                    id="c1", route_kind="straight",
                    label="port to side", label_box=[130, 60, 100, 18], label_style=label,
                    stroke="#2563eb", stroke_style={"stroke_width": 2}, arrow_end=True)
    wires.connector({"ref": "left", "side": "south"}, [300, 140],
                    id="c2", route=[[80, 130], [300, 130]], route_kind="orthogonal",
                    stroke="#1f2937",
                    stroke_style={"stroke_width": 1.5, "stroke_dasharray": [5, 3]})
    wires.connector("left", {"ref": "right", "side": "north", "offset": 10}, id="c3")

    doc = builder.build()                       # Document.model_validate green
    c1, c2, c3 = doc.pages[0].layers[1].objects
    assert (c1.type, c2.type, c3.type) == ("connector", "connector", "connector")

    # endpoint forms land on the canonical model keys
    assert c1.from_.ref == "left" and c1.from_.port == "east"
    assert c1.to.ref == "right" and c1.to.side == "west"
    assert c2.from_.side == "south"
    assert c2.to == [300.0, 140.0]              # a bare point anchors as Point
    assert c3.from_.ref == "left"               # bare id string -> {"ref": id}
    assert c3.to.side == "north" and c3.to.offset == 10

    # route + label + marker lowering
    assert c1.route.kind == "straight" and c1.route.points is None
    assert c2.route.kind == "orthogonal"
    assert c2.route.points == [[80.0, 130.0], [300.0, 130.0]]
    assert c1.label.text == "port to side" and c1.label.box == [130.0, 60.0, 100.0, 18.0]
    assert c1.label.style == "label"
    assert c1.stroke_style.arrow_end is True    # marker merged into stroke_style
    assert c1.stroke_style.stroke_width == 2


def test_connector_marker_merge_and_label_box_guards():
    builder, page, _ = _diagram()
    wires = page.layer("wires")
    with pytest.raises(ValueError, match="label_box"):
        wires.connector("left", "right", label="needs a box")
    with pytest.raises(TypeError, match="stroke_style"):
        wires.connector("left", "right", arrow_end=True, stroke_style="some_token")


def test_connector_paints_through_the_svg_proxy():
    """Render smoke: same geometry as fixtures/connectors.fg.yaml, same SVG output."""
    builder, page, label = _diagram()
    wires = page.layer("wires")
    wires.connector({"ref": "left", "port": "east"}, {"ref": "right", "side": "west"},
                    route_kind="straight",
                    label="port to side", label_box=[130, 60, 100, 18], label_style=label,
                    stroke="#2563eb", stroke_style={"stroke_width": 2}, arrow_end=True)
    wires.connector({"ref": "left", "side": "south"}, [300, 140],
                    route=[[80, 130], [300, 130]], route_kind="orthogonal",
                    stroke="#1f2937",
                    stroke_style={"stroke_width": 1.5, "stroke_dasharray": [5, 3]})

    svg = render_page_svgs(builder.build())[0]
    assert '<line x1="120" y1="79" x2="240" y2="79"' in svg     # port -> side anchor
    assert 'marker-end="url(#' in svg                           # arrow_end marker
    assert ">port to side</tspan>" in svg                       # boxed label text
    assert '<polyline points="80,104 80,130 300,130 300,140"' in svg  # waypoint route
    assert 'stroke-dasharray="5 3"' in svg
