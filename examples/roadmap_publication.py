#!/usr/bin/env python3
"""Publish the FrameGraph v2 roadmap as two deliverables from one SDK client:

  * a print **PDF** (A4 pages, editorial) — render with tooling/render_pdf.py
  * an **Instagram Stories** set (1080x1920, 9:16) — render with tooling/render_chromium.py

Both lean on the canvas presets: the PDF pages use ``canvas="A4"`` and the story
cards use ``canvas="instagram-story"`` (the social-media preset). Content is a
curated digest of docs/roadmap-draft.md, headlined by the new 2.3 milestone
(content/presentation split + multi-format mapping).

Run from the repo root::

    uv run python examples/roadmap_publication.py            # writes both YAMLs
    uv run --group pdfout python tooling/render_pdf.py out/roadmap/roadmap-print.fg.yaml --out out/roadmap
    uv run --group browser python tooling/render_chromium.py out/roadmap/roadmap-stories.fg.yaml --out out/roadmap
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, linear_gradient, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

SANS = ["Inter", "Helvetica", "Arial", "sans-serif"]


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


# ---------------------------------------------------------------------------- #
#  Instagram Stories — 1080x1920, 9:16, dark + vibrant                          #
# ---------------------------------------------------------------------------- #
INK, INK2 = "#0B1020", "#161C3A"
VIOLET, CYAN, PINK, YELLOW = "#7C5CFF", "#22D3EE", "#FF5E7E", "#FDE047"
WHITE, SUB = "#FFFFFF", "#A6AECF"
ACCENT = linear_gradient([(VIOLET, 0.0), (CYAN, 0.55), (PINK, 1.0)], angle=180)

SW, SH = 1080, 1920
MX = 96  # side margin


def _story(b, sid):
    page = b.page(sid, canvas="instagram-story", coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, SW, SH], fill=INK)
    page.rect([0, 0, 14, SH], fill=ACCENT)          # accent spine
    page.layer("body")
    return page


def _footer(page, n):
    page.rect([MX, SH - 150, SW - 2 * MX, 2], fill="#2A325C")
    page.text([MX, SH - 130, SW - 2 * MX, 30], "FrameGraph v2 · roadmap (draft)",
              style=ts(24, SUB, spacing=1))
    page.text([SW - MX - 120, SH - 130, 120, 30], f"{n} / 5",
              style=ts(24, SUB, align="right"))


def build_stories() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph v2 — Roadmap (Stories)", profile="deck", lang="en")

    # 1 — cover
    p = _story(b, "s1-cover")
    p.text([MX, 300, SW - 2 * MX, 40], "FRAMEGRAPH v2",
           style=ts(32, CYAN, weight=700, spacing=6, transform="uppercase"))
    p.text([MX, 360, SW - 2 * MX, 320], "ROADMAP",
           style=ts(184, WHITE, weight=800, spacing=-4, lh=0.9))
    p.rect([MX, 700, 220, 10], fill=ACCENT)
    p.text([MX, 760, SW - 2 * MX, 200],
           "Where FrameGraph is going — defensible gaps, scope decisions, and the next major split.",
           style=ts(40, SUB, lh=1.4))
    p.text([MX, 1080, SW - 2 * MX, 40], "DRAFT · design-target — not commitments",
           style=ts(28, YELLOW, weight=700, spacing=2, transform="uppercase"))
    _footer(p, 1)

    # 2 — the bet
    p = _story(b, "s2-bet")
    p.text([MX, 300, SW - 2 * MX, 40], "THE BET",
           style=ts(32, CYAN, weight=700, spacing=6, transform="uppercase"))
    p.text([MX, 380, SW - 2 * MX, 600],
           "One substrate for decks and books — with a semantic graph attached.",
           style=ts(76, WHITE, weight=800, lh=1.05))
    p.text([MX, 980, SW - 2 * MX, 260],
           "Most tools pick one lane. FrameGraph spans both, and is strong on typographic, "
           "i18n, and color vocabulary. The models are the source of truth; everything else is "
           "generated from or checked against them.",
           style=ts(38, SUB, lh=1.45))
    _footer(p, 2)

    # 3 — where the work is
    p = _story(b, "s3-phases")
    p.text([MX, 280, SW - 2 * MX, 40], "WHERE THE WORK IS",
           style=ts(32, CYAN, weight=700, spacing=6, transform="uppercase"))
    phases = [
        ("PHASE 1 · defensible gaps", VIOLET,
         "Graph auto-layout for diagrams · accessibility / tagged export · "
         "conformance suite + golden-render tolerance."),
        ("PHASE 2 · scope decisions", CYAN,
         "Chart data layer · print color management · geometry / 3D (SDK already ships) · "
         "book composition API · generative content (resolved once, pinned)."),
        ("PHASE 3 · conditional", PINK,
         "Interaction / animation — only if live presentation becomes a goal."),
    ]
    y = 360
    for label, col, body in phases:
        h = 380 if "Phase 2" in label or "PHASE 2" in label else 300
        p.rect([MX, y, SW - 2 * MX, h], radius=28, fill=INK2)
        p.rect([MX, y, 10, h], fill=col)
        p.text([MX + 44, y + 40, SW - 2 * MX - 88, 40], label,
                style=ts(34, col, weight=800, spacing=1, transform="uppercase"))
        p.text([MX + 44, y + 100, SW - 2 * MX - 88, h - 120], body,
                style=ts(34, WHITE, lh=1.4))
        y += h + 34
    _footer(p, 3)

    # 4 — 2.3 split content/presentation
    p = _story(b, "s4-split")
    p.text([MX, 280, 360, 200], "2.3", style=ts(150, CYAN, weight=800, lh=0.9))
    p.text([MX, 470, SW - 2 * MX, 240], "Split content\nand presentation",
           style=ts(78, WHITE, weight=800, lh=1.02))
    # content | presentation diagram
    cw = (SW - 2 * MX - 40) / 2
    ch = 320
    p.rect([MX, 760, cw, ch], radius=24, fill=INK2)
    p.rect([MX, 760, cw, 8], fill=CYAN)
    p.text([MX + 32, 800, cw - 64, 40], "CONTENT", style=ts(30, CYAN, weight=800, spacing=2))
    p.text([MX + 32, 856, cw - 64, ch - 116], "what it says — sections, blocks, figures, reading order",
           style=ts(30, SUB, lh=1.35))
    p.rect([MX + cw + 40, 760, cw, ch], radius=24, fill=INK2)
    p.rect([MX + cw + 40, 760, cw, 8], fill=PINK)
    p.text([MX + cw + 72, 800, cw - 64, 40], "PRESENTATION", style=ts(30, PINK, weight=800, spacing=2))
    p.text([MX + cw + 72, 856, cw - 64, ch - 116], "how it looks — style, layout, canvas, paint, transforms",
           style=ts(30, SUB, lh=1.35))
    p.text([MX, 760 + ch + 60, SW - 2 * MX, 300],
           "Bound by a mapping, not co-located fields. The content tree stays the source of truth; "
           "presentation becomes a resolved view — keeping the closed model and golden determinism.",
           style=ts(36, SUB, lh=1.45))
    _footer(p, 4)

    # 5 — 2.3 map to many formats
    p = _story(b, "s5-map")
    p.text([MX, 280, 360, 200], "2.3", style=ts(150, CYAN, weight=800, lh=0.9))
    p.text([MX, 470, SW - 2 * MX, 240], "Map to many\nformats",
           style=ts(78, WHITE, weight=800, lh=1.02))
    chips = ["SVG", "PDF", "LaTeX", "HTML", "raster"]
    x = MX
    for c in chips:
        w = 52 + len(c) * 22
        p.rect([x, 760, w, 70], radius=35, fill=INK2, stroke=CYAN, stroke_style={"stroke_width": 2})
        p.text([x, 776, w, 40], c, style=ts(30, WHITE, weight=700, align="center"))
        x += w + 18
    p.text([MX, 920, SW - 2 * MX, 620],
           "One content tree + a presentation profile → the format-specific artifact, so a document "
           "renders to many targets without re-authoring. Deterministic and verifiable (same input ⇒ "
           "same artifact, golden-locked); an unsupported feature degrades explicitly — never silently.",
           style=ts(38, SUB, lh=1.5))
    _footer(p, 5)
    return b


# ---------------------------------------------------------------------------- #
#  Print PDF — A4 (595x842 pt), editorial light                                 #
# ---------------------------------------------------------------------------- #
PAPER, PINK_INK = "#FFFFFF", "#0F172A"
BLUE, MUTE, LINE, FAINT = "#2563EB", "#64748B", "#E2E8F0", "#F1F5F9"
AW, AH = 595, 842
PM = 56  # page margin


def _a4(b, sid):
    page = b.page(sid, canvas="A4", coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, AW, AH], fill=PAPER)
    page.rect([0, 0, 8, AH], fill=BLUE)
    page.layer("body")
    return page


def _running(page, n):
    page.text([PM, AH - 36, AW - 2 * PM, 12], "FrameGraph v2 · Roadmap (draft) · 2026",
              style=ts(8.5, MUTE, spacing=0.5))
    page.text([AW - PM - 60, AH - 36, 60, 12], f"{n}", style=ts(8.5, MUTE, align="right"))


def build_pdf() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph v2 — Roadmap (Print)", profile="report", lang="en")

    # Page 1 — cover
    p = _a4(b, "p1-cover")
    p.text([PM, 150, AW - 2 * PM, 16], "FRAMEGRAPH v2 · ROADMAP",
           style=ts(11, BLUE, weight=700, spacing=3, transform="uppercase"))
    p.text([PM, 188, AW - 2 * PM, 90], "The Roadmap",
           style=ts(46, PINK_INK, weight=800, spacing=-1, lh=1.0))
    p.rect([PM, 290, 90, 5], fill=BLUE)
    p.text([PM, 320, AW - 2 * PM, 120],
           "A forward gap analysis for FrameGraph v2 — defensible gaps, explicit scope decisions, "
           "and the 2.3 milestone that splits content from presentation.",
           style=ts(13, MUTE, lh=1.55))
    p.rect([PM, 470, AW - 2 * PM, 1], fill=LINE)
    p.text([PM, 486, AW - 2 * PM, 16], "DRAFT / design-target — not commitments",
           style=ts(10, "#B45309", weight=700, spacing=1, transform="uppercase"))
    p.text([PM, 512, AW - 2 * PM, 40],
           "The models (models/framegraph.py, HEAD 2.2.0) are the source of truth; this document is "
           "a direction, not a delivery plan.",
           style=ts(10.5, MUTE, lh=1.5))
    _running(p, 1)

    # Page 2 — the bet + priority at a glance
    p = _a4(b, "p2-priority")
    p.text([PM, 64, AW - 2 * PM, 16], "THE BET",
           style=ts(11, BLUE, weight=700, spacing=2, transform="uppercase"))
    p.text([PM, 88, AW - 2 * PM, 60],
           "One substrate spanning decks and books, with a semantic graph attached — uncommon, and "
           "strong on typographic, i18n, and color vocabulary.",
           style=ts(13, PINK_INK, lh=1.5))
    p.text([PM, 168, AW - 2 * PM, 16], "PRIORITY AT A GLANCE",
           style=ts(11, BLUE, weight=700, spacing=2, transform="uppercase"))
    rows = [
        ("Phase 1 — defensible gaps", BLUE,
         "Graph auto-layout for diagrams · accessibility / tagged (PDF-UA) export · "
         "conformance suite + a tolerance band over the golden-render lock."),
        ("Phase 2 — scope decisions", "#7C3AED",
         "Chart data layer · print color management · geometry / transformed-spaces / 3D authoring "
         "(the SDK already ships) · book composition API · generative content (resolved once, pinned)."),
        ("Phase 3 — conditional", MUTE,
         "Interaction / animation for presented decks — lowest priority unless live presentation "
         "becomes a goal."),
    ]
    y = 196
    for label, col, body in rows:
        p.rect([PM, y, AW - 2 * PM, 96], radius=8, fill=FAINT)
        p.rect([PM, y, 5, 96], fill=col)
        p.text([PM + 18, y + 16, AW - 2 * PM - 36, 18], label,
                style=ts(13, col, weight=800))
        p.text([PM + 18, y + 42, AW - 2 * PM - 36, 48], body, style=ts(10.5, PINK_INK, lh=1.5))
        y += 112
    _running(p, 2)

    # Page 3 — version 2.3
    p = _a4(b, "p3-v23")
    p.text([PM, 64, AW - 2 * PM, 16], "THE NEXT MAJOR STEP",
           style=ts(11, BLUE, weight=700, spacing=2, transform="uppercase"))
    p.text([PM, 88, AW - 2 * PM, 60], "Version 2.3 — content / presentation split + multi-format mapping",
           style=ts(22, PINK_INK, weight=800, lh=1.1))
    blocks = [
        ("2.3-A · Split content from presentation",
         "A semantic content model (sections, blocks, figures, reading order) — what a document is — "
         "separated from a presentation model (style, layout, canvas, paint) — how it is realized. "
         "They bind through a mapping, not co-located fields; content stays the source of truth and "
         "presentation becomes a resolved view, preserving the closed model and golden determinism."),
        ("2.3-B · Map the rendering to many formats",
         "Promote the existing backend-neutral ScenePainter port (SVG · Chromium raster · LaTeX/TikZ · "
         "HTML) and Document.targets into a first-class mapping layer: one content tree maps to many "
         "formats (SVG, PDF, LaTeX, HTML, raster) without re-authoring. Deterministic and verifiable; "
         "a target that cannot represent a feature degrades explicitly, never silently."),
        ("Open questions",
         "Migration of co-located style via the codemod · where the content/presentation boundary sits "
         "(box and layout intent straddle both) · whether a mapping is data or code, and how per-target "
         "overrides compose without re-introducing co-mingling."),
    ]
    y = 168
    for label, body in blocks:
        p.text([PM, y, AW - 2 * PM, 16], label, style=ts(13, BLUE, weight=800))
        p.text([PM, y + 22, AW - 2 * PM, 130], body, style=ts(10.5, PINK_INK, lh=1.55))
        y += 168
    _running(p, 3)
    return b


# The MCP renders whatever build() returns; default to the visual deliverable.
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
