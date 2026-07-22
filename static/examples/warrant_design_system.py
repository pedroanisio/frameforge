"""Warrant — the design-system proposal, typeset in its own system.

Source: _tmp/warrant-design-system-proposal.md (v0.1.0-draft, 2026-07-22).
Every token this client uses is the one the proposal defines: the closed
warrant palette on drafting-grey paper, Archivo's real width axis carrying
the structural register, Source Serif 4 prose, IBM Plex Mono data (the
declared fallback — Commit Mono is not in this runtime; noted in the
colophon), the 1.2 modular scale, the 8px grid, and the provenance rail on
every content block. The document eats its own dogfood.
"""
from __future__ import annotations

from frameforge.sdk import DocumentBuilder

# ---------------------------------------------------------------- canvas ----
W, H = 1240, 1754                      # A4 portrait @ ~150 dpi
PX = 1.5625                            # css-px (96dpi) -> render-px (150dpi)
MX, MT, MB = 112, 108, 148             # margins on the 8px grid; foot widest
CW = W - 2 * MX                        # content width 1016
PROSE_W = 824                          # ~65ch measure for serif body

# ------------------------------------------------------- warrant palette ----
PAPER = "#EEF1EF"
INK = "#10171B"          # 15.91:1 on paper
PETROL = "#12414F"       # 9.74:1  structure
LIVE = "#0A6B77"         # 5.46:1  interactive/live accents
GRAPHITE = "#5C696E"     # 4.99:1  metadata, captions
OXIDE = "#B3341F"        # 5.39:1  RESERVED: contradicted only
# dark mode
SURFACE = "#131A1F"
INK_INV = "#DCE3E3"
LIVE_INV = "#3FB3C2"
OXIDE_INV = "#E86A50"
GRAPHITE_INV = "#6E7C82"
PETROL_TINT = "#1B3A45"  # surface tint in dark mode, never a foreground

# ------------------------------------------------------------ type scale ----
# 1.2 modular scale, rem -> render px (1rem = 16 css px = 25 render px)
def rem(r: float) -> float:
    return round(r * 16 * PX, 1)

S_ANNOT = rem(0.694)     # 17.4 — provenance annotation ONLY
S_SMALL = rem(0.833)     # 20.8
S_BODY = rem(1.0)        # 25.0
S_H3 = rem(1.2)          # 30.0
S_H2 = rem(1.44)         # 36.0
S_H1 = rem(1.728)        # 43.2
S_DISP = rem(2.074)      # 51.9
S_HERO = rem(2.488)      # 62.2

SERIF = "Source Serif 4"
DISPLAY = "Archivo"
MONO = "IBM Plex Mono"

def disp(size, *, wdth=110, wght=600, color=PETROL, **kw):
    """Archivo, the width axis carrying the register (>=110 structural).

    The raster lane now embeds variable faces so font-variation-settings DO
    reach the pixels (tests/test_raster_variable_fonts.py) — but real-metrics
    text measurement still reads the variable file's DEFAULT instance, so this
    client uses REAL static instances cut with fontTools for exact
    measure==render agreement at every register:
    Cnd 62/600 · FG 100/500 · Exp 125/560 · Display 112/650 · Hero 118/680."""
    fam = ("Archivo FG Hero" if wdth >= 118 and wght >= 660 else
           "Archivo FG Display" if wdth >= 110 and wght >= 620 else
           "Archivo FG Exp" if wdth >= 110 else
           "Archivo FG Cnd" if wdth <= 80 else
           "Archivo FG")
    return {"font_family": fam, "font_size": size, "color": color, **kw}

def serif(size=S_BODY, *, color=INK, lh=1.45, wght=400, **kw):
    st = {"font_family": SERIF, "font_size": size, "color": color,
          "line_height": lh, **kw}
    if wght != 400:
        st["font_weight"] = wght
    return st

def mono(size=S_SMALL, *, color=GRAPHITE, **kw):
    return {"font_family": MONO, "font_size": size, "color": color, **kw}

# ------------------------------------------------------------- the rail -----
# 3px rail + 12px gutter at 96dpi -> 5 + 19 render px, snapped to grid.
RAIL_W, RAIL_W_CTR, GUTTER = 5, 6, 19
RAIL = {
    "verified":     dict(color=PETROL,   alpha=1.00, dash=None,  w=RAIL_W,     tag="VER"),
    "derived":      dict(color=PETROL,   alpha=0.72, dash=None,  w=RAIL_W,     tag="DER"),
    "asserted":     dict(color=GRAPHITE, alpha=1.00, dash=None,  w=RAIL_W,     tag="ASR"),
    "unverified":   dict(color=GRAPHITE, alpha=0.60, dash=[3, 5], w=RAIL_W,     tag="UNV"),
    "contradicted": dict(color=OXIDE,    alpha=1.00, dash=None,  w=RAIL_W_CTR, tag="CTR"),
}
LEVELS = list(RAIL)


def rail(layer, x, y, h, level, *, tag=True, tag_color=GRAPHITE):
    """The provenance rail: leading-edge rule + mono tag at the foot."""
    t = RAIL[level]
    obj = {"type": "rect", "box": [x, y, t["w"], h], "fill": t["color"],
           "opacity": t["alpha"]}
    if t["dash"]:
        # dashed rail: draw as a stroked line so stroke-dasharray applies
        obj = {"type": "line", "from": [x + t["w"] / 2, y],
               "to": [x + t["w"] / 2, y + h], "stroke": t["color"],
               "stroke_opacity": t["alpha"],
               "stroke_style": {"stroke_width": t["w"], "stroke_dasharray": t["dash"]}}
    layer.add(obj)
    if tag:
        layer.text([x - 2, y + h + 8, 64, 20], t["tag"],
                   style=mono(S_ANNOT, color=tag_color))
    return x + t["w"] + GUTTER


