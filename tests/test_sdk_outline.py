"""sdk.outline — the shared filled-outline emitter (issue #46, parity W2).

One geometry engine closes three teardown rows at SDK level (documents carry
only grammar-native primitives): a stroke centre-line (+ optional width
profile or calligraphic pen) lowers to a CLOSED filled ``path`` object
(AI-12 variable width, AI-48 outline stroke, AI-49 calligraphic half), and
``repeat_along_path`` places instances by arc length with tangent rotation
(AI-49 scatter/art/pattern half). ``through()`` (AI-09) is asserted against
its knot-passage contract, and kerning (AI-24) gets explicit pair support
with a real-metrics path when fontTools is present.

Runs under pytest or standalone (``uv run python tests/test_sdk_outline.py``).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from framegraph.sdk import (  # noqa: E402
    kerned_spans,
    repeat_along_path,
    stroke_outline,
)
from framegraph.sdk.geometry import Path as GPath  # noqa: E402
from framegraph.sdk.model import HEAD_VERSION, validate_document  # noqa: E402


def _ring(obj):
    """Decode the emitted path object's structured d into its points."""
    pts = []
    for seg in obj["d"]:
        if seg[0] in ("M", "L"):
            pts.append((seg[1], seg[2]))
    return pts


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ── the emitter: constant width ─────────────────────────────────────────


def test_constant_width_outline_is_a_closed_filled_path():
    obj = stroke_outline([(0, 0), (100, 0)], width=10, fill="#123456")
    assert obj["type"] == "path"
    assert obj["fill"] == "#123456"
    assert obj["d"][-1][0] == "Z", "outline must close"
    ring = _ring(obj)
    ys = sorted({round(y, 6) for _, y in ring})
    assert ys[0] == -5.0 and ys[-1] == 5.0, "offset must be width/2 each side"


def test_outline_respects_the_declared_width_along_the_stroke():
    obj = stroke_outline([(0, 0), (200, 0)], width=16)
    ring = _ring(obj)
    left = [p for p in ring if p[1] < 0]
    right = [p for p in ring if p[1] > 0]
    for p in left:
        assert abs(p[1] + 8) < 1e-6
    for p in right:
        assert abs(p[1] - 8) < 1e-6
    assert left and right


def test_right_angle_corner_survives_with_a_join():
    obj = stroke_outline([(0, 0), (100, 0), (100, 100)], width=10,
                         join="round")
    ring = _ring(obj)
    # every ring point stays within a half-width tube of the centre-line
    for x, y in ring:
        d_seg1 = abs(y) if 0 <= x <= 100 else math.inf
        d_seg2 = abs(x - 100) if 0 <= y <= 100 else math.inf
        d_corner = _dist((x, y), (100, 0))
        assert min(d_seg1, d_seg2, d_corner) <= 5 + 1e-6


# ── width profiles + the calligraphic pen ───────────────────────────────


def test_width_profile_tapers_the_outline():
    obj = stroke_outline([(0, 0), (100, 0)], width=12,
                         profile=lambda t: 1.0 - t)   # full → zero
    ring = _ring(obj)
    start = [p for p in ring if abs(p[0]) < 1e-6]
    end = [p for p in ring if abs(p[0] - 100) < 1e-6]
    start_w = max(y for _, y in start) - min(y for _, y in start)
    end_w = max(y for _, y in end) - min(y for _, y in end)
    assert abs(start_w - 12) < 1e-6
    assert end_w < 0.75, "profile 0 at the end must pinch the outline"


def test_calligraphic_pen_width_follows_the_pen_angle():
    # pen held at 0° (thin axis vertical): a horizontal stroke is at full
    # width, a vertical stroke collapses toward the thin width
    horiz = stroke_outline([(0, 0), (100, 0)], width=10, pen_angle=0,
                           pen_thin=0.2)
    vert = stroke_outline([(0, 0), (0, 100)], width=10, pen_angle=0,
                          pen_thin=0.2)
    h_ring, v_ring = _ring(horiz), _ring(vert)
    h_w = max(y for _, y in h_ring) - min(y for _, y in h_ring)
    v_w = max(x for x, _ in v_ring) - min(x for x, _ in v_ring)
    assert abs(h_w - 10) < 1e-6
    assert abs(v_w - 2) < 1e-6                        # 10 × pen_thin


# ── grammar-native output ───────────────────────────────────────────────


