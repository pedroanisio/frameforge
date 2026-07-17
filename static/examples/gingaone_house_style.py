#!/usr/bin/env python3
"""GINGA ONE — house-style template for whitepaper / fine-print material.

A reusable FrameForge *template* (a "house style") for Ginga One's institutional
print material — whitepapers, briefings, letters, terms & conditions and other
fine-print collateral. The brand lives in ONE swap point (``BRAND`` + the token
installer), so an instance is a thin story over a shared, on-brand skeleton.

The typesetting engine is the ``mode: flow`` layer: Knuth–Plass line breaking +
Liang hyphenation, page masters with running header/footer/page-number
furniture, multi-column fine print, and a generated table of contents.

────────────────────────────────────────────────────────────────────────────
PROVENANCE / VERIFICATION (CLAUDE.md rule 2 — "formalize means research")
────────────────────────────────────────────────────────────────────────────
The identity below is RENDERED from the live site with Playwright (the site is a
client-rendered SPA, so a plain fetch returns nothing) and read from its computed
styles + `:root` custom properties, gingaone.com, 2026-07-17:

  • Wordmark ...... "GiNGA.ONE" — bold Inter, white on the olive header bar
  • Typeface ...... Inter (63/64 text elements)                       [verified]
  • --green-primary  #6B7B47   (olive/sage) ...................... [:root var]
  • --blue-secondary #0066CC   (corporate blue) ................. [:root var]
  • ink #111827 · body #4B5563 · muted #9CA3AF · wash #E8EADC · gray-50 #F9FAFB
  • Positioning ... "Criamos oportunidades e resolvemos problemas através da
                    tecnologia" · "referência em desenvolvimento no Brasil
                    desde 2011"                                      [hero copy]
  • Numbers ....... 14+ anos · 50+ clientes de grande porte · 3 meses de
                    garantia                                     [site, verified]
  • Contact ....... comercial@gingaone.com · +55 (11) 99107-4404 · São Paulo, SP
  • Clients ....... Walmart, Pão de Açúcar, Yamaha, Swift, Sanofi, Extra,
                    Faber-Castell                                [logo wall]

The wordmark is reconstructed as live Inter text (the site ships a 141×30 white
raster that would blur upscaled for print); swap in the vector logo when
available. AI-generated artifact — Claude Opus 4.8 (1M context) via Claude Code.

Run from the repository root::

    uv run python static/examples/gingaone_house_style.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder  # noqa: E402
from frameforge.sdk.author import MasterBuilder  # noqa: E402
from frameforge.sdk.paint import linear_gradient  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
#  BRAND — the single swap point (values verified from gingaone.com)
# ═══════════════════════════════════════════════════════════════════════════
BRAND = {
    "name":       "Ginga One",
    "wordmark":   "GiNGA.ONE",
    "site":       "gingaone.com",
    "tagline":    "Desenvolvimento Mobile e Software · Especialistas em Varejo",
    "positioning": "Criamos oportunidades e resolvemos problemas através da tecnologia.",
    "since":      "2011",
    "lang":       "pt-BR",
    "email":      "comercial@gingaone.com",
    "phone":      "+55 (11) 99107-4404",
    "locality":   "São Paulo, SP · Brasil",
    "legal_name": "Ginga One",
    "clients":    ["Walmart", "Pão de Açúcar", "Yamaha", "Swift",
                   "Sanofi", "Extra", "Faber-Castell"],
}

# ── verified palette ───────────────────────────────────────────────────────
GREEN    = "#6B7B47"   # --green-primary (olive/sage)
GREEN_DK = "#55632F"   # darkened for AA-contrast small text
GREEN_XD = "#414B22"
BLUE     = "#0066CC"   # --blue-secondary
WASH     = "#E8EADC"   # sage-cream hero wash
BLUE_PALE = "#E3EBF3"  # pale-blue end of the hero gradient
INK      = "#111827"   # gray-900
BODY     = "#374151"   # gray-700 (print body)
BODY2    = "#4B5563"   # gray-600 (site body)
MUTE     = "#6B7280"   # gray-500
MUTE2    = "#9CA3AF"   # gray-400
LINE     = "#E5E7EB"   # gray-200
LINE2    = "#D1D5DB"   # gray-300
SOFT     = "#F9FAFB"   # gray-50
PAPER    = "#FFFFFF"

# ── typefaces (Inter, as on the site) ──────────────────────────────────────
INTER = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
MONO  = ["JetBrains Mono", "IBM Plex Mono", "DejaVu Sans Mono", "monospace"]

# ── page geometry: A4 portrait @ 96 dpi ────────────────────────────────────
W, H = 794, 1123
ML = MR = 88
CW = W - ML - MR
HEADER_Y, HEADER_RULE = 60, 84
FOOTER_RULE, FOOTER_Y = 1058, 1067


# ═══════════════════════════════════════════════════════════════════════════
#  primitives (text style under `style`; paint/stroke top-level)
# ═══════════════════════════════════════════════════════════════════════════
def T(x, y, w, h, s, *, size=12, color=INK, weight=None, align=None, font=None,
      track=None, lh=None, italic=False, upper=False, field=None, fit=True):
    st = {"font_size": size, "color": color, "font_family": font or INTER}
    if fit:
        st["overflow"] = "shrink_to_fit"
    if weight:
        st["font_weight"] = weight
    if align:
        st["text_align"] = align
    if track is not None:
        st["letter_spacing"] = track
    if lh is not None:
        st["line_height"] = lh
    if italic:
        st["font_style"] = "italic"
    if upper:
        st["text_transform"] = "uppercase"
    o = {"type": "text", "box": [x, y, w, h], "text": s, "style": st}
    if field is not None:
        o["field"] = field
    return o


def R(x, y, w, h, **f):
    return {"type": "rect", "box": [x, y, w, h], **f}


def LN(x1, y1, x2, y2, *, color=LINE, width=1.0):
    return {"type": "line", "from": [x1, y1], "to": [x2, y2],
            "stroke": color, "stroke_style": {"stroke_width": width}}


def PATH(d, *, fill="none", stroke=None, width=1.6, cap="round", join="round"):
    o = {"type": "path", "d": d, "fill": fill}
    if stroke is not None:
        o["stroke"] = stroke
        o["stroke_style"] = {"stroke_width": width,
                             "stroke_linecap": cap, "stroke_linejoin": join}
    return o


def wordmark(x, y, *, size=22, on_dark=True):
    """The 'GiNGA.ONE' wordmark reconstructed in Inter 800 (swap for the vector
    logo). White on the olive masthead; ink on paper."""
    col = "#FFFFFF" if on_dark else INK
    return T(x, y, size * 9, size * 1.5, BRAND["wordmark"], size=size, weight=800,
             color=col, track=-0.3, fit=False)


# ═══════════════════════════════════════════════════════════════════════════
#  house style — token installer
# ═══════════════════════════════════════════════════════════════════════════
def house_document(title: str) -> DocumentBuilder:
    b = DocumentBuilder(title=title, lang=BRAND["lang"], profile="book")
    b.describe(f"{BRAND['name']} — {title}")
    b.meta(brand=BRAND["name"], template="gingaone-house-style",
           generated_by="Claude Opus 4.8 (1M context) via Claude Code")
    b.text_contract(overflow="shrink_to_fit", min_font_size=6.0)
    install_house_style(b)
    return b


def install_house_style(b: DocumentBuilder) -> None:
    for name, value in {
        "green": GREEN, "green_dk": GREEN_DK, "blue": BLUE, "ink": INK,
        "body": BODY, "mute": MUTE, "line": LINE, "wash": WASH,
        "soft": SOFT, "paper": PAPER,
    }.items():
        b.define_color(name, value)

    b.define_style("kicker", font_family=INTER, font_size=9, font_weight=700,
                   letter_spacing=1.8, text_transform="uppercase", color=GREEN_DK)
    b.define_style("h1", font_family=INTER, font_size=22, font_weight=800,
                   line_height=1.14, color=INK, letter_spacing=-0.4)
    b.define_style("h2", font_family=INTER, font_size=14, font_weight=700,
                   line_height=1.2, color=INK, letter_spacing=-0.2)
    b.define_style("h3", font_family=INTER, font_size=10, font_weight=700,
                   letter_spacing=0.4, color=GREEN_DK)
    b.define_style("lead", font_family=INTER, font_size=12.5, line_height=1.55,
                   color=BODY, font_weight=400, text_align="left", text_indent=0)
    # left-aligned, no forced indent — the brand's clean web voice (Inter,
    # ragged-right), not loose justified word-spacing.
    b.define_style("body", font_family=INTER, font_size=10.5, line_height=1.6,
                   color=BODY, text_align="left", text_indent=0)
    b.define_style("callout", font_family=INTER, font_size=12.5, line_height=1.45,
                   color=GREEN_XD, font_weight=500, text_indent=0)
    b.define_style("caption", font_family=INTER, font_size=8.5, line_height=1.35,
                   color=MUTE)
    b.define_style("fine", font_family=INTER, font_size=7.8, line_height=1.45,
                   color=BODY2, text_align="left", text_indent=0)
    b.define_style("fine_h", font_family=INTER, font_size=8.5, font_weight=700,
                   letter_spacing=0.4, color=GREEN_DK)
    b.define_style("mono", font_family=MONO, font_size=8.5, color=INK, line_height=1.5)


# ═══════════════════════════════════════════════════════════════════════════
#  running furniture
# ═══════════════════════════════════════════════════════════════════════════
def _running_header() -> list:
    return [
        T(ML, HEADER_Y, CW - 150, 16, "", size=8.5, color=MUTE, track=1.5,
          upper=True, weight=600, field={"string": "running"}),
        T(W - MR - 150, HEADER_Y, 150, 16, BRAND["wordmark"], size=8.5,
          color=GREEN_DK, weight=800, align="right", track=-0.2),
        LN(ML, HEADER_RULE, W - MR, HEADER_RULE, color=LINE, width=1),
    ]


def _running_footer() -> list:
    return [
        LN(ML, FOOTER_RULE, W - MR, FOOTER_RULE, color=LINE, width=1),
        T(ML, FOOTER_Y, CW - 80, 14,
          f"© 2026 {BRAND['legal_name']} · {BRAND['site']} · Confidencial",
          size=7.5, color=MUTE2),
        T(W - MR - 80, FOOTER_Y, 80, 14, "1", size=8.5, color=MUTE,
          weight=600, align="right", field="page"),
    ]


# ═══════════════════════════════════════════════════════════════════════════
#  masters
# ═══════════════════════════════════════════════════════════════════════════
def body_master(b: DocumentBuilder) -> MasterBuilder:
    m = b.master("body", {"size": [W, H], "units": "px"})
    m.margin([HEADER_RULE + 22, MR, H - FOOTER_RULE + 20, ML])
    m.region("main", [ML, HEADER_RULE + 22, CW, 928])
    m.running_header(_running_header())
    m.running_footer(_running_footer())
    return m


def fineprint_master(b: DocumentBuilder) -> MasterBuilder:
    fx, ft = 72, HEADER_RULE + 18
    fw = W - 2 * fx
    m = b.master("fine", {"size": [W, H], "units": "px"})
    m.margin([ft, fx, H - FOOTER_RULE + 20, fx])
    m.region("cols", [fx, ft, fw, 936], columns=2, column_gap=28,
             column_fill="balance")
    m.running_header(_running_header())
    m.running_footer(_running_footer())
    return m


# ═══════════════════════════════════════════════════════════════════════════
#  cover — mirrors the site: olive masthead + green→blue hero gradient
# ═══════════════════════════════════════════════════════════════════════════
def cover_page(b: DocumentBuilder, *, doctype: str, title_lines: list[str],
               subtitle: str, ref: str, date: str, version: str) -> None:
    pg = b.page("cover", canvas={"size": [W, H], "units": "px"},
                coordinate_mode="absolute")
    L = pg.layer("cover")

    L.add(R(0, 0, W, 84, fill=GREEN, decorative=True))
    L.add(wordmark(ML, 28, size=23, on_dark=True))
    L.add(T(W - MR - 200, 34, 200, 20, BRAND["site"], size=10, color="#FFFFFF",
            weight=500, align="right"))

    L.add(R(0, 84, W, 556, fill=linear_gradient(
        [(WASH, "0%"), (BLUE_PALE, "100%")], angle=90), decorative=True))
    L.add(T(ML, 150, CW, 16, f"{doctype} · {BRAND['name'].upper()}", size=9.5,
            color=GREEN_DK, weight=700, track=2, upper=True))
    ty = 190
    for i, line in enumerate(title_lines):
        L.add(T(ML, ty + i * 50, CW - 20, 54, line, size=37, color=INK,
                weight=800, lh=1.05, track=-0.6))
    ty += len(title_lines) * 50 + 22
    L.add(R(ML, ty, 56, 4, fill=GREEN, decorative=True))
    L.add(T(ML, ty + 20, CW - 70, 56, subtitle, size=14, color=BODY, lh=1.5,
            weight=400))
    cy = 470
    L.add(R(ML, cy, 168, 36, radius=8, fill=GREEN, decorative=True))
    L.add(T(ML, cy + 11, 168, 16, f"EDIÇÃO {date[:4]} · v{version}", size=9.5,
            color="#FFFFFF", weight=700, align="center", track=0.6))
    L.add(R(ML + 182, cy, 150, 36, radius=8, fill="#FFFFFF", stroke=GREEN,
            stroke_style={"stroke_width": 1.4}, decorative=True))
    L.add(T(ML + 182, cy + 11, 150, 16, "CONFIDENCIAL", size=9.5, color=GREEN_DK,
            weight=700, align="center", track=0.6))

    my = 704
    for lab, val in [("REFERÊNCIA", ref), ("EDIÇÃO", f"{date} · versão {version}"),
                     ("CLASSIFICAÇÃO", "Confidencial — uso interno"),
                     ("CONTATO", f"{BRAND['email']} · {BRAND['phone']}")]:
        L.add(T(ML, my, 140, 14, lab, size=8, color=GREEN_DK, weight=700, track=1.4))
        L.add(T(ML + 150, my - 2, CW - 150, 18, val, size=11, color=INK, weight=500))
        my += 30
    L.add(T(ML, 866, CW, 14, "Confiança das maiores empresas do Brasil".upper(),
            size=8, color=GREEN_DK, weight=700, track=1.6))
    L.add(T(ML, 886, CW, 18, " · ".join(BRAND["clients"]), size=10.5,
            color=MUTE, weight=500))

    L.add(LN(ML, H - 92, W - MR, H - 92, color=LINE, width=1))
    L.add(T(ML, H - 76, CW, 16, f"{BRAND['name']} · {BRAND['tagline']}",
            size=9, color=MUTE))
    L.add(T(ML, H - 58, CW, 14,
            "Documento-modelo gerado a partir do template FrameForge da Ginga One.",
            size=8, color=MUTE2, italic=True))


# ═══════════════════════════════════════════════════════════════════════════
#  DEMONSTRATION INSTANCE — a plausible Ginga One whitepaper + fine print
# ═══════════════════════════════════════════════════════════════════════════
def build() -> DocumentBuilder:
    b = house_document("Engenharia de aplicativos para o varejo")

    cover_page(
        b, doctype="White Paper",
        title_lines=["Engenharia de", "aplicativos para", "o varejo"],
        subtitle=BRAND["positioning"] + " Referência em desenvolvimento no "
                 f"Brasil desde {BRAND['since']}.",
        ref="GO-WP-2026-01", date="2026-07-17", version="1.0",
    )

    body = body_master(b)

    def section(fl, kicker, title, sid, running):
        fl.spacer(height=20)
        fl.para(kicker, style="kicker")
        fl.spacer(height=3)
        fl.heading(1, title, id=sid, style="h1",
                   set_string=[{"name": "running", "value": running}])
        fl.spacer(height=4)

    with b.section("corpo", master=body, media="paged") as fl:
        fl.toc(title="Sumário", levels=[1], leader=".", style="caption")
        fl.spacer(height=14)

        section(fl, "Seção 01", "Contexto", "ctx", "01 · Contexto")
        fl.para("A Ginga One é referência em desenvolvimento no Brasil desde "
                f"{BRAND['since']}, especializada em soluções e projetos de alta "
                "complexidade para o varejo. Este documento é um modelo: mostra "
                "como um único conjunto de tokens, masters e mobiliário de página "
                "compõe todo o material impresso da empresa com a mesma voz.",
                style="lead")
        fl.spacer(height=6)
        fl.para("Os números do site institucional — mais de 14 anos de "
                "experiência, mais de 50 clientes de grande porte e três meses de "
                "garantia em alocação de recursos — são reproduzidos aqui como "
                "evidência citada, não como afirmação independente. Todo dado "
                "factual em um documento real deve trazer a sua fonte.",
                style="body")

        section(fl, "Seção 02", "Abordagem", "abr", "02 · Abordagem")
        fl.para("A abordagem separa a marca (tokens de cor e tipografia) da "
                "estrutura (masters de página) e do conteúdo (a história). Trocar "
                "a paleta ou a fonte re-veste todos os documentos sem tocar no "
                "texto.", style="body")
        fl.spacer(height=6)
        fl.bullet([
            "**Tokens de marca** — o verde institucional e a face Inter em um "
            "único ponto de troca.",
            "**Masters** — corpo de uma coluna e letra miúda em duas colunas, "
            "com cabeçalho e rodapé corridos.",
            "**Aparato gerado** — sumário, numeração e notas, produzidos pelo "
            "motor de fluxo.",
        ], style="body")
        fl.spacer(height=10)
        fl.figure(_pipeline_figure(), size=[CW, 128], align="center",
                  caption="Fluxo Varejo → Mobile → Dados, desenhado como vetores "
                  "no próprio documento.", id="fig-fluxo")

        section(fl, "Seção 03", "Camadas de referência", "arq", "03 · Arquitetura")
        fl.para("Tabelas paginam e repetem o cabeçalho após cada quebra de "
                "página; o tema vem da marca.", style="body")
        fl.spacer(height=6)
        fl.table(
            columns=[{"label": "Camada", "width": 150}, "Responsabilidade", "Cadência"],
            rows=[
                ["Experiência", "Apps mobile e PDV", "Contínua"],
                ["Serviços", "APIs e integração de varejo", "Semanal"],
                ["Dados", "Eventos, catálogo e telemetria", "Streaming"],
                ["Governança", "Verificação e conformidade", "Por release"],
            ],
            header=True, caption="Tabela 1 — Camadas de referência (modelo).",
            style={"header_fill": GREEN, "header_text": "#FFFFFF",
                   "cell_text": INK, "zebra_fill": SOFT},
        )

        section(fl, "Seção 04", "Governança e verificação", "gov", "04 · Governança")
        fl.para("Toda saída gerada por IA é tratada como não verificada por "
                "padrão. A verificação é uma camada de projeto — não um "
                "pós-processamento opcional.", style="body")
        fl.spacer(height=8)
        fl.add({"type": "block", "role": "note", "style": "callout",
                "fill": WASH, "padding": [16, 20],
                "children": [{"type": "paragraph", "style": "callout",
                              "text": "“A ausência de uma camada de verificação é "
                              "um defeito de projeto, não um erro de execução.”"}]})

    fine = fineprint_master(b)
    with b.section("letra-miuda", master=fine, media="paged") as fl:
        fl.para("Termos & Condições", style="kicker")
        fl.heading(1, "Termos, condições e avisos legais", id="terms",
                   style="fine_h",
                   set_string=[{"name": "running", "value": "Termos & Condições"}])
        fl.spacer(height=6)
        clauses = [
            ("1. Objeto", "Este instrumento é um modelo de letra miúda. Substitua "
             "cada cláusula pelo texto jurídico real, revisado pelo departamento "
             "competente, antes de qualquer publicação."),
            ("2. Confidencialidade", "As informações aqui contidas destinam-se ao "
             "uso interno e não devem ser reproduzidas sem autorização por escrito "
             "da Ginga One."),
            ("3. Propriedade intelectual", "Marcas, logotipos e conteúdos são de "
             "titularidade de seus respectivos detentores; o uso é regido pelos "
             "termos aplicáveis."),
            ("4. Limitação de responsabilidade", "Na máxima extensão permitida pela "
             "legislação aplicável, a responsabilidade limita-se aos termos "
             "expressamente acordados em contrato."),
            ("5. Proteção de dados", "O tratamento de dados pessoais observa a "
             "legislação vigente, incluindo a LGPD; consulte a política de "
             "privacidade para detalhes."),
            ("6. Garantia", "Serviços de alocação de recursos observam o prazo de "
             "garantia informado em proposta comercial."),
            ("7. Foro", "Fica eleito o foro da comarca de São Paulo/SP para dirimir "
             "controvérsias, com renúncia a qualquer outro."),
        ]
        for head, txt in clauses:
            fl.para([{"text": head + ". ", "style": {"font_weight": 700, "color": INK}},
                     txt], style="fine")
        fl.spacer(height=4)
        fl.para("Aviso metodológico: nenhum conteúdo deste modelo deve ser tomado "
                "como definitivo. Espelhando o DISCLAIMER.md do repositório, "
                "afirmações sem definição lógica ou referência verificável podem "
                "ser inválidas; toda cláusula real exige revisão jurídica.",
                style="fine")

    return b


def _pipeline_figure() -> dict:
    labels = [("Varejo", GREEN), ("Mobile", INK), ("Dados", BLUE)]
    children = []
    bw, gap, y = 152, 66, 34
    for i, (lab, col) in enumerate(labels):
        x = i * (bw + gap)
        children.append(R(x, y, bw, 62, radius=10, fill=SOFT, decorative=True,
                          stroke=col, stroke_style={"stroke_width": 1.5}))
        children.append({"type": "text", "box": [x, y + 21, bw, 22], "text": lab,
                         "style": {"font_family": INTER, "font_size": 12.5,
                         "font_weight": 700, "color": col, "text_align": "center"}})
        if i < len(labels) - 1:
            ax = x + bw
            children.append(PATH(f"M {ax+8} {y+31} L {ax+gap-8} {y+31}",
                                 stroke=MUTE2, width=1.5))
            children.append(PATH(f"M {ax+gap-15} {y+26} L {ax+gap-8} {y+31} "
                                 f"L {ax+gap-15} {y+36}", stroke=MUTE2, width=1.5))
    total = 3 * bw + 2 * gap
    return {"type": "group", "box": [(CW - total) / 2, 0, total, 128],
            "children": children}


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {BRAND['name']} template — pages={len(doc.pages)} "
          f"ok={report.ok} errors={len(errors)} warnings={len(warns)}")
    for i in (errors + warns)[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    from frameforge.sdk import serialize
    out_dir = os.path.join(ROOT, "out", "gingaone")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "gingaone-template.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