def block(layer, x, y, w, level, lines, *, size=S_BODY, lh=1.45, color=INK,
          face=SERIF, wght=400, gap=0):
    """A railed prose block; returns the y below it."""
    n = len(lines) if isinstance(lines, list) else 1
    text = lines if isinstance(lines, str) else "\n".join(lines)
    h = round(n * size * lh) + 8 + gap
    cx = rail(layer, x, y, h, level)
    st = {"font_family": face, "font_size": size, "color": color,
          "line_height": lh}
    if wght != 400:
        st["font_weight"] = wght
    layer.text([cx, y - size * (lh - 1) / 2, w - (cx - x), h + 20], text, style=st)
    return y + h + 44


def footer(layer, page_no, section):
    layer.add({"type": "line", "from": [MX, H - MB + 40], "to": [W - MX, H - MB + 40],
               "stroke": GRAPHITE, "stroke_opacity": 0.45,
               "stroke_style": {"stroke_width": 1}})
    layer.text([MX, H - MB + 52, 760, 52], f"Warrant · v0.1.0-draft · {section}",
               style=mono(S_ANNOT, color=GRAPHITE))
    layer.text([W - MX - 120, H - MB + 52, 120, 24], f"{page_no:02d} / 12",
               style=mono(S_ANNOT, color=GRAPHITE), id=f"folio-{page_no}")


def header(layer, kicker, title, *, y=MT, color=PETROL):
    layer.text([MX, y, CW, 26], kicker,
               style=disp(S_SMALL, wdth=125, wght=560, color=GRAPHITE,
                          letter_spacing=2.2, text_transform="uppercase"))
    th = 118 if len(title) > 40 else 60
    layer.text([MX, y + 40, CW, th], title,
               style=disp(S_H1, wdth=110, wght=640, color=color, line_height=1.2))
    rule_y = y + 40 + th + 10
    layer.add({"type": "line", "from": [MX, rule_y], "to": [W - MX, rule_y],
               "stroke": PETROL, "stroke_style": {"stroke_width": 2}})
    return rule_y + 34


# =========================================================================== #
doc = DocumentBuilder(title="Warrant — a design system proposal",
                      profile="report")
doc.define_text_style("body", font_family=SERIF, font_size=S_BODY, color=INK,
                      line_height=1.45)


def page(pid):
    p = doc.page(pid, canvas={"size": [W, H], "units": "px"},
                 coordinate_mode="absolute")
    lyr = p.layer("main")
    lyr.rect([0, 0, W, H], fill=PAPER)
    return p, lyr


# ------------------------------------------------------------ 01 · cover ----
p, L = page("cover")
# the five rails, tall, as the cover motif — the signature element IS the cover
rx = MX
for i, lv in enumerate(LEVELS):
    t = RAIL[lv]
    x = MX + i * 56
    if t["dash"]:
        L.add({"type": "line", "from": [x + t["w"] / 2, MT], "to": [x + t["w"] / 2, MT + 380],
               "stroke": t["color"], "stroke_opacity": t["alpha"],
               "stroke_style": {"stroke_width": t["w"], "stroke_dasharray": t["dash"]}})
    else:
        L.add({"type": "rect", "box": [x, MT, t["w"], 380], "fill": t["color"],
               "opacity": t["alpha"]})
    L.text([x - 6, MT + 396, 64, 22], t["tag"], style=mono(S_ANNOT, color=GRAPHITE))

L.text([MX, 640, CW, 150], "Warrant",
       style=disp(rem(1.2 ** 8), wdth=118, wght=680, color=INK))  # scale step +8
L.text([MX, 792, CW, 40], "A DESIGN SYSTEM PROPOSAL",
       style=disp(S_H3, wdth=125, wght=520, color=PETROL, letter_spacing=6))
L.text([MX, 872, PROSE_W, 170],
       "Conventional systems encode state: success, warning, error, disabled.\n"
       "This one encodes warrant — how well-founded is the thing\n"
       "you are looking at.",
       style=serif(S_H3, lh=1.5, color=INK))

# meta block, railed VERIFIED (it describes itself)
y = 1120
cx = rail(L, MX, y, 176, "verified")
for i, (k, v) in enumerate([("version", "0.1.0-draft"), ("date", "2026-07-22"),
                            ("author", "Claude (Opus 4.8)"),
                            ("status", "proposal / unratified"),
                            ("prefix", "wr-")]):
    L.text([cx, y + i * 34, 190, 26], k, style=mono(S_SMALL, color=GRAPHITE))
    L.text([cx + 200, y + i * 34, 560, 26], v, style=mono(S_SMALL, color=INK))

L.text([MX, 1420, CW - 40, 150],
       "Nothing in this document should be taken for granted. Any statement not backed by a real\n"
       "logical definition or a verifiable reference may be invalid, erroneous, or a hallucination.\n"
       "Biographical claims inherit the low reliability of their aggregator sources; the only computed\n"
       "claims are the WCAG contrast ratios, reproducible from Appendix A.",
       style=serif(S_SMALL, color=GRAPHITE, lh=1.55))
footer(L, 1, "cover")

# ----------------------------------------------- 02 · §1 what the record ----
p, L = page("record")
y = header(L, "Section 1", "What the search returned")

y = block(L, MX, y, CW, "asserted", [
    "Reconstructed from trade-press coverage, primarily a cluster of August 2021",
    "announcements. Grades: A computed/primary · B named publication · C aggregator,",
    "unverified · D author's inference."], size=S_BODY)

