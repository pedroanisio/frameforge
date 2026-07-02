#!/usr/bin/env python3
"""SYRUS — client-acquisition proposal, built in the "Modern Sovereign" brand.

Implements the SYRUS Brand Refactor & Proposal Build Brief as one FrameGraph
deck (16:9, 1920x1080, 14 sections). The strategy/voice (brief §2-3) drives the
copy; the visual system (brief §4, Register A) drives the look; the section list
(brief §5) drives the build. The §6 acceptance gates are designed-in:

  * zero hype words (the §3.5 blacklist never appears in copy)
  * gold is a scalpel — seal, one rule, one metric, CTAs only (<=10% / screen)
  * dark/Bone rhythm: no more than two dark sections without a Bone break
  * numbering only on the onboarding timeline (pillars/comparison are labelled)
  * WCAG AA: Cloud/Mist on Obsidian and Ink on Bone clear AA; on Bone, accent
    text is Bronze (gold-on-bone fails), gold there is decorative (seal/rule)
  * the signature is present on every authority moment: the seal stamps cover,
    new-way, system, guarantee, CTA and back; the contour motif is structure.

Personalization is a working template field: edit ``PROSPECT`` and every page
re-keys (cover, footers, copy). Case-study numbers are illustrative placeholders
to be replaced with verified client results (marked on the proof page).

Run from the repo root::

    uv run python examples/syrus_proposal.py
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize  # noqa: E402
from framegraph.sdk.paint import rgba  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
#  Personalization — the master-template fields (brief §5). Edit per send.     #
# --------------------------------------------------------------------------- #
PROSPECT = {
    "company": "Apex Roofing & Exteriors",
    "owner": "Marcus Reed",
    "city": "Charlotte, NC",
    "trade": "Roofing & Exteriors",
}
COMPANY, OWNER, CITY, TRADE = (PROSPECT[k] for k in ("company", "owner", "city", "trade"))

# --------------------------------------------------------------------------- #
#  Color tokens (brief §4.2)                                                   #
# --------------------------------------------------------------------------- #
OBSIDIAN = "#0B0F14"   # primary dark ground
GRAPHITE = "#151A21"   # surfaces / cards on dark
GRAPHITE2 = "#1B222C"  # raised surface
SLATE = "#2A323C"      # borders, dividers, contour lines
GOLD = "#C8A24B"       # primary accent
GOLD_HI = "#DDB968"    # hover / active
BRONZE = "#8A6A38"     # deep accent, seal shading, accent text on Bone
BONE = "#F5F2E9"       # light "paper" ground
BONE2 = "#ECE7DA"      # raised paper surface
INK = "#0E1217"        # text on Bone
CLOUD = "#E7EAEE"      # primary text on dark
MIST = "#A7B0BC"       # muted / secondary text on dark
BONE_SUB = "#574F41"   # secondary text on Bone (warm; gold-on-bone fails AA)
BONE_LINE = "#D9D2C2"  # hairlines on Bone
SIGNAL = "#45C08A"     # positive data only
ALERT = "#E0653C"      # errors / "the cost" only

# --------------------------------------------------------------------------- #
#  Type system (brief §4.3) — serif display, sans body, mono for data.         #
#  Sizes follow the §4.3 scale, set on a generous centred column so the web    #
#  desktop proportions hold on the deck canvas.                                #
# --------------------------------------------------------------------------- #
SERIF = ["Fraunces", "GT Super", "Canela", "Playfair Display", "Georgia", "Times New Roman", "serif"]
SANS = ["Inter", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans", "sans-serif"]
MONO = ["Geist Mono", "IBM Plex Mono", "DejaVu Sans Mono", "monospace"]

W, H = 1920, 1080
MX = 200               # side margin -> 1520 content width
MT = 150               # content top
MB = 96                # bottom margin
CW = W - 2 * MX
TOTAL = 14

# type scale
T_DISPLAY = 104        # cover/back hero (hero-exempt from body scale)
T_H1 = 60
T_H2 = 42
T_H3 = 28
T_BODYL = 21
T_BODY = 18
T_SMALL = 15
T_EYEBROW = 15
T_METRIC = 64


# --------------------------------------------------------------------------- #
#  Text helpers                                                                #
# --------------------------------------------------------------------------- #
def ts(size, color, *, weight=None, align=None, spacing=None, lh=None,
       transform=None, family=None, valign=None, italic=False):
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
    if valign is not None:
        s["vertical_align"] = valign
    if italic:
        s["font_style"] = "italic"
    return s


def eyebrow(page, x, y, text, *, color=GOLD, w=900, align="left"):
    """The brand eyebrow: uppercase 0.16em sans label. Tiny — gold stays scarce."""
    page.text([x, y, w, 22], text,
              style=ts(T_EYEBROW, color, weight=600, spacing=2.4,
                       transform="uppercase", align=align))


def head(page, x, y, lines, *, size=T_H1, color=CLOUD, family=SERIF, weight=600,
         lh=1.04, align="left", w=1180):
    """A serif headline. The renderer breaks lines only by width, so each given
    line is its own stacked text object (advance = size * lh)."""
    adv = size * lh
    for i, line in enumerate(lines):
        page.add({"type": "text", "box": [x, y + i * adv, w, int(size * 1.5)],
                  "spans": [{"text": line}],
                  "style": {"font_family": family, "font_size": size,
                            "font_weight": weight, "line_height": 1.02,
                            "color": color, "align": align}})
    return y + len(lines) * adv


def runs(page, x, y, parts, *, size=T_H1, family=SERIF, weight=600, w=1180, align="left"):
    """One headline line with coloured runs. A per-span style does NOT inherit the
    block ``font_family``/size in this renderer, so each span carries the full face."""
    span_face = {"font_family": family, "font_size": size, "font_weight": weight}
    page.add({"type": "text", "box": [x, y, w, int(size * 1.5)],
              "spans": [{"text": t, "style": {**span_face, "color": c}} for t, c in parts],
              "style": {"font_family": family, "font_size": size,
                        "font_weight": weight, "line_height": 1.02, "align": align}})


def body(page, x, y, w, text, *, size=T_BODY, color=MIST, lh=1.62, weight=400,
         family=None, h=None, align="left"):
    page.text([x, y, w, h if h is not None else 400], text,
              style=ts(size, color, weight=weight, lh=lh, align=align, family=family))


def rule(page, x, y, w, *, color=GOLD, weight=2.0):
    """A single hairline rule — the brand's quiet divider (never with the motif)."""
    page.line([x, y], [x + w, y], stroke=color, stroke_style={"stroke_width": weight})


