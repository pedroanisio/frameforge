#!/usr/bin/env python3
"""Declutter + overflow signals — sdk.separate and overflow_report, end to end.

A worked pair for the two layout-feedback features:

* **Collision/label separation** (``sdk.separate``): a station rail whose four
  label chips were authored on one row at a 76 px pitch — 96 px chips, so each
  neighbour pair overlaps by 20 px, exactly what the static ``overlap`` audit
  WARNs about. ``apply_separation(gap=6)`` spreads the row apart (horizontal is
  the cheapest escape at this geometry), clamped to the cluster box, and the
  audit goes quiet. Anchor ticks stay put, so the applied displacement is
  visible. Page 1 is the authored state, page 2 the separated state.

* **Typed layout-overflow signals** (``overflow_report`` /
  ``diagnostics["overflow"]``): the same page carries a caption whose text
  silently exceeds its two-line box (a clip signal, ``acknowledged: false``)
  and a footnote authored ``overflow: visible`` whose spill stays fully
  on-canvas (a spill signal, acknowledged). The script prints the typed report
  so both losses are visible before any pixels.

Run from the repository root::

    uv run python static/examples/declutter_and_overflow.py
    # writes _tmp/declutter/{before,after}.svg + YAML, prints both reports
"""
from __future__ import annotations

import copy
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT_DIR = os.path.join(ROOT, "_tmp", "declutter")
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    apply_separation,
    overflow_report,
    render_page_svgs,
    serialize,
    validate_static_rules,
)

INK = "#1c2733"
ACCENT = "#3b6ea5"
# translucent chip fill: where authored chips overlap, the double-painted
# band darkens — the before state SHOWS its collision instead of hiding it
CHIP_FILL = "rgba(59, 110, 165, 0.16)"
CHIP_EDGE = "#c5d2e0"
TICK = "#98a4b3"

STATIONS = ("Intake", "Triage", "Compose", "Verify")
DOT_XS = (126, 202, 278, 354)          # 76 px pitch, centred on the 480 canvas
RAIL_Y = 120
# the no-overlap scope (a free group), exactly one chip-row tall: the world
# clamp blocks the vertical escape, so the solver's feasibility-aware axis
# fallback resolves the cluster as a spread ROW (which is what a label row
# wants), not a staircase
CLUSTER_BOX = [30, 170, 420, 40]

CAPTION = ("Figure 1 — four stations on one rail; every chip was authored on "
           "the same row at a 76 px pitch, so 96 px chips overlap by 20 px "
           "until the solver spreads the row apart.")


def _chip(cid: str, x: float, y: float, text: str) -> dict:
    """A label chip: a box-bearing sub-group (so the solver moves it as one
    unit) holding a decorative fill rect + the centred label text."""
    return {"type": "group", "id": cid, "box": [x, y, 96, 26], "children": [
        {"type": "rect", "id": f"{cid}-bg", "box": [0, 0, 96, 26],
         "fill": CHIP_FILL, "stroke": CHIP_EDGE,
         "stroke_style": {"stroke_width": 1}, "decorative": True},
        {"type": "text", "id": f"{cid}-t", "box": [0, 0, 96, 26], "text": text,
         "style": {"font_size": 11, "color": INK, "align": "center",
                   "vertical_align": "middle"}},
    ]}


def _diagram_page(b: DocumentBuilder, page_id: str, note: str) -> None:
    pg = b.page(page_id, canvas={"size": [480, 400], "units": "px"})
    pg.text([30, 18, 420, 22], note, id=f"{page_id}-headline",
            style={"font_size": 14, "color": INK, "font_weight": 600})
    # the rail + station dots (decorative art: exempt from the overlap scope)
    pg.add({"type": "line", "id": f"{page_id}-rail",
            "from": [60, RAIL_Y], "to": [420, RAIL_Y],
            "stroke": INK, "stroke_style": {"stroke_width": 1.5},
            "decorative": True})
    for i, dx in enumerate(DOT_XS):
        pg.add({"type": "ellipse", "id": f"{page_id}-dot-{i}",
                "center": [dx, RAIL_Y], "rx": 7, "ry": 7, "fill": ACCENT,
                "decorative": True})
        # anchor tick down to the label row — it stays put after separation,
        # so the solver's applied displacement is visible in the after state
        pg.add({"type": "line", "id": f"{page_id}-tick-{i}",
                "from": [dx, RAIL_Y + 9], "to": [dx, CLUSTER_BOX[1]],
                "stroke": TICK, "stroke_style": {"stroke_width": 1},
                "decorative": True})
    # the chip cluster: authored overlapping (one row, 76 px pitch, 96 wide)
    pg.group([_chip(f"{page_id}-l{i}", dx - 48 - CLUSTER_BOX[0], 7, txt)
              for i, (dx, txt) in enumerate(zip(DOT_XS, STATIONS))],
             id=f"{page_id}-labels", box=CLUSTER_BOX)
    # overflow demonstrations (top-level, untouched by separation):
    # a caption clipped to its two-line box (silent clip -> signal), and a
    # footnote whose authored `overflow: visible` spill stays on-canvas
    pg.text([30, 258, 330, 30], CAPTION, id=f"{page_id}-caption",
            style={"font_size": 11, "line_height": 1.3, "color": INK})
    pg.text([374, 258, 76, 14], "Footnote: all units are page px.",
            id=f"{page_id}-footnote",
            style={"font_size": 11, "line_height": 1.3, "color": INK,
                   "overflow": "visible"})


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Declutter + overflow signals", profile="deck")
    _diagram_page(b, "before", "Authored: the label row collides")
    return b


def _codes(data: dict) -> set[str]:
    return {i.rule_id for i in validate_static_rules(data).issues}


def _retitle(data: dict, object_id: str, text: str) -> None:
    """Rewrite one text object's content in a plain document dict."""
    def walk(node):
        if isinstance(node, dict):
            if node.get("id") == object_id and node.get("type") == "text":
                node["text"] = text
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(data)


def main() -> int:
    data = build().build_dict()
    fixed = apply_separation(copy.deepcopy(data), gap=6.0)
    fixed["pages"][0]["id"] = "after"
    _retitle(fixed, "before-headline",
             "apply_separation(gap=6): the row resolved, audit-clean")

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, doc in (("before", data), ("after", fixed)):
        svg = render_page_svgs(doc)[0]
        with open(os.path.join(OUT_DIR, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
        with open(os.path.join(OUT_DIR, f"{name}.fg.yaml"), "w", encoding="utf-8") as fh:
            fh.write(serialize(doc, format="yaml"))

    print(f"audit codes before: {sorted(_codes(data)) or '—'}")
    print(f"audit codes after : {sorted(_codes(fixed)) or '—'}")
    print("overflow signals:")
    for sig in overflow_report(data):
        print(f"  #{sig.id}: {sig.source}/{sig.kind} policy={sig.policy} "
              f"box={sig.box[2]:g}×{sig.box[3]:g} needs "
              f"{sig.needed[0]:.0f}×{sig.needed[1]:.0f} "
              f"acknowledged={sig.acknowledged}")
    print(f"Wrote before/after SVG + YAML to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
