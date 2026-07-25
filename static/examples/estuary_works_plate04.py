#!/usr/bin/env python3
"""THE ESTUARY WORKS — Plate 04 · 3840x2160 single-canvas technical plate.

A FrameForge adaptation of the estuary-works build plan: one dark editorial
plate documenting the (fictional) Meridian Barrier proving closure of
2026-02-28 — hero dusk scene, cross-section at pier 4, exploded gate module,
flood-extent map, water-level chart, operations console, and a two-column
essay, all driven by one token system and computed data.

Exposes ``build() -> DocumentBuilder`` (the MCP run contract).
"""
from __future__ import annotations

import math
import random

from frameforge.sdk import DocumentBuilder
from frameforge.sdk.paint import linear_gradient, radial_gradient, rgba, hatch, dots
from frameforge.sdk.paint import (blur_filter, filter_chain, filter_fn,
                                  style_effects)
from frameforge.sdk.chevreul import contrast_ratio
from frameforge.sdk.metrics import measure_text, wrap_text

W, H = 3840, 2160
SEED = 1849

# --------------------------------------------------------------------------- #
# §0 · Colour — the source plan's oklch tokens, converted exactly to sRGB.
# --------------------------------------------------------------------------- #
def oklch(L, C, Hdeg):
    hr = math.radians(Hdeg)
    a, b = C * math.cos(hr), C * math.sin(hr)
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = +4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bl = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    def gam(u):
        u = min(1.0, max(0.0, u))
        return 12.92 * u if u <= 0.0031308 else 1.055 * u ** (1 / 2.4) - 0.055
    return "#%02X%02X%02X" % tuple(round(gam(v) * 255) for v in (r, g, bl))


INK    = oklch(0.96, 0.012, 95)    # near-white warm ink
INK2   = oklch(0.80, 0.015, 95)
INK3   = oklch(0.62, 0.015, 95)
PAPER  = oklch(0.165, 0.020, 245)  # deep blue-grey ground
PANELC = oklch(0.205, 0.022, 245)  # panel surface (used at alpha .72)
LINE   = oklch(0.72, 0.020, 245)   # hairlines (used at alpha .42)
SIGNAL = oklch(0.685, 0.185, 45)   # orange — structure & emphasis
TIDE   = oklch(0.775, 0.105, 215)  # cyan — water, data
SILT   = oklch(0.635, 0.045, 80)   # warm sediment neutral
OK     = oklch(0.76, 0.13, 155)
WARN   = oklch(0.80, 0.14, 85)
FAULT  = oklch(0.62, 0.19, 25)

LINE_A = rgba(LINE, 0.42)
GRID_A = rgba(LINE, 0.14)
PANEL_A = rgba(PANELC, 0.78)

# hero-scene locals (tones of the closed palette, not new duties)
SKY_HI   = oklch(0.14, 0.020, 250)
SKY_MID  = oklch(0.24, 0.035, 240)
DUSK     = oklch(0.45, 0.085, 55)   # low-sun band, subdued signal kin
WATER_HI = oklch(0.30, 0.045, 225)
WATER_LO = oklch(0.15, 0.022, 240)
CONC     = oklch(0.34, 0.020, 250)  # concrete in shadow
CONC_LIT = oklch(0.47, 0.045, 70)   # concrete, sun side
STEEL    = oklch(0.42, 0.115, 45)   # gate steel in shadow
STEEL_LIT = oklch(0.58, 0.155, 48)  # gate steel, lit face

# --------------------------------------------------------------------------- #
# §3 · Type — IBM Plex is not resolvable in this runtime; nearest coherent
# substitutes: Fira Sans / Condensed / Mono + Charis SIL (Charter) serif.
# --------------------------------------------------------------------------- #
SERIF   = ["Charis SIL", "Gentium", "DejaVu Serif", "serif"]
SANS    = ["Fira Sans", "DejaVu Sans", "sans-serif"]
SANS_SB = ["Fira Sans SemiBold", "Fira Sans", "DejaVu Sans", "sans-serif"]
COND    = ["Fira Sans Condensed SemiBold", "Fira Sans Condensed", "Fira Sans"]
MONO    = ["Fira Mono", "DejaVu Sans Mono", "monospace"]
MONO_MD = ["Fira Mono Medium", "Fira Mono", "DejaVu Sans Mono", "monospace"]


def ts(size, color, *, family=SANS, weight=None, lh=None, ls=None, align=None,
       upper=False, italic=False, shadow=None, opacity=None, letter_spacing=None):
    if letter_spacing is not None:
        ls = letter_spacing
    s = {"font_family": family, "font_size": size, "color": color}
    if weight is not None:
        s["font_weight"] = weight
    if lh is not None:
        s["line_height"] = lh
    if ls is not None:
        s["letter_spacing"] = ls
    if align is not None:
        s["align"] = align
    if upper:
        s["text_transform"] = "uppercase"
    if italic:
        s["italic"] = True
    if shadow is not None:
        s["text_shadow"] = shadow
    if opacity is not None:
        s["opacity"] = opacity
    return s


TY = {
    "display": ts(168, INK,  family=COND, weight=600, lh=160 / 168, ls=-1.7, upper=True),
    "kicker":  ts(22, SIGNAL, family=MONO_MD, weight=500, lh=32 / 22, ls=3.1, upper=True),
    "stand":   ts(44, INK2, family=SERIF, lh=56 / 44, italic=True),
    "body":    ts(27, INK,  family=SERIF, lh=32 / 27),
    "caption": ts(22, INK2, family=SANS, lh=28 / 22),
    "foot":    ts(21, INK3, family=SERIF, lh=24 / 21),
    "label":   ts(20, INK2, family=SANS_SB, weight=600, lh=24 / 20, ls=2.0, upper=True),
    "data":    ts(22, INK,  family=MONO, lh=32 / 22),
    "chip":    ts(19, INK2, family=MONO_MD, weight=500, lh=24 / 19, ls=1.15, upper=True),
}


def sty(name, **over):
    s = dict(TY[name])
    s.update({k: v for k, v in over.items() if v is not None})
    return s


def st(w, color=None, dash=None, cap="round", join="round"):
    d = {"stroke_width": w, "stroke_linecap": cap, "stroke_linejoin": join}
    if dash is not None:
        d["stroke_dasharray"] = list(dash)
    return ({"stroke": color} if color is not None else {}) | {"stroke_style": d}


def lerp(a, b, t):
    return a + (b - a) * t


def grad(stops, angle=180):
    return linear_gradient([(c, p / 100.0) for p, c in stops], angle=angle)


def rgrad(stops, at=None):
    return radial_gradient([(c, p / 100.0) for p, c in stops], at=at)


def wobble(scale, seed=18497, freq=(0.004, 0.09)):
    """§6 water adaptation — the painter's displacement filter is self-contained:
    it reads its own noise params (base_frequency/seed/octaves) off the same FilterFn."""
    return style_effects(filter=filter_chain(
        filter_fn("displacement_map", scale=scale, base_frequency=list(freq),
                  num_octaves=2, seed=seed, type="fractalNoise")))


def film_grain(seed, freq=0.71, opacity=0.35):
    """§19 grain adaptation — the painter's turbulence preset multiplies noise into
    the source at `opacity` (FuncA slope); callers set the object-level blend."""
    return filter_chain(
        filter_fn("turbulence", base_frequency=freq, num_octaves=2, seed=seed,
                  type="fractalNoise", opacity=opacity))


# --------------------------------------------------------------------------- #
# §1 · Layout constants (the 16-column grid of the plan)
# --------------------------------------------------------------------------- #
MX = 128                      # side margins
COL_L = (128, 872)            # essay zone   x, w
COL_C = (1032, 1550)          # section zone x, w
COL_R = (2614, 1098)          # panel rail   x, w
Y_MAST, Y_RULE = 120, 504
Y_CONTENT = 536
Y_COLO = 2008
BASE = 32                     # baseline grid


