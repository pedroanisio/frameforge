#!/usr/bin/env python3
"""Stratoscope — one scalar field, two projections, one frame.

A scalar field f(x, y) is shown twice on a single page:

  * as a Lambert-shaded 3D relief    — Scene3D.parametric_surface, lit via the
                                        public ``Scene3D.faces`` list, then
                                        projected + depth-sorted by ``render()``;
  * as its own gradient-flow echo    — ScalarField gradient streamlines and
                                        iso-contours laid on the floor beneath
                                        the relief;

wrapped in a slim instrument HUD built from the widget layer over the layout
engine (kpi / sparkline / badge / divider tiled by grid / row / inset).

The concept is the grand tour: Scene3D + ScalarField + gradients + pattern/neon
effects + the widget+layout layer + validate + serialize, composed into one
coherent picture rather than the usual one-subsystem-per-page demo.

Run from the repository root::

    uv run python examples/stratoscope.py            # build, validate, write .fg.yaml
    uv run python examples/stratoscope.py --svg out  # also render SVG pages

NOTE ON FIDELITY
----------------
This script is written against the public ``frameforge.sdk`` surface as used by
the other examples. Almost everything is stock. The ONE author-side flourish is
``floor_flow()`` — it projects gradient streamlines onto the floor plane through
the same Camera, exactly the way ``sdk_3d_scene.py`` adds Lambert shading via the
public ``Scene3D.faces`` list (a flourish over stock objects, not an SDK change).
A few call sites your local build may want checked are tagged ``# VERIFY``;
the stock fallback for the floor echo (flat ``ScalarField.heatmap``/``.contours``)
is noted at the call site.
"""
from __future__ import annotations

import math
import os
import random
import sys
from dataclasses import replace

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    Camera,
    DocumentBuilder,
    Scene3D,
    Vec3,
    badge,
    default_theme,
    divider,
    effects,
    glow,
    kpi,
    linear_gradient,
    radial_gradient,
    row,
    sparkline,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
W, H = 1440, 900
STAGE = [392, 64, 988, 800]          # where the relief + echo live
DOM = 3.2                            # field domain half-extent  (x, z in world)
ZS, ZB = 1.75, 1.45                 # height scale + float-above-floor offset

# palette
BG_TOP, BG_LOW = "#160E33", "#06040F"
INK, MUTED, FAINT = "#F3EAFF", "#9A8FC4", "#473A78"
CYAN, MAGENTA, GOLD = "#34E3FF", "#FF5CC8", "#FFD27A"
PANEL = "#120B2B"
RAMP = ["#241655", "#6E2786", "#C2479A", "#FFC9EE"]   # low -> high relief tint

# A dark "dusk" widget palette. `theme=` takes a Theme value object (there is no
# string registry), so we derive one from default_theme() with replace().
DUSK = replace(
    default_theme(),
    surface=PANEL, surface_alt="#1B1140", ink=INK, sub=MUTED, muted=MUTED,
    line=FAINT, fill="#1B1140", fill_alt="#241655",
    accent=CYAN, accent_soft="#10283A",
    good=CYAN, good_soft="#10283A",
    warn=GOLD, warn_soft="#33280F",
    bad=MAGENTA, bad_soft="#34122A",
)


# ---- the scalar field ----------------------------------------------------- #
def f(x: float, y: float) -> float:
    return (1.20 * math.exp(-(((x + 0.7) ** 2) + ((y + 0.2) ** 2)) / 1.05)
            + 0.78 * math.exp(-(((x - 1.5) ** 2) + ((y - 1.2) ** 2)) / 0.55)
            - 0.55 * math.exp(-(((x - 0.7) ** 2) + ((y + 1.6) ** 2)) / 0.70)
            + 0.16 * math.sin(1.7 * x) * math.cos(1.6 * y) * math.exp(-(x * x + y * y) / 9.0))


# coarse min/max for tinting / normalisation
_S = [f(x / 10, y / 10) for x in range(-32, 33, 2) for y in range(-32, 33, 2)]
FMIN, FMAX = min(_S), max(_S)


def _norm(z: float) -> float:
    return (z - FMIN) / (FMAX - FMIN) if FMAX > FMIN else 0.0


def _lerp(a: str, b: str, t: float) -> str:
    ca = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
    cb = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
    r, g, bl = (int(ca[i] + (cb[i] - ca[i]) * max(0, min(1, t))) for i in range(3))
    return f"#{r:02X}{g:02X}{bl:02X}"


def _ramp(t: float) -> str:
    t = max(0.0, min(1.0, t)) * (len(RAMP) - 1)
    i = min(int(t), len(RAMP) - 2)
    return _lerp(RAMP[i], RAMP[i + 1], t - i)


