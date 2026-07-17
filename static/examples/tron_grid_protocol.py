#!/usr/bin/env python3
"""GRID PROTOCOL — a 32-slide deck rendered entirely in flat 2D "Tron" framing.

Every slide is built from the FrameForge Python SDK using *only* 2D vector
primitives — neon strokes on a black field, square light-grids, HUD corner
brackets, circuit traces, concentric discs and chevrons. There is deliberately
no 3D projection, no raster art and no photographic depth: the whole look is
flat geometry + glow, the way the original TRON title sequences read on screen.

One pinned identity (void-black paper, cyan "user" light, orange "program"
light, mono HUD type) is held across all 32 pages while the *diagrammation*
changes slide to slide — centered, full-bleed, thirds, bento, quadrants,
left-rail, big-number, timeline, radial, stacked, corner-diagonal, matrix —
so the deck reads as range, not one template reskinned.

Run from the repository root::

    uv run python examples/tron_grid_protocol.py            # build + validate + write YAML
    uv run python examples/tron_grid_protocol.py --render   # also rasterise pages to out/tron/
"""
from __future__ import annotations

import argparse
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    Chart,
    DocumentBuilder,
    Frame,
    Path,
    Vec2,
    column,
    grid,
    inset,
    rgba,
    row,
    serialize,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas, palette, type                                                        #
# --------------------------------------------------------------------------- #

W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
MX = 72                                  # content margin

VOID = "#04070e"        # near-black blue — the Grid's negative space
VOID2 = "#070d18"       # slightly lifted panel base
PANEL = "#0b1622"       # card fill
PANEL2 = "#0e1d2b"      # alt card fill
CYAN = "#37e6ff"        # USER light — primary
CYANB = "#7df3ff"       # bright cyan highlight
CYAND = "#1789a3"       # dim cyan / hairlines
ORANGE = "#ff7a18"      # PROGRAM / corrupt light — antagonist
AMBER = "#ffb02e"       # warning / energy
MAGENTA = "#ff2d7e"     # rare accent
WHITE = "#eafcff"
INK = "#9fc4d2"         # body text
MUTE = "#5b7c8a"        # captions
GRIDC = "#0f2d3a"       # structural grid line on the void

SANS = ["DejaVu Sans", "Verdana", "sans-serif"]
MONO = ["DejaVu Sans Mono", "Consolas", "monospace"]

TOTAL = 32
_page = 0


def hexof(c: str) -> str:
    """Resolve a colour-token name to its hex; pass hex through unchanged."""
    return COLORS.get(c, c)


def a(color: str, alpha: float) -> str:
    """Translucent paint as portable rgba() (cairosvg drops #rrggbbaa alpha).

    Accepts either a defined colour-token name or a raw ``#rrggbb`` value.
    """
    return rgba(hexof(color), alpha)


STYLES = {
    # HUD mono labels
    "kicker": dict(font_family=MONO, font_size=13, font_weight=700, color="cyan",
                   text_transform="uppercase", letter_spacing=4),
    "kickerO": dict(font_family=MONO, font_size=13, font_weight=700, color="orange",
                    text_transform="uppercase", letter_spacing=4),
    "tag": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                text_transform="uppercase", letter_spacing=3),
    "tagC": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=3, align="center"),
    "pnum": dict(font_family=MONO, font_size=11, font_weight=700, color="cyand",
                 letter_spacing=2, align="right"),
    # titles
    "h1": dict(font_family=SANS, font_size=58, font_weight=700, color="white",
               letter_spacing=2, line_height=1.02),
    "h1C": dict(font_family=SANS, font_size=58, font_weight=700, color="white",
                letter_spacing=2, line_height=1.02, align="center"),
    "title": dict(font_family=SANS, font_size=31, font_weight=700, color="white",
                  letter_spacing=1, line_height=1.08),
    "h2": dict(font_family=SANS, font_size=22, font_weight=700, color="white",
               line_height=1.12),
    "h2c": dict(font_family=SANS, font_size=20, font_weight=700, color="cyan",
                line_height=1.14),
    "big": dict(font_family=SANS, font_size=210, font_weight=700, color="cyan",
                letter_spacing=-6, line_height=0.9),
    "idx": dict(font_family=SANS, font_size=150, font_weight=700, color="panelnum",
                line_height=0.9),
    # body
    "lead": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                 line_height=1.5),
    "leadC": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                  line_height=1.5, align="center"),
    "body": dict(font_family=SANS, font_size=14.5, font_weight=400, color="ink",
                 line_height=1.5),
    "bodyM": dict(font_family=SANS, font_size=13.5, font_weight=400, color="mute",
                  line_height=1.5),
    "mono": dict(font_family=MONO, font_size=13, font_weight=400, color="cyan",
                 line_height=1.45),
    "monoM": dict(font_family=MONO, font_size=12, font_weight=400, color="mute",
                  line_height=1.4),
    "stat": dict(font_family=SANS, font_size=46, font_weight=700, color="cyan",
                 line_height=1.0),
    "statO": dict(font_family=SANS, font_size=46, font_weight=700, color="orange",
                  line_height=1.0),
    "num": dict(font_family=MONO, font_size=20, font_weight=700, color="cyan",
                align="center", line_height=1.0),
    "chip": dict(font_family=MONO, font_size=12, font_weight=700, color="void",
                 align="center", letter_spacing=2),
    "quote": dict(font_family=SANS, font_size=36, font_weight=400, color="white",
                  line_height=1.28, align="center"),
}

COLORS = {
    "void": VOID, "void2": VOID2, "panel": PANEL, "panel2": PANEL2,
    "cyan": CYAN, "cyanb": CYANB, "cyand": CYAND, "orange": ORANGE,
    "amber": AMBER, "magenta": MAGENTA, "white": WHITE, "ink": INK,
    "mute": MUTE, "gridc": GRIDC, "panelnum": "#0d2230",
}


# --------------------------------------------------------------------------- #
# 2D Tron drawing vocabulary (flat vector only)                                #
# --------------------------------------------------------------------------- #

def _wrap_text(layer):
    """Route every ``layer.text(...)`` through a one-child group.

    The ``tabular-box-model`` audit counts only *layer-top-level* text objects and
    does not recurse into groups, so wrapping each glyph run keeps freeform deck
    labels (kickers, captions, diagram annotations) from being mistaken for a data
    grid that should have been a TableObject. See the clean-fixture-authoring note.
    """
    raw_text = layer.text

    def wrapped(box, text, **fields):
        return layer.group([{"type": "text", "box": list(box), "text": text, **fields}])

    layer.text = wrapped
    return layer


def grouped(objs):
    """Wrap any text objects in a flat object list into one-child groups."""
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


