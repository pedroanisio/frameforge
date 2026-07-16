"""Lesson 02 — reconstruct the cover of *The Understory* as a FrameGraph document.

Every number here was measured from `docs/tutorial/lesson-02/target/lesson-02.jpg`;
none was eyeballed. See `docs/tutorial/lesson-02/index.md` for the derivation and
for what this reconstruction honestly does *not* match.

Geometry
    The mosaic is the arrangement of eight lines recovered by Hough transform:
    six diagonals of slope +-1.5 (= (H/4)/(W/4) = 169.5/113) through the grid
    points (113i, 169.5j), plus the central vertical x=226 and horizontal y=339.
    Those eight lines cut the page into 16 congruent triangles of area 19153.5,
    which tile it exactly: 16 x 19153.5 = 306456 = 452 x 678.

Colour
    Each face is filled with the MEDIAN of its source pixels. `spread` records
    the median absolute deviation from that median -- it is the honesty column:
    <=8 means the face really is flat and reconstructs exactly; >=68 means a
    photographic collage sits there and a flat fill is a reduction, not a match.

Type
    No installed face is narrow enough (source ink/cap = 0.38; the narrowest
    installed, PT Sans Narrow, is 0.57). Two unknowns are therefore solved per
    line: `size` from the measured cap band, and an x-compression `K` from the
    measured letter ink, with `letter_spacing` solved to land the measured line
    width after compression. K costs horizontal stroke weight -- declared, not
    hidden.

Run:
    uv run python static/examples/lesson_02_book_cover.py   # -> _tmp/lesson-02/
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

from pathlib import Path  # noqa: E402

from framegraph.sdk import DocumentBuilder  # noqa: E402

W, H = 452, 678
MX, MY = W / 4, H / 4  # 113, 169.5 -- the lattice module

TITLE_FACE = "PT Sans Narrow"
CAP_EM = 0.700  # PT Sans Narrow OS/2.sCapHeight / unitsPerEm

GREY = "#7B6D64"  # the flat background wedges (spread 0 and 1 -- exact)
CREAM_INK = "#F9E2BE"  # median of the title glyph cores
DARK_INK = "#732805"  # median of the translator glyph cores

# (polygon, median fill, spread) -- spread is the median |px - median| over RGB.
FACES: list[tuple[list[tuple[float, float]], str, int]] = [
    ([(0, 0), (226, 0), (113, 169.5)], "#055336", 28),
    ([(0, 0), (113, 169.5), (0, 339)], GREY, 0),
    ([(226, 0), (226, 339), (113, 169.5)], "#F6BB6F", 122),
    ([(113, 169.5), (226, 339), (0, 339)], "#EE5E1D", 6),
    ([(226, 0), (452, 0), (339, 169.5)], "#3C3732", 106),
    ([(226, 0), (339, 169.5), (226, 339)], "#0A4D33", 44),
    ([(452, 0), (452, 339), (339, 169.5)], GREY, 1),
    ([(339, 169.5), (452, 339), (226, 339)], "#F8C67A", 95),
    ([(226, 339), (113, 508.5), (0, 339)], "#0B4B31", 35),
    ([(0, 678), (0, 339), (113, 508.5)], "#095034", 36),
    ([(226, 339), (226, 678), (113, 508.5)], "#E77A21", 68),
    ([(226, 678), (0, 678), (113, 508.5)], "#1A160F", 8),
    ([(452, 339), (339, 508.5), (226, 339)], "#E46B1E", 76),
    ([(226, 339), (339, 508.5), (226, 678)], "#0C5436", 37),
    ([(452, 339), (452, 678), (339, 508.5)], "#EF5E1D", 3),
    ([(339, 508.5), (452, 678), (226, 678)], "#171715", 0),
]

# (text, font size, x-compression K, letter_spacing, cap-centre x, cap-centre y, ink colour)
#
# `size` starts at cap_px / CAP_EM, then takes ONE Newton step against the first
# render's measured cap band (same mask on source and render): the round letters
# of UNDERSTORY overshoot the cap line, so the table value alone rendered 61 px
# where the source measures 56. Closed-loop, not a fudge factor.
# `letter_spacing` solves the INK extent, not the advance sum: the first glyph's
# left side-bearing and the last glyph's right side-bearing sit inside the
# advances but outside the measured ink, so
#     ink = (Σadvance − lsb(first) − rsb(last) + (n−1)·ls) · K
# Omitting the two bearings made every line render short (−8 px on the title).
# `cy` carries the cap-centre error measured off the previous render.
LINES = [
    ("TRANSLATED BY", 14.29, 0.8602, 1.17, 114.0, 291.5, DARK_INK),
    ("MUI POOPOKSAKUL", 21.43, 0.7372, 1.17, 108.0, 315.0, DARK_INK),
    ("THE", 32.92, 0.6378, 6.02, 224.5, 446.0, CREAM_INK),
    ("UNDERSTORY", 74.76, 0.7396, 11.20, 226.0, 506.5, CREAM_INK),
    ("SANEH SANGSUK", 38.57, 0.7149, 5.30, 223.0, 592.0, CREAM_INK),
]


def build():
    doc = DocumentBuilder(title="The Understory — cover reconstruction", profile="diagram")
    page = doc.page("cover", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")

    page.rect([0, 0, W, H], fill=GREY, id="ground")
    for i, (poly, fill, _spread) in enumerate(FACES):
        page.polygon(poly, fill=fill, id=f"face{i:02d}")

    for text, size, k, ls, cx, cy, ink in LINES:
        # CSS letter-spacing is emitted after the last glyph too, so a centred
        # run drifts left by half a step; take it back on the box centre.
        anchor = cx + ls * k / 2.0
        # Widest box that stays centred on `anchor` AND inside the canvas, so the
        # containment rule stays quiet without moving the type.
        box_w = min(2 * anchor, 2 * (W - anchor), float(W))
        box_h = size * 1.6
        page.text(
            [anchor - box_w / 2, cy - box_h / 2, box_w, box_h],
            text,
            id="t_" + text.split()[0].lower(),
            style={
                "font_family": TITLE_FACE,
                "font_size": size,
                "color": ink,
                "text_align": "center",
                "letter_spacing": ls,
                # Compress about the line's own centre: the face is ~32% too wide.
                "transform": f"translate({anchor} 0) scale({k} 1) translate({-anchor} 0)",
            },
        )
    return doc


if __name__ == "__main__":
    from framegraph.sdk.validate import validate_static_rules

    out = Path(ROOT) / "_tmp" / "lesson-02"
    out.mkdir(parents=True, exist_ok=True)
    doc = build()
    report = validate_static_rules(doc.build())
    if not report.ok:
        for issue in report.issues:
            print(f"  {issue.severity}: {issue.rule_id}: {issue.message}", file=sys.stderr)
        raise SystemExit("validation failed")
    doc.write(out / "lesson-02.fg.yaml", fail_on_error=True)
    print(f"OK: validated -> {out}")
