#!/usr/bin/env python3
"""Generate the SDK ergonomics showcase fixture."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    dots,
    fill_stroke,
    greeble,
    grid_lines,
    hatch_fill,
    neon,
    soft_shadow,
    sparkline,
)

OUT = ROOT / "tests" / "fixtures" / "sdk-ergonomics-showcase.fg.yaml"


def build() -> DocumentBuilder:
    builder = DocumentBuilder(title="SDK ergonomics showcase", profile="deck")
    ink = builder.define_color("ink", "#111827")
    title_style = builder.define_text_style(
        "title",
        font_family="Inter",
        font_size=34,
        font_weight=700,
        color=ink,
    )
    label_style = builder.define_text_style(
        "label",
        font_family="Inter",
        font_size=15,
        color="#334155",
    )

    with builder.symbol("metric_badge", [0, 0, 140, 48]) as sym:
        sym.rect(
            [0, 0, 140, 48],
            radius=10,
            decorative=True,
            **fill_stroke("$fill", "#0f172a", 1.2),
        )
        sym.text([14, 8, 112, 14], "$label", style=label_style)
        sym.text([14, 24, 112, 18], "$value", style=label_style)

    page = builder.page(
        "sdk-ergonomics",
        canvas={"size": [960, 540], "units": "px"},
        reading_order=["title", "caption"],
        coordinate_mode="absolute",
    ).layer("main")

    page.rect([0, 0, 960, 540], fill="#f8fafc")
    page.text([48, 38, 560, 44], "SDK ergonomics showcase", id="title", style=title_style)
    page.text(
        [50, 92, 700, 26],
        "Symbols, local panels, pattern paint and procedural texture lower to core objects.",
        id="caption",
        style=label_style,
    )

    page.use_at(
        "metric_badge",
        48,
        142,
        190,
        64,
        params={"fill": "#dbeafe", "label": "symbol", "value": "author once"},
    )
    page.use_at(
        "metric_badge",
        258,
        142,
        190,
        64,
        params={"fill": "#dcfce7", "label": "use_at", "value": "place many"},
    )

    with page.local([48, 238, 400, 230], id="texture-panel") as panel:
        panel.rect([0, 0, 400, 230], radius=12, fill="#ffffff",
                   shadow=soft_shadow(), decorative=True)
        panel.extend(hatch_fill([22, 22, 150, 72], fg="#64748b", bg="#f1f5f9", scale=9))
        panel.rect([196, 22, 150, 72], fill=dots(fg="#475569", bg="#e0f2fe", scale=10))
        panel.extend(grid_lines([22, 120, 150, 72], cols=5, rows=4, color="#94a3b8"))
        panel.add(sparkline([(0, 2), (1, 4), (2, 3), (3, 7), (4, 5)], [196, 120, 150, 72]))

    with page.local([500, 142, 360, 326], id="procedural-panel") as panel:
        panel.rect([0, 0, 360, 326], radius=12, fill="#0f172a",
                   shadow=soft_shadow(), decorative=True)
        with panel.bleed():
            panel.extend(greeble([24, 24, 312, 210], seed=22, density=0.9, fill="#334155"))
        panel.star([180, 130], 70, 30, 7, fill="#facc15", **neon("#22d3ee", blur=14))
        panel.text([36, 264, 288, 28], "deterministic macro texture", style=label_style)

    return builder


def main() -> None:
    build().write(OUT, fail_on_error=True)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
