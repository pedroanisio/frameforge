#!/usr/bin/env python3
"""Vector Construction Coach — staged-loop demo (framegraph.coach POC).

Shows the disciplined loop the coach enforces, reusing the SDK end-to-end:

  01 Construction  — block the subject as flat volumes (+ guides / gesture line)
  02 Silhouette    — to_silhouette() flattens it to black-on-white; the gate asks
                     "is it readable as a solid shape?" BEFORE any detail (the
                     rubric is shown on-page; the judgement is the model's/VLM's)
  03 Styled        — apply the resolved StyleProfile (flat_icon) palette

The coach supplies the scaffold (intent, style-as-grammar, layer-order, the
silhouette gate). The drawing itself is hand-composed with SDK primitives — the
coach never claims to draw for you.

Run from the repo root::

    uv run python examples/coach_demo.py out/coach/coach-demo.fg.yaml
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize  # noqa: E402
from framegraph.sdk.paint import rgba  # noqa: E402
from framegraph.coach import (  # noqa: E402
    create_plan,
    parse_intent,
    resolve_style,
    stage_rubric,
    to_silhouette,
    validate_order,
)

W, H = 900, 660
INK, SUB, LINE, PAPER, BG = "#1E2030", "#8A90A6", "#E7E9F2", "#FFFFFF", "#F2F3F8"
SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
DISPLAY = ["Poppins", "Inter Display", "Inter", "Arial", "sans-serif"]

# construction = neutral volumes; styled = the flat_icon profile's colours
CONSTRUCT = dict(body="#C9CDD6", belly="#DDE0E7", ear="#C9CDD6", eye="#FFFFFF",
                 pupil="#9AA0AC", beak="#B8BEC9", wing="#BCC1CC")
STYLED = dict(body="#6D28D9", belly="#8B5CF6", ear="#6D28D9", eye="#FFFFFF",
              pupil="#1E2030", beak="#22D3EE", wing="#5B21B6")


def _t(size, color, *, weight=400, family=None, align="left", spacing=None, lh=None,
       upper=False, wrap=True):
    s = {"font_family": family or SANS, "font_size": size, "font_weight": weight,
         "color": color, "align": align}
    if spacing is not None:
        s["letter_spacing"] = spacing
    if lh is not None:
        s["line_height"] = lh
    if upper:
        s["text_transform"] = "uppercase"
    if not wrap:
        s["white_space"] = "nowrap"
    return s


def draw_owl(L, cx, cy, pal, *, guides=False):
    """A simple flat owl — recognizable by silhouette. Parts take colours from
    ``pal`` so the same construction renders neutral, black (via to_silhouette), or
    styled without changing the geometry."""
    if guides:                                  # 01_guides / 02_construction overlay
        for gx, gy, r in ((cx, cy - 8, 96), (cx - 44, cy - 26, 38), (cx + 44, cy - 26, 38)):
            L.add({"type": "ellipse", "center": [gx, gy], "rx": r, "ry": r, "fill": "none",
                   "stroke": rgba("#6D28D9", 0.35), "stroke_style": {"stroke_width": 1.4,
                   "stroke_dasharray": [5, 5]}})
        L.line([cx, cy - 150], [cx, cy + 150], stroke=rgba("#6D28D9", 0.3),
               stroke_style={"stroke_width": 1.4, "stroke_dasharray": [5, 5]})
    # ear tufts
    L.polygon([[cx - 78, cy - 56], [cx - 52, cy - 124], [cx - 26, cy - 58]], fill=pal["ear"])
    L.polygon([[cx + 78, cy - 56], [cx + 52, cy - 124], [cx + 26, cy - 58]], fill=pal["ear"])
    # wings
    L.add({"type": "ellipse", "center": [cx - 96, cy + 24], "rx": 30, "ry": 74, "fill": pal["wing"]})
    L.add({"type": "ellipse", "center": [cx + 96, cy + 24], "rx": 30, "ry": 74, "fill": pal["wing"]})
    # body + belly
    L.rect([cx - 92, cy - 78, 184, 210], radius=92, fill=pal["body"])
    L.add({"type": "ellipse", "center": [cx, cy + 34], "rx": 66, "ry": 86, "fill": pal["belly"]})
    # eyes
    for ex in (cx - 44, cx + 44):
        L.add({"type": "ellipse", "center": [ex, cy - 26], "rx": 36, "ry": 36, "fill": pal["eye"]})
        L.add({"type": "ellipse", "center": [ex, cy - 26], "rx": 15, "ry": 15, "fill": pal["pupil"]})
        L.add({"type": "ellipse", "center": [ex + 5, cy - 31], "rx": 5, "ry": 5,
               "fill": rgba("#FFFFFF", 0.85)})
    # beak
    L.polygon([[cx - 13, cy - 8], [cx + 13, cy - 8], [cx, cy + 16]], fill=pal["beak"])
    # feet
    for fx in (cx - 30, cx + 30):
        L.add({"type": "ellipse", "center": [fx, cy + 132], "rx": 18, "ry": 11, "fill": pal["beak"]})


def _caption(L, num, title, note=""):
    L.text([56, 40, W - 112, 18], f"STEP {num}",
           style=_t(12, "#6D28D9", weight=700, family=DISPLAY, spacing=2.4, upper=True, wrap=False))
    L.text([56, 60, W - 112, 30], title, style=_t(24, INK, weight=700, family=DISPLAY, wrap=False))
    if note:
        L.text([56, 96, W - 112, 20], note, style=_t(13, SUB, wrap=False))


def _page(b, pid, bg=BG):
    p = b.page(pid, canvas={"size": [W, H]}, coordinate_mode="absolute")
    p.layer("bg").rect([0, 0, W, H], fill=bg, decorative=True)
    return p


def build_document():
    # the coach scaffold (deterministic) ------------------------------------ #
    intent = parse_intent("a friendly owl mascot, flat icon, front view")
    plan = create_plan()
    assert validate_order(plan.layers) == []           # discipline holds
    style = resolve_style(intent.style)                 # flat_icon profile

    b = DocumentBuilder(title="Coach demo — staged vector loop", profile="deck", lang="en")

    # 01 — construction (neutral volumes + guides) --------------------------- #
    p1 = _page(b, "01-construction")
    _caption(p1, "01", "Construction", "Block volumes + gesture — no detail yet.")
    draw_owl(p1.layer("subject"), W / 2, H / 2 + 40, CONSTRUCT, guides=True)

    # 02 — silhouette gate (REAL to_silhouette of the construction) ---------- #
    owl = DocumentBuilder(title="owl", profile="diagram")
    op = owl.page("s", canvas={"size": [W, H]}, coordinate_mode="absolute")
    op.layer("bg").rect([0, 0, W, H], fill=PAPER, decorative=True)
    draw_owl(op.layer("subject"), W / 2, H / 2 + 40, CONSTRUCT)
    sil = to_silhouette(owl)
    sil_layers = sil.model_dump(by_alias=True, exclude_none=True)["pages"][0]["layers"]

    p2 = _page(b, "02-silhouette", bg=PAPER)
    b._doc["pages"][-1]["layers"].extend(sil_layers)    # inject the flattened owl
    cap = p2.layer("caption")
    _caption(cap, "02", "Silhouette gate", "Readable as a solid shape?")
    ry = 150
    for line in stage_rubric("silhouette"):
        cap.text([56, ry, 360, 40], "•  " + line, style=_t(11.5, SUB, lh=1.4))
        ry += 26

    # 03 — styled (apply the resolved StyleProfile palette) ------------------ #
    p3 = _page(b, "03-styled")
    _caption(p3, "03", f"Styled · {style.name}", "Palette + flat fills from the style grammar.")
    draw_owl(p3.layer("subject"), W / 2, H / 2 + 40, STYLED)
    return b


doc = build_document()


def main() -> int:
    from framegraph.sdk.validate import validate_static_rules
    built = doc.build()
    rep = validate_static_rules(built)
    errs = [i for i in rep.issues if i.severity == "error"]
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "coach", "coach-demo.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(built, format="yaml"))
    print(f"coach-demo: {len(built.pages)} pages, ok={rep.ok}, errors={len(errs)} -> {out}")
    for i in errs[:20]:
        print("  ERROR:", i.code, i.message)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
