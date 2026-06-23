#!/usr/bin/env python3
"""Minimal worked example of the SDK's Tier-1 authoring toolkit.

Shows the three helpers added for technical decks working together:

  * ``page(..., coordinate_mode="absolute")`` — no more reaching into the page dict;
  * ``layout.grid`` / ``layout.row`` — tile a container box into child boxes; and
  * ``Chart`` — axis spines, ticks, gridlines, a series and a legend over a ``Frame``.

Run from the repository root::

    uv run python examples/sdk_toolkit_demo.py   # build, validate, write examples/sdk-toolkit.fg.yaml
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import Chart, DocumentBuilder, Frame, grid, inset, row, serialize, theme  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1280, 720
CANVAS = {"size": [W, H], "units": "px"}
INK, TEAL, AMBER, PANEL, MUTED = "#0E2436", "#1FA39B", "#E0903B", "#F1F5FA", "#7C8AA0"

STYLES = {
    "kicker": {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 15,
               "font_weight": 700, "color": TEAL, "letter_spacing": 2.0,
               "text_transform": "uppercase"},
    "title": {"font_family": ["Charter", "Georgia", "serif"], "font_size": 33,
              "font_weight": 700, "color": "#21364C"},
    "stat": {"font_family": ["Charter", "Georgia", "serif"], "font_size": 40,
             "font_weight": 700, "color": "#21364C"},
    "lbl": {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 13, "color": MUTED},
}


def kpi_page(builder: DocumentBuilder) -> None:
    """A KPI dashboard whose six cards are placed by layout.grid."""
    page = builder.page("kpis", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    page.rect([0, 0, W, H], fill="#FFFFFF")
    page.text([76, 92, 1128, 26], "layout.grid", style={"class": "kicker"})
    page.text([76, 122, 1128, 60], "Six cards, one grid call", style={"class": "title"})

    cards = [("Δ", "7 700 t"), ("Speed", "16 kn"), ("Fn", "0.30"),
             ("P_D", "7.6 MW"), ("GM", "0.90 m"), ("D_T", "5 L")]
    for (label, value), box in zip(cards, grid([76, 212, 1128, 420], cols=3, count=6,
                                               gap=24, row_gap=28)):
        page.rect(box, fill=PANEL, radius=14)
        head = inset(box, [22, 24])
        page.text([head[0], head[1], head[2], 18], label, style={"class": "lbl"})
        page.text([head[0], head[1] + 26, head[2], 48], value, style={"class": "stat"})


def chart_page(builder: DocumentBuilder) -> None:
    """A plot page: layout.row splits the canvas, Chart draws the figure."""
    page = builder.page("chart", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    page.rect([0, 0, W, H], fill="#FFFFFF")
    page.text([76, 92, 1128, 26], "Chart + layout.row", style={"class": "kicker"})
    page.text([76, 122, 1128, 60], "A figure in three lines", style={"class": "title"})

    left, right = row([76, 210, 1128, 430], gap=40, weights=[1, 1.4])
    page.text([left[0], left[1], left[2], 120],
              "layout.row splits the body into a caption column and a plot panel; "
              "Chart lowers axes, gridlines, a smooth series and a legend over a Frame.",
              style={"class": "lbl", "font_size": 16})

    page.rect(right, fill=PANEL, radius=14)
    plot = inset(right, [70, 60, 70, 60])
    frame = Frame(domain=(0, 0, 20, 600), box=tuple(plot))
    chart = (
        Chart(frame)
        .axes(x_ticks=[0, 5, 10, 15, 20], y_ticks=[0, 200, 400, 600],
              x_format=lambda v: f"{v:g}", y_format=lambda v: f"{v:g}", grid=True)
        .line([(v, 1.2 * v ** 1.825) for v in range(0, 21)], stroke=AMBER, width=2.4,
              smooth=True, label="friction")
        .line([(v, min(0.012 * v ** 3.4, 600)) for v in range(0, 21)], stroke=TEAL,
              width=2.4, smooth=True, label="wave")
        .legend(at="tl")
    )
    page.extend(chart.objects())


def build() -> DocumentBuilder:
    builder = DocumentBuilder(title="SDK Toolkit Demo", profile="deck", lang="en")
    theme(builder, styles=STYLES)
    kpi_page(builder)
    chart_page(builder)
    return builder


def main() -> int:
    builder = build()
    doc = builder.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} pages — ok={report.ok} errors={len(errors)}")
    for i in errors[:10]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "examples", "sdk-toolkit.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
