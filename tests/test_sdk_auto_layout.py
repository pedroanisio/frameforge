#!/usr/bin/env python3
"""Automatic graph layout (roadmap item 1): positioning inferred from declared
edges, not chosen by hand. Graph.layout_kind() picks the algorithm from structure
and Graph.auto_layout()/render() apply it without the author selecting one."""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.sdk.topology import Graph  # noqa: E402


def test_layout_kind_inferred_from_structure():
    # no edges -> grid
    g = Graph().node("a").node("b").node("c")
    assert g.layout_kind() == "grid"
    # undirected tree -> radial (hub view)
    t = Graph().edge("a", "b").edge("a", "c")
    assert t._is_tree() and not t._is_directed() and t.layout_kind() == "radial"
    # directed acyclic -> layered hierarchy
    dag = Graph().edge("a", "b", directed=True).edge("b", "c", directed=True).edge("a", "c", directed=True)
    assert dag._is_dag() and dag.layout_kind() == "layered"
    # directed cycle -> spring (force-directed)
    cyc = Graph().edge("a", "b", directed=True).edge("b", "c", directed=True).edge("c", "a", directed=True)
    assert not cyc._is_dag() and cyc.layout_kind() == "spring"


def test_auto_layout_positions_every_node():
    for g in (
        Graph().node("a").node("b"),                                   # grid
        Graph().edge("root", "x").edge("root", "y").edge("root", "z"), # radial
        Graph().edge("a", "b", directed=True).edge("b", "c", directed=True),  # layered
        Graph().edge("a", "b").edge("b", "c").edge("c", "a"),          # spring (cycle)
    ):
        pos = g.auto_layout()
        assert set(pos) == {n.id for n in g.nodes}
        assert all(hasattr(p, "x") and hasattr(p, "y") for p in pos.values())


def test_render_without_positions_auto_layouts():
    g = Graph().edge("a", "b", directed=True).edge("b", "c", directed=True)
    group = g.render(box=[0, 0, 200, 120])           # no positions -> auto_layout
    assert group["type"] == "group"
    assert isinstance(group.get("children"), list) and group["children"]


def test_explicit_positions_still_honoured():
    from framegraph.sdk.geometry import Vec2
    g = Graph().edge("a", "b", directed=True)
    group = g.render({"a": Vec2(0, 0), "b": Vec2(1, 1)}, box=[0, 0, 100, 100])
    assert group["type"] == "group"


def test_auto_root_prefers_directed_source():
    g = Graph().edge("root", "child1", directed=True).edge("root", "child2", directed=True)
    assert g._auto_root() == "root"                  # in-degree-0 source
