#!/usr/bin/env python3
"""Marina and the Singing Sea — a polished children's picture book via the FrameGraph SDK.

A second, deliberately more *crafted* book than ``starlight_fox.py``. Every page is
an original illustration assembled from geometry primitives — there are no image
assets. The underwater setting is chosen to exercise the SDK's expressive range:

  * **Depth** — multi-stop vertical gradients carry the eye from sunlit shallows
    down into the black deep and back up to a moonlit surface.
  * **Light** — translucent god-ray shafts, rippling caustics and soft radial
    glows (bioluminescence, the moon) are all gradient paint over geometry.
  * **Atmosphere** — a radial vignette, drifting particle/bubble fields and
    parallax silhouette layers give each spread real depth.
  * **Character** — a recurring cast (Marina the whale, a jellyfish, a turtle, a
    lantern-fish, the Great Whale) drawn from ``Path`` curves and the typed
    ``PageBuilder`` primitives (``ellipse`` / ``circle`` / ``polyline`` /
    ``polygon`` / ``path``).

Run from the repository root::

    uv run python examples/marina_whale.py            # build + validate + write YAML
    uv run python examples/marina_whale.py --render    # also write per-page SVGs to out/marina/
"""
from __future__ import annotations

import argparse
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    Path,
    Vec2,
    serialize,
    theme,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas & palette                                                            #
# --------------------------------------------------------------------------- #

W, H = 1200, 900
CANVAS = {"size": [W, H], "units": "px"}

# Water, by depth
SHALLOW_TOP = "#74D2DE"
SHALLOW_LOW = "#2E7FA8"
MID_TOP = "#2C6F9B"
MID_LOW = "#123E63"
DEEP_TOP = "#0E2C4C"
DEEP_LOW = "#050F1C"
SURFACE_NIGHT_TOP = "#0B1E3A"
SURFACE_NIGHT_LOW = "#123A5C"

# Marina the whale
WHALE = "#4C80B8"
WHALE_DK = "#34608E"
WHALE_LT = "#74A2D2"
BELLY = "#E9F3FB"
FIN = "#345C86"
EYE = "#1B2536"

# Cast & coral
JELLY = "#F4A6CC"
JELLY_DK = "#E07AAC"
GLOW_BLUE = "#9DE9FF"
GLOW_GOLD = "#FFE6A0"
GLOW_PINK = "#FFC2E2"
TURTLE = "#4E8C6A"
TURTLE_LT = "#74B48E"
TURTLE_SH = "#356A4E"
LANTERN = "#3A4A66"
SAND = "#E7D9AE"
FOAM = "#EAF7FB"
MOON = "#FBF2C4"
MOON_SEA = "#ECDFA6"
CORAL = ["#E98A72", "#F0AC63", "#9C82C6", "#54B6A8", "#E5739B"]
SILHOUETTE = "#0A2138"

SANS = ["Quicksand", "Baloo 2", "Nunito", "sans-serif"]
SERIF = ["Fraunces", "Georgia", "Cambria", "serif"]

STYLES = {
    "title": {"font_family": SERIF, "font_size": 82, "font_weight": 700,
              "color": "#FBFEFF", "line_height": 1.0, "align": "center"},
    "title_sh": {"font_family": SERIF, "font_size": 82, "font_weight": 700,
                 "color": "#06243C", "line_height": 1.0, "align": "center"},
    "subtitle": {"font_family": SANS, "font_size": 25, "font_weight": 500,
                 "color": "#CDEAF4", "align": "center", "letter_spacing": 4},
    "byline": {"font_family": SANS, "font_size": 16, "font_weight": 500,
               "color": "#9FC6D8", "align": "center", "letter_spacing": 2},
    "story": {"font_family": SERIF, "font_size": 31, "font_weight": 500,
              "color": "#EAF6FB", "line_height": 1.42, "align": "center"},
    "dedicate": {"font_family": SERIF, "font_size": 28, "font_weight": 500,
                 "color": "#DDEFF6", "line_height": 1.5, "align": "center"},
    "pnum": {"font_family": SANS, "font_size": 17, "font_weight": 600,
             "color": "#BFE0EC", "align": "center"},
    "theend": {"font_family": SERIF, "font_size": 64, "font_weight": 700,
               "color": "#FBFEFF", "align": "center"},
}

_page_no = 0


# --------------------------------------------------------------------------- #
# Colour helpers                                                              #
# --------------------------------------------------------------------------- #

def a(hex6, aa):
    """Apply an 8-bit alpha (two hex digits) to a #rrggbb colour, as ``rgba()``.

    rgba() is used in preference to 8-digit ``#rrggbbaa`` because it is honoured
    by every SVG rasteriser in the toolchain (including older ones), so the
    translucent god-rays, glows and vignette composite identically everywhere.
    """
    r, g, b = int(hex6[1:3], 16), int(hex6[3:5], 16), int(hex6[5:7], 16)
    return f"rgba({r},{g},{b},{int(aa, 16) / 255:.3f})"


def clear(hex6):
    return a(hex6, "00")


def vgrad(top, low, *mid, angle=180):
    stops = [{"color": top, "position": "0%"}]
    for color, pos in mid:
        stops.append({"color": color, "position": pos})
    stops.append({"color": low, "position": "100%"})
    return {"kind": "linear", "angle": angle, "stops": stops}


def rgrad(inner, outer, at="50% 50%"):
    return {"kind": "radial", "at": at,
            "stops": [{"color": inner, "position": "0%"},
                      {"color": outer, "position": "100%"}]}


# --------------------------------------------------------------------------- #
# Page scaffolding                                                            #
# --------------------------------------------------------------------------- #