# career table
rows = [
    ("~1998–2001", "Co-founder — MailBR, reported as Brazil's first free email service", "B"),
    ("~2001–2003", "Development coordinator, webmail stack — iBest S/A", "C"),
    ("~2001–2003", "IT Coordinator II — Brasil Telecom S/A  (stale, see §1.2)", "C"),
    ("—", "Contributor — Walmart.com Brasil marketplace build", "B"),
    ("—", "Digital transformation lead — Grupo Estado", "B"),
    ("—", "CTO — Ginga One;  CTO — Wine.com.br;  iG", "B"),
    ("2019–2021", "CIO — Dotz", "B"),
    ("2017–", "Partner-administrator — Farol Digital (CNPJ status: inapta)", "C"),
    ("—", "Founder — Parsec Digital (mobile app development)", "B"),
    ("2021–now", "Digital Director / Head of Digital — Sem Parar (Fleetcor → Corpay)", "B"),
]
th = 58
L.add({"type": "rect", "box": [MX, y, CW, 46], "fill": PETROL})
L.text([MX + 20, y + 10, 220, 26], "PERIOD", style=disp(S_SMALL, wdth=118, wght=560, color=PAPER, letter_spacing=1.5))
L.text([MX + 240, y + 10, 560, 26], "ROLE · ORGANIZATION", style=disp(S_SMALL, wdth=118, wght=560, color=PAPER, letter_spacing=1.5))
L.text([MX + CW - 118, y + 10, 108, 26], "GRADE", style=disp(S_SMALL, wdth=118, wght=560, color=PAPER, letter_spacing=1.5))
y += 46
for i, (period, role, grade) in enumerate(rows):
    if i % 2:
        L.add({"type": "rect", "box": [MX, y, CW, th], "fill": PETROL, "opacity": 0.05})
    L.text([MX + 20, y + 15, 210, 26], period, style=mono(S_SMALL, color=GRAPHITE))
    L.text([MX + 240, y + 15, CW - 360, 30], role, style=serif(S_SMALL, lh=1.3))
    tag_color = GRAPHITE if grade == "C" else PETROL
    L.text([MX + CW - 84, y + 15, 60, 26], grade,
           style=mono(S_SMALL, color=tag_color, font_weight=600))
    y += th
y += 40

y = block(L, MX, y, CW, "asserted", [
    "Education: technology degree in information systems, Centro Universitário Carioca;",
    "MBA in the same field, PUC."], size=S_BODY)
y = block(L, MX, y, CW, "unverified", [
    "Recent activity (LinkedIn snippet, indexed ~2 weeks prior): an AI Manifesto signing at",
    "Sem Parar Corpay, a Visa AI Lab challenge, an internal AI program launch, a guest",
    "evaluator seat on an academic business-project panel."], size=S_BODY)
footer(L, 2, "§1 · the record")

# ----------------------------------- 03 · §1.2 wrong record + sources -------
p, L = page("wrong")
y = header(L, "Section 1.2", "What the record gets wrong", color=OXIDE)

# the contradicted block — the ONLY warm mark in the whole document
y = block(L, MX, y, CW, "contradicted", [
    "One aggregator asserts a CURRENT role: IT Coordinator II at Brasil Telecom.",
    "That is a scraped Lattes CV field frozen around 2001–2003. Brasil Telecom itself",
    "was absorbed into Oi in 2009. Any tool ingesting that page without a recency",
    "check will produce a wrong present-tense claim."], size=S_BODY)

y = block(L, MX, y, CW, "derived", [
    "This is a live example of the failure class the pals-assessment skill exists to",
    "catch — silent acceptance of unverified machine-readable data. It warrants a",
    "formal correction request if machine-readable accuracy matters to you."], size=S_BODY)

y += 8
L.text([MX, y, CW, 30], "1.3 · Sources", style=disp(S_H3, wdth=112, wght=620, color=PETROL))
y += 52
sources = [
    ("B", "mundorh.com.br — pedro-anisio-e-o-novo-head-de-digital-do-sem-parar"),
    ("B", "itforum.com.br — pedro-anisio-e-anunciado-head-de-digital-do-sem-parar"),
    ("B", "baguete.com.br — ex-dotz-agora-e-diretor-na-sem-parar"),
    ("B", "forbes.com.br — carreira/2021/08/c-suite (August 2021 cluster)"),
    ("B", "propmark.com.br — sem-parar-apresenta-novo-head-de-digital"),
    ("C", "escavador.com/sobre/2109367 — stale Lattes mirror"),
    ("C", "cnpjrocks.com — CNPJ 28.269.649/0001-21, Farol Digital"),
    ("C", "linkedin.com/in/pedroanisio — snippet only, not fetched"),
    ("A", "ISO 128-2:2022 preview — cdn.standards.iteh.ai (line-width series)"),
]
for grade, src in sources:
    tag_color = PETROL if grade in ("A", "B") else GRAPHITE
    L.text([MX + 8, y, 44, 24], grade, style=mono(S_SMALL, color=tag_color, font_weight=600))
    L.text([MX + 64, y, CW - 80, 24], src, style=mono(S_SMALL, color=INK))
    y += 38
y += 30

L.text([MX, y, CW, 30], "1.4 · What the search did not find", style=disp(S_H3, wdth=112, wght=620, color=PETROL))
y += 52
y = block(L, MX, y, CW, "verified", [
    "No public design portfolio, brand guidelines, personal site, or visual work under",
    "this name. Everything visual here is built from first principles against the OUTPUT",
    "FORMATS, not against an existing identity to extend. If a house style already exists",
    "internally, this document is a competing proposal — and should say so."], size=S_BODY)
footer(L, 3, "§1.2–1.4 · corrections & sources")

# -------------------------------------- 04 · §2 interpretation chosen -------
p, L = page("interp")
y = header(L, "Section 2", "The interpretation I chose, and the one I rejected")

y = block(L, MX, y, CW, "derived",
          ['"Propose a Design System to me" is under-specified. Two defensible readings:'],
          size=S_BODY)

card_h = 320
# rejected card
L.add({"type": "rect", "box": [MX, y, CW / 2 - 16, card_h], "fill": PAPER,
       "stroke": GRAPHITE, "stroke_style": {"stroke_width": 1.5, "stroke_dasharray": [4, 4]}})
L.text([MX + 28, y + 26, 200, 30], "A · REJECTED",
       style=disp(S_SMALL, wdth=125, wght=600, color=GRAPHITE, letter_spacing=2))
L.text([MX + 28, y + 74, CW / 2 - 72, 200],
       "A corporate/product UI system — a component library for Sem Parar Corpay, or a "
       "personal brand identity. No access to Corpay's brand constraints; a personal-brand "
       "system for an executive with no public visual practice would be decoration "
       "without a job.",
       style=serif(S_SMALL, lh=1.5, color=GRAPHITE))
