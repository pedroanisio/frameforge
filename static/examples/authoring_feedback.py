#!/usr/bin/env python3
"""Authoring feedback — safe text widths, whitespace, dashes, bleed, validation.

This small 2.6 example demonstrates the contracts used by positioned-text
authors and MCP clients after the 2026-07 feedback pass:

* ``fit_width`` uses the same metric mode as proxy layout and includes its fit
  tolerance;
* preserving ``white_space`` modes keep authored spacing;
* SVG-style dash strings normalize through ``stroke``;
* ``bleed()`` declares both decorative and containment intent;
* validation runs text fit by default; and
* overflow records distinguish post-layout ``needed`` from
  ``unwrapped_width``.

Run from the repository root::

    uv run python static/examples/authoring_feedback.py
"""
from __future__ import annotations

from frameforge_sdk import (
    DocumentBuilder,
    fit_width,
    measure_text,
    stroke,
    validate_static_rules,
)
from frameforge.conform import overflow_report


def build() -> dict:
    family = ["Inter", "DejaVu Sans", "sans-serif"]
    label = "Advanced   SQL"
    label_width = fit_width(label, font_family=family, font_size=13)

    builder = DocumentBuilder(title="Authoring feedback", profile="diagram")
    layer = builder.page(
        "feedback", canvas={"size": [520, 240], "units": "px"}
    ).layer("main")

    with layer.bleed():
        layer.rect([-8, 0, 536, 12], fill="#2563eb")

    layer.text(
        [32, 36, label_width, 24],
        label,
        id="positioned",
        style={
            "font_family": family,
            "font_size": 13,
            "white_space": "pre",
        },
    )
    layer.line(
        [32, 68],
        [32 + label_width, 68],
        **stroke(1, color="#2563eb", dash="4 4"),
    )
    layer.text(
        [32, 92, 180, 58],
        "Spacing   survives and this run wraps without collapsing.",
        style={"font_size": 12, "white_space": "pre-wrap"},
    )
    layer.text(
        [300, 92, 80, 20],
        "one unwrapped positioned token",
        id="spill",
        style={"font_size": 12, "overflow": "visible"},
    )
    return builder.build_dict()


def main() -> int:
    document = build()
    report = validate_static_rules(document)
    print("validation:", [(issue.rule_id, issue.severity) for issue in report.issues])
    print(
        "positioned advance/safe width:",
        measure_text(
            "Advanced   SQL",
            font_family=["Inter", "DejaVu Sans", "sans-serif"],
            font_size=13,
        ),
        fit_width(
            "Advanced   SQL",
            font_family=["Inter", "DejaVu Sans", "sans-serif"],
            font_size=13,
        ),
    )
    for signal in overflow_report(document):
        print(
            f"#{signal.id}: needed={signal.needed}, "
            f"unwrapped_width={signal.unwrapped_width}"
        )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