def new_page(builder, pid):
    return builder.page(pid, canvas=CANVAS, coordinate_mode="absolute").layer("art")


def page(builder, pid):
    global _page_no
    _page_no += 1
    return new_page(builder, pid)


def water(layer, paint):
    layer.rect([0, 0, W, H], fill=paint)


def vignette(layer, color=SILHOUETTE, edge_aa="9E", at="50% 42%", inner="42%"):
    """A soft radial darkening at the edges to focus each spread."""
    layer.rect([0, 0, W, H], fill={
        "kind": "radial", "at": at,
        "stops": [{"color": clear(color), "position": inner},
                  {"color": a(color, edge_aa), "position": "100%"}]})


# --------------------------------------------------------------------------- #
# Light: god-rays, caustics, glows, particles                                 #
# --------------------------------------------------------------------------- #

def god_rays(layer, src_x, top=-20, rays=6, spread=620, length=820, aa="22"):
    """Translucent light shafts spilling down from the surface."""
    grad = vgrad(a("#EAFBFF", aa), clear("#EAFBFF"))
    for i in range(rays):
        t = (i / max(rays - 1, 1)) - 0.5
        x = src_x + t * spread
        w_top = 14 + 10 * (i % 3)
        w_bot = w_top * 5 + 60
        skew = t * 240
        layer.polygon([(x - w_top, top), (x + w_top, top),
                       (x + skew + w_bot, top + length),
                       (x + skew - w_bot, top + length)], fill=grad)


def caustics(layer, y, count=8, color="#CFF6FF", aa="3A", width=2.0, amp=10, span=W):
    """Rippling bright lines just under the surface."""
    for k in range(count):
        x0 = (k / count) * span
        x1 = x0 + span / count * 1.3
        yy = y + amp * math.sin(k * 1.7)
        p = Path().move_to(x0, yy)
        p.through([(x0 + (x1 - x0) * 0.5, yy - amp), (x1, yy + amp * 0.4)])
        layer.path(p, fill="none", stroke=a(color, aa),
                   stroke_style={"stroke_width": width, "stroke_linecap": "round"})


def glow(layer, cx, cy, r, color=GLOW_BLUE, aa="66"):
    layer.ellipse([cx, cy], r, r, fill=rgrad(a(color, aa), clear(color)))


def bubble(layer, cx, cy, r):
    layer.circle([cx, cy], r, fill=a(FOAM, "44"),
                 stroke=a("#FFFFFF", "70"), stroke_style={"stroke_width": 1})
    layer.circle([cx - r * 0.32, cy - r * 0.32], max(1.0, r * 0.26), fill=a("#FFFFFF", "C8"))


def bubble_trail(layer, cx, cy, n=7, dr=2.0, rise=26, sway=12):
    for i in range(n):
        bubble(layer, cx + sway * math.sin(i * 0.9), cy - i * rise, 3 + i * dr * 0.5)


# Deterministic particle/plankton field (no RNG; stable across runs).
_MOTES = [(73, 0.5), (151, 0.2), (211, 0.8), (293, 0.35), (347, 0.66), (419, 0.12),
          (467, 0.9), (538, 0.42), (601, 0.74), (659, 0.28), (727, 0.6), (788, 0.16),
          (842, 0.85), (919, 0.46), (977, 0.7), (1051, 0.3), (1109, 0.78), (1163, 0.55)]


def motes(layer, y0, y1, color="#CDEAF4", aa="40", rows=3):
    for r in range(rows):
        for x, t in _MOTES:
            yy = y0 + (y1 - y0) * ((t + r * 0.31) % 1.0)
            xx = (x + r * 53) % W
            layer.circle([xx, yy], 1.6 + (r % 2), fill=a(color, aa))


def starfield(layer, color="#FFF7E0", upto=420):
    for x, y, r in [(90, 70, 4), (220, 120, 2.5), (360, 60, 3), (500, 110, 2.5),
                    (640, 70, 3.5), (770, 140, 2.5), (900, 60, 4), (1030, 120, 2.5),
                    (1130, 70, 3), (160, 230, 3), (430, 210, 3.5), (700, 240, 2.5),
                    (980, 220, 3), (1110, 300, 2.5), (300, 330, 3), (820, 350, 3)]:
        if y <= upto:
            star(layer, x, y, r, fill=color)


def star(layer, cx, cy, r, fill=MOON, n=5, rot=-90.0):
    pts = []
    for i in range(n * 2):
        ang = math.radians(rot + i * 180.0 / n)
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    layer.polygon(pts, fill=fill)


def moon(layer, cx, cy, r):
    glow(layer, cx, cy, r * 2.2, color="#FFF7D8", aa="55")
    layer.ellipse([cx, cy], r, r, fill=MOON)
    for dx, dy, rr in [(-0.34, -0.26, 0.17), (0.3, 0.12, 0.13), (-0.08, 0.4, 0.11),
                       (0.42, -0.38, 0.09)]:
        layer.ellipse([cx + dx * r, cy + dy * r], rr * r, rr * r, fill=MOON_SEA)


# --------------------------------------------------------------------------- #
# Seabed, reef, kelp                                                          #
# --------------------------------------------------------------------------- #

def seabed(layer, base_y, fill=SAND, bow=None):
    if bow is None:
        bow = [(300, base_y - 30), (700, base_y + 14), (1000, base_y - 22)]
    pts = [(-40, base_y)] + bow + [(W + 40, base_y)]
    p = Path().move_to(pts[0][0], pts[0][1]).through(pts[1:])
    p.line_to(W + 40, H + 40).line_to(-40, H + 40).close()
    layer.path(p, fill=fill)


