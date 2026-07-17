#!/usr/bin/env python3
"""Cookbook: the CG-canon residual geometry — patches, curve hits, hull, curvature.

A single diagram page where every figure is live SDK output, exercising the four
capabilities that closed the CG-canon backlog's last residuals:

* **B5** — `bezier_patch` / `bspline_patch`: a raised 4×4 control net rendered as
  two surfaces (the Bézier interpolates its corners; the uniform B-spline pulls in).
* **B8** — `segment_curve_intersections`: a cubic Bézier crossed by a line, with
  every intersection marked.
* **B9** — `surface_curvature`: Gaussian K and mean H read off a sphere and a
  saddle (the numbers printed are the API's, not hand-typed).
* **B10** — `convex_hull_3d`: the projected triangular hull of a 3D point cloud.

Run from the repository root::

    uv run python static/examples/cg_canon_residuals_demo.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    Camera, CubicBezier, DocumentBuilder, Material, Vec2, Vec3,
    bezier_patch, bspline_patch, convex_hull_3d, segment_curve_intersections,
    surface_curvature,
)

W, H = 920, 600
INK, PAPER, INDIGO, TERRA, TEAL = "#15181D", "#FBFAF6", "#2B4C7E", "#B75A34", "#2E7D7A"


def _fit(points, box, pad=14, flip_y=True):
    """Return a mapper fitting data `points` (x,y) into `box`=[x,y,w,h] uniformly."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    bx, by, bw, bh = box
    sx = (bw - 2 * pad) / max(maxx - minx, 1e-9)
    sy = (bh - 2 * pad) / max(maxy - miny, 1e-9)
    s = min(sx, sy)
    ox = bx + (bw - (maxx - minx) * s) / 2
    oy = by + (bh - (maxy - miny) * s) / 2

    def m(x, y):
        py = (maxy - y) if flip_y else (y - miny)
        return [ox + (x - minx) * s, oy + py * s]
    return m


def _panel(page, box, title, tag):
    x, y, w, h = box
    page.rect([x, y, w, h], fill="#FFFFFF", stroke="#D8D2C4", stroke_style={"stroke_width": 1})
    page.rect([x, y, w, 26], fill="#F1ECE0")
    page.text([x + 12, y + 6, w - 130, 16], title, style="h")
    page.text([x + w - 112, y + 6, 100, 16], tag, style="tag")
    return [x, y + 26, w, h - 26]


# ── B5 — Bézier vs uniform B-spline patch over one raised control net ────────
def _control_net():
    return [[(i / 3.0, j / 3.0, 1.0 if (i in (1, 2) and j in (1, 2)) else 0.0)
             for j in range(4)] for i in range(4)]


def panel_patches(page, box):
    inner = _panel(page, box, "B5 — surface patches", "bezier_patch")
    x, y, w, h = inner
    cam = Camera(eye=Vec3(2.4, 2.0, 2.9), target=Vec3(0.5, 0.4, 0.5), fov=40)
    net = _control_net()
    half = (w - 18) / 2
    for i, (make, name, col) in enumerate((
        (bezier_patch, "bezier_patch", INDIGO),
        (bspline_patch, "bspline_patch", TERRA),
    )):
        bx = x + 6 + i * (half + 6)
        grp = make(net, steps_u=14, steps_v=14).render(
            box=[bx, y + 6, half, h - 34], camera=cam, shading="lambert",
            material=Material(fill=col, stroke=INK), light=Vec3(-0.4, -0.6, 0.7))
        page.add(grp)
        page.text([bx, y + h - 26, half, 14], name, style="cap")


# ── B8 — a cubic Bézier crossed by a line; mark the intersections ────────────
def panel_curve_hits(page, box):
    inner = _panel(page, box, "B8 — curve × line intersections", "curve hits")
    curve = CubicBezier(Vec2(0, 0), Vec2(1, 3), Vec2(2, 3), Vec2(3, 0))  # y=9t(1-t) arch
    a0, a1 = Vec2(-0.4, 1.0), Vec2(3.4, 1.0)
    hits = segment_curve_intersections(a0, a1, curve)

    samples = [curve.point(k / 60.0) for k in range(61)]
    frame = samples + [a0, a1] + hits
    m = _fit([(p.x, p.y) for p in frame], inner, pad=22)

    page.polyline([m(p.x, p.y) for p in samples], fill="none",
                  stroke=INDIGO, stroke_style={"stroke_width": 2.4})
    page.line(m(a0.x, a0.y), m(a1.x, a1.y), stroke=TEAL, stroke_style={"stroke_width": 1.8})
    for hpt in hits:
        cx, cy = m(hpt.x, hpt.y)
        page.circle([cx, cy], 4.5, fill=TERRA, stroke=INK, stroke_style={"stroke_width": 1})
    page.text([inner[0] + 10, inner[1] + inner[3] - 20, inner[2] - 20, 14],
              f"{len(hits)} intersections found", style="cap")


