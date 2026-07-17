"""POC-05 — the whole loop, together: ingest → coach gate → style → compose.

Wires the session's pieces into ONE pipeline on a demo raster:

    demo/*.jpeg
      │  coach.ingest (vectorize)            → editable objects (outline + region)
      │  coach.create_plan / validate_order  → layer discipline (printed)
      │  coach.to_silhouette                 → readability gate + stage_rubric
      │  coach.resolve_style(hybrid)         → the style grammar
      │  coach.recolor_to_style + gradientize→ region fills re-skinned to the palette
      └─ one composed page: ingested · silhouette gate · styled — every step gated.

Run (needs the vision group for the OpenCV trace):
    uv run --group vision python examples/poc5_coach_ingest.py \
        demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc5
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get("FG_ROOT", ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402
from frameforge.coach import (  # noqa: E402
    create_plan, gradientize, ingest, recolor_to_style, resolve_style, stage_rubric,
    to_silhouette, validate_order,
)
from poc3_ingest_compose import place  # noqa: E402  — reuse the layout transform

Obj = dict[str, Any]
DEFAULT_IMG = os.path.join(ROOT, "demo", "Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg")
DARK, PAPER, MUTE = "#0E1116", "#F6F3EC", "#8B949E"
FONT = ["Inter", "Helvetica", "Arial", "sans-serif"]


def _txt(layer, box, text, size, color, weight=400):
    layer.add({"type": "text", "box": list(box), "text": text,
               "style": {"font_family": FONT, "font_size": size, "font_weight": weight, "color": color}})


def _silhouette_objs(region: list[Obj], src) -> list[Obj]:
    """Run the coach gate for real: region fills → black-on-white via to_silhouette."""
    w, h = src
    sub = DocumentBuilder(title="sil")
    sp = sub.page("s", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    sp.layer("bg").rect([0, 0, w, h], fill="#FFFFFF", decorative=True)
    lay = sp.layer("r")
    for o in region:
        lay.add(o)
    dumped = to_silhouette(sub).model_dump(by_alias=True, exclude_none=True)
    return [o for L in dumped["pages"][0]["layers"] for o in L.get("objects", [])]


def build_page(outline, region, src, style):
    cw, ch, pad = 488, 470, 24
    W, H = 3 * cw + 4 * pad, 44 + ch + 2 * pad
    b = DocumentBuilder(title="poc5-ingest-to-styled")
    page = b.page("loop", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill=DARK)
    _txt(page, [pad, 12, W - 2 * pad, 26],
         f"Ingest → gate → style — one loop  (style: {style.name})", 18, "#F2F5FA", 700)
    inner = [cw - 20, ch - 56]
    boxes = [pad + i * (cw + pad) for i in range(3)]
    y = 44 + pad

    # panel 1 — ingested line-art (as traced, inked)
    p1 = page.layer("ingested")
    p1.add({"type": "rect", "box": [boxes[0], y, cw, ch], "fill": PAPER, "radius": 10})
    _txt(p1, [boxes[0] + 14, y + 8, cw - 28, 20], "1 · ingested  (vectorized objects)", 13, "#1E2440", 700)
    for o in place(recolor_to_style(outline, style, width=1.2),
                   [boxes[0] + 10, y + 40, inner[0], inner[1]], src):
        p1.add(o)

    # panel 2 — silhouette gate (coach.to_silhouette) + rubric
    p2 = page.layer("gate")
    p2.add({"type": "rect", "box": [boxes[1], y, cw, ch], "fill": "#FFFFFF", "radius": 10})
    _txt(p2, [boxes[1] + 14, y + 8, cw - 28, 20], "2 · silhouette gate  (readable as a shape?)", 13, "#11151C", 700)
    for o in place(_silhouette_objs(region, src), [boxes[1] + 10, y + 40, inner[0], inner[1]], src):
        p2.add(o)
    ry = y + ch - 92
    for line in stage_rubric("silhouette")[:3]:
        _txt(p2, [boxes[1] + 16, ry, cw - 32, 18], "• " + line, 9.5, MUTE)
        ry += 16

    # panel 3 — styled (region recolour + gradient, line-art on top)
    p3 = page.layer("styled")
    p3.add({"type": "rect", "box": [boxes[2], y, cw, ch], "fill": "#0B2A4A", "radius": 10})
    _txt(p3, [boxes[2] + 14, y + 8, cw - 28, 20], "3 · styled  (palette + gradients, lines on top)", 13, "#8FD3FF", 700)
    reg = gradientize(recolor_to_style(region, style))
    for o in place(reg, [boxes[2] + 10, y + 40, inner[0], inner[1]], src):
        p3.add(o)
    for o in place(recolor_to_style(outline, style, width=1.0),
                   [boxes[2] + 10, y + 40, inner[0], inner[1]], src):
        p3.add(o)
    return b


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?", default=DEFAULT_IMG)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "poc5"))
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    style = resolve_style("comic_ink", "blueprint")
    layers_ok = validate_order(create_plan().layers) == []
    outline, w, h = ingest(args.image, mode="outline", max_dim=1400)
    region, _, _ = ingest(args.image, mode="region", colors=6, min_area=140.0, max_dim=1400)
    src = (w, h)
    print(f"[ingest] outline={len(outline)} strokes, region={len(region)} polygons ({w}x{h})")
    print(f"[coach] style={style.name}  layers_valid={layers_ok}")

    # gates
    inv = [o.get("points") for o in region] == [o.get("points") for o in recolor_to_style(region, style)]
    print(f"[gate] recolor_to_style preserves geometry: {'PASS' if inv else 'FAIL'}")
    skinned = recolor_to_style(region, style)
    on_palette = all(o["fill"] in style.palette for o in skinned if isinstance(o.get("fill"), str))
    print(f"[gate] region fills mapped onto the style palette: {'PASS' if on_palette else 'FAIL'}")
    sil_n = len(_silhouette_objs(region, src))
    print(f"[gate] silhouette gate produced a flattened subject ({sil_n} objs): {'PASS' if sil_n else 'FAIL'}")

    b = build_page(outline, region, src, style)
    svg = render_page_svgs(b.build())[0]
    ok_render = svg.startswith("<svg") and "gradient" in svg.lower()
    print(f"[gate] composed page validates + renders gradients: {'PASS' if ok_render else 'FAIL'}")

    b.write(os.path.join(args.out, "ingest_to_styled.fg.yaml"))
    with open(os.path.join(args.out, "ingest_to_styled.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"[write] {args.out}/ingest_to_styled.svg (+ .fg.yaml)")

    verdict = layers_ok and inv and on_palette and bool(sil_n) and ok_render
    print(f"\nVERDICT: {'WIRED — ingest x coach x style x gate compose' if verdict else 'NEEDS WORK'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