# --------------------------------------------------------------------------- #
#  Geometry helpers                                                            #
# --------------------------------------------------------------------------- #
def _pol(cx, cy, r, deg, squish=1.0):
    rad = math.radians(deg)
    return [cx + r * math.cos(rad), cy + r * squish * math.sin(rad)]


def _perturb(deg):
    """A fixed organic radius perturbation in roughly [-1, 1] for contour rings."""
    t = math.radians(deg)
    return 0.6 * math.sin(3 * t + 0.5) + 0.4 * math.sin(2 * t + 1.7)


def contour_field(page, cx, cy, *, rings=7, r0=120, dr=66, color=SLATE,
                  width=1.4, alpha=0.5, squish=0.66, fade=True, n=96):
    """The territory-contour motif — nested topographic lines. The perturbation
    is shared and bounded under dr/2, so rings nest and never cross. Used as
    structure (backgrounds, the seal's field, the CTA convergence), not decor."""
    with page.bleed():
        for i in range(rings):
            base = r0 + i * dr
            a = alpha * (1.0 - 0.55 * i / max(1, rings - 1)) if fade else alpha
            pts = []
            for k in range(n + 1):
                deg = k * 360.0 / n
                r = base + dr * 0.4 * _perturb(deg)
                pts.append(_pol(cx, cy, r, deg, squish))
            page.polyline(pts, smooth=True, closed=True, fill="none",
                          stroke=rgba(color, a), stroke_style={"stroke_width": width})


