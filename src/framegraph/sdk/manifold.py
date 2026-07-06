"""Parametric manifolds and wave surfaces.

Each builder returns a :class:`~framegraph.sdk.Scene3D` whose ``parametric_surface``
mesh is ready to ``.render(box=..., camera=...)`` through a perspective
:class:`~framegraph.sdk.Camera`. Includes the classic embedded surfaces (sphere,
torus, Möbius band, Klein bottle, saddle) plus :func:`wave` heightfields — the
"waves" in fields/waves/lattices/manifolds.
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

from framegraph.sdk.draw import Scene3D
from framegraph.sdk.geometry import Vec3, _v3


def parametric(
    fn: Callable[[float, float], Sequence[float]],
    *,
    u: tuple[float, float],
    v: tuple[float, float],
    steps_u: int = 28,
    steps_v: int = 28,
    **style: object,
) -> Scene3D:
    """A thin alias for :meth:`Scene3D.parametric_surface` returning a fresh scene."""
    return Scene3D().parametric_surface(fn, u=u, v=v, steps_u=steps_u, steps_v=steps_v, **style)


# --------------------------------------------------------------------------- #
#  B5 — bicubic Bézier surface patch (Harrington Ch11). 16 control points, the  #
#  Bernstein tensor product; interpolates the four corner controls exactly.     #
# --------------------------------------------------------------------------- #
def _bernstein3(t: float) -> tuple[float, float, float, float]:
    w = 1.0 - t
    return (w * w * w, 3 * t * w * w, 3 * t * t * w, t * t * t)


def _patch_control(control: Sequence[Sequence[Vec3 | Sequence[float]]]) -> list[list[Vec3]]:
    rows = [list(r) for r in control]
    if len(rows) != 4 or any(len(r) != 4 for r in rows):
        raise ValueError("bezier_patch needs a 4×4 grid of control points")
    return [[_v3(p) for p in row] for row in rows]


def _eval_patch(P: list[list[Vec3]], u: float, v: float) -> tuple[float, float, float]:
    bu, bv = _bernstein3(u), _bernstein3(v)
    x = y = z = 0.0
    for i in range(4):
        for j in range(4):
            w = bu[i] * bv[j]
            p = P[i][j]
            x += w * p.x
            y += w * p.y
            z += w * p.z
    return (x, y, z)


def bezier_patch_point(
    control: Sequence[Sequence[Vec3 | Sequence[float]]], u: float, v: float,
) -> Vec3:
    """Evaluate a bicubic Bézier surface patch at ``(u, v)`` in [0,1]² (B5). The
    ``control`` net is a 4×4 grid; the Bernstein tensor product interpolates the
    four corners exactly (``(0,0)``→P₀₀, ``(1,1)``→P₃₃)."""
    return Vec3(*_eval_patch(_patch_control(control), u, v))


def bezier_patch(
    control: Sequence[Sequence[Vec3 | Sequence[float]]], *,
    steps_u: int = 20, steps_v: int = 20, **style: object,
) -> Scene3D:
    """A bicubic Bézier surface patch (B5, Harrington Ch11) tessellated into a
    :class:`Scene3D` — ``steps_u × steps_v`` quads over a 4×4 control net. Renders
    like any other manifold: ``.render(box=…, camera=…, shading="phong")``."""
    P = _patch_control(control)
    return parametric(lambda u, v: _eval_patch(P, u, v),
                      u=(0.0, 1.0), v=(0.0, 1.0), steps_u=steps_u, steps_v=steps_v, **style)


# --------------------------------------------------------------------------- #
#  B5 residual — uniform bicubic B-spline surface patch (Harrington Ch11). An   #
#  m×n control net (m,n ≥ 4); the uniform (non-clamped) cubic basis, so the     #
#  surface lies inside the control hull rather than interpolating the corners.  #
# --------------------------------------------------------------------------- #
def _bspline3(t: float) -> tuple[float, float, float, float]:
    """The four uniform cubic B-spline basis weights at local parameter ``t`` in
    [0,1]; they sum to 1 (partition of unity)."""
    t2 = t * t
    t3 = t2 * t
    return ((1.0 - 3.0 * t + 3.0 * t2 - t3) / 6.0,
            (4.0 - 6.0 * t2 + 3.0 * t3) / 6.0,
            (1.0 + 3.0 * t + 3.0 * t2 - 3.0 * t3) / 6.0,
            t3 / 6.0)


def _bspline_span(g: float, spans: int) -> tuple[int, float]:
    """Map a global coordinate ``g`` in [0, spans] to ``(span_index, local_t)``,
    clamping the span into ``[0, spans-1]`` so ``g == spans`` lands at the last
    span's ``t = 1``."""
    span = int(math.floor(g))
    span = max(0, min(span, spans - 1))
    return span, g - span


def _bspline_control(control: Sequence[Sequence[Vec3 | Sequence[float]]]) -> list[list[Vec3]]:
    rows = [list(r) for r in control]
    if len(rows) < 4:
        raise ValueError("bspline_patch needs a control net with ≥4 rows")
    width = len(rows[0])
    if width < 4:
        raise ValueError("bspline_patch needs a control net with ≥4 columns")
    if any(len(r) != width for r in rows):
        raise ValueError("bspline_patch needs a rectangular (non-ragged) control net")
    return [[_v3(p) for p in row] for row in rows]


def _eval_bspline(P: list[list[Vec3]], u: float, v: float) -> tuple[float, float, float]:
    m, n = len(P), len(P[0])
    su, tu = _bspline_span(u * (m - 3), m - 3)
    sv, tv = _bspline_span(v * (n - 3), n - 3)
    bu, bv = _bspline3(tu), _bspline3(tv)
    x = y = z = 0.0
    for a in range(4):
        for b in range(4):
            w = bu[a] * bv[b]
            p = P[su + a][sv + b]
            x += w * p.x
            y += w * p.y
            z += w * p.z
    return (x, y, z)


