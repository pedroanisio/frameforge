#!/usr/bin/env python3
"""A complex, shaded 3D scene composed with the FrameGraph SDK — *today*.

The SDK already ships a software 3D pipeline: :class:`framegraph.sdk.Scene3D`
projects meshes / parametric surfaces / revolved solids / extrusions through a
:class:`Camera` (perspective ``look_at`` + ``perspective_fov``) into depth-sorted
2D polylines. Its only gap is shading — faces are emitted flat.

This example closes that gap *without changing the SDK*: ``Scene3D.faces`` is a
public ``list[(face_vertices, style)]``, so after building geometry we run a
Lambert shading pass over it — compute each face normal, orient it toward the
camera, dot it with a light direction, and bake the lit colour into the face's
``fill``. Then ``Scene3D.render()`` projects, depth-sorts and emits as usual.

The scene — a dusk "archipelago observatory" — exercises every Scene3D generator:

  * ``parametric_surface``  → rolling terrain, a ringed planet, a moon, the ring
  * ``revolve``             → the central tapered tower
  * ``mesh``                → faceted crystals (octahedra) and stone buildings
  * ``extrude``             → standing monolith slabs

Run from the repository root::

    uv run python examples/sdk_3d_scene.py
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
    Scene3D,
    Vec3,
    linear_gradient,
    radial_gradient,
    rgba,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1440, 900
SCENE_BOX = [70, 96, 1300, 740]
SANS = ["DejaVu Sans", "Arial", "sans-serif"]
MONO = ["DejaVu Sans Mono", "Courier New", "monospace"]

# dusk palette
SKY_TOP, SKY_MID, SKY_LOW = "#171033", "#3A1E54", "#B5526B"
SUN = "#FFD27A"
INK = "#0E0A1E"


# ======================================================================= #
#  author-side Lambert shading over Scene3D.faces (no SDK change)
# ======================================================================= #
LIGHT = (-0.42, 0.84, 0.50)
_ll = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _ll for c in LIGHT)


def _rgb(hexc):
    h = hexc.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(r, g, b):
    clamp = lambda v: max(0, min(255, int(round(v))))
    return f"#{clamp(r):02X}{clamp(g):02X}{clamp(b):02X}"


def _tint(base, b):
    r, g, bl = _rgb(base)
    return _hex(r * b, g * b, bl * b)


def _face_normal(verts):
    a, b, c = verts[0], verts[1], verts[2]
    u, v = b - a, c - a
    nx = u.y * v.z - u.z * v.y
    ny = u.z * v.x - u.x * v.z
    nz = u.x * v.y - u.y * v.x
    n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / n, ny / n, nz / n)


def shade(faces, base, *, eye, two_sided=False, ambient=0.30, facet=False):
    """Bake a Lambert fill into each (verts, style) entry, in place.

    The normal is flipped to face the camera first, so visible faces are lit by
    their orientation regardless of the generator's winding — robust for a
    painter's-algorithm renderer that does no back-face culling.
    """
    ex, ey, ez = eye.x, eye.y, eye.z
    lx, ly, lz = LIGHT
    for verts, style in faces:
        nx, ny, nz = _face_normal(verts)
        cx = sum(p.x for p in verts) / len(verts)
        cy = sum(p.y for p in verts) / len(verts)
        cz = sum(p.z for p in verts) / len(verts)
        if nx * (ex - cx) + ny * (ey - cy) + nz * (ez - cz) < 0:
            nx, ny, nz = -nx, -ny, -nz
        d = nx * lx + ny * ly + nz * lz
        d = abs(d) if two_sided else max(0.0, d)
        b = ambient + (1.0 - ambient) * d
        style["fill"] = _tint(base, b)
        if facet:
            style["stroke"] = _tint(base, max(0.0, b - 0.28))
            style["stroke_style"] = {"stroke_width": 0.6}
        else:
            style["stroke"] = "none"
    return faces


# ======================================================================= #
#  geometry generators (each builds in its own Scene3D, returns its faces)
# ======================================================================= #
def g_sphere(cx, cy, cz, r, nu=22, nv=14):
    s = Scene3D()
    s.parametric_surface(
        lambda u, v: (cx + r * math.sin(v) * math.cos(u),
                      cy + r * math.cos(v),
                      cz + r * math.sin(v) * math.sin(u)),
        u=(0.0, 2 * math.pi), v=(0.0, math.pi), steps_u=nu, steps_v=nv)
    return s.faces


def g_torus(cx, cy, cz, R, rr, tilt_deg, nu=36, nv=14):
    t = math.radians(tilt_deg)
    ct, st = math.cos(t), math.sin(t)

    def fn(u, v):
        px = (R + rr * math.cos(v)) * math.cos(u)
        py = rr * math.sin(v)
        pz = (R + rr * math.cos(v)) * math.sin(u)
        # tilt about the x axis, then place
        return (cx + px, cy + py * ct - pz * st, cz + py * st + pz * ct)

    s = Scene3D()
    s.parametric_surface(fn, u=(0.0, 2 * math.pi), v=(0.0, 2 * math.pi),
                         steps_u=nu, steps_v=nv)
    return s.faces


def g_terrain(half=5.4, steps=30, amp=0.5):
    def h(x, z):
        return (amp * math.sin(x * 0.85) * math.cos(z * 0.8)
                + 0.18 * math.sin(x * 1.7 + z * 0.6)
                - 0.05 * (x * x + z * z) * 0.02)

    s = Scene3D()
    s.parametric_surface(lambda u, v: (u, h(u, v), v),
                         u=(-half, half), v=(-half, half),
                         steps_u=steps, steps_v=steps)
    return s.faces


def g_tower():
    # base sunk to y=-0.8 so its downward cap hides under the terrain
    profile = [(0.0, -0.8), (1.05, -0.8), (0.92, 0.1), (0.72, 0.5),
               (0.68, 2.6), (0.98, 2.8), (0.64, 3.0), (0.46, 3.5),
               (0.58, 3.8), (0.0, 4.4)]
    s = Scene3D()
    s.revolve(profile, segments=38)
    return s.faces


def _box_faces(cx, cy, cz, sx, sy, sz):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    v = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
         (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
         (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
         (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
    faces = [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7],
             [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]]
    s = Scene3D()
    s.mesh(v, faces)
    return s.faces


def g_building(cx, cz, w_, h_):
    # span y=-0.3..h_ so the downward base cap hides under the terrain
    return _box_faces(cx, (h_ - 0.3) / 2, cz, w_, h_ + 0.3, w_)


def g_octahedron(cx, cy, cz, r):
    v = [(cx + r, cy, cz), (cx - r, cy, cz), (cx, cy + r, cz),
         (cx, cy - r, cz), (cx, cy, cz + r), (cx, cy, cz - r)]
    faces = [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
             [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]]
    s = Scene3D()
    s.mesh(v, faces)
    return s.faces


def g_monolith(cx, height, thick=0.34, width=0.5):
    # extrude an upright rectangle in the XY plane → a standing slab in z
    poly = [(cx - width / 2, -0.3), (cx + width / 2, -0.3),
            (cx + width / 2, height), (cx - width / 2, height)]
    s = Scene3D()
    s.extrude(poly, depth=thick)
    return s.faces


# ======================================================================= #
#  compose the scene
# ======================================================================= #
def build_scene(eye):
    master = Scene3D()

    def add(faces, base, **kw):
        shade(faces, base, eye=eye, **kw)
        master.faces.extend(faces)

    # ground
    add(g_terrain(), "#1C9C86", two_sided=True, ambient=0.34)
    # hero tower at the origin
    add(g_tower(), "#E4BE83", ambient=0.26, facet=True)
    # a little town around it
    for cx, cz, w_, h_, col in [
            (-2.0, 1.6, 0.85, 1.4, "#8FA3B0"), (2.1, 1.3, 0.75, 2.0, "#A7B4BE"),
            (-2.7, -0.8, 0.65, 1.1, "#7C93A1"), (1.8, -1.9, 0.95, 1.6, "#9FB0BA"),
            (3.0, 0.3, 0.6, 1.0, "#8497A4"), (-1.4, -2.2, 0.7, 0.9, "#9AAAB6")]:
        add(g_building(cx, cz, w_, h_), col, ambient=0.28, facet=True)
    # standing monoliths
    for cx, h_ in [(-3.9, 2.5), (4.1, 2.0), (-4.4, 1.6)]:
        add(g_monolith(cx, h_), "#6E6A86", ambient=0.30, facet=True)
    # floating faceted crystals
    for cx, cy, cz, r, col in [
            (-1.2, 3.4, -0.6, 0.50, "#E8568F"), (1.7, 3.9, -1.2, 0.40, "#46D6E6"),
            (0.3, 4.4, 0.9, 0.34, "#B6E84A"), (2.6, 3.0, 0.7, 0.30, "#F0A24E")]:
        add(g_octahedron(cx, cy, cz, r), col, ambient=0.24, facet=True)
    # ringed planet + moon, hanging in the sky
    add(g_sphere(-2.6, 5.4, -2.2, 1.35), "#5B6CF0", ambient=0.22)
    add(g_torus(-2.6, 5.4, -2.2, 2.15, 0.18, 24.0), "#F0C75C",
        two_sided=True, ambient=0.30)
    add(g_sphere(-0.6, 6.0, -3.0, 0.5), "#F0865A", ambient=0.26)
    return master


# ======================================================================= #
#  page
# ======================================================================= #
def T(page, box, s, **kw):
    with page.grouped() as g:
        g.text(box, s, **kw)


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph SDK — composed 3D scene",
                        profile="deck", lang="en")
    page = b.page("scene", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute").layer("sky")

    # sky + sun + stars (plain 2D)
    page.rect([0, 0, W, H],
              fill=linear_gradient([(SKY_TOP, 0), (SKY_MID, 0.55),
                                    (SKY_LOW, 1)], angle=180))
    page.ellipse([W * 0.30, H * 0.66], 260, 260,
                 fill=radial_gradient([(rgba(SUN, 0.55), 0), (rgba(SUN, 0.0), 1)]))
    page.ellipse([W * 0.30, H * 0.66], 64, 64, fill=rgba(SUN, 0.9))
    for i, (sx, sy, sr) in enumerate([
            (180, 110, 1.6), (340, 80, 1.1), (520, 140, 1.8), (760, 70, 1.2),
            (980, 120, 1.5), (1180, 90, 1.1), (1280, 180, 1.7), (120, 220, 1.2),
            (1340, 300, 1.4), (90, 360, 1.0), (640, 60, 1.3), (1080, 200, 1.2)]):
        page.ellipse([sx, sy], sr, sr, fill=rgba("#FFFFFF", 0.85))

    # title (kept to two layer-level texts — under the tabular threshold)
    page.layer("label")
    T(page, [70, 34, 1000, 30], "A composed 3D scene — built with the SDK today",
      style=dict(font_family=SANS, font_size=24, font_weight=800,
                 color="#FFFFFF", letter_spacing=-0.4))
    T(page, [70, 66, 1100, 20],
      "Scene3D projection + Camera perspective, with author-side Lambert shading "
      "baked into the public face list.",
      style=dict(font_family=SANS, font_size=13, color=rgba("#FFFFFF", 0.78)))

    # the 3D scene
    page.layer("scene")
    cam = Camera(eye=Vec3(7.4, 4.8, 9.6), target=Vec3(0.0, 1.9, -0.2),
                 fov=40, aspect=SCENE_BOX[2] / SCENE_BOX[3])
    scene = build_scene(cam.eye)
    group = scene.render(box=SCENE_BOX, camera=cam, fill="#888", stroke="none",
                         id="scene3d")
    page.add(group)

    # legend of the generators used (inside one group → no tabular flag)
    page.layer("legend")
    items = [("parametric_surface", "terrain · planet · ring · moon", "#1C9C86"),
             ("revolve", "central tower", "#E4BE83"),
             ("mesh", "crystals · buildings", "#E8568F"),
             ("extrude", "monolith slabs", "#6E6A86")]
    lx, ly = 70, H - 132
    page.rect([lx - 14, ly - 16, 360, 132], fill=rgba("#000000", 0.28), radius=12)
    T(page, [lx, ly - 4, 320, 16], "GENERATORS IN THIS SCENE",
      style=dict(font_family=MONO, font_size=10.5, font_weight=700,
                 color=rgba("#FFFFFF", 0.7), letter_spacing=1.2))
    for i, (name, what, col) in enumerate(items):
        yy = ly + 22 + i * 24
        page.rect([lx, yy, 12, 12], fill=col, radius=3)
        T(page, [lx + 22, yy - 2, 180, 14], name,
          style=dict(font_family=MONO, font_size=12, font_weight=700,
                     color="#FFFFFF"))
        T(page, [lx + 168, yy - 2, 200, 14], what,
          style=dict(font_family=SANS, font_size=11,
                     color=rgba("#FFFFFF", 0.66)))
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    nfaces = sum(len(layer.get("objects", []))
                 for pg in [doc.pages[0]] for layer in [])
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in errors[:20]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:20]:
        print(f"  warn  [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "fixtures", "sdk-3d-scene.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
