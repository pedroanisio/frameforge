#!/usr/bin/env python3
"""GEOMETRY & TOPOLOGY — a reusable presentation *template* (FrameGraph SDK).

Ten 16:9 slides, each one a reusable layout archetype (cover, contents,
section divider, content-with-figure, full-bleed diagram, two-column
comparison, dual showcase, panel grid, closing) whose hero illustration is
produced by a *real* SDK geometry/topology helper rather than a flat image:

    * ``manifold.torus / sphere / mobius / klein_bottle / saddle``  — parametric
      surfaces projected through a perspective ``Camera`` and Lambert-shaded;
    * ``Scene3D.mesh``        — an icosahedron from its 12 golden-ratio vertices;
    * ``topology.Graph``      — spring / circular node-link layouts;
    * ``lattice("fcc")``      — a crystal block projected through the camera;
    * ``ScalarField`` + ``VectorField`` — marching-squares contours and a flow
      field of arrows.

Every mathematical claim on the slides is a standard result stated in full:
Euler's polyhedron formula ``V - E + F = 2``; the genus relation
``chi = 2 - 2g``; Gauss-Bonnet ``integral K dA = 2*pi*chi``; the handshake
lemma ``sum(deg) = 2|E|``; coordination numbers of the cubic lattices.

Provenance: AI-generated (Claude Opus 4.8) original illustration, authored
through ``framegraph.sdk`` and validated against the authoritative model
before serialisation. Geometry is grounded (icosahedron from the canonical
``cyclic-perm(0, +/-1, +/-phi)`` vertices; surfaces from their standard
parametrisations); layout coordinates are hand-composed.

Run from the repository root::

    uv run python examples/geometry_topology_deck.py            # build + validate + write YAML
    uv run python examples/geometry_topology_deck.py --render   # also write per-page SVGs
"""
from __future__ import annotations

import argparse
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    Camera,
    DocumentBuilder,
    Graph,
    ScalarField,
    Scene3D,
    Vec3,
    VectorField,
    klein_bottle,
    lattice,
    linear_gradient,
    mobius,
    radial_gradient,
    saddle,
    serialize,
    sphere,
    torus,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas, palette, type                                                        #
# --------------------------------------------------------------------------- #
W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
MX = 72                       # page margin
TOTAL = 10
PHI = (1.0 + 5.0 ** 0.5) / 2.0

INK0 = "#070c18"
INK1 = "#0d1730"
PANEL = "#12203f"
PANEL2 = "#0c1730"
LINE = "#2c3c64"
LINE_SOFT = "#1b2848"
GHOST = "#101d3c"
GLOW = "#1c3a6e"
SUB = "#93a4c4"
MUT = "#5e6f93"
WHITE = "#eef4ff"
GOLD = "#e8c45a"
GOLDD = "#b8902f"
CYAN = "#56d3c9"
BLUE = "#5aa9e6"
VIOL = "#a78bdb"
ROSE = "#f0a06f"
GREEN = "#73cf93"

DISPLAY = ["Space Grotesk", "Sora", "Inter", "Arial", "sans-serif"]
SANS = ["Inter", "Helvetica Neue", "Arial", "sans-serif"]
MONO = ["JetBrains Mono", "DejaVu Sans Mono", "Courier New", "monospace"]

