"""Prehistoric Savanna — 16 silhouette scenes (A4 landscape).

A flat-silhouette, layered-parallax landscape book in the style of a warm
savanna-at-sunset vector illustration, but populated with dinosaurs and swept
through 16 moods: dawn, sunrise, morning, midday, afternoon, golden hour,
sunset, dusk, twilight, moonrise, night, deep night, autumn, winter, storm and
an aurora finale.

Everything is built with the FrameGraph Python SDK and lowers to grammar-native
primitives (rect / ellipse / closed polyline). Atmospheric perspective is a
single colour lerp from the horizon tint to the foreground dark, so distant
animals read pale/warm and near ones read almost black — exactly as in the
reference art. Deterministic pseudo-random placement keeps every render stable.
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
# colour helpers
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


def disc(cx, cy, r, fill, opacity=None):
    o = {"type": "ellipse", "center": [float(cx), float(cy)], "rx": float(r),
         "ry": float(r), "fill": fill, "decorative": True}
    if opacity is not None:
        o["opacity"] = opacity
    return o


# --------------------------------------------------------------------------- #
# scenery
# --------------------------------------------------------------------------- #
def sky(stops):
    return {"type": "rect", "box": [0, 0, W, H], "decorative": True,
            "fill": linear_gradient(stops, angle=180)}


def orb(kind, cx, cy, r, color):
    glow = radial_gradient([(color, 0.0), (rgba(color, 0.35), 0.4), (rgba(color, 0.0), 1.0)])
    objs = [{"type": "ellipse", "center": [cx, cy], "rx": r * 4.2, "ry": r * 4.2,
             "fill": glow, "decorative": True},
            disc(cx, cy, r, color)]
    return objs


def stars(rr: R, n, y_max, tint):
    out = []
    for _ in range(n):
        x = rr.rng(0, W)
        y = rr.rng(6, y_max)
        s = rr.rng(0.5, 1.6)
        out.append(disc(x, y, s, tint, opacity=rr.rng(0.35, 1.0)))
    return out


def aurora(rr: R, colors):
    out = []
    for k in range(len(colors) * 2):
        c = colors[k % len(colors)]
        x0 = rr.rng(-60, W)
        w = rr.rng(70, 150)
        top = rr.rng(-10, 40)
        bot = rr.rng(180, 300)
        sway = rr.rng(-40, 40)
        pts = [(x0, top), (x0 + w, top), (x0 + w + sway, bot), (x0 + sway, bot)]
        g = linear_gradient([(rgba(c, 0.0), 0.0), (rgba(c, 0.55), 0.5), (rgba(c, 0.0), 1.0)], angle=180)
        out.append(poly(pts, g, opacity=0.7))
    return out


def clouds(rr: R, color):
    out = []
    for _ in range(rr.pick([2, 3, 3, 4])):
        cx = rr.rng(60, W - 60)
        cy = rr.rng(40, 150)
        w = rr.rng(90, 200)
        h = rr.rng(10, 22)
        pts = [(cx - w, cy), (cx - w * 0.4, cy - h), (cx + w * 0.3, cy - h * 0.7),
               (cx + w, cy), (cx + w * 0.3, cy + h * 0.5), (cx - w * 0.5, cy + h * 0.4)]
        out.append(poly(pts, color, smooth=True, opacity=rr.rng(0.25, 0.5)))
    return out


def crest(baseline, amp, seed):
    n = 16
    return [(-60 + (W + 120) * i / n,
             baseline - amp * (0.55 * math.sin(i * 0.8 + seed) + 0.45 * math.sin(i * 0.33 + seed * 1.7)))
            for i in range(n + 1)]


def band(baseline, amp, color, seed):
    pts = crest(baseline, amp, seed) + [(W + 60, H + 90), (-60, H + 90)]
    return poly(pts, color, smooth=True)


def grass(y, x0, x1, color, s, rr: R):
    out = []
    x = x0
    while x < x1:
        h = rr.rng(s * 0.7, s * 1.7)
        w = s * 0.28
        lean = rr.rng(-w, w)
        out.append(poly([(x - w, y + 2), (x + w, y + 2), (x + lean, y - h)], color))
        x += rr.rng(s * 0.5, s * 1.1)
    return out


# --------------------------------------------------------------------------- #
# trees
# --------------------------------------------------------------------------- #
def _place(px, py, s, flip):
    return lambda x, y: (px + flip * s * x, py - s * y)


def acacia(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    trunk = poly([P(-0.09, 0), P(0.09, 0), P(0.14, 1.55), P(-0.06, 1.6)], color)
    canopy = poly([P(-1.35, 1.55), P(-0.7, 1.85), P(0.1, 1.95), P(0.95, 1.88),
                   P(1.4, 1.68), P(0.7, 1.6), P(-0.2, 1.55), P(-0.9, 1.5)], color, smooth=True)
    return [trunk, canopy]


def roundtree(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    trunk = poly([P(-0.08, 0), P(0.08, 0), P(0.1, 1.1), P(-0.1, 1.15)], color)
    canopy = poly([P(-0.85, 1.15), P(-0.6, 1.85), P(0, 2.15), P(0.6, 1.9),
                   P(0.9, 1.25), P(0.55, 0.95), P(-0.5, 0.95)], color, smooth=True)
    return [trunk, canopy]


def pine(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = [poly([P(-0.07, 0), P(0.07, 0), P(0.07, 0.5), P(-0.07, 0.5)], color)]
    for i, (yb, yt, w) in enumerate([(0.35, 1.2, 0.75), (0.9, 1.75, 0.55), (1.4, 2.3, 0.36)]):
        out.append(poly([P(-w, yb), P(w, yb), P(0, yt)], color))
    return out


def frame_tree(right, s, color):
    """Big out-of-frame canopy in a top corner with hanging tendrils."""
    fx = W if right else 0.0
    flip = -1 if right else 1
    P = _place(fx, 0, s, flip)
    out = []
    # thick branch arcing in from the corner
    out.append(poly([P(0.1, -0.3), P(0.2, -0.9), P(1.9, -1.7), P(3.4, -1.3),
                     P(2.0, -1.9), P(0.55, -1.6), P(0.3, -0.9)], color, smooth=True))
    # canopy blob overlapping the corner
    out.append(poly([P(-0.4, 0.4), P(0.6, -0.2), P(2.1, -0.6), P(3.6, -1.1),
                     P(3.9, -2.1), P(2.4, -2.7), P(0.9, -2.4), P(0.1, -1.6),
                     P(-0.4, -0.6)], color, smooth=True))
    # hanging tendrils
    rr = R(7 if right else 11)
    for _ in range(7):
        hx = rr.rng(0.5, 3.4)
        top = rr.rng(-1.6, -0.6)
        length = rr.rng(0.8, 2.6)
        a, b = P(hx, top), P(hx + 0.02, top)
        c, d = P(hx - 0.05, top + length), P(hx + 0.05, top + length)
        out.append(poly([a, b, d, c], color))
    return out


# --------------------------------------------------------------------------- #
# dinosaurs  (stylised silhouettes; y-up local frame, feet on baseline)
# --------------------------------------------------------------------------- #
def _legs(P, hips, color, top, w):
    return [poly([P(h - w, top), P(h + w, top), P(h + w * 0.6, 0), P(h - w * 0.6, 0)], color)
            for h in hips]


def sauropod(px, py, s, color, flip=1, baby=False):
    if baby:
        s *= 0.42
    P = _place(px, py, s, flip)
    out = _legs(P, [0.55, 0.32, -0.2, -0.62], color, 0.66, 0.13)
    body = [(-1.5, 0.55), (-0.9, 0.8), (-0.2, 0.98), (0.35, 0.95), (0.55, 1.2),
            (0.72, 1.85), (0.86, 2.2), (1.16, 2.3), (1.36, 2.12), (1.18, 1.98),
            (0.9, 1.72), (0.74, 1.2), (0.64, 0.72), (-0.1, 0.62), (-0.85, 0.6), (-1.2, 0.5)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    tail = [(-1.2, 0.5), (-1.95, 0.62), (-2.45, 0.7), (-1.95, 0.48), (-1.2, 0.34)]
    out.append(poly([P(*p) for p in tail], color, smooth=True))
    return out


def trex(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _legs(P, [0.28], color, 1.05, 0.2)      # rear leg (far)
    body = [(-1.55, 0.85), (-0.9, 1.05), (-0.3, 1.12), (0.35, 1.2), (0.7, 1.55),
            (0.66, 1.92), (0.96, 2.1), (1.34, 2.06), (1.36, 1.82), (1.02, 1.7),
            (0.92, 1.42), (0.86, 1.0), (0.66, 0.75), (0.2, 0.62), (-0.5, 0.62), (-1.0, 0.68)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    out += _legs(P, [0.42], color, 1.1, 0.22)     # near leg
    out.append(poly([P(0.55, 1.05), P(0.85, 1.0), P(0.72, 0.78)], color))  # tiny arm
    tail = [(-1.0, 0.68), (-1.9, 0.9), (-2.65, 0.98), (-1.9, 0.7), (-1.0, 0.55)]
    out.append(poly([P(*p) for p in tail], color, smooth=True))
    return out


def stegosaurus(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _legs(P, [0.6, 0.35, -0.35, -0.6], color, 0.55, 0.12)
    body = [(-1.55, 0.5), (-0.85, 0.68), (-0.2, 1.15), (0.45, 1.28), (0.95, 1.12),
            (1.3, 1.0), (1.5, 1.02), (1.42, 0.86), (1.1, 0.82), (0.55, 0.68),
            (-0.4, 0.58), (-1.0, 0.5)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    for i in range(6):                             # back plates
        bx = -0.6 + i * 0.28
        by = 1.0 + 0.28 * math.sin((i + 1) * 0.5)
        out.append(poly([P(bx - 0.11, by), P(bx + 0.11, by), P(bx, by + 0.42)], color))
    out.append(poly([P(-1.55, 0.5), P(-1.75, 0.72), P(-1.6, 0.42)], color))  # tail spike
    out.append(poly([P(-1.5, 0.58), P(-1.72, 0.5), P(-1.55, 0.36)], color))
    return out


def triceratops(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _legs(P, [0.7, 0.45, -0.35, -0.62], color, 0.6, 0.13)
    body = [(-1.5, 0.55), (-0.85, 0.78), (-0.1, 0.86), (0.6, 0.84), (1.0, 0.95),
            (1.3, 1.15), (1.55, 1.1), (1.72, 0.82), (1.98, 0.86), (1.86, 0.6),
            (1.6, 0.5), (1.68, 0.32), (1.46, 0.42), (1.15, 0.5), (0.5, 0.56),
            (-0.4, 0.55), (-1.0, 0.52)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    out.append(poly([P(1.35, 1.0), P(1.7, 0.95), P(1.55, 0.62)], color))    # frill/horn brow
    return out


def parasaur(px, py, s, color, flip=1):
    P = _place(px, py, s, flip)
    out = _legs(P, [0.45], color, 1.0, 0.16)
    body = [(-1.5, 0.75), (-0.85, 0.95), (-0.2, 1.05), (0.4, 1.12), (0.72, 1.4),
            (0.62, 1.78), (0.4, 1.95), (0.72, 2.02), (1.05, 1.78), (1.28, 1.9),
            (1.12, 1.6), (0.98, 1.35), (0.9, 1.0), (0.62, 0.75), (0.1, 0.62), (-0.7, 0.66)]
    out.append(poly([P(*p) for p in body], color, smooth=True))
    out += _legs(P, [0.55], color, 1.05, 0.18)
    tail = [(-0.7, 0.66), (-1.7, 0.88), (-2.4, 0.9), (-1.7, 0.66), (-0.7, 0.52)]
    out.append(poly([P(*p) for p in tail], color, smooth=True))
    return out


def pterosaur(cx, cy, s, color, flip=1):
    P = _place(cx, cy, s, flip)
    pts = [(-1.5, 0.0), (-0.8, 0.42), (-0.2, 0.16), (0.0, 0.28), (0.2, 0.16),
           (0.8, 0.42), (1.5, 0.0), (0.65, 0.06), (0.12, -0.12), (-0.12, -0.12), (-0.65, 0.06)]
    return [poly([P(*p) for p in pts], color, smooth=True)]


QUADS = [sauropod, stegosaurus, triceratops]
BIPEDS = [trex, parasaur]
GROUND = QUADS + BIPEDS


# --------------------------------------------------------------------------- #
# palettes (16 moods)
# --------------------------------------------------------------------------- #
SUN = "#ffe6b0"
MOON = "#e9edf4"
P = []


def pal(name, stops, horizon, fg, **k):
    d = {"name": name, "stops": stops, "horizon": horizon, "fg": fg,
         "orb": None, "stars": 0, "clouds": False, "snow": False,
         "leaves": None, "aurora": None, "trees": "acacia", "ptero": True}
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
    "#ef7a34", "#1e0308", orb=("sun", .28, .62, 46, "#ff9a4a"), trees="acacia", ptero=True)
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
    "#b59a86", "#0e0c13", clouds=True, orb=None, trees="mixed")
pal("Aurora Finale", [("#03060f", 0), ("#071022", .55), ("#0c1a30", 1)],
    "#0c1a30", "#010309", stars=170, orb=("moon", .8, .2, 18, MOON),
    aurora=["#3af0a0", "#7bf0c8", "#4a90f0"], trees="pine", ptero=False)


# --------------------------------------------------------------------------- #
# compose one scene
# --------------------------------------------------------------------------- #
TREE_FN = {"acacia": [acacia], "pine": [pine], "mixed": [acacia, roundtree, pine]}


def band_color(pl, i, n):
    return lerp(pl["horizon"], pl["fg"], 0.13 + 0.17 * i)


def actor_color(pl, i, n):
    # one depth-step darker than field i — animals/trees carry the tone of the
    # next, nearer field, which is what gives the reference its readable layers.
    return lerp(pl["horizon"], pl["fg"], 0.13 + 0.17 * (i + 1))


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

    # flying pterosaurs (mid-distance tint)
    if pl["ptero"]:
        pc = lerp(pl["horizon"], pl["fg"], 0.42)
        fx = rr.rng(0.35, 0.62)
        fy = rr.rng(0.20, 0.34)
        for k in range(rr.pick([3, 4, 5])):
            S += pterosaur((fx + k * 0.07) * W + rr.rng(-14, 14),
                           (fy + (k % 2) * 0.03) * H, rr.rng(14, 22), pc)

    n = 5
    baselines = [0.44, 0.57, 0.70, 0.84, 1.0]
    for i in range(n):
        base = baselines[i] * H
        col = band_color(pl, i, n)
        acol = actor_color(pl, i, n)
        amp = 8 + i * 5
        S.append(band(base, amp, col, seed=idx * 0.7 + i))

        tsize = 13 + i * 6
        tree_pool = TREE_FN[pl["trees"]]
        for _ in range(4 - i if i < 3 else 2):
            tx = rr.rng(15, W - 15)
            S += rr.pick(tree_pool)(tx, base + 2, tsize, acol, flip=rr.pick([1, -1]))

        # dinosaurs grazing on this field (skip the far haze band)
        if i >= 1:
            dsize = 9 + i * 7
            count = rr.pick([2, 3, 3, 4]) if i < n - 1 else 2
            for _ in range(count):
                dx = rr.rng(0.06, 0.94) * W
                if i == n - 1 and 0.28 * W < dx < 0.74 * W:
                    continue  # keep the hero zone clear
                S += rr.pick(GROUND)(dx, base + 3, dsize, acol, flip=rr.pick([1, -1]))

        S += grass(base, -10, W + 10, acol, 5 + i * 3, R(idx * 50 + i))

    # hero foreground pair (echoes the elephant + calf) — dramatic biped at night
    hero_col = pl["fg"]
    hy = 0.985 * H
    night_like = pl["name"] in ("Sunset", "Storm", "Night", "Deep Night", "Aurora Finale")
    if night_like:
        S += trex(0.46 * W, hy, 54, hero_col, flip=-1)
    else:
        S += sauropod(0.50 * W, hy, 58, hero_col, flip=1)
        S += sauropod(0.70 * W, hy, 58, hero_col, flip=1, baby=True)
    S += grass(hy, -10, W + 10, hero_col, 10, R(idx * 77))

    # big framing canopy in a top corner
    S += frame_tree(right=(idx % 2 == 0), s=70, color=pl["fg"])

    # weather overlays
    if pl["snow"]:
        sr = R(900 + idx)
        for _ in range(140):
            S.append(disc(sr.rng(0, W), sr.rng(0, H), sr.rng(0.8, 2.2), "#f4f8ff",
                          opacity=sr.rng(0.4, 0.95)))
    if pl["leaves"]:
        lr = R(950 + idx)
        for _ in range(70):
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
    import os
    out = os.environ.get("OUTPUT_YAML_PATH", "prehistoric_savanna.fg.yaml")
    from framegraph.sdk import serialize
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}")
