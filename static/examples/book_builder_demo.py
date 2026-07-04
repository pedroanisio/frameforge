#!/usr/bin/env python3
"""BookBuilder — the semantic book layer end to end (roadmap item 8).

A three-chapter A5 book from one fluent builder: front matter (title,
author, contents), build-time chapter/section numbering, per-chapter
figure numbers folded into captions (`Figure 2.1 — …`), figures kept with
their captions, chapters opening on fresh pages — all lowered through
``FlowBuilder`` and paginated by the flow engine (ADR-0003, Johnston
margins). Writes ``_tmp/book-builder/`` (YAML + SVGs). The MCP run
contract is ``build()``; the canonical fixture
``tests/fixtures/book-composition.fg.yaml`` is this document verbatim.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import BookBuilder, render_page_svgs, serialize  # noqa: E402
from framegraph.sdk import stroke_outline  # noqa: E402

PROSE = (
    "Composition is a settling of accounts between content and page. The "
    "column earns its measure, the margin its silence; what remains is the "
    "text's own rhythm, carried line by line through the book. "
)


def build():
    """MCP contract: a small three-chapter book."""
    book = BookBuilder(title="On Composition", author="FrameGraph Press",
                       lang="en")

    ch1 = book.chapter("The Column")
    ch1.para(PROSE * 5)
    ch1.section("Measure and margin")
    ch1.para(PROSE * 4)
    ch1.figure({"type": "rect", "box": [0, 0, 300, 110], "fill": "#0f7d88",
                "radius": 6},
               caption="The column as a solid", alt="teal column plate")
    ch1.section("The grey page")
    ch1.para(PROSE * 3)

    ch2 = book.chapter("The Line")
    ch2.para(PROSE * 4)
    ch2.figure(stroke_outline([(0, 60), (90, 20), (190, 70), (300, 30)],
                              width=14, smooth=True, pen_angle=30,
                              pen_thin=0.2, fill="#1d1e22"),
               caption="A calligraphic line, computed", alt="swash plate")
    ch2.section("Breaks and keeps")
    ch2.para(PROSE * 4)

    ch3 = book.chapter("The Book")
    ch3.para(PROSE * 3)
    ch3.numbered(["Front matter carries the identity.",
                  "Chapters number themselves.",
                  "Figures keep their captions."])
    ch3.para(PROSE * 2)

    return book.build()


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "book-builder")
    os.makedirs(out, exist_ok=True)
    doc = build()
    with open(os.path.join(out, "book.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc))
    for i, svg in enumerate(render_page_svgs(doc, base_dir=out), 1):
        with open(os.path.join(out, f"page-{i:02d}.svg"), "w",
                  encoding="utf-8") as fh:
            fh.write(svg)
    print(f"Wrote the book to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
