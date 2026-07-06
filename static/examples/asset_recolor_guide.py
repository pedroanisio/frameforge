#!/usr/bin/env python3
"""Using imported assets — recolour/gradient them, or trace on top of them.

`place_figure` imports another FrameGraph page's objects as EDITABLE children
(deepcopied, not a frozen image), so an ingested asset can be:

  01 reused as-is        p.figure(src, box, page=...)
  02 recoloured/gradient walk the children, remap fills + swap gradients
  03 used as a guideline place it faint (low opacity) and hand-draw on top

Same idea applies to a vision draft from `propose_from_image` (a screenshot →
detected primitives) — it's just another editable object tree to recolour or trace.

    uv run python examples/asset_recolor_guide.py out/coach/asset-recolor-guide.fg.yaml
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, os.path.join(ROOT, "static", "examples"))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, merge_figure_defs, place_figure, serialize  # noqa: E402
from framegraph.sdk.paint import linear_gradient, rgba  # noqa: E402
from landing_headers import ring, cross, _dot  # noqa: E402  — reuse the kit to draw on top

SRC = os.path.join(ROOT, "out", "coach", "coach-demo.fg.yaml")   # the styled owl asset
PAGE = "03-styled"
W, H = 1280, 720
INK, SUB, BG, CARD = "#1E2030", "#8A90A6", "#EEF0F5", "#FFFFFF"
DISPLAY = ["Poppins", "Inter Display", "Inter", "Arial", "sans-serif"]
SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
BOX = [700, 150, 500, 440]

# recolour map: the owl's purple/cyan palette -> a teal/amber re-skin
SWAP = {"#6D28D9": "#0E7C86", "#8B5CF6": "#14B8A6", "#5B21B6": "#0B5563",
        "#22D3EE": "#F59E0B", "#9AA0AC": "#9AA0AC", "#1E2030": "#1E2030"}
NEW_GRAD = linear_gradient([("#14B8A6", 0), ("#0B5563", 100)], angle=135)


def _t(size, color, *, weight=400, family=None, lh=None):
    s = {"font_family": family or SANS, "font_size": size, "font_weight": weight, "color": color}
    if lh is not None:
        s["line_height"] = lh
    return s


def _recolor(obj, swap, grad):
    """Walk an imported object tree, remapping solid fills and swapping gradients."""
    if isinstance(obj, dict):
        f = obj.get("fill")
        if isinstance(f, str) and f != "none":
            obj["fill"] = swap.get(f.upper(), swap.get(f, f))
        elif isinstance(f, dict):                       # a gradient → swap wholesale
            obj["fill"] = grad
        s = obj.get("stroke")
        if isinstance(s, str) and s != "none":
            obj["stroke"] = swap.get(s.upper(), swap.get(s, s))
        for v in obj.values():
            _recolor(v, swap, grad)
    elif isinstance(obj, list):
        for v in obj:
            _recolor(v, swap, grad)


def _caption(p, step, title, note):
    p.text([70, 56, 560, 18], f"STEP {step}",
            style={**_t(12, "#6D28D9", weight=700, family=DISPLAY), "letter_spacing": 2.4,
                   "text_transform": "uppercase", "white_space": "nowrap"})
    p.text([70, 78, 560, 30], title, style=_t(25, INK, weight=700, family=DISPLAY))
    p.text([70, 122, 540, 120], note, style=_t(14, SUB, lh=1.6))


def _page(b, pid):
    p = b.page(pid, canvas={"size": [W, H]}, coordinate_mode="absolute")
    p.layer("bg").rect([0, 0, W, H], fill=BG, decorative=True)
    p.rect([BOX[0] - 30, BOX[1] - 30, BOX[2] + 60, BOX[3] + 60], radius=24, fill=CARD,
           decorative=True)
    return p


def build_document():
    b = DocumentBuilder(title="Imported assets — recolour & trace", profile="deck", lang="en")

    # 01 — import as-is (editable, not a frozen image)
    p1 = _page(b, "01-import")
    _caption(p1, "01", "Import an asset", "place_figure() pulls another page's objects in "
             "as editable children — not a flattened image.")
    p1.figure(SRC, BOX, page=PAGE)

    # 02 — recolour + re-gradient the SAME objects
    p2 = _page(b, "02-recolor")
    _caption(p2, "02", "Recolour + gradient", "Walk the children, remap fills and swap the "
             "gradient — the asset re-skins because it's real vector objects.")
    pl = place_figure(SRC, BOX, page=PAGE)
    merge_figure_defs(b._doc, pl.defs)
    _recolor(pl.group, SWAP, NEW_GRAD)
    p2.add(pl.group)

    # 03 — use as a faint guideline, then hand-draw on top
    p3 = _page(b, "03-trace")
    _caption(p3, "03", "Guideline → draw on top", "Place it faint as an underlay, then "
             "construct fresh shapes over it with the SDK / kit.")
    guide = place_figure(SRC, BOX, page=PAGE)
    merge_figure_defs(b._doc, guide.defs)
    guide.group["opacity"] = 0.16
    p3.add(guide.group)
    over = p3.layer("overlay")
    cx, cy = BOX[0] + BOX[2] / 2, BOX[1] + BOX[3] / 2 + 14
    ring(over, cx, cy, 150, "#6D28D9", 2.5)                         # trace the head/body mass
    for dx, dy, label in ((-70, -120, "ears"), (70, -40, "eyes"), (140, 30, "beak")):
        _dot(over, cx + dx, cy + dy, 6, "#F2B705")
        over.line([cx + dx, cy + dy], [cx + dx + 40, cy + dy - 26],
                  stroke="#6D28D9", stroke_style={"stroke_width": 1.6})
        over.text([cx + dx + 46, cy + dy - 38, 120, 18], label,
                  style={**_t(13, INK, weight=600, family=DISPLAY), "white_space": "nowrap"})
    cross(over, BOX[0] + 30, BOX[1] + 30, 8, "#F2B705")
    return b


doc = build_document()


def main() -> int:
    from framegraph.sdk.validate import validate_static_rules
    built = doc.build()
    rep = validate_static_rules(built)
    errs = [i for i in rep.issues if i.severity == "error"]
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "coach", "asset-recolor-guide.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(built, format="yaml"))
    print(f"asset-recolor-guide: {len(built.pages)} pages, ok={rep.ok}, errors={len(errs)} -> {out}")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
