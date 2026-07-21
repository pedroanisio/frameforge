"""Building Stunning Infographics — a 20-page designed field guide.

Design system: closed warm-paper palette (Chevreul duties, tone before hue),
Archivo (variable grotesque) for display over Fira Sans text, sizes from a
1.25 modular scale, 6-column grid, foot-weighted margins. Every page keeps
one focal mass balanced steelyard-fashion against the footer band.
"""

from frameforge.sdk import DocumentBuilder
from frameforge.sdk.chevreul import contrast_ratio
from frameforge.sdk.paint import stroke as _stroke

# ---------------------------------------------------------------- canvas ----
W, H = 1240, 1754                      # A4 portrait @ ~150 dpi
MX, MT, MB = 110, 118, 150             # margins: foot widest (canon)
CW = W - 2 * MX                        # content width = 1020
COLS, GUT = 6, 18
COLW = (CW - (COLS - 1) * GUT) / COLS  # 6-col grid unit

def col(i, span=1):
    """Left edge and width of a span starting at column i (0-based)."""
    x = MX + i * (COLW + GUT)
    w = span * COLW + (span - 1) * GUT
    return x, w

# --------------------------------------------------------------- palette ----
GROUND  = "#F6F1E7"   # warm paper — one ground, never two
INK     = "#2B2520"   # warm near-black ink (never pure #000)
MUTED   = "#6E6353"   # quiet step from the ink's own scale
FAINT   = "#B9AE9C"   # hairlines, ghost labels
PANEL   = "#ECE5D6"   # panel tint of the ground
ACCENT  = "#C2472E"   # vermilion — structure & emphasis only (~8 % area)
ACCENT2 = "#27584F"   # deep teal, subdued complement — data/positive duty
PAPER   = "#FBF8F2"   # card face, one tone above ground

# Verify legibility as tones BEFORE rendering (WCAG floors).
assert contrast_ratio(INK, GROUND) >= 4.5, "body ink fails 4.5:1"
assert contrast_ratio(MUTED, GROUND) >= 4.5, "muted text fails 4.5:1"
assert contrast_ratio(ACCENT2, GROUND) >= 4.5, "teal text fails 4.5:1"
assert contrast_ratio(ACCENT, GROUND) >= 3.0, "accent display fails 3:1"
assert contrast_ratio(GROUND, INK) >= 4.5, "reversed footer text fails 4.5:1"

# ------------------------------------------------------------ type scale ----
# Modular scale, base 21 px @ 150 dpi (~10 pt), ratio 1.25 (assertive).
S_SMALL, S_BODY, S_LEAD, S_H3, S_H2, S_H1 = 17, 21, 26, 33, 41, 51
S_STEP, S_COVER = 125, 100
SANS, DISPLAY, MONO = "Fira Sans", "Archivo", "Fira Mono"

doc = DocumentBuilder(title="Building Stunning Infographics", profile="report")

def ts(name, **kw):
    return doc.define_text_style(name, **kw)

ST_KICK  = ts("kick",  font_family=DISPLAY, font_size=S_SMALL, color=ACCENT,
              font_weight=700, letter_spacing=3.4)
ST_KICK2 = ts("kick2", font_family=DISPLAY, font_size=S_SMALL, color=MUTED,
              font_weight=600, letter_spacing=3.4)
ST_H1    = ts("h1",    font_family=DISPLAY, font_size=S_H1, color=INK,
              font_weight=700, line_height=1.06)
ST_H2    = ts("h2",    font_family=DISPLAY, font_size=S_H2, color=INK,
              font_weight=700, line_height=1.1)
ST_H3    = ts("h3",    font_family=DISPLAY, font_size=S_H3, color=INK,
              font_weight=650, line_height=1.12)
ST_CARDT = ts("cardt", font_family=DISPLAY, font_size=26, color=INK,
              font_weight=700, line_height=1.15)
ST_LEAD  = ts("lead",  font_family=SANS, font_size=S_LEAD, color=MUTED,
              line_height=1.4)
ST_BODY  = ts("body",  font_family=SANS, font_size=S_BODY, color=INK,
              line_height=1.45)
ST_BODYM = ts("bodym", font_family=SANS, font_size=S_BODY, color=MUTED,
              line_height=1.45)
ST_SMALL = ts("small", font_family=SANS, font_size=S_SMALL, color=MUTED,
              line_height=1.4)
ST_STEP  = ts("stepn", font_family=DISPLAY, font_size=S_STEP, color=ACCENT,
              font_weight=800, line_height=1.0)
ST_MONO  = ts("mono",  font_family=MONO, font_size=S_SMALL, color=ACCENT2,
              line_height=1.4)
ST_FOOT  = ts("foot",  font_family=DISPLAY, font_size=S_SMALL, color=GROUND,
              font_weight=600, letter_spacing=2.2)
ST_INV   = ts("inv",   font_family=SANS, font_size=S_BODY, color=GROUND,
              line_height=1.45)
ST_INVT  = ts("invt",  font_family=DISPLAY, font_size=26, color=GROUND,
              font_weight=700, letter_spacing=2.6)
ST_COVER = ts("cover", font_family=DISPLAY, font_size=S_COVER, color=INK,
              font_weight=800, line_height=1.02)
ST_WHITET = ts("whitet", font_family=DISPLAY, font_size=26, color=PAPER,
               font_weight=700, line_height=1.15)
ST_FOOT_R = ts("footr", font_family=DISPLAY, font_size=S_SMALL, color=GROUND,
               font_weight=600, letter_spacing=2.2, align="right")
ST_CARDT_C = ts("cardtc", font_family=DISPLAY, font_size=26, color=INK,
                font_weight=700, line_height=1.15, align="center")
ST_WHITET_C = ts("whitetc", font_family=DISPLAY, font_size=26, color=PAPER,
                 font_weight=700, line_height=1.15, align="center")
ST_SMALL_C = ts("smallc", font_family=SANS, font_size=S_SMALL, color=MUTED,
                line_height=1.4, align="center")

# ------------------------------------------------------------- scaffolds ----
PAGES = []

