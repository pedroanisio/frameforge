#!/usr/bin/env python3
"""A presentation that answers a critique: "all these layouts are just variations
of the same set."

That is true *only* if you author at one altitude — hand-placed absolute
[x, y, w, h] boxes. Then "bento", "editorial" and "collage" are the same
primitive (positioned rect + positioned text) with different numbers.

This deck is built so each section is produced by a DIFFERENT layout MECHANISM,
not a re-skin of the same boxes:

  0. absolute          — the baseline (coordinates I type by hand)
  1. renderer-arranged grid    — I pass a LIST; the engine tiles it (no x/y)
  2. renderer-arranged nesting — a row of columns; layouts compose
  3. chart             — geometry derived from a data domain, not placed
  4. table             — a tabular model, not free boxes
  5. flow              — text reflows through a multi-column master and
                         auto-paginates (a different document model entirely)

Sections 0-4 are `mode: page`; section 5 is `mode: flow`. A single Document
holds both (profile: mixed) — which is the whole point.

Run from the repository root::

    uv run python examples/layout_mechanisms_deck.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import Chart, DocumentBuilder, Frame, lorem, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1280, 720  # 16:9 slide
CANVAS = {"size": [W, H], "units": "px"}

COLORS = {
    "ink": "#0b1020", "ink2": "#141a36", "faint": "#1b2347", "line": "#2a325c",
    "sub": "#9aa3c7", "white": "#ffffff", "inkd": "#11162e", "paper": "#ffffff",
    "a1": "#ff5e7e", "a2": "#7c5cff", "a3": "#22d3ee", "a4": "#fde047",
}
SANS = ["Inter", "Arial", "sans-serif"]
SERIF = ["Charter", "Georgia", "serif"]

STYLES = {
    "kicker":  dict(font_family=SANS, font_size=15, font_weight=700, color="a3",
                    letter_spacing=3, text_transform="uppercase"),
    "title":   dict(font_family=SANS, font_size=44, font_weight=800, color="white",
                    letter_spacing=-1, line_height=1.02),
    "big":     dict(font_family=SANS, font_size=92, font_weight=800, color="white",
                    letter_spacing=-3, line_height=0.95),
    "sub":     dict(font_family=SANS, font_size=19, color="sub", line_height=1.45),
    "note":    dict(font_family=SANS, font_size=15, color="sub", line_height=1.5),
    "foot":    dict(font_family=SANS, font_size=13, color="sub", letter_spacing=1),
    "ghost":   dict(font_family=SANS, font_size=300, font_weight=800, color="faint",
                    line_height=0.9),
    "swatch":  dict(font_family=SANS, font_size=13, font_weight=600, color="white",
                    align="center"),
    # flow (light A4 report) styles
    "fTitle":  dict(font_family=SERIF, font_size=24, font_weight=800, color="inkd"),
    "fLead":   dict(font_family=SANS, font_size=12, color="sub", line_height=1.5),
    "fBody":   dict(font_family=SANS, font_size=10.5, color="inkd", line_height=1.55),
    "fH":      dict(font_family=SANS, font_size=12, font_weight=700, color="a2",
                    letter_spacing=1, text_transform="uppercase"),
    "running": dict(font_family=SANS, font_size=9, color="sub"),
    # table styles
    "thw":     dict(font_family=SANS, font_size=14, font_weight=700, color="white"),
    "tdd":     dict(font_family=SANS, font_size=14, color="inkd"),
    "chartlab": dict(font_family=SANS, font_size=12, color="sub"),
}

ACCENT = {"kind": "linear", "angle": 180,
          "stops": [{"color": "a1", "position": "0%"},
                    {"color": "a2", "position": "50%"},
                    {"color": "a3", "position": "100%"}]}


def tile_fill(i):
    """A distinct gradient per tile, derived from the index (no hand-tuning)."""
    pairs = [("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a4", "a1"),
             ("a1", "a3"), ("a2", "a4"), ("a3", "a1"), ("a4", "a2"), ("a1", "a4")]
    c0, c1 = pairs[i % len(pairs)]
    return {"kind": "linear", "angle": 90 + (i * 17) % 90,
            "stops": [{"color": c0, "position": "0%"}, {"color": c1, "position": "100%"}]}


def chrome(b, sid, kicker, title, n, ghost=None):
    """Shared slide chrome, applied by a function (DRY reuse via code)."""
    page = b.page(sid, canvas=CANVAS, coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill="ink")
    page.rect([0, 0, 10, H], fill=ACCENT)
    if ghost is not None:
        page.text([W - 430, 70, 600, 420], ghost, style="ghost")
    page.layer("chrome")
    page.text([72, 64, W - 144, 22], kicker, style="kicker")
    page.text([72, 96, W - 144, 60], title, style="title")
    page.rect([72, H - 64, W - 144, 2], fill="line")
    page.text([72, H - 50, 600, 18],
              f"FrameGraph · layout mechanism {n} of 5", style="foot")
    page.layer("body")
    return page


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Beyond the Box — Layout Mechanisms",
                        profile="mixed", lang="en")
    for name, value in COLORS.items():
        b.define_color(name, value)
    for name, style in STYLES.items():
        b.define_text_style(name, **style)
    b.define_stroke_style("grid", color="line", width=1)

    # ---- 0. TITLE — absolute (the baseline / the critique) --------------- #
    page = chrome(b, "s0-title", "A presentation about presentations",
                  "Are all layouts\njust the same set?", 0, ghost="?")
    page.text([72, 250, 760, 120],
              "Only if you author at one altitude: hand-placed [x, y, w, h] boxes. "
              "Then bento, editorial and collage are the SAME primitive with "
              "different numbers.", style="sub")
    page.text([72, 470, 820, 120],
              "The next five slides are each produced by a DIFFERENT mechanism — "
              "engine-arranged groups, a chart, a table, and a reflowing flow "
              "document — so the structure differs, not just the coordinates.",
              style="note")

    # ---- 1. RENDERER-ARRANGED GRID — engine tiles a list ----------------- #
    page = chrome(b, "s1-grid", "Mechanism 1 — renderer-arranged group",
                  "I pass a list. The engine tiles it.", 1)
    # nine children, each box [0,0,w,h]: NO x/y authored — the grid layout places them.
    cards = [{"type": "rect", "box": [0, 0, 240, 130], "radius": 16, "fill": tile_fill(i)}
             for i in range(9)]
    page.group(cards, box=[72, 196, 760, 430],
               layout={"kind": "grid", "columns": 3, "gap": 20})
    page.text([880, 200, 340, 28], "layout = grid, columns 3", style="note")
    page.text([880, 250, 340, 380],
              "Every tile's box is [0, 0, w, h]. Not one x/y coordinate is typed. "
              "Add or remove an item from the list and the engine re-tiles — the "
              "layout is computed from intent, not transcribed.", style="sub")

    # ---- 2. RENDERER-ARRANGED NESTING — a row of columns ----------------- #
    page = chrome(b, "s2-nest", "Mechanism 2 — layouts compose",
                  "A row of columns.", 2)
    columns = []
    for c in range(4):
        stack = [{"type": "rect", "box": [0, 0, 150, 90], "radius": 12,
                  "fill": tile_fill(c * 2 + r)} for r in range(3)]
        columns.append({"type": "group", "box": [0, 0, 150, 320],
                        "layout": {"kind": "column", "gap": 16}, "children": stack})
    page.group(columns, box=[72, 210, 760, 320],
               layout={"kind": "row", "gap": 24})
    page.text([880, 220, 330, 300],
              "Outer group: kind=row. Each child is itself a kind=column group. "
              "The engine arranges the row, then each column arranges its own "
              "children. Layouts nest and compose — you can't get that by typing "
              "coordinates faster.", style="sub")

    # ---- 3. CHART — geometry from a data domain -------------------------- #
    page = chrome(b, "s3-chart", "Mechanism 3 — chart",
                  "Geometry derived from data.", 3)
    page.rect([72, 200, 760, 460], radius=18, fill="ink2")
    frame = Frame(domain=(0, 0, 12, 100), box=(150, 250, 620, 360))
    chart = (
        Chart(frame)
        .axes(x_ticks=[0, 3, 6, 9, 12], y_ticks=[0, 25, 50, 75, 100],
              x_format=lambda v: f"{v:g}", y_format=lambda v: f"{v:g}",
              grid=True, axis_color="#3a4374", grid_color="#222a52",
              label_style={"class": "chartlab"})
        .line([(v, 8 * v) for v in range(0, 13)], stroke="#22d3ee", width=3,
              smooth=True, label="absolute (linear effort)")
        .line([(v, min(4 * v ** 1.45, 100)) for v in range(0, 13)], stroke="#ff5e7e",
              width=3, smooth=True, label="mechanisms (compounding reuse)")
        .legend(at="tl", label_style={"class": "chartlab"})
    )
    page.extend(chart.objects())
    page.text([880, 220, 330, 300],
              "Axes, ticks, gridlines and two smoothed series come from a data "
              "domain mapped into a box by Frame. No point was hand-placed; move "
              "the domain and everything re-scales.", style="sub")

    # ---- 4. TABLE — a tabular model ------------------------------------- #
    page = chrome(b, "s4-table", "Mechanism 4 — table",
                  "Rows and columns, not free boxes.", 4)
    page.rect([72, 200, 1136, 420], radius=18, fill="paper")
    page.add({
        "type": "table",
        "box": [104, 232, 1072, 356],
        "zebra": True,
        "stroke_style": "grid",
        "row_height": 46,
        "header_height": 52,
        "cell_padding": 12,
        "style": {"header_fill": "a2", "header_text": "thw", "cell_text": "tdd"},
        "columns": [
            {"label": "Mechanism", "width": "30%", "align": "left"},
            {"label": "Who places it", "width": "26%", "align": "left"},
            {"label": "Adapts to content?", "width": "22%", "align": "center"},
            {"label": "Reusable?", "width": "22%", "align": "center"},
        ],
        "header": ["Mechanism", "Who places it", "Adapts to content?", "Reusable?"],
        "rows": [
            ["Absolute boxes", "You (x, y)", "No", "No"],
            ["Group layout", "The engine", "Yes — re-tiles", "Yes"],
            ["Chart / Frame", "Data domain", "Yes — re-scales", "Yes"],
            ["Flow + master", "The paginator", "Yes — reflows", "Yes (master)"],
        ],
    })

    # ---- 5. FLOW — reflowing, multi-column, auto-paginated --------------- #
    b.define_master("report", {
        "canvas": "A4",
        "regions": [{"id": "col", "box": [56, 96, 483, 700],
                     "columns": 2, "column_gap": 26}],
        "running": {
            "header": [{"type": "text", "text": "Beyond the Box — appendix",
                        "style": "running", "box": [56, 56, 483, 14]}],
            "page_number": {"font_family": SANS, "font_size": "9pt",
                            "color": "sub", "text_align": "center"},
        },
    })
    # A meaningful opener, then lorem bulk (SDK helper) to force real pagination.
    para = (
        "A flow section is not a slide. There are no object coordinates at all: a "
        "story of headings and paragraphs is poured into the master's regions and "
        "the paginator breaks it into as many pages as the content needs. Change a "
        "sentence and the column rebalances; change the region and the whole "
        "document repaginates. "
    )
    b.flow("s5-flow", master="report", story=[
        {"type": "heading", "level": 1, "text": "The flow model", "style": "fTitle"},
        {"type": "paragraph", "style": "fLead",
         "text": "Same document, a completely different layout engine — text that "
                 "sets itself into the master's region and across as many pages as "
                 "it takes. (The region declares two columns; the SVG proxy renders "
                 "one — multi-column validates but is a backend feature.)"},
        {"type": "heading", "level": 2, "text": "Why it is not the same set", "style": "fH"},
        {"type": "paragraph", "style": "fBody", "text": para + lorem(sentences=8, start=False)},
        {"type": "paragraph", "style": "fBody", "text": lorem(sentences=12, offset=5)},
        {"type": "heading", "level": 2, "text": "What the author writes", "style": "fH"},
        {"type": "paragraph", "style": "fBody", "text": lorem(sentences=12, offset=9)},
        {"type": "paragraph", "style": "fBody", "text": lorem(sentences=10, offset=14)},
    ])
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} section(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:25]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "fixtures", "layout-mechanisms-deck.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