def elbow(pg, frm, to, color=LINE_A, w=1.5):
    """Elbow leader: vertical from `frm`, then horizontal into `to`."""
    midy = to[1]
    pg.polyline([[frm[0], frm[1]], [frm[0], midy], [to[0], midy]],
                fill="none", **st(w, color, cap="round"))
    pg.ellipse([frm[0], frm[1]], 4, 4, fill=color)


def num_chip(pg, cx, cy, n, r=15):
    pg.ellipse([cx, cy], r, r, fill=SIGNAL)
    pg.text([cx - r, cy - 12, 2 * r, 24], str(n),
            style=ts(19, PAPER, family=MONO_MD, weight=500, align="center"))


def gate_glyph(pg, x, y, s, color, w=2.0):
    """sym.gate — a sill line and a quarter-arc leaf over it."""
    pg.line([x - s / 2, y], [x + s / 2, y], **st(w, color))
    arc = [[x + (s / 2) * math.cos(math.radians(a)), y - (s / 2) * math.sin(math.radians(a))]
           for a in range(20, 95, 8)]
    pg.polyline(arc, fill="none", **st(w, color))


def panel(pg, x, y, w, h, title):
    """C.panel — translucent glass card with an uppercase label; returns body box."""
    pg.rect([x + 6, y + 10, w, h], radius=20, fill=rgba("#000000", 0.28))
    pg.rect([x, y, w, h], radius=20, fill=PANEL_A, stroke=LINE_A,
            stroke_style={"stroke_width": 1},
            **style_effects(backdrop_filter=filter_chain(blur_filter("18px"))))
    pg.text([x + 24, y + 20, w - 48, 24], title, style=sty("label"))
    return (x + 24, y + 64, w - 48, h - 88)


# --------------------------------------------------------------------------- #
# §14 · Data — harmonic prediction + surge + seeded noise, computed for real.
# t is hours from 2026-02-27T00:00Z over 72 h at 6-minute steps.
# --------------------------------------------------------------------------- #
HARM = [  # name, amplitude m, phase deg, period h (standard constituent speeds)
    ("M2", 2.21, 143, 12.4206012),
    ("S2", 0.71, 188, 12.0),
    ("N2", 0.44, 121, 12.65834751),
    ("K1", 0.09, 17, 23.93447213),
    ("O1", 0.07, 352, 25.81933871),
]
DATUM = 0.42
T_PEAK = 27.0 + 40.0 / 60.0          # 2026-02-28T03:40Z
SURGE_SIGMA = 2.6                     # 2 h 36 m
DEFENCE = 4.60
PEAK_TARGET = 5.31                    # the essay's stated peak — surge calibrated to it


def predicted(t):
    v = DATUM
    for _n, amp, ph, per in HARM:
        v += amp * math.cos(2 * math.pi * t / per - math.radians(ph))
    return v


def surge_base(t):
    return math.exp(-(((t - T_PEAK) / SURGE_SIGMA) ** 2))


T_STEP = 0.1
TS_H = [i * T_STEP for i in range(0, 721)]
_PRED = [predicted(t) for t in TS_H]
# calibrate surge amplitude so the combined peak hits the stated 5.31 m
_amp = 1.9
for _ in range(4):
    comb = [p + _amp * surge_base(t) for p, t in zip(_PRED, TS_H)]
    i_mx = max(range(len(comb)), key=lambda i: comb[i])
    _amp += (PEAK_TARGET - comb[i_mx]) / max(surge_base(TS_H[i_mx]), 1e-6)
SURGE_AMP = _amp
_SMOOTH = [p + SURGE_AMP * surge_base(t) for p, t in zip(_PRED, TS_H)]
_rng = random.Random(184910)
_OBS = [v + _rng.gauss(0.0, 0.05) for v in _SMOOTH]
PEAK_I = max(range(len(_SMOOTH)), key=lambda i: _SMOOTH[i])
PEAK_T, PEAK_V = TS_H[PEAK_I], _SMOOTH[PEAK_I]


def _hhmm(t):
    hh = int(t) % 24
    mm = int(round((t - int(t)) * 60))
    if mm == 60:
        hh, mm = (hh + 1) % 24, 0
    return f"{hh:02d}:{mm:02d}"


# closure window: where the smooth combined level exceeds the defence level
_above = [i for i, v in enumerate(_SMOOTH) if v > DEFENCE]
CLOSE_T0, CLOSE_T1 = TS_H[_above[0]], TS_H[_above[-1]]
CLOSURE_LABEL = f"closure {_hhmm(CLOSE_T0)}–{_hhmm(CLOSE_T1)} · peak {PEAK_V:.2f} m"

CLOSURES = [(1987, 0), (1991, 1), (1995, 0), (1999, 1), (2003, 1), (2007, 2),
            (2011, 1), (2015, 2), (2019, 2), (2022, 3), (2023, 1), (2024, 2),
            (2025, 1), (2026, 1)]

# --------------------------------------------------------------------------- #
# Hero scene (§5–§9 adapted) — dusk over the barrier, drawn in tone first.
# Nine modules recede left→right toward the horizon; gates 4–5 stand closed,
# gate 7 is mid-travel. Everything is decorative ground for the plate.
# --------------------------------------------------------------------------- #
HORIZON = 940
SUN = (2280, 918)


def module_xy(i):
    """Anchor (waterline centre), and px-per-metre scale for module i (0..8)."""
    t = i / 8.0
    x = 1128 + t * 1340
    y = 1192 - t * 258
    k = 3.55 - t * 2.60            # px per metre
    return x, y, k


