#!/usr/bin/env python3
"""DEPRECATED shim — this R&D script was promoted into the FrameGraph package.

The mollify → level-set → Fourier-smooth-loop preprocessor now lives in
``framegraph.vision.infrastructure.regions``: the single-run pass is
``extract_smooth_regions`` (PARAMETER-SENSITIVE by construction — prefer the
ensemble ``consensus_smooth_regions`` / ``detect_regions(..., method='consensus')``),
and the helpers (``mollify``, ``smooth_loop``, ``green_area``, ``load_image``,
``smooth_regions_svg``) are re-exported below. The old ``Region`` dataclass is
replaced by the canonical ``DetectedRegion``.

This shim re-exports the promoted API and delegates its CLI (to the robust
consensus method); it will be removed.
"""
from __future__ import annotations

from framegraph.vision.infrastructure.regions import (  # noqa: F401
    DetectedRegion,
    RegionAnalysis,
    detect_regions,
    extract_smooth_regions,
    green_area,
    load_image,
    mollify,
    smooth_loop,
    smooth_regions_svg,
)
from framegraph.vision.infrastructure.regions import main as _regions_main

__all__ = ["DetectedRegion", "RegionAnalysis", "detect_regions",
           "extract_smooth_regions", "green_area", "load_image", "mollify",
           "smooth_loop", "smooth_regions_svg", "main"]


def main(argv: "list[str] | None" = None) -> int:
    return _regions_main(argv, default_method="consensus")


if __name__ == "__main__":
    raise SystemExit(main())
