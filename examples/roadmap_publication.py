#!/usr/bin/env python3
"""Publish the FrameGraph v2 roadmap as two brand-true deliverables from one SDK client:

  * a print **PDF** (A4 pages, editorial) — render with tooling/render_pdf.py
  * an **Instagram Stories** set (1080x1920, 9:16) — render with tooling/render_chromium.py

Design follows docs/BRAND.md + the seed canonical deck: warm-paper interiors and an
ink cover, IBM Plex type, frame-blue / graph-cyan accents (flat — no gradients in
chrome), and the brand graphic language drawn with the SDK: corner crop-marks, a
hairline drafting grid, left-accent-bar cards, state chips, and the derivation fan.
The **logo is the original brand mark** — ``mark()``/``wordmark()`` are imported from
examples/framegraph_logo.py (the canonical source of truth) so it can never diverge.

Run from the repo root::

    uv run python examples/roadmap_publication.py
    uv run --group pdfout  python tooling/render_pdf.py      out/roadmap/roadmap-print.fg.yaml   --out out/roadmap
    uv run --group browser python tooling/render_chromium.py out/roadmap/roadmap-stories.fg.yaml --out out/roadmap/stories
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "examples"))   # for the canonical logo
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402
from framegraph_logo import mark, wordmark  # noqa: E402  — the canonical FrameGraph logo

# --- brand tokens (docs/BRAND.md §4, brand/framegraph.tokens.fg.yaml) -------- #
INK, PAPER, CANVAS = "#15181E", "#FBFAF6", "#FFFFFF"
FRAME, CYAN = "#1F4FD8", "#12B0C3"          # frame-blue (primary) · graph-cyan (flow)
GREEN, RED = "#1E9E5A", "#D23B2B"           # gate states: pass · drift
GRID, MUTE = "#D4D8DE", "#6B7280"           # hairlines · captions
MUTE_DK, GRID_DK = "#9AA3B5", "#2A2E3A"     # on-ink equivalents
MONO = ["IBM Plex Mono", "DejaVu Sans Mono", "monospace"]
SANS = ["IBM Plex Sans", "DejaVu Sans", "Helvetica", "Arial", "sans-serif"]


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None, transform=None, family=None):
    s = {"font_family": family or SANS, "font_size": size, "color": color}
    if weight is not None:
        s["font_weight"] = weight
    if align is not None:
        s["align"] = align
    if spacing is not None:
        s["letter_spacing"] = spacing
    if lh is not None:
        s["line_height"] = lh
    if transform is not None:
        s["text_transform"] = transform
    return s


def crop_marks(page, w, h, color, *, m=46, arm=40, sw=3):
    """The brand frame motif — technical-drawing corner brackets at the 4 corners."""
    for dx in (1, -1):
        for dy in (1, -1):
            x, y = (m if dx > 0 else w - m), (m if dy > 0 else h - m)
            page.line([x, y], [x + dx * arm, y], stroke=color, stroke_style={"stroke_width": sw})
            page.line([x, y], [x, y + dy * arm], stroke=color, stroke_style={"stroke_width": sw})


def hairline_grid(page, w, h, color, *, step):
    x = step
    while x < w:
        page.line([x, 0], [x, h], stroke=color, stroke_style={"stroke_width": 1})
        x += step
    y = step
    while y < h:
        page.line([0, y], [w, y], stroke=color, stroke_style={"stroke_width": 1})
        y += step


def _check(page, x, y, s, color):
    """A checkmark drawn as a polyline — renders identically in every backend
    (the ✓ glyph is tofu in the cairosvg PDF), and is an SDK-native state-chip glyph."""
    page.polyline([[x, y + 0.52 * s], [x + 0.38 * s, y + s], [x + s, y]],
                  stroke=color, fill="none",
                  stroke_style={"stroke_width": max(s * 0.16, 2),
                                "stroke_linecap": "round", "stroke_linejoin": "round"})


def _in_sync(page, right_x, y, *, fs, mono_w):
    """Draw the '✓ IN SYNC' state chip ending at right_x: a drawn check + mono label."""
    label_w = mono_w * len("IN SYNC")
    lx = right_x - label_w
    _check(page, lx - fs - 8, y + fs * 0.05, fs, GREEN)
    page.text([lx, y, label_w + 4, fs + 6], "IN SYNC",
              style=ts(fs, GREEN, weight=700, family=MONO, spacing=1))


# ---------------------------------------------------------------------------- #
#  Instagram Stories — 1080x1920, 9:16                                          #
# ---------------------------------------------------------------------------- #
SW, SH = 1080, 1920
MX = 84


def _topbar(page, *, dark):
    fg = PAPER if dark else INK
    mark(page, MX + 22, 96, 44, frame=fg, graph=FRAME, node_fill=(INK if dark else CANVAS))
    wordmark(page, MX + 54, 76, 30, frame_color=fg, graph_color=FRAME)
    _in_sync(page, SW - MX, 78, fs=24, mono_w=16)


def _footer(page, n, *, dark):
    page.rect([MX, SH - 116, SW - 2 * MX, 1.5], fill=(GRID_DK if dark else GRID))
    page.text([MX, SH - 100, 640, 26], "framegraph v2 · roadmap · draft",
              style=ts(22, MUTE_DK if dark else MUTE, family=MONO, spacing=1))
    page.text([SW - MX - 160, SH - 100, 160, 26], f"{n:02d} / 05",
              style=ts(22, MUTE_DK if dark else MUTE, family=MONO, align="right"))


def _lcard(page, box, accent, kicker, title, body):
    x, y, w, h = box
    page.rect([x, y, w, h], radius=16, fill=CANVAS, stroke=GRID, stroke_style={"stroke_width": 1.5})
    page.rect([x, y, 10, h], fill=accent)
    page.text([x + 44, y + 34, w - 88, 30], kicker,
              style=ts(25, accent, weight=700, family=MONO, spacing=2, transform="uppercase"))
    if title:
        page.text([x + 44, y + 74, w - 88, 56], title, style=ts(44, INK, weight=700, lh=1.04))
        body_y = y + 138
    else:
        body_y = y + 86
    page.text([x + 44, body_y, w - 88, y + h - body_y - 30], body, style=ts(31, MUTE, lh=1.42))


def _story(b, sid, *, dark=False):
    page = b.page(sid, canvas="instagram-story", coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, SW, SH], fill=INK if dark else PAPER)
    if not dark:
        hairline_grid(page, SW, SH, GRID, step=120)
    crop_marks(page, SW, SH, PAPER if dark else INK)
    page.layer("body")
    return page


def build_stories() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph v2 — Roadmap (Stories)", profile="deck", lang="en")

    # 1 — cover (ink)
    p = _story(b, "s1-cover", dark=True)
    _topbar(p, dark=True)
    mark(p, SW / 2, 560, 300, frame=PAPER, graph=FRAME, node_fill=INK)   # the original mark, hero
    wordmark(p, MX, 770, 104, frame_color=PAPER, graph_color=FRAME)
    p.text([MX, 912, SW - 2 * MX, 30], "v2 · roadmap · draft",
           style=ts(27, FRAME, weight=700, family=MONO, spacing=3, transform="uppercase"))
    p.text([MX, 980, SW - 2 * MX, 200], "The output layer\nfor the agent era.",
           style=ts(66, PAPER, weight=700, lh=1.05))
    p.text([MX, 1230, SW - 2 * MX, 200],
           "A forward gap analysis — defensible gaps, explicit scope decisions, and the "
           "next major step: the 2.3 content / presentation split.",
           style=ts(34, MUTE_DK, lh=1.45))
    _footer(p, 1, dark=True)

    # 2 — the bet (paper)
    p = _story(b, "s2-bet")
    _topbar(p, dark=False)
    p.text([MX, 220, SW - 2 * MX, 30], "the bet",
           style=ts(26, FRAME, weight=700, family=MONO, spacing=3, transform="uppercase"))
    p.text([MX, 280, SW - 2 * MX, 360],
           "One substrate for decks and books — with a semantic graph attached.",
           style=ts(72, INK, weight=700, lh=1.06))
    mark(p, MX + 150, 1020, 240, frame=INK, graph=FRAME, node_fill=CANVAS)  # the source→generated fan
    p.text([MX, 1260, SW - 2 * MX, 280],
           "Most tools pick one lane. FrameGraph spans both, strong on typographic, i18n, and "
           "color vocabulary. The models are the source of truth — everything else is generated "
           "from or checked against them, so a document can't silently drift.",
           style=ts(34, MUTE, lh=1.5))
    _footer(p, 2, dark=False)

    # 3 — where the work is (paper)
    p = _story(b, "s3-phases")
    _topbar(p, dark=False)
    p.text([MX, 220, SW - 2 * MX, 30], "roadmap · phases",
           style=ts(26, FRAME, weight=700, family=MONO, spacing=3, transform="uppercase"))
    p.text([MX, 274, SW - 2 * MX, 70], "Where the work is",
           style=ts(58, INK, weight=700, lh=1.02))
    cards = [
        (FRAME, "Phase 1 · defensible gaps",
         "Graph auto-layout for diagrams · accessibility / tagged (PDF-UA) export · "
         "a conformance suite + a tolerance band over the golden-render lock.", 296),
        (CYAN, "Phase 2 · scope decisions",
         "Chart data layer · print color management · geometry / 3D (the SDK already ships) · "
         "book composition API · generative content (resolved once, then pinned).", 340),
        (MUTE, "Phase 3 · conditional",
         "Interaction / animation for presented decks — lowest priority, only if live "
         "presentation becomes a goal.", 280),
    ]
    y = 392
    for accent, kicker, body, h in cards:
        _lcard(p, [MX, y, SW - 2 * MX, h], accent, kicker, "", body)
        y += h + 30
    _footer(p, 3, dark=False)

    # 4 — 2.3 split (paper)
    p = _story(b, "s4-split")
    _topbar(p, dark=False)
    p.text([MX, 220, SW - 2 * MX, 30], "version 2.3 · a",
           style=ts(26, FRAME, weight=700, family=MONO, spacing=3, transform="uppercase"))
    p.text([MX, 274, SW - 2 * MX, 200], "Split content and presentation",
           style=ts(58, INK, weight=700, lh=1.05))
    # two crop-bracketed boxes joined by a mono mapping arrow
    cw = (SW - 2 * MX - 120) / 2
    by = 560
    _lcard(p, [MX, by, cw, 300], CYAN, "content", "",
           "what it says — sections, blocks, figures, reading order")
    _lcard(p, [MX + cw + 120, by, cw, 300], FRAME, "presentation", "",
           "how it looks — style, layout, canvas, paint, transforms")
    p.text([MX + cw + 18, by + 120, 84, 60], "→", style=ts(64, INK, weight=700, family=MONO, align="center"))
    p.text([MX + cw - 4, by + 200, 128, 28], "mapping", style=ts(22, MUTE, family=MONO, align="center"))
    p.text([MX, by + 380, SW - 2 * MX, 280],
           "Bound by a mapping, not co-located fields. The content tree stays the source of "
           "truth; presentation becomes a resolved view — keeping the closed model and the "
           "golden-render determinism the format is built on.",
           style=ts(34, MUTE, lh=1.5))
    _footer(p, 4, dark=False)

    # 5 — 2.3 map: the derivation fan, applied to formats (paper)
    p = _story(b, "s5-map")
    _topbar(p, dark=False)
    p.text([MX, 220, SW - 2 * MX, 30], "version 2.3 · b",
           style=ts(26, FRAME, weight=700, family=MONO, spacing=3, transform="uppercase"))
    p.text([MX, 274, SW - 2 * MX, 70], "Map to many formats",
           style=ts(58, INK, weight=700, lh=1.02))
    # one content node (frame-blue source) fanning to five generated format nodes
    ox, oy = MX + 110, 760
    formats = ["SVG", "PDF", "LaTeX", "HTML", "raster"]
    tx = SW - MX - 320
    for i, label in enumerate(formats):
        ty = oy - 330 + i * 165
        p.line([ox, oy], [tx, ty], stroke=CYAN, stroke_style={"stroke_width": 2})
        p.circle([tx, ty], 12, fill=CANVAS, stroke=INK, stroke_style={"stroke_width": 2.5})
        p.text([tx + 30, ty - 18, 260, 36], label, style=ts(34, INK, weight=600, family=MONO))
    p.circle([ox, oy], 17, fill=FRAME, stroke=FRAME, stroke_style={"stroke_width": 2})
    p.text([ox - 220, oy - 18, 196, 36], "content", style=ts(30, INK, weight=700, family=MONO, align="right"))
    p.text([MX, 1230, SW - 2 * MX, 320],
           "One content tree + a presentation profile → the format-specific artifact, so a "
           "document renders to many targets without re-authoring. Deterministic and verifiable "
           "(same input ⇒ same artifact, golden-locked); an unsupported feature degrades "
           "explicitly — never silently.",
           style=ts(34, MUTE, lh=1.5))
    _footer(p, 5, dark=False)
    return b


# ---------------------------------------------------------------------------- #
#  Print PDF — A4 (595x842 pt)                                                  #
# ---------------------------------------------------------------------------- #
AW, AH = 595, 842
PM = 50


def _a4(b, sid, *, dark=False):
    page = b.page(sid, canvas="A4", coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, AW, AH], fill=INK if dark else PAPER)
    if not dark:
        hairline_grid(page, AW, AH, GRID, step=68)
    crop_marks(page, AW, AH, PAPER if dark else INK, m=26, arm=22, sw=1.6)
    page.layer("body")
    return page


def _a4_top(page, *, dark):
    fg = PAPER if dark else INK
    mark(page, PM + 13, 54, 26, frame=fg, graph=FRAME, node_fill=(INK if dark else CANVAS))
    wordmark(page, PM + 32, 44, 18, frame_color=fg, graph_color=FRAME)
    _in_sync(page, AW - PM, 47, fs=11, mono_w=7)


def _a4_foot(page, n, *, dark):
    page.text([PM, AH - 34, 360, 12], "framegraph v2 · roadmap · draft",
              style=ts(8.5, MUTE_DK if dark else MUTE, family=MONO, spacing=0.5))
    page.text([AW - PM - 60, AH - 34, 60, 12], f"{n:02d} / 03",
              style=ts(8.5, MUTE_DK if dark else MUTE, family=MONO, align="right"))


def _a4_card(page, box, accent, kicker, body):
    x, y, w, h = box
    page.rect([x, y, w, h], radius=8, fill=CANVAS, stroke=GRID, stroke_style={"stroke_width": 1})
    page.rect([x, y, 5, h], fill=accent)
    page.text([x + 18, y + 16, w - 36, 14], kicker,
              style=ts(11, accent, weight=700, family=MONO, spacing=1, transform="uppercase"))
    page.text([x + 18, y + 40, w - 36, h - 52], body, style=ts(10.5, INK, lh=1.5))


def build_pdf() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph v2 — Roadmap (Print)", profile="report", lang="en")

    # 1 — cover (ink)
    p = _a4(b, "p1-cover", dark=True)
    _a4_top(p, dark=True)
    mark(p, AW / 2, 300, 150, frame=PAPER, graph=FRAME, node_fill=INK)
    wordmark(p, PM, 400, 52, frame_color=PAPER, graph_color=FRAME)
    p.text([PM, 470, AW - 2 * PM, 14], "v2 · roadmap · draft",
           style=ts(11, FRAME, weight=700, family=MONO, spacing=2, transform="uppercase"))
    p.text([PM, 496, AW - 2 * PM, 70], "The output layer for the agent era.",
           style=ts(26, PAPER, weight=700, lh=1.1))
    p.text([PM, 580, AW - 2 * PM, 60],
           "A forward gap analysis — defensible gaps, explicit scope decisions, and the 2.3 "
           "content / presentation split. DRAFT / design-target — not commitments.",
           style=ts(11, MUTE_DK, lh=1.55))
    _a4_foot(p, 1, dark=True)

    # 2 — the bet + priority (paper)
    p = _a4(b, "p2-priority", dark=False)
    _a4_top(p, dark=False)
    p.text([PM, 96, AW - 2 * PM, 12], "the bet",
           style=ts(11, FRAME, weight=700, family=MONO, spacing=2, transform="uppercase"))
    p.text([PM, 116, AW - 2 * PM, 48],
           "One substrate spanning decks and books, with a semantic graph attached — uncommon, "
           "and strong on typographic, i18n, and color vocabulary.",
           style=ts(13, INK, lh=1.5))
    p.text([PM, 196, AW - 2 * PM, 12], "priority at a glance",
           style=ts(11, FRAME, weight=700, family=MONO, spacing=2, transform="uppercase"))
    rows = [
        (FRAME, "Phase 1 — defensible gaps",
         "Graph auto-layout for diagrams · accessibility / tagged (PDF-UA) export · conformance "
         "suite + a tolerance band over the golden-render lock."),
        (CYAN, "Phase 2 — scope decisions",
         "Chart data layer · print color management · geometry / 3D authoring (the SDK already "
         "ships) · book composition API · generative content (resolved once, pinned)."),
        (MUTE, "Phase 3 — conditional",
         "Interaction / animation for presented decks — lowest priority unless live presentation "
         "becomes a goal."),
    ]
    y = 224
    for accent, kicker, body in rows:
        _a4_card(p, [PM, y, AW - 2 * PM, 92], accent, kicker, body)
        y += 104
    _a4_foot(p, 2, dark=False)

    # 3 — version 2.3 (paper)
    p = _a4(b, "p3-v23", dark=False)
    _a4_top(p, dark=False)
    p.text([PM, 96, AW - 2 * PM, 12], "the next major step",
           style=ts(11, FRAME, weight=700, family=MONO, spacing=2, transform="uppercase"))
    p.text([PM, 116, AW - 2 * PM, 48], "Version 2.3 — content / presentation split + multi-format mapping",
           style=ts(21, INK, weight=700, lh=1.1))
    blocks = [
        (FRAME, "2.3-A · split content from presentation",
         "A semantic content model (sections, blocks, figures, reading order) — what a document "
         "is — separated from a presentation model (style, layout, canvas, paint). They bind "
         "through a mapping, not co-located fields; content stays the source of truth and "
         "presentation becomes a resolved view, preserving the closed model and golden determinism."),
        (CYAN, "2.3-B · map the rendering to many formats",
         "Promote the existing backend-neutral ScenePainter port (SVG · Chromium raster · "
         "LaTeX/TikZ · HTML) and Document.targets into a first-class mapping layer: one content "
         "tree maps to many formats (SVG, PDF, LaTeX, HTML, raster) without re-authoring. "
         "Deterministic and verifiable; an unsupported feature degrades explicitly, never silently."),
        (MUTE, "open questions",
         "Migration of co-located style via the codemod · where the content / presentation "
         "boundary sits (box and layout intent straddle both) · whether a mapping is data or "
         "code, and how per-target overrides compose without re-introducing co-mingling."),
    ]
    y = 188
    for accent, kicker, body in blocks:
        _a4_card(p, [PM, y, AW - 2 * PM, 150], accent, kicker, body)
        y += 162
    _a4_foot(p, 3, dark=False)
    return b


def build() -> DocumentBuilder:
    return build_stories()


def _write(b, name):
    doc = b.build()
    rep = validate_static_rules(doc)
    errs = [i for i in rep.issues if i.severity == "error"]
    out_dir = os.path.join(ROOT, "out", "roadmap")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"  {name}: {len(doc.pages)} page(s), ok={rep.ok} errors={len(errs)} -> {out}")
    return len(errs)


def main() -> int:
    print("FrameGraph v2 — Roadmap publication")
    e = _write(build_pdf(), "roadmap-print.fg.yaml")
    e += _write(build_stories(), "roadmap-stories.fg.yaml")
    print("Render: tooling/render_pdf.py (PDF) + tooling/render_chromium.py (Story PNGs).")
    return 1 if e else 0


if __name__ == "__main__":
    raise SystemExit(main())
