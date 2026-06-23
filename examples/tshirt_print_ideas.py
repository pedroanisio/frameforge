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


def fine_path(layer, d: str, width=1.45, color=None, dash=None):
    layer.path(
        d,
        fill="none",
        **stroke(width, color=color or rgba(INK, 0.78), cap="round", join="round", dash=dash),
    )


def brush_path(layer, d: str, width: float, color: str):
    layer.path(d, fill="none", **stroke(width, color=color, cap="round", join="round"))


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
    for d, w in [
        ("M 268 112 C 324 58 448 46 568 88 C 646 116 704 210 718 304", 2.0),
        ("M 306 84 C 368 108 414 154 430 230 C 436 258 426 286 404 318", 1.45),
        ("M 424 76 C 472 108 506 162 520 234 C 528 276 520 310 500 352", 1.35),
        ("M 548 102 C 608 132 654 190 674 260 C 690 314 684 382 660 444", 1.55),
        ("M 624 172 C 658 220 682 284 682 342 C 682 404 654 462 606 506", 1.2),
        ("M 478 382 C 520 356 562 352 610 378", 1.25),
        ("M 536 424 C 584 440 636 432 680 404", 1.2),
        ("M 456 512 C 506 526 554 530 598 512", 1.35),
    ]:
        fine_path(page, d, w)
    for d in [
        "M 242 136 C 284 112 326 118 360 154",
        "M 232 256 C 270 244 326 250 374 286",
        "M 238 378 C 282 374 340 392 402 444",
        "M 272 328 C 310 332 348 320 384 300",
        "M 286 470 C 328 478 370 466 410 440",
        "M 250 528 C 286 538 322 552 352 590",
    ]:
        fine_path(page, d, 1.25, rgba(INK, 0.58))
    for d, w, color in [
        ("M 272 122 C 240 198 236 292 250 378", 20, rgba("#FFF1A8", 0.34)),
        ("M 640 162 C 700 248 704 390 624 510", 24, rgba("#08030A", 0.32)),
        ("M 492 112 C 556 132 620 194 654 278", 10, rgba("#FF746C", 0.28)),
        ("M 512 380 C 560 388 612 376 656 342", 12, rgba("#13060B", 0.22)),
        ("M 288 512 C 330 550 378 560 432 526", 8, rgba("#FFE166", 0.28)),
    ]:
        brush_path(page, d, w, color)
    page.ellipse([574, 320], 94, 118, fill="none", **stroke(1.4, color=rgba(INK, 0.58)))
    page.ellipse([574, 320], 62, 74, fill="none", **stroke(1.2, color=rgba("#FFE1D1", 0.55)))
    page.ellipse([574, 320], 33, 39, fill="none", **stroke(1.4, color=rgba(INK, 0.72)))
    fine_path(page, "M 550 276 C 572 292 592 294 614 282", 1.25, rgba("#FFE7C8", 0.72))
    fine_path(page, "M 548 350 C 570 366 598 366 620 348", 1.2, rgba(INK, 0.48))
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
    for d, w in [
        ("M 356 526 C 416 548 488 604 546 686", 2.0),
        ("M 426 538 C 498 570 572 650 632 770", 1.4),
        ("M 566 492 C 604 548 624 616 626 694", 1.35),
        ("M 292 618 C 326 646 376 662 456 676", 1.35),
        ("M 96 696 C 152 660 214 650 272 686", 1.5),
        ("M 92 748 C 150 718 212 734 260 792", 1.25),
        ("M 604 682 C 642 732 660 826 646 930", 1.4),
        ("M 666 706 C 706 778 724 868 718 970", 1.2),
    ]:
        fine_path(page, d, w)
    for d, w, color in [
        ("M 128 690 C 210 644 300 670 382 724", 16, rgba("#FFB7A5", 0.24)),
        ("M 306 674 C 410 694 546 750 654 850", 14, rgba("#FF7768", 0.22)),
        ("M 500 748 C 566 778 630 844 660 930", 18, rgba("#07040A", 0.3)),
        ("M 180 884 C 276 970 444 1036 628 1070", 10, rgba("#1A0308", 0.24)),
        ("M 116 1016 C 142 1000 172 992 210 996", 8, rgba("#FF6A5A", 0.22)),
    ]:
        brush_path(page, d, w, color)

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
    for d, w in [
        ("M 170 644 L 214 740 L 170 808 L 104 766 L 132 684 Z", 1.6),
        ("M 196 864 C 278 928 396 968 520 984", 1.4),
        ("M 258 736 C 326 750 426 774 560 806", 1.25),
        ("M 296 708 C 358 714 438 742 514 786", 1.15),
        ("M 188 930 C 252 1020 388 1080 622 1088", 1.35),
        ("M 504 862 C 558 874 610 892 656 920", 1.2),
        ("M 526 980 C 574 992 618 1014 648 1048", 1.15),
        ("M 84 1012 C 116 1000 148 996 178 1002", 1.1),
        ("M 108 1078 C 130 1068 154 1060 178 1058", 1.1),
    ]:
        fine_path(page, d, w, rgba(INK, 0.72))
    for d in [
        "M 150 742 C 182 720 214 722 246 758",
        "M 340 760 C 400 774 462 792 522 818",
        "M 378 928 C 430 944 482 956 538 964",
        "M 584 744 C 628 792 646 842 640 900",
    ]:
        fine_path(page, d, 1.0, rgba("#FFB0A0", 0.52))
    for d in [
        "M 228 742 C 322 742 430 776 548 834",
        "M 232 950 C 336 1000 476 1030 620 1034",
        "M 456 924 C 526 944 586 970 638 1010",
        "M 70 846 C 106 812 156 780 222 760",
        "M 606 696 C 650 760 676 842 680 932",
    ]:
        fine_path(page, d, 0.9, rgba("#FFFFFF", 0.2))
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
