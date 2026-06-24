#!/usr/bin/env python3
"""Illustration plates for the book chapter *Layout Methods — A Field Guide*.

Each figure is one absolute-mode page, authored through the FrameGraph SDK and
rendered by the project's own SVG proxy — the system drawing the very layout
methods it is built on. The figures are deliberately *didactic schematics*, not
spec-complete implementations of the algorithms they depict (see the chapter's
disclaimer).

The plates dogfood the SDK's own layout helpers (``inset`` / ``row`` /
``column`` / ``grid``) — the same box-geometry primitives the chapter argues a
layout layer should expose — so the figures are, themselves, an instance of the
thesis they illustrate.

The script lives in ``examples/`` (the conventional home for SDK author-clients,
alongside ``architecture_map.py``) but writes its rendered plates into the book
chapter's directory, ``_tmp/figures/``.

Run from the repository root::

    uv run python examples/layout_methods_figures.py     # writes _tmp/figures/*.svg
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    Chart,
    DocumentBuilder,
    Frame,
    render_page_svgs,
    serialize,
)
from framegraph.sdk.layout import column, grid, inset, row  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Shared visual system — a sober, low-chroma print palette.
#
# One restrained primary accent (a muted steel-indigo) carries the page chrome:
# spine, kicker, title rule, primary nodes. Every other hue is a desaturated,
# print-weight tint reserved for a genuine semantic role — never decoration.
# Purely enumerative fills (grid cells, treemap cells) collapse to a single
# accent so that area and number, not colour, do the encoding.
# --------------------------------------------------------------------------- #
W = 1100
MARGIN = 56

SANS = ["Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"]

# Neutrals — a calm paper-and-ink ramp; soft near-black, never pure black.
PAPER = "#FFFFFF"
CARD = "#FFFFFF"            # raised content rectangles, on the panel ground
PANEL = "#F3F5F8"           # quiet section panels
INK = "#1F2530"             # primary text
MUTE = "#5B6573"            # secondary text
FAINT = "#646D7B"           # tertiary / mono micro-labels (AA ~4.8:1 on white)
LINE = "#E5E8EC"            # hairlines
RULE = "#C6CBD3"            # title rule / heavier separators
INKBG = "#1F2A36"           # dark "code / formula" slab

# Accent families (fill, stroke, text) — muted, one hue per conceptual role.
INDIGO = ("#ECEDF6", "#5C618E", "#3F4168")   # primary accent / page chrome
VIOLET = ("#EFEBF4", "#6E5E8A", "#4C3F66")
BLUE = ("#E9EEF5", "#42648F", "#2D4865")
TEAL = ("#E5EFED", "#3E807A", "#2B5853")
AMBER = ("#F4EEDD", "#8F7236", "#665024")
ROSE = ("#F3E9E6", "#A05E56", "#75403A")
EMER = ("#E6EFE9", "#4C7D5F", "#365844")
SLATE = ("#EDF0F3", "#5C6776", "#3B4654")
GEN = ("#F1ECDC", "#867840", "#5E522D")

RED = "#A05E56"             # muted terracotta — negative / waste
GREEN = "#4C7D5F"           # muted moss — positive / gain

# Subtle non-accent tints reused across plates.
GUIDE = "#A9A2BE"           # muted lilac for dashed reference guides
BAR = "#D9E0EA"             # pale content bars (sublines, placeholders)

# On-dark tints, for text drawn on the INKBG slab.
D_TITLE = "#9DB0C9"         # muted accent label
D_BODY = "#D2D9E2"          # body text
D_GREEN = "#8FB39B"
D_RED = "#D29A92"
D_FAINT = "#8B94A1"
D_RULE = "#33414F"          # divider on dark


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None,
       transform=None, family=None):
    """An inline text Style dict (the model accepts inline Style anywhere)."""
    s = {"font_family": family or SANS, "font_size": size, "color": color}
    if weight is not None:
        s["font_weight"] = weight
    if align is not None:
        s["align"] = align
    if spacing is not None:
        s["letter_spacing"] = spacing
    if lh is not None:
        s["line_height"] = lh
    if transform is not None:
        s["text_transform"] = transform
    return s


def header(page, H, kicker, title, *, sub=None):
    """Standard plate chrome: kicker tag, title, a thin rule, optional subtitle."""
    page.layer("bg")
    page.rect([0, 0, W, H], fill=PAPER)
    page.rect([0, 0, 6, H], fill=INDIGO[2])
    page.layer("head")
    page.text([MARGIN, 30, W - 2 * MARGIN, 14], kicker,
              style=ts(12, INDIGO[1], weight=800, spacing=2.2, transform="uppercase"))
    page.text([MARGIN, 49, W - 2 * MARGIN, 32], title,
              style=ts(25, INK, weight=800, spacing=-0.4))
    ry = 92
    if sub is not None:
        page.text([MARGIN, 86, W - 2 * MARGIN, 18], sub, style=ts(13, MUTE, lh=1.3))
        ry = 112
    page.rect([MARGIN, ry, W - 2 * MARGIN, 1.4], fill=RULE)
    page.layer("body")
    # Diagram labels are freeform annotation, not tabular data: declare them as
    # lettering so the tabular-box-model heuristic does not misread the plate as
    # an unstructured table. (Each plate uses a fresh page builder, so leaving the
    # depth raised for the page's lifetime is correct.)
    page._lettering_depth += 1
    return ry + 1


def vcenter(page, box, text, *, size, color, weight=None, family=None,
            spacing=None, align="center"):
    """Place a single line of text vertically centred in ``box``."""
    x, y, w, h = box
    page.text([x, y + (h - size) / 2.0 - 1, w, size + 5], text,
              style=ts(size, color, weight=weight, align=align, family=family,
                       spacing=spacing))


def chip(page, box, label, palette, *, size=12.5, weight=700, sub=None,
         radius=8, sw=1.6, family=None, dash=None):
    """A rounded node box with a centred (optionally two-line) label."""
    x, y, w, h = box
    fill, stroke, text = palette
    ss = {"stroke_width": sw}
    if dash is not None:
        ss["stroke_dasharray"] = dash
    page.rect([x, y, w, h], radius=radius, fill=fill, stroke=stroke, stroke_style=ss)
    if sub is not None:
        page.text([x, y + h / 2 - 16, w, 17], label,
                  style=ts(size, text, weight=weight, align="center", family=family))
        page.text([x, y + h / 2 + 2, w, 14], sub,
                  style=ts(10.5, text, align="center"))
    else:
        vcenter(page, box, label, size=size, color=text, weight=weight, family=family)


def caption(page, H, text):
    """A muted one-line takeaway pinned to the plate's bottom edge."""
    page.text([MARGIN, H - 34, W - 2 * MARGIN, 16], text,
              style=ts(12, MUTE, lh=1.35))


def measure_label(page, box, text, *, color=FAINT, size=10.5):
    """A small mono coordinate/measure label, top-left of a region."""
    x, y, w, h = box
    page.text([x, y, w, h], text, style=ts(size, color, family=MONO))


