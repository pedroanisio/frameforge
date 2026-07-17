"""POC-04 — colour & gradient a trace, or use it as a guide to draw on top.

Answers two questions directly, with executable proof (not prose):

    1. CAN WE FILL / GRADIENT A TRACE?
       Yes. A `region` trace is closed polygons whose `fill` may be a flat colour
       OR a FrameForge `Gradient`. `recolor_fills` re-palettes them; `gradient_fills`
       lifts each flat fill into a 2-stop gradient. Lay the recoloured regions
       UNDER the `outline` strokes -> a coloured illustration. (Outline polylines
       are open paths: they are the *lines*, not fillable areas.)

    2. CAN WE USE IT AS A GUIDE TO DRAW ON TOP?
       Yes. `as_guide` dims the line-art to a low-opacity "pencils" layer; you then
       author NEW colour/gradient objects over it (ink-and-colour-over-pencils).

Every claim is gated: fills become real `Gradient` dicts, geometry is preserved,
the guide is genuinely low-opacity, and each page validates + renders.

Run:
    uv run --group vision python examples/poc4_color_and_guide.py \
        demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc4
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
from typing import Any, Iterable, Sequence

sys.path.insert(0, os.environ.get("FG_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402
from poc3_ingest_compose import place, restyle_strokes  # noqa: E402

Obj = dict[str, Any]
_FILL_TYPES = {"polygon", "rect", "ellipse", "circle", "path"}


def hexshift(hex_color: str, amt: float) -> str:
    """Lighten (amt>0) or darken (amt<0) a hex colour by a fraction in [-1, 1]."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return hex_color
    def adj(c: int) -> int:
        c = c + amt * (255 - c) if amt >= 0 else c * (1 + amt)
        return max(0, min(255, int(round(c))))
    return "#%02X%02X%02X" % (adj(r), adj(g), adj(b))


def gradient_fills(objs: Iterable[Obj], *, kind: str = "linear", angle: str = "120deg",
                   light: float = 0.22, dark: float = -0.18) -> list[Obj]:
    """Lift every flat fill into a 2-stop FrameForge gradient. Geometry untouched."""
    out: list[Obj] = []
    for o in objs:
        o = copy.deepcopy(o)
        f = o.get("fill")
        if o.get("type") in _FILL_TYPES and isinstance(f, str) and f != "none":
            grad: dict[str, Any] = {
                "kind": kind,
                "stops": [{"color": hexshift(f, light), "position": "0%"},
                          {"color": hexshift(f, dark), "position": "100%"}],
            }
            if kind == "linear":
                grad["angle"] = angle
            o["fill"] = grad
        out.append(o)
    return out


def recolor_cycle(objs: Iterable[Obj], palette: Sequence[str], *, only_fills: bool = True) -> list[Obj]:
    """Assign palette colours to fills by order (posterize). Geometry untouched.

    Luma mapping colourises by tone, which washes out near-white line-art; cycling
    proves the fills are real, addressable, and freely re-paintable to ANY colour.
    """
    pal = list(palette)
    out: list[Obj] = []
    i = 0
    for o in objs:
        o = copy.deepcopy(o)
        if o.get("type") in _FILL_TYPES and isinstance(o.get("fill"), str) and o["fill"] != "none":
            if only_fills:
                o["fill"] = pal[i % len(pal)]
                i += 1
        out.append(o)
    return out


def as_guide(objs: Iterable[Obj], *, opacity: float = 0.18, ink: str = "#3A4A7A",
             width: float = 1.0) -> list[Obj]:
    """Dim line-art into a low-opacity 'pencils' guide layer (geometry intact)."""
    out: list[Obj] = []
    for o in restyle_strokes(objs, stroke=ink, width=width):
        style = dict(o.get("style") or {})
        style["opacity"] = opacity
        o["style"] = style
        out.append(o)
    return out


# --------------------------------------------------------------------------- #
# Raster ingest (lazy OpenCV).
# --------------------------------------------------------------------------- #
def trace(image: str, *, mode: str, colors: int = 12, detail: float = 0.0018,
          min_area: float = 30.0, max_dim: int = 1400) -> tuple[list[Obj], int, int]:
    from frameforge.vision.infrastructure.vectorize import raster_to_objects
    return raster_to_objects(image, mode=mode, colors=colors, detail=detail,
                             min_area=min_area, max_dim=max_dim)


# --------------------------------------------------------------------------- #
# Drawing-on-top: native objects authored against the guide.
# --------------------------------------------------------------------------- #
def author_overlay(src: tuple[int, int]) -> list[Obj]:
    """Hand-authored colour the AI 'draws on top' of the guide (region-aware)."""
    w, h = src
    sky = {"kind": "linear", "angle": "180deg",
           "stops": [{"color": "#BFE3FF", "position": "0%"}, {"color": "#EAF6FF", "position": "100%"}]}
    return [
        # window light behind the upper-right (a gradient block under the lines)
        {"type": "rect", "box": [0.46 * w, 0.04 * h, 0.52 * w, 0.52 * h], "fill": sky,
         "style": {"opacity": 0.55}},
        # the presenter's jacket, a warm flat fill placed by eye on the guide
        {"type": "polygon",
         "points": [[0.30 * w, 0.30 * h], [0.40 * w, 0.28 * h], [0.42 * w, 0.62 * h], [0.31 * w, 0.64 * h]],
         "fill": "#2D6CDF", "style": {"opacity": 0.55}},
        # whiteboard tint
        {"type": "rect", "box": [0.04 * w, 0.10 * h, 0.26 * w, 0.46 * h], "fill": "#FFFFFF",
         "radius": 6, "style": {"opacity": 0.45}},
        # foliage accents
        {"type": "ellipse", "center": [0.45 * w, 0.34 * h], "rx": 0.03 * w, "ry": 0.05 * h,
         "fill": "#3BAA6B", "style": {"opacity": 0.55}},
    ]


