#!/usr/bin/env python3
"""test_geometry_curvature.py — B9: curvature & arc-length for curves (CG-canon).

`CubicBezier` gains derivatives, signed `curvature(t)` (κ = 1/R, sign = bend
direction), and `arc_length()` (adaptive Simpson on speed |B'(t)|); a module
`polyline_length()` sums segment lengths. Verified against analytic truths: a
straight-line cubic has κ ≡ 0 and length == chord; the κ quarter-circle Bézier
integrates to ≈ π/2 with curvature ≈ 1/R at its midpoint; and every cubic's
arc length lies between its chord and its control-polygon length.
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import CubicBezier, Vec2, polyline_length, quarter_circle_kappa  # noqa: E402


def _straight():
    return CubicBezier(Vec2(0, 0), Vec2(1, 0), Vec2(2, 0), Vec2(3, 0))


def _unit_quarter_circle():
    k = quarter_circle_kappa()
    return CubicBezier(Vec2(1, 0), Vec2(1, k), Vec2(k, 1), Vec2(0, 1))


def test_derivative_endpoints_match_the_hodograph():
    b = CubicBezier(Vec2(0, 0), Vec2(1, 2), Vec2(4, 2), Vec2(5, 0))
    # B'(0) = 3(p1 - p0), B'(1) = 3(p3 - p2).
    d0 = b.derivative(0.0)
    d1 = b.derivative(1.0)
    assert math.isclose(d0.x, 3.0) and math.isclose(d0.y, 6.0)
    assert math.isclose(d1.x, 3.0) and math.isclose(d1.y, -6.0)


def test_straight_cubic_has_zero_curvature_everywhere():
    b = _straight()
    for t in (0.0, 0.25, 0.5, 0.9, 1.0):
        assert abs(b.curvature(t)) < 1e-9, f"straight line curvature at {t}"


def test_straight_cubic_arc_length_equals_chord():
    assert math.isclose(_straight().arc_length(), 3.0, abs_tol=1e-6)


def test_arc_length_between_chord_and_control_polygon():
    b = CubicBezier(Vec2(0, 0), Vec2(0, 4), Vec2(6, 4), Vec2(6, 0))
    chord = math.dist(b.p0.tuple(), b.p3.tuple())
    poly = (math.dist(b.p0.tuple(), b.p1.tuple())
            + math.dist(b.p1.tuple(), b.p2.tuple())
            + math.dist(b.p2.tuple(), b.p3.tuple()))
    length = b.arc_length()
    assert chord < length < poly, f"{chord} < {length} < {poly}"


def test_quarter_circle_arc_length_approximates_half_pi():
    length = _unit_quarter_circle().arc_length()
    assert math.isclose(length, math.pi / 2, abs_tol=1e-3), length


def test_quarter_circle_curvature_is_unit_radius_at_midpoint():
    # the κ Bézier approximates the unit circle; κ = 1/R ≈ 1 near the middle.
    k = abs(_unit_quarter_circle().curvature(0.5))
    assert math.isclose(k, 1.0, abs_tol=0.03), k


def test_curvature_sign_flips_with_bend_direction():
    up = CubicBezier(Vec2(0, 0), Vec2(1, 1), Vec2(2, 1), Vec2(3, 0))
    down = CubicBezier(Vec2(0, 0), Vec2(1, -1), Vec2(2, -1), Vec2(3, 0))
    assert up.curvature(0.5) * down.curvature(0.5) < 0, "mirror bends → opposite sign"


def test_polyline_length_sums_segments():
    assert math.isclose(polyline_length([(0, 0), (3, 4)]), 5.0)
    assert math.isclose(polyline_length([(0, 0), (3, 4), (6, 0)]), 10.0)
    assert polyline_length([(1, 1)]) == 0.0
    assert polyline_length([]) == 0.0
