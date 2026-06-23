#!/usr/bin/env python3
"""KING KONG: HEART OF THUNDER -- a 30-page manga made with FrameGraph SDK.

This is a complete black-and-white one-shot built from vector geometry only:
panels, gutters, captions, speech balloons, speed lines, city silhouettes,
jungle foliage, ships, aircraft, and a recurring giant-ape figure. No bitmap
assets are used.

Run from the repository root:

    uv run python examples/king_kong_manga.py
"""
from __future__ import annotations

import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, column, linear_gradient, radial_gradient, rgba, row, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# The detailed hero ape: a faithful vector trace of the King Kong stencil,
# authored in examples/king_kong_gorilla.py and reused here as one even-odd path.
from king_kong_gorilla import KONG_SUBPATHS, W as KONG_W, H as KONG_H  # noqa: E402

W, H = 1200, 1700
CANVAS = {"size": [W, H], "units": "px"}
MARGIN = 54
GUTTER = 18

SANS = ["DejaVu Sans", "Arial", "sans-serif"]
SERIF = ["Bitstream Charter", "Georgia", "serif"]
MONO = ["DejaVu Sans Mono", "Fira Mono", "monospace"]

CO = {
    "ink": "#101014",
    "paper": "#f2efe6",
    "paper2": "#e5dfcf",
    "tone1": "#d2ccbd",
    "tone2": "#aaa292",
    "tone3": "#746d61",
    "shadow": "#343138",
    "night": "#090910",
    "storm": "#202833",
    "silver": "#c8ccd0",
    "sky": "#b7bec7",
    "blood": "#b92520",
    "gold": "#d9a441",
    "sea": "#17232c",
    "leaf": "#23321f",
    "mist": "#f7f3e9",
}

TEXT = {
    "title": dict(font_family=SANS, font_size=132, font_weight=900, color="paper", line_height=0.88),
    "title_dark": dict(font_family=SANS, font_size=96, font_weight=900, color="ink", line_height=0.9),
    "chapter": dict(font_family=MONO, font_size=18, font_weight=700, color="gold", letter_spacing=4),
    "narr_l": dict(font_family=SERIF, font_size=22, color="paper", line_height=1.35),
    "narr_d": dict(font_family=SERIF, font_size=22, color="ink", line_height=1.35),
    "speech": dict(font_family=SANS, font_size=23, font_weight=700, color="ink", line_height=1.12, align="center"),
    "small": dict(font_family=SANS, font_size=18, font_weight=700, color="ink", line_height=1.18, align="center"),
    "shout": dict(font_family=SANS, font_size=28, font_weight=900, color="ink", line_height=1.0, align="center"),
    "sfx": dict(font_family=SANS, font_size=112, font_weight=900, color="ink", letter_spacing=-3),
    "sfx_light": dict(font_family=SANS, font_size=112, font_weight=900, color="paper", letter_spacing=-3),
    "label": dict(font_family=MONO, font_size=14, font_weight=700, color="tone3", letter_spacing=2),
    "folio": dict(font_family=MONO, font_size=14, color="tone3"),
    "credits": dict(font_family=SERIF, font_size=24, color="paper", line_height=1.55, align="center"),
}

PAGE_NO = 0

