#!/usr/bin/env python3
"""DEPRECATED shim — this R&D script was promoted into the FrameGraph package.

The ensemble (consensus) region segmentation — segment across a (sigma, level)
grid, keep what the majority agrees on, smooth the boundaries — now lives in
``framegraph.vision.infrastructure.regions`` (``consensus_smooth_regions`` /
``detect_regions(..., method='consensus')``), including the per-run helpers
(``ensemble_vote``) and the SVG emitter (``smooth_regions_svg``).

    from framegraph.vision.infrastructure.regions import detect_regions
    detect_regions("img.png", method="consensus", sigmas=(4, 6, 8, 10),
                   levels=(0.25, 0.30, 0.35, 0.40), agree=0.5)

This shim re-exports the promoted API and delegates its CLI; it will be removed.
"""
from __future__ import annotations

from framegraph.vision.infrastructure.regions import (  # noqa: F401
    DetectedRegion,
    RegionAnalysis,
    consensus_smooth_regions,
    detect_regions,
    ensemble_vote,
    smooth_regions_svg,
)
from framegraph.vision.infrastructure.regions import main as _regions_main

__all__ = ["DetectedRegion", "RegionAnalysis", "consensus_smooth_regions",
           "detect_regions", "ensemble_vote", "smooth_regions_svg", "main"]


def main(argv: "list[str] | None" = None) -> int:
    return _regions_main(argv, default_method="consensus")


if __name__ == "__main__":
    raise SystemExit(main())
