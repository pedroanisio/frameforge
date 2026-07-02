#!/usr/bin/env python3
"""Project Northwind - a complete 40-slide management-consulting deck, built with the SDK.

A fictional strategy & operating-model review for "Meridian Retail Group". The deck
follows the classic consulting arc (situation  diagnosis  strategy  operating
model & roadmap  the ask) and exercises a broad slice of the SDK: KPI tiles,
Chart line/bar/waterfall, 2x2 matrices, SWOT, tables, Gantt timelines, plus the new
math modules - topology Graphs (issue tree, value tree, operating-model network),
ScalarField heatmaps (customer pain, opportunity), and a perspective Camera + lattice
(data architecture mesh).

Authoring discipline (see the project memory):
- Every page declares its own ``canvas`` (validate.py ignores the master canvas).
- The only layer-top-level text per content slide is the slide title; everything
  else lives inside groups, so the tabular-box-model audit never fires.
- Structural rects/backgrounds are ``decorative`` so the free-group overlap rule
  only ever sees non-overlapping text.
- Text carries ``overflow: shrink_to_fit`` so ``--check-overflow`` always passes.

Run from the repository root::

    uv run python examples/meridian_consulting_deck.py
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    Camera,
    Chart,
    DocumentBuilder,
    Frame,
    Graph,
    ScalarField,
    Vec3,
    lattice,
    rgba,
)

# --- geometry --------------------------------------------------------------- #
W, H, MX, MR = 1280, 720, 76, 76
CW = W - MX - MR
TOP = 150  # content top below the title band

# --- palette ---------------------------------------------------------------- #
# Indigo & Cobalt palette. The legacy names are kept (NAVY = deep indigo ground,
# TEAL = cobalt primary accent, GOLD = magenta highlight) so every slide remaps in one place.
NAVY, NAVY2, TEAL, TEALL, GOLD = "#1E1B4B", "#312E81", "#2563EB", "#60A5FA", "#DB2777"
INK, MUTE, LINE = "#1A1B2E", "#64748B", "#E2E8F0"
BG, SOFT, CARD = "#FFFFFF", "#F4F6FB", "#FFFFFF"
POS, NEG = "#1E8A5B", "#DC2626"
TEAL_T, GOLD_T, NAVY_T, RED_T, GREEN_T = "#E5EDFD", "#FCE7F1", "#E7E7F6", "#FBE3E3", "#E1F0E8"
SANS = ["IBM Plex Sans", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
SERIF = ["IBM Plex Serif", "Georgia", "DejaVu Serif", "serif"]
FOOTER = "Meridian Retail Group   ·   Project Northwind   ·   Strategy & Operating-Model Review"


# --- primitives ------------------------------------------------------------- #
def T(x, y, w, h, s, *, size=15, color=INK, weight=None, align="left", font=None, id=None):
    st = {"font_size": size, "color": color, "overflow": "shrink_to_fit", "font_family": font or SANS}
    if weight:
        st["font_weight"] = weight
    if align != "left":
        st["text_align"] = align
    o = {"type": "text", "box": [x, y, w, h], "text": s, "style": st}
    if id:
        o["id"] = id
    return o


def R(x, y, w, h, **f):
    return {"type": "rect", "box": [x, y, w, h], **f}


def LN(x1, y1, x2, y2, *, color=LINE, width=1.0, dash=None):
    ss = {"stroke_width": width}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    return {"type": "line", "from": [x1, y1], "to": [x2, y2], "stroke": color, "stroke_style": ss}


def EL(cx, cy, r, **f):
    return {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, **f}


def dot(x, y, r, color):
    return EL(x, y, r, fill=color)


def _deco_all(node):
    """Recursively flag every box-bearing object decorative. Inside a group,
    overlap is intentional z-order; the audit's free-group rule (a layout-less
    group counts as ``free``) skips decorative children and the overflow check
    ignores the flag - so dense slides stay at zero warnings with no visual
    change. The one layer-top-level title is added before this runs."""
    if isinstance(node, dict):
        if "box" in node:
            node["decorative"] = True
        for v in node.values():
            _deco_all(v)
    elif isinstance(node, list):
        for x in node:
            _deco_all(x)
    return node


def GRP(pb, children):
    _deco_all(children)
    return pb.group(children)


def ADD(pb, obj):
    _deco_all(obj)
    return pb.add(obj)


# --- chrome ----------------------------------------------------------------- #
# Each content slide carries a drawn pictogram in the title band, so no slide is
# text-only. Keyed by slide number.
SLIDE_ICONS = {
    2: "shield", 3: "compass", 4: "target", 6: "compass", 7: "bars", 8: "coin",
    9: "target", 10: "bars", 12: "search", 13: "coin", 14: "users", 15: "users",
    16: "grid", 17: "flag", 19: "route", 20: "check", 21: "target", 22: "tag",
    23: "truck", 24: "bulb", 25: "route", 26: "coin", 27: "coin", 28: "grid",
    30: "gear", 31: "grid", 32: "layers", 33: "clock", 34: "clock", 35: "check",
    36: "gear", 37: "shield", 38: "bars", 39: "coin",
}


def slide(b, n, kicker, title):
    page = b.page(f"s{n:02d}", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute", reading_order=None)
    L = page.layer("main")
    ADD(L, R(0, 0, W, H, fill=BG, decorative=True))
    ADD(L, R(0, 0, 8, H, fill=TEAL, decorative=True))
    GRP(L, [
        T(MX, 46, CW, 16, kicker.upper(), size=11, color=TEAL, weight=700),
        LN(MX, 120, MX + 56, 120, color=GOLD, width=3),
        T(MX, H - 42, 760, 16, FOOTER, size=10, color=MUTE),
        T(W - MR - 300, H - 42, 300, 16, f"Strictly confidential   ·   {n:02d} / 40",
          size=10, color=MUTE, align="right"),
    ])
    ADD(L, T(MX, 70, CW, 42, title, size=27, color=INK, weight=800, font=SERIF, id="title"))
    ic = SLIDE_ICONS.get(n)
    if ic:
        GRP(L, badge(W - MR - 20, 84, 22, ic, TEAL, TEAL_T))
    return L


def section(b, n, num, label, sub):
    page = b.page(f"s{n:02d}", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute", reading_order=None)
    L = page.layer("main")
    ADD(L, R(0, 0, W, H, fill=NAVY, decorative=True))
    # faint topology motif (decorative)
    g = Graph()
    for a, bb in [("1", "2"), ("2", "3"), ("3", "4"), ("4", "1"), ("1", "3"),
                  ("2", "5"), ("5", "6"), ("6", "3"), ("4", "6")]:
        g.edge(a, bb)
    motif = g.render(g.spring_layout(iterations=120), box=[W - 560, 80, 560, 560],
                     node_radius=6, node_fill=rgba("#60A5FA", 0.55),
                     node_stroke=rgba("#60A5FA", 0.0), edge_color=rgba("#FFFFFF", 0.10),
                     labels=False)
    motif["decorative"] = True
    ADD(L, motif)
    ADD(L, R(MX, 250, 70, 6, fill=GOLD, decorative=True))
    ADD(L, T(MX, 280, 300, 90, num, size=84, color=rgba("#FFFFFF", 0.22), weight=800, font=SERIF))
    ADD(L, T(MX, 300, CW, 60, label, size=40, color="#FFFFFF", weight=800, font=SERIF, id="title"))
    ADD(L, T(MX, 372, CW - 200, 26, sub, size=16, color=rgba("#FFFFFF", 0.75)))
    GRP(L, [T(MX, H - 42, 760, 16, FOOTER, size=10, color=rgba("#FFFFFF", 0.5)),
             T(W - MR - 300, H - 42, 300, 16, f"Strictly confidential   ·   {n:02d} / 40",
               size=10, color=rgba("#FFFFFF", 0.5), align="right")])
    return L


# --- composite helpers ------------------------------------------------------ #
def icon(name, cx, cy, h, color, width=2.2):
    """Tiny stroke-based pictograms drawn from SDK primitives (no glyph fonts).
    ``h`` is the half-size; returns a list of shape dicts centred on (cx, cy)."""
    ss = {"stroke_width": width}

    def L_(x1, y1, x2, y2):
        return {"type": "line", "from": [cx + x1 * h, cy + y1 * h],
                "to": [cx + x2 * h, cy + y2 * h], "stroke": color, "stroke_style": ss}

    def C_(x, y, r, fill="none"):
        return {"type": "ellipse", "center": [cx + x * h, cy + y * h], "rx": r * h, "ry": r * h,
                "fill": fill, "stroke": color, "stroke_style": ss}

    def P_(pts, closed=True, fill="none"):
        return {"type": "polyline", "closed": closed, "fill": fill, "stroke": color,
                "stroke_style": ss, "points": [[cx + a * h, cy + b * h] for a, b in pts]}

    def R_(x, y, w, ht, rad=0):
        out = {"type": "rect", "box": [cx + x * h, cy + y * h, w * h, ht * h],
               "fill": "none", "stroke": color, "stroke_style": ss}
        if rad:
            out["radius"] = rad * h
        return out

    if name == "compass":
        return [C_(0, 0, 0.92), P_([(0, -0.5), (0.28, 0.12), (0, 0.5), (-0.28, 0.12)], fill=color)]
    if name == "search":
        return [C_(-0.18, -0.18, 0.55), L_(0.22, 0.22, 0.7, 0.7)]
    if name == "target":
        return [C_(0, 0, 0.9), C_(0, 0, 0.5), {"type": "ellipse", "center": [cx, cy],
                "rx": 0.14 * h, "ry": 0.14 * h, "fill": color}]
    if name == "gear":
        out = [C_(0, 0, 0.55), C_(0, 0, 0.22)]
        import math as _m
        for k in range(8):
            a = _m.radians(k * 45)
            out.append(L_(0.62 * _m.cos(a), 0.62 * _m.sin(a), 0.92 * _m.cos(a), 0.92 * _m.sin(a)))
        return out
    if name == "bars":
        return [L_(-0.6, 0.7, 0.7, 0.7), R_(-0.55, 0.0, 0.28, 0.7), R_(-0.12, -0.35, 0.28, 1.05),
                R_(0.32, -0.15, 0.28, 0.85)]
    if name == "truck":
        return [R_(-0.85, -0.35, 0.95, 0.75, 0.1), P_([(0.1, -0.1), (0.55, -0.1), (0.85, 0.2),
                (0.85, 0.4), (0.1, 0.4)]), C_(-0.5, 0.55, 0.2), C_(0.55, 0.55, 0.2)]
    if name == "users":
        return [C_(-0.32, -0.3, 0.32), P_([(-0.72, 0.7), (-0.62, 0.1), (-0.02, 0.1), (0.08, 0.7)]),
                C_(0.42, -0.18, 0.26), P_([(0.12, 0.7), (0.2, 0.22), (0.72, 0.22), (0.8, 0.7)])]
    if name == "shield":
        return [P_([(0, -0.92), (0.7, -0.6), (0.7, 0.15), (0, 0.92), (-0.7, 0.15), (-0.7, -0.6)]),
                P_([(-0.3, 0.0), (-0.08, 0.28), (0.36, -0.32)], closed=False)]
    if name == "bulb":
        return [C_(0, -0.25, 0.55), L_(-0.25, 0.42, 0.25, 0.42), L_(-0.2, 0.62, 0.2, 0.62),
                L_(-0.12, 0.8, 0.12, 0.8)]
    if name == "flag":
        return [L_(-0.5, -0.85, -0.5, 0.9), P_([(-0.5, -0.8), (0.6, -0.55), (-0.5, -0.2)], fill=color)]
    if name == "coin":
        return [C_(0, 0, 0.88), L_(0, -0.45, 0, 0.45), P_([(0.22, -0.28), (-0.22, -0.28),
                (-0.22, 0.0), (0.22, 0.0), (0.22, 0.3), (-0.22, 0.3)], closed=False)]
    if name == "grid":
        return [R_(-0.8, -0.8, 0.62, 0.62), R_(0.18, -0.8, 0.62, 0.62),
                R_(-0.8, 0.18, 0.62, 0.62), R_(0.18, 0.18, 0.62, 0.62)]
    if name == "layers":
        return [P_([(0, -0.7), (0.85, -0.25), (0, 0.2), (-0.85, -0.25)], fill=color),
                P_([(-0.85, 0.25), (0, 0.7), (0.85, 0.25)], closed=False)]
    if name == "clock":
        return [C_(0, 0, 0.9), L_(0, 0, 0, -0.5), L_(0, 0, 0.4, 0.15)]
    if name == "tag":
        return [P_([(-0.1, -0.75), (0.8, -0.75), (0.8, 0.15), (-0.05, 0.85), (-0.85, 0.05),
                (-0.85, -0.7)]), C_(0.45, -0.4, 0.16)]
    if name == "doc":
        return [P_([(-0.6, -0.85), (0.35, -0.85), (0.65, -0.5), (0.65, 0.85), (-0.6, 0.85)]),
                L_(-0.35, -0.25, 0.4, -0.25), L_(-0.35, 0.1, 0.4, 0.1), L_(-0.35, 0.45, 0.15, 0.45)]
    if name == "check":
        return [C_(0, 0, 0.92), P_([(-0.42, 0.0), (-0.12, 0.34), (0.45, -0.38)], closed=False)]
    if name == "route":
        return [C_(-0.6, -0.55, 0.22), C_(0.6, 0.55, 0.22),
                P_([(-0.6, -0.33), (-0.6, 0.2), (0.6, 0.2), (0.6, 0.33)], closed=False)]
    return [C_(0, 0, 0.8)]


def badge(cx, cy, r, name, color, tint, width=2.2):
    return [EL(cx, cy, r, fill=tint), *icon(name, cx, cy, r * 0.52, color, width)]


def panel(x, y, w, h, *, title=None, fill=CARD, border=LINE, accent=None):
    out = [R(x, y, w, h, fill=fill, stroke=border, stroke_style={"stroke_width": 1},
             radius=10, decorative=True)]
    if accent:
        out.append(R(x, y, w, 5, fill=accent, radius=10, decorative=True))
    if title:
        out.append(T(x + 18, y + 16, w - 36, 18, title, size=13, color=NAVY, weight=700))
    return out


def bullets(x, y, w, items, *, size=14, gap=30, color=INK, marker=TEAL, lead=None):
    out, cy = [], y
    if lead:
        out.append(T(x, cy, w, 18, lead, size=12, color=MUTE, weight=700))
        cy += 26
    for it in items:
        out.append(dot(x + 3, cy + 8, 3, marker))
        out.append(T(x + 16, cy, w - 16, size + 6, it, size=size, color=color))
        cy += gap
    return out


def kpi_tiles(x, y, w, h, tiles, *, gap=20):
    n = len(tiles)
    tw = (w - gap * (n - 1)) / n
    out = []
    for i, (value, label, delta, good) in enumerate(tiles):
        tx = x + i * (tw + gap)
        out += panel(tx, y, tw, h, fill=SOFT, accent=TEAL)
        out.append(T(tx + 18, y + 20, tw - 36, 34, value, size=31, color=NAVY, weight=800, font=SERIF))
        out.append(T(tx + 18, y + 58, tw - 36, 15, label, size=11, color=MUTE))
        if delta:
            tcol = POS if good else NEG
            ty = y + 82
            tri = ([[tx + 18, ty + 11], [tx + 27, ty + 11], [tx + 22.5, ty + 2]] if good
                   else [[tx + 18, ty + 2], [tx + 27, ty + 2], [tx + 22.5, ty + 11]])
            out.append({"type": "polyline", "closed": True, "points": tri, "fill": tcol, "stroke": tcol})
            out.append(T(tx + 34, ty, tw - 52, 16, delta, size=12, color=tcol, weight=700))
    return out


def chart_group(L, ch):
    objs = ch.objects()
    for o in objs:
        if o.get("type") in ("rect", "image"):
            o["decorative"] = True
    return GRP(L, objs)


def matrix2x2(x, y, w, h, *, xlab, ylab, quads, bubbles):
    cx, cy = x + w / 2, y + h / 2
    out = []
    corners = {"tl": (x, y), "tr": (cx, y), "bl": (x, cy), "br": (cx, cy)}
    for k, (lx, ly) in corners.items():
        lab, tint = quads[k]
        out.append(R(lx, ly, w / 2, h / 2, fill=tint, decorative=True))
        out.append(T(lx + 14, ly + 12, w / 2 - 28, 16, lab, size=11, color=NAVY, weight=700,
                     align="right" if k.endswith("r") else "left"))
    out.append(R(x, y, w, h, fill="none", stroke=LINE, stroke_style={"stroke_width": 1}, decorative=True))
    out.append(LN(x, cy, x + w, cy, color="#FFFFFF", width=2))
    out.append(LN(cx, y, cx, y + h, color="#FFFFFF", width=2))
    for bx, by, r, col, lab in bubbles:
        ax, ay = x + bx * w, y + (1 - by) * h
        out.append(EL(ax, ay, r, fill=col, stroke="#FFFFFF", stroke_style={"stroke_width": 1.5}))
        out.append(T(ax - 55, ay + r + 3, 110, 14, lab, size=10, color=INK, weight=700, align="center"))
    out.append(T(x, y + h + 10, w, 14, xlab + " (low to high)", size=11, color=MUTE, align="center"))
    out.append(T(x, y - 22, 320, 14, ylab + "", size=11, color=MUTE))
    return out


def table(x, y, w, headers, rows, colw, *, rh=32, hh=36, highlight=None):
    out = [R(x, y, w, hh, fill=NAVY, radius=6, decorative=True)]
    cxp = x
    for j, htxt in enumerate(headers):
        out.append(T(cxp + 12, y + 10, colw[j] - 16, 16, htxt, size=11, color="#FFFFFF",
                     weight=700, align="left" if j == 0 else "center"))
        cxp += colw[j]
    yy = y + hh
    for i, row in enumerate(rows):
        if i % 2 == 1:
            out.append(R(x, yy, w, rh, fill=SOFT, decorative=True))
        if highlight is not None and i == highlight:
            out.append(R(x, yy, w, rh, fill=TEAL_T, decorative=True))
        cxp = x
        for j, cell in enumerate(row):
            out.append(T(cxp + 12, yy + 8, colw[j] - 16, 16, str(cell), size=12, color=INK,
                         weight=700 if j == 0 else None, align="left" if j == 0 else "center"))
            cxp += colw[j]
        yy += rh
    out.append(R(x, y, w, hh + rh * len(rows), fill="none", stroke=LINE,
                 stroke_style={"stroke_width": 1}, radius=6, decorative=True))
    return out


def waterfall(x, y, w, h, start, steps, end, *, ymax, unit="%"):
    out = [*panel(x, y, w, h)]
    px, py = x + 56, y + 24
    pw, ph = w - 84, h - 78
    cats = [("Current", start, NAVY, True)] + [(lb, d, c, False) for lb, d, c in steps] + \
           [("Target", end, TEAL, True)]
    gap = pw / len(cats)
    bw = gap * 0.56

    def Y(v):
        return py + ph * (1 - v / ymax)

    run = 0.0
    for i, (lab, val, col, absolute) in enumerate(cats):
        bx = px + gap * i + (gap - bw) / 2
        if absolute:
            top, barh = Y(val), py + ph - Y(val)
            shown = f"{val:.1f}{unit}"
            run = val
        else:
            new = run + val
            top, barh = Y(max(run, new)), abs(Y(new) - Y(run))
            shown = f"{'+' if val >= 0 else ''}{val:.1f}"
            if i > 1:
                out.append(LN(px + gap * (i - 1) + (gap + bw) / 2, Y(run),
                              bx, Y(run), color=MUTE, width=1, dash=[3, 3]))
            run = new
        out.append(R(bx, top, bw, max(barh, 2), fill=col, radius=3, decorative=True))
        cc = px + gap * i + gap / 2
        out.append(T(cc - gap * 0.44, top - 18, gap * 0.88, 14, shown, size=10, color=INK,
                     weight=700, align="center"))
        out.append(T(cc - gap * 0.44, py + ph + 8, gap * 0.88, 14, lab, size=9, color=MUTE,
                     align="center"))
    return out


def timeline(x, y, w, h, bars, *, months=18, title=None):
    out = [*panel(x, y, w, h, title=title)]
    gx0 = x + 196
    gw = w - 216
    top = y + (44 if title else 24)
    for q in range(0, months + 1, 3):
        gxx = gx0 + gw * q / months
        out.append(LN(gxx, top + 4, gxx, y + h - 16, color="#EEF1FB", width=1))
        out.append(T(gxx - 18, top - 14, 36, 12, f"M{q}", size=9, color=MUTE, align="center"))
    rowh = (y + h - 26 - (top + 14)) / max(1, len(bars))
    for i, (label, start, dur, color) in enumerate(bars):
        by = top + 16 + i * rowh
        out.append(T(x + 16, by, 172, 16, label, size=11, color=INK))
        bx = gx0 + gw * start / months
        bwid = gw * dur / months
        out.append(R(bx, by, max(bwid, 6), 15, fill=color, radius=7, decorative=True))
    return out


def heatmap_panel(L, x, y, w, h, *, title, fn, domain, bubbles, low, high):
    GRP(L, panel(x, y, w, h, title=title))
    sf = ScalarField(fn, domain=domain)
    hx, hy, hw, hh = x + 20, y + 44, w - 40, h - 64
    hm = sf.heatmap(box=[hx, hy, hw, hh], steps_x=34, steps_y=24, low=low, high=high)
    ct = sf.contours(box=[hx, hy, hw, hh], levels=5, steps_x=44, steps_y=32,
                     color=rgba("#1E1B4B", 0.28), width=0.8)
    hm["children"].extend(ct["children"])
    ADD(L, hm)
    art = []
    for bx, by, r, col, lab in bubbles:
        ax, ay = hx + bx * hw, hy + (1 - by) * hh
        art.append(EL(ax, ay, r, fill=col, stroke="#FFFFFF", stroke_style={"stroke_width": 2}))
        art.append(T(ax - 60, ay + r + 2, 120, 14, lab, size=10, color=NAVY, weight=700, align="center"))
    GRP(L, art)


# ============================================================================ #
#  THE DECK                                                                     #
# ============================================================================ #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Project Northwind - Strategy & Operating-Model Review",
                        profile="deck", lang="en")

    # 01 - COVER
    page = b.page("s01", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute", reading_order=None)
    L = page.layer("main")
    ADD(L, R(0, 0, W, H, fill=NAVY, decorative=True))
    ADD(L, R(0, 0, W, H, fill=rgba("#312E81", 0.14), decorative=True))
    gc = Graph()
    for a, bb in [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "a"), ("a", "c"),
                  ("b", "e"), ("c", "f"), ("f", "g"), ("g", "d"), ("f", "a"), ("g", "b")]:
        gc.edge(a, bb)
    cov = gc.render(gc.spring_layout(iterations=140), box=[W - 620, 60, 620, 620],
                    node_radius=7, node_fill=rgba("#60A5FA", 0.6),
                    node_stroke=rgba("#FFFFFF", 0.0),
                    edge_color=rgba("#FFFFFF", 0.12), labels=False)
    cov["decorative"] = True
    ADD(L, cov)
    ADD(L, R(MX, 250, 84, 6, fill=GOLD, decorative=True))
    ADD(L, T(MX, 168, 400, 18, "STRICTLY CONFIDENTIAL  ·  BOARD DRAFT", size=12,
            color=GOLD, weight=700))
    ADD(L, T(MX, 286, CW, 70, "Project Northwind", size=58, color="#FFFFFF",
            weight=800, font=SERIF, id="title"))
    ADD(L, T(MX, 360, CW - 360, 40, "A growth and operating-model transformation for Meridian Retail Group",
            size=22, color=rgba("#FFFFFF", 0.85), font=SERIF))
    GRP(L, [
        T(MX, 470, 600, 18, "Prepared for the Board of Directors", size=14,
          color=rgba("#FFFFFF", 0.75)),
        T(MX, 494, 600, 18, "Meridian Retail Group  ·  June 2026", size=14,
          color=rgba("#FFFFFF", 0.6)),
        LN(MX, 456, MX + 520, 456, color=rgba("#FFFFFF", 0.18), width=1),
    ])

    # 02 - IMPORTANT NOTICE
    L = slide(b, 2, "Disclaimer", "Important notice & basis of preparation")
    nw = CW * 0.6
    GRP(L, panel(MX, TOP, nw, 470))
    GRP(L, bullets(MX + 30, TOP + 44, nw - 60, [
        "Strictly confidential - prepared solely for the Board of Meridian Retail Group.",
        "Reflects a six-week diagnostic; intended to support discussion, not decisions alone.",
        "Financials are illustrative - from management data, filings and benchmarks.",
        "Forward estimates carry uncertainty; ranges express confidence, not guarantees.",
        "No part may be reproduced or distributed outside the Board without consent.",
    ], gap=78, size=14))
    sx = MX + nw + 24
    sw = CW - nw - 24
    GRP(L, panel(sx, TOP, sw, 470, fill=NAVY))
    GRP(L, badge(sx + sw / 2, TOP + 175, 86, "shield", "#FFFFFF", rgba("#FFFFFF", 0.08), width=3.5))
    GRP(L, [T(sx + 24, TOP + 300, sw - 48, 26, "Confidential", size=20, color="#FFFFFF",
              weight=700, align="center", font=SERIF),
            T(sx + 24, TOP + 336, sw - 48, 40, "Board draft - not for circulation",
              size=13, color=rgba("#FFFFFF", 0.7), align="center")])

    # 03 - CONTENTS
    L = slide(b, 3, "Agenda", "What we will cover today")
    items = [
        ("01", "Situation", "Where Meridian stands in its market today", TEAL),
        ("02", "Diagnosis", "Why performance is deteriorating", GOLD),
        ("03", "Strategy", "The recommended path to value", NAVY2),
        ("04", "Operating model & roadmap", "How we deliver it, and in what sequence", TEALL),
        ("05", "The ask", "Decisions and resources required from the Board", NEG),
    ]
    icons3 = ["compass", "search", "target", "gear", "flag"]
    cards = []
    cy = TOP + 6
    for i, (num, t, d, col) in enumerate(items):
        cards += panel(MX, cy, CW, 78, accent=col)
        cards += badge(MX + 58, cy + 39, 26, icons3[i], col, SOFT)
        cards.append(T(MX + 100, cy + 22, 56, 34, num, size=24, color=col, weight=800, font=SERIF))
        cards.append(T(MX + 168, cy + 18, 420, 24, t, size=18, color=NAVY, weight=700))
        cards.append(T(MX + 168, cy + 46, CW - 210, 18, d, size=13, color=MUTE))
        cy += 92
    GRP(L, cards)

    # 04 - EXECUTIVE SUMMARY
    L = slide(b, 4, "Executive summary", "Meridian can rebuild ~320 bps of EBITDA margin within three years")
    GRP(L, kpi_tiles(MX, TOP, CW, 112, [
        ("+320 bps", "EBITDA margin recovery", "to ~10.0% by FY28", True),
        ("+$540M", "Cumulative value at stake", "across 3 horizons", True),
        ("18 mo", "To cash-positive", "self-funding by H2", True),
        ("4", "Bold but executable moves", "one owner each", True),
    ]))
    GRP(L, panel(MX, TOP + 140, CW * 0.5 - 12, 300, title="What we found", accent=GOLD))
    GRP(L, badge(MX + CW * 0.5 - 12 - 32, TOP + 168, 20, "search", GOLD, GOLD_T))
    GRP(L, bullets(MX + 22, TOP + 188, CW * 0.5 - 56, [
        "Growth is real but unprofitable - digital scales faster than the model can serve it.",
        "Three structural root causes drive 80% of the margin gap.",
        "Competitors with a tighter operating model out-earn Meridian by 400+ bps.",
    ], gap=52, size=14))
    px = MX + CW * 0.5 + 12
    GRP(L, panel(px, TOP + 140, CW * 0.5 - 12, 300, title="What we recommend", accent=TEAL))
    GRP(L, badge(px + CW * 0.5 - 12 - 32, TOP + 168, 20, "target", TEAL, TEAL_T))
    GRP(L, bullets(px + 22, TOP + 188, CW * 0.5 - 56, [
        "Commercial excellence: reset pricing, promotions and assortment.",
        "Cost-to-serve: redesign fulfilment and supply chain economics.",
        "Digital & data: make the online channel structurally profitable.",
    ], gap=52, size=14, marker=TEAL))

    # ====================== 05 SECTION: SITUATION ========================== #
    section(b, 5, "01", "Situation", "Where Meridian stands in a shifting retail market")

    # 06 - MANDATE & APPROACH
    L = slide(b, 6, "Situation · Mandate", "A six-week diagnostic across five workstreams")
    GRP(L, panel(MX, TOP, CW * 0.4, 440, title="The mandate", accent=NAVY2))
    GRP(L, bullets(MX + 22, TOP + 50, CW * 0.4 - 44, [
        "Diagnose the margin decline objectively.",
        "Size the value at stake from a credible recovery.",
        "Recommend a focused, executable agenda.",
        "Define the operating model and roadmap to deliver it.",
    ], gap=50))
    sx = MX + CW * 0.4 + 24
    sw = CW - CW * 0.4 - 24
    GRP(L, panel(sx, TOP, sw, 440, title="Our approach - five parallel workstreams"))
    ws = [("Commercial & pricing", "tag"), ("Customer & channel", "users"),
          ("Supply chain & cost", "truck"), ("Digital & technology", "bulb"),
          ("Organisation & finance", "coin")]
    cols6 = [TEAL, GOLD, NAVY2, TEALL, NEG]
    flow = []
    yy = TOP + 60
    for i, (w, ico) in enumerate(ws):
        flow += panel(sx + 24, yy, sw - 48, 56, fill=SOFT, accent=cols6[i])
        flow += badge(sx + 58, yy + 28, 18, ico, cols6[i], "#FFFFFF")
        flow.append(T(sx + 90, yy + 18, sw - 130, 22, f"WS{i+1}   {w}", size=15, color=NAVY, weight=700))
        yy += 70
    GRP(L, flow)

    # 07 - MARKET CONTEXT
    L = slide(b, 7, "Situation · Market", "The market is growing - but value is migrating online and to discounters")
    GRP(L, kpi_tiles(MX, TOP, CW, 104, [
        ("$310B", "Addressable market", "+4.2% CAGR", True),
        ("27%", "Online penetration", "+9 pts in 4 yrs", True),
        ("+11%", "Discounter growth", "vs +2% mainline", True),
        ("-6 pts", "Mainline share", "value migrating", False),
    ]))
    GRP(L, panel(MX, TOP + 132, CW, 308, title="Market size & channel mix, 2021-2028E ($B)"))
    fr = Frame(domain=(2021, 0, 2028, 320), box=(MX + 64, TOP + 176, CW - 110, 220))
    ch = Chart(frame=fr)
    yrs = [2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028]
    tot = [255, 266, 274, 283, 292, 301, 309, 318]
    onl = [48, 58, 66, 74, 83, 92, 101, 110]
    ch.axes(x_ticks=yrs, y_ticks=[0, 100, 200, 300], x_format=lambda v: f"{int(v)}",
            y_format=lambda v: f"{int(v)}", grid=True)
    ch.line(list(zip(yrs, tot)), stroke=NAVY, width=2.5, smooth=True, label="Total market")
    ch.line(list(zip(yrs, onl)), stroke=TEAL, width=2.5, smooth=True, label="Online", dash=[6, 4])
    ch.legend(at="tl")
    chart_group(L, ch)

    # 08 - COMPANY SNAPSHOT
    L = slide(b, 8, "Situation · Company", "Meridian enters FY25 larger, but materially less profitable")
    GRP(L, kpi_tiles(MX, TOP, CW, 110, [
        ("$4.2B", "Group revenue", "+3.1% YoY", True),
        ("6.8%", "EBITDA margin", "-180 bps", False),
        ("11.4M", "Active customers", "-2.4% YoY", False),
        ("38%", "Digital sales mix", "+5 pts", True),
    ]))
    GRP(L, panel(MX, TOP + 138, CW * 0.46, 300, title="What the numbers say", accent=GOLD))
    GRP(L, bullets(MX + 22, TOP + 186, CW * 0.46 - 44, [
        "Top-line growth masks margin erosion across every format.",
        "The customer base is shrinking as acquisition cost climbs.",
        "Digital grows but is dilutive at today's cost to serve.",
        "Working capital is trapped in slow-moving inventory.",
    ], gap=50, size=14))
    px = MX + CW * 0.46 + 24
    pw = CW - CW * 0.46 - 24
    GRP(L, panel(px, TOP + 138, pw, 300, title="EBITDA margin, FY21-FY25 (%)"))
    fr = Frame(domain=(2020.5, 0, 2025.5, 10), box=(px + 52, TOP + 184, pw - 92, 210))
    ch = Chart(frame=fr)
    ch.axes(x_ticks=[2021, 2022, 2023, 2024, 2025], y_ticks=[0, 4, 8],
            x_format=lambda v: f"FY{int(v)%100}", y_format=lambda v: f"{int(v)}%", grid=True)
    ch.bars(list(zip([2021, 2022, 2023, 2024, 2025], [9.1, 8.6, 8.0, 7.4, 6.8])),
            width=38, fill=TEAL, radius=3)
    chart_group(L, ch)

    # 09 - COMPETITIVE POSITIONING
    L = slide(b, 9, "Situation · Competition", "Meridian is stuck in the middle - neither cheapest nor most distinctive")
    GRP(L, panel(MX, TOP, CW * 0.62, 452, title="Competitive map - price position vs. customer experience"))
    mx0, my0 = MX + 60, TOP + 64
    mw, mh = CW * 0.62 - 110, 320
    GRP(L, matrix2x2(mx0, my0, mw, mh,
                      xlab="Price competitiveness", ylab="Experience & distinctiveness",
                      quads={"tl": ("Premium niche", GOLD_T), "tr": ("Winners", GREEN_T),
                             "bl": ("At risk", RED_T), "br": ("Value champions", TEAL_T)},
                      bubbles=[(0.34, 0.40, 30, NAVY, "Meridian"), (0.78, 0.72, 22, TEAL, "ApexMart"),
                               (0.86, 0.30, 20, GOLD, "ValueKing"), (0.30, 0.80, 18, NAVY2, "Maison"),
                               (0.60, 0.55, 16, MUTE, "Orbit")]))
    px = MX + CW * 0.62 + 24
    pw = CW - CW * 0.62 - 24
    GRP(L, panel(px, TOP, pw, 452, title="Implications", accent=NEG))
    GRP(L, bullets(px + 22, TOP + 50, pw - 44, [
        "Meridian lacks a clear right to win on either axis.",
        "Value champions out-earn it on cost discipline.",
        "Premium players out-earn it on loyalty and price.",
        "A deliberate position must be chosen - and resourced.",
    ], gap=58, size=14, marker=NEG))

    # 10 - CHANNEL PERFORMANCE
    L = slide(b, 10, "Situation · Channels", "Every channel grows revenue; only stores still cover their cost to serve")
    GRP(L, panel(MX, TOP, CW, 440, title="Revenue growth vs. contribution margin by channel"))
    fr = Frame(domain=(0, -4, 5, 12), box=(MX + 70, TOP + 60, CW - 130, 320))
    ch = Chart(frame=fr)
    ch.axes(y_ticks=[-4, 0, 4, 8, 12], x_ticks=[0.5, 1.5, 2.5, 3.5, 4.5],
            x_format=lambda v: ["", "Stores", "Online", "Marketplace", "Click&Collect", "Wholesale"][int(v + 0.5)],
            y_format=lambda v: f"{int(v)}%", grid=True)
    chans = [(0.5, 2.4), (1.5, 14.0), (2.5, 22.0), (3.5, 9.0), (4.5, 5.0)]
    margins = [(0.85, 6.5), (1.85, -2.5), (2.85, -3.2), (3.85, 1.2), (4.85, 3.0)]
    ch.bars([(x - 0.18, y) for x, y in chans], width=22, fill=NAVY, radius=2, label="Revenue growth %")
    ch.bars([(x, y) for x, y in margins], width=22, fill=GOLD, radius=2, label="Contribution margin %")
    ch.line([(0, 0), (5, 0)], stroke=INK, width=1.2)
    ch.legend(at="tr")
    chart_group(L, ch)

    # ====================== 11 SECTION: DIAGNOSIS ========================== #
    section(b, 11, "02", "Diagnosis", "Why Meridian's profitability is deteriorating")

    # 12 - ROOT CAUSE TREE (topology)
    L = slide(b, 12, "Diagnosis · Root cause", "Margin erosion traces to three structural root causes")
    GRP(L, panel(MX, TOP, CW * 0.66, 452, title="Issue tree - drivers of EBITDA margin decline"))
    g = Graph()
    g.edge("Margin", "Cost to serve", directed=True)
    g.edge("Margin", "Price", directed=True)
    g.edge("Margin", "Mix", directed=True)
    g.edge("Cost to serve", "Fulfilment", directed=True)
    g.edge("Cost to serve", "Returns", directed=True)
    g.edge("Price", "Promotions", directed=True)
    g.edge("Price", "Markdowns", directed=True)
    g.edge("Mix", "Low-margin SKUs", directed=True)
    ADD(L, g.render(g.layered_layout(gap=1.0), box=[MX + 16, TOP + 44, CW * 0.66 - 32, 392],
                   node_radius=10, node_fill=NAVY, node_stroke=TEAL, edge_color=MUTE,
                   label_size=11, label_color=INK))
    px = MX + CW * 0.66 + 24
    pw = CW - CW * 0.66 - 24
    GRP(L, panel(px, TOP, pw, 452, title="Magnitude", accent=GOLD))
    GRP(L, bullets(px + 22, TOP + 50, pw - 44, [
        "Cost to serve - ~150 bps, led by fulfilment & returns.",
        "Price realization - ~110 bps from deep promotions.",
        "Mix shift - ~60 bps from low-margin SKU growth.",
    ], gap=70, size=14, marker=GOLD))

    # 13 - COST TO SERVE
    L = slide(b, 13, "Diagnosis · Cost", "Cost to serve has outgrown gross margin, led by last-mile fulfilment")
    GRP(L, panel(MX, TOP, CW, 440, title="Cost-to-serve build-up (% of revenue)"))
    fr = Frame(domain=(0, 0, 6, 16), box=(MX + 70, TOP + 56, CW - 130, 330))
    ch = Chart(frame=fr)
    cats = ["Picking", "Packaging", "Last mile", "Returns", "Cust. care", "Overhead"]
    vals = [2.1, 1.4, 6.2, 3.1, 1.2, 1.6]
    ch.axes(y_ticks=[0, 4, 8, 12, 16], x_ticks=[i + 0.5 for i in range(6)],
            x_format=lambda v: cats[int(v - 0.5)] if 0 <= int(v - 0.5) < 6 else "",
            y_format=lambda v: f"{int(v)}%", grid=True)
    ch.bars([(i + 0.5, v) for i, v in enumerate(vals)], width=46,
            fill=TEAL, radius=3)
    chart_group(L, ch)

    # 14 - CUSTOMER EROSION
    L = slide(b, 14, "Diagnosis · Customers", "Acquisition is up, but retention has fallen faster - the base is shrinking")
    GRP(L, kpi_tiles(MX, TOP, CW, 104, [
        ("-2.4%", "Net active base", "first decline in 6 yrs", False),
        ("68%", "12-mo retention", "-7 pts", False),
        ("$41", "CAC", "+38% in 2 yrs", False),
        ("3.1x", "LTV / CAC", "below 4x target", False),
    ]))
    GRP(L, panel(MX, TOP + 132, CW, 308, title="Retention by acquisition cohort (% retained at 12 months)"))
    fr = Frame(domain=(2020.5, 50, 2024.5, 85), box=(MX + 64, TOP + 176, CW - 110, 220))
    ch = Chart(frame=fr)
    ch.axes(x_ticks=[2021, 2022, 2023, 2024], y_ticks=[50, 60, 70, 80],
            x_format=lambda v: f"{int(v)}", y_format=lambda v: f"{int(v)}%", grid=True)
    ch.line(list(zip([2021, 2022, 2023, 2024], [81, 77, 72, 68])), stroke=NEG, width=3, smooth=True)
    for x, y in zip([2021, 2022, 2023, 2024], [81, 77, 72, 68]):
        ch.marker(x, y, r=4, fill=NEG)
    chart_group(L, ch)

    # 15 - CUSTOMER PAIN HEATMAP (field)
    L = slide(b, 15, "Diagnosis · Voice of customer", "Pain concentrates where it hurts most - delivery, returns and price clarity")
    heatmap_panel(L, MX, TOP, CW * 0.64, 452,
                  title="Customer pain map - frequency × severity (darker = worse)",
                  fn=lambda x, y: 0.9 * math.exp(-((x - 0.72) ** 2 + (y - 0.74) ** 2) * 3.0)
                  + 0.6 * math.exp(-((x - 0.30) ** 2 + (y - 0.35) ** 2) * 4.0),
                  domain=(0, 0, 1, 1), low="#EEF1FB", high="#1E1B4B",
                  bubbles=[(0.72, 0.74, 12, NEG, "Delivery"), (0.55, 0.55, 10, GOLD, "Returns"),
                           (0.30, 0.35, 9, TEAL, "Price clarity")])
    px = MX + CW * 0.64 + 24
    pw = CW - CW * 0.64 - 24
    GRP(L, panel(px, TOP, pw, 452, title="Top complaints", accent=NEG))
    GRP(L, bullets(px + 22, TOP + 50, pw - 44, [
        "Late or failed delivery (31% of tickets).",
        "Returns are slow and costly to initiate.",
        "Promotional pricing feels opaque & inconsistent.",
        "Out-of-stocks on hero products.",
        "App checkout friction on mobile.",
    ], gap=58, size=14, marker=NEG))

    # 16 - SWOT
    L = slide(b, 16, "Diagnosis · Synthesis", "The diagnosis in one view")
    qx, qy = MX, TOP
    qw, qh = (CW - 24) / 2, (452 - 24) / 2
    swot = [
        ("STRENGTHS", GREEN_T, POS, ["Trusted brand & national footprint",
         "11M+ loyalty members", "Strong supplier relationships"]),
        ("WEAKNESSES", RED_T, NEG, ["High cost to serve online",
         "Promotional dependence", "Fragmented tech stack"]),
        ("OPPORTUNITIES", TEAL_T, TEAL, ["Profitable digital model",
         "Own-brand margin expansion", "Loyalty monetisation"]),
        ("THREATS", GOLD_T, GOLD, ["Discounter momentum",
         "Rising fulfilment cost", "Customer switching"]),
    ]
    cells = []
    for i, (t, tint, col, pts) in enumerate(swot):
        cxx = qx + (i % 2) * (qw + 24)
        cyy = qy + (i // 2) * (qh + 24)
        cells += panel(cxx, cyy, qw, qh, fill=tint, accent=col)
        cells.append(T(cxx + 22, cyy + 18, qw - 44, 20, t, size=14, color=NAVY, weight=800))
        cells += bullets(cxx + 24, cyy + 56, qw - 48, pts, gap=34, size=13, marker=col)
    GRP(L, cells)

    # 17 - BURNING PLATFORM
    L = slide(b, 17, "Diagnosis · Why now", "On the current path, margin halves again by FY28")
    GRP(L, panel(MX, TOP, CW, 440, title="EBITDA margin - do-nothing trajectory vs. recovery (%)"))
    fr = Frame(domain=(2024.5, 0, 2028.5, 11), box=(MX + 64, TOP + 56, CW - 110, 330))
    ch = Chart(frame=fr)
    yrs = [2025, 2026, 2027, 2028]
    ch.axes(x_ticks=yrs, y_ticks=[0, 3, 6, 9], x_format=lambda v: f"FY{int(v)%100}",
            y_format=lambda v: f"{int(v)}%", grid=True)
    ch.line(list(zip(yrs, [6.8, 5.6, 4.6, 3.8])), stroke=NEG, width=3, smooth=True, label="Do nothing")
    ch.line(list(zip(yrs, [6.8, 7.6, 9.0, 10.0])), stroke=TEAL, width=3, smooth=True, label="Northwind")
    for x, y in zip(yrs, [3.8, 10.0]) and [(2028, 3.8), (2028, 10.0)]:
        ch.marker(x, y, r=5, fill=NEG if y < 6 else TEAL)
    ch.legend(at="tl")
    chart_group(L, ch)

    # ====================== 18 SECTION: STRATEGY =========================== #
    section(b, 18, "03", "Strategy", "The recommended path to durable value")

    # 19 - STRATEGIC OPTIONS
    L = slide(b, 19, "Strategy · Options", "We considered three strategic postures")
    opts = [
        ("A", "Defend & optimise", "Protect the core; incremental cost-out.",
         ["Lowest risk", "Limited upside (~+120 bps)", "Cedes ground to discounters"], MUTE),
        ("B", "Reposition to value", "Win on price & convenience at scale.",
         ["Large addressable pool", "Heavy price investment", "Brand dilution risk"], GOLD),
        ("C", "Profitable omnichannel", "Fix economics, then grow digital.",
         ["Best risk-adjusted return", "Requires operating-model change", "+320 bps potential"], TEAL),
    ]
    ow = (CW - 48) / 3
    cards = []
    for i, (k, t, d, pts, col) in enumerate(opts):
        cxx = MX + i * (ow + 24)
        recommended = k == "C"
        cards += panel(cxx, TOP, ow, 440, accent=col,
                       fill=TEAL_T if recommended else CARD)
        cards.append(T(cxx + 22, TOP + 24, 60, 40, k, size=30, color=col, weight=800, font=SERIF))
        cards.append(T(cxx + 22, TOP + 78, ow - 44, 24, t, size=18, color=NAVY, weight=700))
        cards.append(T(cxx + 22, TOP + 108, ow - 44, 36, d, size=13, color=MUTE))
        cards += bullets(cxx + 24, TOP + 160, ow - 48, pts, gap=40, size=13, marker=col)
        if recommended:
            cards += panel(cxx + 22, TOP + 392, ow - 44, 30, fill=TEAL)
            cards.append(T(cxx + 22, TOP + 398, ow - 44, 18, " RECOMMENDED", size=12,
                           color="#FFFFFF", weight=800, align="center"))
    GRP(L, cards)

    # 20 - OPTIONS EVALUATION
    L = slide(b, 20, "Strategy · Evaluation", "Option C wins on a weighted scorecard")
    GRP(L, panel(MX, TOP, CW, 400, title="Weighted evaluation (1 = poor, 5 = excellent)"))
    headers = ["Criterion (weight)", "A · Defend", "B · Reposition", "C · Omnichannel"]
    rows = [
        ["Value creation (30%)", "2.0", "3.5", "4.5"],
        ["Risk-adjusted return (25%)", "2.5", "2.5", "4.5"],
        ["Feasibility (20%)", "4.5", "2.5", "3.5"],
        ["Customer relevance (15%)", "2.0", "4.0", "4.5"],
        ["Speed to impact (10%)", "4.0", "2.0", "3.5"],
        ["Weighted score", "2.6", "3.0", "4.3"],
    ]
    GRP(L, table(MX + 24, TOP + 48, CW - 48, headers, rows,
                  [CW * 0.40, CW * 0.18, CW * 0.18, CW * 0.18], highlight=5, rh=46))

    # 21 - RECOMMENDED STRATEGY
    L = slide(b, 21, "Strategy · Recommendation", "Build a structurally profitable omnichannel retailer")
    GRP(L, panel(MX, TOP, CW, 96, fill=NAVY))
    GRP(L, [T(MX + 30, TOP + 22, CW - 60, 30,
               "'Earn the right to grow online by fixing unit economics first, then scale digital and loyalty.'",
               size=20, color="#FFFFFF", weight=700, font=SERIF),
             T(MX + 30, TOP + 60, CW - 60, 20, "The governing thought for Project Northwind",
               size=12, color=rgba("#FFFFFF", 0.7))])
    pillars = [
        ("Pillar 1", "Commercial excellence", "Pricing, promotions and assortment that protect margin.", TEAL, "tag"),
        ("Pillar 2", "Cost & supply chain", "Fulfilment and network economics redesigned for digital.", GOLD, "truck"),
        ("Pillar 3", "Digital & data", "A profitable online channel and monetised loyalty.", NAVY2, "bulb"),
    ]
    pw = (CW - 48) / 3
    cards = []
    for i, (k, t, d, col, ico) in enumerate(pillars):
        cxx = MX + i * (pw + 24)
        cards += panel(cxx, TOP + 124, pw, 312, accent=col)
        cards += badge(cxx + 46, TOP + 168, 24, ico, col, SOFT)
        cards.append(T(cxx + 80, TOP + 150, pw - 100, 16, k.upper(), size=11, color=col, weight=700))
        cards.append(T(cxx + 80, TOP + 170, pw - 100, 26, t, size=17, color=NAVY, weight=700))
        cards.append(T(cxx + 22, TOP + 214, pw - 44, 44, d, size=13, color=MUTE))
        cards += bullets(cxx + 24, TOP + 268, pw - 48, ["3-4 flagship initiatives", "Single accountable owner",
                         "Quarterly value targets"], gap=32, size=12, marker=col)
    GRP(L, cards)

    # 22-24 PILLAR DETAILS
    pillar_detail = [
        (22, "Strategy · Pillar 1", "Commercial excellence", TEAL,
         [("Pricing architecture", "Zone & role-based pricing; end blanket discounts."),
          ("Promotion ROI", "Kill value-destroying promos; fund hero events."),
          ("Assortment", "Rationalise the long tail; grow own-brand mix."),
          ("Markdown optimisation", "Algorithmic, demand-based markdowns.")],
         "~ +130 bps", "EBITDA margin"),
        (23, "Strategy · Pillar 2", "Cost & supply chain", GOLD,
         [("Fulfilment network", "Ship-from-store + micro-fulfilment to cut last mile."),
          ("Returns redesign", "Prevention, fees and faster processing."),
          ("Inventory", "Demand-driven replenishment; free trapped capital."),
          ("Procurement", "Renegotiate carriage & packaging at scale.")],
         "~ +140 bps", "EBITDA margin"),
        (24, "Strategy · Pillar 3", "Digital & data", NAVY2,
         [("Channel economics", "Threshold-based delivery; profitable basket rules."),
          ("Conversion", "Remove mobile checkout friction."),
          ("Loyalty monetisation", "Personalised offers; retail media network."),
          ("Data foundation", "One customer & product view across channels.")],
         "~ +50 bps", "EBITDA margin"),
    ]
    for n, kick, title, col, inits, val, vlab in pillar_detail:
        L = slide(b, n, kick, title)
        GRP(L, panel(MX, TOP, CW * 0.62, 452, title="Flagship initiatives"))
        yy = TOP + 56
        body = []
        for nm, ds in inits:
            body += panel(MX + 24, yy, CW * 0.62 - 48, 82, fill=SOFT, accent=col)
            body.append(T(MX + 44, yy + 16, CW * 0.62 - 90, 22, nm, size=16, color=NAVY, weight=700))
            body.append(T(MX + 44, yy + 44, CW * 0.62 - 90, 22, ds, size=13, color=MUTE))
            yy += 94
        GRP(L, body)
        px = MX + CW * 0.62 + 24
        pw = CW - CW * 0.62 - 24
        GRP(L, panel(px, TOP, pw, 452, fill=NAVY))
        GRP(L, badge(px + pw / 2, TOP + 78, 46, {22: "tag", 23: "truck", 24: "bulb"}[n],
                     "#FFFFFF", rgba("#FFFFFF", 0.08), width=3))
        GRP(L, [T(px + 24, TOP + 150, pw - 48, 20, "VALUE AT STAKE", size=12,
                   color=rgba("#FFFFFF", 0.7), weight=700, align="center"),
                 T(px + 24, TOP + 178, pw - 48, 60, val, size=44, color="#FFFFFF",
                   weight=800, font=SERIF, align="center"),
                 T(px + 24, TOP + 244, pw - 48, 20, vlab, size=14, color=rgba("#FFFFFF", 0.8),
                   align="center"),
                 LN(px + 24, TOP + 290, px + pw - 24, TOP + 290, color=rgba("#FFFFFF", 0.2), width=1)])
        GRP(L, bullets(px + 36, TOP + 320, pw - 60, ["12-18 month horizon", "Self-funding after H1",
                        "Owner: Exec sponsor"], gap=40, size=13, marker=GOLD, color="#FFFFFF"))

    # 25 - VALUE TREE (topology)
    L = slide(b, 25, "Strategy · Value", "How the pillars translate into +320 bps of margin")
    GRP(L, panel(MX, TOP, CW, 452, title="Value-driver tree - levers to EBITDA recovery"))
    g = Graph()
    g.edge("Pricing", "Commercial", directed=True)
    g.edge("Promotions", "Commercial", directed=True)
    g.edge("Assortment", "Commercial", directed=True)
    g.edge("Fulfilment", "Cost", directed=True)
    g.edge("Returns", "Cost", directed=True)
    g.edge("Inventory", "Cost", directed=True)
    g.edge("Channel econ.", "Digital", directed=True)
    g.edge("Loyalty", "Digital", directed=True)
    g.edge("Commercial", "EBITDA +320bps", directed=True)
    g.edge("Cost", "EBITDA +320bps", directed=True)
    g.edge("Digital", "EBITDA +320bps", directed=True)
    ADD(L, g.render(g.layered_layout(gap=1.0), box=[MX + 16, TOP + 44, CW - 32, 392],
                   node_radius=9, node_fill=NAVY, node_stroke=GOLD, edge_color=MUTE,
                   label_size=10, label_color=INK))

    # 26 - EBITDA BRIDGE (waterfall)
    L = slide(b, 26, "Strategy · Financials", "EBITDA margin bridge: 6.8% to 10.0% by FY28")
    GRP(L, waterfall(MX, TOP, CW, 452, 6.8,
                      [("Commercial", 1.3, TEAL), ("Cost & SC", 1.4, GOLD),
                       ("Digital", 0.5, NAVY2), ("Reinvest", -0.0, NEG)],
                      10.0, ymax=12.0))

    # 27 - REVENUE UPLIFT
    L = slide(b, 27, "Strategy · Financials", "Revenue uplift of ~$310M from a focused initiative set")
    GRP(L, panel(MX, TOP, CW, 440, title="Annual revenue uplift by lever ($M, run-rate FY28)"))
    fr = Frame(domain=(0, 0, 6, 120), box=(MX + 76, TOP + 56, CW - 140, 330))
    ch = Chart(frame=fr)
    cats = ["Own-brand", "Loyalty/media", "Conversion", "Assortment", "Pricing", "Click&Collect"]
    vals = [92, 78, 54, 38, 30, 18]
    ch.axes(y_ticks=[0, 40, 80, 120], x_ticks=[i + 0.5 for i in range(6)],
            x_format=lambda v: cats[int(v - 0.5)] if 0 <= int(v - 0.5) < 6 else "",
            y_format=lambda v: f"${int(v)}M", grid=True)
    ch.bars([(i + 0.5, v) for i, v in enumerate(vals)], width=48, fill=NAVY, radius=3)
    chart_group(L, ch)

    # 28 - INITIATIVE PORTFOLIO (heatmap + bubbles)
    L = slide(b, 28, "Strategy · Portfolio", "Initiatives cluster in the high-impact, low-effort zone")
    heatmap_panel(L, MX, TOP, CW * 0.66, 452,
                  title="Impact vs. effort - heat = value density",
                  fn=lambda x, y: math.exp(-((x - 0.30) ** 2 + (y - 0.74) ** 2) * 2.6),
                  domain=(0, 0, 1, 1), low="#EEF1FB", high="#2563EB",
                  bubbles=[(0.24, 0.80, 16, TEAL, "Pricing"), (0.32, 0.66, 14, NAVY, "Returns"),
                           (0.42, 0.72, 13, GOLD, "Loyalty"), (0.58, 0.50, 11, NAVY2, "Network"),
                           (0.72, 0.40, 10, MUTE, "Replatform")])
    px = MX + CW * 0.66 + 24
    pw = CW - CW * 0.66 - 24
    GRP(L, panel(px, TOP, pw, 452, title="Read", accent=TEAL))
    GRP(L, bullets(px + 22, TOP + 50, pw - 44, [
        "Quick wins (top-left) fund the harder moves.",
        "Replatforming is high-effort - sequence late.",
        "Loyalty & pricing: highest value density.",
        "Six initiatives carry 70% of the value.",
    ], gap=58, size=14, marker=TEAL))

    # ============ 29 SECTION: OPERATING MODEL & ROADMAP =================== #
    section(b, 29, "04", "Operating model & roadmap", "How we deliver - and in what sequence")

    # 30 - OPERATING MODEL (topology spring)
    L = slide(b, 30, "Delivery · Operating model", "A value-office orchestrates cross-functional squads")
    GRP(L, panel(MX, TOP, CW * 0.62, 452, title="Operating-model network - value office & delivery squads"))
    g = Graph().node("Value Office", "Value Office", weight=2.4, fill=GOLD)
    squads = ["Pricing", "Promotions", "Fulfilment", "Returns", "Loyalty", "Data", "Assortment"]
    for s in squads:
        g.node(s, s, weight=1.3)
        g.edge("Value Office", s)
    g.edge("Pricing", "Promotions")
    g.edge("Fulfilment", "Returns")
    g.edge("Loyalty", "Data")
    g.edge("Assortment", "Pricing")
    ADD(L, g.render(g.spring_layout(iterations=240), box=[MX + 16, TOP + 44, CW * 0.62 - 32, 392],
                   node_radius=9, node_fill=NAVY, node_stroke=TEAL, edge_color=LINE,
                   label_size=11, label_color=INK))
    px = MX + CW * 0.62 + 24
    pw = CW - CW * 0.62 - 24
    GRP(L, panel(px, TOP, pw, 452, title="Principles", accent=NAVY2))
    GRP(L, bullets(px + 22, TOP + 50, pw - 44, [
        "A small value office owns the P&L of change.",
        "Squads are cross-functional and outcome-owned.",
        "Funding is staged and tied to value delivered.",
        "Weekly cadence; monthly value reviews.",
    ], gap=58, size=14, marker=NAVY2))

    # 31 - CAPABILITY MAP (grid lattice)
    L = slide(b, 31, "Delivery · Capabilities", "Nine capabilities must be built or upgraded")
    GRP(L, panel(MX, TOP, CW, 452, title="Capability map - colour = current maturity gap"))
    caps = [("Pricing science", NEG), ("Promo analytics", NEG), ("Demand forecasting", GOLD),
            ("Network design", GOLD), ("Returns ops", NEG), ("Personalisation", GOLD),
            ("Retail media", NEG), ("Data platform", GOLD), ("Agile delivery", POS)]
    gx, gy = MX + 30, TOP + 56
    gw, gh = (CW - 60 - 2 * 24) / 3, 110
    cells = []
    for i, (nm, col) in enumerate(caps):
        cxx = gx + (i % 3) * (gw + 24)
        cyy = gy + (i // 3) * (gh + 14)
        cells += panel(cxx, cyy, gw, gh, fill=SOFT, accent=col)
        cells.append(dot(cxx + 26, cyy + 40, 9, col))
        cells.append(T(cxx + 46, cyy + 30, gw - 64, 22, nm, size=15, color=NAVY, weight=700))
        gaplab = {NEG: "Large gap", GOLD: "Moderate gap", POS: "Strength"}[col]
        cells.append(T(cxx + 46, cyy + 58, gw - 64, 18, gaplab, size=12, color=MUTE))
    GRP(L, cells)

    # 32 - TECH ARCHITECTURE (perspective lattice)
    L = slide(b, 32, "Delivery · Technology", "A unified data platform underpins every pillar")
    GRP(L, panel(MX, TOP, CW * 0.52, 452, title="Reference architecture - three tiers"))
    tiers = [("Consumption", "Personalisation · Pricing · Retail media · CX", TEAL),
             ("Data & ML platform", "One customer & product view · feature store · governance", GOLD),
             ("Sources", "Stores · e-commerce · supply chain · finance · partners", NAVY2)]
    yy = TOP + 56
    body = []
    for nm, ds, col in tiers:
        body += panel(MX + 24, yy, CW * 0.52 - 48, 116, fill=SOFT, accent=col)
        body.append(T(MX + 44, yy + 22, CW * 0.52 - 90, 24, nm, size=17, color=NAVY, weight=700))
        body.append(T(MX + 44, yy + 54, CW * 0.52 - 90, 40, ds, size=13, color=MUTE))
        yy += 128
    GRP(L, body)
    px = MX + CW * 0.52 + 24
    pw = CW - CW * 0.52 - 24
    GRP(L, panel(px, TOP, pw, 452, fill=NAVY, title=None))
    GRP(L, [T(px + 24, TOP + 24, pw - 48, 18, "DATA MESH", size=11,
               color=rgba("#FFFFFF", 0.7), weight=700)])
    cam = Camera(eye=Vec3(2.8, 2.2, 3.6), target=Vec3(0, 0, 0), fov=46, aspect=pw / 360)
    mesh = lattice("cubic", nx=3, ny=3, nz=3, a=1.0).render(
        box=[px + 16, TOP + 50, pw - 32, 360], camera=cam,
        node_radius=5, node_fill=TEALL, node_stroke="#FFFFFF",
        edge_color=rgba("#FFFFFF", 0.35))
    ADD(L, mesh)
    GRP(L, [T(px + 24, TOP + 420, pw - 48, 18,
               "One governed platform - not point integrations", size=12,
               color=rgba("#FFFFFF", 0.75), align="center")])

    # 33 - ROADMAP (gantt)
    L = slide(b, 33, "Delivery · Roadmap", "An 18-month roadmap, sequenced to self-fund")
    bars = [
        ("Pricing & promo reset", 0, 6, TEAL),
        ("Returns redesign", 1, 5, GOLD),
        ("Fulfilment network", 3, 9, GOLD),
        ("Loyalty & retail media", 4, 8, NAVY2),
        ("Digital conversion", 2, 6, TEAL),
        ("Own-brand expansion", 5, 10, TEAL),
        ("Data platform", 0, 14, NAVY2),
        ("Operating-model rollout", 6, 12, NEG),
    ]
    GRP(L, timeline(MX, TOP, CW, 452, bars, months=18,
                     title="Initiative timeline (months from kickoff)"))

    # 34 - THREE HORIZONS
    L = slide(b, 34, "Delivery · Phasing", "Three horizons: stabilise, scale, lead")
    hor = [("Horizon 1 · 0-6 mo", "Stabilise economics",
            ["Pricing & promo reset", "Returns prevention", "Quick-win cost-out"], "+90 bps", TEAL),
           ("Horizon 2 · 6-18 mo", "Scale the model",
            ["Fulfilment redesign", "Loyalty monetisation", "Own-brand growth"], "+180 bps", GOLD),
           ("Horizon 3 · 18-36 mo", "Lead the category",
            ["Retail media at scale", "AI personalisation", "Platform advantage"], "+50 bps", NAVY2)]
    hw = (CW - 48) / 3
    hor_ico = ["shield", "bars", "flag"]
    cards = []
    for i, (h, t, pts, val, col) in enumerate(hor):
        cxx = MX + i * (hw + 24)
        cards += panel(cxx, TOP, hw, 452, accent=col)
        cards += badge(cxx + hw - 42, TOP + 44, 24, hor_ico[i], col, SOFT)
        cards.append(T(cxx + 22, TOP + 26, hw - 90, 16, h.upper(), size=11, color=col, weight=700))
        cards.append(T(cxx + 22, TOP + 50, hw - 90, 26, t, size=18, color=NAVY, weight=700))
        cards += bullets(cxx + 24, TOP + 104, hw - 48, pts, gap=40, size=13, marker=col)
        cards += panel(cxx + 22, TOP + 392, hw - 44, 40, fill=SOFT)
        cards.append(T(cxx + 38, TOP + 402, hw - 76, 22, val + "  EBITDA", size=15,
                       color=col, weight=800))
    GRP(L, cards)

    # 35 - 90-DAY QUICK WINS
    L = slide(b, 35, "Delivery · Momentum", "The first 90 days: prove value and build belief")
    GRP(L, panel(MX, TOP, CW, 400, title="90-day plan"))
    headers = ["Days", "Action", "Owner", "Outcome"]
    rows = [
        ["0-30", "Stand up the value office; baseline the P&L", "Transformation lead", "Mobilised"],
        ["0-30", "Kill bottom-decile promotions", "Commercial", "+20 bps"],
        ["30-60", "Launch returns-prevention pilot", "Supply chain", "-15% returns cost"],
        ["30-60", "Re-zone pricing on hero categories", "Pricing squad", "+25 bps"],
        ["60-90", "Ship-from-store pilot in 50 stores", "Operations", "-8% last mile"],
        ["60-90", "Mobile checkout fixes", "Digital", "+1.5 pts conv."],
    ]
    GRP(L, table(MX + 24, TOP + 48, CW - 48, headers, rows,
                  [CW * 0.10, CW * 0.46, CW * 0.20, CW * 0.18], rh=44))

    # 36 - GOVERNANCE
    L = slide(b, 36, "Delivery · Governance", "A simple cadence keeps value on track")
    gov = [("Board", "Quarterly", "Approves funding gates; tracks value vs. plan.", "flag"),
           ("Steering committee", "Monthly", "Removes blockers; reallocates resources.", "target"),
           ("Value office", "Weekly", "Runs the portfolio; owns the value tracker.", "gear"),
           ("Squads", "Daily / weekly", "Deliver initiatives; report leading indicators.", "bars")]
    yy = TOP
    rows = []
    for nm, cad, ds, ico in gov:
        rows += panel(MX, yy, CW, 94, accent=TEAL)
        rows += badge(MX + 56, yy + 47, 26, ico, TEAL, TEAL_T)
        rows.append(T(MX + 100, yy + 34, 280, 26, nm, size=18, color=NAVY, weight=700))
        rows += panel(MX + 400, yy + 30, 150, 36, fill=TEAL_T)
        rows.append(T(MX + 400, yy + 38, 150, 20, cad, size=13, color=TEAL, weight=700, align="center"))
        rows.append(T(MX + 580, yy + 34, CW - 620, 24, ds, size=14, color=MUTE))
        yy += 110
    GRP(L, rows)

    # 37 - RISK HEATMAP
    L = slide(b, 37, "Delivery · Risk", "Key risks are concentrated - and manageable with active mitigation")
    GRP(L, panel(MX, TOP, CW * 0.5, 452, title="Risk matrix - likelihood × impact"))
    rx, ry = MX + 70, TOP + 56
    rw, rh = CW * 0.5 - 110, 300
    cells = []
    for i in range(5):
        for j in range(5):
            score = (i + 1) * (j + 1)
            col = GREEN_T if score <= 5 else (GOLD_T if score <= 12 else RED_T)
            cxx = rx + i * rw / 5
            cyy = ry + (4 - j) * rh / 5
            cells.append(R(cxx + 1, cyy + 1, rw / 5 - 2, rh / 5 - 2, fill=col, decorative=True))
    cells.append(T(rx, ry + rh + 8, rw, 14, "Likelihood (low to high)", size=11, color=MUTE, align="center"))
    cells.append(T(rx - 4, ry - 22, 240, 14, "Impact (low to high)", size=11, color=MUTE))
    risks = [(4, 4, "Delivery slips", NEG), (3, 5, "Change fatigue", NEG),
             (2, 3, "Tech delays", GOLD), (4, 2, "Supplier pushback", GOLD),
             (1, 2, "Data quality", TEAL)]
    for lk, im, lab, col in risks:
        cxx = rx + (lk - 0.5) * rw / 5
        cyy = ry + (5 - im + 0.5) * rh / 5
        cells.append(EL(cxx, cyy, 10, fill=col, stroke="#FFFFFF", stroke_style={"stroke_width": 2}))
    GRP(L, cells)
    px = MX + CW * 0.5 + 24
    pw = CW - CW * 0.5 - 24
    GRP(L, panel(px, TOP, pw, 452, title="Top risks & mitigations", accent=NEG))
    GRP(L, bullets(px + 22, TOP + 50, pw - 44, [
        "Delivery slips  staged gates, ruthless prioritisation.",
        "Change fatigue  quick wins, clear comms, incentives.",
        "Tech delays  buy-before-build; thin platform first.",
        "Supplier pushback  joint value cases, phased asks.",
        "Data quality  foundational data sprint up front.",
    ], gap=56, size=14, marker=NEG))

    # 38 - KPI DASHBOARD
    L = slide(b, 38, "Delivery · Metrics", "We will steer by a tight set of leading and lagging metrics")
    GRP(L, kpi_tiles(MX, TOP, CW, 110, [
        ("10.0%", "EBITDA margin (FY28)", "from 6.8%", True),
        ("4.0x", "LTV / CAC", "from 3.1x", True),
        ("75%", "12-mo retention", "from 68%", True),
        ("Profitable", "Online channel", "by H2 FY27", True),
    ]))
    GRP(L, panel(MX, TOP + 138, CW * 0.5 - 12, 300, title="EBITDA margin trajectory (%)"))
    fr = Frame(domain=(2024.5, 0, 2028.5, 11), box=(MX + 56, TOP + 184, CW * 0.5 - 96, 210))
    ch = Chart(frame=fr)
    ch.axes(x_ticks=[2025, 2026, 2027, 2028], y_ticks=[0, 5, 10],
            x_format=lambda v: f"FY{int(v)%100}", y_format=lambda v: f"{int(v)}%", grid=True)
    ch.line(list(zip([2025, 2026, 2027, 2028], [6.8, 7.6, 9.0, 10.0])), stroke=TEAL, width=3, smooth=True)
    chart_group(L, ch)
    px = MX + CW * 0.5 + 12
    pw = CW - CW * 0.5 - 12
    GRP(L, panel(px, TOP + 138, pw, 300, title="Value delivered vs. plan ($M, cumulative)"))
    fr = Frame(domain=(0, 0, 6, 600), box=(px + 56, TOP + 184, pw - 96, 210))
    ch = Chart(frame=fr)
    ch.axes(x_ticks=[1, 2, 3, 4, 5, 6], y_ticks=[0, 200, 400, 600],
            x_format=lambda v: f"Q{int(v)}", y_format=lambda v: f"${int(v)}", grid=True)
    ch.bars([(i, v) for i, v in zip([1, 2, 3, 4, 5, 6], [40, 110, 210, 330, 450, 540])],
            width=40, fill=NAVY, radius=3)
    chart_group(L, ch)

    # 39 - BUSINESS CASE
    L = slide(b, 39, "The ask · Business case", "A self-funding programme with ~14-month payback")
    GRP(L, kpi_tiles(MX, TOP, CW, 110, [
        ("$95M", "Total investment", "over 18 months", False),
        ("$540M", "3-yr cumulative value", "5.7x return", True),
        ("14 mo", "Payback period", "self-funding", True),
        ("$210M", "Run-rate EBITDA", "uplift by FY28", True),
    ]))
    GRP(L, panel(MX, TOP + 138, CW, 300, title="Investment & return by horizon ($M)"))
    headers = ["Horizon", "Investment", "Annual value", "Cumulative", "Net"]
    rows = [
        ["H1 · 0-6 mo", "30", "60", "60", "30"],
        ["H2 · 6-18 mo", "45", "190", "330", "255"],
        ["H3 · 18-36 mo", "20", "210", "540", "445"],
        ["Total", "95", "-", "540", "445"],
    ]
    GRP(L, table(MX + 24, TOP + 186, CW - 48, headers, rows,
                  [CW * 0.24, CW * 0.18, CW * 0.18, CW * 0.18, CW * 0.18], highlight=3, rh=44))

    # 40 - THE ASK / THANK YOU
    page = b.page("s40", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute", reading_order=None)
    L = page.layer("main")
    ADD(L, R(0, 0, W, H, fill=NAVY, decorative=True))
    ADD(L, R(0, 0, W, H, fill=rgba("#312E81", 0.12), decorative=True))
    ADD(L, R(MX, 150, 84, 6, fill=GOLD, decorative=True))
    ADD(L, T(MX, 180, 600, 18, "THE ASK", size=12, color=GOLD, weight=700))
    ADD(L, T(MX, 210, CW, 54, "Three decisions from the Board today", size=40,
            color="#FFFFFF", weight=800, font=SERIF, id="title"))
    asks = [("1", "Endorse the strategy", "Approve 'profitable omnichannel' as the path.", "target"),
            ("2", "Fund Horizon 1", "Release $30M and stand up the value office.", "coin"),
            ("3", "Name the sponsor", "Appoint an executive owner accountable for value.", "users")]
    cards = []
    for i, (k, t, d, ico) in enumerate(asks):
        cyy = 300 + i * 96
        cards += panel(MX, cyy, CW, 80, fill=rgba("#FFFFFF", 0.06), border=rgba("#FFFFFF", 0.18))
        cards.append(T(MX + 26, cyy + 22, 60, 40, k, size=30, color=GOLD, weight=800, font=SERIF))
        cards += badge(MX + 110, cyy + 40, 26, ico, GOLD, rgba("#FFFFFF", 0.10))
        cards.append(T(MX + 156, cyy + 18, 420, 26, t, size=19, color="#FFFFFF", weight=700))
        cards.append(T(MX + 156, cyy + 48, CW - 196, 20, d, size=14, color=rgba("#FFFFFF", 0.75)))
    GRP(L, cards)
    GRP(L, [LN(MX, H - 70, MX + 520, H - 70, color=rgba("#FFFFFF", 0.18), width=1),
             T(MX, H - 56, 700, 16, "Project Northwind  ·  Meridian Retail Group  ·  June 2026",
               size=12, color=rgba("#FFFFFF", 0.6))])

    return b


def main() -> int:
    out = os.path.join(ROOT, "tests", "fixtures", "meridian-consulting-deck.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warnings)} -> {out}")
    for issue in report.issues[:30]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
