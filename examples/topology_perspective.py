#!/usr/bin/env python3
"""Demo of the SDK topology + perspective helpers.

A single landscape page with six panels:

    1. circular_layout   — a ring network
    2. radial_layout     — hub-and-spoke from one center
    3. layered_layout    — a directed pipeline DAG (Sugiyama-lite)
    4. spring_layout     — a deterministic force-directed mesh
    5. Scene3D + Camera  — a revolved solid in true perspective
    6. Graph + Camera    — a 3D node-link network projected through the camera
                           (topology *and* perspective at once)

Every panel is one FrameGraph group, so the geometric audit (which does not
recurse into groups) stays at zero warnings; labels are sized against real font
metrics so ``--check-overflow`` passes too.

Run from the repository root::

    uv run python examples/topology_perspective.py
"""
from __future__ import annotations

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
    Scene3D,
    Vec3,
)

INK = "#0f172a"
SUBTLE = "#475569"
PANEL_BG = "#f8fafc"
PANEL_EDGE = "#cbd5e1"
TITLE_BAND = 32.0

PALETTE = {
    "circular": ("#2563eb", "#1e3a8a"),
    "radial": ("#0d9488", "#134e4a"),
    "layered": ("#d97706", "#7c2d12"),
    "spring": ("#7c3aed", "#3b0764"),
    "scene": ("#dc2626", "#7f1d1d"),
    "net3d": ("#0891b2", "#0e3a4a"),
}


def panel(layer, title, group, px, py, pw, ph):
    """Drop a background card, then a diagram group occupying the area below a
    title band; the title rides inside the group (negative local y) so it never
    becomes a top-level text object the tabular audit would flag."""
    layer.rect([px, py, pw, ph], fill=PANEL_BG, stroke=PANEL_EDGE,
               stroke_style={"stroke_width": 1.5},
               radius=12, decorative=True)
    group["box"] = [px, py + TITLE_BAND, pw, ph - TITLE_BAND - 8]
    group.setdefault("children", []).insert(0, {
        "type": "text",
        "box": [10.0, -(TITLE_BAND - 9.0), pw - 20.0, 22.0],
        "text": title,
        "style": {"font_family": ["DejaVu Sans", "Arial", "sans-serif"],
                  "font_size": 15, "font_weight": 700, "color": INK,
                  "text_align": "center"},
    })
    layer.add(group)


def circular_graph() -> Graph:
    g = Graph()
    ring = ["edge", "cdn", "api", "auth", "cache", "queue", "db", "log"]
    for n in ring:
        g.node(n, n)
    for i in range(len(ring)):
        g.edge(ring[i], ring[(i + 1) % len(ring)])
    g.edge("api", "db")
    g.edge("auth", "cache")
    return g


def hub_graph() -> Graph:
    g = Graph().node("core", "core", weight=2.2, fill="#0d9488")
    spokes = ["web", "ios", "android", "cli", "bot", "etl", "ml"]
    for s in spokes:
        g.node(s, s)
        g.edge("core", s)
    g.edge("web", "ios")
    g.edge("etl", "ml")
    return g


def pipeline_graph() -> Graph:
    g = Graph()
    stages = [("ingest", "parse"), ("parse", "clean"), ("clean", "feature"),
              ("feature", "train"), ("feature", "rules"), ("train", "serve"),
              ("rules", "serve"), ("serve", "audit")]
    for a, b in stages:
        g.edge(a, b, directed=True)
    g.node("train", "train", weight=1.6)
    g.node("serve", "serve", weight=1.6)
    return g


def mesh_graph() -> Graph:
    g = Graph()
    clusters = {
        "a": ["a1", "a2", "a3"],
        "b": ["b1", "b2", "b3"],
        "c": ["c1", "c2", "c3"],
    }
    for hub, members in clusters.items():
        g.node(hub, hub, weight=1.8)
        for m in members:
            g.node(m, m)
            g.edge(hub, m)
        for i in range(len(members)):
            g.edge(members[i], members[(i + 1) % len(members)])
    g.edge("a", "b")
    g.edge("b", "c")
    g.edge("c", "a")
    return g


