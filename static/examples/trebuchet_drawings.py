#!/usr/bin/env python3
"""Author a 30-sheet engineering drawing package for a counterweight trebuchet.

This is a *demonstration* of the public FrameGraph Python SDK (:mod:`framegraph.sdk`)
that deliberately picks a different output genre from the slide decks in this
folder: it is a **drafting package**, not a deck. Every sheet wears the furniture
of a real engineering drawing —

  * a ruled drawing border with A--F / 1--8 *zone* references in the margin;
  * an ANSI/ISO-style **title block** in the bottom-right corner carrying the
    drawing number, scale, sheet x-of-y, material, revision and a third-angle
    projection symbol;
  * dimensioned orthographic views (side / front / plan elevations), section
    views with cross-hatching, detail callouts on lettered bubbles, exploded
    assemblies, free-body diagrams and kinematic schematics; and
  * a bill of materials.

All linework is solved in *machine space* (millimetres) and mapped to the sheet
through a tiny ``MScale`` helper, so the same trebuchet geometry is reused
consistently across the general-arrangement, mechanism and analysis sheets. The
data plots (trajectory, performance) lower through the SDK ``Chart`` helper; the
isometric general view projects a 3-D wire model through ``Mat4.isometric``.

The identity is intentionally *not* the navy slide-deck house style: warm
drafting vellum, drafting-ink linework, a single engineering-red for cutting
planes and key callouts, and the Fira Sans Condensed / Fira Mono technical
type families (verified installed via ``fc-list``).

Run from the repository root::

    uv run python examples/trebuchet_drawings.py            # build + validate + write YAML
    uv run python examples/trebuchet_drawings.py --render   # also write per-sheet SVGs

Output document: ``fixtures/trebuchet-engineering-drawings.fg.yaml`` (a checked-in
fixture, so the component flows through the ``make check`` gate).
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
    Mat4,
    Path,
    Vec2,
    Vec3,
    grid,
    row,
    serialize,
    theme,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Sheet, identity and type                                                     #
# --------------------------------------------------------------------------- #

W, H = 1400, 990                       # ~ISO A3 landscape proportion (1:1.414)
OUTER = 22                             # outer trim border inset
FRAME = 46                             # inner drawing-frame inset
FX0, FY0, FX1, FY1 = FRAME, FRAME, W - FRAME, H - FRAME

# Title block (bottom-right, inside the frame)
TBW, TBH = 392, 150
TBX, TBY = FX1 - TBW, FY1 - TBH

TOTAL = 30
_sheet = 0  # 1-based sheet counter consumed by the title block

# --- drafting-vellum palette (distinct from the deck house style) ----------- #
PAPER = "#F4F1E8"      # warm drawing vellum
INK = "#211E18"        # drafting ink (headings / titles)
SOFT = "#5B5648"       # secondary text
FAINT = "#8B8674"      # tertiary / units
OBJ = "#23211B"        # object outlines (visible edges)
THIN = "#B4AD9A"       # construction / extension lines
DIM = "#46413510"      # (placeholder, overwritten below)
DIM = "#403B31"        # dimension lines + arrows
HID = "#9A9melted"      # (overwritten)
HID = "#94917F"        # hidden-detail dashes
HATCH = "#8E8870"      # section cross-hatch
CL = "#A0603F"         # centreline chain (muted oxide)
RED = "#A4382C"        # cutting planes, section letters, key notes
BLUE = "#2C5C7B"       # auxiliary / motion / reference
OLIVE = "#6C6A2E"      # counterweight / mass accents
PANEL = "#ECE8DB"      # faint cell fill
PANEL2 = "#E2DDCB"     # table header fill
WHITE = "#FFFFFF"

# blueprint cover/hero
BP = "#15303F"
BPL = "#4E81A0"
BPW = "#EAF2F6"

COND = ["Fira Sans Condensed", "DejaVu Sans Condensed", "Arial Narrow", "sans-serif"]
SANS = ["Fira Sans", "DejaVu Sans", "Helvetica Neue", "sans-serif"]
MONO = ["Fira Mono", "DejaVu Sans Mono", "monospace"]

STYLES = {
    "head": {"font_family": COND, "font_size": 23, "font_weight": 700, "color": INK,
             "line_height": 1.04, "letter_spacing": 0.2},
    "kick": {"font_family": COND, "font_size": 11.5, "font_weight": 600, "color": RED,
             "text_transform": "uppercase", "letter_spacing": 2.6},
    "noteh": {"font_family": COND, "font_size": 12.5, "font_weight": 700, "color": INK,
              "text_transform": "uppercase", "letter_spacing": 1.4},
    "note": {"font_family": SANS, "font_size": 12, "font_weight": 400, "color": SOFT,
             "line_height": 1.42},
    "lede": {"font_family": SANS, "font_size": 13.5, "font_weight": 400, "color": "#34312A",
             "line_height": 1.44},
    "lbl": {"font_family": COND, "font_size": 12, "font_weight": 600, "color": INK,
            "letter_spacing": 0.4},
    "lblr": {"font_family": COND, "font_size": 12, "font_weight": 600, "color": RED,
             "letter_spacing": 0.4},
    "lblb": {"font_family": COND, "font_size": 12, "font_weight": 600, "color": BLUE,
             "letter_spacing": 0.4},
    "dim": {"font_family": MONO, "font_size": 10.5, "font_weight": 500, "color": DIM},
    "dimr": {"font_family": MONO, "font_size": 10.5, "font_weight": 500, "color": RED},
    "small": {"font_family": COND, "font_size": 10, "font_weight": 500, "color": FAINT,
              "letter_spacing": 0.6},
    "bub": {"font_family": COND, "font_size": 12.5, "font_weight": 700, "color": WHITE,
            "align": "center"},
    "tbprj": {"font_family": COND, "font_size": 10.5, "font_weight": 700, "color": INK,
              "text_transform": "uppercase", "letter_spacing": 1.6},
    "tbl": {"font_family": COND, "font_size": 7.6, "font_weight": 600, "color": FAINT,
            "text_transform": "uppercase", "letter_spacing": 1.0},
    "tbv": {"font_family": COND, "font_size": 12.5, "font_weight": 600, "color": INK},
    "tbtitle": {"font_family": COND, "font_size": 16.5, "font_weight": 700, "color": INK,
                "line_height": 1.06},
    "tbno": {"font_family": MONO, "font_size": 17, "font_weight": 700, "color": INK},
    "zone": {"font_family": COND, "font_size": 11, "font_weight": 600, "color": SOFT,
             "align": "center"},
    "axis": {"font_family": COND, "font_size": 10.5, "font_weight": 600, "color": SOFT},
    "th": {"font_family": COND, "font_size": 11, "font_weight": 700, "color": INK,
           "text_transform": "uppercase", "letter_spacing": 0.8},
    "td": {"font_family": SANS, "font_size": 11, "font_weight": 400, "color": "#34312A"},
    "tdm": {"font_family": MONO, "font_size": 10.5, "font_weight": 500, "color": "#34312A"},
    # hero (blueprint)
    "hk": {"font_family": COND, "font_size": 14, "font_weight": 600, "color": BPL,
           "text_transform": "uppercase", "letter_spacing": 4},
    "h1": {"font_family": COND, "font_size": 58, "font_weight": 700, "color": BPW,
           "line_height": 1.02},
    "hsub": {"font_family": SANS, "font_size": 17, "font_weight": 400, "color": "#BcSomething"},
}
STYLES["hsub"]["color"] = "#B9D0DC"

PROJECT = "FRAMEGRAPH WORKS · SIEGE-ENGINE DIVISION"


# --------------------------------------------------------------------------- #
# Primitive drafting vocabulary                                               #
# --------------------------------------------------------------------------- #

def stroke(width, color=OBJ, **extra):
    return {"stroke": color, "stroke_style": {"stroke_width": width, **extra}}


def line(layer, a, b, color=OBJ, width=1.0, **extra):
    layer.line([a[0], a[1]], [b[0], b[1]], **stroke(width, color, **extra))


def hline(layer, x0, x1, y, color=OBJ, width=1.0, **extra):
    layer.line([x0, y], [x1, y], **stroke(width, color, **extra))


def vline(layer, x, y0, y1, color=OBJ, width=1.0, **extra):
    layer.line([x, y0], [x, y1], **stroke(width, color, **extra))


def dot(layer, c, r, fill):
    layer.add({"type": "ellipse", "center": [c[0], c[1]], "rx": r, "ry": r, "fill": fill})


def ring(layer, c, r, color=OBJ, width=1.2, fill="none", **extra):
    layer.add({"type": "ellipse", "center": [c[0], c[1]], "rx": r, "ry": r,
               "fill": fill, "stroke": color, "stroke_style": {"stroke_width": width, **extra}})


def poly(layer, pts, *, closed=False, **fields):
    obj = {"type": "polyline", "points": [[p[0], p[1]] for p in pts]}
    if closed:
        obj["closed"] = True
    obj.update(fields)
    layer.add(obj)


def rect(layer, box, **fields):
    layer.rect(box, **fields)


def arrowhead(layer, tip, ang, color=DIM, size=9.0):
    """Filled triangular arrowhead with its point at ``tip`` pointing along ``ang``."""
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    spread = size * 0.30
    bx, by = tip[0] - dx * size, tip[1] - dy * size
    poly(layer, [tip, [bx + px * spread, by + py * spread],
                 [bx - px * spread, by - py * spread]], closed=True, fill=color)


def centerline(layer, a, b, color=CL, width=0.9):
    line(layer, a, b, color, width, stroke_dasharray=[14, 4, 3, 4])


def cl_cross(layer, c, r, color=CL):
    centerline(layer, [c[0] - r, c[1]], [c[0] + r, c[1]], color)
    centerline(layer, [c[0], c[1] - r], [c[0], c[1] + r], color)


def hatch(layer, box, *, gap=8.0, color=HATCH, width=0.6):
    """45-degree section cross-hatching clipped to a rectangle ``box``."""
    bx, by, bw, bh = box
    left, top, right, bottom = bx, by, bx + bw, by + bh
    k = left - bottom
    kmax = right - top
    while k <= kmax:
        pts = []
        for (ex, ey) in (("L", left - k), ("R", right - k)):
            pass
        # line  x - y = k  intersected with the rectangle edges
        cand = []
        y_at_left = left - k
        if top <= y_at_left <= bottom:
            cand.append((left, y_at_left))
        y_at_right = right - k
        if top <= y_at_right <= bottom:
            cand.append((right, y_at_right))
        x_at_top = top + k
        if left <= x_at_top <= right:
            cand.append((x_at_top, top))
        x_at_bottom = bottom + k
        if left <= x_at_bottom <= right:
            cand.append((x_at_bottom, bottom))
        uniq = []
        for p in cand:
            if not any(abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6 for q in uniq):
                uniq.append(p)
        if len(uniq) >= 2:
            line(layer, uniq[0], uniq[1], color, width)
        k += gap


def dim_h(layer, x0, x1, y, text, *, ext_to=None, color=DIM, style="dim", above=True):
    """Horizontal dimension between x0 and x1 at height y, arrows pointing outward."""
    line(layer, [x0, y], [x1, y], color, 0.9)
    arrowhead(layer, [x0, y], math.pi, color)
    arrowhead(layer, [x1, y], 0.0, color)
    if ext_to is not None:
        line(layer, [x0, ext_to], [x0, y + (4 if ext_to < y else -4)], THIN, 0.7)
        line(layer, [x1, ext_to], [x1, y + (4 if ext_to < y else -4)], THIN, 0.7)
    ty = y - 16 if above else y + 4
    layer.text([(x0 + x1) / 2 - 70, ty, 140, 14], text,
               style={"class": style, "align": "center"})


def dim_v(layer, x, y0, y1, text, *, ext_to=None, color=DIM, style="dim", right=True):
    """Vertical dimension between y0 and y1 at x; text offset to one side (horizontal)."""
    line(layer, [x, y0], [x, y1], color, 0.9)
    arrowhead(layer, [x, y0], -math.pi / 2, color)
    arrowhead(layer, [x, y1], math.pi / 2, color)
    if ext_to is not None:
        line(layer, [ext_to, y0], [x + (4 if ext_to < x else -4), y0], THIN, 0.7)
        line(layer, [ext_to, y1], [x + (4 if ext_to < x else -4), y1], THIN, 0.7)
    my = (y0 + y1) / 2
    if right:
        layer.text([x + 7, my - 7, 90, 14], text, style={"class": style})
    else:
        layer.text([x - 97, my - 7, 90, 14], text, style={"class": style, "align": "right"})


def leader(layer, frm, to, label, *, color=DIM, style="lbl", align=None):
    """Annotation leader: a line from a point ``frm`` to a text anchor ``to``."""
    line(layer, frm, to, color, 0.8)
    arrowhead(layer, frm, math.atan2(frm[1] - to[1], frm[0] - to[0]), color, 7)
    a = align or ("right" if to[0] < frm[0] else "left")
    tx = to[0] - 150 if a == "right" else to[0] + 4
    layer.text([tx, to[1] - 7, 146, 14], label, style={"class": style, "align": a})


def bubble(layer, c, label, *, r=12, color=RED):
    ring(layer, c, r, color, 1.4, fill=PAPER)
    layer.text([c[0] - r, c[1] - 8, 2 * r, 16], label, style={"class": "bub", "color": color})


def view_label(layer, x, y, title, scale=None):
    layer.text([x, y, 460, 16], title, style={"class": "lbl", "font_size": 13.5})
    hline(layer, x, x + min(8 + len(title) * 7.0, 300), y + 19, INK, 1.4)
    if scale:
        layer.text([x, y + 23, 300, 14], f"SCALE  {scale}", style={"class": "small"})


# --------------------------------------------------------------------------- #
# Sheet chrome — border, zone references and the title block                   #
# --------------------------------------------------------------------------- #

def new_layer(builder, pid):
    return builder.page(pid, canvas={"size": [W, H], "units": "px"},
                        coordinate_mode="absolute").layer("main")


def title_block(layer, dwg_no, title, *, scale, material, rev="A"):
    global _sheet
    n = _sheet
    rect(layer, [TBX, TBY, TBW, TBH], fill=WHITE, stroke=INK,
         stroke_style={"stroke_width": 1.6})
    # internal grid
    vline(layer, TBX + 236, TBY, TBY + TBH, INK, 1.0)
    hline(layer, TBX, TBX + 236, TBY + 22, INK, 1.0)      # under project band
    hline(layer, TBX, TBX + 236, TBY + 84, INK, 1.0)      # under title
    hline(layer, TBX + 236, TBX + TBW, TBY + 52, INK, 1.0)
    hline(layer, TBX + 236, TBX + TBW, TBY + 84, INK, 1.0)
    hline(layer, TBX, TBX + TBW, TBY + 116, INK, 1.0)     # bottom band
    vline(layer, TBX + 78, TBY + 84, TBY + TBH, INK, 1.0)
    vline(layer, TBX + 236 + 78, TBY + 52, TBY + 84, INK, 1.0)
    vline(layer, TBX + 130, TBY + 116, TBY + TBH, INK, 1.0)
    vline(layer, TBX + 250, TBY + 116, TBY + TBH, INK, 1.0)

    layer.text([TBX + 10, TBY + 6, 224, 14], PROJECT, style={"class": "tbprj"})
    layer.text([TBX + 10, TBY + 30, 224, 48], title, style={"class": "tbtitle"})
    # left bottom band cells: scale | material | sheet-rule below
    def cell(x, y, w, lbl, val, vstyle="tbv"):
        layer.text([x + 6, y + 3, w - 8, 10], lbl, style={"class": "tbl"})
        layer.text([x + 6, y + 13, w - 8, 16], val, style={"class": vstyle})
    cell(TBX, TBY + 88, 78, "Drawn", "P. ANÍSIO")
    cell(TBX + 78, TBY + 88, 158, "Standard", "ISO 128 · 1st-angle")
    cell(TBX, TBY + 118, 130, "Scale", scale, "tbv")
    cell(TBX + 130, TBY + 118, 120, "Material", material, "tbv")
    cell(TBX + 250, TBY + 118, 92, "Units", "mm / °", "tbv")
    # right column: drawing number / sheet / rev
    layer.text([TBX + 244, TBY + 6, 140, 10], "Drawing no.", style={"class": "tbl"})
    layer.text([TBX + 244, TBY + 22, 148, 22], dwg_no, style={"class": "tbno"})
    layer.text([TBX + 244, TBY + 58, 70, 10], "Sheet", style={"class": "tbl"})
    layer.text([TBX + 244, TBY + 68, 70, 14], f"{n:02d} / {TOTAL}", style={"class": "tbv"})
    layer.text([TBX + 322, TBY + 58, 60, 10], "Rev", style={"class": "tbl"})
    layer.text([TBX + 322, TBY + 68, 60, 14], rev, style={"class": "tbv"})
    # third-angle projection symbol, bottom-right
    sx, sy = TBX + 348, TBY + 132
    ring(layer, [sx, sy], 6, INK, 1.0)
    ring(layer, [sx, sy], 3, INK, 1.0)
    poly(layer, [[sx + 18, sy - 6], [sx + 40, sy - 4], [sx + 40, sy + 4], [sx + 18, sy + 6]],
         closed=True, fill="none", stroke=INK, stroke_style={"stroke_width": 1.0})
    line(layer, [sx + 18, sy], [sx + 40, sy], INK, 0.7, stroke_dasharray=[3, 2])


def sheet(builder, dwg_no, title, kicker, *, scale="1:25", material="OAK / WROUGHT IRON"):
    """Standard drawing sheet: vellum, ruled border, zone refs, header, title block."""
    global _sheet
    _sheet += 1
    layer = new_layer(builder, f"sheet-{_sheet:02d}")
    rect(layer, [0, 0, W, H], fill=PAPER)
    # trim + drawing border (double rule)
    rect(layer, [OUTER, OUTER, W - 2 * OUTER, H - 2 * OUTER], fill="none", stroke=INK,
         stroke_style={"stroke_width": 1.0})
    rect(layer, [FX0, FY0, W - 2 * FRAME, H - 2 * FRAME], fill="none", stroke=INK,
         stroke_style={"stroke_width": 1.8})
    _zone_refs(layer)
    # header band
    layer.text([FX0 + 16, FY0 + 12, 900, 16], kicker, style={"class": "kick"})
    layer.text([FX0 + 16, FY0 + 28, 980, 30], title, style={"class": "head"})
    hline(layer, FX0 + 16, FX0 + 360, FY0 + 60, RED, 2.2)
    hline(layer, FX0 + 360, FX1 - 16, FY0 + 60, THIN, 1.0)
    title_block(layer, dwg_no, title, scale=scale, material=material)
    return layer


def _zone_refs(layer):
    cols = 8
    rows = 6
    for i in range(cols):
        x = FX0 + (FX1 - FX0) * (i + 0.5) / cols
        layer.text([x - 12, OUTER + 4, 24, 14], str(i + 1), style={"class": "zone"})
        layer.text([x - 12, FY1 + 4, 24, 14], str(i + 1), style={"class": "zone"})
        if i:
            xt = FX0 + (FX1 - FX0) * i / cols
            vline(layer, xt, OUTER, FY0, INK, 0.6)
            vline(layer, xt, FY1, H - OUTER, INK, 0.6)
    for j in range(rows):
        y = FY0 + (FY1 - FY0) * (j + 0.5) / rows
        ltr = chr(ord("A") + (rows - 1 - j))
        layer.text([OUTER, y - 8, 24, 14], ltr, style={"class": "zone"})
        layer.text([FX1 + 2, y - 8, 24, 14], ltr, style={"class": "zone"})
        if j:
            yt = FY0 + (FY1 - FY0) * j / rows
            hline(layer, OUTER, FX0, yt, INK, 0.6)
            hline(layer, FX1, W - OUTER, yt, INK, 0.6)


def _wrapped_lines(text, width_px, char_px=6.4):
    cpl = max(10, int(width_px / char_px))
    total = 0
    for seg in text.split("\n"):
        total += max(1, math.ceil(len(seg) / cpl))
    return total


def notes_panel(layer, box, header, items, *, numbered=True):
    x, y, w, h = box
    text_w = w - (44 if numbered else 40)
    heights = [_wrapped_lines(it, text_w) for it in items]
    needed = 40 + sum(n * 16 + 10 for n in heights) + 6
    full_h = max(h, needed)
    rect(layer, [x, y, w, full_h], fill=PANEL, stroke=THIN, stroke_style={"stroke_width": 0.8})
    layer.text([x + 12, y + 10, w - 20, 16], header, style={"class": "noteh"})
    hline(layer, x + 12, x + w - 12, y + 30, THIN, 0.8)
    cy = y + 40
    for i, (it, n) in enumerate(zip(items, heights), 1):
        if numbered:
            layer.text([x + 12, cy, 18, 14], f"{i}.", style={"class": "lbl", "color": RED})
            layer.text([x + 32, cy, w - 44, n * 16 + 4], it, style={"class": "note"})
        else:
            dot(layer, [x + 16, cy + 6], 1.6, SOFT)
            layer.text([x + 26, cy, w - 38, n * 16 + 4], it, style={"class": "note"})
        cy += n * 16 + 10
    return y + full_h


def table(layer, box, headers, rows, widths, *, hfill=PANEL2):
    x, y, w, h = box
    rh = 20
    rect(layer, [x, y, w, rh], fill=hfill, stroke=INK, stroke_style={"stroke_width": 1.0})
    cx = x
    for head, ww in zip(headers, widths):
        layer.text([cx + 7, y + 5, ww - 10, 14], head, style={"class": "th"})
        cx += ww
    cy = y + rh
    for r in rows:
        cx = x
        for val, ww in zip(r, widths):
            st = "tdm" if (val and (val[0].isdigit() or val[0] in "±Ø⌀")) else "td"
            layer.text([cx + 7, cy + 4, ww - 10, 14], val, style={"class": st})
            cx += ww
        hline(layer, x, x + w, cy + rh, THIN, 0.6)
        cy += rh
    rect(layer, [x, y, w, cy - y], fill="none", stroke=INK, stroke_style={"stroke_width": 1.0})
    cx = x
    for ww in widths[:-1]:
        cx += ww
        vline(layer, cx, y, cy, THIN, 0.6)
    return cy


# --------------------------------------------------------------------------- #
# Trebuchet geometry — solved once in machine space (metres), reused           #
# --------------------------------------------------------------------------- #

PIVOT = (0.0, 3.05)          # main axle height above ground
ARM_L = 4.80                 # long (sling) arm, m
ARM_S = 1.25                 # short (counterweight) arm, m
CW_LINK = 0.95               # counterweight hanger length, m
CW_HALF = 0.58               # counterweight box half-size, m
SLING_L = 4.55               # sling length, m
FOOT_F = (1.20, 0.0)         # front A-frame foot (throwing side)
FOOT_B = (-1.45, 0.0)        # rear A-frame foot
GUY = (-2.15, 0.0)           # rear brace ground anchor
SILL = (-2.35, 2.95)         # ground-sill x-extents


class MScale:
    """Map machine space (metres, y-up) to a sheet box (px, y-down)."""

    def __init__(self, ox, oy, s):
        self.ox, self.oy, self.s = ox, oy, s

    def p(self, x, y):
        return [self.ox + x * self.s, self.oy - y * self.s]

    def d(self, metres):           # length → px
        return metres * self.s


def treb(theta_deg):
    """Return key trebuchet points (m) for a long-arm angle ``theta`` (deg, y-up)."""
    a = math.radians(theta_deg)
    dx, dy = math.cos(a), math.sin(a)
    long_tip = (PIVOT[0] + ARM_L * dx, PIVOT[1] + ARM_L * dy)
    short_tip = (PIVOT[0] - ARM_S * dx, PIVOT[1] - ARM_S * dy)
    cw_top = (short_tip[0], short_tip[1] - CW_LINK)          # hanger swings vertical
    cw_c = (cw_top[0], cw_top[1] - CW_HALF)
    return dict(pivot=PIVOT, long_tip=long_tip, short_tip=short_tip,
                cw_top=cw_top, cw_c=cw_c)


def beam_quad(M, a, b, width_m):
    """Four page points for a beam segment a→b with thickness ``width_m`` (m)."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * width_m / 2, dx / L * width_m / 2
    return [M.p(ax + nx, ay + ny), M.p(bx + nx, by + ny),
            M.p(bx - nx, by - ny), M.p(ax - nx, ay - ny)]


