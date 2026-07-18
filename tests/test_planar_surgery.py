#!/usr/bin/env python3
"""Planar surgery — fillet, chamfer, trim, extend (the sketcher's edit verbs).

The planar kernel already does booleans, offsets and path cuts; these are the
remaining corner/segment operators every 2D CAD sketcher carries. Ground truth
is analytic: known corner replacements on the unit square, the exact area a
fillet removes, and line-intersection trims/extends.
"""
from __future__ import annotations

import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from frameforge.sdk.planar import (  # noqa: E402
    chamfer_ring, extend_segment, fillet_ring, ring_area, trim_segment)

SQUARE = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def test_chamfer_square_cuts_each_corner():
    out = chamfer_ring(SQUARE, 0.2)
    assert len(out) == 8
    assert (pytest.approx(0.2), pytest.approx(0.0)) in [(x, y) for x, y in out] or \
        any(abs(x - 0.2) < 1e-9 and abs(y) < 1e-9 for x, y in out)
    # every original corner is gone
    for corner in SQUARE:
        assert not any(abs(x - corner[0]) < 1e-9 and abs(y - corner[1]) < 1e-9
                       for x, y in out)
    # chamfer area removal: 4 * (d²/2)
    assert abs(ring_area(out)) == pytest.approx(1.0 - 4 * 0.02, abs=1e-9)


def test_fillet_square_area_matches_analytic():
    r = 0.25
    out = fillet_ring(SQUARE, r, samples=24)
    assert len(out) == 4 * 25
    # a 90° fillet removes (4 − π)·r² of area in total across four corners
    expected = 1.0 - (4.0 - math.pi) * r * r
    assert abs(ring_area(out)) == pytest.approx(expected, abs=2e-4)
    # tangency: the arc meets the bottom edge r away from the corner
    assert any(abs(y) < 1e-6 and abs(x - r) < 1e-6 for x, y in out)


def test_fillet_selected_corner_only():
    out = fillet_ring(SQUARE, 0.2, corners=[0], samples=6)
    assert len(out) == 3 + 7
    # untouched corners remain
    assert any(abs(x - 1.0) < 1e-9 and abs(y - 1.0) < 1e-9 for x, y in out)


def test_fillet_skips_oversized_radius():
    # a radius needing more edge than exists must leave that corner alone
    tiny = [(0.0, 0.0), (0.1, 0.0), (0.1, 1.0), (0.0, 1.0)]
    out = fillet_ring(tiny, 0.4, samples=4)
    assert (0.1, 0.0) in [(round(x, 6), round(y, 6)) for x, y in out]


def test_trim_segment_at_cutting_line():
    p0, p1 = trim_segment((0, 0), (10, 0), (4, -5), (4, 5))
    assert p0 == (0, 0)
    assert p1 == (pytest.approx(4.0), pytest.approx(0.0))
    with pytest.raises(ValueError):
        trim_segment((0, 0), (10, 0), (0, 1), (10, 1))    # parallel


def test_extend_segment_to_line():
    p0, p1 = extend_segment((0, 0), (2, 0), (5, -3), (5, 9))
    assert p1 == (pytest.approx(5.0), pytest.approx(0.0))
