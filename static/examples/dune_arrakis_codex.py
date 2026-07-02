#!/usr/bin/env python3
"""ARRAKIS CODEX — a 30-slide Dune deck built on the FrameGraph Python SDK.

A field-codex for the desert planet, rendered in flat vector. The deck leans on
the SDK's newer geometry affordances so the detail is authored, not hand-rolled:

* ``ring`` (annulus)        — the Eyes of Ibad, the twin moons, orbital bands, trust rings
* ``arc`` / ``sector``      — orbital paths, the melange cycle, spice gauges, the worm's maw
* ``regular_polygon``       — sietch cells, crysknife facets
* ``star``                  — the Arrakeen night field
* ``polyline(smooth=True)`` — dune ridges, the worm's body, spice/population curves
* ``effects(glow=…)``       — spice glow, the blue-in-blue eye, prophecy shimmer
* ``define_symbol`` / ``use`` — the spice-eye crest authored once and instanced across plates

One pinned identity (Arrakis night, melange orange, Fremen blue, a monumental
serif) is held across all 30 plates while the *diagrammation* changes slide to
slide, so the deck reads as range rather than one template reskinned.

Run from the repository root::

    uv run python examples/dune_arrakis_codex.py            # build + validate + write YAML
    uv run python examples/dune_arrakis_codex.py --render   # also rasterise pages to out/dune/
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
    Chart,
    DocumentBuilder,
    Frame,
    column,
    effects,
    glow,
    grid,
    inset,
    linear_gradient,
    radial_gradient,
    rgba,
    row,
    serialize,
    shadow,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas, palette, type                                                        #
# --------------------------------------------------------------------------- #

W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
MX = 78

NIGHT = "#0b0d14"       # Arrakis night sky — near-black blue
NIGHT2 = "#11131d"      # lifted panel base
PANEL = "#17140e"       # warm sand-shadow card
PANEL2 = "#1e1810"      # alt card
DUNE = "#2a2114"        # deep dune shadow / structure
SAND = "#d9b787"        # dune tan
SANDL = "#f0d9b0"       # pale sand highlight
SPICE = "#e8731f"       # melange orange — primary
SPICEB = "#ff9a3c"      # bright spice
EMBER = "#b8481a"       # deep ember
FREMEN = "#2f7fb0"      # Fremen blue — secondary
FREMENB = "#5bc8e8"     # bright blue glow (the Eyes of Ibad)
GOLD = "#e3b23c"        # Corrino / Imperial gold
BLOOD = "#8a2d2d"       # Harkonnen
CREAM = "#f5ecdd"       # headline cream
INK = "#cdb597"         # warm body
MUTE = "#897761"        # captions
GRIDC = "#1a1610"       # faint warm grid on the night

SERIF = ["DejaVu Serif", "Georgia", "serif"]                  # monumental headers
SANS = ["Fira Sans", "Arial", "sans-serif"]                   # body
MONO = ["DejaVu Sans Mono", "Consolas", "monospace"]          # Mentat / BG data tags

TOTAL = 30
_page = 0

COLORS = {
    "night": NIGHT, "night2": NIGHT2, "panel": PANEL, "panel2": PANEL2,
    "dune": DUNE, "sand": SAND, "sandl": SANDL, "spice": SPICE, "spiceb": SPICEB,
    "ember": EMBER, "fremen": FREMEN, "fremenb": FREMENB, "gold": GOLD,
    "blood": BLOOD, "cream": CREAM, "ink": INK, "mute": MUTE, "gridc": GRIDC,
    "ghost": "#15121b",
}


def hexof(c: str) -> str:
    return COLORS.get(c, c)


def a(color: str, alpha: float) -> str:
    """Translucent paint as portable rgba() (cairosvg drops #rrggbbaa alpha)."""
    return rgba(hexof(color), alpha)


def EF(*, blur, color, opacity=0.55, sh=None):
    """effects() helper: an object-level glow (+ optional shadow), never lost in stroke_style."""
    g = glow(blur=blur, color=hexof(color), opacity=opacity)
    return effects(glow=g, shadow=sh)


STYLES = {
    "kicker": dict(font_family=MONO, font_size=13, font_weight=700, color="spice",
                   text_transform="uppercase", letter_spacing=4),
    "kickerB": dict(font_family=MONO, font_size=13, font_weight=700, color="fremenb",
                    text_transform="uppercase", letter_spacing=4),
    "tag": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                text_transform="uppercase", letter_spacing=3),
    "tagC": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=4, align="center"),
    "pnum": dict(font_family=MONO, font_size=11, font_weight=700, color="sand",
                 letter_spacing=2, align="right"),
    "h1": dict(font_family=SERIF, font_size=62, font_weight=700, color="cream",
               letter_spacing=1, line_height=1.0),
    "h1C": dict(font_family=SERIF, font_size=58, font_weight=700, color="cream",
                letter_spacing=1, line_height=1.04, align="center"),
    "title": dict(font_family=SERIF, font_size=33, font_weight=700, color="cream",
                  letter_spacing=0, line_height=1.08),
    "h2": dict(font_family=SERIF, font_size=23, font_weight=700, color="cream",
               line_height=1.14),
    "h2s": dict(font_family=SERIF, font_size=22, font_weight=700, color="spice",
                line_height=1.16),
    "h2b": dict(font_family=SERIF, font_size=22, font_weight=700, color="fremenb",
                line_height=1.16),
    "big": dict(font_family=SERIF, font_size=190, font_weight=700, color="spice",
                letter_spacing=-2, line_height=0.9),
    "idx": dict(font_family=SERIF, font_size=176, font_weight=700, color="ghost",
                line_height=0.9),
    "lead": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                 line_height=1.5),
    "leadC": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                  line_height=1.5, align="center"),
    "body": dict(font_family=SANS, font_size=14.5, font_weight=400, color="ink",
                 line_height=1.5),
    "bodyM": dict(font_family=SANS, font_size=13, font_weight=400, color="mute",
                  line_height=1.45),
    "mono": dict(font_family=MONO, font_size=13, font_weight=400, color="ink",
                 line_height=1.45),
    "monoS": dict(font_family=MONO, font_size=12.5, font_weight=700, color="spice",
                  line_height=1.4, letter_spacing=1),
    "stat": dict(font_family=SERIF, font_size=46, font_weight=700, color="spice",
                 line_height=1.0),
    "statB": dict(font_family=SERIF, font_size=46, font_weight=700, color="fremenb",
                  line_height=1.0),
    "num": dict(font_family=MONO, font_size=18, font_weight=700, color="spice",
                align="center", line_height=1.0),
    "chip": dict(font_family=MONO, font_size=13, font_weight=700, color="night",
                 align="center", letter_spacing=3, text_transform="uppercase"),
    "litany": dict(font_family=SERIF, font_size=38, font_weight=700, color="cream",
                   line_height=1.26, align="center"),
}


# --------------------------------------------------------------------------- #
# Drawing vocabulary                                                           #
# --------------------------------------------------------------------------- #

def _wrap_text(layer):
    def wrapped(box, text, **fields):
        return layer.group([{"type": "text", "box": list(box), "text": text, **fields}])
    layer.text = wrapped
    return layer


def grouped(objs):
    out = []
    for o in objs:
        if isinstance(o, dict) and o.get("type") == "text":
            out.append({"type": "group", "children": [o]})
        else:
            out.append(o)
    return out


def new_page(b, pid):
    layer = b.page(pid, canvas=CANVAS, coordinate_mode="absolute").layer("main")
    return _wrap_text(layer)


