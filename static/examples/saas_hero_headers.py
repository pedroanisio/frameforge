"""SaaS landing-page hero headers — built from PRIMITIVES only (no widgets).

Nine cohesive, modern SaaS hero sections. Everything is drawn with rect / text /
line / ellipse / circle / polygon / path / arc / sector primitives + gradient
paint, so the look is bespoke rather than the stock widget set.
"""
from __future__ import annotations

import math

from frameforge.sdk import DocumentBuilder, linear_gradient, radial_gradient, rgba

# ---- palette --------------------------------------------------------------- #
INK = "#1E2440"
SUB = "#8A93A8"
PAPER = "#FFFFFF"
BG = "#F4F5FB"
VIOLET = "#7C3AED"
PURPLE = "#8B5CF6"
INDIGO = "#5B6CF6"
BLUE = "#3B82F6"
SOFTBLUE = "#60A5FA"
CYAN = "#22D3EE"
TEAL = "#2DD4BF"
PINK = "#EC4899"
PINKS = "#F472B6"
YELLOW = "#FBBF24"
FONT = ("Poppins", "Montserrat", "Inter", "Helvetica", "Arial", "sans-serif")

W, H = 1280, 720
CM = 26                      # card margin
CARD = [CM, CM, W - 2 * CM, H - 2 * CM]
PAD = 70


def txt(size, *, color=INK, weight=400, align="left", valign="top", overflow="clip",
        wrap=False, **extra):
    st = {"font_family": list(FONT), "font_size": size, "font_weight": weight,
          "color": color, "align": align, "vertical_align": valign, "overflow": overflow}
    if not wrap:
        st["white_space"] = "nowrap"
    st.update(extra)
    return st


def soft(dy=22, blur=50, color="#5B3FA8", opacity=0.12):
    return {"dx": 0, "dy": dy, "blur": blur, "color": color, "opacity": opacity}


# ---- generic primitive helpers -------------------------------------------- #
def rrect(L, box, fill, *, radius=16, shadow=None, opacity=None, stroke=None, sw=None):
    obj = {"type": "rect", "box": list(box), "fill": fill, "radius": radius}
    if shadow:
        obj["shadow"] = shadow
    if opacity is not None:
        obj["opacity"] = opacity
    if stroke:
        obj["stroke"] = stroke
        obj["stroke_style"] = {"stroke_width": sw or 1.5}
    L.add(obj)


