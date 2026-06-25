#!/usr/bin/env python3
"""Painter kit — render-safe atmosphere primitives for guided-draw compositions.

glow / vignette / haze / wash / soft_shadow build depth from gradients + alpha
only (no blur filter / blend mode, which the browser-free rasteriser drops). The
helpers are pure dict builders, so they unit-test without OpenCV.
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

from guided_paint import (  # noqa: E402
    fade,
    glow,
    haze,
    linear,
    radial,
    soft_shadow,
    stop,
    vignette,
    wash,
)


def test_fade_emits_rgba_and_clamps_alpha():
    assert fade("#FFCC00", 0.5) == "rgba(255, 204, 0, 0.5)"
    assert fade("#fc0", 1.0) == "rgba(255, 204, 0, 1)"      # 3-digit hex expands
    assert fade("#000000", 2.0).endswith(", 1)")            # clamp high
    assert fade("#000000", -3.0).endswith(", 0)")           # clamp low


def test_stop_and_gradient_builders():
    assert stop("#fff", 0.25) == {"color": "#fff", "position": "25%"}
    g = linear([stop("#000", 0), stop("#fff", 1)], "90deg")
    assert g["kind"] == "linear" and g["angle"] == "90deg" and len(g["stops"]) == 2
    r = radial([stop("#000", 0), stop("#fff", 1)], at="40% 60%")
    assert r["kind"] == "radial" and r["at"] == "40% 60%"


def test_glow_is_core_plus_transparent_halo():
    objs = glow(100, 80, 20, "#FFEEAA")
    assert len(objs) == 2 and all(o["type"] == "ellipse" for o in objs)
    halo, disc = objs
    assert halo["rx"] > disc["rx"]                          # halo wider than core
    # the outermost stop of both is fully transparent -> soft edge, no hard ring
    assert halo["fill"]["stops"][-1]["color"].endswith(", 0)")
    assert disc["fill"]["stops"][-1]["color"].endswith(", 0)")


def test_vignette_is_transparent_centre_to_dark_edge():
    v = vignette(400, 300, color="#000000", strength=0.5)
    assert v["type"] == "rect" and v["box"] == [0, 0, 400, 300]
    stops = v["fill"]["stops"]
    assert stops[0]["color"].endswith(", 0)")              # clear centre
    assert stops[-1]["color"] == "rgba(0, 0, 0, 0.5)"      # dark rim


def test_haze_and_wash_fade_to_transparent():
    h = haze([0, 0, 100, 50], "#DDEEFF", opacity=0.4)
    assert h["fill"]["stops"][0]["color"] == "rgba(221, 238, 255, 0.4)"
    assert h["fill"]["stops"][-1]["color"].endswith(", 0)")
    wsh = wash([0, 0, 100, 50], "#FFFFFF", "#000000", opacity=0.2)
    assert wsh["fill"]["kind"] == "linear" and len(wsh["fill"]["stops"]) == 2


def test_soft_shadow_fades_out():
    s = soft_shadow(50, 50, 20, 6, color="#101820", strength=0.4)
    assert s["type"] == "ellipse" and s["rx"] == 20 and s["ry"] == 6
    assert s["fill"]["stops"][0]["color"] == "rgba(16, 24, 32, 0.4)"
    assert s["fill"]["stops"][-1]["color"].endswith(", 0)")


def test_atmosphere_renders_through_framegraph():
    from framegraph.sdk import DocumentBuilder, render_page_svgs
    b = DocumentBuilder(title="paint")
    p = b.page("p", canvas={"size": [200, 120], "units": "px"}, coordinate_mode="absolute")
    layer = p.layer("m")
    layer.add({"type": "rect", "box": [0, 0, 200, 120], "fill": "#16324F"})
    for o in glow(100, 60, 30):
        layer.add(o)
    layer.add(haze([0, 0, 200, 60], "#DDEEFF"))
    layer.add(vignette(200, 120))
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg")
    assert "radialGradient" in svg and "linearGradient" in svg   # atmosphere reached the SVG
