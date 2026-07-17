#!/usr/bin/env python3
"""Three real fighter-jet mechanism patents, reconstructed as literal 3D
``Scene3D`` models — one page per patent, plus a cover/index page.

Sources (verified via Google Patents, cited again in-page on each entry):

  * US4212441A — "Wing pivot assembly for variable sweep wing aircraft"
    (US Dept. of the Air Force; filed 1978-05-11, granted 1980-07-15).
  * US4363445A — "Thrust-vectoring nozzle for jet propulsion system"
    (SNECMA, now Safran Aircraft Engines; filed 1980-11-24, granted 1982-12-14).
  * EP3608220A1 — "Folding wing hinge, aircraft and method therefor"
    (Boeing Co; priority 2018-08-06, granted 2022-06-29).

These are **schematic topology reconstructions** built from each patent's
claims/description (component names, spatial arrangement, load path) — not
to-scale CAD traced from the original patent drawings, which this script does
not have pixel access to. Every named part in the legend quotes the patent's
own element name/number; dimensions are illustrative. Two rotation states are
drawn per mechanism (solid = primary position, translucent = the mechanism's
other extreme) to show what the patent's own claims say the part *does*, not
just what it looks like at rest.

Run from the repository root::

    uv run python examples/patent_fighter_jet_mechanisms_3d.py
"""
from __future__ import annotations

import math
import os
import sys

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
    grid,
    inset,
    linear_gradient,
    rgba,
    row,
    serialize,
    table,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1440, 900
M = 56
CANVAS = {"size": [W, H], "units": "px"}
TH = default_theme()
SANS = list(TH.font)
MONO = list(TH.mono)

# ---- blueprint palette ------------------------------------------------- #
BG = "#081522"
BG2 = "#0D2035"
GRIDLINE = "#173350"
STEEL = "#9FB3C8"      # fixed / non-moving structure
STEEL_DK = "#5E7086"   # fixed structure, recessed / secondary
BRASS = "#D2A94E"      # the part the patent's claim is actually about
AMBER = "#E8A23C"      # pins, bearings, actuators — load-carrying highlights
GHOST = "#7FD8E8"      # translucent "other end of travel" overlay
WHITE = "#EAF2F8"
MUTE = "#7E93AC"

STYLES = {
    "reg": dict(font_family=MONO, font_size=12, font_weight=700, color="#7FE3C0",
                letter_spacing=2.0),
    "klass": dict(font_family=SANS, font_size=14, font_weight=700, color="#9FB0CC",
                  letter_spacing=0.5),
    "name": dict(font_family=SANS, font_size=27, font_weight=800, color="#F2F5FA",
                 letter_spacing=-0.5, line_height=1.15),
    "body": dict(font_family=SANS, font_size=13, color="#C3CCDA", line_height=1.55),
    "lbl": dict(font_family=SANS, font_size=11, font_weight=700, color="#7E8CA6",
                letter_spacing=0.8, text_transform="uppercase"),
    "foot": dict(font_family=MONO, font_size=10.5, color="#5E6A82", letter_spacing=0.6,
                 line_height=1.5),
    "cover": dict(font_family=SANS, font_size=52, font_weight=800, color="#F2F5FA",
                  letter_spacing=-1.6),
    "coversub": dict(font_family=SANS, font_size=15.5, color="#A9B6CE", line_height=1.6),
    "idxno": dict(font_family=MONO, font_size=12, font_weight=700, color="#7FE3C0"),
    "idx": dict(font_family=SANS, font_size=15, font_weight=700, color="#EAF2F8"),
    "idxk": dict(font_family=SANS, font_size=11.5, color="#8093AE", line_height=1.4),
    "legend": dict(font_family=SANS, font_size=11.5, color="#C3CCDA"),
}


# ======================================================================= #
#  vector + shaded-face parts library (tube / box / oriented-box / sphere /
#  arc-shell), painter's-algorithm friendly: each face is one flat polygon
#  with a baked-in normal-lit fill, appended straight into a Scene3D.
# ======================================================================= #
def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vscale(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def vdot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def vcross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
                          a[0] * b[1] - a[1] * b[0])


def vlen(a): return math.sqrt(vdot(a, a)) or 1.0
def vunit(a): l = vlen(a); return (a[0] / l, a[1] / l, a[2] / l)