def circle(L, cx, cy, r, fill, *, opacity=None, stroke=None, sw=None, shadow=None):
    obj = {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": fill}
    if opacity is not None:
        obj["opacity"] = opacity
    if stroke:
        obj["stroke"] = stroke
        obj["stroke_style"] = {"stroke_width": sw or 2}
    if shadow:
        obj["shadow"] = shadow
    L.add(obj)


def blob(L, cx, cy, rx, ry, stops, *, radial=True, angle=120, opacity=1.0, rotate=0.0):
    fill = radial_gradient(stops) if radial else linear_gradient(stops, angle=angle)
    obj = {"type": "ellipse", "center": [cx, cy], "rx": rx, "ry": ry, "fill": fill}
    if opacity < 1.0:
        obj["opacity"] = opacity
    if rotate:
        obj["rotation"] = rotate
    L.add(obj)


_BLOB_SEED = [0]


def _blob_path(cx, cy, rx, ry, *, seed, amp=0.12, n=9):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        wob = 1 + amp * math.sin(seed + i * 1.9) + amp * 0.55 * math.cos(seed * 1.7 + i * 2.6)
        pts.append((cx + rx * wob * math.cos(a), cy + ry * wob * math.sin(a)))

    def mid(p, q):
        return ((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)

    m0 = mid(pts[-1], pts[0])
    d = f"M {m0[0]:.1f} {m0[1]:.1f} "
    for i in range(n):
        nm = mid(pts[i], pts[(i + 1) % n])
        d += f"Q {pts[i][0]:.1f} {pts[i][1]:.1f} {nm[0]:.1f} {nm[1]:.1f} "
    return d + "Z"


def organic_blob(L, cx, cy, rx, ry, stops, *, radial=True, angle=120, opacity=1.0, rotate=0.0):
    """A soft, abstract organic blob (smooth closed path) instead of a flat circle."""
    _BLOB_SEED[0] += 1
    seed = _BLOB_SEED[0] * 1.3
    fill = radial_gradient(stops) if radial else linear_gradient(stops, angle=angle)
    # faint halo lobe behind, offset up-left, for depth
    L.add({"type": "path", "d": _blob_path(cx - rx * 0.10, cy - ry * 0.12, rx * 1.12, ry * 1.12,
           seed=seed + 4.0, amp=0.16), "fill": fill, "opacity": 0.16})
    obj = {"type": "path", "d": _blob_path(cx, cy, rx, ry, seed=seed), "fill": fill}
    if opacity < 1.0:
        obj["opacity"] = opacity
    if rotate:
        obj["rotation"] = rotate
    L.add(obj)


def dots(L, x, y, cols, rows, gap, r, color, *, opacity=0.5):
    for i in range(cols):
        for j in range(rows):
            circle(L, x + i * gap, y + j * gap, r, color, opacity=opacity)


def line(L, a, b, color, w=2.0, *, cap="round"):
    L.add({"type": "line", "from": list(a), "to": list(b), "stroke": color,
           "stroke_style": {"stroke_width": w, "stroke_linecap": cap}})


def star4(L, cx, cy, r, color):
    pts = []
    for i in range(8):
        ang = -math.pi / 2 + i * math.pi / 4
        rad = r if i % 2 == 0 else r * 0.34
        pts.append([cx + rad * math.cos(ang), cy + rad * math.sin(ang)])
    L.polygon(pts, fill=color)


# ---- shared landing scaffold ---------------------------------------------- #
def card_bg(L):
    L.rect([0, 0, W, H], fill=BG, decorative=True)
    rrect(L, CARD, PAPER, radius=28, shadow=soft(dy=26, blur=70, opacity=0.14))


def nav(L, active=0):
    cx = CM + PAD
    cy = CM + 52
    # logo mark + wordmark
    rrect(L, [cx, cy - 15, 30, 30],
          linear_gradient([(VIOLET, 0), (CYAN, 100)], angle=45), radius=10)
    circle(L, cx + 15, cy, 5.5, "#FFFFFF", opacity=0.9)
    L.text([cx + 42, cy - 11, 220, 22], "YOUR LOGO",
           style=txt(18, color=INK, weight=800, valign="middle", letter_spacing=0.5))
    items = ["Home", "About us", "Portfolio", "Info", "Contact us"]
    widths = [len(s) * 8.6 + 8 for s in items]
    gap = 30
    total = sum(widths) + gap * (len(items) - 1)
    rx = CM + CARD[2] - PAD - total
    x = rx
    for i, s in enumerate(items):
        wmt = widths[i]
        active_i = i == active
        L.text([x, cy - 9, wmt + 10, 20], s,
               style=txt(14.5, color=INK if active_i else SUB,
                         weight=700 if active_i else 500, valign="middle"))
        if active_i:
            rrect(L, [x, cy + 16, wmt, 3], VIOLET, radius=2)
        x += wmt + gap


def button(L, x, y, label="Get Started", w=196, h=58):
    rrect(L, [x, y, w, h], linear_gradient([(VIOLET, 0), (INDIGO, 100)], angle=90),
          radius=h / 2, shadow={"dx": 0, "dy": 12, "blur": 26, "color": VIOLET, "opacity": 0.42})
    L.text([x + 24, y, w - 60, h], label,
           style=txt(17, color="#FFFFFF", weight=700, valign="middle"))
    circle(L, x + w - 30, y + h / 2, 13, rgba("#FFFFFF", 0.18))
    L.text([x + w - 43, y, 26, h], "→",
           style=txt(17, color="#FFFFFF", weight=800, align="center", valign="middle"))


def hero_text(L, lines, body, *, top=210, accent=VIOLET):
    x = CM + PAD
    # eyebrow chip
    rrect(L, [x, top - 46, 150, 30], rgba(accent, 0.12), radius=15)
    circle(L, x + 18, top - 31, 4, accent)
    L.text([x + 30, top - 45, 120, 26], "WELCOME",
           style=txt(11.5, color=accent, weight=800, valign="middle", letter_spacing=1.5))
    y = top
    for ln in lines:
        L.text([x, y, 560, 70], ln, style=txt(58, color=INK, weight=800,
               letter_spacing=-1.2))
        y += 64
    L.text([x, y + 14, 470, 110], body,
           style=txt(15.5, color=SUB, weight=400, wrap=True, line_height=1.7))
    button(L, x, y + 132)
    # tiny social proof row
    for i in range(4):
        circle(L, x + 250 + i * 26, y + 132 + 29, 17, "#FFFFFF", shadow=soft(6, 12, opacity=0.18))
        circle(L, x + 250 + i * 26, y + 132 + 29, 15,
               [PURPLE, CYAN, PINKS, TEAL][i])
    L.text([x + 250 + 4 * 26 + 6, y + 132, 150, 58], "5k+ users",
           style=txt(13, color=SUB, weight=600, valign="middle"))


def confetti(L, cx, cy, accent):
    """A light scatter of abstract decorative dots + tiny rings around a hero."""
    spots = [(-300, -120, 4, PINKS), (-286, 96, 5, CYAN), (330, -96, 4, YELLOW),
             (322, 150, 5, PINK), (-250, 210, 3, VIOLET), (300, 220, 3, CYAN),
             (-150, -185, 3, accent), (150, -185, 3, PINKS)]
    for dx, dy, r, c in spots:
        circle(L, cx + dx, cy + dy, r, c, opacity=0.75)
    ring(L, cx - 300, cy + 24, 9, rgba(accent, 0.55), sw=3)
    ring(L, cx + 332, cy + 36, 7, rgba(CYAN, 0.55), sw=3)


# ---- people + object primitives ------------------------------------------- #
def person(L, x, y, s=1.0, *, shirt=VIOLET, skin="#F4C7A6", hair="#2E1A55",
           arm=None, smile=True):
    arm = arm or shirt
    # legs/seat hint
    rrect(L, [x - 17 * s, y + 44 * s, 34 * s, 26 * s], shirt, radius=10 * s)
    # torso
    rrect(L, [x - 18 * s, y + 12 * s, 36 * s, 40 * s], shirt, radius=14 * s)
    # arms
    rrect(L, [x - 26 * s, y + 16 * s, 12 * s, 30 * s], arm, radius=6 * s)
    rrect(L, [x + 14 * s, y + 16 * s, 12 * s, 30 * s], arm, radius=6 * s)
    # neck + head
    rrect(L, [x - 4 * s, y + 4 * s, 8 * s, 12 * s], skin, radius=4 * s)
    circle(L, x, y - 8 * s, 13 * s, skin)
    # hair cap
    L.add({"type": "path",
           "d": f"M {x-13*s} {y-8*s} A {13*s} {13*s} 0 0 1 {x+13*s} {y-8*s} L {x+13*s} {y-12*s} "
                f"A {13*s} {13*s} 0 0 0 {x-13*s} {y-12*s} Z", "fill": hair})
    circle(L, x - 13 * s, y - 8 * s, 4 * s, hair)
    circle(L, x + 13 * s, y - 8 * s, 4 * s, hair)
    # face
    circle(L, x - 4.5 * s, y - 9 * s, 1.6 * s, INK)
    circle(L, x + 4.5 * s, y - 9 * s, 1.6 * s, INK)
    if smile:
        L.add({"type": "path", "d": f"M {x-4*s} {y-3*s} Q {x} {y+1*s} {x+4*s} {y-3*s}",
               "fill": "none", "stroke": "#B5705A", "stroke_style": {"stroke_width": 1.6 * s,
               "stroke_linecap": "round"}})


def mini_card(L, x, y, w, h, *, fill="#FFFFFF", accent=VIOLET, lines=2, radius=14):
    rrect(L, [x, y, w, h], fill, radius=radius, shadow=soft(10, 22, opacity=0.16))
    circle(L, x + 18, y + 18, 9, accent)
    for i in range(lines):
        rrect(L, [x + 34, y + 12 + i * 12, w - 50 - (i * 14), 5], rgba(SUB, 0.5), radius=2.5)


def bars(L, x, y, w, h, vals, *, color=VIOLET, gap=8):
    n = len(vals)
    bw = (w - gap * (n - 1)) / n
    for i, v in enumerate(vals):
        bh = h * v
        rrect(L, [x + i * (bw + gap), y + h - bh, bw, bh],
              linear_gradient([(color, 0), (rgba(color, 0.55), 100)], angle=90),
              radius=bw / 2.4)


def plant(L, x, y, s=1.0):
    rrect(L, [x - 10 * s, y, 20 * s, 24 * s], linear_gradient([(TEAL, 0), (CYAN, 100)], angle=90),
          radius=6 * s)
    for dx, rot, c in ((-8, -34, "#34D399"), (0, 0, "#10B981"), (8, 34, "#34D399")):
        L.add({"type": "ellipse", "center": [x + dx * s, y - 20 * s], "rx": 8 * s, "ry": 22 * s,
               "fill": c, "rotation": rot})


# =========================================================================== #
def build_document():
    doc = DocumentBuilder(title="SaaS Landing Hero Headers", profile="deck")

    def page(pid, active, lines, body, accent, illo):
        p = doc.page(pid, canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
        L = p.layer("main")
        card_bg(L)
        nav(L, active=active)
        hero_text(L, lines, body, accent=accent)
        illo(L)
        confetti(L, rx, ry, accent)
        return L

    rx = CM + CARD[2] - 360       # illustration centre x (right column)
    ry = 380                       # illustration centre y

    # 1 — Business Team -----------------------------------------------------#
    def illo_team(L):
        organic_blob(L, rx, ry, 290, 270, [(rgba(PURPLE, 0.9), 0), (rgba(INDIGO, 0.85), 100)])
        ground_shadow(L, rx, ry + 150, 300)
        blob(L, rx + 120, ry - 150, 70, 70, [(CYAN, 0), (BLUE, 100)], opacity=0.9)
        dots(L, rx - 250, ry + 150, 4, 3, 16, 3, PINKS, opacity=0.6)
        # desk
        rrect(L, [rx - 150, ry + 70, 300, 26], "#FFFFFF", radius=10, shadow=soft(12, 26, opacity=0.18))
        # laptop
        rrect(L, [rx - 34, ry + 20, 68, 46], INK, radius=6)
        rrect(L, [rx - 30, ry + 24, 60, 38], CYAN, radius=4)
        rrect(L, [rx - 44, ry + 64, 88, 8], "#D6DAEA", radius=4)
        person(L, rx - 95, ry - 12, 1.05, shirt=VIOLET, hair="#3A2466")
        person(L, rx + 95, ry - 12, 1.05, shirt=BLUE, hair="#22304F", skin="#E8B48C")
        person(L, rx, ry - 42, 1.15, shirt=PINK, hair="#2E1A55")
        # chat bubbles
        rrect(L, [rx - 200, ry - 120, 86, 44], "#FFFFFF", radius=14, shadow=soft(10, 22, opacity=0.16))
        for i in range(3):
            circle(L, rx - 185 + i * 22, ry - 98, 5, [VIOLET, CYAN, PINK][i])
        mini_card(L, rx + 130, ry + 10, 120, 54, accent=CYAN)
        plant(L, rx - 175, ry + 70, 1.0)

    page("team", 1, ["Our business", "team"],
         "Bring your whole team together in one calm, collaborative workspace built "
         "for momentum and clarity.", VIOLET, illo_team)

    # 2 — Boost your business ----------------------------------------------#
    def illo_boost(L):
        organic_blob(L, rx, ry, 280, 280, [(rgba(INDIGO, 0.92), 0), (rgba(BLUE, 0.85), 100)])
        star4(L, rx - 180, ry - 170, 14, YELLOW)
        star4(L, rx + 180, ry + 150, 10, CYAN)
        dots(L, rx + 150, ry - 150, 3, 3, 16, 3, "#FFFFFF", opacity=0.7)
        # rocket
        body_x, body_y = rx + 10, ry - 30
        L.add({"type": "path",
               "d": f"M {body_x} {body_y-90} Q {body_x+34} {body_y-30} {body_x+30} {body_y+60} "
                    f"L {body_x-30} {body_y+60} Q {body_x-34} {body_y-30} {body_x} {body_y-90} Z",
               "fill": linear_gradient([("#FFFFFF", 0), ("#E4E9FF", 100)], angle=90)})
        circle(L, body_x, body_y - 16, 16, CYAN, stroke="#FFFFFF", sw=4)
        L.polygon([[body_x - 30, body_y + 26], [body_x - 56, body_y + 64], [body_x - 30, body_y + 60]], fill=PINK)
        L.polygon([[body_x + 30, body_y + 26], [body_x + 56, body_y + 64], [body_x + 30, body_y + 60]], fill=PINK)
        # flames
        L.polygon([[body_x - 16, body_y + 60], [body_x, body_y + 112], [body_x + 16, body_y + 60]], fill=YELLOW)
        L.polygon([[body_x - 9, body_y + 60], [body_x, body_y + 92], [body_x + 9, body_y + 60]], fill=PINKS)
        person(L, rx - 150, ry + 70, 1.0, shirt=VIOLET)
        person(L, rx + 150, ry + 70, 1.0, shirt=CYAN, hair="#22304F")
        # gear
        gear(L, rx + 160, ry - 30, 26, "#FFFFFF")
        # launch pad under the crew
        rrect(L, [rx - 84, ry + 150, 188, 16], rgba("#FFFFFF", 0.9), radius=8)
        ground_shadow(L, rx, ry + 176, 200)
        # dashed ascent trajectory
        L.add({"type": "path", "d": f"M {rx+10} {ry+30} Q {rx-120} {ry-130} {rx-190} {ry-150}",
               "fill": "none", "stroke": rgba("#FFFFFF", 0.7),
               "stroke_style": {"stroke_width": 3, "stroke_dasharray": [2, 11], "stroke_linecap": "round"}})
        # growth chip
        rrect(L, [rx + 120, ry - 152, 100, 42], "#FFFFFF", radius=12, shadow=soft(10, 22, opacity=0.18))
        L.text([rx + 130, ry - 152, 84, 42], "+45%", style=txt(17, color="#16A34A", weight=800, valign="middle"))

    page("boost", 2, ["Boost your", "business"],
         "Launch faster with growth tools that put your startup on the fastest path "
         "to liftoff.", INDIGO, illo_boost)

    # 3 — Online education --------------------------------------------------#
    def illo_edu(L):
        organic_blob(L, rx, ry, 285, 270, [(rgba(CYAN, 0.85), 0), (rgba(VIOLET, 0.9), 100)])
        ground_shadow(L, rx, ry + 150, 250)
        # big document/tablet
        rrect(L, [rx - 70, ry - 130, 150, 200], "#FFFFFF", radius=16, shadow=soft(16, 36, opacity=0.2))
        rrect(L, [rx - 70, ry - 130, 150, 46], linear_gradient([(VIOLET, 0), (CYAN, 100)], angle=45),
              radius=16)
        circle(L, rx - 40, ry - 107, 11, "#FFFFFF")
        for i in range(5):
            rrect(L, [rx - 52, ry - 56 + i * 22, 110 - (i % 2) * 26, 7], rgba(SUB, 0.45), radius=3.5)
        # graduation cap
        cap_x, cap_y = rx + 96, ry - 150
        L.polygon([[cap_x - 30, cap_y], [cap_x, cap_y - 16], [cap_x + 30, cap_y], [cap_x, cap_y + 16]], fill=INK)
        rrect(L, [cap_x - 14, cap_y + 4, 28, 16], INK, radius=3)
        line(L, (cap_x + 30, cap_y), (cap_x + 30, cap_y + 26), YELLOW, 2.5)
        circle(L, cap_x + 30, cap_y + 28, 4, YELLOW)
        person(L, rx + 120, ry + 40, 1.05, shirt=PINK, hair="#2E1A55")
        person(L, rx - 150, ry + 50, 1.0, shirt=BLUE, hair="#22304F")
        # floating books
        for i, c in enumerate((VIOLET, CYAN, PINK)):
            rrect(L, [rx - 200 + i * 8, ry + 96 + i * 2, 60, 12], c, radius=3)
        mini_card(L, rx + 120, ry - 40, 120, 50, accent=CYAN)

    page("education", 0, ["Online", "education"],
         "Learn anything at your own pace with bite-sized lessons, mentors and a "
         "community that cheers you on.", CYAN, illo_edu)

    # 4 — Online shopping ---------------------------------------------------#
    def illo_shop(L):
        organic_blob(L, rx, ry, 285, 275, [(rgba(PURPLE, 0.9), 0), (rgba(BLUE, 0.85), 100)])
        ground_shadow(L, rx, ry + 150, 250)
        # storefront
        rrect(L, [rx - 130, ry - 90, 200, 150], "#FFFFFF", radius=16, shadow=soft(16, 36, opacity=0.2))
        rrect(L, [rx - 130, ry - 90, 200, 40],
              linear_gradient([(VIOLET, 0), (INDIGO, 100)], angle=0), radius=16)
        for i in range(4):
            L.add({"type": "path", "d": f"M {rx-130+i*50} {ry-50} h 50 v 14 a 25 7 0 0 1 -50 0 Z",
                   "fill": [PINKS, CYAN][i % 2]})
        # shopping cart (clearer basket + handle + wheels)
        cart_x, cart_y = rx + 104, ry + 18
        L.add({"type": "path", "d": f"M {cart_x-34} {cart_y-22} h 14 l 12 12 h 70",
               "fill": "none", "stroke": "#FFFFFF",
               "stroke_style": {"stroke_width": 6, "stroke_linecap": "round", "stroke_linejoin": "round"}})
        L.polygon([[cart_x - 8, cart_y + 2], [cart_x + 66, cart_y + 2],
                   [cart_x + 56, cart_y + 36], [cart_x + 2, cart_y + 36]], fill="#FFFFFF")
        for dx in (10, 28, 46):
            line(L, (cart_x + dx, cart_y + 6), (cart_x + dx - 2, cart_y + 32), rgba(VIOLET, 0.55), 2)
        circle(L, cart_x + 12, cart_y + 48, 7, VIOLET)
        circle(L, cart_x + 46, cart_y + 48, 7, VIOLET)
        # discount tag
        tag_x, tag_y = rx - 160, ry - 130
        L.polygon([[tag_x, tag_y], [tag_x + 54, tag_y], [tag_x + 70, tag_y + 22],
                   [tag_x + 54, tag_y + 44], [tag_x, tag_y + 44]], fill=PINK)
        circle(L, tag_x + 54, tag_y + 22, 5, "#FFFFFF")
        L.text([tag_x, tag_y, 54, 44], "-50%", style=txt(13, color="#FFFFFF", weight=800,
               align="center", valign="middle"))
        person(L, rx - 150, ry + 60, 1.05, shirt=CYAN)
        # coins
        for i in range(3):
            circle(L, rx + 150, ry + 110 - i * 10, 13, YELLOW, stroke="#F59E0B", sw=2)

    page("shopping", 3, ["Online", "shopping"],
         "Open your store in minutes and sell everywhere your customers already love "
         "to shop.", PURPLE, illo_shop)

    # 5 — Stay healthy active ----------------------------------------------#
    def illo_health(L):
        organic_blob(L, rx, ry, 285, 270, [(rgba(CYAN, 0.85), 0), (rgba(PURPLE, 0.9), 100)])
        # running person (dynamic)
        hx, hy = rx, ry - 10
        circle(L, hx, hy - 60, 16, "#F4C7A6")
        circle(L, hx + 12, hy - 64, 6, "#2E1A55")
        rrect(L, [hx - 16, hy - 46, 34, 44], PINK, radius=12, opacity=1.0)
        line(L, (hx + 4, hy - 30), (hx + 40, hy - 44), PINK, 12)
        line(L, (hx - 4, hy - 30), (hx - 36, hy - 18), "#F4C7A6", 12)
        line(L, (hx + 2, hy), (hx + 34, hy + 40), VIOLET, 14)
        line(L, (hx - 2, hy), (hx - 30, hy + 44), VIOLET, 14)
        circle(L, hx + 36, hy + 46, 8, "#FFFFFF")
        circle(L, hx - 32, hy + 50, 8, "#FFFFFF")
        # smartwatch / health card with heart + activity bars
        rrect(L, [rx + 124, ry - 116, 104, 92], "#FFFFFF", radius=16, shadow=soft(12, 26, opacity=0.18))
        heart(L, rx + 150, ry - 92, 11, PINK)
        L.text([rx + 168, ry - 104, 56, 26], "98", style=txt(18, color=INK, weight=800, valign="middle"))
        bars(L, rx + 138, ry - 70, 78, 30, [0.4, 0.7, 0.5, 0.9], color=VIOLET)
        # plants + dots + step trail + ground
        ground_shadow(L, hx, hy + 60, 130)
        for i in range(5):
            circle(L, hx - 150 + i * 26, hy + 64, 4.5, rgba("#FFFFFF", 0.65))
        plant(L, rx - 170, ry + 110, 1.2)
        plant(L, rx + 160, ry + 110, 1.0)
        dots(L, rx - 200, ry - 150, 3, 3, 16, 3, "#FFFFFF", opacity=0.7)

    page("health", 4, ["Stay healthy", "active"],
         "Build habits that stick with friendly nudges, daily streaks and goals you "
         "actually reach.", CYAN, illo_health)

    # 6 — Creative collaboration -------------------------------------------#
    def illo_create(L):
        organic_blob(L, rx, ry, 285, 270, [(rgba(BLUE, 0.88), 0), (rgba(INDIGO, 0.9), 100)])
        ground_shadow(L, rx, ry + 150, 220)
        # 2x2 interlocking puzzle board
        bx, by, ps, g = rx - 44, ry - 46, 64, 10
        cols = [VIOLET, CYAN, PINKS, TEAL]
        k = 0
        for r2 in range(2):
            for c2 in range(2):
                puzzle_piece(L, bx + c2 * (ps + g), by + r2 * (ps + g), ps, cols[k])
                k += 1
        person(L, rx - 150, ry + 40, 1.05, shirt=PINK)
        person(L, rx + 150, ry + 40, 1.05, shirt=VIOLET, hair="#22304F")
        # one lifted piece (being placed)
        puzzle_piece(L, rx + 120, ry - 134, 46, YELLOW, shadow=True)
        star4(L, rx - 190, ry - 130, 12, YELLOW)
        dots(L, rx + 150, ry + 110, 4, 2, 15, 3, "#FFFFFF", opacity=0.7)

    page("create", 1, ["Create", "together"],
         "Where ideas click into place — design, review and ship beautiful work as "
         "one team.", BLUE, illo_create)

    # 7 — Virtual reality platform -----------------------------------------#
    def illo_vr(L):
        organic_blob(L, rx, ry, 285, 275, [(rgba(VIOLET, 0.92), 0), (rgba(INDIGO, 0.88), 100)])
        for sx, sy, sr in [(rx - 170, ry - 160, 12), (rx + 160, ry - 130, 9),
                           (rx + 180, ry + 120, 14), (rx - 190, ry + 130, 8)]:
            star4(L, sx, sy, sr, "#FFFFFF")
        # orbit + planet (sci-fi)
        ring(L, rx - 150, ry - 20, 42, rgba("#FFFFFF", 0.85), sw=3)
        circle(L, rx - 150, ry - 20, 13, CYAN)
        circle(L, rx - 150 - 42, ry - 20, 5, PINKS)
        # floating holographic panel
        rrect(L, [rx + 96, ry - 130, 152, 98], rgba("#FFFFFF", 0.96), radius=16,
              shadow=soft(14, 30, opacity=0.22))
        rrect(L, [rx + 110, ry - 116, 124, 14], rgba(VIOLET, 0.2), radius=6)
        bars(L, rx + 110, ry - 88, 84, 38, [0.5, 0.8, 0.6, 0.95], color=CYAN)
        circle(L, rx + 214, ry - 62, 13, PINK)
        # linked UI orbs
        orbs = [(rx + 150, ry + 64, PINK), (rx + 190, ry + 96, CYAN), (rx + 150, ry + 128, YELLOW)]
        line(L, orbs[0][:2], orbs[1][:2], rgba("#FFFFFF", 0.6), 2)
        line(L, orbs[1][:2], orbs[2][:2], rgba("#FFFFFF", 0.6), 2)
        for ox, oy, oc in orbs:
            circle(L, ox, oy, 12, oc, shadow=soft(8, 16, opacity=0.25))
        # person with a chunky VR headset
        hx, hy = rx - 16, ry + 50
        ground_shadow(L, hx, hy + 74, 120)
        person(L, hx, hy, 1.25, shirt=CYAN, hair="#2E1A55")
        rrect(L, [hx - 27, hy - 24, 56, 28], INK, radius=12)
        rrect(L, [hx - 20, hy - 19, 42, 18], linear_gradient([(CYAN, 0), (VIOLET, 100)], angle=0), radius=7)
        rrect(L, [hx - 33, hy - 16, 8, 11], INK, radius=3)

    page("vr", 2, ["Virtual reality", "platform"],
         "Step inside immersive worlds and build experiences your users will never "
         "forget.", VIOLET, illo_vr)

    # 8 — App development ---------------------------------------------------#
    def illo_app(L):
        organic_blob(L, rx, ry, 280, 280, [(rgba(INDIGO, 0.92), 0), (rgba(PURPLE, 0.88), 100)])
        ground_shadow(L, rx, ry + 172, 230)
        # big phone
        px, py = rx + 30, ry - 10
        rrect(L, [px - 70, py - 150, 140, 290], INK, radius=28, shadow=soft(18, 40, opacity=0.24))
        rrect(L, [px - 60, py - 138, 120, 266], "#FFFFFF", radius=20)
        rrect(L, [px - 60, py - 138, 120, 70],
              linear_gradient([(VIOLET, 0), (CYAN, 100)], angle=45), radius=20)
        circle(L, px, py - 150, 4, "#3A3F55")
        for i in range(3):
            rrect(L, [px - 46, py - 50 + i * 34, 92, 22], rgba(VIOLET, 0.12), radius=8)
            circle(L, px - 34, py - 39 + i * 34, 7, [VIOLET, CYAN, PINK][i])
        person(L, rx - 150, ry + 40, 1.05, shirt=CYAN)
        # code card
        rrect(L, [rx - 210, ry - 110, 130, 86], "#FFFFFF", radius=14, shadow=soft(12, 26, opacity=0.18))
        for i in range(4):
            rrect(L, [rx - 196, ry - 96 + i * 18, 60 + (i % 2) * 36, 6], [VIOLET, CYAN, PINK, SUB][i], radius=3)
        gear(L, rx + 150, ry + 90, 22, "#FFFFFF")

    page("app", 3, ["App", "development"],
         "From idea to App Store — design, build and ship native apps your users "
         "love.", INDIGO, illo_app)

    # 9 — SEO analysis ------------------------------------------------------#
    def illo_seo(L):
        organic_blob(L, rx, ry, 285, 270, [(rgba(CYAN, 0.85), 0), (rgba(INDIGO, 0.9), 100)])
        ground_shadow(L, rx, ry + 150, 250)
        # dashboard
        rrect(L, [rx - 130, ry - 110, 240, 170], "#FFFFFF", radius=18, shadow=soft(16, 36, opacity=0.2))
        rrect(L, [rx - 130, ry - 110, 240, 36], linear_gradient([(VIOLET, 0), (CYAN, 100)], angle=0), radius=18)
        bars(L, rx - 110, ry - 22, 120, 64, [0.45, 0.7, 0.55, 0.85, 0.6], color=VIOLET)
        # line chart
        pts = [(rx + 26, ry + 30), (rx + 50, ry - 4), (rx + 74, ry + 8), (rx + 98, ry - 30)]
        for i in range(len(pts) - 1):
            line(L, pts[i], pts[i + 1], CYAN, 3.5)
        for p in pts:
            circle(L, p[0], p[1], 4, PINK)
        # magnifier
        mx, my = rx + 140, ry + 90
        ring(L, mx, my, 30, VIOLET, sw=8)
        line(L, (mx + 22, my + 22), (mx + 44, my + 44), VIOLET, 9)
        person(L, rx - 160, ry + 60, 1.05, shirt=PINK)
        star4(L, rx + 150, ry - 150, 12, YELLOW)

    page("seo", 4, ["SEO", "analysis"],
         "See exactly what moves your rankings with clear dashboards and insights you "
         "can act on today.", CYAN, illo_seo)

    return doc


# ---- compound icon primitives (defined after use is fine at runtime) ------ #
def gear(L, cx, cy, r, color):
    for k in range(8):
        a = k * math.pi / 4
        line(L, (cx + (r - 3) * math.cos(a), cy + (r - 3) * math.sin(a)),
             (cx + (r + 6) * math.cos(a), cy + (r + 6) * math.sin(a)), color, 6)
    circle(L, cx, cy, r, color)
    circle(L, cx, cy, r * 0.45, rgba(INDIGO, 0.9))


def ring(L, cx, cy, r, color, *, sw=7):
    L.add({"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": "none",
           "stroke": color, "stroke_style": {"stroke_width": sw}})


def ground_shadow(L, cx, cy, w):
    L.add({"type": "ellipse", "center": [cx, cy], "rx": w / 2, "ry": w / 10,
           "fill": rgba("#2A1E55", 0.16)})


def puzzle_piece(L, x, y, s, color, *, shadow=False):
    rrect(L, [x, y, s, s], color, radius=12, shadow=(soft(10, 22, opacity=0.22) if shadow else None))
    circle(L, x + s * 0.5, y, s * 0.17, color)
    circle(L, x + s, y + s * 0.5, s * 0.17, color)
    circle(L, x + s * 0.5, y + s, s * 0.17, color)


def heart(L, cx, cy, s, color):
    circle(L, cx - s * 0.5, cy - s * 0.28, s * 0.6, color)
    circle(L, cx + s * 0.5, cy - s * 0.28, s * 0.6, color)
    L.polygon([[cx - s * 1.02, cy - s * 0.02], [cx + s * 1.02, cy - s * 0.02],
               [cx, cy + s * 1.15]], fill=color)



doc = build_document()

if __name__ == "__main__":
    import sys
    doc.write(sys.argv[1] if len(sys.argv) > 1 else "saas_hero_headers.fg.yaml",
              fail_on_error=True)