def S(w, color=SPICE, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": w, **extra}}


def hline(layer, x0, x1, y, color=DUNE, w=1.0, **extra):
    layer.line([x0, y], [x1, y], **S(w, color, **extra))


def vline(layer, x, y0, y1, color=DUNE, w=1.0, **extra):
    layer.line([x, y0], [x, y1], **S(w, color, **extra))


def dot(layer, cx, cy, r, fill, **extra):
    layer.ellipse([cx, cy], r, r, fill=fill, **extra)


def circle_ring(layer, cx, cy, r, color=SPICE, w=2.0, **extra):
    layer.ellipse([cx, cy], r, r, fill="none", **S(w, color, **extra))


def dune_ridges(layer, box, *, n=4, color=DUNE, base="spice", amp=26):
    """Stacked smooth dune ridges via polyline(smooth=True) — the deck's signature curve."""
    x, y, bw, bh = box
    for i in range(n):
        yy = y + bh * (0.32 + 0.62 * i / max(1, n - 1))
        pts = []
        for k in range(7):
            px = x + bw * k / 6
            py = yy - amp * math.sin(k * 0.9 + i * 1.3) * (1 - i / (n + 1))
            pts.append([px, py])
        col = base if i == n - 1 else color
        layer.polyline(pts, smooth=True, fill="none",
                       **S(2.0 if i == n - 1 else 1.4, col, stroke_linecap="round"))


def star_field(layer, box, *, n=22, color="sandl"):
    """Scatter small stars (regular star polygons) across a box — deterministic placement."""
    x, y, bw, bh = box
    for i in range(n):
        sx = x + (i * 137 % 1000) / 1000 * bw
        sy = y + (i * 89 % 1000) / 1000 * bh
        r = 2.2 + (i % 3)
        layer.star([sx, sy], r, r * 0.45, 4, rotation=-90,
                   fill=a(color, 0.5 + 0.12 * (i % 4)))


def hexcell(layer, cx, cy, r, *, color=SPICE, fill="none", w=1.8, **extra):
    layer.regular_polygon([cx, cy], r, 6, rotation=-90, fill=fill, **S(w, color), **extra)


def chevron(layer, cx, cy, size, color=SPICE, w=2.4, down=False):
    s = -1 if down else 1
    layer.polyline([[cx - size, cy + s * size * 0.6], [cx, cy - s * size * 0.6],
                    [cx + size, cy + s * size * 0.6]], **S(w, color, stroke_linecap="round"))


def trace(layer, pts, color=SPICE, w=1.6, node_r=3.5, node=True, smooth=False):
    layer.polyline(pts, smooth=smooth, **S(w, color, stroke_linecap="round", stroke_linejoin="round"))
    if node:
        dot(layer, *pts[0], node_r, color)
        dot(layer, *pts[-1], node_r, color)


# --------------------------------------------------------------------------- #
# Cinematic atmosphere — gradient skies, a low sun, layered dune silhouettes,   #
# god-rays, heat-haze, vignette and letterbox. This is what carries the mood.   #
# --------------------------------------------------------------------------- #

SKIES = {
    # vertical sky gradients (top → horizon); the warm band low is the desert glow
    "night": [("#05060e", 0.0), ("#080a16", 0.5), ("#0f1320", 0.84), ("#241812", 1.0)],
    "dusk":  [("#06060e", 0.0), ("#0b0a16", 0.40), ("#241121", 0.70), ("#7a2f16", 0.90),
              ("#c4471a", 1.0)],
    "dawn":  [("#0c1030", 0.0), ("#33203f", 0.42), ("#8a4421", 0.74), ("#e8731f", 0.90),
              ("#f3dcb2", 1.0)],
}


def sky(layer, mood="night", *, horizon=None):
    """Full-bleed sky gradient — the cinematic ground for every plate."""
    layer.rect([0, 0, W, H], fill=linear_gradient(SKIES[mood], angle=180))


def sun(layer, cx, cy, r, *, core="#fff3d0", edge="spice", halo=2.8, glow_blur=46):
    """A low glowing sun: a soft radial halo + a bright disc with a wide glow."""
    layer.ellipse([cx, cy], r * halo, r * halo,
                  fill=radial_gradient([(a(edge, 0.42), 0.0), (a(edge, 0.0), 1.0)]),
                  decorative=True)
    layer.ellipse([cx, cy], r, r,
                  fill=radial_gradient([(core, 0.0), (hexof(edge), 0.7), (a(edge, 0.0), 1.0)]),
                  **EF(blur=glow_blur, color=edge, opacity=0.5), decorative=True)


def _ridge(ridge_y, amp, phase, *, steps=10):
    pts = []
    for k in range(steps + 1):
        x = -60 + (W + 120) * k / steps
        y = ridge_y + amp * math.sin(k * 0.7 + phase) - amp * 0.4 * math.sin(k * 1.9 + phase)
        pts.append([x, y])
    return pts


def dune_band(layer, ridge_y, amp, phase, fill, *, glow_top=None):
    """A filled dune silhouette to the bottom of the frame (depth layer)."""
    pts = _ridge(ridge_y, amp, phase) + [[W + 60, H + 80], [-60, H + 80]]
    layer.polyline(pts, smooth=True, closed=True, fill=fill, decorative=True)
    if glow_top:
        # a thin sun-lit rim along the crest
        layer.polyline(_ridge(ridge_y, amp, phase), smooth=True, fill="none",
                       decorative=True, **S(1.6, glow_top, stroke_linecap="round"))


def dune_scape(layer, horizon, *, lit="ember", rim=None):
    """Receding dune ridges from the horizon down — far/pale to near/dark."""
    bands = [
        (horizon + 6, 14, 0.4, a(lit, 0.30), None),
        (horizon + 40, 22, 2.1, a("#160d09", 0.92), rim),
        (horizon + 96, 30, 4.3, "#0c0705", None),
        (horizon + 168, 34, 1.2, "#060403", None),
    ]
    for ry, amp, ph, fill, gtop in bands:
        dune_band(layer, ry, amp, ph, fill, glow_top=gtop)


def godrays(layer, cx, cy, *, color="spice", n=7, spread=150, length=520, alpha=0.06):
    """Soft translucent light shafts fanning down from the sun."""
    for i in range(n):
        t = (i / (n - 1)) - 0.5
        x2 = cx + t * spread
        w = 18 + 26 * (1 - abs(t))
        layer.polygon([[cx - 3, cy], [cx + 3, cy], [x2 + w, cy + length], [x2 - w, cy + length]],
                      fill=a(color, alpha), decorative=True)


def haze(layer, y, h, color="spice", alpha=0.10):
    layer.rect([0, y, W, h], fill=a(color, alpha), decorative=True)


def dust(layer, box, *, n=40, color="sandl"):
    x, y, bw, bh = box
    for i in range(n):
        sx = x + (i * 167 % 1000) / 1000 * bw
        sy = y + (i * 113 % 1000) / 1000 * bh
        dot(layer, sx, sy, 0.8 + (i % 3) * 0.6, a(color, 0.10 + 0.05 * (i % 3)))


def vignette(layer, strength=0.72):
    layer.rect([0, 0, W, H], decorative=True,
               fill=radial_gradient([(a("#04030a", 0.0), 0.45), (a("#04030a", strength), 1.0)],
                                    at="50% 44%"))


def letterbox(layer, h=42):
    layer.rect([0, 0, W, h], fill="#04030a", decorative=True)
    layer.rect([0, H - h, W, h], fill="#04030a", decorative=True)


def worm_silhouette(layer, base_x, base_y, height, *, w=78, sun_color="spice"):
    """A sandworm rearing up out of the dune line — the deck's hero silhouette."""
    top = base_y - height
    body = [
        [base_x - w, base_y], [base_x - w * 0.7, base_y - height * 0.42],
        [base_x - w * 0.34, base_y - height * 0.78], [base_x - w * 0.5, top + height * 0.06],
        [base_x, top], [base_x + w * 0.5, top + height * 0.06],
        [base_x + w * 0.34, base_y - height * 0.78], [base_x + w * 0.7, base_y - height * 0.42],
        [base_x + w, base_y],
    ]
    layer.polyline(body, smooth=True, closed=True, fill="#080503", decorative=True,
                   **S(2, a(sun_color, 0.5)))
    # the open maw at the crest — a ring of teeth around a dark gullet
    layer.ring([base_x, top + 6], 26, 11, fill="#0a0604",
               **S(1.6, sun_color), **EF(blur=14, color=sun_color, opacity=0.5))
    for deg in range(0, 360, 30):
        tx = base_x + 18 * math.cos(math.radians(deg))
        ty = (top + 6) + 18 * math.sin(math.radians(deg))
        layer.star([tx, ty], 5, 2, 3, rotation=deg + 90, fill=a("sandl", 0.85))


def fremen_figure(layer, fx, fy, h, *, accent="fremenb"):
    """A small cloaked Fremen silhouette standing on a ridge."""
    w = h * 0.32
    body = [[fx, fy - h], [fx + w * 0.5, fy - h * 0.86], [fx + w * 0.7, fy - h * 0.3],
            [fx + w, fy], [fx - w, fy], [fx - w * 0.7, fy - h * 0.3], [fx - w * 0.5, fy - h * 0.86]]
    layer.polyline(body, smooth=True, closed=True, fill="#070506", decorative=True,
                   **S(1.4, a(accent, 0.4)))
    # the blue-in-blue eyes, a faint glowing pair
    layer.ellipse([fx - 4, fy - h * 0.9], 1.6, 1.6, fill=accent,
                  **EF(blur=6, color=accent, opacity=0.9), decorative=True)
    layer.ellipse([fx + 4, fy - h * 0.9], 1.6, 1.6, fill=accent,
                  **EF(blur=6, color=accent, opacity=0.9), decorative=True)


def ornithopter(layer, ox, oy, s, *, color="dune"):
    """A distant dragonfly-winged 'thopter against the sky."""
    layer.polygon([[ox - s, oy], [ox, oy - s * 0.22], [ox + s, oy]], fill=a(color, 0.85),
                  decorative=True)
    for sgn in (-1, 1):
        layer.polyline([[ox, oy - 2], [ox + sgn * s * 1.4, oy - s * 0.5],
                        [ox + sgn * s * 0.6, oy - 1]], fill=a(color, 0.5),
                       decorative=True, **S(1.2, a(color, 0.7)))


def panel(layer, box, *, color=DUNE, fill="panel", w=1.4, fill_alpha=None, radius=5):
    f = a(color, fill_alpha) if fill_alpha is not None else a("#0a0712", 0.62)
    layer.rect(box, fill=f, radius=radius, **S(w, color))


def chrome(b, kicker, title, *, kstyle="kicker", accent="spice", mood="night", horizon=560):
    """Cinematic content frame: a dusk sky over distant dunes, vignette, letterbox."""
    global _page
    _page += 1
    n = _page
    layer = new_page(b, f"p{n:02d}")
    with layer.bleed():
        sky(layer, mood)
        star_field(layer, [0, 0, W, horizon - 160], n=30)
        dune_scape(layer, horizon, lit=accent)
        dust(layer, [0, horizon - 120, W, 200], n=26)
        vignette(layer, 0.66)
        letterbox(layer, 34)
    layer.text([MX, 64, W - 2 * MX, 22], kicker, style=kstyle)
    layer.text([MX, 90, W - 2 * MX, 56], title, style="title")
    layer.rect([MX, 146, 92, 5], fill=accent, radius=2, **EF(blur=10, color=accent, opacity=0.5))
    layer.text([W - MX - 220, 694, 220, 18], f"CODEX · {n:02d}/{TOTAL}", style="pnum")
    layer.text([MX, 694, 560, 18], "ARRAKIS CODEX · IMPERIUM YEAR 10191 · THE SPICE MUST FLOW",
               style="tag")
    return layer


def footer(layer, text):
    layer.text([MX, 662, W - 2 * MX, 18], text, style="bodyM")


# --------------------------------------------------------------------------- #
# 01 — Cover                                                                    #
# --------------------------------------------------------------------------- #

def cover(b, eye):
    global _page
    _page += 1
    layer = new_page(b, "cover")
    with layer.bleed():
        sky(layer, "dawn")
        star_field(layer, [0, 0, W, 300], n=40)
        sun(layer, 880, 392, 96, core="#fff6da", edge="spiceb", halo=3.2, glow_blur=60)
        godrays(layer, 880, 392, color="spice", n=9, spread=420, length=360, alpha=0.05)
        haze(layer, 380, 120, "spice", 0.06)
        ornithopter(layer, 520, 230, 16)
        dune_scape(layer, 452, lit="spice", rim=a("spiceb", 0.5))
        worm_silhouette(layer, 980, 470, 230, w=64, sun_color="spice")
        fremen_figure(layer, 250, 512, 84)
        fremen_figure(layer, 320, 524, 64)
        dust(layer, [0, 300, W, 260], n=44)
        vignette(layer, 0.7)
        letterbox(layer, 52)
    layer.text([MX, 150, 760, 26], "A FIELD CODEX OF THE DESERT PLANET", style="kicker")
    layer.text([MX, 196, 820, 130], "ARRAKIS", style="h1")
    layer.rect([MX, 286, 150, 5], fill="spice", radius=2, **EF(blur=12, color="spice", opacity=0.6))
    layer.text([MX, 308, 620, 40], "DUNE · known to the Fremen as the place of the worm",
               style="lead")
    layer.text([MX, 600, 860, 20],
               "30 PLATES · FRAMEGRAPH PYTHON SDK · RING / ARC / SECTOR / STAR / SMOOTH / SYMBOLS",
               style="tag")
    layer.text([W - MX - 220, 600, 220, 18], "PLATE 01 / 30", style="pnum")


# --------------------------------------------------------------------------- #
# 02 — Contents                                                                 #
# --------------------------------------------------------------------------- #

def contents(b):
    layer = chrome(b, "The codex — five readings of Arrakis", "Contents")
    items = [
        ("I", "The Planet", "Arrakis itself — its moons, climate and the sietch warren.", "spice"),
        ("II", "The Spice", "Melange: its cycle, its powers, and who it makes rich.", "spiceb"),
        ("III", "The Fremen", "The people of the desert — water, stillsuit and crysknife.", "fremenb"),
        ("IV", "The Powers", "Houses, Guild, Sisterhood and the Imperial throne.", "gold"),
        ("V", "The Prophecy", "The breeding path, Muad'Dib, and the storm to come.", "spice"),
    ]
    rows = column([MX, 196, W - 2 * MX, 5 * 86], 5)
    for (n, head, sub, col), rb in zip(items, rows):
        x, y, bw, bh = rb
        hexcell(layer, x + 28, y + 30, 26, color=col, w=2.0)
        layer.text([x + 10, y + 16, 44, 30], n, style={"class": "num", "color": col})
        layer.text([x + 78, y + 8, bw - 120, 30], head, style="h2")
        layer.text([x + 78, y + 42, bw - 140, 30], sub, style="body")
        hline(layer, x + 78, x + bw - 10, y + 74, "dune", 1)


# --------------------------------------------------------------------------- #
# Section dividers                                                              #
# --------------------------------------------------------------------------- #

def divider(b, pid, secno, title, subtitle, eye, *, accent="spice"):
    global _page
    _page += 1
    layer = new_page(b, pid)
    with layer.bleed():
        sky(layer, "dusk")
        star_field(layer, [0, 0, W, 360], n=44)
        sun(layer, 1040, 250, 150, core="#ffe7c2", edge=accent, halo=2.4, glow_blur=64)
        godrays(layer, 1040, 250, color=accent, n=9, spread=360, length=470, alpha=0.045)
        dune_scape(layer, 500, lit=accent, rim=a(accent, 0.45))
        fremen_figure(layer, 1120, 548, 70, accent="fremenb")
        dust(layer, [0, 280, W, 280], n=34)
        vignette(layer, 0.72)
        letterbox(layer, 46)
    kstyle = "kickerB" if accent == "fremenb" else "kicker"
    layer.text([MX - 4, 150, 560, 280], secno, style="idx")
    layer.text([MX + 4, 268, 360, 22], f"READING {secno}", style=kstyle)
    layer.text([MX, 300, 760, 120], title, style="h1")
    layer.rect([MX + 4, 414, 130, 5], fill=accent, radius=2, **EF(blur=10, color=accent, opacity=0.6))
    layer.text([MX + 4, 438, 620, 80], subtitle, style="lead")
    layer.text([W - MX - 220, 694, 220, 18], f"CODEX · {_page:02d}/{TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 04 — Litany (centered)                                                        #
# --------------------------------------------------------------------------- #

def litany(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    with layer.bleed():
        sky(layer, "night")
        star_field(layer, [0, 0, W, 460], n=70)
        sun(layer, W / 2, 250, 130, core="#1a2740", edge="fremen", halo=2.6, glow_blur=70)
        dune_scape(layer, 560, lit="fremen", rim=a("fremenb", 0.3))
        fremen_figure(layer, W / 2, 600, 150, accent="fremenb")
        dust(layer, [0, 300, W, 280], n=30, color="fremenb")
        vignette(layer, 0.74)
        letterbox(layer, 52)
    layer.text([0, 150, W, 22], "BENE GESSERIT · THE LITANY AGAINST FEAR", style="tagC")
    layer.text([180, 196, W - 360, 170],
               "Fear is the mind-killer.\nFear is the little-death\nthat brings total obliteration.",
               style="litany")
    layer.rect([W / 2 - 70, 408, 140, 5], fill="fremenb", radius=2,
               **EF(blur=12, color="fremenb", opacity=0.6))
    layer.text([W / 2 - 380, 436, 760, 70],
               "I will face my fear. I will permit it to pass over me and through me. Where the "
               "fear has gone there will be nothing. Only I will remain.", style="leadC")
    layer.text([W - MX - 220, 694, 220, 18], f"CODEX · {_page:02d}/{TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 05 — Planet cross-section (radial, ring/arc)                                  #
# --------------------------------------------------------------------------- #

def planet(b):
    layer = chrome(b, "I · The Planet", "Anatomy of Arrakis")
    cx, cy = 446, 414
    # concentric shells drawn as true annuli (ring)
    shells = [
        (200, 168, "dune", "CRUST", "rock and the shield wall"),
        (168, 120, "spice", "SPICE SANDS", "the great erg — melange beds"),
        (120, 74, "ember", "MANTLE", "where the makers are born"),
        (74, 30, "gold", "CORE", "the planet's old heat"),
    ]
    for r_out, r_in, col, name, sub in shells:
        layer.ring([cx, cy], r_out, r_in, fill=a(col, 0.30), **S(1.6, col))
    layer.ellipse([cx, cy], 30, 30, fill="gold", **EF(blur=12, color="gold", opacity=0.5))
    # a polar cap arc and the night terminator arc
    layer.arc([cx, cy], 206, 196, 250, **S(3, "fremenb", stroke_linecap="round"),
              **EF(blur=8, color="fremenb", opacity=0.4))
    # leader lines + labels
    for i, (r_out, r_in, col, name, sub) in enumerate(shells):
        ly = 224 + i * 100
        px = cx + (r_out + r_in) / 2
        layer.line([px, cy], [800, ly + 12], **S(1.2, col))
        dot(layer, px, cy, 4, col)
        layer.text([814, ly, 380, 24], name, style={"class": "h2s", "color": col})
        layer.text([814, ly + 28, 380, 24], sub, style="bodyM")
    footer(layer, "No standing water, no native life above the worm — yet the most valuable surface in the Imperium.")


# --------------------------------------------------------------------------- #
# 06 — Twin moons (orbital arcs)                                                #
# --------------------------------------------------------------------------- #

def moons(b):
    layer = chrome(b, "I · The Planet", "The first and second moon")
    cx, cy = 470, 420
    star_field(layer, [MX, 196, W - 2 * MX, 360], n=30)
    # Arrakis
    layer.ellipse([cx, cy], 70, 70, fill=a("spice", 0.2), **S(2, "spice"))
    dune_ridges(layer, [cx - 70, cy - 30, 140, 70], n=2, amp=8, base="ember")
    # two orbital bands (ring) + moons riding an arc each
    for r, col, name, frac, mr in ((150, "sandl", "FIRST MOON", 0.18, 16),
                                   (220, "fremen", "SECOND MOON", 0.62, 12)):
        layer.ring([cx, cy], r + 1.2, r - 1.2, fill=col, style={"fill_rule": "evenodd"})
        layer.arc([cx, cy], r, -150, 30, **S(1.2, col, stroke_dasharray=[5, 6]))
        deg = -150 + 180 * frac
        mx = cx + r * math.cos(math.radians(deg))
        my = cy + r * math.sin(math.radians(deg))
        layer.ellipse([mx, my], mr, mr, fill=col, **EF(blur=10, color=col, opacity=0.5))
        # the hand of the first moon is a Fremen sign — note it
        layer.text([mx + mr + 8, my - 8, 200, 18], name,
                   style={"class": "kicker", "color": col, "font_size": 11})
    note = [880, 220, W - 880 - MX, 380]
    panel(layer, note, color="dune", fill="night2", w=1.4)
    layer.text([note[0] + 22, note[1] + 22, note[2] - 44, 26], "Read the sky", style="h2s")
    layer.text([note[0] + 22, note[1] + 60, note[2] - 44, 300],
               "The Fremen read the first moon's hand-shaped maria for the season of the "
               "worm. The second moon governs the tides of dust. Off-world, the two moons "
               "are how a pilot fixes Arrakeen from orbit before the storms close the sky.",
               style="body")
    footer(layer, "Dashed bands are the charted orbits; the discs ride them at the present hour.")


# --------------------------------------------------------------------------- #
# 07 — Water scarcity (big number)                                             #
# --------------------------------------------------------------------------- #

def water(b):
    layer = chrome(b, "I · The Planet", "The price of water")
    layer.text([MX - 4, 210, 760, 240], "0%", style="big")
    layer.text([MX + 2, 452, 520, 30], "of Arrakis is open water — none, anywhere, ever",
               style="lead")
    layer.rect([MX, 502, 300, 5], fill="spice", radius=2)
    notes = column([812, 206, W - 812 - MX, 380], 3, gap=22)
    facts = [
        ("THE DEW", "Stillsuits reclaim sweat and breath; a Fremen loses almost nothing to the air."),
        ("THE DEAD", "A body is water owed to the tribe — rendered to the sietch's hidden reservoir."),
        ("THE DREAM", "Liet-Kynes' secret: enough caught water, over centuries, could green the south."),
    ]
    for nb, (h, body) in zip(notes, facts):
        x, y, bw, bh = nb
        vline(layer, x, y + 2, y + 58, "fremenb", 3)
        layer.text([x + 18, y, bw - 18, 22], h, style="h2b")
        layer.text([x + 18, y + 32, bw - 18, 80], body, style="body")


# --------------------------------------------------------------------------- #
# 08 — Sietch network (hex node graph)                                          #
# --------------------------------------------------------------------------- #

def sietch_network(b):
    layer = chrome(b, "I · The Planet", "The sietch warren")
    cx, cy = 470, 422
    nodes = {
        "tabr": (cx, cy, "spice", 30),
        "n1": (cx - 230, cy - 110, "fremen", 22),
        "n2": (cx + 210, cy - 140, "fremen", 22),
        "n3": (cx - 250, cy + 110, "fremen", 22),
        "n4": (cx + 250, cy + 96, "fremen", 22),
        "n5": (cx - 20, cy - 210, "sandl", 18),
        "n6": (cx + 60, cy + 200, "sandl", 18),
    }
    edges = [("tabr", k) for k in nodes if k != "tabr"] + [("n1", "n5"), ("n2", "n5"),
             ("n3", "n6"), ("n4", "n6"), ("n1", "n3")]
    for u, v in edges:
        x1, y1, _, _ = nodes[u]
        x2, y2, _, _ = nodes[v]
        # buried qanat routes — smooth so they read as desert paths, not wires
        midx, midy = (x1 + x2) / 2, (y1 + y2) / 2 - 22
        layer.polyline([[x1, y1], [midx, midy], [x2, y2]], smooth=True, fill="none",
                       **S(1.3, "dune", stroke_dasharray=[5, 5]))
    for k, (x, y, col, r) in nodes.items():
        hexcell(layer, x, y, r, color=col, fill=a(col, 0.12), w=2.0)
        dot(layer, x, y, 4, col)
    box = [840, 232, W - 840 - MX, 376]
    panel(layer, box, color="dune", fill="night2", w=1.4)
    layer.text([box[0] + 22, box[1] + 22, box[2] - 44, 26], "Sietch Tabr at centre", style="h2s")
    legend = [
        ("spice", "Tabr — Stilgar's seat; the warren the others answer to."),
        ("fremen", "A populous sietch; thousands deep in the rock."),
        ("sandl", "An outpost cache — water and weapons, lightly held."),
    ]
    for i, (col, txt) in enumerate(legend):
        ly = box[1] + 72 + i * 78
        hexcell(layer, box[0] + 42, ly + 12, 14, color=col, fill=a(col, 0.14), w=2)
        layer.text([box[0] + 74, ly - 4, box[2] - 100, 60], txt, style="body")
    footer(layer, "Routes are walked by night and never charted off-world; a known sietch is a dead sietch.")


# --------------------------------------------------------------------------- #
# 10 — Spice properties (thirds)                                               #
# --------------------------------------------------------------------------- #

def spice_properties(b):
    layer = chrome(b, "II · The Spice", "What melange does")
    cols = row([MX, 200, W - 2 * MX, 412], 3, gap=26)
    data = [
        ("LIFE", "spice", "It extends a human life by decades and turns the eyes blue-in-blue. "
         "To breathe spice is to never be free of it again."),
        ("MIND", "fremenb", "In the Bene Gesserit it opens Other Memory; in a Mentat it sharpens "
         "computation the Imperium banned machines from doing."),
        ("SPACE", "gold", "Folded through a Guild Navigator's prescience, it alone makes safe "
         "faster-than-light travel possible. No spice, no Imperium."),
    ]
    for cb, (head, col, body) in zip(cols, data):
        x, y, bw, bh = cb
        panel(layer, cb, color=col, fill="panel", w=1.5)
        layer.ellipse([x + bw / 2, y + 64], 30, 30, fill=a(col, 0.18), **S(2, col),
                      **EF(blur=10, color=col, opacity=0.45))
        layer.rect([x + 26, y + 110, 56, 5], fill=col, radius=2)
        layer.text([x + 26, y + 132, bw - 52, 30], head, style={"class": "h2", "color": col})
        layer.text([x + 26, y + 178, bw - 52, 200], body, style="body")


# --------------------------------------------------------------------------- #
# 11 — Melange cycle (circular sector diagram)                                  #
# --------------------------------------------------------------------------- #

def melange_cycle(b):
    layer = chrome(b, "II · The Spice", "The cycle of the maker")
    cx, cy = 446, 416
    stages = [
        ("SANDTROUT", "spice", "Larval makers seal off water underground."),
        ("PRE-SPICE MASS", "ember", "Trapped water + sand ferments; an explosion blooms."),
        ("THE WORM", "gold", "A sandworm grows to guard the bed for centuries."),
        ("MELANGE", "spiceb", "Sun-cured spice is left blowing across the open sand."),
    ]
    # four quadrant sectors forming a melange wheel
    for i, (name, col, sub) in enumerate(stages):
        a0 = -90 + i * 90 + 4
        a1 = -90 + (i + 1) * 90 - 4
        layer.sector([cx, cy], 150, a0, a1, fill=a(col, 0.16), **S(1.6, col))
        mid = math.radians((a0 + a1) / 2)
        lx = cx + 92 * math.cos(mid)
        ly = cy + 92 * math.sin(mid)
        layer.text([lx - 60, ly - 8, 120, 16], name,
                   style={"class": "kicker", "color": col, "align": "center", "font_size": 10})
    layer.ring([cx, cy], 40, 22, fill=a("spiceb", 0.4), **S(1.4, "spiceb"))
    # curved arrows around the wheel implying the cycle direction
    for i in range(4):
        a0 = -90 + i * 90 + 10
        layer.arc([cx, cy], 168, a0, a0 + 64, **S(1.6, "sand", stroke_linecap="round"))
    # right-hand legend
    for i, (name, col, sub) in enumerate(stages):
        ly = 224 + i * 96
        layer.text([760, ly, 420, 22], f"{i+1}. {name}", style={"class": "h2s", "color": col})
        layer.text([760, ly + 28, 420, 44], sub, style="body")
    footer(layer, "The maker and the spice are one organism across its life — kill the worms and the spice ends.")


# --------------------------------------------------------------------------- #
# 12 — CHOAM shares (bar chart)                                                 #
# --------------------------------------------------------------------------- #

def choam(b):
    layer = chrome(b, "II · The Spice", "Who holds the spice")
    layer.text([MX, 196, 360, 170],
               "Declared CHOAM directorship shares at the opening of the year — the ledger the "
               "whole Imperium fights over.", style="lead")
    for i, (lbl, val, col) in enumerate([("THRONE", "Corrino", "gold"),
                                         ("THE GUILD", "monopoly", "fremenb"),
                                         ("GREAT HOUSES", "the rest", "spice")]):
        y = 380 + i * 78
        vline(layer, MX, y, y + 54, col, 3)
        layer.text([MX + 18, y - 4, 320, 30], val, style={"class": "stat", "color": col, "font_size": 30})
        layer.text([MX + 18, y + 40, 320, 18], lbl, style="tag")
    pbox = [524, 196, W - 524 - MX, 420]
    panel(layer, pbox, color="dune", fill="night2", w=1.4)
    chart = Chart(Frame(domain=(0, 0, 6, 40),
                        box=(pbox[0] + 58, pbox[1] + 40, pbox[2] - 92, pbox[3] - 100)))
    bars = [("CORRINO", 34), ("GUILD", 25), ("ATREIDES", 14), ("HARKONNEN", 12),
            ("BG", 8), ("OTHER", 7)]
    chart.axes(x_ticks=[], y_ticks=[0, 10, 20, 30, 40], y_format=lambda v: f"{int(v)}%",
               grid=True, axis_color=DUNE, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    cols = [GOLD, FREMENB, SPICE, BLOOD, FREMEN, SAND]
    for i, ((name, val), col) in enumerate(zip(bars, cols)):
        chart.bars([(i + 0.5, val)], width=56, fill=col, radius=3)
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    for i, (name, val) in enumerate(bars):
        p = fr.point(i + 0.5, 0)
        layer.text([p.x - 52, pbox[1] + pbox[3] - 50, 104, 16], name,
                   style={"class": "tag", "align": "center"})
    footer(layer, "Shares in percent of CHOAM. The throne and the Guild together can starve any House of spice.")


# --------------------------------------------------------------------------- #
# 13 — Sandworm anatomy (smooth body + leader lines)                            #
# --------------------------------------------------------------------------- #

def sandworm(b):
    layer = chrome(b, "II · The Spice", "Shai-Hulud — the maker")
    # the worm body as one long smooth curve, bled across the plate
    with layer.bleed():
        body = [[120, 560], [300, 470], [520, 540], [740, 430], [980, 500], [1180, 380]]
        layer.polyline(body, smooth=True, fill="none",
                       **S(34, a("ember", 0.5), stroke_linecap="round"))
        layer.polyline(body, smooth=True, fill="none",
                       **S(22, a("sand", 0.5), stroke_linecap="round"))
        # ring segments along the body
        for bx, by in body[1:-1]:
            layer.ellipse([bx, by], 16, 16, fill="none", **S(1.4, a("dune", 0.9)))
    # the maw: concentric ring + a ring of crystal teeth (star)
    mx, my = 120, 560
    layer.ring([mx, my], 40, 18, fill=a("ember", 0.6), **S(2, "spice"),
               **EF(blur=12, color="spice", opacity=0.45))
    for deg in range(0, 360, 30):
        tx = mx + 28 * math.cos(math.radians(deg))
        ty = my + 28 * math.sin(math.radians(deg))
        layer.star([tx, ty], 6, 2.4, 3, rotation=deg + 90, fill="sandl")
    # labels
    labels = [
        ([120, 560], "THE MAW", "Crystal teeth; it swallows a harvester whole."),
        ([520, 540], "RING SEGMENTS", "Each segment a separate brain — it cannot be killed by shock."),
        ([1180, 380], "SENSING TAIL", "Reads rhythmic drum-sand; walk without rhythm to live."),
    ]
    lx = 470
    for i, (pt, head, body_t) in enumerate(labels):
        ly = 200 + i * 76
        layer.line([lx - 16, ly + 12], [lx + 320, ly + 12], **S(1.0, "dune"))
        layer.text([lx, ly, 320, 22], head, style="h2s")
        layer.text([lx, ly + 28, 360, 40], body_t, style="body")
    footer(layer, "Up to four hundred metres long. To the Fremen it is god; to the Guild it is the source of everything.")


# --------------------------------------------------------------------------- #
# 14 — Spice price (smooth line chart)                                          #
# --------------------------------------------------------------------------- #

def spice_price(b):
    layer = chrome(b, "II · The Spice", "The price of melange")
    pbox = [MX, 200, W - 2 * MX, 410]
    panel(layer, pbox, color="dune", fill="night2", w=1.4)
    chart = Chart(Frame(domain=(0, 0, 12, 100),
                        box=(pbox[0] + 64, pbox[1] + 36, pbox[2] - 110, pbox[3] - 96)))
    chart.axes(x_ticks=[0, 3, 6, 9, 12], y_ticks=[0, 25, 50, 75, 100],
               x_format=lambda v: f"M{int(v)}", y_format=lambda v: f"{int(v)}", grid=True,
               axis_color=DUNE, grid_color=GRIDC, label_style={"font_family": MONO, "color": MUTE})
    price = [(t, 40 + 22 * math.sin(t / 2.2) + 3.2 * t) for t in range(0, 13)]
    output = [(t, 70 - 2.6 * t + 8 * math.sin(t / 1.5)) for t in range(0, 13)]
    chart.line(price, stroke=SPICE, width=3.0, smooth=True, label="solari / decagram")
    chart.line(output, stroke=FREMENB, width=2.6, smooth=True, label="harvest yield")
    chart.legend(at=(pbox[0] + 64, pbox[1] + pbox[3] - 24))
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    p = fr.point(12, 78)
    dot(layer, p.x, p.y, 5, "spiceb", **EF(blur=8, color="spiceb", opacity=0.6))
    layer.text([p.x - 160, p.y - 26, 150, 16], "HARKONNEN SABOTAGE", style="kicker")
    footer(layer, "As yield falls the price climbs; whoever can throttle the harvest sets the number.")


# --------------------------------------------------------------------------- #
# 16 — Fremen discipline (quadrants)                                            #
# --------------------------------------------------------------------------- #

def fremen_creed(b):
    layer = chrome(b, "III · The Fremen", "The water discipline")
    quads = grid([MX, 196, W - 2 * MX, 420], cols=2, count=4, gap=20)
    laws = [
        ("THE TRIBE'S WATER", "fremenb", "Your body water belongs to the sietch, not to you. The dead are rendered."),
        ("NEVER ALONE", "spice", "Travel masked, by night, in rhythm. The desert kills the careless first."),
        ("THE MAKER", "gold", "Ride Shai-Hulud only when called; to summon a worm is to be made a man."),
        ("THE LONG PLAN", "sand", "Hoard water for generations. Kynes taught patience as a weapon."),
    ]
    for qb, (name, col, body) in zip(quads, laws):
        x, y, bw, bh = qb
        panel(layer, qb, color=col, fill="panel", w=1.5)
        layer.rect([x, y, 7, bh], fill=col)
        hexcell(layer, x + bw - 62, y + 58, 26, color=col, fill=a(col, 0.1), w=2)
        layer.text([x + 32, y + 38, bw - 150, 28], name, style={"class": "h2", "color": col})
        layer.text([x + 32, y + 84, bw - 120, 90], body, style="body")


# --------------------------------------------------------------------------- #
# 17 — Stillsuit schematic (radial leaders)                                     #
# --------------------------------------------------------------------------- #

def stillsuit(b):
    layer = chrome(b, "III · The Fremen", "The stillsuit")
    cx = 380
    # a simple figure silhouette from smooth outline
    outline = [[cx, 250], [cx + 34, 270], [cx + 30, 360], [cx + 40, 470], [cx + 20, 560],
               [cx, 560], [cx - 20, 560], [cx - 40, 470], [cx - 30, 360], [cx - 34, 270], [cx, 250]]
    layer.polyline(outline, smooth=True, closed=True, fill=a("fremen", 0.12), **S(2, "fremen"))
    layer.ellipse([cx, 224, ], 26, 26, fill=a("fremen", 0.14), **S(2, "fremen"))
    # catchment nodes
    nodes = [([cx, 224], "CAP & PLUGS", "Reclaims breath and the moisture of the nose."),
             ([cx + 30, 360], "TORSO LAYER", "Body heat drives the pumps; sweat is filtered back."),
             ([cx - 30, 470], "THIGH PUMPS", "Walking works the reclamation — motion is water."),
             ([cx, 558], "CATCHPOCKET", "Reclaimed water sipped through a tube at the neck.")]
    lx = 720
    for i, (pt, head, body_t) in enumerate(nodes):
        ly = 214 + i * 102
        trace(layer, [[pt[0], pt[1]], [lx - 40, pt[1]], [lx - 40, ly + 12], [lx, ly + 12]],
              color="fremen", w=1.4)
        layer.text([lx + 12, ly, 380, 22], head, style="h2b")
        layer.text([lx + 12, ly + 28, 380, 50], body_t, style="body")
    footer(layer, "A working stillsuit loses a thimble of water a day. Fremen children are fitted before they walk.")


# --------------------------------------------------------------------------- #
# 18 — Fremen roster (left rail, instanced eye crest)                           #
# --------------------------------------------------------------------------- #

def roster(b, eye):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="night")
    layer.rect([0, 0, 432, H], fill="night2")
    star_field(layer, [0, 0, 432, H], n=22)
    vline(layer, 432, 0, H, "spice", 2.2)
    layer.text([MX, 96, 320, 22], "III · THE FREMEN", style="kicker")
    layer.text([MX, 130, 320, 140], "The desert\npeople", style="h1")
    layer.rect([MX, 252, 120, 5], fill="spice", radius=2)
    layer.text([MX, 284, 300, 160],
               "Five who carry the prophecy and the water — by sietch and by station.", style="lead")
    layer.use(eye, [MX, 470, 120, 120],
              params={"rim": SPICE, "iris": FREMEN, "irisb": FREMENB, "pupil": NIGHT})
    layer.text([W - MX - 220, 698, 220, 18], f"CODEX · {_page:02d}/{TOTAL}", style="pnum")
    cards = column([474, 78, W - 474 - MX, 568], 5, gap=14)
    crew = [
        ("STILGAR", "naib of sietch tabr", "spice", "Leads Tabr. Measures every man by the water he keeps."),
        ("CHANI", "sayyadina · fedaykin", "fremenb", "Kynes' daughter; a death-commando and Muad'Dib's beloved."),
        ("LIET-KYNES", "imperial planetologist", "gold", "Serves two masters; dreams of an Arrakis turned green."),
        ("JAMIS", "fremen warrior", "sand", "Challenges the outsider to the crysknife — and loses."),
        ("THE FREMEN", "millions, uncounted", "ember", "The Imperium's blind spot: an army it never bothered to count."),
    ]
    for cb, (name, role, col, body) in zip(cards, crew):
        x, y, bw, bh = cb
        panel(layer, cb, color=col, fill="panel", w=1.4)
        layer.rect([x, y, 5, bh], fill=col)
        layer.ellipse([x + 44, y + bh / 2], 18, 18, fill=a("fremen", 0.5), **S(2, col))
        layer.ellipse([x + 44, y + bh / 2], 6, 6, fill="night")
        layer.text([x + 84, y + 16, bw - 240, 26], name, style={"class": "h2", "color": "cream", "font_size": 21})
        layer.text([x + 84, y + 50, bw - 240, 24], body, style="body")
        layer.text([x + bw - 196, y + 18, 176, 18], role.upper(),
                   style={"class": "tag", "align": "right"})


# --------------------------------------------------------------------------- #
# 19 — Crysknife geometry (angular)                                            #
# --------------------------------------------------------------------------- #

def crysknife(b):
    layer = chrome(b, "III · The Fremen", "The crysknife")
    layer.text([MX, 196, 380, 200],
               "Ground from a dead sandworm's tooth, the crysknife is never drawn without drawing "
               "blood. A fixed blade will dissolve unless kept near a body's electric field.", style="lead")
    facts = [("milk-white", "the fixed blade, made stable"),
             ("crystal", "the unfixed; volatile, kept caged"),
             ("never sheathed clean", "a Fremen law of honour")]
    for i, (eq, note) in enumerate(facts):
        y = 392 + i * 70
        panel(layer, [MX, y, 380, 56], color="sand", fill="panel", w=1.4)
        layer.text([MX + 18, y + 12, 200, 32], eq, style={"class": "monoS", "color": "sand", "font_size": 16})
        layer.text([MX + 224, y + 18, 150, 22], note, style="bodyM")
    # the blade itself — an angular faceted form
    pbox = [500, 196, W - 500 - MX, 420]
    panel(layer, pbox, color="dune", fill="night2", w=1.4)
    bx, by = pbox[0] + pbox[2] / 2, pbox[1] + pbox[3] / 2
    blade = [[bx, by - 150], [bx + 22, by - 40], [bx + 14, by + 80], [bx, by + 150],
             [bx - 14, by + 80], [bx - 22, by - 40]]
    layer.polygon(blade, fill=a("sandl", 0.16), **S(2.2, "sandl"))
    layer.line([bx, by - 150], [bx, by + 150], **S(1.0, a("sand", 0.7)))
    # the hilt ring + facet stars
    layer.ring([bx, by + 150], 26, 14, fill=a("ember", 0.5), **S(1.6, "spice"))
    for yy in (by - 90, by - 30, by + 30):
        layer.star([bx, yy], 5, 2, 4, rotation=-90, fill="sandl")
    layer.text([pbox[0] + 20, pbox[1] + 16, 260, 18], "MILK-WHITE · FIXED", style="kicker")
    footer(layer, "To show a crysknife to an outsider is to commit to killing them or sharing water — there is no third path.")


# --------------------------------------------------------------------------- #
# 20 — Fremen strength (gauges)                                                 #
# --------------------------------------------------------------------------- #

def fremen_strength(b):
    layer = chrome(b, "III · The Fremen", "What the Imperium never counted")
    bars = [
        ("DESERT MOBILITY", 0.97, "spice"),
        ("WORM-RIDING CORPS", 0.62, "gold"),
        ("STILLSUIT DISCIPLINE", 0.93, "fremenb"),
        ("WATER STORES (SOUTH)", 0.78, "fremen"),
        ("LOYALTY TO MUAD'DIB", 0.99, "ember"),
    ]
    track_x, track_w = 520, 590
    for i, (name, frac, col) in enumerate(bars):
        y = 224 + i * 78
        layer.text([MX, y - 2, 400, 22], name, style="mono")
        layer.rect([track_x, y, track_w, 18], fill="night2", radius=9, **S(1.2, "dune"))
        layer.rect([track_x, y, max(18, track_w * frac), 18], fill=col, radius=9,
                   **EF(blur=8, color=col, opacity=0.4))
        layer.text([track_x + track_w + 16, y - 4, 120, 26], f"{int(frac*100)}%",
                   style={"class": "stat", "color": col, "font_size": 24})
        for t in range(1, 10):
            tx = track_x + track_w * t / 10
            vline(layer, tx, y, y + 18, "night", 1)
    footer(layer, "Every gauge the Harkonnens never bothered to read — which is exactly why they lose the planet.")


# --------------------------------------------------------------------------- #
# 22 — Houses (two columns)                                                     #
# --------------------------------------------------------------------------- #

def houses(b):
    layer = chrome(b, "IV · The Powers", "Atreides & Harkonnen")
    left = [MX, 200, (W - 2 * MX - 28) / 2, 412]
    right = [left[0] + left[2] + 28, 200, left[2], 412]
    for box, name, col, blurb, rows in (
        (left, "HOUSE ATREIDES", "spice", "Ruled by loyalty and the Duke's word; loved by those they lead.",
         [("SEAT", "Caladan → Arrakis"), ("ARMY", "by devotion"),
          ("EDGE", "the desert's trust"), ("FLAW", "honour, exploited")]),
        (right, "HOUSE HARKONNEN", "blood", "Ruled by cruelty and debt; feared, never followed.",
         [("SEAT", "Giedi Prime"), ("ARMY", "by terror"),
          ("EDGE", "the throne's favour"), ("FLAW", "appetite, endless")]),
    ):
        panel(layer, box, color=col, fill="panel", w=1.8)
        x, y, bw, bh = box
        layer.rect([x, y, bw, 6], fill=col)
        hexcell(layer, x + bw / 2, y + 84, 40, color=col, w=2.2)
        layer.text([x, y + 148, bw, 30], name,
                   style={"class": "h2", "color": col, "align": "center", "font_size": 25})
        layer.text([x + 40, y + 190, bw - 80, 44], blurb, style={"class": "body", "align": "center"})
        for i, (k, v) in enumerate(rows):
            ry = y + 256 + i * 38
            hline(layer, x + 36, x + bw - 36, ry - 8, "dune", 1)
            layer.text([x + 36, ry, 160, 22], k, style={"class": "tag", "color": "mute"})
            layer.text([x + bw - 250, ry - 2, 214, 24], v,
                       style={"class": "monoS", "color": col, "align": "right", "font_size": 15})
    dot(layer, W / 2, 408, 26, "night2")
    circle_ring(layer, W / 2, 408, 26, "cream", 2)
    layer.text([W / 2 - 26, 396, 52, 24], "VS", style={"class": "num", "color": "cream"})


# --------------------------------------------------------------------------- #
# 23 — Landsraad hierarchy (tree)                                              #
# --------------------------------------------------------------------------- #

def landsraad(b):
    layer = chrome(b, "IV · The Powers", "The balance of the Imperium")
    def node(box, head, sub, col):
        x, y, bw, bh = box
        panel(layer, box, color=col, fill="night2", w=1.6)
        layer.rect([x, y, bw, 5], fill=col)
        layer.text([x + 16, y + 14, bw - 32, 24], head, style={"class": "h2", "font_size": 18, "color": "cream"})
        layer.text([x + 16, y + 44, bw - 32, 18], sub, style="tag")

    emperor = [W / 2 - 150, 192, 300, 74]
    node(emperor, "PADISHAH EMPEROR", "Shaddam IV · Corrino", "gold")
    tier = row([MX, 440, W - 2 * MX, 80], 3, gap=28)
    branches = [
        ("THE LANDSRAAD", "the Great Houses, in council", "spice"),
        ("THE SPACING GUILD", "monopoly on travel & banking", "fremenb"),
        ("THE BENE GESSERIT", "the hidden hand, the breeding plan", "fremen"),
    ]
    spine_y = 400
    hline(layer, tier[0][0] + tier[0][2] / 2, tier[-1][0] + tier[-1][2] / 2, spine_y, "dune", 1.6)
    vline(layer, W / 2, 266, spine_y, "dune", 1.6)
    for tb, (head, sub, col) in zip(tier, branches):
        cx = tb[0] + tb[2] / 2
        vline(layer, cx, spine_y, tb[1], "dune", 1.6)
        node(tb, head, sub, col)
        layer.text([tb[0] + 12, tb[1] + 92, tb[2] - 24, 18], "↳ checks the throne", style="bodyM")
    layer.text([MX, 300, 300, 90],
               "No power rules alone. The Emperor commands the Sardaukar; the Guild commands "
               "the void; the Sisterhood commands the bloodlines.", style="body")
    footer(layer, "Arrakis breaks the balance: whoever holds the spice can ignore all three at once.")


# --------------------------------------------------------------------------- #
# 24 — Power matrix (bento)                                                     #
# --------------------------------------------------------------------------- #

def power_matrix(b):
    layer = chrome(b, "IV · The Powers", "Four hidden powers")
    big = [MX, 196, 560, 420]
    panel(layer, big, color="fremenb", fill="panel", w=1.8)
    layer.text([MX + 30, 226, 500, 26], "THE SPACING GUILD", style="h2b")
    layer.text([MX + 30, 266, 500, 110],
               "Navigators mutated by spice fold space by prescience. They never rule openly — "
               "they simply decide who may travel, and so who may rule at all.", style="body")
    # a folded-space motif: nested rings + an arc
    layer.ring([MX + 280, 470, ], 96, 60, fill=a("fremenb", 0.1), **S(1.6, "fremenb"))
    layer.arc([MX + 280, 470], 120, 150, 390, **S(2, "fremen", stroke_linecap="round"))
    layer.star([MX + 280, 470], 18, 8, 4, fill="fremenb", **EF(blur=10, color="fremenb", opacity=0.5))

    tiles = [
        ([664, 196, 280, 200], "BENE GESSERIT", "fremen", "Centuries of breeding toward one mind."),
        ([960, 196, W - 960 - MX, 200], "THE MENTATS", "spice", "Human computers; thought the Imperium can't outlaw."),
        ([664, 416, W - 664 - MX, 200], "THE SARDAUKAR", "gold", "The Emperor's terror troops — until the desert."),
    ]
    for box, name, col, body in tiles:
        panel(layer, box, color=col, fill="panel", w=1.6)
        layer.text([box[0] + 22, box[1] + 20, box[2] - 44, 24], name, style={"class": "h2", "color": col, "font_size": 19})
        layer.text([box[0] + 22, box[1] + 54, box[2] - 44, 120], body, style="body")
        hexcell(layer, box[0] + box[2] - 40, box[1] + box[3] - 38, 14, color=col, w=1.6)


# --------------------------------------------------------------------------- #
# 25 — Trust rings (concentric)                                                 #
# --------------------------------------------------------------------------- #

def trust_rings(b):
    layer = chrome(b, "IV · The Powers", "Concentric loyalties")
    cx, cy = 446, 416
    zones = [
        (200, 158, "sand", "THE IMPERIUM", "a thousand worlds, loosely held"),
        (158, 110, "spice", "THE LANDSRAAD", "the Houses that can be called"),
        (110, 62, "fremenb", "THE INNER COUNCIL", "Guild, Sisterhood, throne"),
        (62, 22, "gold", "THE SPICE", "the one thing they all need"),
    ]
    for r_out, r_in, col, name, sub in zones:
        layer.ring([cx, cy], r_out, r_in, fill=a(col, 0.14), **S(1.8, col))
    layer.ellipse([cx, cy], 22, 22, fill="gold", **EF(blur=12, color="gold", opacity=0.55))
    for deg in range(0, 360, 30):
        layer.line([cx, cy], [cx + 200 * math.cos(math.radians(deg)),
                              cy + 200 * math.sin(math.radians(deg))], **S(1.0, "ghost"))
    for i, (r_out, r_in, col, name, sub) in enumerate(zones):
        ly = 228 + i * 96
        px = cx + (r_out + r_in) / 2
        layer.line([px, cy], [800, ly + 12], **S(1.2, col))
        dot(layer, px, cy, 4, col)
        layer.text([814, ly, 380, 24], name, style={"class": "h2s", "color": col})
        layer.text([814, ly + 28, 380, 24], sub, style="bodyM")
    footer(layer, "Trust thins outward; the spice at the centre is the only loyalty every ring shares.")


# --------------------------------------------------------------------------- #
# 27 — Breeding path (timeline)                                                 #
# --------------------------------------------------------------------------- #

def breeding_path(b):
    layer = chrome(b, "V · The Prophecy", "The breeding plan")
    spine_y = 404
    hline(layer, MX, W - MX, spine_y, "fremen", 2)
    nodes = row([MX, spine_y - 14, W - 2 * MX, 28], 5)
    beats = [
        ("−90 gen", "THE PLAN BEGINS", "The Sisterhood breeds toward one mind across centuries."),
        ("−2 gen", "JESSICA", "Ordered to bear a daughter — she bears a son for love instead."),
        ("0", "PAUL", "The unplanned Kwisatz Haderach, a generation early."),
        ("+spice", "THE AWAKENING", "Arrakis' spice opens what the bloodline only prepared."),
        ("+jihad", "OUT OF CONTROL", "The Sisterhood's tool becomes a force it cannot recall."),
    ]
    for i, (nb, (code, head, body_t)) in enumerate(zip(nodes, beats)):
        cx = nb[0] + nb[2] / 2
        col = "spice" if i in (2, 3) else "fremen"
        dot(layer, cx, spine_y, 10, "night")
        hexcell(layer, cx, spine_y, 11, color=col, w=2.2)
        dot(layer, cx, spine_y, 3, col)
        above = i % 2 == 0
        ty = spine_y - 150 if above else spine_y + 42
        layer.text([cx - 96, ty, 192, 18], code, style={"class": "kicker", "color": col, "align": "center"})
        layer.text([cx - 96, ty + 24, 192, 24], head, style={"class": "h2", "align": "center", "font_size": 16})
        layer.text([cx - 96, ty + 54, 192, 72], body_t, style={"class": "body", "align": "center", "font_size": 13})
    footer(layer, "The Bene Gesserit planned a messiah they could steer; they got one the desert steers instead.")


# --------------------------------------------------------------------------- #
# 28 — Muad'Dib's path (vertical roadmap)                                       #
# --------------------------------------------------------------------------- #

def path_of_muaddib(b):
    layer = chrome(b, "V · The Prophecy", "The path of Muad'Dib")
    layer.text([MX, 196, 360, 240],
               "Four turns carry a betrayed heir to the throne of the Imperium — each opening "
               "only once the desert has remade him.", style="lead")
    phases = [
        ("EXILE", "BETRAYAL", "Harkonnens take Arrakeen; the Duke dies, Paul flees to the sand.", "blood"),
        ("DESERT", "USUL", "The Fremen take him in; he is named, and learns the worm.", "spice"),
        ("UPRISING", "MUAD'DIB", "He breaks the spice harvest and bends the Guild to his will.", "gold"),
        ("THRONE", "KWISATZ HADERACH", "He takes the Imperium — and sees the jihad he cannot stop.", "fremenb"),
    ]
    bx, bw = 512, W - 512 - MX
    vline(layer, bx + 18, 208, 208 + len(phases) * 100 - 36, "dune", 2)
    for i, (ph, head, body_t, col) in enumerate(phases):
        y = 208 + i * 100
        dot(layer, bx + 18, y + 20, 12, "night")
        hexcell(layer, bx + 18, y + 20, 13, color=col, w=2.4)
        dot(layer, bx + 18, y + 20, 3, col)
        layer.text([bx + 58, y, 160, 18], ph, style={"class": "kicker", "color": col})
        layer.text([bx + 58, y + 22, bw - 60, 24], head, style={"class": "h2", "color": "cream", "font_size": 20})
        layer.text([bx + 58, y + 52, bw - 60, 42], body_t, style="body")
    footer(layer, "Prescience is a trap: seeing the path, he walks it — the storm was always at the end of the road.")


# --------------------------------------------------------------------------- #
# 29 — Quote (centered)                                                         #
# --------------------------------------------------------------------------- #

def quote(b, eye):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    with layer.bleed():
        sky(layer, "dusk")
        star_field(layer, [0, 0, W, 340], n=40)
        sun(layer, W / 2, 232, 120, core="#ffe6bf", edge="spice", halo=2.8, glow_blur=66)
        godrays(layer, W / 2, 232, color="spice", n=11, spread=560, length=420, alpha=0.04)
        dune_scape(layer, 540, lit="spice", rim=a("spiceb", 0.4))
        worm_silhouette(layer, W / 2, 560, 280, w=70, sun_color="spice")
        dust(layer, [0, 280, W, 280], n=36)
        vignette(layer, 0.74)
        letterbox(layer, 52)
    layer.use(eye, [W / 2 - 56, 168, 112, 112],
              params={"rim": SPICE, "iris": FREMEN, "irisb": FREMENB, "pupil": NIGHT})
    layer.text([180, 326, W - 360, 150],
               "“He who controls the spice\ncontrols the universe.”", style="h1C")
    layer.rect([W / 2 - 60, 470, 120, 5], fill="spice", radius=2,
               **EF(blur=12, color="spice", opacity=0.6))
    layer.text([0, 500, W, 22], "— BARON VLADIMIR HARKONNEN", style="tagC")
    layer.text([W - MX - 220, 694, 220, 18], f"CODEX · {_page:02d}/{TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 30 — Closing                                                                  #
# --------------------------------------------------------------------------- #

def closing(b, eye):
    global _page
    _page += 1
    layer = new_page(b, "close")
    with layer.bleed():
        sky(layer, "dawn")
        star_field(layer, [0, 0, W, 280], n=34)
        sun(layer, 900, 392, 104, core="#fff6da", edge="spiceb", halo=3.0, glow_blur=62)
        godrays(layer, 900, 392, color="spice", n=9, spread=440, length=360, alpha=0.05)
        dune_scape(layer, 452, lit="spice", rim=a("spiceb", 0.5))
        worm_silhouette(layer, 1000, 470, 240, w=66, sun_color="spice")
        fremen_figure(layer, 250, 512, 86)
        dust(layer, [0, 300, W, 260], n=40)
        vignette(layer, 0.72)
        letterbox(layer, 52)
    layer.text([MX, 150, 800, 22], "END OF CODEX", style="kicker")
    layer.text([MX, 192, 900, 130], "The spice\nmust flow.", style="h1")
    layer.text([MX, 360, 560, 28],
               "The codex is one program — fork it, fold it, carry it across the sand.", style="lead")
    chip = [MX, 430, 320, 56]
    layer.rect(chip, fill="spice", radius=6, **EF(blur=16, color="spice", opacity=0.6))
    layer.text([chip[0], chip[1] + 18, chip[2], 22], "uv run · dune_arrakis_codex", style="chip")
    layer.text([MX, 600, 900, 20],
               "FRAMEGRAPH PYTHON SDK · 30 PLATES · RING / ARC / SECTOR / STAR / SMOOTH / SYMBOLS",
               style="tag")
    layer.text([W - MX - 220, 600, 220, 18], "PLATE 30 / 30", style="pnum")


# --------------------------------------------------------------------------- #
# Assembly                                                                      #
# --------------------------------------------------------------------------- #

def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Arrakis Codex", profile="deck", lang="en")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)

    # The spice-eye crest — authored once, instanced across cover, dividers, roster,
    # quote and closing (friction #4: define_symbol + use, recoloured per instance).
    eye = b.define_symbol(
        "spice_eye",
        box=[0, 0, 100, 100],
        objects=[
            {"type": "ellipse", "center": [50, 50], "rx": 47, "ry": 47, "fill": "none",
             "stroke": "$rim", "stroke_style": {"stroke_width": 3},
             "glow": {"blur": 12, "color": "$rim", "opacity": 0.45}},
            {"type": "ellipse", "center": [50, 50], "rx": 35, "ry": 35, "fill": "$iris"},
            {"type": "ellipse", "center": [50, 50], "rx": 35, "ry": 35, "fill": "none",
             "stroke": "$irisb", "stroke_style": {"stroke_width": 2}},
            {"type": "ellipse", "center": [50, 50], "rx": 13, "ry": 13, "fill": "$pupil",
             "glow": {"blur": 8, "color": "$irisb", "opacity": 0.7}},
        ],
    )

    cover(b, eye)                                                       # 01
    contents(b)                                                         # 02
    divider(b, "div1", "I", "The Planet", "Arrakis, its moons and its warren.", eye)  # 03
    litany(b)                                                           # 04
    planet(b)                                                           # 05
    moons(b)                                                            # 06
    water(b)                                                            # 07
    sietch_network(b)                                                   # 08
    divider(b, "div2", "II", "The Spice", "Melange — the cycle and the powers.", eye)  # 09
    spice_properties(b)                                                 # 10
    melange_cycle(b)                                                    # 11
    choam(b)                                                            # 12
    sandworm(b)                                                         # 13
    spice_price(b)                                                      # 14
    divider(b, "div3", "III", "The Fremen", "Water, stillsuit and crysknife.", eye,
            accent="fremenb")                                           # 15
    fremen_creed(b)                                                     # 16
    stillsuit(b)                                                        # 17
    roster(b, eye)                                                      # 18
    crysknife(b)                                                        # 19
    fremen_strength(b)                                                  # 20
    divider(b, "div4", "IV", "The Powers", "Houses, Guild, Sisterhood, throne.", eye,
            accent="gold")                                              # 21
    houses(b)                                                           # 22
    landsraad(b)                                                        # 23
    power_matrix(b)                                                     # 24
    trust_rings(b)                                                      # 25
    divider(b, "div5", "V", "The Prophecy", "The breeding path and the storm.", eye)  # 26
    breeding_path(b)                                                    # 27
    path_of_muaddib(b)                                                  # 28
    quote(b, eye)                                                       # 29
    closing(b, eye)                                                     # 30
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="rasterise pages to out/dune/")
    args = ap.parse_args()

    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} slides — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in report.issues[:50]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    out = os.path.join(ROOT, "tests", "fixtures", "dune-arrakis-codex.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")

    if args.render:
        os.system(f"cd {ROOT} && python3 tooling/render_fixtures.py "
                  f"tests/fixtures/dune-arrakis-codex.fg.yaml --out out/dune")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
