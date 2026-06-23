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


__all__ = ["klein_bottle", "mobius", "parametric", "saddle", "sphere", "torus", "wave"]
