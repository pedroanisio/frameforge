
"""Two Compilers, One Problem — comparative technical assessment.

Design system per Johnston (letter), Chevreul (hue), Batchelder (arrangement):
tone structure first, closed palette with assigned duties, modular scale,
every text/ground pair verified against WCAG floors before authoring.
"""
from frameforge.sdk import DocumentBuilder, widgets
from frameforge.sdk.paint import stroke

# ---------------------------------------------------------------- palette
PAPER      = "#F2EEE6"   # ground, warm
COVER      = "#14171A"   # cover ground, cool near-black
INK        = "#1B1E22"   # 14.46:1 on paper
G1         = "#4A4F56"   # 7.13:1  secondary text
G2         = "#5F656D"   # 5.09:1  tertiary text
G3         = "#9AA0A8"   # 2.28:1  RULES AND FILLS ONLY — never text
ZEBRA      = "#EAE5DA"
CARD       = "#FAF8F4"   # card tint, sits just above the paper ground
RUST_P     = "#8F4420"   # 6.02:1  stackforge, on paper
INDIGO_P   = "#26456E"   # 8.41:1  SpecForge, on paper
RUST_C     = "#E2926A"   # 7.33:1  stackforge, on cover
INDIGO_C   = "#8FB0DC"   # 8.06:1  SpecForge, on cover
PAPER_DIM  = "#BDB7AC"   # 9.02:1  secondary, on cover

# ------------------------------------------------------------ modular scale
MICRO, CAPTION, BODY = 11.5, 14.375, 17.96875
H3, H2, H1 = 22.4609375, 28.076171875, 35.09521484375
DISPLAY, COVERSZ = 43.8690185546875, 54.836273193359375
TITLE = COVERSZ * 1.25

# ------------------------------------------------------------------- grid
PW, PH = 1240, 1754
ML, MT = 111, 140
MAIN_X, MAIN_W = 111, 600
SIDE_X, SIDE_W = 751, 267
CONTENT_W = 907
FOOT_Y = 1620

TH = widgets.Theme(
    surface=PAPER, surface_alt=ZEBRA, ink=INK, sub=G1, muted=G2,
    line=G3, fill=PAPER, fill_alt=ZEBRA, accent=INDIGO_P,
    font=("Fira Sans", "sans-serif"), mono=("Fira Mono", "monospace"),
    radius=0.0, pad=14.0, control_h=32.0,
)

doc = DocumentBuilder(title="Two Compilers, One Problem")

def ts(name, **kw):
    return doc.define_text_style(name, **kw)

# cover styles
S_EYEBROW = ts("eyebrow", font_family="Fira Sans", font_size=MICRO, color=PAPER_DIM,
               letter_spacing=2.6, text_transform="uppercase", v_align="top")
S_TITLE   = ts("title", font_family="EB Garamond", font_size=TITLE, color=PAPER,
               line_height=1.08, v_align="top")
S_SUB     = ts("sub", font_family="EB Garamond", font_size=H3, color=PAPER_DIM,
               line_height=1.45, font_style="italic", v_align="top")
S_SYSNAME = ts("sysname", font_family="EB Garamond", font_size=H3, color=PAPER, v_align="top")
S_SYSMETA = ts("sysmeta", font_family="Fira Mono", font_size=CAPTION, color=PAPER_DIM, v_align="top")
S_COVLAB  = ts("covlab", font_family="Fira Sans", font_size=MICRO, color=PAPER_DIM,
               letter_spacing=1.8, text_transform="uppercase", v_align="top")
S_COVVAL  = ts("covval", font_family="Fira Sans", font_size=CAPTION, color=PAPER,
               line_height=1.45, v_align="top")

# interior styles
S_SECNUM  = ts("secnum", font_family="Fira Sans", font_size=CAPTION, color=RUST_P,
               letter_spacing=2.2, text_transform="uppercase", v_align="top")
S_H1      = ts("h1", font_family="EB Garamond", font_size=H1, color=INK,
               line_height=1.15, v_align="top")
S_H2      = ts("h2", font_family="EB Garamond", font_size=H3, color=INK,
               line_height=1.2, v_align="top")
S_H3      = ts("h3", font_family="EB Garamond", font_size=H3, color=INK,
               line_height=1.3, v_align="top")
S_BODY    = ts("body", font_family="EB Garamond", font_size=BODY, color=INK,
               line_height=1.58, v_align="top")
