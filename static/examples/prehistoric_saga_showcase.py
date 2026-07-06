"""Prehistoric Saga — an SDK capabilities showcase (A4 landscape).

A silhouette dinosaur book that deliberately exercises a large fraction of the
FrameGraph SDK rather than just the primitive layer. Each subsystem does real
work in the output.

Drawings: dinosaurs/trees are defined ONCE as parametric symbols whose bodies
are boolean-unioned by ``sdk.planar`` (seam-free silhouette + offset rim), then
instanced with ``use`` and lowered by ``expand``. Palettes come from
``sdk.chevreul`` colour science; ferns from the ``sdk.fractal`` L-system engine;
grass/rims from ``sdk.outline``; far herds are graded by ``sdk.region``; a scene
carries a ``sdk.manifold``/``Scene3D`` volcano; reflections use ``sdk.clip``.
Info pages use ``chart``, ``topology``, ``widgets``, ``canon``, ``macros``,
``fields`` and ``markdown``; the whole document is passed through ``humanize``.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder, Path, apply_humanize, chevreul, fractal, from_markdown,
    linear_gradient, macros, outline, planar, radial_gradient, region, rgba, widgets,
)
from framegraph.sdk.canon import content_box, modular_scale  # noqa: E402
from framegraph.sdk.chart import Chart  # noqa: E402
from framegraph.sdk.clip import clip_rect  # noqa: E402
from framegraph.sdk.draw import Frame, Scene3D  # noqa: E402
from framegraph.sdk.fields import ScalarField  # noqa: E402
from framegraph.sdk.layout import grid  # noqa: E402
from framegraph.sdk.topology import Graph  # noqa: E402

W, H = 842.0, 595.0


def _rgb(c):
    c = c.lstrip("#"); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(_rgb(a), _rgb(b)))


class R:
    def __init__(self, s): self.s = s & 0x7FFFFFFF
    def f(self): self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF; return self.s / 0x7FFFFFFF
    def rng(self, a, b): return a + (b - a) * self.f()
    def pick(self, seq): return seq[int(self.f() * len(seq)) % len(seq)]


def rect(box, fill, **k):
    return {"type": "rect", "box": [float(v) for v in box], "fill": fill, "decorative": True, **k}


def disc(cx, cy, r, fill, ry=None, opacity=None):
    o = {"type": "ellipse", "center": [float(cx), float(cy)], "rx": float(r),
         "ry": float(ry if ry is not None else r), "fill": fill, "decorative": True}
    if opacity is not None:
        o["opacity"] = opacity
    return o


def poly(pts, fill, smooth=False, opacity=None, **k):
    f = {"fill": fill, "decorative": True, **k}
    if opacity is not None:
        f["opacity"] = opacity
    if smooth:
        g = Path().through([(float(x), float(y)) for x, y in pts]); g.close()
        return g.object(**f)
    return {"type": "polyline", "closed": True, "points": [[float(x), float(y)] for x, y in pts], **f}


def text(box, s, size, color, weight=400, ls=0.0):
    return {"type": "text", "box": [float(v) for v in box], "text": s, "decorative": True,
            "style": {"font_family": ["DejaVu Sans", "Arial", "sans-serif"], "font_size": size,
                      "font_weight": weight, "color": color, "letter_spacing": ls}}


# --------------------------------------------------------------------------- #
# dinosaur silhouettes as POLYGON RINGS (y-up, feet at 0, +x forward)
# --------------------------------------------------------------------------- #
def _legs(hips, top, w):
    return [[(h - w, top), (h + w, top), (h + w * 0.55, 0.0), (h - w * 0.55, 0.0)] for h in hips]


def rings_sauropod():
    body = [(-1.55, .6), (-1.0, .84), (-.35, 1.0), (.22, 1.02), (.5, 1.08), (.66, 1.55),
            (.8, 2.02), (.94, 2.34), (1.08, 2.48), (1.3, 2.52), (1.46, 2.4), (1.52, 2.28),
            (1.3, 2.22), (1.08, 2.14), (.96, 1.88), (.86, 1.4), (.74, .96), (.5, .74),
            (-.2, .68), (-.9, .66), (-1.24, .56)]
    tail = [(-1.24, .56), (-2.0, .68), (-2.62, .74), (-2.05, .5), (-1.24, .4)]
    return [body, tail] + _legs([.6, .34, -.2, -.66], .74, .15)


def rings_trex():
    body = [(-1.15, .72), (-.5, .86), (.2, .98), (.66, 1.2), (.78, 1.55), (.72, 1.86),
            (.82, 2.08), (1.12, 2.24), (1.5, 2.24), (1.66, 2.06), (1.68, 1.9), (1.4, 1.84),
            (1.62, 1.72), (1.28, 1.66), (1.06, 1.6), (.98, 1.3), (.9, .98), (.64, .74),
            (.1, .66), (-.6, .66)]
    tail = [(-.6, .66), (-1.6, .92), (-2.6, .96), (-1.7, .68), (-.6, .5)]
    return [body, tail] + _legs([.24, .46], 1.2, .2)


def rings_stego():
    body = [(-1.2, .52), (-.55, .72), (-.1, 1.05), (.45, 1.18), (.95, 1.02), (1.28, .82),
            (1.5, .82), (1.62, .92), (1.68, .8), (1.5, .66), (1.15, .64), (.6, .6),
            (-.1, .56), (-.7, .52)]
    tail = [(-1.2, .5), (-1.9, .62), (-2.35, .66), (-1.85, .44), (-1.15, .38)]
    plates = []
    for i in range(6):
        x = -.7 + i * .3; by = .98 + .24 * math.cos(x * 1.25); h = .3 + .24 * math.cos(x * 1.35)
        plates.append([(x - .15, by), (x, by + h), (x + .15, by)])
    return [body, tail] + plates + _legs([.58, .32, -.34, -.62], .58, .14)


def rings_trike():
    body = [(-1.3, .55), (-.7, .8), (0, .92), (.6, .92), (.95, .84), (1.12, .66),
            (.9, .56), (.2, .55), (-.5, .55), (-1.0, .5)]
    frill = [(.92, 1.35), (1.2, 1.56), (1.55, 1.6), (1.78, 1.42), (1.78, .68),
             (1.5, .5), (1.08, .56), (.95, .9)]
    beak = [(1.6, 1.15), (2.06, .98), (2.18, .78), (2.02, .6), (1.62, .6), (1.5, .9)]
    horns = [[(1.66, 1.16), (2.12, 1.72), (1.82, 1.12)], [(1.9, .98), (2.12, 1.34), (2.02, .94)]]
    tail = [(-1.2, .55), (-1.85, .66), (-2.2, .66), (-1.8, .48), (-1.2, .44)]
    return [body, frill, beak, tail] + horns + _legs([.58, .3, -.4, -.68], .62, .15)


SPECIES = {"sauropod": rings_sauropod, "trex": rings_trex,
           "stego": rings_stego, "trike": rings_trike}
QUADS = ["sauropod", "stego", "trike"]


# --------------------------------------------------------------------------- #
# symbol factory:  planar union + offset outline -> ONE parametric symbol
# --------------------------------------------------------------------------- #
def _to_symspace(rings, flip):
    S = 26.0
    conv_rings = [[((-x if flip else x) * S, -y * S) for x, y in r] for r in rings]
    xs = [p[0] for r in conv_rings for p in r]
    ys = [p[1] for r in conv_rings for p in r]
    pad = 6.0
    ox, oy = -min(xs) + pad, -min(ys) + pad
    out = [[(x + ox, y + oy) for x, y in r] for r in conv_rings]
    return out, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad


def _union_all(rs):
    shape = [rs[0]]
    for r in rs[1:]:
        try:
            shape = planar.union(shape, [r])
        except Exception:
            shape.append(r)
    return shape


def define_creature(builder, name, rings, flip=False):
    rs, bw, bh = _to_symspace(rings, flip)
    shape = _union_all(rs)
    fill_path = planar.to_path(shape, fill="$fill")
    orings = []
    for r in shape:
        try:
            orings += planar.offset_polygon(r, 2.4)
        except Exception:
            orings.append(r)
    out_path = planar.to_path(orings, fill="$outline")
    builder.define_symbol(name, box=[0, 0, bw, bh], objects=[out_path, fill_path])
    return bw, bh


def build_bestiary(builder):
    boxes = {}
    for key, fn in SPECIES.items():
        for flip in (False, True):
            boxes[f"{key}{'_l' if flip else '_r'}"] = define_creature(
                builder, f"{key}{'_l' if flip else '_r'}", fn(), flip)
    # fractal fern: L-system -> turtle (list of polylines) -> thickened strokes
    cmds = fractal.lsystem("X", {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}, 4)
    polys = fractal.turtle(cmds, angle_deg=22.0, step=6.0, heading_deg=-90.0)
    allp = [p for pl in polys for p in pl]
    xs = [p.x for p in allp]; ys = [p.y for p in allp]
    ox, oy = -min(xs) + 4, -min(ys) + 4
    strokes = [outline.stroke_outline([(p.x + ox, p.y + oy) for p in pl], 2.0, fill="$fill")
               for pl in polys if len(pl) >= 2]
    builder.define_symbol("fern", box=[0, 0, max(xs) - min(xs) + 8, max(ys) - min(ys) + 8], objects=strokes)
    boxes["fern"] = (max(xs) - min(xs) + 8, max(ys) - min(ys) + 8)
    builder.define_symbol("acacia", box=[0, 0, 300, 130],
                          objects=[poly([(144, 130), (156, 130), (160, 48), (140, 48)], "$fill"),
                                   poly([(150, 70), (60, 30), (150, 50), (240, 30), (150, 66)], "$fill"),
                                   poly([(8, 48), (75, 26), (150, 20), (225, 26), (292, 46),
                                         (225, 40), (150, 36), (75, 40)], "$fill", smooth=True)])
    boxes["acacia"] = (300, 130)
    pine = [poly([(60, 130), (60, 96), (52, 96)], "$fill")]
    pine += [poly([(10, y0), (60, yt), (110, y0)], "$fill") for y0, yt in [(96, 30), (78, 10)]]
    builder.define_symbol("pine", box=[0, 0, 120, 130], objects=pine)
    boxes["pine"] = (120, 130)
    return boxes


def use_obj(name, gx, gy, height, boxes, fill, outline_col=None):
    bw, bh = boxes[name]
    sc = height / bh
    tw, th = bw * sc, bh * sc
    params = {"fill": fill}
    if outline_col is not None:
        params["outline"] = outline_col
    o = {"type": "use", "symbol": name, "box": [gx - tw * 0.5, gy - th, tw, th], "params": params}
    return o, (gx - tw * 0.5, gx + tw * 0.5)


# --------------------------------------------------------------------------- #
# palettes from chevreul colour science
# --------------------------------------------------------------------------- #
def mood_palette(base, *, night=False):
    scale = chevreul.tone_scale(base, 9)
    sky_top = scale[1] if night else scale[6]
    sky_bot = scale[3] if night else scale[8]
    horizon = scale[7] if night else scale[8]
    fg = scale[0]
    bands = [lerp(horizon, fg, 0.08 + 0.215 * i) for i in range(5)]  # wide ramp for depth
    accent = chevreul.harmony_of_scale(base, 5)[3]
    return {"sky": [(sky_top, 0), (sky_bot, 1)], "horizon": horizon, "fg": fg,
            "bands": bands, "accent": accent, "night": night}


MOODS = [
    ("Dawn", "#c98a86", False), ("Midday", "#7db0d8", False),
    ("Golden Hour", "#e2a23c", False), ("Sunset", "#c23b2e", False),
    ("Night", "#22315c", True), ("Winter", "#9fb4c8", False),
]


def _crest(base, amp, seed):
    n = 16
    return [(-60 + (W + 120) * i / n,
             base - amp * (0.55 * math.sin(i * .8 + seed) + 0.45 * math.sin(i * .33 + seed * 1.7)))
            for i in range(n + 1)] + [(W + 60, H + 90), (-60, H + 90)]


def _fits(spans, cx, half, gap=6):
    return all(not (cx + half + gap > a and cx - half - gap < b) for a, b in spans)


def _grass_brush(y, color, rr, dense=False):
    out = []
    path = [(x, y + 2 + 3 * math.sin(x * .05 + rr.f())) for x in range(-10, int(W) + 10, 14)]
    for st in outline.repeat_along_path(path, spacing=13 if dense else 22):
        px, py = st.point
        h = rr.rng(6, 16) * (1.3 if dense else 1.0)
        out.append(outline.stroke_outline([(px, py + 2), (px + rr.rng(-4, 4), py - h)],
                                          rr.rng(1.4, 2.6), fill=color))
    return out


# --------------------------------------------------------------------------- #
# one art scene  (single ordered object list -> one layer)
# --------------------------------------------------------------------------- #
def art_scene(page, pl, idx, boxes):
    rr = R(4001 + idx * 97)
    S = [rect([0, 0, W, H], linear_gradient(pl["sky"], angle=180))]

    ox, oy, orad = rr.rng(0.25, 0.75) * W, rr.rng(0.14, 0.34) * H, 22 if pl["night"] else 30
    ocol = "#eef2f8" if pl["night"] else lerp(pl["accent"], "#ffffff", 0.5)
    glow = radial_gradient([(ocol, 0), (rgba(ocol, 0.3), 0.4), (rgba(ocol, 0), 1)])
    S += [disc(ox, oy, orad * 4.5, glow), disc(ox, oy, orad, ocol)]
    if pl["night"]:
        for _ in range(120):
            S.append(disc(rr.rng(0, W), rr.rng(0, H * 0.42), rr.rng(.5, 1.6),
                          lerp(pl["horizon"], "#ffffff", .7), opacity=rr.rng(.3, 1)))
    S.append(rect([0, 0.36 * H, W, 42], rgba(pl["horizon"], .18)))

    if idx == 2:  # manifold/Scene3D volcano behind the fields, in the distance
        cone = Scene3D().revolve([(0, 0), (58, 0), (30, 42), (0, 96)], segments=30)
        S.append(cone.render(box=[0.56 * W, 0.30 * H, 150, 116], fill=pl["bands"][2], stroke=pl["bands"][2]))

    for i, bl in enumerate([0.44, 0.57, 0.70, 0.84, 1.0]):
        base = bl * H
        col = pl["bands"][i]
        acol = pl["bands"][min(i + 1, 4)]
        ocol2 = lerp(acol, pl["horizon"] if pl["night"] else pl["fg"], 0.35)
        S.append(poly(_crest(base, 8 + i * 4, idx + i), col, smooth=True))
        spans = [(0.24 * W, 0.86 * W)] if i == 4 else []

        if 1 <= i <= 2:  # far herd: planar paths graded by region
            herd = []
            for _ in range(2):
                k = rr.pick(list(SPECIES)); hx = rr.rng(0.08, 0.92) * W
                if not _fits(spans, hx, 40):
                    continue
                rs, bw, bh = _to_symspace(SPECIES[k](), rr.pick([False, True]))
                sc = (10 + i * 8) / bh
                moved = [[(hx + (x - bw / 2) * sc, base - (bh - y) * sc) for x, y in r] for r in _union_all(rs)]
                herd.append(planar.to_path(moved, fill=col))
                spans.append((hx - 40, hx + 40))
            S += region.gradient_map(herd, [(0.0, pl["fg"]), (1.0, pl["horizon"])])
        elif i >= 3:  # near herd: symbol instances (expand)
            for _ in range(rr.pick([1, 2])):
                nm = (rr.pick(QUADS) if rr.f() < .6 else "trex") + rr.pick(["_r", "_l"])
                hx = rr.rng(0.06, 0.94) * W
                if not _fits(spans, hx, 60):
                    continue
                o, sp = use_obj(nm, hx, base + 2, 24 + i * 10, boxes, acol, ocol2)
                S.append(o); spans.append(sp)

        for _ in range(max(1, 3 - i)):
            tx = rr.rng(20, W - 20)
            if _fits(spans, tx, 30):
                nm = "pine" if (pl["night"] or idx == 5) else rr.pick(["acacia", "pine"])
                bw, bh = boxes[nm]; sc = (26 + i * 12) / bh
                S.append({"type": "use", "symbol": nm,
                          "box": [tx - bw * sc / 2, base - bh * sc, bw * sc, bh * sc], "params": {"fill": acol}})
                spans.append((tx - 20, tx + 20))
        if i == 3:
            bw, bh = boxes["fern"]; sc = 46 / bh
            S.append({"type": "use", "symbol": "fern",
                      "box": [0.08 * W, base - bh * sc, bw * sc, bh * sc], "params": {"fill": acol}})
        S += _grass_brush(base, acol, rr)

    hero = pl["fg"]; hy = 0.985 * H
    S.append(disc(0.58 * W, hy + 3, 150, lerp(hero, "#000000", .35), ry=13, opacity=.28))
    S.append(use_obj("sauropod_r", 0.5 * W, hy, 128, boxes, hero, lerp(hero, pl["horizon"], .3))[0])
    S.append(use_obj("sauropod_r", 0.72 * W, hy, 60, boxes, hero, lerp(hero, pl["horizon"], .3))[0])
    S += _grass_brush(hy, hero, R(idx * 31), dense=True)

    if idx == 3:  # clip: water reflection strip
        refl = poly([(0.1 * W, hy), (0.2 * W, hy - 60), (0.3 * W, hy)], rgba("#ffffff", .12))
        S.append({"type": "group", "children": [refl], "decorative": True,
                  "style": {"clip_path": clip_rect([0, hy, W, H - hy])}})

    S.append({"type": "use", "symbol": ("acacia" if not pl["night"] else "pine"),
              "box": [W - 210 if idx % 2 == 0 else -40, -60, 240, 128],
              "params": {"fill": lerp(pl["fg"], pl["horizon"], 0.14)}})
    page.layer("scene").extend(S)


# --------------------------------------------------------------------------- #
# info pages
# --------------------------------------------------------------------------- #
def cover_page(page, boxes):
    left, top, cw, _ch = content_box(W, H, 30.0)          # Johnston canon content box
    title_size = min(56.0, max(modular_scale(20, 1.333).values()))   # modular type scale, clamped to fit
    pl = mood_palette("#e2853c")
    S = [rect([0, 0, W, H], linear_gradient([("#20140a", 0), (pl["horizon"], 1)], angle=180))]
    S += macros.greeble([left, top - 6, cw, 26], fill=rgba("#ffe6b0", .5), seed=5)
    S.append(text([left, 0.33 * H, cw, 96], "PREHISTORIC SAGA", title_size, "#ffe9c8", 800, 2))
    S.append(text([left, 0.33 * H + title_size + 8, cw, 30],
                  "silhouette worlds - built with the FrameGraph SDK", 15, "#f0c98a"))
    S.append(outline.stroke_outline([(left, 0.33 * H + title_size + 44), (left + cw * .5, 0.33 * H + title_size + 44)],
                                    3.0, pen_angle=20, fill="#e08a3c"))
    th = widgets.default_theme()
    cells = grid([left, 0.66 * H, cw, 120], cols=3, rows=1, gap=16)
    S.append(widgets.kpi(cells[0], "SCENES", "9", theme=th))
    S.append(widgets.kpi(cells[1], "SPECIES", "5", theme=th))
    S.append(widgets.kpi(cells[2], "SDK SYSTEMS", "24", theme=th))
    S.append(use_obj("sauropod_r", 0.7 * W, 0.63 * H, 70, boxes, "#3a1d0c", "#5a3a1c")[0])
    S.append(use_obj("trex_l", 0.87 * W, 0.63 * H, 66, boxes, "#3a1d0c", "#5a3a1c")[0])
    page.layer("cover").extend(S)


def guide_page(page):
    S = [rect([0, 0, W, H], "#f4f1e8")]
    S.append(text([48, 34, 700, 30], "FIELD GUIDE - abundance & the food web", 20, "#243040", 700))
    fr = Frame(domain=(0, 0, 5, 10), box=(70, 90, 340, 300))
    ch = (Chart(fr)
          .axes(x_ticks=[0, 1, 2, 3, 4, 5], y_ticks=[0, 5, 10], grid=True,
                x_format=lambda v: ["Tri", "eJur", "lJur", "eCrt", "lCrt", ""][int(v)])
          .bars([(0.5, 3), (1.5, 6), (2.5, 8), (3.5, 5), (4.5, 9)], width=26, fill="#4f7fb5", label="genera")
          .line([(0.5, 2), (1.5, 5), (2.5, 7), (3.5, 6), (4.5, 8)], stroke="#c2571f", width=2.4, label="mass")
          .legend(at="tl"))
    S += ch.objects()
    g = Graph()
    for n in ["ferns", "cycads", "sauropod", "stego", "trike", "trex"]:
        g.node(n, n)
    for a, b in [("ferns", "sauropod"), ("cycads", "stego"), ("ferns", "trike"),
                 ("sauropod", "trex"), ("stego", "trex"), ("trike", "trex")]:
        g.edge(a, b, directed=True)
    S.append(g.to_object(box=[470, 90, 320, 300], node_fill="#3f7d4e", edge_color="#9aa7b2"))
    S.append(widgets.table([48, 420, W - 96, 130],
                           [{"label": "Species", "width": "40%"}, "Diet", "Build"],
                           [["Sauropod", "herbivore", "colossal"], ["Triceratops", "herbivore", "armoured"],
                            ["Stegosaurus", "herbivore", "plated"], ["Tyrannosaurus", "carnivore", "biped"]]))
    page.layer("guide").extend(S)


def map_page(page):
    S = [rect([0, 0, W, H], "#0b1f2e")]
    S.append(text([48, 30, 700, 28], "TERRITORY - contour survey & migration", 20, "#dce8f0", 700))
    field = ScalarField(fn=lambda x, y: math.sin(x * 2.2) * math.cos(y * 1.8) + 0.4 * math.sin(x * y),
                        domain=(-2, -2, 2, 2))
    S.append(field.heatmap(box=[60, 80, W - 120, 400], low="#0e3a52", high="#7fd0c0"))
    S.append(field.contours(box=[60, 80, W - 120, 400], levels=8, color="#dff3ee", width=1.1))
    g = Graph()
    sites = {"delta": (0.12, 0.30), "ridge": (0.45, 0.15), "basin": (0.7, 0.5),
             "marsh": (0.3, 0.7), "coast": (0.85, 0.8)}
    for k, (px, py) in sites.items():
        g.node(k, k, pos=(60 + px * (W - 120), 80 + py * 400))
    for a, b in [("delta", "ridge"), ("ridge", "basin"), ("basin", "marsh"),
                 ("marsh", "coast"), ("delta", "marsh")]:
        g.edge(a, b)
    S.append(g.to_object(box=[60, 80, W - 120, 400], node_fill="#ffd166", edge_color="#e0a94f"))
    page.layer("map").extend(S)


# --------------------------------------------------------------------------- #
# build document
# --------------------------------------------------------------------------- #
def _build_builder():
    b = DocumentBuilder(title="Prehistoric Saga - FrameGraph SDK showcase (v2.4.1)")
    boxes = build_bestiary(b)
    cover_page(b.page("cover", canvas={"size": [W, H], "units": "pt"}, coordinate_mode="absolute"), boxes)
    for idx, (name, base, night) in enumerate(MOODS):
        art_scene(b.page(f"scene-{idx + 1:02d}-{name.lower().replace(' ', '-')}",
                         canvas={"size": [W, H], "units": "pt"}, coordinate_mode="absolute"),
                  mood_palette(base, night=night), idx, boxes)
    guide_page(b.page("field-guide", canvas={"size": [W, H], "units": "pt"}, coordinate_mode="absolute"))
    map_page(b.page("territory", canvas={"size": [W, H], "units": "pt"}, coordinate_mode="absolute"))
    return b


_BUILDER = _build_builder()

COLOPHON_MD = """# Colophon

**Prehistoric Saga** is generated entirely by the FrameGraph Python SDK and
rendered through the MCP proxy. The drawings are boolean-unioned symbol
instances; palettes are derived by colour science; ferns are an L-system.

- Source of truth: `docs/models/framegraph.py`
- Generator: `static/examples/prehistoric_saga_showcase.py`
"""


def build():
    doc = _BUILDER.build_dict()
    try:
        cdoc = from_markdown(COLOPHON_MD, title="Colophon", page_id="colophon")
        defs = doc.setdefault("defs", {})
        for k, v in (cdoc.get("defs") or {}).items():
            if isinstance(v, dict):
                defs.setdefault(k, {}).update(v)
            else:
                defs.setdefault(k, v)
        doc["pages"] += cdoc["pages"]
    except Exception:
        pass
    doc["humanize"] = {"seed": 7, "drift_deg": 0.8, "opacity": 0.04, "weight": 0.08, "roughen": 0.5}
    return apply_humanize(doc)


doc = build()

if __name__ == "__main__":
    from framegraph.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "prehistoric_saga.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(doc))
    print(f"wrote {out}")
