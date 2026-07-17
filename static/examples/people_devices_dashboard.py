#!/usr/bin/env python3
"""High-fidelity vector recreation of an HR "People / Devices / Security" mobile
dashboard (3 phone screens) using the FrameForge SDK.

  1. People    — metric pills (Interviews/Hired/Project time/Output) + scrolling
                 people cards (avatar, role, status, dept/country/salary). The
                 list is CLIPPED to the phone body so it cuts off at the bottom.
  2. Devices   — device chips + a stylised world "Map Session" with numbered
                 markers + a selected-device card.
  3. Security  — a two-tone "Security status" gauge (55% / Medium Risk) + a dark
                 "Session History" list (device icon, avatar, time, country flag).

Vector techniques: rounded-rect clip paths (page.group(clip=...)), gauge as a
thick round-cap polyline arc, stylised flat avatars, mini flags, a blobby world
map, and SDK gradients. Photos are recreated as vector stand-ins.

Run from the repository root::

    uv run python examples/people_devices_dashboard.py
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
    clip_path,
    linear_gradient,
    rgba,
)
from frameforge.sdk.paint import effects, shadow  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas + palette
# --------------------------------------------------------------------------- #
W, H = 1500, 1140
PW, PH, PR = 360, 880, 46          # phone width / height / corner radius

COLORS = {
    "stage":   "#9AA1AD",
    "stage2":  "#888F9C",
    "body":    "#6C7178",          # phone screen base
    "body2":   "#777C84",
    "panel":   "#5E636B",          # map / inner panel (darker)
    "ink":     "#23272E",          # dark navy
    "white":   "#F4F4F6",
    "g9":      "#9DA1A9",
    "g8":      "#878C94",
    "g6":      "#6B7079",
    "mut":     "#B7BAC1",          # muted on dark
    "card":    "#FBFBFC",          # white card
    "cardLt":  "#DDDEE2",          # light gray card
    "cardDk":  "#2A2E36",          # dark navy card
    "yellow":  "#E9F24B",
    "yellowDk": "#D4DE39",
    "green":   "#CDE8A2",
    "greenDot": "#6FAF4A",
    "graypill": "#C8CACF",
    "graydot": "#8B8F97",
    "line":    "#E6E6EA",
    "land":    "#C6C8CC",          # map continents
}

SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]


def _ts(size, weight=500, color="ink", align="left", ls=0.0, lh=1.25):
    return dict(font_family=SANS, font_size=size, font_weight=weight,
                color=color, align=align, letter_spacing=ls, line_height=lh)


STYLES = {
    "h1":       _ts(40, 800, "white", "left", -1.0),
    "h2white":  _ts(25, 700, "white", "left", -0.4),
    "h2ink":    _ts(27, 700, "ink", "center", -0.4),
    "statLbl":  _ts(12, 500, "mut", "left"),
    "pctDark":  _ts(15, 800, "white", "center"),
    "pctYel":   _ts(16, 800, "ink", "center"),
    "pctOut":   _ts(14, 700, "white", "center"),
    "name":     _ts(17, 700, "ink", "left", -0.2),
    "role":     _ts(13, 500, "g8", "left"),
    "pillG":    _ts(13, 600, "ink", "center"),
    "colLbl":   _ts(12, 500, "g9", "left"),
    "colVal":   _ts(14, 700, "ink", "left"),
    "dateLbl":  _ts(13, 500, "g9", "left"),
    "dateVal":  _ts(14, 700, "ink", "left"),
    "navPill":  _ts(14, 600, "ink", "center"),
    "export":   _ts(15, 600, "ink", "left"),
    "devName":  _ts(13, 700, "ink", "left"),
    "devItems": _ts(13, 500, "g8", "left"),
    "macAir":   _ts(16, 700, "ink", "left"),
    "macVer":   _ts(13, 500, "g8", "left"),
    "macLoc":   _ts(14, 600, "ink", "left"),
    "macTime":  _ts(13, 500, "g8", "right"),
    "bigPct":   _ts(36, 800, "ink", "center", -1.0),
    "risk":     _ts(14, 500, "g6", "center"),
    "sessName": _ts(15, 700, "white", "left"),
    "sessTime": _ts(12, 500, "mut", "left"),
    "city":     _ts(12, 500, "mut", "right"),
    "count":    _ts(22, 700, "white", "right"),
    "mapNum":   _ts(13, 800, "ink", "center"),
}


# --------------------------------------------------------------------------- #
# A tiny collector that mirrors the PageBuilder primitive API so a screen can be
# drawn imperatively and then emitted as ONE clipped group.
# --------------------------------------------------------------------------- #
class Collector:
    """Mirrors the PageBuilder primitive API. Shapes are tagged ``decorative`` by
    default: this is illustrative artwork, so the free-group overlap/containment
    heuristics (meant to catch accidental diagram overlaps) should not fire on the
    deliberately layered avatars, gauge arcs and flags. Text stays semantic."""

    def __init__(self):
        self.objs: list[dict] = []

    def _add(self, o, deco=True):
        if deco and "decorative" not in o:
            o["decorative"] = True
        self.objs.append(o)
        return self

    def rect(self, box, **f):
        return self._add({"type": "rect", "box": box, **f})

    def text(self, box, text, **f):
        return self._add({"type": "text", "box": box, "text": text, **f}, deco=False)

    def ellipse(self, c, rx, ry, **f):
        return self._add({"type": "ellipse", "center": [c[0], c[1]], "rx": rx, "ry": ry, **f})

    def circle(self, c, r, **f):
        return self.ellipse(c, r, r, **f)

    def line(self, a, b, **f):
        return self._add({"type": "line", "from": a, "to": b, **f})

    def polyline(self, pts, *, closed=False, **f):
        o = {"type": "polyline", "points": pts}
        if closed:
            o["closed"] = True
        o.update(f)
        return self._add(o)

    def polygon(self, pts, **f):
        # Emit the canonical closed polyline (not the deprecated `polygon` alias).
        o = {"type": "polyline", "points": pts, "closed": True}
        o.update(f)
        return self._add(o)

    def path(self, d, **f):
        return self._add({"type": "path", "d": d, **f})


def rrect(x, y, w, h, r):
    return (f"M{x+r},{y} H{x+w-r} A{r},{r} 0 0 1 {x+w},{y+r} V{y+h-r} "
            f"A{r},{r} 0 0 1 {x+w-r},{y+h} H{x+r} A{r},{r} 0 0 1 {x},{y+h-r} "
            f"V{y+r} A{r},{r} 0 0 1 {x+r},{y} Z")


def lg(p0, p1, stops):
    ang = round(math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])), 1)
    return linear_gradient([(c, pos) for pos, c in stops], angle=ang)


SHADOW = effects(shadow=shadow(dy=10, blur=26, color="#3C4047", opacity=0.22))


# --------------------------------------------------------------------------- #
# Icons / glyphs
# --------------------------------------------------------------------------- #
def chevron(s, cx, cy, color="ink", sz=9):
    s.polyline([[cx + sz * 0.4, cy - sz], [cx - sz * 0.5, cy], [cx + sz * 0.4, cy + sz]],
               fill="none", stroke=color,
               stroke_style={"stroke_width": 2.4, "stroke_linecap": "round", "stroke_linejoin": "round"})


def plus(s, cx, cy, color="ink", sz=9):
    s.line([cx - sz, cy], [cx + sz, cy], stroke=color, stroke_style={"stroke_width": 2.4, "stroke_linecap": "round"})
    s.line([cx, cy - sz], [cx, cy + sz], stroke=color, stroke_style={"stroke_width": 2.4, "stroke_linecap": "round"})


def minus(s, cx, cy, color="ink", sz=9):
    s.line([cx - sz, cy], [cx + sz, cy], stroke=color, stroke_style={"stroke_width": 2.4, "stroke_linecap": "round"})


def sliders(s, cx, cy, color="ink"):
    for dy, kx in ((-5, 4), (5, -4)):
        s.line([cx - 9, cy + dy], [cx + 9, cy + dy], stroke=color,
               stroke_style={"stroke_width": 2.0, "stroke_linecap": "round"})
        s.ellipse([cx + kx, cy + dy], 3.0, 3.0, fill="white", stroke=color,
                  stroke_style={"stroke_width": 2.0})


def smiley(s, cx, cy, r=10, color="ink"):
    s.ellipse([cx, cy], r, r, fill="none", stroke=color, stroke_style={"stroke_width": 1.8})
    s.ellipse([cx - r * 0.32, cy - r * 0.18], 1.4, 1.4, fill=color)
    s.ellipse([cx + r * 0.32, cy - r * 0.18], 1.4, 1.4, fill=color)
    s.path(f"M {cx-r*0.42} {cy+r*0.18} Q {cx} {cy+r*0.62} {cx+r*0.42} {cy+r*0.18}",
           fill="none", stroke=color, stroke_style={"stroke_width": 1.8, "stroke_linecap": "round"})


def kebab(s, cx, cy, color="g8"):
    for dy in (-6, 0, 6):
        s.ellipse([cx, cy + dy], 1.8, 1.8, fill=color)


def checkbox(s, x, y, sz=30, checked=False):
    if checked:
        s.rect([x, y, sz, sz], fill="ink", radius=9)
        s.polyline([[x + sz * 0.26, y + sz * 0.52], [x + sz * 0.43, y + sz * 0.68],
                    [x + sz * 0.74, y + sz * 0.32]], fill="none", stroke="white",
                   stroke_style={"stroke_width": 2.4, "stroke_linecap": "round", "stroke_linejoin": "round"})
    else:
        s.rect([x, y, sz, sz], fill="none", stroke="g9", stroke_style={"stroke_width": 1.8}, radius=9)


def dev_glyph(s, cx, cy, kind, color="ink"):
    if kind == "laptop":
        s.rect([cx - 8, cy - 6, 16, 11], fill="none", stroke=color, stroke_style={"stroke_width": 1.7}, radius=2)
        s.line([cx - 11, cy + 7], [cx + 11, cy + 7], stroke=color, stroke_style={"stroke_width": 1.7, "stroke_linecap": "round"})
    elif kind == "tablet":
        s.rect([cx - 7, cy - 9, 14, 18], fill="none", stroke=color, stroke_style={"stroke_width": 1.7}, radius=3)
        s.ellipse([cx, cy + 6], 1.2, 1.2, fill=color)
    else:  # phone
        s.rect([cx - 5.5, cy - 9, 11, 18], fill="none", stroke=color, stroke_style={"stroke_width": 1.7}, radius=3)
        s.line([cx - 1.8, cy - 6.5], [cx + 1.8, cy - 6.5], stroke=color, stroke_style={"stroke_width": 1.5, "stroke_linecap": "round"})


def laptop_thumb(s, cx, cy):
    s.rect([cx - 22, cy - 14, 44, 28], fill=lg([cx, cy - 14], [cx, cy + 14],
           [(0, "#3A3F47"), (1, "#15181D")]), radius=4)
    s.rect([cx - 18, cy - 10, 36, 20], fill="#0E1014", radius=2)
    s.ellipse([cx - 9, cy - 3], 8, 6, fill=rgba("#7C8390", 0.5), decorative=True)
    s.rect([cx - 27, cy + 13, 54, 4], fill="#2A2E35", radius=2)


def phone_thumb(s, cx, cy):
    s.rect([cx - 13, cy - 18, 26, 36], fill=lg([cx, cy - 18], [cx, cy + 18],
           [(0, "#3A3F47"), (1, "#101317")]), radius=7)
    s.rect([cx - 9, cy - 14, 18, 28], fill="#0E1014", radius=4)
    s.ellipse([cx + 2, cy - 4], 7, 9, fill=rgba("#9AA0AC", 0.45), decorative=True)


def flag(s, x, y, code, w=24, h=16):
    r = 3
    bg = {"it": None, "fr": None, "us": "#B22234", "ua": "#0057B7",
          "ca": "#FFFFFF", "au": "#012169"}.get(code, "#CCCCCC")
    if code in ("it", "fr"):
        cols = {"it": ["#3A8E5C", "#FFFFFF", "#CE2B37"],
                "fr": ["#2A3E8F", "#FFFFFF", "#CE2B37"]}[code]
        for i, c in enumerate(cols):
            s.rect([x + i * w / 3, y, w / 3 + (0.6 if i < 2 else 0), h], fill=c,
                   radius=(r if i in (0, 2) else 0))
    elif code == "ua":
        s.rect([x, y, w, h / 2], fill="#0057B7", radius=r)
        s.rect([x, y + h / 2, w, h / 2], fill="#FFD700", radius=r)
        s.rect([x, y + h / 2 - 2, w, 4], fill="#0057B7")
        s.rect([x, y + h / 2, w, 2], fill="#FFD700")
    elif code == "us":
        s.rect([x, y, w, h], fill="#FFFFFF", radius=r)
        for i in range(4):
            s.rect([x, y + 1.6 + i * (h - 2) / 4, w, (h - 2) / 8], fill="#B22234")
        s.rect([x, y, w * 0.45, h * 0.55], fill="#2A3E8F", radius=r)
    elif code == "ca":
        s.rect([x, y, w, h], fill="#FFFFFF", radius=r)
        s.rect([x, y, w * 0.26, h], fill="#D52B1E", radius=r)
        s.rect([x + w * 0.74, y, w * 0.26, h], fill="#D52B1E", radius=r)
        s.ellipse([x + w / 2, y + h / 2], 3.0, 3.2, fill="#D52B1E")
    elif code == "au":
        s.rect([x, y, w, h], fill="#012169", radius=r)
        s.rect([x, y, w * 0.5, h * 0.5], fill="#0B2C7A")
        s.line([x, y], [x + w * 0.5, y + h * 0.5], stroke="#FFFFFF", stroke_style={"stroke_width": 1.4})
        s.line([x + w * 0.5, y], [x, y + h * 0.5], stroke="#FFFFFF", stroke_style={"stroke_width": 1.0})
        s.ellipse([x + w * 0.74, y + h * 0.62], 1.6, 1.6, fill="#FFFFFF")
        s.ellipse([x + w * 0.26, y + h * 0.78], 1.3, 1.3, fill="#FFFFFF")


# --------------------------------------------------------------------------- #
# Avatars (flat vector stand-ins for the photos)
# --------------------------------------------------------------------------- #
def avatar(s, cx, cy, r, skin, hair, shirt, longhair=False):
    s.ellipse([cx, cy], r, r, fill="#EAEAEE")
    s.ellipse([cx, cy + 0.54 * r], 0.74 * r, 0.46 * r, fill=shirt)       # shoulders
    s.rect([cx - 0.12 * r, cy + 0.02 * r, 0.24 * r, 0.30 * r], fill=skin)  # neck
    if longhair:
        s.ellipse([cx, cy - 0.02 * r], 0.48 * r, 0.52 * r, fill=hair)
        s.ellipse([cx, cy - 0.02 * r], 0.34 * r, 0.42 * r, fill=skin)
    else:
        s.ellipse([cx, cy - 0.06 * r], 0.40 * r, 0.43 * r, fill=skin)
        s.ellipse([cx, cy - 0.24 * r], 0.42 * r, 0.32 * r, fill=hair)
        s.ellipse([cx, cy - 0.02 * r], 0.36 * r, 0.34 * r, fill=skin)
    s.ellipse([cx - 0.14 * r, cy - 0.05 * r], 0.045 * r, 0.06 * r, fill="#33373E")
    s.ellipse([cx + 0.14 * r, cy - 0.05 * r], 0.045 * r, 0.06 * r, fill="#33373E")


AV = {
    "harry":   dict(skin="#E7B488", hair="#3B2E25", shirt="#46618F"),
    "katy":    dict(skin="#E2A983", hair="#2C2420", shirt="#C08A6A", longhair=True),
    "jonathan": dict(skin="#C2855A", hair="#2A201B", shirt="#6A707A"),
    "billie":  dict(skin="#E8C49C", hair="#C7A24B", shirt="#566AA2"),
    "sarah":   dict(skin="#ECC6A4", hair="#D8C07A", shirt="#B0644F", longhair=True),
    "erica":   dict(skin="#D7A87E", hair="#241C18", shirt="#7A5AA0", longhair=True),
}


# --------------------------------------------------------------------------- #
# Shared chrome
# --------------------------------------------------------------------------- #
def circle_btn(s, cx, cy, r=24, fill="cardLt"):
    s.ellipse([cx, cy], r, r, fill=fill)


def pill_nav(s, x, y, w, label, h=44):
    s.rect([x, y, w, h], fill="cardLt", radius=h / 2)
    s.text([x, y + h / 2 - 9, w, 18], label, style="navPill")


def topbar(s, x, y, w, *, mode):
    """mode 'people' or 'devices' header buttons."""
    circle_btn(s, x + 48, y + 30, 24)
    chevron(s, x + 48, y + 30, "ink")
    if mode == "people":
        # + , sliders, Export
        ex_w = 116
        ex_x = x + w - 24 - ex_w
        s.rect([ex_x, y + 6, ex_w, 48], fill="cardLt", radius=24)
        smiley(s, ex_x + 26, y + 30, 10, "ink")
        s.text([ex_x + 42, y + 21, ex_w - 50, 18], "Export", style="export")
        sl_cx = ex_x - 12 - 24
        circle_btn(s, sl_cx, y + 30, 24); sliders(s, sl_cx, y + 30, "ink")
        pl_cx = sl_cx - 12 - 48
        circle_btn(s, pl_cx, y + 30, 24); plus(s, pl_cx, y + 30, "ink", 8)
    else:
        sl_cx = x + w - 24 - 24
        circle_btn(s, sl_cx, y + 30, 24); sliders(s, sl_cx, y + 30, "ink")
        oc_w = 96
        oc_x = sl_cx - 24 - 12 - oc_w
        pill_nav(s, oc_x, y + 8, oc_w, "Org Chat")
        di_w = 96
        di_x = oc_x - 10 - di_w
        pill_nav(s, di_x, y + 8, di_w, "Directory")


# --------------------------------------------------------------------------- #
# Phone 1 — People
# --------------------------------------------------------------------------- #
def screen_people(s, x, y, w, h):
    s.rect([x, y, w, h], fill=lg([x, y], [x, y + h], [(0, "#71767D"), (1, "#656A71")]))
    topbar(s, x, y, w, mode="people")
    s.text([x + 24, y + 88, 260, 52], "People", style="h1")

    # metric pills
    labels_pills = [
        ("Interviews", "25%", x + 16, 66, "dark"),
        ("Hired", "51%", x + 88, 104, "yellow"),
        ("Project time", "10%", x + 204, 62, "hatch"),
        ("Output", "14%", x + 278, 58, "out"),
    ]
    ly = y + 168
    for label, pct, px, pwid, kind in labels_pills:
        s.text([px, ly, pwid + 30, 16], label, style="statLbl")
        py = ly + 24
        if kind == "yellow":
            s.rect([px, py - 6, pwid, 56], fill="yellow", radius=28)
            s.text([px, py + 12, pwid, 20], pct, style="pctYel")
        elif kind == "dark":
            s.rect([px, py, pwid, 44], fill="ink", radius=22)
            s.text([px, py + 13, pwid, 18], pct, style="pctDark")
        elif kind == "hatch":
            s.rect([px, py, pwid, 44], fill=rgba("#FFFFFF", 0.06), stroke="g9",
                   stroke_style={"stroke_width": 1.4}, radius=22)
            for k in range(-1, 5):
                s.line([px + k * 14, py + 44], [px + k * 14 + 22, py], stroke=rgba("#FFFFFF", 0.30),
                       stroke_style={"stroke_width": 1.4})
            s.text([px, py + 13, pwid, 18], pct, style="pctOut")
        else:
            s.rect([px, py, pwid, 44], fill="none", stroke="g9", stroke_style={"stroke_width": 1.4}, radius=22)
            s.text([px, py + 13, pwid, 18], pct, style="pctOut")

    people = [
        ("harry", "Harry Bender", "Head of Design", "green", "Product", "it", "Rome", "$1,350", "Mar 13, 2023", False),
        ("katy", "Katy Fuller", "Fullstack Engineer", "gray", "Engineering", "us", "Miami", "$1,500", "Oct 13, 2023", True),
        ("jonathan", "Jonathan Kelly", "Mobile Lead", "green", "Product", "ua", "Kyiv", "$1,350", "Mar 13, 2023", False),
        ("billie", "Billie Wright", "Backend Engineer", "green", "Engineering", "fr", "Paris", "$1,400", "Jan 9, 2023", False),
    ]
    cy0 = y + 300
    for i, (key, name, role, status, dept, fcode, city, sal, date, checked) in enumerate(people):
        cyT = cy0 + i * 214
        elevated = (status == "gray")
        s.rect([x + 16, cyT, w - 32, 196], fill="card", radius=24,
               **(SHADOW if elevated else {}))
        avatar(s, x + 56, cyT + 46, 28, **AV[key])
        s.text([x + 100, cyT + 26, 140, 22], name, style="name")
        s.text([x + 100, cyT + 50, 150, 16], role, style="role")
        # status pill
        if status == "green":
            s.rect([x + w - 132, cyT + 22, 108, 34], fill="green", radius=17)
            s.ellipse([x + w - 116, cyT + 39], 4, 4, fill="greenDot")
            s.text([x + w - 110, cyT + 30, 80, 16], "Invited", style="pillG")
        else:
            s.rect([x + w - 132, cyT + 22, 108, 34], fill="graypill", radius=17)
            s.ellipse([x + w - 116, cyT + 39], 4, 4, fill="graydot")
            s.text([x + w - 110, cyT + 30, 80, 16], "Invited", style="pillG")
        # columns
        s.text([x + 24, cyT + 86, 110, 14], "Departament", style="colLbl")
        s.text([x + 24, cyT + 106, 100, 18], dept, style="colVal")
        s.text([x + 152, cyT + 86, 90, 14], "Country", style="colLbl")
        flag(s, x + 152, cyT + 104, fcode)
        s.text([x + 182, cyT + 106, 90, 18], city, style="colVal")
        s.text([x + 262, cyT + 86, 80, 14], "Salary", style="colLbl")
        s.text([x + 262, cyT + 106, 90, 18], sal, style="colVal")
        s.line([x + 24, cyT + 140], [x + w - 24, cyT + 140], stroke="line", stroke_style={"stroke_width": 1.0})
        s.text([x + 24, cyT + 156, 90, 14], "Start date", style="dateLbl")
        s.text([x + 110, cyT + 155, 120, 18], date, style="dateVal")
        checkbox(s, x + w - 56, cyT + 150, 30, checked)


# --------------------------------------------------------------------------- #
# Phone 2 — Devices + Map Session
# --------------------------------------------------------------------------- #
NA = [(0.04, 0.16), (0.16, 0.07), (0.27, 0.10), (0.30, 0.20), (0.27, 0.30),
      (0.30, 0.40), (0.22, 0.50), (0.14, 0.44), (0.09, 0.32), (0.05, 0.24)]
SA = [(0.27, 0.55), (0.34, 0.56), (0.36, 0.66), (0.31, 0.82), (0.25, 0.90),
      (0.22, 0.76), (0.23, 0.63)]
EU = [(0.46, 0.16), (0.56, 0.13), (0.58, 0.22), (0.52, 0.27), (0.46, 0.24)]
AF = [(0.47, 0.34), (0.58, 0.32), (0.63, 0.46), (0.58, 0.64), (0.49, 0.66), (0.45, 0.50)]
AS = [(0.58, 0.10), (0.84, 0.07), (0.96, 0.20), (0.90, 0.34), (0.74, 0.38),
      (0.63, 0.30), (0.58, 0.18)]
AU = [(0.80, 0.62), (0.93, 0.60), (0.96, 0.72), (0.85, 0.76), (0.79, 0.68)]
US_DARK = [(0.07, 0.30), (0.27, 0.28), (0.30, 0.40), (0.22, 0.50), (0.12, 0.46), (0.07, 0.36)]


def _scale(pts, mx, my, mw, mh):
    return [[mx + px * mw, my + py * mh] for px, py in pts]


def screen_devices(s, x, y, w, h):
    s.rect([x, y, w, h], fill=lg([x, y], [x, y + h], [(0, "#71767D"), (1, "#646970")]))
    topbar(s, x, y, w, mode="devices")
    s.text([x + 24, y + 70, 260, 52], "Devices", style="h1")

    # device chips
    for i, (thumb, nm, items) in enumerate([(laptop_thumb, "MacBook Pro", "2 items"),
                                            (phone_thumb, "iPhone 16 Pro", "4 items")]):
        bx = x + 16 + i * 174
        s.rect([bx, y + 132, 164, 70], fill="card", radius=18)
        s.rect([bx + 12, y + 146, 42, 42], fill="#F0F0F2", radius=10)
        thumb(s, bx + 33, y + 167)
        s.text([bx + 64, y + 150, 96, 18], nm, style="devName")
        s.text([bx + 64, y + 172, 96, 16], items, style="devItems")

    # map panel
    mx, my, mw, mh = x + 0, y + 224, w, 372
    s.text([x + 24, y + 232, 240, 32], "Map Session", style="h2white")
    map_box = [mx, my + 56, mw, mh - 56]
    bx0, by0, bw0, bh0 = map_box
    for pts, fill in [(NA, "land"), (SA, "land"), (EU, "land"), (AF, "land"),
                      (AS, "land"), (AU, "land")]:
        s.polygon(_scale(pts, bx0, by0, bw0, bh0), fill=fill)
    s.polygon(_scale(US_DARK, bx0, by0, bw0, bh0), fill="ink")
    # zoom buttons
    s.ellipse([x + w - 56, my + 78], 24, 24, fill="card"); plus(s, x + w - 56, my + 78, "ink", 8)
    s.ellipse([x + w - 56, my + 132], 24, 24, fill="card"); minus(s, x + w - 56, my + 132, "ink", 8)
    # markers
    for px, py, num in [(0.205, 0.12, "2"), (0.175, 0.33, "7"), (0.30, 0.66, "3")]:
        cxm, cym = bx0 + px * bw0, by0 + py * bh0
        s.ellipse([cxm, cym], 14, 14, fill="yellow")
        s.text([cxm - 14, cym - 8, 28, 16], num, style="mapNum")
    # France flag pin (Europe)
    fpx, fpy = bx0 + 0.515 * bw0, by0 + 0.20 * bh0
    s.polygon([[fpx, fpy + 14], [fpx - 7, fpy], [fpx + 7, fpy]], fill="yellow")
    flag(s, fpx - 11, fpy - 18, "fr", 22, 14)

    # selected-device card (bottom)
    cardY = y + h - 168
    s.rect([x + 16, cardY, w - 32, 148], fill="card", radius=22, **SHADOW)
    s.rect([x + 32, cardY + 22, 52, 40], fill="#F0F0F2", radius=10)
    laptop_thumb(s, x + 58, cardY + 42)
    s.text([x + 100, cardY + 24, 180, 22], "MacBook Air", style="macAir")
    s.text([x + 100, cardY + 48, 160, 16], "Version M1", style="macVer")
    kebab(s, x + w - 44, cardY + 40, "g8")
    for k in range(28):
        s.ellipse([x + 32 + k * (w - 64) / 27, cardY + 84], 1.3, 1.3, fill="line", decorative=True)
    flag(s, x + 32, cardY + 104, "fr")
    s.text([x + 62, cardY + 106, 120, 18], "Paris, France", style="macLoc")
    s.text([x + w - 168, cardY + 106, 144, 18], "Sep 12, 13:00", style="macTime")


# --------------------------------------------------------------------------- #
# Phone 3 — Security status + Session History
# --------------------------------------------------------------------------- #
def screen_security(s, x, y, w, h):
    s.rect([x, y, w, h], fill=lg([x, y], [x, y + h], [(0, "#70757C"), (1, "#646970")]))
    topbar(s, x, y, w, mode="devices")
    s.text([x + 24, y + 70, 260, 52], "Devices", style="h1")

    # security status card
    s.rect([x + 24, y + 138, w - 48, 250], fill="cardLt", radius=28)
    s.text([x + 24, y + 162, w - 48, 36], "Security status", style="h2ink")
    cxg, cyg, R = x + w / 2, y + 360, 96
    yel = [[cxg + R * math.cos(math.radians(a)), cyg - R * math.sin(math.radians(a))]
           for a in [180 - i * (99 / 22) for i in range(23)]]
    drk = [[cxg + R * math.cos(math.radians(a)), cyg - R * math.sin(math.radians(a))]
           for a in [81 - i * (81 / 18) for i in range(19)]]
    s.polyline(yel, fill="none", stroke="yellow",
               stroke_style={"stroke_width": 34, "stroke_linecap": "round", "stroke_linejoin": "round"})
    s.polyline(drk, fill="none", stroke="ink",
               stroke_style={"stroke_width": 34, "stroke_linecap": "round", "stroke_linejoin": "round"})
    s.text([cxg - 70, y + 322, 140, 40], "55%", style="bigPct")
    s.text([cxg - 80, y + 366, 160, 18], "Medium Risk", style="risk")

    # session history card
    scY = y + 406
    scH = h - (scY - y) - 22
    s.rect([x + 24, scY, w - 48, scH], fill="cardDk", radius=28)
    s.text([x + 44, scY + 24, 214, 28], "Session History", style="h2white")
    s.text([x + w - 88, scY + 22, 64, 30], "2/8", style="count")

    rows = [
        ("harry", "laptop", "Harry Bender", "Jan 12, 13:00", "fr", "Paris"),
        ("katy", "tablet", "Katy Fuller", "Jan 12, 11:30", "us", "New York"),
        ("jonathan", "phone", "Jonathan Kelly", "Jan 11, 16:45", "ca", "Victoria"),
        ("billie", "phone", "Billie Wright", "Jan 11, 14:00", "fr", "Paris"),
        ("sarah", "laptop", "Sarah Page", "Jan 11, 10:30", "au", "Perth"),
        ("erica", "phone", "Erica Wyatt", "Jan 10, 15:40", "fr", "Paris"),
    ]
    r0 = scY + 78
    step = (scH - 96) / len(rows)
    for i, (key, dev, name, when, fcode, city) in enumerate(rows):
        ry = r0 + i * step
        s.ellipse([x + 48, ry], 17, 17, fill="#3A3F48")
        dev_glyph(s, x + 48, ry, dev, "mut")
        avatar(s, x + 92, ry, 19, **AV[key])
        s.text([x + 122, ry - 12, 150, 18], name, style="sessName")
        s.text([x + 122, ry + 8, 110, 16], when, style="sessTime")
        flag(s, x + w - 66, ry - 14, fcode, 22, 14)
        s.text([x + w - 120, ry + 6, 54, 16], city, style="city")


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="People · Devices · Security — mobile dashboard",
                          profile="diagram", lang="en")
    for name, value in COLORS.items():
        doc.define_color(name, value)
    for name, style in STYLES.items():
        doc.define_text_style(name, **style)

    page = doc.page("people_devices_dashboard",
                    canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute").layer("stage")
    page.rect([0, 0, W, H], fill=lg([0, 0], [W, H],
              [(0, "#A2A8B3"), (0.5, "#9AA1AD"), (1, "#8C93A0")]))

    phones = [
        (95, 235, screen_people),
        (570, 120, screen_devices),
        (1045, 185, screen_security),
    ]
    page.layer("phones")
    for px, py, draw in phones:
        # body + cast shadow
        page.rect([px - 4, py + 12, PW + 8, PH], fill=rgba("#3A3F47", 0.22), radius=PR + 4, decorative=True)
        page.rect([px, py, PW, PH], fill="body", radius=PR)
        col = Collector()
        draw(col, px, py, PW, PH)
        page.group(col.objs, clip=clip_path(rrect(px, py, PW, PH, PR)))
        # crisp body border on top
        page.rect([px, py, PW, PH], fill="none", stroke=rgba("#FFFFFF", 0.35),
                  stroke_style={"stroke_width": 1.2}, radius=PR)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "static", "examples", "fixtures", "people-devices-dashboard.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(report.issues) - len(errors)} -> {out}")
    for i in report.issues[:25]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