SCENES = [
    ("01", "The map names no island", "A storm opens like a black mouth. The Venture follows a compass that should not work.", "CAPTAIN: Keep the lamps covered. The reef is listening.", "KRAK"),
    ("02", "Fog over the wall", "At dawn, the crew finds a stone wall taller than any church, older than any crown.", "ANN: Something behind it is breathing.", "HUUU"),
    ("03", "Drums under the rain", "The village drums do not warn the island. They warn the sea.", "ELDER: No crown can command Kong. Only grief can call him.", "DUM"),
    ("04", "The offering refused", "They dress Ann in gold and terror. She refuses to kneel.", "ANN: I am not a gift.", "SNAP"),
    ("05", "Kong descends", "The mountain moves. The jungle falls silent by instinct.", "SAILOR: That is not a beast. That is the island standing up.", "KRROOOM"),
    ("06", "Hand like a bridge", "Kong reaches through torchlight, not as a tyrant, but as a question.", "ANN: You understand fear, don't you?", "THUD"),
    ("07", "Ravine chase", "Men with rifles turn courage into noise. The ravine answers with teeth.", "CAPTAIN: Run for the vines!", "RAA"),
    ("08", "The old throne", "Kong carries Ann to a cliff where bones of older giants shine in moonlight.", "ANN: This was your kingdom.", "WHUF"),
    ("09", "Thunder lizard", "A predator from the swamp challenges the mountain king.", "ANN: Behind you!", "GRAA"),
    ("10", "Crown of scars", "Kong wins, but every victory on the island is another scar under the fur.", "ANN: I see you. Not the monster. You.", "HHRR"),
    ("11", "Chains in the hold", "Greed speaks softly. Steel speaks louder.", "SHOWMAN: New York will bow to the Eighth Wonder.", "CLANK"),
    ("12", "Sea without stars", "The ship drags a king across the world, and the waves refuse to look.", "ANN: I am sorry. I am so sorry.", "CREAK"),
    ("13", "White lights", "The theater lights burn brighter than lightning and colder than moonlight.", "SHOWMAN: Smile, ladies and gentlemen. History is chained tonight.", "FLASH"),
    ("14", "Curtain breaks", "Kong sees the crowd, the cameras, the tiny cage of civilization.", "KONG: RRRRRAAAAH!", "KRAK"),
    ("15", "City canyon", "Broadway becomes a ravine of glass. Sirens replace drums.", "POLICE: Flood the avenue! Keep him moving!", "WOOO"),
    ("16", "Ann runs toward him", "Everyone runs from Kong. Ann runs toward him, because she knows the shape of his panic.", "ANN: Kong! Look at me!", "ANN!"),
    ("17", "Iron birds", "The sky fills with machines that mistake height for courage.", "PILOT: Target is climbing. Repeat, target is climbing.", "DRRRM"),
    ("18", "The tower", "He climbs because the city has no mountain, only a needle aimed at heaven.", "ANN: Put me down. Please. They will shoot.", "GONG"),
    ("19", "Against the dawn", "For one breath, Kong and the sun are the same size.", "KONG: HHHHNNN.", "SILENCE"),
    ("20", "First wound", "The bullets find him. Ann's scream finds what bullets cannot.", "ANN: Stop! He is afraid!", "TAK"),
    ("21", "Swat the sky", "Kong strikes back at thunder made by men.", "PILOT: He hit Mason! Break left!", "WHAM"),
    ("22", "Grip slipping", "Stone, steel, fur, blood. The tower keeps no promises.", "ANN: Hold on!", "SKRR"),
    ("23", "A king falls", "The island king falls through the city that paid to see him fall.", "CROWD: ...", "BOOM"),
    ("24", "No beauty killed him", "Reporters invent a simple ending because the true one would indict them all.", "ANN: No. It was not beauty.", "CLICK"),
    ("25", "Return of the drums", "Far away, the island drums answer a death they never witnessed.", "ELDER: The crown returns to thunder.", "DUM"),
    ("26", "Seed in the stone", "In the crack of the old wall, a red flower opens where Kong once rested his hand.", "CHILD: Will another king come?", "..."),
    ("27", "Ann's testimony", "Ann tells the story without chains, stages, or ticket stubs.", "ANN: He was lonely. We made loneliness a spectacle.", "SCRITCH"),
    ("28", "The city remembers wrong", "Posters fade. Headlines yellow. The tower keeps a shadow no rain removes.", "NEWSBOY: Extra! Wonder slain!", "FLAP"),
]


def split_rows(box, weights):
    return column(box, gap=GUTTER, weights=weights)


def split_cols(box, weights):
    return row(box, gap=GUTTER, weights=weights)


def sheet(builder, page_id, *, bg="paper", folio=True):
    global PAGE_NO
    PAGE_NO += 1
    page = builder.page(page_id, canvas=CANVAS, coordinate_mode="absolute")
    page.layer("paper")
    page.rect([0, 0, W, H], fill=bg)
    page.layer("art")
    if folio:
        x = W - MARGIN - 52 if PAGE_NO % 2 == 0 else MARGIN
        text(page, [x, H - 34, 52, 18], f"{PAGE_NO:02d}", style="folio")
    return page


def content_box():
    return [MARGIN, MARGIN, W - MARGIN * 2, H - MARGIN * 2]


def text(page, box, value, **fields):
    with page.lettering():
        page.text([float(v) for v in box], value, **fields)


def panel(page, box, *, fill="paper", border="ink", width=5, pad=18):
    page.rect(box, fill=fill, stroke=border, stroke_style={"stroke_width": width})
    x, y, w, h = box
    return [x + pad, y + pad, w - pad * 2, h - pad * 2]


def caption(page, box, value, *, dark=True, accent="gold"):
    fill = CO["ink"] if dark else CO["paper"]
    stroke = CO["paper"] if dark else CO["ink"]
    page.rect(box, fill=fill, stroke=stroke, stroke_style={"stroke_width": 1.2})
    x, y, w, h = box
    page.rect([x, y, 7, h], fill=accent)
    text(page, [x + 20, y + 14, w - 34, h - 24], value, style="narr_l" if dark else "narr_d")


def star_points(cx, cy, rx, ry, spikes=12, inner=0.72):
    pts = []
    for i in range(spikes * 2):
        angle = math.pi * i / spikes - math.pi / 2
        radius = 1.0 if i % 2 == 0 else inner
        pts.append([cx + math.cos(angle) * rx * radius, cy + math.sin(angle) * ry * radius])
    return pts