def rot_x(p, deg):
    r = math.radians(deg); co, si = math.cos(r), math.sin(r)
    x, y, z = p
    return (x, y * co - z * si, y * si + z * co)


def rot_y(p, deg):
    r = math.radians(deg); co, si = math.cos(r), math.sin(r)
    x, y, z = p
    return (x * co + z * si, y, -x * si + z * co)


def rot_z(p, deg):
    r = math.radians(deg); co, si = math.cos(r), math.sin(r)
    x, y, z = p
    return (x * co - y * si, x * si + y * co, z)


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
LIGHT = vunit((-0.40, 0.85, 0.35))


def _shade(pts, base):
    if len(pts) < 3:
        return base
    n = vunit(vcross(vsub(pts[1], pts[0]), vsub(pts[2], pts[0])))
    d = vdot(n, LIGHT)
    i = AMBIENT + (1.0 - AMBIENT) * (0.5 + 0.5 * d)   # half-Lambert
    return _mul(base, i), i


def face(scene, pts, base, *, edge=True, alpha=None):
    shaded, _i = _shade(pts, base)
    if alpha is None:
        style = {"fill": shaded}
        style["stroke"] = _mul(shaded, 0.62) if edge else shaded
        if edge:
            style["stroke_style"] = {"stroke_width": 0.5}
    else:
        style = {"fill": rgba(shaded, alpha), "stroke": "none"}
    scene.mesh(pts, [list(range(len(pts)))], **style)


def _ring(center, u, v, r, seg):
    return [vadd(center, vadd(vscale(u, r * math.cos(2 * math.pi * k / seg)),
                              vscale(v, r * math.sin(2 * math.pi * k / seg))))
            for k in range(seg)]


def tube(scene, p0, p1, r0, base, *, r1=None, seg=18, cap0=True, cap1=True,
         edge=True, alpha=None):
    r1 = r0 if r1 is None else r1
    a, u, v = _basis(vsub(p1, p0))
    ring0 = _ring(p0, u, v, r0, seg)
    ring1 = _ring(p1, u, v, r1, seg)
    for k in range(seg):
        kn = (k + 1) % seg
        face(scene, [ring0[k], ring0[kn], ring1[kn], ring1[k]], base, edge=edge, alpha=alpha)
    if cap0 and r0 > 1e-4:
        for k in range(seg):
            face(scene, [p0, ring0[(k + 1) % seg], ring0[k]], base, edge=edge, alpha=alpha)
    if cap1 and r1 > 1e-4:
        for k in range(seg):
            face(scene, [p1, ring1[k], ring1[(k + 1) % seg]], base, edge=edge, alpha=alpha)


def sphere(scene, center, r, base, *, seg=16, rings=8, edge=True, alpha=None):
    a, u, v = _basis((0, 1, 0))
    pts = [[vadd(center, vadd(vscale(a, r * math.cos(math.pi * i / rings)),
            vadd(vscale(u, r * math.sin(math.pi * i / rings) * math.cos(2 * math.pi * j / seg)),
                 vscale(v, r * math.sin(math.pi * i / rings) * math.sin(2 * math.pi * j / seg)))))
            for j in range(seg)] for i in range(rings + 1)]
    for i in range(rings):
        for j in range(seg):
            jn = (j + 1) % seg
            face(scene, [pts[i][j], pts[i][jn], pts[i + 1][jn], pts[i + 1][j]], base,
                 edge=edge, alpha=alpha)


def obox(scene, center, udir, vdir, wdir, su, sv, sw, base, *, edge=True, alpha=None):
    """Oriented box: su/sv/sw are full extents along the (unit-ish) u/v/w axes."""
    u, v, w = vunit(udir), vunit(vdir), vunit(wdir)
    hu, hv, hw = su / 2, sv / 2, sw / 2

    def P(su_, sv_, sw_):
        return vadd(center, vadd(vscale(u, su_ * hu), vadd(vscale(v, sv_ * hv), vscale(w, sw_ * hw))))

    c = [P(-1, -1, -1), P(1, -1, -1), P(1, 1, -1), P(-1, 1, -1),
         P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1)]
    for f in ([0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2],
              [4, 5, 1, 0], [3, 2, 6, 7]):
        face(scene, [c[i] for i in f], base, edge=edge, alpha=alpha)


