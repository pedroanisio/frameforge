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

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, os.path.join(ROOT, "static", "examples"))   # for the canonical logo
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


PROG_N = 7   # number of story cards (drives the segmented progress bar)


def _ig(b, sid):
    """One Instagram-story canvas (1080x1920) — dark, full-bleed, immersive. No
    drafting-table chrome (hairline grid / crop-marks / page numbers): a story is
    *output*, designed for the channel, not a print document auto-scaled to 9:16.
    The brand stays FLAT — energy comes from a dark ground, electric blue/cyan, and
    scale, never gradients."""
    page = b.page(sid, canvas="instagram-story", coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, SW, SH], fill=INK)
    page.layer("body")
    return page


def _progress(page, idx):
    """The segmented progress bar — Instagram Stories' signature top chrome. Segments
    up to ``idx`` (0-based) read as watched; the rest sit faint behind."""
    gap, top, h = 11, 52, 7
    seg = (SW - 2 * MX - (PROG_N - 1) * gap) / PROG_N
    for i in range(PROG_N):
        x = MX + i * (seg + gap)
        page.rect([x, top, seg, h], radius=h / 2, fill=PAPER if i <= idx else GRID_DK)


def _handle(page):
    """The story header: the mark as a profile avatar + the @handle — reads as a real
    Instagram account, not a slide footer."""
    mark(page, MX + 20, 124, 40, frame=PAPER, graph=CYAN, node_fill=INK)
    page.text([MX + 54, 102, 600, 36], "@framegraph", style=ts(31, PAPER, weight=700))
    page.text([MX + 54, 142, 600, 26], "FrameGraph v2 · roadmap",
              style=ts(22, MUTE_DK, family=MONO, spacing=1))


def _dogfoot(page):
    """A quiet watermark on every card: this artifact *is* FrameGraph output."""
    page.text([MX, SH - 96, SW - 2 * MX, 28],
              "made with FrameGraph — this story is a .fg document",
              style=ts(21, MUTE_DK, family=MONO, align="center", spacing=1))


def _chrome(page, idx):
    _progress(page, idx)
    _handle(page)
    _dogfoot(page)


def _fan(page, ox, oy, source_label, targets, *, span=620):
    """The derivation fan (the brand mark, applied) on the dark story ground: one
    filled blue source node fanning via cyan edges to N hollow target nodes (ink
    fill, paper stroke) with paper mono labels."""
    n = len(targets)
    tx = SW - MX - 330
    for i, label in enumerate(targets):
        ty = oy + (i * span / (n - 1) - span / 2 if n > 1 else 0)
        page.line([ox, oy], [tx, ty], stroke=CYAN, stroke_style={"stroke_width": 2.5})
        page.circle([tx, ty], 13, fill=INK, stroke=PAPER, stroke_style={"stroke_width": 2.5})
        page.text([tx + 32, ty - 20, 320, 40], label, style=ts(34, PAPER, weight=600, family=MONO))
    page.circle([ox, oy], 18, fill=FRAME, stroke=FRAME, stroke_style={"stroke_width": 2})
    page.text([ox - 250, oy - 20, 224, 40], source_label,
              style=ts(30, PAPER, weight=700, family=MONO, align="right"))


def _kicker(page, idx, text):
    """The story title block: IG chrome + a mono eyebrow + the big headline area
    start. Returns nothing; headline is drawn by the caller under y≈300."""
    _chrome(page, idx)
    page.text([MX, 232, SW - 2 * MX, 34], text,
              style=ts(28, CYAN, weight=700, family=MONO, spacing=3, transform="uppercase"))


def _head(page, y, text, *, size=64, color=PAPER):
    """A big single-colour story headline. The renderer ignores '\\n' and breaks lines
    only by width, so to control the break each line is emitted as its *own* text
    object stacked downward from ``y`` (advance = size · 1.06). Colour is set at the
    block level (per-span colour only resolves on a single line with no block colour —
    see ``_runs``)."""
    adv = size * 1.06
    for i, line in enumerate(text.split("\n")):
        page.add({"type": "text", "box": [MX, y + i * adv, SW - 2 * MX, int(size * 1.3)],
                  "spans": [{"text": line}],
                  "style": {"font_family": SANS, "font_size": size, "font_weight": 700,
                            "line_height": 1.05, "color": color}})


def _runs(page, y, runs, *, size):
    """One headline line with multiple coloured runs. Per-span colour resolves only on
    a single line with no block-level colour (the wordmark pattern), so a multi-colour
    headline stacks one ``_runs`` call per line. ``runs`` is a list of (text, colour)."""
    page.add({"type": "text", "box": [MX, y, SW - 2 * MX, int(size * 1.3)],
              "spans": [{"text": t, "style": {"color": c}} for t, c in runs],
              "style": {"font_family": SANS, "font_size": size, "font_weight": 700,
                        "line_height": 1.05}})


