"""Orthogonal connector routing — the elbow chain `route.kind: "orthogonal"` draws.

Before this module the kind was an advisory hint that never changed geometry:
point-less orthogonal routes rendered as straight diagonals and authors
hand-computed page-space elbows that went stale whenever a box moved. Explicit
`route.points` keep absolute precedence — this function is only consulted when
the author declared orthogonal intent and gave no waypoints.

The rule set (deterministic; exhaustively pinned by
tests/test_connector_orthogonal_routing.py):

  * A sided endpoint (attached to a box side) leaves that side perpendicularly
    through a stub tip `STUB` units out; free endpoints (explicit point, box
    centre, named port) take no stub.
  * Opposing sides on the connecting axis: midpoint rule — H-V-H (east/west)
    or V-H-V (north/south) splitting at the midpoint between the stub tips.
  * Same sides: route along the outermost stub line (the common clearance
    line beyond both tips, on the side the stubs point to).
  * Perpendicular sides: the single corner that extends the start stub's axis
    — unless that corner would double back through either stub, in which case
    the midpoint rule on the start axis applies (the stub jog stays visible:
    an endpoint always leaves its side perpendicularly).
  * One sided endpoint: its axis leads; the free end takes the single corner.
  * Two free endpoints: horizontal-first, elbow at (end.x, start.y).
  * Chains are deduped and same-direction collinear runs merged, so aligned
    endpoints collapse to the straight line they are. Direction REVERSALS are
    kept — they are the visible stub jog, not noise.
"""
from __future__ import annotations

STUB = 12.0

_DIR = {"north": (0.0, -1.0), "south": (0.0, 1.0),
        "east": (1.0, 0.0), "west": (-1.0, 0.0)}
_AXIS = {"north": "v", "south": "v", "east": "h", "west": "h"}
_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}

Point = tuple[float, float]


def route_orthogonal(start, start_side, end, end_side, stub: float = STUB) -> list[Point]:
    """Full drawn chain start → elbows… → end (≥ 2 points, axis-aligned)."""
    s: Point = (float(start[0]), float(start[1]))
    e: Point = (float(end[0]), float(end[1]))
    if s == e:
        return [s, e]
    ss = start_side if start_side in _DIR else None
    es = end_side if end_side in _DIR else None
    sp: Point = (s[0] + stub * _DIR[ss][0], s[1] + stub * _DIR[ss][1]) if ss else s
    ep: Point = (e[0] + stub * _DIR[es][0], e[1] + stub * _DIR[es][1]) if es else e
    return _clean([s] + _middle(sp, ss, ep, es) + [e])


def _middle(sp: Point, ss, ep: Point, es) -> list[Point]:
    if sp == ep:
        return [sp]
    if sp[0] == ep[0] or sp[1] == ep[1]:
        return [sp, ep]
    if ss and es:
        if _AXIS[ss] == _AXIS[es]:
            if es == _OPPOSITE[ss]:
                return _midpoint(sp, ep, _AXIS[ss])
            d = _DIR[ss]                                   # same side: outer line
            if _AXIS[ss] == "h":
                ox = max(sp[0], ep[0]) if d[0] > 0 else min(sp[0], ep[0])
                return [sp, (ox, sp[1]), (ox, ep[1]), ep]
            oy = max(sp[1], ep[1]) if d[1] > 0 else min(sp[1], ep[1])
            return [sp, (sp[0], oy), (ep[0], oy), ep]
        # perpendicular sides: single corner extending the start axis, IF it
        # leaves the start stub forward and arrives onto the end stub from
        # outside; else midpoint rule on the start axis.
        if _AXIS[ss] == "h":
            corner: Point = (ep[0], sp[1])
            leg1, dir1 = corner[0] - sp[0], _DIR[ss][0]
            leg2, dir2 = ep[1] - corner[1], -_DIR[es][1]
        else:
            corner = (sp[0], ep[1])
            leg1, dir1 = corner[1] - sp[1], _DIR[ss][1]
            leg2, dir2 = ep[0] - corner[0], -_DIR[es][0]
        ok1 = leg1 == 0 or (leg1 > 0) == (dir1 > 0)
        ok2 = leg2 == 0 or (leg2 > 0) == (dir2 > 0)
        if ok1 and ok2:
            return [sp, corner, ep]
        return _midpoint(sp, ep, _AXIS[ss])
    if ss:                                                 # free end follows the start axis
        corner = (ep[0], sp[1]) if _AXIS[ss] == "h" else (sp[0], ep[1])
        return [sp, corner, ep]
    if es:                                                 # approach runs along the end axis
        corner = (sp[0], ep[1]) if _AXIS[es] == "h" else (ep[0], sp[1])
        return [sp, corner, ep]
    return [sp, (ep[0], sp[1]), ep]                        # point→point: horizontal first


def _midpoint(p: Point, q: Point, axis: str) -> list[Point]:
    if axis == "h":
        m = (p[0] + q[0]) / 2.0
        return [p, (m, p[1]), (m, q[1]), q]
    m = (p[1] + q[1]) / 2.0
    return [p, (p[0], m), (q[0], m), q]


def _clean(chain: list[Point]) -> list[Point]:
    out: list[Point] = []
    for pt in chain:
        if not out or pt != out[-1]:
            out.append(pt)
    if len(out) == 1:
        return [out[0], out[0]]
    merged = [out[0]]
    for pt in out[1:]:
        if len(merged) >= 2:
            (x0, y0), (x1, y1) = merged[-2], merged[-1]
            x2, y2 = pt
            if (x0 == x1 == x2 and (y1 - y0) * (y2 - y1) > 0) or \
               (y0 == y1 == y2 and (x1 - x0) * (x2 - x1) > 0):
                merged[-1] = pt
                continue
        merged.append(pt)
    return merged
