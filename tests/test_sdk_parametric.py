#!/usr/bin/env python3
"""Parametric / function / polar curve sampling (roadmap Appendix A.3 — the 2D
curve sampler with adaptive flatness subdivision; previously missing). Pins that
samples concentrate on curvature, lie on the curve, map through a Frame's scales,
and emit polyline/path objects."""
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import Frame, function_plot, parametric_curve, polar_plot  # noqa: E402


def test_adaptive_refines_on_curvature_and_stays_on_curve():
    obj = parametric_curve(lambda t: (math.cos(t), math.sin(t)), (0.0, math.pi),
                           init_segments=4, tolerance=0.01)
    assert obj["type"] == "polyline"
    pts = obj["points"]
    assert len(pts) > 5                                   # refined past the 4 seed segments
    assert abs(pts[0][0] - 1.0) < 1e-9 and abs(pts[-1][0] + 1.0) < 1e-9   # endpoints
    assert all(abs(math.hypot(x, y) - 1.0) < 1e-6 for x, y in pts)        # on the unit circle


def test_straight_line_does_not_over_refine():
    # a line is flat everywhere -> only the seed points, no recursive splits
    obj = parametric_curve(lambda t: (t, 2 * t), (0.0, 1.0), init_segments=4)
    assert len(obj["points"]) == 5                       # 4 seed segments -> 5 points


def test_emit_path_object():
    obj = parametric_curve(lambda t: (t, t * t), (0.0, 1.0), emit="path")
    assert obj["type"] == "path" and isinstance(obj["d"], str) and obj["d"].startswith("M")


def test_function_plot_maps_through_frame_x_domain():
    frame = Frame(domain=(0, 0, 10, 100), box=(0, 0, 200, 100))
    pts = function_plot(lambda x: x * x, frame)["points"]
    assert abs(pts[0][0] - 0.0) < 1e-6                    # x=0 -> page x=0
    assert abs(pts[-1][0] - 200.0) < 1e-6                 # x=10 -> page x=200


def test_polar_plot_unit_circle_through_frame():
    frame = Frame(domain=(-1, -1, 1, 1), box=(0, 0, 100, 100))
    pts = polar_plot(lambda th: 1.0, frame)["points"]    # unit circle
    assert len(pts) > 8
    assert all(abs(math.hypot(x - 50, y - 50) - 50) < 1.0 for x, y in pts)  # mapped circle


def test_log_scale_samples_in_page_space():
    # with a log x-scale the flatness is measured in page space, so a straight data
    # line becomes curved on the page and gets refined
    frame = Frame(domain=(1, 0, 100, 100), box=(0, 0, 200, 100), x_scale="log")
    pts = function_plot(lambda x: x, frame, domain=(1, 100), init_segments=2, tolerance=0.5)["points"]
    assert len(pts) > 3                                   # refined due to log curvature on page
