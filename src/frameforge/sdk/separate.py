"""Collision / label-separation solver for FrameForge documents.

Rationale
---------
The static audit *detects* scoped overlap (``tooling/validate.py``
``_free_group_overlap``, rule id ``overlap``: children of a free-layout group
or a ``meta.no_overlap: true`` cluster whose boxes overlap by more than 10% of
the smaller box AND more than 100 px²) but nothing in the tree could *fix* it —
authors and agents nudged boxes by hand. This module closes the
detect-without-solve gap with a deterministic AABB separation solver.

Scope, stated honestly
----------------------
* ``separate_rects`` is the pure kernel: axis-aligned boxes only, iterative
  pairwise relaxation along the axis of minimum penetration. It is not a
  force-directed graph layout and does not minimise total displacement
  globally; it resolves overlaps locally and clamps to a world box. An
  over-constrained input (boxes that cannot fit) terminates after
  ``max_passes`` with residual overlap rather than hanging.
* ``apply_separation`` moves ONLY what the audit flags: box-bearing,
  non-decorative children of free-layout groups / ``meta.no_overlap``
  clusters that contain at least one audit-level overlap. Global/layer
  overlap is intentional z-order layering (§3.3) and is never touched.
  Boxless children (a ``path``'s ``d``, a ``circle``'s ``center``) are not
  part of the audit's box scope and are left where they are.
* Per §A.0 doctrine the SDK computes and the document receives plain
  objects: the solver rewrites ``box`` x/y in place of a deep copy —
  no transforms are introduced, w/h never change, and a document with
  nothing to fix is returned unchanged (identity, same object).

Determinism (the load-bearing constraint)
-----------------------------------------
Same input → same output, always: fixed pair iteration order, no randomness,
centre/index tie-breaking. Safe inside the golden-fixture regime.
"""
from __future__ import annotations

import copy
from typing import Any, Optional, Sequence

__all__ = ["apply_separation", "separate_rects"]

Rect = tuple[float, float, float, float]

# The audit's intervention thresholds (tooling/validate.py _free_group_overlap):
# a pair is flagged when its overlap area exceeds BOTH bounds.
_AUDIT_AREA_FRACTION = 0.1
_AUDIT_AREA_MIN = 100.0


# --------------------------------------------------------------------------- #
#  kernel
# --------------------------------------------------------------------------- #
def separate_rects(
    rects: Sequence[Sequence[float]],
    *,
    world: Optional[Sequence[float]] = None,
    gap: float = 0.0,
    movable: Optional[Sequence[bool]] = None,
    max_passes: int = 32,
) -> list[tuple[float, float]]:
    """Resolve pairwise AABB overlaps; return per-rect ``(dx, dy)`` offsets.

    ``rects`` are ``(x, y, w, h)`` boxes. Overlapping pairs are pushed apart
    along the axis of minimum penetration: both movers take half the push,
    a pair with one immovable rect (``movable[i] is False``) pushes the
    movable one the full distance, and a fully immovable pair is skipped.
    ``gap`` demands at least that much clearance on the separation axis
    (touching counts as separated only when ``gap == 0``). ``world`` is an
    optional ``(x, y, w, h)`` clamp applied to movable rects after every
    pass. The relaxation runs until no pair moves or ``max_passes`` is
    exhausted — over-constrained input terminates with residual overlap
    instead of hanging. Deterministic and pure: fixed iteration order, no
    randomness, the input sequence is never mutated.
    """
    boxes = [[float(v) for v in r[:4]] for r in rects]
    n = len(boxes)
    mov = [True] * n if movable is None else [bool(m) for m in movable]
    origin = [(b[0], b[1]) for b in boxes]

    def clamp() -> None:
        if world is None:
            return
        wx, wy, ww, wh = (float(v) for v in world[:4])
        for k in range(n):
            if not mov[k]:
                continue
            b = boxes[k]
            b[0] = min(max(b[0], wx), wx + ww - b[2]) if b[2] <= ww else wx
            b[1] = min(max(b[1], wy), wy + wh - b[3]) if b[3] <= wh else wy

    def room(k: int, axis: int, direction: float) -> float:
        """How far box ``k`` may move along ``axis`` in ``direction`` before
        the world wall (unbounded without a world; zero when immovable)."""
        if not mov[k]:
            return 0.0
        if world is None:
            return float("inf")
        wx, wy, ww, wh = (float(v) for v in world[:4])
        lo, span = (wx, ww) if axis == 0 else (wy, wh)
        b = boxes[k]
        if direction < 0:
            return max(0.0, b[axis] - lo)
        return max(0.0, (lo + span) - (b[axis] + b[axis + 2]))

    def directions(i: int, j: int, axis: int) -> tuple[float, float]:
        """Escape directions for the pair along ``axis``: centre order
        decides who goes low/high; index breaks exact ties."""
        a, b = boxes[i], boxes[j]
        low_first = (a[axis] + a[axis + 2] / 2) <= (b[axis] + b[axis + 2] / 2)
        return ((-1.0, 1.0) if low_first else (1.0, -1.0))

    def push_pair(i: int, j: int, axis: int, pen: float) -> float:
        """Split ``pen`` between the pair, wall-aware: whatever one side
        cannot absorb (immovable, or flush against the world wall in its
        escape direction) is redistributed to the other, so a chain pressed
        against a wall resolves exactly instead of converging geometrically.
        The nanoscopic over-push lands pairs strictly separated, killing the
        floating-point asymptotic tail of chain relaxation. Returns the total
        distance actually moved (0.0 when both sides are wall/immovable-stuck)."""
        pen += 1e-7
        si, sj = directions(i, j, axis)
        want_i = pen / 2 if (mov[i] and mov[j]) else (pen if mov[i] else 0.0)
        move_i = min(want_i, room(i, axis, si))
        move_j = min(pen - move_i, room(j, axis, sj))
        # i absorbs whatever j could not, up to its own wall
        move_i = min(pen - move_j, room(i, axis, si))
        boxes[i][axis] += si * move_i
        boxes[j][axis] += sj * move_j
        return move_i + move_j

    def pair_room(i: int, j: int, axis: int) -> float:
        si, sj = directions(i, j, axis)
        return room(i, axis, si) + room(j, axis, sj)

    for _ in range(max(1, max_passes)):
        progressed = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if not (mov[i] or mov[j]):
                    continue
                ax, ay, aw, ah = boxes[i]
                bx, by, bw, bh = boxes[j]
                # penetration including the demanded clearance
                px = min(ax + aw, bx + bw) - max(ax, bx) + gap
                py = min(ay + ah, by + bh) - max(ay, by) + gap
                if px <= 0 or py <= 0:
                    continue
                # Feasibility-aware axis choice: prefer the cheaper (smaller-
                # penetration) axis, but never grind a wall-blocked axis while
                # the other can actually resolve the pair — a room-blind
                # min-penetration rule burns passes on zero-progress pushes.
                order = [(0, px), (1, py)] if px <= py else [(1, py), (0, px)]
                axis, pen = order[0]
                if pair_room(i, j, axis) < pen <= pair_room(i, j, order[1][0]) \
                        or (pair_room(i, j, axis) <= 0.0 < pair_room(i, j, order[1][0])):
                    axis, pen = order[1]
                progressed += push_pair(i, j, axis, pen)
        clamp()
        if progressed <= 1e-12:
            break
    return [(b[0] - ox, b[1] - oy) for b, (ox, oy) in zip(boxes, origin)]


