#!/usr/bin/env python3
"""Deterministic sampling: Halton, Poisson disk, and a jittered grid.

The three panels use the public ``frameforge_sdk.rand`` surface to generate
ordinary circle geometry in Y-down page space.  Named ``Rand.derive`` streams
keep each panel stable when another panel is edited or reordered.  ``build()``
is the MCP ``run_sdk_code`` contract and returns a validated-ready plain
FrameForge document; running the file writes YAML and SVG under
``_tmp/seeded-sampling/``.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge_sdk import Rand, halton, jittered_grid, poisson_disk, serialize
from frameforge.conform import render_page_svgs
from frameforge_sdk.model import HEAD_VERSION

_SANS = ["DejaVu Sans", "Arial", "sans-serif"]


def _circle(point, radius: float, fill: str, *, id: str) -> dict:
    return {
        "type": "ellipse",
        "id": id,
        "center": [point.x, point.y],
        "rx": radius,
        "ry": radius,
        "fill": fill,
        "decorative": True,
    }


def _label(x: float, title: str, detail: str) -> list[dict]:
    return [
        {
            "type": "text",
            "box": [x, 54, 250, 24],
            "text": title,
            "style": {
                "font_family": _SANS,
                "font_size": 16,
                "font_weight": 700,
                "color": "ink",
                "white_space": "nowrap",
            },
        },
        {
            "type": "text",
            "box": [x, 78, 250, 18],
            "text": detail,
            "style": {
                "font_family": _SANS,
                "font_size": 10,
                "color": "muted",
                "white_space": "nowrap",
            },
        },
    ]


def build() -> dict:
    """Build the deterministic three-sampler showcase for MCP or local use."""
    root = Rand("seeded-sampling-showcase")
    halton_points = halton(64, box=[40, 112, 250, 350], skip=7)
    poisson_points = poisson_disk(
        [355, 112, 250, 350], radius=16, rand=root.derive("poisson")
    )
    grid_points = jittered_grid(
        [670, 112, 250, 350], nx=6, ny=5, amount=0.72, rand=root.derive("grid")
    )

    objects: list[dict] = [
        {
            "type": "rect",
            "box": [0, 0, 960, 540],
            "fill": "paper",
            "decorative": True,
        },
        {
            "type": "text",
            "box": [40, 20, 880, 25],
            "text": "Seeded sampling — repeatable geometry, independent streams",
            "style": {
                "font_family": _SANS,
                "font_size": 18,
                "font_weight": 700,
                "color": "ink",
                "white_space": "nowrap",
            },
        },
    ]
    for x, title, detail in (
        (40, "Halton", "64 low-discrepancy terms · skip 7"),
        (355, "Poisson disk", f"{len(poisson_points)} points · min 16 px"),
        (670, "Jittered grid", "6 × 5 strata · amount 0.72"),
    ):
        objects.extend(_label(x, title, detail))
        objects.append(
            {
                "type": "rect",
                "box": [x, 112, 250, 350],
                "fill": "panel",
                "stroke": "edge",
                "stroke_style": {"stroke_width": 1},
                "decorative": True,
            }
        )

    objects.extend(
        _circle(point, 2.5, "halton", id=f"halton-{index:03d}")
        for index, point in enumerate(halton_points)
    )
    objects.extend(
        _circle(point, 3.2, "poisson", id=f"poisson-{index:03d}")
        for index, point in enumerate(poisson_points)
    )
    objects.extend(
        _circle(point, 4.0, "grid", id=f"grid-{index:03d}")
        for index, point in enumerate(grid_points)
    )

    return {
        "dsl": "FrameForge",
        "version": HEAD_VERSION,
        "title": "Seeded sampling showcase",
        "profile": "diagram",
        "defs": {
            "tokens": {
                "colors": {
                    "paper": "#f7f4ec",
                    "panel": "#fffdf8",
                    "edge": "#d9d2c3",
                    "ink": "#20242a",
                    "muted": "#667085",
                    "halton": "#2563eb",
                    "poisson": "#d4572b",
                    "grid": "#16856b",
                }
            }
        },
        "pages": [
            {
                "mode": "page",
                "id": "seeded-sampling",
                "canvas": {"size": [960, 540], "units": "px"},
                "rendering": {"coordinate_mode": "absolute"},
                "layers": [{"id": "sampling", "objects": objects}],
            }
        ],
    }


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "seeded-sampling")
    os.makedirs(out, exist_ok=True)
    document = build()
    with open(os.path.join(out, "seeded-sampling.fg.yaml"), "w", encoding="utf-8") as handle:
        handle.write(serialize(document))
    with open(os.path.join(out, "seeded-sampling.svg"), "w", encoding="utf-8") as handle:
        handle.write(render_page_svgs(document, base_dir=out)[0])
    print(f"Wrote the seeded-sampling showcase to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