def hero(pg):
    dec = {"decorative": True}
    # sky
    pg.rect([0, 0, W, HORIZON], fill=grad([
        (0, SKY_HI), (52, SKY_MID), (82, oklch(0.33, 0.055, 250)),
        (94, DUSK), (100, oklch(0.52, 0.105, 60))]), **dec)
    # sun glow
    pg.ellipse([SUN[0], SUN[1]], 620, 240, fill=rgrad([
        (0, rgba(oklch(0.72, 0.13, 60), 0.55)), (45, rgba(DUSK, 0.28)),
        (100, rgba(DUSK, 0.0))]), **dec)
    # far shore strips
    pg.polygon([[0, HORIZON], [520, HORIZON - 26], [1180, HORIZON - 8], [1560, HORIZON],
                [0, HORIZON]], fill=oklch(0.175, 0.02, 250), **dec)
    pg.polygon([[2510, HORIZON], [3080, HORIZON - 20], [3840, HORIZON - 34],
                [3840, HORIZON], [2510, HORIZON]], fill=oklch(0.175, 0.02, 250), **dec)
    # water
    pg.rect([0, HORIZON, W, H - HORIZON], fill=grad([
        (0, oklch(0.40, 0.075, 70)), (7, WATER_HI), (34, oklch(0.22, 0.035, 235)),
        (100, WATER_LO)]), **dec)
    # sun lane on the water
    pg.polygon([[SUN[0] - 55, HORIZON + 2], [SUN[0] + 55, HORIZON + 2],
                [SUN[0] + 210, 1520], [SUN[0] - 290, 1520]],
               fill=grad([(0, rgba(oklch(0.62, 0.12, 60), 0.16)),
                          (100, rgba(oklch(0.62, 0.12, 60), 0.0))]),
               decorative=True, **wobble(16, freq=(0.003, 0.11)))
    # wave strokes — seeded, denser and shorter near the horizon
    wr = random.Random(18492)
    for _ in range(150):
        d = wr.random() ** 1.6
        y = HORIZON + 8 + d * 1150
        x = wr.uniform(-100, W)
        ln = lerp(26, 320, d) * wr.uniform(0.4, 1.0)
        warm = abs(x + ln / 2 - SUN[0]) < lerp(260, 700, d) and y < 1700
        col = rgba(oklch(0.62, 0.10, 65), wr.uniform(0.05, 0.16)) if warm else \
            rgba(TIDE, wr.uniform(0.03, 0.10))
        pg.line([x, y], [x + ln, y + wr.uniform(-1.5, 1.5)],
                **st(lerp(1.0, 2.6, d), col), decorative=True)

    # the barrier — pier far first (right), near last (left)
    for i in range(8, -1, -1):
        x, y, k = module_xy(i)
        closed = i in (3, 4)
        moving = i == 6
        # gate leaf spans toward the next module (drawn before its piers)
        if (closed or moving) and i < 8:
            x2, y2, k2 = module_xy(i + 1)
            top = 17.0 * k if closed else 6.5 * k
            top2 = 17.0 * k2 if closed else 6.5 * k2
            pw = 6.0
            xa, xb = x + pw * k, x2 - pw * k2
            # curved crest: sampled quadratic sag between pier tops
            crest = []
            base = []
            for s_ in range(0, 13):
                u = s_ / 12.0
                cx = lerp(xa, xb, u)
                sag = math.sin(math.pi * u) * 0.055
                crest.append([cx, lerp(y - top, y2 - top2, u) + sag * (top + top2) / 2])
                base.append([cx, lerp(y + 2 * k, y2 + 2 * k2, u)])
            pg.polygon(crest + base[::-1], fill=grad([
                (0, STEEL_LIT if closed else rgba(STEEL_LIT, 0.9)),
                (58, STEEL), (100, oklch(0.30, 0.075, 42))]), **dec)
            # rib lines on the leaf
            for s_ in range(1, 12):
                u = s_ / 12.0
                pg.line([crest[s_][0], crest[s_][1] + 3],
                        [base[s_][0], base[s_][1] - 1],
                        **st(max(1.0, 0.55 * k), rgba("#000000", 0.18)), decorative=True)
            # crest highlight
            pg.polyline(crest, fill="none",
                        **st(max(1.2, 0.5 * k), rgba(oklch(0.75, 0.14, 55), 0.75)),
                        decorative=True)
            # reflection — §6 water: displaced by seeded streak turbulence
            pg.polygon([[xa, y + 2 * k], [xb, y2 + 2 * k2],
                        [xb, y2 + 2 * k2 + top2 * 0.8], [xa, y + 2 * k + top * 0.8]],
                       fill=grad([(0, rgba(STEEL, 0.34)), (100, rgba(STEEL, 0.0))]),
                       decorative=True, **wobble(max(6.0, 4.5 * k)))
        # pier
        pw, ph = 6.0 * k, 17.6 * k
        lit = 1.9 * k
        pg.polygon([[x - pw, y + 2.2 * k], [x - pw, y - ph + 1.2 * k], [x - pw * 0.62, y - ph],
                    [x + pw * 0.62, y - ph], [x + pw, y - ph + 1.2 * k], [x + pw, y + 2.2 * k]],
                   fill=CONC, **dec)
        pg.polygon([[x + pw - lit, y + 2.2 * k], [x + pw - lit, y - ph + 1.1 * k],
                    [x + pw * 0.62, y - ph], [x + pw, y - ph + 1.2 * k], [x + pw, y + 2.2 * k]],
                   fill=rgba(CONC_LIT, 0.85), **dec)
        # machinery house + beacon
        hw, hh = 3.4 * k, 3.2 * k
        pg.rect([x - hw, y - ph - hh, 2 * hw, hh], fill=oklch(0.40, 0.03, 250), **dec)
        pg.rect([x + hw - 1.2 * k, y - ph - hh, 1.2 * k, hh], fill=rgba(CONC_LIT, 0.7), **dec)
        by = y - ph - hh - 1.1 * k
        pg.ellipse([x, by], 2.2 * k, 2.2 * k, fill=rgba(SIGNAL, 0.16), **dec)
        pg.ellipse([x, by], 0.75 * k, 0.75 * k, fill=SIGNAL, **dec)
        # pier reflection — displaced like the leaf reflections
        pg.polygon([[x - pw, y + 2.2 * k], [x + pw, y + 2.2 * k],
                    [x + pw * 0.8, y + 2.2 * k + ph * 0.55], [x - pw * 0.8, y + 2.2 * k + ph * 0.55]],
                   fill=grad([(0, rgba(CONC, 0.40)), (100, rgba(CONC, 0.0))]),
                   decorative=True, **wobble(max(5.0, 3.5 * k), seed=18497 + i))

    # mist band over the far water — §8 fog, now genuinely soft
    pg.rect([900, HORIZON - 14, 2000, 130], fill=grad([
        (0, rgba(INK2, 0.0)), (45, rgba(INK2, 0.09)), (100, rgba(INK2, 0.0))]),
            decorative=True, **style_effects(filter=filter_chain(blur_filter("16px"))))


def scrims(pg):
    dec = {"decorative": True}
    pg.rect([0, 0, W, 620], fill=grad([(0, rgba(PAPER, 0.86)), (55, rgba(PAPER, 0.42)),
                                       (100, rgba(PAPER, 0.0))]), **dec)
    pg.rect([0, 0, 1180, H], fill=grad([(0, rgba(PAPER, 0.92)), (55, rgba(PAPER, 0.55)),
                                        (100, rgba(PAPER, 0.0))], angle=90), **dec)
    pg.rect([0, 1360, W, 800], fill=grad([(0, rgba(PAPER, 0.0)), (52, rgba(PAPER, 0.55)),
                                          (100, rgba(PAPER, 0.82))]), **dec)
    pg.rect([2560, 0, 1280, H], fill=grad([(0, rgba(PAPER, 0.0)), (100, rgba(PAPER, 0.45))],
                                          angle=90), **dec)
    pg.rect([0, 0, W, H], fill=rgrad([(0, rgba(PAPER, 0.0)), (58, rgba(PAPER, 0.0)),
                                      (100, rgba(PAPER, 0.30))]),
            decorative=True, **style_effects(mix_blend_mode="multiply"))


# --------------------------------------------------------------------------- #
# §16 · Editorial — masthead, standfirst, essay (baseline-locked columns),
# archival figure, footnotes, colophon.
# --------------------------------------------------------------------------- #
ESSAY_1 = ("he Alder was engineered long before it was understood. Wharves "
           "narrowed its mouth, dredgers deepened its bed, and each intervention "
           "invited the sea a little further upstream. The Meridian Barrier is "
           "the estuary's reply: nine sector gates resting on the riverbed, "
           "invisible to shipping until they are needed, then rotating up "
           "through the water to stand as a steel cliff against the tide.")
ESSAY_2 = ("On the night of 28 February the barrier closed in anger for the "
           f"eighth time in five years. A deepening low over the North Sea drove "
           f"a surge of {SURGE_AMP:.1f} metres onto a spring tide¹; water at "
           f"the mouth reached {PEAK_V:.2f} metres above datum, seventy "
           "centimetres over the town's defended level. Behind the gates, the "
           "river rose only as far as its own patience allowed.")
ESSAY_3 = ("This plate documents that closure as a single system: the geometry "
           "of the gates, the bathymetry that shapes the surge, the record of "
           "levels, and the console through which the decision was "
           "taken². Every figure is generated from one model and one seed; "
           "nothing here is illustrative only.")


def masthead(pg):
    pg.text([MX, 122, 2400, 32],
            "ALDER TIDAL DEFENCE · TECHNICAL PLATE 04 · SPRING SURGE PROVING",
            style=sty("kicker"))
    pg.text([MX, 170, 2500, 170], "THE ESTUARY WORKS", style=sty("display"))
    for i, ln in enumerate(("PLATE 04 / 12", "SURVEY 2026-02-28",
                            "DATUM ODN · GRID LOCAL-M", "MODEL ALDER-V12 · SEED 1849")):
        pg.text([2614, 140 + i * 32, 1098, 30], ln, style=sty("data", align="right"))
    pg.text([MX, 358, 1972, 112],
            "Nine gates, one tide: how a river learns to close its own door.",
            style=sty("stand"))
    pg.line([MX, Y_RULE], [W - MX, Y_RULE], **st(1, LINE_A, cap="butt"))


