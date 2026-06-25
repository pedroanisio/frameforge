"""Web Design Proposal — a full multi-page brochure authored with framegraph.sdk.

A showcase document: cover, contents, about, services, process diagram, timeline
chart, analytics charts, pricing tiers, team avatar grid, comparison table,
testimonials with star ratings, and a contact back cover. Golden + charcoal +
marble theme.
"""
from __future__ import annotations

import math
from dataclasses import replace

from framegraph.sdk import (
    Chart,
    DocumentBuilder,
    avatar,
    badge,
    card,
    kpi,
    linear_gradient,
    pill,
    progress,
    table,
)
from framegraph.sdk.draw import Frame
from framegraph.sdk.macros import lorem
from framegraph.sdk.widgets import default_theme

# --- palette ---------------------------------------------------------------- #
INK = "#23262B"
SUB = "#565B63"
MUTED = "#9AA0A8"
LINE = "#E7E6E1"
PAPER = "#FFFFFF"
PANEL = "#F5F4F0"
PANEL2 = "#ECEAE3"
CHARCOAL = "#23262B"
GOLD = "#F2A81C"
GOLD_DK = "#D8920C"
GOLD_SOFT = "#FCEED0"
FONT = ("Inter", "Helvetica", "Arial", "sans-serif")

TH = replace(
    default_theme(),
    accent=GOLD, accent_soft=GOLD_SOFT, ink=INK, sub=SUB, muted=MUTED,
    line=LINE, surface=PAPER, surface_alt=PANEL, fill=PANEL, fill_alt=PANEL2,
    good="#1F9254", good_soft="#E2F3E9", bad="#C23B3B",
    font=FONT, radius=12.0, pad=18.0, control_h=38.0,
)

W, H = 820, 1100
M = 66


# --- text helper ------------------------------------------------------------ #
def txt(size, *, color=INK, weight=400, align="left", valign="top",
        overflow="clip", wrap=False, **extra):
    st = {
        "font_family": list(FONT), "font_size": size, "font_weight": weight,
        "color": color, "align": align, "vertical_align": valign, "overflow": overflow,
    }
    if not wrap:
        st["white_space"] = "nowrap"
    st.update(extra)
    return st


# --- shared decorative pieces ---------------------------------------------- #
def marble(layer):
    """A subtle near-white marble field with faint diagonal veins."""
    layer.rect([0, 0, W, H], fill=linear_gradient(
        [("#FCFCFA", 0), ("#F0EFEA", 100)], angle=160), decorative=True)
    veins = [(-40, 120, 260, -60), (120, 420, 520, 140), (380, 980, 900, 540),
             (40, 760, 360, 520)]
    for x1, y1, x2, y2 in veins:
        layer.line([x1, y1], [x2, y2], stroke_style={"stroke_width": 1.2},
                   stroke="#E2E0D8", opacity=0.6, decorative=True)


def header(layer, number, title, sub=None):
    layer.text([M, 84, 120, 22], number, style=txt(13, color=GOLD, weight=800,
               letter_spacing=2))
    layer.text([M, 104, W - 2 * M, 46], title, style=txt(38, color=INK, weight=800,
               letter_spacing=-0.5))
    layer.rect([M, 158, 54, 5], fill=GOLD, radius=2.5)
    if sub:
        layer.text([M, 176, W - 2 * M, 22], sub, style=txt(14, color=MUTED, weight=500))


def footer(layer, page_no, label="Web Design Proposal"):
    layer.line([M, H - 56], [W - M, H - 56], stroke_style={"stroke_width": 1},
               stroke=LINE, decorative=True)
    layer.text([M, H - 46, 300, 18], label, style=txt(11, color=MUTED, weight=600,
               letter_spacing=1))
    layer.text([W - M - 60, H - 46, 60, 18], f"{page_no:02d}",
               style=txt(11, color=INK, weight=700, align="right"))


