#!/usr/bin/env python3
"""A styled FrameForge rendition of docs/output-space.md.

The output-space record, composed AS a FrameForge document — a five-page dark
concept deck authored entirely through the SDK, with custom line-art icons, a
hero "one IR → many outputs" starburst, and a low-discrepancy starfield for
depth. It dogfoods the very primitives (paths, polylines, arcs, regular polygons,
arrows) the doc says a `ScenePainter` lowers.

    uv run python examples/output_space_poster.py     # writes _tmp/output-space/*

Exposes `build() -> DocumentBuilder` (the MCP run contract).
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, HERE)
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, render_page_svgs, serialize  # noqa: E402
from frameforge.sdk.layout import grid, row  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1280, 760
MX = 72

# ---- seed canonical · LIGHT palette (examples/frameforge_seed_deck.py) ------ #
BG = "#FBFAF6"              # PAPER — warm technical paper, the default surface
PANEL = "#FFFFFF"          # CANVAS — pure card surface
PANEL2 = "#F3F5F9"         # faint tint surface (secondary cards)
INK = "#15181E"            # graphite text/lines (never pure black)
MUTE = "#6B7280"           # captions, secondary text
FAINT = "#9AA0AB"          # tertiary / chrome labels
LINE = "#D4D8DE"           # GRID — hairlines, the drafting grid
ACCENT = "#1F4FD8"         # FRAME-blue — primary accent (the "Frame" half)
LIVE = "#1E9E5A"           # gate-green — wired / in-sync
BLUE = "#1F4FD8"           # renditions — the canonical render family (FRAME)
TEAL = "#12B0C3"           # GRAPH-cyan — hand-offs
VIOLET = "#7C3AED"         # derivatives (brand violet, from the seed cover field)
AMBER = "#F5A623"          # the hub
RED = "#D23B2B"            # drift-red — boundaries

SANS = ["IBM Plex Sans", "DejaVu Sans", "Helvetica", "Arial", "sans-serif"]
MONO = ["IBM Plex Mono", "DejaVu Sans Mono", "Menlo", "monospace"]


def _rgb(c):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def tint(color, a, base=BG):
    """A SOLID pale colour: ``color`` blended ``a`` of the way over ``base`` (the
    paper ground). Solid hex renders identically in every backend — unlike an
    ``#RRGGBBAA`` alpha fill, which CairoSVG (the `pdf` target) flattens to solid.
    Keeps the SVG, PNG and PDF renders in lock-step."""
    cr, cg, cb = _rgb(color)
    br, bg_, bb = _rgb(base)
    m = lambda c, b: round(c * a + b * (1 - a))            # noqa: E731
    return f"#{m(cr, br):02X}{m(cg, bg_):02X}{m(cb, bb):02X}"


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None,
       family=None, transform=None):
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


def _st(w=1.8):
    return {"stroke_width": w, "stroke_linecap": "round", "stroke_linejoin": "round"}


# --------------------------------------------------------------------------- #
# Custom line-art icons — each draws centred at (cx, cy), half-extent ~s.
# --------------------------------------------------------------------------- #
def _pl(pg, pts, c, w=1.6, closed=False):
    pg.polyline(pts, closed=closed, fill="none", stroke=c, stroke_style=_st(w))


def ic_doc(pg, cx, cy, s, c):
    w, h = s * 1.3, s * 1.7
    x, y = cx - w / 2, cy - h / 2
    pg.rect([x, y, w, h], radius=3, fill="none", stroke=c, stroke_style=_st(1.5))
    for i in range(3):
        yy = y + h * 0.3 + i * h * 0.2
        pg.line([x + w * 0.22, yy], [x + w * 0.78, yy], stroke=c, stroke_style=_st(1.3))


def ic_model(pg, cx, cy, s, c):
    pts = [(cx + math.cos(math.radians(a)) * s * 0.82,
            cy + math.sin(math.radians(a)) * s * 0.82) for a in (-90, 35, 150)]
    for p in pts:
        pg.line([cx, cy], list(p), stroke=c, stroke_style=_st(1.3))
    pg.ellipse([cx, cy], s * 0.26, s * 0.26, fill=c)
    for p in pts:
        pg.ellipse(list(p), s * 0.2, s * 0.2, fill=BG, stroke=c, stroke_style=_st(1.4))


def ic_layers(pg, cx, cy, s, c):
    for dy in (s * 0.52, 0.0, -s * 0.52):
        _pl(pg, [[cx - s, cy + dy], [cx, cy + dy - s * 0.46],
                 [cx + s, cy + dy], [cx, cy + dy + s * 0.46]], c, 1.4, closed=True)


def ic_port(pg, cx, cy, s, c):
    pg.regular_polygon([cx, cy], s, 6, rotation=-90, fill="none", stroke=c, stroke_style=_st(1.6))
    pg.ellipse([cx, cy], s * 0.3, s * 0.3, fill=c)


def ic_out(pg, cx, cy, s, c):
    pg.ellipse([cx + s * 0.55, cy], s * 0.42, s * 0.42, fill="none", stroke=c, stroke_style=_st(1.5))
    pg.arrow([cx - s, cy], [cx + s * 0.18, cy], color=c, width=1.7, head=6)


def ic_svg(pg, cx, cy, s, c):
    pg.polyline([[cx - s, cy + s * 0.5], [cx - s * 0.2, cy - s * 0.7],
                 [cx + s * 0.3, cy + s * 0.6], [cx + s, cy - s * 0.5]],
                smooth=True, fill="none", stroke=c, stroke_style=_st(1.7))
    for px, py in [(cx - s, cy + s * 0.5), (cx + s, cy - s * 0.5)]:
        pg.rect([px - 2.6, py - 2.6, 5.2, 5.2], fill=BG, stroke=c, stroke_style=_st(1.4))


def ic_grid(pg, cx, cy, s, c):
    cell = s * 0.62
    for r in range(3):
        for col in range(3):
            x, y = cx - cell * 1.5 + col * cell, cy - cell * 1.5 + r * cell
            on = (r + col) % 2 == 0
            pg.rect([x + 1, y + 1, cell - 2, cell - 2], radius=1,
                    fill=c if on else "none", stroke=c, stroke_style=_st(1.1))


def ic_page(pg, cx, cy, s, c):
    w, h = s * 1.3, s * 1.7
    x, y = cx - w / 2, cy - h / 2
    f = w * 0.36
    _pl(pg, [[x, y], [x + w - f, y], [x + w, y + f], [x + w, y + h], [x, y + h]], c, 1.5, closed=True)
    _pl(pg, [[x + w - f, y], [x + w - f, y + f], [x + w, y + f]], c, 1.3)


def ic_code(pg, cx, cy, s, c):
    _pl(pg, [[cx - s * 0.35, cy - s * 0.75], [cx - s, cy], [cx - s * 0.35, cy + s * 0.75]], c, 1.7)
    _pl(pg, [[cx + s * 0.35, cy - s * 0.75], [cx + s, cy], [cx + s * 0.35, cy + s * 0.75]], c, 1.7)
    pg.line([cx + s * 0.18, cy - s * 0.85], [cx - s * 0.18, cy + s * 0.85], stroke=c, stroke_style=_st(1.4))


def ic_braces(pg, cx, cy, s, c):
    for sgn in (-1, 1):
        x = cx + sgn * s * 0.55
        _pl(pg, [[x + sgn * s * 0.45, cy - s], [x, cy - s * 0.55], [x, cy - s * 0.16],
                 [x - sgn * s * 0.3, cy], [x, cy + s * 0.16], [x, cy + s * 0.55],
                 [x + sgn * s * 0.45, cy + s]], c, 1.5)


def ic_book(pg, cx, cy, s, c):
    pg.line([cx, cy - s * 0.85], [cx, cy + s * 0.8], stroke=c, stroke_style=_st(1.4))
    for sgn in (-1, 1):
        _pl(pg, [[cx, cy - s * 0.85], [cx + sgn * s, cy - s * 0.55],
                 [cx + sgn * s, cy + s * 0.8], [cx, cy + s * 0.55]], c, 1.4)


def ic_rings(pg, cx, cy, s, c):
    for rr in (s, s * 0.64, s * 0.3):
        pg.ellipse([cx, cy], rr, rr, fill="none", stroke=c, stroke_style=_st(1.4))
    pg.ellipse([cx, cy], 1.8, 1.8, fill=c)


def ic_sqrt(pg, cx, cy, s, c):
    _pl(pg, [[cx - s, cy + s * 0.05], [cx - s * 0.55, cy + s * 0.7],
             [cx - s * 0.1, cy - s * 0.85], [cx + s, cy - s * 0.85]], c, 1.7)
    pg.line([cx + s, cy - s * 0.85], [cx + s, cy - s * 0.45], stroke=c, stroke_style=_st(1.5))


def ic_import(pg, cx, cy, s, c):
    pg.rect([cx + s * 0.1, cy - s, s * 1.05, s * 2], radius=3, fill="none", stroke=c, stroke_style=_st(1.4))
    pg.arrow([cx - s * 1.25, cy], [cx + s * 0.2, cy], color=c, width=1.7, head=6)


def ic_overlap(pg, cx, cy, s, c):
    pg.rect([cx - s, cy - s * 0.75, s * 1.4, s * 1.4], radius=3, fill="none", stroke=c, stroke_style=_st(1.5))
    pg.ellipse([cx + s * 0.35, cy + s * 0.25], s * 0.72, s * 0.72, fill="none", stroke=c, stroke_style=_st(1.5))


def ic_handoff(pg, cx, cy, s, c):
    ic_doc(pg, cx - s * 0.55, cy, s * 0.78, c)
    pg.arrow([cx + s * 0.25, cy], [cx + s * 1.2, cy], color=c, width=1.7, head=6)


def ic_branch(pg, cx, cy, s, c):
    pg.ellipse([cx - s, cy], s * 0.24, s * 0.24, fill=c)
    for ey in (cy - s * 0.72, cy, cy + s * 0.72):
        _pl(pg, [[cx - s + s * 0.24, cy], [cx, cy], [cx, ey], [cx + s, ey]], c, 1.4)
        pg.ellipse([cx + s, ey], s * 0.2, s * 0.2, fill=BG, stroke=c, stroke_style=_st(1.3))


def ic_spark(pg, cx, cy, s, c):
    for a in (0, 45, 90, 135):
        r = math.radians(a)
        pg.line([cx - math.cos(r) * s, cy - math.sin(r) * s],
                [cx + math.cos(r) * s, cy + math.sin(r) * s], stroke=c, stroke_style=_st(1.4))
    pg.ellipse([cx, cy], s * 0.24, s * 0.24, fill=c)


# --------------------------------------------------------------------------- #
# Background — the seed canonical light ground: warm paper + a faint drafting
# grid, framed by technical-drawing corner brackets (the "Frame" motif).
# --------------------------------------------------------------------------- #
def graph_paper(pg, step=96):
    x = step
    while x < W:
        pg.line([x, 0], [x, H], stroke=LINE, stroke_style={"stroke_width": 0.5}, decorative=True)
        x += step
    y = step
    while y < H:
        pg.line([0, y], [W, y], stroke=LINE, stroke_style={"stroke_width": 0.5}, decorative=True)
        y += step


def corner_brackets(pg, *, color=INK, inset=30, arm=22, sw=1.6):
    for x, y, dx, dy in [(inset, inset, 1, 1), (W - inset, inset, -1, 1),
                         (inset, H - inset, 1, -1), (W - inset, H - inset, -1, -1)]:
        pg.line([x, y], [x + dx * arm, y], stroke=color, stroke_style={"stroke_width": sw})
        pg.line([x, y], [x, y + dy * arm], stroke=color, stroke_style={"stroke_width": sw})


def ground(pg):
    pg.rect([0, 0, W, H], fill=BG)
    graph_paper(pg)
    corner_brackets(pg)


# --------------------------------------------------------------------------- #
# Page chrome + composite helpers
# --------------------------------------------------------------------------- #
def page(b, pid, kicker, title):
    pg = b.page(pid, canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    pg._lettering_depth += 1
    pg.layer("bg")
    ground(pg)
    pg.layer("head")
    pg.text([MX, 44, W - 2 * MX, 16], kicker,
            style=ts(11.5, ACCENT, family=MONO, weight=700, spacing=2.4, transform="uppercase"))
    pg.text([MX, 62, W - 2 * MX, 40], title, style=ts(33, INK, weight=800, spacing=-0.6))
    pg.text([MX, H - 42, W - 2 * MX, 16], "FrameForge · the output space",
            style=ts(10.5, MUTE, family=MONO, weight=600, spacing=0.8))
    pg.text([W - MX - 120, H - 42, 120, 16], "p." + pid.replace("p", "0") + " / 05",
            style=ts(10.5, MUTE, family=MONO, align="right", spacing=0.5))
    pg.layer("body")
    return pg


def card(pg, box, *, title, sub=None, accent=ACCENT, fill=PANEL, title_size=15,
         tag=None, mono_sub=False, icon=None, foot=None, foot_color=None):
    x, y, w, h = box
    pg.rect([x, y, w, h], radius=12, fill=fill, stroke=LINE, stroke_style={"stroke_width": 1.2})
    pg.rect([x, y + 14, 4, h - 28], radius=2, fill=accent)
    if icon is not None:
        pg.ellipse([x + w - 28, y + 28], 16, 16,
                   fill=tint(accent, 0.10), stroke=tint(accent, 0.38), stroke_style={"stroke_width": 1})
        icon(pg, x + w - 28, y + 28, 8.5, accent)
    tw = w - (52 if icon else 30)
    pg.text([x + 18, y + 16, tw, 22], title, style=ts(title_size, INK, weight=750))
    if tag is not None:
        cw = 16 + len(tag) * 6.4
        pg.rect([x + w - cw - 14, y + 15, cw, 18], radius=9, fill=tint(accent, 0.14),
                stroke=accent, stroke_style={"stroke_width": 1})
        pg.text([x + w - cw - 14, y + 17, cw, 14], tag,
                style=ts(9.5, accent, weight=700, align="center", spacing=0.6))
    if sub is not None:
        pg.text([x + 18, y + 16 + title_size + 8, w - 34, h - title_size - 30], sub,
                style=ts(10.5, MUTE, lh=1.4, family=MONO if mono_sub else SANS))
    if foot is not None:
        pg.text([x + 18, y + h - 26, w - 30, 16], foot,
                style=ts(9.5, foot_color or accent, family=MONO, weight=600))


def chip(pg, x, y, label, accent):
    w = 16 + len(label) * 6.6
    pg.rect([x, y, w, 24], radius=12, fill=tint(accent, 0.12), stroke=accent, stroke_style={"stroke_width": 1})
    pg.ellipse([x + 12, y + 12], 3, 3, fill=accent)
    pg.text([x + 20, y + 4, w, 16], label, style=ts(11, accent, weight=650))
    return w + 18 + 9


def bullets(pg, x, y, items, accent=ACCENT, gap=24, size=11.5, w=360):
    for i, it in enumerate(items):
        yy = y + i * gap
        pg.ellipse([x + 3, yy + 7], 2.6, 2.6, fill=accent)
        pg.text([x + 14, yy, w - 14, gap], it, style=ts(size, MUTE, lh=1.3))


def callout(pg, box, *, label, icon, accent=ACCENT):
    """A sober emphasis box: a neutral white card with ONE thin accent rule and a
    small icon that differentiates it — instead of a saturated, per-slide colour
    fill (which broke the visual flow). Returns (x, w, y) for the body text."""
    x, y, w, h = box
    pg.rect([x, y, w, h], radius=14, fill=PANEL, stroke=LINE, stroke_style={"stroke_width": 1.2})
    pg.rect([x, y + 16, 3.5, h - 32], radius=2, fill=accent)
    icon(pg, x + 32, y + 27, 8, accent)
    pg.text([x + 48, y + 20, w - 90, 16], label,
            style=ts(10.5, FAINT, family=MONO, weight=700, spacing=1.7, transform="uppercase"))
    return x + 24, w - 48, y + 42


# --------------------------------------------------------------------------- #
# The hero — one IR node, many output spokes.
# --------------------------------------------------------------------------- #
def hero(pg, cx, cy, R):
    spokes = [
        ("SVG", BLUE), ("PDF", TEAL), ("PNG", BLUE), ("HTML", TEAL),
        ("EPUB", TEAL), ("DOCX", TEAL), ("PDF/UA", VIOLET), ("glTF", VIOLET),
        ("DOT", VIOLET), ("Schema", VIOLET), ("Index", VIOLET), ("Braille", VIOLET),
    ]
    n = len(spokes)
    for i, (lab, c) in enumerate(spokes):
        a = math.radians(-90 + i * 360.0 / n)
        ca, sa = math.cos(a), math.sin(a)
        sx, sy = cx + ca * 40, cy + sa * 40
        ex, ey = cx + ca * R, cy + sa * R
        pg.line([sx, sy], [ex, ey], stroke=tint(c, 0.42), stroke_style=_st(1.3))
        pg.ellipse([ex, ey], 3.4, 3.4, fill=c)
        lx = ex + ca * 14
        ly = ey + sa * 10
        al = "start" if ca > 0.25 else "end" if ca < -0.25 else "center"
        ox = lx if al == "start" else lx - 70 if al == "end" else lx - 35
        pg.text([ox, ly - 7, 70, 13], lab,
                style=ts(9.5, c, weight=650, align=al))
    # central IR node
    pg.regular_polygon([cx, cy], 38, 6, rotation=-90, fill=PANEL, stroke=ACCENT, stroke_style=_st(2.2))
    pg.regular_polygon([cx, cy], 38, 6, rotation=-90, fill="none", stroke=tint(ACCENT, 0.20), stroke_style=_st(8))
    ic_model(pg, cx, cy - 4, 13, ACCENT)
    pg.text([cx - 40, cy + 13, 80, 14], "the IR", style=ts(10, INK, weight=700, align="center"))


# --------------------------------------------------------------------------- #
# Page 1 — cover
# --------------------------------------------------------------------------- #
def cover(b):
    pg = b.page("p1", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    pg._lettering_depth += 1
    pg.layer("bg")
    ground(pg)
    pg.layer("art")
    hero(pg, 968, 392, 168)
    pg.layer("body")
    pg.text([MX, 96, 720, 18], "FRAMEFORGE · CONCEPT RECORD",
            style=ts(12.5, ACCENT, family=MONO, weight=700, spacing=3.0, transform="uppercase"))
    pg.text([MX, 128, 760, 90], "The output space", style=ts(72, INK, weight=800, spacing=-2))
    pg.text([MX, 230, 560, 60],
            "Everything FrameForge can generate — concretely (wired today) and "
            "conceptually (what the architecture admits).", style=ts(17, MUTE, lh=1.45))

    bx, bw, by = callout(pg, [MX, 380, 560, 144],
                         label="THE GENERATING PRINCIPLE", icon=ic_port)
    pg.text([bx, by, bw, 96],
            "FrameForge is not a renderer — it is a verifiable IR for visual "
            "documents. An output is possible iff (a) the model can express the "
            "semantics, and (b) an adapter maps the display-list to the target. "
            "The limit is IR expressiveness and adapters — never the architecture.",
            style=ts(14, INK, lh=1.5))

    x = MX
    for lab, c in [("Wired today", LIVE), ("Renditions", BLUE), ("Hand-offs", TEAL),
                   ("Derivatives", VIOLET), ("The hub", AMBER), ("Boundaries", RED)]:
        x += chip(pg, x, 566, lab, c)
    return pg


# --------------------------------------------------------------------------- #
# Page 2 — the pipeline
# --------------------------------------------------------------------------- #
def pipeline(b):
    pg = page(b, "p2", "§ The generating principle", "One pipeline, the whole space")
    stages = [
        ("Authoring", "YAML · SDK", ACCENT, ic_doc),
        ("Document model", "the source of truth", LIVE, ic_model),
        ("Renderer", "resolve + z-order walk", BLUE, ic_layers),
        ("ScenePainter port", "primitive display-list", VIOLET, ic_port),
        ("Backend adapter", "emits the target", AMBER, ic_out),
    ]
    boxes = row([MX, 205, W - 2 * MX, 188], len(stages), gap=44)
    for (name, sub, c, ic), box in zip(stages, boxes):
        x, y, w, h = box
        pg.rect([x, y, w, h], radius=13, fill=PANEL2, stroke=LINE, stroke_style={"stroke_width": 1.2})
        pg.rect([x, y, w, 4], radius=2, fill=c)
        pg.ellipse([x + w / 2, y + 54], 26, 26, fill=tint(c, 0.10), stroke=tint(c, 0.40), stroke_style={"stroke_width": 1.2})
        ic(pg, x + w / 2, y + 54, 13, c)
        pg.text([x + 10, y + 96, w - 20, 20], name, style=ts(14.5, INK, weight=750, align="center"))
        pg.text([x + 10, y + 120, w - 20, 16], sub, style=ts(10, MUTE, align="center"))
    for i in range(len(stages) - 1):
        bx, nx = boxes[i], boxes[i + 1]
        pg.arrow([bx[0] + bx[2] + 5, bx[1] + 54], [nx[0] - 5, nx[1] + 54],
                 color=FAINT, width=2.2, head=10)

    pg.text([MX, 432, W - 2 * MX, 22],
            "An output exists iff the model can express it AND an adapter can draw it.",
            style=ts(15, MUTE, lh=1.4))
    g = row([MX, 472, W - 2 * MX, 206], 2, gap=40)
    card(pg, g[0], title="(a)  IR expressiveness", icon=ic_model, accent=LIVE,
         sub="Pages, layers, vector / text / image primitives, flow + typesetting "
             "semantics, styles, a 3D scene graph, and an accessibility vocabulary "
             "(reading_order · alt · decorative). If the model can say it, a "
             "backend can be written for it.")
    card(pg, g[1], title="(b)  An adapter exists", icon=ic_port, accent=VIOLET,
         sub="A ScenePainter (or model-walker) maps the resolved display-list to a "
             "concrete target. Fidelity degrades only where a target cannot hold "
             "an IR feature — gradients flatten in TikZ; flow degrades in the HTML "
             "path. No renderer is conformant; proxies are sanity checks.")
    return pg


# --------------------------------------------------------------------------- #
# Page 3 — generated today
# --------------------------------------------------------------------------- #
def today(b):
    pg = page(b, "p3", "§ Generated today", "What is wired and exercised now")
    items = [
        ("SVG", "vector · primary", "painters/svg.py", BLUE, ic_svg),
        ("PNG", "raster · Chromium", "render_chromium.py", BLUE, ic_grid),
        ("Raster", "matplotlib proxy", "render_fg_doc.py", BLUE, ic_grid),
        ("PDF", "LaTeX/TikZ · lua+pdf", "render_latex.py", TEAL, ic_page),
        ("PDF", "cairosvg · SVG→PDF", "render_pdf.py", TEAL, ic_page),
        ("HTML/CSS", "semantic · limits", "backends/html.py", TEAL, ic_code),
        ("JSON Schema", "format contract", "build_schema.py", VIOLET, ic_braces),
        ("Docs site", "ref · gallery · SDK", "gen_docs.py", VIOLET, ic_book),
        ("Golden hashes", "per-page SHA-256", "render_golden.py", VIOLET, ic_rings),
        ("Math", "TeX→SVG · MathJax", "mathjax_tex_to_svg.mjs", AMBER, ic_sqrt),
        ("Import: PDF→FG", "fixed-layout extract", "pdf_to_frameforge_yml.py", LIVE, ic_import),
        ("Import: image→FG", "vision proposal", "propose_from_image", LIVE, ic_import),
    ]
    cells = grid([MX, 196, W - 2 * MX, 384], cols=4, rows=3, gap=20)
    for (name, kind, path, c, ic), box in zip(items, cells):
        card(pg, list(box), title=name, sub=kind, accent=c, fill=PANEL,
             title_size=14, icon=ic, foot=path, foot_color=c)
    pg.text([MX, 600, W - 2 * MX, 40],
            "The core both paths share: the ScenePainter port (domain/ports.py) + "
            "the Renderer. The TikzPainter migration will route LaTeX through the "
            "same port and retire the FigureTikz fork.",
            style=ts(12.5, MUTE, lh=1.45))
    return pg


# --------------------------------------------------------------------------- #
# Page 4 — what it could generate
# --------------------------------------------------------------------------- #
def could(b):
    pg = page(b, "p4", "§ The conceptual space", "Three families, and a hub")
    cols = row([MX, 196, W - 2 * MX, 400], 3, gap=26)
    fam = [
        ("A · Renditions", BLUE, ic_overlap, "the document drawn — any painter",
         ["EPS / PostScript, Typst, ConTeXt", "PDF/X (print), PDF/A (archival)",
          "JPEG · WebP · TIFF · sprite sheets", "Canvas / WebGL · React / Web Components",
          "CMYK separations · imposition · bleed", "thumbnails · multi-resolution exports"]),
        ("B · Hand-offs", TEAL, ic_handoff, "another engine owns final layout",
         ["LaTeX · Typst · Beamer", "DOCX · PPTX · ODT · RTF",
          "InDesign IDML/ICML · Scribus SLA", "EPUB 3 · MOBI / KF8",
          "Markdown · AsciiDoc · HTML", "reveal.js · Pandoc AST"]),
        ("C · Derivatives", VIOLET, ic_branch, "from the model, not the pixels",
         ["Tagged PDF/UA · ARIA tree", "Reading-order text · SSML · Braille",
          "TOC · list-of-figures · index", "Search index / embeddings · doc diff",
          "TS / Zod / Protobuf · DOT · glTF/STL", "metrics · bounding boxes · page count"]),
    ]
    for (title, c, ic, sub, rows_), box in zip(fam, cols):
        x, y, w, h = box
        pg.rect([x, y, w, h], radius=14, fill=PANEL, stroke=LINE, stroke_style={"stroke_width": 1.2})
        pg.rect([x, y, w, 4], radius=2, fill=c)
        pg.ellipse([x + w - 36, y + 36], 19, 19, fill=tint(c, 0.10), stroke=tint(c, 0.38), stroke_style={"stroke_width": 1.2})
        ic(pg, x + w - 36, y + 36, 10, c)
        pg.text([x + 22, y + 22, w - 70, 22], title, style=ts(17, INK, weight=800))
        pg.text([x + 22, y + 48, w - 70, 16], sub, style=ts(11, c, weight=600))
        bullets(pg, x + 22, y + 88, rows_, accent=c, gap=44, size=12, w=w - 38)

    bx, bw, by = callout(pg, [MX, 606, W - 2 * MX, 88],
                         label="THE HUB  ·  ANY → FRAMEFORGE → ANY", icon=ic_model)
    pg.text([bx, by, bw, 44],
            "Because the import side exists (PDF/image → FG), every importer × "
            "exporter pair is reachable — a Pandoc for visual documents. The "
            "largest latent output.", style=ts(12.5, MUTE, lh=1.45))
    return pg


# --------------------------------------------------------------------------- #
# Page 5 — boundaries + the one-line answer
# --------------------------------------------------------------------------- #
def boundaries(b):
    pg = page(b, "p5", "§ Boundaries", "What it deliberately will not generate")
    left = [MX, 200, 540, 326]
    pg.rect(left, radius=14, fill=PANEL, stroke=tint(RED, 0.42), stroke_style={"stroke_width": 1.4})
    pg.rect([left[0], left[1], left[2], 4], radius=2, fill=RED)
    pg.text([left[0] + 22, left[1] + 20, 480, 20], "Non-goals (by decision)",
            style=ts(16, RED, weight=800))
    for i, it in enumerate(["A WYSIWYG editor", "A browser-only rendering core",
                            "An interactive presentation runtime",
                            "A constraint-solver for every diagram class",
                            "A general scientific-charting replacement"]):
        yy = left[1] + 62 + i * 38
        pg.ellipse([left[0] + 32, yy + 8], 9, 9, fill="none", stroke=RED, stroke_style=_st(1.6))
        pg.line([left[0] + 26, yy + 2], [left[0] + 38, yy + 14], stroke=RED, stroke_style=_st(1.6))
        pg.text([left[0] + 52, yy + 1, 466, 22], it, style=ts(13, INK, lh=1.3))

    right = [MX + 568, 200, W - MX - (MX + 568), 326]
    pg.rect(right, radius=14, fill=PANEL2, stroke=LINE, stroke_style={"stroke_width": 1.2})
    pg.text([right[0] + 22, right[1] + 22, right[2] - 40, 18], "AND — IR-GATED",
            style=ts(11, FAINT, weight=800, spacing=2))
    # a tiny timeline-with-a-gap motif for "no temporal axis"
    ty = right[1] + 70
    pg.line([right[0] + 24, ty], [right[0] + right[2] - 24, ty], stroke=LINE, stroke_style=_st(2))
    for k in range(7):
        tx = right[0] + 40 + k * (right[2] - 80) / 6
        miss = k in (3, 4)
        pg.ellipse([tx, ty], 4, 4, fill="none" if miss else AMBER,
                   stroke=RED if miss else AMBER, stroke_style=_st(1.4))
    pg.text([right[0] + 22, right[1] + 96, right[2] - 44, 120],
            "…and anything needing semantics the IR does not model. Time / "
            "animation (Lottie, SMIL, video) is not expressible until the model "
            "grows a temporal axis — so it is out, for now, by construction rather "
            "than by choice.", style=ts(14, MUTE, lh=1.55))

    bx, bw, by = callout(pg, [MX, 566, W - 2 * MX, 138],
                         label="THE ONE-LINE ANSWER", icon=ic_spark)
    pg.text([bx, by, bw, 86],
            "FrameForge can generate any artifact that is a pure function of a "
            "laid-out, accessibility-annotated visual-document model — every "
            "rendition a painter can draw, every format another engine can typeset "
            "from, and every semantic derivative the structured tree affords.",
            style=ts(15, INK, weight=600, lh=1.5))
    return pg


PAGES = [cover, pipeline, today, could, boundaries]


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameForge — The Output Space", profile="deck", lang="en")
    for fn in PAGES:
        fn(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errs = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errs)} warnings={len(report.issues) - len(errs)}")
    for i in report.issues[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "_tmp", "output-space")
    os.makedirs(out, exist_ok=True)
    for idx, svg in enumerate(render_page_svgs(doc), 1):
        open(os.path.join(out, f"page-{idx}.svg"), "w", encoding="utf-8").write(svg)
    open(os.path.join(out, "output-space.fg.yaml"), "w", encoding="utf-8").write(
        serialize(doc, format="yaml"))
    print(f"Wrote {len(doc.pages)} SVG(s) + YAML to {out}")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
