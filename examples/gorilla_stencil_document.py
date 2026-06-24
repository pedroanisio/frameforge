#!/usr/bin/env python3
"""Gorilla stencil document composed with the FrameGraph SDK.

The artwork is a geometric black-and-white composition inspired by the supplied
reference image: a left-facing gorilla bust with high-contrast silhouette mass,
negative-space facial planes, chest cuts, shoulder fur, and forearm texture.

Run from the repository root::

    uv run python examples/gorilla_stencil_document.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, Path, rgba, stroke  # noqa: E402

W, H = 894, 1000
INK = "#000000"
PAPER = "#FFFFFF"


def sw(width: float, color: str = INK, *, cap: str = "round", join: str = "round") -> dict:
    return stroke(width, color=color, cap=cap, join=join)


def poly(page, points, fill=INK, border=None, width=0.0, **extra):
    kwargs = {"fill": fill, **extra}
    if border:
        kwargs.update(stroke=border, stroke_style={"stroke_width": width, "stroke_linejoin": "round"})
    page.polygon(points, **kwargs)


def blade(page, points, *, fill=PAPER):
    poly(page, points, fill=fill, border=None, decorative=True)


def whisker(page, points, width=5.0):
    page.polyline(points, fill="none", **sw(width, PAPER), decorative=True)


def ink_path(page, d: str, *, fill=INK, width=0.0, opacity=1.0):
    kwargs = {"fill": fill, "opacity": opacity}
    if width:
        kwargs.update(**sw(width, INK))
    page.path(d, **kwargs)


def paper_path(page, d: str, *, width=0.0, opacity=1.0):
    kwargs = {"fill": PAPER, "opacity": opacity, "decorative": True}
    if width:
        kwargs.update(**sw(width, PAPER))
    page.path(d, **kwargs)


def fur_saw(page, ridge, *, fill=INK):
    poly(page, ridge, fill=fill, border=None, decorative=True)


def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="Gorilla Stencil Study", profile="diagram", lang="en")
    doc.define_text_style(
        "caption",
        font_family=["DejaVu Sans", "Arial", "sans-serif"],
        font_size=14,
        color=rgba(INK, 0.0),
    )
    page = doc.page(
        "gorilla_stencil",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
        reading_order=["caption"],
    ).layer("stencil")

    page.rect([0, 0, W, H], fill=PAPER)

    # Main silhouette: back, shoulders, torso, and heavy arms.
    ink_path(
        page,
        "M 326 0 C 395 -7 454 7 502 35 C 548 63 579 109 597 166 "
        "C 618 238 662 276 725 296 C 775 311 815 343 840 391 "
        "C 870 449 876 552 858 664 C 848 726 850 799 875 894 "
        "C 884 926 886 957 872 1000 L 704 1000 C 700 915 690 831 672 748 "
        "C 652 660 637 597 643 541 C 646 502 637 470 616 446 "
        "C 586 412 535 400 466 407 C 399 413 351 440 325 488 "
        "C 297 539 298 614 322 710 C 346 803 373 891 379 1000 L 154 1000 "
        "C 159 895 148 813 122 755 C 87 680 58 607 56 528 "
        "C 54 433 88 345 157 295 C 198 265 236 243 270 220 "
        "C 287 158 300 64 326 0 Z",
    )

    # Head and face mass.
    ink_path(
        page,
        "M 262 71 C 306 26 383 9 449 34 C 503 55 536 99 541 151 "
        "C 550 238 506 314 438 344 C 362 378 269 359 228 299 "
        "C 193 247 207 151 262 71 Z",
    )
    ink_path(
        page,
        "M 213 151 C 173 192 167 254 197 304 C 226 352 282 379 342 376 "
        "C 300 397 250 389 216 360 C 165 316 146 248 164 194 C 175 164 191 151 213 151 Z",
    )

    # Crown spikes and hairline like cut paper teeth.
    fur_saw(
        page,
        [
            [271, 69], [282, 34], [292, 58], [311, 18], [316, 49], [341, 10],
            [341, 44], [370, 2], [365, 41], [401, 0], [390, 42], [429, 9],
            [409, 49], [459, 29], [426, 61], [486, 52], [433, 80], [357, 79],
        ],
    )

    # Ear and side head cut-outs.
    page.ellipse([444, 150], 22, 36, fill=PAPER, decorative=True)
    page.ellipse([451, 152], 12, 26, fill=INK, decorative=True)
    page.ellipse([456, 154], 8, 17, fill=PAPER, decorative=True)
    blade(page, [[308, 95], [324, 62], [332, 121], [350, 87], [355, 148], [326, 134]])
    blade(page, [[241, 118], [260, 88], [259, 145], [285, 104], [276, 166]])

    # Brow, eyes, nose, muzzle and scowl built from white negative space.
    paper_path(
        page,
        "M 220 166 C 258 137 305 126 351 129 C 326 154 303 171 275 181 "
        "C 249 189 231 185 220 166 Z",
    )
    paper_path(
        page,
        "M 311 134 C 362 132 407 146 436 174 C 407 183 372 184 333 175 "
        "C 317 162 309 149 311 134 Z",
    )
    blade(page, [[240, 202], [296, 195], [285, 218], [247, 221]])
    blade(page, [[327, 198], [402, 191], [383, 220], [335, 223]])
    poly(page, [[249, 206], [291, 200], [279, 213], [250, 215]], fill=INK)
    poly(page, [[343, 204], [386, 198], [375, 212], [345, 215]], fill=INK)
    paper_path(
        page,
        "M 224 239 C 251 249 286 250 311 238 C 329 226 353 225 378 238 "
        "C 367 264 342 276 309 273 C 277 271 244 261 224 239 Z",
    )
    poly(page, [[265, 239], [288, 227], [318, 232], [337, 246], [320, 259], [286, 257]], fill=INK)
    blade(page, [[281, 244], [299, 239], [297, 253], [280, 254]])
    blade(page, [[311, 240], [331, 247], [315, 255]])
    paper_path(
        page,
        "M 237 287 C 276 311 336 312 381 286 C 371 323 338 350 293 351 "
        "C 260 351 240 327 237 287 Z",
    )
    poly(page, [[256, 296], [299, 307], [365, 291], [343, 322], [287, 325]], fill=INK)
    paper_path(page, "M 283 328 C 314 341 343 331 365 314 C 350 354 304 369 271 347 Z")
    page.line([233, 305], [213, 338], **sw(7, PAPER), decorative=True)
    page.line([386, 304], [413, 334], **sw(7, PAPER), decorative=True)
    blade(page, [[203, 142], [237, 103], [227, 160], [263, 125], [247, 182]], fill=INK)
    blade(page, [[284, 111], [319, 82], [311, 145], [354, 108], [341, 171]], fill=INK)
    blade(page, [[217, 224], [263, 232], [242, 244], [207, 236]])
    blade(page, [[357, 226], [413, 215], [389, 237], [344, 240]])
    poly(page, [[273, 247], [292, 239], [286, 259], [269, 263]], fill=INK, decorative=True)
    poly(page, [[315, 240], [339, 249], [321, 263], [307, 258]], fill=INK, decorative=True)
    whisker(page, [[249, 285], [288, 297], [341, 293], [383, 275]], 3.2)
    whisker(page, [[258, 319], [296, 335], [343, 330], [376, 306]], 3.4)
    blade(page, [[214, 365], [258, 374], [307, 368], [264, 388]], fill=INK)
    blade(page, [[331, 367], [385, 355], [418, 330], [388, 378]], fill=INK)
    blade(page, [[247, 82], [263, 42], [268, 105], [290, 67], [286, 132]], fill=INK)
    blade(page, [[350, 66], [381, 30], [366, 111], [409, 75], [389, 149]], fill=INK)
    blade(page, [[199, 172], [223, 146], [218, 209], [247, 181], [239, 235]])
    blade(page, [[388, 168], [431, 151], [401, 207], [447, 190], [403, 239]])
    blade(page, [[229, 255], [267, 272], [239, 280], [211, 266]])
    blade(page, [[344, 270], [384, 249], [371, 276], [331, 288]])
    poly(page, [[243, 224], [263, 222], [256, 236], [237, 236]], fill=INK, decorative=True)
    poly(page, [[372, 219], [395, 212], [383, 230], [365, 233]], fill=INK, decorative=True)
    whisker(page, [[209, 292], [250, 311], [309, 316], [374, 297]], 2.8)
    whisker(page, [[232, 352], [278, 378], [341, 374], [399, 344]], 3.1)

    # Shoulder fur collar: white torn tufts cut through the black shoulders.
    blade(page, [[84, 349], [122, 302], [112, 363], [166, 291], [148, 381], [215, 288], [188, 400], [270, 293], [239, 416], [327, 332], [278, 455], [195, 428], [122, 410]])
    blade(page, [[505, 366], [548, 297], [539, 377], [602, 312], [583, 400], [669, 322], [627, 429], [724, 351], [672, 464], [781, 418], [658, 492], [560, 455]])
    blade(page, [[95, 389], [145, 342], [128, 418], [192, 357], [166, 451], [234, 383], [198, 487], [137, 454]])
    blade(page, [[539, 424], [598, 370], [574, 449], [646, 385], [613, 484], [697, 414], [653, 523], [579, 491]])
    blade(page, [[694, 382], [753, 353], [725, 405], [793, 386], [746, 442], [817, 424], [743, 474]])
    poly(page, [[156, 392], [205, 354], [190, 413], [146, 455]], fill=INK, decorative=True)
    poly(page, [[615, 394], [675, 350], [650, 429], [598, 465]], fill=INK, decorative=True)

    # Chest plates and abdomen negative-space cuts.
    paper_path(
        page,
        "M 176 417 C 218 360 298 344 366 383 C 324 413 294 454 279 512 "
        "C 234 514 191 482 176 417 Z",
    )
    paper_path(
        page,
        "M 341 393 C 424 344 546 341 627 397 C 553 410 486 439 424 489 "
        "C 395 461 368 429 341 393 Z",
    )
    paper_path(
        page,
        "M 255 558 C 301 529 366 538 415 576 C 371 571 337 583 311 615 "
        "C 291 588 273 570 255 558 Z",
    )
    ink_path(
        page,
        "M 334 506 C 405 458 528 455 598 514 C 641 551 656 625 647 718 "
        "C 637 811 621 902 611 1000 L 333 1000 C 337 894 322 800 299 720 "
        "C 277 645 286 558 334 506 Z",
    )
    blade(page, [[236, 620], [269, 563], [271, 701], [291, 585], [304, 721], [332, 605], [335, 758], [260, 744]])
    blade(page, [[361, 592], [407, 570], [382, 650], [443, 595], [395, 712], [470, 620], [416, 769], [367, 731]])
    blade(page, [[329, 438], [393, 410], [366, 451], [446, 429], [405, 476], [493, 449], [451, 506], [365, 489]])
    blade(page, [[518, 430], [589, 399], [558, 452], [633, 423], [604, 486], [673, 459], [640, 531], [562, 499]])
    blade(page, [[190, 521], [256, 536], [218, 555], [168, 548]])
    blade(page, [[294, 530], [380, 495], [356, 523], [306, 552]])
    whisker(page, [[425, 497], [504, 462], [588, 471], [653, 518]], 6)
    blade(page, [[322, 575], [384, 535], [360, 604], [430, 553], [392, 642], [461, 588], [416, 693]])
    blade(page, [[480, 565], [547, 534], [512, 612], [585, 568], [536, 662], [609, 612], [554, 724]])
    whisker(page, [[302, 706], [356, 673], [423, 660], [497, 675]], 4.2)
    whisker(page, [[397, 735], [459, 704], [526, 701], [592, 732]], 4.2)
    blade(page, [[309, 832], [347, 760], [337, 914], [377, 794], [361, 961], [411, 831], [398, 1000], [304, 1000]])
    blade(page, [[428, 824], [486, 739], [444, 917], [523, 779], [468, 975], [548, 833], [512, 1000], [418, 1000]])

    # Arms and forearm fur highlights.
    ink_path(
        page,
        "M 74 555 C 43 626 33 728 58 820 C 75 881 103 944 100 1000 L 0 1000 "
        "L 0 637 C 12 594 36 565 74 555 Z",
    )
    ink_path(
        page,
        "M 760 482 C 828 515 878 604 887 708 C 894 797 880 894 847 1000 "
        "L 725 1000 C 720 914 729 843 747 777 C 773 682 775 586 760 482 Z",
    )
    blade(page, [[23, 600], [56, 577], [45, 644], [86, 596], [68, 696], [105, 642], [81, 753], [121, 693], [91, 828], [52, 790]])
    blade(page, [[720, 540], [756, 493], [751, 579], [801, 527], [780, 631], [835, 584], [801, 700], [851, 660], [809, 804], [754, 754]])
    blade(page, [[39, 849], [78, 804], [76, 890], [118, 841], [104, 944], [151, 902], [126, 1000], [37, 1000]])
    blade(page, [[711, 827], [760, 763], [745, 889], [797, 805], [777, 949], [835, 868], [810, 1000], [702, 1000]])
    blade(page, [[34, 708], [64, 690], [57, 744], [82, 716], [75, 779], [105, 750], [95, 814], [61, 795]])
    blade(page, [[86, 910], [119, 884], [113, 947], [151, 913], [139, 982], [182, 940], [165, 1000], [96, 1000]])
    blade(page, [[744, 614], [789, 574], [768, 677], [817, 628], [792, 742], [843, 688], [820, 808], [766, 747]])
    blade(page, [[760, 902], [802, 846], [785, 958], [833, 897], [811, 1000], [747, 1000]])
    for pts in [
        [[86, 843], [124, 826], [141, 858], [112, 884]],
        [[126, 870], [171, 852], [189, 883], [152, 911]],
        [[152, 920], [198, 897], [213, 934], [175, 962]],
        [[65, 930], [104, 905], [118, 945], [82, 974]],
        [[115, 956], [158, 934], [176, 973], [139, 1000]],
    ]:
        blade(page, pts)
    for pts in [
        [[57, 875], [83, 843], [80, 914]],
        [[105, 908], [136, 872], [129, 954]],
        [[155, 940], [188, 900], [178, 985]],
        [[72, 964], [105, 920], [101, 1000]],
        [[132, 987], [166, 940], [158, 1000]],
    ]:
        poly(page, pts, fill=INK, decorative=True)
    for pts in [
        [[742, 808], [780, 768], [772, 864], [813, 819], [793, 922]],
        [[798, 836], [840, 782], [824, 900], [865, 846], [846, 958]],
        [[713, 934], [748, 888], [741, 1000], [699, 1000]],
    ]:
        blade(page, pts)
    for pts in [
        [[726, 861], [754, 821], [750, 912]],
        [[775, 888], [806, 840], [799, 948]],
        [[824, 914], [854, 865], [847, 982]],
    ]:
        poly(page, pts, fill=INK, decorative=True)
    whisker(page, [[166, 986], [212, 882], [244, 804]], 4)
    whisker(page, [[205, 986], [247, 875], [279, 790]], 4)
    whisker(page, [[238, 986], [280, 872], [318, 782]], 4)
    whisker(page, [[748, 972], [766, 878], [774, 780]], 3.7)
    whisker(page, [[793, 966], [811, 868], [825, 768]], 3.7)

    # Interior fur strokes and torn silhouette accents.
    for pts in [
        [[101, 318], [153, 290], [129, 331], [196, 295]],
        [[118, 449], [170, 430], [137, 463], [208, 456]],
        [[188, 668], [233, 628], [213, 702]],
        [[562, 505], [611, 488], [583, 535], [642, 517]],
        [[613, 576], [664, 543], [649, 614], [704, 561]],
        [[600, 685], [648, 631], [629, 723], [680, 661]],
        [[548, 826], [601, 759], [572, 898]],
    ]:
        blade(page, pts)

    for pts in [
        [[169, 553], [217, 526], [190, 568], [251, 545]],
        [[186, 620], [240, 594], [209, 643], [270, 615]],
        [[226, 740], [271, 690], [252, 786]],
        [[258, 784], [292, 724], [283, 846]],
        [[632, 353], [692, 329], [663, 378], [731, 355]],
        [[674, 431], [735, 398], [704, 463], [774, 437]],
    ]:
        blade(page, pts)

    # Fine white linework for stern expression, brow scars, and fur rhythm.
    whisker(page, [[211, 180], [243, 196], [284, 194]], 5)
    whisker(page, [[321, 188], [363, 184], [409, 171]], 5)
    whisker(page, [[226, 257], [265, 274], [321, 276], [374, 259]], 4)
    whisker(page, [[240, 339], [284, 366], [343, 362], [394, 333]], 5)
    whisker(page, [[530, 315], [593, 302], [654, 316]], 4.5)
    whisker(page, [[615, 360], [687, 348], [752, 369]], 4.2)
    whisker(page, [[667, 414], [728, 408], [784, 423]], 4)
    for x in [220, 248, 279, 313, 347, 381]:
        page.line([x, 805], [x - 42, 980], **sw(4, PAPER), decorative=True)
    for x in [432, 463, 497, 532, 568]:
        page.line([x, 790], [x - 84, 1000], **sw(4, PAPER), decorative=True)
    for x in [642, 677, 711, 746, 779]:
        page.line([x, 650], [x + 15, 880], **sw(4, PAPER), decorative=True)

    # A few black islands inside white cuts recover the hand-inked stencil feel.
    poly(page, [[196, 438], [241, 413], [222, 466]], fill=INK, decorative=True)
    poly(page, [[420, 430], [507, 397], [471, 453]], fill=INK, decorative=True)
    poly(page, [[304, 612], [332, 590], [329, 682]], fill=INK, decorative=True)
    poly(page, [[719, 731], [750, 690], [748, 800]], fill=INK, decorative=True)
    poly(page, [[354, 519], [452, 497], [420, 536], [333, 551]], fill=INK, decorative=True)
    poly(page, [[520, 505], [608, 520], [574, 548], [491, 532]], fill=INK, decorative=True)
    poly(page, [[126, 424], [181, 386], [169, 444], [118, 470]], fill=INK, decorative=True)
    poly(page, [[664, 431], [724, 389], [704, 462], [646, 493]], fill=INK, decorative=True)
    poly(page, [[205, 560], [259, 548], [241, 590], [185, 602]], fill=INK, decorative=True)
    poly(page, [[332, 578], [384, 548], [365, 620], [318, 645]], fill=INK, decorative=True)
    poly(page, [[748, 846], [785, 798], [778, 902], [738, 932]], fill=INK, decorative=True)
    poly(page, [[101, 928], [141, 880], [134, 979], [89, 1000]], fill=INK, decorative=True)
    whisker(page, [[520, 340], [580, 325], [649, 334], [717, 362]], 3.2)
    whisker(page, [[585, 405], [652, 391], [721, 403], [782, 431]], 3.2)
    whisker(page, [[312, 428], [366, 392], [438, 382], [512, 399]], 3.0)
    whisker(page, [[298, 475], [363, 445], [438, 438], [516, 459]], 3.0)

    # Invisible accessibility label.
    page.text(
        [24, H - 36, 440, 20],
        "Black and white vector gorilla stencil study",
        id="caption",
        style="caption",
        opacity=0.0,
    )
    return doc


def main() -> int:
    out = os.path.join(ROOT, "fixtures", "gorilla-stencil-document.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [issue for issue in report.issues if issue.severity == "error"]
    warnings = [issue for issue in report.issues if issue.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warnings)} -> {out}")
    for issue in (errors + warnings)[:20]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