STYLES = {
    "kicker": dict(font_family=SANS, font_size=14, font_weight=700, color=GOLD,
                   letter_spacing=3, text_transform="uppercase"),
    "cover_kick": dict(font_family=MONO, font_size=14, color=CYAN, letter_spacing=5,
                       text_transform="uppercase"),
    "title": dict(font_family=DISPLAY, font_size=42, font_weight=800, color=WHITE,
                  letter_spacing=-0.5, line_height=1.0),
    "big": dict(font_family=DISPLAY, font_size=104, font_weight=800, color=WHITE,
                letter_spacing=-3, line_height=0.92),
    "lead": dict(font_family=SANS, font_size=21, color=WHITE, line_height=1.4),
    "sub": dict(font_family=SANS, font_size=18, color=SUB, line_height=1.45),
    "body": dict(font_family=SANS, font_size=15.5, color=SUB, line_height=1.55),
    "bullet": dict(font_family=SANS, font_size=16.5, color=WHITE, line_height=1.45),
    "label": dict(font_family=SANS, font_size=12.5, font_weight=700, color=MUT,
                  letter_spacing=2, text_transform="uppercase"),
    "mono": dict(font_family=MONO, font_size=13, color=CYAN, letter_spacing=0.5),
    "formula": dict(font_family=MONO, font_size=22, font_weight=700, color=GOLD),
    "formula_s": dict(font_family=MONO, font_size=14, color=WHITE),
    "foot": dict(font_family=SANS, font_size=12, color=MUT, letter_spacing=1),
    "foot_r": dict(font_family=MONO, font_size=12, color=MUT, letter_spacing=1, align="right"),
    "idx": dict(font_family=MONO, font_size=20, font_weight=700, color=GOLD),
    "stat": dict(font_family=DISPLAY, font_size=34, font_weight=800, color=GOLD, align="center"),
    "statlab": dict(font_family=SANS, font_size=11, color=MUT, letter_spacing=1.5,
                    align="center", text_transform="uppercase"),
    "ghost": dict(font_family=DISPLAY, font_size=400, font_weight=800, color=GHOST,
                  line_height=0.9),
    "panel_t": dict(font_family=DISPLAY, font_size=20, font_weight=800, color=WHITE),
    "cap_c": dict(font_family=SANS, font_size=13.5, color=SUB, line_height=1.4, align="center"),
    "glyph_n": dict(font_family=MONO, font_size=18, font_weight=700, color=GOLD, align="center"),
    "chi_h": dict(font_family=MONO, font_size=13, font_weight=700, color=GOLD),
}

_SN = 0


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def T(page, box, text, style, **over):
    if over:
        merged = dict(STYLES[style]); merged.update(over)
        page.text(box, text, style=merged)
    else:
        page.text(box, text, style=style)


def stroke(width, color, *, dash=None, cap=None, join=None):
    st = {"stroke_width": width}
    if dash:
        st["stroke_dasharray"] = dash
    if cap:
        st["stroke_linecap"] = cap
    if join:
        st["stroke_linejoin"] = join
    return {"stroke": color, "stroke_style": st}


def lg(angle, *stops):
    return linear_gradient([(c, p) for c, p in stops], angle=angle)


def rg(*stops, at=None):
    return radial_gradient([(c, p) for c, p in stops], at=at)


LIGHT = Vec3(-0.45, -0.72, 0.55)


def render3d(scene, box, cam, fill, *, stroke_color="none", ambient=0.46, diffuse=0.62, id=None):
    """Lambert-shaded projection of a Scene3D into an absolute box.

    Scene3D.render() emits children local to the group box and depth-sorts
    near-last for perspective (draw.py::_avg_z), so passing the absolute target
    box is enough — no manual repositioning needed. Camera aspect is kept at 1.0
    so the surface is not pre-distorted; the renderer then fits it uniformly."""
    return scene.render(box=box, camera=cam, fill=fill, stroke=stroke_color,
                        shading="lambert", light=LIGHT, ambient=ambient, diffuse=diffuse, id=id)


def cam(eye, *, fov=33, target=(0.0, 0.0, 0.0)):
    return Camera(eye=Vec3(*eye), target=Vec3(*target), fov=fov, aspect=1.0)


# --------------------------------------------------------------------------- #
# Slide chrome (the reusable template scaffold)                                #
# --------------------------------------------------------------------------- #
def decor(page):
    """A faint glow plus concentric arcs anchored off the bottom-left corner.

    Wrapped in ``bleed()`` so the off-canvas flourish is exempt from the
    containment SHOULD (it is intentionally allowed to extend past the edge)."""
    with page.bleed():
        page.ellipse([W * 0.76, H * 0.30], 540, 380,
                     fill=rg((GLOW + "44", 0.0), (GLOW + "00", 1.0)))
        for r in (150, 240, 340, 450, 560):
            page.circle([-30, H + 40], r, fill="none", **stroke(1.0, LINE_SOFT))


def base_bg(page):
    page.rect([0, 0, W, H], fill=lg(155, (INK0, 0.0), (INK1, 0.62), (INK0, 1.0)))
    decor(page)
    page.rect([0, 0, 7, H], fill=lg(180, (GOLD, 0.0), (CYAN, 1.0)))


