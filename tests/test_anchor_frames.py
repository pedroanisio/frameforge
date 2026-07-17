"""Anchor/connector coordinate frames (pixel-perfect campaign, C2 stage).

TX-6 — anchors to objects inside a laid-out (row/column/grid/wrap) group must
resolve to the ARRANGED position (the same math `_group_children` paints with,
via `LayoutEngine.arrange`), not the authored box.

TX-7 — port anchors are authored in the same frame as the object's `box`
(the committed fixture `tests/fixtures/connectors.fg.yaml` pins that frame:
page space for a top-level object), so they must ride every offset the box
receives: ancestor group origins AND layout arrangement. Previously they were
returned verbatim, missing nested targets by exactly the ancestor offset.
"""
import re

from frameforge.rendering.application.renderer import Renderer


def _render(doc):
    r = Renderer(doc, ".")
    svg = r.render_page(doc["pages"][0])[0]
    return r, svg


def _line_coords(svg):
    m = re.search(r'<line x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', svg)
    assert m, f"no <line> in {svg[:400]}"
    return tuple(float(v) for v in m.groups())


def _doc(objects):
    return {
        "dsl": "FrameForge", "version": "2.5.0",
        "pages": [{"mode": "page", "id": "p", "canvas": {"size": [1000, 800]},
                   "layers": [{"id": "L", "objects": objects}]}],
    }


# --------------------------------------------------------------------------- #
# TX-6 — layout arrangement composes into anchor resolution                    #
# --------------------------------------------------------------------------- #

def test_anchor_hits_arranged_child_in_row_layout_group():
    doc = _doc([
        {"type": "group", "id": "g", "box": [100, 100, 2000, 400],
         "layout": {"kind": "row", "gap": 50},
         "children": [
             {"type": "rect", "id": "a", "box": [0, 0, 300, 400]},
             {"type": "rect", "id": "b", "box": [0, 0, 300, 400]},
         ]},
        {"type": "connector", "id": "c",
         "from": {"object": "b", "side": "west"}, "to": {"point": [900, 300]}},
    ])
    _, svg = _render(doc)
    # b's arranged slot is x=350 group-local (300 + gap 50); group origin adds
    # (100,100): west anchor = (100+350, 100+200) = (450, 300).
    assert 'translate(350 0)' in svg  # the paint-side arrangement this must match
    x1, y1, _, _ = _line_coords(svg)
    assert (x1, y1) == (450.0, 300.0)


def test_anchor_hits_grandchild_of_arranged_group():
    doc = _doc([
        {"type": "group", "id": "g", "box": [100, 100, 2000, 400],
         "layout": {"kind": "row", "gap": 50},
         "children": [
             {"type": "rect", "id": "a", "box": [0, 0, 300, 400]},
             {"type": "group", "id": "g2", "box": [0, 0, 300, 400],
              "children": [{"type": "rect", "id": "r", "box": [10, 20, 50, 30]}]},
         ]},
        {"type": "connector", "id": "c",
         "from": {"object": "r"}, "to": {"point": [900, 700]}},
    ])
    _, svg = _render(doc)
    # r's page box = group origin (100,100) + g2 arranged (350,0) + authored
    # (10,20) → (460,120); default anchor is the centre → (485, 135).
    x1, y1, _, _ = _line_coords(svg)
    assert (x1, y1) == (485.0, 135.0)


def test_anchor_hits_arranged_child_in_column_layout():
    doc = _doc([
        {"type": "group", "id": "g", "box": [200, 50, 400, 700],
         "layout": {"kind": "column", "gap": 20},
         "children": [
             {"type": "rect", "id": "top", "box": [0, 0, 400, 100]},
             {"type": "rect", "id": "mid", "box": [0, 0, 400, 100]},
         ]},
        {"type": "connector", "id": "c",
         "from": {"object": "mid", "side": "north"}, "to": {"point": [900, 700]}},
    ])
    _, svg = _render(doc)
    # mid's arranged slot is y=120 group-local; group origin (200,50):
    # north anchor = (200 + 200, 50 + 120) = (400, 170).
    x1, y1, _, _ = _line_coords(svg)
    assert (x1, y1) == (400.0, 170.0)


def test_anchor_to_authored_box_child_is_unchanged():
    """Free (non-laid-out) groups keep the existing authored-box composition."""
    doc = _doc([
        {"type": "group", "id": "g", "box": [100, 100, 500, 400],
         "children": [{"type": "rect", "id": "a", "box": [40, 60, 100, 80]}]},
        {"type": "connector", "id": "c",
         "from": {"object": "a", "side": "east"}, "to": {"point": [900, 300]}},
    ])
    _, svg = _render(doc)
    x1, y1, _, _ = _line_coords(svg)
    assert (x1, y1) == (240.0, 200.0)  # (100+40+100, 100+60+40)


# --------------------------------------------------------------------------- #
# TX-7 — port anchors ride the object's rendered offset                        #
# --------------------------------------------------------------------------- #

def test_port_on_top_level_object_stays_in_the_committed_frame():
    """Frame pin: tests/fixtures/connectors.fg.yaml authors ports in the same
    frame as the box (page space at top level) — verbatim for offset (0,0)."""
    doc = _doc([
        {"type": "rect", "id": "n", "box": [40, 54, 80, 50],
         "ports": {"east": [120, 79]}},
        {"type": "connector", "id": "c",
         "from": {"object": "n", "port": "east"}, "to": {"point": [300, 79]}},
    ])
    _, svg = _render(doc)
    x1, y1, _, _ = _line_coords(svg)
    assert (x1, y1) == (120.0, 79.0)


def test_port_on_nested_object_is_offset_by_the_group_origin():
    doc = _doc([
        {"type": "group", "id": "g", "box": [600, 300, 300, 200],
         "children": [{"type": "rect", "id": "n", "box": [40, 54, 80, 50],
                       "ports": {"east": [120, 79]}}]},
        {"type": "connector", "id": "c",
         "from": {"object": "n", "port": "east"}, "to": {"point": [950, 700]}},
    ])
    _, svg = _render(doc)
    x1, y1, _, _ = _line_coords(svg)
    assert (x1, y1) == (720.0, 379.0)  # port + group origin (600,300)


def test_port_on_arranged_child_rides_the_arrangement():
    doc = _doc([
        {"type": "group", "id": "g", "box": [100, 100, 2000, 400],
         "layout": {"kind": "row", "gap": 50},
         "children": [
             {"type": "rect", "id": "a", "box": [0, 0, 300, 400]},
             {"type": "rect", "id": "b", "box": [0, 0, 300, 400],
              "ports": {"in": [0, 200]}},
         ]},
        {"type": "connector", "id": "c",
         "from": {"object": "b", "port": "in"}, "to": {"point": [900, 700]}},
    ])
    _, svg = _render(doc)
    # b's rendered shift = group origin (100,100) + arranged slot (350,0):
    # port [0,200] → (450, 300).
    x1, y1, _, _ = _line_coords(svg)
    assert (x1, y1) == (450.0, 300.0)