def bubble(page, box, value, *, kind="speech", tail=None):
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    if tail is not None:
        tx, ty = tail
        dx, dy = tx - cx, ty - cy
        length = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / length * 14, dx / length * 14
        page.polygon([[cx + ox, cy + oy], [cx - ox, cy - oy], [tx, ty]], fill="paper", stroke="ink", stroke_style={"stroke_width": 3})
    if kind == "shout":
        page.polygon(star_points(cx, cy, w / 2, h / 2, spikes=13, inner=0.78), fill="paper", stroke="ink", stroke_style={"stroke_width": 3})
        style = "shout"
    else:
        page.ellipse([cx, cy], w / 2, h / 2, fill="paper", stroke="ink", stroke_style={"stroke_width": 3})
        style = "speech" if h > 74 else "small"
    text(page, [x + 18, y + 15, w - 36, h - 26], value, style=style)


def sfx(page, x, y, value, *, light=False, size=104):
    style = "sfx_light" if light else "sfx"
    shadow_style = "sfx" if light else "sfx_light"
    with page.bleed():
        text(page, [x + 6, y + 6, 760, 140], value, style=shadow_style)
        text(page, [x, y, 760, 140], value, style=style)


def speed_lines(page, box, *, focus=None, count=26, color="ink"):
    x, y, w, h = box
    fx, fy = focus or (x + w * 0.55, y + h * 0.5)
    with page.bleed():
        for i in range(count):
            side = i % 4
            t = (i + 0.5) / count
            if side == 0:
                start = [x, y + h * t]
            elif side == 1:
                start = [x + w, y + h * t]
            elif side == 2:
                start = [x + w * t, y]
            else:
                start = [x + w * t, y + h]
            page.line(start, [fx, fy], stroke=color, stroke_style={"stroke_width": 1.2 + (i % 5) * 0.7, "opacity": 0.26})


