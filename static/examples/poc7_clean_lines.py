"""POC-07 — image-agnostic line/contour cleanup, measured on any subject.

The generalizable lesson from vela-nova: improve the *lines* (simplify, denoise),
not the anatomy. This ingests a raster, runs coach.clean (RDP + speckle drop),
and measures — for ANY image — node reduction (cleaner/editable/smaller) at a
near-flat ink-IoU (the picture is preserved). Renders a before/after.

Run:
    uv run --group vision python examples/poc7_clean_lines.py \
        demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc7
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get("FG_ROOT", ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framegraph.sdk import DocumentBuilder, render_page_svgs  # noqa: E402
from framegraph.coach import clean, ingest, node_count  # noqa: E402
from poc3_ingest_compose import ink_iou, place, restyle_strokes  # noqa: E402

DEFAULT_IMG = os.path.join(ROOT, "demo", "Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg")
FONT = ["Inter", "Helvetica", "Arial", "sans-serif"]


def _fidelity(image, objs, w, h):
    b = DocumentBuilder(title="f")
    p = b.page("p", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    p.rect([0, 0, w, h], fill="#FFFFFF")
    lay = p.layer("ink")
    for o in restyle_strokes(objs, stroke="#000000", width=1.0):
        lay.add(o)
    return ink_iou(image, render_page_svgs(b.build())[0])


def _panel(page, x, y, w, h, label, color, objs, src):
    page.add({"type": "rect", "box": [x, y, w, h], "fill": "#FFFFFF", "radius": 10})
    page.add({"type": "text", "box": [x + 14, y + 8, w - 28, 20], "text": label,
              "style": {"font_family": FONT, "font_size": 13, "font_weight": 700, "color": color}})
    for o in place(restyle_strokes(objs, stroke="#10151F", width=1.0),
                   [x + 10, y + 34, w - 20, h - 44], src):
        page.add(o)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?", default=DEFAULT_IMG)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "poc7"))
    ap.add_argument("--eps", type=float, default=1.3)
    ap.add_argument("--min-span", type=float, default=8.0)
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    base, w, h = ingest(args.image, mode="outline", max_dim=1400)
    cleaned = clean(base, min_span=args.min_span, eps=args.eps)
    src = (w, h)

    n0, n1 = node_count(base), node_count(cleaned)
    s0, s1 = len(base), len(cleaned)
    f0 = _fidelity(args.image, base, w, h) or 0.0
    f1 = _fidelity(args.image, cleaned, w, h) or 0.0
    dn = 100.0 * (n0 - n1) / n0 if n0 else 0.0
    name = os.path.basename(args.image)[:34]
    print(f"  {name:<36} strokes {s0:>5}→{s1:<5}  nodes {n0:>6}→{n1:<6} (-{dn:4.0f}%)  "
          f"ink-IoU {f0:.3f}→{f1:.3f} (Δ{f1 - f0:+.3f})")

    # before/after render
    cw, ch, pad = 600, 470, 24
    W, H = 2 * cw + 3 * pad, 44 + ch + 2 * pad
    b = DocumentBuilder(title="poc7-clean")
    page = b.page("ba", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.add({"type": "text", "box": [pad, 12, W - 2 * pad, 26],
              "text": "Line cleanup (image-agnostic): RDP + speckle drop — same picture, fewer nodes",
              "style": {"font_family": FONT, "font_size": 18, "font_weight": 700, "color": "#F2F5FA"}})
    _panel(page, pad, 44 + pad, cw, ch, f"raw trace — {n0} nodes, {s0} strokes", "#8B949E", base, src)
    _panel(page, pad + cw + pad, 44 + pad, cw, ch,
           f"cleaned — {n1} nodes (-{dn:.0f}%), ink-IoU {f1:.3f}", "#3FB950", cleaned, src)
    b.write(os.path.join(args.out, "clean_before_after.fg.yaml"))
    with open(os.path.join(args.out, "clean_before_after.svg"), "w", encoding="utf-8") as fh:
        fh.write(render_page_svgs(b.build())[0])

    ok = n1 < n0 and (f1 - f0) > -0.03      # fewer nodes, fidelity not materially worse
    print(f"  → {'IMPROVED (lighter + preserved)' if ok else 'NO NET GAIN'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
