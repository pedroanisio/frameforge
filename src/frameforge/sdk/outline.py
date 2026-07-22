"""Filled-outline stroke engine + repeat-along-path brushes (issue #46, W2).

One shared emitter lowers three Illustrator-class capabilities to
grammar-native primitives at author time (nothing new enters the schema):

- :func:`stroke_outline` — a stroke centre-line becomes a CLOSED filled
  ``path`` object. Constant width is the Outline-Stroke conversion (AI-48);
  a ``profile`` callable varies width along the stroke (AI-12, the Width
  tool); a calligraphic pen (``pen_angle``/``pen_thin``) modulates width by
  stroke direction (AI-49's calligraphic brush). ``smooth=True`` routes the
  centre-line through Catmull-Rom (:meth:`CubicBezier.catmull_rom`) — the
  declarative curvature-tool outcome (AI-09).
- :func:`repeat_along_path` — arc-length placements with tangent rotation,
  the scatter / art / pattern brush half of AI-49; pass ``stamp=`` to get
  translated object copies directly.

The geometry is deliberately plain: flatten → per-vertex averaged normals →
offset both sides → caps. Joins: ``miter`` (scaled averaged normal, capped
at ``miterlimit``), ``bevel`` (both segment normals), ``round`` (sampled
arc). This is an authoring emitter, not a general polygon-offset kernel —
self-intersection surgery on pathological centre-lines is W1's planar
kernel, out of scope here (nonzero fill hides the common cases).
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from frameforge.sdk.geometry import CubicBezier, Vec2

__all__ = ["Placement", "place_stamp", "repeat_along_path", "stroke_outline"]

Pt = Sequence[float]
_EPS = 1e-9


def _v2(p: Vec2 | Pt) -> Vec2:
    return p if isinstance(p, Vec2) else Vec2(float(p[0]), float(p[1]))


def _unit(v: Vec2) -> Vec2:
    n = math.hypot(v.x, v.y)
    return Vec2(v.x / n, v.y / n) if n > _EPS else Vec2(0.0, 0.0)


def _flatten(points: Sequence[Vec2 | Pt], smooth: bool,
             samples: int) -> list[Vec2]:
    pts = [_v2(p) for p in points]
    if len(pts) < 2:
        raise ValueError("stroke_outline needs at least two centre-line points")
    if not smooth:
        return pts
    out: list[Vec2] = [pts[0]]
    for seg in CubicBezier.catmull_rom(pts):
        for i in range(1, samples + 1):
            out.append(seg.point(i / samples))
    return out


def _arc_params(pts: list[Vec2]) -> tuple[list[float], float]:
    """Cumulative arc length per vertex and the total."""
    acc, total = [0.0], 0.0
    for a, b in zip(pts, pts[1:]):
        total += math.hypot(b.x - a.x, b.y - a.y)
        acc.append(total)
    return acc, total


def _half_widths(pts: list[Vec2], width: float,
                 profile: Callable[[float], float] | None,
                 pen_angle: float | None, pen_thin: float) -> list[float]:
    acc, total = _arc_params(pts)
    halves = []
    for i, p in enumerate(pts):
        w = width
        if profile is not None:
            t = acc[i] / total if total > _EPS else 0.0
            w = width * max(0.0, float(profile(t)))
        if pen_angle is not None:
            d = _tangent(pts, i)
            delta = math.atan2(d.y, d.x) - math.radians(pen_angle)
            w = w * math.sqrt(math.cos(delta) ** 2
                              + (pen_thin * math.sin(delta)) ** 2)
        halves.append(w / 2.0)
    return halves


def _tangent(pts: list[Vec2], i: int) -> Vec2:
    if i == 0:
        return _unit(pts[1] - pts[0])
    if i == len(pts) - 1:
        return _unit(pts[-1] - pts[-2])
    return _unit(_unit(pts[i] - pts[i - 1]) + _unit(pts[i + 1] - pts[i]))


def _normal(d: Vec2) -> Vec2:
    return Vec2(-d.y, d.x)


def _arc_points(center: Vec2, start: Vec2, end: Vec2, radius: float,
                steps: int = 8) -> list[Vec2]:
    """Sampled arc from direction `start` to `end` (unit vectors) around
    center, choosing the shorter sweep."""
    a0 = math.atan2(start.y, start.x)
    a1 = math.atan2(end.y, end.x)
    sweep = a1 - a0
    while sweep > math.pi:
        sweep -= 2 * math.pi
    while sweep < -math.pi:
        sweep += 2 * math.pi
    return [Vec2(center.x + radius * math.cos(a0 + sweep * k / steps),
                 center.y + radius * math.sin(a0 + sweep * k / steps))
            for k in range(1, steps)]


def _side(pts: list[Vec2], halves: list[float], sign: float,
          join: str, miterlimit: float) -> list[Vec2]:
    """One offset side of the centre-line, joins resolved per vertex."""
    out: list[Vec2] = []
    n = len(pts)
    for i, p in enumerate(pts):
        h = halves[i]
        if i == 0 or i == n - 1 or h <= _EPS:
            d = _tangent(pts, i)
            out.append(p + _normal(d) * (sign * h))
            continue
        d_in = _unit(pts[i] - pts[i - 1])
        d_out = _unit(pts[i + 1] - pts[i])
        n_in, n_out = _normal(d_in) * sign, _normal(d_out) * sign
        avg = _unit(n_in + n_out)
        cos_half = avg.x * n_in.x + avg.y * n_in.y  # cos of the half-angle
        turn = d_in.x * d_out.y - d_in.y * d_out.x  # >0 left turn
        outer = (turn * sign) < 0                   # this side is the outside
        if not outer or cos_half > 0.999:           # inner side / straight
            scale = 1.0 / max(cos_half, 0.25)
            out.append(p + avg * (h * scale))
        elif join == "round":
            out.append(p + n_in * h)
            out.extend(_arc_points(p, n_in, n_out, h))
            out.append(p + n_out * h)
        elif join == "miter" and cos_half > 1.0 / miterlimit:
            out.append(p + avg * (h / cos_half))
        else:                                       # bevel (and miter overflow)
            out.append(p + n_in * h)
            out.append(p + n_out * h)
    return out


def _cap(p: Vec2, d: Vec2, h: float, cap: str, from_n: Vec2,
         to_n: Vec2) -> list[Vec2]:
    """End-cap points between offset side ends (from_n → to_n are unit
    normals of the two sides at this end; ``d`` points OUT of the stroke)."""
    if h <= _EPS or cap == "butt":
        return []
    if cap == "square":
        e = d * h
        return [p + from_n * h + e, p + to_n * h + e]
    # round: from_n → to_n are opposite, so the shorter-sweep arc is
    # ambiguous at π — route it explicitly through the outward direction
    return (_arc_points(p, from_n, d, h) + [p + d * h]
            + _arc_points(p, d, to_n, h))


def stroke_outline(points: Sequence[Vec2 | Pt], width: float, *,
                   profile: Callable[[float], float] | None = None,
                   pen_angle: float | None = None, pen_thin: float = 0.25,
                   cap: str = "butt", join: str = "miter",
                   miterlimit: float = 4.0, smooth: bool = False,
                   samples: int = 24, emit_params: bool = True,
                   **fields: Any) -> dict[str, Any]:
    """A stroke centre-line as a closed, filled ``path`` object.

    ``width`` is the full stroke width. ``profile(t)`` (t = arc-length
    fraction 0→1) scales it along the stroke. A calligraphic pen sets the
    effective width to ``width·√(cos²Δ + pen_thin²·sin²Δ)`` where Δ is the
    angle between the local tangent and ``pen_angle`` — full width along
    the pen direction, ``width·pen_thin`` across it. Extra ``fields``
    (fill, id, opacity …) pass through to the emitted object; ``fill``
    defaults to ``currentColor``.
    """
    pts = _flatten(points, smooth, samples)
    halves = _half_widths(pts, float(width), profile, pen_angle, pen_thin)
    fwd = _side(pts, halves, +1.0, join, miterlimit)
    back = _side(pts, halves, -1.0, join, miterlimit)

    d_end = _tangent(pts, len(pts) - 1)
    d_start = _tangent(pts, 0)
    end_cap = _cap(pts[-1], d_end, halves[-1], cap,
                   _normal(d_end), _normal(d_end) * -1.0)
    start_cap = _cap(pts[0], d_start * -1.0, halves[0], cap,
                     _normal(d_start) * -1.0, _normal(d_start))

    ring = fwd + end_cap + list(reversed(back)) + start_cap
    d: list[list[Any]] = [["M", ring[0].x, ring[0].y]]
    d.extend(["L", p.x, p.y] for p in ring[1:])
    d.append(["Z"])
    fields.setdefault("fill", "currentColor")
    if emit_params:
        # G3 provenance: the generative parameters ride on the object's meta
        # bag (never interpreted by the renderer), so an emitted stroke stays
        # a PARAMETRIC object — geometry refinement (vision refine_geometry)
        # and future edits can re-derive the outline instead of freezing it.
        prov: dict[str, Any] = {
            "spine": [[round(p.x, 2), round(p.y, 2)] for p in pts],
            "width": float(width),
            "profile": [round(float(profile(i / 15.0)), 4) for i in range(16)]
                       if profile is not None else None,
            "cap": cap,
            "join": join,
        }
        if prov["profile"] is None:
            del prov["profile"]
        if pen_angle is not None:
            prov["pen_angle"] = float(pen_angle)
            prov["pen_thin"] = float(pen_thin)
        meta = dict(fields.pop("meta", None) or {})
        meta.setdefault("stroke_outline", prov)
        fields["meta"] = meta
    return {"type": "path", "d": d, **fields}


@dataclass(frozen=True)
class Placement:
    """One repeat-along-path stop: page point, tangent angle (deg), t."""

    point: tuple[float, float]
    angle: float
    t: float


def repeat_along_path(points: Sequence[Vec2 | Pt], *, spacing: float,
                      smooth: bool = False, samples: int = 24,
                      stamp: dict[str, Any] | None = None,
                      ) -> list[Placement] | list[dict[str, Any]]:
    """Arc-length placements along a centre-line (the brush half of AI-49).

    Returns :class:`Placement` stops every ``spacing`` units (both ends
    included). With ``stamp=`` the stamp object is copied to each stop —
    ``center``/``box``/``from``+``to`` geometry is translated in place;
    anything else is wrapped in a translated (and, off-axis, rotated)
    ``group``.
    """
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    pts = _flatten(points, smooth, samples)
    acc, total = _arc_params(pts)
    stops: list[Placement] = []
    s, seg = 0.0, 0
    while s <= total + _EPS:
        while seg < len(acc) - 2 and acc[seg + 1] < s - _EPS:
            seg += 1
        seg_len = acc[seg + 1] - acc[seg]
        f = (s - acc[seg]) / seg_len if seg_len > _EPS else 0.0
        p = pts[seg] + (pts[seg + 1] - pts[seg]) * f
        d = _unit(pts[seg + 1] - pts[seg])
        stops.append(Placement((p.x, p.y), math.degrees(math.atan2(d.y, d.x)),
                               s / total if total > _EPS else 0.0))
        s += spacing
    if stamp is None:
        return stops
    return [place_stamp(stamp, hit) for hit in stops]


def place_stamp(stamp: dict[str, Any], hit: Placement) -> dict[str, Any]:
    """Copy ``stamp`` to a :class:`Placement` — geometry-translated where the
    object carries ``center``/``box``/``from``+``to``, group-wrapped otherwise."""
    obj = copy.deepcopy(stamp)
    x, y = hit.point
    if "center" in obj:
        obj["center"] = [obj["center"][0] + x, obj["center"][1] + y]
        return obj
    if "box" in obj:
        bx, by, bw, bh = obj["box"]
        obj["box"] = [bx + x, by + y, bw, bh]
        return obj
    if "from" in obj and "to" in obj:
        obj["from"] = [obj["from"][0] + x, obj["from"][1] + y]
        obj["to"] = [obj["to"][0] + x, obj["to"][1] + y]
        return obj
    transform: dict[str, Any] = {"translate": [x, y]}
    if abs(hit.angle) > _EPS:
        transform["rotate"] = hit.angle
    return {"type": "group", "transform": transform, "children": [obj]}