# chosen card
cx0 = MX + CW / 2 + 16
L.add({"type": "rect", "box": [cx0, y, CW / 2 - 16, card_h], "fill": PETROL})
L.text([cx0 + 28, y + 26, 220, 30], "B · CHOSEN",
       style=disp(S_SMALL, wdth=125, wght=620, color=PAPER, letter_spacing=2))
L.text([cx0 + 28, y + 74, CW / 2 - 72, 200],
       "A rendering substrate for the work actually produced. The strongest evidence is "
       "the skill library itself: twenty-seven skills, at least eight emitting visual "
       "artifacts independently — and they share no token layer.",
       style=serif(S_SMALL, lh=1.5, color=PAPER))
y += card_h + 44

y = block(L, MX, y, CW, "verified", [
    "engineering-svg · eng-schematic-renderer · advanced-dataviz · iandeadv-dataviz ·",
    "print-ready · pitch-deck-mastery · product-briefing · canvas-design"],
    size=S_SMALL, face=MONO, color=LIVE)

y = block(L, MX, y, CW, "derived", [
    "A schematic, a dashboard, a briefing, and a deck produced from the same analysis",
    "will not look like they came from the same system, because nothing forces them to.",
    "That is the concrete gap. If reading (A) was meant — say so; this restarts, not",
    "retrofits."], size=S_BODY)

y += 8
L.text([MX, y, CW, 30], "2.1 · An adjacent finding", style=disp(S_H3, wdth=112, wght=620, color=PETROL))
y += 52
y = block(L, MX, y, CW, "derived", [
    "advanced-dataviz and iandeadv-dataviz carry functionally identical descriptions —",
    "a routing collision: the skill selector has no principled basis to choose. Merge",
    "them, or make one a documented extension that names its difference first."],
    size=S_BODY)
footer(L, 4, "§2 · interpretation")

# ------------------------------------------------- 05 · §3 design thesis ----
p, L = page("thesis")
y = header(L, "Section 3", "Design thesis")

L.text([MX, y + 20, CW, 120],
       "Conventional design systems encode state.",
       style=serif(S_H2, color=GRAPHITE, lh=1.3))
L.text([MX, y + 84, CW, 120],
       "This one encodes warrant.",
       style=serif(S_H2, color=INK, wght=600, lh=1.3))
y += 190

y = block(L, MX, y, CW, "derived", [
    "The entire skill library is organized around one question: what warrants this",
    "claim?  cfs-mapper extracts claims with provenance. formal-completeness-checker",
    "asks whether a case analysis is exhaustive. research-kb grades sources on a",
    "five-tier authority hierarchy. pals-assessment audits systems for silent",
    "acceptance of unverified LLM output. anti-slop separates writing that does",
    "intellectual work from writing that performs its shape."], size=S_BODY)

# name cards
ch = 190
L.add({"type": "rect", "box": [MX, y, CW / 2 - 16, ch], "fill": PETROL})
L.text([MX + 28, y + 24, 300, 54], "Warrant", style=disp(S_DISP, wdth=115, wght=640, color=PAPER))
L.text([MX + 28, y + 96, 300, 26], "token prefix  wr-", style=mono(S_SMALL, color=INK_INV))
L.text([MX + 28, y + 134, CW / 2 - 72, 40], "primary — the epistemic reading",
       style=serif(S_SMALL, color=PAPER))
cx0 = MX + CW / 2 + 16
L.add({"type": "rect", "box": [cx0, y, CW / 2 - 16, ch], "fill": PAPER,
       "stroke": PETROL, "stroke_style": {"stroke_width": 1.5}})
L.text([cx0 + 28, y + 24, 300, 54], "Aferido", style=disp(S_DISP, wdth=115, wght=640, color=PETROL))
L.text([cx0 + 28, y + 96, 300, 26], "token prefix  af-", style=mono(S_SMALL, color=GRAPHITE))
L.text([cx0 + 28, y + 134, CW / 2 - 72, 40], "alternative — Pt., gauged / calibrated",
       style=serif(S_SMALL, color=GRAPHITE))
y += ch + 24
L.text([MX, y, CW, 24], "Naming is the weakest-evidence decision here; treat it as placeholder.",
       style=serif(S_SMALL, color=GRAPHITE, italic=True))
y += 64

L.text([MX, y, CW, 30], "Signature element · the provenance rail", style=disp(S_H3, wdth=112, wght=620, color=PETROL))
y += 52
y = block(L, MX, y, CW, "verified", [
    "A narrow vertical rule on the leading edge of any block of content, carrying that",
    "block's warrant level. It renders identically in HTML, printed PDF, SVG schematic",
    "annotation, a slide, and plain Markdown. It is the one thing that makes artifacts",
    "from different skills legible as one system — including every page of this one."],
    size=S_BODY)
footer(L, 5, "§3 · thesis")

# ------------------------------------------ 06 · §4 scale + light palette ---
p, L = page("tokens-light")
y = header(L, "Section 4", "Tokens — the warrant scale, light palette")

# warrant scale rows with live rails
scale_rows = [
    ("verified", "Traced to a primary source, or a computation reproducible from this document"),
    ("derived", "Follows by stated inference from verified material"),
    ("asserted", "Stated by a named party without independent confirmation"),
    ("unverified", "No source located; may be true"),
    ("contradicted", "Conflicts with verified material"),
]
for lv, meaning in scale_rows:
    t = RAIL[lv]
    cx = rail(L, MX, y, 58, lv, tag=False)
    L.text([cx, y + 2, 240, 30], lv, style=mono(S_BODY, color=INK, font_weight=600))
    L.text([cx + 240, y + 2, CW - 440, 62], meaning, style=serif(S_SMALL, lh=1.3))
    L.text([MX + CW - 70, y + 8, 60, 26], t["tag"],
           style=mono(S_BODY, color=t["color"], font_weight=600))
    y += 86
