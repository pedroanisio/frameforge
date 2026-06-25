#!/usr/bin/env python3
"""House visual system + illustration plates for the book *Brand, From Products
to Source Code* — authored end-to-end through the FrameGraph SDK.

This module is the book's **drawing style**: a single low-chroma editorial
palette, a reusable imprint mark (the "stamp"), a hairline *ripple* field used as
a cover texture, and four didactic plates that redraw the figures the book's
Appendix A specifies as vector artwork (it ships them only as Mermaid starting
points):

    * fig-stack    — the five-layer brand stack, with diagnose-down / build-up   (§1.1)
    * fig-loop     — the domain-general loop                                      (§1.2)
    * fig-process  — the brand-study process flow with decision gates            (§1.6.2)
    * fig-axis     — the trust-and-ownership axis placing the four subjects       (§2.5)

The plates obey the shape grammar the book names: rounded rectangle = step,
diamond = gate, pill = terminal, dashed = loop-back; grayscale-safe (shape +
label, never colour alone). The mark and the ripple field are exported so the
book's cover and running heads share one identity — the system is its own
imprint, dogfooded.

Run from the repository root::

    uv run python examples/brand_book_figures.py     # writes _tmp/brand-book/figures/*.svg

⚠ ARCHITECTURAL CONTRACT (PALS's LAW): the prose and figures are LLM-authored.
They are validated here against the model (``build``) and the static rules
(``validate_static_rules``); the build fails loudly on any model error. The
plates are deliberate schematics — they show the *shape* of each idea, not a
measured dataset.
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    render_page_svgs,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# The house palette — a sober, print-weight editorial system. One restrained
# steel-indigo carries chrome and primary nodes; every other hue is a
# desaturated tint reserved for a genuine semantic role (an evidence weight, a
# subject family) — never decoration. Purely enumerative fills collapse to one
# accent so that shape and number, not colour, do the encoding.
# --------------------------------------------------------------------------- #
W = 1100
MARGIN = 56

SERIF = ["Charter", "Bitstream Charter", "Georgia", "serif"]
SANS = ["Fira Sans", "Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["Fira Mono", "JetBrains Mono", "DejaVu Sans Mono", "monospace"]

PAPER = "#FFFFFF"
CREAM = "#FBFAF6"           # warm book paper, for cover / front matter grounds
PANEL = "#F3F1EB"           # quiet section panels (warm grey)
CARD = "#FFFFFF"
INK = "#1E2329"             # primary text — soft near-black
MUTE = "#5A6069"            # secondary text
FAINT = "#6A7079"           # tertiary / micro-labels
LINE = "#E4E2DA"            # hairlines (warm)
RULE = "#C7C3B7"            # heavier separators
INKBG = "#23252B"           # dark code / formula slab
GOLD = "#9A7B3F"            # the imprint accent — a struck, foil-like gold-brown

# Accent families (fill, stroke, text) — one hue per conceptual role.
INDIGO = ("#EAEBF2", "#565B82", "#393C5F")   # primary accent / chrome
SLATE = ("#ECEEF1", "#5A6573", "#39424E")   # layer 1 (the mark)
BLUE = ("#E7EDF4", "#3F608A", "#2A4360")   # layer 2 (the sign)
TEAL = ("#E2EEEB", "#3B7C76", "#27534E")   # layer 3 (the signal)
VIOLET = ("#EDE9F2", "#6B5B87", "#473A60")   # layer 4 (memory)
AMBER = ("#F3ECDC", "#8C6F34", "#5F4B22")   # gate / iterate / caution
ROSE = ("#F1E7E4", "#9C5A52", "#6F3E38")   # stop / attention-monetizing end
EMER = ("#E5EEE7", "#487A5B", "#335240")   # go / ownership end

# Evidence-weight colours — the spine of the book's method; reused inline.
EV_SOURCED = EMER          # traceable, verifiable
EV_SYNTH = INDIGO        # analyst's reading / model
EV_ILLUS = AMBER         # stylized example
EV_RESEARCH = ROSE          # open question — primary research not done

GUIDE = "#B4AE9E"           # dashed reference guides
BAR = "#DBD7CB"            # pale content bars

# On-dark tints for text on the INKBG slab.
D_TITLE = "#B6A887"
D_BODY = "#D9D6CE"
D_FAINT = "#938E84"


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None,
       transform=None, family=None, style=None):
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
    if family is not None:
        s["font_family"] = family
    if style is not None:
        s["font_style"] = style
    return s


def vcenter(page, box, text, *, size, color, weight=None, family=None,
            spacing=None, align="center"):
    """Place a single line of text vertically centred in ``box``."""
    x, y, w, h = box
    page.text([x, y + (h - size) / 2.0 - 1, w, size + 5], text,
              style=ts(size, color, weight=weight, align=align, family=family,
                       spacing=spacing))


# --------------------------------------------------------------------------- #
# The imprint identity — a reusable mark + a cover texture. These are the
# "patterns / drawings / style" the book is published with; the cover and the
# running heads pull from here so the whole object reads as one imprint.
# --------------------------------------------------------------------------- #
def brand_mark(page, cx, cy, r, *, ink=INK, accent=GOLD, ring=True):
    """The imprint stamp — a struck seal. The word *brand* is literally a burn
    (Old Norse *brandr*); the mark reads as a branding-iron stamp: an outer ring
    (the iron), a struck bracket pair (ownership / the trademark), and a small
    burn-point spark. Scales to any ``r``; used on the cover and running heads."""
    if ring:
        page.circle([cx, cy], r, fill="none", stroke=accent,
                    stroke_style={"stroke_width": max(1.4, r * 0.05)})
        page.circle([cx, cy], r * 0.80, fill="none", stroke=ink,
                    stroke_style={"stroke_width": max(1.0, r * 0.028)})
    # The struck bracket pair — "[ ]", the mark that says whose this is.
    bw = r * 0.30          # bracket horizontal arm
    bh = r * 0.52          # bracket half-height
    th = max(2.0, r * 0.10)
    for sgn in (-1, 1):
        ax = cx + sgn * r * 0.42
        # vertical stem
        page.rect([ax - (th / 2 if sgn < 0 else th / 2), cy - bh, th, 2 * bh],
                  fill=ink)
        # top + bottom arms, pointing inward
        page.rect([ax - (bw if sgn > 0 else 0), cy - bh, bw, th], fill=ink)
        page.rect([ax - (bw if sgn > 0 else 0), cy + bh - th, bw, th], fill=ink)
    # The burn-point spark at the centre.
    page.circle([cx, cy], r * 0.13, fill=accent)


def ripple_field(page, cx, cy, *, n=11, r0=70, dr=58, color=LINE, width=1.0,
                 max_r=2000):
    """A hairline ripple texture — concentric rings emanating from the mark, the
    engraved-banknote feel that signals provenance/trust. Very low contrast; a
    cover ground, never foreground. Rings are clipped only by the page bounds the
    caller chose, so keep ``cx, cy`` and ``max_r`` inside the canvas of interest."""
    for i in range(n):
        r = r0 + i * dr
        if r > max_r:
            break
        page.circle([cx, cy], r, fill="none", stroke=color,
                    stroke_style={"stroke_width": width})


def hairline_grid(page, box, *, step=26, color=LINE, width=0.8):
    """A faint baseline-grid field for editorial grounds (front matter)."""
    x, y, w, h = box
    yy = y
    while yy <= y + h + 0.5:
        page.line([x, yy], [x + w, yy], stroke=color,
                  stroke_style={"stroke_width": width})
        yy += step


def header(page, H, kicker, title, *, sub=None):
    """Standard plate chrome: imprint rule, kicker tag, title, thin rule."""
    page.layer("bg")
    page.rect([0, 0, W, H], fill=PAPER)
    page.rect([0, 0, 6, H], fill=INDIGO[2])
    page.layer("head")
    brand_mark(page, MARGIN + 16, 44, 15)
    page.text([MARGIN + 42, 30, W - 2 * MARGIN - 42, 14], kicker,
              style=ts(12, INDIGO[1], weight=800, spacing=2.2, transform="uppercase"))
    page.text([MARGIN + 42, 49, W - 2 * MARGIN - 42, 32], title,
              style=ts(24, INK, weight=800, spacing=-0.4))
    ry = 92
    if sub is not None:
        page.text([MARGIN + 42, 84, W - 2 * MARGIN - 42, 18], sub,
                  style=ts(13, MUTE, lh=1.3))
        ry = 110
    page.rect([MARGIN, ry, W - 2 * MARGIN, 1.4], fill=RULE)
    page.layer("body")
    # Diagram labels are freeform annotation, not tabular data — declare the page
    # as lettering so the tabular-box-model heuristic does not misread it.
    page._lettering_depth += 1
    return ry + 1


def caption(page, H, text, *, width=None):
    """A muted takeaway pinned to the plate's bottom edge; wraps to ≤2 lines."""
    from framegraph.sdk.metrics import wrap_text
    cw = width or (W - 2 * MARGIN)
    lines = wrap_text(text, width=cw, font_family=SANS, font_size=12)[:2]
    y0 = H - 30 - (len(lines) - 1) * 15
    for ln in lines:
        page.text([MARGIN, y0, cw, 16], ln,
                  style=ts(12, MUTE, lh=1.3, style="italic"))
        y0 += 15


