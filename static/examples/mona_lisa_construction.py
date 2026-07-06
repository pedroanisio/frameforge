"""Anatomy of the Mona Lisa — a construction plate (FrameGraph SDK).

Renders the essay's thesis: the portrait is *constructed* before it is painted.
A stylized sfumato figure (earth palette, gradient modelling, atmospheric-
perspective landscape) sits under a semi-transparent sanguine overlay of the
invisible geometry — the pyramidal composition, the skull oval, the turned
vertical axis, the eye/nose/mouth proportion guides, the contrapposto spiral,
and the cylinders of the folded hands — each annotated in a serif hand.

Built entirely from SDK primitives (gradients / ellipses / smooth paths / text).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import DocumentBuilder, Path, linear_gradient, radial_gradient, rgba  # noqa: E402

W, H = 980.0, 1320.0
SAN = "#a83f28"        # sanguine construction ink
SERIF = ["Georgia", "Times New Roman", "serif"]


def lin(stops, angle=None):
    return linear_gradient(stops, angle=angle)


def rect(box, fill, **k):
    return {"type": "rect", "box": [float(v) for v in box], "fill": fill, "decorative": True, **k}


def ell(cx, cy, rx, ry, **k):
    return {"type": "ellipse", "center": [float(cx), float(cy)], "rx": float(rx), "ry": float(ry),
            "decorative": True, **k}


def blob(pts, fill, opacity=None, smooth=True, **k):   # always smooth; absorb the kwarg
    g = Path().through([(float(x), float(y)) for x, y in pts]); g.close()
    f = {"fill": fill, "decorative": True, **k}
    if opacity is not None:
        f["opacity"] = opacity
    return g.object(**f)


def linepoly(pts, stroke, w=1.2, dash=None, opacity=None, closed=False, smooth=False):
    ss = {"stroke_width": w}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    o = {"type": "polyline", "points": [[float(x), float(y)] for x, y in pts],
         "stroke": stroke, "stroke_style": ss, "fill": "none", "decorative": True}
    if closed:
        o["closed"] = True
    if opacity is not None:
        o["opacity"] = opacity
    if smooth:
        g = Path().through([(float(x), float(y)) for x, y in pts])
        if closed:
            g.close()
        return {**g.object(stroke=stroke, stroke_style=ss, fill="none", decorative=True),
                **({"opacity": opacity} if opacity is not None else {})}
    return o


def seg(a, b, stroke, w=1.2, dash=None, opacity=0.85):
    return linepoly([a, b], stroke, w=w, dash=dash, opacity=opacity)


def ring(cx, cy, rx, ry, stroke, w=1.2, dash=None, opacity=0.85):
    return ell(cx, cy, rx, ry, fill="none", stroke=stroke,
               stroke_style={"stroke_width": w, **({"stroke_dasharray": list(dash)} if dash else {})},
               opacity=opacity)


def label(x, y, text, size=17, color="#2c2318", w=320, align="left", weight=400, italic=False):
    st = {"font_family": SERIF, "font_size": size, "color": color, "align": align,
          "vertical_align": "middle"}
    if weight != 400:
        st["font_weight"] = weight
    if italic:
        st["font_style"] = "italic"
    return {"type": "text", "box": [float(x), float(y), float(w), float(size * 1.6)],
            "text": text, "style": st, "decorative": True}


# --------------------------------------------------------------------------- #
#  layer 1 — atmospheric-perspective landscape
# --------------------------------------------------------------------------- #
def landscape():
    S = [rect([0, 0, W, H], lin([("#8fa0a6", 0), ("#b7b79a", 0.42), ("#cbb98f", 0.62)], angle=180))]
    HZ = 560
    # far mountains — cool, low-contrast (recede)
    S.append(blob([(0, HZ - 40), (120, HZ - 150), (250, HZ - 70), (400, HZ - 190),
                   (560, HZ - 90), (720, HZ - 200), (900, HZ - 100), (W, HZ - 150),
                   (W, HZ), (0, HZ)], "#93a6ab", smooth=True, opacity=0.9))
    S.append(blob([(0, HZ - 10), (160, HZ - 80), (360, HZ - 30), (600, HZ - 110),
                   (820, HZ - 40), (W, HZ - 80), (W, HZ + 40), (0, HZ + 40)],
                  "#9fa585", smooth=True))
    # winding river (light, cooler) + a bridge
    S.append(blob([(120, HZ + 10), (240, HZ - 20), (360, HZ + 20), (300, HZ + 70),
                   (180, HZ + 60), (90, HZ + 90)], "#c4cabc", smooth=True, opacity=0.85))
    for i in range(5):
        S.append(rect([250 + i * 15, HZ - 26 + i * 1.5, 12, 20], "#8f8266", opacity=0.8))
    # near warm hills flanking the figure (right side higher, "dreamlike" imbalance)
    S.append(blob([(0, HZ + 30), (200, HZ + 6), (330, HZ + 40), (330, 780), (0, 780)],
                  "#7d6a45", smooth=True))
    S.append(blob([(650, HZ + 40), (820, HZ - 6), (W, HZ + 30), (W, 820), (650, 820)],
                  "#6f5c3b", smooth=True))
    # balcony parapet + two column bases (the loggia)
    S.append(rect([0, 690, W, 26], "#6a5638"))
    S.append(rect([44, 610, 40, 90], lin([("#8a7550", 0), ("#5e4a30", 1)], angle=90)))
    S.append(rect([W - 84, 610, 40, 90], lin([("#5e4a30", 0), ("#8a7550", 1)], angle=90)))
    return S


# --------------------------------------------------------------------------- #
#  layer 2 — the figure (sfumato modelling with gradients + soft overlays)
# --------------------------------------------------------------------------- #
CX = 486.0   # figure axis
def figure():
    S = []
    # garment pyramid (broad base -> narrow shoulders), warm dark umber with fold light
    S.append(blob([(CX, 590), (210, 1150), (210, H), (W - 210, H), (W - 210, 1150)],
                  lin([("#4a3826", 0), ("#2a1e12", 1)], angle=180), smooth=True))
    # veil/shawl over the shoulders (translucent warm)
    S.append(blob([(CX, 604), (300, 900), (350, 1060), (CX, 1010), (W - 350, 1060),
                   (W - 300, 900)], rgba("#6a563a", 0.5), smooth=True))
    # fold accents on the garment
    for fx in (330, 400, 560, 640):
        S.append(seg((fx, 900), (fx - 30, 1200), rgba("#1c130a", 0.5), w=6, opacity=0.5))
    # gathered sleeve (ochre/gold) lower-left, foreground
    S.append(blob([(250, 1010), (300, 940), (430, 980), (470, 1090), (360, 1180), (250, 1140)],
                  lin([("#9a6f34", 0), ("#5f451f", 1)], angle=120), smooth=True))
    for a, b in [((300, 990), (350, 1140)), ((360, 975), (420, 1130)), ((420, 990), (455, 1120))]:
        S.append(seg(a, b, rgba("#3a2a12", 0.6), w=4, opacity=0.6))

    # neck (cylinder) with core shadow to the right
    S.append(blob([(430, 545), (545, 545), (560, 660), (520, 700), (452, 700), (420, 660)],
                  "#c79a6c", smooth=True))
    S.append(blob([(512, 560), (560, 620), (540, 690), (500, 690)], rgba("#7d5636", 0.55),
                  smooth=True, opacity=0.7))

    # hair behind (dark), center-parted, falling to the shoulders
    S.append(blob([(CX, 236), (330, 300), (300, 560), (360, 720), (452, 640), (452, 340)],
                  "#241a12", smooth=True))
    S.append(blob([(CX, 236), (642, 300), (676, 560), (620, 720), (520, 640), (520, 340)],
                  "#20160f", smooth=True))

    # face base (warm flesh), oval
    S.append(ell(CX, 372, 96, 122, fill="#d8b083"))
    # light from upper-left: soft highlight
    S.append(ell(CX - 34, 336, 74, 92, fill=radial_gradient(
        [(rgba("#f0d7b2", 0.9), 0), (rgba("#f0d7b2", 0.0), 1)])))
    # form shadow (right/underside) — the cheek turning from the light
    S.append(blob([(CX + 30, 300), (CX + 96, 372), (CX + 70, 470), (CX + 10, 500),
                   (CX + 20, 430), (CX + 44, 360)], rgba("#9a6f45", 0.55), smooth=True, opacity=0.8))
    S.append(blob([(CX - 70, 452), (CX + 60, 452), (CX + 40, 500), (CX - 46, 496)],
                  rgba("#8a6038", 0.4), smooth=True, opacity=0.7))  # under-chin / jaw shadow
    # cheek warmth
    S.append(ell(CX - 44, 404, 26, 20, fill=radial_gradient(
        [(rgba("#d98a63", 0.5), 0), (rgba("#d98a63", 0.0), 1)])))

    # hairline meeting a high forehead (center-parted, no bangs) + veil edge
    S.append(linepoly([(CX - 94, 316), (CX - 42, 286), (CX, 300), (CX + 42, 286), (CX + 94, 316)],
                      "#241a12", w=12, smooth=True, opacity=0.92))
    S.append(linepoly([(CX - 150, 300), (CX - 96, 262), (CX, 250), (CX + 96, 262), (CX + 150, 300)],
                      rgba("#d8cdb0", 0.5), w=3, smooth=True, opacity=0.5))  # sheer veil

    # eyes — hooded, the far (left-in-image) eye slightly narrower (the head turns)
    S.append(blob([(CX - 62, 356), (CX - 40, 348), (CX - 18, 356), (CX - 40, 366)],
                  "#efe7d6", smooth=True))                     # near eye white
    S.append(blob([(CX + 20, 358), (CX + 40, 351), (CX + 58, 358), (CX + 40, 366)],
                  "#e7ddc9", smooth=True))                     # far eye white (narrower)
    S.append(ell(CX - 40, 357, 7.5, 8.5, fill="#3a2716"))      # iris near
    S.append(ell(CX + 40, 358, 6.5, 7.5, fill="#3a2716"))      # iris far
    for ex in (-40, 40):                                       # upper-lid shadow (no eyebrows)
        S.append(linepoly([(CX + ex - 22, 350), (CX + ex, 344), (CX + ex + 22, 350)],
                          rgba("#6e4c2c", 0.7), w=3, smooth=True, opacity=0.75))
    # nose — central ridge lit, soft shadow on the right, nostril hint
    S.append(blob([(CX - 6, 366), (CX + 6, 366), (CX + 20, 430), (CX - 2, 442), (CX - 18, 428)],
                  rgba("#b07f4f", 0.4), smooth=True, opacity=0.7))
    S.append(ell(CX + 12, 432, 5, 3.5, fill=rgba("#7d5636", 0.5)))
    # mouth — the smile: a soft, asymmetric band of shadow, no hard contour
    S.append(blob([(CX - 40, 470), (CX, 466), (CX + 42, 468), (CX + 20, 480),
                   (CX, 482), (CX - 22, 480)], rgba("#8a4f38", 0.55), smooth=True, opacity=0.8))
    S.append(linepoly([(CX - 40, 470), (CX - 10, 474), (CX + 20, 472), (CX + 42, 466)],
                      rgba("#5e3220", 0.6), w=2.2, smooth=True, opacity=0.7))  # the shadow line
    S.append(ell(CX - 40, 470, 5, 4, fill=rgba("#c98a63", 0.5)))   # lifted-cheek corner (smile)

    # folded hands (foreground) — cylinders of fingers, one hand over the wrist
    S.append(blob([(CX - 120, 1015), (CX - 20, 995), (CX + 90, 1010), (CX + 130, 1075),
                   (CX + 60, 1120), (CX - 70, 1120), (CX - 130, 1075)],
                  lin([("#e0b385", 0), ("#b07f50", 1)], angle=160), smooth=True))
    for i, fx in enumerate((-70, -34, 2, 40)):                 # four resting fingers (near hand)
        S.append(blob([(CX + fx, 1010), (CX + fx + 22, 1012), (CX + fx + 20, 1092),
                       (CX + fx + 2, 1096)], rgba("#c99a68", 0.9), smooth=True))
        S.append(seg((CX + fx + 22, 1016), (CX + fx + 20, 1088), rgba("#8a6038", 0.5), w=2, opacity=0.6))
    S.append(blob([(CX + 60, 1040), (CX + 140, 1035), (CX + 150, 1080), (CX + 70, 1100)],
                  lin([("#d3a570", 0), ("#9a6f45", 1)], angle=160), smooth=True))  # crossing hand
    return S


# --------------------------------------------------------------------------- #
#  layer 3 — the construction overlay (sanguine, semi-transparent) + labels
# --------------------------------------------------------------------------- #
def construction():
    S = []
    ap = (CX, 250)                         # pyramid apex (head)
    bl, br = (206, 1180), (W - 206, 1180)  # base corners (folded hands / lap)
    # pyramidal composition
    S.append(linepoly([bl, ap, br], SAN, w=1.6, opacity=0.8))
    S.append(seg(bl, br, SAN, w=1.2, dash=(7, 6), opacity=0.6))
    # turned vertical axis (slightly off vertical — the head turns)
    S.append(seg((CX + 26, 250), (CX - 10, 520), SAN, w=1.3, dash=(6, 5), opacity=0.85))
    # skull oval + face proportion guides
    S.append(ring(CX, 372, 96, 122, SAN, w=1.4, opacity=0.85))
    for gy, tag in ((357, "eye line — ½ of the head"),
                    (432, "base of the nose"),
                    (474, "band of the mouth")):
        S.append(seg((CX - 150, gy), (CX + 150, gy), SAN, w=1.1, dash=(5, 5), opacity=0.8))
    S.append(seg((CX - 150, 262), (CX + 150, 262), SAN, w=1.0, dash=(4, 5), opacity=0.6))  # hairline
    # eye centres + the perspective note (far eye narrower)
    for ex in (-40, 40):
        S.append(ring(CX + ex, 357, 12, 9, SAN, w=1.0, opacity=0.7))
    # contrapposto spiral — shoulder rotation arrows around the central column
    S.append(linepoly([(300, 660), (CX, 596), (676, 648)], SAN, w=1.2, smooth=True, opacity=0.75))
    S.append(linepoly([(360, 690), (400, 645), (452, 660)], SAN, w=1.2, smooth=True, opacity=0.7))
    S.append(linepoly([(560, 660), (610, 646), (650, 686)], SAN, w=1.2, smooth=True, opacity=0.7))
    # finger cylinders on the hands
    for fx in (-70, -34, 2, 40):
        S.append(ring(CX + fx + 11, 1012, 12, 6, SAN, w=1.0, opacity=0.7))
        S.append(seg((CX + fx, 1012), (CX + fx, 1092), SAN, w=0.9, dash=(3, 4), opacity=0.6))
        S.append(seg((CX + fx + 22, 1014), (CX + fx + 20, 1090), SAN, w=0.9, dash=(3, 4), opacity=0.6))
    # eye-travel loop (face -> hands -> garment -> landscape -> face)
    S.append(ring(CX, 720, 250, 470, SAN, w=1.0, dash=(2, 8), opacity=0.4))
    return S


def annotations():
    S = []
    def leader(a, b):
        return seg(a, b, SAN, w=0.9, opacity=0.6)
    items = [
        ((44, 250), (206, 260), "PYRAMIDAL COMPOSITION\nbroad base, narrow apex", 15, True),
        ((44, 372), (CX - 96, 372), "the skull as an oval —\nfeatures grown from a volume", 14, False),
        ((44, 357), (CX - 150, 357), "eye line at the half", 13, False),
        ((44, 470), (CX - 150, 474), "the smile: no contour,\nderived from gradients", 14, False),
        ((690, 300), (CX + 96, 320), "sfumato — the edge is\nlost into atmosphere", 14, False),
        ((690, 560), (760, 470), "atmospheric perspective:\nfar = cooler, lighter, softer", 14, False),
        ((646, 1152), (CX + 132, 1086), "hands = cylinders;\noverlap makes depth", 14, True),
        ((44, 636), (300, 636), "contrapposto —\na quiet spiral of volumes", 14, False),
    ]
    for (lx, ly), (ax, ay), text, size, head in items:
        S.append(leader((lx + (300 if lx < 400 else 0), ly), (ax, ay)))
        col = SAN if head else "#33291e"
        for i, line in enumerate(text.split("\n")):
            S.append(label(lx, ly + i * (size + 4), line, size=size,
                           color=col, weight=700 if (head and i == 0) else 400,
                           italic=not head, align="left"))
    # title / colophon
    S.append(label(44, 60, "ANATOMY OF THE MONA LISA", size=30, color="#2c2318", weight=700, w=700))
    S.append(label(44, 96, "geometry becoming presence — the construction beneath the sfumato",
                   size=16, color="#5e4a30", italic=True, w=760))
    S.append(label(44, H - 54, "Constructed with the FrameGraph SDK · after Leonardo",
                   size=13, color="#cabb97", italic=True, w=760))
    return S


def build_builder():
    b = DocumentBuilder(title="Anatomy of the Mona Lisa — construction plate (FrameGraph)")
    page = b.page("mona-lisa", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    layer = page.layer("plate")
    for group in (landscape(), figure(), construction(), annotations()):
        layer.extend(group)
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from framegraph.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "mona_lisa_construction.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}")
