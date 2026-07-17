"""Declarative graph auto-layout at expansion time (roadmap item 1).

The missing render-time bridge: `sdk.topology.Graph` already computes node
placements from declared edges, but only author-side (call a layout method,
bake the coordinates). This wires it as a DECLARATIVE, expansion-tier form —
a grammar-level ``type: graph`` object (nodes + edges + algorithm) that
``sdk.expand`` lowers into a positioned core ``group`` (§A.0: the SDK
computes, the document receives plain geometry). No schema change: `graph`
is a pre-expansion authoring type, exactly like `use`/`component`, and never
reaches the validated document.

Runs under pytest or standalone (``uv run python tests/test_sdk_graph_expand.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.sdk import expand, render_pages_with_stats  # noqa: E402
from frameforge.sdk.model import HEAD_VERSION, validate_document  # noqa: E402


def _doc(graph_obj):
    return {"dsl": "FrameForge", "version": HEAD_VERSION, "title": "g",
            "profile": "diagram",
            "pages": [{"mode": "page", "id": "p",
                       "canvas": {"size": [400, 300], "units": "px"},
                       "rendering": {"coordinate_mode": "absolute"},
                       "layers": [{"id": "main", "objects": [graph_obj]}]}]}


def _graph(**fields):
    base = {"type": "graph", "box": [20, 20, 360, 260],
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"},
                      {"id": "c", "label": "C"}],
            "edges": [{"from": "a", "to": "b", "directed": True},
                      {"from": "a", "to": "c", "directed": True}]}
    base.update(fields)
    return base


def _expanded_objects(doc):
    ex = expand(doc).document.model_dump(by_alias=True, exclude_none=True)
    return ex, ex["pages"][0]["layers"][0]["objects"]


# ── the bridge ──────────────────────────────────────────────────────────


def test_graph_object_lowers_to_a_positioned_group():
    ex, objs = _expanded_objects(_doc(_graph(id="g1")))
    assert len(objs) == 1
    grp = objs[0]
    assert grp["type"] == "group" and grp["id"] == "g1"
    assert grp["box"] == [20, 20, 360, 260]
    assert all(o.get("type") != "graph" for o in objs), "graph must be lowered"
    kinds = {c["type"] for c in grp["children"]}
    assert "ellipse" in kinds, "nodes become ellipses"
    assert "polyline" in kinds, "edges become polylines"
    validate_document(ex)             # the lowered doc is core-only + valid


def test_node_and_edge_counts_survive():
    _, objs = _expanded_objects(_doc(_graph()))
    children = objs[0]["children"]
    ellipses = [c for c in children if c["type"] == "ellipse"]
    # each edge is a line polyline; a directed edge adds a closed arrowhead
    lines = [c for c in children
             if c["type"] == "polyline" and not c.get("closed")]
    assert len(ellipses) == 3               # a, b, c
    assert len(lines) == 2                  # a→b, a→c


def test_labels_reach_the_children():
    _, objs = _expanded_objects(_doc(_graph()))
    texts = [c.get("text") for c in objs[0]["children"] if c["type"] == "text"]
    assert {"A", "B", "C"} <= set(texts)


def test_children_are_fitted_inside_the_box():
    _, objs = _expanded_objects(_doc(_graph(box=[20, 20, 360, 260])))
    for c in objs[0]["children"]:
        if c["type"] == "ellipse":
            cx, cy = c["center"]
            assert 0 <= cx <= 360 and 0 <= cy <= 260, "node centre in local box"


def test_explicit_algorithm_is_honoured():
    """A directed acyclic graph auto-infers `layered`; forcing `circular`
    must change the geometry."""
    auto = _expanded_objects(_doc(_graph(algorithm="layered")))[1][0]
    circ = _expanded_objects(_doc(_graph(algorithm="circular")))[1][0]
    auto_pts = sorted(tuple(c["center"]) for c in auto["children"]
                      if c["type"] == "ellipse")
    circ_pts = sorted(tuple(c["center"]) for c in circ["children"]
                      if c["type"] == "ellipse")
    assert auto_pts != circ_pts


def test_absolute_node_positions_override_the_layout():
    """`pos` on a node pins it — the layout must place it there (§A.0
    override)."""
    g = _graph(algorithm="grid",
               nodes=[{"id": "a", "label": "A", "pos": [0, 0]},
                      {"id": "b", "label": "B", "pos": [100, 100]}],
               edges=[])
    _, objs = _expanded_objects(_doc(g))
    # nodes render in declaration order → ellipse[0] is 'a' (pinned [0,0]),
    # ellipse[1] is 'b' (pinned [100,100]); after the box-fit b sits down-right
    ellipses = [c for c in objs[0]["children"] if c["type"] == "ellipse"]
    (ax, ay), (bx, by) = ellipses[0]["center"], ellipses[1]["center"]
    assert bx > ax and by > ay, "the pinned far corner must stay far"


def test_expansion_is_deterministic():
    a, _ = _expanded_objects(_doc(_graph(algorithm="spring")))
    b, _ = _expanded_objects(_doc(_graph(algorithm="spring")))
    assert a == b


def test_empty_graph_is_an_empty_group_not_a_crash():
    _, objs = _expanded_objects(_doc(_graph(nodes=[], edges=[])))
    assert objs[0]["type"] == "group"
    assert objs[0].get("children", []) == []


def test_graph_absence_leaves_the_document_untouched():
    """A document with no graph/use/component must pass through expand
    byte-identical (the golden-stability guard)."""
    plain = {"dsl": "FrameForge", "version": HEAD_VERSION, "title": "plain",
             "profile": "diagram",
             "pages": [{"mode": "page", "id": "p",
                        "canvas": {"size": [100, 100], "units": "px"},
                        "rendering": {"coordinate_mode": "absolute"},
                        "layers": [{"id": "m", "objects": [
                            {"type": "rect", "box": [0, 0, 50, 50],
                             "fill": "#111111"}]}]}]}
    out = expand(plain).document.model_dump(by_alias=True, exclude_none=True)
    assert out["pages"][0]["layers"][0]["objects"] == \
        plain["pages"][0]["layers"][0]["objects"]


# ── the render gate ─────────────────────────────────────────────────────


def test_expanded_graph_renders_clean():
    ex, _ = _expanded_objects(_doc(_graph()))
    svgs, stats = render_pages_with_stats(ex, base_dir=str(ROOT))
    assert svgs and stats.get("uncontained", 0) == 0


def test_committed_showcase_fixture_renders_clean():
    import yaml
    doc = yaml.safe_load(
        (ROOT / "tests" / "fixtures" / "graph-autolayout.fg.yaml")
        .read_text(encoding="utf-8"))
    svgs, stats = render_pages_with_stats(doc, base_dir=str(ROOT))
    assert svgs
    assert stats.get("clipped", 0) == 0
    assert stats.get("uncontained", 0) == 0


def test_graph_to_object_round_trips_through_expand():
    from frameforge.sdk.topology import Graph
    g = Graph().node("a", "A").node("b", "B").edge("a", "b", directed=True)
    obj = g.to_object(box=[0, 0, 200, 120], algorithm="layered", id="rt")
    assert obj["type"] == "graph" and obj["id"] == "rt"
    _, objs = _expanded_objects(_doc(obj))
    assert objs[0]["type"] == "group" and objs[0]["id"] == "rt"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
