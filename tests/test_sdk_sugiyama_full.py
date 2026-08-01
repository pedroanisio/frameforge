#!/usr/bin/env python3
"""Full four-stage Sugiyama absorption contract (GitHub #30)."""
from __future__ import annotations

import pytest

from frameforge_sdk.sugiyama import SugiyamaConfig, _assign_layers, _count_crossings_between_layers, _median, _remove_cycles, sugiyama_layout


def test_each_sugiyama_stage_enforces_its_structural_contract():
    dag, reversed_edges = _remove_cycles(
        ["a", "b", "c", "x"],
        [("a", "b"), ("b", "c"), ("c", "a"), ("x", "x")],
    )
    assert len(reversed_edges & {("a", "b"), ("b", "c"), ("c", "a")}) == 1
    assert ("x", "x") in reversed_edges
    assert ("x", "x") not in dag

    layered = _assign_layers(
        ["a", "b", "c", "d"],
        [("a", "b"), ("b", "c"), ("c", "d"), ("a", "d")],
    )
    assert [layered.layer[node] for node in ("a", "b", "c", "d")] == [0, 1, 2, 3]
    assert len([node for node in layered.nodes if layered.is_dummy.get(node)]) == 2

    with pytest.raises(ValueError, match="cycles"):
        _assign_layers(["a", "b"], [("a", "b"), ("b", "a")])


def test_crossing_measurement_and_median_helpers_are_exact():
    assert _count_crossings_between_layers(
        ["a", "b"], ["c", "d"], {"a": ["c"], "b": ["d"]}
    ) == 0
    assert _count_crossings_between_layers(
        ["a", "b"], ["c", "d"], {"a": ["d"], "b": ["c"]}
    ) == 1
    assert _median([]) == -1.0
    assert _median([1, 5, 9]) == 5.0
    assert _median([1, 5, 9, 13]) == 7.0


def test_sugiyama_is_deterministic_and_restores_cycle_edge_direction():
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("a", "d")]

    first = sugiyama_layout(nodes, edges)
    second = sugiyama_layout(nodes, edges)

    assert first == second
    assert first.reversed_edges
    assert set(first.positions) == set(nodes)
    assert set(first.edges) == set(edges)
    for edge in edges:
        assert first.edges[edge][0] == first.positions[edge[0]]
        assert first.edges[edge][-1] == first.positions[edge[1]]


def test_sugiyama_subdivides_long_edges_and_minimizes_crossings():
    nodes = ["top", "left", "right", "bottom"]
    edges = [
        ("top", "left"),
        ("top", "right"),
        ("left", "bottom"),
        ("right", "bottom"),
        ("top", "bottom"),
    ]

    result = sugiyama_layout(
        nodes,
        edges,
        config=SugiyamaConfig(layer_height=90, node_width=80, node_gap=24),
    )

    assert result.crossings == 0
    # One dummy on the single intermediate layer yields source, bend, target.
    assert len(result.edges[("top", "bottom")]) == 3
    assert [result.positions[n][1] for n in ("top", "left", "bottom")] == [0, 90, 180]
    assert result.layers[0] == ["top"]
    assert result.layers[-1] == ["bottom"]


def test_brandes_koepf_assignment_is_compact_normalized_and_configurable():
    chain = sugiyama_layout(["a", "b", "c"], [("a", "b"), ("b", "c")])
    assert max(chain.positions[node][0] for node in chain.positions) == pytest.approx(0.0)

    configured = sugiyama_layout(
        ["a", "b"],
        [("a", "b")],
        config=SugiyamaConfig(layer_height=200.0),
    )
    assert configured.positions["b"][1] - configured.positions["a"][1] == pytest.approx(200.0)

    disconnected = sugiyama_layout(["a", "b"], [])
    assert disconnected.layers == [["a", "b"]]
    assert all(position[1] == 0.0 for position in disconnected.positions.values())
