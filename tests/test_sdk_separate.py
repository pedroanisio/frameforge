#!/usr/bin/env python3
"""test_sdk_separate.py — the collision/label-separation solver (sdk.separate).

The static audit DETECTS scoped overlap (`tooling/validate.py
_free_group_overlap`, rule id ``overlap``: children of a free-layout group or a
``meta.no_overlap: true`` cluster whose boxes overlap by more than 10% of the
smaller box AND more than 100 px²) but nothing in the tree could FIX it — the
author had to nudge boxes by hand. ``sdk.separate`` closes that gap. These
tests pin its contract:

  * KERNEL — ``separate_rects(rects, *, world, gap, movable, max_passes)`` is a
    pure, deterministic AABB separation solver: it returns per-rect ``(dx, dy)``
    offsets that resolve every pairwise overlap along the axis of minimum
    penetration, honouring immovable rects, a minimum ``gap``, and a ``world``
    clamp. Non-overlapping input → all-zero offsets. Over-constrained input
    terminates (bounded passes) instead of hanging.
  * AUDIT-SCOPED — ``apply_separation(data)`` moves ONLY what the audit flags:
    box-bearing, non-decorative children of free-layout groups /
    ``meta.no_overlap`` clusters containing at least one audit-level overlap.
    Global/layer overlap stays untouched (z-order is legal, §3.3).
  * ABSENCE IS IDENTITY — a document with nothing to fix returns the SAME
    object (``is data``), so existing pipelines cannot churn.
  * CONVERGENT WITH THE AUDIT — after ``apply_separation`` the ``overlap``
    finding is gone from ``validate_static_rules``.
  * SHAPE-PRESERVING — only ``box`` x/y move; w/h and every other field are
    byte-identical. Output round-trips through the authoritative model.
  * DETERMINISTIC & PURE — same input → equal output; the input document is
    never mutated.

Runs under pytest or standalone (``uv run python tests/test_sdk_separate.py``).
"""
from __future__ import annotations

import copy
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk.model import validate_document          # noqa: E402
from frameforge.sdk.separate import apply_separation, separate_rects  # noqa: E402
from frameforge.sdk.validate import validate_static_rules   # noqa: E402

EPS = 1e-6


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def _apply(rects, offsets):
    return [(x + dx, y + dy, w, h) for (x, y, w, h), (dx, dy) in zip(rects, offsets)]