def essay(pg):
    x1, x2, wcol = 128, 580, 420
    y0, max_lines, sz = Y_CONTENT, 23, 27
    ind = 116
    pg.text([x1 - 4, y0 - 26, 160, 160], "T",
            style=ts(150, SIGNAL, family=SERIF, weight=700))
    lines = []
    narrow = wrap_text(ESSAY_1, width=wcol - ind, font_family="Charis SIL", font_size=sz)
    lines += [(t, ind) for t in narrow[:3]]
    lines += [(t, 0) for t in wrap_text(" ".join(narrow[3:]), width=wcol,
                                        font_family="Charis SIL", font_size=sz)]
    for para in (ESSAY_2, ESSAY_3):
        lines.append(("", 0))
        lines += [(t, 0) for t in wrap_text(para, width=wcol,
                                            font_family="Charis SIL", font_size=sz)]
    for n, (txt, indent) in enumerate(lines):
        col, row = divmod(n, max_lines)
        if col > 1:
            break
        if txt:
            x = (x1 if col == 0 else x2) + indent
            pg.text([x, y0 + row * BASE, wcol - indent, 36], txt, style=sty("body"))
    return len(lines)


def archival(pg):
    """Fig. 2 — press-plate duotone of the pier-4 cofferdam (drawn, §10 adapted)."""
    x, y, w, h = 128, 1320, 872, 440
    DK, LT = oklch(0.24, 0.05, 250), oklch(0.94, 0.02, 95)
    MIDT = oklch(0.62, 0.035, 235)
    dec = {"decorative": True}
    pg.rect([x, y, w, h], fill=grad([(0, LT), (58, oklch(0.86, 0.025, 100)),
                                     (100, oklch(0.78, 0.03, 105))]), **dec)
    # sky hatch band
    pg.rect([x, y, w, 128], fill=hatch(fg=rgba(DK, 0.14), scale=5, angle=0), **dec)
    # water: horizontal broken strokes
    ar = random.Random(18499)
    for _ in range(90):
        yy = y + 150 + ar.random() ** 1.3 * (h - 170)
        xx = x + ar.uniform(8, w - 130)
        pg.line([xx, yy], [xx + ar.uniform(30, 120), yy],
                **st(1.6, rgba(DK, ar.uniform(0.18, 0.42)), cap="butt"), decorative=True)
    # cofferdam ring — 64 sheet piles around an ellipse in perspective
    cx, cy, rx, ry = x + 400, y + 268, 250, 96
    pg.ellipse([cx, cy], rx + 7, ry + 5, fill=rgba(LT, 0.85), stroke=DK,
               stroke_style={"stroke_width": 2}, decorative=True)
    pg.ellipse([cx, cy], rx - 12, ry - 8, fill=oklch(0.70, 0.03, 230),
               stroke=DK, stroke_style={"stroke_width": 1.4}, decorative=True)
    for i in range(64):
        a = 2 * math.pi * i / 64
        ca, sa = math.cos(a), math.sin(a)
        pg.line([cx + ca * (rx - 12), cy + sa * (ry - 8)],
                [cx + ca * (rx + 7), cy + sa * (ry + 5)],
                **st(2.2, DK, cap="butt"), decorative=True)
        if sa > -0.2:  # pile heads on the near rim
            pg.line([cx + ca * (rx + 7), cy + sa * (ry + 5)],
                    [cx + ca * (rx + 7), cy + sa * (ry + 5) - 14],
                    **st(2.2, DK, cap="butt"), decorative=True)
    # pier stub + crane inside
    pg.rect([cx - 52, cy - 34, 104, 60], fill=rgba(DK, 0.85), **dec)
    pg.rect([cx - 36, cy - 48, 72, 16], fill=rgba(DK, 0.65), **dec)
    pg.line([cx + 120, cy + 6], [cx + 120, cy - 118], **st(3, DK, cap="butt"), decorative=True)
    pg.line([cx + 120, cy - 118], [cx + 210, cy - 66], **st(2.2, DK), decorative=True)
    pg.line([cx + 210, cy - 66], [cx + 210, cy - 20], **st(1.4, DK), decorative=True)
    # attendant barge, far right
    pg.polygon([[x + 700, y + 176], [x + 800, y + 176], [x + 786, y + 196], [x + 712, y + 196]],
               fill=rgba(DK, 0.8), **dec)
    pg.rect([x + 726, y + 160, 30, 16], fill=rgba(DK, 0.8), **dec)
    # halftone screen + press grain (§10) + duotone mid-wash + plate border
    pg.rect([x, y, w, h], fill=dots(fg=rgba(DK, 0.10), scale=4.6), **dec)
    pg.rect([x, y, w, h], fill=LT, opacity=0.16, decorative=True,
            **style_effects(filter=film_grain(18499, freq=0.5), mix_blend_mode="multiply"))
    pg.rect([x, y, w, h], fill=rgba(MIDT, 0.08), **dec)
    pg.rect([x + 0.5, y + 0.5, w - 1, h - 1], fill="none", stroke=rgba(DK, 0.6),
            stroke_style={"stroke_width": 1}, decorative=True)
    pg.text([x, y + h + 24, w, 56],
            "Fig. 2 — Pier 4 cofferdam during construction, rendered from the "
            "survey model; press-plate reproduction.", style=sty("caption"))


def footnotes(pg):
    x, y, w = 128, 1848, 872
    pg.line([x, y - 2], [x + w, y - 2], **st(1, LINE_A, cap="butt"))
    pg.text([x, y + 10, w, 24],
            "1  Surge residual measured against the 1987–2016 harmonic epoch.",
            style=sty("foot"))
    pg.text([x, y + 38, w, 24],
            "2  Console shown in proving mode; live telemetry replaced by the survey dataset.",
            style=sty("foot"))


def colophon(pg):
    pg.text([MX, Y_COLO + 4, W - 2 * MX, 32],
            "ESTUARY WORKS · PLATE 04 · MODEL ALDER-V12 · SEED 1849 · SRGB / D65 "
            "· FIRA SANS & CHARIS SIL · CC BY-NC 4.0 · SHA-256 IN MANIFEST · "
            "STUDIO ALDER 2026",
            style=sty("chip", color=INK3))


# --------------------------------------------------------------------------- #
# §15 · Section at pier 4 — world metres → page px, cut styling per the plan.
# --------------------------------------------------------------------------- #
SEC = (1032, 1464, 1550, 352)


def sx(wx):
    return SEC[0] + (wx + 70.0) * (SEC[2] / 140.0)


def sy(wy):
    return SEC[1] + (30.0 - wy) * (SEC[3] / 50.0)


def w2p(pts):
    return [[sx(a), sy(b)] for a, b in pts]


BED = [(-70, -8), (-40, -9), (-25, -10.5), (-16, -13), (-8, -14), (8, -14),
       (16, -13), (25, -11), (40, -9.5), (70, -9)]


