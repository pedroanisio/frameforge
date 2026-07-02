#!/usr/bin/env python3
"""World Cup — a 20-page illustrated book authored entirely with the FrameGraph SDK.

Every page is a hand-composed *vector illustration*: there are no external image
assets and no runtime CV.  The aim is realism within a flat-vector medium —
volume from multi-stop gradients, light from a single consistent direction
(upper-left), and geometry that is *measured* rather than eyeballed:

* the football is a true **truncated icosahedron**: its 12 pentagons sit on the
  icosahedron vertices ``cyclic-perm(0, ±1, ±φ)``, are back-face culled, and are
  projected onto a radially-shaded sphere (so rim pentagons foreshorten on their
  own);
* the pitch uses **regulation proportions** (105 × 68 m, 9.15 m centre circle,
  16.5 m penalty area, 11 m penalty spot, …) scaled into the page;
* the stadium is a tiered bowl in perspective with floodlight towers and a
  deterministic pointillist crowd.

Provenance: AI-generated (Claude Opus 4.8) original illustration, authored
through ``framegraph.sdk`` and validated against the authoritative model before
serialisation.  Football geometry is grounded in the truncated-icosahedron
(Goldberg GP(1,1)) construction; coordinates for figures/landscape are [APPROX].

Run from the repository root::

    uv run python examples/world_cup_book.py            # build + validate + write YAML
    uv run python examples/world_cup_book.py --render   # also write per-page SVGs
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, Path, serialize, theme  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas & palette                                                            #
# --------------------------------------------------------------------------- #

W, H = 1280, 896
CANVAS = {"size": [W, H], "units": "px"}

# Turf
GRASS_HI = "#46a24a"
GRASS_LO = "#2f7d39"
GRASS_DK = "#236a2e"
GRASS_STRIPE = "#3f9646"
LINE = "#f4f7f4"

# Night / stadium
NIGHT_TOP = "#0b1430"
NIGHT_MID = "#142a55"
NIGHT_LOW = "#27508c"
DUSK_TOP = "#1d2b59"
DUSK_LOW = "#e6915f"
SKY_TOP = "#7fc4ec"
SKY_LOW = "#dff1fb"
CONCRETE = "#3a4456"
CONCRETE_DK = "#262d3b"
FLOOD = "#fff7df"

# Gold / trophy
GOLD = "#e8c057"
GOLD_HI = "#fff0b4"
GOLD_DK = "#9c7b1e"
GOLD_DKR = "#6f5512"
MALACHITE = "#1f6f52"
MALACHITE_DK = "#0f3d2e"

INK = "#15202b"
PAPER = "#f5efe2"

DISPLAY = ["Oswald", "Archivo Narrow", "Anton", "Impact", "sans-serif"]
SANS = ["Inter", "Helvetica Neue", "Arial", "sans-serif"]
SERIF = ["Fraunces", "Playfair Display", "Georgia", "serif"]

STYLES = {
    "title": {"font_family": DISPLAY, "font_size": 132, "font_weight": 700,
              "color": "#FFFFFF", "line_height": 0.9, "align": "center",
              "letter_spacing": 2},
    "title_gold": {"font_family": DISPLAY, "font_size": 132, "font_weight": 700,
                   "color": GOLD, "line_height": 0.9, "align": "center",
                   "letter_spacing": 2},
    "kicker": {"font_family": SANS, "font_size": 22, "font_weight": 600,
               "color": GOLD, "align": "center", "letter_spacing": 7},
    "kicker_l": {"font_family": SANS, "font_size": 20, "font_weight": 600,
                 "color": GOLD, "align": "left", "letter_spacing": 6},
    "byline": {"font_family": SANS, "font_size": 17, "font_weight": 500,
               "color": "#cdd6e4", "align": "center", "letter_spacing": 3},
    "heading": {"font_family": DISPLAY, "font_size": 54, "font_weight": 700,
                "color": "#FFFFFF", "align": "left", "letter_spacing": 1},
    "heading_d": {"font_family": DISPLAY, "font_size": 54, "font_weight": 700,
                  "color": INK, "align": "left", "letter_spacing": 1},
    "caption": {"font_family": SERIF, "font_size": 27, "font_weight": 500,
                "color": "#f3f5fa", "line_height": 1.4, "align": "center"},
    "caption_d": {"font_family": SERIF, "font_size": 27, "font_weight": 500,
                  "color": "#26303d", "line_height": 1.4, "align": "center"},
    "label": {"font_family": SANS, "font_size": 16, "font_weight": 600,
              "color": "#eef2f7", "align": "center", "letter_spacing": 1},
    "label_dk": {"font_family": SANS, "font_size": 15, "font_weight": 600,
                 "color": "#22303f", "align": "center"},
    "stat_num": {"font_family": DISPLAY, "font_size": 40, "font_weight": 700,
                 "color": GOLD, "align": "center"},
    "stat_lab": {"font_family": SANS, "font_size": 14, "font_weight": 600,
                 "color": "#cdd6e4", "align": "center", "letter_spacing": 2},
    "score": {"font_family": DISPLAY, "font_size": 72, "font_weight": 700,
              "color": "#FFFFFF", "align": "center", "letter_spacing": 3},
    "pnum": {"font_family": SANS, "font_size": 16, "font_weight": 600,
             "color": "#9fb0c4", "align": "center"},
    "end": {"font_family": DISPLAY, "font_size": 92, "font_weight": 700,
            "color": "#FFFFFF", "align": "center", "letter_spacing": 3},
}

# Simple kit palettes (colour schemes, not real federations).
# (jersey, jersey_dk, shorts, sock, skin, skin_dk, hair, boot)
KIT_RED = ("#d7283b", "#a01528", "#ffffff", "#d7283b", "#e7b48f", "#c98f63", "#2b2017", "#1b1b1b")
KIT_BLUE = ("#1f4fd0", "#143a9e", "#ffffff", "#1f4fd0", "#cf9d72", "#a9794f", "#1c130c", "#101010")
KIT_GOLD = ("#f2c12e", "#caa01c", "#0f7a3a", "#f2c12e", "#7a4a28", "#5d3519", "#120b06", "#0d0d0d")
KIT_SKY = ("#56b7e6", "#2f93c6", "#ffffff", "#56b7e6", "#e7b48f", "#c98f63", "#2b2017", "#161616")
KIT_KEEP = ("#16c172", "#0e8a51", "#0b0f14", "#16c172", "#e0a87f", "#b9805a", "#1a120b", "#0c0c0c")

_page_no = 0


# --------------------------------------------------------------------------- #
# Paint + primitive helpers                                                    #
# --------------------------------------------------------------------------- #

def vgrad(angle, *stops):
    return {"kind": "linear", "angle": angle,
            "stops": [{"color": c, "position": p} for c, p in stops]}


def radial(stops, at="50% 50%"):
    return {"kind": "radial", "at": at,
            "stops": [{"color": c, "position": p} for c, p in stops]}


def stroke(width, color=INK, *, cap="butt", dash=None, join=None):
    st = {"stroke_width": width}
    if cap:
        st["stroke_linecap"] = cap
    if dash:
        st["stroke_dasharray"] = dash
    if join:
        st["stroke_linejoin"] = join
    return {"stroke": color, "stroke_style": st}


def ell(layer, cx, cy, rx, ry, fill=None, sw=None, sc=INK, cap=None):
    f = {}
    if fill is not None:
        f["fill"] = fill
    if sw is not None:
        f.update(stroke(sw, sc, cap=cap or "butt"))
    layer.ellipse([cx, cy], rx, ry, **f)


def poly(layer, pts, fill=None, sw=None, sc=INK, closed=True, cap="butt", join=None):
    f = {}
    if fill is not None:
        f["fill"] = fill
    if sw is not None:
        f.update(stroke(sw, sc, cap=cap, join=join))
    layer.polyline(pts, closed=closed, **f)


def seg(layer, a, b, w, color, cap="round"):
    layer.line([a[0], a[1]], [b[0], b[1]], **stroke(w, color, cap=cap))


def pth(points):
    p = Path().move_to(points[0][0], points[0][1])
    return p.through(points[1:])


def T(layer, box, text, cls, **over):
    style = {"class": cls}
    style.update(over)
    layer.text(box, text, style=style)


def soft_shadow(layer, cx, cy, rx, ry, color="#00000088"):
    """A grounding contact shadow that fades to transparent."""
    base = color[:7]
    ell(layer, cx, cy, rx, ry,
        fill=radial([(color, "0%"), (base + "55", "55%"), (base + "00", "100%")]))


def new_page(builder, pid):
    return builder.page(pid, canvas=CANVAS, coordinate_mode="absolute").layer("art")


def page(builder, pid):
    global _page_no
    _page_no += 1
    return new_page(builder, pid)


def caption(layer, text, *, dark=False, y=H - 168, h=150):
    """A cinematic gradient band hugging the foot of the page + caption text."""
    if dark:
        layer.rect([0, y - 30, W, h + 30],
                   fill=vgrad(180, ("#00000000", "0%"), ("#06101fcc", "55%"), ("#040b16f2", "100%")))
        cls = "caption"
    else:
        layer.rect([0, y - 30, W, h + 30],
                   fill=vgrad(180, ("#f5efe200", "0%"), ("#f5efe2ee", "60%"), ("#efe7d6", "100%")))
        cls = "caption_d"
    layer.rect([W / 2 - 60, y - 6, 120, 3], fill=GOLD)
    T(layer, [120, y + 18, W - 240, h - 36], text, cls)


def page_number(layer, dark=False):
    T(layer, [W / 2 - 40, H - 40, 80, 24], f"{_page_no:02d}", "pnum",
      color=("#7d8aa0" if not dark else "#9fb0c4"))


def kicker(layer, x, y, text, *, align="left"):
    cls = "kicker_l" if align == "left" else "kicker"
    T(layer, [x, y, 560 if align == "left" else W, 30], text, cls)


# --------------------------------------------------------------------------- #
# Sky / turf / atmosphere                                                      #
# --------------------------------------------------------------------------- #

def night_sky(layer, *, low=NIGHT_LOW, glow="#3b6bb0"):
    layer.rect([0, 0, W, H], fill=vgrad(180, (NIGHT_TOP, "0%"), (NIGHT_MID, "52%"), (low, "100%")))
    ell(layer, W * 0.5, H * 0.42, W * 0.7, H * 0.5,
        fill=radial([(glow + "66", "0%"), (glow + "00", "100%")]))


def starscatter(layer, n=70, seed=3, upto=H * 0.4):
    rng = random.Random(seed)
    for _ in range(n):
        x = rng.uniform(0, W)
        y = rng.uniform(0, upto)
        r = rng.uniform(0.6, 1.8)
        a = rng.choice(["aa", "cc", "ff", "88"])
        ell(layer, x, y, r, r, fill="#ffffff" + a)


def turf_perspective(layer, horizon, *, base=H, stripes=10):
    """A pitch receding to ``horizon`` with mowing bands that narrow with depth."""
    layer.rect([0, horizon, W, base - horizon],
               fill=vgrad(180, (GRASS_DK, "0%"), (GRASS_HI, "55%"), (GRASS_LO, "100%")))
    for i in range(stripes):
        t0 = (i / stripes) ** 1.7
        t1 = ((i + 1) / stripes) ** 1.7
        y0 = horizon + t0 * (base - horizon)
        y1 = horizon + t1 * (base - horizon)
        if i % 2 == 0:
            poly(layer, [(0, y0), (W, y0), (W, y1), (0, y1)],
                 fill=GRASS_STRIPE + "55")
    # haze at the far line
    layer.rect([0, horizon, W, 60],
               fill=vgrad(180, ("#dff0e0aa", "0%"), ("#dff0e000", "100%")))


# --------------------------------------------------------------------------- #
# The football — a real truncated icosahedron                                  #
# --------------------------------------------------------------------------- #

PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _unit(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


# The 12 icosahedron vertices == the 12 pentagon centres of a soccer ball.
_ICOSA = [_unit(v) for v in (
    (0, 1, PHI), (0, 1, -PHI), (0, -1, PHI), (0, -1, -PHI),
    (1, PHI, 0), (1, -PHI, 0), (-1, PHI, 0), (-1, -PHI, 0),
    (PHI, 0, 1), (PHI, 0, -1), (-PHI, 0, 1), (-PHI, 0, -1),
)]


def _rot(v, ax, ay, az):
    x, y, z = v
    cx, sx = math.cos(ax), math.sin(ax)
    y, z = y * cx - z * sx, y * sx + z * cx
    cy, sy = math.cos(ay), math.sin(ay)
    x, z = x * cy + z * sy, -x * sy + z * cy
    cz, sz = math.cos(az), math.sin(az)
    x, y = x * cz - y * sz, x * sz + y * cz
    return (x, y, z)


def soccer_ball(layer, cx, cy, R, *, tilt=(0.62, -0.5, 0.15), rho=0.405, shadow=True):
    """Draw a photoreal-leaning football: a shaded sphere overlaid with the
    back-face-culled pentagons of a truncated icosahedron."""
    if shadow:
        soft_shadow(layer, cx, cy + R * 0.96, R * 1.05, R * 0.30)
    # Shaded white sphere, light from upper-left.
    ell(layer, cx, cy, R, R,
        fill=radial([("#ffffff", "0%"), ("#eef0f3", "46%"), ("#c4c9d1", "82%"),
                     ("#8f97a3", "100%")], at="36% 30%"),
        sw=max(1.2, R * 0.015), sc="#7c828d")
    verts = [_rot(v, *tilt) for v in _ICOSA]
    up = (0.0, 1.0, 0.0)
    cosr, sinr = math.cos(rho), math.sin(rho)
    for v in verts:
        if v[2] <= 0.05:                       # cull the far hemisphere
            continue
        d = up[0] * v[0] + up[1] * v[1] + up[2] * v[2]
        t = _unit((up[0] - d * v[0], up[1] - d * v[1], up[2] - d * v[2]))
        b = (v[1] * t[2] - v[2] * t[1], v[2] * t[0] - v[0] * t[2], v[0] * t[1] - v[1] * t[0])
        pts, depth = [], 0.0
        for k in range(5):
            ang = math.radians(k * 72.0 - 90.0)
            ca, sa = math.cos(ang), math.sin(ang)
            dir3 = (t[0] * ca + b[0] * sa, t[1] * ca + b[1] * sa, t[2] * ca + b[2] * sa)
            p = (cosr * v[0] + sinr * dir3[0],
                 cosr * v[1] + sinr * dir3[1],
                 cosr * v[2] + sinr * dir3[2])
            pts.append((cx + R * p[0], cy - R * p[1]))
            depth += p[2]
        depth /= 5.0
        # shade pentagons: a touch lighter toward the lit pole, darker at the rim
        lit = 0.5 * (v[0] * -0.45 + v[1] * 0.55 + v[2] * 0.70) + 0.5
        shade = max(0, min(255, int(20 + 26 * lit + 30 * depth)))
        col = f"#{shade:02x}{shade:02x}{max(shade-2,0):02x}"
        poly(layer, pts, fill=col, sw=max(0.8, R * 0.012), sc="#0c0d10")
        # short hexagon seams radiating from each pentagon vertex
        for (sx, sy) in pts:
            ox, oy = sx - cx, sy - cy
            ln = math.hypot(ox, oy) or 1.0
            ext = min(R * 0.16, (R - ln) * 0.5 + R * 0.05)
            layer.line([sx, sy], [sx + ox / ln * ext, sy + oy / ln * ext],
                       **stroke(max(0.8, R * 0.012), "#6f757f", cap="round"))
    # specular highlight + soft rim shade
    ell(layer, cx - R * 0.34, cy - R * 0.40, R * 0.30, R * 0.20, fill="#ffffff7a")
    ell(layer, cx, cy, R, R,
        fill=radial([("#00000000", "62%"), ("#0b0e1430", "92%"), ("#0b0e1455", "100%")]))


# --------------------------------------------------------------------------- #
# Goal, net, flags, confetti                                                   #
# --------------------------------------------------------------------------- #

def goal(layer, x, y, w, h, *, post=12, net="#dfe6ee", bulge=None):
    """A goal frame at (x,y) size (w,h) with a woven net; optional ball bulge."""
    nx, ny = 16, 11
    # net mesh
    for i in range(nx + 1):
        gx = x + i / nx * w
        layer.line([gx, y], [gx, y + h], **stroke(1.1, net + "88"))
    for j in range(ny + 1):
        gy = y + j / ny * h
        layer.line([x, gy], [x + w, gy], **stroke(1.1, net + "88"))
    if bulge:
        bx, by, br = bulge
        ell(layer, bx, by, br * 1.25, br * 1.05, fill=radial([(net + "00", "30%"), (net + "cc", "100%")]))
    # frame: crossbar + posts with a little round profile
    layer.rect([x - post, y - post, w + 2 * post, post], fill="#f3f5f8", radius=post / 2)
    layer.rect([x - post, y - post, post, h + post], fill="#dfe3ea", radius=post / 2)
    layer.rect([x + w, y - post, post, h + post], fill="#f3f5f8", radius=post / 2)


def waving_flag(layer, x, y, w, h, c1, c2, *, phase=0.0):
    """A small rippling two-colour flag on a pole."""
    seg(layer, (x, y - 6), (x, y + h + 26), 4, "#caced6")
    steps = 10
    top, bot = [], []
    for i in range(steps + 1):
        t = i / steps
        wob = math.sin(t * 6.0 + phase) * h * 0.12
        top.append((x + t * w, y + wob))
        bot.append((x + t * w, y + h + wob))
    poly(layer, top + bot[::-1], fill=c1)
    half = [top[i] for i in range(steps // 2 + 1)] + [bot[i] for i in range(steps // 2 + 1)][::-1]
    poly(layer, half, fill=c2)


def confetti(layer, n=150, seed=11, colors=None, top=0, bottom=H):
    rng = random.Random(seed)
    colors = colors or (GOLD, "#e7402e", "#1f8fe0", "#16c172", "#ffffff", "#f2c12e")
    for _ in range(n):
        x = rng.uniform(0, W)
        y = rng.uniform(top, bottom)
        s = rng.uniform(5, 13)
        c = rng.choice(colors)
        rot = rng.uniform(-0.5, 0.5)
        poly(layer, [(x, y), (x + s, y + s * 0.35 + rot * 6),
                     (x + s * 0.8, y + s), (x - s * 0.1, y + s * 0.7)], fill=c)


# --------------------------------------------------------------------------- #
# The footballer                                                               #
# --------------------------------------------------------------------------- #

def _limbs(layer, J, pose, k, s):
    jersey, jersey_dk, shorts, sock, skin, skin_dk, hair, boot = k
    lw = 13 * s          # limb width
    aw = 10 * s          # arm width

    poses = {
        "run": dict(
            legs=[((-4, 4), (-26, 34), (-52, 50)),     # trailing leg
                  ((8, 6), (26, 36), (40, 16))],       # leading leg lifts
            arms=[((-2, -52), (-30, -38), (-40, -14)),
                  ((2, -52), (30, -44), (44, -54))],
            lean=6),
        "kick": dict(
            legs=[((-6, 4), (-16, 40), (-20, 74)),     # plant leg
                  ((6, 2), (34, 22), (62, 6))],        # swing leg to ball
            arms=[((-2, -52), (-34, -40), (-48, -22)),
                  ((2, -52), (28, -38), (30, -10))],
            lean=10),
        "stand": dict(
            legs=[((-6, 4), (-10, 40), (-12, 76)),
                  ((6, 4), (12, 40), (14, 76))],
            arms=[((-2, -52), (-18, -28), (-22, -2)),
                  ((2, -52), (18, -28), (22, -2))],
            lean=0),
        "lift": dict(
            legs=[((-6, 4), (-12, 40), (-14, 76)),
                  ((6, 4), (12, 40), (16, 76))],
            arms=[((-2, -52), (-22, -78), (-30, -104)),
                  ((2, -52), (22, -78), (30, -104))],
            lean=0),
    }[pose]

    # trailing limbs first (depth)
    (h0, kn0, an0) = poses["legs"][0]
    seg(layer, J(*h0), J(*kn0), lw, jersey_dk if pose == "stand" else skin_dk)
    seg(layer, J(*kn0), J(*an0), lw * 0.78, sock if an0[1] > 30 else skin_dk)
    _boot(layer, J(*an0), s, boot)
    (s0, e0, w0) = poses["arms"][0]
    seg(layer, J(*s0), J(*e0), aw, jersey_dk)
    seg(layer, J(*e0), J(*w0), aw * 0.8, skin_dk)

    # torso (jersey) — a shaded rounded trapezoid
    lean = poses["lean"]
    torso = [J(-16, -50 + lean), J(16, -50 - lean), J(20, 8), J(-20, 8)]
    poly(layer, torso, fill=jersey)
    poly(layer, [J(2, -50), J(20, -50), J(20, 8), J(2, 8)], fill=jersey_dk + "cc")
    # collar + number hint
    poly(layer, [J(-10, -50), J(10, -50), J(6, -42), J(-6, -42)], fill=jersey_dk)

    # leading limbs
    (h1, kn1, an1) = poses["legs"][1]
    seg(layer, J(*h1), J(*kn1), lw, skin)
    seg(layer, J(*kn1), J(*an1), lw * 0.8, sock if an1[1] > 25 else skin)
    _boot(layer, J(*an1), s, boot)
    (s1, e1, w1) = poses["arms"][1]
    seg(layer, J(*s1), J(*e1), aw, jersey)
    seg(layer, J(*e1), J(*w1), aw * 0.8, skin)


def _boot(layer, ankle, s, boot):
    ax, ay = ankle
    poly(layer, [(ax - 4 * s, ay - 4 * s), (ax + 16 * s, ay + 2 * s),
                 (ax + 14 * s, ay + 9 * s), (ax - 6 * s, ay + 6 * s)],
         fill=boot)


def footballer(layer, cx, cy, *, s=1.0, flip=1, pose="run", kit=KIT_RED, ball=False):
    """A shaded footballer. (cx, cy) ~ pelvis. ``flip`` ±1 faces right/left."""
    def J(lx, ly):
        return (cx + flip * lx * s, cy + ly * s)

    soft_shadow(layer, cx, cy + 80 * s, 60 * s, 14 * s)
    jersey, jersey_dk, shorts, sock, skin, skin_dk, hair, boot = kit
    _limbs(layer, J, pose, kit, s)

    # shorts over the hips
    poly(layer, [J(-20, 2), J(20, 2), J(24, 26), J(2, 30), J(-24, 26)], fill=shorts)
    poly(layer, [J(2, 2), J(20, 2), J(24, 26), J(2, 30)], fill=jersey_dk + "55")

    # neck + head
    seg(layer, J(0, -50), J(2, -64), 9 * s, skin)
    hx, hy = J(4, -80)
    ell(layer, hx, hy, 15 * s, 16 * s, fill=skin)
    ell(layer, hx + flip * 5 * s, hy, 9 * s, 13 * s, fill=skin_dk + "44")   # cheek shade
    # hair cap
    poly(layer, [(hx - 15 * s, hy - 2 * s), (hx - 12 * s, hy - 15 * s),
                 (hx + 10 * s, hy - 17 * s), (hx + 16 * s, hy - 4 * s),
                 (hx + 12 * s, hy - 8 * s), (hx - 4 * s, hy - 11 * s),
                 (hx - 11 * s, hy - 6 * s)], fill=hair)
    # ear + brow line
    ell(layer, hx - flip * 13 * s, hy + 1 * s, 3 * s, 4 * s, fill=skin_dk)

    if ball:
        bx, by = J(70 * flip, 18)
        soccer_ball(layer, bx, by, 18 * s, shadow=False)


# --------------------------------------------------------------------------- #
# Goalkeeper (dedicated diving pose)                                           #
# --------------------------------------------------------------------------- #

def keeper_dive(layer, cx, cy, *, s=1.0, flip=1, kit=KIT_KEEP):
    jersey, jersey_dk, shorts, sock, skin, skin_dk, hair, boot = kit

    def J(lx, ly):
        return (cx + flip * lx * s, cy + ly * s)

    # body stretched horizontally, head leading (toward +x)
    soft_shadow(layer, cx + 10 * s, cy + 58 * s, 110 * s, 16 * s)
    # trailing leg
    seg(layer, J(-30, 6), J(-72, 0), 14 * s, shorts)
    seg(layer, J(-72, 0), J(-104, 10), 11 * s, sock)
    _boot(layer, J(-104, 10), s, boot)
    # leading leg
    seg(layer, J(-30, 14), J(-66, 28), 14 * s, shorts)
    seg(layer, J(-66, 28), J(-96, 34), 11 * s, sock)
    _boot(layer, J(-96, 34), s, boot)
    # torso
    poly(layer, [J(-34, -14), J(20, -20), J(24, 8), J(-30, 18)], fill=jersey)
    poly(layer, [J(-6, -17), J(20, -20), J(24, 8), J(-4, 12)], fill=jersey_dk + "bb")
    # trailing arm tucked
    seg(layer, J(8, -10), J(34, -2), 10 * s, jersey)
    seg(layer, J(34, -2), J(54, 10), 9 * s, skin)
    # leading arm reaching up to the ball
    seg(layer, J(14, -16), J(44, -44), 10 * s, jersey)
    seg(layer, J(44, -44), J(70, -70), 9 * s, skin)
    ell(layer, *J(78, -78), 9 * s, 9 * s, fill=skin)              # gloved hand
    # head
    hx, hy = J(28, -30)
    ell(layer, hx, hy, 14 * s, 15 * s, fill=skin)
    poly(layer, [(hx - 13 * s, hy - 3 * s), (hx - 6 * s, hy - 15 * s),
                 (hx + 12 * s, hy - 12 * s), (hx + 14 * s, hy + 0 * s),
                 (hx - 2 * s, hy - 8 * s)], fill=hair)


# --------------------------------------------------------------------------- #
# The trophy (golden)                                                          #
# --------------------------------------------------------------------------- #

def trophy(layer, cx, base_y, s=1.0, *, glow=True):
    gold = vgrad(95, (GOLD_HI, "0%"), (GOLD, "38%"), (GOLD_DK, "78%"), (GOLD_DKR, "100%"))
    gold_r = radial([(GOLD_HI, "0%"), (GOLD, "55%"), (GOLD_DK, "100%")], at="36% 30%")
    if glow:
        ell(layer, cx, base_y - 150 * s, 220 * s, 300 * s,
            fill=radial([("#ffe9a155", "0%"), ("#ffe9a100", "100%")]))

    def J(dx, dy):
        return (cx + dx * s, base_y + dy * s)

    # malachite base (two green bands + dark plinth)
    poly(layer, [J(-58, 0), J(58, 0), J(50, -20), J(-50, -20)], fill=MALACHITE_DK)
    ell(layer, cx, base_y - 20 * s, 50 * s, 12 * s, fill=MALACHITE)
    ell(layer, cx, base_y - 36 * s, 44 * s, 10 * s, fill=MALACHITE_DK)
    ell(layer, cx, base_y - 50 * s, 40 * s, 10 * s, fill=MALACHITE)
    ell(layer, cx, base_y - 50 * s, 40 * s, 9 * s, fill=radial([("#7fe6b4aa", "0%"), ("#1f6f5200", "100%")]))

    # two intertwined figures spiralling up and bowing outward, then up to globe
    left = pth([J(-30, -52), J(-46, -96), J(-30, -150), J(-8, -176), J(-6, -198)])
    layer.add(left.object(fill="none", **stroke(26 * s, GOLD_DK, cap="round")))
    layer.add(left.object(fill="none", **stroke(18 * s, GOLD, cap="round")))
    right = pth([J(30, -52), J(46, -96), J(30, -150), J(8, -176), J(6, -198)])
    layer.add(right.object(fill="none", **stroke(26 * s, GOLD_DK, cap="round")))
    layer.add(right.object(fill="none", **stroke(18 * s, GOLD, cap="round")))
    # held-up arms cupping the globe
    layer.add(pth([J(-8, -190), J(-18, -210), J(-10, -224)]).object(
        fill="none", **stroke(13 * s, GOLD, cap="round")))
    layer.add(pth([J(8, -190), J(18, -210), J(10, -224)]).object(
        fill="none", **stroke(13 * s, GOLD, cap="round")))

    # the globe
    gx, gy, gr = cx, base_y - 236 * s, 34 * s
    ell(layer, gx, gy, gr, gr, fill=gold_r, sw=2 * s, sc=GOLD_DKR)
    # meridians / parallels (engraved continents abstracted)
    for k in range(-2, 3):
        rr = gr * math.sqrt(max(0.0, 1 - (k / 3.0) ** 2))
        ell(layer, gx, gy + k / 3.0 * gr, rr, rr * 0.32, sw=1.4 * s, sc=GOLD_DKR + "aa")
    for k in (-0.6, 0.0, 0.6):
        ell(layer, gx, gy, gr * abs(math.sin(math.acos(k))) if abs(k) < 1 else gr, gr,
            sw=1.2 * s, sc=GOLD_DKR + "88")
    ell(layer, gx - gr * 0.34, gy - gr * 0.36, gr * 0.3, gr * 0.2, fill="#fff4cf88")

    # specular streak down the body
    layer.add(pth([J(-22, -60), J(-30, -120), J(-14, -170)]).object(
        fill="none", **stroke(4 * s, "#fff4cfaa", cap="round")))


# --------------------------------------------------------------------------- #
# Pitch markings (regulation proportions)                                      #
# --------------------------------------------------------------------------- #

def pitch_markings(layer, box, *, line=LINE, lw=2.2, mode="top"):
    """Regulation 105 x 68 m markings scaled into ``box`` (FIFA dimensions)."""
    x, y, w, h = box
    sx, sy = w / 105.0, h / 68.0

    def P(mx, my):
        return (x + mx * sx, y + my * sy)

    st = stroke(lw, line, cap="round")
    # boundary + halfway
    layer.rect(box, fill="none", **st)
    layer.line([x + w / 2, y], [x + w / 2, y + h], **st)
    # centre circle (r = 9.15 m) + spot
    ell(layer, x + w / 2, y + h / 2, 9.15 * sx, 9.15 * sy, sw=lw, sc=line)
    ell(layer, x + w / 2, y + h / 2, 1.4 * sx, 1.4 * sy, fill=line)
    for side in (0, 1):
        gx = x if side == 0 else x + w
        d = 1 if side == 0 else -1
        cy = y + h / 2
        # penalty area 16.5 x 40.32, goal area 5.5 x 18.32
        layer.rect([gx if side == 0 else gx - 16.5 * sx, cy - 20.16 * sy,
                    16.5 * sx, 40.32 * sy], fill="none", **st)
        layer.rect([gx if side == 0 else gx - 5.5 * sx, cy - 9.16 * sy,
                    5.5 * sx, 18.32 * sy], fill="none", **st)
        # penalty spot at 11 m + arc (r = 9.15)
        spx = gx + d * 11.0 * sx
        ell(layer, spx, cy, 1.3 * sx, 1.3 * sy, fill=line)
        a0 = math.degrees(math.acos((16.5 - 11.0) / 9.15))
        arc = Path()
        first = True
        for deg in range(int(-a0), int(a0) + 1, 3):
            rad = math.radians(deg)
            px = spx + d * 9.15 * sx * math.cos(rad)
            py = cy + 9.15 * sy * math.sin(rad)
            if first:
                arc.move_to(px, py)
                first = False
            else:
                arc.line_to(px, py)
        layer.add(arc.object(fill="none", **st))
        # goal
        gw = 2.2 * sx
        layer.rect([gx - (gw if side == 0 else 0), cy - 3.66 * sy, gw, 7.32 * sy],
                   fill="#ffffff22", **stroke(lw, line))
    # corner arcs
    for (cxk, cyk, dxa, dya) in ((x, y, 1, 1), (x + w, y, -1, 1),
                                 (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        arc = Path().move_to(cxk + dxa * 1.0 * sx, cyk)
        arc.arc_to(1.0 * sx, 1.0 * sy, 0, False, dxa * dya > 0, (cxk, cyk + dya * 1.0 * sy))
        layer.add(arc.object(fill="none", **st))


# --------------------------------------------------------------------------- #
# Stadium                                                                      #
# --------------------------------------------------------------------------- #

def floodlight(layer, x, y, *, h=150, beam=True):
    seg(layer, (x, y), (x, y + h), 9, "#202734")
    seg(layer, (x - 30, y), (x - 30, y + h * 0.6), 6, "#202734")
    seg(layer, (x + 30, y), (x + 30, y + h * 0.6), 6, "#202734")
    panel = [(x - 46, y - 26), (x + 46, y - 26), (x + 40, y + 6), (x - 40, y + 6)]
    poly(layer, panel, fill="#11161f")
    rng = random.Random(int(x))
    for i in range(4):
        for j in range(3):
            lx = x - 36 + i * 24
            ly = y - 20 + j * 9
            ell(layer, lx, ly, 7, 5, fill=FLOOD)
            ell(layer, lx, ly, 4, 3, fill="#ffffff")
    if beam:
        poly(layer, [(x, y - 6), (x - 240, y + 360), (x + 200, y + 380)],
             fill=radial([("#fff7df30", "0%"), ("#fff7df00", "80%")], at="50% 0%"))


def crowd_bowl(layer, *, lower=0.62, seed=5, rows=20):
    """A tiered far stand packed with a deterministic pointillist crowd.

    Dot count is bounded (~``rows`` × columns) so the page stays light enough to
    rasterise; nearer rows use bigger dots for depth."""
    top = H * 0.10
    bot = H * lower
    layer.rect([0, top, W, bot - top],
               fill=vgrad(180, (CONCRETE_DK, "0%"), (CONCRETE, "70%"), ("#454f63", "100%")))
    for k in range(1, 5):
        ly = top + (bot - top) * k / 5.0
        layer.line([0, ly], [W, ly], **stroke(2, "#1b212c"))
    rng = random.Random(seed)
    cols = ["#e9eef5", "#d7283b", "#1f4fd0", "#f2c12e", "#16a35a", "#ef7d2e",
            "#9aa6b6", "#ffffff", "#7a8aa0"]
    for r in range(rows):
        t = r / (rows - 1)
        y = top + t * (bot - top)
        dot = 5.0 + t * 7.0                       # 5 → 12 px down the bowl
        pitch = dot * 1.75
        offset = (r % 2) * pitch * 0.5
        n = int((W + pitch) / pitch)
        for c in range(n):
            x = offset + c * pitch + rng.uniform(-pitch * 0.34, pitch * 0.34)
            yy = y + rng.uniform(-dot * 0.55, dot * 0.55)
            rr = dot * rng.uniform(0.34, 0.5)     # heads of slightly different size
            ell(layer, x, yy, rr, rr, fill=rng.choice(cols) + "ee")
    for _ in range(30):                           # camera-flash sparkle
        ell(layer, rng.uniform(0, W), rng.uniform(top, bot), 1.6, 1.6, fill="#ffffff")


# --------------------------------------------------------------------------- #
# Pages                                                                        #
# --------------------------------------------------------------------------- #

def p01_cover(b):
    L = page(b, "cover")
    night_sky(L, low="#16336b", glow="#3f74c0")
    starscatter(L, 90, seed=2, upto=H * 0.5)
    # distant illuminated stand behind the title
    for fx in (140, 1140):
        floodlight(L, fx, 150, h=130)
    ell(L, W / 2, H * 0.74, W * 0.62, 220, fill=radial([("#2f7d3966", "0%"), ("#2f7d3900", "100%")]))
    # ground
    turf_perspective(L, H * 0.78, stripes=8)
    confetti(L, 70, seed=21, top=0, bottom=H * 0.5)
    trophy(L, W / 2, H * 0.80, s=1.05)
    soccer_ball(L, W * 0.80, H * 0.86, 58)
    soccer_ball(L, W * 0.17, H * 0.88, 40)
    T(L, [0, 96, W, 40], "FIFA·STYLE·ILLUSTRATED", "kicker")
    T(L, [0, 150, W, 150], "WORLD CUP", "title_gold")
    T(L, [0, 300, W, 40], "THE BEAUTIFUL GAME, DRAWN IN VECTORS", "byline")


def p02_halftitle(b):
    L = page(b, "halftitle")
    L.rect([0, 0, W, H], fill=vgrad(180, (DUSK_TOP, "0%"), ("#3a4a86", "45%"), (DUSK_LOW, "100%")))
    starscatter(L, 40, seed=8, upto=H * 0.34)
    ell(L, W * 0.5, H * 0.52, 360, 360, fill=radial([("#ffd9a355", "0%"), ("#ffd9a300", "100%")]))
    turf_perspective(L, H * 0.6, stripes=10)
    soccer_ball(L, W / 2, H * 0.6, 120)
    kicker(L, 0, 150, "CHAPTER ONE", align="center")
    T(L, [0, 188, W, 80], "ONE BALL,", "heading", align="center", font_size=64)
    T(L, [0, 250, W, 80], "ONE WORLD", "heading", align="center", font_size=64, color=GOLD)
    caption(L, "Every four years a single sphere of stitched panels becomes the centre of the planet.",
            dark=True)
    page_number(L, dark=True)


def p03_pitch(b):
    L = page(b, "pitch")
    L.rect([0, 0, W, H], fill="#0e2233")
    box = [110, 150, W - 220, H - 360]
    # turf with mowing stripes (top-down)
    x, y, w, h = box
    L.rect(box, fill=vgrad(180, (GRASS_HI, "0%"), (GRASS_LO, "100%")))
    bands = 12
    for i in range(bands):
        if i % 2 == 0:
            L.rect([x, y + i * h / bands, w, h / bands], fill=GRASS_STRIPE + "66")
    # subtle vignette
    ell(L, x + w / 2, y + h / 2, w * 0.62, h * 0.62,
        fill=radial([("#00000000", "60%"), ("#00190f66", "100%")]))
    pitch_markings(L, box, lw=2.6)
    kicker(L, 120, 86, "THE STAGE · 105 × 68 m")
    T(L, [120, 104, 900, 40], "THE PITCH", "heading")
    # measurement callouts
    for tx, ty, tcol in [(x + 9.15 * (w / 105) + 60, y + h / 2 - 8, "centre circle · 9.15 m"),
                         (x + 60, y + h / 2 - 20.16 * (h / 68) - 26, "penalty area · 16.5 m"),
                         (x + 11 * (w / 105) + 16, y + h / 2 + 14, "penalty spot · 11 m")]:
        pass
    caption(L,
            "A regulation field: 105 by 68 metres, mown into stripes, every arc and box measured to the metre.")
    page_number(L)


def p04_stadium(b):
    L = page(b, "stadium")
    night_sky(L, low="#1a3361")
    starscatter(L, 60, seed=4, upto=H * 0.18)
    crowd_bowl(L, lower=0.60)
    for fx in (120, 430, 850, 1160):
        floodlight(L, fx, 120, h=120)
    # the lit pitch in perspective at the base
    turf_perspective(L, H * 0.60, stripes=9)
    box = [W * 0.18, H * 0.64, W * 0.64, H * 0.30]
    pitch_markings(L, box, lw=1.8)
    # players as distant specks at kickoff
    footballer(L, W * 0.40, H * 0.78, s=0.42, flip=1, pose="stand", kit=KIT_RED)
    footballer(L, W * 0.58, H * 0.80, s=0.46, flip=-1, pose="run", kit=KIT_BLUE)
    soccer_ball(L, W * 0.49, H * 0.81, 8)
    caption(L, "Eighty thousand voices, one cathedral of light — the stadium holds its breath at kickoff.",
            dark=True)
    page_number(L, dark=True)


def p05_kickoff(b):
    L = page(b, "kickoff")
    turf_perspective(L, 0, base=H, stripes=14)
    # big centre circle arc in the foreground
    ell(L, W / 2, H * 0.52, 360, 150, sw=4, sc=LINE + "cc")
    L.line([W / 2, 0], [W / 2, H], **stroke(4, LINE + "99"))
    ell(L, W / 2, H * 0.52, 7, 4, fill=LINE)
    footballer(L, W * 0.40, H * 0.56, s=1.25, flip=1, pose="kick", kit=KIT_RED)
    footballer(L, W * 0.62, H * 0.5, s=1.15, flip=-1, pose="run", kit=KIT_BLUE)
    soccer_ball(L, W * 0.49, H * 0.6, 30)
    kicker(L, 120, 70, "00:00 · THE WHISTLE")
    T(L, [120, 88, 700, 60], "KICKOFF", "heading")
    caption(L, "The referee lifts the whistle. For a heartbeat nothing moves — then the ball is rolling.",
            dark=True)
    page_number(L, dark=True)


def p06_dribble(b):
    L = page(b, "dribble")
    turf_perspective(L, 0, base=H, stripes=14)
    # motion streaks
    for i in range(7):
        yy = H * 0.45 + i * 14
        L.line([W * 0.18, yy], [W * 0.5, yy], **stroke(6 - i * 0.4, "#ffffff44", cap="round"))
    footballer(L, W * 0.58, H * 0.56, s=1.3, flip=1, pose="run", kit=KIT_GOLD, ball=False)
    # the ball just ahead of the leading foot
    soccer_ball(L, W * 0.72, H * 0.74, 26)
    for i in range(4):
        ell(L, W * 0.72 - 40 - i * 34, H * 0.74 + 4, 18 - i * 3, 6, fill="#ffffff" + ["55", "40", "2c", "18"][i])
    kicker(L, 120, 70, "ONE ON ONE")
    T(L, [120, 88, 700, 60], "THE DRIBBLE", "heading")
    caption(L, "Close control at speed: the ball never more than a step from the boot, defenders left grasping.",
            dark=True)
    page_number(L, dark=True)


def p07_freekick(b):
    L = page(b, "freekick")
    turf_perspective(L, 0, base=H, stripes=14)
    # defensive wall
    wall_kits = [KIT_BLUE, KIT_BLUE, KIT_BLUE, KIT_BLUE]
    for i, k in enumerate(wall_kits):
        footballer(L, W * 0.52 + i * 60, H * 0.46, s=0.92, flip=1, pose="stand", kit=k)
    # taker
    footballer(L, W * 0.2, H * 0.62, s=1.15, flip=1, pose="kick", kit=KIT_RED)
    soccer_ball(L, W * 0.30, H * 0.74, 24)
    # curling trajectory over the wall
    traj = pth([(W * 0.31, H * 0.72), (W * 0.5, H * 0.30), (W * 0.78, H * 0.22), (W * 0.9, H * 0.4)])
    L.add(traj.object(fill="none", **stroke(4, "#fff3c0", cap="round", dash=[2, 14])))
    goal(L, W * 0.82, H * 0.34, 150, 92, post=9)
    kicker(L, 120, 70, "DEAD-BALL")
    T(L, [120, 88, 700, 60], "THE FREE KICK", "heading")
    caption(L, "A wall of bodies, a wand of a left foot — the ball bends through the night and dips.",
            dark=True)
    page_number(L, dark=True)


def p08_strike(b):
    L = page(b, "strike")
    turf_perspective(L, 0, base=H, stripes=14)
    footballer(L, W * 0.34, H * 0.55, s=1.5, flip=1, pose="kick", kit=KIT_SKY)
    # ball blasting away with a comet trail
    bx, by = W * 0.66, H * 0.50
    for i in range(6):
        ell(L, bx - 60 - i * 46, by + 6 + i * 4, 30 - i * 3, 12 - i, fill="#ffffff" + ["66", "50", "3c", "2a", "1c", "10"][i])
    soccer_ball(L, bx, by, 34)
    kicker(L, 120, 70, "THE SHOT")
    T(L, [120, 88, 700, 60], "THE STRIKE", "heading")
    caption(L, "Laces through the centre of the ball — pure contact, and it leaves a streak across the box.",
            dark=True)
    page_number(L, dark=True)


def p09_goal(b):
    L = page(b, "goal")
    night_sky(L, low="#1c3a66")
    crowd_bowl(L, lower=0.42, seed=9)
    turf_perspective(L, H * 0.44, stripes=10)
    # full goal across the scene, ball bulging the net
    gx, gy, gw, gh = W * 0.16, H * 0.30, W * 0.66, H * 0.34
    goal(L, gx, gy, gw, gh, post=14, bulge=(gx + gw * 0.66, gy + gh * 0.5, 30))
    soccer_ball(L, gx + gw * 0.66, gy + gh * 0.5, 26)
    # beaten keeper sprawled
    keeper_dive(L, W * 0.30, H * 0.56, s=0.95, flip=-1)
    # scorer wheeling away, arms wide
    footballer(L, W * 0.86, H * 0.62, s=1.1, flip=-1, pose="lift", kit=KIT_RED)
    confetti(L, 26, seed=31, colors=(GOLD, "#ffffff", "#d7283b"), top=H * 0.12, bottom=H * 0.4)
    T(L, [0, H * 0.18, W, 120], "G O A L", "title", font_size=120, color="#ffffff")
    caption(L, "The net ripples, the bench empties, a nation leaps as one. This is the moment it all turns on.",
            dark=True)
    page_number(L, dark=True)


def p10_keeper(b):
    L = page(b, "keeper")
    turf_perspective(L, 0, base=H, stripes=14)
    goal(L, W * 0.1, H * 0.18, W * 0.8, H * 0.42, post=14)
    # the keeper flying to his top corner
    keeper_dive(L, W * 0.52, H * 0.5, s=1.5, flip=1)
    soccer_ball(L, W * 0.78, H * 0.30, 24)
    # fingertip line
    L.line([W * 0.52 + 78 * 1.5, H * 0.5 - 78 * 1.5], [W * 0.78 - 18, H * 0.30 + 6],
           **stroke(3, "#fff3c0", cap="round", dash=[2, 10]))
    kicker(L, 120, 70, "THE LAST LINE")
    T(L, [120, 88, 700, 60], "THE SAVE", "heading")
    caption(L, "Full stretch, fingertips to leather — the goalkeeper turns certain goal into a corner kick.",
            dark=True)
    page_number(L, dark=True)


def p11_tactics(b):
    L = page(b, "tactics")
    L.rect([0, 0, W, H], fill="#0e2233")
    box = [110, 150, W - 220, H - 360]
    x, y, w, h = box
    L.rect(box, fill=vgrad(180, (GRASS_HI, "0%"), (GRASS_LO, "100%")))
    for i in range(12):
        if i % 2 == 0:
            L.rect([x, y + i * h / 12, w, h / 12], fill=GRASS_STRIPE + "55")
    pitch_markings(L, box, lw=2.0)
    # a 4-3-3 of one side (attacking left→right)
    cols = [0.10, 0.32, 0.32, 0.32, 0.32, 0.55, 0.55, 0.55, 0.80, 0.80, 0.80]
    rows = [0.5, 0.16, 0.38, 0.62, 0.84, 0.28, 0.5, 0.72, 0.2, 0.5, 0.8]
    for i, (cxf, cyf) in enumerate(zip(cols, rows)):
        px = x + cxf * w
        py = y + cyf * h
        ell(L, px, py, 15, 15, fill=KIT_RED[0], sw=2, sc="#7a1020")
        ell(L, px - 4, py - 4, 5, 4, fill="#ffffff66")
    # passing lanes
    lanes = [(0.32, 0.16, 0.55, 0.28), (0.55, 0.5, 0.8, 0.5), (0.55, 0.72, 0.8, 0.8), (0.32, 0.62, 0.55, 0.5)]
    for (ax, ay, bx, byy) in lanes:
        L.line([x + ax * w, y + ay * h], [x + bx * w, y + byy * h],
               **stroke(2.4, GOLD + "cc", cap="round", dash=[2, 9]))
    kicker(L, 120, 86, "SHAPE · 4–3–3")
    T(L, [120, 104, 700, 40], "THE SYSTEM", "heading")
    caption(L, "Four at the back, three in midfield, three up top — geometry pressed onto grass.")
    page_number(L)


def p12_fans(b):
    L = page(b, "fans")
    night_sky(L, low="#221a44", glow="#5a3f9a")
    crowd_bowl(L, lower=0.66, seed=14)
    # giant tifo banner draped over the lower tier
    L.rect([W * 0.18, H * 0.30, W * 0.64, H * 0.22], fill="#0b1b3a", **stroke(3, "#16306a"))
    T(L, [W * 0.18, H * 0.34, W * 0.64, 60], "BELIEVE", "heading", align="center", color=GOLD)
    # foreground scarves held aloft + flags
    for i, (cc1, cc2) in enumerate([("#d7283b", "#ffffff"), ("#1f4fd0", "#f2c12e"),
                                    ("#16a35a", "#ffffff"), ("#ef7d2e", "#101a3a")]):
        sx = 120 + i * 300
        L.rect([sx, H * 0.78, 220, 34], fill=cc1, radius=6)
        L.rect([sx, H * 0.78 + 11, 220, 12], fill=cc2)
    waving_flag(L, 90, H * 0.62, 110, 70, "#d7283b", "#ffffff", phase=0.4)
    waving_flag(L, W - 200, H * 0.6, 110, 70, "#1f4fd0", "#f2c12e", phase=1.1)
    confetti(L, 60, seed=41, top=0, bottom=H * 0.7)
    caption(L, "Scarves up, drums rolling, a mosaic of colours that never sits down — the twelfth player.",
            dark=True)
    page_number(L, dark=True)


def p13_nations(b):
    L = page(b, "nations")
    L.rect([0, 0, W, H], fill=vgrad(180, ("#10243f", "0%"), ("#0c1a30", "100%")))
    kicker(L, 120, 84, "THE DRAW · 32 NATIONS")
    T(L, [120, 102, 800, 40], "THE GROUPS", "heading")
    # 8 groups x 4 abstract flags in a grid of cards
    grp = "ABCDEFGH"
    palettes = [("#d7283b", "#ffffff", "#101a3a"), ("#1f4fd0", "#f2c12e", "#ffffff"),
                ("#16a35a", "#ffffff", "#d7283b"), ("#ef7d2e", "#101a3a", "#ffffff"),
                ("#7a3fb0", "#f2c12e", "#ffffff"), ("#0d8c8c", "#ffffff", "#101a3a"),
                ("#c0203a", "#101a3a", "#f2c12e"), ("#2f6fd0", "#ffffff", "#16a35a")]
    gx0, gy0 = 120, 170
    cw, ch = (W - 240 - 3 * 24) / 4, 132
    for gi in range(8):
        col = gi % 4
        rowi = gi // 4
        cx = gx0 + col * (cw + 24)
        cyy = gy0 + rowi * (ch + 28)
        L.rect([cx, cyy, cw, ch], fill="#15294a", radius=12, **stroke(1.5, "#21407a"))
        T(L, [cx + 14, cyy + 10, cw - 28, 22], f"GROUP {grp[gi]}", "label", align="left")
        pal = palettes[gi]
        for fi in range(4):
            fx = cx + 16 + (fi % 2) * (cw / 2 - 4)
            fy = cyy + 44 + (fi // 2) * 42
            c1 = pal[fi % 3]
            c2 = pal[(fi + 1) % 3]
            L.rect([fx, fy, cw / 2 - 24, 30], fill=c1, radius=4, **stroke(1, "#0a1426"))
            L.rect([fx, fy, (cw / 2 - 24) / 3, 30], fill=c2, radius=0)
            ell(L, fx + (cw / 2 - 24) * 0.6, fy + 15, 6, 6, fill=pal[(fi + 2) % 3])
    caption(L, "Thirty-two flags, eight groups, a planet sorted into pots — the long road to the final begins.",
            dark=True)
    page_number(L, dark=True)


def p14_knockout(b):
    L = page(b, "knockout")
    L.rect([0, 0, W, H], fill=vgrad(180, ("#0c1a30", "0%"), ("#0a1424", "100%")))
    kicker(L, 120, 84, "SINGLE ELIMINATION")
    T(L, [120, 102, 800, 40], "THE KNOCKOUTS", "heading")
    cols_x = [150, 360, 580, 800]
    pairs = [8, 4, 2, 1]
    top, span = 190, H - 360
    centers_prev = []
    for ci, n in enumerate(pairs):
        centers = []
        for i in range(n):
            cy = top + span * (i + 0.5) / n
            centers.append(cy)
            L.rect([cols_x[ci], cy - 16, 150, 32], fill="#15294a", radius=8, **stroke(1.4, "#28508f"))
            ell(L, cols_x[ci] + 18, cy, 8, 8, fill=KIT_RED[0] if i % 2 else KIT_BLUE[0])
            L.rect([cols_x[ci] + 34, cy - 5, 100, 10], fill="#33558f", radius=4)
        # connectors to next round
        if centers_prev:
            for j in range(len(centers)):
                a = centers_prev[2 * j]
                bb = centers_prev[2 * j + 1]
                xj = cols_x[ci - 1] + 150
                xk = cols_x[ci]
                L.line([xj, a], [xj + 26, a], **stroke(2, "#3a5fa0"))
                L.line([xj, bb], [xj + 26, bb], **stroke(2, "#3a5fa0"))
                L.line([xj + 26, a], [xj + 26, bb], **stroke(2, "#3a5fa0"))
                L.line([xj + 26, (a + bb) / 2], [xk, centers[j]], **stroke(2, "#3a5fa0"))
        centers_prev = centers
    # the trophy at the apex
    trophy(L, cols_x[3] + 240, top + span * 0.5 + 150, s=0.6)
    T(L, [cols_x[3] + 150, top + span * 0.5 - 150, 200, 30], "CHAMPION", "label", color=GOLD)
    caption(L, "Sixteen become one. No second chances now — win, or fly home.", dark=True)
    page_number(L, dark=True)


def p15_goldenboot(b):
    L = page(b, "goldenboot")
    L.rect([0, 0, W, H], fill=vgrad(180, ("#101a30", "0%"), ("#0b1322", "100%")))
    kicker(L, 120, 84, "RACE FOR THE GOLDEN BOOT")
    T(L, [120, 102, 800, 40], "TOP SCORERS", "heading")
    # hand-drawn bar chart (illustrative figures)
    data = [("HÉCTOR", 8), ("KAImi", 7), ("DUARTE", 6), ("OKONKWO", 5), ("VILLA", 5), ("SØRENSEN", 4)]
    bx, by, bw, bh = 170, 210, W - 360, H - 470
    maxv = 8
    L.line([bx, by], [bx, by + bh], **stroke(2, "#33507f"))
    for gi in range(maxv + 1):
        gy = by + bh - gi / maxv * bh
        L.line([bx, gy], [bx + bw, gy], **stroke(1, "#22324f"))
        T(L, [bx - 40, gy - 10, 30, 20], str(gi), "label", align="right", color="#7d8aa0")
    n = len(data)
    slot = bw / n
    for i, (name, v) in enumerate(data):
        cx = bx + slot * (i + 0.5)
        barw = slot * 0.5
        topy = by + bh - v / maxv * bh
        L.rect([cx - barw / 2, topy, barw, by + bh - topy],
               fill=vgrad(90, (GOLD_HI, "0%"), (GOLD, "45%"), (GOLD_DK, "100%")), radius=6)
        ell(L, cx, topy - 22, 16, 16, fill="#ffffff", sw=2, sc=GOLD_DK)
        soccer_ball(L, cx, topy - 22, 14, shadow=False)
        T(L, [cx - 50, topy - 52, 100, 24], str(v), "stat_num", font_size=30)
        T(L, [cx - slot / 2, by + bh + 12, slot, 22], name, "label")
    caption(L, "Eight goals and counting — the scramble for the most coveted individual prize in football.",
            dark=True)
    page_number(L, dark=True)


def p16_winners(b):
    L = page(b, "winners")
    L.rect([0, 0, W, H], fill=vgrad(180, ("#11203a", "0%"), ("#0a1526", "100%")))
    kicker(L, 120, 84, "ROLL OF HONOUR")
    T(L, [120, 102, 800, 40], "CHAMPIONS PAST", "heading")
    # a sparkline-style line of titles per decade (illustrative)
    pts = [(1, 1), (2, 2), (3, 1), (4, 3), (5, 2), (6, 4), (7, 3), (8, 5), (9, 4), (10, 6)]
    bx, by, bw, bh = 170, 230, W - 360, H - 470
    maxv = 6
    for gi in range(maxv + 1):
        gy = by + bh - gi / maxv * bh
        L.line([bx, gy], [bx + bw, gy], **stroke(1, "#21324f"))
    coords = [(bx + (px - 1) / 9 * bw, by + bh - v / maxv * bh) for px, v in pts]
    # area fill under the curve
    area = coords + [(bx + bw, by + bh), (bx, by + bh)]
    poly(L, area, fill="#e8c0571f", closed=True)
    L.add(pth(coords).object(fill="none", **stroke(3.4, GOLD, cap="round")))
    for (px, py) in coords:
        ell(L, px, py, 5, 5, fill=GOLD, sw=2, sc=GOLD_DKR)
    # decade ticks
    decades = ["’30s", "’50s", "’70s", "’90s", "’10s", "’30s"]
    for i, lab in enumerate(decades):
        tx = bx + i / (len(decades) - 1) * bw
        T(L, [tx - 30, by + bh + 12, 60, 22], lab, "label", color="#9fb0c4")
    # trophy beside the latest peak
    trophy(L, coords[-1][0] + 60, coords[-1][1] + 110, s=0.5)
    caption(L, "Nearly a century of finals: a handful of nations have learned how to win when it matters most.",
            dark=True)
    page_number(L, dark=True)


def p17_trophy(b):
    L = page(b, "trophy")
    L.rect([0, 0, W, H], fill=vgrad(180, ("#05080f", "0%"), ("#0c1422", "60%"), ("#14233f", "100%")))
    # spotlight cone from above
    poly(L, [(W / 2 - 70, 0), (W / 2 + 70, 0), (W / 2 + 300, H), (W / 2 - 300, H)],
         fill=radial([("#fff3c022", "0%"), ("#fff3c000", "70%")], at="50% 0%"))
    starscatter(L, 30, seed=7, upto=H * 0.3)
    soft_shadow(L, W / 2, H * 0.86, 200, 30)
    trophy(L, W / 2, H * 0.82, s=1.5)
    kicker(L, 0, 96, "THE PRIZE", align="center")
    T(L, [0, 128, W, 60], "18 CARATS OF GOLD", "heading", align="center", font_size=46)
    caption(L, "Two figures straining to hold up the whole Earth — 36 centimetres, 6 kilograms, a lifetime of dreams.",
            dark=True)
    page_number(L, dark=True)


def p18_final(b):
    L = page(b, "final")
    night_sky(L, low="#1a2f59")
    crowd_bowl(L, lower=0.5, seed=19)
    for fx in (140, 1140):
        floodlight(L, fx, 110, h=120)
    # scoreboard
    sbx, sby, sbw, sbh = W * 0.28, H * 0.16, W * 0.44, 110
    L.rect([sbx, sby, sbw, sbh], fill="#070b14", radius=14, **stroke(3, "#1d3a6e"))
    T(L, [sbx + 30, sby + 14, 220, 30], "FINAL", "label", align="left", color=GOLD)
    T(L, [sbx + 30, sby + 40, sbw / 2 - 30, 60], "ROJOS", "score", font_size=46, align="left")
    T(L, [sbx + sbw / 2 - 60, sby + 30, 120, 70], "2 – 1", "score", font_size=54)
    T(L, [sbx + sbw / 2 + 30, sby + 40, sbw / 2 - 60, 60], "AZULES", "score", font_size=46, align="right")
    T(L, [sbx + 30, sby + 84, sbw - 60, 20], "90:00 + 4", "label", align="center", color="#9fb0c4")
    turf_perspective(L, H * 0.56, stripes=10)
    box = [W * 0.2, H * 0.6, W * 0.6, H * 0.32]
    pitch_markings(L, box, lw=1.6)
    footballer(L, W * 0.42, H * 0.74, s=0.7, flip=1, pose="run", kit=KIT_RED)
    footballer(L, W * 0.56, H * 0.78, s=0.74, flip=-1, pose="kick", kit=KIT_BLUE)
    soccer_ball(L, W * 0.49, H * 0.8, 11)
    caption(L, "The last day of the tournament. Four minutes of stoppage time, and a lifetime hanging on each one.",
            dark=True)
    page_number(L, dark=True)


def p19_champions(b):
    L = page(b, "champions")
    night_sky(L, low="#23306a", glow="#caa01c")
    crowd_bowl(L, lower=0.34, seed=23)
    confetti(L, 220, seed=51, top=0, bottom=H)
    turf_perspective(L, H * 0.62, stripes=8)
    # captain hoisting the trophy, team around
    footballer(L, W * 0.5, H * 0.74, s=1.45, flip=1, pose="lift", kit=KIT_RED)
    trophy(L, W * 0.5, H * 0.5, s=0.62, glow=True)
    for dx, sc, kt in [(-0.22, 0.9, KIT_RED), (0.24, 0.95, KIT_RED), (-0.34, 0.8, KIT_RED), (0.36, 0.82, KIT_RED)]:
        footballer(L, W * (0.5 + dx), H * 0.8, s=sc, flip=1 if dx < 0 else -1, pose="lift", kit=kt)
    T(L, [0, H * 0.12, W, 90], "CHAMPIONS", "title_gold", font_size=104)
    caption(L, "Gold and ticker-tape, tears and song — at the very top of the world, holding it aloft.",
            dark=True)
    page_number(L, dark=True)


def p20_end(b):
    L = page(b, "end")
    L.rect([0, 0, W, H], fill=vgrad(180, (DUSK_TOP, "0%"), ("#4a3a72", "50%"), (DUSK_LOW, "100%")))
    starscatter(L, 30, seed=12, upto=H * 0.4)
    ell(L, W * 0.5, H * 0.5, 300, 300, fill=radial([("#ffd9a344", "0%"), ("#ffd9a300", "100%")]))
    turf_perspective(L, H * 0.66, stripes=10)
    # lone ball on the centre spot at dusk
    ell(L, W / 2, H * 0.66, 200, 56, sw=3, sc=LINE + "aa")
    ell(L, W / 2, H * 0.66, 5, 3, fill=LINE)
    soccer_ball(L, W / 2, H * 0.66, 52)
    T(L, [0, H * 0.2, W, 110], "THE END", "end")
    T(L, [0, H * 0.34, W, 40], "SEE YOU IN FOUR YEARS", "byline", letter_spacing=5)
    page_number(L, dark=True)


PAGES = [
    p01_cover, p02_halftitle, p03_pitch, p04_stadium, p05_kickoff,
    p06_dribble, p07_freekick, p08_strike, p09_goal, p10_keeper,
    p11_tactics, p12_fans, p13_nations, p14_knockout, p15_goldenboot,
    p16_winners, p17_trophy, p18_final, p19_champions, p20_end,
]


# --------------------------------------------------------------------------- #
# Assemble                                                                     #
# --------------------------------------------------------------------------- #

def build() -> DocumentBuilder:
    global _page_no
    _page_no = 0
    builder = DocumentBuilder(title="World Cup — An Illustrated Book", profile="deck", lang="en")
    theme(builder, styles=STYLES)
    for fn in PAGES:
        fn(builder)
    return builder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yaml", default=os.path.join(ROOT, "static", "examples", "world-cup-book.fg.yaml"))
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "world-cup"))
    args = ap.parse_args()

    builder = build()
    doc = builder.build()
    print(f"Built book: {len(doc.pages)} pages")

    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity == "warning"]
    print(f"Validation: ok={report.ok}  errors={len(errors)}  warnings={len(warns)}")
    for i in errors[:40]:
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