def coral_fan(layer, x, base_y, s=1.0, color="#E5739B"):
    for ang in (-34, -16, 0, 16, 34):
        tip = (x + 120 * s * math.sin(math.radians(ang)),
               base_y - 150 * s * math.cos(math.radians(ang)))
        mid = (x + 50 * s * math.sin(math.radians(ang)), base_y - 80 * s)
        p = Path().move_to(x, base_y).through([mid, tip])
        layer.path(p, fill="none", stroke=color,
                   stroke_style={"stroke_width": 7 * s, "stroke_linecap": "round"})


def coral_blob(layer, x, base_y, s=1.0, color="#F0AC63"):
    layer.ellipse([x, base_y - 36 * s], 40 * s, 44 * s, fill=color)
    layer.ellipse([x - 34 * s, base_y - 18 * s], 26 * s, 30 * s, fill=color)
    layer.ellipse([x + 34 * s, base_y - 20 * s], 28 * s, 32 * s, fill=color)
    for dx in (-30, 0, 30):
        layer.circle([x + dx * s, base_y - 40 * s], 6 * s, fill=a("#FFFFFF", "33"))


def kelp(layer, x, base_y, height=320, s=1.0, color="#2F6E55", sway=46):
    p = Path().move_to(x, base_y)
    pts = []
    for i in range(1, 6):
        t = i / 5
        pts.append((x + sway * math.sin(i * 1.3) * s, base_y - height * t * s))
    p.through(pts)
    layer.path(p, fill="none", stroke=color,
               stroke_style={"stroke_width": 14 * s, "stroke_linecap": "round"})
    for px, py in pts[:-1]:
        layer.ellipse([px, py], 13 * s, 7 * s, fill=color)


def reef_silhouette(layer, base_y, color=SILHOUETTE):
    """A flat back layer of reef shapes for parallax depth."""
    for x, s in [(120, 1.0), (300, 0.7), (520, 1.2), (760, 0.8), (980, 1.1), (1140, 0.7)]:
        layer.ellipse([x, base_y], 90 * s, 70 * s, fill=color)
    seabed(layer, base_y, fill=color, bow=[(300, base_y - 10), (760, base_y + 8)])


# --------------------------------------------------------------------------- #
# The cast                                                                    #
# --------------------------------------------------------------------------- #

def draw_whale(layer, cx, cy, s=1.0, flip=1, mouth="smile", eyes="open", spout=False):
    """Marina, a round little whale. (cx, cy) is the body centre; flip ±1."""
    def p(dx, dy):
        return (cx + flip * dx * s, cy + dy * s)

    outline = [p(104, -2), p(95, -36), p(40, -60), p(-30, -56), p(-92, -42),
               p(-142, -72), p(-112, -18), p(-150, 10), p(-86, -4),
               p(-30, 30), p(44, 44), p(90, 26)]
    body = Path().move_to(*outline[0]).through(outline[1:]).close()
    layer.path(body, fill=WHALE, stroke=WHALE_DK, stroke_style={"stroke_width": 3 * s})
    # top sheen
    sheen = Path().move_to(*p(70, -40)).through([p(20, -52), p(-40, -48), p(-86, -36)])
    layer.path(sheen, fill="none", stroke=a(WHALE_LT, "AA"),
               stroke_style={"stroke_width": 7 * s, "stroke_linecap": "round"})
    # belly patch
    belly = Path().move_to(*p(92, 18)).through([p(40, 40), p(-26, 28), p(-78, 6)])
    belly2 = Path().move_to(*p(-78, 6)).through([p(-20, 18), p(50, 30), p(92, 12)]).close()
    layer.path(belly, fill="none", stroke=a(BELLY, "00"))
    blob = Path().move_to(*p(92, 14)).through(
        [p(44, 34), p(-24, 26), p(-72, 8), p(-20, 16), p(48, 26)]).close()
    layer.path(blob, fill=a(BELLY, "F2"))
    # throat pleats
    for k in range(3):
        gx = -10 + k * 26
        pl = Path().move_to(*p(gx + 60, 8 + k * 2)).through([p(gx + 30, 22), p(gx + 4, 18)])
        layer.path(pl, fill="none", stroke=a(WHALE_DK, "66"),
                   stroke_style={"stroke_width": 1.6 * s})
    # pectoral fin
    fin = Path().move_to(*p(36, 26)).through([p(8, 52), p(46, 50), p(60, 30)]).close()
    layer.path(fin, fill=FIN)
    # blowhole
    layer.ellipse([*p(64, -46)], 4 * s, 2.4 * s, fill=WHALE_DK)
    # eye
    layer.circle([*p(80, -22)], 5.4 * s, fill=EYE)
    layer.circle([p(80, -22)[0] + 1.7 * s, p(80, -22)[1] - 2 * s], 1.8 * s, fill="#FFFFFF")
    # mouth
    if mouth == "open":
        layer.ellipse([*p(96, 6)], 9 * s, 11 * s, fill=a("#214055", "EE"))
    else:
        m = Path().move_to(*p(104, 0)).through([p(86, 12), p(60, 8)])
        layer.path(m, fill="none", stroke=WHALE_DK,
                   stroke_style={"stroke_width": 2.4 * s, "stroke_linecap": "round"})
    if eyes == "closed":
        e = Path().move_to(p(80, -22)[0] - 5 * s, p(80, -22)[1])
        e.quad_to((p(80, -22)[0], p(80, -22)[1] + 5 * s), (p(80, -22)[0] + 5 * s, p(80, -22)[1]))
        layer.path(e, fill="none", stroke=EYE, stroke_style={"stroke_width": 2.2 * s})
    if spout:
        sx, sy = p(64, -48)
        glow(layer, sx, sy - 60 * s, 50 * s, color="#CFF2FF", aa="44")
        for off in (-18, 0, 18):
            d = Path().move_to(sx, sy).through([(sx + off * s, sy - 50 * s),
                                                (sx + off * 1.6 * s, sy - 100 * s)])
            layer.path(d, fill="none", stroke=a("#DFF6FF", "CC"),
                       stroke_style={"stroke_width": 4 * s, "stroke_linecap": "round"})
        for bx, by, br in [(sx - 26 * s, sy - 96 * s, 6 * s), (sx + 2 * s, sy - 118 * s, 7 * s),
                           (sx + 28 * s, sy - 92 * s, 5 * s)]:
            bubble(layer, bx, by, br)