def arc_shell(scene, p0, p1, r, start_deg, end_deg, base, *, seg=12, edge=True, alpha=None):
    """A partial cylindrical shell ('N° arc of a cylinder') between p0 and p1."""
    _a, u, v = _basis(vsub(p1, p0))
    s0, s1 = math.radians(start_deg), math.radians(end_deg)

    def ring_arc(center):
        return [vadd(center, vadd(vscale(u, r * math.cos(s0 + (s1 - s0) * k / seg)),
                                   vscale(v, r * math.sin(s0 + (s1 - s0) * k / seg))))
                for k in range(seg + 1)]

    ring0, ring1 = ring_arc(p0), ring_arc(p1)
    for k in range(seg):
        face(scene, [ring0[k], ring0[k + 1], ring1[k + 1], ring1[k]], base, edge=edge, alpha=alpha)


def rot_axis(p, axis_point, axis_dir, deg):
    """Rotate point/direction ``p`` by ``deg`` about the general 3D line through
    ``axis_point`` with direction ``axis_dir`` (Rodrigues' rotation formula) —
    needed where a patent's own hinge/fold line isn't aligned to a coordinate
    axis (e.g. EP3608220A1's fold line runs slanted across the wingtip)."""
    a = vunit(axis_dir)
    rel = vsub(p, axis_point)
    r = math.radians(deg)
    co, si = math.cos(r), math.sin(r)
    term1 = vscale(rel, co)
    term2 = vscale(vcross(a, rel), si)
    term3 = vscale(a, vdot(a, rel) * (1 - co))
    return vadd(axis_point, vadd(vadd(term1, term2), term3))


def wedge(scene, center, taper_dir, const_dir, depth_dir, size_near, size_far,
          const_size, depth_size, base, *, edge=True, alpha=None):
    """A box whose extent along ``taper_dir`` tapers from ``size_near`` (at
    -``depth_dir``) to ``size_far`` (at +``depth_dir``) — a laminated wedge,
    not a plain prism (e.g. US4363445A's elastic-element stack, thin at the
    engine axis and wide where it hugs the duct wall)."""
    tp, cd, dd = vunit(taper_dir), vunit(const_dir), vunit(depth_dir)
    hc, hd = const_size / 2, depth_size / 2

    def P(t_, c_, d_):
        ht = (size_near / 2) if d_ < 0 else (size_far / 2)
        return vadd(center, vadd(vscale(tp, t_ * ht), vadd(vscale(cd, c_ * hc), vscale(dd, d_ * hd))))

    c = [P(-1, -1, -1), P(1, -1, -1), P(1, 1, -1), P(-1, 1, -1),
         P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1)]
    for f in ([0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2],
              [4, 5, 1, 0], [3, 2, 6, 7]):
        face(scene, [c[i] for i in f], base, edge=edge, alpha=alpha)


def gimbal(scene, center, base_a, base_b, *, r=0.19, t=0.035, seg=20):
    """A stack of thin, tapering discs standing in for a flat-plate rotary
    bearing (US4212441A Figs. 4/5 draw the wing-sweep bearing as sandwiched
    plates with a rotation arrow, not a smooth ball)."""
    tube(scene, vadd(center, (-t, 0, 0)), center, r, base_a, seg=seg)
    tube(scene, center, vadd(center, (t, 0, 0)), r * 0.80, base_b, seg=seg)
    tube(scene, vadd(center, (t, 0, 0)), vadd(center, (2 * t, 0, 0)), r * 0.60, base_a, seg=seg)


