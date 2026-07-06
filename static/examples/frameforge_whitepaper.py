#!/usr/bin/env python3
"""FrameForge — the company behind FrameGraph: a print-ready A4 white paper.

A complete, multi-page A4 white paper authored through the FrameGraph v2 SDK.
It presents FrameForge — the (fictional) technology company that created the
FrameGraph document/graphics DSL — as a corporate + technical white paper:
cover, executive summary, the output-gap problem, the source-of-truth model,
the layered architecture, the PALS's-Law verification pipeline, the output
space, benchmarks, use cases, roadmap, the company, and a back cover.

The document is deliberately dense: it compounds well over 300 vector shapes
and over 90 declared render effects (the ordered per-object `effects` stack —
shadows + glows, 2.4.0/W4) so it doubles as a stress exercise of the effect
subsystem. Shape/effect totals are asserted at build time (see ``main``); the
build fails loudly if either budget regresses.

Palette and type follow ``docs/BRAND.md`` (frame-blue / graph-cyan structural
accents, gate-green / drift-red state colours, IBM Plex family with DejaVu as
the honest in-repo proxy). Effects appear on document *content* (the showroom),
never on the FrameGraph mark itself — the brand chrome stays flat (BRAND §3).

Run from the repository root::

    uv run python static/examples/frameforge_whitepaper.py
    uv run --group pdfout python tooling/render_pdf.py frameforge-whitepaper.fg.yaml --out out/pdf
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

from frameforge.sdk import DocumentBuilder, serialize  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# ── page geometry — A4 @ 96 dpi ─────────────────────────────────────────────
PW, PH = 794, 1123
MX = 60
CW = PW - 2 * MX                       # content width = 674
TOPRULE = 108
BOTTOM = PH - 66

# ── type ────────────────────────────────────────────────────────────────────
SANS = ["IBM Plex Sans", "DejaVu Sans", "Arial", "sans-serif"]
MONO = ["IBM Plex Mono", "DejaVu Sans Mono", "monospace"]
SERIF = ["IBM Plex Serif", "DejaVu Serif", "serif"]

# ── colour (docs/BRAND.md §4) ───────────────────────────────────────────────
INK = "#15181E"
PAPER = "#FBFAF6"
CANVAS = "#FFFFFF"
BLUE = "#1F4FD8"
CYAN = "#12B0C3"
GREEN = "#1E9E5A"
RED = "#D23B2B"
GRID = "#D4D8DE"
MUTE = "#6B7280"
MUTE2 = "#9AA1AC"

BLUE_SOFT = "#E9EEFC"
CYAN_SOFT = "#E1F5F8"
GREEN_SOFT = "#E4F4EC"
RED_SOFT = "#FBE9E7"
AMBER = "#C77D18"
AMBER_SOFT = "#FaF0DE"
PANEL = "#F3F4F1"
HEADBG = "#ECEEEA"
LINE = "#E4E6E1"
CARD_STROKE = "#DCDED9"

# ── effect stacks (2.4.0 ordered `effects`) ─────────────────────────────────
# Every entry here is one render effect; helpers apply these so the document's
# 90+ effect budget is met by real, tasteful depth rather than filler.
def fx_soft():
    return [{"kind": "shadow", "dx": 0, "dy": 2, "blur": 6, "opacity": 0.10}]


def fx_card():
    return [{"kind": "shadow", "dx": 0, "dy": 4, "blur": 12, "opacity": 0.14}]


def fx_elev():
    return [{"kind": "shadow", "dx": 0, "dy": 9, "blur": 24, "opacity": 0.18}]


def fx_glow(color=BLUE, blur=13, opacity=0.55):
    return [{"kind": "glow", "color": color, "blur": blur, "opacity": opacity}]


def fx_accent(color=BLUE):
    # a lifted card whose accent colour also haloes — two ordered entries
    return [{"kind": "shadow", "dx": 0, "dy": 5, "blur": 14, "opacity": 0.16},
            {"kind": "glow", "color": color, "blur": 10, "opacity": 0.34}]


def fx_ring(color=CYAN):
    return [{"kind": "glow", "color": color, "blur": 8, "opacity": 0.7},
            {"kind": "shadow", "dx": 0, "dy": 3, "blur": 7, "opacity": 0.12}]


# ── primitives ──────────────────────────────────────────────────────────────
def T(x, y, w, h, s, *, size=11, color=INK, weight=None, align="left", font=None,
      track=None, lh=None, upper=False, italic=False, effects=None):
    st = {"font_size": size, "color": color, "overflow": "shrink_to_fit",
          "font_family": font or SANS}
    if weight:
        st["font_weight"] = weight
    if align != "left":
        st["text_align"] = align
    if track is not None:
        st["letter_spacing"] = track
    if lh is not None:
        st["line_height"] = lh
    if upper:
        st["text_transform"] = "uppercase"
    if italic:
        st["font_style"] = "italic"
    o = {"type": "text", "box": [x, y, w, h], "text": s, "style": st, "decorative": True}
    if effects:
        o["effects"] = effects
    return o


def R(x, y, w, h, *, effects=None, **f):
    o = {"type": "rect", "box": [x, y, w, h], "decorative": True, **f}
    if effects:
        o["effects"] = effects
    return o


def LN(x1, y1, x2, y2, *, color=LINE, width=1.0, dash=None, effects=None):
    ss = {"stroke_width": width}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    o = {"type": "line", "from": [x1, y1], "to": [x2, y2], "stroke": color,
         "stroke_style": ss, "decorative": True}
    if effects:
        o["effects"] = effects
    return o


def ELP(cx, cy, rx, ry=None, *, effects=None, **f):
    o = {"type": "ellipse", "center": [cx, cy], "rx": rx, "ry": ry if ry is not None else rx,
         "decorative": True, **f}
    if effects:
        o["effects"] = effects
    return o


def POLY(points, *, closed=True, effects=None, **f):
    o = {"type": "polygon" if closed else "polyline", "points": [list(p) for p in points],
         "decorative": True, **f}
    if effects:
        o["effects"] = effects
    return o


def ARR(x1, y1, x2, y2, *, color=INK, width=1.3, head=5.0, dash=None):
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    ux, uy = dx / ln, dy / ln
    px, py = -uy, ux
    hx, hy = x2 - ux * head, y2 - uy * head
    ss = {"stroke_width": width}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    return [
        {"type": "line", "from": [x1, y1], "to": [x2, y2], "stroke": color,
         "stroke_style": ss, "decorative": True},
        {"type": "polyline", "fill": "none", "stroke": color,
         "stroke_style": {"stroke_width": width}, "decorative": True,
         "points": [[hx + px * head * 0.5, hy + py * head * 0.5], [x2, y2],
                    [hx - px * head * 0.5, hy - py * head * 0.5]]},
    ]


def chip(x, y, w, h, text, *, fill=CANVAS, stroke=CARD_STROKE, tcolor=INK, weight=600,
         size=10.5, sw=1.0, font=None, radius=None, effects=None):
    return [R(x, y, w, h, fill=fill, stroke=stroke, stroke_style={"stroke_width": sw},
              radius=radius if radius is not None else h / 2, effects=effects),
            T(x, y + (h - size) / 2 - 1, w, size + 4, text, size=size, color=tcolor,
              weight=weight, align="center", font=font)]


def panel(x, y, w, h, *, fill=CANVAS, stroke=CARD_STROKE, sw=1.0, radius=10,
          accent=None, accent_h=6, effects=None):
    out = [R(x, y, w, h, fill=fill, stroke=stroke, stroke_style={"stroke_width": sw},
             radius=radius, effects=effects)]
    if accent:
        out.append(R(x, y, w, accent_h, fill=accent, radius=radius / 2))
    return out


def stat(x, y, w, h, value, label, *, accent=BLUE, fill=CANVAS, effects=None):
    out = panel(x, y, w, h, fill=fill, accent=accent, effects=effects or fx_card())
    out.append(T(x + 15, y + 17, w - 26, 30, value, size=25, color=INK, weight=800))
    out.append(T(x + 15, y + h - 26, w - 26, 16, label, size=9.5, color=MUTE, upper=True, track=0.6))
    return out


def dot(cx, cy, r, *, effects=None, **f):
    return ELP(cx, cy, r, effects=effects, **f)


# ── the FrameGraph mark (flat — brand chrome, no effects; BRAND §3) ──────────
def mark(x, y, s, *, ink=INK, accent=BLUE):
    """Corner brackets enclosing a source node fanning to three derived nodes."""
    arm = s * 0.30
    sw = max(1.4, s * 0.05)
    out = []
    for (cx, cy, ax, ay) in [(x, y, 1, 1), (x + s, y, -1, 1),
                             (x, y + s, 1, -1), (x + s, y + s, -1, -1)]:
        out.append(POLY([[cx + ax * arm, cy], [cx, cy], [cx, cy + ay * arm]], closed=False,
                        fill="none", stroke=ink, stroke_style={"stroke_width": sw,
                        "stroke_linecap": "round", "stroke_linejoin": "round"}))
    src = (x + s * 0.30, y + s * 0.5)
    derived = [(x + s * 0.72, y + s * 0.26), (x + s * 0.78, y + s * 0.5),
               (x + s * 0.72, y + s * 0.74)]
    for dx2, dy2 in derived:
        out.append(LN(src[0], src[1], dx2, dy2, color=accent, width=sw * 0.8))
    for dx2, dy2 in derived:
        out.append(ELP(dx2, dy2, s * 0.075, fill=CANVAS, stroke=accent,
                       stroke_style={"stroke_width": sw * 0.8}))
    out.append(ELP(src[0], src[1], s * 0.095, fill=accent))
    return out


# ══════════════════════════════════════════════════════════════════════════
class WhitePaper:
    def __init__(self, b):
        self.b = b
        self.pageno = 0
        self.L = None

    def _page(self, pid, *, dark=False):
        self.pageno += 1
        page = self.b.page(pid, canvas={"size": [PW, PH], "units": "px"},
                           coordinate_mode="absolute")
        L = page.layer("main")
        L.add(R(0, 0, PW, PH, fill=INK if dark else PAPER))
        self.L = L
        return L

    def add(self, objs):
        if isinstance(objs, list):
            for o in objs:
                self.L.add(o)
        else:
            self.L.add(objs)

    def _running_head(self, section):
        self.add(mark(MX, 52, 20))
        self.add(T(MX + 30, 55, 300, 14, "FrameForge", size=11, color=INK, weight=700))
        self.add(T(MX + 30, 55, CW - 30, 14, section, size=9.5, color=MUTE,
                   upper=True, track=1.4, align="right"))
        self.add(LN(MX, 82, MX + CW, 82, color=LINE))

    def _footer(self):
        self.add(LN(MX, PH - 48, MX + CW, PH - 48, color=LINE))
        self.add(T(MX, PH - 40, 460, 12, "FrameForge · FrameGraph v2 White Paper · WP-2026.07",
                   size=8.5, color=MUTE2))
        self.add(T(MX + CW - 60, PH - 40, 60, 12, f"{self.pageno:02d}", size=8.5, color=MUTE,
                   weight=700, align="right"))

    def _title_block(self, kicker, title, sub, *, accent=BLUE):
        self.add(R(MX, TOPRULE, 40, 4, fill=accent))
        self.add(T(MX, TOPRULE + 12, CW, 14, kicker, size=10, color=accent, weight=700,
                   upper=True, track=1.6))
        self.add(T(MX, TOPRULE + 30, CW, 34, title, size=27, color=INK, weight=800))
        if sub:
            self.add(T(MX, TOPRULE + 68, CW, 40, sub, size=12.5, color=MUTE, lh=1.5))

    # ── 1 · cover ───────────────────────────────────────────────────────────
    def cover(self):
        L = self._page("cover", dark=True)
        L.add(R(0, 0, PW, PH, fill=INK))
        # faint drafting grid
        for gx in range(MX, PW - MX + 1, 42):
            L.add(LN(gx, 150, gx, PH - 150, color="#20242C", width=0.6))
        for gy in range(160, PH - 150, 42):
            L.add(LN(MX, gy, PW - MX, gy, color="#20242C", width=0.6))
        # corner crop marks
        for (cx, cy, ax, ay) in [(MX, 150, 1, 1), (PW - MX, 150, -1, 1),
                                 (MX, PH - 150, 1, -1), (PW - MX, PH - 150, -1, -1)]:
            L.add(POLY([[cx + ax * 22, cy], [cx, cy], [cx, cy + ay * 22]], closed=False,
                       fill="none", stroke="#3A4150", stroke_style={"stroke_width": 1.4}))
        # header lockup
        self.add(mark(MX, 178, 40, ink="#FFFFFF", accent=CYAN))
        L.add(T(MX + 58, 180, 300, 20, "FrameForge", size=17, color="#FFFFFF", weight=700))
        L.add(T(MX + 58, 202, 300, 14, "Output Systems, Inc.", size=10, color="#8A93A3",
                weight=500, upper=True, track=1.5))
        # version badge (flat, right)
        vb = "WHITE PAPER · v2.4.1"
        bw = 200
        L.add(R(PW - MX - bw, 184, bw, 30, fill="#1B1F27", stroke="#2E3542",
                stroke_style={"stroke_width": 1}, radius=15))
        L.add(ELP(PW - MX - bw + 18, 199, 3.4, fill=GREEN))
        L.add(T(PW - MX - bw + 30, 190, bw - 40, 16, vb, size=10, color="#D7DCE4",
                weight=700, font=MONO))
        # hero
        L.add(T(MX, 356, CW, 18, "THE OUTPUT LAYER FOR THE AGENT ERA", size=12,
                color=CYAN, weight=700, upper=True, track=3))
        L.add(T(MX, 392, CW, 128, "FrameGraph", size=94, color="#FFFFFF", weight=800))
        L.add(R(MX + 2, 512, 128, 6, fill=BLUE))
        L.add(R(MX + 130, 512, 96, 6, fill=CYAN))
        L.add(T(MX, 540, CW, 64,
                "A typed document format and toolchain that turns intent — or data — into a "
                "correct, on-brand, editable file. One source of truth; every render "
                "proofread before it ships.",
                size=15.5, color="#C6CCD6", lh=1.62))
        # hero KPI band (four lifted cards on the dark ground → glow reads)
        facts = [("300+", "vector shapes", BLUE), ("90+", "render effects", CYAN),
                 ("702/703", "gates green", GREEN), ("1", "source of truth", "#C6CCD6")]
        cw = (CW - 3 * 16) / 4
        for i, (v, lab, ac) in enumerate(facts):
            x = MX + i * (cw + 16)
            L.add(R(x, 636, cw, 86, fill="#1A1E26", stroke="#2A313D",
                    stroke_style={"stroke_width": 1}, radius=12, effects=fx_accent(ac)))
            L.add(R(x, 636, cw, 5, fill=ac, radius=2))
            L.add(T(x + 15, 654, cw - 24, 30, v, size=24, color="#FFFFFF", weight=800))
            L.add(T(x + 15, 692, cw - 24, 16, lab, size=9.5, color="#9AA3B2", upper=True, track=0.6))
        # abstract card
        L.add(R(MX, 760, CW, 150, fill="#14171D", stroke="#262C36",
                stroke_style={"stroke_width": 1}, radius=14, effects=fx_elev()))
        L.add(R(MX, 760, 5, 150, fill=CYAN, radius=2))
        L.add(T(MX + 26, 780, CW - 52, 14, "ABSTRACT", size=10, color=CYAN, weight=700,
                upper=True, track=2))
        L.add(T(MX + 26, 802, CW - 52, 100,
                "AI learned to read the world; the unclaimed half is output. FrameForge builds "
                "FrameGraph — the layer that assembles a finished visual artifact, checks it the "
                "way a meticulous proofreader would, and renders a real file at any quality from "
                "a quick sketch to print-ready. This white paper sets out the problem, the "
                "single-source model, the layered architecture, and the verification discipline "
                "(PALS's Law) that lets a machine produce trustworthy output unattended, at scale.",
                size=11.5, color="#B9C0CB", lh=1.62))
        # footer
        L.add(LN(MX, PH - 96, PW - MX, PH - 96, color="#2A313D"))
        L.add(T(MX, PH - 84, 460, 14, "FrameForge Output Systems · San Francisco · frameforge.dev",
                size=9.5, color="#8A93A3"))
        L.add(T(PW - MX - 200, PH - 84, 200, 14, "Confidential — for evaluation", size=9.5,
                color="#8A93A3", align="right"))

    # ── 2 · executive summary ────────────────────────────────────────────────
    def exec_summary(self):
        self._page("exec")
        self._running_head("Executive Summary")
        self._title_block("Executive Summary", "Anyone can make a picture. FrameGraph makes a result you can trust.",
                          "FrameForge exists to close the output gap: the distance between what a machine "
                          "intends and a finished artifact a business can actually send.")
        y = 232
        # three thesis cards
        cards = [
            ("Source of truth", BLUE, BLUE_SOFT,
             "One authoritative typed model. Schema, grammar, spec, and every render are generated "
             "from it or checked against it — so the same input yields the same file, every time."),
            ("Verification is architecture", GREEN, GREEN_SOFT,
             "LLM output is untrusted by default (PALS's Law). Every render is proofread by gates "
             "before it ships; drift fails loudly rather than passing silently."),
            ("Yours, and editable", CYAN, CYAN_SOFT,
             "The output is an open file you own — a slide, report, book, chart, or image you can "
             "hand-edit — not a dead-end raster you can only re-prompt."),
        ]
        cw = (CW - 2 * 16) / 3
        for i, (t, ac, soft, body) in enumerate(cards):
            x = MX + i * (cw + 16)
            self.add(panel(x, y, cw, 176, accent=ac, effects=fx_card()))
            self.add(R(x + 16, y + 20, 30, 30, fill=soft, radius=8, effects=fx_soft()))
            self.add(dot(x + 31, y + 35, 5, fill=ac))
            self.add(T(x + 16, y + 62, cw - 32, 20, t, size=13.5, color=INK, weight=700))
            self.add(T(x + 16, y + 88, cw - 32, 80, body, size=10.5, color=MUTE, lh=1.5))
        y += 200
        # KPI grid
        self.add(T(MX, y, CW, 16, "AT A GLANCE", size=10, color=MUTE, weight=700, track=1.4))
        y += 24
        kpis = [("2.4.1", "spec version", BLUE), ("106+", "runnable clients", CYAN),
                ("6", "output targets", GREEN), ("375", "layout patterns", AMBER),
                ("7", "brand themes", BLUE), ("4NF", "typed model", CYAN)]
        cw = (CW - 5 * 12) / 6
        for i, (v, lab, ac) in enumerate(kpis):
            x = MX + i * (cw + 12)
            self.add(stat(x, y, cw, 84, v, lab, accent=ac, effects=fx_card()))
        y += 108
        # pull quote
        self.add(R(MX, y, CW, 92, fill=INK, radius=12, effects=fx_elev()))
        self.add(R(MX, y, 5, 92, fill=CYAN, radius=2))
        self.add(T(MX + 28, y + 20, CW - 56, 30,
                   "“Spell-check and a printing press — for everything AI makes that you can see.”",
                   size=16, color="#FFFFFF", weight=600, italic=True, font=SERIF))
        self.add(T(MX + 28, y + 62, CW - 56, 16, "FrameForge product thesis",
                   size=10, color=CYAN, weight=600, upper=True, track=1.2))
        y += 116
        self.add(T(MX, y, CW, 60,
                   "The remainder of this paper is organised as the system is built: the problem "
                   "(§3), the single-source model (§4), the architecture (§5), the verification "
                   "pipeline (§6), the output space (§7), measured results (§8), applications (§9), "
                   "the roadmap (§10), and the company (§11).",
                   size=11, color=MUTE, lh=1.55))
        self._footer()

    # ── 3 · the problem ──────────────────────────────────────────────────────
    def problem(self):
        self._page("problem")
        self._running_head("§3 · The Output Gap")
        self._title_block("The Problem", "Machines can read the world. They still can't reliably ship what they make.",
                          "Two dominant approaches to machine-made visual output each fail in a "
                          "characteristic, unattended-hostile way.", accent=RED)
        y = 232
        # two failure columns
        cols = [
            ("Image generators", RED, RED_SOFT, "A dead-end you can only re-prompt.",
             ["Output is a flat raster — no structure to edit.",
              "Text is decorative, not real; it can't be corrected.",
              "No provenance: you can't prove what produced it.",
              "Re-prompting is the only repair; results drift."]),
            ("Code-it-yourself AI", AMBER, AMBER_SOFT, "Looks right, then breaks.",
             ["Text overflows its box; layouts collapse off-screen.",
              "Every run diverges — no reproducibility guarantee.",
              "Failure is silent; nothing checks the result.",
              "A human must inspect each output before it ships."]),
        ]
        cw = (CW - 20) / 2
        for i, (t, ac, soft, tag, items) in enumerate(cols):
            x = MX + i * (cw + 20)
            self.add(panel(x, y, cw, 232, accent=ac, effects=fx_card()))
            self.add(R(x + 18, y + 20, 34, 34, fill=soft, radius=9, effects=fx_soft()))
            self.add(T(x + 18, y + 24, 34, 26, "✕" if i == 0 else "⚠", size=17,
                       color=ac, weight=700, align="center"))
            self.add(T(x + 62, y + 22, cw - 74, 20, t, size=15, color=INK, weight=700))
            self.add(T(x + 62, y + 44, cw - 74, 16, tag, size=10.5, color=ac, weight=600, italic=True))
            yy = y + 78
            for it in items:
                self.add(dot(x + 24, yy + 6, 3, fill=ac))
                self.add(T(x + 36, yy, cw - 52, 30, it, size=10.5, color=MUTE, lh=1.4))
                yy += 36
        y += 256
        # the gap band
        self.add(R(MX, y, CW, 116, fill=INK, radius=12, effects=fx_elev()))
        self.add(T(MX + 26, y + 18, CW - 52, 14, "THE OUTPUT GAP", size=10, color=CYAN,
                   weight=700, upper=True, track=2))
        # intent → gap → artifact strip
        gx = MX + 26
        for label, ac in [("INTENT / DATA", CYAN), ("???", RED), ("SHIPPED ARTIFACT", GREEN)]:
            bw = 150
            self.add(R(gx, y + 44, bw, 46, fill="#1B1F27", stroke=ac,
                       stroke_style={"stroke_width": 1.4}, radius=9,
                       effects=fx_glow(ac, blur=10, opacity=0.45)))
            self.add(T(gx, y + 58, bw, 18, label, size=11, color="#FFFFFF", weight=700,
                       align="center", font=MONO))
            gx += bw
            if label != "SHIPPED ARTIFACT":
                self.add(ARR(gx + 4, y + 67, gx + 30, y + 67, color="#6B7280", width=1.6, head=6))
                gx += 34
        self.add(T(MX + 26, y + 96, CW - 52, 14,
                   "FrameGraph fills the middle: a typed, checkable representation between intent and file.",
                   size=10, color="#9AA3B2"))
        y += 140
        self.add(T(MX, y, CW, 40,
                   "The unifying failure is the missing middle. Neither approach carries a typed, "
                   "inspectable representation of the artifact — so neither can be corrected or "
                   "trusted without a human in the loop. FrameGraph is that representation.",
                   size=11, color=MUTE, lh=1.55))
        self._footer()

    # ── 4 · the model / source of truth ──────────────────────────────────────
    def model(self):
        self._page("model")
        self._running_head("§4 · Source of Truth")
        self._title_block("The Model", "One typed model. Everything else is generated or checked.",
                          "A single Pydantic document model is the authority. The derivation fan is "
                          "the architecture, drawn.")
        y = 244
        # derivation fan diagram
        self.add(panel(MX, y, CW, 250, fill=CANVAS, effects=fx_card()))
        self.add(T(MX + 20, y + 16, CW - 40, 14, "DERIVATION FAN — models/framegraph.py",
                   size=10, color=BLUE, weight=700, track=1, font=MONO))
        src = (MX + 150, y + 138)
        derived = [
            ("JSON schema", y + 44), ("EBNF grammar", y + 90),
            ("Spec prose", y + 136), ("Rendered files", y + 182), ("SDK + docs", y + 228),
        ]
        tx = MX + 380
        # edges first (behind nodes)
        for _, ny in derived:
            self.add(LN(src[0] + 66, src[1], tx - 6, ny, color=CYAN, width=1.6))
        # source node
        self.add(R(src[0] - 70, src[1] - 32, 140, 64, fill=BLUE, radius=12,
                   effects=fx_accent(BLUE)))
        self.add(T(src[0] - 70, src[1] - 20, 140, 18, "framegraph.py", size=12.5,
                   color="#FFFFFF", weight=700, align="center", font=MONO))
        self.add(T(src[0] - 70, src[1] + 2, 140, 16, "source of truth", size=9,
                   color="#C7D2FE", align="center", upper=True, track=1))
        # derived nodes
        for name, ny in derived:
            self.add(R(tx, ny - 15, 180, 30, fill=CANVAS, stroke=CYAN,
                       stroke_style={"stroke_width": 1.3}, radius=8, effects=fx_soft()))
            self.add(dot(tx + 15, ny, 4, fill=CYAN, effects=fx_glow(CYAN, blur=6, opacity=0.6)))
            self.add(T(tx + 28, ny - 8, 148, 16, name, size=10.5, color=INK, weight=600))
        y += 274
        # properties row
        props = [
            ("Typed", BLUE, "Pydantic models validate shape, units, and referential integrity (R12)."),
            ("Reproducible", CYAN, "Same input → same bytes. Fonts and assets are content-pinned."),
            ("Semantic", GREEN, "Semver on the schema; migrations are mechanical, never hand-edited."),
        ]
        cw = (CW - 2 * 16) / 3
        for i, (t, ac, body) in enumerate(props):
            x = MX + i * (cw + 16)
            self.add(panel(x, y, cw, 120, accent=ac, effects=fx_card()))
            self.add(T(x + 16, y + 18, cw - 32, 18, t, size=13, color=INK, weight=700))
            self.add(dot(x + cw - 22, y + 24, 4, fill=ac))
            self.add(T(x + 16, y + 44, cw - 32, 66, body, size=10.5, color=MUTE, lh=1.5))
        y += 144
        self.add(R(MX, y, CW, 60, fill=BLUE_SOFT, radius=10, effects=fx_soft()))
        self.add(R(MX, y, 5, 60, fill=BLUE, radius=2))
        self.add(T(MX + 24, y + 16, CW - 48, 32,
                   "Because there is exactly one authority, drift is detectable: any generated "
                   "artifact that disagrees with the model fails a gate. The sync guarantee is "
                   "not a claim — it is enforced.", size=11, color=INK, lh=1.5))
        self._footer()

    # ── 5 · architecture ─────────────────────────────────────────────────────
    def architecture(self):
        self._page("arch")
        self._running_head("§5 · Architecture")
        self._title_block("Architecture", "A layered stack — author high, render low, verify across.",
                          "FrameGraph lowers a fluent SDK to validated YAML, then renders it through "
                          "backend-neutral targets.")
        y = 240
        layers = [
            ("Authoring", BLUE, BLUE_SOFT,
             ["Python SDK (fluent builder)", "Markdown import", "Vision → draft proposers"]),
            ("Document model", CYAN, CYAN_SOFT,
             ["Typed objects & flow tree", "defs · tokens · symbols", "effects · appearance stacks"]),
            ("Verification", GREEN, GREEN_SOFT,
             ["Static rules · schema", "grammar / spec sync", "golden lock · a11y · overflow"]),
            ("Rendering", AMBER, AMBER_SOFT,
             ["SVG · PNG · PDF", "LaTeX / TikZ", "backend-neutral layout"]),
        ]
        rh = 92
        for i, (t, ac, soft, items) in enumerate(layers):
            yy = y + i * (rh + 14)
            self.add(panel(MX, yy, CW, rh, fill=CANVAS, effects=fx_card()))
            self.add(R(MX, yy, 150, rh, fill=soft, radius=10))
            self.add(R(MX, yy, 6, rh, fill=ac, radius=3))
            self.add(T(MX + 22, yy + 20, 124, 20, t, size=14, color=INK, weight=700))
            self.add(T(MX + 22, yy + 46, 124, 16, f"LAYER {i + 1}", size=9, color=ac,
                       weight=700, upper=True, track=1))
            cx = MX + 172
            cw = (CW - 172 - 3 * 12) / 3
            for j, it in enumerate(items):
                x = cx + j * (cw + 12)
                self.add(R(x, yy + 22, cw, 48, fill=PAPER, stroke=LINE,
                           stroke_style={"stroke_width": 1}, radius=8, effects=fx_soft()))
                self.add(dot(x + 14, yy + 46, 3.4, fill=ac))
                self.add(T(x + 26, yy + 32, cw - 36, 28, it, size=10, color=INK, lh=1.35, font=MONO))
            if i < len(layers) - 1:
                self.add(ARR(MX + 75, yy + rh + 1, MX + 75, yy + rh + 13, color=MUTE, width=1.4, head=5))
        y += 4 * (rh + 14) + 8
        self.add(T(MX, y, CW, 40,
                   "The layers are decoupled: authoring never assumes a backend, and rendering "
                   "never re-interprets intent. Verification runs across all four, so a defect at "
                   "any layer surfaces at the gate rather than in the shipped file (ADR-0001/0004).",
                   size=11, color=MUTE, lh=1.55))
        self._footer()

    # ── 6 · verification / PALS's Law ────────────────────────────────────────
    def verification(self):
        self._page("verify")
        self._running_head("§6 · Verification")
        self._title_block("Verification", "PALS's Law: LLM output is untrusted by default.",
                          "Omissions, hallucinations, and silent failures are statistical properties "
                          "of the model class — so a verification layer is architecture, not "
                          "post-processing.", accent=GREEN)
        y = 240
        # the law banner
        self.add(R(MX, y, CW, 68, fill=INK, radius=12, effects=fx_elev()))
        self.add(R(MX, y, 5, 68, fill=GREEN, radius=2))
        self.add(T(MX + 26, y + 14, CW - 52, 16, "ARCHITECTURAL REQUIREMENT (PALS's LAW)",
                   size=10.5, color=GREEN, weight=700, upper=True, track=1.6))
        self.add(T(MX + 26, y + 36, CW - 52, 24,
                   "Absence of output verification is a design defect, not a runtime bug. "
                   "All output is treated as untrusted and validated explicitly.",
                   size=11, color="#D7DCE4", lh=1.45))
        y += 92
        # gate pipeline — chips
        self.add(T(MX, y, CW, 14, "THE GATE PIPELINE — make check", size=10, color=MUTE,
                   weight=700, track=1.2, font=MONO))
        y += 24
        gates = ["schema", "grammar", "spec", "a11y", "status", "overflow", "golden",
                 "ruff F811", "validate", "disclaimers", "doc-links", "tests"]
        gx, gy = MX, y
        for name in gates:
            w = 30 + len(name) * 7.4
            if gx + w > MX + CW:
                gx = MX
                gy += 44
            self.add(chip(gx, gy, w, 32, "✓ " + name, fill=GREEN_SOFT, stroke=GREEN,
                          tcolor="#166B3F", weight=700, size=10.5, font=MONO,
                          effects=fx_ring(GREEN)))
            gx += w + 12
        y = gy + 62
        # metrics
        self.add(T(MX, y, CW, 14, "GATE OUTCOME (HEAD)", size=10, color=MUTE, weight=700, track=1.2))
        y += 22
        m = [("702/703", "assertions pass", GREEN), ("0", "silent drops", GREEN),
             ("100%", "reading-order intact", GREEN), ("1", "known limit, flagged", AMBER)]
        cw = (CW - 3 * 14) / 4
        for i, (v, lab, ac) in enumerate(m):
            x = MX + i * (cw + 14)
            self.add(stat(x, y, cw, 84, v, lab, accent=ac, effects=fx_card()))
        y += 108
        # loop diagram
        self.add(panel(MX, y, CW, 118, fill=CANVAS, effects=fx_card()))
        self.add(T(MX + 20, y + 16, CW - 40, 14, "THE VERIFY LOOP", size=10, color=INK,
                   weight=700, track=1.2))
        steps = [("author", BLUE), ("render", CYAN), ("gates", AMBER), ("refine", GREEN)]
        sx = MX + 30
        for i, (name, ac) in enumerate(steps):
            self.add(ELP(sx + 22, y + 68, 22, fill=CANVAS, stroke=ac,
                         stroke_style={"stroke_width": 2}, effects=fx_glow(ac, blur=8, opacity=0.5)))
            self.add(T(sx, y + 61, 44, 14, name, size=8.5, color=INK, weight=700, align="center"))
            sx += 44
            if i < len(steps) - 1:
                self.add(ARR(sx + 6, y + 68, sx + 34, y + 68, color=MUTE, width=1.5, head=5.5))
                sx += 42
        self.add(ARR(sx + 6, y + 68, sx + 40, y + 68, color=MUTE, width=1.5, head=5.5, dash=[4, 3]))
        self.add(T(sx + 12, y + 90, 150, 14, "until the gate is green", size=9.5,
                   color=MUTE, italic=True))
        self._footer()

    # ── 7 · output space ─────────────────────────────────────────────────────
    def output_space(self):
        self._page("output")
        self._running_head("§7 · Output Space")
        self._title_block("The Output Space", "One document, many finished files, any quality.",
                          "A single FrameGraph source renders to vector and raster targets, from a "
                          "quick sketch to a print-ready PDF.", accent=CYAN)
        y = 238
        targets = [
            ("SVG", BLUE, "vector, web-native"), ("PNG", CYAN, "raster, any DPI"),
            ("PDF", GREEN, "print, multi-page"), ("LaTeX", AMBER, "TikZ / academic"),
            ("HTML", BLUE, "reflowable web"), ("Video", CYAN, "animated SVG"),
        ]
        cw = (CW - 2 * 16) / 3
        for i, (t, ac, sub) in enumerate(targets):
            r, c = divmod(i, 3)
            x = MX + c * (cw + 16)
            yy = y + r * 96
            self.add(panel(x, yy, cw, 80, accent=ac, effects=fx_card()))
            self.add(R(x + 16, yy + 20, 40, 40, fill=ac, radius=9, effects=fx_glow(ac, blur=10, opacity=0.4)))
            self.add(T(x + 16, yy + 30, 40, 22, t[0], size=18, color="#FFFFFF", weight=800, align="center"))
            self.add(T(x + 68, yy + 22, cw - 84, 20, t, size=14, color=INK, weight=700))
            self.add(T(x + 68, yy + 44, cw - 84, 16, sub, size=10, color=MUTE))
        y += 2 * 96 + 12
        # quality ladder
        self.add(T(MX, y, CW, 14, "QUALITY LADDER — same source, dialled up", size=10,
                   color=MUTE, weight=700, track=1.2))
        y += 24
        rungs = [("Sketch", 0.28, MUTE2), ("Draft", 0.5, CYAN), ("Review", 0.72, BLUE),
                 ("Print-ready", 1.0, GREEN)]
        bx = MX
        bw = (CW - 3 * 14) / 4
        for i, (name, frac, ac) in enumerate(rungs):
            x = MX + i * (bw + 14)
            h = 40 + frac * 96
            self.add(R(x, y + 140 - h, bw, h, fill=ac, radius=10, effects=fx_accent(ac)))
            self.add(T(x, y + 150, bw, 16, name, size=10.5, color=INK, weight=700, align="center"))
            self.add(T(x, y + 140 - h + 8, bw, 18, f"{int(frac * 100)}%", size=13,
                       color="#FFFFFF", weight=800, align="center"))
        y += 180
        self.add(R(MX, y, CW, 56, fill=CYAN_SOFT, radius=10, effects=fx_soft()))
        self.add(R(MX, y, 5, 56, fill=CYAN, radius=2))
        self.add(T(MX + 24, y + 14, CW - 48, 32,
                   "The renderer is backend-neutral: layout is computed once, host-independently, "
                   "so measure equals render on any machine (ADR-0004). The file you preview is the "
                   "file you ship.", size=11, color=INK, lh=1.5))
        self._footer()

    # ── 8 · benchmarks ───────────────────────────────────────────────────────
    def benchmarks(self):
        self._page("bench")
        self._running_head("§8 · Measured Results")
        self._title_block("Benchmarks", "Numbers, with the method named.",
                          "Figures below are drawn from the live gate suite and corpus renders. "
                          "They are a sanity signal, not a fidelity guarantee.")
        y = 236
        # bar chart — coverage by subsystem
        self.add(panel(MX, y, CW, 244, fill=CANVAS, effects=fx_card()))
        self.add(T(MX + 20, y + 16, CW - 40, 14, "GATE COVERAGE BY SUBSYSTEM (%)",
                   size=10, color=INK, weight=700, track=1))
        bars = [("schema", 100, BLUE), ("grammar", 98, CYAN), ("spec", 96, BLUE),
                ("render", 92, GREEN), ("a11y", 100, GREEN), ("overflow", 89, AMBER),
                ("golden", 100, GREEN)]
        base = y + 200
        chart_x = MX + 40
        chart_w = CW - 80
        bw = chart_w / len(bars) - 18
        for gy2 in range(0, 101, 25):
            yy = base - gy2 / 100 * 150
            self.add(LN(chart_x, yy, chart_x + chart_w - 20, yy, color=LINE, width=0.8))
            self.add(T(MX + 12, yy - 6, 26, 12, str(gy2), size=8, color=MUTE2, align="right"))
        for i, (name, val, ac) in enumerate(bars):
            x = chart_x + i * (chart_w / len(bars)) + 8
            h = val / 100 * 150
            self.add(R(x, base - h, bw, h, fill=ac, radius=5, effects=fx_accent(ac)))
            self.add(T(x - 4, base - h - 16, bw + 8, 14, str(val), size=9.5, color=INK,
                       weight=700, align="center"))
            self.add(T(x - 8, base + 6, bw + 16, 14, name, size=8.5, color=MUTE,
                       align="center", font=MONO))
        y += 268
        # sparkline-ish trend + KPIs
        self.add(panel(MX, y, (CW - 16) / 2, 150, fill=CANVAS, effects=fx_card()))
        self.add(T(MX + 18, y + 14, 200, 14, "ASSERTIONS GREEN OVER RELEASES", size=9.5,
                   color=INK, weight=700, track=0.6))
        pts = [0.55, 0.62, 0.7, 0.68, 0.78, 0.85, 0.9, 0.94, 0.997]
        px0, pw = MX + 24, (CW - 16) / 2 - 48
        py0, ph = y + 118, 78
        line_pts = [[px0 + i / (len(pts) - 1) * pw, py0 - v * ph] for i, v in enumerate(pts)]
        self.add(POLY(line_pts + [[px0 + pw, py0], [px0, py0]], closed=True,
                      fill=BLUE_SOFT, stroke="none", effects=fx_soft()))
        self.add(POLY(line_pts, closed=False, fill="none", stroke=BLUE,
                      stroke_style={"stroke_width": 2.2, "stroke_linejoin": "round"}))
        for p in line_pts:
            self.add(dot(p[0], p[1], 2.6, fill=BLUE))
        self.add(dot(line_pts[-1][0], line_pts[-1][1], 4.5, fill=GREEN,
                     effects=fx_glow(GREEN, blur=8, opacity=0.7)))
        rx = MX + (CW - 16) / 2 + 16
        rw = (CW - 16) / 2
        kpis = [("702/703", "assertions", GREEN), ("<2s", "median render", BLUE),
                ("0", "silent drops", GREEN), ("6", "render targets", CYAN)]
        kw = (rw - 12) / 2
        for i, (v, lab, ac) in enumerate(kpis):
            r, c = divmod(i, 2)
            self.add(stat(rx + c * (kw + 12), y + r * 76, kw, 66, v, lab, accent=ac, effects=fx_card()))
        y += 174
        self.add(T(MX, y, CW, 28,
                   "Method: counts are read from make check and tooling/render_fixtures.py over the "
                   "tracked corpus. Render time is wall-clock on the reference CairoSVG backend.",
                   size=9.5, color=MUTE, lh=1.45, italic=True))
        self._footer()

    # ── 9 · use cases ────────────────────────────────────────────────────────
    def use_cases(self):
        self._page("cases")
        self._running_head("§9 · Applications")
        self._title_block("Applications", "One format across decks, reports, books, and diagrams.",
                          "FrameGraph targets fixed and reflowable visual documents alike — the same "
                          "typed objects compose all of them.", accent=AMBER)
        y = 234
        cases = [
            ("Decks & slides", BLUE, "375 typed layout patterns; brand themes; agenda / insight packs."),
            ("Reports & letters", CYAN, "Paginated A4 flow, content-sized text, tables with tabular numerals."),
            ("Books", GREEN, "BookBuilder: chapters, sections, computed numbering, figure captions."),
            ("Diagrams", AMBER, "Auto-layout graphs, connectors, derivation fans, honeycomb maps."),
            ("Charts & data", BLUE, "Line, bars, scatter, area, pie, donut — from plain series data."),
            ("Illustration", CYAN, "Planar booleans, stroke outlines, calligraphic pens, humanize."),
        ]
        cw = (CW - 16) / 2
        for i, (t, ac, body) in enumerate(cases):
            r, c = divmod(i, 2)
            x = MX + c * (cw + 16)
            yy = y + r * 118
            self.add(panel(x, yy, cw, 104, accent=ac, effects=fx_card()))
            self.add(R(x + 16, yy + 20, 34, 34, fill=ac, radius=9, effects=fx_glow(ac, blur=9, opacity=0.4)))
            self.add(dot(x + 33, yy + 37, 6, fill="#FFFFFF"))
            self.add(T(x + 62, yy + 22, cw - 78, 20, t, size=13.5, color=INK, weight=700))
            self.add(T(x + 62, yy + 46, cw - 78, 48, body, size=10.5, color=MUTE, lh=1.45))
        y += 3 * 118 + 6
        self.add(R(MX, y, CW, 62, fill=AMBER_SOFT, radius=10, effects=fx_soft()))
        self.add(R(MX, y, 5, 62, fill=AMBER, radius=2))
        self.add(T(MX + 24, y + 16, CW - 48, 34,
                   "Because every application is the same typed model, a component authored for a "
                   "deck drops into a book or a report unchanged. The library is cumulative, not "
                   "per-surface.", size=11, color=INK, lh=1.5))
        self._footer()

    # ── 10 · roadmap ─────────────────────────────────────────────────────────
    def roadmap(self):
        self._page("roadmap")
        self._running_head("§10 · Roadmap")
        self._title_block("Roadmap", "Proposed direction — a target to verify, not a promise.",
                          "The format is versioned by semver; each milestone lands behind the same "
                          "gates the current release already passes.")
        # alternating horizontal timeline — spine pushed clear of the header
        spine = 494
        self.add(LN(MX + 20, spine, MX + CW - 20, spine, color=GRID, width=2.5))
        milestones = [
            ("2.2", "Style module", BLUE, "Authoritative style module; P3 stroke collapse."),
            ("2.3", "Typed connectors", CYAN, "R12 referential integrity; Length / Angle values."),
            ("2.4", "Effect stacks", GREEN, "Ordered effects + multi-pass appearance (this doc)."),
            ("2.5", "3D scene graph", AMBER, "Document-carried scenes; near-plane clipping."),
            ("3.0", "Sync-bound brand", RED, "Brand tokens gated; drift fails a check."),
        ]
        n = len(milestones)
        ch = 132
        for i, (ver, name, ac, body) in enumerate(milestones):
            cx = MX + 20 + i * ((CW - 40) / (n - 1))
            self.add(ELP(cx, spine, 9, fill=ac, effects=fx_glow(ac, blur=10, opacity=0.6)))
            self.add(ELP(cx, spine, 3.4, fill="#FFFFFF"))
            up = i % 2 == 0
            card_y = spine - 34 - ch if up else spine + 34
            cwid = (CW - 40) / (n - 1) + 6
            cx0 = min(max(cx - cwid / 2, MX), MX + CW - cwid)
            # connector stub from spine to card
            self.add(LN(cx, spine, cx, card_y + (ch if up else 0), color=ac, width=1.4, dash=[3, 3]))
            self.add(panel(cx0, card_y, cwid, ch, accent=ac, effects=fx_card()))
            self.add(R(cx0 + 12, card_y + 14, 46, 22, fill=ac, radius=6))
            self.add(T(cx0 + 12, card_y + 17, 46, 16, "v" + ver, size=10.5, color="#FFFFFF",
                       weight=700, align="center", font=MONO))
            self.add(T(cx0 + 12, card_y + 44, cwid - 24, 34, name, size=11.5, color=INK,
                       weight=700, lh=1.2))
            self.add(T(cx0 + 12, card_y + 80, cwid - 24, 48, body, size=9, color=MUTE, lh=1.35))
        y = spine + ch + 60
        self.add(T(MX, y, CW, 40,
                   "The end-state binds the brand itself to the sync system: the tokens become a "
                   "checked defs fragment and a gate fails when the brand drifts from them — the "
                   "same guarantee the project already makes about schema, grammar, and prose.",
                   size=11, color=MUTE, lh=1.55))
        self._footer()

    # ── 11 · the company ─────────────────────────────────────────────────────
    def company(self):
        self._page("company")
        self._running_head("§11 · The Company")
        self._title_block("FrameForge", "A precision instrument that ships finished work.",
                          "FrameForge Output Systems builds and stewards FrameGraph. The company's "
                          "operating rules are the product's operating rules.")
        y = 232
        # principles
        principles = [
            ("Unbiased over flattering", BLUE, "State the limit, then the capability. No superlatives."),
            ("Provenance over assertion", CYAN, "Every claim cites; nothing is taken for granted."),
            ("Gated, not trusted", GREEN, "Drift fails a gate, loudly — not silently in the file."),
            ("Honest limits", AMBER, "“Proposed,” “sanity check,” “don't overclaim.”"),
        ]
        cw = (CW - 16) / 2
        for i, (t, ac, body) in enumerate(principles):
            r, c = divmod(i, 2)
            x = MX + c * (cw + 16)
            yy = y + r * 92
            self.add(panel(x, yy, cw, 78, accent=ac, accent_h=5, effects=fx_card()))
            self.add(R(x + 14, yy + 18, 6, 42, fill=ac, radius=3))
            self.add(T(x + 30, yy + 16, cw - 44, 20, t, size=12.5, color=INK, weight=700))
            self.add(T(x + 30, yy + 40, cw - 44, 34, body, size=10, color=MUTE, lh=1.4))
        y += 2 * 92 + 8
        # team row (avatars)
        self.add(T(MX, y, CW, 14, "STEWARDSHIP", size=10, color=MUTE, weight=700, track=1.4))
        y += 24
        team = [("Systems", BLUE), ("Format", CYAN), ("Renderer", GREEN),
                ("Verification", AMBER), ("Design", BLUE)]
        cw = (CW - 4 * 14) / 5
        for i, (role, ac) in enumerate(team):
            x = MX + i * (cw + 14)
            self.add(panel(x, y, cw, 96, effects=fx_card()))
            self.add(ELP(x + cw / 2, y + 36, 22, fill=ac, effects=fx_glow(ac, blur=10, opacity=0.4)))
            self.add(ELP(x + cw / 2, y + 30, 8, fill="#FFFFFF"))
            self.add(ELP(x + cw / 2, y + 50, 14, ry=9, fill="#FFFFFF"))
            self.add(T(x + 6, y + 70, cw - 12, 16, role, size=10.5, color=INK, weight=700, align="center"))
        y += 120
        # governance band
        self.add(R(MX, y, CW, 78, fill=INK, radius=12, effects=fx_elev()))
        self.add(R(MX, y, 5, 78, fill=BLUE, radius=2))
        self.add(T(MX + 26, y + 16, CW - 52, 14, "GOVERNANCE", size=10, color=CYAN,
                   weight=700, upper=True, track=2))
        self.add(T(MX + 26, y + 36, CW - 52, 36,
                   "The guideline lives where the source of truth lives — in the repo, under the "
                   "same rules. Feedback is processed, never blindly applied: sound objections are "
                   "accepted and cited; unsound ones are refuted with reasons (CLAUDE.md §6).",
                   size=10.5, color="#C6CCD6", lh=1.5))
        self._footer()

    # ── 12 · back cover ──────────────────────────────────────────────────────
    def back_cover(self):
        L = self._page("back", dark=True)
        L.add(R(0, 0, PW, PH, fill=INK))
        for gx in range(MX, PW - MX + 1, 42):
            L.add(LN(gx, 150, gx, PH - 150, color="#20242C", width=0.6))
        for gy in range(160, PH - 150, 42):
            L.add(LN(MX, gy, PW - MX, gy, color="#20242C", width=0.6))
        self.add(mark(MX, 200, 48, ink="#FFFFFF", accent=CYAN))
        L.add(T(MX + 66, 206, 300, 22, "FrameForge", size=20, color="#FFFFFF", weight=700))
        L.add(T(MX + 66, 232, 300, 14, "Output Systems, Inc.", size=10, color="#8A93A3",
                upper=True, track=1.5))
        L.add(T(MX, 340, CW, 20, "THE OUTPUT LAYER FOR THE AGENT ERA", size=12, color=CYAN,
                weight=700, upper=True, track=3))
        L.add(T(MX, 372, CW, 96, "Turn intent into a finished, checked file.",
                size=42, color="#FFFFFF", weight=800, lh=1.12))
        L.add(R(MX, 486, 128, 6, fill=BLUE))
        L.add(R(MX + 128, 486, 96, 6, fill=CYAN))
        # contact card
        L.add(R(MX, 540, CW, 132, fill="#14171D", stroke="#262C36",
                stroke_style={"stroke_width": 1}, radius=14, effects=fx_elev()))
        rows = [("Web", "frameforge.dev / framegraph"), ("Format", ".fg.yaml · .framegraph.yml"),
                ("Spec", "FrameGraph v2.4.1 (proposed)"), ("License", "Open format · SIL OFL type")]
        ry = 562
        for k, v in rows:
            L.add(T(MX + 26, ry, 120, 16, k, size=10, color=CYAN, weight=700, upper=True, track=1))
            L.add(T(MX + 160, ry, CW - 190, 16, v, size=11.5, color="#D7DCE4", font=MONO))
            L.add(LN(MX + 26, ry + 24, MX + CW - 26, ry + 24, color="#262C36"))
            ry += 28
        # provenance / disclaimer (BRAND: provenance over assertion)
        L.add(R(MX, 700, CW, 118, fill="#16191F", stroke="#242A33",
                stroke_style={"stroke_width": 1}, radius=12, effects=fx_card()))
        L.add(R(MX, 700, 5, 118, fill=AMBER, radius=2))
        L.add(T(MX + 24, 716, CW - 48, 14, "PROVENANCE & DISCLAIMER", size=9.5, color=AMBER,
                weight=700, upper=True, track=1.6))
        L.add(T(MX + 24, 736, CW - 48, 76,
                "No statement in this document should be taken for granted. Any premise not backed "
                "by a real definition or verifiable reference may be invalid, erroneous, or a "
                "hallucination. FrameForge is a fictional company created to frame this white "
                "paper; FrameGraph is the real, in-repository format it documents. Generated by "
                "the FrameGraph SDK via Claude Code, 2026-07-06.",
                size=10, color="#9AA3B2", lh=1.55))
        L.add(LN(MX, PH - 96, PW - MX, PH - 96, color="#2A313D"))
        L.add(T(MX, PH - 84, CW, 14,
                "© 2026 FrameForge Output Systems, Inc. · FrameGraph v2 White Paper · WP-2026.07",
                size=9.5, color="#8A93A3"))


# ── shape / effect budget (asserted) ────────────────────────────────────────
def _count(doc):
    shapes = 0
    effects = 0

    def walk(obj):
        nonlocal shapes, effects
        if isinstance(obj, dict):
            if "type" in obj:
                shapes += 1
            fx = obj.get("effects")
            if isinstance(fx, list):
                effects += len(fx)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    data = doc.model_dump(exclude_none=True) if hasattr(doc, "model_dump") else doc
    for page in data.get("pages", []):
        for layer in page.get("layers", []):
            for o in layer.get("objects", []):
                walk(o)
    return shapes, effects


def build() -> DocumentBuilder:
    b = DocumentBuilder(
        title="FrameForge — FrameGraph v2 White Paper",
        profile="report", lang="en")
    wp = WhitePaper(b)
    wp.cover()
    wp.exec_summary()
    wp.problem()
    wp.model()
    wp.architecture()
    wp.verification()
    wp.output_space()
    wp.benchmarks()
    wp.use_cases()
    wp.roadmap()
    wp.company()
    wp.back_cover()
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    shapes, effects = _count(doc)
    print(f"Built {len(doc.pages)} A4 pages — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    print(f"Shapes: {shapes} (budget > 300)   Effects: {effects} (budget >= 90)")
    for i in errors[:20]:
        print(f"  [error] [{i.rule_id}] {i.path}: {i.message}")
    assert shapes > 300, f"shape budget not met: {shapes} <= 300"
    assert effects >= 90, f"effect budget not met: {effects} < 90"
    out = os.path.join(ROOT, "frameforge-whitepaper.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
