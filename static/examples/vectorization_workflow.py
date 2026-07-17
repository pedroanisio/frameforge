#!/usr/bin/env python3
"""AI-Assisted Vectorization Workflow — a product/landing composition.

A single 1440x1000 vector document, built with FrameForge primitives only,
that sells an AI-assisted raster->vector service ("from messy bitmap to
editable production vector"). Everything below is drawn with rect / rounded
rect / text / line / ellipse / circle / polygon / path / group primitives plus
gradient + shadow paint. No raster images are imported: the "low-res JPG" on
the Input side is *simulated* out of vector pixel blocks, colour jitter, scan
noise and a chroma ghost, so the whole asset stays inspectable and editable.

Named layers (semantic groups), in z-order:
    background · hero · before_after_panel · input_bitmap_simulation ·
    output_vector_reconstruction · workflow_pipeline · api_flow_card ·
    value_cards · annotations

Run from the repository root::

    uv run python static/examples/vectorization_workflow.py

Writes the source YAML (`vectorization-workflow.fg.yaml`) and the true SVG
(`vectorization-workflow.svg`) to the repo root. Rasterize to PNG with::

    uv run python tooling/render_chromium.py vectorization-workflow.fg.yaml \\
        --out out/vectorization --max-pages 1
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    linear_gradient,
    measure_text,
    radial_gradient,
    rgba,
    render_page_svgs,
    render_pages_with_stats,
    serialize,
    validate_static_rules,
)
from frameforge.sdk.clip import clip_rect  # noqa: E402
from frameforge.sdk.paint import effects, shadow, soft_shadow  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas + palette
# --------------------------------------------------------------------------- #
W, H = 1440, 1000
M = 40                       # page margin
CW = W - 2 * M               # content width

COLORS = {
    "bg":        "#F7F6F2",  # warm off-white
    "bg2":       "#F1EFEA",
    "paper":     "#FFFFFF",
    "ink":       "#191B22",  # charcoal
    "ink2":      "#2A2D38",
    "sub":       "#6B7180",  # muted body
    "faint":     "#9AA0AE",
    "hair":      "#E8E6E0",
    "hair2":     "#E2E4EA",
    "violet":    "#6D4EF2",  # electric violet accent
    "violet2":   "#8B74F7",
    "blue":      "#3B6EF2",  # electric blue accent
    "blue2":     "#5B8CFF",
    "ok":        "#12A150",  # clean / approved
    "okbg":      "#E9F7EF",
    "warm":      "#F0603A",  # bad-input warm accent
    "warm2":     "#F5834E",
    "warmbg":    "#FEF1EB",  # input panel tint
    "warmline":  "#F4C4AE",
    "coolbg":    "#F3F0FF",  # output panel tint
    "coolline":  "#DAD2FB",
    # emblem brand colours (shared by both sides)
    "amber":     "#F2B705",
    "amber2":    "#F7CE4B",
    "peakA":     "#6D4EF2",
    "peakB":     "#3B6EF2",
    "ground":    "#242732",
    "dark":      "#14151B",  # api card
    "darkln":    "#2C2E3A",
    "darkkey":   "#3A3D4C",
}

SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
MONO = ["JetBrains Mono", "SF Mono", "DejaVu Sans Mono", "monospace"]


def _ts(size, weight=500, color="ink", align="left", ls=0.0, lh=1.32, family=None):
    return dict(font_family=family or SANS, font_size=size, font_weight=weight,
                color=color, align=align, letter_spacing=ls, line_height=lh)


STYLES = {
    "brand":    _ts(15, 800, "ink", "left", 0.4, 1.0),
    "h1":       _ts(37, 700, "ink", "left", -0.8, 1.08),
    "sub":      _ts(15.5, 400, "sub", "left", 0, 1.4),
    "badge":    _ts(12, 700, "violet", "left", 0.4),
    "seclabel": _ts(12.5, 700, "faint", "left", 1.8),
    "sidekick": _ts(11, 700, "faint", "left", 1.6),
    "panelTag": _ts(12, 800, "paper", "center", 1.2),
    "panelTitle": _ts(19, 700, "ink", "left", -0.2),
    "panelSub": _ts(12.5, 500, "sub", "left"),
    "mark":     _ts(20, 800, "ink", "center", 2.0),
    "markSub":  _ts(9.5, 600, "sub", "center", 3.0),
    "anno":     _ts(11.5, 600, "ink", "left", 0.1),
    "annoWarm": _ts(11.5, 700, "warm", "left", 0.1),
    "annoOk":   _ts(11.5, 700, "ok", "left", 0.1),
    "stepNum":  _ts(11, 800, "paper", "center", 0),
    "stepTitle": _ts(13.5, 700, "ink", "left", -0.1),
    "stepBody": _ts(11, 400, "sub", "left", 0, 1.32),
    "cardH":    _ts(15.5, 700, "paper", "left", 0.2),
    "apiMethod": _ts(11, 800, "paper", "center", 0.4),
    "apiPath":  _ts(13, 600, "#E7E9F2", "left", 0, 1.2, MONO),
    "apiNote":  _ts(11, 500, "#9AA0B8", "left", 0, 1.35),
    "apiStep":  _ts(11, 500, "#B9BDD0", "left", 0.2),
    "valTitle": _ts(15, 700, "ink", "left", -0.1),
    "valBody":  _ts(12, 400, "sub", "left", 0, 1.34),
    "valKick":  _ts(10.5, 700, "violet", "left", 1.2),
    "foot":     _ts(11, 500, "faint", "left", 0.2),
}


# --------------------------------------------------------------------------- #
# Paint + measure helpers
# --------------------------------------------------------------------------- #
def lg(p0, p1, stops):
    ang = round(math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])), 1)
    return linear_gradient([(c, p) for (p, c) in stops], angle=ang)


def rg(at, stops, shape="circle"):
    return radial_gradient([(c, p) for (p, c) in stops], at=at, shape=shape)


def tw(text, size, weight=500):
    return measure_text(text, font_family=SANS, font_size=size, bold=weight >= 600)


def card(L, box, *, radius=16, fill="paper", border="hair", bw=1.0, sh="soft", **extra):
    f = dict(fill=fill, radius=radius, **extra)
    if border:
        f["stroke"] = border
        f["stroke_style"] = {"stroke_width": bw}
    if sh == "soft":
        f.update(effects(shadow=shadow(dy=10, blur=30, color="#5A5B72", opacity=0.13)))
    elif sh == "lift":
        f.update(effects(shadow=shadow(dy=18, blur=44, color="#4A4B66", opacity=0.18)))
    L.rect(box, **f)


def pill(L, x, y, label, *, fg="violet", bg="coolbg", dot=True, h=26, style="badge"):
    lw = tw(label, 12, 700)
    w = lw + (36 if dot else 24)
    L.rect([x, y, w, h], fill=bg, radius=h / 2, stroke="hair2", stroke_style={"stroke_width": 1})
    tx = x + 14
    if dot:
        L.ellipse([x + 15, y + h / 2], 3.4, 3.4, fill=fg)
        tx = x + 26
    L.text([tx, y + (h - 15) / 2, lw + 8, 16], label, style=style)
    return w


def arrow(L, x1, y1, x2, y2, *, color="faint", width=1.6, head=6.0, dash=None):
    ss = {"stroke_width": width, "stroke_linecap": "round"}
    if dash:
        ss["stroke_dasharray"] = dash
    L.line([x1, y1], [x2, y2], stroke=color, stroke_style=ss)
    ang = math.atan2(y2 - y1, x2 - x1)
    for s in (+1, -1):
        a = ang + math.pi + s * 0.42
        L.line([x2, y2], [x2 + head * math.cos(a), y2 + head * math.sin(a)],
               stroke=color, stroke_style={"stroke_width": width, "stroke_linecap": "round"})


# --------------------------------------------------------------------------- #
# Shared emblem geometry — a fictional "APEX BUILD CO" peak mark.
# Both the pixel simulation and the clean vector are generated from these
# normalized (0..1, y-down) coordinates so the before/after is the SAME mark.
# --------------------------------------------------------------------------- #
SUN_C, SUN_R = (0.70, 0.30), 0.105
PEAK_A = [(0.40, 0.20), (0.14, 0.70), (0.66, 0.70)]   # back peak (violet)
PEAK_B = [(0.63, 0.33), (0.36, 0.70), (0.90, 0.70)]   # front peak (blue)
GROUND = (0.70, 0.775)                                 # ground band v-range


def _in_tri(p, tri):
    (x, y), ((ax, ay), (bx, by), (cx, cy)) = p, tri
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-9:
        return False
    a = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / d
    b = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
    return a >= 0 and b >= 0 and (a + b) <= 1


def _emblem_color(u, v):
    """Which brand region owns normalized point (u,v)? Front-to-back order."""
    if GROUND[0] <= v <= GROUND[1] and 0.12 <= u <= 0.92:
        return "ground"
    if _in_tri((u, v), PEAK_B):
        return "peakB"
    if _in_tri((u, v), PEAK_A):
        return "peakA"
    if (u - SUN_C[0]) ** 2 + (v - SUN_C[1]) ** 2 <= SUN_R ** 2:
        return "amber"
    return None


HEX = {"amber": (242, 183, 5), "peakA": (109, 78, 242),
       "peakB": (59, 110, 242), "ground": (36, 39, 50), "bg": (233, 226, 214)}


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(c))) for c in rgb)


def _jitter(rgb, rng, amt):
    return tuple(c + rng.randint(-amt, amt) for c in rgb)


# --------------------------------------------------------------------------- #
# INPUT — low-res / JPEG bitmap simulation (vector pixel blocks + noise)
# --------------------------------------------------------------------------- #
def draw_pixel_mark(L, box):
    ax, ay, aw, ah = box
    rng = random.Random(0xC0FFEE)
    N = 26                       # grid resolution -> chunky "pixels"
    cw, ch = aw / N, ah / N

    # chroma ghost: a faint magenta-shifted copy offset down-right (JPEG bleed)
    with L.bleed():
        for gy in range(N):
            for gx in range(N):
                u, v = (gx + 0.5) / N, (gy + 0.5) / N
                key = _emblem_color(u, v)
                if key in (None, "bg"):
                    continue
                base = _jitter(HEX[key], rng, 18)
                ghost = (min(255, base[0] + 40), base[1], min(255, base[2] + 30))
                L.rect([ax + gx * cw + 2.6, ay + gy * ch + 2.6, cw + 0.6, ch + 0.6],
                       fill=rgba(_hex(ghost), 0.28), decorative=True)

    # main quantized bitmap
    for gy in range(N):
        for gx in range(N):
            u, v = (gx + 0.5) / N, (gy + 0.5) / N
            key = _emblem_color(u, v)
            if key is None:
                # sparse background scan noise
                if rng.random() < 0.05:
                    g = rng.randint(198, 232)
                    L.rect([ax + gx * cw, ay + gy * ch, cw + 0.7, ch + 0.7],
                           fill=_hex((g, g - 4, g - 12)))
                continue
            base = _jitter(HEX[key], rng, 22)
            # occasional dead / banded pixel to sell the low-res look
            if rng.random() < 0.06:
                base = _jitter(base, rng, 34)
            L.rect([ax + gx * cw, ay + gy * ch, cw + 0.7, ch + 0.7], fill=_hex(base))

    # blur/compression haze — translucent light wash + horizontal scanlines
    with L.bleed():
        L.rect([ax, ay, aw, ah], fill=rgba("#FFFFFF", 0.06), decorative=True)
        for gy in range(0, N, 2):
            L.rect([ax, ay + gy * ch, aw, ch * 0.5],
                   fill=rgba("#000000", 0.05), decorative=True)
        # a few JPEG "mosquito" speckle blocks near edges
        for _ in range(14):
            sx = ax + rng.random() * aw
            sy = ay + rng.random() * ah
            g = rng.randint(150, 210)
            L.rect([sx, sy, cw * 0.9, ch * 0.9], fill=rgba(_hex((g, g, g)), 0.4),
                   decorative=True)

    # low-res wordmark: fuzzy double-printed text
    ty = ay + ah + 16
    L.text([ax - 12, ty + 1.4, aw + 24, 24], "APEX BUILD",
           style=dict(**STYLES["mark"], **{}) if False else "mark")
    L.text([ax - 12, ty, aw + 24, 24], "APEX BUILD",
           style=dict(font_family=SANS, font_size=20, font_weight=800, color=rgba("#191B22", 0.55),
                      align="center", letter_spacing=2.0))
    L.text([ax - 12, ty + 27, aw + 24, 14], "C O N S T R U C T I O N",
           style=dict(font_family=SANS, font_size=9.5, font_weight=600,
                      color=rgba("#6B7180", 0.6), align="center", letter_spacing=3.0))


# --------------------------------------------------------------------------- #
# OUTPUT — clean editable vector reconstruction (smooth paths, layered)
# --------------------------------------------------------------------------- #
def _poly_px(pts, box):
    ax, ay, aw, ah = box
    return [[ax + u * aw, ay + v * ah] for (u, v) in pts]


def draw_vector_mark(L, box, *, show_editing=True):
    ax, ay, aw, ah = box

    # frame (subtle, so the mark reads as artwork on an artboard)
    L.rect([ax - 6, ay - 6, aw + 12, ah + 12], fill="none", radius=14,
           stroke="coolline", stroke_style={"stroke_width": 1, "stroke_dasharray": [3, 4]},
           decorative=True)

    # --- layer: sun (amber, behind peaks) ---
    scx, scy = ax + SUN_C[0] * aw, ay + SUN_C[1] * ah
    sr = SUN_R * aw
    L.ellipse([scx, scy], sr, sr,
              fill=lg([scx - sr, scy - sr], [scx + sr, scy + sr],
                      [(0, "amber2"), (1, "amber")]))
    L.ellipse([scx, scy], sr, sr, fill="none", stroke=rgba("#B98705", 0.5),
              stroke_style={"stroke_width": 1})

    # --- layer: back peak (violet) with smooth apex ---
    pa = _poly_px(PEAK_A, box)
    L.polygon(pa, fill=lg([pa[0][0], pa[0][1]], [pa[1][0], pa[2][1]],
                          [(0, "violet2"), (1, "violet")]))
    # --- layer: front peak (blue) + snow facet highlight ---
    pb = _poly_px(PEAK_B, box)
    L.polygon(pb, fill=lg([pb[0][0], pb[0][1]], [pb[2][0], pb[2][1]],
                          [(0, "blue2"), (1, "blue")]))
    apex = pb[0]
    L.polygon([apex, [apex[0] - 0.09 * aw, apex[1] + 0.16 * ah],
               [apex[0] + 0.02 * aw, apex[1] + 0.13 * ah]],
              fill=rgba("#FFFFFF", 0.85))

    # --- layer: ground band (charcoal, rounded) ---
    gy0, gy1 = ay + GROUND[0] * ah, ay + GROUND[1] * ah
    L.rect([ax + 0.12 * aw, gy0, 0.80 * aw, gy1 - gy0], fill="ground",
           radius=(gy1 - gy0) / 2)

    # editable-vector cues: anchor squares + one bezier handle on the front peak
    if show_editing:
        for vx, vy in pb:
            L.rect([vx - 3, vy - 3, 6, 6], fill="paper", stroke="blue",
                   stroke_style={"stroke_width": 1.4}, decorative=True)
        hx, hy = apex
        L.line([hx, hy], [hx - 26, hy - 14], stroke=rgba("#3B6EF2", 0.8),
               stroke_style={"stroke_width": 1}, decorative=True)
        L.ellipse([hx - 26, hy - 14], 3, 3, fill="paper", stroke="blue",
                  stroke_style={"stroke_width": 1.4}, decorative=True)
        L.line([hx, hy], [hx + 26, hy - 14], stroke=rgba("#3B6EF2", 0.8),
               stroke_style={"stroke_width": 1}, decorative=True)
        L.ellipse([hx + 26, hy - 14], 3, 3, fill="paper", stroke="blue",
                  stroke_style={"stroke_width": 1.4}, decorative=True)

    # crisp wordmark
    ty = ay + ah + 16
    L.text([ax - 12, ty, aw + 24, 24], "APEX BUILD", style="mark")
    L.text([ax - 12, ty + 27, aw + 24, 14], "C O N S T R U C T I O N", style="markSub")


# --------------------------------------------------------------------------- #
# Pipeline step icons (primitive line-art, 24x24 nominal, centered on cx,cy)
# --------------------------------------------------------------------------- #
def _stroke(w=1.8, cap="round", join="round"):
    return {"stroke_width": w, "stroke_linecap": cap, "stroke_linejoin": join}


def icon_upload(L, cx, cy, col):
    L.rect([cx - 12, cy + 3, 24, 9], fill="none", radius=2, stroke=col, stroke_style=_stroke())
    L.line([cx, cy + 7], [cx, cy - 11], stroke=col, stroke_style=_stroke())
    L.line([cx, cy - 11], [cx - 6, cy - 5], stroke=col, stroke_style=_stroke())
    L.line([cx, cy - 11], [cx + 6, cy - 5], stroke=col, stroke_style=_stroke())


def icon_analyze(L, cx, cy, col):
    L.ellipse([cx - 2, cy - 2], 8, 8, fill="none", stroke=col, stroke_style=_stroke())
    L.line([cx + 4, cy + 4], [cx + 11, cy + 11], stroke=col, stroke_style=_stroke(2.2))
    for dx, dy in ((-4, -2), (-1, 1), (2, -3)):
        L.ellipse([cx - 2 + dx, cy - 2 + dy], 1.2, 1.2, fill=col)


def icon_rebuild(L, cx, cy, col):
    pts = [[cx, cy - 11], [cx + 10, cy - 4], [cx + 10, cy + 7],
           [cx, cy + 12], [cx - 10, cy + 7], [cx - 10, cy - 4]]
    L.polygon(pts, fill="none", stroke=col, stroke_style=_stroke())
    for p in pts:
        L.rect([p[0] - 2, p[1] - 2, 4, 4], fill="paper", stroke=col, stroke_style=_stroke(1.4))


def icon_review(L, cx, cy, col):
    L.polygon([[cx - 11, cy - 8], [cx + 11, cy - 8], [cx + 11, cy + 5],
               [cx - 5, cy + 5], [cx - 9, cy + 10], [cx - 9, cy + 5], [cx - 11, cy + 5]],
              fill="none", stroke=col, stroke_style=_stroke())
    L.line([cx - 6, cy - 1.5], [cx - 2, cy + 2], stroke=col, stroke_style=_stroke(2.0))
    L.line([cx - 2, cy + 2], [cx + 6, cy - 5], stroke=col, stroke_style=_stroke(2.0))


def icon_export(L, cx, cy, col):
    L.path(f"M {cx-9} {cy-11} L {cx+4} {cy-11} L {cx+9} {cy-6} L {cx+9} {cy+11} "
           f"L {cx-9} {cy+11} Z", fill="none", stroke=col, stroke_style=_stroke())
    L.line([cx + 4, cy - 11], [cx + 4, cy - 6], stroke=col, stroke_style=_stroke())
    L.line([cx + 4, cy - 6], [cx + 9, cy - 6], stroke=col, stroke_style=_stroke())
    L.line([cx, cy - 3], [cx, cy + 7], stroke=col, stroke_style=_stroke())
    L.line([cx, cy + 7], [cx - 4, cy + 3], stroke=col, stroke_style=_stroke())
    L.line([cx, cy + 7], [cx + 4, cy + 3], stroke=col, stroke_style=_stroke())


PIPELINE = [
    ("Upload reference", "Drop a logo, sketch, scan\nor low-res bitmap.", icon_upload, "warm"),
    ("Analyze shapes", "AI detects regions, edges\nand colour clusters.", icon_analyze, "blue"),
    ("Rebuild as primitives", "Traced into clean paths,\nfills and named layers.", icon_rebuild, "violet"),
    ("Human review", "A designer verifies and\ncorrects every result.", icon_review, "ink"),
    ("Export final assets", "Ship SVG, PDF, PNG\nand HTML from one source.", icon_export, "ok"),
]


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="AI-Assisted Vectorization Workflow",
                          profile="diagram", lang="en")
    for name, value in COLORS.items():
        doc.define_color(name, value)
    for name, style in STYLES.items():
        doc.define_text_style(name, **style)

    page = doc.page("vectorization", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")

    # ---- layout bands --------------------------------------------------- #
    HERO_Y = 34
    BA_Y, BA_H = 156, 356          # before/after band
    PIPE_Y, PIPE_H = 528, 136      # workflow pipeline
    BOT_Y, BOT_H = 676, 292        # api card + value cards

    # ============================ background ============================= #
    bg = page.layer("background")
    bg.rect([0, 0, W, H], fill=lg([0, 0], [0, H], [(0, "bg"), (1, "bg2")]))
    # faint dot grid
    with bg.bleed():
        for gy in range(0, H, 34):
            for gx in range(0, W, 34):
                bg.ellipse([gx, gy], 0.9, 0.9, fill=rgba("#000000", 0.035), decorative=True)
    # soft accent glows top-corners
    bg.ellipse([W - 120, 60], 360, 360,
               fill=rg("50% 50%", [(0, rgba("#6D4EF2", 0.10)), (1, rgba("#6D4EF2", 0))]),
               decorative=True)
    bg.ellipse([120, 120], 320, 320,
               fill=rg("50% 50%", [(0, rgba("#F0603A", 0.07)), (1, rgba("#F0603A", 0))]),
               decorative=True)

    # ================================ hero =============================== #
    hero = page.layer("hero")
    # brand lockup: small peak glyph + wordmark
    gx, gy = M + 4, HERO_Y + 4
    hero.polygon([[gx, gy + 20], [gx + 9, gy + 4], [gx + 18, gy + 20]], fill="violet")
    hero.polygon([[gx + 11, gy + 20], [gx + 18, gy + 9], [gx + 25, gy + 20]], fill="blue")
    hero.ellipse([gx + 22, gy + 6], 4, 4, fill="amber")
    hero.text([gx + 34, gy + 4, 240, 18], "VECTORFORGE", style="brand")
    hero.text([gx + 34, gy + 22, 260, 14], "raster → editable vector, reviewed",
              style=dict(font_family=SANS, font_size=10.5, font_weight=600,
                         color="faint", align="left", letter_spacing=1.2))
    # top-right badge
    badge_txt = "Python SDK · MCP · SVG / PDF / PNG / HTML export"
    bwd = tw(badge_txt, 12, 700) + 44
    card(hero, [W - M - bwd, HERO_Y + 6, bwd, 30], radius=15,
         fill="paper", border="coolline", sh=None)
    hero.ellipse([W - M - bwd + 18, HERO_Y + 21], 3.4, 3.4, fill="violet")
    hero.text([W - M - bwd + 28, HERO_Y + 13, bwd, 16], badge_txt, style="badge")

    # headline + subtitle
    hero.text([M, HERO_Y + 54, 980, 46], "AI-Assisted Vectorization Workflow", style="h1")
    hero.text([M, HERO_Y + 98, 900, 22],
              "Turn low-quality logos, sketches, and bitmap artwork into editable "
              "SVG/PDF assets — with human review.", style="sub")

    # ========================= before / after ============================ #
    baL = page.layer("before_after_panel")
    baL.text([M, BA_Y - 4, 400, 16], "BEFORE  /  AFTER", style="seclabel")
    baL.text([M + 148, BA_Y - 3, 500, 16], "one mark, reconstructed",
             style=dict(font_family=SANS, font_size=11, font_weight=500,
                        color="faint", align="left", letter_spacing=0.4))

    pan_y = BA_Y + 22
    pan_h = BA_H - 22
    pan_w = 592
    lx = M
    rx = W - M - pan_w
    midx = (lx + pan_w + rx) / 2

    # Input panel (warm)
    card(baL, [lx, pan_y, pan_w, pan_h], radius=18,
         fill=lg([lx, pan_y], [lx, pan_y + pan_h], [(0, "#FFF9F6"), (1, "#FCEDE6")]),
         border="warmline", sh="soft")
    # tag + title row
    tag_w = tw("INPUT", 12, 800) + 26
    baL.rect([lx + 22, pan_y + 20, tag_w, 22], fill="warm", radius=11)
    baL.text([lx + 22, pan_y + 25, tag_w, 14], "INPUT", style="panelTag")
    baL.text([lx + 22 + tag_w + 12, pan_y + 18, 300, 20], "Low-res JPG upload", style="panelTitle")
    baL.text([lx + 22 + tag_w + 12, pan_y + 40, 320, 14],
             "apex-logo.jpg · 240 × 240 px · 72 dpi", style="panelSub")

    # Output panel (cool)
    card(baL, [rx, pan_y, pan_w, pan_h], radius=18,
         fill=lg([rx, pan_y], [rx, pan_y + pan_h], [(0, "#FAF8FF"), (1, "#F1EDFF")]),
         border="coolline", sh="soft")
    tag_w2 = tw("OUTPUT", 12, 800) + 26
    baL.rect([rx + 22, pan_y + 20, tag_w2, 22], fill="violet", radius=11)
    baL.text([rx + 22, pan_y + 25, tag_w2, 14], "OUTPUT", style="panelTag")
    baL.text([rx + 22 + tag_w2 + 12, pan_y + 18, 320, 20], "Editable vector asset", style="panelTitle")
    baL.text([rx + 22 + tag_w2 + 12, pan_y + 40, 340, 14],
             "apex-logo.svg · 4 named layers · vector", style="panelSub")

    # center transform node ("AI + human")
    ncy = pan_y + pan_h / 2
    baL.ellipse([midx, ncy], 58, 58,
                fill=rg("50% 50%", [(0, rgba("#6D4EF2", 0.26)), (0.6, rgba("#3B6EF2", 0.10)),
                                    (1, rgba("#3B6EF2", 0))]), decorative=True)
    baL.ellipse([midx, ncy], 30, 30,
                fill=lg([midx - 30, ncy - 30], [midx + 30, ncy + 30], [(0, "violet2"), (1, "blue")]),
                **effects(shadow=shadow(dy=6, blur=18, color="#4A3AD0", opacity=0.4)))
    baL.ellipse([midx, ncy], 30, 30, fill="none", stroke=rgba("#FFFFFF", 0.6),
                stroke_style={"stroke_width": 1})
    # tiny "vector" glyph inside node
    baL.line([midx - 9, ncy + 7], [midx - 2, ncy - 8], stroke="paper", stroke_style=_stroke(2.2))
    baL.line([midx - 2, ncy - 8], [midx + 9, ncy + 2], stroke="paper", stroke_style=_stroke(2.2))
    for px, py in ((midx - 9, ncy + 7), (midx - 2, ncy - 8), (midx + 9, ncy + 2)):
        baL.rect([px - 2.4, py - 2.4, 4.8, 4.8], fill="paper")
    baL.text([midx - 60, ncy + 40, 120, 14], "AI + human",
             style=dict(font_family=SANS, font_size=10, font_weight=700,
                        color="violet", align="center", letter_spacing=0.6))
    arrow(baL, lx + pan_w + 8, ncy, midx - 34, ncy, color="warm2", width=2.0, head=7)
    arrow(baL, midx + 34, ncy, rx - 8, ncy, color="violet", width=2.0, head=7)

    # artwork boxes (square, centered in each panel's body)
    art = 168
    art_lx = lx + (pan_w - art) / 2 - 6
    art_rx = rx + (pan_w - art) / 2 - 6
    art_y = pan_y + 92

    inp = page.layer("input_bitmap_simulation")
    draw_pixel_mark(inp, [art_lx, art_y, art, art])

    outp = page.layer("output_vector_reconstruction")
    draw_vector_mark(outp, [art_rx, art_y, art, art])

    # ========================= workflow pipeline ========================= #
    pipe = page.layer("workflow_pipeline")
    pipe.text([M, PIPE_Y - 2, 400, 16], "WORKFLOW", style="seclabel")
    pipe.text([M + 108, PIPE_Y - 1, 500, 16], "five steps, AI-assisted with a human in the loop",
              style=dict(font_family=SANS, font_size=11, font_weight=500,
                         color="faint", align="left", letter_spacing=0.4))

    n = len(PIPELINE)
    gap = 20
    step_w = (CW - gap * (n - 1)) / n
    step_y = PIPE_Y + 24
    step_h = PIPE_H - 24
    centers = []
    for i, (title, body, icon, col) in enumerate(PIPELINE):
        sx = M + i * (step_w + gap)
        cbox = [sx, step_y, step_w, step_h]
        card(pipe, cbox, radius=14, fill="paper", border="hair", sh="soft")
        # children clipped to the card: a card is a container here, not just a
        # rect drawn behind free-floating text — nothing can leak past its edge.
        with pipe.grouped(clip=clip_rect(cbox)) as g:
            g.rect([sx + 16, step_y + 16, 40, 40], fill=rgba(COLORS[col], 0.10), radius=11,
                   decorative=True)  # background swatch under the icon glyph
            icon(g, sx + 36, step_y + 36, col)
            g.ellipse([sx + step_w - 22, step_y + 20], 10, 10, fill=col)
            g.text([sx + step_w - 32, step_y + 14, 20, 14], str(i + 1), style="stepNum")
            g.text([sx + 16, step_y + 60, step_w - 30, 18], title, style="stepTitle")
            g.text([sx + 16, step_y + 80, step_w - 26, 30], body, style="stepBody")
        centers.append((sx + step_w, step_y + step_h / 2))
    # connectors between steps
    for i in range(n - 1):
        cxp, cyp = centers[i]
        arrow(pipe, cxp + 2, cyp, cxp + gap - 2, cyp, color="faint", width=1.5, head=5)

    # ===================== bottom: API card + value cards ================ #
    api_w = 548
    apiL = page.layer("api_flow_card")
    card(apiL, [M, BOT_Y, api_w, BOT_H], radius=18, fill="dark", border="darkln", sh="lift")
    ax0 = M
    apiL.text([ax0 + 26, BOT_Y + 22, 300, 18], "Possible API flow",
              style=dict(font_family=SANS, font_size=17, font_weight=700,
                         color="paper", align="left", letter_spacing=-0.2))
    apiL.text([ax0 + 26, BOT_Y + 46, 360, 14], "REST + MCP · async job with a review gate",
              style="apiNote")
    apiL.line([ax0 + 26, BOT_Y + 70, ], [ax0 + api_w - 26, BOT_Y + 70], stroke="darkln",
              stroke_style={"stroke_width": 1})

    rows = [
        ("POST", "warm", "/vectorize", "upload artwork → returns job id", True),
        ("GET", "blue", "/jobs/{id}/preview", "render vector preview (SVG/PNG)", True),
        ("POST", "violet", "/jobs/{id}/corrections", "request human corrections", True),
        ("POST", "ok", "/jobs/{id}/approve", "designer approves result", False),
        ("GET", "faint", "/jobs/{id}/export", "download SVG · PDF · PNG · HTML", False),
    ]
    ry = BOT_Y + 84
    row_h = 34
    for i, (method, mcol, path, note, arr) in enumerate(rows):
        apiL.rect([ax0 + 26, ry, api_w - 52, row_h - 6], fill=rgba("#FFFFFF", 0.03),
                  radius=8, stroke="darkln", stroke_style={"stroke_width": 1})
        mw = tw(method, 11, 800) + 18
        apiL.rect([ax0 + 36, ry + (row_h - 6 - 18) / 2, mw, 18], fill=mcol, radius=5)
        apiL.text([ax0 + 36, ry + (row_h - 6 - 13) / 2, mw, 14], method, style="apiMethod")
        apiL.text([ax0 + 36 + mw + 10, ry + (row_h - 6 - 14) / 2, 220, 16], path, style="apiPath")
        apiL.text([ax0 + api_w - 52 - 6 - 210, ry + (row_h - 6 - 12) / 2 + 1, 210, 14], note,
                  style=dict(font_family=SANS, font_size=10, font_weight=500,
                             color="#8A8FA6", align="right", letter_spacing=0.1))
        ry += row_h
    apiL.text([ax0 + 26, BOT_Y + BOT_H - 22, api_w - 52, 14],
              "Every job passes a human-review gate before export — AI-assisted, not automatic.",
              style="apiNote")

    # value proposition cards (3, stacked in the right column)
    valL = page.layer("value_cards")
    val_x = M + api_w + 32
    val_w = W - M - val_x
    vgap = 14
    vh = (BOT_H - vgap * 2) / 3
    VALUES = [
        ("FOR VECTORIZATION SERVICES", "Scale your redraw desk",
         "Reduce repetitive redraw work while keeping human quality control on every asset.",
         "violet", icon_rebuild),
        ("FOR GRAPHIC RESOURCE SITES", "Editable previews on demand",
         "Generate editable previews, templates, and production-ready derivatives at catalogue scale.",
         "blue", icon_analyze),
        ("FOR PRINT · SIGNAGE · APPAREL", "Geometry that scales cleanly",
         "Deliver clean geometry, scalable artwork, and consistent exports across every medium.",
         "ok", icon_export),
    ]
    for i, (kick, title, body, col, icon) in enumerate(VALUES):
        vy = BOT_Y + i * (vh + vgap)
        card(valL, [val_x, vy, val_w, vh], radius=16, fill="paper", border="hair", sh="soft")
        # accent rail
        valL.rect([val_x, vy + 14, 4, vh - 28], fill=col, radius=2)
        valL.rect([val_x + 22, vy + (vh - 42) / 2, 42, 42], fill=rgba(COLORS[col], 0.10), radius=12)
        icon(valL, val_x + 43, vy + vh / 2, col)
        tx = val_x + 82
        valL.text([tx, vy + 16, val_w - tx + val_x - 20, 14], kick,
                  style=dict(font_family=SANS, font_size=10, font_weight=700,
                             color=col, align="left", letter_spacing=1.1))
        valL.text([tx, vy + 34, val_w - tx + val_x - 20, 18], title, style="valTitle")
        valL.text([tx, vy + 55, val_w - tx + val_x - 20, 34], body, style="valBody")

    # =============================== annotations ========================= #
    ann = page.layer("annotations")

    def tag(x, y, text, style, side="left", to=None, col="faint"):
        wd = tw(text, 11.5, 700) + 16
        bx = x if side == "left" else x - wd
        ann.rect([bx, y, wd, 20], fill="paper", radius=6, stroke="hair2",
                 stroke_style={"stroke_width": 1},
                 **effects(shadow=shadow(dy=3, blur=8, color="#000000", opacity=0.08)))
        ann.text([bx + 8, y + 3.5, wd, 14], text, style=style)
        if to:
            ann.ellipse([to[0], to[1]], 2.4, 2.4, fill=col)
            sxp = bx + (wd if side == "left" else 0)
            arrow(ann, sxp, y + 10, to[0], to[1], color=col, width=1.2, head=4)
        return bx

    # input annotations (warm) — point at the pixel mark
    ilx, ily = art_lx, art_y
    tag(lx + 18, art_y - 2, "low-res JPG", "annoWarm", side="left",
        to=(ilx + art * 0.30, ily + art * 0.20), col="warm2")
    tag(lx + 18, art_y + art * 0.55, "background noise", "annoWarm", side="left",
        to=(ilx + art * 0.14, ily + art * 0.85), col="warm2")
    tag(lx + pan_w - 18, art_y + 30, "jagged edges", "annoWarm", side="right",
        to=(ilx + art * 0.80, ily + art * 0.34), col="warm2")
    tag(lx + pan_w - 18, art_y + art * 0.62, "missing detail", "annoWarm", side="right",
        to=(ilx + art * 0.66, ily + art * 0.72), col="warm2")

    # output annotations (ok/violet) — point at the vector mark
    orx, ory = art_rx, art_y
    tag(rx + 18, art_y - 2, "clean paths", "annoOk", side="left",
        to=(orx + art * 0.30, ory + art * 0.34), col="ok")
    tag(rx + 18, art_y + art * 0.55, "editable layers", "annoOk", side="left",
        to=(orx + art * 0.30, ory + art * 0.72), col="ok")
    tag(rx + pan_w - 18, art_y + 30, "print-ready SVG", "annoOk", side="right",
        to=(orx + art * 0.70, ory + art * 0.30), col="ok")
    tag(rx + pan_w - 18, art_y + art * 0.62, "export PDF / PNG", "annoOk", side="right",
        to=(orx + art * 0.85, ory + art * 0.70), col="ok")

    # footer note
    ann.text([M, H - 24, 900, 14],
             "Built with FrameForge primitives — the bitmap on the left is vector-simulated, not an imported raster.",
             style="foot")
    ann.text([W - M - 400, H - 24, 400, 14],
             "AI-assisted · human-reviewed · not fully automatic",
             style=dict(font_family=SANS, font_size=11, font_weight=600,
                        color="violet", align="right", letter_spacing=0.2))

    return doc


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warns)}")
    for i in errors[:30]:
        print(f"  [ERROR] [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:8]:
        print(f"  [warn] [{i.rule_id}] {i.path}: {i.message}")

    # Verification gate (PALS's law): the renderer never silently drops text —
    # it reports overflow as telemetry. `visible_overflow`/`uncontained` are the
    # ones that actually paint past a box; treat any as a leak to investigate.
    svgs, tstats = render_pages_with_stats(doc)
    leak = tstats.get("visible_overflow", 0) + tstats.get("uncontained", 0)
    print(f"text: total={tstats['total']} contained={tstats['contained']} "
          f"wrapped={tstats['wrapped']} clipped={tstats['clipped']} "
          f"visible_overflow={tstats['visible_overflow']} uncontained={tstats['uncontained']}"
          + ("  <-- LEAK" if leak else "  (no visible leaks)"))

    out_svg = os.path.join(ROOT, "vectorization-workflow.svg")
    with open(out_svg, "w", encoding="utf-8") as fh:
        fh.write(svgs[0])
    print(f"Wrote {out_svg}")

    out_yaml = os.path.join(ROOT, "vectorization-workflow.fg.yaml")
    with open(out_yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out_yaml}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
