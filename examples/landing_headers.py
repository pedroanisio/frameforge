#!/usr/bin/env python3
"""Landing-page hero headers — a cohesive SaaS illustration pack (FrameGraph SDK).

Operating model (see the craft-floor discussion): this brief is a *refined* request
(named palette, "cohesive design pack", "consistent design system", explicit
anti-generic guardrails), so it is built **primitives-first** — a hand-composed
design system + a reusable flat-vector illustration kit — with widgets used only,
and restyled, for incidental chrome. The kit (blobs, busts, devices, UI cards,
charts, plants, dots, nav, CTA) is the thing that makes nine headers read as one
pack; this file ships the kit + the first header ("Business Team") as a vertical
slice to set the bar before fanning out to the rest.

Wide desktop hero (1600x900); each header is a soft-shadowed white card mockup.
Run standalone or via the MCP::

    uv run python examples/landing_headers.py out/landing/landing-headers.fg.yaml

All copy is illustrative placeholder content.
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

from framegraph.sdk import DocumentBuilder, measure_text, serialize  # noqa: E402
from framegraph.sdk.paint import effects, linear_gradient, radial_gradient, rgba, soft_shadow  # noqa: E402

# --- design tokens ---------------------------------------------------------- #
VIOLET, PURPLE, INDIGO = "#7C5CFC", "#6D28D9", "#4F46E5"
BLUE, SKYBLUE, CYAN, TEAL = "#4F8DF0", "#60A5FA", "#22D3EE", "#2DD4BF"
PINK, MAGENTA = "#EC4899", "#F472B6"
INK, NAVINK = "#1E2030", "#2A2D3A"
GRAY, GRAY2 = "#8A90A6", "#B9BECD"
CARD, BACKDROP, LINE = "#FFFFFF", "#EEF0F7", "#E7E9F2"
SKIN = ["#F4C9A6", "#E8B48C", "#F7D2B5"]

DISPLAY = ["Poppins", "Montserrat", "Inter Display", "Inter", "Helvetica Neue", "Arial", "sans-serif"]
SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]

PURPLE_BLUE = linear_gradient([(VIOLET, 0), (BLUE, 100)], angle=135)
CYAN_BLUE = linear_gradient([(CYAN, 0), (SKYBLUE, 100)], angle=135)

W, H = 1600, 900
CARDBOX = [40, 40, 1520, 820]
PADX = 84


# --------------------------------------------------------------------------- #
#  text + primitives                                                           #
# --------------------------------------------------------------------------- #
def t(size, color, *, weight=400, family=None, spacing=None, lh=None, align="left",
      valign="top", wrap=True):
    st = {"font_family": family or SANS, "font_size": size, "font_weight": weight,
          "color": color, "align": align, "vertical_align": valign}
    if spacing is not None:
        st["letter_spacing"] = spacing
    if lh is not None:
        st["line_height"] = lh
    if not wrap:
        st["white_space"] = "nowrap"
    return st


def headline(L, x, y, lines, *, size=70, color=INK, lh=1.04):
    for i, line in enumerate(lines):
        L.add({"type": "text", "box": [x, y + i * size * lh, 640, int(size * 1.3)],
               "spans": [{"text": line}],
               "style": {"font_family": DISPLAY, "font_size": size, "font_weight": 800,
                         "line_height": 1.0, "color": color, "letter_spacing": -0.8}})


def _dot(L, cx, cy, r, fill, **f):
    L.add({"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": fill, **f})


def blob(L, cx, cy, r, fill, *, squish=0.92, rot=0.0, wobble=0.16, n=72, **f):
    """A soft organic blob (smooth closed path) filled with ``fill`` (a gradient ok)."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + wobble * (math.sin(3 * a + rot) * 0.6 + math.sin(2 * a + rot * 1.7) * 0.4))
        pts.append([cx + rr * math.cos(a), cy + rr * squish * math.sin(a)])
    L.polyline(pts, smooth=True, closed=True, fill=fill, **f)