def scaffold(pid, kicker_text, page_no, footer_note="BUILDING STUNNING INFOGRAPHICS"):
    """Ground, kicker line, and the reversed footer band every page shares."""
    page = doc.page(pid, canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")
    main = page.layer("main")
    main.rect([0, 0, W, H], fill=GROUND)
    if kicker_text:
        main.text([MX, 64, CW - 120, 26], kicker_text, style=ST_KICK2)
        main.line([MX, 100], [W - MX, 100], **_stroke(1.5, color=FAINT))
    # Footer band: the answering mass at the foot (steelyard, not luck).
    main.rect([0, H - 64, W, 64], fill=INK)
    main.text([MX, H - 44, 700, 24], footer_note, style=ST_FOOT)
    main.text([W - MX - 80, H - 44, 80, 24], f"{page_no:02d} / 20",
              style=ST_FOOT_R)
    PAGES.append(page)
    return main

def kicker_accent(m, y, text):
    m.text([MX, y, CW, 26], text, style=ST_KICK)

def step_head(m, num, title, dek, y=150):
    """Step pages open on one heavy mass: the number, then the name."""
    m.text([MX - 8, y, 300, 140], num, style=ST_STEP)
    tx = MX + 218
    m.text([tx, y + 8, W - MX - tx, 60], title, style=ST_H1)
    m.text([tx, y + 78, W - MX - tx, 152], dek, style=ST_LEAD)
    m.line([MX, y + 238], [W - MX, y + 238], **_stroke(3, color=INK))
    return y + 272

def card(m, box, title, body, face=PAPER, bar=ACCENT2, title_style=None):
    x, y, w, h = box
    m.rect([x, y, w, h], fill=face)
    m.rect([x, y, 8, h], fill=bar)
    m.text([x + 26, y + 22, w - 44, 34], title, style=title_style or ST_CARDT)
    m.text([x + 26, y + 64, w - 44, h - 84], body, style=ST_BODY)

def action_strip(m, items, y=None, title="NOW IT'S YOUR TURN"):
    """The closing do-this rail: an ink mass above the footer."""
    y = y if y is not None else H - 264
    m.rect([MX, y, CW, 168], fill=INK)
    m.text([MX + 30, y + 24, 500, 30], title, style=ST_INVT)
    step_w = (CW - 60) / len(items)
    for i, item in enumerate(items):
        x = MX + 30 + i * step_w
        m.circle([x + 12, y + 84], 12, fill=ACCENT)
        m.text([x + 34, y + 66, step_w - 44, 94], item, style=ST_INV)

def challenge(m, y, q):
    """Design-challenge callout: one accent-ruled question."""
    m.line([MX, y], [MX, y + 106], **_stroke(5, color=ACCENT))
    m.text([MX + 26, y, 250, 24], "DESIGN CHALLENGE", style=ST_KICK)
    m.text([MX + 26, y + 30, CW - 52, 78], q, style=ST_BODYM)


# ================================================================ page 1 ----
# Cover: title mass upper-left, an abstract infographic column answering right.
m = scaffold("p01", None, 1, footer_note="A TEN-STEP FIELD GUIDE")
m.rect([0, 0, W, 14], fill=ACCENT)
m.text([MX, 200, 340, 26], "A FIELD GUIDE IN TEN STEPS", style=ST_KICK)
m.text([MX, 250, 760, 420], "Building\nStunning\nInfographics", style=ST_COVER)
m.text([MX, 620, 620, 130],
       "From the first question about your audience to the day you share it: "
       "a complete, practical method for turning data and ideas into one "
       "clear visual story.", style=ST_LEAD)
m.line([MX, 790], [MX + 620, 790], **_stroke(3, color=INK))
m.text([MX, 816, 620, 60],
       "Message  ·  Visual story  ·  Production  ·  Review  ·  Share",
       style=ST_BODYM)
# Cover motif: a tall abstract infographic (donut, bars, pictograms, spark).
cx, cw = 880, 250
m.rect([cx - 30, 200, cw + 60, 1240], fill=PANEL)
m.ring([cx + cw / 2, 330], 78, 46, fill=ACCENT2)
m.sector([cx + cw / 2, 330], 78, -90, 30, fill=ACCENT)
bars = [(0.55, ACCENT2), (0.8, ACCENT2), (1.0, ACCENT), (0.42, ACCENT2)]
for i, (f, c) in enumerate(bars):
    bh = int(220 * f)
    m.rect([cx + i * 62, 700 - bh, 44, bh], fill=c)
m.line([cx - 8, 700], [cx + 240, 700], **_stroke(3, color=INK))
for r in range(2):
    for i in range(5):
        px, py = cx + 10 + i * 48, 780 + r * 74
        filled = (r * 5 + i) < 7
        m.circle([px + 12, py + 12], 12, fill=(ACCENT if filled else FAINT))
        m.rect([px + 2, py + 30, 20, 30], fill=(ACCENT if filled else FAINT))
pts = [[cx - 6 + i * 42, 1020 - v] for i, v in
       enumerate([0, 34, 22, 66, 50, 96])]
m.polyline(pts, **_stroke(5, color=ACCENT2))
m.circle([pts[-1][0], pts[-1][1]], 8, fill=ACCENT)
m.rect([cx - 8, 1090, 250, 16], fill=INK)
m.rect([cx - 8, 1122, 190, 16], fill=MUTED)
m.rect([cx - 8, 1154, 220, 16], fill=MUTED)
m.rect([cx - 8, 1230, 250, 60], fill=ACCENT)
m.text([cx + 8, 1247, 220, 28], "CALL TO ACTION", style=ST_FOOT)

# ================================================================ page 2 ----
m = scaffold("p02", "THE METHOD", 2)
m.text([MX, 150, CW, 60], "Ten steps, three movements", style=ST_H1)
m.text([MX, 224, 900, 148],
       "An infographic is designed backwards from its reader. The method "
       "moves from message to visual story to production — each step feeds "
       "the next, and every later decision answers to the first three.",
       style=ST_LEAD)
part_data = [
    ("PART I — CRAFT A POWERFUL MESSAGE", ACCENT,
     [("1", "Identify your audience", "the WHO"),
      ("2", "Clarify the purpose", "the WHY"),
      ("3", "Create the story", "the WHAT")]),
    ("PART II — DESIGN A VISUAL STORY", ACCENT2,
     [("4", "Identify data & visuals", "evidence"),
      ("5", "Select a layout", "the stage"),
      ("6", "Choose design elements", "colour · type · flow"),
      ("7", "Sketch your ideas", "cheap drafts")]),
    ("PART III — BRING IT TO LIFE", INK,
     [("8", "Draft the infographic", "build"),
      ("9", "Review it", "four lenses"),
      ("10", "Revise, finalize, share", "ship")]),
]
y = 380
for label, tint, steps in part_data:
    m.text([MX, y, 700, 24], label, style=ST_KICK2)
    m.line([MX, y + 34], [W - MX, y + 34], **_stroke(2, color=FAINT))
    sw = (CW - (len(steps) - 1) * 24) / len(steps)
    for i, (n, t, s) in enumerate(steps):
        x = MX + i * (sw + 24)
        m.rect([x, y + 56, sw, 190], fill=PAPER)
        m.rect([x, y + 56, sw, 10], fill=tint)
        m.text([x + 22, y + 78, sw - 40, 66],
               n, style=ST_H2)
        m.text([x + 22, y + 150, sw - 40, 60], t, style=ST_CARDT)
        m.text([x + 22, y + 208, sw - 40, 28], s.upper(), style=ST_KICK2)
        if i < len(steps) - 1:
            ax = x + sw + 3
            m.line([ax, y + 150], [ax + 18, y + 150], **_stroke(3, color=MUTED))
    y += 300
m.text([MX, y + 6, CW, 66],
       "Checkpoint rule: at the end of each part, re-read your purpose "
       "statement. If a page element no longer serves it, the element goes.",
       style=ST_BODYM)

# ================================================================ page 3 ----
m = scaffold("p03", "FOUNDATIONS", 3)
m.text([MX, 150, CW, 60], "Why infographics work", style=ST_H1)
m.text([MX, 224, 620, 176],
       "An infographic tells a data story. It packages content into "
       "visually appealing, consumable chunks — improving understanding "
       "and perception, and starting conversation around the story it "
       "tells.", style=ST_LEAD)
for i, (t, b) in enumerate([
        ("It compresses", "One page carries what a memo takes ten to say — "
         "the reader grasps structure before reading a word."),
        ("It travels", "A single image moves through websites, newsletters, "
         "and social feeds — reaching audiences a report never will."),
        ("It persuades", "Pairing evidence with story engages both judgement "
         "and attention: the data earns trust, the design earns time.")]):
    x, w = col(0, 2)
    x = MX + i * (w + GUT) if False else col(i * 2, 2)[0]
    card(m, [x, 410, w, 244], t, b)
# Anatomy of the form, labelled.
m.text([MX, 672, 500, 40], "Anatomy of the form", style=ST_H3)
ax, ay, aw, ah = MX, 720, 360, 700
m.rect([ax, ay, aw, ah], fill=PAPER)
m.rect([ax, ay, aw, 74], fill=INK)
m.text([ax + 20, ay + 24, aw - 40, 30], "ENGAGING TITLE", style=ST_FOOT)
m.rect([ax + 20, ay + 96, aw - 40, 56], fill=PANEL)
m.rect([ax + 20, ay + 172, aw - 40, 120], fill=ACCENT)
m.text([ax + 40, ay + 216, aw - 80, 40], "CENTRAL MESSAGE", style=ST_FOOT)
for i in range(3):
    m.rect([ax + 20 + i * ((aw - 40 - 24) / 3 + 12),
            ay + 316, (aw - 40 - 24) / 3, 130], fill=PANEL)
m.rect([ax + 20, ay + 470, aw - 40, 90], fill=PANEL)
m.rect([ax + 20, ay + 584, aw - 40, 64], fill=ACCENT2)
m.text([ax + 40, ay + 604, aw - 80, 28], "CALL TO ACTION", style=ST_FOOT)
labels = [
    ("A title that hooks the audience it was written for", ay + 26),
    ("An introduction that sets the scene — the foundation the reader "
     "needs to grasp what follows", ay + 110),
    ("The one message everything else exists to support", ay + 220),
    ("Evidence in consumable chunks: data displays, icon arrays, "
     "illustrations — each one tied to the message", ay + 360),
    ("A conclusion that closes the loop on the purpose", ay + 495),
    ("A call to action that tells the reader what to do next", ay + 600)]
for text, ly in labels:
    m.line([ax + aw + 14, ly + 12], [ax + aw + 44, ly + 12],
           **_stroke(2, color=ACCENT))
    m.text([ax + aw + 56, ly, W - MX - ax - aw - 60, 78], text, style=ST_BODY)

# ================================================================ page 4 ----
m = scaffold("p04", "PART I — CRAFT A POWERFUL MESSAGE", 4)
y = step_head(m, "1", "Identify your audience",
              "Every choice that follows — data, layout, colour, channel — "
              "belongs to the reader, not to you. Name them first.")
m.text([MX, y, 460, 34], "Ask of every audience", style=ST_H3)
for i, q in enumerate([
        "WHO are the stakeholders for this story?",
        "WHAT information do they need from it?",
        "HOW will they meet it — print in hand, or a phone screen?",
        "WHERE will it reach them: report, website, feed?"]):
    m.circle([MX + 14, y + 66 + i * 68], 5, fill=ACCENT)
    m.text([MX + 38, y + 50 + i * 68, 440, 62], q, style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 490, 34], "What each reader needs", style=ST_H3)