def draw_frame(layer, M, *, ground=True, label=False):
    """The A-frame, ground sills and axle, in side elevation."""
    if ground:
        hline(layer, M.p(SILL[0] - 0.25, 0)[0], M.p(SILL[1] + 0.25, 0)[0],
              M.p(0, 0)[1], OBJ, 2.4)
        # ground hatching ticks
        gx0 = M.p(SILL[0] - 0.2, 0)[0]
        gy = M.p(0, 0)[1]
        x = gx0
        while x < M.p(SILL[1] + 0.2, 0)[0]:
            line(layer, [x, gy], [x - 7, gy + 9], FAINT, 0.7)
            x += 13
    # sills
    line(layer, M.p(SILL[0], 0.04), M.p(SILL[1], 0.04), OBJ, 3.0)
    # A-frame legs (as solid timbers)
    for foot in (FOOT_F, FOOT_B):
        poly(layer, beam_quad(M, foot, PIVOT, 0.16), closed=True,
             fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.4})
    # rear guy brace
    poly(layer, beam_quad(M, GUY, (PIVOT[0] - 0.05, PIVOT[1] - 0.55), 0.10),
         closed=True, fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.2})
    # collar / cross tie
    line(layer, M.p(-0.55, 1.65), M.p(0.5, 1.65), OBJ, 1.6)
    # axle boss + centreline
    p = M.p(*PIVOT)
    ring(layer, p, 12, OBJ, 1.8, fill=PANEL)
    dot(layer, p, 3, OBJ)
    cl_cross(layer, p, 26)
    if label:
        leader(layer, [p[0] + 9, p[1] - 9], [p[0] + 70, p[1] - 40], "MAIN AXLE", style="lbl")


def draw_arm(layer, M, pts, *, sling=True, projectile=True, cw=True, mode="cocked"):
    """Throwing arm + counterweight + sling for the given posture points."""
    # arm beam (tapered: thicker at pivot)
    poly(layer, beam_quad(M, pts["short_tip"], pts["pivot"], 0.16) , closed=True,
         fill="#E7E2D2", stroke=OBJ, stroke_style={"stroke_width": 1.6})
    poly(layer, beam_quad(M, pts["pivot"], pts["long_tip"], 0.12), closed=True,
         fill="#E7E2D2", stroke=OBJ, stroke_style={"stroke_width": 1.6})
    # counterweight hanger + box
    if cw:
        line(layer, M.p(*pts["short_tip"]), M.p(*pts["cw_top"]), OBJ, 1.6)
        line(layer, M.p(pts["short_tip"][0] - 0.18, pts["short_tip"][1]),
             M.p(pts["cw_top"][0] - 0.18, pts["cw_top"][1]), OBJ, 1.0)
        line(layer, M.p(pts["short_tip"][0] + 0.18, pts["short_tip"][1]),
             M.p(pts["cw_top"][0] + 0.18, pts["cw_top"][1]), OBJ, 1.0)
        cc = pts["cw_c"]
        box = [M.p(cc[0] - CW_HALF, cc[1] + CW_HALF)[0],
               M.p(cc[0] - CW_HALF, cc[1] + CW_HALF)[1],
               M.d(2 * CW_HALF), M.d(2 * CW_HALF)]
        rect(layer, box, fill="#DCD6BE", stroke=OBJ, stroke_style={"stroke_width": 1.8})
        hatch(layer, box, gap=9, color=OLIVE, width=0.6)
        dot(layer, M.p(*pts["short_tip"]), 4, OBJ)
        dot(layer, M.p(*pts["cw_top"]), 3, OBJ)
    # sling
    if sling:
        lt = pts["long_tip"]
        if mode == "cocked":
            pouch = (lt[0] - 3.05, 0.13)
        else:  # release — sling extended up-forward
            pouch = (lt[0] + SLING_L * math.cos(math.radians(48)),
                     lt[1] + SLING_L * math.sin(math.radians(48)))
        line(layer, M.p(*lt), M.p(*pouch), OBJ, 1.1)
        line(layer, M.p(lt[0], lt[1] - 0.05), M.p(pouch[0], pouch[1] - 0.05), OBJ, 0.8)
        if projectile:
            ring(layer, M.p(*pouch), 8, OBJ, 1.6, fill="#CFC7AE")
            dot(layer, M.p(*pouch), 2, OBJ)
        dot(layer, M.p(*lt), 3.5, OBJ)
    else:
        dot(layer, M.p(*pts["long_tip"]), 3.5, OBJ)


# Parameter schedule reused across sheets.
PARAMS = [
    ("Throwing-arm length", "L₁", "4 800 mm"),
    ("Counterweight arm", "L₂", "1 250 mm"),
    ("Lever ratio L₁:L₂", "—", "3.84 : 1"),
    ("Axle height", "h", "3 050 mm"),
    ("Counterweight mass", "M", "2 000 kg"),
    ("Projectile mass", "m", "15 kg"),
    ("Sling length", "Lₛ", "4 550 mm"),
    ("Release velocity", "v", "≈ 47 m/s"),
    ("Max range", "R", "≈ 185 m"),
]