y += 6
y = block(L, MX, y, CW, "verified", [
    "The three-letter mono tag is not ornament: it is the fallback that survives grayscale",
    "printing, screen readers, plain-text diffing, and CSV export. Colour is the",
    "enhancement; the tag is the payload."], size=S_SMALL)

L.text([MX, y, CW, 30], "4.2 · Light palette — ground paper #EEF1EF",
       style=disp(S_H3, wdth=112, wght=620, color=PETROL))
y += 54
swatches = [
    ("wr-ink", INK, "15.91:1", "all body text, always"),
    ("wr-petrol", PETROL, "9.74:1", "structure: rules, headers, verified rail"),
    ("wr-petrol-live", LIVE, "5.46:1", "interactive affordances, links"),
    ("wr-graphite", GRAPHITE, "4.99:1", "dimension lines, metadata, captions"),
    ("wr-oxide", OXIDE, "5.39:1", "RESERVED — contradicted only"),
]
sw = (CW - 4 * 20) / 5
for i, (name, hexv, ratio, use) in enumerate(swatches):
    x = MX + i * (sw + 20)
    L.add({"type": "rect", "box": [x, y, sw, 128], "fill": hexv})
    # contrast bar: ratio out of 16, drawn on the swatch foot in paper
    frac = min(1.0, float(ratio.split(":")[0]) / 16.0)
    L.add({"type": "rect", "box": [x, y + 118, sw, 10], "fill": PAPER, "opacity": 0.35})
    L.add({"type": "rect", "box": [x, y + 118, sw * frac, 10], "fill": PAPER})
    L.text([x, y + 140, sw, 24], name, style=mono(S_SMALL, color=INK, font_weight=600))
    L.text([x, y + 168, sw, 22], hexv, style=mono(S_ANNOT, color=GRAPHITE))
    L.text([x, y + 192, sw, 22], ratio + " on paper", style=mono(S_ANNOT, color=GRAPHITE))
    L.text([x, y + 220, sw, 60], use, style=serif(S_ANNOT, color=GRAPHITE, lh=1.3))
y += 296
y = block(L, MX, y, CW, "verified", [
    "Contrast ratios are computed, not asserted (Appendix A). The ground is a cool",
    "drafting grey-green, not cream: cream + serif + terracotta is the current default",
    "look of machine-generated design, and it reads as a tell."], size=S_SMALL)
footer(L, 6, "§4.1–4.2 · scale & palette")

# ------------------------------------------------- 07 · dark + constraint ---
p, L = page("tokens-dark")
y = header(L, "Section 4.2", "Dark palette, and the constraint that makes it a system")

# dark panel
ph = 560
L.add({"type": "rect", "box": [MX, y, CW, ph], "fill": SURFACE})
L.text([MX + 36, y + 30, 500, 28], "ground wr-surface #131A1F",
       style=mono(S_SMALL, color=GRAPHITE_INV))
dark_rows = [
    ("wr-ink-inv", INK_INV, "13.50:1", "body text"),
    ("wr-petrol-live-inv", LIVE_INV, "7.06:1", "interactive"),
    ("wr-oxide-inv", OXIDE_INV, "5.53:1", "contradicted"),
    ("wr-graphite-inv", GRAPHITE_INV, "4.07:1", "metadata ONLY — below AA for body, never prose"),
]
yy = y + 88
for name, hexv, ratio, use in dark_rows:
    L.add({"type": "rect", "box": [MX + 36, yy, 72, 72], "fill": hexv})
    L.text([MX + 132, yy + 2, 330, 26], name, style=mono(S_SMALL, color=INK_INV, font_weight=600))
    L.text([MX + 132, yy + 34, 330, 24], f"{hexv} · {ratio} on surface",
           style=mono(S_ANNOT, color=GRAPHITE_INV))
    L.text([MX + 500, yy + 2, CW - 560, 78], use,
           style=serif(S_SMALL, color=INK_INV, lh=1.35))
    yy += 100
# petrol tint demo
L.add({"type": "rect", "box": [MX + 36, yy, CW - 72, 64], "fill": PETROL_TINT})
L.text([MX + 60, yy + 6, CW - 140, 66],
       "wr-petrol #1B3A45 inverts to a SURFACE TINT — not legible as a foreground here, never an ink.",
       style=serif(S_SMALL, color=INK_INV))
y += ph + 48

y = block(L, MX, y, CW, "verified", [
    "THE CONSTRAINT THAT MAKES THIS A SYSTEM RATHER THAN A PALETTE:",
    "wr-oxide is allocated to contradicted and nothing else. No warm hue appears",
    "anywhere for decorative purposes. The consequence: a warm mark anywhere in any",
    "artifact means exactly one thing, and a reader can scan a forty-page report for",
    "contradictions by colour alone."], size=S_BODY)
# oxide dose demonstration: one thin warm event on a cool field
L.add({"type": "rect", "box": [MX, y, CW, 56], "fill": PETROL, "opacity": 0.06})
for i in range(24):
    L.add({"type": "rect", "box": [MX + 16 + i * 41, y + 20, 24, 16],
           "fill": OXIDE if i == 17 else PETROL,
           "opacity": 1.0 if i == 17 else 0.35})
L.text([MX + CW - 420, y + 64, 420, 26], "one warm mark = one contradiction",
       style=mono(S_ANNOT, color=GRAPHITE))
footer(L, 7, "§4.2 · dark mode & the oxide reservation")

# ------------------------------------------ 08 · §4.3 the failed ramp -------
p, L = page("correction")
y = header(L, "Section 4.3", "A correction the arithmetic forced")

y = block(L, MX, y, CW, "verified", [
    "The first draft encoded warrant as an ink-density ramp on the content itself —",
    "verified at full ink, degrading to a ghosted unverified. The contrast computation",
    "kills it:"], size=S_BODY)

