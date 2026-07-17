"""Type along a path — per-glyph placement on a measured polyline (recon gap F3).

Reconstruction sessions kept hand-rolling this walker, and kept re-making the
same two mistakes: offsetting glyphs to the convex side of a curve, and
measuring advances on the centreline while drawing on the offset path (which
visibly spreads or crushes the run wherever the path bends). This module owns
both decisions:

- :func:`offset_path` shifts a polyline along its **left normal** ``(-ty, tx)``
  — on a path sampled with increasing angle, positive offsets move toward the
  curve's centre (the concave side, where arc-set type conventionally sits);
- :func:`text_on_path` walks the *offset* path itself, so glyph advances are
  true distances on the line the glyphs actually occupy.

Glyphs are emitted as plain model ``text`` objects (one per glyph, ``rotation``
following the local tangent) ready for ``PageBuilder.extend`` — wrap the call
in ``with page.lettering():`` so the tabular-box heuristic knows the intent.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Sequence

from frameforge.sdk.metrics import measure_text

Pt = Sequence[float]

__all__ = ["offset_path", "path_length", "path_walker", "text_on_path"]


def path_length(points: Sequence[Pt]) -> float:
    """Total length of the open polyline through ``points``."""
    return sum(math.hypot(q[0] - p[0], q[1] - p[1])
               for p, q in zip(points, points[1:]))


def path_walker(
    points: Sequence[Pt],
) -> tuple[Callable[[float], tuple[tuple[float, float], tuple[float, float]]], float]:
    """Return ``(at, length)`` — ``at(s)`` gives ``((x, y), (tx, ty))`` at arc length ``s``.

    ``s`` is clamped to the path; the tangent is the containing segment's unit
    direction.
    """
    segs: list[tuple[float, Pt, Pt, float]] = []
    total = 0.0
    for p, q in zip(points, points[1:]):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        if d <= 0.0:
            continue
        segs.append((total, p, q, d))
        total += d
    if not segs:
        raise ValueError("path_walker needs a polyline with at least two distinct points")

    def at(s: float) -> tuple[tuple[float, float], tuple[float, float]]:
        s = max(0.0, min(float(s), total - 1e-9))
        for l0, p, q, d in segs:
            if s <= l0 + d:
                u = (s - l0) / d
                return ((p[0] + u * (q[0] - p[0]), p[1] + u * (q[1] - p[1])),
                        ((q[0] - p[0]) / d, (q[1] - p[1]) / d))
        p, q, d = segs[-1][1], segs[-1][2], segs[-1][3]
        return ((q[0], q[1]), ((q[0] - p[0]) / d, (q[1] - p[1]) / d))

    return at, total


def offset_path(points: Sequence[Pt], offset: float) -> list[tuple[float, float]]:
    """``points`` shifted by ``offset`` along the local left normal ``(-ty, tx)``.

    In page space (y down) a positive offset on a path sampled with increasing
    angle lands on the concave side — toward the centre of curvature.
    """
    out: list[tuple[float, float]] = []
    n = len(points)
    for i, p in enumerate(points):
        a, b = points[max(0, i - 1)], points[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        length = math.hypot(tx, ty) or 1.0
        out.append((p[0] - ty / length * offset, p[1] + tx / length * offset))
    return out


def text_on_path(
    points: Sequence[Pt],
    text: str,
    *,
    size: float,
    family: str | Sequence[str],
    weight: int | str | None = None,
    color: str | None = None,
    offset: float = 0.0,
    s0: float = 0.0,
    track: float = 2.5,
    space_advance: float = 0.32,
    style: dict[str, Any] | None = None,
    **fields: Any,
) -> list[dict[str, Any]]:
    """Set ``text`` glyph by glyph along ``points``, offset to the concave side.

    Advances come from real glyph metrics (:func:`~frameforge.sdk.metrics.measure_text`)
    measured **on the offset path**, so spacing stays optically even through
    curvature. Returns model ``text`` object dicts; extra ``fields`` are copied
    onto every glyph object (ids, meta, opacity …).
    """
    fam_list = [family] if isinstance(family, str) else list(family)
    fam = fam_list[0]
    walk_pts = offset_path(points, offset) if offset else [tuple(p) for p in points]
    at, _total = path_walker(walk_pts)

    base_style: dict[str, Any] = {"font_family": fam_list, "font_size": size,
                                  "align": "center"}
    if weight is not None:
        base_style["font_weight"] = weight
    if color is not None:
        base_style["color"] = color
    if style:
        base_style.update(style)

    bw = max(40.0, size * 2.0)
    objs: list[dict[str, Any]] = []
    s = float(s0)
    for ch in text:
        if ch == " ":
            s += size * space_advance + track
            continue
        adv = measure_text(ch, font_family=fam, font_size=size) + track
        (px, py), (tx, ty) = at(s + adv / 2.0)
        objs.append({
            "type": "text",
            "box": [px - bw / 2.0, py - size * 0.74, bw, size * 1.35],
            "text": ch,
            "rotation": math.degrees(math.atan2(ty, tx)),
            "style": dict(base_style),
            **fields,
        })
        s += adv
    return objs
