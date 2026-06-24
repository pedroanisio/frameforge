#!/usr/bin/env python3
"""FrameGraph — Seed Pitch, authored *in* FrameGraph (the canonical seed).

This is the deck that defines FrameGraph as "the output layer for the agent era,"
authored through the FrameGraph SDK and rendered by the project's own renderer —
the system producing the artifact that pitches it. It is **not a copy** of the
source PDF: it is the canonical, on-brand rendering, built strictly on the brand
tokens and motifs in `docs/BRAND.md` (paper/ink, frame-blue/graph-cyan,
gate-green/drift-red for state only, the corner-bracket frame, the derivation-fan
mark, the ✓ ON-PROFILE state chip, IBM Plex with the honest DejaVu proxy).

Run from the repository root::

    uv run python examples/framegraph_seed_deck.py     # writes docs/seed/*.svg + the .fg.yaml
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
    DocumentBuilder,
    radial_gradient,
    render_page_svgs,
    rgba,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# The brand mark + wordmark are owned by the standalone logo document (single
# source of truth — examples/framegraph_logo.py), imported here rather than redefined.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # the examples/ dir
from framegraph_logo import fan, mark, wordmark  # noqa: E402,F401

# --------------------------------------------------------------------------- #
# Brand system — straight from docs/BRAND.md §4–§5 (the official tokens).
# --------------------------------------------------------------------------- #
W, H = 1280, 720                      # 16:9
M = 72                                # outer margin

INK   = "#15181E"   # graphite text/lines (never pure black)
PAPER = "#FBFAF6"   # warm technical paper — the default surface
CANVAS = "#FFFFFF"  # pure render surface (cards)
FRAME = "#1F4FD8"   # frame-blue — PRIMARY accent (the "Frame" half)
GRAPH = "#12B0C3"   # graph-cyan — secondary accent (the "Graph" half)
GREEN = "#1E9E5A"   # gate-green — semantic: pass / in-sync (state only)
RED   = "#D23B2B"   # drift-red  — semantic: fail / drift (state only)
GRID  = "#D4D8DE"   # hairlines, the drafting grid
MUTE  = "#6B7280"   # captions, secondary text

SANS  = ["IBM Plex Sans", "DejaVu Sans", "Helvetica", "Arial", "sans-serif"]
MONO  = ["IBM Plex Mono", "DejaVu Sans Mono", "Menlo", "monospace"]
SERIF = ["IBM Plex Serif", "DejaVu Serif", "Georgia", "serif"]

N_SLIDES = 16


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None,
       transform=None, family=None):
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


# --------------------------------------------------------------------------- #
# Reusable brand chrome + motifs.
# --------------------------------------------------------------------------- #
def graph_paper(page):
    """A faint drafting grid (the brand's hairline grid), coarse and quiet."""
    step = 96
    x = step
    while x < W:
        page.line([x, 0], [x, H], stroke=GRID, stroke_style={"stroke_width": 0.5})
        x += step
    y = step
    while y < H:
        page.line([0, y], [W, y], stroke=GRID, stroke_style={"stroke_width": 0.5})
        y += step


def corner_brackets(page, *, color=INK, inset=30, arm=22, sw=1.6):
    """Technical-drawing crop marks at the four corners — the *Frame* motif."""
    pts = [
        (inset, inset, 1, 1), (W - inset, inset, -1, 1),
        (inset, H - inset, 1, -1), (W - inset, H - inset, -1, -1),
    ]
    for x, y, dx, dy in pts:
        page.line([x, y], [x + dx * arm, y], stroke=color, stroke_style={"stroke_width": sw})
        page.line([x, y], [x, y + dy * arm], stroke=color, stroke_style={"stroke_width": sw})


def check(page, x, y, *, size=10, color=GREEN, sw=2.0):
    """A drawn check glyph (never the ✓ codepoint — font-independent)."""
    page.polyline([[x, y + size * 0.55], [x + size * 0.38, y + size],
                   [x + size, y]], stroke=color, fill="none",
                  stroke_style={"stroke_width": sw})


def on_profile(page):
    """Top-right state chip: FRAMEGRAPH ✓ ON-PROFILE (the gate, promoted to chrome)."""
    rx = W - M
    page.text([rx - 230, 30, 110, 12], "FRAMEGRAPH",
              style=ts(10.5, MUTE, family=MONO, weight=600, spacing=0.8))
    check(page, rx - 116, 31, size=9, color=GREEN)
    page.text([rx - 100, 30, 100, 12], "ON-PROFILE",
              style=ts(10.5, INK, family=MONO, weight=700, spacing=0.8))


def pagenum(page, n):
    page.text([W - M - 100, H - 40, 100, 12], f"p.{n:02d} / {N_SLIDES}",
              style=ts(10.5, MUTE, family=MONO, align="right", spacing=0.5))


def kicker(page, text, *, color=FRAME):
    page.text([M, 64, W - 2 * M, 14], text,
              style=ts(12, color, family=MONO, weight=700, spacing=2.4,
                       transform="uppercase"))


def cover_field(page):
    """The seed-pitch cover effect: a deep-navy ground with two soft radial glows
    (blue upper, violet lower-right), each an opaque centre fading to zero alpha."""
    page.rect([0, 0, W, H], fill="#0A0E1A")
    page.rect([0, 0, W, H], decorative=True, fill=radial_gradient(
        [(rgba("#3A63FF", 0.55), "0%"), (rgba("#3A63FF", 0.0), "58%")],
        at="58% 14%", shape="ellipse"))
    page.rect([0, 0, W, H], decorative=True, fill=radial_gradient(
        [(rgba("#7C3AED", 0.42), "0%"), (rgba("#7C3AED", 0.0), "55%")],
        at="84% 62%", shape="ellipse"))


def chrome(b, sid, n, kick, *, dark=False, grid=True, cover=False):
    """Build a slide page with the full brand chrome; return its PageBuilder.

    ``cover`` paints the dark hero treatment (deep navy + two radial glows,
    matching the seed-pitch cover) and switches the chrome to its light variant."""
    page = b.page(sid, canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    page.layer("bg")
    if cover:
        cover_field(page)
        dark = True
    else:
        page.rect([0, 0, W, H], fill=(INK if dark else PAPER))
        if grid and not dark:
            graph_paper(page)
    corner_brackets(page, color=(PAPER if dark else INK))
    page.layer("chrome")
    # On dark slides the chip + page number invert to paper-ink.
    if dark:
        rx = W - M
        page.text([rx - 230, 30, 110, 12], "FRAMEGRAPH",
                  style=ts(10.5, "#8A93A0", family=MONO, weight=600, spacing=0.8))
        check(page, rx - 116, 31, size=9, color=GREEN)
        page.text([rx - 100, 30, 100, 12], "ON-PROFILE",
                  style=ts(10.5, PAPER, family=MONO, weight=700, spacing=0.8))
        page.text([W - M - 100, H - 40, 100, 12], f"p.{n:02d} / {N_SLIDES}",
                  style=ts(10.5, "#8A93A0", family=MONO, align="right", spacing=0.5))
    else:
        on_profile(page)
        pagenum(page, n)
    # Directional progress — a pitch reads forward; the bar fills left→right to the
    # current slide, pointing the eye the way the story moves.
    pb_w = W - 2 * M - 124
    page.rect([M, H - 33, pb_w, 3], radius=1.5, decorative=True,
              fill=("#2A2E3A" if dark else GRID))
    page.rect([M, H - 33, pb_w * n / N_SLIDES, 3], radius=1.5, decorative=True,
              fill=(GRAPH if dark else FRAME))
    if kick:
        kicker(page, kick, color=(GRAPH if dark else FRAME))
    page.layer("body")
    page._lettering_depth += 1   # deck labels are lettering, not a tabular grid
    return page


def headline(page, y, text, *, size=50, color=INK, lh=1.04, w=None):
    page.text([M, y, (w or (W - 2 * M)), int(size * lh * 3) + 8], text,
              style=ts(size, color, weight=700, spacing=-0.6, lh=lh))


def lead(page, y, text, *, w=820, color=MUTE, size=19, lh=1.45):
    page.text([M, y, w, 200], text, style=ts(size, color, lh=lh))


def card(page, box, label, title, body, *, accent=FRAME, label_color=None,
         title_color=INK, fill=CANVAS, title_size=19):
    """A bordered card: mono kicker label · bold title · body. The brand card.

    ``title`` may be empty (label + body only) and ``title_size`` enlarges it for
    stat cards ($50B+ / yr)."""
    x, y, w, h = box
    page.rect([x, y, w, h], radius=10, fill=fill, stroke=GRID,
              stroke_style={"stroke_width": 1.3})
    page.rect([x, y, 4, h], radius=2, fill=accent)            # left accent tick
    pad = 22
    page.text([x + pad, y + 20, w - 2 * pad, 12], label,
              style=ts(11, label_color or accent, family=MONO, weight=700,
                       spacing=1.4, transform="uppercase"))
    if title:
        page.text([x + pad, y + 40, w - 2 * pad, title_size + 8], title,
                  style=ts(title_size, title_color, weight=700, spacing=-0.3))
        by = y + 44 + title_size
    else:
        by = y + 44
    if body:
        page.text([x + pad, by, w - 2 * pad, h - (by - y) - 16], body,
                  style=ts(13.5, MUTE, lh=1.45))


def banner(page, box, text, *, fill=FRAME, color=PAPER, size=18, weight=700):
    x, y, w, h = box
    page.rect([x, y, w, h], radius=12, fill=fill)
    page.text([x + 28, y + 16, w - 56, h - 28], text,
              style=ts(size, color, weight=weight, lh=1.35))


# The mark (`mark()`) and wordmark (`wordmark()`) live in their own reusable logo
# document, examples/framegraph_logo.py, so the logo can never diverge between the
# asset and the deck that stamps it. Both are imported once, near the top of this
# file.


# --------------------------------------------------------------------------- #
# Slides.
# --------------------------------------------------------------------------- #
def s01_cover(b):
    page = chrome(b, "s01-cover", 1, None, cover=True)
    page.text([M, 150, 700, 14], "SEED ROUND · 2026 · CONFIDENTIAL",
              style=ts(12, "#7FA0FF", family=MONO, weight=700, spacing=2.6))
    wordmark(page, M - 4, 196, 104, frame_color="#F4F6FA", graph_color="#3A63FF")
    headline(page, 344, "The output layer for the agent era.", size=44, w=470,
             color="#F4F6FA")
    page.text([M, 470, 600, 110],
              "AI can read the world. FrameGraph lets it produce the finished "
              "result — documents and images that are correct, on-brand, and "
              "ready to use.", style=ts(19, "#AEB6C2", lh=1.5))
    page.text([M, H - 84, 700, 14], "[ Founder name ]  ·  [ email ]  ·  [ website ]",
              style=ts(11.5, "#7A8395", family=MONO, spacing=0.6))
    return page


def s02_shift(b):
    page = chrome(b, "s02-shift", 2, "The shift")
    headline(page, 110, "AI learned to read.\nNow it has to produce.", size=46)
    lead(page, 246, "For two years the race was comprehension — models that read "
                    "screens, documents, and images. That half is largely solved. "
                    "The unclaimed half is output: turning what a machine intends "
                    "into a real, finished, trustworthy artifact a business can "
                    "actually send.", w=1040)
    cols = _row3(384, 152)
    card(page, cols[0], "01 — Solved", "Read",
         "Machines now understand screens, files, and images. This is the part "
         "everyone built.", accent=MUTE, label_color=MUTE)
    card(page, cols[1], "02 — Open", "Produce",
         "Machines making finished, correct visual artifacts on their own. Still "
         "largely missing.", accent=FRAME)
    card(page, cols[2], "03 — The prize", "The layer",
         "Whoever builds the infrastructure for that output owns a foundational "
         "position.", accent=GRAPH)
    page.text([M, 580, W - 2 * M, 24], "FrameGraph is building that layer.",
              style=ts(19, INK, weight=700))
    return page


def s03_problem(b):
    page = chrome(b, "s03-problem", 3, "The problem")
    headline(page, 108, "A machine-made document today\nis either fake-looking or\nquietly broken.",
             size=42)
    cols = _row2(318, 168)
    card(page, cols[0], "Image generators", "It produces a picture",
         "You can't edit it, the text comes out garbled, the numbers are "
         "invented, and you can't trust it for anything that matters.",
         accent=RED, label_color=MUTE)
    card(page, cols[1], "Code-it-yourself AI", "It looks right, then breaks",
         "Output that looks right but breaks: text overflows, things overlap, "
         "the layout collapses. Plausible — not shippable.", accent=RED,
         label_color=MUTE)
    page.text([M, 560, W - 2 * M, 60],
              "Generating something is easy. Turning it into a finished artifact "
              "you can trust enough to ship without a human checking it is the "
              "bottleneck — and today that's still a person's job.",
              style=ts(17, INK, lh=1.45, weight=600))
    return page


def s04_objection(b):
    page = chrome(b, "s04-objection", 4, "The obvious objection")
    headline(page, 110, "“But AI can already write\ncode and make a UI.”", size=42)
    page.text([M, 244, 1080, 60],
              "True. The difference isn't who draws it first — it's what you're "
              "left holding. A generated image is a dead-end you can only change "
              "by re-prompting. We hand you an open file you own.",
              style=ts(17.5, INK, lh=1.45, weight=600))
    cols = _row3(338, 192)
    card(page, cols[0], "Yours, not the tool's", "Open & editable",
         "A structured file a person or an agent can open, change, and extend — "
         "change one number or color by hand; don't regenerate the whole thing.",
         accent=FRAME)
    card(page, cols[1], "No lock-in", "Walk away with it",
         "For UI it's one framework-free HTML file — the moment a developer has "
         "it, they can use it however they like, with or without us.", accent=GRAPH)
    card(page, cols[2], "Ship unattended", "Checked, every time",
         "Because it's structured, we proofread every output automatically — a "
         "machine can produce it at scale without a human checking each one.",
         accent=GREEN)
    banner(page, [M, 568, W - 2 * M, 86],
           "The labs' output traps you; ours sets you free. The lock-in isn't the "
           "file — it's the flow that produces a perfect one on every change, at "
           "volume. A better model just feeds that flow.")
    return page


# ---- shared column helpers ------------------------------------------------ #
def _row3(y, h, *, gap=28):
    w = (W - 2 * M - 2 * gap) / 3
    return [[M + i * (w + gap), y, w, h] for i in range(3)]


def _row2(y, h, *, gap=28):
    w = (W - 2 * M - gap) / 2
    return [[M + i * (w + gap), y, w, h] for i in range(2)]


def _row4(y, h, *, gap=22):
    w = (W - 2 * M - 3 * gap) / 4
    return [[M + i * (w + gap), y, w, h] for i in range(4)]


def s05_solution(b):
    page = chrome(b, "s05-solution", 5, "The solution")
    headline(page, 112, "FrameGraph turns intent into a finished, checked file.",
             size=44, w=980)
    lead(page, 252, "You — or your AI — describe what you want, or point it at "
                    "your data. FrameGraph assembles the artifact, checks it the "
                    "way a meticulous proofreader would, and renders a real file: "
                    "a slide, a report, a web page, a chart, an image. At any "
                    "quality, from a quick sketch to print-ready.", w=1040, size=18)
    banner(page, [M, 396, W - 2 * M, 72],
           "Spell-check and a printing press — for everything AI makes that you "
           "can see.", size=20)
    return page


def s06_how(b):
    page = chrome(b, "s06-how", 6, "How it works")
    headline(page, 112, "Three steps. No design software. No guesswork.",
             size=44, w=980)
    cols = _row3(330, 168)
    card(page, cols[0], "Step 1", "Describe",
         "A person or an AI says what's needed — or simply hands over the data.",
         accent=FRAME)
    card(page, cols[1], "Step 2", "Build",
         "FrameGraph lays it out correctly — spacing, alignment, brand, "
         "structure — automatically.", accent=FRAME)
    card(page, cols[2], "Step 3", "Check & render",
         "It proofreads the result against the rules, then outputs a finished "
         "file. Anything wrong is caught before it ships.", accent=GREEN)
    page.text([M, 544, W - 2 * M, 16],
              "The same step that makes it work for one document makes it work "
              "for a million.", style=ts(13, MUTE, family=MONO))
    return page


def s07_moat(b):
    page = chrome(b, "s07-moat", 7, "Why it's different · the moat")
    headline(page, 108, "Anyone can make a picture. We make a result you can trust.",
             size=42, w=900)
    r1 = _row2(288, 116)
    r2 = _row2(418, 116)
    card(page, r1[0], "Checked", "",
         "Every output is automatically proofread for layout and brand. It won't "
         "ship broken.", accent=GREEN)
    card(page, r1[1], "Consistent", "",
         "Same input, same file, every time — which is what lets it plug into "
         "real business systems.", accent=FRAME)
    card(page, r2[0], "Built for machines", "",
         "Designed for AI to operate directly, at scale, without a human "
         "babysitting each one.", accent=GRAPH)
    card(page, r2[1], "Flexible", "",
         "One tool from rough sketch to polished, final asset. No switching "
         "between apps.", accent=FRAME)
    page.text([M, 566, W - 2 * M, 16],
              "Image generators: can't edit, can't trust.    ·    Design tools: "
              "slow, human-only, one at a time.", style=ts(13, MUTE, family=MONO))
    return page


def _thumb(page, box, kind, accent):
    """A small stylized artifact preview (browser chrome + abstract content)."""
    x, y, w, h = box
    page.rect([x, y, w, h], radius=8, fill=CANVAS, stroke=GRID,
              stroke_style={"stroke_width": 1.3})
    page.rect([x, y, w, 18], radius=8, fill="#EEF0F3")
    for i in range(3):
        page.circle([x + 14 + i * 11, y + 9], 2.4, fill=GRID)
    ix, iy = x + 16, y + 32
    iw = w - 32
    if kind == "dashboard":
        for i in range(4):
            page.rect([ix + i * (iw / 4), iy, iw / 4 - 8, 24], radius=4,
                      fill="#EAF0FB", stroke=accent, stroke_style={"stroke_width": 1})
        for r in range(3):
            page.rect([ix, iy + 38 + r * 15, iw, 8], radius=2, fill="#EDEFF2")
    elif kind == "doc":
        for r in range(6):
            page.rect([ix, iy + r * 15, iw * (0.95 if r % 3 else 0.6), 7],
                      radius=2, fill="#E9EBEF")
    elif kind == "codex":
        page.rect([x + 1, y + 18, w - 2, h - 19], fill="#161A22")
        page.circle([x + w / 2, y + h / 2 + 4], 15, fill="#F5A623")
        page.rect([ix, y + h - 24, iw, 7], radius=2, fill="#2A2F3A")
    else:  # landing
        page.rect([ix, iy, iw, 36], radius=6, fill="#EAF0FB")
        page.rect([ix, iy + 46, iw * 0.5, 9], radius=2, fill=accent)
        for r in range(3):
            page.rect([ix, iy + 64 + r * 13, iw, 6], radius=2, fill="#EDEFF2")


def s08_proof(b):
    page = chrome(b, "s08-proof", 8, "Proof — it already works")
    headline(page, 108, "Not a concept. A working system.", size=44, w=900)
    tw, gap = 266, 24
    kinds = [("landing", FRAME), ("doc", MUTE), ("dashboard", GRAPH), ("codex", INK)]
    for i, (kind, accent) in enumerate(kinds):
        _thumb(page, [M + i * (tw + gap), 268, tw, 150], kind, accent)
    caps = [("Range", "Real software screens, full marketing pages, dashboards, "
             "and a 30-page designed book — all from the same engine.", FRAME),
            ("Self-checking", "It proofreads its own output automatically and "
             "flags anything off-spec.", GRAPH),
            ("Dogfooded", "It even renders its own workspace, end to end.", GREEN)]
    cw = (W - 2 * M - 2 * 28) / 3
    for i, (lab, body, ac) in enumerate(caps):
        cx = M + i * (cw + 28)
        page.text([cx, 448, cw, 12], lab.upper(),
                  style=ts(11, ac, family=MONO, weight=700, spacing=1.4))
        page.text([cx, 468, cw, 80], body, style=ts(13, MUTE, lh=1.45))
    return page


def s09_reframe(b):
    page = chrome(b, "s09-reframe", 9, "Market · the reframe")
    headline(page, 104, "These stopped being separate markets the moment the "
             "maker became a machine.", size=38, w=760)
    lead(page, 318, "Design tools, slide software, document systems, dashboards, "
                    "image generators — each exists because a person operated it. "
                    "Take the person out and they're one thing: producing a visual "
                    "artifact. FrameGraph is the layer underneath all of them.",
         w=1090, size=16.5)
    chips = ["Design tools", "Slide software", "Document systems",
             "Dashboards / BI", "Image generators"]
    for i, c in enumerate(chips):
        cx = M + (i % 2) * 210
        ry = 446 + (i // 2) * 44
        page.rect([cx, ry, 196, 34], radius=8, fill=CANVAS, stroke=GRID,
                  stroke_style={"stroke_width": 1.2})
        page.text([cx, ry + 10, 196, 14], c,
                  style=ts(12.5, INK, family=MONO, align="center"))
    page.arrow([498, 500], [564, 500], color=FRAME, width=2.6, head=12)
    banner(page, [586, 452, W - M - 586, 96],
           "One layer: produce any visual artifact — correct, on-brand, and yours.",
           fill=INK, color=PAPER, size=18)
    page.text([M, 626, W - 2 * M, 16],
              "We don't boil that ocean. We start at automated branded documents "
              "+ a verified-output API — then expand outward.",
              style=ts(12.5, MUTE, family=MONO))
    return page


def s10_size(b):
    page = chrome(b, "s10-size", 10, "Market · the size")
    headline(page, 108, "A tens-of-billions shift, riding the fastest-growing "
             "category in software.", size=40, w=820)
    cols = _row3(300, 196)
    card(page, cols[0], "TAM · the category", "$50B+ / yr",
         "Producing every business visual artifact — design, presentation & "
         "customer-document software — inside a generative-AI market compounding "
         "30–40%+ a year.", accent=FRAME, title_color=FRAME, title_size=30)
    card(page, cols[1], "SAM · what we serve", "~$12B / yr",
         "The slice that's machine-produced at volume: automated documents, "
         "images, dashboards & UI for business, plus verified-output "
         "infrastructure for AI products.", accent=GRAPH, title_color=GRAPH,
         title_size=30)
    card(page, cols[2], "SOM · beachhead", "$50–150M",
         "Reachable now: branded documents & dynamic images at scale, plus a "
         "verified-output API for AI builders — on usage-based pricing.",
         accent=GREEN, title_color=GREEN, title_size=30)
    page.text([M, 524, W - 2 * M, 14],
              "Anchors (2025 analyst estimates): design ~$10–18B · presentation "
              "~$9B · customer-document / CCM ~$2.5B · generative AI ~$25–70B at "
              "+30–40%/yr.", style=ts(11, MUTE, family=MONO))
    page.text([M, 546, W - 2 * M, 14],
              "Third-party estimates (Mordor, Grand View, Precedence, Coherent et "
              "al., 2025–26), ranges for scale — not a forecast of company revenue.",
              style=ts(10.5, MUTE, family=MONO))
    return page


def s11_model(b):
    page = chrome(b, "s11-model", 11, "Business model")
    headline(page, 112, "We get paid every time something is produced.",
             size=44, w=900)
    cols = _row3(300, 178)
    card(page, cols[0], "Usage", "Pay per use",
         "A small fee each time a document or image is rendered. Grows "
         "automatically with a customer's usage.", accent=FRAME)
    card(page, cols[1], "Teams", "Team plans",
         "Subscriptions for companies that produce regularly and want seats and "
         "shared brand rules.", accent=FRAME)
    card(page, cols[2], "Enterprise", "Enterprise",
         "Brand & compliance controls plus private deployment for large "
         "customers — the high-value tier.", accent=GRAPH)
    page.text([M, 514, W - 2 * M, 16],
              "Software margins. Revenue that scales with our customers' success "
              "— not our headcount.", style=ts(13, MUTE, family=MONO))
    return page


def s12_ask(b):
    page = chrome(b, "s12-ask", 12, "The ask", dark=True, grid=False)
    headline(page, 132, "Raising $2.0M to turn a working system into a paid "
             "product.", size=46, color=PAPER, w=900)
    rows = [("Build the team",
             "A small, senior engineering and go-to-market team."),
            ("Ship the first paid product",
             "And land our first paying customers."),
            ("Earn the next round",
             "Hit the milestones that make a Series A the obvious next step.")]
    ry = 384
    for lab, body in rows:
        page.text([M, ry + 2, 290, 14], lab.upper(),
                  style=ts(11.5, GRAPH, family=MONO, weight=700, spacing=1.3))
        page.text([M + 310, ry - 4, 620, 44], body,
                  style=ts(17, PAPER, lh=1.4))
        ry += 72
    page.text([M, H - 84, 700, 14],
              "~18–24 months of runway · standard post-money SAFE",
              style=ts(11, "#8A93A0", family=MONO))
    return page


def s13_team(b):
    page = chrome(b, "s13-team", 13, "Team")
    headline(page, 112, "Why us.", size=48, w=600)
    cols = _row3(252, 152)
    card(page, cols[0], "Founder", "[ Your name ]",
         "One line: the most relevant thing you've built or shipped — and why it "
         "makes you the right person to build this.", accent=FRAME)
    card(page, cols[1], "Unfair advantage", "[ Why you, why now ]",
         "The insight, head start, or access you have that others don't — e.g., a "
         "working system already producing this range.", accent=GRAPH)
    card(page, cols[2], "First hires", "[ Who you'll add ]",
         "The 2–3 roles this round funds, and any advisors or early believers "
         "already on board.", accent=MUTE)
    page.text([M, 452, W - 2 * M, 16],
              "Note for you, not the investor: at seed, this is the slide they "
              "weigh most. Make it concrete and specific.",
              style=ts(12.5, MUTE, family=MONO))
    return page


def s14_outputs(b):
    """Pitch update — the output surface, told with the *canonical* derivation fan
    (`fan()` from the brand module, the same native composition our roadmap dogfood
    ships in its Instagram stories and A4 print PDF). One source → every audience,
    on every surface. Dark, to match the shipped stories."""
    page = chrome(b, "s14-outputs", 14, "The platform · 2.3 → 3.0",
                  dark=True, grid=False)
    headline(page, 100, "One source of truth. Every audience, every surface.",
             size=34, color=PAPER, w=W - 2 * M)
    page.text([M, 158, W - 2 * M, 20],
              "Split the data from the look — one source derives every audience's "
              "artifact, on every surface.", style=ts(15, "#9AA3B5", lh=1.4))

    # The canonical fan (the brand mark, applied): Q3 numbers → audiences/surfaces.
    fan(page, 300, 360, 812, "Q3 results",
        ["SEC filing", "investor deck", "IG story", "LinkedIn", "A4 print"],
        span=300, source=FRAME, edge=GRAPH, node_stroke=PAPER, node_fill=INK,
        label=PAPER, label_size=16, node_r=9, src_r=15)

    banner(page, [M, 556, W - 2 * M, 86],
           "We already dogfood this: our own v2 roadmap → an A4 print PDF and "
           "Instagram stories, one .fg source rendered by the SDK. No Figma, no "
           "InDesign — and the figures can't disagree, by construction.",
           fill=FRAME, color=PAPER, size=15)
    return page


def s15_vision(b):
    page = chrome(b, "s15-vision", 15, "The vision", dark=True, grid=False)
    headline(page, 168, "Soon, every page a business shows the world will be "
             "produced and checked by a machine.", size=44, color=PAPER, w=820)
    lead(page, 472, "FrameGraph is the layer that makes that output real, "
                    "correct, and yours.", w=820, color="#C2C9D2", size=19)
    page.text([M, 544, 760, 14], "Let's talk.    [ email ]    ·    [ calendar link ]",
              style=ts(12.5, GRAPH, family=MONO, spacing=0.6))
    return page


def s16_logo(b):
    """Endcap — the FrameGraph mark, shown as a system, not an illustration: one
    square glyph (the Frame + a derivation Graph) that holds up two-tone, in one
    colour, and reversed, all the way down to favicon size. That a single geometry
    survives every context is exactly what makes it a mark."""
    page = chrome(b, "s16-logo", 16, None, grid=False)

    # Primary mark — two-tone (Frame ink / Graph blue), large and centred.
    mark(page, W / 2, 292, 286)
    page.text([0, 448, W, 22], "The mark — a framed derivation",
              style=ts(15, MUTE, align="center", spacing=0.4))

    # Proof it is a mark, not a picture: one geometry, every context, every size.
    # A baseline-aligned scale ramp (two-tone → one-colour → small) ending in the
    # reversed-on-ink lockup.
    base = 604                                       # common baseline for the ramp
    ramp = [("two-tone", 80, {}),
            ("one-colour", 54, {"graph": INK}),
            ("small", 34, {"graph": INK}),
            ("favicon", 22, {"graph": INK})]
    gap, chip = 58, 80
    total = sum(s for _, s, _ in ramp) + chip + gap * len(ramp)
    x = (W - total) / 2
    for label, s, kw in ramp:
        mark(page, x + s / 2, base - s / 2, s, **kw)
        page.text([x + s / 2 - 60, base + 18, 120, 16], label,
                  style=ts(10, MUTE, align="center", transform="uppercase",
                           spacing=1.2))
        x += s + gap
    page.rect([x, base - chip, chip, chip], fill=INK)   # reversed-on-ink
    mark(page, x + chip / 2, base - chip / 2, 54,
         frame=PAPER, graph=PAPER, node_fill=INK)
    page.text([x + chip / 2 - 60, base + 18, 120, 16], "reversed",
              style=ts(10, MUTE, align="center", transform="uppercase",
                       spacing=1.2))
    return page


SLIDES = [s01_cover, s02_shift, s03_problem, s04_objection, s05_solution,
          s06_how, s07_moat, s08_proof, s09_reframe, s10_size, s11_model,
          s12_ask, s13_team, s14_outputs, s15_vision, s16_logo]


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph — Seed Pitch (canonical)",
                        profile="deck", lang="en")
    for fn in SLIDES:
        fn(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} slide(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out_dir = os.path.join(ROOT, "docs", "seed")
    os.makedirs(out_dir, exist_ok=True)
    for idx, svg in enumerate(render_page_svgs(doc), start=1):
        with open(os.path.join(out_dir, f"seed-{idx:02d}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    with open(os.path.join(ROOT, "docs", "framegraph-seed.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {len(doc.pages)} SVG(s) to {out_dir} + docs/framegraph-seed.fg.yaml")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