ramp = [
    ("verified · α 1.00", "#10171B", "15.91:1", True),
    ("derived · α 0.72", "#4E5456", "6.77:1", True),
    ("asserted · α 0.52", "#7B8081", "3.52:1", False),
    ("unverified · α 0.38", "#9A9E9E", "2.38:1", False),
]
SPEC = "The reader most needs to inspect exactly this claim."
for label, hexv, ratio, passes in ramp:
    L.add({"type": "rect", "box": [MX, y, CW, 92],
           "fill": PETROL if passes else OXIDE, "opacity": 0.05})
    L.text([MX + 20, y + 10, 300, 24], label, style=mono(S_SMALL, color=GRAPHITE))
    L.text([MX + 20, y + 44, 680, 40], SPEC,
           style=serif(S_BODY, color=hexv, lh=1.2))
    L.text([MX + 700, y + 30, 160, 28], ratio, style=mono(S_BODY, color=INK))
    verdict = "pass" if passes else "FAIL"
    vc = PETROL if passes else OXIDE
    L.text([MX + 880, y + 30, 120, 28], verdict,
           style=mono(S_BODY, color=vc, font_weight=700))
    y += 104
y += 20

y = block(L, MX, y, CW, "verified", [
    "Encoding warrant by making text harder to read is an accessibility failure and a",
    "rhetorical one: it renders the least-confident claims as the least legible — which",
    "is backwards. Those are the claims a reader most needs to inspect."], size=S_BODY)

y = block(L, MX, y, CW, "derived", [
    "THE RULE: the density ramp applies to the rail and to non-text ornament only.",
    "Body text is always full wr-ink. Recorded rather than silently fixed, because the",
    "failed version is the intuitive one and someone will propose it again."],
    size=S_BODY)
footer(L, 8, "§4.3 · the failed density ramp")

# ------------------------------------------------- 09 · §4.4 type specimen --
p, L = page("type")
y = header(L, "Section 4.4", "Type — three faces, one width axis")

# Archivo width axis: the register IS the axis
for wdth, wght, axis, note in [
        (62, 600, "wdth 62 · wght 600", "dense data labels"),
        (100, 500, "wdth 100 · wght 500", "UI and captions"),
        (125, 560, "wdth 125 · wght 560", "structural markers — the semantic register")]:
    L.text([MX, y, 760, 56], "Archivo, gauged",
           style=disp(S_DISP, wdth=wdth, wght=wght, color=INK))
    L.text([MX + 800, y + 14, 260, 26], axis, style=mono(S_SMALL, color=LIVE))
    L.text([MX + 800, y + 40, 300, 48], note, style=serif(S_ANNOT, color=GRAPHITE, lh=1.3))
    y += 88
y += 8
y = block(L, MX, y, CW, "asserted", [
    "The width axis carries meaning rather than taste: expanded (≥110) for structural",
    "labels and section markers, normal (100) for UI. One family, two semantic registers.",
    "Untested idea — this page is the rendered specimen §9 said was missing."], size=S_SMALL)

L.text([MX, y, 700, 40],
       "Source Serif 4 — long-form technical reading.",
       style=serif(S_H3, wght=600))
y += 48
L.text([MX, y, PROSE_W, 130],
       "A serif in a technical system is deliberate: these outputs are argued documents, "
       "not dashboards with paragraphs. The prose face must sustain a forty-page report "
       "without fatigue.", style=serif(S_BODY, lh=1.5))
y += 146
L.text([MX, y, CW, 34], "IBM Plex Mono — tags, keys, dimensions, code, figures",
       style=mono(S_H3, color=INK))
y += 44
L.text([MX, y, CW, 26], "VER DER ASR UNV CTR · 0.13 0.18 0.25 0.35 0.5 0.7 1 1.4 2 mm · wr-oxide #B3341F",
       style=mono(S_SMALL, color=GRAPHITE))
y += 56
y = block(L, MX, y, CW, "asserted", [
    "Declared face is Commit Mono; this runtime lacks it, so the render uses the declared",
    "first fallback, IBM Plex Mono — the substitution the system's own rules require",
    "naming rather than hiding. Deliberately not Inter, and not geometric-sans + display",
    "serif: both are current machine-default tells."], size=S_SMALL)

# modular scale staircase
L.text([MX, y, CW, 30], "Scale · ratio 1.2 from a 16px base",
       style=disp(S_H3, wdth=112, wght=620, color=PETROL))
y += 56
steps = [0.694, 0.833, 1.0, 1.2, 1.44, 1.728, 2.074, 2.488]
x = MX
base_y = y + 130
for r in steps:
    size = rem(r)
    L.text([x, base_y - size, 220, size + 8], "Aa",
           style=serif(size, wght=500))
    L.text([x, base_y + 12, 110, 20], f"{r:.3f}", style=mono(S_ANNOT, color=GRAPHITE))
    x += max(58, size * 1.7)
L.text([MX, base_y + 44, CW, 56],
       "0.694 is the provenance-annotation size, used nowhere else.\nSpacing: 8px grid, 4px half-step — the rail plus its gutter lands on grid in HTML and SVG alike.",
       style=serif(S_ANNOT, color=GRAPHITE, lh=1.55))
footer(L, 9, "§4.4–4.5 · type & spacing")

# --------------------------------------------------- 10 · §5 rail anatomy ---
p, L = page("rail-spec")
y = header(L, "Section 5", "The provenance rail — specification")

# anatomy diagram, zoomed
ax, ay, ah = MX + 60, y + 96, 170
L.add({"type": "rect", "box": [ax, ay, 12, ah], "fill": PETROL})           # rail (zoomed)
L.add({"type": "rect", "box": [ax + 12, ay, 48, ah], "fill": PETROL, "opacity": 0.07})  # gutter zone
L.text([ax + 76, ay + 6, 620, 120],
       "Content begins here. Body text is always full ink,\nregardless of warrant level.",
       style=serif(S_BODY, lh=1.5))
L.text([ax - 4, ay + ah + 14, 80, 22], "VER", style=mono(S_ANNOT, color=GRAPHITE))
# dimension callouts
L.add({"type": "line", "from": [ax, ay - 22], "to": [ax + 12, ay - 22], "stroke": GRAPHITE,
       "stroke_style": {"stroke_width": 1}})
