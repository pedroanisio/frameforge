#!/usr/bin/env python3
"""FrameForge — the logo, as a standalone, reusable FrameForge document.

This file is the **canonical home of the FrameForge mark**. ``mark()`` below is the
single source of truth for the logo geometry — the seed deck imports it from here
rather than redefining it, so the mark can never diverge between the logo asset and
the places that stamp it.

The logo is *the framed derivation*: a square **Frame** (four corner brackets — the
bounded, finished artifact) holding a minimal **Graph** (one source node deriving a
three-node fan whose nodes lie on a common arc — equal radius, equal angle).
Colour mirrors the wordmark: Frame = ink, Forge = blue; it collapses to one ink for
mono and inverts for reversed, and stays crisp to favicon size.

``build()`` emits one clean master per variant — primary (two-tone), mono
(one-colour), reversed (on ink), favicon (tight crop), and the horizontal lockup
(mark + wordmark) — each on a tightly-cropped canvas with a defined clear-space,
ready to drop onto any surface. They are written to the out-of-tree brand-asset
location, ``_tmp/brand/`` (brand assets are non-core and stay out of the tree).

Run from the repository root::

    uv run python static/examples/frameforge_logo.py   # writes _tmp/brand/frameforge-*.svg + _tmp/brand/frameforge-logo.fg.yaml
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT_DIR = os.path.join(ROOT, "_tmp", "brand")
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    measure_text,
    render_page_svgs,
    serialize,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Brand tokens used by the mark (docs/BRAND.md §4). The mark needs only these.
# --------------------------------------------------------------------------- #
INK    = "#15181E"   # graphite — the "Frame" half
PAPER  = "#FBFAF6"   # warm technical paper (for reversed strokes)
CANVAS = "#FFFFFF"   # open-node fill on a light ground
FRAME  = "#1F4FD8"   # frame-blue — the "Forge" half

GRAPH = "#12B0C3"   # graph-cyan — the derivation edges (the "Graph" flow)
SANS = ["IBM Plex Sans", "DejaVu Sans", "Helvetica", "Arial", "sans-serif"]
MONO = ["IBM Plex Mono", "DejaVu Sans Mono", "Menlo", "monospace"]


# --------------------------------------------------------------------------- #
# THE MARK — single source of truth. Imported by examples/frameforge_seed_deck.py.
# --------------------------------------------------------------------------- #
def mark(page, cx, cy, size, *, frame=INK, graph=FRAME, node_fill=CANVAS):
    """The FrameForge mark — *the framed derivation*. The name's two halves fuse
    into one glyph: a square **Frame** (four corner brackets — the bounded,
    finished artifact, and the deck's own page-chrome motif) holding a minimal
    **Graph** (one source node deriving a three-node fan). The square frame gives
    the directional graph a stable 1:1 lockup with fixed clear-space.

    Constructed, not eyeballed: the three derived nodes lie on a *common arc* —
    equal radius ``R`` and equal angular step ``θ`` from the source — so the fan
    is provably symmetric. Drawn on a normalized grid scaled by ``size`` (the icon
    side), centred on ``(cx, cy)``.

    Colour mirrors the wordmark: ``frame`` (ink) for the Frame, ``graph`` (blue)
    for the Graph. Pass ``graph=INK`` for the one-colour form, or invert all three
    colours for the reversed-on-ink form — so the mark is mono-safe and scales to
    a favicon. ``size`` drives every weight and radius proportionally."""
    import math

    # Stroke weights scale with `size` but are floored, so the mark stays crisp at
    # small sizes (optical-minimum compensation) instead of fading to sub-pixel.
    sw = max(size * 0.013, 1.1)                    # frame stroke
    ew = max(size * 0.010, 0.9)                    # edge stroke
    nw = max(size * 0.013, 1.0)                    # node stroke
    half = size / 2.0
    arm = size * 0.26                              # corner-bracket arm length
    for dx in (-1, 1):                             # four corner brackets
        for dy in (-1, 1):
            x, y = cx + dx * half, cy + dy * half
            page.line([x, y], [x - dx * arm, y], stroke=frame,
                      stroke_style={"stroke_width": sw})
            page.line([x, y], [x, y - dy * arm], stroke=frame,
                      stroke_style={"stroke_width": sw})

    sx, sy = cx - 0.22 * size, cy                  # source node (left of centre)
    R, th = 0.46 * size, math.radians(30)          # equal radius, equal angle
    derived = [(sx + R * math.cos(a), sy - R * math.sin(a)) for a in (th, 0.0, -th)]
    for dx, dy in derived:                         # derivation edges
        page.line([sx, sy], [dx, dy], stroke=graph,
                  stroke_style={"stroke_width": ew})
    for dx, dy in derived:                         # derived nodes (open)
        page.circle([dx, dy], size * 0.052, fill=node_fill, stroke=graph,
                    stroke_style={"stroke_width": nw})
    page.circle([sx, sy], size * 0.075, fill=graph, stroke=graph,
                stroke_style={"stroke_width": nw})  # source (filled)


def wordmark(page, x, y, size, *, frame_color=INK, graph_color=FRAME, box_w=900):
    """'Frame' (ink) + 'Forge' (frame-blue) as ONE text with two coloured spans.

    Emitting the lockup as a single text *flow* — not two objects, one
    hand-positioned at a guessed width — means 'Forge' always follows 'Frame' in
    whatever font a renderer resolves. The second run carries no x, so it can't
    overlap or drift across viewers; the SVG and the PDF agree. ``box_w`` bounds the
    text box (default leaves slack for headline use; the logo lockup passes a
    measured width so the box fits its tight canvas)."""
    page.add({"type": "text", "box": [x, y, box_w, int(size * 1.3)],
              "spans": [{"text": "Frame", "style": {"color": frame_color}},
                        {"text": "Forge", "style": {"color": graph_color}}],
              "style": {"font_family": SANS, "font_size": size,
                        "font_weight": 700, "letter_spacing": -1.5}})


def fan(page, ox, oy, target_x, source_label, targets, *, span=300.0,
        source=FRAME, edge=GRAPH, node_stroke=INK, node_fill=CANVAS,
        label=INK, node_r=9.0, src_r=14.0, label_size=15.0, sw=2.0):
    """The derivation fan — the brand mark, *applied* as a labelled diagram: one
    filled source node fanning via edges to N target nodes, each labelled. This is
    the same native composition the roadmap dogfood (examples/roadmap_publication.py)
    ships in its Instagram stories and A4 print PDF, lifted here as a parametric
    primitive so it scales to any ground (light deck or dark story). ``(ox, oy)`` is
    the source; targets stack at ``target_x`` across ``span``; colours/sizes are
    parameterised so it inverts cleanly onto a dark ground."""
    n = len(targets)
    for i, lab in enumerate(targets):
        ty = oy + (i * span / (n - 1) - span / 2 if n > 1 else 0.0)
        page.line([ox, oy], [target_x, ty], stroke=edge,
                  stroke_style={"stroke_width": sw})
        page.circle([target_x, ty], node_r, fill=node_fill, stroke=node_stroke,
                    stroke_style={"stroke_width": sw})
        page.add({"type": "text",
                  "box": [target_x + node_r + 14, ty - label_size, 360,
                          label_size * 2.2],
                  "spans": [{"text": lab, "style": {"color": label}}],
                  "style": {"font_family": MONO, "font_size": label_size,
                            "font_weight": 600}})
    page.circle([ox, oy], src_r, fill=source, stroke=source,
                stroke_style={"stroke_width": sw})
    page.add({"type": "text",
              "box": [ox - 250, oy - label_size, 232, label_size * 2.2],
              "spans": [{"text": source_label, "style": {"color": label}}],
              "style": {"font_family": MONO, "font_size": label_size,
                        "font_weight": 700, "align": "right"}})


# --------------------------------------------------------------------------- #
# The logo document — one clean master per variant.
# --------------------------------------------------------------------------- #
CANVAS_PX = 512        # master canvas (vector — scales to any size)
CLEARSPACE = 0.25      # clear-space margin as a fraction of the mark side


def _logo_page(b, sid, *, side=CANVAS_PX, ground=None, msize=None, **mark_kw):
    """One square master: optional ``ground`` fill, then the mark centred with a
    ``CLEARSPACE`` margin (overridable via ``msize`` for tight crops)."""
    page = b.page(sid, canvas={"size": [side, side], "units": "px"},
                  coordinate_mode="absolute")
    if ground is not None:
        page.rect([0, 0, side, side], fill=ground)
    page._lettering_depth += 1
    if msize is None:
        msize = side / (1 + 2 * CLEARSPACE)
    mark(page, side / 2.0, side / 2.0, msize, **mark_kw)
    return page


LOCKUP_WORD = "FrameForge"
_LETTER_SPACING = -1.5


def _lockup_page(b, sid, *, m=176.0, fs=128.0):
    """The horizontal lockup: the mark + the wordmark on one tightly-cropped canvas.
    The canvas width is *measured*, not guessed — ``measure_text`` gives the wordmark
    width, padded with a small safety factor (the actual render font can be a touch
    wider than the metric), so the crop holds and the text never clips in whatever
    font the renderer resolves."""
    cs = CLEARSPACE * m                                  # clear-space margin
    gap = 0.22 * m                                       # mark → word gap
    word_w = measure_text(LOCKUP_WORD, font_family=SANS, font_size=fs, bold=True) * 1.07
    wx = cs + m + gap
    width = wx + word_w + cs
    height = m + 2 * cs
    page = b.page(sid, canvas={"size": [round(width), round(height)], "units": "px"},
                  coordinate_mode="absolute")
    page._lettering_depth += 1
    mark(page, cs + m / 2.0, height / 2.0, m)
    wordmark(page, wx, height / 2.0 - fs * 0.66, fs, box_w=round(word_w))
    return page


# (page id, output filename under brand/, strip the injected white ground?)
MASTERS = [
    ("logo-primary",  "frameforge-mark.svg",          True),
    ("logo-mono",     "frameforge-mark-mono.svg",     True),
    ("logo-reversed", "frameforge-mark-reversed.svg", False),   # keeps its ink ground
    ("logo-favicon",  "frameforge-mark-favicon.svg",  True),
    ("logo-lockup",   "frameforge-wordmark.svg",      True),    # the horizontal lockup
]

# The SVG painter always injects an opaque white page ground. A logo master must be
# *transparent* so it can sit on any surface (the brand surface is warm paper
# #FBFAF6, on which a baked pure-white rect would show). We strip that one injected
# rect from the exported masters; the reversed variant keeps its own ink ground,
# drawn on top, as the visible background. Verified, not assumed (PALS's Law): if
# the renderer ever changes this literal, the build fails loudly instead of silently
# shipping a white box.
_INJECTED_WHITE_BG = '<rect width="100%" height="100%" fill="white"/>'


def _transparent(svg: str) -> str:
    if _INJECTED_WHITE_BG not in svg:
        raise RuntimeError(
            "renderer no longer injects the expected white background rect — update "
            "_INJECTED_WHITE_BG in examples/frameforge_logo.py")
    return svg.replace(_INJECTED_WHITE_BG, "", 1)


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameForge — Logo", profile="deck", lang="en")
    _logo_page(b, "logo-primary")                                  # two-tone (transparent)
    _logo_page(b, "logo-mono", graph=INK)                          # one-colour ink (transparent)
    _logo_page(b, "logo-reversed", ground=INK,                     # reversed on ink
               frame=PAPER, graph=PAPER, node_fill=INK)
    _logo_page(b, "logo-favicon", side=64, msize=56)               # tight favicon master
    _lockup_page(b, "logo-lockup")                                 # mark + wordmark
    return b


def build_logo_document():
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    return doc, report


def build_outputs(doc=None) -> dict[str, str]:
    """Return the exact committed brand-asset bytes for a freshly built logo."""
    if doc is None:
        doc, _report = build_logo_document()
    outputs: dict[str, str] = {}
    for (_sid, fname, strip), svg in zip(MASTERS, render_page_svgs(doc)):
        outputs[fname] = _transparent(svg) if strip else svg
    outputs["frameforge-logo.fg.yaml"] = serialize(doc, format="yaml")
    return outputs


def stale_outputs(out_dir, outputs: dict[str, str]) -> list[str]:
    """List generated logo outputs that are missing or differ on disk."""
    stale: list[str] = []
    out_dir = os.fspath(out_dir)
    for fname, fresh in outputs.items():
        path = os.path.join(out_dir, fname)
        if not os.path.exists(path):
            stale.append(fname)
            continue
        with open(path, encoding="utf-8") as fh:
            if fh.read() != fresh:
                stale.append(fname)
    return stale


def write_outputs(out_dir, outputs: dict[str, str]) -> None:
    out_dir = os.fspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    for fname, content in outputs.items():
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as fh:
            fh.write(content)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build or check FrameForge logo assets.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the out-of-tree brand assets (_tmp/brand) differ from a fresh build",
    )
    args = parser.parse_args(argv)

    doc, report = build_logo_document()
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} logo master(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    outputs = build_outputs(doc)
    if args.check:
        stale = stale_outputs(OUT_DIR, outputs)
        if stale:
            print(f"STALE logo output(s): {', '.join(stale)}")
            print("Run `uv run python examples/frameforge_logo.py` and commit the regenerated assets.")
            return 1
        print(f"Logo assets are fresh in {OUT_DIR}")
        return 1 if errors else 0

    write_outputs(OUT_DIR, outputs)
    print(f"Wrote {len(MASTERS)} master(s) to {OUT_DIR} + frameforge-logo.fg.yaml")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
