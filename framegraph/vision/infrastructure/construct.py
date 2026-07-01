"""Vector construction from anchor points — the raster→vector output stage.

The measurement / workspace layers let the AI *find* precise coordinates; this
layer turns those coordinates into actual FrameGraph vector geometry. Given ordered
anchor points (workspace pins or explicit image-pixel points) and a shape kind, it
authors a real FrameGraph document via the SDK — so the reconstruction is validated
by the model and rendered by the same pipeline as everything else, and can be diffed
against the source with ``compare_images``.

Supported kinds map onto the SDK's canonical primitives:

    line ......... 2 points          -> line
    path/trace ... >=2 points        -> polyline (open)
    curve/spline . >=2 points        -> smooth polyline (Catmull-Rom -> path)
    polygon ...... >=3 points        -> polygon (closed polyline)
    triangle ..... 3 points          -> polygon
    closed ....... >=3 points        -> closed polyline (custom closed region)
    rect ......... 2+ points (bbox)  -> rect
    ellipse ...... 2+ points (bbox)  -> ellipse
    circle ....... 1 point + r, or 2 points (centre, rim) -> circle
    star ......... 1 point + r, or 2 points; ``points_count``/``inner_ratio`` -> polygon

The SDK validates every object, so a malformed shape fails loudly here rather than
producing a silently-wrong document.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

_DEFAULT_STYLE = {"stroke": "#e01c2c", "stroke_width": 2}
_OPEN_KINDS = {"line", "path", "trace", "polyline", "curve", "spline"}


def _normalize_style(style: dict[str, Any]) -> dict[str, Any]:
    """Lower the ergonomic ``stroke_width`` into ``stroke_style`` (P3: stroke geometry
    is not a direct object field; only stroke *paint* is)."""
    s = dict(style)
    sw = s.pop("stroke_width", None)
    if sw is not None:
        ss = dict(s.get("stroke_style") or {})
        ss.setdefault("stroke_width", sw)
        s["stroke_style"] = ss
    return s
_CLOSED_KINDS = {"polygon", "triangle", "closed", "rect", "ellipse", "circle", "star"}
SHAPE_KINDS = sorted(_OPEN_KINDS | _CLOSED_KINDS)


def _xy(p: Sequence[float]) -> list[float]:
    if len(p) < 2:
        raise ValueError(f"point {p!r} needs [x, y]")
    return [float(p[0]), float(p[1])]


def _bbox(points: Sequence[Sequence[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _star_points(center: Sequence[float], r_outer: float, n: int,
                 inner_ratio: float, rotation_deg: float = -90.0) -> list[list[float]]:
    cx, cy = float(center[0]), float(center[1])
    r_in = r_outer * inner_ratio
    pts: list[list[float]] = []
    for i in range(n * 2):
        ang = math.radians(rotation_deg) + i * math.pi / n
        r = r_outer if i % 2 == 0 else r_in
        pts.append([cx + r * math.cos(ang), cy + r * math.sin(ang)])
    return pts


def _add_shape(pb, shape: dict[str, Any]) -> dict[str, Any]:
    """Add one shape to a PageBuilder; return a summary record."""
    kind = str(shape.get("kind", "")).lower()
    if kind not in SHAPE_KINDS:
        raise ValueError(f"unknown shape kind {kind!r}; use one of {SHAPE_KINDS}")
    pts = [_xy(p) for p in (shape.get("points") or [])]
    style = _normalize_style({**_DEFAULT_STYLE, **(shape.get("style") or {})})
    # closed fills default to none unless the caller sets one
    summary: dict[str, Any] = {"kind": kind, "n_points": len(pts)}

    if kind == "line":
        if len(pts) != 2:
            raise ValueError("line needs exactly 2 points")
        pb.line(pts[0], pts[1], **style)
    elif kind in ("path", "trace", "polyline"):
        if len(pts) < 2:
            raise ValueError(f"{kind} needs >= 2 points")
        pb.polyline(pts, closed=False, **style)
    elif kind in ("curve", "spline"):
        if len(pts) < 2:
            raise ValueError(f"{kind} needs >= 2 points")
        pb.polyline(pts, closed=False, smooth=True, **style)
    elif kind in ("polygon", "triangle"):
        need = 3 if kind == "triangle" else 3
        if len(pts) < need:
            raise ValueError(f"{kind} needs >= {need} points")
        if kind == "triangle" and len(pts) != 3:
            raise ValueError("triangle needs exactly 3 points")
        pb.polygon(pts, **style)
    elif kind == "closed":
        if len(pts) < 3:
            raise ValueError("closed region needs >= 3 points")
        pb.polyline(pts, closed=True, **style)
    elif kind == "rect":
        if len(pts) < 2:
            raise ValueError("rect needs >= 2 points (its bbox)")
        x, y, w, h = _bbox(pts)
        pb.rect([x, y, w, h], **style)
        summary["box"] = [x, y, w, h]
    elif kind == "ellipse":
        if len(pts) < 2:
            raise ValueError("ellipse needs >= 2 points (its bbox)")
        x, y, w, h = _bbox(pts)
        pb.ellipse([x + w / 2, y + h / 2], w / 2, h / 2, **style)
    elif kind == "circle":
        if len(pts) == 1:
            r = float(shape.get("r", 0))
            if r <= 0:
                raise ValueError("circle from 1 point needs a positive 'r'")
            center = pts[0]
        elif len(pts) >= 2:
            center = pts[0]
            r = math.hypot(pts[1][0] - center[0], pts[1][1] - center[1])
        else:
            raise ValueError("circle needs a centre point")
        pb.circle(center, r, **style)
        summary["center"], summary["r"] = center, r
    elif kind == "star":
        if len(pts) == 1:
            r = float(shape.get("r", 0))
            if r <= 0:
                raise ValueError("star from 1 point needs a positive 'r'")
            center = pts[0]
        elif len(pts) >= 2:
            center = pts[0]
            r = math.hypot(pts[1][0] - center[0], pts[1][1] - center[1])
        else:
            raise ValueError("star needs a centre point")
        n = int(shape.get("points_count", 5))
        inner = float(shape.get("inner_ratio", 0.5))
        if n < 2:
            raise ValueError("star needs points_count >= 2")
        star = _star_points(center, r, n, inner)
        pb.polygon(star, **style)
        summary["center"], summary["r"], summary["points_count"] = center, r, n
    return summary


def build_document(shapes: Sequence[dict[str, Any]], *, width: int, height: int,
                   background: str | None = None,
                   title: str = "Vector reconstruction") -> tuple[str, list[dict[str, Any]]]:
    """Author a FrameGraph YAML document from resolved shapes; return (yaml, summaries).

    ``shapes`` carry points already resolved to image pixels. The page is sized to
    the source image (px), so the drawn geometry overlays the raster 1:1.
    """
    from framegraph.sdk import DocumentBuilder, serialize

    if not shapes:
        raise ValueError("no shapes to construct")
    doc = DocumentBuilder(title=title)
    canvas: dict[str, Any] = {"size": [int(width), int(height)], "units": "px"}
    page = doc.page("reconstruction", canvas=canvas, coordinate_mode="absolute")
    # A page background is a full-canvas fill rect (the CanvasObject has no
    # `background` field), drawn first so the shapes sit on top of it.
    if background:
        page.rect([0, 0, int(width), int(height)], fill=background)
    summaries = [_add_shape(page, dict(s)) for s in shapes]
    yaml_text = serialize(doc.build(), format="yaml")
    return yaml_text, summaries
