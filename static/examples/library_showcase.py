#!/usr/bin/env python3
"""Library showcase — themes, symbol packs, and generators end to end.

The #32 content library in one runnable client: a themed cover + agenda +
insight page assembled from the symbol packs (expanded through
``sdk.expand``), then the two data-driven generators reproducing their
committed example data — the honeycomb capability map and the radial module
hub. Writes ``_tmp/library-showcase/`` — one YAML + one SVG per page. The
MCP run contract is ``build()`` (returns the honeycomb capability map).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.library import (  # noqa: E402
    honeycomb_capability_map,
    load_example,
    load_symbols,
    load_theme,
    module_hub_radial,
    support_text_styles,
)
from framegraph.sdk import expand, render_page_svgs, serialize  # noqa: E402
from framegraph.sdk.model import HEAD_VERSION  # noqa: E402


def build():
    """MCP contract: the honeycomb capability map from its committed data."""
    return honeycomb_capability_map(load_example("honeycomb"))


def build_symbol_pages():
    """Cover + agenda assembled from symbol packs under the McKinsey theme."""
    theme = load_theme("mckinsey")
    theme["text_styles"] = {**theme["text_styles"],
                            **support_text_styles("covers", "sections")}
    authored = {
        "dsl": "FrameGraph", "version": HEAD_VERSION,
        "title": "FrameGraph library — symbol packs", "profile": "deck",
        "defs": {"tokens": theme,
                 "symbols": load_symbols("covers", "sections")},
        "pages": [
            {"mode": "page", "id": "cover",
             "canvas": {"size": [960, 540], "units": "px"},
             "rendering": {"coordinate_mode": "absolute"},
             "layers": [{"id": "main", "objects": [
                 {"type": "use", "symbol": "cover_minimal_sidebar",
                  "box": [0, 0, 960, 540],
                  "params": {"title": "FrameGraph Library",
                             "subtitle": "Themes · symbol packs · generators",
                             "page_number": "01",
                             "bg_color": "#FFFFFF",
                             "accent_color": "accent",
                             "right_pane_color": "primary"}}]}]},
            {"mode": "page", "id": "agenda",
             "canvas": {"size": [960, 540], "units": "px"},
             "rendering": {"coordinate_mode": "absolute"},
             "layers": [{"id": "main", "objects": [
                 {"type": "use", "symbol": "agenda_left_pane",
                  "box": [0, 0, 960, 540],
                  "params": {"section_label": "Agenda",
                             "left_pane_color": "primary",
                             "accent_color": "accent",
                             "page_number": "02",
                             "item_1": "Seven consulting themes",
                             "item_2": "Cover and agenda symbol packs",
                             "item_3": "Insight box, KPI card, 2×2, stencil node",
                             "item_4": "Honeycomb capability map",
                             "item_5": "Radial module hub",
                             "item_6": "", "item_7": ""}}]}]},
        ],
    }
    return expand(authored).document.model_dump(by_alias=True,
                                                exclude_none=True)


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "library-showcase")
    os.makedirs(out, exist_ok=True)
    docs = {"symbols": build_symbol_pages(),
            "honeycomb": build(),
            "module-hub": module_hub_radial(load_example("module_hub"))}
    for name, doc in docs.items():
        stem = os.path.join(out, name)
        with open(f"{stem}.fg.yaml", "w", encoding="utf-8") as fh:
            fh.write(serialize(doc))
        for idx, svg in enumerate(render_page_svgs(doc, base_dir=out)):
            with open(f"{stem}-{idx}.svg", "w", encoding="utf-8") as fh:
                fh.write(svg)
        print(f"  {name} -> {stem}.fg.yaml / .svg")
    print(f"Wrote {len(docs)} library document(s) to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