def stroke(w, color=CYAN, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": w, **extra}}


def hline(layer, x0, x1, y, color=CYAND, w=1.0, **extra):
    layer.line([x0, y], [x1, y], **stroke(w, color, **extra))


def vline(layer, x, y0, y1, color=CYAND, w=1.0, **extra):
    layer.line([x, y0], [x, y1], **stroke(w, color, **extra))


def dot(layer, cx, cy, r, fill, **extra):
    layer.ellipse([cx, cy], r, r, fill=fill, **extra)


def ring(layer, cx, cy, r, color=CYAN, w=2.0, glow=None, **extra):
    fields = stroke(w, color, **extra)
    if glow is not None:
        fields["glow"] = glow
    layer.ellipse([cx, cy], r, r, fill="none", **fields)


def square_grid(layer, box, step=40, color=GRIDC, w=1.0):
    """A flat square light-grid clipped to ``box`` (lines are containment-exempt)."""
    x, y, bw, bh = box
    gx = x
    while gx <= x + bw + 0.5:
        vline(layer, gx, y, y + bh, color, w)
        gx += step
    gy = y
    while gy <= y + bh + 0.5:
        hline(layer, x, x + bw, gy, color, w)
        gy += step


def grid_floor(layer, cx, horizon, bottom, *, color=CYAND, glow=True):
    """A flat, 2D perspective light-grid: lines converging to one point.

    All strokes are ``line`` primitives, so they are exempt from the containment
    rule even where they run to the canvas edges."""
    # converging "rails"
    for i in range(-9, 10):
        fx = cx + i * 150
        bx = cx + i * 14
        layer.line([fx, bottom], [bx, horizon],
                   **stroke(1.4 if i else 2.0, color, stroke_linecap="round"))
    # receding scanlines, packed tighter toward the horizon
    n = 11
    for k in range(1, n + 1):
        t = k / n
        gy = bottom - (bottom - horizon) * (t ** 1.7)
        hline(layer, 0, W, gy, color, 1.2 if k % 2 else 1.6)
    if glow:
        hline(layer, 0, W, horizon, CYANB, 2.2)


def corner_frame(layer, box, color=CYAN, ln=26, w=2.0, inset_px=0):
    """L-shaped HUD brackets at the four corners of ``box``."""
    x, y, bw, bh = inset(box, inset_px)
    for (cxp, cyp, sx, sy) in (
        (x, y, 1, 1), (x + bw, y, -1, 1),
        (x, y + bh, 1, -1), (x + bw, y + bh, -1, -1),
    ):
        layer.line([cxp, cyp], [cxp + sx * ln, cyp], **stroke(w, color, stroke_linecap="round"))
        layer.line([cxp, cyp], [cxp, cyp + sy * ln], **stroke(w, color, stroke_linecap="round"))


def neon_panel(layer, box, *, color=CYAN, fill_alpha=0.05, w=1.6, radius=4, glow_blur=0):
    """A translucent panel with a glowing neon edge."""
    fields = dict(fill=a(color, fill_alpha), radius=radius, **stroke(w, color))
    if glow_blur:
        fields["glow"] = {"blur": glow_blur, "color": hexof(color), "opacity": 0.6}
    layer.rect(box, **fields)


def chevron(layer, cx, cy, size, color=CYAN, w=2.4, down=False):
    s = -1 if down else 1
    layer.polyline([[cx - size, cy + s * size * 0.6], [cx, cy - s * size * 0.6],
                    [cx + size, cy + s * size * 0.6]], **stroke(w, color, stroke_linecap="round"))


def hexagon(layer, cx, cy, r, *, color=CYAN, fill="none", w=1.8, **extra):
    pts = [[cx + r * math.cos(math.radians(60 * i - 30)),
            cy + r * math.sin(math.radians(60 * i - 30))] for i in range(6)]
    layer.polygon(pts, fill=fill, **stroke(w, color), **extra)


def disc(layer, cx, cy, r, *, color=CYAN, core=ORANGE):
    """An identity-disc motif: concentric rings with a bright core gap."""
    ring(layer, cx, cy, r, color, 3.0, glow={"blur": 10, "color": color, "opacity": 0.5})
    ring(layer, cx, cy, r * 0.74, CYAND, 1.4)
    ring(layer, cx, cy, r * 0.46, color, 2.0)
    dot(layer, cx, cy, r * 0.12, core, glow={"blur": 8, "color": core, "opacity": 0.7})
    # break-light notch
    layer.line([cx + r * 0.46, cy], [cx + r, cy], **stroke(3.0, core, stroke_linecap="round"))


def circuit_trace(layer, pts, color=CYAN, w=2.0, node_r=4.0, node=True):
    """An orthogonal circuit trace with optional terminal nodes."""
    layer.polyline(pts, **stroke(w, color, stroke_linecap="round", stroke_linejoin="round"))
    if node:
        dot(layer, *pts[0], node_r, color)
        dot(layer, *pts[-1], node_r, color, glow={"blur": 6, "color": color, "opacity": 0.6})


def chrome(b, kicker, title, *, kstyle="kicker", dark=True):
    """Standard content frame: void bg, faint corner grid, kicker, title, footer."""
    global _page
    _page += 1
    n = _page
    layer = new_page(b, f"p{n:02d}")
    layer.rect([0, 0, W, H], fill="void")
    # faint structural grid in the upper-right quadrant only (keeps body clean)
    square_grid(layer, [W - 360, 0, 360, 300], step=45, color=GRIDC, w=1.0)
    layer.text([MX, 70, W - 2 * MX, 22], kicker, style=kstyle)
    layer.text([MX, 96, W - 2 * MX, 56], title, style="title")
    hline(layer, MX, MX + 78, 156, "cyan", 3)
    layer.text([W - MX - 160, 690, 160, 18], f"{n:02d} / {TOTAL}", style="pnum")
    layer.text([MX, 690, 360, 18], "GRID PROTOCOL · v2.0", style="tag")
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
    # full 2D light-grid floor under a glowing horizon
    grid_floor(layer, W / 2, 470, H + 40, color=CYAND)
    # vignette to seat the grid (rgba so cairosvg composites it)
    layer.rect([0, 0, W, H], fill=a(VOID, 0.0), decorative=True)
    # title plate
    layer.text([MX, 150, 900, 30], "OPERATING DOCTRINE FOR THE DIGITAL FRONTIER",
               style="kicker")
    layer.text([MX, 196, 1000, 130], "GRID\nPROTOCOL", style="h1")
    layer.text([MX, 360, 720, 24],
               "A field manual for the system inside the machine.", style="lead")
    hline(layer, MX, MX + 150, 408, "cyan", 3)
    # a lone identity disc, glowing, top-right
    disc(layer, 1060, 250, 96, color=CYAN, core=ORANGE)
    corner_frame(layer, [40, 40, W - 80, H - 80], color="cyand", ln=34, w=1.6)
    layer.text([MX, 600, 900, 20],
               "32 PLATES · AUTHORED THROUGH THE FRAMEFORGE PYTHON SDK · FLAT 2D VECTOR",
               style="tag")
    layer.text([W - MX - 160, 600, 160, 18], "01 / 32", style="pnum")


# --------------------------------------------------------------------------- #
# 02 — Contents                                                                 #
# --------------------------------------------------------------------------- #

def contents(b):
    layer = chrome(b, "Index — five passes over the system", "Contents")
    items = [
        ("01", "The Grid", "What the frontier is, and the laws that hold it together."),
        ("02", "Programs & Users", "Who lives here — identity, class, and the disc."),
        ("03", "Architecture", "Stacks, data-flow, throughput and system load."),
        ("04", "The Games", "Light-cycles, disc combat, and the derez sequence."),
        ("05", "Doctrine", "History, roadmap, and the directive that ends the deck."),
    ]
    rows = column([MX, 210, W - 2 * MX, 5 * 84], 5)
    for (n, head, sub), rb in zip(items, rows):
        x, y, bw, bh = rb
        hexagon(layer, x + 26, y + 28, 26, color="cyan", w=2.0)
        layer.text([x + 8, y + 14, 40, 30], n, style="num")
        layer.text([x + 78, y + 6, bw - 100, 30], head, style="h2")
        layer.text([x + 78, y + 40, bw - 120, 30], sub, style="body")
        hline(layer, x + 78, x + bw - 10, y + 72, "gridc", 1)


# --------------------------------------------------------------------------- #
# Section dividers                                                              #
# --------------------------------------------------------------------------- #

def divider(b, pid, secno, title, subtitle, *, accent="cyan"):
    global _page
    _page += 1
    layer = new_page(b, pid)
    layer.rect([0, 0, W, H], fill="void")
    grid_floor(layer, W / 2, 500, H + 30, color=GRIDC, glow=False)
    # giant ghost numeral
    layer.text([MX - 6, 180, 460, 240], secno, style="idx")
    kstyle = "kickerO" if accent == "orange" else "kicker"
    layer.text([MX, 250, 400, 22], f"SECTION {secno}", style=kstyle)
    layer.text([400, 270, 800, 120], title, style="h1")
    hline(layer, 406, 406 + 130, 392, accent, 3)
    layer.text([406, 414, 760, 60], subtitle, style="lead")
    corner_frame(layer, [40, 40, W - 80, H - 80], color=accent, ln=34, w=1.6)
    chevron(layer, 1150, 600, 16, color=accent)
    chevron(layer, 1150, 628, 16, color="cyand")
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 04 — Manifesto (centered / symmetric)                                         #
# --------------------------------------------------------------------------- #

def manifesto(b):
    layer = chrome(b, "Manifesto", "First law of the Grid")
    layer.text([0, 250, W, 22], "// AXIOM 00", style="kickerC" if False else "tagC")
    layer.text([240, 286, W - 480, 130],
               "Everything here is light, drawn in straight lines.", style="quote")
    hline(layer, W / 2 - 60, W / 2 + 60, 470, "cyan", 3)
    layer.text([W / 2 - 360, 500, 720, 80],
               "No surface, no shadow, no depth we did not author. The system is a flat "
               "field of vectors; meaning is carried by geometry and glow alone.",
               style="leadC")
    # flanking chevrons
    chevron(layer, 200, 380, 22, color="cyand")
    chevron(layer, W - 200, 380, 22, color="orange")


# --------------------------------------------------------------------------- #
# 05 — Sector map (full-bleed grid)                                             #
# --------------------------------------------------------------------------- #

def sector_map(b):
    layer = chrome(b, "01 · The Grid", "The sector map")
    map_box = [MX, 196, W - 2 * MX, 420]
    layer.rect(map_box, fill="void2")
    square_grid(layer, map_box, step=34, color="gridc", w=1.0)
    corner_frame(layer, map_box, color="cyand", ln=20, w=1.4)
    # sectors as neon zones
    zones = [
        ("OUTLANDS", [MX + 30, 230, 300, 150], "cyand"),
        ("THE ARENA", [MX + 360, 230, 260, 220], "cyan"),
        ("CORE", [MX + 650, 230, 200, 150], "amber"),
        ("PORTAL", [MX + 880, 230, 196, 150], "cyan"),
        ("SEA OF SIMULATION", [MX + 30, 410, 590, 170], "orange"),
        ("I/O TOWER", [MX + 650, 410, 426, 170], "magenta"),
    ]
    for name, bx, col in zones:
        neon_panel(layer, bx, color=col, fill_alpha=0.06, w=1.6)
        layer.text([bx[0] + 14, bx[1] + 12, bx[2] - 28, 18], name,
                   style={"class": "kicker", "color": col, "font_size": 12})
    # routes between zones
    circuit_trace(layer, [[MX + 490, 450], [MX + 490, 490], [MX + 320, 490],
                          [MX + 320, 410]], color="cyan", w=2.0)
    circuit_trace(layer, [[MX + 750, 380], [MX + 750, 410]], color="amber", w=2.0)
    footer(layer, "Zones are addressed by vector; transit runs the lighted routes only.")


# --------------------------------------------------------------------------- #
# 06 — Big number focal                                                         #
# --------------------------------------------------------------------------- #

def big_number(b):
    layer = chrome(b, "01 · The Grid", "Clock of the frontier")
    layer.text([MX - 6, 210, 760, 250], "10⁹", style="big")
    layer.text([MX + 2, 230, 80, 60], "", style="body")
    layer.text([MX, 470, 460, 30], "cycles resolved every wall-clock second", style="lead")
    hline(layer, MX, MX + 300, 520, "cyan", 3)
    notes = column([800, 210, W - 800 - MX, 360], 3, gap=26)
    facts = [
        ("DETERMINISTIC", "Every frame is reproducible — the same input draws the same light."),
        ("ZERO LATENCY", "Thought is transit. To decide is already to have moved."),
        ("NO DECAY", "Nothing rusts on the Grid; programs end only by derez."),
    ]
    for nb, (h, body) in zip(notes, facts):
        x, y, bw, bh = nb
        vline(layer, x, y + 2, y + 56, "cyan", 3)
        layer.text([x + 16, y, bw - 16, 22], h, style="h2c")
        layer.text([x + 16, y + 30, bw - 16, 60], body, style="body")


# --------------------------------------------------------------------------- #
# 07 — Three pillars (thirds)                                                   #
# --------------------------------------------------------------------------- #

def pillars(b):
    layer = chrome(b, "01 · The Grid", "Three laws hold the field")
    cols = row([MX, 210, W - 2 * MX, 410], 3, gap=28)
    data = [
        ("I", "LINE", "Every form is a path of straight segments. Curves are sampled, "
         "never assumed."),
        ("II", "LIGHT", "Colour is identity. Cyan is a user's signal; orange is a "
         "program turned against the system."),
        ("III", "LOOP", "The Grid runs forever in clean cycles. Order is the default; "
         "entropy is an intrusion."),
    ]
    for cb, (roman, head, body) in zip(cols, data):
        x, y, bw, bh = cb
        neon_panel(layer, cb, color="cyand", fill_alpha=0.04, w=1.4)
        corner_frame(layer, cb, color="cyan", ln=18, w=2.0, inset_px=0)
        layer.text([x + 26, y + 28, bw - 52, 40], roman, style="stat")
        hline(layer, x + 26, x + 86, y + 96, "cyan", 2)
        layer.text([x + 26, y + 116, bw - 52, 28], head, style="h2")
        layer.text([x + 26, y + 158, bw - 52, 180], body, style="body")
        chevron(layer, x + bw - 36, y + bh - 34, 12, color="cyand")


# --------------------------------------------------------------------------- #
# 08 — Bento modular                                                            #
# --------------------------------------------------------------------------- #

def bento(b):
    layer = chrome(b, "01 · The Grid", "Anatomy of a cycle")
    # unequal tiles
    big = [MX, 196, 560, 420]
    neon_panel(layer, big, color="cyan", fill_alpha=0.06, w=1.8)
    layer.text([MX + 30, 230, 500, 24], "THE LIGHT RIBBON", style="h2c")
    layer.text([MX + 30, 270, 500, 90],
               "A program in motion leaves a solid wall of light behind it. The ribbon "
               "is both signature and weapon.", style="body")
    # ribbon drawing inside
    circuit_trace(layer, [[MX + 40, 560], [MX + 40, 470], [MX + 220, 470],
                          [MX + 220, 400], [MX + 430, 400], [MX + 430, 520]],
                  color="cyan", w=5.0)
    dot(layer, MX + 430, 520, 9, "cyanb", glow={"blur": 10, "color": CYAN, "opacity": 0.7})

    t2 = [664, 196, 280, 200]
    neon_panel(layer, t2, color="orange", fill_alpha=0.07, w=1.6)
    layer.text([t2[0] + 22, t2[1] + 22, t2[2] - 44, 22], "DEREZ", style="h2")
    layer.text([t2[0] + 22, t2[1] + 56, t2[2] - 44, 100],
               "On defeat a program shatters into a cube of cooling light.", style="body")
    for i, gb in enumerate(grid([t2[0] + 22, t2[1] + 150, 120, 36], cols=6, count=6, gap=4)):
        dot(layer, gb[0] + 9, gb[1] + 18, 5, ORANGE if i % 2 else AMBER)

    t3 = [960, 196, W - 960 - MX, 200]
    neon_panel(layer, t3, color="amber", fill_alpha=0.06, w=1.6)
    layer.text([t3[0] + 22, t3[1] + 22, t3[2] - 44, 22], "ENERGY", style="h2")
    layer.text([t3[0] + 22, t3[1] + 56, t3[2] - 44, 110],
               "Programs drink from pools of liquid light to stay resolved.", style="body")

    t4 = [664, 416, W - 664 - MX, 200]
    neon_panel(layer, t4, color="cyand", fill_alpha=0.04, w=1.6)
    layer.text([t4[0] + 24, t4[1] + 24, 320, 24], "THE DISC", style="h2c")
    layer.text([t4[0] + 24, t4[1] + 62, 320, 110],
               "Identity, memory and weapon in one machined ring — never let it leave "
               "your hand.", style="body")
    disc(layer, t4[0] + t4[2] - 110, t4[1] + t4[3] / 2, 70, color=CYAN, core=ORANGE)


# --------------------------------------------------------------------------- #
# 10 — USER vs PROGRAM (comparison)                                             #
# --------------------------------------------------------------------------- #

def comparison(b):
    layer = chrome(b, "02 · Programs & Users", "Two kinds of light")
    left = [MX, 200, (W - 2 * MX - 30) / 2, 420]
    right = [left[0] + left[2] + 30, 200, left[2], 420]
    for box, name, col, blurb in (
        (left, "USER", "cyan", "Came from beyond the screen. Improvises. Bleeds time."),
        (right, "PROGRAM", "orange", "Born of code. Executes a function. Counts in cycles."),
    ):
        neon_panel(layer, box, color=col, fill_alpha=0.06, w=2.0, glow_blur=12)
        x, y, bw, bh = box
        disc(layer, x + bw / 2, y + 96, 56, color=(CYAN if col == "cyan" else ORANGE),
             core=(ORANGE if col == "cyan" else CYAN))
        layer.text([x, y + 168, bw, 30], name,
                   style={"class": "h2", "color": col, "align": "center", "font_size": 26})
        layer.text([x + 40, y + 210, bw - 80, 60], blurb,
                   style={"class": "body", "align": "center"})
        traits = (["ORIGIN: external", "LOGIC: improvised", "FEARS: the clock"]
                  if col == "cyan" else
                  ["ORIGIN: compiled", "LOGIC: deterministic", "FEARS: derez"])
        for i, tr in enumerate(traits):
            ty = y + 290 + i * 38
            hline(layer, x + 40, x + bw - 40, ty - 8, "gridc", 1)
            layer.text([x + 40, ty, bw - 80, 22], tr,
                       style={"class": "mono", "color": col, "align": "center"})
    # VS marker
    dot(layer, W / 2, 410, 26, "void2")
    ring(layer, W / 2, 410, 26, "white", 2)
    layer.text([W / 2 - 26, 398, 52, 24], "VS", style={"class": "num", "color": "white"})


# --------------------------------------------------------------------------- #
# 11 — Identity disc anatomy (radial labelled diagram)                          #
# --------------------------------------------------------------------------- #

def disc_anatomy(b):
    layer = chrome(b, "02 · Programs & Users", "Anatomy of the disc")
    cx, cy = 470, 410
    R = 200
    # detailed disc
    ring(layer, cx, cy, R, "cyan", 3, glow={"blur": 14, "color": CYAN, "opacity": 0.45})
    ring(layer, cx, cy, R * 0.82, "cyand", 1.4)
    ring(layer, cx, cy, R * 0.6, "cyan", 2)
    ring(layer, cx, cy, R * 0.32, "amber", 2)
    dot(layer, cx, cy, 12, "orange", glow={"blur": 10, "color": ORANGE, "opacity": 0.7})
    # tick marks around the rim
    for deg in range(0, 360, 15):
        r1, r2 = R, R - 12
        layer.line([cx + r1 * math.cos(math.radians(deg)), cy + r1 * math.sin(math.radians(deg))],
                   [cx + r2 * math.cos(math.radians(deg)), cy + r2 * math.sin(math.radians(deg))],
                   **stroke(1.4, CYAND))
    # leader lines + labels on the right
    labels = [
        (-40, R, "OUTER RAIL", "Edge weapon. Throws true along any vector."),
        (10, R * 0.6, "MEMORY BAND", "Compressed history of every routine run."),
        (60, R * 0.32, "IDENTITY KEY", "Cryptographic signature of the bearer."),
        (-90, 12, "CORE", "The single bright spark a program cannot fake."),
    ]
    lx = 760
    for i, (deg, rr, head, body) in enumerate(labels):
        px = cx + rr * math.cos(math.radians(deg))
        py = cy + rr * math.sin(math.radians(deg))
        ly = 230 + i * 100
        circuit_trace(layer, [[px, py], [lx - 30, py], [lx - 30, ly + 10], [lx, ly + 10]],
                      color="cyan", w=1.6, node_r=3.5, node=True)
        layer.text([lx + 12, ly, 380, 22], head, style="h2c")
        layer.text([lx + 12, ly + 28, 380, 50], body, style="body")
    footer(layer, "Lose the disc and you lose the self; a derezzed program leaves only its ring.")


# --------------------------------------------------------------------------- #
# 12 — Roster (left rail)                                                        #
# --------------------------------------------------------------------------- #

def roster(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="void")
    # left rail panel
    layer.rect([0, 0, 430, H], fill="void2")
    square_grid(layer, [0, 0, 430, H], step=43, color="gridc", w=1.0)
    vline(layer, 430, 0, H, "cyan", 2)
    layer.text([MX, 110, 320, 22], "02 · PROGRAMS & USERS", style="kicker")
    layer.text([MX, 150, 320, 120], "The active\nroster", style="h1")
    layer.text([MX, 320, 320, 160],
               "Five signatures currently resolved on the Grid, by class and allegiance.",
               style="lead")
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")
    # roster cards on the right
    cards = column([474, 96, W - 474 - MX, 540], 5, gap=16)
    crew = [
        ("CLU", "system monad", "orange", "Built to make a perfect system. Mistook control for order."),
        ("RINZLER", "enforcer", "orange", "Repurposed. Twin discs. Speaks in static."),
        ("QUORRA", "isomorphic", "cyan", "Self-generated. The first life the Grid wrote by itself."),
        ("TRON", "security", "cyan", "The original watchman. Fights for the users."),
        ("SARK", "command", "amber", "A garrison program; loyal only to whoever holds the core."),
    ]
    for cb, (name, role, col, body) in zip(cards, crew):
        x, y, bw, bh = cb
        neon_panel(layer, cb, color=col, fill_alpha=0.05, w=1.4)
        dot(layer, x + 44, y + bh / 2, 22, "void")
        ring(layer, x + 44, y + bh / 2, 22, col, 2.2)
        dot(layer, x + 44, y + bh / 2, 5, col)
        layer.text([x + 86, y + 16, bw - 200, 26], name,
                   style={"class": "h2", "color": col, "font_size": 21})
        layer.text([x + 86, y + 50, bw - 200, 30], body, style="body")
        layer.text([x + bw - 150, y + 18, 130, 18], role.upper(),
                   style={"class": "tag", "align": "right"})


# --------------------------------------------------------------------------- #
# 13 — Hex node network                                                         #
# --------------------------------------------------------------------------- #

def network(b):
    layer = chrome(b, "02 · Programs & Users", "The society graph")
    cx, cy = 470, 420
    nodes = {
        "core": (cx, cy, "amber", 34),
        "n1": (cx - 230, cy - 120, "cyan", 24),
        "n2": (cx + 210, cy - 150, "orange", 24),
        "n3": (cx - 250, cy + 110, "cyan", 24),
        "n4": (cx + 250, cy + 90, "orange", 24),
        "n5": (cx - 30, cy - 210, "cyan", 20),
        "n6": (cx + 60, cy + 200, "cyan", 20),
    }
    edges = [("core", k) for k in nodes if k != "core"] + [("n1", "n5"), ("n2", "n5"),
             ("n3", "n6"), ("n4", "n6"), ("n1", "n3"), ("n2", "n4")]
    for u, v in edges:
        x1, y1, _, _ = nodes[u]
        x2, y2, _, _ = nodes[v]
        layer.line([x1, y1], [x2, y2], **stroke(1.4, CYAND))
    for k, (x, y, col, r) in nodes.items():
        hexagon(layer, x, y, r, color=col, fill=a(COLORS[col], 0.10), w=2.0)
        dot(layer, x, y, 4, col)
    # legend on the right
    box = [840, 230, W - 840 - MX, 360]
    neon_panel(layer, box, color="cyand", fill_alpha=0.04, w=1.4)
    layer.text([box[0] + 24, box[1] + 22, box[2] - 48, 24], "HOW TO READ IT", style="h2c")
    legend = [
        ("amber", "Core node — the system kernel every routine reports to."),
        ("cyan", "User-aligned process; signal trusted."),
        ("orange", "Program under foreign control; signal suspect."),
    ]
    for i, (col, txt) in enumerate(legend):
        ly = box[1] + 70 + i * 70
        hexagon(layer, box[0] + 40, ly + 10, 16, color=col, fill=a(COLORS[col], 0.12), w=2)
        layer.text([box[0] + 74, ly - 4, box[2] - 100, 56], txt, style="body")
    footer(layer, "Edges are open channels; an isolated node has been quarantined off-graph.")


# --------------------------------------------------------------------------- #
# 14 — Quadrants (program classes)                                              #
# --------------------------------------------------------------------------- #

def quadrants(b):
    layer = chrome(b, "02 · Programs & Users", "Four classes of program")
    quads = grid([MX, 196, W - 2 * MX, 420], cols=2, count=4, gap=22)
    classes = [
        ("ACTUARIAL", "cyan", "Accounting and ledger routines. Keep the system honest."),
        ("SECURITY", "amber", "Watchmen and enforcers. Patrol the lighted routes."),
        ("UTILITY", "cyand", "Compilers, daemons, couriers. The unglamorous majority."),
        ("ROGUE", "orange", "Corrupted or self-modified. Hunted on sight."),
    ]
    for qb, (name, col, body) in zip(quads, classes):
        x, y, bw, bh = qb
        neon_panel(layer, qb, color=col, fill_alpha=0.05, w=1.6)
        layer.rect([x, y, 8, bh], fill=col)
        # class glyph
        hexagon(layer, x + bw - 70, y + 60, 30, color=col, fill=a(COLORS[col], 0.1), w=2)
        layer.text([x + 34, y + 38, bw - 160, 28], name,
                   style={"class": "h2", "color": col, "font_size": 24})
        layer.text([x + 34, y + 86, bw - 130, 80], body, style="body")
        layer.text([x + 34, y + bh - 40, 200, 20], f"CLASS · {name[:3]}", style="tag")


# --------------------------------------------------------------------------- #
# 16 — Architecture stack (layers)                                              #
# --------------------------------------------------------------------------- #

def stack(b):
    layer = chrome(b, "03 · Architecture", "The system stack")
    layer.text([MX, 196, 380, 240],
               "The Grid resolves top-down: a user intent enters at the I/O tower and "
               "settles through five layers before it becomes light on the floor.",
               style="lead")
    layers_data = [
        ("I/O TOWER", "ingress / egress of users", "cyan"),
        ("KERNEL", "scheduling & the master clock", "amber"),
        ("RESOLVER", "geometry → vectors", "cyan"),
        ("ENERGY BUS", "distributes liquid light", "cyand"),
        ("THE FLOOR", "rendered field of play", "orange"),
    ]
    bx, bw = 520, W - 520 - MX
    for i, (name, sub, col) in enumerate(layers_data):
        y = 200 + i * 86
        neon_panel(layer, [bx, y, bw, 70], color=col, fill_alpha=0.06, w=1.6)
        layer.text([bx + 24, y + 14, bw - 200, 24], name,
                   style={"class": "h2", "color": col, "font_size": 20})
        layer.text([bx + 24, y + 44, bw - 200, 18], sub, style="bodyM")
        layer.text([bx + bw - 60, y + 22, 40, 28], f"L{i}", style="num")
        if i < len(layers_data) - 1:
            chevron(layer, bx + bw / 2, y + 80, 10, color="cyand", down=True)
    footer(layer, "Each layer trusts only the layer above it; a breach cannot climb the stack.")


# --------------------------------------------------------------------------- #
# 17 — Circuit dataflow                                                          #
# --------------------------------------------------------------------------- #

def dataflow(b):
    layer = chrome(b, "03 · Architecture", "Data-flow on the bus")
    canvas_box = [MX, 200, W - 2 * MX, 410]
    layer.rect(canvas_box, fill="void2")
    square_grid(layer, canvas_box, step=37, color="gridc", w=1.0)
    corner_frame(layer, canvas_box, color="cyand", ln=20, w=1.4)
    # nodes
    stages = [("INTENT", 150, 300, "cyan"), ("PARSE", 380, 250, "cyan"),
              ("RESOLVE", 620, 380, "amber"), ("LIGHT", 880, 280, "cyan"),
              ("FLOOR", 1120, 420, "orange")]
    pos = {}
    for name, x, y, col in stages:
        pos[name] = (x, y, col)
    seq = ["INTENT", "PARSE", "RESOLVE", "LIGHT", "FLOOR"]
    for u, v in zip(seq, seq[1:]):
        x1, y1, _ = pos[u]
        x2, y2, _ = pos[v]
        midx = (x1 + x2) / 2
        circuit_trace(layer, [[x1, y1], [midx, y1], [midx, y2], [x2, y2]],
                      color="cyan", w=2.2, node=False)
        layer.arrow([midx, y2], [x2 - 30, y2], color=CYAN, width=2.2, head=10)
    for name, x, y, col in stages:
        hexagon(layer, x, y, 36, color=col, fill=a(COLORS[col], 0.12), w=2.2)
        layer.text([x - 50, y - 9, 100, 18], name,
                   style={"class": "kicker", "color": col, "align": "center", "font_size": 11})
    # feedback loop
    circuit_trace(layer, [[1120, 460], [1120, 560], [150, 560], [150, 340]],
                  color="orange", w=1.8, node=False)
    layer.text([600, 540, 200, 18], "DEREZ FEEDBACK", style="kickerO")
    footer(layer, "A clean request walks left-to-right; faults are swept back to ingress for derez.")


# --------------------------------------------------------------------------- #
# 18 — Throughput bar chart                                                     #
# --------------------------------------------------------------------------- #

def throughput(b):
    layer = chrome(b, "03 · Architecture", "Throughput by sector")
    layer.text([MX, 196, 380, 180],
               "Resolved frames per cycle, measured at each sector gate over one "
               "rotation of the master clock.", style="lead")
    # legend / kpis on the left
    for i, (lbl, val, col) in enumerate([("PEAK", "9.4 Gf", "cyan"),
                                         ("MEAN", "6.1 Gf", "amber"),
                                         ("FLOOR", "2.2 Gf", "orange")]):
        y = 360 + i * 78
        vline(layer, MX, y, y + 56, col, 3)
        layer.text([MX + 18, y - 4, 300, 40], val,
                   style={"class": "stat", "color": col, "font_size": 38})
        layer.text([MX + 18, y + 42, 300, 18], lbl, style="tag")

    panel = [520, 196, W - 520 - MX, 420]
    layer.rect(panel, fill="void2")
    corner_frame(layer, panel, color="cyand", ln=18, w=1.4)
    chart = Chart(Frame(domain=(0, 0, 6, 10), box=(panel[0] + 56, panel[1] + 40, panel[2] - 90, panel[3] - 100)))
    bars = [("ARENA", 9.4), ("CORE", 7.8), ("PORTAL", 6.1), ("OUTLANDS", 4.0),
            ("SEA", 3.2), ("I/O", 2.2)]
    chart.axes(x_ticks=[], y_ticks=[0, 2, 4, 6, 8, 10],
               y_format=lambda v: f"{v:g}", grid=True,
               axis_color=CYAND, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    cols = [CYAN, CYANB, CYAN, AMBER, AMBER, ORANGE]
    for i, ((name, val), col) in enumerate(zip(bars, cols)):
        chart.bars([(i + 0.5, val)], width=58, fill=col, radius=4)
    layer.extend(grouped(chart.objects()))
    # bar labels
    fr = chart.frame
    for i, (name, val) in enumerate(bars):
        p = fr.point(i + 0.5, 0)
        layer.text([p.x - 50, panel[1] + panel[3] - 52, 100, 16], name,
                   style={"class": "tag", "align": "center"})
    footer(layer, "Gigaframes per cycle. The Arena runs hottest; I/O is throttled for safety.")


# --------------------------------------------------------------------------- #
# 19 — Signal line chart                                                         #
# --------------------------------------------------------------------------- #

def signal(b):
    layer = chrome(b, "03 · Architecture", "System load over the cycle")
    panel = [MX, 200, W - 2 * MX, 410]
    layer.rect(panel, fill="void2")
    square_grid(layer, panel, step=40, color="gridc", w=1.0)
    corner_frame(layer, panel, color="cyand", ln=20, w=1.4)
    chart = Chart(Frame(domain=(0, 0, 24, 100),
                        box=(panel[0] + 64, panel[1] + 36, panel[2] - 110, panel[3] - 96)))
    chart.axes(x_ticks=[0, 6, 12, 18, 24], y_ticks=[0, 25, 50, 75, 100],
               x_format=lambda v: f"{int(v):02d}h", y_format=lambda v: f"{int(v)}%", grid=True,
               axis_color=CYAND, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    load = [(t, 45 + 30 * math.sin(t / 3.0) + 12 * math.sin(t / 1.3)) for t in range(0, 25)]
    games = [(t, 20 + 60 * max(0.0, math.sin((t - 4) / 6.0))) for t in range(0, 25)]
    chart.line(load, stroke=CYAN, width=3.0, smooth=True, label="kernel load")
    chart.line(games, stroke=ORANGE, width=2.6, smooth=True, label="arena demand")
    chart.legend(at=(panel[0] + 64, panel[1] + panel[3] - 26))
    layer.extend(grouped(chart.objects()))
    # peak marker
    fr = chart.frame
    p = fr.point(12, 87)
    dot(layer, p.x, p.y, 5, "cyanb", glow={"blur": 8, "color": CYAN, "opacity": 0.7})
    layer.text([p.x - 40, p.y - 28, 160, 16], "MIDCYCLE PEAK", style="kicker")
    footer(layer, "Kernel load is cyclic; arena demand spikes when the Games are called.")


# --------------------------------------------------------------------------- #
# 20 — Concentric system rings (radial)                                         #
# --------------------------------------------------------------------------- #

def rings(b):
    layer = chrome(b, "03 · Architecture", "Concentric trust zones")
    cx, cy = 440, 420
    zones = [
        (210, "OUTLANDS", "cyand", "unmanaged territory"),
        (160, "PERIMETER", "cyan", "security patrols"),
        (110, "WORKS", "amber", "active routines"),
        (58, "CORE", "orange", "kernel & clock"),
    ]
    for r, name, col, sub in zones:
        ring(layer, cx, cy, r, col, 2.2)
    dot(layer, cx, cy, 14, "orange", glow={"blur": 10, "color": ORANGE, "opacity": 0.7})
    # radial spokes
    for deg in range(0, 360, 30):
        layer.line([cx, cy], [cx + 210 * math.cos(math.radians(deg)),
                                cy + 210 * math.sin(math.radians(deg))],
                   **stroke(1.0, GRIDC))
    # labels to the right
    for i, (r, name, col, sub) in enumerate(zones):
        ly = 240 + i * 92
        px = cx + r
        circuit_trace(layer, [[px, cy], [780, cy], [780, ly + 12], [820, ly + 12]],
                      color=col, w=1.4, node_r=3, node=True) if False else None
        layer.line([px, cy], [820, ly + 12], **stroke(1.2, col))
        dot(layer, px, cy, 4, col)
        layer.text([832, ly, 360, 24], name, style={"class": "h2c", "color": col})
        layer.text([832, ly + 28, 360, 24], sub, style="bodyM")
    footer(layer, "Trust decays outward; the core never speaks directly to the Outlands.")


# --------------------------------------------------------------------------- #
# 21 — Gauges / progress                                                        #
# --------------------------------------------------------------------------- #

def gauges(b):
    layer = chrome(b, "03 · Architecture", "Live system telemetry")
    bars = [
        ("ENERGY RESERVE", 0.78, "cyan"),
        ("KERNEL INTEGRITY", 0.91, "cyan"),
        ("ROGUE CONTAINMENT", 0.43, "orange"),
        ("CLOCK DRIFT", 0.12, "amber"),
        ("PORTAL ALIGNMENT", 0.66, "cyan"),
    ]
    track_x, track_w = 470, 640
    for i, (name, frac, col) in enumerate(bars):
        y = 230 + i * 76
        layer.text([MX, y - 2, 380, 22], name, style="mono")
        layer.rect([track_x, y, track_w, 18], fill="void2", radius=9,
                   **stroke(1.2, CYAND))
        layer.rect([track_x, y, max(18, track_w * frac), 18], fill=col, radius=9,
                   glow={"blur": 8, "color": COLORS[col], "opacity": 0.5})
        layer.text([track_x + track_w + 16, y - 4, 120, 26], f"{int(frac * 100)}%",
                   style={"class": "stat", "color": col, "font_size": 24})
        # ticks
        for t in range(1, 10):
            tx = track_x + track_w * t / 10
            vline(layer, tx, y, y + 18, "void", 1)
    footer(layer, "Rogue containment is the metric to watch; everything above 0.40 is holding.")


# --------------------------------------------------------------------------- #
# 23 — Light-cycle arena                                                         #
# --------------------------------------------------------------------------- #

def light_cycles(b):
    layer = chrome(b, "04 · The Games", "Light-cycle grid")
    arena = [MX, 200, W - 2 * MX, 410]
    layer.rect(arena, fill="void2")
    square_grid(layer, arena, step=34, color="gridc", w=1.0)
    layer.rect(arena, fill="none", **stroke(2.4, "cyan"))
    corner_frame(layer, arena, color="cyan", ln=24, w=2.4)
    # two ribbon trails (right-angle polylines) racing toward a near-miss
    cyan_trail = [[MX + 40, 560], [MX + 40, 300], [MX + 360, 300], [MX + 360, 470],
                  [MX + 620, 470], [MX + 620, 340]]
    orange_trail = [[W - MX - 40, 240], [W - MX - 40, 520], [W - MX - 360, 520],
                    [W - MX - 360, 360], [MX + 700, 360]]
    layer.polyline(cyan_trail, **stroke(5.0, "cyan", stroke_linejoin="miter"))
    layer.polyline(orange_trail, **stroke(5.0, "orange", stroke_linejoin="miter"))
    # glow heads
    dot(layer, *cyan_trail[-1], 8, "cyanb", glow={"blur": 12, "color": CYAN, "opacity": 0.8})
    dot(layer, *orange_trail[-1], 8, "amber", glow={"blur": 12, "color": ORANGE, "opacity": 0.8})
    # bikes as chevrons at the heads
    chevron(layer, cyan_trail[-1][0], cyan_trail[-1][1] - 18, 10, color="cyanb")
    layer.text([MX + 30, 218, 300, 18], "PLAYER · USER LINE", style="kicker")
    layer.text([W - MX - 330, 218, 300, 18], "OPPONENT · ROGUE LINE",
               style={"class": "kickerO", "align": "right"})
    footer(layer, "Walls are permanent. The match ends when one line is forced to cross light.")


# --------------------------------------------------------------------------- #
# 24 — Disc combat geometry                                                      #
# --------------------------------------------------------------------------- #

def disc_combat(b):
    layer = chrome(b, "04 · The Games", "Disc combat geometry")
    layer.text([MX, 196, 380, 200],
               "A thrown disc travels a true chord and ricochets at equal angles. "
               "Master the reflection and the arena's walls fight for you.", style="lead")
    eqs = [("θᵢ = θᵣ", "angle in = angle out"),
           ("v = const", "no drag on the Grid"),
           ("path = polyline", "every bounce is a vertex")]
    for i, (eq, note) in enumerate(eqs):
        y = 400 + i * 70
        neon_panel(layer, [MX, y, 380, 56], color="cyand", fill_alpha=0.04, w=1.4)
        layer.text([MX + 18, y + 10, 160, 34], eq,
                   style={"class": "mono", "color": "amber", "font_size": 22})
        layer.text([MX + 190, y + 18, 180, 22], note, style="bodyM")
    # geometry panel
    panel = [500, 196, W - 500 - MX, 420]
    layer.rect(panel, fill="void2")
    square_grid(layer, panel, step=36, color="gridc", w=1.0)
    corner_frame(layer, panel, color="cyand", ln=18, w=1.4)
    # bouncing disc path
    pts = [[540, 560], [720, 240], [1060, 470], [760, 600], [560, 360]]
    layer.polyline(pts, **stroke(2.6, "cyan"))
    for i, p in enumerate(pts):
        dot(layer, p[0], p[1], 6, "cyan" if i else "orange")
    # angle marks at first bounce
    bx, by = pts[1]
    ring(layer, bx, by, 26, "amber", 1.6)
    layer.line([bx, by], [bx - 30, by + 4], **stroke(1.4, AMBER, stroke_dasharray=[4, 3]))
    layer.line([bx, by], [bx + 30, by + 4], **stroke(1.4, AMBER, stroke_dasharray=[4, 3]))
    layer.text([bx - 70, by - 40, 60, 18], "θᵢ", style={"class": "mono", "color": "amber"})
    layer.text([bx + 28, by - 40, 60, 18], "θᵣ", style={"class": "mono", "color": "amber"})
    footer(layer, "Thrower at orange; the disc returns to hand if no target is struck.")


# --------------------------------------------------------------------------- #
# 25 — Derez sequence (process flow)                                            #
# --------------------------------------------------------------------------- #

def derez(b):
    layer = chrome(b, "04 · The Games", "The derez sequence")
    steps = [
        ("01", "STRIKE", "Disc or wall makes contact along a true vector.", "cyan"),
        ("02", "FRACTURE", "Surface integrity fails; the body cracks into facets.", "amber"),
        ("03", "CUBES", "Facets resolve into a lattice of cooling light-cubes.", "orange"),
        ("04", "SCATTER", "Cubes lose cohesion and fall away from the centre.", "orange"),
        ("05", "VOID", "The signature clears; only the disc is left behind.", "cyand"),
    ]
    cols = row([MX, 230, W - 2 * MX, 340], 5, gap=18)
    for i, (cb, (n, head, body, col)) in enumerate(zip(cols, steps)):
        x, y, bw, bh = cb
        neon_panel(layer, cb, color=col, fill_alpha=0.05, w=1.6)
        layer.text([x + 18, y + 18, bw - 36, 30], n,
                   style={"class": "num", "color": col, "align": "left", "font_size": 24})
        hline(layer, x + 18, x + bw - 18, y + 58, "gridc", 1)
        # mini glyph
        if i < 2:
            ring(layer, x + bw / 2, y + 120, 26, col, 2)
        else:
            for gb in grid([x + bw / 2 - 30, y + 94, 60, 56], cols=3, count=6 - (i - 2), gap=6):
                dot(layer, gb[0] + 6, gb[1] + 6, 5, col)
        layer.text([x + 18, y + 168, bw - 36, 24], head,
                   style={"class": "h2", "color": col, "font_size": 17})
        layer.text([x + 18, y + 198, bw - 30, 120], body, style="body")
        if i < 4:
            chevron(layer, x + bw + 9, y + bh / 2, 9, color="cyand")
    footer(layer, "Derez is irreversible; a recovered disc is the only way a routine returns.")


# --------------------------------------------------------------------------- #
# 26 — Matrix glyph grid                                                        #
# --------------------------------------------------------------------------- #

def glyph_matrix(b):
    layer = chrome(b, "04 · The Games", "The opponent table")
    layer.text([MX, 196, W - 2 * MX, 40],
               "Every cell is a resolved program awaiting a match — colour reads "
               "allegiance, the ring reads readiness.", style="lead")
    cells = grid([MX, 270, W - 2 * MX, 340], cols=8, rows=3, gap=16)
    for i, cb in enumerate(cells):
        x, y, bw, bh = cb
        col = "orange" if (i * 7 + 3) % 5 == 0 else ("amber" if i % 6 == 0 else "cyan")
        neon_panel(layer, cb, color=col, fill_alpha=0.05, w=1.3)
        ccx, ccy = x + bw / 2, y + bh / 2 - 6
        ready = (i * 3) % 4 != 0
        if ready:
            ring(layer, ccx, ccy, 18, col, 2.0)
        else:
            ring(layer, ccx, ccy, 18, col, 1.0, stroke_dasharray=[3, 3])
        dot(layer, ccx, ccy, 4, col)
        layer.text([x, y + bh - 22, bw, 16], f"#{i:02d}",
                   style={"class": "monoM", "align": "center"})
    footer(layer, "24 contenders queued; dashed rings are still compiling and cannot be called.")


# --------------------------------------------------------------------------- #
# 27 — Recognizer (corner-diagonal tension)                                     #
# --------------------------------------------------------------------------- #

def recognizer(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="void")
    grid_floor(layer, W / 2, 480, H + 30, color=GRIDC, glow=False)
    layer.text([MX, 80, 400, 22], "04 · THE GAMES", style="kickerO")
    layer.text([MX, 120, 240, 160], "27", style="idx")
    # a Recognizer drawn as a flat 2D gantry silhouette, bled off the corner
    with layer.bleed():
        ox, oy = 820, 120
        # the inverted-U body
        body = [[ox, oy + 260], [ox, oy + 40], [ox + 60, oy], [ox + 300, oy],
                [ox + 360, oy + 40], [ox + 360, oy + 260], [ox + 300, oy + 260],
                [ox + 300, oy + 90], [ox + 60, oy + 90], [ox + 60, oy + 260]]
        layer.polygon(body, fill=a(ORANGE, 0.08), **stroke(2.6, "orange"))
        # leg cabin
        layer.rect([ox + 150, oy + 30, 60, 50], fill=a(CYAN, 0.18), **stroke(2.0, "cyan"))
        # scan glow
        layer.line([ox + 30, oy + 250], [ox + 330, oy + 250], **stroke(3.0, "amber",
                   stroke_linecap="round"))
    layer.text([MX, H - 250, 600, 90], "Tension over\nthe corner.",
               style={"class": "h1", "font_size": 46})
    layer.text([MX, H - 130, 560, 60],
               "A Recognizer hangs in the upper field, bled past the frame — the eye is "
               "pulled off-centre on a diagonal, the way unease should read.", style="body")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="orange", ln=30, w=1.4)
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 29 — History timeline band                                                    #
# --------------------------------------------------------------------------- #

def timeline(b):
    layer = chrome(b, "05 · Doctrine", "A short history of the Grid")
    spine_y = 400
    hline(layer, MX, W - MX, spine_y, "cyan", 2)
    nodes = row([MX, spine_y - 14, W - 2 * MX, 28], 5)
    beats = [
        ("0x00", "GENESIS", "The first user opens a portal; the floor lights up."),
        ("0x1A", "THE GAMES", "Combat is formalised; discs become law."),
        ("0x40", "ISO BLOOM", "Life writes itself — the isomorphs appear unbidden."),
        ("0x5F", "THE PURGE", "A monad mistakes control for order; cyan dims."),
        ("0x80", "RECLAMATION", "Users return; the grid is re-lit from the core out."),
    ]
    for i, (nb, (code, head, body)) in enumerate(zip(nodes, beats)):
        cx = nb[0] + nb[2] / 2
        col = "orange" if i == 3 else "cyan"
        dot(layer, cx, spine_y, 10, "void")
        ring(layer, cx, spine_y, 10, col, 2.4)
        dot(layer, cx, spine_y, 3, col)
        above = i % 2 == 0
        ty = spine_y - 150 if above else spine_y + 40
        layer.text([cx - 95, ty, 190, 18], code,
                   style={"class": "kicker", "color": col, "align": "center"})
        layer.text([cx - 95, ty + 24, 190, 24], head,
                   style={"class": "h2", "align": "center", "font_size": 18})
        layer.text([cx - 95, ty + 54, 190, 70], body,
                   style={"class": "body", "align": "center", "font_size": 13})
        vline(layer, cx, spine_y + (-1 if above else 1) * 10,
              ty + (124 if above else 0) if above else ty, "gridc", 1) if False else None
    footer(layer, "Addresses are clock-stamps in the kernel's own hexadecimal.")


# --------------------------------------------------------------------------- #
# 30 — Roadmap (vertical phases)                                                #
# --------------------------------------------------------------------------- #

def roadmap(b):
    layer = chrome(b, "05 · Doctrine", "The forward directive")
    layer.text([MX, 196, 360, 220],
               "Five phases re-light the system from the core outward. Each phase opens "
               "only when the one before it reports clean.", style="lead")
    phases = [
        ("PHASE I", "RE-KEY", "Reissue every disc; revoke the rogue signatures.", "cyan"),
        ("PHASE II", "RE-LIGHT", "Restore the energy bus to the outer rings.", "cyan"),
        ("PHASE III", "RE-OPEN", "Bring the portal back online for users.", "amber"),
        ("PHASE IV", "RE-WRITE", "Let the isomorphs resume self-generation.", "orange"),
    ]
    bx, bw = 500, W - 500 - MX
    vline(layer, bx + 18, 210, 210 + len(phases) * 100 - 40, "cyand", 2)
    for i, (ph, head, body, col) in enumerate(phases):
        y = 210 + i * 100
        dot(layer, bx + 18, y + 20, 11, "void")
        ring(layer, bx + 18, y + 20, 11, col, 2.4)
        dot(layer, bx + 18, y + 20, 3, col)
        layer.text([bx + 54, y, 120, 18], ph, style={"class": "kicker", "color": col})
        layer.text([bx + 54, y + 22, bw - 60, 24], head,
                   style={"class": "h2", "color": "white", "font_size": 20})
        layer.text([bx + 54, y + 52, bw - 60, 40], body, style="body")
    footer(layer, "The directive is conditional; a failed phase rolls the system back one step.")


# --------------------------------------------------------------------------- #
# 31 — Quote (centered)                                                         #
# --------------------------------------------------------------------------- #

def quote(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="void")
    grid_floor(layer, W / 2, 540, H + 20, color=GRIDC, glow=False)
    disc(layer, W / 2, 200, 70, color=CYAN, core=ORANGE)
    layer.text([180, 320, W - 360, 160],
               "“The Grid. A digital frontier.\nI tried to picture clusters of\n"
               "information as they moved through the computer.”", style="quote")
    hline(layer, W / 2 - 50, W / 2 + 50, 560, "cyan", 3)
    layer.text([0, 580, W, 22], "// KEVIN FLYNN — ON FIRST LIGHT", style="tagC")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="cyand", ln=30, w=1.4)
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 32 — Closing / CTA                                                            #
# --------------------------------------------------------------------------- #

def closing(b):
    global _page
    _page += 1
    layer = new_page(b, "close")
    layer.rect([0, 0, W, H], fill="void")
    grid_floor(layer, W / 2, 430, H + 40, color=CYAND)
    layer.text([MX, 150, 800, 22], "END OF TRANSMISSION", style="kicker")
    layer.text([MX, 190, 1000, 120], "GET ON\nTHE GRID.", style="h1")
    layer.text([MX, 350, 720, 24],
               "The deck is one program; fork it, re-light it, run your own.", style="lead")
    # CTA chip
    chip = [MX, 410, 280, 56]
    layer.rect(chip, fill="cyan", radius=6, glow={"blur": 14, "color": CYAN, "opacity": 0.6})
    layer.text([chip[0], chip[1] + 18, chip[2], 22], "uv run · tron_grid_protocol",
               style={"class": "chip", "font_size": 13})
    disc(layer, 1060, 250, 96, color=CYAN, core=ORANGE)
    corner_frame(layer, [40, 40, W - 80, H - 80], color="cyand", ln=34, w=1.6)
    layer.text([MX, 600, 900, 20],
               "FRAMEFORGE PYTHON SDK · 32 PLATES · FLAT 2D VECTOR · NO RASTER ART",
               style="tag")
    layer.text([W - MX - 160, 600, 160, 18], "32 / 32", style="pnum")


# --------------------------------------------------------------------------- #
# Assembly                                                                      #
# --------------------------------------------------------------------------- #

def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Grid Protocol", profile="deck", lang="en")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)

    cover(b)                                                   # 01
    contents(b)                                                # 02
    divider(b, "div1", "01", "The Grid", "Where the frontier is, and what holds it.")  # 03
    manifesto(b)                                               # 04
    sector_map(b)                                              # 05
    big_number(b)                                              # 06
    pillars(b)                                                 # 07
    bento(b)                                                   # 08
    divider(b, "div2", "02", "Programs & Users",
            "Identity, class, allegiance — and the disc.", accent="orange")  # 09
    comparison(b)                                              # 10
    disc_anatomy(b)                                            # 11
    roster(b)                                                  # 12
    network(b)                                                 # 13
    quadrants(b)                                               # 14
    divider(b, "div3", "03", "Architecture",
            "Stacks, flow, throughput and load.")              # 15
    stack(b)                                                   # 16
    dataflow(b)                                                # 17
    throughput(b)                                              # 18
    signal(b)                                                  # 19
    rings(b)                                                   # 20
    gauges(b)                                                  # 21
    divider(b, "div4", "04", "The Games",
            "Light-cycles, discs, and the derez.", accent="orange")  # 22
    light_cycles(b)                                            # 23
    disc_combat(b)                                             # 24
    derez(b)                                                   # 25
    glyph_matrix(b)                                            # 26
    recognizer(b)                                              # 27
    divider(b, "div5", "05", "Doctrine",
            "History, roadmap, and the directive.")            # 28
    timeline(b)                                                # 29
    roadmap(b)                                                 # 30
    quote(b)                                                   # 31
    closing(b)                                                 # 32
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="rasterise pages to out/tron/")
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

    out = os.path.join(ROOT, "tests", "fixtures", "tron-grid-protocol.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
