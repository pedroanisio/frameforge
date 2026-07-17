#!/usr/bin/env python3
"""Coach, end-to-end, with the new paint layer — raster → on-brand painted scene.

Runs the whole coach in one pass on a real image, so the new ``coach.paint``
layer is shown in context rather than alone:

    parse_intent            structure the brief (+ defaults)
    resolve_style           style-as-grammar -> a concrete palette/weights
    create_plan/validate    layer-order discipline (no detail before structure)
    ingest (region+outline) raster -> fillable polygons + line-art   [vision group]
    clean                   denoise + RDP-simplify the line-art (fewer nodes)
    recolor_to_style        re-skin the region fills to the style palette
    gradientize             flat fills -> 2-stop gradients (form)
    atmosphere              style-driven glow + wash + vignette (DEPTH)  [new]
    to_silhouette           the readability gate (advisory rubric)

Compose order = the layer plan: atmosphere.back → fills → ink → atmosphere.front.

    uv run --group vision python examples/coach_paint_showcase.py \
        demo/Gemini_Generated_Image_1h4no51h4no51h4n.jpeg --out out/coach_paint
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.coach import (  # noqa: E402
    atmosphere, clean, cleanup_params, create_plan, curve_count, gradientize, ingest, node_count,
    parse_intent, recolor_to_style, redraw, redraw_params, resolve_style, stage_rubric,
    to_silhouette, validate_order,
)
from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402


def _place(objs, box, src):
    """Fit src-sized geometry into box (centered) via a style.transform."""
    import copy
    bx, by, bw, bh = box
    sw, sh = src
    s = min(bw / sw, bh / sh) if sw and sh else 1.0
    tx, ty = bx + (bw - sw * s) / 2, by + (bh - sh * s) / 2
    pre = f"translate({tx:.3f} {ty:.3f}) scale({s:.5f})"
    out = []
    for o in objs:
        o = copy.deepcopy(o)
        st = dict(o.get("style") or {})
        st["transform"] = f"{pre} {st['transform']}" if st.get("transform") else pre
        o["style"] = st
        out.append(o)
    return out


def build(image, *, style_names=("children_book",), out_dir="out/coach_paint"):
    intent = parse_intent(f"a city illustration, {style_names[0]}, three-quarter")
    style = resolve_style(*style_names)
    plan = create_plan()
    plan_issues = validate_order(plan.layers)

    region, w, h = ingest(image, mode="region", colors=10, min_area=120.0)
    outline, _, _ = ingest(image, mode="outline", detail=0.0018, min_area=22.0)
    src = (w, h)

    # clean + redraw are now STYLE-DRIVEN (params derived from the StyleProfile)
    n_before = node_count(outline)
    cleaned = clean(outline, **cleanup_params(style))
    n_after = node_count(cleaned)
    ink = redraw(cleaned, **redraw_params(style), stroke=style.palette[0])   # 06_line_art
    n_curves = curve_count(ink)

    fills = gradientize(recolor_to_style(region, style))
    atm = atmosphere(style, w, h)

    # ---- hero: the coach layer plan, composed ----
    W, H = 1280, int(1280 * h / w)
    b = DocumentBuilder(title="coach-paint-hero")
    page = b.page("hero", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    box = [0, 0, W, H]
    bg = page.layer("00_atmosphere_back")
    for o in atm["back"]:
        bg.add(o)
    fl = page.layer("07_flat_colors")
    for o in _place(fills, box, src):
        fl.add(o)
    li = page.layer("06_line_art")
    for o in _place(ink, box, src):
        li.add(o)
    fr = page.layer("09_highlights")
    for o in atm["front"]:
        fr.add(o)
    hero_svg = render_page_svgs(b.build())[0]

    # ---- silhouette gate on the cleaned line-art ----
    sg = DocumentBuilder(title="sg")
    sgp = sg.page("s", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    sgp.layer("bg").rect([0, 0, W, H], fill="#FFFFFF", decorative=True)
    sl = sgp.layer("03_silhouette")
    for o in _place(ink, box, src):
        sl.add(o)
    sil_svg = render_page_svgs(to_silhouette(sg))[0]

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "hero.svg"), "w", encoding="utf-8") as fh:
        fh.write(hero_svg)
    with open(os.path.join(out_dir, "silhouette.svg"), "w", encoding="utf-8") as fh:
        fh.write(sil_svg)

    print(f"[coach] intent.subject={intent.subject!r}")
    print(f"[coach] style={style.name} palette={list(style.palette)}")
    print(f"[coach] layer plan valid: {not plan_issues}  ({len(plan.layers)} stages)")
    print(f"[ingest] region={len(region)} fills, outline={len(outline)} strokes ({w}x{h})")
    print(f"[clean] nodes {n_before} -> {n_after}  (style: {cleanup_params(style)})")
    print(f"[redraw] {n_curves} smooth Bézier strokes  (style: {redraw_params(style)})")
    print(f"[paint] atmosphere: {len(atm['back'])} back + {len(atm['front'])} front (style-driven)")
    print(f"[gate] silhouette rubric: {stage_rubric('silhouette')[0]}")
    print(f"[write] {out_dir}/hero.svg, silhouette.svg")
    ok = hero_svg.startswith("<svg") and "gradient" in hero_svg.lower() and not plan_issues
    print(f"\nVERDICT: {'coach + paint pipeline ran end-to-end' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--style", default="children_book")
    ap.add_argument("--out", default="out/coach_paint")
    args = ap.parse_args(argv)
    return build(args.image, style_names=(args.style,), out_dir=args.out)


if __name__ == "__main__":
    raise SystemExit(main())