def draw_jelly(layer, cx, cy, s=1.0, glowing=True):
    if glowing:
        glow(layer, cx, cy + 6 * s, 130 * s, color=GLOW_PINK, aa="4E")
    # bell
    bell = Path().move_to(cx - 60 * s, cy)
    bell.through([(cx - 54 * s, cy - 48 * s), (cx, cy - 66 * s),
                  (cx + 54 * s, cy - 48 * s), (cx + 60 * s, cy)])
    # scalloped hem
    hem = [(cx + 60 * s, cy)]
    for k in range(6):
        hx = cx + 60 * s - k * 24 * s
        hem.append((hx - 12 * s, cy + 12 * s))
        hem.append((hx - 24 * s, cy))
    bell.through(hem[1:]).close()
    layer.path(bell, fill=a(JELLY, "E0"), stroke=a(JELLY_DK, "AA"),
               stroke_style={"stroke_width": 2 * s})
    layer.path(Path().move_to(cx - 30 * s, cy - 20 * s).through(
        [(cx - 10 * s, cy - 40 * s), (cx + 16 * s, cy - 34 * s)]),
        fill="none", stroke=a("#FFFFFF", "88"), stroke_style={"stroke_width": 5 * s,
                                                              "stroke_linecap": "round"})
    # tentacles
    for k in range(7):
        tx = cx - 48 * s + k * 16 * s
        t = Path().move_to(tx, cy + 6 * s)
        t.through([(tx + 10 * s * math.sin(k), cy + 60 * s),
                   (tx - 8 * s * math.sin(k), cy + 120 * s),
                   (tx + 6 * s, cy + 170 * s)])
        layer.path(t, fill="none", stroke=a(JELLY, "B0"),
                   stroke_style={"stroke_width": 3 * s, "stroke_linecap": "round"})
    # face
    for sgn in (-1, 1):
        layer.circle([cx + sgn * 18 * s, cy - 20 * s], 4 * s, fill=EYE)
    sm = Path().move_to(cx - 12 * s, cy - 10 * s).quad_to(
        (cx, cy - 2 * s), (cx + 12 * s, cy - 10 * s))
    layer.path(sm, fill="none", stroke=EYE, stroke_style={"stroke_width": 2.2 * s,
                                                          "stroke_linecap": "round"})


def draw_turtle(layer, cx, cy, s=1.0, flip=1):
    def p(dx, dy):
        return (cx + flip * dx * s, cy + dy * s)
    # flippers
    for dx, dy, rot in [(-50, -8, 30), (-36, 34, -10), (44, -6, -28), (40, 34, 14)]:
        f = Path().move_to(*p(dx, dy)).through([p(dx + 30 * (1 if dx > 0 else -1), dy - 6),
                                                p(dx + 44 * (1 if dx > 0 else -1), dy + 14)]).close()
        layer.path(f, fill=TURTLE_SH)
    # head
    layer.ellipse([*p(72, -6)], 24 * s, 20 * s, fill=TURTLE_LT)
    layer.circle([*p(84, -10)], 3.4 * s, fill=EYE)
    sm = Path().move_to(*p(80, -2)).quad_to(p(88, 2), p(92, -4))
    layer.path(sm, fill="none", stroke=TURTLE_SH, stroke_style={"stroke_width": 2 * s})
    # shell
    layer.ellipse([*p(0, 4)], 78 * s, 62 * s, fill=TURTLE)
    layer.ellipse([*p(0, 0)], 60 * s, 46 * s, fill=TURTLE_LT)
    # carapace plates
    for ang in range(0, 360, 60):
        hx = p(0, 0)[0] + 38 * s * math.cos(math.radians(ang))
        hy = p(0, 0)[1] + 28 * s * math.sin(math.radians(ang))
        layer.circle([hx, hy], 11 * s, fill="none", stroke=a(TURTLE_SH, "AA"),
                     stroke_style={"stroke_width": 2 * s})
    layer.circle([*p(0, 0)], 14 * s, fill="none", stroke=a(TURTLE_SH, "AA"),
                 stroke_style={"stroke_width": 2 * s})


