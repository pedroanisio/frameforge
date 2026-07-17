#!/usr/bin/env python3
"""GINGA ONE — house-style template for whitepaper / fine-print material.

A reusable FrameForge *template* (a "house style") for Ginga One's institutional
print material — whitepapers, briefings, letters, terms & conditions and other
fine-print collateral. The brand lives in ONE swap point (``BRAND`` + the three
design-system scales below), so an instance is a thin story over a shared,
on-brand, systematised skeleton.

Design system (audited by `frameforge_render.py <doc> --to audit`):
  • SIZES — 6 steps only (SCALE): display / h1 / h2 / body / small / micro
  • WEIGHTS — 4 (WEIGHT): regular / medium / bold / heavy
  • COLOURS — one tight brand palette (PAL)
  • SPACING — a 4-step rhythm (SPACE)
Nothing outside these scales is used; the audit target proves it.

────────────────────────────────────────────────────────────────────────────
PROVENANCE (CLAUDE.md rule 2). Identity RENDERED from the live SPA with
Playwright and read from computed styles + `:root` vars (gingaone.com, 2026-07):
  • Wordmark "GiNGA.ONE" · Typeface Inter · --green-primary #6B7B47 ·
    --blue-secondary #0066CC · ink #111827 · body #4B5563 · wash #E8EADC
  • "desde 2011" · comercial@gingaone.com · +55 (11) 99107-4404 · São Paulo
The wordmark is reconstructed as live Inter text (the site ships a white raster
that would blur upscaled for print). AI-generated — Claude Opus 4.8 via Claude Code.

Run from the repository root::

    uv run python static/examples/gingaone_house_style.py
    uv run python tooling/frameforge_render.py \\
        out/gingaone/gingaone-template.fg.yaml --to audit --out out/gingaone/audit
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
#  DESIGN SYSTEM — the only sizes / weights / colours / spacings allowed
# ═══════════════════════════════════════════════════════════════════════════
SCALE = {"display": 32, "h1": 20, "h2": 14, "body": 12, "small": 8.5, "micro": 7}
WEIGHT = {"reg": 400, "med": 600, "bold": 700, "heavy": 800}
SPACE = {"xs": 4, "sm": 8, "md": 16, "lg": 24}
PAL = {
    "ink":   "#111827",  # gray-900 — headings / strong text
    "body":  "#374151",  # gray-700 — running text
    "mute":  "#6B7280",  # gray-500 — secondary
    "faint": "#9CA3AF",  # gray-400 — faint labels
    "green": "#6B7B47",  # --green-primary (fills / accents)
    "green_dk": "#55632F",  # AA-contrast green for small text
    "blue":  "#0066CC",  # --blue-secondary (sparingly)
    "wash":  "#E8EADC",  # sage-cream surface
    "blue_pale": "#E3EBF3",  # hero-gradient end
    "soft":  "#F9FAFB",  # gray-50 surface
    "line":  "#E5E7EB",  # gray-200 hairline
    "white": "#FFFFFF",
}
INTER = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]

# ── page geometry: A4 portrait @ 96 dpi ────────────────────────────────────
W, H = 794, 1123
ML = MR = 88
CW = W - ML - MR
HEADER_Y, HEADER_RULE = 60, 84
FOOTER_RULE, FOOTER_Y = 1058, 1067


# ═══════════════════════════════════════════════════════════════════════════
#  primitives — every size/weight/colour comes from the scales above
# ═══════════════════════════════════════════════════════════════════════════
def T(x, y, w, h, s, *, size="body", color="ink", weight=None, align=None,
      track=None, lh=None, italic=False, upper=False, field=None, fit=True):
    st = {"font_size": SCALE[size], "color": PAL[color], "font_family": INTER}
    if fit:
        st["overflow"] = "shrink_to_fit"
    if weight:
        st["font_weight"] = WEIGHT[weight]
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


def LN(x1, y1, x2, y2, *, color="line", width=1.0):
    return {"type": "line", "from": [x1, y1], "to": [x2, y2],
            "stroke": PAL[color], "stroke_style": {"stroke_width": width}}


def PATH(d, *, stroke="mute", width=1.5):
    return {"type": "path", "d": d, "fill": "none", "stroke": PAL[stroke],
            "stroke_style": {"stroke_width": width, "stroke_linecap": "round",
                             "stroke_linejoin": "round"}}


def wordmark(x, y, *, size="h1", on_dark=True):
    return T(x, y, SCALE[size] * 9, SCALE[size] * 1.5, "GiNGA.ONE", size=size,
             weight="heavy", color="white" if on_dark else "ink", track=-0.3, fit=False)


# ═══════════════════════════════════════════════════════════════════════════
#  house style — named styles, all drawn from SCALE/WEIGHT/PAL
# ═══════════════════════════════════════════════════════════════════════════
def house_document(title: str) -> DocumentBuilder:
    b = DocumentBuilder(title=title, lang="pt-BR", profile="book")
    b.describe(f"Ginga One — {title}")
    b.meta(brand="Ginga One", template="gingaone-house-style",
           generated_by="Claude Opus 4.8 (1M context) via Claude Code")
    b.text_contract(overflow="shrink_to_fit", min_font_size=6.0)
    for name, hexv in PAL.items():
        b.define_color(name, hexv)

    def style(name, *, size, color, weight=None, lh=None, track=None,
              upper=False, italic=False, align=None, indent=None):
        kw = {"font_family": INTER, "font_size": SCALE[size], "color": PAL[color]}
        if weight:  kw["font_weight"] = WEIGHT[weight]
        if lh is not None:  kw["line_height"] = lh
        if track is not None:  kw["letter_spacing"] = track
        if upper:  kw["text_transform"] = "uppercase"
        if italic:  kw["font_style"] = "italic"
        if align:  kw["text_align"] = align
        if indent is not None:  kw["text_indent"] = indent
        b.define_style(name, **kw)

    style("kicker", size="small", color="green_dk", weight="bold", track=1.8, upper=True)
    style("h1", size="h1", color="ink", weight="heavy", lh=1.15, track=-0.4)
    style("h2", size="h2", color="ink", weight="bold", lh=1.25)
    # optional intro emphasis: SAME size as body (never a jarring size jump),
    # only a touch darker/heavier so a standfirst reads as intentional, not broken
    style("lead", size="body", color="ink", weight="med", lh=1.6, align="left", indent=0)
    style("body", size="body", color="body", weight="reg", lh=1.6, align="left", indent=0)
    style("callout", size="h2", color="green_dk", weight="med", lh=1.4, indent=0)
    style("caption", size="small", color="mute", weight="reg", lh=1.35)
    style("toc", size="small", color="mute", weight="reg", lh=1.6)
    style("fine", size="micro", color="body", weight="reg", lh=1.5, align="left", indent=0)
    style("fine_h", size="small", color="green_dk", weight="bold")
    return b


# ═══════════════════════════════════════════════════════════════════════════
#  running furniture
# ═══════════════════════════════════════════════════════════════════════════
def _header() -> list:
    return [
        T(ML, HEADER_Y, CW - 150, 16, "", size="small", color="mute", track=1.5,
          upper=True, weight="med", field={"string": "running"}),
        T(W - MR - 150, HEADER_Y, 150, 16, "GiNGA.ONE", size="small",
          color="green_dk", weight="heavy", align="right", track=-0.2),
        LN(ML, HEADER_RULE, W - MR, HEADER_RULE, width=1),
    ]


def _footer() -> list:
    return [
        LN(ML, FOOTER_RULE, W - MR, FOOTER_RULE, width=1),
        T(ML, FOOTER_Y, CW - 80, 14, "© 2026 Ginga One · gingaone.com · Confidencial",
          size="micro", color="faint"),
        T(W - MR - 80, FOOTER_Y, 80, 14, "1", size="small", color="mute",
          weight="bold", align="right", field="page"),
    ]


def body_master(b: DocumentBuilder) -> MasterBuilder:
    m = b.master("body", {"size": [W, H], "units": "px"})
    m.margin([HEADER_RULE + 22, MR, H - FOOTER_RULE + 20, ML])
    m.region("main", [ML, HEADER_RULE + 22, CW, 928])
    m.running_header(_header())
    m.running_footer(_footer())
    return m


def fineprint_master(b: DocumentBuilder) -> MasterBuilder:
    fx, ft = 72, HEADER_RULE + 18
    m = b.master("fine", {"size": [W, H], "units": "px"})
    m.margin([ft, fx, H - FOOTER_RULE + 20, fx])
    m.region("cols", [fx, ft, W - 2 * fx, 936])
    m.running_header(_header())
    m.running_footer(_footer())
    return m


# ═══════════════════════════════════════════════════════════════════════════
#  cover — olive masthead + green→blue hero gradient (mirrors the site)
# ═══════════════════════════════════════════════════════════════════════════
def cover_page(b: DocumentBuilder, *, doctype, title_lines, subtitle, ref, date, version):
    L = b.page("cover", canvas={"size": [W, H], "units": "px"},
               coordinate_mode="absolute").layer("cover")
    L.add(R(0, 0, W, 84, fill=PAL["green"], decorative=True))
    L.add(wordmark(ML, 28, on_dark=True))
    L.add(T(W - MR - 200, 34, 200, 20, "gingaone.com", size="small", color="white",
            weight="med", align="right"))
    L.add(R(0, 84, W, 556, decorative=True,
            fill=linear_gradient([(PAL["wash"], "0%"), (PAL["blue_pale"], "100%")], angle=90)))
    L.add(T(ML, 150, CW, 16, f"{doctype} · GINGA ONE", size="small",
            color="green_dk", weight="bold", track=2, upper=True))
    ty = 190
    for i, line in enumerate(title_lines):
        L.add(T(ML, ty + i * 44, CW - 20, 48, line, size="display", color="ink",
                weight="heavy", lh=1.05, track=-0.6))
    ty += len(title_lines) * 44 + 22
    L.add(R(ML, ty, 56, 4, fill=PAL["green"], decorative=True))
    L.add(T(ML, ty + 20, CW - 70, 56, subtitle, size="h2", color="body", lh=1.5))
    cy = 470
    L.add(R(ML, cy, 168, 36, radius=8, fill=PAL["green"], decorative=True))
    L.add(T(ML, cy + 11, 168, 16, f"EDIÇÃO {date[:4]} · v{version}", size="small",
            color="white", weight="bold", align="center", track=0.6))
    L.add(R(ML + 182, cy, 150, 36, radius=8, fill=PAL["white"], stroke=PAL["green"],
            stroke_style={"stroke_width": 1.4}, decorative=True))
    L.add(T(ML + 182, cy + 11, 150, 16, "CONFIDENCIAL", size="small", color="green_dk",
            weight="bold", align="center", track=0.6))
    my = 704
    for lab, val in [("REFERÊNCIA", ref), ("EDIÇÃO", f"{date} · versão {version}"),
                     ("CLASSIFICAÇÃO", "Confidencial — uso interno"),
                     ("CONTATO", "comercial@gingaone.com · +55 (11) 99107-4404")]:
        L.add(T(ML, my, 140, 14, lab, size="small", color="green_dk", weight="bold", track=1.4))
        L.add(T(ML + 150, my - 2, CW - 150, 18, val, size="body", color="ink", weight="med"))
        my += 30
    L.add(T(ML, 866, CW, 14, "CONFIANÇA DAS MAIORES EMPRESAS DO BRASIL",
            size="small", color="green_dk", weight="bold", track=1.6))
    L.add(T(ML, 886, CW, 18, "Walmart · Pão de Açúcar · Yamaha · Swift · Sanofi · "
            "Extra · Faber-Castell", size="body", color="mute", weight="med"))
    L.add(LN(ML, H - 92, W - MR, H - 92, width=1))
    L.add(T(ML, H - 76, CW, 16, "Ginga One · Desenvolvimento Mobile e Software · "
            "Especialistas em Varejo", size="small", color="mute"))
    L.add(T(ML, H - 58, CW, 14, "Documento-modelo gerado a partir do template "
            "FrameForge da Ginga One.", size="micro", color="faint", italic=True))


# ═══════════════════════════════════════════════════════════════════════════
#  DEMONSTRATION INSTANCE
# ═══════════════════════════════════════════════════════════════════════════
def build() -> DocumentBuilder:
    b = house_document("Engenharia de aplicativos para o varejo")
    cover_page(b, doctype="White Paper",
               title_lines=["Engenharia de", "aplicativos para", "o varejo"],
               subtitle="Criamos oportunidades e resolvemos problemas através da "
                        "tecnologia. Referência em desenvolvimento no Brasil desde 2011.",
               ref="GO-WP-2026-01", date="2026-07-17", version="1.0")

    body = body_master(b)

    def section(fl, kicker, title, sid, running):
        fl.spacer(height=SPACE["lg"])
        fl.para(kicker, style="kicker")
        fl.spacer(height=SPACE["xs"])
        fl.heading(1, title, id=sid, style="h1",
                   set_string=[{"name": "running", "value": running}])
        fl.spacer(height=SPACE["sm"])

    with b.section("corpo", master=body, media="paged") as fl:
        fl.para("Sumário", style="h2")
        fl.spacer(height=SPACE["sm"])
        fl.toc(levels=[1], leader=".", style="toc")

        section(fl, "Seção 01", "Contexto", "ctx", "01 · Contexto")
        fl.para("A Ginga One é referência em desenvolvimento no Brasil desde 2011, "
                "especializada em soluções e projetos de alta complexidade para o "
                "varejo. Este documento é um modelo: mostra como um único conjunto "
                "de tokens, masters e mobiliário de página compõe todo o material "
                "impresso da empresa com a mesma voz.", style="lead")
        fl.spacer(height=SPACE["sm"])
        fl.para("Os números do site institucional — mais de 14 anos de experiência, "
                "mais de 50 clientes de grande porte e três meses de garantia em "
                "alocação de recursos — são reproduzidos aqui como evidência citada, "
                "não como afirmação independente. Todo dado factual em um documento "
                "real deve trazer a sua fonte.", style="body")

        section(fl, "Seção 02", "Abordagem", "abr", "02 · Abordagem")
        fl.para("A abordagem separa a marca (tokens de cor e tipografia) da estrutura "
                "(masters de página) e do conteúdo (a história). Trocar a paleta ou a "
                "fonte re-veste todos os documentos sem tocar no texto.", style="body")
        fl.spacer(height=SPACE["sm"])
        fl.bullet([
            "**Tokens de marca** — o verde institucional e a face Inter em um único "
            "ponto de troca.",
            "**Masters** — um master de corpo e um de letra miúda, ambos com "
            "cabeçalho, rodapé e número de página corridos.",
            "**Aparato gerado** — sumário, numeração e notas, produzidos pelo motor "
            "de fluxo.",
        ], style="body")
        fl.spacer(height=SPACE["md"])
        fl.figure(_pipeline_figure(), size=[CW, 118], align="center",
                  caption="Fluxo Varejo → Mobile → Dados, desenhado como vetores no "
                  "próprio documento.", id="fig-fluxo")

        section(fl, "Seção 03", "Camadas de referência", "arq", "03 · Arquitetura")
        fl.para("Tabelas paginam e repetem o cabeçalho após cada quebra de página; o "
                "tema vem da marca.", style="body")
        fl.spacer(height=SPACE["sm"])
        fl.table(
            columns=[{"label": "Camada", "width": 150}, "Responsabilidade", "Cadência"],
            rows=[["Experiência", "Apps mobile e PDV", "Contínua"],
                  ["Serviços", "APIs e integração de varejo", "Semanal"],
                  ["Dados", "Eventos, catálogo e telemetria", "Streaming"],
                  ["Governança", "Verificação e conformidade", "Por release"]],
            header=True, caption="Tabela 1 — Camadas de referência (modelo).",
            style={"header_fill": PAL["green"], "header_text": PAL["white"],
                   "cell_text": PAL["ink"], "zebra_fill": PAL["soft"],
                   "grid_color": PAL["line"], "cell_size": SCALE["small"]})

        section(fl, "Seção 04", "Governança e verificação", "gov", "04 · Governança")
        fl.para("Toda saída gerada por IA é tratada como não verificada por padrão. A "
                "verificação é uma camada de projeto — não um pós-processamento "
                "opcional.", style="body")
        fl.spacer(height=SPACE["sm"])
        fl.add({"type": "block", "role": "note", "style": "callout",
                "fill": PAL["wash"], "padding": [SPACE["md"], 20],
                "children": [{"type": "paragraph", "style": "callout",
                              "text": "“A ausência de uma camada de verificação é um "
                              "defeito de projeto, não um erro de execução.”"}]})

    fine = fineprint_master(b)
    with b.section("letra-miuda", master=fine, media="paged") as fl:
        fl.para("Termos & Condições", style="kicker")
        fl.spacer(height=SPACE["xs"])
        fl.heading(1, "Termos, condições e avisos legais", id="terms", style="fine_h",
                   set_string=[{"name": "running", "value": "Termos & Condições"}])
        fl.spacer(height=SPACE["sm"])
        for head, txt in [
            ("1. Objeto", "Este instrumento é um modelo de letra miúda. Substitua cada "
             "cláusula pelo texto jurídico real, revisado pelo departamento competente, "
             "antes de qualquer publicação."),
            ("2. Confidencialidade", "As informações aqui contidas destinam-se ao uso "
             "interno e não devem ser reproduzidas sem autorização por escrito da Ginga One."),
            ("3. Propriedade intelectual", "Marcas, logotipos e conteúdos são de "
             "titularidade de seus respectivos detentores; o uso é regido pelos termos "
             "aplicáveis."),
            ("4. Limitação de responsabilidade", "Na máxima extensão permitida pela "
             "legislação aplicável, a responsabilidade limita-se aos termos expressamente "
             "acordados em contrato."),
            ("5. Proteção de dados", "O tratamento de dados pessoais observa a legislação "
             "vigente, incluindo a LGPD; consulte a política de privacidade para detalhes."),
            ("6. Foro", "Fica eleito o foro da comarca de São Paulo/SP para dirimir "
             "controvérsias, com renúncia a qualquer outro."),
        ]:
            fl.para([{"text": head + ". ", "style": {"font_weight": WEIGHT["bold"],
                     "color": PAL["ink"]}}, txt], style="fine")
        fl.spacer(height=SPACE["xs"])
        fl.para("Aviso metodológico: nenhum conteúdo deste modelo deve ser tomado como "
                "definitivo. Espelhando o DISCLAIMER.md do repositório, afirmações sem "
                "definição lógica ou referência verificável podem ser inválidas; toda "
                "cláusula real exige revisão jurídica.", style="fine")
    return b


def _pipeline_figure() -> dict:
    labels = [("Varejo", "green"), ("Mobile", "ink"), ("Dados", "blue")]
    children = []
    bw, gap, y = 152, 66, 30
    for i, (lab, col) in enumerate(labels):
        x = i * (bw + gap)
        children.append(R(x, y, bw, 58, radius=10, fill=PAL["soft"], decorative=True,
                          stroke=PAL[col], stroke_style={"stroke_width": 1.5}))
        children.append({"type": "text", "box": [x, y + 19, bw, 22], "text": lab,
                         "style": {"font_family": INTER, "font_size": SCALE["body"],
                         "font_weight": WEIGHT["bold"], "color": PAL[col],
                         "text_align": "center"}})
        if i < len(labels) - 1:
            ax = x + bw
            children.append(PATH(f"M {ax+8} {y+29} L {ax+gap-8} {y+29}"))
            children.append(PATH(f"M {ax+gap-15} {y+24} L {ax+gap-8} {y+29} "
                                 f"L {ax+gap-15} {y+34}"))
    total = 3 * bw + 2 * gap
    return {"type": "group", "box": [(CW - total) / 2, 0, total, 118],
            "children": children}


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built Ginga One template — pages={len(doc.pages)} ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:20]:
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