def spec_panel(layer, box, header="DESIGN PARAMETERS", rows=PARAMS):
    x, y, w, h = box
    rect(layer, box, fill=PANEL, stroke=THIN, stroke_style={"stroke_width": 0.8})
    layer.text([x + 12, y + 10, w - 20, 16], header, style={"class": "noteh"})
    hline(layer, x + 12, x + w - 12, y + 30, THIN, 0.8)
    cy = y + 38
    for name, sym, val in rows:
        layer.text([x + 12, cy, w - 110, 14], name, style={"class": "note", "font_size": 11})
        layer.text([x + w - 96, cy, 88, 14], val,
                   style={"class": "dim", "align": "right", "color": INK})
        cy += 20
    return cy


# --------------------------------------------------------------------------- #
# Front matter                                                                 #
# --------------------------------------------------------------------------- #

def page_cover(builder):
    global _sheet
    _sheet += 1
    layer = new_layer(builder, "cover")
    rect(layer, [0, 0, W, H], fill=BP)
    # blueprint grid
    for gx in range(0, W, 32):
        vline(layer, gx, 0, H, "#1C3C4F", 0.6)
    for gy in range(0, H, 32):
        hline(layer, 0, W, gy, "#1C3C4F", 0.6)
    rect(layer, [OUTER, OUTER, W - 2 * OUTER, H - 2 * OUTER], fill="none",
         stroke=BPL, stroke_style={"stroke_width": 1.4})
    # hero side-elevation of the machine in blueprint white
    M = MScale(ox=905, oy=812, s=118)
    pts = treb(-33)
    # ground
    hline(layer, M.p(SILL[0] - 0.3, 0)[0], M.p(SILL[1] + 0.6, 0)[0], M.p(0, 0)[1], BPL, 1.6)
    for foot in (FOOT_F, FOOT_B):
        poly(layer, beam_quad(M, foot, PIVOT, 0.16), closed=True, fill="none",
             stroke=BPW, stroke_style={"stroke_width": 1.6})
    poly(layer, beam_quad(M, GUY, (PIVOT[0] - 0.05, PIVOT[1] - 0.55), 0.10), closed=True,
         fill="none", stroke=BPL, stroke_style={"stroke_width": 1.2})
    poly(layer, beam_quad(M, pts["short_tip"], pts["long_tip"], 0.13), closed=True,
         fill="none", stroke=BPW, stroke_style={"stroke_width": 2.0})
    line(layer, M.p(*pts["short_tip"]), M.p(*pts["cw_top"]), BPW, 1.4)
    cc = pts["cw_c"]
    rect(layer, [M.p(cc[0] - CW_HALF, cc[1] + CW_HALF)[0], M.p(cc[0] - CW_HALF, cc[1] + CW_HALF)[1],
                 M.d(2 * CW_HALF), M.d(2 * CW_HALF)], fill="none", stroke=BPW,
         stroke_style={"stroke_width": 1.8})
    lt = pts["long_tip"]
    pouch = (lt[0] - 3.05, 0.13)
    line(layer, M.p(*lt), M.p(*pouch), BPL, 1.2)
    ring(layer, M.p(*pouch), 7, BPW, 1.4)
    ring(layer, M.p(*PIVOT), 11, BPW, 1.6)
    cl_cross(layer, M.p(*PIVOT), 24, BPL)

    layer.text([FX0 + 6, 150, 700, 22], "TECHNICAL DRAWING PACKAGE", style={"class": "hk"})
    layer.text([FX0 + 6, 188, 760, 170],
               "Counterweight\nTrebuchet", style={"class": "h1"})
    hline(layer, FX0 + 6, FX0 + 132, 360, BPL, 3)
    layer.text([FX0 + 6, 384, 640, 60],
               "General arrangement, structural, mechanism and detail schematics —\n"
               "a 30-sheet drawing set authored entirely with the FrameGraph Python SDK.",
               style={"class": "hsub"})
    # a small blueprint title block
    bx, by = FX0 + 6, 470
    rect(layer, [bx, by, 360, 96], fill="none", stroke=BPL, stroke_style={"stroke_width": 1.2})
    vline(layer, bx + 220, by, by + 96, BPL, 1.0)
    hline(layer, bx, bx + 220, by + 48, BPL, 1.0)
    for (lbl, val, ox, oy) in [("DRAWING NO.", "TREB-GA-00", 10, 8),
                               ("SHEET", "01 / 30", 10, 56),
                               ("SCALE", "AS NOTED", 230, 8),
                               ("REV", "A", 230, 56)]:
        layer.text([bx + ox, by + oy, 200, 12], lbl,
                   style={"class": "tbl", "color": BPL})
        layer.text([bx + ox, by + oy + 14, 200, 18], val,
                   style={"class": "tbv", "color": BPW, "font_family": MONO})
    layer.text([FX0 + 6, H - 70, 700, 16],
               "framegraph.sdk · DocumentBuilder · MScale · Path · Chart · Mat4.isometric",
               style={"class": "small", "color": BPL})


def page_index(builder):
    layer = sheet(builder, "TREB-IDX-01", "Drawing register & sheet index",
                  "Front matter · contents", scale="—", material="—")
    intro = ("This package documents a gravity (counterweight) trebuchet at 1:25 unless "
             "noted. Sheets are grouped A–F; every sheet carries its own title block, "
             "scale and revision. Read sheet 03 (general notes) before fabrication.")
    layer.text([FX0 + 16, FY0 + 76, 1000, 40], intro, style={"class": "lede"})
    rows = [
        ("01", "TREB-GA-00", "Cover — general arrangement (blueprint)", "AS NOTED"),
        ("02", "TREB-IDX-01", "Drawing register & sheet index", "—"),
        ("03", "TREB-GN-01", "General notes, tolerances & materials schedule", "—"),
        ("04", "TREB-GA-01", "General arrangement — side elevation (cocked)", "1:25"),
        ("05", "TREB-GA-02", "General arrangement — launch geometry & swept arc", "1:25"),
        ("06", "TREB-GA-03", "General arrangement — front elevation & plan", "1:25"),
        ("07", "TREB-GA-04", "General arrangement — isometric view", "1:30"),
        ("08", "TREB-STR-01", "Structure — base sills & frame plan", "1:25"),
        ("09", "TREB-STR-02", "Structure — A-frame upright elevation", "1:20"),
        ("10", "TREB-STR-03", "Structure — cross-beam & axle housing", "1:15"),
        ("11", "TREB-STR-04", "Structure — joinery & bracing details", "1:8"),
        ("12", "TREB-STR-05", "Structure — frame load paths (free body)", "N.T.S."),
        ("13", "TREB-ARM-01", "Throwing arm — elevation & sections", "1:20"),
        ("14", "TREB-ARM-02", "Throwing arm — section schedule & taper", "1:20"),
        ("15", "TREB-ARM-03", "Main axle & pivot bearing assembly", "1:8"),
        ("16", "TREB-ARM-04", "Counterweight box assembly", "1:15"),
        ("17", "TREB-ARM-05", "Sling & pouch geometry", "1:20"),
        ("18", "TREB-MEC-01", "Cocking winch, drum & pawl", "1:12"),
        ("19", "TREB-MEC-02", "Trigger / release-hook mechanism", "1:5"),
        ("20", "TREB-MEC-03", "Kinematic linkage schematic", "N.T.S."),
        ("21", "TREB-MEC-04", "Release-angle & sling-slip geometry", "N.T.S."),
        ("22", "TREB-MEC-05", "Throw sequence — four phases", "1:40"),
        ("23", "TREB-ANL-01", "Free-body diagram at release", "N.T.S."),
        ("24", "TREB-ANL-02", "Energy-transfer schematic", "N.T.S."),
        ("25", "TREB-ANL-03", "Lever & mechanical-advantage diagram", "N.T.S."),
        ("26", "TREB-ANL-04", "Trajectory & range chart", "N.T.S."),
        ("27", "TREB-ANL-05", "Performance — tip speed vs CW ratio", "N.T.S."),
        ("28", "TREB-DET-01", "Axle pin & gudgeon detail", "1:4"),
        ("29", "TREB-DET-02", "Sling release-pin detail", "1:2"),
        ("30", "TREB-DET-03", "Exploded assembly & bill of materials", "1:30"),
    ]
    half = 15
    table(layer, [FX0 + 16, FY0 + 124, 632, 0], ["SHT", "DRAWING NO.", "TITLE", "SCALE"],
          rows[:half], [44, 132, 392, 64])
    table(layer, [FX0 + 666, FY0 + 124, 632, 0], ["SHT", "DRAWING NO.", "TITLE", "SCALE"],
          rows[half:], [44, 132, 392, 64])


def page_notes(builder):
    layer = sheet(builder, "TREB-GN-01", "General notes, tolerances & materials",
                  "Front matter · general notes", scale="—", material="—")
    notes_panel(layer, [FX0 + 16, FY0 + 76, 408, 360], "GENERAL NOTES", [
        "All dimensions in millimetres unless noted; angles in degrees.",
        "Drawings are first-angle projection (ISO 128). Do not scale the drawing — work to figured dimensions.",
        "Timber: seasoned European oak, moisture content ≤ 18%. Grain to run along member length.",
        "Ironwork: wrought iron / mild steel; axle journals case-hardened and greased.",
        "All load-bearing joints pegged with 24 mm oak treenails plus iron strapping.",
        "Counterweight ballast: lead pigs or rubble in a banded oak crate — see sheet 16.",
        "Commission unloaded; proof-load the frame to 1.25× working counterweight.",
    ])
    notes_panel(layer, [FX0 + 440, FY0 + 76, 408, 250], "TOLERANCES (ISO 2768-m)", [
        "Linear  ±0.5 mm  up to 30 mm; ±1.0 mm to 400 mm; ±2.0 mm to 2000 mm.",
        "Over 2000 mm  ±0.3% of nominal length.",
        "Angular  ±0°30′ on machined faces; ±1° on framing.",
        "Axle bore / journal fit  H8/f7 running clearance.",
        "Surface texture on bearing journals  Ra 1.6 µm.",
    ])
    # materials schedule
    layer.text([FX0 + 440, FY0 + 340, 400, 14], "MATERIALS SCHEDULE", style={"class": "noteh"})
    table(layer, [FX0 + 440, FY0 + 360, 408, 0], ["ITEM", "MATERIAL", "SPEC"], [
        ("Main frame", "Oak", "Quercus robur"),
        ("Throwing arm", "Laminated ash", "glued + banded"),
        ("Main axle", "Wrought iron", "Ø90 journal"),
        ("Bearings", "Bronze", "cast, split"),
        ("Counterweight", "Lead / rubble", "2 000 kg"),
        ("Sling", "Hemp rope", "Ø16, 4-strand"),
        ("Fixings", "Iron", "treenail + strap"),
    ], [120, 150, 138])
    spec_panel(layer, [FX0 + 868, FY0 + 76, 430, 250])
    notes_panel(layer, [FX0 + 868, FY0 + 340, 430, 130], "REVISIONS", [
        "Rev A — first issue. Geometry frozen for prototype build.",
    ], numbered=False)


# --------------------------------------------------------------------------- #
# Section A — general arrangement                                             #
# --------------------------------------------------------------------------- #

def page_ga_side(builder):
    layer = sheet(builder, "TREB-GA-01", "General arrangement — side elevation",
                  "A · general arrangement", scale="1:25")
    spec_panel(layer, [FX0 + 16, FY0 + 80, 300, 250])
    notes_panel(layer, [FX0 + 16, FY0 + 344, 300, 150], "POSTURE", [
        "Shown cocked (armed): long arm down on the throwing side, counterweight raised.",
        "Counterweight hanger swings free — always plumb under the short-arm tip.",
    ], numbered=False)

    M = MScale(ox=792, oy=742, s=132)
    pts = treb(-33)
    draw_frame(layer, M, label=True)
    draw_arm(layer, M, pts, mode="cocked")
    view_label(layer, 360, FY0 + 70, "SIDE ELEVATION — COCKED", "1:25")

    # dimensions
    gy = M.p(0, 0)[1]
    # axle height
    px, py = M.p(*PIVOT)
    dim_v(layer, M.p(SILL[0] - 0.15, 0)[0] - 18, py, gy, "3050",
          ext_to=M.p(SILL[0] - 0.15, 0)[0], right=False)
    # base length (sill extents)
    dim_h(layer, M.p(SILL[0], 0)[0], M.p(SILL[1], 0)[0], gy + 40, "5300",
          ext_to=gy, above=False)
    # wheelbase feet
    dim_h(layer, M.p(*FOOT_B)[0], M.p(*FOOT_F)[0], gy + 18, "2650", ext_to=gy, above=True)
    # counterweight callouts
    leader(layer, M.p(*pts["cw_c"]), [M.p(*pts["cw_c"])[0] - 70, M.p(*pts["cw_c"])[1] + 40],
           "CW BOX 2000 kg", style="lbl")
    leader(layer, M.p(*pts["long_tip"]), [M.p(*pts["long_tip"])[0] - 16, M.p(*pts["long_tip"])[1] - 56],
           "SLING SWIVEL", style="lbl", align="right")
    # arm length leaders
    mid_long = ((PIVOT[0] + pts["long_tip"][0]) / 2, (PIVOT[1] + pts["long_tip"][1]) / 2)
    leader(layer, M.p(*mid_long), [M.p(*mid_long)[0] + 20, M.p(*mid_long)[1] + 56],
           "L₁ = 4800 (long arm)", style="lblr")
    mid_short = ((PIVOT[0] + pts["short_tip"][0]) / 2, (PIVOT[1] + pts["short_tip"][1]) / 2)
    leader(layer, M.p(*mid_short), [M.p(*mid_short)[0] - 30, M.p(*mid_short)[1] - 44],
           "L₂ = 1250", style="lblr")
    bubble(layer, [M.p(*PIVOT)[0] + 44, M.p(*PIVOT)[1] + 36], "A")


