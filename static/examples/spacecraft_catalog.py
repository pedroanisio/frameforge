#!/usr/bin/env python3
"""ORBITAL REGISTRY — a 21-page catalog of spacecraft, every craft a real 3D
model built and projected through the SDK's ``Scene3D``.

Each of the twenty craft is assembled from a small parts library (tube / box /
dome / disc / panel / sphere) into world-space triangle/quad meshes, given
half-Lambert shading from a world-space light, then depth-sorted and projected
by ``Scene3D.render`` onto the page. The spec panels are composed with the SDK's
widget layer (card / kpi / badge / table). Page 1 is the cover + index.

Run from the repository root::

    uv run python examples/spacecraft_catalog.py   # build, validate, write the fixture
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    Mat4,
    Scene3D,
    badge,
    card,
    default_theme,
    divider,
    grid,
    inset,
    kpi,
    row,
    serialize,
    table,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1440, 900
M = 56
CANVAS = {"size": [W, H], "units": "px"}
TH = default_theme()
# Page space is Y-down, so world +Y projects downward under a raw isometric.
# Compose a world Y-flip first so "up" in the model reads as up on the page.
_FLIP_Y = Mat4(((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
CAMERA = Mat4.isometric() @ _FLIP_Y
LIGHT = (-0.42, 0.78, 0.46)

SANS = list(TH.font)
MONO = list(TH.mono)

# palette
SPACE = "#0A1020"
SPACE2 = "#131B30"
HULL = "#C8D0DB"
HULL2 = "#A9B4C4"
WHITE = "#E9EDF3"
DARK = "#2B3445"
PANELC = "#3A4456"
GOLD = "#C8A24C"
SOLAR = "#2A4F8C"
COPPER = "#9C6B47"
RED = "#C0392B"
TEAL = "#2E8B8B"
RADP = "#5A6678"

STYLES = {
    "reg": dict(font_family=MONO, font_size=12, font_weight=700, color="#7FE3C0",
                letter_spacing=2.0),
    "no": dict(font_family=MONO, font_size=13, font_weight=700, color="#8FA0BC"),
    "name": dict(font_family=SANS, font_size=30, font_weight=800, color="#F2F5FA",
                 letter_spacing=-0.6),
    "klass": dict(font_family=SANS, font_size=14, font_weight=700, color="#9FB0CC",
                  letter_spacing=0.5),
    "body": dict(font_family=SANS, font_size=13, color="#C3CCDA", line_height=1.5),
    "lbl": dict(font_family=SANS, font_size=11, font_weight=700, color="#7E8CA6",
                letter_spacing=0.8, text_transform="uppercase"),
    "foot": dict(font_family=MONO, font_size=11, color="#5E6A82", letter_spacing=1),
    "cover": dict(font_family=SANS, font_size=60, font_weight=800, color="#F2F5FA",
                  letter_spacing=-2),
    "coversub": dict(font_family=SANS, font_size=16, color="#A9B6CE", line_height=1.6),
    "idx": dict(font_family=SANS, font_size=14, font_weight=600, color="#D4DCE8"),
    "idxno": dict(font_family=MONO, font_size=12, font_weight=700, color="#7FE3C0"),
    "idxk": dict(font_family=SANS, font_size=11, color="#8093AE"),
}


# ======================================================================= #
#  vector helpers + shaded faces
# ======================================================================= #
def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vscale(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def vdot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def vcross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
                          a[0] * b[1] - a[1] * b[0])


def vlen(a): return math.sqrt(vdot(a, a)) or 1.0
def vunit(a): l = vlen(a); return (a[0] / l, a[1] / l, a[2] / l)


def _basis(axis):
    a = vunit(axis)
    helper = (0.0, 1.0, 0.0) if abs(a[1]) < 0.9 else (1.0, 0.0, 0.0)
    u = vunit(vcross(helper, a))
    v = vcross(a, u)
    return a, u, v


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def _mul(base, f):
    c = base.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return _hex((r * f, g * f, b * f))


AMBIENT = 0.34


def _shade(pts, base):
    if len(pts) < 3:
        return base
    n = vunit(vcross(vsub(pts[1], pts[0]), vsub(pts[2], pts[0])))
    d = vdot(n, LIGHT)
    i = AMBIENT + (1.0 - AMBIENT) * (0.5 + 0.5 * d)      # half-Lambert
    return _mul(base, i)


def face(scene, pts, base, *, edge=True):
    shade = _shade(pts, base)
    style = {"fill": shade}
    if edge:
        style["stroke"] = _mul(shade, 0.62)
        style["stroke_style"] = {"stroke_width": 0.5}
    else:
        style["stroke"] = shade
    scene.mesh(pts, [list(range(len(pts)))], **style)


# ======================================================================= #
#  parts library
# ======================================================================= #
def _ring(center, u, v, r, seg):
    return [vadd(center, vadd(vscale(u, r * math.cos(2 * math.pi * k / seg)),
                              vscale(v, r * math.sin(2 * math.pi * k / seg))))
            for k in range(seg)]


def tube(scene, p0, p1, r0, base, *, r1=None, seg=18, cap0=True, cap1=True, edge=True):
    r1 = r0 if r1 is None else r1
    a, u, v = _basis(vsub(p1, p0))
    ring0 = _ring(p0, u, v, r0, seg)
    ring1 = _ring(p1, u, v, r1, seg)
    for k in range(seg):
        kn = (k + 1) % seg
        face(scene, [ring0[k], ring0[kn], ring1[kn], ring1[k]], base, edge=edge)
    if cap0 and r0 > 1e-4:
        for k in range(seg):
            face(scene, [p0, ring0[(k + 1) % seg], ring0[k]], base, edge=edge)
    if cap1 and r1 > 1e-4:
        for k in range(seg):
            face(scene, [p1, ring1[k], ring1[(k + 1) % seg]], base, edge=edge)


def box(scene, center, size, base, *, edge=True):
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    cx, cy, cz = center
    c = [(cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
         (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
         (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
         (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)]
    for f in ([0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2],
              [4, 5, 1, 0], [3, 2, 6, 7]):
        face(scene, [c[i] for i in f], base, edge=edge)


def disc(scene, center, axis, r, base, *, seg=20, edge=True):
    _, u, v = _basis(axis)
    ring = _ring(center, u, v, r, seg)
    for k in range(seg):
        face(scene, [center, ring[k], ring[(k + 1) % seg]], base, edge=edge)


def dome(scene, center, axis, r, base, *, seg=16, rings=5, full=False, edge=True):
    a, u, v = _basis(axis)
    lat_max = math.pi if full else math.pi / 2
    pts = [[vadd(center, vadd(vscale(a, r * math.cos(lat_max * i / rings)),
            vadd(vscale(u, r * math.sin(lat_max * i / rings) * math.cos(2 * math.pi * j / seg)),
                 vscale(v, r * math.sin(lat_max * i / rings) * math.sin(2 * math.pi * j / seg)))))
            for j in range(seg)] for i in range(rings + 1)]
    for i in range(rings):
        for j in range(seg):
            jn = (j + 1) % seg
            face(scene, [pts[i][j], pts[i][jn], pts[i + 1][jn], pts[i + 1][j]], base, edge=edge)


def sphere(scene, center, r, base, **kw):
    dome(scene, center, (0, 1, 0), r, base, full=True, rings=8, **kw)


def panel(scene, center, udir, vdir, w, h, base, *, nu=4, nv=2):
    u, v = vunit(udir), vunit(vdir)
    base2 = _mul(base, 0.8)
    for iu in range(nu):
        for iv in range(nv):
            x0, x1 = -w / 2 + w * iu / nu, -w / 2 + w * (iu + 1) / nu
            y0, y1 = -h / 2 + h * iv / nv, -h / 2 + h * (iv + 1) / nv

            def P(xx, yy):
                return vadd(center, vadd(vscale(u, xx), vscale(v, yy)))
            face(scene, [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)],
                 base if (iu + iv) % 2 == 0 else base2)


def quad(scene, p0, p1, p2, p3, base):
    face(scene, [p0, p1, p2, p3], base)


def dish(scene, center, axis, r, base, *, seg=18, rings=4):
    """A shallow parabolic antenna dish facing ``axis``."""
    a, u, v = _basis(axis)
    pts = [[vadd(center, vadd(vscale(a, 0.35 * r * (i / rings) ** 2),
            vadd(vscale(u, r * (i / rings) * math.cos(2 * math.pi * j / seg)),
                 vscale(v, r * (i / rings) * math.sin(2 * math.pi * j / seg)))))
            for j in range(seg)] for i in range(rings + 1)]
    for i in range(rings):
        for j in range(seg):
            jn = (j + 1) % seg
            face(scene, [pts[i][j], pts[i][jn], pts[i + 1][jn], pts[i + 1][j]], base)
    tip = vadd(center, vscale(a, 0.35 * r + r * 0.5))
    tube(scene, center, tip, r * 0.05, DARK, seg=6, cap0=False)


def solar_wings(scene, center, span, w, h, base=SOLAR):
    for sgn in (-1, 1):
        c = vadd(center, (sgn * (span + w / 2), 0, 0))
        tube(scene, center, vadd(center, (sgn * span, 0, 0)), 0.03, DARK,
             seg=6, cap0=False, cap1=False)
        panel(scene, c, (1, 0, 0), (0, 0, 1), w, h, base, nu=5, nv=3)


# ======================================================================= #
#  craft builders  (each adds to `s`)
# ======================================================================= #
def c_capsule(s):
    tube(s, (-1.2, 0, 0), (-0.2, 0, 0), 0.62, HULL2)              # service module
    panel(s, (-0.7, 0, 1.15), (1, 0, 0), (0, 0, 1), 1.0, 1.4, SOLAR, nu=3, nv=3)
    panel(s, (-0.7, 0, -1.15), (1, 0, 0), (0, 0, 1), 1.0, 1.4, SOLAR, nu=3, nv=3)
    tube(s, (-0.2, 0, 0), (0.7, 0, 0), 0.62, WHITE, r1=0.2)       # capsule cone
    disc(s, (0.7, 0, 0), (1, 0, 0), 0.2, HULL)
    tube(s, (-1.3, 0, 0), (-1.2, 0, 0), 0.3, COPPER)             # engine bell


def c_station(s):
    tube(s, (-2.4, 0, 0), (2.4, 0, 0), 0.16, HULL)               # truss spine
    for x in (-1.4, 0.0, 1.4):
        tube(s, (x, -0.55, 0), (x, 0.55, 0), 0.4, HULL2, r1=0.4)  # modules
    tube(s, (0, 0, -0.9), (0, 0, 0.9), 0.34, WHITE)
    for x in (-2.0, 2.0):
        for z in (-1, 1):
            panel(s, (x, 0, z * 1.4), (0, 0, 1), (0, 1, 0), 2.2, 1.0, SOLAR, nu=6, nv=2)
    dish(s, (0, -0.7, 0), (0, -1, 0), 0.5, HULL)


def c_rover(s):
    box(s, (0, 0.1, 0), (1.8, 0.5, 1.1), HULL2)                  # chassis
    panel(s, (0, 0.42, 0), (1, 0, 0), (0, 0, 1), 1.7, 1.0, SOLAR, nu=5, nv=2)
    for x in (-0.7, 0, 0.7):
        for z in (-0.62, 0.62):
            tube(s, (x, -0.25, z), (x, -0.25, z + (0.12 if z > 0 else -0.12)),
                 0.26, DARK, seg=12)                              # wheels
    tube(s, (0.6, 0.35, 0), (0.85, 1.1, 0), 0.05, HULL)         # mast
    box(s, (0.85, 1.15, 0), (0.18, 0.16, 0.4), WHITE)           # camera head
    dish(s, (-0.4, 0.7, 0.2), (0, 0.5, 1), 0.32, HULL)


def c_probe(s):
    box(s, (0, 0, 0), (0.7, 0.7, 0.7), GOLD)                     # bus (foil)
    dish(s, (0.45, 0, 0), (1, 0, 0), 0.95, HULL)                # high-gain
    tube(s, (-0.35, 0, 0), (-2.0, -0.2, 0), 0.04, DARK, seg=6)  # RTG boom
    for x in (-1.5, -1.8):
        tube(s, (x, -0.2, 0), (x, -0.2, 0.0001), 0.12, COPPER, seg=10)
    tube(s, (0, 0.35, 0), (0, 1.7, 0), 0.03, HULL, seg=6)       # magnetometer boom


def c_lander(s):
    for ang in range(4):
        a = math.pi / 4 + ang * math.pi / 2
        foot = (1.0 * math.cos(a), -0.9, 1.0 * math.sin(a))
        hip = (0.45 * math.cos(a), 0.0, 0.45 * math.sin(a))
        tube(s, hip, foot, 0.05, HULL, seg=6)
        disc(s, foot, (0, 1, 0), 0.16, DARK)
    tube(s, (0, -0.1, 0), (0, 0.4, 0), 0.62, GOLD, r1=0.6)      # descent stage
    for ang in range(4):
        a = ang * math.pi / 2
        tube(s, (0.5 * math.cos(a), -0.15, 0.5 * math.sin(a)),
             (0.5 * math.cos(a), 0.25, 0.5 * math.sin(a)), 0.16, HULL2)  # tanks
    tube(s, (0, 0.4, 0), (0, 1.0, 0), 0.42, WHITE, r1=0.34)     # ascent cabin
    dome(s, (0, 1.0, 0), (0, 1, 0), 0.34, WHITE)
    tube(s, (0, -0.1, 0), (0, -0.4, 0), 0.2, COPPER, r1=0.28)   # engine


def c_telescope(s):
    tube(s, (-1.4, 0, 0), (0.6, 0, 0), 0.55, DARK)              # barrel
    disc(s, (0.6, 0, 0), (1, 0, 0), 0.55, "#0E1422")           # aperture
    tube(s, (-1.6, 0, 0), (-1.4, 0, 0), 0.5, HULL2)            # bus
    for i, off in enumerate((-0.55, -0.4, -0.25)):              # sunshield layers
        panel(s, (off - 0.2, -0.7 - i * 0.06, 0), (1, 0, 0.0), (0, 0, 1),
              2.4, 1.6, _mul(GOLD, 1.0 - i * 0.12), nu=6, nv=4)
    panel(s, (-1.6, 0, 1.1), (1, 0, 0), (0, 0, 1), 0.9, 1.3, SOLAR, nu=3, nv=3)


def c_rocket(s):
    tube(s, (0, -1.8, 0), (0, 0.4, 0), 0.4, WHITE)             # first stage
    tube(s, (0, 0.4, 0), (0, 1.2, 0), 0.34, HULL)             # second stage
    tube(s, (0, 1.2, 0), (0, 1.85, 0), 0.34, WHITE, r1=0.05)  # fairing
    for ang in range(4):
        a = ang * math.pi / 2
        quad(s, (0.4 * math.cos(a), -1.8, 0.4 * math.sin(a)),
             (0.4 * math.cos(a), -1.4, 0.4 * math.sin(a)),
             (0.75 * math.cos(a), -1.85, 0.75 * math.sin(a)),
             (0.75 * math.cos(a), -1.95, 0.75 * math.sin(a)), DARK)     # fins
    for ang in range(5):
        a = ang * 2 * math.pi / 5
        tube(s, (0.2 * math.cos(a), -1.8, 0.2 * math.sin(a)),
             (0.2 * math.cos(a), -2.0, 0.2 * math.sin(a)), 0.1, COPPER, r1=0.13)


def c_shuttle(s):
    tube(s, (-1.6, 0, 0), (1.4, 0, 0), 0.42, WHITE, r1=0.12)   # fuselage
    disc(s, (1.4, 0, 0), (1, 0, 0), 0.12, DARK)
    for z in (-1, 1):                                           # delta wings
        quad(s, (-1.3, -0.1, 0), (-0.1, -0.1, 0),
             (-0.6, -0.12, z * 1.5), (-1.4, -0.12, z * 0.6), HULL2)
    quad(s, (-1.5, 0.1, 0), (-1.5, 0.8, 0), (-1.15, 0.7, 0), (-1.15, 0.1, 0), HULL)  # tail
    panel(s, (0, -0.3, 0), (1, 0, 0), (0, 0, 1), 1.6, 0.7, DARK, nu=6, nv=3)  # belly tiles


def c_cargo(s):
    tube(s, (-1.4, 0, 0), (0.6, 0, 0), 0.6, WHITE)            # pressurized module
    tube(s, (-1.5, 0, 0), (-1.4, 0, 0), 0.5, DARK)
    tube(s, (0.6, 0, 0), (1.0, 0, 0), 0.6, HULL2)            # service section
    disc(s, (1.0, 0, 0), (1, 0, 0), 0.45, GOLD)              # docking ring
    tube(s, (1.0, 0, 0), (1.2, 0, 0), 0.22, HULL)
    solar_wings(s, (0.7, 0, 0), 0.6, 1.8, 0.9)


def c_iontug(s):
    tube(s, (-1.8, 0, 0), (1.4, 0, 0), 0.12, HULL)           # spine
    box(s, (1.2, 0, 0), (0.5, 0.5, 0.5), HULL2)             # avionics
    for x in (-1.0, -0.2):
        tube(s, (x, -0.5, 0), (x, 0.5, 0), 0.22, GOLD)      # xenon tanks
    for s_ in (-1, 1):
        panel(s, (-0.6, 0, s_ * 1.6), (1, 0, 0), (0, 0, 1), 2.6, 2.0, SOLAR, nu=7, nv=4)
    for z in (-0.15, 0.15):
        tube(s, (-1.8, 0, z), (-2.05, 0, z), 0.08, TEAL, r1=0.12)  # ion thrusters


def c_spaceplane(s):
    tube(s, (-1.4, 0, 0), (1.5, 0, 0), 0.38, WHITE, r1=0.08)  # lifting body
    for z in (-1, 1):
        quad(s, (-1.0, -0.05, 0), (0.6, -0.05, 0),
             (0.2, -0.06, z * 1.2), (-1.1, -0.06, z * 0.5), HULL2)   # wings
    for z in (-1, 1):
        quad(s, (-0.2, 0.0, 0.3 * z), (0.5, 0.0, 0.2 * z),
             (0.45, 0.4, 0.25 * z), (-0.1, 0.35, 0.3 * z), HULL)     # twin tails
    disc(s, (-1.4, 0, 0), (-1, 0, 0), 0.3, COPPER)


def c_comsat(s):
    box(s, (0, 0, 0), (0.7, 0.9, 0.6), GOLD)                 # bus
    for s_ in (-1, 1):
        panel(s, (s_ * 1.5, 0, 0), (1, 0, 0), (0, 1, 0), 1.8, 0.7, SOLAR, nu=6, nv=2)
        tube(s, (s_ * 0.35, 0, 0), (s_ * 0.6, 0, 0), 0.03, DARK, seg=6)
    dish(s, (0.0, 0.0, 0.4), (0, 0, 1), 0.5, HULL)
    dish(s, (0.2, 0.0, 0.4), (0.2, 0, 1), 0.3, HULL2)
    tube(s, (0, 0.45, 0), (0, 1.1, 0), 0.02, HULL, seg=6)    # antenna


def c_miner(s):
    box(s, (0, 0, 0), (1.4, 0.7, 0.9), DARK)               # frame
    for z in (-0.6, 0.6):
        tube(s, (0.4, 0.0, z), (1.3, -0.3, z), 0.08, HULL2, seg=8)  # grapple arms
        sphere(s, (1.35, -0.3, z), 0.12, COPPER)
    for x in (-0.4, 0.4):
        tube(s, (x, 0.35, 0), (x, 0.75, 0), 0.25, HULL, r1=0.22)    # ore bins
    tube(s, (-0.7, 0, 0), (-1.2, 0, 0), 0.3, COPPER, r1=0.18)       # reactor
    panel(s, (0, -0.2, 0), (1, 0, 0), (0, 0, 1), 1.2, 0.8, SOLAR, nu=4, nv=2)


def c_crewtransport(s):
    tube(s, (-1.3, 0, 0), (-0.3, 0, 0), 0.6, WHITE)        # trunk
    panel(s, (-0.8, 0, 0.95), (1, 0, 0), (0, 0, 1), 1.0, 1.2, SOLAR, nu=3, nv=3)
    tube(s, (-0.3, 0, 0), (0.55, 0, 0), 0.6, HULL, r1=0.22)  # capsule
    dome(s, (0.55, 0, 0), (1, 0, 0), 0.22, WHITE)
    for ang in range(4):
        a = math.pi / 4 + ang * math.pi / 2
        tube(s, (0.0, 0.5 * math.cos(a), 0.5 * math.sin(a)),
             (0.1, 0.62 * math.cos(a), 0.62 * math.sin(a)), 0.06, DARK, seg=6)  # thrusters


def c_gateway(s):
    tube(s, (-1.8, 0, 0), (1.8, 0, 0), 0.14, HULL)         # backbone
    for x in (-1.0, -0.2, 0.6):
        tube(s, (x, -0.5, 0), (x, 0.5, 0), 0.36, HULL2, r1=0.36)  # habitat modules
    tube(s, (1.2, 0, -0.6), (1.2, 0, 0.6), 0.3, WHITE)
    for s_ in (-1, 1):
        panel(s, (-1.4, 0, s_ * 1.3), (1, 0, 0), (0, 0, 1), 2.0, 1.6, GOLD, nu=6, nv=3)
    dish(s, (1.7, 0.3, 0), (1, 0.3, 0), 0.4, HULL)


def c_starprobe(s):
    panel(s, (0, 0, 0), (1, 0, 0), (0, 0, 1), 3.2, 3.2, _mul(GOLD, 1.05), nu=8, nv=8)  # sail
    for c in ((-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)):
        tube(s, (0, -0.6, 0), vscale(c, 1.6), 0.02, DARK, seg=5, cap0=False)  # shrouds
    box(s, (0, -0.6, 0), (0.3, 0.3, 0.3), HULL2)          # bus
    dish(s, (0, -0.85, 0), (0, -1, 0), 0.4, HULL)


def c_depot(s):
    tube(s, (-1.6, 0, 0), (1.6, 0, 0), 0.12, HULL)        # truss
    for x in (-1.0, 0.0, 1.0):
        sphere(s, (x, 0, 0), 0.45, WHITE)                 # spherical tanks
    tube(s, (1.6, 0, 0), (1.9, 0, 0), 0.25, GOLD, r1=0.3)  # docking
    disc(s, (1.9, 0, 0), (1, 0, 0), 0.3, HULL2)
    for s_ in (-1, 1):
        panel(s, (0, s_ * 1.1, 0), (1, 0, 0), (0, 0, 1), 2.4, 0.9, SOLAR, nu=7, nv=2)


def c_orbiter(s):
    box(s, (0, 0, 0), (0.8, 0.8, 0.8), GOLD)             # bus
    dish(s, (-0.5, 0, 0), (-1, 0, 0), 0.8, HULL)
    tube(s, (0, 0.4, 0), (0, 1.6, 0), 0.03, HULL, seg=6)  # instrument boom
    box(s, (0, 1.6, 0), (0.2, 0.2, 0.5), WHITE)
    for s_ in (-1, 1):
        panel(s, (s_ * 1.3, 0, 0), (1, 0, 0), (0, 0, 1), 1.6, 0.8, SOLAR, nu=5, nv=2)
    tube(s, (0.4, 0, 0), (0.7, 0, 0), 0.18, COPPER, r1=0.22)  # main engine


def c_skycrane(s):
    box(s, (0, 0.5, 0), (1.3, 0.4, 1.0), GOLD)          # descent stage
    for ang in range(4):
        a = math.pi / 4 + ang * math.pi / 2
        tube(s, (0.55 * math.cos(a), 0.5, 0.45 * math.sin(a)),
             (0.85 * math.cos(a), 0.7, 0.7 * math.sin(a)), 0.12, HULL2, r1=0.16)  # thruster pods
        tube(s, (0.85 * math.cos(a), 0.7, 0.7 * math.sin(a)),
             (0.85 * math.cos(a), 0.55, 0.7 * math.sin(a)), 0.1, COPPER, r1=0.14)
    for z in (-0.5, 0.5):                                 # bridle cables
        tube(s, (0.2, 0.3, z), (0.2, -0.55, z * 0.6), 0.015, DARK, seg=5, cap0=False)
    box(s, (0, -0.75, 0), (1.0, 0.3, 0.7), HULL2)       # slung rover
    for x in (-0.35, 0.35):
        for z in (-0.4, 0.4):
            tube(s, (x, -0.95, z), (x, -0.95, z + 0.08), 0.13, DARK, seg=10)


def c_marsship(s):
    tube(s, (-1.6, 0, 0), (0.8, 0, 0), 0.6, WHITE)      # habitat
    dome(s, (0.8, 0, 0), (1, 0, 0), 0.6, HULL)
    for s_ in (-1, 1):                                   # radiators
        panel(s, (-0.4, s_ * 0.9, 0), (1, 0, 0), (0, 0, 1), 1.8, 0.7, RADP, nu=6, nv=2)
    tube(s, (-1.6, 0, 0), (-2.4, 0, 0), 0.2, HULL2)     # truss to engine
    tube(s, (-2.4, 0, 0), (-2.9, 0, 0), 0.3, COPPER, r1=0.42)  # nuclear engine
    for x in (-2.0, -1.8):
        tube(s, (x, -0.55, 0), (x, 0.55, 0), 0.2, GOLD)  # propellant tanks
    dish(s, (0.4, 0.6, 0), (0.2, 1, 0), 0.4, HULL)


# ======================================================================= #
#  catalog data
# ======================================================================= #
CRAFT = [
    (c_capsule, dict(name="Aegis-VII Capsule", klass="Crewed Capsule", role="LEO crew ferry",
        crew="4", mass="11.2 t", length="6.4 m", power="2.1 kW", year="2031", tone="accent",
        sys=["ECLSS", "PICA-X TPS", "Draco RCS"],
        desc="A reusable low-Earth-orbit crew ferry: a blunt-cone re-entry capsule "
             "atop a service module with twin deployable arrays.")),
    (c_station, dict(name="Concord Station", klass="Modular Outpost", role="Crewed LEO station",
        crew="7", mass="290 t", length="62 m", power="120 kW", year="2034", tone="good",
        sys=["Truss bus", "8× SAW arrays", "Robotic arm"],
        desc="A modular research outpost: three pressurized modules on a central truss "
             "with four steerable solar wings and a steerable comms dish.")),
    (c_rover, dict(name="Pathlume Rover", klass="Surface Rover", role="Planetary science",
        crew="0", mass="0.9 t", length="2.2 m", power="0.4 kW", year="2029", tone="warn",
        sys=["6-wheel rocker", "Mast cams", "Drill"],
        desc="A six-wheel rocker-bogie rover with a solar deck, a sensor mast and a "
             "steerable high-gain dish for direct-to-orbit relay.")),
    (c_probe, dict(name="Far Herald", klass="Deep-Space Probe", role="Outer-planet flyby",
        crew="0", mass="2.4 t", length="11 m", power="0.9 kW (RTG)", year="2032", tone="accent",
        sys=["RTG", "4.7 m HGA", "Magnetometer"],
        desc="A radioisotope-powered flyby probe: a gold-foil bus, a large high-gain "
             "antenna and a boom-mounted RTG balanced by a magnetometer mast.")),
    (c_lander, dict(name="Selene Lander", klass="Crewed Lander", role="Lunar descent/ascent",
        crew="2", mass="15 t", length="7.5 m", power="3.0 kW", year="2030", tone="good",
        sys=["Throttle descent", "4 legs", "Ascent stage"],
        desc="A two-stage crewed lander: a foil-clad descent stage on four shock legs "
             "with a pressurized ascent cabin and a deep-throttling main engine.")),
    (c_telescope, dict(name="Clearview Telescope", klass="Space Telescope", role="IR astronomy",
        crew="0", mass="6.2 t", length="13 m", power="2.0 kW", year="2033", tone="accent",
        sys=["Cryo optics", "5-layer shield", "Fine guidance"],
        desc="An infrared observatory with a chilled optical barrel shaded by a "
             "five-layer tensioned sunshield, on a sun-tracking solar bus.")),
    (c_rocket, dict(name="Vulcan-Heavy", klass="Launch Vehicle", role="Heavy lift",
        crew="0", mass="540 t", length="64 m", power="—", year="2028", tone="bad",
        sys=["5× core engines", "Cryo upper", "Grid fins"],
        desc="A two-stage heavy-lift launcher: a five-engine cryogenic core, a "
             "single-engine upper stage and a protective payload fairing.")),
    (c_shuttle, dict(name="Albatross Orbiter", klass="Spaceplane", role="Reusable orbiter",
        crew="5", mass="78 t", length="34 m", power="7 kW", year="2035", tone="good",
        sys=["Delta wing", "TPS tiles", "OMS pods"],
        desc="A reusable winged orbiter with a delta planform, a tiled thermal belly "
             "and a vertical stabilizer for hypersonic re-entry and runway landing.")),
    (c_cargo, dict(name="Porter Freighter", klass="Cargo Vehicle", role="Station resupply",
        crew="0", mass="20 t", length="10 m", power="5 kW", year="2030", tone="warn",
        sys=["Pressurized hold", "CBM port", "2× arrays"],
        desc="An automated resupply freighter: a pressurized cargo module, a service "
             "section with two solar wings and a common-berthing docking ring.")),
    (c_iontug, dict(name="Halcyon Tug", klass="Electric Tug", role="Orbit raising",
        crew="0", mass="9 t", length="9 m", power="40 kW", year="2036", tone="teal",
        sys=["Hall thrusters", "Xenon tanks", "Mega-arrays"],
        desc="A solar-electric orbital tug: a slender truss carrying two huge arrays, "
             "twin xenon tanks and a cluster of high-efficiency ion thrusters.")),
    (c_spaceplane, dict(name="Kestrel Spaceplane", klass="Spaceplane", role="Suborbital crew",
        crew="6", mass="22 t", length="15 m", power="3 kW", year="2034", tone="accent",
        sys=["Lifting body", "Twin tails", "Hybrid motor"],
        desc="A lifting-body suborbital spaceplane with stubby wings, twin canted "
             "tails and a single hybrid rocket motor for runway-to-space hops.")),
    (c_comsat, dict(name="Meridian-K", klass="Comms Satellite", role="GEO broadband",
        crew="0", mass="6 t", length="35 m (deployed)", power="18 kW", year="2031", tone="accent",
        sys=["Ka/Ku payload", "2× SADA wings", "Steerable dishes"],
        desc="A geostationary broadband satellite: a foil bus with two long solar "
             "wings, multiple steerable reflectors and a deployable omni antenna.")),
    (c_miner, dict(name="Prospector-9", klass="Asteroid Miner", role="Resource extraction",
        crew="0", mass="14 t", length="6 m", power="12 kW", year="2038", tone="warn",
        sys=["Grapple arms", "Ore bins", "Fission reactor"],
        desc="A robotic asteroid miner: an open frame with two grapple arms and "
             "contact drills, ore hoppers and a compact fission reactor.")),
    (c_crewtransport, dict(name="Vanguard Crew", klass="Crew Vehicle", role="Beyond-LEO crew",
        crew="4", mass="13 t", length="8 m", power="2.5 kW", year="2033", tone="good",
        sys=["Solar trunk", "Ablative TPS", "RCS quads"],
        desc="A beyond-LEO crew vehicle: a pressurized capsule on a solar-equipped "
             "trunk, ringed by reaction-control thruster quads.")),
    (c_gateway, dict(name="Tideway Gateway", klass="Cislunar Station", role="Lunar gateway",
        crew="4", mass="40 t", length="28 m", power="60 kW", year="2037", tone="teal",
        sys=["Hab modules", "Power bus", "Logistics port"],
        desc="A small cislunar gateway: three habitat modules and a node on a power "
             "backbone, with foil arrays and a high-gain relay dish.")),
    (c_starprobe, dict(name="Lightsail Errant", klass="Interstellar Probe", role="Sail demonstrator",
        crew="0", mass="0.1 t", length="32 m (sail)", power="0.2 kW", year="2040", tone="accent",
        sys=["Solar sail", "Star tracker", "Micro-bus"],
        desc="A solar-sail demonstrator: a large reflective square membrane on four "
             "shrouds supporting a micro-bus and a small communications dish.")),
    (c_depot, dict(name="Wellspring Depot", klass="Propellant Depot", role="Orbital refueling",
        crew="0", mass="65 t", length="34 m", power="8 kW", year="2039", tone="good",
        sys=["Cryo tanks", "Zero-boiloff", "Transfer arm"],
        desc="An orbital propellant depot: three spherical cryogenic tanks on a truss "
             "with zero-boil-off coolers, solar panels and a docking interface.")),
    (c_orbiter, dict(name="Sentinel Orbiter", klass="Science Orbiter", role="Planetary orbiter",
        crew="0", mass="3.1 t", length="9 m", power="2.2 kW", year="2032", tone="accent",
        sys=["HGA", "Instrument boom", "Bipropellant"],
        desc="A planetary science orbiter: a compact bus with a large high-gain dish, "
             "a boom-mounted instrument package and two tracking solar panels.")),
    (c_skycrane, dict(name="Talon Sky-Crane", klass="Descent System", role="Rover delivery",
        crew="0", mass="3.6 t", length="5 m", power="1 kW", year="2035", tone="warn",
        sys=["Throttle pods", "Bridle", "Radar altimeter"],
        desc="A powered descent stage that lowers a slung rover on a bridle under "
             "four throttleable thruster pods before flying clear.")),
    (c_marsship, dict(name="Ares Transit", klass="Interplanetary Ship", role="Crewed Mars transit",
        crew="6", mass="330 t", length="58 m", power="200 kW", year="2042", tone="bad",
        sys=["NTR engine", "Radiators", "Spin hab"],
        desc="A crewed Mars transit vehicle: a long habitat with deployable radiators, "
             "propellant tanks and a nuclear-thermal engine on a stand-off truss.")),
]


# ======================================================================= #
#  page composition
# ======================================================================= #
def _backdrop(page, vp):
    x, y, w, h = vp
    page.rect(vp, fill={"kind": "linear", "angle": 135,
                        "stops": [{"color": SPACE2, "position": "0%"},
                                  {"color": SPACE, "position": "100%"}]},
              radius=16)
    # faint horizon grid
    for i in range(1, 5):
        gy = y + h * i / 5
        page.line([x + 16, gy], [x + w - 16, gy], stroke="#1B2440",
                  stroke_style={"stroke_width": 1})
    # scattered stars (decorative, deterministic)
    stars = []
    seed = 12345
    for _ in range(46):
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        sx = x + 16 + (seed % 1000) / 1000 * (w - 32)
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        sy = y + 16 + (seed % 1000) / 1000 * (h - 32)
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        r = 1.0 + (seed % 100) / 100 * 1.6
        stars.append({"type": "rect", "box": [sx, sy, r, r], "fill": "#46557A",
                      "radius": r / 2, "decorative": True})
    page.add({"type": "group", "children": stars, "meta": {"role": "stars"}})


def entry_page(b, i, builder, meta):
    page = b.page(f"craft_{i:02d}", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    page.rect([0, 0, W, H], fill=SPACE)
    notes = []

    # header
    notes.append(_t([M, 40, 400, 18], f"ORBITAL REGISTRY · NO. {i:02d}/20", "reg"))
    notes.append(_t([M, 62, 500, 18], meta["role"].upper(), "klass"))
    notes.append(_t([W - M - 220, 44, 220, 18], "FRAMEGRAPH · SCENE3D", "foot",
                    align="right"))

    # 3D viewport
    vp = [M, 96, 800, H - 96 - M]
    _backdrop(page, vp)
    scene = Scene3D()
    builder(scene)
    page.add(scene.render(camera=CAMERA, box=inset(vp, 40), fill=HULL, stroke=DARK))
    notes.append(_t([vp[0] + 20, vp[1] + vp[3] - 30, vp[2] - 40, 16],
                    "Procedural mesh · half-Lambert shading · painter's-sorted projection",
                    "foot"))

    # spec panel
    px = M + 800 + 28
    pw = W - px - M
    notes.append(_t([px, 110, pw, 16], meta["klass"], "klass"))
    notes.append(_t([px, 130, pw, 40], meta["name"], "name"))

    th = default_theme()
    page.add(badge([px, 182, 150, 26], meta["role"], tone=meta["tone"], theme=th))

    stats = [("Crew", meta["crew"]), ("Mass", meta["mass"]),
             ("Length", meta["length"]), ("Power", meta["power"])]
    for (lbl, val), bx in zip(stats, grid([px, 224, pw, 150], cols=2, rows=2,
                                          gap=14, row_gap=14)):
        page.add(_kpi_dark(bx, lbl, val))

    # description
    notes.append(_t([px, 392, pw, 14], "PROFILE", "lbl"))
    notes.append(_t([px, 412, pw, 120], meta["desc"], "body"))

    # spec table
    notes.append(_t([px, 540, pw, 14], "REGISTRY DATA", "lbl"))
    page.add(table([px, 562, pw, 132],
                   [{"label": "Field", "width": "45%"}, {"label": "Value", "width": "55%"}],
                   [["Classification", meta["klass"]], ["First flight", meta["year"]],
                    ["Role", meta["role"]], ["Registry", f"OR-{1000 + i}"]],
                   header=False, row_height=32, theme=th))

    # systems
    notes.append(_t([px, 712, pw, 14], "KEY SYSTEMS", "lbl"))
    sx = px
    for sysname in meta["sys"]:
        bw = 22 + len(sysname) * 7
        page.add(badge([sx, 732, bw, 24], sysname, tone="muted", theme=th))
        sx += bw + 8

    page.add({"type": "group", "children": notes, "meta": {"role": "labels"}})


def _kpi_dark(box, label, value):
    x, y, w, h = box
    return {"type": "group", "box": [x, y, w, h], "meta": {"widget": "kpi"}, "children": [
        {"type": "rect", "box": [0, 0, w, h], "fill": "#101A30",
         "stroke": "#243152", "stroke_style": {"stroke_width": 1}, "radius": 12,
         "decorative": True},
        {"type": "text", "box": [16, 16, w - 32, 14], "text": label.upper(),
         "style": dict(font_family=SANS, font_size=11, font_weight=700, color="#7E8CA6",
                       letter_spacing=0.8, vertical_align="top")},
        {"type": "text", "box": [16, 36, w - 32, 34], "text": value,
         "style": dict(font_family=SANS, font_size=24, font_weight=800, color="#F2F5FA",
                       letter_spacing=-0.5, vertical_align="top", overflow="shrink_to_fit",
                       min_font_size=13)},
    ]}


def _t(box, text, style, **overrides):
    """A text object. ``style`` is a defined text-style name; ``overrides`` (e.g.
    align) are merged inline from that style's source props in STYLES."""
    if overrides:
        base = STYLES[style] if isinstance(style, str) else dict(style)
        st = {**base, **overrides}
    else:
        st = style
    return {"type": "text", "box": [float(v) for v in box], "text": str(text), "style": st}