S_LEAD    = ts("lead", font_family="EB Garamond", font_size=H3, color=G1,
               line_height=1.5, v_align="top")
S_NOTE    = ts("note", font_family="Fira Sans", font_size=CAPTION, color=G1,
               line_height=1.55, v_align="top")
S_LABEL   = ts("label", font_family="Fira Sans", font_size=MICRO, color=G2,
               letter_spacing=1.8, text_transform="uppercase", v_align="top")
S_MONO    = ts("mono", font_family="Fira Mono", font_size=CAPTION, color=INK, v_align="top")
S_FIGLAB  = ts("figlab", font_family="Fira Sans", font_size=CAPTION, color=G1, v_align="top")
S_FIGLABC = ts("figlabc", font_family="Fira Sans", font_size=CAPTION, color=G1,
               text_align="center", v_align="top")
S_FOOT    = ts("foot", font_family="Fira Sans", font_size=MICRO, color=G2, v_align="top")
S_FOOTR   = ts("footr", font_family="Fira Sans", font_size=MICRO, color=G2,
               text_align="right", v_align="top")
S_SFNAME  = ts("sfname", font_family="Fira Sans", font_size=CAPTION, color=RUST_P,
               letter_spacing=1.6, text_transform="uppercase", v_align="top")
S_SPNAME  = ts("spname", font_family="Fira Sans", font_size=CAPTION, color=INDIGO_P,
               letter_spacing=1.6, text_transform="uppercase", v_align="top")
S_PULL    = ts("pull", font_family="EB Garamond", font_size=H3, color=INK,
               line_height=1.35, font_style="italic", v_align="top")

# ------------------------------------------------------------------ helpers
def marker_stackforge(lay, x, y, s=13):
    """Filled square — distinguishable from the ring in greyscale."""
    lay.rect([x, y, s, s], fill=RUST_P)

def marker_specforge(lay, x, y, s=13):
    """Hollow ring — shape carries identity, never hue alone."""
    lay.circle([x + s / 2, y + s / 2], s / 2, fill="none",
               **stroke(2.4, color=INDIGO_P))

def interior(pid):
    p = doc.page(pid, canvas={"size": [PW, PH], "units": "px"}, coordinate_mode="absolute")
    p.layer("bg").rect([0, 0, PW, PH], fill=PAPER)
    return p

def sechead(p, num, title, kicker=None):
    lay = p.layer("head")
    p.text([ML, MT - 34, 400, 20], num, style=S_SECNUM)
    lay.line([ML, MT - 8], [ML + CONTENT_W, MT - 8], **stroke(1.1, color=G3))
    p.text([ML, MT + 14, CONTENT_W, 60], title, style=S_H1)
    if kicker:
        p.text([ML, MT + 78, MAIN_W + 120, 60], kicker, style=S_LEAD)

def footer(p, n):
    lay = p.layer("foot")
    lay.line([ML, FOOT_Y], [ML + CONTENT_W, FOOT_Y], **stroke(0.8, color=G3))
    p.text([ML, FOOT_Y + 14, 600, 20],
           "Two Compilers, One Problem — comparative technical assessment", style=S_FOOT)
    p.text([ML + CONTENT_W - 300, FOOT_Y + 14, 300, 20], f"{n:02d}", style=S_FOOTR)

