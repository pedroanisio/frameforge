"""recipe.graph — generic dependency-graph helpers.

One implementation of topological order and cycle detection, shared by both
linking levels: steps within a recipe and recipes within a book. ``edges[n]`` is
the list of nodes ``n`` depends on (i.e. that must come *before* ``n``). Unknown
dependencies (ids not in ``nodes``) are ignored here — callers report those
separately as dangling references.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping


def find_cycle(nodes: Iterable[str], edges: Mapping[str, list[str]]) -> list[str] | None:
    """Return one dependency cycle as a path (``[a, b, a]``), or None if acyclic."""
    node_list = list(nodes)
    known = set(node_list)
    WHITE, GREY, BLACK = 0, 1, 2
    color = dict.fromkeys(node_list, WHITE)
    stack: list[str] = []

    def visit(n: str) -> list[str] | None:
        color[n] = GREY
        stack.append(n)
        for m in edges.get(n, []):
            if m not in known:
                continue
            if color[m] == GREY:
                return stack[stack.index(m):] + [m]
            if color[m] == WHITE:
                found = visit(m)
                if found:
                    return found
        stack.pop()
        color[n] = BLACK
        return None

    for node in node_list:
        if color[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def topo_order(nodes: Iterable[str], edges: Mapping[str, list[str]]) -> list[str]:
    """Kahn's algorithm: dependencies first, stable in input order among ready
    nodes. Assumes acyclic (callers reject cycles); any cycle remnant is
    appended in input order so the result is always a permutation of ``nodes``."""
    node_list = list(nodes)
    known = set(node_list)
    deps = {n: {d for d in edges.get(n, []) if d in known} for n in node_list}
    order: list[str] = []
    ready = [n for n in node_list if not deps[n]]
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in node_list:
            if n in deps[m]:
                deps[m].discard(n)
                if not deps[m] and m not in order and m not in ready:
                    ready.append(m)
    if len(order) != len(node_list):
        order += [n for n in node_list if n not in order]
    return order
