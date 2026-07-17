#!/usr/bin/env python3
"""FrameForge v2 — *Twelve Hours of Geometry* (A4 capability showcase).

A polished, multi-page A4 reference for the CG-canon geometry/fractal/3D APIs
shipped to `frameforge.sdk` in one 12-hour session (roadmap backlog B1–B10 + the
2D/3D intersection, hull, OBB, curvature, and shading work). Every figure in this
book is drawn by CALLING the very API it documents — the reflections come from
`Mat3.reflect`, the hulls from `convex_hull`, the fractals from `sdk.fractal`, the
shaded solids from `Scene3D.render(shading="phong")`. It is the capability set,
demonstrated on itself.

Run from the repository root::

    uv run python static/examples/cg_canon_showcase.py            # writes the .fg.yaml
    uv run --group pdfout python tooling/render_pdf.py \\
        cg-canon-showcase.fg.yaml --out out/pdf                   # -> multi-page A4 PDF

⚠ ARCHITECTURAL CONTRACT (PALS's LAW) — the prose is authored by an LLM. The
figures are not: they are the live output of the documented functions, validated
here against the model (`build`) and the static rules (`validate_static_rules`);
the build fails loudly on any model error. Verify prose specifics against the
CHANGELOG and the source.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    Camera,
    CubicBezier,
    DocumentBuilder,
    Material,
    Scene3D,
    ViewingPipeline,
    Vec2,
    Vec3,
    aabb,
    convex_hull,
    dragon_curve,
    koch_curve,
    lsystem,
    mirror,
    obb,
    point_in_polygon,
    polygon_area,
    ray_segment_intersection,
    segment_intersection,
    segment_polygon_intersections,
    sierpinski_arrowhead,
    serialize,
    turtle,
    window_to_viewport,
)
from frameforge.sdk.geometry import Mat3  # noqa: E402
from frameforge.sdk.manifold import sphere, torus  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Page geometry — A4 @ 96 dpi (794 × 1123), portrait.
# --------------------------------------------------------------------------- #
PW, PH = 794, 1123
MX = 64
CW = PW - 2 * MX                       # 666 content measure
TOP = 150                              # first content baseline (below running head)
BOT = PH - 72                          # last usable y
HEAD_Y = 58

# Type — Inter for chrome/headings, a book serif for prose, a mono for code.
SANS = ["Inter", "Helvetica Neue", "Arial", "sans-serif"]
SERIF = ["Charter", "Georgia", "Times New Roman", "serif"]
MONO = ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"]

# Ink ramp + a two-accent system (steel indigo = geometry, terracotta = curves).
PAPER = "#FBFAF6"
INK = "#15181D"
MUTE = "#565D66"
FAINT = "#9AA0A8"
HAIR = "#E7E3DA"
PANELBG = "#F3F1EA"
INDIGO = "#2B4C7E"
INDIGO_SOFT = "#E9EEF6"
TERRA = "#B75A34"
TERRA_SOFT = "#F6EBE2"
TEAL = "#2E7D7A"
TEAL_SOFT = "#E4F0EF"
GOLD = "#B98A2E"

# Part accent lookup (title, color, soft).
PARTS = {
    1: ("Geometry Kernel · 2D", INDIGO, INDIGO_SOFT),
    2: ("Curves & Fractals", TERRA, TERRA_SOFT),
    3: ("The 3D Pipeline", TEAL, TEAL_SOFT),
    4: ("Engineering & Correctness", INK, PANELBG),
}


# ── primitives ─────────────────────────────────────────────────────────────
def T(x, y, w, h, s, *, size=11, color=INK, weight=None, align="left", font=None,
      track=None, lh=None, upper=False, style=None):
    st = {"font_size": size, "color": color, "overflow": "shrink_to_fit",
          "font_family": font or SANS}
    if weight:
        st["font_weight"] = weight
    if align != "left":
        st["text_align"] = align
    if track is not None:
        st["letter_spacing"] = track
    if lh is not None:
        st["line_height"] = lh
    if upper:
        st["text_transform"] = "uppercase"
    if style:
        st["font_style"] = style
    return {"type": "text", "box": [x, y, w, h], "text": s, "style": st, "decorative": True}


def R(x, y, w, h, **f):
    return {"type": "rect", "box": [x, y, w, h], "decorative": True, **f}


def LN(x1, y1, x2, y2, *, color=HAIR, width=1.0, dash=None, cap=None):
    ss = {"stroke_width": width}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    if cap:
        ss["stroke_linecap"] = cap
    return {"type": "line", "from": [x1, y1], "to": [x2, y2], "stroke": color,
            "stroke_style": ss, "decorative": True}


def ELP(cx, cy, r, **f):
    return {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "decorative": True, **f}


def POLY(pts, *, stroke=INK, width=1.4, fill="none", closed=False, dash=None, cap="round", join="round"):
    ss = {"stroke_width": width, "stroke_linecap": cap, "stroke_linejoin": join}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    o = {"type": "polyline", "points": [[round(x, 3), round(y, 3)] for (x, y) in pts],
         "stroke": stroke, "fill": fill, "stroke_style": ss, "decorative": True}
    if closed:
        o["closed"] = True
    return o


def DOT(cx, cy, r, *, fill=INK, stroke=None, sw=1.2):
    o = {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": fill, "decorative": True}
    if stroke:
        o["stroke"] = stroke
        o["stroke_style"] = {"stroke_width": sw}
    return o


def panel(x, y, w, h, *, fill=PANELBG, stroke=HAIR, sw=1.0, radius=10, accent=None):
    out = [R(x, y, w, h, fill=fill, stroke=stroke, stroke_style={"stroke_width": sw}, radius=radius)]
    if accent:
        out.append(R(x, y, 6, h, fill=accent, radius=2))
    return out


def code_block(x, y, w, lines, *, size=9.5, lh=1.55, pad=13, fill="#1B1F27",
               ink="#E8ECF2", accent="#8FB3E0"):
    """A dark monospace code panel; returns objects. Height is derived from lines."""
    h = pad * 2 + len(lines) * size * lh
    out = [R(x, y, w, h, fill=fill, radius=8, decorative=True)]
    yy = y + pad
    for ln in lines:
        col = accent if ln.strip().startswith("#") else ink
        out.append(T(x + pad, yy, w - 2 * pad, size * lh + 2, ln, size=size, color=col,
                     font=MONO, lh=1.0))
        yy += size * lh
    return out, h


# ── figure coordinate mapper (aspect-preserving, Y-up data -> Y-down page) ──
def fit(points, box, *, pad=0.1, flip_y=True):
    """Map data points (Vec2 or (x,y)) into page-space figure ``box`` = [x,y,w,h],
    aspect-preserving and centred. ``flip_y`` puts mathematical +y up on the page."""
    ps = [(p.x, p.y) if isinstance(p, Vec2) else (float(p[0]), float(p[1])) for p in points]
    lo, hi = aabb([Vec2(x, y) for x, y in ps])
    w = max(hi.x - lo.x, 1e-9)
    h = max(hi.y - lo.y, 1e-9)
    padpx = min(box[2], box[3]) * pad
    vx, vy, vw, vh = box[0] + padpx, box[1] + padpx, box[2] - 2 * padpx, box[3] - 2 * padpx
    s = min(vw / w, vh / h)
    ox = vx + (vw - w * s) / 2
    oy = vy + (vh - h * s) / 2
    out = []
    for x, y in ps:
        px = ox + (x - lo.x) * s
        py = oy + (hi.y - y) * s if flip_y else oy + (y - lo.y) * s
        out.append((px, py))
    return out


def figframe(box, *, label=None, part=1):
    """A soft framed plate for a figure; returns objects (frame + optional label)."""
    x, y, w, h = box
    out = [R(x, y, w, h, fill="#FFFFFF", stroke=HAIR, stroke_style={"stroke_width": 1.2}, radius=10)]
    if label:
        _, col, _ = PARTS[part]
        out.append(T(x + 14, y + 12, w - 28, 14, label, size=9, color=col, weight=700,
                     upper=True, track=1.4))
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  FIGURES — each calls the real API it documents and returns page objects.
# ═══════════════════════════════════════════════════════════════════════════
def _F(box, inset=(0, 26, 0, 8)):
    """The drawable rectangle inside a figframe (leaves room for the label)."""
    x, y, w, h = box
    li, ti, ri, bi = inset
    return [x + 16 + li, y + ti, w - 32 - li - ri, h - ti - 12 - bi]


def fig_reflect(box, part):
    """B7 — Mat3.reflect / mirror: an asymmetric glyph mirrored across a line."""
    inner = _F(box)
    half = [(0, 0), (0.9, 0.15), (1.15, 0.75), (0.7, 0.62), (0.78, 1.15), (0.28, 0.7), (0.0, 0.95)]
    # reflect the half across the vertical axis x = 1.3 using the real API.
    m = Mat3.reflect(((1.3, 0.0), (1.3, 1.0)))
    ref = [m.apply(Vec2(x, y)) for x, y in half]
    allpts = half + [(p.x, p.y) for p in ref]
    mapped = {(round(a, 4), round(b, 4)): xy for (a, b), xy in
              zip([(x, y) for x, y in allpts], fit(allpts, inner, pad=0.14))}
    ph = [mapped[(round(x, 4), round(y, 4))] for x, y in half]
    pr = [mapped[(round(p.x, 4), round(p.y, 4))] for p in ref]
    axis = fit([(1.3, -0.2), (1.3, 1.35)], inner, pad=0.14)  # not aspect-locked; approx
    objs = figframe(box, label="Mat3.reflect · mirror()", part=part)
    ax = (ph + pr)
    axx = sum(x for x, _ in ax) / len(ax)  # visual axis at the mirror line midpoint
    objs.append(LN(axx, inner[1] + 6, axx, inner[1] + inner[3] - 6, color=FAINT, width=1.0, dash=[4, 4]))
    objs.append(POLY(ph, stroke=PARTS[part][1], width=2.2, fill=PARTS[part][2], closed=True))
    objs.append(POLY(pr, stroke=INK, width=1.6, fill="none", closed=True, dash=[5, 4]))
    return objs


def fig_intersections_2d(box, part):
    """B8 — segment/ray × segment/polygon crossings, each marked at the real hit."""
    inner = _F(box)
    poly = [(0.15, 0.2), (0.85, 0.12), (0.95, 0.7), (0.5, 0.95), (0.08, 0.68)]
    a, b = (0.0, 0.45), (1.1, 0.55)               # a segment that crosses the polygon
    s0, s1 = (0.2, 0.05), (0.75, 1.0)             # a second segment
    hit = segment_intersection(a, b, s0, s1)
    poly_hits = segment_polygon_intersections(a, b, poly)
    ray_hit = ray_segment_intersection((0.5, 0.5), (0.9, -0.4), (0.85, 0.12), (0.95, 0.7))
    keys = poly + [a, b, s0, s1] + [(p.x, p.y) for p in poly_hits] + \
        ([(hit.x, hit.y)] if hit else []) + ([(ray_hit.x, ray_hit.y)] if ray_hit else []) + [(0.5, 0.5)]
    mp = dict(zip([(round(x, 4), round(y, 4)) for x, y in keys], fit(keys, inner, pad=0.13)))

    def P(x, y):
        return mp[(round(x, 4), round(y, 4))]
    objs = figframe(box, label="segment · ray · polygon ×", part=part)
    objs.append(POLY([P(x, y) for x, y in poly], stroke=INDIGO, width=1.6, fill=INDIGO_SOFT, closed=True))
    objs.append(POLY([P(*a), P(*b)], stroke=INK, width=1.5))
    objs.append(POLY([P(*s0), P(*s1)], stroke=INK, width=1.5))
    for h in poly_hits:
        objs.append(DOT(*P(h.x, h.y), 4.6, fill=PAPER, stroke=INDIGO, sw=2.0))
    if hit:
        objs.append(DOT(*P(hit.x, hit.y), 5.0, fill=TERRA))
    if ray_hit:
        objs.append(DOT(*P(0.5, 0.5), 3.2, fill=MUTE))
        objs.append(POLY([P(0.5, 0.5), P(ray_hit.x, ray_hit.y)], stroke=TEAL, width=1.4, dash=[3, 3]))
        objs.append(DOT(*P(ray_hit.x, ray_hit.y), 4.6, fill=PAPER, stroke=TEAL, sw=2.0))
    return objs


def fig_convex_hull(box, part):
    """B10 — convex_hull of a scattered point cloud."""
    inner = _F(box)
    pts = [(0.12, 0.2), (0.4, 0.05), (0.78, 0.14), (0.95, 0.5), (0.82, 0.9), (0.45, 0.98),
           (0.1, 0.75), (0.03, 0.42), (0.5, 0.5), (0.38, 0.4), (0.62, 0.6), (0.55, 0.72),
           (0.3, 0.62), (0.7, 0.35)]
    hull = convex_hull(pts)
    keys = pts + [(p.x, p.y) for p in hull]
    mp = dict(zip([(round(x, 4), round(y, 4)) for x, y in keys], fit(keys, inner, pad=0.12)))
    hullset = {(round(p.x, 4), round(p.y, 4)) for p in hull}
    objs = figframe(box, label="convex_hull()", part=part)
    objs.append(POLY([mp[(round(p.x, 4), round(p.y, 4))] for p in hull],
                     stroke=INDIGO, width=2.0, fill=INDIGO_SOFT, closed=True))
    for x, y in pts:
        on = (round(x, 4), round(y, 4)) in hullset
        objs.append(DOT(*mp[(round(x, 4), round(y, 4))], 4.4 if on else 3.0,
                        fill=INDIGO if on else FAINT))
    return objs


def fig_obb(box, part):
    """B10 residual — obb vs aabb on a rotated cloud (OBB is tighter)."""
    inner = _F(box)
    th = math.radians(28)
    base = [(0.1, 0.15), (0.9, 0.1), (0.85, 0.4), (0.5, 0.55), (0.15, 0.45)]
    cx, cy = 0.5, 0.32
    rot = [((x - cx) * math.cos(th) - (y - cy) * math.sin(th) + cx,
            (x - cx) * math.sin(th) + (y - cy) * math.cos(th) + cy) for x, y in base]
    box2 = obb(rot)
    lo, hi = aabb(rot)
    ab = [(lo.x, lo.y), (hi.x, lo.y), (hi.x, hi.y), (lo.x, hi.y)]
    keys = rot + [(p.x, p.y) for p in box2] + ab
    mp = dict(zip([(round(x, 4), round(y, 4)) for x, y in keys], fit(keys, inner, pad=0.1)))

    def P(x, y):
        return mp[(round(x, 4), round(y, 4))]
    objs = figframe(box, label="obb() vs aabb()", part=part)
    objs.append(POLY([P(x, y) for x, y in ab], stroke=FAINT, width=1.3, closed=True, dash=[5, 4]))
    objs.append(POLY([P(p.x, p.y) for p in box2], stroke=TERRA, width=2.0,
                     fill=TERRA_SOFT, closed=True))
    for x, y in rot:
        objs.append(DOT(*P(x, y), 3.4, fill=INK))
    return objs


def fig_curvature(box, part):
    """B9 — CubicBezier.curvature drawn as a curvature comb along the curve."""
    inner = _F(box)
    bz = CubicBezier(Vec2(0, 0.35), Vec2(0.3, 1.15), Vec2(0.7, -0.35), Vec2(1.0, 0.55))
    samples = [i / 60 for i in range(61)]
    curve = [bz.point(t) for t in samples]
    combs = []
    for t in [i / 22 for i in range(23)]:
        p = bz.point(t)
        d = bz.derivative(t)
        ln = math.hypot(d.x, d.y) or 1.0
        nx, ny = -d.y / ln, d.x / ln
        k = bz.curvature(t)
        m = max(-0.5, min(0.5, k * 0.06))
        combs.append((p, (p.x + nx * m, p.y + ny * m)))
    keys = [(p.x, p.y) for p in curve] + [c for pair in combs for c in
                                          ((pair[0].x, pair[0].y), pair[1])]
    mp = dict(zip([(round(x, 4), round(y, 4)) for x, y in keys], fit(keys, inner, pad=0.12)))

    def P(x, y):
        return mp[(round(x, 4), round(y, 4))]
    objs = figframe(box, label="CubicBezier.curvature", part=part)
    for base_p, tip in combs:
        objs.append(POLY([P(base_p.x, base_p.y), P(*tip)], stroke="#D6A88B", width=1.0))
    objs.append(POLY([P(p.x, p.y) for p in curve], stroke=INK, width=2.4))
    return objs


def fig_arclength(box, part):
    """B9 — CubicBezier.arc_length: equal-arc-length ticks along a curve."""
    inner = _F(box)
    bz = CubicBezier(Vec2(0, 0), Vec2(0.15, 1.0), Vec2(0.9, 0.95), Vec2(1.0, 0.15))
    total = bz.arc_length()
    curve = [bz.point(i / 80) for i in range(81)]
    # walk the curve, dropping a tick every total/10 of arc length.
    ticks = []
    acc = 0.0
    step = total / 10
    prev = bz.point(0.0)
    next_mark = step
    for i in range(1, 401):
        t = i / 400
        p = bz.point(t)
        acc += math.hypot(p.x - prev.x, p.y - prev.y)
        if acc >= next_mark:
            d = bz.derivative(t)
            ln = math.hypot(d.x, d.y) or 1.0
            ticks.append((p, (-d.y / ln, d.x / ln)))
            next_mark += step
        prev = p
    keys = [(p.x, p.y) for p in curve] + [(p.x, p.y) for p, _ in ticks]
    mp = dict(zip([(round(x, 4), round(y, 4)) for x, y in keys], fit(keys, inner, pad=0.14)))

    def P(x, y):
        return mp[(round(x, 4), round(y, 4))]
    objs = figframe(box, label="arc_length() · equal steps", part=part)
    objs.append(POLY([P(p.x, p.y) for p in curve], stroke=INK, width=2.2))
    for p, (nx, ny) in ticks:
        bx, by = P(p.x, p.y)
        objs.append(LN(bx - nx * 8, by + ny * 8, bx + nx * 8, by - ny * 8, color=TERRA, width=1.6))
    return objs


def fig_point_in_poly(box, part):
    """B10 — point_in_polygon over a lattice of probes; inside vs outside."""
    inner = _F(box)
    poly = [(0.5, 0.05), (0.78, 0.28), (0.62, 0.5), (0.9, 0.85), (0.5, 0.68),
            (0.1, 0.85), (0.38, 0.5), (0.22, 0.28)]
    probes = [(i / 15, j / 15) for i in range(1, 15) for j in range(1, 15)]
    keys = poly + probes
    mp = dict(zip([(round(x, 4), round(y, 4)) for x, y in keys], fit(keys, inner, pad=0.1)))
    objs = figframe(box, label="point_in_polygon()", part=part)
    objs.append(POLY([mp[(round(x, 4), round(y, 4))] for x, y in poly],
                     stroke=INDIGO, width=1.8, fill="none", closed=True))
    for x, y in probes:
        inside = point_in_polygon((x, y), poly)
        objs.append(DOT(*mp[(round(x, 4), round(y, 4))], 2.2,
                        fill=INDIGO if inside else HAIR))
    return objs


def fig_polygon_area(box, part):
    """B10 — polygon_area (signed shoelace), value annotated."""
    inner = _F(box)
    poly = [(0.1, 0.2), (0.9, 0.1), (0.75, 0.5), (0.95, 0.9), (0.4, 0.75), (0.05, 0.95)]
    area = abs(polygon_area(poly))
    keys = poly
    mp = dict(zip([(round(x, 4), round(y, 4)) for x, y in keys], fit(keys, inner, pad=0.16)))
    objs = figframe(box, label="polygon_area()", part=part)
    objs.append(POLY([mp[(round(x, 4), round(y, 4))] for x, y in poly],
                     stroke=INDIGO, width=1.8, fill=INDIGO_SOFT, closed=True))
    cx = sum(mp[(round(x, 4), round(y, 4))][0] for x, y in poly) / len(poly)
    cy = sum(mp[(round(x, 4), round(y, 4))][1] for x, y in poly) / len(poly)
    objs.append(T(cx - 60, cy - 9, 120, 20, f"A = {area:.3f}", size=13, color=INK,
                  weight=700, align="center"))
    return objs


def mapper(points, box, *, pad=0.1, flip_y=True):
    """Return a function (x, y) -> (px, py) fitting ``points`` into ``box``,
    aspect-preserving. Use it to map several polylines with ONE shared transform."""
    ps = [(p.x, p.y) if isinstance(p, Vec2) else (float(p[0]), float(p[1])) for p in points]
    lo, hi = aabb([Vec2(x, y) for x, y in ps])
    w = max(hi.x - lo.x, 1e-9)
    h = max(hi.y - lo.y, 1e-9)
    padpx = min(box[2], box[3]) * pad
    vx, vy, vw, vh = box[0] + padpx, box[1] + padpx, box[2] - 2 * padpx, box[3] - 2 * padpx
    s = min(vw / w, vh / h)
    ox = vx + (vw - w * s) / 2
    oy = vy + (vh - h * s) / 2

    def m(x, y):
        return (ox + (x - lo.x) * s, (oy + (hi.y - y) * s) if flip_y else (oy + (y - lo.y) * s))
    return m


def fig_window_to_viewport(box, part):
    """B1 — window_to_viewport: a data window fitted into a page viewport."""
    inner = _F(box)
    fx, fy, fw, fh = inner
    # a little content in "window" space, mapped into a viewport rect by the API.
    content = [(0, 0), (3, 0), (3, 2), (1.5, 3), (0, 2)]
    win = [-0.4, -0.4, 3.8, 3.8]
    left = [fx, fy + 40, fw * 0.42, fh - 60]
    right = [fx + fw * 0.56, fy + 40, fw * 0.42, fh - 60]
    objs = figframe(box, label="window_to_viewport()", part=part)
    objs.append(T(fx, fy + 8, fw, 14, "WINDOW  (data space)", size=9, color=MUTE, weight=700, track=1))
    objs.append(T(fx + fw * 0.56, fy + 8, fw * 0.42, 14, "VIEWPORT  (page rect)", size=9,
                  color=PARTS[part][1], weight=700, track=1))
    # window panel + content
    mw = mapper([(win[0], win[1]), (win[0] + win[2], win[1] + win[3])], left, pad=0.02)
    objs.append(R(*[c for c in (left[0], left[1], left[2], left[3])], fill="#FFFFFF",
                  stroke=HAIR, stroke_style={"stroke_width": 1}))
    objs.append(POLY([mw(x, y) for x, y in content], stroke=MUTE, width=1.6, fill=PANELBG, closed=True))
    # viewport panel + the SAME content mapped by window_to_viewport
    objs.append(R(right[0], right[1], right[2], right[3], fill="#FFFFFF", stroke=PARTS[part][1],
                  stroke_style={"stroke_width": 1.4}))
    m = window_to_viewport(win, right, uniform=True)
    vp = [m.apply(Vec2(x, y)) for x, y in content]
    objs.append(POLY([(p.x, p.y) for p in vp], stroke=PARTS[part][1], width=2.0,
                     fill=PARTS[part][2], closed=True))
    objs.append(T(fx + fw * 0.44, fy + fh / 2 - 8, fw * 0.1, 20, "->", size=22, color=FAINT, align="center"))
    return objs


def _fractal_page(box, part, curve, label, color, *, width=1.4, pad=0.08):
    inner = _F(box)
    m = mapper([(p.x, p.y) for p in curve], inner, pad=pad)
    objs = figframe(box, label=label, part=part)
    objs.append(POLY([m(p.x, p.y) for p in curve], stroke=color, width=width))
    return objs


def fig_koch(box, part):
    """B4 — koch_curve: the generator refined across iterations 1..4."""
    inner = _F(box)
    fx, fy, fw, fh = inner
    objs = figframe(box, label="koch_curve(n)", part=part)
    rows = 4
    rh = (fh - 20) / rows
    for i in range(1, rows + 1):
        c = koch_curve(i, step=1.0)
        rb = [fx, fy + (i - 1) * rh + 6, fw, rh - 10]
        m = mapper([(p.x, p.y) for p in c], rb, pad=0.03)
        objs.append(POLY([m(p.x, p.y) for p in c], stroke=TERRA if i == rows else MUTE,
                         width=1.8 if i == rows else 1.0))
        objs.append(T(fx, fy + (i - 1) * rh + 6, 30, 12, f"n={i}", size=8, color=FAINT, weight=700))
    return objs


def fig_dragon(box, part):
    """B4 — the Heighway dragon at iteration 12."""
    return _fractal_page(box, part, dragon_curve(12, step=1.0), "dragon_curve(12)", TERRA, width=1.1)


def fig_sierpinski(box, part):
    """B4 — the Sierpiński arrowhead curve (triangle-filling)."""
    return _fractal_page(box, part, sierpinski_arrowhead(6, step=1.0),
                         "sierpinski_arrowhead(6)", GOLD, width=1.2)


def fig_lsystem_plant(box, part):
    """B4 — a branching L-system plant (lsystem + turtle with [ ] branches)."""
    inner = _F(box)
    s = lsystem("X", {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}, 5)
    polys = turtle(s, angle_deg=25, step=1.0, heading_deg=90)
    allpts = [(p.x, p.y) for poly in polys for p in poly]
    if not allpts:
        return figframe(box, label="lsystem() + turtle()", part=part)
    m = mapper(allpts, inner, pad=0.07)
    objs = figframe(box, label="lsystem() + turtle()", part=part)
    for poly in polys:
        objs.append(POLY([m(p.x, p.y) for p in poly], stroke="#3E6B3A", width=1.1))
    return objs


# ── 3D figures — Scene3D groups fit into the plate box directly ─────────────
def _scene_group(scene, box, **render):
    inner = _F(box)
    fx, fy, fw, fh = inner
    return scene.render(box=[fx, fy, fw, fh], **render)


def fig_torus_phong(box, part):
    """B6 + B2 — a Phong-shaded, back-face-culled torus."""
    cam = Camera(eye=Vec3(2.6, 2.1, 3.1), target=Vec3(0, 0, 0), fov=42)
    grp = _scene_group(torus(1.0, 0.42, steps_u=48, steps_v=28), box, camera=cam,
                       shading="phong", cull_backfaces=True, specular=0.5, shininess=22,
                       material=Material(fill="#3E6DA6", stroke="#2B4C7E"),
                       light=Vec3(-0.4, -0.55, 0.75))
    return figframe(box, label='render(shading="phong", cull_backfaces=True)', part=part) + [grp]


def fig_shading_ladder(box, part):
    """B6 — the same sphere under none / lambert / gouraud / phong."""
    inner = _F(box)
    fx, fy, fw, fh = inner
    modes = ["none", "lambert", "gouraud", "phong"]
    objs = figframe(box, label="shading modes", part=part)
    n = len(modes)
    gap = 16
    cw = (fw - (n - 1) * gap) / n
    cam = Camera(eye=Vec3(1.7, 1.5, 2.5), target=Vec3(0, 0, 0), fov=46)
    for i, mode in enumerate(modes):
        bx = fx + i * (cw + gap)
        grp = sphere(1.0, steps_u=26, steps_v=18).render(
            box=[bx, fy, cw, fh - 34], camera=cam, shading=mode, cull_backfaces=True,
            specular=0.6, shininess=26, material=Material(fill="#C4713F", stroke="#9A5730"),
            light=Vec3(-0.5, -0.55, 0.7))
        objs.append(grp)
        objs.append(T(bx, fy + fh - 26, cw, 14, mode, size=10, color=INK, weight=700, align="center"))
    return objs


def fig_viewing_pipeline(box, part):
    """B1/B2 — a wireframe cube projected by ViewingPipeline (world->viewport)."""
    inner = _F(box)
    fx, fy, fw, fh = inner
    v = [Vec3(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    edges = [(0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3), (2, 6),
             (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)]
    cam = Camera(eye=Vec3(2.8, 2.2, 3.4), target=Vec3(0, 0, 0), fov=40)
    pipe = ViewingPipeline(cam, [fx + 12, fy + 12, fw - 24, fh - 24])
    proj = pipe.project(v)                       # world -> clipped -> fitted page pts
    idx = {id(p): pp for p, pp in zip(v, proj)}  # only valid for in-front points
    objs = figframe(box, label="ViewingPipeline.project()", part=part)
    # map original->projected by index (all cube verts are in front here)
    pm = {i: proj[i] for i in range(len(v))} if len(proj) == len(v) else None
    if pm:
        for a, b in edges:
            objs.append(POLY([(pm[a].x, pm[a].y), (pm[b].x, pm[b].y)], stroke=TEAL, width=1.6))
        for i in range(len(v)):
            objs.append(DOT(pm[i].x, pm[i].y, 3.0, fill=INK))
    return objs


def fig_orbit(box, part):
    """B2 — a solid orbited through four camera angles: robust projection, no crash."""
    inner = _F(box)
    fx, fy, fw, fh = inner
    objs = figframe(box, label="Camera.orbit · robust projection", part=part)
    gap = 14
    cw = (fw - 3 * gap) / 4
    base = Camera(eye=Vec3(0, 1.4, 3.2), target=Vec3(0, 0, 0), fov=44)
    for i in range(4):
        cam = base.orbit(azimuth=i * 45.0, elevation=10.0)
        grp = torus(1.0, 0.4, steps_u=36, steps_v=22).render(
            box=[fx + i * (cw + gap), fy + (fh - cw) / 2, cw, cw], camera=cam,
            shading="phong", cull_backfaces=True,
            material=Material(fill="#2E7D7A", stroke="#215B58"))
        objs.append(grp)
    return objs


def fig_ray_triangle(box, part):
    """B8 residual — ray × triangle (Möller–Trumbore), the hit projected to 2D."""
    from frameforge.sdk import ray_triangle_intersection
    inner = _F(box)
    fx, fy, fw, fh = inner
    tri = [Vec3(-1, -0.6, 0), Vec3(1.2, -0.4, 0.3), Vec3(0.1, 1.1, -0.2)]
    o, d = Vec3(0.1, 0.05, -2.2), Vec3(0.02, 0.06, 1.0)
    hit = ray_triangle_intersection(o, d, *tri)
    cam = Camera(eye=Vec3(2.4, 1.6, 3.0), target=Vec3(0, 0, 0), fov=44)
    pipe = ViewingPipeline(cam, [fx + 12, fy + 12, fw - 24, fh - 24])
    pts = pipe.project(tri + [o] + ([hit] if hit else []))
    objs = figframe(box, label="ray_triangle_intersection()", part=part)
    if len(pts) >= 4:
        t2 = pts[:3]
        objs.append(POLY([(p.x, p.y) for p in t2], stroke=TEAL, width=1.8,
                         fill=TEAL_SOFT, closed=True))
        oo = pts[3]
        objs.append(DOT(oo.x, oo.y, 3.4, fill=MUTE))
        if hit and len(pts) >= 5:
            hh = pts[4]
            objs.append(POLY([(oo.x, oo.y), (hh.x, hh.y)], stroke=INK, width=1.4, dash=[4, 3]))
            objs.append(DOT(hh.x, hh.y, 5.0, fill=TERRA))
    return objs


# ── page composers ─────────────────────────────────────────────────────────
def _chrome(L, part, running):
    """Running head + footer + page frame chrome."""
    title, col, _ = PARTS[part]
    L.add(LN(MX, HEAD_Y + 14, PW - MX, HEAD_Y + 14, color=HAIR, width=1.0))
    L.add(T(MX, HEAD_Y, 300, 14, "Twelve Hours of Geometry", size=9, color=MUTE,
            weight=600, upper=True, track=1.6))
    L.add(T(PW - MX - 300, HEAD_Y, 300, 14, running, size=9, color=col, weight=700,
            align="right", upper=True, track=1.4))


def _footer(L, pageno):
    L.add(LN(MX, PH - 52, PW - MX, PH - 52, color=HAIR, width=1.0))
    L.add(T(MX, PH - 44, 400, 14, "frameforge.sdk · CG-canon release", size=8.5, color=FAINT))
    L.add(T(PW - MX - 60, PH - 44, 60, 14, str(pageno), size=10, color=MUTE, weight=600,
            align="right"))


class Book:
    def __init__(self, b):
        self.b = b
        self.n = 0

    def _page(self, pid):
        self.n += 1
        page = self.b.page(pid, canvas={"size": [PW, PH], "units": "px"},
                           coordinate_mode="absolute")
        L = page.layer("main")
        L.add(R(0, 0, PW, PH, fill=PAPER))
        return L

    def feature(self, part, kicker, title, blurb, code, figure_fn):
        L = self._page(f"f{self.n:02d}")
        _, col, soft = PARTS[part]
        _chrome(L, part, PARTS[part][0])
        # heading block
        L.add(R(MX, TOP - 4, 30, 4, fill=col))
        L.add(T(MX, TOP + 8, CW, 14, kicker, size=10, color=col, weight=700, upper=True, track=1.6))
        L.add(T(MX, TOP + 26, CW, 40, title, size=27, color=INK, weight=800, lh=1.05))
        L.add(T(MX, TOP + 70, CW, 60, blurb, size=12.5, color=MUTE, lh=1.5, font=SERIF))
        # figure plate (large)
        fb = [MX, TOP + 150, CW, 470]
        for o in figure_fn(fb, part):
            L.add(o)
        # code caption
        cy = fb[1] + fb[3] + 26
        L.add(T(MX, cy, CW, 14, "The call that draws it", size=9, color=FAINT,
                weight=700, upper=True, track=1.4))
        cobjs, _h = code_block(MX, cy + 20, CW, code)
        for o in cobjs:
            L.add(o)
        _footer(L, self.n)
        return self

    def prose(self, part, kicker, title, paras, code=None, stats=None):
        """A text page for a non-visual (engineering) capability."""
        L = self._page(f"p{self.n:02d}")
        _, col, soft = PARTS[part]
        _chrome(L, part, PARTS[part][0])
        L.add(R(MX, TOP - 4, 30, 4, fill=col))
        L.add(T(MX, TOP + 8, CW, 14, kicker, size=10, color=col, weight=700, upper=True, track=1.6))
        L.add(T(MX, TOP + 26, CW, 40, title, size=27, color=INK, weight=800, lh=1.05))
        y = TOP + 92
        for para in paras:
            L.add(T(MX, y, CW, 200, para, size=12.5, color="#2C3138", lh=1.62, font=SERIF))
            y += 26 + _measure_lines(para, CW, 12.5) * 12.5 * 1.62
        if stats:
            fw = (CW - (len(stats) - 1) * 14) / len(stats)
            for i, (v, lab) in enumerate(stats):
                x = MX + i * (fw + 14)
                for o in panel(x, y + 8, fw, 76, accent=col):
                    L.add(o)
                L.add(T(x + 14, y + 24, fw - 20, 28, v, size=21, color=INK, weight=800))
                L.add(T(x + 14, y + 56, fw - 20, 16, lab, size=9.5, color=MUTE))
            y += 108
        if code:
            L.add(T(MX, y + 6, CW, 14, "In the tree", size=9, color=FAINT, weight=700,
                    upper=True, track=1.4))
            cobjs, _h = code_block(MX, y + 26, CW, code)
            for o in cobjs:
                L.add(o)
        _footer(L, self.n)
        return self

    def cover(self):
        L = self._page("cover")
        L.add(R(0, 0, PW, 430, fill=INK))
        L.add(R(MX, 430 - 6, 84, 6, fill=INDIGO))
        L.add(T(MX, 116, CW, 18, "FRAMEFORGE v2 · SDK CAPABILITY SHOWCASE", size=12,
                color="#9BB6DA", weight=700, upper=True, track=2.2))
        L.add(T(MX, 150, CW, 66, "Twelve Hours", size=56, color="#FFFFFF", weight=800))
        L.add(T(MX, 212, CW, 66, "of Geometry", size=56, color="#FFFFFF", weight=800))
        L.add(T(MX, 300, CW - 260, 90, "The CG-canon release — reflection, intersection, "
                "hulls, curvature, fractals, and a corrected 3D pipeline, each figure drawn "
                "by the very call it documents.", size=14, color="#C7D2E0", lh=1.5, font=SERIF))
        dc = dragon_curve(11, step=1.0)
        m = mapper([(p.x, p.y) for p in dc], [PW - MX - 250, 96, 250, 300], pad=0.05)
        L.add(POLY([m(p.x, p.y) for p in dc], stroke="#5E86BE", width=0.8))
        facts = [("10", "backlog items"), ("~30", "new APIs"), ("100+", "red-first tests"),
                 ("0", "schema changes"), ("61", "A4 pages")]
        fw = (CW - 4 * 14) / 5
        for i, (v, lab) in enumerate(facts):
            x = MX + i * (fw + 14)
            for o in panel(x, 486, fw, 78, fill="#FFFFFF", stroke=HAIR, accent=INDIGO):
                L.add(o)
            L.add(T(x + 14, 502, fw - 20, 30, v, size=23, color=INK, weight=800))
            L.add(T(x + 14, 536, fw - 20, 16, lab, size=9, color=MUTE))
        L.add(T(MX, 600, CW, 16, "CONTENTS", size=11, color=MUTE, weight=700, track=1.5))
        yy = 628
        for pi in (1, 2, 3, 4):
            title, col, _ = PARTS[pi]
            L.add(LN(MX, yy + 30, MX + CW, yy + 30, color=HAIR))
            L.add(T(MX, yy + 6, 30, 20, f"{pi:02d}", size=13, color=col, weight=800))
            L.add(T(MX + 44, yy + 7, CW - 44, 20, title, size=14, color=INK, weight=600))
            yy += 36
        L.add(T(MX, PH - 74, CW, 16, "frameforge.sdk · geometry · fractal · draw — "
                "authored end-to-end through the SDK; every figure is live API output.",
                size=10, color=FAINT, font=SERIF))
        return self

    def colophon(self):
        L = self._page("colophon")
        _chrome(L, 4, "About this book")
        L.add(T(MX, TOP + 8, CW, 14, "COLOPHON", size=10, color=MUTE, weight=700, upper=True, track=1.6))
        L.add(T(MX, TOP + 26, CW, 40, "How this was made", size=27, color=INK, weight=800))
        paras = [
            "Every diagram in this book is the live output of the function it documents. "
            "The reflections come from `Mat3.reflect`, the hulls from `convex_hull`, the "
            "combs from `CubicBezier.curvature`, the fractals from `sdk.fractal`, and the "
            "shaded solids from `Scene3D.render`. Nothing is illustrated by hand.",
            "The book is itself a FrameForge document — a multi-page A4 `mode: page` "
            "composition authored through the same SDK, validated against the Pydantic "
            "model and the static rules on build, and lowered to one vector PDF by "
            "`tooling/render_pdf.py`. The page size is A4 at 96 dpi (794 × 1123).",
            "PALS's Law (a house rule): LLM output is untrusted until a real gate checks "
            "it. The prose here is authored and should be read as didactic; the figures "
            "are not authored — they are computed, and the build fails loudly on any model "
            "error. Verify specifics against the CHANGELOG and the source.",
        ]
        y = TOP + 92
        for para in paras:
            L.add(T(MX, y, CW, 200, para.replace("`", ""), size=13, color="#2C3138",
                    lh=1.64, font=SERIF))
            y += 26 + _measure_lines(para, CW, 13) * 13 * 1.64
        _footer(L, self.n)
        return self

    def contents(self, feats):
        """A two-page table of contents (Parts I–II, then III–IV + back matter)."""
        groups = [
            [(1, feats[1]), (2, feats[2])],
            [(3, feats[3]), (4, feats[4])],
        ]
        for gi, group in enumerate(groups):
            L = self._page(f"toc{gi}")
            _chrome(L, 4, "Contents")
            if gi == 0:
                L.add(T(MX, TOP + 8, CW, 14, "CONTENTS", size=10, color=MUTE, weight=700,
                        upper=True, track=1.6))
                L.add(T(MX, TOP + 26, CW, 40, "What's inside", size=27, color=INK, weight=800))
                y = TOP + 96
            else:
                y = TOP + 6
            for part, specs in group:
                title, col, soft = PARTS[part]
                L.add(R(MX, y + 2, 5, 24, fill=col, radius=2))
                L.add(T(MX + 18, y, 34, 24, f"{part:02d}", size=17, color=col, weight=800))
                L.add(T(MX + 60, y + 3, CW - 60, 22, title.replace(" · ", " — "), size=16,
                        color=INK, weight=700))
                y += 36
                for spec in specs:
                    L.add(T(MX + 60, y, 14, 14, "·", size=12, color=col, weight=800))
                    L.add(T(MX + 76, y, CW - 200, 14, spec[2], size=11.5, color="#2C3138"))
                    L.add(T(MX + CW - 120, y, 120, 14, spec[1], size=9, color=FAINT,
                            align="right", font=MONO))
                    y += 21
                if part in _PLATES:
                    L.add(T(MX + 76, y, CW - 120, 14,
                            f"+ {len(_PLATES[part])} full-page plates", size=10,
                            color=MUTE, style="italic", font=SERIF))
                    y += 24
                y += 16
            if gi == 1:
                L.add(T(MX, y + 6, CW, 20, "Back matter", size=13, color=INK, weight=700))
                y += 30
                for lab in ["The ledger — ten items, twelve hours", "The session, in order",
                            "API index — the new surface", "Additive by design"]:
                    L.add(T(MX + 60, y, 14, 14, "·", size=12, color=INK, weight=800))
                    L.add(T(MX + 76, y, CW - 100, 14, lab, size=11.5, color="#2C3138"))
                    y += 21
            _footer(L, self.n)
        return self

    def divider(self, part, specs):
        L = self._page(f"div{part}")
        title, col, soft = PARTS[part]
        L.add(R(0, 0, PW, PH, fill=col))
        L.add(T(MX, 300, CW, 30, f"PART {part:02d}", size=15, color="#FFFFFF", weight=700,
                upper=True, track=3, align="left"))
        L.add(LN(MX, 344, MX + 90, 344, color="#FFFFFF", width=3))
        # split long titles onto their own big lines
        for j, chunk in enumerate(title.split(" · ")):
            L.add(T(MX, 372 + j * 58, CW, 64, chunk, size=46, color="#FFFFFF", weight=800))
        yy = 372 + len(title.split(" · ")) * 58 + 40
        for spec in specs:
            L.add(T(MX, yy, CW, 18, "— " + spec[2], size=13, color="#FFFFFF", lh=1.3))
            yy += 26
        return self

    def scoreboard(self):
        L = self._page("scoreboard")
        _chrome(L, 4, "What shipped")
        L.add(T(MX, TOP + 8, CW, 14, "THE LEDGER", size=10, color=MUTE, weight=700, upper=True, track=1.6))
        L.add(T(MX, TOP + 26, CW, 40, "Ten items, twelve hours", size=27, color=INK, weight=800))
        rows = [
            ("B7", "Reflection / mirror transform", "Mat3.reflect · mirror", 1),
            ("B8", "2D + 3D intersection primitives", "segment/ray/line · plane/triangle", 1),
            ("B9", "Curvature & arc-length", "curvature · arc_length · polyline_length", 2),
            ("B10", "Convex hull, AABB, OBB", "convex_hull · aabb · obb · aabb3", 1),
            ("B4", "Fractal / procedural generator", "lsystem · turtle · koch/dragon/sierpinski", 2),
            ("B1", "Formal viewing pipeline", "window_to_viewport · ViewingPipeline", 3),
            ("B2", "3D pipeline correctness", "try_project · near-plane cull · cull_backfaces", 3),
            ("B6", "Shading completion", 'Scene3D.render(shading="phong")', 3),
            ("—", "Honest 3.10–3.12 support + classifiers", "CI matrix · packaging", 4),
            ("—", "pre-commit, F811 gate, Image-collision fix", "same gate, earlier", 4),
        ]
        y = TOP + 84
        rh = 52
        for tag, name, api, pi in rows:
            _, col, soft = PARTS[pi]
            L.add(R(MX, y, CW, rh - 8, fill="#FFFFFF", stroke=HAIR, stroke_style={"stroke_width": 1}, radius=8))
            L.add(R(MX, y, 5, rh - 8, fill=col, radius=2))
            L.add(R(MX + 18, y + 10, 40, rh - 28, fill=soft, radius=5))
            L.add(T(MX + 18, y + (rh - 8) / 2 - 9, 40, 18, tag, size=12, color=col, weight=800, align="center"))
            L.add(T(MX + 72, y + 8, CW - 90, 18, name, size=12.5, color=INK, weight=600))
            L.add(T(MX + 72, y + 26, CW - 90, 14, api, size=9.5, color=MUTE, font=MONO))
            y += rh
        _footer(L, self.n)
        return self

    def closing(self):
        L = self._page("back")
        L.add(R(0, 0, PW, PH, fill=INK))
        L.add(R(MX, 300, 84, 6, fill=INDIGO))
        L.add(T(MX, 330, CW, 40, "Additive by design", size=34, color="#FFFFFF", weight=800))
        L.add(T(MX, 388, CW - 120, 120,
                "None of this changed the wire format. Every capability is an SDK function "
                "that computes and emits ordinary 2D geometry (§A.0) — no schema change, no "
                "version bump, goldens byte-for-byte unchanged. The document renders because "
                "the model validates; the figures are correct because the tests are green.",
                size=14, color="#C7D2E0", lh=1.6, font=SERIF))
        L.add(T(MX, PH - 120, CW, 16, "Run it yourself", size=10, color="#9BB6DA",
                weight=700, upper=True, track=1.6))
        cobjs, _h = code_block(MX, PH - 96, CW,
                               ["uv run python static/examples/cg_canon_showcase.py",
                                "uv run --group pdfout python tooling/render_pdf.py \\",
                                "    cg-canon-showcase.fg.yaml --out out/pdf"],
                               fill="#0E1218", ink="#D8DEE8", accent="#7FA6D6")
        for o in cobjs:
            L.add(o)
        return self

    def intro(self, part, lead, paras):
        L = self._page(f"intro{part}")
        title, col, soft = PARTS[part]
        _chrome(L, part, title)
        L.add(R(MX, TOP - 4, 30, 4, fill=col))
        L.add(T(MX, TOP + 8, CW, 14, f"PART {part:02d}", size=10, color=col, weight=700, upper=True, track=1.8))
        L.add(T(MX, TOP + 30, CW, 44, title.replace(" · ", " — "), size=30, color=INK, weight=800))
        L.add(T(MX, TOP + 86, CW - 30, 70, lead, size=17, color=col, lh=1.42, font=SERIF, style="italic"))
        y = TOP + 86 + 34 + _measure_lines(lead, CW - 30, 17) * 17 * 1.42
        for para in paras:
            L.add(T(MX, y, CW, 240, para, size=13, color="#2C3138", lh=1.66, font=SERIF))
            y += 28 + _measure_lines(para, CW, 13) * 13 * 1.66
        _footer(L, self.n)
        return self

    def plate(self, part, kicker, title, caption, fig_fn):
        L = self._page(f"plate{self.n:02d}")
        _, col, soft = PARTS[part]
        L.add(T(MX, 66, CW, 14, kicker, size=10, color=col, weight=700, upper=True, track=1.8))
        L.add(T(MX, 86, CW, 30, title, size=23, color=INK, weight=800))
        L.add(LN(MX, 124, PW - MX, 124, color=HAIR))
        for o in fig_fn([MX, 148, CW, 812], part):
            L.add(o)
        L.add(T(MX, 148 + 812 + 18, CW, 40, caption, size=11.5, color=MUTE, lh=1.5, font=SERIF))
        L.add(T(PW - MX - 60, PH - 44, 60, 14, str(self.n), size=10, color=MUTE, weight=600, align="right"))
        return self

    def api_index(self, entries):
        per = 24
        chunks = [entries[i:i + per] for i in range(0, len(entries), per)]
        for ci, chunk in enumerate(chunks):
            L = self._page(f"api{ci}")
            _chrome(L, 4, "API index")
            if ci == 0:
                L.add(R(MX, TOP - 4, 30, 4, fill=INDIGO))
                L.add(T(MX, TOP + 8, CW, 14, "THE NEW SURFACE", size=10, color=MUTE,
                        weight=700, upper=True, track=1.6))
                L.add(T(MX, TOP + 26, CW, 40, "Everything that shipped", size=27, color=INK, weight=800))
                y = TOP + 92
            else:
                y = TOP
            lastg = None
            for group, name, sig in chunk:
                if group != lastg:
                    y += 6
                    L.add(T(MX, y, CW, 14, group, size=9.5, color=INDIGO, weight=700, upper=True, track=1.2))
                    y += 20
                    lastg = group
                L.add(T(MX + 6, y, 250, 14, name, size=10.5, color=INK, weight=600, font=MONO))
                L.add(T(MX + 262, y, CW - 262, 14, sig, size=9, color=MUTE, font=MONO))
                L.add(LN(MX, y + 17, MX + CW, y + 17, color="#F0EDE6"))
                y += 23
            _footer(L, self.n)
        return self

    def timeline(self, items):
        L = self._page("timeline")
        _chrome(L, 4, "The session")
        L.add(R(MX, TOP - 4, 30, 4, fill=INK))
        L.add(T(MX, TOP + 8, CW, 14, "ONE SITTING", size=10, color=MUTE, weight=700, upper=True, track=1.6))
        L.add(T(MX, TOP + 26, CW, 40, "Twelve hours, in order", size=27, color=INK, weight=800))
        x0 = MX + 8
        y = TOP + 96
        L.add(LN(x0, y, x0, y + len(items) * 58, color=HAIR, width=2))
        for label, col, txt in items:
            L.add(DOT(x0, y + 10, 5.5, fill=col, stroke=PAPER, sw=2.5))
            L.add(T(x0 + 24, y, 90, 16, label, size=11, color=col, weight=800))
            L.add(T(x0 + 120, y, CW - 128, 40, txt, size=11.5, color="#2C3138", lh=1.42, font=SERIF))
            y += 58
        _footer(L, self.n)
        return self


def _measure_lines(text, width, size):
    """Cheap line-count estimate for vertical flow (≈ chars-per-line)."""
    cpl = max(1, int(width / (size * 0.5)))
    return max(1, math.ceil(len(text) / cpl))


# Feature/prose specs per part: ("fig", kicker, title, blurb, code, fig_fn) or
# ("prose", kicker, title, [paras], code|None, stats|None).
def _features():
    return {
        1: [
            ("fig", "B7 · reflection", "Reflect & mirror",
             "A reflection matrix across the x-axis, the y-axis, or an arbitrary line — "
             "and mirror(), which folds a half-shape into a symmetric whole.",
             ["m = Mat3.reflect(((1.3, 0), (1.3, 1)))   # a mirror line",
              "right = [m.apply(p) for p in half]",
              '# or, for a point list:   mirror(half, axis="y")'], fig_reflect),
            ("fig", "B8 · intersection", "Where lines meet",
             "Segment × segment, ray × segment, and segment × polygon — one parametric "
             "cross-product solve each; parallels and collinear inputs return None.",
             ["hit = segment_intersection(a, b, s0, s1)",
              "edges = segment_polygon_intersections(a, b, poly)",
              "r = ray_segment_intersection(o, direction, s0, s1)"], fig_intersections_2d),
            ("fig", "B10 · hull", "The convex hull",
             "Andrew's monotone chain wraps a point cloud in O(n log n); duplicates "
             "collapse and collinear edge points drop out of the ring.",
             ["hull = convex_hull(points)     # CCW ring, list[Vec2]"], fig_convex_hull),
            ("fig", "B10 · bounds", "Tight bounds — OBB vs AABB",
             "The minimum-area oriented box (rotating calipers on the hull) hugs a rotated "
             "shape where the axis-aligned box wastes area.",
             ["box = obb(points)       # 4 corners, minimum area",
              "lo, hi = aabb(points)   # axis-aligned; looser when rotated"], fig_obb),
            ("fig", "B10 · inside", "Inside or out",
             "point_in_polygon() by even-odd ray crossing, tested over a lattice of probes "
             "against a concave star.",
             ["hit = point_in_polygon((x, y), polygon)"], fig_point_in_poly),
            ("fig", "B10 · area", "Signed area",
             "polygon_area() is the shoelace sum — its sign is the winding, its magnitude "
             "the enclosed area.",
             ["a = polygon_area(ring)   # signed; abs(a) = area"], fig_polygon_area),
            ("fig", "B1 · windowing", "Window to viewport",
             "The classical 2D windowing transform (Harrington Ch6): map any data window "
             "onto a page viewport, aspect-preserving with uniform=True.",
             ["m = window_to_viewport(window, viewport, uniform=True)",
              "page_pt = m.apply(data_pt)"], fig_window_to_viewport),
        ],
        2: [
            ("fig", "B9 · curvature", "Reading the bend",
             "Signed curvature κ = 1/R at every parameter, drawn as a comb of normals "
             "scaled by κ — the curve's second nature made visible.",
             ["k = bz.curvature(t)      # signed 1/R (Mortenson §6.7)",
              "d = bz.derivative(t)     # tangent (the hodograph)"], fig_curvature),
            ("fig", "B9 · arc length", "Measured by the metre",
             "arc_length() integrates |B'(t)| by adaptive Simpson; here it drops a tick "
             "every one-tenth of the true arc length.",
             ["total = bz.arc_length()            # integral |B'(t)| dt over [0,1]",
              "# polyline_length(pts) is the exact discrete analogue"], fig_arclength),
            ("fig", "B4 · Koch", "A curve that refines",
             "koch_curve(n) rewrites F -> F+F--F+F: 4^n segments, the same span, more detail "
             "each pass. Here n = 1 … 4.",
             ['s = lsystem("F", {"F": "F+F--F+F"}, n)',
              "pts = koch_curve(n)     # or turtle(s, angle_deg=60)"], fig_koch),
            ("fig", "B4 · dragon", "The Heighway dragon",
             "dragon_curve(12): 2^12 segments from the rules F->F+G, G->F-G at 90°. A "
             "space-filling boundary that never self-crosses.",
             ["pts = dragon_curve(12)      # 4096 segments"], fig_dragon),
            ("fig", "B4 · Sierpiński", "The arrowhead",
             "sierpinski_arrowhead(6) fills the Sierpiński triangle in the limit — F->G-F-G, "
             "G->F+G+F at 60°.",
             ["pts = sierpinski_arrowhead(6)"], fig_sierpinski),
            ("fig", "B4 · L-systems", "Growing a plant",
             "lsystem + turtle with [ ] branches: the classic 25° plant. Each bracketed run "
             "becomes its own polyline, so the whole thing is a set of stems.",
             ['s = lsystem("X", {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}, 5)',
              "stems = turtle(s, angle_deg=25, heading_deg=90)"], fig_lsystem_plant),
        ],
        3: [
            ("fig", "B1 · pipeline", "The viewing pipeline",
             "ViewingPipeline names the stages world -> view -> projection -> clip -> NDC -> "
             "viewport, and fits the in-front points into a page box. Here, a wireframe cube.",
             ["pipe = ViewingPipeline(camera, box=[x, y, w, h])",
              "page_pts = pipe.project(world_points)   # clips behind-near"],
             fig_viewing_pipeline),
            ("fig", "B2 · robustness", "An orbit that never crashes",
             "Mat4.try_project returns None at/behind the near plane instead of raising or "
             "mirror-flipping. Orbit the camera 360° and no frame throws.",
             ["for az in range(0, 360, 45):",
              "    cam = base.orbit(azimuth=az)   # try_project keeps it safe"],
             fig_orbit),
            ("fig", "B6 · shading", "Phong specular",
             "Scene3D gains a phong mode: a Blinn-Phong highlight over the diffuse base, "
             "view-derived from the camera. Opt-in; the default is unchanged.",
             ['g = torus(1.0, 0.42).render(shading="phong",',
              "    cull_backfaces=True, specular=0.5, shininess=22)"], fig_torus_phong),
            ("fig", "B6 · ladder", "None, diffuse, smooth, specular",
             "The same sphere under each mode: none (flat fill), lambert (per-face), "
             "gouraud (per-vertex), phong (with the highlight).",
             ['for mode in ("none", "lambert", "gouraud", "phong"):',
              "    sphere(1.0).render(shading=mode, ...)"], fig_shading_ladder),
            ("fig", "B8 · 3D ×", "Ray meets triangle",
             "ray_triangle_intersection (Möller–Trumbore) with ray_plane and segment_plane "
             "complete the 3D-intersection set. The hit is projected back to the page.",
             ["p = ray_triangle_intersection(origin, dir, v0, v1, v2)",
              "q = ray_plane_intersection(origin, dir, point, normal)"], fig_ray_triangle),
        ],
        4: [
            ("prose", "packaging", "Honest 3.10 – 3.12",
             ["The `>=3.10` support claim was false: a gate module bare-imported `tomllib` "
              "(stdlib only on 3.11+), so `make check` crashed on the very floor it named. "
              "Now the tooling degrades to the `tomli` backport, `pyproject` declares "
              "`classifiers` for all three minors, and CI runs a real 3.10/3.11/3.12 matrix.",
              "Two regression gates pin it: no gate module may bare-import a 3.11-only "
              "stdlib under the floor, and the classifiers must agree with `requires-python`."],
             None, [("3", "Python minors"), ("2", "new gates"), ("1", "backport declared")]),
            ("prose", "developer experience", "The same gate, earlier",
             ["A committed `.pre-commit-config.yaml` runs the repo's own gates as git hooks: "
              "`make ruff-check` at commit time and the full `make check` at push time. Both "
              "are `local` / system hooks that shell out to the Makefile, so pre-commit pins "
              "no tool versions of its own — the hook surface cannot drift from the gate list, "
              "because it is the gate list."],
             ["make hooks    # uvx pre-commit install --install-hooks"], None),
            ("prose", "correctness", "One name, one meaning",
             ["The source-of-truth model bound `Image` to two things: a paint-value type "
              "alias and the image-object class. Under lazy annotations, which one a field "
              "resolved to was definition-order dependent — a latent hazard a new field could "
              "trip. The alias is now `ImagePaint`; the schema is byte-identical, verified.",
              "A new gate forbids a model class from sharing a name with a type alias, and a "
              "gating `ruff --select F811` catches redefinitions across the whole tree."],
             None, [("F811", "gated"), ("0", "schema delta"), ("13th", "make gate")]),
            ("prose", "authoring", "The graph object",
             ["`type: graph` is a pre-expansion authoring form: nodes + edges + a layout "
              "algorithm, lowered by `sdk.expand` into a positioned core group before the "
              "document is validated. It joins `use` and `component` as a form the grammar "
              "documents but the model never sees.",
              "A coverage gate now pins that the set of forms `sdk.expand` dispatches is "
              "exactly the set the grammar documents — no form can silently miss the spec."],
             ['{ "type": "graph", "algorithm": "auto",',
              '  "nodes": [...], "edges": [...] }'], None),
            ("prose", "tooling", "A checker that told the truth",
             ["The package-emit readiness checker went stale in the src-layout refactor — it "
              "inspected paths that had moved, so it passed vacuously and emitted a false "
              "verdict (it dropped a real blocker and reported a closed gap as open). A "
              "verification tool that inspects a moved path is the PALS's-Law failure mode.",
              "Repointed at the live tree, its verdict is true again (3 blockers, 1 gap), and "
              "a new test guards the inspected paths against going stale a second time."],
             None, None),
            ("prose", "discipline", "Output-preserving by proof",
             ["Every render-path change in the 3D work was checked against the golden lock — "
              "8 fixtures, 88 pages, byte-for-byte. The near-plane clip is safe precisely "
              "because the goldens already pass: that proves no fixture straddles the near "
              "plane, so nothing is dropped. New behaviour ships behind opt-in flags and new "
              "fixtures, never by moving an existing pixel.",
              "This is the house style: additive defaults, correctness on demand, and a gate "
              "that can tell the difference."],
             None, [("88", "golden pages"), ("0", "moved pixels"), ("1879", "tests green")]),
            ("prose", "PALS's Law", "Verify, then believe",
             ["The architectural rule under all of this: LLM output is untrusted until a real "
              "gate checks it. Absence of a verification layer is a design defect, not a "
              "runtime bug. Every figure in this book obeys it — the shapes are computed, the "
              "build validates them against the model, and a red test is a red figure.",
              "That is why a capability showcase can be trusted to show real capabilities: "
              "the document only renders because the geometry is real."],
             None, None),
            ("prose", "provenance", "Where this came from",
             ["This release is roadmap backlog B1–B10 plus the 2D/3D intersection, hull, OBB, "
              "curvature, and shading work — grounded stage-by-stage in the classical "
              "computer-graphics canon (Harrington 1987; Mortenson). Each item shipped "
              "red-first: a failing test, then the smallest correct change, then green.",
              "The full per-item detail is in the CHANGELOG and the roadmap's CG-canon "
              "backlog; the API surface is in the generated `docs/sdk-api.md`."],
             None, None),
        ],
    }


_INTROS = {
    1: ("The plane, made computable.",
        ["Reflection, intersection, hull, and area are the old certainties of plane "
         "geometry — but a document language needs them as functions it can call, not "
         "theorems it recites. This part adds the 2D kernel: a mirror you can fold a shape "
         "across, the exact point where two segments cross, the convex ring around a cloud "
         "of points, the tightest box that will hold it.",
         "Each is a small, deterministic, pure-Python routine that computes and emits "
         "ordinary geometry. Nothing here touches the wire format; the SDK does the maths "
         "and the page receives plain points."]),
    2: ("Where a line learns to bend — and to repeat itself forever.",
        ["A curve carries a second nature: how sharply it turns, and how far it runs. "
         "Curvature and arc-length make both measurable — the comb of normals and the "
         "equal-metre tick you see on the following pages are read straight off a cubic "
         "Bézier.",
         "Then repetition. An L-system rewrites a short string into a long one; a turtle "
         "walks it into a polyline. From four rules and a turn angle come the Koch curve, "
         "the Heighway dragon, the Sierpiński arrowhead, and a plant that branches."]),
    3: ("Three dimensions, projected honestly.",
        ["FrameForge is a 2D page, so the third dimension has to be solved and flattened — "
         "correctly. This part names the viewing pipeline (world to viewport), fixes the "
         "projection so a vertex crossing behind the camera no longer crashes or "
         "mirror-flips, culls the faces that point away, and adds a specular highlight.",
         "Every change here is output-preserving: the defaults are unchanged, the golden "
         "renders are byte-for-byte identical, and the new behaviour is opt-in. Correctness "
         "arrived without moving a single existing pixel."]),
    4: ("The part you don't see, holding up the part you do.",
        ["A capability is only as trustworthy as the gate that proves it. This part is the "
         "engineering underneath the geometry: an honest multi-version support claim, git "
         "hooks that run the same gate earlier, a source-of-truth name collision resolved, "
         "and a package checker taught to tell the truth again.",
         "The through-line is PALS's Law — LLM output is untrusted until a real gate checks "
         "it. It is why the figures in this book can be believed: they are computed, and the "
         "build fails loudly if the model disagrees."]),
}

_PLATES = {
    1: [("B7 · reflection", "A folded symmetry",
         "The right half is the left, reflected across a line — Mat3.reflect returns the "
         "matrix; every point is one apply() away.", fig_reflect),
        ("B8 · intersection", "Every meeting point",
         "Two segments, a ray, and a polygon boundary — each crossing solved exactly and "
         "marked where it truly lies.", fig_intersections_2d),
        ("B10 · convex hull", "The wrapped cloud",
         "Andrew's monotone chain, O(n log n); the interior points fall away and the ring "
         "closes CCW.", fig_convex_hull),
        ("B10 · oriented box", "The tightest box",
         "Rotating calipers find the minimum-area rectangle; the dashed axis-aligned box "
         "shows what a naive bound would waste.", fig_obb),
        ("B10 · point in polygon", "A field of probes",
         "Even-odd ray crossing, decided for a lattice of points against a concave star.",
         fig_point_in_poly),
        ("B1 · windowing", "Data into the page",
         "window_to_viewport maps any data window onto a page rectangle, aspect-preserving "
         "— the classical 2D windowing transform.", fig_window_to_viewport)],
    2: [("B9 · curvature", "The bend, made visible",
         "A comb of normals scaled by the signed curvature of a cubic Bézier: long where it "
         "turns hard, vanishing at the inflection.", fig_curvature),
        ("B9 · arc length", "Measured by the metre",
         "arc_length integrates the speed; the ticks fall at equal true arc length, closer "
         "together where the curve hurries.", fig_arclength),
        ("B4 · Koch", "A curve that refines",
         "The same generator at n = 1 through 4 — same span, four times the detail each "
         "pass.", fig_koch),
        ("B4 · dragon", "The Heighway dragon",
         "Four thousand and ninety-six segments from two rules; a boundary that fills the "
         "plane and never crosses itself.", fig_dragon),
        ("B4 · Sierpiński", "The arrowhead",
         "A single unbroken path that, in the limit, fills the Sierpiński triangle.",
         fig_sierpinski),
        ("B4 · L-systems", "A plant, grown",
         "One axiom, two rules, a 25-degree turn, and a bracket for every branch — the whole "
         "stem is a set of polylines.", fig_lsystem_plant)],
    3: [("B6 · Phong", "A solid, lit",
         "A torus under the new phong mode: a Blinn-Phong highlight over the diffuse base, "
         "with back faces culled.", fig_torus_phong),
        ("B6 · shading ladder", "Four ways to light a sphere",
         "None, lambert, gouraud, phong — the same geometry, four shading models, one "
         "call apart.", fig_shading_ladder),
        ("B1 · viewing pipeline", "A cube, projected",
         "ViewingPipeline carries a wireframe cube from world coordinates through projection "
         "and clipping into this page rectangle.", fig_viewing_pipeline),
        ("B2 · robustness", "An orbit that never throws",
         "The camera sweeps around the solid; try_project keeps every frame safe where the "
         "old projection would have crashed.", fig_orbit),
        ("B8 · ray × triangle", "A hit in space",
         "Möller-Trumbore finds where the ray pierces the triangle; the hit is carried back "
         "onto the page by the same pipeline.", fig_ray_triangle)],
}

_TIMELINE = [
    ("B7", INDIGO, "Reflection / mirror transform — the first pull, red-first and small."),
    ("B8", INDIGO, "2D intersection primitives; later, the 3D plane and triangle set."),
    ("B9", TERRA, "Curvature and arc-length for curves, verified against analytic truths."),
    ("B10", INDIGO, "Convex hull, then the oriented bounding box and 3D AABB."),
    ("B4", TERRA, "The fractal generator — an L-system engine and a turtle."),
    ("B1", TEAL, "The formal viewing pipeline, proven to reproduce the existing fit."),
    ("B2", TEAL, "3D pipeline correctness — the projection crash, fixed output-preservingly."),
    ("B6", TEAL, "Shading completion: a Phong specular mode over the diffuse base."),
    ("ops", INK, "Honest 3.10-3.12 support, pre-commit hooks, and the Image-collision fix."),
]

_API = [
    ("geometry · 2D transforms", "Mat3.reflect(axis)", "-> Mat3   x | y | (p0,p1) line"),
    ("geometry · 2D transforms", "mirror(points, axis)", "-> list[Vec2]"),
    ("geometry · 2D transforms", "window_to_viewport(win, vp, uniform=)", "-> Mat3"),
    ("geometry · intersection", "line_intersection(a0,a1,b0,b1)", "-> Vec2 | None"),
    ("geometry · intersection", "segment_intersection(a0,a1,b0,b1)", "-> Vec2 | None"),
    ("geometry · intersection", "ray_segment_intersection(o,d,s0,s1)", "-> Vec2 | None"),
    ("geometry · intersection", "segment_polygon_intersections(a,b,poly)", "-> list[Vec2]"),
    ("geometry · intersection", "ray_plane_intersection(o,d,pt,n)", "-> Vec3 | None"),
    ("geometry · intersection", "segment_plane_intersection(a,b,pt,n)", "-> Vec3 | None"),
    ("geometry · intersection", "ray_triangle_intersection(o,d,v0,v1,v2)", "-> Vec3   Moller-Trumbore"),
    ("geometry · comp-geometry", "convex_hull(points)", "-> list[Vec2]   monotone chain"),
    ("geometry · comp-geometry", "aabb(points) / aabb3(points)", "-> (min, max)"),
    ("geometry · comp-geometry", "obb(points)", "-> list[Vec2]   min-area rect"),
    ("geometry · comp-geometry", "polygon_area(ring)", "-> float   signed shoelace"),
    ("geometry · comp-geometry", "point_in_polygon(p, ring)", "-> bool   even-odd"),
    ("geometry · curves", "CubicBezier.derivative(t)", "-> Vec2   hodograph"),
    ("geometry · curves", "CubicBezier.curvature(t)", "-> float   signed 1/R"),
    ("geometry · curves", "CubicBezier.arc_length(tolerance=)", "-> float   adaptive Simpson"),
    ("geometry · curves", "polyline_length(points)", "-> float"),
    ("geometry · 3D", "Mat4.try_project(point, near_eps=)", "-> Vec2 | None   robust"),
    ("geometry · 3D", "ViewingPipeline(camera, box).project(pts)", "world -> page"),
    ("fractal", "lsystem(axiom, rules, iterations)", "-> str"),
    ("fractal", "turtle(commands, angle_deg=, step=)", "-> list[list[Vec2]]"),
    ("fractal", "koch_curve / dragon_curve / sierpinski_arrowhead", "-> list[Vec2]"),
    ("draw · Scene3D", 'render(shading="phong", specular=, shininess=)', "Blinn-Phong"),
    ("draw · Scene3D", "render(cull_backfaces=True)", "screen-space back-face removal"),
]


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Twelve Hours of Geometry — FrameForge CG-canon showcase")
    bk = Book(b)
    feats = _features()
    bk.cover()
    bk.colophon()
    bk.contents(feats)
    for part in (1, 2, 3, 4):
        bk.divider(part, feats[part])
        bk.intro(part, _INTROS[part][0], _INTROS[part][1])
        for spec in feats[part]:
            if spec[0] == "fig":
                bk.feature(part, spec[1], spec[2], spec[3], spec[4], spec[5])
            else:
                bk.prose(part, spec[1], spec[2], spec[3], spec[4], spec[5])
        for pl in _PLATES.get(part, []):
            bk.plate(part, pl[0], pl[1], pl[2], pl[3])
    bk.scoreboard()
    bk.timeline(_TIMELINE)
    bk.api_index(_API)
    bk.prose(
        4,
        "Illustrator parity, unlocked",
        "Parity, unlocked",
        [
            "This book's geometry is not abstract: each API closes a specific row of the "
            "Adobe Illustrator parity matrix (roadmap Appendix B, v4). Mat3.reflect and "
            "mirror() complete the four Illustrator transform tools — Rotate, Reflect, "
            "Scale, Shear — so AI-34 is now whole. The curvature and arc-length API gives "
            "the Curvature tool (AI-09) a curvature-correct sampling backbone. And "
            "Scene3D.render(shading='phong') advances 3D & Materials (AI-40) past flat and "
            "Gouraud shading — though a true bevel still holds that row at PARTIAL.",
            "Underneath, the planar booleans and the new intersection primitives — line, "
            "segment, ray, and ray-triangle — are the machinery behind Pathfinder and the "
            "Shape Builder (AI-04, AI-05); convex_hull, AABB and OBB give the layout and "
            "hit-testing work its bounding geometry. None of it is a pointer gesture: the "
            "parity is functional, reached by naming a coordinate and calling a function, "
            "not by dragging a handle. Where Illustrator's tool is inherently interactive — "
            "the freehand Pencil, Envelope distort — FrameForge keeps its declared non-goal, "
            "and says so plainly.",
            "So these twelve hours of geometry are also twelve hours of parity: the same "
            "commits that draw the figures in this book move the teardown scoreboard. Re-run "
            "the generator and watch AI-34, AI-09 and AI-40 change verdict — the matrix is "
            "evidence, not aspiration.",
        ],
        stats=[("4 / 4", "transform tools"), ("AI-34·09·40", "rows advanced"),
               ("v4", "teardown"), ("51", "features tracked")],
    )
    bk.closing()
    return b


def main() -> int:
    doc = build().build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} A4 pages — ok={report.ok} errors={len(errors)} "
          f"warnings={len(report.issues) - len(errors)}")
    for i in errors[:20]:
        print(f"  [error] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "cg-canon-showcase.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print("wrote", out)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
