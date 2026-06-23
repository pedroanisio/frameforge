#!/usr/bin/env python3
"""THE GREAT REWRITE — a complete storyboard for a 20-minute YouTube documentary
about AI and Workforce Transformation, composed entirely with the FrameGraph SDK.

This is a *production document*, not a comic: a cover / brief, a shot-type legend,
and six storyboard sheets carrying 36 numbered shots that run a tight 20:00. Each
shot cell pairs a real 16:9 styleframe — drawn from geometry, no image assets —
with the metadata a director and editor actually use: timecode, duration, shot
type, camera/motion, the voiceover line, and the on-screen text / lower-third.

The thumbnails are genuine mini-illustrations dispatched by an ``art`` key: host
shots, kinetic title cards, a revolutions timeline, an adoption line chart, a
task-bundle diagram, an automate-vs-augment matrix, a human+AI loop, a sector bar
chart, before/after case cards, an end screen, and more — so every frame on the
board is distinct on a real axis (subject, mechanism, diagrammation), never a
reskin of one template.

Design notes honouring the engine's static rules so the fixture validates clean:
art lives at layer level (where overlap is legal z-order); every glyph run is
wrapped in a one-child group (the ``tabular-box-model`` heuristic only inspects
*layer-level* text, and lettering is gridded by nature); translucent fills are
emitted with ``rgba()`` so the proxy renderer keeps the alpha.

Run from the repository root::

    uv run python examples/ai_workforce_storyboard.py
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
    DocumentBuilder,
    Path,
    column,
    linear_gradient,
    radial_gradient,
    rgba,
    row,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Page + palette
# --------------------------------------------------------------------------- #
W, H = 1600, 1000                       # 16:10 landscape board sheet
CANVAS = {"size": [W, H], "units": "px"}
M = 56

SANS = ["Inter", "Helvetica Neue", "DejaVu Sans", "Arial", "sans-serif"]
SERIF = ["Bitstream Charter", "Noto Serif", "Georgia", "serif"]
MONO = ["DejaVu Sans Mono", "Fira Mono", "monospace"]

C = {
    "ink": "#15181f", "paper": "#f6f4ee", "board": "#e9e6dd", "panel": "#ffffff",
    "frame": "#eef1f6", "frame2": "#e3e8f1", "line": "#c8c3b6", "hair": "#d9d5c9",
    "sub": "#565d68", "muted": "#8b8f99", "ink2": "#2b303a",
    "blue": "#2f6df0", "teal": "#13a99a", "amber": "#e7a23a", "coral": "#e2604f",
    "violet": "#6b4ef0", "rose": "#d6477e", "green": "#3aa564", "ink_blue": "#0f1b3a",
    "white": "#ffffff",
}

# Scene accent cycle — each act gets an identity colour on the board.
SCENE_C = [C["blue"], C["violet"], C["teal"], C["amber"], C["coral"], C["rose"],
           C["green"], C["blue"]]

STYLES = {
    "h1":      dict(font_family=SANS, font_size=82, font_weight=800, color="paper",
                    letter_spacing=-3, line_height=0.92),
    "h1b":     dict(font_family=SANS, font_size=82, font_weight=800, color="amber",
                    letter_spacing=-3, line_height=0.92),
    "kicker":  dict(font_family=MONO, font_size=18, font_weight=700, color="amber",
                    letter_spacing=7, text_transform="uppercase"),
    "kicker_d": dict(font_family=MONO, font_size=13, font_weight=700, color="sub",
                     letter_spacing=4, text_transform="uppercase"),
    "lede":    dict(font_family=SERIF, font_size=22, color="paper", line_height=1.5),
    "meta":    dict(font_family=MONO, font_size=14, color="paper", line_height=1.7,
                    letter_spacing=1),
    "meta_k":  dict(font_family=MONO, font_size=14, color="amber", line_height=1.7,
                    letter_spacing=2, text_transform="uppercase"),
    # board chrome
    "board_t": dict(font_family=SANS, font_size=26, font_weight=800, color="ink",
                    letter_spacing=-0.5),
    "board_s": dict(font_family=MONO, font_size=13, font_weight=700, color="sub",
                    letter_spacing=2, text_transform="uppercase"),
    "folio":   dict(font_family=MONO, font_size=13, color="muted", letter_spacing=2),
    # cell chrome
    "shot_no": dict(font_family=SANS, font_size=22, font_weight=800, color="white",
                    align="center"),
    "tag":     dict(font_family=MONO, font_size=11, font_weight=700, color="white",
                    letter_spacing=1.5, text_transform="uppercase", align="center"),
    "tc":      dict(font_family=MONO, font_size=14, font_weight=700, color="ink",
                    letter_spacing=0.5),
    "dur":     dict(font_family=MONO, font_size=12, color="muted", letter_spacing=0.5),
    "vo":      dict(font_family=SERIF, font_size=14, color="ink2", line_height=1.34),
    "note":    dict(font_family=MONO, font_size=11, color="sub", line_height=1.4,
                    letter_spacing=0.3),
    "note_k":  dict(font_family=MONO, font_size=11, font_weight=700, color="muted",
                    letter_spacing=1, text_transform="uppercase"),
    # in-frame styleframe lettering
    "fbig":    dict(font_family=SANS, font_size=46, font_weight=800, color="ink",
                    letter_spacing=-1.5, align="center", line_height=0.96),
    "fbig_w":  dict(font_family=SANS, font_size=46, font_weight=800, color="white",
                    letter_spacing=-1.5, align="center", line_height=0.96),
    "fmid":    dict(font_family=SANS, font_size=24, font_weight=700, color="ink",
                    align="center", line_height=1.05),
    "fmid_w":  dict(font_family=SANS, font_size=22, font_weight=700, color="white",
                    align="center", line_height=1.08),
    "flbl":    dict(font_family=MONO, font_size=12, font_weight=700, color="sub",
                    letter_spacing=1.5, text_transform="uppercase", align="center"),
    "flbl_l":  dict(font_family=MONO, font_size=12, font_weight=700, color="sub",
                    letter_spacing=1.5, text_transform="uppercase"),
    "fstat":   dict(font_family=SANS, font_size=88, font_weight=800, color="ink",
                    letter_spacing=-4, align="center", line_height=0.9),
    "fchip":   dict(font_family=MONO, font_size=12, font_weight=700, color="ink2",
                    align="center"),
    "fquote":  dict(font_family=SERIF, font_size=24, italic=True, color="ink",
                    line_height=1.25),
    "fattr":   dict(font_family=MONO, font_size=12, font_weight=700, color="sub",
                    letter_spacing=1),
    "ftiny":   dict(font_family=MONO, font_size=9, color="muted", align="center"),
    "lower3":  dict(font_family=SANS, font_size=16, font_weight=800, color="white"),
    "lower3s": dict(font_family=MONO, font_size=10, font_weight=700, color="white",
                    letter_spacing=1.5, text_transform="uppercase"),
}


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def sheet(b, pid, *, bg="board"):
    page = b.page(pid, canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill=C[bg])
    page.layer("art")
    return page


_STYLE_PROPS = {"align", "color", "font_size", "font_weight",
                "letter_spacing", "line_height", "italic", "text_transform"}


def TT(p, box, s, style=None, **fields):
    """One text object wrapped in a one-child group (hidden from the grid audit).

    ``align``/``color`` and friends are text-*style* properties, so any such
    keyword is folded into the style (resolving a named style to a private copy)
    rather than placed on the text object, which forbids them.
    """
    child = {"type": "text", "box": [float(v) for v in box], "text": s}
    overrides = {k: fields.pop(k) for k in list(fields) if k in _STYLE_PROPS
                 and fields[k] is not None}
    if overrides:
        base = dict(STYLES[style]) if isinstance(style, str) else dict(style or {})
        base.update(overrides)
        style = base
    if style is not None:
        child["style"] = style
    child.update(fields)
    p.add({"type": "group", "children": [child]})


def fmt_tc(sec):
    return f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"


def clip(box):
    """A 16:9-ish styleframe clip: cool fill + thin keyline. Returns inner box."""
    return box


def figure(p, cx, base, s, color, *, arms="rest"):
    """A loose storyboard human: head + shoulders, optional gesture. base = chin-down."""
    head_r = 20 * s
    hy = base - 96 * s
    p.circle([cx, hy], head_r, fill=color)
    # shoulders / torso as a rounded trapezoid
    tw, th = 96 * s, 80 * s
    p.path(
        Path().move_to(cx - tw / 2, base)
        .line_to(cx - tw * 0.40, base - th)
        .through([[cx - 24 * s, base - th - 10 * s], [cx + 24 * s, base - th - 10 * s]])
        .line_to(cx + tw * 0.40, base - th)
        .line_to(cx + tw / 2, base).close(),
        fill=color)
    if arms == "present":     # one arm gesturing out
        p.line([cx + tw * 0.34, base - th * 0.7], [cx + tw * 0.9, base - th * 1.05],
               stroke=color, stroke_style={"stroke_width": 9 * s, "stroke_linecap": "round"})


def device_window(p, box, C_, *, title="", accent="blue"):
    """A browser/app chrome window. Returns the content box."""
    x, y, w, h = box
    p.rect(box, fill=C_["white"], stroke=C_["line"], stroke_style={"stroke_width": 1.5},
           radius=8)
    p.rect([x, y, w, 20], fill=C_["frame2"], radius=8)
    for i, col in enumerate((C_["coral"], C_["amber"], C_["green"])):
        p.circle([x + 12 + i * 13, y + 10], 4, fill=col)
    if title:
        TT(p, [x + 60, y + 4, w - 80, 14], title, "ftiny", align="start")
    return [x + 12, y + 30, w - 24, h - 42]


# --------------------------------------------------------------------------- #
# Styleframe painters — each draws inside a 16:9 frame box [x,y,w,h]
# --------------------------------------------------------------------------- #
def _bgfill(p, box, top, bot):
    p.rect(box, fill=linear_gradient([(top, 0), (bot, 1)], angle=160))


def art_host(p, box, *, framing="MS", accent="blue", caption=None, sub=None):
    x, y, w, h = box
    _bgfill(p, box, "#dfe6f2", "#cdd7ea")
    ac = C[accent]
    # vignette / studio pool of light
    p.ellipse([x + w * 0.5, y + h * 0.46], w * 0.42, h * 0.42,
              fill=rgba(C["white"], 0.55), decorative=True)
    scale = {"CU": 1.9, "MCU": 1.5, "MS": 1.15, "WS": 0.8}.get(framing, 1.15)
    figure(p, x + w * 0.42, y + h + (40 if framing == "WS" else 18),
           scale, C["ink_blue"], arms="present" if framing in ("MS", "WS") else "rest")
    # lower third
    lh = 30
    p.rect([x + 14, y + h - lh - 12, w * 0.62, lh], fill=rgba(C["ink"], 0.86), radius=4)
    p.rect([x + 14, y + h - lh - 12, 5, lh], fill=ac)
    if caption:
        TT(p, [x + 28, y + h - lh - 7, w * 0.6, 16], caption, "lower3")
    if sub:
        TT(p, [x + 28, y + h - 24, w * 0.55, 12], sub, "lower3s")
    TT(p, [x + 12, y + 8, 70, 14], framing, "flbl_l")


def art_title(p, box, *, big="TITLE", small="", accent="amber", dark=True):
    x, y, w, h = box
    if dark:
        p.rect(box, fill=linear_gradient([(C["ink"], 0), (C["ink_blue"], 1)], angle=150))
    else:
        _bgfill(p, box, "#f2eee4", "#e6e0d2")
    ac = C[accent]
    p.rect([x + w * 0.5 - 60, y + h * 0.5 - 44, 120, 5], fill=ac)
    TT(p, [x + 20, y + h * 0.5 - 36, w - 40, 70],
       big, "fbig_w" if dark else "fbig")
    if small:
        st = dict(STYLES["flbl"]); st["color"] = "white" if dark else "sub"
        TT(p, [x + 20, y + h * 0.5 + 34, w - 40, 18], small, st)


def art_question(p, box, *, q="?", small="", accent="amber"):
    x, y, w, h = box
    p.rect(box, fill=linear_gradient([(C["ink_blue"], 0), (C["ink"], 1)], angle=160))
    ac = C[accent]
    nlines = q.count("\n") + 1
    fs = 40 if nlines >= 3 else 46
    TT(p, [x + 24, y + 22, w - 48, h - 70], q,
       dict(STYLES["fbig_w"], font_size=fs))
    if small:
        TT(p, [x + 24, y + h - 50, w - 48, 30], small,
           dict(STYLES["fmid_w"], color=accent))
    p.circle([x + w - 40, y + 38], 4, fill=ac, decorative=True)


def art_montage(p, box, *, accent="blue"):
    x, y, w, h = box
    _bgfill(p, box, "#1a2238", "#0f1626")
    cells = []
    cols, rows = 3, 2
    gx, gy = 8, 8
    cw = (w - (cols + 1) * gx) / cols
    ch = (h - (rows + 1) * gy) / rows
    icons = ["screen", "gear", "chat", "doc", "cart", "chart"]
    accents = [C["blue"], C["teal"], C["amber"], C["coral"], C["violet"], C["rose"]]
    k = 0
    for r in range(rows):
        for c in range(cols):
            bx = x + gx + c * (cw + gx)
            by = y + gy + r * (ch + gy)
            p.rect([bx, by, cw, ch], fill=rgba(C["white"], 0.06),
                   stroke=rgba(accents[k], 0.8), stroke_style={"stroke_width": 1.5},
                   radius=4)
            _mini_icon(p, [bx, by, cw, ch], icons[k], accents[k])
            k += 1
    TT(p, [x + 14, y + h - 26, w - 28, 16],
       "FLASH MONTAGE — AI in every desk, dock, clinic", "ftiny", align="start",
       color="white")


def _mini_icon(p, box, kind, col):
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    s = min(w, h) * 0.26
    if kind == "screen":
        p.rect([cx - s, cy - s * 0.7, 2 * s, 1.4 * s], fill=None, stroke=col,
               stroke_style={"stroke_width": 2}, radius=2)
        p.line([cx - s * 0.4, cy + s * 0.7], [cx + s * 0.4, cy + s * 0.7], stroke=col,
               stroke_style={"stroke_width": 2})
    elif kind == "gear":
        for a in range(8):
            ang = math.pi / 4 * a
            p.line([cx + math.cos(ang) * s * 0.7, cy + math.sin(ang) * s * 0.7],
                   [cx + math.cos(ang) * s, cy + math.sin(ang) * s], stroke=col,
                   stroke_style={"stroke_width": 2})
        p.circle([cx, cy], s * 0.55, fill=None, stroke=col, stroke_style={"stroke_width": 2})
    elif kind == "chat":
        p.rect([cx - s, cy - s * 0.7, 2 * s, 1.3 * s], fill=None, stroke=col,
               stroke_style={"stroke_width": 2}, radius=6)
        p.polygon([[cx - s * 0.4, cy + s * 0.6], [cx - s * 0.1, cy + s * 0.6],
                   [cx - s * 0.5, cy + s]], fill=col)
    elif kind == "doc":
        p.rect([cx - s * 0.7, cy - s, 1.4 * s, 2 * s], fill=None, stroke=col,
               stroke_style={"stroke_width": 2}, radius=2)
        for i in range(3):
            p.line([cx - s * 0.4, cy - s * 0.3 + i * s * 0.4],
                   [cx + s * 0.4, cy - s * 0.3 + i * s * 0.4], stroke=col,
                   stroke_style={"stroke_width": 1.5})
    elif kind == "cart":
        p.rect([cx - s * 0.7, cy - s * 0.5, 1.4 * s, s], fill=None, stroke=col,
               stroke_style={"stroke_width": 2})
        p.circle([cx - s * 0.4, cy + s * 0.8], 3, fill=col)
        p.circle([cx + s * 0.4, cy + s * 0.8], 3, fill=col)
    else:  # chart
        for i, hh in enumerate((0.4, 0.8, 0.6)):
            p.rect([cx - s + i * s * 0.8, cy + s - 2 * s * hh, s * 0.5, 2 * s * hh],
                   fill=col)


def art_timeline(p, box, *, accent="violet"):
    x, y, w, h = box
    _bgfill(p, box, "#f1eee6", "#e3ddcf")
    ax_y = y + h * 0.6
    p.line([x + 40, ax_y], [x + w - 30, ax_y], stroke=C["ink"],
           stroke_style={"stroke_width": 2.5})
    nodes = [("STEAM", "1780", C["sub"]), ("ELECTRIC", "1890", C["teal"]),
             ("COMPUTER", "1975", C["blue"]), ("AI", "2023", C["coral"])]
    n = len(nodes)
    for i, (lab, yr, col) in enumerate(nodes):
        nx = x + 60 + i * (w - 110) / (n - 1)
        r = 7 + i * 3
        p.circle([nx, ax_y], r, fill=col)
        TT(p, [nx - 60, ax_y - 44, 120, 16], lab, "flbl")
        TT(p, [nx - 60, y + h - 26, 120, 14], yr, "ftiny")
        if i:
            p.path(Path().move_to(px, ax_y - 30).through(
                [[(px + nx) / 2, ax_y - 30 - 10 * i]]).line_to(nx, ax_y - 30 - 14 * i),
                fill=None, stroke=rgba(col, 0.0))  # spacer (kept invisible)
        px = nx
    # accelerating curve hint above
    TT(p, [x + 30, y + 14, w - 60, 16], "EACH WAVE ARRIVES FASTER", "flbl_l",
       color=accent)


def art_linechart(p, box, *, accent="blue"):
    x, y, w, h = box
    _bgfill(p, box, "#ffffff", "#eef1f6")
    px0, py0 = x + 46, y + 24
    pw, ph = w - 70, h - 64
    for i in range(4):                      # gridlines
        gy = py0 + ph * i / 3
        p.line([px0, gy], [px0 + pw, gy], stroke=C["hair"], stroke_style={"stroke_width": 1})
    p.line([px0, py0], [px0, py0 + ph], stroke=C["sub"], stroke_style={"stroke_width": 1.5})
    p.line([px0, py0 + ph], [px0 + pw, py0 + ph], stroke=C["sub"],
           stroke_style={"stroke_width": 1.5})
    pts = [(0, 0.04), (0.2, 0.07), (0.4, 0.16), (0.55, 0.32), (0.7, 0.58),
           (0.85, 0.82), (1.0, 0.97)]
    poly = [[px0 + pw * t, py0 + ph * (1 - v)] for t, v in pts]
    p.path(Path().move_to(*poly[0]).through([q for q in poly[1:]]),
           fill=None, stroke=C[accent], stroke_style={"stroke_width": 3.5,
                                                       "stroke_linecap": "round"})
    p.circle(poly[-1], 5, fill=C[accent])
    TT(p, [px0, y + 6, pw, 14], "GENERATIVE-AI ADOPTION (users)", "flbl_l")
    TT(p, [px0 + pw - 80, py0 + 4, 80, 12], "2024 →", "ftiny", align="end")


def art_broll(p, box, *, kind="factory", accent="teal"):
    x, y, w, h = box
    _bgfill(p, box, "#dde3ec", "#c6cfdd")
    ground = y + h * 0.74
    p.rect([x, ground, w, h - (ground - y)], fill=rgba(C["ink_blue"], 0.10))
    ink = C["ink_blue"]
    if kind == "factory":
        for i in range(3):
            bx = x + 30 + i * (w - 90) / 3
            bh = (0.5 + 0.15 * i) * (ground - y)
            p.rect([bx, ground - bh, (w - 120) / 3, bh], fill=rgba(ink, 0.65))
            p.rect([bx + 18, ground - bh - 30, 12, 30], fill=rgba(ink, 0.65))  # chimney
        cap = "ARCHIVAL — assembly line → open-plan office (dissolve)"
    elif kind == "office":
        for i in range(4):
            dx = x + 36 + i * (w - 80) / 4
            p.rect([dx, ground - 28, (w - 90) / 4 - 10, 28], fill=rgba(ink, 0.5))  # desk
            figure(p, dx + 22, ground - 28, 0.5, ink)
        cap = "B-ROLL — knowledge workers, monitors aglow"
    else:  # classroom / reskilling
        p.rect([x + w * 0.62, ground - 70, w * 0.3, 70], fill=rgba(ink, 0.7))  # board
        TT(p, [x + w * 0.62, ground - 60, w * 0.3, 18], "RE / SKILL", "flbl",
           color="white")
        for i in range(3):
            figure(p, x + 60 + i * 60, ground, 0.5, ink)
        cap = "B-ROLL — reskilling cohort, laptops open"
    TT(p, [x + 14, y + 12, w - 28, 14], cap, "ftiny", align="start")


def art_stat(p, box, *, value="50%", label="", accent="coral", source=""):
    x, y, w, h = box
    p.rect(box, fill=linear_gradient([(C[accent], 0), (_darken(accent), 1)], angle=150))
    TT(p, [x + 16, y + h * 0.5 - 56, w - 32, 92], value, "fstat", color="white")
    st = dict(STYLES["fmid_w"])
    TT(p, [x + 24, y + h * 0.5 + 36, w - 48, 44], label, st)
    if source:
        TT(p, [x + 16, y + h - 22, w - 32, 12], source, "ftiny", color="white")


def _darken(name):
    return {"coral": "#b23a2c", "blue": "#1c45a8", "teal": "#0c6f64", "amber": "#b9791f",
            "violet": "#46339c", "rose": "#9c2f57", "green": "#247044"}.get(name, "#222")


def art_taskbundle(p, box, *, accent="blue"):
    x, y, w, h = box
    _bgfill(p, box, "#f3f0e8", "#e6e0d2")
    # the JOB on the left
    jb = [x + 28, y + h * 0.5 - 44, 150, 88]
    p.rect(jb, fill=C["ink_blue"], radius=10)
    TT(p, [jb[0], jb[1] + 24, jb[2], 24], "ONE JOB", "fmid_w")
    TT(p, [jb[0], jb[1] + 52, jb[2], 14], "= a bundle of tasks", "ftiny", color="white")
    # tasks fanning out on the right; some shaded as "automatable"
    tasks = [("schedule", True), ("email triage", True), ("analysis", False),
             ("judgement", False), ("client trust", False), ("data entry", True)]
    tx = x + 230
    for i, (t, auto) in enumerate(tasks):
        ty = y + 18 + i * (h - 40) / len(tasks)
        col = C["coral"] if auto else C["teal"]
        p.arrow([jb[0] + jb[2], y + h * 0.5], [tx - 8, ty + 12], color=C["line"], width=1.5)
        p.rect([tx, ty, 150, 24], fill=rgba(col, 0.16), stroke=col,
               stroke_style={"stroke_width": 1.5}, radius=12)
        TT(p, [tx + 8, ty + 5, 134, 14], t, "fchip", align="start")
    TT(p, [tx + 4, y + h - 16, 200, 12], "■ exposed   ■ human-held", "ftiny",
       align="start")


def art_matrix(p, box, *, accent="violet"):
    x, y, w, h = box
    _bgfill(p, box, "#ffffff", "#eef1f6")
    cx, cy = x + w * 0.52, y + h * 0.5
    p.line([x + 30, cy], [x + w - 20, cy], stroke=C["sub"], stroke_style={"stroke_width": 1.5})
    p.line([cx, y + 20], [cx, y + h - 24], stroke=C["sub"], stroke_style={"stroke_width": 1.5})
    quad = [("AUTOMATE", C["coral"], -1, -1, "routine · predictable"),
            ("AUGMENT", C["teal"], 1, -1, "judgement + speed"),
            ("DELEGATE", C["amber"], -1, 1, "low-stakes drafts"),
            ("RESERVE", C["blue"], 1, 1, "trust · ethics · care")]
    for lab, col, sx, sy, sub in quad:
        qx = cx + sx * w * 0.22
        qy = cy + sy * h * 0.22
        p.circle([qx, qy], 7, fill=col)
        st = dict(STYLES["flbl"]); st["color"] = "ink"
        TT(p, [qx - 70, qy - 26, 140, 16], lab, st)
        TT(p, [qx - 70, qy + 12, 140, 12], sub, "ftiny")
    TT(p, [x + 24, y + 6, w * 0.4, 12], "← repetitive", "ftiny", align="start")
    TT(p, [cx + 10, y + h - 16, w * 0.4, 12], "creative →", "ftiny", align="start")


def art_screen(p, box, *, accent="blue"):
    x, y, w, h = box
    _bgfill(p, box, "#cfd7e6", "#b9c4d8")
    inner = device_window(p, [x + 26, y + 20, w - 52, h - 40], C, title="draft.doc — AI assist")
    ix, iy, iw, ih = inner
    # document lines
    for i in range(4):
        p.line([ix + 10, iy + 14 + i * 16], [ix + iw * 0.55, iy + 14 + i * 16],
               stroke=C["hair"], stroke_style={"stroke_width": 3})
    # AI suggestion panel
    px = ix + iw * 0.6
    p.rect([px, iy + 8, iw * 0.38, ih - 16], fill=rgba(C[accent], 0.12),
           stroke=C[accent], stroke_style={"stroke_width": 1.5}, radius=6)
    TT(p, [px + 8, iy + 14, iw * 0.34, 12], "✦ SUGGESTED", "ftiny", align="start",
       color=accent)
    for i in range(3):
        p.line([px + 10, iy + 36 + i * 14], [px + iw * 0.30, iy + 36 + i * 14],
               stroke=rgba(C[accent], 0.6), stroke_style={"stroke_width": 3})
    TT(p, [x + 14, y + 4, w - 28, 12], "SCREEN-CAP — copilot in the flow of work",
       "ftiny", align="start")


def art_sectorbars(p, box, *, accent="amber"):
    x, y, w, h = box
    _bgfill(p, box, "#ffffff", "#eef1f6")
    data = [("Clerical", 0.92, C["coral"]), ("Finance", 0.74, C["amber"]),
            ("Legal", 0.63, C["amber"]), ("Software", 0.58, C["blue"]),
            ("Health", 0.34, C["teal"]), ("Trades", 0.16, C["green"])]
    bx = x + 96
    bw = w - bx - 26
    for i, (lab, frac, col) in enumerate(data):
        by = y + 22 + i * (h - 44) / len(data)
        bh = (h - 44) / len(data) - 8
        TT(p, [x + 14, by + bh * 0.5 - 7, 78, 14], lab, "flbl_l")
        p.rect([bx, by, bw, bh], fill=C["frame2"], radius=3)
        p.rect([bx, by, bw * frac, bh], fill=col, radius=3)
        TT(p, [bx + bw * frac - 40, by + bh * 0.5 - 6, 36, 12],
           f"{int(frac*100)}%", "ftiny", align="end", color="white")
    TT(p, [bx, y + 4, bw, 12], "SHARE OF TASKS EXPOSED TO AI", "flbl_l")


def art_roles(p, box, *, accent="rose"):
    x, y, w, h = box
    _bgfill(p, box, "#f1eee6", "#e3ddcf")
    roles = ["Analyst", "Writer", "Coder", "Designer", "Recruiter", "Support",
             "Teacher", "Nurse"]
    cols = 4
    cw = (w - 40) / cols
    ch = (h - 50) / 2
    for i, r in enumerate(roles):
        cxp = x + 20 + (i % cols) * cw
        cyp = y + 28 + (i // cols) * ch
        p.rect([cxp + 6, cyp, cw - 12, ch - 12], fill=C["white"], stroke=C["line"],
               stroke_style={"stroke_width": 1.2}, radius=6)
        figure(p, cxp + cw / 2, cyp + ch * 0.52, 0.38, C["ink_blue"])
        TT(p, [cxp + 6, cyp + ch - 26, cw - 12, 12], r, "ftiny")
    TT(p, [x + 16, y + 6, w - 32, 14], "EVERY KNOWLEDGE ROLE, TOUCHED", "flbl_l")


def art_quote(p, box, *, text="", attrib="", accent="teal"):
    x, y, w, h = box
    p.rect(box, fill=linear_gradient([(C["ink"], 0), (C["ink_blue"], 1)], angle=150))
    p.rect([x + 30, y + 26, 5, h - 80], fill=C[accent])
    TT(p, [x + 50, y + 26, w - 80, h - 90], text,
       dict(STYLES["fquote"], color="#f3f1ea"))
    TT(p, [x + 50, y + h - 40, w - 80, 16], attrib,
       dict(STYLES["fattr"], color=accent), align="start")


def art_loop(p, box, *, accent="teal"):
    x, y, w, h = box
    _bgfill(p, box, "#eef4f2", "#dce8e3")
    hub_l = [x + w * 0.26, y + h * 0.5]
    hub_r = [x + w * 0.72, y + h * 0.5]
    p.circle(hub_l, 40, fill=C["white"], stroke=C["ink_blue"], stroke_style={"stroke_width": 2})
    figure(p, hub_l[0], hub_l[1] + 22, 0.45, C["ink_blue"])
    p.circle(hub_r, 40, fill=C["white"], stroke=C[accent], stroke_style={"stroke_width": 2})
    TT(p, [hub_r[0] - 40, hub_r[1] - 12, 80, 24], "AI", "fmid", color=accent)
    # two arcs forming a loop
    p.path(Path().move_to(hub_l[0] + 42, hub_l[1] - 14).through(
        [[x + w * 0.5, y + h * 0.22]]).line_to(hub_r[0] - 42, hub_r[1] - 14),
        fill=None, stroke=C["teal"], stroke_style={"stroke_width": 2.5})
    p.arrow([x + w * 0.5, y + h * 0.27], [hub_r[0] - 42, hub_r[1] - 12],
            color=C["teal"], width=2.5)
    p.path(Path().move_to(hub_r[0] - 42, hub_r[1] + 14).through(
        [[x + w * 0.5, y + h * 0.78]]).line_to(hub_l[0] + 42, hub_l[1] + 14),
        fill=None, stroke=C["blue"], stroke_style={"stroke_width": 2.5})
    p.arrow([x + w * 0.5, y + h * 0.73], [hub_l[0] + 42, hub_l[1] + 12],
            color=C["blue"], width=2.5)
    TT(p, [x + w * 0.5 - 90, y + h * 0.12, 180, 14], "asks / directs", "ftiny")
    TT(p, [x + w * 0.5 - 90, y + h - 20, 180, 14], "drafts / scales", "ftiny")
    TT(p, [x + 16, y + 8, w - 32, 14], "CENTAUR LOOP — human judgement × AI speed",
       "flbl_l")


def art_casecard(p, box, *, before="", after="", metric="", accent="green"):
    x, y, w, h = box
    _bgfill(p, box, "#ffffff", "#eef1f6")
    half = (w - 60) / 2
    p.rect([x + 20, y + 30, half, h - 60], fill=C["frame2"], stroke=C["line"],
           stroke_style={"stroke_width": 1.2}, radius=8)
    p.rect([x + 40 + half, y + 30, half, h - 60], fill=rgba(C[accent], 0.12),
           stroke=C[accent], stroke_style={"stroke_width": 1.5}, radius=8)
    TT(p, [x + 20, y + 8, half, 14], "BEFORE", "flbl")
    TT(p, [x + 40 + half, y + 8, half, 14], "AFTER AI", "flbl", color=accent)
    TT(p, [x + 28, y + h * 0.5 - 14, half - 16, 40],
       before, dict(STYLES["fmid"], font_size=18))
    TT(p, [x + 48 + half, y + h * 0.5 - 24, half - 16, 30],
       after, dict(STYLES["fmid"], font_size=18, color=accent))
    TT(p, [x + 48 + half, y + h * 0.5 + 8, half - 16, 18], metric,
       dict(STYLES["ftiny"], color=accent, align="start"))
    p.arrow([x + 20 + half - 4, y + h * 0.5], [x + 40 + half + 4, y + h * 0.5],
            color=C["sub"], width=2.5, head=10)


def art_skillstack(p, box, *, accent="blue"):
    x, y, w, h = box
    _bgfill(p, box, "#f3f0e8", "#e6e0d2")
    layers = [("Judgement & taste", C["coral"]), ("Direction of AI", C["amber"]),
              ("Domain depth", C["blue"]), ("Communication", C["teal"]),
              ("Data literacy", C["violet"])]
    lh = (h - 50) / len(layers)
    for i, (lab, col) in enumerate(layers):
        ly = y + 30 + i * lh
        ww = w * (0.5 + 0.09 * (len(layers) - i))
        p.rect([x + (w - ww) / 2, ly, ww, lh - 8], fill=rgba(col, 0.16), stroke=col,
               stroke_style={"stroke_width": 1.5}, radius=5)
        TT(p, [x + (w - ww) / 2, ly + lh * 0.5 - 12, ww, 16], lab,
           dict(STYLES["flbl"], color="ink"))
    TT(p, [x + 16, y + 8, w - 32, 14], "THE NEW SKILL STACK", "flbl_l")


def art_checklist(p, box, *, title="PLAYBOOK", items=None, accent="amber"):
    x, y, w, h = box
    _bgfill(p, box, "#ffffff", "#eef1f6")
    p.rect([x, y, w, 30], fill=C[accent])
    TT(p, [x + 16, y + 8, w - 32, 16], title, dict(STYLES["flbl"], color="white"),
       align="start")
    items = items or []
    for i, it in enumerate(items):
        iy = y + 44 + i * (h - 54) / len(items)
        p.rect([x + 18, iy, 16, 16], fill=C["white"], stroke=C[accent],
               stroke_style={"stroke_width": 2}, radius=3)
        p.path(Path().move_to(x + 21, iy + 8).line_to(x + 25, iy + 12).line_to(x + 32, iy + 3),
               fill=None, stroke=C[accent], stroke_style={"stroke_width": 2.5,
                                                           "stroke_linecap": "round"})
        TT(p, [x + 44, iy + 1, w - 60, 16], it, dict(STYLES["fchip"], align="start",
                                                     font_size=13))


def art_flow(p, box, *, steps=None, accent="violet"):
    x, y, w, h = box
    _bgfill(p, box, "#eef0f6", "#dde1ee")
    steps = steps or ["MAP tasks", "SORT auto/aug", "REDESIGN roles", "RESKILL"]
    n = len(steps)
    bw = (w - 40 - (n - 1) * 18) / n
    for i, s in enumerate(steps):
        bx = x + 20 + i * (bw + 18)
        by = y + h * 0.5 - 34
        p.rect([bx, by, bw, 68], fill=C["white"], stroke=C[accent],
               stroke_style={"stroke_width": 1.5}, radius=8)
        TT(p, [bx + 4, by + 24, bw - 8, 30], s, dict(STYLES["fchip"], font_size=13))
        if i:
            p.arrow([bx - 16, by + 34], [bx - 2, by + 34], color=C[accent], width=2.5)
    TT(p, [x + 16, y + 10, w - 32, 14], "WORKFORCE REDESIGN — a 4-step loop",
       "flbl_l")


def art_numbered(p, box, *, title="DO THIS", items=None, accent="coral"):
    x, y, w, h = box
    p.rect(box, fill=linear_gradient([(C["ink"], 0), (C["ink_blue"], 1)], angle=150))
    TT(p, [x + 22, y + 16, w - 44, 18], title,
       dict(STYLES["kicker"], font_size=14, color=accent), align="start")
    items = items or []
    for i, it in enumerate(items):
        iy = y + 50 + i * (h - 64) / len(items)
        p.circle([x + 36, iy + 12], 13, fill=C[accent])
        TT(p, [x + 24, iy + 4, 24, 16], str(i + 1), dict(STYLES["fchip"], color="white"))
        TT(p, [x + 60, iy + 2, w - 80, 18], it,
           dict(STYLES["fchip"], color="#f3f1ea", align="start", font_size=14))


def art_kinetic(p, box, *, lines=None, accent="amber"):
    x, y, w, h = box
    p.rect(box, fill=linear_gradient([(C["ink_blue"], 0), (C["ink"], 1)], angle=160))
    lines = lines or ["AI WON'T", "REPLACE YOU.", "BUT SOMEONE", "USING IT MIGHT."]
    cols = ["#f3f1ea", accent, "#f3f1ea", accent]
    for i, ln in enumerate(lines):
        st = dict(STYLES["fbig_w"], font_size=30, align="start",
                  color=cols[i % len(cols)])
        TT(p, [x + 28, y + 22 + i * (h - 50) / len(lines), w - 56, 30], ln, st)


def art_endscreen(p, box, *, accent="coral"):
    x, y, w, h = box
    p.rect(box, fill=linear_gradient([(C["ink"], 0), (C["ink_blue"], 1)], angle=150))
    # subscribe button
    p.rect([x + w * 0.5 - 90, y + 28, 180, 40], fill=C[accent], radius=20)
    TT(p, [x + w * 0.5 - 90, y + 39, 180, 18], "▶  SUBSCRIBE",
       dict(STYLES["flbl"], color="white", font_size=14))
    # two up-next thumbnails
    for i in range(2):
        tx = x + 40 + i * (w * 0.5 - 10)
        p.rect([tx, y + h - 92, w * 0.42, 70], fill=rgba(C["white"], 0.08),
               stroke=rgba(C["white"], 0.4), stroke_style={"stroke_width": 1.2}, radius=6)
        p.polygon([[tx + 24, y + h - 74], [tx + 24, y + h - 48], [tx + 46, y + h - 61]],
                  fill=C[accent])
        TT(p, [tx + 56, y + h - 70, w * 0.42 - 64, 28],
           ["Reskilling, fast", "AI org design"][i],
           dict(STYLES["ftiny"], color="white", align="start", font_size=11))
    TT(p, [x + 20, y + h * 0.5 - 4, w - 40, 16], "UP NEXT — keep watching",
       dict(STYLES["flbl"], color="white"))


PAINTERS = {
    "host": art_host, "title": art_title, "question": art_question,
    "montage": art_montage, "timeline": art_timeline, "linechart": art_linechart,
    "broll": art_broll, "stat": art_stat, "taskbundle": art_taskbundle,
    "matrix": art_matrix, "screen": art_screen, "sectorbars": art_sectorbars,
    "roles": art_roles, "quote": art_quote, "loop": art_loop, "casecard": art_casecard,
    "skillstack": art_skillstack, "checklist": art_checklist, "flow": art_flow,
    "numbered": art_numbered, "kinetic": art_kinetic, "endscreen": art_endscreen,
}


# --------------------------------------------------------------------------- #
# Shot list — 36 shots, a real 20:00 documentary cut
# --------------------------------------------------------------------------- #
# Each shot: (scene_idx, type, dur_sec, cam, vo, osd, art_name, art_kwargs)
SHOTS = [
    # SCENE 0 — COLD OPEN
    (0, "MONT", 8, "Whip-pan cuts, 4–6 frames/s",
     "Every morning, a billion people sit down to work…",
     "—", "montage", {}),
    (0, "TITLE", 10, "Slam-cut, hard zoom",
     "…and an invisible new colleague is already at the desk.",
     "WILL AI TAKE YOUR JOB?", "question",
     {"q": "WILL AI\nTAKE YOUR\nJOB?", "small": "wrong question."}),
    (0, "MS", 14, "Handheld, push-in",
     "I'm going to argue that's the wrong question — and show you the right one.",
     "Host · cold open", "host", {"framing": "MS", "caption": "THE RIGHT QUESTION",
                                  "sub": "host"}),
    (0, "TITLE", 8, "Logo sting + sub bass",
     "This is The Great Rewrite.",
     "SERIES TITLE CARD", "title", {"big": "THE GREAT\nREWRITE",
                                    "small": "AI & THE FUTURE OF WORK"}),

    # SCENE 1 — NOT THE FIRST TIME
    (1, "MCU", 16, "Locked off, eyeline left",
     "We've rewritten work before — steam, electricity, the PC. Each time, fear; "
     "each time, more jobs, different jobs.",
     "We've been here before", "host", {"framing": "MCU", "accent": "violet",
                                        "caption": "WE'VE BEEN HERE BEFORE"}),
    (1, "GFX", 22, "2.5D parallax dolly along axis",
     "But look at the spacing. Steam took eighty years to bite. The web took fifteen.",
     "Timeline: 1780 → today", "timeline", {}),
    (1, "GFX", 20, "Animated draw-on, ease-out",
     "Generative AI crossed a hundred million users in two months. Nothing has "
     "moved this fast.",
     "Adoption curve", "linechart", {"accent": "violet"}),
    (1, "BROLL", 16, "Match-cut dissolve, archival→modern",
     "The pattern is old. The clock-speed is brand new.",
     "Archival → modern", "broll", {"kind": "factory", "accent": "violet"}),
    (1, "STAT", 10, "Number counts up, snap hold",
     "Five years. That's the window analysts give for the bulk of this shift.",
     "Lower-third stat", "stat", {"value": "~5 yrs", "label": "to reshape most\nknowledge work",
                                  "accent": "violet", "source": "SOURCE: composite, 2024"}),

    # SCENE 2 — TASKS, NOT JOBS
    (2, "MS", 18, "Slow push-in",
     "Here's the reframe. AI doesn't do jobs. It does tasks. And every job is just "
     "a bundle of them.",
     "Tasks, not jobs", "host", {"framing": "MS", "accent": "teal",
                                 "caption": "TASKS, NOT JOBS"}),
    (2, "GFX", 24, "Explode-out, staggered springs",
     "Pull a job apart and you find tasks a machine can take — and tasks that are "
     "stubbornly, valuably human.",
     "Job → task bundle", "taskbundle", {"accent": "teal"}),
    (2, "GFX", 20, "Quadrant fields fade in",
     "Sort the tasks. Automate the routine. Augment the judgement. The middle is "
     "where work gets redesigned.",
     "Automate vs augment", "matrix", {}),
    (2, "SCREEN", 18, "Screen-cap, cursor follow",
     "You've felt this already — the draft that writes its own first pass while you "
     "decide what's true.",
     "Copilot in-flow", "screen", {"accent": "teal"}),
    (2, "STAT", 12, "Punch-in on figure",
     "On average, AI touches a quarter to a half of the tasks in a typical "
     "office role.",
     "Exposure stat", "stat", {"value": "30–50%", "label": "of tasks exposed\nin office roles",
                               "accent": "teal", "source": "SOURCE: labour studies, 2023–24"}),

    # SCENE 3 — WHO'S AFFECTED
    (3, "MCU", 16, "Locked, eyeline right",
     "So who feels it first? Not the people you'd guess from the headlines.",
     "Who's affected", "host", {"framing": "MCU", "accent": "amber",
                                "caption": "WHO FEELS IT FIRST"}),
    (3, "GFX", 22, "Bars wipe in left→right",
     "It's the desk, not the dock. Clerical and analytical work is most exposed; "
     "hands-on trades, least.",
     "Exposure by sector", "sectorbars", {}),
    (3, "GFX", 18, "Grid reveals, soft stagger",
     "Analyst, writer, coder, recruiter — every knowledge role gets re-cut, not "
     "deleted.",
     "Roles grid", "roles", {}),
    (3, "QUOTE", 16, "Slow vertical crawl",
     "“The future is already here — it's just not evenly distributed.”",
     "Pull-quote", "quote", {"text": "“The future is already\nhere — it's just not\nevenly distributed.”",
                             "attrib": "— WILLIAM GIBSON", "accent": "amber"}),

    # SCENE 4 — THE AUGMENTATION STORY
    (4, "MS", 18, "Push-in, warm key",
     "Now the hopeful part — and it's backed by data. The winners aren't humans or "
     "AI. They're humans with AI.",
     "Humans + AI", "host", {"framing": "MS", "accent": "coral",
                             "caption": "HUMANS + AI WIN"}),
    (4, "GFX", 22, "Loop animates, arrows cycle",
     "Think of it as a centaur: you bring judgement and taste, it brings speed and "
     "reach. Round and round.",
     "Centaur loop", "loop", {"accent": "teal"}),
    (4, "GFX", 20, "Before/after slider wipe",
     "A support team I studied cut resolution time in half and *raised* satisfaction "
     "— because agents stopped copy-pasting and started caring.",
     "Case: support", "casecard", {"before": "11 min /\nticket",
                                   "after": "5 min /\nticket",
                                   "metric": "CSAT +14 pts", "accent": "green"}),
    (4, "STAT", 14, "Count-up, hold on peak",
     "Across early studies, well-deployed AI lifts knowledge-worker output by a "
     "third or more.",
     "Productivity stat", "stat", {"value": "+34%", "label": "output, when AI is\ndeployed well",
                                   "accent": "green", "source": "SOURCE: field experiments, 2023"}),

    # SCENE 5 — THE NEW SKILLS
    (5, "MCU", 16, "Locked, calm",
     "If the tasks change, the skills change. So what's actually worth learning now?",
     "The new skills", "host", {"framing": "MCU", "accent": "rose",
                                "caption": "WHAT TO LEARN NOW"}),
    (5, "GFX", 22, "Layers stack bottom→top",
     "Underneath: data literacy and clear communication. On top: domain depth, "
     "directing AI, and the judgement to know when it's wrong.",
     "Skill stack", "skillstack", {}),
    (5, "GFX", 16, "Chips orbit in",
     "Notice none of these are 'prompt tricks.' They're durable, human, and they "
     "compound.",
     "Durable skills", "kinetic",
     {"lines": ["DURABLE.", "HUMAN.", "COMPOUNDING.", "NOT A PROMPT HACK."],
      "accent": "rose"}),
    (5, "BROLL", 14, "Slow dolly across cohort",
     "And they're learnable — fast — by people already in the workforce.",
     "Reskilling b-roll", "broll", {"kind": "classroom", "accent": "rose"}),

    # SCENE 6 — WHAT COMPANIES MUST DO
    (6, "MS", 16, "Push-in, authoritative",
     "If you run a team, the trap is buying tools and skipping the redesign. Don't.",
     "For leaders", "host", {"framing": "MS", "accent": "green",
                             "caption": "IF YOU LEAD A TEAM"}),
    (6, "GFX", 22, "Steps light up in sequence",
     "Map the tasks. Sort them. Redesign the role around what's left. Then reskill "
     "the people into it.",
     "Redesign loop", "flow", {}),
    (6, "GFX", 18, "Checks tick on, audio pops",
     "The companies pulling ahead share four habits — and 'announce a policy' isn't "
     "one of them.",
     "Org playbook", "checklist",
     {"title": "ORG PLAYBOOK", "accent": "green",
      "items": ["Redesign work, not just tools", "Train managers first",
                "Measure outcomes, not usage", "Share the productivity dividend"]}),
    (6, "STAT", 12, "Snap-in figure",
     "Reskilling an existing worker costs a fraction of replacing them — and keeps "
     "the institutional memory.",
     "Reskill ROI", "stat", {"value": "1/6th", "label": "cost to reskill vs.\nre-hire",
                             "accent": "green", "source": "SOURCE: HR benchmarks"}),

    # SCENE 7 — WHAT YOU SHOULD DO + OUTRO
    (7, "MCU", 16, "Direct address, lock",
     "And if it's just you, watching this, wondering where you fit — here's the move.",
     "For you", "host", {"framing": "MCU", "accent": "blue",
                         "caption": "IF IT'S JUST YOU"}),
    (7, "GFX", 20, "Numbers stamp in, kinetic",
     "Adopt the tools on your own tasks this week. Get fluent. Then aim them at the "
     "part of your job only you can do.",
     "Personal playbook", "numbered",
     {"title": "YOUR MOVE", "accent": "coral",
      "items": ["Automate your busywork now", "Build judgement AI can't fake",
                "Become the person who directs it"]}),
    (7, "TITLE", 18, "Kinetic type, beat-synced",
     "Because here's the honest version of the headline:",
     "Thesis card", "kinetic", {}),
    (7, "MS", 26, "Slow push to close-up, music swells",
     "AI isn't the end of work. It's the biggest rewrite of what work means in a "
     "century — and you still hold the pen. Let's go write it.",
     "Outro / thesis", "host", {"framing": "MS", "accent": "blue",
                                "caption": "YOU HOLD THE PEN"}),
    (7, "END", 22, "End-screen template, 20s hold",
     "If this reframed anything for you, subscribe — next week we reskill a whole "
     "team in thirty days.",
     "End screen + CTA", "endscreen", {"accent": "coral"}),
]


# Authoritative shot durations (seconds), retimed so the cut lands a true 20:00.
# Kept in one place so the running time is easy to audit and rebalance; the values
# above the per-shot tuples are placeholders this list overrides.
DURATIONS = [
    9, 12, 18, 10,            # 0 cold open
    36, 48, 36, 30, 20,       # 1 not the first time
    40, 50, 38, 34, 24,       # 2 tasks, not jobs
    34, 42, 34, 30,           # 3 who's affected
    40, 48, 38, 28,           # 4 humans + AI
    36, 48, 32, 28,           # 5 the new skills
    36, 42, 36, 24,           # 6 for leaders
    32, 42, 36, 60, 48,       # 7 your move + outro
]
assert len(DURATIONS) == len(SHOTS), (len(DURATIONS), len(SHOTS))
SHOTS = [(s[0], s[1], d, *s[3:]) for s, d in zip(SHOTS, DURATIONS)]


# --------------------------------------------------------------------------- #
# Cell + page composition
# --------------------------------------------------------------------------- #
def board_header(p, title, sub, folio):
    p.rect([0, 0, W, 64], fill=C["ink"])
    p.rect([0, 64, W, 3], fill=C["amber"])
    TT(p, [M, 18, 900, 30], title, dict(STYLES["board_t"], color="paper"), align="start")
    TT(p, [M, 44, 900, 14], sub, dict(STYLES["board_s"], color="amber"), align="start")
    TT(p, [W - 360, 24, 304, 16], "THE GREAT REWRITE · STORYBOARD v1",
       dict(STYLES["folio"], color="muted"), align="end")
    TT(p, [W - 360, 42, 304, 14], folio, dict(STYLES["folio"], color="muted"),
       align="end")


def shot_cell(p, box, idx, shot):
    """One storyboard cell: numbered styleframe + the editor's metadata."""
    scene, stype, dur, cam, vo, osd, art, kw = shot
    x, y, w, h = box
    ac = SCENE_C[scene]
    tc = TC_INDEX[idx]

    head_h = 22
    frame_h = round(w * 9 / 16)
    fx, fy = x, y + head_h
    # --- cell header: scene stripe + shot number + type tag ---
    p.rect([x, y, w, head_h - 6], fill=C["board"])
    p.rect([x, y, 30, head_h - 6], fill=ac)
    TT(p, [x, y - 1, 30, 18], f"{idx + 1:02d}", "shot_no")
    TT(p, [x + 38, y + 1, w - 120, 14],
       fmt_tc(tc), dict(STYLES["tc"], font_size=13), align="start")
    # type tag pill on the right
    tagw = 56
    p.rect([x + w - tagw, y, tagw, head_h - 6], fill=C["ink"], radius=3)
    TT(p, [x + w - tagw, y + 1, tagw, 14], stype, "tag")

    # --- styleframe ---
    p.rect([fx, fy, w, frame_h], fill=C["frame"], stroke=C["line"],
           stroke_style={"stroke_width": 1.5})
    PAINTERS[art](p, [fx + 2, fy + 2, w - 4, frame_h - 4], **kw)
    p.rect([fx, fy, w, frame_h], fill=None, stroke=C["ink"],
           stroke_style={"stroke_width": 1.5})
    # corner duration chip
    p.rect([fx + w - 52, fy + frame_h - 20, 52, 20], fill=rgba(C["ink"], 0.82))
    TT(p, [fx + w - 52, fy + frame_h - 17, 48, 14], f"{dur}s",
       dict(STYLES["tag"], align="end"), align="end")

    # --- metadata block under the frame ---
    my = fy + frame_h + 8
    avail = (y + h) - my
    # VO
    TT(p, [x, my, 38, 12], "VO", "note_k", align="start")
    TT(p, [x + 40, my - 1, w - 40, 52], f"“{vo}”", "vo", align="start")
    # camera + on-screen lines
    ly = my + 52
    TT(p, [x, ly, 38, 12], "CAM", "note_k", align="start")
    TT(p, [x + 40, ly, w - 40, 12], cam, "note", align="start")
    TT(p, [x, ly + 16, 38, 12], "OSD", "note_k", align="start")
    TT(p, [x + 40, ly + 16, w - 40, 12], osd, "note", align="start")


