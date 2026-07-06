#!/usr/bin/env python3
"""test_sdk_fractal.py — B4: the fractal / procedural generator (CG-canon backlog).

`framegraph.sdk.fractal` is a small L-system + turtle engine (Harrington Ch11 /
Mortenson) that lowers self-similar curves to plain polylines. Tests pin the
string-rewriting, the turtle's coordinate maps, the exact Koch generator, and the
fractal growth law (Koch: 4ⁿ segments, Dragon: 2ⁿ) — all deterministic.
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

from framegraph.sdk import (  # noqa: E402
    dragon_curve,
    koch_curve,
    lsystem,
    sierpinski_arrowhead,
    turtle,
)


def test_lsystem_rewrites_the_axiom():
    assert lsystem("F", {"F": "F+F--F+F"}, 0) == "F"
    assert lsystem("F", {"F": "F+F--F+F"}, 1) == "F+F--F+F"
    # a symbol with no rule is left unchanged (the +/- turtle commands).
    assert lsystem("F", {"F": "F+G", "G": "F-G"}, 2) == "F+G+F-G"


def test_turtle_forward_and_turn_maps():
    (poly,) = turtle("F", angle_deg=90, step=10)
    assert [p.tuple() for p in poly] == [(0.0, 0.0), (10.0, 0.0)]
    # heading 0 -> draw +x; turn +90 (CCW in math) -> heading +y (down in Y-down).
    (poly,) = turtle("F+F", angle_deg=90, step=10)
    assert [round(p.x, 6) for p in poly] == [0.0, 10.0, 10.0]
    assert [round(p.y, 6) for p in poly] == [0.0, 0.0, 10.0]


def test_turtle_branching_returns_multiple_polylines():
    # the bracketed [+F] is a branch off the trunk -> a separate polyline.
    polys = turtle("F[+F]F", angle_deg=45, step=10)
    assert len(polys) == 2


def test_koch_curve_is_the_classic_generator():
    pts = koch_curve(1, step=3.0)
    xs = [round(p.x, 3) for p in pts]
    ys = [round(p.y, 3) for p in pts]
    assert xs == [0.0, 3.0, 4.5, 6.0, 9.0]
    peak = round(3.0 * math.sin(math.radians(60)), 3)
    assert ys == [0.0, 0.0, peak, 0.0, 0.0]


def test_koch_growth_law_four_to_the_n_segments():
    for n in range(4):
        pts = koch_curve(n)
        assert len(pts) == 4**n + 1, f"koch({n}) should have 4^{n}+1 points"


def test_dragon_growth_law_two_to_the_n_segments():
    for n in range(5):
        pts = dragon_curve(n)
        assert len(pts) == 2**n + 1, f"dragon({n}) should have 2^{n}+1 points"


def test_sierpinski_arrowhead_is_deterministic_and_connected():
    a = sierpinski_arrowhead(3)
    b = sierpinski_arrowhead(3)
    assert [p.tuple() for p in a] == [p.tuple() for p in b]  # deterministic
    assert len(a) >= 4  # a real curve, not degenerate