def page_ga_launch(builder):
    layer = sheet(builder, "TREB-GA-02", "General arrangement — launch geometry",
                  "A · general arrangement", scale="1:25")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "LAUNCH GEOMETRY", [
        "Counterweight falls; the arm sweeps ~150° and the sling whips the projectile up and over.",
        "Release occurs as the sling open-link slips the fixed pin near 45° of arm past vertical.",
        "Phantom (dashed) outline shows the cocked start posture.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 296, 300, 198],
               header="KEY ANGLES",
               rows=[("Arm sweep", "Δθ", "≈ 150°"),
                     ("Release angle", "—", "≈ 45°"),
                     ("Sling at release", "—", "≈ 48° up"),
                     ("Tip speed", "v_t", "≈ 28 m/s"),
                     ("Release speed", "v", "≈ 47 m/s")])

    M = MScale(ox=820, oy=800, s=78)
    pts0 = treb(-33)
    pts1 = treb(108)
    draw_frame(layer, M)
    # swept arc of the long tip
    n = 26
    arc = []
    for i in range(n + 1):
        th = -33 + (108 - (-33)) * i / n
        arc.append(M.p(*treb(th)["long_tip"]))
    poly(layer, arc, stroke=BLUE, fill="none", stroke_style={"stroke_width": 1.0,
         "stroke_dasharray": [6, 4]})
    arrowhead(layer, arc[-1], math.atan2(arc[-1][1] - arc[-3][1], arc[-1][0] - arc[-3][0]), BLUE, 9)
    # cocked phantom
    poly(layer, beam_quad(M, pts0["short_tip"], pts0["long_tip"], 0.10), closed=True,
         fill="none", stroke=HID, stroke_style={"stroke_width": 1.0, "stroke_dasharray": [7, 5]})
    line(layer, M.p(*pts0["short_tip"]), M.p(*pts0["cw_top"]), HID, 0.9, stroke_dasharray=[7, 5])
    # release posture (solid) — arm + counterweight, projectile leaving the tip
    draw_arm(layer, M, pts1, sling=False, cw=True)
    lt = pts1["long_tip"]
    a_v = math.radians(45)
    vtip = [M.p(*lt)[0] + 120 * math.cos(a_v), M.p(*lt)[1] - 120 * math.sin(a_v)]
    line(layer, M.p(*lt), vtip, RED, 2.6)
    arrowhead(layer, vtip, math.atan2(vtip[1] - M.p(*lt)[1], vtip[0] - M.p(*lt)[0]), RED, 12)
    ring(layer, M.p(*lt), 7, OBJ, 1.6, fill="#CFC7AE")
    view_label(layer, 380, FY0 + 70, "LAUNCH GEOMETRY — RELEASE POSTURE", "1:25")
    leader(layer, arc[n // 2], [arc[n // 2][0] + 30, arc[n // 2][1] - 40],
           "SWEPT ARC OF TIP", style="lblb")
    leader(layer, vtip, [vtip[0] + 8, vtip[1] - 26], "RELEASE  v @ ~45°", style="lblr")


def page_ga_front_plan(builder):
    layer = sheet(builder, "TREB-GA-03", "General arrangement — front elevation & plan",
                  "A · general arrangement", scale="1:25")
    # FRONT ELEVATION (left)
    view_label(layer, FX0 + 40, FY0 + 76, "FRONT ELEVATION", "1:25")
    M = MScale(ox=300, oy=720, s=118)  # here x = transverse (z), y = up
    # two A-frame uprights seen head-on, splayed
    half = 0.95
    apex_y = 3.05
    for s in (-1, 1):
        poly(layer, [M.p(s * half * 1.55, 0), M.p(s * 0.12, apex_y),
                     M.p(s * 0.30, apex_y), M.p(s * half * 1.55 + s * 0.22, 0)],
             closed=True, fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.4})
    # axle across, counterweight box centred
    line(layer, M.p(-0.45, apex_y), M.p(0.45, apex_y), OBJ, 3.0)
    ring(layer, M.p(0, apex_y), 9, OBJ, 1.6, fill=PANEL)
    rect(layer, [M.p(-CW_HALF, 2.3)[0], M.p(-CW_HALF, 2.3)[1], M.d(2 * CW_HALF), M.d(2 * CW_HALF)],
         fill="#DCD6BE", stroke=OBJ, stroke_style={"stroke_width": 1.6})
    hatch(layer, [M.p(-CW_HALF, 2.3)[0], M.p(-CW_HALF, 2.3)[1], M.d(2 * CW_HALF), M.d(2 * CW_HALF)],
          gap=9, color=OLIVE)
    line(layer, M.p(0, apex_y), M.p(0, 2.3 + 0.04)[0:2] if False else M.p(0, 2.88), OBJ, 1.4)
    hline(layer, M.p(-1.6, 0)[0], M.p(1.6, 0)[0], M.p(0, 0)[1], OBJ, 2.4)
    gy = M.p(0, 0)[1]
    dim_h(layer, M.p(-half * 1.55, 0)[0], M.p(half * 1.55, 0)[0], gy + 34, "2950",
          ext_to=gy, above=False)
    dim_v(layer, M.p(-1.55, 0)[0] - 16, M.p(0, apex_y)[1], gy, "3050",
          ext_to=M.p(-1.55, 0)[0], right=False)
    leader(layer, M.p(0, 2.3), [M.p(0, 2.3)[0] + 60, M.p(0, 2.3)[1] + 10],
           "BALLAST CRATE", style="lbl")

    # PLAN (right), looking down: x along, z across
    view_label(layer, 760, FY0 + 76, "PLAN VIEW", "1:25")
    P = MScale(ox=860, oy=410, s=80)   # x machine→page x ; z (across)→page y
    # ground sills (two longitudinal at z=±0.9)
    for z in (-0.9, 0.9):
        rect(layer, [P.p(SILL[0], 0)[0], P.p(0, z)[1] - 5, P.d(SILL[1] - SILL[0]), 10],
             fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.2})
    # cross sills at feet
    for x in (FOOT_B[0], FOOT_F[0], GUY[0]):
        rect(layer, [P.p(x, 0)[0] - 5, P.p(0, 0.9)[1], 10, P.d(1.8)],
             fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.0})
    # axle across centre + arm footprint (centred)
    line(layer, P.p(0, -0.95), P.p(0, 0.95), OBJ, 2.2)
    rect(layer, [P.p(-ARM_S, -0.08)[0], P.p(0, 0.08)[1], P.d(ARM_S + ARM_L), P.d(0.16)],
         fill="#E7E2D2", stroke=OBJ, stroke_style={"stroke_width": 1.2})
    cl_cross(layer, P.p(0, 0), 18)
    centerline(layer, P.p(SILL[0] - 0.2, 0), P.p(ARM_L + 0.3, 0))
    dim_v(layer, P.p(SILL[0], 0)[0] - 16, P.p(0, -0.9)[1], P.p(0, 0.9)[1], "1800",
          ext_to=P.p(SILL[0], 0)[0], right=False)
    dim_h(layer, P.p(SILL[0], 0)[0], P.p(SILL[1], 0)[0], P.p(0, 0.9)[1] + 30, "5300",
          ext_to=P.p(0, 0.9)[1], above=False)
    leader(layer, P.p(ARM_L * 0.6, 0), [P.p(ARM_L * 0.6, 0)[0], P.p(0, -0.9)[1] - 26],
           "THROWING ARM envelope over sills", style="lbl")


def _iso_segments():
    """Wire model of the machine in 3-D (x throw, y up, z across)."""
    segs = []

    def add(a, b, color=OBJ, w=1.2):
        segs.append((Vec3(*a), Vec3(*b), color, w))
    pts = treb(-33)
    for z in (-0.9, 0.9):
        add((FOOT_F[0], 0, z), (0, 3.05, z))
        add((FOOT_B[0], 0, z), (0, 3.05, z))
        add((GUY[0], 0, z), (0, 2.5, z), OBJ, 1.0)
        add((SILL[0], 0.02, z), (SILL[1], 0.02, z), OBJ, 1.4)
    # cross sills + axle
    for x in (FOOT_B[0], FOOT_F[0], GUY[0]):
        add((x, 0.02, -0.9), (x, 0.02, 0.9), OBJ, 1.0)
    add((0, 3.05, -0.95), (0, 3.05, 0.95), OBJ, 1.8)
    add((-0.55, 1.65, -0.9), (-0.55, 1.65, 0.9), OBJ, 0.8)
    # arm (centre plane)
    add((pts["short_tip"][0], pts["short_tip"][1], 0), (pts["long_tip"][0], pts["long_tip"][1], 0), OBJ, 2.2)
    # counterweight box wire
    cc = pts["cw_c"]
    add((pts["short_tip"][0], pts["short_tip"][1], 0), (cc[0], cc[1] + CW_HALF, 0), OBJ, 1.2)
    for zc in (-0.45, 0.45):
        add((cc[0] - CW_HALF, cc[1] - CW_HALF, zc), (cc[0] + CW_HALF, cc[1] - CW_HALF, zc), OLIVE, 1.4)
        add((cc[0] - CW_HALF, cc[1] + CW_HALF, zc), (cc[0] + CW_HALF, cc[1] + CW_HALF, zc), OLIVE, 1.4)
        add((cc[0] - CW_HALF, cc[1] - CW_HALF, zc), (cc[0] - CW_HALF, cc[1] + CW_HALF, zc), OLIVE, 1.4)
        add((cc[0] + CW_HALF, cc[1] - CW_HALF, zc), (cc[0] + CW_HALF, cc[1] + CW_HALF, zc), OLIVE, 1.4)
    # sling + projectile
    add((pts["long_tip"][0], pts["long_tip"][1], 0), (pts["long_tip"][0] - 3.05, 0.13, 0), OBJ, 0.9)
    return segs


def page_ga_iso(builder):
    layer = sheet(builder, "TREB-GA-04", "General arrangement — isometric view",
                  "A · general arrangement", scale="1:30")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "PROJECTION", [
        "Isometric (35.26° elevation) projected through Mat4.isometric from a 3-D wire model.",
        "Cocked posture. Twin A-frames braced fore-and-aft on a ground-sill raft.",
        "For figured dimensions refer to the orthographic sheets 04–06.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 296, 300, 198],
               header="ENVELOPE",
               rows=[("Overall length", "—", "≈ 7 400 mm"),
                     ("Overall width", "—", "1 800 mm"),
                     ("Overall height", "—", "3 900 mm"),
                     ("Mass (empty)", "—", "≈ 850 kg"),
                     ("Mass (armed)", "—", "≈ 2 850 kg")])

    segs = _iso_segments()
    cam = Mat4.isometric()
    proj = [(cam.project(a), cam.project(b), c, w) for a, b, c, w in segs]
    xs = [p.x for a, b, _, _ in proj for p in (a, b)]
    ys = [p.y for a, b, _, _ in proj for p in (a, b)]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    box = [380, FY0 + 90, 900, 700]
    scale = min(box[2] / (maxx - minx), box[3] / (maxy - miny)) * 0.86
    ox = box[0] + (box[2] - (maxx - minx) * scale) / 2
    oy = box[1] + (box[3] - (maxy - miny) * scale) / 2

    def mp(p):
        return [ox + (p.x - minx) * scale, oy + (p.y - miny) * scale]
    for a, b, c, w in proj:
        line(layer, mp(a), mp(b), c, w)
    view_label(layer, 380, FY0 + 70, "ISOMETRIC GENERAL VIEW", "1:30")


# --------------------------------------------------------------------------- #
# Section B — structure                                                        #
# --------------------------------------------------------------------------- #

def page_str_base(builder):
    layer = sheet(builder, "TREB-STR-01", "Structure — base sills & frame plan",
                  "B · structure", scale="1:25")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 170], "BASE FRAME", [
        "Two longitudinal ground sills carry the A-frame feet; three transverse sills tie them and spread bearing onto the ground raft.",
        "Halved-and-pegged crossings; iron straps at every intersection.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 266, 300, 150],
               header="SILL SCHEDULE",
               rows=[("Longitudinal sill", "2 off", "200×250"),
                     ("Transverse sill", "3 off", "180×220"),
                     ("Raft length", "—", "5 300 mm"),
                     ("Raft width", "—", "1 800 mm")])

    P = MScale(ox=820, oy=470, s=150)
    for z in (-0.9, 0.9):
        rect(layer, [P.p(SILL[0], 0)[0], P.p(0, z)[1] - 8, P.d(SILL[1] - SILL[0]), 16],
             fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.4})
    for x in (FOOT_B[0], 0.0, FOOT_F[0]):
        rect(layer, [P.p(x, 0)[0] - 7, P.p(0, 0.92)[1], 14, P.d(1.84)],
             fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.2})
    # A-frame foot footprints (dashed hidden squares)
    for x in (FOOT_B[0], FOOT_F[0]):
        for z in (-0.9, 0.9):
            rect(layer, [P.p(x, 0)[0] - 12, P.p(0, z)[1] - 12, 24, 24], fill="none",
                 stroke=HID, stroke_style={"stroke_width": 1.0, "stroke_dasharray": [5, 3]})
    centerline(layer, P.p(SILL[0] - 0.3, 0), P.p(SILL[1] + 0.3, 0))
    centerline(layer, P.p(0, -1.2), P.p(0, 1.2))
    view_label(layer, 380, FY0 + 70, "BASE FRAME — PLAN", "1:25")
    dim_h(layer, P.p(SILL[0], 0)[0], P.p(SILL[1], 0)[0], P.p(0, 0.92)[1] + 36, "5300",
          ext_to=P.p(0, 0.92)[1], above=False)
    dim_h(layer, P.p(FOOT_B[0], 0)[0], P.p(FOOT_F[0], 0)[0], P.p(0, -0.92)[1] - 22, "2650",
          ext_to=P.p(0, -0.92)[1], above=True)
    dim_v(layer, P.p(SILL[0], 0)[0] - 18, P.p(0, -0.9)[1], P.p(0, 0.9)[1], "1800",
          ext_to=P.p(SILL[0], 0)[0], right=False)
    bubble(layer, [P.p(FOOT_F[0], 0.9)[0] + 34, P.p(FOOT_F[0], 0.9)[1] - 22], "B")
    leader(layer, [P.p(FOOT_F[0], 0.9)[0] + 24, P.p(FOOT_F[0], 0.9)[1] - 18],
           [P.p(FOOT_F[0], 0.9)[0] + 70, P.p(FOOT_F[0], 0.9)[1] - 40],
           "HALVED CROSSING — SEE SHT 11", style="lbl")