# ======================================================================= #
#  mechanism 1 — US4212441A: wing pivot assembly for variable-sweep wing
#  local axes: Y = vertical pivot axis · X = spanwise (fuselage −X / tip +X)
#  · Z = fore-aft (+Z toward the nose)
# ======================================================================= #
def build_wing_pivot(s):
    # FIXED (fuselage-side, non-rotating) ------------------------------- #
    tube(s, (0, 0.02, 0), (0, 0.95, 0), 0.15, STEEL, cap0=False, cap1=True)       # outer pin element 52
    tube(s, (0, -0.95, 0), (0, -0.02, 0), 0.15, STEEL_DK, cap0=True, cap1=False)  # inner pin element 54
    tube(s, (0, -0.05, 0), (0, 0.05, 0), 0.20, AMBER, cap0=False, cap1=False)     # pin retainer 56

    for ly in (0.55, -0.55):                                                     # inboard lugs 26 / 28
        obox(s, (-0.95, ly, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), 1.55, 0.14, 0.46, STEEL)

    # anti-rotation bracket (Fig. 2's element 90): a substantial diagonal PLATE
    # above the bore ending in a bolted yoke (82/84/88) — not the thin rod-and-
    # collar this originally drew; the plate is what actually keeps the pin
    # from turning while the outboard lugs sweep around it.
    plate_a, plate_b = (0.0, 0.55, 0.0), (-1.55, 0.95, 0.35)
    plate_len = vlen(vsub(plate_b, plate_a))
    obox(s, vscale(vadd(plate_a, plate_b), 0.5), vunit(vsub(plate_b, plate_a)),
         (0, 0, 1), (0, 1, 0), plate_len, 0.16, 0.10, STEEL_DK)
    sphere(s, plate_b, 0.10, AMBER)                                              # yoke ball 82/84

    # shear load path: a rigid, two-ball-jointed strut (66) — ball / rod / ball
    # — not the plain rod this originally drew; swivels at 64 (near the bore)
    # and 68/78 (toward the fuselage closeout rib).
    ball_near, ball_far = (0.05, -0.20, 0.30), (-1.35, -0.30, 0.55)
    sphere(s, ball_near, 0.07, AMBER)
    sphere(s, ball_far, 0.07, AMBER)
    tube(s, ball_near, ball_far, 0.045, STEEL_DK, cap0=False, cap1=False)        # strut 66
    obox(s, vadd(ball_far, (-0.25, -0.05, 0.05)), (1, 0, 0), (0, 1, 0), (0, 0, 1),
         0.5, 0.4, 0.14, STEEL_DK)                                               # fuselage closeout rib

    arc_shell(s, (0, 0.16, 0), (0, 0.34, 0), 0.24, -10, 90, STEEL_DK)             # outboard shear fitting 83
    arc_shell(s, (0, -0.34, 0), (0, -0.16, 0), 0.24, -12, 95, STEEL_DK)           # inboard shear fitting 60

    # ROTATING (outboard lugs + wing), drawn at two sweep angles --------- #
    def outer(sweep_deg, base_lug, base_wing, *, alpha=None):
        d = rot_y((1.0, 0.0, 0.0), sweep_deg)
        w = rot_y((0.0, 0.0, 1.0), sweep_deg)
        for ly in (0.55, -0.55):
            c = rot_y((1.05, ly, 0.0), sweep_deg)
            obox(s, c, d, (0, 1, 0), w, 1.35, 0.14, 0.46, base_lug, alpha=alpha)
        wc = rot_y((2.55, 0.0, 0.0), sweep_deg)
        obox(s, wc, d, (0, 1, 0), w, 1.9, 0.30, 1.3, base_wing, alpha=alpha)

    outer(18, STEEL, BRASS)                    # ~18° — loiter sweep, solid
    outer(62, GHOST, GHOST, alpha=0.30)        # ~62° — dash sweep, ghost overlay

    # "spherical" bearings (86) — Figs. 4/5 actually draw a sandwiched flat-
    # plate gimbal stack with a rotation arrow, not a smooth ball; the discs
    # sit face-on to the front-elevation view, centered on the fixed pivot axis
    for ly in (0.55, -0.55):
        gimbal(s, (0, ly, 0), AMBER, STEEL_DK)


