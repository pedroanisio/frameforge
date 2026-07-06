#!/usr/bin/env python3
"""Pattern compose — filled catalog patterns as rendered deck pages.

The #28/#29 pipeline end to end: pick patterns from the 375-pattern catalog,
validate a ``{role: content}`` fill against each pattern's contract (sidecar
overrides included), and compose them into absolute 1920×1080 deck pages —
zone boxes computed from the placement vocabulary, treatments (cards, accent
bars, label slots) applied from the pattern's enterprise layout.

Writes ``_tmp/pattern-compose/`` — one YAML + one SVG per pattern — for the
SWOT Analysis (10), the Business Model Canvas (44, object-item sidecar), and
the Diagnostic Summary (111, column bands). The MCP run contract is
``build()`` (returns the composed SWOT document).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.patterns import compose, load_sidecars  # noqa: E402
from framegraph.sdk import render_page_svgs, serialize  # noqa: E402

SHOWN = (10, 44, 111)


def build():
    """MCP contract: one composed document (the SWOT plate)."""
    return compose(10, load_sidecars()[10].example_fill)


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "pattern-compose")
    os.makedirs(out, exist_ok=True)
    sidecars = load_sidecars()
    for pid in SHOWN:
        doc = compose(pid, sidecars[pid].example_fill)
        stem = os.path.join(out, f"pattern-{pid:03d}")
        with open(f"{stem}.fg.yaml", "w", encoding="utf-8") as fh:
            fh.write(serialize(doc))
        svg = render_page_svgs(doc, base_dir=out)[0]
        with open(f"{stem}.svg", "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"  pattern {pid:03d} -> {stem}.fg.yaml / .svg")
    print(f"Wrote {len(SHOWN)} composed pattern(s) to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
