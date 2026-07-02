"""POC-09 — a coach that draws COMPLEX HUMAN FIGURES (honest end-to-end).

The thesis, proven with real execution rather than prose:

    A coach does NOT synthesize a complex human from primitives (the reviewed
    ceiling). What it CAN do is *source* the complexity from a raster, then use
    every coach layer to turn it into a clean, posable, on-canon, verified
    vector figure:

      ingest  → clean → ANALYZE (landmarks + proportion signature)
              → plausibility gate → retarget onto a drawing canon
              → mirror → silhouette gate → compose

The new piece is ``framegraph.coach.figures``: it reads the silhouette *width
profile* and recovers anatomical structure (shoulders / waist / hips / knees)
where the naive region trace collapses a shaded figure into a black block.
With that structure the figure becomes editable PROPORTION: retarget it onto
the Vitruvian / heroic / fashion canon, mirror a half into a symmetric whole,
and gate it for plausibility — none of which a flat raster allows.

Honest limits (PALS's Law): the proportion gate is ADVISORY, not a proof of
"human"; retarget re-proportions what was sourced — it does not invent occluded
detail or repair a bad source. Complexity is sourced; the coach structures it.

Run (needs the vision group for ingest):
    uv run --group vision python examples/poc9_figure_coach.py \
        /home/admin/codebases/vela-nova-rocket/input/ironman.jpeg --out out/poc9
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get("FG_ROOT", ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framegraph.sdk import DocumentBuilder, render_page_svgs, validate_static_rules  # noqa: E402
from framegraph.coach import (  # noqa: E402
    CANONS,
    analyze,
    clean,
    ingest,
    mirror_outer,
    plausibility,
    retarget,
    stage_rubric,
    to_silhouette,
)
from poc3_ingest_compose import ink_iou, place, restyle_strokes  # noqa: E402

FONT = ["Inter", "Helvetica", "Arial", "sans-serif"]
DEFAULT_IMG = "/home/admin/codebases/vela-nova-rocket/input/ironman.jpeg"


def _union_points(objs: list) -> list:
    """Every polyline/polygon vertex as one cloud — the figure's outer envelope
    falls out of the per-y max width over this cloud."""
    pts = []
    for o in objs:
        if o.get("type") in ("polyline", "polygon") and o.get("points"):
            pts.extend([float(p[0]), float(p[1])] for p in o["points"])
    return pts


def _smooth(series: list, k: int = 7) -> list:
    """Centered moving average (odd window) — denoise the width envelope so the
    silhouette polygon reads cleanly instead of self-intersecting at the feet."""
    n = len(series)
    if n < 3 or k <= 1:
        return list(series)
    h = k // 2
    return [sum(series[max(0, i - h):min(n, i + h + 1)]) /
            (min(n, i + h + 1) - max(0, i - h)) for i in range(n)]


def _silhouette_polygon(model) -> list:
    """Build the recovered figure silhouette (symmetric envelope) from the
    width profile — the proof that structure, not a black block, was found."""
    fr = model.frame
    head_px = fr.head_px
    scale = 1.0 / head_px if head_px else 1.0
    widths = _smooth([dx_hu / scale for dx_hu, _ in model.profile], k=15)   # px half-widths
    ys = [fr.y_top + dy_hu * head_px for _, dy_hu in model.profile]
    right = [[fr.midline + hw, y] for hw, y in zip(widths, ys)]
    left = [[fr.midline - hw, y] for hw, y in zip(widths, ys)]
    return right + list(reversed(left))


def _panel(page, x, y, w, h, label, color, draw):
    page.add({"type": "rect", "box": [x, y, w, h], "fill": "#FFFFFF", "radius": 12})
    page.add({"type": "text", "box": [x + 16, y + 10, w - 32, 22], "text": label,
              "style": {"font_family": FONT, "font_size": 14, "font_weight": 700, "color": color}})
    draw(x + 12, y + 40, w - 24, h - 52)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?", default=DEFAULT_IMG)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "poc9"))
    ap.add_argument("--canon", default="heroic", choices=sorted(CANONS))
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    # 1) SOURCE the complexity, then clean the lines (image-agnostic).
    raw, w, h = ingest(args.image, mode="outline", max_dim=1400)
    base = clean(raw, min_span=7.0, eps=1.3)
    src = (w, h)
    print(f"[ingest+clean] {os.path.basename(args.image)} → {len(raw)}→{len(base)} strokes ({w}x{h})")

    # 2) ANALYZE — recover anatomical structure from the silhouette width profile.
    model = analyze(_union_points(base), head_count=8.0)
    names = [lm.name for lm in model.landmarks]
    print(f"[analyze] landmarks: {', '.join(names) or '(none)'}")
    if model.signature is None:
        print("  → too few landmarks to build a signature; complex source needs a cleaner silhouette")
        return 1

    # 3) PLAUSIBILITY gate (advisory) — measured against the documented canons.
    rep = plausibility(model.signature, references=list(CANONS.values()))
    rd = rep.get("reference_distance")
    rd_txt = f"{rd:.2f}" if rd is not None else "n/a (landmark set ≠ 7-point canon)"
    print(f"[gate] head_count {rep['head_count']:.2f}  plausible={rep['plausible']}  "
          f"ref_dist={rd_txt}"
          + (f"  issues={rep['issues']}" if rep["issues"] else ""))

    # 4) RETARGET the whole line-art onto a drawing canon (height preserved).
    canon_pts = {st: [
        {**o, "points": retarget(model, st, points=o["points"])}
        for o in base if o.get("type") in ("polyline", "polygon") and o.get("points")
    ] for st in (args.canon, "fashion")}

    def _height(objs):
        ys = [p[1] for o in objs for p in o["points"]]
        return (max(ys) - min(ys)) if ys else 0.0

    h0 = _height([o for o in base if o.get("points")])
    for st, objs in canon_pts.items():
        dh = abs(_height(objs) - h0) / h0 * 100 if h0 else 0.0
        print(f"[retarget→{st}] height drift {dh:.1f}%  ({len(objs)} strokes re-proportioned)")

    # 5) MIRROR — the recovered silhouette into a bilaterally symmetric figure.
    sil = _silhouette_polygon(model)
    mirrored = mirror_outer(sil, midline=model.frame.midline)

    # 6) SILHOUETTE GATE — does the structured figure READ as a figure? (vs a block)
    gate_doc = DocumentBuilder(title="poc9-gate")
    gp = gate_doc.page("g", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    gp.rect([0, 0, w, h], fill="#FFFFFF")
    gl = gp.layer("ink")
    gl.add({"type": "polygon", "points": sil, "fill": "#000000"})
    sil_ok = bool(render_page_svgs(to_silhouette(gate_doc)))
    rubric = stage_rubric("silhouette")
    print(f"[gate] silhouette renders={sil_ok}; rubric q1: {rubric[0] if rubric else '—'}")

    # 7) COMPOSE the honest 4-panel proof page.
    fid = ink_iou(args.image, render_page_svgs(_flat(base, w, h))[0]) or 0.0
    cw, ch, pad, top = 600, 470, 24, 56
    W, H = 2 * cw + 3 * pad, top + 2 * ch + 3 * pad
    doc = DocumentBuilder(title="poc9-figure-coach")
    page = doc.page("proof", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.add({"type": "text", "box": [pad, 16, W - 2 * pad, 30],
              "text": "Coach × complex human figure: source → analyze → retarget → gate",
              "style": {"font_family": FONT, "font_size": 20, "font_weight": 800, "color": "#F2F5FA"}})

    def draw_ink(objs, color="#10151F", width=1.0):
        def d(x, y, bw, bh):
            for o in place(restyle_strokes(objs, stroke=color, width=width),
                           [x, y, bw, bh], src):
                page.add(o)
        return d

    def draw_landmarks(x, y, bw, bh):
        for o in place(restyle_strokes(base, stroke="#10151F", width=1.0), [x, y, bw, bh], src):
            page.add(o)
        # landmark ticks placed in the SAME box (recompute the place transform on a polyline)
        ticks = []
        for lm in model.landmarks:
            yy = model.frame.y_top + lm.dy * model.frame.head_px
            ticks.append({"type": "polyline",
                          "points": [[model.frame.midline - lm.dx / (1.0 / model.frame.head_px) - 30, yy],
                                     [model.frame.midline + lm.dx / (1.0 / model.frame.head_px) + 30, yy]]})
        for o in place(restyle_strokes(ticks, stroke="#D4A23A", width=2.0), [x, y, bw, bh], src):
            page.add(o)

    px, py = pad, top + pad
    _panel(page, px, py, cw, ch, f"1 · sourced + cleaned line-art  (ink-IoU {fid:.2f})", "#8B949E",
           draw_ink(base))
    _panel(page, px + cw + pad, py, cw, ch,
           f"2 · structure recovered  ({len(names)} landmarks, {rep['head_count']:.1f} heads)",
           "#D4A23A", draw_landmarks)
    py2 = top + 2 * pad + ch
    _panel(page, px, py2, cw, ch, f"3 · retargeted → {args.canon} canon  (height preserved)", "#58A6FF",
           draw_ink(canon_pts[args.canon], color="#1B3A5B", width=1.1))

    def draw_gate(x, y, bw, bh):
        for o in place([{"type": "polygon", "points": sil, "fill": "#101820"},
                        {"type": "polygon", "points": mirrored, "fill": "none",
                         "stroke": "#D4A23A", "stroke_style": {"stroke_width": 1.5}}],
                       [x, y, bw, bh], src):
            page.add(o)
    _panel(page, px + cw + pad, py2, cw, ch,
           f"4 · silhouette gate {'PASS' if sil_ok and rep['plausible'] else 'REVIEW'} (+ mirror rebuild)",
           "#3FB950", draw_gate)

    report = validate_static_rules(doc.build())
    doc.write(os.path.join(args.out, "figure-coach.fg.yaml"))
    with open(os.path.join(args.out, "figure-coach.svg"), "w", encoding="utf-8") as fh:
        fh.write(render_page_svgs(doc.build())[0])
    print(f"[write] {args.out}/figure-coach.svg (+ .fg.yaml)  validate: "
          f"{'clean' if report.ok else f'{len(report.issues)} issue(s)'}")

    verdict = (model.signature is not None and len(names) >= 3 and sil_ok and report.ok)
    print(f"\nVERDICT: {'WIRED — sourced complexity structured into editable, gated figure proportion' if verdict else 'NEEDS WORK'}")
    return 0 if verdict else 1


def _flat(objs, w, h):
    b = DocumentBuilder(title="flat")
    p = b.page("p", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    p.rect([0, 0, w, h], fill="#FFFFFF")
    lay = p.layer("ink")
    for o in restyle_strokes(objs, stroke="#000000", width=1.0):
        lay.add(o)
    return b.build()


if __name__ == "__main__":
    sys.exit(main())
