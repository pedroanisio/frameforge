"""Planar geometry kernel — booleans, offset, surgery, regions (issue #45, W1).

One expansion-tier kernel closes five parity rows. Per §A.0 doctrine the SDK
computes and the document receives plain ``path`` objects:

- :func:`union` / :func:`intersect` / :func:`subtract` / :func:`divide` —
  polygon booleans (Greiner–Hormann on flattened rings; AI-04 Pathfinder,
  AI-05 Shape Builder's merge gesture);
- :func:`offset_polygon` — closed-polygon outward/inward offset with miter
  corners (AI-47; the open-path case is W2's :func:`~frameforge.sdk.outline.
  stroke_outline`);
- :func:`split_at` / :func:`cut_along` — path surgery (AI-06 Scissors &
  Knife): arc-length split and cut-by-line via half-plane booleans;
- :func:`fill_regions` — every bounded region of a small shape overlay as
  its own fillable face (AI-17 Live Paint), computed as boolean atoms.

Scope, stated honestly: inputs are FLATTENED rings (lists of points; run
curves through the geometry helpers first). Degenerate inputs (shared
edges, touching vertices) are handled by a tiny deterministic perturbation
and answers carry that tolerance. Holes are EMITTED (even-odd, multi-ring
paths) but holed shapes are not re-consumed by further booleans;
self-intersection surgery on pathological offsets is out of scope. This is
an authoring kernel, not a CAD engine. Everything is stdlib-only and
deterministic — the same call always returns the same rings.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

__all__ = ["contains", "cut_along", "divide", "fill_regions", "intersect",
           "offset_polygon", "ring_area", "split_at", "subtract", "to_path",
           "union"]

Pt = tuple[float, float]
Ring = list[Pt]
_EPS = 1e-9


# ── ring primitives ─────────────────────────────────────────────────────


def ring_area(ring: Sequence[Sequence[float]]) -> float:
    """Signed shoelace area (positive = counter-clockwise in math axes)."""
    total = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _pt_in_ring(pt: Pt, ring: Ring) -> bool:
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) / (y2 - y1) * (x2 - x1)
            if x < xin:
                inside = not inside
    return inside


def contains(rings: Sequence[Ring], pt: Sequence[float]) -> bool:
    """Even-odd membership of a point in a multi-ring shape."""
    p = (float(pt[0]), float(pt[1]))
    return sum(_pt_in_ring(p, r) for r in rings) % 2 == 1


def _norm(ring: Sequence[Sequence[float]]) -> Ring:
    out = [(float(p[0]), float(p[1])) for p in ring]
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


# ── Greiner–Hormann pairwise clipping ───────────────────────────────────


class _V:
    __slots__ = ("x", "y", "nxt", "prv", "neighbour", "intersect", "entry",
                 "visited")

    def __init__(self, x: float, y: float):
        self.x, self.y = x, y
        self.nxt = self.prv = None
        self.neighbour = None
        self.intersect = False
        self.entry = False
        self.visited = False


def _build(ring: Ring) -> _V:
    head = None
    prev = None
    for x, y in ring:
        v = _V(x, y)
        if head is None:
            head = v
            v.nxt = v.prv = v
        else:
            v.prv, v.nxt = prev, head
            prev.nxt = v
            head.prv = v
        prev = v
    return head

def _walk(head: _V):
    v = head
    while True:
        yield v
        v = v.nxt
        if v is head:
            break


def _seg_intersect(p1: Pt, p2: Pt, q1: Pt, q2: Pt):
    """Proper intersection of open segments; returns (point, ta, tb) or None."""
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = q2[0] - q1[0], q2[1] - q1[1]
    den = d1x * d2y - d1y * d2x
    if abs(den) < _EPS:
        return None
    ta = ((q1[0] - p1[0]) * d2y - (q1[1] - p1[1]) * d2x) / den
    tb = ((q1[0] - p1[0]) * d1y - (q1[1] - p1[1]) * d1x) / den
    if _EPS < ta < 1 - _EPS and _EPS < tb < 1 - _EPS:
        return (p1[0] + ta * d1x, p1[1] + ta * d1y), ta, tb
    return None


def _degenerate(a: Ring, b: Ring) -> bool:
    """Any b-vertex on an a-edge (or vice versa) breaks GH — detect it."""
    def on_edge(pt, ring):
        for i in range(len(ring)):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % len(ring)]
            cross = (x2 - x1) * (pt[1] - y1) - (y2 - y1) * (pt[0] - x1)
            if abs(cross) < 1e-7:
                dot = (pt[0] - x1) * (x2 - x1) + (pt[1] - y1) * (y2 - y1)
                if -1e-7 <= dot <= (x2 - x1) ** 2 + (y2 - y1) ** 2 + 1e-7:
                    return True
        return False
    return any(on_edge(p, a) for p in b) or any(on_edge(p, b) for p in a)


_NUDGES = ((1.0, 1.618), (-1.0, -1.618), (1.0, -1.618), (-1.0, 1.618))


def _perturb(ring: Ring, scale: float, attempt: int) -> Ring:
    # deterministic nudge; the direction cycles so a touching pair is pushed
    # INTO engagement on some attempt regardless of which side it touches
    ux, uy = _NUDGES[attempt % 4]
    mag = 1.0000003e-6 * scale * (1 + attempt // 4)
    return [(x + ux * mag, y + uy * mag) for x, y in ring]


def _insert_intersections(a_head: _V, b_head: _V) -> int:
    count = 0
    a_edges = [(v, v.nxt) for v in _walk(a_head) if not v.intersect]
    b_edges = [(v, v.nxt) for v in _walk(b_head) if not v.intersect]
    for av, an in a_edges:
        hits_a = []
        for bv, bn in b_edges:
            hit = _seg_intersect((av.x, av.y), (an.x, an.y),
                                 (bv.x, bv.y), (bn.x, bn.y))
            if hit:
                hits_a.append((hit[1], hit[2], hit[0], bv, bn))
        for ta, tb, pt, bv, bn in sorted(hits_a):
            ia, ib = _V(*pt), _V(*pt)
            ia.intersect = ib.intersect = True
            ia.neighbour, ib.neighbour = ib, ia
            # insert ia between av-chain (respecting earlier inserts by t)
            ref = av
            while ref.nxt.intersect and _t_along(av, an, ref.nxt) < ta:
                ref = ref.nxt
            _link_after(ref, ia)
            ref = bv
            while ref.nxt.intersect and _t_along(bv, bn, ref.nxt) < tb:
                ref = ref.nxt
            _link_after(ref, ib)
            count += 1
    return count


def _t_along(v1: _V, v2: _V, v: _V) -> float:
    dx, dy = v2.x - v1.x, v2.y - v1.y
    if abs(dx) >= abs(dy):
        return (v.x - v1.x) / dx if dx else 0.0
    return (v.y - v1.y) / dy if dy else 0.0


def _link_after(ref: _V, v: _V) -> None:
    v.nxt = ref.nxt
    v.prv = ref
    ref.nxt.prv = v
    ref.nxt = v


def _mark_entries(head: _V, other: Ring) -> None:
    for v in _walk(head):
        if not v.intersect:
            continue
        # sample just past the intersection along travel direction
        nx, ny = v.nxt.x, v.nxt.y
        sx = v.x + (nx - v.x) * 1e-4
        sy = v.y + (ny - v.y) * 1e-4
        v.entry = _pt_in_ring((sx, sy), other)


def _trace(a_head: _V) -> list[Ring]:
    rings: list[Ring] = []
    for start in [v for v in _walk(a_head) if v.intersect]:
        if start.visited:
            continue
        ring: Ring = []
        cur = start
        while not cur.visited:
            cur.visited = True
            if cur.neighbour is not None:
                cur.neighbour.visited = True
            ring.append((cur.x, cur.y))
            step_forward = cur.entry
            nxt = cur.nxt if step_forward else cur.prv
            while not nxt.intersect:
                ring.append((nxt.x, nxt.y))
                nxt = nxt.nxt if step_forward else nxt.prv
            cur = nxt.neighbour
        if len(ring) >= 3 and abs(ring_area(ring)) > 1e-6:
            rings.append(ring)
    return rings


def _pair_bool(a: Ring, b: Ring, op: str, _depth: int = 0) -> list[Ring]:
    """Pairwise Greiner–Hormann boolean of two simple rings."""
    a, b = _norm(a), _norm(b)
    if _degenerate(a, b):
        if _depth >= 8:
            raise ValueError("planar boolean: unresolved degeneracy")
        span = max(max(x for x, _ in a) - min(x for x, _ in a), 1.0)
        for attempt in range(_depth, 8):
            nb = _perturb(b, span, attempt)
            if not _degenerate(a, nb):
                # prefer a nudge that ENGAGES the pair (intersections exist);
                # touching shapes pushed apart give the wrong disjoint answer
                probe = _pair_bool(a, nb, op, 8)
                engaged = (len(probe) == 1 if op == "union"
                           else bool(probe) if op == "intersect" else True)
                if engaged:
                    return probe
        return _pair_bool(a, _perturb(b, span, 0), op, 8)

    a_head, b_head = _build(a), _build(b)
    hits = _insert_intersections(a_head, b_head)
    if hits == 0:
        a_in_b = _pt_in_ring(a[0], b)
        b_in_a = _pt_in_ring(b[0], a)
        if op == "union":
            if a_in_b:
                return [b]
            if b_in_a:
                return [a]
            return [a, b]
        if op == "intersect":
            if a_in_b:
                return [a]
            if b_in_a:
                return [b]
            return []
        # difference a \ b
        if a_in_b:
            return []
        if b_in_a:
            return [a, list(reversed(b))]        # even-odd hole
        return [a]

    _mark_entries(a_head, b)
    _mark_entries(b_head, a)
    # op-specific entry flips (the classic GH formulation): intersection
    # walks interior; union flips both; difference flips the clip only
    if op in ("union", "difference"):
        for v in _walk(a_head):
            if v.intersect:
                v.entry = not v.entry
    if op == "union":
        for v in _walk(b_head):
            if v.intersect:
                v.entry = not v.entry
    if op == "difference":
        pass                                     # b keeps interior marks
    return _trace(a_head)


# ── shape-level booleans (shapes = lists of non-nested rings) ───────────


def _merge_rings(rings: list[Ring]) -> list[Ring]:
    """Union a soup of rings pairwise until no two overlap."""
    rings = [_norm(r) for r in rings if len(r) >= 3]
    changed = True
    while changed:
        changed = False
        for i in range(len(rings)):
            for j in range(i + 1, len(rings)):
                merged = _pair_bool(rings[i], rings[j], "union")
                if len(merged) == 1:             # they actually combined
                    rings = ([r for k, r in enumerate(rings)
                              if k not in (i, j)] + merged)
                    changed = True
                    break
            if changed:
                break
    return rings


def union(a: Sequence[Ring], b: Sequence[Ring]) -> list[Ring]:
    """Union of two shapes (each a list of independent rings)."""
    return _merge_rings(list(a) + list(b))


def intersect(a: Sequence[Ring], b: Sequence[Ring]) -> list[Ring]:
    """Intersection of two shapes."""
    out: list[Ring] = []
    for ra in a:
        for rb in b:
            out.extend(_pair_bool(ra, rb, "intersect"))
    return out


def subtract(a: Sequence[Ring], b: Sequence[Ring]) -> list[Ring]:
    """Difference a − b (b's rings removed from a's, sequentially)."""
    pieces = [_norm(r) for r in a]
    for rb in b:
        nxt: list[Ring] = []
        for piece in pieces:
            if ring_area(piece) < 0:             # emitted hole: keep as-is
                nxt.append(piece)
                continue
            nxt.extend(_pair_bool(piece, rb, "difference"))
        pieces = nxt
    return pieces


def divide(a: Sequence[Ring], b: Sequence[Ring]) -> list[list[Ring]]:
    """Pathfinder Divide: the disjoint pieces [a−b, a∩b, b−a] (non-empty)."""
    pieces = [subtract(a, b), intersect(a, b), subtract(b, a)]
    return [p for p in pieces if p]


# ── offset (AI-47) ──────────────────────────────────────────────────────


def offset_polygon(ring: Sequence[Sequence[float]], d: float) -> list[Ring]:
    """Closed-polygon offset with miter corners: ``d > 0`` grows the shape,
    ``d < 0`` shrinks it; a fully collapsed shrink returns ``[]``."""
    pts = _norm(ring)
    if len(pts) < 3 or abs(d) < _EPS:
        return [pts] if len(pts) >= 3 else []
    n = len(pts)
    base_area = ring_area(pts)
    sign = 1.0 if base_area > 0 else -1.0

    out: Ring = []
    for i in range(n):
        p_prev, p, p_next = pts[i - 1], pts[i], pts[(i + 1) % n]
        d_in = _unit((p[0] - p_prev[0], p[1] - p_prev[1]))
        d_out = _unit((p_next[0] - p[0], p_next[1] - p[1]))
        n_in = (d_in[1] * sign, -d_in[0] * sign)     # outward for this winding
        n_out = (d_out[1] * sign, -d_out[0] * sign)
        avg = _unit((n_in[0] + n_out[0], n_in[1] + n_out[1]))
        cos_half = max(avg[0] * n_in[0] + avg[1] * n_in[1], 0.25)
        out.append((p[0] + avg[0] * d / cos_half,
                    p[1] + avg[1] * d / cos_half))

    new_area = ring_area(out)
    if d < 0:
        if new_area * base_area <= 0 or abs(new_area) >= abs(base_area):
            return []                                # collapsed inward offset
        for i in range(n):                           # edge direction reversed
            ox = pts[(i + 1) % n][0] - pts[i][0]     # → vertices crossed over
            oy = pts[(i + 1) % n][1] - pts[i][1]
            nx = out[(i + 1) % n][0] - out[i][0]
            ny = out[(i + 1) % n][1] - out[i][1]
            if ox * nx + oy * ny <= 0:
                return []
    return [out]


def _unit(v: Pt) -> Pt:
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > _EPS else (0.0, 0.0)


# ── path surgery (AI-06) ────────────────────────────────────────────────


def split_at(points: Sequence[Sequence[float]], t: float) -> tuple[Ring, Ring]:
    """Split an open polyline at arc-length fraction ``t`` (0..1)."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    if len(pts) < 2:
        raise ValueError("split_at needs at least two points")
    lengths = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    target = max(0.0, min(1.0, t)) * sum(lengths)
    acc = 0.0
    for i, seg in enumerate(lengths):
        if acc + seg >= target - _EPS:
            f = (target - acc) / seg if seg > _EPS else 0.0
            cut = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f,
                   pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)
            left = pts[: i + 1] + [cut]
            right = [cut] + pts[i + 1:]
            return left, right
        acc += seg
    return pts, [pts[-1]]


