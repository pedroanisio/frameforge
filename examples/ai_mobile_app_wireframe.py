#!/usr/bin/env python3
"""Compose a COMPLETE low-fidelity wireframe of an advanced AI mobile app with
the FrameGraph Python SDK.

The document is one multi-page deck. Page 1 is a flow-map overview (six device
thumbnails wired together by the primary user journey); pages 2-7 are full
390x844 phone screens drawn in classic wireframe language — grey placeholder
fills, dashed device chrome, bar-stand-ins for copy, and dotted annotation
call-outs down the right rail.

Screens
  1. Onboarding / Welcome      — assistant orb, wordmark, sign-in CTAs
  2. Assistant Home            — ask bar, model chip, quick actions, recents, tab bar
  3. Conversation             — message thread, tool-call card, composer
  4. Voice / Live mode         — reactive orb, live caption, call controls
  5. Discover (agents & tools) — featured agent, category chips, agent grid
  6. Settings                  — profile, model, personalization, privacy

Everything is built through the SDK: DocumentBuilder + PageBuilder primitives,
the layout helpers (row / column / grid / inset), define_color / define_text_style,
then validate_static_rules and serialize().

Run from the repository root::

    uv run python examples/ai_mobile_app_wireframe.py   # build, validate, write the fixture
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    PageBuilder,
    column,
    grid,
    inset,
    row,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# ---- device + palette ----------------------------------------------------- #
W, H = 390, 844                       # iPhone-class logical points
M = 20                                # screen side margin
CANVAS = {"size": [W, H], "units": "px"}

COLORS = {
    "paper":  "#FFFFFF",   # screen background
    "ink":    "#1D2430",   # primary "text" tone (used for heavy bars / labels)
    "fill":   "#ECEEF2",   # neutral placeholder fill
    "fill2":  "#E0E4EA",   # secondary placeholder fill
    "line":   "#C7CDD7",   # wireframe stroke / dashes
    "bar":    "#C2C8D2",   # text-line stand-in
    "barlt":  "#D8DCE3",   # lighter text-line stand-in
    "muted":  "#8A93A3",   # annotation + caption tone
    "accent": "#5B5BD6",   # single accent: AI / primary actions
    "accsft": "#E5E5FB",   # accent wash
    "stage":  "#F4F6F9",   # canvas behind the overview thumbnails
}

SANS = ["Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["SFMono-Regular", "Menlo", "monospace"]

STYLES = {
    "deckTitle": dict(font_family=SANS, font_size=34, font_weight=800, color="ink",
                      letter_spacing=-1),
    "deckSub":   dict(font_family=SANS, font_size=15, color="muted", line_height=1.5),
    "thumbCap":  dict(font_family=SANS, font_size=13, font_weight=700, color="ink"),
    "thumbNo":   dict(font_family=MONO, font_size=11, font_weight=700, color="accent"),
    "flowNote":  dict(font_family=MONO, font_size=11, color="muted", letter_spacing=0.5),

    "status":    dict(font_family=SANS, font_size=12, font_weight=700, color="ink"),
    "screenH":   dict(font_family=SANS, font_size=20, font_weight=800, color="ink",
                      letter_spacing=-0.4),
    "h":         dict(font_family=SANS, font_size=14, font_weight=700, color="ink"),
    "lbl":       dict(font_family=SANS, font_size=12, font_weight=600, color="muted"),
    "btn":       dict(font_family=SANS, font_size=14, font_weight=700, color="paper",
                      align="center"),
    "btnGhost":  dict(font_family=SANS, font_size=14, font_weight=700, color="ink",
                      align="center"),
    "chip":      dict(font_family=SANS, font_size=12, font_weight=600, color="ink"),
    "chipA":     dict(font_family=SANS, font_size=12, font_weight=700, color="accent"),
    "place":     dict(font_family=SANS, font_size=13, color="muted"),
    "glyph":     dict(font_family=SANS, font_size=16, font_weight=700, color="muted",
                      align="center"),
    "glyphA":    dict(font_family=SANS, font_size=18, font_weight=800, color="paper",
                      align="center"),
    "tab":       dict(font_family=SANS, font_size=10, font_weight=600, color="muted",
                      align="center"),
    "wordmark":  dict(font_family=SANS, font_size=30, font_weight=800, color="ink",
                      letter_spacing=-0.5, align="center"),
    "caption":   dict(font_family=SANS, font_size=14, color="ink", align="center"),
    "annot":     dict(font_family=MONO, font_size=10, color="muted", line_height=1.45),
    "badge":     dict(font_family=MONO, font_size=11, font_weight=700, color="muted"),
}

DASH = {"stroke_width": 1.2, "stroke_dasharray": [4, 3]}
HAIR = {"stroke_width": 1.0}


# ---- small wireframe vocabulary ------------------------------------------- #
def bars(page: PageBuilder, box, n=3, gap=9, h=8, last=0.6, color="bar", radius=4):
    """Stack of rounded bars standing in for n lines of copy."""
    x, y, w, _ = box
    cy = y
    for i in range(n):
        bw = w * (last if i == n - 1 else 1.0)
        page.rect([x, cy, bw, h], fill=color, radius=radius)
        cy += h + gap


def ghost(page: PageBuilder, box, radius=10, label=None, fill="fill"):
    """Dashed placeholder region with an optional centered glyph/label."""
    page.rect(box, fill=fill, stroke="line", stroke_style=DASH, radius=radius)
    if label is not None:
        x, y, w, h = box
        page.text([x, y + h / 2 - 9, w, 18], label, style="glyph")


def pill(page: PageBuilder, box, text=None, *, fill="fill", style="chip",
         stroke=None, radius=None):
    x, y, w, h = box
    r = radius if radius is not None else h / 2
    kw = {"fill": fill, "radius": r}
    if stroke:
        kw["stroke"] = stroke
        kw["stroke_style"] = HAIR
    page.rect(box, **kw)
    if text is not None:
        page.text([x + 12, y + h / 2 - 8, w - 24, 16], text, style=style)


def circle(page: PageBuilder, cx, cy, r, *, fill="fill", stroke=None, dash=False):
    kw = {"fill": fill, "radius": r}
    if stroke:
        kw["stroke"] = stroke
        kw["stroke_style"] = DASH if dash else HAIR
    page.rect([cx - r, cy - r, 2 * r, 2 * r], **kw)


def icon(page: PageBuilder, box, glyph="▢", *, fill="fill2", style="glyph", radius=9):
    x, y, w, h = box
    page.rect(box, fill=fill, radius=radius)
    page.text([x, y + h / 2 - 9, w, 18], glyph, style=style)


def annotate(page: PageBuilder, x, y, text, *, lead_to=None):
    """Dotted annotation tick + mono note in the right rail."""
    page.text([x, y, W - x - 8, 40], text, style="annot")
    if lead_to is not None:
        page.line([x - 6, y + 6], lead_to, stroke="line", stroke_style=DASH)


def screen(b: DocumentBuilder, sid, *, title=None, dark=False) -> PageBuilder:
    """A phone screen: paper, dashed device frame, status bar, home indicator."""
    page = b.page(sid, canvas=CANVAS, coordinate_mode="absolute").layer("frame")
    page.rect([0, 0, W, H], fill="stage" if dark else "paper")
    page.rect([0, 0, W, H], fill="none", stroke="line", stroke_style=HAIR, radius=2)
    # status bar
    page.text([M, 16, 60, 16], "9:41", style="status")
    page.rect([W - 64, 20, 16, 9], fill="bar", radius=2)          # signal
    page.rect([W - 44, 20, 14, 9], fill="bar", radius=2)          # wifi
    page.rect([W - 26, 19, 18, 10], fill="ink", radius=2)         # battery
    # home indicator
    page.rect([W / 2 - 60, H - 10, 120, 4], fill="line", radius=2)
    page.layer("main")
    if title is not None:
        page.text([M, 56, W - 2 * M, 26], title, style="screenH")
    return page


def appbar(page: PageBuilder, *, back=False, title=None, right=("⋯",), y=52):
    if back:
        icon(page, [M, y, 32, 32], "‹", radius=9)
    if title is not None:
        tx = M + 44 if back else M
        page.text([tx, y + 6, 200, 20], title, style="h")
    rx = W - M - 32
    for g in right:
        icon(page, [rx, y, 32, 32], g, radius=9)
        rx -= 40


def tabbar(page: PageBuilder, active=0):
    page.rect([0, H - 78, W, 78], fill="paper")
    page.rect([0, H - 78, W, 1], fill="line")
    tabs = ["Home", "Discover", "", "Library", "Profile"]
    cols = row([0, H - 70, W, 46], count=5)
    for i, (c, name) in enumerate(zip(cols, tabs)):
        cx = c[0] + c[2] / 2
        if i == 2:  # center voice FAB
            circle(page, cx, H - 64, 26, fill="accent")
            page.text([cx - 26, H - 73, 52, 20], "◉", style="glyphA")
            page.text([cx - 26, H - 30, 52, 12], "Voice", style="tab")
            continue
        col = "accent" if i == active else "muted"
        page.rect([cx - 9, H - 64, 18, 14], fill=col, radius=3)
        page.text([c[0], H - 42, c[2], 12], name, style="tab")


# ===========================================================================
# Page 1 — overview / flow map
# ===========================================================================
def overview(b: DocumentBuilder) -> None:
    OW, OH = 1440, 1040
    page = b.page("overview", canvas={"size": [OW, OH], "units": "px"},
                  coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, OW, OH], fill="stage")
    page.rect([0, 0, OW, 10], fill="accent")

    page.layer("head")
    page.text([64, 56, 1000, 44], "Aura AI — Advanced Assistant", style="deckTitle")
    page.text([64, 104, 1040, 48],
              "Complete mobile wireframe · 6 screens · low-fidelity flow map. "
              "Built end-to-end with the FrameGraph SDK and rendered to SVG.",
              style="deckSub")
    pill(page, [64, 162, 150, 26], "v0.1 · WIREFRAME", fill="accsft", style="chipA")
    pill(page, [222, 162, 120, 26], "390 × 844", fill="fill", style="chip")

    page.layer("thumbs")
    screens = [
        ("01", "Onboarding"), ("02", "Home"), ("03", "Conversation"),
        ("04", "Voice / Live"), ("05", "Discover"), ("06", "Settings"),
    ]
    cells = grid([64, 236, OW - 128, 740], cols=3, rows=2, gap=40, row_gap=64)
    centers = []
    for (no, name), cell in zip(screens, cells):
        cx, cy, cw, ch = cell
        fw, fh = 176, 320                       # mini device
        fx, fy = cx + (cw - fw) / 2, cy
        ip = 16                                 # device inner padding
        iw = fw - 2 * ip
        centers.append((fx + fw / 2, fy + fh / 2, fx, fy, fw, fh))
        page.rect([fx, fy, fw, fh], fill="paper", stroke="line",
                  stroke_style=HAIR, radius=20)
        page.rect([fx + fw / 2 - 24, fy + 11, 48, 7], fill="fill2", radius=4)  # notch
        # schematic content per thumbnail
        page.rect([fx + ip, fy + 34, iw, 20], fill="fill", radius=6)
        bars(page, [fx + ip, fy + 66, iw, 0], n=3, gap=10, h=8,
             last=0.5, color="barlt")
        page.rect([fx + ip, fy + 122, iw, 96], fill="fill", radius=10)
        bars(page, [fx + ip, fy + 232, iw, 0], n=2, gap=10, h=8,
             last=0.7, color="barlt")
        page.rect([fx + ip, fy + fh - 34, iw, 22], fill="fill2", radius=8)
        # caption
        page.text([fx, fy + fh + 16, 30, 16], f"{no}", style="thumbNo")
        page.text([fx + 30, fy + fh + 14, fw, 18], name, style="thumbCap")

    # flow arrows along the journey 1→2→3, 2→4, 2→5, 2→6
    def arrow(a, bpt, label=None):
        page.line(list(a), list(bpt), stroke="accent", stroke_style={"stroke_width": 1.6})
        page.rect([bpt[0] - 4, bpt[1] - 4, 8, 8], fill="accent", radius=4)
        if label:
            mx, my = (a[0] + bpt[0]) / 2, (a[1] + bpt[1]) / 2
            page.text([mx - 40, my - 24, 80, 14], label, style="flowNote")

    c = centers
    arrow((c[0][2] + c[0][4], c[0][1]), (c[1][2], c[1][1]), "sign in")
    arrow((c[1][2] + c[1][4], c[1][1]), (c[2][2], c[2][1]), "ask")
    arrow((c[1][0], c[1][1] + c[1][5] / 2), (c[3][0], c[3][1] - c[3][5] / 2), "hold mic")
    arrow((c[1][0] + 40, c[1][1] + c[1][5] / 2), (c[4][0], c[4][1] - c[4][5] / 2), "browse")
    arrow((c[1][0] - 40, c[1][1] + c[1][5] / 2), (c[5][0], c[5][1] - c[5][5] / 2), "profile")

    page.text([64, OH - 40, 1200, 18],
              "FrameGraph SDK · DocumentBuilder + layout helpers · one composed document",
              style="flowNote")


# ===========================================================================
# Page 2 — Onboarding / Welcome
# ===========================================================================
def onboarding(b: DocumentBuilder) -> None:
    page = screen(b, "s1_onboarding")
    # reactive assistant orb (concentric)
    cx, cy = W / 2, 250
    circle(page, cx, cy, 78, fill="accsft", stroke="line", dash=True)
    circle(page, cx, cy, 54, fill="fill")
    circle(page, cx, cy, 30, fill="accent")

    page.text([0, 372, W, 36], "Aura AI", style="wordmark")
    page.text([M + 30, 416, W - 2 * (M + 30), 44],
              "Your advanced AI assistant for everything.", style="caption")

    # value props
    rows = column([M + 16, 480, W - 2 * (M + 16), 96], count=3, gap=8)
    props = ["Chat, voice & vision in one place",
             "Agents & tools that take action",
             "Private by default · on-device memory"]
    for r, txt in zip(rows, props):
        circle(page, r[0] + 9, r[1] + 11, 7, fill="accsft", stroke="accent")
        page.text([r[0] + 26, r[1] + 3, r[2] - 26, 18], txt, style="place")

    # CTAs
    pill(page, [M, 636, W - 2 * M, 50], None, fill="accent", radius=14)
    page.text([M, 652, W - 2 * M, 18], "Continue with Apple", style="btn")
    pill(page, [M, 696, W - 2 * M, 50], None, fill="fill", stroke="line", radius=14)
    page.text([M, 712, W - 2 * M, 18], "Continue with email", style="btnGhost")
    page.text([M, 760, W - 2 * M, 16], "Skip for now", style="lbl")

    page.layer("annot")
    annotate(page, W - 150, 196, "Idle orb animates\nwhile listening",
             lead_to=(cx + 60, cy))
    annotate(page, W - 150, 628, "Primary CTA uses\nthe one accent")


# ===========================================================================
# Page 3 — Assistant Home
# ===========================================================================
def home(b: DocumentBuilder) -> None:
    page = screen(b, "s2_home")
    # greeting + avatar
    page.text([M, 56, 240, 24], "Good morning", style="screenH")
    page.text([M, 84, 240, 16], "What can I help with?", style="lbl")
    circle(page, W - M - 18, 70, 18, fill="fill2", stroke="line")

    # ask-anything bar
    pill(page, [M, 120, W - 2 * M, 52], None, fill="fill", stroke="line", radius=16)
    page.text([M + 18, 138, 180, 16], "Ask anything…", style="place")
    icon(page, [W - M - 84, 130, 32, 32], "▦")        # camera / vision
    icon(page, [W - M - 44, 130, 32, 32], "◉")        # mic

    # model + tools chips
    pill(page, [M, 188, 150, 30], "Aura-Pro  ▾", fill="accsft", style="chipA")
    pill(page, [M + 160, 188, 92, 30], "Tools  ▾", fill="fill", stroke="line")
    pill(page, [M + 260, 188, 90, 30], "Temp ▾", fill="fill", stroke="line")

    # quick actions grid
    page.text([M, 240, 200, 16], "Quick actions", style="h")
    acts = [("✎", "Write"), ("≣", "Summarize"), ("</>", "Code"), ("◧", "Image")]
    for (g, name), cell in zip(acts, grid([M, 266, W - 2 * M, 150],
                                          cols=2, rows=2, gap=12, row_gap=12)):
        page.rect(cell, fill="fill", radius=14)
        ix, iy, iw, _ = inset(cell, 14)
        icon(page, [ix, iy, 34, 34], g, fill="paper")
        page.text([ix, iy + 44, iw, 16], name, style="h")

    # recents
    page.text([M, 440, 200, 16], "Recent", style="h")
    page.text([W - M - 60, 440, 60, 16], "See all", style="chipA")
    rrows = column([M, 466, W - 2 * M, 234], count=3, gap=10)
    for r in rrows:
        page.rect(r, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
        ix, iy, iw, ih = inset(r, [12, 14])
        icon(page, [ix, iy + ih / 2 - 17, 34, 34], "✦", fill="accsft", style="chipA")
        bars(page, [ix + 46, iy + 8, iw - 80, 0], n=2, gap=8, h=9, last=0.7)
        page.text([r[0] + r[2] - 24, iy + ih / 2 - 8, 16, 16], "›", style="glyph")

    tabbar(page, active=0)


# ===========================================================================
# Page 4 — Conversation thread
# ===========================================================================
def conversation(b: DocumentBuilder) -> None:
    page = screen(b, "s3_conversation")
    appbar(page, back=True, title="New chat", right=("⋯",))
    pill(page, [W / 2 - 55, 56, 110, 26], "Aura-Pro ▾", fill="accsft", style="chipA")

    y = 104
    # user bubble (right)
    uw = 210
    page.rect([W - M - uw, y, uw, 44], fill="accsft", radius=14)
    bars(page, [W - M - uw + 14, y + 12, uw - 28, 0], n=2, gap=7, h=8, last=0.6,
         color="accent")
    y += 60

    # assistant bubble (left)
    aw = 250
    page.rect([M, y, aw, 96], fill="fill", radius=14)
    bars(page, [M + 14, y + 14, aw - 28, 0], n=4, gap=8, h=8, last=0.45)
    y += 112

    # tool-call card
    page.rect([M, y, W - 2 * M, 56], fill="paper", stroke="line",
              stroke_style=DASH, radius=12)
    icon(page, [M + 12, y + 12, 32, 32], "⚙", fill="accsft", style="chipA")
    page.text([M + 54, y + 12, 200, 14], "Searching the web…", style="h")
    page.text([M + 54, y + 32, 220, 12], "tool · 3 sources found", style="lbl")
    pill(page, [W - M - 64, y + 16, 52, 24], "Run", fill="accent", style="btn")
    y += 72

    # assistant bubble with a chart placeholder
    page.rect([M, y, W - 2 * M, 150], fill="fill", radius=14)
    ghost(page, [M + 14, y + 14, W - 2 * M - 28, 86], radius=8, label="◔ chart")
    bars(page, [M + 14, y + 112, W - 2 * M - 28, 0], n=2, gap=8, h=8, last=0.5)
    y += 166

    # suggestion chips
    pill(page, [M, y, 120, 28], "Explain more", fill="paper", stroke="line")
    pill(page, [M + 130, y, 96, 28], "Export", fill="paper", stroke="line")
    pill(page, [M + 234, y, 110, 28], "Regenerate", fill="paper", stroke="line")

    # composer
    cy = H - 96
    page.rect([0, cy - 8, W, 96], fill="paper")
    page.rect([0, cy - 8, W, 1], fill="line")
    icon(page, [M, cy, 36, 36], "＋")
    pill(page, [M + 46, cy, W - 2 * M - 92, 36], None, fill="fill",
         stroke="line", radius=18)
    page.text([M + 62, cy + 10, 140, 16], "Message Aura…", style="place")
    icon(page, [W - M - 80, cy, 36, 36], "◉")           # voice
    circle(page, W - M - 18, cy + 18, 18, fill="accent")
    page.text([W - M - 36, cy + 9, 36, 18], "↑", style="glyphA")

    page.layer("annot")
    annotate(page, M, 568, "↑ tool calls render inline as live status cards · "
             "tap Run to approve", lead_to=None)


# ===========================================================================
# Page 5 — Voice / Live mode
# ===========================================================================
def voice(b: DocumentBuilder) -> None:
    page = screen(b, "s4_voice", dark=True)
    appbar(page, title="Live", right=("✕",))
    pill(page, [M, 56, 110, 26], "● Listening", fill="accsft", style="chipA")

    # reactive orb + waveform ring
    cx, cy = W / 2, 300
    circle(page, cx, cy, 110, fill="paper", stroke="line", dash=True)
    circle(page, cx, cy, 74, fill="accsft")
    circle(page, cx, cy, 44, fill="accent")
    # waveform bars across the orb
    heights = [16, 30, 48, 26, 54, 22, 40, 18]
    bx = cx - (len(heights) * 9 - 5) / 2
    for i, hgt in enumerate(heights):
        page.rect([bx + i * 9, cy - hgt / 2, 5, hgt], fill="paper", radius=2)

    # live caption
    page.text([M, 452, W - 2 * M, 16], "TRANSCRIPT", style="badge")
    bars(page, [M, 480, W - 2 * M, 0], n=3, gap=12, h=10, last=0.55, color="barlt")

    # controls
    ctrls = row([M, 600, W - 2 * M, 64], count=3, gap=16)
    labels = [("⊘", "Mute"), ("⚏", "Captions"), ("⌨", "Keyboard")]
    for cbox, (g, name) in zip(ctrls, labels):
        circle(page, cbox[0] + cbox[2] / 2, cbox[1] + 24, 24, fill="fill",
               stroke="line")
        page.text([cbox[0], cbox[1] + 16, cbox[2], 18], g, style="glyph")
        page.text([cbox[0], cbox[1] + 54, cbox[2], 12], name, style="tab")

    # end call
    pill(page, [M + 60, 700, W - 2 * (M + 60), 52], None, fill="accent", radius=26)
    page.text([M, 716, W - 2 * M, 18], "End conversation", style="btn")

    page.layer("annot")
    annotate(page, W - 150, 220, "Orb scales with\nmic amplitude",
             lead_to=(cx + 80, cy))
    annotate(page, W - 154, 470, "Real-time caption\nstreams as user talks")


# ===========================================================================
# Page 6 — Discover (agents & tools)
# ===========================================================================
def discover(b: DocumentBuilder) -> None:
    page = screen(b, "s5_discover", title="Discover")
    icon(page, [W - M - 32, 52, 32, 32], "⌕")

    # featured agent
    page.rect([M, 92, W - 2 * M, 130], fill="accsft", radius=16)
    icon(page, [M + 16, 108, 44, 44], "✦", fill="paper", style="chipA")
    page.text([M + 72, 112, 200, 18], "Research Agent", style="h")
    page.text([M + 72, 134, 220, 14], "Featured this week", style="chipA")
    bars(page, [M + 16, 168, W - 2 * M - 32, 0], n=2, gap=8, h=8, last=0.7,
         color="barlt")
    pill(page, [W - M - 80, 178, 64, 30], "Try", fill="accent", style="btn")

    # category chips
    cats = ["All", "Writing", "Code", "Data", "Image"]
    cx = M
    for i, name in enumerate(cats):
        cw = 16 + len(name) * 8
        st = ("accsft", "chipA") if i == 0 else ("fill", "chip")
        pill(page, [cx, 240, cw, 28], name, fill=st[0], style=st[1])
        cx += cw + 8

    # agent grid 2 x 3
    page.text([M, 290, 200, 16], "Popular agents", style="h")
    glyphs = ["✎", "</>", "◧", "≣", "✦", "☰"]
    names = ["Writer", "Coder", "Designer", "Analyst", "Tutor", "Planner"]
    for g, name, cell in zip(glyphs, names,
                             grid([M, 316, W - 2 * M, 360], cols=2, rows=3,
                                  gap=12, row_gap=12)):
        page.rect(cell, fill="paper", stroke="line", stroke_style=HAIR, radius=14)
        ix, iy, iw, _ = inset(cell, 12)
        icon(page, [ix, iy, 34, 34], g, fill="accsft", style="chipA")
        page.text([ix, iy + 42, iw, 16], name, style="h")
        bars(page, [ix, iy + 62, iw, 0], n=1, gap=0, h=8, last=0.8, color="barlt")
        pill(page, [ix, iy + 84, 56, 22], "Open", fill="fill", style="chip")

    tabbar(page, active=1)

    page.layer("annot")
    annotate(page, W - 150, 96, "Featured agent slot\nrotates weekly")


# ===========================================================================
# Page 7 — Settings
# ===========================================================================
def settings(b: DocumentBuilder) -> None:
    page = screen(b, "s6_settings", title="Settings")

    # profile row
    page.rect([M, 92, W - 2 * M, 72], fill="fill", radius=16)
    circle(page, M + 40, 128, 24, fill="paper", stroke="line")
    page.text([M + 76, 110, 180, 18], "Pedro A.", style="h")
    page.text([M + 76, 132, 200, 14], "pedro@example.com · Pro", style="lbl")
    page.text([W - M - 24, 120, 16, 16], "›", style="glyph")

    def section(title, y, rows):
        page.text([M, y, 240, 14], title, style="badge")
        box = [M, y + 22, W - 2 * M, len(rows) * 48 + 8]
        page.rect(box, fill="paper", stroke="line", stroke_style=HAIR, radius=14)
        rr = column([M, y + 26, W - 2 * M, len(rows) * 48], count=len(rows))
        for (g, label, kind), r in zip(rows, rr):
            ix, iy, iw, ih = inset(r, [0, 16])
            icon(page, [ix, iy + ih / 2 - 14, 28, 28], g, fill="fill2", radius=8)
            page.text([ix + 40, iy + ih / 2 - 8, iw - 120, 16], label, style="chip")
            if kind == "toggle":
                pill(page, [ix + iw - 44, iy + ih / 2 - 11, 40, 22], None,
                     fill="accent", radius=11)
                circle(page, ix + iw - 14, iy + ih / 2, 8, fill="paper")
            elif kind == "toggle_off":
                pill(page, [ix + iw - 44, iy + ih / 2 - 11, 40, 22], None,
                     fill="fill2", radius=11)
                circle(page, ix + iw - 30, iy + ih / 2, 8, fill="paper")
            else:
                page.text([ix + iw - 70, iy + ih / 2 - 8, 70, 16], kind,
                          style="lbl")
        return box[1] + box[3] + 22

    y = 186
    y = section("MODEL", y, [
        ("✦", "Default model", "Aura-Pro ›"),
        ("◔", "Response length", "Balanced ›"),
    ])
    y = section("PERSONALIZATION", y, [
        ("✎", "Custom instructions", "›"),
        ("⊚", "Memory", "toggle"),
        ("☾", "Dark appearance", "toggle_off"),
    ])
    y = section("PRIVACY", y, [
        ("⛉", "Train on my data", "toggle_off"),
        ("⤓", "Export data", "›"),
    ])

    pill(page, [M, y + 4, W - 2 * M, 46], None, fill="fill", stroke="line", radius=14)
    page.text([M, y + 18, W - 2 * M, 18], "Sign out", style="btnGhost")

    page.layer("annot")
    annotate(page, W - 150, 300, "Memory toggle gates\non-device context")


# ---- build ---------------------------------------------------------------- #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Aura AI — Mobile Wireframe", profile="deck", lang="en")
    for name, value in COLORS.items():
        b.define_color(name, value)
    for name, style in STYLES.items():
        b.define_text_style(name, **style)

    overview(b)
    onboarding(b)
    home(b)
    conversation(b)
    voice(b)
    discover(b)
    settings(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "fixtures", "ai-mobile-app-wireframe.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
