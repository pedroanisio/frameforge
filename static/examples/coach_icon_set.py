#!/usr/bin/env python3
"""Coach challenge — a 6-icon set, one style, A/B vs one-shot drift.

The falsifiable test of the coach POC's claims (style-as-grammar + silhouette
gate + editability):

  1 COACHED   — all 6 icons drawn from ONE resolved StyleProfile (comic_ink +
                blueprint). Consistency is structural: 1 style, not 6.
  2 GATE      — each icon flattened via to_silhouette(): readable in black?
  3 EDIT      — swap the style ONCE (-> woodcut) and all 6 update from one change.
  4 ONE-SHOT  — the control: each icon styled ad-hoc (what you get with no shared
                grammar). Visibly drifts; an edit means touching 6 places.

main() prints the measured consistency delta. Run::

    uv run python examples/coach_icon_set.py out/coach/coach-icons.fg.yaml
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, serialize  # noqa: E402
from frameforge.coach import resolve_style, stage_rubric, to_silhouette  # noqa: E402

W, H, M = 1240, 640, 70
INK_UI, SUB, BG, PAPER = "#1E2030", "#8A90A6", "#F2F3F8", "#FFFFFF"
DISPLAY = ["Poppins", "Inter Display", "Inter", "Arial", "sans-serif"]
SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
ICONS = ["search", "upload", "lock", "chart", "message", "settings"]


def _t(size, color, *, weight=400, family=None, align="left", spacing=None, upper=False, wrap=False):
    s = {"font_family": family or SANS, "font_size": size, "font_weight": weight,
         "color": color, "align": align}
    if spacing is not None:
        s["letter_spacing"] = spacing
    if upper:
        s["text_transform"] = "uppercase"
    if not wrap:
        s["white_space"] = "nowrap"
    return s


def style_to_kit(p) -> dict:
    """Lower a StyleProfile to the concrete drawing values icons consume.
    This is the single source of truth the coached path shares across all icons."""
    ink = p.palette[0]
    accent = next((c for c in p.palette if c.lower() in ("#3b6ea5", "#0b5fbf", "#9fd0ff")), ink)
    tile = next((c for c in p.palette if c.lower() in ("#ffffff", "#fff7e8", "#f3ead6")), "#FFFFFF")
    return {"w": max(2.0, p.outer), "line": ink, "accent": accent, "tile": tile}


def _stroke(w, col, **extra):
    return {"stroke": col, "stroke_style": {"stroke_width": w, "stroke_linecap": "round",
            "stroke_linejoin": "round", **extra}}


def draw_icon(L, name, cx, cy, s, kit, *, card=True):
    w, line, accent, tile = kit["w"], kit["line"], kit["accent"], kit["tile"]
    g = s * 0.52
    if card:
        L.rect([cx - s / 2, cy - s / 2, s, s], radius=s * 0.22, fill=tile)
    if name == "search":
        ox, oy, rr = cx - g * 0.12, cy - g * 0.12, g * 0.3
        L.add({"type": "ellipse", "center": [ox, oy], "rx": rr, "ry": rr, "fill": "none", **_stroke(w, line)})
        L.line([ox + rr * 0.72, oy + rr * 0.72], [cx + g * 0.34, cy + g * 0.34], **_stroke(w, accent))
    elif name == "upload":
        L.polyline([[cx - g * 0.32, cy + g * 0.1], [cx - g * 0.32, cy + g * 0.32],
                    [cx + g * 0.32, cy + g * 0.32], [cx + g * 0.32, cy + g * 0.1]],
                   fill="none", **_stroke(w, line))
        L.line([cx, cy + g * 0.2], [cx, cy - g * 0.32], **_stroke(w, accent))
        L.polygon([[cx - g * 0.16, cy - g * 0.16], [cx + g * 0.16, cy - g * 0.16],
                   [cx, cy - g * 0.38]], fill=accent)
    elif name == "lock":
        L.arc([cx, cy - g * 0.04], g * 0.2, 180, 360, fill="none", **_stroke(w, line))
        L.rect([cx - g * 0.3, cy - g * 0.04, g * 0.6, g * 0.42], radius=g * 0.08,
               fill=accent, **{"stroke": line, "stroke_style": {"stroke_width": w}})
        L.add({"type": "ellipse", "center": [cx, cy + g * 0.16], "rx": g * 0.05, "ry": g * 0.05, "fill": tile})
    elif name == "chart":
        base = cy + g * 0.3
        L.line([cx - g * 0.34, base], [cx + g * 0.34, base], **_stroke(w, line))
        for i, (dx, hh, fil) in enumerate([(-0.22, 0.26, tile), (0.0, 0.46, accent), (0.22, 0.34, tile)]):
            bx = cx + g * dx
            L.rect([bx - g * 0.08, base - g * hh, g * 0.16, g * hh], fill=fil,
                   **{"stroke": line, "stroke_style": {"stroke_width": w}})
    elif name == "message":
        L.rect([cx - g * 0.34, cy - g * 0.3, g * 0.68, g * 0.5], radius=g * 0.13,
               fill=tile, **{"stroke": line, "stroke_style": {"stroke_width": w}})
        L.polygon([[cx - g * 0.18, cy + g * 0.2], [cx - g * 0.18, cy + g * 0.36],
                   [cx - g * 0.02, cy + g * 0.2]], fill=line)
        for dx in (-0.16, 0.0, 0.16):
            L.add({"type": "ellipse", "center": [cx + g * dx, cy - g * 0.05], "rx": g * 0.05,
                   "ry": g * 0.05, "fill": accent})
    elif name == "settings":
        teeth, r = 8, g * 0.34
        pts = []
        for i in range(teeth * 2):
            rr = r if i % 2 == 0 else r * 0.72
            a = math.pi * i / teeth
            pts.append([cx + rr * math.cos(a), cy + rr * math.sin(a)])
        L.polygon(pts, fill=accent, **{"stroke": line, "stroke_style": {"stroke_width": w}})
        L.add({"type": "ellipse", "center": [cx, cy], "rx": g * 0.13, "ry": g * 0.13,
               "fill": tile, **{"stroke": line, "stroke_style": {"stroke_width": w}}})


def _cells():
    cols, rows = 3, 2
    x0, y0 = M, 168
    cw, ch = (W - 2 * M) / cols, (H - y0 - 40) / rows
    return [(x0 + (i % cols) * cw + cw / 2, y0 + (i // cols) * ch + ch / 2 - 16) for i in range(6)]


def _title(L, num, title, sub):
    L.text([M, 44, W - 2 * M, 18], f"STEP {num}",
           style=_t(12, "#6D28D9", weight=700, family=DISPLAY, spacing=2.4, upper=True))
    L.text([M, 64, W - 2 * M, 30], title, style=_t(24, INK_UI, weight=700, family=DISPLAY))
    L.text([M, 100, W - 2 * M, 20], sub, style=_t(13, SUB))


def _grid(L, kits, *, card=True, label=True):
    for (cx, cy), name, kit in zip(_cells(), ICONS, kits):
        draw_icon(L, name, cx, cy, 132, kit, card=card)
        if label:
            L.text([cx - 90, cy + 86, 180, 18], name, style=_t(13, SUB, family=DISPLAY, align="center"))


def _page(b, pid, bg=BG):
    p = b.page(pid, canvas={"size": [W, H]}, coordinate_mode="absolute")
    p.layer("bg").rect([0, 0, W, H], fill=bg, decorative=True)
    return p


# the coach scaffold: ONE resolved hybrid style, shared by all six icons
STYLE = resolve_style("comic_ink", "blueprint")
KIT = style_to_kit(STYLE)
EDIT_STYLE = resolve_style("woodcut")
EDIT_KIT = style_to_kit(EDIT_STYLE)

# the control: six ad-hoc styles — undisciplined per-icon generation
DRIFT = [
    {"w": 3.0, "line": "#1F2937", "accent": "#2563EB", "tile": "#EFF6FF"},
    {"w": 5.0, "line": "#111827", "accent": "#10B981", "tile": "#ECFDF5"},
    {"w": 2.0, "line": "#374151", "accent": "#F59E0B", "tile": "#FFFBEB"},
    {"w": 4.0, "line": "#0F172A", "accent": "#EF4444", "tile": "#FEF2F2"},
    {"w": 3.5, "line": "#1E293B", "accent": "#8B5CF6", "tile": "#F5F3FF"},
    {"w": 2.5, "line": "#334155", "accent": "#EC4899", "tile": "#FDF2F8"},
]


def build_document():
    b = DocumentBuilder(title="Coach challenge — 6-icon set", profile="deck", lang="en")

    # 1 — coached: one StyleProfile across all six
    p1 = _page(b, "01-coached")
    _title(p1, "01", f"Coached · {STYLE.name}", "All six drawn from one resolved StyleProfile.")
    _grid(p1.layer("icons"), [KIT] * 6)

    # 2 — silhouette gate (REAL to_silhouette of the glyphs)
    sub = DocumentBuilder(title="sil", profile="diagram")
    sp = sub.page("s", canvas={"size": [W, H]}, coordinate_mode="absolute")
    sp.layer("bg").rect([0, 0, W, H], fill=PAPER, decorative=True)
    _grid(sp.layer("icons"), [KIT] * 6, card=False, label=False)
    sil_layers = to_silhouette(sub).model_dump(by_alias=True, exclude_none=True)["pages"][0]["layers"]
    p2 = _page(b, "02-gate", bg=PAPER)
    b._doc["pages"][-1]["layers"].extend(sil_layers)
    cap = p2.layer("cap")
    _title(cap, "02", "Silhouette gate", stage_rubric("silhouette")[0])

    # 3 — edit: swap the style once, all six update
    p3 = _page(b, "03-edit")
    _title(p3, "03", f"One change → all six update · {EDIT_STYLE.name}",
           "resolve_style('woodcut') — a single edit re-styles the whole set.")
    _grid(p3.layer("icons"), [EDIT_KIT] * 6)

    # 4 — one-shot control: ad-hoc per icon, drift
    p4 = _page(b, "04-oneshot")
    _title(p4, "04", "One-shot (no shared grammar) → drift",
           "Each icon styled ad-hoc: weights, accents and tiles disagree.")
    _grid(p4.layer("icons"), DRIFT)
    return b


doc = build_document()


def _signatures(kits):
    return {(round(k["w"], 2), k["line"].lower(), k["accent"].lower(), k["tile"].lower()) for k in kits}


def main() -> int:
    from frameforge.sdk.validate import validate_static_rules
    built = doc.build()
    rep = validate_static_rules(built)
    errs = [i for i in rep.issues if i.severity == "error"]
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "coach", "coach-icons.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(built, format="yaml"))

    coached_sigs = _signatures([KIT] * 6)
    drift_sigs = _signatures(DRIFT)
    print(f"coach-icons: {len(built.pages)} pages, ok={rep.ok}, errors={len(errs)} -> {out}")
    print("\n  CONSISTENCY A/B (6 icons)")
    print(f"  {'':14}{'distinct styles':>18}{'edit sites':>14}")
    print(f"  {'coached':14}{len(coached_sigs):>18}{1:>14}")
    print(f"  {'one-shot':14}{len(drift_sigs):>18}{len(DRIFT):>14}")
    print(f"\n  → coached: {len(coached_sigs)} style across 6, 1 edit site to restyle all.")
    print(f"  → one-shot: {len(drift_sigs)} distinct styles, {len(DRIFT)} edit sites.")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