def draw_lantern_fish(layer, cx, cy, s=1.0, flip=1):
    def p(dx, dy):
        return (cx + flip * dx * s, cy + dy * s)
    # lure stalk + bulb
    stalk = Path().move_to(*p(20, -28)).through([p(40, -70), p(70, -86)])
    layer.path(stalk, fill="none", stroke=LANTERN, stroke_style={"stroke_width": 3 * s})
    glow(layer, *p(76, -90), 46 * s, color=GLOW_GOLD, aa="A0")
    layer.circle([*p(76, -90)], 9 * s, fill=GLOW_GOLD)
    # body
    layer.ellipse([*p(0, 0)], 46 * s, 36 * s, fill=LANTERN)
    layer.ellipse([*p(-6, 8)], 34 * s, 22 * s, fill=a("#5A6E90", "AA"))
    # tail
    layer.polygon([p(-40, 0), p(-72, -22), p(-72, 22)], fill=LANTERN)
    # friendly eye + smile
    layer.circle([*p(18, -6)], 8 * s, fill="#FBF6E6")
    layer.circle([*p(20, -6)], 4 * s, fill=EYE)
    sm = Path().move_to(*p(10, 14)).quad_to(p(26, 22), p(38, 12))
    layer.path(sm, fill="none", stroke="#1A2336", stroke_style={"stroke_width": 2 * s,
                                                               "stroke_linecap": "round"})
    # little teeth-glints (cute, not scary)
    for tx in (16, 26):
        layer.polygon([p(tx, 16), p(tx + 5, 16), p(tx + 2, 21)], fill="#FBF6E6")


def little_fish(layer, cx, cy, s=1.0, flip=1, color="#6FD0C6"):
    def p(dx, dy):
        return (cx + flip * dx * s, cy + dy * s)
    layer.ellipse([*p(0, 0)], 18 * s, 11 * s, fill=color)
    layer.polygon([p(-16, 0), p(-30, -10), p(-30, 10)], fill=color)
    layer.circle([*p(10, -2)], 2.4 * s, fill=EYE)


def school(layer, cx, cy, n=7, spread=120, color="#7FE0D2", flip=1):
    for i in range(n):
        ang = i * 2.4
        x = cx + math.cos(ang) * spread * (0.4 + 0.6 * (i / n))
        y = cy + math.sin(ang * 1.3) * spread * 0.5
        little_fish(layer, x, y, s=0.7 + 0.2 * (i % 2), flip=flip, color=color)


def great_whale(layer, cx, cy, s=1.0, flip=1, aa="C8"):
    """A vast, distant whale silhouette — drawn faintly for depth and awe."""
    def p(dx, dy):
        return (cx + flip * dx * s, cy + dy * s)
    outline = [p(300, 0), p(260, -70), p(120, -120), p(-90, -118), p(-260, -86),
               p(-380, -150), p(-300, -30), p(-400, 40), p(-250, 6),
               p(-80, 70), p(140, 86), p(260, 44)]
    body = Path().move_to(*outline[0]).through(outline[1:]).close()
    layer.path(body, fill=a("#0E3052", aa))
    layer.path(Path().move_to(*p(250, -50)).through([p(80, -96), p(-160, -86), p(-300, -60)]),
               fill="none", stroke=a(WHALE_LT, "40"),
               stroke_style={"stroke_width": 8 * s, "stroke_linecap": "round"})
    layer.circle([*p(214, -34)], 8 * s, fill=a("#CFE6F6", "C0"))


# --------------------------------------------------------------------------- #
# Caption + page number                                                       #
# --------------------------------------------------------------------------- #

def caption(layer, text, *, y=742, h=128):
    layer.rect([108, y, W - 216, h], fill=a("#08233B", "DC"), radius=30,
               stroke=a("#8FD3E6", "33"), stroke_style={"stroke_width": 1.5})
    # top sheen line + a small bubble motif
    layer.path(Path().move_to(150, y + 12).line_to(W - 150, y + 12),
               fill="none", stroke=a("#FFFFFF", "22"), stroke_style={"stroke_width": 2})
    for bx, by, br in [(150, y + h - 30, 7), (168, y + h - 46, 4), (138, y + h - 48, 3)]:
        layer.circle([bx, by], br, fill=a(GLOW_BLUE, "55"),
                     stroke=a("#FFFFFF", "50"), stroke_style={"stroke_width": 1})
    layer.text([170, y + 20, W - 340, h - 34], text, style={"class": "story"})


def page_number(layer):
    global _page_no
    layer.circle([W / 2, 868], 16, fill=a("#08233B", "AA"),
                 stroke=a(GLOW_BLUE, "44"), stroke_style={"stroke_width": 1})
    layer.text([W / 2 - 40, 858, 80, 24], f"{_page_no}", style={"class": "pnum"})


# --------------------------------------------------------------------------- #
# Pages                                                                        #
# --------------------------------------------------------------------------- #

def page_cover(builder):
    layer = page(builder, "cover")
    water(layer, vgrad(SHALLOW_TOP, MID_LOW, (SHALLOW_LOW, "48%"), (MID_TOP, "74%")))
    god_rays(layer, 560, rays=7, spread=900, length=900, aa="2A")
    caustics(layer, 70, count=10, aa="46")
    motes(layer, 120, 820, rows=3)
    reef_silhouette(layer, 820, color=a("#0C2A45", "FF"))
    coral_fan(layer, 220, 824, s=1.0, color=a("#2C5C72", "FF"))
    coral_fan(layer, 1000, 828, s=1.2, color=a("#2C5C72", "FF"))
    draw_whale(layer, 600, 540, s=1.5, flip=1, mouth="smile")
    bubble_trail(layer, 770, 470, n=8)
    vignette(layer, edge_aa="7A")
    # title with a soft drop-shadow (drawn twice)
    layer.text([0, 170, W, 110], "Marina", style={"class": "title_sh"})
    layer.text([0, 164, W, 110], "Marina", style={"class": "title"})
    layer.text([0, 286, W, 50], "and the Singing Sea", style={"class": "subtitle"})
    layer.text([0, 836, W, 28], "an original picture book drawn with the FrameGraph SDK",
               style={"class": "byline"})


