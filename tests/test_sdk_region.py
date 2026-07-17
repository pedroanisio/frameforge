#!/usr/bin/env python3
"""Region operations on a flat object list — select / place / grade by region.

These are the SDK primitives behind "region-based transformation": pick the
objects in a window (``select_in``), map a sub-window into a target box with an
optional affine and a page-space clip (``place_region``), and recolour by
luminance, globally (``gradient_map``) or per region (``region_grade``).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import pytest  # noqa: E402

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    Mat3,
    extract_objects,
    gradient_map,
    object_bbox,
    place_region,
    region_grade,
    select_in,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402


def _source_doc() -> DocumentBuilder:
    """A doc with a background object and a transformed group holding a target rect."""
    b = DocumentBuilder(title="source", lang="en")
    p = b.page("a", canvas={"size": [400, 300], "units": "px"}, coordinate_mode="absolute")
    lyr = p.layer("art")
    lyr.rect([0, 0, 400, 300], fill="#ffffff", id="bg")
    p.group([{"type": "rect", "box": [0, 0, 10, 10], "fill": "#ff0000", "id": "target"}],
            transform=Mat3.translate(100, 50), id="grp")
    return b


# --------------------------------------------------------------------------- #
#  object_bbox                                                                 #
# --------------------------------------------------------------------------- #
def test_object_bbox_rect_and_path_and_ellipse_and_line():
    assert object_bbox({"type": "rect", "box": [10, 20, 30, 40]}) == (10.0, 20.0, 40.0, 60.0)
    assert object_bbox({"type": "path", "d": "M0 0 L10 4 L2 9 Z"}) == (0.0, 0.0, 10.0, 9.0)
    assert object_bbox({"type": "ellipse", "center": [50, 60], "rx": 5, "ry": 8}) == (45.0, 52.0, 55.0, 68.0)
    assert object_bbox({"type": "line", "from": [1, 2], "to": [9, 1]}) == (1.0, 1.0, 9.0, 2.0)
    assert object_bbox({"type": "polygon", "points": [[0, 0], [4, 0], [4, 6]]}) == (0.0, 0.0, 4.0, 6.0)


def test_object_bbox_none_when_no_geometry():
    assert object_bbox({"type": "text", "box": None, "text": "x"}) is None or isinstance(
        object_bbox({"type": "text", "box": [0, 0, 5, 5], "text": "x"}), tuple)
    assert object_bbox({"type": "group", "children": []}) is None


# --------------------------------------------------------------------------- #
#  select_in                                                                   #
# --------------------------------------------------------------------------- #
def _objs():
    return [
        {"type": "rect", "box": [0, 0, 10, 10], "fill": "#000"},     # inside [0,0,20,20]
        {"type": "rect", "box": [15, 15, 20, 20], "fill": "#111"},   # straddles edge
        {"type": "rect", "box": [100, 100, 5, 5], "fill": "#222"},   # far outside
    ]


def test_select_in_intersect_is_default():
    sel = select_in(_objs(), [0, 0, 20, 20])
    assert len(sel) == 2                       # inside + straddling, not the far one


def test_select_in_contain_excludes_straddler():
    sel = select_in(_objs(), [0, 0, 20, 20], mode="contain")
    assert len(sel) == 1 and sel[0]["box"] == [0, 0, 10, 10]


def test_select_in_center_uses_centroid():
    sel = select_in(_objs(), [0, 0, 20, 20], mode="center")
    # rect#2 centre is (25,25) → outside; only rect#1 (centre 5,5) qualifies
    assert len(sel) == 1 and sel[0]["box"] == [0, 0, 10, 10]


def test_select_in_does_not_mutate_or_alias_inputs():
    src = _objs()
    sel = select_in(src, [0, 0, 20, 20])
    sel[0]["fill"] = "#changed"
    assert src[0]["fill"] == "#000"            # returned objects are copies


# --------------------------------------------------------------------------- #
#  gradient_map                                                                #
# --------------------------------------------------------------------------- #
def test_gradient_map_maps_luminance_endpoints():
    ramp = [(0.0, "#000000"), (1.0, "#ffffff")]
    out = gradient_map([{"type": "rect", "box": [0, 0, 1, 1], "fill": "#000000"},
                        {"type": "rect", "box": [0, 0, 1, 1], "fill": "#ffffff"}], ramp)
    assert out[0]["fill"] == "#000000"
    assert out[1]["fill"] == "#ffffff"


def test_gradient_map_colours_by_luminance_not_hue():
    ramp = [(0.0, "#000000"), (1.0, "#ff0000")]
    out = gradient_map([{"type": "path", "d": "M0 0", "fill": "#ffffff", "stroke": "#000000"}], ramp)
    assert out[0]["fill"] == "#ff0000"         # white → ramp top
    assert out[0]["stroke"] == "#000000"       # black → ramp bottom


def test_gradient_map_leaves_non_hex_paint_alone():
    out = gradient_map([{"type": "rect", "box": [0, 0, 1, 1], "fill": "none"}],
                       [(0.0, "#000"), (1.0, "#fff")])
    assert out[0]["fill"] == "none"


# --------------------------------------------------------------------------- #
#  region_grade                                                                #
# --------------------------------------------------------------------------- #
def test_region_grade_assigns_by_centroid_first_match_wins():
    objs = [
        {"type": "rect", "box": [0, 0, 10, 10], "fill": "#ffffff"},      # centre (5,5) → A
        {"type": "rect", "box": [200, 0, 10, 10], "fill": "#ffffff"},    # centre (205,5) → B
        {"type": "rect", "box": [900, 0, 10, 10], "fill": "#ffffff"},    # centre → default
    ]
    regions = [
        ([0, 0, 100, 100], "#ff0000"),         # A: solid
        ([150, 0, 200, 100], [(0.0, "#000000"), (1.0, "#00ff00")]),    # B: ramp (white→top)
    ]
    out = region_grade(objs, regions, default="#0000ff")
    assert out[0]["fill"] == "#ff0000"
    assert out[1]["fill"] == "#00ff00"
    assert out[2]["fill"] == "#0000ff"


def test_region_grade_default_none_leaves_unmatched_untouched():
    objs = [{"type": "rect", "box": [900, 0, 10, 10], "fill": "#abcabc"}]
    out = region_grade(objs, [([0, 0, 100, 100], "#ff0000")], default=None)
    assert out[0]["fill"] == "#abcabc"


# --------------------------------------------------------------------------- #
#  place_region — clip rides a static parent, transform on the inner group      #
# --------------------------------------------------------------------------- #
def test_place_region_nests_clip_outside_transform():
    objs = [{"type": "rect", "box": [0, 0, 100, 100], "fill": "#abc"}]
    grp = place_region(objs, [0, 0, 100, 100], [10, 10, 50, 50])
    assert grp["type"] == "group"
    # outer carries the clip, NOT a transform (so the clip masks in page space)
    assert "clip_path" in grp["style"] and "transform" not in grp["style"]
    inner = grp["children"][0]
    assert inner["type"] == "group" and "transform" in inner["style"]


def test_place_region_without_clip_is_a_single_transformed_group():
    objs = [{"type": "rect", "box": [0, 0, 100, 100], "fill": "#abc"}]
    grp = place_region(objs, [0, 0, 100, 100], [10, 10, 50, 50], clip=False)
    assert grp["type"] == "group" and "transform" in grp["style"]
    assert grp["children"][0]["type"] == "rect"


def test_place_region_select_mode_filters_objects():
    objs = [
        {"type": "rect", "box": [0, 0, 10, 10], "fill": "#000"},
        {"type": "rect", "box": [500, 500, 10, 10], "fill": "#111"},
    ]
    grp = place_region(objs, [0, 0, 100, 100], [0, 0, 50, 50], clip=False, select="center")
    # only the first rect's centroid is inside the source window
    flat = grp["children"]
    assert len(flat) == 1 and flat[0]["box"] == [0, 0, 10, 10]


def test_place_region_builds_and_validates_clean():
    objs = [{"type": "path", "d": "M0 0 L100 0 L100 100 Z", "fill": "#3a3"}]
    b = DocumentBuilder(title="region", lang="en")
    page = b.page("p", canvas={"size": [400, 300], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, 400, 300], fill="#fff")
    page.add(place_region(objs, [0, 0, 100, 100], [40, 40, 160, 160], transform=Mat3.rotate(20)))
    report = validate_static_rules(b.build())
    assert [i for i in report.issues if i.severity == "error"] == []


# --------------------------------------------------------------------------- #
#  place_region — CSS / compositing style on the region                         #
# --------------------------------------------------------------------------- #
def test_place_region_style_merges_onto_clip_wrapper():
    objs = [{"type": "rect", "box": [0, 0, 100, 100], "fill": "#abc"}]
    grp = place_region(objs, [0, 0, 100, 100], [10, 10, 50, 50],
                       style={"opacity": 0.6, "mix_blend_mode": "multiply", "css": "filter:saturate(1.4)"})
    # CSS rides on the clip wrapper; the clip place_region set is preserved
    assert grp["style"]["opacity"] == 0.6
    assert grp["style"]["mix_blend_mode"] == "multiply"
    assert grp["style"]["css"] == "filter:saturate(1.4)"
    assert "clip_path" in grp["style"]


def test_place_region_style_on_inner_when_unclipped():
    objs = [{"type": "rect", "box": [0, 0, 100, 100], "fill": "#abc"}]
    grp = place_region(objs, [0, 0, 100, 100], [10, 10, 50, 50], clip=False,
                       style={"opacity": 0.5})
    assert grp["style"]["opacity"] == 0.5 and "transform" in grp["style"]


def test_place_region_geometry_keys_win_over_style():
    objs = [{"type": "rect", "box": [0, 0, 100, 100], "fill": "#abc"}]
    grp = place_region(objs, [0, 0, 100, 100], [10, 10, 50, 50],
                       style={"clip_path": "BOGUS", "transform": "BOGUS"})
    # place_region owns geometry: its clip_path is not clobbered by the style arg
    assert grp["style"]["clip_path"] != "BOGUS"


def test_place_region_passes_through_fields_like_id():
    objs = [{"type": "rect", "box": [0, 0, 100, 100], "fill": "#abc"}]
    grp = place_region(objs, [0, 0, 100, 100], [10, 10, 50, 50], id="hero")
    assert grp["id"] == "hero" and grp["type"] == "group"
    assert "clip_path" in grp["style"]                  # essential keys not clobbered
    bare = place_region(objs, [0, 0, 100, 100], [10, 10, 50, 50], clip=False, id="hero2")
    assert bare["id"] == "hero2" and "transform" in bare["style"]


def test_place_region_with_style_builds_and_validates_clean():
    objs = [{"type": "path", "d": "M0 0 L100 0 L100 100 Z", "fill": "#3a3"}]
    b = DocumentBuilder(title="region-style", lang="en")
    page = b.page("p", canvas={"size": [400, 300], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, 400, 300], fill="#fff")
    page.add(place_region(objs, [0, 0, 100, 100], [40, 40, 160, 160],
                          style={"opacity": 0.8, "mix_blend_mode": "screen"}))
    report = validate_static_rules(b.build())
    assert [i for i in report.issues if i.severity == "error"] == []


# --------------------------------------------------------------------------- #
#  extract_objects — element-level copy across compositions                     #
# --------------------------------------------------------------------------- #
def test_extract_by_layer_returns_top_level_objects():
    objs = extract_objects(_source_doc(), layer="art")
    assert len(objs) == 2                                    # bg rect + the group
    assert any(o.get("id") == "bg" for o in objs)
    assert any(o.get("type") == "group" for o in objs)


def test_extract_all_when_ids_none():
    assert len(extract_objects(_source_doc())) == 2


def test_extract_by_id_bakes_ancestor_transform():
    found = extract_objects(_source_doc(), ids="target")
    assert len(found) == 1
    wrapper = found[0]
    # the ancestor group's transform is preserved on a wrapper so world position holds
    assert wrapper["type"] == "group" and wrapper["style"].get("transform")
    inner = wrapper["children"][0]
    assert inner["id"] == "target" and inner["type"] == "rect"


def test_extract_by_id_no_bake_returns_bare_object():
    found = extract_objects(_source_doc(), ids="target", bake=False)
    assert len(found) == 1 and found[0]["id"] == "target" and found[0]["type"] == "rect"


def test_extract_group_by_id_takes_whole_subtree():
    found = extract_objects(_source_doc(), ids="grp")
    assert len(found) == 1
    grp = found[0]
    assert grp["id"] == "grp" and grp["type"] == "group"
    assert any(c.get("id") == "target" for c in grp["children"])


def test_extract_unknown_id_returns_empty():
    assert extract_objects(_source_doc(), ids={"nope"}) == []


def test_extract_does_not_alias_source():
    src = _source_doc()
    first = extract_objects(src, ids="target", bake=False)[0]
    first["fill"] = "#000000"
    again = extract_objects(src, ids="target", bake=False)[0]
    assert again["fill"] == "#ff0000"                       # source untouched


def test_extract_missing_layer_raises():
    with pytest.raises(ValueError):
        extract_objects(_source_doc(), layer="does-not-exist")


def test_extract_paste_into_other_composition_validates():
    skier = extract_objects(_source_doc(), ids="target")     # baked wrapper
    b = DocumentBuilder(title="target-doc", lang="en")
    page = b.page("p", canvas={"size": [300, 200], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, 300, 200], fill="#08323a")
    for obj in skier:
        page.add(obj)
    report = validate_static_rules(b.build())
    assert [i for i in report.issues if i.severity == "error"] == []