WING_PIVOT_CAMERA = Camera(eye=Vec3(3.4, 2.1, 3.7), target=Vec3(0.5, -0.05, 0.0), fov=38)
WING_PIVOT_LEGEND = [
    (STEEL, "Pivot pin (50) — two-piece 52/54 + retainer 56"),
    (STEEL, "Inboard lugs 26/28 — fixed to fuselage carry-through"),
    (BRASS, "Outboard lugs 30/32 + wing root — sweep with the wing"),
    (AMBER, "Bearings (86) — flat gimbal-plate stack (Figs. 4/5), not a ball"),
    (STEEL_DK, "Anti-rotation plate (90) + two-ball strut (66) + shear fittings 83/60"),
    (GHOST, "18° ↔ 62° sweep envelope (ghost = second extreme)"),
]
WING_PIVOT_META = dict(
    patent="US 4,212,441 A", title="Wing Pivot Assembly for Variable Sweep Wing Aircraft",
    assignee="United States Department of the Air Force",
    assignee_short="United States Department of the Air Force",
    office="USPTO", filed="1978-05-11", granted="1980-07-15",
    url="patents.google.com/patent/US4212441A",
    desc=("A fail-safe pivot: paired inboard lugs (fixed) and outboard lugs (wing-side) "
          "share a two-piece pin through spherical, Teflon-lined bearings that carry bending "
          "loads while letting the wing sweep; a separate anti-rotation device keeps the pin "
          "itself from turning, and an arc-shaped shear-fitting/strut chain routes vertical "
          "shear into the fuselage independently of the bending path."),
)


# ======================================================================= #
#  mechanism 2 — US4363445A: thrust-vectoring nozzle (SNECMA)
#  local axes: X = engine centerline (−X core / +X exhaust)
# ======================================================================= #
def build_thrust_nozzle(s):
    tube(s, (-2.0, 0, 0), (0, 0, 0), 0.60, STEEL, r1=0.56, cap0=True, cap1=False)   # fixed duct (1)
    tube(s, (-0.08, 0, 0), (0.08, 0, 0), 0.64, STEEL_DK, cap0=False, cap1=False)    # spherical collar (3)

    def nozzle(deg, base, *, alpha=None):
        p0 = rot_z((0, 0, 0), deg)
        p1 = rot_z((1.55, 0, 0), deg)
        tube(s, p0, p1, 0.56, base, r1=0.40, cap0=False, cap1=True, alpha=alpha)    # pivoting part (2)
        e0, e1 = rot_z((-0.05, 0, 0), deg), rot_z((0.08, 0, 0), deg)
        tube(s, e0, e1, 0.60, base, cap0=False, cap1=False, alpha=alpha)            # spherical edge (12)

    nozzle(0, BRASS)                       # neutral thrust line — solid
    nozzle(-16, GHOST, alpha=0.30)         # ~16° vectored — ghost overlay

    # elastic laminate sets (10/15): Fig. 1 draws these as a curved, TAPERED
    # wedge hugging the duct wall (thin at the engine axis, wide at the wall)
    # — not the four discrete rectangular pads this originally drew.
    for k in range(4):
        ang = math.radians(90 * k + 45)
        radial = (0.0, math.cos(ang), math.sin(ang))
        tangential = (0.0, -math.sin(ang), math.cos(ang))
        base_pt = (0.0, 0.60 * math.cos(ang), 0.60 * math.sin(ang))
        wedge(s, base_pt, tangential, (1, 0, 0), radial, 0.08, 0.26, 0.22, 0.34, STEEL_DK)

    # jacks (4/8/23): Fig. 1 draws these as long actuator rods running nearly
    # parallel to the duct wall, then a short rod to the extension point (6)
    # on the pivoting nozzle — not short rams straight between the two parts.
    for k in range(3):
        ang = math.radians(120 * k + 90)
        wall_r = 0.74
        ram_a = (-1.35, wall_r * math.cos(ang), wall_r * math.sin(ang))
        ram_b = (-0.35, wall_r * math.cos(ang), wall_r * math.sin(ang))
        pivot_pt = rot_z((0.30, 0.66 * math.cos(ang), 0.66 * math.sin(ang)), -16)
        tube(s, ram_a, ram_b, 0.05, AMBER, seg=10)                                # jack ram, along the wall
        tube(s, ram_b, pivot_pt, 0.04, AMBER, seg=10)                             # rod to extension (6)
        sphere(s, ram_a, 0.055, AMBER, seg=10, rings=6)
        sphere(s, pivot_pt, 0.05, AMBER, seg=10, rings=6)