# --------------------------------------------------------------------------- #
#  doc level — audit-scoped
# --------------------------------------------------------------------------- #
def apply_separation(data: dict, *, gap: float = 0.0, max_passes: int = 32) -> dict:
    """Separate audit-flagged overlapping children in a plain document dict.

    Walks the document exactly like the ``overlap`` audit: every ``group``
    whose layout kind is ``free`` (the default) or that is marked
    ``meta.no_overlap: true`` is a no-overlap scope. A scope is *solved*
    only when it contains at least one audit-level overlap (area > 10% of
    the smaller box AND > 100 px²) — sub-threshold overlaps are a design
    idiom the audit tolerates, so the solver tolerates them too. Solving a
    scope resolves ALL positive overlaps among its box-bearing,
    non-decorative children (plus ``gap`` clearance), clamped to the
    group's own box when it has one (children are parent-relative, so the
    world is ``[0, 0, gw, gh]``).

    Pure and deterministic: a document with no flagged scope is returned
    unchanged (the same object); otherwise a deep copy is returned and the
    input is never mutated. Only ``box`` x/y move — w/h and every other
    field survive byte-identical.
    """
    if not _find_flagged_groups(data):
        return data
    out = copy.deepcopy(data)
    for group in _find_flagged_groups(out):
        _solve_group(group, gap=gap, max_passes=max_passes)
    return out


def _eligible_children(group: dict) -> list[dict]:
    """The audit's box scope: dict children with a 4-number box, not decorative."""
    kids = []
    for ch in group.get("children") or []:
        if (isinstance(ch, dict) and not ch.get("decorative")
                and isinstance(ch.get("box"), (list, tuple)) and len(ch["box"]) >= 4
                and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                        for v in ch["box"][:4])):
            kids.append(ch)
    return kids


def _is_no_overlap_scope(node: dict) -> bool:
    if node.get("type") != "group":
        return False
    layout_kind = (node.get("layout") or {}).get("kind", "free")
    no_overlap = (node.get("meta") or {}).get("no_overlap") is True
    return layout_kind == "free" or no_overlap


def _audit_flags(children: list[dict]) -> bool:
    """True when at least one pair trips the audit thresholds."""
    boxes = [tuple(float(v) for v in ch["box"][:4]) for ch in children]
    for a in range(len(boxes)):
        ax, ay, aw, ah = boxes[a]
        for b in range(a + 1, len(boxes)):
            bx, by, bw, bh = boxes[b]
            ox = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
            oy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
            area = ox * oy
            if area > _AUDIT_AREA_FRACTION * min(aw * ah, bw * bh) and area > _AUDIT_AREA_MIN:
                return True
    return False


def _find_flagged_groups(data: dict) -> list[dict]:
    """Every no-overlap scope (document order) with an audit-level overlap."""
    flagged: list[dict] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            if _is_no_overlap_scope(node):
                kids = _eligible_children(node)
                if len(kids) >= 2 and _audit_flags(kids):
                    flagged.append(node)
            for value in node.values():
                walk(value)

    walk(data.get("pages", []))
    return flagged


def _solve_group(group: dict, *, gap: float, max_passes: int) -> None:
    kids = _eligible_children(group)
    rects = [tuple(float(v) for v in ch["box"][:4]) for ch in kids]
    world = None
    gbox = group.get("box")
    if (isinstance(gbox, (list, tuple)) and len(gbox) >= 4
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in gbox[:4])):
        world = (0.0, 0.0, float(gbox[2]), float(gbox[3]))
    offsets = separate_rects(rects, world=world, gap=gap, max_passes=max_passes)
    for ch, (dx, dy) in zip(kids, offsets):
        if dx or dy:
            box = list(ch["box"])
            box[0] = float(box[0]) + dx
            box[1] = float(box[1]) + dy
            ch["box"] = box