# --------------------------------------------------------------------------- #
#  The seal / crest (brief §4.4) — crest (authority) + map (territory) +       #
#  S monogram (ownership). Stamped once per authority moment.                  #
# --------------------------------------------------------------------------- #
def seal(page, cx, cy, r, *, gold=GOLD, line=SLATE, disc=None, mono=True):
    with page.bleed():
        if disc is not None:
            page.circle([cx, cy], r, fill=disc)
        # faint contour field inside the seal — the "territory"
        contour_field(page, cx, cy, rings=4, r0=r * 0.22, dr=r * 0.16,
                      color=gold, width=1.0, alpha=0.22, squish=0.82, fade=False, n=72)
        # double bezel ring
        page.circle([cx, cy], r, fill="none", stroke=gold, stroke_style={"stroke_width": max(2.0, r * 0.028)})
        page.circle([cx, cy], r * 0.9, fill="none", stroke=gold, stroke_style={"stroke_width": 1.2})
        # bezel ticks (compass), long at the four cardinals
        count = 48
        for i in range(count):
            deg = i * 360.0 / count
            cardinal = i % (count // 4) == 0
            r1 = r * (0.9)
            r2 = r * (0.79 if cardinal else 0.85)
            a, b = _pol(cx, cy, r1, deg), _pol(cx, cy, r2, deg)
            page.line(a, b, stroke=gold, stroke_style={"stroke_width": 2.0 if cardinal else 1.0})
        # north marker
        tip = _pol(cx, cy, r * 0.9, -90)
        page.polygon([[tip[0], tip[1] - r * 0.06],
                      [tip[0] - r * 0.05, tip[1] + r * 0.04],
                      [tip[0] + r * 0.05, tip[1] + r * 0.04]], fill=gold)
        # S monogram
        if mono:
            page.add({"type": "text", "box": [cx - r, cy - r * 0.94, 2 * r, 2 * r * 0.94],
                      "spans": [{"text": "S"}],
                      "style": {"font_family": SERIF, "font_size": r * 1.15,
                                "font_weight": 600, "color": gold,
                                "align": "center", "vertical_align": "middle"}})


def wordmark(page, x, y, size, *, color=CLOUD, descriptor=True, dcolor=None, align="left", w=900):
    """SYRUS wordmark + descriptor lockup (brief §4.4)."""
    page.add({"type": "text", "box": [x, y, w, int(size * 1.2)],
              "spans": [{"text": "SYRUS"}],
              "style": {"font_family": SERIF, "font_size": size, "font_weight": 600,
                        "color": color, "letter_spacing": size * 0.04, "align": align}})
    if descriptor:
        page.text([x, y + size * 1.12, w, 22],
                  "Client Acquisition for Contractors",
                  style=ts(max(13, size * 0.20), dcolor or MIST, weight=600,
                           spacing=2.0, transform="uppercase", align=align))


# --------------------------------------------------------------------------- #
#  State glyphs — drawn (renderer-safe) check / cross / dot                    #
# --------------------------------------------------------------------------- #
def check(page, x, y, s, color):
    page.polyline([[x, y + 0.52 * s], [x + 0.4 * s, y + s], [x + s, y]],
                  fill="none", stroke=color,
                  stroke_style={"stroke_width": max(s * 0.16, 2),
                                "stroke_linecap": "round", "stroke_linejoin": "round"})


def cross(page, x, y, s, color):
    sw = {"stroke_width": max(s * 0.14, 2), "stroke_linecap": "round"}
    page.line([x, y], [x + s, y + s], stroke=color, stroke_style=sw)
    page.line([x + s, y], [x, y + s], stroke=color, stroke_style=sw)


# --------------------------------------------------------------------------- #
#  Page scaffolding + chrome                                                   #
# --------------------------------------------------------------------------- #
def _page(b, sid, *, dark=True):
    page = b.page(sid, canvas="deck-16x9", coordinate_mode="absolute")
    page.layer("bg")
    page.rect([0, 0, W, H], fill=OBSIDIAN if dark else BONE)
    page.layer("body")
    return page


def chrome(page, n, *, dark=True, label="THE PROPOSAL"):
    fg = CLOUD if dark else INK
    sub = MIST if dark else BONE_SUB
    ln = SLATE if dark else BONE_LINE
    # top hairline + masthead
    page.line([MX, 96], [W - MX, 96], stroke=ln, stroke_style={"stroke_width": 1})
    page.add({"type": "text", "box": [MX, 60, 400, 28], "spans": [{"text": "SYRUS"}],
              "style": {"font_family": SERIF, "font_size": 21, "font_weight": 600,
                        "color": fg, "letter_spacing": 2.0}})
    eyebrow(page, W - MX - 600, 66, label, color=sub, w=600, align="right")
    # footer
    page.line([MX, H - 70], [W - MX, H - 70], stroke=ln, stroke_style={"stroke_width": 1})
    page.text([MX, H - 58, 900, 20], f"Prepared for {COMPANY} · {CITY}",
              style=ts(13, sub, weight=500, spacing=0.4))
    page.text([W - MX - 200, H - 58, 200, 20], f"{n:02d} / {TOTAL:02d}",
              style=ts(13, sub, weight=600, family=MONO, align="right", spacing=1))


# --------------------------------------------------------------------------- #
#  1 — Cover                                                                   #
# --------------------------------------------------------------------------- #
def p_cover(b):
    p = _page(b, "p01-cover", dark=True)
    # faint territory drawn behind, bleeding from lower-right
    contour_field(p, W + 120, H + 60, rings=9, r0=180, dr=92, color=SLATE,
                  width=1.4, alpha=0.5, squish=0.74)
    seal(p, W / 2, 372, 132, disc=OBSIDIAN)
    # §5.1: gold lives only on the seal + one rule here — the master line is Cloud.
    head(p, MX, 556, ["Own Your Territory"], size=T_DISPLAY, color=CLOUD, w=CW, align="center")
    rule(p, W / 2 - 90, 712, 180, color=GOLD, weight=2.5)
    p.text([MX, 752, CW, 40], f"An acquisition system for {COMPANY}",
            style=ts(28, CLOUD, weight=400, family=SERIF, align="center", italic=True))
    p.text([MX, 836, CW, 24], f"Prepared for {OWNER} · {CITY} · {TRADE}",
            style=ts(T_SMALL, MIST, weight=500, spacing=2.0, transform="uppercase", align="center"))
    wordmark(p, MX, H - 96, 0, color=CLOUD)  # placeholder removed below
    # bottom lockup
    p.add({"type": "text", "box": [0, H - 86, W, 26], "spans": [{"text": "SYRUS"}],
           "style": {"font_family": SERIF, "font_size": 18, "font_weight": 600,
                     "color": MIST, "letter_spacing": 4.0, "align": "center"}})
    return p


# --------------------------------------------------------------------------- #
#  2 — The reframe (Bone)                                                      #
# --------------------------------------------------------------------------- #
def p_reframe(b):
    p = _page(b, "p02-reframe", dark=False)
    chrome(p, 2, dark=False)
    eyebrow(p, MX, MT, "The real problem", color=BRONZE)
    y = head(p, MX, MT + 38,
             ["Your pipeline runs on", "two things you don’t control."],
             size=T_H1, color=INK, w=1400)
    body(p, MX, y + 40, 1080,
         "Referrals when they happen — and shared leads, sold to four of your "
         "competitors at the same time. One is unpredictable. The other isn’t "
         "really yours. Neither lets you plan, hire, or choose the work you take.",
         size=T_BODYL, color=BONE_SUB, lh=1.62, h=200)
    rule(p, MX, y + 240, 120, color=BRONZE, weight=2.5)
    p.text([MX, y + 268, 1080, 30],
            "Before we show you anything, we want to be right about where you actually stand.",
            style=ts(T_BODY, INK, weight=500, italic=True, family=SERIF, lh=1.5))
    return p


# --------------------------------------------------------------------------- #
#  3 — The stakes (dark)                                                       #
# --------------------------------------------------------------------------- #
def p_stakes(b):
    p = _page(b, "p03-stakes", dark=True)
    chrome(p, 3)
    eyebrow(p, MX, MT, "The cost of standing still")
    head(p, MX, MT + 38, ["Every month without a", "system is a month you", "paid for in lost work."],
         size=T_H1, color=CLOUD, w=1180)
    # one gold metric, restrained
    mx2 = W - MX - 560
    p.text([mx2, MT + 60, 560, 26], "ONE MISSED JOB",
            style=ts(T_SMALL, MIST, weight=600, spacing=2.0))
    p.add({"type": "text", "box": [mx2, MT + 92, 560, 90], "spans": [{"text": "$9,400"}],
           "style": {"font_family": MONO, "font_size": 84, "font_weight": 500, "color": GOLD}})
    p.text([mx2, MT + 196, 560, 70],
            "average value of one " + TRADE.split(" & ")[0].lower() + " job you didn’t quote",
            style=ts(T_BODY, MIST, lh=1.55))
    body(p, MX, MT + 360, 760,
         "Jobs you didn’t quote. A territory you didn’t claim. A competitor who "
         "did — and who now owns the reviews, the referrals, and the next ten roofs "
         "on that street. The status quo isn’t neutral. It compounds against you.",
         size=T_BODYL, color=CLOUD, lh=1.6, h=240)
    return p


# --------------------------------------------------------------------------- #
#  4 — The new way (dark, transition; seal returns)                            #
# --------------------------------------------------------------------------- #
def p_newway(b):
    p = _page(b, "p04-newway", dark=True)
    chrome(p, 4)
    contour_field(p, W - 300, H / 2, rings=8, r0=120, dr=80, color=SLATE,
                  width=1.4, alpha=0.45, squish=0.9)
    seal(p, W - 360, 300, 96, disc=OBSIDIAN)
    eyebrow(p, MX, MT, "The new way")
    runs(p, MX, MT + 38, [("You don’t need more leads.", CLOUD)], size=T_H1, w=1180)
    runs(p, MX, MT + 38 + T_H1 * 1.04, [("You need a ", CLOUD), ("system", GOLD), (".", CLOUD)],
         size=T_H1, w=1180)
    body(p, MX, MT + 220, 880,
         "SYRUS is a client-acquisition system built exclusively for premium "
         "contractors. We install a predictable engine that delivers exclusive, "
         "pre-qualified, ready-to-buy appointments straight to your calendar — and "
         "the command center to manage them. One client per territory. You stop "
         "chasing referrals and cold leads, and start choosing the jobs you want.",
         size=T_BODYL, color=MIST, lh=1.62, h=300)
    rule(p, MX, MT + 470, 120, color=GOLD, weight=2.5)
    p.text([MX, MT + 498, 900, 30], "Predictably. Exclusively. On demand.",
            style=ts(T_H3, CLOUD, weight=500, family=SERIF))
    return p


# --------------------------------------------------------------------------- #
#  5 — The system (Bone): engine diagram + four pillars (labelled, not numbered)#
# --------------------------------------------------------------------------- #
def _engine(p, x, y, w):
    """ad -> qualified homeowner -> booked appointment -> command center."""
    nodes = ["Targeted\ncampaign", "Qualified\nhomeowner", "Booked\nappointment", "Command\ncenter"]
    n = len(nodes)
    gap = w / n
    r = 30
    cy = y + r
    for i, label in enumerate(nodes):
        cx = x + gap * i + gap / 2
        last = i == n - 1
        p.circle([cx, cy], r, fill=(OBSIDIAN if last else BONE),
                 stroke=(GOLD if last else BRONZE), stroke_style={"stroke_width": 2.2})
        # a centre dot, not a number — numbering belongs only on the timeline (§4.8)
        p.circle([cx, cy], r * 0.3, fill=(GOLD if last else BRONZE))
        for j, ln in enumerate(label.split("\n")):
            p.text([cx - gap / 2, cy + r + 16 + j * 22, gap, 22], ln,
                   style=ts(T_SMALL, INK, weight=600, align="center"))
        if i < n - 1:
            nx = x + gap * (i + 1) + gap / 2
            p.arrow([cx + r + 6, cy], [nx - r - 6, cy], color=BRONZE, width=2.0, head=10)


def p_system(b):
    p = _page(b, "p05-system", dark=False)
    chrome(p, 5, dark=False)
    eyebrow(p, MX, MT, "The system", color=BRONZE)
    head(p, MX, MT + 36, ["The machine that books your work."], size=T_H2, color=INK, w=1400)
    _engine(p, MX, MT + 150, CW)
    pillars = [
        ("Predictable Pipeline", "An always-on engine of exclusive, qualified appointments.",
         "Turn it up when you want more work."),
        ("Booked, Not Chased", "Homeowners book themselves onto your calendar.",
         "No speed-to-lead panic, no ghosting chase."),
        ("Command Center", "Every lead, job, and follow-up in one system.",
         "We install it and run it for you. Nothing slips."),
        ("Built for the Trade", "Built only for contractors — territory-exclusive.",
         "One client per market. We protect it."),
    ]
    cy = MT + 330
    ch = 250
    gap = 28
    cwid = (CW - 3 * gap) / 4
    for i, (title, line, how) in enumerate(pillars):
        x = MX + i * (cwid + gap)
        differ = i == 3
        p.rect([x, cy, cwid, ch], radius=14, fill=(OBSIDIAN if differ else BONE2),
               stroke=(GOLD if differ else BONE_LINE), stroke_style={"stroke_width": 1.4})
        # seal-mark instead of a number
        seal(p, x + 34, cy + 38, 16, gold=(GOLD if differ else BRONZE),
             disc=(OBSIDIAN if differ else BONE2), mono=False)
        tcol = CLOUD if differ else INK
        scol = MIST if differ else BONE_SUB
        p.text([x + 24, cy + 70, cwid - 48, 56], title,
               style=ts(20, tcol, weight=700, family=SANS, lh=1.1))
        p.text([x + 24, cy + 130, cwid - 48, 70], line,
               style=ts(T_SMALL, scol, lh=1.5))
        p.text([x + 24, cy + ch - 56, cwid - 48, 46], how,
               style=ts(13.5, (GOLD if differ else BRONZE), weight=600, lh=1.4))
    return p


# --------------------------------------------------------------------------- #
#  6 — How it works (dark): the one place numbering belongs                    #
# --------------------------------------------------------------------------- #
def p_timeline(b):
    p = _page(b, "p06-timeline", dark=True)
    chrome(p, 6)
    eyebrow(p, MX, MT, "How it works · onboarding")
    head(p, MX, MT + 36, ["Done-for-you. Live in weeks."], size=T_H2, color=CLOUD, w=1200)
    steps = [
        ("01", "Week 1", "Install & configure", "We set up your territory, calendar, command center, and tracking. You hand us the keys; we do the build."),
        ("02", "Week 2", "Campaigns live", "Targeted campaigns launch in your exclusive area. Qualified homeowners start booking themselves in."),
        ("03", "~Day 14", "First booked appointment", "A real, pre-qualified, ready-to-buy appointment on your calendar — typically within the first two weeks."),
    ]
    baseY = MT + 230
    rule(p, MX + 40, baseY, CW - 80, color=GOLD, weight=2.0)
    n = len(steps)
    seg = (CW - 80) / n
    for i, (num, when, title, desc) in enumerate(steps):
        cx = MX + 40 + seg * i + 80
        p.circle([cx, baseY], 9, fill=GOLD)
        p.add({"type": "text", "box": [cx - 60, baseY + 34, 200, 60], "spans": [{"text": num}],
               "style": {"font_family": MONO, "font_size": 54, "font_weight": 500, "color": GOLD}})
        p.text([cx - 60, baseY + 104, seg - 40, 22], when.upper(),
               style=ts(T_SMALL, MIST, weight=600, spacing=1.6))
        p.text([cx - 60, baseY + 130, seg - 40, 30], title,
               style=ts(22, CLOUD, weight=700))
        p.text([cx - 60, baseY + 168, seg - 60, 150], desc,
               style=ts(T_SMALL, MIST, lh=1.55))
    p.text([MX, H - 150, CW, 30], "We run it. You show up and close.",
            style=ts(T_H3, CLOUD, weight=500, family=SERIF, align="center", italic=True))
    return p


# --------------------------------------------------------------------------- #
#  7 — Proof (dark): named case studies + real numbers, no zeros               #
# --------------------------------------------------------------------------- #
def p_proof(b):
    p = _page(b, "p07-proof", dark=True)
    chrome(p, 7)
    eyebrow(p, MX, MT, "Proof · named results")
    head(p, MX, MT + 36, ["Numbers, not adjectives."], size=T_H2, color=CLOUD, w=1200)
    cases = [
        ("Summit Roofing Co.", "Roofing · Austin, TX",
         "Referral-dependent, feast-or-famine pipeline.",
         "46", "booked appointments", "$50 cost-per-appointment · 20 days"),
        ("Ironclad Exteriors", "Exteriors · Denver, CO",
         "Burned by a shared-lead reseller; low close rate.",
         "47", "booked appointments", "exclusive · 30 days"),
        ("Keystone Solar", "Solar · Phoenix, AZ",
         "Could not scale past word-of-mouth.",
         "3.1×", "pipeline in 90 days", "1 territory · fully exclusive"),
    ]
    cy = MT + 150
    ch = 470
    gap = 28
    cwid = (CW - 2 * gap) / 3
    for i, (name, meta, before, num, unit, foot) in enumerate(cases):
        x = MX + i * (cwid + gap)
        p.rect([x, cy, cwid, ch], radius=14, fill=GRAPHITE,
               stroke=SLATE, stroke_style={"stroke_width": 1.2})
        p.text([x + 26, cy + 28, cwid - 52, 26], name,
               style=ts(20, CLOUD, weight=700))
        p.text([x + 26, cy + 58, cwid - 52, 20], meta.upper(),
               style=ts(12.5, MIST, weight=600, spacing=1.4))
        p.line([x + 26, cy + 96], [x + cwid - 26, cy + 96], stroke=SLATE, stroke_style={"stroke_width": 1})
        p.text([x + 26, cy + 112, cwid - 52, 20], "BEFORE",
               style=ts(12, BRONZE, weight=700, spacing=2.0))
        p.text([x + 26, cy + 134, cwid - 52, 70], before,
               style=ts(T_SMALL, MIST, lh=1.5))
        p.text([x + 26, cy + 224, cwid - 52, 20], "AFTER",
               style=ts(12, GOLD, weight=700, spacing=2.0))
        p.add({"type": "text", "box": [x + 26, cy + 248, cwid - 52, 78], "spans": [{"text": num}],
               "style": {"font_family": MONO, "font_size": 70, "font_weight": 500, "color": GOLD}})
        p.text([x + 26, cy + 332, cwid - 52, 22], unit,
               style=ts(T_BODY, CLOUD, weight=600))
        p.text([x + 26, cy + ch - 52, cwid - 52, 40], foot,
               style=ts(13, MIST, family=MONO, lh=1.45))
    p.text([MX, cy + ch + 22, CW, 20],
            "Illustrative — replace with your verified client results, named, with real metric and timeframe.",
            style=ts(12.5, MIST, italic=True))
    return p


# --------------------------------------------------------------------------- #
#  8 — Why SYRUS (Bone): three-way comparison, SYRUS column accented           #
# --------------------------------------------------------------------------- #
def p_why(b):
    p = _page(b, "p08-why", dark=False)
    chrome(p, 8, dark=False)
    eyebrow(p, MX, MT, "Why SYRUS", color=BRONZE)
    head(p, MX, MT + 36, ["Three ways to fill a calendar.", "Only one is yours."],
         size=T_H2, color=INK, w=1400)
    rows = [
        ("Exclusive to you", False, False, True),
        ("Built only for the trade", False, False, True),
        ("Done-for-you — we run it", False, "partial", True),
        ("Owns ad → booked appointment", "partial", False, True),
        ("Territory-protected", False, False, True),
    ]
    cols = ["Lead resellers", "Generalist ad agency", "SYRUS"]
    tableX = MX
    tableY = MT + 200
    labelW = 560
    colW = (CW - labelW) / 3
    rowH = 90
    # SYRUS column dark card (the accented choice)
    sx = tableX + labelW + 2 * colW
    p.rect([sx - 8, tableY - 56, colW + 16, rowH * len(rows) + 76], radius=14,
           fill=OBSIDIAN)
    # headers
    for j, c in enumerate(cols):
        cx = tableX + labelW + j * colW
        is_syrus = j == 2
        p.text([cx, tableY - 44, colW, 26], c,
               style=ts(T_BODY, (GOLD if is_syrus else BONE_SUB),
                        weight=700, align="center"))
    p.line([tableX, tableY - 6], [tableX + labelW, tableY - 6],
           stroke=BONE_LINE, stroke_style={"stroke_width": 1})
    for ri, (label, a, bb, c) in enumerate(rows):
        ry = tableY + ri * rowH
        p.text([tableX, ry + rowH / 2 - 14, labelW - 30, 28], label,
               style=ts(T_BODY, INK, weight=500, valign="middle"))
        for j, val in enumerate((a, bb, c)):
            cx = tableX + labelW + j * colW + colW / 2
            mid = ry + rowH / 2
            on_dark = j == 2
            if val is True:
                check(p, cx - 13, mid - 9, 26, GOLD if on_dark else SIGNAL)
            elif val == "partial":
                p.text([cx - 60, mid - 12, 120, 24], "partial",
                       style=ts(13, MIST if on_dark else BONE_SUB,
                                italic=True, align="center"))
            else:
                cross(p, cx - 11, mid - 11, 22, MIST if on_dark else "#B9B1A0")
        if ri < len(rows) - 1:
            p.line([tableX, ry + rowH], [tableX + labelW + 2 * colW, ry + rowH],
                   stroke=BONE_LINE, stroke_style={"stroke_width": 1})
    p.text([sx, tableY + rowH * len(rows) - 16, colW, 22],
            "One contractor per territory.",
            style=ts(13, GOLD, weight=600, align="center"))
    return p


# --------------------------------------------------------------------------- #
#  9 — The offer (dark): tiered packages, recommended tier seal-marked         #
# --------------------------------------------------------------------------- #
def p_offer(b):
    p = _page(b, "p09-offer", dark=True)
    chrome(p, 9)
    eyebrow(p, MX, MT, "The offer")
    head(p, MX, MT + 36, ["Pick the engine for your market."], size=T_H2, color=CLOUD, w=1200)
    tiers = [
        ("Territory", "$4,500", "/ mo", False,
         ["One exclusive territory", "Predictable Pipeline engine", "Self-booking to your calendar",
          "Command Center, installed", "Monthly performance review"]),
        ("Territory+", "$7,500", "/ mo", True,
         ["Everything in Territory", "Higher campaign volume", "Priority build & support",
          "Show-rate optimization", "Quarterly territory strategy"]),
        ("Dominion", "Custom", "", False,
         ["Multi-territory rollout", "Dedicated strategist", "Custom playbooks per market",
          "Crew-capacity planning", "Executive reporting"]),
    ]
    cy = MT + 160
    ch = 540
    gap = 30
    cwid = (CW - 2 * gap) / 3
    for i, (name, price, per, rec, feats) in enumerate(tiers):
        x = MX + i * (cwid + gap)
        p.rect([x, cy, cwid, ch], radius=16, fill=(GRAPHITE2 if rec else GRAPHITE),
               stroke=(GOLD if rec else SLATE), stroke_style={"stroke_width": 2.0 if rec else 1.2})
        if rec:
            seal(p, x + cwid - 44, cy + 44, 22, gold=GOLD, disc=GRAPHITE2, mono=False)
            p.text([x + 30, cy + 28, cwid - 120, 20], "RECOMMENDED",
                   style=ts(12, GOLD, weight=700, spacing=2.0))
        p.text([x + 30, cy + 64, cwid - 60, 30], name,
               style=ts(24, CLOUD, weight=700, family=SERIF))
        p.add({"type": "text", "box": [x + 30, cy + 108, cwid - 60, 66],
               "spans": [{"text": price}],
               "style": {"font_family": MONO, "font_size": 48, "font_weight": 500,
                         "color": (GOLD if rec else CLOUD)}})
        if per:
            p.text([x + 30, cy + 170, cwid - 60, 20], per,
                   style=ts(T_SMALL, MIST, weight=500))
        p.line([x + 30, cy + 206], [x + cwid - 30, cy + 206], stroke=SLATE, stroke_style={"stroke_width": 1})
        for k, f in enumerate(feats):
            fy = cy + 230 + k * 52
            check(p, x + 30, fy + 2, 16, GOLD if rec else MIST)
            p.text([x + 58, fy - 4, cwid - 88, 44], f,
                   style=ts(T_SMALL, CLOUD if rec else MIST, lh=1.35))
    p.text([MX, cy + ch + 16, CW, 22],
            "Every plan is one contractor per territory — stated plainly, because premium positioning doesn’t hide the price.",
            style=ts(13.5, MIST, italic=True, align="center"))
    return p


# --------------------------------------------------------------------------- #
#  10 — The guarantee (Bone): a sealed certificate panel                       #
# --------------------------------------------------------------------------- #
def p_guarantee(b):
    p = _page(b, "p10-guarantee", dark=False)
    chrome(p, 10, dark=False)
    eyebrow(p, MX, MT, "The guarantee", color=BRONZE)
    head(p, MX, MT + 36, ["You will never be sold out", "to your competitor."], size=T_H2, color=INK, w=1400)
    # certificate panel
    px, py, pw, ph = MX, MT + 220, CW, 540
    p.rect([px, py, pw, ph], radius=10, fill=BONE2, stroke=BRONZE, stroke_style={"stroke_width": 2.0})
    p.rect([px + 14, py + 14, pw - 28, ph - 28], radius=6, fill="none",
           stroke=rgba(BRONZE, 0.5), stroke_style={"stroke_width": 1.0})
    seal(p, px + pw - 180, py + ph / 2, 92, gold=BRONZE, line=BRONZE, disc=BONE2)
    p.text([px + 70, py + 70, pw - 460, 24], "TERRITORY EXCLUSIVITY",
            style=ts(T_SMALL, BRONZE, weight=700, spacing=2.4))
    body(p, px + 70, py + 110, pw - 460,
         "We work with one contractor per territory, and we protect it. While you’re "
         "a SYRUS client, we will not run acquisition for a competing "
         + TRADE.split(" & ")[0].lower() + " contractor in your service area. In writing.",
         size=T_BODYL, color=INK, lh=1.6, h=180)
    p.line([px + 70, py + 300], [px + pw - 360, py + 300], stroke=BONE_LINE, stroke_style={"stroke_width": 1})
    p.text([px + 70, py + 324, pw - 460, 22], "PERFORMANCE & ONBOARDING COMMITMENT",
            style=ts(T_SMALL, BRONZE, weight=700, spacing=2.0))
    body(p, px + 70, py + 360, pw - 460,
         "We install, configure, and launch on a fixed onboarding schedule — and we "
         "run the system for you. If we miss the build commitment, you don’t pay for "
         "that month. Clear terms, in plain language, before you sign.",
         size=T_BODY, color=BONE_SUB, lh=1.6, h=160)
    return p


# --------------------------------------------------------------------------- #
#  11 — Investment & ROI (dark): one clean comparison, one gold figure         #
# --------------------------------------------------------------------------- #
def p_roi(b):
    p = _page(b, "p11-roi", dark=True)
    chrome(p, 11)
    eyebrow(p, MX, MT, "Investment & ROI")
    head(p, MX, MT + 36, ["The math is not close."], size=T_H2, color=CLOUD, w=1200)
    # left: what it books ; right: what it costs ; equals: gold net
    colY = MT + 200
    leftX = MX
    rightX = MX + 560
    p.text([leftX, colY, 480, 22], "WHAT THE SYSTEM BOOKS / MONTH",
            style=ts(T_SMALL, MIST, weight=600, spacing=1.6))
    rows = [("8 booked jobs", "× $9,400 avg job"), ("close 4 of them", "= $37,600 won")]
    for i, (a, bb) in enumerate(rows):
        ry = colY + 44 + i * 64
        p.text([leftX, ry, 320, 30], a, style=ts(T_BODYL, CLOUD, weight=500))
        p.text([leftX + 300, ry, 260, 30], bb, style=ts(T_BODY, MIST, family=MONO))
    p.text([rightX, colY, 480, 22], "WHAT IT COSTS / MONTH",
            style=ts(T_SMALL, MIST, weight=600, spacing=1.6))
    p.text([rightX, colY + 44, 480, 30], "Territory+ plan", style=ts(T_BODYL, CLOUD, weight=500))
    p.text([rightX + 300, colY + 44, 260, 30], "$7,500", style=ts(T_BODY, MIST, family=MONO))
    p.text([rightX, colY + 108, 480, 30], "+ ad spend (you control)", style=ts(T_BODYL, CLOUD, weight=500))
    p.text([rightX + 300, colY + 108, 260, 30], "≈ $2,300", style=ts(T_BODY, MIST, family=MONO))
    rule(p, MX, colY + 230, CW, color=SLATE, weight=1.2)
    # the one gold figure
    p.text([MX, colY + 270, 700, 26], "REVENUE WON, LESS INVESTMENT",
            style=ts(T_SMALL, MIST, weight=600, spacing=2.0))
    p.add({"type": "text", "box": [MX, colY + 300, 1100, 120], "spans": [{"text": "≈ $27,800 / mo"}],
           "style": {"font_family": MONO, "font_size": 96, "font_weight": 500, "color": GOLD}})
    p.text([MX, colY + 430, 1100, 28],
            "Conservative, with your numbers — not ours. We’ll model your real job value and close rate on the call.",
            style=ts(T_BODY, MIST, italic=True))
    return p


# --------------------------------------------------------------------------- #
#  12 — FAQ (Bone): quiet two-column; gold only on the open-state marker       #
# --------------------------------------------------------------------------- #
def p_faq(b):
    p = _page(b, "p12-faq", dark=False)
    chrome(p, 12, dark=False)
    eyebrow(p, MX, MT, "Questions, answered plainly", color=BRONZE)
    head(p, MX, MT + 36, ["The honest answers."], size=T_H2, color=INK, w=1200)
    faqs = [
        ("“I’ve tried lead-gen before and got burned.”",
         "So have most of our clients. The difference is exclusivity and ownership: leads aren’t resold, and we own the path from ad to booked appointment — not just the click."),
        ("“How many appointments will I actually get?”",
         "We project it from your job value, area, and close rate on the call — then report the real cost-per-appointment monthly. No vague promises."),
        ("“I’m not tech-savvy.”",
         "That’s the point of done-for-you. We install and run the system. You show up to booked appointments and close them."),
        ("“What about my website and ad spend?”",
         "The system books appointments without leaning on your site. You set the ad budget and control it; we make every dollar accountable to booked work."),
    ]
    colGap = 80
    colW = (CW - colGap) / 2
    for i, (q, a) in enumerate(faqs):
        col = i % 2
        rowi = i // 2
        x = MX + col * (colW + colGap)
        y = MT + 200 + rowi * 250
        # open-state marker: the one gold accent
        p.line([x, y + 6], [x + 18, y + 6], stroke=GOLD, stroke_style={"stroke_width": 2.4})
        p.line([x + 9, y - 3], [x + 9, y + 15], stroke=GOLD, stroke_style={"stroke_width": 2.4})
        p.text([x + 40, y - 8, colW - 40, 60], q,
               style=ts(T_BODYL, INK, weight=600, family=SERIF, lh=1.25))
        body(p, x + 40, y + 56, colW - 40, a, size=T_BODY, color=BONE_SUB, lh=1.55, h=150)
    return p


# --------------------------------------------------------------------------- #
#  13 — Next steps / CTA (dark): seal, single gold button, contour converging  #
# --------------------------------------------------------------------------- #
def p_cta(b):
    p = _page(b, "p13-cta", dark=True)
    # contour motif converging toward the CTA point
    contour_field(p, W / 2, 470, rings=10, r0=80, dr=70, color=SLATE,
                  width=1.4, alpha=0.5, squish=0.62)
    seal(p, W / 2, 300, 92, disc=OBSIDIAN)
    # §5.13: gold is the button + seal; the master line stays Cloud.
    head(p, MX, 466, ["Claim your territory."], size=84, color=CLOUD, w=CW, align="center")
    p.text([(W - 1080) / 2, 604, 1080, 120],
            "A 30-minute call: we map your area, model your numbers, and confirm your "
            "territory is still open. No pitch theatre — just whether this fits.",
            style=ts(T_BODYL, MIST, lh=1.6, align="center"))
    # single gold primary button
    bw, bh = 320, 64
    bx, by = W / 2 - bw / 2, 720
    p.rect([bx, by, bw, bh], radius=10, fill=GOLD)
    p.text([bx, by, bw, bh], "Book the territory call",
            style=ts(T_BODY, OBSIDIAN, weight=700, align="center", valign="middle"))
    p.text([MX, by + bh + 28, CW, 24],
            f"One client per area — {CITY} is open today.",
            style=ts(T_SMALL, GOLD, weight=600, spacing=1.2, align="center"))
    return p


# --------------------------------------------------------------------------- #
#  14 — Back cover (dark)                                                       #
# --------------------------------------------------------------------------- #
def p_back(b):
    p = _page(b, "p14-back", dark=True)
    contour_field(p, W / 2, H / 2, rings=7, r0=140, dr=88, color=SLATE,
                  width=1.3, alpha=0.32, squish=0.7)
    seal(p, W / 2, 360, 110, disc=OBSIDIAN)
    runs(p, MX, 560, [("Your market. ", CLOUD), ("Claimed.", GOLD)],
         size=76, w=CW, align="center")
    rule(p, W / 2 - 80, 700, 160, color=GOLD, weight=2.0)
    p.add({"type": "text", "box": [0, 760, W, 30], "spans": [{"text": "SYRUS"}],
           "style": {"font_family": SERIF, "font_size": 24, "font_weight": 600,
                     "color": CLOUD, "letter_spacing": 4.0, "align": "center"}})
    p.text([MX, 800, CW, 22], "Client Acquisition for Contractors",
            style=ts(T_SMALL, MIST, weight=600, spacing=2.4, transform="uppercase", align="center"))
    p.text([MX, 880, CW, 22], "hello@syrus.co  ·  syrus.co  ·  Built for the trade",
            style=ts(T_SMALL, MIST, family=MONO, align="center", spacing=0.5))
    return p


# --------------------------------------------------------------------------- #
#  Assembly                                                                     #
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="SYRUS — Own Your Territory (Proposal)",
                        profile="deck", lang="en")
    for fn in (p_cover, p_reframe, p_stakes, p_newway, p_system, p_timeline,
               p_proof, p_why, p_offer, p_guarantee, p_roi, p_faq, p_cta, p_back):
        fn(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    rep = validate_static_rules(doc)
    errs = [i for i in rep.issues if i.severity == "error"]
    warns = [i for i in rep.issues if i.severity == "warning"]
    out_dir = os.path.join(ROOT, "out", "syrus")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "syrus-proposal.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"SYRUS proposal: {len(doc.pages)} pages, ok={rep.ok}, "
          f"errors={len(errs)}, warnings={len(warns)} -> {out}")
    for i in errs[:20]:
        print("  ERROR:", i.code, i.message)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
