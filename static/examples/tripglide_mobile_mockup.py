#!/usr/bin/env python3
"""Compose a TripGlide-style travel mobile app mockup with the FrameForge SDK.

The reference is a two-phone product shot: a home/search travel discovery screen
and a destination detail screen, both on a pale studio background. This example
recreates the composition as vector artwork: device chrome, status bars, rounded
cards, bottom navigation, chips, destination imagery, and angled phone placement.

Run from the repository root::

    uv run python examples/tripglide_mobile_mockup.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, Mat3, serialize  # noqa: E402
from frameforge.sdk.clip import clip_rect  # noqa: E402
from frameforge.sdk.paint import effects, linear_gradient, radial_gradient, shadow, stroke  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

OUT = os.path.join(ROOT, "tests", "fixtures", "tripglide-mobile-mockup.fg.yaml")
W, H = 1600, 1000
PW, PH = 430, 880
SCREEN_PAD = 24
SCREEN = [SCREEN_PAD, SCREEN_PAD, PW - 2 * SCREEN_PAD, PH - 2 * SCREEN_PAD]
SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]

COLORS = {
    "stage": "#D4D7D8",
    "stage2": "#C9CDCE",
    "phone": "#121416",
    "metal": "#6E7374",
    "glass": "#FAFBFC",
    "ink": "#202326",
    "muted": "#818589",
    "soft": "#F1F2F3",
    "card": "#FFFFFF",
    "nav": "#202326",
    "line": "#E5E8EA",
    "lake": "#35B9C7",
    "sky": "#9EDCE5",
    "terra": "#B75C32",
    "terra2": "#E09158",
    "forest": "#426C3B",
    "gold": "#F3C846",
    "blue": "#3A6EE8",
}


def ts(size, weight=500, color="ink", align="left", lh=1.18):
    return {
        "font_family": SANS,
        "font_size": size,
        "font_weight": weight,
        "color": color,
        "align": align,
        "letter_spacing": 0,
        "line_height": lh,
    }


STYLES = {
    "time": ts(17, 800, "ink"),
    "time_light": ts(17, 800, "card"),
    "h1": ts(30, 850, "ink"),
    "h2": ts(25, 850, "ink"),
    "sub": ts(17, 500, "muted"),
    "search": ts(20, 500, "muted"),
    "chip": ts(18, 600, "muted", "center"),
    "chip_active": ts(18, 700, "card", "center"),
    "place": ts(18, 650, "card"),
    "card_title": ts(25, 850, "card"),
    "small_light": ts(15, 600, "card"),
    "btn": ts(18, 750, "card", "center"),
    "detail_title": ts(30, 850, "ink"),
    "body": ts(18, 500, "ink", lh=1.32),
    "label": ts(18, 800, "ink"),
    "tour_title": ts(20, 800, "ink"),
    "tour_meta": ts(15, 500, "muted"),
    "rating": ts(16, 700, "ink"),
    "reviews": ts(15, 500, "muted"),
    "nav_icon": ts(27, 700, "card", "center"),
    "nav_dark": ts(27, 700, "ink", "center"),
    "glyph": ts(24, 650, "ink", "center"),
}


def add_tokens(doc: DocumentBuilder) -> None:
    for name, color in COLORS.items():
        doc.define_color(name, color)
    for name, style in STYLES.items():
        doc.define_text_style(name, **style)


def soft_rect(page, box, fill="card", radius=26, opacity=None, sh=False, **extra):
    fields = {"fill": fill, "radius": radius, **extra}
    if opacity is not None:
        fields["opacity"] = opacity
    if sh:
        fields.update(effects(shadow=shadow(dy=14, blur=28, color="#6E7374", opacity=0.16)))
    page.rect(box, **fields)


def circle(page, cx, cy, r, fill="card", stroke_color=None, sw=1.4, **extra):
    fields = {"fill": fill, **extra}
    if stroke_color:
        fields.update(stroke(sw, color=stroke_color))
    page.ellipse([cx, cy], r, r, **fields)


def icon_search(page, cx, cy, s=1.0, color="ink"):
    page.ellipse([cx, cy], 12 * s, 12 * s, fill="none", **stroke(2.7 * s, color=color, cap="round"))
    page.line([cx + 9 * s, cy + 9 * s], [cx + 19 * s, cy + 19 * s], **stroke(2.7 * s, color=color, cap="round"))


def icon_sliders(page, cx, cy, color="card"):
    for y, knob in [(-10, 8), (0, -7), (10, 5)]:
        page.line([cx - 13, cy + y], [cx + 13, cy + y], **stroke(2.2, color=color, cap="round"))
        circle(page, cx + knob, cy + y, 3.7, fill="nav")
        circle(page, cx + knob, cy + y, 2.2, fill=color)


def icon_heart(page, cx, cy, s=1.0, color="card", sw=2.4):
    d = (
        f"M {cx} {cy+13*s} C {cx-20*s} {cy-2*s} {cx-15*s} {cy-21*s} {cx-1*s} {cy-12*s} "
        f"C {cx+14*s} {cy-21*s} {cx+20*s} {cy-2*s} {cx} {cy+13*s} Z"
    )
    page.path(d, fill="none", **stroke(sw, color=color, join="round", cap="round"))


def icon_star(page, cx, cy, r=11, fill="none", color="card", sw=1.8):
    page.star([cx, cy], r, r * 0.44, 5, fill=fill, **stroke(sw, color=color, join="round"))


def icon_home(page, cx, cy, color="ink"):
    page.path(
        f"M {cx-14} {cy} L {cx} {cy-13} L {cx+14} {cy} L {cx+14} {cy+16} L {cx-14} {cy+16} Z",
        fill="none",
        **stroke(2.4, color=color, cap="round", join="round"),
    )
    page.line([cx - 5, cy + 16], [cx - 5, cy + 5], **stroke(2.4, color=color, cap="round"))
    page.line([cx + 5, cy + 16], [cx + 5, cy + 5], **stroke(2.4, color=color, cap="round"))


def icon_grid(page, cx, cy, color="card"):
    for dx in [-8, 8]:
        for dy in [-8, 8]:
            circle(page, cx + dx, cy + dy, 2.8, fill=color)


def icon_list(page, cx, cy, color="card"):
    for dy in [-8, 0, 8]:
        page.line([cx - 12, cy + dy], [cx + 12, cy + dy], **stroke(2.2, color=color, cap="round"))
        circle(page, cx - 16, cy + dy, 2.0, fill=color)


def flag_brazil(page, cx, cy, s=1.0):
    circle(page, cx, cy, 12 * s, fill="#4EB354")
    page.polygon([[cx, cy - 9 * s], [cx + 11 * s, cy], [cx, cy + 9 * s], [cx - 11 * s, cy]], fill="gold")
    circle(page, cx, cy, 4.6 * s, fill="blue")


def mountain_photo(page, box, variant="rio", radius=0, clip_radius=None):
    x, y, w, h = box
    clip = clip_rect([x, y, w, h])
    with page.grouped(clip=clip) as g:
        sky = linear_gradient([("#A8E6EE", 0), ("#65C5DA", 0.45), ("#F7B77F", 1)], angle=90)
        g.rect([x, y, w, h], fill=sky)
        if variant == "lake":
            g.rect([x, y + h * 0.55, w, h * 0.45], fill="#28B8C9")
            g.polygon([[x, y + h * 0.50], [x + w * 0.22, y + h * 0.30], [x + w * 0.46, y + h * 0.55]], fill="#244B2D", opacity=0.95)
            g.polygon([[x + w * 0.20, y + h * 0.54], [x + w * 0.55, y + h * 0.26], [x + w, y + h * 0.56]], fill="#4F7A3F")
            g.polygon([[x + w * 0.62, y + h * 0.55], [x + w * 0.86, y + h * 0.37], [x + w, y + h * 0.56]], fill="#2B5834")
            g.path(f"M {x} {y+h*.62} C {x+w*.25} {y+h*.56} {x+w*.60} {y+h*.73} {x+w} {y+h*.64}", fill="none", **stroke(4, color="#6BE4EC", cap="round"))
            return
        if variant == "sunset":
            g.rect([x, y + h * 0.46, w, h * 0.54], fill="#AF6B32")
            g.polygon([[x - 20, y + h * 0.62], [x + w * 0.30, y + h * 0.20], [x + w * 0.62, y + h * 0.62]], fill="#C57938")
            g.polygon([[x + w * 0.10, y + h * 0.62], [x + w * 0.54, y + h * 0.28], [x + w + 20, y + h * 0.64]], fill="#7F462A")
            g.polygon([[x + w * 0.22, y + h * 0.62], [x + w * 0.46, y + h * 0.40], [x + w * 0.72, y + h * 0.64]], fill="#D89050")
            return
        g.rect([x, y + h * 0.55, w, h * 0.45], fill="#253F36")
        g.polygon([[x - 40, y + h * 0.73], [x + w * 0.28, y + h * 0.34], [x + w * 0.54, y + h * 0.75]], fill="#8E4F33")
        g.polygon([[x + w * 0.20, y + h * 0.74], [x + w * 0.52, y + h * 0.20], [x + w * 0.88, y + h * 0.75]], fill="#C36B3A")
        g.polygon([[x + w * 0.48, y + h * 0.75], [x + w * 0.70, y + h * 0.32], [x + w + 30, y + h * 0.73]], fill="#495A5A")
        g.polygon([[x + w * 0.48, y + h * 0.20], [x + w * 0.53, y + h * 0.29], [x + w * 0.42, y + h * 0.29]], fill="#F3D3AD")
        g.polygon([[x + w * 0.66, y + h * 0.33], [x + w * 0.72, y + h * 0.43], [x + w * 0.60, y + h * 0.44]], fill="#E8E2D5")
        g.path(f"M {x+w*.06} {y+h*.78} C {x+w*.26} {y+h*.64} {x+w*.52} {y+h*.64} {x+w*.84} {y+h*.98}", fill="none", opacity=0.55, **stroke(3.2, color="#C7B18B", cap="round"))


def phone_shell(page, light_status=True):
    page.rect([-5, 228, 7, 70], fill="metal", radius=3)
    page.rect([-5, 318, 7, 92], fill="metal", radius=3)
    page.rect([PW - 2, 338, 7, 82], fill="metal", radius=3)
    soft_rect(page, [0, 0, PW, PH], fill="metal", radius=76, opacity=0.95)
    soft_rect(page, [8, 8, PW - 16, PH - 16], fill="phone", radius=69)
    soft_rect(page, [21, 24, PW - 42, PH - 48], fill="glass", radius=56)
    soft_rect(page, [PW / 2 - 62, 40, 124, 36], fill="#030405", radius=18)
    circle(page, PW / 2 + 44, 58, 7, fill="#0A1228")
    circle(page, PW / 2 + 47, 57, 3, fill="#1E3D9D", opacity=0.65)
    page.text([70, 58, 60, 18], "9:41", style="time_light" if light_status else "time")
    for i, ht in enumerate([6, 9, 12, 15]):
        page.rect([PW - 128 + i * 8, 67 - ht, 5, ht], fill="card" if light_status else "ink", radius=2)
    page.path(f"M {PW-88} 57 C {PW-78} 50 {PW-68} 50 {PW-58} 57", fill="none", **stroke(2.5, color="card" if light_status else "ink", cap="round"))
    page.rect([PW - 48, 52, 28, 13], fill="none", **stroke(2, color="card" if light_status else "ink"), radius=3)
    page.rect([PW - 44, 55, 19, 7], fill="card" if light_status else "ink", radius=2)
    page.rect([PW / 2 - 62, PH - 24, 124, 5], fill="#050607", radius=3)


def status_overlay(page, light_status=True):
    color = "card" if light_status else "ink"
    page.text([70, 58, 60, 18], "9:41", style="time_light" if light_status else "time")
    soft_rect(page, [PW / 2 - 62, 40, 124, 36], fill="#030405", radius=18)
    circle(page, PW / 2 + 44, 58, 7, fill="#0A1228")
    circle(page, PW / 2 + 47, 57, 3, fill="#1E3D9D", opacity=0.65)
    for i, ht in enumerate([6, 9, 12, 15]):
        page.rect([PW - 128 + i * 8, 67 - ht, 5, ht], fill=color, radius=2)
    page.path(f"M {PW-88} 57 C {PW-78} 50 {PW-68} 50 {PW-58} 57", fill="none", **stroke(2.5, color=color, cap="round"))
    page.rect([PW - 48, 52, 28, 13], fill="none", **stroke(2, color=color), radius=3)
    page.rect([PW - 44, 55, 19, 7], fill=color, radius=2)


def search_screen(page):
    phone_shell(page, light_status=False)
    sx, sy, sw, sh = SCREEN
    page.text([sx + 8, sy + 88, 250, 36], "Hello, Vanessa", style="h1")
    page.text([sx + 8, sy + 128, 240, 22], "Welcome to TripGlide", style="sub")
    with page.grouped(clip=clip_rect([sx + sw - 72, sy + 72, 54, 54])) as g:
        circle(g, sx + sw - 45, sy + 99, 27, fill="#73C5D6")
        circle(g, sx + sw - 45, sy + 88, 16, fill="#2B1D18")
        g.rect([sx + sw - 64, sy + 103, 38, 28], fill="#F7B35D", radius=16)
        g.path(f"M {sx+sw-62} {sy+95} C {sx+sw-54} {sy+74} {sx+sw-34} {sy+75} {sx+sw-27} {sy+96}", fill="none", **stroke(6, color="#1C1613", cap="round"))

    soft_rect(page, [sx + 8, sy + 178, sw - 16, 74], fill="card", radius=36, sh=True)
    icon_search(page, sx + 58, sy + 214, 1.15, "ink")
    page.text([sx + 95, sy + 201, 150, 26], "Search", style="search")
    circle(page, sx + sw - 72, sy + 215, 34, fill="nav")
    icon_sliders(page, sx + sw - 72, sy + 215, "card")

    page.text([sx + 8, sy + 292, 270, 34], "Select your next trip", style="h2")
    chips = [("Asia", 30, False), ("Europe", 132, False), ("South America", 258, True), ("Nor", 496, False)]
    for label, cx, active in chips:
        width = 96 if len(label) < 6 else 194
        soft_rect(page, [sx + cx, sy + 344, width, 51], fill="nav" if active else "card", radius=28)
        page.text([sx + cx, sy + 359, width, 20], label, style="chip_active" if active else "chip")

    # Side cards visible behind the active destination card.
    mountain_photo(page, [sx + 16, sy + 426, 150, 326], variant="lake", radius=34, clip_radius=34)
    mountain_photo(page, [sx + sw - 82, sy + 416, 94, 336], variant="sunset", radius=34, clip_radius=34)

    card = [sx + 42, sy + 402, sw - 72, 330]
    soft_rect(page, card, fill="card", radius=36, sh=True)
    mountain_photo(page, card, variant="rio", radius=36, clip_radius=36)
    page.rect([card[0], card[1] + card[3] * 0.48, card[2], card[3] * 0.52], fill=linear_gradient([("#00000000", 0), ("#111315", 0.72)], angle=90), radius=36, opacity=0.96)
    circle(page, card[0] + card[2] - 58, card[1] + 58, 32, fill="#FFFFFF22", stroke_color="#FFFFFF77")
    icon_heart(page, card[0] + card[2] - 58, card[1] + 58, 0.9, "card", 2.3)
    page.text([card[0] + 30, card[1] + card[3] - 156, 150, 22], "Brazil", style="place")
    page.text([card[0] + 30, card[1] + card[3] - 119, 260, 36], "Rio de Janeiro", style="card_title")
    icon_star(page, card[0] + 52, card[1] + card[3] - 65, 10, color="card")
    page.text([card[0] + 68, card[1] + card[3] - 78, 44, 22], "5.0", style="small_light")
    page.text([card[0] + 126, card[1] + card[3] - 78, 110, 22], "143 reviews", style="small_light")
    soft_rect(page, [card[0] + 30, card[1] + card[3] - 80, card[2] - 60, 68], fill="#2B2D2FCC", radius=36)
    page.text([card[0] + 30, card[1] + card[3] - 57, card[2] - 60, 23], "See more", style="btn")
    circle(page, card[0] + card[2] - 62, card[1] + card[3] - 46, 30, fill="card")
    page.text([card[0] + card[2] - 77, card[1] + card[3] - 63, 30, 34], "›", style="nav_dark")

    soft_rect(page, [sx + 44, sy + sh - 102, sw - 88, 70], fill="nav", radius=38, sh=True)
    circle(page, sx + 102, sy + sh - 67, 35, fill="card")
    icon_home(page, sx + 102, sy + sh - 76, "ink")
    icon_list(page, sx + 190, sy + sh - 68, "card")
    icon_heart(page, sx + 276, sy + sh - 69, 0.68, "card", 2.4)
    icon_grid(page, sx + 356, sy + sh - 68, "card")


def tour_card(page, x, y, w, variant="sunset", title="Iconic Brazil", rating="4.6", reviews="56 reviews"):
    soft_rect(page, [x, y, w, 324], fill="card", radius=24, sh=True)
    mountain_photo(page, [x + 12, y + 12, w - 24, 178], variant=variant, radius=20, clip_radius=20)
    circle(page, x + w - 50, y + 58, 28, fill="card")
    icon_heart(page, x + w - 50, y + 58, 0.78, "ink", 2.2)
    page.text([x + 18, y + 206, w - 36, 25], title, style="tour_title")
    page.text([x + 18, y + 240, w - 36, 19], "8 days  •  from $659/person", style="tour_meta")
    icon_star(page, x + 28, y + 292, 9, color="ink")
    page.text([x + 44, y + 282, 38, 20], rating, style="rating")
    page.text([x + 90, y + 282, 110, 20], reviews, style="reviews")
    circle(page, x + w - 52, y + 286, 30, fill="nav")
    page.text([x + w - 68, y + 268, 32, 36], "→", style="nav_icon")


def detail_screen(page):
    phone_shell(page, light_status=True)
    sx, sy, sw, sh = SCREEN
    hero = [sx, sy, sw, 360]
    mountain_photo(page, hero, variant="rio", radius=50, clip_radius=50)
    page.rect([sx, sy, sw, 360], fill=linear_gradient([("#00000022", 0), ("#00000000", 0.65)], angle=90), radius=50)
    status_overlay(page, light_status=True)
    circle(page, sx + 56, sy + 102, 34, fill="card")
    page.text([sx + 40, sy + 80, 32, 40], "‹", style="glyph")
    circle(page, sx + sw - 56, sy + 104, 34, fill="card")
    icon_heart(page, sx + sw - 56, sy + 104, 0.83, "ink", 2.2)

    panel_y = sy + 316
    d = f"M {sx} {panel_y+32} C {sx+60} {panel_y-18} {sx+sw-70} {panel_y-4} {sx+sw} {panel_y+42} L {sx+sw} {sy+sh} L {sx} {sy+sh} Z"
    page.path(d, fill="glass")
    page.rect([sx + sw / 2 - 40, panel_y + 24, 80, 5], fill="line", radius=3)
    page.text([sx + 26, panel_y + 64, 270, 42], "Rio de Janeiro", style="detail_title")
    flag_brazil(page, sx + 42, panel_y + 128, 0.88)
    page.text([sx + 68, panel_y + 117, 85, 24], "Brazil", style="label")
    soft_rect(page, [sx + sw - 105, panel_y + 85, 78, 37], fill="card", radius=18, stroke="line")
    icon_star(page, sx + sw - 84, panel_y + 104, 9, color="ink")
    page.text([sx + sw - 66, panel_y + 93, 36, 20], "5.0", style="rating")
    page.text([sx + sw - 124, panel_y + 147, 108, 23], "143 reviews", style="label")
    page.line([sx + sw - 124, panel_y + 174], [sx + sw - 16, panel_y + 174], **stroke(1.8, color="ink", cap="round"))
    body = "Rio de Janeiro, often simply called Rio, is one\nof Brazil's most iconic cities, renowned for..."
    page.text([sx + 26, panel_y + 196, sw - 52, 72], body, style="body")
    page.text([sx + 26, panel_y + 286, 120, 24], "Read more", style="label")
    page.line([sx + 26, panel_y + 313], [sx + 118, panel_y + 313], **stroke(1.8, color="ink", cap="round"))
    page.text([sx + 26, panel_y + 366, 230, 32], "Upcoming tours", style="h2")
    page.text([sx + sw - 94, panel_y + 382, 70, 20], "See all", style="label")
    page.line([sx + sw - 94, panel_y + 406], [sx + sw - 33, panel_y + 406], **stroke(1.5, color="ink", cap="round"))
    tour_card(page, sx + 18, panel_y + 426, 330, "sunset", "Iconic Brazil", "4.6", "56 reviews")
    tour_card(page, sx + 368, panel_y + 438, 220, "lake", "Beach", "4.8", "")


def build_document():
    doc = DocumentBuilder(title="TripGlide mobile mockup")
    add_tokens(doc)
    page = doc.page("tripglide-two-phone-composition", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.layer("stage")
    page.rect([0, 0, W, H], fill=linear_gradient([("stage", 0), ("stage2", 1)], angle=105))
    page.ellipse([800, 860], 520, 70, fill="#A9AFB1", opacity=0.23)

    page.layer("phones")
    # Backing soft shadows in page coordinates before rotating the devices.
    page.ellipse([505, 845], 210, 52, fill="#8B9294", opacity=0.18)
    page.ellipse([1085, 848], 220, 52, fill="#8B9294", opacity=0.18)

    with page.grouped(transform=Mat3.translate(232, 62) @ Mat3.rotate(-1.8)) as left:
        search_screen(left)
    with page.grouped(transform=Mat3.translate(835, 79) @ Mat3.rotate(4.0)) as right:
        detail_screen(right)
    return doc


def build():
    return build_document()


def main() -> None:
    doc = build_document().build()
    report = validate_static_rules(doc)
    if not report.ok:
        for issue in report.issues:
            print(issue)
        raise SystemExit(1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(OUT)


if __name__ == "__main__":
    main()