def cut_along(ring: Sequence[Sequence[float]], p1: Sequence[float],
              p2: Sequence[float]) -> list[list[Ring]]:
    """Knife cut: the pieces of ``ring`` on each side of the infinite line
    through ``p1``–``p2`` (each piece a shape, possibly multi-ring)."""
    pts = _norm(ring)
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    span = 4 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    d = _unit((float(p2[0]) - float(p1[0]), float(p2[1]) - float(p1[1])))
    if d == (0.0, 0.0):
        raise ValueError("cut_along needs two distinct points")
    nrm = (-d[1], d[0])
    cx, cy = float(p1[0]), float(p1[1])
    half = []
    for side in (1.0, -1.0):
        half.append([
            (cx - d[0] * span, cy - d[1] * span),
            (cx + d[0] * span, cy + d[1] * span),
            (cx + d[0] * span + nrm[0] * side * span,
             cy + d[1] * span + nrm[1] * side * span),
            (cx - d[0] * span + nrm[0] * side * span,
             cy - d[1] * span + nrm[1] * side * span),
        ])
    pieces = [intersect([pts], [h]) for h in half]
    return [p for p in pieces if p]


# ── regions (AI-17) ─────────────────────────────────────────────────────


def fill_regions(shapes: Sequence[Sequence[Sequence[float]]],
                 *, max_shapes: int = 8) -> list[list[Ring]]:
    """Every bounded region of an overlay of simple shapes, as its own
    fillable face (the Live Paint decomposition): for each non-empty subset
    S the atom ``(∩ S) − (∪ rest)``. Authoring scope: at most
    ``max_shapes`` inputs (the atom count is exponential)."""
    rings = [_norm(s) for s in shapes]
    if len(rings) > max_shapes:
        raise ValueError(f"fill_regions is scoped to ≤{max_shapes} shapes")
    faces: list[list[Ring]] = []
    n = len(rings)
    for mask in range(1, 2 ** n):
        inside = [rings[i] for i in range(n) if mask >> i & 1]
        outside = [rings[i] for i in range(n) if not mask >> i & 1]
        atom = [inside[0]]
        for shp in inside[1:]:
            atom = intersect(atom, [shp])
            if not atom:
                break
        for shp in outside:
            if not atom:
                break
            atom = subtract(atom, [shp])
        if atom and sum(abs(ring_area(r)) for r in atom) > 1e-6:
            faces.append(atom)
    return faces


# ── document emission ───────────────────────────────────────────────────


def to_path(rings: Sequence[Ring], **fields: Any) -> dict[str, Any]:
    """A multi-ring shape as one even-odd ``path`` object (holes native)."""
    d: list[list[Any]] = []
    for ring in rings:
        pts = _norm(ring)
        if len(pts) < 3:
            continue
        d.append(["M", pts[0][0], pts[0][1]])
        d.extend(["L", x, y] for x, y in pts[1:])
        d.append(["Z"])
    fields.setdefault("fill", "currentColor")
    style = dict(fields.pop("style", None) or {})
    style.setdefault("fill_rule", "evenodd")
    return {"type": "path", "d": d, "style": style, **fields}
