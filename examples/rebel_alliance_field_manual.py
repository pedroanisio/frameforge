#!/usr/bin/env python3
"""ALLIANCE FIELD MANUAL — a 20-slide Rebel Alliance briefing.

The companion piece to the cold "Imperial Doctrine" deck, authored from the same
FrameGraph Python SDK but built on the opposite visual identity. Where the Empire
is gunmetal, condensed, hard-cornered and symmetric, the Rebellion is warm and
hand-built: a brown-black field, rebel-orange and Alliance-blue accents, a humanist
serif for headings, rounded corners, soft glows and an asymmetric, annotation-heavy
layout language. The recurring emblem is the starbird crest.

The pair shares the SDK but almost no cosmetics, so the two decks read as range
rather than one template reskinned.

Run from the repository root::

    uv run python examples/rebel_alliance_field_manual.py            # build + validate + write YAML
    uv run python examples/rebel_alliance_field_manual.py --render   # also rasterise to out/rebels/
"""
from __future__ import annotations

import argparse
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
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
MX = 78                                  # content margin
R = 9                                    # the Rebellion's soft corner radius

BASE = "#15100b"        # warm brown-black — the Alliance's negative space
BASE2 = "#1d160d"       # lifted panel base
PANEL = "#241a10"       # card fill
PANEL2 = "#2c2114"      # alt card fill
GRIDC = "#2a1d11"       # faint warm grid
ORANGE = "#ee5a24"      # rebel orange / starbird — primary
AMBER = "#f2a73b"       # amber / energy
GOLD = "#f4c95d"        # bright highlight
BLUE = "#3fa7d6"        # Alliance blue — secondary
GREEN = "#5fb87a"       # field-green ops marker (rare)
RUST = "#b8431c"        # dim rust
CREAM = "#f7ede0"       # headline cream
INK = "#d8c7b2"         # warm body text
MUTE = "#8a7666"        # captions
SAND = "#c9b89f"        # mid sand

SERIF = ["Bitstream Charter", "Georgia", "serif"]              # humanist headers
SANS = ["DejaVu Sans", "Verdana", "sans-serif"]               # body
MONO = ["DejaVu Sans Mono", "Consolas", "monospace"]          # stencilled tags

TOTAL = 20
_page = 0

COLORS = {
    "base": BASE, "base2": BASE2, "panel": PANEL, "panel2": PANEL2,
    "gridc": GRIDC, "orange": ORANGE, "amber": AMBER, "gold": GOLD,
    "blue": BLUE, "green": GREEN, "rust": RUST, "cream": CREAM,
    "ink": INK, "mute": MUTE, "sand": SAND, "ghost": "#1f1810",
}


def hexof(c: str) -> str:
    return COLORS.get(c, c)


def a(color: str, alpha: float) -> str:
    """Translucent paint as portable rgba() (cairosvg drops #rrggbbaa alpha)."""
    return rgba(hexof(color), alpha)


STYLES = {
    # stencilled mono field-tags
    "kicker": dict(font_family=MONO, font_size=13, font_weight=700, color="orange",
                   text_transform="uppercase", letter_spacing=3),
    "kickerB": dict(font_family=MONO, font_size=13, font_weight=700, color="blue",
                    text_transform="uppercase", letter_spacing=3),
    "tag": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                text_transform="uppercase", letter_spacing=2),
    "tagC": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=3, align="center"),
    "tagR": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=2, align="right"),
    "pnum": dict(font_family=MONO, font_size=11, font_weight=700, color="sand",
                 letter_spacing=1, align="right"),
    # serif headings — humanist, hand-printed feel
    "h1": dict(font_family=SERIF, font_size=60, font_weight=700, color="cream",
               letter_spacing=0, line_height=1.02),
    "title": dict(font_family=SERIF, font_size=34, font_weight=700, color="cream",
                  letter_spacing=0, line_height=1.08),
    "h2": dict(font_family=SERIF, font_size=24, font_weight=700, color="cream",
               line_height=1.14),
    "h2o": dict(font_family=SERIF, font_size=23, font_weight=700, color="orange",
                line_height=1.16),
    "big": dict(font_family=SERIF, font_size=190, font_weight=700, color="orange",
                letter_spacing=-2, line_height=0.9),
    "idx": dict(font_family=SERIF, font_size=168, font_weight=700, color="ghost",
                line_height=0.9),
    # body
    "lead": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                 line_height=1.52),
    "leadC": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                  line_height=1.52, align="center"),
    "body": dict(font_family=SANS, font_size=14.5, font_weight=400, color="ink",
                 line_height=1.52),
    "bodyM": dict(font_family=SANS, font_size=13, font_weight=400, color="mute",
                  line_height=1.48),
    "mono": dict(font_family=MONO, font_size=13, font_weight=400, color="ink",
                 line_height=1.45),
    "monoO": dict(font_family=MONO, font_size=12.5, font_weight=700, color="orange",
                  line_height=1.4, letter_spacing=1),
    "stat": dict(font_family=SERIF, font_size=46, font_weight=700, color="orange",
                 line_height=1.0),
    "statB": dict(font_family=SERIF, font_size=46, font_weight=700, color="blue",
                  line_height=1.0),
    "num": dict(font_family=MONO, font_size=18, font_weight=700, color="orange",
                align="center", line_height=1.0),
    "chip": dict(font_family=MONO, font_size=13, font_weight=700, color="base",
                 align="center", letter_spacing=2, text_transform="uppercase"),
    "creed": dict(font_family=SERIF, font_size=40, font_weight=700, color="cream",
                  line_height=1.22, align="center"),
}


# --------------------------------------------------------------------------- #
# Rebel drawing vocabulary (warm, rounded, hand-built)                         #
# --------------------------------------------------------------------------- #