NOZZLE_CAMERA = Camera(eye=Vec3(2.7, 1.5, 3.1), target=Vec3(-0.2, 0.0, 0.0), fov=36)
NOZZLE_LEGEND = [
    (STEEL, "Fixed duct (1) + spherical collar (3)"),
    (BRASS, "Pivoting nozzle (2) — the vectored thrust line"),
    (STEEL_DK, "Elastic laminate (10/15) — tapered wedge, thin at the axis, wide at the wall"),
    (AMBER, "Jacks (4/8/23) — wall-parallel rams to extension points (6), differential to vector"),
    (GHOST, "0° ↔ ~16° deflection (ghost = vectored)"),
]
NOZZLE_META = dict(
    patent="US 4,363,445 A", title="Thrust-Vectoring Nozzle for Jet Propulsion System",
    assignee="SNECMA — Société Nationale d'Etude et de Construction de Moteurs d'Aviation",
    assignee_short="SNECMA (now Safran Aircraft Engines)",
    office="USPTO (French assignee)", filed="1980-11-24", granted="1982-12-14",
    url="patents.google.com/patent/US4363445A",
    desc=("No gimbal bearing: the pivoting nozzle is centered by pairs of rubber/metal or "
          "corrugated-metal elastic elements distributed around the joint, cut so their "
          "shared symmetry axes meet on the engine centerline. Jacks push the nozzle off-axis; "
          "aligned element pairs twist while diametrically opposite pairs compress, giving "
          "stable steering with no sliding mechanical bearing at all."),
)