def chip(page, box, label, palette, *, size=13, weight=700, sub=None,
         radius=9, sw=1.6, family=None, dash=None, align="center"):
    """A rounded node box with a centred (optionally two-line) label."""
    x, y, w, h = box
    fill, stroke, text = palette
    ss = {"stroke_width": sw}
    if dash is not None:
        ss["stroke_dasharray"] = dash
    page.rect([x, y, w, h], radius=radius, fill=fill, stroke=stroke, stroke_style=ss)
    if sub is not None:
        page.text([x + 12, y + h / 2 - 16, w - 24, 17], label,
                  style=ts(size, text, weight=weight, align=align))
        page.text([x + 12, y + h / 2 + 3, w - 24, 14], sub,
                  style=ts(10, text, align=align, lh=1.2))
    else:
        vcenter(page, box, label, size=size, color=text, weight=weight, family=family)


def poly_arrow(page, pts, *, color, width=1.8, head=9, dash=None):
    """A multi-segment connector through ``pts`` with one arrowhead at the end.
    Straight segments are plain lines; only the last carries the head, so
    orthogonal loop-backs route cleanly without hand-rolled triangles."""
    ss = {"stroke_width": width}
    if dash is not None:
        ss["stroke_dasharray"] = dash
    for a, b in zip(pts[:-2], pts[1:-1]):
        page.line(a, b, stroke=color, stroke_style=ss)
    page.arrow(pts[-2], pts[-1], color=color, width=width, head=head,
               stroke_style=({"stroke_dasharray": dash} if dash else {}))