for i, (who, want) in enumerate([
        ("Funders", "evidence of cost-effectiveness and results"),
        ("Policymakers", "broad statistics they can act on and repeat"),
        ("Practitioners", "figures that motivate the daily work"),
        ("General public", "a story that needs no prior context")]):
    cy = y + 52 + i * 96
    m.rect([x2, cy, W - MX - x2, 84], fill=PAPER)
    m.rect([x2, cy, 8, 84], fill=ACCENT2)
    m.text([x2 + 24, cy + 14, 220, 30], who, style=ST_CARDT)
    m.text([x2 + 24, cy + 48, W - MX - x2 - 40, 30], want, style=ST_BODYM)
challenge(m, 1330,
          "Serving multiple audiences at once? Design for the primary one, "
          "then check nothing actively confuses the others.")
action_strip(m, [
    "Write one sentence naming your primary audience.",
    "List the three things they already know.",
    "Decide the device or surface they will meet it on."])

# ================================================================ page 5 ----
m = scaffold("p05", "PART I — CRAFT A POWERFUL MESSAGE", 5)
y = step_head(m, "2", "Clarify the purpose",
              "The why. Being exceptionally clear about purpose — and holding "
              "every later design decision to it — is what makes an "
              "infographic a powerful communication tool.")
hub_x, hub_y, hub_r = W / 2, y + 300, 118
for ang, label in [(-150, "Story"), (-90, "Data"), (-30, "Layout"),
                   (30, "Design"), (90, "Draft"), (150, "Share")]:
    import math
    ex = hub_x + math.cos(math.radians(ang)) * 300
    ey = hub_y + math.sin(math.radians(ang)) * 210
    m.line([hub_x, hub_y], [ex, ey], **_stroke(2, color=FAINT))
    m.circle([ex, ey], 56, fill=PAPER)
    m.text([ex - 52, ey - 14, 104, 28], label, style=ST_CARDT_C)
m.circle([hub_x, hub_y], hub_r, fill=ACCENT)
m.text([hub_x - 90, hub_y - 30, 180, 60], "PURPOSE", style=ST_WHITET_C)
m.text([MX, y + 560, CW, 92],
       "Every spoke answers to the hub: when a chart, colour, or channel "
       "cannot say which part of the purpose it serves, it is decoration.",
       style=ST_BODYM)
challenge(m, 1330,
          "Part of a larger study? The infographic's purpose is narrower "
          "than the study's — one finding, sharply told, not all of them.")
action_strip(m, [
    "Complete: “This infographic exists so that ___ will ___.”",
    "Pin the sentence beside your screen.",
    "Test each later decision against it."])

# ================================================================ page 6 ----
m = scaffold("p06", "PART I — CRAFT A POWERFUL MESSAGE", 6)
y = step_head(m, "3", "Create the story",
              "The what. A story is not a by-product of populating a page "
              "with attractive images — it is decided here, before any "
              "visual exists.")
seq = [("TITLE", "An engaging title that earns the stop", ACCENT),
       ("INTRO", "The scene-setting the message needs", ACCENT2),
       ("CENTRAL MESSAGE", "The one thing you need to share", INK),
       ("CONCLUSION + CTA", "Reinforce the purpose; say what to do", ACCENT2)]
sw = (CW - 3 * 26) / 4
for i, (t, b, tint) in enumerate(seq):
    x = MX + i * (sw + 26)
    m.rect([x, y + 20, sw, 196], fill=PAPER)
    m.rect([x, y + 20, sw, 10], fill=tint)
    m.text([x + 18, y + 44, sw - 36, 52], t, style=ST_KICK if tint == ACCENT
           else ST_KICK2)
    m.text([x + 18, y + 100, sw - 36, 108], b, style=ST_BODY)
    if i < 3:
        axx = x + sw + 4
        m.line([axx, y + 104], [axx + 18, y + 104], **_stroke(3, color=MUTED))
