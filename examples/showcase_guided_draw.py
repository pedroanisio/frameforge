"""Showcase — guided draw: a line-art trace becomes the under-drawing, and we
paint a finished colour illustration ON TOP of it (POC-04's guide workflow).

Pipeline: ingest the skier line-art -> drop it to a low-opacity guide
(`as_guide`) -> author native FrameGraph colour (gradient sky, a glowing sun,
the snow slope, mountains, spray, the skier's jacket) positioned against the
guide -> re-lay the guide as the final "ink". The output is a deliberate
illustration, not a recoloured trace.

    uv run --group vision python examples/showcase_guided_draw.py \
        demo/Gemini_Generated_Image_mq7v2pmq7v2pmq7v.jpeg --out out/showcase
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Sequence

sys.path.insert(0, os.environ.get("FG_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framegraph.sdk import DocumentBuilder, render_page_svgs  # noqa: E402
from poc3_ingest_compose import place  # noqa: E402
from poc4_color_and_guide import as_guide  # noqa: E402

Obj = dict[str, Any]


def author_skier(src: tuple[int, int]) -> list[Obj]:
    """Native colour, drawn against the skier guide (sunset-alpine palette)."""
    w, h = src
    sky = {"kind": "linear", "angle": "180deg",
           "stops": [{"color": "#34537F", "position": "0%"},
                     {"color": "#8FA9C9", "position": "52%"},
                     {"color": "#F6C98C", "position": "100%"}]}
    snow = {"kind": "linear", "angle": "205deg",
            "stops": [{"color": "#FBFDFF", "position": "0%"}, {"color": "#C3D2EA", "position": "100%"}]}
    sun_glow = {"kind": "radial", "at": "50% 50%",
                "stops": [{"color": "#FFF6DA", "position": "0%"},
                          {"color": "#FFE3A6", "position": "55%"},
                          {"color": "#F6C98C", "position": "100%"}]}
    spray = {"kind": "linear", "angle": "150deg",
             "stops": [{"color": "#FFFFFF", "position": "0%"}, {"color": "#DCEBFF", "position": "100%"}]}

    def fx(x): return x * w
    def fy(y): return y * h
    return [
        # sky fills the frame
        {"type": "rect", "box": [0, 0, w, h], "fill": sky},
        # glowing sun behind the drawn circle (aligned to the guide's circle)
        {"type": "ellipse", "center": [fx(0.452), fy(0.455)], "rx": fx(0.052), "ry": fx(0.052),
         "fill": sun_glow, "style": {"opacity": 0.95}},
        # soft outer halo
        {"type": "ellipse", "center": [fx(0.452), fy(0.455)], "rx": fx(0.10), "ry": fx(0.10),
         "fill": sun_glow, "style": {"opacity": 0.28}},
        # the snow slope (below the ridge sweeping up to the right)
        {"type": "polygon",
         "points": [[fx(0.0), fy(0.82)], [fx(0.42), fy(0.60)], [fx(0.72), fy(0.40)],
                    [fx(1.0), fy(0.16)], [fx(1.0), fy(1.0)], [fx(0.0), fy(1.0)]],
         "fill": snow},
        # dark alpine ridge, lower-left
        {"type": "polygon",
         "points": [[fx(0.0), fy(0.86)], [fx(0.12), fy(0.78)], [fx(0.22), fy(0.84)],
                    [fx(0.34), fy(0.76)], [fx(0.46), fy(0.85)], [fx(0.46), fy(1.0)], [fx(0.0), fy(1.0)]],
         "fill": "#2B3A5C", "style": {"opacity": 0.92}},
        # powder spray around the skier (upper-right)
        {"type": "ellipse", "center": [fx(0.80), fy(0.22)], "rx": fx(0.17), "ry": fy(0.20),
         "fill": spray, "style": {"opacity": 0.45}},
        # the skier's jacket, a small warm accent on the figure's torso
        {"type": "polygon",
         "points": [[fx(0.600), fy(0.31)], [fx(0.632), fy(0.315)], [fx(0.636), fy(0.40)], [fx(0.604), fy(0.40)]],
         "fill": "#C8472F", "style": {"opacity": 0.85}},
    ]


def build_showcase(guide_objs: list[Obj], src: tuple[int, int]):
    """A 3-beat story page: guide -> authored colour -> final composite."""
    aw, ah = 880, 491                       # 16:9 art tiles
    pad = 24
    W = aw + 2 * pad
    H = 3 * ah + 4 * pad + 70
    b = DocumentBuilder(title="showcase-guided-draw")
    page = b.page("guided", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.text([pad, 20, W - 2 * pad, 34],
              "Guided draw: a line-art trace becomes the under-drawing for a painted illustration",
              style={"font_family": ["Inter", "sans-serif"], "font_size": 22, "font_weight": 800,
                     "color": "#F2F5FA"})

    tiles = [
        ("1 - guide (line-art @ 16% opacity)", "#8B949E", "guide"),
        ("2 - draw on top (native colour, no lines)", "#3FB7EB", "paint"),
        ("3 - final (colour + guide as ink)", "#3FB950", "final"),
    ]
    for i, (label, color, kind) in enumerate(tiles):
        x, y = pad, 70 + pad + i * (ah + pad)
        layer = page.layer(kind)
        layer.add({"type": "rect", "box": [x, y, aw, ah], "fill": "#F3EFE6", "radius": 10})
        box = [x + 8, y + 30, aw - 16, ah - 38]
        if kind == "guide":
            for o in place(as_guide(guide_objs, opacity=0.16, ink="#2A3550"), box, src):
                layer.add(o)
        elif kind == "paint":
            for o in place(author_skier(src), box, src):
                layer.add(o)
        else:
            for o in place(author_skier(src), box, src):
                layer.add(o)
            for o in place(as_guide(guide_objs, opacity=0.7, ink="#101728", width=1.2), box, src):
                layer.add(o)
        layer.add({"type": "text", "box": [x + 14, y + 7, aw - 28, 20], "text": label,
                   "style": {"font_family": ["Inter", "sans-serif"], "font_size": 13,
                             "font_weight": 700, "color": color}})
    return b


def build_hero(guide_objs: list[Obj], src: tuple[int, int]):
    """A single full-bleed final, for the showcase image."""
    W, H = 1376, 768
    b = DocumentBuilder(title="showcase-guided-draw-hero")
    page = b.page("hero", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    layer = page.layer("art")
    box = [0, 0, W, H]
    for o in place(author_skier(src), box, src):
        layer.add(o)
    for o in place(as_guide(guide_objs, opacity=0.72, ink="#101728", width=1.2), box, src):
        layer.add(o)
    return b


def trace(image: str):
    from framegraph.vision.infrastructure.vectorize import raster_to_objects
    return raster_to_objects(image, mode="outline", detail=0.0015, min_area=16.0, max_dim=1500)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--out", default="out/showcase")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    guide, w, h = trace(args.image)
    src = (w, h)
    print(f"[ingest] guide={len(guide)} strokes ({w}x{h})")

    story = build_showcase(guide, src)
    hero = build_hero(guide, src)
    story_svg = render_page_svgs(story.build())[0]
    hero_svg = render_page_svgs(hero.build())[0]
    ok = story_svg.startswith("<svg") and "gradient" in story_svg.lower() and hero_svg.startswith("<svg")
    print(f"[gate] story + hero validate and carry authored gradients: {'PASS' if ok else 'FAIL'}")

    story.write(os.path.join(args.out, "guided_draw_story.fg.yaml"))
    for name, svg in (("guided_draw_story", story_svg), ("guided_draw_hero", hero_svg)):
        with open(os.path.join(args.out, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print(f"[write] {args.out}/guided_draw_story.svg, guided_draw_hero.svg")
    print(f"\nVERDICT: {'guided draw showcase rendered' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
