#!/usr/bin/env python3
"""High-fidelity vector recreation of the "Spendora" SaaS landing page mock-up
(AI Treasury & Spend Management) using the FrameForge SDK.

A single tall web canvas, top to bottom:

  1. Nav + hero    — logo, links, "Start Free Trial", two-line headline, a
                     glowing geometric tile field behind a black Spendora card,
                     a Trustpilot-style trust line.
  2. Logo strip    — six muted partner wordmarks (stylised placeholders).
  3. Feature       — pill + headline + three feature cards with dot-matrix art.
  4. Benefits      — a central plus node fanning out to four benefit cards.
  5. Stats         — 94% / 6.2x / 120+ / $14B with hairline dividers.
  6. Integration   — a dark card with a scattered grid of app-icon tiles.
  7. Pricing       — Starter (white) + Enterprise (pink gradient) plans.
  8. CTA           — "Smarter treasury starts here" with corner tile decor.

Everything lowers to SDK primitives (rect / ellipse / polygon / line / path /
text), gradients and round-cap strokes. Partner logos and app icons are
stylised placeholders, not brand reproductions.

Run from the repository root::

    uv run python examples/spendora_landing.py
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    linear_gradient,
    measure_text,
    radial_gradient,
    rgba,
)
from frameforge.sdk.layout import grid  # noqa: E402
from frameforge.sdk.paint import effects, shadow  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas + palette
# --------------------------------------------------------------------------- #
W = 1440

COLORS = {
    "bg":        "#E9E9EF",
    "white":     "#FFFFFF",
    "ink":       "#15161A",
    "sub":       "#5C6270",
    "muted":     "#9AA0AC",
    "muted2":    "#BCC0CA",
    "hair":      "#EDEDF2",
    "hair2":     "#E2E2EA",
    "chipbg":    "#F3F3F7",
    "pink":      "#E85FD0",
    "magenta":   "#D63CC0",
    "purple":    "#7C6FF0",
    "green":     "#00B67A",
    "btn":       "#17181C",
    "btntext":   "#FFFFFF",
    "dark":      "#101013",
    "darkpill":  "#2A2A30",
}

SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]


def _ts(size, weight=500, color="ink", align="left", ls=0.0, lh=1.3):
    return dict(font_family=SANS, font_size=size, font_weight=weight, color=color,
                align=align, letter_spacing=ls, line_height=lh)


STYLES = {
    "logo":     _ts(17, 800, "ink", "left", 1.5, 1.0),
    "nav":      _ts(15, 500, "ink", "left"),
    "navbtn":   _ts(14, 600, "white", "left"),
    "h1":       _ts(41, 600, "ink", "center", -0.6, 1.22),
    "trust":    _ts(14, 500, "sub", "left"),
    "logoword": _ts(22, 700, "muted2", "center", 0.4),
    "pill":     _ts(12, 700, "sub", "left", 1.6),
    "pillD":    _ts(12, 700, "muted2", "left", 1.6),
    "h2":       _ts(34, 600, "ink", "center", -0.6, 1.22),
    "cardTitle": _ts(21, 600, "ink", "left", -0.2),
    "cardBody": _ts(15, 400, "sub", "left", 0, 1.5),
    "learn":    _ts(14, 600, "ink", "left"),
    "benTitle": _ts(16, 700, "ink", "left", -0.1),
    "benBody":  _ts(13, 400, "sub", "left", 0, 1.45),
    "statNum":  _ts(58, 700, "ink", "left", -1.6),
    "statUnit": _ts(22, 600, "ink", "left"),
    "statLbl":  _ts(14, 500, "sub", "left"),
    "integHead": _ts(30, 600, "white", "center", -0.4, 1.28),
    "cardword": dict(font_family=SANS, font_size=33, font_weight=800,
                     color="#F1E9EF", align="left", letter_spacing=5.0),
    "cardnum":  _ts(13, 600, "#B9B2BE", "left", 1.2),
    "tier":     _ts(15, 600, "ink", "left", 0.3),
    "price":    _ts(46, 700, "ink", "left", -1.2),
    "priceU":   _ts(15, 500, "sub", "left"),
    "feat":     _ts(13.5, 500, "sub", "left"),
    "choose":   _ts(14, 600, "white", "left"),
    "ctaH":     _ts(40, 600, "ink", "center", -0.6),
    "ctaSub":   _ts(15, 400, "sub", "center", 0, 1.5),
}

# --------------------------------------------------------------------------- #
# Paint helpers
# --------------------------------------------------------------------------- #
def lg(p0, p1, stops):
    ang = round(math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])), 1)
    return linear_gradient([(c, p) for (p, c) in stops], angle=ang)


def rg(at, stops, shape="circle"):
    return radial_gradient([(c, p) for (p, c) in stops], at=at, shape=shape)


def panel(layer, box, *, radius=22, fill="white", border="hair2", sh=True, **extra):
    f = dict(fill=fill, radius=radius, **extra)
    if border:
        f["stroke"] = border
        f["stroke_style"] = {"stroke_width": 1}
    if sh:
        f.update(effects(shadow=shadow(dy=14, blur=38, color="#8A8AA4", opacity=0.16)))
    layer.rect(box, **f)


def tw(text, size, weight=500):
    return measure_text(text, font_family=SANS, font_size=size, bold=weight >= 600)


def star(layer, cx, cy, r, fill, rot=-90.0):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        a = math.radians(rot + i * 36)
        pts.append([cx + rad * math.cos(a), cy + rad * math.sin(a)])
    layer.polygon(pts, fill=fill)


# --------------------------------------------------------------------------- #
# Hero geometric tile field
# --------------------------------------------------------------------------- #
PASTEL = {
    "pink":   ("#F8CDEC", "#F0A6DD"),
    "purple": ("#DCC8F6", "#C4A8F0"),
    "blue":   ("#C6D6F6", "#A9C0F0"),
    "cyan":   ("#C2E9E2", "#A6DED5"),
    "green":  ("#CDEAC6", "#AADFB0"),
    "yellow": ("#F4E9AE", "#EEDC88"),
}
GLOWC = {"pink": "#FF8FE0", "purple": "#B98CFF", "blue": "#7FB0FF",
         "cyan": "#6FE0D4", "green": "#7FE08F", "yellow": "#FFE27A"}
COLHUE = ["pink", "purple", "blue", "cyan", "green", "yellow", "pink"]
GLOWS = [(0, 0, "pink"), (1, 0, "pink"), (5, 0, "yellow"), (6, 0, "yellow"),
         (0, 2, "pink"), (0, 3, "pink"), (6, 2, "yellow"), (6, 3, "green"),
         (2, 3, "cyan"), (3, 3, "purple"), (4, 3, "blue"), (3, 0, "blue")]


def geo_tiles(layer, x0, y0, cols, rows, size, gap):
    with layer.bleed():
        for r in range(rows):
            for c in range(cols):
                lt, dk = PASTEL[COLHUE[c % len(COLHUE)]]
                x = x0 + c * (size + gap)
                y = y0 + r * (size + gap)
                if (c + r) % 2 == 0:
                    layer.polygon([[x, y], [x + size, y], [x, y + size]], fill=lt)
                    layer.polygon([[x + size, y], [x + size, y + size], [x, y + size]], fill=dk)
                else:
                    layer.polygon([[x, y], [x + size, y], [x + size, y + size]], fill=dk)
                    layer.polygon([[x, y], [x + size, y + size], [x, y + size]], fill=lt)
        for (c, r, hue) in GLOWS:
            cx = x0 + c * (size + gap) + size / 2
            cy = y0 + r * (size + gap) + size / 2
            gc = GLOWC[hue]
            layer.ellipse([cx, cy], size * 1.05, size * 1.05,
                          fill=rg("50% 50%", [(0.0, rgba("#FFFFFF", 0.95)),
                                              (0.34, rgba(gc, 0.78)), (1.0, rgba(gc, 0.0))]))
            layer.ellipse([cx, cy], size * 0.30, size * 0.30, fill=rgba("#FFFFFF", 0.9))


def credit_card(layer, box):
    x, y, w, h = box
    layer.rect([x + 12, y + 20, w, h], fill=rgba("#3A1E3A", 0.30), radius=22, decorative=True)
    layer.rect([x, y, w, h], fill=lg([x, y], [x + w, y + h],
               [(0, "#272730"), (1, "#0B0B0F")]), radius=22)
    layer.rect([x, y, w, h * 0.55], fill=lg([x, y], [x, y + h * 0.55],
               [(0, rgba("#FFFFFF", 0.10)), (1, rgba("#FFFFFF", 0.0))]),
               radius=22, decorative=True)
    layer.text([x + 30, y + h * 0.27, w - 60, 44], "SPENDORA", style="cardword")
    layer.text([x + 32, y + h - 52, 240, 20], "****  -  ****  -  0523", style="cardnum")
    mx, my = x + w - 78, y + h - 44
    layer.ellipse([mx, my], 19, 19, fill="#EB001B")
    layer.ellipse([mx + 24, my], 19, 19, fill="#F79E1B")
    layer.ellipse([mx + 12, my], 12, 19, fill="#FF5F00", decorative=True)


# --------------------------------------------------------------------------- #
# Dot-matrix blob for feature cards
# --------------------------------------------------------------------------- #
def dot_blob(layer, box):
    x, y, w, h = box
    cols, rows = 15, 11
    sx, sy = w / (cols + 1), h / (rows + 1)
    cc, rc = (cols - 1) / 2, (rows - 1) / 2
    with layer.bleed():
        for r in range(rows):
            for c in range(cols):
                dx, dy = (c - cc) / cols, (r - rc) / rows
                d = (dx * dx + dy * dy) ** 0.5
                if d <= 0.48:
                    a = 1.0 if d < 0.30 else (0.6 if d < 0.40 else 0.32)
                    layer.ellipse([x + sx * (c + 1), y + sy * (r + 1)], 2.6, 2.6,
                                  fill=rgba("#7C6FF0", a))


def feature_card(layer, box, title, body):
    x, y, w, h = box
    panel(layer, box, radius=18, sh=True)
    layer.text([x + 28, y + 30, w - 56, 26], title, style="cardTitle")
    dot_blob(layer, [x + 26, y + 78, w - 52, h * 0.40])
    layer.text([x + 28, y + h - 116, w - 56, 60], body, style="cardBody")
    layer.text([x + 28, y + h - 46, 120, 18], "[Learn More]", style="learn")
    lw = tw("[Learn More]", 14, 600)
    layer.line([x + 28, y + h - 26], [x + 28 + lw, y + h - 26],
               stroke="ink", stroke_style={"stroke_width": 1})


# --------------------------------------------------------------------------- #
# Benefits node + connectors
# --------------------------------------------------------------------------- #
def node_icon(layer, cx, cy, s=30):
    layer.ellipse([cx, cy], s * 1.9, s * 1.9,
                  fill=rg("50% 50%", [(0, rgba("#EC4FD8", 0.5)), (1, rgba("#EC4FD8", 0.0))]),
                  decorative=True)
    layer.rect([cx - s / 2, cy - s / 2, s, s],
               fill=lg([cx - s / 2, cy - s / 2], [cx + s / 2, cy + s / 2],
                       [(0, "#F06CDE"), (1, "#D63CC0")]), radius=11,
               **effects(shadow=shadow(dy=4, blur=14, color="#D63CC0", opacity=0.5)))
    layer.rect([cx - s / 2, cy - s / 2, s, s], fill="none",
               stroke=rgba("#FFFFFF", 0.5), stroke_style={"stroke_width": 1}, radius=11)
    layer.line([cx - 8, cy], [cx + 8, cy], stroke="white",
               stroke_style={"stroke_width": 3, "stroke_linecap": "round"})
    layer.line([cx, cy - 8], [cx, cy + 8], stroke="white",
               stroke_style={"stroke_width": 3, "stroke_linecap": "round"})


def connector(layer, x1, y1, x2, y2):
    my = (y1 + y2) / 2
    layer.path(f"M {x1:.1f} {y1:.1f} C {x1:.1f} {my:.1f} {x2:.1f} {my:.1f} {x2:.1f} {y2:.1f}",
               fill="none", stroke="#D4D4DE", stroke_style={"stroke_width": 1.4})


def benefit_card(layer, box, title, body):
    x, y, w, h = box
    panel(layer, box, radius=14, sh=False, border="hair2")
    layer.text([x + 20, y + 24, w - 40, 20], title, style="benTitle")
    layer.text([x + 20, y + 54, w - 40, 56], body, style="benBody")


# --------------------------------------------------------------------------- #
# Integration app tiles (stylised placeholders, not brand logos)
# --------------------------------------------------------------------------- #
def _g_chat(layer, cx, cy, col):
    layer.rect([cx - 11, cy - 10, 22, 18], fill=col, radius=6)
    layer.polygon([[cx - 4, cy + 6], [cx - 4, cy + 12], [cx + 3, cy + 6]], fill=col)


def _g_spark(layer, cx, cy, col):
    for a in range(0, 360, 45):
        r = math.radians(a)
        layer.line([cx, cy], [cx + 11 * math.cos(r), cy + 11 * math.sin(r)],
                   stroke=col, stroke_style={"stroke_width": 3, "stroke_linecap": "round"})


def _g_hex(layer, cx, cy, col):
    pts = [[cx + 12 * math.cos(math.radians(60 * i - 90)),
            cy + 12 * math.sin(math.radians(60 * i - 90))] for i in range(6)]
    layer.polygon(pts, fill=col)


def _g_play(layer, cx, cy, col):
    layer.polygon([[cx - 7, cy - 9], [cx - 7, cy + 9], [cx + 9, cy]], fill=col)


def _g_grid(layer, cx, cy, col):
    for dx in (-6, 6):
        for dy in (-6, 6):
            layer.rect([cx + dx - 4, cy + dy - 4, 8, 8], fill=col, radius=2)


def _g_ring(layer, cx, cy, col):
    layer.ellipse([cx, cy], 11, 11, fill="none", stroke=col,
                  stroke_style={"stroke_width": 3.4})


def _g_blob(layer, cx, cy, col):
    layer.ellipse([cx - 4, cy], 7, 9, fill=col)
    layer.ellipse([cx + 4, cy], 7, 9, fill=col)


def _g_cam(layer, cx, cy, col):
    layer.rect([cx - 11, cy - 8, 22, 16], fill=col, radius=5)
    layer.ellipse([cx, cy], 5, 5, fill="#FFFFFF")


GLYPHS = [_g_chat, _g_spark, _g_hex, _g_play, _g_grid, _g_ring, _g_blob, _g_cam]


def app_tile(layer, cx, cy, glyph, col, glow=False, s=46):
    if glow:
        layer.ellipse([cx, cy], s, s,
                      fill=rg("50% 50%", [(0, rgba(col, 0.5)), (1, rgba(col, 0.0))]),
                      decorative=True)
    layer.rect([cx - s / 2, cy - s / 2, s, s], fill="white", radius=12,
               **effects(shadow=shadow(dy=4, blur=14, color="#000000", opacity=0.45)))
    glyph(layer, cx, cy, col)


# --------------------------------------------------------------------------- #
# Pricing card
# --------------------------------------------------------------------------- #
def pricing_card(layer, box, tier, price, period, features, *, highlight=False):
    x, y, w, h = box
    if highlight:
        layer.rect(box, fill=lg([x, y], [x + w, y + h],
                   [(0, "#F7CBEF"), (1, "#EC74D6")]), radius=18,
                   **effects(shadow=shadow(dy=16, blur=44, color="#E06CD0", opacity=0.30)))
        bcol = rgba("#FFFFFF", 0.55)
    else:
        panel(layer, box, radius=18, sh=True, border="hair2")
        bcol = "hair2"
    p = 26
    hh = 56
    layer.text([x + p, y + 20, w - 2 * p, 20], tier, style="tier")
    layer.line([x, y + hh], [x + w, y + hh], stroke=bcol, stroke_style={"stroke_width": 1})
    midx = x + w * 0.46
    layer.line([midx, y + hh], [midx, y + h - 78], stroke=bcol, stroke_style={"stroke_width": 1})
    # price (left cell)
    layer.text([x + p, y + hh + 34, 150, 48], price, style="price")
    pw = tw(price, 46, 700)
    layer.text([x + p + pw + 6, y + hh + 56, 60, 18], period, style="priceU")
    # features (right cell)
    fy = y + hh + 26
    for feat in features:
        layer.ellipse([midx + 22, fy + 8], 2.6, 2.6, fill="sub")
        layer.text([midx + 32, fy, w - (midx - x) - 44, 18], feat, style="feat")
        fy += 26
    # button
    bx = [x + p, y + h - 58, w - 2 * p, 38]
    layer.rect(bx, fill="btn", radius=10)
    cw = tw("Choose Plans", 14, 600)
    layer.text([bx[0] + (bx[2] - cw) / 2, bx[1] + 11, cw + 6, 18], "Choose Plans", style="choose")


# --------------------------------------------------------------------------- #
# CTA corner decor
# --------------------------------------------------------------------------- #
def corner_tiles(layer, x0, y0, hue, flip=1):
    lt, dk = PASTEL[hue]
    gc = GLOWC[hue]
    with layer.bleed():
        layer.ellipse([x0 + 40 * flip, y0 + 40], 60, 60,
                      fill=rg("50% 50%", [(0, rgba(gc, 0.55)), (1, rgba(gc, 0.0))]))
        for i in range(2):
            for j in range(2):
                x = x0 + (i * 46) * flip - (46 if flip < 0 else 0)
                y = y0 + j * 46
                layer.polygon([[x, y], [x + 42, y], [x, y + 42]], fill=lt)
                layer.polygon([[x + 42, y], [x + 42, y + 42], [x, y + 42]], fill=dk)


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="Spendora — AI Treasury & Spend Management",
                          profile="diagram", lang="en")
    for name, value in COLORS.items():
        doc.define_color(name, value)
    for name, style in STYLES.items():
        doc.define_text_style(name, **style)

    M = 48
    CW = W - 2 * M

    # vertical layout cursor
    y = 40
    HERO = (M, y, CW, 756); y += 756 + 28
    LOGO = (M, y, CW, 150); y += 150 + 92
    FEAT_PILL = y; y += 46
    FEAT_H1 = y; y += 110
    FEAT_CARDS_Y = y; y += 430 + 96
    BEN = (M, y, CW, 392); y += 392 + 90
    STATS = (M, y, CW, 214); y += 214 + 88
    INTEG = (M, y, CW, 500); y += 500 + 96
    PRICE_PILL = y; y += 46
    PRICE_H1 = y; y += 110
    PRICE_CARDS_Y = y; y += 376 + 96
    CTA = (M, y, CW, 376); y += 376 + 44
    H = y

    page = doc.page("spendora", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")
    bg = page.layer("bg")
    bg.rect([0, 0, W, H], fill=lg([0, 0], [0, H], [(0, "#ECECF1"), (1, "#E5E5EC")]))

    layer = page.layer("main")

    # ---- 1. HERO ---------------------------------------------------------- #
    hx, hy, hw, hh = HERO
    panel(layer, HERO, radius=26, sh=True, border="hair")
    # nav
    layer.text([hx + 40, hy + 30, 120, 18], "SPEN", style="logo")
    layer.text([hx + 40, hy + 46, 120, 18], "DORA", style="logo")
    layer.line([hx + 30, hy + 34], [hx + 30, hy + 60], stroke="ink",
               stroke_style={"stroke_width": 2})
    navs = ["Home", "Work", "Services", "About"]
    nxs = [600, 690, 800, 905]
    for label, nx in zip(navs, nxs):
        layer.text([hx + nx, hy + 40, 90, 18], label, style="nav")
    chx = hx + 690 + tw("Work", 15) + 8
    chy = hy + 49
    layer.line([chx, chy], [chx + 4, chy + 4], stroke="ink",
               stroke_style={"stroke_width": 1.4, "stroke_linecap": "round"})
    layer.line([chx + 4, chy + 4], [chx + 8, chy], stroke="ink",
               stroke_style={"stroke_width": 1.4, "stroke_linecap": "round"})
    # CTA button (sized to content)
    dark_button(layer, hx + hw - 40 - dbw("Start Free Trial"), hy + 30, "Start Free Trial")
    # headline
    layer.text([hx + 120, hy + 130, hw - 240, 120],
               "AI Treasury & Spend Management\nBuilt for Modern Finance Teams", style="h1")
    # geometric field + card
    geo_tiles(layer, 402, hy + 280, 7, 4, 84, 8)
    credit_card(layer, [520, hy + 352, 400, 232])
    # trust line
    trust_txt = "Trusted by 3,500+ finance teams worldwide"
    tt_w = tw(trust_txt, 14)
    total = 5 * 22 + 14 + tt_w
    sx0 = hx + (hw - total) / 2
    ty = hy + hh - 50
    for i in range(5):
        layer.rect([sx0 + i * 24 - 3, ty - 3, 22, 22], fill="green", radius=4, decorative=True)
        star(layer, sx0 + i * 24 + 8, ty + 8, 7.5, "white")
    layer.text([sx0 + 5 * 24 + 10, ty, tt_w + 20, 18], trust_txt, style="trust")

    # ---- 2. LOGO STRIP ---------------------------------------------------- #
    panel(layer, LOGO, radius=20, sh=True, border="hair")
    lx, ly, lw, lh = LOGO
    words = ["Webflow", "qualtrics", "WordPress", "INMOBI", "AXIS", "GONG"]
    for box, word in zip(grid([lx + 40, ly + 56, lw - 80, 40], cols=6, count=6, gap=10), words):
        layer.text([box[0], box[1] + 8, box[2], 24], word, style="logoword")

    # ---- 3. FEATURE ------------------------------------------------------- #
    section_pill(layer, W / 2, FEAT_PILL, "FEATURE")
    layer.text([220, FEAT_H1, 1000, 96],
               "Everything your finance team needs\nin one intelligent platform", style="h2")
    feats = [
        ("AI Cash Flow Forecasting",
         "Predict incoming and outgoing cash movement\nwith machine learning models."),
        ("Smart Spend Monitoring",
         "Track department expenses in real time and\nidentify unusual spending instantly."),
        ("Fraud & Risk Detection",
         "Detect suspicious activities and financial\nanomalies before they become costly issues."),
    ]
    for box, (title, body) in zip(
            grid([96, FEAT_CARDS_Y, W - 192, 430], cols=3, count=3, gap=30), feats):
        feature_card(layer, box, title, body)

    # ---- 4. BENEFITS ------------------------------------------------------ #
    panel(layer, BEN, radius=22, fill="#F4F4F8", sh=False, border="hair2")
    bx, by, bw, bh = BEN
    ncx, ncy = bx + bw / 2, by + 70
    node_icon(layer, ncx, ncy)
    benefits = [
        ("Reduce Costs", "Eliminate repetitive manual\ntreasury tasks."),
        ("Improve Accuracy", "Make faster decisions with\npredictive intelligence."),
        ("Financial Visibility", "See every transaction and\naccount in real time."),
        ("Scale Globally", "Manage multi-entity finances\nfrom one platform."),
    ]
    bcards = grid([bx + 70, by + 150, bw - 140, 168], cols=4, count=4, gap=26)
    for box, (title, body) in zip(bcards, benefits):
        connector(layer, ncx, ncy + 34, box[0] + box[2] / 2, box[1])
        benefit_card(layer, box, title, body)

    # ---- 5. STATS --------------------------------------------------------- #
    panel(layer, STATS, radius=22, sh=True, border="hair")
    sx, sy, sw, sh2 = STATS
    stats = [("94", "%", "Faster Reporting"), ("6.2", "x", "ROI Average"),
             ("120", "+", "Countries Supported"), ("$14", "B", "Annual Transactions")]
    cells = grid([sx + 70, sy + 50, sw - 140, 120], cols=4, count=4, gap=0)
    for i, (box, (num, unit, label)) in enumerate(zip(cells, stats)):
        layer.text([box[0], box[1], 200, 64], num, style="statNum")
        nw = tw(num, 58, 700)
        layer.text([box[0] + nw + 4, box[1] + 4, 40, 24], unit, style="statUnit")
        layer.text([box[0] + 2, box[1] + 82, box[2], 20], label, style="statLbl")
        if i < 3:
            layer.line([box[0] + box[2] - 8, box[1] + 6], [box[0] + box[2] - 8, box[1] + 70],
                       stroke="hair2", stroke_style={"stroke_width": 1})

    # ---- 6. INTEGRATION --------------------------------------------------- #
    ix, iy, iw, ih = INTEG
    layer.rect(INTEG, fill=lg([ix, iy], [ix + iw, iy + ih], [(0, "#161619"), (1, "#0B0B0E")]),
               radius=24, **effects(shadow=shadow(dy=16, blur=44, color="#000000", opacity=0.25)))
    pill_dark(layer, W / 2, iy + 42, "INTEGRATION")
    layer.text([ix + 120, iy + 78, iw - 240, 90],
               "Integrates with your\nexisting finance stack", style="integHead")
    tiles = [
        (ix + 250, iy + 330, _g_grid, "#111111", False),
        (ix + 360, iy + 250, _g_chat, "#E01E5A", True),
        (ix + 470, iy + 330, _g_spark, "#F2C94C", False),
        (ix + 470, iy + 210, _g_blob, "#5B5BD6", True),
        (ix + 600, iy + 290, _g_ring, "#6E56CF", False),
        (ix + 700, iy + 360, _g_play, "#10A37F", True),
        (ix + 760, iy + 240, _g_hex, "#2DA44E", False),
        (ix + 880, iy + 300, _g_grid, "#0EA5E9", False),
        (ix + 980, iy + 230, _g_spark, "#F2542D", True),
        (ix + 1010, iy + 350, _g_blob, "#0061FF", False),
        (ix + 1110, iy + 290, _g_cam, "#2D8CFF", False),
        (ix + 850, iy + 390, _g_chat, "#7C3AED", False),
    ]
    # faint connectors between consecutive tiles
    for a, b in zip(tiles, tiles[1:]):
        layer.line([a[0], a[1]], [b[0], b[1]], stroke=rgba("#FFFFFF", 0.10),
                   stroke_style={"stroke_width": 1}, decorative=True)
    for cx, cy, g, col, glow in tiles:
        app_tile(layer, cx, cy, g, col, glow=glow)

    # ---- 7. PRICING ------------------------------------------------------- #
    section_pill(layer, W / 2, PRICE_PILL, "PRICING")
    layer.text([220, PRICE_H1, 1000, 96],
               "Flexible plans for growing\nfinance teams", style="h2")
    cardw, gap = 408, 28
    x0 = (W - (cardw * 2 + gap)) / 2
    pricing_card(layer, [x0, PRICE_CARDS_Y, cardw, 376], "Starter", "$29", "/mo",
                 ["AI forecasting", "Expense tracking", "Up to 5 users"])
    pricing_card(layer, [x0 + cardw + gap, PRICE_CARDS_Y, cardw, 376], "Enterprise", "$99", "/mo",
                 ["Custom infrastructure", "Dedicated support", "Advanced security"],
                 highlight=True)

    # ---- 8. CTA ----------------------------------------------------------- #
    cx0, cy0, cw, ch = CTA
    panel(layer, CTA, radius=24, sh=True, border="hair")
    corner_tiles(layer, cx0 + 40, cy0 + ch - 130, "pink", flip=1)
    corner_tiles(layer, cx0 + cw - 40, cy0 + ch - 130, "yellow", flip=-1)
    layer.text([cx0 + 120, cy0 + 110, cw - 240, 56], "Smarter treasury starts here", style="ctaH")
    layer.text([cx0 + 220, cy0 + 178, cw - 440, 48],
               "Join modern finance teams using AI to simplify\ntreasury and spending operations.",
               style="ctaSub")
    bw2 = dbw("Start Free Trial")
    dark_button(layer, cx0 + (cw - bw2) / 2, cy0 + 256, "Start Free Trial", h=48)

    return doc


def dbw(label, h=46):
    return 24 + tw(label, 14, 600) + 14 + 26 + 16


def dark_button(layer, x, y, label, *, h=46):
    lw = tw(label, 14, 600)
    w = dbw(label, h)
    layer.rect([x, y, w, h], fill="btn", radius=10)
    layer.text([x + 22, y + (h - 18) / 2, lw + 12, 18], label, style="navbtn")
    acx, acy = x + 22 + lw + 20, y + h / 2
    layer.ellipse([acx, acy], 13, 13, fill="white")
    layer.line([acx - 5, acy], [acx + 5, acy], stroke="btn",
               stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})
    layer.line([acx + 1, acy - 4], [acx + 5, acy], stroke="btn",
               stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})
    layer.line([acx + 1, acy + 4], [acx + 5, acy], stroke="btn",
               stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})
    return w


def section_pill(layer, cx, y, label, *, dark=False):
    lw = tw(label, 12, 700)
    w = lw + 52
    x = cx - w / 2
    layer.rect([x, y, w, 30], fill="white", radius=15, stroke="hair2",
               stroke_style={"stroke_width": 1})
    layer.ellipse([x + 22, y + 15], 4, 4, fill="pink")
    layer.text([x + 34, y + 9, w - 40, 16], label, style="pill")


def pill_dark(layer, cx, y, label):
    lw = tw(label, 12, 700)
    w = lw + 52
    x = cx - w / 2
    layer.rect([x, y - 15, w, 30], fill="darkpill", radius=15)
    layer.ellipse([x + 22, y], 4, 4, fill="pink")
    layer.text([x + 34, y - 6, w - 40, 16], label, style="pillD")


def main() -> int:
    out = os.path.join(ROOT, "static", "examples", "fixtures", "spendora-landing.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warns)} -> {out}")
    for i in errors[:20]:
        print(f"  [ERROR] [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:6]:
        print(f"  [warn] [{i.rule_id}] {i.path}: {i.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
