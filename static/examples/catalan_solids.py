#!/usr/bin/env python3
"""The thirteen Catalan solids, derived — a FrameForge poster at diverse angles.

Nothing here is hand-typed geometry. Each Catalan solid is DERIVED:

    1. Its dual Archimedean solid is generated from the canonical coordinate
       orbits (permutation + sign-parity rules over {1, √2, φ, tribonacci t,
       snub-dodecahedral ξ}, with t³ = t² + t + 1 and ξ³ = 2ξ + φ solved
       numerically at build time).
    2. Faces are recovered by supporting-plane enumeration over the vertex
       hull (SVD-refit planes, tolerance-scaled support tests).
    3. The Catalan solid is the polar reciprocal about the Archimedean
       midsphere (edge-tangent sphere, normalized to radius 1): each face
       plane {x·n̂ = d} reciprocates to the vertex n̂/d; each vertex to a face.

Verification gates (PALS): every Archimedean must have equal edge lengths and
a true midsphere (deviation < 1e-6 relative), and every solid must hit the
known (V, E, F) table exactly — the build RAISES on any mismatch, so a wrong
remembered coordinate orbit cannot render. References: coordinate orbits per
the standard constructions (Williams, *The Geometrical Foundation of Natural
Structure*, 1979; en.wikipedia.org per-solid pages); duality by polar
reciprocation (Cundy & Rollett, *Mathematical Models*, 1961, §3.2).

Rendering is the engine's own ``Scene3D.mesh(...).render(shading="phong")``;
each solid gets its own camera on a golden-angle azimuth spiral with varied
elevation — the "diverse angles" are printed in each cell.

    uv run python static/examples/catalan_solids.py
    uv run python tooling/frameforge_render.py out/catalan_solids/catalan_solids.fg.yaml --to png --out out/catalan_solids

AI-generated (Claude Opus 4.8 via Claude Code).
"""
from __future__ import annotations

import colorsys
import math
import os
import sys
from itertools import combinations, permutations

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402
from frameforge.sdk.draw import Camera, Scene3D, Vec3  # noqa: E402

OUT_DIR = os.path.join(ROOT, "out", "catalan_solids")

PHI = (1 + math.sqrt(5)) / 2
SQ2 = math.sqrt(2)
TRIB = float(np.real(sorted(np.roots([1, -1, -1, -1]), key=lambda r: -np.real(r))[0]))
XI = float(np.real(sorted(np.roots([1, 0, -2, -PHI]), key=lambda r: -np.real(r))[0]))


# --------------------------------------------------------------------------- #
#  Derivation kernel: orbits -> hull -> midsphere -> polar reciprocal          #
# --------------------------------------------------------------------------- #
def _perm_parity(p) -> int:
    return sum(1 for i in range(3) for j in range(i + 1, 3) if p[i] > p[j]) % 2


def orbit(base, perm_parity=None, sign_parity=None):
    """All permutations/sign combinations of ``base`` under the parity rules."""
    out = set()
    for p in permutations(range(3)):
        if perm_parity is not None and _perm_parity(p) != perm_parity:
            continue
        v = [base[i] for i in p]
        for s in range(8):
            signs = [(-1) ** ((s >> k) & 1) for k in range(3)]
            if sign_parity is not None and sum(1 for x in signs if x < 0) % 2 != sign_parity:
                continue
            out.add(tuple(round(signs[k] * v[k], 9) for k in range(3)))
    return [list(v) for v in sorted(out)]


