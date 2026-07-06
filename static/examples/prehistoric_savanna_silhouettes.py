"""Prehistoric Savanna — 16 silhouette scenes (A4 landscape).

A flat-silhouette, layered-parallax landscape book in the style of a warm
savanna-at-sunset vector illustration, but populated with dinosaurs and swept
through 16 moods: dawn, sunrise, morning, midday, afternoon, golden hour,
sunset, dusk, twilight, moonrise, night, deep night, autumn, winter, storm and
an aurora finale.

Everything is built with the FrameGraph Python SDK and lowers to grammar-native
primitives (rect / ellipse / closed polyline / Catmull-Rom path). Atmospheric
perspective is a single colour lerp from the horizon tint to the foreground
dark, so distant animals read pale/warm and near ones read almost black — as in
the reference art. Placement is collision-aware (per-field occupancy intervals)
so silhouettes stay clean and readable rather than merging into blobs, and a
deterministic LCG keeps every render stable.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import DocumentBuilder, Path, linear_gradient, radial_gradient, rgba  # noqa: E402

W, H = 842.0, 595.0  # A4 landscape, points @72dpi


# --------------------------------------------------------------------------- #
# colour + rng helpers
# --------------------------------------------------------------------------- #
def _rgb(c: str):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(_rgb(a), _rgb(b)))


class R:
    """Tiny deterministic LCG so each page varies but renders identically."""

    def __init__(self, seed: int):
        self.s = seed & 0x7FFFFFFF

    def f(self) -> float:
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF

    def rng(self, a: float, b: float) -> float:
        return a + (b - a) * self.f()

    def pick(self, seq):
        return seq[int(self.f() * len(seq)) % len(seq)]


# --------------------------------------------------------------------------- #
# primitive emitters (raw model dicts)
# --------------------------------------------------------------------------- #
def poly(points, fill, smooth=False, opacity=None):
    fields = {"fill": fill, "decorative": True}
    if opacity is not None:
        fields["opacity"] = opacity
    if smooth:
        g = Path().through([(float(x), float(y)) for x, y in points])
        g.close()
        return g.object(**fields)
    return {"type": "polyline", "closed": True,
            "points": [[float(x), float(y)] for x, y in points], **fields}


def disc(cx, cy, r, fill, ry=None, opacity=None):
    o = {"type": "ellipse", "center": [float(cx), float(cy)], "rx": float(r),
         "ry": float(ry if ry is not None else r), "fill": fill, "decorative": True}
    if opacity is not None:
        o["opacity"] = opacity
    return o


def _place(px, py, s, flip):
    return lambda x, y: (px + flip * s * x, py - s * y)


# --------------------------------------------------------------------------- #
# sky, light, weather
# --------------------------------------------------------------------------- #
def sky(stops):
    return {"type": "rect", "box": [0, 0, W, H], "decorative": True,
            "fill": linear_gradient(stops, angle=180)}


def orb(kind, cx, cy, r, color):
    glow = radial_gradient([(color, 0.0), (rgba(color, 0.32), 0.4), (rgba(color, 0.0), 1.0)])
    return [disc(cx, cy, r * 4.4, glow), disc(cx, cy, r, color)]


def stars(rr, n, y_max, tint):
    return [disc(rr.rng(0, W), rr.rng(6, y_max), rr.rng(0.5, 1.7), tint,
                 opacity=rr.rng(0.35, 1.0)) for _ in range(n)]


def aurora(rr, colors):
    out = []
    for k in range(len(colors) * 2):
        c = colors[k % len(colors)]
        x0, w = rr.rng(-60, W), rr.rng(70, 150)
        top, bot, sway = rr.rng(-10, 40), rr.rng(180, 300), rr.rng(-40, 40)
        g = linear_gradient([(rgba(c, 0.0), 0.0), (rgba(c, 0.5), 0.5), (rgba(c, 0.0), 1.0)], angle=180)
        out.append(poly([(x0, top), (x0 + w, top), (x0 + w + sway, bot), (x0 + sway, bot)], g, opacity=0.7))
    return out


def clouds(rr, color):
    out = []
    for _ in range(rr.pick([2, 3, 3, 4])):
        cx, cy = rr.rng(60, W - 60), rr.rng(40, 150)
        w, h = rr.rng(90, 200), rr.rng(10, 22)
        out.append(poly([(cx - w, cy), (cx - w * 0.4, cy - h), (cx + w * 0.3, cy - h * 0.7),
                         (cx + w, cy), (cx + w * 0.3, cy + h * 0.5), (cx - w * 0.5, cy + h * 0.4)],
                        color, smooth=True, opacity=rr.rng(0.25, 0.5)))
    return out


def crest(baseline, amp, seed):
    n = 16
    return [(-60 + (W + 120) * i / n,
             baseline - amp * (0.55 * math.sin(i * 0.8 + seed) + 0.45 * math.sin(i * 0.33 + seed * 1.7)))
            for i in range(n + 1)]


def band(baseline, amp, color, seed):
    return poly(crest(baseline, amp, seed) + [(W + 60, H + 90), (-60, H + 90)], color, smooth=True)


def grass(y, x0, x1, color, s, rr):
    """Clumped tufts of 2-4 curved blades — softer than uniform spikes."""
    out = []
    x = x0
    while x < x1:
        blades = rr.pick([1, 2, 2, 3])
        for _ in range(blades):
            bx = x + rr.rng(-s * 0.4, s * 0.4)
            h = rr.rng(s * 0.8, s * 2.0)
            lean = rr.rng(-s * 0.5, s * 0.5)
            wj = s * 0.16
            out.append(poly([(bx - wj, y + 2), (bx + wj, y + 2),
                             (bx + lean * 0.5, y - h * 0.6), (bx + lean, y - h)], color, smooth=True))
        x += rr.rng(s * 1.8, s * 3.0)
    return out


# --------------------------------------------------------------------------- #
# trees
# --------------------------------------------------------------------------- #
def acacia(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    trunk = poly([P(-0.05, 0), P(0.05, 0), P(0.09, 1.7), P(-0.02, 1.74)], color)
    branch = poly([P(0.02, 1.35), P(-0.85, 1.98), P(-0.02, 1.72), P(0.9, 1.98), P(0.05, 1.5)], color)
    # flat, wide umbrella crown — much wider than tall so it never reads as a mushroom cap
    canopy = poly([P(-1.75, 1.98), P(-0.85, 2.12), P(0.2, 2.15), P(1.2, 2.07), P(1.75, 1.9),
                   P(0.85, 1.86), P(-0.35, 1.86), P(-1.15, 1.9)], color, smooth=True)
    return [trunk, branch, canopy]


def roundtree(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    trunk = poly([P(-0.08, 0), P(0.08, 0), P(0.1, 1.1), P(-0.1, 1.15)], color)
    canopy = poly([P(-0.86, 1.1), P(-0.72, 1.7), P(-0.3, 2.05), P(0.3, 2.08), P(0.78, 1.78),
                   P(0.9, 1.2), P(0.5, 0.92), P(-0.5, 0.92)], color, smooth=True)
    return [trunk, canopy]


def pine(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = [poly([P(-0.07, 0), P(0.07, 0), P(0.07, 0.45), P(-0.07, 0.45)], color)]
    for yb, yt, w in [(0.3, 1.15, 0.78), (0.85, 1.7, 0.56), (1.35, 2.3, 0.34)]:
        out.append(poly([P(-w, yb), P(0, yt), P(w, yb)], color))
    return out


def frame_tree(right, s, color):
    fx = W if right else 0.0
    flip = -1 if right else 1
    P = _place(fx, 0, s, flip)
    out = [poly([P(0.1, -0.3), P(0.2, -0.9), P(1.9, -1.7), P(3.4, -1.3),
                 P(2.0, -1.9), P(0.55, -1.6), P(0.3, -0.9)], color, smooth=True),
           poly([P(-0.4, 0.4), P(0.6, -0.2), P(2.1, -0.6), P(3.6, -1.1), P(3.9, -2.1),
                 P(2.4, -2.7), P(0.9, -2.4), P(0.1, -1.6), P(-0.4, -0.6)], color, smooth=True)]
    rr = R(7 if right else 11)
    for _ in range(7):
        hx, top, ln = rr.rng(0.5, 3.4), rr.rng(-1.6, -0.6), rr.rng(0.8, 2.6)
        out.append(poly([P(hx, top), P(hx + 0.02, top), P(hx + 0.05, top + ln), P(hx - 0.05, top + ln)], color))
    return out


# --------------------------------------------------------------------------- #
# dinosaurs  (defined silhouettes; y-up local frame, feet on baseline, +x = forward)
# --------------------------------------------------------------------------- #
def _legs(P, hips, color, top, w, foot=0.0):
    out = []
    for h in hips:
        out.append(poly([P(h - w, top), P(h + w, top), P(h + w * 0.6 + foot, 0), P(h - w * 0.6, 0)], color))
    return out


def _biped_leg(P, hx, color, hip):
    return [poly([P(hx - 0.24, hip), P(hx + 0.17, hip), P(hx + 0.24, hip * 0.5), P(hx - 0.15, hip * 0.5)], color),
            poly([P(hx + 0.02, hip * 0.55), P(hx + 0.23, hip * 0.5), P(hx + 0.16, 0.05), P(hx - 0.02, 0.05)], color),
            poly([P(hx - 0.06, 0.12), P(hx + 0.36, 0.0), P(hx - 0.08, 0.0)], color)]


def sauropod(px, py, s, color, flip=1, baby=False):
    if baby:
        s *= 0.44
    P = _place(px, py, s, flip)
    out = _legs(P, [0.6, 0.34, -0.2, -0.66], color, 0.74, 0.15)
    body = [(-1.55, 0.6), (-1.0, 0.84), (-0.35, 1.0), (0.22, 1.02), (0.5, 1.08), (0.66, 1.55),
            (0.8, 2.02), (0.94, 2.34), (1.08, 2.48), (1.3, 2.52), (1.46, 2.4), (1.52, 2.28),
            (1.3, 2.22), (1.08, 2.14), (0.96, 1.88), (0.86, 1.4), (0.74, 0.96), (0.5, 0.74),
            (-0.2, 0.68), (-0.9, 0.66), (-1.24, 0.56)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    out.append(poly([P(-1.24, 0.56), P(-2.0, 0.68), P(-2.62, 0.74), P(-2.05, 0.5), P(-1.24, 0.4)],
                    color, smooth=True))
    return out


def trex(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _biped_leg(P, 0.24, color, 1.18)                       # far leg
    out.append(poly([P(-1.15, 0.72), P(-2.05, 0.94), P(-2.9, 0.96), P(-2.1, 0.68), P(-1.15, 0.52)],
                    color, smooth=True))                          # tail
    body = [(-1.15, 0.72), (-0.5, 0.86), (0.2, 0.98), (0.66, 1.2), (0.78, 1.55), (0.72, 1.86),
            (0.82, 2.08), (1.12, 2.24), (1.5, 2.24), (1.66, 2.06), (1.68, 1.9), (1.4, 1.84),
            (1.62, 1.72), (1.28, 1.66), (1.06, 1.6), (0.98, 1.3), (0.9, 0.98), (0.64, 0.74),
            (0.1, 0.66), (-0.6, 0.66)]
    out.append(poly([P(*p) for p in body], color, smooth=True))  # body + big head + jaw
    out.append(poly([P(0.6, 1.12), P(0.86, 1.02), P(0.74, 0.82)], color))   # tiny arm
    out += _biped_leg(P, 0.46, color, 1.22)                      # near leg
    return out


def stegosaurus(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _legs(P, [-0.62, -0.34], color, 0.66, 0.15)            # taller back legs
    out += _legs(P, [0.32, 0.58], color, 0.5, 0.13)              # shorter front legs
    out.append(poly([P(-1.15, 0.5), P(-1.9, 0.62), P(-2.35, 0.66), P(-1.85, 0.44), P(-1.15, 0.38)],
                    color, smooth=True))                          # tail
    for i in range(4):                                            # thagomizer spikes
        a = -1.7 - i * 0.02
        out.append(poly([P(a, 0.6 + i * 0.05), P(a - 0.28, 0.78 + i * 0.08), P(a + 0.06, 0.5 + i * 0.05)], color))
    body = [(-1.2, 0.52), (-0.55, 0.72), (-0.1, 1.05), (0.45, 1.18), (0.95, 1.02), (1.28, 0.82),
            (1.5, 0.82), (1.62, 0.92), (1.68, 0.8), (1.5, 0.66), (1.15, 0.64), (0.6, 0.6),
            (-0.1, 0.56), (-0.7, 0.52)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    for i in range(7):                                            # double-row back plates
        x = -0.7 + i * 0.28
        by = 0.98 + 0.24 * math.cos(x * 1.25)
        h = 0.3 + 0.24 * math.cos(x * 1.35)
        out.append(poly([P(x - 0.15, by), P(x - 0.08, by + h * 0.72), P(x, by + h),
                         P(x + 0.08, by + h * 0.72), P(x + 0.15, by)], color, smooth=True))
    return out


def triceratops(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _legs(P, [0.58, 0.3, -0.4, -0.68], color, 0.62, 0.15)
    out.append(poly([P(-1.2, 0.55), P(-1.85, 0.66), P(-2.2, 0.66), P(-1.8, 0.48), P(-1.2, 0.44)],
                    color, smooth=True))                          # tail
    body = [(-1.3, 0.55), (-0.7, 0.8), (0.0, 0.92), (0.6, 0.92), (0.95, 0.84), (1.12, 0.66),
            (0.9, 0.56), (0.2, 0.55), (-0.5, 0.55), (-1.0, 0.5)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    out.append(poly([P(0.92, 1.35), P(1.2, 1.56), P(1.55, 1.6), P(1.78, 1.42), P(1.78, 0.68),
                     P(1.5, 0.5), P(1.08, 0.56), P(0.95, 0.9)], color, smooth=True))   # frill
    out.append(poly([P(1.6, 1.15), P(2.06, 0.98), P(2.18, 0.78), P(2.02, 0.6), P(1.62, 0.6),
                     P(1.5, 0.9)], color, smooth=True))            # beak/face
    out.append(poly([P(1.66, 1.16), P(2.12, 1.72), P(1.82, 1.12)], color))            # brow horn 1
    out.append(poly([P(1.5, 1.12), P(1.92, 1.62), P(1.68, 1.08)], color))             # brow horn 2
    out.append(poly([P(1.9, 0.98), P(2.12, 1.34), P(2.02, 0.94)], color))             # nose horn
    return out


def parasaur(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _biped_leg(P, 0.42, color, 1.02)
    out.append(poly([P(-0.6, 0.66), P(-1.6, 0.86), P(-2.3, 0.88), P(-1.6, 0.62), P(-0.6, 0.5)],
                    color, smooth=True))                          # tail
    body = [(-0.6, 0.66), (0.0, 0.85), (0.4, 1.12), (0.72, 1.45), (0.66, 1.75), (0.56, 1.92),
            (0.74, 2.0), (1.02, 1.82), (1.28, 1.72), (1.32, 1.56), (1.08, 1.5), (1.0, 1.3),
            (0.92, 1.02), (0.66, 0.78), (0.15, 0.68)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    out.append(poly([P(0.72, 1.92), P(0.42, 2.14), P(0.05, 2.26), P(-0.12, 2.14), P(0.24, 2.0),
                     P(0.56, 1.86)], color, smooth=True))         # signature backward crest
    out.append(poly([P(0.6, 1.05), P(0.84, 0.98), P(0.74, 0.8)], color))   # arm
    out += _biped_leg(P, 0.56, color, 1.06)
    return out


def ankylosaurus(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _legs(P, [0.7, 0.35, -0.4, -0.72], color, 0.32, 0.14)
    out.append(poly([P(-1.2, 0.3), P(-1.9, 0.4), P(-2.15, 0.42), P(-1.9, 0.28)], color, smooth=True))
    out.append(disc(*P(-2.32, 0.44), s * 0.17, color))            # tail club
    body = [(-1.25, 0.3), (-0.6, 0.5), (0.2, 0.62), (1.0, 0.6), (1.45, 0.5), (1.66, 0.5),
            (1.72, 0.4), (1.5, 0.3), (0.9, 0.28), (0.0, 0.26), (-0.7, 0.27)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    for i in range(6):                                            # armour ridge
        x = -0.85 + i * 0.32
        out.append(poly([P(x - 0.1, 0.58), P(x, 0.74), P(x + 0.1, 0.58)], color))
    return out


def pterosaur(cx, cy, s, color, flip=1):
    P = _place(cx, cy, s, flip)
    wing = [(-1.5, 0.06), (-0.75, 0.38), (-0.2, 0.15), (0.0, 0.24), (0.2, 0.15),
            (0.75, 0.38), (1.5, 0.06), (0.6, 0.08), (0.12, -0.06), (-0.12, -0.06), (-0.6, 0.08)]
    return [poly([P(*p) for p in wing], color, smooth=True),
            poly([P(0.05, 0.2), P(0.52, 0.14), P(0.08, 0.04)], color),      # beak
            poly([P(0.03, 0.22), P(-0.24, 0.36), P(0.12, 0.18)], color)]    # head crest


QUADS = [sauropod, stegosaurus, triceratops, ankylosaurus]
BIPEDS = [trex, parasaur]
GROUND = QUADS + BIPEDS
# footprint half-width in local units, for collision spacing
FOOT = {sauropod: 2.4, stegosaurus: 1.9, triceratops: 2.1, ankylosaurus: 2.3,
        trex: 2.6, parasaur: 2.3}


# --------------------------------------------------------------------------- #
# palettes (16 moods)
# --------------------------------------------------------------------------- #
MOON = "#e9edf4"
P = []


def pal(name, stops, horizon, fg, **k):
    d = {"name": name, "stops": stops, "horizon": horizon, "fg": fg, "orb": None,
         "stars": 0, "clouds": False, "snow": False, "leaves": None, "aurora": None,
         "trees": "acacia", "ptero": True}
    d.update(k)
    P.append(d)


pal("Dawn", [("#392a56", 0), ("#7d5a86", .4), ("#c98a86", .72), ("#f0b48a", 1)],
    "#f0b48a", "#241033", orb=("sun", .74, .70, 26, "#ffd7a0"), trees="mixed")
pal("Sunrise", [("#f19a28", 0), ("#f6b83f", .42), ("#f3c65a", .68), ("#d95a2a", 1)],
    "#e06a2c", "#2c0806", orb=("sun", .30, .30, 30, "#ffe9b0"), clouds=True, trees="acacia")
pal("Morning Mist", [("#b7cdd2", 0), ("#d6e0d4", .5), ("#f1e6c6", 1)],
    "#f1e6c6", "#2e3a3a", orb=("sun", .68, .34, 22, "#fff2d0"), clouds=True, trees="mixed")
pal("Clear Midday", [("#5aa6d6", 0), ("#93c6e6", .5), ("#d9edf6", 1)],
    "#d9edf6", "#20313a", orb=("sun", .5, .2, 24, "#ffffff"), clouds=True, trees="acacia")
pal("Afternoon Gold", [("#e6ab45", 0), ("#f0c96a", .5), ("#f7e6ac", 1)],
    "#f7e6ac", "#39280f", orb=("sun", .32, .26, 26, "#fff0c0"), clouds=True, trees="mixed")
pal("Golden Hour", [("#d97a2a", 0), ("#eaa03c", .45), ("#f6c85c", 1)],
    "#f6c85c", "#301503", orb=("sun", .70, .58, 40, "#ffdf95"), trees="acacia")
pal("Sunset", [("#7a1f2b", 0), ("#c23b2e", .4), ("#e8632e", .7), ("#f3a23c", 1)],
    "#ef7a34", "#1e0308", orb=("sun", .28, .62, 46, "#ff9a4a"), trees="acacia")
pal("Dusk", [("#3a1140", 0), ("#7b2452", .4), ("#c0466a", .72), ("#e88a5a", 1)],
    "#e88a5a", "#160420", orb=("sun", .74, .72, 30, "#ffb27a"), stars=18, trees="mixed")
pal("Twilight", [("#141c4a", 0), ("#33306e", .45), ("#6b4f86", .78), ("#b07a86", 1)],
    "#b07a86", "#0a0a22", stars=60, orb=("moon", .3, .26, 20, MOON), trees="mixed")
pal("Moonrise", [("#0e1636", 0), ("#22315c", .5), ("#4a5c82", .85), ("#8a97ad", 1)],
    "#8a97ad", "#060a1c", stars=90, orb=("moon", .74, .64, 34, MOON), trees="pine")
pal("Night", [("#05081c", 0), ("#0c1436", .5), ("#1a2650", 1)],
    "#1a2650", "#01030c", stars=150, orb=("moon", .68, .24, 30, MOON), trees="mixed")
pal("Deep Night", [("#02030e", 0), ("#050a22", .6), ("#0a1230", 1)],
    "#0a1230", "#000208", stars=220, orb=("moon", .84, .16, 14, MOON), trees="pine")
pal("Autumn", [("#b8461f", 0), ("#d9772b", .4), ("#e7a23f", .72), ("#f2cf6a", 1)],
    "#f2cf6a", "#2a1206", orb=("sun", .3, .34, 30, "#ffdf8a"), leaves="#e0812b", trees="mixed")
pal("Winter", [("#8fa9c4", 0), ("#b9cbdc", .5), ("#e8eff6", 1)],
    "#dbe6f0", "#182430", orb=("sun", .66, .3, 22, "#f4f8ff"), snow=True, trees="pine", ptero=False)
pal("Storm", [("#2b2733", 0), ("#4a4453", .45), ("#7b6f72", .78), ("#b59a86", 1)],
    "#b59a86", "#0e0c13", clouds=True, trees="mixed")
pal("Aurora Finale", [("#03060f", 0), ("#071022", .55), ("#0c1a30", 1)],
    "#0c1a30", "#010309", stars=170, orb=("moon", .8, .2, 18, MOON),
    aurora=["#3af0a0", "#7bf0c8", "#4a90f0"], trees="pine", ptero=False)


# --------------------------------------------------------------------------- #
# compose one scene
# --------------------------------------------------------------------------- #
TREE_FN = {"acacia": [acacia], "pine": [pine], "mixed": [acacia, roundtree, pine]}


def band_color(pl, i):
    # wider value ramp: near-horizon bands stay light, foreground goes dark, so
    # same-value silhouettes stop stacking through the centre (atmospheric perspective)
    return lerp(pl["horizon"], pl["fg"], 0.08 + 0.205 * i)


def actor_color(pl, i):
    return lerp(pl["horizon"], pl["fg"], 0.08 + 0.205 * (i + 1))


def _fits(spans, cx, half, gap=8.0):
    for a, b in spans:
        if cx + half + gap > a and cx - half - gap < b:
            return False
    return True


def _reserve(spans, cx, half):
    spans.append((cx - half, cx + half))


def scene(pl, idx):
    rr = R(1009 + idx * 131)
    S = [sky(pl["stops"])]

    if pl["aurora"]:
        S += aurora(R(500 + idx), pl["aurora"])
    if pl["stars"]:
        S += stars(R(300 + idx), pl["stars"], H * 0.5, lerp(pl["horizon"], "#ffffff", 0.7))
    if pl["orb"]:
        kind, fx, fy, r, col = pl["orb"]
        S += orb(kind, fx * W, fy * H, r, col)
    if pl["clouds"]:
        S += clouds(R(700 + idx), lerp(pl["stops"][-1][0], pl["fg"], 0.12))

    if pl["ptero"]:                                              # flying flock, mid-distance tint
        pc = lerp(pl["horizon"], pl["fg"], 0.42)
        fx, fy = rr.rng(0.34, 0.6), rr.rng(0.2, 0.34)
        for k in range(rr.pick([2, 3, 3])):
            S += pterosaur((fx + k * 0.07) * W + rr.rng(-14, 14),
                           (fy + (k % 2) * 0.03) * H, rr.rng(15, 23), pc, flip=rr.pick([1, -1]))

    baselines = [0.44, 0.57, 0.70, 0.84, 1.0]
    hero_zone = (0.24 * W, 0.86 * W)
    for i, bl in enumerate(baselines):
        base = bl * H
        col, acol = band_color(pl, i), actor_color(pl, i)
        S.append(band(base, 8 + i * 5, col, seed=idx * 0.7 + i))
        spans = []
        if i == len(baselines) - 1:                             # reserve the hero grouping
            spans.append(hero_zone)

        for _ in range(max(1, 3 - i) if i < 3 else 1):         # trees (collision-aware, thinned)
            tsize = 13 + i * 6
            for _try in range(5):
                tx = rr.rng(20, W - 20)
                if _fits(spans, tx, tsize * 1.0):
                    S += rr.pick(TREE_FN[pl["trees"]])(tx, base + 2, tsize, acol, flip=rr.pick([1, -1]))
                    _reserve(spans, tx, tsize * 1.0)
                    break

        if i >= 1:                                              # grazing dinosaurs (collision-aware)
            dsize = 9 + i * 7
            for _ in range(rr.pick([1, 1, 2, 2]) if i < len(baselines) - 1 else 1):
                fn = rr.pick(GROUND)
                half = FOOT[fn] * dsize * 0.5
                for _try in range(6):
                    dx = rr.rng(0.06, 0.94) * W
                    if _fits(spans, dx, half):
                        S += fn(dx, base + 3, dsize, acol, flip=rr.pick([1, -1]))
                        _reserve(spans, dx, half)
                        break

        S += grass(base, -10, W + 10, acol, 5 + i * 3, R(idx * 50 + i))

    # hero foreground grouping (echoes the elephant + calf) — grounded with a soft shadow
    hero_col = pl["fg"]
    hy = 0.985 * H
    shade = lerp(pl["fg"], "#000000", 0.35)
    night_like = pl["name"] in ("Sunset", "Storm", "Night", "Deep Night", "Aurora Finale")
    if night_like:
        S.append(disc(0.48 * W, hy + 4, 150, shade, ry=15, opacity=0.30))
        S += trex(0.48 * W, hy, 66, hero_col, flip=-1)
    else:
        S.append(disc(0.56 * W, hy + 4, 185, shade, ry=16, opacity=0.30))
        S += sauropod(0.48 * W, hy, 70, hero_col, flip=1)
        S += sauropod(0.72 * W, hy, 58, hero_col, flip=1, baby=True)
    S += grass(hy, -10, W + 10, hero_col, 10, R(idx * 77))

    # framing canopy — smaller and slightly lighter than the hero so it frames, not dominates
    S += frame_tree(right=(idx % 2 == 0), s=54, color=lerp(pl["fg"], pl["horizon"], 0.14))

    if pl["snow"]:
        sr = R(900 + idx)
        for _ in range(85):
            S.append(disc(sr.rng(0, W), sr.rng(0, H), sr.rng(0.8, 2.2), "#f4f8ff", opacity=sr.rng(0.4, 0.95)))
    if pl["leaves"]:
        lr = R(950 + idx)
        for _ in range(38):
            x, y, s = lr.rng(0, W), lr.rng(0, H * 0.9), lr.rng(1.4, 3.2)
            S.append(poly([(x, y), (x + s, y + s * 0.6), (x, y + s * 1.3), (x - s, y + s * 0.6)],
                          pl["leaves"], opacity=lr.rng(0.5, 0.9)))
    return S


# --------------------------------------------------------------------------- #
# build the document
# --------------------------------------------------------------------------- #
def build_builder() -> DocumentBuilder:
    b = DocumentBuilder(title="Prehistoric Savanna — 16 Silhouette Scenes (FrameGraph v2.4.1)")
    for idx, pl in enumerate(P):
        page = b.page(f"scene-{idx + 1:02d}-{pl['name'].lower().replace(' ', '-')}",
                      canvas={"size": [W, H], "units": "pt"}, coordinate_mode="absolute")
        page.layer("scene").extend(scene(pl, idx))
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from framegraph.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "prehistoric_savanna.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}")
