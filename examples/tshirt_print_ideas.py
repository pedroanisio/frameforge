#!/usr/bin/env python3
"""Vector recreation of the supplied T-shirt print idea using FrameGraph SDK.

Run from the repository root::

    uv run python examples/tshirt_print_ideas.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, Path, linear_gradient, radial_gradient, rgba, stroke  # noqa: E402

W, H = 736, 1308
INK = "#05050A"
INK2 = "#15131A"
RED = "#ED102A"
RED_DK = "#9B0617"
RED_LT = "#FF5B51"
GOLD = "#F7C63A"
GOLD_DK = "#8F5A08"
GOLD_LT = "#FFF0A5"
BLUE = "#8CEAFF"
STEEL = "#7C8C92"


def sw(width: float, color: str = INK, **extra):
    return stroke(width, color=color, join="round", cap="round", **extra)


def lg(start, end, stops):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = round(__import__("math").degrees(__import__("math").atan2(dy, dx)), 1)
    return linear_gradient([(color, pos) for pos, color in stops], angle=angle)


def rg(center, _radius, stops):
    return radial_gradient([(color, pos) for pos, color in stops], at=center, shape="circle")


def poly(layer, pts, fill, border=INK, width=3.0, **extra):
    layer.polygon(pts, fill=fill, stroke=border, stroke_style={"stroke_width": width, "stroke_linejoin": "round"}, **extra)


def lens(layer, points):
    poly(layer, points, fill=lg([255, 254], [362, 238], [(0, "#021B2E"), (0.35, BLUE), (1, "#FFFFFF")]), width=4)
    layer.polyline(points + [points[0]], closed=False, fill="none", **sw(1.4, "#D9FBFF"))


def rivet(layer, x, y, r=4):
    layer.ellipse([x, y], r, r, fill=INK)
    layer.ellipse([x - r * 0.28, y - r * 0.35], r * 0.22, r * 0.22, fill="#77818D")


def panel_line(layer, pts, width=2.2):
    layer.polyline(pts, fill="none", **sw(width, rgba(INK, 0.8)))


def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="T-shirt print ideas - armored hero vector", profile="diagram", lang="en")
    doc.define_text_style("caption", font_family=["DejaVu Sans", "Arial", "sans-serif"], font_size=18, color="#202020")
    page = doc.page(
        "tshirt_print_ideas",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
        reading_order=["caption"],
    ).layer("main")

    page.rect([0, 0, W, H], fill="#FFFFFF")
    page.ellipse([456, 166], 150, 70, fill=rgba("#F6F0DC", 0.35), decorative=True)
    page.ellipse([428, 328], 230, 290, fill=rgba("#F2D965", 0.08), decorative=True)

    red_gloss = lg([252, 74], [694, 614], [(0, RED_LT), (0.35, RED), (0.72, RED_DK), (1, "#22030A")])
    red_panel = lg([120, 600], [660, 1160], [(0, RED_LT), (0.45, RED), (1, RED_DK)])
    gold_face = lg([232, 130], [374, 518], [(0, GOLD_LT), (0.45, GOLD), (1, GOLD_DK)])
    black_cut = lg([470, 250], [630, 720], [(0, "#0B0911"), (1, "#010106")])

    # Neck and under-suit.
    poly(page, [[360, 520], [520, 470], [604, 720], [488, 780], [326, 690]], fill=lg([360, 520], [552, 768], [(0, RED), (1, "#2A0208")]), width=3.5)
    poly(page, [[520, 516], [640, 590], [662, 798], [530, 734]], fill=INK2, border=INK, width=3)
    panel_line(page, [[506, 572], [606, 642], [624, 744]], 2.2)
    panel_line(page, [[386, 590], [462, 742]], 2.1)

    # Helmet shell.
    poly(page, [[245, 92], [382, 56], [520, 84], [666, 176], [720, 324], [690, 486], [594, 538], [492, 510], [424, 556], [298, 516], [244, 396], [224, 260]], fill=red_gloss, width=4.2)
    poly(page, [[446, 88], [544, 96], [650, 164], [714, 298], [684, 378], [618, 330], [594, 224], [520, 150]], fill=lg([446, 88], [700, 360], [(0, RED), (0.55, RED_DK), (1, "#170006")]), width=3.2)
    poly(page, [[594, 224], [686, 360], [674, 474], [592, 528], [544, 438], [554, 306]], fill=black_cut, width=3)
    poly(page, [[246, 96], [298, 80], [386, 154], [330, 304], [238, 374], [218, 254]], fill=gold_face, width=4)
    poly(page, [[388, 154], [520, 150], [594, 224], [554, 306], [424, 252]], fill=lg([386, 154], [566, 314], [(0, GOLD_DK), (0.55, GOLD), (1, "#5C3306")]), width=3.4)
    poly(page, [[236, 374], [330, 304], [420, 350], [402, 442], [292, 470]], fill=lg([230, 354], [420, 470], [(0, GOLD), (0.58, GOLD_DK), (1, "#1D1205")]), width=3.4)
    poly(page, [[292, 470], [402, 442], [456, 492], [350, 560], [248, 522]], fill=lg([260, 472], [456, 556], [(0, GOLD_LT), (0.45, GOLD), (1, GOLD_DK)]), width=3)
    poly(page, [[250, 522], [350, 560], [446, 500], [492, 542], [352, 634], [240, 586]], fill=lg([240, 516], [492, 634], [(0, RED_LT), (0.5, RED), (1, RED_DK)]), width=4)
    poly(page, [[240, 586], [352, 634], [416, 610], [360, 672], [252, 650]], fill=INK, width=3)

    # Helmet eye, ear ring, seams and highlights.
    lens(page, [[278, 324], [362, 286], [388, 304], [346, 340], [274, 352]])
    page.ellipse([574, 320], 78, 102, fill=lg([510, 220], [640, 430], [(0, RED_LT), (0.5, RED_DK), (1, INK)]), stroke=INK, stroke_style={"stroke_width": 4})
    page.ellipse([574, 320], 48, 58, fill=lg([532, 260], [612, 378], [(0, "#FF625D"), (0.6, RED), (1, RED_DK)]), stroke=INK, stroke_style={"stroke_width": 3})
    page.ellipse([574, 320], 24, 28, fill=INK)
    page.ellipse([590, 316], 10, 16, fill=RED_DK)
    panel_line(page, [[382, 56], [430, 116], [446, 188], [424, 252]], 2.4)
    panel_line(page, [[520, 150], [604, 142], [690, 212]], 2.1)
    panel_line(page, [[554, 306], [528, 434], [544, 438]], 2.2)
    panel_line(page, [[600, 458], [696, 446]], 2.2)
    page.ellipse([326, 206], 22, 62, fill=rgba("#FFFFFF", 0.55), decorative=True)
    page.ellipse([505, 70], 36, 10, fill=rgba("#FFF7D0", 0.72), decorative=True)
    for x, y in [(462, 146), (676, 174), (706, 236), (458, 568), (622, 554)]:
        rivet(page, x, y, 4)

    # Shoulders and torso silhouette.
    poly(page, [[106, 700], [260, 596], [436, 640], [610, 706], [704, 828], [736, 1060], [736, H], [84, H], [0, 1160], [30, 870]], fill=INK, border=INK, width=2)
    poly(page, [[78, 686], [218, 628], [304, 706], [214, 940], [82, 1000], [28, 846]], fill=red_panel, width=4)
    poly(page, [[282, 640], [606, 716], [690, 896], [622, 1088], [258, 1022], [178, 854]], fill=red_panel, width=4)
    poly(page, [[596, 682], [690, 688], [736, 778], [736, 1040], [666, 980], [614, 832]], fill=lg([596, 680], [736, 1010], [(0, RED_LT), (0.45, RED), (1, RED_DK)]), width=4)
    poly(page, [[304, 642], [438, 672], [512, 718], [472, 770], [302, 726]], fill=lg([310, 650], [512, 770], [(0, "#DFEEF1"), (0.48, STEEL), (1, "#1A2228")]), width=3)
    poly(page, [[478, 752], [626, 792], [654, 902], [544, 880]], fill=INK2, width=3)
    poly(page, [[514, 910], [656, 944], [640, 1040], [470, 1010]], fill=lg([514, 910], [656, 1040], [(0, RED), (1, RED_DK)]), width=3)

    # Chest reactor.
    page.ellipse([204, 962], 66, 82, fill=INK, stroke=INK, stroke_style={"stroke_width": 3})
    page.ellipse([204, 962], 52, 66, fill=rg([204, 962], 70, [(0, "#FFFFFF"), (0.72, BLUE), (1, "#0B446B")]), stroke=INK, stroke_style={"stroke_width": 3})
    page.ellipse([204, 962], 38, 54, fill="#F7FEFF")
    page.ellipse([204, 962], 82, 100, fill="none", stroke=rgba(BLUE, 0.35), stroke_style={"stroke_width": 7})

    # Torso armor facets, seams, highlights, and print-like graphic contrast.
    poly(page, [[132, 686], [214, 652], [246, 724], [170, 780], [104, 746]], fill=lg([104, 650], [246, 780], [(0, RED_LT), (1, RED_DK)]), width=3)
    poly(page, [[86, 1022], [164, 1000], [176, 1198], [72, 1260]], fill=lg([86, 1000], [176, 1260], [(0, RED), (1, "#47030B")]), width=3)
    poly(page, [[256, 734], [560, 806], [502, 1004], [238, 942], [186, 858]], fill=lg([246, 728], [560, 1004], [(0, RED_LT), (0.52, RED), (1, RED_DK)]), width=2.6)
    page.ellipse([254, 794], 32, 48, fill=rgba("#FFF0B8", 0.8), decorative=True)
    page.ellipse([430, 816], 38, 52, fill=rgba("#FFF0B8", 0.85), decorative=True)
    page.ellipse([650, 720], 14, 30, fill=rgba("#FFF0B8", 0.78), decorative=True)
    page.ellipse([674, 698], 12, 24, fill=rgba("#FFF0B8", 0.78), decorative=True)
    page.ellipse([586, 632], 44, 18, fill=rgba("#FFF0B8", 0.75), decorative=True)
    for pts in [
        [[78, 686], [186, 858], [214, 940]],
        [[238, 942], [502, 1004], [622, 1088]],
        [[304, 706], [286, 858], [258, 1022]],
        [[560, 806], [626, 792], [654, 902]],
        [[596, 682], [614, 832], [666, 980]],
    ]:
        panel_line(page, pts, 2.3)
    for x, y in [(172, 844), (230, 1026), (260, 1008), (506, 1024), (598, 816), (622, 904), (566, 1108), (690, 1062)]:
        rivet(page, x, y, 5)

    # Lower red blocks crop at the shirt/poster edge.
    poly(page, [[168, 1190], [328, 1216], [360, H], [150, H]], fill=lg([168, 1190], [360, H], [(0, RED), (1, "#3A020A")]), width=3)
    poly(page, [[438, 1070], [664, 1116], [736, 1224], [736, H], [518, H]], fill=lg([438, 1070], [736, H], [(0, RED), (0.52, RED_DK), (1, INK)]), width=3)
    panel_line(page, [[482, 1124], [704, 1170]], 2.2)

    # Tiny label kept in reading order but visually unobtrusive.
    page.text([24, H - 34, 360, 20], "vector SDK recreation", id="caption", style="caption", opacity=0.0)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "examples", "fixtures", "tshirt-print-ideas.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [issue for issue in report.issues if issue.severity == "error"]
    print(f"ok={report.ok} errors={len(errors)} -> {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