def _overlap_area(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ox = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    oy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    return ox * oy


def _pairwise_max_overlap(rects):
    worst = 0.0
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            worst = max(worst, _overlap_area(rects[i], rects[j]))
    return worst


def _doc(objects, *, canvas=(400, 300)):
    return {"dsl": "FrameForge", "version": "2.3.0", "title": "t",
            "pages": [{"mode": "page", "id": "p1",
                       "canvas": {"size": list(canvas), "units": "px"},
                       "layers": [{"id": "l1", "objects": objects}]}]}


def _group(children, gid="g1", box=None, **extra):
    obj = {"type": "group", "id": gid, "children": children}
    if box is not None:
        obj["box"] = box
    obj.update(extra)
    return obj


def _rect(rid, x, y, w=80, h=40, **extra):
    obj = {"type": "rect", "id": rid, "box": [x, y, w, h], "fill": "#3388ff"}
    obj.update(extra)
    return obj


def _codes(data):
    return {i.rule_id for i in validate_static_rules(data).issues}


def _boxes_by_id(data):
    out = {}

    def walk(node):
        if isinstance(node, dict):
            if node.get("id") and node.get("box"):
                out[node["id"]] = list(node["box"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return out


# Two 80×40 rects overlapping by 40×40 = 1600 px² (> 100, > 0.1·3200): the
# audit-level overlap every doc-level test builds on.
FLAGGED = [_rect("a", 10, 10), _rect("b", 50, 10)]


# --------------------------------------------------------------------------- #
#  kernel: separate_rects
# --------------------------------------------------------------------------- #
def test_kernel_disjoint_input_is_identity():
    rects = [(0, 0, 50, 50), (100, 0, 50, 50), (0, 100, 50, 50)]
    assert separate_rects(rects) == [(0.0, 0.0)] * 3


def test_kernel_resolves_a_simple_overlap():
    rects = [(0, 0, 100, 100), (60, 0, 100, 100)]     # 40 px x-penetration
    offsets = separate_rects(rects)
    moved = _apply(rects, offsets)
    assert _pairwise_max_overlap(moved) <= EPS


def test_kernel_pushes_along_minimum_penetration_axis_symmetrically():
    # identical squares, x-penetration (40) < y-penetration (100):
    # separation must be horizontal, split between both movers, y untouched.
    rects = [(0, 0, 100, 100), (60, 0, 100, 100)]
    (dx1, dy1), (dx2, dy2) = separate_rects(rects)
    assert dy1 == dy2 == 0.0
    assert dx1 < 0 < dx2
    assert abs(abs(dx1) - abs(dx2)) <= EPS


def test_kernel_immovable_rect_stays_fixed():
    rects = [(0, 0, 100, 100), (60, 0, 100, 100)]
    offsets = separate_rects(rects, movable=[True, False])
    assert offsets[1] == (0.0, 0.0)
    assert _pairwise_max_overlap(_apply(rects, offsets)) <= EPS


def test_kernel_gap_keeps_inflated_boxes_disjoint():
    rects = [(0, 0, 100, 100), (60, 0, 100, 100)]
    gap = 8.0
    moved = _apply(rects, separate_rects(rects, gap=gap))
    inflated = [(x - gap / 2, y - gap / 2, w + gap, h + gap) for x, y, w, h in moved]
    assert _pairwise_max_overlap(inflated) <= EPS


def test_kernel_world_clamps_results():
    # 320 px of width fits three 100-wide rects with 20 px slack — feasible,
    # but only if the solver both separates and clamps.
    world = (0, 0, 320, 120)
    rects = [(0, 0, 100, 100), (60, 0, 100, 100), (120, 0, 100, 100)]
    moved = _apply(rects, separate_rects(rects, world=world))
    for x, y, w, h in moved:
        assert x >= world[0] - EPS and y >= world[1] - EPS
        assert x + w <= world[0] + world[2] + EPS
        assert y + h <= world[1] + world[3] + EPS
    assert _pairwise_max_overlap(moved) <= EPS


def test_kernel_overconstrained_terminates_without_resolution():
    # five 100×100 rects can never fit in a 150×150 world — the solver must
    # return (bounded passes), not hang, and must still clamp to the world.
    world = (0, 0, 150, 150)
    rects = [(0, 0, 100, 100)] * 5
    offsets = separate_rects(rects, world=world, max_passes=16)
    assert len(offsets) == 5
    for x, y, w, h in _apply(rects, offsets):
        assert x >= -EPS and y >= -EPS
        assert x + w <= 150 + EPS and y + h <= 150 + EPS


def test_kernel_is_deterministic_and_pure():
    rects = [(0, 0, 100, 100), (60, 0, 100, 100), (30, 50, 100, 100)]
    snapshot = copy.deepcopy(rects)
    assert separate_rects(rects) == separate_rects(rects)
    assert rects == snapshot


# --------------------------------------------------------------------------- #
#  doc level: apply_separation — audit-scoped
# --------------------------------------------------------------------------- #
def test_flagged_free_group_is_solved_and_audit_goes_quiet():
    data = _doc([_group(copy.deepcopy(FLAGGED))])
    assert "overlap" in _codes(data)                  # precondition: audit fires
    fixed = apply_separation(data)
    assert "overlap" not in _codes(fixed)
    a, b = _boxes_by_id(fixed)["a"], _boxes_by_id(fixed)["b"]
    assert _overlap_area(a, b) <= EPS


def test_sizes_and_unrelated_fields_survive():
    data = _doc([_group(copy.deepcopy(FLAGGED))])
    fixed = apply_separation(data)
    boxes = _boxes_by_id(fixed)
    assert boxes["a"][2:] == [80, 40] and boxes["b"][2:] == [80, 40]
    objs = fixed["pages"][0]["layers"][0]["objects"][0]["children"]
    assert all(o["fill"] == "#3388ff" for o in objs)


def test_clean_document_is_identity_same_object():
    data = _doc([_group([_rect("a", 10, 10), _rect("b", 200, 10)])])
    assert apply_separation(data) is data


def test_subthreshold_overlap_is_left_alone():
    # 8×40 = 320 px² overlap: > 100 but ≤ 0.1·3200 — the audit tolerates it,
    # so the solver must too (intentional slight overlaps are a design idiom).
    data = _doc([_group([_rect("a", 10, 10), _rect("b", 82, 10)])])
    assert "overlap" not in _codes(data)
    assert apply_separation(data) is data


def test_global_layer_overlap_is_legal_and_untouched():
    # Two overlapping top-level objects (no group): z-order layering, legal.
    data = _doc([_rect("bg", 0, 0, 300, 200), _rect("badge", 20, 20, 120, 60)])
    assert apply_separation(data) is data


def test_decorative_children_are_exempt():
    flagged = [_rect("a", 10, 10, decorative=True), _rect("b", 50, 10)]
    data = _doc([_group(flagged)])
    assert "overlap" not in _codes(data)              # audit skips decorative
    assert apply_separation(data) is data


def test_meta_no_overlap_cluster_is_solved():
    data = _doc([_group(copy.deepcopy(FLAGGED), meta={"no_overlap": True})])
    fixed = apply_separation(data)
    a, b = _boxes_by_id(fixed)["a"], _boxes_by_id(fixed)["b"]
    assert _overlap_area(a, b) <= EPS


def test_group_box_clamps_children_to_parent_local_world():
    # Children are parent-relative: a boxed group clamps its children to
    # [0, 0, gw, gh]. Three 80-wide rects fit a 260-wide group only if the
    # solver both separates and clamps.
    children = [_rect("a", 0, 10), _rect("b", 40, 10), _rect("c", 80, 10)]
    data = _doc([_group(children, box=[20, 20, 260, 100])])
    fixed = apply_separation(data)
    boxes = [_boxes_by_id(fixed)[k] for k in ("a", "b", "c")]
    assert _pairwise_max_overlap(boxes) <= EPS
    for x, y, w, h in boxes:
        assert x >= -EPS and y >= -EPS
        assert x + w <= 260 + EPS and y + h <= 100 + EPS


def test_nested_group_is_walked():
    inner = _group(copy.deepcopy(FLAGGED), gid="inner")
    data = _doc([_group([inner], gid="outer", box=[0, 0, 400, 300])])
    fixed = apply_separation(data)
    a, b = _boxes_by_id(fixed)["a"], _boxes_by_id(fixed)["b"]
    assert _overlap_area(a, b) <= EPS


def test_gap_parameter_reaches_the_doc_level():
    data = _doc([_group(copy.deepcopy(FLAGGED))])
    gap = 6.0
    fixed = apply_separation(data, gap=gap)
    a, b = _boxes_by_id(fixed)["a"], _boxes_by_id(fixed)["b"]
    inflated = [(x - gap / 2, y - gap / 2, w + gap, h + gap) for x, y, w, h in (a, b)]
    assert _pairwise_max_overlap(inflated) <= EPS


def test_apply_separation_is_deterministic_and_pure():
    data = _doc([_group(copy.deepcopy(FLAGGED))])
    snapshot = copy.deepcopy(data)
    fixed1 = apply_separation(data)
    fixed2 = apply_separation(copy.deepcopy(snapshot))
    assert fixed1 == fixed2
    assert data == snapshot                           # input never mutated


def test_output_round_trips_through_the_model():
    data = _doc([_group(copy.deepcopy(FLAGGED))])
    fixed = apply_separation(data)
    validated = validate_document(fixed)
    assert validated.pages[0] is not None


def test_flat_sdk_export():
    import frameforge.sdk as sdk
    assert sdk.separate_rects is separate_rects
    assert sdk.apply_separation is apply_separation
    assert "separate_rects" in sdk.__all__ and "apply_separation" in sdk.__all__


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
