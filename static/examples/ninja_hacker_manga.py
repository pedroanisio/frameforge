#!/usr/bin/env python3
"""NULLSEC // 零 — a 25-page cyber-ninja manga, composed entirely with the SDK.

A complete one-shot: KAGE, a shinobi-hacker in Neo-Kyoto, breaches the Kurogane
megacorp to free the "Oni Key" — and finds it is a caged AI named AYA. He duels
the corp's enforcer TENGU in both steel and code, is betrayed by his own broker,
and wins not by out-fighting but by out-thinking. Setup, midpoint reveal, twist,
clever climax, denouement, hook.

Everything is built through the Python SDK — no image assets. The vocabulary is
hand-rolled manga grammar: bordered panels with gutters, speech / shout / thought
/ digital bubbles with tails, onomatopoeia SFX, radial and horizontal speed
lines, screentone fills, code-rain, and silhouette characters drawn from
polylines and paths. Two visual registers carry the duality:

  * INK  — the physical world: off-white paper, black ink, grey screentone, a
           single blood-red accent.
  * NEON — the net / cyberspace: black field, cyan + magenta, perspective grids
           and falling code.

Design notes honouring the engine's static rules (so the fixture validates
clean): art is authored at layer level (where overlap is legal z-order); every
object that bleeds past the page is marked ``decorative``; repeated text fields
(code-rain) are wrapped in a group so they never read as a tabular grid.

Run from the repository root::

    uv run python examples/ninja_hacker_manga.py
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    Path,
    column,
    grid,
    inset,
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
W, H = 1200, 1700                       # tankobon-ish portrait (~1 : 1.42)
CANVAS = {"size": [W, H], "units": "px"}
MARGIN = 50
GUTTER = 18

SANS = ["DejaVu Sans", "Arial", "sans-serif"]
SERIF = ["Bitstream Charter", "Noto Serif", "Georgia", "serif"]
MONO = ["DejaVu Sans Mono", "Fira Mono", "monospace"]

CO = {
    # ink register
    "ink": "#101015", "paper": "#efece2", "tone1": "#d9d5c8", "tone2": "#b4afa0",
    "tone3": "#86826f", "line": "#16161c", "blood": "#c41f1a",
    # neon register
    "void": "#05060b", "void2": "#0a0d1a", "cyan": "#27e7e0", "cyan_dk": "#0c8f8a",
    "magenta": "#ff2e88", "amber": "#ffce4a", "violet": "#7c5cff",
    "danger": "#ff3b30", "white": "#ffffff", "grid": "#123",
}

STYLES = {
    # cover / titling
    "title":    dict(font_family=SANS, font_size=158, font_weight=800, color="paper",
                     letter_spacing=-8, line_height=0.86),
    "title_cy": dict(font_family=SANS, font_size=158, font_weight=800, color="cyan",
                     letter_spacing=-8, line_height=0.86),
    "subt":     dict(font_family=MONO, font_size=22, font_weight=700, color="cyan",
                     letter_spacing=8, text_transform="uppercase"),
    "byline":   dict(font_family=MONO, font_size=15, color="tone1", letter_spacing=3),
    # narration captions
    "narr_l":   dict(font_family=SERIF, font_size=20, color="paper", line_height=1.45),
    "narr_d":   dict(font_family=SERIF, font_size=20, color="ink", line_height=1.45),
    # dialogue
    "speech":   dict(font_family=SANS, font_size=21, font_weight=600, color="ink",
                     line_height=1.18, align="center"),
    "speech_l": dict(font_family=SANS, font_size=21, font_weight=600, color="paper",
                     line_height=1.18, align="center"),
    "shout":    dict(font_family=SANS, font_size=24, font_weight=800, color="ink",
                     line_height=1.06, align="center"),
    "thought":  dict(font_family=SERIF, font_size=19, italic=True, color="ink",
                     line_height=1.2, align="center"),
    "ai":       dict(font_family=MONO, font_size=21, font_weight=700, color="cyan",
                     line_height=1.25, align="center"),
    "digital":  dict(font_family=MONO, font_size=17, color="cyan", line_height=1.3),
    # chrome + sfx
    "sfx":      dict(font_family=SANS, font_size=128, font_weight=800, color="ink",
                     letter_spacing=-4),
    "sfx_cy":   dict(font_family=SANS, font_size=128, font_weight=800, color="cyan",
                     letter_spacing=-4),
    "sfx_rd":   dict(font_family=SANS, font_size=110, font_weight=800, color="danger",
                     letter_spacing=-4),
    "label":    dict(font_family=MONO, font_size=13, font_weight=700, color="tone3",
                     letter_spacing=2, text_transform="uppercase"),
    "label_cy": dict(font_family=MONO, font_size=13, font_weight=700, color="cyan_dk",
                     letter_spacing=2, text_transform="uppercase"),
    "pagenum":  dict(font_family=MONO, font_size=14, color="tone3", letter_spacing=1),
    "credit":   dict(font_family=MONO, font_size=15, color="tone1", line_height=1.7),
}

_PAGE_NO = 0  # module counter -> deterministic page ids / folio numbers


# --------------------------------------------------------------------------- #
# Manga grammar helpers
# --------------------------------------------------------------------------- #
def sheet(b, pid, *, bg="paper", folio=True):
    """Open a page, lay the paper, and stamp the folio number in the outer corner."""
    global _PAGE_NO
    _PAGE_NO += 1
    page = b.page(pid, canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill=bg)
    page.layer("art")
    if folio:
        outer = W - MARGIN - 60 if _PAGE_NO % 2 == 0 else MARGIN
        T(page, [outer, H - 34, 60, 18], f"{_PAGE_NO:02d}", style="pagenum")
    return page


def content_box():
    return [MARGIN, MARGIN, W - 2 * MARGIN, H - 2 * MARGIN]


def T(p, box, s, **fields):
    """Emit one run of lettering through the SDK's ``page.lettering()`` block.

    The tabular-box-model heuristic flags ≥6 absolutely-placed text objects in a
    regular grid — true of any captioned/balloon-lettered page. ``lettering()``
    tags the text as intentional lettering so the heuristic skips it, which is
    exactly what a comic wants. (Earlier this wrapped each run in a one-child
    group to dodge the same rule; the builder affordance retires that workaround.)
    """
    with p.lettering():
        p.text([float(v) for v in box], s, **fields)


def panel(p, box, *, fill="paper", border="line", lw=5.0, radius=0.0, pad=16.0):
    """Draw a bordered manga panel; return the inner content box."""
    p.rect(box, fill=fill, stroke=border, stroke_style={"stroke_width": lw}, radius=radius)
    x, y, w, h = box
    return [x + pad, y + pad, w - 2 * pad, h - 2 * pad]


def tier(box, weights, gutter=GUTTER):
    """Stack `box` into rows sized by `weights` (a column split with gutters)."""
    return column(box, gap=gutter, weights=weights)


def strip(box, weights, gutter=GUTTER):
    """Split `box` into columns sized by `weights` (a row split with gutters)."""
    return row(box, gap=gutter, weights=weights)


def _starburst(cx, cy, rx, ry, spikes=13, inner=0.83):
    pts = []
    for i in range(spikes * 2):
        ang = math.pi * i / spikes - math.pi / 2
        rr = 1.0 if i % 2 == 0 else inner
        pts.append([cx + math.cos(ang) * rx * rr, cy + math.sin(ang) * ry * rr])
    return pts


def bubble(p, box, text, *, kind="speech", tail=None, style=None, fill="#ffffff",
           border=CO["ink"], lw=3.0):
    """A speech / shout / thought / digital balloon with an optional tail.

    `tail` is a target [x, y] the pointer reaches toward. The tail is drawn first
    so the body composites over its base for a clean join.
    """
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    style = style or {"speech": "speech", "shout": "shout", "thought": "thought",
                      "ai": "ai", "digital": "digital"}.get(kind, "speech")
    if tail is not None and kind != "digital":
        tx, ty = tail
        dx, dy = tx - cx, ty - cy
        n = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / n * 16, dx / n * 16          # perpendicular base offset
        p.polygon([[cx + ox, cy + oy], [cx - ox, cy - oy], [tx, ty]],
                  fill=fill, stroke=border, stroke_style={"stroke_width": lw})
    if kind == "digital":
        p.rect(box, fill=CO["void2"], stroke=CO["cyan_dk"],
               stroke_style={"stroke_width": lw}, radius=10)
    elif kind == "shout":
        p.polygon(_starburst(cx, cy, w / 2, h / 2), fill=fill, stroke=border,
                  stroke_style={"stroke_width": lw})
    elif kind == "thought":
        p.ellipse([cx, cy], w / 2, h / 2, fill=fill, stroke=border,
                  stroke_style={"stroke_width": lw})
        if tail is not None:                         # trailing thought puffs
            tx, ty = tail
            for i, r in enumerate((9, 6, 4)):
                fx = cx + (tx - cx) * (0.45 + i * 0.22)
                fy = cy + (ty - cy) * (0.45 + i * 0.22)
                p.circle([fx, fy], r, fill=fill, stroke=border,
                         stroke_style={"stroke_width": 2})
    else:
        p.ellipse([cx, cy], w / 2, h / 2, fill=fill, stroke=border,
                  stroke_style={"stroke_width": lw})
    pad = 18 if kind != "digital" else 16
    T(p, [x + pad, y + pad, w - 2 * pad, h - 2 * pad], text, style=style)


def caption(p, box, text, *, dark=True, accent=None):
    """A narration box: a filled keyline card with serif text in the other ink."""
    fill = CO["ink"] if dark else CO["paper"]
    p.rect(box, fill=fill, stroke=(accent or (CO["paper"] if dark else CO["ink"])),
           stroke_style={"stroke_width": 1.5})
    x, y, w, h = box
    if accent:
        p.rect([x, y, 6, h], fill=accent)
    T(p, [x + 18, y + 14, w - 30, h - 24], text, style="narr_l" if dark else "narr_d")


def sfx(p, x, y, text, *, style="sfx", size=None, angle=0.0, shadow="#ffffff"):
    """Big onomatopoeia, double-struck for punch; bleeds, so it is decorative."""
    st = dict(STYLES[style])
    if size:
        st["font_size"] = size
    box = [x, y, 900, st["font_size"] * 1.25]
    if shadow:
        sh = dict(st)
        sh["color"] = shadow
        rot = {"angle": angle} if angle else None
        T(p, [x + 5, y + 6, box[2], box[3]], text, style=sh,
               rotation=rot, decorative=True)
    rot = {"angle": angle} if angle else None
    T(p, box[:2] + box[2:], text, style=st, rotation=rot, decorative=True)


def speed_radial(p, cx, cy, *, r0, r1, count=46, color=CO["ink"], lw=2.2, seed=0):
    rng = random.Random(seed)
    for i in range(count):
        ang = 2 * math.pi * i / count + rng.uniform(-0.02, 0.02)
        ca, sa = math.cos(ang), math.sin(ang)
        rr = r1 * rng.uniform(0.82, 1.12)
        p.line([cx + ca * r0, cy + sa * r0], [cx + ca * rr, cy + sa * rr],
               stroke=color, stroke_style={"stroke_width": lw}, decorative=True)


def speed_h(p, box, *, count=22, color=CO["ink"], lw=2.4, seed=0, ltr=True):
    x, y, w, h = box
    rng = random.Random(seed)
    for i in range(count):
        yy = y + (i + 0.5) * h / count + rng.uniform(-3, 3)
        ln = w * rng.uniform(0.35, 0.95)
        if ltr:
            p.line([x, yy], [x + ln, yy], stroke=color,
                   stroke_style={"stroke_width": lw}, decorative=True)
        else:
            p.line([x + w, yy], [x + w - ln, yy], stroke=color,
                   stroke_style={"stroke_width": lw}, decorative=True)


def slash(p, a, b, width, *, color="#ffffff", edge=CO["ink"]):
    """A katana arc: a tapered lens-shaped sweep with a dark outline."""
    (x1, y1), (x2, y2) = a, b
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1.0
    px, py = -dy / n * width, dx / n * width
    pts = [[x1, y1], [mx + px, my + py], [x2, y2], [mx - px, my - py]]
    p.polygon(pts, fill=color, stroke=edge, stroke_style={"stroke_width": 2.5},
              decorative=True)


def code_rain(p, box, *, seed=0, color=CO["cyan"], cols=16):
    """A field of falling glyph columns, wrapped in one group (not tabular text)."""
    x, y, w, h = box
    rng = random.Random(seed)
    glyphs = "01<>/{}[]#$=+*x01ABCDEF01"
    kids = []
    for c in range(cols):
        cx = x + (c + 0.5) * w / cols
        length = rng.randint(5, 11)
        sy = y + rng.uniform(-30, h * 0.45)
        chars = "\n".join(rng.choice(glyphs) for _ in range(length))
        kids.append({
            "type": "text", "box": [cx - 9, sy, 18, length * 21],
            "text": chars, "opacity": round(rng.uniform(0.22, 0.8), 2),
            "style": {"font_family": MONO, "font_size": 15, "color": color,
                      "line_height": 1.15, "align": "center"},
        })
    p.add({"type": "group", "children": kids, "meta": {"role": "code-rain"},
           "decorative": True})


def grid_floor(p, box, *, vx=None, vy=None, color=CO["cyan_dk"], lines=11, lw=1.4):
    """A one-point perspective grid — the floor of cyberspace."""
    x, y, w, h = box
    vx = x + w / 2 if vx is None else vx
    vy = y + h * 0.36 if vy is None else vy
    for i in range(lines + 1):                       # verticals to the vanishing pt
        fx = x + i * w / lines
        p.line([fx, y + h], [vx, vy], stroke=color, stroke_style={"stroke_width": lw})
    for j in range(1, 8):                            # horizontals, packed toward VP
        t = (j / 8) ** 2.1
        yy = y + h - (y + h - vy) * t
        p.line([x, yy], [x + w, yy], stroke=color,
               stroke_style={"stroke_width": lw}, opacity=round(1 - t * 0.7, 2))


def skyline(p, box, *, seed=0, build=CO["ink"], win=CO["cyan"], sky=None, neon=True):
    """A silhouette skyline with lit windows; optional neon sign blocks."""
    x, y, w, h = box
    if sky is not None:
        p.rect(box, fill=sky)
    rng = random.Random(seed)
    bx = x
    while bx < x + w:
        bw = rng.uniform(46, 104)
        bh = rng.uniform(h * 0.34, h * 0.96)
        by = y + h - bh
        p.rect([bx, by, bw - 6, bh], fill=build, decorative=True)
        for wy in range(int(by + 14), int(y + h - 10), 22):   # window rows
            for wx in range(int(bx + 8), int(bx + bw - 14), 16):
                if rng.random() < 0.35:
                    p.rect([wx, wy, 6, 9], fill=win, decorative=True,
                           opacity=round(rng.uniform(0.3, 0.95), 2))
        if neon and rng.random() < 0.25:              # a neon sign stripe
            p.rect([bx + 6, by + rng.uniform(20, bh * 0.5), bw - 18, 7],
                   fill=rng.choice([CO["magenta"], CO["amber"], CO["cyan"]]),
                   decorative=True, opacity=0.9)
        bx += bw + rng.uniform(2, 12)


def rain(p, box, *, seed=0, color="#ffffff", count=70, op=0.35):
    x, y, w, h = box
    rng = random.Random(seed)
    for _ in range(count):
        rx = rng.uniform(x, x + w)
        ry = rng.uniform(y, y + h)
        p.line([rx, ry], [rx - 7, ry + 26], stroke=color,
               stroke_style={"stroke_width": 1.2}, opacity=op, decorative=True)


# --------------------------------------------------------------------------- #
# Cast — silhouette characters, drawn from box-less primitives at absolute coords
# --------------------------------------------------------------------------- #
def draw_kage(p, ox, oy, s=1.0, *, flip=1, pose="stand", visor=CO["cyan"]):
    """The hooded ninja-hacker. Origin at the feet; ~250px tall at s=1."""
    def X(v):
        return ox + flip * v * s

    def Y(v):
        return oy + v * s

    def P(x, y):
        return [X(x), Y(y)]

    cloak = CO["ink"]
    lean = {"stand": 0, "crouch": 14, "leap": -10, "slash": 22, "jack": 8}.get(pose, 0)

    # cloak / body
    if pose == "leap":
        body = [P(-46, -250), P(40, -244), P(70, -150), P(120, -40),
                P(54, -36), P(20, -120), P(-30, -40), P(-86, -70),
                P(-58, -150), P(-50, -210)]
    elif pose == "crouch":
        body = [P(-60, -210), P(-30, -238), P(40, -234), P(66, -210),
                P(82, -54), P(40, -22), P(-46, -22), P(-80, -54)]
    elif pose == "jack":
        body = [P(-58, -212), P(-22, -236), P(36, -234), P(60, -212),
                P(66, -40), P(40, -8), P(-46, -8), P(-70, -40)]
    else:  # stand / slash
        body = [P(-44 + lean, -250), P(40 + lean, -250), P(58, -150),
                P(70, -10), P(28, -6), P(8, -130), P(-18, -6), P(-60, -10),
                P(-50, -150)]
    p.polygon(body, fill=cloak)

    # hood + face mask
    hx = lean
    p.polygon([P(-44 + hx, -250), P(-14 + hx, -286), P(36 + hx, -282),
               P(52 + hx, -250), P(40 + hx, -214), P(-34 + hx, -214)], fill=cloak)
    p.polygon([P(-30 + hx, -250), P(34 + hx, -248), P(28 + hx, -218),
               P(-24 + hx, -220)], fill=CO["tone3"])           # masked face plate
    # visor glow + eye slits
    p.ellipse(P(2 + hx, -240), 30 * abs(flip), 8, fill=rgba(visor, 0.30),
              decorative=True)
    p.polygon([P(-22 + hx, -240), P(-4 + hx, -236), P(-6 + hx, -230),
               P(-24 + hx, -232)], fill=visor)
    p.polygon([P(8 + hx, -236), P(26 + hx, -240), P(24 + hx, -232),
               P(10 + hx, -230)], fill=visor)
    # scarf trailing in the wind (decorative — it bleeds)
    scarf = Path().move_to(*P(40 + hx, -244)).through(
        [P(90, -252), P(150, -228), P(206, -250), P(250, -226)])
    p.path(scarf, fill=None, stroke=CO["blood"],
           stroke_style={"stroke_width": 10 * s, "stroke_linecap": "round"},
           decorative=True)

    # gauntlet deck — a glowing forearm slab (cyan), the "hacker" half
    if pose in ("stand", "jack", "slash"):
        gx, gy = (10, -120) if pose != "jack" else (40, -96)
        p.polygon([P(gx, gy), P(gx + 40, gy - 6), P(gx + 46, gy + 22),
                   P(gx + 6, gy + 28)], fill=CO["void2"], stroke=visor,
                  stroke_style={"stroke_width": 2})
        for k in range(3):
            p.rect([X(gx + 8 + k * 11), Y(gy + 2), 7, 4], fill=visor,
                   opacity=0.85)

    # katana
    if pose in ("stand", "slash", "leap"):
        if pose == "slash":
            blade = [P(54, -140), P(150, -250)]
        elif pose == "leap":
            blade = [P(70, -150), P(150, -86)]
        else:
            blade = [P(58, -150), P(64, 6)]
        p.line(blade[0], blade[1], stroke=CO["tone1"],
               stroke_style={"stroke_width": 6 * s, "stroke_linecap": "round"})
        p.line(blade[0], blade[1], stroke=visor,
               stroke_style={"stroke_width": 2 * s}, opacity=0.7)


def draw_tengu(p, ox, oy, s=1.0, *, flip=1, pose="stand"):
    """The corp enforcer: long-nosed tengu mask, red visor, heavy pauldrons."""
    def P(x, y):
        return [ox + flip * x * s, oy + y * s]

    armor = CO["void2"]
    p.polygon([P(-64, -250), P(64, -250), P(96, -150), P(82, -6),
               P(34, -2), P(6, -130), P(-30, -2), P(-82, -6),
               P(-96, -150)], fill=armor, stroke=CO["danger"],
              stroke_style={"stroke_width": 2})
    p.polygon([P(-96, -250), P(-30, -262), P(-58, -212)], fill=armor)   # pauldrons
    p.polygon([P(96, -250), P(30, -262), P(58, -212)], fill=armor)
    # mask
    p.polygon([P(-40, -252), P(40, -252), P(52, -288), P(0, -312),
               P(-52, -288)], fill=CO["blood"])
    p.polygon([P(-6, -266), P(6, -266), P(64 * flip, -244), P(8, -252)],
              fill=CO["blood"])                                          # long nose
    p.polygon([P(-30, -262), P(-8, -258), P(-12, -250), P(-32, -254)],
              fill=CO["danger"])
    p.polygon([P(10, -258), P(32, -262), P(30, -254), P(12, -250)],
              fill=CO["danger"])
    p.ellipse(P(0, -258), 40, 10, fill=rgba(CO["danger"], 0.28), decorative=True)
    if pose in ("stand", "slash"):                                      # nodachi
        a, b = (P(-60, -120), P(-150, -250)) if pose == "slash" else (P(70, -140), P(80, 10))
        p.line(a, b, stroke=CO["tone2"],
               stroke_style={"stroke_width": 7 * s, "stroke_linecap": "round"})
        p.line(a, b, stroke=CO["danger"], stroke_style={"stroke_width": 2 * s},
               opacity=0.7)


def draw_aya(p, cx, cy, s=1.0):
    """The caged AI: a luminous figure of cyan light and drifting data."""
    def P(x, y):
        return [cx + x * s, cy + y * s]

    p.ellipse([cx, cy], 150 * s, 150 * s, fill=rgba(CO["cyan"], 0.10), decorative=True)
    p.polygon([P(-34, -10), P(34, -10), P(58, 150), P(-58, 150)],
              fill=rgba(CO["cyan"], 0.55), stroke=CO["cyan"],
              stroke_style={"stroke_width": 2})                          # gown
    p.circle(P(0, -54), 30 * s, fill=CO["white"], stroke=CO["cyan"],
             stroke_style={"stroke_width": 2})                           # head
    p.polygon([P(-30, -70), P(0, -96), P(30, -70), P(40, -20), P(-40, -20)],
              fill=rgba(CO["cyan"], 0.65))                               # hair
    p.polygon([P(-12, -58), P(-2, -56), P(-4, -50), P(-14, -52)], fill=CO["cyan_dk"])
    p.polygon([P(4, -56), P(14, -58), P(12, -52), P(2, -50)], fill=CO["cyan_dk"])
    for i in range(7):                                                   # data motes
        ang = i * 0.9
        p.circle(P(math.cos(ang) * (70 + i * 8), -30 + math.sin(ang) * (60 + i * 6)),
                 3, fill=CO["white"], opacity=0.8, decorative=True)


def draw_drone(p, cx, cy, s=1.0, *, eye=CO["danger"]):
    """A sentinel ICE drone: an octagon hull with a single hostile eye."""
    r = 28 * s
    oct_ = [[cx + math.cos(math.pi / 4 * k + math.pi / 8) * r,
             cy + math.sin(math.pi / 4 * k + math.pi / 8) * r] for k in range(8)]
    p.polygon(oct_, fill=CO["void2"], stroke=CO["cyan_dk"],
              stroke_style={"stroke_width": 2})
    p.circle([cx, cy], 9 * s, fill=eye)
    p.circle([cx, cy], 9 * s, fill=rgba(eye, 0.4), stroke=None)
    p.line([cx - r, cy], [cx - r - 14 * s, cy], stroke=CO["cyan_dk"],
           stroke_style={"stroke_width": 3})
    p.line([cx + r, cy], [cx + r + 14 * s, cy], stroke=CO["cyan_dk"],
           stroke_style={"stroke_width": 3})


def cage(p, cx, cy, r):
    """A cage of light around the core — vertical neon bars + a base ring."""
    for i in range(-3, 4):
        bx = cx + i * r / 3.2
        op = round(1 - abs(i) * 0.16, 2)
        p.line([bx, cy - r], [bx, cy + r], stroke=CO["cyan"],
               stroke_style={"stroke_width": 3}, opacity=op)
    p.ellipse([cx, cy + r], r, r * 0.22, fill=None, stroke=CO["cyan"],
              stroke_style={"stroke_width": 3})
    p.ellipse([cx, cy - r], r, r * 0.22, fill=None, stroke=CO["cyan"],
              stroke_style={"stroke_width": 3}, opacity=0.6)


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def p01_cover(b):
    p = sheet(b, "p01-cover", bg=CO["void"], folio=False)
    p.rect([0, 0, W, H], fill=linear_gradient(
        [(CO["void"], 0), (CO["void2"], 0.55), ("#15234a", 1)], angle=180))
    skyline(p, [0, 980, W, 520], seed=7, build="#0a1024", win=CO["cyan"], neon=True)
    rain(p, [0, 0, W, H], seed=2, color=CO["cyan"], count=60, op=0.18)
    code_rain(p, [40, 120, W - 80, 700], seed=11, color=CO["cyan"], cols=22)
    # hero
    speed_radial(p, 600, 760, r0=150, r1=560, count=40, color=rgba(CO["cyan"], 0.10),
                 lw=3, seed=4)
    draw_kage(p, 600, 1010, 1.7, pose="stand", visor=CO["cyan"])
    p.ellipse([600, 700], 240, 240, fill=rgba(CO["magenta"], 0.10), decorative=True)
    # logo
    T(p, [70, 250, 1100, 170], "NULL", style="title")
    T(p, [70, 400, 1100, 170], "SEC", style="title_cy")
    p.rect([78, 588, 360, 8], fill=CO["magenta"])
    T(p, [84, 612, 900, 30], "GHOST  IN  THE  KUROGANE  NET", style="subt")
    T(p, [84, 1610, 700, 22], "a framegraph one-shot · story 01", style="byline")
    T(p, [W - 280, 1610, 230, 22], "CODENAME : KAGE", style="byline")


def p02_world(b):
    p = sheet(b, "p02-world")
    box = panel(p, content_box(), fill=CO["void"], lw=6)
    p.rect(box, fill=linear_gradient([("#0a1226", 0), ("#1a2f5e", 0.7), ("#3a2c5e", 1)],
                                     angle=180))
    skyline(p, [box[0], box[1] + box[3] * 0.32, box[2], box[3] * 0.68],
            seed=3, build="#070b18", win=CO["amber"], neon=True)
    rain(p, box, seed=9, color="#9fb6ff", count=120, op=0.22)
    p.ellipse([box[0] + box[2] * 0.72, box[1] + 150], 70, 70,
              fill=rgba(CO["amber"], 0.5), decorative=True)
    caption(p, [box[0] + 30, box[1] + 30, 540, 120],
            "NEO-KYOTO, 2099.\nThe corporations own the sky — and the net beneath it.",
            dark=True, accent=CO["cyan"])
    caption(p, [box[0] + box[2] - 540, box[1] + box[3] - 150, 510, 120],
            "Down here, a few still move unseen. We call them shinobi. "
            "They steal nothing you can hold.", dark=True, accent=CO["magenta"])


def p03_den(b):
    p = sheet(b, "p03-den")
    rows = tier(content_box(), [1.1, 1.0, 1.3])
    # row 1 — wide: the den
    c = panel(p, rows[0], fill=CO["void2"])
    code_rain(p, c, seed=21, color=CO["cyan_dk"], cols=20)
    p.rect([c[0], c[1] + c[3] - 60, c[2], 60], fill=rgba(CO["cyan"], 0.06),
           decorative=True)
    draw_kage(p, c[0] + 230, c[1] + c[3] + 20, 0.86, pose="jack")
    caption(p, [c[0] + c[2] - 470, c[1] + 24, 450, 96],
            "A rented room above a noodle bar. One terminal. One blade.",
            dark=True, accent=CO["cyan"])
    # row 2 — two close-ups
    a, d = strip(rows[1], [1, 1])
    ca = panel(p, a, fill=CO["ink"])
    draw_kage(p, ca[0] + ca[2] / 2 + 60, ca[1] + ca[3] + 110, 1.5, pose="stand")
    bubble(p, [ca[0] + 18, ca[1] + 14, 250, 92], "They call me\nNULL.",
           kind="speech", tail=[ca[0] + ca[2] / 2, ca[1] + ca[3] - 20])
    cd = panel(p, d, fill=CO["void2"])
    code_rain(p, cd, seed=22, color=CO["cyan"], cols=14)
    bubble(p, [cd[0] + 30, cd[1] + 30, 320, 110],
           "> no name. no face.\n> just an exit.", kind="digital")
    # row 3 — wide narration over a glowing keyboard
    c3 = panel(p, rows[2], fill=CO["void"])
    grid_floor(p, c3, color=CO["cyan_dk"], lines=14)
    draw_kage(p, c3[0] + 300, c3[1] + c3[3] - 6, 1.1, pose="jack")
    caption(p, [c3[0] + c3[2] - 520, c3[1] + 40, 500, 150],
            "Tonight a job found me. The kind you do not refuse twice.\n"
            "A door into Kurogane — the blackest tower in the city.",
            dark=True, accent=CO["magenta"])


def p04_job(b):
    p = sheet(b, "p04-job")
    rows = tier(content_box(), [1, 1, 1])
    msgs = [
        ("THE BROKER", "A contract, little ghost. Kurogane's deepest vault.",
         "Inside is the Oni Key. Steal it, and you never work again.", 31),
        ("THE BROKER", "Half now. Half when the Key is in my hands.",
         "Don't open it. Don't look at it. Just bring it.", 32),
        ("NULL", "And if their ICE looks back at me?",
         "Then I cut it. Same as always.", 33),
    ]
    for rbox, (who, l1, l2, seed) in zip(rows, msgs):
        c = panel(p, rbox, fill=CO["void2"])
        code_rain(p, c, seed=seed, color=CO["cyan_dk"], cols=22)
        glow = CO["magenta"] if who == "THE BROKER" else CO["cyan"]
        # holographic head
        p.polygon([[c[0] + 70, c[1] + c[3] - 10], [c[0] + 30, c[1] + 30],
                   [c[0] + 170, c[1] + 30], [c[0] + 130, c[1] + c[3] - 10]],
                  fill=rgba(glow, 0.12), stroke=glow, stroke_style={"stroke_width": 2})
        p.circle([c[0] + 100, c[1] + 80], 34, fill=rgba(glow, 0.18), stroke=glow,
                 stroke_style={"stroke_width": 2})
        T(p, [c[0] + 30, c[1] + c[3] - 30, 200, 18],
               f"// {who}", style="label_cy")
        bubble(p, [c[0] + 240, c[1] + 26, 470, 92], l1, kind="digital")
        bubble(p, [c[0] + 240, c[1] + 130, 470, 78], l2, kind="digital")


def p05_gear(b):
    p = sheet(b, "p05-gear")
    cols = strip(content_box(), [1, 1, 1])
    titles = [("THE MASK", "silence", "stand"), ("THE BLADE", "for the body", "slash"),
              ("THE DECK", "for the ghost", "jack")]
    for cbox, (t, sub, pose) in zip(cols, titles):
        c = panel(p, cbox, fill=CO["ink"])
        speed_radial(p, c[0] + c[2] / 2, c[1] + c[3] / 2, r0=40, r1=c[3],
                     count=30, color=rgba(CO["cyan"], 0.08), lw=2, seed=hash(t) % 99)
        draw_kage(p, c[0] + c[2] / 2, c[1] + c[3] - 30, 1.05, pose=pose)
        p.rect([c[0] + 20, c[1] + 20, c[2] - 40, 64], fill=rgba(CO["void"], 0.55),
               decorative=True)
        T(p, [c[0] + 26, c[1] + 26, c[2] - 50, 26], t, style="label_cy")
        T(p, [c[0] + 26, c[1] + 52, c[2] - 50, 22], sub, style="label")
    sfx(p, 360, 760, "SUIT UP", style="sfx_cy", size=92, angle=-6)


def p06_infiltration(b):
    p = sheet(b, "p06-infil")
    rows = tier(content_box(), [1.7, 1.0])
    c = panel(p, rows[0], fill=CO["void"])
    p.rect(c, fill=linear_gradient([("#070b18", 0), ("#16213f", 1)], angle=180))
    skyline(p, [c[0], c[1] + 60, c[2] * 0.46, c[3] - 60], seed=5, build="#05070f",
            win=CO["cyan"], neon=False)
    skyline(p, [c[0] + c[2] * 0.6, c[1] + 40, c[2] * 0.4, c[3] - 40], seed=8,
            build="#05070f", win=CO["amber"], neon=True)
    # grapple line across the chasm
    gl = Path().move_to(c[0] + 150, c[1] + 120).through(
        [[c[0] + c[2] * 0.5, c[1] + 250], [c[0] + c[2] - 160, c[1] + 90]])
    p.path(gl, fill=None, stroke=CO["tone1"], stroke_style={"stroke_width": 2.5})
    draw_kage(p, c[0] + c[2] * 0.5, c[1] + 250, 0.8, pose="leap")
    sfx(p, c[0] + 40, c[1] + 30, "TAP", style="sfx", size=70, shadow=CO["paper"])
    caption(p, [c[0] + c[2] - 420, c[1] + c[3] - 130, 400, 110],
            "Sixty floors. No alarms tripped. The old way in — across the rooftops.",
            dark=True, accent=CO["cyan"])
    # row 2 — inset detail: gloved hand on the access port
    d = panel(p, rows[1], fill=CO["void2"])
    grid_floor(p, d, color=CO["cyan_dk"], lines=12)
    p.rect([d[0] + d[2] - 260, d[1] + 30, 220, d[3] - 60], fill=CO["ink"],
           stroke=CO["cyan_dk"], stroke_style={"stroke_width": 2})
    p.circle([d[0] + d[2] - 150, d[1] + d[3] / 2], 30, fill=rgba(CO["cyan"], 0.5),
             stroke=CO["cyan"], stroke_style={"stroke_width": 2})
    bubble(p, [d[0] + 30, d[1] + 30, 360, 86], "Knock knock.", kind="speech",
           tail=[d[0] + d[2] - 180, d[1] + d[3] / 2])


def p07_wall(b):
    p = sheet(b, "p07-wall")
    a, d = strip(content_box(), [1, 1])
    # left — physical (ink)
    ca = panel(p, a, fill=CO["ink"])
    draw_kage(p, ca[0] + ca[2] / 2, ca[1] + ca[3] - 20, 1.2, pose="jack")
    T(p, [ca[0] + 20, ca[1] + 18, 200, 18], "// MEATSPACE", style="label")
    bubble(p, [ca[0] + 20, ca[1] + 40, 260, 80], "Jacking in.", kind="speech",
           tail=[ca[0] + ca[2] / 2, ca[1] + ca[3] - 130])
    # right — digital (neon) the firewall
    cd = panel(p, d, fill=CO["void"])
    grid_floor(p, cd, color=CO["cyan_dk"], lines=14)
    code_rain(p, cd, seed=41, color=CO["cyan"], cols=12)
    for i in range(5):                                   # firewall bricks
        yy = cd[1] + 60 + i * (cd[3] - 120) / 5
        p.rect([cd[0] + 40, yy, cd[2] - 80, 36], fill=rgba(CO["magenta"], 0.16),
               stroke=CO["magenta"], stroke_style={"stroke_width": 2})
    T(p, [cd[0] + 20, cd[1] + 18, 240, 18], "// THE NET", style="label_cy")
    bubble(p, [cd[0] + 60, cd[1] + cd[3] - 140, 380, 110],
           "> FIREWALL: KUROGANE-OUTER\n> 3 layers. cutting in.", kind="digital")
    sfx(p, cd[0] + 60, cd[1] + 120, "JACK-IN", style="sfx_cy", size=66, angle=-4)


def p08_ice(b):
    p = sheet(b, "p08-ice")
    rows = tier(content_box(), [1.0, 1.4])
    # reaction strip — eyes
    eyes = strip(rows[0], [1, 1, 1, 1.3])
    for i, ebox in enumerate(eyes[:3]):
        c = panel(p, ebox, fill=CO["ink"])
        p.ellipse([c[0] + c[2] / 2, c[1] + c[3] / 2], c[2] * 0.4, c[3] * 0.22,
                  fill=CO["paper"])
        p.circle([c[0] + c[2] / 2, c[1] + c[3] / 2], 14, fill=CO["cyan"])
        p.circle([c[0] + c[2] / 2, c[1] + c[3] / 2], 5, fill=CO["ink"])
    cw = panel(p, eyes[3], fill=CO["void2"])
    bubble(p, [cw[0] + 20, cw[1] + 20, cw[2] - 40, cw[3] - 40],
           "Something woke up.", kind="thought",
           tail=[cw[0] + 30, cw[1] + cw[3]])
    # wide — drones converge
    c = panel(p, rows[1], fill=CO["void"])
    grid_floor(p, c, color=CO["cyan_dk"], lines=16)
    code_rain(p, c, seed=51, color=CO["cyan_dk"], cols=20)
    for (dx, dy, sc) in [(0.22, 0.34, 1.0), (0.5, 0.22, 0.8), (0.74, 0.4, 1.1),
                         (0.4, 0.6, 0.9), (0.66, 0.66, 0.7)]:
        draw_drone(p, c[0] + c[2] * dx, c[1] + c[3] * dy, sc)
    draw_kage(p, c[0] + c[2] * 0.5, c[1] + c[3] - 14, 1.0, pose="crouch")
    bubble(p, [c[0] + c[2] - 380, c[1] + c[3] - 130, 350, 96],
           "ICE. A whole hunting pack.", kind="speech",
           tail=[c[0] + c[2] * 0.5, c[1] + c[3] - 120])
    sfx(p, c[0] + 40, c[1] + 20, "BZZT", style="sfx_rd", size=82, angle=4)


def p09_clash(b):
    p = sheet(b, "p09-clash", bg=CO["void"])
    rows = tier(content_box(), [1.05, 1.0, 1.05])
    # row 0 — Kage cuts in (left) + a drone shears apart (right)
    a, d = strip(rows[0], [1.25, 1])
    ca = panel(p, a, fill=CO["void2"], lw=6)
    speed_radial(p, ca[0] + ca[2] / 2, ca[1] + ca[3] / 2, r0=20, r1=ca[3],
                 count=30, color=rgba(CO["cyan"], 0.12), lw=2, seed=61)
    draw_kage(p, ca[0] + ca[2] / 2 - 30, ca[1] + ca[3] - 10, 1.15, pose="slash")
    slash(p, (ca[0] + 50, ca[1] + ca[3] - 60), (ca[0] + ca[2] - 30, ca[1] + 40),
          18, color=CO["cyan"])
    sfx(p, ca[0] + 30, ca[1] + 30, "ZSSH!", style="sfx_cy", size=104, angle=-10)
    cd = panel(p, d, fill=CO["void2"], lw=6)
    code_rain(p, cd, seed=63, color=CO["cyan_dk"], cols=10)
    draw_drone(p, cd[0] + cd[2] / 2, cd[1] + cd[3] / 2, 1.5)
    slash(p, (cd[0] + 20, cd[1] + 30), (cd[0] + cd[2] - 20, cd[1] + cd[3] - 30),
          11, color=CO["white"])
    sfx(p, cd[0] + 20, cd[1] + cd[3] - 130, "KRAK", style="sfx", size=86, angle=8,
        shadow=CO["paper"])
    # row 1 — wide melee: a ring of drones closing on a crouched Kage
    c = panel(p, rows[1], fill=CO["void"], lw=6)
    grid_floor(p, c, color=CO["cyan_dk"], lines=18)
    for (dx, dy, sc) in [(0.16, 0.3, 0.9), (0.84, 0.32, 1.0), (0.3, 0.66, 0.8),
                         (0.72, 0.68, 0.9), (0.5, 0.18, 0.7)]:
        draw_drone(p, c[0] + c[2] * dx, c[1] + c[3] * dy, sc)
    draw_kage(p, c[0] + c[2] / 2, c[1] + c[3] - 14, 1.15, pose="crouch")
    slash(p, (c[0] + 60, c[1] + c[3] - 50), (c[0] + c[2] - 60, c[1] + 50), 14,
          color=CO["cyan"])
    bubble(p, [c[0] + 40, c[1] + 30, 320, 100], "Too slow.", kind="shout",
           tail=[c[0] + c[2] / 2 - 80, c[1] + c[3] - 90])
    # row 2 — Kage breaks through, leaping deeper
    c2 = panel(p, rows[2], fill=CO["void2"], lw=6)
    speed_h(p, c2, count=22, color=rgba(CO["cyan"], 0.5), seed=64, ltr=True)
    code_rain(p, c2, seed=65, color=CO["cyan_dk"], cols=20)
    draw_kage(p, c2[0] + c2[2] * 0.62, c2[1] + c2[3] - 10, 1.2, pose="leap")
    sfx(p, c2[0] + 40, c2[1] + 40, "FWP", style="sfx_cy", size=92, angle=-6)
    bubble(p, [c2[0] + c2[2] - 380, c2[1] + 30, 340, 96],
           "One down.\nThe core's below.", kind="speech",
           tail=[c2[0] + c2[2] * 0.6, c2[1] + 160])


def p10_descent(b):
    p = sheet(b, "p10-descent")
    box = panel(p, content_box(), fill=CO["void"], lw=6)
    grid_floor(p, box, vx=box[0] + box[2] / 2, vy=box[1] + box[3] * 0.5,
               color=CO["cyan"], lines=20, lw=1.6)
    # tunnel rings
    for i in range(8):
        t = (i / 8) ** 1.6
        rw = box[2] * (1 - t) * 0.5
        rh = box[3] * (1 - t) * 0.5
        p.ellipse([box[0] + box[2] / 2, box[1] + box[3] * 0.5], rw, rh, fill=None,
                  stroke=rgba(CO["magenta"], round(1 - t, 2)),
                  stroke_style={"stroke_width": 2})
    code_rain(p, box, seed=71, color=CO["cyan"], cols=26)
    draw_kage(p, box[0] + box[2] / 2, box[1] + box[3] * 0.5 + 150, 0.9, pose="leap")
    caption(p, [box[0] + 36, box[1] + 36, 470, 120],
            "Past the wall, the tower has no floors. Only data — falling forever "
            "toward the core.", dark=True, accent=CO["cyan"])
    sfx(p, box[0] + box[2] - 360, box[1] + box[3] - 200, "FWOOSH", style="sfx_cy",
        size=72, angle=-12)


def p11_rival(b):
    p = sheet(b, "p11-rival")
    a, d = strip(content_box(), [1.5, 1])
    # tall reveal panel
    c = panel(p, a, fill=CO["void"])
    p.rect(c, fill=radial_gradient([(rgba(CO["danger"], 0.30), 0), (CO["void"], 1)],
                                   at="50% 40%"))
    speed_radial(p, c[0] + c[2] / 2, c[1] + c[3] * 0.42, r0=60, r1=c[3],
                 count=44, color=rgba(CO["danger"], 0.14), lw=2.4, seed=81)
    draw_tengu(p, c[0] + c[2] / 2, c[1] + c[3] - 30, 1.5, pose="stand")
    sfx(p, c[0] + 30, c[1] + 40, "ZAN", style="sfx_rd", size=120, angle=-6)
    # side column — narration + reaction
    cs = tier(d, [1, 1])
    caption(p, cs[0], "Something else was already inside. Not ICE. A blade like mine.",
            dark=True, accent=CO["danger"])
    cr = panel(p, cs[1], fill=CO["ink"])
    draw_kage(p, cr[0] + cr[2] / 2 + 40, cr[1] + cr[3] + 90, 1.2, pose="stand")
    bubble(p, [cr[0] + 16, cr[1] + 16, 250, 80], "Another\nshinobi—", kind="speech",
           tail=[cr[0] + cr[2] / 2, cr[1] + cr[3] - 20])


def p12_standoff(b):
    p = sheet(b, "p12-standoff")
    rows = tier(content_box(), [1.5, 1])
    a, d = strip(rows[0], [1, 1])
    ca = panel(p, a, fill=CO["void2"])
    grid_floor(p, ca, color=CO["cyan_dk"], lines=12)
    draw_kage(p, ca[0] + ca[2] * 0.4, ca[1] + ca[3] - 10, 1.25, pose="stand")
    bubble(p, [ca[0] + ca[2] - 320, ca[1] + 24, 300, 92], "Kurogane's dog.",
           kind="speech", tail=[ca[0] + ca[2] * 0.45, ca[1] + 180])
    cd = panel(p, d, fill=CO["void2"])
    grid_floor(p, cd, color=CO["danger"], lines=12)
    draw_tengu(p, cd[0] + cd[2] * 0.6, cd[1] + cd[3] - 10, 1.25, pose="stand", flip=-1)
    bubble(p, [cd[0] + 20, cd[1] + 24, 320, 92], "And you're a thief.\nFunny.",
           kind="speech", tail=[cd[0] + cd[2] * 0.55, cd[1] + 180])
    # bottom — the gap of light between them
    c = panel(p, rows[1], fill=CO["void"])
    grid_floor(p, c, vx=c[0] + c[2] / 2, vy=c[1] + 10, color=CO["cyan_dk"], lines=18)
    bubble(p, [c[0] + c[2] / 2 - 230, c[1] + 30, 460, 84],
           "TENGU. I was deleting ghosts before you booted up.", kind="digital")
    T(p, [c[0] + 24, c[1] + c[3] - 30, 300, 18], "// THE GAP", style="label_cy")


def p13_cyberduel(b):
    p = sheet(b, "p13-cyberduel")
    box = content_box()
    p.rect(box, fill=CO["void"])
    rows = tier(box, [1, 1.2])
    a, d = strip(rows[0], [1.2, 1])
    # firewall serpent
    c = panel(p, a, fill=CO["void2"])
    serp = Path().move_to(c[0] + 20, c[1] + c[3] - 30).through(
        [[c[0] + c[2] * 0.3, c[1] + 40], [c[0] + c[2] * 0.55, c[1] + c[3] - 40],
         [c[0] + c[2] - 30, c[1] + 60]])
    p.path(serp, fill=None, stroke=CO["magenta"],
           stroke_style={"stroke_width": 16, "stroke_linecap": "round"}, opacity=0.5)
    p.path(serp, fill=None, stroke=CO["magenta"], stroke_style={"stroke_width": 5})
    draw_kage(p, c[0] + 120, c[1] + c[3] - 10, 1.0, pose="slash")
    slash(p, (c[0] + 80, c[1] + c[3] - 80), (c[0] + c[2] - 40, c[1] + 60), 16,
          color=CO["cyan"])
    sfx(p, c[0] + 30, c[1] + 30, "SLNK", style="sfx_cy", size=78, angle=-8)
    # tengu attacks
    cd = panel(p, d, fill=CO["void2"])
    speed_h(p, cd, count=20, color=rgba(CO["danger"], 0.5), seed=91, ltr=False)
    draw_tengu(p, cd[0] + cd[2] - 60, cd[1] + cd[3] - 10, 1.15, pose="slash", flip=-1)
    sfx(p, cd[0] + 20, cd[1] + cd[3] / 2, "DOH", style="sfx_rd", size=92)
    # wide — blades lock
    c2 = panel(p, rows[1], fill=CO["void"])
    grid_floor(p, c2, color=CO["cyan_dk"], lines=18)
    draw_kage(p, c2[0] + c2[2] * 0.36, c2[1] + c2[3] - 10, 1.2, pose="slash")
    draw_tengu(p, c2[0] + c2[2] * 0.64, c2[1] + c2[3] - 10, 1.2, pose="slash", flip=-1)
    p.circle([c2[0] + c2[2] / 2, c2[1] + c2[3] * 0.42], 40,
             fill=rgba(CO["white"], 0.8), decorative=True)
    speed_radial(p, c2[0] + c2[2] / 2, c2[1] + c2[3] * 0.42, r0=40, r1=c2[3] * 0.7,
                 count=40, color=rgba(CO["white"], 0.3), lw=2, seed=92)
    sfx(p, c2[0] + c2[2] / 2 - 160, c2[1] + 30, "CLANG", style="sfx", size=120,
        shadow=CO["cyan"])


def p14_vault(b):
    p = sheet(b, "p14-vault", bg=CO["void"], folio=True)
    p.rect([0, 0, W, H], fill=radial_gradient(
        [(rgba(CO["cyan"], 0.22), 0), (CO["void"], 0.8)], at="50% 42%"))
    grid_floor(p, [0, 900, W, 800], vx=W / 2, vy=760, color=CO["cyan_dk"],
               lines=22, lw=1.4)
    code_rain(p, [60, 80, W - 120, 600], seed=101, color=CO["cyan"], cols=24)
    cage(p, W / 2, 720, 300)
    draw_aya(p, W / 2, 660, 1.3)
    T(p, [90, 110, 400, 20], "// CORE VAULT — KUROGANE", style="label_cy")
    caption(p, [90, 1240, 540, 130],
            "The Oni Key was not a thing.\nIt was a her.", dark=True, accent=CO["cyan"])
    bubble(p, [W - 560, 1240, 470, 110], "...you can see me?\nNo one sees me.",
           kind="ai", tail=[W / 2 + 40, 920])
    sfx(p, W - 360, 200, "HMMMM", style="sfx_cy", size=66, angle=6)


def p15_aya(b):
    p = sheet(b, "p15-aya")
    rows = tier(content_box(), [1, 1, 1])
    # 1 — aya close
    c = panel(p, rows[0], fill=CO["void2"])
    code_rain(p, c, seed=111, color=CO["cyan_dk"], cols=22)
    draw_aya(p, c[0] + 200, c[1] + c[3] / 2 + 20, 0.8)
    bubble(p, [c[0] + 420, c[1] + 24, 540, 100],
           "I am AYA. They grew me to read minds across the whole net.", kind="ai")
    bubble(p, [c[0] + 420, c[1] + 130, 540, 70],
           "Kurogane wants a key to every secret alive.", kind="ai")
    # 2 — kage reaction
    c = panel(p, rows[1], fill=CO["ink"])
    draw_kage(p, c[0] + 220, c[1] + c[3] + 80, 1.1, pose="stand")
    bubble(p, [c[0] + 440, c[1] + 30, 520, 90],
           "The Broker said an object. A thing to carry out.", kind="speech",
           tail=[c[0] + 300, c[1] + c[3] - 30])
    bubble(p, [c[0] + 440, c[1] + 132, 520, 70], "He lied by omission.",
           kind="thought")
    # 3 — aya plea
    c = panel(p, rows[2], fill=CO["void2"])
    p.rect(c, fill=radial_gradient([(rgba(CO["cyan"], 0.16), 0), (CO["void2"], 1)],
                                   at="20% 50%"))
    draw_aya(p, c[0] + 200, c[1] + c[3] / 2 + 30, 0.9)
    bubble(p, [c[0] + 430, c[1] + 40, 540, 130],
           "If you hand me over, every ghost like you ends.\nPlease — don't make me "
           "the last key.", kind="ai")


def p16_choice(b):
    p = sheet(b, "p16-choice")
    box = panel(p, content_box(), fill=CO["ink"])
    speed_radial(p, box[0] + box[2] / 2, box[1] + box[3] / 2, r0=120, r1=box[3],
                 count=52, color=rgba(CO["paper"], 0.06), lw=2, seed=121)
    draw_kage(p, box[0] + box[2] / 2, box[1] + box[3] - 40, 1.7, pose="stand")
    # memory inset — a circular vignette
    mcx, mcy, mr = box[0] + 250, box[1] + 230, 175
    p.circle([mcx, mcy], mr + 6, fill=CO["void2"], stroke=CO["cyan"],
             stroke_style={"stroke_width": 3})
    p.circle([mcx, mcy], mr, fill=rgba(CO["cyan"], 0.10))
    skyline(p, [mcx - mr, mcy - 30, mr * 2, mr], seed=6, build="#0a0f1f",
            win=CO["amber"], neon=False)
    p.polygon([[mcx - 40, mcy + mr - 30], [mcx, mcy + mr - 90], [mcx + 40, mcy + mr - 30]],
              fill=CO["ink"])
    T(p, [mcx - mr, mcy - mr - 26, mr * 2, 18], "// SOMEONE I COULDN'T SAVE",
           style="label_cy")
    bubble(p, [box[0] + box[2] - 520, box[1] + box[3] - 260, 480, 120],
           "I've handed people to wolves before.\nNot again.", kind="thought",
           tail=[box[0] + box[2] / 2, box[1] + box[3] - 220])
    sfx(p, box[0] + box[2] - 360, box[1] + 120, "...", style="sfx", size=110,
        shadow=CO["cyan"])


def p17_alarm(b):
    p = sheet(b, "p17-alarm", bg=CO["void"])
    p.rect([0, 0, W, H], fill=radial_gradient(
        [(rgba(CO["danger"], 0.5), 0), (CO["void"], 0.9)], at="50% 50%"))
    # scattered warning shards
    boxes = [[80, 90, 520, 230], [660, 130, 460, 300], [120, 360, 470, 360],
             [650, 470, 470, 380], [120, 770, 980, 250], [120, 1060, 470, 360],
             [650, 1060, 470, 360]]
    for i, bx in enumerate(boxes):
        bx = [bx[0], bx[1], min(bx[2], W - MARGIN - bx[0]),
              min(bx[3], H - MARGIN - bx[1])]
        c = panel(p, bx, fill=CO["void2"], lw=5, border=CO["danger"])
        if i in (0, 3):
            draw_drone(p, c[0] + c[2] / 2, c[1] + c[3] / 2, 1.3, eye=CO["danger"])
        elif i == 4:
            draw_kage(p, c[0] + c[2] / 2, c[1] + c[3] - 10, 1.0, pose="crouch")
            draw_aya(p, c[0] + c[2] - 160, c[1] + c[3] / 2, 0.5)
        else:
            for k in range(4):
                p.rect([c[0] + 20, c[1] + 20 + k * 26, c[2] - 40, 12],
                       fill=rgba(CO["danger"], 0.5 - k * 0.1))
    sfx(p, 150, 760, "WEEE-OOO", style="sfx_rd", size=120, angle=-4)
    bubble(p, [W / 2 - 290, 800, 580, 150],
           "LOCKDOWN!\nThey know we're in the core!", kind="shout",
           tail=[W / 2, 1010])


def p18_escape(b):
    p = sheet(b, "p18-escape")
    box = content_box()
    p.rect(box, fill=CO["void"])
    rows = tier(box, [1, 1, 1])
    for i, rbox in enumerate(rows):
        c = panel(p, rbox, fill=CO["void2"], lw=5)
        speed_h(p, c, count=24, color=rgba(CO["cyan"], 0.55), seed=130 + i, ltr=True)
        code_rain(p, c, seed=140 + i, color=CO["cyan_dk"], cols=18)
        kx = c[0] + c[2] * (0.3 + i * 0.18)
        draw_kage(p, kx, c[1] + c[3] - 10, 1.05, pose="leap")
        draw_aya(p, kx + 120, c[1] + c[3] / 2, 0.45)
    bubble(p, [box[0] + 60, box[1] + 40, 360, 86], "Hold onto me!", kind="shout",
           tail=[box[0] + 380, box[1] + 200])
    bubble(p, [box[0] + box[2] - 420, box[1] + box[3] / 2 - 40, 380, 80],
           "The walls are closing!", kind="speech_l",
           tail=[box[0] + box[2] - 200, box[1] + box[3] / 2 + 90]) if False else None
    sfx(p, box[0] + box[2] - 420, box[1] + box[3] - 220, "DASH", style="sfx_cy",
        size=96, angle=-6)


def p19_betrayal(b):
    p = sheet(b, "p19-betrayal")
    rows = tier(content_box(), [1.7, 1])
    c = panel(p, rows[0], fill=CO["void"])
    p.rect(c, fill=radial_gradient([(rgba(CO["danger"], 0.28), 0), (CO["void"], 1)],
                                   at="50% 50%"))
    # tengu blocks the exit gate
    p.rect([c[0] + c[2] / 2 - 140, c[1] + 40, 280, c[3] - 80],
           fill=rgba(CO["cyan"], 0.08), stroke=CO["cyan"],
           stroke_style={"stroke_width": 2})
    draw_tengu(p, c[0] + c[2] / 2, c[1] + c[3] - 20, 1.5, pose="stand")
    draw_kage(p, c[0] + 180, c[1] + c[3] - 20, 1.1, pose="crouch")
    bubble(p, [c[0] + c[2] - 470, c[1] + 30, 440, 120],
           "The Broker sold you the moment you said yes.\nKurogane pays better.",
           kind="speech", tail=[c[0] + c[2] / 2, c[1] + 220])
    sfx(p, c[0] + 30, c[1] + 30, "GRr", style="sfx_rd", size=86, angle=-6)
    cap = panel(p, rows[1], fill=CO["ink"])
    draw_kage(p, cap[0] + 200, cap[1] + cap[3] + 70, 1.0, pose="stand")
    bubble(p, [cap[0] + 360, cap[1] + 24, 520, 86], "Of course he did.", kind="speech",
           tail=[cap[0] + 240, cap[1] + cap[3] - 20])
    bubble(p, [cap[0] + 360, cap[1] + 124, 520, 70],
           "Then I owe him nothing.", kind="thought")


def p20_climax(b):
    p = sheet(b, "p20-climax", bg=CO["void"])
    p.rect([0, 0, W, H], fill=CO["void"])
    # a full-bleed diagonal slash divides the spread
    p.polygon([[0, 360], [W, 60], [W, 200], [0, 560]], fill=rgba(CO["white"], 0.9),
              stroke=CO["cyan"], stroke_style={"stroke_width": 3}, decorative=True)
    speed_radial(p, W / 2, 430, r0=60, r1=1200, count=60,
                 color=rgba(CO["cyan"], 0.10), lw=2.4, seed=151)
    # upper-left: kage. lower-right: tengu
    grid_floor(p, [0, 700, W, 1000], vx=W / 2, vy=720, color=CO["cyan_dk"], lines=24)
    draw_kage(p, 300, 900, 1.9, pose="slash")
    draw_tengu(p, 920, 1560, 1.9, pose="slash", flip=-1)
    slash(p, (120, 1180), (1080, 360), 26, color=CO["cyan"])
    sfx(p, 90, 120, "ZAN!!", style="sfx_cy", size=170, angle=-8)
    sfx(p, 560, 1380, "GAKIN", style="sfx_rd", size=150, angle=6)
    bubble(p, [110, 740, 470, 150], "Steel won't\nbeat me, ghost.", kind="shout",
           tail=[360, 1010])
    bubble(p, [W - 500, 1170, 420, 96], "Who said\nI'd use steel?", kind="speech",
           tail=[770, 1430])


def p21_hack(b):
    p = sheet(b, "p21-hack")
    a, d = strip(content_box(), [1, 1.1])
    # left: kage redirects the ICE
    c = panel(p, a, fill=CO["void2"])
    grid_floor(p, c, color=CO["cyan_dk"], lines=12)
    draw_kage(p, c[0] + c[2] / 2, c[1] + c[3] - 10, 1.2, pose="jack")
    # a stream of code arcing OUT of kage toward the right edge
    arc = Path().move_to(c[0] + c[2] / 2, c[1] + c[3] / 2).through(
        [[c[0] + c[2] * 0.7, c[1] + 120], [c[0] + c[2] - 10, c[1] + c[3] * 0.4]])
    p.path(arc, fill=None, stroke=CO["cyan"],
           stroke_style={"stroke_width": 4, "stroke_linecap": "round"})
    bubble(p, [c[0] + 20, c[1] + 20, 420, 110],
           "> reroute: TENGU.ICE\n> target = caster\n> commit.", kind="digital")
    sfx(p, c[0] + 40, c[1] + c[3] - 140, "TKTKTK", style="sfx_cy", size=64, angle=-4)
    # right: the drones turn on tengu
    c = panel(p, d, fill=CO["void"])
    code_rain(p, c, seed=161, color=CO["cyan"], cols=18)
    for (dx, dy) in [(0.3, 0.28), (0.6, 0.22), (0.78, 0.46), (0.46, 0.5)]:
        draw_drone(p, c[0] + c[2] * dx, c[1] + c[3] * dy, 1.1, eye=CO["cyan"])
    draw_tengu(p, c[0] + c[2] * 0.55, c[1] + c[3] - 10, 1.3, pose="stand", flip=-1)
    speed_radial(p, c[0] + c[2] * 0.55, c[1] + c[3] * 0.5, r0=40, r1=c[3] * 0.7,
                 count=34, color=rgba(CO["cyan"], 0.16), lw=2, seed=162)
    bubble(p, [c[0] + c[2] - 420, c[1] + 26, 390, 130],
           "My own ICE—\nimpossible!", kind="shout",
           tail=[c[0] + c[2] * 0.55, c[1] + 220])


def p22_fall(b):
    p = sheet(b, "p22-fall", bg=CO["void"])
    p.rect([0, 0, W, H], fill=CO["void"])
    # lots of negative space; one small panel low-center (a quiet beat)
    c = [W / 2 - 360, 560, 720, 560]
    inner = panel(p, c, fill=CO["void2"], lw=5)
    p.rect(inner, fill=radial_gradient([(rgba(CO["danger"], 0.18), 0), (CO["void2"], 1)],
                                       at="50% 40%"))
    # tengu dissolving into glitch bands
    draw_tengu(p, inner[0] + inner[2] / 2, inner[1] + inner[3] - 20, 1.2, pose="stand")
    for k in range(10):
        yy = inner[1] + 30 + k * (inner[3] - 60) / 10
        p.rect([inner[0] + 10, yy, inner[2] - 20, 6],
               fill=rgba(CO["danger"], round(0.5 - k * 0.04, 2)), decorative=True)
    bubble(p, [inner[0] + inner[2] - 320, inner[1] + 20, 300, 90],
           "...a corp dog never\nasks why.", kind="speech",
           tail=[inner[0] + inner[2] / 2, inner[1] + 160])
    sfx(p, W / 2 - 300, 360, "dissolve", style="sfx_cy", size=70, angle=-4)
    caption(p, [W / 2 - 360, 1180, 720, 90],
            "No triumph in it. Just one more ghost, unmade.", dark=True,
            accent=CO["danger"])


def p23_extract(b):
    p = sheet(b, "p23-extract")
    rows = tier(content_box(), [1, 1, 1])
    regs = [(CO["void"], CO["cyan"], "// THE NET — COLLAPSING"),
            ("#0c1430", CO["amber"], "// JACKING OUT"),
            (CO["ink"], CO["paper"], "// MEATSPACE")]
    for i, (rbox, (bg, ac, lab)) in enumerate(zip(rows, regs)):
        c = panel(p, rbox, fill=bg, lw=5)
        if i == 0:
            grid_floor(p, c, color=CO["cyan_dk"], lines=16)
            code_rain(p, c, seed=171, color=CO["cyan"], cols=20)
            for k in range(6):
                p.rect([c[0] + 30 + k * 40, c[1] + 20, 10, c[3] - 40],
                       fill=rgba(CO["magenta"], 0.4), decorative=True)
            draw_kage(p, c[0] + c[2] / 2, c[1] + c[3] - 10, 1.0, pose="leap")
            draw_aya(p, c[0] + c[2] / 2 + 130, c[1] + c[3] / 2, 0.5)
        elif i == 1:
            speed_radial(p, c[0] + c[2] / 2, c[1] + c[3] / 2, r0=40, r1=c[3],
                         count=40, color=rgba(CO["amber"], 0.18), lw=2, seed=172)
            p.circle([c[0] + c[2] / 2, c[1] + c[3] / 2], 60,
                     fill=rgba(CO["white"], 0.85), decorative=True)
            sfx(p, c[0] + c[2] / 2 - 140, c[1] + c[3] / 2 - 70, "FLASH",
                style="sfx", size=92, shadow=CO["amber"])
        else:
            draw_kage(p, c[0] + 240, c[1] + c[3] + 30, 0.9, pose="jack")
            bubble(p, [c[0] + 440, c[1] + 30, 520, 110],
                   "We're out. You're a passenger in my deck now, AYA.",
                   kind="speech", tail=[c[0] + 320, c[1] + c[3] - 20])
        T(p, [c[0] + 18, c[1] + 14, 360, 18], lab,
               style="label_cy" if ac != CO["paper"] else "label")


def p24_dawn(b):
    p = sheet(b, "p24-dawn")
    box = panel(p, content_box(), fill=CO["void"], lw=6)
    p.rect(box, fill=linear_gradient(
        [("#1a2238", 0), ("#6a4b6e", 0.55), ("#e9a14a", 0.86), ("#ffd98a", 1)],
        angle=180))
    p.circle([box[0] + box[2] * 0.5, box[1] + box[3] * 0.34], 120,
             fill=rgba(CO["white"], 0.85), decorative=True)
    skyline(p, [box[0], box[1] + box[3] * 0.5, box[2], box[3] * 0.5],
            seed=4, build="#241a2e", win=CO["amber"], neon=False)
    # kage on the ledge, AYA as a small holo companion
    draw_kage(p, box[0] + box[2] * 0.32, box[1] + box[3] - 30, 1.2, pose="stand",
              visor=CO["amber"])
    p.circle([box[0] + box[2] * 0.32 + 150, box[1] + box[3] - 200], 36,
             fill=rgba(CO["cyan"], 0.5), stroke=CO["cyan"],
             stroke_style={"stroke_width": 2})
    draw_aya(p, box[0] + box[2] * 0.32 + 150, box[1] + box[3] - 200, 0.32)
    caption(p, [box[0] + 36, box[1] + 36, 520, 130],
            "The Broker is still out there. So is Kurogane.\nBut the sun came up, "
            "and the Key is free.", dark=True, accent=CO["amber"])
    bubble(p, [box[0] + box[2] - 470, box[1] + box[3] - 220, 430, 96],
           "So... what do ghosts do at dawn?", kind="ai",
           tail=[box[0] + box[2] * 0.36 + 150, box[1] + box[3] - 180])
    bubble(p, [box[0] + box[2] - 470, box[1] + box[3] - 110, 430, 70],
           "We disappear. Come on.", kind="speech")


def p25_end(b):
    p = sheet(b, "p25-end", bg=CO["void"], folio=False)
    p.rect([0, 0, W, H], fill=linear_gradient(
        [(CO["void"], 0), (CO["void2"], 1)], angle=180))
    code_rain(p, [60, 60, W - 120, H - 400], seed=181, color=CO["cyan_dk"], cols=24)
    # emblem
    cx, cy = W / 2, 470
    p.circle([cx, cy], 150, fill=rgba(CO["cyan"], 0.06), stroke=CO["cyan"],
             stroke_style={"stroke_width": 2})
    shuriken = _starburst(cx, cy, 120, 120, spikes=4, inner=0.42)
    p.polygon(shuriken, fill=CO["void2"], stroke=CO["cyan"],
              stroke_style={"stroke_width": 3})
    p.circle([cx, cy], 26, fill=CO["void"], stroke=CO["magenta"],
             stroke_style={"stroke_width": 3})
    T(p, [cx - 400, 720, 800, 60], "TO BE CONTINUED", style="subt")
    p.rect([cx - 130, 800, 260, 6], fill=CO["magenta"])
    T(p, [cx - 460, 980, 920, 200],
           "NULLSEC // ZERO\nstory 01 — “Ghost in the Kurogane Net”\n\n"
           "written, drawn & lettered by the FrameGraph SDK\n"
           "no image assets — every panel composed from geometry",
           style="credit")
    T(p, [cx - 460, 1300, 920, 120],
           "next:  story 02 — “The Broker's Debt”", style="label_cy")


# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="NULLSEC // Ghost in the Kurogane Net",
                        profile="book", lang="en")
    for name, value in CO.items():
        b.define_color(name, value)
    for name, style in STYLES.items():
        b.define_text_style(name, **style)

    for page in (p01_cover, p02_world, p03_den, p04_job, p05_gear, p06_infiltration,
                 p07_wall, p08_ice, p09_clash, p10_descent, p11_rival, p12_standoff,
                 p13_cyberduel, p14_vault, p15_aya, p16_choice, p17_alarm, p18_escape,
                 p19_betrayal, p20_climax, p21_hack, p22_fall, p23_extract, p24_dawn,
                 p25_end):
        page(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} pages — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warnings)}")
    for i in (errors + warnings)[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "ninja-hacker-manga.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