# =========================================================================== #
# Figure A — the five-layer brand stack (§1.1): diagnose down, build up.
# =========================================================================== #
def fig_stack(b):
    H = 736
    page = b.page("fig-stack", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§1.1 · The concept stack",
           "What a brand is — five layers, one mark to a feeling",
           sub="A stack accumulated over ~four millennia, from a literal burn to "
               "an impression in a head. Diagnose down it; build back up it.")

    # Bands: layer 1 (the mark) at the bottom, layer 5 (the felt impression) on
    # top — the order the book reads them, concrete → affective.
    bands = [
        ("L1", "A mark — ownership & origin", "“Whose is this, and who made it?”",
         "ON brandr", SLATE),
        ("L2", "A distinguishing sign — the trademark", "“Which option is which?”",
         "AMA", BLUE),
        ("L3", "A quality signal — reputation under uncertainty",
         "“Can I trust this without checking?”", "Erdem-Swait 98", TEAL),
        ("L4", "A structure in memory — associations",
         "“What comes to mind, and how strongly?”", "Keller 93", VIOLET),
        ("L5", "A felt impression — the gut feeling",
         "“the affective summary of the stack”", "Neumeier 03", INDIGO),
    ]
    bx, bw = 196, 700
    bh, gap = 86, 13
    total = len(bands) * bh + (len(bands) - 1) * gap
    y_bottom = 632
    y_top = y_bottom - total                       # top of the topmost band
    # Draw from top (L5) down to bottom (L1): reverse so list[0]=L1 sits lowest.
    tops = []
    for i, (code, name, q, src, pal) in enumerate(reversed(bands)):
        y = y_top + i * (bh + gap)
        tops.append(y)
        fill, stroke, text = pal
        page.rect([bx, y, bw, bh], radius=11, fill=fill, stroke=stroke,
                  stroke_style={"stroke_width": 1.6})
        # number badge
        page.rect([bx + 16, y + bh / 2 - 19, 38, 38], radius=9, fill=stroke)
        vcenter(page, [bx + 16, y + bh / 2 - 19, 38, 38], code, size=13,
                color="#FFFFFF", weight=800)
        page.text([bx + 70, y + 16, bw - 240, 20], name,
                  style=ts(15, text, weight=800))
        page.text([bx + 70, y + 42, bw - 240, 18], q,
                  style=ts(12.5, MUTE, style="italic"))
        page.text([bx + bw - 168, y + bh / 2 - 8, 150, 16], src,
                  style=ts(10.5, FAINT, family=MONO, align="right"))

    # Left rail — DIAGNOSE, pointing down.
    rail_l = bx - 40
    page.arrow([rail_l, y_top + 6], [rail_l, y_bottom - 6], color=ROSE[1],
               width=2.2, head=11)
    page.text([rail_l - 84, y_top - 26, 120, 14], "DIAGNOSE",
              style=ts(11, ROSE[2], weight=800, spacing=2.0, align="center"))
    page.text([rail_l - 96, y_top - 10, 132, 14],
              "what it rests on",
              style=ts(9.5, MUTE, align="center", style="italic"))
    # Right rail — BUILD, pointing up.
    rail_r = bx + bw + 40
    page.arrow([rail_r, y_bottom - 6], [rail_r, y_top + 6], color=EMER[1],
               width=2.2, head=11)
    page.text([rail_r - 36, y_top - 26, 120, 14], "BUILD",
              style=ts(11, EMER[2], weight=800, spacing=2.0, align="center"))
    page.text([rail_r - 60, y_top - 10, 168, 14],
              "sign → reputation → feeling",
              style=ts(9.5, MUTE, align="center", style="italic"))

    caption(page, H, "Treating any single layer as the definition — as the "
                     "“gut feeling” shorthand does — collapses the stack. Each "
                     "rung is sourced; the ordering is a synthesis.")
    return H


