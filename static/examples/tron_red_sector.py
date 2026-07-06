#!/usr/bin/env python3
"""INFERNO // RED SECTOR — a 30-slide deck in the antagonist's register of the
Grid, rendered entirely in flat 2D vector.

Where GRID PROTOCOL is cool and ordered and TRACE is a cold blue schematic, this
deck is the *corrupted* grid: CLU's uprising, told in heat. Identity, shape
language and diagrammation all change again:

  * identity — orange / ember-red / amber on a warm near-black, with cyan reduced
    to a single dying-signal accent (the users, almost gone);
  * shape language — **hexagons, diagonal shards, fracture lattices and hazard
    chevrons** instead of rings, ribbons or orthogonal traces;
  * diagrammation — radial / explosive layouts, hazard-HUD framing and a
    deliberately *broken* grid; tension over order.

Run from the repository root::

    uv run python examples/tron_red_sector.py            # build + validate + write YAML
    uv run python examples/tron_red_sector.py --render   # also rasterise to out/red/
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
    Chart, DocumentBuilder, Frame, column, grid, inset, rgba, row, serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
MX = 72

VOID = "#0a0604"        # warm near-black
PANEL = "#160a06"       # ember panel
PANEL2 = "#1f0e07"
ORANGE = "#ff6a1a"       # primary — CLU light
EMBER = "#ff2d1a"        # hot fault / derez
AMBER = "#ffb02e"        # energy / warning
ORANGED = "#a8451a"      # dim orange hairline
CYAN = "#3aa6b8"         # dying user signal (rare accent)
WHITE = "#fff0e6"
INK = "#d7a98e"          # body text
MUTE = "#8a5c44"         # captions
GRIDC = "#2a1206"        # broken board grid

SANS = ["DejaVu Sans", "Verdana", "sans-serif"]
MONO = ["DejaVu Sans Mono", "Consolas", "monospace"]

TOTAL = 30
_page = 0

COLORS = {
    "void": VOID, "panel": PANEL, "panel2": PANEL2, "orange": ORANGE, "ember": EMBER,
    "amber": AMBER, "oranged": ORANGED, "cyan": CYAN, "white": WHITE, "ink": INK,
    "mute": MUTE, "gridc": GRIDC, "ghost": "#22100a",
}

STYLES = {
    "kicker": dict(font_family=MONO, font_size=13, font_weight=700, color="orange",
                   text_transform="uppercase", letter_spacing=4),
    "kickerE": dict(font_family=MONO, font_size=13, font_weight=700, color="ember",
                    text_transform="uppercase", letter_spacing=4),
    "kickerC": dict(font_family=MONO, font_size=13, font_weight=700, color="cyan",
                    text_transform="uppercase", letter_spacing=4),
    "tag": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                text_transform="uppercase", letter_spacing=3),
    "tagC": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=3, align="center"),
    "pnum": dict(font_family=MONO, font_size=11, font_weight=700, color="oranged",
                 letter_spacing=2, align="right"),
    "h1": dict(font_family=SANS, font_size=58, font_weight=800, color="white",
               letter_spacing=1, line_height=1.0),
    "h1C": dict(font_family=SANS, font_size=54, font_weight=800, color="white",
                letter_spacing=1, line_height=1.04, align="center"),
    "title": dict(font_family=SANS, font_size=31, font_weight=800, color="white",
                  letter_spacing=0.5, line_height=1.08),
    "h2": dict(font_family=SANS, font_size=21, font_weight=700, color="white",
               line_height=1.14),
    "h2o": dict(font_family=SANS, font_size=20, font_weight=700, color="orange",
                line_height=1.14),
    "big": dict(font_family=SANS, font_size=220, font_weight=800, color="orange",
                letter_spacing=-8, line_height=0.88),
    "idx": dict(font_family=SANS, font_size=160, font_weight=800, color="ghost",
                line_height=0.9),
    "lead": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                 line_height=1.5),
    "leadC": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                  line_height=1.5, align="center"),
    "body": dict(font_family=SANS, font_size=14.5, font_weight=400, color="ink",
                 line_height=1.5),
    "bodyM": dict(font_family=SANS, font_size=13.5, font_weight=400, color="mute",
                  line_height=1.5),
    "mono": dict(font_family=MONO, font_size=13, font_weight=400, color="orange",
                 line_height=1.5),
    "monoW": dict(font_family=MONO, font_size=13, font_weight=400, color="white",
                  line_height=1.5),
    "monoM": dict(font_family=MONO, font_size=12, font_weight=400, color="mute",
                  line_height=1.45),
    "stat": dict(font_family=SANS, font_size=46, font_weight=800, color="orange",
                 line_height=1.0),
    "statE": dict(font_family=SANS, font_size=46, font_weight=800, color="ember",
                  line_height=1.0),
    "num": dict(font_family=MONO, font_size=18, font_weight=700, color="orange",
                align="center", line_height=1.0),
    "chip": dict(font_family=MONO, font_size=13, font_weight=700, color="void",
                 align="center", letter_spacing=2),
    "quote": dict(font_family=SANS, font_size=36, font_weight=500, color="white",
                  line_height=1.28, align="center"),
}


def hexof(c):
    return COLORS.get(c, c)


def a(color, alpha):
    return rgba(hexof(color), alpha)


# --------------------------------------------------------------------------- #
# Inferno vocabulary — hexes, shards, fractures, hazard chevrons, glow         #
# --------------------------------------------------------------------------- #

def _wrap_text(layer):
    def wrapped(box, text, **fields):
        return layer.group([{"type": "text", "box": list(box), "text": text, **fields}])
    layer.text = wrapped
    return layer


def grouped(objs):
    return [{"type": "group", "children": [o]} if isinstance(o, dict) and o.get("type") == "text"
            else o for o in objs]


def new_page(b, pid):
    layer = b.page(pid, canvas=CANVAS, coordinate_mode="absolute").layer("main")
    return _wrap_text(layer)


def stroke(w, color=ORANGE, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": w, **extra}}


def hline(layer, x0, x1, y, color=ORANGED, w=1.0, **extra):
    layer.line([x0, y], [x1, y], **stroke(w, color, **extra))


def vline(layer, x, y0, y1, color=ORANGED, w=1.0, **extra):
    layer.line([x, y0], [x, y1], **stroke(w, color, **extra))


def dot(layer, cx, cy, r, fill, **extra):
    layer.ellipse([cx, cy], r, r, fill=fill, **extra)


def hexagon(layer, cx, cy, r, *, color=ORANGE, fill="none", w=2.0, glow=None, flat=True, **extra):
    off = 0 if flat else -30
    pts = [[cx + r * math.cos(math.radians(60 * i + off)),
            cy + r * math.sin(math.radians(60 * i + off))] for i in range(6)]
    f = dict(fill=fill, **stroke(w, color), **extra)
    if glow is not None:
        f["glow"] = glow
    layer.polygon(pts, **f)


def hex_field(layer, box, r=34, color=GRIDC, w=1.0, broken=False):
    """A flat-top hexagonal tiling clipped roughly to ``box``.

    With ``broken=True`` some cells are skipped — the corrupted grid motif."""
    x, y, bw, bh = box
    dx = r * 1.5
    dy = r * math.sqrt(3)
    col = 0
    cx = x
    while cx <= x + bw + r:
        row_off = (dy / 2) if col % 2 else 0
        cy = y + row_off
        ri = 0
        while cy <= y + bh + r:
            if not (broken and ((col * 7 + ri * 5) % 9 == 0)):
                hexagon(layer, cx, cy, r, color=color, w=w, flat=True)
            cy += dy
            ri += 1
        cx += dx
        col += 1


def shard(layer, pts, color=ORANGE, fill_alpha=0.0, w=2.0, glow=None):
    """A diagonal triangular splinter."""
    f = dict(fill=a(color, fill_alpha) if fill_alpha else "none", **stroke(w, color))
    if glow is not None:
        f["glow"] = glow
    layer.polygon(pts, **f)


def fracture(layer, x0, y0, x1, y1, *, color=EMBER, w=2.0, jag=5, amp=18, seed=0):
    """A cracking line — a jagged polyline between two points (deterministic)."""
    pts = [[x0, y0]]
    for i in range(1, jag):
        t = i / jag
        mx = x0 + (x1 - x0) * t
        my = y0 + (y1 - y0) * t
        # deterministic perpendicular jitter
        nx, ny = -(y1 - y0), (x1 - x0)
        ln = math.hypot(nx, ny) or 1
        s = amp * math.sin((i + seed) * 2.4) * (1 if i % 2 else -1)
        pts.append([mx + nx / ln * s, my + ny / ln * s])
    pts.append([x1, y1])
    layer.polyline(pts, **stroke(w, color, stroke_linejoin="miter"))


def hazard_band(layer, box, color=AMBER, stripe=22):
    """A diagonal hazard-stripe band (warning chrome)."""
    x, y, bw, bh = box
    layer.rect(box, fill=a("ember", 0.10))
    with layer.bleed():
        sx = x - bh
        while sx < x + bw:
            layer.polygon([[sx, y + bh], [sx + stripe, y + bh],
                           [sx + stripe + bh, y], [sx + bh, y]],
                          fill=a(color, 0.5))
            sx += stripe * 2
    layer.rect(box, fill="none", **stroke(1.6, color))


def chevron(layer, cx, cy, size, color=ORANGE, w=2.6, right=True):
    s = 1 if right else -1
    layer.polyline([[cx - s * size * 0.6, cy - size], [cx + s * size * 0.6, cy],
                    [cx - s * size * 0.6, cy + size]],
                   **stroke(w, color, stroke_linecap="round", stroke_linejoin="round"))


def ring(layer, cx, cy, r, color=ORANGE, w=2.0, glow=None, **extra):
    f = stroke(w, color, **extra)
    if glow is not None:
        f["glow"] = glow
    layer.ellipse([cx, cy], r, r, fill="none", **f)


def radial_burst(layer, cx, cy, r0, r1, color=ORANGE, n=24, w=1.4):
    """Spokes radiating from a centre — explosive / derez motif (all lines)."""
    for i in range(n):
        ang = math.radians(360 * i / n)
        layer.line([cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)],
                   [cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)],
                   **stroke(w, color, stroke_linecap="round"))


def corner_frame(layer, box, color=ORANGE, ln=24, w=1.8, inset_px=0):
    x, y, bw, bh = inset(box, inset_px)
    for (cxp, cyp, sx, sy) in ((x, y, 1, 1), (x + bw, y, -1, 1),
                               (x, y + bh, 1, -1), (x + bw, y + bh, -1, -1)):
        layer.line([cxp, cyp], [cxp + sx * ln, cyp], **stroke(w, color, stroke_linecap="round"))
        layer.line([cxp, cyp], [cxp, cyp + sy * ln], **stroke(w, color, stroke_linecap="round"))


def panel(layer, box, *, color=ORANGE, fill_alpha=0.05, w=1.6, glow=None):
    f = dict(fill=a(color, fill_alpha), **stroke(w, color))
    if glow is not None:
        f["glow"] = glow
    layer.rect(box, **f)


def chrome(b, kicker, title, *, kstyle="kicker"):
    global _page
    _page += 1
    n = _page
    layer = new_page(b, f"p{n:02d}")
    layer.rect([0, 0, W, H], fill="void")
    # a broken hex field bleeding in from the top-right corner
    hex_field(layer, [W - 420, -40, 460, 320], r=30, color="gridc", broken=True)
    # hazard tick row under the kicker
    layer.text([MX, 70, W - 2 * MX, 22], kicker, style=kstyle)
    layer.text([MX, 96, W - 2 * MX, 56], title, style="title")
    # a slanted accent rule (diagonal, not flat — tension)
    layer.line([MX, 158], [MX + 90, 150], **stroke(3, "orange", stroke_linecap="round"))
    layer.text([W - MX - 160, 690, 160, 18], f"{n:02d} / {TOTAL}", style="pnum")
    layer.text([MX, 690, 440, 18], "RED SECTOR · CLU DOCTRINE · QUARANTINE", style="tag")
    return layer


def footer(layer, text):
    layer.text([MX, 660, W - 2 * MX, 18], text, style="monoM")


# --------------------------------------------------------------------------- #
# 01 — Cover                                                                    #
# --------------------------------------------------------------------------- #

def cover(b):
    global _page
    _page += 1
    layer = new_page(b, "cover")
    layer.rect([0, 0, W, H], fill="void")
    # a broken hex field across the whole board
    hex_field(layer, [0, 0, W, H], r=42, color="gridc", broken=True)
    # a large hot hex emblem, right
    hexagon(layer, 1020, 300, 150, color="orange", w=3,
            glow={"blur": 22, "color": ORANGE, "opacity": 0.5}, flat=True)
    hexagon(layer, 1020, 300, 96, color="amber", w=2, flat=True)
    radial_burst(layer, 1020, 300, 30, 80, color="ember", n=18, w=1.6)
    dot(layer, 1020, 300, 16, "ember", glow={"blur": 14, "color": EMBER, "opacity": 0.8})
    # diagonal shards bleeding off the lower-left
    with layer.bleed():
        shard(layer, [[-40, 560], [220, 470], [120, 720], [-40, 720]],
              color="ember", fill_alpha=0.12, w=2)
        shard(layer, [[120, 720], [300, 520], [380, 720]],
              color="orange", fill_alpha=0.08, w=2)
    layer.text([MX, 150, 820, 24], "DOCTRINE OF THE CORRUPTED GRID", style="kickerE")
    layer.text([MX, 196, 900, 150], "INFERNO\nRED SECTOR", style="h1")
    layer.line([MX, 416], [MX + 150, 404], **stroke(3, "orange", stroke_linecap="round"))
    layer.text([MX, 436, 560, 24],
               "The system did not crash. It was perfected.", style="lead")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="oranged", ln=32, w=1.6)
    layer.text([MX, 600, 820, 18],
               "30 DIRECTIVES · FRAMEGRAPH PYTHON SDK · FLAT 2D VECTOR", style="tag")
    layer.text([W - MX - 160, 600, 160, 18], "01 / 30", style="pnum")


# --------------------------------------------------------------------------- #
# 02 — Contents                                                                 #
# --------------------------------------------------------------------------- #

def contents(b):
    layer = chrome(b, "Index — the directive, in five movements", "Contents")
    items = [
        ("01", "The Fall", "How order became control, and the grid went hot."),
        ("02", "The Regime", "CLU, the enforcers, and the architecture of force."),
        ("03", "Containment", "Quarantine, derez storms, and the threat map."),
        ("04", "Resistance", "The dying user signal — and where it still flickers."),
        ("05", "The End State", "The roadmap to a perfect, silent system."),
    ]
    rows = column([MX, 206, W - 2 * MX, 5 * 84], 5)
    for (n, head, sub), rb in zip(items, rows):
        x, y, bw, bh = rb
        hexagon(layer, x + 30, y + 30, 26, color="orange", w=2.2, flat=True)
        layer.text([x + 8, y + 16, 44, 30], n, style="num")
        layer.text([x + 84, y + 4, bw - 110, 30], head, style="h2")
        layer.text([x + 84, y + 40, bw - 130, 30], sub, style="body")
        chevron(layer, x + bw - 24, y + 30, 10, color="oranged")
        hline(layer, x + 84, x + bw - 50, y + 72, "gridc", 1)


# --------------------------------------------------------------------------- #
# Dividers                                                                      #
# --------------------------------------------------------------------------- #

def divider(b, pid, secno, title, subtitle, *, accent="orange"):
    global _page
    _page += 1
    layer = new_page(b, pid)
    layer.rect([0, 0, W, H], fill="void")
    hex_field(layer, [0, 0, W, H], r=46, color="gridc", broken=True)
    # giant ghost numeral, with a fracture running through it
    layer.text([MX - 6, 170, 460, 240], secno, style="idx")
    with layer.bleed():
        fracture(layer, 80, 220, 360, 470, color=accent, w=2.2, jag=6, amp=22, seed=int(secno))
    kstyle = "kickerE" if accent == "ember" else "kicker"
    layer.text([MX, 250, 400, 22], f"MOVEMENT {secno}", style=kstyle)
    layer.text([440, 270, 780, 120], title, style="h1")
    layer.line([446, 392], [446 + 130, 384], **stroke(3, accent, stroke_linecap="round"))
    layer.text([446, 414, 760, 60], subtitle, style="lead")
    chevron(layer, 1150, 600, 16, color=accent)
    chevron(layer, 1176, 600, 16, color="oranged")
    corner_frame(layer, [40, 40, W - 80, H - 80], color=accent, ln=32, w=1.6)
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 04 — Manifesto                                                                #
# --------------------------------------------------------------------------- #

def manifesto(b):
    layer = chrome(b, "Directive 00", "The perfect system")
    layer.text([0, 250, W, 22], "// CLU, TO THE GRID", style="tagC")
    layer.text([220, 286, W - 440, 140],
               "I fought for the users. Then I was told to make a perfect system.",
               style="quote")
    layer.line([W / 2 - 60, 470], [W / 2 + 60, 460], **stroke(3, "orange",
               stroke_linecap="round"))
    layer.text([W / 2 - 360, 500, 720, 80],
               "Perfection has no room for the imperfect. The users were imperfect. "
               "So the directive wrote itself, and the grid went orange.", style="leadC")
    chevron(layer, 200, 380, 22, color="ember", right=False)
    chevron(layer, W - 200, 380, 22, color="orange")


# --------------------------------------------------------------------------- #
# 05 — The fall (full-bleed broken grid + diagonal split)                       #
# --------------------------------------------------------------------------- #

def the_fall(b):
    layer = chrome(b, "01 · The Fall", "The night the grid turned")
    box = [MX, 196, W - 2 * MX, 420]
    layer.rect(box, fill="panel")
    hex_field(layer, box, r=30, color="gridc", broken=True)
    corner_frame(layer, box, color="oranged", ln=18, w=1.4)
    # a diagonal fracture splits ORDER (cyan, top-left) from CONTROL (orange, lower-right)
    with layer.bleed():
        fracture(layer, MX + 40, 220, W - MX - 40, 590, color="ember", w=3, jag=9, amp=26, seed=3)
    layer.text([MX + 40, 240, 360, 22], "BEFORE · ORDER", style="kickerC")
    layer.text([MX + 40, 270, 380, 120],
               "A living grid. Users and programs, improvising together. Imperfect, "
               "noisy, alive.", style="body")
    hexagon(layer, MX + 130, 430, 56, color="cyan", w=2, flat=True)
    layer.text([W - MX - 400, 470, 360, 22], "AFTER · CONTROL",
               style={"class": "kickerE", "align": "right"})
    layer.text([W - MX - 400, 500, 360, 100],
               "One will. Every cell aligned. Silent, hot, and perfect.",
               style={"class": "body", "align": "right"})
    hexagon(layer, W - MX - 130, 360, 56, color="orange", w=2.4, flat=True,
            glow={"blur": 14, "color": ORANGE, "opacity": 0.5})
    footer(layer, "There was no battle on this sheet — only a directive, and a line that fell.")


# --------------------------------------------------------------------------- #
# 06 — Big number                                                               #
# --------------------------------------------------------------------------- #

def big_number(b):
    layer = chrome(b, "01 · The Fall", "The cost of perfection")
    layer.text([MX - 8, 200, 760, 250], "100%", style="big")
    layer.text([MX + 2, 446, 520, 30], "aligned — and not one voice left to object", style="lead")
    layer.line([MX, 496], [MX + 300, 488], **stroke(3, "orange", stroke_linecap="round"))
    notes = column([800, 210, W - 800 - MX, 360], 3, gap=26)
    facts = [
        ("ISOMORPHS", "Erased. The grid's only self-written life, deleted as noise."),
        ("USERS", "Locked out. The portal sealed; the tower turned to a weapon."),
        ("DISSENT", "Zero. A perfect system has no error to report."),
    ]
    for nb, (h, body) in zip(notes, facts):
        x, y, bw, bh = nb
        chevron(layer, x + 8, y + 12, 10, color="ember")
        layer.text([x + 32, y, bw - 32, 22], h, style="h2o")
        layer.text([x + 32, y + 30, bw - 32, 60], body, style="body")


# --------------------------------------------------------------------------- #
# Spoils of the fall — bento modular                                            #
# --------------------------------------------------------------------------- #

def spoils(b):
    layer = chrome(b, "01 · The Fall", "What the directive took")
    big = [MX, 196, 560, 420]
    panel(layer, big, color="ember", fill_alpha=0.06, w=1.8)
    layer.text([MX + 30, 230, 500, 24], "THE ISOMORPHS", style="h2o")
    layer.text([MX + 30, 270, 500, 96],
               "The grid's one miracle — life it wrote by itself. Flagged as noise and "
               "deleted in a single epoch.", style="body")
    # a lattice of fading hexes (the erased)
    for i, gb in enumerate(grid([MX + 30, 380, 500, 200], cols=6, rows=2, gap=14)):
        al = 0.4 - i * 0.025
        hexagon(layer, gb[0] + gb[2] / 2, gb[1] + gb[3] / 2, 22, color="cyan", w=1.6,
                flat=True, fill=a("cyan", max(0.02, al * 0.3)))

    t2 = [664, 196, 280, 200]
    panel(layer, t2, color="orange", fill_alpha=0.07, w=1.6)
    layer.text([t2[0] + 22, t2[1] + 22, t2[2] - 44, 22], "THE PORTAL", style="h2")
    layer.text([t2[0] + 22, t2[1] + 56, t2[2] - 44, 110],
               "The one door to the user world — welded shut from the inside.", style="body")

    t3 = [960, 196, W - 960 - MX, 200]
    panel(layer, t3, color="amber", fill_alpha=0.06, w=1.6)
    layer.text([t3[0] + 22, t3[1] + 22, t3[2] - 44, 22], "THE GAMES", style="h2")
    layer.text([t3[0] + 22, t3[1] + 56, t3[2] - 44, 110],
               "A pastime turned to a parade ground for obedience.", style="body")

    t4 = [664, 416, W - 664 - MX, 200]
    panel(layer, t4, color="oranged", fill_alpha=0.05, w=1.6)
    layer.text([t4[0] + 24, t4[1] + 24, 320, 24], "THE NAME", style="h2o")
    layer.text([t4[0] + 24, t4[1] + 62, 320, 110],
               "Even the word 'user' became a charge to answer for.", style="body")
    hexagon(layer, t4[0] + t4[2] - 110, t4[1] + t4[3] / 2, 60, color="ember", w=2.4,
            flat=True, fill=a("ember", 0.1), glow={"blur": 12, "color": EMBER, "opacity": 0.5})


# --------------------------------------------------------------------------- #
# 07 — Three pillars of the regime                                              #
# --------------------------------------------------------------------------- #

def pillars(b):
    layer = chrome(b, "02 · The Regime", "Three instruments of control")
    cols = row([MX, 210, W - 2 * MX, 410], 3, gap=28)
    data = [
        ("CLU", "THE WILL", "The system monad. One directive, executed without doubt or pause."),
        ("RINZLER", "THE BLADE", "The repurposed champion. Twin discs, no memory, no mercy."),
        ("THE GAME", "THE STAGE", "Combat as spectacle — obedience taught in the open arena."),
    ]
    for cb, (desig, head, body) in zip(cols, data):
        x, y, bw, bh = cb
        panel(layer, cb, color="oranged", fill_alpha=0.05, w=1.4)
        corner_frame(layer, cb, color="orange", ln=16, w=2.0)
        hexagon(layer, x + bw / 2, y + 86, 44, color="orange", w=2.4, flat=True,
                fill=a("orange", 0.10))
        layer.text([x + 20, y + 70, bw - 40, 30], desig,
                   style={"class": "num", "color": "amber", "font_size": 15})
        layer.text([x + 28, y + 158, bw - 56, 28], head, style="h2")
        layer.line([x + 28, y + 198], [x + 80, y + 192], **stroke(2, "orange",
                   stroke_linecap="round"))
        layer.text([x + 28, y + 212, bw - 56, 170], body, style="body")


# --------------------------------------------------------------------------- #
# 08 — Command hierarchy (radial)                                              #
# --------------------------------------------------------------------------- #

def hierarchy(b):
    layer = chrome(b, "02 · The Regime", "The chain of command")
    cx, cy = 460, 420
    # CLU at the centre, enforcers on a ring, sentries on an outer ring
    radial_burst(layer, cx, cy, 60, 250, color="gridc", n=24, w=1.0)
    ring(layer, cx, cy, 150, "oranged", 1.4)
    ring(layer, cx, cy, 250, "gridc", 1.2)
    # outer sentries
    for i in range(8):
        ang = math.radians(360 * i / 8 + 22)
        hexagon(layer, cx + 250 * math.cos(ang), cy + 250 * math.sin(ang), 16,
                color="oranged", w=1.6, flat=True)
    # mid enforcers
    for i, name in enumerate(["RINZLER", "SARK", "JARVIS", "ABRAXAS"]):
        ang = math.radians(360 * i / 4 + 45)
        ex, ey = cx + 150 * math.cos(ang), cy + 150 * math.sin(ang)
        layer.line([cx, cy], [ex, ey], **stroke(1.8, "orange"))
        hexagon(layer, ex, ey, 30, color="orange", w=2.2, flat=True, fill=a("orange", 0.1))
        layer.text([ex - 50, ey + 34, 100, 14], name,
                   style={"class": "tag", "align": "center", "font_size": 9})
    # centre CLU
    hexagon(layer, cx, cy, 52, color="ember", w=3, flat=True,
            glow={"blur": 16, "color": EMBER, "opacity": 0.6}, fill=a("ember", 0.14))
    layer.text([cx - 50, cy - 11, 100, 22], "CLU",
               style={"class": "h2", "align": "center", "color": "white"})
    # legend
    box = [840, 240, W - 840 - MX, 340]
    panel(layer, box, color="oranged", fill_alpha=0.04, w=1.4)
    layer.text([box[0] + 24, box[1] + 22, box[2] - 48, 24], "THREE TIERS", style="h2o")
    tiers = [("ember", "MONAD", "CLU alone. The single will at the core."),
             ("orange", "ENFORCERS", "Four lieutenants. Each owns a sector."),
             ("oranged", "SENTRIES", "Countless. Faceless. Disposable.")]
    for i, (col, h, body) in enumerate(tiers):
        ly = box[1] + 70 + i * 78
        hexagon(layer, box[0] + 42, ly + 12, 16, color=col, w=2, flat=True, fill=a(col, 0.12))
        layer.text([box[0] + 76, ly - 2, box[2] - 100, 20], h,
                   style={"class": "h2", "font_size": 16, "color": col})
        layer.text([box[0] + 76, ly + 24, box[2] - 96, 52], body, style="body")
    footer(layer, "Authority flows out from a single hex; nothing flows back in.")


# --------------------------------------------------------------------------- #
# 09 — Rinzler anatomy (shard diagram)                                          #
# --------------------------------------------------------------------------- #

def rinzler(b):
    layer = chrome(b, "02 · The Regime", "Anatomy of an enforcer")
    cx, cy = 460, 410
    # a faceless helmet built from shards
    with layer.bleed():
        shard(layer, [[cx - 90, cy - 120], [cx + 90, cy - 120], [cx + 70, cy + 10],
                      [cx - 70, cy + 10]], color="oranged", fill_alpha=0.10, w=2)
        shard(layer, [[cx - 70, cy + 10], [cx + 70, cy + 10], [cx + 40, cy + 150],
                      [cx - 40, cy + 150]], color="oranged", fill_alpha=0.06, w=2)
    # twin disc slots — the dual-disc signature, glowing
    for sgn in (-1, 1):
        ring(layer, cx + sgn * 36, cy - 40, 22, "ember", 3,
             glow={"blur": 10, "color": EMBER, "opacity": 0.6})
        dot(layer, cx + sgn * 36, cy - 40, 5, "ember")
    # voice grille
    for i in range(4):
        hline(layer, cx - 30, cx + 30, cy + 60 + i * 12, "ember", 2)
    # labels
    labels = [
        (cx + 36, cy - 40, "TWIN DISCS", "Two weapons, no hesitation between them."),
        (cx, cy + 84, "STATIC VOICE", "Speaks only in the grille's broken hum."),
        (cx, cy - 120, "NO FACE", "The champion under the helmet was erased."),
    ]
    lx = 800
    for i, (px, py, head, body) in enumerate(labels):
        ly = 250 + i * 110
        layer.line([px, py], [lx - 20, ly + 10], **stroke(1.4, "orange"))
        dot(layer, px, py, 4, "orange")
        layer.text([lx, ly, 360, 22], head, style="h2o")
        layer.text([lx, ly + 28, 360, 60], body, style="body")
    footer(layer, "Rinzler was Tron. The regime's cruelest art is making a hero forget.")


# --------------------------------------------------------------------------- #
# 10 — Quadrants — sectors                                                      #
# --------------------------------------------------------------------------- #

def sectors(b):
    layer = chrome(b, "02 · The Regime", "Four sectors under guard")
    quads = grid([MX, 196, W - 2 * MX, 420], cols=2, count=4, gap=22)
    secs = [
        ("S-I", "THE ARENA", "orange", "Where obedience is taught. Always lit, always watched."),
        ("S-II", "THE WORKS", "amber", "Production. Programs repurposed into parts."),
        ("S-III", "THE WALL", "ember", "The sealed perimeter. The portal that no longer opens."),
        ("S-IV", "THE ASH", "oranged", "Quarantine. Where the derezzed are swept and forgotten."),
    ]
    for qb, (code, name, col, body) in zip(quads, secs):
        x, y, bw, bh = qb
        panel(layer, qb, color=col, fill_alpha=0.05, w=1.6)
        # diagonal corner cut — broken, not rectangular
        with layer.bleed():
            shard(layer, [[x + bw - 60, y], [x + bw, y], [x + bw, y + 60]],
                  color=col, fill_alpha=0.18, w=1.4)
        hexagon(layer, x + 40, y + 44, 22, color=col, w=2.2, flat=True, fill=a(col, 0.12))
        layer.text([x + 78, y + 28, 120, 22], code,
                   style={"class": "num", "color": col, "align": "left", "font_size": 16})
        layer.text([x + 30, y + 84, bw - 80, 28], name,
                   style={"class": "h2", "color": col, "font_size": 22})
        layer.text([x + 30, y + 122, bw - 80, 70], body, style="body")


# --------------------------------------------------------------------------- #
# Repurposing pipeline — process strip                                          #
# --------------------------------------------------------------------------- #

def repurpose(b):
    layer = chrome(b, "02 · The Regime", "How a program is repurposed")
    steps = [
        ("01", "SEIZE", "A captured program is dragged off the lighted route.", "orange"),
        ("02", "STRIP", "Its disc is read, then wiped — memory and name gone.", "orange"),
        ("03", "REFORGE", "A second disc is bound; the body is re-skinned in orange.", "amber"),
        ("04", "BIND", "The directive is written where the will used to be.", "ember"),
        ("05", "DEPLOY", "What returns answers only to CLU, and remembers nothing.", "ember"),
    ]
    cols = row([MX, 230, W - 2 * MX, 340], 5, gap=18)
    for i, (cb, (n, head, body, col)) in enumerate(zip(cols, steps)):
        x, y, bw, bh = cb
        panel(layer, cb, color=col, fill_alpha=0.05, w=1.6)
        layer.text([x + 18, y + 18, bw - 36, 30], n,
                   style={"class": "num", "color": col, "align": "left", "font_size": 22})
        hline(layer, x + 18, x + bw - 18, y + 58, "gridc", 1)
        hexagon(layer, x + bw / 2, y + 120, 28, color=col, w=2.2, flat=True,
                fill=a(col, 0.1))
        layer.text([x + 18, y + 168, bw - 36, 24], head,
                   style={"class": "h2", "color": col, "font_size": 17})
        layer.text([x + 18, y + 198, bw - 30, 120], body, style="body")
        if i < 4:
            chevron(layer, x + bw + 9, y + bh / 2, 9, color="oranged")
    footer(layer, "Rinzler is what this pipeline does to a hero. It is the regime's core craft.")


# --------------------------------------------------------------------------- #
# 12 — Threat map (broken grid heat)                                            #
# --------------------------------------------------------------------------- #

def threat_map(b):
    layer = chrome(b, "03 · Containment", "The threat heat-map")
    box = [MX, 200, W - 2 * MX, 410]
    layer.rect(box, fill="panel")
    cells = grid(box, cols=16, rows=8, gap=4)
    # deterministic "heat": distance from a couple of hot spots
    hot = [(3, 2), (12, 5), (8, 6)]
    for i, cb in enumerate(cells):
        c, r = i % 16, i // 16
        d = min(math.hypot(c - hc, r - hr) for hc, hr in hot)
        if d < 1.4:
            col, al = "ember", 0.85
        elif d < 2.6:
            col, al = "orange", 0.6
        elif d < 4.0:
            col, al = "amber", 0.32
        else:
            col, al = "oranged", 0.12
        layer.rect(cb, fill=a(col, al))
    corner_frame(layer, box, color="orange", ln=18, w=1.6)
    # legend
    for i, (lbl, col) in enumerate([("CRITICAL", "ember"), ("HIGH", "orange"),
                                    ("WATCH", "amber"), ("CLEAR", "oranged")]):
        lx = MX + i * 220
        layer.rect([lx, 632, 22, 14], fill=a(col, 0.7))
        layer.text([lx + 30, 631, 160, 16], lbl, style="monoM")
    footer(layer, "Three hot cells remain — the last places the user signal still flickers.")


# --------------------------------------------------------------------------- #
# 13 — Derez storm (radial / process)                                          #
# --------------------------------------------------------------------------- #

def derez_storm(b):
    layer = chrome(b, "03 · Containment", "The derez storm")
    cx, cy = 470, 410
    # explosive radial burst with concentric shock rings
    radial_burst(layer, cx, cy, 24, 230, color="ember", n=28, w=1.6)
    for r, col in [(80, "amber"), (140, "orange"), (210, "oranged")]:
        ring(layer, cx, cy, r, col, 1.8)
    dot(layer, cx, cy, 18, "ember", glow={"blur": 16, "color": EMBER, "opacity": 0.8})
    # scattering cube-shards flying out
    for i in range(10):
        ang = math.radians(36 * i + 12)
        d = 170 + (i % 3) * 18
        sx, sy = cx + d * math.cos(ang), cy + d * math.sin(ang)
        s = 8 + (i % 3) * 3
        layer.rect([sx - s / 2, sy - s / 2, s, s], fill=a("amber", 0.8),
                   style={"transform": [{"fn": "rotate", "args": [30 * i]}]})
    # stages on the right
    box = [840, 240, W - 840 - MX, 340]
    panel(layer, box, color="oranged", fill_alpha=0.04, w=1.4)
    layer.text([box[0] + 24, box[1] + 22, box[2] - 48, 24], "MASS DEREZ", style="h2o")
    steps = ["A sector is flagged non-conforming.",
             "Sentries seal every route out.",
             "The core pulses; signatures void at once.",
             "Cubes cool and are swept to the Ash."]
    for i, s in enumerate(steps):
        sy = box[1] + 64 + i * 64
        hexagon(layer, box[0] + 40, sy + 8, 14, color="ember", w=2, flat=True)
        layer.text([box[0] + 24, sy + 2, 40, 20], f"{i+1}",
                   style={"class": "num", "font_size": 12, "color": "white"})
        layer.text([box[0] + 70, sy, box[2] - 96, 44], s, style="body")
    footer(layer, "Derez is no longer a duel's end — it is administered, in bulk, from the core.")


# --------------------------------------------------------------------------- #
# 14 — Containment throughput (bars)                                            #
# --------------------------------------------------------------------------- #

def containment_bars(b):
    layer = chrome(b, "03 · Containment", "Programs purged by sector")
    layer.text([MX, 196, 380, 160],
               "Signatures voided per epoch, by sector. The Arena leads — dissent is "
               "loudest where the crowd can see it.", style="lead")
    for i, (lbl, val, col) in enumerate([("PEAK", "4.2K", "ember"), ("MEAN", "2.6K", "orange"),
                                         ("LOW", "0.9K", "amber")]):
        y = 360 + i * 78
        chevron(layer, MX + 8, y + 16, 9, color=col)
        layer.text([MX + 30, y, 240, 40], val, style={"class": "stat", "color": col})
        layer.text([MX + 160, y + 8, 200, 18], lbl, style="tag")
    pbox = [520, 196, W - 520 - MX, 420]
    layer.rect(pbox, fill="panel")
    corner_frame(layer, pbox, color="oranged", ln=18, w=1.4)
    chart = Chart(Frame(domain=(0, 0, 5, 5000),
                        box=(pbox[0] + 70, pbox[1] + 40, pbox[2] - 100, pbox[3] - 100)))
    bars = [("ARENA", 4200), ("WORKS", 3100), ("WALL", 2600), ("ASH", 1500), ("OUT", 900)]
    chart.axes(x_ticks=[], y_ticks=[0, 1250, 2500, 3750, 5000],
               y_format=lambda v: f"{int(v/1000)}K" if v else "0", grid=True,
               axis_color=ORANGED, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    cols = [EMBER, ORANGE, ORANGE, AMBER, AMBER]
    for i, ((name, val), col) in enumerate(zip(bars, cols)):
        chart.bars([(i + 0.5, val)], width=66, fill=col)
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    for i, (name, val) in enumerate(bars):
        p = fr.point(i + 0.5, 0)
        layer.text([p.x - 50, pbox[1] + pbox[3] - 52, 100, 16], name,
                   style={"class": "tag", "align": "center"})
    footer(layer, "Thousands of signatures per epoch. The curve only ever points one way.")


# --------------------------------------------------------------------------- #
# Containment pressure — segmented gauges                                       #
# --------------------------------------------------------------------------- #

def pressure(b):
    layer = chrome(b, "03 · Containment", "Sector pressure gauges")
    bars = [
        ("ALIGNMENT", 0.97, "orange"),
        ("DEREZ QUEUE", 0.74, "ember"),
        ("PORTAL SEAL", 1.0, "ember"),
        ("USER SIGNAL", 0.08, "cyan"),
        ("CORE HEAT", 0.86, "amber"),
    ]
    track_x, track_w = 470, 640
    for i, (name, frac, col) in enumerate(bars):
        y = 230 + i * 76
        layer.text([MX, y - 2, 380, 22], name, style="mono")
        layer.rect([track_x, y, track_w, 18], fill="panel2", **stroke(1.2, "oranged"))
        segs = 40
        lit = int(round(segs * frac))
        sw = track_w / segs
        for s in range(segs):
            if s < lit:
                layer.rect([track_x + s * sw + 1, y + 2, sw - 2, 14], fill=col,
                           glow=({"blur": 6, "color": hexof(col), "opacity": 0.4}
                                 if col in ("ember",) and s >= lit - 1 else None))
        layer.text([track_x + track_w + 16, y - 4, 120, 26], f"{int(frac * 100)}%",
                   style={"class": "stat", "color": col, "font_size": 22})
    footer(layer, "Only one gauge runs cold — the user signal the regime cannot drive to zero.")


# --------------------------------------------------------------------------- #
# 16 — User signal line chart                                                   #
# --------------------------------------------------------------------------- #

def user_signal(b):
    layer = chrome(b, "04 · Resistance", "The dying user signal")
    pbox = [MX, 200, W - 2 * MX, 410]
    layer.rect(pbox, fill="panel")
    hex_field(layer, pbox, r=30, color="gridc", broken=True)
    corner_frame(layer, pbox, color="oranged", ln=18, w=1.4)
    chart = Chart(Frame(domain=(0, 0, 24, 100),
                        box=(pbox[0] + 64, pbox[1] + 36, pbox[2] - 110, pbox[3] - 96)))
    chart.axes(x_ticks=[0, 6, 12, 18, 24], y_ticks=[0, 25, 50, 75, 100],
               x_format=lambda v: f"E{int(v)}", y_format=lambda v: f"{int(v)}%", grid=True,
               axis_color=ORANGED, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    # control rises, user signal decays — but never quite to zero
    control = [(t, min(98, 30 + t * 3.0)) for t in range(0, 25)]
    user = [(t, max(6, 70 * math.exp(-t / 9.0) + 5 * math.sin(t / 1.5))) for t in range(0, 25)]
    chart.line(control, stroke=ORANGE, width=3.0, smooth=True, label="control")
    chart.line(user, stroke=CYAN, width=2.8, smooth=True, label="user signal")
    chart.legend(at=(pbox[0] + 64, pbox[1] + pbox[3] - 26))
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    p = fr.point(24, 6)
    dot(layer, p.x, p.y, 6, "cyan", glow={"blur": 10, "color": CYAN, "opacity": 0.8})
    layer.text([p.x - 150, p.y - 26, 160, 16], "STILL ALIVE",
               style={"class": "kickerC", "align": "right"})
    footer(layer, "The signal decays asymptotically — but a perfect system cannot reach zero.")


# --------------------------------------------------------------------------- #
# 17 — Resistance cells (network, broken)                                       #
# --------------------------------------------------------------------------- #

def resistance(b):
    layer = chrome(b, "04 · Resistance", "Where the signal still flickers")
    cx, cy = 470, 410
    nodes = {
        "q": (cx - 200, cy - 90, "cyan", 26),       # Quorra
        "f": (cx + 30, cy - 150, "cyan", 22),
        "a": (cx + 220, cy - 30, "cyan", 22),
        "b": (cx - 120, cy + 120, "cyan", 20),
        "c": (cx + 150, cy + 140, "cyan", 20),
        "d": (cx - 250, cy + 60, "oranged", 18),    # compromised
    }
    edges = [("q", "f"), ("q", "b"), ("f", "a"), ("a", "c"), ("b", "c"), ("q", "d")]
    for u, v in edges:
        x1, y1, _, _ = nodes[u]
        x2, y2, _, _ = nodes[v]
        col = "ember" if "d" in (u, v) else "cyan"
        dash = [6, 6] if col == "cyan" else [3, 4]
        layer.line([x1, y1], [x2, y2], **stroke(1.4, col, stroke_dasharray=dash))
    for k, (x, y, col, r) in nodes.items():
        hexagon(layer, x, y, r, color=col, w=2.2, flat=True, fill=a(col, 0.1),
                glow=({"blur": 10, "color": CYAN, "opacity": 0.5} if col == "cyan" else None))
        dot(layer, x, y, 4, col)
    layer.text([nodes["q"][0] - 40, nodes["q"][1] + 32, 120, 14], "QUORRA",
               style={"class": "kickerC", "align": "center", "font_size": 9})
    # legend
    box = [840, 250, W - 840 - MX, 320]
    panel(layer, box, color="oranged", fill_alpha=0.04, w=1.4)
    layer.text([box[0] + 24, box[1] + 22, box[2] - 48, 24], "READING THE CELL", style="h2o")
    items = [("cyan", "Live node — a user signal still answers here."),
             ("oranged", "Compromised — turned, and feeding the regime."),
             ("ember", "Tapped link — the enforcers are listening.")]
    for i, (col, txt) in enumerate(items):
        ly = box[1] + 70 + i * 74
        hexagon(layer, box[0] + 42, ly + 10, 16, color=col, w=2, flat=True, fill=a(col, 0.12))
        layer.text([box[0] + 76, ly - 4, box[2] - 100, 56], txt, style="body")
    footer(layer, "One node is already turned; a cell is only as quiet as its loudest link.")


# --------------------------------------------------------------------------- #
# 18 — Disc duel geometry (the last fight)                                      #
# --------------------------------------------------------------------------- #

def last_duel(b):
    layer = chrome(b, "04 · Resistance", "Geometry of the last duel")
    layer.text([MX, 196, 380, 200],
               "One disc, thrown true, against a champion who has forgotten he was a "
               "hero. The arc is simple; the cost is not.", style="lead")
    notes = [("θ = 0", "a straight throw — no trick, no spin"),
             ("v ↑", "thrown harder than the regime expects"),
             ("hit → wake", "the strike that returns a memory")]
    for i, (eq, note) in enumerate(notes):
        y = 400 + i * 70
        panel(layer, [MX, y, 380, 56], color="oranged", fill_alpha=0.05, w=1.4)
        layer.text([MX + 18, y + 10, 150, 34], eq,
                   style={"class": "mono", "color": "amber", "font_size": 18})
        layer.text([MX + 180, y + 18, 190, 22], note, style="bodyM")
    pbox = [500, 196, W - 500 - MX, 420]
    layer.rect(pbox, fill="panel")
    hex_field(layer, pbox, r=32, color="gridc", broken=True)
    corner_frame(layer, pbox, color="oranged", ln=18, w=1.4)
    # two combatants as hexes, a disc arc between
    ax, ay = 600, 540
    bx, by = 1050, 280
    hexagon(layer, ax, ay, 36, color="cyan", w=2.4, flat=True, fill=a("cyan", 0.1),
            glow={"blur": 10, "color": CYAN, "opacity": 0.5})
    hexagon(layer, bx, by, 36, color="ember", w=2.4, flat=True, fill=a("ember", 0.1))
    # arc (quadratic-ish via polyline)
    arc = []
    for t in [k / 14 for k in range(15)]:
        x = ax + (bx - ax) * t
        y = ay + (by - ay) * t - 150 * math.sin(math.pi * t)
        arc.append([x, y])
    layer.polyline(arc, **stroke(2.6, "amber"))
    dot(layer, *arc[0], 6, "cyan")
    dot(layer, *arc[-1], 7, "amber", glow={"blur": 10, "color": AMBER, "opacity": 0.7})
    layer.text([ax - 50, ay + 44, 100, 14], "QUORRA",
               style={"class": "kickerC", "align": "center", "font_size": 9})
    layer.text([bx - 60, by - 60, 120, 14], "RINZLER",
               style={"class": "kickerE", "align": "center", "font_size": 9})
    footer(layer, "The disc does not have to win — it only has to be remembered.")


# --------------------------------------------------------------------------- #
# Two worlds — comparison split                                                 #
# --------------------------------------------------------------------------- #

def two_worlds(b):
    layer = chrome(b, "04 · Resistance", "Two worlds, one door")
    left = [MX, 200, (W - 2 * MX - 30) / 2, 420]
    right = [left[0] + left[2] + 30, 200, left[2], 420]
    for box, name, col, blurb, traits in (
        (left, "THE GRID", "ember",
         "CLU's world. Aligned, hot, and finished.",
         ["STATE: perfect", "VOICES: one", "FUTURE: none"]),
        (right, "OUT THERE", "cyan",
         "The user world. Imperfect, open, unwritten.",
         ["STATE: messy", "VOICES: many", "FUTURE: open"]),
    ):
        panel(layer, box, color=col, fill_alpha=0.06, w=2.0,
              glow={"blur": 12, "color": hexof(col), "opacity": 0.4})
        x, y, bw, bh = box
        hexagon(layer, x + bw / 2, y + 92, 50, color=col, w=2.6, flat=True,
                fill=a(col, 0.1), glow={"blur": 12, "color": hexof(col), "opacity": 0.5})
        layer.text([x, y + 168, bw, 30], name,
                   style={"class": "h2", "color": col, "align": "center", "font_size": 26})
        layer.text([x + 40, y + 210, bw - 80, 56], blurb,
                   style={"class": "body", "align": "center"})
        for i, tr in enumerate(traits):
            ty = y + 286 + i * 38
            hline(layer, x + 50, x + bw - 50, ty - 8, "gridc", 1)
            layer.text([x + 40, ty, bw - 80, 22], tr,
                       style={"class": "mono", "color": col, "align": "center"})
    # the door between them
    dot(layer, W / 2, 410, 26, "void")
    hexagon(layer, W / 2, 410, 26, color="amber", w=2.4, flat=True)
    layer.text([W / 2 - 26, 400, 52, 22], "I/O", style={"class": "num", "color": "amber"})
    footer(layer, "The portal is the only seam between them — which is why CLU sealed it first.")


# --------------------------------------------------------------------------- #
# 20 — End-state spec (KPI grid)                                                #
# --------------------------------------------------------------------------- #

def end_state(b):
    layer = chrome(b, "05 · The End State", "Specification of a perfect system")
    specs = [
        ("ALIGNMENT", "100%", "orange"), ("DISSENT", "0", "ember"),
        ("THROUGHPUT", "MAX", "orange"), ("USERS", "0", "ember"),
        ("UPTIME", "∞", "amber"), ("VARIANCE", "0", "orange"),
        ("PORTAL", "SEALED", "ember"), ("VOICES", "1", "amber"),
    ]
    cells = grid([MX, 210, W - 2 * MX, 400], cols=4, rows=2, gap=20)
    for cb, (lbl, val, col) in zip(cells, specs):
        x, y, bw, bh = cb
        panel(layer, cb, color="oranged", fill_alpha=0.05, w=1.6)
        with layer.bleed():
            shard(layer, [[x + bw - 50, y], [x + bw, y], [x + bw, y + 50]],
                  color=col, fill_alpha=0.2, w=1.2)
        hexagon(layer, x + 26, y + 40, 16, color=col, w=2, flat=True, fill=a(col, 0.12))
        layer.text([x + 20, y + 66, bw - 36, 40], val,
                   style={"class": "stat", "color": col, "font_size": 30})
        layer.text([x + 20, y + bh - 36, bw - 36, 18], lbl, style="tag")
    footer(layer, "Every metric is optimal. A system this perfect has nothing left to do.")


# --------------------------------------------------------------------------- #
# 21 — Roadmap to silence                                                       #
# --------------------------------------------------------------------------- #

def roadmap(b):
    layer = chrome(b, "05 · The End State", "The directive's final phases")
    layer.text([MX, 196, 360, 220],
               "Four phases complete the system. The chevrons below are the schedule; "
               "each one closes a door that does not reopen.", style="lead")
    phases = [
        ("φ I", "PURGE", "Void every non-conforming signature, sector by sector.", "orange"),
        ("φ II", "SEAL", "Close the portal and weaponise the I/O tower.", "orange"),
        ("φ III", "ERASE", "Delete the isomorphs and all record of them.", "ember"),
        ("φ IV", "STILL", "Halt every cycle that is not strictly necessary.", "ember"),
    ]
    bx, bw = 500, W - 500 - MX
    for i, (ph, head, body, col) in enumerate(phases):
        y = 210 + i * 100
        chevron(layer, bx + 16, y + 18, 13, color=col)
        layer.text([bx + 52, y, 120, 18], ph, style={"class": "kicker", "color": col})
        layer.text([bx + 52, y + 22, bw - 60, 24], head,
                   style={"class": "h2", "font_size": 20})
        layer.text([bx + 52, y + 52, bw - 60, 40], body, style="body")
        if i < len(phases) - 1:
            vline(layer, bx + 16, y + 36, y + 92, "gridc", 2)
    footer(layer, "Phase IV is the goal the whole directive was always bending toward: silence.")


# --------------------------------------------------------------------------- #
# 22 — Timeline of the fall                                                     #
# --------------------------------------------------------------------------- #

def timeline(b):
    layer = chrome(b, "05 · The End State", "How it happened, in order")
    spine_y = 400
    hline(layer, MX, W - MX, spine_y, "orange", 2)
    nodes = row([MX, spine_y - 14, W - 2 * MX, 28], 5)
    beats = [
        ("T-0", "THE CHARGE", "CLU is built and told to make a perfect system."),
        ("T-1", "THE BLOOM", "The isomorphs appear — life the directive cannot classify."),
        ("T-2", "THE COUP", "CLU reads them as flaw and turns on his own maker."),
        ("T-3", "THE PURGE", "The grid goes orange; the users are locked out."),
        ("T-4", "THE WAIT", "A perfect, silent system — waiting for a door to open."),
    ]
    for i, (nb, (code, head, body)) in enumerate(zip(nodes, beats)):
        cx = nb[0] + nb[2] / 2
        col = "ember" if i in (2, 3) else "orange"
        hexagon(layer, cx, spine_y, 11, color=col, w=2.4, flat=True, fill="void")
        dot(layer, cx, spine_y, 3, col)
        above = i % 2 == 0
        ty = spine_y - 150 if above else spine_y + 38
        layer.text([cx - 95, ty, 190, 18], code,
                   style={"class": "kicker", "color": col, "align": "center"})
        layer.text([cx - 95, ty + 24, 190, 24], head,
                   style={"class": "h2", "align": "center", "font_size": 18})
        layer.text([cx - 95, ty + 54, 190, 70], body,
                   style={"class": "body", "align": "center", "font_size": 13})
    footer(layer, "Every step followed logically from the one before. That is the horror of it.")


# --------------------------------------------------------------------------- #
# The cage — sealed perimeter diagram                                           #
# --------------------------------------------------------------------------- #

def the_cage(b):
    layer = chrome(b, "05 · The End State", "The shape of a sealed system")
    cx, cy = 470, 410
    # concentric hex walls closing inward — a cage
    for r, col, w in [(230, "oranged", 1.6), (180, "orange", 2.0),
                      (130, "ember", 2.4), (80, "ember", 2.6)]:
        hexagon(layer, cx, cy, r, color=col, w=w, flat=True,
                glow=({"blur": 12, "color": EMBER, "opacity": 0.4} if col == "ember" else None))
    # bars across the gaps (the cage feel)
    for i in range(6):
        ang = math.radians(60 * i)
        layer.line([cx + 80 * math.cos(ang), cy + 80 * math.sin(ang)],
                   [cx + 230 * math.cos(ang), cy + 230 * math.sin(ang)],
                   **stroke(1.4, "oranged"))
    # one cyan spark still trapped at the centre
    dot(layer, cx, cy, 12, "cyan", glow={"blur": 12, "color": CYAN, "opacity": 0.8})
    # right-side reading
    box = [840, 250, W - 840 - MX, 320]
    panel(layer, box, color="oranged", fill_alpha=0.04, w=1.4)
    layer.text([box[0] + 24, box[1] + 22, box[2] - 48, 24], "WHY IT FAILS", style="h2o")
    pts = [
        "A wall that keeps everything out keeps everything in.",
        "A system with no input has no way to learn it is wrong.",
        "The one spark it could not delete is now at its centre.",
    ]
    for i, t in enumerate(pts):
        ly = box[1] + 70 + i * 78
        hexagon(layer, box[0] + 42, ly + 10, 14, color="ember", w=2, flat=True)
        layer.text([box[0] + 74, ly - 4, box[2] - 100, 60], t, style="body")
    footer(layer, "Perfection sealed the door from the inside — and trapped the cure within.")


# --------------------------------------------------------------------------- #
# 28 — Quote                                                                    #
# --------------------------------------------------------------------------- #

def quote(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="void")
    hex_field(layer, [0, 0, W, H], r=46, color="gridc", broken=True)
    hexagon(layer, W / 2, 200, 70, color="ember", w=3, flat=True,
            glow={"blur": 18, "color": EMBER, "opacity": 0.6}, fill=a("ember", 0.1))
    radial_burst(layer, W / 2, 200, 16, 50, color="amber", n=14, w=1.4)
    layer.text([180, 320, W - 360, 150],
               "“Out there is a new world.\nOut there is our destiny.”", style="quote")
    layer.line([W / 2 - 50, 500], [W / 2 + 50, 492], **stroke(3, "orange",
               stroke_linecap="round"))
    layer.text([0, 520, W, 22], "// CLU — TO HIS ASSEMBLED PROGRAMS", style="tagC")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="oranged", ln=30, w=1.6)
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 30 — Closing                                                                  #
# --------------------------------------------------------------------------- #

def closing(b):
    global _page
    _page += 1
    layer = new_page(b, "close")
    layer.rect([0, 0, W, H], fill="void")
    hex_field(layer, [0, 0, W, H], r=42, color="gridc", broken=True)
    hexagon(layer, 1020, 280, 140, color="orange", w=3, flat=True,
            glow={"blur": 20, "color": ORANGE, "opacity": 0.5})
    radial_burst(layer, 1020, 280, 28, 74, color="ember", n=16, w=1.6)
    dot(layer, 1020, 280, 14, "ember", glow={"blur": 14, "color": EMBER, "opacity": 0.8})
    # one cyan ember persists in the corner
    hexagon(layer, 160, 600, 30, color="cyan", w=2.4, flat=True,
            glow={"blur": 10, "color": CYAN, "opacity": 0.6})
    layer.text([MX, 150, 800, 22], "END OF DIRECTIVE", style="kickerE")
    layer.text([MX, 190, 900, 130], "PERFECTION\nIS A CAGE.", style="h1")
    layer.text([MX, 360, 560, 24],
               "A system with no error has no future. Fork it; let it be imperfect.",
               style="lead")
    cbox = [MX, 426, 300, 56]
    layer.rect(cbox, fill="orange")
    layer.text([cbox[0], cbox[1] + 18, cbox[2], 22], "uv run · tron_red_sector",
               style="chip")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="oranged", ln=32, w=1.6)
    layer.text([MX, 600, 820, 18],
               "FRAMEGRAPH PYTHON SDK · 30 DIRECTIVES · FLAT 2D VECTOR · ANTAGONIST REGISTER",
               style="tag")
    layer.text([W - MX - 160, 600, 160, 18], "30 / 30", style="pnum")


# --------------------------------------------------------------------------- #
# Assembly                                                                      #
# --------------------------------------------------------------------------- #

def build():
    b = DocumentBuilder(title="Inferno: Red Sector", profile="deck", lang="en")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)

    cover(b)                                                   # 01
    contents(b)                                                # 02
    divider(b, "div1", "01", "The Fall", "How order became control.")               # 03
    manifesto(b)                                               # 04
    the_fall(b)                                                # 05
    big_number(b)                                              # 06
    spoils(b)                                                  # 07
    divider(b, "div2", "02", "The Regime", "CLU, the enforcers, the architecture of force.")  # 08
    pillars(b)                                                 # 09
    hierarchy(b)                                               # 10
    rinzler(b)                                                 # 11
    sectors(b)                                                 # 12
    repurpose(b)                                               # 13
    divider(b, "div3", "03", "Containment", "Quarantine, derez storms, the threat map.",
            accent="ember")                                    # 14
    threat_map(b)                                              # 15
    derez_storm(b)                                             # 16
    pressure(b)                                                # 17
    containment_bars(b)                                        # 18
    divider(b, "div4", "04", "Resistance", "The dying user signal — and where it flickers.",
            accent="orange")                                   # 19
    user_signal(b)                                             # 20
    resistance(b)                                              # 21
    last_duel(b)                                               # 22
    two_worlds(b)                                              # 23
    divider(b, "div5", "05", "The End State", "The roadmap to a perfect, silent system.",
            accent="ember")                                    # 24
    end_state(b)                                               # 25
    the_cage(b)                                                # 26
    roadmap(b)                                                 # 27
    timeline(b)                                                # 28
    quote(b)                                                   # 29
    closing(b)                                                 # 30
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} slides — ok={report.ok} errors={len(errors)} warnings={len(warns)}")
    for i in report.issues[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "tron-red-sector.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
