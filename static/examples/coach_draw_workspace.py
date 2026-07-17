"""Coach draws ``demo/images.jpeg`` — a flat workspace illustration.

Honest framing (POC ceiling, PALS's Law): the coach does NOT invent this scene
from primitives. It *sources* the complexity from the raster and uses its
generalizable lane to structure it into a clean, editable, validated vector:

    ingest(region)  → flat colour fills as polygons   (the look)
    ingest(outline) → crisp black edges as polylines   (the linework)
            → clean (denoise + RDP-simplify)            → fewer nodes, bounded shape change
            → compose on the SDK + validate_static_rules (a real FrameForge doc)

The figure/proportion machinery (analyze/retarget/mirror) is human-specific and
deliberately NOT used here — this asset is a scene, not a posable figure.

Run:
    uv run --group vision python examples/coach_draw_workspace.py
or via the frameforge MCP (run_sdk_client → build()).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get("FG_ROOT", ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frameforge.sdk import DocumentBuilder, render_page_svgs, serialize, validate_static_rules  # noqa: E402
from frameforge.coach import clean, ingest, node_count  # noqa: E402
from poc3_ingest_compose import ink_iou, restyle_strokes  # noqa: E402

IMG = os.path.join(ROOT, "demo", "images.jpeg")

# Region tracing keeps the flat fills; outline tracing keeps the crisp linework.
_REGION = dict(mode="region", colors=8, detail=0.0020, min_area=22.0, max_dim=900)
_OUTLINE = dict(mode="outline", colors=8, detail=0.0016, min_area=14.0, max_dim=900)
_INK = "#14181F"


def _trace():
    regions, w, h = ingest(IMG, **_REGION)
    outline, _, _ = ingest(IMG, **_OUTLINE)
    regions_c = clean(regions, min_span=4.0, eps=1.1)
    outline_c = clean(outline, min_span=6.0, eps=1.0)
    return regions_c, outline_c, w, h


def build():
    regions, outline, w, h = _trace()
    doc = DocumentBuilder(title="coach-draw-workspace")
    page = doc.page("draw", canvas={"size": [w, h], "units": "px"},
                    coordinate_mode="absolute")
    page.rect([0, 0, w, h], fill="#FFFFFF")
    fills = page.layer("fills")          # flat colour, big shapes first (sourced order)
    for o in regions:
        fills.add(o)
    ink = page.layer("ink")              # crisp black edges on top
    for o in restyle_strokes(outline, stroke=_INK, width=1.4):
        ink.add(o)
    return doc.build()


def main() -> int:
    regions, outline, w, h = _trace()
    doc = build()
    report = validate_static_rules(doc)
    svg = render_page_svgs(doc)[0]
    out_dir = os.path.join(ROOT, "out", "coach_workspace")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "workspace.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)
    doc_path = os.path.join(out_dir, "workspace.fg.yaml")
    with open(doc_path, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc))
    fid = ink_iou(IMG, svg) or 0.0
    print(f"[trace]    region polys={len(regions)}  outline strokes={len(outline)}  ({w}x{h})")
    print(f"[clean]    nodes: region={node_count(regions)}  outline={node_count(outline)}")
    print(f"[validate] {'clean' if report.ok else f'{len(report.issues)} issue(s)'}")
    print(f"[fidelity] ink-IoU vs source = {fid:.2f}")
    print(f"[write]    {out_dir}/workspace.svg (+ .fg.yaml)")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
