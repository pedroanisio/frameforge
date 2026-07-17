#!/usr/bin/env python3
"""Coach paint layer — render-safe atmosphere/depth for the colour stages.

glow / haze / vignette / wash / soft_shadow build depth from gradients + alpha
only (no blur filter / blend mode, which the browser-free rasteriser drops), and
``atmosphere`` derives that depth from the resolved StyleProfile palette. Pure
dict builders — unit-testable without OpenCV; boundary-clean (sdk + stdlib).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path.insert(0, ROOT)

from frameforge.coach import resolve_style  # noqa: E402
from frameforge.coach.paint import (  # noqa: E402
    atmosphere,
    darkest,
    fade,
    glow,
    haze,
    lightest,
    soft_shadow,
    vignette,
    wash,
)


def test_fade_emits_rgba_and_clamps():
    assert fade("#FFCC00", 0.5) == "rgba(255, 204, 0, 0.5)"
    assert fade("#fc0", 1.0) == "rgba(255, 204, 0, 1)"
    assert fade("#000000", 9.0).endswith(", 1)")
    assert fade("#000000", -9.0).endswith(", 0)")


def test_glow_is_core_plus_transparent_halo():
    halo, disc = glow(100, 80, 20, "#FFEEAA")
    assert halo["type"] == disc["type"] == "ellipse" and halo["rx"] > disc["rx"]
    assert halo["fill"]["stops"][-1]["color"].endswith(", 0)")     # soft edge, no ring
    assert disc["fill"]["stops"][-1]["color"].endswith(", 0)")


def test_vignette_haze_wash_soft_shadow_fade_out():
    v = vignette(400, 300, color="#000000", strength=0.5)
    assert v["fill"]["stops"][0]["color"].endswith(", 0)") and v["fill"]["stops"][-1]["color"] == "rgba(0, 0, 0, 0.5)"
    h = haze([0, 0, 100, 50], "#DDEEFF", opacity=0.4)
    assert h["fill"]["stops"][0]["color"] == "rgba(221, 238, 255, 0.4)"
    assert h["fill"]["stops"][-1]["color"].endswith(", 0)")
    w = wash([0, 0, 100, 50], "#FFFFFF", "#000000", opacity=0.2)
    assert w["fill"]["kind"] == "linear" and len(w["fill"]["stops"]) == 2
    s = soft_shadow(50, 50, 20, 6, color="#101820", strength=0.4)
    assert s["fill"]["stops"][-1]["color"].endswith(", 0)")


def test_lightest_darkest_pick_by_luma():
    pal = ["#101010", "#FFFFFF", "#808080"]
    assert lightest(pal) == "#FFFFFF"
    assert darkest(pal) == "#101010"


def test_atmosphere_is_style_driven_and_layered():
    style = resolve_style("comic_ink")
    atm = atmosphere(style, 1000, 600)
    assert set(atm) == {"back", "front"}
    # back is an ambient wash + a glow (>=3 objects); front is a single vignette
    assert len(atm["back"]) >= 3 and len(atm["front"]) == 1
    # key light is drawn from the palette's lightest colour
    key = lightest(style.palette)
    kr, kg, kb = (int(key.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    glow_disc = atm["back"][-1]
    assert f"{kr}, {kg}, {kb}" in glow_disc["fill"]["stops"][0]["color"]
    # vignette uses the palette's darkest colour
    ink = darkest(style.palette)
    ir, ig, ib = (int(ink.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    assert f"{ir}, {ig}, {ib}" in atm["front"][0]["fill"]["stops"][-1]["color"]


def test_atmosphere_renders_through_frameforge():
    from frameforge.sdk import DocumentBuilder, render_page_svgs
    style = resolve_style("children_book")
    atm = atmosphere(style, 200, 120)
    b = DocumentBuilder(title="atm")
    p = b.page("p", canvas={"size": [200, 120], "units": "px"}, coordinate_mode="absolute")
    layer = p.layer("m")
    for o in atm["back"]:
        layer.add(o)
    layer.add({"type": "ellipse", "center": [100, 60], "rx": 30, "ry": 30, "fill": "#FFFFFF"})
    for o in atm["front"]:
        layer.add(o)
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg") and "radialGradient" in svg and "linearGradient" in svg