def bspline_patch_point(
    control: Sequence[Sequence[Vec3 | Sequence[float]]], u: float, v: float,
) -> Vec3:
    """Evaluate a uniform bicubic B-spline surface at ``(u, v)`` in [0,1]² (B5
    residual). ``control`` is an ``m×n`` grid (``m, n ≥ 4``); the surface lies
    inside the control net's convex hull and, being uniform, does **not**
    interpolate the corner controls (contrast :func:`bezier_patch_point`)."""
    return Vec3(*_eval_bspline(_bspline_control(control), u, v))


def bspline_patch(
    control: Sequence[Sequence[Vec3 | Sequence[float]]], *,
    steps_u: int = 24, steps_v: int = 24, **style: object,
) -> Scene3D:
    """A uniform bicubic B-spline surface patch (B5 residual, Harrington Ch11)
    tessellated into a :class:`Scene3D` — ``steps_u × steps_v`` quads over an
    ``m×n`` control net (``m, n ≥ 4``). Renders like any other manifold:
    ``.render(box=…, camera=…, shading="phong")``."""
    P = _bspline_control(control)
    return parametric(lambda u, v: _eval_bspline(P, u, v),
                      u=(0.0, 1.0), v=(0.0, 1.0), steps_u=steps_u, steps_v=steps_v, **style)


def sphere(radius: float = 1.0, *, steps_u: int = 28, steps_v: int = 18, **style: object) -> Scene3D:
    def f(u: float, v: float) -> tuple[float, float, float]:
        return (radius * math.sin(v) * math.cos(u),
                radius * math.cos(v),
                radius * math.sin(v) * math.sin(u))
    return parametric(f, u=(0, 2 * math.pi), v=(0, math.pi),
                      steps_u=steps_u, steps_v=steps_v, **style)


def torus(major: float = 1.0, minor: float = 0.38, *,
          steps_u: int = 36, steps_v: int = 20, **style: object) -> Scene3D:
    def f(u: float, v: float) -> tuple[float, float, float]:
        return ((major + minor * math.cos(v)) * math.cos(u),
                minor * math.sin(v),
                (major + minor * math.cos(v)) * math.sin(u))
    return parametric(f, u=(0, 2 * math.pi), v=(0, 2 * math.pi),
                      steps_u=steps_u, steps_v=steps_v, **style)


def mobius(radius: float = 1.0, width: float = 0.4, *,
           steps_u: int = 48, steps_v: int = 6, **style: object) -> Scene3D:
    def f(u: float, v: float) -> tuple[float, float, float]:
        w = width * v
        return ((radius + w * math.cos(u / 2)) * math.cos(u),
                w * math.sin(u / 2),
                (radius + w * math.cos(u / 2)) * math.sin(u))
    return parametric(f, u=(0, 2 * math.pi), v=(-1, 1),
                      steps_u=steps_u, steps_v=steps_v, **style)


def klein_bottle(scale: float = 0.25, *, steps_u: int = 40, steps_v: int = 24, **style: object) -> Scene3D:
    def f(u: float, v: float) -> tuple[float, float, float]:
        cu, su = math.cos(u), math.sin(u)
        cv, sv = math.cos(v), math.sin(v)
        x = -(2 / 15) * cu * (3 * cv - 30 * su + 90 * cu**4 * su - 60 * cu**6 * su + 5 * cu * cv * su)
        y = -(1 / 15) * su * (3 * cv - 3 * cu**2 * cv - 48 * cu**4 * cv + 48 * cu**6 * cv
                              - 60 * su + 5 * cu * cv * su - 5 * cu**3 * cv * su
                              - 80 * cu**5 * cv * su + 80 * cu**7 * cv * su)
        z = (2 / 15) * (3 + 5 * cu * su) * sv
        return (x * scale, y * scale, z * scale)
    return parametric(f, u=(0, math.pi), v=(0, 2 * math.pi),
                      steps_u=steps_u, steps_v=steps_v, **style)


def saddle(extent: float = 1.0, *, steps: int = 26, **style: object) -> Scene3D:
    def f(u: float, v: float) -> tuple[float, float, float]:
        return (u, (u * u - v * v) * 0.6, v)
    return parametric(f, u=(-extent, extent), v=(-extent, extent),
                      steps_u=steps, steps_v=steps, **style)


def wave(
    *,
    extent: float = 1.0,
    amplitude: float = 0.32,
    wavelength: float = 0.7,
    sources: Sequence[tuple[float, float]] = ((0.0, 0.0),),
    steps: int = 40,
    **style: object,
) -> Scene3D:
    """A radial-interference wave heightfield ``y = Σ A·sin(2π·r/λ)``.

    With one source it is a ripple; with several it is an interference pattern.
    Returned as a perspective-ready mesh (height on the Y axis, X/Z on the plane).
    """
    k = 2 * math.pi / wavelength

    def f(u: float, v: float) -> tuple[float, float, float]:
        h = 0.0
        for sx, sz in sources:
            r = math.hypot(u - sx, v - sz)
            h += amplitude * math.sin(k * r)
        return (u, h / max(1, len(sources)) * len(sources), v)
    return parametric(f, u=(-extent, extent), v=(-extent, extent),
                      steps_u=steps, steps_v=steps, **style)


__all__ = ["bezier_patch", "bezier_patch_point", "bspline_patch", "bspline_patch_point",
           "klein_bottle", "mobius", "parametric", "saddle", "sphere", "torus", "wave"]