L.text([ax - 24, ay - 76, 340, 48], "3 px rail (0.35 mm print)", style=mono(S_ANNOT, color=GRAPHITE))
L.add({"type": "line", "from": [ax + 12, ay - 6], "to": [ax + 60, ay - 6], "stroke": GRAPHITE,
       "stroke_style": {"stroke_width": 1, "stroke_dasharray": [3, 3]}})
L.text([ax + 72, ay - 30, 220, 22], "12 px gutter", style=mono(S_ANNOT, color=GRAPHITE))
L.text([ax + 76, ay + ah + 14, 720, 24],
       "mono tag · 0.694 rem · wr-graphite · baseline-aligned to the last line",
       style=serif(S_ANNOT, color=GRAPHITE))
y = ay + ah + 88

# treatment table with drawn rails
L.add({"type": "rect", "box": [MX, y, CW, 42], "fill": PETROL})
for tx, name in [(20, "LEVEL"), (268, "RAIL"), (392, "COLOUR"), (576, "α"),
                 (664, "DASH"), (772, "WIDTH"), (CW - 56, "TAG")]:
    L.text([MX + tx, y + 9, 160, 24], name,
           style=disp(S_ANNOT, wdth=118, wght=560, color=PAPER, letter_spacing=1.5))
y += 42
treat = [
    ("verified", "wr-petrol", "1.00", "none", "3px / 0.35mm"),
    ("derived", "wr-petrol", "0.72", "none", "3px / 0.35mm"),
    ("asserted", "wr-graphite", "1.00", "none", "3px / 0.25mm"),
    ("unverified", "wr-graphite", "0.60", "2 3", "3px / 0.25mm"),
    ("contradicted", "wr-oxide", "1.00", "none", "4px / 0.5mm"),
]
for i, (lv, ctok, alpha, dash, width) in enumerate(treat):
    t = RAIL[lv]
    if i % 2:
        L.add({"type": "rect", "box": [MX, y, CW, 56], "fill": PETROL, "opacity": 0.05})
    L.text([MX + 20, y + 15, 240, 26], lv, style=mono(S_SMALL, color=INK))
    # live rail sample
    if t["dash"]:
        L.add({"type": "line", "from": [MX + 280, y + 10], "to": [MX + 280, y + 46],
               "stroke": t["color"], "stroke_opacity": t["alpha"],
               "stroke_style": {"stroke_width": t["w"], "stroke_dasharray": t["dash"]}})
    else:
        L.add({"type": "rect", "box": [MX + 277, y + 10, t["w"], 36], "fill": t["color"],
               "opacity": t["alpha"]})
    L.text([MX + 392, y + 15, 180, 26], ctok, style=mono(S_SMALL, color=GRAPHITE))
    L.text([MX + 576, y + 15, 80, 26], alpha, style=mono(S_SMALL, color=GRAPHITE))
    L.text([MX + 664, y + 15, 100, 26], dash, style=mono(S_SMALL, color=GRAPHITE))
    L.text([MX + 772, y + 18, 170, 24], width, style=mono(S_ANNOT, color=GRAPHITE))
    L.text([MX + CW - 60, y + 15, 56, 26], t["tag"],
           style=mono(S_SMALL, color=t["color"], font_weight=600))
    y += 56
y += 28
y = block(L, MX, y, CW, "verified", [
    "Four discriminating channels — hue, density, dash, tag. Any single channel can be",
    "lost (grayscale print, colourblind reader, plain-text export, hairline PDF viewer)",
    "and the level remains recoverable."], size=S_SMALL)

# ISO width series
L.text([MX, y, CW, 30], "5.2 · Line weights — ISO 128-2:2022 series (mm)",
       style=disp(S_H3, wdth=112, wght=620, color=PETROL))
y += 50
mm2px = 150 / 25.4
x = MX
for wmm in [0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0]:
    L.add({"type": "line", "from": [x, y + 16], "to": [x + 84, y + 16], "stroke": INK,
           "stroke_style": {"stroke_width": max(0.6, wmm * mm2px)}})
    L.text([x, y + 30, 84, 20], f"{wmm}", style=mono(S_ANNOT, color=GRAPHITE))
    x += 108
y += 68
L.text([MX, y, CW, 84],
       "4:2:1 ratio between extra-wide, wide, and narrow. ISO 128-24:2014 is WITHDRAWN — engineering-svg may still cite it.\n"
       "Screen rails quantize to whole px (3 / 4); exact mm survive in the print and SVG adapters.\n"
       "Do not let a build step unify them — different targets, different rendering models.",
       style=serif(S_ANNOT, color=GRAPHITE, lh=1.55))
footer(L, 10, "§5 · the rail, specified")

# --------------------------------------------- 11 · §6 tokens + §7 adapters -
p, L = page("adapters")
y = header(L, "Sections 6–7", "One token source, six thin adapters")

code = [
    ("kw", "export const"), ("id", " WARRANT_LEVELS"), ("p", " = ["),
]
snippet = (
    'export const WARRANT_LEVELS =\n'
    '  ["verified","derived","asserted",\n'
    '   "unverified","contradicted"] as const;\n'
    '\n'
    'export function aggregate(levels) {\n'
    '  if (levels.length === 0) return "unverified";\n'
    '  if (levels.includes("contradicted"))\n'
    '    return "contradicted";       // absorbing\n'
    '  return levels.reduce((a, b) =>\n'
    '    RANK[a] <= RANK[b] ? a : b); // weakest wins\n'
    '}')
ch2 = 476
L.add({"type": "rect", "box": [MX, y, CW / 2 - 16, ch2], "fill": SURFACE})
L.text([MX + 28, y + 20, 400, 24], "packages/warrant-tokens/src/warrant.ts",
       style=mono(S_ANNOT, color=GRAPHITE_INV))
L.text([MX + 28, y + 58, CW / 2 - 72, ch2 - 80], snippet,
       style=mono(S_SMALL, color=INK_INV, line_height=1.5))