def tone_dots(page, box, *, step=34, color="tone2", opacity=0.28):
    x, y, w, h = box
    with page.bleed():
        rows = int(h // step) + 2
        cols = int(w // step) + 2
        for r in range(rows):
            for c in range(cols):
                if (r + c) % 2 == 0:
                    page.circle([x + c * step + (r % 2) * step * 0.45, y + r * step], 3.2, fill=rgba(CO[color], opacity), decorative=True)


def rain(page, box, *, count=42):
    x, y, w, h = box
    with page.bleed():
        for i in range(count):
            px = x + (i * 37) % max(w, 1)
            py = y + (i * 91) % max(h, 1)
            page.line([px, py], [px - 26, py + 82], stroke="paper", stroke_style={"stroke_width": 1.3, "opacity": 0.42})


def draw_city(page, box, *, night=True):
    x, y, w, h = box
    page.rect(box, fill=linear_gradient([("storm" if night else "sky", 0), ("paper2", 1)], angle=90))
    horizon = y + h * 0.58
    for i in range(13):
        bw = w * (0.055 + (i % 3) * 0.012)
        bh = h * (0.24 + (i % 5) * 0.055)
        bx = x + i * w / 12 - bw * 0.45
        by = horizon - bh
        page.rect([bx, by, bw, bh], fill="ink" if night else "shadow", stroke="ink", stroke_style={"stroke_width": 1})
        for r in range(3, int(bh // 28)):
            for c in range(1, max(2, int(bw // 24))):
                if (i + r + c) % 3 == 0:
                    page.rect([bx + c * 18, by + r * 22, 7, 11], fill="gold" if night else "paper")
    page.rect([x, horizon, w, h - (horizon - y)], fill="night" if night else "tone2")
    for k in range(7):
        yy = horizon + 28 + k * 38
        page.line([x, yy], [x + w, yy - 24], stroke="paper" if night else "tone3", stroke_style={"stroke_width": 1.0, "opacity": 0.38})


def draw_jungle(page, box):
    x, y, w, h = box
    page.rect(box, fill=linear_gradient([("paper2", 0), ("leaf", 1)], angle=90))
    for i in range(19):
        base_x = x + (i + 0.3) * w / 19
        trunk_h = h * (0.45 + (i % 5) * 0.055)
        page.rect([base_x, y + h - trunk_h, 9 + i % 4, trunk_h], fill="ink")
        crown_y = y + h - trunk_h
        for j in range(4):
            page.ellipse([base_x + (j - 1.5) * 25, crown_y + j * 16], 45, 18, fill="leaf", stroke="ink", stroke_style={"stroke_width": 1.2})
    tone_dots(page, box, step=42, color="paper", opacity=0.2)


def draw_sea(page, box):
    x, y, w, h = box
    page.rect(box, fill=linear_gradient([("storm", 0), ("sea", 1)], angle=90))
    rain(page, box, count=34)
    for i in range(10):
        yy = y + h * 0.58 + i * 28
        page.polyline([[x + 15, yy], [x + w * 0.25, yy - 14], [x + w * 0.52, yy + 7], [x + w - 20, yy - 18]], stroke="paper", stroke_style={"stroke_width": 2.0, "opacity": 0.28}, fill="none")


def draw_ship(page, box):
    x, y, w, h = box
    hull_y = y + h * 0.72
    page.polygon([[x + w * 0.16, hull_y], [x + w * 0.80, hull_y], [x + w * 0.70, hull_y + h * 0.13], [x + w * 0.24, hull_y + h * 0.13]], fill="ink")
    page.rect([x + w * 0.35, hull_y - h * 0.13, w * 0.22, h * 0.13], fill="paper", stroke="ink", stroke_style={"stroke_width": 3})
    page.rect([x + w * 0.58, hull_y - h * 0.25, w * 0.04, h * 0.24], fill="ink")
    page.line([x + w * 0.24, hull_y], [x + w * 0.68, y + h * 0.27], stroke="ink", stroke_style={"stroke_width": 3})
    page.line([x + w * 0.76, hull_y], [x + w * 0.68, y + h * 0.27], stroke="ink", stroke_style={"stroke_width": 3})


def draw_planes(page, box, *, count=3):
    x, y, w, h = box
    for i in range(count):
        px = x + w * (0.18 + 0.24 * i)
        py = y + h * (0.16 + 0.11 * (i % 2))
        scale = 1.0 - i * 0.12
        page.line([px - 58 * scale, py], [px + 70 * scale, py], stroke="ink", stroke_style={"stroke_width": 5 * scale})
        page.line([px - 10 * scale, py - 25 * scale], [px + 26 * scale, py + 25 * scale], stroke="ink", stroke_style={"stroke_width": 4 * scale})
        page.line([px + 32 * scale, py - 18 * scale], [px + 62 * scale, py + 18 * scale], stroke="ink", stroke_style={"stroke_width": 3 * scale})
        page.circle([px + 76 * scale, py], 8 * scale, fill="ink")
        page.line([px - 88 * scale, py - 18 * scale], [px - 170 * scale, py - 46 * scale], stroke="paper", stroke_style={"stroke_width": 2, "opacity": 0.55})


def draw_human(page, cx, cy, scale=1.0, *, dress=False):
    ink = "paper" if dress else "ink"
    page.circle([cx, cy - 52 * scale], 16 * scale, fill=ink, stroke="ink", stroke_style={"stroke_width": 2})
    page.line([cx, cy - 34 * scale], [cx, cy + 28 * scale], stroke=ink, stroke_style={"stroke_width": 8 * scale})
    page.line([cx, cy - 6 * scale], [cx - 34 * scale, cy + 18 * scale], stroke=ink, stroke_style={"stroke_width": 5 * scale})
    page.line([cx, cy - 6 * scale], [cx + 34 * scale, cy + 12 * scale], stroke=ink, stroke_style={"stroke_width": 5 * scale})
    if dress:
        page.polygon([[cx - 18 * scale, cy - 4 * scale], [cx + 18 * scale, cy - 4 * scale], [cx + 44 * scale, cy + 70 * scale], [cx - 42 * scale, cy + 70 * scale]], fill="paper", stroke="ink", stroke_style={"stroke_width": 2})
    else:
        page.line([cx, cy + 28 * scale], [cx - 25 * scale, cy + 82 * scale], stroke=ink, stroke_style={"stroke_width": 6 * scale})
        page.line([cx, cy + 28 * scale], [cx + 28 * scale, cy + 82 * scale], stroke=ink, stroke_style={"stroke_width": 6 * scale})


def draw_kong(page, cx, base, scale=1.0, *, pose="stand", wounded=False):
    fur = "ink"
    cut = "paper"

    def p(points):
        return [[cx + x * scale, base + y * scale] for x, y in points]

    def slash(points, fill=cut):
        page.polygon(p(points), fill=fill)

    def ink_poly(points):
        page.polygon(p(points), fill=fur)

    if pose == "roar":
        left_arm = [(-90, -310), (-230, -460), (-280, -412), (-210, -235), (-154, -92), (-105, -126)]
        right_arm = [(90, -310), (235, -460), (286, -410), (218, -235), (152, -92), (106, -126)]
        hand_l, hand_r = (-250, -445), (256, -445)
    elif pose == "climb":
        left_arm = [(-78, -308), (-150, -540), (-202, -516), (-176, -338), (-126, -114), (-82, -138)]
        right_arm = [(78, -308), (158, -520), (210, -492), (176, -332), (122, -118), (82, -138)]
        hand_l, hand_r = (-154, -544), (164, -522)
    else:
        left_arm = [(-92, -302), (-190, -188), (-178, -30), (-118, -18), (-102, -128), (-62, -286)]
        right_arm = [(92, -302), (192, -188), (180, -30), (120, -18), (104, -128), (62, -286)]
        hand_l, hand_r = (-178, -22), (180, -22)

    ink_poly([(-98, -422), (-58, -494), (10, -536), (94, -512), (162, -424), (184, -300), (132, -350), (62, -386), (-38, -392)])
    ink_poly(left_arm)
    ink_poly(right_arm)
    page.ellipse([cx + hand_l[0] * scale, base + hand_l[1] * scale], 34 * scale, 27 * scale, fill=fur)
    page.ellipse([cx + hand_r[0] * scale, base + hand_r[1] * scale], 34 * scale, 27 * scale, fill=fur)
    if pose == "stand":
        for hx, hy in (hand_l, hand_r):
            for offset in (-18, -4, 10, 23):
                page.ellipse([cx + (hx + offset) * scale, base + (hy + 11) * scale], 9 * scale, 7 * scale, fill=cut)
            page.ellipse([cx + (hx - 30) * scale, base + (hy + 2) * scale], 11 * scale, 8 * scale, fill=cut)

    page.line([cx - 54 * scale, base - 94 * scale], [cx - 96 * scale, base + 42 * scale], stroke=fur, stroke_style={"stroke_width": 50 * scale})
    page.line([cx + 54 * scale, base - 94 * scale], [cx + 96 * scale, base + 42 * scale], stroke=fur, stroke_style={"stroke_width": 50 * scale})
    page.ellipse([cx - 100 * scale, base + 44 * scale], 46 * scale, 18 * scale, fill=fur)
    page.ellipse([cx + 100 * scale, base + 44 * scale], 46 * scale, 18 * scale, fill=fur)

    ink_poly([
        (-178, -326), (-132, -414), (-54, -456), (52, -450), (142, -406),
        (202, -316), (176, -214), (152, -108), (82, -38), (-76, -44),
        (-156, -112), (-184, -218),
    ])
    ink_poly([(-178, -310), (-228, -258), (-214, -174), (-158, -140), (-126, -242)])
    ink_poly([(178, -310), (228, -258), (214, -174), (158, -140), (126, -242)])
    page.ellipse([cx - 104 * scale, base - 302 * scale], 72 * scale, 62 * scale, fill=fur)
    page.ellipse([cx + 104 * scale, base - 302 * scale], 72 * scale, 62 * scale, fill=fur)
    page.ellipse([cx, base - 258 * scale], 126 * scale, 152 * scale, fill=fur)
    ink_poly([(-118, -86), (-42, -36), (44, -34), (122, -86), (84, 24), (-82, 24)])

    ink_poly([
        (-74, -444), (-54, -512), (-18, -574), (34, -596), (92, -576),
        (130, -522), (136, -448), (96, -394), (22, -382), (-44, -398),
    ])
    for spike in [
        [(-32, -565), (-16, -628), (4, -572)],
        [(0, -586), (30, -646), (32, -578)],
        [(38, -584), (82, -632), (66, -566)],
        [(78, -552), (138, -584), (100, -526)],
    ]:
        ink_poly(spike)

    page.ellipse([cx + 90 * scale, base - 500 * scale], 18 * scale, 30 * scale, fill=fur, stroke=cut, stroke_style={"stroke_width": 5 * scale})
    page.ellipse([cx + 94 * scale, base - 500 * scale], 8 * scale, 17 * scale, fill=fur, stroke=cut, stroke_style={"stroke_width": 3 * scale})

    slash([(-62, -498), (-28, -542), (18, -548), (2, -506), (-38, -482)])
    slash([(8, -526), (70, -520), (106, -488), (38, -494)])
    slash([(-62, -468), (-22, -492), (8, -474), (-36, -446)])
    slash([(34, -486), (90, -492), (106, -462), (56, -448)])
    slash([(-48, -454), (-6, -474), (38, -458), (60, -426), (16, -408), (-38, -422)])
    slash([(-40, -456), (-8, -468), (26, -456), (40, -438), (14, -426), (-30, -432)])
    page.ellipse([cx - 8 * scale, base - 446 * scale], 22 * scale, 13 * scale, fill=fur)
    page.ellipse([cx - 32 * scale, base - 474 * scale], 8 * scale, 5 * scale, fill=fur)
    page.ellipse([cx + 30 * scale, base - 472 * scale], 8 * scale, 5 * scale, fill=fur)
    page.ellipse([cx - 18 * scale, base - 444 * scale], 4.5 * scale, 3 * scale, fill=cut)
    page.ellipse([cx + 4 * scale, base - 444 * scale], 4.5 * scale, 3 * scale, fill=cut)
    slash([(-32, -424), (36, -426), (24, -416), (-22, -414)])
    page.rect([cx - 27 * scale, base - 412 * scale, 60 * scale, 6 * scale], fill=cut)
    slash([(-36, -398), (32, -400), (14, -384), (-24, -386)])

    slash([(-150, -332), (-94, -372), (-34, -360), (-72, -312), (-138, -284)])
    slash([(-98, -304), (-42, -340), (8, -328), (-32, -286), (-84, -266)])
    slash([(22, -326), (100, -364), (152, -338), (118, -288), (52, -274)])
    slash([(92, -294), (160, -326), (178, -288), (130, -242), (78, -254)])
    slash([(-162, -354), (-124, -392), (-84, -384), (-112, -348)])
    slash([(116, -384), (172, -368), (186, -336), (130, -346)])
    slash([(-62, -244), (-16, -270), (42, -256), (8, -224), (-46, -214)])
    slash([(34, -220), (94, -248), (132, -220), (86, -188)])

    for side in (-1, 1):
        slash([(side * 116, -272), (side * 168, -302), (side * 198, -284), (side * 150, -244)], fill=cut)
        slash([(side * 138, -220), (side * 184, -246), (side * 198, -222), (side * 154, -188)], fill=cut)
        slash([(side * 140, -164), (side * 178, -188), (side * 186, -160), (side * 152, -124)], fill=cut)
        slash([(side * 172, -106), (side * 216, -136), (side * 204, -92), (side * 170, -64)], fill=cut)
        slash([(side * 90, -74), (side * 126, -116), (side * 118, -38), (side * 90, -18)], fill=cut)

    for x, lean in [(-58, 26), (-36, 18), (-12, 12), (14, 8), (40, 4), (66, -2)]:
        slash([(x, -126), (x + lean, -170), (x + 8, -16), (x - 12, -56)])
    slash([(-96, -28), (-62, -72), (-48, 32), (-78, 42)])
    slash([(96, -28), (62, -72), (48, 32), (78, 42)])
    page.ellipse([cx, base - 214 * scale], 54 * scale, 86 * scale, fill=rgba(CO["paper"], 0.07))
    if wounded:
        page.line([cx + 36 * scale, base - 282 * scale], [cx + 76 * scale, base - 224 * scale], stroke="blood", stroke_style={"stroke_width": 8 * scale})


def _kong_path_d(box, *, fit=0.94, flip=False):
    """Transform the traced ape (KONG_W x KONG_H) to fit ``box``, centered.

    Returns one SVG ``d`` string (all contour loops); the figure plus its
    white negative-space cuts render as a single even-odd path.
    """
    x, y, w, h = box
    scale = min(w / KONG_W, h / KONG_H) * fit
    fig_w, fig_h = KONG_W * scale, KONG_H * scale
    ox, oy = x + (w - fig_w) / 2.0, y + (h - fig_h) / 2.0

    def place(px, py):
        sx = (KONG_W - px) if flip else px
        return ox + sx * scale, oy + py * scale

    parts = []
    for subpath in KONG_SUBPATHS:
        nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", subpath)]
        pts = [place(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        if len(pts) < 3:
            continue
        seg = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
        seg += [f"L{qx:.1f} {qy:.1f}" for qx, qy in pts[1:]]
        seg.append("Z")
        parts.append("".join(seg))
    return " ".join(parts)


def kong_portrait(page, box, *, ink="ink", glow=None, flip=False, fit=0.94):
    """Place the detailed traced ape as a single even-odd hero figure.

    ``ink`` fills the figure (use ``"paper"`` for a luminous ape on a dark page,
    ``"ink"`` on a light page); the white cuts show whatever sits behind, so an
    optional ``glow`` paints a soft backing disc first.
    """
    x, y, w, h = box
    if glow is not None:
        page.ellipse([x + w / 2.0, y + h * 0.52], w * 0.46, h * 0.5, fill=glow)
    d = _kong_path_d(box, fit=fit, flip=flip)
    page.add({
        "type": "path",
        "id": f"kong-hero-{int(x)}-{int(y)}",
        "d": d,
        "fill": ink,
        "style": {"fill_rule": "evenodd"},
    })


def draw_tower(page, box):
    x, y, w, h = box
    cx = x + w * 0.55
    top = y + h * 0.06
    bottom = y + h * 1.04
    page.polygon([[cx - w * 0.06, bottom], [cx + w * 0.06, bottom], [cx + w * 0.025, top], [cx - w * 0.025, top]], fill="shadow", stroke="ink", stroke_style={"stroke_width": 3})
    for i in range(14):
        yy = bottom - i * h * 0.07
        page.line([cx - w * 0.07, yy], [cx + w * 0.07, yy], stroke="paper", stroke_style={"stroke_width": 1.2, "opacity": 0.38})
    page.line([cx, top], [cx, top - 82], stroke="ink", stroke_style={"stroke_width": 5})


def art_for_scene(page, box, idx):
    if idx in {1, 12}:
        draw_sea(page, box)
        draw_ship(page, box)
    elif idx in {2, 3, 4, 5, 6, 7, 8, 9, 10, 25, 26, 29}:
        draw_jungle(page, box)
        if idx >= 5 and idx not in {7, 25, 26}:
            draw_kong(page, box[0] + box[2] * 0.58, box[1] + box[3] * 0.92, box[3] / 650, pose="roar" if idx in {5, 9, 29} else "stand")
        if idx in {4, 6, 8, 9, 10}:
            draw_human(page, box[0] + box[2] * 0.27, box[1] + box[3] * 0.78, box[3] / 640, dress=True)
    elif idx in {11, 13, 14}:
        page.rect(box, fill="night")
        tone_dots(page, box, step=30, color="paper", opacity=0.18)
        draw_kong(page, box[0] + box[2] * 0.53, box[1] + box[3] * 0.92, box[3] / 600, pose="roar" if idx == 14 else "stand")
        for n in range(6):
            draw_human(page, box[0] + box[2] * (0.12 + n * 0.13), box[1] + box[3] * 0.91, box[3] / 1050)
    elif idx in {15, 16, 24, 27, 28}:
        draw_city(page, box, night=True)
        if idx in {15, 16}:
            draw_kong(page, box[0] + box[2] * 0.62, box[1] + box[3] * 0.94, box[3] / 690, pose="stand")
        if idx in {16, 24, 27}:
            draw_human(page, box[0] + box[2] * 0.24, box[1] + box[3] * 0.86, box[3] / 700, dress=True)
    elif idx in {17, 18, 19, 20, 21, 22, 23}:
        draw_city(page, box, night=False)
        draw_tower(page, box)
        draw_kong(page, box[0] + box[2] * 0.53, box[1] + box[3] * 0.72, box[3] / 760, pose="climb", wounded=idx >= 20)
        if idx in {17, 20, 21, 22}:
            draw_planes(page, box, count=4 if idx >= 20 else 3)
        if idx in {18, 19, 20, 22}:
            draw_human(page, box[0] + box[2] * 0.48, box[1] + box[3] * 0.39, box[3] / 980, dress=True)
    else:
        draw_city(page, box, night=True)


def page_layout(box, idx):
    if idx % 4 == 0:
        top, bottom = split_rows(box, [1.12, 0.88])
        left, right = split_cols(bottom, [0.95, 1.05])
        return [top, left, right]
    if idx % 4 == 1:
        left, right = split_cols(box, [0.88, 1.12])
        r1, r2 = split_rows(right, [1, 1])
        return [left, r1, r2]
    if idx % 4 == 2:
        top, mid, bot = split_rows(box, [0.72, 1.12, 0.74])
        return [top, mid, bot]
    top_l, top_r = split_cols(split_rows(box, [0.95, 1.05])[0], [1, 1])
    bottom = split_rows(box, [0.95, 1.05])[1]
    return [top_l, top_r, bottom]


def story_page(builder, idx, scene):
    number, heading, narration, dialogue, fx = scene
    page = sheet(builder, f"p{idx:02d}-{slug(heading)}", bg="paper")
    boxes = page_layout(content_box(), idx)
    first = panel(page, boxes[0], fill="paper2" if idx % 2 else "night")
    art_for_scene(page, first, idx)
    speed_lines(page, first, focus=[first[0] + first[2] * 0.58, first[1] + first[3] * 0.48], count=18 if idx in {5, 9, 14, 21, 23, 29} else 8, color="paper" if idx % 2 else "ink")
    caption(page, [first[0] + 18, first[1] + 18, min(540, first[2] - 36), 112], f"{number} / {heading.upper()}\n{narration}", dark=idx % 2 == 0, accent="gold")
    if fx and fx != "...":
        sfx(page, first[0] + first[2] * 0.08, first[1] + first[3] * 0.62, fx, light=idx % 2 == 0, size=86 if len(fx) > 5 else 112)

    second = panel(page, boxes[1], fill="paper")
    art_for_scene(page, second, idx)
    bubble(page, [second[0] + second[2] * 0.08, second[1] + 22, second[2] * 0.62, 96], dialogue, kind="shout" if "KONG:" in dialogue or "!" in dialogue else "speech", tail=[second[0] + second[2] * 0.53, second[1] + second[3] * 0.55])

    third = panel(page, boxes[2], fill="paper2")
    art_for_scene(page, third, idx)
    if idx in {7, 14, 17, 20, 21, 22, 23}:
        speed_lines(page, third, count=30, color="ink")
    closing = closing_line(idx)
    caption(page, [third[0] + third[2] - min(490, third[2] * 0.78) - 18, third[1] + third[3] - 112, min(490, third[2] * 0.78), 92], closing, dark=False, accent="blood" if idx in {20, 22, 23, 24} else "gold")


def closing_line(idx):
    lines = {
        1: "The island waits beyond the lightning.",
        2: "Some doors are built to keep the world out. Some keep a wound in.",
        3: "The drums say his name before any human dares.",
        4: "A chain is only a question asked by cowards.",
        5: "Kong arrives like weather with eyes.",
        6: "His hand could crush her. It does not.",
        7: "The ravine keeps the loudest men.",
        8: "On the throne, even a king can look abandoned.",
        9: "The jungle crowns whoever survives its hunger.",
        10: "Ann touches the scar. Kong lets the world go quiet.",
        11: "The cage is built before the lie is spoken.",
        12: "An ocean is still too small for a stolen king.",
        13: "Applause sounds too much like rain on chains.",
        14: "The curtain falls. The cage follows.",
        15: "The city has walls too. They are made of windows.",
        16: "Her voice is the only landmark he knows.",
        17: "The machines circle like hungry punctuation.",
        18: "He climbs toward the nearest memory of a mountain.",
        19: "Dawn gives him one mercy: a horizon.",
        20: "Civilization proves it can wound what it cannot understand.",
        21: "He fights the sky because the ground betrayed him.",
        22: "Even kings have fingers. Even towers have edges.",
        23: "The city finally grows silent enough to hear itself.",
        24: "A headline is a cage made of words.",
        25: "Across the sea, thunder lowers its head.",
        26: "The island does not replace him. It remembers him.",
        27: "A true witness refuses the easy myth.",
        28: "The posters sell a monster. The shadow keeps a king.",
        29: "His roar returns as rain.",
    }
    return lines[idx]


def cover(builder):
    page = sheet(builder, "p00-cover", bg="night", folio=False)
    page.rect([0, 0, W, H], fill=radial_gradient([("storm", 0), ("night", 0.78), ("ink", 1)], at=[0.48, 0.32], shape="circle"))
    moon = [W * 0.68, H * 0.25]
    page.circle(moon, 210, fill="paper", stroke="ink", stroke_style={"stroke_width": 4})
    with page.bleed():
        draw_city(page, [0, H * 0.56, W, H * 0.44], night=True)
        draw_tower(page, [W * 0.34, H * 0.24, W * 0.42, H * 0.70])
    kong_portrait(page, [W * 0.17, H * 0.26, W * 0.66, H * 0.56], ink="paper", fit=0.97)
    draw_planes(page, [90, 120, 930, 330], count=4)
    sfx(page, 86, 740, "ROOOAR", light=True, size=132)
    text(page, [76, 74, 940, 220], "KING KONG", style="title")
    text(page, [82, 292, 620, 70], "HEART OF THUNDER", style="chapter")
    caption(page, [72, H - 220, 520, 116], "A 30-page vector manga one-shot\ncomposed with the FrameGraph SDK", dark=True, accent="gold")


def end_page(builder):
    page = sheet(builder, "p30-end", bg="night", folio=False)
    page.rect([0, 0, W, H], fill=linear_gradient([("night", 0), ("storm", 0.62), ("ink", 1)], angle=90))
    draw_jungle(page, [80, 220, W - 160, 600])
    draw_city(page, [80, 900, W - 160, 420], night=True)
    page.rect([80, 820, W - 160, 28], fill="paper")
    page.circle([W / 2, 536], 135, fill=rgba(CO["paper"], 0.16), stroke="paper", stroke_style={"stroke_width": 2})
    kong_portrait(page, [W * 0.28, 286, W * 0.44, 760], ink="paper", fit=0.95)
    text(page, [190, 120, 820, 96], "THE END", style="title")
    text(page, [180, 1360, 840, 178], "King Kong: Heart of Thunder\nwritten, drawn, lettered, and rendered by geometry\n30 pages - no bitmap assets", style="credits")
    text(page, [220, 1548, 760, 44], "FRAMEGRAPH SDK MANGA SAMPLE", style="chapter")


def slug(value):
    keep = []
    for ch in value.lower():
        if ch.isalnum():
            keep.append(ch)
        elif keep and keep[-1] != "-":
            keep.append("-")
    return "".join(keep).strip("-")


def build() -> DocumentBuilder:
    global PAGE_NO
    PAGE_NO = 0
    builder = DocumentBuilder(title="King Kong: Heart of Thunder", profile="book", lang="en")
    for name, value in CO.items():
        builder.define_color(name, value)
    for name, style in TEXT.items():
        builder.define_text_style(name, **style)
    cover(builder)
    for idx, scene in enumerate(SCENES, start=1):
        story_page(builder, idx, scene)
    end_page(builder)
    return builder


def main() -> int:
    builder = build()
    doc = builder.build()
    report = validate_static_rules(doc)
    errors = [issue for issue in report.issues if issue.severity == "error"]
    warnings = [issue for issue in report.issues if issue.severity != "error"]
    print(f"Built {len(doc.pages)} pages - ok={report.ok} errors={len(errors)} warnings={len(warnings)}")
    for issue in (errors + warnings)[:40]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    out = os.path.join(ROOT, "fixtures", "king-kong-manga.fg.yaml")
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