# ======================================================================= #
#  mechanism 3 — EP3608220A1: folding wing hinge (Boeing)
#  local axes: Z = hinge/fold axis · X = spanwise (root −X / tip +X) ·
#  Y = vertical (the tip folds upward, +Y)
# ======================================================================= #
def build_folding_hinge(s):
    obox(s, (-1.15, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), 2.3, 0.22, 1.9, STEEL)  # fixed portion 204

    # Fig. 2A draws the fold line (206) crossing the wingtip at an angle, not
    # perpendicular to the span — every knuckle/pin/drive-block position below
    # is placed along this slanted axis instead of the plain Z axis.
    HINGE_AXIS = vunit((0.30, 0.0, 1.0))

    # interdigitated knuckles: Figs. 3/4 draw a continuous comb of rectangular
    # teeth (finger-joint style, each side's tooth overlapping past center) —
    # not the discrete round bosses this originally drew.
    zs = [-0.82, -0.55, -0.27, 0.0, 0.27, 0.55, 0.82]
    owners = ["fixed", "fold", "fixed", "fold", "fixed", "fold", "fixed"]
    tooth_len, tooth_h, tooth_w = 0.34, 0.16, 0.24
    overlap = 0.06
    for z, own in zip(zs, owners):
        axis_pt = vscale(HINGE_AXIS, z)
        col = STEEL_DK if own == "fixed" else BRASS
        x_side = -1.0 if own == "fixed" else 1.0
        tooth_c = vadd(axis_pt, (x_side * (tooth_len / 2 - overlap), 0, 0))
        obox(s, tooth_c, (1, 0, 0), (0, 1, 0), (0, 0, 1), tooth_len, tooth_h, tooth_w, col)

    # hinge pins: EP3608220A1 Fig. 6A shows one long primary pin (600) plus two
    # short pins (601/602) only at the outermost knuckle pairs — not three
    # equal segments.
    for t0, t1, w in ((-0.86, -0.24, 0.045), (-0.24, 0.24, 0.07), (0.24, 0.86, 0.045)):
        p0, p1 = vscale(HINGE_AXIS, t0), vscale(HINGE_AXIS, t1)
        tube(s, p0, p1, w, AMBER, seg=10)

    tube(s, (0.16, 0, 0), (0.42, 0, 0), 0.09, GHOST, r1=0.05, seg=10)               # input fitting 610
    tube(s, (0.06, 0, 0), (0.18, 0, 0), 0.13, STEEL_DK, seg=12)                     # spline coupling 620
    for t in (-0.30, 0.30):                                                        # hinge pin bushings 760/761
        p = vscale(HINGE_AXIS, t)
        tube(s, vadd(p, (-0.03, 0, 0)), vadd(p, (0.03, 0, 0)), 0.16, STEEL, cap0=False, cap1=False, seg=12)

    # rotary drive block (530): Fig. 6A places this CENTRALLY in the knuckle
    # stack, not at the outboard end.
    obox(s, (0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.22, 0.32, 0.32, STEEL_DK)

    def outer_panel(fold_deg, base, *, alpha=None):
        c = rot_axis((1.15, 0.0, 0.0), (0, 0, 0), HINGE_AXIS, fold_deg)
        u = rot_axis((1, 0, 0), (0, 0, 0), HINGE_AXIS, fold_deg)
        v = rot_axis((0, 1, 0), (0, 0, 0), HINGE_AXIS, fold_deg)
        obox(s, c, u, v, HINGE_AXIS, 2.3, 0.20, 1.9, base, alpha=alpha)

    outer_panel(0, BRASS)                    # unfolded / flight — solid
    outer_panel(112, GHOST, alpha=0.30)      # folded / stowed — ghost, rotated about the slanted fold axis


HINGE_CAMERA = Camera(eye=Vec3(2.7, 2.9, 3.5), target=Vec3(0.4, 0.5, 0.0), fov=40)
HINGE_LEGEND = [
    (STEEL, "Fixed wing portion (204)"),
    (BRASS, "Folding wing portion (202)"),
    (STEEL_DK, "Interdigitated knuckles — comb/finger-joint teeth (Figs. 3/4), overlapping past center"),
    (AMBER, "Hinge pins: one long 600 + two short 601/602 (Fig. 6A) — the flight load path"),
    (GHOST, "Input fitting (610) / spline (620) / bushings (760–761); drive block (530) centered"),
    (GHOST, "Flight ↔ stowed fold about the slanted fold line (206), ghost = folded"),
]
HINGE_META = dict(
    patent="EP 3 608 220 A1", title="Folding Wing Hinge, Aircraft and Method Therefor",
    assignee="The Boeing Company", assignee_short="The Boeing Company", office="EPO",
    filed="2019-08-02 (priority 2018-08-06)", granted="2022-06-29",
    url="patents.google.com/patent/EP3608220A1",
    desc=("Plain hinge pins carry flight loads through interdigitated knuckles, but a separate "
          "spline-coupled input fitting isolates the fold-drive torque from those flight loads: "
          "crowned-tooth splines form miniature universal joints, so the fitting can twist to "
          "fold the wing without ever loading the same load path the hinge pins use in flight."),
)


MECHS = [
    (build_wing_pivot, WING_PIVOT_CAMERA, WING_PIVOT_LEGEND, WING_PIVOT_META),
    (build_thrust_nozzle, NOZZLE_CAMERA, NOZZLE_LEGEND, NOZZLE_META),
    (build_folding_hinge, HINGE_CAMERA, HINGE_LEGEND, HINGE_META),
]


# ======================================================================= #
#  page composition
# ======================================================================= #
def _t(box, text, style, **overrides):
    st = {**STYLES[style], **overrides} if overrides else STYLES[style]
    return {"type": "text", "box": [float(v) for v in box], "text": str(text), "style": st}


def _backdrop(page, box):
    x, y, w, h = box
    page.rect(box, fill=linear_gradient([(BG2, 0), (BG, 1)], angle=180), radius=16)
    for i in range(1, 6):
        gy = y + h * i / 6
        page.line([x + 16, gy], [x + w - 16, gy], stroke=GRIDLINE, stroke_style={"stroke_width": 1})
    for i in range(1, 6):
        gx = x + w * i / 6
        page.line([gx, y + 16], [gx, y + h - 16], stroke=GRIDLINE, stroke_style={"stroke_width": 1})


def cover(b):
    page = b.page("cover", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    page.rect([0, 0, W, H], fill=BG)
    _backdrop(page, [40, 40, W - 80, H - 80])
    notes = [
        _t([M + 24, 88, 900, 20], "PATENT OFFICES · WORLDWIDE PRIOR ART", "reg"),
        _t([M + 24, 116, 1150, 130], "Fighter-Jet Mechanisms, Reconstructed in 3D", "cover"),
        _t([M + 24, 250, 1000, 30], "Three patented articulated assemblies, rebuilt as real "
           "FrameForge Scene3D geometry", "cover", font_size=22, color="#A9B6CE",
           letter_spacing=-0.3),
        _t([M + 24, 296, 980, 120],
           "Sourced from the USPTO and the European Patent Office (Espacenet/Google Patents "
           "aggregation), chosen for genuinely complex, moving mechanical parts rather than "
           "flat structural drawings. Each page below cites its patent number, assignee, and "
           "filing/grant dates, and states plainly that this is a schematic topology "
           "reconstruction from the claims/description — not a to-scale CAD trace of the "
           "original drawings.", "coversub"),
    ]
    for i, (_builder, _cam, _legend, meta) in enumerate(MECHS, start=1):
        ry = 440 + i * 74
        notes.append(_t([M + 24, ry, 40, 16], f"{i:02d}", "idxno"))
        notes.append(_t([M + 74, ry - 2, 760, 20], meta["title"], "idx"))
        notes.append(_t([M + 74, ry + 20, 900, 34],
                        f"{meta['patent']} · {meta['assignee_short']} · {meta['office']}",
                        "idxk"))
    notes.append(_t([M + 24, H - 56, 1000, 16],
                    "Built with frameforge.sdk · Scene3D (mesh/tube/oriented-box primitives) "
                    "· one composed document", "foot"))
    page.add({"type": "group", "children": notes, "meta": {"role": "labels"}})


def mech_page(b, i, builder, camera, legend, meta):
    page = b.page(f"mechanism_{i:02d}", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    page.rect([0, 0, W, H], fill=BG)

    header = [
        _t([M, 34, 500, 16], f"PATENTED MECHANISM · {i:02d}/03", "reg"),
        _t([M, 54, 760, 60], meta["title"], "name"),
        _t([W - M - 260, 40, 260, 16], meta["patent"], "foot", align="right"),
    ]

    vp = [M, 130, 800, H - 130 - M]
    _backdrop(page, vp)
    scene = Scene3D()
    builder(scene)
    aspect = inset(vp, 36)[2] / inset(vp, 36)[3]
    cam = Camera(eye=camera.eye, target=camera.target, up=camera.up, fov=camera.fov,
                 aspect=aspect, near=camera.near, far=camera.far)
    page.add(scene.render(camera=cam, box=inset(vp, 36), fill=STEEL, stroke="none"))
    header.append(_t([vp[0] + 20, vp[1] + vp[3] - 26, vp[2] - 40, 16],
                     "Solid = primary position · translucent = the mechanism's other extreme",
                     "foot"))

    px = M + 800 + 28
    pw = W - px - M
    header.append(_t([px, 130, pw, 16], meta["office"], "klass"))
    header.append(_t([px, 150, pw, 20], meta["assignee_short"], "body", font_size=13.5,
                     color="#DCE4EE"))

    header.append(_t([px, 188, pw, 14], "COMPONENT LEGEND", "lbl"))
    ly0 = 210
    for k, (color, label) in enumerate(legend):
        yy = ly0 + k * 25
        page.rect([px, yy + 3, 13, 13], fill=color, radius=3)
        header.append(_t([px + 22, yy, pw - 22, 20], label, "legend"))
    ly_end = ly0 + len(legend) * 25 + 10

    header.append(_t([px, ly_end, pw, 14], "WHAT IT DOES", "lbl"))
    desc_y = ly_end + 20
    desc_h = 112
    header.append(_t([px, desc_y, pw, desc_h], meta["desc"], "body"))

    table_y = desc_y + desc_h + 16
    page.add(table([px, table_y, pw, 116],
                   [{"label": "Field", "width": "34%"}, {"label": "Value", "width": "66%"}],
                   [["Filed", meta["filed"]], ["Granted", meta["granted"]],
                    ["Assignee", meta["assignee_short"]], ["Source", meta["url"]]],
                   header=False, row_height=29, theme=TH))

    page.add({"type": "group", "children": header, "meta": {"role": "labels"}})


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Patented Fighter-Jet Mechanisms — Reconstructed in 3D",
                        profile="deck", lang="en")
    for name, style in STYLES.items():
        b.define_text_style(name, **style)
    cover(b)
    for i, (builder, cam, legend, meta) in enumerate(MECHS, start=1):
        mech_page(b, i, builder, cam, legend, meta)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in errors[:20]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:20]:
        print(f"  warn  [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "patent-fighter-jet-mechanisms-3d.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