def page_str_aframe(builder):
    layer = sheet(builder, "TREB-STR-02", "Structure — A-frame upright",
                  "B · structure", scale="1:20")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 160], "A-FRAME", [
        "Two identical A-frames, braced fore-and-aft, carry the axle. Apex slotted for the bronze bearing housing (sheet 15).",
        "Members in oak; iron straps at apex and feet.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 256, 300, 160],
               header="MEMBER SIZES",
               rows=[("Front leg", "—", "180×200"),
                     ("Rear leg", "—", "180×200"),
                     ("Collar tie", "—", "120×160"),
                     ("Apex height", "h", "3 050 mm"),
                     ("Foot spread", "—", "2 650 mm")])

    M = MScale(ox=760, oy=760, s=170)
    apex = (0, 3.05)
    hline(layer, M.p(SILL[0], 0)[0], M.p(SILL[1], 0)[0], M.p(0, 0)[1], OBJ, 2.6)
    for foot in (FOOT_F, FOOT_B):
        poly(layer, beam_quad(M, foot, apex, 0.20), closed=True, fill=PANEL,
             stroke=OBJ, stroke_style={"stroke_width": 1.6})
    poly(layer, beam_quad(M, (-0.55, 1.65), (0.5, 1.65), 0.14), closed=True, fill=PANEL,
         stroke=OBJ, stroke_style={"stroke_width": 1.4})
    # apex bearing slot
    rect(layer, [M.p(-0.18, 3.18)[0], M.p(-0.18, 3.18)[1], M.d(0.36), M.d(0.30)],
         fill="#D7E0E6", stroke=OBJ, stroke_style={"stroke_width": 1.4})
    ring(layer, M.p(0, 3.05), 12, OBJ, 1.8, fill=WHITE)
    cl_cross(layer, M.p(0, 3.05), 26)
    # iron straps
    for foot in (FOOT_F, FOOT_B):
        line(layer, M.p(foot[0], 0.25), M.p(foot[0] * 0.7, 0.55), RED, 2.2)
    view_label(layer, 360, FY0 + 70, "A-FRAME — ELEVATION", "1:20")
    dim_v(layer, M.p(SILL[0] + 0.1, 0)[0] - 16, M.p(0, 3.05)[1], M.p(0, 0)[1], "3050",
          ext_to=M.p(SILL[0] + 0.1, 0)[0], right=False)
    dim_h(layer, M.p(*FOOT_B)[0], M.p(*FOOT_F)[0], M.p(0, 0)[1] + 34, "2650",
          ext_to=M.p(0, 0)[1], above=False)
    dim_v(layer, M.p(FOOT_F[0] + 0.4, 0)[0] + 90, M.p(-0.0, 1.65)[1], M.p(0, 0)[1], "1650",
          ext_to=M.p(0.5, 1.65)[0], right=True)
    leader(layer, M.p(0, 3.18), [M.p(0, 3.18)[0] + 70, M.p(0, 3.18)[1] - 30],
           "BEARING SLOT", style="lbl")
    leader(layer, M.p(FOOT_F[0] * 0.85, 0.4), [M.p(FOOT_F[0] * 0.85, 0.4)[0] + 60, M.p(0, 0.4)[1] + 20],
           "IRON FOOT STRAP", style="lblr")


def page_str_crossbeam(builder):
    layer = sheet(builder, "TREB-STR-03", "Structure — cross-beam & axle housing",
                  "B · structure", scale="1:15")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 160], "AXLE HOUSING", [
        "Split bronze bearing seats in an oak housing block, capped and bolted to the A-frame apex.",
        "Section A–A taken on the axle centreline (see sheet 04).",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 256, 300, 150],
               header="HOUSING",
               rows=[("Housing block", "—", "300×260"),
                     ("Bearing bore", "Ø", "90 mm"),
                     ("Cap bolts", "4 off", "M20"),
                     ("Bearing", "—", "split bronze")])
    # housing elevation (section A-A): a block with bore, hatched
    bx, by, bw, bh = 470, FY0 + 110, 360, 300
    rect(layer, [bx, by, bw, bh], fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.8})
    hline(layer, bx, bx + bw, by + bh * 0.42, OBJ, 1.4)   # cap joint
    cx, cy = bx + bw / 2, by + bh * 0.52
    # bore + bronze bearing ring
    ring(layer, [cx, cy], 64, OBJ, 1.8, fill=WHITE)
    ring(layer, [cx, cy], 44, OBJ, 1.6, fill="#CBB68A")
    ring(layer, [cx, cy], 30, OBJ, 1.4, fill=WHITE)
    cl_cross(layer, [cx, cy], 86)
    # hatch the solid block quadrants (skip the bore)
    for q in [[bx, by, bw, bh * 0.42]]:
        hatch(layer, q, gap=10)
    # cap bolts
    for sx in (-1, 1):
        for sy in (-1, 1):
            dot(layer, [cx + sx * 100, cy + sy * 80], 4, OBJ)
    view_label(layer, bx, FY0 + 70, "SECTION A–A — AXLE HOUSING", "1:15")
    dim_h(layer, bx, bx + bw, by + bh + 28, "300", ext_to=by + bh, above=False)
    dim_v(layer, bx - 18, by, by + bh, "260", ext_to=bx, right=False)
    leader(layer, [cx + 44, cy - 30], [cx + 150, cy - 70], "Ø90 BORE", style="lbl")
    leader(layer, [cx + 54, cy + 20], [cx + 150, cy + 60], "SPLIT BRONZE BEARING", style="lbl")
    bubble(layer, [cx + 150, cy + 96], "C")


def page_str_joinery(builder):
    layer = sheet(builder, "TREB-STR-04", "Structure — joinery & bracing details",
                  "B · structure", scale="1:8")
    details = [
        ("MORTISE & TENON", "Collar to leg — pegged"),
        ("HALVED CROSSING", "Sill intersection"),
        ("GUSSET STRAP", "Apex iron reinforcement"),
        ("TREENAIL PEG", "Ø24 oak draw-bore"),
    ]
    cells = grid([FX0 + 24, FY0 + 96, 1280, 700], cols=2, rows=2, gap=40)
    for (title, sub), cell in zip(details, cells):
        x, y, w, h = cell
        rect(layer, [x, y, w, h], fill=WHITE, stroke=THIN, stroke_style={"stroke_width": 0.8})
        view_label(layer, x + 16, y + 14, title, None)
        layer.text([x + 16, y + 36, w - 30, 14], sub, style={"class": "small"})
        cx, cy = x + w / 2, y + h / 2 + 16
        if title.startswith("MORTISE"):
            rect(layer, [cx - 90, cy - 30, 180, 60], fill=PANEL, stroke=OBJ,
                 stroke_style={"stroke_width": 1.6})
            rect(layer, [cx + 60, cy - 16, 80, 32], fill=WHITE, stroke=OBJ,
                 stroke_style={"stroke_width": 1.4})  # tenon
            rect(layer, [cx + 130, cy - 16, 70, 32], fill="#E7E2D2", stroke=OBJ,
                 stroke_style={"stroke_width": 1.4})  # mating member
            dot(layer, [cx + 95, cy], 4, OBJ)
            dim_h(layer, cx - 90, cx + 90, cy + 50, "240", ext_to=cy + 30, above=False)
        elif title.startswith("HALVED"):
            rect(layer, [cx - 110, cy - 18, 220, 36], fill="#E7E2D2", stroke=OBJ,
                 stroke_style={"stroke_width": 1.4})
            rect(layer, [cx - 18, cy - 70, 36, 140], fill=PANEL, stroke=OBJ,
                 stroke_style={"stroke_width": 1.4})
            hatch(layer, [cx - 18, cy - 18, 36, 36], gap=8)
            dot(layer, [cx, cy], 4, OBJ)
        elif title.startswith("GUSSET"):
            poly(layer, [[cx - 90, cy + 60], [cx, cy - 70], [cx + 90, cy + 60]],
                 closed=True, fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.4})
            poly(layer, [[cx - 40, cy + 10], [cx, cy - 30], [cx + 40, cy + 10]],
                 closed=True, fill="none", stroke=RED, stroke_style={"stroke_width": 2.0})
            for dx in (-25, 0, 25):
                dot(layer, [cx + dx, cy + 30], 3.5, OBJ)
        else:
            rect(layer, [cx - 80, cy - 22, 160, 44], fill="#E7E2D2", stroke=OBJ,
                 stroke_style={"stroke_width": 1.4})
            rect(layer, [cx - 80, cy + 22, 160, 30], fill=PANEL, stroke=OBJ,
                 stroke_style={"stroke_width": 1.4})
            ring(layer, [cx, cy + 8], 10, OBJ, 1.6, fill=WHITE)
            line(layer, [cx, cy - 30], [cx, cy + 56], OBJ, 2.2)
            leader(layer, [cx, cy + 40], [cx + 70, cy + 40], "Ø24 PEG", style="lbl")


def page_str_loadpath(builder):
    layer = sheet(builder, "TREB-STR-05", "Structure — frame load paths",
                  "B · structure", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "STATIC FREE BODY", [
        "At hold (cocked) the axle reaction R carries arm + counterweight weight; the A-frame legs resolve it to the sills.",
        "Front leg works in compression, rear leg + guy resist the overturning couple from the offset counterweight.",
        "Reactions shown for the armed, static case before release.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 296, 300, 170],
               header="STATIC REACTIONS",
               rows=[("Axle reaction", "R", "≈ 28 kN"),
                     ("Front-leg comp.", "C₁", "≈ 22 kN"),
                     ("Rear-leg comp.", "C₂", "≈ 12 kN"),
                     ("Guy tension", "T", "≈ 6 kN"),
                     ("Sill bearing", "q", "≈ 31 kN")])

    M = MScale(ox=792, oy=740, s=128)
    draw_frame(layer, M)
    pts = treb(-33)
    poly(layer, beam_quad(M, pts["short_tip"], pts["long_tip"], 0.10), closed=True,
         fill="none", stroke=HID, stroke_style={"stroke_width": 1.0, "stroke_dasharray": [7, 5]})
    line(layer, M.p(*pts["short_tip"]), M.p(*pts["cw_top"]), HID, 0.9, stroke_dasharray=[7, 5])

    def fvec(at, ang, length, label, color=RED):
        a = math.radians(ang)
        tip = [at[0] + length * math.cos(a), at[1] - length * math.sin(a)]
        line(layer, at, tip, color, 2.4)
        arrowhead(layer, tip, math.atan2(tip[1] - at[1], tip[0] - at[0]), color, 11)
        layer.text([tip[0] - 30, tip[1] - 20, 80, 14], label,
                   style={"class": "lblr", "align": "center", "color": color})
    # weight of counterweight (down)
    fvec(M.p(*pts["cw_c"]), -90, 70, "W_cw", OLIVE)
    # axle reaction (up)
    fvec(M.p(*PIVOT), 90, 64, "R", RED)
    # leg compression vectors along legs
    fvec(M.p(FOOT_F[0] * 0.5, 1.5), 245, 56, "C₁", BLUE)
    fvec(M.p(FOOT_B[0] * 0.5, 1.5), 295, 50, "C₂", BLUE)
    fvec(M.p(*GUY), 60, 48, "T", BLUE)
    view_label(layer, 360, FY0 + 70, "FRAME FREE-BODY (STATIC, ARMED)", "N.T.S.")
    layer.text([400, FY0 + 100, 360, 16], "ΣF = 0   ·   ΣM_axle = 0",
               style={"class": "dim", "font_size": 13, "color": INK})


# --------------------------------------------------------------------------- #
# Section C — throwing arm                                                     #
# --------------------------------------------------------------------------- #

def page_arm_elev(builder):
    layer = sheet(builder, "TREB-ARM-01", "Throwing arm — elevation & sections",
                  "C · throwing arm", scale="1:20")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 170], "THROWING ARM", [
        "Laminated ash beam, tapered from the axle boss toward each tip; banded with iron at the boss and tips.",
        "Pivots about the axle bore at L₂ from the counterweight tip.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 266, 300, 150],
               header="ARM",
               rows=[("Overall length", "—", "6 050 mm"),
                     ("Boss section", "—", "200×260"),
                     ("Tip section", "—", "120×140"),
                     ("Axle bore", "Ø", "92 mm")])
    # straight elevation of the whole arm laid horizontal
    ax0, ax1 = 360, 1320
    cy = FY0 + 180
    boss = (ax0 + (ax1 - ax0) * ARM_S / (ARM_S + ARM_L))
    # tapered top/bottom edges
    poly(layer, [[ax0, cy - 8], [boss, cy - 24], [ax1, cy - 10],
                 [ax1, cy + 10], [boss, cy + 24], [ax0, cy + 8]],
         closed=True, fill="#E7E2D2", stroke=OBJ, stroke_style={"stroke_width": 1.6})
    ring(layer, [boss, cy], 16, OBJ, 1.8, fill=WHITE)
    dot(layer, [boss, cy], 3, OBJ)
    cl_cross(layer, [boss, cy], 30)
    centerline(layer, [ax0 - 20, cy], [ax1 + 20, cy])
    # iron bands
    for bx in (ax0 + 16, boss, ax1 - 16):
        line(layer, [bx, cy - 26], [bx, cy + 26], RED, 2.4)
    view_label(layer, ax0, FY0 + 130, "ARM — ELEVATION (laid level)", "1:20")
    dim_h(layer, ax0, boss, cy + 60, "1250", ext_to=cy + 24, above=False)
    dim_h(layer, boss, ax1, cy + 60, "4800", ext_to=cy + 24, above=False)
    layer.text([ax0 - 4, cy - 52, 80, 14], "CW TIP", style={"class": "lbl"})
    layer.text([ax1 - 70, cy - 52, 80, 14], "SLING TIP", style={"class": "lbl", "align": "right"})
    bubble(layer, [boss, cy - 70], "D")
    # two cross-sections below
    sy = FY0 + 360
    for i, (label, ww, hh, x) in enumerate([("SECT D–D (boss)", 70, 92, 560),
                                            ("SECT E–E (tip)", 44, 56, 980)]):
        rect(layer, [x - ww / 2, sy - hh / 2, ww, hh], fill=PANEL, stroke=OBJ,
             stroke_style={"stroke_width": 1.6})
        hatch(layer, [x - ww / 2, sy - hh / 2, ww, hh], gap=9)
        if i == 0:
            ring(layer, [x, sy], 14, OBJ, 1.6, fill=WHITE)
        cl_cross(layer, [x, sy], hh / 2 + 14)
        layer.text([x - 90, sy + hh / 2 + 16, 180, 14], label,
                   style={"class": "lbl", "align": "center"})
        dim_h(layer, x - ww / 2, x + ww / 2, sy + hh / 2 + 40,
              "200" if i == 0 else "120", ext_to=sy + hh / 2, above=False)


def page_arm_schedule(builder):
    layer = sheet(builder, "TREB-ARM-02", "Throwing arm — section schedule & taper",
                  "C · throwing arm", scale="1:20")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 150], "TAPER", [
        "Depth tapers linearly from the boss to each tip to follow the bending-moment envelope and shed tip mass.",
        "Section modulus must exceed demand at every station — see schedule and curve.",
    ], numbered=False)
    table(layer, [FX0 + 16, FY0 + 246, 320, 0], ["STN", "x (mm)", "d (mm)", "Z (cm³)"], [
        ("0", "0", "260", "2253"),
        ("1", "900", "232", "1796"),
        ("2", "1800", "204", "1387"),
        ("3", "3000", "176", "1032"),
        ("4", "4200", "150", "750"),
        ("5", "5400", "140", "653"),
    ], [44, 90, 90, 96])

    # bending-moment / section-modulus curve via Chart
    bx, by, bw, bh = 470, FY0 + 110, 820, 560
    rect(layer, [bx, by, bw, bh], fill=WHITE, stroke=THIN, stroke_style={"stroke_width": 0.8})
    view_label(layer, bx + 16, by + 14, "SECTION MODULUS — DEMAND vs PROVIDED", "—")
    fr = Frame(domain=(0, 0, 6.05, 2400), box=(bx + 70, by + 60, bw - 130, bh - 130))
    ch = Chart(fr)
    ch.axes(x_ticks=[0, 1, 2, 3, 4, 5, 6], y_ticks=[0, 600, 1200, 1800, 2400],
            x_format=lambda v: f"{v:g}", y_format=lambda v: f"{int(v)}", grid=True)
    provided = [(0, 2253), (0.9, 1796), (1.8, 1387), (3.0, 1032), (4.2, 750), (5.4, 653)]
    demand = [(x / 10, 2100 * math.sin(math.pi * min(x / 60.5, 1.0)) ** 1.1)
              for x in range(0, 61)]
    ch.line(demand, stroke=RED, width=2.4, smooth=True, label="Moment demand")
    ch.line(provided, stroke=BLUE, width=2.6, label="Z provided")
    ch.legend(at=(bx + 90, by + bh - 70))
    layer.extend(ch.objects())
    layer.text([bx + 16, by + bh - 22, 400, 14], "x — station from boss (m)",
               style={"class": "axis"})


