#!/usr/bin/env python3
"""Web Design Proposal — a premium editorial proposal booklet, authored with the SDK.

A faithful FrameForge port of the crafted reference (_tmp/web-design-proposal.html):
ultra-light display headings with a single bold word, gold eyebrows on wide
tracking, angular photo frames (silhouette + gold slash + tag), hand-drawn
thin-line icons, a real Gantt, a rotated "Draft" stamp, charcoal contrast pages,
and a gold/marble perspective showcase scene. Everything is hand-composed — no
default widgets — so the document reads as a designed brochure, not a template.

A4 portrait pages at 96 dpi (794x1123 px). Run standalone or via the MCP::

    uv run python examples/web_design_proposal.py out/web/web-design-proposal.fg.yaml

TEMPLATE DISCLAIMER: every name, role, year, price, percentage and paragraph is
ILLUSTRATIVE PLACEHOLDER content authored to demonstrate layout only — replace
with verified data before any real use. Photos are labelled placeholder frames.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, serialize  # noqa: E402
from frameforge.sdk.paint import linear_gradient, radial_gradient, rgba  # noqa: E402

# --- tokens (mirrors the reference :root) ----------------------------------- #
GOLD, GOLD2, GOLD_SOFT = "#F2B705", "#FFC72C", "#FCEBB3"
CHAR, CHAR2 = "#232528", "#191A1C"
INK, PAPER, PAPER2 = "#1C1D1F", "#FFFFFF", "#FAFAF7"
MUTE, MUTE2, LINE = "#9A9A97", "#6F7073", "#E6E6E1"
BODYCOL, LEADCOL = "#46474A", "#3A3B3D"

DISPLAY = ["Sora", "Inter Display", "Inter", "Helvetica Neue", "Arial", "sans-serif"]
BODY = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
LIGHT, EXLIGHT = 300, 200

PW, PH, PAD = 794, 1123, 64
PHOTO_GRAD = linear_gradient([("#CDCDCA", 0), ("#A9A9A6", 38), ("#7E7E7C", 70), ("#5D5D5B", 100)], angle=135)


# --------------------------------------------------------------------------- #
#  Text helpers                                                                #
# --------------------------------------------------------------------------- #
def t(size, color, *, weight=400, family=None, spacing=None, lh=None, align="left",
      upper=False, valign="top", italic=False, wrap=True):
    st = {"font_family": family or BODY, "font_size": size, "font_weight": weight,
          "color": color, "align": align, "vertical_align": valign}
    if spacing is not None:
        st["letter_spacing"] = spacing
    if lh is not None:
        st["line_height"] = lh
    if upper:
        st["text_transform"] = "uppercase"
    if italic:
        st["font_style"] = "italic"
    if not wrap:
        st["white_space"] = "nowrap"
    return st


def eyebrow(L, x, y, text, *, color=GOLD, w=600):
    L.text([x, y, w, 16], text, style=t(10, color, weight=600, family=DISPLAY,
           spacing=3.8, upper=True, wrap=False))


def heading(L, x, y, lines, *, size=46, color=INK, lh=1.02, w=640):
    """Two-tone display heading: light face with a single bold word per the runs.
    ``lines`` is a list of lines; each line a list of ``(text, is_bold)`` runs."""
    for i, line in enumerate(lines):
        spans = [{"text": tx, "style": {"font_family": DISPLAY, "font_size": size,
                  "font_weight": (600 if b else EXLIGHT), "color": color}} for tx, b in line]
        L.add({"type": "text", "box": [x, y + i * size * lh, w, int(size * 1.34)],
               "spans": spans,
               "style": {"font_family": DISPLAY, "font_size": size,
                         "font_weight": EXLIGHT, "line_height": 1.0, "color": color}})
    return y + len(lines) * size * lh


def body(L, x, y, w, text, *, size=11.5, color=BODYCOL, lh=1.85, h=300, align="left"):
    L.text([x, y, w, h], text, style=t(size, color, lh=lh, align=align))


# --------------------------------------------------------------------------- #
#  Page furniture                                                              #
# --------------------------------------------------------------------------- #
def mark(L, x, y, s, *, color=GOLD):
    """The notched-square brand mark (clip-path polygon 0 0,100 0,100 72,72 100,0 100)."""
    L.polygon([[x, y], [x + s, y], [x + s, y + s * 0.72], [x + s * 0.72, y + s], [x, y + s]],
              fill=color)


def pagehead(L, nav, *, dark=False):
    fg = PAPER if dark else INK
    navc = rgba(PAPER, 0.5) if dark else MUTE2
    mark(L, PAD, 44, 17)
    L.text([PAD + 26, 43, 320, 20], "LUMEN & CO.",
           style=t(13, fg, weight=700, family=DISPLAY, spacing=0.3, wrap=False))
    L.text([PW - PAD - 360, 47, 360, 16], nav,
           style=t(9.5, navc, weight=600, family=DISPLAY, spacing=3.2, upper=True,
                   align="right", wrap=False))


def rule(L, *, x=PAD, y=78, w=54):
    L.rect([x, y, w, 3], fill=GOLD)


def pagefoot(L, label, pno, *, dark=False):
    fg = PAPER if dark else INK
    sub = rgba(PAPER, 0.45) if dark else MUTE
    L.text([PAD, PH - 48, 460, 14], label,
           style=t(9.5, sub, weight=500, family=DISPLAY, spacing=2.6, upper=True, wrap=False))
    L.text([PW - PAD - 60, PH - 48, 60, 14], pno,
           style=t(9.5, fg, weight=600, family=DISPLAY, spacing=2.0, align="right", wrap=False))


def page(doc, pid, *, bg=PAPER):
    p = doc.page(pid, canvas={"size": [PW, PH]}, coordinate_mode="absolute")
    L = p.layer("main")
    L.rect([0, 0, PW, PH], fill=bg, decorative=True)
    return L


# --------------------------------------------------------------------------- #
#  Photo placeholder — angular frame + silhouette + gold slash + tag           #
# --------------------------------------------------------------------------- #
def _clip_poly(x, y, w, h, kind):
    if kind == "corner":
        return [[x, y], [x + w, y], [x + w, y + 0.78 * h], [x + 0.82 * w, y + h], [x, y + h]]
    if kind == "skew":
        return [[x, y + 0.08 * h], [x + w, y], [x + w, y + 0.92 * h], [x, y + h]]
    if kind == "tri":
        return [[x, y], [x + w, y], [x + w, y + 0.86 * h], [x, y + h]]
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def photo(L, x, y, w, h, *, kind="corner", tag="Photo · placeholder", slash=True,
          slash_at=0.62, fig_op=0.34):
    poly = _clip_poly(x, y, w, h, kind)
    cx = x + w / 2
    hr = min(w, h) * 0.16          # head radius scales to the SHORT side, so a wide
    sr = min(w, h) * 0.46          # band reads as a portrait, not a giant blob
    children = [
        {"type": "polyline", "points": poly, "closed": True, "fill": PHOTO_GRAD, "decorative": True},
        {"type": "ellipse", "center": [x + w * 0.32, y + h * 0.2], "rx": w * 0.5, "ry": h * 0.4,
         "fill": rgba("#FFFFFF", 0.14), "decorative": True},
        {"type": "ellipse", "center": [cx, y + h - sr * 1.7], "rx": hr, "ry": hr,
         "fill": rgba("#FFFFFF", fig_op), "decorative": True},
        {"type": "ellipse", "center": [cx, y + h + sr * 0.2], "rx": sr, "ry": sr,
         "fill": rgba("#FFFFFF", fig_op), "decorative": True},
    ]
    if slash:
        sx = x + w * slash_at
        lean = h * 0.16
        children.append({"type": "polyline",
                         "points": [[sx, y - 2], [sx + 16, y - 2], [sx + 16 - lean, y + h + 2], [sx - lean, y + h + 2]],
                         "closed": True, "fill": GOLD})
    # everything clipped to the angular frame so the silhouette never overflows
    L.group(children, clip=poly)
    # tag chip
    tw = 7.0 * len(tag) * 0.62 + 12
    L.rect([x + 9, y + h - 22, tw, 14], fill=rgba("#000000", 0.30), radius=1)
    L.text([x + 14, y + h - 21, tw, 12], tag,
           style=t(7.5, rgba(PAPER, 0.9), family=DISPLAY, spacing=1.6, upper=True, wrap=False))


# --------------------------------------------------------------------------- #
#  Thin-line icons — ported verbatim from the reference SVG symbols (24-unit)  #
# --------------------------------------------------------------------------- #
def _icon_paths(name):
    return {
        "bulb": ["M12 3a6 6 0 0 0-3.6 10.8c.5.4.8 1 .8 1.7V17h5.6v-1.5c0-.7.3-1.3.8-1.7A6 6 0 0 0 12 3Z",
                 "M9.5 20h5", "M10 22h4"],
        "clip": ["M6.5 4h11a1.5 1.5 0 0 1 1.5 1.5v15a1.5 1.5 0 0 1-1.5 1.5h-11a1.5 1.5 0 0 1-1.5-1.5v-15a1.5 1.5 0 0 1 1.5-1.5Z",
                 "M9 4V3h6v1", "M8.5 9h7", "M8.5 12.5h7", "M8.5 16h4"],
        "doc": ["M7 3h7l4 4v14H7Z", "M14 3v4h4", "M10 12h5", "M10 15.5h5", "M10 8.5h2"],
        "gears": ["M10 4.5v-2", "M10 17.5v-2", "M4.5 10h-2", "M17.5 10h-2",
                  "M6.1 6.1 4.7 4.7", "M15.3 15.3l-1.4-1.4", "M13.9 6.1l1.4-1.4", "M6.1 13.9l-1.4 1.4"],
        "img": ["M5.5 5h13a1.5 1.5 0 0 1 1.5 1.5v11a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5v-11A1.5 1.5 0 0 1 5.5 5Z",
                "m5 17 4.5-4 3 2.5L16 11l3 3.5"],
        "pencil": ["M4 20h4l9.5-9.5a2 2 0 0 0-2.8-2.8L5 17.2 4 20Z", "m13.5 6.5 4 4"],
        "sliders": ["M5 8h9", "M18 8h1", "M5 16h1", "M10 16h9"],
        "rocket": ["M12 3c3 1.5 5 5 5 9l-2.5 2.5h-5L7 12c0-4 2-7.5 5-9Z",
                   "M9.5 17 7 21", "M14.5 17 17 21", "M9.5 16.5 12 19l2.5-2.5"],
        "search": ["m15 15 4.5 4.5"],
        "shield": ["M12 3 5 6v6c0 4 3 6.5 7 8 4-1.5 7-4 7-8V6Z", "m9 12 2 2 4-4"],
        "globe": ["M3.5 12h17", "M12 3.5c2.5 2.5 2.5 14.5 0 17", "M12 3.5c-2.5 2.5-2.5 14.5 0 17"],
    }.get(name, [])


def _icon_circles(name):
    return {
        "gears": [(10, 10, 3.2), (17, 17, 2.2)],
        "img": [(9, 10, 1.6)],
        "sliders": [(16, 8, 2.1), (8, 16, 2.1)],
        "rocket": [(12, 9.5, 1.6)],
        "search": [(10.5, 10.5, 5.5)],
        "globe": [(12, 12, 8.5)],
    }.get(name, [])


def icon(L, name, cx, cy, S, color):
    """Draw a 24-unit line icon centred at (cx, cy) scaled to size S."""
    k = S / 24.0
    sw = 1.5 / k
    st = {"stroke_width": sw, "stroke_linecap": "round", "stroke_linejoin": "round"}
    with L.frame(cx - S / 2, cy - S / 2, scale=k) as f:
        for cxx, cyy, r in _icon_circles(name):
            f.circle([cxx, cyy], r, fill="none", stroke=color, stroke_style=st)
        for d in _icon_paths(name):
            f.path(d, fill="none", stroke=color, stroke_style=st)


def tile(L, x, y, s, name, *, kind="gold"):
    """A square icon tile: gold→char icon, dark→gold icon, ghost→ink icon."""
    if kind == "gold":
        L.rect([x, y, s, s], fill=GOLD); ic = CHAR
    elif kind == "dark":
        L.rect([x, y, s, s], fill=CHAR); ic = GOLD
    else:
        L.rect([x, y, s, s], fill=PAPER2, stroke=LINE, stroke_style={"stroke_width": 1}); ic = INK
    icon(L, name, x + s / 2, y + s / 2, s * 0.46, ic)


def notch_tile(L, x, y, s, name, *, fill=GOLD, ic=CHAR):
    """A small notched-corner icon chip (the 'featrow .ix' style)."""
    L.polygon([[x, y], [x + s, y], [x + s, y + s * 0.78], [x + s * 0.78, y + s], [x, y + s]], fill=fill)
    icon(L, name, x + s / 2, y + s / 2, s * 0.5, ic)


# =========================================================================== #
#  PAGES
# =========================================================================== #
def p_cover(doc):
    L = page(doc, "cover", bg=PAPER)
    L.polygon([[0, 0], [PW, 0], [PW, 348], [0, 640]], fill=CHAR2, decorative=True)  # diag2
    L.polygon([[0, 0], [PW, 0], [PW, 651], [0, PH]], fill=CHAR, decorative=True)    # diag
    L.polygon([[680, 0], [710, 0], [710, 258], [680, 300]], fill=GOLD)             # gold-bar
    L.polygon([[PW, 370], [PW, 520], [644, 520]], fill=GOLD)                       # gold-tri
    # head
    mark(L, PAD, 46, 17)
    L.text([PAD + 26, 45, 300, 20], "LUMEN & CO.",
           style=t(13, PAPER, weight=700, family=DISPLAY, spacing=0.3, wrap=False))
    L.text([PW - PAD - 360, 49, 360, 16], "Proposal · No. WD-2026-014",
           style=t(9.5, rgba(PAPER, 0.6), weight=600, family=DISPLAY, spacing=2.6, upper=True, align="right", wrap=False))
    # cover photo
    photo(L, PW - PAD - 250, 150, 250, 320, kind="corner", tag="Portrait · placeholder", slash_at=0.66)
    # title
    eyebrow(L, PAD, 300, "Prepared for a new digital presence")
    heading(L, PAD, 322, [[("Web", False)]], size=74, color=GOLD, w=520)
    heading(L, PAD, 322 + 72, [[("Design", False)], [("Proposal", False)]], size=74, color=PAPER, w=520, lh=0.97)
    # meta grid 2x2
    meta = [("Project No.", "WD-2026-014"), ("Date", "[Month YYYY]"),
            ("Prepared for", "[Client / Company]"), ("Prepared by", "[Lead Designer]")]
    mx, my = PAD, PH - 380          # kept high enough to stay on the charcoal field
    for i, (l, v) in enumerate(meta):
        gx = mx + (i % 2) * 220
        gy = my + (i // 2) * 56
        L.text([gx, gy, 200, 12], l, style=t(9, GOLD, family=DISPLAY, spacing=2.7, upper=True, wrap=False))
        L.text([gx, gy + 16, 210, 18], v, style=t(13, PAPER, weight=500, wrap=False))
    # foot sits in the white triangle (bottom-right) in dark ink, so it reads
    L.text([PW - PAD - 360, PH - 52, 360, 14], "Lumen & Co.  ·  Confidential",
           style=t(9.5, MUTE2, family=DISPLAY, spacing=2.6, upper=True, align="right", wrap=False))
    return L


def p_about(doc):
    L = page(doc, "about", bg=PAPER)
    pagehead(L, "About"); rule(L)
    eyebrow(L, PAD, 150, "Who we are")
    heading(L, PAD, 168, [[("About ", False), ("Us", True)]], size=46)
    colw = (PW - 2 * PAD - 26) / 2
    body(L, PAD, 250, colw,
         "We are a compact studio of designers, strategists and engineers who build "
         "digital products with intent. Every engagement begins with the questions a "
         "brief usually skips — who is this for, what single job must the page do, and "
         "how will we know it worked.", h=200)
    body(L, PAD + colw + 26, 250, colw,
         "Our work favours clarity over decoration. We treat structure as information "
         "and typography as voice, and we ship measurable outcomes rather than mood "
         "boards. This proposal sets out how we would approach your project, our team, "
         "our process, and a transparent plan for time and cost.", h=200)
    # gold angular quote
    qy = 430
    L.polygon([[PAD, qy], [PW - PAD, qy], [PW - PAD, qy + 96], [PAD + 0.07 * (PW - 2 * PAD), qy + 96], [PAD, qy + 82]], fill=GOLD)
    L.text([PAD + 28, qy + 26, PW - 2 * PAD - 56, 60],
           "“Good design is the shortest distance between a question and a confident decision.”",
           style=t(20, CHAR, weight=LIGHT, family=DISPLAY, lh=1.32))
    # stats
    stats = [("120", "+", "Projects shipped (placeholder)"), ("14", "", "Specialists on staff"),
             ("9", "yr", "Average client tenure")]
    sx = PAD
    for n, suf, lab in stats:
        L.add({"type": "text", "box": [sx, PH - 200, 150, 50],
               "spans": [{"text": n, "style": {"font_family": DISPLAY, "font_size": 40, "font_weight": EXLIGHT, "color": GOLD}},
                         {"text": suf, "style": {"font_family": DISPLAY, "font_size": 40, "font_weight": LIGHT, "color": INK}}],
               "style": {"font_family": DISPLAY, "font_size": 40, "font_weight": EXLIGHT, "color": INK}})
        L.text([sx, PH - 200 + 50, 200, 28], lab, style=t(10, MUTE2, lh=1.3))
        sx += 220
    pagefoot(L, "Lumen & Co. · Web Design Proposal", "02")
    return L


def p_vision(doc):
    L = page(doc, "vision", bg=CHAR)
    pagehead(L, "Vision", dark=True); rule(L)
    eyebrow(L, PAD, 104, "What drives the work")
    heading(L, PAD, 122, [[("Vision &", False)], [("Mission", True)]], size=46, color=PAPER, lh=1.0)
    photo(L, PAD, 250, PW - 2 * PAD, 150, kind="skew", tag="Team photo · placeholder", slash_at=0.7)
    blocks = [("Our Vision", "A web where every interface is honest about what it does and effortless to use — fast, accessible, and unmistakably the client's own."),
              ("Our Mission", "To turn ambiguous goals into shipped, measurable digital experiences, pairing editorial craft with disciplined engineering on every release."),
              ("Our Promise", "Clear scope, transparent pricing, and no surprises. You will always know what is being built, why, and when it arrives.")]
    by = 446
    for h3, ptext in blocks:
        L.rect([PAD, by, 2, 66], fill=GOLD)
        L.text([PAD + 20, by, 400, 16], h3, style=t(13, GOLD, weight=600, family=DISPLAY, spacing=1.8, upper=True, wrap=False))
        body(L, PAD + 20, by + 24, PW - 2 * PAD - 20, ptext, size=11, color=rgba(PAPER, 0.78), lh=1.8, h=60)
        by += 92
    pagefoot(L, "Vision & Mission", "03", dark=True)
    return L


def p_letter(doc):
    L = page(doc, "letter", bg=PAPER)
    L.polygon([[PW - 26, 0], [PW, 0], [PW, PH * 0.55], [PW - 26, PH * 0.55 - 36]], fill=GOLD)  # lstrip
    pagehead(L, "Letter"); rule(L)
    eyebrow(L, PAD, 104, "A note before we begin")
    heading(L, PAD, 122, [[("Business", False)], [("Letter", True)]], size=46, lh=1.0)
    L.text([PAD, 252, 200, 16], "[Month DD, YYYY]", style=t(10, MUTE2, family=DISPLAY, wrap=False))
    L.text([PAD, 270, 300, 16], "To: [Client Name], [Title]", style=t(10, MUTE2, family=DISPLAY, wrap=False))
    L.text([PAD, 286, 300, 16], "[Client Company]", style=t(10, MUTE2, family=DISPLAY, wrap=False))
    L.text([PAD, 326, 400, 26], "Dear [Client Name],", style=t(20, INK, weight=LIGHT, family=DISPLAY, wrap=False))
    paras = [
        "Thank you for the opportunity to propose a new website for [Client Company]. We have reviewed your goals and prepared a plan that balances a distinctive brand presence with the performance and accessibility your audience expects.",
        "The pages that follow outline who we are, the team who would deliver the work, our process from planning through optimisation, and a clear timeline with transparent pricing. We have written it so that scope, cost and schedule are easy to compare against your own expectations.",
        "We would welcome the chance to walk you through it and adjust anything that does not fit. Whenever you are ready, we are prepared to begin.",
    ]
    py = 372
    for para in paras:
        body(L, PAD, py, PW - 2 * PAD - 30, para, size=11, lh=1.95, h=90)
        py += 96
    # signature
    sy = PH - 200
    L.text([PAD, sy, 300, 36], "[ Signature ]", style=t(30, INK, weight=EXLIGHT, family=DISPLAY, italic=True, wrap=False))
    L.rect([PAD, sy + 46, 160, 1], fill=INK)
    L.text([PAD, sy + 54, 300, 16], "[Lead Designer]", style=t(11, INK, weight=600, family=DISPLAY, wrap=False))
    L.text([PAD, sy + 72, 360, 14], "Founder & Design Lead, Lumen & Co.", style=t(10, MUTE2, wrap=False))
    pagefoot(L, "Business Letter", "04")
    return L


def p_toc(doc):
    L = page(doc, "toc", bg=PAPER2)
    pagehead(L, "Contents"); rule(L)
    eyebrow(L, PAD, 104, "Inside this proposal")
    heading(L, PAD, 122, [[("Table of", False)], [("Contents", True)]], size=46, lh=1.0)
    rows = [("01", "About Us", "02"), ("02", "Vision & Mission", "03"), ("03", "Director Board", "06"),
            ("04", "Our Team", "07"), ("05", "Your Website", "08"), ("06", "Development Process", "09"),
            ("07", "Project Timeline", "12"), ("08", "Pricing", "13"), ("09", "Project Terms", "14")]
    ry = 248
    for no, nm, pg in rows:
        L.text([PAD, ry, 30, 18], no, style=t(11, GOLD, weight=600, family=DISPLAY, wrap=False))
        L.text([PAD + 44, ry - 3, 400, 22], nm, style=t(17, INK, weight=LIGHT, family=DISPLAY, wrap=False))
        L.text([PW - PAD - 40, ry, 40, 18], pg, style=t(12, MUTE2, weight=600, family=DISPLAY, align="right", wrap=False))
        L.rect([PAD, ry + 30, PW - 2 * PAD, 1], fill=LINE, decorative=True)
        ry += 48
    L.polygon([[PW, PH - 170], [PW, PH], [PW - 170, PH]], fill=GOLD)
    L.text([PW - 92, PH - 70, 70, 44], "09", style=t(40, CHAR, weight=EXLIGHT, family=DISPLAY, align="right", wrap=False))
    pagefoot(L, "Table of Contents", "05")
    return L


def p_directors(doc):
    L = page(doc, "dir", bg=PAPER)
    pagehead(L, "Leadership"); rule(L)
    eyebrow(L, PAD, 104, "The people accountable")
    heading(L, PAD, 122, [[("Director", False)], [("Board", True)]], size=46, lh=1.0)
    dirs = [("[Director One]", "Managing Director", "Sets studio direction and owns client outcomes. Twenty-plus years across brand and product design.", "Experience · 22 years"),
            ("[Director Two]", "Creative Director", "Leads art direction and design quality. Background in editorial and digital typography.", "Experience · 16 years"),
            ("[Director Three]", "Technical Director", "Owns engineering standards, performance budgets and accessibility across every build.", "Experience · 18 years")]
    ry = 268
    for i, (nm, role, ptext, exp) in enumerate(dirs):
        photo(L, PAD, ry, 118, 142, kind="corner", tag="Photo", slash=(i == 1), slash_at=0.7)
        ix = PAD + 142
        L.text([ix, ry + 6, 360, 22], nm, style=t(17, INK, weight=600, family=DISPLAY, wrap=False))
        L.text([ix, ry + 32, 360, 14], role, style=t(10, GOLD, family=DISPLAY, spacing=2.2, upper=True, wrap=False))
        body(L, ix, ry + 54, 300, ptext, size=10.5, color="#54565A", lh=1.7, h=60)
        L.text([ix, ry + 110, 300, 14], exp, style=t(9, MUTE2, family=DISPLAY, spacing=1.4, upper=True, wrap=False))
        ry += 164
    pagefoot(L, "Director Board", "06")
    return L


def p_team(doc):
    L = page(doc, "team", bg=CHAR)
    pagehead(L, "Team", dark=True); rule(L)
    eyebrow(L, PAD, 104, "Who builds your project")
    heading(L, PAD, 122, [[("Our ", False), ("Team", True)]], size=46, color=PAPER)
    team = [("[Name]", "Lead UX Designer", "11 years experience"), ("[Name]", "UI Designer", "7 years experience"),
            ("[Name]", "Frontend Engineer", "9 years experience"), ("[Name]", "Backend Engineer", "10 years experience"),
            ("[Name]", "Content Strategist", "8 years experience"), ("[Name]", "QA & Accessibility", "6 years experience")]
    cols, gx, gy = 3, 20, 22
    cw = (PW - 2 * PAD - (cols - 1) * gx) / cols
    ph = cw * 1.18
    x0, y0 = PAD, 200
    for i, (nm, role, exp) in enumerate(team):
        cx = x0 + (i % cols) * (cw + gx)
        cy = y0 + (i // cols) * (ph + 78)
        photo(L, cx, cy, cw, ph, kind="corner", tag="Photo", slash=(i in (1, 4)))
        L.text([cx, cy + ph + 12, cw, 18], nm, style=t(12.5, PAPER, weight=600, family=DISPLAY, wrap=False))
        L.text([cx, cy + ph + 30, cw, 14], role, style=t(9.5, GOLD, family=DISPLAY, spacing=1.4, upper=True, wrap=False))
        L.text([cx, cy + ph + 46, cw, 14], exp, style=t(9, rgba(PAPER, 0.55), family=DISPLAY, spacing=0.8, wrap=False))
    pagefoot(L, "Our Team", "07", dark=True)
    return L


def p_site(doc):
    L = page(doc, "site", bg=PAPER)
    pagehead(L, "Scope"); rule(L)
    eyebrow(L, PAD, 104, "What we will build")
    heading(L, PAD, 122, [[("Your ", False), ("Website", True)]], size=46)
    body(L, PAD, 196, PW - 2 * PAD, "A responsive, accessible marketing site built on a modern "
         "component framework. The scope below is a starting point; we will confirm the final list "
         "together during planning.", h=60)
    feats = [("globe", "Responsive marketing site", "Up to 8 core templates, designed mobile-first and tuned for speed."),
             ("doc", "Content management", "Editable pages, blog and case studies through a headless CMS."),
             ("search", "SEO foundation", "Semantic markup, metadata, sitemap and analytics wired in."),
             ("shield", "Accessibility & security", "WCAG-aligned components, HTTPS, and form protection by default.")]
    fy = 300
    for ic, h4, ptext in feats:
        notch_tile(L, PAD, fy, 30, ic, fill=GOLD, ic=CHAR)
        L.text([PAD + 44, fy - 1, PW - 2 * PAD - 44, 16], h4, style=t(12, INK, weight=600, family=DISPLAY, wrap=False))
        body(L, PAD + 44, fy + 17, PW - 2 * PAD - 44, ptext, size=10, color="#54565A", lh=1.65, h=28)
        L.rect([PAD, fy + 52, PW - 2 * PAD, 1], fill=LINE, decorative=True)
        fy += 66
    # dark deliverables block (angular)
    dy = PH - 180
    L.polygon([[PAD, dy], [PW - PAD, dy], [PW - PAD, dy + 92], [PAD + 0.04 * (PW - 2 * PAD), dy + 92], [PAD, dy + 74]], fill=CHAR)
    L.text([PAD + 24, dy + 18, 400, 14], "Deliverables", style=t(9, GOLD, family=DISPLAY, spacing=2.7, upper=True, wrap=False))
    body(L, PAD + 24, dy + 38, PW - 2 * PAD - 48, "Design system, production codebase, CMS, documentation "
         "and a hand-off session — everything you need to run the site without us.", size=10.5, color=rgba(PAPER, 0.82), lh=1.7, h=44)
    pagefoot(L, "Your Website", "08")
    return L


def p_procicons(doc):
    L = page(doc, "procicons", bg=PAPER)
    pagehead(L, "Process"); rule(L)
    eyebrow(L, PAD, 104, "How we work")
    heading(L, PAD, 122, [[("Development", False)], [("Process", True)]], size=46, lh=1.0)
    steps = [("01", "Initial Planning", "bulb", "gold"), ("02", "Wireframing", "clip", "dark"),
             ("03", "Mockups", "img", "dark"), ("04", "Copy & Graphics", "pencil", "gold"),
             ("05", "Development", "gears", "gold"), ("06", "Testing", "shield", "dark"),
             ("07", "Deployment", "rocket", "dark"), ("08", "Optimization", "sliders", "gold")]
    cols, gx, gy = 2, 26, 22
    cw = (PW - 2 * PAD - gx) / cols
    ts = 116
    x0, y0 = PAD, 250
    for i, (no, nm, ic, kind) in enumerate(steps):
        cx = x0 + (i % cols) * (cw + gx)
        cy = y0 + (i // cols) * (ts + gy + 28)
        tile(L, cx, cy, ts, ic, kind=kind)
        L.text([cx + ts + 22, cy + ts / 2 - 18, cw - ts - 22, 12], f"Step {no}",
                style=t(9, GOLD, weight=600, family=DISPLAY, spacing=2.0, upper=True, wrap=False))
        L.text([cx + ts + 22, cy + ts / 2 - 4, cw - ts - 22, 22], nm,
                style=t(15, INK, weight=600, family=DISPLAY, wrap=False))
    pagefoot(L, "Development Process", "09")
    return L


def _pdetail(doc, pid, eyebrow_txt, head_runs, rows, pno):
    L = page(doc, pid, bg=PAPER)
    pagehead(L, "Process · Detail"); rule(L)
    eyebrow(L, PAD, 104, eyebrow_txt)
    heading(L, PAD, 122, [head_runs], size=46)
    ry = 224
    for no, nm, ic, kind, ptext in rows:
        tile(L, PAD, ry, 70, ic, kind=kind)
        ix = PAD + 92
        L.text([ix, ry, 360, 12], f"Step {no}", style=t(9, GOLD, weight=600, family=DISPLAY, spacing=2.4, upper=True, wrap=False))
        L.text([ix, ry + 14, 400, 20], nm, style=t(14, INK, weight=600, family=DISPLAY, wrap=False))
        body(L, ix, ry + 38, PW - PAD - ix, ptext, size=10.5, color="#54565A", lh=1.72, h=46)
        L.rect([PAD, ry + 92, PW - 2 * PAD, 1], fill=LINE, decorative=True)
        ry += 108
    pagefoot(L, "Process Detail", pno)
    return L


def p_pdetail1(doc):
    rows = [("01", "Initial Planning", "bulb", "gold", "We align on goals, audience and success metrics, audit the current site, and agree the scope, sitemap and a single definition of done."),
            ("02", "Wireframing", "clip", "dark", "Low-fidelity layouts establish structure and flow before any visual design, so we resolve hierarchy decisions early and cheaply."),
            ("03", "Mockups", "img", "dark", "High-fidelity designs apply your brand to the wireframes, producing the look and feel for every key template and state."),
            ("04", "Copy & Graphics", "pencil", "gold", "We write interface copy and prepare imagery and icons so the design ships with real content, not placeholder text.")]
    return _pdetail(doc, "pd1", "Steps 01–04", [("In ", False), ("Detail", True)], rows, "10")


def p_pdetail2(doc):
    rows = [("05", "Development", "gears", "gold", "Engineers build a component library and assemble pages against performance and accessibility budgets, reviewed continuously."),
            ("06", "Testing", "shield", "dark", "Cross-browser, device and accessibility testing, plus content review, before anything is considered ready to ship."),
            ("07", "Deployment", "rocket", "dark", "We launch on a modern hosting setup with monitoring, backups and a rollback plan, and walk your team through the handover."),
            ("08", "Optimization", "sliders", "gold", "After launch we measure real usage and iterate — refining speed, conversion and content against the goals set in planning.")]
    return _pdetail(doc, "pd2", "Steps 05–08", [("Build & ", False), ("Beyond", True)], rows, "11")


def p_timeline(doc):
    L = page(doc, "timeline", bg=PAPER)
    pagehead(L, "Schedule"); rule(L)
    eyebrow(L, PAD, 104, "From kickoff to launch")
    heading(L, PAD, 122, [[("Project ", False), ("Timeline", True)]], size=46)
    body(L, PAD, 196, 600, "An indicative ten-week schedule. Bars show the working window for each "
         "phase; some phases overlap. Exact dates are confirmed at kickoff. All durations are placeholders.", h=44)
    gx, gy, gw = PAD, 268, PW - 2 * PAD
    labw = 150
    trackw = gw - labw
    weeks = 10
    # header
    L.text([gx, gy, labw, 14], "PHASE", style=t(8.5, INK, weight=600, family=DISPLAY, spacing=0.6, wrap=False))
    for w in range(weeks):
        wx = gx + labw + trackw * w / weeks
        L.text([wx, gy, trackw / weeks, 14], f"W{w + 1}", style=t(8.5, MUTE2, family=DISPLAY, align="center", wrap=False))
    L.rect([gx, gy + 20, gw, 2], fill=INK)
    rows = [("Initial Planning", 0.0, 0.20, True), ("Wireframing", 0.15, 0.20, False),
            ("Mockups", 0.28, 0.22, False), ("Design Approval", 0.46, 0.10, True),
            ("Development", 0.50, 0.32, False), ("Testing", 0.72, 0.16, True),
            ("Deployment", 0.86, 0.09, False), ("Optimization", 0.90, 0.10, True)]
    ry = gy + 30
    rh = 38
    for lab, left, wfrac, dark in rows:
        L.text([gx, ry + rh / 2 - 7, labw - 10, 16], lab, style=t(10, INK, weight=500, family=DISPLAY, wrap=False))
        bx = gx + labw + trackw * left
        bw = trackw * wfrac
        L.rect([bx, ry + rh / 2 - 7, bw, 14], fill=(CHAR if dark else GOLD), radius=2)
        L.rect([gx, ry + rh, gw, 1], fill=LINE, decorative=True)
        ry += rh
    body(L, PAD, PH - 210, 600, "Milestones — design sign-off in Week 5, code freeze in Week 9, go-live "
         "at the end of Week 10. Optimization continues into a post-launch care period agreed separately.",
         size=10, color="#54565A", lh=1.7, h=44)
    # legend
    ly = PH - 150
    L.rect([PAD, ly, 22, 10], fill=GOLD, radius=1)
    L.text([PAD + 30, ly - 2, 220, 14], "Design & build phases", style=t(9.5, MUTE2, wrap=False))
    L.rect([PAD + 230, ly, 22, 10], fill=CHAR, radius=1)
    L.text([PAD + 260, ly - 2, 240, 14], "Review & release phases", style=t(9.5, MUTE2, wrap=False))
    pagefoot(L, "Project Timeline", "12")
    return L


def p_pricing(doc):
    L = page(doc, "pricing", bg=PAPER)
    pagehead(L, "Investment"); rule(L)
    eyebrow(L, PAD, 104, "Transparent investment")
    heading(L, PAD, 122, [[("Pricing", True)]], size=46)
    rows = [("Discovery & Planning", "Workshops, audit, sitemap and scope.", "$0,000"),
            ("UX & UI Design", "Wireframes, mockups and design system.", "$0,000"),
            ("Development", "Frontend, CMS integration and APIs.", "$00,000"),
            ("Content & Graphics", "Copy support, imagery and icon set.", "$0,000"),
            ("Testing & Launch", "QA, accessibility, deployment.", "$0,000")]
    ry = 196
    for h4, desc, amt in rows:
        L.text([PAD, ry, 360, 16], h4, style=t(12.5, INK, weight=600, family=DISPLAY, wrap=False))
        L.text([PAD, ry + 18, 360, 14], desc, style=t(9.5, MUTE2, wrap=False))
        L.text([PW - PAD - 160, ry, 160, 22], amt, style=t(18, INK, weight=LIGHT, family=DISPLAY, align="right", wrap=False))
        L.rect([PAD, ry + 44, PW - 2 * PAD, 1], fill=LINE, decorative=True)
        ry += 60
    # total (gold angular)
    ty = ry + 8
    L.polygon([[PAD, ty], [PW - PAD, ty], [PW - PAD, ty + 58], [PAD + 0.04 * (PW - 2 * PAD), ty + 58], [PAD, ty + 44]], fill=GOLD)
    L.text([PAD + 22, ty + 18, 300, 20], "Estimated Total", style=t(13, CHAR, weight=600, family=DISPLAY, wrap=False))
    L.text([PW - PAD - 180, ty + 14, 158, 28], "$00,000", style=t(24, CHAR, weight=600, family=DISPLAY, align="right", wrap=False))
    body(L, PAD, PH - 130, PW - 2 * PAD, "All figures are placeholders for layout only and are not a quote. "
         "Replace with your own verified pricing. Taxes, third-party licences and ongoing hosting are excluded unless stated.",
         size=8.5, color=MUTE, lh=1.6, h=40)
    pagefoot(L, "Pricing", "13")
    return L


def p_terms(doc):
    L = page(doc, "terms", bg=PAPER2)
    pagehead(L, "Terms"); rule(L)
    eyebrow(L, PAD, 104, "The agreement")
    heading(L, PAD, 122, [[("Project ", False), ("Terms", True)]], size=46)
    clauses = [("01", "Scope & Changes", "Work covers the deliverables listed in this proposal. Changes are quoted separately before any additional work begins."),
               ("02", "Payment", "An initial deposit secures the schedule, with the balance billed at agreed milestones. Invoices are due within the stated period."),
               ("03", "Timeline", "The schedule assumes timely feedback and content. Delays in either may shift dependent dates accordingly."),
               ("04", "Revisions", "Each design stage includes a set number of revision rounds. Further rounds are available at an agreed rate."),
               ("05", "Ownership", "On final payment, ownership of the delivered work transfers to the client, excluding third-party and licensed assets."),
               ("06", "Confidentiality", "Both parties keep shared materials confidential and use them only for the purpose of this project."),
               ("07", "Warranty", "We correct defects reported within an agreed window after launch at no charge. New features fall outside this warranty."),
               ("08", "Termination", "Either party may end the engagement in writing. Work completed to that point remains payable.")]
    colw = (PW - 2 * PAD - 26) / 2
    col_y = [196, 196]
    for i, (no, h4, ptext) in enumerate(clauses):
        col = i % 2
        cx = PAD + col * (colw + 26)
        cy = col_y[col]
        L.add({"type": "text", "box": [cx, cy, colw, 14],
               "spans": [{"text": no + "  ", "style": {"font_family": DISPLAY, "font_size": 10.5, "font_weight": 600, "color": GOLD}},
                         {"text": h4, "style": {"font_family": DISPLAY, "font_size": 10.5, "font_weight": 600, "color": INK}}],
               "style": {"font_family": DISPLAY, "font_size": 10.5, "font_weight": 600, "color": INK}})
        body(L, cx, cy + 18, colw, ptext, size=9.5, color="#54565A", lh=1.7, h=70)
        col_y[col] += 96
    # rotated stamp
    sx, sy = PW - PAD - 74, PH - 150
    with L.frame(sx + 37, sy + 37, rotate=-12) as f:
        f.circle([0, 0], 37, fill="none", stroke=GOLD, stroke_style={"stroke_width": 2})
        f.text([-37, -12, 74, 16], "DRAFT", style=t(9, GOLD, weight=600, family=DISPLAY, spacing=1.2, align="center", wrap=False))
        f.text([-37, 2, 74, 16], "NOT BINDING", style=t(8, GOLD, weight=600, family=DISPLAY, spacing=1.0, align="center", wrap=False))
    pagefoot(L, "Project Terms", "14")
    return L


def p_back(doc):
    L = page(doc, "back", bg=PAPER)
    L.polygon([[PW * 0.34, 0], [PW, 0], [PW, PH], [0, PH]], fill=CHAR, decorative=True)
    L.add({"type": "polyline", "points": [[PW * 0.48, 0], [PW, 0], [PW, PH * 0.64], [0, PH]], "closed": True,
           "fill": rgba(CHAR2, 0.5), "decorative": True})
    L.polygon([[PW * 0.40, PH * 0.46], [PW * 0.40 + 90, PH * 0.46], [PW * 0.40 + 90, PH * 0.46 + 21], [PW * 0.40, PH * 0.46 + 26]], fill=GOLD)
    # center block
    cyf = PH * 0.46
    mark(L, PAD, cyf - 120, 30)
    heading(L, PAD, cyf - 76, [[("Let's build", False)], [("something", False)], [("worth visiting.", True)]], size=34, color=INK, lh=1.06, w=300)
    body(L, PAD, cyf + 64, 230, "We would be glad to talk it through and tailor this proposal to your goals.",
         size=11, color=MUTE2, lh=1.7, h=60)
    # contact
    contacts = [("Email", "hello@lumenco.example"), ("Phone", "+00 000 000 0000"), ("Web", "lumenco.example")]
    ccx = PAD
    for lab, val in contacts:
        L.text([ccx, PH - 70, 140, 12], lab, style=t(8, GOLD, family=DISPLAY, spacing=2.6, upper=True, wrap=False))
        L.text([ccx, PH - 56, 150, 14], val, style=t(10, INK, wrap=False))
        ccx += 150
    # thanks (on dark)
    L.text([PW - 360, PH - 92, 320, 30], "Thank you.", style=t(26, PAPER, weight=EXLIGHT, family=DISPLAY, align="right", wrap=False))
    L.text([PW - 360, PH - 58, 320, 14], "Lumen & Co.", style=t(9, rgba(PAPER, 0.55), family=DISPLAY, spacing=2.6, upper=True, align="right", wrap=False))
    return L


# --------------------------------------------------------------------------- #
#  Showcase scene — gold field + marble disc + 3 perspective mini-pages        #
# --------------------------------------------------------------------------- #
def _mini_cover(f):
    f.rect([0, 0, 210, 297], fill=PAPER)
    f.polygon([[0, 0], [210, 0], [210, 172], [0, 297]], fill=CHAR)
    f.polygon([[180, 0], [188, 0], [188, 70], [180, 80]], fill=GOLD)
    f.rect([14, 150, 66, 85], fill=rgba("#9a9a98", 1.0))
    f.text([14, 150, 90, 18], "Web", style=t(20, GOLD, weight=EXLIGHT, family=DISPLAY, wrap=False))
    f.text([14, 172, 120, 16], "Design", style=t(18, PAPER, weight=EXLIGHT, family=DISPLAY, wrap=False))
    f.text([14, 192, 120, 16], "Proposal", style=t(18, PAPER, weight=EXLIGHT, family=DISPLAY, wrap=False))


def _mini_vision(f):
    f.rect([0, 0, 210, 297], fill=CHAR)
    f.rect([18, 30, 40, 3], fill=GOLD)
    f.text([18, 40, 170, 18], "Vision &", style=t(17, PAPER, weight=EXLIGHT, family=DISPLAY, wrap=False))
    f.text([18, 58, 170, 18], "Mission", style=t(17, PAPER, weight=600, family=DISPLAY, wrap=False))
    f.polygon([[18, 96], [192, 88], [192, 150], [18, 158]], fill=rgba("#9a9a98", 1.0))
    for i in range(3):
        f.rect([18, 180 + i * 30, 2, 22], fill=GOLD)
        f.rect([28, 184 + i * 30, 150, 4], fill=rgba(PAPER, 0.5))


def _mini_timeline(f):
    f.rect([0, 0, 210, 297], fill=PAPER)
    f.rect([18, 30, 40, 3], fill=GOLD)
    f.text([18, 40, 170, 18], "Project", style=t(16, INK, weight=EXLIGHT, family=DISPLAY, wrap=False))
    f.text([18, 57, 170, 18], "Timeline", style=t(16, INK, weight=600, family=DISPLAY, wrap=False))
    bars = [(0.0, 0.2, True), (0.15, 0.2, False), (0.28, 0.22, False), (0.46, 0.1, True),
            (0.5, 0.32, False), (0.72, 0.16, True), (0.86, 0.12, False)]
    for i, (l, w, d) in enumerate(bars):
        y = 110 + i * 22
        f.rect([18, y, 174, 1], fill=LINE)
        f.rect([18 + 174 * l, y - 8, 174 * w, 9], fill=(CHAR if d else GOLD), radius=1)


def p_showcase(doc):
    L = page(doc, "showcase", bg=GOLD)
    L.add({"type": "ellipse", "center": [PW / 2, PH * 0.10], "rx": PW * 0.9, "ry": PH * 0.6,
           "fill": radial_gradient([("#FFD64D", 0), (GOLD, 46), ("#E0A704", 100)]), "decorative": True})
    # marble disc
    L.add({"type": "ellipse", "center": [PW / 2, PH * 0.52], "rx": 360, "ry": 360,
           "fill": radial_gradient([("#FFFFFF", 0), ("#F3F2EE", 46), ("#E7E6E0", 72), ("#DCDBD4", 100)],
                                   at="38% 34%"), "decorative": True})
    # header
    L.text([PAD, 70, PW - 2 * PAD, 16], "STUDIO PROPOSAL  /  TEMPLATE",
           style=t(11, CHAR, weight=700, family=DISPLAY, spacing=4.2, align="center", upper=True, wrap=False))
    L.add({"type": "text", "box": [PAD, 92, PW - 2 * PAD, 56],
           "spans": [{"text": "Web", "style": {"font_family": DISPLAY, "font_size": 46, "font_weight": 700, "color": CHAR}},
                     {"text": " Design Proposal", "style": {"font_family": DISPLAY, "font_size": 46, "font_weight": EXLIGHT, "color": CHAR}}],
           "style": {"font_family": DISPLAY, "font_size": 46, "font_weight": EXLIGHT, "color": CHAR, "align": "center"}})
    L.text([PW / 2 - 280, 156, 560, 50], "A complete editorial proposal booklet — cover, about, board, team, "
           "process, timeline, pricing and terms. Every page is one FrameForge document.",
           style=t(12, "#5B4A08", lh=1.6, align="center"))
    # three perspective minis (shadow + body + glare)
    def placed(cx, cy, scale, rot, drawer):
        w, h = 210 * scale, 297 * scale
        L.add({"type": "ellipse", "center": [cx, cy + h / 2 + 18], "rx": w * 0.6, "ry": 22,
               "fill": rgba("#3C2D00", 0.34), "decorative": True})
        with L.frame(cx - w / 2, cy - h / 2, scale=scale, rotate=rot) as f:
            drawer(f)
            f.add({"type": "rect", "box": [0, 0, 210, 297],
                   "fill": linear_gradient([(rgba(PAPER, 0.30), 0), (rgba(PAPER, 0), 22),
                                            (rgba(PAPER, 0), 78), (rgba("#000000", 0.06), 100)], angle=108),
                   "decorative": True})

    mid = PH * 0.54
    placed(PW / 2 - 250, mid + 14, 1.06, -5, _mini_vision)
    placed(PW / 2 + 250, mid + 14, 1.06, 5, _mini_timeline)
    placed(PW / 2, mid - 18, 1.26, 0, _mini_cover)
    L.text([PAD, PH - 70, PW - 2 * PAD, 16], "LUMEN & CO. — DIGITAL DESIGN STUDIO",
           style=t(9.5, "#5B4A08", family=DISPLAY, spacing=3.0, align="center", upper=True, wrap=False))
    return L


# =========================================================================== #
def build_document():
    doc = DocumentBuilder(title="Web Design Proposal — Template", profile="report", lang="en")
    p_showcase(doc)
    p_cover(doc)
    p_about(doc)
    p_vision(doc)
    p_letter(doc)
    p_toc(doc)
    p_directors(doc)
    p_team(doc)
    p_site(doc)
    p_procicons(doc)
    p_pdetail1(doc)
    p_pdetail2(doc)
    p_timeline(doc)
    p_pricing(doc)
    p_terms(doc)
    p_back(doc)
    return doc


doc = build_document()


def main() -> int:
    from frameforge.sdk.validate import validate_static_rules
    built = doc.build()
    rep = validate_static_rules(built)
    errs = [i for i in rep.issues if i.severity == "error"]
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "web", "web-design-proposal.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(built, format="yaml"))
    print(f"web-design-proposal: {len(built.pages)} pages, ok={rep.ok}, errors={len(errs)} -> {out}")
    for i in errs[:20]:
        print("  ERROR:", i.code, i.message)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