def page_dedication(builder):
    layer = page(builder, "dedication")
    water(layer, vgrad(MID_TOP, DEEP_TOP, (MID_LOW, "60%")))
    motes(layer, 80, 860, rows=4)
    glow(layer, 600, 360, 150, color=GLOW_BLUE, aa="3A")
    draw_jelly(layer, 600, 320, s=1.1)
    bubble_trail(layer, 380, 700, n=9)
    bubble_trail(layer, 840, 740, n=7)
    layer.text([200, 560, W - 400, 130],
               "For every small voice\nstill learning its song.",
               style={"class": "dedicate"})
    vignette(layer, edge_aa="7A")
    page_number(layer)


def page_shallows(builder):
    layer = page(builder, "p-shallows")
    water(layer, vgrad(SHALLOW_TOP, MID_LOW, (SHALLOW_LOW, "52%")))
    god_rays(layer, 640, rays=6, spread=780, length=760, aa="26")
    caustics(layer, 64, count=10, aa="48")
    motes(layer, 120, 720, rows=2)
    reef_silhouette(layer, 858, color="#15405E")
    for i, x in enumerate((150, 360, 880, 1080)):
        coral_blob(layer, x, 854, s=0.8 + 0.1 * i, color=a(CORAL[i % len(CORAL)], "FF"))
    coral_fan(layer, 560, 860, s=1.0, color=CORAL[4])
    kelp(layer, 1140, 858, height=300, color="#2F6E55")
    draw_whale(layer, 540, 470, s=1.15, flip=1)
    school(layer, 900, 360, n=8, color="#7FE0D2")
    bubble_trail(layer, 700, 420, n=6)
    vignette(layer)
    caption(layer, "In the warm blue shallows lived a little whale named Marina.")
    page_number(layer)


def page_nosong(builder):
    layer = page(builder, "p-nosong")
    water(layer, vgrad(SHALLOW_LOW, MID_LOW, (MID_TOP, "55%")))
    god_rays(layer, 520, rays=5, spread=640, length=720, aa="1E")
    motes(layer, 120, 760, rows=2)
    reef_silhouette(layer, 860, color="#123A56")
    draw_whale(layer, 560, 470, s=1.3, flip=1, mouth="open", eyes="closed")
    # only one tiny bubble comes out
    bubble(layer, 720, 430, 9)
    bubble(layer, 742, 408, 5)
    glow(layer, 720, 430, 40, color=GLOW_BLUE, aa="33")
    vignette(layer)
    caption(layer, "But one morning, when she tried to sing… only one small bubble came out.")
    page_number(layer)


def page_jelly(builder):
    layer = page(builder, "p-jelly")
    water(layer, vgrad(MID_TOP, DEEP_TOP, (MID_LOW, "55%")))
    motes(layer, 80, 840, rows=3)
    draw_jelly(layer, 760, 320, s=1.25)
    school(layer, 980, 560, n=6, spread=90, color=a(JELLY, "FF"), flip=-1)
    draw_whale(layer, 420, 540, s=1.15, flip=1, eyes="open")
    bubble_trail(layer, 250, 650, n=6)
    vignette(layer)
    caption(layer, "“Songs hide down in the deep,” glowed a jellyfish. “Follow the little lights.”")
    page_number(layer)


def page_descend(builder):
    layer = page(builder, "p-descend")
    water(layer, vgrad(MID_TOP, DEEP_LOW, (MID_LOW, "40%"), (DEEP_TOP, "74%")))
    god_rays(layer, 600, top=-20, rays=5, spread=520, length=420, aa="16")
    motes(layer, 120, 860, rows=4)
    # faint reef far below
    reef_silhouette(layer, 880, color="#06192C")
    draw_whale(layer, 600, 430, s=1.2, flip=1, eyes="open")
    bubble_trail(layer, 470, 360, n=10, rise=30)
    glow(layer, 980, 560, 60, color=GLOW_GOLD, aa="55")
    glow(layer, 240, 640, 44, color=GLOW_PINK, aa="50")
    glow(layer, 1080, 720, 40, color=GLOW_BLUE, aa="55")
    vignette(layer, edge_aa="A8")
    caption(layer, "So down she swam, to where the water turns to evening.")
    page_number(layer)


def page_turtle(builder):
    layer = page(builder, "p-turtle")
    water(layer, vgrad(MID_LOW, DEEP_LOW, (DEEP_TOP, "58%")))
    motes(layer, 80, 860, rows=4)
    for gx, gy, gc in [(220, 300, GLOW_BLUE), (1020, 240, GLOW_GOLD), (900, 700, GLOW_PINK)]:
        glow(layer, gx, gy, 36, color=gc, aa="50")
    draw_turtle(layer, 760, 360, s=1.4, flip=-1)
    draw_whale(layer, 400, 560, s=1.1, flip=1, eyes="open")
    bubble_trail(layer, 250, 660, n=6)
    vignette(layer, edge_aa="A0")
    caption(layer, "A wise old turtle drifted by. “Listen,” he said. “The sea is full of voices.”")
    page_number(layer)