def page_arm_axle(builder):
    layer = sheet(builder, "TREB-ARM-03", "Main axle & pivot bearing assembly",
                  "C · throwing arm", scale="1:8")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 170], "AXLE ASSEMBLY", [
        "Wrought-iron axle through the arm boss, running in split bronze bearings in each A-frame apex.",
        "Section on the axle centreline; arm shown in half-section (hatched) at the boss.",
        "End collars and cotter pins retain the axle laterally.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 286, 300, 130],
               header="FITS",
               rows=[("Journal", "Ø", "90 f7"),
                     ("Bore", "Ø", "90 H8"),
                     ("Clearance", "—", "0.03–0.10"),
                     ("Bearing length", "—", "120 mm")])
    # axle along z (across), drawn horizontal
    cx, cy = 880, FY0 + 320
    axl = 560
    ax0 = cx - axl / 2
    # axle shaft
    rect(layer, [ax0, cy - 16, axl, 32], fill="#D9D2BE", stroke=OBJ,
         stroke_style={"stroke_width": 1.6})
    centerline(layer, [ax0 - 30, cy], [ax0 + axl + 30, cy])
    # two bearing housings
    for hx in (ax0 + 90, ax0 + axl - 90):
        rect(layer, [hx - 36, cy - 60, 72, 120], fill=PANEL, stroke=OBJ,
             stroke_style={"stroke_width": 1.6})
        hatch(layer, [hx - 36, cy - 60, 72, 28], gap=8)
        hatch(layer, [hx - 36, cy + 32, 72, 28], gap=8)
        rect(layer, [hx - 30, cy - 18, 60, 36], fill="#CBB68A", stroke=OBJ,
             stroke_style={"stroke_width": 1.2})  # bronze
    # arm boss centred (half-section hatched)
    rect(layer, [cx - 70, cy - 88, 140, 176], fill="#E7E2D2", stroke=OBJ,
         stroke_style={"stroke_width": 1.8})
    hatch(layer, [cx - 70, cy - 88, 140, 70], gap=10)
    hatch(layer, [cx - 70, cy + 18, 140, 70], gap=10)
    rect(layer, [cx - 70, cy - 16, 140, 32], fill="#D9D2BE", stroke=OBJ,
         stroke_style={"stroke_width": 1.0})  # axle through boss
    # end collars + cotters
    for ex in (ax0 + 6, ax0 + axl - 6):
        rect(layer, [ex - 6, cy - 24, 12, 48], fill=OBJ)
    view_label(layer, ax0 - 40, FY0 + 110, "AXLE ASSEMBLY — LONGITUDINAL SECTION", "1:8")
    dim_h(layer, ax0, ax0 + axl, cy + 108, "1180", ext_to=cy + 88, above=False)
    dim_v(layer, ax0 - 28, cy - 60, cy + 60, "120", ext_to=ax0 + 90 - 36, right=False)
    leader(layer, [cx + 70, cy - 50], [cx + 150, cy - 90], "ARM BOSS (½ SECT)", style="lbl")
    leader(layer, [ax0 + 90, cy + 18], [ax0 + 40, cy + 96], "BRONZE BEARING", style="lbl")
    bubble(layer, [cx, cy - 118], "C")


def page_cw_box(builder):
    layer = sheet(builder, "TREB-ARM-04", "Counterweight box assembly",
                  "C · throwing arm", scale="1:15")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 170], "COUNTERWEIGHT", [
        "Banded oak crate on a free hinge at the short-arm tip; swings to keep ballast plumb through the throw.",
        "Filled with lead pigs or rubble to 2 000 kg. Iron straps on every face; lifting eyes on top rail.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 286, 300, 150],
               header="CRATE",
               rows=[("Internal", "—", "1100³ mm"),
                     ("Ballast mass", "M", "2 000 kg"),
                     ("Hanger length", "—", "950 mm"),
                     ("Hinge pin", "Ø", "40 mm")])
    # front view of crate hung from tip
    cx, cy = 820, FY0 + 300
    s = 230
    # hanger straps from a pin up top
    dot(layer, [cx, cy - 200], 6, OBJ)
    cl_cross(layer, [cx, cy - 200], 22)
    for dx in (-s / 2 + 20, s / 2 - 20):
        line(layer, [cx, cy - 200], [cx + dx, cy - s / 2], OBJ, 2.0)
    rect(layer, [cx - s / 2, cy - s / 2, s, s], fill="#DCD6BE", stroke=OBJ,
         stroke_style={"stroke_width": 2.0})
    hatch(layer, [cx - s / 2, cy - s / 2, s, s], gap=12, color=OLIVE)
    # banding straps
    for fx in (cx - s / 4, cx + s / 4):
        vline(layer, fx, cy - s / 2, cy + s / 2, RED, 2.0)
    for fy in (cy - s / 4, cy + s / 4):
        hline(layer, cx - s / 2, cx + s / 2, fy, RED, 2.0)
    # lifting eyes
    for ex in (cx - s / 2 + 24, cx + s / 2 - 24):
        ring(layer, [ex, cy - s / 2 - 8], 7, OBJ, 1.6, fill=WHITE)
    view_label(layer, cx - s / 2 - 40, FY0 + 110, "BALLAST CRATE — FRONT VIEW", "1:15")
    dim_h(layer, cx - s / 2, cx + s / 2, cy + s / 2 + 30, "1300", ext_to=cy + s / 2, above=False)
    dim_v(layer, cx - s / 2 - 18, cy - s / 2, cy + s / 2, "1300", ext_to=cx - s / 2, right=False)
    dim_v(layer, cx + s / 2 + 60, cy - 200, cy - s / 2, "950", ext_to=cx + s / 2 - 20, right=True)
    leader(layer, [cx + s / 4, cy], [cx + s / 2 + 70, cy + 30], "IRON BANDING", style="lblr")
    leader(layer, [cx, cy - 200], [cx - s / 2 - 30, cy - 170], "HINGE PIN Ø40", style="lbl")


def page_sling(builder):
    layer = sheet(builder, "TREB-ARM-05", "Sling & pouch geometry",
                  "C · throwing arm", scale="1:20")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 180], "SLING", [
        "Two cords of equal length from the arm tip to the pouch. One is fixed; the other ends in an open ring on the release pin.",
        "Sling length tunes release angle and range — see sheet 21.",
        "Pouch: leather, tailored to the projectile.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 296, 300, 150],
               header="SLING",
               rows=[("Cord length", "Lₛ", "4 550 mm"),
                     ("Cord", "Ø", "16 hemp"),
                     ("Pouch length", "—", "320 mm"),
                     ("Release-pin angle", "—", "set on trial")])
    # geometry: arm tip, two cords to pouch, projectile
    tip = (470, FY0 + 200)
    pouch = (1180, FY0 + 480)
    line(layer, tip, pouch, OBJ, 1.6)                       # fixed cord
    line(layer, tip, [pouch[0], pouch[1] - 40], OBJ, 1.4, stroke_dasharray=[2, 2])  # release cord
    dot(layer, tip, 5, OBJ)
    # release pin + open ring at tip
    rect(layer, [tip[0] - 6, tip[1] - 26, 12, 30], fill=OBJ)
    ring(layer, [tip[0], tip[1] - 22], 8, RED, 2.0, fill="none")
    # pouch + projectile
    poly(layer, [[pouch[0] - 30, pouch[1] - 30], [pouch[0] + 30, pouch[1] - 30],
                 [pouch[0] + 20, pouch[1] + 24], [pouch[0] - 20, pouch[1] + 24]],
         closed=True, fill="#CFC7AE", stroke=OBJ, stroke_style={"stroke_width": 1.6})
    ring(layer, [pouch[0], pouch[1] - 4], 18, OBJ, 1.6, fill="#B7AE92")
    view_label(layer, 460, FY0 + 130, "SLING — DEPLOYED GEOMETRY", "1:20")
    # dimension cord length along the line
    midx, midy = (tip[0] + pouch[0]) / 2, (tip[1] + pouch[1]) / 2
    leader(layer, [midx, midy], [midx + 30, midy - 50], "Lₛ = 4550 (each cord)", style="lblr")
    leader(layer, [tip[0], tip[1] - 22], [tip[0] + 80, tip[1] - 60], "RELEASE PIN — SHT 29", style="lbl")
    leader(layer, [pouch[0], pouch[1]], [pouch[0] - 70, pouch[1] + 60], "POUCH + PROJECTILE Ø180", style="lbl")
    bubble(layer, [tip[0] + 30, tip[1] + 30], "F")


# --------------------------------------------------------------------------- #
# Section D — mechanism                                                        #
# --------------------------------------------------------------------------- #

def page_winch(builder):
    layer = sheet(builder, "TREB-MEC-01", "Cocking winch, drum & pawl",
                  "D · mechanism", scale="1:12")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 180], "COCKING", [
        "A windlass winds the arm down against the rising counterweight; a ratchet & pawl hold each increment.",
        "Cable from the drum to the long-arm tip; released by knocking out the pawl once the trigger is engaged.",
        "Two crew on the bars; gear gives ~30:1 advantage.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 286, 300, 150],
               header="WINCH",
               rows=[("Drum", "Ø", "240 mm"),
                     ("Ratchet teeth", "z", "24"),
                     ("Bar radius", "—", "650 mm"),
                     ("Cable", "Ø", "20 hemp")])
    cx, cy = 820, FY0 + 320
    # drum
    ring(layer, [cx, cy], 110, OBJ, 2.0, fill=PANEL)
    ring(layer, [cx, cy], 26, OBJ, 1.6, fill=WHITE)
    cl_cross(layer, [cx, cy], 130)
    dot(layer, [cx, cy], 4, OBJ)
    # ratchet teeth
    for i in range(24):
        a = 2 * math.pi * i / 24
        r0, r1 = 110, 128
        x0, y0 = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
        x1, y1 = cx + r1 * math.cos(a), cy + r1 * math.sin(a)
        a2 = 2 * math.pi * (i + 0.5) / 24
        x2, y2 = cx + r0 * math.cos(a2), cy + r0 * math.sin(a2)
        poly(layer, [[x0, y0], [x1, y1], [x2, y2]], closed=True, fill=OBJ)
    # pawl
    poly(layer, [[cx + 150, cy - 150], [cx + 118, cy - 118], [cx + 150, cy - 110]],
         closed=True, fill=RED, stroke=OBJ, stroke_style={"stroke_width": 1.2})
    dot(layer, [cx + 150, cy - 150], 4, OBJ)
    # winding bars
    for a in (0.6, 0.6 + math.pi):
        line(layer, [cx, cy], [cx + 150 * math.cos(a), cy + 150 * math.sin(a)], OBJ, 3.0)
    # cable off the drum
    line(layer, [cx - 110, cy], [cx - 280, cy + 30], OBJ, 1.6)
    leader(layer, [cx - 280, cy + 30], [cx - 300, cy + 80], "CABLE TO ARM TIP", style="lbl")
    view_label(layer, cx - 280, FY0 + 130, "WINCH & RATCHET", "1:12")
    leader(layer, [cx + 130, cy - 122], [cx + 200, cy - 150], "PAWL", style="lblr")
    leader(layer, [cx + 120, cy + 30], [cx + 220, cy + 80], "RATCHET DRUM Ø240", style="lbl")


def page_trigger(builder):
    layer = sheet(builder, "TREB-MEC-02", "Trigger / release-hook mechanism",
                  "D · mechanism", scale="1:5")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "TRIGGER", [
        "An iron sear hook holds the long-arm tip ring at full cock. A lanyard rotates the sear off the ring to fire.",
        "The sear geometry is self-holding: the load line passes inside the pivot so it cannot creep open.",
        "Detail shown engaged (solid) and released (phantom).",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 296, 300, 140],
               header="SEAR",
               rows=[("Hook stock", "—", "40×60"),
                     ("Pivot pin", "Ø", "30 mm"),
                     ("Hold load", "—", "≈ 14 kN"),
                     ("Lanyard pull", "—", "≈ 120 N")])
    cx, cy = 820, FY0 + 320
    # base bracket
    rect(layer, [cx - 40, cy + 70, 200, 36], fill=PANEL, stroke=OBJ,
         stroke_style={"stroke_width": 1.6})
    hatch(layer, [cx - 40, cy + 70, 200, 36], gap=9)
    # sear hook (engaged)
    poly(layer, [[cx, cy + 70], [cx - 8, cy - 60], [cx + 30, cy - 90],
                 [cx + 70, cy - 70], [cx + 52, cy - 40], [cx + 24, cy - 50],
                 [cx + 30, cy + 10], [cx + 40, cy + 70]],
         closed=True, fill="#D9D2BE", stroke=OBJ, stroke_style={"stroke_width": 1.8})
    dot(layer, [cx + 20, cy + 40], 6, OBJ)                  # pivot
    cl_cross(layer, [cx + 20, cy + 40], 18)
    # arm-tip ring captured by the hook
    ring(layer, [cx + 44, cy - 64], 16, RED, 2.4, fill="none")
    leader(layer, [cx + 44, cy - 64], [cx + 130, cy - 90], "ARM-TIP RING", style="lblr")
    # load line through pivot inside (annotation)
    line(layer, [cx + 44, cy - 64], [cx + 44, cy + 90], BLUE, 1.0, stroke_dasharray=[6, 4])
    leader(layer, [cx + 44, cy + 80], [cx + 140, cy + 60], "LOAD LINE (inside pivot)", style="lblb")
    # lanyard
    line(layer, [cx + 20, cy + 40], [cx - 110, cy + 10], OBJ, 1.2)
    arrowhead(layer, [cx - 110, cy + 10], math.atan2(cy + 10 - (cy + 40), -130), OBJ, 8)
    leader(layer, [cx - 90, cy + 16], [cx - 180, cy + 50], "LANYARD — PULL TO FIRE", style="lbl")
    view_label(layer, cx - 200, FY0 + 130, "RELEASE SEAR — ENGAGED", "1:5")
    bubble(layer, [cx + 90, cy + 30], "G")


