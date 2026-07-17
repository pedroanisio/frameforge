#!/usr/bin/env python3
"""Stage-poster reconstruction study, v2 — geometry measured from the reference.

Hand-authored FrameForge primitives only (no tracing): the numeral is a
flag+stem polygon plus one elliptical bowl stroke; the dark sweep is a
tapered ``stroke_outline``; type runs are per-glyph placements along the
measured centreline. Canvas equals the reference frame (476x667) so
overlay/compare tools register 1:1.

Exposes ``build() -> DocumentBuilder`` (the MCP run contract).
"""
from __future__ import annotations

import math

from frameforge.sdk import DocumentBuilder
from frameforge.sdk.paint import (rgba, hatch, radial_gradient, filter_chain, filter_fn,
                                  style_effects)
from frameforge.sdk.outline import stroke_outline
from frameforge.sdk.metrics import measure_text
from frameforge.sdk.pathtext import text_on_path

W, H = 476, 667
ART = (12, 12, 450, 593)          # measured art-area frame on the white page

PAGE = "#FAF7F2"
CREAM = "#EEE7C4"
CREAM_DK = "#DFD5B0"
YELLOW = "#F5BB0E"                 # sampled fill of the numeral
INK = "#332B1D"                    # sampled fill of the sweep

COND_XB = ["Fira Sans Condensed ExtraBold", "Fira Sans Condensed", "Fira Sans"]
COND_SB = ["Fira Sans Condensed SemiBold", "Fira Sans Condensed", "Fira Sans"]

TILT = -29.0                       # one angle governs bars and titles (PCA-measured)

# measured centreline of the dark sweep: vertical stem, then the widening curve
SWEEP = [(251, 71), (246, 130), (243, 185), (249, 206), (278, 214), (314, 227),
         (350, 247), (377, 281), (398, 320), (411, 362), (414, 398), (407, 433),
         (400, 455)]


def ts(size, color, *, family=COND_SB, weight=600, align=None, ls=None):
    s = {"font_family": family, "font_size": size, "font_weight": weight, "color": color,
         "text_transform": "uppercase"}
    if align:
        s["align"] = align
    if ls is not None:
        s["letter_spacing"] = ls
    return s


def st(w, color, cap="butt"):
    return {"stroke": color, "stroke_style": {"stroke_width": w, "stroke_linecap": cap,
                                              "stroke_linejoin": "round"}}


def path_walk(pts):
    segs, L = [], 0.0
    for p, q in zip(pts, pts[1:]):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        segs.append((L, p, q, d))
        L += d

    def at(s):
        s = max(0.0, min(s, L - 1e-6))
        for l0, p, q, d in segs:
            if s <= l0 + d:
                u = (s - l0) / d
                return ((p[0] + u * (q[0] - p[0]), p[1] + u * (q[1] - p[1])),
                        ((q[0] - p[0]) / d, (q[1] - p[1]) / d))
        return (segs[-1][2], ((1, 0)))
    return at, L


def offset_path(pts, off):
    """Centreline shifted along its left normal (−ty, tx) by `off` (concave side)."""
    out, n = [], len(pts)
    for i, p in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1.0
        out.append((p[0] - ty / l * off, p[1] + tx / l * off))
    return out


def path_text(pg, pts, text, *, s0, offset, size, family, weight, color=INK, track=2.5):
    """Per-glyph type walking the offset path itself, so spacing stays true."""
    at, _L = path_walk(offset_path(pts, offset))
    fam = family[0]
    s = s0
    for ch in text:
        w = measure_text(ch, font_family=fam, font_size=size) if ch != " " else size * 0.32
        adv = w + track
        (px, py), (tx, ty) = at(s + adv / 2)
        if ch != " ":
            pg.text([px - 20, py - size * 0.74, 40, size * 1.35], ch,
                    style=ts(size, color, family=family, weight=weight, align="center"),
                    rotation=math.degrees(math.atan2(ty, tx)))
        s += adv


def paper(pg):
    pg.rect([0, 0, W, H], fill=PAGE)
    x, y, w, h = ART
    pg.rect([x, y, w, h], fill=CREAM)
    pg.rect([x, y, w, h], fill=hatch(fg=rgba(CREAM_DK, 0.55), scale=4, angle=45),
            decorative=True)
    pg.rect([x, y, w, h], fill=CREAM, opacity=0.35, decorative=True,
            **style_effects(filter=filter_chain(
                filter_fn("turbulence", base_frequency=0.9, num_octaves=2, seed=2012,
                          type="fractalNoise", opacity=0.15)), mix_blend_mode="multiply"))
    pg.rect([x, y, w, h], decorative=True,
            fill=radial_gradient([(rgba("#8A7A50", 0.0), 0.72), (rgba("#8A7A50", 0.10), 1.0)]),
            **style_effects(mix_blend_mode="multiply"))
    # left-edge imprint column, suggested as an illegible hairline
    pg.line([8, 440], [8, 604], **st(1.5, rgba(INK, 0.35), cap="butt"))


