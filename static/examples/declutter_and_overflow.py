#!/usr/bin/env python3
"""Declutter + overflow signals — sdk.separate and overflow_report, end to end.

A worked pair for the two layout-feedback features:

* **Collision/label separation** (``sdk.separate``): an annotated diagram whose
  callout labels were authored overlapping inside a free-layout group — exactly
  what the static ``overlap`` audit WARNs about. ``apply_separation`` resolves
  the cluster deterministically (labels pushed apart along the cheapest axis,
  clamped to the group box, ``gap`` clearance respected) and the audit goes
  quiet. Page 1 is the authored state, page 2 the separated state.

* **Typed layout-overflow signals** (``overflow_report`` /
  ``diagnostics["overflow"]``): the same page carries a caption whose text
  silently exceeds its box (a clip signal, ``acknowledged: false``) and a
  footnote authored ``overflow: visible`` (a spill signal, acknowledged). The
  script prints the typed report so the loss is visible before any pixels.

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
LABEL_FILL = "#eef3f9"

CAPTION = ("Figure 1 — the hub fans out to four stations; every label was "
           "authored at the same y and the cluster collides until the solver "
           "spreads it.")


def _label(lid: str, x: float, y: float, text: str) -> dict:
    """A callout label chip: box-bearing, so it participates in the audit."""
    return {"type": "text", "id": lid, "box": [x, y, 96, 26], "text": text,
            "style": {"font_size": 11, "color": INK, "align": "center",
                      "vertical_align": "middle", "background": LABEL_FILL}}


def _diagram_page(b: DocumentBuilder, page_id: str, note: str) -> None:
    pg = b.page(page_id, canvas={"size": [480, 340], "units": "px"})
    pg.text([24, 16, 432, 22], note,
            style={"font_size": 14, "color": INK, "font_weight": 600})
    # hub + spokes (decorative art: exempt from the overlap scope)
    pg.add({"type": "ellipse", "id": f"{page_id}-hub", "center": [240, 150],
            "rx": 26, "ry": 26, "fill": ACCENT, "decorative": True})
    for i, tip in enumerate(((120, 90), (360, 90), (120, 210), (360, 210))):
        pg.add({"type": "line", "id": f"{page_id}-spoke-{i}",
                "from": [240, 150], "to": list(tip),
                "stroke": INK, "stroke_style": {"stroke_width": 1.5},
                "decorative": True})
    # the label cluster: authored overlapping (same row, 60 px apart, 96 wide)
    pg.group([_label(f"{page_id}-l{i}", 40 + i * 60, 6, txt)
              for i, txt in enumerate(("Intake", "Triage", "Compose", "Verify"))],
             id=f"{page_id}-labels", box=[36, 240, 408, 60])
    # overflow demonstrations (top-level, untouched by separation):
    pg.text([24, 306, 300, 14], CAPTION, id=f"{page_id}-caption",
            style={"font_size": 11, "line_height": 1.3, "color": INK})
    pg.text([340, 306, 116, 14], "Footnote: measurements are page-space px.",
            id=f"{page_id}-footnote",
            style={"font_size": 11, "color": INK, "overflow": "visible"})


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Declutter + overflow signals", profile="deck")
    _diagram_page(b, "before", "Authored: the label cluster collides")
    return b


def _codes(data: dict) -> set[str]:
    return {i.rule_id for i in validate_static_rules(data).issues}


def main() -> int:
    data = build().build_dict()
    fixed = apply_separation(copy.deepcopy(data), gap=6.0)
    # rename the fixed page so both states can live side by side in one report
    fixed["pages"][0]["id"] = "after"
    for obj_holder in fixed["pages"][0]["layers"]:
        pass  # ids inside keep their authored "before-" prefix — provenance

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
