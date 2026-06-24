#!/usr/bin/env python3
"""INOVA PARTNERS — A4 white paper (PT-BR), built with the SDK.

A 12-page print white paper for Inova Partners — "A primeira Workforce Transition
Company do Brasil" — on the AI-driven transition of the workforce. Copy, brand
palette and the bridge/pillar logomark are taken from the live brand at
https://inovapartners.com.br (CSS + /brand/inova_partners_logo_primary_v2.svg).

Brand palette (verbatim from the site's stylesheet and logo):
  primary  #F44B18 (orange-vermilion)   dark shade  #C73D14
  pale tint #FFF1EA / light #FFB89A      ink/near-black #232323
  greys #636363 / #999999  hairline #E2E2E2  soft #FAFAFA  white #FFFFFF
  secondary accent #2400C8 (indigo, used sparingly)

Content note (CLAUDE.md rule 2): every research statistic is reproduced with the
same source attribution shown on the brand site (Gartner 2025, MIT 2025, McKinsey
2025/2026, FGV IBRE/PNAD-IBGE 3T2025). No figure here is invented; numbers are
presented as cited evidence, not as independently verified claims. The document is
authored in Portuguese (PT-BR) because it targets a Brazilian audience — the
exception permitted by CLAUDE.md rule 3(c).

Authoring discipline (mirrors the project's deck conventions): each page declares
its own canvas; the only layer-top-level text per content page is the page title;
all other content lives inside groups; structural rects are decorative; text
carries overflow=shrink_to_fit.

AI-generated artifact — authored by Claude Opus 4.8 via Claude Code.

Run from the repository root::

    uv run python examples/inova_partners_whitepaper.py
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
    Chart,
    DocumentBuilder,
    Frame,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --- geometry --------------------------------------------------------------- #
W, H = 794, 1123                 # A4 portrait @ 96 dpi
CANVAS = {"size": [W, H], "units": "px"}
MX = 64
CW = W - 2 * MX                  # 666
TOP = 172

# --- palette (verbatim from inovapartners.com.br) --------------------------- #
ORANGE, ORANGE2, ORANGET = "#F44B18", "#C73D14", "#FFF1EA"
ORANGE_L = "#FFB89A"
DARK, INK, CHAR, SLATE = "#1A1A1A", "#232323", "#2A2A2A", "#3A3A3A"
MUTE, MUTE2, LINE = "#636363", "#999999", "#E2E2E2"
PAPER, SOFT, CARD = "#FFFFFF", "#FAFAFA", "#FFFFFF"
NEUT_T = "#F2F2F2"
INDIGO = "#2400C8"
POS, NEG = "#1B8B4F", "#C73D14"
ON_DARK = "#FFFFFF"
ON_DARK_MUTE = "#B8B8B8"

SANS = ["IBM Plex Sans", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
SERIF = ["IBM Plex Serif", "Georgia", "DejaVu Serif", "serif"]
FOOTER = "INOVA PARTNERS   ·   Workforce Transition White Paper   ·   Edição 2026"


# --- primitives ------------------------------------------------------------- #
def T(x, y, w, h, s, *, size=14, color=INK, weight=None, align="left", font=None,
      id=None, track=None, lh=None, italic=False, upper=False):
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
    if italic:
        st["font_style"] = "italic"
    if upper:
        st["text_transform"] = "uppercase"
    o = {"type": "text", "box": [x, y, w, h], "text": s, "style": st}
    if id:
        o["id"] = id
    return o


def R(x, y, w, h, **f):
    return {"type": "rect", "box": [x, y, w, h], **f}


def LN(x1, y1, x2, y2, *, color=LINE, width=1.0, dash=None):
    ss = {"stroke_width": width}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    return {"type": "line", "from": [x1, y1], "to": [x2, y2], "stroke": color, "stroke_style": ss}


def EL(cx, cy, r, **f):
    return {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, **f}


def dot(x, y, r, color):
    return EL(x, y, r, fill=color)


def PL(points, *, closed=True, fill=None, stroke=None, width=None):
    o = {"type": "polyline", "closed": closed, "points": [list(p) for p in points]}
    if fill is not None:
        o["fill"] = fill
    if stroke is not None:
        o["stroke"] = stroke
        o["stroke_style"] = {"stroke_width": width or 1.5}
    return o


def _deco_all(node):
    if isinstance(node, dict):
        if "box" in node:
            node["decorative"] = True
        for v in node.values():
            _deco_all(v)
    elif isinstance(node, list):
        for x in node:
            _deco_all(x)
    return node


def GRP(pb, children):
    _deco_all(children)
    return pb.group(children)


def GRPC(pb, children, clip):
    _deco_all(children)
    return pb.group(children, clip=list(clip), decorative=True)


def ADD(pb, obj):
    _deco_all(obj)
    return pb.add(obj)


# --- diagonal stripe motif -------------------------------------------------- #
def diag_field(L, box, colors, *, sw=22, gap=42):
    x, y, w, h = box
    stripes = []
    n = int((w + h) / gap) + 2
    for i in range(n):
        off = -h + i * gap
        stripes.append(PL([[x + off, y + h], [x + off + sw, y + h],
                           [x + off + sw + h, y], [x + off + h, y]], fill=colors[i % len(colors)]))
    GRPC(L, stripes, box)


# --- brand mark (the 5-pillar "bridge" symbol + wordmark) ------------------- #
# Pillar geometry lifted from inova_partners_logo_primary_v2.svg (symbol centred
# on x=450, y=129 in its own 632x520 viewBox; bar width 9, cap radius 14).
_PILLARS = [(-122, 118, 186), (-60, 82, 198), (0, 52, 206), (60, 82, 198), (122, 118, 186)]


def logo_symbol(cx, cy, s, color=ORANGE):
    out = []
    for xo, t, btm in _PILLARS:
        x = cx + xo * s
        t2, b2 = cy + (t - 129) * s, cy + (btm - 129) * s
        out.append({"type": "rect", "box": [x - 4.5 * s, t2, 9 * s, b2 - t2],
                    "fill": color, "radius": 4.5 * s})
        out.append(EL(x, t2, 14 * s, fill=color))
        out.append(EL(x, b2, 14 * s, fill=color))
    return out


def logo(x, y, *, on_dark=False, scale=1.0):
    """Horizontal lockup: bridge symbol + 'Inova' / 'PARTNERS' wordmark."""
    s = 0.16 * scale
    sym_h = 182 * s
    cx, cy = x + 136 * s, y + sym_h / 2
    main = ON_DARK if on_dark else INK
    out = logo_symbol(cx, cy, s)
    tx = x + 272 * s + 12 * scale
    out.append(T(tx, y + sym_h * 0.06, 280 * scale, sym_h * 0.62, "Inova",
                 size=21 * scale, color=main, weight=800))
    out.append(T(tx + 2, y + sym_h * 0.60, 280 * scale, sym_h * 0.42, "PARTNERS",
                 size=10.5 * scale, color=ORANGE, weight=700, track=4))
    return out


def logo_stacked(cx, top, scale, *, on_dark=True):
    """Centred lockup for cover/back: symbol above the wordmark."""
    s = 0.30 * scale
    sym_h = 182 * s
    out = logo_symbol(cx, top + sym_h / 2, s)
    main = ON_DARK if on_dark else INK
    out.append(T(cx - 200, top + sym_h + 8, 400, 40 * scale, "Inova", size=30 * scale,
                 color=main, weight=800, align="center"))
    out.append(T(cx - 200, top + sym_h + 8 + 34 * scale, 400, 24 * scale, "PARTNERS",
                 size=14 * scale, color=ORANGE, weight=700, align="center", track=8))
    return out


# --- stroke pictograms ------------------------------------------------------ #
def icon(name, cx, cy, h, color, width=2.2):
    ss = {"stroke_width": width}

    def L_(x1, y1, x2, y2):
        return {"type": "line", "from": [cx + x1 * h, cy + y1 * h],
                "to": [cx + x2 * h, cy + y2 * h], "stroke": color, "stroke_style": ss}

    def C_(x, y, r, fill="none"):
        return {"type": "ellipse", "center": [cx + x * h, cy + y * h], "rx": r * h, "ry": r * h,
                "fill": fill, "stroke": color, "stroke_style": ss}

    def P_(pts, closed=True, fill="none"):
        return {"type": "polyline", "closed": closed, "fill": fill, "stroke": color,
                "stroke_style": ss, "points": [[cx + a * h, cy + b * h] for a, b in pts]}

    def Rr(x, y, w, ht, rad=0):
        out = {"type": "rect", "box": [cx + x * h, cy + y * h, w * h, ht * h],
               "fill": "none", "stroke": color, "stroke_style": ss}
        if rad:
            out["radius"] = rad * h
        return out

    if name == "compass":
        return [C_(0, 0, 0.92), P_([(0, -0.5), (0.28, 0.12), (0, 0.5), (-0.28, 0.12)], fill=color)]
    if name == "search":
        return [C_(-0.18, -0.18, 0.55), L_(0.22, 0.22, 0.7, 0.7)]
    if name == "target":
        return [C_(0, 0, 0.9), C_(0, 0, 0.5),
                {"type": "ellipse", "center": [cx, cy], "rx": 0.14 * h, "ry": 0.14 * h, "fill": color}]
    if name == "gear":
        out = [C_(0, 0, 0.55), C_(0, 0, 0.22)]
        for k in range(8):
            a = math.radians(k * 45)
            out.append(L_(0.62 * math.cos(a), 0.62 * math.sin(a),
                          0.92 * math.cos(a), 0.92 * math.sin(a)))
        return out
    if name == "bars":
        return [L_(-0.6, 0.7, 0.7, 0.7), Rr(-0.55, 0.0, 0.28, 0.7), Rr(-0.12, -0.35, 0.28, 1.05),
                Rr(0.32, -0.15, 0.28, 0.85)]
    if name == "users":
        return [C_(-0.32, -0.3, 0.32), P_([(-0.72, 0.7), (-0.62, 0.1), (-0.02, 0.1), (0.08, 0.7)]),
                C_(0.42, -0.18, 0.26), P_([(0.12, 0.7), (0.2, 0.22), (0.72, 0.22), (0.8, 0.7)])]
    if name == "shield":
        return [P_([(0, -0.92), (0.7, -0.6), (0.7, 0.15), (0, 0.92), (-0.7, 0.15), (-0.7, -0.6)]),
                P_([(-0.3, 0.0), (-0.08, 0.28), (0.36, -0.32)], closed=False)]
    if name == "bulb":
        return [C_(0, -0.25, 0.55), L_(-0.25, 0.42, 0.25, 0.42), L_(-0.2, 0.62, 0.2, 0.62),
                L_(-0.12, 0.8, 0.12, 0.8)]
    if name == "flag":
        return [L_(-0.5, -0.85, -0.5, 0.9), P_([(-0.5, -0.8), (0.6, -0.55), (-0.5, -0.2)], fill=color)]
    if name == "coin":
        return [C_(0, 0, 0.88), L_(0, -0.45, 0, 0.45), P_([(0.22, -0.28), (-0.22, -0.28),
                (-0.22, 0.0), (0.22, 0.0), (0.22, 0.3), (-0.22, 0.3)], closed=False)]
    if name == "grid":
        return [Rr(-0.8, -0.8, 0.62, 0.62), Rr(0.18, -0.8, 0.62, 0.62),
                Rr(-0.8, 0.18, 0.62, 0.62), Rr(0.18, 0.18, 0.62, 0.62)]
    if name == "layers":
        return [P_([(0, -0.7), (0.85, -0.25), (0, 0.2), (-0.85, -0.25)], fill=color),
                P_([(-0.85, 0.25), (0, 0.7), (0.85, 0.25)], closed=False)]
    if name == "clock":
        return [C_(0, 0, 0.9), L_(0, 0, 0, -0.5), L_(0, 0, 0.4, 0.15)]
    if name == "doc":
        return [P_([(-0.6, -0.85), (0.35, -0.85), (0.65, -0.5), (0.65, 0.85), (-0.6, 0.85)]),
                L_(-0.35, -0.25, 0.4, -0.25), L_(-0.35, 0.1, 0.4, 0.1), L_(-0.35, 0.45, 0.15, 0.45)]
    if name == "check":
        return [C_(0, 0, 0.92), P_([(-0.42, 0.0), (-0.12, 0.34), (0.45, -0.38)], closed=False)]
    if name == "route":
        return [C_(-0.6, -0.55, 0.22), C_(0.6, 0.55, 0.22),
                P_([(-0.6, -0.33), (-0.6, 0.2), (0.6, 0.2), (0.6, 0.33)], closed=False)]
    if name == "chart":
        return [L_(-0.7, -0.7, -0.7, 0.7), L_(-0.7, 0.7, 0.7, 0.7),
                P_([(-0.5, 0.3), (-0.1, -0.1), (0.2, 0.15), (0.62, -0.5)], closed=False)]
    if name == "spark":
        return [P_([(0, -0.9), (0.2, -0.2), (0.9, 0), (0.2, 0.2), (0, 0.9),
                    (-0.2, 0.2), (-0.9, 0), (-0.2, -0.2)], fill=color)]
    if name == "bridge":
        return [L_(-0.85, 0.5, 0.85, 0.5), P_([(-0.85, 0.5), (-0.4, -0.4), (0.4, -0.4), (0.85, 0.5)],
                closed=False), L_(-0.55, 0.5, -0.3, -0.05), L_(0, 0.5, 0, -0.4), L_(0.55, 0.5, 0.3, -0.05)]
    return [C_(0, 0, 0.8)]


def badge(cx, cy, r, name, color, tint, width=2.2):
    return [EL(cx, cy, r, fill=tint), *icon(name, cx, cy, r * 0.52, color, width)]


# --- composite blocks ------------------------------------------------------- #
def panel(x, y, w, h, *, title=None, fill=CARD, border=LINE, accent=None, tcolor=INK):
    out = [R(x, y, w, h, fill=fill, stroke=border, stroke_style={"stroke_width": 1},
             radius=10, decorative=True)]
    if accent:
        out.append(R(x, y, 5, h, fill=accent, radius=2.5, decorative=True))
    if title:
        out.append(T(x + 22, y + 17, w - 40, 18, title, size=13, color=tcolor, weight=700))
    return out


def bullets(x, y, w, items, *, size=13.5, gap=30, color=INK, marker=ORANGE, lead=None, lh=1.4, th=None):
    out, cy = [], y
    if lead:
        out.append(T(x, cy, w, 16, lead, size=11, color=MUTE, weight=700, upper=True, track=1))
        cy += 26
    for it in items:
        out.append(dot(x + 3, cy + 8, 3, marker))
        out.append(T(x + 16, cy, w - 16, th or (size + 8), it, size=size, color=color, lh=lh))
        cy += gap
    return out


def kpi_tiles(x, y, w, h, tiles, *, gap=18):
    n = len(tiles)
    tw = (w - gap * (n - 1)) / n
    out = []
    for i, (value, label, note, good) in enumerate(tiles):
        tx = x + i * (tw + gap)
        out += panel(tx, y, tw, h, fill=SOFT, accent=ORANGE)
        out.append(T(tx + 18, y + 18, tw - 32, 32, value, size=26, color=INK, weight=800, font=SERIF))
        out.append(T(tx + 18, y + 54, tw - 32, 28, label, size=10.5, color=MUTE, lh=1.25))
        if note:
            tcol = MUTE2 if good is None else (POS if good else NEG)
            out.append(T(tx + 18, y + h - 24, tw - 32, 14, note, size=9.5, color=tcol, weight=600))
    return out


def stat_tiles(x, y, w, h, tiles, *, gap=14):
    n = len(tiles)
    tw = (w - gap * (n - 1)) / n
    out = []
    for i, (value, label) in enumerate(tiles):
        tx = x + i * (tw + gap)
        out.append(R(tx, y, tw, h, fill=INK, radius=8, decorative=True))
        out.append(R(tx, y + h - 5, tw, 5, fill=ORANGE, radius=2.5, decorative=True))
        out.append(T(tx + 14, y + 16, tw - 24, 30, value, size=23, color=ON_DARK, weight=800, font=SERIF))
        out.append(T(tx + 14, y + 52, tw - 24, 26, label, size=9.5, color=ON_DARK_MUTE, lh=1.25))
    return out


def ring_pct(cx, cy, r, frac, color, *, track=NEUT_T, width=11, label=None):
    out = [EL(cx, cy, r, fill="none", stroke=track, stroke_style={"stroke_width": width})]
    n = max(8, int(64 * frac))
    pts = [[cx + r * math.cos(math.radians(-90 + 360 * frac * i / n)),
            cy + r * math.sin(math.radians(-90 + 360 * frac * i / n))] for i in range(n + 1)]
    out.append({"type": "polyline", "points": pts, "fill": "none", "stroke": color,
                "stroke_style": {"stroke_width": width, "stroke_linecap": "round"}})
    out.append(T(cx - r, cy - 18, 2 * r, 30, f"{int(round(frac * 100))}%", size=26, color=INK,
                weight=800, align="center", font=SERIF))
    if label:
        out.append(T(cx - r - 26, cy + r + 12, 2 * r + 52, 34, label, size=10.5, color=INK,
                    weight=700, align="center", lh=1.2))
    return out


def chart_group(L, ch):
    objs = ch.objects()
    for o in objs:
        if o.get("type") in ("rect", "image"):
            o["decorative"] = True
    return GRP(L, objs)


def service_card(x, y, w, h, *, ico, tag, title, body, color=ORANGE):
    out = panel(x, y, w, h, fill=CARD)
    out += badge(x + 34, y + 38, 21, ico, color, ORANGET)
    out.append(T(x + 62, y + 22, w - 76, 14, tag, size=9.5, color=ORANGE, weight=700, upper=True, track=2))
    out.append(T(x + 62, y + 37, w - 76, 22, title, size=15, color=INK, weight=700))
    out.append(T(x + 22, y + 80, w - 40, h - 94, body, size=11, color=MUTE, lh=1.45))
    return out


def avatar_mark(cx, cy, r, initials, color=INK):
    return [EL(cx, cy, r, fill=color),
            EL(cx, cy, r, fill="none", stroke=ORANGE, stroke_style={"stroke_width": 2.5}),
            T(cx - r, cy - 14, 2 * r, 30, initials, size=24, color=ON_DARK, weight=800,
              align="center", font=SERIF)]


def chip(x, y, label, *, w=None, fill=NEUT_T, color=INK):
    cw = w if w else 18 + len(label) * 7.2
    return [R(x, y, cw, 26, fill=fill, radius=13, decorative=True),
            T(x + 14, y + 6, cw - 24, 14, label, size=10.5, color=color, weight=600)], cw


def qa(x, y, w, q, a, *, num=None):
    out = []
    if num:
        out.append(T(x, y, 30, 18, num, size=13, color=ORANGE, weight=800, font=SERIF))
    out.append(T(x + 28, y - 1, w - 28, 36, q, size=12.5, color=INK, weight=700, lh=1.2))
    out.append(T(x + 28, y + 40, w - 28, 76, a, size=11, color=MUTE, lh=1.45))
    return out


# --- page chrome ------------------------------------------------------------ #
def page_chrome(b, pid, n, kicker, title, *, ico=None, corner=True):
    page = b.page(pid, canvas=CANVAS, coordinate_mode="absolute", reading_order=None)
    L = page.layer("main")
    ADD(L, R(0, 0, W, H, fill=PAPER, decorative=True))
    if corner:
        diag_field(L, [W - 150, 0, 150, 62], [ORANGE, INK, MUTE2], sw=18, gap=34)
    GRP(L, [
        T(MX, 66, CW - 170, 16, kicker, size=11, color=ORANGE, weight=700, upper=True, track=2),
        LN(MX, 134, MX + 46, 134, color=ORANGE, width=3),
        LN(MX, H - 60, W - MX, H - 60, color=LINE, width=1),
        T(MX, H - 50, 470, 14, FOOTER, size=9.5, color=MUTE),
        T(W - MX - 120, H - 50, 120, 14, f"{n:02d}", size=9.5, color=MUTE, align="right", weight=700),
    ])
    ADD(L, T(MX, 86, CW - 70, 40, title, size=30, color=INK, weight=800, font=SERIF, id="title"))
    if ico:
        GRP(L, badge(W - MX - 110, 98, 19, ico, ORANGE, ORANGET))
    return L


def section_band(x, y, w, h, *, fill=INK):
    return R(x, y, w, h, fill=fill, radius=12, decorative=True)


# ============================================================================ #
#  THE WHITE PAPER                                                              #
# ============================================================================ #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Inova Partners — Workforce Transition White Paper",
                        profile="report", lang="pt-BR")

    # ---------------------------------------------------------------- 01 CAPA
    page = b.page("p01", canvas=CANVAS, coordinate_mode="absolute", reading_order=None)
    L = page.layer("main")
    ADD(L, R(0, 0, W, H, fill=DARK, decorative=True))
    diag_field(L, [-60, 620, 560, 560], [ORANGE, ORANGE2, SLATE, "#525252"], sw=30, gap=66)
    diag_field(L, [W - 250, 0, 250, 110], [ORANGE, "#525252", ORANGE2], sw=20, gap=44)
    GRP(L, logo(MX, 80, on_dark=True, scale=1.15))
    ADD(L, R(MX, 470, 78, 6, fill=ORANGE, decorative=True))
    GRP(L, [T(MX, 360, 560, 18, "A PRIMEIRA WORKFORCE TRANSITION COMPANY DO BRASIL",
              size=12, color=ORANGE, weight=700, upper=True, track=2)])
    ADD(L, T(MX, 392, 640, 92, "White", size=92, color=ON_DARK, weight=800, font=SERIF))
    ADD(L, T(MX, 486, 640, 92, "Paper", size=92, color=ON_DARK, weight=800, font=SERIF))
    GRP(L, [
        T(MX, 600, 600, 30, "A transição da força de trabalho na era da IA.",
          size=22, color=ON_DARK_MUTE, font=SERIF, italic=True),
        T(MX, 642, 540, 44,
          "Do trabalho que está acabando ao trabalho que está nascendo existe uma "
          "travessia — nós construímos essa ponte.",
          size=13.5, color=ON_DARK_MUTE, lh=1.45),
    ])
    GRP(L, [
        LN(MX, H - 96, W - MX, H - 96, color="#3E3E3E", width=1),
        T(MX, H - 78, 420, 16, "inovapartners.com.br", size=13, color=ON_DARK, weight=700),
        T(MX, H - 58, 460, 14, "São Paulo, SP · Brasil", size=11, color=ON_DARK_MUTE),
        T(W - MX - 280, H - 78, 280, 16, "Edição 2026", size=11, color=ON_DARK_MUTE, align="right"),
        T(W - MX - 280, H - 58, 280, 14, "© 2026 Inova Partners", size=11,
          color=ON_DARK_MUTE, align="right"),
    ])

    # ------------------------------------------------------------------ 02 ÍNDICE
    L = page_chrome(b, "p02", 2, "Neste documento", "Índice", ico="doc")
    lw = 250
    GRP(L, panel(MX, TOP, lw, 562, fill=SOFT))
    GRP(L, [T(MX + 22, TOP + 26, lw - 44, 18, "SOBRE ESTE PAPER", size=11, color=ORANGE,
              weight=700, track=1)])
    GRP(L, [T(MX + 22, TOP + 52, lw - 44, 180,
              "Este white paper explica por que a adoção de IA é, antes de tudo, uma "
              "transição da força de trabalho — e como a Inova Partners conduz essa "
              "travessia: do diagnóstico ao redesenho e à implementação, até a mudança "
              "estar enraizada.", size=12, color=INK, lh=1.5)])
    GRP(L, [LN(MX + 22, TOP + 244, MX + lw - 22, TOP + 244, color=LINE, width=1),
            T(MX + 22, TOP + 260, lw - 44, 16, "CONTATO", size=11, color=ORANGE, weight=700, track=1)])
    contact = [("E-mail", "contato@inovapartners.com.br"),
               ("Telefone", "(11) 99736-3382"),
               ("Local", "São Paulo, SP · Brasil"),
               ("Diagnóstico", "diagnostico.inovapartners.com.br")]
    cy = TOP + 286
    crows = []
    for lab, val in contact:
        crows.append(T(MX + 22, cy, lw - 44, 13, lab.upper(), size=9, color=MUTE, weight=700, track=1))
        crows.append(T(MX + 22, cy + 15, lw - 44, 16, val, size=11, color=INK, weight=600))
        cy += 48
    GRP(L, crows)
    GRP(L, logo(MX + 22, TOP + 500, scale=0.95))

    rx = MX + lw + 28
    rw = W - MX - rx
    contents = [
        ("01", "Introdução", "A tese: IA é uma transição do trabalho", 3),
        ("02", "O Problema", "Por que 95% dos pilotos não chegam ao P&L", 4),
        ("03", "O Método", "Diagnóstico, redesenho e implementação", 5),
        ("04", "Os Seis Estágios", "De Spark a Pulse, a jornada completa", 6),
        ("05", "A Travessia", "A ponte do trabalho que acaba ao que nasce", 7),
        ("06", "O Brasil na Travessia", "29,8 milhões de trabalhadores expostos", 8),
        ("07", "Pontos de Entrada", "AI Transition Readiness e Spark Executive", 9),
        ("08", "Liderança", "Quem conduz a travessia", 10),
        ("09", "Perguntas Frequentes", "O que clientes perguntam antes de começar", 11),
    ]
    rows = []
    yy = TOP + 4
    for num, t, d, pg in contents:
        rows += panel(rx, yy, rw, 56, fill=CARD)
        rows.append(T(rx + 18, yy + 15, 46, 28, num, size=20, color=ORANGE, weight=800, font=SERIF))
        rows.append(T(rx + 72, yy + 12, rw - 140, 20, t, size=15, color=INK, weight=700))
        rows.append(T(rx + 72, yy + 33, rw - 140, 16, d, size=11, color=MUTE))
        rows.append(T(rx + rw - 56, yy + 18, 40, 22, f"{pg:02d}", size=15, color=SLATE,
                     weight=700, align="right", font=SERIF))
        yy += 62
    GRP(L, rows)

    # ------------------------------------------------------------ 03 INTRODUÇÃO
    L = page_chrome(b, "p03", 3, "Visão geral", "Introdução", ico="bridge")
    GRP(L, [T(MX, TOP, CW, 30,
              "A IA não é uma transição tecnológica. É uma transição da força de trabalho.",
              size=18, color=INK, weight=700, font=SERIF, lh=1.3)])
    colw = (CW - 28) / 2
    cx2 = MX + colw + 28
    GRP(L, [T(MX, TOP + 52, colw, 320,
              "A próxima década não será definida por quem adotou IA primeiro, mas por quem "
              "redesenhou o trabalho ao redor dela. A tecnologia já está disponível; o gargalo "
              "passou a ser organizacional — como recompor papéis, processos e equipes para que "
              "humanos e máquinas operem de forma coordenada.\n\n"
              "A Inova Partners nasceu para preencher exatamente essa lacuna: a primeira "
              "Workforce Transition Company do Brasil, dedicada a conduzir empresas pela maior "
              "transição do trabalho em um século.",
              size=12.5, color=INK, lh=1.55)])
    GRP(L, [T(cx2, TOP + 52, colw, 200,
              "Entre o trabalho que está acabando e o trabalho que está nascendo existe uma "
              "travessia. A maioria das organizações tenta cruzá-la começando pela ferramenta — "
              "e descobre, tarde demais, que faltou redesenhar o trabalho.\n\n"
              "Nós invertemos a ordem: primeiro o mapa de impacto na força de trabalho, depois a "
              "tecnologia. Diagnóstico, redesenho e implementação, entregues até a mudança estar "
              "enraizada.",
              size=12.5, color=INK, lh=1.55)])
    GRP(L, panel(cx2, TOP + 250, colw, 168, fill=INK))
    GRP(L, badge(cx2 + colw / 2, TOP + 318, 30, "bridge", ON_DARK, "#353535", width=3))
    GRP(L, [T(cx2, TOP + 378, colw, 16, "Do trabalho que acaba ao que nasce — a ponte",
              size=10.5, color=ON_DARK_MUTE, align="center")])
    by = TOP + 452
    GRP(L, [section_band(MX, by, CW, 196)])
    GRP(L, [R(MX, by, 5, 196, fill=ORANGE, radius=2.5, decorative=True),
            T(MX + 30, by + 26, 280, 26, "Missão & Visão", size=20, color=ON_DARK, weight=800, font=SERIF),
            LN(MX + 30, by + 60, MX + 86, by + 60, color=ORANGE, width=3)])
    half = (CW - 90) / 2
    GRP(L, [T(MX + 30, by + 78, half, 16, "MISSÃO", size=10.5, color=ORANGE, weight=700, track=2),
            T(MX + 30, by + 98, half, 80,
              "Preparar empresas para competir e pessoas para liderar na maior transição do "
              "trabalho em um século.",
              size=12, color=ON_DARK_MUTE, lh=1.5)])
    GRP(L, [T(MX + 30 + half + 30, by + 78, half, 16, "PRINCÍPIO", size=10.5, color=ORANGE, weight=700, track=2),
            T(MX + 30 + half + 30, by + 98, half, 80,
              "Não invista uma linha de código antes de ter o mapa do impacto na força de "
              "trabalho. O redesenho vem antes da ferramenta.",
              size=12, color=ON_DARK_MUTE, lh=1.5)])

    # -------------------------------------------------------------- 04 O PROBLEMA
    L = page_chrome(b, "p04", 4, "A evidência", "O Problema", ico="search")
    GRP(L, [T(MX, TOP, CW, 24,
              "Não falta tecnologia — falta redesenho do trabalho. É aí que o valor se perde.",
              size=13.5, color=MUTE, lh=1.4)])
    pw1 = CW * 0.46
    GRP(L, panel(MX, TOP + 44, pw1, 240, title="Onde os projetos de IA falham", accent=ORANGE))
    GRP(L, ring_pct(MX + pw1 * 0.27, TOP + 148, 46, 0.95, ORANGE,
                    label="pilotos sem\nchegar ao P&L"))
    GRP(L, ring_pct(MX + pw1 * 0.73, TOP + 148, 46, 0.75, INK,
                    label="papéis a redesenhar\naté 2030"))
    px2 = MX + pw1 + 24
    pw2 = W - MX - px2
    GRP(L, kpi_tiles(px2, TOP + 44, pw2, 116, [
        ("60%", "sem práticas de dados prontas para IA", "Gartner, 2025", None),
        ("<10%", "dos experimentos com agentes escalam", "McKinsey QB, 2025", None),
    ]))
    GRP(L, panel(px2, TOP + 180, pw2, 104, title="A leitura", accent=INK))
    GRP(L, bullets(px2 + 22, TOP + 212, pw2 - 44, [
        "O piloto prova a tecnologia; o que falha é a operação ao redor dela.",
        "Sem redesenhar papéis e dados, a IA não chega ao resultado.",
    ], gap=40, size=11.5, th=32))
    cyp = TOP + 304
    GRP(L, panel(MX, cyp, CW, 232, title="Por que a IA generativa ainda não virou resultado (% citado)"))
    fr = Frame(domain=(0, 0, 4, 100), box=(MX + 56, cyp + 54, CW - 100, 132))
    ch = Chart(frame=fr)
    cats = ["95% pilotos\nsem P&L", "80%+ sem\nimpacto", "60% sem\ndados", "90% agentes\nsem escala"]
    vals = [95, 82, 60, 90]
    ch.axes(y_ticks=[0, 50, 100], x_ticks=[0.5, 1.5, 2.5, 3.5],
            x_format=lambda v: ["95% MIT", "80% McK.", "60% Gart.", "90% McK."][int(v - 0.5)]
            if 0 <= int(v - 0.5) < 4 else "",
            y_format=lambda v: f"{int(v)}%", grid=True)
    ch.bars([(i + 0.5, v) for i, v in enumerate(vals)], width=58, fill=ORANGE, radius=3)
    chart_group(L, ch)
    GRP(L, [T(MX, cyp + 244, CW, 14,
              "Fontes: MIT (2025) · McKinsey (2026; QuantumBlack jun/2025) · Gartner (2025). "
              "Figuras reproduzidas conforme citadas; não verificadas de forma independente.",
              size=9, color=MUTE2, lh=1.35)])
    GRP(L, stat_tiles(MX, TOP + 568, CW, 84, [
        ("29,8 mi", "trabalhadores BR expostos à IA (FGV, 3T25)"),
        ("75%", "papéis a redesenhar até 2030 (McKinsey)"),
        ("95%", "pilotos sem chegar ao P&L (MIT)"),
        ("<10%", "agentes que escalam (McKinsey QB)"),
    ]))

    # ---------------------------------------------------------------- 05 O MÉTODO
    L = page_chrome(b, "p05", 5, "Como conduzimos", "O Método", ico="route")
    GRP(L, [T(MX, TOP, CW, 24,
              "Um arco disciplinado — diagnóstico, redesenho e implementação — até a mudança "
              "estar enraizada.", size=13.5, color=MUTE, lh=1.4)])
    phases = [
        ("01", "Diagnóstico", "search",
         "Mapear o impacto da IA na força de trabalho e dimensionar o valor em jogo — antes de qualquer ferramenta."),
        ("02", "Redesenho", "gear",
         "Recompor papéis, processos e dados para que humanos e máquinas trabalhem de forma coordenada."),
        ("03", "Implementação", "check",
         "Levar o redesenho à operação, medir o resultado no P&L e transferir capacidade até a mudança enraizar."),
    ]
    pw3 = (CW - 2 * 22) / 3
    ph = 252
    cards = []
    for i, (num, t, ico, d) in enumerate(phases):
        x = MX + i * (pw3 + 22)
        cards += panel(x, TOP + 56, pw3, ph, accent=ORANGE)
        cards.append(T(x + 22, TOP + 78, 60, 36, num, size=30, color=ORANGET, weight=800, font=SERIF))
        cards += badge(x + pw3 - 38, TOP + 92, 19, ico, ORANGE, ORANGET)
        cards.append(T(x + 22, TOP + 128, pw3 - 44, 22, t, size=18, color=INK, weight=800, font=SERIF))
        cards.append(LN(x + 22, TOP + 156, x + 60, TOP + 156, color=ORANGE, width=2.5))
        cards.append(T(x + 22, TOP + 168, pw3 - 44, 118, d, size=11.5, color=MUTE, lh=1.45))
    GRP(L, cards)
    py3 = TOP + 56 + ph + 28
    GRP(L, panel(MX, py3, CW, 196, fill=SOFT, title="Os princípios por trás do método", accent=INK))
    principles = [
        ("O mapa antes do código", "Sem o impacto na força de trabalho mapeado, não se investe em ferramenta."),
        ("Evidência sobre opinião", "Cada decisão se liga a um número que sustentamos."),
        ("Entrega até enraizar", "Não terminamos no piloto — terminamos quando a mudança fica."),
        ("Transferência de capacidade", "O time do cliente assume e sustenta sem depender de nós."),
    ]
    half = (CW - 80) / 2
    pr = []
    for i, (t, d) in enumerate(principles):
        r, c = divmod(i, 2)
        x = MX + 30 + c * (half + 20)
        y = py3 + 52 + r * 70
        pr.append(dot(x + 3, y + 8, 3.5, ORANGE))
        pr.append(T(x + 16, y, half - 20, 18, t, size=13, color=INK, weight=700))
        pr.append(T(x + 16, y + 20, half - 20, 36, d, size=11, color=MUTE, lh=1.4))
    GRP(L, pr)

    # ----------------------------------------------------- 06 OS SEIS ESTÁGIOS
    L = page_chrome(b, "p06", 6, "A jornada completa", "Os Seis Estágios", ico="layers")
    GRP(L, [T(MX, TOP, CW, 40,
              "De Spark a Pulse: seis estágios que levam a empresa do entendimento à "
              "transformação sustentada.", size=13.5, color=MUTE, lh=1.45)])
    services = [
        ("spark", "Estágio 01", "Spark",
         "Entender o impacto da IA no negócio antes de investir — sem precisar virar técnico."),
        ("layers", "Estágio 02", "Blueprint",
         "Estabelecer fundações de dados confiáveis para decidir com segurança."),
        ("target", "Estágio 03", "Ignition",
         "Demonstrar resultado real de IA em semanas, não meses — o centro de gravidade."),
        ("chart", "Estágio 04", "Momentum",
         "Escalar de uma área para a empresa inteira, com tração e governança."),
        ("route", "Estágio 05", "Shift",
         "Transformação operacional completa sem desestabilizar as funções atuais."),
        ("clock", "Estágio 06", "Pulse",
         "Sustentar os ganhos e preparar a empresa para as próximas ondas de IA."),
    ]
    gx, gy = MX, TOP + 64
    cw3 = (CW - 2 * 22) / 3
    ch3 = 198
    cards = []
    for i, (ico, tag, t, body) in enumerate(services):
        r, c = divmod(i, 3)
        cards += service_card(gx + c * (cw3 + 22), gy + r * (ch3 + 22), cw3, ch3,
                              ico=ico, tag=tag, title=t, body=body)
    GRP(L, cards)

    # ----------------------------------------------------------- 07 A TRAVESSIA
    L = page_chrome(b, "p07", 7, "A ponte", "A Travessia", ico="bridge")
    GRP(L, [T(MX, TOP, CW, 24,
              "A sequência que liga o trabalho que está acabando ao que está nascendo.",
              size=13.5, color=MUTE, lh=1.4)])
    GRP(L, [section_band(MX, TOP + 48, CW, 556)])
    roadmap = [
        ("Spark", "Entender o impacto da IA — o ponto de partida da travessia."),
        ("Blueprint", "Construir a fundação de dados sobre a qual tudo se apoia."),
        ("Ignition", "Provar valor real em semanas — o centro de gravidade."),
        ("Momentum", "Escalar de uma área para a organização inteira."),
        ("Shift", "Redesenhar a operação sem desestabilizar o presente."),
        ("Pulse", "Sustentar os ganhos e preparar as próximas ondas."),
    ]
    rsx = MX + 76
    r_top = TOP + 96
    r_seg = 430 / (len(roadmap) - 1)
    GRP(L, [LN(rsx, r_top, rsx, r_top + r_seg * (len(roadmap) - 1) + 2,
               color="#454545", width=2)])
    art = []
    for i, (t, d) in enumerate(roadmap):
        ny = r_top + r_seg * i
        art.append(EL(rsx, ny, 21, fill=ORANGE))
        art.append(T(rsx - 21, ny - 12, 42, 24, str(i + 1), size=18, color=ON_DARK, weight=800,
                    align="center", font=SERIF))
        art.append(T(rsx + 44, ny - 20, CW - 150, 22, t, size=17, color=ON_DARK, weight=700, font=SERIF))
        art.append(T(rsx + 44, ny + 5, CW - 160, 32, d, size=12.5, color=ON_DARK_MUTE, lh=1.4))
    GRP(L, art)

    # ------------------------------------------------- 08 O BRASIL NA TRAVESSIA
    L = page_chrome(b, "p08", 8, "Por que agora", "O Brasil na Travessia", ico="users")
    colw = (CW - 28) / 2
    cx2 = MX + colw + 28
    GRP(L, [T(MX, TOP, colw, 30, "A maior transição do trabalho em um século já começou.",
              size=16, color=INK, weight=700, font=SERIF, lh=1.3)])
    GRP(L, [T(MX, TOP + 50, colw, 300,
              "Segundo a FGV IBRE, com base na PNAD/IBGE, 29,8 milhões de trabalhadores "
              "brasileiros — cerca de 30% da população ocupada — já estão diretamente expostos "
              "à IA generativa. A McKinsey estima que 75% dos papéis atuais precisarão de "
              "redesenho, requalificação ou realocação até 2030.\n\n"
              "A exposição não é uma ameaça distante: é a agenda desta década. Quem redesenhar "
              "o trabalho primeiro define o ritmo — e protege tanto a competitividade da empresa "
              "quanto as carreiras das pessoas.",
              size=12.5, color=INK, lh=1.55)])
    GRP(L, bullets(MX, TOP + 372, colw, [
        "Mapear a exposição por função antes de automatizar.",
        "Requalificar e realocar, não apenas substituir.",
        "Levar a operação inteira junto — sem deixar ninguém para trás.",
    ], gap=44, size=12, th=32, lead="O que isso exige"))
    GRP(L, panel(cx2, TOP, colw, 150, fill=INK))
    GRP(L, [R(cx2 + 24, TOP + 26, 40, 5, fill=ORANGE, decorative=True),
            T(cx2 + 24, TOP + 44, colw - 48, 90,
              "“A próxima década será definida por quem redesenhou o trabalho ao redor da IA — "
              "não por quem a adotou primeiro.”",
              size=15, color=ON_DARK, font=SERIF, italic=True, lh=1.35),
            T(cx2 + 24, TOP + 122, colw - 48, 16, "— Tese fundadora da Inova Partners",
              size=10.5, color=ON_DARK_MUTE)])
    eco = [
        ("coin", "SEBRAETEC", "Subsídio de até 70% para PMEs em 5 estados ativos (PB, PE, MA, SC, AP)."),
        ("users", "FIEPB · SENAI · SESI", "Acesso à rede industrial e capacitação da força de trabalho."),
        ("search", "AI Transition Readiness", "Diagnóstico de 10 minutos, com sessão de interpretação."),
    ]
    sy = TOP + 176
    sl = []
    for i, (ico, t, d) in enumerate(eco):
        y = sy + i * 100
        sl += panel(cx2, y, colw, 86, fill=CARD)
        sl += badge(cx2 + 36, y + 43, 21, ico, ORANGE, ORANGET)
        sl.append(T(cx2 + 68, y + 16, colw - 86, 18, t, size=13.5, color=INK, weight=700))
        sl.append(T(cx2 + 68, y + 38, colw - 86, 38, d, size=10.5, color=MUTE, lh=1.4))
    GRP(L, sl)

    # ------------------------------------------------------ 09 PONTOS DE ENTRADA
    L = page_chrome(b, "p09", 9, "Por onde começar", "Pontos de Entrada", ico="flag")
    GRP(L, [T(MX, TOP, CW, 24,
              "Dois caminhos de baixo risco para iniciar a travessia — um para a organização, "
              "outro para o líder.", size=13.5, color=MUTE, lh=1.4)])
    cardw = (CW - 28) / 2
    entry = [
        ("search", "AI Transition Readiness", "Para a organização",
         "Um diagnóstico de 10 minutos, por convite individual, que revela onde sua empresa "
         "está na travessia e onde o trabalho precisa ser redesenhado. Inclui uma sessão de "
         "15 minutos de interpretação com o fundador.",
         ["10 minutos, por convite", "Interpretação com o fundador", "Mapa de prontidão da empresa"],
         "diagnostico.inovapartners.com.br"),
        ("compass", "Spark Executive", "Para o líder",
         "Uma trilha individual para o C-level entender o impacto real da IA no negócio — sem "
         "virar técnico. O ponto de partida pessoal para quem vai liderar a transição da "
         "própria organização.",
         ["Trilha individual C-level", "Linguagem de negócio, não de TI", "Prepara o líder da travessia"],
         "contato@inovapartners.com.br"),
    ]
    cards = []
    for i, (ico, t, who, body, pts, cta) in enumerate(entry):
        x = MX + i * (cardw + 28)
        cards += panel(x, TOP + 48, cardw, 470, accent=ORANGE)
        cards += badge(x + 44, TOP + 96, 26, ico, ORANGE, ORANGET, width=2.6)
        cards.append(T(x + 82, TOP + 78, cardw - 100, 14, who, size=10, color=ORANGE, weight=700, upper=True, track=2))
        cards.append(T(x + 82, TOP + 94, cardw - 100, 26, t, size=19, color=INK, weight=800, font=SERIF))
        cards.append(T(x + 28, TOP + 148, cardw - 56, 130, body, size=12, color=MUTE, lh=1.5))
        cards += bullets(x + 28, TOP + 286, cardw - 56, pts, gap=40, size=12, th=30)
        cards += panel(x + 28, TOP + 420, cardw - 56, 64, fill=SOFT)
        cards.append(T(x + 44, TOP + 434, cardw - 88, 14, "COMECE POR", size=9, color=MUTE, weight=700, track=1))
        cards.append(T(x + 44, TOP + 452, cardw - 88, 18, cta, size=12.5, color=ORANGE, weight=700))
    GRP(L, cards)
    cby = TOP + 540
    GRP(L, [section_band(MX, cby, CW, 92)])
    GRP(L, [R(MX, cby, 5, 92, fill=ORANGE, radius=2.5, decorative=True),
            T(MX + 30, cby + 22, CW - 260, 24, "Não invista uma linha de código antes deste mapa.",
              size=17, color=ON_DARK, weight=800, font=SERIF),
            T(MX + 30, cby + 52, CW - 280, 30,
              "O diagnóstico é o primeiro passo da travessia — e o de menor risco.",
              size=12, color=ON_DARK_MUTE, lh=1.4),
            T(W - MX - 230, cby + 38, 200, 18, "(11) 99736-3382", size=14, color=ON_DARK,
              weight=700, align="right")])

    # --------------------------------------------------------------- 10 LIDERANÇA
    L = page_chrome(b, "p10", 10, "Quem conduz", "Liderança", ico="users")
    GRP(L, [T(MX, TOP, CW, 24,
              "Uma metodologia forjada em transições de escala enterprise — liderada de perto, "
              "do diagnóstico ao fechamento.", size=13.5, color=MUTE, lh=1.4)])
    # founder card
    fx, fy, fw, fh = MX, TOP + 56, CW, 300
    GRP(L, panel(fx, fy, fw, fh, fill=CARD, accent=ORANGE))
    GRP(L, avatar_mark(fx + 110, fy + 130, 64, "RB"))
    GRP(L, [T(fx + 110 - 80, fy + 214, 160, 16, "FUNDADOR", size=10.5, color=ORANGE,
              weight=700, align="center", track=2)])
    tx = fx + 230
    tw = fw - 230 - 30
    GRP(L, [T(tx, fy + 40, tw, 30, "Rodrigo Bezerra", size=26, color=INK, weight=800, font=SERIF),
            T(tx, fy + 76, tw, 16, "MBA, MIT · 15+ anos liderando transições de escala enterprise",
              size=12, color=ORANGE, weight=600),
            T(tx, fy + 104, tw, 120,
              "Lidera as relações com clientes do diagnóstico ao fechamento do contrato. "
              "Construiu metodologias de transição da força de trabalho à frente de programas de "
              "transformação e inovação em algumas das maiores operações do país — combinando "
              "visão de negócio, dados e o redesenho do trabalho que a IA exige.",
              size=12.5, color=INK, lh=1.55)])
    GRP(L, [T(tx, fy + 230, tw, 14, "ONDE A METODOLOGIA FOI FORJADA", size=9.5, color=MUTE,
              weight=700, track=2)])
    chips_art = []
    cxp = tx
    for name in ["Natura", "Mercado Pago", "Twitter", "Claro", "Banco Safra"]:
        c_art, cwid = chip(cxp, fy + 250, name, fill=NEUT_T)
        chips_art += c_art
        cxp += cwid + 10
    GRP(L, chips_art)
    # credential tiles
    GRP(L, stat_tiles(MX, fy + fh + 28, CW, 86, [
        ("MIT", "MBA pela instituição"),
        ("15+", "anos em transformação"),
        ("5", "operações enterprise"),
        ("1ª", "WTC do Brasil"),
    ]))

    # ------------------------------------------------------------------- 11 FAQ
    L = page_chrome(b, "p11", 11, "Antes de começar", "Perguntas Frequentes", ico="doc")
    colw = (CW - 36) / 2
    cx2 = MX + colw + 36
    faqs_l = [
        ("01", "O que é uma Workforce Transition Company?",
         "Uma empresa dedicada a conduzir a transição da força de trabalho na adoção de IA — diagnóstico, redesenho e implementação — em vez de apenas entregar tecnologia."),
        ("02", "Por que não começar pela tecnologia?",
         "Porque 95% dos pilotos não chegam ao P&L. Sem mapear o impacto no trabalho e redesenhar papéis e dados, a ferramenta não vira resultado."),
        ("03", "Em quanto tempo vemos resultado?",
         "O estágio Ignition é desenhado para demonstrar valor real em semanas, não meses — e serve como centro de gravidade da transição."),
    ]
    faqs_r = [
        ("04", "Vocês escalam sem desestabilizar a operação?",
         "Sim. O estágio Shift conduz a transformação operacional completa sem desestabilizar as funções que mantêm a empresa funcionando hoje."),
        ("05", "Como medem sucesso?",
         "Pelo resultado na operação e no P&L, e pela entrega até a mudança estar enraizada — com a capacidade transferida ao time do cliente."),
        ("06", "Existe apoio ou subsídio?",
         "Para PMEs, o SEBRAETEC pode subsidiar até 70% em estados ativos (PB, PE, MA, SC, AP), além do acesso à rede FIEPB/SENAI/SESI."),
    ]
    yy = TOP + 16
    left = []
    for num, q, a in faqs_l:
        left += qa(MX, yy, colw, q, a, num=num)
        left.append(LN(MX, yy + 122, MX + colw, yy + 122, color=LINE, width=1))
        yy += 144
    GRP(L, left)
    yy = TOP + 16
    right = []
    for num, q, a in faqs_r:
        right += qa(cx2, yy, colw, q, a, num=num)
        right.append(LN(cx2, yy + 122, cx2 + colw, yy + 122, color=LINE, width=1))
        yy += 144
    GRP(L, right)
    cby = TOP + 16 + 144 * 3 + 6
    GRP(L, [section_band(MX, cby, CW, 116)])
    GRP(L, [R(MX, cby, 5, 116, fill=ORANGE, radius=2.5, decorative=True),
            T(MX + 30, cby + 26, CW - 220, 26, "Ainda tem uma pergunta?", size=19, color=ON_DARK,
              weight=800, font=SERIF),
            T(MX + 30, cby + 58, CW - 240, 40,
              "Fale direto com o time — teremos prazer em conversar sobre o seu momento antes de "
              "qualquer compromisso.", size=12, color=ON_DARK_MUTE, lh=1.45),
            T(W - MX - 260, cby + 44, 230, 18, "contato@inovapartners.com.br", size=13.5,
              color=ON_DARK, weight=700, align="right")])

    # ------------------------------------------------------------ 12 CAPA FINAL
    page = b.page("p12", canvas=CANVAS, coordinate_mode="absolute", reading_order=None)
    L = page.layer("main")
    ADD(L, R(0, 0, W, H, fill=DARK, decorative=True))
    diag_field(L, [W - 470, -40, 520, 560], [ORANGE, ORANGE2, SLATE, "#525252"], sw=30, gap=66)
    diag_field(L, [0, H - 110, 250, 110], [ORANGE, "#525252", ORANGE2], sw=20, gap=44)
    GRP(L, logo(MX, 96, on_dark=True, scale=1.15))
    ADD(L, R(MX, 360, 78, 6, fill=ORANGE, decorative=True))
    ADD(L, T(MX, 388, 620, 64, "Vamos construir", size=44, color=ON_DARK, weight=800, font=SERIF))
    ADD(L, T(MX, 440, 620, 64, "a travessia.", size=44, color=ON_DARK, weight=800, font=SERIF))
    GRP(L, [T(MX, 532, 540, 60,
              "Se você precisa redesenhar o trabalho ao redor da IA — e não apenas adotá-la — "
              "nós deveríamos conversar.",
              size=15, color=ON_DARK_MUTE, font=SERIF, italic=True, lh=1.4)])
    contact2 = [("SITE", "inovapartners.com.br"),
                ("E-MAIL", "contato@inovapartners.com.br"),
                ("WHATSAPP", "(11) 99736-3382 · wa.me/5511997363382"),
                ("LOCAL", "São Paulo, SP · Brasil")]
    cyc = 648
    rows = []
    for lab, val in contact2:
        rows.append(T(MX, cyc, 110, 14, lab, size=10, color=ORANGE, weight=700, track=2))
        rows.append(T(MX + 118, cyc - 2, 500, 20, val, size=14, color=ON_DARK, weight=600))
        cyc += 38
    GRP(L, rows)
    GRP(L, [LN(MX, H - 96, W - MX, H - 96, color="#3E3E3E", width=1),
            T(MX, H - 78, 540, 16, "INOVA PARTNERS  ·  Workforce Transition White Paper  ·  Edição 2026",
              size=11, color=ON_DARK_MUTE),
            T(MX, H - 58, 540, 14, "© 2026 Inova Partners. Todos os direitos reservados.",
              size=10.5, color=ON_DARK_MUTE)])

    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} A4 pages — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    from framegraph.sdk import serialize
    out = os.path.join(ROOT, "fixtures", "inova-partners-whitepaper.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