# --------------------------------------------------------------------------- #
#  chrome — nav + CTA                                                          #
# --------------------------------------------------------------------------- #
def logo(L, x, y):
    L.rect([x, y, 34, 34], radius=11, fill=PURPLE_BLUE)
    _dot(L, x + 17, y + 17, 7, CARD)
    L.text([x + 46, y + 6, 240, 24], "YOUR LOGO",
           style=t(17, INK, weight=800, family=DISPLAY, spacing=0.4, wrap=False))


def nav(L, right_x, y, items, active=0):
    xs = []
    widths = []
    for it in items:
        widths.append(measure_text(it, font_family=DISPLAY, font_size=15, bold=False) + 4)
    gap = 38
    total = sum(widths) + gap * (len(items) - 1)
    x = right_x - total
    for i, it in enumerate(items):
        xs.append(x)
        L.text([x, y, widths[i] + 8, 22], it,
                style=t(15, INK if i == active else GRAY, weight=600 if i == active else 500,
                        family=DISPLAY, wrap=False))
        if i == active:
            L.rect([x, y + 26, widths[i] - 4, 3], radius=2, fill=PURPLE)
        x += widths[i] + gap


def cta(L, x, y, label="Get Started", w=190, h=58):
    L.rect([x, y, w, h], radius=h / 2, fill=PURPLE_BLUE,
           **effects(shadow=soft_shadow(dy=10, blur=22, color=PURPLE, opacity=0.34)))
    L.text([x, y, w, h], label, style=t(17, CARD, weight=700, family=DISPLAY,
            align="center", valign="middle", wrap=False))


# --------------------------------------------------------------------------- #
#  illustration kit                                                            #
# --------------------------------------------------------------------------- #
def bust(L, cx, top_y, s, *, shirt, hair="#2E2750", skin=SKIN[0]):
    """A flat head-and-shoulders figure (reads behind a desk/device)."""
    hr = 26 * s
    # soft rim so the figure lifts off the blob instead of blending into it
    L.add({"type": "ellipse", "center": [cx, top_y + 34 * s], "rx": 64 * s, "ry": 80 * s,
           "fill": rgba("#FFFFFF", 0.11), "decorative": True})
    # shoulders (square bottom is hidden behind the device in front)
    L.rect([cx - 52 * s, top_y + 20 * s, 104 * s, 120 * s], radius=40 * s, fill=shirt)
    L.add({"type": "ellipse", "center": [cx, top_y + 26 * s], "rx": 24 * s, "ry": 13 * s,
           "fill": rgba("#FFFFFF", 0.14), "decorative": True})               # collar light
    L.add({"type": "polyline", "points": [[cx - 10 * s, top_y + 22 * s], [cx, top_y + 40 * s],
           [cx + 10 * s, top_y + 22 * s]], "closed": True, "fill": rgba(NAVINK, 0.16)})  # collar V
    L.rect([cx - 11 * s, top_y + 8 * s, 22 * s, 26 * s], fill=skin)         # neck
    _dot(L, cx, top_y - 4 * s, hr + 5 * s, hair)                            # hair cap
    _dot(L, cx, top_y, hr, skin)                                            # head
    _dot(L, cx - 9 * s, top_y - 1 * s, 2.6 * s, NAVINK)                     # eyes
    _dot(L, cx + 9 * s, top_y - 1 * s, 2.6 * s, NAVINK)
    L.arc([cx, top_y + 6 * s], 7 * s, 25, 155, stroke=NAVINK,
          stroke_style={"stroke_width": 2.2 * s, "stroke_linecap": "round"})


