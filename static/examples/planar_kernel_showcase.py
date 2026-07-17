#!/usr/bin/env python3
"""Planar geometry kernel — booleans, offset, surgery, regions (issue #45).

The W1 kernel end to end, one panel per capability: Pathfinder booleans
(union / intersect / subtract-with-hole / divide), closed-polygon offset
rings, a knife cut, and the Live-Paint region decomposition of two
overlapping shapes, each face filled its own colour. Everything on this
page is COMPUTED by ``sdk.planar`` and emitted as plain even-odd ``path``
objects (§A.0). Writes ``_tmp/planar-kernel/`` (YAML + SVG). The MCP run
contract is ``build()``; the canonical fixture
``tests/fixtures/planar-kernel.fg.yaml`` is this document verbatim.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import planar, render_page_svgs, serialize  # noqa: E402
from frameforge.sdk.model import HEAD_VERSION, validate_document  # noqa: E402

_SANS = ["DejaVu Sans", "Arial", "sans-serif"]
_FACE = ["#0f7d88", "#b5642c", "#7c3aed", "#3f7d4e", "#b03060", "#1d4ed8"]


def _at(rings, dx, dy):
    return [[(x + dx, y + dy) for x, y in r] for r in rings]


def _label(x, y, text):
    est = len(text) * 0.52 * 12
    return {"type": "text", "box": [x, y, est + 8, 17], "text": text,
            "style": {"font_family": _SANS, "font_size": 12, "color": "ink",
                      "white_space": "nowrap"}}


def build():
    """MCP contract: the planar-kernel showcase page."""
    sq = [(0, 0), (60, 0), (60, 60), (0, 60)]
    sq2 = [(30, 30), (90, 30), (90, 90), (30, 90)]
    inner = [(18, 18), (42, 18), (42, 42), (18, 42)]

    objects = [
        {"type": "rect", "box": [0, 0, 960, 540], "fill": "paper",
         "decorative": True},
        _label(40, 24, "sdk.planar — one kernel, five Pathfinder-class capabilities (#45)"),
    ]

    # row 1: the four booleans
    panels = [
        ("union", planar.union([sq], [sq2])),
        ("intersect", planar.intersect([sq], [sq2])),
        ("subtract (hole)", planar.subtract([sq], [inner])),
    ]
    x = 40
    for name, rings in panels:
        objects.append(_label(x, 60, name))
        objects.append(planar.to_path(_at(rings, x, 80), fill="teal",
                                      id=f"bool-{name.split()[0]}"))
        x += 200

    # divide: three pieces, each its own colour
    objects.append(_label(x, 60, "divide (3 pieces)"))
    for i, piece in enumerate(planar.divide([sq], [sq2])):
        objects.append(planar.to_path(_at(piece, x, 80), fill=_FACE[i],
                                      id=f"divide-{i}"))

    # row 2: offset rings, knife cut, live-paint regions
    y2, x = 260, 40
    objects.append(_label(x, y2, "offset ±12 (miter)"))
    base = [(10, 10), (70, 10), (70, 70), (10, 70)]
    for d, color in ((12, "#d7e6e8"), (0, "teal"), (-12, "paper")):
        rings = planar.offset_polygon(base, d) if d else [base]
        objects.append(planar.to_path(_at(rings, x, y2 + 20), fill=color,
                                      id=f"offset-{d}"))

    x += 200
    objects.append(_label(x, y2, "cut_along (knife)"))
    for i, piece in enumerate(planar.cut_along(sq, (0, 10), (60, 50))):
        objects.append(planar.to_path(_at(piece, x + i * 8, y2 + 20),
                                      fill=_FACE[i], id=f"cut-{i}"))

    x += 200
    objects.append(_label(x, y2, "fill_regions (Live Paint)"))
    for i, face in enumerate(planar.fill_regions([sq, sq2])):
        objects.append(planar.to_path(_at(face, x, y2 + 20), fill=_FACE[i],
                                      id=f"face-{i}",
                                      stroke="paper",
                                      stroke_style={"stroke_width": 1}))

    doc = {"dsl": "FrameForge", "version": HEAD_VERSION,
           "title": "planar kernel showcase", "profile": "diagram",
           "defs": {"tokens": {"colors": {"paper": "#fcfbf8",
                                          "ink": "#1d1e22",
                                          "teal": "#0f7d88"}}},
           "pages": [{"mode": "page", "id": "planar-kernel",
                      "canvas": {"size": [960, 540], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "main", "objects": objects}]}]}
    validate_document(doc)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "planar-kernel")
    os.makedirs(out, exist_ok=True)
    doc = build()
    with open(os.path.join(out, "planar-kernel.fg.yaml"), "w",
              encoding="utf-8") as fh:
        fh.write(serialize(doc))
    svg = render_page_svgs(doc, base_dir=out)[0]
    with open(os.path.join(out, "planar-kernel.svg"), "w",
              encoding="utf-8") as fh:
        fh.write(svg)
    print(f"Wrote showcase to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
