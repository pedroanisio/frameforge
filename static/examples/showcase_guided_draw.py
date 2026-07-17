"""Showcase — guided draw: a line-art trace becomes the under-drawing, and we
paint a finished colour illustration ON TOP of it (POC-04's guide workflow).

Pipeline: ingest the skier line-art -> drop it to a low-opacity guide
(`as_guide`) -> author native FrameForge colour (gradient sky, a glowing sun,
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

from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402
from guided_paint import fade, glow, haze, linear, radial, soft_shadow, stop, vignette, wash  # noqa: E402
from poc3_ingest_compose import place  # noqa: E402
from poc4_color_and_guide import as_guide  # noqa: E402

Obj = dict[str, Any]


def author_skier(src: tuple[int, int]) -> list[Obj]:
    """A painted sunset-alpine scene, drawn against the skier guide.

    Built in passes like a real illustration: base local colour, then form
    gradients, then atmosphere (glow / haze / wash), then a vignette to seat the
    composition — all gradient/alpha based so it survives cairosvg rasterisation.
    """
    w, h = src

    def fx(x): return x * w
    def fy(y): return y * h

    sky = linear([stop("#2E4E7C", 0.0), stop("#6E8FBC", 0.40),
                  stop("#E9B98A", 0.82), stop("#F7D3A0", 1.0)], "180deg")
    snow = linear([stop("#FCFDFF", 0.0), stop("#D4E0F2", 0.55), stop("#AEC2E0", 1.0)], "200deg")
    ridge = linear([stop("#33456B", 0.0), stop("#212E4C", 1.0)], "180deg")
    slope_pts = [[fx(0.0), fy(0.82)], [fx(0.42), fy(0.60)], [fx(0.72), fy(0.40)],
                 [fx(1.0), fy(0.16)], [fx(1.0), fy(1.0)], [fx(0.0), fy(1.0)]]
    return [
        # --- base sky + atmosphere behind everything ---
        {"type": "rect", "box": [0, 0, w, h], "fill": sky},
        haze([0, 0, w, fy(0.6)], "#F3D8B0", opacity=0.30, angle="180deg"),     # warm horizon glow
        *glow(fx(0.452), fy(0.455), fx(0.052), "#FFF1CE", core=0.98, spread=3.0),  # the sun
        # --- the snow slope, with a rim of light along the ridge ---
        {"type": "polygon", "points": slope_pts, "fill": snow},
        {"type": "polyline",
         "points": [[fx(0.0), fy(0.82)], [fx(0.42), fy(0.60)], [fx(0.72), fy(0.40)], [fx(1.0), fy(0.16)]],
         "stroke": fade("#FFF6E0", 0.85), "stroke_style": {"stroke_width": 3.0, "stroke_linecap": "round"}},
        haze([0, fy(0.45), w, fy(0.55)], "#BFD2EE", opacity=0.22, angle="0deg"),   # snow distance haze
        # --- dark alpine ridge, lower-left ---
        {"type": "polygon",
         "points": [[fx(0.0), fy(0.86)], [fx(0.12), fy(0.78)], [fx(0.22), fy(0.84)],
                    [fx(0.34), fy(0.76)], [fx(0.46), fy(0.85)], [fx(0.46), fy(1.0)], [fx(0.0), fy(1.0)]],
         "fill": ridge},
        # --- powder spray: soft, transparent-edged (no blur filter) ---
        {"type": "ellipse", "center": [fx(0.80), fy(0.22)], "rx": fx(0.18), "ry": fy(0.22),
         "fill": radial([stop(fade("#FFFFFF", 0.65), 0.0), stop(fade("#DCEBFF", 0.25), 0.6),
                         stop(fade("#DCEBFF", 0.0), 1.0)])},
        # --- the skier: cast shadow on snow + warm jacket ---
        soft_shadow(fx(0.60), fy(0.46), fx(0.06), fy(0.018), color="#22324E", strength=0.35),
        {"type": "polygon",
         "points": [[fx(0.600), fy(0.31)], [fx(0.632), fy(0.315)], [fx(0.636), fy(0.40)], [fx(0.604), fy(0.40)]],
         "fill": linear([stop("#E0573F", 0.0), stop("#B5371F", 1.0)], "160deg")},
        # --- finishing: unifying warm wash + vignette to seat the frame ---
        wash([0, 0, w, h], "#FFE9C8", "#2A3A60", opacity=0.12, angle="160deg"),
        vignette(w, h, color="#0B1220", strength=0.42),
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
    from frameforge.vision.infrastructure.vectorize import raster_to_objects
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