def slide(b, sid, kicker, title, *, ghost=None, accent=GOLD):
    global _SN
    _SN += 1
    page = b.page(sid, canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    base_bg(page)
    if ghost is not None:
        with page.bleed():   # decorative oversized numeral may bleed past the edge
            T(page, [W - 540, 24, 760, 540], ghost, "ghost")
    page.layer("chrome")
    T(page, [MX, 56, W - 2 * MX - 160, 20], kicker, "kicker", color=accent)
    T(page, [MX, 86, W - 2 * MX, 56], title, "title")
    page.rect([MX, H - 54, W - 2 * MX, 1.4], fill=LINE)
    T(page, [MX, H - 40, 760, 16], "GEOMETRY & TOPOLOGY  ·  DECK TEMPLATE", "foot")
    T(page, [W - MX - 220, H - 40, 220, 16], f"{_SN:02d} / {TOTAL:02d}", "foot_r")
    page.layer("body")
    return page


def panel(page, box, *, title=None, accent=None):
    page.rect(box, fill=lg(160, (PANEL, 0.0), (PANEL2, 1.0)),
              stroke=LINE_SOFT, stroke_style={"stroke_width": 1.2}, radius=16)
    if accent:
        page.rect([box[0], box[1], 44, 3], fill=accent, radius=2)
    if title:
        T(page, [box[0] + 22, box[1] + 16, box[2] - 44, 24], title, "panel_t")
    return box


def stat(page, x, y, value, label, w=150):
    T(page, [x, y, w, 40], value, "stat")
    T(page, [x, y + 42, w, 16], label, "statlab")


def chip(page, x, y, w, text, *, h=44, style="formula"):
    page.rect([x, y, w, h], fill="#0a142c", stroke=GOLDD,
              stroke_style={"stroke_width": 1.2}, radius=10)
    T(page, [x, y + (h - 26) / 2, w, 30], text, style, align="center")


# --------------------------------------------------------------------------- #
# Geometry: the icosahedron mesh (canonical golden-ratio vertices)             #
# --------------------------------------------------------------------------- #
def icosahedron():
    p = PHI
    verts = [
        (-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0),
        (0, -1, p), (0, 1, p), (0, -1, -p), (0, 1, -p),
        (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1),
    ]
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    return Scene3D().mesh(verts, faces)


# --------------------------------------------------------------------------- #
# Golden rectangle + logarithmic golden spiral                                 #
# --------------------------------------------------------------------------- #
def golden_figure(page, box):
    """A φ:1 rectangle with its square subdivisions and a true logarithmic
    golden spiral (quarter-turn growth = φ), anchored at the rectangle's
    accumulation point (intersection of the reciprocal diagonals)."""
    x, y, w, h = box
    gh = min(h, w / PHI)
    gw = gh * PHI
    rx = x + (w - gw) / 2.0
    ry = y + (h - gh) / 2.0
    sub_w = gw - gh                          # width of the right reciprocal rect
    page.rect([rx, ry, gw, gh], fill="none", **stroke(1.2, LINE))
    page.line([rx + gh, ry], [rx + gh, ry + gh], **stroke(1.0, LINE_SOFT))
    page.line([rx + gh, ry + sub_w], [rx + gw, ry + sub_w], **stroke(1.0, LINE_SOFT))

    t = PHI / math.sqrt(5.0)                 # diagonal-intersection parameter
    eye_x = rx + gw * t
    eye_y = ry + gh * t
    r0 = math.hypot(gw * t, gh * t)          # eye → far (top-left) corner
    phase0 = math.atan2(-gh * t, -gw * t)
    k = math.log(PHI) / (math.pi / 2.0)
    pts = []
    n, turns = 170, 2.4
    for i in range(n + 1):
        th = turns * 2 * math.pi * i / n
        r = r0 * math.exp(-k * th)
        ang = phase0 - th
        pts.append([eye_x + r * math.cos(ang), eye_y + r * math.sin(ang)])
    page.polyline(pts, smooth=True, fill="none", **stroke(2.6, GOLD, cap="round"))


# --------------------------------------------------------------------------- #
# Slide 01 — Cover                                                             #
# --------------------------------------------------------------------------- #
def s01_cover(b):
    global _SN
    _SN += 1
    page = b.page("cover", canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill=lg(150, (INK0, 0.0), ("#101d3e", 0.55), (INK0, 1.0)))
    decor(page)
    page.rect([0, 0, 7, H], fill=lg(180, (GOLD, 0.0), (CYAN, 1.0)))

    page.layer("hero")
    page.add(render3d(torus(1.0, 0.42, steps_u=30, steps_v=14),
                      [688, 150, 528, 460], cam((0.25, 1.7, 3.1), fov=32),
                      GOLD, id="cover_torus"))

    page.layer("type")
    with page.lettering():
        T(page, [MX, 150, 560, 22], "FrameGraph SDK  ·  Deck Template  ·  v1.0", "cover_kick")
        T(page, [MX, 224, 640, 230], "GEOMETRY\n& TOPOLOGY", "big")
        page.rect([MX + 4, 452, 92, 4], fill=GOLD)
        T(page, [MX, 478, 540, 120],
          "A reusable slide kit for talks on shapes, surfaces and networks — "
          "and the spaces in between.", "sub")
        T(page, [MX, 620, 640, 18],
          "shapes · polyhedra · graphs · manifolds · curvature · lattices", "mono")


# --------------------------------------------------------------------------- #
# Slide 02 — Contents                                                          #
# --------------------------------------------------------------------------- #
CONTENTS = [
    (3, "Foundations", "Polygons, proportion and the golden ratio"),
    (4, "Polyhedra", "The five Platonic solids and Euler's formula"),
    (5, "Networks", "Graphs, layouts, degree and connectivity"),
    (6, "Surfaces & genus", "Spheres, tori, and how to count holes"),
    (7, "Non-orientable", "Mobius bands and the Klein bottle"),
    (8, "Fields & lattices", "Curvature, flow fields, crystals and tilings"),
]


def s02_contents(b):
    page = slide(b, "contents", "Overview", "Contents", ghost="·")
    x = MX
    y0, rh = 196, 74
    with page.lettering():
        for i, (sides, name, desc) in enumerate(CONTENTS):
            y = y0 + i * rh
            cy = y + 26
            page.regular_polygon([x + 26, cy], 22, sides, rotation=-90,
                                 fill="none", **stroke(2.0, GOLD if i % 2 == 0 else CYAN))
            T(page, [x + 70, y + 2, 60, 30], f"{i + 1:02d}", "idx")
            T(page, [x + 132, y - 2, 520, 34], name, "lead")
            T(page, [x + 132, y + 34, 620, 22], desc, "body")
            page.rect([x + 70, y + 62, 760, 1], fill=LINE_SOFT)
        T(page, [930, 540, 280, 18], "six sections · one toolkit", "cap_c")
    # ring teaser (already one group — not flagged by the tabular heuristic)
    g = Graph()
    ring = [f"n{i}" for i in range(8)]
    for n in ring:
        g.node(n)
    for i in range(8):
        g.edge(ring[i], ring[(i + 1) % 8])
    g.edge("n0", "n3"); g.edge("n1", "n5"); g.edge("n2", "n6")
    page.add(g.render(g.circular_layout(), box=[930, 250, 280, 280],
                      node_radius=8, node_fill=CYAN, node_stroke="#0b2a28",
                      edge_color=GOLDD, edge_width=1.4, labels=False, id="toc_ring"))


# --------------------------------------------------------------------------- #
# Slide 03 — Section divider + Foundations content                            #
# --------------------------------------------------------------------------- #
def s03_foundations(b):
    page = slide(b, "foundations", "Section 01 · Points, lines & proportion",
                 "Foundations", ghost="01")
    with page.lettering():
        T(page, [MX, 208, 600, 24], "The regular n-gon converges to the circle", "label")
        xs = MX + 36
        base_y = 300
        seq = [3, 4, 5, 6, 8, 12]
        for k, n in enumerate(seq):
            cx = xs + k * 96
            page.regular_polygon([cx, base_y], 36, n, rotation=-90,
                                 fill="none", **stroke(2.0, CYAN))
            T(page, [cx - 36, base_y + 54, 72, 18], f"n={n}", "glyph_n", font_size=13)
        cx = xs + len(seq) * 96
        page.circle([cx, base_y], 36, fill="none", **stroke(2.0, GOLD))
        T(page, [cx - 40, base_y + 54, 80, 18], "n → ∞", "glyph_n", font_size=13)
        T(page, [MX, 392, 660, 70],
          "Increase the sides of a regular polygon and its perimeter approaches a "
          "circle — the first idea of a limit, drawn.", "body")

        gp = [800, 200, 408, 420]
        panel(page, gp, title="The golden ratio", accent=GOLD)
        golden_figure(page, [gp[0] + 36, gp[1] + 66, gp[2] - 72, 246])
        chip(page, gp[0] + 30, gp[1] + 336, gp[2] - 60, "φ = (1+√5)/2 ≈ 1.618")
        T(page, [gp[0] + 30, gp[1] + 388, gp[2] - 60, 20],
          "a : b  =  (a + b) : a", "cap_c")


# --------------------------------------------------------------------------- #
# Slide 04 — Polyhedra (content + figure)                                      #
# --------------------------------------------------------------------------- #
def s04_polyhedra(b):
    page = slide(b, "polyhedra", "Section 02 · Regular polyhedra",
                 "The Platonic solids", ghost="02")
    with page.lettering():
        bullets = [
            "Five — and only five — convex regular polyhedra exist.",
            "Identical regular-polygon faces meet alike at every vertex.",
            "Their faces are limited to the triangle, square, and pentagon.",
        ]
        by = 196
        for tline in bullets:
            page.regular_polygon([MX + 7, by + 11], 7, 3, rotation=-90, fill=GOLD)
            T(page, [MX + 26, by, 540, 50], tline, "bullet")
            by += 60
        chip(page, MX, 388, 290, "V − E + F = 2")
        T(page, [MX + 306, 386, 240, 50], "Euler's\npolyhedron formula", "body")
        platonic_table(page, [MX, 466, 540, 178])

        T(page, [700, 150, 480, 18],
          "icosahedron · 20 faces · 12 vertices · 30 edges", "cap_c")
        glyphs = [(3, GOLD, "3"), (4, CYAN, "4"), (5, VIOL, "5")]
        gx0, gy = 800, 522
        for k, (n, col, lab) in enumerate(glyphs):
            cx = gx0 + k * 130
            page.regular_polygon([cx, gy], 34, n, rotation=-90, fill="none",
                                 **stroke(2.2, col))
            T(page, [cx - 30, gy + 44, 60, 22], lab, "glyph_n")
        T(page, [700, 592, 480, 18],
          "the only regular faces a Platonic solid can use", "cap_c")

    page.add(render3d(icosahedron(), [700, 168, 480, 318],
                      cam((1.5, 1.15, 2.45), fov=34), "#54cfc5",
                      stroke_color="#0a1426", ambient=0.42, diffuse=0.66,
                      id="icosahedron"))


def platonic_table(page, box):
    x, y, w, h = box
    cols = [x, x + 200, x + 290, x + 380, x + 470]
    headers = ["SOLID", "V", "E", "F"]
    rows = [
        ("Tetrahedron", "4", "6", "4", "2"),
        ("Cube", "8", "12", "6", "2"),
        ("Octahedron", "6", "12", "8", "2"),
        ("Dodecahedron", "20", "30", "12", "2"),
        ("Icosahedron", "12", "30", "20", "2"),
    ]
    page.rect([x, y, w, 28], fill="#0a142c", radius=6)
    for c, htxt in zip(cols, headers):
        T(page, [c + 10, y + 6, 120, 16], htxt, "label", color=GOLD, letter_spacing=1)
    T(page, [cols[4] + 10, y + 5, 60, 18], "χ", "chi_h")   # not uppercased
    ry = y + 34
    for r in rows:
        for c, val, st in zip(cols, r, ["bullet", "mono", "mono", "mono", "mono"]):
            T(page, [c + 10, ry, 150, 20], val, st,
              font_size=14, color=(WHITE if st == "bullet" else CYAN))
        ry += 28
    page.rect([cols[4] - 8, y, 1, h], fill=LINE_SOFT)


# --------------------------------------------------------------------------- #
# Slide 05 — Networks (full-bleed diagram)                                     #
# --------------------------------------------------------------------------- #
def s05_networks(b):
    page = slide(b, "networks", "Section 03 · Graph topology",
                 "Graphs & networks", ghost="03")
    g = Graph()
    clusters = {"A": ["a1", "a2", "a3", "a4"], "B": ["b1", "b2", "b3"],
                "C": ["c1", "c2", "c3"]}
    nodes, edges = set(), set()

    def add_edge(u, v):
        g.edge(u, v)
        edges.add(frozenset((u, v)))

    for hub, members in clusters.items():
        g.node(hub, weight=2.1); nodes.add(hub)
        for m in members:
            g.node(m); nodes.add(m)
            add_edge(hub, m)
        for i in range(len(members)):
            add_edge(members[i], members[(i + 1) % len(members)])
    add_edge("A", "B"); add_edge("B", "C"); add_edge("C", "A")
    nV, nE = len(nodes), len(edges)

    page.add(g.render(g.spring_layout(iterations=260), box=[560, 156, 664, 432],
                      node_radius=11, node_fill=CYAN, node_stroke="#0b2a28",
                      node_stroke_width=2.0, edge_color=GOLDD, edge_width=1.6,
                      labels=False, id="mesh_graph"))

    with page.lettering():
        T(page, [MX, 196, 430, 90],
          "A network is pure topology — only which vertices connect, not where "
          "they sit. The layout is just a drawing choice.", "body")
        chip(page, MX, 300, 430, "Σ deg(v) = 2·|E|   (handshake lemma)", h=46, style="formula_s")
        stat(page, MX, 380, str(nV), "vertices |V|", w=120)
        stat(page, MX + 150, 380, str(nE), "edges |E|", w=120)
        stat(page, MX + 300, 380, str(2 * nE), "Σ degrees", w=130)
        T(page, [MX, 470, 430, 20], "Spring (force-directed) layout", "label")
        T(page, [MX, 496, 430, 90],
          "Nodes repel; edges pull like springs. The deterministic equilibrium "
          "reveals clusters and bridges.", "body")
        T(page, [560, 600, 664, 18],
          "Graph.spring_layout() · one deterministic FrameGraph group", "cap_c")


# --------------------------------------------------------------------------- #
# Slide 06 — Surfaces & genus (two-column comparison)                          #
# --------------------------------------------------------------------------- #
def s06_genus(b):
    page = slide(b, "genus", "Section 04 · Closed surfaces",
                 "Surfaces & genus", ghost="04")
    pw, ph = 524, 360
    lx, rx = MX, MX + pw + 40
    py = 188
    panel(page, [lx, py, pw, ph], accent=BLUE)
    panel(page, [rx, py, pw, ph], accent=GOLD)

    page.add(render3d(sphere(1.0, steps_u=24, steps_v=14),
                      [lx + 30, py + 30, pw - 60, 244], cam((0.0, 0.5, 3.0), fov=32),
                      BLUE, id="genus_sphere"))
    page.add(render3d(torus(1.0, 0.42, steps_u=28, steps_v=14),
                      [rx + 30, py + 30, pw - 60, 244], cam((0.1, 1.95, 2.7), fov=32),
                      GOLD, id="genus_torus"))

    with page.lettering():
        T(page, [lx + 28, py + 280, pw - 56, 24], "Sphere", "panel_t")
        T(page, [rx + 28, py + 280, pw - 56, 24], "Torus", "panel_t")
        stat(page, lx + 28, py + 312, "g = 0", "genus / holes", w=150)
        stat(page, lx + 200, py + 312, "χ = 2", "Euler char.", w=150)
        stat(page, rx + 28, py + 312, "g = 1", "genus / holes", w=150)
        stat(page, rx + 200, py + 312, "χ = 0", "Euler char.", w=150)
        chip(page, W / 2 - 190, py + ph + 18, 380, "χ = 2 − 2g")
        T(page, [MX, py + ph + 74, W - 2 * MX, 20],
          "Genus counts the holes; the Euler characteristic falls by 2 for each. "
          "Topology sees a coffee mug and a doughnut as the same surface.", "cap_c")


# --------------------------------------------------------------------------- #
# Slide 07 — Non-orientable surfaces (dual showcase)                           #
# --------------------------------------------------------------------------- #
def s07_nonorientable(b):
    page = slide(b, "nonorientable", "Section 05 · One-sided surfaces",
                 "Non-orientable surfaces", ghost="05")
    pw, ph = 524, 380
    lx, rx = MX, MX + pw + 40
    py = 184
    panel(page, [lx, py, pw, ph], accent=VIOL)
    panel(page, [rx, py, pw, ph], accent=CYAN)

    page.add(render3d(mobius(1.0, 0.42, steps_u=48, steps_v=6),
                      [lx + 24, py + 46, pw - 48, 250], cam((0.25, 1.65, 2.85), fov=34),
                      VIOL, ambient=0.5, diffuse=0.6, id="mobius"))
    page.add(render3d(klein_bottle(0.26, steps_u=30, steps_v=16),
                      [rx + 24, py + 46, pw - 48, 250], cam((0.1, 0.35, 3.2), fov=34),
                      CYAN, ambient=0.5, diffuse=0.6, id="klein"))

    with page.lettering():
        T(page, [lx + 28, py + 18, pw - 56, 24], "Möbius band", "panel_t")
        T(page, [rx + 28, py + 18, pw - 56, 24], "Klein bottle", "panel_t")
        T(page, [lx + 28, py + 306, pw - 56, 56],
          "One side, one boundary edge. Walk the strip and you return mirror-reversed.",
          "body")
        T(page, [rx + 28, py + 306, pw - 56, 56],
          "Closed, no boundary, no inside. It only embeds without self-crossing in 4D.",
          "body")
        T(page, [MX, py + ph + 20, W - 2 * MX, 20],
          "Non-orientable: there is no consistent global choice of \"outward\". Both have χ = 0.",
          "cap_c")


# --------------------------------------------------------------------------- #
# Slide 08 — Curvature & fields (panel pair)                                   #
# --------------------------------------------------------------------------- #
def s08_fields(b):
    page = slide(b, "fields", "Section 06a · Curvature & flow",
                 "Curvature & fields", ghost="06")
    pw, ph = 524, 392
    lx, rx = MX, MX + pw + 40
    py = 184
    panel(page, [lx, py, pw, ph], title="Scalar field + flow", accent=CYAN)
    panel(page, [rx, py, pw, ph], title="Negative curvature", accent=ROSE)

    fbox = [lx + 24, py + 54, pw - 48, 256]

    def pot(x, y):
        r1 = math.hypot(x - 0.45, y) + 0.12
        r2 = math.hypot(x + 0.45, y) + 0.12
        return 1.0 / r1 - 1.0 / r2

    sf = ScalarField(pot, domain=(-1.5, -1.0, 1.5, 1.0))
    page.add(sf.contours(box=fbox, levels=11, steps_x=34, steps_y=24,
                         color="#3f7fb0", width=1.1, id="contours"))

    def flow(x, y):
        return (-y - 0.25 * x, x - 0.25 * y)

    vf = VectorField(flow, domain=(-1.5, -1.0, 1.5, 1.0))
    page.add(vf.render(box=fbox, steps_x=13, steps_y=9, color=BLUE, warm=GOLD,
                       width=1.4, head=5.0, id="flow"))

    page.add(render3d(saddle(1.0, steps=18), [rx + 24, py + 54, pw - 48, 236],
                      cam((1.7, 1.6, 2.0), fov=34), ROSE, ambient=0.48, diffuse=0.6,
                      id="saddle"))

    with page.lettering():
        T(page, [lx + 24, py + ph - 64, pw - 48, 50],
          "Iso-contours of a dipole potential, overlaid with its circulation field.",
          "body")
        T(page, [rx + 24, py + 300, pw - 48, 24], "K < 0   ·   z = x² − y²", "formula_s")
        T(page, [rx + 24, py + 330, pw - 48, 50],
          "Curvature sign: K>0 sphere · K=0 plane · K<0 saddle.   Gauss–Bonnet: ∮K dA = 2πχ.",
          "body")


# --------------------------------------------------------------------------- #
# Slide 09 — Lattices & tilings (panel pair)                                   #
# --------------------------------------------------------------------------- #
def s09_lattices(b):
    page = slide(b, "lattices", "Section 06b · Periodic structure",
                 "Lattices & tilings", ghost="06")
    pw, ph = 524, 392
    lx, rx = MX, MX + pw + 40
    py = 184
    panel(page, [lx, py, pw, ph], title="Crystal lattice — FCC", accent=BLUE)
    panel(page, [rx, py, pw, ph], title="Hexagonal tiling", accent=GREEN)

    lat = lattice("fcc", nx=3, ny=3, nz=2, a=1.0)
    cam_l = Camera(eye=Vec3(3.4, 2.7, 4.0), target=Vec3(1.0, 0.5, 0.5), fov=40, aspect=1.0)
    page.add(lat.render(box=[lx + 24, py + 50, pw - 48, 268], camera=cam_l,
                        node_radius=6.5, node_fill=BLUE, node_stroke="#0b1830",
                        edge_color="#39507e", edge_width=1.1, id="fcc"))
    hex_tiling(page, [rx + 24, py + 50, pw - 48, 268])

    with page.lettering():
        T(page, [lx + 24, py + 322, pw - 48, 56],
          "Face-centred cubic — atoms at every cube corner and face centre "
          "(coordination number 12).", "body")
        T(page, [rx + 24, py + 322, pw - 48, 56],
          "The honeycomb (graphene) tiling — regular hexagons, three meeting at "
          "every vertex.", "body")


def hex_tiling(page, box):
    x, y, w, h = box
    R = 26.0
    dx = 1.5 * R
    dy = math.sqrt(3) * R
    cols = int((w - 30) / dx)
    rows = int((h - 20) / dy) + 1
    for i in range(cols):
        for j in range(rows):
            cx = x + 40 + i * dx
            cy = y + 36 + j * dy + (dy / 2 if i % 2 else 0.0)
            if cx > x + w - 20 or cy > y + h - 16:
                continue
            page.regular_polygon([cx, cy], R, 6, rotation=90,
                                 fill="none", **stroke(1.6, GREEN))
            page.circle([cx, cy], 2.4, fill=GREEN)


# --------------------------------------------------------------------------- #
# Slide 10 — Closing                                                           #
# --------------------------------------------------------------------------- #
def s10_closing(b):
    global _SN
    _SN += 1
    page = b.page("closing", canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill=lg(150, (INK0, 0.0), ("#0f1d3e", 0.55), (INK0, 1.0)))
    decor(page)
    page.rect([0, 0, 7, H], fill=lg(180, (GOLD, 0.0), (CYAN, 1.0)))

    page.layer("hero")
    golden_figure(page, [752, 196, 416, 320])

    page.layer("type")
    with page.lettering():
        T(page, [MX, 224, 560, 22], "End of template", "cover_kick")
        T(page, [MX, 286, 600, 130], "Thank you.", "big", font_size=92)
        T(page, [MX, 410, 540, 110],
          "Swap the heroes, keep the scaffold. Every figure here is regenerated "
          "from code — edit a parameter, re-render the slide.", "sub")
        T(page, [MX, 560, 840, 18],
          "FrameGraph SDK · AI-generated (Claude Opus 4.8) · all geometry computed, not drawn",
          "mono")
        T(page, [MX, H - 40, 760, 16], "GEOMETRY & TOPOLOGY  ·  DECK TEMPLATE", "foot")
        T(page, [W - MX - 220, H - 40, 220, 16], f"{TOTAL:02d} / {TOTAL:02d}", "foot_r")


# --------------------------------------------------------------------------- #
# Assemble                                                                     #
# --------------------------------------------------------------------------- #
PAGES = [
    s01_cover, s02_contents, s03_foundations, s04_polyhedra, s05_networks,
    s06_genus, s07_nonorientable, s08_fields, s09_lattices, s10_closing,
]


def build() -> DocumentBuilder:
    global _SN
    _SN = 0
    b = DocumentBuilder(title="Geometry & Topology — Deck Template",
                        profile="deck", lang="en")
    for name, style in STYLES.items():
        b.define_text_style(name, **style)
    for fn in PAGES:
        fn(b)
    return b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yaml", default=os.path.join(ROOT, "fixtures", "geometry-topology-deck.fg.yaml"))
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "geometry-topology"))
    args = ap.parse_args()

    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} slides — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in errors[:40]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    if warns:
        from collections import Counter
        for code, c in Counter(i.rule_id for i in warns).most_common():
            print(f"  warn x{c}: {code}")

    os.makedirs(os.path.dirname(args.yaml), exist_ok=True)
    with open(args.yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {args.yaml}")

    if args.render:
        from framegraph.sdk.conform import render_page_svgs
        svgs = render_page_svgs(doc, base_dir=ROOT)
        os.makedirs(args.out, exist_ok=True)
        for idx, svg in enumerate(svgs, 1):
            with open(os.path.join(args.out, f"slide-{idx:02d}.svg"), "w", encoding="utf-8") as fh:
                fh.write(svg)
        print(f"Rendered {len(svgs)} SVG slides to {args.out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
