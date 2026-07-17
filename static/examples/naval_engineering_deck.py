#!/usr/bin/env python3
"""Demo: author a 30-page naval-engineering deck with the FrameForge Python SDK.

This script is a *demonstration* of the public SDK surface in :mod:`frameforge.sdk`.
It builds a full slide deck on ship design — hull geometry, hydrostatics, stability,
resistance & propulsion, structures and seakeeping — and leans heavily on:

  * the geometry / drawing helpers (``Path``, ``Frame``, ``Scene3D``, ``Vec2``)
    to generate real technical drawings: hull lines, a body plan, a structural
    midship section, a projected 3D hull block, a turning circle and a design spiral;
  * the ``Chart`` helper to lower every data plot (GZ curve, resistance, open-water,
    bending, buckling, roll decay, the wave-response spectrum) — axes, ticks,
    gridlines, smooth series and legends — to FrameForge primitives;
  * the ``layout`` helpers (``row`` / ``grid``) to tile the card and KPI grids; and
  * dozens of governing equations, rendered as Unicode math (page-mode text does
    not typeset inline ``$tex$``, so the deck spells the formulae out in glyphs).

It then validates the document through the authoritative model + repository rule
catalogue, serialises it to ``examples/naval-engineering-deck.fg.yaml`` and can
optionally rasterise every page to SVG with the bundled proxy renderer.

Run from the repository root::

    uv run python examples/naval_engineering_deck.py            # build + validate + write YAML
    uv run python examples/naval_engineering_deck.py --render   # also write per-page SVGs to out/naval/

Everything below goes through the public SDK — pages declare ``coordinate_mode``,
so nothing reaches into the model.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

# Make the SDK importable when run straight from the repo, and undo the
# package/module name clash the SDK tests document.
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
    Scene3D,
    Vec2,
    column,
    grid,
    row,
    serialize,
    theme,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas, palette and the shared style sheet                                   #
# --------------------------------------------------------------------------- #

W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
MARGIN_X = 76

INK = "#0E2436"        # deep navy — dark page background
INK2 = "#14304A"       # divider numeral
STEEL = "#14507A"      # structural blue
HULL = "#1B3A52"
TEAL = "#1FA39B"       # accent
TEALD = "#147F78"
AMBER = "#E0903B"
RED = "#D4574A"
LINE = "#D8E1EC"       # hairline on white
GRID = "#20415E"       # hairline on navy
PANEL = "#F1F5FA"      # card fill on white
PANEL2 = "#E7EEF6"
INKT = "#26405A"       # body text on white
MUTED = "#7C8AA0"
WHITE = "#FFFFFF"
WATER = "#1FA39B"

SANS = ["Inter", "Helvetica Neue", "Arial", "sans-serif"]
SERIF = ["Charter", "Georgia", "Cambria", "serif"]
MONO = ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"]

STYLES = {
    "kicker": {"font_family": SANS, "font_size": 15, "font_weight": 700,
               "color": TEAL, "text_transform": "uppercase", "letter_spacing": 2.4},
    "h1": {"font_family": SERIF, "font_size": 52, "font_weight": 700,
           "color": WHITE, "line_height": 1.05},
    "title": {"font_family": SERIF, "font_size": 33, "font_weight": 700,
              "color": "#21364C", "line_height": 1.08},
    "subtitle": {"font_family": SANS, "font_size": 19, "font_weight": 400,
                 "color": "#A7B4C6", "line_height": 1.3},
    "lede": {"font_family": SANS, "font_size": 17, "font_weight": 400,
             "color": INKT, "line_height": 1.4},
    "body": {"font_family": SANS, "font_size": 14.5, "font_weight": 400,
             "color": INKT, "line_height": 1.42},
    "bodyD": {"font_family": SANS, "font_size": 14, "font_weight": 400,
              "color": "#C7D2E0", "line_height": 1.45},
    "cardh": {"font_family": SANS, "font_size": 15.5, "font_weight": 700,
              "color": "#21364C", "line_height": 1.18},
    "cardb": {"font_family": SANS, "font_size": 13, "font_weight": 400,
              "color": INKT, "line_height": 1.38},
    "statbig": {"font_family": SERIF, "font_size": 44, "font_weight": 700,
                "color": "#21364C", "line_height": 1.0},
    "statlbl": {"font_family": SANS, "font_size": 12.5, "font_weight": 400,
                "color": MUTED, "line_height": 1.3},
    "eq": {"font_family": MONO, "font_size": 21, "font_weight": 500,
           "color": "#13324B", "line_height": 1.25},
    "eqbig": {"font_family": MONO, "font_size": 26, "font_weight": 600,
              "color": TEALD, "line_height": 1.2},
    "eqnote": {"font_family": SANS, "font_size": 12.5, "font_weight": 400,
               "color": MUTED, "line_height": 1.35},
    "source": {"font_family": SANS, "font_size": 10.5, "font_weight": 400,
               "color": MUTED, "line_height": 1.3},
    "pnum": {"font_family": SANS, "font_size": 10.5, "font_weight": 600,
             "color": MUTED, "letter_spacing": 1},
    "axis": {"font_family": SANS, "font_size": 11, "font_weight": 600,
             "color": "#6B7A90", "line_height": 1.1},
    "axisD": {"font_family": SANS, "font_size": 11, "font_weight": 600,
              "color": "#7E93AB", "line_height": 1.1},
    "barval": {"font_family": SANS, "font_size": 13, "font_weight": 700,
               "color": "#21364C", "line_height": 1.0},
    "num": {"font_family": SERIF, "font_size": 20, "font_weight": 700,
            "color": WHITE, "line_height": 1.0},
    "chip": {"font_family": SANS, "font_size": 12.5, "font_weight": 600,
             "color": TEALD, "line_height": 1.15},
    "draw": {"font_family": SANS, "font_size": 11.5, "font_weight": 600,
             "color": STEEL, "line_height": 1.1},
}

SOURCE_LINE = ("Reference: Lewis (ed.), Principles of Naval Architecture; "
               "Lloyd, Seakeeping; Carlton, Marine Propellers & Propulsion — illustrative values")

TOTAL_PAGES = 30
_page_no = 0  # 1-based counter consumed by the chrome helper


# --------------------------------------------------------------------------- #
# Small drawing vocabulary on top of the PageBuilder                           #
# --------------------------------------------------------------------------- #

def new_page(builder: DocumentBuilder, pid: str):
    """A page sized to the deck canvas, in absolute coordinates."""
    return builder.page(pid, canvas=CANVAS, coordinate_mode="absolute").layer("main")


def stroke(width: float, color: str = STEEL, **extra):
    s = {"stroke": color, "stroke_style": {"stroke_width": width, **extra}}
    return s


def hline(layer, x0, x1, y, color=LINE, width=1.0, **extra):
    layer.line([x0, y], [x1, y], **stroke(width, color, **extra))


def vline(layer, x, y0, y1, color=LINE, width=1.0, **extra):
    layer.line([x, y0], [x, y1], **stroke(width, color, **extra))


def dot(layer, cx, cy, r, fill):
    layer.add({"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": fill})


def chrome(builder, kicker, title, *, dark=False):
    """Standard light/dark content frame: background, kicker, title, footer, page no."""
    global _page_no
    _page_no += 1
    n = _page_no
    layer = new_page(builder, f"page-{n:02d}")
    layer.rect([0, 0, W, H], fill=INK if dark else WHITE)
    layer.text([MARGIN_X, 92, W - 2 * MARGIN_X, 26], kicker, style={"class": "kicker"})
    layer.text([MARGIN_X, 122, W - 2 * MARGIN_X, 70], title,
               style={"class": "title", "color": (WHITE if dark else "#21364C")})
    # Accent rule below the title's descenders (the 33px serif title baseline is
    # ~166; a rule at 168 clipped the 'y'/'p' descenders on every content page).
    hline(layer, MARGIN_X, MARGIN_X + 86, 180, TEAL, 3)
    layer.text([1044, 680, 160, 22], f"{n:02d} / {TOTAL_PAGES}",
               style={"class": "pnum", "align": "right"})
    return layer


def footer_source(layer, text=SOURCE_LINE, dark=False):
    layer.text([MARGIN_X, 680, 920, 26], text,
               style={"class": "source", "color": ("#7E93AB" if dark else MUTED)})


def card(layer, box, *, fill=PANEL, radius=14, **extra):
    layer.rect(box, fill=fill, radius=radius, **extra)


def eq_card(layer, x, y, w, h, formula, *, label=None, note=None, accent=TEALD, fill=PANEL):
    """A rounded panel holding one governing equation + an optional caption."""
    card(layer, [x, y, w, h], fill=fill)
    vline(layer, x, y + 12, y + h - 12, accent, 3)
    cy = y + 18
    if label:
        layer.text([x + 22, cy, w - 40, 18], label,
                   style={"class": "kicker", "font_size": 11.5, "color": accent,
                          "letter_spacing": 1.6})
        cy += 24
    layer.text([x + 22, cy, w - 40, 36], formula,
               style={"class": "eqbig", "color": accent})
    cy += 40
    if note:
        layer.text([x + 22, cy, w - 40, h - (cy - y) - 14], note,
                   style={"class": "eqnote"})


# ---- axis-framed data plots (built on the SDK Frame helper) ---------------- #

def plot_panel(layer, box, title, sub, *, fill=PANEL):
    bx, by, bw, bh = box
    card(layer, box, fill=fill)
    layer.text([bx + 24, by + 18, bw - 40, 22], title,
               style={"class": "cardh", "font_size": 14})
    if sub:
        layer.text([bx + 24, by + 42, bw - 40, 18], sub, style={"class": "statlbl"})


def chart_panel(layer, panel_box, title, sub, *, domain, plot):
    """Draw a titled card and return a Chart over a Frame placed inside it.

    The returned Chart accumulates axes/series/legend objects; the caller flushes
    them with ``layer.extend(chart.objects())`` once the figure is composed.
    """
    plot_panel(layer, panel_box, title, sub)
    return Chart(Frame(domain=domain, box=tuple(plot)))


# --------------------------------------------------------------------------- #
# Cover / contents / section dividers                                          #
# --------------------------------------------------------------------------- #

def page_cover(builder):
    global _page_no
    _page_no += 1
    layer = new_page(builder, "cover")
    layer.rect([0, 0, W, H], fill=INK)
    # A blueprint waterline grid in the corner.
    for gx in range(820, 1240, 40):
        vline(layer, gx, 90, 470, GRID, 1)
    for gy in range(90, 470, 40):
        hline(layer, 820, 1240, gy, GRID, 1)
    # Sheer profile sketch drawn over the grid with the Path builder.
    sheer = (Path().move_to(840, 360)
             .through([(900, 330), (1010, 320), (1140, 330), (1210, 352)])
             .line_to(1210, 392).line_to(840, 392).close())
    layer.add(sheer.object(stroke=TEAL, fill="none", stroke_style={"stroke_width": 2.2}))
    hline(layer, 820, 1240, 392, WATER, 1.4)  # design waterline
    for wl in (372, 352, 332):
        hline(layer, 845, 1205, wl, GRID, 1)

    layer.text([MARGIN_X, 250, 520, 24], "Naval architecture · technical primer",
               style={"class": "kicker"})
    layer.text([MARGIN_X, 286, 720, 190],
               "Ship Design from\nFirst Principles",
               style={"class": "h1", "font_size": 60})
    layer.text([MARGIN_X, 486, 760, 30],
               "Hull form, hydrostatics, resistance, structures & seakeeping",
               style={"class": "subtitle"})
    hline(layer, MARGIN_X, MARGIN_X + 120, 556, TEAL, 3)
    layer.text([MARGIN_X, 574, 820, 24],
               "A 30-page worked deck authored entirely through the FrameForge Python SDK",
               style={"class": "source", "color": "#7E93AB"})
    layer.text([1044, 680, 160, 22], f"01 / {TOTAL_PAGES}",
               style={"class": "pnum", "align": "right"})


def page_contents(builder):
    layer = chrome(builder, "How this deck is organised",
                   "Five passes over the design spiral")
    items = [
        ("01", "Hull geometry & form", "Lines plan, body plan, the form coefficients."),
        ("02", "Hydrostatics & stability", "Buoyancy, hydrostatic curves, GM and the GZ righting arm."),
        ("03", "Resistance & propulsion", "Froude scaling, the resistance build-up, propeller open water."),
        ("04", "Structures", "Midship section, longitudinal bending, plate buckling, 3D blocks."),
        ("05", "Seakeeping & maneuvering", "Wave spectra, RAOs, roll period, the turning circle."),
    ]
    for (n, head, sub), rbox in zip(items, column([88, 224, 1128, 5 * 92], 5)):
        y = rbox[1]
        dot(layer, 106, y + 16, 30, INK)
        layer.text([88, y, 36, 34], n, style={"class": "num", "align": "center"})
        layer.text([162, y - 10, 1028, 30], head, style={"class": "cardh", "font_size": 21})
        layer.text([162, y + 24, 1018, 40], sub, style={"class": "body", "color": MUTED})
        if n != "05":
            hline(layer, 162, 1204, y + 56, LINE, 1)


def page_divider(builder, pid, secno, title, subtitle):
    global _page_no
    _page_no += 1
    layer = new_page(builder, pid)
    layer.rect([0, 0, W, H], fill=INK)
    # faint stations behind the numeral
    for gx in range(96, 300, 28):
        vline(layer, gx, 250, 470, GRID, 1)
    layer.text([MARGIN_X, 210, 400, 24], f"Section {secno}", style={"class": "kicker"})
    layer.text([MARGIN_X, 236, 320, 160], secno,
               style={"class": "h1", "font_size": 150, "color": INK2})
    layer.text([326, 300, 760, 120], title,
               style={"class": "h1", "font_size": 44})
    hline(layer, 332, 422, 344, TEAL, 3)
    layer.text([332, 420, 720, 60], subtitle,
               style={"class": "subtitle", "color": "#A7B4C6"})
    layer.text([1044, 680, 160, 22], f"{_page_no:02d} / {TOTAL_PAGES}",
               style={"class": "pnum", "align": "right"})


# --------------------------------------------------------------------------- #
# Section 01 — hull geometry                                                   #
# --------------------------------------------------------------------------- #

# A simple set of hull offsets: half-breadth (m) as a function of waterline
# height (m) at each of several longitudinal stations 0..10 (AP..FP).
def _station_offsets():
    L, Bmax, T, D = 120.0, 9.0, 5.6, 8.0
    stations = []
    for i in range(11):
        xi = i / 10.0
        # fullness peaks amidships, fines toward the ends
        fore_aft = math.sin(math.pi * xi) ** 0.55
        pts = []
        for j in range(9):
            z = D * j / 8.0
            # rounded bilge: half-breadth grows with height then tucks near deck
            rise = math.sin(min(z / T, 1.0) * math.pi / 2)
            bulge = 1.0 - 0.12 * max(0.0, (z - T) / max(D - T, 1e-6))
            b = Bmax * fore_aft * rise * bulge
            pts.append((b, z))
        stations.append((xi, pts))
    return L, Bmax, T, D, stations


def page_lines_plan(builder):
    layer = chrome(builder, "01 · Hull geometry",
                   "The lines plan: profile & half-breadth")
    layer.text([MARGIN_X, 196, 560, 80],
               "Three orthographic projections describe a hull. The sheer plan shows "
               "waterlines and the profile; the half-breadth plan shows the same "
               "waterlines seen from above, folded about the centreline.",
               style={"class": "lede"})

    L, Bmax, T, D, stations = _station_offsets()
    # --- sheer profile (top drawing) ---
    sx0, sx1, sbase, sheer_top = 700, 1180, 312, 232
    plot_panel(layer, [656, 196, 548, 150], "Sheer profile", "Profile & design waterline")
    prof = (Path()
            .move_to(sx0, sbase)
            .through([(sx0 + 70, sheer_top + 24), (sx0 + 240, sheer_top + 10),
                      (sx1 - 90, sheer_top + 16), (sx1, sheer_top + 34)])
            .line_to(sx1, sbase).close())
    layer.add(prof.object(stroke=STEEL, fill="none", stroke_style={"stroke_width": 2.2}))
    hline(layer, sx0, sx1, sbase - 18, WATER, 1.3)            # DWL
    for k in range(1, 4):
        hline(layer, sx0 + 8, sx1 - 8, sbase - 18 + k * 8, LINE, 1)
    for i in range(11):                                       # station ordinates
        x = sx0 + (sx1 - sx0) * i / 10
        vline(layer, x, sheer_top + 6, sbase, LINE, 1)
    layer.text([sx0, 324, 60, 14], "AP", style={"class": "draw"})
    layer.text([sx1 - 24, 324, 60, 14], "FP", style={"class": "draw"})

    # --- half-breadth plan (lower drawing) ---
    plot_panel(layer, [656, 360, 548, 300], "Half-breadth plan",
               "Waterlines folded about the centreline")
    hbx0, hbx1, cl = 700, 1180, 560
    hline(layer, hbx0, hbx1, cl, "#9FB0C2", 1.4)              # centreline
    for wlj in range(1, 6):                                   # waterline curves
        z = D * wlj / 6.0
        pts = []
        for i, (xi, ofs) in enumerate(stations):
            # interpolate half-breadth at this height
            b = _interp_breadth(ofs, z)
            x = hbx0 + (hbx1 - hbx0) * xi
            pts.append([x, cl - b * 4.2])
        layer.add({"type": "polyline", "points": pts, "stroke": TEAL,
                   "stroke_style": {"stroke_width": 1.8}})
    for i in range(11):
        x = hbx0 + (hbx1 - hbx0) * i / 10
        vline(layer, x, cl - 160, cl, LINE, 1)
    footer_source(layer)


def _interp_breadth(offsets, z):
    """Linear interpolation of half-breadth at height z from (b, z) samples."""
    pts = sorted(offsets, key=lambda p: p[1])
    if z <= pts[0][1]:
        return pts[0][0]
    for (b0, z0), (b1, z1) in zip(pts, pts[1:]):
        if z <= z1:
            t = (z - z0) / max(z1 - z0, 1e-9)
            return b0 + t * (b1 - b0)
    return pts[-1][0]


def page_body_plan(builder):
    layer = chrome(builder, "01 · Hull geometry", "The body plan")
    layer.text([MARGIN_X, 196, 470, 110],
               "The body plan stacks every transverse station on one frame: aft "
               "halves to the left of the centreline, forward halves to the right. "
               "Tight curvature at the ends and full, rounded amidship sections are "
               "read at a glance.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 330, 470, 92,
            "A(x) = 2 · ∫₀ᵀ y(x,z) dz",
            label="Sectional area", accent=STEEL,
            note="Each station's immersed area is the integral of its half-breadth "
                 "over draught — the input to the sectional-area curve.")
    eq_card(layer, MARGIN_X, 436, 470, 92,
            "Cₚ = ∇ ⁄ (A_m · L)",
            label="Prismatic coefficient", accent=TEALD,
            note="How the displaced volume is distributed along the length, relative "
                 "to a prism of the midship section.")

    L, Bmax, T, D, stations = _station_offsets()
    # body plan frame on the right
    cx = 880          # centreline
    base = 600        # keel baseline
    sc_b = 11.0       # px per metre breadth
    sc_z = 11.0       # px per metre height
    card(layer, [636, 196, 568, 430], fill=PANEL)
    layer.text([660, 214, 520, 20], "Body plan — transverse sections",
               style={"class": "cardh", "font_size": 14})
    vline(layer, cx, base - D * sc_z - 10, base + 8, "#9FB0C2", 1.4)   # centreline
    hline(layer, cx - Bmax * sc_b - 10, cx + Bmax * sc_b + 10, base, "#9FB0C2", 1.2)  # baseline
    hline(layer, cx - Bmax * sc_b - 10, cx + Bmax * sc_b + 10, base - T * sc_z, WATER, 1.2)  # DWL
    for xi, ofs in stations:
        side = -1 if xi <= 0.5 else 1                      # aft left, fwd right
        col = TEAL if xi <= 0.5 else STEEL
        mapped = [Vec2(cx + side * b * sc_b, base - z * sc_z) for b, z in ofs]
        path = Path().move_to(mapped[0].x, mapped[0].y).through(mapped[1:])
        layer.add(path.object(stroke=col, fill="none", stroke_style={"stroke_width": 1.6}))
    layer.text([cx - 120, base + 12, 110, 14], "AFT  ◂", style={"class": "draw", "align": "right"})
    layer.text([cx + 14, base + 12, 110, 14], "▸  FWD", style={"class": "draw"})
    footer_source(layer)


def page_coefficients(builder):
    layer = chrome(builder, "01 · Hull geometry", "Form coefficients")
    layer.text([MARGIN_X, 196, 1128, 46],
               "Four dimensionless ratios capture hull fullness — they set resistance, "
               "capacity and seakeeping long before any plating is cut.",
               style={"class": "lede"})
    cards = [
        ("C_B = ∇ ⁄ (L·B·T)", "Block", "0.62", STEEL,
         "Displaced volume vs. its bounding box. Fine for fast hulls, full for tankers."),
        ("C_P = ∇ ⁄ (A_m·L)", "Prismatic", "0.66", TEALD,
         "Longitudinal distribution of volume; drives wave-making at speed."),
        ("C_M = A_m ⁄ (B·T)", "Midship", "0.94", AMBER,
         "Fullness of the midship section — bilge radius and rise of floor."),
        ("C_W = A_w ⁄ (L·B)", "Waterplane", "0.78", RED,
         "Fullness of the waterplane; governs BM and transverse stiffness."),
    ]
    for box, (formula, name, val, accent, note) in zip(
            row([MARGIN_X, 272, 1122, 250], 4, gap=22), cards):
        x, y = box[0], box[1]
        card(layer, box)
        layer.text([x + 22, y + 20, 220, 18], name.upper(),
                   style={"class": "kicker", "font_size": 12, "color": accent})
        layer.text([x + 22, y + 46, 220, 52], val,
                   style={"class": "statbig", "font_size": 46, "color": accent})
        hline(layer, x + 22, x + 120, y + 110, LINE, 1)
        layer.text([x + 22, y + 124, 224, 40], formula, style={"class": "eq", "font_size": 15})
        layer.text([x + 22, y + 172, 224, 70], note, style={"class": "cardb"})
    # a tiny "fullness" bar chart comparing the four coefficients
    plot_panel(layer, [MARGIN_X, 540, 1128, 110], "Relative fullness", "")
    vals = [("C_B", 0.62, STEEL), ("C_P", 0.66, TEALD), ("C_M", 0.94, AMBER), ("C_W", 0.78, RED)]
    track_x, track_w = 360, 620
    y = 560
    for name, v, c in vals:
        w = v * track_w
        layer.text([MARGIN_X + 24, y - 1, 80, 16], name, style={"class": "barval"})
        layer.rect([track_x, y, track_w, 12], fill=PANEL2, radius=6)
        layer.rect([track_x, y, w, 12], fill=c, radius=6)
        layer.text([track_x + w + 10, y - 2, 70, 16], f"{v:.2f}",
                   style={"class": "barval", "color": c})
        y += 22
    footer_source(layer)


# --------------------------------------------------------------------------- #
# Section 02 — hydrostatics & stability                                        #
# --------------------------------------------------------------------------- #

def page_archimedes(builder):
    layer = chrome(builder, "02 · Hydrostatics", "Buoyancy & displacement")
    layer.text([MARGIN_X, 196, 540, 110],
               "A floating hull displaces its own weight in water. The buoyant force "
               "acts up through the centroid of the immersed volume — the centre of "
               "buoyancy B — while weight acts down through G.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 330, 540, 96,
            "F_B = ρ · g · ∇  =  Δ · g",
            label="Archimedes", accent=TEALD,
            note="ρ ≈ 1025 kg/m³ for sea water; ∇ is the displaced volume, "
                 "Δ = ρ∇ the displacement mass.")
    eq_card(layer, MARGIN_X, 436, 540, 96,
            "Δ = ρ · L · B · T · C_B",
            label="Displacement from form", accent=STEEL,
            note="For L=120 m, B=18 m, T=5.6 m, C_B=0.62 → Δ ≈ 7.7 kt.")

    # buoyancy free-body drawing
    card(layer, [656, 196, 548, 430])
    layer.text([680, 214, 480, 20], "Free-body of a floating section",
               style={"class": "cardh", "font_size": 14})
    cx, wl = 930, 360
    # water
    layer.rect([700, wl, 460, 230], fill="#E4F3F1", radius=10)
    hline(layer, 700, 1160, wl, WATER, 1.6)
    # hull section (rounded U)
    hull = (Path().move_to(820, wl - 40)
            .line_to(820, wl + 70)
            .through([(860, wl + 120), (cx, wl + 132), (1000, wl + 120)])
            .line_to(1040, wl - 40))
    layer.add(hull.object(stroke=HULL, fill="#FFFFFF", stroke_style={"stroke_width": 2.4}))
    # Weight acts down through G; buoyancy acts up through the centre of buoyancy B.
    # The two lines of action are drawn slightly apart for legibility, but each
    # vector now originates at its own labelled point (B sits at the foot of F_B,
    # not on the weight line).
    bcx = cx - 58
    dot(layer, cx, wl + 8, 4, "#21364C")
    layer.text([cx + 8, wl - 6, 30, 16], "G", style={"class": "draw"})
    layer.arrow([cx, wl + 8], [cx, wl + 100], color="#21364C", width=2.2, head=11)
    layer.text([cx + 10, wl + 82, 80, 16], "W = Δg", style={"class": "draw", "color": "#21364C"})
    dot(layer, bcx, wl + 78, 4, TEALD)
    layer.text([bcx - 34, wl + 70, 30, 16], "B",
               style={"class": "draw", "color": TEALD, "align": "right"})
    layer.arrow([bcx, wl + 78], [bcx, wl - 6], color=TEALD, width=2.2, head=11)
    layer.text([bcx - 150, wl + 30, 130, 16], "F_B = ρg∇",
               style={"class": "draw", "color": TEALD, "align": "right"})
    footer_source(layer)


def page_hydrostatic_curves(builder):
    layer = chrome(builder, "02 · Hydrostatics", "Hydrostatic curves")
    layer.text([MARGIN_X, 196, 470, 140],
               "Sweeping the waterline through a range of draughts produces the "
               "hydrostatic curves: displacement, waterplane area and the height of "
               "the centre of buoyancy, all as functions of draught T.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 350, 470, 80,
            "TPC = A_w · ρ ⁄ 100",
            label="Tonnes per cm immersion", accent=STEEL,
            note="Added immersion per cm of parallel sinkage.")
    eq_card(layer, MARGIN_X, 440, 470, 80,
            "KB ≈ T · (5⁄6 − C_B ⁄ 3C_W)",
            label="Vertical centre of buoyancy", accent=TEALD,
            note="Morrish's approximation for KB at draught T.")

    chart = chart_panel(layer, [636, 196, 568, 430], "Displacement & KB vs draught",
                        "Draught 0–6 m", domain=(0, 0, 6, 8000), plot=[700, 240, 470, 360])
    disp = [(t, min(1025 * 120 * 18 * t * (0.55 + 0.02 * t) / 1000, 8000))
            for t in [x * 0.5 for x in range(0, 13)]]
    kb = [(t, t * (5 / 6 - 0.62 / (3 * 0.78)) * 1000) for t in [x * 0.5 for x in range(0, 13)]]
    chart.axes(x_ticks=[0, 1, 2, 3, 4, 5, 6], y_ticks=[0, 2000, 4000, 6000, 8000],
               x_format=lambda v: f"{v:g}", y_format=lambda v: f"{int(v / 1000)}k", grid=True)
    chart.line(disp, stroke=TEAL, width=2.8, smooth=True, label="Δ (t)")
    chart.line(kb, stroke=AMBER, width=2.4, smooth=True, label="KB ×10³ (m)")
    chart.legend(at=(700, 612))
    layer.extend(chart.objects())
    footer_source(layer)


def page_stability_geometry(builder):
    layer = chrome(builder, "02 · Stability", "Transverse stability: GM")
    layer.text([MARGIN_X, 196, 470, 110],
               "For small heel the metacentre M is fixed. Stability depends on its "
               "height above G — the metacentric height GM. Positive GM gives a "
               "righting couple; negative GM means the hull lols to a heel.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 318, 470, 86,
            "BM = I_T ⁄ ∇",
            label="Metacentric radius", accent=STEEL,
            note="I_T is the transverse second moment of the waterplane area.")
    eq_card(layer, MARGIN_X, 414, 470, 86,
            "GM = KB + BM − KG",
            label="Metacentric height", accent=TEALD,
            note="A practical merchant hull aims for GM ≈ 0.5–1.5 m.")
    eq_card(layer, MARGIN_X, 510, 470, 86,
            "M_R = Δ · g · GM · sinφ",
            label="Righting moment (small φ)", accent=AMBER,
            note="Linear in heel angle φ while M stays fixed.")

    # heeled section showing K, B, M, G, Z
    card(layer, [636, 196, 568, 430])
    layer.text([660, 214, 480, 20], "Metacentric construction (heeled φ ≈ 18°)",
               style={"class": "cardh", "font_size": 14})
    cx, wl = 920, 470
    # waterline (heeled view: rotate the hull, keep water level)
    layer.rect([700, wl, 460, 150], fill="#E4F3F1", radius=8)
    hline(layer, 700, 1160, wl, WATER, 1.4)
    K = Vec2(cx, wl + 92)
    G = Vec2(cx, wl + 18)
    M = Vec2(cx, wl - 120)
    B = Vec2(cx + 46, wl + 40)   # shifted to low side
    for label, p, c in [("K", K, "#21364C"), ("G", G, "#21364C"),
                         ("M", M, RED), ("B", B, TEALD)]:
        dot(layer, p.x, p.y, 4, c)
        layer.text([p.x + 8, p.y - 8, 30, 16], label, style={"class": "draw", "color": c})
    vline(layer, cx, M.y, K.y, "#9FB0C2", 1.2)            # centreline KM
    # vertical through B (line of buoyancy) up to M
    layer.line([B.x, B.y], [M.x, M.y], **stroke(1.8, TEALD))
    # righting arm GZ
    Z = Vec2(G.x + 40, G.y)
    layer.line([G.x, G.y], [Z.x, Z.y], **stroke(2.4, AMBER))
    dot(layer, Z.x, Z.y, 3, AMBER)
    layer.text([Z.x + 6, Z.y - 16, 60, 16], "Z", style={"class": "draw", "color": AMBER})
    layer.text([cx - 30, wl - 150, 160, 16], "GZ = GM·sinφ",
               style={"class": "draw", "color": AMBER})
    footer_source(layer)


def page_gz_curve(builder):
    layer = chrome(builder, "02 · Stability", "The righting-arm (GZ) curve")
    layer.text([MARGIN_X, 196, 470, 120],
               "Beyond small angles GZ is non-linear. The curve's slope at the origin "
               "equals GM; its peak gives the maximum righting arm, and the angle where "
               "it returns to zero is the range of stability.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 336, 470, 84,
            "dGZ ⁄ dφ |₀ = GM",
            label="Initial slope", accent=STEEL,
            note="The GM tangent is drawn at 1 rad (57.3°).")
    eq_card(layer, MARGIN_X, 430, 470, 84,
            "E = Δ·g · ∫ GZ dφ",
            label="Dynamic stability", accent=TEALD,
            note="Area under the curve = energy to capsize.")

    chart = chart_panel(layer, [646, 196, 558, 430], "GZ vs heel angle",
                        "Static stability, ballast condition",
                        domain=(0, -0.1, 80, 0.9), plot=[710, 270, 450, 280])
    # GZ ≈ GM·sin φ corrected by a wall-sided term
    GM = 0.9
    pts = []
    for deg in range(0, 81, 2):
        r = math.radians(deg)
        pts.append((deg, max(GM * math.sin(r) + 0.18 * math.sin(r) ** 3 - 0.0009 * deg, -0.05)))
    peak = max(pts, key=lambda q: q[1])
    chart.axes(x_ticks=[0, 20, 40, 60, 80], y_ticks=[0, 0.2, 0.4, 0.6, 0.8],
               x_format=lambda v: f"{v:g}°", y_format=lambda v: f"{v:.1f}", grid=True)
    chart.line(pts, stroke=TEAL, width=3.0, smooth=True)
    chart.marker(*peak, r=4, fill=RED)
    layer.extend(chart.objects())
    # GM tangent (origin → 57.3°) + annotations, positioned via the chart's frame
    frame = chart.frame
    p0, p1 = frame.point(0, 0), frame.point(57.3, GM)
    layer.line([p0.x, p0.y], [p1.x, p1.y], **stroke(1.4, AMBER, stroke_dasharray=[5, 4]))
    layer.text([p1.x - 70, p1.y - 18, 120, 16], "GM tangent",
               style={"class": "draw", "color": AMBER})
    pp = frame.point(*peak)
    layer.text([pp.x - 40, pp.y - 22, 120, 16], f"GZ_max ≈ {peak[1]:.2f} m",
               style={"class": "draw", "color": RED})
    footer_source(layer)


# --------------------------------------------------------------------------- #
# Section 03 — resistance & propulsion                                         #
# --------------------------------------------------------------------------- #

def page_froude(builder):
    layer = chrome(builder, "03 · Resistance", "Froude scaling & resistance")
    layer.text([MARGIN_X, 196, 1128, 46],
               "Total resistance splits into a viscous (frictional) part that scales "
               "with Reynolds number and a wave-making part that scales with Froude "
               "number. Model tests exploit the split via Froude's hypothesis.",
               style={"class": "lede"})
    eqs = [
        ("Fn = V ⁄ √(g·L)", "Froude number", STEEL,
         "Speed–length ratio; sets the wave pattern. Fn ≈ 0.30 here."),
        ("Re = V·L ⁄ ν", "Reynolds number", TEALD,
         "Inertia vs. viscosity; governs the friction line."),
        ("R_T = ½ ρ S V² C_T", "Total resistance", AMBER,
         "C_T = C_F + C_R, friction plus residuary."),
        ("C_F = 0.075 ⁄ (log₁₀Re − 2)²", "ITTC-57 friction", RED,
         "The model–ship correlation line."),
    ]
    for box, (formula, name, accent, note) in zip(
            row([MARGIN_X, 268, 1122, 200], 4, gap=22), eqs):
        eq_card(layer, box[0], box[1], box[2], box[3], formula,
                label=name, accent=accent, note=note)
    # resistance build-up bar
    plot_panel(layer, [MARGIN_X, 496, 1128, 150], "Resistance build-up at design speed", "")
    comps = [("Friction C_F", 0.55, STEEL), ("Wave C_W", 0.28, TEAL),
             ("Form/visc.", 0.10, AMBER), ("Air & app.", 0.07, RED)]
    x = MARGIN_X + 24
    total_w = 1080
    for name, frac, c in comps:
        w = frac * total_w
        layer.rect([x, 560, w, 30], fill=c, radius=6)
        layer.text([x, 596, max(w, 90), 16], f"{name} · {int(frac*100)}%",
                   style={"class": "statlbl", "font_size": 11})
        x += w + 6
    footer_source(layer)


def page_resistance_curve(builder):
    layer = chrome(builder, "03 · Resistance", "The resistance curve")
    layer.text([MARGIN_X, 196, 470, 130],
               "Plotted against speed, frictional resistance grows smoothly while the "
               "residuary (wave) component climbs steeply through humps and hollows. "
               "Their sum defines the effective-power demand.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 348, 470, 80, "R_T(V) = R_F(V) + R_R(V)",
            label="Component sum", accent=STEEL,
            note="R_F ∝ V^1.825 (friction), R_R rises faster near hull speed.")
    eq_card(layer, MARGIN_X, 438, 470, 80, "P_E = R_T · V",
            label="Effective power", accent=TEALD,
            note="Tow-rope power: what the bare hull demands.")

    chart = chart_panel(layer, [646, 196, 558, 430], "Resistance vs speed",
                        "Bare-hull, calm water", domain=(0, 0, 22, 600),
                        plot=[710, 260, 450, 300])
    Rf = [(v, min(1.2 * v ** 1.825, 600)) for v in range(0, 23)]
    Rr = [(v, min(0.012 * v ** 3.4, 600)) for v in range(0, 23)]
    Rt = [(v, min(1.2 * v ** 1.825 + 0.012 * v ** 3.4, 600)) for v in range(0, 23)]
    chart.axes(x_ticks=[0, 5, 10, 15, 20], y_ticks=[0, 150, 300, 450, 600],
               x_format=lambda v: f"{v:g}", y_format=lambda v: f"{v:g}", grid=True)
    chart.line(Rt, stroke="#21364C", width=3.0, smooth=True, label="R_T")
    chart.line(Rf, stroke=AMBER, width=2.2, smooth=True, label="R_F")
    chart.line(Rr, stroke=TEAL, width=2.2, smooth=True, label="R_R")
    chart.legend(at=(710, 612))
    layer.extend(chart.objects())
    layer.text([1030, 270, 130, 16], "knots  →  kN",
               style={"class": "statlbl", "align": "right"})
    footer_source(layer)


def page_waves(builder):
    layer = chrome(builder, "03 · Resistance", "The Kelvin wake & wave-making")
    layer.text([MARGIN_X, 196, 470, 130],
               "A moving hull radiates a steady wave pattern bounded by the Kelvin "
               "half-angle of 19.47°, independent of speed in deep water. Transverse "
               "and diverging wave systems interfere along the hull.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 350, 470, 78, "c = √(g·λ ⁄ 2π)",
            label="Deep-water celerity", accent=TEALD,
            note="Longer waves travel faster — the basis of dispersion.")
    eq_card(layer, MARGIN_X, 440, 470, 78, "2α_K = 2·arcsin(1⁄3) ≈ 39°",
            label="Kelvin wedge", accent=STEEL,
            note="Total opening angle of the wake, speed-independent.")

    # Kelvin wake drawing
    card(layer, [636, 196, 568, 430])
    layer.text([660, 214, 480, 20], "Kelvin wave pattern (plan view)",
               style={"class": "cardh", "font_size": 14})
    bow = Vec2(700, 410)
    stern = Vec2(1170, 410)
    hline(layer, bow.x, stern.x, 410, "#9FB0C2", 1.0)        # track
    # diverging cusp lines at ±19.47°
    ang = math.radians(19.47)
    for s in (-1, 1):
        ex = stern.x
        ey = stern.y + s * (stern.x - bow.x) * math.tan(ang)
        layer.line([bow.x, bow.y], [ex, ey], **stroke(1.4, STEEL, stroke_dasharray=[6, 4]))
    # transverse crests (arcs) behind the hull, via Path quad curves
    for k in range(1, 7):
        cxk = bow.x + k * 62
        amp = k * 13
        crest = (Path().move_to(cxk, 410 - amp)
                 .quad_to((cxk - 30, 410), (cxk, 410 + amp)))
        layer.add(crest.object(stroke=TEAL, fill="none", stroke_style={"stroke_width": 1.6}))
    # hull marker
    layer.add({"type": "polyline", "closed": True,
               "points": [[bow.x - 26, 404], [bow.x + 8, 410], [bow.x - 26, 416]],
               "fill": HULL})
    layer.text([1010, 360, 150, 16], "19.5° half-angle", style={"class": "draw"})
    footer_source(layer)


def page_speed_power(builder):
    layer = chrome(builder, "03 · Propulsion", "The powering chain")
    layer.text([MARGIN_X, 196, 470, 110],
               "Effective power at the hull must be delivered through the propeller "
               "and shafting. A cascade of efficiencies links the engine's brake power "
               "to the useful tow-rope power.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 314, 470, 80, "P_D = P_E ⁄ η_D",
            label="Delivered power", accent=STEEL,
            note="η_D = η_H · η_O · η_R, the quasi-propulsive coefficient.")
    eq_card(layer, MARGIN_X, 404, 470, 80, "P_B = P_D ⁄ (η_s · η_g)",
            label="Brake power", accent=TEALD,
            note="Shaft and gearbox losses to the engine flange.")
    eq_card(layer, MARGIN_X, 494, 470, 90, "η_H = (1 − t) ⁄ (1 − w)",
            label="Hull efficiency", accent=AMBER,
            note="Thrust-deduction t and wake fraction w from the hull–propeller "
                 "interaction.")

    chart = chart_panel(layer, [646, 196, 558, 430], "Power vs speed",
                        "Effective & delivered power", domain=(0, 0, 22, 12000),
                        plot=[710, 250, 450, 300])
    PE = [(v, min(1.2 * v ** 1.825 * v * 0.93, 12000)) for v in range(0, 23)]
    PD = [(v, min(p / 0.68, 12000)) for v, p in PE]
    chart.axes(x_ticks=[0, 5, 10, 15, 20], y_ticks=[0, 3000, 6000, 9000, 12000],
               x_format=lambda v: f"{v:g}", y_format=lambda v: f"{int(v / 1000)}k", grid=True)
    chart.line(PE, stroke=TEAL, width=2.8, smooth=True, label="P_E effective")
    chart.line(PD, stroke="#21364C", width=3.0, smooth=True, label="P_D delivered")
    chart.legend(at=(710, 612))
    layer.extend(chart.objects())
    footer_source(layer)


def page_propeller_geometry(builder):
    layer = chrome(builder, "03 · Propulsion", "Propeller geometry")
    layer.text([MARGIN_X, 196, 470, 110],
               "A screw propeller advances by P per revolution in a solid; the real "
               "advance is less by the slip. Blade area ratio and pitch ratio set "
               "thrust, cavitation margin and efficiency.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 314, 470, 78, "J = V_a ⁄ (n · D)",
            label="Advance coefficient", accent=STEEL,
            note="Non-dimensional inflow; the x-axis of the open-water chart.")
    eq_card(layer, MARGIN_X, 404, 470, 78, "slip = 1 − V_a ⁄ (n·P)",
            label="Real slip ratio", accent=TEALD,
            note="The shortfall between geometric and actual advance.")
    eq_card(layer, MARGIN_X, 494, 470, 90, "BAR = A_E ⁄ A_0",
            label="Blade-area ratio", accent=AMBER,
            note="Expanded blade area over disc area; raised to delay cavitation.")

    # 4-blade propeller drawing, built from rotated blade paths
    card(layer, [636, 196, 568, 430])
    layer.text([660, 214, 480, 20], "Four-bladed propeller (projected)",
               style={"class": "cardh", "font_size": 14})
    cx, cy, R = 920, 420, 150
    dot(layer, cx, cy, 26, "#34597A")
    dot(layer, cx, cy, 10, "#21364C")
    # disc circle
    layer.add({"type": "ellipse", "center": [cx, cy], "rx": R, "ry": R,
               "fill": "none", "stroke": LINE, "stroke_style": {"stroke_width": 1.2,
                                                                 "stroke_dasharray": [4, 5]}})
    for b in range(4):
        a0 = b * math.pi / 2
        # build one blade as a closed leaf from hub to tip and back
        def pol(rr, da):
            return (cx + rr * math.cos(a0 + da), cy + rr * math.sin(a0 + da))
        lead = [pol(28, 0.18), pol(80, 0.34), pol(130, 0.30), pol(R, 0.12)]
        trail = [pol(R, -0.12), pol(130, -0.32), pol(80, -0.40), pol(30, -0.20)]
        pts = [Vec2(*p) for p in lead + trail]
        blade = Path().move_to(pts[0].x, pts[0].y).through(pts[1:]).close()
        layer.add(blade.object(stroke=STEEL, fill="#BFD6E6",
                               stroke_style={"stroke_width": 1.8}))
    layer.text([cx + R - 6, cy + R - 10, 80, 16], "D = 4.8 m", style={"class": "draw"})
    footer_source(layer)


def page_open_water(builder):
    layer = chrome(builder, "03 · Propulsion", "Open-water characteristics")
    layer.text([MARGIN_X, 196, 470, 130],
               "The open-water diagram is the propeller's signature: thrust and torque "
               "coefficients and efficiency, all against advance coefficient J. The "
               "design point sits just left of peak efficiency.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 350, 470, 78, "K_T = T ⁄ (ρ n² D⁴)",
            label="Thrust coefficient", accent=STEEL, note="Non-dimensional thrust.")
    eq_card(layer, MARGIN_X, 440, 470, 78,
            "η_O = (J ⁄ 2π) · (K_T ⁄ K_Q)",
            label="Open-water efficiency", accent=TEALD,
            note="Peaks near J ≈ 0.7 for this blade.")

    chart = chart_panel(layer, [646, 196, 558, 430], "K_T, 10·K_Q, η_O vs J",
                        "Open-water test", domain=(0, 0, 1.0, 0.9), plot=[710, 260, 450, 300])
    J = [j / 20 for j in range(0, 21)]
    KT = [(j, max(0.42 * (1 - j / 1.05), 0.0)) for j in J]
    KQ10 = [(j, 10 * max(0.075 * (1 - j / 1.15), 0.0)) for j in J]   # plotted as 10·K_Q
    eta = []
    for j in J:
        kt = max(0.42 * (1 - j / 1.05), 1e-6)
        kq = max(0.075 * (1 - j / 1.15), 1e-6)
        eta.append((j, min(max((j / (2 * math.pi)) * (kt / kq), 0.0), 0.85)))
    chart.axes(x_ticks=[0, 0.25, 0.5, 0.75, 1.0], y_ticks=[0, 0.2, 0.4, 0.6, 0.8],
               x_format=lambda v: f"{v:.2f}", y_format=lambda v: f"{v:.1f}", grid=True)
    chart.line(KT, stroke=STEEL, width=2.6, smooth=True, label="K_T")
    chart.line(KQ10, stroke=AMBER, width=2.6, smooth=True, label="10·K_Q")
    chart.line(eta, stroke=TEAL, width=3.0, smooth=True, label="η_O")
    chart.legend(at=(710, 612))
    layer.extend(chart.objects())
    footer_source(layer)


# --------------------------------------------------------------------------- #
# Section 04 — structures                                                      #
# --------------------------------------------------------------------------- #

def page_midship_section(builder):
    layer = chrome(builder, "04 · Structures", "The midship section")
    layer.text([MARGIN_X, 196, 470, 110],
               "The midship section carries the longitudinal bending of the hull "
               "girder. Its section modulus about the neutral axis sets the stress "
               "for a given bending moment.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 314, 470, 80, "Z = I_NA ⁄ y",
            label="Section modulus", accent=STEEL,
            note="I_NA about the horizontal neutral axis; y to deck or keel.")
    eq_card(layer, MARGIN_X, 404, 470, 80, "σ = M ⁄ Z",
            label="Bending stress", accent=TEALD,
            note="Keep σ below the allowable for the steel grade.")
    eq_card(layer, MARGIN_X, 494, 470, 90, "I = Σ (I_i + A_i·d_i²)",
            label="Parallel-axis assembly", accent=AMBER,
            note="Sum plate & stiffener contributions about the NA.")

    # midship half-section drawing (one side, centreline at right)
    card(layer, [636, 196, 568, 430])
    layer.text([660, 214, 480, 20], "Midship half-section",
               style={"class": "cardh", "font_size": 14})
    clx = 1130       # centreline at right
    keel = 580
    deck = 250
    side = 740
    bilge = 40
    # shell: keel -> bilge radius -> side -> deck
    shell = (Path().move_to(clx, keel)
             .line_to(side + bilge, keel)
             .through([(side, keel - bilge)])
             .line_to(side, deck + 20)
             .line_to(clx, deck + 20))
    layer.add(shell.object(stroke=HULL, fill="#EAF1F8", stroke_style={"stroke_width": 2.6}))
    # deck
    hline(layer, side, clx, deck + 20, STEEL, 2.6)
    # neutral axis
    na = (keel + deck) / 2 + 40
    hline(layer, side - 10, clx + 10, na, RED, 1.6, stroke_dasharray=[7, 5])
    layer.text([side - 90, na - 9, 80, 16], "N.A.", style={"class": "draw", "color": RED, "align": "right"})
    # longitudinal stiffeners (tee bars) along the side and bottom
    for y in range(deck + 60, keel, 46):
        layer.add({"type": "polyline", "closed": True,
                   "points": [[side, y], [side + 16, y - 4], [side + 16, y + 4]],
                   "fill": STEEL})
    for x in range(side + 60, clx, 60):
        layer.add({"type": "polyline", "closed": True,
                   "points": [[x, keel], [x - 4, keel - 16], [x + 4, keel - 16]],
                   "fill": STEEL})
    # double bottom
    hline(layer, clx, side + bilge, keel - 46, "#34597A", 2.0)
    vline(layer, clx, deck + 20, keel, "#9FB0C2", 1.2)   # centreline
    layer.text([clx + 2, deck + 24, 40, 16], "CL", style={"class": "draw"})
    footer_source(layer)


def page_bending(builder):
    layer = chrome(builder, "04 · Structures", "Longitudinal strength")
    layer.text([MARGIN_X, 196, 470, 130],
               "Poised on a wave, the hull girder bends. A crest amidships sags the "
               "ends down (hogging); a trough amidships does the reverse (sagging). "
               "The still-water and wave moments superpose.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 350, 470, 78, "M(x) = ∫₀ˣ ∫₀ˢ q(ξ) dξ ds",
            label="Moment from load", accent=STEEL,
            note="Double-integrate the net buoyancy-minus-weight load q(x).")
    eq_card(layer, MARGIN_X, 440, 470, 78, "M_wave ≈ 0.11·C·L²·B·(C_B+0.7)",
            label="IACS wave moment", accent=TEALD,
            note="Rule estimate of the design hogging/sagging moment.")

    chart = chart_panel(layer, [646, 196, 558, 430], "Bending-moment distribution",
                        "Hog (+) / sag (−)", domain=(0, -1.2, 1.0, 1.2),
                        plot=[710, 270, 450, 250])
    hog = [(x / 20, math.sin(math.pi * x / 20)) for x in range(0, 21)]
    sag = [(x / 20, -0.7 * math.sin(math.pi * x / 20)) for x in range(0, 21)]
    chart.axes(x_ticks=[0, 0.25, 0.5, 0.75, 1.0], y_ticks=[-1.0, -0.5, 0, 0.5, 1.0],
               x_format=lambda v: f"{v:.2f}L", y_format=lambda v: f"{v:+.1f}", grid=True)
    chart.line(hog, stroke=RED, width=2.8, smooth=True, label="Hogging")
    chart.line(sag, stroke=STEEL, width=2.8, smooth=True, label="Sagging")
    chart.marker(0.5, 1.0, r=4, fill=RED)
    chart.legend(at=(710, 612))
    layer.extend(chart.objects())
    pm = chart.frame.point(0.5, 1.0)
    layer.text([pm.x - 50, pm.y - 22, 120, 16], "M_max @ ½L",
               style={"class": "draw", "color": RED})
    footer_source(layer)


def page_buckling(builder):
    layer = chrome(builder, "04 · Structures", "Plate & column buckling")
    layer.text([MARGIN_X, 196, 470, 130],
               "Compression panels in the deck and bottom can buckle long before they "
               "yield. Euler's critical load for a column and the plate buckling "
               "stress set stiffener spacing and plate thickness.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 350, 470, 80, "P_cr = π²·E·I ⁄ (k·L)²",
            label="Euler column", accent=STEEL,
            note="k captures end fixity; slender columns fail elastically.")
    eq_card(layer, MARGIN_X, 442, 470, 90, "σ_cr = k·(π²E ⁄ 12(1−ν²))·(t ⁄ b)²",
            label="Plate buckling", accent=TEALD,
            note="Critical stress rises with the thickness-to-spacing ratio (t/b)².")

    chart = chart_panel(layer, [646, 196, 558, 430], "Critical stress vs slenderness",
                        "σ_cr ⁄ σ_Y", domain=(0, 0, 3.0, 1.2), plot=[710, 270, 450, 250])
    # Euler hyperbola capped at yield (Johnson–Euler)
    pts = [(i / 10, min(1.0 / (i / 10) ** 2, 1.0)) for i in range(1, 31)]
    chart.axes(x_ticks=[0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0], y_ticks=[0, 0.3, 0.6, 0.9, 1.2],
               x_format=lambda v: f"{v:.1f}", y_format=lambda v: f"{v:.1f}", grid=True)
    chart.line(pts, stroke=TEAL, width=3.0, smooth=True)
    layer.extend(chart.objects())
    py = chart.frame.point(1.0, 1.0)
    hline(layer, 710, 1160, py.y, RED, 1.2, stroke_dasharray=[6, 4])
    layer.text([718, py.y - 18, 140, 16], "yield cut-off",
               style={"class": "draw", "color": RED})
    footer_source(layer)


def page_hull_block_3d(builder):
    layer = chrome(builder, "04 · Structures", "The hull as a 3D block model")
    layer.text([MARGIN_X, 196, 470, 150],
               "Before detailing, the hull is blocked out as a solid and projected. "
               "The SDK's Scene3D extrudes a deck outline through the depth and "
               "renders the back-to-front sorted faces in isometric — a quick volume "
               "check for the lines fairing above.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 372, 470, 80, "∇ = ∫∫∫ dV ≈ Σ A_i·Δx",
            label="Block volume", accent=STEEL,
            note="Simpson integration of stations gives the displaced volume.")
    eq_card(layer, MARGIN_X, 462, 470, 80, "LCB = (Σ x_i·A_i) ⁄ (Σ A_i)",
            label="Longitudinal CB", accent=TEALD,
            note="Centroid of the sectional-area curve.")

    card(layer, [636, 196, 568, 430])
    layer.text([660, 214, 480, 20], "Isometric block (Scene3D.extrude)",
               style={"class": "cardh", "font_size": 14})
    # a fined-out deck outline extruded through depth
    deck = [(-2.0, -0.6), (1.4, -1.0), (3.4, -0.55), (3.4, 0.55),
            (1.4, 1.0), (-2.0, 0.6), (-3.2, 0.0)]
    scene = Scene3D().extrude(deck, depth=1.6)
    # Scene3D.render emits children local to the group box, so the absolute panel
    # box positions the whole projection in one step.
    group = scene.render(box=[680, 250, 500, 350], fill="#CFE0EE", stroke=STEEL, id="hull_block")
    layer.add(group)
    layer.text([700, 600, 480, 16],
               "Faces painter-sorted by depth; isometric camera (35.26° elevation)",
               style={"class": "statlbl"})
    footer_source(layer)


# --------------------------------------------------------------------------- #
# Section 05 — seakeeping & maneuvering                                        #
# --------------------------------------------------------------------------- #

def page_spectrum_rao(builder):
    layer = chrome(builder, "05 · Seakeeping", "Wave spectra & response")
    layer.text([MARGIN_X, 196, 1128, 46],
               "A seaway is a sum of components described by an energy spectrum. The "
               "ship's response operator (RAO) maps wave amplitude to motion amplitude; "
               "multiplying spectrum by RAO² gives the response spectrum.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 264, 360, 200,
            "S(ω) = (A ⁄ ω⁵)·e^(−B ⁄ ω⁴)",
            label="Pierson–Moskowitz", accent=STEEL,
            note="Fully-developed sea; A,B from wind speed / sea state.")
    eq_card(layer, 460, 264, 360, 200,
            "RAO(ω) = |x_a ⁄ ζ_a|",
            label="Response amplitude operator", accent=TEALD,
            note="Transfer function from wave to motion; resonant peak near the "
                 "natural frequency.")
    eq_card(layer, 844, 264, 360, 200,
            "m₀ = ∫ S(ω)·RAO²(ω) dω",
            label="Response variance", accent=AMBER,
            note="Significant motion = 2√m₀ from the response spectrum.")

    chart = chart_panel(layer, [MARGIN_X, 484, 1128, 162], "Spectrum × RAO² → response", "",
                        domain=(0, 0, 2.0, 1.0), plot=[MARGIN_X + 60, 512, 1040, 112])
    S = [(w / 20, (0.0 if w == 0 else min((1.6 / (w / 20) ** 5) *
          math.exp(-0.8 / (w / 20) ** 4), 1.0))) for w in range(1, 41)]
    RAO = [(w / 20, min(1.0 / (1 + ((w / 20 - 0.9) * 3) ** 2), 1.0)) for w in range(0, 41)]
    resp = [(w / 20, min(s * r * 1.4, 1.0)) for (w, s), (_, r) in zip(S, RAO[1:])]
    chart.axes(x_ticks=[0, 0.5, 1.0, 1.5, 2.0], y_ticks=[0, 0.5, 1.0],
               x_format=lambda v: f"{v:.1f}", y_format=lambda v: f"{v:.1f}", grid=True)
    chart.line(S, stroke=STEEL, width=2.4, smooth=True, label="S(ω) sea")
    chart.line(RAO, stroke=AMBER, width=2.4, smooth=True, label="RAO")
    chart.line(resp, stroke=TEAL, width=3.0, smooth=True, label="Response")
    chart.legend(at=(MARGIN_X + 60, 636))
    layer.extend(chart.objects())
    footer_source(layer)


def page_roll(builder):
    layer = chrome(builder, "05 · Seakeeping", "Roll motion & resonance")
    layer.text([MARGIN_X, 196, 470, 130],
               "Roll is the lightly-damped motion that matters most for comfort and "
               "cargo. Its natural period depends on the roll radius of gyration and "
               "GM — and a low GM gives a slow, easy (but tender) roll.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 350, 470, 80, "T_φ = 2π·k_xx ⁄ √(g·GM)",
            label="Natural roll period", accent=STEEL,
            note="k_xx ≈ 0.35·B; resonance when T_φ meets the encounter period.")
    eq_card(layer, MARGIN_X, 442, 470, 90,
            "φ̈ + 2ζω·φ̇ + ω²·φ = M(t)⁄I",
            label="Damped oscillator", accent=TEALD,
            note="Roll obeys a forced second-order system; ζ is small for ships.")

    chart = chart_panel(layer, [646, 196, 558, 430], "Free roll decay",
                        "Lightly damped, ζ ≈ 0.06", domain=(0, -1.1, 40, 1.1),
                        plot=[710, 280, 450, 230])
    Tphi, zeta = 11.0, 0.06
    w = 2 * math.pi / Tphi
    ts = [x * 0.5 for x in range(0, 81)]
    decay = [(t, math.exp(-zeta * w * t) * math.cos(w * t)) for t in ts]
    env = [(t, math.exp(-zeta * w * t)) for t in ts]
    chart.axes(x_ticks=[0, 10, 20, 30, 40], y_ticks=[-1.0, -0.5, 0, 0.5, 1.0],
               x_format=lambda v: f"{v:g}s", y_format=lambda v: f"{v:+.1f}", grid=True)
    chart.line(decay, stroke=TEAL, width=2.6, smooth=True)
    chart.line(env, stroke=AMBER, width=1.4, smooth=True)
    chart.line([(t, -e) for t, e in env], stroke=AMBER, width=1.4, smooth=True)
    layer.extend(chart.objects())
    footer_source(layer)


def page_turning_circle(builder):
    layer = chrome(builder, "05 · Maneuvering", "The turning circle")
    layer.text([MARGIN_X, 196, 470, 130],
               "Putting the rudder over, the ship traces a turning circle defined by "
               "advance, transfer and tactical diameter. Steady turning diameter is a "
               "few ship-lengths for a merchant hull.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 350, 470, 78, "D_T ≈ (4–6)·L",
            label="Tactical diameter", accent=STEEL,
            note="Smaller is more manoeuvrable; larger is more course-stable.")
    eq_card(layer, MARGIN_X, 440, 470, 78, "R = V ⁄ r,   β = drift angle",
            label="Steady turn", accent=TEALD,
            note="Yaw rate r and speed V set the turn radius; the hull drifts at β.")

    card(layer, [636, 196, 568, 430])
    layer.text([660, 214, 480, 20], "Turning-circle trajectory",
               style={"class": "cardh", "font_size": 14})
    # approach then a circular arc, drawn with Path arc_to
    start = Vec2(740, 600)
    layer.line([start.x, start.y], [start.x, 470], **stroke(1.6, "#9FB0C2", stroke_dasharray=[6, 5]))
    turn = (Path().move_to(start.x, 470)
            .arc_to(150, 150, 0, True, True, (start.x + 4, 300))
            .arc_to(150, 150, 0, False, True, (start.x, 470)))
    layer.add(turn.object(stroke=TEAL, fill="none", stroke_style={"stroke_width": 2.8}))
    # markers
    dot(layer, start.x, 470, 4, RED)
    layer.text([start.x + 8, 474, 140, 16], "rudder over", style={"class": "draw", "color": RED})
    # advance & transfer annotations
    hline(layer, start.x, start.x + 150, 300, AMBER, 1.2, stroke_dasharray=[5, 4])
    layer.text([start.x + 30, 280, 160, 16], "tactical diameter", style={"class": "draw", "color": AMBER})
    vline(layer, start.x + 150, 300, 470, "#9FB0C2", 1.0)
    # ship glyph at start, rotated
    layer.add({"type": "polyline", "closed": True,
               "points": [[start.x - 6, 470 + 16], [start.x + 6, 470 + 16], [start.x, 470 - 8]],
               "fill": HULL})
    footer_source(layer)


# --------------------------------------------------------------------------- #
# Wrap-up pages                                                                #
# --------------------------------------------------------------------------- #

def page_powering_summary(builder):
    layer = chrome(builder, "Synthesis", "Powering & particulars — worked figures")
    layer.text([MARGIN_X, 196, 1128, 40],
               "Pulling the threads together for the example hull used throughout: "
               "a 120 m general-cargo vessel at 16 knots.",
               style={"class": "lede"})
    stats = [
        ("L_pp", "120 m", STEEL), ("Beam", "18.0 m", STEEL), ("Draught", "5.6 m", STEEL),
        ("Δ", "7 700 t", TEALD), ("C_B", "0.62", TEALD), ("Fn", "0.30", TEALD),
        ("R_T", "≈ 410 kN", AMBER), ("P_D", "≈ 7.6 MW", AMBER), ("η_D", "0.68", AMBER),
        ("GM", "0.90 m", RED), ("T_φ", "11 s", RED), ("D_T", "≈ 5 L", RED),
    ]
    cells = grid([MARGIN_X, 268, 1122, 324], cols=4, count=12, col_gap=22, row_gap=18)
    for (label, val, c), box in zip(stats, cells):
        x, y, cw, ch = box
        card(layer, box)
        vline(layer, x, y + 12, y + ch - 12, c, 3)
        layer.text([x + 20, y + 16, cw - 36, 18], label, style={"class": "statlbl"})
        layer.text([x + 20, y + 38, cw - 36, 44], val,
                   style={"class": "statbig", "font_size": 32, "color": c})
    footer_source(layer)


def page_design_spiral(builder):
    layer = chrome(builder, "Synthesis", "The design spiral", dark=False)
    layer.text([MARGIN_X, 196, 470, 150],
               "Ship design converges: each pass refines mission, lines, hydrostatics, "
               "powering, structure and weights, tightening toward a balanced design. "
               "The spiral below is drawn with the SDK Path through a logarithmic "
               "polar curve.",
               style={"class": "lede"})
    eq_card(layer, MARGIN_X, 380, 470, 80, "r(θ) = r₀·e^(−a·θ)",
            label="Convergent spiral", accent=TEALD,
            note="Radius shrinks each revolution as requirements close.")

    # logarithmic spiral via Path.through
    cx, cy = 920, 410
    pts = []
    for k in range(0, 220):
        th = k * 0.13
        r = 200 * math.exp(-0.035 * th)
        pts.append(Vec2(cx + r * math.cos(th), cy + r * math.sin(th)))
    sp = Path().move_to(pts[0].x, pts[0].y).through(pts[1:])
    layer.add(sp.object(stroke=TEAL, fill="none", stroke_style={"stroke_width": 2.4}))
    # spoke labels around the spiral
    spokes = ["Mission", "Lines", "Hydrostatics", "Powering", "Structure", "Weights"]
    for i, name in enumerate(spokes):
        a = i * math.pi / 3
        rr = 215
        px, py = cx + rr * math.cos(a), cy + rr * math.sin(a)
        layer.line([cx, cy], [px, py], **stroke(1.0, LINE))
        dot(layer, px, py, 4, STEEL)
        layer.text([px - 50, py - 22, 100, 16], name,
                   style={"class": "draw", "align": "center"})
    dot(layer, cx, cy, 5, RED)
    footer_source(layer)


def page_closing(builder):
    global _page_no
    _page_no += 1
    layer = new_page(builder, "closing")
    layer.rect([0, 0, W, H], fill=INK)
    for gy in range(120, 520, 36):
        hline(layer, 760, 1200, gy, GRID, 1)
    layer.text([MARGIN_X, 250, 520, 24], "End of primer", style={"class": "kicker"})
    layer.text([MARGIN_X, 286, 760, 120], "From lines to launch",
               style={"class": "h1", "font_size": 54})
    hline(layer, MARGIN_X, MARGIN_X + 120, 392, TEAL, 3)
    layer.text([MARGIN_X, 410, 640, 120],
               "Every figure in this deck — the hull lines, the GZ curve, the open-water "
               "diagram, the 3D block and the design spiral — was generated "
               "programmatically through the FrameForge Python SDK's geometry and "
               "drawing helpers, then validated against the authoritative model.",
               style={"class": "bodyD", "font_size": 16})
    layer.text([MARGIN_X, 600, 900, 26],
               "frameforge.sdk · DocumentBuilder · Frame · Path · Scene3D · theme",
               style={"class": "source", "color": "#7E93AB"})
    layer.text([1044, 680, 160, 22], f"{TOTAL_PAGES:02d} / {TOTAL_PAGES}",
               style={"class": "pnum", "align": "right"})


# --------------------------------------------------------------------------- #
# Assemble                                                                     #
# --------------------------------------------------------------------------- #

def build_deck() -> DocumentBuilder:
    global _page_no
    _page_no = 0  # reset the page counter so repeated builds are deterministic
    builder = DocumentBuilder(
        title="Ship Design from First Principles",
        profile="deck",
        lang="en",
    )
    theme(builder, colors={}, styles=STYLES)

    # 01–02
    page_cover(builder)
    page_contents(builder)
    # Section 01 — hull geometry (03–06)
    page_divider(builder, "div01", "01", "Hull geometry & form",
                 "Lines, the body plan, and the coefficients that describe a hull.")
    page_lines_plan(builder)
    page_body_plan(builder)
    page_coefficients(builder)
    # Section 02 — hydrostatics & stability (07–11)
    page_divider(builder, "div02", "02", "Hydrostatics & stability",
                 "Buoyancy, the hydrostatic curves, and the GZ righting arm.")
    page_archimedes(builder)
    page_hydrostatic_curves(builder)
    page_stability_geometry(builder)
    page_gz_curve(builder)
    # Section 03 — resistance & propulsion (12–18)
    page_divider(builder, "div03", "03", "Resistance & propulsion",
                 "Froude scaling, the resistance build-up, and propeller open water.")
    page_froude(builder)
    page_resistance_curve(builder)
    page_waves(builder)
    page_speed_power(builder)
    page_propeller_geometry(builder)
    page_open_water(builder)
    # Section 04 — structures (19–23)
    page_divider(builder, "div04", "04", "Structures",
                 "The midship section, longitudinal bending, buckling and 3D blocks.")
    page_midship_section(builder)
    page_bending(builder)
    page_buckling(builder)
    page_hull_block_3d(builder)
    # Section 05 — seakeeping & maneuvering (24–28)
    page_divider(builder, "div05", "05", "Seakeeping & maneuvering",
                 "Wave spectra, response operators, roll period and the turning circle.")
    page_spectrum_rao(builder)
    page_roll(builder)
    page_turning_circle(builder)
    # Synthesis (28–30)
    page_powering_summary(builder)
    page_design_spiral(builder)
    page_closing(builder)
    return builder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yaml", default=os.path.join(ROOT, "static", "examples",
                                                    "naval-engineering-deck.fg.yaml"),
                    help="output document path")
    ap.add_argument("--render", action="store_true",
                    help="also rasterise every page to SVG under out/naval/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "naval"),
                    help="SVG output directory (with --render)")
    args = ap.parse_args()

    builder = build_deck()
    doc = builder.build()                 # validates against the authoritative model
    n_pages = len(doc.pages)
    print(f"Built deck: {n_pages} pages")

    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity == "warning"]
    print(f"Validation: ok={report.ok}  errors={len(errors)}  warnings={len(warns)}")
    for i in errors[:20]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    if warns:
        from collections import Counter
        for code, c in Counter(i.rule_id for i in warns).most_common():
            print(f"  warn ×{c}: {code}")

    os.makedirs(os.path.dirname(args.yaml), exist_ok=True)
    with open(args.yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {args.yaml}")

    if args.render:
        from frameforge.sdk.conform import render_page_svgs
        svgs = render_page_svgs(doc, base_dir=ROOT)
        os.makedirs(args.out, exist_ok=True)
        for idx, svg in enumerate(svgs, 1):
            p = os.path.join(args.out, f"page-{idx:02d}.svg")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(svg)
        print(f"Rendered {len(svgs)} SVG pages to {args.out}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