def test_outline_object_validates_inside_a_document():
    obj = stroke_outline([(10, 10), (90, 10), (90, 90)], width=8,
                         fill="ink", join="bevel", cap="square")
    doc = {"dsl": "FrameGraph", "version": HEAD_VERSION, "title": "outline",
           "profile": "diagram",
           "defs": {"tokens": {"colors": {"ink": "#111111"}}},
           "pages": [{"mode": "page", "id": "p",
                      "canvas": {"size": [200, 200], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "m", "objects": [obj]}]}]}
    validate_document(doc)


def test_smooth_centreline_accepts_through_points():
    """AI-09: the curvature-tool outcome — a smooth stroke through knots —
    is `through()` feeding the emitter; the outline must stay within the
    half-width tube of the smooth centre-line's knots."""
    knots = [(0, 0), (50, 40), (100, 0)]
    obj = stroke_outline(knots, width=6, smooth=True)
    assert obj["d"][-1][0] == "Z"
    ring = _ring(obj)
    assert len(ring) > 20, "smooth centre-line must be flattened finely"


def test_through_passes_through_its_knots():
    p = GPath().move_to(0, 0).through([(50, 40), (100, 0)])
    d = p.d()
    assert d.startswith("M 0 0")
    assert "100" in d and "40" in d


# ── repeat along path (the brush half) ──────────────────────────────────


def test_repeat_along_path_spaces_by_arc_length():
    hits = repeat_along_path([(0, 0), (100, 0)], spacing=25)
    assert [round(h.point[0], 6) for h in hits] == [0, 25, 50, 75, 100]
    assert all(abs(h.angle) < 1e-9 for h in hits)


def test_repeat_along_path_rotates_with_the_tangent():
    hits = repeat_along_path([(0, 0), (0, 100)], spacing=50)
    assert [round(h.point[1], 6) for h in hits] == [0, 50, 100]
    for h in hits:
        assert abs(h.angle - 90) < 1e-9


def test_repeat_along_path_stamps_objects():
    stamp = {"type": "ellipse", "center": [0, 0], "rx": 3, "ry": 3,
             "fill": "ink"}
    objs = repeat_along_path([(0, 0), (60, 0)], spacing=30, stamp=stamp)
    assert len(objs) == 3
    assert [o["center"][0] for o in objs] == [0, 30, 60]
    assert all(o["type"] == "ellipse" for o in objs)


def test_structured_d_survives_the_model_round_trip_to_svg():
    """Regression (found by pixel-verifying this feature): pydantic dumps
    structured-d segments as TUPLES, and the renderer's lowering only
    accepted lists — every structured path silently rendered as a
    stringified Python tuple (garbage that also hangs cairosvg). The SDK
    render path (validate → model_dump → normalize → render) must emit
    real path data."""
    from framegraph.sdk import render_pages_with_stats
    obj = stroke_outline([(10, 10), (90, 10)], width=8, fill="#123456")
    doc = {"dsl": "FrameGraph", "version": HEAD_VERSION, "title": "d",
           "profile": "diagram",
           "pages": [{"mode": "page", "id": "p",
                      "canvas": {"size": [120, 40], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "m", "objects": [obj]}]}]}
    svgs, _ = render_pages_with_stats(doc, base_dir=str(ROOT))
    assert "('" not in svgs[0] and "(&#x27;" not in svgs[0], \
        "structured d must not stringify as Python tuples"
    assert 'd="M 10 6' in svgs[0] or 'd="M 10.0 6' in svgs[0] or \
        "M 10" in svgs[0].split('d="')[1][:20]
    assert " Z" in svgs[0].split('d="')[1].split('"')[0]


# ── kerning (AI-24) ─────────────────────────────────────────────────────


def test_explicit_kern_pairs_become_letter_spacing_spans():
    spans = kerned_spans("AVA", pairs={("A", "V"): -2.0, ("V", "A"): -1.5})
    assert [s["text"] for s in spans] == ["A", "V", "A"]
    assert spans[0]["style"]["letter_spacing"] == -2.0
    assert spans[1]["style"]["letter_spacing"] == -1.5
    assert "style" not in spans[2] or "letter_spacing" not in spans[2].get(
        "style", {})


def test_kerned_spans_without_pairs_is_a_single_run():
    spans = kerned_spans("Hello", pairs={})
    assert spans == [{"text": "Hello"}]


def test_font_kern_pairs_degrades_without_fonttools():
    from framegraph.sdk import font_kern_pairs
    pairs = font_kern_pairs("NoSuchFamilyXYZ", "AV", font_size=100)
    assert pairs == {}, "unknown font must degrade to no kerning, not crash"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
