#!/usr/bin/env python3
"""Deterministic perceptual colour mixing through the public FrameForge SDK.

This numerical example contrasts the legacy sRGB midpoint with the new OKLab
default and emits a multi-stop perceptual ramp as stable JSON. It is suitable
for direct execution or MCP ``run_sdk_code``; no renderer is required.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import delta_e, mix, ramp  # noqa: E402


def build_payload() -> dict[str, object]:
    """Return a stable comparison and a seven-colour perceptual ramp."""
    start, pivot, end = "#172a46", "#b5402c", "#f3c969"
    colors = ramp([start, pivot, end], 7, space="oklab")
    return {
        "delta_e_oklab": round(delta_e(start, end), 6),
        "legacy_midpoint": mix(start, end, 0.5, space="srgb"),
        "oklab_ramp": colors,
        "perceptual_midpoint": mix(start, end, 0.5),
    }


def main() -> int:
    print(json.dumps(build_payload(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
