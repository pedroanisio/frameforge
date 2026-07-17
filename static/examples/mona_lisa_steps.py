"""How to Draw the Mona Lisa — step by step (FrameForge SDK).

Follows the beginner method from the "Warehouse of Ideas / drawingtutorials101"
guide, panel by panel: (1) baseline + head oval + facial guideline cross,
(2) eyes on the reference line, (3) nose and the smile, (4) face contour and
wavy hair, (5) body oval + shoulders + folded hands, (6) finish with tone.

A pencil-construction style: light-blue guide lines, graphite feature lines, and
soft grey shading on the final panel. Proportions reuse the landmarks measured
from the painting (eyes on the half-line, long oval, hands left of the axis).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import DocumentBuilder, Path, rgba  # noqa: E402

W, H = 1440.0, 1040.0
GC = "#a7bccd"          # pencil guideline (light blue)
GD = "#413a30"          # graphite feature line
INK = "#2c2620"
SERIF = ["Georgia", "Times New Roman", "serif"]
SANS = ["Helvetica", "Arial", "sans-serif"]


def rect(box, **k):
    return {"type": "rect", "box": [float(v) for v in box], "decorative": True, **k}


def ell(cx, cy, rx, ry, **k):
    return {"type": "ellipse", "center": [float(cx), float(cy)], "rx": float(rx), "ry": float(ry),
            "decorative": True, **k}


def stroke_ell(cx, cy, rx, ry, color, w=1.4, dash=None, opacity=1.0):
    ss = {"stroke_width": w}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    return ell(cx, cy, rx, ry, fill="none", stroke=color, stroke_style=ss, opacity=opacity)


def line(pts, color, w=1.6, dash=None, opacity=1.0, smooth=False, closed=False, fill="none"):
    ss = {"stroke_width": w}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    if smooth:
        g = Path().through([(float(x), float(y)) for x, y in pts])
        if closed:
            g.close()
        o = g.object(stroke=color, stroke_style=ss, fill=fill, decorative=True)
        o["opacity"] = opacity
        return o
    o = {"type": "polyline", "points": [[float(x), float(y)] for x, y in pts],
         "stroke": color, "stroke_style": ss, "fill": fill, "decorative": True, "opacity": opacity}
    if closed:
        o["closed"] = True
    return o


def fillblob(pts, fill, opacity=1.0):
    g = Path().through([(float(x), float(y)) for x, y in pts]); g.close()
    return g.object(fill=fill, decorative=True, opacity=opacity)


def text(x, y, s, size, color, w=460, align="left", weight=400, fam=SANS, italic=False):
    st = {"font_family": fam, "font_size": size, "color": color, "align": align, "vertical_align": "middle"}
    if weight != 400:
        st["font_weight"] = weight
    if italic:
        st["font_style"] = "italic"
    return {"type": "text", "box": [float(x), float(y), float(w), float(size * 1.6)],
            "text": s, "style": st, "decorative": True}


# --------------------------------------------------------------------------- #
#  the figure at a given step (cumulative), drawn into a panel
# --------------------------------------------------------------------------- #
def figure(cx, top, step):
    """Draw the construction up to `step` (1..6). Feature proportions reuse the
    painting's measured ratios: eyes on the half-line of a long head oval."""
    S = []
    HC = top + 96                        # head-oval centre
    RX, RY = 60.0, 82.0
    crown, chin = HC - RY, HC + RY
    hairline = HC - 52
    eye_y, nose_y, mouth_y = HC - 6, HC + 42, HC + 64
    base_y = top + 360                   # the horizontal baseline (guide step 1)
    sho_y = HC + 126
    hcx, hcy = cx - 22, HC + 236         # folded hands, left of the axis
    final = step >= 6
    gc = rgba(GC, 0.5) if final else GC   # guides fade on the finished panel

    # -- finished shading sits UNDER the linework --
    if final:
        S.append(fillblob([(cx, crown - 8), (cx - RX - 30, hairline + 20), (cx - RX - 26, sho_y),
                           (cx - 30, sho_y + 20), (cx - 8, hairline)], "#5b5048"))   # hair L
        S.append(fillblob([(cx, crown - 8), (cx + RX + 30, hairline + 20), (cx + RX + 26, sho_y),
                           (cx + 30, sho_y + 20), (cx + 8, hairline)], "#514740"))   # hair R
        S.append(ell(cx, HC, RX, RY, fill="#e8d3ba"))                                # face
        # soft shadow hugging the right cheek/jaw (sfumato), not a diagonal slash
        S.append(fillblob([(cx + 30, eye_y + 4), (cx + RX - 4, HC + 6), (cx + RX - 12, chin - 22),
                           (cx + 24, chin - 10), (cx + 34, mouth_y), (cx + 40, HC)],
                          rgba("#c39a70", 0.32)))                                     # cheek shadow
        S.append(fillblob([(cx, sho_y - 8), (cx - 150, base_y + 18), (cx + 150, base_y + 18)],
                          "#3f3630"))                                                # garment
        S.append(fillblob([(hcx - 96, hcy - 44), (hcx + 78, hcy - 40), (hcx + 108, hcy + 8),
                           (hcx + 40, hcy + 40), (hcx - 78, hcy + 36)], "#d9b48c"))  # hands

    # -- step 1: baseline, head oval, facial cross --
    if step >= 1:
        S.append(line([(cx - 210, base_y), (cx + 210, base_y)], gc, w=1.3, dash=(6, 5), opacity=0.9))
        S.append(stroke_ell(cx, HC, RX, RY, gc, w=1.4, opacity=0.95))
        S.append(line([(cx, crown - 6), (cx, chin + 60)], gc, w=1.1, dash=(5, 5), opacity=0.9))
        for gy in (eye_y, nose_y, mouth_y):
            S.append(line([(cx - RX - 14, gy), (cx + RX + 14, gy)], gc, w=1.0, dash=(4, 5), opacity=0.85))
        S.append(line([(cx - RX - 14, hairline), (cx + RX + 14, hairline)], gc, w=1.0, dash=(3, 5), opacity=0.6))

    # -- step 2: eyes on the reference line --
    if step >= 2:
        for ex, w2 in ((-30, 22), (30, 20)):
            S.append(line([(cx + ex - w2, eye_y), (cx + ex, eye_y - 8), (cx + ex + w2, eye_y),
                           (cx + ex, eye_y + 7), (cx + ex - w2, eye_y)], GD, w=1.6, smooth=True))
            S.append(ell(cx + ex, eye_y, 5.5, 6, fill=GD if step >= 3 else "none",
                         stroke=GD, stroke_style={"stroke_width": 1.4}))

    # -- step 3: nose and the smile --
    if step >= 3:
        S.append(line([(cx - 4, eye_y + 8), (cx - 8, nose_y - 8), (cx - 16, nose_y),
                       (cx - 2, nose_y + 6), (cx + 12, nose_y)], GD, w=1.5, smooth=True))
        S.append(line([(cx - 34, mouth_y), (cx - 6, mouth_y + 5), (cx + 24, mouth_y + 3),
                       (cx + 40, mouth_y - 4)], GD, w=1.7, smooth=True))          # the smile (up-curve)
        S.append(line([(cx - 30, mouth_y - 9), (cx, mouth_y - 6), (cx + 34, mouth_y - 10)],
                      rgba(GD, 0.7), w=1.2, smooth=True))                          # upper lip

    # -- step 4: face contour + wavy hair --
    if step >= 4:
        S.append(line([(cx - RX + 2, hairline + 6), (cx - RX - 2, HC + 20), (cx - 42, chin - 6),
                       (cx, chin + 2), (cx + 42, chin - 6), (cx + RX + 2, HC + 20),
                       (cx + RX - 2, hairline + 6)], GD, w=1.8, smooth=True))       # jaw/chin
        # center-parted hair, wavy at the ends
        S.append(line([(cx, crown - 4), (cx - 40, hairline - 8), (cx - RX - 22, hairline + 30),
                       (cx - RX - 26, sho_y - 40), (cx - RX - 6, sho_y + 6), (cx - RX - 30, sho_y + 30)],
                      GD, w=1.8, smooth=True))
        S.append(line([(cx, crown - 4), (cx + 40, hairline - 8), (cx + RX + 22, hairline + 30),
                       (cx + RX + 26, sho_y - 40), (cx + RX + 6, sho_y + 6), (cx + RX + 30, sho_y + 30)],
                      GD, w=1.8, smooth=True))
        S.append(line([(cx - RX - 10, hairline + 4), (cx, hairline - 2), (cx + RX + 10, hairline + 4)],
                      GD, w=1.4, smooth=True))                                      # part

    # -- step 5: body oval + shoulders + folded hands --
    if step >= 5:
        S.append(line([(cx - 30, chin + 2), (cx - 34, sho_y - 10)], GD, w=1.6))     # neck
        S.append(line([(cx + 30, chin + 2), (cx + 34, sho_y - 10)], GD, w=1.6))
        S.append(line([(cx - 150, base_y + 20), (cx - 60, sho_y), (cx, sho_y - 14),
                       (cx + 60, sho_y), (cx + 150, base_y + 20)], GD, w=1.8, smooth=True))  # shoulders
        # folded hands: outline + finger cylinders
        S.append(line([(hcx - 96, hcy - 44), (hcx + 6, hcy - 58), (hcx + 78, hcy - 40),
                       (hcx + 108, hcy + 8), (hcx + 40, hcy + 40), (hcx - 78, hcy + 36),
                       (hcx - 118, hcy)], GD, w=1.7, smooth=True, closed=True))
        for fx in (-52, -26, 0, 26):
            S.append(line([(hcx + fx, hcy - 44), (hcx + fx, hcy + 18)], GD, w=1.2, opacity=0.8))
        S.append(line([(hcx + 46, hcy - 30), (hcx + 104, hcy - 6)], GD, w=1.2, opacity=0.8))  # crossing hand

    return S


