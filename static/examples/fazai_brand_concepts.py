#!/usr/bin/env python3
"""FAZ.AI — six independent branding/logo concepts, rendered as boards.

Source brief: ``faz.ai.md`` (repo root) — FAZ.AI, from the spoken imperative
"faz aí", is a Brazilian platform that turns AI into *measured* business
results for SMBs ("IA que faz resultado"; manifesto: less hype, more margin).

Each concept is a fully independent identity — its own mark geometry, its own
typeface, its own palette, its own lockup architecture. Nothing is shared
between concepts except the presentation-board chrome:

    1. O PONTO       — pure wordmark, Inter Display Black; the "." drawn as a
                       result-green square: the point where AI becomes result.
    2. NO ALVO       — pictogram: three dots on a diagonal funnel into a solid
                       target disc with a knocked-out bullseye — scattered
                       experiments landing on one measured target; Fira Sans.
    3. CARIMBO FEITO — an execution stamp: vermilion badge, white check whose
                       energy breaks out of the corner as an arrow; Archivo.
    4. A CONTA       — ledger tally: four ink strokes and a fifth, closing
                       stroke in blue ("a conta fecha no azul") — results
                       counted, not promised; Cousine.
    5. FAZ.AÍ        — the vernacular voice: rounded lowercase Comfortaa with
                       the spoken accent ("aí") as the only colour.
    6. MONOGRAMA FA  — monogram: F of "faz" and A of "AI" fused in one glyph,
                       the 60° A-leg carrying the only colour change;
                       Bitstream Charter.

    Second round (07-12) — six logotype-led options, each pulling a distinct
    lever from logotype_composition_guide.yaml's technique taxonomy (the
    logotype is the default; the type itself carries the character):

    7. O TOTAL        — "underlined": slab wordmark over the accountant's
                        thin+thick double total-rule; Roboto Slab.
    8. A RAZÃO        — "slashes / mathematical marks": FAZ/AI as a ratio
                        (razão = ratio, reason, and the ledger); Ubuntu.
    9. ESTÊNCIL       — "stencil" + extreme B2B minimalism: crate-stamp
                        condensed caps on kraft, one ink only; Fira Sans
                        Compressed.
    10. FAZ MAIÚSCULO — "small/large" size contrast: giant FAZ, tiny .ai in
                        hype-purple — the hierarchy is the positioning;
                        Cantarell Extra Bold.
    11. MÃO E MENTE   — "mixed font": FAZ in a direct working sans, .AI in a
                        thinking serif — the whole company in one word's
                        contrast; Clear Sans + Source Serif 4.
    12. LINHA D'ÁGUA  — "cropped" + Gestalt closure: the wordmark dips below
                        a waterline and the eye completes it — what counts is
                        what stays above the line; Arimo.

    Composition follows out/logotype-composition-guide.yaml (doc-ray corpus)
    and the repo copy logotype_composition_guide.yaml: solid silhouettes,
    square-ish proportions, consistent stroke weight, whole-number angles,
    figure/ground, subtle asymmetry over symmetry.

Pages: 1 = overview contact sheet, 2–7 = one board per concept (hero lockup,
reversed chip, minimum-scale row, palette with duties, type + rationale).

Run from the repository root::

    uv run python static/examples/fazai_brand_concepts.py   # writes _tmp/fazai-brand/
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT_DIR = os.path.join(ROOT, "_tmp", "fazai-brand")
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    render_page_svgs,
    rgba,
    serialize,
)

W, H = 1280, 800

# Board chrome (presentation furniture, not part of any logo identity).
CHROME_FONT = ["Inter", "DejaVu Sans", "sans-serif"]
CHROME_MED = ["Inter Medium", "Inter", "DejaVu Sans", "sans-serif"]
MONO_FONT = ["Fira Mono", "DejaVu Sans Mono", "monospace"]


def _txt(page, box, spans, *, font, size, weight=400, color="#000", align="left",
         tracking=0.0, line_height=None):
    """One text object; the full face is carried on the block AND every span
    (per-span styles drop the block font_family otherwise)."""
    if isinstance(spans, str):
        spans = [(spans, color)]
    style = {"font_family": font, "font_size": size, "font_weight": weight,
             "letter_spacing": tracking, "text_align": align, "color": color}
    if line_height is not None:
        style["line_height"] = line_height
    page.add({"type": "text", "box": list(box),
              "spans": [{"text": t, "style": {"color": c, "font_family": font}}
                        for (t, c) in spans],
              "style": style})


# =========================================================================== #
# CONCEPT 1 — "O PONTO"  · pure wordmark · Inter Display Black · result-green
# =========================================================================== #
C1 = {
    "num": "01", "name": "O PONTO",
    "angle": "O ponto onde IA vira resultado — a marca é o próprio “.AI”.",
    "type_note": "Inter Display Black — neo-grotesca, caixa-alta, tracking fechado",
    "ground": "#F7F4EE", "ink": "#12151A", "accent": "#007A4A",
    "duties": [("#F7F4EE", "papel / fundo"), ("#12151A", "tinta / wordmark"),
               ("#007A4A", "o ponto — só ele carrega cor")],
    "rationale": ("Sem símbolo: a palavra é a marca. O ponto tipográfico vira um "
                  "quadrado verde-resultado assentado na linha de base — o pixel "
                  "de margem que a empresa procura. Funciona em qualquer corpo."),
}
C1_FONT = ["Inter Display Black", "Inter Black", "Inter", "sans-serif"]


def c1_lockup(page, cx, cy, S, ink, accent):
    """FAZ ▪ AI — flanked text boxes around a drawn baseline square."""
    F = 118 * S                      # font size
    base = cy + 0.36 * F             # optical baseline
    sq = 0.20 * F                    # dot square side
    g = 0.10 * F                     # gap around the square
    # measured with Inter Display Black advances: FAZ ≈ 2.02*F, AI ≈ 1.02*F
    w_faz, w_ai = 2.02 * F, 1.02 * F
    total = w_faz + g + sq + g + w_ai
    x0 = cx - total / 2.0
    yt = base - 0.79 * F             # text-box top so baseline lands on `base`
    _txt(page, [x0 - 0.5 * F, yt, w_faz + 0.5 * F, 1.3 * F], "FAZ",
         font=C1_FONT, size=F, weight=900, color=ink, align="right", tracking=-1.5 * S)
    # rendered baseline sits 0.223 em below `base` (dominant-baseline: central)
    page.rect([x0 + w_faz + g, base + 0.223 * F - sq, sq, sq], fill=accent)
    _txt(page, [x0 + w_faz + g + sq + g, yt, w_ai + 0.5 * F, 1.3 * F], "AI",
         font=C1_FONT, size=F, weight=900, color=ink, align="left", tracking=-1.5 * S)


def c1_icon(page, cx, cy, S, ink, paper, accent):
    """App-icon: ink tile, 'F' + green square dot."""
    side = 96 * S
    page.rect([cx - side / 2, cy - side / 2, side, side], fill=ink, radius=20 * S)
    F = 0.58 * side
    base = cy + 0.30 * F
    _txt(page, [cx - side, base - 0.79 * F, side * 0.92, 1.3 * F], "F",
         font=C1_FONT, size=F, weight=900, color=paper, align="right")
    d = 0.20 * F
    page.rect([cx + 0.10 * F, base + 0.223 * F - d, d, d], fill=accent)


# =========================================================================== #
# CONCEPT 2 — "NO ALVO"  · dots funnel into a bullseye disc · Fira Sans
# =========================================================================== #
C2 = {
    "num": "02", "name": "NO ALVO",
    "angle": "Priorizar e acertar: iniciativas dispersas, um alvo medido.",
    "type_note": "Fira Sans Bold — humanista firme, neutra ao lado do símbolo",
    "ground": "#F5F5F1", "ink": "#26292E", "accent": "#2E3A8C",
    "duties": [("#F5F5F1", "fundo"),
               ("#26292E", "grafite / os pontos e a letra"),
               ("#2E3A8C", "índigo — o alvo: o método que concentra")],
    "rationale": ("Do disperso ao certeiro: três pontos em diagonal — os "
                  "experimentos soltos — afunilam no disco-alvo de miolo "
                  "vazado. Círculos em harmonia, movimento por densidade, "
                  "assimetria na diagonal; sólido de longe, óbvio de perto."),
}
C2_FONT = ["Fira Sans", "sans-serif"]


def c2_mark(page, cx, cy, S, ink, accent, ground):
    """Three ink dots on a diagonal converge into a solid target disc whose
    bullseye ring is knocked out in the ground colour."""
    for (dx, dy, r) in ((-64.0, -50.0, 4.2), (-42.0, -29.0, 6.2), (-19.0, -8.0, 8.6)):
        page.circle([cx + dx * S, cy + dy * S], r * S, fill=ink)
    tx, ty, R = cx + 26 * S, cy + 26 * S, 30.0 * S
    page.circle([tx, ty], R, fill=accent)
    page.circle([tx, ty], 0.52 * R, fill=ground)     # knockout ring …
    page.circle([tx, ty], 0.28 * R, fill=accent)     # … around a solid bull


def c2_lockup(page, cx, cy, S, ink, accent, ground):
    c2_mark(page, cx - 178 * S, cy - 4 * S, S, ink, accent, ground)
    F = 62 * S
    _txt(page, [cx - 96 * S, cy - 0.52 * F, 460 * S, 1.3 * F], "FAZ.AI",
         font=C2_FONT, size=F, weight=700, color=ink, align="left", tracking=1.5 * S)


# =========================================================================== #
# CONCEPT 3 — "CARIMBO FEITO"  · stamp badge + breakout check · Archivo
# =========================================================================== #
C3 = {
    "num": "03", "name": "CARIMBO FEITO",
    "angle": "Menos hype, mais feito: o carimbo de execução que estoura o quadrado.",
    "type_note": "Archivo SemiBold — grotesca de imprensa, caixa-alta espaçada",
    "ground": "#FAF6F0", "ink": "#201D1B", "accent": "#C93A2B",
    "duties": [("#FAF6F0", "papel quente"), ("#201D1B", "fuligem / wordmark"),
               ("#C93A2B", "vermelhão — o carimbo e a seta que escapa")],
    "rationale": ("“Faz aí” é imperativo: a marca é um carimbo de FEITO. O "
                  "check é branco dentro do selo; a energia dele estoura o canto "
                  "como seta vermelha — feito não é o fim, é o próximo degrau."),
}
C3_FONT = ["Archivo", "sans-serif"]  # weight 600 selects the SemiBold instance


def c3_mark(page, cx, cy, S, ink, accent, paper):
    side = 124 * S
    page.rect([cx - side / 2, cy - side / 2, side, side], fill=accent, radius=26 * S)
    # the check, fully inside the badge (white)
    page.polyline([[cx - 30 * S, cy + 2 * S], [cx - 7 * S, cy + 26 * S],
                   [cx + 38 * S, cy - 28 * S]],
                  fill="none", stroke=paper,
                  stroke_style={"stroke_width": 15 * S, "stroke_linecap": "round",
                                "stroke_linejoin": "round"})
    # the breakout arrow: continues the check's final stroke out of the corner
    ux, uy = 0.640, -0.768          # unit vector of the check's last segment
    x0, y0 = cx + 46 * S, cy - 38 * S
    x1, y1 = cx + 74 * S, cy - 72 * S
    page.line([x0, y0], [x1, y1], stroke=accent,
              stroke_style={"stroke_width": 13 * S, "stroke_linecap": "round"})
    # arrowhead at (x1, y1)
    px, py = -uy, ux
    tip = [x1 + 20 * S * ux, y1 + 20 * S * uy]
    page.polygon([tip, [x1 + 14 * S * px, y1 + 14 * S * py],
                  [x1 - 14 * S * px, y1 - 14 * S * py]], fill=accent)


def c3_lockup(page, cx, cy, S, ink, accent, paper):
    c3_mark(page, cx, cy - 46 * S, S, ink, accent, paper)
    F = 46 * S
    _txt(page, [cx - 300 * S, cy + 58 * S, 600 * S, 1.3 * F], "FAZ.AI",
         font=C3_FONT, size=F, weight=600, color=ink, align="center", tracking=7 * S)


# =========================================================================== #
# CONCEPT 4 — "A CONTA"  · ledger tally, fifth stroke in blue · Cousine
# =========================================================================== #
C4 = {
    "num": "04", "name": "A CONTA",
    "angle": "Resultado contado, não prometido — e a conta fecha no azul.",
    "type_note": "Cousine Bold — a máquina de escrever do livro-caixa",
    "ground": "#EFEFE9", "ink": "#1B1B18", "accent": "#1E5AAE",
    "duties": [("#EFEFE9", "papel de razão"),
               ("#1B1B18", "tinta / os quatro riscos e a letra"),
               ("#1E5AAE", "azul — o quinto risco: a conta fecha no azul")],
    "rationale": ("Cinco riscos de contagem: quatro na tinta e o quinto — o "
                  "que fecha o grupo — em azul, porque no Brasil resultado bom "
                  "é estar no azul. Contar o que foi feito é o gesto de "
                  "medição mais honesto que existe. Um traço, uma espessura."),
}
C4_FONT = ["Cousine", "Fira Mono", "monospace"]


def c4_mark(page, cx, cy, S, ink, accent):
    """Tally-five: four upright strokes, the diagonal closing stroke in blue."""
    w = max(12.0 * S, 1.2)
    gap, h = 24.0 * S, 78.0 * S
    x0 = cx - 1.5 * gap
    for i in range(4):
        page.line([x0 + i * gap, cy - h / 2], [x0 + i * gap, cy + h / 2],
                  stroke=ink,
                  stroke_style={"stroke_width": w, "stroke_linecap": "round"})
    # the fifth stroke: 30° diagonal, overshooting the group on both sides
    dx = 0.5 * (3 * gap + 30 * S)
    dy = dx * math.tan(math.radians(30))
    page.line([cx - dx, cy + dy], [cx + dx, cy - dy], stroke=accent,
              stroke_style={"stroke_width": w, "stroke_linecap": "round"})


def c4_lockup(page, cx, cy, S, ink, accent):
    c4_mark(page, cx, cy - 44 * S, 0.95 * S, ink, accent)
    F = 54 * S
    _txt(page, [cx - 300 * S, cy + 62 * S, 600 * S, 1.3 * F], "FAZ.AI",
         font=C4_FONT, size=F, weight=700, color=ink, align="center", tracking=2 * S)


# =========================================================================== #
# CONCEPT 5 — "FAZ.AÍ"  · vernacular lowercase wordmark · Comfortaa · gold í
# =========================================================================== #
C5 = {
    "num": "05", "name": "FAZ.AÍ",
    "angle": "A voz falada: “faz aí” — a marca fala como o dono fala.",
    "type_note": "Comfortaa Bold — geométrica arredondada, caixa-baixa",
    "ground": "#FBF3E4", "ink": "#33261A", "accent": "#A16207",
    "duties": [("#FBF3E4", "creme"), ("#33261A", "café / wordmark"),
               ("#A16207", "ouro — só o “í” falado leva cor")],
    "rationale": ("O nome vem da rua, não do vale do silício. Caixa-baixa "
                  "arredondada, tom de conversa; o acento do “aí” é a única "
                  "cor — ouro, porque o resultado é dinheiro, não demo."),
}
C5_FONT = ["Comfortaa", "Comfortaa Light", "sans-serif"]


def c5_lockup(page, cx, cy, S, ink, accent):
    F = 96 * S
    _txt(page, [cx - 400 * S, cy - 0.52 * F, 800 * S, 1.4 * F],
         [("faz.a", ink), ("í", accent)],
         font=C5_FONT, size=F, weight=700, align="center")


def c5_icon(page, cx, cy, S, ink, paper, accent):
    side = 96 * S
    page.rect([cx - side / 2, cy - side / 2, side, side], fill=ink, radius=side / 2.6)
    F = 0.60 * side
    _txt(page, [cx - side, cy - 0.60 * F, side * 0.96, 1.3 * F], "f",
         font=C5_FONT, size=F, weight=700, color=paper, align="right")
    page.circle([cx + 0.24 * F, cy + 0.28 * F], 0.11 * F, fill=accent)


# =========================================================================== #
# CONCEPT 6 — "MONOGRAMA FA"  · fused F+A glyph, 60° leg · Bitstream Charter
# =========================================================================== #
C6 = {
    "num": "06", "name": "MONOGRAMA FA",
    "angle": "F de faz + A de AI, fundidos numa letra só.",
    "type_note": "Bitstream Charter Bold — serifa transicional: contrato e resultado",
    "ground": "#F7F2EA", "ink": "#241E18", "accent": "#7E2954",
    "duties": [("#F7F2EA", "marfim"), ("#241E18", "tinta / o F e a letra"),
               ("#7E2954", "vinho — a perna do A: a IA entra na estrutura")],
    "rationale": ("Monograma: o braço do F é o topo do A e a barra do meio vira "
                  "travessão; a perna a 60° fecha o glifo. A cor muda só na "
                  "perna — assimetria sutil que guia o olho e separa as duas "
                  "letras sem separar a forma."),
}
C6_FONT = ["Bitstream Charter", "Charis SIL", "serif"]


def c6_mark(page, cx, cy, S, ink, wine):
    """FA monogram: F skeleton + 60° A-leg; the leg alone carries the accent."""
    u = 11.0 * S
    x0, y0 = cx - 5.1 * u, cy - 4.0 * u      # glyph bbox ≈ 10.2u × 8u, centred
    run = 8.0 / math.tan(math.radians(60))   # horizontal run of the full leg
    # F: stem, top arm (doubles as the A's apex bar), middle arm (A crossbar)
    page.rect([x0, y0, 1.5 * u, 8.0 * u], fill=ink)
    page.rect([x0, y0, 5.6 * u, 1.4 * u], fill=ink)
    page.rect([x0, y0 + 3.5 * u, 6.2 * u, 1.4 * u], fill=ink)
    # A-leg: 60° parallelogram strip from the top arm's right end to baseline
    lx = x0 + 4.1 * u                        # leg top-left at the arm's end
    w = 1.6 * u                              # horizontal cut of the strip
    page.polygon([[lx, y0], [lx + w, y0],
                  [lx + w + run * u, y0 + 8.0 * u],
                  [lx + run * u, y0 + 8.0 * u]], fill=wine)


def c6_lockup(page, cx, cy, S, ink, wine):
    c6_mark(page, cx - 168 * S, cy, S, ink, wine)
    F = 58 * S
    _txt(page, [cx - 76 * S, cy - 0.52 * F, 460 * S, 1.3 * F], "FAZ.AI",
         font=C6_FONT, size=F, weight=700, color=ink, align="left", tracking=2 * S)


# =========================================================================== #
# CONCEPT 7 — "O TOTAL"  · underlined: the accountant's double rule · R. Slab
# =========================================================================== #
C7 = {
    "num": "07", "name": "O TOTAL",
    "angle": "A soma fecha: o sublinhado duplo de total de livro-caixa.",
    "type_note": "Roboto Slab Bold — a slab da máquina de somar",
    "ground": "#F4F1EA", "ink": "#201F1D", "accent": "#12586C",
    "duties": [("#F4F1EA", "papel"), ("#201F1D", "tinta / a palavra e o fio fino"),
               ("#12586C", "petróleo — o fio grosso: o total fechado")],
    "rationale": ("Alavanca “underlined”: contador fecha o total com dois fios, "
                  "fino e grosso. A palavra é a marca; o sublinhado é a prova "
                  "de que a conta fechou. Slab serif — a letra das somadoras."),
}
C7_FONT = ["Roboto Slab", "serif"]


def c7_lockup(page, cx, cy, S, ink, accent):
    F = 88 * S
    _txt(page, [cx - 300 * S, cy - 44 * S - 0.65 * F, 600 * S, 1.3 * F], "FAZ.AI",
         font=C7_FONT, size=F, weight=700, color=ink, align="center", tracking=1 * S)
    w = 312 * S
    page.rect([cx - w / 2, cy + 26 * S, w, max(2.6 * S, 0.6)], fill=ink)
    page.rect([cx - w / 2, cy + 36 * S, w, max(7.5 * S, 1.0)], fill=accent)


def c7_small(page, cx, cy, S, ink, accent):
    F = 74 * S
    _txt(page, [cx - 120 * S, cy - 34 * S - 0.65 * F, 240 * S, 1.3 * F], "F",
         font=C7_FONT, size=F, weight=700, color=ink, align="center")
    w = 58 * S
    page.rect([cx - w / 2, cy + 26 * S, w, max(2.4 * S, 0.5)], fill=ink)
    page.rect([cx - w / 2, cy + 34 * S, w, max(6.5 * S, 0.9)], fill=accent)


# =========================================================================== #
# CONCEPT 8 — "A RAZÃO"  · slash as ratio bar: FAZ/AI · Ubuntu
# =========================================================================== #
C8 = {
    "num": "08", "name": "A RAZÃO",
    "angle": "FAZ/AI — a barra de razão: resultado por real investido.",
    "type_note": "Ubuntu Bold — humanista com personalidade própria",
    "ground": "#F5F2EE", "ink": "#241F1C", "accent": "#B4552D",
    "duties": [("#F5F2EE", "papel"), ("#241F1C", "tinta / FAZ e AI"),
               ("#B4552D", "cobre — a barra: a razão que a empresa acompanha")],
    "rationale": ("Alavanca “slashes” e marcas matemáticas: a barra faz do nome "
                  "uma fração — FAZ sobre AI, resultado sobre ferramenta — e "
                  "“razão” é conta e é motivo. A diagonal é o único movimento "
                  "do conjunto; todo o resto fica reto."),
}
C8_FONT = ["Ubuntu", "sans-serif"]


def c8_lockup(page, cx, cy, S, ink, accent):
    F = 92 * S
    w_faz, w_sl, w_ai = 2.02 * F, 0.42 * F, 1.06 * F
    g = 0.05 * F
    total = w_faz + g + w_sl + g + w_ai
    x0 = cx - total / 2.0
    box_y, box_h = cy - 0.65 * F, 1.3 * F
    _txt(page, [x0 - 0.5 * F, box_y, w_faz + 0.5 * F, box_h], "FAZ",
         font=C8_FONT, size=F, weight=700, color=ink, align="right")
    _txt(page, [x0 + w_faz + g, box_y, w_sl, box_h], "/",
         font=C8_FONT, size=1.18 * F, weight=700, color=accent, align="center")
    _txt(page, [x0 + w_faz + g + w_sl + g, box_y, w_ai + 0.5 * F, box_h], "AI",
         font=C8_FONT, size=F, weight=700, color=ink, align="left")


def c8_small(page, cx, cy, S, ink, accent):
    F = 74 * S
    box_y, box_h = cy - 0.65 * F, 1.3 * F
    _txt(page, [cx - 200 * S, box_y, 200 * S - 0.06 * F, box_h], "F",
         font=C8_FONT, size=F, weight=700, color=ink, align="right")
    _txt(page, [cx - 0.21 * F, box_y, 0.42 * F, box_h], "/",
         font=C8_FONT, size=1.18 * F, weight=700, color=accent, align="center")
    _txt(page, [cx + 0.27 * F, box_y, 200 * S, box_h], "A",
         font=C8_FONT, size=F, weight=700, color=ink, align="left")


# =========================================================================== #
# CONCEPT 9 — "ESTÊNCIL"  · crate-stamp stencil, one ink · Fira Compressed
# =========================================================================== #
C9 = {
    "num": "09", "name": "ESTÊNCIL",
    "angle": "Marca de caixote: feita pra operação, não pro palco.",
    "type_note": "Fira Sans Compressed — condensada pesada, corte de estêncil",
    "ground": "#EAE3D6", "ink": "#26221E", "accent": "#26221E",
    "duties": [("#EAE3D6", "kraft — papel de caixote"),
               ("#26221E", "tinta única: estêncil é uma cor só")],
    "rationale": ("Alavanca “stencil” + minimalismo extremo B2B: duas pontes de "
                  "corte atravessam a palavra, como marca batida a tinta em "
                  "caixa de madeira. Uma cor, nenhum enfeite — logística, chão "
                  "de fábrica, execução."),
}
C9_FONT = ["Fira Sans Compressed", "Fira Sans Condensed", "sans-serif"]


def c9_lockup(page, cx, cy, S, ink, ground):
    F = 104 * S
    _txt(page, [cx - 300 * S, cy - 0.65 * F, 600 * S, 1.3 * F], "FAZ.AI",
         font=C9_FONT, size=F, weight=800, color=ink, align="center", tracking=3 * S)
    w = 268 * S
    for dy in (-14.0, 14.0):
        page.rect([cx - w / 2, cy + (dy + 21) * S - 2.6 * S, w, 5.2 * S], fill=ground)


def c9_small(page, cx, cy, S, ink, ground):
    F = 92 * S
    _txt(page, [cx - 120 * S, cy - 0.65 * F, 240 * S, 1.3 * F], "FZ",
         font=C9_FONT, size=F, weight=800, color=ink, align="center", tracking=2 * S)
    w = 84 * S
    for dy in (-13.0, 13.0):
        page.rect([cx - w / 2, cy + (dy + 19) * S - 2.4 * S, w, 4.8 * S], fill=ground)


# =========================================================================== #
# CONCEPT 10 — "FAZ MAIÚSCULO"  · small/large contrast · Cantarell ExtraBold
# =========================================================================== #
C10 = {
    "num": "10", "name": "FAZ MAIÚSCULO",
    "angle": "O FAZ é gigante; a .ai é detalhe — a hierarquia é o conceito.",
    "type_note": "Cantarell Extra Bold — humanista robusta: o grito e o sussurro",
    "ground": "#F6F4F0", "ink": "#1C1B1E", "accent": "#6B34A8",
    "duties": [("#F6F4F0", "fundo"), ("#1C1B1E", "tinta / FAZ em corpo máximo"),
               ("#6B34A8", "roxo-hype — rebaixado a nota de rodapé: .ai")],
    "rationale": ("Alavanca “small/large”: o contraste de corpo carrega o "
                  "posicionamento inteiro. O fazer em corpo máximo; a IA em "
                  "corpo mínimo — e de propósito no roxo do hype, "
                  "pequenininho. Menos discurso de IA, mais FAZ."),
}
C10_FONT = ["Cantarell Extra Bold", "Cantarell", "sans-serif"]


def c10_lockup(page, cx, cy, S, ink, accent):
    Fb, Fs = 124 * S, 36 * S
    w_faz = 2.03 * Fb
    total = w_faz + 0.06 * Fb + 0.95 * Fs * 2.4
    x0 = cx - total / 2.0
    _txt(page, [x0 - 0.5 * Fb, cy - 0.65 * Fb, w_faz + 0.5 * Fb, 1.3 * Fb], "FAZ",
         font=C10_FONT, size=Fb, weight=800, color=ink, align="right",
         tracking=-1.0 * S)
    # baseline-align the small ".ai" with the big FAZ (central-anchor math)
    base = cy + 0.364 * Fb
    small_c = base - 0.364 * Fs
    _txt(page, [x0 + w_faz + 0.06 * Fb, small_c - 0.65 * Fs, 300 * S, 1.3 * Fs],
         ".ai", font=C10_FONT, size=Fs, weight=800, color=accent, align="left")


def c10_small(page, cx, cy, S, ink, accent):
    Fb, Fs = 108 * S, 34 * S
    _txt(page, [cx - 160 * S, cy - 0.65 * Fb, 160 * S + 0.36 * Fb, 1.3 * Fb], "F",
         font=C10_FONT, size=Fb, weight=800, color=ink, align="right")
    base = cy + 0.364 * Fb
    small_c = base - 0.364 * Fs
    _txt(page, [cx + 0.40 * Fb, small_c - 0.65 * Fs, 160 * S, 1.3 * Fs], ".ai",
         font=C10_FONT, size=Fs, weight=800, color=accent, align="left")


# =========================================================================== #
# CONCEPT 11 — "MÃO E MENTE"  · mixed font: sans FAZ + serif .AI
# =========================================================================== #
C11 = {
    "num": "11", "name": "MÃO E MENTE",
    "angle": "Duas vozes numa palavra: o FAZ executa, o .AI pensa.",
    "type_note": "Clear Sans Bold + Source Serif 4 — a mão direta e a mente serifada",
    "ground": "#F3F2EF", "ink": "#1F2124", "accent": "#33475B",
    "duties": [("#F3F2EF", "fundo"), ("#1F2124", "tinta / FAZ — a mão"),
               ("#33475B", "aço — .AI em serifa: a mente")],
    "rationale": ("Alavanca “mixed font”: a fonte nunca é neutra — cada "
                  "família dá à palavra uma personalidade. FAZ em sans de "
                  "trabalho, direta; .AI em serifa de estudo, pensada. A "
                  "empresa inteira cabe no contraste entre as duas metades."),
}
C11_SANS = ["Clear Sans", "sans-serif"]
C11_SERIF = ["Source Serif 4", "serif"]


def c11_lockup(page, cx, cy, S, ink, steel):
    F = 96 * S
    w_faz, w_ai = 2.02 * F, 1.38 * F
    x0 = cx - (w_faz + w_ai) / 2.0
    box_y, box_h = cy - 0.65 * F, 1.3 * F
    _txt(page, [x0 - 0.5 * F, box_y, w_faz + 0.5 * F, box_h], "FAZ",
         font=C11_SANS, size=F, weight=700, color=ink, align="right")
    _txt(page, [x0 + w_faz, box_y, w_ai + 0.5 * F, box_h], ".AI",
         font=C11_SERIF, size=1.02 * F, weight=600, color=steel, align="left")


def c11_small(page, cx, cy, S, ink, steel):
    F = 90 * S
    box_y, box_h = cy - 0.65 * F, 1.3 * F
    _txt(page, [cx - 220 * S, box_y, 220 * S - 0.02 * F, box_h], "F",
         font=C11_SANS, size=F, weight=700, color=ink, align="right")
    _txt(page, [cx + 0.04 * F, box_y, 220 * S, box_h], "A",
         font=C11_SERIF, size=1.02 * F, weight=600, color=steel, align="left")


# =========================================================================== #
# CONCEPT 12 — "LINHA D'ÁGUA"  · cropped at the waterline · Arimo
# =========================================================================== #
C12 = {
    "num": "12", "name": "LINHA D'ÁGUA",
    "angle": "Acima da linha d'água: o resultado que aparece.",
    "type_note": "Arimo Bold — neutra com dispositivo: a linha faz a marca",
    "ground": "#F2F5F6", "ink": "#1B3A4B", "accent": "#2C7DA0",
    "duties": [("#F2F5F6", "fundo / a água"),
               ("#1B3A4B", "marinho / a palavra emersa"),
               ("#2C7DA0", "azul-água — a linha d'água")],
    "rationale": ("Alavanca “cropped”: a palavra mergulha na linha d'água e o "
                  "olho completa o que falta (fechamento Gestalt). O que "
                  "importa é o que fica acima da linha — margem, caixa, "
                  "resultado à vista. Sans neutra + dispositivo."),
}
C12_FONT = ["Arimo", "Liberation Sans", "sans-serif"]


def _c12_wave(page, cx, y, half_w, S, accent):
    n, amp, wl = 64, 3.2 * S, 46.0 * S
    pts = [[cx - half_w + 2 * half_w * k / n,
            y + amp * math.sin(2 * math.pi * (2 * half_w * k / n) / wl)]
           for k in range(n + 1)]
    page.polyline(pts, fill="none", stroke=accent,
                  stroke_style={"stroke_width": max(4.2 * S, 0.8),
                                "stroke_linecap": "round"})


def c12_lockup(page, cx, cy, S, ink, accent, ground):
    F = 94 * S
    _txt(page, [cx - 300 * S, cy - 10 * S - 0.65 * F, 600 * S, 1.3 * F],
         "FAZ.AI", font=C12_FONT, size=F, weight=700, color=ink,
         align="center", tracking=1 * S)
    # the crop: everything below the waterline is submerged (paper)
    base = cy - 10 * S + 0.364 * F
    y_crop = base - 0.14 * 0.72 * F
    page.rect([cx - 320 * S, y_crop, 640 * S, 90 * S], fill=ground)
    _c12_wave(page, cx, y_crop, 236 * S, S, accent)


def c12_small(page, cx, cy, S, ink, accent, ground):
    F = 96 * S
    _txt(page, [cx - 120 * S, cy - 8 * S - 0.65 * F, 240 * S, 1.3 * F], "FA",
         font=C12_FONT, size=F, weight=700, color=ink, align="center")
    base = cy - 8 * S + 0.364 * F
    y_crop = base - 0.14 * 0.72 * F
    page.rect([cx - 90 * S, y_crop, 180 * S, 70 * S], fill=ground)
    _c12_wave(page, cx, y_crop, 66 * S, S, accent)


# =========================================================================== #
# Lockup dispatch (light + reversed) per concept.
# =========================================================================== #
def draw_lockup(page, idx, cx, cy, S, *, reversed_=False):
    c = CONCEPTS[idx]
    ink = c["ground"] if reversed_ else c["ink"]
    if idx == 0:
        c1_lockup(page, cx, cy, S, ink, c["accent"] if not reversed_ else "#19A56B")
    elif idx == 1:
        # dark ground: indigo target brightens, knockout ring cut in the chip ink
        accent = "#7B93E8" if reversed_ else c["accent"]
        ground = c["ink"] if reversed_ else c["ground"]
        c2_lockup(page, cx, cy, S, ink, accent, ground)
    elif idx == 2:
        paper = c["ink"] if reversed_ else c["ground"]
        c3_lockup(page, cx, cy, S, ink, c["accent"], paper)
    elif idx == 3:
        c4_lockup(page, cx, cy, S, ink, c["accent"] if not reversed_ else "#6FA0E8")
    elif idx == 4:
        c5_lockup(page, cx, cy, S, ink, c["accent"] if not reversed_ else "#D9A425")
    elif idx == 5:
        wine = "#C4628F" if reversed_ else c["accent"]
        c6_lockup(page, cx, cy, S, ink, wine)
    elif idx == 6:
        c7_lockup(page, cx, cy, S, ink, "#3E9DB5" if reversed_ else c["accent"])
    elif idx == 7:
        c8_lockup(page, cx, cy, S, ink, "#E08A57" if reversed_ else c["accent"])
    elif idx == 8:
        # stencil bridges are cut in whatever the ground is behind the word
        c9_lockup(page, cx, cy, S, ink, c["ink"] if reversed_ else c["ground"])
    elif idx == 9:
        c10_lockup(page, cx, cy, S, ink, "#B07BE8" if reversed_ else c["accent"])
    elif idx == 10:
        steel = "#A9BED3" if reversed_ else c["accent"]
        c11_lockup(page, cx, cy, S, ink, steel)
    elif idx == 11:
        wave = "#56B3D9" if reversed_ else c["accent"]
        ground = c["ink"] if reversed_ else c["ground"]
        c12_lockup(page, cx, cy, S, ink, wave, ground)


def draw_small(page, idx, cx, cy, S):
    """Minimum-scale element: the mark alone (or the icon for type-led concepts)."""
    c = CONCEPTS[idx]
    if idx == 0:
        c1_icon(page, cx, cy, S, c["ink"], c["ground"], c["accent"])
    elif idx == 1:
        c2_mark(page, cx, cy, S, c["ink"], c["accent"], c["ground"])
    elif idx == 2:
        c3_mark(page, cx, cy, S, c["ink"], c["accent"], c["ground"])
    elif idx == 3:
        c4_mark(page, cx, cy, S, c["ink"], c["accent"])
    elif idx == 4:
        c5_icon(page, cx, cy, S, c["ink"], c["ground"], c["accent"])
    elif idx == 5:
        c6_mark(page, cx, cy, S, c["ink"], c["accent"])
    elif idx == 6:
        c7_small(page, cx, cy, S, c["ink"], c["accent"])
    elif idx == 7:
        c8_small(page, cx, cy, S, c["ink"], c["accent"])
    elif idx == 8:
        c9_small(page, cx, cy, S, c["ink"], c["ground"])
    elif idx == 9:
        c10_small(page, cx, cy, S, c["ink"], c["accent"])
    elif idx == 10:
        c11_small(page, cx, cy, S, c["ink"], c["accent"])
    elif idx == 11:
        c12_small(page, cx, cy, S, c["ink"], c["accent"], c["ground"])


CONCEPTS = [C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12]


# =========================================================================== #
# Boards.
# =========================================================================== #
def _chrome(page, c):
    ink = c["ink"]
    _txt(page, [56, 42, 500, 20], "FAZ.AI — EXPLORAÇÃO DE MARCA",
         font=CHROME_MED, size=12.5, weight=500, color=ink, tracking=3.0)
    _txt(page, [W - 556, 42, 500, 20], f"CONCEITO {c['num']} · {c['name']}",
         font=CHROME_MED, size=12.5, weight=500, color=ink, align="right", tracking=3.0)
    page.line([56, 72], [W - 56, 72], stroke=rgba(ink, 0.35),
              stroke_style={"stroke_width": 1.0})
    _txt(page, [56, H - 54, 700, 20], c["angle"],
         font=CHROME_FONT, size=13, weight=400, color=ink)
    _txt(page, [W - 456, H - 54, 400, 20], "IA que faz resultado.",
         font=CHROME_MED, size=12.5, weight=500, color=ink, align="right", tracking=1.5)


def _concept_board(b, idx):
    c = CONCEPTS[idx]
    page = b.page(f"concept-{c['num']}", canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    page._lettering_depth += 1
    page.rect([0, 0, W, H], fill=c["ground"])
    _chrome(page, c)

    # hero lockup, light ground (the page itself)
    draw_lockup(page, idx, 400, 360, 1.0)

    rx = 810
    # reversed chip
    page.rect([rx, 108, 420, 208], fill=c["ink"], radius=10)
    draw_lockup(page, idx, rx + 210, 212, 0.42, reversed_=True)

    # minimum-scale row
    _txt(page, [rx, 348, 420, 18], "REDUÇÃO", font=CHROME_MED, size=11,
         weight=500, color=c["ink"], tracking=3.0)
    for sx, s in ((rx + 60, 0.55), (rx + 190, 0.34), (rx + 300, 0.20)):
        draw_small(page, idx, sx, 430, s)
    page.line([rx, 500, ], [rx + 420, 500], stroke=rgba(c["ink"], 0.25),
              stroke_style={"stroke_width": 1.0})

    # palette chips with duties
    _txt(page, [rx, 518, 420, 18], "PALETA", font=CHROME_MED, size=11,
         weight=500, color=c["ink"], tracking=3.0)
    y = 546
    for hexv, duty in c["duties"]:
        page.rect([rx, y, 34, 34], fill=hexv, stroke=rgba(c["ink"], 0.5),
                  stroke_style={"stroke_width": 1.0})
        _txt(page, [rx + 46, y + 2, 374, 16], hexv.upper(),
             font=MONO_FONT, size=12, weight=500, color=c["ink"])
        _txt(page, [rx + 46, y + 18, 374, 16], duty,
             font=CHROME_FONT, size=11.5, weight=400, color=c["ink"])
        y += 44

    # type + rationale (left column, under the hero)
    _txt(page, [56, 560, 660, 20], "TIPOGRAFIA", font=CHROME_MED, size=11,
         weight=500, color=c["ink"], tracking=3.0)
    _txt(page, [56, 582, 660, 22], c["type_note"],
         font=CHROME_FONT, size=14.5, weight=400, color=c["ink"])
    _txt(page, [56, 622, 660, 20], "CONCEITO", font=CHROME_MED, size=11,
         weight=500, color=c["ink"], tracking=3.0)
    _txt(page, [56, 644, 640, 72], c["rationale"],
         font=CHROME_FONT, size=14.5, weight=400, color=c["ink"], line_height=1.45)
    return page


def _overview(b, sid, subtitle, start):
    page = b.page(sid, canvas={"size": [W, H], "units": "px"},
                  coordinate_mode="absolute")
    page._lettering_depth += 1
    page.rect([0, 0, W, H], fill="#EFECE6")
    ink = "#17191D"
    _txt(page, [56, 46, 900, 34], "FAZ.AI — caminhos de marca",
         font=["Inter Display SemiBold", "Inter SemiBold", "Inter", "sans-serif"],
         size=26, weight=600, color=ink)
    _txt(page, [56, 84, 900, 20], subtitle,
         font=CHROME_FONT, size=14, weight=400, color="#4A4C50")
    _txt(page, [W - 356, 52, 300, 20], "2026 · FRAMEFORGE",
         font=CHROME_MED, size=12, weight=500, color="#4A4C50", align="right", tracking=3.0)

    gw, gh, gx0, gy0, gap = 378, 296, 56, 130, 17
    for k in range(6):
        i = start + k
        c = CONCEPTS[i]
        col, row = k % 3, k // 3
        x = gx0 + col * (gw + gap)
        y = gy0 + row * (gh + gap)
        page.rect([x, y, gw, gh], fill=c["ground"], radius=8, stroke="#C9C5BC",
                  stroke_style={"stroke_width": 1.0})
        draw_lockup(page, i, x + gw / 2, y + 128, 0.52)
        _txt(page, [x + 20, y + gh - 62, gw - 40, 18],
             f"{c['num']} · {c['name']}", font=CHROME_MED, size=13, weight=500,
             color=c["ink"], tracking=1.5)
        _txt(page, [x + 20, y + gh - 40, gw - 40, 32], c["angle"],
             font=CHROME_FONT, size=11.5, weight=400, color=c["ink"], line_height=1.3)
    return page


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FAZ.AI — Brand Concepts", profile="deck", lang="pt-BR")
    _overview(b, "overview-a",
              "Rodada 1 (01–06): identidades independentes — marca, tipo e "
              "paleta próprios. IA que faz resultado.", 0)
    _overview(b, "overview-b",
              "Rodada 2 (07–12): logotipos — o tipo é a marca; cada opção puxa "
              "uma alavanca do guia de composição.", 6)
    for i in range(len(CONCEPTS)):
        _concept_board(b, i)
    return b


def main() -> int:
    doc = build().build()
    os.makedirs(OUT_DIR, exist_ok=True)
    svgs = render_page_svgs(doc)
    names = (["fazai-overview-a.svg", "fazai-overview-b.svg"]
             + [f"fazai-concept-{c['num']}.svg" for c in CONCEPTS])
    for name, svg in zip(names, svgs):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
    with open(os.path.join(OUT_DIR, "fazai-brand.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {len(names)} SVG(s) + YAML to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
