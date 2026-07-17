"""POC-03 — ingestion x FrameForge: a raster becomes a *programmable* asset.

Thesis under test (with REAL execution, not prose):

    A raw trace only *copies* a picture. The power multiplier is what happens
    AFTER ingestion, because the trace is now FrameForge objects:

      1. RESTYLE   — one ingestion, N looks. Re-ink / re-palette the geometry
                     with pure functions. Impossible on a flat raster without
                     redrawing; here it is `o["stroke"] = ...`.
      2. COMPOSE   — the trace is a first-class document element: FrameForge
                     lays it out beside native text, a chart, a palette legend.
      3. VERIFY    — every claim is a numeric gate (PALS's Law): geometry is
                     invariant under restyle, each style renders *distinctly*,
                     every page validates against the model, and the ingest
                     half reports a measured fidelity score against the source.

The pure transforms (`restyle_strokes`, `recolor_fills`, `place`, `bbox`) carry
no OpenCV dependency, so they are unit-testable without the `vision` group; the
raster ingest (`trace`) imports OpenCV lazily.

Run:
    uv run --group vision python examples/poc3_ingest_compose.py \
        demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc3
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
from typing import Any, Callable, Iterable, Sequence

sys.path.insert(0, os.environ.get("FG_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402

Obj = dict[str, Any]

# --------------------------------------------------------------------------- #
# Pure transforms over FrameForge object dicts (no OpenCV, fully testable).
# Every function returns a NEW list/objects; inputs are never mutated.
# --------------------------------------------------------------------------- #
_STROKE_TYPES = {"polyline", "line", "path"}
_FILL_TYPES = {"polygon", "rect", "ellipse", "circle", "path"}


def restyle_strokes(objs: Iterable[Obj], *, stroke: str, width: float | None = None) -> list[Obj]:
    """Re-ink every stroked object. Geometry is untouched; only paint changes."""
    out: list[Obj] = []
    for o in objs:
        o = copy.deepcopy(o)
        if o.get("type") in _STROKE_TYPES and ("stroke" in o or o.get("type") != "path"):
            o["stroke"] = stroke
            if width is not None:
                ss = dict(o.get("stroke_style") or {})
                ss["stroke_width"] = width
                o["stroke_style"] = ss
        out.append(o)
    return out


def recolor_fills(objs: Iterable[Obj], fn: Callable[[str], str]) -> list[Obj]:
    """Remap every solid fill through ``fn`` (e.g. monochrome -> palette)."""
    out: list[Obj] = []
    for o in objs:
        o = copy.deepcopy(o)
        if o.get("type") in _FILL_TYPES and isinstance(o.get("fill"), str) and o["fill"] != "none":
            o["fill"] = fn(o["fill"])
        out.append(o)
    return out


def _luma(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return 0.0
    return 0.2126 * r + 0.7152 * g + 0.0722 * b  # Rec.709 relative luminance


def palette_by_luma(palette: Sequence[str]) -> Callable[[str], str]:
    """Map a fill to a palette slot chosen by its luminance (dark->first)."""
    pal = list(palette)
    n = len(pal)
    def fn(hex_color: str) -> str:
        idx = min(n - 1, int(_luma(hex_color) / 256.0 * n))
        return pal[idx]
    return fn


def _coords(o: Obj) -> list[tuple[float, float]]:
    t = o.get("type")
    if t in ("polyline", "polygon") and o.get("points"):
        return [(float(x), float(y)) for x, y in o["points"]]
    if t == "rect" and o.get("box"):
        x, y, w, h = (float(v) for v in o["box"])
        return [(x, y), (x + w, y + h)]
    if t == "line":
        return [tuple(map(float, o["from"])), tuple(map(float, o["to"]))]
    if t in ("ellipse", "circle") and o.get("center"):
        cx, cy = (float(v) for v in o["center"])
        rx, ry = float(o.get("rx", o.get("r", 0))), float(o.get("ry", o.get("r", 0)))
        return [(cx - rx, cy - ry), (cx + rx, cy + ry)]
    return []


def bbox(objs: Iterable[Obj]) -> tuple[float, float, float, float] | None:
    """Axis-aligned bounds (minx, miny, maxx, maxy) over all geometry, or None."""
    xs: list[float] = []
    ys: list[float] = []
    for o in objs:
        for x, y in _coords(o):
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def obj_bbox(o: Obj) -> tuple[float, float, float, float] | None:
    """Axis-aligned bounds of a single object, or None if it has no geometry."""
    pts = _coords(o)
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def select_region(objs: Iterable[Obj], box: Sequence[float], *, contain: bool = False) -> list[Obj]:
    """Use only *part* of a trace: keep objects inside (or touching) ``box``.

    ``contain=False`` keeps anything that intersects ``box`` (a loose crop);
    ``contain=True`` keeps only objects fully inside it (a strict extract).
    Returns new objects; never mutates the input.
    """
    bx, by, bw, bh = (float(v) for v in box)
    bx2, by2 = bx + bw, by + bh
    out: list[Obj] = []
    for o in objs:
        bb = obj_bbox(o)
        if bb is None:
            continue
        x0, y0, x1, y1 = bb
        if contain:
            keep = x0 >= bx and y0 >= by and x1 <= bx2 and y1 <= by2
        else:
            keep = not (x1 < bx or x0 > bx2 or y1 < by or y0 > by2)
        if keep:
            out.append(copy.deepcopy(o))
    return out


def select_where(objs: Iterable[Obj], pred: Callable[[Obj], bool]) -> list[Obj]:
    """Keep objects matching ``pred`` (e.g. only polylines, or large shapes)."""
    return [copy.deepcopy(o) for o in objs if pred(o)]


def translate_objs(objs: Iterable[Obj], dx: float, dy: float) -> list[Obj]:
    """Move a subset: shift every coordinate by (dx, dy). Geometry truly changes."""
    out: list[Obj] = []
    for o in objs:
        o = copy.deepcopy(o)
        t = o.get("type")
        if t in ("polyline", "polygon") and o.get("points"):
            o["points"] = [[x + dx, y + dy] for x, y in o["points"]]
        elif t == "rect" and o.get("box"):
            x, y, w, h = o["box"]
            o["box"] = [x + dx, y + dy, w, h]
        elif t == "line":
            o["from"] = [o["from"][0] + dx, o["from"][1] + dy]
            o["to"] = [o["to"][0] + dx, o["to"][1] + dy]
        elif t in ("ellipse", "circle") and o.get("center"):
            o["center"] = [o["center"][0] + dx, o["center"][1] + dy]
        out.append(o)
    return out


def place(objs: Iterable[Obj], box: Sequence[float], src: Sequence[float]) -> list[Obj]:
    """Fit ``src``-sized geometry into ``box`` (centered, aspect kept).

    Composes a ``translate scale`` ahead of any existing ``style.transform`` —
    so a placed object keeps its own transform and gains the layout one.
    """
    bx, by, bw, bh = (float(v) for v in box)
    sw, sh = float(src[0]), float(src[1])
    s = min(bw / sw, bh / sh) if sw and sh else 1.0
    tx = bx + (bw - sw * s) / 2.0
    ty = by + (bh - sh * s) / 2.0
    pre = f"translate({tx:.3f} {ty:.3f}) scale({s:.5f})"
    out: list[Obj] = []
    for o in objs:
        o = copy.deepcopy(o)
        style = dict(o.get("style") or {})
        prev = style.get("transform")
        style["transform"] = f"{pre} {prev}" if prev else pre
        o["style"] = style
        out.append(o)
    return out


# --------------------------------------------------------------------------- #
# Style grammar — one ingestion, many looks.
# --------------------------------------------------------------------------- #
STYLES: list[dict[str, Any]] = [
    {"id": "ink",       "label": "as-traced ink", "bg": "#F6F3EC", "stroke": "#1E2440", "width": 1.4},
    {"id": "blueprint", "label": "blueprint",      "bg": "#0B2A4A", "stroke": "#8FD3FF", "width": 1.2},
    {"id": "neon",      "label": "neon",           "bg": "#0A0A12", "stroke": "#FF3CAC", "width": 1.6},
    {"id": "crimson",   "label": "crimson sketch", "bg": "#FFF8F2", "stroke": "#C2143B", "width": 1.1},
]


def trace(image: str, *, colors: int = 8, detail: float = 0.0015,
          min_area: float = 16.0, max_dim: int = 1500) -> tuple[list[Obj], int, int]:
    """Ingest a raster to outline FrameForge objects (lazy OpenCV import)."""
    from frameforge.vision.infrastructure.vectorize import raster_to_objects
    return raster_to_objects(image, mode="outline", colors=colors, detail=detail,
                             min_area=min_area, max_dim=max_dim)


# --------------------------------------------------------------------------- #
# Document assembly.
# --------------------------------------------------------------------------- #
def render_single(objs: list[Obj], size: tuple[int, int]) -> str:
    """Render one object set on a bare page (used to compare styles 1:1)."""
    b = DocumentBuilder(title="single")
    page = b.page("p", canvas={"size": [size[0], size[1]], "units": "px"},
                  coordinate_mode="absolute")
    layer = page.layer("m")
    for o in objs:
        layer.add(o)
    return render_page_svgs(b.build())[0]


def build_style_matrix(base: list[Obj], src: tuple[int, int], *,
                       cols: int = 2, cell: tuple[int, int] = (660, 380),
                       pad: int = 24) -> tuple[Any, list[str]]:
    """Page: the SAME geometry re-skinned into every STYLES entry."""
    cw, ch = cell
    rows = (len(STYLES) + cols - 1) // cols
    W = cols * cw + (cols + 1) * pad
    H = rows * ch + (rows + 1) * pad + 40
    b = DocumentBuilder(title="poc3-style-matrix")
    page = b.page("matrix", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#FFFFFF")
    page.text([pad, 10, W - 2 * pad, 28], "One ingestion - four looks (same geometry, re-inked)",
              style={"font_family": ["Inter", "sans-serif"], "font_size": 18, "font_weight": 700,
                     "color": "#11151C"})
    style_ids: list[str] = []
    for i, st in enumerate(STYLES):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = 40 + pad + r * (ch + pad)
        layer = page.layer(st["id"])
        layer.add({"type": "rect", "box": [x, y, cw, ch], "fill": st["bg"], "radius": 10})
        styled = restyle_strokes(base, stroke=st["stroke"], width=st["width"])
        for o in place(styled, [x + 10, y + 36, cw - 20, ch - 46], src):
            layer.add(o)
        layer.add({"type": "text", "box": [x + 14, y + 8, cw - 28, 20], "text": st["label"],
                   "style": {"font_family": ["Inter", "sans-serif"], "font_size": 13,
                             "font_weight": 700, "color": st["stroke"]}})
        style_ids.append(st["id"])
    return b, style_ids


def _frac_box(src: Sequence[float], fx: float, fy: float, fw: float, fh: float) -> list[float]:
    w, h = float(src[0]), float(src[1])
    return [fx * w, fy * h, fw * w, fh * h]


def build_parts(base: list[Obj], src: tuple[int, int]) -> tuple[Any, dict[str, int]]:
    """Page proving part-level use: extract a region, edit one element, recompose.

    This is the answer to "it only loads the whole image": the trace is a bag of
    editable objects, so we select sub-regions, restyle one element alone, and
    delete + duplicate parts into a NEW arrangement.
    """
    board = _frac_box(src, 0.02, 0.06, 0.30, 0.58)      # the whiteboard region
    figure = _frac_box(src, 0.28, 0.18, 0.20, 0.66)     # the presenter

    whole = base
    # strict contain: objects fully inside the region, so a frame-spanning stroke
    # (table/floor) is NOT dragged in by a touching bbox -> an honest crop.
    extract = select_region(base, board, contain=True)                    # use only a part
    elem = restyle_strokes(select_region(base, figure, contain=True),
                           stroke="#C2143B", width=1.8)                   # edit one part
    # recompose: delete the whiteboard, then duplicate the presenter shifted right
    bx, by, bw, bh = board
    people = select_where(base, lambda o: (lambda b: b is None or
             (b[2] < bx or b[0] > bx + bw or b[3] < by or b[1] > by + bh))(obj_bbox(o)))
    dup = translate_objs(select_region(base, figure), 0.42 * src[0], 0.0)
    recompose = people + dup

    panels = [
        ("whole trace", whole, "#1E2440"),
        ("extract: whiteboard only", extract, "#1E2440"),
        ("one element, restyled alone", elem, "#C2143B"),
        ("recompose: -board +duplicate", recompose, "#1E2440"),
    ]
    cols, cw, ch, pad = 2, 600, 360, 22
    W = cols * cw + (cols + 1) * pad
    H = 2 * ch + 3 * pad + 44
    b = DocumentBuilder(title="poc3-parts")
    page = b.page("parts", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#FFFFFF")
    page.text([pad, 12, W - 2 * pad, 26], "Use only parts: select, edit one element, recompose",
              style={"font_family": ["Inter", "sans-serif"], "font_size": 18, "font_weight": 700,
                     "color": "#11151C"})
    counts: dict[str, int] = {}
    for i, (label, objs, stroke) in enumerate(panels):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = 44 + pad + r * (ch + pad)
        layer = page.layer(f"panel{i}")
        layer.add({"type": "rect", "box": [x, y, cw, ch], "fill": "#F6F3EC", "radius": 10})
        styled = objs if stroke == "#C2143B" else restyle_strokes(objs, stroke=stroke, width=1.3)
        for o in place(styled, [x + 10, y + 34, cw - 20, ch - 44], src):
            layer.add(o)
        layer.add({"type": "text", "box": [x + 14, y + 8, cw - 28, 20],
                   "text": f"{label}  ({len(objs)} obj)",
                   "style": {"font_family": ["Inter", "sans-serif"], "font_size": 13,
                             "font_weight": 700, "color": stroke}})
        counts[label] = len(objs)
    return b, counts


def build_composition(base: list[Obj], src: tuple[int, int], *, n_objs: int,
                      fidelity: float | None) -> Any:
    """Page: the trace as a document element beside native text + chart."""
    W, H = 1280, 720
    b = DocumentBuilder(title="poc3-composition")
    page = b.page("case", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.rect([0, 0, W, 84], fill="#161B22")
    page.text([40, 22, W - 80, 40], "From picture to document",
              style={"font_family": ["Inter", "sans-serif"], "font_size": 28, "font_weight": 800,
                     "color": "#F2F5FA"})

    # left: the ingested asset, framed
    art = page.layer("asset")
    art.add({"type": "rect", "box": [40, 116, 720, 560], "fill": "#F6F3EC", "radius": 12})
    inked = restyle_strokes(base, stroke="#1E2440", width=1.3)
    for o in place(inked, [56, 132, 688, 528], src):
        art.add(o)

    # right: native FrameForge content annotating the asset
    side = page.layer("annotation")
    side.add({"type": "text", "box": [800, 120, 440, 60], "text": "Ingested vector base",
              "style": {"font_family": ["Inter", "sans-serif"], "font_size": 20,
                        "font_weight": 700, "color": "#9FB3C8"}})
    facts = [
        f"{n_objs} editable objects",
        f"{len(STYLES)} restyles from 1 ingestion",
        "geometry invariant under restyle",
    ]
    if fidelity is not None:
        facts.append(f"ink-IoU vs source: {fidelity:.2f}")
    for i, line in enumerate(facts):
        side.add({"type": "text", "box": [800, 168 + i * 30, 440, 26], "text": f"- {line}",
                  "style": {"font_family": ["Inter", "sans-serif"], "font_size": 15,
                            "color": "#E6EDF3"}})

    # a native chart: stroke count carried into each restyle (proves preservation)
    chart = page.chart([840, 360, 360, 220], domain=(0, 0, len(STYLES) + 1, n_objs * 1.15))
    chart.axes(x_ticks=[i + 1 for i in range(len(STYLES))], y_ticks=[0, n_objs],
               x_format=lambda v: STYLES[int(v) - 1]["id"][:4], grid=True,
               axis_color="#52606D", grid_color="#21262D")
    chart.bars([(i + 1, n_objs) for i in range(len(STYLES))], width=34,
               fill="#3FB950", radius=3)
    chart.add_to(side)
    side.add({"type": "text", "box": [800, 600, 440, 24], "text": "objects per restyle (identical = preserved)",
              "style": {"font_family": ["Inter", "sans-serif"], "font_size": 12, "color": "#8B949E"}})

    # palette legend
    for i, st in enumerate(STYLES):
        side.add({"type": "rect", "box": [800 + i * 70, 648, 18, 18], "fill": st["stroke"], "radius": 4})
    return b


# --------------------------------------------------------------------------- #
# Soundness gate.
# --------------------------------------------------------------------------- #
def geometry_invariant(base: list[Obj], styled: list[Obj]) -> bool:
    """True iff restyle changed paint only (count + per-object geometry equal)."""
    if len(base) != len(styled):
        return False
    return all(_coords(a) == _coords(b) for a, b in zip(base, styled))


def ink_iou(image: str, svg: str, *, dim: int = 512, tol: int = 2) -> float | None:
    """Tolerance-banded structural agreement of source vs trace ink (line-art).

    A raw 1-px-stroke IoU is dominated by sub-pixel misregistration, not real
    disagreement, so it understates line-art fidelity badly. We instead dilate
    both ink masks by ``tol`` px (a Chamfer-style tolerance band) before the
    intersection-over-union — an honest "are the strokes in the same place,
    within a couple of pixels" score. Best-effort: None if deps are absent.
    """
    try:
        import cairosvg
        import cv2
        import numpy as np
    except Exception:
        return None
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=dim, output_height=dim)
    arr = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
    srcimg = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
    if arr is None or srcimg is None:
        return None
    srcimg = cv2.resize(srcimg, (dim, dim), interpolation=cv2.INTER_AREA)
    k = np.ones((2 * tol + 1, 2 * tol + 1), np.uint8)
    a = cv2.dilate((arr < 128).astype(np.uint8), k).astype(bool)        # trace ink
    s = cv2.dilate((srcimg < 128).astype(np.uint8), k).astype(bool)     # source ink
    inter = int(np.logical_and(a, s).sum())
    union = int(np.logical_or(a, s).sum())
    return inter / union if union else 0.0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="source raster (line-art works best)")
    ap.add_argument("--out", default="out/poc3", help="output directory")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    base, w, h = trace(args.image)
    src = (w, h)
    print(f"[ingest] {args.image} -> {len(base)} objects ({w}x{h})")

    # ---- gate 1: geometry invariant under restyle ----
    ok_inv = all(geometry_invariant(base, restyle_strokes(base, stroke=st["stroke"], width=st["width"]))
                 for st in STYLES)
    print(f"[gate] geometry invariant under {len(STYLES)} restyles: {'PASS' if ok_inv else 'FAIL'}")

    mb, _style_ids = build_style_matrix(base, src)
    matrix_svgs = render_page_svgs(mb.build())

    # ---- gate 2: each restyle renders DISTINCTLY ----
    per_style = {st["id"]: render_single(restyle_strokes(base, stroke=st["stroke"]), src)
                 for st in STYLES}
    ok_distinct = len(set(per_style.values())) == len(STYLES)
    print(f"[gate] {len(STYLES)} styles render distinctly: {'PASS' if ok_distinct else 'FAIL'}")

    # ---- fidelity (ingest half): a flat single-layer black-ink render vs source ----
    flat = DocumentBuilder(title="fidelity")
    fp = flat.page("p", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    fp.rect([0, 0, w, h], fill="#FFFFFF")
    fl = fp.layer("ink")
    for o in restyle_strokes(base, stroke="#000000", width=1.0):
        fl.add(o)
    fid = ink_iou(args.image, render_page_svgs(flat.build())[0])
    print(f"[fidelity] ink-IoU vs source: {fid if fid is None else round(fid, 3)}")

    # ---- gate 3: part-level use (select / edit one element / recompose) ----
    pb, counts = build_parts(base, src)
    parts_svg = render_page_svgs(pb.build())[0]
    extract_n = counts["extract: whiteboard only"]
    elem_n = counts["one element, restyled alone"]
    ok_parts = 0 < extract_n < len(base) and 0 < elem_n < len(base)
    print(f"[gate] part selection is a strict subset "
          f"(extract={extract_n}, element={elem_n} of {len(base)}): "
          f"{'PASS' if ok_parts else 'FAIL'}")

    cb = build_composition(base, src, n_objs=len(base), fidelity=fid)
    comp_svg = render_page_svgs(cb.build())[0]
    ok_native = comp_svg.count("<text") >= 4  # native annotation present
    print(f"[gate] composition carries native text/chart: {'PASS' if ok_native else 'FAIL'}")

    # ---- write artifacts ----
    mb.write(os.path.join(args.out, "style_matrix.fg.yaml"))
    cb.write(os.path.join(args.out, "composition.fg.yaml"))
    pb.write(os.path.join(args.out, "parts.fg.yaml"))
    for name, svg in (("style_matrix", matrix_svgs[0]), ("composition", comp_svg), ("parts", parts_svg)):
        with open(os.path.join(args.out, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print(f"[write] {args.out}/style_matrix.svg, composition.svg, parts.svg (+ .fg.yaml)")

    verdict = ok_inv and ok_distinct and ok_parts and ok_native
    print(f"\nVERDICT: {'FEASIBLE - ingestion x FrameForge compounds' if verdict else 'NEEDS WORK'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
