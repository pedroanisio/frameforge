#!/usr/bin/env python3
"""IMPERIAL DOCTRINE — a 20-slide Galactic Empire command briefing.

A Star Wars deck authored entirely from the FrameGraph Python SDK. The Empire's
visual identity is cold and authoritarian: a near-black gunmetal field, Imperial
red as the single accent, condensed bureaucratic type, hard right-angled corners
(no rounding), thin precise rules and a symmetric, hierarchical layout language.
The recurring emblem is the Imperial cog — a toothed command gear.

It is the deliberate opposite of the companion "Alliance Field Manual" deck
(warm, rounded, asymmetric, serif): the two decks share the SDK but almost no
cosmetics, so the pair reads as range, not one template reskinned.

Run from the repository root::

    uv run python examples/imperial_doctrine_deck.py            # build + validate + write YAML
    uv run python examples/imperial_doctrine_deck.py --render   # also rasterise pages to out/empire/
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
    grid,
    inset,
    rgba,
    row,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas, palette, type                                                        #
# --------------------------------------------------------------------------- #

W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
MX = 76                                  # content margin

VOID = "#06080c"        # cold near-black — Imperial negative space
VOID2 = "#0a0e15"       # lifted panel base
PANEL = "#0d131c"       # card fill
PANEL2 = "#111a25"      # alt card fill
STEEL = "#243140"       # structural hairline / gunmetal edge
STEELB = "#3a4a5c"      # brighter steel
GRIDC = "#121b26"       # faint structural grid on the void
RED = "#c4202c"         # Imperial red — the one accent
REDB = "#ff4953"        # bright alert red
REDD = "#7d1820"        # dim oxblood
WHITE = "#eef3f8"
INK = "#9fb0c0"         # body text
MUTE = "#5a6b7a"        # captions
ICE = "#8fb4d6"         # cold scanner highlight (rare)

COND = ["Fira Sans Condensed", "Arial Narrow", "sans-serif"]   # rigid headers
SANS = ["Fira Sans", "Arial", "sans-serif"]                    # body
MONO = ["Fira Mono", "DejaVu Sans Mono", "monospace"]          # HUD / data

TOTAL = 20
_page = 0

COLORS = {
    "void": VOID, "void2": VOID2, "panel": PANEL, "panel2": PANEL2,
    "steel": STEEL, "steelb": STEELB, "gridc": GRIDC, "red": RED,
    "redb": REDB, "redd": REDD, "white": WHITE, "ink": INK, "mute": MUTE,
    "ice": ICE, "ghost": "#0c1420",
}


def hexof(c: str) -> str:
    return COLORS.get(c, c)


def a(color: str, alpha: float) -> str:
    """Translucent paint as portable rgba() (cairosvg drops #rrggbbaa alpha)."""
    return rgba(hexof(color), alpha)


STYLES = {
    # condensed bureaucratic stamps
    "kicker": dict(font_family=MONO, font_size=13, font_weight=700, color="red",
                   text_transform="uppercase", letter_spacing=5),
    "kickerW": dict(font_family=MONO, font_size=13, font_weight=700, color="ice",
                    text_transform="uppercase", letter_spacing=5),
    "tag": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                text_transform="uppercase", letter_spacing=3),
    "tagC": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=4, align="center"),
    "tagR": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=3, align="right"),
    "pnum": dict(font_family=MONO, font_size=11, font_weight=700, color="steelb",
                 letter_spacing=2, align="right"),
    # titles
    "h1": dict(font_family=COND, font_size=62, font_weight=700, color="white",
               letter_spacing=3, line_height=1.0, text_transform="uppercase"),
    "title": dict(font_family=COND, font_size=33, font_weight=700, color="white",
                  letter_spacing=2, line_height=1.06, text_transform="uppercase"),
    "h2": dict(font_family=COND, font_size=22, font_weight=700, color="white",
               line_height=1.12, letter_spacing=1, text_transform="uppercase"),
    "h2r": dict(font_family=COND, font_size=21, font_weight=700, color="red",
                line_height=1.14, letter_spacing=1, text_transform="uppercase"),
    "big": dict(font_family=COND, font_size=200, font_weight=700, color="white",
                letter_spacing=-2, line_height=0.9),
    "idx": dict(font_family=COND, font_size=170, font_weight=700, color="ghost",
                line_height=0.9, text_transform="uppercase"),
    # body
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
    "monoR": dict(font_family=MONO, font_size=12.5, font_weight=700, color="red",
                  line_height=1.4, letter_spacing=1),
    "stat": dict(font_family=COND, font_size=46, font_weight=700, color="red",
                 line_height=1.0),
    "statW": dict(font_family=COND, font_size=46, font_weight=700, color="white",
                  line_height=1.0),
    "num": dict(font_family=MONO, font_size=18, font_weight=700, color="red",
                align="center", line_height=1.0),
    "chip": dict(font_family=MONO, font_size=13, font_weight=700, color="white",
                 align="center", letter_spacing=3, text_transform="uppercase"),
    "creed": dict(font_family=COND, font_size=40, font_weight=700, color="white",
                  line_height=1.18, align="center", letter_spacing=1,
                  text_transform="uppercase"),
}


# --------------------------------------------------------------------------- #
# Imperial drawing vocabulary (cold, hard-edged, symmetric)                    #
# --------------------------------------------------------------------------- #

