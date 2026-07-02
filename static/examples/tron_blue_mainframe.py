#!/usr/bin/env python3
"""TRACE // THE BLUE MAINFRAME — a 30-slide deck in the *original* 1982 Tron
register, rendered entirely in flat 2D vector.

Where GRID PROTOCOL (examples/tron_grid_protocol.py) is the cool cinematic
"Legacy" look — soft discs, neon glow, light-cycle ribbons — this deck commits
to the colder, harder schematic register of the first film: an electric-blue
**circuit board**. Identity, shape language and diagrammation all change:

  * identity — electric blue + white on a near-black board, with a single MCP-red
    threat colour and no soft glow (crisp PCB strokes only);
  * shape language — orthogonal **traces, vias, bus rails, IC chips and bit-grids**
    instead of rings and ribbons;
  * diagrammation — PCB flow schematics, register/memory maps, control-panel
    tables and pipeline strips, leaning technical rather than cinematic.

Run from the repository root::

    uv run python examples/tron_blue_mainframe.py            # build + validate + write YAML
    uv run python examples/tron_blue_mainframe.py --render   # also rasterise to out/blue/
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

VOID = "#02040a"        # board substrate
PANEL = "#06121c"       # masked panel
PANEL2 = "#081a26"
BLUE = "#28c8ff"         # primary trace
BLUEB = "#9fe8ff"        # bright via
BLUED = "#1d6e94"        # dim trace / hairline
WHITE = "#f0faff"
RED = "#ff3b30"          # MCP / fault
AMBER = "#ffc14d"        # warning
GRIDC = "#0a2433"        # board grid
INK = "#88b9cf"          # body text
MUTE = "#4d7588"         # captions

SANS = ["DejaVu Sans", "Verdana", "sans-serif"]
MONO = ["DejaVu Sans Mono", "Consolas", "monospace"]

TOTAL = 30
_page = 0

COLORS = {
    "void": VOID, "panel": PANEL, "panel2": PANEL2, "blue": BLUE, "blueb": BLUEB,
    "blued": BLUED, "white": WHITE, "red": RED, "amber": AMBER, "gridc": GRIDC,
    "ink": INK, "mute": MUTE, "ghost": "#0c2230",
}

STYLES = {
    "kicker": dict(font_family=MONO, font_size=13, font_weight=700, color="blue",
                   text_transform="uppercase", letter_spacing=4),
    "kickerR": dict(font_family=MONO, font_size=13, font_weight=700, color="red",
                    text_transform="uppercase", letter_spacing=4),
    "tag": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                text_transform="uppercase", letter_spacing=3),
    "tagC": dict(font_family=MONO, font_size=11, font_weight=700, color="mute",
                 text_transform="uppercase", letter_spacing=3, align="center"),
    "pnum": dict(font_family=MONO, font_size=11, font_weight=700, color="blued",
                 letter_spacing=2, align="right"),
    "h1": dict(font_family=MONO, font_size=52, font_weight=700, color="white",
               letter_spacing=2, line_height=1.04),
    "h1C": dict(font_family=MONO, font_size=50, font_weight=700, color="white",
                letter_spacing=2, line_height=1.06, align="center"),
    "title": dict(font_family=SANS, font_size=31, font_weight=700, color="white",
                  letter_spacing=1, line_height=1.08),
    "h2": dict(font_family=SANS, font_size=21, font_weight=700, color="white",
               line_height=1.14),
    "h2b": dict(font_family=SANS, font_size=20, font_weight=700, color="blue",
                line_height=1.14),
    "big": dict(font_family=MONO, font_size=180, font_weight=700, color="blue",
                letter_spacing=-4, line_height=0.9),
    "idx": dict(font_family=MONO, font_size=140, font_weight=700, color="ghost",
                line_height=0.9),
    "lead": dict(font_family=SANS, font_size=19, font_weight=400, color="ink",
                 line_height=1.5),
    "body": dict(font_family=SANS, font_size=14.5, font_weight=400, color="ink",
                 line_height=1.5),
    "bodyM": dict(font_family=SANS, font_size=13.5, font_weight=400, color="mute",
                  line_height=1.5),
    "mono": dict(font_family=MONO, font_size=13, font_weight=400, color="blue",
                 line_height=1.5),
    "monoW": dict(font_family=MONO, font_size=13, font_weight=400, color="white",
                  line_height=1.5),
    "monoM": dict(font_family=MONO, font_size=12, font_weight=400, color="mute",
                  line_height=1.45),
    "stat": dict(font_family=MONO, font_size=42, font_weight=700, color="blue",
                 line_height=1.0),
    "statR": dict(font_family=MONO, font_size=42, font_weight=700, color="red",
                  line_height=1.0),
    "num": dict(font_family=MONO, font_size=18, font_weight=700, color="blue",
                align="center", line_height=1.0),
    "cell": dict(font_family=MONO, font_size=12.5, font_weight=400, color="ink",
                 line_height=1.3),
    "cellh": dict(font_family=MONO, font_size=12, font_weight=700, color="blue",
                  text_transform="uppercase", letter_spacing=1),
    "chip": dict(font_family=MONO, font_size=13, font_weight=700, color="void",
                 align="center", letter_spacing=2),
    "quote": dict(font_family=SANS, font_size=34, font_weight=400, color="white",
                  line_height=1.3, align="center"),
}


def hexof(c):
    return COLORS.get(c, c)


def a(color, alpha):
    return rgba(hexof(color), alpha)


# --------------------------------------------------------------------------- #
# Board vocabulary — orthogonal, crisp, no glow                                #
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


def stroke(w, color=BLUE, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": w, **extra}}


def hline(layer, x0, x1, y, color=BLUED, w=1.0, **extra):
    layer.line([x0, y], [x1, y], **stroke(w, color, **extra))


def vline(layer, x, y0, y1, color=BLUED, w=1.0, **extra):
    layer.line([x, y0], [x, y1], **stroke(w, color, **extra))


def dot(layer, cx, cy, r, fill, **extra):
    layer.ellipse([cx, cy], r, r, fill=fill, **extra)


def via(layer, cx, cy, s=7, color=BLUE, ring=True):
    """A square solder pad with an optional annular ring — the PCB join motif."""
    layer.rect([cx - s / 2, cy - s / 2, s, s], fill=color)
    if ring:
        layer.rect([cx - s, cy - s, s * 2, s * 2], fill="none", **stroke(1.2, color))


def board_grid(layer, box, step=40, color=GRIDC, w=1.0):
    x, y, bw, bh = box
    gx = x
    while gx <= x + bw + 0.5:
        vline(layer, gx, y, y + bh, color, w)
        gx += step
    gy = y
    while gy <= y + bh + 0.5:
        hline(layer, x, x + bw, gy, color, w)
        gy += step


def trace(layer, pts, color=BLUE, w=2.0, pads=True):
    """An orthogonal copper trace with square pads at both ends (sharp miters)."""
    layer.polyline(pts, **stroke(w, color, stroke_linejoin="miter", stroke_linecap="square"))
    if pads:
        via(layer, *pts[0], 8, color)
        via(layer, *pts[-1], 8, color)


def bus(layer, x0, x1, y, color=BLUE, w=4.0, taps=None):
    """A thick horizontal bus rail with optional vertical tap stubs."""
    hline(layer, x0, x1, y, color, w)
    for tx, ty in (taps or []):
        vline(layer, tx, y, ty, color, 2.0)
        via(layer, tx, ty, 7, color, ring=False)


def chip(layer, box, label, *, color=BLUE, fill="panel2", pins=4, sub=None):
    """An IC block: dark body, pin stubs on left/right, centred designator."""
    x, y, bw, bh = box
    layer.rect(box, fill=fill, **stroke(1.8, color))
    # notch (pin-1 marker)
    layer.line([x + 10, y], [x + 22, y], **stroke(2.0, color))
    for i in range(pins):
        py = y + bh * (i + 1) / (pins + 1)
        hline(layer, x - 12, x, py, color, 2.0)
        hline(layer, x + bw, x + bw + 12, py, color, 2.0)
        via(layer, x - 12, py, 5, color, ring=False)
        via(layer, x + bw + 12, py, 5, color, ring=False)
    layer.text([x, y + bh / 2 - (20 if sub else 12), bw, 26], label,
               style={"class": "h2", "align": "center", "color": color, "font_size": 18})
    if sub:
        layer.text([x, y + bh / 2 + 8, bw, 18], sub,
                   style={"class": "monoM", "align": "center"})


def corner_frame(layer, box, color=BLUE, ln=24, w=1.6, inset_px=0):
    x, y, bw, bh = inset(box, inset_px)
    for (cxp, cyp, sx, sy) in ((x, y, 1, 1), (x + bw, y, -1, 1),
                               (x, y + bh, 1, -1), (x + bw, y + bh, -1, -1)):
        layer.line([cxp, cyp], [cxp + sx * ln, cyp], **stroke(w, color))
        layer.line([cxp, cyp], [cxp, cyp + sy * ln], **stroke(w, color))


def chrome(b, kicker, title, *, kstyle="kicker"):
    """Content frame: board bg, a left bus-rail accent, kicker, title, footer."""
    global _page
    _page += 1
    n = _page
    layer = new_page(b, f"p{n:02d}")
    layer.rect([0, 0, W, H], fill="void")
    # left bus rail with vias — a recurring board spine
    vline(layer, 36, 60, H - 60, "blued", 2.0)
    for vy in range(110, H - 60, 96):
        via(layer, 36, vy, 6, "blued", ring=False)
    layer.text([MX, 70, W - 2 * MX, 22], kicker, style=kstyle)
    layer.text([MX, 96, W - 2 * MX, 56], title, style="title")
    hline(layer, MX, MX + 78, 156, "blue", 3)
    layer.text([W - MX - 160, 690, 160, 18], f"{n:02d} / {TOTAL}", style="pnum")
    layer.text([MX, 690, 420, 18], "TRACE · MAINFRAME OS · REV 1.982", style="tag")
    return layer


def footer(layer, text):
    layer.text([MX, 660, W - 2 * MX, 18], text, style="monoM")


def table(layer, box, headers, rows, *, weights, color=BLUE, row_h=40, head_h=40):
    """A control-panel style table: header rule, hairline rows, mono cells."""
    x, y, bw, bh = box
    layer.rect(box, fill="panel", **stroke(1.4, "blued"))
    cols = row([x, y, bw, bh], weights=weights)
    # header
    layer.rect([x, y, bw, head_h], fill=a(color, 0.10))
    for cb, htext in zip(cols, headers):
        layer.text([cb[0] + 14, y + head_h / 2 - 8, cb[2] - 20, 18], htext, style="cellh")
    hline(layer, x, x + bw, y + head_h, color, 1.6)
    # rows
    for r, rowvals in enumerate(rows):
        ry = y + head_h + r * row_h
        if r % 2:
            layer.rect([x, ry, bw, row_h], fill=a("blue", 0.03))
        for cb, val, htext in zip(cols, rowvals, headers):
            cstyle = "cell"
            if isinstance(val, tuple):
                val, cstyle = val
            layer.text([cb[0] + 14, ry + row_h / 2 - 8, cb[2] - 20, 18], val, style=cstyle)
        if r < len(rows) - 1:
            hline(layer, x, x + bw, ry + row_h, "gridc", 1)
    for cb in cols[1:]:
        vline(layer, cb[0], y, y + bh, "gridc", 1)


# --------------------------------------------------------------------------- #
# 01 — Cover                                                                    #
# --------------------------------------------------------------------------- #

def cover(b):
    global _page
    _page += 1
    layer = new_page(b, "cover")
    layer.rect([0, 0, W, H], fill="void")
    # a full-board trace field, right half — orthogonal copper with vias
    board_grid(layer, [640, 0, 640, H], step=40, color="gridc")
    rnd = [(680, 90), (820, 200), (980, 140), (1120, 260), (740, 360),
           (900, 440), (1080, 380), (1180, 520), (700, 560), (860, 620)]
    for i, (sx, sy) in enumerate(rnd):
        ex = sx + (80 if i % 2 else 160)
        ey = sy + (120 if i % 3 else -80)
        trace(layer, [[sx, sy], [ex, sy], [ex, ey]], color=("blue" if i % 3 else "blued"),
              w=2.0, pads=True)
    # the MCP chip, prominent
    chip(layer, [900, 300, 220, 130], "MCP", color="red", fill="panel2", pins=4,
         sub="master control")
    layer.text([MX, 150, 760, 24], "OPERATING DOCTRINE OF THE 1982 MAINFRAME", style="kicker")
    layer.text([MX, 196, 760, 150], "TRACE\nTHE BLUE\nMAINFRAME", style="h1")
    hline(layer, MX, MX + 150, 466, "blue", 3)
    layer.text([MX, 486, 520, 24], "A schematic of the system, drawn in copper.",
               style="lead")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="blued", ln=30, w=1.6)
    layer.text([MX, 600, 760, 18],
               "30 SHEETS · FRAMEGRAPH PYTHON SDK · FLAT 2D VECTOR · NO GLOW", style="tag")
    layer.text([W - MX - 160, 600, 160, 18], "01 / 30", style="pnum")


# --------------------------------------------------------------------------- #
# 02 — Contents (bus index)                                                     #
# --------------------------------------------------------------------------- #

def contents(b):
    layer = chrome(b, "Index — the board, sheet by sheet", "Contents")
    items = [
        ("01", "Architecture", "The board, the MCP, and how the subsystems wire up."),
        ("02", "Memory & I/O", "Address space, the I/O tower, bus arbitration."),
        ("03", "Performance", "Throughput, latency, the pipeline and its stalls."),
        ("04", "Security", "Access control, the handshake, the threat ledger."),
        ("05", "Roadmap", "Where the next revision of the board is headed."),
    ]
    busx = 150
    vline(layer, busx, 210, 210 + 5 * 84 - 30, "blue", 3)
    rows = column([MX, 200, W - 2 * MX, 5 * 84], 5)
    for (n, head, sub), rb in zip(items, rows):
        x, y, bw, bh = rb
        via(layer, busx, y + 30, 9, "blue")
        hline(layer, busx, busx + 40, y + 30, "blue", 2)
        layer.text([busx + 54, y + 8, 50, 30], n, style="num")
        layer.text([busx + 120, y + 4, bw - 140, 30], head, style="h2")
        layer.text([busx + 120, y + 40, bw - 160, 30], sub, style="body")
        hline(layer, busx + 120, x + bw - 10, y + 72, "gridc", 1)


# --------------------------------------------------------------------------- #
# Dividers                                                                      #
# --------------------------------------------------------------------------- #

def divider(b, pid, secno, title, subtitle, *, accent="blue"):
    global _page
    _page += 1
    layer = new_page(b, pid)
    layer.rect([0, 0, W, H], fill="void")
    board_grid(layer, [0, 0, W, H], step=48, color="gridc")
    # a trace runs in from the left to a big via beside the numeral
    bus(layer, 0, 360, 360, accent, 4.0, taps=[(360, 300)])
    via(layer, 360, 300, 12, accent)
    layer.text([MX - 4, 180, 460, 220], secno, style="idx")
    kstyle = "kickerR" if accent == "red" else "kicker"
    layer.text([MX, 250, 400, 22], f"SHEET {secno}", style=kstyle)
    layer.text([430, 270, 780, 110], title, style="h1")
    hline(layer, 436, 436 + 130, 388, accent, 3)
    layer.text([436, 410, 760, 60], subtitle, style="lead")
    corner_frame(layer, [40, 40, W - 80, H - 80], color=accent, ln=30, w=1.6)
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 04 — System block schematic                                                   #
# --------------------------------------------------------------------------- #

def overview(b):
    layer = chrome(b, "01 · Architecture", "The board at a glance")
    panel = [MX, 196, W - 2 * MX, 420]
    layer.rect(panel, fill="panel")
    board_grid(layer, panel, step=37, color="gridc")
    corner_frame(layer, panel, color="blued", ln=18, w=1.4)
    # central MCP, peripheral chips wired by traces
    mcp = [560, 350, 180, 110]
    blocks = {
        "CPU": [180, 250, 150, 84],
        "RAM": [180, 470, 150, 84],
        "I/O TOWER": [960, 250, 150, 84],
        "CLOCK": [960, 470, 150, 84],
    }
    for name, bx in blocks.items():
        chip(layer, bx, name, color="blue", pins=3)
        # trace to MCP
        c1 = (bx[0] + bx[2] + 12, bx[1] + bx[3] / 2) if bx[0] < 560 else (bx[0] - 12, bx[1] + bx[3] / 2)
        mid = ((c1[0] + (mcp[0] if c1[0] > mcp[0] else mcp[0] + mcp[2])) / 2)
        target_x = mcp[0] if c1[0] < mcp[0] else mcp[0] + mcp[2]
        ty = mcp[1] + mcp[3] / 2 + (-20 if bx[1] < 350 else 20)
        trace(layer, [[c1[0], c1[1]], [mid, c1[1]], [mid, ty], [target_x, ty]],
              color="blue", w=2.0, pads=False)
    chip(layer, mcp, "MCP", color="red", pins=4, sub="arbiter")
    footer(layer, "Every subsystem talks to the MCP; nothing crosses the board without it.")


# --------------------------------------------------------------------------- #
# 05 — MCP big chip                                                             #
# --------------------------------------------------------------------------- #

def mcp_chip(b):
    layer = chrome(b, "01 · Architecture", "The Master Control Program")
    layer.text([MX, 196, 380, 240],
               "The MCP is the board's arbiter: one chip that schedules every cycle, "
               "owns every bus grant, and answers to no user. Drawn here at the pin "
               "level — forty channels in, forty out.", style="lead")
    facts = [("PINS", "80", "blue"), ("PRIORITY", "0", "red"), ("UPTIME", "∞", "amber")]
    for i, (lbl, val, col) in enumerate(facts):
        y = 430 + i * 64
        via(layer, MX + 6, y + 18, 8, col)
        layer.text([MX + 30, y, 200, 40], val,
                   style={"class": "stat", "color": col, "font_size": 34})
        layer.text([MX + 150, y + 8, 220, 20], lbl, style="tag")
    # big chip with many pins
    x, y, bw, bh = 560, 210, 520, 400
    layer.rect([x, y, bw, bh], fill="panel2", **stroke(2.4, "red"))
    layer.line([x + 16, y], [x + 40, y], **stroke(3.0, "red"))
    for i in range(10):
        py = y + bh * (i + 0.5) / 10
        hline(layer, x - 16, x, py, "blue", 2.0)
        hline(layer, x + bw, x + bw + 16, py, "blue", 2.0)
        via(layer, x - 16, py, 5, "blue", ring=False)
        via(layer, x + bw + 16, py, 5, "blue", ring=False)
    for i in range(8):
        px = x + bw * (i + 0.5) / 8
        vline(layer, px, y - 16, y, "blue", 2.0)
        vline(layer, px, y + bh, y + bh + 16, "blue", 2.0)
    layer.text([x, y + bh / 2 - 44, bw, 56], "MCP", style={"class": "h1", "align": "center",
               "color": "red", "font_size": 64})
    layer.text([x, y + bh / 2 + 28, bw, 20], "MASTER CONTROL · PRIORITY 0",
               style={"class": "tagC", "color": "red"})
    footer(layer, "Designator MCP-900; the only chip on the board with no off pin.")


# --------------------------------------------------------------------------- #
# 06 — Big number                                                               #
# --------------------------------------------------------------------------- #

def big_number(b):
    layer = chrome(b, "01 · Architecture", "The master clock")
    layer.text([MX - 4, 210, 760, 220], "4.77", style="big")
    layer.text([MX + 4, 430, 460, 30], "megahertz — and not one tick wasted", style="lead")
    hline(layer, MX, MX + 300, 480, "blue", 3)
    notes = column([800, 210, W - 800 - MX, 360], 3, gap=26)
    facts = [
        ("ONE DOMAIN", "A single clock fans out to every chip; there is no second time."),
        ("NO SLEEP", "The board never idles — a halted cycle is a fault, not a rest."),
        ("DETERMINISTIC", "Same inputs, same edges, same light. The schedule is a law."),
    ]
    for nb, (h, body) in zip(notes, facts):
        x, y, bw, bh = nb
        via(layer, x + 6, y + 12, 8, "blue")
        layer.text([x + 28, y, bw - 28, 22], h, style="h2b")
        layer.text([x + 28, y + 30, bw - 28, 60], body, style="body")


# --------------------------------------------------------------------------- #
# 07 — Three subsystems (thirds)                                                #
# --------------------------------------------------------------------------- #

def subsystems(b):
    layer = chrome(b, "01 · Architecture", "Three subsystems")
    cols = row([MX, 210, W - 2 * MX, 410], 3, gap=28)
    data = [
        ("U01", "COMPUTE", "Arithmetic and logic units. Where programs are actually run."),
        ("U02", "STORE", "Core memory and the register file. State between the cycles."),
        ("U03", "BRIDGE", "The bus and I/O tower. The board's only door to the outside."),
    ]
    for cb, (desig, head, body) in zip(cols, data):
        x, y, bw, bh = cb
        layer.rect(cb, fill="panel", **stroke(1.6, "blued"))
        corner_frame(layer, cb, color="blue", ln=16, w=2.0)
        chip(layer, [x + bw / 2 - 50, y + 40, 100, 60], desig, color="blue", pins=2)
        layer.text([x + 28, y + 150, bw - 56, 28], head, style="h2")
        hline(layer, x + 28, x + 80, y + 188, "blue", 2)
        layer.text([x + 28, y + 206, bw - 56, 180], body, style="body")


# --------------------------------------------------------------------------- #
# 08 — Register map (bit grid)                                                  #
# --------------------------------------------------------------------------- #

def register_map(b):
    layer = chrome(b, "01 · Architecture", "The status register")
    layer.text([MX, 196, W - 2 * MX, 40],
               "One 32-bit word holds the board's whole mood — lit bits are set, dark "
               "bits are clear. Read it left (MSB) to right (LSB).", style="lead")
    gridbox = [MX, 280, W - 2 * MX, 150]
    cells = grid(gridbox, cols=16, rows=2, gap=8)
    set_bits = {0, 1, 3, 6, 7, 10, 14, 17, 18, 22, 25, 28, 30, 31}
    for i, cb in enumerate(cells):
        x, y, bw, bh = cb
        lit = i in set_bits
        col = "red" if i in (0,) else "blue"
        layer.rect(cb, fill=a(col, 0.18) if lit else "panel",
                   **stroke(1.4, col if lit else "blued"))
        layer.text([x, y + bh / 2 - 12, bw, 22], "1" if lit else "0",
                   style={"class": "mono", "align": "center",
                          "color": col if lit else "mute", "font_size": 18})
        layer.text([x, y + bh - 16, bw, 12], f"{31 - i:02d}",
                   style={"class": "monoM", "align": "center", "font_size": 9})
    # legend of named flags
    flags = [("31  HALT", "red"), ("30  FAULT", "blue"), ("25  IRQ", "blue"),
             ("18  USER", "blue"), ("07  CARRY", "amber"), ("00  RUN", "red")]
    fb = row([MX, 470, W - 2 * MX, 120], 3, gap=24)
    cells2 = []
    for col_box in fb:
        cells2 += column(col_box, 2, gap=12)
    for (name, col), cbx in zip(flags, cells2):
        x, y, bw, bh = cbx
        via(layer, x + 10, y + bh / 2, 8, col)
        layer.text([x + 32, y + bh / 2 - 10, bw - 40, 20], name, style="monoW")
    footer(layer, "Bit 00 (RUN) and bit 31 (HALT) are the only two the MCP will not share.")


# --------------------------------------------------------------------------- #
# 10 — Process table                                                            #
# --------------------------------------------------------------------------- #

def process_table(b):
    layer = chrome(b, "02 · Memory & I/O", "The process table")
    headers = ["PID", "PROGRAM", "STATE", "PRI", "CYCLES"]
    rows = [
        ["0x00", "MCP", ("RUN", "mono"), "0", "∞"],
        ["0x11", "TRON", ("READY", "mono"), "4", "1.2M"],
        ["0x12", "YORI", ("WAIT", "bodyM"), "5", "880K"],
        ["0x1A", "DUMONT", ("READY", "mono"), "6", "640K"],
        ["0x2F", "SARK", ("RUN", "mono"), "1", "3.0M"],
        ["0x40", "RAM", ("WAIT", "bodyM"), "7", "120K"],
        ["0xFF", "<rogue>", ("HALT", "cellR"), "—", "0"],
    ]
    # patch a red 'cellR' style at use-site by mapping to statR-ish via 'mono' red
    table(layer, [MX, 200, W - 2 * MX, 420], headers, rows,
          weights=[1.2, 2.4, 1.4, 0.9, 1.4], color="blue", row_h=48)
    footer(layer, "Priority 0 is reserved; the rogue at 0xFF has been HALTed pending derez.")


# --------------------------------------------------------------------------- #
# 11 — I/O tower stack                                                          #
# --------------------------------------------------------------------------- #

def io_tower(b):
    layer = chrome(b, "02 · Memory & I/O", "The I/O tower")
    layer.text([MX, 196, 360, 240],
               "The tower is the board's single port to the world beyond the screen. "
               "A request climbs five stages; only a beam that clears the top is "
               "allowed back out to the user.", style="lead")
    stages = [
        ("APERTURE", "photonic ingress", "blue"),
        ("DECODE", "beam → packets", "blue"),
        ("AUTHENTICATE", "verify the user", "amber"),
        ("QUEUE", "await a bus grant", "blue"),
        ("LASER", "egress to the user", "red"),
    ]
    bx, bw = 560, W - 560 - MX
    base_y = 596
    for i, (name, sub, col) in enumerate(stages):
        h = 70
        y = base_y - (i + 1) * (h + 12)
        layer.rect([bx, y, bw, h], fill="panel2", **stroke(1.8, col))
        layer.text([bx + 22, y + 14, bw - 200, 24], name,
                   style={"class": "h2", "color": col, "font_size": 19})
        layer.text([bx + 22, y + 44, bw - 200, 18], sub, style="bodyM")
        layer.text([bx + bw - 60, y + 22, 40, 28], f"S{4 - i}", style="num")
        if i:
            via(layer, bx + bw / 2, y + h + 6, 6, "blue", ring=False)
            vline(layer, bx + bw / 2, y + h, y + h + 12, "blue", 2)
    # beam to the top
    vline(layer, bx + bw / 2, 100, base_y - 5 * 82, "amber", 2, stroke_dasharray=[6, 5])
    footer(layer, "Stage S2 (AUTHENTICATE) is where a program proves it speaks for a user.")


# --------------------------------------------------------------------------- #
# 12 — Memory map                                                               #
# --------------------------------------------------------------------------- #

def memory_map(b):
    layer = chrome(b, "02 · Memory & I/O", "The address space")
    layer.text([MX, 196, W - 2 * MX, 40],
               "64K of core, carved into fixed regions. The MCP owns the top page and "
               "the vector table; users never see either.", style="lead")
    regions = [
        ("0x0000", "VECTORS", 0.06, "red"),
        ("0x1000", "MCP CORE", 0.18, "red"),
        ("0x4000", "PROGRAM", 0.34, "blue"),
        ("0xB000", "HEAP", 0.20, "blue"),
        ("0xE000", "I/O WINDOW", 0.12, "amber"),
        ("0xF800", "STACK", 0.10, "blue"),
    ]
    x, y, bw = MX, 280, 280
    total_h = 320
    cy = y
    for addr, name, frac, col in regions:
        h = total_h * frac
        layer.rect([x, cy, bw, h], fill=a(col, 0.14), **stroke(1.6, col))
        layer.text([x + 16, cy + h / 2 - 9, bw - 30, 18], name,
                   style={"class": "monoW", "font_size": 13})
        layer.text([x - 84, cy - 8, 76, 16], addr,
                   style={"class": "monoM", "align": "right"})
        cy += h
    layer.text([x - 84, cy - 8, 76, 16], "0xFFFF", style={"class": "monoM", "align": "right"})
    # notes on the right
    notes = [
        ("VECTORS", "Interrupt jump table — 16 entries, one per IRQ line."),
        ("MCP CORE", "Resident arbiter code. Write-protected, always mapped."),
        ("PROGRAM", "Where user programs are loaded and actually run."),
        ("I/O WINDOW", "Memory-mapped tower registers — the only door out."),
    ]
    nx = 480
    for i, (h, body) in enumerate(notes):
        ny = 290 + i * 80
        via(layer, nx, ny + 10, 8, "blue")
        layer.text([nx + 26, ny, 360, 20], h, style="h2b")
        layer.text([nx + 26, ny + 26, W - nx - MX - 26, 44], body, style="body")
    footer(layer, "Regions are fixed at boot; a program that writes outside PROGRAM faults.")


# --------------------------------------------------------------------------- #
# 13 — Bus arbitration flow                                                     #
# --------------------------------------------------------------------------- #

def arbitration(b):
    layer = chrome(b, "02 · Memory & I/O", "Bus arbitration")
    panel = [MX, 200, W - 2 * MX, 410]
    layer.rect(panel, fill="panel")
    board_grid(layer, panel, step=37, color="gridc")
    corner_frame(layer, panel, color="blued", ln=18, w=1.4)
    stages = [("REQUEST", 170, 300, "blue"), ("ARBITER", 430, 380, "red"),
              ("GRANT", 690, 280, "blue"), ("TRANSFER", 950, 380, "blue"),
              ("RELEASE", 1150, 300, "amber")]
    pos = {n: (x, y, c) for n, x, y, c in stages}
    seq = [s[0] for s in stages]
    for u, v in zip(seq, seq[1:]):
        x1, y1, _ = pos[u]
        x2, y2, _ = pos[v]
        midx = (x1 + x2) / 2
        trace(layer, [[x1, y1], [midx, y1], [midx, y2], [x2, y2]], color="blue", w=2.2, pads=False)
        layer.arrow([midx, y2], [x2 - 26, y2], color=BLUE, width=2.2, head=10)
    for name, x, y, col in stages:
        layer.rect([x - 56, y - 26, 112, 52], fill="panel2", **stroke(2.0, col))
        layer.text([x - 56, y - 9, 112, 18], name,
                   style={"class": "cellh", "align": "center", "color": col})
    # denied path
    trace(layer, [[430, 406], [430, 540], [170, 540], [170, 326]], color="red", w=1.8, pads=False)
    layer.text([520, 520, 240, 18], "DENIED → RETRY", style="kickerR")
    footer(layer, "The arbiter is the MCP; a denied master backs off and re-requests next cycle.")


# --------------------------------------------------------------------------- #
# 14 — Fault classes (quadrants)                                                #
# --------------------------------------------------------------------------- #

def fault_classes(b):
    layer = chrome(b, "02 · Memory & I/O", "Four classes of fault")
    quads = grid([MX, 196, W - 2 * MX, 420], cols=2, count=4, gap=22)
    faults = [
        ("0x01", "BUS FAULT", "blue", "A master held the bus past its grant window."),
        ("0x02", "PAGE FAULT", "amber", "A program addressed memory outside its region."),
        ("0x04", "PARITY", "blue", "A word came back from core with a flipped bit."),
        ("0x08", "ROGUE", "red", "A signature failed the handshake — derez on sight."),
    ]
    for qb, (code, name, col, body) in zip(quads, faults):
        x, y, bw, bh = qb
        layer.rect(qb, fill="panel", **stroke(1.6, col))
        layer.rect([x, y, 8, bh], fill=col)
        layer.text([x + 30, y + 30, 160, 30], code,
                   style={"class": "stat", "color": col, "font_size": 30})
        layer.text([x + 30, y + 78, bw - 60, 28], name,
                   style={"class": "h2", "color": col, "font_size": 22})
        layer.text([x + 30, y + 116, bw - 60, 70], body, style="body")
        via(layer, x + bw - 36, y + 40, 9, col)


# --------------------------------------------------------------------------- #
# 16 — Throughput bars                                                          #
# --------------------------------------------------------------------------- #

def throughput(b):
    layer = chrome(b, "03 · Performance", "Bus throughput by master")
    layer.text([MX, 196, 380, 160],
               "Words moved per thousand cycles, measured at the bus bridge for each "
               "bus master over one scheduling epoch.", style="lead")
    for i, (lbl, val, col) in enumerate([("PEAK", "918", "blue"), ("MEAN", "604", "amber"),
                                         ("MIN", "210", "red")]):
        y = 360 + i * 78
        via(layer, MX + 6, y + 18, 8, col)
        layer.text([MX + 28, y, 240, 40], val, style={"class": "stat", "color": col})
        layer.text([MX + 150, y + 8, 200, 18], lbl + " w/kc", style="tag")
    panel = [520, 196, W - 520 - MX, 420]
    layer.rect(panel, fill="panel")
    corner_frame(layer, panel, color="blued", ln=18, w=1.4)
    chart = Chart(Frame(domain=(0, 0, 6, 1000),
                        box=(panel[0] + 64, panel[1] + 40, panel[2] - 96, panel[3] - 100)))
    bars = [("MCP", 918), ("CPU", 760), ("DMA", 604), ("TOWER", 430), ("RAM", 320), ("AUX", 210)]
    chart.axes(x_ticks=[], y_ticks=[0, 250, 500, 750, 1000], y_format=lambda v: f"{int(v)}",
               grid=True, axis_color=BLUED, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    cols = [RED, BLUE, BLUE, AMBER, BLUE, RED]
    for i, ((name, val), col) in enumerate(zip(bars, cols)):
        chart.bars([(i + 0.5, val)], width=58, fill=col)
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    for i, (name, val) in enumerate(bars):
        p = fr.point(i + 0.5, 0)
        layer.text([p.x - 50, panel[1] + panel[3] - 52, 100, 16], name,
                   style={"class": "tag", "align": "center"})
    footer(layer, "Words per kilocycle. The MCP keeps the largest slice of its own bus.")


# --------------------------------------------------------------------------- #
# 17 — Latency line chart                                                       #
# --------------------------------------------------------------------------- #

def latency(b):
    layer = chrome(b, "03 · Performance", "Latency across the epoch")
    panel = [MX, 200, W - 2 * MX, 410]
    layer.rect(panel, fill="panel")
    board_grid(layer, panel, step=40, color="gridc")
    corner_frame(layer, panel, color="blued", ln=18, w=1.4)
    chart = Chart(Frame(domain=(0, 0, 24, 100),
                        box=(panel[0] + 64, panel[1] + 36, panel[2] - 110, panel[3] - 96)))
    chart.axes(x_ticks=[0, 6, 12, 18, 24], y_ticks=[0, 25, 50, 75, 100],
               x_format=lambda v: f"{int(v)}k", y_format=lambda v: f"{int(v)}c", grid=True,
               axis_color=BLUED, grid_color=GRIDC,
               label_style={"font_family": MONO, "color": MUTE})
    served = [(t, 30 + 18 * math.sin(t / 3.2) + 6 * math.sin(t / 1.1)) for t in range(0, 25)]
    queued = [(t, 20 + 55 * max(0.0, math.sin((t - 5) / 5.5))) for t in range(0, 25)]
    chart.line(served, stroke=BLUE, width=3.0, smooth=True, label="served")
    chart.line(queued, stroke=RED, width=2.6, smooth=True, label="queue depth")
    chart.legend(at=(panel[0] + 64, panel[1] + panel[3] - 26))
    layer.extend(grouped(chart.objects()))
    fr = chart.frame
    p = fr.point(12, 75)
    via(layer, p.x, p.y, 8, "red")
    layer.text([p.x - 30, p.y - 30, 180, 16], "EPOCH STALL", style="kickerR")
    footer(layer, "Queue depth peaks mid-epoch when the tower and DMA contend for the bus.")


# --------------------------------------------------------------------------- #
# 18 — Pipeline stages                                                          #
# --------------------------------------------------------------------------- #

def pipeline(b):
    layer = chrome(b, "03 · Performance", "The five-stage pipeline")
    stages = [
        ("IF", "FETCH", "Pull the next word from core at the program counter.", "blue"),
        ("ID", "DECODE", "Crack the word into an opcode and its operands.", "blue"),
        ("EX", "EXECUTE", "Run it through the arithmetic/logic unit.", "amber"),
        ("ME", "MEMORY", "Touch core if the instruction loads or stores.", "blue"),
        ("WB", "WRITE", "Commit the result back to the register file.", "blue"),
    ]
    cols = row([MX, 230, W - 2 * MX, 320], 5, gap=16)
    for i, (cb, (mn, head, body, col)) in enumerate(zip(cols, stages)):
        x, y, bw, bh = cb
        layer.rect(cb, fill="panel", **stroke(1.6, col))
        layer.rect([x, y, bw, 46], fill=a(col, 0.12))
        layer.text([x, y + 12, bw, 24], mn,
                   style={"class": "mono", "align": "center", "color": col, "font_size": 20})
        layer.text([x + 16, y + 64, bw - 32, 22], head,
                   style={"class": "h2", "font_size": 16, "color": col})
        layer.text([x + 16, y + 96, bw - 28, 160], body, style="body")
        if i < 4:
            layer.arrow([x + bw + 2, y + bh / 2], [x + bw + 14, y + bh / 2],
                        color=BLUE, width=2.2, head=8)
    # hazard note
    layer.rect([MX, 580, W - 2 * MX, 44], fill=a("red", 0.08), **stroke(1.4, "red"))
    layer.text([MX + 18, 593, W - 2 * MX - 36, 20],
               "HAZARD — a load followed by a dependent op stalls the pipe one cycle (bubble).",
               style="mono")


# --------------------------------------------------------------------------- #
# 19 — Interrupt vector table                                                   #
# --------------------------------------------------------------------------- #

def interrupts(b):
    layer = chrome(b, "03 · Performance", "The interrupt vectors")
    headers = ["IRQ", "VECTOR", "SOURCE", "PRI"]
    rows = [
        ["0", "0x0000", "RESET", "0"],
        ["1", "0x0004", "CLOCK TICK", "1"],
        ["2", "0x0008", "BUS FAULT", "2"],
        ["4", "0x0010", "TOWER I/O", "3"],
        ["7", "0x001C", "PARITY", "2"],
        ["F", "0x003C", "ROGUE TRAP", "0"],
    ]
    table(layer, [MX, 200, 660, 360], headers, rows,
          weights=[0.8, 1.6, 2.2, 0.8], color="blue", row_h=50)
    # side panel describing dispatch
    sx = 770
    layer.rect([sx, 200, W - sx - MX, 360], fill="panel2", **stroke(1.6, "blued"))
    corner_frame(layer, [sx, 200, W - sx - MX, 360], color="blue", ln=16, w=1.8)
    layer.text([sx + 26, 226, W - sx - MX - 50, 24], "HOW DISPATCH WORKS", style="h2b")
    steps = [
        "A device raises its IRQ line.",
        "The MCP finishes the current cycle.",
        "It reads the vector at the IRQ's slot.",
        "Control jumps there; state is pushed.",
        "RTI pops state and resumes the program.",
    ]
    for i, s in enumerate(steps):
        sy = 270 + i * 52
        via(layer, sx + 32, sy + 8, 7, "blue")
        layer.text([sx + 52, sy, W - sx - MX - 80, 40], f"{i + 1}.  {s}", style="mono")
    footer(layer, "IRQ 0 and IRQ F both jump at priority 0 — reset and rogue-trap pre-empt all.")


# --------------------------------------------------------------------------- #
# 20 — Power / thermal gauges                                                   #
# --------------------------------------------------------------------------- #

def gauges(b):
    layer = chrome(b, "03 · Performance", "Board telemetry")
    bars = [
        ("CORE VOLTAGE", 0.88, "blue"),
        ("BUS UTILISATION", 0.72, "blue"),
        ("THERMAL MARGIN", 0.54, "amber"),
        ("PARITY HEALTH", 0.96, "blue"),
        ("MCP LOAD", 0.81, "red"),
    ]
    track_x, track_w = 470, 640
    for i, (name, frac, col) in enumerate(bars):
        y = 230 + i * 76
        layer.text([MX, y - 2, 380, 22], name, style="mono")
        layer.rect([track_x, y, track_w, 18], fill="panel2", **stroke(1.2, "blued"))
        # segmented fill — PCB style, not a smooth bar
        segs = 40
        lit = int(segs * frac)
        sw = track_w / segs
        for s in range(segs):
            if s < lit:
                layer.rect([track_x + s * sw + 1, y + 2, sw - 2, 14], fill=col)
        layer.text([track_x + track_w + 16, y - 4, 120, 26], f"{int(frac * 100)}%",
                   style={"class": "stat", "color": col, "font_size": 22})
    footer(layer, "Thermal margin is the metric to watch; under 0.40 the clock is throttled.")


# --------------------------------------------------------------------------- #
# 22 — Access control matrix                                                    #
# --------------------------------------------------------------------------- #

def access_matrix(b):
    layer = chrome(b, "04 · Security", "The access matrix")
    layer.text([MX, 196, W - 2 * MX, 40],
               "Rows are programs; columns are resources. A lit pad is a granted right; "
               "MCP-red marks a right only the arbiter holds.", style="lead")
    progs = ["MCP", "TRON", "YORI", "DUMONT", "SARK"]
    res = ["CORE", "BUS", "TOWER", "CLOCK", "DEREZ"]
    ox, oy = 280, 300
    cw, ch = 150, 56
    # column headers
    for c, rname in enumerate(res):
        layer.text([ox + c * cw, oy - 30, cw, 18], rname,
                   style={"class": "cellh", "align": "center"})
    grants = {
        (0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
        (1, 1), (1, 2), (1, 4),
        (2, 0), (2, 2),
        (3, 1), (3, 2),
        (4, 0), (4, 1), (4, 4),
    }
    mcp_only = {(0, 3), (0, 4), (4, 4)}
    for r, pname in enumerate(progs):
        layer.text([MX, oy + r * ch + ch / 2 - 9, ox - MX - 20, 18], pname,
                   style={"class": "monoW", "align": "right"})
        for c in range(len(res)):
            cell = [ox + c * cw + 6, oy + r * ch + 6, cw - 12, ch - 12]
            if (r, c) in grants:
                col = "red" if (r, c) in mcp_only else "blue"
                layer.rect(cell, fill=a(col, 0.20), **stroke(1.6, col))
                via(layer, cell[0] + cell[2] / 2, cell[1] + cell[3] / 2, 8, col, ring=False)
            else:
                layer.rect(cell, fill="panel", **stroke(1.0, "gridc"))
    footer(layer, "Only the MCP and its enforcer Sark hold DEREZ; no user program does.")


# --------------------------------------------------------------------------- #
# 23 — Handshake sequence                                                       #
# --------------------------------------------------------------------------- #

def handshake(b):
    layer = chrome(b, "04 · Security", "The authentication handshake")
    layer.text([MX, 196, W - 2 * MX, 40],
               "Five messages between a program and the MCP. Miss the timing on any one "
               "and the line is dropped — and the program flagged.", style="lead")
    left_x, right_x = 320, 960
    top = 300
    vline(layer, left_x, top, top + 250, "blue", 2)
    vline(layer, right_x, top, top + 250, "red", 2)
    layer.text([left_x - 120, top - 34, 240, 20], "PROGRAM", style="h2b")
    layer.text([right_x - 120, top - 34, 240, 20], "MCP",
               style={"class": "h2", "color": "red"})
    msgs = [
        ("HELLO ⟶", True, "blue"),
        ("⟵ NONCE", False, "red"),
        ("SIGN(nonce) ⟶", True, "blue"),
        ("⟵ VERIFY", False, "red"),
        ("GRANT ⟷", True, "amber"),
    ]
    for i, (text, l2r, col) in enumerate(msgs):
        y = top + 20 + i * 48
        if l2r:
            layer.arrow([left_x, y], [right_x, y], color=hexof(col), width=2.0, head=10)
        else:
            layer.arrow([right_x, y], [left_x, y], color=hexof(col), width=2.0, head=10)
        layer.text([left_x, y - 24, right_x - left_x, 18], text,
                   style={"class": "mono", "align": "center", "color": col})
    footer(layer, "The nonce is single-use; a replayed signature fails VERIFY and trips a trap.")


# --------------------------------------------------------------------------- #
# 24 — Threat ledger                                                            #
# --------------------------------------------------------------------------- #

def threat_ledger(b):
    layer = chrome(b, "04 · Security", "The threat ledger")
    headers = ["TS", "EVENT", "ORIGIN", "VERDICT"]
    rows = [
        ["0x3A1", "replay attempt", "0xFF", ("DEREZ", "mono")],
        ["0x3B0", "page fault", "0x40", ("KILL", "mono")],
        ["0x3C8", "bus hog", "0x2F", ("WARN", "bodyM")],
        ["0x401", "bad signature", "0xFF", ("DEREZ", "mono")],
        ["0x44F", "clock tamper", "0x2F", ("TRAP", "mono")],
        ["0x460", "user login", "0x11", ("ALLOW", "bodyM")],
    ]
    table(layer, [MX, 200, W - 2 * MX, 380], headers, rows,
          weights=[1.0, 2.6, 1.2, 1.4], color="red", row_h=52)
    footer(layer, "Two DEREZ verdicts in one epoch, both from 0xFF — the same rogue, retrying.")


# --------------------------------------------------------------------------- #
# 26 — Roadmap                                                                  #
# --------------------------------------------------------------------------- #

def roadmap(b):
    layer = chrome(b, "05 · Roadmap", "The next revision")
    layer.text([MX, 196, 360, 220],
               "Four board revisions, each gated on the last passing burn-in. The bus "
               "rail below is the schedule; vias mark a shipped rev.", style="lead")
    phases = [
        ("REV A", "WIDEN BUS", "16-bit → 32-bit data path across the bridge.", "blue"),
        ("REV B", "DUAL CLOCK", "A spare oscillator so a stall is no longer fatal.", "blue"),
        ("REV C", "USER PAGES", "Per-program memory protection, enforced in hardware.", "amber"),
        ("REV D", "OPEN TOWER", "A second I/O port — the board stops being a fortress.", "red"),
    ]
    bx, bw = 500, W - 500 - MX
    railx = bx + 18
    vline(layer, railx, 210, 210 + len(phases) * 100 - 40, "blued", 3)
    for i, (ph, head, body, col) in enumerate(phases):
        y = 210 + i * 100
        via(layer, railx, y + 18, 10, col)
        layer.text([bx + 52, y, 120, 18], ph, style={"class": "kicker", "color": col})
        layer.text([bx + 52, y + 22, bw - 60, 24], head,
                   style={"class": "h2", "font_size": 20})
        layer.text([bx + 52, y + 52, bw - 60, 40], body, style="body")
    footer(layer, "REV D removes the single-port assumption the whole 1982 design was built on.")


# --------------------------------------------------------------------------- #
# 27 — Timeline                                                                 #
# --------------------------------------------------------------------------- #

def timeline(b):
    layer = chrome(b, "05 · Roadmap", "A short history of the board")
    spine_y = 400
    bus(layer, MX, W - MX, spine_y, "blue", 3)
    nodes = row([MX, spine_y - 14, W - 2 * MX, 28], 5)
    beats = [
        ("REV 0", "POWER ON", "The board boots; the MCP claims priority 0."),
        ("REV 1", "THE GRID", "Programs are given the games to keep them busy."),
        ("REV 2", "THE LOCK", "The MCP closes the tower; users are shut out."),
        ("REV 3", "TRON", "A security program is written to fight for the users."),
        ("REV 4", "OPEN", "The tower reopens; the board answers to users again."),
    ]
    for i, (nb, (code, head, body)) in enumerate(zip(nodes, beats)):
        cx = nb[0] + nb[2] / 2
        col = "red" if i == 2 else "blue"
        via(layer, cx, spine_y, 10, col)
        above = i % 2 == 0
        ty = spine_y - 150 if above else spine_y + 38
        layer.text([cx - 95, ty, 190, 18], code,
                   style={"class": "kicker", "color": col, "align": "center"})
        layer.text([cx - 95, ty + 24, 190, 24], head,
                   style={"class": "h2", "align": "center", "font_size": 18})
        layer.text([cx - 95, ty + 54, 190, 70], body,
                   style={"class": "body", "align": "center", "font_size": 13})
    footer(layer, "Revisions are board spins, not software patches — each one re-lays copper.")


# --------------------------------------------------------------------------- #
# 28 — Quote                                                                    #
# --------------------------------------------------------------------------- #

def quote(b):
    global _page
    _page += 1
    layer = new_page(b, f"p{_page:02d}")
    layer.rect([0, 0, W, H], fill="void")
    board_grid(layer, [0, 0, W, H], step=48, color="gridc")
    chip(layer, [W / 2 - 110, 150, 220, 110], "MCP", color="red", pins=4)
    layer.text([180, 320, W - 360, 150],
               "“I've gotten 2,415 times\nsmarter since then.”", style="quote")
    hline(layer, W / 2 - 50, W / 2 + 50, 480, "red", 3)
    layer.text([0, 500, W, 22], "// THE MASTER CONTROL PROGRAM", style="tagC")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="blued", ln=30, w=1.6)
    layer.text([W - MX - 160, 690, 160, 18], f"{_page:02d} / {TOTAL}", style="pnum")


# --------------------------------------------------------------------------- #
# 29 — Spec sheet (KPI grid)                                                    #
# --------------------------------------------------------------------------- #

def spec_sheet(b):
    layer = chrome(b, "05 · Roadmap", "Board specification")
    specs = [
        ("CLOCK", "4.77 MHz", "blue"), ("WORD", "16 bit", "blue"),
        ("CORE", "64 KB", "blue"), ("BUS", "8-master", "amber"),
        ("IRQ LINES", "16", "blue"), ("PIPELINE", "5-stage", "blue"),
        ("TOWER", "1 port", "red"), ("PRIORITY 0", "MCP only", "red"),
    ]
    cells = grid([MX, 210, W - 2 * MX, 400], cols=4, rows=2, gap=20)
    for cb, (lbl, val, col) in zip(cells, specs):
        x, y, bw, bh = cb
        layer.rect(cb, fill="panel", **stroke(1.6, "blued"))
        layer.rect([x, y, bw, 6], fill=col)
        via(layer, x + 20, y + 36, 8, col)
        layer.text([x + 20, y + 64, bw - 36, 40], val,
                   style={"class": "stat", "color": col, "font_size": 30})
        layer.text([x + 20, y + bh - 36, bw - 36, 18], lbl, style="tag")
    footer(layer, "The two red specs — single tower, MCP-only priority 0 — are the design's risk.")


# --------------------------------------------------------------------------- #
# 30 — Closing                                                                  #
# --------------------------------------------------------------------------- #

def closing(b):
    global _page
    _page += 1
    layer = new_page(b, "close")
    layer.rect([0, 0, W, H], fill="void")
    board_grid(layer, [640, 0, 640, H], step=40, color="gridc")
    for i, (sx, sy) in enumerate([(700, 120), (900, 240), (1100, 160), (760, 420), (980, 540)]):
        trace(layer, [[sx, sy], [sx + 120, sy], [sx + 120, sy + 90]],
              color=("blue" if i % 2 else "blued"), w=2.0)
    chip(layer, [900, 300, 220, 120], "TRACE", color="blue", pins=4, sub="end of sheet")
    layer.text([MX, 150, 760, 22], "END OF SCHEMATIC", style="kicker")
    layer.text([MX, 192, 760, 130], "READ THE\nCOPPER.", style="h1")
    layer.text([MX, 360, 520, 24],
               "The board is one file; fork the schematic and re-lay it.", style="lead")
    chipbox = [MX, 420, 320, 56]
    layer.rect(chipbox, fill="blue")
    layer.text([chipbox[0], chipbox[1] + 18, chipbox[2], 22], "uv run · tron_blue_mainframe",
               style="chip")
    corner_frame(layer, [40, 40, W - 80, H - 80], color="blued", ln=30, w=1.6)
    layer.text([MX, 600, 760, 18],
               "FRAMEGRAPH PYTHON SDK · 30 SHEETS · FLAT 2D VECTOR · ORIGINAL 1982 REGISTER",
               style="tag")
    layer.text([W - MX - 160, 600, 160, 18], "30 / 30", style="pnum")


# --------------------------------------------------------------------------- #
# Assembly                                                                      #
# --------------------------------------------------------------------------- #

def build():
    b = DocumentBuilder(title="Trace: The Blue Mainframe", profile="deck", lang="en")
    # a red 'cellR' style used by a couple of tables
    extra = dict(STYLES)
    extra["cellR"] = dict(font_family=MONO, font_size=12.5, font_weight=700, color="red")
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in extra.items():
        b.define_text_style(k, **v)

    cover(b)                                                   # 01
    contents(b)                                                # 02
    divider(b, "div1", "01", "Architecture", "The board, the MCP, the subsystems.")  # 03
    overview(b)                                                # 04
    mcp_chip(b)                                                # 05
    big_number(b)                                              # 06
    subsystems(b)                                              # 07
    register_map(b)                                            # 08
    divider(b, "div2", "02", "Memory & I/O", "Address space, the tower, the bus.")   # 09
    process_table(b)                                           # 10
    io_tower(b)                                                # 11
    memory_map(b)                                              # 12
    arbitration(b)                                             # 13
    fault_classes(b)                                           # 14
    divider(b, "div3", "03", "Performance", "Throughput, latency, the pipeline.")    # 15
    throughput(b)                                              # 16
    latency(b)                                                 # 17
    pipeline(b)                                                # 18
    interrupts(b)                                              # 19
    gauges(b)                                                  # 20
    divider(b, "div4", "04", "Security", "Access, the handshake, the ledger.",
            accent="red")                                      # 21
    access_matrix(b)                                           # 22
    handshake(b)                                               # 23
    threat_ledger(b)                                           # 24
    divider(b, "div5", "05", "Roadmap", "History, revisions, the spec.")             # 25
    roadmap(b)                                                 # 26
    timeline(b)                                                # 27
    quote(b)                                                   # 28
    spec_sheet(b)                                              # 29
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
    out = os.path.join(ROOT, "tests", "fixtures", "tron-blue-mainframe.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