# =========================================================================== #
# Figure B — the domain-general loop (§1.2).
# =========================================================================== #
def fig_loop(b):
    H = 728
    page = b.page("fig-loop", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§1.2 · The domain-general loop",
           "The same five moves, for any entity",
           sub="Strip the corporate vocabulary and one loop appears for a company, "
               "a person, a nation, or a software project.")

    cx, cy, R = 548, 408, 196
    nodes = [
        ("Discover", "purpose · niche · audit"),
        ("Position", "vs. peers / rivals"),
        ("Express", "name · identity · voice"),
        ("Distribute", "consistently, over time"),
        ("Steward", "audit · refresh · govern"),
    ]
    nw, nh = 168, 60
    centers = []
    for i in range(5):
        th = math.radians(-90 + 72 * i)
        px = cx + R * math.cos(th)
        py = cy + R * math.sin(th)
        centers.append((px, py))

    # Connectors first (under the nodes): solid forward, dashed loop-back close.
    for i in range(5):
        a = centers[i]
        bb = centers[(i + 1) % 5]
        dx, dy = bb[0] - a[0], bb[1] - a[1]
        d = math.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        s = (a[0] + ux * 92, a[1] + uy * 92)
        e = (bb[0] - ux * 92, bb[1] - uy * 92)
        if i == 4:    # Steward → Discover : the loop-back, dashed
            page.arrow(s, e, color=GUIDE, width=2.0, head=10,
                       stroke_style={"stroke_dasharray": [7, 5]})
        else:
            page.arrow(s, e, color=INDIGO[1], width=2.2, head=11)

    # Nodes.
    for (label, sub), (px, py) in zip(nodes, centers):
        chip(page, [px - nw / 2, py - nh / 2, nw, nh], label, INDIGO,
             size=14.5, sub=sub)

    # Centre — the irreducible subset.
    page.circle([cx, cy], 86, fill=CREAM, stroke=LINE,
                stroke_style={"stroke_width": 1.2})
    page.text([cx - 80, cy - 30, 160, 16], "THE IRREDUCIBLE CORE",
              style=ts(9.5, GOLD, weight=800, spacing=1.4, align="center"))
    page.text([cx - 80, cy - 10, 160, 16], "a persistent",
              style=ts(12, INK, align="center", weight=600))
    page.text([cx - 80, cy + 6, 160, 16], "distinguishing sign",
              style=ts(12, INK, align="center", weight=700))
    page.text([cx - 80, cy + 24, 160, 16], "+ consistency over time",
              style=ts(11, MUTE, align="center"))

    caption(page, H, "Repetition is the only mechanism that turns a sign into a "
                     "reputation; everything else is scaffolding that scales with "
                     "resources.")
    return H


