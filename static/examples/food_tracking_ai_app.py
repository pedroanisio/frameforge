#!/usr/bin/env python3
"""High-fidelity vector recreation of the Dribbble shot
"Food Tracking Mobile App UI with AI Scan" (by Nixtio) using the FrameForge SDK.

Three phone mock-ups sit on a warm taupe stage:

  1. Dashboard   — calorie gauge (capsule "teeth"), two meal cards, tab bar.
  2. AI Scan     — vegetable hero image with floating kcal badges, headline,
                   pager dots and a dark "Get Started" CTA (onboarding card).
  3. Recipes     — search bar, category chips, a "Trending Recipes" card with a
                   quinoa veggie bowl, difficulty meter and tab bar.

Everything is built from SDK primitives (rect / ellipse / polygon / polyline /
path / line / text), gradients and round-cap "capsule" strokes. Food photos are
recreated as stylised vector illustrations.

Run from the repository root::

    uv run python examples/food_tracking_ai_app.py
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
    radial_gradient,
    rgba,
    stroke,
)
from frameforge.sdk.paint import effects, shadow  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas + palette
# --------------------------------------------------------------------------- #
W, H = 1500, 900

COLORS = {
    "stage":    "#C6BBAC",   # warm taupe background
    "stage2":   "#BFB3A2",
    "ink":      "#211D17",   # near-black warm
    "ink2":     "#2C2820",
    "muted":    "#9C9384",   # warm gray text
    "muted2":   "#B7AE9F",
    "hair":     "#E7E0D4",   # hairline dividers
    "cream":    "#F5F1E9",   # phone screen background
    "card":     "#FFFFFF",
    "cardsoft": "#FBF8F2",
    "chip":     "#FFFFFF",
    "orange":   "#E98C5D",   # primary accent
    "orangeDk": "#DC7642",
    "orangeLt": "#F4AE86",
    "orangeWash": "#F7E3D4",
    "nav":      "#191710",   # dark tab bar / CTA
    "navtext":  "#F5F1E9",
    "green":    "#7FA85A",
    "greenDk":  "#4E7A37",
    "greenLt":  "#A9CC7E",
    "tomato":   "#D6492F",
    "purple":   "#7E5285",
    "white":    "#FFFFFF",
}

SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]


def _ts(size, weight=500, color="ink", align="left", ls=0.0, lh=1.3):
    return dict(font_family=SANS, font_size=size, font_weight=weight,
                color=color, align=align, letter_spacing=ls, line_height=lh)


STYLES = {
    "navTitle":  _ts(19, 800, "ink", "center", -0.3),
    "kcalBig":   _ts(30, 800, "ink", "center", -0.6),
    "kcalDate":  _ts(13, 600, "muted", "center"),
    "kcalGoal":  _ts(13, 700, "orange", "center"),
    "cardTitle": _ts(17, 700, "ink", "left", -0.2),
    "cardSub":   _ts(12, 500, "muted", "left"),
    "kcalR":     _ts(17, 800, "ink", "right", -0.2),
    "pctR":      _ts(12, 700, "orange", "right"),
    "macro":     _ts(11, 600, "muted", "left"),
    "macroV":    _ts(11, 700, "ink", "left"),
    "plus":      _ts(22, 500, "muted", "center"),
    "h1":        _ts(31, 800, "ink", "left", -0.8, 1.08),
    "sub":       _ts(14, 500, "muted", "left", 0, 1.45),
    "btn":       _ts(16, 700, "navtext", "center", 0.2),
    "badgePill": _ts(12, 800, "ink", "center", -0.2),
    "search":    _ts(14, 500, "muted2", "left"),
    "chipLbl":   _ts(12, 600, "ink", "center"),
    "section":   _ts(18, 800, "ink", "left", -0.3),
    "see":       _ts(13, 600, "muted", "right"),
    "cnt":       _ts(11, 800, "white", "center"),
    "time":      _ts(12, 600, "muted", "left"),
    "easy":      _ts(12, 700, "ink", "left"),
    "kcalCard":  _ts(17, 800, "ink", "right", -0.2),
}

HALF = "#00000000"


# --------------------------------------------------------------------------- #
# Small geometry / paint helpers
# --------------------------------------------------------------------------- #
def lg(p0, p1, stops):
    """Linear gradient by angle from two points (screen coords)."""
    ang = round(math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])), 1)
    return linear_gradient([(c, pos) for pos, c in stops], angle=ang)


def rg(center, stops, shape="circle"):
    return radial_gradient([(c, pos) for pos, c in stops], at=center, shape=shape)


def capsule(page, x1, y1, x2, y2, w, color):
    page.line([x1, y1], [x2, y2], stroke=color,
              stroke_style={"stroke_width": w, "stroke_linecap": "round"})


def star(page, cx, cy, r, fill, rot=-90.0):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.42
        a = math.radians(rot + i * 36)
        pts.append([cx + rad * math.cos(a), cy + rad * math.sin(a)])
    page.polygon(pts, fill=fill)


def soft_card(page, box, *, radius, fill="card", sh=True):
    if sh:
        page.rect(box, fill=fill, radius=radius,
                  **effects(shadow=shadow(dy=8, blur=22, color="#6E5B3E", opacity=0.10)))
    else:
        page.rect(box, fill=fill, radius=radius)


# --------------------------------------------------------------------------- #
# Line-art icons (drawn, not glyphs, for fidelity)
# --------------------------------------------------------------------------- #
def ic_calendar(page, x, y, s=20, color="ink"):
    page.rect([x, y + s * 0.12, s, s * 0.82], fill="none", stroke=color,
              stroke_style={"stroke_width": 1.8}, radius=4)
    page.line([x, y + s * 0.40], [x + s, y + s * 0.40], stroke=color,
              stroke_style={"stroke_width": 1.8})
    page.line([x + s * 0.28, y], [x + s * 0.28, y + s * 0.22], stroke=color,
              stroke_style={"stroke_width": 2.0, "stroke_linecap": "round"})
    page.line([x + s * 0.72, y], [x + s * 0.72, y + s * 0.22], stroke=color,
              stroke_style={"stroke_width": 2.0, "stroke_linecap": "round"})


def ic_bell(page, cx, cy, s=11, color="ink"):
    page.path(
        f"M {cx-s*0.8} {cy+s*0.55} "
        f"C {cx-s*0.8} {cy-s*0.2} {cx-s*0.55} {cy-s*0.9} {cx} {cy-s*0.9} "
        f"C {cx+s*0.55} {cy-s*0.9} {cx+s*0.8} {cy-s*0.2} {cx+s*0.8} {cy+s*0.55} Z",
        fill="none", **stroke(1.8, color=color, join="round", cap="round"))
    page.line([cx - s * 1.05, cy + s * 0.55], [cx + s * 1.05, cy + s * 0.55],
              stroke=color, stroke_style={"stroke_width": 1.8, "stroke_linecap": "round"})
    page.ellipse([cx, cy + s * 0.95], s * 0.22, s * 0.22, fill=color)


def ic_search(page, cx, cy, r=8, color="muted2"):
    page.ellipse([cx, cy], r, r, fill="none", stroke=color,
                 stroke_style={"stroke_width": 2.0})
    a = math.radians(45)
    page.line([cx + r * math.cos(a), cy + r * math.sin(a)],
              [cx + (r + 6) * math.cos(a), cy + (r + 6) * math.sin(a)],
              stroke=color, stroke_style={"stroke_width": 2.0, "stroke_linecap": "round"})


def ic_pencil(page, x, y, s=15, color="orange"):
    page.polygon([[x, y + s], [x + s * 0.22, y + s * 0.78],
                  [x + s * 0.95, y + s * 0.05], [x + s * 0.73, y - s * 0.17]],
                 fill="none", stroke=color,
                 stroke_style={"stroke_width": 1.8, "stroke_linejoin": "round"})
    page.line([x + s * 0.62, y - s * 0.06], [x + s * 0.84, y + s * 0.16],
              stroke=color, stroke_style={"stroke_width": 1.8})


def ic_clock(page, cx, cy, r=7, color="muted"):
    page.ellipse([cx, cy], r, r, fill="none", stroke=color,
                 stroke_style={"stroke_width": 1.6})
    page.line([cx, cy], [cx, cy - r * 0.55], stroke=color,
              stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})
    page.line([cx, cy], [cx + r * 0.45, cy], stroke=color,
              stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})


# nav glyphs ----------------------------------------------------------------- #
def nv_home(page, cx, cy, color):
    page.polygon([[cx - 9, cy + 1], [cx, cy - 8], [cx + 9, cy + 1]],
                 fill="none", stroke=color,
                 stroke_style={"stroke_width": 1.9, "stroke_linejoin": "round"})
    page.rect([cx - 6, cy + 1, 12, 9], fill="none", stroke=color,
              stroke_style={"stroke_width": 1.9, "stroke_linejoin": "round"}, radius=1.5)


def nv_book(page, cx, cy, color):
    page.rect([cx - 8, cy - 8, 16, 16], fill="none", stroke=color,
              stroke_style={"stroke_width": 1.9, "stroke_linejoin": "round"}, radius=3)
    page.line([cx, cy - 8], [cx, cy + 8], stroke=color,
              stroke_style={"stroke_width": 1.9})


def nv_scan(page, cx, cy, color):
    for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        page.path(
            f"M {cx + sx*9 - sx*5} {cy + sy*9} L {cx + sx*9} {cy + sy*9} L {cx + sx*9} {cy + sy*9 - sy*5}",
            fill="none", **stroke(2.0, color=color, cap="round", join="round"))
    page.line([cx - 9, cy], [cx + 9, cy], stroke=color,
              stroke_style={"stroke_width": 2.0, "stroke_linecap": "round"})


def nv_star(page, cx, cy, color):
    page.polygon(_star_pts(cx, cy, 9), fill="none", stroke=color,
                 stroke_style={"stroke_width": 1.8, "stroke_linejoin": "round"})


def nv_gear(page, cx, cy, color):
    page.ellipse([cx, cy], 5.5, 5.5, fill="none", stroke=color,
                 stroke_style={"stroke_width": 1.9})
    for i in range(8):
        a = math.radians(i * 45)
        page.line([cx + 6.5 * math.cos(a), cy + 6.5 * math.sin(a)],
                  [cx + 9 * math.cos(a), cy + 9 * math.sin(a)],
                  stroke=color, stroke_style={"stroke_width": 1.9, "stroke_linecap": "round"})


def _star_pts(cx, cy, r, rot=-90.0):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.42
        a = math.radians(rot + i * 36)
        pts.append([cx + rad * math.cos(a), cy + rad * math.sin(a)])
    return pts


# --------------------------------------------------------------------------- #
# Food illustrations
# --------------------------------------------------------------------------- #
def food_thumb(page, cx, cy, r, kind="lunch"):
    """Small circular meal photo for the dashboard cards."""
    page.ellipse([cx, cy], r, r, fill=lg([cx - r, cy - r], [cx + r, cy + r],
                 [(0, "#F0E4CE"), (1, "#E4C79C")]))
    page.ellipse([cx, cy], r * 0.86, r * 0.86, fill="#EAD6AE")  # grain base
    if kind == "lunch":
        page.ellipse([cx - r * 0.30, cy - r * 0.20], r * 0.40, r * 0.30, fill="#83A94F")
        page.ellipse([cx + r * 0.32, cy - r * 0.05], r * 0.26, r * 0.24, fill="#CF4A30")
        page.ellipse([cx + r * 0.05, cy + r * 0.35], r * 0.30, r * 0.22, fill="#C57A38")
        page.ellipse([cx - r * 0.38, cy + r * 0.30], r * 0.18, r * 0.16, fill="#6E4326")
    else:  # breakfast
        page.ellipse([cx - r * 0.18, cy - r * 0.10], r * 0.34, r * 0.34, fill="#F6E7A8")
        page.ellipse([cx - r * 0.18, cy - r * 0.10], r * 0.15, r * 0.15, fill="#F2A93C")
        page.ellipse([cx + r * 0.34, cy + r * 0.18], r * 0.24, r * 0.20, fill="#C0402C")
        page.ellipse([cx - r * 0.30, cy + r * 0.34], r * 0.22, r * 0.16, fill="#7FA64C")
    page.ellipse([cx - r * 0.42, cy - r * 0.42], r * 0.30, r * 0.18,
                 fill=rgba("#FFFFFF", 0.30), decorative=True)


def citrus(page, cx, cy, r, peel, flesh, flesh_dk, segs=10):
    """A halved-citrus slice (orange / grapefruit)."""
    page.ellipse([cx, cy], r, r, fill=peel)
    page.ellipse([cx, cy], r * 0.90, r * 0.90, fill="#FFFFFF")
    page.ellipse([cx, cy], r * 0.82, r * 0.82, fill=flesh)
    for i in range(segs):
        a = math.radians(i * 360 / segs)
        page.line([cx, cy], [cx + r * 0.80 * math.cos(a), cy + r * 0.80 * math.sin(a)],
                  stroke="#FFFFFF", stroke_style={"stroke_width": 2.4, "stroke_linecap": "round"})
    for i in range(segs):
        a = math.radians((i + 0.5) * 360 / segs)
        page.ellipse([cx + r * 0.45 * math.cos(a), cy + r * 0.45 * math.sin(a)],
                     r * 0.10, r * 0.16, fill=flesh_dk, decorative=True)
    page.ellipse([cx, cy], r * 0.12, r * 0.12, fill="#FFF7E6")
    page.ellipse([cx - r * 0.34, cy - r * 0.40], r * 0.22, r * 0.12,
                 fill=rgba("#FFFFFF", 0.45), decorative=True)


def broccoli(page, cx, cy, s):
    page.polygon([[cx - s * 0.18, cy], [cx + s * 0.18, cy],
                  [cx + s * 0.12, cy + s * 0.9], [cx - s * 0.12, cy + s * 0.9]],
                 fill="#9CB86A")
    for dx, dy, rr in [(-0.5, -0.5, 0.42), (0.1, -0.7, 0.46), (0.6, -0.4, 0.40),
                       (-0.2, -0.2, 0.40), (0.4, -0.05, 0.36), (-0.55, -0.05, 0.34)]:
        page.ellipse([cx + dx * s, cy + dy * s], rr * s, rr * s, fill="#4E7A37")
    for dx, dy, rr in [(-0.5, -0.5, 0.42), (0.1, -0.7, 0.46), (0.6, -0.4, 0.40),
                       (-0.2, -0.2, 0.40)]:
        page.ellipse([cx + dx * s - rr * s * 0.3, cy + dy * s - rr * s * 0.3],
                     rr * s * 0.45, rr * s * 0.45, fill="#69995088", decorative=True)


def cabbage(page, cx, cy, r):
    page.ellipse([cx, cy], r, r * 0.96, fill=lg([cx - r, cy - r], [cx + r, cy + r],
                 [(0, "#B7D88A"), (0.6, "#86B257"), (1, "#5C8C3C")]))
    for d in [
        f"M {cx-r*0.8} {cy-r*0.1} C {cx-r*0.3} {cy-r*0.7} {cx+r*0.3} {cy-r*0.7} {cx+r*0.8} {cy-r*0.1}",
        f"M {cx-r*0.7} {cy+r*0.3} C {cx-r*0.2} {cy-r*0.2} {cx+r*0.2} {cy-r*0.2} {cx+r*0.7} {cy+r*0.3}",
        f"M {cx-r*0.5} {cy+r*0.6} C {cx-r*0.15} {cy+r*0.2} {cx+r*0.15} {cy+r*0.2} {cx+r*0.5} {cy+r*0.6}",
    ]:
        page.path(d, fill="none", **stroke(2.2, color=rgba("#3F6B2B", 0.7), cap="round"))
    page.ellipse([cx, cy + r * 0.05], r * 0.34, r * 0.30, fill="#C9E29B")
    page.ellipse([cx - r * 0.35, cy - r * 0.42], r * 0.30, r * 0.16,
                 fill=rgba("#FFFFFF", 0.35), decorative=True)


def veggie_bowl(page, cx, cy, r):
    """Quinoa veggie bowl hero for the recipe card."""
    page.ellipse([cx, cy + r * 0.06], r * 1.02, r * 1.02,
                 fill=rgba("#C9B68C", 0.35), decorative=True)             # plate halo
    page.ellipse([cx, cy], r, r, fill="#FFFFFF")                          # plate
    page.ellipse([cx, cy], r * 0.92, r * 0.92,
                 fill=lg([cx, cy - r], [cx, cy + r], [(0, "#EFE7D6"), (1, "#DACDB4")]))
    page.ellipse([cx, cy], r * 0.80, r * 0.80,
                 fill=lg([cx, cy - r], [cx, cy + r], [(0, "#E2CFA2"), (1, "#CBB17C")]))  # quinoa
    # speckle the quinoa
    spk = [(-0.4, -0.3), (-0.1, 0.4), (0.3, 0.1), (0.45, -0.35), (-0.5, 0.15),
           (0.0, -0.5), (0.2, 0.5), (-0.25, -0.05), (0.5, 0.3), (-0.35, 0.45)]
    for dx, dy in spk:
        page.ellipse([cx + dx * r * 0.7, cy + dy * r * 0.7], r * 0.05, r * 0.05,
                     fill=rgba("#A98A52", 0.65), decorative=True)
    # topping clusters arranged around the bowl
    page.ellipse([cx - r * 0.34, cy - r * 0.30], r * 0.20, r * 0.20, fill="#C9402B")   # tomato
    page.ellipse([cx - r * 0.10, cy - r * 0.40], r * 0.17, r * 0.17, fill="#D84B33")
    page.ellipse([cx - r * 0.40, cy + r * 0.18], r * 0.16, r * 0.16, fill="#7E5285")   # red cabbage
    page.ellipse([cx - r * 0.20, cy + r * 0.30], r * 0.15, r * 0.15, fill="#8C5C92")
    # avocado fan
    for k in range(4):
        ax = cx + r * 0.18 + k * r * 0.11
        page.ellipse([ax, cy + r * 0.10 - k * r * 0.04], r * 0.09, r * 0.20, fill="#83A94F")
        page.ellipse([ax, cy + r * 0.10 - k * r * 0.04], r * 0.05, r * 0.16, fill="#A7C972")
    # chickpeas
    for dx, dy in [(0.30, -0.32), (0.45, -0.18), (0.18, -0.40)]:
        page.ellipse([cx + dx * r, cy + dy * r], r * 0.09, r * 0.08, fill="#D8B86A")
    # parsley flecks
    for dx, dy in [(0.0, 0.45), (-0.05, -0.1), (0.35, 0.35), (-0.3, -0.05)]:
        page.ellipse([cx + dx * r, cy + dy * r], r * 0.05, r * 0.05, fill="#5C8C3C",
                     decorative=True)
    page.ellipse([cx - r * 0.40, cy - r * 0.46], r * 0.34, r * 0.16,
                 fill=rgba("#FFFFFF", 0.28), decorative=True)


# category chip icons (small, 3D-ish food) ---------------------------------- #
def chip_all(page, cx, cy):
    page.ellipse([cx, cy + 4], 13, 9, fill="#E07B45")                  # bowl
    page.ellipse([cx, cy - 2], 13, 7, fill="#F2D7A0")
    page.ellipse([cx - 5, cy - 4], 4, 4, fill="#CF4A30")
    page.ellipse([cx + 4, cy - 3], 4, 4, fill="#83A94F")
    page.ellipse([cx, cy - 6], 3.5, 3.5, fill="#7E5285")


def chip_vegan(page, cx, cy):
    page.ellipse([cx, cy + 4], 13, 8, fill="#FFFFFF", stroke="#E2D9C8",
                 stroke_style={"stroke_width": 1.2})
    page.ellipse([cx - 4, cy], 6, 5, fill="#6E9D3F")
    page.ellipse([cx + 5, cy + 1], 5, 4, fill="#86B257")
    page.path(f"M {cx-2} {cy-2} C {cx-2} {cy-9} {cx+6} {cy-9} {cx+6} {cy-2} Z",
              fill="#4E7A37")


def chip_protein(page, cx, cy):
    page.rect([cx - 8, cy - 6, 16, 16], fill=lg([cx - 8, cy], [cx + 8, cy],
              [(0, "#F2B23C"), (1, "#D98A1E")]), radius=4)
    page.rect([cx - 6, cy - 9, 12, 4], fill="#B8701A", radius=2)
    page.rect([cx - 5, cy - 2, 10, 7, ], fill="#FBE3B0", radius=2)


def chip_snacks(page, cx, cy):
    page.polygon([[cx - 8, cy - 2], [cx + 8, cy - 2], [cx + 6, cy + 9], [cx - 6, cy + 9]],
                 fill="#D6492F")
    for i, dx in enumerate((-5, -1.5, 2, 5.5)):
        page.rect([cx + dx, cy - 9, 2.6, 9], fill="#F2C84B", radius=1.3)


# --------------------------------------------------------------------------- #
# Phone shell
# --------------------------------------------------------------------------- #
def phone(page, x, y, w, h):
    page.rect([x - 3, y + 8, w + 6, h], fill=rgba("#5A4A30", 0.16), radius=52,
              decorative=True)                                          # cast shadow
    page.rect([x, y, w, h], fill="cream", radius=46,
              stroke=rgba("#FFFFFF", 0.6), stroke_style={"stroke_width": 1.0})
    page.rect([x + w / 2 - 52, y + 16, 104, 28], fill="#13110C", radius=14)  # island


def tab_bar(page, x, y, w):
    """Dark pill nav with five icons; centre = orange scan button."""
    bar = [x + 18, y, w - 36, 60]
    page.rect(bar, fill="nav", radius=30,
              **effects(shadow=shadow(dy=8, blur=20, color="#3A2E18", opacity=0.30)))
    cx0 = bar[0]
    step = bar[2] / 5
    centers = [cx0 + step * (i + 0.5) for i in range(5)]
    cyc = y + 30
    nv_home(page, centers[0], cyc, "navtext")
    nv_book(page, centers[1], cyc, "#8C857A")
    page.rect([centers[2] - 22, cyc - 22, 44, 44], fill=lg(
        [centers[2] - 22, cyc - 22], [centers[2] + 22, cyc + 22],
        [(0, "#F4AE86"), (1, "#DC7642")]), radius=15)
    nv_scan(page, centers[2], cyc, "#FFFFFF")
    nv_star(page, centers[3], cyc, "#8C857A")
    nv_gear(page, centers[4], cyc, "#8C857A")


# --------------------------------------------------------------------------- #
# Phone 1 — Dashboard
# --------------------------------------------------------------------------- #
def screen_dashboard(page, x, y, w, h):
    # top bar
    soft_card(page, [x + 20, y + 58, 44, 44], radius=14, fill="card", sh=False)
    ic_calendar(page, x + 32, y + 70, 20, "ink")
    page.text([x + 70, y + 70, w - 140, 22], "Dashboard", style="navTitle")
    soft_card(page, [x + w - 64, y + 58, 44, 44], radius=22, fill="card", sh=False)
    ic_bell(page, x + w - 42, y + 80, 9, "ink")

    # calorie gauge
    cx, cy = x + w / 2, y + 222
    rin, rout, N = 70, 102, 13
    filled = 8
    for i in range(N):
        a = math.radians(208 - i * (236 / (N - 1)))
        col = "orange" if i < filled else "hair"
        if i < filled:
            t = i / filled
            col = lg([0, 0], [1, 0], [(0, "#F4AE86"), (1, "#DC7642")])
            capsule(page, cx + rin * math.cos(a), cy - rin * math.sin(a),
                    cx + rout * math.cos(a), cy - rout * math.sin(a), 15,
                    "#E98C5D" if t < 0.5 else "#DC7642")
        else:
            capsule(page, cx + rin * math.cos(a), cy - rin * math.sin(a),
                    cx + rout * math.cos(a), cy - rout * math.sin(a), 15, "#E5DED1")
    page.text([cx - 80, y + 168, 160, 16], "20 Aug", style="kcalDate")
    page.text([cx - 100, y + 188, 200, 34], "1250 kcal", style="kcalBig")
    page.text([cx - 90, y + 226, 180, 16], "Goal 2000 kcal", style="kcalGoal")

    # add-meal divider button
    page.rect([x + 22, y + 300, w - 44, 42], fill="cardsoft", radius=21,
              stroke="hair", stroke_style={"stroke_width": 1.0})
    page.text([x + w / 2 - 12, y + 308, 24, 26], "+", style="plus")

    # meal cards
    for idx, (kind, title, time, kcal, pct, macros) in enumerate([
        ("lunch", "Lunch", "02:30 PM", "693 kcal", "35% of goal",
         [("Protein", "48g"), ("Carbs", "83g"), ("Fat", "25g")]),
        ("breakfast", "Breakfast", "11:30 AM", "500 kcal", "25% of goal",
         [("Protein", "36g"), ("Carbs", "57g"), ("Fat", "14g")]),
    ]):
        cyTop = y + 360 + idx * 132
        soft_card(page, [x + 16, cyTop, w - 32, 120], radius=22, fill="card")
        food_thumb(page, x + 16 + 28 + 12, cyTop + 38, 28, kind)
        page.text([x + 86, cyTop + 22, 150, 20], title, style="cardTitle")
        page.text([x + 86, cyTop + 44, 150, 16], time, style="cardSub")
        page.text([x + w - 150, cyTop + 21, 134, 20], kcal, style="kcalR")
        page.text([x + w - 150, cyTop + 44, 134, 16], pct, style="pctR")
        page.line([x + 28, cyTop + 78], [x + w - 28, cyTop + 78],
                  stroke="hair", stroke_style={"stroke_width": 1.0})
        mx = x + 30
        for label, val in macros:
            page.ellipse([mx + 3, cyTop + 96, ], 3, 3, fill="orange")
            page.text([mx + 12, cyTop + 89, 60, 14], label, style="macro")
            page.text([mx + 12, cyTop + 100, 60, 14], val, style="macroV")
            mx += 86
        ic_pencil(page, x + w - 44, cyTop + 92, 14, "orange")

    tab_bar(page, x, y + h - 86, w)


# --------------------------------------------------------------------------- #
# Phone 2 — AI Scan / onboarding
# --------------------------------------------------------------------------- #
def screen_aiscan(page, x, y, w, h):
    img = [x + 16, y + 56, w - 32, 432]
    page.rect(img, fill=lg([img[0], img[1]], [img[0] + img[2], img[1] + img[3]],
              [(0, "#EBD9BC"), (0.5, "#DDC8A4"), (1, "#C9AE83")]), radius=30)
    ix, iy, iw, ih = img
    midx, midy = ix + iw / 2, iy + ih / 2
    # vegetables
    broccoli(page, ix + iw * 0.74, iy + ih * 0.28, 56)
    cabbage(page, ix + iw * 0.40, midy - 18, 96)
    citrus(page, ix + iw * 0.62, iy + ih * 0.74, 78, "#E98A2E", "#F6B24A", "#E07C1E", 11)
    citrus(page, ix + iw * 0.24, iy + ih * 0.80, 56, "#E68C5A", "#F2A6A0", "#E06E76", 10)
    page.ellipse([ix + iw * 0.86, iy + ih * 0.66], 30, 22, fill="#C7DD8E")  # lime wedge hint
    page.ellipse([ix + iw * 0.12, iy + ih * 0.30], 26, 20, fill="#9CC065", decorative=True)

    # floating kcal badges with connector dots
    for bx, by, label, dot in [
        (ix + iw * 0.10, iy + ih * 0.16, "170 kkal", (ix + iw * 0.30, iy + ih * 0.34)),
        (ix + iw * 0.66, iy + ih * 0.12, "110 kkal", (ix + iw * 0.74, iy + ih * 0.30)),
        (ix + iw * 0.40, iy + ih * 0.50, "90 kkal", (ix + iw * 0.55, iy + ih * 0.62)),
    ]:
        pw = 94
        page.line([bx + pw / 2, by + 15], list(dot), stroke=rgba("#FFFFFF", 0.85),
                  stroke_style={"stroke_width": 1.6})
        page.ellipse(list(dot), 4, 4, fill="#FFFFFF")
        page.rect([bx, by, pw, 30], fill="#FFFFFF", radius=15,
                  **effects(shadow=shadow(dy=3, blur=8, color="#5A4A30", opacity=0.20)))
        page.ellipse([bx + 16, by + 15], 5, 5, fill="orange")
        page.text([bx + 24, by + 8, pw - 30, 16], label, style="badgePill")

    # headline + sub
    page.text([x + 28, y + 512, w - 56, 38], "Your Food,", style="h1")
    page.text([x + 28, y + 550, w - 56, 38], "Decoded By AI", style="h1")
    page.text([x + 28, y + 600, w - 64, 48],
              "From scanning to tracking – everything\nhappens automatically.", style="sub")

    # pager dots
    dcx = x + 28
    for i in range(3):
        if i == 1:
            page.rect([dcx, y + 662, 22, 7], fill="ink", radius=3.5)
            dcx += 30
        else:
            page.ellipse([dcx + 3, y + 665], 3.5, 3.5, fill="muted2")
            dcx += 14

    # CTA
    page.rect([x + 24, y + 694, w - 48, 58], fill="nav", radius=29,
              **effects(shadow=shadow(dy=8, blur=18, color="#3A2E18", opacity=0.30)))
    page.text([x + 24, y + 712, w - 48, 22], "Get Started", style="btn")


# --------------------------------------------------------------------------- #
# Phone 3 — Search / Recipes
# --------------------------------------------------------------------------- #
def screen_recipes(page, x, y, w, h):
    # search + bell
    page.rect([x + 16, y + 58, w - 74, 46], fill="card", radius=23,
              stroke="hair", stroke_style={"stroke_width": 1.0})
    ic_search(page, x + 38, y + 81, 8, "muted2")
    page.text([x + 56, y + 73, 120, 18], "Search", style="search")
    soft_card(page, [x + w - 50, y + 58, 44, 44], radius=22, fill="card", sh=False)
    ic_bell(page, x + w - 28, y + 80, 9, "ink")

    # category chips
    chips = [("All", chip_all), ("Vegan", chip_vegan),
             ("Protein", chip_protein), ("Snacks", chip_snacks)]
    gap = 12
    cw = (w - 32 - gap * 3) / 4
    for i, (label, draw) in enumerate(chips):
        cxk = x + 16 + i * (cw + gap)
        soft_card(page, [cxk, y + 122, cw, 66], radius=20, fill="card", sh=(i == 0))
        if i == 0:
            page.rect([cxk, y + 122, cw, 66], fill="none", stroke="orange",
                      stroke_style={"stroke_width": 1.6}, radius=20)
        draw(page, cxk + cw / 2, y + 150)
        page.text([cxk, y + 196, cw, 16], label, style="chipLbl")

    # section header
    page.text([x + 20, y + 230, 200, 22], "Trending Recipes", style="section")
    page.ellipse([x + 188, y + 240], 9, 9, fill="orange")
    page.text([x + 179, y + 233, 18, 16], "8", style="cnt")
    page.text([x + w - 90, y + 232, 74, 18], "See All", style="see")

    # recipe card
    cardTop = y + 258
    soft_card(page, [x + 16, cardTop, w - 32, 362], radius=26, fill="card")
    page.text([x + 32, cardTop + 22, 220, 22], "Quinoa Veggie Bowl", style="cardTitle")
    ic_clock(page, x + 40, cardTop + 58, 7, "muted")
    page.text([x + 54, cardTop + 51, 80, 16], "45 min", style="time")
    page.rect([x + w - 60, cardTop + 18, 32, 32], fill="cardsoft", radius=12)
    star(page, x + w - 44, cardTop + 34, 8, "ink")

    veggie_bowl(page, x + w / 2, cardTop + 184, 96)

    # difficulty + kcal
    page.text([x + 36, cardTop + 312, 60, 18], "Easy", style="easy")
    bx = x + 36
    for i in range(5):
        bh = 5 + i * 2.6
        page.rect([bx, cardTop + 336 - bh, 12, bh],
                  fill="orange" if i < 2 else "hair", radius=2)
        bx += 16
    page.text([x + w - 130, cardTop + 310, 114, 22], "750 kcal", style="kcalCard")

    tab_bar(page, x, y + h - 86, w)


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="Food Tracking Mobile App UI with AI Scan", profile="diagram", lang="en")
    for name, value in COLORS.items():
        doc.define_color(name, value)
    for name, style in STYLES.items():
        doc.define_text_style(name, **style)

    page = doc.page(
        "food_tracking_ai_app",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
    ).layer("stage")
    page.rect([0, 0, W, H], fill=lg([0, 0], [W, H],
              [(0, "#CCC2B4"), (0.5, "#C6BBAC"), (1, "#BCB09E")]))

    page.layer("phones")
    # left, centre (elevated), right
    P1 = (150, 150, 350, 720)
    P2 = (569, 64, 362, 772)
    P3 = (1000, 150, 350, 720)
    for spec in (P1, P2, P3):
        phone(page, *spec)

    page.layer("content")
    screen_dashboard(page, *P1)
    screen_aiscan(page, *P2)
    screen_recipes(page, *P3)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "static", "examples", "fixtures", "food-tracking-ai-app.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(report.issues) - len(errors)} -> {out}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