def bullets(p, items, x, y, w, gap=30, marker=None):
    """items: (title, body). Returns the y after the block."""
    lay = p.layer("bul")
    cy = y
    for title, bodytext in items:
        if marker == "sf":
            marker_stackforge(lay, x, cy + 6)
        elif marker == "sp":
            marker_specforge(lay, x, cy + 6)
        else:
            lay.rect([x, cy + 9, 9, 9], fill=G2)
        p.text([x + 30, cy, w - 30, 30], title, style=S_H3)
        h = 26 + 28 * (1 + len(bodytext) // 66)
        p.text([x + 30, cy + 32, w - 30, h], bodytext, style=S_BODY)
        cy += 32 + h + gap
    return cy

# ================================================================= PAGE 1
p1 = doc.page("cover", canvas={"size": [PW, PH], "units": "px"}, coordinate_mode="absolute")
c = p1.layer("bg")
c.rect([0, 0, PW, PH], fill=COVER)

p1.text([ML, 96, 620, 20], "Comparative technical assessment", style=S_EYEBROW)
p1.text([ML + CONTENT_W - 300, 96, 300, 20], "2026 · 07 · 20",
        style=doc.define_text_style("eyebrow_r", font_family="Fira Sans", font_size=MICRO,
                                    color=PAPER_DIM, letter_spacing=2.6,
                                    text_align="right", v_align="top"))
c.line([ML, 130], [ML + CONTENT_W, 130], **stroke(1.0, color=G1))

p1.text([ML, 300, 900, 220], "Two Compilers,\nOne Problem", style=S_TITLE)
p1.text([ML, 508, 660, 130],
        "Convergent theses and opposite bets in deterministic "
        "spec-to-service compilation.", style=S_SUB)

# abstract mark: perpendicular depth — the motif page 5 explains
c.rect([SIDE_X + 30, 1085, 300, 7], fill=RUST_C)
c.rect([SIDE_X + 160, 960, 7, 260], fill=INDIGO_C)

c.line([ML, 830], [ML + CONTENT_W, 830], **stroke(1.0, color=G1))

marker_sq_y = 880
c.rect([ML, marker_sq_y + 8, 14, 14], fill=RUST_C)
p1.text([ML + 34, marker_sq_y, 520, 34], "stackforge", style=S_SYSNAME)
p1.text([ML + 34, marker_sq_y + 38, 560, 24],
        "v0.10.1 · Rust CLI · compiles to Python / FastAPI", style=S_SYSMETA)

ring_y = 980
c.circle([ML + 7, ring_y + 15], 7, fill="none", **stroke(2.6, color=INDIGO_C))
p1.text([ML + 34, ring_y, 520, 34], "SpecForge", style=S_SYSNAME)
p1.text([ML + 34, ring_y + 38, 560, 24],
        "v1.0.0 · TypeScript Studio · compiles to Node / Fastify", style=S_SYSMETA)

c.line([ML, 1440], [ML + CONTENT_W, 1440], **stroke(1.0, color=G1))
meta = [
    ("Scope", "Full source read of both\nsystems; architecture, spec\nschema and lifecycle model."),
    ("Verification", "stackforge built and tested\non host: 43 tests green.\nSpecForge suite not executed."),
    ("Finding", "Convergent thesis;\nperpendicular investment;\nsix clean complements."),
]
for i, (k, v) in enumerate(meta):
    x = ML + i * 305
    p1.text([x, 1476, 260, 18], k, style=S_COVLAB)
    p1.text([x, 1502, 270, 110], v, style=S_COVVAL)

# ================================================================= PAGE 2
p2 = interior("summary")
sechead(p2, "01 — Executive summary", "A shared refusal")
lay2 = p2.layer("c")

p2.text([MAIN_X, MT + 96, MAIN_W, 300],
        "Two independently built systems were assessed. stackforge is a Rust "
        "command-line compiler that targets Python and FastAPI. SpecForge is a "
        "TypeScript studio application that targets Node and Fastify. Both take a "
        "declarative specification as their single source of truth and compile it "
        "into a complete backend service, and neither admits a language model "
        "anywhere in its generation path.",
        style=S_BODY)

p2.text([MAIN_X, MT + 300, MAIN_W, 230],
        "That shared refusal is the central finding. Two designs arriving "
        "independently at the same thesis — that a service's structure should be "
        "compiled from a reviewed contract rather than authored once and then "
        "maintained by hand — is stronger evidence for the thesis than either "
        "system alone would be.",
        style=S_BODY)

p2.text([MAIN_X, MT + 470, MAIN_W, 260],
        "Where they part is investment. stackforge spends its complexity on what "
        "happens after generation: provenance, drift classification, lossless "
        "upgrades and fleet-wide governance. SpecForge spends its on the contract "
        "itself and on proving the output runs. Their strongest capabilities "
        "therefore barely overlap.",
        style=S_BODY)

lay2.line([MAIN_X, MT + 700], [MAIN_X + MAIN_W, MT + 700], **stroke(1.0, color=G3))
p2.text([MAIN_X, MT + 722, 300, 18], "Findings", style=S_LABEL)

findings = [
    ("Convergent thesis",
     "Both systems exclude LLMs from codegen and treat drift as the primary enemy. "
     "Neither cites the other."),
    ("Perpendicular depth",
     "stackforge is narrow-spec and deep-lifecycle. SpecForge is deep-spec, "
     "deep-verification and shallow-lifecycle."),
    ("Six clean complements",
     "Their strongest features barely intersect — edit classification against live-boot "
     "verification being the sharpest pair."),
    ("Two irreconcilable contracts",
     "Spec size and ownership of generated code are opposed, not merely different. "
     "A merged tool must choose."),
]
bullets(p2, findings, MAIN_X, MT + 754, MAIN_W, gap=16)

# side column
p2.text([SIDE_X, MT + 96, SIDE_W, 18], "Basis of assessment", style=S_LABEL)
lay2.line([SIDE_X, MT + 122], [SIDE_X + SIDE_W, MT + 122], **stroke(1.0, color=G3))
p2.text([SIDE_X, MT + 138, SIDE_W, 200],
        "stackforge was read in full and built on the assessment host: the suite "
        "runs green at 43 tests across four binaries.", style=S_NOTE)
p2.text([SIDE_X, MT + 268, SIDE_W, 220],
        "SpecForge was read in full but its suite was not executed. The figure of "
        "118 test files and roughly 994 cases is reported by the repository, not "
        "independently confirmed here.", style=S_NOTE)
lay2.line([SIDE_X, MT + 420], [SIDE_X + SIDE_W, MT + 420], **stroke(1.0, color=G3))
p2.text([SIDE_X, MT + 436, SIDE_W, 18], "A note on naming", style=S_LABEL)
p2.text([SIDE_X, MT + 462, SIDE_W, 200],
        "The directory lambda-spec contains a project that names itself SpecForge. "
        "It is used throughout this report.", style=S_NOTE)
footer(p2, 2)

# ================================================================= PAGE 3
p3 = interior("systems")
sechead(p3, "02 — The subjects", "Two compilers, described")
lay3 = p3.layer("c")

CARD_W, CARD_X2 = 440, 111 + 467
CARD_Y = MT + 110

def factcard(p, lay, x, name, tint, kind, rows):
    lay.rect([x, CARD_Y, CARD_W, 600], fill=CARD)
    lay.rect([x, CARD_Y, CARD_W, 4], fill=tint)
    if kind == "sf":
        lay.rect([x + 22, CARD_Y + 34, 14, 14], fill=tint)
    else:
        lay.circle([x + 29, CARD_Y + 41], 7, fill="none", **stroke(2.6, color=tint))
    p.text([x + 54, CARD_Y + 28, 300, 34], name, style=S_H2)
    t = widgets.table(
        [x + 22, CARD_Y + 86, CARD_W - 44, 480],
        [{"label": "", "width": "42%"}, {"label": "", "width": "58%"}],
        rows, header=False, zebra=True, row_height=54, theme=TH,
    )
    p.add(t)

factcard(p3, lay3, ML, "stackforge", RUST_P, "sf", [
    ["Form factor", "Rust CLI, single binary"],
    ["Size", "~2.6k LOC + 44 templates"],
    ["Spec", "~30-line YAML, 11 sections"],
    ["Target", "Python · FastAPI\nSQLAlchemy · Postgres"],
    ["Validation", "21 rules (SF001–SF021)"],
    ["Verification", "10 checks (SFV01–SFV10)"],
    ["Signature move", "Three-hash upgrade classifier"],
    ["Weakest link", "No authoring story; no runtime\nproof of the generated service"],
])

factcard(p3, lay3, CARD_X2, "SpecForge", INDIGO_P, "sp", [
    ["Form factor", "Web Studio + MySQL + tRPC"],
    ["Size", "~52k LOC TypeScript"],
    ["Spec", "45 KB–563 KB JSON, 73 $defs"],
    ["Target", "TypeScript · Fastify\nDrizzle · Postgres 16"],
    ["Validation", "Ajv + 22 closure laws + CEL"],
    ["Verification", "4 contracts incl. live boot"],
    ["Signature move", "Closure laws + CEL compiler"],
    ["Weakest link", "No per-file edit model; day-2\nis re-emit, not classify"],
])

p3.text([ML, CARD_Y + 640, CONTENT_W, 120],
        "Both compile a contract into a service. The asymmetry in size — a binary of "
        "a few thousand lines against an application of fifty thousand — is not a "
        "measure of ambition but of surface: one ships a compiler, the other ships a "
        "compiler wrapped in an inspection console.",
        style=S_BODY)
lay3.line([ML, CARD_Y + 790], [ML + CONTENT_W, CARD_Y + 790], **stroke(1.0, color=G3))
p3.text([ML, CARD_Y + 812, 300, 18], "Common ground", style=S_LABEL)
for i, (k, v) in enumerate([
        ("No model in the loop", "Neither admits a language model into the generation path."),
        ("Deterministic output", "The same specification yields the same bytes, every run."),
        ("Drift is the enemy", "Both instrument heavily against silent divergence.")]):
    x = ML + i * 305
    lay3.rect([x, CARD_Y + 846, 26, 3], fill=G2)
    p3.text([x, CARD_Y + 864, 268, 28], k, style=S_H3)
    p3.text([x, CARD_Y + 900, 272, 90], v, style=S_NOTE)
footer(p3, 3)

# ================================================================= PAGE 4
p4 = interior("matrix")
sechead(p4, "03 — Comparison", "The matrix")
p4.text([ML, MT + 96, CONTENT_W, 60],
        "Rank is never carried by colour alone: every column is labelled and every "
        "row names its axis.", style=S_NOTE)

rows = [
    ["Form factor", "Rust CLI, single binary", "Web app + DB + tRPC + React Studio"],
    ["Spec format", "YAML, ~30 lines", "JSON, 73 $defs, 7 sections"],
    ["Spec scale", "One screen, reviewable", "45 KB – 563 KB"],
    ["Spec philosophy", "Minimal; defaults-heavy", "Total; the spec is the system"],
    ["Validation", "21 semantic rules", "Ajv + 22 closure laws + CEL"],
    ["Intermediate form", "None; config feeds templates", "Explicit normalised IR"],
    ["Codegen mechanism", "44 minijinja templates", "24 hand-written emitters"],
    ["Target stack", "Python / FastAPI / Alembic", "TypeScript / Fastify / Drizzle"],
    ["DDD treatment", "Modelled and enforced", "Extension zones only"],
    ["Verification", "10 static checks", "4 contracts incl. live boot"],
    ["Statefulness", "Stateless; manifest in tree", "Projects, revisions, runs"],
    ["Day-2 model", "Classify edits, upgrade losslessly", "New revision, re-emit"],
    ["Migrations", "Emits append-only; refuses drops", "Plans risk; does not emit"],
    ["LLM in pipeline", "None", "None"],
]
t4 = widgets.table(
    [ML, MT + 160, CONTENT_W, 800],
    [{"label": "Axis", "width": "26%"},
     {"label": "stackforge", "width": "37%"},
     {"label": "SpecForge", "width": "37%"}],
    rows, header=True, zebra=True, row_height=44, header_height=46, theme=TH,
)
p4.add(t4)
lay4 = p4.layer("c")
lay4.rect([ML + CONTENT_W * 0.26, MT + 148, CONTENT_W * 0.36, 4], fill=RUST_P)
lay4.rect([ML + CONTENT_W * 0.63, MT + 148, CONTENT_W * 0.36, 4], fill=INDIGO_P)
p4.text([ML, MT + 880, CONTENT_W, 90],
        "Read down the last three rows: the day-2 model is where the two designs "
        "diverge most sharply, and it is the axis on which they most need each other.",
        style=S_BODY)
footer(p4, 4)

# ================================================================= PAGE 5
p5 = interior("axes")
sechead(p5, "04 — Analysis", "Perpendicular depth")
p5.text([ML, MT + 96, MAIN_W + 140, 90],
        "Both systems are deep. They are deep along axes that meet at a right angle, "
        "which is why neither reads as a better version of the other.", style=S_LEAD)

lay5 = p5.layer("fig")
X0, Y0, X1, Y1 = 300, 420, 1030, 1150   # plot frame
# quadrant wash: the unoccupied corner
lay5.rect([(X0 + X1) / 2, Y0, (X1 - X0) / 2, (Y1 - Y0) / 2], fill=ZEBRA)
p5.text([(X0 + X1) / 2 + 24, Y0 + 26, 300, 28], "Unoccupied", style=S_FIGLAB)
p5.text([(X0 + X1) / 2 + 24, Y0 + 50, 300, 28], "the composition target", style=S_FIGLAB)

for i in range(1, 4):
    gx = X0 + (X1 - X0) * i / 4
    gy = Y0 + (Y1 - Y0) * i / 4
    lay5.line([gx, Y0], [gx, Y1], **stroke(0.6, color=G3))
    lay5.line([X0, gy], [X1, gy], **stroke(0.6, color=G3))

lay5.line([X0, Y1], [X1 + 26, Y1], **stroke(1.6, color=INK))
lay5.line([X0, Y1], [X0, Y0 - 26], **stroke(1.6, color=INK))
lay5.polygon([[X1 + 40, Y1], [X1 + 24, Y1 - 6], [X1 + 24, Y1 + 6]], fill=INK)
lay5.polygon([[X0, Y0 - 40], [X0 - 6, Y0 - 24], [X0 + 6, Y0 - 24]], fill=INK)

p5.text([X0, Y1 + 30, 420, 24], "Spec expressiveness", style=S_FIGLAB)
p5.text([X0 - 250, Y0 - 46, 230, 24], "Lifecycle governance",
        style=doc.define_text_style("figlab_r", font_family="Fira Sans", font_size=CAPTION,
                                    color=G1, text_align="right", v_align="top"))

# stackforge: modest spec, deep lifecycle
SFX, SFY = X0 + (X1 - X0) * 0.27, Y0 + (Y1 - Y0) * 0.18
lay5.rect([SFX - 11, SFY - 11, 22, 22], fill=RUST_P)
p5.text([SFX + 26, SFY - 30, 300, 28], "stackforge", style=S_SFNAME)
p5.text([SFX + 26, SFY - 2, 250, 28], "narrow spec", style=S_FIGLAB)
p5.text([SFX + 26, SFY + 20, 250, 28], "deep lifecycle", style=S_FIGLAB)

# SpecForge: deep spec, shallower lifecycle
SPX, SPY = X0 + (X1 - X0) * 0.80, Y0 + (Y1 - Y0) * 0.66
lay5.circle([SPX, SPY], 12, fill="none", **stroke(3.2, color=INDIGO_P))
p5.text([SPX - 250, SPY - 30, 226, 28], "SpecForge",
        style=doc.define_text_style("spname_r", font_family="Fira Sans", font_size=CAPTION,
                                    color=INDIGO_P, letter_spacing=1.6,
                                    text_transform="uppercase", text_align="right",
                                    v_align="top"))
S_FIGR2 = doc.define_text_style("figlab_r2", font_family="Fira Sans", font_size=CAPTION,
                                color=G1, text_align="right", v_align="top")
p5.text([SPX - 250, SPY - 2, 226, 28], "deep spec", style=S_FIGR2)
p5.text([SPX - 250, SPY + 20, 226, 28], "shallow lifecycle", style=S_FIGR2)

p5.text([ML, 1240, CONTENT_W, 130],
        "The empty quadrant is the point. Neither system is short of rigour; each has "
        "simply spent it on a different axis. A composition that reached the top-right "
        "would need SpecForge's contract language and SpecForge's runtime proof sitting "
        "on top of stackforge's provenance and fleet governance — and nothing in either "
        "architecture forbids it.",
        style=S_BODY)
footer(p5, 5)

# ================================================================= PAGE 6
p6 = interior("complements")
sechead(p6, "05 — Complementarity", "What each supplies")
p6.text([ML, MT + 96, CONTENT_W, 60],
        "Six complements, grouped by direction of transfer.", style=S_NOTE)

lay6 = p6.layer("c")
lay6.rect([ML, MT + 158, 4, 30], fill=RUST_P)
p6.text([ML + 18, MT + 160, 700, 26], "stackforge supplies to SpecForge", style=S_SFNAME)
t6a = widgets.table(
    [ML, MT + 200, CONTENT_W, 300],
    [{"label": "Capability", "width": "31%"}, {"label": "What it closes", "width": "69%"}],
    [["Three-hash classifier",
      "Per-file edit classification — lets users edit generated code and still upgrade "
      "losslessly, replacing the coarse folder convention"],
     ["Append-only migrator",
      "Emits chained additive migrations and refuses destructive deltas, where SpecForge "
      "only classifies risk"],
     ["Fuzz, golden, mutation",
      "Seeded random specs, snapshot gates and mutation-tested generated tests — a rigor "
      "layer absent upstream"]],
    header=True, zebra=True, row_height=76, header_height=44, theme=TH,
)
p6.add(t6a)

lay6.rect([ML, MT + 560, 4, 30], fill=INDIGO_P)
p6.text([ML + 18, MT + 562, 700, 26], "SpecForge supplies to stackforge", style=S_SPNAME)
t6b = widgets.table(
    [ML, MT + 602, CONTENT_W, 300],
    [{"label": "Capability", "width": "31%"}, {"label": "What it closes", "width": "69%"}],
    [["Elicitation front-end",
      "135 questions with a formal adequacy verdict — an authoring story for a tool whose "
      "premise is a reviewed spec"],
     ["Closure laws and CEL",
      "Cross-referential validation and a real rule language, against 21 flat semantic rules"],
     ["Live-boot sandbox",
      "Boots the generated server on an in-memory Postgres and injects requests, where "
      "stackforge stops at byte-compilation"]],
    header=True, zebra=True, row_height=76, header_height=44, theme=TH,
)
p6.add(t6b)

lay6.line([ML, MT + 960], [ML + CONTENT_W, MT + 960], **stroke(1.0, color=G3))
p6.text([ML, MT + 982, CONTENT_W, 120],
        "The transfer is not symmetric in kind. stackforge exports mechanisms — hashes, "
        "classifiers, emitters. SpecForge exports language and evidence — a way to say "
        "more, and a way to prove it ran.",
        style=S_BODY)
footer(p6, 6)

# ================================================================= PAGE 7
p7 = interior("tensions")
sechead(p7, "06 — Tensions", "Where they cannot merge")
lay7 = p7.layer("c")

p7.text([MAIN_X, MT + 96, MAIN_W, 90],
        "Two contracts are opposed rather than merely different. Any composition must "
        "choose a side; neither can be split.", style=S_LEAD)

tensions = [
    ("Spec size",
     "stackforge bets that a human reviews the whole contract in five minutes. "
     "SpecForge bets that the contract is the entire system, at up to 563 KB. "
     "Reconciling them means a layered spec — a small reviewed core with progressive "
     "detail — which neither has today."),
    ("Ownership of output",
     "stackforge says your edits win: user-modified is a first-class class. SpecForge "
     "says the generated tree is compiler-owned and you extend at the zones. Every "
     "downstream decision follows from this choice."),
]
ty = bullets(p7, tensions, MAIN_X, MT + 210, MAIN_W, gap=26)

lay7.line([MAIN_X, ty + 10], [MAIN_X + MAIN_W, ty + 10], **stroke(1.0, color=G3))
p7.text([MAIN_X, ty + 34, 400, 18], "Recommended composition", style=S_LABEL)

steps = [("Elicit", "SpecForge questionnaire\n→ adequacy verdict"),
         ("Contract", "Layered spec: reviewed core\n+ progressive detail"),
         ("Compile", "Per-target emitter\n(Python or TypeScript)"),
         ("Govern", "Manifest, classifier,\nfleet — stackforge model")]
sy = ty + 70
for i, (k, v) in enumerate(steps):
    x = MAIN_X + i * 152
    tint = RUST_P if i == 3 else (INDIGO_P if i < 2 else G1)
    lay7.rect([x, sy, 128, 4], fill=tint)
    p7.text([x, sy + 16, 128, 24], k, style=S_H3)
    p7.text([x, sy + 48, 132, 80], v, style=S_FIGLAB)
    if i < 3:
        lay7.polygon([[x + 140, sy + 34], [x + 132, sy + 29], [x + 132, sy + 39]], fill=G2)

p7.text([SIDE_X, MT + 96, SIDE_W, 18], "Verdict", style=S_LABEL)
lay7.line([SIDE_X, MT + 122], [SIDE_X + SIDE_W, MT + 122], **stroke(1.0, color=G3))
p7.text([SIDE_X, MT + 138, SIDE_W, 400],
        "SpecForge proves you can express and verify a backend's full meaning. "
        "stackforge proves you can keep a generated backend honest for years, across "
        "a fleet.\n\nThey are the same thesis split in half.", style=S_NOTE)

lay7.line([MAIN_X, 1130], [MAIN_X + CONTENT_W, 1130], **stroke(1.0, color=G3))
p7.text([MAIN_X, 1162, CONTENT_W, 140],
        "“Tools that only generate solve day 0; the expensive problems are day 2 and "
        "beyond.” Both codebases believe this. Only one of them has finished building "
        "the answer — and it is not the larger one.",
        style=S_PULL)
footer(p7, 7)

doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
