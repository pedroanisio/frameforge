"""POC-05 — redrawing *over* a trace: rough polygons -> clean, intentional lines.

Tracing, colouring, and guide-layers all keep the trace's mechanical geometry.
"Redrawing over" replaces it: the polygonal trace (straight segments, contour
noise) is re-emitted as smooth curves, simplified, and — where a blob is really a
circle or a box — snapped to a clean primitive. The output is *new* FrameForge
art that follows the trace, not the trace itself.

    1. SIMPLIFY     — Douglas-Peucker drops contour noise (fewer, meaningful pts).
    2. REDRAW SMOOTH— each polyline/polygon becomes a Catmull-Rom `path` (cubic
                      Béziers), so jagged traces read as deliberate strokes.
    3. SNAP PRIMITIVE — a near-circular/near-rectangular blob is replaced by a
                      clean `ellipse`/`rect` (recognition, not tracing).

Pure geometry (no OpenCV): `simplify`, `redraw_smooth`, `snap_primitives` are
unit-tested directly; only the raster `trace` imports OpenCV (lazily).

Run:
    uv run --group vision python examples/poc5_redraw.py \
        demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc5
"""
from __future__ import annotations

import argparse
import copy
import math
import os
import sys
from typing import Any, Iterable, Sequence

sys.path.insert(0, os.environ.get("FG_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frameforge.sdk import DocumentBuilder, Path, render_page_svgs  # noqa: E402
from poc3_ingest_compose import place, restyle_strokes  # noqa: E402

Obj = dict[str, Any]
Pt = Sequence[float]


# --------------------------------------------------------------------------- #
# Geometry (pure).
# --------------------------------------------------------------------------- #
def _perp_dist(p: Pt, a: Pt, b: Pt) -> float:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def simplify(points: Sequence[Pt], tol: float) -> list[list[float]]:
    """Ramer-Douglas-Peucker: drop points within ``tol`` of the chord. Endpoints kept."""
    pts = [[float(x), float(y)] for x, y in points]
    if len(pts) < 3 or tol <= 0:
        return pts
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = _perp_dist(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        left = simplify(pts[:idx + 1], tol)
        right = simplify(pts[idx:], tol)
        return left[:-1] + right
    return [pts[0], pts[-1]]


def _bbox(points: Sequence[Pt]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def is_circular(points: Sequence[Pt], tol: float = 0.18) -> bool:
    """True for a blob-circle: vertices near-equidistant from the centroid AND the
    polygon fills ~pi/4 of its bounding box (which excludes a square, whose
    corner/edge radii alone can sneak under the equidistance threshold)."""
    if len(points) < 6:
        return False
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    rs = [math.hypot(p[0] - cx, p[1] - cy) for p in points]
    mean = sum(rs) / len(rs)
    if mean <= 0:
        return False
    var = sum((r - mean) ** 2 for r in rs) / len(rs)
    if (var ** 0.5) / mean > tol:
        return False
    x0, y0, x1, y1 = _bbox(points)
    box = (x1 - x0) * (y1 - y0)
    fill = _poly_area(points) / box if box > 0 else 0.0
    return 0.6 <= fill <= 0.92          # circle ~= pi/4 (0.785); square ~= 1.0


def is_rectangular(points: Sequence[Pt], tol: float = 0.12) -> bool:
    """True if a 4-corner simplification fills ~its bounding box (an axis-ish box)."""
    s = simplify(points, max(1.0, 0.02 * max(_span(points))))
    s = s[:-1] if len(s) > 1 and s[0] == s[-1] else s
    if not 4 <= len(s) <= 6:
        return False
    x0, y0, x1, y1 = _bbox(points)
    area_box = (x1 - x0) * (y1 - y0)
    return area_box > 0 and _poly_area(points) / area_box >= (1.0 - tol)


def _span(points: Sequence[Pt]) -> tuple[float, float]:
    x0, y0, x1, y1 = _bbox(points)
    return x1 - x0, y1 - y0


def _poly_area(points: Sequence[Pt]) -> float:
    n = len(points)
    a = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


# --------------------------------------------------------------------------- #
# Redraw transforms.
# --------------------------------------------------------------------------- #
def _carry_style(src: Obj, dst: Obj) -> Obj:
    if isinstance(src.get("style"), dict):
        dst["style"] = copy.deepcopy(src["style"])
    return dst


def redraw_smooth(objs: Iterable[Obj], *, simplify_tol: float = 1.5,
                  width: float = 1.4, stroke: str | None = None) -> list[Obj]:
    """Re-emit polylines/polygons as smooth Catmull-Rom ``path`` objects."""
    out: list[Obj] = []
    for o in objs:
        t = o.get("type")
        pts = o.get("points")
        if t == "polyline" and pts:
            sp = simplify(pts, simplify_tol)
            if len(sp) < 3:
                out.append(copy.deepcopy(o))
                continue
            obj = Path().through(sp).object(
                stroke=stroke or o.get("stroke", "#1E2440"), fill="none",
                stroke_style={"stroke_width": width, "stroke_linecap": "round",
                              "stroke_linejoin": "round"})
            out.append(_carry_style(o, obj))
        elif t == "polygon" and pts:
            sp = simplify(pts, simplify_tol)
            if len(sp) < 3:
                out.append(copy.deepcopy(o))
                continue
            obj = Path().through([*sp, sp[0]]).close().object(fill=o.get("fill", "#000000"))
            out.append(_carry_style(o, obj))
        else:
            out.append(copy.deepcopy(o))
    return out


def snap_primitives(objs: Iterable[Obj], *, circ_tol: float = 0.16) -> list[Obj]:
    """Replace near-circular/near-rectangular polygons with clean primitives."""
    out: list[Obj] = []
    for o in objs:
        if o.get("type") == "polygon" and o.get("points") and len(o["points"]) >= 5:
            pts = o["points"]
            x0, y0, x1, y1 = _bbox(pts)
            if is_circular(pts, circ_tol):
                obj = {"type": "ellipse", "center": [(x0 + x1) / 2, (y0 + y1) / 2],
                       "rx": (x1 - x0) / 2, "ry": (y1 - y0) / 2, "fill": o.get("fill", "#000000")}
                out.append(_carry_style(o, obj))
                continue
            if is_rectangular(pts):
                obj = {"type": "rect", "box": [x0, y0, x1 - x0, y1 - y0], "fill": o.get("fill", "#000000")}
                out.append(_carry_style(o, obj))
                continue
        out.append(copy.deepcopy(o))
    return out


def curve_count(objs: Iterable[Obj]) -> int:
    """How many objects are paths whose ``d`` carries a cubic/quad curve command."""
    n = 0
    for o in objs:
        if o.get("type") == "path":
            d = o.get("d")
            s = d if isinstance(d, str) else " ".join(seg[0] for seg in d if seg)
            if "C" in s or "Q" in s or "S" in s:
                n += 1
    return n


# --------------------------------------------------------------------------- #
# Ingest + page.
# --------------------------------------------------------------------------- #
def trace(image: str, *, mode: str, **kw) -> tuple[list[Obj], int, int]:
    from frameforge.vision.infrastructure.vectorize import raster_to_objects
    return raster_to_objects(image, mode=mode, **kw)


def _panel(layer, x, y, w, h, label, color):
    layer.add({"type": "rect", "box": [x, y, w, h], "fill": "#FFFFFF", "radius": 10})
    layer.add({"type": "text", "box": [x + 14, y + 8, w - 28, 20], "text": label,
               "style": {"font_family": ["Inter", "sans-serif"], "font_size": 13,
                         "font_weight": 700, "color": color}})


def build_redraw(outline: list[Obj], src: tuple[int, int]):
    """Four panels: raw trace, redrawn smooth, simplified+smooth, primitive-snapped."""
    cw, ch, pad = 620, 380, 22
    W = 2 * cw + 3 * pad
    H = 2 * ch + 3 * pad + 44
    b = DocumentBuilder(title="poc5-redraw")
    page = b.page("rd", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.text([pad, 12, W - 2 * pad, 26], "Redraw over a trace: jagged contours -> clean smooth strokes",
              style={"font_family": ["Inter", "sans-serif"], "font_size": 18,
                     "font_weight": 700, "color": "#F2F5FA"})
    inner = [cw - 20, ch - 44]
    cells = [(pad, 44 + pad), (pad + cw + pad, 44 + pad),
             (pad, 44 + pad + ch + pad), (pad + cw + pad, 44 + pad + ch + pad)]
    ink = "#15203A"

    variants = [
        ("raw trace (polylines)", restyle_strokes(outline, stroke=ink, width=1.0), "#8B949E"),
        ("redraw: smooth Catmull-Rom paths", redraw_smooth(outline, simplify_tol=1.2, width=1.5, stroke=ink), "#3FB7EB"),
        ("redraw: simplified + smooth", redraw_smooth(outline, simplify_tol=3.5, width=1.8, stroke=ink), "#3FB950"),
        ("redraw: bold inked (heavy simplify)", redraw_smooth(outline, simplify_tol=6.5, width=2.8, stroke=ink), "#E8B04B"),
    ]
    for (label, objs, color), (x, y) in zip(variants, cells):
        layer = page.layer(label.split(":")[0].strip().replace(" ", "_"))
        _panel(layer, x, y, cw, ch, label, color)
        for o in place(objs, [x + 10, y + 34, inner[0], inner[1]], src):
            layer.add(o)
    return b


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--out", default="out/poc5")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    outline, w, h = trace(args.image, mode="outline", detail=0.0016, min_area=24.0, max_dim=1400)
    src = (w, h)
    print(f"[ingest] outline={len(outline)} polylines ({w}x{h})")

    raw_pts = sum(len(o.get("points", [])) for o in outline)
    redrawn = redraw_smooth(outline, simplify_tol=3.5)
    nc = curve_count(redrawn)
    ok_curves = nc > 0
    print(f"[gate] redraw emits {nc} smooth curve paths (was 0): {'PASS' if ok_curves else 'FAIL'}")

    simp_pts = sum(len(simplify(o.get("points", []), 3.5)) for o in outline if o.get("points"))
    ok_simpler = simp_pts < raw_pts
    print(f"[gate] simplify reduces points {raw_pts} -> {simp_pts}: {'PASS' if ok_simpler else 'FAIL'}")

    snapped = snap_primitives(outline)
    n_prim = sum(1 for o in snapped if o.get("type") in ("ellipse", "rect"))
    print(f"[info] primitive-snap recovered {n_prim} clean ellipse/rect from blobs")

    b = build_redraw(outline, src)
    svg = render_page_svgs(b.build())[0]
    ok_render = svg.startswith("<svg") and ("C" in svg or "c " in svg)
    print(f"[gate] page validates + renders curved paths: {'PASS' if ok_render else 'FAIL'}")

    b.write(os.path.join(args.out, "redraw.fg.yaml"))
    with open(os.path.join(args.out, "redraw.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"[write] {args.out}/redraw.svg (+ .fg.yaml)")

    verdict = ok_curves and ok_simpler and ok_render
    print(f"\nVERDICT: {'YES - the trace can be redrawn into clean, smooth art' if verdict else 'NEEDS WORK'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
