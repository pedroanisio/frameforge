#!/usr/bin/env python3
"""Doc-Field — logo proposal board, recreated as a native FrameGraph document.

A faithful vector reconstruction of the "Doc-Field / LOGO PROPOSAL" board: two
mirrored panels (ink-on-dark, ink-on-light) each carrying the same mark, wordmark,
tagline and chrome. The mark reads left-to-right as the product story —

    incoming data streams  →  a structured node lattice  →  stacked document layers
    (circuit traces)          (beads-on-wires matrix)       (perspective sheets that
                                                             dissolve into a particle field)

— which is exactly ``REVEAL. MAP. STRUCTURE. KNOW.`` The reference art is a raster
(an AI image), so this is a *clean-room vector interpretation*: every element is
constructed from FrameGraph primitives (lines, ellipses, polylines) on a normalized,
scale-parametric grid, so the mark stays crisp at any size and re-colours for the
dark/light grounds from one code path.

Run from the repository root::

    uv run python examples/docfield_logo.py        # writes _tmp/docfield/*.svg
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT_DIR = os.path.join(ROOT, "_tmp", "docfield")
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    linear_gradient,
    measure_text,
    render_page_svgs,
    rgba,
    serialize,
)

# --------------------------------------------------------------------------- #
# Type / palette tokens.
# --------------------------------------------------------------------------- #
# The small technical chrome (header/tagline/footer) is letter-spaced caps; at that
# size a clean sans reads the same as the reference. The wordmark itself is drawn,
# not typeset (see ``_wordmark``), because this render collapses every font-family.
LABEL = ["Chakra Petch", "Saira", "Oxanium", "Fira Mono", "DejaVu Sans Mono", "monospace"]

DARK = {
    "bg_top": "#141518", "bg_mid": "#0c0d10", "bg_bot": "#050506",
    "ink": "#F4F2EC",          # main strokes / solid nodes
    "word": "#F6F5F0",         # wordmark
    "muted": "#B4B4AF",        # tagline
    "chrome": "#C9C9C4",       # header
    "foot": "#7E7E7A",         # footer
    "rule": "#3A3B3E",         # thin rules
}
LIGHT = {
    "bg_top": "#F1F0EB", "bg_mid": "#ECEBE5", "bg_bot": "#E4E3DC",
    "ink": "#17181C",
    "word": "#131418",
    "muted": "#6C6D71",
    "chrome": "#2B2C30",
    "foot": "#565759",
    "rule": "#C7C6C0",
}


# --------------------------------------------------------------------------- #
# THE MARK — drawn in a local unit frame centred on the node lattice, mapped to
# the page by (cx, cy) + local * S. All weights/radii scale with S.
# --------------------------------------------------------------------------- #
# Geometry is authored in *source panel pixels* (the board is rendered at the source's
# 1448×1086, so 1 local unit == 1 reference pixel at S == 1). Origin (0, 0) is the
# lattice centre. Values are measured from the reference: mark bbox ≈ 400×333, five
# wires spanning ~70 px, traces reaching ~165 px left of the wires and sheets ~165 px
# right (the mark is left-right symmetric about the wire column).
WIRES_X = [-35.0, -17.5, 0.0, 17.5, 35.0]                       # five tight wires (span 70)
ROWS_Y = [-115.0, -82.0, -49.0, -16.0, 17.0, 50.0, 83.0, 116.0]  # eight lattice rows
WIRE_TOP, WIRE_BOT = -177.0, 150.0               # wires overrun the lattice top & bottom

# Each sheet is a perspective ruled plane: fine lines dense at the right tip that
# dissolve leftward into a dot stipple (structure resolving out of particles). The
# top/bottom wings are asymmetric, which reads as a plane seen from slightly above.
SHEET_BACK, SHEET_APEX = 44.0, 200.0             # left (near wires) → right tip
SHEET_TOPWING, SHEET_BOTWING = 40.0, 24.0
SHEET_TIP = 3.5                                  # half-height of the (near-pointed) tip
SHEET_DISSOLVE = 44.0                            # stipple reaches this far left of BACK
SHEET_AY = [-102.0, -40.0, 24.0, 86.0]           # four stacked sheets

TRACE_LEFT = -200.0                              # leftmost trace start (mark left edge)
TRACE_TERM = -46.0                               # trace terminal node, just left of wires


def _mark(page, cx, cy, S, c):
    """Draw the whole Doc-Field mark centred on ``(cx, cy)`` at scale ``S`` using
    palette ``c``. Deterministic (seeded jitter) so the vector output is stable."""
    rng = random.Random(20260701)

    def P(dx, dy):
        return [cx + dx * S, cy + dy * S]

    def w(v):
        return v * S

    def dot(dx, dy, r, fill, **kw):
        page.circle(P(dx, dy), max(w(r), 0.4), fill=fill, **kw)

    def seg(a, b, width, color, cap="round", **kw):
        page.line(P(*a), P(*b), stroke=color,
                  stroke_style={"stroke_width": w(width), "stroke_linecap": cap, **kw})

    ink = c["ink"]

    # -- 1. vertical wires (drawn first, behind the beads) ------------------- #
    for wx in WIRES_X:
        seg((wx, WIRE_TOP), (wx, WIRE_BOT), 1.1, ink, cap="round")

    # -- 2. incoming circuit traces (left) ---------------------------------- #
    #    each: horizontal in from the left, a short diagonal down-step, then a
    #    run into the lattice, terminating in a filled node just left of it.
    trace_rows = [ROWS_Y[i] for i in (0, 1, 2, 4, 5, 6)]
    steps = [9, 16, 12, 18, 13, 20]
    vias = {2: True, 4: True}                       # a couple carry a small "via"
    for i, ty in enumerate(trace_rows):
        step = steps[i]
        x_start = TRACE_LEFT - (i % 3) * 6
        pts = [(x_start, ty - step), (-96, ty - step), (-62, ty), (TRACE_TERM, ty)]
        page.polyline([P(*p) for p in pts], fill="none", stroke=ink,
                      stroke_style={"stroke_width": w(1.15), "stroke_linecap": "round",
                                    "stroke_linejoin": "round"})
        seg((TRACE_TERM, ty), (WIRES_X[0], ty), 1.0, ink)   # tie into the first wire
        dot(TRACE_TERM, ty, 4.0 if i % 2 == 0 else 3.2, ink)
        if vias.get(i):
            dot(-104, ty - step, 2.1, ink)
            dot(-140, ty - step, 1.4, ink)

    # -- 3. node lattice: beads strung on the wires, size swelling centre-left #
    for wx in WIRES_X:
        for ry in ROWS_Y:
            bump = math.exp(-(((wx + 6) / 34.0) ** 2 + (ry / 100.0) ** 2))
            r = 2.1 + 3.1 * bump + rng.uniform(-0.25, 0.25)
            dot(wx, ry, r, ink)

    # -- 4. stacked perspective sheets: ruling lines that converge on a short  #
    #       tip edge (so they stay distinct, not a solid wedge), structured at #
    #       the right and dissolving to a dot stipple toward the lattice.      #
    xl = SHEET_BACK - SHEET_DISSOLVE                 # left (back) edge of the plane
    n_rule = 19
    for ay in SHEET_AY:
        for i in range(n_rule):
            f = i / (n_rule - 1)
            ly = ay - SHEET_TOPWING + f * (SHEET_TOPWING + SHEET_BOTWING)   # back end
            ry = ay - SHEET_TIP + f * (2 * SHEET_TIP)                       # tip end
            edge = i in (0, n_rule - 1)              # the two bounding rulings

            def pt(s):                               # s: 0 at tip … 1 at back edge
                return (SHEET_APEX + s * (xl - SHEET_APEX), ry + s * (ly - ry))

            if edge:                                 # bounding rulings: full solid chevron
                seg((SHEET_APEX, ry), pt(1.0), 0.6, ink)
                continue
            # leave the tip wedge (s<0.24) to the two boundary lines so it reads as a
            # clean point; stipple only the body, dense at the right and fading left.
            s = 0.24
            while s < 0.99:
                t = (s - 0.24) / 0.76
                px, py = pt(s)
                dot(px + rng.uniform(-0.5, 0.5), py + rng.uniform(-0.5, 0.5),
                    0.95 - 0.4 * t, rgba(ink, (1.0 - t) * 0.5 + 0.18))
                s += 0.028

    # -- 5. base wedge — a slim ground plane tucked under the lattice -------- #
    seg((-92, 120), (150, 98), 0.9, ink)
    seg((-92, 120), (120, 152), 0.9, ink)


# --------------------------------------------------------------------------- #
# THE WORDMARK — "Doc-Field" as constructed vector letterforms.
#
# The reference uses a wide, geometric "techno" face that is not installed, and
# this render environment collapses every CSS font-family to a single proportional
# sans — so the identity glyph is *drawn*, not typeset. A monoline skeleton (one
# uniform stroke weight, round joins) reproduces the wide, even, engineered rhythm
# and — like any real logo — is resolution- and font-independent.
# --------------------------------------------------------------------------- #
def _wordmark(page, cx, by, cap, color, *, target_width=None):
    """Draw title-case "Doc-Field" centred on ``cx`` with baseline ``by`` and
    cap-height ``cap``, in ``color``.

    Vertical metrics derive from ``cap``; horizontal metrics are stretched by a
    single factor so the mark's total width equals ``target_width`` when given. The
    reference face is *wide* (≈470 px at a 63 px cap), so the stretch — applied to
    glyph advances and gaps but not to the (constant) stroke weight — reproduces its
    engineered, tracked-out proportions exactly rather than by eye."""
    T = cap * 0.135                     # monoline stroke weight
    xh = cap * 0.70                     # lowercase x-height
    topcap = by - cap
    xtop = by - xh
    ryo = (xh - T) / 2.0                # x-height ring radius (centreline)
    cyx = by - xh / 2.0                 # x-height ring centre

    sw = {"stroke": color, "stroke_style": {
        "stroke_width": T, "stroke_linecap": "round", "stroke_linejoin": "round"}}

    def vseg(x, y0, y1):
        page.line([x, y0], [x, y1], **sw)

    def hseg(x0, x1, y):
        page.line([x0, y], [x1, y], **sw)

    def ring(x0, y0, rx, ry):
        page.ellipse([x0, y0], rx, ry, fill="none", **sw)

    def poly_arc(x0, y0, rx, ry, a0, a1, n=30):
        pts = []
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            pts.append([x0 + rx * math.cos(a), y0 + ry * math.sin(a)])
        page.polyline(pts, fill="none", **sw)

    def g_D(x, w):
        sx = x + T / 2
        vseg(sx, topcap + T / 2, by - T / 2)
        hseg(sx, x + w * 0.46, topcap + T / 2)
        hseg(sx, x + w * 0.46, by - T / 2)
        poly_arc(x + w * 0.46, by - cap / 2, w * 0.54 - T / 2, (cap - T) / 2, -90, 90)

    def g_o(x, w):
        ring(x + w / 2, cyx, (w - T) / 2, ryo)

    def g_c(x, w):
        poly_arc(x + w / 2, cyx, (w - T) / 2, ryo, 58, 302)

    def g_hyphen(x, w):
        hseg(x + T / 2, x + w - T / 2, by - xh * 0.60)

    def g_F(x, w):
        sx = x + T / 2
        vseg(sx, topcap + T / 2, by - T / 2)
        hseg(sx, x + w - T / 2, topcap + T / 2)
        hseg(sx, x + w * 0.80, by - cap * 0.46)

    def g_i(x, w):
        sx = x + w / 2
        vseg(sx, xtop + T / 2, by - T / 2)
        page.circle([sx, xtop - T * 0.95], T * 0.58, fill=color)

    def g_e(x, w):
        cx0 = x + w / 2
        rx = (w - T) / 2
        hseg(cx0 - rx, cx0 + rx, cyx)
        poly_arc(cx0, cyx, rx, ryo, 55, 360)

    def g_l(x, w):
        vseg(x + w / 2, topcap + T / 2, by - T / 2)

    def g_d(x, w):
        vseg(x + w - T / 2, topcap + T / 2, by - T / 2)
        ring(x + (w - T) / 2, cyx, (w - T) / 2, ryo)

    specs = [(g_D, 0.70), (g_o, 0.66), (g_c, 0.60), (g_hyphen, 0.46),
             (g_F, 0.58), (g_i, 0.18), (g_e, 0.64), (g_l, 0.18), (g_d, 0.66)]
    gap0 = 0.13 * cap
    nominal = sum(frac * cap for _, frac in specs) + gap0 * (len(specs) - 1)
    xscale = 1.0 if target_width is None else target_width / nominal
    gap = gap0 * xscale
    widths = [frac * cap * xscale for _, frac in specs]
    total = sum(widths) + gap * (len(specs) - 1)
    x = cx - total / 2.0
    for (fn, _), w in zip(specs, widths):
        fn(x, w)
        x += w + gap


# --------------------------------------------------------------------------- #
# One poster panel: ground + chrome + mark + wordmark + tagline.
# --------------------------------------------------------------------------- #
def _panel(page, x0, W, H, c, *, align_right):
    # Positions are the reference's, in panel-local pixels (measured from the source):
    # mark centre ≈ (354, 466), wordmark baseline 708 / cap 63 / width 470, tagline
    # baseline ≈ 774, header at y≈43/64, footer at y≈1038. The board renders at the
    # source resolution, so these map one-to-one.
    axis = x0 + 360           # shared vertical axis for wordmark + tagline
    mark_cx = x0 + 354
    mark_cy = 466

    # ground: a whisper of vertical gradient, like the reference boards
    page.rect([x0, 0, W, H], fill=linear_gradient(
        [(c["bg_top"], 0.0), (c["bg_mid"], 0.5), (c["bg_bot"], 1.0)], angle=180))

    pad = 46
    hx = x0 + pad
    htext_align = "right" if align_right else "left"
    hbox_w = W - 2 * pad
    for k, (txt, wt) in enumerate([("DOC-FIELD", 700), ("LOGO PROPOSAL", 500)]):
        page.add({"type": "text", "box": [hx, 40 + k * 21, hbox_w, 22],
                  "spans": [{"text": txt, "style": {"color": c["chrome"]}}],
                  "style": {"font_family": LABEL, "font_size": 15, "font_weight": wt,
                            "letter_spacing": 4.5, "text_align": htext_align}})
    if align_right:
        page.line([x0 + W - pad - 150, 90], [x0 + W - pad, 90], stroke=c["rule"],
                  stroke_style={"stroke_width": 1.0})
    else:
        page.line([hx, 90], [hx + 150, 90], stroke=c["rule"],
                  stroke_style={"stroke_width": 1.0})

    # -- the mark ------------------------------------------------------------ #
    _mark(page, mark_cx, mark_cy, 1.0, c)

    # -- wordmark (constructed vector letterforms) --------------------------- #
    _wordmark(page, axis, 708, 63, c["word"], target_width=470)
    page.line([axis - 30, 736], [axis + 30, 736], stroke=c["muted"],
              stroke_style={"stroke_width": 1.3})
    # -- tagline ------------------------------------------------------------- #
    page.add({"type": "text", "box": [x0, 760, W, 26],
              "spans": [{"text": "REVEAL.  MAP.  STRUCTURE.  KNOW.",
                         "style": {"color": c["muted"]}}],
              "style": {"font_family": LABEL, "font_size": 15, "font_weight": 500,
                        "letter_spacing": 3.0, "text_align": "center"}})

    # -- footer -------------------------------------------------------------- #
    page.add({"type": "text", "box": [hx, H - 52, hbox_w, 22],
              "spans": [{"text": "PRECISION IN DOCUMENT INTELLIGENCE",
                         "style": {"color": c["foot"]}}],
              "style": {"font_family": LABEL, "font_size": 12.5, "font_weight": 500,
                        "letter_spacing": 3.0, "text_align": htext_align}})


# --------------------------------------------------------------------------- #
# Pages.
# --------------------------------------------------------------------------- #
BOARD_W, BOARD_H = 1448, 1086
PANEL_W = BOARD_W // 2


def _board_page(b):
    page = b.page("board", canvas={"size": [BOARD_W, BOARD_H], "units": "px"},
                  coordinate_mode="absolute")
    page._lettering_depth += 1
    _panel(page, 0, PANEL_W, BOARD_H, DARK, align_right=False)
    _panel(page, PANEL_W, PANEL_W, BOARD_H, LIGHT, align_right=True)
    return page


def _single_page(b, sid, c, align_right):
    page = b.page(sid, canvas={"size": [PANEL_W, BOARD_H], "units": "px"},
                  coordinate_mode="absolute")
    page._lettering_depth += 1
    _panel(page, 0, PANEL_W, BOARD_H, c, align_right=align_right)
    return page


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Doc-Field — Logo Proposal", profile="deck", lang="en")
    _board_page(b)
    _single_page(b, "dark", DARK, align_right=False)
    _single_page(b, "light", LIGHT, align_right=True)
    return b


def main() -> int:
    doc = build().build()
    os.makedirs(OUT_DIR, exist_ok=True)
    svgs = render_page_svgs(doc)
    names = ["docfield-board.svg", "docfield-dark.svg", "docfield-light.svg"]
    for name, svg in zip(names, svgs):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
    with open(os.path.join(OUT_DIR, "docfield.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {len(names)} SVG(s) + YAML to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