# ── B9 — Gaussian & mean curvature read off two surfaces ─────────────────────
def _sphere_fn(r):
    import math
    return lambda u, v: (r * math.sin(v) * math.cos(u), r * math.cos(v), r * math.sin(v) * math.sin(u))


def panel_curvature(page, box):
    inner = _panel(page, box, "B9 — surface curvature (K, H)", "curvature")
    x, y, w, h = inner
    rows = [
        ("unit sphere r=1", surface_curvature(_sphere_fn(1.0), 1.0, 1.2)),
        ("sphere r=2", surface_curvature(_sphere_fn(2.0), 0.7, 1.1)),
        ("saddle z=u²−v²", surface_curvature(lambda u, v: (u, u * u - v * v, v), 0.0, 0.0)),
        ("plane", surface_curvature(lambda u, v: (u, 0.0, v), 0.3, -0.4)),
    ]
    page.text([x + 14, y + 10, w * 0.5, 14], "surface", style="cap")
    page.text([x + w * 0.52, y + 10, w * 0.22, 14], "K (Gauss)", style="cap")
    page.text([x + w * 0.76, y + 10, w * 0.22, 14], "H (mean)", style="cap")
    for i, (name, (K, Hm)) in enumerate(rows):
        ry = y + 34 + i * 26
        page.line([x + 12, ry - 6], [x + w - 12, ry - 6], stroke="#E7E1D2",
                  stroke_style={"stroke_width": 1})
        page.text([x + 14, ry, w * 0.5, 16], name, style="val")
        page.text([x + w * 0.52, ry, w * 0.22, 16], f"{K:+.3f}", style="num")
        page.text([x + w * 0.76, ry, w * 0.22, 16], f"{Hm:+.3f}", style="num")


# ── B10 — the projected triangular convex hull of a 3D point cloud ───────────
def panel_hull(page, box):
    inner = _panel(page, box, "B10 — 3D convex hull", "convex_hull_3d")
    cloud = [Vec3(0, 0, 0), Vec3(2, 0, 0), Vec3(0, 2, 0), Vec3(0, 0, 2),
             Vec3(2, 2, 0), Vec3(2, 0, 2), Vec3(0, 2, 2), Vec3(2, 2, 2),
             Vec3(1, 1, 1), Vec3(1.0, 1.0, 3.0)]  # a cube + interior + an apex
    faces = convex_hull_3d(cloud)
    cam = Camera(eye=Vec3(5.5, 4.5, 6.0), target=Vec3(1, 1, 1), fov=36)
    proj = [[cam.project(v) for v in tri] for tri in faces]
    frame = [(p.x, p.y) for tri in proj for p in tri]
    m = _fit(frame, inner, pad=20)
    for tri in proj:
        pts = [m(p.x, p.y) for p in tri]
        page.polyline(pts, closed=True, fill="none", stroke=INDIGO,
                      stroke_style={"stroke_width": 1.3})
    page.text([inner[0] + 10, inner[1] + inner[3] - 20, inner[2] - 20, 14],
              f"{len(faces)} hull faces from {len(cloud)} points", style="cap")


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="CG-canon residual geometry", profile="diagram", lang="en")
    b.define_text_style("title", font_family=["DejaVu Sans", "sans-serif"], font_size=22,
                        font_weight=800, color=INK)
    b.define_text_style("h", font_family=["DejaVu Sans", "sans-serif"], font_size=13,
                        font_weight=700, color=INK)
    b.define_text_style("tag", font_family=["DejaVu Sans Mono", "monospace"], font_size=9,
                        font_weight=700, color=TEAL, align="right")
    b.define_text_style("cap", font_family=["DejaVu Sans Mono", "monospace"], font_size=10,
                        font_weight=400, color="#5B5442")
    b.define_text_style("val", font_family=["DejaVu Sans", "sans-serif"], font_size=12,
                        font_weight=600, color=INK)
    b.define_text_style("num", font_family=["DejaVu Sans Mono", "monospace"], font_size=12,
                        font_weight=700, color=INDIGO)
    page = b.page("residuals", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute", reading_order=["title"]).layer("main")
    page.rect([0, 0, W, H], fill=PAPER)
    page.text([40, 22, W - 80, 30], "CG-canon residual geometry — live SDK output", id="title",
              style="title")

    mx, top, gap = 40, 70, 18
    pw = (W - 2 * mx - gap) / 2
    ph = (H - top - 40 - gap) / 2
    panel_patches(page, [mx, top, pw, ph])
    panel_curve_hits(page, [mx + pw + gap, top, pw, ph])
    panel_curvature(page, [mx, top + ph + gap, pw, ph])
    panel_hull(page, [mx + pw + gap, top + ph + gap, pw, ph])
    return b


def main() -> int:
    doc = build().build()
    from frameforge.sdk import validate_static_rules
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "cg-canon-residuals.fg.yaml")
    from frameforge.sdk import serialize
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc))
    print(f"ok={not errors} errors={len(errors)} pages={len(doc.pages)} -> {out}")
    for issue in report.issues[:20]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
