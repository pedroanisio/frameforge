#!/usr/bin/env python3
"""Compose a COMPLETE low-fidelity wireframe of an advanced web app — "Helm", a
customer-service suite — with the FrameGraph Python SDK.

One composed deck, 36 pages — 34 desktop (1440×900) + 2 mobile (390×844):

  01 Sitemap / overview        13 Companies               25 Global search
  02 Sign in / SSO             14 Knowledge base          26 Billing & subscription
  03 Onboarding wizard         15 Article editor          27 Integrations marketplace
  04 Dashboard                 16 Reports / analytics     28 Audit log
  05 Inbox (conversations)     17 SLA & performance       29 Tags & custom fields
  06 Conversation detail       18 Automations             30 API keys & webhooks
  07 Tickets table             19 Automation builder      31 Help center (public)
  08 Ticket detail             20 Macros / canned replies 32 Help article (public)
  09 Live chat console         21 Team & agents           33 Customer portal
  10 AI Copilot                22 Roles & permissions     34 CSAT survey
  11 Customers list            23 Settings / channels     35 Mobile inbox
  12 Customer 360 profile      24 Notifications           36 Mobile conversation

Every page shares a sidebar + topbar shell and a small wireframe component
vocabulary (KPI tiles, data tables, charts via the SDK Chart helper, forms,
tabs, badges). Built end-to-end through the SDK: DocumentBuilder + PageBuilder
primitives, the row/column/grid/inset layout helpers, Chart/Frame, then
validate_static_rules and serialize().

Run from the repository root::

    uv run python examples/cs_suite_wireframe.py    # build, validate, write the fixture
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    Chart,
    DocumentBuilder,
    Frame,
    PageBuilder,
    column,
    grid,
    inset,
    row,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# ---- frame + palette ------------------------------------------------------ #
W, H = 1440, 900
SB = 240            # sidebar width
TB = 56             # topbar height
PAD = 28            # content padding
DESK = {"size": [W, H], "units": "px"}
CONTENT = [SB + PAD, TB + PAD, W - SB - 2 * PAD, H - TB - 2 * PAD]   # main work area

COLORS = {
    "paper":   "#FFFFFF",
    "canvas":  "#F4F6F9",
    "sidebar": "#FbFcFe",
    "ink":     "#1D2430",
    "sub":     "#56607A",
    "muted":   "#8A93A3",
    "fill":    "#EEF1F5",
    "fill2":   "#E3E7EE",
    "rowalt":  "#F8FAFC",
    "line":    "#D7DCE4",
    "bar":     "#C6CCD6",
    "barlt":   "#DCE0E7",
    "accent":  "#2563EB",
    "accSft":  "#E6EEFC",
    "good":    "#1F9254", "goodSft": "#E2F3E9",
    "warn":    "#B7791F", "warnSft": "#FBF0DA",
    "bad":     "#C23B3B", "badSft":  "#FBE6E6",
    "stage":   "#EEF1F6",
}

SANS = ["Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["SFMono-Regular", "Menlo", "monospace"]


def ts(size, weight=400, color="ink", **kw):
    return dict(font_family=SANS, font_size=size, font_weight=weight, color=color, **kw)


STYLES = {
    "logo":    ts(17, 800, "ink", letter_spacing=-0.3),
    "navsec":  dict(font_family=SANS, font_size=10, font_weight=700, color="muted",
                    letter_spacing=1.5, text_transform="uppercase"),
    "nav":     ts(13, 600, "sub"),
    "navA":    ts(13, 700, "accent"),
    "crumb":   ts(13, 600, "muted"),
    "h1":      ts(22, 800, "ink", letter_spacing=-0.4),
    "h2":      ts(15, 700, "ink"),
    "h3":      ts(13, 700, "ink"),
    "sub":     ts(13, 400, "sub", line_height=1.5),
    "lbl":     dict(font_family=SANS, font_size=11, font_weight=700, color="muted",
                    letter_spacing=0.6, text_transform="uppercase"),
    "body":    ts(13, 400, "sub", line_height=1.5),
    "mut":     ts(12, 400, "muted"),
    "th":      dict(font_family=SANS, font_size=11, font_weight=700, color="sub",
                    letter_spacing=0.4, text_transform="uppercase"),
    "td":      ts(13, 500, "ink"),
    "tdSub":   ts(12, 400, "muted"),
    "id":      dict(font_family=MONO, font_size=12, color="sub"),
    "kpi":     ts(30, 800, "ink", letter_spacing=-1),
    "btn":     ts(13, 700, "paper", align="center"),
    "btnG":    ts(13, 700, "sub", align="center"),
    "btnA":    ts(13, 700, "accent", align="center"),
    "chip":    ts(12, 600, "sub"),
    "chipA":   ts(12, 700, "accent"),
    "badge":   ts(11, 700, "sub", align="center"),
    "place":   ts(13, 400, "muted"),
    "glyph":   ts(14, 700, "muted", align="center"),
    "glyphW":  ts(14, 800, "paper", align="center"),
    "ava":     ts(12, 700, "sub", align="center"),
    "tab":     ts(13, 600, "muted"),
    "tabA":    ts(13, 700, "ink"),
    "metric":  ts(13, 700, "ink"),
    "delta":   ts(12, 700, "good"),
    "deltaD":  ts(12, 700, "bad"),
    "annot":   dict(font_family=MONO, font_size=10, color="muted", line_height=1.45),
    # sitemap
    "deckH":   ts(32, 800, "ink", letter_spacing=-1),
    "deckSub": ts(14, 400, "sub", line_height=1.5),
    "node":    ts(12, 600, "sub"),
    "nodeH":   ts(12, 800, "ink"),
    "flow":    dict(font_family=MONO, font_size=10, color="muted"),
    # auth
    "authH":   ts(26, 800, "ink", letter_spacing=-0.6, align="center"),
    "authSub": ts(13, 400, "sub", align="center", line_height=1.5),
    # public help center + mobile companion
    "status":  ts(12, 700, "ink"),
    "phoneH":  ts(19, 800, "ink", letter_spacing=-0.3),
    "heroH":   ts(30, 800, "ink", align="center", letter_spacing=-0.6),
    "heroSub": ts(14, 400, "sub", align="center", line_height=1.5),
    "link":    ts(13, 600, "accent"),
    "seg":     ts(13, 600, "muted", align="center"),
    "segA":    ts(13, 700, "ink", align="center"),
    "cardH":   ts(20, 800, "ink", align="center", letter_spacing=-0.3),
}

PHONE = {"size": [390, 844], "units": "px"}
PW, PH = 390, 844
PUB_W = 1080
PUB_X = (W - PUB_W) / 2

HAIR = {"stroke_width": 1.0}
DASH = {"stroke_width": 1.1, "stroke_dasharray": [4, 3]}

# nav model — (section, [(label, screen-key)])
NAV = [
    ("Support", [("Dashboard", "dashboard"), ("Inbox", "inbox"),
                 ("Tickets", "tickets"), ("Live chat", "livechat"),
                 ("AI Copilot", "copilot")]),
    ("Customers", [("Customers", "customers"), ("Companies", "companies")]),
    ("Content", [("Knowledge base", "kb")]),
    ("Insights", [("Reports", "reports"), ("SLA & SLO", "sla")]),
    ("Automate", [("Automations", "automations"), ("Macros", "macros")]),
    ("Admin", [("Team", "team"), ("Roles", "roles"), ("Settings", "settings")]),
]


# ======================================================================= #
#  component vocabulary
# ======================================================================= #
def bars(page, box, n=3, gap=8, h=8, last=0.6, color="bar", radius=4):
    x, y, w, _ = box
    cy = y
    for i in range(n):
        bw = w * (last if i == n - 1 else 1.0)
        page.rect([x, cy, bw, h], fill=color, radius=radius)
        cy += h + gap


def ghost(page, box, label=None, radius=10, fill="fill"):
    page.rect(box, fill=fill, stroke="line", stroke_style=DASH, radius=radius)
    if label is not None:
        x, y, w, h = box
        page.text([x, y + h / 2 - 9, w, 18], label, style="glyph")


def card(page, box, *, title=None, action=None, pad=18, fill="paper"):
    page.rect(box, fill=fill, stroke="line", stroke_style=HAIR, radius=12)
    x, y, w, h = box
    inner = inset(box, pad)
    if title is not None:
        page.text([inner[0], inner[1], inner[2] - 80, 18], title, style="h2")
        if action is not None:
            page.text([x + w - pad - 80, inner[1] + 1, 80, 16], action, style="chipA")
        return [inner[0], inner[1] + 30, inner[2], inner[3] - 30]
    return inner


def pill(page, box, text=None, *, fill="fill", style="chip", stroke=None, radius=None,
         pad=12):
    x, y, w, h = box
    r = radius if radius is not None else h / 2
    kw = {"fill": fill, "radius": r}
    if stroke:
        kw["stroke"] = stroke
        kw["stroke_style"] = HAIR
    page.rect(box, **kw)
    if text is not None:
        page.text([x + pad, y + h / 2 - 8, w - 2 * pad, 16], text, style=style)


def button(page, box, label, kind="primary"):
    if kind == "primary":
        pill(page, box, None, fill="accent", radius=8)
        st = "btn"
    elif kind == "ghost":
        pill(page, box, None, fill="paper", stroke="line", radius=8)
        st = "btnG"
    else:
        pill(page, box, None, fill="fill", radius=8)
        st = "btnG"
    x, y, w, h = box
    page.text([x, y + h / 2 - 8, w, 16], label, style=st)


def icon(page, box, glyph="▢", *, fill="fill", style="glyph", radius=8):
    x, y, w, h = box
    page.rect(box, fill=fill, radius=radius)
    page.text([x, y + h / 2 - 9, w, 18], glyph, style=style)


def circle(page, cx, cy, r, *, fill="fill", stroke=None, dash=False):
    kw = {"fill": fill, "radius": r}
    if stroke:
        kw["stroke"] = stroke
        kw["stroke_style"] = DASH if dash else HAIR
    page.rect([cx - r, cy - r, 2 * r, 2 * r], **kw)


def avatar(page, cx, cy, r, initials=None, *, fill="fill2"):
    circle(page, cx, cy, r, fill=fill, stroke="line")
    if initials:
        page.text([cx - r, cy - 7, 2 * r, 14], initials, style="ava")


_TONE = {"good": ("goodSft", "good"), "warn": ("warnSft", "warn"),
         "bad": ("badSft", "bad"), "accent": ("accSft", "accent"),
         "muted": ("fill", "sub")}


def badge(page, box, text, tone="muted"):
    bg, fg = _TONE.get(tone, _TONE["muted"])
    x, y, w, h = box
    page.rect(box, fill=bg, radius=h / 2)
    page.text([x, y + h / 2 - 7, w, 14], text, style=dict(
        font_family=SANS, font_size=11, font_weight=700, color=fg, align="center"))


def tabs(page, box, items, active=0):
    x, y, w, h = box
    page.rect([x, y + h - 1, w, 1], fill="line")
    cx = x
    for i, label in enumerate(items):
        tw = 24 + len(label) * 7.5
        st = "tabA" if i == active else "tab"
        page.text([cx, y + h / 2 - 8, tw, 16], label, style=st)
        if i == active:
            page.rect([cx, y + h - 2, tw - 18, 2], fill="accent", radius=1)
        cx += tw + 8


def field(page, box, label, value="", *, kind="input"):
    x, y, w, h = box
    page.text([x, y, w, 14], label, style="lbl")
    inp = [x, y + 18, w, h - 18]
    if kind == "area":
        page.rect(inp, fill="paper", stroke="line", stroke_style=HAIR, radius=8)
        bars(page, [x + 12, y + 30, w - 24, 0], n=2, gap=8, h=8, last=0.6, color="barlt")
    elif kind == "select":
        page.rect(inp, fill="paper", stroke="line", stroke_style=HAIR, radius=8)
        page.text([x + 12, y + 18 + (h - 18) / 2 - 8, w - 40, 16],
                  value or "Select…", style="td" if value else "place")
        page.text([x + w - 24, y + 18 + (h - 18) / 2 - 8, 16, 16], "▾", style="glyph")
    else:
        page.rect(inp, fill="paper", stroke="line", stroke_style=HAIR, radius=8)
        page.text([x + 12, y + 18 + (h - 18) / 2 - 8, w - 24, 16],
                  value or "", style="td" if value else "place")


def toggle(page, x, cy, on=True):
    pill(page, [x, cy - 11, 40, 22], None, fill="accent" if on else "fill2", radius=11)
    circle(page, x + (29 if on else 11), cy, 8, fill="paper")


def kpi(page, box, label, value, delta=None, down=False):
    inner = card(page, box, pad=18)
    x, y, w, _ = inner
    page.text([x, y, w, 14], label, style="lbl")
    page.text([x, y + 18, w, 36], value, style="kpi")
    if delta is not None:
        page.text([x, y + 58, w, 16], delta, style="deltaD" if down else "delta")


def table(page, box, cols, rows, *, head_h=40, row_h=46, zebra=True):
    """cols: list of {label, w, kind}. kind in text/sub/id/badge/avatar/bars/right/mut."""
    x, y, w, h = box
    weights = [c.get("w", 1) for c in cols]
    page.rect([x, y, w, head_h], fill="fill", radius=8)
    hcols = row([x, y, w, head_h], weights=weights)
    for c, cb in zip(cols, hcols):
        page.text([cb[0] + 14, y + head_h / 2 - 7, cb[2] - 18, 14], c["label"], style="th")
    cy = y + head_h
    for ri, rdata in enumerate(rows):
        if zebra and ri % 2 == 1:
            page.rect([x, cy, w, row_h], fill="rowalt")
        page.rect([x, cy + row_h - 1, w, 1], fill="line")
        rcols = row([x, cy, w, row_h], weights=weights)
        for c, cb, val in zip(cols, rcols, rdata):
            _cell(page, cb, val, c.get("kind", "text"), row_h)
        cy += row_h
    return cy


def _cell(page, cb, val, kind, row_h):
    cx, cy, cw, _ = cb
    mid = cy + row_h / 2
    px = cx + 14
    if kind == "badge":
        text, tone = val if isinstance(val, tuple) else (val, "muted")
        badge(page, [px, mid - 11, 18 + len(text) * 7, 22], text, tone)
    elif kind == "avatar":
        avatar(page, px + 14, mid, 14, _initials(val))
        page.text([px + 36, mid - 8, cw - 50, 16], val, style="td")
    elif kind == "id":
        page.text([px, mid - 8, cw - 18, 16], val, style="id")
    elif kind == "sub":
        page.text([px, mid - 8, cw - 18, 16], val, style="tdSub")
    elif kind == "right":
        page.text([cx, mid - 8, cw - 18, 16], val,
                  style=dict(font_family=SANS, font_size=13, font_weight=700,
                             color="ink", align="right"))
    elif kind == "bars":
        page.rect([px, mid - 4, (cw - 28) * float(val), 8], fill="accent", radius=4)
        page.rect([px, mid - 4, cw - 28, 8], fill="fill", radius=4)
        page.rect([px, mid - 4, (cw - 28) * float(val), 8], fill="accent", radius=4)
    elif kind == "mut":
        page.text([px, mid - 8, cw - 18, 16], val, style="mut")
    elif kind == "icon":
        page.text([cx, mid - 9, cw - 14, 18], val, style="glyph")
    else:
        page.text([px, mid - 8, cw - 18, 16], val, style="td")


def _initials(name):
    parts = [p for p in name.replace("·", " ").split() if p[:1].isalnum()]
    return (parts[0][:1] + (parts[1][:1] if len(parts) > 1 else "")).upper() if parts else "•"


def annotate(page, x, y, text):
    page.text([x, y, W - x - 28, 40], text, style="annot")


# ======================================================================= #
#  shell (sidebar + topbar)
# ======================================================================= #
def shell(b, sid, active, title, crumb=None, actions=None) -> tuple[PageBuilder, list]:
    page = b.page(sid, canvas=DESK, coordinate_mode="absolute").layer("chrome")
    page.rect([0, 0, W, H], fill="canvas")

    # sidebar
    page.rect([0, 0, SB, H], fill="sidebar")
    page.rect([SB - 1, 0, 1, H], fill="line")
    icon(page, [20, 18, 24, 24], "◆", fill="accent", style="glyphW", radius=7)
    page.text([54, 24, 150, 20], "Helm", style="logo")
    badge(page, [104, 25, 46, 18], "SUITE", "accent")

    y = 72
    for sec, items in NAV:
        page.text([20, y, SB - 40, 12], sec, style="navsec")
        y += 22
        for label, key in items:
            if key == active:
                page.rect([12, y - 6, SB - 24, 32], fill="accSft", radius=8)
                page.rect([12, y - 6, 3, 32], fill="accent", radius=2)
            page.rect([22, y + 2, 14, 14], fill="bar" if key != active else "accent",
                      radius=4)
            page.text([48, y + 1, SB - 70, 16], label,
                      style="navA" if key == active else "nav")
            y += 32
        y += 12

    # sidebar footer — current agent
    page.rect([12, H - 60, SB - 24, 44], fill="fill", radius=10)
    avatar(page, 36, H - 38, 15, "PA")
    page.text([60, H - 46, 120, 14], "Pedro A.", style="h3")
    page.text([60, H - 30, 140, 12], "Admin · Online", style="mut")

    # topbar
    page.rect([SB, 0, W - SB, TB], fill="paper")
    page.rect([SB, TB - 1, W - SB, 1], fill="line")
    page.text([SB + PAD, TB / 2 - 8, 360, 16],
              crumb or title, style="crumb")
    # global search
    sx = SB + 360
    pill(page, [sx, TB / 2 - 17, 380, 34], None, fill="canvas", stroke="line", radius=8)
    page.text([sx + 14, TB / 2 - 8, 200, 16], "⌕  Search tickets, people…",
              style="place")
    # right actions
    rx = W - PAD - 32
    for g in ("◔", "⌗", "✉"):
        icon(page, [rx, TB / 2 - 16, 32, 32], g, fill="canvas")
        rx -= 40
    avatar(page, W - PAD - 32 - 3 * 40 - 4, TB / 2, 15, "PA")

    page.layer("main")
    # page title block
    page.text([CONTENT[0], 78, 700, 28], title, style="h1")
    if actions:
        ax = W - PAD
        for label, kind in reversed(actions):
            bw = 30 + len(label) * 8
            ax -= bw
            button(page, [ax, 80, bw, 36], label, kind)
            ax -= 10
    return page, [CONTENT[0], 130, CONTENT[2], H - 130 - PAD]


# ======================================================================= #
#  01 — sitemap / overview
# ======================================================================= #
def sitemap(b):
    SH = 1060
    page = b.page("sitemap", canvas={"size": [W, SH], "units": "px"},
                  coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, SH], fill="stage")
    page.rect([0, 0, W, 8], fill="accent")
    page.layer("head")
    page.text([56, 44, 900, 40], "Helm — Customer Service Suite", style="deckH")
    page.text([56, 90, 1040, 44],
              "Complete web-app wireframe · 36 screens · low-fidelity sitemap. "
              "Authored end-to-end with the FrameGraph SDK and rendered to SVG.",
              style="deckSub")
    pill(page, [56, 146, 160, 26], "v0.2 · WIREFRAME", fill="accSft", style="chipA")
    pill(page, [224, 146, 130, 26], "1440 × 900", fill="fill", style="chip")
    pill(page, [362, 146, 150, 26], "+ mobile · public", fill="fill", style="chip")

    # groups distributed across four balanced columns
    columns = [
        [("Entry", ["02 · Sign in / SSO", "03 · Onboarding wizard"]),
         ("Overview", ["04 · Dashboard"]),
         ("Support desk", ["05 · Inbox", "06 · Conversation", "07 · Tickets",
                           "08 · Ticket detail", "09 · Live chat", "10 · AI Copilot"])],
        [("Customers", ["11 · Customers", "12 · Customer 360", "13 · Companies"]),
         ("Knowledge", ["14 · Knowledge base", "15 · Article editor"]),
         ("Insights", ["16 · Reports", "17 · SLA & performance"]),
         ("System", ["24 · Notifications", "25 · Global search"])],
        [("Automate", ["18 · Automations", "19 · Flow builder", "20 · Macros"]),
         ("Admin", ["21 · Team", "22 · Roles & perms", "23 · Settings",
                    "26 · Billing", "27 · Integrations", "28 · Audit log",
                    "29 · Tags & fields", "30 · API & webhooks"])],
        [("Customer-facing", ["31 · Help center", "32 · Help article",
                              "33 · Customer portal", "34 · CSAT survey"]),
         ("Mobile agent app", ["35 · Mobile inbox", "36 · Mobile conversation"])],
    ]
    page.layer("nodes")
    col_boxes = row([56, 206, W - 112, 800], count=4, gap=24)
    for col, cbox in zip(columns, col_boxes):
        cx, cyy, cw, _ = cbox
        gy = cyy
        for gname, items in col:
            gh = 40 + len(items) * 36 + 12
            page.rect([cx, gy, cw, gh], fill="paper", stroke="line",
                      stroke_style=HAIR, radius=14)
            page.rect([cx, gy, cw, 30], fill="fill", radius=14)
            page.rect([cx, gy + 16, cw, 24], fill="fill")    # square lower corners
            page.text([cx + 16, gy + 13, cw - 32, 16], gname, style="nodeH")
            iy = gy + 50
            for it in items:
                page.rect([cx + 12, iy, cw - 24, 28], fill="canvas", stroke="line",
                          stroke_style=HAIR, radius=7)
                page.rect([cx + 22, iy + 8, 12, 12], fill="accent", radius=3)
                page.text([cx + 42, iy + 7, cw - 60, 14], it, style="node")
                iy += 36
            gy += gh + 16
    page.text([56, SH - 34, 1100, 16],
              "FrameGraph SDK · shared sidebar/topbar shell · public + mobile shells · "
              "tables · Chart helper · one composed document", style="flow")


# ======================================================================= #
#  02 — sign in
# ======================================================================= #
def signin(b):
    page = b.page("signin", canvas=DESK, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")
    # left brand panel
    page.rect([0, 0, W * 0.5, H], fill="accSft")
    icon(page, [120, 110, 44, 44], "◆", fill="accent", style="glyphW", radius=12)
    page.text([176, 122, 200, 24], "Helm", style="logo")
    page.text([120, 300, 520, 40], "The support desk", style="deckH")
    page.text([120, 344, 520, 40], "your customers deserve.", style="deckH")
    bars(page, [120, 410, 460, 0], n=3, gap=12, h=10, last=0.5, color="barlt")
    for i, t in enumerate(["Omnichannel inbox", "SLA automation", "AI copilot"]):
        cy = 500 + i * 40
        circle(page, 130, cy, 8, fill="paper", stroke="accent")
        page.text([150, cy - 8, 300, 16], t, style="body")

    # right form
    cardbox = [W * 0.5 + 150, 230, 360, 440]
    page.rect(cardbox, fill="paper", stroke="line", stroke_style=HAIR, radius=16)
    cx, cy, cw, _ = inset(cardbox, 34)
    page.text([cx, cy, cw, 28], "Welcome back", style="authH")
    page.text([cx, cy + 34, cw, 18], "Sign in to your workspace", style="authSub")
    field(page, [cx, cy + 74, cw, 58], "Work email", "agent@acme.com")
    field(page, [cx, cy + 146, cw, 58], "Password", "••••••••")
    page.text([cx + cw - 110, cy + 210, 110, 14], "Forgot password?", style="chipA")
    button(page, [cx, cy + 234, cw, 44], "Sign in", "primary")
    page.rect([cx, cy + 300, cw, 1], fill="line")
    page.text([cx + cw / 2 - 20, cy + 292, 40, 16], "or", style="mut")
    button(page, [cx, cy + 318, cw, 42], "Continue with SSO", "ghost")


# ======================================================================= #
#  03 — onboarding wizard
# ======================================================================= #
def onboarding(b):
    page = b.page("onboarding", canvas=DESK, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")
    icon(page, [40, 30, 30, 30], "◆", fill="accent", style="glyphW", radius=8)
    page.text([80, 36, 150, 20], "Helm", style="logo")
    page.text([W - 160, 38, 130, 16], "Step 2 of 4", style="mut")

    # stepper
    steps = ["Workspace", "Channels", "Team", "Done"]
    sx = W / 2 - 280
    for i, s in enumerate(steps):
        cx = sx + i * 186
        done = i < 1
        cur = i == 1
        circle(page, cx, 110, 16, fill="accent" if (done or cur) else "fill",
               stroke="line")
        page.text([cx - 16, 103, 32, 16], "✓" if done else str(i + 1),
                  style="glyphW" if (done or cur) else "glyph")
        page.text([cx - 50, 136, 100, 14], s,
                  style="h3" if cur else "mut")
        if i < len(steps) - 1:
            page.rect([cx + 22, 108, 142, 3], fill="accent" if done else "fill")

    # form card
    cb = [W / 2 - 320, 200, 640, 520]
    page.rect(cb, fill="paper", stroke="line", stroke_style=HAIR, radius=16)
    cx, cy, cw, _ = inset(cb, 40)
    page.text([cx, cy, cw, 26], "Connect your channels", style="h1")
    page.text([cx, cy + 32, cw, 18],
              "Pick where your customers reach you. You can add more later.",
              style="sub")
    chans = [("✉", "Email"), ("◍", "Live chat"), ("☏", "Voice"),
             ("◐", "Messaging"), ("⌥", "Social"), ("◇", "API")]
    for (g, name), cellbox in zip(chans, grid([cx, cy + 76, cw, 250], cols=3, rows=2,
                                              gap=16, row_gap=16)):
        page.rect(cellbox, fill="canvas", stroke="line", stroke_style=HAIR, radius=12)
        ix, iy, iw, _ = inset(cellbox, 16)
        icon(page, [ix, iy, 34, 34], g, fill="paper")
        page.text([ix + 44, iy + 2, iw - 60, 16], name, style="h3")
        page.text([ix + 44, iy + 20, iw - 60, 14], "Connect", style="chipA")
        circle(page, cellbox[0] + cellbox[2] - 24, iy + 14, 9, fill="fill",
               stroke="line")
    button(page, [cx, cy + 360, 140, 44], "Continue", "primary")
    button(page, [cx + 152, cy + 360, 90, 44], "Skip", "ghost")


# ======================================================================= #
#  04 — dashboard
# ======================================================================= #
def dashboard(b):
    page, area = shell(b, "dashboard", "dashboard", "Good morning, Pedro",
                       crumb="Support · Dashboard",
                       actions=[("Export", "ghost"), ("New ticket", "primary")])
    x, y, w, _ = area

    # KPI row
    kpis = [("Open tickets", "248", "▲ 12 today", False),
            ("Avg first reply", "1h 42m", "▼ 8% vs last wk", False),
            ("CSAT", "94%", "▲ 2 pts", False),
            ("Backlog > 24h", "31", "▲ 5 overdue", True)]
    for (lbl, val, d, down), bx in zip(kpis, row([x, y, w, 110], count=4, gap=18)):
        kpi(page, bx, lbl, val, d, down)

    # main charts row
    top = y + 130
    left, right = row([x, top, w, 280], gap=18, weights=[1.7, 1])
    inner = card(page, left, title="Ticket volume — last 14 days", action="Details ▾")
    fr = Frame(domain=(0, 0, 13, 320), box=(inner[0] + 40, inner[1] + 6,
                                            inner[2] - 50, inner[3] - 36))
    vol = [120, 160, 140, 200, 240, 180, 90, 70, 210, 260, 230, 250, 300, 280]
    res = [v - 30 - (i % 3) * 12 for i, v in enumerate(vol)]
    ch = (Chart(fr)
          .axes(x_ticks=[0, 3, 6, 9, 12], y_ticks=[0, 100, 200, 300],
                x_format=lambda v: f"D{int(v) + 1}", y_format=lambda v: f"{int(v)}",
                grid=True)
          .bars([(i, v) for i, v in enumerate(vol)], width=18, fill="accSft",
                radius=3, label="received")
          .line([(i, v) for i, v in enumerate(res)], stroke="accent", width=2.4,
                smooth=True, label="resolved")
          .legend(at="tl"))
    page.extend(ch.objects())

    inner = card(page, right, title="By channel")
    chans = [("Email", 0.46, "good"), ("Chat", 0.28, "accent"),
             ("Voice", 0.14, "warn"), ("Social", 0.12, "muted")]
    ry = inner[1] + 6
    for name, frac, tone in chans:
        page.text([inner[0], ry, 120, 14], name, style="td")
        page.text([inner[0] + inner[2] - 40, ry, 40, 14],
                  f"{int(frac * 100)}%", style="metric")
        page.rect([inner[0], ry + 20, inner[2], 8], fill="fill", radius=4)
        page.rect([inner[0], ry + 20, inner[2] * frac, 8],
                  fill=_TONE.get(tone, _TONE["muted"])[1], radius=4)
        ry += 50

    # bottom: recent tickets + team status
    bot = top + 300
    lt, rt = row([x, bot, w, area[3] - (bot - y) + y - 0], gap=18, weights=[2, 1])
    lt = [lt[0], lt[1], lt[2], H - PAD - bot]
    rt = [rt[0], rt[1], rt[2], H - PAD - bot]
    inner = card(page, lt, title="Needs attention", action="View inbox")
    cols = [{"label": "Subject", "w": 2.4}, {"label": "Customer", "w": 1.6, "kind": "avatar"},
            {"label": "Priority", "w": 1, "kind": "badge"},
            {"label": "SLA", "w": 1, "kind": "badge"}]
    data = [["Refund not received", "Jane Cooper", ("Urgent", "bad"), ("Breached", "bad")],
            ["Can't reset password", "Cody Fisher", ("High", "warn"), ("28m left", "warn")],
            ["Feature request: export", "Esther H.", ("Low", "muted"), ("On track", "good")],
            ["Double charged", "Marvin M.", ("High", "warn"), ("1h left", "good")]]
    table(page, [inner[0], inner[1] + 4, inner[2], inner[3] - 4], cols, data, row_h=42)

    inner = card(page, rt, title="Team status")
    agents = [("Ava N.", "12 open", "good"), ("Leo K.", "9 open", "good"),
              ("Mia R.", "Away", "warn"), ("Sam T.", "Offline", "muted")]
    ay = inner[1] + 4
    for name, st, tone in agents:
        avatar(page, inner[0] + 16, ay + 16, 15, _initials(name))
        page.text([inner[0] + 40, ay + 6, inner[2] - 100, 16], name, style="td")
        page.text([inner[0] + 40, ay + 22, 120, 14], st, style="mut")
        circle(page, inner[0] + inner[2] - 12, ay + 16, 5,
               fill=_TONE.get(tone, _TONE["muted"])[1])
        ay += 44


# ======================================================================= #
#  05 — inbox
# ======================================================================= #
def inbox(b):
    page, area = shell(b, "inbox", "inbox", "Inbox",
                       crumb="Support · Inbox",
                       actions=[("Filters", "ghost"), ("Compose", "primary")])
    x, y, w, h = area
    nav, listcol, preview = (row([x, y, w, h], gap=16, weights=[0.9, 1.6, 2.2]))

    # saved views
    page.rect(nav, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    nx, ny, nw, _ = inset(nav, 14)
    page.text([nx, ny, nw, 14], "VIEWS", style="lbl")
    views = [("All open", "248", True), ("Unassigned", "37", False),
             ("Mentions", "5", False), ("Assigned to me", "12", False),
             ("Breached SLA", "9", False), ("Closed", "1.2k", False)]
    vy = ny + 26
    for name, n, act in views:
        if act:
            page.rect([nx - 4, vy - 4, nw + 8, 30], fill="accSft", radius=8)
        page.text([nx + 4, vy + 3, nw - 50, 16], name, style="navA" if act else "nav")
        page.text([nx + nw - 40, vy + 3, 40, 16], n,
                  style="chipA" if act else "mut")
        vy += 34
    page.rect([nx, vy + 6, nw, 1], fill="line")
    page.text([nx, vy + 18, nw, 14], "TAGS", style="lbl")
    for i, t in enumerate(["billing", "bug", "onboarding", "vip"]):
        pill(page, [nx, vy + 42 + i * 32, nw, 26], "# " + t, fill="fill", style="chip")

    # conversation list
    page.rect(listcol, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    lx, ly, lw, _ = inset(listcol, 0)
    pill(page, [lx + 12, ly + 12, lw - 24, 32], "⌕  Search this view",
         fill="canvas", stroke="line", style="place", radius=8)
    items = [
        ("Jane Cooper", "Refund not received", "Urgent", "bad", "2m", True),
        ("Cody Fisher", "Re: password reset link", "High", "warn", "14m", False),
        ("Esther Howard", "Export to CSV?", "Low", "muted", "1h", False),
        ("Marvin McKinney", "Double charged this month", "High", "warn", "1h", False),
        ("Brooklyn S.", "Loving the new dashboard!", "Low", "good", "3h", False),
        ("Wade Warren", "API returns 500 on sync", "Urgent", "bad", "4h", False),
        ("Floyd Miles", "Cancel my subscription", "Med", "warn", "5h", False),
    ]
    iy = ly + 56
    for name, subj, pr, tone, t, active in items:
        if active:
            page.rect([lx + 6, iy, lw - 12, 66], fill="accSft", radius=8)
            page.rect([lx + 6, iy, 3, 66], fill="accent", radius=2)
        avatar(page, lx + 28, iy + 22, 15, _initials(name))
        page.text([lx + 52, iy + 8, lw - 120, 16], name, style="h3")
        page.text([lx + lw - 50, iy + 9, 40, 14], t, style="mut")
        page.text([lx + 52, iy + 27, lw - 80, 16], subj, style="tdSub")
        badge(page, [lx + 52, iy + 46, 18 + len(pr) * 7, 18], pr, tone)
        page.rect([lx + 12, iy + 66, lw - 24, 1], fill="line")
        iy += 74

    # preview pane
    page.rect(preview, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    _thread_preview(page, inset(preview, 0))


def _thread_preview(page, box):
    x, y, w, h = box
    # header
    page.rect([x, y, w, 60], fill="paper")
    avatar(page, x + 30, y + 30, 17, "JC")
    page.text([x + 58, y + 14, 300, 18], "Jane Cooper", style="h2")
    page.text([x + 58, y + 36, 300, 14], "jane@globex.com · #4821", style="mut")
    badge(page, [x + w - 150, y + 20, 70, 22], "Urgent", "bad")
    icon(page, [x + w - 70, y + 18, 28, 28], "⋯", fill="canvas")
    page.rect([x, y + 60, w, 1], fill="line")
    # messages
    my = y + 80
    page.rect([x + 16, my, w * 0.62, 70], fill="fill", radius=12)
    bars(page, [x + 30, my + 14, w * 0.62 - 28, 0], n=3, gap=8, h=8, last=0.5)
    my += 86
    rw = w * 0.6
    page.rect([x + w - 16 - rw, my, rw, 56], fill="accSft", radius=12)
    bars(page, [x + w - 30 - rw + 14, my + 12, rw - 28, 0], n=2, gap=8, h=8,
         last=0.6, color="accent")
    my += 72
    # AI suggestion card
    page.rect([x + 16, my, w - 32, 52], fill="paper", stroke="accent",
              stroke_style=DASH, radius=10)
    icon(page, [x + 28, my + 12, 28, 28], "✦", fill="accSft", style="chipA")
    page.text([x + 66, my + 11, 200, 14], "Copilot suggests a reply", style="h3")
    page.text([x + 66, my + 29, 260, 13], "Refund policy · ETA 3–5 days", style="mut")
    pill(page, [x + w - 110, my + 13, 80, 26], "Insert", fill="accent", style="btn")
    # composer
    cy = y + h - 92
    page.rect([x + 16, cy, w - 32, 76], fill="canvas", stroke="line",
              stroke_style=HAIR, radius=10)
    page.text([x + 30, cy + 14, w - 60, 14], "Reply to Jane…", style="place")
    for i, g in enumerate(("B", "I", "🔗", "@", "✦")):
        icon(page, [x + 28 + i * 34, cy + 40, 28, 24], g, fill="paper")
    button(page, [x + w - 110, cy + 38, 80, 28], "Send", "primary")


# ======================================================================= #
#  06 — conversation detail
# ======================================================================= #
def conversation(b):
    page, area = shell(b, "conversation", "inbox", "Refund not received",
                       crumb="Inbox · #4821",
                       actions=[("Close", "ghost"), ("Resolve", "primary")])
    x, y, w, h = area
    thread, side = row([x, y, w, h], gap=16, weights=[2.4, 1])

    page.rect(thread, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    tx, ty, tw, _ = inset(thread, 0)
    tabs(page, [tx + 16, ty + 8, tw - 32, 36],
         ["Conversation", "Internal notes", "Activity"], active=0)
    my = ty + 64
    msgs = [("in", 3, "JC"), ("out", 2, "PA"), ("in", 2, "JC"), ("note", 2, None),
            ("out", 3, "PA")]
    for kind, n, who in msgs:
        if kind == "note":
            page.rect([tx + 60, my, tw - 120, 24 + n * 16],
                      fill="warnSft", radius=10)
            page.text([tx + 74, my + 8, 120, 13], "🔒 Internal note", style="mut")
            bars(page, [tx + 74, my + 26, tw - 160, 0], n=n - 1, gap=7, h=7,
                 last=0.5, color="barlt")
            my += 24 + n * 16 + 14
            continue
        out = kind == "out"
        bw = tw * (0.6 if out else 0.66)
        bx = tx + tw - 16 - bw if out else tx + 16
        avatar(page, (bx + bw + 18) if out else (bx - 2), my + 14, 14, who)
        page.rect([bx, my, bw, 24 + n * 16], fill="accSft" if out else "fill",
                  radius=12)
        bars(page, [bx + 16, my + 14, bw - 32, 0], n=n, gap=8, h=8, last=0.5,
             color="accent" if out else "bar")
        my += 24 + n * 16 + 18

    # composer
    cy = ty + thread[3] - 96
    page.rect([tx + 16, cy, tw - 32, 80], fill="canvas", stroke="line",
              stroke_style=HAIR, radius=10)
    page.text([tx + 30, cy + 14, 200, 14], "Write a reply…  (/ for macros)",
              style="place")
    pill(page, [tx + 30, cy + 44, 110, 26], "✦ Ask Copilot", fill="accSft",
         style="chipA")
    button(page, [tx + tw - 120, cy + 42, 90, 30], "Send", "primary")

    # customer side panel
    page.rect(side, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    sx, sy, sw, _ = inset(side, 18)
    avatar(page, sx + 22, sy + 22, 22, "JC")
    page.text([sx + 56, sy + 8, sw - 56, 18], "Jane Cooper", style="h2")
    page.text([sx + 56, sy + 30, sw - 56, 14], "globex.com · VIP", style="chipA")
    page.rect([sx, sy + 64, sw, 1], fill="line")
    facts = [("Email", "jane@globex.com"), ("Plan", "Business · $499/mo"),
             ("Customer since", "Mar 2023"), ("Open tickets", "3"),
             ("Lifetime value", "$11,400")]
    fy = sy + 78
    for k, v in facts:
        page.text([sx, fy, sw * 0.5, 14], k, style="mut")
        page.text([sx + sw * 0.45, fy, sw * 0.55, 14], v,
                  style=dict(font_family=SANS, font_size=12, font_weight=600,
                             color="ink", align="right"))
        fy += 30
    page.rect([sx, fy + 4, sw, 1], fill="line")
    page.text([sx, fy + 16, sw, 14], "RECENT TICKETS", style="lbl")
    for i, (t, tone) in enumerate([("#4602 Billing", "good"), ("#4471 Login", "good"),
                                   ("#4399 API", "warn")]):
        page.rect([sx, fy + 40 + i * 38, sw, 30], fill="canvas", stroke="line",
                  stroke_style=HAIR, radius=8)
        circle(page, sx + 16, fy + 55 + i * 38, 4, fill=_TONE[tone][1])
        page.text([sx + 30, fy + 48 + i * 38, sw - 40, 14], t, style="td")


# ======================================================================= #
#  07 — tickets table
# ======================================================================= #
def tickets(b):
    page, area = shell(b, "tickets", "tickets", "Tickets",
                       crumb="Support · Tickets",
                       actions=[("Import", "ghost"), ("New ticket", "primary")])
    x, y, w, h = area
    # filter bar
    pill(page, [x, y, 300, 36], "⌕  Search 12,481 tickets", fill="paper",
         stroke="line", style="place", radius=8)
    fx = x + 316
    for f in ["Status: Open ▾", "Priority ▾", "Assignee ▾", "Channel ▾", "+ Filter"]:
        bw = 24 + len(f) * 7.5
        pill(page, [fx, y, bw, 36], f, fill="paper", stroke="line", style="chip",
             radius=8)
        fx += bw + 10
    page.text([x + w - 110, y + 10, 110, 16], "⤓ Saved views", style="chipA")

    cols = [{"label": "ID", "w": 0.7, "kind": "id"},
            {"label": "Subject", "w": 2.6},
            {"label": "Requester", "w": 1.6, "kind": "avatar"},
            {"label": "Status", "w": 1, "kind": "badge"},
            {"label": "Priority", "w": 1, "kind": "badge"},
            {"label": "Assignee", "w": 1.4, "kind": "avatar"},
            {"label": "Updated", "w": 1, "kind": "sub"}]
    rows = [
        ["#4821", "Refund not received for May invoice", "Jane Cooper",
         ("Open", "accent"), ("Urgent", "bad"), "Ava N.", "2m ago"],
        ["#4820", "Password reset link expired", "Cody Fisher",
         ("Pending", "warn"), ("High", "warn"), "Leo K.", "14m ago"],
        ["#4819", "Can I export reports to CSV?", "Esther Howard",
         ("Open", "accent"), ("Low", "muted"), "—", "1h ago"],
        ["#4818", "Charged twice this billing cycle", "Marvin McKinney",
         ("Open", "accent"), ("High", "warn"), "Mia R.", "1h ago"],
        ["#4817", "Loving the new dashboard!", "Brooklyn Simmons",
         ("Solved", "good"), ("Low", "good"), "Ava N.", "3h ago"],
        ["#4816", "API returns 500 on contact sync", "Wade Warren",
         ("Open", "accent"), ("Urgent", "bad"), "Sam T.", "4h ago"],
        ["#4815", "Request to cancel subscription", "Floyd Miles",
         ("Pending", "warn"), ("Med", "warn"), "Leo K.", "5h ago"],
        ["#4814", "How do I add a teammate?", "Kristin Watson",
         ("Solved", "good"), ("Low", "good"), "Mia R.", "6h ago"],
        ["#4813", "Webhook signature mismatch", "Darrell Steward",
         ("Open", "accent"), ("High", "warn"), "Sam T.", "7h ago"],
        ["#4812", "Invoice PDF is blank", "Annette Black",
         ("Pending", "warn"), ("Med", "warn"), "Ava N.", "8h ago"],
    ]
    end = table(page, [x, y + 56, w, h - 56], cols, rows, row_h=44)
    page.text([x, end + 14, 300, 16], "Showing 1–10 of 12,481", style="mut")
    px = x + w - 282
    for lbl in ["‹ Prev", "1", "2", "3", "…", "Next ›"]:
        bw = 20 + len(lbl) * 8
        pill(page, [px, end + 6, bw, 28],
             lbl, fill="accent" if lbl == "1" else "paper",
             style="btn" if lbl == "1" else "chip", stroke=None if lbl == "1" else "line",
             radius=7)
        px += bw + 6


# ======================================================================= #
#  08 — ticket detail (form heavy)
# ======================================================================= #
def ticket_detail(b):
    page, area = shell(b, "ticket_detail", "tickets", "Ticket #4818",
                       crumb="Tickets · #4818",
                       actions=[("Merge", "ghost"), ("Save", "primary")])
    x, y, w, h = area
    main, side = row([x, y, w, h], gap=16, weights=[2.2, 1])

    page.rect(main, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    mx, my, mw, _ = inset(main, 22)
    page.text([mx, my, mw, 20], "Charged twice this billing cycle", style="h2")
    page.text([mx, my + 26, mw, 14], "Opened by Marvin McKinney · Mar 14, 2026",
              style="mut")
    page.rect([mx, my + 52, mw, 1], fill="line")
    # description placeholder
    page.text([mx, my + 66, mw, 14], "DESCRIPTION", style="lbl")
    bars(page, [mx, my + 88, mw, 0], n=4, gap=10, h=9, last=0.4)
    # attachments
    page.text([mx, my + 180, mw, 14], "ATTACHMENTS", style="lbl")
    for i, name in enumerate(["invoice.pdf", "screenshot.png"]):
        ax = mx + i * 180
        page.rect([ax, my + 202, 168, 56], fill="canvas", stroke="line",
                  stroke_style=HAIR, radius=10)
        icon(page, [ax + 12, my + 214, 32, 32], "▤", fill="paper")
        page.text([ax + 54, my + 218, 100, 14], name, style="td")
        page.text([ax + 54, my + 236, 100, 12], "PDF · 84 KB", style="mut")
    # activity timeline
    page.text([mx, my + 286, mw, 14], "ACTIVITY", style="lbl")
    acts = [("Marvin created this ticket", "9:02"),
            ("Auto-assigned to Mia R.", "9:02"),
            ("Mia replied", "9:18"), ("Priority set to High", "9:20")]
    for i, (t, ti) in enumerate(acts):
        ly = my + 312 + i * 36
        circle(page, mx + 8, ly + 8, 5, fill="accent")
        if i < len(acts) - 1:
            page.rect([mx + 7, ly + 14, 2, 30], fill="line")
        page.text([mx + 26, ly, mw - 80, 14], t, style="td")
        page.text([mx + mw - 50, ly, 50, 14], ti, style="mut")

    # properties side
    page.rect(side, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    sx, sy, sw, _ = inset(side, 20)
    page.text([sx, sy, sw, 14], "PROPERTIES", style="lbl")
    field(page, [sx, sy + 22, sw, 58], "Status", "Open", kind="select")
    field(page, [sx, sy + 90, sw, 58], "Priority", "High", kind="select")
    field(page, [sx, sy + 158, sw, 58], "Assignee", "Mia Rivera", kind="select")
    field(page, [sx, sy + 226, sw, 58], "Type", "Billing", kind="select")
    page.text([sx, sy + 300, sw, 14], "TAGS", style="lbl")
    tx = sx
    for t in ["billing", "refund", "vip"]:
        bw = 22 + len(t) * 7
        pill(page, [tx, sy + 322, bw, 26], "# " + t, fill="fill", style="chip")
        tx += bw + 8
    button(page, [sx, sy + 366, sw, 40], "Apply macro ▾", "ghost")


# ======================================================================= #
#  09 — live chat console
# ======================================================================= #
def livechat(b):
    page, area = shell(b, "livechat", "livechat", "Live chat",
                       crumb="Support · Live chat",
                       actions=[("Set away", "ghost")])
    x, y, w, h = area
    queue, chat, ctx = row([x, y, w, h], gap=16, weights=[1, 2, 1.2])

    # active chats queue
    page.rect(queue, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    qx, qy, qw, _ = inset(queue, 14)
    page.text([qx, qy, qw, 14], "ACTIVE · 4", style="lbl")
    chats = [("Wade W.", "typing…", "good", True), ("Floyd M.", "2 min", "warn", False),
             ("Kristin W.", "5 min", "muted", False), ("Darrell S.", "waiting", "bad", False)]
    cy = qy + 26
    for name, st, tone, active in chats:
        if active:
            page.rect([qx - 4, cy - 4, qw + 8, 56], fill="accSft", radius=10)
        avatar(page, qx + 18, cy + 22, 16, _initials(name))
        circle(page, qx + 30, cy + 34, 5, fill=_TONE[tone][1], stroke="paper")
        page.text([qx + 44, cy + 10, qw - 60, 16], name, style="h3")
        page.text([qx + 44, cy + 28, qw - 60, 14], st, style="mut")
        cy += 64
    page.rect([qx, cy + 4, qw, 1], fill="line")
    page.text([qx, cy + 16, qw, 14], "WAITING · 2", style="lbl")
    for i in range(2):
        page.rect([qx, cy + 40 + i * 44, qw, 36], fill="canvas", stroke="line",
                  stroke_style=HAIR, radius=8)
        avatar(page, qx + 18, cy + 58 + i * 44, 12, "?")
        page.text([qx + 38, cy + 51 + i * 44, qw - 50, 14], "New visitor", style="td")

    # chat thread
    page.rect(chat, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    cx, cyy, cw, _ = inset(chat, 0)
    page.rect([cx, cyy, cw, 56], fill="paper")
    avatar(page, cx + 28, cyy + 28, 16, "WW")
    page.text([cx + 52, cyy + 14, 200, 16], "Wade Warren", style="h2")
    page.text([cx + 52, cyy + 34, 200, 13], "● Online · web · /pricing", style="mut")
    page.rect([cx, cyy + 56, cw, 1], fill="line")
    my = cyy + 76
    for kind, n in [("in", 2), ("out", 2), ("in", 3), ("out", 1)]:
        out = kind == "out"
        bw = cw * 0.56
        bx = cx + cw - 16 - bw if out else cx + 16
        page.rect([bx, my, bw, 20 + n * 16], fill="accSft" if out else "fill",
                  radius=12)
        bars(page, [bx + 14, my + 12, bw - 28, 0], n=n, gap=7, h=7, last=0.5,
             color="accent" if out else "bar")
        my += 20 + n * 16 + 14
    ccy = cyy + chat[3] - 70
    page.rect([cx + 16, ccy, cw - 32, 54], fill="canvas", stroke="line",
              stroke_style=HAIR, radius=10)
    page.text([cx + 30, ccy + 20, 200, 14], "Type a message…", style="place")
    button(page, [cx + cw - 100, ccy + 13, 70, 28], "Send", "primary")

    # visitor context
    page.rect(ctx, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    xx, xy, xw, _ = inset(ctx, 18)
    page.text([xx, xy, xw, 14], "VISITOR", style="lbl")
    facts = [("Location", "Berlin, DE"), ("Browser", "Chrome 124"),
             ("Pages", "7 this visit"), ("Referrer", "google.com"),
             ("Plan", "Trial · day 9")]
    fy = xy + 24
    for k, v in facts:
        page.text([xx, fy, xw * 0.5, 14], k, style="mut")
        page.text([xx + xw * 0.42, fy, xw * 0.58, 14], v,
                  style=dict(font_family=SANS, font_size=12, font_weight=600,
                             color="ink", align="right"))
        fy += 28
    page.rect([xx, fy + 6, xw, 1], fill="line")
    page.text([xx, fy + 18, xw, 14], "QUICK ACTIONS", style="lbl")
    for i, a in enumerate(["Send article", "Create ticket", "Block visitor"]):
        button(page, [xx, fy + 40 + i * 44, xw, 36], a, "ghost")


# ======================================================================= #
#  10 — AI Copilot
# ======================================================================= #
def copilot(b):
    page, area = shell(b, "copilot", "copilot", "AI Copilot",
                       crumb="Support · Copilot",
                       actions=[("History", "ghost"), ("New thread", "primary")])
    x, y, w, h = area
    chat, panel = row([x, y, w, h], gap=16, weights=[2.3, 1])

    page.rect(chat, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    cx, cy, cw, _ = inset(chat, 0)
    # empty-state suggestions on top, then a sample exchange
    avatar(page, cx + cw / 2, cy + 50, 26, None, fill="accSft")
    page.text([cx + cw / 2 - 14, cy + 42, 28, 18], "✦", style="chipA")
    page.text([cx, cy + 86, cw, 20], "How can I help you work faster?",
              style=dict(font_family=SANS, font_size=18, font_weight=800,
                         color="ink", align="center"))
    sug = ["Summarize ticket #4818", "Draft a refund reply",
           "Find similar past tickets", "Explain our SLA policy"]
    for s, bx in zip(sug, grid([cx + 40, cy + 124, cw - 80, 100], cols=2, rows=2,
                               gap=14, row_gap=14)):
        page.rect(bx, fill="canvas", stroke="line", stroke_style=HAIR, radius=10)
        page.text([bx[0] + 16, bx[1] + bx[3] / 2 - 8, bx[2] - 30, 16], s, style="td")
        page.text([bx[0] + bx[2] - 24, bx[1] + bx[3] / 2 - 9, 16, 18], "↗",
                  style="glyph")
    # one example answer
    ay = cy + 252
    page.rect([cx + 16, ay, cw * 0.5, 40], fill="accSft", radius=12)
    bars(page, [cx + 30, ay + 14, cw * 0.5 - 28, 0], n=1, gap=0, h=8, last=0.8,
         color="accent")
    ay += 56
    page.rect([cx + 16, ay, cw - 32, 120], fill="fill", radius=12)
    icon(page, [cx + 30, ay + 14, 24, 24], "✦", fill="paper", style="chipA")
    page.text([cx + 64, ay + 18, 200, 14], "Copilot", style="h3")
    bars(page, [cx + 30, ay + 48, cw - 60, 0], n=3, gap=9, h=8, last=0.55)
    for i, c in enumerate(["Sources: 3", "Insert", "Copy"]):
        pill(page, [cx + 30 + i * 96, ay + 92, 86, 22], c, fill="paper", style="chip")
    # composer
    ccy = cy + chat[3] - 70
    page.rect([cx + 16, ccy, cw - 32, 54], fill="canvas", stroke="line",
              stroke_style=HAIR, radius=10)
    page.text([cx + 30, ccy + 20, 300, 14], "Ask Copilot anything…", style="place")
    circle(page, cx + cw - 38, ccy + 27, 16, fill="accent")
    page.text([cx + cw - 54, ccy + 18, 32, 18], "↑", style="glyphW")

    # context panel
    page.rect(panel, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    px, py, pw, _ = inset(panel, 18)
    page.text([px, py, pw, 14], "CONTEXT", style="lbl")
    for i, (g, t) in enumerate([("▤", "Ticket #4818"), ("◰", "Customer: Marvin M."),
                                ("◳", "Knowledge base"), ("◷", "Order history")]):
        page.rect([px, py + 24 + i * 46, pw, 38], fill="canvas", stroke="line",
                  stroke_style=HAIR, radius=8)
        icon(page, [px + 8, py + 30 + i * 46, 26, 26], g, fill="paper")
        page.text([px + 44, py + 33 + i * 46, pw - 80, 14], t, style="td")
        toggle(page, px + pw - 46, py + 43 + i * 46, on=i < 2)
    page.rect([px, py + 224, pw, 1], fill="line")
    page.text([px, py + 238, pw, 14], "MODEL", style="lbl")
    pill(page, [px, py + 260, pw, 34], "Helm-Reason ▾", fill="accSft", style="chipA",
         radius=8)
    page.text([px, py + 306, pw, 40],
              "Copilot only reads data you toggle on. Nothing leaves your workspace.",
              style="mut")


# ======================================================================= #
#  11 — customers list
# ======================================================================= #
def customers(b):
    page, area = shell(b, "customers", "customers", "Customers",
                       crumb="Customers · People",
                       actions=[("Import", "ghost"), ("Add customer", "primary")])
    x, y, w, h = area
    pill(page, [x, y, 320, 36], "⌕  Search by name, email, company", fill="paper",
         stroke="line", style="place", radius=8)
    fx = x + 336
    for f in ["Segment ▾", "Plan ▾", "Sort: Recent ▾"]:
        bw = 24 + len(f) * 7.5
        pill(page, [fx, y, bw, 36], f, fill="paper", stroke="line", style="chip",
             radius=8)
        fx += bw + 10

    cols = [{"label": "Name", "w": 2, "kind": "avatar"},
            {"label": "Company", "w": 1.6},
            {"label": "Plan", "w": 1, "kind": "badge"},
            {"label": "Tickets", "w": 0.8, "kind": "sub"},
            {"label": "CSAT", "w": 1, "kind": "bars"},
            {"label": "LTV", "w": 1, "kind": "right"},
            {"label": "Last seen", "w": 1.1, "kind": "sub"}]
    data = [
        ["Jane Cooper", "Globex", ("Business", "accent"), "12", 0.96, "$11,400", "2m ago"],
        ["Cody Fisher", "Initech", ("Pro", "good"), "4", 0.88, "$3,200", "1h ago"],
        ["Esther Howard", "Umbrella", ("Free", "muted"), "1", 0.72, "$0", "1h ago"],
        ["Marvin McKinney", "Soylent", ("Business", "accent"), "7", 0.91, "$8,900", "3h ago"],
        ["Brooklyn Simmons", "Hooli", ("Pro", "good"), "2", 0.99, "$4,100", "4h ago"],
        ["Wade Warren", "Stark Ind.", ("Enterprise", "accent"), "9", 0.83, "$24,000", "5h ago"],
        ["Floyd Miles", "Wayne Ent.", ("Pro", "good"), "5", 0.79, "$5,600", "6h ago"],
        ["Kristin Watson", "Acme", ("Free", "muted"), "1", 0.65, "$0", "1d ago"],
        ["Darrell Steward", "Cyberdyne", ("Business", "accent"), "6", 0.87, "$9,200", "1d ago"],
    ]
    table(page, [x, y + 56, w, h - 56], cols, data, row_h=46)


# ======================================================================= #
#  12 — customer 360
# ======================================================================= #
def customer360(b):
    page, area = shell(b, "customer360", "customers", "Jane Cooper",
                       crumb="Customers · Jane Cooper",
                       actions=[("Message", "ghost"), ("New ticket", "primary")])
    x, y, w, h = area
    left, right = row([x, y, w, h], gap=16, weights=[1, 2.4])

    # profile card
    page.rect(left, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    lx, ly, lw, _ = inset(left, 20)
    avatar(page, lx + lw / 2, ly + 40, 36, "JC")
    page.text([lx, ly + 86, lw, 20], "Jane Cooper",
              style=dict(font_family=SANS, font_size=17, font_weight=800,
                         color="ink", align="center"))
    page.text([lx, ly + 110, lw, 14], "Head of Ops · Globex",
              style=dict(font_family=SANS, font_size=12, color="muted", align="center"))
    badge(page, [lx + lw / 2 - 40, ly + 134, 80, 22], "VIP", "accent")
    page.rect([lx, ly + 174, lw, 1], fill="line")
    facts = [("Email", "jane@globex.com"), ("Phone", "+1 555 0142"),
             ("Plan", "Business"), ("MRR", "$499"), ("Since", "Mar 2023"),
             ("Timezone", "PST")]
    fy = ly + 188
    for k, v in facts:
        page.text([lx, fy, lw * 0.45, 14], k, style="mut")
        page.text([lx + lw * 0.4, fy, lw * 0.6, 14], v,
                  style=dict(font_family=SANS, font_size=12, font_weight=600,
                             color="ink", align="right"))
        fy += 30
    button(page, [lx, fy + 8, lw, 38], "View in CRM ↗", "ghost")

    # activity / tabs
    page.rect(right, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    rx, ry, rw, _ = inset(right, 0)
    tabs(page, [rx + 18, ry + 8, rw - 36, 36],
         ["Timeline", "Tickets (12)", "Orders", "Notes"], active=0)
    # mini KPIs
    mk = row([rx + 18, ry + 60, rw - 36, 80], count=3, gap=14)
    for (lbl, val), bx in zip([("Open tickets", "3"), ("CSAT", "96%"),
                               ("Avg reply", "1h 10m")], mk):
        page.rect(bx, fill="canvas", radius=10)
        page.text([bx[0] + 16, bx[1] + 14, bx[2] - 20, 14], lbl, style="lbl")
        page.text([bx[0] + 16, bx[1] + 34, bx[2] - 20, 30], val, style="kpi")
    # timeline
    items = [("Opened #4821 · Refund not received", "Urgent", "bad", "2m ago"),
             ("CSAT rated 5/5 on #4602", "Survey", "good", "2d ago"),
             ("Upgraded to Business plan", "Billing", "accent", "12d ago"),
             ("Opened #4471 · Login issue", "Solved", "good", "21d ago"),
             ("Joined the workspace", "System", "muted", "Mar 2023")]
    iy = ry + 160
    for t, tag, tone, when in items:
        circle(page, rx + 26, iy + 12, 6, fill=_TONE[tone][1])
        page.rect([rx + 25, iy + 20, 2, 40], fill="line")
        page.text([rx + 44, iy, rw - 200, 16], t, style="td")
        badge(page, [rx + 44, iy + 20, 18 + len(tag) * 7, 18], tag, tone)
        page.text([rx + rw - 90, iy + 2, 72, 14], when, style="mut")
        iy += 58


# ======================================================================= #
#  13 — companies
# ======================================================================= #
def companies(b):
    page, area = shell(b, "companies", "companies", "Companies",
                       crumb="Customers · Companies",
                       actions=[("Add company", "primary")])
    x, y, w, h = area
    cards = grid([x, y, w, 150], cols=4, rows=1, gap=16)
    tiles = [("Globex", "42 people", "$21k MRR"), ("Initech", "18 people", "$6k MRR"),
             ("Stark Ind.", "120 people", "$48k MRR"), ("Hooli", "67 people", "$31k MRR")]
    for (name, ppl, mrr), bx in zip(tiles, cards):
        page.rect(bx, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
        ix, iy, iw, _ = inset(bx, 16)
        icon(page, [ix, iy, 38, 38], "▦", fill="fill")
        page.text([ix + 50, iy + 2, iw - 60, 16], name, style="h2")
        page.text([ix + 50, iy + 22, iw - 60, 14], ppl, style="mut")
        page.rect([ix, iy + 56, iw, 1], fill="line")
        page.text([ix, iy + 68, iw, 16], mrr, style="metric")

    cols = [{"label": "Company", "w": 2, "kind": "avatar"},
            {"label": "Industry", "w": 1.4},
            {"label": "Plan", "w": 1, "kind": "badge"},
            {"label": "People", "w": 0.8, "kind": "sub"},
            {"label": "Open tickets", "w": 1, "kind": "sub"},
            {"label": "Health", "w": 1.2, "kind": "bars"},
            {"label": "MRR", "w": 1, "kind": "right"}]
    data = [
        ["Globex", "Logistics", ("Business", "accent"), "42", "7", 0.9, "$21,000"],
        ["Initech", "Software", ("Pro", "good"), "18", "2", 0.78, "$6,000"],
        ["Stark Ind.", "Manufacturing", ("Enterprise", "accent"), "120", "14", 0.84, "$48,000"],
        ["Hooli", "Internet", ("Business", "accent"), "67", "5", 0.95, "$31,000"],
        ["Umbrella", "Pharma", ("Free", "muted"), "9", "1", 0.55, "$0"],
        ["Soylent", "Food", ("Pro", "good"), "23", "3", 0.7, "$7,400"],
    ]
    table(page, [x, y + 174, w, h - 174], cols, data, row_h=46)


# ======================================================================= #
#  14 — knowledge base
# ======================================================================= #
def knowledge(b):
    page, area = shell(b, "kb", "kb", "Knowledge base",
                       crumb="Content · Knowledge base",
                       actions=[("Settings", "ghost"), ("New article", "primary")])
    x, y, w, h = area
    side, main = row([x, y, w, h], gap=16, weights=[1, 3])

    page.rect(side, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    sx, sy, sw, _ = inset(side, 16)
    page.text([sx, sy, sw, 14], "CATEGORIES", style="lbl")
    cats = [("Getting started", "12", True), ("Billing & plans", "18", False),
            ("Integrations", "24", False), ("Troubleshooting", "31", False),
            ("Account & security", "9", False), ("API reference", "47", False)]
    cyy = sy + 26
    for name, n, act in cats:
        if act:
            page.rect([sx - 4, cyy - 4, sw + 8, 30], fill="accSft", radius=8)
        page.text([sx + 4, cyy + 3, sw - 40, 16], name, style="navA" if act else "nav")
        page.text([sx + sw - 30, cyy + 3, 30, 16], n, style="mut")
        cyy += 34

    page.rect(main, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    mx, my, mw, _ = inset(main, 20)
    pill(page, [mx, my, mw, 38], "⌕  Search 141 articles", fill="canvas",
         stroke="line", style="place", radius=8)
    cols = [{"label": "Title", "w": 3},
            {"label": "Status", "w": 1, "kind": "badge"},
            {"label": "Views", "w": 1, "kind": "sub"},
            {"label": "Helpful", "w": 1.2, "kind": "bars"},
            {"label": "Updated", "w": 1.1, "kind": "sub"}]
    data = [
        ["How to reset your password", ("Live", "good"), "8.2k", 0.92, "2d ago"],
        ["Setting up SSO with SAML", ("Live", "good"), "3.1k", 0.81, "5d ago"],
        ["Understanding your invoice", ("Live", "good"), "5.4k", 0.74, "1w ago"],
        ["Connecting Slack", ("Draft", "warn"), "—", 0.0, "1w ago"],
        ["API rate limits explained", ("Live", "good"), "2.7k", 0.88, "2w ago"],
        ["Exporting reports to CSV", ("Review", "accent"), "1.1k", 0.69, "3w ago"],
        ["Webhook signature verification", ("Live", "good"), "940", 0.9, "1mo ago"],
    ]
    table(page, [mx, my + 54, mw, main[3] - 96], cols, data, row_h=44)


# ======================================================================= #
#  15 — article editor
# ======================================================================= #
def article_editor(b):
    page, area = shell(b, "article_editor", "kb", "Edit article",
                       crumb="Knowledge base · Edit",
                       actions=[("Preview", "ghost"), ("Publish", "primary")])
    x, y, w, h = area
    editor, meta = row([x, y, w, h], gap=16, weights=[2.6, 1])

    page.rect(editor, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    ex, ey, ew, _ = inset(editor, 24)
    # toolbar
    page.rect([ex, ey, ew, 40], fill="canvas", radius=8)
    for i, g in enumerate(("H", "B", "I", "•", "1.", "🔗", "▤", "<>", "✦")):
        icon(page, [ex + 8 + i * 40, ey + 6, 30, 28], g, fill="paper")
    # title
    page.text([ex, ey + 60, ew, 30], "How to reset your password",
              style=dict(font_family=SANS, font_size=24, font_weight=800, color="ink"))
    page.rect([ex, ey + 98, ew, 1], fill="line")
    # body blocks
    by = ey + 116
    page.rect([ex, by, 120, 18], fill="bar", radius=4)        # h2
    bars(page, [ex, by + 32, ew, 0], n=3, gap=11, h=9, last=0.6)
    by += 120
    ghost(page, [ex, by, ew, 120], label="▣ image / screenshot")
    by += 140
    page.rect([ex, by, 150, 18], fill="bar", radius=4)
    bars(page, [ex, by + 32, ew, 0], n=4, gap=11, h=9, last=0.45)

    # metadata side
    page.rect(meta, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    mx, my, mw, _ = inset(meta, 18)
    page.text([mx, my, mw, 14], "ARTICLE", style="lbl")
    field(page, [mx, my + 22, mw, 58], "Category", "Account & security", kind="select")
    field(page, [mx, my + 90, mw, 58], "Visibility", "Public", kind="select")
    field(page, [mx, my + 158, mw, 58], "URL slug", "/reset-password")
    page.text([mx, my + 232, mw, 14], "SEO", style="lbl")
    field(page, [mx, my + 254, mw, 76], "Meta description", "", kind="area")
    page.rect([mx, my + 348, mw, 1], fill="line")
    page.text([mx, my + 362, mw * 0.6, 14], "Auto-translate", style="td")
    toggle(page, mx + mw - 46, my + 369, on=True)


# ======================================================================= #
#  16 — reports
# ======================================================================= #
def reports(b):
    page, area = shell(b, "reports", "reports", "Reports",
                       crumb="Insights · Reports",
                       actions=[("Last 30 days ▾", "ghost"), ("Export", "primary")])
    x, y, w, _ = area
    kpis = [("Tickets resolved", "4,182", "▲ 9%", False),
            ("First response", "1h 38m", "▼ 12%", False),
            ("Resolution time", "6h 04m", "▼ 4%", False),
            ("CSAT", "94.2%", "▲ 1.4", False),
            ("Reopen rate", "3.1%", "▲ 0.4", True)]
    for (lbl, val, d, down), bx in zip(kpis, row([x, y, w, 100], count=5, gap=14)):
        kpi(page, bx, lbl, val, d, down)

    top = y + 120
    big, donut = row([x, top, w, 300], gap=18, weights=[2, 1])
    inner = card(page, big, title="Resolved vs received", action="Daily ▾")
    fr = Frame(domain=(0, 0, 11, 600),
               box=(inner[0] + 44, inner[1] + 6, inner[2] - 54, inner[3] - 36))
    recv = [380, 420, 460, 410, 520, 560, 300, 280, 540, 600, 580, 560]
    reso = [v - 40 - (i % 4) * 15 for i, v in enumerate(recv)]
    ch = (Chart(fr)
          .axes(x_ticks=[0, 3, 6, 9], y_ticks=[0, 200, 400, 600],
                x_format=lambda v: f"W{int(v) + 1}", y_format=lambda v: str(int(v)),
                grid=True)
          .line([(i, v) for i, v in enumerate(recv)], stroke="muted", width=2.2,
                smooth=True, label="received")
          .line([(i, v) for i, v in enumerate(reso)], stroke="accent", width=2.6,
                smooth=True, label="resolved")
          .legend(at="tl"))
    page.extend(ch.objects())

    inner = card(page, donut, title="Resolution by channel")
    # simple stacked bar as a donut stand-in
    segs = [("Email", 0.44, "accent"), ("Chat", 0.3, "good"),
            ("Voice", 0.15, "warn"), ("Social", 0.11, "muted")]
    bx0 = inner[0]
    bw = inner[2]
    page.rect([bx0, inner[1] + 6, bw, 20], fill="fill", radius=10)
    off = bx0
    for name, frac, tone in segs:
        page.rect([off, inner[1] + 6, bw * frac, 20], fill=_TONE[tone][1],
                  radius=0)
        off += bw * frac
    ly = inner[1] + 44
    for name, frac, tone in segs:
        circle(page, bx0 + 6, ly + 7, 6, fill=_TONE[tone][1])
        page.text([bx0 + 20, ly, bw - 60, 14], name, style="td")
        page.text([bx0 + bw - 40, ly, 40, 14], f"{int(frac * 100)}%", style="metric")
        ly += 30

    # agent leaderboard
    bot = top + 320
    inner = card(page, [x, bot, w, H - PAD - bot], title="Agent performance")
    cols = [{"label": "Agent", "w": 1.8, "kind": "avatar"},
            {"label": "Resolved", "w": 1, "kind": "sub"},
            {"label": "Avg reply", "w": 1, "kind": "sub"},
            {"label": "CSAT", "w": 1.6, "kind": "bars"},
            {"label": "SLA met", "w": 1.6, "kind": "bars"}]
    data = [["Ava Nelson", "612", "1h 02m", 0.97, 0.99],
            ["Leo King", "548", "1h 21m", 0.93, 0.96],
            ["Mia Rivera", "501", "1h 44m", 0.9, 0.92],
            ["Sam Turner", "470", "2h 03m", 0.86, 0.88]]
    table(page, [inner[0], inner[1] + 4, inner[2], inner[3] - 4], cols, data, row_h=40)


# ======================================================================= #
#  17 — SLA & performance
# ======================================================================= #
def sla(b):
    page, area = shell(b, "sla", "sla", "SLA & performance",
                       crumb="Insights · SLA",
                       actions=[("Configure SLAs", "ghost"), ("Export", "primary")])
    x, y, w, _ = area
    kpis = [("SLA compliance", "96.4%", "▲ 1.1", False),
            ("At risk now", "14", "next 2h", True),
            ("Breached today", "6", "▲ 2", True),
            ("Avg time to breach", "3h 20m", "buffer", False)]
    for (lbl, val, d, down), bx in zip(kpis, row([x, y, w, 100], count=4, gap=16)):
        kpi(page, bx, lbl, val, d, down)

    top = y + 120
    chartbox, gauge = row([x, top, w, 280], gap=18, weights=[2, 1])
    inner = card(page, chartbox, title="Breaches per day — 14 days")
    fr = Frame(domain=(0, 0, 13, 20),
               box=(inner[0] + 40, inner[1] + 6, inner[2] - 50, inner[3] - 36))
    br = [4, 6, 3, 8, 5, 2, 1, 9, 7, 4, 6, 3, 8, 6]
    ch = (Chart(fr)
          .axes(x_ticks=[0, 4, 8, 12], y_ticks=[0, 5, 10, 15, 20],
                x_format=lambda v: f"D{int(v) + 1}", y_format=lambda v: str(int(v)),
                grid=True)
          .bars([(i, v) for i, v in enumerate(br)], width=20, fill="warn", radius=3,
                label="breaches"))
    page.extend(ch.objects())

    inner = card(page, gauge, title="By policy")
    pols = [("Urgent · 1h", 0.91, "warn"), ("High · 4h", 0.97, "good"),
            ("Normal · 8h", 0.99, "good"), ("Low · 24h", 1.0, "good")]
    gy = inner[1] + 6
    for name, frac, tone in pols:
        page.text([inner[0], gy, inner[2] - 50, 14], name, style="td")
        page.text([inner[0] + inner[2] - 44, gy, 44, 14],
                  f"{int(frac * 100)}%", style="metric")
        page.rect([inner[0], gy + 20, inner[2], 8], fill="fill", radius=4)
        page.rect([inner[0], gy + 20, inner[2] * frac, 8], fill=_TONE[tone][1],
                  radius=4)
        gy += 50

    bot = top + 300
    inner = card(page, [x, bot, w, H - PAD - bot], title="Tickets at risk",
                 action="View all")
    cols = [{"label": "ID", "w": 0.7, "kind": "id"},
            {"label": "Subject", "w": 2.6},
            {"label": "Policy", "w": 1.2, "kind": "badge"},
            {"label": "Assignee", "w": 1.4, "kind": "avatar"},
            {"label": "Time left", "w": 1.1, "kind": "badge"},
            {"label": "Buffer", "w": 1.4, "kind": "bars"}]
    data = [["#4821", "Refund not received", ("Urgent 1h", "bad"), "Ava N.",
             ("Breached", "bad"), 0.0],
            ["#4820", "Password reset expired", ("High 4h", "warn"), "Leo K.",
             ("28m", "warn"), 0.12],
            ["#4816", "API 500 on sync", ("Urgent 1h", "warn"), "Sam T.",
             ("41m", "warn"), 0.3],
            ["#4813", "Webhook mismatch", ("High 4h", "good"), "Sam T.",
             ("2h 10m", "good"), 0.6]]
    table(page, [inner[0], inner[1] + 4, inner[2], inner[3] - 4], cols, data, row_h=42)


# ======================================================================= #
#  18 — automations
# ======================================================================= #
def automations(b):
    page, area = shell(b, "automations", "automations", "Automations",
                       crumb="Automate · Rules",
                       actions=[("Templates", "ghost"), ("New automation", "primary")])
    x, y, w, h = area
    tabs(page, [x, y, w, 36], ["All", "Triggers", "Scheduled", "SLA", "Drafts"],
         active=0)
    cols = [{"label": "", "w": 0.4, "kind": "icon"},
            {"label": "Name", "w": 2.6},
            {"label": "Trigger", "w": 1.8, "kind": "sub"},
            {"label": "Runs (30d)", "w": 1, "kind": "sub"},
            {"label": "Success", "w": 1.4, "kind": "bars"},
            {"label": "Status", "w": 1, "kind": "badge"}]
    data = [
        ["⚡", "Auto-assign by topic", "On ticket created", "4,182", 0.99, ("On", "good")],
        ["⚡", "Escalate urgent to lead", "Priority = Urgent", "311", 0.97, ("On", "good")],
        ["◷", "Reopen if no reply 48h", "Scheduled · daily", "84", 0.95, ("On", "good")],
        ["⚡", "Tag VIP customers", "Customer = VIP", "1,204", 1.0, ("On", "good")],
        ["⚡", "Send CSAT on solve", "Status = Solved", "3,901", 0.92, ("On", "good")],
        ["◷", "Close stale tickets", "No activity 14d", "229", 0.88, ("Paused", "warn")],
        ["⚡", "Route billing to finance", "Type = Billing", "672", 0.96, ("Draft", "muted")],
    ]
    table(page, [x, y + 50, w, h - 50], cols, data, row_h=48)


# ======================================================================= #
#  19 — automation builder (flow)
# ======================================================================= #
def flow_builder(b):
    page, area = shell(b, "flow_builder", "automations", "Edit automation",
                       crumb="Automations · Auto-assign by topic",
                       actions=[("Test", "ghost"), ("Save & enable", "primary")])
    x, y, w, h = area
    palette, canvasb, inspector = row([x, y, w, h], gap=16, weights=[1, 2.6, 1.2])

    # blocks palette
    page.rect(palette, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    px, py, pw, _ = inset(palette, 14)
    page.text([px, py, pw, 14], "BLOCKS", style="lbl")
    blocks = [("⚡", "Trigger"), ("◈", "Condition"), ("✎", "Action"),
              ("⌥", "Branch"), ("◷", "Delay"), ("✉", "Notify"), ("✦", "AI step")]
    for i, (g, name) in enumerate(blocks):
        by = py + 26 + i * 44
        page.rect([px, by, pw, 36], fill="canvas", stroke="line", stroke_style=HAIR,
                  radius=8)
        icon(page, [px + 6, by + 4, 28, 28], "▢", fill="paper")
        page.text([px + 44, by + 10, pw - 56, 16], name, style="td")

    # flow canvas
    page.rect(canvasb, fill="canvas", stroke="line", stroke_style=HAIR, radius=12)
    cx, cyy, cw, _ = inset(canvasb, 0)
    cxm = cx + cw / 2
    nodes = [("TRIGGER", "Ticket created", "accent"),
             ("CONDITION", "Message contains keyword", "warn"),
             ("AI STEP", "Classify topic", "accent"),
             ("ACTION", "Assign to matching team", "good")]
    ny = cyy + 30
    nh, nw = 64, 280
    for i, (kind, label, tone) in enumerate(nodes):
        nx = cxm - nw / 2
        page.rect([nx, ny, nw, nh], fill="paper", stroke="line", stroke_style=HAIR,
                  radius=12)
        page.rect([nx, ny, 4, nh], fill=_TONE[tone][1], radius=2)
        page.text([nx + 18, ny + 12, nw - 30, 12], kind, style="lbl")
        page.text([nx + 18, ny + 30, nw - 30, 18], label, style="h3")
        icon(page, [nx + nw - 38, ny + 18, 28, 28], "⋯", fill="canvas")
        if i < len(nodes) - 1:
            page.line([cxm, ny + nh], [cxm, ny + nh + 34], stroke="line",
                      stroke_style={"stroke_width": 1.4})
            circle(page, cxm, ny + nh + 17, 9, fill="paper", stroke="line")
            page.text([cxm - 9, ny + nh + 9, 18, 16], "+", style="glyph")
        ny += nh + 34
    page.rect([cxm - 14, ny, 28, 28], fill="paper", stroke="accent",
              stroke_style=DASH, radius=8)
    page.text([cxm - 14, ny + 4, 28, 18], "+", style="chipA")

    # inspector
    page.rect(inspector, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    ix, iy, iw, _ = inset(inspector, 18)
    page.text([ix, iy, iw, 14], "STEP · CONDITION", style="lbl")
    field(page, [ix, iy + 22, iw, 58], "When", "Message contains", kind="select")
    field(page, [ix, iy + 90, iw, 58], "Keywords", "refund, charge, invoice")
    field(page, [ix, iy + 158, iw, 58], "Match", "Any of", kind="select")
    page.rect([ix, iy + 232, iw, 1], fill="line")
    page.text([ix, iy + 246, iw, 14], "ELSE BRANCH", style="lbl")
    button(page, [ix, iy + 268, iw, 38], "+ Add fallback", "ghost")


# ======================================================================= #
#  20 — macros / canned replies
# ======================================================================= #
def macros(b):
    page, area = shell(b, "macros", "macros", "Macros",
                       crumb="Automate · Macros",
                       actions=[("Folders", "ghost"), ("New macro", "primary")])
    x, y, w, h = area
    listcol, prev = row([x, y, w, h], gap=16, weights=[1.6, 1.4])

    page.rect(listcol, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    lx, ly, lw, _ = inset(listcol, 0)
    pill(page, [lx + 14, ly + 12, lw - 28, 34], "⌕  Search macros", fill="canvas",
         stroke="line", style="place", radius=8)
    macs = [("Refund — standard", "Billing", "412 uses", True),
            ("Password reset steps", "Account", "388 uses", False),
            ("Ask for more info", "General", "1.2k uses", False),
            ("Escalate to engineering", "Bug", "94 uses", False),
            ("Close — resolved", "General", "2.1k uses", False),
            ("Shipping delay apology", "Orders", "167 uses", False),
            ("Trial extension offer", "Sales", "203 uses", False)]
    iy = ly + 60
    for name, cat, uses, act in macs:
        if act:
            page.rect([lx + 8, iy, lw - 16, 52], fill="accSft", radius=8)
            page.rect([lx + 8, iy, 3, 52], fill="accent", radius=2)
        page.text([lx + 22, iy + 9, lw - 140, 16], name, style="h3")
        badge(page, [lx + 22, iy + 28, 18 + len(cat) * 7, 18], cat, "muted")
        page.text([lx + lw - 90, iy + 17, 80, 14], uses,
                  style=dict(font_family=SANS, font_size=12, color="muted",
                             align="right"))
        page.rect([lx + 14, iy + 52, lw - 28, 1], fill="line")
        iy += 60

    # macro preview / editor
    page.rect(prev, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    qx, qy, qw, _ = inset(prev, 22)
    page.text([qx, qy, qw, 20], "Refund — standard", style="h2")
    badge(page, [qx, qy + 30, 80, 22], "Billing", "muted")
    page.text([qx + 92, qy + 32, 120, 16], "412 uses", style="mut")
    page.rect([qx, qy + 64, qw, 1], fill="line")
    page.text([qx, qy + 78, qw, 14], "ACTIONS", style="lbl")
    for i, a in enumerate(["Set status → Pending", "Set type → Billing",
                           "Reply with template"]):
        page.rect([qx, qy + 100 + i * 40, qw, 32], fill="canvas", stroke="line",
                  stroke_style=HAIR, radius=8)
        circle(page, qx + 16, qy + 116 + i * 40, 5, fill="accent")
        page.text([qx + 30, qy + 108 + i * 40, qw - 40, 14], a, style="td")
    page.text([qx, qy + 236, qw, 14], "REPLY TEXT", style="lbl")
    page.rect([qx, qy + 258, qw, 120], fill="canvas", stroke="line",
              stroke_style=HAIR, radius=10)
    bars(page, [qx + 14, qy + 274, qw - 28, 0], n=4, gap=10, h=8, last=0.5,
         color="barlt")
    button(page, [qx, qy + 394, 120, 38], "Edit macro", "primary")


# ======================================================================= #
#  21 — team & agents
# ======================================================================= #
def team(b):
    page, area = shell(b, "team", "team", "Team",
                       crumb="Admin · Team",
                       actions=[("Export", "ghost"), ("Invite agent", "primary")])
    x, y, w, h = area
    kpis = [("Agents", "24", None, False), ("Online now", "11", None, False),
            ("Avg load", "9.2", "tickets", False), ("Seats left", "6", "of 30", False)]
    for (lbl, val, d, down), bx in zip(kpis, row([x, y, w, 100], count=4, gap=16)):
        kpi(page, bx, lbl, val, d, down)

    cols = [{"label": "Agent", "w": 2, "kind": "avatar"},
            {"label": "Role", "w": 1.2, "kind": "badge"},
            {"label": "Teams", "w": 1.4, "kind": "sub"},
            {"label": "Open", "w": 0.8, "kind": "sub"},
            {"label": "CSAT", "w": 1.4, "kind": "bars"},
            {"label": "Status", "w": 1, "kind": "badge"}]
    data = [
        ["Ava Nelson", ("Admin", "accent"), "Billing, VIP", "12", 0.97, ("Online", "good")],
        ["Leo King", ("Agent", "muted"), "Technical", "9", 0.93, ("Online", "good")],
        ["Mia Rivera", ("Agent", "muted"), "Onboarding", "7", 0.9, ("Away", "warn")],
        ["Sam Turner", ("Agent", "muted"), "Technical", "11", 0.86, ("Offline", "muted")],
        ["Nora Webb", ("Lead", "accent"), "Billing", "5", 0.95, ("Online", "good")],
        ["Owen Diaz", ("Agent", "muted"), "General", "8", 0.84, ("Online", "good")],
        ["Priya Shah", ("Agent", "muted"), "Social", "6", 0.91, ("Away", "warn")],
    ]
    table(page, [x, y + 120, w, h - 120], cols, data, row_h=46)


# ======================================================================= #
#  22 — roles & permissions
# ======================================================================= #
def roles(b):
    page, area = shell(b, "roles", "roles", "Roles & permissions",
                       crumb="Admin · Roles",
                       actions=[("New role", "primary")])
    x, y, w, h = area
    side, main = row([x, y, w, h], gap=16, weights=[1, 3])

    page.rect(side, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    sx, sy, sw, _ = inset(side, 14)
    page.text([sx, sy, sw, 14], "ROLES", style="lbl")
    rls = [("Admin", "3 people", True), ("Lead", "5 people", False),
           ("Agent", "14 people", False), ("Light agent", "2 people", False),
           ("Custom: Finance", "1 person", False)]
    ry = sy + 26
    for name, n, act in rls:
        if act:
            page.rect([sx - 4, ry - 4, sw + 8, 40], fill="accSft", radius=8)
        page.text([sx + 4, ry, sw, 16], name, style="navA" if act else "h3")
        page.text([sx + 4, ry + 18, sw, 14], n, style="mut")
        ry += 46

    page.rect(main, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    mx, my, mw, _ = inset(main, 22)
    page.text([mx, my, mw, 20], "Admin", style="h2")
    page.text([mx, my + 26, mw, 14], "Full access to all workspace settings and data.",
              style="mut")
    page.rect([mx, my + 52, mw, 1], fill="line")
    # permission matrix
    page.text([mx, my + 66, mw, 14], "PERMISSIONS", style="lbl")
    groups = [("Tickets", ["View", "Reply", "Delete", "Reassign"]),
              ("Customers", ["View", "Edit", "Export", "Merge"]),
              ("Settings", ["Billing", "Channels", "Automations", "Roles"])]
    gy = my + 90
    for gname, perms in groups:
        page.text([mx, gy, 140, 16], gname, style="h3")
        cells = row([mx + 150, gy - 4, mw - 150, 28], count=4, gap=12)
        for perm, cbx in zip(perms, cells):
            toggle(page, cbx[0], cbx[1] + 14, on=True)
            page.text([cbx[0] + 50, cbx[1] + 6, cbx[2] - 50, 16], perm, style="td")
        page.rect([mx, gy + 40, mw, 1], fill="line")
        gy += 60


# ======================================================================= #
#  23 — settings / channels
# ======================================================================= #
def settings(b):
    page, area = shell(b, "settings", "settings", "Settings",
                       crumb="Admin · Settings")
    x, y, w, h = area
    nav, main = row([x, y, w, h], gap=16, weights=[1, 3])

    page.rect(nav, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    nx, ny, nw, _ = inset(nav, 14)
    secs = [("General", True), ("Channels", False), ("Branding", False),
            ("Business hours", False), ("Tags & fields", False),
            ("Integrations", False), ("API & webhooks", False),
            ("Billing", False), ("Security", False)]
    yy = ny
    for name, act in secs:
        if act:
            page.rect([nx - 4, yy - 4, nw + 8, 32], fill="accSft", radius=8)
        page.text([nx + 4, yy + 4, nw, 16], name, style="navA" if act else "nav")
        yy += 36

    page.rect(main, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    mx, my, mw, _ = inset(main, 24)
    page.text([mx, my, mw, 20], "General", style="h2")
    page.rect([mx, my + 34, mw, 1], fill="line")
    # workspace fields
    left, right = row([mx, my + 50, mw, 140], gap=24, weights=[1, 1])
    field(page, [left[0], left[1], left[2], 58], "Workspace name", "Acme Support")
    field(page, [right[0], right[1], right[2], 58], "Subdomain", "acme.helm.io")
    field(page, [left[0], left[1] + 70, left[2], 58], "Support email",
          "help@acme.com")
    field(page, [right[0], right[1] + 70, right[2], 58], "Default language",
          "English (US)", kind="select")
    page.rect([mx, my + 210, mw, 1], fill="line")
    # connected channels
    page.text([mx, my + 226, mw, 14], "CONNECTED CHANNELS", style="lbl")
    chans = [("✉", "Email", "help@acme.com", "good", True),
             ("◍", "Live chat", "Website widget", "good", True),
             ("◐", "WhatsApp", "Business API", "good", True),
             ("⌥", "Instagram", "Not connected", "muted", False)]
    for i, (g, name, sub, tone, on) in enumerate(chans):
        ry = my + 250 + i * 56
        page.rect([mx, ry, mw, 48], fill="canvas", stroke="line", stroke_style=HAIR,
                  radius=10)
        icon(page, [mx + 12, ry + 8, 32, 32], g, fill="paper")
        page.text([mx + 56, ry + 9, mw - 200, 16], name, style="h3")
        page.text([mx + 56, ry + 27, mw - 200, 14], sub, style="mut")
        badge(page, [mx + mw - 180, ry + 13, 90, 22],
              "Connected" if on else "Connect", tone if on else "accent")
        toggle(page, mx + mw - 60, ry + 24, on=on)


# ======================================================================= #
#  24 — notifications center
# ======================================================================= #
def notifications(b):
    page, area = shell(b, "notifications", "", "Notifications",
                       crumb="Notifications",
                       actions=[("Mark all read", "ghost"), ("Preferences", "ghost")])
    x, y, w, _ = area
    tabs(page, [x, y, w, 36], ["All", "Mentions", "Assignments", "SLA", "System"],
         active=0)
    feed = [
        ("Today", [
            ("@", "Leo K. mentioned you on #4820", "“can you take a look?”", "12m", True, "accent"),
            ("⚡", "Ticket #4821 assigned to you", "Refund not received · Urgent", "28m", True, "bad"),
            ("◷", "SLA at risk on #4816", "41m until first-reply breach", "41m", True, "warn"),
            ("★", "New 5-star CSAT from Jane Cooper", "“Super fast, thank you!”", "1h", False, "good")]),
        ("Earlier", [
            ("✓", "Mia R. resolved #4814", "How do I add a teammate?", "3h", False, "good"),
            ("◆", "Automation ‘Tag VIP’ ran 42 times", "Daily summary", "5h", False, "muted"),
            ("✉", "New email channel connected", "support@acme.com is live", "1d", False, "accent")]),
    ]
    ny = y + 52
    for group, rows in feed:
        page.text([x, ny, 200, 14], group.upper(), style="lbl")
        ny += 24
        for g, title, sub, t, unread, tone in rows:
            page.rect([x, ny, w, 60], fill="paper", stroke="line",
                      stroke_style=HAIR, radius=10)
            icon(page, [x + 14, ny + 14, 32, 32], g,
                 fill=_TONE[tone][0], style="chipA" if tone == "accent" else "glyph")
            page.text([x + 60, ny + 13, w - 200, 16], title, style="h3")
            page.text([x + 60, ny + 33, w - 200, 14], sub, style="mut")
            page.text([x + w - 70, ny + 14, 56, 14], t,
                      style=dict(font_family=SANS, font_size=12, color="muted",
                                 align="right"))
            if unread:
                circle(page, x + w - 18, ny + 30, 4, fill="accent")
            ny += 68


# ======================================================================= #
#  25 — global search results
# ======================================================================= #
def search_results(b):
    page, area = shell(b, "search", "", "Search", crumb='Search · "refund"')
    x, y, w, h = area
    pill(page, [x, y, w, 42], '⌕   refund', fill="paper", stroke="line",
         style="td", radius=10)
    page.text([x + w - 40, y + 13, 24, 16], "✕", style="glyph")
    fx = x
    for f, n in [("All", "22"), ("Tickets", "12"), ("Customers", "3"),
                 ("Articles", "5"), ("Macros", "2")]:
        lab = f"{f}  {n}"
        bw = 30 + len(lab) * 7
        first = f == "All"
        pill(page, [fx, y + 56, bw, 32], lab,
             fill="accSft" if first else "paper", style="chipA" if first else "chip",
             stroke=None if first else "line", radius=8)
        fx += bw + 10

    ry = y + 108
    # tickets
    page.text([x, ry, 200, 14], "TICKETS", style="lbl")
    tk = [("#4821", "Refund not received for May invoice", ("Urgent", "bad")),
          ("#4818", "Charged twice — needs refund", ("High", "warn")),
          ("#4602", "Refund processed, confirm receipt", ("Solved", "good"))]
    ty = ry + 22
    for tid, subj, (pr, tone) in tk:
        page.rect([x, ty, w, 44], fill="paper", stroke="line", stroke_style=HAIR,
                  radius=8)
        page.text([x + 14, ty + 14, 60, 16], tid, style="id")
        page.text([x + 80, ty + 14, w - 220, 16], subj, style="td")
        badge(page, [x + w - 110, ty + 11, 18 + len(pr) * 7, 22], pr, tone)
        ty += 52
    # customers + articles in two columns
    cy = ty + 12
    lcol, rcol = row([x, cy, w, 200], gap=20, weights=[1, 1])
    page.text([lcol[0], lcol[1], 200, 14], "CUSTOMERS", style="lbl")
    for i, (nm, co) in enumerate([("Jane Cooper", "Globex"), ("Refugio Diaz", "Initech")]):
        ay = lcol[1] + 22 + i * 52
        page.rect([lcol[0], ay, lcol[2], 44], fill="paper", stroke="line",
                  stroke_style=HAIR, radius=8)
        avatar(page, lcol[0] + 26, ay + 22, 14, _initials(nm))
        page.text([lcol[0] + 50, ay + 8, lcol[2] - 60, 16], nm, style="td")
        page.text([lcol[0] + 50, ay + 25, lcol[2] - 60, 14], co, style="mut")
    page.text([rcol[0], rcol[1], 200, 14], "ARTICLES", style="lbl")
    for i, (ti, v) in enumerate([("Understanding your invoice", "5.4k views"),
                                 ("How refunds work", "2.2k views")]):
        ay = rcol[1] + 22 + i * 52
        page.rect([rcol[0], ay, rcol[2], 44], fill="paper", stroke="line",
                  stroke_style=HAIR, radius=8)
        icon(page, [rcol[0] + 10, ay + 8, 28, 28], "▤", fill="canvas")
        page.text([rcol[0] + 48, ay + 8, rcol[2] - 60, 16], ti, style="td")
        page.text([rcol[0] + 48, ay + 25, rcol[2] - 60, 14], v, style="mut")


# ======================================================================= #
#  26 — billing & subscription
# ======================================================================= #
def billing(b):
    page, area = shell(b, "billing", "settings", "Billing & subscription",
                       crumb="Admin · Billing",
                       actions=[("Change plan", "primary")])
    x, y, w, _ = area
    plan, usage = row([x, y, w, 180], gap=18, weights=[1.3, 1])
    inner = card(page, plan, title="Current plan")
    page.text([inner[0], inner[1] + 6, 260, 30], "Business", style="kpi")
    badge(page, [inner[0] + 150, inner[1] + 12, 70, 22], "Active", "good")
    page.text([inner[0], inner[1] + 48, 360, 16], "$499 / month · renews Apr 12, 2026",
              style="sub")
    page.text([inner[0], inner[1] + 74, 360, 16], "24 of 30 seats used", style="mut")
    button(page, [inner[0], inner[1] + 100, 150, 38], "Manage plan", "ghost")
    button(page, [inner[0] + 162, inner[1] + 100, 140, 38], "Cancel", "ghost")

    inner = card(page, usage, title="Usage this cycle")
    meters = [("Seats", 0.8, "24 / 30"), ("Tickets", 0.62, "6.2k / 10k"),
              ("Storage", 0.45, "45 / 100 GB"), ("API calls", 0.3, "300k / 1M")]
    my = inner[1] + 4
    for name, frac, lab in meters:
        page.text([inner[0], my, 150, 14], name, style="td")
        page.text([inner[0] + inner[2] - 110, my, 110, 14], lab,
                  style=dict(font_family=SANS, font_size=12, color="muted",
                             align="right"))
        page.rect([inner[0], my + 18, inner[2], 7], fill="fill", radius=4)
        page.rect([inner[0], my + 18, inner[2] * frac, 7],
                  fill="bad" if frac > 0.75 else "accent", radius=4)
        my += 36

    # payment method
    pm = [x, y + 200, w, 70]
    page.rect(pm, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    icon(page, [x + 18, y + 218, 44, 34], "▭", fill="fill")
    page.text([x + 76, y + 216, 300, 16], "Visa ending 4242", style="h3")
    page.text([x + 76, y + 236, 300, 14], "Expires 08/27", style="mut")
    button(page, [x + w - 150, y + 217, 130, 36], "Update card", "ghost")

    # invoices
    inner = card(page, [x, y + 290, w, area[3] - 290], title="Invoices",
                 action="Download all")
    cols = [{"label": "Date", "w": 1.2, "kind": "sub"},
            {"label": "Invoice", "w": 1.2, "kind": "id"},
            {"label": "Plan", "w": 1.6},
            {"label": "Amount", "w": 1, "kind": "right"},
            {"label": "Status", "w": 1, "kind": "badge"},
            {"label": "", "w": 0.8, "kind": "mut"}]
    data = [["Mar 12, 2026", "INV-2042", "Business · monthly", "$499.00",
             ("Paid", "good"), "⤓ PDF"],
            ["Feb 12, 2026", "INV-2018", "Business · monthly", "$499.00",
             ("Paid", "good"), "⤓ PDF"],
            ["Jan 12, 2026", "INV-1994", "Business · monthly", "$499.00",
             ("Paid", "good"), "⤓ PDF"],
            ["Dec 12, 2025", "INV-1970", "Pro · monthly", "$199.00",
             ("Paid", "good"), "⤓ PDF"]]
    table(page, [inner[0], inner[1] + 4, inner[2], inner[3] - 4], cols, data, row_h=42)


# ======================================================================= #
#  27 — integrations marketplace
# ======================================================================= #
def integrations(b):
    page, area = shell(b, "integrations", "settings", "Integrations",
                       crumb="Admin · Integrations",
                       actions=[("Request app", "ghost")])
    x, y, w, h = area
    pill(page, [x, y, 320, 36], "⌕  Search 120+ integrations", fill="paper",
         stroke="line", style="place", radius=8)
    fx = x + 336
    for i, f in enumerate(["All", "CRM", "Messaging", "Dev tools", "Analytics"]):
        bw = 24 + len(f) * 8
        pill(page, [fx, y, bw, 36], f, fill="accSft" if i == 0 else "paper",
             style="chipA" if i == 0 else "chip", stroke=None if i == 0 else "line",
             radius=8)
        fx += bw + 10

    apps = [("◐", "Slack", "Messaging", True), ("▦", "Salesforce", "CRM", True),
            ("◧", "Jira", "Dev tools", True), ("◍", "HubSpot", "CRM", False),
            ("◉", "Stripe", "Billing", True), ("◰", "Shopify", "E-commerce", False),
            ("◴", "Zapier", "Automation", False), ("◇", "Segment", "Analytics", False)]
    for (g, name, cat, on), bx in zip(apps, grid([x, y + 56, w, h - 56],
                                                 cols=4, rows=2, gap=18, row_gap=18)):
        page.rect(bx, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
        ix, iy, iw, _ = inset(bx, 18)
        icon(page, [ix, iy, 44, 44], g, fill="fill")
        page.text([ix + 56, iy + 4, iw - 60, 16], name, style="h2")
        page.text([ix + 56, iy + 26, iw - 60, 14], cat, style="mut")
        bars(page, [ix, iy + 64, iw, 0], n=2, gap=8, h=7, last=0.6, color="barlt")
        if on:
            badge(page, [ix, iy + 100, 90, 26], "✓ Connected", "good")
        else:
            button(page, [ix, iy + 99, 96, 30], "Connect", "ghost")


# ======================================================================= #
#  28 — audit log
# ======================================================================= #
def audit(b):
    page, area = shell(b, "audit", "settings", "Audit log",
                       crumb="Admin · Audit log",
                       actions=[("Export CSV", "ghost")])
    x, y, w, h = area
    fx = x
    for f in ["Actor ▾", "Action ▾", "Resource ▾", "Last 7 days ▾"]:
        bw = 24 + len(f) * 7.5
        pill(page, [fx, y, bw, 36], f, fill="paper", stroke="line", style="chip",
             radius=8)
        fx += bw + 10
    cols = [{"label": "Time", "w": 1.3, "kind": "sub"},
            {"label": "Actor", "w": 1.6, "kind": "avatar"},
            {"label": "Action", "w": 2.4},
            {"label": "Resource", "w": 1.2, "kind": "id"},
            {"label": "IP", "w": 1.2, "kind": "id"},
            {"label": "Result", "w": 1, "kind": "badge"}]
    data = [
        ["09:42:11", "Ava Nelson", "Updated ticket priority → Urgent", "#4821", "10.0.4.2", ("OK", "good")],
        ["09:38:02", "System", "Automation ‘Auto-assign’ ran", "rule_18", "—", ("OK", "good")],
        ["09:31:55", "Leo King", "Merged tickets #4790 → #4788", "#4788", "10.0.4.9", ("OK", "good")],
        ["09:20:14", "Pedro A.", "Changed role: Sam T. → Agent", "user_42", "10.0.4.1", ("OK", "good")],
        ["08:58:30", "Mia Rivera", "Exported customers (1,204 rows)", "export", "10.0.4.7", ("OK", "good")],
        ["08:44:09", "Unknown", "Failed sign-in attempt", "auth", "203.0.113.5", ("Denied", "bad")],
        ["08:30:51", "Pedro A.", "Connected channel: WhatsApp", "chan_3", "10.0.4.1", ("OK", "good")],
        ["08:12:22", "System", "Webhook delivery retried (3×)", "wh_07", "—", ("Warn", "warn")],
        ["07:59:01", "Nora Webb", "Deleted macro ‘Old refund’", "macro_9", "10.0.4.5", ("OK", "good")],
    ]
    table(page, [x, y + 56, w, h - 56], cols, data, row_h=42)


# ======================================================================= #
#  29 — custom fields & tags
# ======================================================================= #
def custom_fields(b):
    page, area = shell(b, "custom_fields", "settings", "Tags & custom fields",
                       crumb="Admin · Tags & fields",
                       actions=[("New field", "primary")])
    x, y, w, h = area
    main, side = row([x, y, w, h], gap=18, weights=[2.4, 1])
    inner = card(page, main, title="Ticket fields", action="Reorder")
    cols = [{"label": "Field", "w": 2},
            {"label": "Type", "w": 1.2, "kind": "badge"},
            {"label": "Applies to", "w": 1.4, "kind": "sub"},
            {"label": "Required", "w": 1, "kind": "badge"}]
    data = [["Order ID", ("Text", "muted"), "Billing", ("Yes", "accent")],
            ["Severity", ("Dropdown", "accent"), "Bug", ("Yes", "accent")],
            ["Affected URL", ("URL", "muted"), "Bug", ("No", "muted")],
            ["Plan tier", ("Dropdown", "accent"), "All", ("No", "muted")],
            ["Refund amount", ("Number", "muted"), "Billing", ("No", "muted")],
            ["Region", ("Dropdown", "accent"), "All", ("No", "muted")],
            ["Reproducible", ("Checkbox", "muted"), "Bug", ("No", "muted")]]
    table(page, [inner[0], inner[1] + 4, inner[2], inner[3] - 4], cols, data, row_h=44)

    inner = card(page, side, title="Tags", action="+ Add")
    tags = [("billing", "1.2k"), ("bug", "842"), ("vip", "311"),
            ("onboarding", "508"), ("refund", "274"), ("api", "190"),
            ("feature-request", "421")]
    ty = inner[1] + 4
    for name, n in tags:
        page.rect([inner[0], ty, inner[2], 38], fill="canvas", stroke="line",
                  stroke_style=HAIR, radius=8)
        page.text([inner[0] + 14, ty + 11, inner[2] - 80, 16], "# " + name,
                  style="td")
        page.text([inner[0] + inner[2] - 60, ty + 11, 46, 16], n,
                  style=dict(font_family=SANS, font_size=12, color="muted",
                             align="right"))
        ty += 46


# ======================================================================= #
#  30 — API keys & webhooks
# ======================================================================= #
def api_webhooks(b):
    page, area = shell(b, "api_webhooks", "settings", "API & webhooks",
                       crumb="Admin · API & webhooks",
                       actions=[("Docs ↗", "ghost"), ("New key", "primary")])
    x, y, w, _ = area
    inner = card(page, [x, y, w, 240], title="API keys")
    cols = [{"label": "Name", "w": 1.6},
            {"label": "Key", "w": 2.2, "kind": "id"},
            {"label": "Created", "w": 1.2, "kind": "sub"},
            {"label": "Last used", "w": 1.2, "kind": "sub"},
            {"label": "Scope", "w": 1, "kind": "badge"},
            {"label": "", "w": 0.8, "kind": "mut"}]
    data = [["Production", "sk_live_••••••••4f2a", "Jan 2026", "2m ago",
             ("Full", "accent"), "Revoke"],
            ["Backend sync", "sk_live_••••••••91be", "Dec 2025", "1h ago",
             ("Write", "warn"), "Revoke"],
            ["Reporting (RO)", "sk_live_••••••••77c0", "Nov 2025", "3d ago",
             ("Read", "muted"), "Revoke"]]
    table(page, [inner[0], inner[1] + 4, inner[2], inner[3] - 4], cols, data, row_h=44)

    inner = card(page, [x, y + 260, w, area[3] - 260], title="Webhook endpoints",
                 action="+ Add endpoint")
    cols = [{"label": "Endpoint URL", "w": 2.6, "kind": "id"},
            {"label": "Events", "w": 1.8, "kind": "sub"},
            {"label": "Last delivery", "w": 1.4, "kind": "sub"},
            {"label": "Status", "w": 1, "kind": "badge"}]
    data = [["https://acme.com/hooks/helm", "ticket.created, ticket.updated", "200 · 2m ago", ("Active", "good")],
            ["https://acme.com/billing/sync", "invoice.paid", "200 · 1h ago", ("Active", "good")],
            ["https://ops.acme.com/alert", "sla.breached", "503 · 12m ago", ("Failing", "bad")]]
    table(page, [inner[0], inner[1] + 4, inner[2], inner[3] - 4], cols, data, row_h=44)


# ======================================================================= #
#  public help-center shell
# ======================================================================= #
def pubshell(b, sid, *, active=0, signed_in=False):
    page = b.page(sid, canvas=DESK, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")
    page.rect([0, 0, W, 64], fill="paper")
    page.rect([0, 63, W, 1], fill="line")
    icon(page, [PUB_X, 18, 28, 28], "◆", fill="accent", style="glyphW", radius=8)
    page.text([PUB_X + 38, 24, 180, 18], "Helm Help", style="logo")
    lx = PUB_X + 210
    for i, l in enumerate(["Home", "Getting started", "Billing", "API"]):
        tw = 24 + len(l) * 7.5
        page.text([lx, 24, tw, 16], l, style="tabA" if i == active else "tab")
        if i == active:
            page.rect([lx, 48, tw - 18, 2], fill="accent", radius=1)
        lx += tw + 6
    if signed_in:
        page.text([PUB_X + PUB_W - 200, 24, 120, 16], "My requests", style="link")
        avatar(page, PUB_X + PUB_W - 24, 32, 15, "JC")
    else:
        pill(page, [PUB_X + PUB_W - 210, 16, 120, 32], "⌕  Search", fill="canvas",
             stroke="line", style="place", radius=8)
        button(page, [PUB_X + PUB_W - 80, 16, 80, 32], "Sign in", "primary")
    page.layer("main")
    return page, [PUB_X, 96, PUB_W, H - 96 - 32]


# ======================================================================= #
#  31 — help center (customer-facing)
# ======================================================================= #
def help_center(b):
    page, area = pubshell(b, "help_center", active=0)
    page.rect([0, 64, W, 214], fill="accSft")
    page.text([0, 116, W, 32], "How can we help?", style="heroH")
    page.text([0, 154, W, 20], "Search the knowledge base or browse by topic",
              style="heroSub")
    sp = [W / 2 - 300, 196, 600, 48]
    page.rect(sp, fill="paper", stroke="line", stroke_style=HAIR, radius=10)
    page.text([sp[0] + 18, sp[1] + 16, 400, 16], "⌕  Search for articles…",
              style="place")
    button(page, [sp[0] + sp[2] - 96, sp[1] + 7, 86, 34], "Search", "primary")

    x = area[0]
    page.text([x, 306, 360, 20], "Browse by category", style="h2")
    cats = [("◰", "Getting started", "12 articles"), ("◱", "Billing & plans", "18 articles"),
            ("◳", "Integrations", "24 articles"), ("◴", "Troubleshooting", "31 articles"),
            ("◲", "Account & security", "9 articles"), ("◵", "API reference", "47 articles")]
    for (g, name, n), bx in zip(cats, grid([x, 338, area[2], 230], cols=3, rows=2,
                                           gap=20, row_gap=20)):
        page.rect(bx, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
        ix, iy, iw, _ = inset(bx, 18)
        icon(page, [ix, iy, 40, 40], g, fill="accSft", style="chipA")
        page.text([ix, iy + 52, iw, 16], name, style="h2")
        page.text([ix, iy + 74, iw, 14], n, style="mut")

    page.text([x, 598, 360, 20], "Popular articles", style="h2")
    pops = ["How to reset your password", "Understanding your invoice",
            "Setting up SSO with SAML", "Exporting reports to CSV"]
    for i, t in enumerate(pops):
        py = 632 + i * 46
        page.rect([x, py, area[2], 38], fill="paper", stroke="line",
                  stroke_style=HAIR, radius=8)
        icon(page, [x + 10, py + 6, 26, 26], "▤", fill="canvas")
        page.text([x + 48, py + 11, area[2] - 80, 16], t, style="td")
        page.text([x + area[2] - 28, py + 10, 18, 18], "›", style="glyph")


# ======================================================================= #
#  32 — help article (customer-facing)
# ======================================================================= #
def help_article(b):
    page, area = pubshell(b, "help_article", active=1)
    x, y, w, _ = area
    page.text([x, y, 500, 14], "Help center  ›  Account & security", style="mut")
    body, toc = row([x, y + 28, w, area[3] - 28], gap=40, weights=[2.4, 1])

    page.text([body[0], body[1], body[2], 34], "How to reset your password",
              style=dict(font_family=SANS, font_size=28, font_weight=800, color="ink",
                         letter_spacing=-0.5))
    page.text([body[0], body[1] + 42, body[2], 16],
              "Updated 2 days ago · 3 min read · 8,210 views", style="mut")
    page.rect([body[0], body[1] + 70, body[2], 1], fill="line")
    by = body[1] + 90
    page.rect([body[0], by, 160, 18], fill="bar", radius=4)
    bars(page, [body[0], by + 32, body[2], 0], n=3, gap=12, h=9, last=0.6)
    by += 120
    ghost(page, [body[0], by, body[2], 160], label="▣  screenshot")
    by += 184
    page.rect([body[0], by, 200, 18], fill="bar", radius=4)
    bars(page, [body[0], by + 32, body[2], 0], n=4, gap=12, h=9, last=0.4)
    by += 130
    # was this helpful
    page.rect([body[0], by, body[2], 64], fill="canvas", stroke="line",
              stroke_style=HAIR, radius=12)
    page.text([body[0] + 18, by + 24, 220, 16], "Was this article helpful?",
              style="h3")
    button(page, [body[0] + body[2] - 190, by + 16, 80, 32], "👍 Yes", "ghost")
    button(page, [body[0] + body[2] - 100, by + 16, 80, 32], "👎 No", "ghost")

    # toc / related
    page.rect([toc[0], toc[1], toc[2], 160], fill="paper", stroke="line",
              stroke_style=HAIR, radius=12)
    tx, ty, tw, _ = inset([toc[0], toc[1], toc[2], 160], 18)
    page.text([tx, ty, tw, 14], "ON THIS PAGE", style="lbl")
    for i, s in enumerate(["Before you start", "Reset from settings",
                           "Reset via email", "Still locked out?"]):
        page.text([tx, ty + 26 + i * 26, tw, 14], s,
                  style="link" if i == 0 else "body")
    page.rect([toc[0], toc[1] + 180, toc[2], 200], fill="paper", stroke="line",
              stroke_style=HAIR, radius=12)
    rx, ry, rw, _ = inset([toc[0], toc[1] + 180, toc[2], 200], 18)
    page.text([rx, ry, rw, 14], "RELATED", style="lbl")
    for i, s in enumerate(["Enabling two-factor auth", "Managing active sessions",
                           "SSO with SAML"]):
        page.rect([rx, ry + 26 + i * 48, rw, 38], fill="canvas", stroke="line",
                  stroke_style=HAIR, radius=8)
        page.text([rx + 12, ry + 37 + i * 48, rw - 24, 16], s, style="td")


# ======================================================================= #
#  33 — customer portal (my requests)
# ======================================================================= #
def customer_portal(b):
    page, area = pubshell(b, "customer_portal", active=0, signed_in=True)
    x, y, w, _ = area
    page.text([x, y + 6, 400, 30], "My requests", style="h1")
    button(page, [x + w - 180, y + 6, 180, 40], "Submit a request", "primary")
    tabs(page, [x, y + 58, w, 36], ["Open (3)", "Solved (8)", "All"], active=0)
    cols = [{"label": "Subject", "w": 3},
            {"label": "ID", "w": 1, "kind": "id"},
            {"label": "Status", "w": 1.2, "kind": "badge"},
            {"label": "Agent", "w": 1.4, "kind": "avatar"},
            {"label": "Updated", "w": 1.2, "kind": "sub"}]
    data = [["Refund not received for May invoice", "#4821", ("Open", "accent"),
             "Ava Nelson", "2m ago"],
            ["Can't connect Slack integration", "#4799", ("Pending", "warn"),
             "Leo King", "3h ago"],
            ["Question about API rate limits", "#4781", ("Open", "accent"),
             "Mia Rivera", "1d ago"]]
    table(page, [x, y + 110, w, area[3] - 110], cols, data, row_h=48)
    page.text([x, y + 110 + 40 + 3 * 48 + 16, w, 16],
              "Need help with something else?  Browse the help center →", style="link")


# ======================================================================= #
#  34 — CSAT survey (customer-facing)
# ======================================================================= #
def csat(b):
    page = b.page("csat", canvas=DESK, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="accSft")
    cb = [W / 2 - 290, 180, 580, 500]
    page.rect(cb, fill="paper", stroke="line", stroke_style=HAIR, radius=18)
    cx, cy, cw, _ = inset(cb, 40)
    icon(page, [W / 2 - 22, cy, 44, 44], "◆", fill="accent", style="glyphW", radius=12)
    page.text([cx, cy + 60, cw, 26], "How did we do?", style="cardH")
    page.text([cx, cy + 94, cw, 16],
              "Ticket #4821 · Refund not received", style="authSub")
    page.text([cx, cy + 140, cw, 16],
              "How would you rate the support you received?", style="authSub")
    faces = [("☹", "bad"), ("◔", "warn"), ("◐", "muted"), ("◕", "good"), ("☺", "good")]
    fb = row([cx + 40, cy + 174, cw - 80, 64], count=5, gap=14)
    for (g, tone), cbx in zip(faces, fb):
        sel = g == "☺"
        circle(page, cbx[0] + cbx[2] / 2, cbx[1] + 28, 26,
               fill="accSft" if sel else "canvas", stroke="accent" if sel else "line")
        page.text([cbx[0], cbx[1] + 18, cbx[2], 22], g,
                  style=dict(font_family=SANS, font_size=20, color="sub",
                             align="center"))
    page.text([cx + cw - 70, cy + 244, 70, 14], "Excellent", style="chipA")
    page.text([cx, cy + 280, 200, 14], "ANYTHING TO ADD?", style="lbl")
    page.rect([cx, cy + 302, cw, 80], fill="canvas", stroke="line",
              stroke_style=HAIR, radius=10)
    page.text([cx + 14, cy + 316, cw - 28, 16], "Tell us more (optional)…",
              style="place")
    button(page, [cx, cy + 398, cw, 44], "Submit feedback", "primary")
    page.text([0, H - 60, W, 16], "Powered by Helm",
              style=dict(font_family=SANS, font_size=12, color="muted", align="center"))


# ======================================================================= #
#  mobile companion shell
# ======================================================================= #
def phone(b, sid):
    page = b.page(sid, canvas=PHONE, coordinate_mode="absolute").layer("frame")
    page.rect([0, 0, PW, PH], fill="paper")
    page.rect([0, 0, PW, PH], fill="none", stroke="line", stroke_style=HAIR, radius=2)
    page.text([20, 16, 80, 16], "9:41", style="status")
    page.rect([PW - 64, 20, 16, 9], fill="bar", radius=2)
    page.rect([PW - 44, 20, 14, 9], fill="bar", radius=2)
    page.rect([PW - 26, 19, 18, 10], fill="ink", radius=2)
    page.rect([PW / 2 - 60, PH - 10, 120, 4], fill="line", radius=2)
    page.layer("main")
    return page


def _mobile_tabbar(page, active=0):
    page.rect([0, PH - 76, PW, 76], fill="paper")
    page.rect([0, PH - 76, PW, 1], fill="line")
    tabs = [("▤", "Inbox"), ("⌕", "Search"), ("◉", "Profile")]
    cols = row([0, PH - 68, PW, 46], count=3)
    for i, ((g, name), c) in enumerate(zip(tabs, cols)):
        col = "accent" if i == active else "muted"
        cx = c[0] + c[2] / 2
        page.rect([cx - 9, PH - 62, 18, 14], fill=col, radius=3)
        page.text([c[0], PH - 40, c[2], 12],
                  name, style=dict(font_family=SANS, font_size=10, font_weight=600,
                                   color=col, align="center"))


# ======================================================================= #
#  35 — mobile inbox
# ======================================================================= #
def mobile_inbox(b):
    page = phone(b, "mobile_inbox")
    page.text([20, 50, 200, 26], "Inbox", style="phoneH")
    icon(page, [PW - 96, 52, 32, 32], "⚲", fill="canvas")
    icon(page, [PW - 56, 52, 32, 32], "⚙", fill="canvas")
    # segmented control
    seg = [20, 96, PW - 40, 34]
    page.rect(seg, fill="fill", radius=9)
    sw = (seg[2]) / 3
    for i, s in enumerate(["Open", "Mine", "All"]):
        if i == 0:
            page.rect([seg[0] + 3, seg[1] + 3, sw - 6, 28], fill="paper", radius=7)
        page.text([seg[0] + i * sw, seg[1] + 9, sw, 16], s,
                  style="segA" if i == 0 else "seg")
    items = [
        ("Jane Cooper", "Refund not received", "Urgent", "bad", "2m", True),
        ("Cody Fisher", "Re: password reset link", "High", "warn", "14m", False),
        ("Esther Howard", "Export to CSV?", "Low", "muted", "1h", False),
        ("Marvin McKinney", "Double charged this month", "High", "warn", "1h", False),
        ("Wade Warren", "API returns 500 on sync", "Urgent", "bad", "4h", False),
        ("Floyd Miles", "Cancel my subscription", "Med", "warn", "5h", False),
        ("Brooklyn S.", "Loving the new app!", "Low", "good", "6h", False),
    ]
    iy = 148
    for name, subj, pr, tone, t, unread in items:
        if unread:
            page.rect([0, iy, 4, 84], fill="accent")
        avatar(page, 36, iy + 30, 17, _initials(name))
        page.text([66, iy + 14, PW - 130, 16], name, style="h3")
        page.text([PW - 56, iy + 15, 40, 14], t,
                  style=dict(font_family=SANS, font_size=12, color="muted",
                             align="right"))
        page.text([66, iy + 35, PW - 90, 16], subj, style="tdSub")
        badge(page, [66, iy + 56, 18 + len(pr) * 7, 18], pr, tone)
        page.rect([20, iy + 84, PW - 40, 1], fill="line")
        iy += 92
    _mobile_tabbar(page, active=0)


# ======================================================================= #
#  36 — mobile conversation
# ======================================================================= #
def mobile_conversation(b):
    page = phone(b, "mobile_conversation")
    icon(page, [16, 50, 32, 32], "‹", fill="canvas")
    avatar(page, 72, 66, 17, "JC")
    page.text([98, 50, 200, 16], "Jane Cooper", style="h3")
    page.text([98, 68, 200, 14], "globex.com · #4821", style="mut")
    icon(page, [PW - 48, 50, 32, 32], "⋯", fill="canvas")
    badge(page, [98, 88, 64, 18], "Urgent", "bad")
    page.rect([0, 116, PW, 1], fill="line")

    my = 134
    msgs = [("in", 3, "JC"), ("out", 2, "PA"), ("in", 2, "JC"), ("out", 3, "PA")]
    for kind, n, who in msgs:
        out = kind == "out"
        bw = PW * (0.66 if not out else 0.62)
        bx = PW - 16 - bw if out else 16
        page.rect([bx, my, bw, 22 + n * 15], fill="accSft" if out else "fill",
                  radius=12)
        bars(page, [bx + 14, my + 12, bw - 28, 0], n=n, gap=7, h=7, last=0.5,
             color="accent" if out else "bar")
        my += 22 + n * 15 + 14

    # AI suggestion
    page.rect([16, my, PW - 32, 50], fill="paper", stroke="accent",
              stroke_style=DASH, radius=10)
    icon(page, [28, my + 11, 28, 28], "✦", fill="accSft", style="chipA")
    page.text([64, my + 10, 180, 14], "Copilot draft ready", style="h3")
    page.text([64, my + 28, 180, 13], "Refund policy · ETA 3–5 days", style="mut")
    pill(page, [PW - 96, my + 12, 76, 26], "Insert", fill="accent", style="btn", pad=8)

    # composer
    cy = PH - 88
    page.rect([0, cy - 10, PW, 98], fill="paper")
    page.rect([0, cy - 10, PW, 1], fill="line")
    icon(page, [16, cy, 36, 36], "＋", fill="canvas")
    pill(page, [60, cy, PW - 136, 36], None, fill="fill", stroke="line", radius=18)
    page.text([74, cy + 10, 160, 16], "Reply to Jane…", style="place")
    circle(page, PW - 34, cy + 18, 18, fill="accent")
    page.text([PW - 52, cy + 9, 36, 18], "↑", style="glyphW")


# ---- build ---------------------------------------------------------------- #
SCREENS = [sitemap, signin, onboarding, dashboard, inbox, conversation, tickets,
           ticket_detail, livechat, copilot, customers, customer360, companies,
           knowledge, article_editor, reports, sla, automations, flow_builder,
           macros, team, roles, settings,
           notifications, search_results, billing, integrations, audit,
           custom_fields, api_webhooks, help_center, help_article,
           customer_portal, csat, mobile_inbox, mobile_conversation]


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Helm — Customer Service Suite (Wireframe)",
                        profile="deck", lang="en")
    for name, value in COLORS.items():
        b.define_color(name, value)
    for name, style in STYLES.items():
        b.define_text_style(name, **style)
    for screen in SCREENS:
        screen(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in errors[:20]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "tests", "fixtures", "cs-suite-wireframe.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
