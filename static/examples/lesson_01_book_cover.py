#!/usr/bin/env python3
"""Tutorial lesson 01 — reconstruct a photographed book cover as FrameGraph vectors.

The target is a photograph of the cloth binding of *Typesetting: A Primer of
Information About Working at the Case* (A. A. Stewart, 1918), 444x669 px, at
``docs/tutorial/lesson-01/target/lesson-01.png``. This client rebuilds it as pure
FrameGraph objects: no pixels from the source are pasted, every mark is a rect, a
gradient, a pattern or a text run that the validator can inspect.

Every number below was *measured*, not eyeballed — the lesson at
``docs/tutorial/lesson-01/index.md`` records which MCP call produced each one:

- the board/hinge/fore-edge bounds and the cloth colours: pixel profiles across
  the source (``measure_image`` for the coordinate frame);
- the eight text lines' cap bands and centres: a gold-ink mask over the source;
- the font sizes: solved from EB Garamond's real cap-height metric
  (cap/em = 0.658), so ``size = cap_px / 0.658``;
- the per-line tracking: solved from the font's own advance widths against each
  line's measured width;
- the weave pitch (3.2 px): an FFT of a text-free patch of the cloth.

Run from the repository root::

    uv run python static/examples/lesson_01_book_cover.py   # writes _tmp/lesson-01/*

⚠ ARCHITECTURAL CONTRACT (PALS's LAW): a reconstruction is a *claim* that the
output resembles the source. This client validates the document against the model
and the static rules, but resemblance itself is only established by rendering and
comparing against the reference (``compare_images`` / the geometry diff in the
lesson). Treat an unrendered reconstruction as unverified.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    grid_pattern,
    hatch,
    linear_gradient,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# ---- measured constants ----------------------------------------------------
W, H = 444, 669           # source raster size
FACE_CX = 233.9           # centre of the front board (NOT the canvas centre:
                          # the spine roll eats the left edge of the photo)
SERIF = "EB Garamond"
GOLD = "#faf7ad"          # median of the brightest 1% of the title band
CAP_EM = 0.658            # EB Garamond sCapHeight / unitsPerEm

# (text, cap_top_px, cap_height_px, letter_spacing_px)
TITLE = ("TYPESETTING", 121, 32, -0.83)
SUBTITLE = [
    ("A PRIMER OF INFORMATION ABOUT", 0.18),
    ("WORKING AT THE CASE, JUSTIFYING,", -0.01),
    ("SPACING, CORRECTING, MAKING-UP,", -0.39),
    ("AND OTHER OPERATIONS EMPLOYED", -0.36),
    ("IN SETTING TYPE BY HAND", 0.05),
]
SUBTITLE_TOP, SUBTITLE_LEADING, SUBTITLE_CAP = 181, 21, 13
BYLINE = ("BY", 358, 9, 0.72)
AUTHOR = ("A. A. STEWART", 377, 16, -0.67)


def build():
    """Return the reconstruction as a core-model ``Document``."""
    b = DocumentBuilder(title="Typesetting - A. A. Stewart (cover)", profile="deck")
    page = b.page("cover", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    lay = page.layer("main")

    # the sheet the book was photographed on
    lay.rect([0, 0, W, H], fill="#f1f3f4")

    # the cloth board, carrying the measured left->right lighting gradient
    lay.rect([8, 1, 435, 663], fill=linear_gradient(
        [("#154349", 0.0), ("#214c51", 0.45), ("#2d555a", 1.0)], angle="90deg"))

    # the weave: pitch and amplitude both measured off the source, so the
    # texture reads as cloth without inventing a level of detail
    lay.rect([8, 1, 435, 663], fill=grid_pattern(fg="rgba(255,255,255,0.055)",
                                                 scale=3.2))
    lay.rect([8, 1, 435, 663], fill=hatch(fg="rgba(0,0,0,0.05)", scale=3.2,
                                          angle=45))

    # spine roll, hinge shadow, fore-edge and head highlights
    lay.rect([8, 1, 15, 663], fill=linear_gradient(
        [("#3a5c5e", 0.0), ("#416264", 0.35), ("#2a4d52", 1.0)], angle="90deg"))
    lay.rect([23, 1, 8, 663], fill=linear_gradient(
        [("#0d3c40", 0.0), ("#123f44", 1.0)], angle="90deg"))
    lay.rect([436, 1, 7, 663], fill="#2e565a")
    lay.rect([31, 1, 412, 7], fill="#285154")

    _typography(lay)
    return b.build()


def _line(lay, text, cap_top, cap_px, tracking):
    """Place one line by its measured cap band.

    The renderer emits ``dominant-baseline="central"`` at the box's vertical
    centre, which lands the *cap-height centre* on the box centre. So the box is
    derived from the measurement rather than nudged into place by hand.
    """
    size = cap_px / CAP_EM
    box_h = size * 1.6
    cy = cap_top + cap_px / 2
    lay.text([FACE_CX - 210, cy - box_h / 2, 420, box_h], text, style={
        "color": GOLD,
        "font_family": SERIF,
        "font_size": round(size, 2),
        "text_align": "center",
        "letter_spacing": round(tracking, 2),
    })


def _typography(lay):
    text, cap_top, cap_px, track = TITLE
    _line(lay, text, cap_top, cap_px, track)
    for i, (line, track) in enumerate(SUBTITLE):
        _line(lay, line, SUBTITLE_TOP + i * SUBTITLE_LEADING, SUBTITLE_CAP, track)
    for text, cap_top, cap_px, track in (BYLINE, AUTHOR):
        _line(lay, text, cap_top, cap_px, track)


def main():
    doc = build()
    report = validate_static_rules(doc)
    if not report.ok:
        for issue in report.issues:
            print(f"  {issue}")
        raise SystemExit("validation failed")

    from framegraph.sdk import render_page_svgs, serialize

    out = os.path.join(ROOT, "_tmp", "lesson-01")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "cover.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    for i, svg in enumerate(render_page_svgs(doc, base_dir=ROOT), 1):
        with open(os.path.join(out, f"page-{i:03d}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print(f"OK: validated + rendered -> {out}")


if __name__ == "__main__":
    main()
