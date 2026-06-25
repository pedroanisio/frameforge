#!/usr/bin/env python3
"""Everything together — coach (process) + landing kit (vocabulary) + silhouette gate.

This composes the session's new pieces into one pipeline on a single subject (a
startup-launch rocket hero):

  scaffold   coach.parse_intent → resolve_style(hybrid) → create_plan/validate_order
  vocabulary the landing_headers illustration kit (rocket, posed figures, blob…)
  gate       coach.to_silhouette + stage_rubric  (the same gate now on the MCP tools)
  grammar    the resolved StyleProfile palette recolors the *same* geometry

Pages: 01 Construction (neutral volumes + guides) · 02 Silhouette gate (flattened +
rubric) · 03 Styled (palette from the resolved style). Reuses existing assets — the
only new code here is the wiring.

    uv run python examples/coach_pipeline.py out/coach/coach-pipeline.fg.yaml
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "examples"))     # to reuse the landing kit
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize  # noqa: E402
from framegraph.sdk.paint import linear_gradient, rgba  # noqa: E402
from framegraph.coach import (  # noqa: E402  — the PROCESS layer
    create_plan, parse_intent, resolve_style, stage_rubric, to_silhouette, validate_order,
)
import landing_headers as kit  # noqa: E402  — the VOCABULARY layer (reused)
from landing_headers import (  # noqa: E402
    W, H, CARDBOX, PADX, hero_card, header_chrome, hero_text,
    blob, rocket, gear, ladder, person_posed, sparkles, ring, dot_grid, cross,
)

INK_UI, SUB = "#1E2030", "#8A90A6"
DISPLAY = ["Poppins", "Inter Display", "Inter", "Arial", "sans-serif"]
SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]

# ---- the coach scaffold (deterministic, shared by every stage) ------------- #
INTENT = parse_intent("a startup launch hero, comic_ink blueprint, three-quarter")
STYLE = resolve_style("comic_ink", "blueprint")
PLAN = create_plan()
PLAN_OK = validate_order(PLAN.layers) == []

# ---- style grammar -> concrete kit colours (roles pulled from the palette) - #
_pal = [c.lower() for c in STYLE.palette]
_ink = STYLE.palette[0]
_blue = next((c for c in STYLE.palette if c.lower() in ("#3b6ea5", "#0b5fbf")), _ink)
_blue2 = next((c for c in STYLE.palette if c.lower() == "#0b5fbf"), _blue)
_lightblue = next((c for c in STYLE.palette if c.lower() == "#9fd0ff"), "#9FD0FF")
_pop = next((c for c in STYLE.palette if c.lower() == "#e0653c"), _blue)

NEUTRAL = dict(blob="#DEE1EA", body="#EEF0F5", accent="#AEB4C2", accent2="#C4C9D6",
               win="#C4C9D6", shirt="#B6BCCB", pants="#9AA1B2", hair="#8E94A4",
               skin="#CDD2DB", gear="#B6BCCB", gear2="#C4C9D6", ladder="#C9CDD6",
               shadow="#9AA1B2", deco="#C4C9D6", deco2="#AEB4C2")
STYLED = dict(blob=linear_gradient([(_blue, 0), (_blue2, 100)], angle=135),
              body="#F4F7FC", accent=_ink, accent2=_blue, win=_lightblue,
              shirt="#1F3A6E", pants=_ink, hair=_ink, skin="#F4C9A6",
              gear=_blue, gear2=_blue2, ladder=_lightblue, shadow="#08315F",
              deco=_blue, deco2=_pop)


def scene(L, k, *, guides=False):
    """The launch tableau — drawn ONCE, recoloured by the kit dict ``k``."""
    bcx, bcy = 1150, 470
    L.add({"type": "ellipse", "center": [bcx, bcy + 214], "rx": 268, "ry": 30,
           "fill": rgba(k["shadow"], 0.10), "decorative": True})
    blob(L, bcx - 8, bcy, 266, k["blob"], squish=1.0, rot=0.3)
    if guides:
        for gx, gy, r in ((bcx, bcy - 40, 150), (bcx, bcy + 70, 120)):
            L.add({"type": "ellipse", "center": [gx, gy], "rx": r, "ry": r, "fill": "none",
                   "stroke": rgba("#6D28D9", 0.30),
                   "stroke_style": {"stroke_width": 1.4, "stroke_dasharray": [5, 5]}})
    ladder(L, 1276, 472, 64, 150, k["ladder"])
    rocket(L, bcx, bcy + 135, 300, body=k["body"], accent=k["accent"], accent2=k["accent2"], win=k["win"])
    person_posed(L, head=[978, 486], neck=[978, 510], hip=[978, 576],
                 arms=[([968, 520], [958, 556], [998, 560])],
                 back_arm=([990, 516], [1016, 496], [1042, 476]),
                 legs=[([970, 576], [964, 604], [960, 628]), ([988, 576], [995, 604], [1000, 628])],
                 skin=k["skin"], shirt=k["shirt"], pants=k["pants"], hair=k["hair"])
    person_posed(L, head=[1322, 440], neck=[1322, 464], hip=[1322, 524],
                 arms=[([1308, 472], [1282, 446], [1238, 414]), ([1336, 472], [1312, 438], [1258, 400])],
                 legs=[([1314, 524], [1310, 560], [1306, 596]), ([1330, 524], [1336, 560], [1342, 596])],
                 skin=k["skin"], shirt=k["shirt"], pants=k["pants"], hair=k["hair"])
    gear(L, 948, 596, 27, k["gear"])
    gear(L, 986, 620, 16, k["gear2"])
    ring(L, bcx + 252, bcy - 200, 14, k["deco"], 3)
    dot_grid(L, bcx - 324, bcy + 92, 3, 3, 13, 3, rgba(k["accent"], 0.55))
    sparkles(L, [(bcx + 248, bcy + 44, 7, k["deco"]), (bcx + 64, bcy - 250, 6, k["deco2"]),
                 (bcx - 252, bcy - 150, 5, k["deco2"])])
    cross(L, bcx - 300, bcy + 44, 8, k["deco"])


def _t(size, color, *, weight=400, family=None, spacing=None, upper=False):
    s = {"font_family": family or SANS, "font_size": size, "font_weight": weight,
         "color": color, "white_space": "nowrap"}
    if spacing is not None:
        s["letter_spacing"] = spacing
    if upper:
        s["text_transform"] = "uppercase"
    return s


def _scaffold_note(L, y):
    L.text([CARDBOX[0] + PADX, y, 700, 16],
           f"coach ·  intent: launch hero   style: {STYLE.name}   "
           f"layers: {'valid' if PLAN_OK else 'INVALID'}",
           style=_t(12.5, "#6D28D9", weight=600, family=DISPLAY, spacing=0.4))


def build_document():
    b = DocumentBuilder(title="Coach pipeline — all together", profile="deck", lang="en")

    # 01 — construction (vocabulary, neutral) + the coach scaffold
    L1 = hero_card(b, "01-construction")
    header_chrome(L1, active=1)
    scene(L1.layer("scene"), NEUTRAL, guides=True)
    hero_text(L1, ["Launch", "faster"],
              "Block the scene as flat volumes first — the coach scaffold drives it, no detail yet.")
    _scaffold_note(L1, CARDBOX[1] + 700)

    # 02 — silhouette gate (REAL to_silhouette of the scene) + rubric
    sub = DocumentBuilder(title="sil", profile="diagram")
    sp = sub.page("s", canvas={"size": [W, H]}, coordinate_mode="absolute")
    sp.layer("bg").rect([0, 0, W, H], fill="#FFFFFF", decorative=True)
    scene(sp.layer("scene"), NEUTRAL)
    sil = to_silhouette(sub).model_dump(by_alias=True, exclude_none=True)["pages"][0]["layers"]
    p2 = b.page("02-gate", canvas={"size": [W, H]}, coordinate_mode="absolute")
    p2.layer("bg").rect([0, 0, W, H], fill="#FFFFFF", decorative=True)
    b._doc["pages"][-1]["layers"].extend(sil)
    cap = p2.layer("cap")
    cap.text([PADX, 56, 900, 26], "Silhouette gate — readable before detail?",
             style=_t(22, INK_UI, weight=700, family=DISPLAY))
    ry = 96
    for line in stage_rubric("silhouette"):
        cap.text([PADX, ry, 460, 20], "•  " + line, style=_t(12.5, SUB))
        ry += 24

    # 03 — styled (same geometry, recoloured by the resolved StyleProfile)
    L3 = hero_card(b, "03-styled")
    header_chrome(L3, active=1)
    scene(L3.layer("scene"), STYLED)
    hero_text(L3, ["Launch", "faster"],
              "Same construction, recoloured by the resolved style grammar — one source of truth.")
    _scaffold_note(L3, CARDBOX[1] + 700)
    return b


doc = build_document()


def main() -> int:
    from framegraph.sdk.validate import validate_static_rules
    built = doc.build()
    rep = validate_static_rules(built)
    errs = [i for i in rep.issues if i.severity == "error"]
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "coach", "coach-pipeline.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(built, format="yaml"))
    print(f"coach-pipeline: {len(built.pages)} pages, ok={rep.ok}, errors={len(errs)} -> {out}")
    print(f"  scaffold: style={STYLE.name}  layers_valid={PLAN_OK}  kit={kit.__name__}")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
