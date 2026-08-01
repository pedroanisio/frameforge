#!/usr/bin/env python3
"""Sampleable coherent noise rendered through an existing ScalarField.

The page evaluates deterministic simplex noise in Python, lowers the samples to
ordinary heatmap rectangles and marching-squares contours, and renders through
the unchanged SVG lane.  ``build()`` is suitable for MCP ``run_sdk_code``;
running this file writes YAML and SVG under ``_tmp/sampleable-noise/``.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge_sdk import DocumentBuilder, Noise, ScalarField, serialize
from frameforge.conform import render_page_svgs

_SANS = ["DejaVu Sans", "Arial", "sans-serif"]


def build():
    """Build a deterministic noise heatmap with overlaid iso-contours."""
    builder = DocumentBuilder(
        title="Sampleable coherent noise",
        profile="diagram",
        lang="en",
    )
    builder.define_text_style(
        "title",
        font_family=_SANS,
        font_size=24,
        font_weight=800,
        color="#f8fafc",
        white_space="nowrap",
    )
    builder.define_text_style(
        "body",
        font_family=_SANS,
        font_size=12,
        color="#cbd5e1",
        white_space="nowrap",
    )
    page = builder.page(
        "sampleable-noise",
        canvas={"size": [960, 540], "units": "px"},
        coordinate_mode="absolute",
        reading_order=["title", "subtitle"],
    ).layer("main")
    page.rect([0, 0, 960, 540], fill="#07111f", decorative=True)
    page.text([40, 24, 880, 34], "Sampleable coherent noise", id="title", style="title")
    page.text(
        [40, 62, 880, 22],
        "Noise(seed=91, basis='simplex') → ScalarField heatmap + contours",
        id="subtitle",
        style="body",
    )

    source = Noise(91, frequency=0.72, basis="simplex")
    scalar = ScalarField(source.field(), domain=(0.0, 0.0, 12.0, 7.0))
    heatmap = scalar.heatmap(
        box=[40, 104, 880, 380],
        steps_x=48,
        steps_y=28,
        low="#0b2a4a",
        high="#f5b942",
        id="noise-heatmap",
    )
    contours = scalar.contours(
        box=[40, 104, 880, 380],
        levels=9,
        steps_x=56,
        steps_y=34,
        color="#f8fafc",
        width=0.75,
        id="noise-contours",
    )
    heatmap["children"].extend(contours["children"])
    page.add(heatmap)
    page.text(
        [40, 500, 880, 18],
        "Author-time CPU values · deterministic · no renderer-side filter",
        style="body",
    )
    return builder.build()


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "sampleable-noise")
    os.makedirs(out, exist_ok=True)
    document = build()
    with open(os.path.join(out, "sampleable-noise.fg.yaml"), "w", encoding="utf-8") as handle:
        handle.write(serialize(document))
    with open(os.path.join(out, "sampleable-noise.svg"), "w", encoding="utf-8") as handle:
        handle.write(render_page_svgs(document, base_dir=out)[0])
    print(f"Wrote the sampleable-noise showcase to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