# =========================================================================== #
# Figure C — the brand-study process flow with decision gates (§1.6.2).
# =========================================================================== #
def fig_process(b):
    H = 1376
    PW = 1000
    page = b.page("fig-process", canvas={"size": [PW, H], "units": "px"},
                  coordinate_mode="absolute")
    # local header (this plate is wider/taller than the W default)
    page.layer("bg")
    page.rect([0, 0, PW, H], fill=PAPER)
    page.rect([0, 0, 6, H], fill=INDIGO[2])
    page.layer("head")
    brand_mark(page, MARGIN + 16, 44, 15)
    page.text([MARGIN + 42, 30, PW - 2 * MARGIN - 42, 14],
              "§1.6.2 · THE GATED PHASES",
              style=ts(12, INDIGO[1], weight=800, spacing=2.2))
    page.text([MARGIN + 42, 49, PW - 2 * MARGIN - 42, 32],
              "The brand-study process, gate by gate",
              style=ts(24, INK, weight=800, spacing=-0.4))
    page.text([MARGIN + 42, 84, PW - 2 * MARGIN - 42, 18],
              "Each phase ends in a sponsor-owned go / iterate / stop gate. Rounded "
              "rectangle = step · diamond = gate · pill = terminal · dashed = loop-back.",
              style=ts(12.5, MUTE, lh=1.3))
    page.rect([MARGIN, 112, PW - 2 * MARGIN, 1.4], fill=RULE)
    page.layer("body")
    page._lettering_depth += 1

    steps = [
        ("phase", "P0", "Phase 0 — Scope & Contract", "objectives · KPIs · budget"),
        ("gate", "G0", "Brief signed?", None),
        ("phase", "P1", "Phase 1 — Discovery", "interviews · asset & internal audit"),
        ("gate", "G1", "Problem aligned?", None),
        ("phase", "P2", "Phase 2 — Research & Diagnosis", "Brand Audit · gap · SWOT"),
        ("gate", "G2", "Diagnosis accepted?", None),
        ("phase", "P3", "Phase 3 — Strategy", "positioning · brand platform"),
        ("gate", "G3", "Sponsor sign-off", "PIVOTAL"),
        ("phase", "P4", "Phase 4 — Expression", "verbal & visual identity"),
        ("gate", "G4", "On-strategy?", None),
        ("phase", "P5", "Phase 5 — Codification", "brand book · rollout · governance"),
        ("gate", "G5", "Launch ready?", None),
        ("phase", "P6", "Phase 6 — Measurement", "track vs Phase-0 KPIs"),
    ]
    cx = 430
    pw_box, ph_box = 300, 58
    gw, gh = 240, 70
    gapv = 26
    y = 150
    geo = {}                # id -> (kind, top, bottom, ycenter)
    for kind, sid, title, sub in steps:
        if kind == "phase":
            top, h, half = y, ph_box, pw_box / 2
            pal = INDIGO
            page.rect([cx - half, top, pw_box, ph_box], radius=11, fill=pal[0],
                      stroke=pal[1], stroke_style={"stroke_width": 1.7})
            page.text([cx - half + 18, top + 12, pw_box - 36, 18], title,
                      style=ts(13.5, pal[2], weight=800))
            page.text([cx - half + 18, top + 33, pw_box - 36, 16], sub,
                      style=ts(10.5, MUTE))
            geo[sid] = (kind, top, top + h, top + h / 2)
            y += h + gapv
        else:
            pivotal = sub == "PIVOTAL"
            top, h, half = y, gh, gw / 2
            pal = AMBER if not pivotal else GOLD
            fill = AMBER[0] if not pivotal else "#F4ECD7"
            stroke = AMBER[1] if not pivotal else GOLD
            cy = top + h / 2
            pts = [[cx, top], [cx + half, cy], [cx, top + h], [cx - half, cy]]
            page.polygon(pts, fill=fill, stroke=stroke,
                         stroke_style={"stroke_width": 2.0 if pivotal else 1.6})
            page.text([cx - half * 0.66, cy - 16, half * 1.32, 16], title,
                      style=ts(11.5 if not pivotal else 12.5,
                               AMBER[2] if not pivotal else "#5F4B22",
                               weight=800, align="center"))
            if pivotal:
                page.text([cx - half * 0.66, cy + 1, half * 1.32, 14],
                          "the pivotal decision",
                          style=ts(9.5, "#5F4B22", align="center", style="italic"))
            geo[sid] = (kind, top, top + h, cy)
            y += h + gapv

    # Forward "Go" spine — straight down between consecutive elements.
    order = [s[1] for s in steps]
    for a, bb in zip(order[:-1], order[1:]):
        ay = geo[a][2]
        by = geo[bb][1]
        page.arrow([cx, ay + 2], [cx, by - 2], color=EMER[1], width=2.0, head=9)
        if geo[a][0] == "gate":          # label the go-edge leaving a gate
            page.text([cx + 14, (ay + by) / 2 - 8, 40, 14], "Go",
                      style=ts(10, EMER[2], weight=700))

    # Iterate loop-backs — each gate up to its preceding phase, dashed, right.
    chan_r = 690
    pairs = [("G0", "P0"), ("G1", "P1"), ("G2", "P2"), ("G3", "P3"),
             ("G4", "P4"), ("G5", "P5")]
    for g, p in pairs:
        gy = geo[g][3]
        py = geo[p][3]
        poly_arrow(page, [[cx + gw / 2, gy], [chan_r, gy], [chan_r, py],
                          [cx + pw_box / 2, py]],
                   color=AMBER[1], width=1.5, head=8, dash=[6, 5])
    page.text([chan_r - 4, geo["G3"][3] - 4, 96, 14], "Iterate",
              style=ts(10.5, AMBER[2], weight=700))

    # Stop branch from G2 → a terminal pill, to the left.
    g2y = geo["G2"][3]
    page.rect([150, g2y - 23, 150, 46], radius=23, fill=ROSE[0], stroke=ROSE[1],
              stroke_style={"stroke_width": 1.6})
    vcenter(page, [150, g2y - 23, 150, 46], "Halt / re-scope", size=11.5,
            color=ROSE[2], weight=700)
    page.arrow([cx - gw / 2, g2y], [300 + 4, g2y], color=ROSE[1], width=1.8, head=9)
    page.text([318, g2y - 20, 60, 14], "Stop",
              style=ts(10.5, ROSE[2], weight=700))

    # Re-audit loop — P6 bottom back up to P2, dashed, far left.
    chan_l = 80
    p6b = geo["P6"][2]
    p2y = geo["P2"][3]
    poly_arrow(page, [[cx - pw_box / 2, p6b - 12], [chan_l, p6b - 12],
                      [chan_l, p2y], [cx - pw_box / 2, p2y]],
               color=GUIDE, width=1.6, head=9, dash=[7, 5])
    page.text([chan_l + 6, (p2y + p6b) / 2 - 8, 90, 14], "re-audit",
              style=ts(10.5, FAINT, weight=700, style="italic"))

    page.text([MARGIN, H - 38, PW - 2 * MARGIN, 16],
              "The most common failure is governance, not analysis: the agency "
              "recommends; a named sponsor decides each gate.",
              style=ts(12, MUTE, lh=1.35, style="italic"))
    return H


