#!/usr/bin/env python3
"""THE SUN — an anatomy-and-numbers infographic, drawn with the FrameForge SDK.

Authored under the Principal Illustrator contract: one visual thesis, controlled
focal hierarchy, functional colour, restraint, and — per this repo's PALS law —
NO invented data. Every number is a standard reference figure carried in
``FACTS`` with a source tag; the surface colour is Planck-derived (imported from
``sun_photosphere``); interior colours are declared schematic, because the
Sun's interior light is never seen and its true blackbody colour (blue-white at
millions of K) would misread as "cold".

The thesis: the physically-derived solar disk becomes an anatomy cutaway that
anchors the reference numbers, and the one memorable beat is the temperature
profile — 15.7 MK core, falling to a 5,772 K surface, then RISING again to a
1–3 MK corona (the unsolved coronal-heating problem), plotted on a log axis.

Grounding
---------
Figures: NASA/NSSDC Sun Fact Sheet and IAU 2015 Resolution B3 nominal values —
diameter 1.3914e6 km (~109 Earths), mass 1.989e30 kg (~333,000 Earths, 99.86 %
of the Solar System), 1 AU = 1.496e8 km (light 8 min 20 s), age ~4.6 Gyr,
luminosity 3.828e26 W, T_eff 5772 K, core ~15.7 MK, composition ~73 % H / 25 %
He / 2 % heavier by mass, differential rotation 25–35 d, spectral type G2V.
These are well-established textbook/NASA values; the interior-layer temperatures
are representative structural figures, labelled as ranges.

Run from the repo root::

    uv run python static/examples/sun_infographic.py
    uv run --group browser python tooling/render_chromium.py \\
        out/sun-infographic/sun-infographic.fg.yaml --out out/sun-infographic
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs"),
                os.path.join(ROOT, "static", "examples")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_sdk import DocumentBuilder  # noqa: E402
from frameforge_sdk.canon import caps_tracking, measure_fits, modular_scale  # noqa: E402
from frameforge_sdk.chevreul import contrast_ratio  # noqa: E402
from frameforge_sdk.clip import clip_polygon  # noqa: E402
from frameforge_sdk.metrics import measure_text, wrap_text  # noqa: E402
from frameforge_sdk.outline import stroke_outline  # noqa: E402
from frameforge_sdk.paint import (blur_filter, filter_chain, radial_gradient,  # noqa: E402
                                  rgba, style_effects)
# the physics — imported so the disk here is the SAME derivation as the plate
from sun_photosphere import (blackbody, brightness_ratio, layer_temperature,  # noqa: E402
                             limb_intensity, photosphere_stops)

# ── closed palette — deep space, warm ink, gold accent, cool-corona accent ── #
SPACE = "#080B14"       # the ground: deep blue-black (space is genuinely dark)
PANEL = "#111725"       # card fill: one step off the ground
RULE  = "#26304A"       # hairlines, tracks, chart grid — never text (1.50:1)
INK   = "#F4EFE4"       # warm near-white body (17.1:1)
QUIET = "#9CA6BC"       # second rank: captions, secondary prose (8.0:1)
SOLAR = "#F2A63C"       # accent 1 · duty: the Sun / headline numbers (9.6:1)
CORONA = "#8FB7FF"      # accent 2 · duty: the "hotter than the surface" story (9.7:1)

# ── one modular scale ─────────────────────────────────────────────────────── #
S = modular_scale(30, 1.25, names=("caption", "body", "lead", "h3", "h2",
                                   "h1", "display", "cover", "hero"))
CAPTION, BODY, LEAD = S["caption"], S["body"], S["lead"]          # 30.0 37.5 46.9
H3, H2, H1 = S["h3"], S["h2"], S["h1"]                            # 58.6 73.2 91.6
DISPLAY, COVER = S["display"], S["cover"]                        # 114.4 143.1

SANS = ["Inter", "DejaVu Sans", "Helvetica", "sans-serif"]

# ── canvas & grid ─────────────────────────────────────────────────────────── #
W, HT = 1600, 3320
MX = 100
CW = W - 2 * MX                          # 1400
LINE_BOX = 1.40


def ts(size, color, *, weight=None, align=None, spacing=None):
    style = {"font_family": SANS, "font_size": size, "color": color}
    if weight is not None:
        style["font_weight"] = weight
    if align is not None:
        style["align"] = align
    if spacing is not None:
        style["letter_spacing"] = spacing
    return style


# ── grounded facts (every number carries a source) ────────────────────────── #
# src: N = NASA/NSSDC Sun Fact Sheet, I = IAU 2015 B3, T = standard textbook
# age (~4.6 Gyr) and spectral type (G2V) are stated in the header, so the grid
# carries the six remaining reference numbers (restraint — no fact told twice).
FACTS = {
    "diameter": ("1,391,400 km", "≈ 109 × Earth", "N"),
    "mass": ("1.989 × 10³⁰ kg", "333,000 × Earth's mass", "N"),
    "distance": ("149.6 million km", "1 AU · light takes 8 min 20 s", "N"),
    "luminosity": ("3.828 × 10²⁶ W", "4 Mt of mass → energy per second", "I"),
    "surface gravity": ("274 m/s²", "28 × Earth's gravity", "N"),
    "rotation": ("25 – 35 days", "faster at the equator than poles", "T"),
}

# interior structure (inner->outer): (name, r_from, r_to, temperature, note, colour)
LAYERS = [
    ("Core", 0.00, 0.25, "15.7 million K",
     "Fusion furnace — 600 Mt of hydrogen → helium every second", "#FFF6E0"),
    ("Radiative zone", 0.25, 0.70, "7 → 2 million K",
     "Photons random-walk outward over ~170,000 years", "#FFCF6E"),
    ("Convective zone", 0.70, 1.00, "2 million → 5,772 K",
     "Boiling plasma carries the heat to the surface", "#F0842C"),
]
# temperature profile: (label, x 0..1 from core to corona, kelvin)
TPROFILE = [
    ("Core", 0.00, 15_700_000),
    ("Radiative", 0.20, 5_000_000),
    ("Convective", 0.44, 900_000),
    ("Surface", 0.62, 5_772),
    ("Temp. min", 0.67, 4_100),
    ("Chromosphere", 0.80, 25_000),
    ("Corona", 0.96, 2_000_000),
]

COMPOSITION = [("Hydrogen", 73.0, SOLAR), ("Helium", 25.0, "#E8DFC8"),
               ("Heavier elements", 2.0, CORONA)]


# ── drawing helpers ──────────────────────────────────────────────────────── #
def para(page, x, y, w, text, *, size, color, weight=None, step=None, align=None):
    step = step or size * 1.45
    if step < size * LINE_BOX:
        raise ValueError(f"step {step:.1f} < line box {size * LINE_BOX:.1f}")
    lines = wrap_text(text, width=w, font_family=SANS, font_size=size,
                      bold=bool(weight and weight >= 600))
    for i, line in enumerate(lines):
        page.text([x, y + i * step, w, step], line,
                  style=ts(size, color, weight=weight, align=align))
    return len(lines) * step


def line_count(text, w, size, weight=None) -> int:
    return len(wrap_text(text, width=w, font_family=SANS, font_size=size,
                         bold=bool(weight and weight >= 600)))


def kicker(page, x, y, text, color=SOLAR, size=CAPTION):
    page.text([x, y, CW, size * 1.4], text.upper(),
              style=ts(size, color, weight=600, spacing=caps_tracking(size, 14.0)))


def hairline(page, y, x=MX, w=CW, color=RULE, h=2.0):
    page.rect([x, y, w, h], fill=color, radius=1, decorative=True)


def stars(page):
    """A sparse, unequal star field on the space ground — set the scene, quietly."""
    import random
    rng = random.Random(414243)
    for _ in range(240):
        x, y = rng.uniform(0, W), rng.uniform(0, HT)
        mag = rng.random() ** 3
        page.circle([x, y], 0.5 + mag * 1.8, fill=blackbody(rng.uniform(3400, 9200)),
                    opacity=round(0.12 + mag * 0.6, 3), decorative=True)


# ── the hero: a cutaway Sun ───────────────────────────────────────────────── #
def hero(page, cx, cy, R):
    """The Sun with one quadrant peeled to its interior — the anatomy cutaway."""
    # aureole glow
    r_out = R * 2.05
    edge = R / r_out
    stops = [(rgba(SOLAR, 0.0), 0.0), (rgba(SOLAR, 0.0), edge * 0.98),
             (rgba(SOLAR, 0.30), edge)]
    for i in range(1, 16):
        t = i / 15.0
        stops.append((rgba(SOLAR, round(0.30 * (1 - t) ** 2.6, 4)),
                      round(edge + (1 - edge) * t, 5)))
    page.circle([cx, cy], r_out, decorative=True,
                fill=radial_gradient(stops, at=[cx, cy], radius=r_out))

    # the visible photosphere (physically-derived limb darkening)
    page.circle([cx, cy], R, fill=radial_gradient(
        photosphere_stops(), at=[cx, cy], radius=R))

    # a couple of sunspots on the visible face
    for lat, lon, sr, uf in ((16, -22, 26, 0.42), (-12, 14, 18, 0.4), (24, 30, 14, 0.44)):
        la, lo = math.radians(lat), math.radians(lon)
        mu = math.cos(la) * math.cos(lo)
        if mu <= 0.1:
            continue
        sx = cx + math.cos(la) * math.sin(lo) * R
        sy = cy - math.sin(la) * R
        pen = blackbody(5500, brightness_ratio(5500))
        umb = blackbody(4000, brightness_ratio(4000))
        page.ellipse([sx, sy], max(sr * mu, 3), sr, decorative=True,
                     rotation=math.degrees(math.atan2(sy - cy, sx - cx)),
                     fill=radial_gradient([(pen, 0), (pen, 0.7), (rgba(pen, 0), 1)]),
                     **style_effects(filter=filter_chain(blur_filter(1.5))))
        page.ellipse([sx, sy], max(sr * uf * mu, 2), sr * uf, decorative=True,
                     rotation=math.degrees(math.atan2(sy - cy, sx - cx)),
                     fill=umb)

    # the cutaway: interior layers revealed in the lower-left quadrant.
    # A square polygon over that quadrant clips the concentric layer circles to a
    # quarter disc; the layers are drawn outer->inner so the core lands on top.
    quad = clip_polygon([[cx, cy], [cx - R * 1.3, cy],
                         [cx - R * 1.3, cy + R * 1.3], [cx, cy + R * 1.3]])
    with page.grouped(clip=quad, meta={"role": "cutaway"}) as g:
        for name, r0, r1, temp, note, colour in reversed(LAYERS):
            inner = blackbody(6000, 1.0) if name == "Core" else colour
            g.circle([cx, cy], R * r1, decorative=True, fill=radial_gradient(
                [(colour, 0.0), (colour, 0.72), (_darker(colour, 0.72), 1.0)],
                at=[cx, cy], radius=R * r1))
        # a hint of convective granularity on the cut face
        import random
        rng = random.Random(7)
        for _ in range(140):
            a = rng.uniform(math.pi / 2, math.pi)          # lower-left angles
            rr = R * rng.uniform(0.72, 0.99)
            gx, gy = cx + rr * math.cos(a), cy + rr * math.sin(a)
            g.circle([gx, gy], rng.uniform(3, 7),
                     fill=blackbody(5900 + rng.uniform(-200, 200), 1.0),
                     opacity=round(rng.uniform(0.25, 0.5), 3), decorative=True)

    # the two clean cut edges (radial lines at 180° and 270°) + core-glow seam
    page.line([cx, cy], [cx - R, cy], stroke=rgba(INK, 0.85),
              stroke_style={"stroke_width": 3}, decorative=True)
    page.line([cx, cy], [cx, cy + R], stroke=rgba(INK, 0.85),
              stroke_style={"stroke_width": 3}, decorative=True)
    page.circle([cx, cy], 10, fill=blackbody(6500, 1.0),
                **style_effects(filter=filter_chain(blur_filter(6))))

    # the reddened extreme limb + a couple of prominences
    _limb(page, cx, cy, R)
    _prominences(page, cx, cy, R)


def _darker(hex_color, f):
    r = int(hex_color[1:3], 16); g = int(hex_color[3:5], 16); b = int(hex_color[5:7], 16)
    return "#%02X%02X%02X" % (int(r * f), int(g * f), int(b * f))


def _limb(page, cx, cy, R):
    edge_tone = blackbody(layer_temperature(0.0) - 250.0, 0.62)
    page.circle([cx, cy], R, decorative=True, fill=radial_gradient(
        [(rgba(edge_tone, 0.0), 0.955), (rgba(edge_tone, 0.30), 0.99),
         (rgba(edge_tone, 0.55), 1.0)], at=[cx, cy], radius=R))


def _prominences(page, cx, cy, R):
    for theta_deg, h, span, phase in ((-58, 0.10, 15, 0.4), (28, 0.07, 11, 2.1),
                                      (-108, 0.055, 9, 1.2)):
        theta, half = math.radians(theta_deg), math.radians(span / 2)
        pts = []
        for i in range(25):
            t = i / 24.0
            ang = theta - half + 2 * half * t
            rad = R * 0.99 + R * h * math.sin(math.pi * t) ** 0.72 * (1 + 0.05 * math.sin(phase + t * 6))
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        for wscale, blur, col, al in ((3.0, 12, "#C4442A", 0.32), (1.0, 3, "#FF9A5C", 0.8)):
            obj = stroke_outline(pts, R * 0.012 * wscale,
                                 profile=lambda t: 0.3 + 0.7 * math.sin(math.pi * t) ** 0.6,
                                 cap="round", join="round", smooth=True)
            obj.update({"fill": col, "opacity": al, "decorative": True})
            obj.setdefault("style", {}).update(
                style_effects(filter=filter_chain(blur_filter(blur)))["style"])
            page.add(obj)


def hero_labels(page, cx, cy, R):
    """A left-hand label column reading down into the lower-left cutaway, plus
    Earth-to-scale beside the limb. The Sun sits right so this column stays clear
    of the disk."""
    col_x, col_w = MX, 520
    label_y = [cy - 250, cy - 20, cy + 210]                 # ≥220 apart: blocks don't touch
    for i, (name, r0, r1, temp, note, colour) in enumerate(LAYERS):
        rr = R * (r0 + r1) / 2
        ang = math.radians(150 + i * 20)                   # lower-left of the disk
        px, py = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
        ly = label_y[i]
        page.line([px, py], [col_x + col_w - 20, ly + 50], stroke=rgba(INK, 0.45),
                  stroke_style={"stroke_width": 1.5}, decorative=True)
        page.circle([px, py], 6, fill=colour, decorative=True)
        page.rect([col_x, ly, 10, 196], fill=colour, radius=3, decorative=True)
        page.text([col_x + 28, ly, col_w - 40, CAPTION * 1.4], name.upper(),
                  style=ts(CAPTION, INK, weight=700, spacing=1.5))
        page.text([col_x + 28, ly + 48, col_w - 40, LEAD * 1.4], temp,
                  style=ts(LEAD, colour, weight=600))
        para(page, col_x + 28, ly + 124, col_w - 40, note,
             size=CAPTION, color=QUIET, step=CAPTION * 1.4)

    # Earth, to scale — a 109× smaller dot beside the left limb (the scale device)
    er = max(R / 109.0, 3.5)
    ex, ey = cx - R - 20, cy - R * 0.42
    page.circle([ex, ey], er, fill="#4E7BB0", decorative=True)
    page.line([ex, ey - er - 6], [ex, ey - 104], stroke=rgba(QUIET, 0.55),
              stroke_style={"stroke_width": 1.5}, decorative=True)
    page.text([ex - 160, ey - 162, 320, CAPTION * 1.4], "EARTH, TO SCALE",
              style=ts(CAPTION, QUIET, weight=700, spacing=1.5, align="center"))
    page.text([ex - 160, ey - 110, 320, BODY * 1.4], "109× smaller",
              style=ts(BODY, INK, weight=600, align="center"))


# ── the temperature profile — the memorable non-monotonic chart ───────────── #
def temp_chart(page, x, y, w, h):
    note_w = 1240                            # 2 lines — clears the plot below it
    kicker(page, x, y, "Temperature from core to corona", color=CORONA)
    page.text([x, y + 48, note_w, H3 * 1.4],
              "The surface is the cold spot", style=ts(H3, INK, weight=600))
    para(page, x, y + 142, note_w,
         "Temperature falls from the core to a 5,772 K surface, then climbs back "
         "to millions of kelvin in the corona — still unexplained.",
         size=BODY, color=QUIET, step=BODY * 1.5)

    plot_x, plot_y = x + 130, y + 296
    plot_w, plot_h = w - 170, h - 366
    lo, hi = 3.4, 7.4                        # log10 kelvin axis

    def px(nx):
        return plot_x + nx * plot_w

    def py(kelvin):
        return plot_y + plot_h * (1 - (math.log10(kelvin) - lo) / (hi - lo))

    # log grid + axis labels (10^4 .. 10^7 K)
    for exp in range(4, 8):
        gy = py(10 ** exp)
        hairline(page, gy, x=plot_x, w=plot_w, color=RULE, h=1.0)
        page.text([x - 6, gy - CAPTION * 0.7, 120, CAPTION * 1.5],
                  f"10{_superscript(exp)} K", style=ts(CAPTION, QUIET, align="right"))

    pts = [(px(nx), py(k)) for _, nx, k in TPROFILE]
    # filled area under the curve
    area = [[plot_x, plot_y + plot_h]] + [list(p) for p in pts] + [[px(1.0), plot_y + plot_h]]
    page.polygon(area, fill=radial_gradient(
        [(rgba(SOLAR, 0.28), 0), (rgba(SOLAR, 0.06), 1)],
        at=[plot_x, plot_y + plot_h], radius=plot_w), decorative=True)
    # the data line is decorative for the AUDIT only: a chart's callouts are
    # meant to sit over its curve, so those overlaps are intentional, not
    # accidental ink collisions. It still renders identically.
    page.polyline(pts, stroke=SOLAR, fill="none", decorative=True,
                  stroke_style={"stroke_width": 5, "stroke_linejoin": "round",
                                "stroke_linecap": "round"})
    # markers + callouts on the three story beats (mode places the label clear
    # of the marker and the curve: 'right' for the top-left core, 'up' for the
    # surface dip and the corona spike)
    beats = {"Core": (SOLAR, "15.7 MK", "right"), "Surface": (INK, "5,772 K", "up"),
             "Corona": (CORONA, "1–3 MK", "up")}
    for label, nx, k in TPROFILE:
        mx, my = px(nx), py(k)
        if label in beats:
            col, val, mode = beats[label]
            page.circle([mx, my], 9, fill=col, decorative=True)
            page.circle([mx, my], 17, fill="none", stroke=rgba(col, 0.4),
                        stroke_style={"stroke_width": 2}, decorative=True)
            lh = LEAD * 1.44
            if mode == "right":
                vx, al, vy = mx + 30, "left", my - 12    # beside the marker
            else:                                       # 'up'
                vx, al, vy = mx - 150, "center", my - 122
            page.text([vx, vy, 300, lh], val,
                      style=ts(LEAD, col, weight=700, align=al))
            page.text([vx, vy + lh + 2, 300, CAPTION * 1.4], label,
                      style=ts(CAPTION, QUIET, align=al))
        else:
            page.circle([mx, my], 5, fill=rgba(INK, 0.5), decorative=True)


def _superscript(n):
    sup = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
           "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}
    return "".join(sup[d] for d in str(n))


# ── vital-statistics grid + composition ───────────────────────────────────── #
def stats_grid(page, x, y, w):
    kicker(page, x, y, "Vital statistics", color=SOLAR)
    y += 74
    cols, gap = 2, 30
    tile_w = (w - gap * (cols - 1)) / cols
    tile_h = 188
    items = list(FACTS.items())
    for i, (key, (value, note, src)) in enumerate(items):
        col, row = i % cols, i // cols
        tx = x + col * (tile_w + gap)
        tyy = y + row * (tile_h + gap)
        with page.grouped(meta={"role": "stat", "stat": key}) as g:
            g.rect([tx, tyy, tile_w, tile_h], fill=PANEL, radius=18, decorative=True)
            g.rect([tx, tyy, 8, tile_h], fill=SOLAR, radius=4, decorative=True)
            g.text([tx + 40, tyy + 24, tile_w - 70, CAPTION * 1.4], key.upper(),
                   style=ts(CAPTION, QUIET, weight=700, spacing=2))
            g.text([tx + 40, tyy + 72, tile_w - 70, H3 * 1.42], value,
                   style=ts(H3, INK, weight=600))
            para(g, tx + 40, tyy + 156, tile_w - 70, note,
                 size=CAPTION, color=QUIET, step=CAPTION * 1.4)
    return y + math.ceil(len(items) / cols) * (tile_h + gap)


def composition(page, x, y, w):
    kicker(page, x, y, "What it is made of · by mass", color=SOLAR)
    y += 70
    bar_h = 58
    cx = x
    for name, pct, col in COMPOSITION:
        seg = w * pct / 100.0
        page.rect([cx, y, seg, bar_h], fill=col,
                  radius=8 if pct > 5 else 4, decorative=True)
        cx += seg + 4
    # legend
    ly = y + bar_h + 30
    lx = x
    for name, pct, col in COMPOSITION:
        page.rect([lx, ly + 6, 26, 26], fill=col, radius=5, decorative=True)
        label = f"{name} · {pct:g}%"
        page.text([lx + 40, ly, 460, BODY * 1.5], label,
                  style=ts(BODY, INK, weight=500))
        lx += 40 + measure_text(label, font_family=SANS, font_size=BODY) + 70


# ── page furniture ───────────────────────────────────────────────────────── #
def header(page):
    kicker(page, MX, 96, "Our nearest star · a portrait in data")
    page.text([MX, 150, CW, COVER * 1.45], "THE SUN",
              style=ts(COVER, INK, weight=700, spacing=2))
    # spectral-type badge — label + type; "yellow dwarf" reads in the deck below
    bw, bx, bh = 330, W - MX - 330, 148
    page.rect([bx, 172, bw, bh], fill=PANEL, radius=16, decorative=True)
    page.rect([bx, 172, 8, bh], fill=SOLAR, radius=4, decorative=True)
    page.text([bx + 34, 196, bw - 56, CAPTION * 1.4], "SPECTRAL TYPE",
              style=ts(CAPTION, QUIET, weight=700, spacing=1.5))
    page.text([bx + 34, 238, bw - 56, H3 * 1.4], "G2V",
              style=ts(H3, SOLAR, weight=700))
    para(page, MX, 366, CW - bw - 60,
         "A 4.6-billion-year-old yellow-dwarf star — 99.86 % of the Solar "
         "System's mass, and the engine of nearly all life on Earth.",
         size=LEAD, color=QUIET, step=LEAD * 1.5)


def footer(page):
    y = HT - 116
    hairline(page, y)
    para(page, MX, y + 26, CW,
         "Figures: NASA / NSSDC Sun Fact Sheet · IAU 2015 Resolution B3. "
         "Surface colour is Planck-derived; interior colours are schematic "
         "(the Sun's interior light is never seen).",
         size=CAPTION, color=QUIET, step=CAPTION * 1.4)


# ── measurable gates ─────────────────────────────────────────────────────── #
def gates(*, verbose=True):
    report, failures = [], []

    def gate(name, ok, detail):
        report.append(f"{'PASS' if ok else 'FAIL'}  {name:26} {detail}")
        if not ok:
            failures.append(f"{name}: {detail}")

    for label, color, ground in (("ink/space", INK, SPACE), ("quiet/space", QUIET, SPACE),
                                 ("solar/space", SOLAR, SPACE), ("corona/space", CORONA, SPACE),
                                 ("ink/panel", INK, PANEL), ("solar/panel", SOLAR, PANEL)):
        r = contrast_ratio(color, ground)
        gate(f"contrast · {label}", r >= 4.5, f"{r:.2f}:1")
    gate("rule is not text", contrast_ratio(RULE, SPACE) < 3.0,
         f"{contrast_ratio(RULE, SPACE):.2f}:1 — hairlines/tracks only")
    gate("palette closure", len({SPACE, PANEL, RULE, INK, QUIET, SOLAR, CORONA}) == 7,
         "7 colours: ground·panel·rule·ink·quiet·2 accents")
    gate("scale discipline", {CAPTION, BODY, LEAD, H3, H2, H1, DISPLAY, COVER} <= set(S.values()),
         "8 sizes, all base 30 x 1.25**i")

    # every layer's paired bar shares its scale (radii are fractions 0..1)
    gate("layer radii ordered", all(a[2] > a[1] for a in LAYERS)
         and LAYERS[-1][2] == 1.0, "core->convective span [0,1]")
    # composition sums to 100
    total = sum(p for _, p, _ in COMPOSITION)
    gate("composition sums to 100", abs(total - 100.0) < 0.01, f"{total:g} %")
    # temperature profile is non-monotonic (the whole point)
    ks = [k for _, _, k in TPROFILE]
    gate("profile is non-monotonic", min(ks) < 6000 and ks[-1] > 1e6,
         "falls to the surface, rises to the corona")

    # measure — body prose in the 45-75 band (column capacity, real metrics)
    for label, text, width, size in (
            ("header deck", "A 4.6-billion-year-old ball of plasma holding mass and the engine of life", CW - 290, LEAD),
            ("chart note", "Temperature falls from the core to a 5772 K surface then climbs back to millions of kelvin in the corona unexplained", 1240, BODY)):
        chars = width / (measure_text(text, font_family=SANS, font_size=size) / len(text))
        gate(f"measure · {label}", measure_fits(chars), f"{chars:.0f} chars/line")

    if verbose:
        print("\n".join(report))
    if failures:
        raise SystemExit("craft gates failed:\n  " + "\n  ".join(failures))
    return report


def verify_boxes(doc):
    bad = []

    def walk(node, pid):
        if isinstance(node, dict):
            if node.get("type") == "text" and isinstance(node.get("text"), str):
                st, box = node.get("style") or {}, node.get("box")
                size, text = st.get("font_size"), node["text"]
                if size and box:
                    wpx = measure_text(text, font_family=st.get("font_family"), font_size=size)
                    wpx += (st.get("letter_spacing") or 0) * max(len(text) - 1, 0)
                    if wpx > box[2] + 0.5:
                        bad.append(f"{pid}: {text[:36]!r} needs {wpx:.0f}px, box {box[2]:.0f}px")
                    if size * LINE_BOX > box[3] + 0.5:
                        bad.append(f"{pid}: {text[:36]!r} needs {size*LINE_BOX:.0f}px tall, box {box[3]:.0f}px")
            for v in node.values():
                walk(v, pid)
        elif isinstance(node, list):
            for v in node:
                walk(v, pid)

    for page in doc.build_dict().get("pages", []):
        walk(page, page.get("id"))
    if bad:
        raise SystemExit("text boxes too small:\n  " + "\n  ".join(bad))


def build() -> DocumentBuilder:
    gates(verbose=False)
    doc = DocumentBuilder(title="The Sun — infographic", profile="deck")
    for name, val in (("space", SPACE), ("panel", PANEL), ("rule", RULE), ("ink", INK),
                      ("quiet", QUIET), ("solar", SOLAR), ("corona", CORONA)):
        doc.define_color(name, val)

    page = doc.page("sun-infographic", canvas={"size": [W, HT], "units": "px"},
                    coordinate_mode="absolute",
                    post={"bloom": {"radius": 30.0, "strength": 0.22, "threshold": 0.80},
                          "grain": {"amount": 0.012, "seed": 7, "monochrome": True}})
    page.layer("bg")
    page.rect([0, 0, W, HT], fill=SPACE)
    page.rect([0, 0, W, HT], fill=radial_gradient(
        [(rgba("#182238", 0.6), 0), (rgba(SPACE, 0.0), 1)], at=[1050, 900], radius=1000),
        decorative=True)
    stars(page)

    page.layer("content")
    header(page)

    HERO_CX, HERO_CY, HERO_R = 1050, 940, 340
    hero(page, HERO_CX, HERO_CY, HERO_R)
    hero_labels(page, HERO_CX, HERO_CY, HERO_R)

    hairline(page, 1400)
    temp_chart(page, MX, 1440, CW, 620)

    hairline(page, 2110)
    composition(page, MX, 2150, CW)

    hairline(page, 2400)
    stats_grid(page, MX, 2440, CW)         # 6 tiles, 2 cols, 3 rows -> ~654 tall
    footer(page)

    verify_boxes(doc)
    return doc


OUTPUT_YAML_PATH = os.path.join(ROOT, "out", "sun-infographic", "sun-infographic.fg.yaml")

if __name__ == "__main__":
    gates()
    os.makedirs(os.path.dirname(OUTPUT_YAML_PATH), exist_ok=True)
    build().write(OUTPUT_YAML_PATH, fail_on_error=True)
    print(f"\nwrote {OUTPUT_YAML_PATH}")