def page_kinematics(builder):
    layer = sheet(builder, "TREB-MEC-03", "Kinematic linkage schematic",
                  "D · mechanism", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "KINEMATICS", [
        "The trebuchet is a double pendulum: the arm rotates about the fixed axle while the sling (and the hung counterweight) swing about moving pivots.",
        "Three rigid links — counterweight hanger, arm, sling — share two moving joints; the system has 3 degrees of freedom.",
        "Schematic shows links as lines, fixed pivots as a ground triangle, moving pivots as open circles.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 316, 300, 130],
               header="LINKS",
               rows=[("Arm L₁/L₂", "—", "4800 / 1250"),
                     ("Sling", "Lₛ", "4550"),
                     ("CW hanger", "—", "950"),
                     ("DOF", "—", "3")])

    M = MScale(ox=560, oy=640, s=70)
    pts = treb(28)
    # ground / fixed axle
    p = M.p(*PIVOT)
    poly(layer, [[p[0] - 16, p[1] + 20], [p[0] + 16, p[1] + 20], [p[0], p[1]]],
         closed=True, fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.4})
    for hx in range(-16, 17, 8):
        line(layer, [p[0] + hx, p[1] + 20], [p[0] + hx - 6, p[1] + 28], FAINT, 0.8)
    # links
    line(layer, M.p(*pts["short_tip"]), M.p(*pts["long_tip"]), BLUE, 3.0)       # arm
    line(layer, M.p(*pts["short_tip"]), M.p(*pts["cw_top"]), OLIVE, 3.0)        # hanger
    lt = pts["long_tip"]
    pouch = (lt[0] + SLING_L * math.cos(math.radians(40)),
             lt[1] + SLING_L * math.sin(math.radians(40)))
    line(layer, M.p(*lt), M.p(*pouch), RED, 3.0)                                # sling
    # joints
    for jp, lab, col in [(PIVOT, "O (fixed)", OBJ), (pts["short_tip"], "A", BLUE),
                         (pts["long_tip"], "B", BLUE), (pts["cw_top"], "C", OLIVE),
                         (pouch, "P", RED)]:
        ring(layer, M.p(*jp), 7, col, 1.8, fill=PAPER)
        layer.text([M.p(*jp)[0] + 10, M.p(*jp)[1] - 16, 90, 14], lab,
                   style={"class": "lbl", "color": col})
    view_label(layer, 380, FY0 + 70, "DOUBLE-PENDULUM LINKAGE", "N.T.S.")
    layer.text([400, FY0 + 118, 520, 16],
               "links:  C–A hanger · A–B arm (about O) · B–P sling",
               style={"class": "dim", "font_size": 12, "color": INK})


def page_release_geom(builder):
    layer = sheet(builder, "TREB-MEC-04", "Release-angle & sling-slip geometry",
                  "D · mechanism", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "RELEASE", [
        "Release happens when the open ring slides off the fixed pin — set by the pin angle on the arm tip.",
        "The velocity vector of the projectile at release should point ~45° above horizontal for maximum range.",
        "Tuning the pin angle and sling length walks the release point around the arc.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 316, 300, 130],
               header="RELEASE",
               rows=[("Pin angle", "β", "≈ 30°"),
                     ("Release elev.", "α", "≈ 45°"),
                     ("Speed at rel.", "v", "≈ 47 m/s"),
                     ("Sensitivity", "—", "high")])
    cx, cy = 840, FY0 + 380
    # arm tip with pin
    dot(layer, [cx, cy], 6, OBJ)
    line(layer, [cx, cy], [cx - 160, cy - 70], BLUE, 3.0)   # arm to tip
    leader(layer, [cx - 100, cy - 44], [cx - 140, cy - 110], "ARM TIP", style="lblb")
    # pin direction
    a_pin = math.radians(30)
    line(layer, [cx, cy], [cx + 60 * math.cos(a_pin), cy - 60 * math.sin(a_pin)], OBJ, 2.4)
    leader(layer, [cx + 50, cy - 28], [cx + 110, cy - 70], "RELEASE PIN β=30°", style="lbl")
    # velocity vector ~45
    a_v = math.radians(45)
    vx, vy = cx + 200 * math.cos(a_v), cy - 200 * math.sin(a_v)
    line(layer, [cx, cy], [vx, vy], RED, 3.0)
    arrowhead(layer, [vx, vy], math.atan2(vy - cy, vx - cx), RED, 12)
    leader(layer, [vx, vy], [vx + 20, vy - 30], "v  (release, α=45°)", style="lblr")
    # horizontal datum + angle arc
    hline(layer, cx, cx + 220, cy, FAINT, 0.8, stroke_dasharray=[5, 4])
    arc = Path().move_to(cx + 90, cy).arc_to(90, 90, 0, False, False,
                                             (cx + 90 * math.cos(a_v), cy - 90 * math.sin(a_v)))
    layer.add(arc.object(stroke=RED, fill="none", stroke_style={"stroke_width": 1.0}))
    layer.text([cx + 96, cy - 40, 60, 14], "α", style={"class": "lblr"})
    view_label(layer, 480, FY0 + 130, "RELEASE VELOCITY GEOMETRY", "N.T.S.")


def page_sequence(builder):
    layer = sheet(builder, "TREB-MEC-05", "Throw sequence — four phases",
                  "D · mechanism", scale="1:40")
    phases = [("1 · ARMED", -33), ("2 · DROP", 20), ("3 · WHIP", 80), ("4 · RELEASE", 120)]
    cells = grid([FX0 + 20, FY0 + 96, 1288, 632], cols=4, rows=1, gap=18)
    for (label, th), cell in zip(phases, cells):
        x, y, w, h = cell
        rect(layer, [x, y, w, h], fill=WHITE, stroke=THIN, stroke_style={"stroke_width": 0.8})
        layer.text([x + 12, y + 10, w - 20, 16], label, style={"class": "lblr", "font_size": 13})
        hline(layer, x + 12, x + w - 12, y + 30, THIN, 0.7)
        M = MScale(ox=x + w / 2 - 20, oy=y + h - 70, s=44)
        # mini frame
        hline(layer, M.p(SILL[0], 0)[0], M.p(SILL[1], 0)[0], M.p(0, 0)[1], OBJ, 1.6)
        for foot in (FOOT_F, FOOT_B):
            line(layer, M.p(*foot), M.p(*PIVOT), OBJ, 1.4)
        line(layer, M.p(*GUY), M.p(PIVOT[0], PIVOT[1] - 0.5), OBJ, 1.0)
        ring(layer, M.p(*PIVOT), 5, OBJ, 1.4, fill=PAPER)
        pts = treb(th)
        line(layer, M.p(*pts["short_tip"]), M.p(*pts["long_tip"]), BLUE, 2.6)
        line(layer, M.p(*pts["short_tip"]), M.p(*pts["cw_top"]), OLIVE, 2.0)
        rect(layer, [M.p(pts["cw_c"][0] - CW_HALF, pts["cw_c"][1] + CW_HALF)[0],
                     M.p(pts["cw_c"][0] - CW_HALF, pts["cw_c"][1] + CW_HALF)[1],
                     M.d(2 * CW_HALF), M.d(2 * CW_HALF)], fill="#DCD6BE", stroke=OBJ,
             stroke_style={"stroke_width": 1.2})
        lt = pts["long_tip"]
        if th < 100:
            pouch = (lt[0] - 2.6, 0.12) if th < 10 else (lt[0] - 1.6, lt[1] - 1.4)
        else:
            pouch = (lt[0] + 2.6 * math.cos(math.radians(48)), lt[1] + 2.6 * math.sin(math.radians(48)))
        line(layer, M.p(*lt), M.p(*pouch), RED, 1.4)
        ring(layer, M.p(*pouch), 4, OBJ, 1.4, fill="#CFC7AE")
    view_label(layer, FX0 + 20, FY0 + 70, "THROW SEQUENCE", "1:40")


# --------------------------------------------------------------------------- #
# Section E — analysis (schematic)                                             #
# --------------------------------------------------------------------------- #

def page_fbd(builder):
    layer = sheet(builder, "TREB-ANL-01", "Free-body diagram at release",
                  "E · analysis", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "FREE BODY — ARM", [
        "At the instant of release the arm carries: the axle reaction R; the hanger tension T_cw from the falling counterweight; the sling tension T_s; and its own weight W.",
        "Newton–Euler about the axle gives the angular acceleration that spins the tip.",
        "Vectors are schematic, not to scale.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 316, 300, 130],
               header="AT RELEASE",
               rows=[("Hanger tension", "T_cw", "≈ 26 kN"),
                     ("Sling tension", "T_s", "≈ 9 kN"),
                     ("Tip accel.", "a_t", "≈ 90 m/s²"),
                     ("Ang. velocity", "ω", "≈ 6 rad/s")])
    M = MScale(ox=720, oy=720, s=70)
    pts = treb(108)
    line(layer, M.p(*pts["short_tip"]), M.p(*pts["long_tip"]), INK, 3.0)
    ring(layer, M.p(*PIVOT), 8, OBJ, 1.8, fill=PAPER)
    dot(layer, M.p(*pts["short_tip"]), 4, OBJ)
    dot(layer, M.p(*pts["long_tip"]), 4, OBJ)

    def fvec(at, ang_deg, length, label, color):
        a = math.radians(ang_deg)
        tip = [at[0] + length * math.cos(a), at[1] - length * math.sin(a)]
        line(layer, at, tip, color, 2.6)
        arrowhead(layer, tip, math.atan2(tip[1] - at[1], tip[0] - at[0]), color, 12)
        layer.text([tip[0] - 36, tip[1] - 20, 90, 14], label,
                   style={"class": "lbl", "align": "center", "color": color})
    fvec(M.p(*pts["short_tip"]), -90, 84, "T_cw", OLIVE)
    fvec(M.p(*pts["long_tip"]), 228, 70, "T_s", RED)
    fvec(M.p(*PIVOT), 70, 60, "R", BLUE)
    fvec(M.p(0, PIVOT[1]), -90, 44, "W", FAINT)
    cl_cross(layer, M.p(*PIVOT), 22)
    view_label(layer, 380, FY0 + 70, "ARM FREE-BODY @ RELEASE", "N.T.S.")
    layer.text([400, FY0 + 116, 560, 16], "Σ M_O = I_O · α      τ = T_cw·L₂ − T_s·L₁",
               style={"class": "dim", "font_size": 13, "color": INK})


def page_energy(builder):
    layer = sheet(builder, "TREB-ANL-02", "Energy-transfer schematic",
                  "E · analysis", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 180], "ENERGY", [
        "The counterweight's lost potential energy splits between useful projectile kinetic energy and losses (arm & CW kinetic energy, friction, sling).",
        "Efficiency here ≈ 34% — typical for a fixed-counterweight machine; a hinged crate and longer sling raise it.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 276, 300, 160],
               header="ENERGY BUDGET",
               rows=[("CW potential", "E_p", "49.1 kJ"),
                     ("Projectile KE", "E_k", "16.6 kJ"),
                     ("Arm + CW KE", "—", "24.0 kJ"),
                     ("Friction etc.", "—", "8.5 kJ"),
                     ("Efficiency", "η", "≈ 34 %")])
    # input bar
    bx, by = 470, FY0 + 150
    rect(layer, [bx, by, 720, 56], fill=OLIVE, radius=4)
    layer.text([bx + 14, by + 18, 400, 18], "COUNTERWEIGHT  PE  =  M g Δh  =  49.1 kJ",
               style={"class": "lbl", "color": WHITE, "font_size": 14})
    # split into three streams
    streams = [("PROJECTILE  KE = ½ m v²", 16.6, BLUE),
               ("ARM + CW  kinetic energy", 24.0, "#7E7A52"),
               ("FRICTION · SLING · SOUND", 8.5, FAINT)]
    total = sum(s[1] for s in streams)
    y = by + 130
    for name, val, col in streams:
        w = 720 * val / total
        rect(layer, [bx, y, w, 40], fill=col, radius=4)
        line(layer, [bx + 80, by + 56], [bx + w / 2, y], col, 1.4, stroke_dasharray=[5, 4])
        layer.text([bx + 10, y + 12, w - 16, 16], f"{name}   {val:.1f} kJ",
                   style={"class": "lbl", "color": WHITE, "font_size": 12})
        layer.text([bx + 730, y + 12, 90, 16], f"{100 * val / total:.0f}%",
                   style={"class": "dim", "color": INK})
        y += 58
    view_label(layer, bx, FY0 + 110, "ENERGY FLOW  (PE → KE + LOSSES)", "N.T.S.")
    layer.text([bx, y + 6, 720, 16], "η = E_k / E_p ≈ 0.34",
               style={"class": "dim", "font_size": 14, "color": RED})


def page_lever(builder):
    layer = sheet(builder, "TREB-ANL-03", "Lever & mechanical-advantage diagram",
                  "E · analysis", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 200], "LEVER", [
        "The arm is a class-1 lever about the axle. Force advantage favours the counterweight side; speed advantage favours the long throwing side.",
        "Velocity ratio = L₁ / L₂: the tip moves ~3.84× faster than the counterweight — the sling then doubles tip speed again.",
        "This speed trade is the whole point of the machine.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 316, 300, 130],
               header="RATIOS",
               rows=[("Velocity ratio", "L₁/L₂", "3.84"),
                     ("Tip speed", "v_t", "= ω L₁"),
                     ("Sling gain", "—", "≈ ×1.7"),
                     ("Net speed-up", "—", "≈ ×6.5")])
    cx, cy = 820, FY0 + 300
    L1, L2 = 360, 94
    # lever beam
    line(layer, [cx - L2, cy], [cx + L1, cy], INK, 4.0)
    # fulcrum triangle
    poly(layer, [[cx - 16, cy + 22], [cx + 16, cy + 22], [cx, cy]], closed=True,
         fill=PANEL, stroke=OBJ, stroke_style={"stroke_width": 1.4})
    dot(layer, [cx, cy], 4, OBJ)
    cl_cross(layer, [cx, cy], 20)
    # counterweight force down at L2
    line(layer, [cx - L2, cy], [cx - L2, cy + 90], OLIVE, 3.0)
    arrowhead(layer, [cx - L2, cy + 90], math.pi / 2, OLIVE, 12)
    layer.text([cx - L2 - 44, cy + 96, 90, 14], "M g", style={"class": "lbl", "color": OLIVE})
    # projectile reaction up at L1 + velocity arrow
    line(layer, [cx + L1, cy], [cx + L1, cy - 90], BLUE, 3.0)
    arrowhead(layer, [cx + L1, cy - 90], -math.pi / 2, BLUE, 12)
    layer.text([cx + L1 - 30, cy - 110, 90, 14], "v_t = ωL₁",
               style={"class": "lbl", "color": BLUE, "align": "center"})
    dim_h(layer, cx - L2, cx, cy + 130, "L₂ = 1250", ext_to=cy + 90, above=False)
    dim_h(layer, cx, cx + L1, cy + 130, "L₁ = 4800", ext_to=cy + 90, above=False)
    view_label(layer, cx - L2 - 20, FY0 + 130, "CLASS-1 LEVER", "N.T.S.")


def page_trajectory(builder):
    layer = sheet(builder, "TREB-ANL-04", "Trajectory & range chart",
                  "E · analysis", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 170], "BALLISTICS", [
        "Vacuum trajectories from a 47 m/s release at three launch angles. 45° maximises range; air drag trims the real range by ~15–20%.",
        "Range R = v² sin 2α / g.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 266, 300, 150],
               header="RANGE",
               rows=[("Release speed", "v", "47 m/s"),
                     ("Optimum angle", "α", "45°"),
                     ("Range (vacuum)", "R", "225 m"),
                     ("Range (w/ drag)", "—", "≈ 185 m")])
    bx, by, bw, bh = 470, FY0 + 110, 820, 560
    rect(layer, [bx, by, bw, bh], fill=WHITE, stroke=THIN, stroke_style={"stroke_width": 0.8})
    view_label(layer, bx + 16, by + 14, "PROJECTILE TRAJECTORIES — v = 47 m/s", "N.T.S.")
    fr = Frame(domain=(0, 0, 230, 70), box=(bx + 64, by + 60, bw - 110, bh - 130))
    ch = Chart(fr)
    ch.axes(x_ticks=[0, 50, 100, 150, 200], y_ticks=[0, 20, 40, 60],
            x_format=lambda v: f"{int(v)}", y_format=lambda v: f"{int(v)}", grid=True)
    g, v = 9.81, 47.0
    for ang, col, lab in [(35, BLUE, "35°"), (45, RED, "45° (max)"), (55, OLIVE, "55°")]:
        a = math.radians(ang)
        R = v * v * math.sin(2 * a) / g
        pts = []
        for i in range(41):
            x = R * i / 40
            y = x * math.tan(a) - g * x * x / (2 * v * v * math.cos(a) ** 2)
            pts.append((x, max(y, 0)))
        ch.line(pts, stroke=col, width=2.6, smooth=True, label=lab)
    ch.legend(at=(bx + bw - 230, by + 70))
    layer.extend(ch.objects())
    layer.text([bx + 16, by + bh - 22, 400, 14], "ground range (m)  →",
               style={"class": "axis"})


def page_performance(builder):
    layer = sheet(builder, "TREB-ANL-05", "Performance — tip speed vs CW ratio",
                  "E · analysis", scale="N.T.S.")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 180], "PERFORMANCE", [
        "Release speed climbs with the counterweight-to-projectile mass ratio, but with diminishing returns as more energy goes into accelerating the heavy arm and crate.",
        "Design point at ratio 2000:15 ≈ 133 sits on the knee — heavier ballast buys little extra range for much more frame load.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 286, 300, 130],
               header="DESIGN POINT",
               rows=[("CW mass", "M", "2 000 kg"),
                     ("Proj. mass", "m", "15 kg"),
                     ("Mass ratio", "M/m", "133"),
                     ("Release v", "v", "≈ 47 m/s")])
    bx, by, bw, bh = 470, FY0 + 110, 820, 560
    rect(layer, [bx, by, bw, bh], fill=WHITE, stroke=THIN, stroke_style={"stroke_width": 0.8})
    view_label(layer, bx + 16, by + 14, "RELEASE SPEED vs MASS RATIO", "N.T.S.")
    fr = Frame(domain=(0, 0, 260, 60), box=(bx + 64, by + 60, bw - 110, bh - 130))
    ch = Chart(fr)
    ch.axes(x_ticks=[0, 50, 100, 150, 200, 250], y_ticks=[0, 20, 40, 60],
            x_format=lambda v: f"{int(v)}", y_format=lambda v: f"{int(v)}", grid=True)
    vmax = 56.0
    curve = [(r, vmax * (1 - math.exp(-r / 70.0))) for r in range(0, 261, 5)]
    ch.line(curve, stroke=BLUE, width=3.0, smooth=True, label="release speed")
    layer.extend(ch.objects())
    dp = fr.point(133, vmax * (1 - math.exp(-133 / 70.0)))
    ring(layer, [dp.x, dp.y], 6, RED, 2.2, fill=PAPER)
    vline(layer, dp.x, dp.y, fr.point(133, 0).y, RED, 1.0, stroke_dasharray=[5, 4])
    layer.text([dp.x + 10, dp.y - 6, 180, 14], "DESIGN POINT  M/m=133",
               style={"class": "lblr"})
    layer.text([bx + 16, by + bh - 22, 400, 14], "counterweight / projectile mass ratio  →",
               style={"class": "axis"})


# --------------------------------------------------------------------------- #
# Section F — details & bill of materials                                      #
# --------------------------------------------------------------------------- #

def page_det_axle(builder):
    layer = sheet(builder, "TREB-DET-01", "Axle pin & gudgeon detail",
                  "F · details", scale="1:4")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 170], "AXLE PIN", [
        "Forged wrought-iron axle with shouldered journals and cottered end collars.",
        "Journals ground to Ø90 f7 and greased; shoulders locate the arm boss laterally.",
        "Detail C referenced from sheet 15.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 266, 300, 150],
               header="AXLE",
               rows=[("Overall length", "—", "1 320 mm"),
                     ("Journal", "Ø", "90 f7"),
                     ("Shoulder", "Ø", "120 mm"),
                     ("Cotter slot", "—", "12×40")])
    cx, cy = 840, FY0 + 320
    L = 600
    x0 = cx - L / 2
    centerline(layer, [x0 - 30, cy], [x0 + L + 30, cy])
    # stepped shaft profile (top half mirrored)
    steps = [(0, 24), (60, 24), (60, 44), (120, 44), (120, 60), (480, 60),
             (480, 44), (540, 44), (540, 24), (600, 24)]
    top = [[x0 + sx, cy - r] for sx, r in steps]
    bot = [[x0 + sx, cy + r] for sx, r in reversed(steps)]
    poly(layer, top + bot, closed=True, fill="#D9D2BE", stroke=OBJ,
         stroke_style={"stroke_width": 1.8})
    # cotter holes
    for hx in (x0 + 30, x0 + L - 30):
        rect(layer, [hx - 6, cy - 22, 12, 44], fill=WHITE, stroke=OBJ,
             stroke_style={"stroke_width": 1.0})
    view_label(layer, x0 - 30, FY0 + 130, "AXLE PIN — DETAIL C", "1:4")
    dim_h(layer, x0, x0 + L, cy + 86, "1320", ext_to=cy + 60, above=False)
    dim_h(layer, x0 + 120, x0 + 480, cy + 60, "Ø90 JOURNAL", ext_to=cy + 60, above=True)
    leader(layer, [x0 + 30, cy - 22], [x0 - 20, cy - 80], "COTTER SLOT 12×40", style="lbl")
    leader(layer, [x0 + 90, cy - 44], [x0 + 90, cy - 96], "SHOULDER Ø120", style="lbl")
    bubble(layer, [x0 + L / 2, cy - 110], "C")


