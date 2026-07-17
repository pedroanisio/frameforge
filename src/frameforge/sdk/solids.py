"""Solid generators + section cuts — the CAD operator layer over ``Scene3D``.

``Scene3D`` has always been able to hold these meshes (and already carried
``extrude``/``revolve`` as scene methods); this module makes the solid
vocabulary a discoverable, exported API and adds the genuinely new
generators — partial-angle revolve, sweep along a 3D path, loft between
profiles — plus the engineering **section cut**: plane ∩ scene → closed
loops, chained from the kernel's ``segment_plane_intersection`` and emitted
as a hatchable filled path.

Conventions: profiles are 2D rings ``[(x, y), ...]`` (counter-clockwise for
outward caps); paths and plane geometry are 3D. Every generator returns a
fresh ``Scene3D`` ready for ``render``/``multiview``; ``**style`` fields ride
on every face exactly as the manifold generators do.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

from frameforge.sdk.draw import Scene3D
from frameforge.sdk.geometry import Vec3, segment_plane_intersection

__all__ = ["extrude", "loft", "revolve", "section_loops", "section_object", "sweep"]

Pt2 = Sequence[float]
Pt3 = Sequence[float]


def extrude(profile: Sequence[Pt2], depth: float, **style: object) -> Scene3D:
    """Extrude a 2D profile along +z by ``depth`` (capped prism)."""
    return Scene3D().extrude([(float(x), float(y)) for x, y in profile], float(depth), **style)


def revolve(profile: Sequence[Pt2], *, segments: int = 24,
            angle: float = 360.0, **style: object) -> Scene3D:
    """Revolve an ``(r, y)`` profile about the y axis.

    ``angle`` < 360 produces a partial revolution with flat end caps (the
    profile itself, at the start and end angles).
    """
    prof = [(float(r), float(y)) for r, y in profile]
    if abs(angle - 360.0) < 1e-9:
        return Scene3D().revolve(prof, segments=segments, **style)
    sc = Scene3D()
    sweep_rad = math.radians(angle)
    rings: list[list[Vec3]] = []
    for i in range(segments + 1):
        a = sweep_rad * i / segments
        co, si = math.cos(a), math.sin(a)
        rings.append([Vec3(r * co, y, r * si) for r, y in prof])
    for i in range(segments):
        for j in range(len(prof) - 1):
            sc.faces.append(([rings[i][j], rings[i + 1][j],
                              rings[i + 1][j + 1], rings[i][j + 1]], dict(style)))
    sc.faces.append((list(rings[0]), dict(style)))
    sc.faces.append((list(reversed(rings[-1])), dict(style)))
    return sc


def _frame_at(t: "Vec3") -> tuple["Vec3", "Vec3"]:
    """A stable perpendicular basis for tangent ``t`` (unit)."""
    up = Vec3(0.0, 0.0, 1.0) if abs(t.z) < 0.9 else Vec3(0.0, 1.0, 0.0)
    # e1 = up × t, e2 = t × e1
    e1 = Vec3(up.y * t.z - up.z * t.y, up.z * t.x - up.x * t.z, up.x * t.y - up.y * t.x)
    n1 = math.sqrt(e1.x**2 + e1.y**2 + e1.z**2) or 1.0
    e1 = Vec3(e1.x / n1, e1.y / n1, e1.z / n1)
    e2 = Vec3(t.y * e1.z - t.z * e1.y, t.z * e1.x - t.x * e1.z, t.x * e1.y - t.y * e1.x)
    return e1, e2


def sweep(profile: Sequence[Pt2], path: Sequence[Pt3], *,
          caps: bool = True, **style: object) -> Scene3D:
    """Sweep a 2D profile along a 3D polyline path.

    Each path vertex gets a profile ring oriented by the local tangent
    (averaged at interior vertices — a simple miter, adequate for the gentle
    paths engineering sweeps use). ``caps=False`` leaves the ends open.
    """
    pts = [Vec3(float(x), float(y), float(z)) for x, y, z in path]
    if len(pts) < 2:
        raise ValueError("sweep needs a path with at least two points")
    prof = [(float(x), float(y)) for x, y in profile]
    tangents: list[Vec3] = []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        d = Vec3(b.x - a.x, b.y - a.y, b.z - a.z)
        n = math.sqrt(d.x**2 + d.y**2 + d.z**2) or 1.0
        tangents.append(Vec3(d.x / n, d.y / n, d.z / n))
    rings: list[list[Vec3]] = []
    for p, t in zip(pts, tangents):
        e1, e2 = _frame_at(t)
        rings.append([Vec3(p.x + u * e1.x + v * e2.x,
                           p.y + u * e1.y + v * e2.y,
                           p.z + u * e1.z + v * e2.z) for u, v in prof])
    sc = Scene3D()
    n = len(prof)
    for i in range(len(rings) - 1):
        for j in range(n):
            sc.faces.append(([rings[i][j], rings[i][(j + 1) % n],
                              rings[i + 1][(j + 1) % n], rings[i + 1][j]], dict(style)))
    if caps:
        sc.faces.append((list(reversed(rings[0])), dict(style)))
        sc.faces.append((list(rings[-1]), dict(style)))
    return sc


def loft(profiles: Sequence[Sequence[Pt2]], *, heights: Sequence[float] | None = None,
         caps: bool = True, **style: object) -> Scene3D:
    """Loft between 2D profiles stacked along +z at ``heights``.

    All profiles must share a vertex count (ring correspondence is by index);
    ``heights`` defaults to 0, 1, 2, …
    """
    if len(profiles) < 2:
        raise ValueError("loft needs at least two profiles")
    counts = {len(p) for p in profiles}
    if len(counts) != 1:
        raise ValueError(f"loft profiles must share a vertex count, got {sorted(counts)}")
    hs = list(heights) if heights is not None else [float(i) for i in range(len(profiles))]
    if len(hs) != len(profiles):
        raise ValueError("heights must match the number of profiles")
    rings = [[Vec3(float(x), float(y), float(h)) for x, y in prof]
             for prof, h in zip(profiles, hs)]
    sc = Scene3D()
    n = len(rings[0])
    for i in range(len(rings) - 1):
        for j in range(n):
            sc.faces.append(([rings[i][j], rings[i][(j + 1) % n],
                              rings[i + 1][(j + 1) % n], rings[i + 1][j]], dict(style)))
    if caps:
        sc.faces.append((list(rings[0]), dict(style)))
        sc.faces.append((list(reversed(rings[-1])), dict(style)))
    return sc


# --------------------------------------------------------------------------- #
# Section cuts
# --------------------------------------------------------------------------- #
def _plane_basis(normal: "Vec3") -> tuple["Vec3", "Vec3"]:
    n = math.sqrt(normal.x**2 + normal.y**2 + normal.z**2) or 1.0
    nn = Vec3(normal.x / n, normal.y / n, normal.z / n)
    return _frame_at(nn)


def section_loops(scene: Scene3D, *, plane_point: Pt3, plane_normal: Pt3,
                  tol: float = 1e-6) -> list[list[tuple[float, float]]]:
    """Cut a scene with a plane and chain the crossings into closed 2D loops.

    Each face contributes the segment where its edges cross the plane; the
    segments are chained by endpoint proximity. Coordinates come back in the
    plane's own (u, v) basis. Open chains (from unclosed meshes) are dropped —
    a section is by definition a closed cut.
    """
    pp = Vec3(*[float(v) for v in plane_point])
    pn = Vec3(*[float(v) for v in plane_normal])
    e1, e2 = _plane_basis(pn)

    def to2d(p: "Vec3") -> tuple[float, float]:
        d = Vec3(p.x - pp.x, p.y - pp.y, p.z - pp.z)
        return (d.x * e1.x + d.y * e1.y + d.z * e1.z,
                d.x * e2.x + d.y * e2.y + d.z * e2.z)

    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for face, _style in scene.faces:
        hits: list[tuple[float, float]] = []
        for a, b in zip(face, face[1:] + face[:1]):
            hit = segment_plane_intersection(a, b, pp, pn)
            if hit is not None:
                q = to2d(hit if isinstance(hit, Vec3) else Vec3(*hit))
                if not any(abs(q[0] - h[0]) < tol and abs(q[1] - h[1]) < tol for h in hits):
                    hits.append(q)
        if len(hits) >= 2:
            segments.append((hits[0], hits[1]))

    # chain segments into loops by endpoint proximity
    join_tol = 1e-4
    loops: list[list[tuple[float, float]]] = []
    remaining = list(segments)
    while remaining:
        a, b = remaining.pop()
        chain = [a, b]
        grew = True
        while grew:
            grew = False
            for k, (p, q) in enumerate(remaining):
                if math.hypot(chain[-1][0] - p[0], chain[-1][1] - p[1]) < join_tol:
                    chain.append(q)
                elif math.hypot(chain[-1][0] - q[0], chain[-1][1] - q[1]) < join_tol:
                    chain.append(p)
                else:
                    continue
                remaining.pop(k)
                grew = True
                break
        if math.hypot(chain[0][0] - chain[-1][0], chain[0][1] - chain[-1][1]) < join_tol \
                and len(chain) > 3:
            loops.append(chain[:-1])
    return loops


def section_object(scene: Scene3D, *, plane_point: Pt3, plane_normal: Pt3,
                   frame: Sequence[float], fill: str | dict[str, Any] | None = None,
                   hatch_color: str = "#555555", hatch_scale: float = 7.0,
                   stroke: str = "#222222", stroke_width: float = 1.5,
                   **fields: Any) -> dict[str, Any]:
    """The section cut as one FrameForge ``path`` object, fitted into ``frame``.

    Loops become sub-rings of a single even-odd path (holes render as holes),
    scaled uniformly to fit the ``[x, y, w, h]`` frame; the fill defaults to
    the drafting convention — a hatch in ``hatch_color``.
    """
    loops = section_loops(scene, plane_point=plane_point, plane_normal=plane_normal)
    if not loops:
        raise ValueError("section plane does not cut the scene")
    xs = [x for lp in loops for x, _ in lp]
    ys = [y for lp in loops for _, y in lp]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    fx, fy, fw, fh = (float(v) for v in frame)
    span_x, span_y = (x1 - x0) or 1.0, (y1 - y0) or 1.0
    s = min(fw / span_x, fh / span_y)
    ox = fx + (fw - span_x * s) / 2.0
    oy = fy + (fh - span_y * s) / 2.0
    d_parts: list[str] = []
    for lp in loops:
        pts = [(ox + (x - x0) * s, oy + (y - y0) * s) for x, y in lp]
        d_parts.append("M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z")
    from frameforge.sdk.paint import hatch as _hatch
    return {
        "type": "path",
        "d": " ".join(d_parts),
        "fill": fill if fill is not None else _hatch(fg=hatch_color, scale=hatch_scale, angle=45),
        "style": {"fill_rule": "evenodd"},
        "stroke": stroke,
        "stroke_style": {"stroke_width": stroke_width, "stroke_linejoin": "round"},
        **fields,
    }