def page_deep(builder):
    layer = page(builder, "p-deep")
    water(layer, vgrad(DEEP_TOP, DEEP_LOW, ("#081f37", "55%")))
    motes(layer, 60, 880, rows=5, aa="30")
    # a sky of bioluminescent specks
    for x, t in _MOTES:
        for r in range(2):
            gx = (x + r * 120) % W
            gy = 120 + ((t + r * 0.5) % 1.0) * 620
            glow(layer, gx, gy, 16, color=(GLOW_BLUE if (x + r) % 2 else GLOW_GOLD), aa="66")
            layer.circle([gx, gy], 2.4, fill=a("#FFFFFF", "CC"))
    draw_lantern_fish(layer, 720, 430, s=1.4, flip=-1)
    draw_whale(layer, 360, 560, s=1.0, flip=1, eyes="open")
    bubble_trail(layer, 220, 660, n=6)
    vignette(layer, edge_aa="C0")
    caption(layer, "In the dark, tiny lights blinked like stars — and a little lantern-fish smiled.")
    page_number(layer)


def page_hear(builder):
    layer = page(builder, "p-hear")
    water(layer, vgrad(DEEP_TOP, DEEP_LOW, ("#0a2540", "50%")))
    motes(layer, 60, 880, rows=4, aa="2A")
    # concentric song-rings rolling through the water
    for i in range(6):
        rr = 120 + i * 110
        layer.circle([1080, 470], rr, fill="none",
                     stroke=a("#8FD3E6", f"{max(10, 80 - i * 12):02X}"),
                     stroke_style={"stroke_width": 3})
    glow(layer, 1080, 470, 80, color=GLOW_BLUE, aa="3A")
    draw_whale(layer, 380, 520, s=1.15, flip=1, eyes="open")
    vignette(layer, edge_aa="B4")
    caption(layer, "Then Marina heard it — a deep, slow song rolling through the water.")
    page_number(layer)


def page_great(builder):
    layer = page(builder, "p-great")
    water(layer, vgrad("#0c2A48", DEEP_LOW, (DEEP_TOP, "55%")))
    motes(layer, 60, 880, rows=4, aa="26")
    great_whale(layer, 640, 420, s=1.2)
    # song rings from the great whale's head
    for i in range(5):
        layer.circle([300, 350], 90 + i * 90, fill="none",
                     stroke=a("#A7DCEC", f"{max(8, 56 - i * 10):02X}"),
                     stroke_style={"stroke_width": 2.5})
    draw_whale(layer, 360, 660, s=0.8, flip=1, eyes="open")
    bubble_trail(layer, 250, 740, n=5)
    vignette(layer, edge_aa="A8")
    caption(layer, "It was the Great Whale, singing to the whole wide sea.")
    page_number(layer)


def page_note(builder):
    layer = page(builder, "p-note")
    water(layer, vgrad(MID_LOW, DEEP_TOP, (DEEP_TOP, "70%")))
    motes(layer, 80, 860, rows=3)
    great_whale(layer, 1180, 360, s=0.8, flip=-1, aa="70")
    draw_whale(layer, 520, 470, s=1.35, flip=1, mouth="open", eyes="closed")
    # a small, true note slipping out, ringed by its own little echo
    for i in range(3):
        layer.circle([720, 430], 40 + i * 34, fill="none",
                     stroke=a(GLOW_GOLD, f"{max(20, 90 - i * 22):02X}"),
                     stroke_style={"stroke_width": 2.5})
    glow(layer, 720, 430, 44, color=GLOW_GOLD, aa="66")
    bubble(layer, 720, 430, 8)
    vignette(layer, edge_aa="9E")
    caption(layer, "Marina breathed in… and a small, true note slipped out.")
    page_number(layer)


def page_grows(builder):
    layer = page(builder, "p-grows")
    water(layer, vgrad(MID_TOP, DEEP_TOP, (MID_LOW, "58%")))
    god_rays(layer, 600, top=-20, rays=5, spread=560, length=520, aa="18")
    motes(layer, 80, 840, rows=3)
    # song rings, bigger now, full of gathering fish
    for i in range(5):
        layer.circle([560, 440], 80 + i * 90, fill="none",
                     stroke=a(GLOW_GOLD, f"{max(14, 70 - i * 12):02X}"),
                     stroke_style={"stroke_width": 2.5})
    draw_whale(layer, 540, 470, s=1.2, flip=1, mouth="open")
    school(layer, 880, 320, n=9, spread=140, color="#7FE0D2")
    school(layer, 300, 680, n=6, spread=110, color=a(JELLY, "FF"), flip=-1)
    glow(layer, 540, 440, 60, color=GLOW_GOLD, aa="44")
    vignette(layer)
    caption(layer, "The little note grew braver, and the fish all came to listen.")
    page_number(layer)


def page_rise(builder):
    layer = page(builder, "p-rise")
    water(layer, vgrad(SHALLOW_TOP, DEEP_TOP, (SHALLOW_LOW, "40%"), (MID_LOW, "72%")))
    god_rays(layer, 600, rays=7, spread=820, length=900, aa="30")
    caustics(layer, 70, count=11, aa="50")
    motes(layer, 120, 860, rows=3)
    draw_whale(layer, 560, 560, s=1.25, flip=1, mouth="open", eyes="closed")
    bubble_trail(layer, 470, 470, n=12, rise=34)
    bubble_trail(layer, 700, 520, n=9, rise=30, sway=16)
    for i in range(4):
        layer.circle([560, 540], 70 + i * 80, fill="none",
                     stroke=a(GLOW_GOLD, f"{max(16, 64 - i * 12):02X}"),
                     stroke_style={"stroke_width": 2.5})
    vignette(layer, edge_aa="6A")
    caption(layer, "Up and up she rose, her song rising with her.")
    page_number(layer)


