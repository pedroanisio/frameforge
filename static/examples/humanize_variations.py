#!/usr/bin/env python3
"""The Humanize Hand — a specimen sheet of the seeded imperfection pass.

Every panel draws the *same* four-part mark — a square, a ring, a diagonal and a
filled triangle — under a different `humanize` spec, so each channel is legible in
isolation and in combination. Text labels stay crisp (the hand only ever wobbles
geometry). Everything is deterministic: same seed -> byte-identical output; bump
the seed to re-perform the page.

Two plates:
  1. Channels in isolation — roughen (geometry wobble), drift_deg (tilt),
     weight (stroke pressure), opacity (ink density).
  2. Grain (hand tension), combined presets, round-robin (one spec, never
     stamped) and re-perform (same spec, a new seed).

Run from the repository root::

    uv run python static/examples/humanize_variations.py
    uv run framegraph-render <(python static/examples/humanize_variations.py --stdout) --to png   # optional
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder  # noqa: E402

# A hand's world: warm paper, one ink, one earth-red accent (the build_a6 lineage).
BG, INK, MUT, HAIR, ACCENT, FILL = "#F4EFE6", "#23201A", "#8A7F6B", "#DAD1BF", "#B04A2F", "#EAE2D1"

W, H, M = 840, 940, 48
COLS = [M, M + 186, M + 2 * 186, M + 3 * 186]   # four columns
S = 84                                           # mark size
ROWS = [180, 372, 564, 756]                      # row baselines (motif tops)


def _hz(spec):
    """A per-object humanize override, or nothing (the crisp reference)."""
    return {"humanize": dict(spec)} if spec else {}


def mark(page, x, y, spec):
    """The four-part specimen mark. Each primitive exercises a different corner of
    the roughen converter (closed rect, closed curve, straight line, poly) and
    carries the panel's humanize spec so tilt/pressure/ink co-vary per object."""
    e = _hz(spec)
    page.rect([x, y, S, S], fill=FILL, stroke=INK,
              stroke_style={"stroke_width": 1.8, "stroke_linejoin": "round"}, **e)
    page.circle([x + S / 2, y + S / 2], S * 0.30, fill="none", stroke=ACCENT,
                stroke_style={"stroke_width": 1.7}, **e)
    page.line([x + 12, y + S - 12], [x + S - 12, y + 12], stroke=INK,
              stroke_style={"stroke_width": 1.3, "stroke_linecap": "round"}, **e)
    # Triangle centred on the cell centre — like the square, ring and diagonal — so a
    # per-object tilt rotates the whole mark coherently instead of detaching it.
    cx, cy, t = x + S / 2, y + S / 2, 14
    page.polygon([(cx, cy - t - 2), (cx - t, cy + t - 2), (cx + t, cy + t - 2)],
                 fill=ACCENT, **e)


def cell(page, col, row, spec, title, value=""):
    x, y = COLS[col], ROWS[row]
    mark(page, x, y, spec)
    page.text([x, y + S + 16, 150, 16], title, style="lab")
    if value:
        page.text([x, y + S + 32, 150, 14], value, style="val")


def _styles(b):
    serif = ["EB Garamond", "Georgia", "serif"]
    sans = ["Inter", "Helvetica", "Arial", "sans-serif"]
    b.define_text_style("h1", font_family=serif, font_size=27, font_weight=700, color=INK)
    b.define_text_style("lede", font_family=serif, font_size=13, italic=True, color=MUT)
    b.define_text_style("sec", font_family=sans, font_size=10.5, font_weight=700,
                        color=ACCENT, letter_spacing=1.4, text_transform="uppercase")
    b.define_text_style("lab", font_family=sans, font_size=12, font_weight=700, color=INK)
    b.define_text_style("val", font_family=["Fira Mono", "monospace"], font_size=10.5, color=MUT)
    b.define_text_style("foot", font_family=sans, font_size=9, color=MUT)
    b.define_text_style("plate", font_family=["Fira Mono", "monospace"], font_size=10,
                        font_weight=700, color=MUT, letter_spacing=1.2)


