#!/usr/bin/env python3
"""Generate the SDK layout stacks fixture."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from framegraph.sdk import DocumentBuilder, badge, button, kpi, soft_shadow  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "sdk-layout-stacks.fg.yaml"


def build() -> DocumentBuilder:
    builder = DocumentBuilder(title="SDK layout stacks", profile="deck", lang="en")
    ink = builder.define_color("ink", "#111827")
    title = builder.define_text_style("title", font_family="Inter", font_size=30, color=ink)

    page = builder.page(
        "stacks",
        canvas={"size": [900, 520], "units": "px"},
        reading_order=["title", "caption"],
        coordinate_mode="absolute",
    ).layer("main")
    page.rect([0, 0, 900, 520], fill="#f8fafc")
    page.text([48, 34, 520, 40], "Layout-native SDK stacks", id="title", style=title)
    page.text(
        [50, 82, 700, 24],
        "Rows, columns, wrapping chips and grow spacers are emitted as layout groups.",
        id="caption",
        style={"font_family": "Inter", "font_size": 14, "color": "#475569"},
    )

    with page.hstack([48, 128, 804, 72], gap=12, pad=16, align="center", id="actions") as actions:
        actions.add(button("Cancel", kind="ghost"))
        actions.spacer(h=36, grow=1)
        actions.add(button("Preview", kind="subtle"))
        actions.add(button("Deploy", grow=1))

    with page.wrap([48, 228, 360, 120], gap=10, pad=16, id="chips") as chips:
        for label, tone in [
            ("api", "accent"),
            ("renderer", "good"),
            ("schema", "warn"),
            ("layout-native", "accent"),
            ("docs", "muted"),
            ("fixtures", "good"),
        ]:
            chips.add(badge(label, tone=tone))

    with page.vstack([456, 228, 396, 220], gap=14, pad=16, id="metrics") as metrics:
        metrics.add(kpi("Build", "588 passed", delta="full gate",))
        metrics.add(kpi("DX", "less math", delta="layout groups"))

    page.rect([48, 388, 804, 72], fill="#ffffff", radius=12, shadow=soft_shadow(), decorative=True)
    page.text(
        [72, 410, 740, 26],
        "The child boxes stay local; layout controls placement and fill-space growth.",
        style={"font_family": "Inter", "font_size": 16, "color": "#334155"},
    )
    return builder


def main() -> None:
    build().write(OUT, fail_on_error=True)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