def board_page(b, page_no, total_pages, shots_slice, first_idx):
    scene_names = {s[0] for s in shots_slice}
    p = sheet(b, f"board-{page_no:02d}")
    # which scenes appear on this sheet
    here = sorted(scene_names)
    sub = "SHEET " + " · ".join(SCENE_TITLES[s].split(" — ")[0] for s in here)
    board_header(p, f"Storyboard — Sheet {page_no} of {total_pages}",
                 sub, f"SHOTS {first_idx + 1:02d}–{first_idx + len(shots_slice):02d}")

    grid_top = 92
    grid_bot = H - 30
    cols, rows = 3, 2
    gx, gy = 30, 30
    cw = (W - 2 * M - (cols - 1) * gx) / cols
    ch = (grid_bot - grid_top - (rows - 1) * gy) / rows
    for i, shot in enumerate(shots_slice):
        cxp = M + (i % cols) * (cw + gx)
        cyp = grid_top + (i // cols) * (ch + gy)
        shot_cell(p, [cxp, cyp, cw, ch], first_idx + i, shot)


def cover_page(b, total_pages):
    p = sheet(b, "cover", bg="ink")
    p.rect([0, 0, W, H], fill=linear_gradient(
        [(C["ink"], 0), (C["ink_blue"], 0.6), ("#1d2c54", 1)], angle=155))
    # ambient styleframe grid watermark
    for r in range(3):
        for c in range(5):
            bx, by = 120 + c * 230, 150 + r * 200
            p.rect([bx, by, 200, 112], fill=None, stroke=rgba(C["white"], 0.05),
                   stroke_style={"stroke_width": 1}, decorative=True)
    p.rect([M, 150, 360, 6], fill=C["amber"])
    TT(p, [M, 176, 1200, 200], "THE GREAT\nREWRITE", "h1")
    TT(p, [M, 360, 1100, 30], "AI & THE FUTURE OF WORK", "kicker")
    TT(p, [M, 432, 900, 120],
       "A 20-minute YouTube documentary on how artificial intelligence is "
       "rewriting tasks, roles, and the deal between people and work — and what "
       "to do about it.", "lede")

    # production brief card
    bx, by, bw, bh = W - 560, 150, 504, 470
    p.rect([bx, by, bw, bh], fill=rgba(C["white"], 0.05), stroke=rgba(C["white"], 0.25),
           stroke_style={"stroke_width": 1.5}, radius=14)
    p.rect([bx, by, bw, 44], fill=C["amber"], radius=14)
    TT(p, [bx + 24, by + 14, bw - 48, 18], "PRODUCTION BRIEF",
       dict(STYLES["kicker"], font_size=14, color="ink"), align="start")
    brief = [
        ("FORMAT", "YouTube long-form · 16:9 · 4K"),
        ("RUNTIME", f"{fmt_tc(TOTAL)}  ({TOTAL}s) — target 20:00"),
        ("SHOTS", f"{len(SHOTS)} across {len(SCENE_TITLES)} scenes"),
        ("AUDIENCE", "Knowledge workers, founders, students"),
        ("TONE", "Clear, data-grounded, optimistic-realist"),
        ("VISUAL", "Studio host + kinetic GFX + light b-roll"),
        ("PALETTE", "Ink navy · paper · amber + scene accents"),
        ("CTA", "Subscribe → 'Reskill a team in 30 days'"),
    ]
    for i, (k, v) in enumerate(brief):
        ry = by + 66 + i * 48
        TT(p, [bx + 24, ry, 130, 14], k, "meta_k", align="start")
        TT(p, [bx + 160, ry, bw - 184, 32], v, "meta", align="start")

    # scene running order strip along the bottom
    TT(p, [M, 640, 600, 18], "RUNNING ORDER", dict(STYLES["kicker_d"], color="amber"),
       align="start")
    sw = (W - 2 * M - 7 * 12) / 8
    for i, title in SCENE_TITLES.items():
        sx = M + i * (sw + 12)
        p.rect([sx, 672, sw, 150], fill=rgba(C["white"], 0.04),
               stroke=rgba(SCENE_C[i], 0.9), stroke_style={"stroke_width": 1.5},
               radius=8)
        p.rect([sx, 672, sw, 6], fill=SCENE_C[i])
        TT(p, [sx + 12, 690, sw - 24, 16], f"{i:02d}",
           dict(STYLES["board_s"], color="muted"), align="start")
        name, beat = title.split(" — ")
        TT(p, [sx + 12, 712, sw - 24, 60],
           name, dict(STYLES["fmid_w"], font_size=17, align="start", line_height=1.05))
        TT(p, [sx + 12, 786, sw - 24, 30], beat,
           dict(STYLES["ftiny"], color="muted", align="start", font_size=10))
        # shot count for the scene
        cnt = sum(1 for s in SHOTS if s[0] == i)
        TT(p, [sx + 12, 800, sw - 24, 12], f"{cnt} shots",
           dict(STYLES["ftiny"], color=None, align="start"), color=SCENE_C[i])

    TT(p, [M, H - 44, 1200, 16],
       "Composed entirely with the FrameGraph SDK — every styleframe is geometry, "
       "no image assets.", dict(STYLES["folio"], color="muted"), align="start")


SCENE_TITLES = {
    0: "COLD OPEN — the hook & title",
    1: "NOT THE FIRST TIME — historical clock-speed",
    2: "TASKS, NOT JOBS — the reframe",
    3: "WHO'S AFFECTED — desk before dock",
    4: "HUMANS + AI — the augmentation case",
    5: "THE NEW SKILLS — what to learn",
    6: "FOR LEADERS — redesign, don't bolt on",
    7: "YOUR MOVE — individual playbook & outro",
}

# Precompute timecodes + total runtime.
TC_INDEX = []
_acc = 0
for _s in SHOTS:
    TC_INDEX.append(_acc)
    _acc += _s[2]
TOTAL = _acc


# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="The Great Rewrite — AI & the Future of Work (Storyboard)",
                        profile="deck", lang="en")
    for name, value in C.items():
        b.define_color(name, value)
    for name, style in STYLES.items():
        b.define_text_style(name, **style)

    per_page = 6
    pages = [SHOTS[i:i + per_page] for i in range(0, len(SHOTS), per_page)]
    cover_page(b, len(pages))
    for pno, sl in enumerate(pages, start=1):
        board_page(b, pno, len(pages), sl, (pno - 1) * per_page)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} pages · {len(SHOTS)} shots · "
          f"TRT {fmt_tc(TOTAL)} ({TOTAL}s)")
    print(f"validate: ok={report.ok} errors={len(errors)} warnings={len(warnings)}")
    for i in (errors + warnings)[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "fixtures", "ai-workforce-storyboard.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
