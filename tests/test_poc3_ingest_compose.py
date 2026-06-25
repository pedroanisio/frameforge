#!/usr/bin/env python3
"""POC-03 — ingestion x FrameGraph compounding power (the editable-base claim).

The pure transforms over traced object dicts (restyle/recolor/place) and the
soundness gates (geometry invariant under restyle, distinct renders, native
composition) are deterministic and need no OpenCV, so they unit-test directly.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "examples"))

from poc3_ingest_compose import (  # noqa: E402
    STYLES,
    bbox,
    build_composition,
    build_parts,
    build_style_matrix,
    geometry_invariant,
    obj_bbox,
    palette_by_luma,
    place,
    recolor_fills,
    restyle_strokes,
    select_region,
    select_where,
    translate_objs,
)


def _trace_objs():
    """A tiny synthetic 'trace': two polylines + one filled polygon."""
    return [
        {"type": "polyline", "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0]],
         "stroke": "#1E2440", "stroke_style": {"stroke_width": 1.0}},
        {"type": "polyline", "points": [[2.0, 2.0], [6.0, 6.0]],
         "stroke": "#1E2440", "stroke_style": {"stroke_width": 1.0}},
        {"type": "polygon", "points": [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0]], "fill": "#202020"},
    ]


def test_restyle_changes_paint_not_geometry():
    base = _trace_objs()
    out = restyle_strokes(base, stroke="#FF0000", width=3.0)
    assert [o["points"] for o in out] == [o["points"] for o in base]      # geometry intact
    strokes = [o["stroke"] for o in out if o["type"] == "polyline"]
    assert strokes == ["#FF0000", "#FF0000"]
    assert all(o["stroke_style"]["stroke_width"] == 3.0 for o in out if o["type"] == "polyline")
    assert base[0]["stroke"] == "#1E2440"                                  # input not mutated


def test_geometry_invariant_holds_under_every_style():
    base = _trace_objs()
    for st in STYLES:
        assert geometry_invariant(base, restyle_strokes(base, stroke=st["stroke"], width=st["width"]))


def test_geometry_invariant_detects_a_moved_point():
    base = _trace_objs()
    tampered = restyle_strokes(base, stroke="#000000")
    tampered[0]["points"][0][0] = 999.0
    assert not geometry_invariant(base, tampered)


def test_recolor_fills_maps_through_palette():
    base = _trace_objs()
    out = recolor_fills(base, palette_by_luma(["#000080", "#FFD000"]))
    poly = [o for o in out if o["type"] == "polygon"][0]
    assert poly["fill"] == "#000080"        # dark source fill -> first (dark) slot
    assert base[2]["fill"] == "#202020"     # input not mutated


def test_place_composes_transform_and_preserves_count():
    base = _trace_objs()
    out = place(base, [100, 100, 50, 50], src=[20, 20])
    assert len(out) == len(base)
    tr = out[0]["style"]["transform"]
    assert tr.startswith("translate(") and "scale(" in tr


def test_place_keeps_existing_object_transform():
    base = [{"type": "polyline", "points": [[0.0, 0.0], [1.0, 1.0]], "stroke": "#000",
             "style": {"transform": "rotate(10)"}}]
    out = place(base, [0, 0, 10, 10], src=[10, 10])
    assert out[0]["style"]["transform"].endswith("rotate(10)")
    assert out[0]["style"]["transform"].startswith("translate(")


def test_bbox_over_mixed_geometry():
    assert bbox(_trace_objs()) == (0.0, 0.0, 20.0, 20.0)
    assert bbox([]) is None


def test_style_matrix_builds_and_renders_distinct_styles():
    from framegraph.sdk import render_page_svgs
    base = _trace_objs()
    b, ids = build_style_matrix(base, (20, 20))
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg")
    assert ids == [s["id"] for s in STYLES]
    # each style's stroke colour reaches the SVG -> the restyle is observable
    from poc3_ingest_compose import render_single
    per = {st["id"]: render_single(restyle_strokes(base, stroke=st["stroke"]), (20, 20))
           for st in STYLES}
    assert len(set(per.values())) == len(STYLES)


def _grid_objs():
    """Four polylines in known quadrants of a 100x100 frame."""
    return [
        {"type": "polyline", "points": [[10.0, 10.0], [30.0, 30.0]], "stroke": "#000"},  # TL
        {"type": "polyline", "points": [[70.0, 10.0], [90.0, 30.0]], "stroke": "#000"},  # TR
        {"type": "polyline", "points": [[10.0, 70.0], [30.0, 90.0]], "stroke": "#000"},  # BL
        {"type": "polyline", "points": [[70.0, 70.0], [90.0, 90.0]], "stroke": "#000"},  # BR
    ]


def test_select_region_extracts_only_the_part_inside():
    objs = _grid_objs()
    left = select_region(objs, [0, 0, 50, 100])         # left half
    assert len(left) == 2                                # TL + BL only
    assert all(obj_bbox(o)[0] < 50 for o in left)
    assert len(objs) == 4                               # input untouched


def test_select_region_contain_is_stricter_than_intersect():
    objs = _grid_objs()
    touching = select_region(objs, [20, 0, 60, 100])     # clips through TL/TR/BL/BR boxes
    contained = select_region(objs, [20, 0, 60, 100], contain=True)
    assert len(contained) <= len(touching)
    assert len(contained) < len(objs)                    # a real subset, not the whole


def test_select_where_filters_by_predicate():
    objs = _grid_objs() + [{"type": "polygon", "points": [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0]], "fill": "#111"}]
    polys = select_where(objs, lambda o: o["type"] == "polygon")
    assert len(polys) == 1 and polys[0]["type"] == "polygon"


def test_translate_objs_shifts_coordinates_and_preserves_count():
    objs = _grid_objs()
    moved = translate_objs(objs, 5.0, -3.0)
    assert len(moved) == len(objs)
    assert moved[0]["points"] == [[15.0, 7.0], [35.0, 27.0]]
    assert objs[0]["points"] == [[10.0, 10.0], [30.0, 30.0]]   # input untouched


def test_build_parts_recompose_is_a_real_edit():
    from framegraph.sdk import render_page_svgs
    # objects landing in build_parts' board ([2,6,30,58]) and figure ([28,18,20,66])
    # fractional regions for a 100x100 source, plus some elsewhere.
    def pl(p):
        return {"type": "polyline", "points": p, "stroke": "#000"}
    base = (
        [pl([[5.0, 10.0], [25.0, 40.0]])] * 8 +          # inside the board region
        [pl([[30.0, 25.0], [45.0, 70.0]])] * 6 +         # inside the figure region
        [pl([[60.0, 88.0], [95.0, 95.0]])] * 10          # elsewhere
    )
    b, counts = build_parts(base, (100, 100))
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg")
    # the extract and the lifted element are strict, non-empty subsets of the whole
    assert 0 < counts["extract: whiteboard only"] < len(base)
    assert 0 < counts["one element, restyled alone"] < len(base)


def test_composition_carries_native_text_and_chart():
    from framegraph.sdk import render_page_svgs
    base = _trace_objs()
    b = build_composition(base, (20, 20), n_objs=len(base), fidelity=0.42)
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg")
    assert svg.count("<text") >= 4          # native annotation present, not just the trace
    assert "0.42" in svg                    # the measured fidelity is surfaced in the doc