def page_surface(builder):
    layer = page(builder, "p-surface")
    # night sky above, dark water below, split at the surface line
    water(layer, vgrad(SURFACE_NIGHT_TOP, SURFACE_NIGHT_LOW, ("#10406A", "100%")))
    layer.rect([0, 430, W, H - 430], fill=vgrad("#1C5A86", "#0A2C49"))
    starfield(layer, upto=400)
    moon(layer, 940, 200, 92)
    # surface line + foam where Marina breaks through
    layer.path(Path().move_to(0, 430).through([(300, 422), (600, 436), (900, 424), (W, 432)]),
               fill="none", stroke=a(FOAM, "AA"), stroke_style={"stroke_width": 3})
    glow(layer, 520, 430, 150, color="#CFEFFF", aa="3A")
    for i in range(10):
        bubble(layer, 380 + i * 34, 430 - (i % 3) * 14, 4 + (i % 3) * 3)
    draw_whale(layer, 520, 540, s=1.3, flip=1, mouth="open", spout=True)
    # moon's reflection on the water
    for ry, rw in [(470, 70), (510, 90), (550, 60)]:
        layer.line([940 - rw, ry], [940 + rw, ry], **{"stroke": a(MOON_SEA, "66"),
                   "stroke_style": {"stroke_width": 3, "stroke_linecap": "round"}})
    vignette(layer, color="#04122A", edge_aa="8A")
    caption(layer, "She broke the surface beneath a sky full of stars.")
    page_number(layer)


def page_sing(builder):
    layer = page(builder, "p-sing")
    water(layer, vgrad(SURFACE_NIGHT_TOP, "#0A2C49", ("#123A5C", "55%")))
    starfield(layer, upto=420)
    moon(layer, 320, 230, 80)
    for x, y, r in [(640, 150, 6), (980, 220, 7), (820, 320, 5), (1100, 360, 6)]:
        star(layer, x, y, r, fill=GLOW_GOLD)
    layer.rect([0, 470, W, H - 470], fill=vgrad("#15527E", "#0A2C49"))
    layer.path(Path().move_to(0, 470).through([(350, 462), (700, 478), (W, 466)]),
               fill="none", stroke=a(FOAM, "99"), stroke_style={"stroke_width": 3})
    draw_whale(layer, 700, 600, s=1.35, flip=-1, mouth="open", eyes="closed")
    # her song rising toward the moon as golden rings
    for i in range(5):
        layer.circle([560, 540], 60 + i * 70, fill="none",
                     stroke=a(GLOW_GOLD, f"{max(16, 70 - i * 12):02X}"),
                     stroke_style={"stroke_width": 2.5})
    for i, (bx, by) in enumerate([(470, 470), (430, 400), (390, 330), (360, 270)]):
        star(layer, bx, by, 10 - i, fill=a(GLOW_GOLD, "EE"))
    vignette(layer, color="#04122A", edge_aa="84")
    caption(layer, "And there, under the moon, Marina sang her very own song at last.")
    page_number(layer)


def page_end(builder):
    layer = page(builder, "p-end")
    water(layer, vgrad(SURFACE_NIGHT_TOP, "#0A2C49"))
    starfield(layer, upto=520)
    moon(layer, 940, 210, 78)
    layer.rect([0, 560, W, H - 560], fill=vgrad("#123A5C", "#081F37"))
    layer.path(Path().move_to(0, 560).through([(400, 552), (820, 568), (W, 556)]),
               fill="none", stroke=a(FOAM, "88"), stroke_style={"stroke_width": 3})
    draw_whale(layer, 560, 650, s=1.1, flip=1, mouth="smile", eyes="closed")
    bubble_trail(layer, 690, 600, n=5)
    layer.text([0, 350, W, 90], "The End", style={"class": "theend"})
    layer.text([0, 460, W, 44], "Good night, little song.",
               style={"class": "subtitle", "color": "#CDEAF4", "letter_spacing": 2})
    vignette(layer, color="#04122A", edge_aa="80")
    page_number(layer)


# --------------------------------------------------------------------------- #
# Assemble                                                                     #
# --------------------------------------------------------------------------- #

def build_book() -> DocumentBuilder:
    global _page_no
    _page_no = 0
    builder = DocumentBuilder(title="Marina and the Singing Sea", profile="deck", lang="en")
    theme(builder, styles=STYLES)

    page_cover(builder)
    page_dedication(builder)
    page_shallows(builder)
    page_nosong(builder)
    page_jelly(builder)
    page_descend(builder)
    page_turtle(builder)
    page_deep(builder)
    page_hear(builder)
    page_great(builder)
    page_note(builder)
    page_grows(builder)
    page_rise(builder)
    page_surface(builder)
    page_sing(builder)
    page_end(builder)
    return builder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yaml", default=os.path.join(ROOT, "static", "examples", "marina-whale.fg.yaml"))
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "marina"))
    args = ap.parse_args()

    builder = build_book()
    doc = builder.build()
    print(f"Built book: {len(doc.pages)} pages")

    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity == "warning"]
    print(f"Validation: ok={report.ok}  errors={len(errors)}  warnings={len(warns)}")
    for i in errors[:30]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    if warns:
        from collections import Counter
        for code, c in Counter(i.rule_id for i in warns).most_common():
            print(f"  warn x{c}: {code}")

    os.makedirs(os.path.dirname(args.yaml), exist_ok=True)
    with open(args.yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {args.yaml}")

    if args.render:
        from framegraph.sdk.conform import render_page_svgs
        svgs = render_page_svgs(doc, base_dir=ROOT)
        os.makedirs(args.out, exist_ok=True)
        for idx, svg in enumerate(svgs, 1):
            with open(os.path.join(args.out, f"page-{idx:02d}.svg"), "w", encoding="utf-8") as fh:
                fh.write(svg)
        print(f"Rendered {len(svgs)} SVG pages to {args.out}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