def _plate(b, pid, title, lede, plate_no):
    page = b.page(pid, canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute", reading_order=["title", "lede"]).layer("main")
    page.rect([0, 0, W, H], fill=BG, humanize={"enabled": False})   # paper stays crisp
    page.text([M, 44, 620, 30], title, id="title", style="h1")
    page.text([M, 78, 720, 18], lede, id="lede", style="lede")
    page.line([M, 104], [W - M, 104], stroke=HAIR, stroke_style={"stroke_width": 1.0},
              humanize={"enabled": False})
    page.text([W - M - 120, 44, 120, 14], plate_no, style="plate")
    page.text([M, H - 34, W - 2 * M, 14],
              "FrameGraph · humanize hand (roughen · drift · weight · opacity · grain) — "
              "deterministic, seeded; text is exempt.", style="foot")
    return page


def _row_header(page, row, text):
    page.text([M, ROWS[row] - 32, W - 2 * M, 16], text, style="sec")


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="The Humanize Hand — a specimen sheet", profile="diagram")
    _styles(b)

    # -- Plate I — one channel at a time --------------------------------------- #
    p = _plate(b, "channels", "The Humanize Hand",
               "One mark under many hands — the same geometry, each panel a different "
               "seeded imperfection.", "PLATE I / II")
    _row_header(p, 0, "roughen — straight geometry becomes hand-drawn, endpoint-anchored")
    cell(p, 0, 0, None, "reference", "humanize off")
    cell(p, 1, 0, {"seed": 1, "roughen": 0.6}, "roughen", "0.6")
    cell(p, 2, 0, {"seed": 1, "roughen": 1.2}, "roughen", "1.2")
    cell(p, 3, 0, {"seed": 1, "roughen": 2.0}, "roughen", "2.0")

    _row_header(p, 1, "drift_deg — a small per-object tilt, hard-bounded to the amplitude")
    cell(p, 0, 1, {"seed": 2, "drift_deg": 2}, "drift_deg", "2°")
    cell(p, 1, 1, {"seed": 2, "drift_deg": 4}, "drift_deg", "4°")
    cell(p, 2, 1, {"seed": 2, "drift_deg": 6}, "drift_deg", "6°")
    cell(p, 3, 1, {"seed": 2, "drift_deg": 9}, "drift_deg", "9°")

    _row_header(p, 2, "weight — stroke pressure  ·  opacity — ink density (geometry untouched)")
    cell(p, 0, 2, {"seed": 3, "weight": 0.30}, "weight", "0.30")
    cell(p, 1, 2, {"seed": 3, "weight": 0.70}, "weight", "0.70")
    cell(p, 2, 2, {"seed": 3, "opacity": 0.35}, "opacity", "0.35")
    cell(p, 3, 2, {"seed": 3, "opacity": 0.70}, "opacity", "0.70")

    # -- Plate II — grain, presets, variation ---------------------------------- #
    q = _plate(b, "grain-presets", "The Hand's Grain & Repertoire",
               "Tension over one spec, ready-made hands, and why repeats never stamp.",
               "PLATE II / II")
    base = {"seed": 5, "roughen": 0.8, "drift_deg": 2.5, "weight": 0.25, "opacity": 0.25}
    _row_header(q, 0, "grain — hand tension over one spec (roughen 0.8 · drift 2.5° · ink .25)")
    cell(q, 0, 0, {**base, "grain": 1.0}, "grain", "1.0 · tight")
    cell(q, 1, 0, {**base, "grain": 0.6}, "grain", "0.6")
    cell(q, 2, 0, {**base, "grain": 0.3}, "grain", "0.3")
    cell(q, 3, 0, {**base, "grain": 0.0}, "grain", "0.0 · loose")

    _row_header(q, 1, "presets — combined hands, light to expressive")
    cell(q, 0, 1, {"seed": 6, "roughen": 0.5, "drift_deg": 1.5, "weight": 0.15, "opacity": 0.10, "grain": 0.7}, "light")
    cell(q, 1, 1, {"seed": 6, "roughen": 1.0, "drift_deg": 2.5, "weight": 0.25, "opacity": 0.20, "grain": 0.5}, "studio")
    cell(q, 2, 1, {"seed": 6, "roughen": 1.3, "drift_deg": 3.5, "weight": 0.35, "opacity": 0.30, "grain": 0.4}, "heavy")
    cell(q, 3, 1, {"seed": 6, "roughen": 1.8, "drift_deg": 4.5, "weight": 0.48, "opacity": 0.40, "grain": 0.3}, "expressive")

    rr = {"seed": 8, "roughen": 1.2, "drift_deg": 3, "weight": 0.22, "opacity": 0.18, "grain": 0.5}
    _row_header(q, 2, "round-robin — one identical spec, four positions, never stamped")
    for c in range(4):
        cell(q, c, 2, rr, "same spec", f"take {c + 1}")

    rp = {"roughen": 1.2, "drift_deg": 3, "weight": 0.22, "opacity": 0.18, "grain": 0.5}
    _row_header(q, 3, "re-perform — same spec, a new seed is a fresh take")
    for c, sd in enumerate((1, 2, 3, 4)):
        cell(q, c, 3, {**rp, "seed": sd}, "seed", str(sd))

    return b


def main() -> int:
    from framegraph.sdk import render_page_svgs

    args = sys.argv[1:]
    doc = build().build()
    svgs = render_page_svgs(doc)
    if "--stdout" in args:
        sys.stdout.write(svgs[0])
        return 0
    here = os.path.dirname(os.path.abspath(__file__))
    for i, svg in enumerate(svgs, 1):
        out = os.path.join(here, f"humanize_variations-p{i}.svg")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
