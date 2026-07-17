#!/usr/bin/env python3
"""Worked example for SDK pattern paint and geometry helpers.

Run from the repository root::

    uv run python examples/sdk_geometry_patterns.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, pattern, stroke  # noqa: E402


def build() -> DocumentBuilder:
    builder = DocumentBuilder(title="SDK geometry + pattern helpers", profile="diagram", lang="en")
    builder.define_text_style(
        "label",
        font_family=["DejaVu Sans", "Arial", "sans-serif"],
        font_size=16,
        font_weight=700,
        color="#263238",
    )
    page = builder.page(
        "geometry_patterns",
        canvas={"size": [760, 420], "units": "px"},
        coordinate_mode="absolute",
        reading_order=["title"],
    ).layer("main")
    page.rect([0, 0, 760, 420], fill="#f8fafc")
    page.text([40, 28, 500, 28], "Pattern paint and geometry helpers", id="title", style="label")

    hatch = pattern("hatch", fg="#64748b", bg="#e2e8f0", scale=8, angle=45)
    dots = pattern("dots", fg="#0f766e", bg="#ccfbf1", scale=12)

    page.rect([46, 86, 130, 90], fill=hatch, stroke="#334155", stroke_style={"stroke_width": 2})
    page.regular_polygon([270, 132], 56, 6, rotation=-90, fill=dots,
                         stroke="#0f766e", stroke_style={"stroke_width": 2})
    page.star([430, 132], 62, 27, 5, fill="#fde68a",
              stroke="#92400e", stroke_style={"stroke_width": 2})

    page.arc([590, 132], 62, 205, 515, **stroke(5, color="#2563eb", cap="round"))
    page.sector([128, 300], 72, -120, 25, fill="#fed7aa", stroke="#c2410c",
                stroke_style={"stroke_width": 2})
    page.ring([318, 300], 74, 42, fill="#bfdbfe", stroke="#1d4ed8",
              stroke_style={"stroke_width": 2})
    page.polyline([(470, 320), (530, 250), (610, 318), (680, 255)], smooth=True,
                  fill="none", stroke="#7c3aed", stroke_style={"stroke_width": 4})
    return builder


def main() -> int:
    out = os.path.join(ROOT, "tests", "fixtures", "sdk-geometry-patterns.fg.yaml")
    report = build().write(out, format="yaml")
    errors = [issue for issue in report.issues if issue.severity == "error"]
    warnings = [issue for issue in report.issues if issue.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warnings)} -> {out}")
    for issue in report.issues[:20]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