# ---- cover ---------------------------------------------------------------- #
def cover(b):
    page = b.page("cover", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    page.rect([0, 0, W, H], fill=SPACE)
    _backdrop(page, [0, 0, W, H])
    notes = []
    # hero craft
    scene = Scene3D()
    c_station(scene)
    page.add(scene.render(camera=CAMERA, box=[60, 150, 560, 560], fill=HULL, stroke=DARK))

    notes.append(_t([640, 150, 760, 20], "FRAMEGRAPH · SCENE3D CATALOG", "reg"))
    notes.append(_t([640, 184, 760, 60], "Orbital Registry", "cover"))
    notes.append(_t([640, 252, 760, 30], "A Catalog of Spacecraft", "cover",
                    font_size=26, color="#A9B6CE", letter_spacing=-0.4))
    notes.append(_t([640, 332, 720, 70],
                    "Twenty craft, every one a procedural 3D model built and projected "
                    "with the FrameGraph SDK — capsules to interplanetary ships.",
                    "coversub"))

    # index — two columns of 10
    half = len(CRAFT) // 2
    cols = row([640, 430, 740, 420], gap=40, weights=[1, 1])
    for ci, colbox in enumerate(cols):
        for r in range(half):
            idx = ci * half + r
            _, meta = CRAFT[idx]
            ry = colbox[1] + r * 40
            notes.append(_t([colbox[0], ry, 36, 16], f"{idx + 1:02d}", "idxno"))
            notes.append(_t([colbox[0] + 40, ry, colbox[2] - 210, 16], meta["name"], "idx"))
            notes.append(_t([colbox[0] + colbox[2] - 150, ry, 150, 16], meta["klass"],
                            "idxk", align="right"))

    notes.append(_t([60, H - 40, 900, 16],
                    "Built with framegraph.sdk · Scene3D + widgets · one composed document",
                    "foot"))
    page.add({"type": "group", "children": notes, "meta": {"role": "labels"}})


def build():
    b = DocumentBuilder(title="Orbital Registry — Spacecraft Catalog", profile="deck", lang="en")
    for name, style in STYLES.items():
        b.define_text_style(name, **style)
    cover(b)
    for i, (builder, meta) in enumerate(CRAFT, start=1):
        entry_page(b, i, builder, meta)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "spacecraft-catalog.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