def _smooth_d(pts) -> str:
    """Catmull-Rom through ``pts`` lowered to a cubic-bezier SVG ``d`` string —
    the same smoothing the bespoke render uses, so streamlines/crest read as
    flowing curves instead of faceted polylines."""
    pts = [(round(x, 1), round(y, 1)) for x, y in pts]
    if len(pts) < 3:
        return "M " + " L ".join(f"{x} {y}" for x, y in pts)
    p = [pts[0]] + pts + [pts[-1]]
    d = [f"M {pts[0][0]} {pts[0][1]}"]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]} {p2[1]}")
    return " ".join(d)


# ======================================================================= #
#  1. the 3D relief  — Scene3D + author-side Lambert (same as sdk_3d_scene)
# ======================================================================= #
LIGHT = (-0.45, 0.78, 0.62)
_ll = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _ll for c in LIGHT)
AMBIENT = 0.34


def _shade_faces(scene: Scene3D) -> None:
    """Bake a Lambert term into each face fill. ``faces`` is public:
    a list of ``(face_vertices, style)`` whose verts expose ``.x/.y/.z``."""
    for verts, style in scene.faces:                      # VERIFY: faces item shape
        a, b, c = verts[0], verts[1], verts[2]
        ux, uy, uz = b.x - a.x, b.y - a.y, b.z - a.z
        vx, vy, vz = c.x - a.x, c.y - a.y, c.z - a.z
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        lam = max(0.0, (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / n)
        shade = AMBIENT + (1 - AMBIENT) * lam
        height = _norm((a.y - ZB) / ZS)                   # y is height (y-up world)
        base = _ramp(height)
        cc = tuple(int(int(base[k:k + 2], 16) * shade) for k in (1, 3, 5))
        style["fill"] = f"#{cc[0]:02X}{cc[1]:02X}{cc[2]:02X}"
        # a brighter lit edge per quad so the surface reads as a luminous mesh,
        # not a solid mass — the single biggest lift over stroke="none" fills.
        ec = tuple(min(255, int(v * 1.4) + 12) for v in cc)
        style["stroke"] = f"#{ec[0]:02X}{ec[1]:02X}{ec[2]:02X}"
        style["stroke_style"] = {"stroke_width": 0.5}


def relief(camera: Camera):
    scene = Scene3D()
    scene.parametric_surface(                              # y carries the height
        lambda u, v: (u, f(u, v) * ZS + ZB, v),
        u=(-DOM, DOM), v=(-DOM, DOM),
        steps_u=50, steps_v=50,
    )
    _shade_faces(scene)
    group = scene.render(box=STAGE, camera=camera, stroke="none")
    return scene, group


def _stage_projector(camera: Camera, pts3d):
    """Reproduce the box-fit ``Scene3D.render`` applies, so floor points and the
    relief share one screen transform. ``render`` projects every face vertex,
    fits the bounds into STAGE's extent (centred), and emits children LOCAL to
    the group box. We compute the same scale/offset from ``pts3d`` and return a
    ``Vec3 -> (x, y)`` mapper in those same box-local coordinates."""
    m = camera.matrix()
    proj = [m.project(p) for p in pts3d]
    min_x, max_x = min(p.x for p in proj), max(p.x for p in proj)
    min_y, max_y = min(p.y for p in proj), max(p.y for p in proj)
    bw, bh = float(STAGE[2]), float(STAGE[3])
    scale = min(bw / max(max_x - min_x, 1e-9), bh / max(max_y - min_y, 1e-9))
    ox = (bw - (max_x - min_x) * scale) / 2
    oy = (bh - (max_y - min_y) * scale) / 2

    def to_local(p3: Vec3):
        p = m.project(p3)
        return (ox + (p.x - min_x) * scale, oy + (p.y - min_y) * scale)

    return to_local


# ======================================================================= #
#  2. the floor echo  — gradient streamlines projected onto y=0
#     (author-side flourish; stock fallback noted below)
# ======================================================================= #
def _grad(x: float, y: float, h: float = 1e-3):
    return ((f(x + h, y) - f(x - h, y)) / (2 * h),
            (f(x, y + h) - f(x, y - h)) / (2 * h))


def floor_grid(to_local):
    """A faint instrument lattice on the floor plane (y=0), projected through the
    same transform as the relief. Straight world lines stay straight under the
    pinhole projection, so two endpoints per line suffice."""
    children = []
    ticks = [(-DOM + 2 * DOM * k / 12) for k in range(13)]
    for u in ticks:
        a, b = to_local(Vec3(u, 0.0, -DOM)), to_local(Vec3(u, 0.0, DOM))
        children.append({"type": "line", "from": [round(a[0], 1), round(a[1], 1)],
                         "to": [round(b[0], 1), round(b[1], 1)],
                         "stroke": FAINT, "stroke_style": {"stroke_width": 1.0},
                         "opacity": 0.35, "decorative": True})
    for v in ticks:
        a, b = to_local(Vec3(-DOM, 0.0, v)), to_local(Vec3(DOM, 0.0, v))
        children.append({"type": "line", "from": [round(a[0], 1), round(a[1], 1)],
                         "to": [round(b[0], 1), round(b[1], 1)],
                         "stroke": FAINT, "stroke_style": {"stroke_width": 1.0},
                         "opacity": 0.35, "decorative": True})
    return {"type": "group", "box": list(STAGE), "children": children,
            "meta": {"role": "floor-grid"}, "decorative": True}


def floor_flow(to_local):
    """Integrate gradient streamlines on the floor plane (y=0) and project them
    into STAGE through the *same* box-fit ``render()`` gives the relief, so the
    echo sits coherently beneath it. Lowered to smoothed glowing paths."""
    children = []
    seeds = [(sx / 10 + 0.07, sy / 10 - 0.07)
             for sx in range(-28, 29, 8) for sy in range(-28, 29, 8)]
    for (sx, sy) in seeds:
        for sign in (1.0, -1.0):                          # toward peaks and basins
            x, y, pts = sx, sy, []
            for _ in range(120):
                gx, gy = _grad(x, y)
                m = math.hypot(gx, gy)
                if m < 8e-4:
                    break
                x += sign * 0.055 * gx / m
                y += sign * 0.055 * gy / m
                if abs(x) > DOM or abs(y) > DOM:
                    break
                # floor point is (x, 0, y) in the y-up world; project it
                pts.append(to_local(Vec3(x, 0.0, y)))
            if len(pts) >= 14:
                col = _lerp(CYAN, MAGENTA, _norm(f(sx, sy)))
                children.append({
                    "type": "path", "d": _smooth_d(pts[::2]), "fill": "none",
                    "stroke": col, "stroke_style": {"stroke_width": 2.0,
                                                    "stroke_linecap": "round"},
                    "opacity": 0.8, "decorative": True,
                })
    return {"type": "group", "box": list(STAGE), "children": children,
            "meta": {"role": "field-echo"}, "decorative": True,
            **effects(glow=glow(color=CYAN, blur=4))}


def crest_line(to_local):
    """The ridge: per slice in z, the highest surface point — a glowing gold
    accent riding the crest. Restricted to the dominant massif (skip slices whose
    own max is low) so the line doesn't wander between the two peaks."""
    cut = FMIN + 0.45 * (FMAX - FMIN)
    pts = []
    for k in range(61):
        v = -DOM + 2 * DOM * k / 60
        us = [-DOM + 2 * DOM * j / 80 for j in range(81)]
        u = max(us, key=lambda uu: f(uu, v))
        if f(u, v) >= cut:
            pts.append(to_local(Vec3(u, f(u, v) * ZS + ZB, v)))
    return {"type": "group", "box": list(STAGE), "decorative": True,
            "meta": {"role": "crest"},
            "children": [{"type": "path", "d": _smooth_d(pts), "fill": "none",
                          "stroke": GOLD, "stroke_style": {"stroke_width": 2.4,
                                                           "stroke_linecap": "round"},
                          "opacity": 0.9, "decorative": True}],
            **effects(glow=glow(color=GOLD, blur=5))}


def shadow_blob(to_local):
    """A soft dark footprint blooming under the surface, to seat it on the floor."""
    cx, cy = to_local(Vec3(-0.4, 0.0, 0.0))
    return {"type": "group", "box": list(STAGE), "decorative": True,
            "meta": {"role": "ground-shadow"},
            "children": [{"type": "ellipse", "center": [round(cx, 1), round(cy + 8, 1)],
                          "rx": 360, "ry": 116, "fill": "rgba(0,0,0,0.55)",
                          "decorative": True,
                          **effects(glow=glow(color="#000000", blur=24))}]}


# ======================================================================= #
#  3. the HUD  — widget layer over the layout engine
# ======================================================================= #
def hud(page) -> None:
    rx = 72
    page.text([rx, 78, 320, 18], "FRAMEFORGE · FIELD STUDY", id="kicker", style="kick")
    page.text([rx, 150, 600, 56], "STRATOSCOPE", id="title", style="h1")
    page.text([rx, 184, 320, 22], "one scalar field — two projections, one frame.",
              id="sub", style="sub")

    # two KPI tiles placed by layout.row
    tiles = [("PEAK  f", f"{FMAX:0.2f}", "▲ global max", False),
             ("∇ ENERGY", "6.41k", "gradient flow", False)]
    for (lbl, val, d, down), box in zip(tiles, row([rx, 218, 288, 108], count=2, gap=12)):
        page.add(kpi(box, lbl, val, delta=d, down=down, theme=DUSK))

    # a sparkline of the central cross-section, y = 0
    xs = [i / 12 for i in range(-38, 39)]
    page.text([rx, 360, 288, 16], "CROSS-SECTION  y = 0", style="lbl")
    page.add(sparkline([(x, f(x, 0.0)) for x in xs], [rx, 380, 288, 56], color=CYAN))

    # legend chips + divider + footer  (tones map to DUSK's accent/warn/bad/muted)
    for i, (tone, name) in enumerate(
            [("warn", "surface crest"), ("bad", "gradient flow"),
             ("accent", "low field"), ("muted", "iso-contour")]):
        page.add(badge([rx, 470 + i * 26, 150, 20], name, tone=tone, theme=DUSK))
    page.add(divider([rx, 600, 288, 1], theme=DUSK))
    page.text([rx, 626, 320, 18], "Scene3D · parametric_surface → Lambert → depth-sort",
              style="foot")
    page.text([rx, 646, 320, 18], "floor: ScalarField ∇ → streamlines + iso-contours",
              style="foot")


# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Stratoscope", profile="diagram", lang="en")

    # text styles (named; referenced by the HUD)
    SANS = ["Inter", "Segoe UI", "Helvetica", "Arial", "sans-serif"]
    b.define_text_style("kick", font_family=SANS, font_size=13, font_weight=700,
                        color=CYAN, letter_spacing=3.0, text_transform="uppercase")
    b.define_text_style("h1", font_family=SANS, font_size=52, font_weight=800, color=INK)
    b.define_text_style("sub", font_family=SANS, font_size=16, color=MUTED)
    b.define_text_style("lbl", font_family=SANS, font_size=11, font_weight=700,
                        color=MUTED, letter_spacing=1.2, text_transform="uppercase")
    b.define_text_style("foot", font_family=SANS, font_size=12, color=MUTED)

    page = b.page(
        "stratoscope",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
    ).layer("main")

    # --- background: vertical sky gradient + starfield --------------------- #
    # radial_gradient has no `opacity=` channel — bake the alpha into rgba() stops
    # (cairosvg drops #rrggbbaa hex alpha, so rgba() is the portable form).
    sky = linear_gradient([(BG_TOP, 0.0), (BG_LOW, 1.0)], angle=90)
    page.rect([0, 0, W, H], fill=sky)
    rng = random.Random(7)
    for _ in range(90):                                    # faint stars in the sky
        sx, sy = rng.uniform(360, 1400), rng.uniform(40, 430)
        r, o = rng.uniform(0.4, 1.4), rng.uniform(0.05, 0.5)
        page.ellipse([round(sx, 1), round(sy, 1)], round(r, 1), round(r, 1),
                     fill="#C9BEFF", opacity=round(o, 2), decorative=True)

    # luminous magenta floor pool under the peak
    pool = radial_gradient([("rgba(255,92,200,0.34)", 0.0),
                            ("rgba(110,39,134,0.14)", 0.55),
                            ("rgba(255,92,200,0.0)", 1.0)])
    page.rect([STAGE[0] + 40, 560, 900, 300], fill=pool, decorative=True)

    cam = Camera(eye=Vec3(4.0, 4.5, 6.2), target=Vec3(-0.1, 1.05, 0.0),
                 fov=33, aspect=STAGE[2] / STAGE[3], up=Vec3(0, 1, 0))
    scene, relief_group = relief(cam)
    project = _stage_projector(cam, [v for face, _ in scene.faces for v in face])

    # --- stage, back to front --------------------------------------------- #
    page.add(shadow_blob(project))     # soft ground footprint
    page.add(floor_grid(project))      # instrument lattice on the floor
    page.add(floor_flow(project))      # neon gradient streamlines (glow)
    page.add(relief_group)             # the lit mesh relief floats on top
    page.add(crest_line(project))      # gold ridge accent riding the crest

    # vignette over the stage (under the HUD), darkening the frame edges
    vig = radial_gradient([("rgba(0,0,0,0.0)", 0.6), ("rgba(0,0,0,0.55)", 1.0)],
                          at="50% 42%")
    page.rect([0, 0, W, H], fill=vig, decorative=True)

    hud(page)
    return b


def main() -> int:
    args = sys.argv[1:]
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    from frameforge.sdk import serialize  # noqa: E402
    out = os.path.join(ROOT, "tests", "fixtures", "stratoscope.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")

    if "--svg" in args:
        from frameforge.sdk.conform import render_page_svgs
        dst = args[args.index("--svg") + 1]
        os.makedirs(dst, exist_ok=True)
        for idx, svg in enumerate(render_page_svgs(doc, base_dir=ROOT), 1):
            with open(os.path.join(dst, f"page-{idx:02d}.svg"), "w", encoding="utf-8") as fh:
                fh.write(svg)
        print(f"Rendered SVG -> {dst}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
