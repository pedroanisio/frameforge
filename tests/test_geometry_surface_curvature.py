#!/usr/bin/env python3
"""test_geometry_surface_curvature.py — B9 residual: surface curvature.

`surface_curvature(fn, u, v)` returns the Gaussian curvature K and mean curvature
H of a parametric surface r(u,v)=fn(u,v) via the first and second fundamental
forms (Mortenson §8.5). Verified against the closed forms: a sphere of radius R
has K=1/R² and |H|=1/R, a plane has K=H=0, and a saddle has K<0 with H=0 at its
centre.
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

import pytest  # noqa: E402

from framegraph.sdk import surface_curvature  # noqa: E402


def _sphere(radius):
    def fn(u, v):
        return (radius * math.sin(v) * math.cos(u),
                radius * math.cos(v),
                radius * math.sin(v) * math.sin(u))
    return fn


def test_unit_sphere_has_unit_curvature():
    # away from the poles (v=0, v=π), where the parametrization is singular.
    K, H = surface_curvature(_sphere(1.0), u=1.0, v=1.2)
    assert abs(K - 1.0) < 2e-3
    assert abs(abs(H) - 1.0) < 2e-3


def test_sphere_curvature_scales_as_one_over_radius():
    K, H = surface_curvature(_sphere(2.0), u=0.7, v=1.1)
    assert abs(K - 0.25) < 2e-3       # 1/R² = 1/4
    assert abs(abs(H) - 0.5) < 2e-3   # 1/R  = 1/2


def test_plane_is_flat():
    K, H = surface_curvature(lambda u, v: (u, 0.0, v), u=0.3, v=-0.4)
    assert abs(K) < 1e-5
    assert abs(H) < 1e-5


def test_saddle_is_hyperbolic_with_zero_mean_at_the_centre():
    # z = u² − v² (height on the Y axis): K = −4, H = 0 at the origin.
    K, H = surface_curvature(lambda u, v: (u, u * u - v * v, v), u=0.0, v=0.0)
    assert K < 0
    assert abs(K - (-4.0)) < 1e-2
    assert abs(H) < 1e-3


def test_degenerate_point_raises():
    # r_u and r_v are parallel everywhere (v never enters the image) → no plane.
    with pytest.raises(ValueError):
        surface_curvature(lambda u, v: (u, 0.0, 0.0), u=0.5, v=0.5)
