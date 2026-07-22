#!/usr/bin/env python3
"""RED → contract for user-space gradient geometry (Gap A1).

The CSS-flavoured ``Gradient`` (angle-only linear, centre-only radial) cannot
place a fitted colour ramp exactly: a curved shape's bbox is mostly empty, so
bbox-relative geometry mis-lands the ramp — the defect measured on the
lotus-emblem reconstruction (94.5% cells).  A1 adds exact geometry:

* ``line: [[x1, y1], [x2, y2]]``   — linear, in the object's local (user)
  coordinate space → SVG ``gradientUnits="userSpaceOnUse"`` + x1/y1/x2/y2.
* ``radius: <px>``                 — radial user-space radius; requires a
  numeric ``at`` point (there is no bbox to resolve keywords against).
* ``focal: [fx, fy]``              — radial focus (the gloss-highlight
  primitive); requires ``radius``.
* ``GradientStop.opacity: 0..1``   — per-stop alpha → ``stop-opacity``.

Strictness is the contract: incoherent combinations are validation ERRORS,
never silent reinterpretation (agent-native surface — one obvious meaning).
Legacy specs (none of the new keys) must emit byte-identical SVG.

Model + SVG painter lanes (the raster truth path); the html backend mirrors
the SVG defs and is covered in its own lane below.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from frameforge.model import Gradient, GradientStop  # noqa: E402
from tooling.render_fixtures import Renderer  # noqa: E402

_STOPS = [{"color": "#102030", "position": "0%"}, {"color": "#e0f0ff", "position": "100%"}]


# ------------------------------------------------------------------ model lane
def test_linear_line_validates_and_normalises():
    g = Gradient(kind="linear", stops=_STOPS, line=[[10, 20], [110, 20.5]])
    assert g.line == [[10.0, 20.0], [110.0, 20.5]]


def test_line_and_angle_are_mutually_exclusive():
    with pytest.raises(ValidationError, match="line.*angle|angle.*line"):
        Gradient(kind="linear", stops=_STOPS, angle=90, line=[[0, 0], [10, 0]])


@pytest.mark.parametrize("bad", [
    [[0, 0]],                       # one point
    [[0, 0], [1, 1], [2, 2]],       # three points
    [[0, 0], [1]],                  # short point
    [[0, 0], ["x", 1]],             # non-numeric
])
def test_line_shape_is_enforced(bad):
    with pytest.raises(ValidationError):
        Gradient(kind="linear", stops=_STOPS, line=bad)


@pytest.mark.parametrize("kind", ["radial", "conic"])
def test_line_is_linear_only(kind):
    with pytest.raises(ValidationError, match="line"):
        Gradient(kind=kind, stops=_STOPS, line=[[0, 0], [10, 0]])


def test_radial_user_space_validates():
    g = Gradient(kind="radial", stops=_STOPS, at=[100, 80], radius=45)
    assert g.radius == 45.0


@pytest.mark.parametrize("kind", ["linear", "conic"])
def test_radius_is_radial_only(kind):
    with pytest.raises(ValidationError, match="radius"):
        Gradient(kind=kind, stops=_STOPS, radius=45)


def test_radius_requires_a_numeric_at_point():
    with pytest.raises(ValidationError, match="at"):
        Gradient(kind="radial", stops=_STOPS, radius=45)          # no at
    with pytest.raises(ValidationError, match="at"):
        Gradient(kind="radial", stops=_STOPS, radius=45, at="center")  # keyword at


@pytest.mark.parametrize("bad", [0, -3])
def test_radius_must_be_positive(bad):
    with pytest.raises(ValidationError):
        Gradient(kind="radial", stops=_STOPS, at=[10, 10], radius=bad)


def test_focal_requires_radius_and_radial():
    g = Gradient(kind="radial", stops=_STOPS, at=[100, 80], radius=45, focal=[92, 70])
    assert g.focal == [92.0, 70.0]
    with pytest.raises(ValidationError, match="focal"):
        Gradient(kind="radial", stops=_STOPS, at=[100, 80], focal=[92, 70])   # no radius
    with pytest.raises(ValidationError, match="focal"):
        Gradient(kind="linear", stops=_STOPS, focal=[92, 70])


def test_stop_opacity_bounds():
    assert GradientStop(color="#fff", opacity=0.35).opacity == 0.35
    for bad in (-0.1, 1.5):
        with pytest.raises(ValidationError):
            GradientStop(color="#fff", opacity=bad)


# ---------------------------------------------------------------- painter lane
def _render(fill):
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [200, 120]},
                      "layers": [{"id": "l", "objects": [
                          {"type": "rect", "box": [0, 0, 100, 60], "fill": fill}]}]}]}
    r = Renderer(doc, ".")
    return r.render_page(doc["pages"][0])[0], r


def _grad_tag(svg, kind="linearGradient"):
    m = re.search(rf"<{kind}[^>]*>", svg)
    assert m, f"no <{kind}> in {svg[:400]}"
    return m.group(0)


def test_linear_line_emits_user_space_geometry():
    svg, _ = _render({"kind": "linear", "stops": _STOPS, "line": [[10, 20], [110, 20]]})
    tag = _grad_tag(svg)
    assert 'gradientUnits="userSpaceOnUse"' in tag
    assert 'x1="10"' in tag and 'y1="20"' in tag
    assert 'x2="110"' in tag and 'y2="20"' in tag
    assert "%" not in re.sub(r'offset="[^"]*"', "", tag)


def test_radial_user_space_emits_center_radius_and_default_focus():
    svg, _ = _render({"kind": "radial", "stops": _STOPS, "at": [100, 80], "radius": 45})
    tag = _grad_tag(svg, "radialGradient")
    assert 'gradientUnits="userSpaceOnUse"' in tag
    assert 'cx="100"' in tag and 'cy="80"' in tag and 'r="45"' in tag
    assert 'fx="100"' in tag and 'fy="80"' in tag


def test_radial_focal_unpins_focus():
    svg, _ = _render({"kind": "radial", "stops": _STOPS,
                      "at": [100, 80], "radius": 45, "focal": [92, 70]})
    tag = _grad_tag(svg, "radialGradient")
    assert 'fx="92"' in tag and 'fy="70"' in tag
    assert 'cx="100"' in tag and 'cy="80"' in tag


def test_stop_opacity_emits_stop_opacity_attr():
    svg, _ = _render({"kind": "linear", "line": [[0, 0], [100, 0]],
                      "stops": [{"color": "#ffffff", "position": "0%", "opacity": 0.4},
                                {"color": "#000000", "position": "100%"}]})
    assert 'stop-opacity="0.4"' in svg
    # the opacity-less stop must NOT grow the attribute (legacy byte stability)
    plain = re.findall(r"<stop [^>]*#000000[^>]*/>", svg)
    assert plain and all("stop-opacity" not in s for s in plain)


def test_legacy_angle_gradient_gains_no_user_space_attrs():
    svg, _ = _render({"kind": "linear", "angle": 90, "stops": _STOPS})
    tag = _grad_tag(svg)
    assert "gradientUnits" not in tag
    svg2, _ = _render({"kind": "radial", "at": "center", "stops": _STOPS})
    tag2 = _grad_tag(svg2, "radialGradient")
    assert "gradientUnits" not in tag2 and ' r="' not in tag2


def test_repeating_composes_with_user_space_line():
    svg, _ = _render({"kind": "linear", "stops": _STOPS,
                      "line": [[0, 0], [40, 0]], "repeating": True})
    tag = _grad_tag(svg)
    assert 'spreadMethod="repeat"' in tag and 'gradientUnits="userSpaceOnUse"' in tag


# ------------------------------------------------------------------- html lane
# The html backend claims real-paint parity ("paints render for real"); its SVG
# defs lane must lower user-space geometry exactly (shifted into each shape's
# rebased viewBox), and its CSS lane must preserve direction (linear) and
# px placement (radial — CSS radial-gradient speaks px natively).
from frameforge.rendering.infrastructure.backends import html as fgh  # noqa: E402


def _hdoc(objects):
    return {"dsl": "FrameForge", "version": "2.0.0", "title": "T",
            "pages": [{"mode": "page", "id": "p1",
                       "canvas": {"size": [400, 300], "units": "px"},
                       "layers": [{"id": "main", "z": 0, "objects": objects}]}]}


def test_html_path_lane_passes_user_line_through():
    out = fgh.render_document(_hdoc([
        {"type": "path", "d": "M 10 20 L 110 20 L 60 80 Z",
         "fill": {"kind": "linear", "stops": _STOPS, "line": [[10, 20], [110, 20]]}}]))
    assert 'gradientUnits="userSpaceOnUse"' in out
    assert 'x1="10"' in out and 'y1="20"' in out and 'x2="110"' in out


def test_html_polygon_lane_shifts_user_radial_into_rebased_viewbox():
    # polygon bbox min (20, 30), stroke-less pad 1.0 → svg-local origin (19, 29)
    out = fgh.render_document(_hdoc([
        {"type": "polygon", "points": [[20, 30], [120, 30], [70, 110]],
         "fill": {"kind": "radial", "stops": _STOPS, "at": [70, 60], "radius": 40}}]))
    assert 'gradientUnits="userSpaceOnUse"' in out
    assert 'cx="51"' in out and 'cy="31"' in out and 'r="40"' in out


def test_html_rect_css_lane_places_user_radial_in_px():
    out = fgh.render_document(_hdoc([
        {"type": "rect", "box": [40, 30, 200, 150],
         "fill": {"kind": "radial", "stops": _STOPS, "at": [140, 105], "radius": 60}}]))
    assert "radial-gradient(circle 60px at 100px 75px" in out


def test_html_rect_css_lane_preserves_line_direction():
    out = fgh.render_document(_hdoc([
        {"type": "rect", "box": [0, 0, 200, 150],
         "fill": {"kind": "linear", "stops": _STOPS, "line": [[0, 0], [100, 100]]}}]))
    assert "linear-gradient(135deg" in out


def test_html_stop_opacity_both_lanes():
    stops = [{"color": "#ffffff", "position": "0%", "opacity": 0.4},
             {"color": "#000000", "position": "100%"}]
    out = fgh.render_document(_hdoc([
        {"type": "path", "d": "M 0 0 L 50 0 L 25 40 Z",
         "fill": {"kind": "linear", "stops": stops, "line": [[0, 0], [50, 0]]}},
        {"type": "rect", "box": [0, 0, 100, 80],
         "fill": {"kind": "linear", "stops": stops, "line": [[0, 0], [100, 0]]}}]))
    assert 'stop-opacity="0.4"' in out               # SVG defs lane
    assert "rgba(255,255,255,0.4)" in out            # CSS lane


# ------------------------------------------------------------------- tikz lane
# Both TikZ paths (FigureTikz in latex/, TikzPainter in painters/) are box-shade
# approximations; A1 requires them to (a) preserve a `line` gradient's DIRECTION
# via the derived CSS angle and (b) draw a user-space radial exactly — TikZ
# shades already live in page coordinates, so numeric at + radius map 1:1.
from frameforge.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge.rendering.domain.services.text_style_resolver import TextStyleResolver  # noqa: E402
from frameforge.rendering.infrastructure.latex.tikz import FigureTikz  # noqa: E402
from frameforge.rendering.infrastructure.painters.tikz import TikzPainter  # noqa: E402


def _fig():
    color = ColorResolver({})
    return FigureTikz(color, TextStyleResolver({}, {}, color), {})


def test_figuretikz_line_direction_survives_as_axis():
    tex = _fig().render({"type": "rect", "box": [0, 0, 300, 100],
                         "fill": {"kind": "linear", "stops": _STOPS,
                                  "line": [[0, 50], [300, 50]]}})   # horizontal
    assert "left color=" in tex and "right color=" in tex
    assert "top color=" not in tex


def test_figuretikz_user_radial_is_exact_in_page_space():
    tex = _fig().render({"type": "rect", "box": [40, 30, 200, 150],
                         "fill": {"kind": "radial", "stops": _STOPS,
                                  "at": [140, 105], "radius": 60}})
    assert "(140,105) ellipse (60pt and 60pt)" in tex


# -------------------------------------------------------------------- sdk lane
# The authoring helpers must speak the same surface as the model — a helper
# that cannot express `line`/`radius`/`focal`/stop-opacity would leave the SDK
# lane inconsistent with the schema it feeds.
def test_sdk_helpers_expose_user_space_geometry():
    from frameforge.sdk.paint import linear_gradient, radial_gradient

    g = linear_gradient([("#000", "0%"), ("#fff", "100%")], line=[[10, 20], [110, 20]])
    Gradient.model_validate(g)
    assert g["line"] == [[10, 20], [110, 20]] and "angle" not in g

    r = radial_gradient([("#fff", "0%"), ("#000", "100%")],
                        at=[100, 80], radius=45, focal=[92, 70])
    Gradient.model_validate(r)
    assert r["radius"] == 45 and r["focal"] == [92, 70]


def test_sdk_stop_triples_carry_opacity():
    from frameforge.sdk.paint import linear_gradient

    g = linear_gradient([("#fff", "0%", 0.4), ("#000", "100%")], line=[[0, 0], [10, 0]])
    Gradient.model_validate(g)
    assert g["stops"][0]["opacity"] == 0.4
    assert "opacity" not in g["stops"][1]


def test_tikzpainter_line_direction_and_user_radial():
    p = TikzPainter(ColorResolver({}))
    lin = p._gradient_shade({"kind": "linear", "stops": _STOPS,
                             "line": [[0, 50], [300, 50]]}, 0, 0, 300, 100)
    assert lin and "left color=" in lin and "top color=" not in lin
    rad = p._gradient_shade({"kind": "radial", "stops": _STOPS,
                             "at": [140, 105], "radius": 60}, 40, 30, 200, 150)
    assert rad and "(140,105) ellipse (60pt and 60pt)" in rad