def photo(layer, box):
    x, y, w, h = box
    layer.rect(box, fill=linear_gradient([("#E9E7E0", 0), ("#DAD7CE", 100)],
               angle=135), radius=10, decorative=True)
    # a simple "image" glyph: sun + mountains
    cx = x + w / 2
    layer.add({"type": "ellipse", "center": [cx - w * 0.16, y + h * 0.34],
               "rx": 13, "ry": 13, "fill": "#C9C5BA", "decorative": True})
    layer.polygon([[x + w * 0.18, y + h * 0.74], [x + w * 0.40, y + h * 0.46],
                   [x + w * 0.56, y + h * 0.74]], fill="#C2BEB2", decorative=True)
    layer.polygon([[x + w * 0.44, y + h * 0.74], [x + w * 0.64, y + h * 0.52],
                   [x + w * 0.84, y + h * 0.74]], fill="#CBC7BC", decorative=True)


def star(layer, cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append([cx + rad * math.cos(a), cy + rad * math.sin(a)])
    layer.polygon(pts, fill=fill)


def stars(layer, x, y, n=5, r=8):
    for i in range(n):
        star(layer, x + i * (r * 2 + 6) + r, y + r, r, GOLD)


def brandmark(layer, x, y, s, *, ink="#FFFFFF"):
    """A small node-graph logo mark."""
    layer.rect([x, y, s, s], fill=GOLD, radius=s * 0.28)
    nodes = [(x + s * 0.30, y + s * 0.34), (x + s * 0.70, y + s * 0.30),
             (x + s * 0.5, y + s * 0.66)]
    for a in range(len(nodes)):
        for b in range(a + 1, len(nodes)):
            layer.line(list(nodes[a]), list(nodes[b]),
                       stroke=ink, stroke_style={"stroke_width": 2})
    for nx, ny in nodes:
        layer.add({"type": "ellipse", "center": [nx, ny], "rx": s * 0.07,
                   "ry": s * 0.07, "fill": ink})


# =========================================================================== #
def build_document():
    doc = DocumentBuilder(title="Web Design Proposal", profile="deck")

    # ---- P1 COVER --------------------------------------------------------- #
    p = doc.page("cover", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    L.rect([0, 0, W, H], fill=linear_gradient([("#26292F", 0), ("#1A1C20", 100)],
           angle=160), decorative=True)
    # big gold diagonal shapes
    L.polygon([[W, 0], [W, 360], [W - 300, 0]], fill=GOLD)
    L.polygon([[W, 60], [W, 240], [W - 150, 60]], fill=GOLD_DK)
    L.polygon([[0, H], [0, H - 220], [260, H]], fill="#2E3137")
    brandmark(L, M, 72, 46)
    L.text([M + 60, 80, 300, 22], "STUDIO AURORA",
           style=txt(15, color="#FFFFFF", weight=800, letter_spacing=2))
    L.text([M + 60, 102, 300, 18], "digital product studio",
           style=txt(12, color=GOLD, weight=600, letter_spacing=1))
    # title card
    L.add({"type": "rect", "box": [M, 420, 560, 250], "fill": "#FFFFFF",
           "radius": 16, "style": {"box_shadow": [{"offset_x": 0, "offset_y": 18, "blur": 44, "color": "#000000"}]}})
    L.text([M + 40, 462, 480, 20], "PROPOSAL — 2026",
           style=txt(13, color=GOLD_DK, weight=800, letter_spacing=3))
    L.text([M + 40, 492, 500, 64], "Web Design",
           style=txt(62, color=INK, weight=800, letter_spacing=-1.5))
    L.text([M + 40, 556, 500, 64], "Proposal",
           style=txt(62, color=GOLD, weight=800, letter_spacing=-1.5))
    L.text([M + 42, 628, 480, 20], "Prepared for  ·  Northwind Coffee Co.",
           style=txt(14, color=SUB, weight=600))
    L.text([M, H - 120, 600, 20], "A complete redesign & build engagement",
           style=txt(15, color="#C9CCD2", weight=500))
    L.text([M, H - 92, 600, 18], "hello@studioaurora.design   ·   studioaurora.design",
           style=txt(13, color=MUTED, weight=500))

    # ---- P2 CONTENTS ------------------------------------------------------ #
    p = doc.page("contents", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    L.rect([0, 0, 230, H], fill=linear_gradient([("#26292F", 0), ("#1A1C20", 100)],
           angle=170), decorative=True)
    L.polygon([[0, 0], [230, 0], [0, 150]], fill=GOLD)
    L.text([40, H - 200, 170, 30], "01", style=txt(64, color="#33373E", weight=800))
    L.text([40, H - 132, 190, 22], "Contents", style=txt(20, color="#FFFFFF", weight=700))
    L.text([40, H - 104, 190, 40], "What's inside this\nproposal.", style=txt(13, color="#9AA0A8", weight=500, wrap=True, line_height=1.4))
    items = [
        ("01", "About Our Studio", "03"), ("02", "What We Do", "04"),
        ("03", "Our Process", "05"), ("04", "Project Timeline", "06"),
        ("05", "Projected Impact", "07"), ("06", "Packages & Pricing", "08"),
        ("07", "Meet the Team", "09"), ("08", "Compare Packages", "10"),
        ("09", "Kind Words", "11"), ("10", "Let's Talk", "12"),
    ]
    L.text([300, 110, 400, 40], "Table of Contents",
           style=txt(34, color=INK, weight=800, letter_spacing=-0.5))
    L.rect([300, 168, 54, 5], fill=GOLD, radius=2.5)
    y = 230
    for num, name, pg in items:
        L.text([300, y, 40, 22], num, style=txt(15, color=GOLD, weight=800))
        L.text([348, y, 320, 22], name, style=txt(17, color=INK, weight=600))
        L.text([W - M - 40, y, 40, 22], pg, style=txt(15, color=MUTED, weight=700,
               align="right"))
        L.line([348, y + 30], [W - M - 50, y + 30], stroke=LINE,
               stroke_style={"stroke_width": 1}, decorative=True)
        y += 58

    # ---- P3 ABOUT --------------------------------------------------------- #
    p = doc.page("about", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "01 — ABOUT", "About Our Studio", "Ten years crafting digital products that convert.")
    photo(L, [M, 230, 320, 240])
    L.text([M + 360, 230, W - M - (M + 360), 24], "Who we are",
           style=txt(20, color=INK, weight=800))
    L.text([M + 360, 264, W - M - (M + 360), 200], lorem(4), style=txt(13.5, color=SUB, weight=400, wrap=True, line_height=1.6))
    L.text([M, 500, 400, 24], "We help brands grow online",
           style=txt(20, color=INK, weight=800))
    L.text([M, 534, W - 2 * M, 120], lorem(5), style=txt(13.5, color=SUB, weight=400, wrap=True, line_height=1.6))
    kx = M
    for label, value, delta in [("Projects shipped", "150+", "▲ 22% YoY"),
                                ("Client satisfaction", "98%", "▲ top 5%"),
                                ("Design awards", "12", "Awwwards · CSSDA")]:
        L.add(kpi([kx, 700, 220, 116], label, value, delta=delta, theme=TH))
        kx += 236
    L.add(badge([M, 850, 150, 26], "ISO 9001 Certified", tone="accent", theme=TH))
    L.add(pill([M + 168, 850, 150, 26], "B-Corp Pending", theme=TH))
    footer(L, 3)

    # ---- P4 SERVICES ------------------------------------------------------ #
    p = doc.page("services", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "02 — SERVICES", "What We Do", "End-to-end product design and engineering.")
    services = [
        ("UX Research", "Interviews, journey maps and usability testing that ground every decision."),
        ("UI Design", "Pixel-perfect interfaces and a scalable design system in Figma."),
        ("Webflow Build", "Hand-crafted, CMS-driven sites that your team can edit with ease."),
        ("Brand Identity", "Logo, type and a visual language that sets you apart."),
        ("SEO & Content", "Technical SEO, copy and structure tuned for organic growth."),
        ("Care Plans", "Ongoing optimisation, A/B testing and reliable support."),
    ]
    cw, ch, gx, gy = 224, 178, 20, 20
    x0, y0 = M, 230
    for i, (title, desc) in enumerate(services):
        cx = x0 + (i % 3) * (cw + gx)
        cy = y0 + (i // 3) * (ch + gy)
        panel = card([cx, cy, cw, ch], theme=TH)
        L.add(panel.object)
        bx, by, bw, bh = panel.content
        L.rect([bx, by, 40, 40], fill=GOLD_SOFT, radius=10, decorative=True)
        L.text([bx, by, 40, 40], "◆", style=txt(18, color=GOLD_DK, weight=800,
               align="center", valign="middle"))
        L.text([bx, by + 54, bw, 22], title, style=txt(17, color=INK, weight=700))
        L.text([bx, by + 82, bw, 70], desc, style=txt(12.5, color=SUB, wrap=True, line_height=1.5))
    footer(L, 4)

    # ---- P5 PROCESS ------------------------------------------------------- #
    p = doc.page("process", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "03 — PROCESS", "Our Process", "A proven four-phase engagement.")
    steps = [("01", "Discover", "Workshops, audits and goals."),
             ("02", "Design", "Wireframes, UI and prototypes."),
             ("03", "Develop", "Build, integrate and QA."),
             ("04", "Deliver", "Launch, train and optimise.")]
    cy = 360
    n = len(steps)
    span = W - 2 * M
    gap = span / n
    L.line([M + gap / 2, cy], [M + span - gap / 2, cy], stroke=LINE,
           stroke_style={"stroke_width": 3}, decorative=True)
    for i, (num, title, desc) in enumerate(steps):
        ccx = M + gap / 2 + i * gap
        col = GOLD if i <= 1 else "#FFFFFF"
        L.add({"type": "ellipse", "center": [ccx, cy], "rx": 38, "ry": 38,
               "fill": col, "stroke": GOLD if i <= 1 else LINE,
               "stroke_style": {"stroke_width": 3}})
        L.text([ccx - 38, cy - 16, 76, 32], num,
               style=txt(26, color="#FFFFFF" if i <= 1 else MUTED, weight=800,
                         align="center", valign="middle"))
        L.text([ccx - gap / 2 + 8, cy + 64, gap - 16, 22], title,
               style=txt(18, color=INK, weight=700, align="center"))
        L.text([ccx - gap / 2 + 8, cy + 92, gap - 16, 60], desc, style=txt(12.5, color=SUB, wrap=True, align="center", line_height=1.5))
        if i < n - 1:
            ax = ccx + gap - 38
            L.polygon([[ax - 6, cy - 7], [ax + 6, cy], [ax - 6, cy + 7]], fill=GOLD)
    L.text([M, 640, 300, 22], "Current phase", style=txt(13, color=MUTED,
           weight=700, letter_spacing=1))
    L.add(progress([M, 672, W - 2 * M, 12], 0.5, theme=TH))
    L.text([M, 694, 300, 20], "Phase 2 of 4 · Design", style=txt(13, color=INK, weight=700))
    L.text([W - M - 200, 694, 200, 20], "≈ 9 weeks total", style=txt(13, color=SUB,
           weight=600, align="right"))
    footer(L, 5)

    # ---- P6 TIMELINE (bar chart + milestones) ----------------------------- #
    p = doc.page("timeline", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "04 — TIMELINE", "Project Timeline", "Effort by phase, in working days.")
    ch_box = (M + 56, 250, W - 2 * M - 70, 230)
    fr = Frame(domain=(0, 0, 5, 25), box=ch_box)
    chart = Chart(frame=fr)
    data = [(0.5, 10), (1.5, 18), (2.5, 22), (3.5, 14), (4.5, 8)]
    chart.axes(x_ticks=[], y_ticks=[0, 5, 10, 15, 20, 25], grid=True)
    chart.bars(data, fill=GOLD, width=46, radius=4, label="Days")
    chart.add_to(L)
    phases = ["Discover", "Design", "Develop", "Deliver", "Care"]
    for i, name in enumerate(phases):
        px = ch_box[0] + (i + 0.5) / 5 * ch_box[2]
        L.text([px - 50, ch_box[1] + ch_box[3] + 10, 100, 18], name,
               style=txt(12, color=SUB, weight=600, align="center"))
    rows = [
        ["Kickoff workshop", "Week 1", "Discover"],
        ["Design system + UI", "Week 3", "Design"],
        ["Build & integrations", "Week 6", "Develop"],
        ["Launch", "Week 9", "Deliver"],
    ]
    tbl = table([M, 560, W - 2 * M, 250],
                [{"label": "Milestone", "width": "60%"},
                 {"label": "Target", "width": "20%"},
                 {"label": "Phase", "width": "20%", "align": "right"}],
                rows, theme=TH, row_height=46)
    tbl["style"] = {"header_fill": CHARCOAL,
                    "header_text": {"color": "#FFFFFF", "font_weight": 700}}
    L.add(tbl)
    footer(L, 6)

    # ---- P7 IMPACT (line chart + KPIs) ------------------------------------ #
    p = doc.page("impact", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "05 — IMPACT", "Projected Impact", "What success looks like in 6 months.")
    fr = Frame(domain=(0, 0, 6, 100), box=(M + 56, 250, W - 2 * M - 70, 250))
    chart = Chart(frame=fr)
    base = [(0, 30), (1, 38), (2, 41), (3, 55), (4, 68), (5, 72), (6, 84)]
    old = [(0, 30), (1, 31), (2, 33), (3, 34), (4, 36), (5, 37), (6, 39)]
    chart.axes(x_ticks=[0, 1, 2, 3, 4, 5, 6], y_ticks=[0, 25, 50, 75, 100],
               grid=True, x_format=lambda v: f"M{int(v)}")
    chart.line(old, stroke=MUTED, width=2.5, label="Current")
    chart.line(base, stroke=GOLD, width=3.5, label="Projected", smooth=True)
    chart.legend(at="tr")
    chart.add_to(L)
    kx = M
    for label, value, delta, down in [("Conversion", "+38%", "▲ vs today", False),
                                       ("Bounce rate", "-24%", "▼ improved", True),
                                       ("Avg. order value", "+19%", "▲ projected", False)]:
        L.add(kpi([kx, 580, 220, 116], label, value, delta=delta, down=down, theme=TH))
        kx += 236
    footer(L, 7)

    # ---- P8 PRICING ------------------------------------------------------- #
    p = doc.page("pricing", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "06 — PRICING", "Packages & Pricing", "Transparent, fixed-scope engagements.")
    tiers = [
        ("Starter", "$6k", ["5-page site", "Template design", "2 revisions", "Launch support"], False),
        ("Growth", "$14k", ["Up to 15 pages", "Custom UI system", "CMS + blog", "SEO setup", "Priority support"], True),
        ("Scale", "$28k", ["Unlimited pages", "Full brand identity", "Integrations", "A/B testing", "Dedicated team"], False),
    ]
    cw, gap = 224, 20
    x0, y0, chh = M, 240, 470
    for i, (name, price, feats, rec) in enumerate(tiers):
        cx = x0 + i * (cw + gap)
        if rec:
            L.add({"type": "rect", "box": [cx, y0 - 16, cw, chh + 16], "fill": "#FFFFFF",
                   "stroke": GOLD, "stroke_style": {"stroke_width": 2}, "radius": 14,
                   "style": {"box_shadow": [{"offset_x": 0, "offset_y": 14, "blur": 34, "color": "#000000"}]}})
            L.add(badge([cx + cw / 2 - 56, y0 - 30, 112, 26], "RECOMMENDED",
                        tone="accent", theme=TH))
            head_fill = GOLD
        else:
            L.rect([cx, y0, cw, chh], fill="#FFFFFF", stroke=LINE,
                   stroke_style={"stroke_width": 1}, radius=14, decorative=True)
            head_fill = CHARCOAL
        L.rect([cx, y0, cw, 92], fill=head_fill, radius=14, decorative=True)
        L.rect([cx, y0 + 60, cw, 32], fill=head_fill, decorative=True)
        L.text([cx + 24, y0 + 22, cw - 48, 22], name,
               style=txt(16, color="#FFFFFF", weight=700, letter_spacing=1))
        L.text([cx + 24, y0 + 44, cw - 48, 40], price,
               style=txt(34, color="#FFFFFF", weight=800))
        fy = y0 + 120
        for feat in feats:
            L.add({"type": "ellipse", "center": [cx + 30, fy + 8], "rx": 8, "ry": 8,
                   "fill": GOLD_SOFT})
            L.text([cx + 24, fy + 1, 14, 16], "✓", style=txt(11, color=GOLD_DK,
                   weight=800, align="center"))
            L.text([cx + 48, fy, cw - 70, 20], feat,
                   style=txt(13, color=SUB, weight=500))
            fy += 34
        L.add({"type": "rect", "box": [cx + 24, y0 + chh - 56, cw - 48, 40],
               "fill": GOLD if rec else PANEL, "radius": 8})
        L.text([cx + 24, y0 + chh - 56, cw - 48, 40], "Choose plan",
               style=txt(13, color="#FFFFFF" if rec else INK, weight=700,
                         align="center", valign="middle"))
    footer(L, 8)

    # ---- P9 TEAM ---------------------------------------------------------- #
    p = doc.page("team", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "07 — TEAM", "Meet the Team", "The people who will build your product.")
    team = [
        ("Maya Chen", "Creative Director", "MC"), ("Liam Ortega", "Lead Designer", "LO"),
        ("Noa Berg", "UX Researcher", "NB"), ("Ravi Patel", "Webflow Engineer", "RP"),
        ("Sofia Marín", "Brand Designer", "SM"), ("Tomáš Novak", "Front-end Dev", "TN"),
        ("Aisha Khan", "Content Lead", "AK"), ("Erik Lund", "Project Manager", "EL"),
    ]
    cols, cw, ch = 4, 170, 230
    gx = (W - 2 * M - cols * cw) / (cols - 1)
    x0, y0 = M, 250
    tones = ["accent", "neutral", "good", "warn"]
    for i, (name, role, init) in enumerate(team):
        cx = x0 + (i % cols) * (cw + gx)
        cy = y0 + (i // cols) * (ch + 28)
        L.rect([cx, cy, cw, ch], fill="#FFFFFF", stroke=LINE,
               stroke_style={"stroke_width": 1}, radius=14, decorative=True)
        L.add(avatar([cx + cw / 2 - 38, cy + 26, 76, 76], init,
                     tone=tones[i % len(tones)], theme=TH))
        L.text([cx + 10, cy + 122, cw - 20, 22], name,
               style=txt(15, color=INK, weight=700, align="center"))
        L.text([cx + 10, cy + 146, cw - 20, 18], role,
               style=txt(12, color=GOLD_DK, weight=600, align="center"))
        L.rect([cx + cw / 2 - 16, cy + 174, 32, 3], fill=GOLD, radius=1.5,
               decorative=True)
        L.text([cx + 10, cy + 188, cw - 20, 30], "@" + init.lower() + ".aurora",
               style=txt(11, color=MUTED, weight=500, align="center"))
    footer(L, 9)

    # ---- P10 COMPARE TABLE ------------------------------------------------ #
    p = doc.page("compare", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "08 — COMPARE", "Compare Packages", "Every feature, side by side.")
    cmp_rows = [
        ["Custom UI design", "—", "✓", "✓"],
        ["CMS & blog", "—", "✓", "✓"],
        ["Pages included", "5", "15", "∞"],
        ["SEO setup", "—", "✓", "✓"],
        ["A/B testing", "—", "—", "✓"],
        ["Brand identity", "—", "—", "✓"],
        ["Support window", "30 days", "90 days", "12 months"],
        ["Dedicated team", "—", "—", "✓"],
    ]
    tbl = table([M, 240, W - 2 * M, 560],
                [{"label": "Feature", "width": "46%"},
                 {"label": "Starter", "width": "18%", "align": "center"},
                 {"label": "Growth", "width": "18%", "align": "center"},
                 {"label": "Scale", "width": "18%", "align": "center"}],
                cmp_rows, theme=TH, row_height=58, header_height=48)
    tbl["style"] = {"header_fill": CHARCOAL,
                    "header_text": {"color": "#FFFFFF", "font_weight": 700}}
    L.add(tbl)
    L.text([M, 824, W - 2 * M, 20], "All packages include hosting setup, analytics and a launch checklist.",
           style=txt(12, color=MUTED, weight=500))
    footer(L, 10)

    # ---- P11 TESTIMONIALS ------------------------------------------------- #
    p = doc.page("words", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    marble(L)
    header(L, "09 — TESTIMONIALS", "Kind Words", "What our clients say.")
    quotes = [
        ("The new site doubled our signups in a quarter. The team just gets it.",
         "Dana Whitfield", "CEO, Northwind", "DW"),
        ("A flawless process from kickoff to launch. Beautiful, fast, on time.",
         "Marcus Reed", "CMO, Linework", "MR"),
        ("Our conversion rate has never been higher. Worth every cent.",
         "Priya Anand", "Founder, Bloom", "PA"),
    ]
    y = 240
    for quote, name, role, init in quotes:
        L.add({"type": "rect", "box": [M, y, W - 2 * M, 180], "fill": "#FFFFFF",
               "stroke": LINE, "stroke_style": {"stroke_width": 1}, "radius": 14,
               "style": {"box_shadow": [{"offset_x": 0, "offset_y": 8, "blur": 22, "color": "#000000"}]}})
        L.text([M + 28, y + 6, 80, 60], "“", style=txt(72, color=GOLD, weight=800))
        stars(L, M + 28, y + 96, 5, 8)
        L.text([M + 110, y + 30, W - 2 * M - 150, 70], quote, style=txt(17, color=INK, weight=600, wrap=True, line_height=1.5))
        L.add(avatar([W - M - 86, y + 56, 56, 56], init, tone="accent", theme=TH))
        L.text([M + 110, y + 120, 300, 20], name, style=txt(14, color=INK, weight=700))
        L.text([M + 110, y + 142, 300, 18], role, style=txt(12, color=MUTED, weight=500))
        y += 200
    footer(L, 11)

    # ---- P12 CONTACT / BACK COVER ----------------------------------------- #
    p = doc.page("contact", canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    L = p.layer("main")
    L.rect([0, 0, W, H], fill=linear_gradient([("#26292F", 0), ("#16181B", 100)],
           angle=160), decorative=True)
    L.polygon([[0, 0], [320, 0], [0, 240]], fill=GOLD)
    L.polygon([[0, 0], [170, 0], [0, 130]], fill=GOLD_DK)
    L.polygon([[W, H], [W - 300, H], [W, H - 300]], fill="#2E3137")
    brandmark(L, M, 96, 52)
    L.text([M, 300, W - 2 * M, 30], "LET'S BUILD SOMETHING",
           style=txt(18, color=GOLD, weight=800, letter_spacing=3))
    L.text([M, 332, W - 2 * M, 76], "great together.",
           style=txt(64, color="#FFFFFF", weight=800, letter_spacing=-1.5))
    L.text([M, 430, 560, 80], "Ready to start? Reach out and we'll send a tailored "
           "statement of work within two business days.", style=txt(16, color="#C9CCD2", weight=400, wrap=True, line_height=1.6))
    contacts = [("Email", "hello@studioaurora.design"), ("Phone", "+1 (415) 555-0148"),
                ("Web", "studioaurora.design")]
    cy = 560
    for label, value in contacts:
        L.rect([M, cy, W - 2 * M, 60], fill="#2E3137", radius=10, decorative=True)
        L.text([M + 24, cy, 120, 60], label.upper(), style=txt(12, color=GOLD,
               weight=800, letter_spacing=1, valign="middle"))
        L.text([M + 150, cy, W - 2 * M - 170, 60], value,
               style=txt(18, color="#FFFFFF", weight=600, valign="middle"))
        cy += 74
    L.add({"type": "rect", "box": [M, cy + 10, 260, 52], "fill": GOLD, "radius": 10})
    L.text([M, cy + 10, 260, 52], "Book a free call →",
           style=txt(16, color=CHARCOAL, weight=800, align="center", valign="middle"))
    for i, tag in enumerate(["Dribbble", "Behance", "LinkedIn", "Instagram"]):
        L.add(pill([M + 300 + i * 0, 0, 0, 0]) if False else
              {"type": "group", "box": [M + 300 + i * 96, cy + 22, 88, 30],
               "children": [
                   {"type": "rect", "box": [0, 0, 88, 30], "fill": "#33373E",
                    "radius": 15, "decorative": True},
                   {"type": "text", "box": [0, 0, 88, 30], "text": tag,
                    "style": txt(12, color="#FFFFFF", weight=600, align="center",
                                 valign="middle")}]})
    L.text([M, H - 70, W - 2 * M, 18], "Studio Aurora — Web Design Proposal · 2026 · "
           "Generated with FrameGraph", style=txt(11, color=MUTED, weight=500))

    return doc


doc = build_document()

if __name__ == "__main__":
    import sys
    doc.write(sys.argv[1] if len(sys.argv) > 1 else "web_design_proposal.fg.yaml",
              fail_on_error=True)
