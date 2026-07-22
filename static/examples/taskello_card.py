#!/usr/bin/env python3
"""Taskello card — a pure-primitive recreation of a blurred-photo UI card.

A vector reconstruction of the "Taskello App / Card Design" reference
(a rounded cream card whose header is a blurred fiery photograph, cut by a
folder-tab, over a typographic body). The constraint is PURE PRIMITIVES —
no image objects, no embedded SVG, no raster filters (the SVG proxy drops
blur primitives anyway): the blurred photo band is rebuilt as a clipped
stack of user-space radial/linear gradients with `opacity` alpha ramps
(2.5.0 gradient geometry), the folder tab is one ogee path, and the card,
tab and type are rects, paths and text.

Geometry and palette were measured from the reference raster (370×377):
card [44, 47, 287, 273] r≈26 on #fefdf7; banner bottom y≈153; tab top
y≈131 with its S-curve joining at x≈205; fiery palette sampled on a grid.

Two editions build from one parametric card: page 1 is the pt-BR edition
(copy written as Brazilian product language — "Nota do dia", "Notas e
diário" — not word-by-word translation), page 2 keeps the reference's
English copy verbatim, since the recreation is scored against the source
pixels (NCC).

Run from the repository root::

    uv run python static/examples/taskello_card.py
    # writes _tmp/taskello/taskello-card{,-ptbr}.svg + YAML
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT_DIR = os.path.join(ROOT, "_tmp", "taskello")
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    render_page_svgs,
    serialize,
)

BG = "#fefdf7"
CARD = "#f4f3ea"
INK = "#161616"
MUTED = "#a9a89e"

# card frame (measured)
CX, CY, CW, CH = 44, 47, 287, 273
R = 26                       # card corner radius
BANNER_BOTTOM = 153
TAB_TOP = 131

# the banner silhouette: card-rounded top corners, straight bottom
BANNER_D = (f"M {CX} {BANNER_BOTTOM} L {CX} {CY + R} "
            f"Q {CX} {CY} {CX + R} {CY} L {CX + CW - R} {CY} "
            f"Q {CX + CW} {CY} {CX + CW} {CY + R} "
            f"L {CX + CW} {BANNER_BOTTOM} Z")

# the folder tab: left edge up, rounded top-left, shelf, then an ogee
# easing down onto the banner's bottom edge
TAB_D = (f"M {CX} {BANNER_BOTTOM + 2} L {CX} {TAB_TOP + 12} "
         f"Q {CX} {TAB_TOP} {CX + 12} {TAB_TOP} L 158 {TAB_TOP} "
         f"C 178 {TAB_TOP} 182 {BANNER_BOTTOM} 206 {BANNER_BOTTOM} "
         f"L 206 {BANNER_BOTTOM + 2} Z")


def _glow(gid, cx, cy, r, color, alpha=0.95, mid=0.55):
    """A soft radial blob: opaque core feathering to nothing — the pure-
    primitive stand-in for photographic blur."""
    return {"type": "ellipse", "id": gid, "center": [cx, cy], "rx": r, "ry": r,
            "decorative": True,
            "fill": {"kind": "radial", "at": [cx, cy], "radius": r,
                     "stops": [
                         {"color": color, "position": "0%", "opacity": alpha},
                         {"color": color, "position": "55%", "opacity": alpha * mid},
                         {"color": color, "position": "100%", "opacity": 0.0},
                     ]}}


def _banner_children(prefix: str = "") -> list[dict]:
    """The fiery blurred-photo band, darkest-to-brightest blob stack.

    ``prefix`` namespaces the object ids so the same band can appear on
    more than one page (ids are document-global)."""
    kids = [
        # matte base
        {"type": "rect", "id": "fire-base", "box": [CX, CY, CW, BANNER_BOTTOM - CY],
         "fill": "#5e1710", "decorative": True},
        # deep shadows, left and lower-left
        _glow("fire-dark-tl", 70, 58, 66, "#230402", 0.95),
        _glow("fire-dark-bl", 74, 132, 58, "#3f0a05", 0.9),
        # body of the fire
        _glow("fire-red-core", 150, 108, 105, "#c81404", 0.95),
        _glow("fire-red-right", 290, 125, 88, "#b30d02", 0.9),
        _glow("fire-orange-mid", 200, 90, 78, "#f97b27", 0.85),
        _glow("fire-orange-low", 252, 148, 86, "#f4680f", 0.95),
        _glow("fire-ember-left", 96, 100, 44, "#e1490e", 0.8),
        # brighter fire floor along the banner's lower edge (right of the tab)
        _glow("fire-floor-1", 195, 150, 62, "#e85a0e", 0.85),
        _glow("fire-floor-2", 300, 146, 72, "#d43e08", 0.9),
        _glow("fire-under-tab", 100, 126, 46, "#cc1103", 0.85),
        # hot highlights: a bead-chain of glows implies the diagonal
        # motion-blur streak of the source photo
        _glow("fire-peach", 122, 84, 44, "#f7cabb", 0.9),
        _glow("fire-streak-1", 105, 92, 26, "#ffece0", 0.9),
        _glow("fire-streak-2", 135, 78, 24, "#ffd9c4", 0.8),
        _glow("fire-streak-3", 165, 66, 20, "#f8c4ab", 0.6),
        _glow("fire-white", 96, 76, 28, "#ffe9dc", 0.85),
        _glow("fire-peach-2", 210, 118, 30, "#f3b49b", 0.6),
        # the pale smoky wash the title sits on (top-right): radials only —
        # a linear ramp leaves a hard alpha edge at its rect boundary
        _glow("fire-pale-tr", 322, 64, 74, "#c5a596", 0.95),
        _glow("fire-pale-tr2", 292, 54, 54, "#cbb2a4", 0.75),
        # re-darken the mid-right under the title (the wash must hug the
        # corner, not flood the banner's right half)
        _glow("fire-dark-mr", 300, 116, 55, "#8f0f04", 0.75),
        _glow("fire-dark-title", 245, 78, 40, "#4a0b05", 0.55),
    ]
    if prefix:
        for kid in kids:
            kid["id"] = f"{prefix}{kid['id']}"
    return kids


# The two copy decks. ``en`` is the reference art verbatim (the recreation
# must stay faithful to the source pixels); ``ptbr`` is the pt-BR edition —
# written as Brazilian product copy, not translated word by word ("Nota do
# dia" is what a notes app here would actually say; "card" and "app" stay,
# they are everyday market vocabulary).
COPY = {
    "en": {"app": "Taskello App", "design": "Card Design",
           "memo": "Daily memo", "sub": "Notes & Journaling",
           "num": "05", "doc": "Doc", "notes": "1270 Notes"},
    "ptbr": {"app": "App Taskello", "design": "Design de cards",
             "memo": "Nota do dia", "sub": "Notas e diário",
             "num": "05", "doc": "Doc", "notes": "1270 notas"},
}


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Taskello card — pure-primitive recreation",
                        profile="deck")
    # page 1: the pt-BR edition (the default the example showcases);
    # page 2: the reference-faithful English card (the NCC comparison target).
    _card_page(b, "card-ptbr", COPY["ptbr"])
    _card_page(b, "card", COPY["en"])
    return b


def _card_page(b: DocumentBuilder, page_id: str, copy: dict) -> None:
    pid = f"{page_id}-"
    pg = b.page(page_id, canvas={"size": [370, 377], "units": "px"})
    pg.rect([0, 0, 370, 377], id=f"{pid}bg", fill=BG, decorative=True)
    # soft card shadow (no raster filters: one low-alpha offset plate)
    pg.add({"type": "rect", "id": f"{pid}card-shadow",
            "box": [CX + 10, CY + 10, CW - 20, CH], "radius": R,
            "fill": "rgba(96, 78, 60, 0.09)", "decorative": True})
    pg.add({"type": "rect", "id": f"{pid}card", "box": [CX, CY, CW, CH],
            "radius": R, "fill": CARD, "decorative": True})
    # the blurred-photo band: gradient blobs clipped to the banner silhouette
    pg.group(_banner_children(pid), id=f"{pid}banner",
             clip={"shape": "path", "args": {"d": BANNER_D}},
             decorative=True)
    # the folder tab riding over the banner's lower-left
    pg.add({"type": "path", "id": f"{pid}tab", "d": TAB_D, "fill": CARD,
            "decorative": True})
    # ---- type layer (measured boxes) ---------------------------------- #
    pg.text([180, 60, 123, 16], copy["app"], id=f"{pid}t-app",
            style={"font_family": "Inter", "font_size": 13, "font_weight": 700,
                   "color": "#ffffff", "align": "right"})
    pg.text([180, 76, 123, 16], copy["design"], id=f"{pid}t-design",
            style={"font_family": "Inter", "font_size": 13, "font_weight": 700,
                   "color": "#ffffff", "align": "right"})
    pg.text([64, 137, 150, 17], copy["memo"], id=f"{pid}t-memo",
            style={"font_family": "Inter", "font_size": 14.5, "font_weight": 700,
                   "color": INK})
    pg.text([64, 156, 170, 16], copy["sub"], id=f"{pid}t-sub",
            style={"font_family": "Inter", "font_size": 13, "color": MUTED})
    pg.text([62, 273, 58, 32], copy["num"], id=f"{pid}t-num",
            style={"font_family": "Inter", "font_size": 30, "font_weight": 800,
                   "color": INK})
    pg.text([110, 288, 40, 14], copy["doc"], id=f"{pid}t-doc",
            style={"font_family": "Inter", "font_size": 12, "color": MUTED})
    pg.text([196, 283, 114, 16], copy["notes"], id=f"{pid}t-notes",
            style={"font_family": "Inter", "font_size": 13.5, "font_weight": 700,
                   "color": INK, "align": "right"})


def main() -> int:
    doc = build().build()
    os.makedirs(OUT_DIR, exist_ok=True)
    svgs = render_page_svgs(doc)
    names = ["taskello-card-ptbr.svg", "taskello-card.svg"]
    for name, svg in zip(names, svgs):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
    with open(os.path.join(OUT_DIR, "taskello-card.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {', '.join(names)} + YAML to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