# --------------------------------------------------------------------------- #
# §0 — Absolute placement: the anatomy of one hand-placed node.
# --------------------------------------------------------------------------- #
def fig_absolute(b):
    H = 640
    page = b.page("fig-00-absolute", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    top = header(page, H, "§0 · Absolute placement",
                 "One node, placed by hand",
                 sub="Every coordinate is typed. The two “layout” helpers are really "
                     "just coordinate arithmetic — padding and a vertical stack.")

    # The node, drawn large so its inset arithmetic is legible.
    nx, ny, nw, nh = 140, 200, 520, 230
    pl, pt = 70, 56            # exaggerated padding so the inset is visible
    page.rect([nx, ny, nw, nh], radius=12, fill=BLUE[0], stroke=BLUE[1],
              stroke_style={"stroke_width": 2})
    # Content rectangle (the inset).
    cx, cy, cw, ch = inset([nx, ny, nw, nh], [pt, pl])
    page.rect([cx, cy, cw, ch], radius=6, fill="#FFFFFF", stroke=BLUE[1],
              stroke_style={"stroke_width": 1.2, "stroke_dasharray": [5, 4]})
    # Title slot + stacked sublines inside content.
    page.rect([cx, cy, cw, 22], radius=4, fill=BLUE[1])
    vcenter(page, [cx, cy, cw, 22], "title", size=12, color="#FFFFFF",
            weight=700, family=MONO)
    for i in range(3):
        ly = cy + 34 + i * 18
        page.rect([cx, ly, cw * (0.92 - i * 0.16), 11], radius=3, fill=BAR)
        page.text([cx + cw + 8, ly - 2, 150, 13],
                  f"y + 30 + {i}·14", style=ts(9.5, FAINT, family=MONO))

    # Outer coordinate annotations.
    page.text([nx, ny - 22, 320, 14], "page.rect([x, y, w, h])",
              style=ts(11, BLUE[2], weight=700, family=MONO))
    # padding-left dimension.
    page.arrow([nx, ny + nh + 18], [cx, ny + nh + 18], color=FAINT, width=1.2, head=6)
    page.arrow([cx, ny + nh + 18], [nx, ny + nh + 18], color=FAINT, width=1.2, head=6)
    page.text([nx, ny + nh + 24, 160, 13], "padding-left = x + 14",
              style=ts(10, MUTE, family=MONO))
    # padding-top dimension.
    page.arrow([nx - 18, ny], [nx - 18, cy], color=FAINT, width=1.2, head=6)
    page.arrow([nx - 18, cy], [nx - 18, ny], color=FAINT, width=1.2, head=6)
    page.text([6, ny + 22, 106, 13], "padding-top",
              style=ts(10, MUTE, align="right", family=MONO))

    # The two named facts, in a side panel.
    px = 712
    page.rect([px, 196, W - MARGIN - px, 258], radius=10, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    page.text([px + 18, 214, 280, 16], "Already a box model",
              style=ts(13.5, INK, weight=800))
    page.text([px + 18, 236, W - MARGIN - px - 36, 40],
              "x + 14 / w - 26 is padding. The inner content rectangle is "
              "[x+14, y+9, w-26, h-…].", style=ts(11.5, MUTE, lh=1.4))
    page.text([px + 18, 294, 280, 16], "Already a flow",
              style=ts(13.5, INK, weight=800))
    page.text([px + 18, 316, W - MARGIN - px - 36, 56],
              "y + 30 + i·14 is a vertical stack with a fixed 14 px line advance — "
              "a vstack whose offsets you compute by hand.",
              style=ts(11.5, MUTE, lh=1.4))
    page.text([px + 18, 388, W - MARGIN - px - 36, 56],
              "Right for a small, curated figure. Wrong when content size or count "
              "is dynamic.", style=ts(11.5, SLATE[2], lh=1.4, weight=600))

    caption(page, H, "Absolute mode is the compile target every method above it "
                     "eventually lowers to — here the inset and the stack are done by hand.")
    return H


# --------------------------------------------------------------------------- #
# §1 — The ladder of methods: who computes the coordinates?
# --------------------------------------------------------------------------- #
def fig_ladder(b):
    H = 660
    page = b.page("fig-01-ladder", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§1 · The layout problem",
           "A ladder from hand-placed to solver-placed",
           sub="Each rung trades manual control for the machine working positions "
               "out from higher-level intent.")

    # Top rung = most automatic; bottom rung = most manual.
    rungs = [
        ("Force-directed", "relax a physical system", ROSE, "a global energy"),
        ("Graph layout", "read structure, place nodes", VIOLET, "a global cost"),
        ("Constraints", "declare relations, solve", AMBER, "a feasibility region"),
        ("Grid", "tile two axes into tracks", TEAL, "a local packing rule"),
        ("Flow / Flexbox", "pack & distribute one axis", BLUE, "a local packing rule"),
        ("Box model", "named insets over absolute", BLUE, "nothing optimised"),
        ("Absolute", "you type every x, y", SLATE, "nothing optimised"),
    ]
    n = len(rungs)
    rail_x = 110
    top, step = 150, 64
    bx, bw, bh = 150, 360, 46
    for i, (name, how, pal, opt) in enumerate(rungs):
        ry = top + i * step
        chip(page, [bx, ry, bw, bh], name, pal, size=13.5, sub=how)
        # connector from rail to rung.
        page.line([rail_x, ry + bh / 2], [bx, ry + bh / 2], stroke=LINE,
                  stroke_style={"stroke_width": 1.2})

    # The vertical rail: climbing = more automation.
    rail_bottom = top + (n - 1) * step + bh
    page.arrow([rail_x, rail_bottom], [rail_x, top - 6], color=MUTE, width=1.8, head=10)
    page.text([56, top - 18, 220, 14], "machine infers intent",
              style=ts(10.5, MUTE, weight=700))
    page.text([56, rail_bottom + 8, 220, 14], "you place it by hand",
              style=ts(10.5, MUTE, weight=700))

    # Right panel — the two framing questions + the optimised ladder.
    px = 580
    pw = W - MARGIN - px
    page.rect([px, top, pw, n * step - (step - bh) + 6], radius=10, fill=PANEL,
              stroke=LINE, stroke_style={"stroke_width": 1.2})
    page.text([px + 18, top + 16, pw - 36, 16], "Two questions per rung",
              style=ts(13, INK, weight=800))
    page.text([px + 18, top + 40, pw - 36, 44],
              "Who computes the coordinates — you, by formula, or a solver from "
              "declared relations?", style=ts(11.5, MUTE, lh=1.4))
    page.text([px + 18, top + 86, pw - 36, 44],
              "What is optimised — nothing, a local rule, a global cost, or a "
              "feasibility region?", style=ts(11.5, MUTE, lh=1.4))
    page.rect([px + 18, top + 138, pw - 36, 1], fill=LINE)
    page.text([px + 18, top + 150, pw - 36, 14], "WHAT EACH RUNG OPTIMISES",
              style=ts(10.5, FAINT, weight=800, spacing=1.2))
    opt_rows = [
        ("nothing", "absolute · box model", SLATE),
        ("a local packing rule", "flow · flexbox · grid", BLUE),
        ("a feasibility region", "constraints", AMBER),
        ("a global cost / energy", "graph · force-directed", ROSE),
    ]
    for i, (what, who, pal) in enumerate(opt_rows):
        yy = top + 178 + i * 50
        page.rect([px + 18, yy, 12, 34], radius=3, fill=pal[0], stroke=pal[1],
                  stroke_style={"stroke_width": 1.4})
        page.text([px + 40, yy, pw - 60, 14], what,
                  style=ts(11.5, INK, weight=700))
        page.text([px + 40, yy + 17, pw - 60, 13], who, style=ts(10.5, MUTE))

    caption(page, H, "Same move as sdk.expand: author intent high, lower to "
                     "absolute coordinates, render that.")
    return H


# --------------------------------------------------------------------------- #
# §2 — Box model: margin -> border -> padding -> content.
# --------------------------------------------------------------------------- #
def fig_box_model(b):
    H = 600
    page = b.page("fig-02-box-model", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§2 · Box model",
           "Four nested rectangles become named space",
           sub="content = [x + p, y + p, w - 2p, h - 2p]. Once you have content(), "
               "every method below operates inside it.")

    # Concentric boxes.
    layers = [
        ("margin", [150, 160, 470, 330], PANEL, RULE),
        ("border", [196, 196, 378, 258], "#E9ECF0", FAINT),
        ("padding", [232, 230, 306, 190], EMER[0], EMER[1]),
        ("content", [276, 268, 218, 114], CARD, INDIGO[1]),
    ]
    for name, box, fill, stroke in layers:
        x, y, w, h = box
        dash = [6, 4] if name in ("margin", "padding") else None
        ss = {"stroke_width": 1.6}
        if dash:
            ss["stroke_dasharray"] = dash
        page.rect(box, radius=6, fill=fill, stroke=stroke, stroke_style=ss)
        page.text([x + 8, y + 7, 120, 13], name,
                  style=ts(10.5, MUTE, weight=700, family=MONO))
    vcenter(page, [276, 268, 218, 114], "content", size=14, color=INDIGO[2],
            weight=800)

    # Side: the inset formula made concrete (mirrors SDK layout.inset()).
    px = 690
    page.rect([px, 158, W - MARGIN - px, 196], radius=10, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    page.text([px + 16, 174, 300, 16], "inset(box, p)",
              style=ts(13, INK, weight=800, family=MONO))
    rows = [
        ("x", "box.x + p.left"),
        ("y", "box.y + p.top"),
        ("w", "box.w - p.left - p.right"),
        ("h", "box.h - p.top - p.bottom"),
    ]
    for i, (k, v) in enumerate(rows):
        yy = 204 + i * 30
        page.text([px + 16, yy, 24, 14], k, style=ts(11.5, INDIGO[2], weight=800, family=MONO))
        page.text([px + 44, yy, W - MARGIN - px - 60, 14], "= " + v,
                  style=ts(11, SLATE[2], family=MONO))
    page.text([px + 16, 326, W - MARGIN - px - 32, 14],
              "This is the SDK's own layout.inset().",
              style=ts(10.5, MUTE))

    caption(page, H, "Your node()'s asymmetric padding is exactly this — "
                     "formalising it deletes the magic numbers.")
    return H


# --------------------------------------------------------------------------- #
# §3 — Line breaking: greedy vs optimal (Knuth–Plass).
# --------------------------------------------------------------------------- #
def fig_line_breaking(b):
    H = 660
    page = b.page("fig-03-line-breaking", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§3 · Flow & line breaking",
           "Greedy fills each line; optimal balances the paragraph",
           sub="Greedy makes one ugly line to spare the next. Knuth–Plass minimises "
               "a global cost over all breakpoints by dynamic programming.")

    col_w = 380
    right = 612
    # Word widths (a fixed pseudo-paragraph), in px.
    widths = [54, 38, 72, 30, 60, 44, 90, 34, 50, 66, 40, 58, 48, 76, 32, 62,
              52, 44, 70, 36, 56, 48, 64, 40]
    space = 10

    def lay(words, x0, y0, justify):
        """Pack ``words`` (widths) greedily into lines; optionally justify."""
        lines, cur, cw = [], [], 0
        for w in words:
            adv = w if not cur else space + w
            if cw + adv > col_w and cur:
                lines.append(cur)
                cur, cw = [w], w
            else:
                cur.append(w)
                cw += adv
        if cur:
            lines.append(cur)
        for li, line in enumerate(lines):
            yy = y0 + li * 26
            natural = sum(line) + space * (len(line) - 1)
            last = li == len(lines) - 1
            gap = space
            if justify and not last and len(line) > 1:
                gap = space + (col_w - natural) / (len(line) - 1)
            xx = x0
            for w in line:
                page.rect([xx, yy, w, 14], radius=3,
                          fill=BLUE[0] if justify else PANEL,
                          stroke=(INDIGO[1] if justify else FAINT),
                          stroke_style={"stroke_width": 0.8})
                xx += w + gap
            ragged = (col_w - natural) if not last else 0
            if not justify and ragged > 6:
                page.rect([x0 + natural + 2, yy + 4, ragged - 2, 6], radius=2,
                          fill=ROSE[0])
        return len(lines)

    # Greedy column (left).
    page.text([110, 150, col_w, 16], "Greedy / first-fit",
              style=ts(13, SLATE[2], weight=800))
    page.text([110, 170, col_w, 14], "ragged right; uneven looseness",
              style=ts(10.5, MUTE))
    page.rect([110 - 10, 194, col_w + 20, 200], radius=8, fill="#FFFFFF",
              stroke=LINE, stroke_style={"stroke_width": 1.2})
    lay(widths, 110, 206, justify=False)
    page.rect([110 + col_w, 206, 2, 184], fill=ROSE[1])
    page.text([110, 404, col_w, 13], "■ wasted space the next line could have used",
              style=ts(9.5, RED))

    # Optimal column (right).
    page.text([right, 150, col_w, 16], "Optimal / Knuth–Plass",
              style=ts(13, INDIGO[2], weight=800))
    page.text([right, 170, col_w, 14], "flush edges; even inter-word glue",
              style=ts(10.5, MUTE))
    page.rect([right - 10, 194, col_w + 20, 200], radius=8, fill="#FFFFFF",
              stroke=INDIGO[1], stroke_style={"stroke_width": 1.4})
    lay(widths, right, 206, justify=True)
    page.rect([right + col_w, 206, 2, 184], fill=INDIGO[1])

    # The cost shape, as a small inset (badness ~ 100·|r|³).
    page.text([110, 432, 500, 14], "Per-line cost grows steeply with the stretch ratio r:",
              style=ts(11, SLATE[2], weight=600))
    fr = Frame(domain=(-1, 0, 1, 100), box=(118, 456, 360, 124))
    ch = (Chart(fr)
          .axes(x_ticks=[-1, -0.5, 0, 0.5, 1], y_ticks=[0, 50, 100],
                x_format=lambda v: f"{v:g}", y_format=lambda v: f"{v:g}",
                grid=True, axis_color=FAINT, grid_color="#EDEFF4",
                label_style={"class": "_axis"})
          .line([(r / 20.0, min(100, 100 * abs(r / 20.0) ** 3))
                 for r in range(-20, 21)], stroke=INDIGO[1], width=2.5, smooth=True))
    page.extend(ch.objects())
    page.text([496, 466, 280, 40],
              "badness b ~ 100·|r|³,\nr = (desired - natural) / stretch",
              style=ts(11, MUTE, lh=1.5, family=MONO))
    page.text([496, 524, 320, 50],
              "Total demerits Σ(linePenalty + b)² are minimised as a shortest "
              "path over feasible breakpoints.", style=ts(10.5, MUTE, lh=1.4))

    caption(page, H, "Greedy for labels and captions; Knuth–Plass when justified, "
                     "print-quality multi-line typography matters.")
    return H


# --------------------------------------------------------------------------- #
# §4 — Flexbox: distribute the leftover space along one axis.
# --------------------------------------------------------------------------- #
def fig_flexbox(b):
    H = 620
    page = b.page("fig-04-flexbox", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§4 · Stack / Flexbox",
           "Lay items along an axis, distribute the surplus",
           sub="free = container - Σ basis. Each item grows by its share "
               "grow / Σgrow of that free space.")

    cont_x, cont_w = 110, 760
    basis = [150, 110, 200, 90]
    grow = [1, 0, 2, 1]
    labels = ["basis 150\ngrow 1", "basis 110\ngrow 0", "basis 200\ngrow 2",
              "basis 90\ngrow 1"]
    gap = 14
    total_basis = sum(basis)

    # Row A — natural (basis only): leaves visible free space.
    ya = 170
    page.text([cont_x, ya - 22, 400, 14], "Natural sizes (basis only)",
              style=ts(12, SLATE[2], weight=700))
    page.rect([cont_x, ya, cont_w, 70], radius=8, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    xx = cont_x + 10
    for i, ban in enumerate(basis):
        chip(page, [xx, ya + 12, ban, 46], f"{ban}", BLUE, size=13)
        xx += ban + gap
    free_x = xx
    free_w = cont_x + cont_w - 10 - free_x
    if free_w > 4:
        page.rect([free_x, ya + 12, free_w, 46], radius=6, fill=AMBER[0],
                  stroke=AMBER[1], stroke_style={"stroke_width": 1.2,
                                                  "stroke_dasharray": [5, 4]})
        vcenter(page, [free_x, ya + 12, free_w, 46], "free", size=11,
                color=AMBER[2], weight=700)

    # Row B — after grow: free space distributed by grow weight.
    yb = 320
    page.text([cont_x, yb - 22, 400, 14], "After flex-grow (surplus distributed)",
              style=ts(12, INDIGO[2], weight=700))
    page.rect([cont_x, yb, cont_w, 70], radius=8, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    inner = cont_w - 20 - gap * (len(basis) - 1)
    free = inner - total_basis
    tg = sum(grow) or 1
    sizes = [ban + (g / tg) * free for ban, g in zip(basis, grow)]
    xx = cont_x + 10
    for i, sz in enumerate(sizes):
        pal = INDIGO if grow[i] > 0 else SLATE
        chip(page, [xx, yb + 12, sz, 46], labels[i].split("\n")[0], pal,
             size=12, sub=labels[i].split("\n")[1])
        if grow[i] > 0:
            add = sz - basis[i]
            page.text([xx, yb + 64, sz, 12], f"+{add:.0f}px",
                      style=ts(9.5, GREEN, weight=700, align="center"))
        xx += sz + gap

    # Axis legend.
    page.arrow([cont_x, 430], [cont_x + 260, 430], color=MUTE, width=1.4, head=8)
    page.text([cont_x, 436, 260, 13], "main axis (items flow)",
              style=ts(10.5, MUTE))
    page.arrow([cont_x + 320, 414], [cont_x + 320, 458], color=FAINT, width=1.4, head=8)
    page.text([cont_x + 332, 430, 200, 13], "cross axis (align)",
              style=ts(10.5, FAINT))

    # Formula panel.
    px = 716
    page.rect([px, 430, W - MARGIN - px, 132], radius=10, fill=INKBG,
              stroke=INKBG, stroke_style={"stroke_width": 1})
    page.text([px + 16, 444, 300, 14], "surplus", style=ts(10.5, D_TITLE,
              weight=800, transform="uppercase", spacing=1))
    page.text([px + 16, 462, W - MARGIN - px - 32, 14],
              "size = basis + (grow/Σgrow)·free", style=ts(11.5, D_BODY, family=MONO))
    page.text([px + 16, 494, 300, 14], "deficit", style=ts(10.5, D_RED,
              weight=800, transform="uppercase", spacing=1))
    page.text([px + 16, 512, W - MARGIN - px - 32, 28],
              "size = basis + (shrink·basis / Σshrink·basis)·free",
              style=ts(10.5, D_RED, family=MONO, lh=1.3))

    caption(page, H, "Your gate list, legend and tension band are fixed-stride "
                     "vstacks — a flex column with gap and no grow.")
    return H


# --------------------------------------------------------------------------- #
# §5 — Grid: tracks on two axes, and the gen_rows offsets.
# --------------------------------------------------------------------------- #
def fig_grid(b):
    H = 640
    page = b.page("fig-05-grid", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§5 · Grid / table",
           "Tile two axes into tracks — then place into cells",
           sub="fr tracks distribute leftover space exactly like flex-grow. "
               "Resolving track positions is the gen_rows your map writes by hand.")

    # Left: a real 3×3-ish grid laid out by the SDK's grid() helper.
    gx, gy, gw, gh = 110, 168, 360, 300
    page.rect([gx - 12, gy - 12, gw + 24, gh + 24], radius=10, fill=PANEL,
              stroke=LINE, stroke_style={"stroke_width": 1.2})
    cells = grid([gx, gy, gw, gh], cols=3, count=8, gap=14)
    # Cells 1–8 carry no semantic difference, so they take one calm accent:
    # the grid's regularity reads from geometry, not from eight competing hues.
    for i, cell in enumerate(cells):
        chip(page, cell, f"{i + 1}", INDIGO, size=13)
    page.text([gx - 12, gy + gh + 20, gw + 24, 14],
              "grid(box, cols=3, count=8, gap=14)  — row-major cells",
              style=ts(10.5, MUTE, family=MONO))

    # Right: the 1-column grid your gen_rows writes longhand.
    tx = 560
    page.text([tx, 150, 460, 16], "Your gen_rows is a 1-column grid, longhand",
              style=ts(13, INK, weight=800))
    rows_y = [124, 174, 224, 274, 324, 374]      # the file's hand-typed values
    base = 196
    scale = 0.62
    labels = ["schema/…json", "grammar/*.ebnf", "spec/…md", "docs/ (MkDocs)",
              "FIXTURE-STATUS", "viewer/ types"]
    for i, yv in enumerate(rows_y):
        yy = base + i * int(42 * scale + 8 * scale)
        bh = int(42 * scale)
        chip(page, [tx, yy, 300, bh], labels[i], GEN, size=11)
        page.text([tx + 312, yy + bh / 2 - 7, 150, 13],
                  f"y = {yv}", style=ts(11, FAINT, family=MONO))

    # The equality that is the whole lesson.
    page.rect([tx, 466, 460, 96], radius=10, fill=INKBG)
    page.text([tx + 16, 480, 440, 14], "trackOffsets(Array(6).fill(42), 8, 124)",
              style=ts(11, D_TITLE, family=MONO))
    page.text([tx + 16, 504, 440, 14], "-> [124, 174, 224, 274, 324, 374]",
              style=ts(11.5, D_BODY, family=MONO, weight=700))
    page.text([tx + 16, 530, 440, 24],
              "identical to the hand-typed y values — a 7th view would cost zero "
              "arithmetic.", style=ts(10.5, D_FAINT, lh=1.35))

    caption(page, H, "Grid beats flex for genuine 2D alignment; flex beats grid "
                     "for a single axis with content-driven distribution.")
    return H


# --------------------------------------------------------------------------- #
# §6 — Constraint-based layout (Cassowary).
# --------------------------------------------------------------------------- #
def fig_constraints(b):
    H = 620
    page = b.page("fig-06-constraints", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§6 · Constraint-based (Cassowary)",
           "Declare relations; a solver finds the positions",
           sub="The model behind Auto Layout. Constraints carry strengths — "
               "required must hold; strong/medium/weak resolve slack and conflicts.")

    # The three boxes: renderer centred above two equal services.
    svcL = [150, 360, 200, 70]
    svcR = [430, 360, 200, 70]
    rend = [230, 210, 320, 70]
    chip(page, rend, "renderer", VIOLET, size=13, sub="centered over the two services")
    chip(page, svcL, "service · left", SLATE, size=12.5)
    chip(page, svcR, "service · right", SLATE, size=12.5)

    # Constraint annotations.
    # centerX equality: a dashed guide on the shared centre axis, drawn *below*
    # the renderer box (down through the gap between the services) so it never
    # crosses the renderer's caption.
    midx = (svcL[0] + (svcR[0] + svcR[2])) / 2
    page.rect([midx - 0.75, 286, 1.5, 158], fill=GUIDE,
              stroke_style={"stroke_dasharray": [4, 4]})
    page.text([midx + 6, 300, 220, 26],
              "renderer.centerX ==\n(L.right + R.left) / 2", style=ts(10, VIOLET[2],
              family=MONO, lh=1.3))
    # gap >= 16 between the two services.
    page.arrow([svcL[0] + svcL[2], 432], [svcR[0], 432], color=AMBER[1], width=1.3, head=6)
    page.arrow([svcR[0], 432], [svcL[0] + svcL[2], 432], color=AMBER[1], width=1.3, head=6)
    page.text([svcL[0] + svcL[2] + 4, 438, 200, 13], "gap >= 16   required",
              style=ts(10, AMBER[2], family=MONO))
    # equal width.
    page.text([svcL[0], 446, 200, 13], "L.width == R.width",
              style=ts(10, SLATE[2], family=MONO))

    # Strengths panel.
    px = 700
    page.rect([px, 168, W - MARGIN - px, 250], radius=10, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    page.text([px + 16, 184, 300, 16], "Constraint strengths",
              style=ts(13, INK, weight=800))
    strengths = [
        ("required", ROSE, "must hold — hard"),
        ("strong", AMBER, "honoured first when slack"),
        ("medium", BLUE, "next in priority order"),
        ("weak", SLATE, "last; breaks first"),
    ]
    for i, (name, pal, desc) in enumerate(strengths):
        yy = 214 + i * 42
        chip(page, [px + 16, yy, 96, 30], name, pal, size=11.5)
        page.text([px + 122, yy + 8, W - MARGIN - px - 138, 14], desc,
                  style=ts(10.5, MUTE))
    page.text([px + 16, 392, W - MARGIN - px - 32, 14],
              "Solved incrementally — editing one constraint re-solves cheaply.",
              style=ts(10, FAINT, lh=1.3))

    caption(page, H, "Worth it for a resizable interactive canvas; rarely worth the "
                     "solver dependency for a static one-page export.")
    return H


# --------------------------------------------------------------------------- #
# §7a — Tree layout (Reingold–Tilford).
# --------------------------------------------------------------------------- #
def fig_tree(b):
    H = 600
    page = b.page("fig-07a-tree", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§7a · Tree layout",
           "Reingold–Tilford: parents centred, depths aligned",
           sub="Nodes at the same depth share a line; a parent is centred over its "
               "children; contours keep subtrees from colliding in linear time.")

    # A small tree: positions chosen to satisfy the aesthetic rules.
    nodes = {
        "r":  (430, 168),
        "a":  (250, 280), "b": (610, 280),
        "a1": (160, 392), "a2": (340, 392),
        "b1": (520, 392), "b2": (610, 392), "b3": (700, 392),
        "a11": (120, 500), "a12": (210, 500),
    }
    edges = [("r", "a"), ("r", "b"), ("a", "a1"), ("a", "a2"),
             ("b", "b1"), ("b", "b2"), ("b", "b3"),
             ("a1", "a11"), ("a1", "a12")]
    # Depth guide lines (labels on the left so the side panel never covers them).
    for dy, lab in [(168, "depth 0"), (280, "depth 1"), (392, "depth 2"),
                    (500, "depth 3")]:
        page.rect([96, dy + 16, 604, 1], fill=LINE)
        page.text([8, dy + 10, 80, 13], lab,
                  style=ts(9.5, FAINT, family=MONO, align="right"))
    # Edges.
    for u, v in edges:
        x1, y1 = nodes[u]
        x2, y2 = nodes[v]
        page.line([x1, y1 + 16], [x2, y2 - 16], stroke=RULE,
                  stroke_style={"stroke_width": 1.4})
    # Contour silhouettes (left/right) of subtree a.
    page.polyline([[150, 296], [110, 408], [110, 516]], stroke=GUIDE,
                  stroke_style={"stroke_width": 1.4, "stroke_dasharray": [5, 4]},
                  fill="none")
    page.polyline([[350, 296], [355, 408], [225, 516]], stroke=GUIDE,
                  stroke_style={"stroke_width": 1.4, "stroke_dasharray": [5, 4]},
                  fill="none")
    page.text([96, 470, 120, 13], "contour", style=ts(9.5, VIOLET[1], family=MONO))
    # Nodes (draw last, on top).
    for k, (cx, cy) in nodes.items():
        page.circle([cx, cy], 16, fill=VIOLET[0], stroke=VIOLET[1],
                    stroke_style={"stroke_width": 1.8})
    # "parent centred over children" marker on r over a,b.
    page.rect([430 - 0.75, 184, 1.5, 80], fill=GUIDE,
              stroke_style={"stroke_dasharray": [3, 3]})
    page.text([442, 222, 200, 13], "centred over its children",
              style=ts(10, VIOLET[2]))

    # Side note.
    px = 720
    page.rect([px, 168, W - MARGIN - px, 150], radius=10, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    page.text([px + 16, 184, 280, 14], "Aesthetic rules",
              style=ts(12.5, INK, weight=800))
    for i, t in enumerate(["same depth -> same line", "parent centred on children",
                           "isomorphic subtrees drawn alike", "as narrow as those allow"]):
        page.text([px + 16, 210 + i * 24, W - MARGIN - px - 32, 14], "•  " + t,
                  style=ts(10.5, MUTE))

    caption(page, H, "Walker generalised it to n-ary trees; Buchheim–Jünger–Leipert "
                     "restored linear time. Reach for it on strict hierarchies.")
    return H


# --------------------------------------------------------------------------- #
# §7b — Layered / hierarchical layout (Sugiyama).
# --------------------------------------------------------------------------- #
def fig_sugiyama(b):
    H = 620
    page = b.page("fig-07b-sugiyama", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§7b · Layered layout (Sugiyama)",
           "Rank the nodes, then minimise crossings",
           sub="The standard for a directed acyclic graph with a sense of flow — "
               "which is what an architecture map structurally is.")

    # Four ranks; nodes ordered to minimise crossings; one dummy node.
    layers_y = [180, 290, 400, 510]
    ranks = [["A"], ["B", "C"], ["D", "E", "F"], ["G", "H"]]
    pos = {}
    xs = {
        "A": [430], "B": [300, 560], "C": None,
        "D": [200, 430, 660], "G": [330, 560],
    }
    coords = {
        "A": (430, 180),
        "B": (300, 290), "C": (560, 290),
        "D": (200, 400), "E": (430, 400), "F": (660, 400),
        "G": (330, 510), "H": (560, 510),
    }
    dummy = (430, 290)       # a dummy node on a long A->E edge
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("B", "E"),
             ("C", "E"), ("C", "F"), ("D", "G"), ("E", "G"),
             ("E", "H"), ("F", "H")]
    # Layer bands + labels.
    band_labels = ["rank 0", "rank 1", "rank 2", "rank 3"]
    for i, ly in enumerate(layers_y):
        page.rect([96, ly - 26, 584, 52], radius=8, fill=PANEL if i % 2 else "#FFFFFF",
                  stroke=LINE, stroke_style={"stroke_width": 1})
        page.text([8, ly - 6, 80, 13], band_labels[i],
                  style=ts(9.5, FAINT, family=MONO, align="right"))
    # Long edge A->E routed through a dummy node.
    page.line([430, 196], [dummy[0], dummy[1] - 8], stroke=RULE,
              stroke_style={"stroke_width": 1.3, "stroke_dasharray": [4, 3]})
    page.line([dummy[0], dummy[1] + 8], [430, 384], stroke=RULE,
              stroke_style={"stroke_width": 1.3, "stroke_dasharray": [4, 3]})
    page.circle([dummy[0], dummy[1]], 6, fill=CARD, stroke=RULE,
                stroke_style={"stroke_width": 1.2})
    page.text([dummy[0] + 12, dummy[1] - 7, 120, 13], "dummy node",
              style=ts(9, FAINT, family=MONO))
    # Real edges.
    for u, v in edges:
        if (u, v) == ("A", "E"):
            continue
        x1, y1 = coords[u]
        x2, y2 = coords[v]
        page.line([x1, y1 + 18], [x2, y2 - 18], stroke=BLUE[1],
                  stroke_style={"stroke_width": 1.4})
    # Nodes.
    for k, (cx, cy) in coords.items():
        page.circle([cx, cy], 18, fill=BLUE[0], stroke=BLUE[1],
                    stroke_style={"stroke_width": 1.8})
        vcenter(page, [cx - 18, cy - 18, 36, 36], k, size=12, color=BLUE[2], weight=800)

    # Four phases panel.
    px = 700
    page.rect([px, 170, W - MARGIN - px, 200], radius=10, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    page.text([px + 16, 186, 280, 14], "Four phases", style=ts(12.5, INK, weight=800))
    phases = ["1 · remove cycles", "2 · assign layers (ranks)",
              "3 · minimise crossings", "4 · assign x, route edges"]
    for i, t in enumerate(phases):
        page.text([px + 16, 214 + i * 34, W - MARGIN - px - 32, 14], t,
                  style=ts(11, SLATE[2], weight=600))

    caption(page, H, "Graphviz dot implements a variant. It optimises a geometric "
                     "objective — not your semantic one (governance bottom-left).")
    return H


# --------------------------------------------------------------------------- #
# §7c — Force-directed layout.
# --------------------------------------------------------------------------- #
def fig_force(b):
    H = 620
    page = b.page("fig-07c-force", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§7c · Force-directed",
           "Nodes repel, edges pull — the system relaxes",
           sub="No inherent hierarchy: simulate physics and let clusters emerge as "
               "the layout settles toward low energy.")

    # Two emergent clusters.
    nodes = {
        "n1": (250, 250), "n2": (330, 200), "n3": (310, 320), "n4": (210, 340),
        "n5": (560, 260), "n6": (640, 210), "n7": (650, 330), "n8": (560, 360),
        "n9": (430, 460),
    }
    edges = [("n1", "n2"), ("n1", "n3"), ("n2", "n3"), ("n3", "n4"), ("n1", "n4"),
             ("n5", "n6"), ("n6", "n7"), ("n7", "n8"), ("n5", "n8"), ("n5", "n7"),
             ("n3", "n9"), ("n8", "n9")]
    for u, v in edges:
        x1, y1 = nodes[u]
        x2, y2 = nodes[v]
        page.line([x1, y1], [x2, y2], stroke=RULE, stroke_style={"stroke_width": 1.4})
    for k, (cx, cy) in nodes.items():
        page.circle([cx, cy], 13, fill=ROSE[0], stroke=ROSE[1],
                    stroke_style={"stroke_width": 1.8})
    # Spring (attractive) force on one edge.
    page.arrow([300, 250], [318, 210], color=GREEN, width=1.6, head=7)
    page.arrow([318, 210], [300, 250], color=GREEN, width=1.6, head=7)
    page.text([250, 168, 160, 13], "spring  f_a = d²/k", style=ts(10, GREEN, family=MONO))
    # Repulsion between clusters.
    page.arrow([430, 300], [360, 300], color=RED, width=1.6, head=7)
    page.arrow([430, 300], [500, 300], color=RED, width=1.6, head=7)
    page.text([372, 280, 200, 13], "repulsion  f_r = -k²/d",
              style=ts(10, RED, family=MONO))

    # Formula panel.
    px = 712
    page.rect([px, 170, W - MARGIN - px, 230], radius=10, fill=INKBG)
    page.text([px + 16, 184, 300, 14], "Fruchterman–Reingold",
              style=ts(12, D_RED, weight=800))
    page.text([px + 16, 208, W - MARGIN - px - 32, 14], "ideal length  k = C·sqrt(area/|V|)",
              style=ts(10.5, D_BODY, family=MONO))
    page.text([px + 16, 230, W - MARGIN - px - 32, 14], "attract  f_a(d) = d²/k",
              style=ts(10.5, D_GREEN, family=MONO))
    page.text([px + 16, 252, W - MARGIN - px - 32, 14], "repel   f_r(d) = -k²/d",
              style=ts(10.5, D_RED, family=MONO))
    page.text([px + 16, 282, W - MARGIN - px - 32, 14], "cool displacement each step",
              style=ts(10, D_FAINT))
    page.rect([px + 16, 308, W - MARGIN - px - 32, 1], fill=D_RULE)
    page.text([px + 16, 318, W - MARGIN - px - 32, 14], "Kamada–Kawai: minimise stress",
              style=ts(10.5, D_TITLE, weight=700))
    page.text([px + 16, 340, W - MARGIN - px - 32, 28],
              "E = Σ (1/d_ij²)(‖pᵢ-pⱼ‖ - d_ij)²", style=ts(10.5, D_BODY,
              family=MONO, lh=1.3))
    page.text([px + 16, 372, W - MARGIN - px - 32, 14],
              "Barnes–Hut -> O(n log n)", style=ts(10, D_FAINT))

    caption(page, H, "For exploratory networks (dependency clouds, social graphs) — "
                     "not a deliberately composed figure.")
    return H


# --------------------------------------------------------------------------- #
# §7d — Edge routing.
# --------------------------------------------------------------------------- #
def fig_edge_routing(b):
    H = 560
    page = b.page("fig-07d-edge-routing", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§7d · Edge routing",
           "Independent of node placement: how the wire is drawn",
           sub="Once nodes are positioned, the same pair of endpoints can be wired "
               "three different ways.")

    panels = row([90, 200, W - 180, 280], count=3, gap=40)
    titles = ["Straight", "Orthogonal (Manhattan)", "Spline (obstacle-avoiding)"]
    notes = ["sparse, curated figures", "UML, circuit diagrams", "what dot produces"]
    for i, (pbox, title) in enumerate(zip(panels, titles)):
        x, y, w, h = pbox
        page.rect([x, y, w, h], radius=10, fill=PANEL, stroke=LINE,
                  stroke_style={"stroke_width": 1.2})
        page.text([x + 14, y + 12, w - 28, 14], title, style=ts(12.5, INK, weight=800))
        page.text([x + 14, y + 32, w - 28, 13], notes[i], style=ts(10, MUTE))
        # endpoints
        a = [x + 40, y + 90]
        bb = [x + w - 40, y + h - 56]
        # an obstacle box in the middle
        obs = [x + w / 2 - 34, y + 120, 68, 40]
        page.rect(obs, radius=5, fill="#FFFFFF", stroke=FAINT,
                  stroke_style={"stroke_width": 1, "stroke_dasharray": [4, 3]})
        col = [BLUE[1], AMBER[1], VIOLET[1]][i]
        if i == 0:
            page.arrow(a, bb, color=col, width=1.8, head=9)
        elif i == 1:
            midx = x + 40
            page.line(a, [a[0], bb[1]], stroke=col, stroke_style={"stroke_width": 1.8})
            page.arrow([a[0], bb[1]], bb, color=col, width=1.8, head=9)
        else:
            page.polyline([a, [x + w / 2 - 70, y + 110], [x + w / 2 + 70, y + h - 90], bb],
                          smooth=True, stroke=col, fill="none",
                          stroke_style={"stroke_width": 1.8})
            page.arrow([bb[0] - 18, bb[1] - 10], bb, color=col, width=1.8, head=9)
        for p in (a, bb):
            page.circle(p, 8, fill=col)

    caption(page, H, "Your arrows are hand-routed straight segments — fine for a "
                     "sparse figure; automation removes the by-eye collision checking.")
    return H


# --------------------------------------------------------------------------- #
# §8 — Space-filling: slice-and-dice vs squarified treemaps.
# --------------------------------------------------------------------------- #
def fig_treemap(b):
    H = 600
    page = b.page("fig-08-treemap", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§8 · Space-filling (treemaps)",
           "Show quantity by area inside a bounded region",
           sub="Both panels encode the same values. Squarified keeps cells near "
               "square, so areas are easier to compare and label.")

    values = [9, 7, 5, 4, 3, 3, 2, 2]
    total = sum(values)

    # One sequential hue: bigger value -> darker cell. Area already carries the
    # quantity; a single-hue ramp reinforces it instead of letting eight competing
    # identities imply a categorical difference that is not there.
    RAMP = [
        ("#EEF2F7", "#9FB3C9"),
        ("#DBE6F1", "#7C97B7"),
        ("#C6D8EA", "#5E7CA1"),
        ("#AEC6DF", "#46658C"),
        ("#94B1D2", "#345379"),
    ]
    vlo, vhi = min(values), max(values)

    def shade(v):
        idx = (len(RAMP) - 1 if vhi == vlo
               else round((v - vlo) / (vhi - vlo) * (len(RAMP) - 1)))
        return RAMP[idx]

    # Left: slice-and-dice (alternating splits -> thin slivers).
    lx, ly, lw, lh = 110, 178, 340, 300
    page.text([lx, 152, lw, 14], "Slice-and-dice", style=ts(12.5, SLATE[2], weight=800))
    # First split horizontally by the first 2 vs rest, then vertical, etc. — but to
    # show slivers clearly, just slice the whole height into vertical strips by value.
    xx = lx
    for i, v in enumerate(values):
        wv = lw * v / total
        sf, ss = shade(v)
        page.rect([xx, ly, wv - 3, lh], radius=3, fill=sf, stroke=ss,
                  stroke_style={"stroke_width": 1.2})
        # Label every cell, including the thin v=2 slivers (a smaller, centred
        # digit fits even a ~16px strip) so both panels visibly carry all eight.
        fs = 10 if wv > 26 else 8.5
        page.text([xx, ly + lh - 17, max(wv - 3, 8), 12], str(v),
                  style=ts(fs, BLUE[2], weight=700, align="center"))
        xx += wv
    page.text([lx, ly + lh + 12, lw, 13], "thin slivers — hard to compare",
              style=ts(10, RED))

    # Right: squarified (greedy near-square rows).
    rx, ry, rw, rh = 620, 178, 340, 300
    page.text([rx, 152, rw, 14], "Squarified", style=ts(12.5, INDIGO[2], weight=800))
    # A hand-built squarified-style packing of the same values.
    region = [rx, ry, rw, rh]
    cells = _squarify(values, region)
    for i, (cell, v) in enumerate(zip(cells, values)):
        x, y, w, h = cell
        sf, ss = shade(v)
        page.rect([x, y, w - 3, h - 3], radius=4, fill=sf, stroke=ss,
                  stroke_style={"stroke_width": 1.4})
        vcenter(page, [x, y, w - 3, h - 3], str(v), size=13, color=BLUE[2], weight=800)
    page.text([rx, ry + rh + 12, rw, 13], "near-square cells — easy to read",
              style=ts(10, GREEN))

    caption(page, H, "Not for connection structure — for “show proportions in a "
                     "box.” Other space-fillers: circle packing, Voronoi treemaps.")
    return H


def _squarify(values, region):
    """A compact squarified treemap (Bruls–Huizing–van Wijk), enough for a figure."""
    x, y, w, h = region
    total = sum(values)
    scale = (w * h) / total
    areas = [v * scale for v in values]
    cells = []
    i = 0
    while i < len(areas):
        # Grow a row while aspect ratios improve.
        short = min(w, h)
        row_areas = [areas[i]]
        j = i + 1

        def worst(r, length):
            s = sum(r)
            mx, mn = max(r), min(r)
            return max((length * length * mx) / (s * s), (s * s) / (length * length * mn))

        while j < len(areas) and worst(row_areas + [areas[j]], short) <= worst(row_areas, short):
            row_areas.append(areas[j])
            j += 1
        s = sum(row_areas)
        if w <= h:
            # lay the row across the top (a horizontal band)
            band_h = s / w
            xx = x
            for a in row_areas:
                cw = a / band_h
                cells.append([xx, y, cw, band_h])
                xx += cw
            y += band_h
            h -= band_h
        else:
            band_w = s / h
            yy = y
            for a in row_areas:
                chh = a / band_w
                cells.append([x, yy, band_w, chh])
                yy += chh
            x += band_w
            w -= band_w
        i = j
    return cells


# --------------------------------------------------------------------------- #
# §9 — Choosing a method (decision map).
# --------------------------------------------------------------------------- #
def fig_decision(b):
    H = 660
    page = b.page("fig-09-decision", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§9 · Choosing a method",
           "Can you name the structure?",
           sub="If you can name it — tree, DAG, network, proportion — use the "
               "matching algorithm. If the value is human curation, stay absolute.")

    # Root question.
    root = [410, 150, 280, 50]
    chip(page, root, "Name the structure?", INDIGO, size=13)

    # Branch A: structural -> method rows.
    page.arrow([460, 200], [300, 244], color=MUTE, width=1.4, head=8)
    page.arrow([640, 200], [820, 244], color=MUTE, width=1.4, head=8)
    page.text([300, 224, 200, 13], "yes — it has a name",
              style=ts(10, MUTE, weight=600))
    page.text([700, 224, 200, 13], "no — value is curation",
              style=ts(10, MUTE, weight=600, align="right"))

    pairs = [
        ("strict hierarchy", "Tree — Reingold–Tilford", VIOLET),
        ("directed flow / DAG", "Layered — Sugiyama / dot", BLUE),
        ("network, no hierarchy", "Force-directed", ROSE),
        ("quantity by area", "Treemap / packing", TEAL),
        ("wrap a label", "Greedy flow", SLATE),
        ("justified body text", "Knuth–Plass", SLATE),
    ]
    lx = 90
    for i, (cond, method, pal) in enumerate(pairs):
        yy = 256 + i * 56
        chip(page, [lx, yy, 230, 42], cond, SLATE, size=11.5)
        page.arrow([lx + 230, yy + 21], [lx + 276, yy + 21], color=FAINT, width=1.3, head=7)
        chip(page, [lx + 276, yy, 250, 42], method, pal, size=11.5)

    # Branch B: curation -> absolute + borrow.
    bx = 690
    page.rect([bx, 256, W - MARGIN - bx, 300], radius=12, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.3})
    page.text([bx + 18, 274, 280, 16], "Human-curated figure",
              style=ts(13.5, INK, weight=800))
    page.text([bx + 18, 298, W - MARGIN - bx - 36, 40],
              "Grouping and emphasis carry the meaning — your architecture map.",
              style=ts(11, MUTE, lh=1.4))
    chip(page, [bx + 18, 346, W - MARGIN - bx - 36, 44], "Absolute placement", INDIGO,
         size=13)
    page.text([bx + 18, 404, W - MARGIN - bx - 36, 16], "…and borrow the cheap parts:",
              style=ts(11, SLATE[2], weight=600))
    for i, t in enumerate(["a box model (inset)", "a vstack / column", "a grid offset helper"]):
        page.text([bx + 18, 428 + i * 26, W - MARGIN - bx - 36, 14], "•  " + t,
                  style=ts(11, MUTE))
    page.text([bx + 18, 514, W - MARGIN - bx - 36, 30],
              "— just to delete magic numbers, not to surrender the composition.",
              style=ts(10.5, FAINT, lh=1.35))

    caption(page, H, "Automatic layout optimises a geometric objective; curation "
                     "optimises a semantic one. Match the tool to which matters.")
    return H


# --------------------------------------------------------------------------- #
# §10 — One rung up: author high, lower to absolute, render.
# --------------------------------------------------------------------------- #
def fig_lowering(b):
    H = 580
    page = b.page("fig-10-lowering", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§10 · One concrete rung up",
           "A thin primitive layer that lowers to absolute",
           sub="Mirrors how sdk.expand lowers builders into the model: author "
               "intent high, lower to one canonical representation, render that.")

    stages = row([80, 230, W - 160, 210], count=3, gap=56)
    # Stage 1 — author intent.
    s1 = stages[0]
    x, y, w, h = s1
    chip(page, [x, y, w, 42], "Author intent", INDIGO, size=13)
    page.rect([x, y + 56, w, h - 56], radius=10, fill=INKBG)
    page.text([x + 14, y + 70, w - 28, 14], "vstack(page, origin,",
              style=ts(11, D_TITLE, family=MONO))
    page.text([x + 14, y + 88, w - 28, 14], "  items, gap=8)",
              style=ts(11, D_BODY, family=MONO))
    page.text([x + 14, y + 114, w - 28, 14], "grid_offsets(124,",
              style=ts(11, D_TITLE, family=MONO))
    page.text([x + 14, y + 132, w - 28, 14], "  6, 42, 8)",
              style=ts(11, D_BODY, family=MONO))

    # Stage 2 — lower.
    s2 = stages[1]
    x, y, w, h = s2
    chip(page, [x, y, w, 42], "Lower (expand)", VIOLET, size=13)
    page.rect([x, y + 56, w, h - 56], radius=10, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    page.text([x + 14, y + 72, w - 28, 16], "compile to the calls",
              style=ts(11.5, SLATE[2], weight=600))
    page.text([x + 14, y + 92, w - 28, 16], "you write by hand",
              style=ts(11.5, SLATE[2], weight=600))
    page.text([x + 14, y + 124, w - 28, 14], "[124,174,224,",
              style=ts(11, MUTE, family=MONO))
    page.text([x + 14, y + 142, w - 28, 14], " 274,324,374]",
              style=ts(11, MUTE, family=MONO))

    # Stage 3 — render (absolute): the six cards the lowered offsets place, each
    # labelled with the y the lowering emitted — so the render visibly realises
    # the [124, 174, …, 374] list produced one stage to the left.
    s3 = stages[2]
    x, y, w, h = s3
    chip(page, [x, y, w, 42], "Render", TEAL, size=13)
    page.rect([x, y + 56, w, h - 56], radius=10, fill=PANEL, stroke=LINE,
              stroke_style={"stroke_width": 1.2})
    inner = inset([x, y + 56, w, h - 56], 12)
    offsets = [124, 174, 224, 274, 324, 374]
    cards = column([inner[0], inner[1], inner[2], inner[3]], count=len(offsets), gap=6)
    for c, off in zip(cards, offsets):
        cx, cy, cw, ch = c
        page.rect([cx, cy, cw, ch], radius=4, fill=TEAL[0], stroke=TEAL[1],
                  stroke_style={"stroke_width": 1.2})
        vcenter(page, [cx + 10, cy, 70, ch], f"y = {off}", size=9.5,
                color=TEAL[2], family=MONO, align="left")
        page.rect([cx + cw - 46, cy + ch / 2 - 3.5, 34, 7], radius=2, fill="#99F6E4")

    # Arrows between stages.
    for a, bb in ((stages[0], stages[1]), (stages[1], stages[2])):
        ax = a[0] + a[2]
        bx = bb[0]
        cy = a[1] + 21
        page.arrow([ax + 8, cy], [bx - 8, cy], color=MUTE, width=1.8, head=9)

    page.rect([80, 472, W - 160, 56], radius=10, fill=EMER[0], stroke=EMER[1],
              stroke_style={"stroke_width": 1.2})
    page.text([98, 484, W - 196, 16],
              "Absolute mode stays the compile target — the golden SHA-256 page "
              "locks still apply deterministically.", style=ts(12, EMER[2], weight=600))
    page.text([98, 506, W - 196, 14],
              "The brittle arithmetic is gone; a 7th view or an extra gate costs zero edits.",
              style=ts(11, EMER[2]))

    caption(page, H, "The same architectural principle the codebase already trusts: "
                     "author high, lower to one representation, render that.")
    return H


# --------------------------------------------------------------------------- #
# Build + emit.
# --------------------------------------------------------------------------- #
FIGURES = [
    ("fig-00-absolute", fig_absolute),
    ("fig-01-ladder", fig_ladder),
    ("fig-02-box-model", fig_box_model),
    ("fig-03-line-breaking", fig_line_breaking),
    ("fig-04-flexbox", fig_flexbox),
    ("fig-05-grid", fig_grid),
    ("fig-06-constraints", fig_constraints),
    ("fig-07a-tree", fig_tree),
    ("fig-07b-sugiyama", fig_sugiyama),
    ("fig-07c-force", fig_force),
    ("fig-07d-edge-routing", fig_edge_routing),
    ("fig-08-treemap", fig_treemap),
    ("fig-09-decision", fig_decision),
    ("fig-10-lowering", fig_lowering),
]


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Layout Methods — Field Guide Plates",
                        profile="diagram", lang="en")
    # Axis label text style for the embedded charts.
    b.define_text_style("_axis", font_family=SANS, font_size=10, color=MUTE)
    for _id, fn in FIGURES:
        fn(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} figure(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    out_dir = os.path.join(ROOT, "_tmp", "figures")
    os.makedirs(out_dir, exist_ok=True)
    svgs = render_page_svgs(doc)
    for (fig_id, _fn), svg in zip(FIGURES, svgs):
        path = os.path.join(out_dir, f"{fig_id}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
    print(f"Wrote {len(svgs)} SVG(s) to {out_dir}")

    out_yaml = os.path.join(ROOT, "_tmp", "layout-methods-figures.fg.yaml")
    with open(out_yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out_yaml}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