def hull(V, tol=1e-6):
    """Convex-hull faces of ``V`` (every vertex extreme, origin inside):
    (unit_normal, offset, CCW-from-outside vertex indices)."""
    V = np.asarray(V, float)
    idx = np.array(list(combinations(range(len(V)), 3)))
    a, b, c = V[idx[:, 0]], V[idx[:, 1]], V[idx[:, 2]]
    nrm = np.cross(b - a, c - a)
    ln = np.linalg.norm(nrm, axis=1)
    keep = ln > 1e-9
    nrm = nrm[keep] / ln[keep, None]
    d = np.einsum("ij,ij->i", nrm, a[keep])
    nrm[d < 0] *= -1
    d = np.abs(d)
    scale = float(np.abs(V).max())
    loose = 1e-5 * scale
    _, rep = np.unique(np.round(np.column_stack([nrm, d]), 6), axis=0, return_index=True)
    faces, seen = [], set()
    for ri in rep:
        nv, dd = nrm[ri], d[ri]
        dots = V @ nv
        if dots.max() > dd + loose:
            continue
        on = np.where(dots >= dd - loose)[0]
        if len(on) < 3:
            continue
        # refit the plane from the full on-set (SVD normal through centroid)
        ctr = V[on].mean(axis=0)
        _, _, vt = np.linalg.svd(V[on] - ctr)
        nv = vt[-1] if np.dot(vt[-1], ctr) >= 0 else -vt[-1]
        dd = float(np.dot(nv, ctr))
        dots = V @ nv
        if dots.max() > dd + tol * scale:
            continue
        on = np.where(dots >= dd - tol * scale)[0]
        if len(on) < 3:
            continue
        fkey = tuple(sorted(on.tolist()))
        if fkey in seen:
            continue
        seen.add(fkey)
        ctr = V[on].mean(axis=0)
        ref = V[on[0]] - ctr
        ref /= np.linalg.norm(ref)
        up = np.cross(nv, ref)
        ang = np.arctan2((V[on] - ctr) @ up, (V[on] - ctr) @ ref)
        faces.append((nv, dd, on[np.argsort(ang)].tolist()))
    return faces


def edges_of(faces):
    es = set()
    for f in faces:
        ring = f[2] if isinstance(f, tuple) else f
        for i in range(len(ring)):
            es.add(tuple(sorted((ring[i], ring[(i + 1) % len(ring)]))))
    return sorted(es)


def edge_uniformity(V, faces):
    """(edge count, relative edge-length spread, midradius, relative spread)."""
    V = np.asarray(V, float)
    es = edges_of(faces)
    L, mid = [], []
    for i, j in es:
        p, q = V[i], V[j]
        L.append(float(np.linalg.norm(q - p)))
        t = -np.dot(p, q - p) / np.dot(q - p, q - p)
        mid.append(float(np.linalg.norm(p + min(1.0, max(0.0, t)) * (q - p))))
    return (len(es), (max(L) - min(L)) / max(L),
            (min(mid) + max(mid)) / 2, (max(mid) - min(mid)) / max(mid))


def polar_dual(V, faces):
    """Polar reciprocal about the unit sphere (midradius must be 1)."""
    V = np.asarray(V, float)
    DV = np.array([n / d for n, d, _ in faces])
    incident: dict[int, list[int]] = {}
    for fi, (_, _, ring) in enumerate(faces):
        for vi in ring:
            incident.setdefault(vi, []).append(fi)
    dfaces = []
    for vi in range(len(V)):
        fs = np.array(incident[vi])
        axis = V[vi] / np.linalg.norm(V[vi])
        ctr = DV[fs].mean(axis=0)
        ref = DV[fs[0]] - ctr
        ref -= axis * np.dot(ref, axis)
        ref /= np.linalg.norm(ref)
        up = np.cross(axis, ref)
        rel = DV[fs] - ctr
        dfaces.append(fs[np.argsort(np.arctan2(rel @ up, rel @ ref))].tolist())
    return DV, dfaces


