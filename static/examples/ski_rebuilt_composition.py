#!/usr/bin/env python3
"""Ingest ``ski_rebuilt.flat.svg`` and compose + transform it as native FrameForge.

This client takes one flattened vector drawing (the coach-rebuilt ``ski`` figure —
1 white ground + 1,332 paths) and shows the full round trip that makes an external
SVG a *first-class FrameForge asset*:

  * **Ingest** — :func:`svg_to_objects` lowers every SVG element into FrameForge
    primitive dicts (``rect`` / ``path``) the renderer draws 1:1. No raster step.
  * **Compose** — the lowered objects are assembled into a real ``DocumentBuilder``
    document (validatable, restyle-able, re-renderable).
  * **Transform** — the ingested figure is instanced as ``group``s whose
    ``style.transform`` carries one affine matrix each (rotate / scale / mirror /
    shear / squash), so the same geometry is placed many ways without re-emitting it.

Six pages:
  1. ``rebuild``  — the drawing at native size, faithful (all 1,333 objects).
  2. ``atlas``    — a transformation atlas: the figure under six affine transforms.
  3. ``poster``   — a designed composition (hero + rotated filmstrip).
  4. ``region``   — a region studio: select / clip / transform a sub-window of the
                    figure (clip rides on a static parent so it masks in page space).
  5. ``shot``     — the perfect shot: distinct colouring applied BY REGION LEVEL
                    (each region its own luminance ramp), full-bleed, with a vignette.
  6. ``grades``   — three region-level grade options (alpenglow / glacier / noir).

Run::

    uv run python examples/ski_rebuilt_composition.py            # build + validate + YAML
    uv run python examples/ski_rebuilt_composition.py --render   # also write page SVGs

Through the FrameForge MCP, ``run_sdk_client`` imports this module's ``build()``.
"""
from __future__ import annotations

import argparse
import copy
import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
# Drop a namespace-package shadow of ``frameforge`` if another working dir injected one.
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder, Mat3, clip_rect, radial_gradient, render_page_svgs, rgba, serialize,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402
from frameforge.vision.infrastructure.svg_import import svg_to_objects  # noqa: E402

SVG_PATH = os.path.join(ROOT, "ski_rebuilt.flat.svg")

FONT = ["Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"]

INK = "#0E1116"          # board / poster ground
PAPER = "#FFFFFF"        # the drawing's own ground
CARD = "#F6F7FB"         # contact-sheet tile
EDGE = "#D7DCE6"         # tile border
LIGHT = "#F2F5FA"        # text on dark
MUTE = "#9AA4B2"         # muted text on dark
SLATE = "#39414F"        # caption title on light
GREY = "#6B7585"         # caption expr on light
ACCENT = "#3AA0D8"       # rule / accents

_NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _ingest() -> tuple[dict, list[dict], list[dict], float, float]:
    """Lower the SVG once → (ground rect, all paths, clean paths, width, height)."""
    objs = svg_to_objects(SVG_PATH)
    ground = next((o for o in objs if o["type"] == "rect"), {"type": "rect",
                  "box": [0, 0, 2752, 1536], "fill": PAPER})
    w, h = ground["box"][2], ground["box"][3]
    paths = [o for o in objs if o["type"] == "path"]
    # The "clean" subset drops the near-degenerate congruence-marker dots (2–3 pts),
    # keeping the substantial silhouette — used where the figure is instanced many
    # times so a transform reads clearly and the page stays light to render.
    clean = [o for o in paths if len(_NUM.findall(o["d"])) // 2 >= 4]
    return ground, paths, clean, w, h


def _shear_x(degrees: float) -> Mat3:
    """Horizontal shear (skewX) as a bare affine matrix."""
    return Mat3(a=1.0, b=0.0, c=math.tan(math.radians(degrees)), d=1.0, e=0.0, f=0.0)


def _place(cell, transform: Mat3, *, w: float, h: float,
           margin: float = 0.86, reserve: float = 0.0) -> Mat3:
    """Matrix that fits the w×h figure into ``cell`` then applies ``transform`` about its center.

    ``reserve`` carves a caption strip off the bottom of the cell. Composition order
    (right→left on a point): center the figure, scale-to-fit, apply the showcased
    transform about that center, translate into the cell.
    """
    cx, cy, cw, ch = cell
    avail_h = ch - reserve
    fit = min(cw / w, avail_h / h) * margin
    return (Mat3.translate(cx + cw / 2, cy + avail_h / 2)
            @ transform
            @ Mat3.scale(fit)
            @ Mat3.translate(-w / 2, -h / 2))


def _instance(page, paths: list[dict], matrix: Mat3, *, clip=None) -> None:
    """Stamp a deep copy of ``paths`` as one transformed, decorative group.

    With ``clip``, the transform goes on an inner group and the clip on a static
    outer group, so the clip rectangle masks in page space (a clip applied on the
    same element as the transform would ride along inside the transformed frame).
    """
    inner = {"type": "group", "children": copy.deepcopy(paths),
             "style": {"transform": [matrix.transform_fn()]}, "decorative": True}
    if clip is not None:
        page.group([inner], clip=clip, decorative=True)
    else:
        page.add(inner)


# --------------------------------------------------------------------------- #
#  Region operations — select / clip / transform a sub-window of the figure    #
# --------------------------------------------------------------------------- #
def _bbox(d: str) -> tuple[float, float, float, float]:
    n = [float(x) for x in _NUM.findall(d)]
    xs, ys = n[0::2], n[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _select(paths: list[dict], region: list[float]) -> list[dict]:
    """Objects whose bounding box intersects ``region`` ([x, y, w, h]) — region extraction."""
    rx, ry, rw, rh = region
    rx1, ry1 = rx + rw, ry + rh
    out = []
    for o in paths:
        x0, y0, x1, y1 = _bbox(o["d"])
        if x1 >= rx and x0 <= rx1 and y1 >= ry and y0 <= ry1:
            out.append(o)
    return out


def _region_to_cell(region: list[float], cell, *, reserve: float = 0.0,
                    margin: float = 1.0) -> Mat3:
    """Matrix mapping ``region`` (aspect-preserved, centered) into ``cell`` minus a caption strip."""
    rx, ry, rw, rh = region
    cx, cy, cw, ch = cell
    avail_h = ch - reserve
    s = min(cw / rw, avail_h / rh) * margin
    tx = cx + (cw - rw * s) / 2 - rx * s
    ty = cy + (avail_h - rh * s) / 2 - ry * s
    return Mat3(a=s, b=0.0, c=0.0, d=s, e=tx, f=ty)


def _contained(d: str, region: list[float], pad: float = 8.0) -> bool:
    """True when a path's bbox sits inside ``region`` — isolates a region's own marks
    from the canvas-spanning sky path (which only *intersects* every region)."""
    x0, y0, x1, y1 = _bbox(d)
    rx, ry, rw, rh = region
    return x0 >= rx - pad and y0 >= ry - pad and x1 <= rx + rw + pad and y1 <= ry + rh + pad


# Region windows over the native figure ([x, y, w, h] in source pixels), tuned visually.
REGIONS = [
    ("skier", [1470, 330, 560, 520]),
    ("spray", [1700, 30, 1010, 600]),
    ("mountains", [40, 940, 1240, 560]),
    ("sun disc", [1235, 620, 200, 200]),
]


# --------------------------------------------------------------------------- #
#  Distinct colouring — region-level luminance gradient-map grade               #
# --------------------------------------------------------------------------- #
def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hexc(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def _lum(h: str) -> float:
    r, g, b = _rgb(h)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def _ramp(level: float, stops: list[tuple[float, str]]) -> str:
    """Map a 0..1 luminance to a colour on a multi-stop ramp (the gradient map)."""
    level = max(0.0, min(1.0, level))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if level <= p1:
            t = 0.0 if p1 == p0 else (level - p0) / (p1 - p0)
            a, b = _rgb(c0), _rgb(c1)
            return _hexc(a[i] + (b[i] - a[i]) * t for i in range(3))
    return stops[-1][1]


def _is_hex(v) -> bool:
    return isinstance(v, str) and v.startswith("#") and len(v) in (4, 7)


def _grade_paint(o: dict, stops: list[tuple[float, str]]) -> dict:
    """Return a copy of ``o`` with its fill/stroke remapped through ``stops``."""
    o = dict(o)
    if _is_hex(o.get("fill")):
        o["fill"] = _ramp(_lum(o["fill"]), stops)
    if _is_hex(o.get("stroke")):
        o["stroke"] = _ramp(_lum(o["stroke"]), stops)
    return o


# Region grade: every region carries its OWN luminance ramp, so the recolour is
# applied by region level. Each path is assigned to the region its centroid falls
# in (most-specific first: sun → skier → spray → mountains, else sky/background),
# then remapped through that region's ramp. The skier ramp is the colour complement
# of the sky so the subject reads as distinct, never camouflaged.
REGION_BOX = {
    "skier": REGIONS[0][1],
    "spray": REGIONS[1][1],
    "mountains": REGIONS[2][1],
    "sun": REGIONS[3][1],
}
_REGION_ORDER = ("sun", "skier", "spray", "mountains")

GRADES = {
    "alpenglow": dict(
        sky=[(0.0, "#1a1540"), (0.42, "#7a3f6b"), (0.72, "#d97a64"), (1.0, "#ffd9a0")],
        mountains=[(0.0, "#142a4d"), (0.5, "#3f6fa0"), (1.0, "#c2e2f5")],
        spray=[(0.0, "#caa9b6"), (0.5, "#f2c79b"), (1.0, "#fff3e0")],
        skier=[(0.0, "#06222b"), (0.5, "#36c6e8"), (1.0, "#eafcff")],
        sun="#ffd98a"),
    "glacier": dict(
        sky=[(0.0, "#0a1a2f"), (0.5, "#2f6f93"), (1.0, "#e2f4ff")],
        mountains=[(0.0, "#0e2230"), (0.5, "#356b7e"), (1.0, "#c2e8ef")],
        spray=[(0.0, "#9fc3d6"), (0.5, "#d2ecf5"), (1.0, "#ffffff")],
        skier=[(0.0, "#2a1505"), (0.5, "#ff8a3c"), (1.0, "#ffe7b0")],
        sun="#ffe9c2"),
    "noir": dict(
        sky=[(0.0, "#0b0d12"), (0.5, "#454c58"), (1.0, "#cfd5de")],
        mountains=[(0.0, "#0e1014"), (0.5, "#5b6472"), (1.0, "#eef1f6")],
        spray=[(0.0, "#6b7280"), (0.5, "#aab2bd"), (1.0, "#ffffff")],
        skier=[(0.0, "#3a0a0a"), (0.5, "#ff3b30"), (1.0, "#ffd0cc")],
        sun="#ff4d3d"),
}


def _region_of(d: str) -> str:
    """The region a path belongs to, by bbox centroid (most-specific window first)."""
    x0, y0, x1, y1 = _bbox(d)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for key in _REGION_ORDER:
        rx, ry, rw, rh = REGION_BOX[key]
        if rx <= cx <= rx + rw and ry <= cy <= ry + rh:
            return key
    return "sky"


def _grade_figure(ground: dict, paths: list[dict], grade: str) -> tuple[dict, list[dict]]:
    """Recolour the ingested figure by region level — each region its own ramp."""
    g = GRADES[grade]
    gr_ground = _grade_paint(ground, g["sky"])
    out = []
    for o in paths:
        reg = _region_of(o.get("d", ""))
        if reg == "sun":
            no = dict(o)
            if _is_hex(no.get("fill")):
                no["fill"] = g["sun"]
            if _is_hex(no.get("stroke")):
                no["stroke"] = g["sun"]
        else:
            no = _grade_paint(o, g[reg])
        out.append(no)
    return gr_ground, out


# --------------------------------------------------------------------------- #
#  Pages                                                                       #
# --------------------------------------------------------------------------- #
def _page_rebuild(b: DocumentBuilder, ground, paths, w, h) -> None:
    """The ingested drawing at native size — faithful, every object kept."""
    page = b.page("rebuild", canvas={"size": [w, h], "units": "px"},
                  coordinate_mode="absolute")
    layer = page.layer("ink")
    layer.add(copy.deepcopy(ground))
    with layer.bleed():
        for o in paths:
            layer.add(copy.deepcopy(o))


def _page_atlas(b: DocumentBuilder, clean, w, h) -> None:
    """Transformation atlas: the figure under six affine transforms, contact-sheet style."""
    pad, gap, top, cap = 48, 44, 150, 60
    cols, rows = 3, 2
    cw, ch = 820, 512
    W = pad * 2 + cols * cw + (cols - 1) * gap
    H = top + rows * ch + (rows - 1) * gap + pad

    specs = [
        ("identity", "scale-to-fit · translate", Mat3.identity()),
        ("rotate", "rotate(−12°)", Mat3.rotate(-12)),
        ("uniform scale", "scale(0.72)", Mat3.scale(0.72)),
        ("mirror", "scale(−1, 1)", Mat3.scale(-1.0, 1.0)),
        ("shear", "skewX(18°)", _shear_x(18)),
        ("non-uniform", "scale(1.0, 0.60)", Mat3.scale(1.0, 0.60)),
    ]

    page = b.page("atlas", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill=INK)
    with page.lettering():
        page.text([pad, 46, W - 2 * pad, 54], "ski_rebuilt — transformation atlas",
                  style={"font_family": FONT, "font_size": 38, "font_weight": 800,
                         "color": LIGHT, "letter_spacing": -0.5})
        page.text([pad, 104, W - 2 * pad, 30],
                  "one ingested SVG (1,332 paths) instanced as FrameForge groups "
                  "— one affine transform per cell",
                  style={"font_family": FONT, "font_size": 19, "font_weight": 500,
                         "color": MUTE})

    for i, (name, expr, X) in enumerate(specs):
        r, c = divmod(i, cols)
        cx = pad + c * (cw + gap)
        cy = top + r * (ch + gap)
        cell = [cx, cy, cw, ch]
        page.rect(cell, fill=CARD, stroke=EDGE, stroke_style={"stroke_width": 1.5})
        with page.bleed():
            _instance(page, clean, _place(cell, X, w=w, h=h, margin=0.82, reserve=cap))
        with page.lettering():
            page.text([cx + 22, cy + 18, 60, 24], f"{i + 1:02d}",
                      style={"font_family": MONO, "font_size": 18, "font_weight": 700,
                             "color": ACCENT})
            page.text([cx + 24, cy + ch - cap + 8, cw - 48, 26], name,
                      style={"font_family": FONT, "font_size": 21, "font_weight": 700,
                             "color": SLATE})
            page.text([cx + 24, cy + ch - cap + 34, cw - 48, 22], expr,
                      style={"font_family": MONO, "font_size": 16, "font_weight": 500,
                             "color": GREY})


def _page_poster(b: DocumentBuilder, paths, clean, w, h) -> None:
    """A designed composition: hero figure on a light panel + a rotated filmstrip."""
    W, H = int(w), int(h)
    m = 72
    hero_w = int(W * 0.60)
    hero = [m, m, hero_w - m, H - 2 * m]

    page = b.page("poster", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill=INK)

    # Hero: full faithful figure on its own light panel.
    page.rect(hero, fill=PAPER, stroke="#1A2230", stroke_style={"stroke_width": 2})
    with page.bleed():
        _instance(page, paths, _place(hero, Mat3.identity(), w=w, h=h, margin=0.92))

    # Right column.
    rx = hero_w + 28
    rw = W - rx - m
    with page.lettering():
        page.text([rx, m + 14, rw, 26], "FRAMEFORGE · VECTOR INGEST",
                  style={"font_family": MONO, "font_size": 17, "font_weight": 700,
                         "color": ACCENT, "letter_spacing": 2.0})
        page.text([rx, m + 50, rw, 118], "ski_rebuilt",
                  style={"font_family": FONT, "font_size": 88, "font_weight": 800,
                         "color": LIGHT, "letter_spacing": -2.0})
        page.text([rx, m + 180, rw, 156],
                  "A flattened SVG, lowered into FrameForge primitives and recomposed "
                  "— then re-instanced under affine transforms. The geometry is "
                  "authored once; each frame is a matrix.",
                  style={"font_family": FONT, "font_size": 23, "font_weight": 400,
                         "color": MUTE, "line_height": 1.45})

    page.rect([rx, m + 344, rw, 3], fill=ACCENT)

    # Filmstrip: three rotated thumbnails of the clean figure.
    strip_y = m + 376
    strip_h = H - strip_y - m
    fw = (rw - 2 * 24) / 3
    for j, ang in enumerate((-8.0, 0.0, 8.0)):
        fx = rx + j * (fw + 24)
        frame = [fx, strip_y, fw, strip_h]
        page.rect(frame, fill="#161C26", stroke="#283042",
                  stroke_style={"stroke_width": 1.5})
        with page.bleed():
            _instance(page, clean, _place(frame, Mat3.rotate(ang), w=w, h=h,
                                          margin=0.80, reserve=40))
        with page.lettering():
            page.text([fx + 14, strip_y + strip_h - 34, fw - 28, 22],
                      f"rotate({ang:+.0f}°)" if ang else "rotate(0°)",
                      style={"font_family": MONO, "font_size": 14, "font_weight": 600,
                             "color": MUTE})


def _page_region_studio(b: DocumentBuilder, paths, w, h) -> None:
    """Region studio: select · clip · transform a sub-window of the ingested figure."""
    pad, gap, top, cap = 48, 40, 152, 58
    cols = 4
    cw, ch = 600, 452
    W = pad * 2 + cols * cw + (cols - 1) * gap
    lab_h = 64
    rowB_y = top + ch + gap + lab_h
    chB = 452
    H = rowB_y + chB + pad

    page = b.page("region", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill=INK)
    with page.lettering():
        page.text([pad, 46, W - 2 * pad, 54], "ski_rebuilt — region studio",
                  style={"font_family": FONT, "font_size": 38, "font_weight": 800,
                         "color": LIGHT, "letter_spacing": -0.5})
        page.text([pad, 104, W - 2 * pad, 30],
                  "the ingested figure is per-object addressable — select a window, "
                  "clip to it, transform only that region",
                  style={"font_family": FONT, "font_size": 19, "font_weight": 500,
                         "color": MUTE})

    # Row A — clip each region window and zoom it to fill a tile (region focus).
    for i, (name, region) in enumerate(REGIONS):
        cx = pad + i * (cw + gap)
        cell = [cx, top, cw, ch]
        page.rect(cell, fill=CARD, stroke=EDGE, stroke_style={"stroke_width": 1.5})
        focus = [cx, top, cw, ch - cap]
        sub = _select(paths, region)
        with page.bleed():
            _instance(page, sub, _region_to_cell(region, cell, reserve=cap),
                      clip=clip_rect(focus))
        rx, ry, rw, rh = region
        with page.lettering():
            page.text([cx + 22, top + 16, cw - 44, 24], f"{i + 1:02d}  clip",
                      style={"font_family": MONO, "font_size": 15, "font_weight": 700,
                             "color": ACCENT})
            page.text([cx + 24, top + ch - cap + 8, cw - 48, 26], name,
                      style={"font_family": FONT, "font_size": 21, "font_weight": 700,
                             "color": SLATE})
            page.text([cx + 24, top + ch - cap + 34, cw - 48, 22],
                      f"[{rx}, {ry}, {rw}, {rh}]  ·  {len(sub)} objs",
                      style={"font_family": MONO, "font_size": 14, "font_weight": 500,
                             "color": GREY})

    # Row label.
    with page.lettering():
        page.text([pad, top + ch + gap + 14, W - 2 * pad, 34],
                  "→ select the skier region, then transform it in isolation "
                  "(the rest of the drawing is untouched)",
                  style={"font_family": FONT, "font_size": 20, "font_weight": 600,
                         "color": LIGHT})

    # Row B — extract ONE region (skier) and experiment with it independently.
    skier = _select(paths, REGIONS[0][1])
    region = REGIONS[0][1]
    experiments = [
        ("extracted", Mat3.identity()),
        ("scale(1.5)", Mat3.scale(1.5)),
        ("rotate(+18°)", Mat3.rotate(18)),
    ]
    bcw = (W - 2 * pad - 2 * gap) / 3
    rcx, rcy, rrw, rrh = region
    pivot = Mat3.translate(rcx + rrw / 2, rcy + rrh / 2)
    unpivot = Mat3.translate(-(rcx + rrw / 2), -(rcy + rrh / 2))
    for j, (lbl, X) in enumerate(experiments):
        cx = pad + j * (bcw + gap)
        cell = [cx, rowB_y, bcw, chB]
        page.rect(cell, fill="#161C26", stroke="#283042", stroke_style={"stroke_width": 1.5})
        focus = [cx, rowB_y, bcw, chB - cap]
        base = _region_to_cell(region, cell, reserve=cap, margin=0.9)
        # apply the experiment about the region's own center, in source space
        matrix = base @ pivot @ X @ unpivot
        with page.bleed():
            _instance(page, skier, matrix, clip=clip_rect(focus))
        with page.lettering():
            page.text([cx + 22, rowB_y + 16, bcw - 44, 24], lbl,
                      style={"font_family": MONO, "font_size": 16, "font_weight": 700,
                             "color": ACCENT})


SHOT_GRADE = "alpenglow"


def _page_shot(b: DocumentBuilder, ground, paths, w, h, grade: str = SHOT_GRADE) -> None:
    """The perfect shot: the figure recoloured by region, full-bleed, with a vignette."""
    W, H = int(w), int(h)
    g = GRADES[grade]
    gr_ground, graded = _grade_figure(ground, paths, grade)
    page = b.page("shot", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill=g["sky"][0][1])     # deep base so no gaps show
    layer = page.layer("graded")
    layer.add(gr_ground)
    with layer.bleed():
        for o in graded:
            layer.add(o)
        # Cinematic vignette: transparent centre → dark edges, on top of the art.
        page.rect([0, 0, W, H], fill=radial_gradient(
            [(rgba("#05030f", 0.0), 0.46), (rgba("#05030f", 0.30), 0.82),
             (rgba("#05030f", 0.62), 1.0)], at="52% 44%", shape="ellipse"))


def _page_grades(b: DocumentBuilder, ground, paths, w, h) -> None:
    """Grade options: the figure recoloured under each distinct region grade — pick one."""
    pad, gap, top, cap = 48, 40, 150, 58
    names = list(GRADES.keys())
    cols = len(names)
    cw, ch = 820, 512
    W = pad * 2 + cols * cw + (cols - 1) * gap
    Hh = top + ch + pad

    page = b.page("grades", canvas={"size": [W, Hh], "units": "px"},
                  coordinate_mode="absolute")
    page.rect([0, 0, W, Hh], fill=INK)
    with page.lettering():
        page.text([pad, 46, W - 2 * pad, 54], "ski_rebuilt — grade options",
                  style={"font_family": FONT, "font_size": 38, "font_weight": 800,
                         "color": LIGHT, "letter_spacing": -0.5})
        page.text([pad, 104, W - 2 * pad, 30],
                  "distinct colouring applied by region level (sky · mountains · spray · "
                  "skier · sun) — same geometry, three grades",
                  style={"font_family": FONT, "font_size": 19, "font_weight": 500,
                         "color": MUTE})

    for i, name in enumerate(names):
        cx = pad + i * (cw + gap)
        cell = [cx, top, cw, ch]
        gr_ground, graded = _grade_figure(ground, paths, name)
        page.rect(cell, fill=GRADES[name]["sky"][0][1])
        focus = [cx, top, cw, ch - cap]
        matrix = _region_to_cell([0, 0, w, h], cell, reserve=cap, margin=1.0)
        with page.bleed():
            _instance(page, [gr_ground] + graded, matrix, clip=clip_rect(focus))
        marker = "  ★ shot" if name == SHOT_GRADE else ""
        with page.lettering():
            page.text([cx + 22, top + 16, cw - 44, 24], f"{i + 1:02d}",
                      style={"font_family": MONO, "font_size": 16, "font_weight": 700,
                             "color": LIGHT})
            page.text([cx + 24, top + ch - cap + 12, cw - 48, 30], name + marker,
                      style={"font_family": FONT, "font_size": 22, "font_weight": 700,
                             "color": LIGHT})


def build() -> DocumentBuilder:
    """Assemble the six-page composition (MCP entry point)."""
    ground, paths, clean, w, h = _ingest()
    b = DocumentBuilder(title="ski_rebuilt — composition & transformations", lang="en")
    _page_rebuild(b, ground, paths, w, h)
    _page_atlas(b, clean, w, h)
    _page_poster(b, paths, clean, w, h)
    _page_region_studio(b, paths, w, h)
    _page_shot(b, ground, paths, w, h)
    _page_grades(b, ground, paths, w, h)
    return b


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "ski_rebuilt"))
    ap.add_argument("--render", action="store_true", help="also write per-page SVG files")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    b = build()
    model = b.build()

    report = validate_static_rules(model)
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity == "warning"]
    print(f"pages: {len(model.pages)}  |  errors: {len(errors)}  warnings: {len(warnings)}")
    for i in errors + warnings:
        print(f"  [{i.severity}] {i.rule}: {i.message}")

    yaml_path = os.path.join(args.out, "ski_rebuilt.fg.yaml")
    with open(yaml_path, "w", encoding="utf-8") as fh:
        fh.write(serialize(model, format="yaml"))
    print("wrote", os.path.relpath(yaml_path, ROOT))

    if args.render:
        svgs = render_page_svgs(model)
        for page, svg in zip(model.pages, svgs):
            sp = os.path.join(args.out, f"{page.id}.svg")
            with open(sp, "w", encoding="utf-8") as fh:
                fh.write(svg)
            print("wrote", os.path.relpath(sp, ROOT))

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
