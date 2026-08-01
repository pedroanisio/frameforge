#!/usr/bin/env python3
"""Export a document to a self-contained, accessible HTML page — and prove parity.

The HTML target used to be a second renderer with its own idea of what a
document was. It drew 13 of the model's 34 object types and replaced the rest
with grey "unsupported type" boxes, so a deck with a table or a UML box exported
to HTML looked broken while the same document exported to SVG looked right.

It is painted by the shared engine now, so whatever `--to svg` can draw, `--to
html` draws. This example builds a page that deliberately uses object types the
old backend could not, writes the HTML, and then *checks its own claim* rather
than asserting it: it renders the same document to SVG and compares the marks.

Run it::

    python static/examples/html_export_parity.py [-o out/html-parity.html]

Three ways to reach the same renderer
-------------------------------------
* CLI  — ``ff-render doc.fg.yaml --to html --out DIR``
* SDK  — ``from frameforge.sdk import render_html`` (used below)
* MCP  — any render tool with ``to="html"``; the page is written into the
  session and reported as ``result.html`` + the
  ``frameforge://session/<id>/document.html`` resource (by reference — the tool
  never inlines a whole document).

What you get in the file
------------------------
One HTML document with no external assets: a `<figure>` per page wrapping inline
SVG artwork, the document's own palette hoisted to `:root` custom properties, its
named text styles as `.fg-ts-<name>` classes, a screen-reader landmark heading,
and any authored `Page.links` as a real `<nav>`. It needs no server, no network
and no optional dependency — open it, mail it, or serve it as-is.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import DocumentBuilder, render_html  # noqa: E402
from frameforge.sdk.conform import render_pages_with_stats  # noqa: E402

#: Leaf marks, so the parity check compares artwork and ignores the structural
#: `<g>` wrappers HTML adds (layer tree, object identity) and SVG declines.
_LEAF = re.compile(
    r"<(?:rect|ellipse|circle|line|polygon|polyline|path|image)\b[^>]*/?>"
    r"|<text\b[^>]*>.*?</text>",
    re.DOTALL,
)


def build():
    """A page using object types the standalone HTML backend could not draw."""
    b = DocumentBuilder(title="HTML export — engine parity")
    for name, value in (("ink", "#14213f"), ("accent", "#1f4fd8"),
                        ("paper", "#ffffff")):
        b.define_color(name, value)
    b.define_style("title", font_size=26, font_weight=700, color="ink")
    b.define_style("body", font_size=12, color="ink")

    page = b.page("p1", canvas={"size": [720, 460], "units": "px"})
    page.rect([0, 0, 720, 460], id="bg", fill="paper", decorative=True)
    page.text([40, 34, 640, 34], "Everything on this page also exports to SVG",
              id="heading", style="title")

    # A table: previously a grey placeholder in HTML.
    page.add({"type": "table", "id": "spec",
              "box": [40, 96, 300, 120],
              "rows": [["target", "types"], ["svg", "34"], ["html", "34"]]})

    # A UML classifier: the whole UML surface was invisible in HTML.
    page.add({"type": "uml.classifier_box", "id": "widget",
              "box": [400, 96, 280, 120], "name": "Renderer",
              "attributes": ["painter: ScenePainter"],
              "operations": ["render_page(page)"]})

    # A connector between them: also previously a placeholder. Note the P3
    # split — `stroke` is PAINT (a colour), geometry lives in `stroke_style`.
    b.define_stroke_style("hair", width=1.5)
    page.add({"type": "connector", "id": "link",
              "from": {"ref": "spec"}, "to": {"ref": "widget"},
              "stroke": "accent", "stroke_style": "hair"})

    page.text([40, 250, 640, 60],
              "One builder paints both targets, so this page cannot drift from "
              "its SVG twin — the check below is run, not asserted.",
              id="note", style="body")
    return b.build()


def marks(svg: str) -> list[str]:
    """Leaf marks, normalised past the HTML-only additions."""
    out = []
    for mark in _LEAF.findall(svg):
        mark = re.sub(r' class="fg-ts-[^"]*"', "", mark)
        mark = re.sub(r"var\(--fg-[^,]+, ([^)]*)\)", r"\1", mark)
        out.append(mark)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "out", "html-parity.html"))
    args = ap.parse_args()

    doc = build()
    html = render_html(doc)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)

    # Verify the parity claim instead of stating it (PALS's Law: an unverified
    # claim about generated output is not a result).
    svgs, _stats = render_pages_with_stats(doc)
    same = marks(html) == marks("".join(svgs))

    print(f"wrote {args.out} ({len(html):,} bytes)")
    print(f"  palette tokens hoisted : {html.count('--fg-')}")
    print(f"  text-style classes     : {len(set(re.findall(r'fg-ts-[a-z0-9-]+', html)))}")
    print(f"  identified objects     : {len(re.findall(r'<g id=', html))}")
    print(f"  unsupported placeholders: {html.count('unsupported type')}")
    print(f"  marks match --to svg   : {same}")
    return 0 if same and "unsupported type" not in html else 1


if __name__ == "__main__":
    raise SystemExit(main())
