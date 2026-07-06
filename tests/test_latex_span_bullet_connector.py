#!/usr/bin/env python3
"""LaTeX painter regressions found on the capability tour's PDF pixels.

Three defects, one review: (1) styled text spans were placed as one TikZ node
PER RUN, advanced by a character-count width guess — bold/mono runs overprinted
their neighbours everywhere rich paragraphs appear; (2) `bullet_list` treated
`gap` as the full line stride while the SVG proxy treats it as inter-item pitch
floored at the line height — small authored gaps collapsed items onto one line;
(3) typed connectors with `{object, port/side}` anchors and a route *dict*
(`{type, points}`) were silently skipped, because anchors could not resolve ids
and only a legacy route list was read.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from framegraph.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402


def _fig():
    color = ColorResolver({})
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


def test_span_runs_render_as_one_tex_node_with_inline_switches():
    tex = _fig().render({
        "type": "text", "box": [0, 0, 200, 20],
        "spans": ["with styled ",
                  {"text": "spans",
                   "style": {"font_weight": 700, "color": "#3B6EA5"}},
                  " inside one box."],
        "style": {"font_size": 11},
    })
    assert tex.count("\\node") == 1, "one node — TeX owns the run advances"
    assert "\\bfseries" in tex
    assert "with styled" in tex and "inside one box." in tex
    # \color takes the bare xcolor expression; a double-braced argument sends
    # the TeX tokenizer into an input-stack loop (found compiling the tour).
    assert "\\color{rgb,255:red,59;green,110;blue,165}" in tex
    assert "\\color{{" not in tex


def test_bullet_list_gap_is_floored_at_line_height():
    tex = _fig().render({
        "type": "bullet_list", "box": [0, 0, 200, 60],
        "items": ["alpha", "beta"], "gap": 4,
        "style": {"font_size": 10},
    })
    marker_ys = sorted({float(m) for m in
                        re.findall(r"at \(0,([0-9.]+)\)", tex)})
    assert len(marker_ys) == 2
    # proxy semantics: stride = max(gap, line height); never the raw 4pt gap
    assert marker_ys[1] - marker_ys[0] >= 10.0


def test_connector_resolves_object_anchors_and_route_dict():
    fig = _fig()
    fig.begin_page([
        {"type": "rect", "id": "a", "box": [40, 54, 80, 50],
         "ports": {"east": [120, 79]}},
        {"type": "rect", "id": "b", "box": [240, 54, 80, 50]},
    ])
    tex = fig.render({
        "type": "connector",
        "from": {"object": "a", "port": "east"},
        "to": {"object": "b", "side": "west"},
        "route": {"type": "orthogonal", "points": [[180, 79], [180, 100]]},
    })
    assert "(120,79)" in tex and "(240,79)" in tex     # port + west side
    assert "(180,79)" in tex and "(180,100)" in tex    # route dict points
    assert "->" in tex


def test_connector_label_dict_renders_its_text_not_the_repr():
    fig = _fig()
    fig.begin_page([{"type": "rect", "id": "a", "box": [0, 0, 10, 10]}])
    tex = fig.render({
        "type": "connector",
        "from": {"object": "a", "side": "east"},
        "to": {"point": [60, 5]},
        "label": {"text": "wired", "box": [20, 0, 20, 10]},
    })
    assert "wired" in tex and "'text'" not in tex


def test_connector_resolves_canonical_ref_anchor_key():
    """The model normalises `object:` to `ref:` on validation — the painter
    must resolve the canonical key, not only the authoring alias (a connector
    that round-trips through the model was silently skipped)."""
    fig = _fig()
    fig.begin_page([
        {"type": "rect", "id": "a", "box": [0, 0, 50, 26],
         "ports": {"east": [50, 13]}},
        {"type": "rect", "id": "b", "box": [100, 60, 50, 26]},
    ])
    tex = fig.render({
        "type": "connector",
        "from": {"ref": "a", "port": "east"},
        "to": {"ref": "b", "side": "west"},
        "route": {"kind": "orthogonal", "points": [[75, 13], [75, 73]]},
    })
    assert "(50,13)" in tex and "(100,73)" in tex
    assert "->" in tex


def test_layout_group_children_are_arranged_not_stacked():
    """A group carrying `layout:` must run the shared LayoutEngine (as the
    SVG proxy does) — raw [0,0,w,h] children previously all painted at the
    group origin, collapsing a 3x2 grid into one visible tile."""
    tex = _fig().render({
        "type": "group", "box": [10, 20, 160, 60],
        "layout": {"kind": "grid", "columns": 3, "gap": 6},
        "children": [{"type": "rect", "box": [0, 0, 40, 24],
                      "fill": "#111111"} for _ in range(6)],
    })
    assert tex.count("rectangle") == 6
    shifts = set(re.findall(r"shift=\{\(([-0-9.]+,[-0-9.]+)\)\}", tex))
    assert len(shifts) >= 5, f"children not spread: {shifts}"