def section(pg):
    x0, y0, w0, h0 = SEC
    pg.text([x0, 1416, w0, 32], "SECTION AT PIER 4 · LOOKING SEAWARD", style=sty("label"))
    CUT_FILL = rgba(SILT, 0.25)
    CUT = {"stroke": INK, "stroke_style": {"stroke_width": 1.5, "stroke_linejoin": "round"}}

    # water — sea (left, +2.40) held back by the leaf; basin (right, +0.90)
    sea = [(-70, 2.4), (-16.2, 2.4), (-14.8, -4), (-11, -10), (-8, -13.9),
           (-16, -13), (-25, -10.5), (-40, -9), (-70, -8)]
    basin = [(6, 0.9), (70, 0.9), (70, -9), (40, -9.5), (25, -11), (16, -13), (8, -14), (6, -14)]
    pg.polygon(w2p(sea), fill=rgba(TIDE, 0.13), decorative=True)
    pg.polygon(w2p(basin), fill=rgba(TIDE, 0.10), decorative=True)
    pg.line([sx(-70), sy(2.4)], [sx(-16.2), sy(2.4)], **st(1.5, TIDE, dash=[6, 4], cap="butt"))
    pg.line([sx(8), sy(0.9)], [sx(70), sy(0.9)], **st(1.5, TIDE, dash=[6, 4], cap="butt"))
    pg.text([sx(-68), sy(2.4) - 30, 300, 24], "TIDE +2.40", style=sty("chip", color=TIDE))
    pg.text([sx(46), sy(0.9) - 30, 300, 24], "BASIN +0.90", style=sty("chip", color=TIDE))

    # bed + silt mass
    silt_poly = BED + [(70, -20), (-70, -20)]
    pg.polygon(w2p(silt_poly), fill=rgba(SILT, 0.20), decorative=True)
    pg.polygon(w2p(silt_poly), fill=hatch(fg=rgba(SILT, 0.28), scale=7, angle=45), decorative=True)
    pg.polyline(w2p(BED), fill="none", **CUT)

    # scour aprons + sill beam
    pg.polygon(w2p([(-17, -12.9), (-8, -13.6), (-8, -14.3), (-17, -13.9)]), fill=CUT_FILL, **CUT)
    pg.polygon(w2p([(17, -12.0), (8, -13.6), (8, -14.3), (17, -13.0)]), fill=CUT_FILL, **CUT)
    pg.polygon(w2p([(-8, -12.4), (8, -12.4), (8, -14), (-8, -14)]),
               fill=rgba(SILT, 0.42), **CUT)

    # caisson pier (the §5 profile) + ballast chamber + machinery gallery
    pier = [(-6, -14), (6, -14), (6, 16), (3.4, 20), (-3.4, 20), (-6, 16)]
    pg.polygon(w2p(pier), fill=CUT_FILL, **CUT)
    pg.polygon(w2p([(-4.6, 0), (4.6, 0), (4.6, -12), (-4.6, -12)]),
               fill=hatch(fg=rgba(TIDE, 0.30), scale=6, angle=0),
               stroke=rgba(INK, 0.8), stroke_style={"stroke_width": 1})
    pg.polygon(w2p([(-3, 16.4), (3, 16.4), (3, 19.4), (-3, 19.4)]),
               fill=rgba(PAPER, 0.55), stroke=rgba(INK, 0.8),
               stroke_style={"stroke_width": 1})

    # sector-gate leaf — skin arc about the trunnion (0, 4), r 15.2–16.4
    def arcpts(r, a0, a1, n=26):
        return [(r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                 4 + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    skin = arcpts(16.4, 96, 196) + arcpts(15.2, 196, 96)
    pg.polygon(w2p(skin), fill=grad([(0, STEEL_LIT), (100, STEEL)], angle=200), **CUT)
    for a in (112, 150, 188):
        pg.line([sx(0), sy(4)], [sx(15.2 * math.cos(math.radians(a))),
                                 sy(4 + 15.2 * math.sin(math.radians(a)))],
                **st(2.2, rgba(STEEL_LIT, 0.9)))
    pg.ellipse([sx(0), sy(4)], 14, 14, fill=STEEL_LIT, **CUT)
    pg.ellipse([sx(0), sy(4)], 4.5, 4.5, fill=INK)

    # datum ticks along the bottom edge
    for wx in range(-60, 61, 20):
        pg.line([sx(wx), y0 + h0], [sx(wx), y0 + h0 - 8], **st(1, LINE_A, cap="butt"))
        pg.text([sx(wx) - 40, y0 + h0 + 6, 80, 22], f"{wx:+d} m" if wx else "0",
                style=sty("chip", color=INK3, align="center", letter_spacing=0.5))


CALLOUTS = [
    (1, "left", 1548, (-9.0, 15.0), "Sector-gate leaf · 46 m span"),
    (5, "left", 1496, (-1.5, 18.0), "Machinery gallery"),
    (3, "left", 1716, (-2.0, -6.0), "Caisson ballast chamber"),
    (2, "right", 1608, (1.6, 4.6), "Trunnion bearing · rotation axis"),
    (4, "right", 1776, (10.0, -13.2), "Sill beam and scour apron"),
]


def callouts(pg):
    for n, side, cy, (wx, wy), text in CALLOUTS:
        ax, ay = sx(wx), sy(wy)
        if side == "left":
            chip_x = 1058
            pg.polyline([[chip_x + 20, cy], [ax, cy], [ax, ay]], fill="none",
                        **st(1.5, LINE_A))
            pg.ellipse([ax, ay], 4, 4, fill=LINE_A)
            num_chip(pg, chip_x, cy, n)
            pg.text([chip_x + 30, cy - 13, 250, 56], text, style=sty("caption"))
        else:
            chip_x = 2556
            pg.polyline([[chip_x - 20, cy], [ax, cy], [ax, ay]], fill="none",
                        **st(1.5, LINE_A))
            pg.ellipse([ax, ay], 4, 4, fill=LINE_A)
            num_chip(pg, chip_x, cy, n)
            pg.text([chip_x - 30 - 280, cy - 13, 280, 56], text,
                    style=sty("caption", align="right"))


def hero_annotations(pg):
    """§9 anchors — leaders from scene features to floating captions."""
    # Gate 4 leaf (module index 3 → leaf toward module 4)
    x3, y3, k3 = module_xy(3)
    gx, gy = x3 + 90, y3 - 17.0 * k3 + 26
    pg.polyline([[gx, gy], [gx, 1194], [1596, 1194]], fill="none", **st(1.5, LINE_A))
    pg.ellipse([gx, gy], 4.5, 4.5, fill=SIGNAL)
    gate_glyph(pg, 1236, 1198, 22, SIGNAL)
    pg.text([1262, 1180, 330, 28], "Gate 4 · closed for proving test", style=sty("caption"))
    # Navigation beacon on module 2's pier
    x2, y2, k2 = module_xy(2)
    bx, by = x2, y2 - 21.9 * k2
    pg.polyline([[bx, by], [bx, 1108], [1692, 1108]], fill="none", **st(1.5, LINE_A))
    pg.ellipse([bx, by], 4.5, 4.5, fill=SIGNAL)
    pg.text([1700, 1094, 400, 28], "Navigation beacon · Fl(2) 6 s", style=sty("caption"))


# --------------------------------------------------------------------------- #
# §13 · Cartography — flood-extent map in the top rail panel.
# Local-m extent: x ∈ [-1600, 1600], z ∈ [-744, 744]  →  1050×488 body.
# --------------------------------------------------------------------------- #
LAND_N = [(-1600, -744), (-1600, -190), (-880, -165), (-330, -120), (180, -140),
          (820, -70), (1600, 30), (1600, -744)]
LAND_S = [(-1600, 744), (-1600, 95), (-760, 120), (-140, 190), (420, 150),
          (1010, 240), (1600, 330), (1600, 744)]
FLOOD_A = [(-700, 140), (-460, 320), (-80, 300), (220, 360), (440, 190), (-120, 210)]
FLOOD_B = [(-820, 130), (-560, 420), (-60, 400), (300, 470), (560, 220), (-140, 230)]
THALWEG = [(-1600, -140), (-820, -60), (-260, 20), (300, -10), (900, 90), (1600, 210)]


def offset_polyline(pts, d):
    """Points offset perpendicular to the local tangent by d (map metres)."""
    out = []
    n = len(pts)
    for i, (x, z) in enumerate(pts):
        x0, z0 = pts[max(0, i - 1)]
        x1, z1 = pts[min(n - 1, i + 1)]
        tx, tz = x1 - x0, z1 - z0
        ln = math.hypot(tx, tz) or 1.0
        out.append((x - tz / ln * d, z + tx / ln * d))
    return out


def map_panel(pg):
    bx, by, bw, bh = panel(pg, COL_R[0], 536, COL_R[1], 576, "ESTUARY · FLOOD EXTENT")
    sxm, sym = bw / 3200.0, bh / 1488.0

    def mx(x):
        return bx + (x + 1600) * sxm

    def my(z):
        return by + (z + 744) * sym

    def mpts(pts):
        return [[mx(a), my(b)] for a, b in pts]

    pg.rect([bx, by, bw, bh], radius=12, fill=oklch(0.23, 0.035, 235),
            stroke=LINE_A, stroke_style={"stroke_width": 1})
    # graticule (500 m)
    for gx in range(-1500, 1501, 500):
        pg.line([mx(gx), by + 1], [mx(gx), by + bh - 1], **st(1, GRID_A, cap="butt"))
    for gz in (-500, 0, 500):
        pg.line([bx + 1, my(gz)], [bx + bw - 1, my(gz)], **st(1, GRID_A, cap="butt"))
    for gx in (-1000, 0, 1000):
        pg.text([mx(gx) - 60, by + 8, 120, 20], f"{gx:+d}" if gx else "0",
                style=ts(15, rgba(INK3, 0.8), family=MONO, align="center", letter_spacing=0.5))
    # depth contours around the thalweg (under the land masses)
    for d, op in ((70, 0.50), (145, 0.38), (230, 0.27), (330, 0.18)):
        for sgn in (1, -1):
            pg.polyline(mpts(offset_polyline(THALWEG, sgn * d)), smooth=True,
                        fill="none", **st(1, rgba(TIDE, op), cap="butt"), decorative=True)
    # land
    pg.polygon(mpts(LAND_N), fill=oklch(0.28, 0.03, 80), decorative=True)
    pg.polygon(mpts(LAND_S), fill=oklch(0.28, 0.03, 80), decorative=True)
    # intertidal hatch bands along both shorelines
    edge_n = [(-1600, -190), (-880, -165), (-330, -120), (180, -140), (820, -70), (1600, 30)]
    edge_s = [(-1600, 95), (-760, 120), (-140, 190), (420, 150), (1010, 240), (1600, 330)]
    band_n = edge_n + offset_polyline(edge_n, 60)[::-1]
    band_s = edge_s + offset_polyline(edge_s, -60)[::-1]
    for band in (band_n, band_s):
        pg.polygon(mpts(band), fill=hatch(fg=rgba(SILT, 0.40), scale=5, angle=45),
                   decorative=True)
    # navigation channel
    pg.polyline(mpts(THALWEG), smooth=True, fill="none",
                **st(1.5, INK3, dash=[10, 6], cap="butt"))
    # flood extents — 1-in-200 beneath 1-in-20
    pg.polygon(mpts(FLOOD_B), fill=rgba(SIGNAL, 0.26), stroke=SIGNAL,
               stroke_style={"stroke_width": 1, "stroke_dasharray": [4, 4]})
    pg.polygon(mpts(FLOOD_A), fill=rgba(SIGNAL, 0.14))
    # the barrier — nine gate symbols on the axis
    pg.line([mx(0), my(-230)], [mx(0), my(230)], **st(1.5, rgba(SIGNAL, 0.5), cap="butt"))
    for i in range(9):
        z = -208 + i * 52
        gate_glyph(pg, mx(0), my(z) + 5, 17, SIGNAL, w=2.2)
    # hero-camera frustum
    cxp, czp = mx(-620), my(470)
    ang = math.atan2(-30 - 470, 40 - (-620))
    half = math.radians(27.3)
    rng = 720 * sxm
    e1 = [cxp + rng * math.cos(ang - half), czp + rng * math.sin(ang - half)]
    e2 = [cxp + rng * math.cos(ang + half), czp + rng * math.sin(ang + half)]
    pg.polygon([[cxp, czp], e1, e2], fill=rgba(TIDE, 0.05), stroke=rgba(TIDE, 0.40),
               stroke_style={"stroke_width": 1, "stroke_dasharray": [6, 4]})
    pg.ellipse([cxp, czp], 4, 4, fill=TIDE)
    # labels
    halo = [{"offset_x": 0, "offset_y": 0, "blur": 8, "color": PAPER}]
    pg.text([mx(-1250), my(-20) - 14, 420, 28], "RIVER ALDER",
            style=sty("label", text_shadow=halo))
    pg.line([mx(0), my(-100)], [mx(70), my(-262)], **st(1, LINE_A, cap="butt"))
    pg.text([mx(70) - 30, my(-300) - 24, 420, 28], "MERIDIAN BARRIER",
            style=sty("label", text_shadow=halo))
    # scale bar (bl)
    sb_x, sb_y = bx + 24, by + bh - 46
    for x0m, x1m, filled in ((0, 250, True), (250, 500, False), (500, 1000, True)):
        pg.rect([sb_x + x0m * sxm, sb_y, (x1m - x0m) * sxm, 7],
                fill=INK2 if filled else "none", stroke=INK2,
                stroke_style={"stroke_width": 1})
    for m, lab in ((0, "0"), (500, "500"), (1000, "1 000 m")):
        pg.text([sb_x + m * sxm - 40, sb_y + 12, 110, 20], lab,
                style=ts(15, INK3, family=MONO, align="left" if m == 1000 else "center"))
    # north (tr)
    nx, ny = bx + bw - 40, by + 44
    pg.polygon([[nx, ny - 20], [nx - 9, ny + 12], [nx, ny + 4], [nx + 9, ny + 12]],
               fill=INK2)
    pg.text([nx - 20, ny + 16, 40, 20], "N",
            style=ts(15, INK2, family=SANS_SB, weight=600, align="center"))
    # legend (br)
    lg_x, lg_y, lg_w, lg_h = bx + bw - 320, by + bh - 130, 296, 106
    pg.rect([lg_x, lg_y, lg_w, lg_h], radius=8, fill=rgba(PAPER, 0.66),
            stroke=LINE_A, stroke_style={"stroke_width": 1})
    rows = [("swatch", rgba(SIGNAL, 0.14), "1-IN-20 EXTENT"),
            ("swatch", rgba(SIGNAL, 0.26), "1-IN-200 EXTENT"),
            ("gate", SIGNAL, "GATE MODULE")]
    for i, (kind, c, lab) in enumerate(rows):
        ry = lg_y + 16 + i * 30
        if kind == "swatch":
            pg.rect([lg_x + 16, ry, 26, 16], fill=c, stroke=rgba(SIGNAL, 0.5),
                    stroke_style={"stroke_width": 1})
        else:
            gate_glyph(pg, lg_x + 29, ry + 13, 18, SIGNAL, w=1.8)
        pg.text([lg_x + 56, ry - 3, lg_w - 64, 22], lab, style=ts(15, INK2, family=MONO_MD, weight=500, ls=0.8))


# --------------------------------------------------------------------------- #
# §14 · Water-level chart + §17 scrubber
# --------------------------------------------------------------------------- #
X_TICKS = [(0, "27 FEB"), (12, "12:00"), (24, "28 FEB"), (36, "12:00"),
           (48, "01 MAR"), (60, "12:00"), (72, "02 MAR")]


def tide_chart(pg):
    bx, by, bw, bh = panel(pg, COL_R[0], 1144, COL_R[1], 320, "WATER LEVEL · ALDER MOUTH")
    px0, px1 = bx + 52, bx + bw - 6
    py0, py1 = by + 8, by + bh - 30
    VMIN, VMAX = -3.5, 6.2

    def cx(t):
        return px0 + (t / 72.0) * (px1 - px0)

    def cy(v):
        return py1 - (v - VMIN) / (VMAX - VMIN) * (py1 - py0)

    for v in (-2, 0, 2, 4):
        pg.line([px0, cy(v)], [px1, cy(v)], **st(1, GRID_A, cap="butt"))
        pg.text([bx, cy(v) - 10, 44, 20], f"{v:+d}" if v else "0",
                style=ts(15, INK3, family=MONO, align="right"))
    for t, lab in X_TICKS:
        pg.line([cx(t), py1], [cx(t), py1 + 6], **st(1, LINE_A, cap="butt"))
        pg.text([cx(t) - 50, py1 + 10, 100, 20], lab,
                style=ts(15, INK3, family=MONO, align="center"))
    pg.line([px0, py1], [px1, py1], **st(1, LINE_A, cap="butt"))
    pg.text([bx, py0 - 6, 120, 20], "M ODN", style=ts(15, INK3, family=MONO_MD, ls=1))

    # defence level rule
    pg.line([px0, cy(DEFENCE)], [px1, cy(DEFENCE)], **st(1.5, SIGNAL, dash=[8, 5], cap="butt"))
    pg.text([px0 + 12, cy(DEFENCE) - 24, 300, 20], f"DEFENCE {DEFENCE:.2f}",
            style=ts(15, SIGNAL, family=MONO_MD, ls=0.8))

    # series
    pred_pts = [[cx(t), cy(v)] for t, v in zip(TS_H[::3], _PRED[::3])]
    obs_pts = [[cx(t), cy(v)] for t, v in zip(TS_H[::2], _OBS[::2])]
    pg.polyline(pred_pts, fill="none", **st(1.5, INK3, dash=[3, 5], cap="butt"))
    pg.polyline(obs_pts, fill="none", **st(3, TIDE, cap="round"))

    # closure annotation — flagged at the decision time, tied to the curve
    mx_ = cx(T_PEAK)
    v_at = _SMOOTH[int(round(T_PEAK / T_STEP))]
    pg.line([mx_, cy(v_at) - 4], [mx_, py0 + 24], **st(1, rgba(SIGNAL, 0.6), cap="butt"))
    gate_glyph(pg, mx_, py0 + 22, 16, SIGNAL)
    pg.text([px1 - 346, py0 + 2, 340, 20], CLOSURE_LABEL.upper(),
            style=ts(15, SIGNAL, family=MONO_MD, align="right", letter_spacing=0.6))

    # legend — one row in the panel's title band (clear of the plot)
    ly = by - 34
    lx = bx + bw - 296
    pg.line([lx, ly], [lx + 28, ly], **st(1.5, INK3, dash=[3, 5], cap="butt"))
    pg.text([lx + 36, ly - 10, 110, 20], "PREDICTED",
            style=ts(15, INK2, family=MONO, letter_spacing=0.8))
    pg.line([lx + 148, ly], [lx + 176, ly], **st(3, TIDE))
    pg.text([lx + 184, ly - 10, 110, 20], "OBSERVED",
            style=ts(15, INK2, family=MONO, letter_spacing=0.8))


def scrubber(pg):
    x0, y0, w0 = 1032, 1856, 1550
    axis_y = y0 + 40

    def xs(t):
        return x0 + (t / 72.0) * w0

    # exceedance region (the closure)
    pg.rect([xs(CLOSE_T0), y0 + 12, xs(CLOSE_T1) - xs(CLOSE_T0), axis_y - y0 - 12],
            fill=rgba(SIGNAL, 0.20))
    pg.line([x0, axis_y], [x0 + w0, axis_y], **st(1.5, LINE_A, cap="butt"))
    for t, lab in X_TICKS:
        pg.line([xs(t), axis_y], [xs(t), axis_y - 8], **st(1, LINE_A, cap="butt"))
        align = "left" if t == 0 else ("right" if t == 72 else "center")
        off = 0 if t == 0 else (-100 if t == 72 else -50)
        pg.text([xs(t) + off, axis_y + 8, 100, 20], lab,
                style=ts(15, INK3, family=MONO, align=align))
    # playhead
    phx = xs(T_PEAK)
    pg.line([phx, y0 + 2], [phx, axis_y + 4], **st(2, SIGNAL, cap="butt"))
    pg.ellipse([phx, y0 + 4], 9, 9, fill=SIGNAL)
    pg.ellipse([phx, y0 + 4], 3, 3, fill=PAPER)
    pg.text([phx + 18, y0 - 4, 340, 20], "2026-02-28 T 03:40 Z",
            style=ts(15, SIGNAL, family=MONO_MD, ls=0.8))


# --------------------------------------------------------------------------- #
# §11–§12 · Ops console + exploded gate module
# --------------------------------------------------------------------------- #
def mixc(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def status_chip(pg, x, y, label, tone):
    tw = measure_text(label, font_family="Fira Mono Medium", font_size=19)
    w = 14 + 10 + 8 + tw + 16
    pg.rect([x, y, w, 36], radius=18, fill=rgba(tone, 0.16), stroke=rgba(tone, 0.5),
            stroke_style={"stroke_width": 1})
    pg.ellipse([x + 19, y + 18], 5, 5, fill=tone)
    pg.text([x + 32, y + 7, tw + 12, 24], label, style=ts(19, tone, family=MONO_MD, weight=500, ls=1.15))
    return w


def mini_btn(pg, x, y, w, h, label, variant, state, fsize=15):
    op = 0.38 if state == "disabled" else None
    dy = 1 if state == "pressed" else 0
    if variant == "primary":
        fill = {"default": SIGNAL, "hover": mixc(SIGNAL, "#FFFFFF", 0.08),
                "pressed": mixc(SIGNAL, "#000000", 0.10), "focus": SIGNAL,
                "disabled": SIGNAL}[state]
        pg.rect([x, y + dy, w, h], radius=6, fill=fill, opacity=op)
        tcol = PAPER
    else:
        fill = rgba(LINE, 0.08) if state == "hover" else "none"
        pg.rect([x, y + dy, w, h], radius=6, fill=fill, stroke=LINE_A,
                stroke_style={"stroke_width": 1}, opacity=op)
        tcol = INK
    if state == "focus":
        pg.rect([x - 3, y - 3, w + 6, h + 6], radius=9, fill="none", stroke=TIDE,
                stroke_style={"stroke_width": 2})
    pg.text([x, y + dy + h / 2 - fsize * 0.7, w, fsize * 1.5], label,
            style=ts(fsize, tcol, family=SANS_SB, weight=600, align="center",
                     ls=1.4, upper=True, opacity=op))


def ops_console(pg):
    bx, by, bw, bh = panel(pg, COL_R[0], 1496, COL_R[1], 472, "BARRIER OPERATIONS · PROVING MODE")
    # row 1 — status chips
    x = bx
    for label, tone in (("GATE 4 · CLOSED", OK), ("GATE 5 · CLOSED", OK),
                        ("GATE 7 · SLOW DRIVE", WARN)):
        x += status_chip(pg, x, by, label, tone) + 12
    # row 2 — surge-watch toggle + actions
    ty_ = by + 54
    pg.rect([bx, ty_ + 12, 64, 32], radius=16, fill=TIDE)
    pg.ellipse([bx + 47, ty_ + 28], 12, 12, fill=PAPER)
    pg.text([bx + 78, ty_ + 16, 240, 24], "SURGE WATCH", style=sty("label"))
    w_open = measure_text("OPEN ALL", font_family="Fira Sans SemiBold", font_size=19) + 56
    w_close = measure_text("CLOSE REMAINING", font_family="Fira Sans SemiBold", font_size=19) + 56
    mini_btn(pg, bx + bw - w_open, ty_, w_open, 56, "Open all", "quiet", "disabled", fsize=19)
    mini_btn(pg, bx + bw - w_open - 12 - w_close, ty_, w_close, 56, "Close remaining",
             "primary", "default", fsize=19)
    # closures-per-year bars
    cy0 = by + 132
    pg.text([bx, cy0, bw, 24], "CLOSURES PER YEAR · 1987–2026", style=sty("chip"))
    base_y = cy0 + 82
    pg.line([bx, base_y], [bx + bw, base_y], **st(1, GRID_A, cap="butt"))
    for yr, n in CLOSURES:
        xb = bx + (yr - 1987) * ((bw - 12) / 39.0)
        if n > 0:
            hgt = n * 16
            pg.rect([xb, base_y - hgt, 10, hgt], radius=2,
                    fill=SIGNAL if yr == 2026 else TIDE)
        else:
            pg.rect([xb, base_y - 3, 10, 3], radius=1, fill=rgba(TIDE, 0.35))
    for yr in (1987, 1999, 2011, 2023):
        xb = bx + (yr - 1987) * ((bw - 12) / 39.0)
        pg.text([xb - 40, base_y + 6, 90, 20], str(yr),
                style=ts(15, INK3, family=MONO, align="center"))
    # control-state specimen
    sp0 = by + 252
    pg.text([bx, sp0, bw, 24], "CONTROL STATES", style=sty("chip"))
    states = ["default", "hover", "pressed", "focus", "disabled"]
    cell = (bw - 4 * 10) / 5.0
    for i, s_ in enumerate(states):
        cxx = bx + i * (cell + 10)
        pg.text([cxx, sp0 + 26, cell, 18], s_.upper(),
                style=ts(15, INK3, family=MONO, align="center", letter_spacing=1))
        mini_btn(pg, cxx + (cell - 172) / 2, sp0 + 50, 172, 36, "Close", "primary", s_)
        mini_btn(pg, cxx + (cell - 172) / 2, sp0 + 94, 172, 36, "Open", "quiet", s_)


def exploded(pg):
    bx, by, bw, bh = panel(pg, 1936, 536, 646, 464, "GATE MODULE · EXPLODED")
    cx = bx + 222
    lab_x = bx + 452
    pg.line([cx, by + 8], [cx, by + bh - 8], **st(1, GRID_A, dash=[4, 6], cap="butt"))

    def part_label(txt, yy, anchor_x):
        pg.line([anchor_x, yy], [lab_x - 10, yy], **st(1, rgba(LINE, 0.25), dash=[2, 4], cap="butt"))
        pg.text([lab_x, yy - 9, bw - (lab_x - bx), 20], txt,
                style=ts(15, INK3, family=MONO, letter_spacing=1))

    # beacon
    pg.ellipse([cx, by + 26], 16, 16, fill=rgba(SIGNAL, 0.18))
    pg.ellipse([cx, by + 26], 8, 8, fill=SIGNAL)
    part_label("BEACON", by + 26, cx + 22)
    # machinery housing
    hy = by + 62
    pg.polygon([[cx - 55, hy], [cx - 43, hy - 12], [cx + 67, hy - 12], [cx + 55, hy]],
               fill=oklch(0.62, 0.02, 250), decorative=True)
    pg.rect([cx - 55, hy, 110, 48], fill=oklch(0.50, 0.02, 250))
    pg.rect([cx + 55, hy, 12, 48], fill=oklch(0.40, 0.02, 250))
    pg.rect([cx - 12, hy + 16, 24, 32], fill=rgba(PAPER, 0.6))
    part_label("MACHINERY HOUSE", hy + 22, cx + 70)
    # railing
    ry = by + 134
    pg.line([cx - 80, ry], [cx + 80, ry], **st(2, INK3, cap="butt"))
    for i in range(12):
        px_ = cx - 80 + i * (160 / 11.0)
        pg.line([px_, ry], [px_, ry + 14], **st(1.5, INK3, cap="butt"))
    part_label("RAILING", ry + 7, cx + 84)
    # gate leaf — curved skin bowing down, ribs across
    lc_y, r_out, r_in = by - 96.0, 340.0, 318.0
    a0, a1 = 230, 310

    def arc(r, aa, bb, n=26):
        return [[cx + r * math.cos(math.radians(aa + (bb - aa) * i / n)),
                 lc_y - r * math.sin(math.radians(aa + (bb - aa) * i / n))] for i in range(n + 1)]
    skin = arc(r_out, a0, a1) + arc(r_in, a1, a0)
    pg.polygon(skin, fill=grad([(0, STEEL_LIT), (100, STEEL)], angle=180),
               stroke=INK, stroke_style={"stroke_width": 1.5})
    for i in range(1, 11):
        aa = math.radians(a0 + (a1 - a0) * i / 11.0)
        pg.line([cx + r_in * math.cos(aa), lc_y - r_in * math.sin(aa)],
                [cx + r_out * math.cos(aa), lc_y - r_out * math.sin(aa)],
                **st(1.5, rgba("#000000", 0.25), cap="butt"))
    part_label("GATE LEAF", by + 196, cx + 172)
    # trunnion axis
    ta = by + 268
    pg.line([cx - 160, ta], [cx + 160, ta], **st(3, rgba(STEEL_LIT, 0.9), cap="butt"))
    pg.ellipse([cx - 160, ta], 8, 8, fill=STEEL_LIT, stroke=INK, stroke_style={"stroke_width": 1})
    pg.ellipse([cx + 160, ta], 8, 8, fill=STEEL_LIT, stroke=INK, stroke_style={"stroke_width": 1})
    part_label("TRUNNION AXIS", ta, cx + 168)
    # pier
    py_ = by + 296
    pier = [[cx - 92, py_ + 78], [cx - 92, py_ + 18], [cx - 58, py_], [cx + 58, py_],
            [cx + 92, py_ + 18], [cx + 92, py_ + 78]]
    pg.polygon(pier, fill=rgba(SILT, 0.25), stroke=INK, stroke_style={"stroke_width": 1.5})
    pg.polygon(pier, fill=hatch(fg=rgba(SILT, 0.20), scale=7, angle=45), decorative=True)
    part_label("CAISSON PIER", py_ + 36, cx + 96)


# --------------------------------------------------------------------------- #
# Assembly + QA report
# --------------------------------------------------------------------------- #
def _qa_report():
    panel_eff = mixc(PANELC, PAPER, 0.22)  # panel surface composited on paper
    checks = [
        ("body ink / paper", INK, PAPER, 4.5),
        ("body ink / panel", INK, panel_eff, 4.5),
        ("ink2 label / panel", INK2, panel_eff, 4.5),
        ("ink3 foot / paper", INK3, PAPER, 4.5),
        ("tide / panel", TIDE, panel_eff, 3.0),
        ("signal / panel", SIGNAL, panel_eff, 3.0),
        ("paper on signal (btn)", PAPER, SIGNAL, 4.5),
    ]
    print("— palette:", {"paper": PAPER, "ink": INK, "ink2": INK2, "ink3": INK3,
                         "signal": SIGNAL, "tide": TIDE, "silt": SILT,
                         "ok": OK, "warn": WARN, "fault": FAULT})
    for name, a, bcol, floor in checks:
        r = contrast_ratio(a, bcol)
        print(f"— contrast {name}: {r:.2f}:1 (floor {floor}:1) {'PASS' if r >= floor else 'FAIL'}")
    print(f"— surge amp calibrated: {SURGE_AMP:.3f} m; peak {PEAK_V:.2f} m @ t={PEAK_T:.2f} h")
    print(f"— {CLOSURE_LABEL}")
    n_chars = round((420) / max(measure_text('n', font_family='Charis SIL', font_size=27), 1e-6))
    print(f"— essay measure ≈ {n_chars} ch/line (canon band 45–75; narrow plate columns, hyphenless)")


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="The Estuary Works — Plate 04", profile="diagram", lang="en-GB")
    pg = b.page("plate04", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    pg.layer("bg")
    pg.rect([0, 0, W, H], fill=PAPER)
    hero(pg)
    pg.layer("scrim")
    scrims(pg)
    pg.layer("anno")
    section(pg)
    callouts(pg)
    hero_annotations(pg)
    scrubber(pg)
    pg.layer("panels")
    map_panel(pg)
    tide_chart(pg)
    ops_console(pg)
    exploded(pg)
    pg.layer("edit")
    masthead(pg)
    essay(pg)
    archival(pg)
    footnotes(pg)
    colophon(pg)
    pg.layer("grain")   # §19 ly.grain — blend overlay, opacity 0.10
    pg.rect([0, 0, W, H], fill=PAPER, opacity=0.10, decorative=True,
            **style_effects(filter=film_grain(184911), mix_blend_mode="overlay"))
    _qa_report()
    return b
