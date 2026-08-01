"""`route.kind: "orthogonal"` computes real elbows when no waypoints are given.

Before this, `kind` was an advisory hint that never changed drawn geometry —
migrated production decks authoring `route: {type: orthogonal}` with no points
(e.g. tests/fixtures/newset/code-base-mapper.deck.v2.fg.yaml) silently got
straight diagonals, and authors hand-computed `hv`/`vh` elbows in page space
that go stale the moment a box moves (2026-07-27 incident, second round).

Contract (rendering/domain/routing.py — deterministic, exhaustively pinned):
  * gate: kind == "orthogonal" AND no explicit points; authored `route.points`
    ALWAYS win verbatim; `straight`/`curved`/absent kinds are unchanged.
  * sided endpoints leave their box side perpendicularly via a STUB=12.0 tip;
  * opposing sides route via the midpoint between stub tips (H-V-H / V-H-V);
    same sides via the outermost stub line; perpendicular sides via the single
    corner that extends the start stub's axis, falling back to the midpoint
    rule when that corner would double back through either stub; free
    endpoints (point / centre / named port) take no stub — a lone sided
    endpoint imposes its axis, two free endpoints go horizontal-first;
  * chains are deduped and collinear-merged, so aligned endpoints collapse to
    the straight line they are.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # evict a models-module shadow
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge_render.domain.routing import route_orthogonal  # noqa: E402
from tooling.render_fixtures import Renderer  # noqa: E402


# --------------------------------------------------------------------------- #
#  Pure rule set (STUB = 12.0)                                                 #
# --------------------------------------------------------------------------- #
def test_opposing_horizontal_sides_route_via_midpoint():
    # east → west, stub tips at x=112 / x=188, midpoint x=150
    assert route_orthogonal((100, 50), "east", (200, 90), "west") == \
        [(100.0, 50.0), (150.0, 50.0), (150.0, 90.0), (200.0, 90.0)]


def test_opposing_horizontal_reversed():
    assert route_orthogonal((200, 90), "west", (100, 50), "east") == \
        [(200.0, 90.0), (150.0, 90.0), (150.0, 50.0), (100.0, 50.0)]


def test_opposing_vertical_sides_route_via_midpoint():
    # south → north, stub tips at y=112 / y=188, midpoint y=150
    assert route_orthogonal((50, 100), "south", (90, 200), "north") == \
        [(50.0, 100.0), (50.0, 150.0), (90.0, 150.0), (90.0, 200.0)]


def test_same_side_south_routes_via_outermost_stub_line():
    # stub tips y=112 / y=152 → clearance line at max = 152
    assert route_orthogonal((50, 100), "south", (90, 140), "south") == \
        [(50.0, 100.0), (50.0, 152.0), (90.0, 152.0), (90.0, 140.0)]


def test_same_side_north_uses_min():
    assert route_orthogonal((50, 100), "north", (90, 140), "north") == \
        [(50.0, 100.0), (50.0, 88.0), (90.0, 88.0), (90.0, 140.0)]


def test_same_side_east_uses_max_x():
    assert route_orthogonal((100, 50), "east", (140, 90), "east") == \
        [(100.0, 50.0), (152.0, 50.0), (152.0, 90.0), (140.0, 90.0)]


def test_perpendicular_sides_single_corner_when_respected():
    # east → north: corner (200, 50) extends the start stub and arrives onto
    # the end stub from outside — one elbow.
    assert route_orthogonal((100, 50), "east", (200, 120), "north") == \
        [(100.0, 50.0), (200.0, 50.0), (200.0, 120.0)]


def test_perpendicular_sides_fall_back_to_midpoint_when_corner_doubles_back():
    # end is BEHIND the east stub → the single corner would reverse through it;
    # midpoint rule on the start axis: midx = (112 + 60) / 2 = 86. The +x stub
    # jog to 112 stays visible — the endpoint leaves its side perpendicularly.
    assert route_orthogonal((100, 50), "east", (60, 120), "north") == \
        [(100.0, 50.0), (112.0, 50.0), (86.0, 50.0), (86.0, 108.0),
         (60.0, 108.0), (60.0, 120.0)]


def test_sided_start_to_free_point_extends_start_axis():
    assert route_orthogonal((100, 50), "east", (200, 120), None) == \
        [(100.0, 50.0), (200.0, 50.0), (200.0, 120.0)]


def test_free_start_to_sided_end_arrives_along_end_axis():
    # west end: approach must run horizontally into the stub
    assert route_orthogonal((100, 50), None, (200, 120), "west") == \
        [(100.0, 50.0), (100.0, 120.0), (200.0, 120.0)]


def test_point_to_point_goes_horizontal_first():
    assert route_orthogonal((10, 20), None, (50, 80), None) == \
        [(10.0, 20.0), (50.0, 20.0), (50.0, 80.0)]


def test_aligned_endpoints_collapse_to_the_straight_line():
    assert route_orthogonal((100, 50), "east", (200, 50), "west") == \
        [(100.0, 50.0), (200.0, 50.0)]


def test_coincident_endpoints_stay_a_two_point_chain():
    assert route_orthogonal((30, 30), None, (30, 30), None) == \
        [(30.0, 30.0), (30.0, 30.0)]


def test_determinism():
    a = route_orthogonal((100, 50), "east", (60, 120), "north")
    b = route_orthogonal((100, 50), "east", (60, 120), "north")
    assert a == b


# --------------------------------------------------------------------------- #
#  Renderer integration (gate + precedence + markers)                          #
# --------------------------------------------------------------------------- #
def _render(objects):
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [400, 200], "units": "px"},
        "layers": [{"id": "l", "objects": objects}],
    }]}
    r = Renderer(doc, ".")
    return "".join(r.render_page(doc["pages"][0])), r.diagnostics


def _boxes():
    return [{"type": "rect", "id": "a", "box": [20, 60, 80, 50], "fill": "#eee"},
            {"type": "rect", "id": "b", "box": [280, 20, 80, 50], "fill": "#eee"}]


def _polyline_points(svg):
    m = re.search(r'<polyline points="([^"]+)"', svg)
    assert m, f"no polyline in: {svg[:400]}"
    return [tuple(float(v) for v in p.split(",")) for p in m.group(1).split()]


def _axis_aligned(pts):
    return all(x1 == x2 or y1 == y2 for (x1, y1), (x2, y2) in zip(pts, pts[1:]))


def test_pointless_orthogonal_route_draws_axis_aligned_elbows():
    svg, _ = _render(_boxes() + [{
        "type": "connector", "id": "c",
        "from": {"ref": "a", "side": "east"}, "to": {"ref": "b", "side": "west"},
        "route": {"kind": "orthogonal"}, "stroke": "#333"}])
    pts = _polyline_points(svg)
    assert len(pts) >= 3 and _axis_aligned(pts)
    assert pts[0] == (100.0, 85.0) and pts[-1] == (280.0, 45.0)   # side midpoints


def test_legacy_type_key_is_honored_on_the_raw_dict_path():
    svg, _ = _render(_boxes() + [{
        "type": "connector", "id": "c",
        "from": {"ref": "a", "side": "east"}, "to": {"ref": "b", "side": "west"},
        "route": {"type": "orthogonal"}, "stroke": "#333"}])
    assert _axis_aligned(_polyline_points(svg))


def test_explicit_points_always_win_verbatim():
    svg, _ = _render(_boxes() + [{
        "type": "connector", "id": "c",
        "from": {"ref": "a", "side": "east"}, "to": {"ref": "b", "side": "west"},
        "route": {"kind": "orthogonal", "points": [[150, 150], [250, 150]]},
        "stroke": "#333"}])
    assert _polyline_points(svg) == [
        (100.0, 85.0), (150.0, 150.0), (250.0, 150.0), (280.0, 45.0)]


def test_straight_kind_and_absent_route_stay_two_point_lines():
    for route in ({"kind": "straight"}, None):
        obj = {"type": "connector", "id": "c",
               "from": {"ref": "a", "side": "east"}, "to": {"ref": "b", "side": "west"},
               "stroke": "#333"}
        if route:
            obj["route"] = route
        svg, _ = _render(_boxes() + [obj])
        assert "<polyline" not in svg and "<line " in svg


def test_arrow_marker_attaches_to_the_elbowed_chain():
    svg, diags = _render(_boxes() + [{
        "type": "connector", "id": "c",
        "from": {"ref": "a", "side": "east"}, "to": {"ref": "b", "side": "west"},
        "route": {"kind": "orthogonal"},
        "stroke": "#333", "stroke_style": {"arrow_end": True}}])
    assert 'marker-end="url(#' in svg and _axis_aligned(_polyline_points(svg))
    assert not [w for w in diags["warnings"] if w["kind"] == "arrow_marker_fallback"]


def test_named_port_endpoint_is_free_no_stub():
    # port resolves to an exact point: no side, so no stub jog at that end —
    # the sided start imposes its axis and the chain stays axis-aligned.
    boxes = _boxes()
    boxes[1]["ports"] = {"in": [280, 30]}
    svg, _ = _render(boxes + [{
        "type": "connector", "id": "c",
        "from": {"ref": "a", "side": "east"}, "to": {"ref": "b", "port": "in"},
        "route": {"kind": "orthogonal"}, "stroke": "#333"}])
    pts = _polyline_points(svg)
    assert _axis_aligned(pts) and pts[-1] == (280.0, 30.0)