def page_det_pin(builder):
    layer = sheet(builder, "TREB-DET-02", "Sling release-pin detail",
                  "F · details", scale="1:2")
    notes_panel(layer, [FX0 + 16, FY0 + 80, 300, 180], "RELEASE PIN", [
        "Curved iron finger on the arm tip. The fixed sling cord stays captive; the open ring of the release cord slides off as the arm passes the set angle.",
        "Pin angle β is adjustable in the tip block to trim release elevation (sheet 21).",
        "Detail F referenced from sheet 17.",
    ], numbered=False)
    spec_panel(layer, [FX0 + 16, FY0 + 296, 300, 130],
               header="PIN",
               rows=[("Stock", "Ø", "22 mm"),
                     ("Reach", "—", "140 mm"),
                     ("Angle β", "—", "20–40° adj"),
                     ("Material", "—", "wrought iron")])
    cx, cy = 840, FY0 + 320
    # tip block
    rect(layer, [cx - 60, cy + 30, 160, 70], fill="#E7E2D2", stroke=OBJ,
         stroke_style={"stroke_width": 1.8})
    hatch(layer, [cx - 60, cy + 30, 160, 70], gap=10)
    # adjustable angle holes
    for dx in (-30, 0, 30):
        ring(layer, [cx + dx, cy + 65], 5, OBJ, 1.2, fill=WHITE)
    # the curved pin
    pin = (Path().move_to(cx, cy + 40)
           .line_to(cx + 8, cy - 70)
           .quad_to((cx + 60, cy - 110), (cx + 96, cy - 78))
           .quad_to((cx + 70, cy - 96), (cx + 30, cy - 70))
           .line_to(cx + 22, cy + 40).close())
    layer.add(pin.object(stroke=OBJ, fill="#D9D2BE", stroke_style={"stroke_width": 1.8}))
    # captured rings
    ring(layer, [cx + 60, cy - 92], 12, RED, 2.2, fill="none")
    leader(layer, [cx + 60, cy - 92], [cx + 150, cy - 110], "RELEASE-CORD RING", style="lblr")
    leader(layer, [cx + 10, cy], [cx - 130, cy - 30], "FIXED-CORD EYE", style="lbl")
    view_label(layer, cx - 130, FY0 + 130, "RELEASE PIN — DETAIL F", "1:2")
    dim_v(layer, cx + 150, cy - 100, cy + 40, "140", ext_to=cx + 96, right=True)
    bubble(layer, [cx - 90, cy + 65], "F")


def page_bom(builder):
    layer = sheet(builder, "TREB-DET-03", "Exploded assembly & bill of materials",
                  "F · details", scale="1:30")
    # exploded iso on the left half: reuse iso wire but offset parts vertically
    segs = _iso_segments()
    cam = Mat4.isometric()
    proj = [(cam.project(a), cam.project(b), c, w) for a, b, c, w in segs]
    xs = [p.x for a, b, _, _ in proj for p in (a, b)]
    ys = [p.y for a, b, _, _ in proj for p in (a, b)]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    box = [FX0 + 20, FY0 + 96, 620, 690]
    scale = min(box[2] / (maxx - minx), box[3] / (maxy - miny)) * 0.8
    ox = box[0] + (box[2] - (maxx - minx) * scale) / 2
    oy = box[1] + (box[3] - (maxy - miny) * scale) / 2
    for a, b, c, w in proj:
        line(layer, [ox + (a.x - minx) * scale, oy + (a.y - miny) * scale],
             [ox + (b.x - minx) * scale, oy + (b.y - miny) * scale], c, w)
    # item balloons
    for (px, py, n) in [(0.30, 0.18, "1"), (0.52, 0.42, "2"), (0.50, 0.74, "3"),
                        (0.30, 0.66, "4"), (0.72, 0.55, "5"), (0.16, 0.86, "6")]:
        bubble(layer, [box[0] + box[2] * px, box[1] + box[3] * py], n)
    view_label(layer, box[0], FY0 + 70, "EXPLODED ASSEMBLY", "1:30")
    # BOM table on the right
    layer.text([FX0 + 676, FY0 + 76, 400, 14], "BILL OF MATERIALS", style={"class": "noteh"})
    table(layer, [FX0 + 676, FY0 + 96, 624, 0],
          ["NO", "DESCRIPTION", "QTY", "MATERIAL", "MASS"],
          [("1", "A-frame upright assembly", "2", "Oak", "180 kg"),
           ("2", "Main axle + bearings", "1", "Iron/bronze", "62 kg"),
           ("3", "Throwing arm (laminated)", "1", "Ash", "95 kg"),
           ("4", "Counterweight crate", "1", "Oak + lead", "2 000 kg"),
           ("5", "Sling + pouch", "1", "Hemp/leather", "4 kg"),
           ("6", "Ground-sill raft", "1", "Oak", "240 kg"),
           ("7", "Cocking winch", "1", "Iron/oak", "70 kg"),
           ("8", "Trigger sear + lanyard", "1", "Iron", "6 kg"),
           ("9", "Treenails & straps", "lot", "Iron/oak", "30 kg")],
          [40, 256, 56, 150, 82])
    layer.text([FX0 + 676, FY0 + 320, 624, 16],
               "TOTAL (armed) ≈ 2 850 kg     ·     ITEM BALLOONS KEYED TO EXPLODED VIEW",
               style={"class": "small"})
    notes_panel(layer, [FX0 + 676, FY0 + 360, 624, 110], "END OF SET", [
        "Sheets 01–30 complete. Every view, dimension, section and chart on this set "
        "was generated programmatically through the FrameGraph Python SDK and validated "
        "against the authoritative model. — framegraph.sdk",
    ], numbered=False)


# --------------------------------------------------------------------------- #
# Assemble                                                                     #
# --------------------------------------------------------------------------- #

def build_package() -> DocumentBuilder:
    global _sheet
    _sheet = 0
    builder = DocumentBuilder(
        title="Counterweight Trebuchet — Engineering Drawings",
        profile="deck",
        lang="en",
    )
    theme(builder, colors={}, styles=STYLES)

    page_cover(builder)          # 01
    page_index(builder)          # 02
    page_notes(builder)          # 03
    # A — general arrangement
    page_ga_side(builder)        # 04
    page_ga_launch(builder)      # 05
    page_ga_front_plan(builder)  # 06
    page_ga_iso(builder)         # 07
    # B — structure
    page_str_base(builder)       # 08
    page_str_aframe(builder)     # 09
    page_str_crossbeam(builder)  # 10
    page_str_joinery(builder)    # 11
    page_str_loadpath(builder)   # 12
    # C — throwing arm
    page_arm_elev(builder)       # 13
    page_arm_schedule(builder)   # 14
    page_arm_axle(builder)       # 15
    page_cw_box(builder)         # 16
    page_sling(builder)          # 17
    # D — mechanism
    page_winch(builder)          # 18
    page_trigger(builder)        # 19
    page_kinematics(builder)     # 20
    page_release_geom(builder)   # 21
    page_sequence(builder)       # 22
    # E — analysis
    page_fbd(builder)            # 23
    page_energy(builder)         # 24
    page_lever(builder)          # 25
    page_trajectory(builder)     # 26
    page_performance(builder)    # 27
    # F — details
    page_det_axle(builder)       # 28
    page_det_pin(builder)        # 29
    page_bom(builder)            # 30
    return builder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yaml", default=os.path.join(ROOT, "tests", "fixtures",
                                                    "trebuchet-engineering-drawings.fg.yaml"),
                    help="output document path")
    ap.add_argument("--render", action="store_true",
                    help="also rasterise every sheet to SVG under out/trebuchet/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "trebuchet"),
                    help="SVG output directory (with --render)")
    args = ap.parse_args()

    builder = build_package()
    doc = builder.build()
    n_pages = len(doc.pages)
    print(f"Built drawing package: {n_pages} sheets")

    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity == "warning"]
    print(f"Validation: ok={report.ok}  errors={len(errors)}  warnings={len(warns)}")
    for i in errors[:25]:
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
            p = os.path.join(args.out, f"sheet-{idx:02d}.svg")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(svg)
        print(f"Rendered {len(svgs)} SVG sheets to {args.out}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

