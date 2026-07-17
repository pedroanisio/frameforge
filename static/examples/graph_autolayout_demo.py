#!/usr/bin/env python3
"""Declarative graph auto-layout — the render-time bridge (roadmap item 1).

`sdk.topology.Graph` computes node placements from declared edges; this
client shows the *declarative* form that `sdk.expand` lowers at expansion
time: a `type: graph` object (nodes + edges + algorithm) becomes a
positioned core `group`, no coordinates baked by hand and no renderer
contract change (§A.0). One page, four panels — the four inferred
algorithms plus an explicit override — each a graph laid out from the same
kind of declaration.

Writes ``_tmp/graph-autolayout/`` (YAML + SVG). The MCP run contract is
``build()``; the canonical fixture ``tests/fixtures/graph-autolayout.fg.yaml``
is this document verbatim (post-expansion).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import expand, render_page_svgs, serialize  # noqa: E402
from frameforge.sdk.model import HEAD_VERSION  # noqa: E402
from frameforge.sdk.topology import Graph  # noqa: E402

_SANS = ["DejaVu Sans", "Arial", "sans-serif"]


def _label(x, y, text):
    return {"type": "text", "box": [x, y, 420, 18], "text": text,
            "style": {"font_family": _SANS, "font_size": 13,
                      "font_weight": 700, "color": "ink",
                      "white_space": "nowrap"}}


def _pipeline():
    g = Graph()
    for nid, lbl in (("in", "Ingest"), ("va", "Validate"), ("ex", "Expand"),
                     ("re", "Render"), ("ck", "Verify")):
        g.node(nid, lbl)
    for a, b in (("in", "va"), ("va", "ex"), ("ex", "re"), ("re", "ck"),
                 ("va", "ck")):
        g.edge(a, b, directed=True)
    return g


def _hub():
    g = Graph().node("core", "Model")
    for sat in ("SDK", "MCP", "CLI", "Vision", "Coach"):
        g.node(sat, sat)
        g.edge("core", sat)
    return g


def _mesh():
    g = Graph()
    for n in "abcdef":
        g.node(n, n.upper())
    for a, b in (("a", "b"), ("b", "c"), ("c", "a"), ("c", "d"),
                 ("d", "e"), ("e", "f"), ("f", "d")):
        g.edge(a, b)
    return g


def build():
    """MCP contract: the graph auto-layout showcase (post-expansion)."""
    objects = [
        {"type": "rect", "box": [0, 0, 960, 540], "fill": "paper",
         "decorative": True},
        {"type": "text", "box": [40, 24, 880, 20],
         "text": "Declarative graph auto-layout — computed at expansion, "
                 "not by hand",
         "style": {"font_family": _SANS, "font_size": 13, "font_weight": 700,
                   "color": "ink", "white_space": "nowrap"}},

        # A directed acyclic pipeline → `auto` infers `layered` (Sugiyama)
        _label(40, 60, "auto → layered (a DAG becomes a hierarchy)"),
        _pipeline().to_object(box=[40, 84, 420, 180], algorithm="auto",
                              id="g-pipeline", node_fill="#0f7d88",
                              edge_color="#94a3b8"),

        # An undirected star → `auto` infers `radial` (hub view)
        _label(500, 60, "auto → radial (a tree becomes a hub)"),
        _hub().to_object(box=[500, 84, 420, 180], algorithm="auto",
                         id="g-hub", node_fill="#b5642c",
                         edge_color="#cbb39a"),

        # A cyclic mesh → `auto` infers `spring` (force-directed)
        _label(40, 300, "auto → spring (a cyclic mesh relaxes)"),
        _mesh().to_object(box=[40, 324, 420, 180], algorithm="auto",
                          id="g-mesh", node_fill="#7c3aed",
                          edge_color="#c3a9ea"),

        # The same pipeline forced circular — the algorithm is declarable
        _label(500, 300, "explicit: circular (override the inference)"),
        _pipeline().to_object(box=[500, 324, 420, 180], algorithm="circular",
                              id="g-circ", node_fill="#1d4ed8",
                              edge_color="#9db4ec"),
    ]
    doc = {"dsl": "FrameForge", "version": HEAD_VERSION,
           "title": "graph auto-layout showcase", "profile": "diagram",
           "defs": {"tokens": {"colors": {"paper": "#fcfbf8",
                                          "ink": "#1d1e22"}}},
           "pages": [{"mode": "page", "id": "graph-autolayout",
                      "canvas": {"size": [960, 540], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "main", "objects": objects}]}]}
    # lower the graph objects to positioned groups; the returned doc is
    # core-only and validated
    return expand(doc).document.model_dump(by_alias=True, exclude_none=True)


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "graph-autolayout")
    os.makedirs(out, exist_ok=True)
    doc = build()
    with open(os.path.join(out, "graph-autolayout.fg.yaml"), "w",
              encoding="utf-8") as fh:
        fh.write(serialize(doc))
    svg = render_page_svgs(doc, base_dir=out)[0]
    with open(os.path.join(out, "graph-autolayout.svg"), "w",
              encoding="utf-8") as fh:
        fh.write(svg)
    print(f"Wrote the showcase to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
