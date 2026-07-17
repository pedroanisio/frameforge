"""Anatomy of the Mona Lisa — a construction plate (FrameForge SDK).

Renders the essay's thesis: the portrait is *constructed* before it is painted.
A stylized sfumato figure (earth palette, gradient modelling, atmospheric-
perspective landscape) sits under a semi-transparent sanguine overlay of the
invisible geometry — the pyramidal composition, the skull oval, the turned
vertical axis, the eye/nose/mouth proportion guides, the contrapposto spiral,
and the cylinders of the folded hands — each annotated in a serif hand.

The proportions are landmark-driven: feature positions were measured off the
reference painting with the MCP `measure_image` tool (1057x1600 source) and
mapped to this canvas — a longer face, eyes on the half-line, hands left of the
face axis, and the painting's famous mismatched horizon.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import DocumentBuilder, Path, linear_gradient, radial_gradient, rgba  # noqa: E402

W, H = 980.0, 1400.0     # ~0.70 — close to the Mona Lisa's 0.66 trim
SAN = "#a83f28"          # sanguine construction ink
SERIF = ["Georgia", "Times New Roman", "serif"]

# --- landmark-derived geometry (normalized reads x canvas) ------------------ #
CX = 476.0               # face axis (0.485 W) — a touch left of centre
CROWN, HAIRLINE = 150.0, 236.0
EYE_Y, NOSE_Y, MOUTH_Y, CHIN_Y = 336.0, 430.0, 500.0, 566.0
FACE_CY = (CROWN + CHIN_Y) / 2       # 358
FACE_RY = (CHIN_Y - CROWN) / 2       # 208
FACE_RX = 127.0
EYE_DX = 62.0                         # eyes at CX +/- 62
SHO_Y = 690.0                         # shoulder line (~0.49 H)
HANDS_CX, HANDS_CY = 402.0, 1180.0   # hands centred LEFT of the face axis
HZ_L, HZ_R = 690.0, 610.0            # mismatched horizon (left lower, right higher)


def rect(box, fill, **k):
    return {"type": "rect", "box": [float(v) for v in box], "fill": fill, "decorative": True, **k}


def ell(cx, cy, rx, ry, **k):
    return {"type": "ellipse", "center": [float(cx), float(cy)], "rx": float(rx), "ry": float(ry),
            "decorative": True, **k}


def blob(pts, fill, opacity=None, smooth=True, **k):
    g = Path().through([(float(x), float(y)) for x, y in pts]); g.close()
    f = {"fill": fill, "decorative": True, **k}
    if opacity is not None:
        f["opacity"] = opacity
    return g.object(**f)


def linepoly(pts, stroke, w=1.2, dash=None, opacity=None, closed=False, smooth=False):
    ss = {"stroke_width": w}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    if smooth:
        g = Path().through([(float(x), float(y)) for x, y in pts])
        if closed:
            g.close()
        o = g.object(stroke=stroke, stroke_style=ss, fill="none", decorative=True)
        if opacity is not None:
            o["opacity"] = opacity
        return o
    o = {"type": "polyline", "points": [[float(x), float(y)] for x, y in pts],
         "stroke": stroke, "stroke_style": ss, "fill": "none", "decorative": True}
    if closed:
        o["closed"] = True
    if opacity is not None:
        o["opacity"] = opacity
    return o


def seg(a, b, stroke, w=1.2, dash=None, opacity=0.85):
    return linepoly([a, b], stroke, w=w, dash=dash, opacity=opacity)


def ring(cx, cy, rx, ry, stroke, w=1.2, dash=None, opacity=0.85):
    ss = {"stroke_width": w}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    return ell(cx, cy, rx, ry, fill="none", stroke=stroke, stroke_style=ss, opacity=opacity)


def label(x, y, text, size=17, color="#2c2318", w=340, align="left", weight=400, italic=False):
    st = {"font_family": SERIF, "font_size": size, "color": color, "align": align,
          "vertical_align": "middle"}
    if weight != 400:
        st["font_weight"] = weight
    if italic:
        st["font_style"] = "italic"
    return {"type": "text", "box": [float(x), float(y), float(w), float(size * 1.6)],
            "text": text, "style": st, "decorative": True}


# --------------------------------------------------------------------------- #
#  layer 1 — atmospheric-perspective landscape (mismatched horizon)
# --------------------------------------------------------------------------- #
def landscape():
    S = [rect([0, 0, W, H], linear_gradient(
        [("#8fa0a6", 0), ("#b7b79a", 0.4), ("#cbb98f", 0.58)], angle=180))]
    # far mountains — cool, low-contrast; left side sits lower than the right
    S.append(blob([(0, HZ_L - 40), (150, HZ_L - 140), (330, HZ_L - 70),
                   (560, HZ_R - 130), (760, HZ_R - 40), (W, HZ_R - 120),
                   (W, HZ_R + 40), (0, HZ_L + 40)], "#93a6ab", opacity=0.9))
    S.append(blob([(0, HZ_L - 6), (200, HZ_L - 70), (380, HZ_L - 20),
                   (620, HZ_R - 70), (860, HZ_R - 20), (W, HZ_R - 50),
                   (W, HZ_R + 60), (0, HZ_L + 60)], "#9fa585"))
    # winding river (left, cooler) + a bridge
    S.append(blob([(120, HZ_L + 6), (250, HZ_L - 26), (360, HZ_L + 16), (300, HZ_L + 64),
                   (170, HZ_L + 54), (86, HZ_L + 86)], "#c4cabc", opacity=0.85))
    for i in range(5):
        S.append(rect([250 + i * 15, HZ_L - 30 + i * 1.5, 12, 22], "#8f8266", opacity=0.8))
    # near warm hills flanking the figure
    S.append(blob([(0, HZ_L + 30), (210, HZ_L + 4), (340, HZ_L + 40), (340, 900), (0, 900)],
                  "#7d6a45"))
    S.append(blob([(640, HZ_R + 40), (830, HZ_R - 6), (W, HZ_R + 30), (W, 940), (640, 940)],
                  "#6f5c3b"))
    # balcony parapet + two column bases (the loggia)
    S.append(rect([0, 780, W, 28], "#6a5638"))
    S.append(rect([44, 690, 42, 100], linear_gradient([("#8a7550", 0), ("#5e4a30", 1)], angle=90)))
    S.append(rect([W - 86, 690, 42, 100], linear_gradient([("#5e4a30", 0), ("#8a7550", 1)], angle=90)))
    return S


# --------------------------------------------------------------------------- #
#  layer 2 — the figure (sfumato modelling)
# --------------------------------------------------------------------------- #
def figure():
    S = []
    # garment pyramid (apex below the neck, broad base)
    S.append(blob([(CX, SHO_Y - 6), (200, 1220), (200, H), (W - 200, H), (W - 200, 1220)],
                  linear_gradient([("#4a3826", 0), ("#2a1e12", 1)], angle=180)))
    # veil/shawl across the shoulders
    S.append(blob([(CX, SHO_Y + 10), (300, 1000), (350, 1150), (CX, 1090),
                   (W - 350, 1150), (W - 300, 1000)], rgba("#6a563a", 0.5)))
    for fx in (330, 400, 560, 640):
        S.append(seg((fx, 1000), (fx - 30, 1330), rgba("#1c130a", 0.5), w=6, opacity=0.5))

    # neck (cylinder) with a core shadow to the right
    S.append(blob([(CX - 56, CHIN_Y - 20), (CX + 56, CHIN_Y - 20), (CX + 72, SHO_Y),
                   (CX + 34, SHO_Y + 40), (CX - 34, SHO_Y + 40), (CX - 66, SHO_Y)], "#c79a6c"))
    S.append(blob([(CX + 26, CHIN_Y - 6), (CX + 72, SHO_Y - 30), (CX + 52, SHO_Y + 30),
                   (CX + 14, SHO_Y + 30)], rgba("#7d5636", 0.55), opacity=0.7))

    # hair behind — center-parted, framing the long oval, falling past the shoulders
    S.append(blob([(CX, CROWN - 14), (CX - 150, HAIRLINE + 40), (CX - 172, 620),
                   (CX - 120, 820), (CX - 30, 720), (CX - 8, HAIRLINE)], "#241a12"))
    S.append(blob([(CX, CROWN - 14), (CX + 150, HAIRLINE + 40), (CX + 176, 620),
                   (CX + 124, 820), (CX + 34, 720), (CX + 12, HAIRLINE)], "#20160f"))

    # face base (long oval), light from upper-left
    S.append(ell(CX, FACE_CY, FACE_RX, FACE_RY, fill="#d8b083"))
    S.append(ell(CX - 34, FACE_CY - 46, FACE_RX * 0.74, FACE_RY * 0.62, fill=radial_gradient(
        [(rgba("#f0d7b2", 0.9), 0), (rgba("#f0d7b2", 0.0), 1)])))
    # form shadow down the right cheek / jaw
    S.append(blob([(CX + 34, HAIRLINE + 30), (CX + FACE_RX, FACE_CY), (CX + 78, CHIN_Y - 40),
                   (CX + 12, CHIN_Y - 6), (CX + 26, FACE_CY + 40), (CX + 50, FACE_CY - 30)],
                  rgba("#9a6f45", 0.5), opacity=0.8))
    S.append(blob([(CX - 76, CHIN_Y - 44), (CX + 64, CHIN_Y - 44), (CX + 42, CHIN_Y),
                   (CX - 48, CHIN_Y - 4)], rgba("#8a6038", 0.4), opacity=0.7))   # under-jaw
    S.append(ell(CX - 46, NOSE_Y - 8, 28, 20, fill=radial_gradient(
        [(rgba("#d98a63", 0.5), 0), (rgba("#d98a63", 0.0), 1)])))               # cheek warmth

    # hairline meeting a high forehead (center-parted, no bangs)
    S.append(linepoly([(CX - 108, HAIRLINE + 8), (CX - 52, HAIRLINE - 12), (CX, HAIRLINE - 4),
                       (CX + 52, HAIRLINE - 12), (CX + 108, HAIRLINE + 8)], "#241a12", w=8,
                      smooth=True, opacity=0.9))
    S.append(linepoly([(CX - 152, HAIRLINE), (CX - 96, HAIRLINE - 40), (CX, HAIRLINE - 54),
                       (CX + 96, HAIRLINE - 40), (CX + 152, HAIRLINE)], rgba("#d8cdb0", 0.5),
                      w=3, smooth=True, opacity=0.5))     # sheer veil

    # eyes — hooded; the far (left-in-image) eye slightly narrower (the head turns)
    S.append(blob([(CX - 64, EYE_Y), (CX - 40, EYE_Y - 9), (CX - 16, EYE_Y),
                   (CX - 40, EYE_Y + 9)], "#efe7d6"))
    S.append(blob([(CX + 22, EYE_Y + 1), (CX + 42, EYE_Y - 7), (CX + 60, EYE_Y + 1),
                   (CX + 42, EYE_Y + 8)], "#e7ddc9"))
    S.append(ell(CX - 40, EYE_Y + 1, 8, 9, fill="#3a2716"))
    S.append(ell(CX + 42, EYE_Y + 1, 7, 8, fill="#3a2716"))
    for ex in (-40, 42):
        S.append(linepoly([(CX + ex - 17, EYE_Y - 6), (CX + ex, EYE_Y - 12),
                           (CX + ex + 17, EYE_Y - 6)], rgba("#6e4c2c", 0.6), w=2.4,
                          smooth=True, opacity=0.7))
    # nose — central ridge lit, soft shadow right, nostril hint
    S.append(blob([(CX - 6, EYE_Y + 6), (CX + 6, EYE_Y + 6), (CX + 22, NOSE_Y),
                   (CX - 2, NOSE_Y + 12), (CX - 20, NOSE_Y - 2)], rgba("#b07f4f", 0.4), opacity=0.7))
    S.append(ell(CX + 12, NOSE_Y + 2, 5, 3.5, fill=rgba("#7d5636", 0.5)))
    # mouth — the smile: a soft asymmetric band of shadow, no hard contour
    S.append(blob([(CX - 42, MOUTH_Y), (CX, MOUTH_Y - 4), (CX + 44, MOUTH_Y - 2),
                   (CX + 22, MOUTH_Y + 12), (CX, MOUTH_Y + 14), (CX - 24, MOUTH_Y + 12)],
                  rgba("#8a4f38", 0.55), opacity=0.8))
    S.append(linepoly([(CX - 42, MOUTH_Y), (CX - 10, MOUTH_Y + 4), (CX + 22, MOUTH_Y + 2),
                       (CX + 44, MOUTH_Y - 4)], rgba("#5e3220", 0.6), w=2.2, smooth=True, opacity=0.7))
    S.append(ell(CX - 42, MOUTH_Y, 5, 4, fill=rgba("#c98a63", 0.5)))            # lifted-cheek corner

    # folded hands (foreground), centred LEFT of the face axis; fingers point right
    hx, hy = HANDS_CX, HANDS_CY
    S.append(blob([(hx - 120, hy - 60), (hx - 20, hy - 80), (hx + 96, hy - 66), (hx + 138, hy),
                   (hx + 64, hy + 46), (hx - 70, hy + 46), (hx - 130, hy)],
                  linear_gradient([("#e0b385", 0), ("#b07f50", 1)], angle=160)))
    for i, fx in enumerate((-70, -34, 2, 40)):
        S.append(blob([(hx + fx, hy - 66), (hx + fx + 22, hy - 64), (hx + fx + 20, hy + 16),
                       (hx + fx + 2, hy + 20)], rgba("#c99a68", 0.92)))
        S.append(seg((hx + fx + 22, hy - 60), (hx + fx + 20, hy + 12), rgba("#8a6038", 0.5),
                     w=2, opacity=0.6))
    S.append(blob([(hx + 64, hy - 40), (hx + 148, hy - 44), (hx + 158, hy), (hx + 78, hy + 20)],
                  linear_gradient([("#d3a570", 0), ("#9a6f45", 1)], angle=160)))  # crossing hand
    # gathered sleeve behind the hands (ochre)
    S.append(blob([(hx - 150, hy + 10), (hx - 100, hy - 60), (hx + 20, hy - 20), (hx + 40, hy + 90),
                   (hx - 70, hy + 150), (hx - 170, hy + 110)],
                  linear_gradient([("#9a6f34", 0), ("#5f451f", 1)], angle=120)))
    return S


# --------------------------------------------------------------------------- #
#  layer 3 — the construction overlay (sanguine) + annotations
# --------------------------------------------------------------------------- #
def construction():
    S = []
    ap = (CX, CROWN - 4)
    bl, br = (206, H - 150), (W - 206, H - 150)
    S.append(linepoly([bl, ap, br], SAN, w=1.6, opacity=0.8))                    # pyramid
    S.append(seg(bl, br, SAN, w=1.2, dash=(7, 6), opacity=0.6))
    S.append(seg((CX + 26, CROWN), (CX - 10, CHIN_Y + 30), SAN, w=1.3, dash=(6, 5), opacity=0.85))  # turned axis
    S.append(ring(CX, FACE_CY, FACE_RX, FACE_RY, SAN, w=1.4, opacity=0.85))      # skull oval
    for gy in (EYE_Y, NOSE_Y, MOUTH_Y):                                         # feature guides
        S.append(seg((CX - 160, gy), (CX + 160, gy), SAN, w=1.1, dash=(5, 5), opacity=0.8))
    S.append(seg((CX - 160, HAIRLINE), (CX + 160, HAIRLINE), SAN, w=1.0, dash=(4, 5), opacity=0.55))
    for ex in (-EYE_DX, EYE_DX):
        S.append(ring(CX + ex, EYE_Y, 13, 9, SAN, w=1.0, opacity=0.7))
    # contrapposto — shoulder rotation around the central column
    S.append(linepoly([(300, SHO_Y + 40), (CX, SHO_Y - 30), (676, SHO_Y + 26)], SAN, w=1.2,
                      smooth=True, opacity=0.75))
    # finger cylinders on the hands
    for fx in (-70, -34, 2, 40):
        S.append(ring(HANDS_CX + fx + 11, HANDS_CY - 64, 12, 6, SAN, w=1.0, opacity=0.7))
        S.append(seg((HANDS_CX + fx, HANDS_CY - 64), (HANDS_CX + fx, HANDS_CY + 16), SAN,
                     w=0.9, dash=(3, 4), opacity=0.6))
        S.append(seg((HANDS_CX + fx + 22, HANDS_CY - 62), (HANDS_CX + fx + 20, HANDS_CY + 14),
                     SAN, w=0.9, dash=(3, 4), opacity=0.6))
    # eye-travel loop
    S.append(ring(CX - 20, 800, 250, 470, SAN, w=1.0, dash=(2, 8), opacity=0.4))
    return S


def annotations():
    S = []
    items = [
        ((44, CROWN + 20), (206, CROWN + 40), "PYRAMIDAL COMPOSITION\nbroad base, narrow apex", 15, True),
        ((44, FACE_CY - 10), (CX - FACE_RX, FACE_CY), "the skull as a long oval —\nfeatures grown from a volume", 14, False),
        ((44, EYE_Y), (CX - 160, EYE_Y), "eye line on the half", 13, False),
        ((44, MOUTH_Y + 6), (CX - 160, MOUTH_Y), "the smile: no contour,\nderived from gradients", 14, False),
        ((690, HAIRLINE + 30), (CX + FACE_RX, FACE_CY - 30), "sfumato — the edge is\nlost into atmosphere", 14, False),
        ((690, HZ_R + 30), (830, HZ_R - 40), "atmospheric perspective;\nthe two horizons disagree", 14, False),
        ((646, HANDS_CY + 40), (HANDS_CX + 150, HANDS_CY), "hands = cylinders;\noverlap makes depth", 14, True),
        ((44, SHO_Y + 30), (300, SHO_Y + 30), "contrapposto —\na quiet spiral of volumes", 14, False),
    ]
    for (lx, ly), (ax, ay), text, size, head in items:
        S.append(seg((lx if lx < 400 else lx, ly), (ax, ay), SAN, w=0.9, opacity=0.55))
        col = SAN if head else "#33291e"
        for i, line in enumerate(text.split("\n")):
            S.append(label(lx, ly + i * (size + 4), line, size=size, color=col,
                           weight=700 if (head and i == 0) else 400, italic=not head))
    S.append(label(44, 58, "ANATOMY OF THE MONA LISA", size=30, color="#2c2318", weight=700, w=760))
    S.append(label(44, 94, "geometry becoming presence — proportions measured from the painting",
                   size=16, color="#5e4a30", italic=True, w=820))
    S.append(label(44, H - 46, "Constructed with the FrameForge SDK · landmarks via measure_image · after Leonardo",
                   size=13, color="#cabb97", italic=True, w=860))
    return S


def build_builder():
    b = DocumentBuilder(title="Anatomy of the Mona Lisa — construction plate (FrameForge)")
    page = b.page("mona-lisa", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    layer = page.layer("plate")
    for group in (landscape(), figure(), construction(), annotations()):
        layer.extend(group)
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from frameforge.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "mona_lisa_construction.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}")
