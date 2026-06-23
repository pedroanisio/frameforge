#!/usr/bin/env python3
"""Demo of the SDK field / wave / lattice / manifold helpers.

A single landscape page, eight panels (4×2):

    1. VectorField           — a rotational flow field of arrows
    2. ScalarField           — heatmap + marching-squares contours
    3. lattice (2D)          — a honeycomb lattice with bonds
    4. lattice (3D)          — an FCC cell projected through a Camera
    5. manifold.wave         — a two-source interference wave surface
    6. manifold.torus        — a torus in perspective
    7. manifold.mobius       — a Möbius band in perspective
    8. manifold.klein_bottle — an immersed Klein bottle in perspective

Each panel is one FrameGraph group, so the geometric audit stays at zero
warnings; the only text is the panel titles (sized to fit, so --check-overflow
passes) and the page header.

Run from the repository root::

    uv run python examples/fields_lattices_manifolds.py
"""
from __future__ import annotations

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
    ScalarField,
    Vec3,
    VectorField,
    lattice,
    manifold,
)

INK = "#0f172a"
SUBTLE = "#475569"
PANEL_BG = "#0b1220"
PANEL_EDGE = "#1e293b"
TITLE_BAND = 30.0


def panel(layer, title, group, px, py, pw, ph, *, light=False):
    layer.rect([px, py, pw, ph], fill=PANEL_BG, stroke=PANEL_EDGE,
               stroke_style={"stroke_width": 1.5}, radius=12, decorative=True)
    group["box"] = [px, py + TITLE_BAND, pw, ph - TITLE_BAND - 8]
    group.setdefault("children", []).insert(0, {
        "type": "text",
        "box": [10.0, -(TITLE_BAND - 8.0), pw - 20.0, 20.0],
        "text": title,
        "style": {"font_family": ["DejaVu Sans", "Arial", "sans-serif"],
                  "font_size": 14, "font_weight": 700,
                  "color": "#0f172a" if light else "#e2e8f0",
                  "text_align": "center"},
    })
    layer.add(group)


def build() -> DocumentBuilder:
    builder = DocumentBuilder(title="Fields, waves, lattices & manifolds",
                              profile="diagram", lang="en")
    builder.define_text_style("h1", font_family=["DejaVu Sans", "Arial", "sans-serif"],
                              font_size=28, font_weight=800, color=INK)
    builder.define_text_style("sub", font_family=["DejaVu Sans", "Arial", "sans-serif"],
                              font_size=14, color=SUBTLE)

    W, H = 1200, 720
    page = builder.page(
        "fields_lattices_manifolds",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
        reading_order=["h1"],
    ).layer("main")
    page.rect([0, 0, W, H], fill="#ffffff")
    page.text([40, 28, 1000, 34], "Fields · waves · lattices · manifolds", id="h1", style="h1")
    page.text([40, 66, 1080, 22],
              "Sample a function over a domain, generate a crystal lattice, or "
              "project a parametric surface — all deterministic, all one group.",
              style="sub")

    margin, gap = 36, 18
    top = 104
    pw = (W - 2 * margin - 3 * gap) / 4
    ph = (H - top - margin - gap) / 2
    cols = [margin + i * (pw + gap) for i in range(4)]
    rows = [top + j * (ph + gap) for j in range(2)]
    aspect = pw / ph
    cam = Camera(eye=Vec3(2.7, 2.1, 3.4), target=Vec3(0, 0, 0), fov=46, aspect=aspect)

    # --- Row 1 ---------------------------------------------------------------
    vf = VectorField(lambda x, y: (-y, x), domain=(-1, -1, 1, 1))
    panel(page, "VectorField (curl)",
          vf.render(box=[0, 0, pw, ph], steps_x=12, steps_y=12,
                    color="#38bdf8", warm="#f472b6"),
          cols[0], rows[0], pw, ph)

    sf = ScalarField(lambda x, y: math.sin(2.4 * x) * math.cos(2.4 * y),
                     domain=(-1.6, -1.6, 1.6, 1.6))
    hm = sf.heatmap(box=[0, 0, pw, ph], steps_x=26, steps_y=24,
                    low="#0b3866", high="#fde047")
    ct = sf.contours(box=[0, 0, pw, ph], levels=6, steps_x=42, steps_y=38,
                     color="#0f172a", width=0.9)
    hm["children"].extend(ct["children"])
    panel(page, "ScalarField (iso)", hm, cols[1], rows[0], pw, ph)

    hexlat = lattice("honeycomb", nx=4, ny=3, a=1.0)
    panel(page, "lattice 2D (hex)",
          hexlat.render(box=[0, 0, pw, ph], node_radius=4.5, node_fill="#34d399",
                        node_stroke="#065f46", edge_color="#475569"),
          cols[2], rows[0], pw, ph)

    fcc = lattice("fcc", nx=2, ny=2, nz=2, a=1.0)
    panel(page, "lattice 3D (FCC)",
          fcc.render(box=[0, 0, pw, ph], camera=cam, node_radius=5.0,
                     node_fill="#f59e0b", node_stroke="#7c2d12", edge_color="#64748b"),
          cols[3], rows[0], pw, ph)

    # --- Row 2 (manifolds in perspective) ------------------------------------
    panel(page, "wave (interference)",
          manifold.wave(sources=[(-0.55, -0.55), (0.55, 0.55)], amplitude=0.3,
                        wavelength=0.6, steps=34)
          .render(box=[0, 0, pw, ph], camera=cam, fill="#7dd3fc", stroke="#0369a1"),
          cols[0], rows[1], pw, ph)

    panel(page, "manifold.torus",
          manifold.torus(major=1.0, minor=0.36, steps_u=40, steps_v=22)
          .render(box=[0, 0, pw, ph], camera=cam, fill="#f9a8d4", stroke="#9d174d"),
          cols[1], rows[1], pw, ph)

    panel(page, "manifold.mobius",
          manifold.mobius(radius=1.0, width=0.42, steps_u=56, steps_v=6)
          .render(box=[0, 0, pw, ph], camera=cam, fill="#c4b5fd", stroke="#5b21b6"),
          cols[2], rows[1], pw, ph)

    panel(page, "manifold.klein",
          manifold.klein_bottle(scale=0.26, steps_u=42, steps_v=26)
          .render(box=[0, 0, pw, ph], camera=cam.orbit(azimuth=20),
                  fill="#86efac", stroke="#166534"),
          cols[3], rows[1], pw, ph)

    return builder


def main() -> int:
    out = os.path.join(ROOT, "fixtures", "fields-lattices-manifolds.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warnings)} -> {out}")
    for issue in report.issues[:20]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
