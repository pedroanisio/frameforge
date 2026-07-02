#!/usr/bin/env python3
"""DEPRECATED shim — this R&D script was promoted into the FrameGraph package.

The unified fill-partition segmentation (every maximal uniform-fill area is one
region, solid and hollow alike, with sampled ``fill_hex`` and solid/hollow/outline
classification) now lives in ``framegraph.vision.infrastructure.regions``
(``segment_fill_regions`` / ``detect_regions(..., method='flat')``). The old
``FilledRegion`` dataclass is replaced by the canonical ``DetectedRegion``.

    from framegraph.vision.infrastructure.regions import detect_regions
    detect_regions("img.png", method="flat", colors=8, min_area=100)

This shim re-exports the promoted API and delegates its CLI for compatibility;
removal is an operator decision (CLAUDE.md §8) — prefer the package import above.
"""
from __future__ import annotations

from framegraph.vision.infrastructure.regions import (  # noqa: F401
    DetectedRegion,
    RegionAnalysis,
    detect_regions,
    render_overlay,
    segment_fill_regions,
    solid_ink_regions,
)
from framegraph.vision.infrastructure.regions import main as _regions_main

__all__ = ["DetectedRegion", "RegionAnalysis", "detect_regions",
           "segment_fill_regions", "solid_ink_regions", "render_overlay", "main"]


def main(argv: "list[str] | None" = None) -> int:
    return _regions_main(argv, default_method="flat")


if __name__ == "__main__":
    raise SystemExit(main())
