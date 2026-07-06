"""Formula 1 car — a 128-layer, vision-checked composition (FrameGraph SDK).

A side-profile modern F1 car in a race-day scene, authored as exactly 128
stacked layers and verified against the rendered pixels with the FrameGraph
MCP vision tools (detect_regions for silhouette separation, measure_image /
compare_images for structure). Every drawn object is one layer; parametric
detail (grandstand crowd, kerb teeth, tyre spokes, speed streaks) is generated
so the total lands on 128 exactly (asserted at build time).

Reading order (back to front): sky -> grandstand + crowd -> track + kerb +
motion streaks -> car shadow -> rear wing -> engine cover / airbox / halo ->
cockpit + helmet -> sidepod -> floor -> nose -> front wing -> wheels +
suspension -> livery + number.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import DocumentBuilder, Path, linear_gradient, radial_gradient, rgba  # noqa: E402

W, H = 1280.0, 720.0
TARGET_LAYERS = 128

# ---- palette -------------------------------------------------------------- #
SKY_T, SKY_B = "#7fb4d8", "#dcecf5"
BODY = "#f2591f"          # papaya
BODY_HI = "#ff7a3c"
BODY_SH = "#c4400c"
CARBON = "#171d28"
CARBON_HI = "#2b3444"
WHITE = "#f6f4ee"
CYAN = "#18c2d6"
TYRE = "#141519"
TYRE_HI = "#33363d"
RIM = "#b9822e"
RIM_HI = "#e7bd60"
HALO = "#3c424b"
TARMAC = "#3a3e45"
TARMAC_HI = "#4a4f57"
KERB_R = "#cf3a2b"
KERB_W = "#ece9df"
STAND = "#8b96a3"
STAND_D = "#6f7a88"
SANS = ["Helvetica", "Arial", "sans-serif"]


# ---- primitive builders (raw model dicts, all decorative) ----------------- #
def rect(box, **k):
    return {"type": "rect", "box": [float(v) for v in box], "decorative": True, **k}


def ell(cx, cy, rx, ry, sw=None, **k):
    if sw is not None:                       # stroke width lives in stroke_style, not on the shape
        k.setdefault("stroke_style", {"stroke_width": sw})
    return {"type": "ellipse", "center": [float(cx), float(cy)], "rx": float(rx), "ry": float(ry),
            "decorative": True, **k}


def disc(cx, cy, r, sw=None, **k):
    return ell(cx, cy, r, r, sw=sw, **k)


def line(pts, color, w=2.0, dash=None, opacity=1.0, cap="round"):
    ss = {"stroke_width": w, "stroke_linecap": cap}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    return {"type": "polyline", "points": [[float(x), float(y)] for x, y in pts],
            "stroke": color, "stroke_style": ss, "fill": "none",
            "decorative": True, "opacity": opacity}


def poly(pts, fill, opacity=1.0, stroke=None, sw=0.0, smooth=False):
    """Filled polygon; smooth=True lowers to a closed Catmull-Rom path."""
    fields = {"fill": fill, "decorative": True, "opacity": opacity}
    if stroke:
        fields["stroke"] = stroke
        fields["stroke_style"] = {"stroke_width": sw, "stroke_linejoin": "round"}
    if smooth:
        g = Path().through([(float(x), float(y)) for x, y in pts]).close()
        return g.object(**fields)
    return {"type": "polygon", "points": [[float(x), float(y)] for x, y in pts], **fields}


def text(x, y, s, size, color, w=300, align="left", weight=700, italic=False):
    st = {"font_family": SANS, "font_size": size, "color": color,
          "align": align, "vertical_align": "middle", "font_weight": weight}
    if italic:
        st["font_style"] = "italic"
    return {"type": "text", "box": [float(x), float(y), float(w), float(size * 1.5)],
            "text": s, "style": st, "decorative": True}


# ---- deterministic jitter (no random module: stable across renders) -------- #
def jit(i, a=12.9898, b=78.233, m=43758.5453):
    v = math.sin(i * a + b) * m
    return v - math.floor(v)          # in [0,1)


# --------------------------------------------------------------------------- #
#  scene sections — each returns an ordered list of layers (back -> front)
# --------------------------------------------------------------------------- #
def background():
    S = []
    S.append(rect([0, 0, W, H], fill=linear_gradient([(SKY_T, 0.0), (SKY_B, 1.0)], angle=180)))  # sky
    S.append(disc(1060, 130, 46, fill=rgba("#fff6d8", 0.85)))                                     # hazy sun
    S.append(rect([0, 300, W, 40], fill=rgba("#c9d6df", 0.7)))                                    # haze band
    # grandstand roof + tiers
    S.append(poly([(0, 300), (W, 300), (W, 210), (120, 178), (0, 196)], STAND_D))                 # roof
    S.append(rect([0, 300, W, 90], fill=STAND))                                                   # stand face
    for r in range(2):                                                                            # tier rails
        y = 318 + r * 30
        S.append(line([(0, y), (W, y)], rgba(STAND_D, 0.6), w=3))
    S.append(rect([0, 388, W, 14], fill=CARBON_HI))                                               # pit wall
    return S


def crowd(n):
    """n dots across the grandstand tiers — fills the layer budget to 128."""
    S = []
    cols = ["#e7c9a0", "#d98b6a", "#c15b48", "#e3d7c2", "#b7c2cf", "#8f6f5a"]
    for i in range(n):
        row = i % 4
        y = 316 + row * 18 + jit(i * 2) * 4
        x = 10 + ((i * 37.0) % (W - 20)) + jit(i) * 6
        c = cols[i % len(cols)]
        S.append(disc(x, y, 3.4, fill=rgba(c, 0.9)))
    return S


def track():
    S = []
    S.append(rect([0, 402, W, H - 402], fill=TARMAC))                                             # tarmac
    S.append(poly([(0, 402), (W, 402), (W, 470), (0, 520)], TARMAC_HI, opacity=0.5))              # sheen
    # red/white kerb along the base
    n = 8
    for i in range(n):
        S.append(rect([i * (W / n), 706, W / n, 14], fill=KERB_R if i % 2 == 0 else KERB_W))
    return S


def motion_streaks(n):
    S = []
    for i in range(n):
        y = 300 + jit(i * 3) * 240
        w = 90 + jit(i) * 170
        x = jit(i * 5) * 260
        S.append(rect([x, y, w, 3.4], fill=rgba(WHITE, 0.20 + 0.18 * jit(i * 7)), radius=2))
    return S


# ---- the car (side profile, facing right) --------------------------------- #
GY = 560.0                       # ground contact
RWX, FWX = 372.0, 972.0          # rear / front wheel centres
WR = 78.0                        # tyre radius
WHEEL_Y = GY - WR                # 482


def car_shadow():
    return [ell((RWX + FWX) / 2, GY + 8, 380, 26, fill=rgba("#0b0d10", 0.32))]


def rear_wing():
    # mounted BEHIND the rear wheel (wheel spans x 294..450) so nothing floats over it
    S = []
    S.append(rect([182, 366, 16, 116], fill=CARBON, radius=3))                # endplate (tall, rearmost)
    S.append(poly([(190, 386), (300, 380), (300, 398), (190, 402)], CARBON))  # main plane
    S.append(poly([(190, 368), (298, 364), (298, 380), (190, 386)], BODY))    # upper flap (DRS)
    S.append(rect([198, 452, 96, 10], fill=CARBON, radius=2))                 # beam wing
    S.append(poly([(300, 470), (356, 462), (356, 520), (300, 520)], CARBON_HI))  # diffuser (under body)
    return S


def rear_bridge():
    # swan-neck strut from the engine-cover top up to the wing root, drawn OVER the
    # wheel so the wing reads as cantilevered off the body (fixes the 'floating wing')
    return [poly([(346, 472), (298, 400), (312, 394), (360, 466)], CARBON_HI)]


def body():
    S = []
    # engine-cover / chassis silhouette (one filled body)
    sil = [(352, 520), (352, 474), (430, 466), (474, 452), (506, 430),
           (524, 420), (548, 452), (620, 470), (700, 466), (860, 470),
           (1010, 498), (1150, 512), (1150, 524), (1010, 526), (700, 528),
           (352, 528)]
    S.append(poly(sil, BODY, smooth=False))
    S.append(poly([(506, 430), (524, 420), (548, 452), (506, 452)], BODY_HI))  # airbox highlight
    S.append(poly([(352, 474), (506, 452), (548, 452), (430, 496), (352, 496)], BODY_SH, opacity=0.5))  # flank shade
    # shark fin on the engine cover
    S.append(poly([(430, 466), (524, 422), (392, 470)], rgba(CARBON, 0.9)))
    # airbox intake (the scoop above the driver)
    S.append(poly([(512, 428), (532, 420), (536, 436), (516, 442)], CARBON))
    return S


def halo_and_cockpit():
    S = []
    S.append(poly([(548, 452), (566, 470), (628, 474), (652, 464), (600, 452)], CARBON))  # cockpit tub opening
    S.append(disc(600, 456, 22, fill=WHITE))                       # helmet dome
    S.append(poly([(578, 456), (622, 456), (620, 470), (580, 470)], CYAN))  # helmet lower stripe
    S.append(poly([(586, 444), (614, 444), (610, 452), (590, 452)], BODY))  # helmet top stripe
    S.append(rect([596, 450, 22, 8], fill=CARBON, radius=3))       # visor
    # halo — titanium hoop over the cockpit
    hp = [(548, 452), (556, 428), (584, 414), (620, 414), (650, 430), (660, 456)]
    S.append(line(hp, HALO, w=9))
    S.append(rect([600, 414, 9, 42], fill=HALO))                   # halo central strut
    S.append(line([(560, 448), (556, 430)], rgba(WHITE, 0.5), w=2))  # halo spec highlight
    return S


def sidepod():
    S = []
    S.append(poly([(430, 470), (610, 476), (648, 500), (620, 524), (430, 524)], CARBON))  # sidepod body
    S.append(poly([(430, 476), (452, 470), (456, 512), (430, 516)], CARBON_HI))            # radiator inlet
    S.append(poly([(430, 476), (444, 474), (446, 510), (430, 512)], rgba("#000000", 0.55)))  # inlet mouth
    S.append(poly([(470, 522), (620, 522), (600, 534), (470, 534)], rgba(CARBON, 0.7)))    # undercut shadow
    S.append(rect([500, 484, 96, 6], fill=CYAN, radius=3))                                  # sidepod accent
    return S


def floor_and_nose():
    S = []
    S.append(rect([352, 524, 690, 10], fill=CARBON))                    # floor plank
    S.append(poly([(690, 528), (740, 528), (726, 548), (690, 548)], CARBON_HI))  # floor edge fin
    # raised nose sweeping DOWN to meet the front-wing mount
    S.append(poly([(860, 470), (1040, 500), (1132, 534), (1152, 548),
                   (1132, 552), (1030, 528), (860, 502)], BODY))
    S.append(poly([(1108, 528), (1152, 546), (1152, 550), (1108, 540)], BODY_HI))  # nose tip highlight
    S.append(poly([(700, 466), (760, 452), (770, 468), (720, 480)], CARBON))        # chassis bulkhead vane
    return S


def front_wing():
    # ahead of the front wheel (wheel spans x 894..1050); bold stack + tall endplate
    S = []
    S.append(rect([1044, 548, 152, 9], fill=CARBON, radius=2))          # main plane
    S.append(rect([1052, 536, 138, 7], fill=BODY, radius=2))            # 2nd element
    S.append(rect([1060, 526, 124, 6], fill=CARBON, radius=2))          # 3rd element
    S.append(rect([1068, 517, 108, 5], fill=BODY, radius=2))            # top flap
    S.append(poly([(1186, 506), (1208, 508), (1208, 568), (1184, 568)], CARBON))  # endplate (tall)
    S.append(poly([(1044, 557), (1122, 557), (1108, 572), (1044, 572)], CARBON_HI))  # footplate
    return S


def wheel(cx, spokes=8, front=False):
    S = []
    S.append(disc(cx, WHEEL_Y, WR, fill=TYRE))                           # tyre
    S.append(disc(cx, WHEEL_Y, WR, fill="none", stroke=TYRE_HI, sw=6))   # sidewall shoulder
    S.append(ell(cx - WR * 0.32, WHEEL_Y - WR * 0.34, WR * 0.5, WR * 0.42,
                 fill=rgba(TYRE_HI, 0.6)))                               # top-left tyre sheen
    S.append(disc(cx, WHEEL_Y, WR - 6, fill="none", stroke=rgba(WHITE, 0.85), sw=3))  # sidewall band
    S.append(disc(cx, WHEEL_Y, WR * 0.56, fill=CARBON_HI))              # rim well
    S.append(disc(cx, WHEEL_Y, WR * 0.5, fill=radial_gradient(
        [(RIM_HI, 0.0), (RIM, 1.0)], at="35% 35%")))                    # rim face
    for k in range(spokes):                                             # spokes
        a = (2 * math.pi * k / spokes)
        r0, r1 = WR * 0.16, WR * 0.48
        S.append(line([(cx + r0 * math.cos(a), WHEEL_Y + r0 * math.sin(a)),
                       (cx + r1 * math.cos(a), WHEEL_Y + r1 * math.sin(a))],
                      rgba(CARBON, 0.75), w=3))
    S.append(disc(cx, WHEEL_Y, WR * 0.16, fill=CARBON))                 # hub
    S.append(disc(cx, WHEEL_Y, WR * 0.07, fill=CYAN if front else BODY))  # wheel nut
    return S


def suspension():
    S = []
    # rear wishbones + pushrod (car body -> rear hub)
    S.append(line([(420, 496), (RWX + 30, WHEEL_Y - 6)], CARBON, w=5))     # upper
    S.append(line([(420, 522), (RWX + 24, WHEEL_Y + 20)], CARBON, w=5))    # lower
    S.append(line([(452, 470), (RWX + 34, WHEEL_Y + 10)], CARBON_HI, w=4)) # pushrod
    # front wishbones + trackrod (chassis -> front hub)
    S.append(line([(880, 500), (FWX - 30, WHEEL_Y - 6)], CARBON, w=5))     # upper
    S.append(line([(880, 524), (FWX - 24, WHEEL_Y + 20)], CARBON, w=5))    # lower
    S.append(line([(852, 486), (FWX - 34, WHEEL_Y + 6)], CARBON_HI, w=4))  # pushrod
    return S


def livery_and_marks():
    S = []
    # cyan accents that stay on the bodywork (never cross a wheel)
    S.append(poly([(700, 478), (882, 486), (882, 494), (700, 486)], CYAN, opacity=0.9))     # chassis flash
    S.append(poly([(1052, 516), (1130, 532), (1128, 538), (1050, 522)], CYAN, opacity=0.9))  # nose-tip flash
    S.append(poly([(452, 468), (520, 456), (536, 462), (472, 480)], WHITE, opacity=0.9))  # engine-cover flash
    S.append(text(452, 501, "FRAMEGRAPH", 14, WHITE, w=170, weight=700, italic=True))     # sidepod title sponsor
    S.append(disc(712, 486, 20, fill=WHITE))                          # number roundel (on the orange nose)
    S.append(disc(712, 486, 20, fill="none", stroke=CARBON, sw=2))
    S.append(text(700, 486, "16", 22, CARBON, w=26, align="center"))  # car number
    for (x, y, w) in [(770, 480, 26), (802, 478, 20)]:               # small engine-cover sponsors
        S.append(rect([x, y, w, 8], fill=rgba(WHITE, 0.85), radius=1))
    S.append(rect([1060, 526, 40, 5], fill=WHITE, opacity=0.8, radius=1))  # front-wing sponsor
    return S


def caption():
    S = []
    S.append(text(40, 40, "FORMULA 1", 34, CARBON, w=400, weight=800))
    S.append(text(40, 74, "128-layer composition · vision-checked · FrameGraph SDK", 14,
                  rgba(CARBON, 0.8), w=560, weight=600))
    return S


# --------------------------------------------------------------------------- #
#  assemble — order is z-order; crowd count is solved so total == 128
# --------------------------------------------------------------------------- #
def scene():
    bg = background()
    trk = track()
    streaks = motion_streaks(4)
    car = (car_shadow() + rear_wing() + body() + halo_and_cockpit() + sidepod()
           + floor_and_nose() + front_wing()
           + wheel(RWX, spokes=8, front=False) + wheel(FWX, spokes=8, front=True)
           + rear_bridge() + suspension() + livery_and_marks())
    cap = caption()
    fixed = len(bg) + len(trk) + len(streaks) + len(car) + len(cap)
    n_crowd = TARGET_LAYERS - fixed
    if n_crowd < 0:
        raise ValueError(f"fixed layers {fixed} already exceed target {TARGET_LAYERS}")
    layers = bg + crowd(n_crowd) + trk + streaks + car + cap
    assert len(layers) == TARGET_LAYERS, f"{len(layers)} != {TARGET_LAYERS}"
    return layers


def build_builder():
    b = DocumentBuilder(title="Formula 1 — 128-layer composition (FrameGraph)")
    page = b.page("f1", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.layer("scene").extend(scene())
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from framegraph.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "f1_car_128_layers.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}  ({len(scene())} layers)")
