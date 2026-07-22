"""Inverse primitive fitting — region mask → stroke_outline parameters (G1).

The round trip that closed the authored-lane fidelity gap, self-contained:
author a flame petal with ``sdk.outline.stroke_outline`` (a KNOWN spine +
width profile), rasterise its mask, then recover the parameters with
``frameforge.vision.domain.spine_fit.fit_spine`` — skeleton thinning, the
longest skeleton path extended to the tips, exact perpendicular-chord widths,
and an anchored least-squares cubic. Re-authoring from the FIT must reproduce
the shape (IoU printed; the test suite pins ≥ 0.90).

The same capability is one argument over MCP —
``detect_regions(image, fit_spines=True)`` attaches a ``spine`` payload to
every big-enough region: measured shapes become authorable spec-table rows
instead of traced outlines (lotus e2e: hand-guessed spines NCC 0.49 →
fitted spines + refined paints NCC 0.90).

Run: ``uv run python static/examples/spine_fit_demo.py``
(needs the ``vision`` group; writes to ``_tmp/spine-fit-demo/``).
"""
from __future__ import annotations

import math
import os
import pathlib
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import numpy as np

from frameforge.sdk import DocumentBuilder
from frameforge.sdk.io import serialize
from frameforge.sdk.outline import stroke_outline
from frameforge.sdk.paint import linear_gradient
from frameforge.vision.domain.spine_fit import fit_spine, spine_profile
from frameforge.vision.infrastructure.vectorize import _shape_mask

SIZE = (600, 800)


def true_spine(n=64):
    b, c1, c2, e = (150, 700), (180, 420), (390, 180), (520, 120)
    pts = []
    for i in range(n + 1):
        s = i / n
        u = 1.0 - s
        pts.append((
            u**3 * b[0] + 3 * u * u * s * c1[0] + 3 * u * s * s * c2[0] + s**3 * e[0],
            u**3 * b[1] + 3 * u * u * s * c1[1] + 3 * u * s * s * c2[1] + s**3 * e[1],
        ))
    return pts


def flame(t, peak=0.4):
    if t <= peak:
        return math.sin(min(max(t / peak, 0.0), 1.0) * math.pi / 2.0) ** 0.7
    x = min(max((t - peak) / (1.0 - peak), 0.0), 1.0)
    return math.cos(x * math.pi / 2.0) ** 0.9


def main() -> None:
    # 1. the ORACLE: a petal authored from known parameters
    original = stroke_outline(true_spine(), 110, profile=flame, cap="round",
                              join="round", fill="#f00")
    mask = np.asarray(_shape_mask(original, SIZE)[0]) > 0

    # 2. the INVERSE: recover spine + widths from the mask alone
    fit = fit_spine(mask)
    print(f"spine: {len(fit['spine'])} pts  length {fit['length']}  "
          f"width_max {fit['width_max']}  peak {fit['peak']}  "
          f"cubic_rms {fit['cubic_rms']}  elongation {fit['elongation']}")

    # 3. the ROUND TRIP: re-author from the fit and measure agreement
    rebuilt = stroke_outline(fit["spine"], fit["width_max"],
                             profile=spine_profile(fit["profile"]),
                             cap="round", join="round",
                             fill=linear_gradient(
                                 [("#9fe1f7", "0%"), ("#0a86fa", "45%"),
                                  ("#1213a8", "100%")],
                                 line=[list(fit["spine"][-1]), list(fit["spine"][0])]))
    remask = np.asarray(_shape_mask(rebuilt, SIZE)[0]) > 0
    iou = float((mask & remask).sum()) / float((mask | remask).sum())
    print(f"round-trip IoU: {iou:.4f}  (the suite pins >= 0.90)")

    doc = DocumentBuilder(title="Spine-fit round trip", lang="en")
    page = doc.page("demo", canvas={"size": [1200, 800], "units": "px"},
                    coordinate_mode="absolute")
    page.layer("bg").rect([0, 0, 1200, 800], fill="#101014")
    left = page.layer("original")
    left.add(dict(original, fill="#3a4a63"))
    right = page.layer("rebuilt")
    shifted = dict(rebuilt)
    shifted["style"] = {"transform": "translate(600,0)"}
    right.add(shifted)

    out = pathlib.Path(ROOT) / "_tmp" / "spine-fit-demo"
    out.mkdir(parents=True, exist_ok=True)
    (out / "spine-fit-demo.fg.yaml").write_text(
        serialize(doc.build(), format="yaml"), encoding="utf-8")
    print(f"wrote {out / 'spine-fit-demo.fg.yaml'}")


if __name__ == "__main__":
    main()
