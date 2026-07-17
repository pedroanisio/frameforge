#!/usr/bin/env python3
"""Clip-path exposure on the SDK.

The authoritative ``ClipPath`` model and the SVG proxy already honour
``style.clip_path``; these tests pin the SDK *binding* added so an author can clip
a group/frame (or any primitive) without hand-writing the style bag — constructors
that lower to the model's ``{shape, args}`` dicts, a ``group(clip=...)`` /
``frame(clip=...)`` convenience, and the end-to-end guarantee that the proxy
emits a real ``clipPath`` for SDK-authored clips.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    Mat3,
    Path,
    clip_circle,
    clip_ellipse,
    clip_inset,
    clip_path,
    clip_polygon,
    clip_rect,
    mask_gradient,
    mask_none,
    mask_style,
    mask_url,
)
from frameforge.sdk.conform import render_page_svgs  # noqa: E402

CANVAS = {"size": [200, 200], "units": "px"}


def _walk(doc):
    out = []

    def rec(o):
        out.append(o)
        for c in o.get("children", []) or []:
            rec(c)

    for pg in doc["pages"]:
        for ly in pg.get("layers", []) or []:
            for o in ly.get("objects", []) or []:
                rec(o)
    return out


def _build(make):
    b = DocumentBuilder(title="clip", profile="diagram", lang="en")
    pg = b.page("p", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    make(pg)
    return b.build_dict(expand_reuse=False)


def _only_group(doc):
    groups = [o for o in _walk(doc) if o.get("type") == "group"]
    assert len(groups) == 1, f"expected one group, got {len(groups)}"
    return groups[0]


# ---- constructors --------------------------------------------------------- #
def test_clip_rect_is_absolute_polygon():
    assert clip_rect([10, 20, 100, 40]) == {
        "shape": "polygon",
        "args": {"points": [[10.0, 20.0], [110.0, 20.0], [110.0, 60.0], [10.0, 60.0]]},
    }


def test_clip_inset_uniform_and_explicit():
    assert clip_inset(18) == {"shape": "inset",
                              "args": {"top": 18, "right": 18, "bottom": 18, "left": 18}}
    assert clip_inset(4, 8) == {"shape": "inset",
                                "args": {"top": 4, "right": 8, "bottom": 4, "left": 8}}


def test_clip_circle_and_ellipse_omit_empty_args():
    assert clip_circle() == {"shape": "circle"}
    assert clip_ellipse(center=[10, 10], rx=5, ry=3) == {
        "shape": "ellipse", "args": {"center": [10.0, 10.0], "rx": 5.0, "ry": 3.0}}


def test_clip_polygon_coerces_points():
    assert clip_polygon([(0, 0), (10, 0), (5, 8)]) == {
        "shape": "polygon", "args": {"points": [[0.0, 0.0], [10.0, 0.0], [5.0, 8.0]]}}


def test_clip_path_from_builder_emits_d():
    cp = clip_path(Path().move_to(0, 0).line_to(10, 0).close())
    assert cp["shape"] == "path"
    assert isinstance(cp["args"]["d"], str) and cp["args"]["d"].startswith("M")


def test_mask_helpers_lower_to_style_mask_values():
    assert mask_none() == "none"
    assert mask_url("assets/noise.png") == {"url": "assets/noise.png"}
    grad = {"kind": "linear", "stops": [{"color": "#000", "position": "0%"}]}
    assert mask_gradient(grad) is grad
    assert mask_style(mask_url("assets/alpha.png")) == {"style": {"mask": {"url": "assets/alpha.png"}}}


# ---- group / frame lowering ----------------------------------------------- #
def test_group_clip_box_lowers_to_polygon_style():
    doc = _build(lambda pg: pg.group(
        [{"type": "rect", "box": [0, 0, 300, 300], "fill": "#ff0000"}], clip=[10, 10, 80, 80]))
    grp = _only_group(doc)
    assert grp["style"]["clip_path"]["shape"] == "polygon"
    assert grp["style"]["clip_path"]["args"]["points"][0] == [10.0, 10.0]


def test_group_clip_composes_with_transform():
    doc = _build(lambda pg: pg.group(
        [{"type": "rect", "box": [0, 0, 10, 10], "fill": "#0000ff"}],
        transform=Mat3.translate(5, 5), clip=clip_circle()))
    grp = _only_group(doc)
    assert "transform" in grp["style"]
    assert grp["style"]["clip_path"]["shape"] == "circle"


def test_frame_clip_wraps_in_clipped_group():
    b = DocumentBuilder(title="f", profile="diagram", lang="en")
    pg = b.page("p", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    with pg.frame(20, 20, clip=[0, 0, 50, 50]) as f:
        f.rect([0, 0, 200, 200], fill="#00ff00")
    doc = b.build_dict(expand_reuse=False)
    assert _only_group(doc)["style"]["clip_path"]["shape"] == "polygon"


def test_clip_on_primitive_via_style_validates():
    """A box-derived inset / circle clip on a plain rect must validate via build()."""
    b = DocumentBuilder(title="v", profile="diagram", lang="en")
    pg = b.page("p", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    pg.rect([0, 0, 100, 100], fill="#0000ff", style={"clip_path": clip_inset(10)})
    pg.rect([20, 0, 100, 100], fill="#00ffff", style={"clip_path": clip_circle()})
    b.build()  # raises ValidationError on an invalid clip_path


# ---- end-to-end: the proxy honours an SDK-authored clip ------------------- #
def test_render_honors_sdk_group_clip():
    b = DocumentBuilder(title="r", profile="diagram", lang="en")
    pg = b.page("p", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    pg.group([{"type": "rect", "box": [0, 0, 300, 300], "fill": "#ff0000"}], clip=[10, 10, 80, 80])
    svg = "\n".join(render_page_svgs(b.build()))
    assert "clipPath" in svg and "clip-path" in svg