# --------------------------------------------------------------------------- #
#  The thirteen, via their Archimedean duals                                   #
#  (base orbit, perm parity, sign parity) — parity None = unrestricted;        #
#  snubs carry both chirality candidates and the gate picks the valid one.     #
# --------------------------------------------------------------------------- #
_SNUB_A = XI - 1 / XI
_SNUB_B = XI * PHI + PHI ** 2 + PHI / XI
CATALOG = [
    # catalan name, face shape, archimedean name, orbits, archimedean (V, E, F)
    ("Triakis tetrahedron", "isosceles triangles", "truncated tetrahedron",
     [((1, 1, 3), None, 0)], (12, 18, 8)),
    ("Rhombic dodecahedron", "rhombi", "cuboctahedron",
     [((1, 1, 0), None, None)], (12, 24, 14)),
    ("Triakis octahedron", "isosceles triangles", "truncated cube",
     [((SQ2 - 1, 1, 1), None, None)], (24, 36, 14)),
    ("Tetrakis hexahedron", "isosceles triangles", "truncated octahedron",
     [((0, 1, 2), None, None)], (24, 36, 14)),
    ("Deltoidal icositetrahedron", "kites", "rhombicuboctahedron",
     [((1, 1, 1 + SQ2), None, None)], (24, 48, 26)),
    ("Disdyakis dodecahedron", "scalene triangles", "truncated cuboctahedron",
     [((1, 1 + SQ2, 1 + 2 * SQ2), None, None)], (48, 72, 26)),
    ("Pentagonal icositetrahedron", "chiral pentagons", "snub cube",
     [((1, 1 / TRIB, TRIB), 0, 1), ((1, 1 / TRIB, TRIB), 1, 0)], (24, 60, 38)),
    ("Rhombic triacontahedron", "rhombi", "icosidodecahedron",
     [((0, 0, PHI), 0, None), ((0.5, PHI / 2, PHI ** 2 / 2), 0, None)], (30, 60, 32)),
    ("Triakis icosahedron", "isosceles triangles", "truncated dodecahedron",
     [((0, 1 / PHI, 2 + PHI), 0, None), ((1 / PHI, PHI, 2 * PHI), 0, None),
      ((PHI, 2, PHI ** 2), 0, None)], (60, 90, 32)),
    ("Pentakis dodecahedron", "isosceles triangles", "truncated icosahedron",
     [((0, 1, 3 * PHI), 0, None), ((1, 2 + PHI, 2 * PHI), 0, None),
      ((PHI, 2, 2 * PHI + 1), 0, None)], (60, 90, 32)),
    ("Deltoidal hexecontahedron", "kites", "rhombicosidodecahedron",
     [((1, 1, PHI ** 3), 0, None), ((PHI ** 2, PHI, 2 * PHI), 0, None),
      ((2 + PHI, 0, PHI ** 2), 0, None)], (60, 120, 62)),
    ("Disdyakis triacontahedron", "scalene triangles", "truncated icosidodecahedron",
     [((1 / PHI, 1 / PHI, 3 + PHI), 0, None), ((2 / PHI, PHI, 1 + 2 * PHI), 0, None),
      ((1 / PHI, PHI ** 2, 3 * PHI - 1), 0, None), ((2 * PHI - 1, 2, 2 + PHI), 0, None),
      ((PHI, 3, 2 * PHI), 0, None)], (120, 180, 62)),
    ("Pentagonal hexecontahedron", "chiral pentagons", "snub dodecahedron",
     [((2 * _SNUB_A, 2, 2 * _SNUB_B), 0, 0),
      ((_SNUB_A + _SNUB_B / PHI + PHI, -_SNUB_A * PHI + _SNUB_B + 1 / PHI,
        _SNUB_A / PHI + _SNUB_B * PHI - 1), 0, 0),
      ((_SNUB_A + _SNUB_B / PHI - PHI, _SNUB_A * PHI - _SNUB_B + 1 / PHI,
        _SNUB_A / PHI + _SNUB_B * PHI + 1), 0, 0),
      ((-_SNUB_A / PHI + _SNUB_B * PHI + 1, -_SNUB_A + _SNUB_B / PHI - PHI,
        _SNUB_A * PHI + _SNUB_B - 1 / PHI), 0, 0),
      ((-_SNUB_A / PHI + _SNUB_B * PHI - 1, _SNUB_A - _SNUB_B / PHI - PHI,
        _SNUB_A * PHI + _SNUB_B + 1 / PHI), 0, 0)], (60, 150, 92)),
]


def derive(orbits, expect, tol=1e-6):
    """Archimedean from orbits -> gated -> Catalan dual, gated. Raises on FAIL."""
    seen, V = set(), []
    for base, pp, sp in orbits:
        for v in orbit(base, pp, sp):
            k = tuple(round(x, 8) for x in v)
            if k not in seen:
                seen.add(k)
                V.append(v)
    V = np.asarray(V, float)
    faces = hull(V)
    ne, edev, mid, mdev = edge_uniformity(V, faces)
    got = (len(V), ne, len(faces))
    if got != expect:
        raise AssertionError(f"Archimedean (V,E,F)={got}, expected {expect}")
    if edev > tol or mdev > tol:
        raise AssertionError(f"not uniform: edge_dev={edev:.2e} mid_dev={mdev:.2e}")
    Vm = V / mid                                  # midsphere -> unit sphere
    DV, dfaces = polar_dual(Vm, hull(Vm))
    exp_c = (expect[2], expect[1], expect[0])
    got_c = (len(DV), len(edges_of(dfaces)), len(dfaces))
    if got_c != exp_c:
        raise AssertionError(f"Catalan (V,E,F)={got_c}, expected {exp_c}")
    return DV, dfaces, got_c