def laptop(L, cx, base_y, w):
    sh = w * 0.62
    sx, sy = cx - w / 2, base_y - sh
    # keyboard deck — a trapezoid (wider at the front) reads as 3/4 depth
    L.polygon([[sx + 4, base_y - 2], [sx + w - 4, base_y - 2],
               [cx + w * 0.62, base_y + 20], [cx - w * 0.62, base_y + 20]], fill="#D7DCEC")
    L.polygon([[cx - w * 0.62, base_y + 20], [cx + w * 0.62, base_y + 20],
               [cx + w * 0.60, base_y + 27], [cx - w * 0.60, base_y + 27]], fill="#BFC6DC")
    L.rect([cx - 48, base_y + 4, 96, 10], radius=5, fill="#C6CCE0")          # trackpad/keys hint
    # lid + screen + a richer dashboard UI
    L.rect([sx, sy, w, sh], radius=14, fill=NAVINK)
    L.rect([sx + 11, sy + 11, w - 22, sh - 22], radius=8, fill="#F4F6FC")
    L.rect([sx + 24, sy + 24, w - 48, 14], radius=7, fill=PURPLE_BLUE)       # top bar
    L.rect([sx + 24, sy + 48, (w - 48) * 0.30, sh - 84], radius=6, fill="#E9ECF7")  # sidebar
    for i in range(3):
        L.rect([sx + 33, sy + 62 + i * 15, (w - 48) * 0.18, 6], radius=3, fill="#CDD4E8")
    bx, by = sx + 24 + (w - 48) * 0.40, sy + sh - 28
    for i, hh in enumerate((16, 28, 20, 34, 24)):
        L.rect([bx + i * 16, by - hh, 10, hh], radius=3, fill=(CYAN if i % 2 else VIOLET))
    L.polygon([[sx + 11, sy + 11], [sx + 58, sy + 11], [sx + 24, sy + sh - 11], [sx + 11, sy + sh - 11]],
              fill=rgba("#FFFFFF", 0.08))                                  # glass sheen


def ui_card(L, x, y, w, h, *, accent=VIOLET, kind="lines"):
    L.rect([x, y, w, h], radius=16, fill=CARD,
           **effects(shadow=soft_shadow(dy=12, blur=26, color=INDIGO, opacity=0.16)))
    if kind == "chart":
        _dot(L, x + 22, y + 22, 9, accent)
        L.rect([x + 38, y + 17, w - 60, 8], radius=4, fill="#E4E7F1")
        bx, by = x + 18, y + h - 20
        for i, hh in enumerate((16, 28, 20, 34, 24)):
            L.rect([bx + i * ((w - 36) / 5), by - hh, (w - 36) / 5 - 6, hh], radius=3,
                   fill=accent if i % 2 == 0 else CYAN)
    elif kind == "avatar":
        _dot(L, x + 26, y + h / 2, 16, accent)
        L.rect([x + 50, y + h / 2 - 12, w - 70, 8], radius=4, fill="#E4E7F1")
        L.rect([x + 50, y + h / 2 + 2, (w - 70) * 0.7, 7], radius=3, fill="#EDEFF6")
    else:
        for i in range(3):
            L.rect([x + 18, y + 20 + i * 16, (w - 36) * (1 - i * 0.18), 8], radius=4,
                   fill=accent if i == 0 else "#E4E7F1")


def chat_bubble(L, x, y, w, h, *, fill=CARD, dotcol=VIOLET, tail="left"):
    L.rect([x, y, w, h], radius=16, fill=fill,
           **effects(shadow=soft_shadow(dy=8, blur=18, color=INDIGO, opacity=0.14)))
    ty = y + h
    if tail == "left":
        L.polygon([[x + 22, ty - 2], [x + 22, ty + 16], [x + 44, ty - 2]], fill=fill)
    for i in range(3):
        _dot(L, x + 22 + i * 18, y + h / 2, 5, dotcol if i == 0 else rgba(dotcol, 0.4))


def plant(L, cx, base_y, s=1.0):
    L.add({"type": "polyline", "points": [[cx - 18 * s, base_y], [cx + 18 * s, base_y],
           [cx + 13 * s, base_y + 34 * s], [cx - 13 * s, base_y + 34 * s]], "closed": True,
           "fill": "#E6873C"})
    for ang, ln, col in ((-32, 60, TEAL), (0, 74, CYAN), (30, 58, "#34D399")):
        tipx = cx + ln * s * math.sin(math.radians(ang))
        tipy = base_y - ln * s * math.cos(math.radians(ang))
        L.polyline([[cx, base_y], [tipx - 9 * s, (base_y + tipy) / 2], [tipx, tipy],
                    [tipx + 9 * s, (base_y + tipy) / 2]], smooth=True, closed=True, fill=col)