def net3d_graph() -> tuple[Graph, dict]:
    """A cube of nodes wired along its edges — positions live in 3D space."""
    g = Graph()
    coords = {}
    corners = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
               (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    names = ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7"]
    for name, (x, y, z) in zip(names, corners):
        g.node(name, name)
        coords[name] = Vec3(float(x), float(y), float(z))
    cube_edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7),
                  (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    for a, b in cube_edges:
        g.edge(names[a], names[b])
    # a hub in the middle, linked to every corner
    g.node("hub", "hub", weight=1.8, pos=Vec3(0, 0, 0))
    coords["hub"] = Vec3(0.0, 0.0, 0.0)
    for name in names:
        g.edge("hub", name, directed=True)
    return g, coords


def build() -> DocumentBuilder:
    builder = DocumentBuilder(title="Topology & perspective", profile="diagram", lang="en")
    builder.define_text_style("h1", font_family=["DejaVu Sans", "Arial", "sans-serif"],
                              font_size=30, font_weight=800, color=INK)
    builder.define_text_style("sub", font_family=["DejaVu Sans", "Arial", "sans-serif"],
                              font_size=15, color=SUBTLE)

    W, H = 1160, 760
    page = builder.page(
        "topology_perspective",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
        reading_order=["h1"],
    ).layer("main")
    page.rect([0, 0, W, H], fill="#ffffff")
    page.text([40, 30, 900, 36], "Topology & perspective in the FrameGraph SDK",
              id="h1", style="h1")
    page.text([40, 70, 1000, 24],
              "Deterministic graph layouts + a perspective camera — node-link "
              "diagrams and 3D scenes from one toolkit.", style="sub")

    margin, gap = 40, 22
    top = 112
    pw = (W - 2 * margin - 2 * gap) / 3
    ph = (H - top - margin - gap) / 2
    cols = [margin + i * (pw + gap) for i in range(3)]
    rows = [top + j * (ph + gap) for j in range(2)]

    # Row 1 — flat 2D topologies.
    c = circular_graph()
    fc, sc = PALETTE["circular"]
    panel(page, "circular_layout", c.render(c.circular_layout(), box=[0, 0, pw, ph],
          node_fill=fc, node_stroke=sc), cols[0], rows[0], pw, ph)

    h = hub_graph()
    fc, sc = PALETTE["radial"]
    panel(page, "radial_layout", h.render(h.radial_layout("core"), box=[0, 0, pw, ph],
          node_fill=fc, node_stroke=sc), cols[1], rows[0], pw, ph)

    p = pipeline_graph()
    fc, sc = PALETTE["layered"]
    panel(page, "layered_layout (DAG)", p.render(p.layered_layout(), box=[0, 0, pw, ph],
          node_fill=fc, node_stroke=sc, edge_color="#a16207"),
          cols[2], rows[0], pw, ph)

    # Row 2 — force layout, a perspective solid, and a 3D network.
    m = mesh_graph()
    fc, sc = PALETTE["spring"]
    panel(page, "spring_layout (force)", m.render(m.spring_layout(), box=[0, 0, pw, ph],
          node_fill=fc, node_stroke=sc, edge_color="#a78bfa"),
          cols[0], rows[1], pw, ph)

    cam = Camera(eye=Vec3(2.6, 2.0, 3.4), target=Vec3(0, 0.15, 0), fov=42, aspect=pw / ph)
    fc, sc = PALETTE["scene"]
    goblet = (Scene3D().revolve(
        [(0.10, -1.0), (0.55, -0.95), (0.62, -0.55), (0.18, -0.35),
         (0.16, 0.35), (0.70, 0.75), (0.78, 1.0)], segments=28))
    panel(page, "Scene3D + Camera", goblet.render(box=[0, 0, pw, ph], camera=cam,
          fill="#fecaca", stroke=sc), cols[1], rows[1], pw, ph)

    g3, coords = net3d_graph()
    cam2 = Camera(eye=Vec3(3.0, 2.4, 3.6), target=Vec3(0, 0, 0), fov=46, aspect=pw / ph)
    fc, sc = PALETTE["net3d"]
    panel(page, "Graph + Camera (3D)", g3.render(coords, box=[0, 0, pw, ph], camera=cam2,
          node_fill=fc, node_stroke=sc, edge_color="#67e8f9", labels=False),
          cols[2], rows[1], pw, ph)

    return builder


def main() -> int:
    out = os.path.join(ROOT, "fixtures", "topology-perspective.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warnings)} -> {out}")
    for issue in report.issues[:20]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
