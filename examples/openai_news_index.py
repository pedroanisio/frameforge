#!/usr/bin/env python3
"""High-fidelity vector recreation of the OpenAI news/index screenshot using the
FrameGraph SDK.

The page, top to bottom:

  1. Nav bar      — "OpenAI" wordmark, six section links, a search glyph, a light
                    "Log in" pill and a black "Try ChatGPT" button.
  2. Hero feature — a large rounded image tile (a stylised event-site + finance
                    dashboard collage: periwinkle panel with cropped headline text,
                    a green dot scatter, big stat numbers and a deep-blue block on
                    the left; a vivid purple "[Sites] in (C…" panel on the right; a
                    floating "ELEVATE / Financial Landscape / $430K" browser card
                    straddling the two), then the article title "Codex for every
                    role, tool, and workflow" and a "Product · 7 min read" caption.
  3. Right rail   — three stacked article cards (orange "Daybreak", coral "Improving
                    health intelligence in ChatGPT", and a sky-blue "Better memory"
                    card cropped by the fold), each a gradient image + title + meta.

Everything lowers to SDK primitives (rect / ellipse / polygon / line / path /
text) with linear/radial gradients and rounded-rect clip paths. Brand wordmarks
(OpenAI, ELEVATE, Daybreak, …) are set as plain text; no logos are reproduced.

Run from the repository root::

    uv run python examples/openai_news_index.py
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    linear_gradient,
    measure_text,
    radial_gradient,
    rgba,
)
from framegraph.sdk.clip import clip_path  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas (the displayed screenshot size — coordinates map straight off the image)
# --------------------------------------------------------------------------- #
W, H = 2000, 1302

COLORS = {
    "page":      "#FFFFFF",
    "ink":       "#0D0D0D",
    "nav":       "#1A1A1A",
    "meta":      "#1A1A1A",
    "metasub":   "#9B9B9B",
    "loginbg":   "#ECECEC",
    "black":     "#0D0D0D",
    "white":     "#FFFFFF",
    # hero — periwinkle panel
    "peri":      "#AEB4EF",
    "peri_lt":   "#C2C7F4",
    "navy":      "#23259A",
    "navy_dk":   "#1B1C7E",
    "blueblock": "#3437EE",
    "green":     "#73B985",
    "green_dk":  "#5BA571",
    # hero — purple panel
    "purple":    "#7C5CFF",
    "purple_lt": "#9070FF",
    "purple_dk": "#6A47F2",
    # browser card
    "card":      "#FBFAFF",
    "indigo":    "#2E2270",
    "indigo2":   "#4A3AA8",
    "lilac":     "#6B5BC9",
    "chrome":    "#C9C9D6",
    # rail cards
    "orange":    "#FF9D4D",
    "amber":     "#FFC766",
    "coral":     "#F4B7A6",
    "rose":      "#EFB6C9",
    "sky":       "#BFE2F4",
    "sky_dk":    "#7FC2EC",
    "footbg":    "#F2F2F2",
    "footink":   "#7A7A7A",
}

SANS = ["Helvetica Neue", "Inter", "Arial", "DejaVu Sans", "sans-serif"]


def _ts(size, weight=400, color="ink", align="left", ls=0.0, lh=1.25):
    return dict(font_family=SANS, font_size=size, font_weight=weight, color=color,
                align=align, letter_spacing=ls, line_height=lh)


STYLES = {
    "logo":     _ts(27, 700, "ink", "left", -0.3),
    "nav":      _ts(18, 400, "nav", "left"),
    "login":    _ts(17, 500, "ink", "center"),
    "trybtn":   _ts(17, 500, "white", "center"),
    "heroH":    _ts(53, 400, "ink", "left", -0.8, 1.06),
    "metaCat":  _ts(18, 500, "meta", "left"),
    "metaSub":  _ts(18, 400, "metasub", "left"),
    "cardH":    _ts(25, 500, "ink", "left", -0.2, 1.2),
    # hero collage type
    "crop":     _ts(74, 700, "navy", "left", -1.5, 1.0),
    "statnum":  _ts(40, 700, "navy", "left", -0.5),
    "sitesfaint": dict(font_family=SANS, font_size=86, font_weight=700,
                       color=rgba("#FFFFFF", 0.16), align="left", letter_spacing=-1.0,
                       line_height=1.05),
    "elevate":  _ts(31, 600, "indigo2", "left", 7.0),
    "wnav":     _ts(20, 500, "indigo2", "left"),
    "finance":  _ts(82, 700, "indigo", "left", -2.0, 0.98),
    "subline":  _ts(26, 400, "lilac", "left", -0.2),
    "oplabel":  _ts(17, 600, "lilac", "left", 1.0),
    "opval":    _ts(44, 700, "indigo", "left", -1.0),
    "tinypill": _ts(15, 600, "navy_dk", "left", 0.5),
    "footword": _ts(15, 600, "footink", "left", 0.5),
    "footnav":  _ts(15, 600, "navy_dk", "left", 1.0),
    # white text inside rail images
    "railimgH": _ts(34, 600, "white", "left", -0.4, 1.12),
}

# --------------------------------------------------------------------------- #
# Paint + geometry helpers
# --------------------------------------------------------------------------- #
def lg(p0, p1, stops):
    ang = round(math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])), 1)
    return linear_gradient([(c, p) for (p, c) in stops], angle=ang)


def rg(at, stops, shape="circle"):
    return radial_gradient([(c, p) for (p, c) in stops], at=at, shape=shape)


def rrect(x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    return (f"M{x + r},{y} H{x + w - r} A{r},{r} 0 0 1 {x + w},{y + r} "
            f"V{y + h - r} A{r},{r} 0 0 1 {x + w - r},{y + h} "
            f"H{x + r} A{r},{r} 0 0 1 {x},{y + h - r} "
            f"V{y + r} A{r},{r} 0 0 1 {x + r},{y} Z")


def tw(text, size, weight=400):
    return measure_text(text, font_family=SANS, font_size=size, bold=weight >= 600)


# --------------------------------------------------------------------------- #
# 1. NAV BAR
# --------------------------------------------------------------------------- #
def search_glyph(layer, cx, cy):
    layer.ellipse([cx, cy], 9, 9, fill="none", stroke="nav",
                  stroke_style={"stroke_width": 2})
    layer.line([cx + 6.5, cy + 6.5], [cx + 12, cy + 12], stroke="nav",
               stroke_style={"stroke_width": 2, "stroke_linecap": "round"})


def chevron(layer, cx, cy, color="ink", s=4.5, up=False):
    dy = -s if up else s
    layer.line([cx - s, cy - dy / 2], [cx, cy + dy / 2], stroke=color,
               stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})
    layer.line([cx, cy + dy / 2], [cx + s, cy - dy / 2], stroke=color,
               stroke_style={"stroke_width": 1.6, "stroke_linecap": "round"})


def arrow_ne(layer, x, y, color="white", s=11):
    layer.line([x, y + s], [x + s, y], stroke=color,
               stroke_style={"stroke_width": 2, "stroke_linecap": "round"})
    layer.line([x + 1.5, y], [x + s, y], stroke=color,
               stroke_style={"stroke_width": 2, "stroke_linecap": "round"})
    layer.line([x + s, y], [x + s, y + s - 1.5], stroke=color,
               stroke_style={"stroke_width": 2, "stroke_linecap": "round"})


def nav(layer):
    cy = 35
    layer.text([88, cy - 13, 200, 30], "OpenAI", style="logo")
    links = [("Research", 226), ("Products", 338), ("Business", 452),
             ("Developers", 564), ("Company", 692), ("Foundation", 808)]
    for label, x in links:
        layer.text([x, cy - 10, 160, 24], label, style="nav")
    search_glyph(layer, 942, cy)

    # "Try ChatGPT" black button, right aligned
    tlabel = "Try ChatGPT"
    tw_t = tw(tlabel, 17, 500)
    bw = tw_t + 36 + 22
    bx = 1908 - bw
    by, bh = 12, 46
    layer.rect([bx, by, bw, bh], fill="black", radius=23)
    layer.text([bx + 22, by + (bh - 22) / 2, tw_t + 6, 22], tlabel, style="trybtn")
    arrow_ne(layer, bx + 22 + tw_t + 9, by + bh / 2 - 6)

    # "Log in" pill to its left
    llabel = "Log in"
    tw_l = tw(llabel, 17, 500)
    lw = tw_l + 30 + 22
    lx = bx - 18 - lw
    layer.rect([lx, by, lw, bh], fill="loginbg", radius=23)
    layer.text([lx + 18, by + (bh - 22) / 2, tw_l + 6, 22], llabel, style="login")
    chevron(layer, lx + 18 + tw_l + 14, by + bh / 2, color="ink")


# --------------------------------------------------------------------------- #
# 2. HERO IMAGE COLLAGE
# --------------------------------------------------------------------------- #
def green_scatter(layer, x0, y0, w, h):
    rnd = random.Random(73)
    cx, cy = x0 + w * 0.46, y0 + h * 0.5
    for _ in range(150):
        a = rnd.uniform(0, math.tau)
        rr = rnd.random() ** 0.5
        px = cx + math.cos(a) * rr * w * 0.52 + rnd.uniform(-10, 10)
        py = cy + math.sin(a) * rr * h * 0.55
        if px < x0 - 8 or py < y0 - 8 or py > y0 + h + 8:
            continue
        rad = rnd.uniform(4.5, 8.5)
        col = "green" if rnd.random() < 0.7 else "green_dk"
        layer.ellipse([px, py], rad, rad, fill=col, decorative=True)


def browser_card(layer, x, y, w, h):
    # window body + soft drop shadow
    layer.rect([x + 6, y + 16, w, h], fill=rgba("#2A1E5E", 0.18), radius=20,
               decorative=True)
    layer.rect([x, y, w, h], fill="card", radius=20)
    # title bar dots
    for i, dx in enumerate((34, 60, 86)):
        layer.ellipse([x + dx, y + 30], 8, 8, fill="chrome")
    # brand orb + wordmark
    ox, oy = x + 56, y + 118
    layer.ellipse([ox, oy], 30, 30,
                  fill=rg("38% 32%", [(0.0, "#C9A8FF"), (0.55, "#9A6CFF"),
                                      (1.0, "#6A3CE0")]))
    layer.ellipse([ox - 8, oy - 9], 9, 9, fill=rgba("#FFFFFF", 0.55),
                  decorative=True)
    layer.text([x + 98, y + 100, 280, 38], "ELEVATE", style="elevate")
    # top-right nav
    wnav = [("Overview", x + 520, True), ("Reports", x + 690, False),
            ("Forecast", x + 838, False), ("An", x + 1000, False)]
    for label, nx, active in wnav:
        layer.text([nx, y + 102, 180, 26], label, style="wnav")
        if active:
            ww = tw(label, 20, 500)
            layer.line([nx, y + 134], [nx + ww, y + 134], stroke="indigo2",
                       stroke_style={"stroke_width": 2})
    # big heading
    layer.text([x + 56, y + 196, 620, 190], "Financial\nLandscape", style="finance")
    # subtitle
    layer.text([x + 58, y + 384, 640, 34], "See the big picture. Make better decisions.",
               style="subline")
    # operating expense block (right)
    layer.text([x + 858, y + 300, 360, 24], "OPERATING EXPEN", style="oplabel")
    layer.text([x + 856, y + 322, 260, 56], "$430K", style="opval")


def hero_collage(layer, box):
    hx, hy, hw, hh = box
    split = hx + int(hw * 0.495)   # periwinkle | purple boundary

    with layer.grouped(clip=clip_path(rrect(hx, hy, hw, hh, 14))) as g:
        with g.bleed():
            # --- left periwinkle panel ---
            g.rect([hx, hy, split - hx, hh],
                   fill=lg([hx, hy], [hx, hy + hh],
                           [(0, "peri_lt"), (1, "peri")]))
            # cropped headline (overflows left edge -> clipped)
            g.text([hx - 248, hy + 78, 860, 84], "together ideas.", style="crop")
            g.text([hx - 124, hy + 196, 760, 84], "together.", style="crop")
            g.text([hx + 12, hy + 300, 400, 26], "on ideas,", style="subline")
            g.text([hx + 12, hy + 332, 400, 26], "build next.", style="subline")
            # "How it works" pill (cropped left)
            g.rect([hx - 44, hy + 396, 150, 40], fill="white", radius=20,
                   stroke="peri", stroke_style={"stroke_width": 1.5})
            g.text([hx + 8, hy + 405, 120, 22], "w it works", style="subline")
            # green dot scatter
            green_scatter(g, hx + 130, hy + 150, 470, 230)
            # big stat numbers
            for label, sx in (("1.2k", 26), ("236", 200), ("78", 360)):
                g.text([hx + sx, hy + 470, 200, 50], label, style="statnum")
            # deep-blue block (lower left, does not reach the bottom)
            g.rect([hx, hy + 524, 386, 168], fill="blueblock")
            # footer nav strip on the periwinkle below the blue block
            fy = hy + hh - 56
            for label, fx in (("ABOUT", 30), ("SPEAKERS", 158), ("FAQ", 360)):
                g.text([hx + fx, fy, 200, 22], label, style="footnav")
            g.rect([hx + 466, fy - 9, 116, 40], fill="navy_dk", radius=8)
            g.text([hx + 492, fy + 1, 100, 22], "RE", style="trybtn")

            # --- right purple panel ---
            g.rect([split, hy, hx + hw - split, hh],
                   fill=lg([split, hy], [hx + hw, hy + hh],
                           [(0, "purple_lt"), (1, "purple_dk")]))
            g.text([split + 24, hy + 60, 900, 110], "[Sites] in (Co", style="sitesfaint")
            g.text([split + 24, hy + 232, 900, 110], "[Sites] in (Co", style="sitesfaint")

            # --- floating browser card straddling the two panels ---
            browser_card(g, hx + 432, hy + 282, 1010, 560)


# --------------------------------------------------------------------------- #
# 3. RIGHT RAIL CARDS
# --------------------------------------------------------------------------- #
def rail_image(layer, box, kind):
    x, y, w, h = box
    clip = clip_path(rrect(x, y, w, h, 14))
    with layer.grouped(clip=clip) as g:
        with g.bleed():
            if kind == "daybreak":
                g.rect([x, y, w, h], fill=lg([x, y], [x + w, y + h],
                       [(0, "amber"), (0.5, "orange"), (1, "#FF8A3D")]))
                g.ellipse([x + w * 0.7, y + h * 0.35], w * 0.5, h * 0.7,
                          fill=rg("50% 50%", [(0, rgba("#FFE6B0", 0.7)),
                                              (1, rgba("#FFE6B0", 0.0))]),
                          decorative=True)
            elif kind == "health":
                g.rect([x, y, w, h], fill=lg([x, y], [x + w, y + h],
                       [(0, "coral"), (1, "rose")]))
                g.ellipse([x + w * 0.5, y + h * 0.42], w * 0.62, h * 0.5,
                          fill=rg("50% 50%", [(0, rgba("#F9D6C8", 0.65)),
                                              (1, rgba("#F9D6C8", 0.0))]),
                          decorative=True)
                g.text([x + 40, y + h * 0.30, w - 80, 160],
                       "Improving\nhealth intelligence\nin ChatGPT", style="railimgH")
            elif kind == "memory":
                g.rect([x, y, w, h], fill=lg([x, y], [x + w, y + h],
                       [(0, "sky"), (1, "sky_dk")]))
                g.ellipse([x + w * 0.55, y + h * 0.4], w * 0.55, h * 0.7,
                          fill=rg("50% 50%", [(0, rgba("#FFFFFF", 0.55)),
                                              (1, rgba("#FFFFFF", 0.0))]),
                          decorative=True)
                g.text([x + 40, y + 44, w - 80, 100], "Better memory for",
                       style="railimgH")


def meta_line(layer, x, y, cat, sub=None):
    layer.text([x, y, 200, 24], cat, style="metaCat")
    if sub:
        cw = tw(cat, 18, 500)
        layer.text([x + cw + 20, y, 200, 24], sub, style="metaSub")


def right_rail(layer, rx, rw):
    # card 1 — Daybreak
    rail_image(layer, [rx, 78, rw, 178], "daybreak")
    layer.text([rx, 282, rw, 100],
               "Daybreak: Tools for securing every\norganization in the world",
               style="cardH")
    meta_line(layer, rx, 392, "Security", "8 min read")

    # card 2 — health intelligence
    rail_image(layer, [rx, 452, rw, 400], "health")
    layer.text([rx, 906, rw, 90],
               "Improving health intelligence\nin ChatGPT", style="cardH")
    meta_line(layer, rx, 1016, "Product")

    # card 3 — memory (cropped by the fold)
    rail_image(layer, [rx, 1096, rw, 240], "memory")


# --------------------------------------------------------------------------- #
# Footer (a sliver at the very bottom, mostly below the fold)
# --------------------------------------------------------------------------- #
def footer(layer):
    layer.rect([0, 1288, W, H - 1288], fill="footbg", decorative=True)
    for i in range(9):
        cx = 1080 + i * 96
        layer.ellipse([cx, 1300], 9, 9, fill="footink", decorative=True)


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="OpenAI — News index recreation",
                          profile="diagram", lang="en")
    for name, value in COLORS.items():
        doc.define_color(name, value)
    for name, style in STYLES.items():
        doc.define_text_style(name, **style)

    page = doc.page("openai_news", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")
    bg = page.layer("bg")
    bg.rect([0, 0, W, H], fill="page")

    layer = page.layer("main")

    nav(layer)

    HERO = (88, 78, 1357, 757)
    hero_collage(layer, HERO)
    layer.text([88, 862, 1357, 70], "Codex for every role, tool, and workflow",
               style="heroH")
    meta_line(layer, 88, 956, "Product", "7 min read")

    right_rail(layer, 1475, 433)

    footer(layer)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "examples", "fixtures", "openai-news-index.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warns)} -> {out}")
    for i in errors[:20]:
        print(f"  [ERROR] [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:6]:
        print(f"  [warn] [{i.rule_id}] {i.path}: {i.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
