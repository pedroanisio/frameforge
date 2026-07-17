#!/usr/bin/env python3
"""test_geometry_reflect.py — B7: reflection / mirror transform (CG-canon backlog).

`Mat3.reflect(axis)` builds the reflection matrix across the x-axis, the y-axis, or
an arbitrary line given as two points (Mortenson §3.6); `mirror(points, axis)`
applies it to a sequence of points — the primitive for building a symmetric shape
from one half. Reflection is orientation-reversing (det == -1) and an involution
(applying it twice is the identity); both are asserted here as invariants.
"""
from __future__ import annotations

import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import Mat3, Vec2, mirror  # noqa: E402


def _close(p, q, tol=1e-9):
    return abs(p.x - q.x) < tol and abs(p.y - q.y) < tol


def test_reflect_across_x_axis_negates_y():
    m = Mat3.reflect("x")
    assert _close(m.apply(Vec2(2.0, 3.0)), Vec2(2.0, -3.0))


def test_reflect_across_y_axis_negates_x():
    m = Mat3.reflect("y")
    assert _close(m.apply(Vec2(2.0, 3.0)), Vec2(-2.0, 3.0))


def test_reflect_through_line_y_equals_x_swaps_coordinates():
    m = Mat3.reflect(((0.0, 0.0), (1.0, 1.0)))
    assert _close(m.apply(Vec2(2.0, 3.0)), Vec2(3.0, 2.0))
    assert _close(m.apply(Vec2(1.0, 0.0)), Vec2(0.0, 1.0))


def test_reflect_through_offset_horizontal_line():
    # the line y = 1 (through (0,1)-(1,1)); (0,0) mirrors to (0,2).
    m = Mat3.reflect(((0.0, 1.0), (1.0, 1.0)))
    assert _close(m.apply(Vec2(0.0, 0.0)), Vec2(0.0, 2.0))
    # a point ON the line is fixed.
    assert _close(m.apply(Vec2(5.0, 1.0)), Vec2(5.0, 1.0))


def test_reflection_is_orientation_reversing():
    for axis in ("x", "y", ((0.0, 0.0), (1.0, 2.0))):
        m = Mat3.reflect(axis)
        det = m.a * m.d - m.b * m.c
        assert math.isclose(det, -1.0, abs_tol=1e-9), f"det should be -1 for {axis!r}"


def test_reflection_is_an_involution():
    m = Mat3.reflect(((1.0, -2.0), (4.0, 5.0)))
    twice = m @ m
    for p in (Vec2(0.0, 0.0), Vec2(3.0, 7.0), Vec2(-2.0, 1.5)):
        assert _close((m @ m).apply(p), p), "reflect twice must be identity"
    assert math.isclose(twice.a, 1.0, abs_tol=1e-9) and math.isclose(twice.d, 1.0, abs_tol=1e-9)


def test_mirror_reflects_a_sequence_of_points():
    pts = [Vec2(1.0, 1.0), (2.0, 3.0), Vec2(0.0, -1.0)]
    out = mirror(pts, "y")
    assert [p.tuple() for p in out] == [(-1.0, 1.0), (-2.0, 3.0), (0.0, -1.0)]


def test_reflect_rejects_bad_axis():
    with pytest.raises(ValueError):
        Mat3.reflect("z")
    with pytest.raises(ValueError):
        Mat3.reflect(((0.0, 0.0), (0.0, 0.0)))  # degenerate line