# --------------------------------------------------------------------------- #
#  the 6-panel sheet
# --------------------------------------------------------------------------- #
CAPS = [
    "1 · Guidelines — baseline, head oval, facial cross",
    "2 · Eyes on the reference line",
    "3 · The nose and the smile",
    "4 · Face contour and wavy hair",
    "5 · Body oval, shoulders, folded hands",
    "6 · Finish — tone and shading",
]


def sheet():
    S = [rect([0, 0, W, H], fill="#f0ece2")]
    S.append(text(40, 40, "HOW TO DRAW THE MONA LISA", 30, INK, w=900, weight=700, fam=SERIF))
    S.append(text(40, 74, "step by step, following the guide · built with the FrameForge SDK",
                  15, "#6a5f4e", w=900, italic=True, fam=SERIF))
    mx, top_band, gap = 30.0, 104.0, 28.0
    pw = (W - mx * 2 - gap * 2) / 3
    ph = (H - top_band - 40 - gap) / 2
    for i in range(6):
        col, row = i % 3, i // 3
        px = mx + col * (pw + gap)
        py = top_band + row * (ph + gap)
        S.append(rect([px, py, pw, ph], fill="#fbfaf6", stroke="#d9d3c5",
                      stroke_style={"stroke_width": 1.2}, radius=6))
        S.append(rect([px, py, 30, 30], fill="#e7ae44", radius=6))
        S.append(text(px + 7, py + 15, str(i + 1), 16, "#ffffff", w=24, weight=700, align="center"))
        S += figure(px + pw / 2, py + 14, i + 1)
        S.append(text(px + 14, py + ph - 22, CAPS[i], 12.5, "#4a4130", w=pw - 28, fam=SANS))
    return S


def build_builder():
    b = DocumentBuilder(title="How to Draw the Mona Lisa — step by step (FrameForge)")
    page = b.page("steps", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.layer("sheet").extend(sheet())
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from frameforge.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "mona_lisa_steps.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}")
