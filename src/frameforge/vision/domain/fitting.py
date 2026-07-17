"""Landmark alignment fitting — pure ``math`` only, no PIL/OpenCV.

Fits the transform that best maps overlay landmarks onto base landmarks and reports
per-pair offsets + post-fit residuals. Extracted from
``frameforge.vision.infrastructure.overlay_align`` (which re-exports these names and
keeps the PIL compositing) so the fit maths is import-cheap and unit-testable.

Scope (honest): the model is a **similarity WITHOUT rotation** — uniform scale + 2D
translation only (``base = scale · overlay + t``). Rotation and shear are NOT
modelled, so a rotated overlay surfaces as large residuals rather than being
silently "corrected". One pair yields a pure translation. This is a deliberate
scope choice, not an approximation to fix — do not swap in a rotation-bearing fit
without changing the tool contract.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class Similarity:
    """A uniform-scale + translation transform: ``base = scale * overlay + t``."""

    scale: float
    tx: float
    ty: float

    def apply(self, x: float, y: float) -> tuple[float, float]:
        return (self.scale * x + self.tx, self.scale * y + self.ty)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scale": round(self.scale, 6),
            "translation_px": [round(self.tx, 3), round(self.ty, 3)],
            "model": "similarity (uniform scale + translation; no rotation/shear)",
            "forward": "base_px = scale * overlay_px + translation_px",
        }


def fit_similarity(pairs: Sequence[tuple[tuple[float, float], tuple[float, float]]]) -> Similarity:
    """Least-squares uniform scale + translation mapping overlay→base over ``pairs``.

    Each pair is ``((base_x, base_y), (overlay_x, overlay_y))``. One pair → pure
    translation (scale 1). Two or more → the closed-form best fit.
    """
    n = len(pairs)
    if n == 0:
        raise ValueError("need at least one landmark pair")
    bxs = [p[0][0] for p in pairs]
    bys = [p[0][1] for p in pairs]
    oxs = [p[1][0] for p in pairs]
    oys = [p[1][1] for p in pairs]
    if n == 1:
        return Similarity(1.0, bxs[0] - oxs[0], bys[0] - oys[0])
    bmx, bmy = sum(bxs) / n, sum(bys) / n
    omx, omy = sum(oxs) / n, sum(oys) / n
    num = sum((oxs[i] - omx) * (bxs[i] - bmx) + (oys[i] - omy) * (bys[i] - bmy) for i in range(n))
    den = sum((oxs[i] - omx) ** 2 + (oys[i] - omy) ** 2 for i in range(n))
    scale = num / den if den > 1e-9 else 1.0
    return Similarity(scale, bmx - scale * omx, bmy - scale * omy)


def landmark_offsets(pairs: Sequence[tuple[tuple[float, float], tuple[float, float]]],
                     transform: Similarity) -> list[dict[str, Any]]:
    """Per-pair raw offset (base − overlay) and post-fit residual."""
    out: list[dict[str, Any]] = []
    for i, ((bx, by), (ox, oy)) in enumerate(pairs, start=1):
        mx, my = transform.apply(ox, oy)
        out.append({
            "pair": i,
            "base_px": [round(bx, 2), round(by, 2)],
            "overlay_px": [round(ox, 2), round(oy, 2)],
            "offset_px": [round(bx - ox, 2), round(by - oy, 2)],
            "residual_px": [round(bx - mx, 2), round(by - my, 2)],
            "residual_dist": round(math.hypot(bx - mx, by - my), 3),
        })
    return out


def rms_residual(offsets: Sequence[dict[str, Any]]) -> float:
    if not offsets:
        return 0.0
    return round(math.sqrt(sum(o["residual_dist"] ** 2 for o in offsets) / len(offsets)), 3)
