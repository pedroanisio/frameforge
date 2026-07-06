#!/usr/bin/env python3
"""High-fidelity vector recreation of the shadcn / v0 "radix-nova" component
gallery screenshot using the FrameGraph SDK.

The page is a dense masonry of finance / music-dashboard cards over a dark
configuration sidebar:

  * top bar      — section links, a search box and Get Code button
  * sidebar      — "Menu" with Style / Base Color / Theme / … control rows and
                   preset buttons
  * column 1     — Contribution History (bar chart), Distribute Track, a QR
                   connect card, Q2 Dividend Income
  * column 2     — Payout Threshold (currency / slider / notes), Claimable
                   Balance, Preferences (toggles)
  * column 3     — Savings Targets, a wide Recent Transactions list, an
                   Overview / Account navigation menu
  * column 4     — Buy Investment, a Payments breadcrumb list
  * column 5     — Account Access, Card Balance / Payment Due, Yearly Activity
                   (bar chart), Transfer Funds
  * column 6     — Payout Preferences, Power Usage (bar chart), Connect Bank,
                   Upcoming Payments (calendar)

Everything lowers to SDK primitives (rect / ellipse / line / polygon / path /
text) with gradients and rounded-rect clip paths. Brand names (Bitwarden,
Spotify, Stripe, …) are plain text; no logos are reproduced.

Run from the repository root::

    uv run python examples/radix_nova_gallery.py
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

from framegraph.sdk import DocumentBuilder, measure_text, rgba  # noqa: E402
from framegraph.sdk.clip import clip_path  # noqa: E402

W, H = 2000, 1032

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
COLORS = {
    "page":     "#FFFFFF",
    "ink":      "#0A0A0A",
    "ink2":     "#171717",
    "sub":      "#737373",
    "mut":      "#9A9A9A",
    "mut2":     "#BDBDBD",
    "border":   "#E6E6E6",
    "border2":  "#EDEDED",
    "fieldbg":  "#FAFAFA",
    "track":    "#E9E9E9",
    "fill":     "#1A1A1A",
    "bar":      "#9C9C9C",
    "bardk":    "#707070",
    "green":    "#16A34A",
    "purple":   "#6D4AFF",
    "blue":     "#3B82F6",
    "red":      "#DC2626",
    "black":    "#0A0A0A",
    "white":    "#FFFFFF",
    "yellow":   "#EAB308",
    "btnlight": "#E4E4E4",
    "sb_bg":    "#171717",
    "sb_row":   "#242424",
    "sb_row2":  "#2C2C2C",
    "sb_sub":   "#8C8C8C",
    "sb_txt":   "#F4F4F4",
    "sb_btn":   "#2A2A2A",
}

SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]

# --------------------------------------------------------------------------- #
# Programmatic text-style registry
# --------------------------------------------------------------------------- #
_STYLES: dict[str, dict] = {}


def S(size, weight=400, color="ink", align="left", ls=0.0, lh=1.3):
    key = ("s%s_%s_%s_%s_%s_%s" % (size, weight, color, align, ls, lh)
           ).replace(".", "p").replace("-", "n").replace("#", "h")
    if key not in _STYLES:
        _STYLES[key] = dict(font_family=SANS, font_size=size, font_weight=weight,
                            color=color, align=align, letter_spacing=ls, line_height=lh)
    return key


def tw(text, size, weight=400):
    return measure_text(text, font_family=SANS, font_size=size, bold=weight >= 600)


def rrect(x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    return (f"M{x + r},{y} H{x + w - r} A{r},{r} 0 0 1 {x + w},{y + r} "
            f"V{y + h - r} A{r},{r} 0 0 1 {x + w - r},{y + h} "
            f"H{x + r} A{r},{r} 0 0 1 {x},{y + h - r} "
            f"V{y + r} A{r},{r} 0 0 1 {x + r},{y} Z")


# --------------------------------------------------------------------------- #
# Generic primitives
# --------------------------------------------------------------------------- #
def card(layer, box, *, radius=12, fill="white", border="border", shadow=True):
    x, y, w, h = box
    if shadow:
        layer.rect([x, y + 2, w, h], fill=rgba("#101828", 0.05), radius=radius,
                   decorative=True)
    f = dict(fill=fill, radius=radius)
    if border:
        f["stroke"] = border
        f["stroke_style"] = {"stroke_width": 1}
    layer.rect(box, **f)


def btn(layer, box, label, *, variant="dark", size=13):
    x, y, w, h = box
    if variant == "dark":
        layer.rect(box, fill="black", radius=8)
        col = "white"
    elif variant == "light":
        layer.rect(box, fill="btnlight", radius=8)
        col = "sub"
    else:  # outline
        layer.rect(box, fill="white", radius=8, stroke="border",
                   stroke_style={"stroke_width": 1})
        col = "ink2"
    lw = tw(label, size, 600)
    layer.text([x + (w - lw) / 2, y + (h - size) / 2 - 1, lw + 6, size + 6], label,
               style=S(size, 600, col, "left"))


def field(layer, box, value, *, placeholder=False, prefix=None, chevron=False, size=13.5):
    x, y, w, h = box
    layer.rect(box, fill="white", radius=8, stroke="border",
               stroke_style={"stroke_width": 1})
    tx = x + 12
    if prefix:
        layer.text([x + 12, y + (h - 14) / 2, 16, 18], prefix, style=S(13, 400, "sub"))
        tx = x + 26
    col = "mut" if placeholder else "ink2"
    reserve = 20 if chevron else 10
    layer.text([tx, y + (h - size) / 2 - 1, w - (tx - x) - reserve, size + 6], value,
               style=S(size, 400, col))
    if chevron:
        chev_down(layer, x + w - 17, y + h / 2, "sub")


def chev_down(layer, cx, cy, color="sub", s=4):
    layer.line([cx - s, cy - s / 2], [cx, cy + s / 2], stroke=color,
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})
    layer.line([cx, cy + s / 2], [cx + s, cy - s / 2], stroke=color,
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})


def chev_right(layer, cx, cy, color="mut", s=4):
    layer.line([cx - s / 2, cy - s], [cx + s / 2, cy], stroke=color,
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})
    layer.line([cx + s / 2, cy], [cx - s / 2, cy + s], stroke=color,
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})


def close_x(layer, cx, cy, color="mut", s=5):
    layer.line([cx - s, cy - s], [cx + s, cy + s], stroke=color,
               stroke_style={"stroke_width": 1.4, "stroke_linecap": "round"})
    layer.line([cx + s, cy - s], [cx - s, cy + s], stroke=color,
               stroke_style={"stroke_width": 1.4, "stroke_linecap": "round"})


def badge(layer, x, y, label, *, bg="white", fg="ink2", border="border", size=11.5):
    bw = tw(label, size, 500) + 20
    layer.rect([x, y, bw, 22], fill=bg, radius=7, stroke=border,
               stroke_style={"stroke_width": 1})
    layer.text([x + 10, y + (22 - size) / 2 - 1, bw, size + 4], label, style=S(size, 500, fg))
    return bw


def toggle(layer, x, y, on=True):
    w, h = 36, 20
    layer.rect([x, y, w, h], fill="black" if on else "track", radius=10)
    kx = x + w - 11 if on else x + 11
    layer.ellipse([kx, y + h / 2], 8, 8, fill="white")


def progress(layer, x, y, w, pct, *, h=7, track="track", fill="fill"):
    layer.rect([x, y, w, h], fill=track, radius=h / 2)
    layer.rect([x, y, max(h, w * pct), h], fill=fill, radius=h / 2)


def bars(layer, box, values, labels, *, color="bar", label_style=None, gap_ratio=0.42,
         radius=3):
    x, y, w, h = box
    n = len(values)
    slot = w / n
    bw = slot * (1 - gap_ratio)
    off = (slot - bw) / 2
    mx = max(values) or 1
    for i, v in enumerate(values):
        bh = max(3, (v / mx) * h)
        bx = x + i * slot + off
        layer.rect([bx, y + h - bh, bw, bh], fill=color, radius=radius)
    if labels and label_style:
        for i, lab in enumerate(labels):
            layer.text([x + i * slot, y + h + 7, slot, 14], lab,
                       style=label_style)


def small_icon(layer, x, y, s=26, *, bg="fieldbg", glyph="dot"):
    layer.rect([x, y, s, s], fill=bg, radius=7, stroke="border",
               stroke_style={"stroke_width": 1})
    cx, cy = x + s / 2, y + s / 2
    if glyph == "dot":
        layer.ellipse([cx, cy], 4, 4, fill="sub")
    elif glyph == "ring":
        layer.ellipse([cx, cy], 5, 5, fill="none", stroke="sub",
                      stroke_style={"stroke_width": 1.6})
    elif glyph == "bag":
        layer.path(f"M{cx-5},{cy-2} h10 v7 a1,1 0 0 1 -1,1 h-8 a1,1 0 0 1 -1,-1 Z",
                   fill="none", stroke="sub", stroke_style={"stroke_width": 1.4})
        layer.path(f"M{cx-3},{cy-2} a3,3 0 0 1 6,0", fill="none", stroke="sub",
                   stroke_style={"stroke_width": 1.4})
    elif glyph == "card":
        layer.rect([cx - 6, cy - 4, 12, 8], fill="none", stroke="sub",
                   stroke_style={"stroke_width": 1.4}, radius=2)
        layer.line([cx - 6, cy - 1], [cx + 6, cy - 1], stroke="sub",
                   stroke_style={"stroke_width": 1.4})


# --------------------------------------------------------------------------- #
# Top bar + sidebar
# --------------------------------------------------------------------------- #
def menu_icon(layer, x, y, kind, color="sub"):
    """Minimal 14×14 Lucide-style line glyphs for the navigation menu."""
    s = {"stroke_width": 1.25, "stroke_linecap": "round", "stroke_linejoin": "round"}
    o = {"fill": "none", "stroke": color, "stroke_style": s}
    cx, cy = x + 7, y + 7

    def L(a, b, c, d):
        layer.line([a, b], [c, d], stroke=color, stroke_style=s)

    if kind == "grid":
        for dx in (0, 8):
            for dy in (0, 8):
                layer.rect([x + dx, y + dy, 6, 6], radius=1.5, **o)
    elif kind == "list":
        for dy in (1, 6, 11):
            L(x + 2, y + dy, x + 13, y + dy)
    elif kind == "chart":
        for i, bh in enumerate((5, 9, 7)):
            L(x + 2 + i * 5, y + 13, x + 2 + i * 5, y + 13 - bh)
    elif kind == "wallet":
        layer.rect([x, y + 2, 14, 10], radius=2, **o)
        layer.ellipse([x + 10, cy + 1.5], 1.3, 1.3, fill=color)
    elif kind == "coin":
        layer.ellipse([cx, cy], 6, 6, **o)
        L(cx - 2.5, cy, cx + 2.5, cy)
    elif kind == "flag":
        L(x + 3, y + 1, x + 3, y + 13)
        layer.path(f"M{x+3},{y+2} h8 l-2,3 l2,3 h-8 Z", **o)
    elif kind == "pie":
        layer.ellipse([cx, cy], 6, 6, **o)
        L(cx, cy, cx, cy - 6)
        L(cx, cy, cx + 6, cy)
    elif kind == "doc":
        layer.rect([x + 2, y, 10, 14], radius=1.5, **o)
        L(x + 4, y + 5, x + 10, y + 5)
        L(x + 4, y + 8, x + 10, y + 8)
        L(x + 4, y + 11, x + 8, y + 11)
    elif kind == "user":
        layer.ellipse([cx, y + 4], 2.6, 2.6, **o)
        layer.path(f"M{x+2},{y+13} a5,5 0 0 1 10,0", **o)
    elif kind == "card":
        layer.rect([x, y + 2, 14, 10], radius=2, **o)
        L(x, y + 5.5, x + 14, y + 5.5)
    elif kind == "bell":
        layer.path(f"M{cx},{y+1} a4,4 0 0 1 4,4 v3 l1,2 h-10 l1,-2 v-3 a4,4 0 0 1 4,-4 Z", **o)
        layer.ellipse([cx, y + 13], 1.3, 1.3, fill=color)
    elif kind == "lock":
        layer.rect([x + 2, y + 6, 10, 7], radius=1.5, **o)
        layer.path(f"M{x+4},{y+6} v-2 a3,3 0 0 1 6,0 v2", **o)
    elif kind == "eye":
        layer.path(f"M{x+1},{cy} q6,-6 12,0 q-6,6 -12,0 Z", **o)
        layer.ellipse([cx, cy], 1.7, 1.7, fill=color)
    elif kind == "help":
        layer.ellipse([cx, cy], 6, 6, **o)
        layer.text([x, y + 1, 14, 12], "?", style=S(9, 700, color, "center"))
    elif kind == "mail":
        layer.rect([x, y + 2, 14, 10], radius=2, **o)
        layer.path(f"M{x+1},{y+3} l6,4.5 l6,-4.5", **o)
    elif kind == "book":
        layer.path(f"M{x+1},{y+1} h6 a2,2 0 0 1 2,2 v10 a2,2 0 0 0 -2,-2 h-6 Z", **o)
        L(x + 9, y + 3, x + 13, y + 3)
    elif kind == "wave":
        layer.path(f"M{x+1},{cy} l3,-4 l3,8 l3,-8 l3,4", **o)
    else:
        layer.rect([x, y, 14, 14], radius=3, **o)


def github_mark(layer, cx, cy):
    # simplified GitHub invertocat: filled dark disc + the tail notch
    layer.ellipse([cx, cy], 7.5, 7.5, fill="ink2")
    layer.path(f"M{cx - 2.5},{cy + 7} v-2.5 a2.5,2.5 0 0 1 5,0 v2.5",
               fill="white", decorative=True)
    layer.path(f"M{cx},{cy + 3} v4", fill="none", stroke="white",
               stroke_style={"stroke_width": 1}, decorative=True)


def theme_glyph(layer, cx, cy):
    layer.ellipse([cx, cy], 7, 7, fill="none", stroke="sub",
                  stroke_style={"stroke_width": 1.4})
    layer.path(f"M{cx},{cy - 7} A7,7 0 0 1 {cx},{cy + 7} Z", fill="sub", decorative=True)


def topbar(layer):
    layer.rect([0, 0, W, 4], fill="purple")
    layer.line([0, 50], [W, 50], stroke="border", stroke_style={"stroke_width": 1})
    x = 18
    for label in ["Home", "Docs", "Components", "Blocks", "Charts", "Directory", "Create"]:
        lw = tw(label, 13, 500)
        layer.text([x, 18, lw + 8, 18], label, style=S(13, 500, "ink2"))
        x += lw + 18
    # ---- right cluster: laid out left -> right, ending at the 1992 margin ----
    rx = 1486
    layer.rect([rx, 13, 250, 26], fill="white", radius=7, stroke="border",
               stroke_style={"stroke_width": 1})
    sgx = rx + 16
    layer.ellipse([sgx, 26], 5, 5, fill="none", stroke="mut",
                  stroke_style={"stroke_width": 1.4})
    layer.line([sgx + 3.5, 29.5], [sgx + 7, 33], stroke="mut",
               stroke_style={"stroke_width": 1.4, "stroke_linecap": "round"})
    layer.text([rx + 30, 19, 210, 16], "Search documentation...", style=S(12, 400, "mut"))
    cx = rx + 250 + 22
    github_mark(layer, cx, 26)
    layer.text([cx + 13, 19, 44, 16], "117k", style=S(12, 500, "sub"))
    cx2 = cx + 13 + tw("117k", 12, 500) + 16
    theme_glyph(layer, cx2, 26)
    cx3 = cx2 + 16
    layer.text([cx3, 19, 60, 16], "Open in", style=S(12, 500, "ink2"))
    vx = cx3 + tw("Open in", 12, 500) + 9
    layer.rect([vx, 15, 24, 22], fill="black", radius=5)
    layer.text([vx + 6, 19, 24, 16], "v0", style=S(11, 700, "white"))
    gx = vx + 24 + 12
    gw = 1992 - gx
    layer.rect([gx, 13, gw, 26], fill="black", radius=7)
    layer.text([gx + (gw - tw("Get Code", 12, 600)) / 2, 19, 80, 16], "Get Code",
               style=S(12, 600, "white"))


def sidebar(layer):
    x, y, w = 8, 56, 164
    layer.rect([x, y, w, 700], fill="sb_bg", radius=12)
    # header
    layer.text([x + 16, y + 16, 100, 18], "Menu", style=S(13, 600, "sb_txt"))
    for i in range(3):
        layer.line([x + w - 30, y + 18 + i * 5], [x + w - 16, y + 18 + i * 5],
                   stroke="sb_sub", stroke_style={"stroke_width": 1.6})

    rows = [
        ("Style", "Nova", "swatch"), ("Base Color", "Neutral", "circle"),
        ("Theme", "Neutral", "circle"), ("Chart Color", "Neutral", "circle"),
        ("Heading", "Inter", "Aa"), ("Font", "Inter", "Aa"),
        ("Icon Library", "Lucide", "chev"), ("Radius", "Default", "corner"),
        ("Menu", "Default / Solid", "lines"), ("Menu Accent", "Subtle", "drop"),
    ]
    ry = y + 48
    rh = 44
    for label, value, icon in rows:
        layer.rect([x + 12, ry, w - 24, rh - 8], fill="sb_row", radius=8)
        layer.text([x + 24, ry + 6, w - 60, 12], label, style=S(10.5, 400, "sb_sub"))
        layer.text([x + 24, ry + 19, w - 60, 14], value, style=S(12.5, 500, "sb_txt"))
        ix, iy = x + w - 40, ry + 9
        if icon == "circle":
            layer.ellipse([ix + 8, iy + 9], 7, 7, fill="white", stroke="sb_sub",
                          stroke_style={"stroke_width": 1})
        elif icon == "Aa":
            layer.text([ix, iy + 3, 24, 14], "Aa", style=S(12, 500, "sb_txt"))
        elif icon == "swatch":
            layer.rect([ix + 1, iy + 2, 14, 14], fill="white", radius=4)
        elif icon == "chev":
            chev_down(layer, ix + 9, iy + 9, "sb_sub")
        elif icon == "corner":
            layer.path(f"M{ix},{iy+15} v-7 a7,7 0 0 1 7,-7 h7", fill="none",
                       stroke="sb_sub", stroke_style={"stroke_width": 1.6})
        elif icon == "lines":
            for k in range(3):
                layer.line([ix, iy + 4 + k * 5], [ix + 16, iy + 4 + k * 5],
                           stroke="sb_sub", stroke_style={"stroke_width": 1.6})
        elif icon == "drop":
            layer.path(f"M{ix+8},{iy+2} l5,7 a5,5 0 1 1 -10,0 Z", fill="none",
                       stroke="sb_sub", stroke_style={"stroke_width": 1.4})
        ry += rh

    # preset buttons
    by = ry + 6
    btn(layer, [x + 12, by, w - 24, 28], "--preset b0", variant="outline", size=12)
    btn(layer, [x + 12, by + 34, w - 24, 28], "Open Preset", variant="dark", size=12)
    btn(layer, [x + 12, by + 68, w - 24, 28], "Shuffle", variant="dark", size=12)
    layer.rect([x + 12, by + 102, w - 24, 30], fill="white", radius=8)
    layer.text([x + (w - tw("Get Code", 12, 600)) / 2, by + 110, 80, 16], "Get Code",
               style=S(12, 600, "ink2"))


# --------------------------------------------------------------------------- #
# Column 1
# --------------------------------------------------------------------------- #
def c_contribution(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w, 20], "Contribution History", style=S(15, 600, "ink"))
    layer.text([x + 20, y + 40, w, 16], "Last 6 months of activity", style=S(12, 400, "sub"))
    vals = [0.55, 0.74, 0.48, 0.82, 0.5, 0.95]
    labs = ["Dec", "Jan", "Feb", "Mar", "Apr", "May"]
    bars(layer, [x + 20, y + 70, w - 40, 120], vals, labs, color="bardk",
         label_style=S(11, 400, "sub", "center"), gap_ratio=0.45)
    # two stat cells
    cy = y + 222
    layer.line([x + 20, cy - 8], [x + w - 20, cy - 8], stroke="border2",
               stroke_style={"stroke_width": 1})
    layer.text([x + 22, cy, 120, 12], "UPCOMING", style=S(10, 600, "mut", "left", 0.6))
    layer.text([x + 22, cy + 16, 160, 18], "May 25, 2024", style=S(15, 600, "ink"))
    layer.text([x + 22, cy + 40, 160, 14], "$1,000 scheduled", style=S(11.5, 400, "sub"))
    mx = x + w / 2 + 6
    layer.text([mx, cy, 160, 12], "AUTO-SAVE PLAN", style=S(10, 600, "mut", "left", 0.6))
    layer.text([mx, cy + 16, 160, 18], "Accelerated", style=S(15, 600, "ink"))
    layer.text([mx, cy + 40, 160, 14], "Recurring weekly", style=S(11.5, 400, "sub"))
    btn(layer, [x + 20, y + h - 44, w - 40, 32], "View Full Report")


def c_distribute(layer, box):
    x, y, w, h = box
    card(layer, box)
    cx = x + w / 2
    layer.ellipse([cx, y + 44, ], 18, 18, fill="white", stroke="border",
                  stroke_style={"stroke_width": 1.2})
    layer.line([cx - 6, y + 44], [cx + 6, y + 44], stroke="sub",
               stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})
    layer.line([cx, y + 38], [cx, y + 50], stroke="sub",
               stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})
    layer.text([x, y + 76, w, 20], "Distribute Track", style=S(15, 600, "ink", "center"))
    layer.text([x + 24, y + 104, w - 48, 60],
               "Upload your first master to start reaching\nlisteners on Spotify, Apple Music, and more.",
               style=S(12, 400, "sub", "center", 0, 1.45))
    bwd = tw("Create Release", 13, 600) + 32
    btn(layer, [cx - bwd / 2, y + h - 52, bwd, 32], "Create Release")


def c_qr(layer, box):
    x, y, w, h = box
    card(layer, box)
    qs = 120
    qx, qy = x + (w - qs) / 2, y + 16
    layer.rect([qx, qy, qs, qs], fill="white", radius=6, stroke="border",
               stroke_style={"stroke_width": 1})
    _qr(layer, qx + 8, qy + 8, qs - 16)
    layer.text([x, qy + qs + 12, w, 18], "Scan to connect your mobile device",
               style=S(12.5, 600, "ink", "center"))
    layer.text([x + 18, qy + qs + 34, w - 36, 36],
               "Open the Ledger mobile app and scan this\ncode to link your device.",
               style=S(11, 400, "sub", "center", 0, 1.4))
    layer.rect([x + 20, y + h - 42, w - 40, 30], fill="fieldbg", radius=8,
               stroke="border", stroke_style={"stroke_width": 1})
    layer.text([x, y + h - 35, w, 16], "Got it", style=S(12.5, 600, "ink2", "center"))


def _qr(layer, x, y, s):
    n = 13
    cell = s / n
    pat = [
        "1111111011101",
        "1000001010101",
        "1011101000111",
        "1011101011001",
        "1011101010101",
        "1000001001101",
        "1111111010101",
        "0000000011001",
        "1101011101011",
        "0100100010100",
        "1110111011101",
        "0010001000101",
        "1011101110111",
    ]
    for r in range(n):
        for c in range(n):
            if pat[r][c] == "1":
                layer.rect([x + c * cell, y + r * cell, cell + 0.5, cell + 0.5],
                           fill="black", decorative=True)


def c_dividend(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w - 40, 18], "Q2 Dividend Income", style=S(14, 600, "ink"))
    close_x(layer, x + w - 22, y + 25)
    layer.text([x + 20, y + 44, w - 40, 50],
               "Quarterly dividend payouts across your\nportfolio holdings.",
               style=S(12, 400, "sub", "left", 0, 1.45))


# --------------------------------------------------------------------------- #
# Column 2
# --------------------------------------------------------------------------- #
def c_payout_threshold(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w - 40, 18], "Payout Threshold", style=S(15, 600, "ink"))
    close_x(layer, x + w - 22, y + 25)
    layer.text([x + 20, y + 42, w - 40, 40],
               "Set the minimum balance required before a\npayout is triggered.",
               style=S(12, 400, "sub", "left", 0, 1.4))
    layer.text([x + 20, y + 92, w, 14], "Preferred Currency", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 110, w - 40, 36], "USD — United States Dollar", chevron=True, size=11.5)
    layer.text([x + 20, y + 161, 150, 14], "Minimum Payout Amount", style=S(10.5, 500, "ink2"))
    layer.text([x + w - 110, y + 153, 90, 20], "$2500.00", style=S(16, 700, "ink", "right"))
    # slider
    sy = y + 190
    progress(layer, x + 20, sy, w - 40, 0.32, h=5)
    layer.ellipse([x + 20 + (w - 40) * 0.32, sy + 2.5], 8, 8, fill="white",
                  stroke="fill", stroke_style={"stroke_width": 2})
    layer.text([x + 20, sy + 16, 80, 14], "$50 (MIN)", style=S(11, 400, "sub"))
    layer.text([x + w - 110, sy + 16, 90, 14], "$10,000 (MAX)", style=S(11, 400, "sub", "right"))
    layer.text([x + 20, y + 234, 60, 14], "Notes", style=S(12.5, 500, "ink2"))
    layer.rect([x + 20, y + 252, w - 40, 48], fill="white", radius=8, stroke="border",
               stroke_style={"stroke_width": 1})
    layer.text([x + 30, y + 262, w - 60, 16], "Add any notes for this payout configuration...",
               style=S(11.5, 400, "mut"))
    layer.line([x + w - 30, y + 294], [x + w - 24, y + 288], stroke="mut",
               stroke_style={"stroke_width": 1})
    layer.line([x + w - 30, y + 290], [x + w - 25, y + 285], stroke="mut",
               stroke_style={"stroke_width": 1})
    btn(layer, [x + 20, y + h - 46, w - 40, 32], "Save Threshold")


def c_claimable(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w, 16], "Claimable Balance", style=S(12.5, 500, "sub"))
    layer.text([x + 20, y + 38, w, 44], "$0.00", style=S(38, 700, "ink", "left", -1))
    layer.ellipse([x + 26, y + 96, ], 4, 4, fill="yellow")
    layer.text([x + 36, y + 88, 140, 16], "Pending Setup", style=S(12, 500, "ink2"))
    rows = [("Net Royalties", "$0.00"), ("Processing Fee", "-$0.00"),
            ("Total Ready to Claim", "$0.00 USD")]
    ry = y + 118
    for i, (lab, val) in enumerate(rows):
        layer.line([x + 20, ry - 6, ], [x + w - 20, ry - 6], stroke="border2",
                   stroke_style={"stroke_width": 1}) if i else None
        bold = i == 2
        layer.text([x + 20, ry + 6, 160, 16], lab,
                   style=S(12.5, 600 if bold else 400, "ink2" if bold else "sub"))
        layer.text([x + w - 140, ry + 6, 120, 16], val,
                   style=S(12.5, 600 if bold else 500, "ink2", "right"))
        ry += 30
    layer.text([x + 20, ry + 8, w - 40, 70],
               "Once your bank is connected, balances over\n$10.00 are automatically eligible for monthly\ndistribution on the 15th of each month.",
               style=S(11.5, 400, "sub", "left", 0, 1.5))


def c_preferences(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w - 40, 18], "Preferences", style=S(15, 600, "ink"))
    close_x(layer, x + w - 22, y + 25)
    layer.text([x + 20, y + 42, w - 40, 40],
               "Manage your account settings and\nnotifications.",
               style=S(12, 400, "sub", "left", 0, 1.4))
    layer.text([x + 20, y + 92, w, 14], "Default Currency", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 110, w - 40, 36], "USD — United States Dollar", chevron=True, size=11.5)
    # toggles
    ty = y + 166
    for lab, sub in [("Public Statistics", "Allow others to see your total stream count\nand listening activity"),
                     ("Email Notifications", "Monthly royalty reports and distribution\nupdates")]:
        layer.text([x + 20, ty, w - 80, 14], lab, style=S(12.5, 500, "ink2"))
        layer.text([x + 20, ty + 18, w - 80, 32], sub, style=S(11, 400, "sub", "left", 0, 1.4))
        toggle(layer, x + w - 56, ty, on=True)
        ty += 64
    layer.line([x + 20, ty - 2], [x + w - 20, ty - 2], stroke="border2",
               stroke_style={"stroke_width": 1})
    btn(layer, [x + w - 144, ty + 10, 124, 32], "Save Preferences")
    btn(layer, [x + 20, ty + 10, 60, 32], "Reset", variant="outline")


# --------------------------------------------------------------------------- #
# Column 3
# --------------------------------------------------------------------------- #
def c_savings(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w, 20], "Savings Targets", style=S(15, 600, "ink"))
    badge(layer, x + w - 92, y + 16, "New Goal")
    layer.text([x + 20, y + 42, w, 16], "Active milestones for 2024", style=S(12, 400, "sub"))
    goals = [("RETIREMENT", "$420,000", 0.65, "65% achieved", "$273,000"),
             ("REAL ESTATE", "$85,000", 0.32, "32% achieved", "$27,200")]
    gy = y + 70
    for tag, amt, pct, pl, pr in goals:
        layer.rect([x + 20, gy, w - 40, 88], fill="fieldbg", radius=10, stroke="border2",
                   stroke_style={"stroke_width": 1})
        layer.text([x + 34, gy + 14, 200, 12], tag, style=S(10, 600, "mut", "left", 0.6))
        layer.text([x + 34, gy + 30, 200, 30], amt, style=S(24, 700, "ink", "left", -0.5))
        progress(layer, x + 34, gy + 66, w - 68, pct, h=5)
        layer.text([x + 34, gy + 74, 140, 14], pl, style=S(11, 400, "sub")) \
            if False else None
        gy += 100
    layer.text([x + 34, y + 70 + 74, 140, 14], "65% achieved", style=S(11, 400, "sub"))
    layer.text([x + w - 130, y + 70 + 74, 110, 14], "$273,000", style=S(11.5, 600, "ink2", "right"))
    layer.text([x + 34, y + 170 + 74, 140, 14], "32% achieved", style=S(11, 400, "sub"))
    layer.text([x + w - 130, y + 170 + 74, 110, 14], "$27,200", style=S(11.5, 600, "ink2", "right"))
    layer.text([x + 16, y + h - 30, w - 32, 16], "You have not met your targets for this year.",
               style=S(10.5, 400, "sub", "center"))


def c_transactions(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, 200, 20], "Recent Transactions", style=S(15, 600, "ink"))
    layer.rect([x + w - 96, y + 16, 76, 24], fill="white", radius=7, stroke="border",
               stroke_style={"stroke_width": 1})
    layer.text([x + w - 84, y + 21, 60, 14], "View All", style=S(11.5, 500, "ink2"))
    layer.text([x + 20, y + 42, w, 16], "Your latest account activity", style=S(12, 400, "sub"))
    rows = [
        ("Blue Bottle Coffee", "Food & Drink", "Today, 10:24 AM", "-$6.50", "ink2", "bag"),
        ("Whole Foods Market", "Groceries", "Yesterday", "-$142.30", "ink2", "bag"),
        ("Stripe Payout", "Income", "Oct 12", "+$4,200.00", "green", "card"),
        ("Uber Technologies", "Transport", "Oct 11", "-$24.10", "ink2", "ring"),
        ("Netflix Subscription", "Entertainment", "Oct 10", "-$19.99", "ink2", "card"),
    ]
    ry = y + 72
    for name, cat, when, amt, acol, gl in rows:
        small_icon(layer, x + 20, ry, 30, glyph=gl)
        layer.text([x + 62, ry - 1, 220, 16], name, style=S(13, 600, "ink2"))
        layer.text([x + 62, ry + 16, 220, 14], cat, style=S(11.5, 400, "sub"))
        layer.text([x + w * 0.52, ry + 6, 130, 16], when, style=S(12, 400, "sub"))
        layer.text([x + w - 130, ry + 6, 90, 16], amt, style=S(13, 600, acol, "right"))
        layer.text([x + w - 30, ry + 4, 16, 16], "...", style=S(14, 600, "mut"))
        ry += 40


def c_navmenu(layer, box):
    x, y, w, h = box
    card(layer, box)
    midx = x + w / 2
    layer.line([midx, y + 14], [midx, y + h - 14], stroke="border2",
               stroke_style={"stroke_width": 1})
    left = [("Overview", None), ("Dashboard", "grid"), ("Transactions", "list"),
            ("Investments", "chart"), ("Accounts", "wallet"), ("Spending", "coin"),
            ("Planning", None), ("Goals", "flag"), ("Budget", "pie"),
            ("Reports", "doc"), ("Documents", "doc")]
    right = [("Account", None), ("Profile", "user"), ("Billing", "card"),
             ("Notifications", "bell"), ("Security", "lock"), ("Appearance", "eye"),
             ("Support", None), ("Help Center", "help"), ("Contact Us", "mail"),
             ("Documentation", "book"), ("Status", "wave")]

    def col(items, cx):
        iy = y + 16
        for label, icon in items:
            if icon is None:
                iy += 6 if iy > y + 16 else 0
                layer.text([cx, iy, 140, 14], label, style=S(11, 600, "mut", "left", 0.4))
                iy += 24
            else:
                active = label == "Dashboard"
                if active:
                    layer.rect([cx - 6, iy - 4, w / 2 - 28, 26], fill="fieldbg", radius=6)
                menu_icon(layer, cx, iy, icon, color="ink2" if active else "sub")
                layer.text([cx + 22, iy, 150, 16], label,
                           style=S(12.5, 500 if active else 400, "ink2"))
                iy += 30
    col(left, x + 22)
    col(right, midx + 22)


# --------------------------------------------------------------------------- #
# Column 4
# --------------------------------------------------------------------------- #
def c_buy(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w, 20], "Buy Investment", style=S(15, 600, "ink"))
    layer.text([x + 20, y + 48, w, 14], "Amount to Invest", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 66, w - 40, 36], "1,000.00", prefix="$")
    layer.text([x + 20, y + 114, w, 14], "Order Type", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 132, w - 40, 36], "Market Order", chevron=True)
    layer.text([x + 20, y + 176, w - 24, 16], "Market orders execute at the current price.",
               style=S(10.5, 400, "sub"))
    layer.line([x + 20, y + 204], [x + w - 20, y + 204], stroke="border2",
               stroke_style={"stroke_width": 1})
    layer.text([x + 20, y + 214, 160, 14], "Estimated Shares", style=S(12.5, 400, "sub"))
    layer.text([x + w - 100, y + 214, 80, 14], "1.95", style=S(12.5, 600, "ink2", "right"))
    layer.text([x + 20, y + 238, 160, 14], "Buying Power", style=S(12.5, 400, "sub"))
    layer.text([x + w - 120, y + 238, 100, 14], "$12,450.00", style=S(12.5, 600, "ink2", "right"))
    btn(layer, [x + 20, y + 268, w - 40, 34], "Review Order")
    layer.text([x + 20, y + 314, w - 40, 30],
               "Trades are typically executed within minutes during\nmarket hours.",
               style=S(11, 400, "sub", "center", 0, 1.4))


def c_breadcrumb(layer, box):
    x, y, w, h = box
    card(layer, box)
    # breadcrumb
    layer.text([x + 20, y + 16, 60, 14], "Home", style=S(12, 400, "sub"))
    chev_right(layer, x + 64, y + 23, "mut")
    layer.text([x + 74, y + 16, 24, 14], "...", style=S(12, 600, "mut"))
    chev_right(layer, x + 100, y + 23, "mut")
    layer.text([x + 112, y + 16, 100, 14], "Payments", style=S(12, 500, "ink2"))
    items = [
        ("Change transfer limit", "Adjust how much you can send from\nyour balance."),
        ("Scheduled transfers", "Set up a transfer to send at a later date."),
        ("Direct Debits", "Set up and manage regular payments."),
        ("Recurring card payments", "Manage your repeated card\ntransactions."),
    ]
    iy = y + 48
    for title, sub in items:
        ih = 58
        layer.rect([x + 14, iy, w - 28, ih - 8], fill="white", radius=9, stroke="border2",
                   stroke_style={"stroke_width": 1})
        layer.rect([x + 26, iy + 14, 16, 16], fill="none", stroke="sub",
                   stroke_style={"stroke_width": 1.2}, radius=4)
        layer.text([x + 54, iy + 11, w - 110, 16], title, style=S(12.5, 600, "ink2"))
        layer.text([x + 54, iy + 28, w - 110, 28], sub, style=S(11, 400, "sub", "left", 0, 1.35))
        chev_right(layer, x + w - 30, iy + (ih - 8) / 2, "mut", s=5)
        iy += ih


# --------------------------------------------------------------------------- #
# Column 5
# --------------------------------------------------------------------------- #
def c_account_access(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w, 20], "Account Access", style=S(15, 600, "ink"))
    layer.text([x + 20, y + 42, w - 18, 16], "Update your credentials or re-authenticate.",
               style=S(10, 400, "sub"))
    layer.text([x + 20, y + 70, w, 14], "Email Address", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 88, w - 40, 34], "artist@studio.inc")
    layer.text([x + 20, y + 132, 140, 14], "Current Password", style=S(12.5, 500, "ink2"))
    layer.text([x + w - 80, y + 132, 60, 14], "FORGOT?", style=S(10.5, 600, "blue", "right", 0.4))
    layer.rect([x + 20, y + 150, w - 40, 34], fill="white", radius=8, stroke="blue",
               stroke_style={"stroke_width": 1.4})
    layer.text([x + 32, y + 160, 160, 16], "•" * 12, style=S(13, 600, "ink2"))
    # bitwarden shield glyph
    shx, shy = x + w - 38, y + 159
    layer.path(f"M{shx},{shy} l8,2 v6 q0,5 -8,8 q-8,-3 -8,-8 v-6 Z", fill="blue",
               decorative=True)
    layer.path(f"M{shx-3.5},{shy+8} l2.5,2.5 l5,-5", fill="none", stroke="white",
               stroke_style={"stroke_width": 1.3, "stroke_linecap": "round"}, decorative=True)
    # bitwarden dropdown
    layer.text([x + 32, y + 192, 160, 14], "Save to Bitwarden", style=S(12, 500, "blue"))
    layer.rect([x + 20, y + 214, w - 40, 30], fill="black", radius=7)
    usw = tw("Update Security", 12, 600)
    usx = x + (w - usw - 18) / 2
    layer.path(f"M{usx+4},{y+228} v-2 a3,3 0 0 1 6,0 v2", fill="none", stroke="white",
               stroke_style={"stroke_width": 1.2})
    layer.rect([usx + 1, y + 228, 12, 8], fill="white", radius=1.5)
    layer.text([usx + 20, y + 221, 160, 16], "Update Security", style=S(12, 600, "white"))
    # danger zone
    layer.line([x + 20, y + 256], [x + w - 20, y + 256], stroke="border2",
               stroke_style={"stroke_width": 1})
    layer.ellipse([x + 28, y + 274, ], 6, 6, fill="none", stroke="red",
                  stroke_style={"stroke_width": 1.4})
    layer.text([x + 42, y + 268, 160, 14], "Danger Zone", style=S(12.5, 600, "red"))
    layer.text([x + 42, y + 286, w - 54, 14], "Archive account and remove catalog",
               style=S(10.5, 400, "sub"))
    chev_right(layer, x + w - 28, y + 282, "mut", s=5)


def c_card_balance(layer, box):
    x, y, w, h = box
    # left mini
    lw = w * 0.56
    card(layer, [x, y, lw - 6, h])
    layer.text([x + 18, y + 16, 120, 14], "Card Balance", style=S(11.5, 500, "sub"))
    layer.text([x + 18, y + 34, 140, 24], "US$12.94", style=S(20, 700, "ink", "left", -0.5))
    layer.text([x + 18, y + 62, 160, 14], "US$11,337.06", style=S(11.5, 400, "sub"))
    layer.text([x + 18, y + 78, 160, 14], "Available", style=S(11.5, 400, "sub"))
    # right mini
    rx = x + lw + 6
    rw = w - lw - 6
    card(layer, [rx, y, rw, h])
    layer.text([rx + 16, y + 16, 120, 14], "Payment Due", style=S(11.5, 500, "sub"))
    layer.text([rx + 16, y + 32, 120, 24], "1 Apr", style=S(20, 700, "ink", "left", -0.5))
    layer.rect([rx + 16, y + 66, 80, 26], fill="white", radius=7, stroke="border",
               stroke_style={"stroke_width": 1})
    layer.text([rx + 28, y + 72, 70, 14], "Pay Early", style=S(11.5, 500, "ink2"))


def c_yearly(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 18, y + 16, 110, 16], "Yearly Activity", style=S(12.5, 500, "sub"))
    bw = tw("+US$0.25 Daily Cash", 10.5, 500) + 20
    badge(layer, x + w - bw - 16, y + 14, "+US$0.25 Daily Cash", bg="white", fg="ink2", size=10.5)
    vals = [0.4, 0.55, 0.45, 0.62, 0.5, 0.66, 0.72, 0.5, 0.6, 0.46, 0.56, 0.86]
    labs = list("JFMAMJJASOND")
    bars(layer, [x + 18, y + 44, w - 36, 54], vals, labs, color="bardk",
         label_style=S(9.5, 400, "sub", "center"), gap_ratio=0.4, radius=2)


def c_transfer(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w - 40, 20], "Transfer Funds", style=S(15, 600, "ink"))
    close_x(layer, x + w - 22, y + 25)
    layer.text([x + 20, y + 42, w - 40, 32], "Move money between your connected\naccounts.",
               style=S(11.5, 400, "sub", "left", 0, 1.4))
    layer.text([x + 20, y + 84, 160, 14], "Amount to Transfer", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 102, w - 40, 34], "1,200.00", prefix="$")
    layer.text([x + 20, y + 146, 140, 14], "From Account", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 164, w - 40, 34], "Main Checking (··8402) — $12,450.00", chevron=True, size=11)
    layer.text([x + 20, y + 208, 140, 14], "To Account", style=S(12.5, 500, "ink2"))
    field(layer, [x + 20, y + 226, w - 40, 34], "High Yield Savings (··1192) — $42,100.00", chevron=True, size=11)
    rows = [("Estimated arrival", "Today, Apr 14", "ink2"),
            ("Transaction fee", "$0.00", "sub"),
            ("Total amount", "$1,200.00", "ink2")]
    ry = y + 274
    for lab, val, vc in rows:
        layer.text([x + 20, ry, 160, 14], lab, style=S(12, 400, "sub"))
        layer.text([x + w - 140, ry, 120, 14], val, style=S(12.5, 600, vc, "right"))
        ry += 30
    btn(layer, [x + 20, ry + 4, w - 40, 34], "Confirm Transfer")


# --------------------------------------------------------------------------- #
# Column 6
# --------------------------------------------------------------------------- #
def c_payout_pref(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 16, w - 40, 16], "Payout Preferences", style=S(12.5, 500, "sub"))
    close_x(layer, x + w - 22, y + 23)
    layer.text([x + 20, y + 36, w, 18], "Receiving Method", style=S(15, 600, "ink"))
    layer.text([x + 20, y + 62, w, 14], "Account Holder Name", style=S(12, 500, "ink2"))
    field(layer, [x + 20, y + 80, w - 40, 34], "Synthetic Horizons Music LLC", size=11.5)
    layer.text([x + 20, y + 124, w, 14], "Receiving Method", style=S(12, 500, "ink2"))
    # two radio options
    ow = (w - 50) / 2
    layer.rect([x + 20, y + 142, ow, 44], fill="white", radius=8, stroke="black",
               stroke_style={"stroke_width": 1.4})
    layer.ellipse([x + 32, y + 156, ], 5, 5, fill="none", stroke="black",
                  stroke_style={"stroke_width": 1.4})
    layer.ellipse([x + 32, y + 156, ], 2.2, 2.2, fill="black")
    layer.text([x + 44, y + 150, ow, 14], "Bank Transfer", style=S(12, 600, "ink2"))
    layer.text([x + 44, y + 166, ow, 12], "SWIFT / IBAN", style=S(10.5, 400, "sub"))
    rx2 = x + 30 + ow
    layer.rect([rx2, y + 142, ow, 44], fill="white", radius=8, stroke="border",
               stroke_style={"stroke_width": 1})
    layer.ellipse([rx2 + 12, y + 156, ], 5, 5, fill="none", stroke="mut",
                  stroke_style={"stroke_width": 1.4})
    layer.text([rx2 + 24, y + 150, ow, 14], "PayPal", style=S(12, 600, "ink2"))
    layer.text([rx2 + 24, y + 166, ow, 12], "Instant Payout", style=S(10.5, 400, "sub"))
    layer.text([x + 20, y + 200, w, 14], "IBAN / Account Number", style=S(12, 500, "ink2"))
    field(layer, [x + 20, y + 218, w - 40, 34], "DE89 3704 0044 ....")
    layer.rect([x + 20, y + h - 44, w - 40, 32], fill="btnlight", radius=8)
    layer.text([x, y + h - 36, w, 16], "Save Payout Settings", style=S(12.5, 600, "sub", "center"))


def c_power(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w, 18], "Power Usage", style=S(15, 600, "ink"))
    layer.text([x + 20, y + 40, w, 14], "Whole Home", style=S(11.5, 400, "sub"))
    vals = [0.35, 0.5, 0.42, 0.55, 0.6, 0.72, 0.88, 0.66]
    labs = ["6a", "8a", "10a", "12p", "2p", "4p", "6p", "8p"]
    bars(layer, [x + 20, y + 66, w - 40, 78], vals, labs, color="bardk",
         label_style=S(10, 400, "sub", "center"), gap_ratio=0.4)
    cy = y + 176
    layer.text([x + 20, cy, 140, 14], "Currently Using", style=S(11.5, 400, "sub"))
    layer.text([x + 20, cy + 16, 120, 22], "3.4 kW", style=S(18, 700, "ink", "left", -0.5))
    layer.text([x + w / 2 + 6, cy, 120, 14], "Solar Gen", style=S(11.5, 400, "sub"))
    layer.text([x + w / 2 + 6, cy + 16, 120, 22], "+1.2 kW", style=S(18, 700, "mut", "left", -0.5))
    layer.text([x + 20, cy + 52, 140, 14], "Battery Level", style=S(11.5, 400, "sub"))
    layer.text([x + w - 60, cy + 52, 40, 14], "85%", style=S(11.5, 600, "ink2", "right"))
    progress(layer, x + 20, cy + 72, w - 40, 0.85, h=6)


def c_connect(layer, box):
    x, y, w, h = box
    card(layer, box)
    cx = x + w / 2
    layer.rect([cx - 16, y + 26, 32, 24], fill="none", stroke="sub",
               stroke_style={"stroke_width": 1.4}, radius=5)
    layer.line([cx - 16, y + 34], [cx + 16, y + 34], stroke="sub",
               stroke_style={"stroke_width": 1.4})
    layer.text([x, y + 64, w, 18], "Connect Bank", style=S(15, 600, "ink", "center"))
    layer.text([x + 18, y + 92, w - 36, 56],
               "Link your payout method to receive\nmonthly royalty distributions automatically.",
               style=S(11, 400, "sub", "center", 0, 1.45))
    bwd = tw("Set Up Payouts", 12.5, 600) + 32
    btn(layer, [cx - bwd / 2, y + h - 44, bwd, 30], "Set Up Payouts")


def c_calendar(layer, box):
    x, y, w, h = box
    card(layer, box)
    layer.text([x + 20, y + 18, w, 18], "Upcoming Payments", style=S(15, 600, "ink"))
    layer.text([x + 20, y + 42, w, 14], "Select a date to view scheduled payments.",
               style=S(11.5, 400, "sub"))
    # month header
    hy = y + 70
    layer.rect([x + 16, hy, w - 32, 30], fill="white", radius=8, stroke="border2",
               stroke_style={"stroke_width": 1})
    layer.line([x + 35, hy + 10], [x + 30, hy + 15], stroke="ink2",
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})
    layer.line([x + 30, hy + 15], [x + 35, hy + 20], stroke="ink2",
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})
    layer.text([x, hy + 8, w, 16], "June 2026", style=S(12.5, 600, "ink2", "center"))
    layer.line([x + w - 36, hy + 11], [x + w - 32, hy + 15], stroke="ink2",
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})
    layer.line([x + w - 32, hy + 15], [x + w - 36, hy + 19], stroke="ink2",
               stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})
    # weekday row
    days = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
    cw = (w - 32) / 7
    wy = hy + 40
    for i, d in enumerate(days):
        layer.text([x + 16 + i * cw, wy, cw, 14], d, style=S(10.5, 500, "mut", "center"))
    # one partial week (June 2026 starts on Monday)
    ny = wy + 22
    for i, dnum in enumerate(["", "1", "2", "3", "4", "5", "6"]):
        if dnum:
            layer.text([x + 16 + i * cw, ny, cw, 14], dnum, style=S(11, 400, "ink2", "center"))


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="shadcn v0 — radix-nova gallery recreation",
                          profile="diagram", lang="en")
    for name, value in COLORS.items():
        doc.define_color(name, value)

    page = doc.page("radix_nova", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")
    bg = page.layer("bg")
    bg.rect([0, 0, W, H], fill="page")
    layer = page.layer("main")

    topbar(layer)
    sidebar(layer)

    # column geometry: (x, width)
    C1, W1 = 213, 266
    C2, W2 = 521, 244
    C3, W3 = 808, 264
    C4, W4 = 1105, 256
    C5, W5 = 1402, 252
    C6, W6 = 1700, 259
    WIDE = 553  # recent transactions spans C3+C4

    # C1
    c_contribution(layer, [C1, 68, W1, 330])
    c_distribute(layer, [C1, 415, W1, 256])
    c_qr(layer, [C1, 688, W1, 248])
    c_dividend(layer, [C1, 952, W1, 110])
    # C2
    c_payout_threshold(layer, [C2, 68, W2, 366])
    c_claimable(layer, [C2, 450, W2, 300])
    c_preferences(layer, [C2, 766, W2, 304])
    # C3
    c_savings(layer, [C3, 68, W3, 348])
    c_transactions(layer, [C3, 420, WIDE, 238])
    c_navmenu(layer, [C3, 706, W3, 348])
    # C4
    c_buy(layer, [C4, 68, W4, 300])
    c_breadcrumb(layer, [C4, 706, W4, 290])
    # C5
    c_account_access(layer, [C5, 68, W5, 300])
    c_card_balance(layer, [C5, 380, W5, 96])
    c_yearly(layer, [C5, 484, W5, 118])
    c_transfer(layer, [C5, 606, W5, 360])
    # C6
    c_payout_pref(layer, [C6, 68, W6, 296])
    c_power(layer, [C6, 380, W6, 256])
    c_connect(layer, [C6, 700, W6, 196])
    c_calendar(layer, [C6, 912, W6, 200])

    # cover-art label (c2 bottom)
    layer.text([C2, 1018, 120, 14], "COVER ART", style=S(10.5, 600, "mut", "left", 0.6))
    # pagination 01 02 (bottom-right corner, below the calendar chevron)
    layer.rect([1926, 1006, 26, 22], fill="black", radius=5)
    layer.text([1931, 1011, 24, 14], "01", style=S(10.5, 600, "white"))
    layer.text([1960, 1011, 24, 14], "02", style=S(10.5, 600, "mut"))

    # browser status-bar URL tooltip (bottom-left)
    url = "https://v0.dev/chat/api/open?url=https://ui.shadcn.com/init?v0?preset=b0&base=radix&title=New radix-nova project"
    uw = tw(url, 11, 400) + 24
    layer.rect([0, 1010, uw, 22], fill="#1A1A1A", decorative=True)
    layer.text([12, 1015, uw, 14], url, style=S(11, 400, "white"))

    for name, style in _STYLES.items():
        doc.define_text_style(name, **style)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "static", "examples", "fixtures", "radix-nova-gallery.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warns)} -> {out}")
    for i in errors[:25]:
        print(f"  [ERROR] [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:6]:
        print(f"  [warn] [{i.rule_id}] {i.path}: {i.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
