#!/usr/bin/env python3
"""Starlight Fox — a children's picture book authored entirely with the FrameForge SDK.

Every page is a hand-composed *illustration*: there are no external image assets.
The fox, the little star, the moon, the rolling hills, the silver pond, the owl
and the tall trees are all drawn from geometry primitives exposed by
:mod:`frameforge.sdk` — ``Path`` (Bézier / Catmull-Rom curves), polylines,
ellipses, gradient fills and the ``Frame`` mapping helper. The story text is set
through the same builder, and the whole book is validated against the
authoritative model before it is serialised.

Run from the repository root::

    uv run python examples/starlight_fox.py             # build + validate + write YAML
    uv run python examples/starlight_fox.py --render    # also write per-page SVGs to out/starlight/

The book is a 15-page bedtime story: a little fox named Pip finds a fallen star
and carries it back up to the night sky.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

# Make the SDK importable when run straight from the repo, and undo the
# package/module name clash the SDK tests document.
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    Path,
    serialize,
    theme,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas & palette                                                            #
# --------------------------------------------------------------------------- #

W, H = 1200, 900
CANVAS = {"size": [W, H], "units": "px"}

# Foxes
FOX = "#E8743B"
FOX_DK = "#C2511F"
FOX_LT = "#F4A269"
CREAM = "#FBEEDC"
NOSE = "#3A2A2E"
INK = "#332A33"

# Star
GOLD = "#FCC23D"
GOLD_DK = "#E0A11E"
GOLD_LT = "#FFE08A"
BLUSH = "#F7A1A1"

# Sky & land
NIGHT_TOP = "#1B1B3A"
NIGHT_MID = "#39306B"
NIGHT_LOW = "#7C5C8E"
DUSK_TOP = "#2E2A5C"
DUSK_LOW = "#E59B7B"
DAY_TOP = "#9AD7F0"
DAY_LOW = "#E7F6FB"
HILL_A = "#3E6B52"
HILL_B = "#345C46"
HILL_C = "#2A4C3A"
HILL_NIGHT_A = "#2C3F58"
HILL_NIGHT_B = "#233247"
HILL_NIGHT_C = "#1B2738"
TRUNK = "#6E4A33"
LEAF = "#3E6B52"
LEAF_DK = "#345C46"
POND = "#2C4F6E"
POND_LT = "#5C86A6"
MOON = "#FBF2C4"
MOON_SEA = "#EBDFA6"
PAPER = "#FBF4E6"

SANS = ["Quicksand", "Baloo 2", "Nunito", "Comic Sans MS", "sans-serif"]
SERIF = ["Fraunces", "Georgia", "Cambria", "serif"]

STYLES = {
    "title": {"font_family": SERIF, "font_size": 78, "font_weight": 700,
              "color": "#FFF7E8", "line_height": 1.02, "align": "center"},
    "subtitle": {"font_family": SANS, "font_size": 26, "font_weight": 500,
                 "color": "#FBE0C2", "line_height": 1.3, "align": "center",
                 "letter_spacing": 1.5},
    "byline": {"font_family": SANS, "font_size": 17, "font_weight": 500,
               "color": "#D9C7E0", "align": "center", "letter_spacing": 2},
    "story": {"font_family": SERIF, "font_size": 31, "font_weight": 500,
              "color": "#42323A", "line_height": 1.4, "align": "center"},
    "story_d": {"font_family": SERIF, "font_size": 31, "font_weight": 500,
                "color": "#FBF2DF", "line_height": 1.4, "align": "center"},
    "dedicate": {"font_family": SERIF, "font_size": 27, "font_weight": 500,
                 "color": "#5A4A52", "line_height": 1.5, "align": "center"},
    "pnum": {"font_family": SANS, "font_size": 18, "font_weight": 600,
             "color": "#C9B79E", "align": "center"},
    "theend": {"font_family": SERIF, "font_size": 60, "font_weight": 700,
               "color": "#FFF7E8", "align": "center"},
}

_page_no = 0


# --------------------------------------------------------------------------- #
# Tiny drawing vocabulary                                                      #
# --------------------------------------------------------------------------- #

def new_page(builder, pid):
    return builder.page(pid, canvas=CANVAS, coordinate_mode="absolute").layer("art")


def stroke(width, color=INK, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": width, **extra}}


# These wrap the SDK's typed PageBuilder primitives (layer.ellipse / .polyline)
# with a terse stroke shorthand (sw = width, sc = colour) for the artwork below.
def _stroke_fields(sw, sc, extra):
    f = dict(extra)
    if sw is not None:
        f["stroke"] = sc
        f["stroke_style"] = {"stroke_width": sw}
    return f


def ellipse(layer, cx, cy, rx, ry, fill=None, sw=None, sc=INK, **extra):
    f = _stroke_fields(sw, sc, extra)
    if fill is not None:
        f["fill"] = fill
    layer.ellipse([cx, cy], rx, ry, **f)


def poly(layer, points, fill=None, sw=None, sc=INK, closed=True):
    f = _stroke_fields(sw, sc, {})
    if fill is not None:
        f["fill"] = fill
    layer.polyline(points, closed=closed, **f)


def vgradient(top, low, *mid):
    """A vertical (top→bottom) linear-gradient paint."""
    stops = [{"color": top, "position": "0%"}]
    for color, pos in mid:
        stops.append({"color": color, "position": pos})
    stops.append({"color": low, "position": "100%"})
    return {"kind": "linear", "angle": 180, "stops": stops}


def radial(inner, outer, at="50% 50%"):
    return {"kind": "radial", "at": at,
            "stops": [{"color": inner, "position": "0%"},
                      {"color": outer, "position": "100%"}]}


def sky(layer, paint):
    layer.rect([0, 0, W, H], fill=paint)


# --------------------------------------------------------------------------- #
# Stars, moon, sparkles                                                        #
# --------------------------------------------------------------------------- #

def star_pts(cx, cy, r, inner=0.42, n=5, rot=-90.0):
    pts = []
    for i in range(n * 2):
        ang = math.radians(rot + i * 180.0 / n)
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    return pts


def star_shape(layer, cx, cy, r, fill=GOLD, sw=None, sc=GOLD_DK, inner=0.42, rot=-90.0):
    poly(layer, star_pts(cx, cy, r, inner=inner, rot=rot), fill=fill, sw=sw, sc=sc)


def sparkle(layer, cx, cy, r, color="#FFFFFF"):
    """A soft four-point twinkle."""
    poly(layer, [(cx, cy - r), (cx + r * 0.22, cy - r * 0.22),
                 (cx + r, cy), (cx + r * 0.22, cy + r * 0.22),
                 (cx, cy + r), (cx - r * 0.22, cy + r * 0.22),
                 (cx - r, cy), (cx - r * 0.22, cy - r * 0.22)], fill=color)


# A fixed scatter of background stars (deterministic, no RNG needed).
_STARFIELD = [
    (90, 70, 5), (180, 140, 3), (250, 60, 6), (330, 120, 3), (410, 80, 4),
    (520, 50, 5), (610, 130, 3), (700, 70, 4), (790, 150, 3), (880, 60, 6),
    (970, 120, 3), (1050, 70, 4), (1130, 140, 5), (140, 230, 4), (300, 250, 3),
    (470, 210, 5), (660, 240, 3), (840, 220, 4), (1010, 250, 5), (1140, 300, 3),
    (60, 320, 4), (230, 360, 3), (400, 330, 4), (560, 380, 3), (760, 340, 5),
    (930, 370, 3), (1090, 410, 4),
]


def starfield(layer, density=1.0, color="#FFF7E0", upto=None):
    for x, y, r in _STARFIELD:
        if upto is not None and y > upto:
            continue
        star_shape(layer, x, y, r * density, fill=color, sc=color)


def moon(layer, cx, cy, r, glow=True):
    if glow:
        ellipse(layer, cx, cy, r * 1.9, r * 1.9, fill=radial("#FFF7D880", "#FFF7D800"))
    ellipse(layer, cx, cy, r, r, fill=MOON)
    for dx, dy, rr in [(-0.35, -0.25, 0.18), (0.3, 0.1, 0.14), (-0.1, 0.4, 0.12),
                       (0.4, -0.4, 0.1), (-0.45, 0.2, 0.09)]:
        ellipse(layer, cx + dx * r, cy + dy * r, rr * r, rr * r, fill=MOON_SEA)


def crescent(layer, cx, cy, r):
    ellipse(layer, cx, cy, r, r, fill=MOON)
    ellipse(layer, cx + r * 0.45, cy - r * 0.15, r * 0.92, r * 0.92, fill=NIGHT_TOP)


# --------------------------------------------------------------------------- #
# Landscape elements                                                          #
# --------------------------------------------------------------------------- #

def hill(layer, base_y, crest_y, fill, x0=-40, x1=W + 40, bow=None):
    """A soft rolling hill filling from a crest curve down to the page bottom."""
    if bow is None:
        bow = [( (x0 + x1) / 2, crest_y )]
    top = [(x0, base_y)] + [(bx, by) for bx, by in bow] + [(x1, base_y)]
    p = Path().move_to(top[0][0], top[0][1]).through(top[1:])
    p.line_to(x1, H + 40).line_to(x0, H + 40).close()
    layer.add(p.object(fill=fill))


def tree(layer, x, base_y, s=1.0, leaf=LEAF, leaf_dk=LEAF_DK, trunk=TRUNK):
    """A round storybook tree: a trunk and three overlapping leaf clouds."""
    tw = 26 * s
    layer.rect([x - tw / 2, base_y - 150 * s, tw, 160 * s], fill=trunk, radius=tw / 2)
    ellipse(layer, x, base_y - 250 * s, 120 * s, 110 * s, fill=leaf_dk)
    ellipse(layer, x - 70 * s, base_y - 210 * s, 80 * s, 74 * s, fill=leaf)
    ellipse(layer, x + 72 * s, base_y - 205 * s, 84 * s, 78 * s, fill=leaf)
    ellipse(layer, x, base_y - 300 * s, 92 * s, 86 * s, fill=leaf)


def pine(layer, x, base_y, s=1.0, fill=HILL_NIGHT_C):
    for i, (w, top, bot) in enumerate([(64, 120, 64), (52, 80, 28), (40, 44, 0)]):
        poly(layer, [(x, base_y - top * s), (x - w * s, base_y - bot * s),
                     (x + w * s, base_y - bot * s)], fill=fill)
    layer.rect([x - 6 * s, base_y, 12 * s, 22 * s], fill=TRUNK)


def cloud(layer, cx, cy, s=1.0, fill="#FFFFFF"):
    ellipse(layer, cx, cy, 70 * s, 44 * s, fill=fill)
    ellipse(layer, cx - 64 * s, cy + 12 * s, 48 * s, 36 * s, fill=fill)
    ellipse(layer, cx + 66 * s, cy + 14 * s, 52 * s, 38 * s, fill=fill)
    ellipse(layer, cx + 6 * s, cy + 22 * s, 80 * s, 40 * s, fill=fill)


def sun(layer, cx, cy, r, fill="#FFD86B"):
    ellipse(layer, cx, cy, r * 2.1, r * 2.1, fill=radial("#FFE9A855", "#FFE9A800"))
    for i in range(12):
        a = math.radians(i * 30)
        x0, y0 = cx + r * 1.25 * math.cos(a), cy + r * 1.25 * math.sin(a)
        x1, y1 = cx + r * 1.7 * math.cos(a), cy + r * 1.7 * math.sin(a)
        layer.line([x0, y0], [x1, y1], **stroke(6, fill, stroke_linecap="round"))
    ellipse(layer, cx, cy, r, r, fill=fill)


# --------------------------------------------------------------------------- #
# The fox                                                                      #
# --------------------------------------------------------------------------- #

def draw_fox(layer, cx, cy, s=1.0, flip=1, eyes="open", curl=False):
    """Draw Pip the fox. (cx, cy) is the centre of the body.

    ``flip`` is +1 (facing right) or -1 (facing left); ``eyes`` is "open" or
    "closed"; ``curl`` draws the fox curled up asleep instead of sitting.
    """
    def px(dx, dy):
        return (cx + flip * dx * s, cy + dy * s)

    def rb(dx, dy, w, h):
        x0 = cx + flip * dx * s
        x1 = cx + flip * (dx + w) * s
        return [min(x0, x1), cy + dy * s, abs(x1 - x0), h * s]

    if curl:
        _draw_fox_curled(layer, cx, cy, s, flip, eyes)
        return

    # --- tail (behind the body) ---
    tail = (Path().move_to(*px(-38, -8))
            .through([px(-74, -20), px(-104, 2), px(-98, 40), px(-66, 50), px(-42, 24)])
            .close())
    layer.add(tail.object(fill=FOX, stroke=FOX_DK, stroke_style={"stroke_width": 3 * s}))
    ellipse(layer, *px(-92, 28), 26 * s, 28 * s, fill=CREAM)

    # --- hind leg + front legs ---
    ellipse(layer, *px(-22, 44), 20 * s, 24 * s, fill=FOX_DK)
    layer.rect(rb(2, 30, 16, 40), fill=FOX, radius=8 * s)
    layer.rect(rb(26, 30, 16, 40), fill=FOX_LT, radius=8 * s)
    ellipse(layer, *px(10, 70), 11 * s, 8 * s, fill=CREAM)
    ellipse(layer, *px(34, 70), 11 * s, 8 * s, fill=CREAM)

    # --- body & chest ---
    ellipse(layer, *px(-2, 12), 54 * s, 44 * s, fill=FOX)
    ellipse(layer, *px(20, 26), 28 * s, 32 * s, fill=CREAM)

    # --- head ---
    ellipse(layer, *px(34, -32), 36 * s, 34 * s, fill=FOX)
    # ears
    poly(layer, [px(12, -54), px(2, -96), px(30, -64)], fill=FOX, sw=2.5 * s, sc=FOX_DK)
    poly(layer, [px(40, -64), px(58, -94), px(62, -52)], fill=FOX, sw=2.5 * s, sc=FOX_DK)
    poly(layer, [px(14, -58), px(9, -84), px(26, -64)], fill=FOX_DK)
    poly(layer, [px(44, -62), px(55, -82), px(57, -56)], fill=FOX_DK)
    # cheek fluff + muzzle
    poly(layer, [px(20, -34), px(8, -16), px(30, -12)], fill=CREAM)
    muzzle = (Path().move_to(*px(34, -40)).through([px(72, -30), px(74, -16), px(36, -10)]).close())
    layer.add(muzzle.object(fill=CREAM))
    ellipse(layer, *px(72, -22), 7 * s, 6 * s, fill=NOSE)
    # eyes
    if eyes == "open":
        for ex, ey in [px(26, -38), px(48, -36)]:
            ellipse(layer, ex, ey, 4.6 * s, 5.6 * s, fill=INK)
            ellipse(layer, ex + 1.5 * s, ey - 2 * s, 1.6 * s, 1.6 * s, fill="#FFFFFF")
    else:
        for ex, ey in [px(26, -38), px(48, -36)]:
            arc = Path().move_to(ex - 5 * s, ey).quad_to((ex, ey + 5 * s), (ex + 5 * s, ey))
            layer.add(arc.object(fill="none", stroke=INK, stroke_style={"stroke_width": 2.4 * s}))


def _draw_fox_curled(layer, cx, cy, s, flip, eyes):
    def px(dx, dy):
        return (cx + flip * dx * s, cy + dy * s)
    # curled body as a fat crescent
    body = (Path().move_to(*px(-86, 6))
            .through([px(-60, -44), px(0, -58), px(64, -34), px(86, 14),
                      px(40, 40), px(-30, 42)])
            .close())
    layer.add(body.object(fill=FOX, stroke=FOX_DK, stroke_style={"stroke_width": 3 * s}))
    # tail wrapping around the front, cream tip resting by the nose
    tail = (Path().move_to(*px(-78, 8))
            .through([px(-96, -20), px(-70, -36), px(-34, -22), px(-6, -2), px(24, 14)])
            .close())
    layer.add(tail.object(fill=FOX_LT, stroke=FOX_DK, stroke_style={"stroke_width": 2.5 * s}))
    ellipse(layer, *px(22, 12), 22 * s, 20 * s, fill=CREAM)
    # head tucked
    ellipse(layer, *px(58, 2), 30 * s, 28 * s, fill=FOX)
    poly(layer, [px(48, -22), px(40, -52), px(64, -32)], fill=FOX, sw=2.5 * s, sc=FOX_DK)
    poly(layer, [px(70, -30), px(86, -50), px(86, -22)], fill=FOX, sw=2.5 * s, sc=FOX_DK)
    poly(layer, [px(50, -26), px(46, -44), px(60, -32)], fill=FOX_DK)
    ellipse(layer, *px(74, 8), 18 * s, 14 * s, fill=CREAM)
    ellipse(layer, *px(86, 6), 6 * s, 5 * s, fill=NOSE)
    for ex, ey in [px(56, -4), px(72, -2)]:
        arc = Path().move_to(ex - 5 * s, ey).quad_to((ex, ey + 5 * s), (ex + 5 * s, ey))
        layer.add(arc.object(fill="none", stroke=INK, stroke_style={"stroke_width": 2.4 * s}))


# --------------------------------------------------------------------------- #
# The little star (a character with a face)                                    #
# --------------------------------------------------------------------------- #

def draw_star_char(layer, cx, cy, r, glow=True, eyes="open", rot=-90.0):
    if glow:
        ellipse(layer, cx, cy, r * 2.6, r * 2.6, fill=radial("#FFE89066", "#FFE89000"))
    star_shape(layer, cx, cy, r, fill=GOLD, sw=3.0, sc=GOLD_DK, rot=rot)
    star_shape(layer, cx, cy - r * 0.04, r * 0.66, fill=GOLD_LT, rot=rot)
    # face sits in the middle of the star body
    ex = r * 0.26
    ey = -r * 0.04
    if eyes == "open":
        for sgn in (-1, 1):
            ellipse(layer, cx + sgn * ex, cy + ey, r * 0.085, r * 0.11, fill=INK)
            ellipse(layer, cx + sgn * ex + r * 0.03, cy + ey - r * 0.04,
                    r * 0.03, r * 0.03, fill="#FFFFFF")
    else:
        for sgn in (-1, 1):
            a = Path().move_to(cx + sgn * ex - r * 0.1, cy + ey)
            a.quad_to((cx + sgn * ex, cy + ey + r * 0.1), (cx + sgn * ex + r * 0.1, cy + ey))
            layer.add(a.object(fill="none", stroke=INK, stroke_style={"stroke_width": r * 0.04}))
    # rosy cheeks + smile
    ellipse(layer, cx - ex - r * 0.04, cy + r * 0.16, r * 0.08, r * 0.05, fill=BLUSH)
    ellipse(layer, cx + ex + r * 0.04, cy + r * 0.16, r * 0.08, r * 0.05, fill=BLUSH)
    smile = Path().move_to(cx - r * 0.14, cy + r * 0.12)
    smile.quad_to((cx, cy + r * 0.30), (cx + r * 0.14, cy + r * 0.12))
    layer.add(smile.object(fill="none", stroke=INK, stroke_style={"stroke_width": r * 0.045,
                                                                   "stroke_linecap": "round"}))


def shooting_star(layer, x0, y0, x1, y1, r=18, color=GOLD):
    # tapering trail
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / ln, dx / ln
    poly(layer, [(x0 + nx * r * 0.7, y0 + ny * r * 0.7),
                 (x0 - nx * r * 0.7, y0 - ny * r * 0.7), (x1, y1)],
         fill=radial(GOLD_LT, "#FFE08A00", at="0% 0%"))
    poly(layer, [(x0 + nx * r * 0.4, y0 + ny * r * 0.4),
                 (x0 - nx * r * 0.4, y0 - ny * r * 0.4), (x1, y1)], fill="#FFFFFF")
    star_shape(layer, x1, y1, r, fill=color, sc=GOLD_DK, sw=2)


# --------------------------------------------------------------------------- #
# The owl                                                                      #
# --------------------------------------------------------------------------- #

def draw_owl(layer, cx, cy, s=1.0):
    ellipse(layer, cx, cy, 46 * s, 56 * s, fill="#7B6A86")          # body
    ellipse(layer, cx, cy + 18 * s, 34 * s, 40 * s, fill="#9A89A6")  # belly
    poly(layer, [(cx - 46 * s, cy - 30 * s), (cx - 30 * s, cy - 70 * s),
                 (cx - 12 * s, cy - 36 * s)], fill="#6A5A76")        # ear tufts
    poly(layer, [(cx + 46 * s, cy - 30 * s), (cx + 30 * s, cy - 70 * s),
                 (cx + 12 * s, cy - 36 * s)], fill="#6A5A76")
    for sgn in (-1, 1):                                              # big eyes
        ellipse(layer, cx + sgn * 20 * s, cy - 18 * s, 19 * s, 19 * s, fill="#FBF2DF")
        ellipse(layer, cx + sgn * 20 * s, cy - 18 * s, 9 * s, 9 * s, fill=INK)
        ellipse(layer, cx + sgn * 20 * s + 3 * s, cy - 21 * s, 3 * s, 3 * s, fill="#FFFFFF")
    poly(layer, [(cx - 7 * s, cy - 8 * s), (cx + 7 * s, cy - 8 * s),
                 (cx, cy + 6 * s)], fill=GOLD)                       # beak
    for sgn in (-1, 1):                                             # wings
        wing = Path().move_to(cx + sgn * 44 * s, cy - 8 * s)
        wing.through([(cx + sgn * 58 * s, cy + 20 * s), (cx + sgn * 40 * s, cy + 40 * s)]).close()
        layer.add(wing.object(fill="#6A5A76"))


# --------------------------------------------------------------------------- #
# Caption + page chrome                                                        #
# --------------------------------------------------------------------------- #

def caption(layer, text, *, dark=False, y=744, h=126):
    band = "#241F3A" if dark else PAPER
    cls = "story_d" if dark else "story"
    layer.rect([110, y, W - 220, h], fill=band, radius=28,
               stroke=("#3A335A" if dark else "#EAD9BC"),
               stroke_style={"stroke_width": 2})
    # Generous text box so two-line captions never clip; the proxy renderer
    # wraps long lines and would otherwise crop the overflow.
    layer.text([150, y + 20, W - 300, h - 34], text, style={"class": cls})


def page_number(layer, dark=False):
    global _page_no
    layer.text([W / 2 - 40, 858, 80, 26], f"{_page_no}",
               style={"class": "pnum", "color": ("#6A6080" if dark else "#C9B79E")})


def page(builder, pid):
    global _page_no
    _page_no += 1
    return new_page(builder, pid)


# --------------------------------------------------------------------------- #
# Pages                                                                        #
# --------------------------------------------------------------------------- #

def page_cover(builder):
    layer = page(builder, "cover")
    sky(layer, vgradient(NIGHT_TOP, NIGHT_LOW, (NIGHT_MID, "55%")))
    starfield(layer, density=1.1)
    moon(layer, 980, 210, 96)
    for x, y, r in [(150, 300, 9), (1080, 430, 7), (300, 180, 6), (760, 250, 8)]:
        sparkle(layer, x, y, r)
    # hills
    hill(layer, 700, 560, HILL_NIGHT_C, bow=[(300, 600), (700, 520), (1000, 590)])
    hill(layer, 760, 640, "#16202F", bow=[(420, 690), (820, 600)])
    # a tree on the hill and the fox gazing up
    tree(layer, 250, 720, s=0.9, leaf=HILL_NIGHT_B, leaf_dk=HILL_NIGHT_C, trunk="#4A3526")
    draw_fox(layer, 760, 690, s=1.3, flip=-1)
    draw_star_char(layer, 905, 330, 40)
    # title
    layer.text([0, 250, W, 100], "Starlight Fox", style={"class": "title"})
    layer.text([0, 372, W, 40], "A BEDTIME STORY", style={"class": "subtitle"})
    layer.text([0, 832, W, 30], "drawn entirely with the FrameForge SDK",
               style={"class": "byline"})


def page_dedication(builder):
    layer = page(builder, "dedication")
    sky(layer, vgradient("#FBF4E6", "#F3E7D0"))
    for x, y, r in [(160, 140, 10), (1040, 180, 12), (240, 760, 9),
                    (980, 720, 11), (600, 110, 7)]:
        star_shape(layer, x, y, r, fill=GOLD_LT, sc=GOLD)
    draw_star_char(layer, 600, 360, 70)
    layer.text([200, 520, W - 400, 120],
               "For everyone, big or small,\nwho looks up and makes a wish.",
               style={"class": "dedicate"})
    page_number(layer)


def page_den(builder):
    layer = page(builder, "p-den")
    sky(layer, vgradient(DAY_TOP, DAY_LOW, ("#C9ECF6", "60%")))
    sun(layer, 200, 180, 70)
    cloud(layer, 520, 150, s=0.8)
    cloud(layer, 940, 230, s=1.0)
    hill(layer, 560, 420, "#8FCB7B", bow=[(280, 470), (760, 380), (1040, 450)])
    hill(layer, 660, 560, HILL_A, bow=[(360, 600), (820, 520)])
    tree(layer, 980, 690, s=1.05)
    # the den: a dark burrow under a grassy mound
    ellipse(layer, 360, 700, 150, 96, fill=HILL_B)
    ellipse(layer, 360, 716, 70, 60, fill="#1F1A1E")
    draw_fox(layer, 360, 690, s=1.05, flip=1)
    caption(layer, "Pip the fox lived in a cosy den at the edge of the Whispering Wood.")
    page_number(layer)


def page_dusk(builder):
    layer = page(builder, "p-dusk")
    sky(layer, vgradient(DUSK_TOP, DUSK_LOW, ("#6E4F86", "45%"), ("#C97C7C", "78%")))
    starfield(layer, density=0.8, color="#FFF7E0", upto=300)
    crescent(layer, 980, 170, 70)
    hill(layer, 640, 500, "#6E5A86", bow=[(300, 540), (780, 470), (1040, 520)])
    hill(layer, 720, 600, "#4E3E66", bow=[(420, 640), (860, 560)])
    pine(layer, 200, 720, s=1.0, fill="#2E2746")
    pine(layer, 1040, 700, s=0.8, fill="#2E2746")
    draw_fox(layer, 560, 660, s=1.15, flip=1)
    for x, y, r in [(420, 220, 5), (640, 160, 6), (760, 250, 4)]:
        sparkle(layer, x, y, r, color="#FFF7E0")
    caption(layer, "Each night, when the sky turned violet, Pip watched the first stars wake up.")
    page_number(layer)


def page_fall(builder):
    layer = page(builder, "p-fall")
    sky(layer, vgradient(NIGHT_TOP, NIGHT_LOW, (NIGHT_MID, "60%")))
    starfield(layer, density=1.0)
    crescent(layer, 180, 160, 56)
    hill(layer, 700, 580, HILL_NIGHT_C, bow=[(300, 620), (760, 540), (1040, 600)])
    pine(layer, 980, 740, s=1.0)
    shooting_star(layer, 280, 150, 820, 470, r=22)
    draw_fox(layer, 520, 700, s=1.0, flip=1, eyes="open")
    caption(layer, "One night a star slipped — and tumbled down, down, down…", dark=True)
    page_number(layer, dark=True)


def page_land(builder):
    layer = page(builder, "p-land")
    sky(layer, vgradient(NIGHT_TOP, "#6E5C8E", (NIGHT_MID, "58%")))
    starfield(layer, density=0.9, upto=380)
    moon(layer, 1020, 200, 70)
    hill(layer, 560, 470, HILL_NIGHT_B, bow=[(300, 510), (820, 440), (1040, 500)])
    hill(layer, 660, 600, HILL_NIGHT_C, bow=[(400, 640), (860, 560)])
    # tall grass tufts
    for gx in range(120, 1120, 46):
        gy = 700 + 18 * math.sin(gx * 0.05)
        layer.line([gx, gy], [gx - 10, gy - 46], **stroke(3, "#2C4A38", stroke_linecap="round"))
        layer.line([gx, gy], [gx + 10, gy - 50], **stroke(3, "#356041", stroke_linecap="round"))
    draw_star_char(layer, 470, 650, 46)
    draw_fox(layer, 760, 678, s=1.0, flip=-1, eyes="open")
    for x, y, r in [(470, 580, 6), (520, 640, 4), (420, 630, 4)]:
        sparkle(layer, x, y, r, color=GOLD_LT)
    caption(layer, "It landed in the tall grass with a soft, twinkly thump.", dark=True)
    page_number(layer, dark=True)


def page_meet(builder):
    layer = page(builder, "p-meet")
    sky(layer, vgradient(NIGHT_TOP, "#5A4A7E", (NIGHT_MID, "62%")))
    starfield(layer, density=0.8, upto=420)
    moon(layer, 150, 180, 58)
    hill(layer, 720, 640, HILL_NIGHT_C, bow=[(360, 680), (820, 600)])
    # the fox and the star, close together, looking at each other
    draw_star_char(layer, 470, 470, 78, eyes="open")
    draw_fox(layer, 820, 640, s=1.5, flip=-1, eyes="open")
    caption(layer, "“Hello,” said the little Star. “I have lost my way home.”", dark=True)
    page_number(layer, dark=True)


def page_climb_on(builder):
    layer = page(builder, "p-climbon")
    sky(layer, vgradient(NIGHT_TOP, NIGHT_LOW, (NIGHT_MID, "58%")))
    starfield(layer, density=0.9)
    crescent(layer, 1020, 170, 64)
    hill(layer, 620, 560, HILL_NIGHT_B, bow=[(280, 600), (760, 520), (1040, 580)])
    hill(layer, 720, 650, HILL_NIGHT_C, bow=[(420, 690), (860, 600)])
    # a winding path
    pathline = (Path().move_to(120, 760).through([(360, 720), (560, 700), (820, 650), (1080, 600)]))
    layer.add(pathline.object(fill="none", stroke="#5A6E84",
                              stroke_style={"stroke_width": 16, "stroke_dasharray": [4, 18],
                                            "stroke_linecap": "round"}))
    pine(layer, 200, 700, s=0.9)
    pine(layer, 1060, 660, s=0.7)
    draw_fox(layer, 540, 690, s=1.25, flip=1, eyes="open")
    draw_star_char(layer, 505, 560, 34)  # riding on the fox's back
    caption(layer, "“Climb on,” said Pip. “I know the tallest hill in the wood.”", dark=True)
    page_number(layer, dark=True)


def page_pond(builder):
    layer = page(builder, "p-pond")
    sky(layer, vgradient(NIGHT_TOP, "#4E5E86", (NIGHT_MID, "55%")))
    starfield(layer, density=0.9, upto=440)
    moon(layer, 880, 200, 78, glow=True)
    hill(layer, 460, 400, HILL_NIGHT_B, bow=[(300, 440), (820, 370), (1040, 430)])
    # the silver pond
    ellipse(layer, 600, 660, 480, 150, fill=POND)
    ellipse(layer, 600, 648, 470, 138, fill=radial("#7CA2C266", "#2C4F6E00"))
    # moon's reflection wobbling in the water
    ellipse(layer, 760, 690, 64, 22, fill=MOON_SEA)
    for ry in (665, 700, 735):
        layer.line([420, ry], [800, ry], **stroke(2.5, "#88AAC6", stroke_linecap="round"))
    draw_fox(layer, 270, 640, s=1.05, flip=1, eyes="open")
    draw_star_char(layer, 250, 540, 30)
    caption(layer, "They crossed the silver pond, where the Moon was swimming.", dark=True)
    page_number(layer, dark=True)


def page_owl(builder):
    layer = page(builder, "p-owl")
    sky(layer, vgradient(NIGHT_TOP, NIGHT_LOW, (NIGHT_MID, "60%")))
    starfield(layer, density=0.9)
    crescent(layer, 180, 170, 54)
    hill(layer, 720, 640, HILL_NIGHT_C, bow=[(360, 690), (840, 600)])
    # a big tree with the owl on a branch
    tree(layer, 820, 760, s=1.4, leaf=HILL_NIGHT_B, leaf_dk=HILL_NIGHT_C, trunk="#4A3526")
    layer.line([820, 560], [620, 520], **stroke(14, "#4A3526", stroke_linecap="round"))
    draw_owl(layer, 620, 470, s=1.0)
    draw_fox(layer, 360, 700, s=1.1, flip=1, eyes="open")
    draw_star_char(layer, 330, 590, 30)
    caption(layer, "A wise Owl hooted, “The highest branch is closest to the sky.”", dark=True)
    page_number(layer, dark=True)


def page_climb(builder):
    layer = page(builder, "p-climb")
    sky(layer, vgradient(NIGHT_TOP, NIGHT_MID, ("#2A2550", "70%")))
    starfield(layer, density=1.0)
    moon(layer, 1040, 150, 62)
    # one enormous tree filling the page; the fox climbing the trunk
    layer.rect([560, 240, 70, 560], fill=TRUNK, radius=18)
    layer.line([594, 520], [430, 470], **stroke(18, TRUNK, stroke_linecap="round"))
    layer.line([596, 380], [760, 330], **stroke(18, TRUNK, stroke_linecap="round"))
    for cxk, cyk, sk in [(595, 230, 1.6), (430, 430, 1.0), (770, 300, 1.0)]:
        ellipse(layer, cxk, cyk, 150 * sk, 130 * sk, fill=LEAF_DK)
        ellipse(layer, cxk - 90 * sk, cyk + 30 * sk, 90 * sk, 80 * sk, fill=LEAF)
        ellipse(layer, cxk + 92 * sk, cyk + 26 * sk, 96 * sk, 84 * sk, fill=LEAF)
    # little sleeping birds
    for bx, by in [(440, 430), (770, 300)]:
        ellipse(layer, bx, by, 16, 12, fill="#D7C7E6")
        arc = Path().move_to(bx - 8, by - 2).quad_to((bx - 4, by - 8), (bx, by - 2))
        layer.add(arc.object(fill="none", stroke=INK, stroke_style={"stroke_width": 2}))
    draw_fox(layer, 600, 600, s=1.0, flip=-1, eyes="open")
    draw_star_char(layer, 540, 520, 28)
    caption(layer, "Up and up they climbed, past sleeping birds and dreaming leaves.", dark=True)
    page_number(layer, dark=True)


def page_top(builder):
    layer = page(builder, "p-top")
    sky(layer, vgradient(NIGHT_TOP, "#6E5C8E", (NIGHT_MID, "55%")))
    starfield(layer, density=1.1)
    moon(layer, 990, 220, 88)
    for x, y, r in [(200, 320, 8), (1080, 470, 6), (320, 200, 6)]:
        sparkle(layer, x, y, r)
    # a small treetop platform of leaves at the summit
    hill(layer, 720, 660, HILL_NIGHT_C, bow=[(360, 700), (840, 620)])
    ellipse(layer, 600, 720, 220, 70, fill=LEAF_DK)
    ellipse(layer, 600, 700, 200, 60, fill=LEAF)
    # the fox stretching up, holding the star high
    draw_fox(layer, 600, 660, s=1.25, flip=1, eyes="open")
    layer.line([628, 612], [690, 470], **stroke(16, FOX, stroke_linecap="round"))  # raised arm
    draw_star_char(layer, 710, 410, 60)
    caption(layer, "At the very top, Pip held the Star up high.", dark=True)
    page_number(layer, dark=True)


def page_leap(builder):
    layer = page(builder, "p-leap")
    sky(layer, vgradient(NIGHT_TOP, NIGHT_LOW, (NIGHT_MID, "58%")))
    starfield(layer, density=1.0)
    moon(layer, 200, 200, 70)
    hill(layer, 760, 700, HILL_NIGHT_C, bow=[(360, 740), (840, 660)])
    # the star's golden leap arcing up into the sky
    arc = Path().move_to(560, 660).through([(640, 460), (820, 320), (1020, 220)])
    layer.add(arc.object(fill="none", stroke=radial(GOLD_LT, "#FFE08A00"),
                         stroke_style={"stroke_width": 10, "stroke_linecap": "round"}))
    arc2 = Path().move_to(560, 660).through([(640, 460), (820, 320), (1010, 230)])
    layer.add(arc2.object(fill="none", stroke="#FFFFFF",
                          stroke_style={"stroke_width": 3, "stroke_dasharray": [2, 14],
                                        "stroke_linecap": "round"}))
    draw_star_char(layer, 1020, 215, 40)
    draw_fox(layer, 520, 720, s=1.0, flip=1, eyes="open")
    caption(layer, "The Star leapt — a streak of gold — back into the night.", dark=True)
    page_number(layer, dark=True)


def page_bright(builder):
    layer = page(builder, "p-bright")
    sky(layer, vgradient(NIGHT_TOP, NIGHT_LOW, (NIGHT_MID, "56%")))
    starfield(layer, density=0.9)
    crescent(layer, 240, 180, 50)
    # one extra-bright star, just for Pip
    ellipse(layer, 880, 250, 130, 130, fill=radial("#FFE89055", "#FFE89000"))
    draw_star_char(layer, 880, 250, 44, eyes="closed")
    for x, y, r in [(760, 180, 6), (1000, 320, 7), (820, 360, 5)]:
        sparkle(layer, x, y, r, color=GOLD_LT)
    hill(layer, 660, 600, HILL_NIGHT_C, bow=[(320, 640), (820, 560)])
    pine(layer, 1040, 700, s=0.9)
    draw_fox(layer, 420, 660, s=1.2, flip=1, eyes="open")
    caption(layer, "And every night after, one star shone a little brighter, just for Pip.", dark=True)
    page_number(layer, dark=True)


def page_end(builder):
    layer = page(builder, "p-end")
    sky(layer, vgradient(NIGHT_TOP, "#2A2550"))
    starfield(layer, density=0.8, upto=520)
    moon(layer, 980, 220, 80)
    for x, y, r in [(200, 300, 7), (1060, 430, 6), (380, 200, 6), (700, 160, 7)]:
        sparkle(layer, x, y, r)
    hill(layer, 700, 640, HILL_NIGHT_C, bow=[(360, 690), (860, 600)])
    # Pip curled up asleep with the star tucked beside
    draw_fox(layer, 540, 640, s=1.3, curl=True)
    draw_star_char(layer, 690, 660, 26, eyes="closed", glow=True)
    layer.text([0, 360, W, 90], "The End", style={"class": "theend"})
    layer.text([0, 470, W, 50], "Good night.", style={"class": "subtitle",
                                                       "color": "#D9C7E0"})
    page_number(layer, dark=True)


# --------------------------------------------------------------------------- #
# Assemble                                                                     #
# --------------------------------------------------------------------------- #

def build_book() -> DocumentBuilder:
    global _page_no
    _page_no = 0
    builder = DocumentBuilder(title="Starlight Fox", profile="deck", lang="en")
    theme(builder, styles=STYLES)

    page_cover(builder)
    page_dedication(builder)
    page_den(builder)
    page_dusk(builder)
    page_fall(builder)
    page_land(builder)
    page_meet(builder)
    page_climb_on(builder)
    page_pond(builder)
    page_owl(builder)
    page_climb(builder)
    page_top(builder)
    page_leap(builder)
    page_bright(builder)
    page_end(builder)
    return builder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yaml", default=os.path.join(ROOT, "static", "examples", "starlight-fox.fg.yaml"))
    ap.add_argument("--render", action="store_true",
                    help="also rasterise every page to SVG under out/starlight/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "starlight"))
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
        from frameforge.sdk.conform import render_page_svgs
        svgs = render_page_svgs(doc, base_dir=ROOT)
        os.makedirs(args.out, exist_ok=True)
        for idx, svg in enumerate(svgs, 1):
            with open(os.path.join(args.out, f"page-{idx:02d}.svg"), "w", encoding="utf-8") as fh:
                fh.write(svg)
        print(f"Rendered {len(svgs)} SVG pages to {args.out}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
