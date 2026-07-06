"""Painter kit — render-safe atmosphere primitives for guided-draw compositions.

This module is now a thin re-export of :mod:`framegraph.coach.paint`, which is the
canonical home for the painting layer (promoted into the coach so the colour
stages — flat colours / shadows / highlights — share one implementation). Kept
here so existing examples/tests that import ``guided_paint`` keep working.

The kit builds depth — soft glow, haze, a unifying wash, a vignette — from
gradients + transparency ONLY, because the browser-free rasteriser (cairosvg)
renders gradients and alpha but drops SVG blur filters and ``mix-blend-mode``.
Everything here survives rasterisation.
"""
from __future__ import annotations

from framegraph.coach.paint import (  # noqa: F401
    darkest,
    fade,
    glow,
    haze,
    lightest,
    linear,
    radial,
    soft_shadow,
    stop,
    vignette,
    wash,
)

__all__ = [
    "fade", "stop", "linear", "radial", "glow", "vignette", "haze", "wash",
    "soft_shadow", "lightest", "darkest",
]