m.text([MX, y + 268, 480, 34], "Titles that work harder", style=ST_H3)
m.text([MX, y + 314, 470, 150],
       "Lead with the finding, not the topic. “K–12 policy implementation: "
       "lessons learned” tells a reader what they will get and why to "
       "care — a label like “Study results” tells them nothing.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y + 268, 460, 34], "One message, sourced", style=ST_H3)
m.text([x2, y + 314, W - MX - x2, 150],
       "Develop a single compelling central message and conclude with "
       "purpose. Cite your sources on the graphic itself — credibility is "
       "part of the design.", style=ST_BODY)
challenge(m, 1330,
          "Can't compress the story? You are holding two messages — split "
          "them into two infographics rather than blur one.")
action_strip(m, [
    "Draft the title and central message as plain sentences.",
    "Write the intro a stranger would need.",
    "Choose the action the conclusion asks for."])


# ================================================================ page 7 ----
m = scaffold("p07", "PART II — DESIGN A VISUAL STORY", 7)
y = step_head(m, "4", "Identify data & visuals",
              "Working from the central message, decide which data are most "
              "relevant and how each will be shown. Visuals are evidence, "
              "not decoration.")
fams = [("Icons", "Compress a concept into a glyph; colourize, layer, and "
         "group them consistently."),
        ("Photographs", "Bring people and places into the story — licensed, "
         "and true to the audience's world."),
        ("Illustrations", "Explain what a camera cannot: processes, systems, "
         "the not-yet-built."),
        ("Data displays", "Charts and diagrams that carry the numbers behind "
         "the message.")]
sw = (CW - 3 * 22) / 4
for i, (t, b) in enumerate(fams):
    x = MX + i * (sw + 22)
    card(m, [x, y + 10, sw, 248], t, b)
m.text([MX, y + 290, 470, 34], "The icon-array effect", style=ST_H3)
m.text([MX, y + 334, 460, 150],
       "Readers process and recall people-like icons better than circles or "
       "abstract shapes. When the data is about people, let the marks be "
       "people — one glyph per unit, filled to the count.", style=ST_BODY)
ax0 = MX + 530
m.rect([ax0 - 20, y + 290, W - MX - ax0 + 20, 190], fill=PAPER)
for r in range(2):
    for i in range(5):
        px, py = ax0 + i * 78, y + 316 + r * 84
        filled = (r * 5 + i) < 7
        c = ACCENT2 if filled else FAINT
        m.circle([px + 16, py + 10], 11, fill=c)
        m.rect([px + 6, py + 26, 20, 34], fill=c)
m.text([ax0, y + 492, 400, 26], "e.g. “7 in 10 completed the program”",
       style=ST_MONO)
m.text([MX, y + 540, CW, 92],
       "Two duties before anything ships: visuals must be culturally "
       "sensitive to the audience reading them, and every image, icon, and "
       "photo must clear its licence.", style=ST_BODYM)
action_strip(m, [
    "List each claim the message makes.",
    "Attach one visual family to each claim.",
    "Check licences and cultural fit now, not at the end."])

# ================================================================ page 8 ----
m = scaffold("p08", "PART II — DESIGN A VISUAL STORY", 8)
m.text([MX, 150, CW, 60], "Choose the data display", style=ST_H1)
m.text([MX, 224, 900, 96],
       "One chart, one claim. Pick the form that shows the claim's shape — "
       "then strip everything the claim does not need.", style=ST_LEAD)
qw = (CW - 22) / 2
def chart_panel(x, y2, title, note):
    m.rect([x, y2, qw, 300], fill=PAPER)
    m.text([x + 24, y2 + 20, qw - 48, 30], title, style=ST_CARDT)
    m.text([x + 24, y2 + 250, qw - 48, 40], note, style=ST_SMALL)
    return x + 40, y2 + 80
bx, by = chart_panel(MX, 350, "Comparison — bars",
                     "Order the bars by value; label directly on the mark.")
for i, f in enumerate([0.45, 0.7, 1.0, 0.55]):
    bh = int(130 * f)
    m.rect([bx + i * 100, by + 140 - bh, 64, bh],
           fill=(ACCENT if f == 1.0 else ACCENT2))
m.line([bx - 6, by + 140], [bx + 380, by + 140], **_stroke(2.5, color=INK))
lx, ly = chart_panel(MX + qw + 22, 350, "Trend — line",
                     "Time runs left to right; mark the point that matters.")
pts = [[lx + i * 72, ly + 130 - v] for i, v in
       enumerate([8, 46, 30, 78, 60, 122])]
m.polyline(pts, **_stroke(5, color=ACCENT2))
m.circle([pts[-1][0], pts[-1][1]], 9, fill=ACCENT)
m.line([lx - 6, ly + 140], [lx + 380, ly + 140], **_stroke(2.5, color=INK))
px_, py_ = chart_panel(MX, 690, "Part of a whole — donut",
                       "Few slices, one highlighted; percentages, labelled.")
m.ring([px_ + 160, py_ + 70, ], 92, 54, fill=ACCENT2)
m.sector([px_ + 160, py_ + 70], 92, -90, 20, fill=ACCENT)
m.circle([px_ + 160, py_ + 70], 54, fill=PAPER)
sx, sy = chart_panel(MX + qw + 22, 690, "Relationship — scatter",
                     "Two measures per mark; let the cluster tell the story.")
import random
random.seed(7)
for _ in range(26):
    rx = sx + 20 + random.random() * 330
    ry = sy + 20 + (1 - (rx - sx - 20) / 360) * 110 + random.random() * 34
    m.circle([rx, ry], 6, fill=ACCENT2)
m.circle([sx + 320, sy + 34], 8, fill=ACCENT)
m.line([sx - 6, sy + 150], [sx + 374, sy + 150], **_stroke(2.5, color=INK))
m.text([MX, 1030, CW, 34], "Then remove the clutter", style=ST_H3)
for i, tip in enumerate([
        "Cut gridlines, borders, and legends the labels already replace.",
        "Multiple font treatments on one chart add noise, not order.",
        "If a cue adds no visual value — like an arrow nobody needs — "
        "delete it."]):
    m.circle([MX + 14, 1092 + i * 54], 5, fill=ACCENT)
    m.text([MX + 38, 1076 + i * 54, CW - 60, 48], tip, style=ST_BODY)
challenge(m, 1258,
          "Unsure between two chart forms? Sketch both and show a colleague "
          "for five seconds each — keep the one whose claim they can repeat.")

# ================================================================ page 9 ----
m = scaffold("p09", "PART II — DESIGN A VISUAL STORY", 9)
y = step_head(m, "5", "Select a layout",
              "Layout is the audience interface: where they meet the "
              "graphic decides its shape, size, and level of interaction.")
m.text([MX, y, 470, 34], "Format follows the surface", style=ST_H3)
m.rect([MX, y + 54, 150, 240], fill=PAPER)
m.rect([MX, y + 54, 150, 34], fill=ACCENT2)
m.text([MX + 170, y + 54, 300, 120],
       "Vertical scrolls with the web and phones — the default for feeds "
       "and pages.", style=ST_BODY)
m.rect([MX, y + 330, 240, 150], fill=PAPER)
m.rect([MX, y + 330, 34, 150], fill=ACCENT2)
m.text([MX + 260, y + 330, 210, 150],
       "Horizontal suits slides, screens, and side-by-side comparison.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 460, 34], "The interaction ladder", style=ST_H3)
for i, (t, b) in enumerate([
        ("Static", "print and PDF — one fixed reading"),
        ("Clickable", "regions link out to sources and detail"),
        ("Animated", "motion reveals the story in stages"),
        ("Video", "narrated data stories for feeds"),
        ("Interactive", "the reader explores their own path")]):
    cy = y + 50 + i * 88
    m.rect([x2, cy, W - MX - x2, 76], fill=PAPER)
    m.rect([x2, cy, 8, 76], fill=(ACCENT if i == 4 else ACCENT2))
    m.text([x2 + 24, cy + 12, 220, 28], t, style=ST_CARDT)
    m.text([x2 + 24, cy + 44, W - MX - x2 - 40, 26], b, style=ST_SMALL)
challenge(m, 1330,
          "Scaling to a poster? Low-resolution visuals pixelate when "
          "enlarged, and white space that felt right on screen can gape at "
          "wall size — re-check both at true scale.")
action_strip(m, [
    "Name the primary surface: print, page, feed, or wall.",
    "Pick orientation from the surface, not from habit.",
    "Choose the lowest interaction level that serves the purpose."])

# =============================================================== page 10 ----
m = scaffold("p10", "PART II — DESIGN A VISUAL STORY", 10)
m.text([MX, 150, CW, 60], "The grid does the hand-holding", style=ST_H1)
m.text([MX, 224, 900, 132],
       "Hierarchy is visual hand-holding: putting information in groups, "
       "columns, and levels tells the reader where to begin and what to "
       "read next. A grid makes that order repeatable.", style=ST_LEAD)
grids = [("Manuscript", "one column of continuous story"),
         ("Multicolumn", "parallel threads and comparisons"),
         ("Modular", "cards of equal-weight chunks"),
         ("Hierarchical", "zones sized by importance")]
sw = (CW - 3 * 22) / 4
for i, (t, b) in enumerate(grids):
    x = MX + i * (sw + 22)
    m.rect([x, 380, sw, 292], fill=PAPER)
    gx, gy, gw2 = x + 20, 400, sw - 40
    if i == 0:
        m.rect([gx, gy, gw2, 180], fill=PANEL)
    elif i == 1:
        for c in range(2):
            m.rect([gx + c * (gw2 / 2 + 6) - (6 if c else 0), gy,
                    gw2 / 2 - 3, 180], fill=PANEL)
    elif i == 2:
        for r in range(2):
            for c in range(2):
                m.rect([gx + c * (gw2 / 2 + 6) - (6 if c else 0),
                        gy + r * 96, gw2 / 2 - 3, 84], fill=PANEL)
    else:
        m.rect([gx, gy, gw2, 108], fill=ACCENT2)
        m.rect([gx, gy + 120, gw2 / 2 - 3, 60], fill=PANEL)
        m.rect([gx + gw2 / 2 + 3, gy + 120, gw2 / 2 - 3, 60], fill=PANEL)
    m.text([x + 20, 596, sw - 40, 30], t, style=ST_CARDT)
    m.text([x + 20, 630, sw - 40, 50], b, style=ST_SMALL)
m.text([MX, 712, 470, 34], "Balance the attractions", style=ST_H3)
m.text([MX, 758, 460, 210],
       "Everything on the page pulls at the eye — darker, larger, more "
       "eccentric pulls harder. Balance like a steelyard: a heavy element "
       "near the axis, answered by a small one far from it. Sections and "
       "white space then steer the eye toward the central message.",
       style=ST_BODY)
bx0 = MX + 530
m.rect([bx0, 712, W - MX - bx0, 230], fill=PAPER)
fx = bx0 + (W - MX - bx0) / 2
m.line([fx, 742], [fx, 892], **_stroke(2, color=FAINT))
m.line([bx0 + 40, 892], [W - MX - 40, 892], **_stroke(3, color=INK))
m.rect([fx - 150, 802, 120, 90], fill=ACCENT)
m.rect([fx + 170, 856, 44, 36], fill=ACCENT2)
m.text([bx0 + 24, 952, W - MX - bx0 - 48, 50],
       "heavy near the axis · light far out — repose without symmetry",
       style=ST_SMALL)
challenge(m, 1330,
          "A section nobody reads? It is either off-grid, off-message, or "
          "both — move it onto the grid or move it out of the graphic.")
action_strip(m, [
    "Choose a grid family before placing anything.",
    "Assign each story section a zone sized by importance.",
    "Squint: one focal mass, answered — not five shouting."])

# =============================================================== page 11 ----
m = scaffold("p11", "PART II — DESIGN A VISUAL STORY", 11)
y = step_head(m, "6", "Colour with intention",
              "Select one scheme that serves the audience and message, "
              "assign each colour a duty, and apply it consistently to "
              "every element — colour is information, not paint.")
duties = [(GROUND, "GROUND", "one paper — the field everything sits on"),
          (INK, "INK", "near-black for text; never pure black"),
          (MUTED, "QUIET", "greys from the ink's own scale"),
          (ACCENT, "ACCENT", "one hue, one duty: emphasis"),
          (ACCENT2, "SECOND", "its complement, subdued — data")]
sw = (CW - 4 * 20) / 5
for i, (c, t, b) in enumerate(duties):
    x = MX + i * (sw + 20)
    m.rect([x, y + 10, sw, 96], fill=c)
    if c == GROUND:
        m.rect([x, y + 10, sw, 96], fill="none", **_stroke(2, color=FAINT))
    m.text([x, y + 122, sw, 24], t, style=ST_KICK2)
    m.text([x, y + 150, sw, 72], b, style=ST_SMALL)
m.text([MX, y + 250, 500, 34], "Dose it like a page", style=ST_H3)
m.rect([MX, y + 300, int(CW * 0.62), 44], fill=GROUND)
m.rect([MX, y + 300, int(CW * 0.62), 44], fill="none", **_stroke(2, color=FAINT))
m.rect([MX + int(CW * 0.62), y + 300, int(CW * 0.30), 44], fill=INK)
m.rect([MX + int(CW * 0.92), y + 300, CW - int(CW * 0.92), 44], fill=ACCENT)
m.text([MX, y + 354, CW, 26],
       "ground ~62 %   ·   text & structure ~30 %   ·   accent ~8 %",
       style=ST_MONO)
m.text([MX, y + 420, 470, 34], "The grey test", style=ST_H3)
m.text([MX, y + 464, 460, 156],
       "Drain the design of hue. If the hierarchy still reads in greyscale, "
       "it was built in tone and will survive print, projection, and every "
       "reader's eyes. If it dissolves, it trusted hue alone.", style=ST_BODY)
gx0 = MX + 530
for k, (c1, c2, c3) in enumerate([(ACCENT, ACCENT2, PANEL),
                                  ("#6B6B6B", "#4A4A4A", "#DDDDDD")]):
    ox = gx0 + k * 240
    m.rect([ox, y + 420, 210, 170], fill=PAPER)
    m.rect([ox + 18, y + 438, 80, 60], fill=c1)
    m.rect([ox + 112, y + 438, 80, 100], fill=c2)
    m.rect([ox + 18, y + 512, 80, 60], fill=c3)
    m.text([ox + 18, y + 552, 174, 24],
           "in colour" if k == 0 else "in grey — still reads",
           style=ST_SMALL)
challenge(m, 1330,
          "Need a second accent? Take the first accent's complement, "
          "subdued — never both at full strength and equal area.")
action_strip(m, [
    "Pick the scheme; write each colour's duty beside its swatch.",
    "Apply colours to elements consistently, page-wide.",
    "Print it grey once before anyone sees it in colour."])

# =============================================================== page 12 ----
m = scaffold("p12", "PART II — DESIGN A VISUAL STORY", 12)
y = step_head(m, "6", "Type that stays harmonious",
              "Fonts carry the reading. Choose few, size them from one "
              "scale, and let size — not decoration — express hierarchy.",)
m.text([MX, y, 470, 34], "A working size ladder", style=ST_H3)
ladder = [("Display 51", S_H1, 700), ("Heading 41", S_H2, 700),
          ("Subhead 33", S_H3, 650), ("Body 21", S_BODY, 400),
          ("Caption 17", S_SMALL, 400)]
ly2 = y + 50
for label, size, wgt in ladder:
    stl = doc.define_text_style(f"lad{size}", font_family=DISPLAY if wgt >= 650
                                else SANS, font_size=size, color=INK,
                                font_weight=wgt)
    m.text([MX, ly2, 470, size + 14], label, style=stl)
    ly2 += size + 26
m.text([MX, ly2 + 8, 460, 116],
       "Each level is one scale step from the next — near enough to be "
       "family, far enough to be rank.", style=ST_BODYM)
x2 = MX + 530
m.text([x2, y, 490, 34], "Decoration isn't hierarchy", style=ST_H3)
m.rect([x2, y + 50, W - MX - x2, 150], fill=PAPER)
m.text([x2 + 24, y + 66, 60, 40], "✕", style=ST_H2)
m.text([x2 + 90, y + 74, W - MX - x2 - 110, 112],
       "Bolding, italicising, AND underlining the same line is visual "
       "clutter — three signals fighting for one job.", style=ST_BODY)
m.rect([x2, y + 220, W - MX - x2, 150], fill=PAPER)
m.rect([x2, y + 220, 8, 150], fill=ACCENT2)
m.text([x2 + 24, y + 236, 60, 40], "✓", style=ST_H2)
m.text([x2 + 90, y + 244, W - MX - x2 - 110, 112],
       "Use font size (and a single weight step) to rank information — "
       "one change, one meaning.", style=ST_BODY)
m.text([x2, y + 410, 460, 34], "Pairing rule", style=ST_H3)
m.text([x2, y + 454, W - MX - x2, 120],
       "One display face for structure, one text face for reading, and a "
       "mono for figures if the data needs it. Every face you add must "
       "earn its seat.", style=ST_BODY)
challenge(m, 1330,
          "Tempted by a decorative font? Set the title in it, squint, and "
          "ask whether the audience — not the designer — gains anything.")
action_strip(m, [
    "Choose the text face first, display second.",
    "Build the ladder from one ratio; delete odd sizes.",
    "Strip double treatments wherever two signals do one job."])

# =============================================================== page 13 ----
m = scaffold("p13", "PART II — DESIGN A VISUAL STORY", 13)
y = step_head(m, "6", "Flow and the focal point",
              "Decide where the eye lands first and the route it takes "
              "after — then make every cue on the page serve that route.")
m.text([MX, y, 460, 34], "Give the eye a route", style=ST_H3)
for k, (label, path_pts) in enumerate([
        ("Z-path — screens & posters",
         [[0, 0], [300, 0], [40, 170], [320, 190]]),
        ("Column path — scrolls & phones",
         [[160, 0], [160, 90], [160, 190]])]):
    ox, oy = MX + k * 250, y + 60
    m.rect([ox, oy, 220, 230], fill=PAPER)
    pts = [[ox + 30 + px * 0.53, oy + 24 + py * 0.9] for px, py in path_pts]
    m.polyline(pts, **_stroke(4, color=ACCENT2))
    m.circle([pts[0][0], pts[0][1]], 9, fill=ACCENT)
    m.text([ox + 12, oy + 240, 210, 68], label, style=ST_SMALL)
x2 = MX + 560
m.text([x2, y, 440, 34], "One focal point", style=ST_H3)
m.rect([x2, y + 60, 420, 230], fill=PAPER)
m.rect([x2 + 30, y + 88, 200, 130], fill=ACCENT)
m.rect([x2 + 250, y + 96, 70, 40], fill=PANEL)
m.rect([x2 + 250, y + 150, 70, 40], fill=PANEL)
m.rect([x2 + 330, y + 96, 70, 94], fill=PANEL)
m.text([x2, y + 300, 440, 116],
       "The largest, darkest, most eccentric element wins the first "
       "glance — award that win to the central message, deliberately.",
       style=ST_BODY)
m.text([MX, y + 420, CW, 96],
       "Cues must earn their keep: an arrow that guides nobody is clutter "
       "wearing a uniform. Add a cue only when the route fails without it — "
       "and cut it the moment it stops adding visual value.", style=ST_BODYM)
challenge(m, 1330,
          "Where does the eye go first? Show the draft for three seconds; "
          "if the answer is not the central message, re-weight the page.")
action_strip(m, [
    "Mark the intended first glance and route on your sketch.",
    "Size and tone the focal point to win — once.",
    "Audit every arrow, rule, and box: keep only working cues."])


# =============================================================== page 14 ----
m = scaffold("p14", "PART II — DESIGN A VISUAL STORY", 14)
y = step_head(m, "7", "Sketch your ideas",
              "Paper is the cheapest design software you will ever own. "
              "Sketch the layout before any tool renders a pixel.")
m.text([MX, y, 460, 34], "Basic sketch first", style=ST_H3)
sk_x, sk_y, sk_w, sk_h = MX, y + 54, 440, 520
m.rect([sk_x, sk_y, sk_w, sk_h], fill=PAPER)
wob = {"seed": 7, "roughen": 2.4, "drift_deg": 1.6}
m.rect([sk_x + 30, sk_y + 30, sk_w - 60, 60], fill="none", **_stroke(3, color=MUTED), humanize=wob)
m.rect([sk_x + 30, sk_y + 110, sk_w - 60, 120], fill="none", **_stroke(3, color=ACCENT), humanize=wob)
m.rect([sk_x + 30, sk_y + 250, 180, 130], fill="none", **_stroke(3, color=MUTED), humanize=wob)
m.rect([sk_x + 230, sk_y + 250, 180, 130], fill="none", **_stroke(3, color=MUTED), humanize=wob)
m.rect([sk_x + 30, sk_y + 400, sk_w - 60, 80], fill="none", **_stroke(3, color=MUTED), humanize=wob)
m.line([sk_x + 40, sk_y + 60], [sk_x + sk_w - 70, sk_y + 66],
       **_stroke(2.5, color=MUTED), humanize=wob)
m.text([sk_x + 46, sk_y + 150, 200, 30], "message", style=ST_MONO)
x2 = MX + 530
m.text([x2, y, 490, 34], "Then add detail", style=ST_H3)
m.text([x2, y + 50, W - MX - x2, 200],
       "The first pass places the story sections from your layout. The "
       "second pass adds the real title, the chosen visuals, and the flow "
       "cues — still on paper, still disposable. Move from Step 5's layout "
       "to a basic sketch, then to a detailed one, before opening any "
       "design platform.", style=ST_BODY)
m.rect([x2, y + 290, W - MX - x2, 254], fill=PAPER)
m.rect([x2, y + 290, 8, 254], fill=ACCENT2)
m.text([x2 + 26, y + 310, W - MX - x2 - 52, 30], "Why it works",
       style=ST_CARDT)
m.text([x2 + 26, y + 352, W - MX - x2 - 52, 176],
       "A sketch you can discard in ten seconds invites honest criticism; "
       "a polished draft defends itself. Iterate where iteration is "
       "cheapest — adjust the process to your own creative flow.",
       style=ST_BODY)
challenge(m, 1330,
          "Software pulling you toward its templates? Sketch the story "
          "first — then make the tool serve the sketch, not the reverse.")
action_strip(m, [
    "Sketch the layout zones from Step 5 in five minutes.",
    "Redraw once with title, visuals, and flow marked.",
    "Show it to one reader before you open the software."])

# =============================================================== page 15 ----
m = scaffold("p15", "PART III — BRING IT TO LIFE", 15)
y = step_head(m, "8", "Draft: platform & foundation",
              "Pick the platform that fits your skills and format, set the "
              "canvas, and lay the foundation before any content lands.")
m.text([MX, y, 470, 34], "Files that survive scaling", style=ST_H3)
vx, vy = MX, y + 54
m.rect([vx, vy, 220, 190], fill=PAPER)
m.polygon([[vx + 40, vy + 150], [vx + 110, vy + 30], [vx + 180, vy + 150]],
          fill="none", **_stroke(4, color=ACCENT2))
m.text([vx + 20, vy + 152, 190, 48], "vector — crisp at any size",
       style=ST_SMALL)
rx0, ry0 = MX + 240, y + 54
m.rect([rx0, ry0, 220, 190], fill=PAPER)
steps = [(60, 128), (80, 108), (100, 88), (120, 68), (140, 48), (160, 28)]
for sxx, syy in steps:
    m.rect([rx0 + sxx, ry0 + syy, 22, 22], fill=MUTED)
m.text([rx0 + 20, ry0 + 152, 200, 48], "raster — pixelates enlarged",
       style=ST_SMALL)
m.text([MX, y + 270, 460, 170],
       "Vector art (like SVG) scales cleanly and can carry interactivity; "
       "raster images suit photographs. Match the file type to the job "
       "and the final surface — especially before poster-scale output.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 490, 34], "Foundation, in order", style=ST_H3)
for i, (t, b) in enumerate([
        ("Size the canvas", "set final dimensions before placing anything"),
        ("Background", "the ground colour arrives first"),
        ("Sections", "zones from your layout, drawn as regions"),
        ("Visual cues", "rules and bands that mark the route")]):
    cy = y + 50 + i * 92
    m.rect([x2, cy, W - MX - x2, 80], fill=PAPER)
    m.text([x2 + 20, cy + 12, 44, 44], str(i + 1), style=ST_H3)
    m.text([x2 + 76, cy + 14, 300, 28], t, style=ST_CARDT)
    m.text([x2 + 76, cy + 46, W - MX - x2 - 96, 26], b, style=ST_SMALL)
challenge(m, 1330,
          "Choosing a platform? The best one is the one whose output "
          "format, licence terms, and learning curve fit this project — "
          "not the one with the most features.")
action_strip(m, [
    "Set canvas size from the chosen surface.",
    "Paint ground, then sections, then cues — in that order.",
    "Collect every visual as the right file type before building."])

# =============================================================== page 16 ----
m = scaffold("p16", "PART III — BRING IT TO LIFE", 16)
y = step_head(m, "8", "Draft: build the page",
              "Bring visuals and text in deliberately: build linearly "
              "through the storyline, or build outward around the focal "
              "point — never all at once, everywhere.")
bx1, by1 = MX, y + 40
m.rect([bx1, by1, 470, 300], fill=PAPER)
m.text([bx1 + 24, by1 + 18, 430, 30], "Build linearly", style=ST_CARDT)
for i in range(4):
    zy = by1 + 64 + i * 54
    m.rect([bx1 + 24, zy, 330, 40], fill=PANEL)
    m.text([bx1 + 366, zy + 6, 40, 30], str(i + 1), style=ST_H3)
m.text([bx1 + 24, by1 + 64 + 4 * 54 + 6, 430, 50],
       "top to bottom, section by section — the scroll's natural order",
       style=ST_SMALL)
bx2 = MX + 530
m.rect([bx2, by1, W - MX - bx2, 300], fill=PAPER)
m.text([bx2 + 24, by1 + 18, 400, 30], "Build around the focal point",
       style=ST_CARDT)
m.rect([bx2 + 150, by1 + 90, 170, 110], fill=ACCENT)
m.text([bx2 + 168, by1 + 128, 140, 30], "1", style=ST_WHITET)
for lbl, px2, py2 in [("2", bx2 + 60, by1 + 70), ("3", bx2 + 350, by1 + 84),
                      ("4", bx2 + 66, by1 + 196), ("5", bx2 + 356, by1 + 210)]:
    m.rect([px2, py2, 64, 48], fill=PANEL)
    m.text([px2 + 22, py2 + 8, 30, 30], lbl, style=ST_H3)
m.text([bx2 + 24, by1 + 250, 400, 26],
       "the message first; everything else placed in its orbit",
       style=ST_SMALL)
m.text([MX, y + 390, 470, 34], "Craft the parts", style=ST_H3)
for i, tip in enumerate([
        "Icons: colourize to the palette, then layer and group so they "
        "move as one object.",
        "Shapes: construct custom visuals from simple forms before "
        "reaching for stock art.",
        "Data displays: format them in the page's colours and type — a "
        "chart is not a screenshot."]):
    m.circle([MX + 14, y + 456 + i * 62], 5, fill=ACCENT)
    m.text([MX + 38, y + 438 + i * 62, CW - 60, 56], tip, style=ST_BODY)
challenge(m, 1330,
          "Placed everything and it still looks busy? Rebuild linearly: "
          "add one section at a time and stop when the story is told.")
action_strip(m, [
    "Choose your build order: linear or focal-first.",
    "Group each finished section before starting the next.",
    "Stop building the moment the story reads complete."])

# =============================================================== page 17 ----
m = scaffold("p17", "PART III — BRING IT TO LIFE", 17)
m.text([MX, 150, CW, 60], "Accessible is the baseline", style=ST_H1)
m.text([MX, 224, 900, 132],
       "Accessibility compliance is part of drafting, not a retrofit: if a "
       "reader cannot perceive the story, the story was not told.",
       style=ST_LEAD)
for i, (t, b) in enumerate([
        ("Contrast", "Text must stand on its ground in tone — check the "
         "ratio, not the vibe. Body text needs more than display."),
        ("Alt text", "Every meaningful image carries a text alternative "
         "that tells the same story to a screen reader."),
        ("Reading order", "The structure a sighted reader sees is the "
         "order assistive technology must traverse."),
        ("Never hue alone", "Colour-blind readers lose rank encoded only "
         "in hue — carry it on tone, position, or label too.")]):
    x = MX + (i % 2) * (CW / 2 + 11)
    cy = 360 + (i // 2) * 200
    card(m, [x, cy, CW / 2 - 11, 180], t, b)
m.text([MX, 790, 470, 34], "The legend, twice", style=ST_H3)
lx0, ly0 = MX, 840
m.rect([lx0, ly0, 470, 150], fill=PAPER)
m.text([lx0 + 24, ly0 + 14, 60, 40], "✕", style=ST_H2)
for j, c in enumerate(["#C24D2C", "#27584F", "#C2A22C"]):
    m.circle([lx0 + 110 + j * 110, ly0 + 46], 14, fill=c)
    m.text([lx0 + 132 + j * 110, ly0 + 34, 80, 24], "series", style=ST_SMALL)
m.text([lx0 + 24, ly0 + 92, 420, 52],
       "hue is the only difference — rank lost to 1 in 12 male readers",
       style=ST_SMALL)
lx1 = MX + 530
m.rect([lx1, ly0, W - MX - lx1, 150], fill=PAPER)
m.rect([lx1, ly0, 8, 150], fill=ACCENT2)
m.text([lx1 + 24, ly0 + 14, 60, 40], "✓", style=ST_H2)
labels2 = [("A · dark", INK), ("B · mid", MUTED), ("C · light", FAINT)]
for j, (lb, c) in enumerate(labels2):
    m.circle([lx1 + 110 + j * 120, ly0 + 46], 14, fill=c)
    m.text([lx1 + 96 + j * 120, ly0 + 70, 110, 24], lb, style=ST_SMALL)
m.text([lx1 + 24, ly0 + 96, W - MX - lx1 - 48, 40],
       "tone + label carry the rank; hue is free to add character",
       style=ST_SMALL)
m.text([MX, 1030, CW, 90],
       "Then remove clutter one last time: decoration that carries no "
       "information taxes every reader, and the readers using assistive "
       "technology pay it twice.", style=ST_BODYM)
challenge(m, 1330,
          "Print the draft in greyscale and read it at arm's length: "
          "whatever disappears was carried by hue alone — fix it in tone.")
action_strip(m, [
    "Check every text/ground pair as a tone ratio.",
    "Write alt text that tells the story, not the pixels.",
    "Re-read the page in greyscale before sign-off."])

# =============================================================== page 18 ----
m = scaffold("p18", "PART III — BRING IT TO LIFE", 18)
y = step_head(m, "9", "Review through four lenses",
              "A draft is a hypothesis. Review it deliberately — checklist "
              "in hand — before the audience reviews it for you.")
lenses = [("STORY", "Does the title hook? Does the intro set the scene? "
           "Is there exactly one central message, and does the "
           "conclusion reinforce the purpose?"),
          ("CONTENT", "Is every claim accurate and sourced? Is the data "
           "current, relevant, and honestly represented?"),
          ("DESIGN", "Do colour, type, flow, and focal point serve the "
           "message? Does the hierarchy read at a squint?"),
          ("VISUALS", "Is each visual the right family for its claim, "
           "licensed, culturally appropriate, and clutter-free?")]
sw = (CW - 22) / 2
for i, (t, b) in enumerate(lenses):
    x = MX + (i % 2) * (sw + 22)
    cy = y + 20 + (i // 2) * 246
    m.rect([x, cy, sw, 226], fill=PAPER)
    m.rect([x, cy, sw, 12], fill=(ACCENT if i % 3 == 0 else ACCENT2))
    m.text([x + 26, cy + 30, sw - 52, 30], t, style=ST_KICK)
    m.text([x + 26, cy + 68, sw - 52, 150], b, style=ST_BODY)
m.text([MX, y + 534, 470, 34], "Two speeds of review", style=ST_H3)
m.text([MX, y + 578, 460, 150],
       "Run quick-glance reviews for first impressions — the three-second "
       "test — and in-depth reviews for accuracy and design. They find "
       "different defects; you need both.", style=ST_BODY)
x2 = MX + 530
m.text([x2, y + 534, 490, 34], "Choosing reviewers", style=ST_H3)
m.text([x2, y + 578, W - MX - x2, 150],
       "Include members of the actual audience, a content expert, and a "
       "reviewer who can judge cultural appropriateness — the review "
       "process is where that question gets answered.", style=ST_BODY)
challenge(m, 1330,
          "Reviewers disagreeing? Weigh feedback against purpose and "
          "audience — not against who argued longest.")
action_strip(m, [
    "Run the three-second test with a fresh reader.",
    "Work the four-lens checklist top to bottom.",
    "Log every finding before fixing any of them."])

# =============================================================== page 19 ----
m = scaffold("p19", "PART III — BRING IT TO LIFE", 19)
y = step_head(m, "10", "Revise, finalize, share",
              "Iterate with discipline, finish deliberately, and put the "
              "graphic where its audience already is.")
m.text([MX, y, 470, 34], "Revise against the purpose", style=ST_H3)
import math as _math
cx0, cy0, cr = MX + 220, y + 240, 150
for k in range(4):
    a0 = -90 + k * 90
    m.sector([cx0, cy0], cr, a0 + 6, a0 + 78,
             fill=(ACCENT2 if k % 2 else PANEL))
lblc = [("revise", 0), ("align", 1), ("edit", 2), ("finalize", 3)]
for t, k in lblc:
    ang = _math.radians(-45 + k * 90)
    lx2 = cx0 + _math.cos(ang) * (cr + 44) - 40
    ly2 = cy0 + _math.sin(ang) * (cr + 44) - 12
    m.text([lx2, ly2, 96, 24], t, style=ST_SMALL_C)
m.circle([cx0, cy0], 74, fill=ACCENT)
m.text([cx0 - 64, cy0 - 26, 128, 52], "PURPOSE", style=ST_WHITET_C)
m.text([MX, y + 430, 460, 150],
       "With each change, check the infographic still aligns with its "
       "purpose and central message. Revision that drifts from the "
       "purpose is not polish — it is a new, unplanned graphic.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 490, 34], "Go where the audience is", style=ST_H3)
for i, (t, b) in enumerate([
        ("Landing page", "one home URL that everything else points to"),
        ("Social media", "sized and cropped for the feed it rides in"),
        ("Embedded in a report", "the graphic where the decision happens"),
        ("Newsletter", "the story delivered, not merely available")]):
    cy2 = y + 50 + i * 96
    m.rect([x2, cy2, W - MX - x2, 84], fill=PAPER)
    m.rect([x2, cy2, 8, 84], fill=ACCENT2)
    m.text([x2 + 24, cy2 + 12, 340, 30], t, style=ST_CARDT)
    m.text([x2 + 24, cy2 + 48, W - MX - x2 - 44, 28], b, style=ST_SMALL)
challenge(m, 1330,
          "Working with a team? Pair the data storyteller with the "
          "technical skill set — the blend, not either alone, ships it.")
action_strip(m, [
    "Freeze the message; edit only how it is told.",
    "Export for each channel's size and format.",
    "Publish, then listen — the audience finishes the review."])

# =============================================================== page 20 ----
m = scaffold("p20", None, 20, footer_note="BUILDING STUNNING INFOGRAPHICS")
m.rect([0, 0, W, 14], fill=ACCENT)
m.text([MX, 90, 400, 26], "THE WHOLE METHOD", style=ST_KICK)
m.text([MX, 130, CW, 60], "Ten steps, one page", style=ST_H1)
steps20 = [
    ("1", "Audience", "name WHO it is for and where they meet it"),
    ("2", "Purpose", "write WHY it exists in one sentence"),
    ("3", "Story", "title · intro · one message · conclusion + CTA"),
    ("4", "Data & visuals", "one visual family per claim, licensed"),
    ("5", "Layout", "format and orientation from the surface"),
    ("6", "Design elements", "one palette, one type ladder, one focal point"),
    ("7", "Sketch", "paper first; iterate where it is cheap"),
    ("8", "Draft", "foundation, then sections, then visuals"),
    ("9", "Review", "story · content · design · visuals"),
    ("10", "Ship", "revise to purpose, share where readers are")]
ty = 230
for n, t, b in steps20:
    m.rect([MX, ty, 54, 54], fill="none", **_stroke(3, color=INK))
    m.text([MX + 74, ty - 2, 90, 44], n, style=ST_H2)
    m.text([MX + 170, ty - 2, 300, 40], t, style=ST_CARDT)
    m.text([MX + 480, ty + 2, CW - 480, 44], b, style=ST_BODYM)
    ty += 96
m.rect([MX, ty + 20, CW, 170], fill=INK)
m.text([MX + 40, ty + 62, CW - 80, 90],
       "Structure in tone before hue. One message before many charts. "
       "The reader before everything.", style=ST_INV)
m.rect([MX, ty + 20, 10, 170], fill=ACCENT)

# ------------------------------------------------------------------ write ---
doc.write(globals().get("OUTPUT_YAML_PATH", "infographics_guide.yaml"),
          fail_on_error=True)
