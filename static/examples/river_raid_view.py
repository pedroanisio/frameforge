#!/usr/bin/env python3
"""RIVER RAID — a vector homage to the 1982 Activision vertical shooter.

A single game-view composition, built with FrameForge primitives only: a player
jet flying up a winding blue river between green banks, a bridge level-marker, a
fleet of enemies (tanker, helicopters, enemy jet, fuel depot), and the black
Atari HUD — pixel-digit score, remaining lives, and a fuel gauge — all inside a
CRT cabinet with scanlines and a vignette.

No raster assets: the river/banks are meander polygons, the craft are
run-length pixel sprites, the score is a hand-rolled 3x5 bitmap font.

This is an original vector tribute; it is not affiliated with or endorsed by
Activision, and reproduces no game code or art assets.

Named layers (z-order): cabinet · playfield · bridge · enemies · player ·
hud · crt · marquee.

Run from the repository root::

    uv run python static/examples/river_raid_view.py
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

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    linear_gradient,
    radial_gradient,
    render_page_svgs,
    render_pages_with_stats,
    rgba,
    serialize,
    validate_static_rules,
)
from frameforge.sdk.paint import effects, shadow  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas / cabinet / screen geometry
# --------------------------------------------------------------------------- #
W, H = 880, 1080
CAB = [24, 24, 832, 1032]                 # console face
SX, SY, SW, SH = 64, 86, 752, 844         # CRT screen
PLAY_H = 726                              # playfield height (river)
HUD_Y = SY + PLAY_H                       # 812
HUD_H = SH - PLAY_H                       # 118
MID = SX + SW / 2                         # river mid-x = 440
PX = 4                                    # sprite pixel cell

FONT = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]

# Atari-ish River Raid palette (approximate homage, not sampled)
C = {
    "space":   "#0C0D11",
    "cab_hi":  "#2C303B",
    "cab_lo":  "#14161D",
    "bezel":   "#05060A",
    "land":    "#3AA23A",
    "land_d":  "#2C8330",
    "land_l":  "#54B94A",
    "bush":    "#2A7A2C",
    "water":   "#2F4ACB",
    "water_d": "#22369E",
    "water_l": "#5E77E6",
    "foam":    "#AFC0FF",
    "sand":    "#D8C489",
    "jet":     "#D4D9E2",
    "jet_d":   "#8A90A0",
    "canopy":  "#6FA8FF",
    "red":     "#E0463A",
    "red_d":   "#AE3128",
    "yellow":  "#EAB92A",
    "grey":    "#AEB3BE",
    "grey_d":  "#5A5E6A",
    "flame":   "#FF9A2E",
    "flame_h": "#FFE05A",
    "hud_bg":  "#04040A",
    "score":   "#F4C430",
    "green":   "#4BD24F",
    "amber":   "#F2A93B",
}


def txt(size, *, color, weight=700, align="left", ls=0.0, lh=1.1):
    return dict(font_family=FONT, font_size=size, font_weight=weight, color=color,
                align=align, letter_spacing=ls, line_height=lh)


# --------------------------------------------------------------------------- #
# Pixel helpers (RLE sprite + bitmap digits + scanlines)
# --------------------------------------------------------------------------- #
def sprite(L, ox, oy, art, pal, *, cell=PX, flip=False):
    """Stamp a run-length pixel sprite. ``pal`` maps glyph -> colour."""
    for r, rowstr in enumerate(art):
        if flip:
            rowstr = rowstr[::-1]
        c, n = 0, len(rowstr)
        while c < n:
            col = pal.get(rowstr[c])
            if col is None:
                c += 1
                continue
            run = 1
            while c + run < n and rowstr[c + run] == rowstr[c]:
                run += 1
            L.rect([ox + c * cell, oy + r * cell, run * cell, cell], fill=col, decorative=True)
            c += run


def place(L, cx, cy, art, pal, *, cell=PX, flip=False):
    w = max(len(r) for r in art) * cell
    h = len(art) * cell
    sprite(L, cx - w / 2, cy - h / 2, art, pal, cell=cell, flip=flip)


DIG = {
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", "..#", "..#", "..#"],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
}


def stamp_number(L, s, x, y, cell, color):
    for ch in s:
        g = DIG.get(ch)
        if g:
            for r, row in enumerate(g):
                for c, px in enumerate(row):
                    if px == "#":
                        L.rect([x + c * cell, y + r * cell, cell, cell], fill=color,
                               decorative=True)
        x += 4 * cell        # 3 wide + 1 gap
    return x


def scanlines(L, box, *, op=0.14, cell=6):
    x, y, w, h = box
    yy = y
    while yy < y + h:
        L.rect([x, yy, w, 2], fill=rgba("#000000", op), decorative=True)
        yy += cell


# --------------------------------------------------------------------------- #
# River meander
# --------------------------------------------------------------------------- #
def cx_of(y):
    t = y - SY
    return MID + 74 * math.sin(t * 0.0135 + 0.4) + 22 * math.sin(t * 0.031 + 1.1)


def hw_of(y):
    t = y - SY
    return 150 + 62 * math.sin(t * 0.017 + 2.0)      # half-width 88..212


def river(L):
    # land base
    L.rect([SX, SY, SW, PLAY_H], fill=linear_gradient(
        [(C["land_l"], 0.0), (C["land"], 0.5), (C["land_d"], 1.0)], angle=90))
    # scattered bush texture on the banks
    for i in range(46):
        y = SY + 14 + (i * 15.7) % (PLAY_H - 28)
        side = -1 if i % 2 else 1
        bx = cx_of(y) + side * (hw_of(y) + 22 + (i * 13) % 120)
        if SX + 10 < bx < SX + SW - 10:
            r = 5 + (i % 3) * 2
            L.ellipse([bx, y], r, r * 0.8, fill=C["bush"], decorative=True)

    ys = list(range(SY, SY + PLAY_H + 1, 6))
    left = [(cx_of(y) - hw_of(y), y) for y in ys]
    right = [(cx_of(y) + hw_of(y), y) for y in ys]
    # water body
    L.polygon(left + right[::-1],
              fill=linear_gradient([(C["water_l"], 0.0), (C["water"], 0.5),
                                    (C["water_d"], 1.0)], angle=90), decorative=True)

    def path_of(pts):
        d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "
        d += " ".join(f"L {x:.1f} {y:.1f}" for x, y in pts[1:])
        return d
    # bank shorelines: sand rim + dark water edge
    for pts in (left, right):
        L.path(path_of(pts), fill="none", stroke=C["sand"],
               stroke_style={"stroke_width": 4}, decorative=True)
        L.path(path_of(pts), fill="none", stroke=rgba("#0B1A66", 0.55),
               stroke_style={"stroke_width": 2}, decorative=True)
    # centre reflection glints
    for i, y in enumerate(range(SY + 20, SY + PLAY_H, 46)):
        gx = cx_of(y) + 14 * math.sin(i * 1.7)
        L.rect([gx - 10, y, 20, 3], fill=rgba(C["foam"], 0.5), decorative=True)
        L.rect([gx + 24, y + 10, 12, 2], fill=rgba(C["foam"], 0.32), decorative=True)


def island(L, cy, w=60, h=92):
    cx = cx_of(cy)
    L.ellipse([cx, cy], w / 2 + 4, h / 2 + 4, fill=C["sand"], decorative=True)
    L.ellipse([cx, cy], w / 2, h / 2, fill=C["land"], decorative=True)
    L.ellipse([cx - 6, cy - h * 0.18], w / 2 - 8, h / 2 - 10, fill=C["land_l"], decorative=True)
    for k in range(3):
        L.ellipse([cx - 10 + k * 12, cy + 6 + (k % 2) * 10], 5, 4, fill=C["bush"], decorative=True)


# --------------------------------------------------------------------------- #
# Bridge (level marker)
# --------------------------------------------------------------------------- #
def bridge(L, y):
    l, r = cx_of(y) - hw_of(y), cx_of(y) + hw_of(y)
    # abutments onto the banks
    L.rect([l - 20, y - 30, 22, 60], fill=C["grey_d"], decorative=True)
    L.rect([r - 2, y - 30, 22, 60], fill=C["grey_d"], decorative=True)
    # deck
    L.rect([l - 4, y - 20, (r - l) + 8, 40], fill=C["grey"])
    L.rect([l - 4, y - 20, (r - l) + 8, 6], fill="#D7DBE3", decorative=True)
    L.rect([l - 4, y + 14, (r - l) + 8, 6], fill=C["grey_d"], decorative=True)
    # truss X-bracing + rivets
    step = 30
    x = l
    while x < r - step:
        L.line([x, y - 18], [x + step, y + 18], stroke=C["grey_d"],
               stroke_style={"stroke_width": 3}, decorative=True)
        L.line([x + step, y - 18], [x, y + 18], stroke=C["grey_d"],
               stroke_style={"stroke_width": 3}, decorative=True)
        x += step
    for rx in range(int(l), int(r), 16):
        L.ellipse([rx, y - 16], 1.6, 1.6, fill="#3B3E48", decorative=True)
        L.ellipse([rx, y + 16], 1.6, 1.6, fill="#3B3E48", decorative=True)
    L.rect([l - 4, y - 2, (r - l) + 8, 4], fill=C["yellow"], decorative=True)


# --------------------------------------------------------------------------- #
# Craft sprites
# --------------------------------------------------------------------------- #
PLAYER = [
    "......#......",
    "......#......",
    ".....###.....",
    ".....#C#.....",
    ".....#C#.....",
    "....#####....",
    "..#########..",
    ".###########.",
    "####.###.####",
    "....#####....",
    ".....###.....",
    ".....#.#.....",
    "....##.##....",
    "...dd...dd...",
]
PLAYER_PAL = {"#": C["jet"], "C": C["canopy"], "d": C["jet_d"]}

ENEMY_JET = [
    "...rr...rr...",
    "....#.#......",
    ".....#.#.....",
    ".....###.....",
    "....#####....",
    "####.###.####",
    ".###########.",
    "..#########..",
    "....#####....",
    ".....#C#.....",
    ".....#C#.....",
    ".....###.....",
    "......#......",
    "......#......",
]
ENEMY_JET_PAL = {"#": C["red"], "C": "#3A0E0A", "r": C["red_d"]}

HELI = [
    "....y.y....",
    "....yyy....",
    "...yyCyy...",
    "..yyyyyyy..",
    "...yyyyy...",
    "....yyy....",
    ".....y.....",
    ".....y.....",
    "...yy.yy...",
]
HELI_PAL = {"y": C["yellow"], "C": C["canopy"]}


def helicopter(L, cx, cy):
    # rotor motion blur first (behind body)
    L.ellipse([cx, cy - 14], 34, 5, fill=rgba("#D9DEE8", 0.5), decorative=True)
    L.ellipse([cx, cy - 14], 34, 2, fill=rgba("#FFFFFF", 0.7), decorative=True)
    place(L, cx, cy, HELI, HELI_PAL)


def tanker(L, cx, cy):
    hw = hw_of(cy)
    w = min(hw * 1.5, 172)
    h = 34
    x, y = cx - w / 2, cy - h / 2
    L.rect([x, y, w, h], fill="#E7EAF0", radius=h / 2)           # hull
    L.rect([x, y, w, h], fill="none", stroke=C["grey_d"],
           stroke_style={"stroke_width": 2}, radius=h / 2, decorative=True)
    L.rect([x + 8, cy - 4, w - 16, 8], fill=C["red"], decorative=True)   # deck stripe
    L.rect([cx - 22, cy - 12, 44, 24], fill=C["grey"], radius=4, decorative=True)  # bridge
    L.rect([cx - 22, cy - 12, 44, 6], fill="#D7DBE3", radius=3, decorative=True)
    for k in (-1, 1):                                            # bow/stern caps
        L.ellipse([cx + k * (w / 2 - 6), cy], 6, h / 2 - 2, fill=C["red_d"], decorative=True)


def fuel_depot(L, cx, cy):
    w, h = 62, 78
    x, y = cx - w / 2, cy - h / 2
    L.rect([x, y, w, h], fill=C["red"], radius=8,
           **effects(shadow=shadow(dy=3, blur=8, color="#000000", opacity=0.35)))
    L.rect([x, y, w, h], fill="none", stroke=C["red_d"], stroke_style={"stroke_width": 2},
           radius=8, decorative=True)
    # hazard chevrons top & bottom
    for yy in (y + 6, y + h - 12):
        for i in range(5):
            L.polygon([[x + 6 + i * 12, yy], [x + 12 + i * 12, yy],
                       [x + 6 + i * 12, yy + 6]], fill=C["yellow"], decorative=True)
    # tank ribs + big white FUEL
    for rx in (x + 14, x + w - 16):
        L.rect([rx, y + 16, 4, h - 32], fill=rgba("#000000", 0.18), decorative=True)
    L.text([x, cy - 12, w, 24], "FUEL",
           style=txt(15, color="#FFFFFF", weight=800, align="center", ls=1.0))


def player(L, cx, cy):
    L.ellipse([cx, cy + 6], 24, 10, fill=rgba("#000000", 0.28), decorative=True)  # shadow
    place(L, cx, cy, PLAYER, PLAYER_PAL)
    # twin exhaust flames
    for dx in (-8, 8):
        L.polygon([[cx + dx - 5, cy + 24], [cx + dx + 5, cy + 24], [cx + dx, cy + 44]],
                  fill=C["flame"], decorative=True)
        L.polygon([[cx + dx - 3, cy + 24], [cx + dx + 3, cy + 24], [cx + dx, cy + 36]],
                  fill=C["flame_h"], decorative=True)
    # tracer / bullet going up
    for i, yy in enumerate(range(int(cy) - 40, int(cy) - 190, -26)):
        L.rect([cx - 1.5, yy, 3, 12], fill=rgba("#FFFFFF", 0.9 - i * 0.12), decorative=True)


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="River Raid — vector homage", profile="diagram", lang="en")
    page = doc.page("river_raid", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")

    # -------- cabinet ------------------------------------------------------ #
    cab = page.layer("cabinet")
    cab.rect([0, 0, W, H], fill=linear_gradient([("#131419", 0.0), ("#0A0B0F", 1.0)], angle=90))
    cx0, cy0, cw, ch = CAB
    cab.rect(CAB, fill=linear_gradient([(C["cab_hi"], 0.0), (C["cab_lo"], 1.0)], angle=90),
             radius=28, stroke="#3A3F4C", stroke_style={"stroke_width": 1.5},
             **effects(shadow=shadow(dy=20, blur=50, color="#000000", opacity=0.55)))
    cab.rect([cx0 + 10, cy0 + 10, cw - 20, 3], fill=rgba("#FFFFFF", 0.06), radius=2, decorative=True)
    # recessed bezel around the screen
    cab.rect([SX - 16, SY - 16, SW + 32, SH + 32], fill=C["bezel"], radius=14,
             **effects(shadow=shadow(dy=-2, blur=6, color="#000000", opacity=0.6)))
    cab.rect([SX, SY, SW, SH], fill="#06121A")            # screen base

    # -------- playfield (river) ------------------------------------------- #
    pf = page.layer("playfield")
    river(pf)
    island(pf, SY + 92)
    island(pf, SY + 404, w=46, h=56)

    # -------- bridge ------------------------------------------------------- #
    bl = page.layer("bridge")
    Y_BRIDGE = SY + 176
    bridge(bl, Y_BRIDGE)

    # -------- enemies ------------------------------------------------------ #
    en = page.layer("enemies")
    place(en, cx_of(SY + 262), SY + 262, ENEMY_JET, ENEMY_JET_PAL)
    helicopter(en, cx_of(SY + 356), SY + 356)
    tanker(en, cx_of(SY + 452), SY + 452)
    fuel_depot(en, cx_of(SY + 566), SY + 566)
    helicopter(en, cx_of(SY + 636), SY + 636)

    # -------- player ------------------------------------------------------- #
    pl = page.layer("player")
    player(pl, cx_of(SY + 690), SY + 690)

    # -------- HUD ---------------------------------------------------------- #
    hud = page.layer("hud")
    hud.rect([SX, HUD_Y, SW, HUD_H], fill=C["hud_bg"])
    hud.rect([SX, HUD_Y, SW, 3], fill=rgba("#2B57C0", 0.6), decorative=True)
    # score
    hud.text([SX + 26, HUD_Y + 12, 120, 12], "SCORE", style=txt(11, color="#7C8AB8", ls=2.0))
    stamp_number(hud, "023650", SX + 26, HUD_Y + 28, 7, C["score"])
    # lives (mini jets)
    hud.text([SX + SW - 210, HUD_Y + 12, 120, 12], "JETS", style=txt(11, color="#7C8AB8", ls=2.0))
    for i in range(3):
        place(hud, SX + SW - 150 + i * 42, HUD_Y + 34, PLAYER, PLAYER_PAL, cell=2)
    # fuel gauge
    gx, gy, gw, gh = SX + 26, HUD_Y + 74, SW - 52, 24
    hud.text([gx, gy - 17, gw, 12], "FUEL",
             style=txt(12, color="#DFE4F2", weight=800, align="center", ls=3.0))
    hud.rect([gx, gy, gw, gh], fill="#0B0E18", radius=5, stroke="#3A4160",
             stroke_style={"stroke_width": 1.5})
    frac = 0.66
    # danger zone (empty end) then fill
    hud.rect([gx + 3, gy + 3, gw * 0.16, gh - 6], fill=rgba(C["red"], 0.35), radius=3,
             decorative=True)
    hud.rect([gx + 3, gy + 3, (gw - 6) * frac, gh - 6],
             fill=linear_gradient([(C["green"], 0.0), (C["amber"], 1.0)], angle=0),
             radius=3, decorative=True)
    for i in range(1, 10):                               # tick marks
        tx = gx + gw * i / 10
        hud.line([tx, gy + 2], [tx, gy + gh - 2], stroke=rgba("#000000", 0.35),
                 stroke_style={"stroke_width": 1}, decorative=True)
    # indicator + E/F ends
    ix = gx + 3 + (gw - 6) * frac
    hud.polygon([[ix - 6, gy - 3], [ix + 6, gy - 3], [ix, gy + 5]], fill="#FFFFFF", decorative=True)
    hud.text([gx - 2, gy + 4, 16, 16], "E", style=txt(13, color=C["red"], weight=800, align="center"))
    hud.text([gx + gw - 14, gy + 4, 16, 16], "F", style=txt(13, color=C["green"], weight=800, align="center"))

    # -------- CRT overlay -------------------------------------------------- #
    crt = page.layer("crt")
    scanlines(crt, [SX, SY, SW, SH], op=0.12, cell=6)
    crt.rect([SX, SY, SW, SH], fill=radial_gradient(
        [(rgba("#000000", 0.0), 0.55), (rgba("#000000", 0.10), 0.8), (rgba("#02040A", 0.6), 1.0)],
        at="50% 46%", shape="ellipse"), decorative=True)
    crt.polygon([[SX, SY], [SX + SW * 0.5, SY], [SX, SY + SH * 0.42]],
                fill=rgba("#FFFFFF", 0.05), decorative=True)   # glass glare
    crt.rect([SX, SY, SW, SH], fill="none", stroke=rgba("#000000", 0.5),
             stroke_style={"stroke_width": 3}, radius=2, decorative=True)

    # -------- marquee ------------------------------------------------------ #
    mq = page.layer("marquee")
    my = CAB[1] + CAB[3] - 96
    # speaker grille dots
    for i in range(9):
        mq.ellipse([CAB[0] + 40 + i * 14, my + 30], 3, 3, fill=rgba("#FFFFFF", 0.14), decorative=True)
        mq.ellipse([CAB[0] + CAB[2] - 40 - i * 14, my + 30], 3, 3, fill=rgba("#FFFFFF", 0.14),
                   decorative=True)
    # tiny jet mark before the title
    place(mq, MID - 176, my + 34, PLAYER, PLAYER_PAL, cell=2)
    mq.text([CAB[0], my + 14, CAB[2], 44], "RIVER  RAID",
            style=txt(40, color="#EAF0FF", weight=800, align="center", ls=7.0))
    mq.text([CAB[0], my + 58, CAB[2], 18],
            "vector homage · FrameForge SDK · not affiliated with Activision",
            style=txt(12, color="#8A93B0", weight=500, align="center", ls=1.0))

    return doc


def main() -> int:
    doc = build().build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warns)}")
    for i in errors[:30]:
        print(f"  [ERROR] [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:8]:
        print(f"  [warn] [{i.rule_id}] {i.path}: {i.message}")

    svgs, tstats = render_pages_with_stats(doc)
    leak = tstats.get("visible_overflow", 0) + tstats.get("uncontained", 0)
    print(f"text: total={tstats['total']} contained={tstats['contained']} "
          f"clipped={tstats['clipped']} visible_overflow={tstats['visible_overflow']}"
          + ("  <-- LEAK" if leak else "  (no visible leaks)"))

    out_svg = os.path.join(ROOT, "river-raid-view.svg")
    with open(out_svg, "w", encoding="utf-8") as fh:
        fh.write(svgs[0])
    print(f"Wrote {out_svg}")
    out_yaml = os.path.join(ROOT, "river-raid-view.fg.yaml")
    with open(out_yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out_yaml}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