# --------------------------------------------------------------------------- #
#  Poster                                                                      #
# --------------------------------------------------------------------------- #
W, H = 1440, 1920
BG, PANEL, INKY, MUTED = "#0e1116", "#141922", "#dfe4ec", "#8b94a3"
ELEVATIONS = [18, 34, 8, 46, 26, 55, 14, 38, 22, 50, 30, 12, 42]


def accent(i: int) -> tuple[str, str]:
    """(fill, stroke) accent pair for solid i — muted hue wheel on dark."""
    h = (i / 13.0 + 0.03) % 1.0
    fill = colorsys.hls_to_rgb(h, 0.62, 0.52)
    edge = colorsys.hls_to_rgb(h, 0.16, 0.45)
    return ("#%02x%02x%02x" % tuple(round(c * 255) for c in fill),
            "#%02x%02x%02x" % tuple(round(c * 255) for c in edge))


def build():
    solids = []
    for name, shape, arch, orbits, expect in CATALOG:
        if "chiral" in shape and len(orbits) == 2 and orbits[0][0] == orbits[1][0]:
            pass  # snub cube: both parity halves belong to ONE chirality candidate
        DV, dfaces, counts = derive(orbits, expect)
        DV = DV / np.linalg.norm(DV, axis=1).max()      # unit circumradius
        solids.append((name, shape, arch, DV, dfaces, counts))
        print(f"[derive] {name:30s} V={counts[0]:3d} E={counts[1]:3d} F={counts[2]:3d} OK")

    b = DocumentBuilder(title="The Catalan Solids — thirteen duals, derived")
    page = b.page("poster", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute",
                  notes="All geometry derived at build time by polar reciprocation "
                        "of the Archimedean solids about their midsphere; V/E/F "
                        "gates raise on mismatch. Cameras on a golden-angle spiral.")

    bg = page.layer("00_bg")
    bg.rect([0, 0, W, H], fill=BG, decorative=True)

    hd = page.layer("01_header")
    hd.text([66, 58, W - 132, 64], "THE CATALAN SOLIDS",
            style={"font_family": "Inter", "font_size": 52, "font_weight": 200,
                   "color": INKY, "letter_spacing": 10})
    hd.text([66, 128, W - 132, 30],
            "the thirteen duals of the Archimedean solids · derived by polar "
            "reciprocation about the midsphere · shown at thirteen distinct viewing angles",
            style={"font_family": "Inter", "font_size": 16.5, "font_weight": 400,
                   "color": MUTED})
    hd.line([66, 182], [W - 66, 182], stroke="#2a3140",
            style={"stroke_width": 1})

    grid_top, grid_bot, margin = 216, 1876, 66
    cols, rows = 4, 4
    cw = (W - 2 * margin) / cols
    ch = (grid_bot - grid_top) / rows

    cells = page.layer("10_cells")
    scenes = page.layer("20_solids")
    labels = page.layer("30_labels")

    for i, (name, shape, arch, DV, dfaces, counts) in enumerate(solids):
        r, c = divmod(i, cols)
        x, y = margin + c * cw, grid_top + r * ch
        cells.rect([x + 8, y + 8, cw - 16, ch - 16], fill=PANEL, radius=10,
                   decorative=True)

        az = math.radians((i * 137.508) % 360)
        el = math.radians(ELEVATIONS[i])
        eye = Vec3(3.1 * math.cos(el) * math.cos(az), 3.1 * math.sin(el),
                   3.1 * math.cos(el) * math.sin(az))
        fill, edge = accent(i)
        grp = (Scene3D()
               .mesh(DV.tolist(), dfaces)
               .render(camera=Camera(eye=eye, target=Vec3(0, 0, 0), fov=38),
                       box=[x + 34, y + 26, cw - 68, cw - 68],
                       fill=fill, stroke=edge, shading="phong",
                       specular=0.28, shininess=14.0,
                       cull_backfaces=True, id=f"solid_{i}"))
        scenes.add(grp)

        ty = y + ch - 108
        labels.text([x + 22, ty - 26, 40, 22], f"{i + 1:02d}",
                    style={"font_family": "Inter", "font_size": 15,
                           "font_weight": 700, "color": fill})
        labels.text([x + 22, ty, cw - 44, 24], name,
                    style={"font_family": "Inter", "font_size": 17.5,
                           "font_weight": 600, "color": INKY})
        labels.text([x + 22, ty + 26, cw - 44, 20], f"dual of the {arch}",
                    style={"font_family": "Inter", "font_size": 13,
                           "font_weight": 400, "color": MUTED, "font_style": "italic"})
        labels.text([x + 22, ty + 48, cw - 44, 20],
                    f"{counts[2]} {shape} · E {counts[1]} · V {counts[0]}",
                    style={"font_family": "Inter", "font_size": 13,
                           "font_weight": 400, "color": MUTED})
        labels.text([x + 22, ty + 70, cw - 44, 20],
                    f"view az {round(math.degrees(az))}° · el {ELEVATIONS[i]}°",
                    style={"font_family": "Inter", "font_size": 12,
                           "font_weight": 400, "color": "#5b6472"})

    # colophon panel spanning the last three cells of the bottom row
    cx = margin + 1 * cw
    cy = grid_top + 3 * ch
    cells.rect([cx + 8, cy + 8, 3 * cw - 16, ch - 16], fill="#10151d", radius=10,
               decorative=True, stroke="#232b38", style={"stroke_width": 1})
    labels.text([cx + 40, cy + 44, 3 * cw - 80, 26], "DERIVED, NOT DRAWN",
                style={"font_family": "Inter", "font_size": 19, "font_weight": 600,
                       "color": INKY, "letter_spacing": 3})
    colophon = (
        "Every solid on this sheet is computed at build time. The thirteen Archimedean "
        "solids are generated from their canonical coordinate orbits — permutation and "
        "sign-parity rules over {1, √2, φ, t, ξ}, where t³ = t² + t + 1 (tribonacci) and "
        "ξ³ = 2ξ + φ — and their faces recovered by supporting-plane enumeration. Each "
        "Catalan solid is the polar reciprocal about its dual's midsphere: the face plane "
        "x·n̂ = d becomes the vertex n̂⁄d, and each vertex becomes a face. Verification "
        "gates require equal Archimedean edge lengths, a true midsphere (< 1e-6 relative "
        "deviation), and an exact match of the known (V, E, F) census for all 26 solids — "
        "the build fails otherwise. Two of the thirteen (07, 13) are chiral: one "
        "enantiomorph of each is shown. Shading: Scene3D Blinn-Phong; one camera per "
        "solid on a golden-angle azimuth spiral (Δaz = 137.5°) with varied elevation.")
    labels.text([cx + 40, cy + 88, 3 * cw - 80, ch - 140], colophon,
                style={"font_family": "Inter", "font_size": 13.5, "font_weight": 400,
                       "color": MUTED, "line_height": 1.55, "wrap": True})

    ft = page.layer("40_footer")
    ft.text([66, H - 34, W - 132, 20],
            "FrameForge · Scene3D phong · geometry gates: 26/26 PASS · "
            "refs: Cundy & Rollett 1961 §3.2; Williams 1979",
            style={"font_family": "Inter", "font_size": 11.5, "color": "#4d5563"})

    doc = b.build()
    os.makedirs(OUT_DIR, exist_ok=True)
    import yaml
    data = doc.model_dump(mode="json", by_alias=True, exclude_none=True)
    yaml_path = os.path.join(OUT_DIR, "catalan_solids.fg.yaml")
    with open(yaml_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=None, width=1000)
    svg = render_page_svgs(doc)[0]
    svg_path = os.path.join(OUT_DIR, "catalan_solids.svg")
    with open(svg_path, "w", encoding="utf-8") as fh:
        fh.write(svg)

    print(f"[write] {yaml_path}")
    print(f"[write] {svg_path}  ({len(svg) // 1024} KiB)")
    ok = len(solids) == 13 and svg.startswith("<svg")
    print(f"\nVERDICT: {'all 13 Catalan solids derived, gated, and rendered' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(build())