def sparkles(L, pts):
    for cx, cy, r, col in pts:
        _dot(L, cx, cy, r, col)


def cross(L, cx, cy, s, col):
    L.line([cx - s, cy], [cx + s, cy], stroke=col, stroke_style={"stroke_width": 3, "stroke_linecap": "round"})
    L.line([cx, cy - s], [cx, cy + s], stroke=col, stroke_style={"stroke_width": 3, "stroke_linecap": "round"})


def ring(L, cx, cy, r, col, w=3):
    L.add({"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": "none",
           "stroke": col, "stroke_style": {"stroke_width": w}})


def dot_grid(L, x, y, cols, rows, gap, r, col):
    for i in range(cols):
        for j in range(rows):
            _dot(L, x + i * gap, y + j * gap, r, col)


PURPLE_MAGENTA = linear_gradient([("#7C3AED", 0), ("#A21CAF", 60), ("#C026D3", 100)], angle=140)


# --- richer illustration: posable full-body figures + theme props ----------- #
def capsule(L, p0, p1, w, col):
    L.line(p0, p1, stroke=col, stroke_style={"stroke_width": w, "stroke_linecap": "round"})


def limb_fill(L, p0, p1, r0, r1, col):
    """A filled, tapered limb (a trapezoid + rounded ends) — gives volume, so the
    body reads as a clothed silhouette instead of a uniform-width stick."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy) or 1.0
    px, py = -dy / d, dx / d
    L.polygon([[p0[0] + px * r0, p0[1] + py * r0], [p1[0] + px * r1, p1[1] + py * r1],
               [p1[0] - px * r1, p1[1] - py * r1], [p0[0] - px * r0, p0[1] - py * r0]], fill=col)
    _dot(L, p0[0], p0[1], r0, col)
    _dot(L, p1[0], p1[1], r1, col)


def shoe(L, foot, knee, col, ln=20):
    ang = math.atan2(foot[1] - knee[1], foot[0] - knee[0]) + math.pi / 2
    toe = [foot[0] + ln * math.cos(ang), foot[1] + ln * math.sin(ang)]
    L.polyline([[foot[0], foot[1] - 9], [toe[0], toe[1] - 5], [toe[0], toe[1] + 4],
                [foot[0], foot[1] + 9]], smooth=True, closed=True, fill=col)
    _dot(L, foot[0], foot[1], 9, col)


def person_posed(L, *, head, neck, hip, arms, legs, skin, shirt, pants, hair,
                 headr=24, shoecol="#1B1636", back_arm=None, sw=27, ww=16, build=1.0):
    """A full-body flat figure from FILLED silhouette shapes (shaped torso +
    tapered limbs), layered back-to-front — not capsule sticks."""
    a = build
    if back_arm:
        s, e, h = back_arm
        limb_fill(L, s, e, 13 * a, 10 * a, _shade(shirt)); limb_fill(L, e, h, 10 * a, 7 * a, _shade(shirt))
        _dot(L, h[0], h[1], 8 * a, _shade(skin))
    for hp, knee, foot in legs:
        shoe(L, foot, knee, shoecol)
        limb_fill(L, hp, knee, 17 * a, 13 * a, pants); limb_fill(L, knee, foot, 13 * a, 9 * a, pants)
    # torso silhouette: wide rounded shoulders tapering to the waist
    L.polyline([[neck[0] - sw, neck[1] + 6], [neck[0] + sw, neck[1] + 6],
                [hip[0] + ww, hip[1]], [hip[0] - ww, hip[1]]], smooth=True, closed=True, fill=shirt)
    _dot(L, neck[0] - sw + 4, neck[1] + 9, 13 * a, shirt)
    _dot(L, neck[0] + sw - 4, neck[1] + 9, 13 * a, shirt)
    for s, e, h in arms:
        limb_fill(L, s, e, 13 * a, 10 * a, shirt); limb_fill(L, e, h, 10 * a, 7 * a, shirt)
        _dot(L, h[0], h[1], 8 * a, skin)
    L.rect([neck[0] - 7, neck[1] - 7, 14, 17], fill=skin)
    _dot(L, head[0], head[1] - headr * 0.2, headr + 4, hair)
    _dot(L, head[0], head[1], headr, skin)


def _shade(hexv, k=0.82):
    h = hexv.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % (int(r * k), int(g * k), int(b * k))


def rocket(L, cx, base_y, h, *, body="#F5F3FF", accent=PURPLE, accent2=MAGENTA, win=CYAN):
    w = h * 0.34
    top = base_y - h
    # exhaust (behind body)
    L.polygon([[cx - w * 0.26, base_y - h * 0.04], [cx + w * 0.26, base_y - h * 0.04],
               [cx, base_y + h * 0.24]], fill="#FBBF24")
    L.polygon([[cx - w * 0.13, base_y - h * 0.04], [cx + w * 0.13, base_y - h * 0.04],
               [cx, base_y + h * 0.14]], fill="#FB7185")
    # fins
    L.polygon([[cx - w / 2, top + h * 0.64], [cx - w / 2 - w * 0.4, base_y],
               [cx - w / 2 + w * 0.04, base_y]], fill=accent2)
    L.polygon([[cx + w / 2, top + h * 0.64], [cx + w / 2 + w * 0.4, base_y],
               [cx + w / 2 - w * 0.04, base_y]], fill=accent2)
    # body + nose
    L.rect([cx - w / 2, top + h * 0.2, w, h * 0.64], radius=w * 0.5, fill=body)
    L.polygon([[cx, top], [cx - w / 2 + 2, top + h * 0.27], [cx + w / 2 - 2, top + h * 0.27]], fill=accent)
    # window + band
    L.add({"type": "ellipse", "center": [cx, top + h * 0.42], "rx": w * 0.2, "ry": w * 0.2,
           "fill": win, "stroke": accent, "stroke_style": {"stroke_width": 5}})
    _dot(L, cx - w * 0.06, top + h * 0.38, w * 0.06, rgba("#FFFFFF", 0.7))
    L.rect([cx - w / 2, top + h * 0.6, w, h * 0.05], fill=accent)


def gear(L, cx, cy, r, col, teeth=9):
    pts = []
    for i in range(teeth * 2):
        rr = r if i % 2 == 0 else r * 0.74
        a = math.pi * i / teeth
        pts.append([cx + rr * math.cos(a), cy + rr * math.sin(a)])
    L.polygon(pts, fill=col)
    _dot(L, cx, cy, r * 0.34, CARD)


def ladder(L, x, y, w, h, col="#B9A7F0"):
    capsule(L, [x, y], [x + w * 0.34, y + h], 7, col)
    capsule(L, [x + w, y], [x + w + w * 0.34, y + h], 7, col)
    for i in range(1, 4):
        ry = y + h * i / 4
        rx = x + w * 0.34 * (i / 4)
        capsule(L, [rx, ry], [rx + w, ry], 6, col)


# --------------------------------------------------------------------------- #
#  page scaffold (the soft-shadowed white hero card)                           #
# --------------------------------------------------------------------------- #
def hero_card(doc, pid):
    p = doc.page(pid, canvas={"size": [W, H]}, coordinate_mode="absolute")
    L = p.layer("main")
    L.rect([0, 0, W, H], fill=BACKDROP, decorative=True)
    cx, cy, cw, ch = CARDBOX
    L.rect([cx, cy, cw, ch], radius=30, fill=CARD,
           **effects(shadow=soft_shadow(dy=34, blur=70, color="#3A2E70", opacity=0.16)))
    return L


def header_chrome(L, active=0):
    cx, cy, cw, ch = CARDBOX
    logo(L, cx + PADX, cy + 56)
    nav(L, cx + cw - PADX, cy + 60, ["Home", "About us", "Portfolio", "Info", "Contact us"], active=active)
    L.rect([cx + PADX, cy + 116, cw - 2 * PADX, 1], fill=LINE, decorative=True)


def hero_text(L, lines, paragraph, *, top=322):
    cx, cy = CARDBOX[0], CARDBOX[1]
    x = cx + PADX
    headline(L, x, cy + top, lines)
    L.text([x, cy + top + len(lines) * 73 + 26, 520, 110], paragraph,
           style=t(18, GRAY, lh=1.7))
    cta(L, x, cy + top + len(lines) * 73 + 26 + 130, "Get Started")


# --------------------------------------------------------------------------- #
#  HEADER 1 — Business Team                                                    #
# --------------------------------------------------------------------------- #
def h_business_team(doc):
    L = hero_card(doc, "business-team")
    header_chrome(L, active=0)
    # --- illustration (right) ---
    bcx, bcy = 1150, 470
    L.add({"type": "ellipse", "center": [bcx, bcy + 210], "rx": 280, "ry": 32,
           "fill": rgba(INDIGO, 0.10), "decorative": True})                 # scene ground shadow
    blob(L, bcx + 30, bcy + 30, 250, radial_gradient([(rgba(CYAN, 0.55), 0), (rgba(SKYBLUE, 0.0), 100)]),
         squish=1.0, wobble=0.12)
    blob(L, bcx, bcy, 270, PURPLE_BLUE, squish=0.96, rot=0.6)
    L.add({"type": "ellipse", "center": [bcx - 96, bcy - 104], "rx": 118, "ry": 86,
           "fill": rgba("#FFFFFF", 0.10), "decorative": True})              # blob top-light
    # team behind the laptop
    bust(L, bcx, bcy - 150, 1.05, shirt="#5B21B6", hair="#241F45", skin=SKIN[0])
    bust(L, bcx - 120, bcy - 96, 0.95, shirt="#6655E8", hair="#2A2118", skin=SKIN[1])
    bust(L, bcx + 122, bcy - 100, 0.95, shirt=INDIGO, hair="#1F1B3A", skin=SKIN[2])
    laptop(L, bcx, bcy + 92, 280)
    # floating UI around the scene
    ui_card(L, bcx - 300, bcy - 150, 150, 96, accent=VIOLET, kind="chart")
    _dot(L, bcx - 300 + 150, bcy - 150, 11, PINK)                          # notification badge
    L.text([bcx - 300 + 144, bcy - 158, 14, 14], "3",
           style=t(10, CARD, weight=700, family=DISPLAY, align="center", valign="middle", wrap=False))
    chat_bubble(L, bcx + 165, bcy - 165, 120, 70, dotcol=PINK)
    ui_card(L, bcx + 150, bcy + 70, 165, 64, accent=CYAN, kind="avatar")
    _dot(L, bcx + 150 + 165 - 24, bcy + 70 + 32, 13, VIOLET)               # add-member control
    cross(L, bcx + 150 + 165 - 24, bcy + 70 + 32, 5, CARD)
    plant(L, bcx - 235, bcy + 150, 1.1)
    ring(L, bcx + 262, bcy - 214, 15, VIOLET, 3)
    ring(L, bcx - 286, bcy - 66, 11, CYAN, 3)
    dot_grid(L, bcx - 332, bcy + 96, 3, 3, 13, 3, rgba(VIOLET, 0.55))
    sparkles(L, [(bcx + 250, bcy + 36, 7, CYAN), (bcx + 70, bcy - 258, 6, MAGENTA),
                 (bcx - 112, bcy + 206, 5, VIOLET), (bcx + 304, bcy - 96, 5, PINK),
                 (bcx - 250, bcy - 150, 4, PINK)])
    cross(L, bcx + 232, bcy - 198, 9, VIOLET)
    cross(L, bcx - 300, bcy + 44, 8, CYAN)
    # --- hero copy (left) ---
    hero_text(L, ["Our business", "team"],
              "A friendly crew that ships. Plan, build, and launch your product with "
              "people who sweat the details as much as you do.")
    return L


# --------------------------------------------------------------------------- #
#  HEADER 2 — Boost your business (rocket) — built at the original's ambition  #
# --------------------------------------------------------------------------- #
def h_boost_business(doc):
    L = hero_card(doc, "boost-business")
    header_chrome(L, active=1)
    bcx, bcy = 1150, 470
    L.add({"type": "ellipse", "center": [bcx, bcy + 214], "rx": 268, "ry": 30,
           "fill": rgba(INDIGO, 0.10), "decorative": True})
    blob(L, bcx - 8, bcy, 266, PURPLE_MAGENTA, squish=1.0, rot=0.3)
    L.add({"type": "ellipse", "center": [bcx - 92, bcy - 108], "rx": 118, "ry": 88,
           "fill": rgba("#FFFFFF", 0.10), "decorative": True})
    ladder(L, 1276, 472, 64, 150)
    rocket(L, bcx, bcy + 135, 300)
    # left figure — holding a laptop, gesturing up at the rocket
    person_posed(L, head=[978, 486], neck=[978, 510], hip=[978, 576],
                 arms=[([968, 520], [958, 556], [998, 560])],
                 back_arm=([990, 516], [1016, 496], [1042, 476]),
                 legs=[([970, 576], [964, 604], [960, 628]), ([988, 576], [995, 604], [1000, 628])],
                 skin=SKIN[0], shirt=INDIGO, pants="#2A2348", hair="#241F45")
    L.rect([980, 548, 46, 30], radius=4, fill=NAVINK)
    L.rect([984, 552, 38, 22], radius=2, fill="#EAEBFB")
    # right figure — on the ladder, reaching to the rocket
    person_posed(L, head=[1322, 440], neck=[1322, 464], hip=[1322, 524],
                 arms=[([1308, 472], [1282, 446], [1238, 414]), ([1336, 472], [1312, 438], [1258, 400])],
                 legs=[([1314, 524], [1310, 560], [1306, 596]), ([1330, 524], [1336, 560], [1342, 596])],
                 skin=SKIN[2], shirt=PURPLE, pants="#2A2348", hair="#1F1B3A")
    gear(L, 948, 596, 27, "#8B5CF6")
    gear(L, 986, 620, 16, "#6655E8")
    ui_card(L, bcx + 152, bcy - 156, 150, 90, accent=VIOLET, kind="chart")
    ring(L, bcx + 252, bcy - 200, 14, MAGENTA, 3)
    dot_grid(L, bcx - 324, bcy + 92, 3, 3, 13, 3, rgba(VIOLET, 0.5))
    sparkles(L, [(bcx + 248, bcy + 44, 7, CYAN), (bcx + 64, bcy - 250, 6, MAGENTA),
                 (bcx - 252, bcy - 150, 5, PINK), (bcx + 300, bcy - 88, 5, VIOLET)])
    cross(L, bcx - 300, bcy + 44, 8, CYAN)
    hero_text(L, ["Boost your", "business"],
              "Launch faster with the tools your team needs to plan, ship and grow — "
              "all wired together and ready before liftoff.")
    return L


def build_document():
    doc = DocumentBuilder(title="Landing Page Headers — SaaS pack", profile="deck", lang="en")
    h_boost_business(doc)
    h_business_team(doc)
    return doc


doc = build_document()


def main() -> int:
    from framegraph.sdk.validate import validate_static_rules
    built = doc.build()
    rep = validate_static_rules(built)
    errs = [i for i in rep.issues if i.severity == "error"]
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "landing", "landing-headers.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(built, format="yaml"))
    print(f"landing-headers: {len(built.pages)} page(s), ok={rep.ok}, errors={len(errs)} -> {out}")
    for i in errs[:20]:
        print("  ERROR:", i.code, i.message)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