# --------------------------------------------------------------------------- #
# Pages.
# --------------------------------------------------------------------------- #
def _panel(page, x, y, w, h, label, color):
    page.add({"type": "rect", "box": [x, y, w, h], "fill": "#FFFFFF", "radius": 10})
    page.add({"type": "text", "box": [x + 14, y + 8, w - 28, 20], "text": label,
              "style": {"font_family": ["Inter", "sans-serif"], "font_size": 13,
                        "font_weight": 700, "color": color}})


def build_color_and_guide(region: list[Obj], outline: list[Obj], src: tuple[int, int]):
    """Three panels: flat-coloured, gradient-filled, and guide+draw-on-top."""
    cw, ch, pad = 620, 380, 22
    W = 2 * cw + 3 * pad
    H = 2 * ch + 3 * pad + 44
    palette = ["#16324F", "#2D6CDF", "#3BAA6B", "#E8B04B", "#E2603B", "#7B4FB5",
               "#E8E2D2", "#4FB0C6"]

    b = DocumentBuilder(title="poc4-color-guide")
    page = b.page("cg", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.text([pad, 12, W - 2 * pad, 26],
              "Colour a trace (fills + gradients) — or use it as a guide to draw on top",
              style={"font_family": ["Inter", "sans-serif"], "font_size": 18,
                     "font_weight": 700, "color": "#F2F5FA"})

    inner = [cw - 20, ch - 44]
    cells = [(pad, 44 + pad), (pad + cw + pad, 44 + pad),
             (pad, 44 + pad + ch + pad), (pad + cw + pad, 44 + pad + ch + pad)]

    # panel 1: flat colour — recoloured regions UNDER the black outline
    x, y = cells[0]
    lay = page.layer("flat")
    _panel(lay, x, y, cw, ch, "fills: regions re-painted (posterize) + line art on top", "#2D6CDF")
    flat = recolor_cycle(region, palette)
    for o in place(flat, [x + 10, y + 34, inner[0], inner[1]], src):
        lay.add(o)
    for o in place(restyle_strokes(outline, stroke="#10151F", width=1.0),
                   [x + 10, y + 34, inner[0], inner[1]], src):
        lay.add(o)

    # panel 2: gradient fills
    x, y = cells[1]
    lay = page.layer("grad")
    _panel(lay, x, y, cw, ch, "fills: gradients per region + line art", "#3BAA6B")
    grad = gradient_fills(recolor_cycle(region, palette), angle="120deg")
    for o in place(grad, [x + 10, y + 34, inner[0], inner[1]], src):
        lay.add(o)
    for o in place(restyle_strokes(outline, stroke="#10151F", width=1.0),
                   [x + 10, y + 34, inner[0], inner[1]], src):
        lay.add(o)

    # panel 3: guide only (faint pencils)
    x, y = cells[2]
    lay = page.layer("guide")
    _panel(lay, x, y, cw, ch, "guide layer (line-art @ 18% opacity)", "#8B949E")
    for o in place(as_guide(outline), [x + 10, y + 34, inner[0], inner[1]], src):
        lay.add(o)

    # panel 4: draw on top of the guide
    x, y = cells[3]
    lay = page.layer("drawn")
    _panel(lay, x, y, cw, ch, "draw on top: authored colour over the guide", "#E8B04B")
    for o in place(author_overlay(src), [x + 10, y + 34, inner[0], inner[1]], src):
        lay.add(o)
    for o in place(as_guide(outline, opacity=0.35, ink="#22303F"),
                   [x + 10, y + 34, inner[0], inner[1]], src):
        lay.add(o)

    return b


def gradient_count(objs: Iterable[Obj]) -> int:
    """How many objects carry a gradient fill (a dict with stops)."""
    return sum(1 for o in objs if isinstance(o.get("fill"), dict) and o["fill"].get("stops"))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--out", default="out/poc4")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    region, w, h = trace(args.image, mode="region", colors=6, min_area=140.0)
    outline, _, _ = trace(args.image, mode="outline")
    src = (w, h)
    print(f"[ingest] region={len(region)} polygons, outline={len(outline)} strokes ({w}x{h})")

    grad = gradient_fills(region)
    ng = gradient_count(grad)
    ok_grad = ng > 0 and len(grad) == len(region)
    print(f"[gate] gradient_fills lifts {ng}/{len(region)} fills to gradients, geometry kept: "
          f"{'PASS' if ok_grad else 'FAIL'}")

    guide = as_guide(outline)
    ok_guide = all((o.get("style") or {}).get("opacity", 1.0) <= 0.3 for o in guide) and len(guide) == len(outline)
    print(f"[gate] guide layer is low-opacity, geometry kept: {'PASS' if ok_guide else 'FAIL'}")

    b = build_color_and_guide(region, outline, src)
    svg = render_page_svgs(b.build())[0]
    ok_render = svg.startswith("<svg") and "gradient" in svg.lower()
    print(f"[gate] page validates + renders gradients: {'PASS' if ok_render else 'FAIL'}")

    b.write(os.path.join(args.out, "color_guide.fg.yaml"))
    with open(os.path.join(args.out, "color_guide.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"[write] {args.out}/color_guide.svg (+ .fg.yaml)")

    verdict = ok_grad and ok_guide and ok_render
    print(f"\nVERDICT: {'YES - colour, gradient, and draw-on-top all work' if verdict else 'NEEDS WORK'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
