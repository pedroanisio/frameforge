#!/usr/bin/env python3
"""Worked example of the SDK's clip + author-intent helpers.

Three things that previously needed hand-written style bags or per-object flags,
now first-class on the builder:

  * ``group(clip=...)`` / ``clip_rect`` / ``clip_circle`` — mask a group's contents
    to a region (a panel, a vignette), lowering to ``style.clip_path``;
  * ``page.bleed()``     — a block whose objects are ``decorative`` (may run off
    the canvas without tripping the containment SHOULD);
  * ``page.lettering()`` — a block of captions exempt from the tabular-box-model
    heuristic, so freeform lettering need not be a grid group or TableObject.

Run from the repository root::

    uv run python examples/clip_and_lettering_demo.py   # build, validate, write the fixture
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    clip_circle,
    clip_rect,
    grid,
    linear_gradient,
)

W, H = 900, 600
CANVAS = {"size": [W, H], "units": "px"}
INK, PAPER, ACCENT, SUB = "#16202b", "#f4f1ea", "#e0633b", "#6b7787"
GRAD = linear_gradient([("#7028e4", 0), ("#e5b2ca", 1)], angle=45)

STYLES = {
    "title": dict(font_family=["DejaVu Sans", "Arial", "sans-serif"], font_size=24,
                  font_weight=800, color=INK, letter_spacing=-0.5),
    "cap":   dict(font_family=["DejaVu Sans Mono", "monospace"], font_size=13,
                  color=SUB, letter_spacing=0.5),
    "lbl":   dict(font_family=["DejaVu Sans", "Arial", "sans-serif"], font_size=14,
                  font_weight=700, color=INK),
}


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="SDK clip + lettering demo", profile="diagram", lang="en")
    for name, style in STYLES.items():
        b.define_text_style(name, **style)
    p = b.page("clip_and_lettering", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    p.rect([0, 0, W, H], fill=PAPER)
    p.text([40, 26, W - 80, 30], "Clip & author-intent helpers", style="title")

    # 1 — group(clip=rect): a big gradient + overflowing circles, masked to a panel
    pa = [60, 90, 360, 320]
    p.group(
        [{"type": "rect", "box": [20, 50, 460, 400], "fill": GRAD},
         {"type": "ellipse", "center": [60, 110], "rx": 90, "ry": 90, "fill": "#ffffff",
          "opacity": 0.35},
         {"type": "ellipse", "center": [430, 400], "rx": 120, "ry": 120, "fill": INK,
          "opacity": 0.35}],
        clip=clip_rect(pa))
    p.rect(pa, fill=None, stroke=INK, stroke_style={"stroke_width": 3})
    p.text([60, 420, 360, 18], "group(clip=clip_rect(box)) — masked to the panel",
           style="cap")

    # 2 — clip_circle on a boxed rect: a circular vignette derived from the box
    pb = [500, 90, 320, 320]
    p.rect(pb, fill=GRAD, style={"clip_path": clip_circle()})
    p.text([500, 420, 320, 18], "rect + clip_circle() — derived from the box",
           style="cap")

    # 3 — bleed(): a diagonal flourish that runs off the canvas (no containment warn)
    with p.bleed():
        p.polygon([[-60, 470], [W + 60, 250], [W + 60, 300], [-60, 520]],
                  fill=ACCENT, opacity=0.18)

    # 4 — lettering(): six captions in a regular grid, exempt from tabular-box-model
    cells = grid([60, 470, W - 120, 96], cols=3, count=6, gap=18, row_gap=14)
    notes = ["mask a group", "vignette art", "panel borders",
             "bleed past edge", "freeform captions", "zero warnings"]
    with p.lettering():
        for box, note in zip(cells, notes):
            p.text([box[0], box[1] + box[3] / 2 - 9, box[2], 18], f"· {note}", style="lbl")
    return b


def main() -> int:
    b = build()
    out = os.path.join(ROOT, "tests", "fixtures", "sdk-clip-and-lettering.fg.yaml")
    report = b.write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warnings)} -> {out}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
