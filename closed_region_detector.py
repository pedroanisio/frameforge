#!/usr/bin/env python3
"""DEPRECATED shim — this R&D script was promoted into the FrameGraph package.

The topological enclosed-face detector now lives in
``framegraph.vision.infrastructure.regions`` (``detect_closed_regions`` /
``detect_regions(..., method='closed')``), emitting the canonical
``DetectedRegion`` records instead of this script's private ``Region``.

    from framegraph.vision.infrastructure.regions import detect_regions
    detect_regions("input.png", method="closed", min_area=200)

This shim re-exports the promoted API and delegates its CLI; it will be removed.
"""
from __future__ import annotations

from framegraph.vision.infrastructure.regions import (  # noqa: F401
    DetectedRegion,
    RegionAnalysis,
    detect_closed_regions,
    detect_regions,
    distinct_colors,
    render_overlay,
)
from framegraph.vision.infrastructure.regions import main as _regions_main

__all__ = ["DetectedRegion", "RegionAnalysis", "detect_closed_regions",
           "detect_regions", "distinct_colors", "render_overlay", "main"]


def main(argv: "list[str] | None" = None) -> int:
    return _regions_main(argv, default_method="closed")


if __name__ == "__main__":
    raise SystemExit(main())