def _wrap_text(layer):
    raw_text = layer.text  # noqa: F841

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


def stroke(w, color=ORANGE, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": w, **extra}}


def hline(layer, x0, x1, y, color=MUTE, w=1.0, **extra):
    layer.line([x0, y], [x1, y], **stroke(w, color, **extra))


def vline(layer, x, y0, y1, color=MUTE, w=1.0, **extra):
    layer.line([x, y0], [x, y1], **stroke(w, color, **extra))


def dot(layer, cx, cy, r, fill, **extra):
    layer.ellipse([cx, cy], r, r, fill=fill, **extra)


def ring(layer, cx, cy, r, color=ORANGE, w=2.0, glow=None, **extra):
    fields = stroke(w, color, **extra)
    if glow is not None:
        fields["glow"] = glow
    layer.ellipse([cx, cy], r, r, fill="none", **fields)


def dotgrid(layer, box, step=42, color=GRIDC, r=1.2):
    """A soft dot-grid (rebel field-notebook texture) — ellipses, containment-exempt."""
    x, y, bw, bh = box
    gy = y
    while gy <= y + bh + 0.5:
        gx = x
        while gx <= x + bw + 0.5:
            dot(layer, gx, gy, r, color)
            gx += step
        gy += step


def card(layer, box, *, color=ORANGE, fill="panel", w=1.6, fill_alpha=None,
         radius=R, glow_blur=0):
    """A soft rounded Rebel card."""
    f = a(color, fill_alpha) if fill_alpha is not None else fill
    fields = dict(fill=f, radius=radius, **stroke(w, color))
    if glow_blur:
        fields["glow"] = {"blur": glow_blur, "color": hexof(color), "opacity": 0.45}
    layer.rect(box, **fields)


def tab(layer, box, text, color=ORANGE, tstyle="chip"):
    """A rounded stencil tab (the Rebellion stamps everything)."""
    layer.rect(box, fill=color, radius=R)
    layer.text([box[0], box[1] + box[3] / 2 - 9, box[2], 18], text, style=tstyle)


def starbird(layer, cx, cy, s, *, color=ORANGE, ring_col=None):
    """The Alliance starbird crest: a phoenix rising inside a broken ring."""
    if ring_col:
        # broken outer ring (two arcs)
        ring(layer, cx, cy, s * 1.25, ring_col, 2.4)
        # gaps drawn by overpainting with base wedges (kept simple: side notches)
        layer.line([cx - s * 1.25, cy], [cx - s * 1.45, cy], **stroke(4.0, "base"))
        layer.line([cx + s * 1.25, cy], [cx + s * 1.45, cy], **stroke(4.0, "base"))
    # central rising body + head
    layer.polygon([[cx, cy - s], [cx + s * 0.18, cy + s * 0.5],
                   [cx, cy + s * 0.8], [cx - s * 0.18, cy + s * 0.5]],
                  fill=a(color, 0.9), **stroke(1.4, color))
    # swept wings (upward arcs)
    for sgn in (-1, 1):
        layer.polyline([[cx, cy + s * 0.1],
                        [cx + sgn * s * 0.55, cy - s * 0.15],
                        [cx + sgn * s * 0.85, cy - s * 0.7],
                        [cx + sgn * s * 0.5, cy - s * 0.45]],
                       **stroke(3.4, color, stroke_linecap="round", stroke_linejoin="round"))
    dot(layer, cx, cy - s * 0.95, s * 0.12, color)


def chevron(layer, cx, cy, size, color=ORANGE, w=2.6, down=False):
    s = -1 if down else 1
    layer.polyline([[cx - size, cy + s * size * 0.6], [cx, cy - s * size * 0.6],
                    [cx + size, cy + s * size * 0.6]],
                   **stroke(w, color, stroke_linecap="round"))


def trace(layer, pts, color=ORANGE, w=2.0, node_r=4.0, node=True):
    layer.polyline(pts, **stroke(w, color, stroke_linecap="round", stroke_linejoin="round"))
    if node:
        dot(layer, *pts[0], node_r, color)
        dot(layer, *pts[-1], node_r, color)


def chrome(b, kicker, title, *, kstyle="kicker", accent="orange"):
    """Standard Rebel content frame: warm bg, dot texture, kicker, title, footer."""
    global _page
    _page += 1
    n = _page
    layer = new_page(b, f"p{n:02d}")
    layer.rect([0, 0, W, H], fill="base")
    dotgrid(layer, [0, 0, W, H], step=46, color="ghost", r=1.2)
    # small starbird stamp by the kicker
    starbird(layer, MX + 14, 70, 16, color=accent)
    layer.text([MX + 44, 50, W - 2 * MX - 44, 22], kicker, style=kstyle)
    layer.text([MX + 44, 78, W - 2 * MX - 44, 56], title, style="title")
    layer.rect([MX + 44, 138, 84, 5], fill=accent, radius=3)
    hline(layer, MX, W - MX, 686, "gridc", 1.4)
    layer.text([W - MX - 220, 694, 220, 18], f"REC · {n:02d}/{TOTAL}", style="pnum")
    layer.text([MX, 694, 560, 18], "ALLIANCE FIELD MANUAL · EYES ONLY · MANY BOTHANS",
               style="tag")
    return layer


def footer(layer, text):
    layer.text([MX, 660, W - 2 * MX, 18], text, style="bodyM")


# --------------------------------------------------------------------------- #
# 01 — Cover                                                                    #
# --------------------------------------------------------------------------- #

def cover(b):
    global _page
    _page += 1
    layer = new_page(b, "cover")
    layer.rect([0, 0, W, H], fill="base")
    dotgrid(layer, [0, 0, W, H], step=44, color="ghost", r=1.3)
    # big glowing starbird crest, right
    starbird(layer, 1012, 350, 150, color="orange", ring_col="amber")
    dot(layer, 1012, 350, 196, a("orange", 0.0))  # spacer (decorative-free, no box)
    layer.text([MX, 170, 760, 26], "REBEL ALLIANCE · INTELLIGENCE DIVISION", style="kicker")
    layer.text([MX, 214, 820, 150], "Alliance\nField Manual", style="h1")
    layer.rect([MX, 392, 150, 5], fill="orange", radius=3)
    layer.text([MX, 418, 640, 28],
               "Rebellions are built on hope — this is how we keep ours alive.",
               style="lead")
    layer.text([MX, 600, 820, 20],
               "20 PLATES · AUTHORED THROUGH THE FRAMEGRAPH PYTHON SDK · FLAT VECTOR",
               style="tag")
    layer.text([W - MX - 220, 600, 220, 18], "REC 01 / 20", style="pnum")


# --------------------------------------------------------------------------- #
# 02 — Contents                                                                 #
# --------------------------------------------------------------------------- #

def contents(b):
    layer = chrome(b, "Briefing index — three passes over the cause", "Contents")
    items = [
        ("01", "The Cause", "Why we fight, how cells survive, and the creed that holds.", "orange"),
        ("02", "The Fleet", "Starfighters, the squadrons, and what we fly against a wall.", "blue"),
        ("03", "Operations", "Supply lines, the mission profile, and the plan ahead.", "amber"),
    ]
    rows = column([MX, 206, W - 2 * MX, 3 * 138], 3, gap=14)
    for (n, head, sub, col), rb in zip(items, rows):
        x, y, bw, bh = rb
        card(layer, [x, y, bw, bh - 14], color=col, fill="base2", w=1.5)
        starbird(layer, x + 60, y + (bh - 14) / 2, 26, color=col)
        layer.text([x + 110, y + 24, 60, 30], n,
                   style={"class": "num", "color": col, "font_size": 22, "align": "left"})
        layer.text([x + 160, y + 24, bw - 200, 30], head, style="h2")
        layer.text([x + 160, y + 64, bw - 220, 30], sub, style="body")
        tab(layer, [x + bw - 132, y + 28, 100, 32], f"PASS {n}", color=col)


# --------------------------------------------------------------------------- #
# Section dividers                                                              #
# --------------------------------------------------------------------------- #

def divider(b, pid, secno, title, subtitle, *, accent="orange"):
    global _page
    _page += 1
    layer = new_page(b, pid)
    layer.rect([0, 0, W, H], fill="base")
    dotgrid(layer, [0, 0, W, H], step=50, color="ghost", r=1.3)
    layer.text([MX - 4, 152, 520, 280], secno, style="idx")
    kstyle = "kickerB" if accent == "blue" else "kicker"
    layer.text([520, 250, 360, 22], f"BRIEFING {secno}", style=kstyle)
    layer.text([520, 282, 700, 120], title, style="h1")
    layer.rect([522, 396, 130, 5], fill=accent, radius=3)
    layer.text([522, 420, 660, 80], subtitle, style="lead")
    starbird(layer, 1126, 156, 54, color=accent, ring_col="amber")
    chevron(layer, 1150, 600, 15, color=accent)
    chevron(layer, 1150, 628, 15, color="sand")
    layer.text([W - MX - 220, 694, 220, 18], f"REC · {_page:02d}/{TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 04 — The creed (centered)                                                     #
# --------------------------------------------------------------------------- #

def creed(b):
    layer = chrome(b, "The cause — what we hold to", "Rebellions are built on hope")
    layer.text([0, 236, W, 22], "// FIELD CREED", style="tagC")
    layer.text([180, 278, W - 360, 150],
               "“Hope is like the sun. If you only\nbelieve it when you can see it,\n"
               "you'll never make it through the night.”", style="creed")
    layer.rect([W / 2 - 70, 506, 140, 5], fill="orange", radius=3)
    layer.text([0, 536, W, 22], "— GENERAL LEIA ORGANA", style="tagC")
    starbird(layer, 240, 360, 30, color="amber")
    starbird(layer, W - 240, 360, 30, color="blue")


# --------------------------------------------------------------------------- #
# 05 — Cell network (node graph)                                               #
# --------------------------------------------------------------------------- #

def network(b):
    layer = chrome(b, "01 · The Cause", "How the Alliance is built", accent="orange")
    cx, cy = 470, 426
    nodes = {
        "hq": (cx, cy, "orange", 32),
        "a": (cx - 230, cy - 120, "blue", 22),
        "b": (cx + 210, cy - 140, "blue", 22),
        "c": (cx - 250, cy + 110, "amber", 22),
        "d": (cx + 250, cy + 96, "amber", 22),
        "e": (cx - 20, cy - 210, "blue", 18),
        "f": (cx + 60, cy + 198, "amber", 18),
    }
    edges = [("hq", k) for k in nodes if k != "hq"] + [("a", "e"), ("b", "e"),
             ("c", "f"), ("d", "f")]
    for u, v in edges:
        x1, y1, _, _ = nodes[u]
        x2, y2, _, _ = nodes[v]
        layer.line([x1, y1], [x2, y2], **stroke(1.4, "rust", stroke_dasharray=[5, 4]))
    for k, (x, y, col, r) in nodes.items():
        dot(layer, x, y, r, a(col, 0.14))
        ring(layer, x, y, r, col, 2.2)
        dot(layer, x, y, 4, col)
    legend = [824, 232, W - 824 - MX, 384]
    card(layer, legend, color="amber", fill="base2", w=1.4)
    layer.text([legend[0] + 24, legend[1] + 22, legend[2] - 48, 26], "Read the cell map",
               style="h2o")
    rows = [
        ("orange", "Command cell — Alliance High Command. Knows the whole graph."),
        ("blue", "Active cell — a crew and a ship. Knows only its neighbours."),
        ("amber", "Sleeper cell — dormant until a courier wakes it."),
    ]
    for i, (col, txt) in enumerate(rows):
        ly = legend[1] + 72 + i * 80
        dot(layer, legend[0] + 40, ly + 12, 12, a(col, 0.2))
        ring(layer, legend[0] + 40, ly + 12, 12, col, 2.2)
        layer.text([legend[0] + 70, ly - 2, legend[2] - 100, 60], txt, style="body")
    footer(layer, "No cell knows the whole. Cut one loose and the Rebellion still breathes — that is the design.")


# --------------------------------------------------------------------------- #
# 06 — Why we fight (thirds)                                                    #
# --------------------------------------------------------------------------- #

def pillars(b):
    layer = chrome(b, "01 · The Cause", "Three reasons we hold the line", accent="orange")
    cols = row([MX, 200, W - 2 * MX, 412], 3, gap=26)
    data = [
        ("FREEDOM", "blue", "Every world the Empire garrisons once governed itself. "
         "We fight to give that choice back, system by system."),
        ("MEMORY", "orange", "Alderaan had no fleet and no fortress. We carry it so the "
         "next world they threaten is not faced alone."),
        ("HOPE", "amber", "The Empire rules by fear, which is expensive. Hope is cheap, "
         "it spreads on its own, and it cannot be blockaded."),
    ]
    for cb, (head, col, body) in zip(cols, data):
        x, y, bw, bh = cb
        card(layer, cb, color=col, fill="base2", w=1.5)
        starbird(layer, x + 44, y + 56, 26, color=col)
        layer.rect([x + 26, y + 100, 56, 5], fill=col, radius=3)
        layer.text([x + 26, y + 122, bw - 52, 30], head,
                   style={"class": "h2", "color": col})
        layer.text([x + 26, y + 168, bw - 52, 200], body, style="body")
        chevron(layer, x + bw - 38, y + bh - 36, 11, color="sand")


# --------------------------------------------------------------------------- #
# 08 — Starfighter roster (left rail)                                          #
# --------------------------------------------------------------------------- #

def roster(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="base")
    # full-bleed left rail: rounded only on the right, so it runs off three edges
    layer.rect([-R, -R, 432 + R, H + 2 * R], fill="base2", radius=R,
               decorative=True, **stroke(2.0, "blue"))
    vline(layer, 432, 0, H, "blue", 2.0)
    dotgrid(layer, [0, 0, 432, H], step=46, color="gridc", r=1.2)
    starbird(layer, MX + 14, 110, 16, color="blue")
    layer.text([MX + 44, 92, 320, 22], "02 · THE FLEET", style="kickerB")
    layer.text([MX, 132, 340, 140], "What we fly\nto war", style="h1")
    layer.rect([MX, 268, 120, 5], fill="blue", radius=3)
    layer.text([MX, 296, 300, 200],
               "Five airframes carry the Alliance. Most were never built for war — we "
               "made them fight anyway.", style="lead")
    starbird(layer, MX + 70, 566, 44, color="orange")
    layer.text([W - MX - 220, 694, 220, 18], f"REC · {_page:02d}/{TOTAL}", style="pnum")

    cards = column([474, 78, W - 474 - MX, 568], 5, gap=14)
    ships = [
        ("T-65 X-WING", "all-role fighter", "S-foils", "orange"),
        ("BTL Y-WING", "bomber · workhorse", "ion payload", "amber"),
        ("RZ-1 A-WING", "interceptor · fast", "thin armour", "blue"),
        ("CR90 CORVETTE", "blockade runner", "courier hull", "blue"),
        ("GR-75 TRANSPORT", "supply lifter", "soft, vital", "green"),
    ]
    for cb, (name, role, note, col) in zip(cards, ships):
        x, y, bw, bh = cb
        card(layer, cb, color=col, fill="base2", w=1.4)
        # simple fighter glyph — a forward dart
        layer.polygon([[x + 32, y + bh / 2], [x + 84, y + bh / 2 - 16],
                       [x + 72, y + bh / 2], [x + 84, y + bh / 2 + 16]],
                      fill=a(col, 0.18), **stroke(1.6, col))
        layer.text([x + 110, y + 16, bw - 250, 26], name,
                   style={"class": "h2", "color": "cream", "font_size": 21})
        layer.text([x + 110, y + 50, bw - 250, 24], role.upper(), style="tag")
        tab(layer, [x + bw - 168, y + bh / 2 - 17, 144, 34], note.upper(),
            color=col, tstyle={"class": "chip", "font_size": 11})


# --------------------------------------------------------------------------- #
# 09 — X-wing schematic (radial labelled)                                      #
# --------------------------------------------------------------------------- #

def schematic(b):
    layer = chrome(b, "02 · The Fleet", "T-65 X-wing · field schematic", accent="blue")
    cx, cy = 430, 412
    # fuselage
    layer.polygon([[cx - 150, cy - 14], [cx + 150, cy - 8], [cx + 168, cy],
                   [cx + 150, cy + 8], [cx - 150, cy + 14]],
                  fill=a("blue", 0.12), **stroke(2.0, "blue"))
    # nose + cockpit
    dot(layer, cx + 110, cy, 12, a("amber", 0.3))
    ring(layer, cx + 110, cy, 12, "amber", 1.8)
    # four S-foils, open in attack position
    for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        bx, by = cx - 70, cy
        ex, ey = cx - 150, cy + sy * 96
        layer.line([bx, by], [ex, ey], **stroke(3.0, "blue", stroke_linecap="round"))
        # cannon tip
        dot(layer, ex, ey, 5, "orange")
        layer.line([ex, ey], [ex + 26, ey + sy * 4], **stroke(2.2, "orange",
                   stroke_linecap="round"))
    labels = [
        ([cx + 168, cy], "NOSE LASER", "Targeting computer feeds all four cannons."),
        ([cx + 110, cy], "COCKPIT", "One pilot, one astromech — no room for fear."),
        ([cx - 150, cy - 96], "S-FOIL", "Wings split to spread the guns for the run."),
        ([cx - 150, cy + 96], "CANNON", "Four KX9 lasers; fire-link for the trench."),
    ]
    lx = 832
    for i, (pt, head, body) in enumerate(labels):
        ly = 218 + i * 100
        trace(layer, [[pt[0], pt[1]], [lx - 34, pt[1]], [lx - 34, ly + 12], [lx, ly + 12]],
              color="blue", w=1.4, node_r=3.5)
        layer.text([lx + 12, ly, 360, 22], head, style="h2o")
        layer.text([lx + 12, ly + 28, 360, 50], body, style="body")
    footer(layer, "Astromech in the socket, S-foils locked open — the X-wing was made for exactly one run.")


# --------------------------------------------------------------------------- #
# 10 — Squadrons (bento, unequal tiles)                                        #
# --------------------------------------------------------------------------- #

def squadrons(b):
    layer = chrome(b, "02 · The Fleet", "The squadrons", accent="orange")
    big = [MX, 196, 560, 420]
    card(layer, big, color="orange", fill="base2", w=1.8)
    layer.text([MX + 30, 226, 500, 26], "RED SQUADRON", style="h2o")
    layer.text([MX + 30, 266, 500, 90],
               "Twelve X-wings off the carrier. They flew the trench at Yavin and pulled "
               "the impossible shot — the run every recruit now trains against.",
               style="body")
    # twelve ship pips
    for i, gb in enumerate(grid([MX + 30, 392, 480, 150], cols=6, count=12, gap=12)):
        col = "orange" if i in (0, 4) else ("amber" if i == 8 else "sand")
        layer.polygon([[gb[0] + 4, gb[1] + gb[3] / 2], [gb[0] + 44, gb[1] + gb[3] / 2 - 12],
                       [gb[0] + 36, gb[1] + gb[3] / 2], [gb[0] + 44, gb[1] + gb[3] / 2 + 12]],
                      fill=a(col, 0.2), **stroke(1.4, col))
        layer.text([gb[0], gb[1] + gb[3] - 16, gb[2], 14], f"R{i+1}",
                   style={"class": "tag", "align": "left", "font_size": 9})

    t2 = [664, 196, 280, 200]
    card(layer, t2, color="amber", fill="base2", w=1.6)
    layer.text([t2[0] + 22, t2[1] + 22, t2[2] - 44, 24], "GOLD SQUADRON",
               style={"class": "h2", "font_size": 20})
    layer.text([t2[0] + 22, t2[1] + 58, t2[2] - 44, 110],
               "Y-wing bombers. Slow, ugly, and the reason the shield generators fall.",
               style="body")

    t3 = [960, 196, W - 960 - MX, 200]
    card(layer, t3, color="blue", fill="base2", w=1.6)
    layer.text([t3[0] + 22, t3[1] + 22, t3[2] - 44, 24], "ROGUE SQUADRON",
               style={"class": "h2", "font_size": 20})
    layer.text([t3[0] + 22, t3[1] + 58, t3[2] - 44, 120],
               "The ones sent where the line cannot hold. Hand-picked; deniable.",
               style="body")

    t4 = [664, 416, W - 664 - MX, 200]
    card(layer, t4, color="green", fill="base2", w=1.6)
    layer.text([t4[0] + 24, t4[1] + 22, 320, 24], "GREEN & BLUE", style="h2")
    layer.text([t4[0] + 24, t4[1] + 58, 360, 110],
               "Reserve and escort wings. They get the transports home, which wins more "
               "battles than any ace.", style="body")
    starbird(layer, t4[0] + t4[2] - 90, t4[1] + t4[3] / 2, 48, color="green")


# --------------------------------------------------------------------------- #
# 11 — Starfighter stats (bar chart)                                           #
# --------------------------------------------------------------------------- #

def stats(b):
    layer = chrome(b, "02 · The Fleet", "Airframes, by the numbers", accent="blue")
    layer.text([MX, 196, 360, 170],
               "Relative top speed of the Alliance line, rated against atmosphere — the "
               "A-wing buys the others time.", style="lead")
    for i, (lbl, val, col) in enumerate([("FASTEST", "A-WING", "blue"),
                                         ("HARDEST HIT", "Y-WING", "amber"),
                                         ("BEST ALL-ROUND", "X-WING", "orange")]):
        y = 384 + i * 78
        vline(layer, MX, y, y + 54, col, 3)
        layer.text([MX + 18, y - 4, 320, 30], val,
                   style={"class": "stat", "color": col, "font_size": 30})
        layer.text([MX + 18, y + 40, 320, 18], lbl, style="tag")

    pbox = [524, 196, W - 524 - MX, 420]
    card(layer, pbox, color="gridc", fill="base2", w=1.4)
    chart = Chart(Frame(domain=(0, 0, 5, 100),
                        box=(pbox[0] + 60, pbox[1] + 40, pbox[2] - 96, pbox[3] - 100)))
    bars = [("A-WING", 92), ("X-WING", 74), ("Y-WING", 56),
            ("CORVETTE", 38), ("GR-75", 26)]
    chart.axes(x_ticks=[], y_ticks=[0, 25, 50, 75, 100],
               y_format=lambda v: f"{int(v)}", grid=True,
               axis_color=MUTE, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    cols = [BLUE, ORANGE, AMBER, BLUE, GREEN]
    for i, ((name, val), col) in enumerate(zip(bars, cols)):
        chart.bars([(i + 0.5, val)], width=56, fill=col, radius=4)
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    for i, (name, val) in enumerate(bars):
        p = fr.point(i + 0.5, 0)
        layer.text([p.x - 52, pbox[1] + pbox[3] - 50, 104, 16], name,
                   style={"class": "tag", "align": "center"})
    footer(layer, "Speed rated to 100. We rarely out-gun the Empire — we out-run it and pick the fight.")


# --------------------------------------------------------------------------- #
# 13 — Supply-line map (full-bleed, hand-drawn routes)                         #
# --------------------------------------------------------------------------- #

def supply_map(b):
    layer = chrome(b, "03 · Operations", "Supply lines & safe ports", accent="amber")
    map_box = [MX, 196, W - 2 * MX, 420]
    card(layer, map_box, color="gridc", fill="base2", w=1.4)
    dotgrid(layer, inset(map_box, 8), step=34, color="gridc", r=1.0)
    bases = [
        ("YAVIN 4", MX + 120, 320, "orange", "fwd base"),
        ("HOTH", MX + 360, 250, "blue", "ice cache"),
        ("DANTOOINE", MX + 360, 470, "amber", "abandoned"),
        ("SULLUST", MX + 700, 300, "green", "muster pt"),
        ("MON CALA", MX + 940, 430, "blue", "shipyard"),
        ("OUTPOST X", MX + 980, 250, "amber", "courier"),
    ]
    pos = {n: (x, y, c) for n, x, y, c, s in bases}
    routes = [("YAVIN 4", "HOTH"), ("HOTH", "SULLUST"), ("DANTOOINE", "SULLUST"),
              ("SULLUST", "MON CALA"), ("MON CALA", "OUTPOST X"), ("YAVIN 4", "DANTOOINE")]
    for u, v in routes:
        x1, y1, _ = pos[u]
        x2, y2, _ = pos[v]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 26
        layer.path([["M", x1, y1], ["Q", mx, my, x2, y2]],
                   fill="none", **stroke(1.8, "amber", stroke_dasharray=[7, 5]))
    for name, x, y, col, status in bases:
        starbird(layer, x, y, 16, color=col)
        layer.text([x - 70, y + 22, 140, 16], name,
                   style={"class": "kicker", "color": col, "align": "center", "font_size": 11})
        layer.text([x - 70, y + 40, 140, 14], status.upper(),
                   style={"class": "tag", "align": "center", "color": "mute"})
    footer(layer, "Dashed lanes are the only ones we trust this rotation; a known route is a route the Empire can find.")


# --------------------------------------------------------------------------- #
# 14 — Mission profile (process flow)                                          #
# --------------------------------------------------------------------------- #

def mission(b):
    layer = chrome(b, "03 · Operations", "The mission profile", accent="orange")
    steps = [
        ("01", "INFILTRATE", "Slip in cold on a transport's transponder; no comms.", "blue"),
        ("02", "MARK", "A ground cell paints the target and confirms the window.", "amber"),
        ("03", "STRIKE", "Fighters make one pass on the marked point — only one.", "orange"),
        ("04", "EXFIL", "Scatter on separate vectors; rally beyond the jump line.", "amber"),
        ("05", "VANISH", "Ditch the transponder; the cell goes dark for a month.", "green"),
    ]
    cols = row([MX, 224, W - 2 * MX, 348], 5, gap=18)
    for i, (cb, (n, head, body, col)) in enumerate(zip(cols, steps)):
        x, y, bw, bh = cb
        card(layer, cb, color=col, fill="base2", w=1.5)
        layer.text([x + 18, y + 18, bw - 36, 30], n,
                   style={"class": "num", "color": col, "align": "left", "font_size": 22})
        hline(layer, x + 18, x + bw - 18, y + 56, "gridc", 1)
        starbird(layer, x + bw / 2, y + 118, 22, color=col)
        layer.text([x + 18, y + 166, bw - 36, 24], head,
                   style={"class": "h2", "color": col, "font_size": 17})
        layer.text([x + 18, y + 196, bw - 30, 130], body, style="body")
        if i < 4:
            chevron(layer, x + bw + 9, y + bh / 2, 9, color="sand")
    footer(layer, "One pass, then gone. We do not hold ground we cannot defend — we trade it for the strike.")


# --------------------------------------------------------------------------- #
# 15 — Trench run (attack geometry)                                            #
# --------------------------------------------------------------------------- #

def trench_run(b):
    layer = chrome(b, "03 · Operations", "The trench run", accent="orange")
    layer.text([MX, 196, 380, 200],
               "Stay below the surface guns, hold the line to the exhaust port, and "
               "release on the computer's mark. Speed is the only cover down there.",
               style="lead")
    eqs = [("len ≈ 2 km", "tower to the port"),
           ("port = 2 m", "the only opening"),
           ("window = 1", "one pass, then turn")]
    for i, (eq, note) in enumerate(eqs):
        y = 400 + i * 70
        card(layer, [MX, y, 380, 56], color="amber", fill="base2", w=1.4)
        layer.text([MX + 18, y + 12, 158, 32], eq,
                   style={"class": "monoO", "color": "amber", "font_size": 19})
        layer.text([MX + 190, y + 18, 178, 22], note, style="bodyM")

    pbox = [500, 196, W - 500 - MX, 420]
    card(layer, pbox, color="gridc", fill="base2", w=1.4)
    # the trench: two walls converging to the port
    layer.line([520, 250, ], [pbox[0] + pbox[2] - 60, 320], **stroke(2.0, "blue"))
    layer.line([520, 560], [pbox[0] + pbox[2] - 60, 420], **stroke(2.0, "blue"))
    # surface gun emplacements (ticks off the walls)
    for t in (0.2, 0.4, 0.6, 0.78):
        gx = 520 + (pbox[0] + pbox[2] - 60 - 520) * t
        layer.line([gx, 250 + 70 * t], [gx, 250 + 70 * t - 16], **stroke(1.6, "rust"))
        layer.line([gx, 560 - 140 * t], [gx, 560 - 140 * t + 16], **stroke(1.6, "rust"))
    # the exhaust port
    port = [pbox[0] + pbox[2] - 60, 370]
    ring(layer, port[0], port[1], 16, "orange", 2.4,
         glow={"blur": 12, "color": ORANGE, "opacity": 0.6})
    dot(layer, port[0], port[1], 5, "gold")
    # attack vector — a fighter's approach polyline
    pts = [[540, 470], [700, 430], [860, 400], [1000, 384], port]
    layer.polyline(pts, **stroke(2.8, "orange", stroke_linecap="round"))
    for p in pts[:-1]:
        dot(layer, p[0], p[1], 4, "amber")
    # the lead fighter
    layer.polygon([[pts[-2][0], pts[-2][1] - 9], [pts[-2][0] + 22, pts[-2][1]],
                   [pts[-2][0], pts[-2][1] + 9]], fill=a("orange", 0.4),
                  **stroke(1.6, "orange"))
    layer.text([port[0] - 150, port[1] - 44, 150, 16], "EXHAUST PORT",
               style={"class": "kicker", "align": "right", "font_size": 11})
    footer(layer, "Use the Force, or use the computer — either way the port is two metres and you get one shot.")


# --------------------------------------------------------------------------- #
# 16 — Base readiness (gauges)                                                 #
# --------------------------------------------------------------------------- #

def readiness(b):
    layer = chrome(b, "03 · Operations", "Echo Base readiness", accent="blue")
    bars = [
        ("FIGHTERS FLIGHT-READY", 0.71, "orange"),
        ("ION CANNON CHARGED", 0.86, "blue"),
        ("TRANSPORTS FUELLED", 0.64, "amber"),
        ("SHIELD GENERATOR", 0.92, "blue"),
        ("EVAC PLAN REHEARSED", 0.79, "green"),
    ]
    track_x, track_w = 520, 590
    for i, (name, frac, col) in enumerate(bars):
        y = 224 + i * 78
        layer.text([MX, y - 2, 400, 22], name, style="mono")
        layer.rect([track_x, y, track_w, 18], fill="base2", radius=9, **stroke(1.2, "gridc"))
        layer.rect([track_x, y, max(18, track_w * frac), 18], fill=col, radius=9,
                   glow={"blur": 8, "color": COLORS[col], "opacity": 0.4})
        layer.text([track_x + track_w + 16, y - 4, 120, 26], f"{int(frac*100)}%",
                   style={"class": "stat", "color": col, "font_size": 24})
        for t in range(1, 10):
            tx = track_x + track_w * t / 10
            vline(layer, tx, y, y + 18, "base", 1)
    footer(layer, "The evac plan is rehearsed for a reason — every base is temporary, and the shield buys the transports.")


# --------------------------------------------------------------------------- #
# 17 — Recruitment growth (line chart)                                         #
# --------------------------------------------------------------------------- #

def growth(b):
    layer = chrome(b, "03 · Operations", "Cells lit, cycle over cycle", accent="amber")
    pbox = [MX, 200, W - 2 * MX, 410]
    card(layer, pbox, color="gridc", fill="base2", w=1.4)
    chart = Chart(Frame(domain=(0, 0, 12, 100),
                        box=(pbox[0] + 64, pbox[1] + 36, pbox[2] - 110, pbox[3] - 96)))
    chart.axes(x_ticks=[0, 3, 6, 9, 12], y_ticks=[0, 25, 50, 75, 100],
               x_format=lambda v: f"M{int(v)}", y_format=lambda v: f"{int(v)}", grid=True,
               axis_color=MUTE, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    active = [(t, 14 + 6.2 * t + 6 * math.sin(t / 1.6)) for t in range(0, 13)]
    sleeper = [(t, 8 + 3.0 * t) for t in range(0, 13)]
    chart.line(active, stroke=ORANGE, width=3.0, smooth=True, label="active cells")
    chart.line(sleeper, stroke=BLUE, width=2.6, smooth=True, label="sleeper cells")
    chart.legend(at=(pbox[0] + 64, pbox[1] + pbox[3] - 24))
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    p = fr.point(12, 88)
    dot(layer, p.x, p.y, 5, "gold", glow={"blur": 8, "color": GOLD, "opacity": 0.6})
    layer.text([p.x - 150, p.y - 26, 150, 16], "AFTER YAVIN",
               style={"class": "kicker", "align": "right"})
    footer(layer, "One impossible shot lit more cells than a year of couriers — hope recruits faster than fear.")


# --------------------------------------------------------------------------- #
# 18 — History timeline                                                        #
# --------------------------------------------------------------------------- #

def timeline(b):
    layer = chrome(b, "03 · Operations", "How we got here", accent="orange")
    spine_y = 404
    hline(layer, MX, W - MX, spine_y, "orange", 2)
    nodes = row([MX, spine_y - 14, W - 2 * MX, 28], 5)
    beats = [
        ("2 BBY", "FIRST SPARK", "Scattered cells agree to fight as one Alliance."),
        ("0 BBY", "STOLEN PLANS", "The station's flaw is carried out at terrible cost."),
        ("0 ABY", "YAVIN", "One shot ends the battle station and lights the galaxy."),
        ("3 ABY", "HOTH", "Echo Base falls; the fleet scatters but survives."),
        ("4 ABY", "ENDOR", "The second station and the Emperor fall together."),
    ]
    for i, (nb, (code, head, body)) in enumerate(zip(nodes, beats)):
        cx = nb[0] + nb[2] / 2
        col = "gold" if i == 2 else ("blue" if i == 3 else "orange")
        dot(layer, cx, spine_y, 10, "base")
        starbird(layer, cx, spine_y, 12, color=col)
        above = i % 2 == 0
        ty = spine_y - 150 if above else spine_y + 44
        layer.text([cx - 96, ty, 192, 18], code,
                   style={"class": "kicker", "color": col, "align": "center"})
        layer.text([cx - 96, ty + 24, 192, 24], head,
                   style={"class": "h2", "align": "center", "font_size": 17})
        layer.text([cx - 96, ty + 54, 192, 72], body,
                   style={"class": "body", "align": "center", "font_size": 13})
    footer(layer, "Dates run from the Battle of Yavin; the line we walk bends, scatters, and never quite breaks.")


# --------------------------------------------------------------------------- #
# 19 — The plan ahead (vertical phases)                                        #
# --------------------------------------------------------------------------- #

def plan(b):
    layer = chrome(b, "03 · Operations", "The plan ahead", accent="blue")
    layer.text([MX, 196, 360, 240],
               "Four moves carry the Alliance from raids to a fleet that can meet the "
               "Empire in the open. Each waits on the one before it.", style="lead")
    phases = [
        ("MOVE I", "GATHER", "Light the sleeper cells; muster every hull that can jump.", "orange"),
        ("MOVE II", "SHIELD", "Take Mon Cala's yards; build the capital line we lack.", "blue"),
        ("MOVE III", "STRIKE", "Bait the fleet to a system of our choosing, not theirs.", "amber"),
        ("MOVE IV", "FREE", "Break the second station; let the garrisons fall on their own.", "green"),
    ]
    bx, bw = 512, W - 512 - MX
    vline(layer, bx + 18, 208, 208 + len(phases) * 100 - 36, "gridc", 2)
    for i, (ph, head, body, col) in enumerate(phases):
        y = 208 + i * 100
        dot(layer, bx + 18, y + 20, 12, "base")
        starbird(layer, bx + 18, y + 20, 13, color=col)
        layer.text([bx + 58, y, 130, 18], ph, style={"class": "kicker", "color": col})
        layer.text([bx + 58, y + 22, bw - 60, 24], head,
                   style={"class": "h2", "color": "cream", "font_size": 21})
        layer.text([bx + 58, y + 52, bw - 60, 42], body, style="body")
    footer(layer, "The plan is patient on purpose; a rebellion that survives the night has already won the hard part.")


# --------------------------------------------------------------------------- #
# 20 — Closing                                                                  #
# --------------------------------------------------------------------------- #

def closing(b):
    global _page
    _page += 1
    layer = new_page(b, "close")
    layer.rect([0, 0, W, H], fill="base")
    dotgrid(layer, [0, 0, W, H], step=44, color="ghost", r=1.3)
    starbird(layer, 1012, 350, 150, color="orange", ring_col="amber")
    layer.text([MX, 168, 800, 22], "END OF BRIEFING", style="kicker")
    layer.text([MX, 210, 900, 140], "Stay\nhopeful.", style="h1")
    layer.text([MX, 392, 680, 28],
               "The manual is one program — fork it, hide it, hand it to the next cell.",
               style="lead")
    chip = [MX, 452, 340, 56]
    layer.rect(chip, fill="orange", radius=R)
    layer.text([chip[0], chip[1] + 18, chip[2], 22], "uv run · alliance_field_manual",
               style="chip")
    layer.text([MX, 600, 900, 20],
               "FRAMEGRAPH PYTHON SDK · 20 PLATES · FLAT VECTOR · EYES ONLY",
               style="tag")
    layer.text([W - MX - 220, 600, 220, 18], "REC 20 / 20", style="pnum")


# --------------------------------------------------------------------------- #
# Assembly                                                                      #
# --------------------------------------------------------------------------- #

def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Alliance Field Manual", profile="deck", lang="en")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)

    cover(b)                                                          # 01
    contents(b)                                                       # 02
    divider(b, "div1", "01", "The Cause", "Why we fight, and how a cell survives.")  # 03
    creed(b)                                                          # 04
    network(b)                                                        # 05
    pillars(b)                                                        # 06
    divider(b, "div2", "02", "The Fleet",
            "Starfighters, squadrons, and what we fly.", accent="blue")  # 07
    roster(b)                                                         # 08
    schematic(b)                                                      # 09
    squadrons(b)                                                      # 10
    stats(b)                                                          # 11
    divider(b, "div3", "03", "Operations",
            "Supply, missions, and the plan ahead.", accent="amber")  # 12
    supply_map(b)                                                     # 13
    mission(b)                                                        # 14
    trench_run(b)                                                     # 15
    readiness(b)                                                      # 16
    growth(b)                                                         # 17
    timeline(b)                                                       # 18
    plan(b)                                                           # 19
    closing(b)                                                        # 20
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="rasterise pages to out/rebels/")
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

    out = os.path.join(ROOT, "fixtures", "rebel-alliance-field-manual.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")

    if args.render:
        os.system(f"cd {ROOT} && python3 tooling/render_fixtures.py "
                  f"fixtures/rebel-alliance-field-manual.fg.yaml --out out/rebels")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
