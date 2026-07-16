#!/usr/bin/env python3
"""Tutorial lesson 03 — reconstruct a typeset chapter-opening page.

The target is a 602x678 book page — chapter label, an origami-heart ornament, a
display title, a two-line drop cap and nine lines of *justified* body text —
at ``docs/tutorial/lesson-03/target/lesson-03.png``. This client rebuilds it as
FrameGraph objects: polygons for the ornament, text runs for everything else.

Where lesson 01 reconstructed a *photograph*, this page is *typesetting*, so the
numbers come from type metrics rather than colour profiles. The lesson at
``docs/tutorial/lesson-03/index.md`` records which MCP call produced each:

- the coordinate frame: ``measure_image``;
- the ornament's 4 facets: ``detect_regions`` (method=flat) — which works here,
  on flat vector-like shading, exactly where it failed on lesson 01's cloth;
- the body face + size: solved from *word* ink-widths. The text is justified, so
  line width is set by the justifier and cannot identify a size — but individual
  words are unstretched, and Gentium Book Plus fits their widths (sd 0.27 px),
  x-height (0.19 px) and ascender (0.16 px) simultaneously;
- the baselines: measured from each line's x-height band (leading 31.17 px);
- the justification: computed here, per line, as ``word_spacing`` — because
  ``text_align: justify`` is a NO-OP on SVG text (see below).

Run from the repository root::

    uv run python static/examples/lesson_03_chapter_page.py   # -> _tmp/lesson-03/

⚠ ARCHITECTURAL CONTRACT (PALS's LAW): this document validates clean, and its
first draft still had ragged-right body text — the model accepts
``text_align: justify``, the validator passes it, the renderer emits it, and SVG
ignores it. `ok: true` is not `correct: true`. Resemblance here is established
only by the geometry diff and ``compare_images`` recorded in the lesson.
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

from framegraph.sdk import DocumentBuilder  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# ---- measured constants ----------------------------------------------------
W, H = 602, 932
CX = 302.25               # the page's axis of symmetry, from the ornament trace
BODY_FACE = "Gentium Book Plus"
DISPLAY_FACE = "EB Garamond"      # a STAND-IN: no installed face matches the title
INK, GREY = "#1a1a1a", "#6f6f6f"
WING, INNER = "#93918f", "#767773"

# `dominant-baseline="central"` puts the font's CENTRAL baseline on the box
# centre. central sits (ascent + descent)/2 above the alphabetic baseline, so
# this constant is read from each font's own metrics — never nudged by hand.
K_BODY = 0.3662           # Gentium Book Plus: (2250 + -750) / 2 / 2048
K_DISPLAY = 0.2260        # EB Garamond:       ( 726 + -274) / 2 / 1000

BODY_SIZE = 18.29         # solved from word ink-widths
LEADING = 31.17           # measured between x-height bands

# (text, pen_x, baseline, word_spacing) — word_spacing solved from the font's
# advances, then corrected by the measured render deficit (Chromium lands ~0.6%
# short of the fontTools prediction; see the lesson).
BODY_LINES = [
    ("eing down gives you a reason to come up again. You hit", 101.33, 555, 2.232),
    ("rock bottom and feel worse than you think is possible,", 101.53, 586, 3.649),
    ("but then suddenly you find the inner strength to shoot up", 59.93, 617, 4.467),
    ("again with full force and in full colour. This is (sort of) what", 59.33, 648, 2.696),
    ("happened to me while sitting in a café in Shoreditch London", 59.53, 679, 2.643),
    ("in early 2008, just before my thirty-second birthday. I was", 59.39, 711, 5.134),
    ("pulling back to process my life and feeling incredibly lonely,", 59.53, 742, 3.306),
    ("when suddenly my heart “spoke.” And it spoke loud and", 59.84, 773, 6.590),
    ("clear. It told me to write a list of all the qualities my dream", 59.33, 804, 2.991),
]


def build():
    """Return the reconstruction as a core-model ``Document``."""
    b = DocumentBuilder(title="Chapter opening — lesson 03", profile="book")
    page = b.page("p9", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    lay = page.layer("main")
    lay.rect([0, 0, W, H], fill="#ffffff")

    _line(lay, "CHAPTER 2", 215.17, 116, 26.01, color=GREY, track=6.68)
    _ornament(lay)
    _line(lay, "Man From My List", 128.37, 398, 48.37,
          family=DISPLAY_FACE, k=K_DISPLAY, track=0.2)
    _line(lay, "B", 58.67, 586, 73.82)          # drop cap, on line 2's baseline
    for text, pen_x, baseline, ws in BODY_LINES:
        _line(lay, text, pen_x, baseline, BODY_SIZE, word_spacing=ws)
    _line(lay, "9", 298.11, 884, 19.23, color=GREY)

    # the source crop's own rules — an artifact of the screenshot, not the design
    lay.rect([0, 0, 3, H], fill="#222222")
    lay.rect([0, 0, W, 1], fill="#222222")
    return b.build()


def _line(lay, text, pen_x, baseline, size, *, family=BODY_FACE, color=INK,
          k=K_BODY, track=None, word_spacing=None):
    """Place one line by its measured baseline and pen position.

    The renderer emits ``<tspan x=pen_x>`` at the box centre, so pen_x is exact
    and the box centre is solved back from the baseline via the font's own
    central-baseline offset.
    """
    box_h = size * 1.6
    cy = baseline - k * size
    style = {"color": color, "font_family": family, "font_size": round(size, 2),
             "text_align": "left"}
    if track is not None:
        style["letter_spacing"] = round(track, 2)
    if word_spacing is not None:
        style["word_spacing"] = round(word_spacing, 3)
    lay.text([pen_x, cy - box_h / 2, W - pen_x - 1, box_h], text, style=style)


def _ornament(lay):
    """The origami heart: 4 flat facets, mirrored about the page's axis.

    Vertices come from a row-by-row trace of the source: the tone boundary is a
    straight crease from (279.5, 204) to the bottom point, and the top notch
    closes at (CX, 217.5).
    """
    def mirror(pts):
        return [(2 * CX - x, y) for x, y in pts]

    wing = [(276, 204), (263, 215), (263, 230), (CX, 281.5), (279.5, 204)]
    inner = [(279.5, 204), (288, 204), (CX, 217.5), (CX, 281.5)]
    for poly, fill in ((wing, WING), (mirror(wing), WING),
                       (inner, INNER), (mirror(inner), INNER)):
        lay.polygon(poly, fill=fill, stroke="none")


def main():
    doc = build()
    report = validate_static_rules(doc)
    if not report.ok:
        for issue in report.issues:
            print(f"  {issue}")
        raise SystemExit("validation failed")

    from framegraph.sdk import render_page_svgs, serialize

    out = os.path.join(ROOT, "_tmp", "lesson-03")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "page.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    for i, svg in enumerate(render_page_svgs(doc, base_dir=ROOT), 1):
        with open(os.path.join(out, f"page-{i:03d}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print(f"OK: validated + rendered -> {out}")


if __name__ == "__main__":
    main()
