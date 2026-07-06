"""sdk.planar — the planar geometry kernel (issue #45, parity W1).

One expansion-tier kernel closes five teardown rows: polygon booleans
(union / subtract / intersect / divide — AI-04 Pathfinder, AI-05 Shape
Builder), path surgery (`split_at`, `cut_along` — AI-06 Scissors & Knife),
closed-polygon offset (AI-47 Offset path, reusing W2's offset machinery),
and bounded-region decomposition (`fill_regions` — AI-17 Live Paint).
Pure stdlib math, deterministic, results emitted as plain ``path`` objects
(§A.0: the SDK computes, the document receives geometry).

Properties, not pictures: areas, ring counts, point membership and length
conservation pin the kernel; the canonical fixture pins the pixels.

Runs under pytest or standalone (``uv run python tests/test_sdk_planar.py``).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from framegraph.sdk import planar  # noqa: E402
from framegraph.sdk.model import HEAD_VERSION, validate_document  # noqa: E402

SQ = [(0, 0), (10, 0), (10, 10), (0, 10)]                 # 10×10 at origin
SQ_OFF = [(5, 5), (15, 5), (15, 15), (5, 15)]             # overlapping 10×10
SQ_FAR = [(30, 0), (40, 0), (40, 10), (30, 10)]           # disjoint


def area(rings):
    return sum(abs(planar.ring_area(r)) for r in rings)


# ── booleans: union / intersect / subtract / divide ─────────────────────


def test_union_of_overlapping_squares():
    rings = planar.union([SQ], [SQ_OFF])
    assert len(rings) == 1
    assert area(rings) == pytest.approx(100 + 100 - 25)


def test_intersect_is_the_overlap_rect():
    rings = planar.intersect([SQ], [SQ_OFF])
    assert len(rings) == 1
    assert area(rings) == pytest.approx(25)
    xs = sorted({round(x, 6) for x, _ in rings[0]})
    ys = sorted({round(y, 6) for _, y in rings[0]})
    assert xs == [5, 10] and ys == [5, 10]


def test_subtract_leaves_the_l_shape():
    rings = planar.subtract([SQ], [SQ_OFF])
    assert area(rings) == pytest.approx(75)


def test_subtract_inner_square_leaves_a_hole():
    inner = [(3, 3), (7, 3), (7, 7), (3, 7)]
    rings = planar.subtract([SQ], [inner])
    assert len(rings) == 2, "outer ring + hole ring"
    assert area(rings) == pytest.approx(100 + 16)   # |outer| + |hole| by abs
    # membership: hole centre is outside the shape, ring edge inside
    assert not planar.contains(rings, (5, 5))
    assert planar.contains(rings, (1, 5))


def test_divide_returns_the_three_pieces():
    pieces = planar.divide([SQ], [SQ_OFF])
    assert len(pieces) == 3
    total = sum(area(p) for p in pieces)
    assert total == pytest.approx(175)              # the union, partitioned
    assert sorted(round(area(p)) for p in pieces) == [25, 75, 75]


def test_disjoint_union_keeps_both_rings():
    rings = planar.union([SQ], [SQ_FAR])
    assert len(rings) == 2
    assert area(rings) == pytest.approx(200)


def test_disjoint_intersection_is_empty():
    assert planar.intersect([SQ], [SQ_FAR]) == []


def test_shared_edge_union_is_one_rect():
    right = [(10, 0), (20, 0), (20, 10), (10, 10)]  # shares SQ's right edge
    rings = planar.union([SQ], [right])
    assert len(rings) == 1
    assert area(rings) == pytest.approx(200, rel=1e-3)


def test_booleans_are_deterministic():
    a = planar.union([SQ], [SQ_OFF])
    b = planar.union([SQ], [SQ_OFF])
    assert a == b


# ── offset (AI-47) ──────────────────────────────────────────────────────


def test_offset_polygon_outward_grows_the_area():
    rings = planar.offset_polygon(SQ, 2)
    assert len(rings) == 1
    assert area(rings) == pytest.approx(14 * 14)    # miter corners are exact


def test_offset_polygon_inward_shrinks_the_area():
    rings = planar.offset_polygon(SQ, -2)
    assert area(rings) == pytest.approx(6 * 6)


def test_offset_polygon_inward_past_collapse_is_empty():
    assert planar.offset_polygon(SQ, -6) == []


# ── path surgery (AI-06) ────────────────────────────────────────────────


def test_split_at_halves_the_length():
    left, right = planar.split_at([(0, 0), (100, 0)], 0.5)
    assert left == [(0, 0), (50, 0)]
    assert right == [(50, 0), (100, 0)]


def test_split_at_respects_arc_length_over_vertices():
    pts = [(0, 0), (30, 0), (30, 40)]               # total length 70
    left, right = planar.split_at(pts, 0.5)         # cut at 35 → on leg 2
    assert left[-1] == pytest.approx((30, 5))
    assert right[0] == pytest.approx((30, 5))


def test_cut_along_a_diagonal_makes_two_triangles():
    pieces = planar.cut_along(SQ, (0, 0), (10, 10))
    assert len(pieces) == 2
    for p in pieces:                       # cut through two vertices resolves
        assert area(p) == pytest.approx(50, abs=1e-2)   # via the perturbation


# ── regions (AI-17) ─────────────────────────────────────────────────────


def test_fill_regions_decomposes_two_overlapping_squares():
    faces = planar.fill_regions([SQ, SQ_OFF])
    assert len(faces) == 3                          # two crescents + the lens
    assert sum(area(f) for f in faces) == pytest.approx(175)
    assert sorted(round(area(f)) for f in faces) == [25, 75, 75]


def test_fill_regions_guard_rails():
    with pytest.raises(ValueError):
        planar.fill_regions([SQ] * 9)               # authoring scope: small N


# ── document emission ───────────────────────────────────────────────────


def test_rings_emit_a_validating_path_object():
    rings = planar.subtract([SQ], [[(3, 3), (7, 3), (7, 7), (3, 7)]])
    obj = planar.to_path(rings, fill="ink", id="holed")
    assert obj["type"] == "path"
    assert obj["style"]["fill_rule"] == "evenodd"
    assert sum(1 for seg in obj["d"] if seg[0] == "M") == 2
    doc = {"dsl": "FrameGraph", "version": HEAD_VERSION, "title": "planar",
           "profile": "diagram",
           "defs": {"tokens": {"colors": {"ink": "#1d1e22"}}},
           "pages": [{"mode": "page", "id": "p",
                      "canvas": {"size": [50, 50], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "m", "objects": [obj]}]}]}
    validate_document(doc)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