def build_stories() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph v2 — Roadmap (Stories)", profile="deck", lang="en")
    HEAD, BODY = 64, 40        # card headline / body sizes (big + punchy)
    CW = SW - 2 * MX

    # 1 — cover: the mark, hero, on dark
    p = _ig(b, "s1-cover")
    _chrome(p, 0)
    mark(p, SW / 2, 620, 320, frame=PAPER, graph=FRAME, node_fill=INK)   # the canonical mark, hero
    wordmark(p, MX, 884, 112, frame_color=PAPER, graph_color=FRAME)
    p.text([MX, 1034, CW, 34], "v2 · roadmap · draft",
           style=ts(29, CYAN, weight=700, family=MONO, spacing=4, transform="uppercase"))
    _head(p, 1108, "The output layer\nfor the agent era.", size=80)

    # 2 — the bet (color-keyed headline)
    p = _ig(b, "s2-bet")
    _kicker(p, 1, "the bet")
    _head(p, 320, "One substrate.", size=80)
    _runs(p, 412, [("Decks", CYAN), (" and ", PAPER), ("books", FRAME), (".", PAPER)], size=80)
    _head(p, 504, "One semantic graph.", size=80)
    p.text([MX, 780, CW, 360],
           "Most tools pick one lane. FrameGraph spans both — and the models are the "
           "source of truth, so every artifact is generated from or checked against "
           "them. A document can't silently drift.",
           style=ts(BODY, MUTE_DK, lh=1.5))

    # 3 — where the work is (big numbered rows)
    p = _ig(b, "s3-phases")
    _kicker(p, 2, "the work")
    _head(p, 296, "Where the work is", size=HEAD)
    rows = [
        ("01", FRAME, "Defensible gaps", "graph auto-layout · a11y / PDF-UA · conformance lock"),
        ("02", CYAN, "Scope decisions", "chart data · print color · 3D · book API · generative"),
        ("03", MUTE_DK, "Conditional", "interaction / animation — only if live decks land"),
    ]
    y = 520
    for num, col, label, sub in rows:
        p.text([MX, y - 14, 200, 130], num, style=ts(116, col, weight=700, family=MONO))
        p.text([MX + 210, y, CW - 210, 60], label, style=ts(50, PAPER, weight=700))
        p.text([MX + 210, y + 70, CW - 210, 132], sub, style=ts(34, MUTE_DK, lh=1.36))
        y += 300

    # 4 — 2.3-A: split content from presentation
    p = _ig(b, "s4-split")
    _kicker(p, 3, "version 2.3 · a")
    _head(p, 296, "Split content\n& presentation", size=HEAD)
    ny = 680
    lcx, rcx = MX + 150, SW - MX - 150
    p.circle([lcx, ny], 26, fill=CYAN, stroke=CYAN, stroke_style={"stroke_width": 2})
    p.circle([rcx, ny], 26, fill=INK, stroke=FRAME, stroke_style={"stroke_width": 4})
    p.line([lcx + 60, ny], [rcx - 60, ny], stroke=PAPER, stroke_style={"stroke_width": 2.5})
    p.text([(lcx + rcx) / 2 - 80, ny - 64, 160, 40], "maps", style=ts(28, MUTE_DK, family=MONO, align="center"))
    p.text([lcx - 150, ny + 52, 300, 44], "content", style=ts(36, PAPER, weight=700, align="center"))
    p.text([lcx - 150, ny + 104, 300, 34], "what it says", style=ts(28, MUTE_DK, align="center"))
    p.text([rcx - 150, ny + 52, 300, 44], "presentation", style=ts(36, PAPER, weight=700, align="center"))
    p.text([rcx - 150, ny + 104, 300, 34], "how it looks", style=ts(28, MUTE_DK, align="center"))
    p.text([MX, 1000, CW, 360],
           "Bound by a mapping, not co-located fields — the content tree stays the "
           "source of truth, presentation becomes a resolved view. The closed model "
           "and golden-render determinism hold.",
           style=ts(BODY, MUTE_DK, lh=1.5))

    # 5 — 2.3-B: retarget one content tree to any surface
    p = _ig(b, "s5-retarget")
    _kicker(p, 4, "version 2.3 · b")
    _head(p, 296, "Retarget to\nany surface", size=HEAD)
    _fan(p, MX + 110, 880, "content", ["IG story", "IG post", "A4 print", "YouTube", "LinkedIn"])
    p.text([MX, 1300, CW, 420],
           "One content tree + a canvas preset → the surface-specific artifact, no "
           "re-authoring. The social presets already ship — instagram-story, "
           "youtube-banner, tiktok, linkedin — synced across the model, grammar, "
           "spec and renderer.",
           style=ts(BODY, MUTE_DK, lh=1.5))

    # 6 — 3.0: one source derives every artifact via select / filter
    p = _ig(b, "s6-source")
    _kicker(p, 5, "version 3.0")
    _head(p, 296, "One source,\nevery audience", size=HEAD)
    _fan(p, MX + 130, 880, "Q3 results",
         ["SEC filing", "investor deck", "IG story", "LinkedIn", "press post"])
    p.text([MX, 1300, CW, 420],
           "One source derives every artifact: the same quarterly numbers become the "
           "SEC / investor report and the media posts — via filters / selects, each "
           "retargeted to its surface. The filing and the IG story can't disagree.",
           style=ts(BODY, MUTE_DK, lh=1.5))

    # 7 — dogfooding: this whole thing is FrameGraph output
    p = _ig(b, "s7-proof")
    _kicker(p, 6, "made with framegraph")
    _head(p, 320, "You're reading", size=78)
    _runs(p, 410, [("FrameGraph", FRAME), (" output.", PAPER)], size=78)
    _fan(p, MX + 90, 940, "one .fg", ["this story", "the A4 PDF"], span=300)
    p.text([MX, 1260, CW, 320],
           "This Instagram story and the 4-page print PDF are one FrameGraph "
           "document, rendered by the SDK — no Figma, no InDesign. Decks, books, "
           "social: one substrate, generated and verified.",
           style=ts(BODY, MUTE_DK, lh=1.5))
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
    page.text([AW - PM - 60, AH - 34, 60, 12], f"{n:02d} / 04",
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
    p.text([PM, 690, AW - 2 * PM, 40],
           "Dogfooded — every page of this PDF, and the companion Instagram story, is one "
           "FrameGraph document rendered by the SDK. No Figma, no InDesign.",
           style=ts(10, CYAN, lh=1.6, family=MONO))
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
    p.text([PM, 116, AW - 2 * PM, 48], "Version 2.3 — split content from presentation + retarget to any surface",
           style=ts(21, INK, weight=700, lh=1.1))
    blocks = [
        (FRAME, "2.3-A · split content from presentation",
         "A semantic content model (sections, blocks, figures, reading order) — what a document "
         "is — separated from a presentation model (style, layout, canvas, paint). They bind "
         "through a mapping, not co-located fields; content stays the source of truth and "
         "presentation becomes a resolved view, preserving the closed model and golden determinism."),
        (CYAN, "2.3-B · retarget one content tree to any canvas / surface",
         "The same content maps to many surfaces — social-media formats (Instagram story/post, "
         "LinkedIn, YouTube, TikTok), print (A4, Letter), and screen — by pairing it with a canvas "
         "preset + profile. The social-media presets already ship (instagram-story 1080×1920, "
         "youtube-banner, …), synced across model / grammar / spec / CanvasResolver; 2.3 makes the "
         "retarget first-class. Output formats (SVG · PDF · LaTeX · HTML · raster) are the "
         "orthogonal axis the same mapping drives."),
    ]
    y = 196
    for accent, kicker, body in blocks:
        _a4_card(p, [PM, y, AW - 2 * PM, 212], accent, kicker, body)
        y += 232
    _a4_foot(p, 3, dark=False)

    # 4 — version 3.0 (paper)
    p = _a4(b, "p4-v30", dark=False)
    _a4_top(p, dark=False)
    p.text([PM, 96, AW - 2 * PM, 12], "the deeper payoff",
           style=ts(11, FRAME, weight=700, family=MONO, spacing=2, transform="uppercase"))
    p.text([PM, 116, AW - 2 * PM, 48], "Version 3.0 — derive every artifact from one source (select + filter)",
           style=ts(21, INK, weight=700, lh=1.1))
    blocks2 = [
        (FRAME, "one source, every audience",
         "The 2.3 split makes the payoff possible: the same quarterly results render as the formal "
         "SEC / investor report (A4, full tables) AND the media posts (an Instagram story, a "
         "LinkedIn card) — derived from the same numbers via filters / selects, each selecting the "
         "subset its audience needs and retargeting (2.3) to its surface, never re-keyed by hand."),
        (CYAN, "a view = select + surface",
         "A declared view — a select / filter over the content graph, bound to a target surface + "
         "profile — produces one audience artifact; many views over one source produce the full set "
         "(filing, deck, story, post). One source of numbers: a figure that changes once propagates "
         "everywhere, so the SEC table and the Instagram story can never disagree."),
        (MUTE, "new surface area vs. 2.3",
         "2.3 retargets one whole document to many canvases; 3.0 adds the selection layer (which "
         "slice each artifact shows) — a query / view model over the content graph, not a canvas "
         "swap. Deterministic and verifiable (golden-locked); a view selecting an element a surface "
         "cannot represent degrades explicitly, never silently."),
    ]
    y = 188
    for accent, kicker, body in blocks2:
        _a4_card(p, [PM, y, AW - 2 * PM, 150], accent, kicker, body)
        y += 162
    _a4_foot(p, 4, dark=False)
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
