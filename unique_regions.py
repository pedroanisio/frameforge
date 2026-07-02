#!/usr/bin/env python3
"""DEPRECATED shim — this R&D script was promoted into the FrameGraph package.

Shape-equivalence clustering (translation-congruent tile counting and
rotation/reflection-congruent distinct-shape counting) now lives in
``framegraph.vision.infrastructure.regions`` as ``cluster_regions`` — or in one
call via the funnel:

    from framegraph.vision.infrastructure.regions import detect_regions
    detect_regions("input.png", method="closed", cluster="translation",
                   cluster_tol=0.90)

CLI: ``python unique_regions.py input.png --cluster translation`` (the cluster
flag is now explicit). This shim re-exports the promoted API for compatibility;
removal is an operator decision (CLAUDE.md §8) — prefer the package import above.
"""
from __future__ import annotations

from framegraph.vision.infrastructure.regions import (  # noqa: F401
    DetectedRegion,
    RegionAnalysis,
    cluster_regions,
    detect_closed_regions,
    detect_regions,
    distinct_colors,
)
from framegraph.vision.infrastructure.regions import main as _regions_main

__all__ = ["DetectedRegion", "RegionAnalysis", "cluster_regions",
           "detect_closed_regions", "detect_regions", "distinct_colors", "main"]


def main(argv: "list[str] | None" = None) -> int:
    return _regions_main(argv, default_method="closed")


if __name__ == "__main__":
    raise SystemExit(main())