def _wrap_text(layer):
    """Route every layer.text(...) through a one-child group (tabular-box-model)."""
    raw_text = layer.text  # noqa: F841 — kept to mirror the SDK monkeypatch idiom

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


def stroke(w, color=STEEL, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": w, **extra}}


def hline(layer, x0, x1, y, color=STEEL, w=1.0, **extra):
    layer.line([x0, y], [x1, y], **stroke(w, color, **extra))


def vline(layer, x, y0, y1, color=STEEL, w=1.0, **extra):
    layer.line([x, y0], [x, y1], **stroke(w, color, **extra))


def dot(layer, cx, cy, r, fill, **extra):
    layer.ellipse([cx, cy], r, r, fill=fill, **extra)


def ring(layer, cx, cy, r, color=RED, w=2.0, glow=None, **extra):
    fields = stroke(w, color, **extra)
    if glow is not None:
        fields["glow"] = glow
    layer.ellipse([cx, cy], r, r, fill="none", **fields)


def square_grid(layer, box, step=40, color=GRIDC, w=1.0):
    x, y, bw, bh = box
    gx = x
    while gx <= x + bw + 0.5:
        vline(layer, gx, y, y + bh, color, w)
        gx += step
    gy = y
    while gy <= y + bh + 0.5:
        hline(layer, x, x + bw, gy, color, w)
        gy += step


def corner_ticks(layer, box, color=STEELB, ln=22, w=1.6, inset_px=0):
    """Hard L-brackets at the four corners — the Imperial readout frame."""
    x, y, bw, bh = inset(box, inset_px)
    for (cxp, cyp, sx, sy) in (
        (x, y, 1, 1), (x + bw, y, -1, 1),
        (x, y + bh, 1, -1), (x + bw, y + bh, -1, -1),
    ):
        layer.line([cxp, cyp], [cxp + sx * ln, cyp], **stroke(w, color))
        layer.line([cxp, cyp], [cxp, cyp + sy * ln], **stroke(w, color))


def panel(layer, box, *, color=STEEL, fill="panel", w=1.4, fill_alpha=None, glow_blur=0):
    """A hard-cornered Imperial panel (radius 0)."""
    f = a(color, fill_alpha) if fill_alpha is not None else fill
    fields = dict(fill=f, radius=0, **stroke(w, color))
    if glow_blur:
        fields["glow"] = {"blur": glow_blur, "color": hexof(color), "opacity": 0.5}
    layer.rect(box, **fields)


def cog(layer, cx, cy, r, *, color=RED, teeth=12, core="void2"):
    """Imperial command cog — a toothed gear ring with a hex core."""
    ring(layer, cx, cy, r, color, 2.6)
    ring(layer, cx, cy, r * 0.66, color, 1.6)
    for i in range(teeth):
        deg = i * 360 / teeth
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        layer.line([cx + r * c, cy + r * s], [cx + (r + 11) * c, cy + (r + 11) * s],
                   **stroke(3.0, color))
    # central six-point hex
    hexagon(layer, cx, cy, r * 0.40, color=color, fill=a(color, 0.12), w=2.0)
    dot(layer, cx, cy, r * 0.10, color)


def hexagon(layer, cx, cy, r, *, color=RED, fill="none", w=1.8, **extra):
    pts = [[cx + r * math.cos(math.radians(60 * i - 30)),
            cy + r * math.sin(math.radians(60 * i - 30))] for i in range(6)]
    layer.polygon(pts, fill=fill, **stroke(w, color), **extra)


def chevron(layer, cx, cy, size, color=RED, w=2.4, down=False):
    s = -1 if down else 1
    layer.polyline([[cx - size, cy + s * size * 0.6], [cx, cy - s * size * 0.6],
                    [cx + size, cy + s * size * 0.6]], **stroke(w, color))


def trace(layer, pts, color=RED, w=2.0, node_r=4.0, node=True):
    layer.polyline(pts, **stroke(w, color))
    if node:
        dot(layer, *pts[0], node_r, color)
        dot(layer, *pts[-1], node_r, color)


def chrome(b, kicker, title, *, kstyle="kicker"):
    """Standard Imperial content frame: void bg, corner grid, kicker, title, footer."""
    global _page
    _page += 1
    n = _page
    layer = new_page(b, f"p{n:02d}")
    layer.rect([0, 0, W, H], fill="void")
    square_grid(layer, [0, 0, W, 150], step=48, color=GRIDC, w=1.0)
    hline(layer, 0, W, 150, "steel", 1.2)
    layer.text([MX, 56, W - 2 * MX, 22], kicker, style=kstyle)
    layer.text([MX, 82, W - 2 * MX, 56], title, style="title")
    # twin Imperial rule
    layer.rect([MX, 138, 96, 5], fill="red", radius=0)
    hline(layer, 0, W, 690, "steel", 1.0)
    layer.text([W - MX - 200, 698, 200, 18], f"ISB · {n:02d}/{TOTAL}", style="pnum")
    layer.text([MX, 698, 520, 18], "IMPERIAL DOCTRINE · CLASSIFIED · ORDER THROUGH POWER",
               style="tag")
    return layer


def footer(layer, text):
    layer.text([MX, 664, W - 2 * MX, 18], text, style="bodyM")


# --------------------------------------------------------------------------- #
# 01 — Cover                                                                    #
# --------------------------------------------------------------------------- #

def cover(b):
    global _page
    _page += 1
    layer = new_page(b, "cover")
    layer.rect([0, 0, W, H], fill="void")
    square_grid(layer, [0, 0, W, H], step=64, color=GRIDC, w=1.0)
    # central authority cog, large, dead-centre-right
    cog(layer, 1010, 360, 150, color="red", teeth=16)
    ring(layer, 1010, 360, 196, "steel", 1.2)
    # title plate, hard left
    layer.text([MX, 168, 760, 26], "GALACTIC EMPIRE · IMPERIAL SECURITY BUREAU",
               style="kicker")
    layer.text([MX, 214, 820, 150], "IMPERIAL\nDOCTRINE", style="h1")
    layer.rect([MX, 392, 150, 5], fill="red")
    layer.text([MX, 418, 600, 28], "Order Through Power — a doctrine of the New Order.",
               style="lead")
    corner_ticks(layer, [40, 40, W - 80, H - 80], color="steel", ln=34, w=1.4)
    layer.text([MX, 600, 820, 20],
               "20 PLATES · AUTHORED THROUGH THE FRAMEGRAPH PYTHON SDK · FLAT VECTOR",
               style="tag")
    layer.text([W - MX - 200, 600, 200, 18], "PLATE 01 / 20", style="pnum")


# --------------------------------------------------------------------------- #
# 02 — Contents                                                                 #
# --------------------------------------------------------------------------- #

def contents(b):
    layer = chrome(b, "Manifest — three passes over the New Order", "Contents")
    items = [
        ("I", "The Order", "Doctrine, command and the chain that cannot be broken."),
        ("II", "The Fleet", "Capital line, the battle station, and force projection."),
        ("III", "Operations", "Deployment, readiness and the campaign to come."),
    ]
    rows = column([MX, 208, W - 2 * MX, 3 * 138], 3, gap=14)
    for (n, head, sub), rb in zip(items, rows):
        x, y, bw, bh = rb
        panel(layer, [x, y, bw, bh - 14], color="steel", fill="void2", w=1.3)
        layer.rect([x, y, 6, bh - 14], fill="red")
        hexagon(layer, x + 64, y + (bh - 14) / 2, 30, color="red", w=2.2)
        layer.text([x + 44, y + (bh - 14) / 2 - 18, 44, 34], n, style="num")
        layer.text([x + 118, y + 26, bw - 160, 30], head, style="h2")
        layer.text([x + 118, y + 62, bw - 200, 30], sub, style="body")
        layer.text([x + bw - 96, y + 26, 72, 20], f"{rows.index(rb)+1:02d}",
                   style={"class": "tagR", "color": "steelb", "font_size": 13})


# --------------------------------------------------------------------------- #
# Section dividers                                                              #
# --------------------------------------------------------------------------- #

def divider(b, pid, secno, title, subtitle):
    global _page
    _page += 1
    layer = new_page(b, pid)
    layer.rect([0, 0, W, H], fill="void")
    square_grid(layer, [0, 0, W, H], step=64, color="ghost", w=1.0)
    layer.text([MX - 4, 150, 520, 280], secno, style="idx")
    layer.text([520, 248, 360, 22], f"SECTION {secno}", style="kicker")
    layer.text([520, 280, 700, 120], title, style="h1")
    layer.rect([526, 396, 130, 5], fill="red")
    layer.text([526, 420, 660, 80], subtitle, style="lead")
    # flanking cog
    cog(layer, 1130, 150, 56, color="redd", teeth=12)
    corner_ticks(layer, [40, 40, W - 80, H - 80], color="steel", ln=34, w=1.4)
    chevron(layer, 1150, 600, 15, color="red")
    chevron(layer, 1150, 626, 15, color="steel")
    layer.text([W - MX - 200, 698, 200, 18], f"ISB · {_page:02d}/{TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 04 — The creed (centered / symmetric)                                         #
# --------------------------------------------------------------------------- #

def creed(b):
    layer = chrome(b, "Doctrine — first article", "The New Order")
    layer.text([0, 232, W, 22], "// ARTICLE I", style="tagC")
    layer.text([200, 272, W - 400, 150],
               "Peace is the silence\nof a galaxy that obeys.", style="creed")
    layer.rect([W / 2 - 70, 470, 140, 5], fill="red")
    layer.text([W / 2 - 380, 500, 760, 90],
               "Order is not requested; it is imposed and then maintained. Where fear "
               "of this station is decisive, dissent never has the chance to organise.",
               style="leadC")
    cog(layer, 240, 360, 30, color="steel", teeth=10)
    cog(layer, W - 240, 360, 30, color="steel", teeth=10)


# --------------------------------------------------------------------------- #
# 05 — Chain of command (hierarchy tree)                                        #
# --------------------------------------------------------------------------- #

def hierarchy(b):
    layer = chrome(b, "I · The Order", "Chain of command")
    # node helper
    def node(box, head, sub, col):
        x, y, bw, bh = box
        panel(layer, box, color=col, fill="void2", w=1.6)
        layer.rect([x, y, bw, 5], fill=col)
        layer.text([x + 16, y + 16, bw - 32, 24], head,
                   style={"class": "h2", "font_size": 18, "color": "white"})
        layer.text([x + 16, y + 46, bw - 32, 18], sub, style="tag")

    emperor = [W / 2 - 150, 196, 300, 76]
    node(emperor, "THE EMPEROR", "Palpatine · absolute", "red")
    vader = [W / 2 - 130, 320, 260, 70]
    node(vader, "LORD VADER", "enforcer of the will", "red")
    vline(layer, W / 2, 272, 320, "red", 2)

    tier = row([MX, 452, W - 2 * MX, 80], 4, gap=20)
    branches = [
        ("MOFF TARKIN", "Outer Rim · governance", "steelb"),
        ("HIGH COMMAND", "Navy · order of battle", "steelb"),
        ("ISB", "security · loyalty", "steelb"),
        ("COMPNOR", "doctrine · the New Order", "steelb"),
    ]
    spine_y = 420
    hline(layer, tier[0][0] + tier[0][2] / 2, tier[-1][0] + tier[-1][2] / 2, spine_y,
          "steel", 1.6)
    vline(layer, W / 2, 390, spine_y, "steel", 1.6)
    for tb, (head, sub, col) in zip(tier, branches):
        cx = tb[0] + tb[2] / 2
        vline(layer, cx, spine_y, tb[1], "steel", 1.6)
        node(tb, head, sub, col)
        # subordinate rank
        layer.text([tb[0] + 12, tb[1] + 92, tb[2] - 24, 18],
                   "↳ line officers · garrisons", style="bodyM")
    footer(layer, "Authority flows in one direction only; a severed branch is replaced, never repaired.")


# --------------------------------------------------------------------------- #
# 06 — Doctrine pillars (thirds)                                                #
# --------------------------------------------------------------------------- #

def pillars(b):
    layer = chrome(b, "I · The Order", "Three pillars of control")
    cols = row([MX, 200, W - 2 * MX, 410], 3, gap=26)
    data = [
        ("I", "FEAR", "The battle station, not the senate, keeps the systems in line. "
         "Fear of force is cheaper to garrison than consent."),
        ("II", "ORDER", "One law, one currency, one fleet. Variation is inefficiency; "
         "inefficiency is the first symptom of rebellion."),
        ("III", "SUPREMACY", "Technological terror without rival. The Empire is never "
         "matched — only obeyed or destroyed."),
    ]
    for cb, (roman, head, body) in zip(cols, data):
        x, y, bw, bh = cb
        panel(layer, cb, color="steel", fill="void2", w=1.4)
        corner_ticks(layer, cb, color="red", ln=18, w=2.0)
        layer.text([x + 26, y + 30, bw - 52, 50], roman, style="stat")
        hline(layer, x + 26, x + 80, y + 98, "red", 3)
        layer.text([x + 26, y + 118, bw - 52, 28], head, style="h2")
        layer.text([x + 26, y + 160, bw - 52, 200], body, style="body")
        hexagon(layer, x + bw - 40, y + bh - 38, 12, color="steelb", w=1.6)


# --------------------------------------------------------------------------- #
# 08 — Fleet roster (left rail)                                                 #
# --------------------------------------------------------------------------- #

def roster(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="void")
    layer.rect([0, 0, 432, H], fill="void2")
    square_grid(layer, [0, 0, 432, H], step=48, color="gridc", w=1.0)
    vline(layer, 432, 0, H, "red", 2.4)
    layer.text([MX, 96, 320, 22], "II · THE FLEET", style="kicker")
    layer.text([MX, 130, 320, 140], "THE CAPITAL\nLINE", style="h1")
    layer.rect([MX, 268, 120, 5], fill="red")
    layer.text([MX, 296, 300, 180],
               "Five classes hold the Imperial order of battle, listed bow to stern "
               "by displacement and command weight.", style="lead")
    cog(layer, MX + 70, 560, 50, color="redd", teeth=12)
    layer.text([W - MX - 200, 698, 200, 18], f"ISB · {_page:02d}/{TOTAL}", style="pnum")

    cards = column([474, 78, W - 474 - MX, 568], 5, gap=14)
    ships = [
        ("EXECUTOR", "super star destroyer", "19,000 m", "red"),
        ("IMPERIAL II", "star destroyer · line", "1,600 m", "steelb"),
        ("VICTORY", "star destroyer · picket", "900 m", "steelb"),
        ("TIE/LN", "interceptor swarm", "6.4 m", "steelb"),
        ("LAMBDA", "command shuttle", "20 m", "steelb"),
    ]
    for cb, (name, role, scale, col) in zip(cards, ships):
        x, y, bw, bh = cb
        panel(layer, cb, color=col, fill="void2", w=1.3)
        layer.rect([x, y, 5, bh], fill=col)
        # wedge silhouette glyph (a Star Destroyer is a triangle)
        layer.polygon([[x + 30, y + bh / 2 - 18], [x + 92, y + bh / 2],
                       [x + 30, y + bh / 2 + 18]], fill=a(col, 0.16), **stroke(1.6, col))
        layer.text([x + 116, y + 16, bw - 250, 26], name,
                   style={"class": "h2", "color": "white", "font_size": 21})
        layer.text([x + 116, y + 50, bw - 250, 24], role.upper(), style="tag")
        layer.text([x + bw - 150, y + 22, 130, 30], scale,
                   style={"class": "monoR", "align": "right", "font_size": 18})
        layer.text([x + bw - 150, y + 54, 130, 16], "LENGTH",
                   style={"class": "tagR", "color": "mute"})


# --------------------------------------------------------------------------- #
# 09 — Star Destroyer schematic (radial labelled)                              #
# --------------------------------------------------------------------------- #

def schematic(b):
    layer = chrome(b, "II · The Fleet", "Imperial-class · schematic")
    # the wedge, centred-left, drawn flat
    apex = [300, 410]
    base_top = [780, 300]
    base_bot = [780, 520]
    layer.polygon([apex, base_top, base_bot],
                  fill=a("steel", 0.14), **stroke(2.2, "steelb"))
    # spine + structural ribs
    layer.line([apex[0], apex[1]], [base_top[0], 410], **stroke(1.4, "steel"))
    for t in (0.3, 0.5, 0.7, 0.88):
        x = apex[0] + (base_top[0] - apex[0]) * t
        yt = apex[1] + (base_top[1] - apex[1]) * t
        yb = apex[1] + (base_bot[1] - apex[1]) * t
        layer.line([x, yt], [x, yb], **stroke(1.0, "steel"))
    # command tower
    panel(layer, [690, 372, 60, 22], color="red", fill_alpha=0.22, w=1.6)
    dot(layer, 720, 360, 6, "redb")
    # labelled leaders to the right
    labels = [
        (apex, "BOW LANCE", "Forward ion array; first to fire on approach."),
        ([560, 360], "HANGAR THROAT", "Launches six TIE squadrons in one cycle."),
        ([720, 360], "COMMAND TOWER", "Bridge, sensor globes and the captain's deck."),
        ([770, 500], "ENGINE BANK", "Three main drives; sublight at flank in seconds."),
    ]
    lx = 850
    for i, (pt, head, body) in enumerate(labels):
        ly = 214 + i * 102
        trace(layer, [[pt[0], pt[1]], [lx - 34, pt[1]], [lx - 34, ly + 12], [lx, ly + 12]],
              color="red", w=1.4, node_r=3.5)
        layer.text([lx + 12, ly, 360, 22], head, style="h2r")
        layer.text([lx + 12, ly + 28, 360, 50], body, style="body")
    footer(layer, "Sixty turbolasers, sixty ion cannons, a full wing of fighters — one ship, one province subdued.")


# --------------------------------------------------------------------------- #
# 10 — Fleet strength (big number)                                             #
# --------------------------------------------------------------------------- #

def big_number(b):
    layer = chrome(b, "II · The Fleet", "The order of battle")
    layer.text([MX - 4, 210, 760, 240], "25,000", style="big")
    layer.text([MX + 2, 452, 520, 30], "star destroyers in active Imperial service",
               style="lead")
    layer.rect([MX, 502, 300, 5], fill="red")
    notes = column([812, 206, W - 812 - MX, 380], 3, gap=24)
    facts = [
        ("ONE DOCTRINE", "Every keel is built to a single specification; any yard can berth any ship."),
        ("TOTAL REACH", "A destroyer can be on station in any sector inside a standard rotation."),
        ("NO ATTRITION", "Losses are replaced from the slips faster than an enemy can inflict them."),
    ]
    for nb, (h, body) in zip(notes, facts):
        x, y, bw, bh = nb
        vline(layer, x, y + 2, y + 58, "red", 3)
        layer.text([x + 18, y, bw - 18, 22], h, style="h2r")
        layer.text([x + 18, y + 32, bw - 18, 80], body, style="body")


# --------------------------------------------------------------------------- #
# 11 — Force comparison (two columns)                                          #
# --------------------------------------------------------------------------- #

def comparison(b):
    layer = chrome(b, "II · The Fleet", "The balance of force")
    left = [MX, 200, (W - 2 * MX - 28) / 2, 412]
    right = [left[0] + left[2] + 28, 200, left[2], 412]
    for box, name, col, blurb, rows in (
        (left, "THE EMPIRE", "red",
         "An industrial war machine answering to one will.",
         [("HULLS", "25,000+"), ("FIGHTERS", "millions"),
          ("DOCTRINE", "annihilation"), ("MORALE", "by decree")]),
        (right, "THE INSURGENCY", "steelb",
         "A scattering of stolen ships and borrowed crews.",
         [("HULLS", "~ 220"), ("FIGHTERS", "few hundred"),
          ("DOCTRINE", "hit and fade"), ("MORALE", "by hope")]),
    ):
        panel(layer, box, color=col, fill="void2", w=1.8)
        x, y, bw, bh = box
        layer.rect([x, y, bw, 6], fill=col)
        cog(layer, x + bw / 2, y + 86, 44, color=col, teeth=12)
        layer.text([x, y + 150, bw, 30], name,
                   style={"class": "h2", "color": col, "align": "center", "font_size": 26})
        layer.text([x + 40, y + 192, bw - 80, 44], blurb,
                   style={"class": "body", "align": "center"})
        for i, (k, v) in enumerate(rows):
            ry = y + 256 + i * 40
            hline(layer, x + 36, x + bw - 36, ry - 8, "gridc", 1)
            layer.text([x + 36, ry, 160, 22], k,
                       style={"class": "tag", "color": "mute"})
            layer.text([x + bw - 240, ry - 2, 204, 24], v,
                       style={"class": "monoR", "color": col, "align": "right",
                              "font_size": 16})
    dot(layer, W / 2, 408, 26, "void2")
    ring(layer, W / 2, 408, 26, "white", 2)
    layer.text([W / 2 - 26, 396, 52, 24], "VS", style={"class": "num", "color": "white"})


# --------------------------------------------------------------------------- #
# 12 — Battle station (concentric rings)                                       #
# --------------------------------------------------------------------------- #

def battle_station(b):
    layer = chrome(b, "II · The Fleet", "The ultimate sanction")
    cx, cy = 446, 416
    zones = [
        (208, "OUTER HULL", "steel", "120 km of armoured plate"),
        (158, "TRENCH LINE", "steelb", "surface defence corridor"),
        (104, "REACTOR SHAFT", "red", "the single thermal exhaust"),
        (54, "CORE", "redb", "hypermatter annihilation reactor"),
    ]
    for r, name, col, sub in zones:
        ring(layer, cx, cy, r, col, 2.2)
    # the superlaser dish (offset crater, upper-left)
    ring(layer, cx - 64, cy - 64, 46, "red", 2.2)
    dot(layer, cx - 64, cy - 64, 12, "redb", glow={"blur": 12, "color": REDB, "opacity": 0.6})
    # converging superlaser beams
    for dx, dy in ((-30, -10), (-10, -30), (-46, -46), (10, -46), (-46, 10)):
        layer.line([cx - 64 + dx, cy - 64 + dy], [cx - 64, cy - 64], **stroke(1.2, "red"))
    dot(layer, cx, cy, 12, "redb", glow={"blur": 10, "color": REDB, "opacity": 0.7})
    for deg in range(0, 360, 30):
        layer.line([cx, cy], [cx + 208 * math.cos(math.radians(deg)),
                              cy + 208 * math.sin(math.radians(deg))], **stroke(1.0, "ghost"))
    for i, (r, name, col, sub) in enumerate(zones):
        ly = 232 + i * 96
        px = cx + r
        layer.line([px, cy], [820, ly + 12], **stroke(1.2, col))
        dot(layer, px, cy, 4, col)
        layer.text([832, ly, 360, 24], name, style={"class": "h2r", "color": col})
        layer.text([832, ly + 28, 360, 24], sub, style="bodyM")
    footer(layer, "One reactor shaft, two metres wide, runs straight to the core — the only line the defence plan ignores.")


# --------------------------------------------------------------------------- #
# 14 — Deployment map (full-bleed sector grid)                                 #
# --------------------------------------------------------------------------- #

def deployment(b):
    layer = chrome(b, "III · Operations", "Outer Rim deployment")
    map_box = [MX, 196, W - 2 * MX, 420]
    layer.rect(map_box, fill="void2")
    square_grid(layer, map_box, step=37, color="gridc", w=1.0)
    corner_ticks(layer, map_box, color="steel", ln=20, w=1.4)
    zones = [
        ("CORE WORLDS", [MX + 28, 228, 280, 150], "steelb", "pacified"),
        ("THE COLONIES", [MX + 330, 228, 240, 220], "steelb", "garrisoned"),
        ("MID RIM", [MX + 596, 228, 230, 150], "red", "contested"),
        ("OUTER RIM", [MX + 852, 228, 224, 220], "red", "active ops"),
        ("THE EXPANSE", [MX + 28, 400, 540, 178], "steel", "uncharted"),
        ("WILD SPACE", [MX + 596, 400, 230, 178], "redd", "denied"),
    ]
    for name, bx, col, status in zones:
        panel(layer, bx, color=col, fill_alpha=0.06, w=1.5)
        layer.text([bx[0] + 14, bx[1] + 12, bx[2] - 28, 18], name,
                   style={"class": "kicker", "color": col, "font_size": 12})
        layer.text([bx[0] + 14, bx[1] + bx[3] - 26, bx[2] - 28, 16], f"STATUS · {status}",
                   style={"class": "tag", "color": "mute"})
    # patrol vectors
    layer.arrow([MX + 308, 300], [MX + 596, 300], color=RED, width=2.0, head=10)
    layer.arrow([MX + 826, 320], [MX + 852, 320], color=RED, width=2.0, head=10)
    layer.arrow([MX + 568, 470], [MX + 596, 470], color=REDD, width=2.0, head=9)
    # fleet markers
    for (mx, my) in ((MX + 700, 300), (MX + 960, 320), (MX + 700, 490)):
        hexagon(layer, mx, my, 12, color="red", fill=a("red", 0.18), w=1.8)
    footer(layer, "Red sectors are under active subjugation; the Rim falls inward, system by system.")


# --------------------------------------------------------------------------- #
# 15 — Order of battle (quadrants)                                             #
# --------------------------------------------------------------------------- #

def order_of_battle(b):
    layer = chrome(b, "III · Operations", "Four fleet groups")
    quads = grid([MX, 196, W - 2 * MX, 420], cols=2, count=4, gap=20)
    groups = [
        ("DEATH SQUADRON", "red", "Vader's flag. The Executor and her escorts hunt the rebellion directly."),
        ("CORE PICKET", "steelb", "Holds the throneworld approaches; never deploys beyond the Colonies."),
        ("RIM ENFORCEMENT", "steelb", "Disperses to a hundred systems; one destroyer to one province."),
        ("RESERVE SLIPS", "steel", "Hulls fitting out at Kuat; the line that replaces every loss."),
    ]
    for qb, (name, col, body) in zip(quads, groups):
        x, y, bw, bh = qb
        panel(layer, qb, color=col, fill="void2", w=1.5)
        layer.rect([x, y, 7, bh], fill=col)
        hexagon(layer, x + bw - 64, y + 58, 28, color=col, fill=a(col, 0.1), w=2)
        layer.text([x + 32, y + 38, bw - 150, 28], name,
                   style={"class": "h2", "color": col, "font_size": 23})
        layer.text([x + 32, y + 84, bw - 120, 90], body, style="body")
        layer.text([x + 32, y + bh - 38, 260, 18], "READINESS · CONDITION I", style="tag")


# --------------------------------------------------------------------------- #
# 16 — Force projection (bar chart)                                            #
# --------------------------------------------------------------------------- #

def projection(b):
    layer = chrome(b, "III · Operations", "Garrison by sector")
    layer.text([MX, 196, 360, 160],
               "Standing destroyer strength assigned to each sector command at the "
               "close of the fiscal cycle.", style="lead")
    for i, (lbl, val, col) in enumerate([("PEAK", "94", "red"),
                                         ("MEAN", "61", "white"),
                                         ("FLOOR", "22", "steelb")]):
        y = 372 + i * 80
        vline(layer, MX, y, y + 56, col, 3)
        layer.text([MX + 18, y - 4, 280, 40], val,
                   style={"class": "stat", "color": col, "font_size": 40})
        layer.text([MX + 18, y + 44, 280, 18], f"{lbl} · DESTROYERS", style="tag")

    pbox = [524, 196, W - 524 - MX, 420]
    layer.rect(pbox, fill="void2")
    corner_ticks(layer, pbox, color="steel", ln=18, w=1.4)
    chart = Chart(Frame(domain=(0, 0, 6, 100),
                        box=(pbox[0] + 58, pbox[1] + 40, pbox[2] - 92, pbox[3] - 100)))
    bars = [("CORE", 94), ("COLONIES", 78), ("MID RIM", 61), ("OUTER", 40),
            ("EXPANSE", 30), ("WILD", 22)]
    chart.axes(x_ticks=[], y_ticks=[0, 25, 50, 75, 100],
               y_format=lambda v: f"{int(v)}", grid=True,
               axis_color=STEEL, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    cols = [RED, REDB, RED, STEELB, STEELB, STEEL]
    for i, ((name, val), col) in enumerate(zip(bars, cols)):
        chart.bars([(i + 0.5, val)], width=56, fill=col, radius=0)
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    for i, (name, val) in enumerate(bars):
        p = fr.point(i + 0.5, 0)
        layer.text([p.x - 50, pbox[1] + pbox[3] - 50, 100, 16], name,
                   style={"class": "tag", "align": "center"})
    footer(layer, "Destroyers per sector. The Core is over-garrisoned by design; the Rim is held thin.")


# --------------------------------------------------------------------------- #
# 17 — Readiness (gauges)                                                      #
# --------------------------------------------------------------------------- #

def readiness(b):
    layer = chrome(b, "III · Operations", "Fleet readiness board")
    bars = [
        ("HULL AVAILABILITY", 0.88, "red"),
        ("CREW AT STATION", 0.94, "red"),
        ("REBEL CONTAINMENT", 0.41, "steelb"),
        ("SUPPLY IN DEPOT", 0.73, "red"),
        ("INTELLIGENCE PENETRATION", 0.58, "red"),
    ]
    track_x, track_w = 510, 600
    for i, (name, frac, col) in enumerate(bars):
        y = 224 + i * 78
        layer.text([MX, y - 2, 400, 22], name, style="mono")
        layer.rect([track_x, y, track_w, 18], fill="void2", radius=0, **stroke(1.2, "steel"))
        layer.rect([track_x, y, max(18, track_w * frac), 18], fill=col, radius=0)
        layer.text([track_x + track_w + 16, y - 4, 120, 26], f"{int(frac*100)}%",
                   style={"class": "stat", "color": col, "font_size": 24})
        for t in range(1, 10):
            tx = track_x + track_w * t / 10
            vline(layer, tx, y, y + 18, "void", 1)
    footer(layer, "Rebel containment is the one metric below standard; every other board reports green.")


# --------------------------------------------------------------------------- #
# 18 — Campaign timeline                                                       #
# --------------------------------------------------------------------------- #

def timeline(b):
    layer = chrome(b, "III · Operations", "The road to total order")
    spine_y = 404
    hline(layer, MX, W - MX, spine_y, "red", 2)
    nodes = row([MX, spine_y - 14, W - 2 * MX, 28], 5)
    beats = [
        ("19 BBY", "DECLARATION", "The Republic ends; the New Order is proclaimed."),
        ("18 BBY", "THE PURGE", "The Jedi are scattered; the old guardians fall."),
        ("14 BBY", "RIM PACIFIED", "Outer systems brought to heel by the line fleet."),
        ("4 BBY", "ALLIANCE FORMS", "Scattered cells declare a single rebellion."),
        ("0 BBY", "THE STATION", "The battle station ends debate — and is then lost."),
    ]
    for i, (nb, (code, head, body)) in enumerate(zip(nodes, beats)):
        cx = nb[0] + nb[2] / 2
        col = "steelb" if i == 3 else "red"
        dot(layer, cx, spine_y, 9, "void")
        hexagon(layer, cx, spine_y, 11, color=col, w=2.2)
        dot(layer, cx, spine_y, 3, col)
        above = i % 2 == 0
        ty = spine_y - 150 if above else spine_y + 42
        layer.text([cx - 96, ty, 192, 18], code,
                   style={"class": "kicker", "color": col, "align": "center"})
        layer.text([cx - 96, ty + 24, 192, 24], head,
                   style={"class": "h2", "align": "center", "font_size": 17})
        layer.text([cx - 96, ty + 54, 192, 72], body,
                   style={"class": "body", "align": "center", "font_size": 13})
    footer(layer, "Dates count down to the Battle of Yavin; the line that ends the Republic also writes the rebellion.")


# --------------------------------------------------------------------------- #
# 19 — The directive (vertical phases)                                         #
# --------------------------------------------------------------------------- #

def directive(b):
    layer = chrome(b, "III · Operations", "The standing directive")
    layer.text([MX, 196, 360, 240],
               "Four phases bring any rebellious sector back to order. Each opens only "
               "when the Bureau certifies the one before it complete.", style="lead")
    phases = [
        ("PHASE I", "ISOLATE", "Blockade the system; cut the holonet and the trade lanes.", "red"),
        ("PHASE II", "OCCUPY", "Land the garrison; install a Moff and a curfew.", "red"),
        ("PHASE III", "PACIFY", "Hunt the cells; make examples until informers come forward.", "redb"),
        ("PHASE IV", "NORMALISE", "Reopen the lanes under Imperial license; tax the loyal.", "steelb"),
    ]
    bx, bw = 512, W - 512 - MX
    vline(layer, bx + 18, 208, 208 + len(phases) * 100 - 36, "steel", 2)
    for i, (ph, head, body, col) in enumerate(phases):
        y = 208 + i * 100
        dot(layer, bx + 18, y + 20, 11, "void")
        hexagon(layer, bx + 18, y + 20, 12, color=col, w=2.4)
        dot(layer, bx + 18, y + 20, 3, col)
        layer.text([bx + 56, y, 130, 18], ph, style={"class": "kicker", "color": col})
        layer.text([bx + 56, y + 22, bw - 60, 24], head,
                   style={"class": "h2", "color": "white", "font_size": 21})
        layer.text([bx + 56, y + 52, bw - 60, 42], body, style="body")
    footer(layer, "The directive is absolute; a failed phase is repeated with greater force, never abandoned.")


# --------------------------------------------------------------------------- #
# 20 — Closing                                                                  #
# --------------------------------------------------------------------------- #

def closing(b):
    global _page
    _page += 1
    layer = new_page(b, "close")
    layer.rect([0, 0, W, H], fill="void")
    square_grid(layer, [0, 0, W, H], step=64, color="ghost", w=1.0)
    cog(layer, 1010, 360, 150, color="redd", teeth=16)
    layer.text([MX, 168, 800, 22], "END OF BRIEFING", style="kicker")
    layer.text([MX, 210, 900, 140], "ORDER\nWILL HOLD.", style="h1")
    layer.text([MX, 392, 660, 28],
               "The doctrine is one program; brief it, drill it, enforce it without exception.",
               style="lead")
    chip = [MX, 452, 320, 56]
    layer.rect(chip, fill="red", radius=0)
    layer.text([chip[0], chip[1] + 18, chip[2], 22], "uv run · imperial_doctrine", style="chip")
    corner_ticks(layer, [40, 40, W - 80, H - 80], color="steel", ln=34, w=1.4)
    layer.text([MX, 600, 900, 20],
               "FRAMEGRAPH PYTHON SDK · 20 PLATES · FLAT VECTOR · CLASSIFIED ISB",
               style="tag")
    layer.text([W - MX - 200, 600, 200, 18], "PLATE 20 / 20", style="pnum")


# --------------------------------------------------------------------------- #
# Assembly                                                                      #
# --------------------------------------------------------------------------- #

def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Imperial Doctrine", profile="deck", lang="en")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)

    cover(b)                                                          # 01
    contents(b)                                                       # 02
    divider(b, "div1", "I", "The Order", "Doctrine, command and the unbroken chain.")  # 03
    creed(b)                                                          # 04
    hierarchy(b)                                                      # 05
    pillars(b)                                                        # 06
    divider(b, "div2", "II", "The Fleet", "The capital line, the station, and force.")  # 07
    roster(b)                                                         # 08
    schematic(b)                                                      # 09
    big_number(b)                                                     # 10
    comparison(b)                                                     # 11
    battle_station(b)                                                 # 12
    divider(b, "div3", "III", "Operations", "Deployment, readiness and the campaign.")  # 13
    deployment(b)                                                     # 14
    order_of_battle(b)                                                # 15
    projection(b)                                                     # 16
    readiness(b)                                                      # 17
    timeline(b)                                                       # 18
    directive(b)                                                      # 19
    closing(b)                                                        # 20
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="rasterise pages to out/empire/")
    args = ap.parse_args()

    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} slides — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in report.issues[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    out = os.path.join(ROOT, "tests", "fixtures", "imperial-doctrine-deck.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")

    if args.render:
        os.system(f"cd {ROOT} && python3 tooling/render_fixtures.py "
                  f"tests/fixtures/imperial-doctrine-deck.fg.yaml --out out/empire")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