def numeral(pg):
    # flag + stem — the measured 6-corner polygon, verbatim geometry
    pg.polygon([[220, 96], [59, 184], [77, 214], [173, 162], [150, 303], [195, 242]],
               fill=YELLOW)
    # lower bowl — elliptical arc stroke, centreline fit C=(253,393) a=112 b=124
    a, b, cx, cy = 112.0, 124.0, 253.0, 393.0
    pts = [[cx + a * math.cos(math.radians(t)), cy + b * math.sin(math.radians(t))]
           for t in range(-139, 104, 4)]
    pg.polyline(pts, fill="none", **st(34, YELLOW))


def sweep(pg):
    # tapering dark band: full width down the stem, thinning through the curve
    obj = stroke_outline([(x, y) for x, y in SWEEP], 33.0,
                         profile=lambda t: 1.0 if t < 0.32 else 1.0 - 0.62 * (t - 0.32) / 0.68,
                         cap="butt", smooth=True)
    obj["fill"] = INK
    pg.add(obj)


def stage_bars(pg):
    pg.line([51, 166], [213, 85], **st(13, INK))
    pg.text([44, 138, 90, 18], "STAGE",
            style=ts(11, CREAM, family=COND_SB, weight=600, align="center", ls=1.6),
            rotation=TILT)
    pg.line([80, 217], [147, 187], **st(13, INK))
    pg.text([63, 192, 102, 16], "197 KILOMETERS",
            style=ts(8.5, CREAM, family=COND_SB, weight=600, align="center", ls=0.8),
            rotation=TILT)


def titles(pg):
    pg.extend(text_on_path(SWEEP, "TOUR DE FRANCE 2012", s0=158, offset=29,
                            size=22, family=COND_SB, weight=600, color=INK,
                            track=3.2, style={"text_transform": "uppercase"}))
    pg.text([99, 314, 300, 66], "ORCHIES",
            style=ts(54, INK, family=COND_XB, weight=800, align="center", ls=0.5),
            rotation=TILT)
    pg.text([59, 374, 340, 46], "BOULOGNE-SUR-MER",
            style=ts(35, INK, family=COND_XB, weight=800, align="center", ls=0.3),
            rotation=TILT)
    pg.line([103, 486], [319, 369], **st(2.5, INK, cap="butt"))
    pg.text([202, 430, 170, 22], "TUESDAY 3 JULY",
            style=ts(15, YELLOW, family=COND_XB, weight=800, align="center", ls=1.0),
            rotation=TILT)
    # circled monogram
    pg.ellipse([237, 481], 10, 10, fill="none", stroke=rgba(INK, 0.4),
               stroke_style={"stroke_width": 1.2})
    pg.polyline([[231, 482], [235, 477], [239, 484], [243, 478]], smooth=True, fill="none",
                **st(1, rgba(INK, 0.4), cap="round"))


def cyclist(pg):
    """Rider on the shoulder of the sweep — wheels at the measured centres."""
    rear, front, r = (281, 181), (315, 197), 14.0
    ang = math.atan2(front[1] - rear[1], front[0] - rear[0])
    cr, sr = math.cos(ang), math.sin(ang)
    mid = ((rear[0] + front[0]) / 2, (rear[1] + front[1]) / 2)

    def P(x, y):
        return [mid[0] + x * cr - y * sr, mid[1] + x * sr + y * cr]

    def line(p, q, w):
        pg.line(P(*p), P(*q), **st(w, INK, cap="round"))

    for wx in (-19.5, 19.5):
        pg.ellipse(P(wx, 0), r, r, fill="none", stroke=INK, stroke_style={"stroke_width": 2.6})
        pg.ellipse(P(wx, 0), 1.6, 1.6, fill=INK)
    line((-19.5, 0), (0, -3.5), 2)
    line((0, -3.5), (-8, -19), 2.4)
    line((0, -3.5), (12, -17.5), 2.4)
    line((-8.5, -19.5), (11, -18), 2)
    line((12, -17.5), (19.5, 0), 2)
    line((-19.5, 0), (-8, -19), 1.8)
    pg.ellipse(P(0, -3.5), 3.4, 3.4, fill="none", stroke=INK, stroke_style={"stroke_width": 1.8})
    pg.polygon([P(-10, -20), P(-7, -26), P(-1, -30), P(6, -32), P(12, -31), P(14, -28),
                P(9, -24), P(2, -22), P(-5, -19)], smooth=True, fill=INK)
    pg.ellipse(P(16, -30), 4.3, 4.3, fill=INK)
    line((9, -28), (15, -19), 2.6)
    line((-7, -20), (4, -12), 3)
    line((4, -12), (1, -2.5), 2.6)
    line((-7, -20), (-2, -9), 2.6)


def footer(pg):
    d = 18
    pg.polygon([[238, 637 - d], [238 + d * 0.95, 637], [238, 637 + d], [238 - d * 0.95, 637]],
               fill="none", stroke=INK, stroke_style={"stroke_width": 1.6})
    pg.ellipse([238, 637], 4, 4, fill="none", stroke=rgba(INK, 0.7),
               stroke_style={"stroke_width": 1})


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Stage poster reconstruction study v2", profile="diagram", lang="en")
    pg = b.page("poster", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    pg.layer("paper")
    paper(pg)
    pg.layer("art")
    numeral(pg)
    sweep(pg)
    cyclist(pg)
    footer(pg)
    pg.layer("type")
    with pg.lettering():
        stage_bars(pg)
        titles(pg)
    return b