cx0 = MX + CW / 2 + 16
L.text([cx0 + 12, y + 8, CW / 2 - 40, ch2],
       "Single source of truth. Every other format is generated from it, never "
       "hand-maintained.\n\n"
       "An aggregate is never stronger than its weakest cited input — except that "
       "contradicted is absorbing: one contradiction poisons the composite, exactly "
       "as it should.",
       style=serif(S_BODY, lh=1.55))
y += ch2 + 44

adapters = [
    ("@warrant/css", "custom properties, both themes", "any HTML artifact"),
    ("@warrant/svg", "ISO stroke presets, hatches, the rail primitive", "engineering-svg"),
    ("@warrant/print", "@page, rail at mm widths, margin tag column", "print-ready"),
    ("@warrant/deck", "slide masters, warrant badge on claim slides", "pitch-deck-mastery"),
    ("@warrant/md", "frontmatter schema, blockquote \u2192 rail mapping", "product-briefing"),
    ("@warrant/viz", "ramps from petrol/graphite; OXIDE EXCLUDED", "advanced-dataviz"),
]
L.add({"type": "rect", "box": [MX, y, CW, 42], "fill": PETROL})
for tx, name in [(20, "PACKAGE"), (300, "TARGET"), (760, "CONSUMED BY")]:
    L.text([MX + tx, y + 9, 300, 24],
           name, style=disp(S_ANNOT, wdth=118, wght=560, color=PAPER, letter_spacing=1.5))
y += 42
for i, (pkg, target, consumer) in enumerate(adapters):
    if i % 2:
        L.add({"type": "rect", "box": [MX, y, CW, 52], "fill": PETROL, "opacity": 0.05})
    L.text([MX + 20, y + 13, 270, 26], pkg, style=mono(S_SMALL, color=LIVE, font_weight=600))
    L.text([MX + 300, y + 13, 450, 26], target, style=serif(S_SMALL))
    L.text([MX + 760, y + 13, CW - 780, 26], consumer, style=mono(S_ANNOT, color=GRAPHITE))
    y += 52
y += 28
y = block(L, MX, y, CW, "derived", [
    "The @warrant/viz exclusion matters: if oxide appears as the fifth colour of a",
    "categorical series, the reserved meaning of warm marks is destroyed system-wide.",
    "Markdown mapping: > [!VER] … extends GFM alerts with the five tags — renders as",
    "the rail, degrades to a labelled blockquote, stays greppable."], size=S_SMALL)
footer(L, 11, "§6–7 · tokens & adapters")

# -------------------------------------- 12 · §8 adoption + §9 weaknesses ----
p, L = page("adoption")
y = header(L, "Sections 8–9", "Adoption order, and where this is weak")

steps8 = [
    ("1", "warrant-tokens + @warrant/md", "highest-volume output is Markdown. One package, one week, immediately useful."),
    ("2", "@warrant/css + @warrant/print", "every HTML artifact becomes a printable one that matches the Markdown."),
    ("3", "@warrant/svg", "highest effort — includes correcting the withdrawn ISO 128-24 citation in engineering-svg."),
    ("4", "@warrant/viz + @warrant/deck", "only if the first three hold up. Stop when the returns flatten."),
]
for n, what, why in steps8:
    L.add({"type": "rect", "box": [MX, y, 52, 52], "fill": PETROL})
    L.text([MX, y + 8, 52, 36], n, style=disp(S_H2, wdth=100, wght=640, color=PAPER, align="center"))
    L.text([MX + 76, y, 460, 28], what, style=mono(S_BODY, color=INK, font_weight=600))
    L.text([MX + 76, y + 32, CW - 100, 40], why, style=serif(S_SMALL, color=GRAPHITE, lh=1.35))
    y += 84
y += 24

L.text([MX, y, CW, 32], "9 · Where this proposal is weak",
       style=disp(S_H2, wdth=112, wght=630, color=PETROL))
y += 60
weak = [
    ("unverified", "The interpretation may be wrong — reading (B) was chosen on inspectable evidence, not supplied intent. If (A) was meant: discard, not adapt."),
    ("unverified", "The name is the weakest decision. 'Warrant' carries a legal reading that may defeat the epistemic one."),
    ("asserted", "Archivo's width axis carrying semantics was untested — §4.4 of THIS render is the first specimen."),
    ("unverified", "Five warrant levels is a guess; if research-kb's five-tier hierarchy conflicts, that hierarchy wins — it exists and is in use."),
    ("verified", "No component inventory: this is a token and semantic layer, not yet a complete design system by the usual definition."),
    ("unverified", "Dark mode is under-specified — wr-petrol becoming a surface tint leaves every structural rule needing a separate dark decision."),
]
for lv, txt in weak:
    cx = rail(L, MX, y, 62, lv, tag=True)
    L.text([cx, y, CW - (cx - MX) - 20, 92], txt, style=serif(S_SMALL, lh=1.4))
    y += 104
y += 4
# appendix + colophon
L.add({"type": "line", "from": [MX, y], "to": [W - MX, y], "stroke": GRAPHITE,
       "stroke_opacity": 0.5, "stroke_style": {"stroke_width": 1}})
y += 22
L.text([MX, y, CW, 52],
       "Appendix A · contrast = (L_hi+0.05)/(L_lo+0.05), WCAG 2.x — every §4 ratio reproduces.",
       style=mono(S_ANNOT, color=GRAPHITE))
y += 30
L.text([MX, y, CW, 52],
       "Colophon · typeset in its own system · FrameForge · Archivo · Source Serif 4 · IBM Plex Mono",
       style=mono(S_ANNOT, color=GRAPHITE))
y += 30
L.text([MX, y, CW, 52],
       "(Commit Mono unavailable; its declared fallback is used and disclosed, as the system requires.)",
       style=mono(S_ANNOT, color=GRAPHITE))
footer(L, 12, "§8–9 · adoption & weaknesses")


def build():
    return doc.build()


if __name__ == "__main__":
    import pathlib
    out = pathlib.Path("out/warrant")
    out.mkdir(parents=True, exist_ok=True)
    doc.write(str(out / "warrant-design-system.fg.yaml"), fail_on_error=True)
    print("wrote", out / "warrant-design-system.fg.yaml")