# =========================================================================== #
# Figure D — the trust-and-ownership axis (§2.5).
# =========================================================================== #
def fig_axis(b):
    H = 588
    page = b.page("fig-axis", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    header(page, H, "§2.5 · Cross-case synthesis",
           "The trust-and-ownership axis",
           sub="How much each subject asks users to trust it with, versus how much "
               "control it hands to them.")

    axis_y = 322
    x0, x1 = 150, 956
    # The axis bar — a warm neutral spine with tinted ends.
    page.rect([x0, axis_y - 5, x1 - x0, 10], radius=5, fill=BAR)
    page.rect([x0, axis_y - 5, 150, 10], radius=5, fill=ROSE[0])
    page.rect([x1 - 150, axis_y - 5, 150, 10], radius=5, fill=EMER[0])
    page.arrow([x0 + 14, axis_y], [x0 - 6, axis_y], color=ROSE[1], width=2.2, head=11)
    page.arrow([x1 - 14, axis_y], [x1 + 6, axis_y], color=EMER[1], width=2.2, head=11)
    page.text([x0 - 14, axis_y + 18, 300, 16], "ATTENTION & DATA",
              style=ts(11.5, ROSE[2], weight=800, spacing=1.4))
    page.text([x0 - 14, axis_y + 36, 320, 14], "monetize attention — the far end",
              style=ts(10.5, MUTE, style="italic"))
    page.text([x1 - 300, axis_y + 18, 314, 16], "OWNERSHIP & CONTROL",
              style=ts(11.5, EMER[2], weight=800, spacing=1.4, align="right"))
    page.text([x1 - 320, axis_y + 36, 334, 14],
              "your files · your hardware · yours",
              style=ts(10.5, MUTE, style="italic", align="right"))

    # Subjects: (x on axis, card x, above?, name, line, palette)
    subs = [
        (212, 120, True, "Meta", "advertising; attention + data", ROSE),
        (468, 360, False, "Claude", "ad-free; a space to think; limits on use", BLUE),
        (752, 636, True, "Obsidian", "local-first; user-funded; no ads", TEAL),
        (902, 800, False, "Ollama", "local runtime; your hardware; offline", EMER),
    ]
    cw, ch = 246, 80
    for ax, cardx, above, name, line, pal in subs:
        page.circle([ax, axis_y], 7, fill=pal[1], stroke=PAPER,
                    stroke_style={"stroke_width": 2})
        if above:
            cy = axis_y - 116
            page.line([ax, axis_y - 7], [ax, cy + ch], stroke=pal[1],
                      stroke_style={"stroke_width": 1.4})
        else:
            cy = axis_y + 70
            page.line([ax, axis_y + 7], [ax, cy], stroke=pal[1],
                      stroke_style={"stroke_width": 1.4})
        cardx = min(cardx, W - MARGIN - cw)
        page.rect([cardx, cy, cw, ch], radius=10, fill=CARD, stroke=pal[1],
                  stroke_style={"stroke_width": 1.6})
        page.rect([cardx, cy, 5, ch], radius=2, fill=pal[1])
        page.text([cardx + 18, cy + 14, cw - 30, 20], name,
                  style=ts(16, pal[2], weight=800))
        page.text([cardx + 18, cy + 40, cw - 30, 30], line,
                  style=ts(11.5, MUTE, lh=1.25))

    caption(page, H, "Structure is the proof: the brands whose structure matches "
                     "their claim — a PBC, a bootstrapped no-ads model — are the "
                     "credible ones. A rename cannot project an unearned reputation.")
    return H


# --------------------------------------------------------------------------- #
# Build + emit.
# --------------------------------------------------------------------------- #
FIGURES = [
    ("fig-stack", fig_stack),
    ("fig-loop", fig_loop),
    ("fig-process", fig_process),
    ("fig-axis", fig_axis),
]


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Brand Book — Plates", profile="diagram", lang="en")
    for _id, fn in FIGURES:
        fn(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} figure(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in report.issues[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    out_dir = os.path.join(ROOT, "_tmp", "brand-book", "figures")
    os.makedirs(out_dir, exist_ok=True)
    svgs = render_page_svgs(doc)
    for (fig_id, _fn), svg in zip(FIGURES, svgs):
        with open(os.path.join(out_dir, f"{fig_id}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    with open(os.path.join(ROOT, "_tmp", "brand-book", "figures.fg.yaml"),
              "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {len(svgs)} SVG(s) to {out_dir}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
