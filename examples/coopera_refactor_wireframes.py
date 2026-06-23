#!/usr/bin/env python3
"""Twenty distinct refactor proposals for the Coopera (Sicoob) rewards site &
marketplace — composed as low-fidelity wireframes with the FrameGraph Python SDK,
plus an "IA na jornada" capstone mapping AI capabilities across the funnel.

Grounded in the *live* site (shopcoopera.com.br + sicoob.com.br/coopera, probed
June 2026 via Playwright): a VTEX marketplace ("Navegue por experiência" —
Shopping / Agronegócio / Saúde / Viagens) where cooperados earn Coopera points
(cashback 3–8 pts/R$) via partner purchases through the Sicoob Super App (credited
in up to 45 days), points valid 24 months, redeemable for 250k+ products OR as
cash-back (invoice discount / account credit / wallet), paid with points + card +
PIX. Sections: Ofertas, Produtos dos Cooperados, Mais vendidos, Doações.

Distinct from the Esfera deck on two real axes Coopera owns: it is a *cooperative*
(cooperados, sobras, local singular cooperative, member-made products, donations)
and points double as *cash* (3 redemption destinations). Identity is therefore
Coopera teal, not Esfera red. Each page pairs a concept rail (problem → approach →
outcome → AI insight) with a minimal grayscale wireframe; one teal accent marks
the new idea. Mirrors the Reclame Aqui pain (points vanish, redemption errors).

Run from the repository root::

    uv run python examples/coopera_refactor_wireframes.py
"""
from __future__ import annotations

import os
import sys
import textwrap

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    grid,
    inset,
    row,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# ---- frame + palette (wireframe: grayscale + one Coopera-teal accent) ------ #
# NOTE: the accent token is named "red" so the proven Esfera component helpers
# reuse verbatim; here its VALUE is Coopera teal — that is the identity swap.
W, H = 1440, 980
RAIL_X, RAIL_W = 32, 366
MX = 430
MW = W - MX - 32
TOP = 86
BODY_H = H - TOP - 32
CANVAS = {"size": [W, H], "units": "px"}

COLORS = {
    "paper":  "#FFFFFF",
    "canvas": "#F3F6F5",
    "rail":   "#F7FAF9",
    "ink":    "#13211E",
    "sub":    "#4F5C58",
    "muted":  "#8C9A95",
    "faint":  "#B7C4BF",
    "fill":   "#EAF0EE",
    "fill2":  "#DEE7E4",
    "bar":    "#C4D0CC",
    "barlt":  "#D7E0DC",
    "line":   "#D2DCD8",
    "rowalt":  "#F6F9F8",
    # accent — Coopera / Sicoob teal-green (token kept as "red" for helper reuse)
    "red":    "#0A8C7E",
    "redSft": "#E0F2EF",
    "redDk":  "#0A5C52",
    "good":   "#2F7D55",
    "goodSft": "#E4F1E9",
}

SANS = ["DejaVu Sans", "Arial", "sans-serif"]
MONO = ["DejaVu Sans Mono", "Courier New", "monospace"]


def ts(size, weight=400, color="ink", **kw):
    return dict(font_family=SANS, font_size=size, font_weight=weight, color=color, **kw)


STYLES = {
    "band":    ts(13, 700, "ink", letter_spacing=0.4),
    "bandMut": ts(12, 600, "muted", letter_spacing=0.6),
    "bandR":   ts(12, 700, "red", align="right", letter_spacing=0.6),
    "num":     ts(46, 800, "red", letter_spacing=-1),
    "title":   ts(21, 800, "ink", letter_spacing=-0.4, line_height=1.12),
    "axis":    dict(font_family=MONO, font_size=11, font_weight=700, color="redDk",
                    letter_spacing=0.3),
    "lbl":     dict(font_family=SANS, font_size=10.5, font_weight=700, color="muted",
                    letter_spacing=1.2, text_transform="uppercase"),
    "para":    ts(12.5, 400, "sub", line_height=1.5),
    "bull":    ts(12.5, 500, "ink", line_height=1.42),
    "foot":    dict(font_family=MONO, font_size=10.5, color="muted"),
    "logo":    ts(16, 800, "ink", letter_spacing=-0.3),
    "nav":     ts(12.5, 600, "sub"),
    "navA":    ts(12.5, 700, "red"),
    "h1":      ts(18, 800, "ink", letter_spacing=-0.3),
    "h2":      ts(14, 700, "ink"),
    "h3":      ts(12.5, 700, "ink"),
    "body":    ts(12, 400, "sub", line_height=1.45),
    "mut":     ts(11.5, 400, "muted"),
    "tiny":    ts(10.5, 500, "muted"),
    "kpi":     ts(26, 800, "ink", letter_spacing=-0.8),
    "kpiR":    ts(26, 800, "red", letter_spacing=-0.8),
    "pts":     ts(13, 800, "red"),
    "chip":    ts(11.5, 600, "sub"),
    "chipA":   ts(11.5, 700, "red"),
    "btn":     ts(12, 700, "paper", align="center"),
    "btnG":    ts(12, 700, "sub", align="center"),
    "glyph":   ts(13, 700, "muted", align="center"),
    "glyphW":  ts(13, 800, "paper", align="center"),
    "glyphR":  ts(13, 800, "red", align="center"),
    "ava":     ts(11, 700, "sub", align="center"),
    "tab":     ts(12.5, 600, "muted"),
    "tabA":    ts(12.5, 700, "ink"),
    "th":      dict(font_family=SANS, font_size=10.5, font_weight=700, color="sub",
                    letter_spacing=0.4, text_transform="uppercase"),
    "td":      ts(12, 500, "ink"),
    "url":     dict(font_family=MONO, font_size=11, color="sub"),
    "place":   ts(12, 400, "muted"),
    "right":   ts(12, 700, "ink", align="right"),
    "ctr":     ts(12, 600, "sub", align="center"),
    "big":     ts(34, 800, "ink", align="center", letter_spacing=-1),
}

HAIR = {"stroke_width": 1.0}
DASH = {"stroke_width": 1.1, "stroke_dasharray": [4, 3]}
DASHR = {"stroke_width": 1.4, "stroke_dasharray": [5, 3]}


# ======================================================================= #
#  component vocabulary  (reused verbatim from the Esfera deck engine)
# ======================================================================= #
def T(page, box, s, **kw):
    """Emit one text run wrapped in a boxless one-child group.

    The ``tabular-box-model`` audit counts layer-top-level text objects and does
    not recurse into groups, so wrapping each glyph run keeps dense wireframe
    text from reading as an (unintended) data table. See the SDK memory note.
    """
    with page.grouped() as g:
        g.text(box, s, **kw)


def bars(page, box, n=3, gap=7, h=8, last=0.6, color="bar", radius=3):
    x, y, w, _ = box
    cy = y
    for i in range(n):
        bw = w * (last if i == n - 1 else 1.0)
        page.rect([x, cy, bw, h], fill=color, radius=radius)
        cy += h + gap


def ghost(page, box, label=None, radius=10, fill="fill", dash=True):
    page.rect(box, fill=fill, stroke="faint", stroke_style=DASH if dash else HAIR,
              radius=radius)
    if label is not None:
        x, y, w, h = box
        T(page, [x, y + h / 2 - 8, w, 16], label, style="glyph")


def card(page, box, *, fill="paper", radius=10, stroke="line", style=HAIR):
    page.rect(box, fill=fill, stroke=stroke, stroke_style=style, radius=radius)


def pill(page, box, text=None, *, fill="fill", style="chip", stroke=None, radius=None,
         pad=11):
    x, y, w, h = box
    r = radius if radius is not None else h / 2
    kw = {"fill": fill, "radius": r}
    if stroke:
        kw["stroke"] = stroke
        kw["stroke_style"] = HAIR
    page.rect(box, **kw)
    if text is not None:
        T(page, [x + pad, y + h / 2 - 8, w - 2 * pad, 16], text, style=style)


def button(page, box, label, kind="primary"):
    if kind == "primary":
        pill(page, box, None, fill="red", radius=7)
        st = "btn"
    elif kind == "dark":
        pill(page, box, None, fill="ink", radius=7)
        st = "btn"
    else:
        pill(page, box, None, fill="paper", stroke="line", radius=7)
        st = "btnG"
    x, y, w, h = box
    T(page, [x, y + h / 2 - 8, w, 16], label, style=st)


def icon(page, box, glyph="▢", *, fill="fill", style="glyph", radius=7):
    x, y, w, h = box
    page.rect(box, fill=fill, radius=radius)
    T(page, [x, y + h / 2 - 9, w, 18], glyph, style=style)


def circle(page, cx, cy, r, *, fill="fill", stroke=None, dash=False):
    kw = {"fill": fill, "radius": r}
    if stroke:
        kw["stroke"] = stroke
        kw["stroke_style"] = DASH if dash else HAIR
    page.rect([cx - r, cy - r, 2 * r, 2 * r], **kw)


def avatar(page, cx, cy, r, initials=None, *, fill="fill2"):
    circle(page, cx, cy, r, fill=fill, stroke="line")
    if initials:
        T(page, [cx - r, cy - 7, 2 * r, 14], initials, style="ava")


_TONE = {"red": ("redSft", "redDk"), "good": ("goodSft", "good"),
         "muted": ("fill", "sub")}


def badge(page, box, text, tone="muted"):
    bg, fg = _TONE.get(tone, _TONE["muted"])
    x, y, w, h = box
    page.rect(box, fill=bg, radius=h / 2)
    T(page, [x, y + h / 2 - 7, w, 14], text,
              style=dict(font_family=SANS, font_size=10.5, font_weight=700,
                         color=fg, align="center"))


def tabs(page, box, items, active=0):
    x, y, w, h = box
    page.rect([x, y + h - 1, w, 1], fill="line")
    cx = x
    for i, label in enumerate(items):
        tw = 20 + len(label) * 7.2
        T(page, [cx, y + h / 2 - 8, tw, 16], label,
                  style="tabA" if i == active else "tab")
        if i == active:
            page.rect([cx, y + h - 2, tw - 16, 2], fill="red", radius=1)
        cx += tw + 10


def field(page, box, label, value="", *, kind="input"):
    x, y, w, h = box
    if label:
        T(page, [x, y, w, 13], label, style="lbl")
        inp = [x, y + 16, w, h - 16]
    else:
        inp = [x, y, w, h]
    page.rect(inp, fill="paper", stroke="line", stroke_style=HAIR, radius=7)
    iy = inp[1] + inp[3] / 2 - 8
    T(page, [inp[0] + 11, iy, w - 40, 16], value or "Selecionar…",
              style="td" if value else "place")
    if kind == "select":
        T(page, [inp[0] + w - 22, iy, 16, 16], "▾", style="glyph")


def thumb(page, box, label=None, *, fill="fill"):
    """A boxless-ish image placeholder with a diagonal slash mark."""
    x, y, w, h = box
    page.rect(box, fill=fill, radius=8)
    page.line([x + 10, y + h - 10], [x + w - 10, y + 10], stroke="bar",
              stroke_style=HAIR)
    page.line([x + 10, y + 10], [x + w - 10, y + h - 10], stroke="bar",
              stroke_style=HAIR)
    if label:
        T(page, [x, y + h / 2 - 8, w, 16], label, style="glyph")


def product(page, box, name, pts, *, hot=False):
    card(page, box)
    x, y, w, h = inset(box, 10)
    thumb(page, [x, y, w, h - 44])
    T(page, [x, y + h - 40, w, 14], name, style="h3")
    T(page, [x, y + h - 22, w, 14], pts, style="pts")
    if hot:
        badge(page, [box[0] + box[2] - 52, box[1] + 8, 44, 18], "TOP", "red")


def progressbar(page, box, frac, *, fill="red", track="fill"):
    x, y, w, h = box
    page.rect(box, fill=track, radius=h / 2)
    page.rect([x, y, max(h, w * frac), h], fill=fill, radius=h / 2)


def browser(page, url, *, box=None):
    bx = box or [MX, TOP, MW, BODY_H]
    x, y, w, h = bx
    page.rect(bx, fill="paper", stroke="line", stroke_style=HAIR, radius=12)
    page.rect([x, y, w, 34], fill="canvas", radius=12)
    page.rect([x, y + 22, w, 12], fill="canvas")
    for i, c in enumerate(("faint", "faint", "faint")):
        circle(page, x + 18 + i * 16, y + 17, 4, fill=c)
    pill(page, [x + 70, y + 9, w - 150, 18], None, fill="paper", stroke="line",
         radius=9)
    T(page, [x + 82, y + 11, w - 180, 14], url, style="url")
    page.rect([x, y + 34, w, 1], fill="line")
    return [x, y + 34, w, h - 34]


# ---- Coopera site chrome: logo + experience tabs + secondary nav ---------- #
EXPERIENCES = ["Shopping", "Agronegócio", "Saúde", "Viagens"]


def site_header(page, region, *, active="Shopping",
                search="Busca por produto, marca, experiência…"):
    x, y, w, _ = region
    page.rect([x, y, w, 86], fill="paper")
    page.rect([x, y + 86, w, 1], fill="line")
    icon(page, [x + 18, y + 14, 26, 26], "co", fill="red", style="glyphW", radius=13)
    T(page, [x + 52, y + 18, 130, 18], "coopera", style="logo")
    util = ["Comprar pontos", "Juntar pontos", "Doações", "Entrar"]
    ux = x + w - 24
    circle(page, x + w - 30, y + 21, 9, fill="fill", stroke="line")  # cart
    ux -= 52
    for t in reversed(util):
        tw = 14 + len(t) * 6.6
        ux -= tw + 8
        T(page, [ux, y + 14, tw, 14], t, style="mut")
    # experience tabs + search
    tabs(page, [x + 52, y + 48, 372, 32], EXPERIENCES + ["Categorias"],
         active=EXPERIENCES.index(active) if active in EXPERIENCES else 0)
    pill(page, [x + 446, y + 50, w - 486, 28], None, fill="canvas", stroke="line",
         radius=8)
    T(page, [x + 460, y + 57, w - 520, 14], "⌕  " + search, style="place")
    return [x, y + 86, w, region[3] - 86]


# ======================================================================= #
#  concept scaffold — rail (problem→approach→outcome→AI) + deck band
# ======================================================================= #
def concept(b, *, n, key, title, axis, problem, approach, outcome, refactors,
            ai, draw):
    page = b.page(key, canvas=CANVAS, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")

    page.rect([0, 0, W, 4], fill="red")
    T(page, [32, 22, 400, 18], "Coopera · Reframe", style="band")
    T(page, [32, 44, 400, 14],
      "Refatorações distintas do programa de pontos do Sicoob", style="bandMut")
    T(page, [W - 432, 22, 400, 16], f"PROPOSTA {n:02d} / 20", style="bandR")
    T(page, [W - 432, 44, 400, 14], "Wireframe · baixa fidelidade",
      style=dict(font_family=MONO, font_size=11, color="muted", align="right"))

    page.layer("rail")
    rail = [RAIL_X, TOP, RAIL_W, BODY_H]
    page.rect(rail, fill="rail", stroke="line", stroke_style=HAIR, radius=12)
    rx, ry, rw, _ = inset(rail, 22)
    T(page, [rx, ry - 8, 120, 50], f"{n:02d}", style="num")
    T(page, [rx + 70, ry + 4, 90, 16], "/ 20",
      style=dict(font_family=MONO, font_size=12, color="faint"))
    title_w = _wrap(title, 24)
    T(page, [rx, ry + 44, rw, 46], title_w, style="title")
    cy = ry + 50 + _lines(title_w) * 24
    page.rect([rx, cy, rw, 26], fill="redSft", radius=6)
    T(page, [rx + 12, cy + 7, rw - 24, 14], "EIXO  ·  " + axis, style="axis")
    cy += 42

    def section(label, lines, gap_after=18, style="para"):
        nonlocal cy
        T(page, [rx, cy, rw, 13], label, style="lbl")
        cy += 20
        for ln in lines:
            T(page, [rx, cy, rw, 40], ln, style=style)
            cy += _lines(ln) * 17 + (4 if style == "bull" else 0)
        cy += gap_after

    section("Problema hoje", [_wrap(problem, 43)])
    section("Abordagem", ["•  " + _wrap(a, 40, hang=3) for a in approach],
            style="bull")
    section("Resultado", [_wrap(outcome, 43)])

    ai_lines = _wrap(ai, 40)
    ai_h = 44 + _lines(ai_lines) * 16
    aibox = [rx, cy + 4, rw, ai_h]
    page.rect(aibox, fill="ink", radius=10)
    page.rect([aibox[0], aibox[1], 4, aibox[3]], fill="red", radius=2)
    T(page, [rx + 16, cy + 16, rw - 28, 14], "✦  IA NA JORNADA",
      style=dict(font_family=SANS, font_size=10.5, font_weight=700, color="redSft",
                 letter_spacing=1.2))
    T(page, [rx + 16, cy + 36, rw - 28, ai_h], ai_lines,
      style=dict(font_family=SANS, font_size=12, color="paper", line_height=1.42))

    page.rect([rx, rail[1] + rail[3] - 64, rw, 1], fill="line")
    T(page, [rx, rail[1] + rail[3] - 50, rw, 13], "REFATORA", style="lbl")
    T(page, [rx, rail[1] + rail[3] - 32, rw, 14], refactors, style="foot")

    page.layer("mock")
    draw(page)
    return page


def _lines(s):
    return s.count("\n") + 1


def _wrap(s, width, hang=0):
    parts = textwrap.wrap(s, width=width)
    if not parts:
        return s
    if hang:
        pad = " " * hang
        return ("\n" + pad).join(parts) if len(parts) > 1 else parts[0]
    return "\n".join(parts)


# ======================================================================= #
#  00 — index / current-state teardown + 20-proposal map
# ======================================================================= #
def index(b):
    page = b.page("00_index", canvas=CANVAS, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")
    page.rect([0, 0, W, 4], fill="red")
    T(page, [32, 26, 1100, 30], "Coopera — 20 refatorações do programa do Sicoob",
      style=dict(font_family=SANS, font_size=26, font_weight=800, color="ink",
                 letter_spacing=-0.6))
    T(page, [32, 62, 1000, 18],
      "Cada proposta reestrutura a arquitetura de informação por um eixo "
      "diferente — não é re-skin. Wireframe de baixa fidelidade.", style="body")
    pill(page, [32, 92, 188, 24], "ANÁLISE · shopcoopera.com.br", fill="redSft",
         style="chipA")
    pill(page, [228, 92, 180, 24], "Sondado via Playwright", fill="fill",
         style="chip")
    pill(page, [416, 92, 230, 24], "Pesquisa loyalty UX 2026", fill="fill",
         style="chip")

    page.layer("asis")
    tear = [32, 130, 384, H - 130 - 40]
    card(page, tear, fill="paper")
    tx, ty, tw, _ = inset(tear, 20)
    T(page, [tx, ty, tw, 16], "COMO É HOJE", style="lbl")
    T(page, [tx, ty + 20, tw, 20], "Marketplace VTEX genérico", style="h1")
    asis = [
        ("Navegue por experiência", "Shopping/Agro/Saúde/Viagens solto"),
        ("Juntar via Super App", "compra na parceira, crédito em 45d"),
        ("Sem painel", "saldo, validade 24m e nível invisíveis"),
        ("Ponto é dinheiro?", "cashback fatura/conta/carteira escondido"),
        ("Pontos somem", "‘não aparecem / zerados’ — dor nº 1"),
        ("Resgate falha", "erro no pagamento por ~40 dias"),
    ]
    iy = ty + 48
    for k, v in asis:
        page.rect([tx, iy, 4, 28], fill="red", radius=2)
        T(page, [tx + 14, iy, tw - 14, 14], k, style="h3")
        T(page, [tx + 14, iy + 15, tw - 14, 13], _wrap(v, 44), style="mut")
        iy += 38
    page.rect([tx, iy + 4, tw, 1], fill="line")
    T(page, [tx, iy + 16, tw, 14], "PRINCÍPIOS (PESQUISA 2026)", style="lbl")
    princ = [
        "Resgate sem atrito (1 clique)",
        "Valor do ponto sempre visível",
        "Combater breakage (validade 24m)",
        "Cooperativismo como diferencial",
        "Hiper-personalização por IA",
        "Confiança: rastrear cada ponto",
    ]
    py = iy + 38
    for p in princ:
        circle(page, tx + 6, py + 6, 5, fill="red")
        T(page, [tx + 18, py, tw - 18, 14], p, style="td")
        py += 26

    page.layer("map")
    mapbox = [432, 130, W - 432 - 32, H - 130 - 40]
    colL, colR = row(mapbox, count=2, gap=18)
    for col, items in ((colL, PROPOSALS[:10]), (colR, PROPOSALS[10:])):
        rh = (col[3] - 9 * 8) / 10
        for i, (num, ttl, ax) in enumerate(items):
            cb = [col[0], col[1] + i * (rh + 8), col[2], rh]
            card(page, cb, fill="paper")
            x, y, w, _ = inset(cb, 12)
            T(page, [x, y + rh / 2 - 22, 44, 26], f"{num:02d}", style="kpiR")
            T(page, [x + 46, y + 1, w - 46, 16], ttl, style="h2")
            T(page, [x + 46, y + 20, w - 46, 13], "EIXO · " + ax, style="axis")
            if num in AI_FORWARD:
                badge(page, [cb[0] + cb[2] - 52, cb[1] + rh / 2 - 10, 40, 20],
                      "✦ IA", "red")


AI_FORWARD = {4, 6, 12, 15}  # proposals where AI is the load-bearing mechanism

PROPOSALS = [
    (1, "Cockpit do cooperado", "home centrada na conta"),
    (2, "Cashback: 3 destinos", "ponto vira dinheiro"),
    (3, "Acúmulo guiado", "transparência do ganho"),
    (4, "Extrato auditável", "confiança / rastreio"),
    (5, "Shop facetado", "layout (facetas)"),
    (6, "Busca unificada", "IA orientada à busca"),
    (7, "Checkout pontos+PIX", "fluxo / pagamento"),
    (8, "Minha cooperativa", "identidade cooperativa"),
    (9, "Produtos dos Cooperados", "curadoria / origem"),
    (10, "Navegue por experiência", "IA por vertical"),
    (11, "Coopera no Super App", "fator de forma"),
    (12, "Feed personalizado", "conteúdo algorítmico"),
    (13, "Valor do ponto", "transparência de preço"),
    (14, "Central de validade", "ciclo de vida / 24m"),
    (15, "Concierge IA", "interação conversacional"),
    (16, "Diretório de parceiras", "descoberta de lojas"),
    (17, "Doações & impacto", "propósito / ESG"),
    (18, "Status de resgate", "pós-compra / rastreio"),
    (19, "Como funciona", "compreensão / clareza"),
    (20, "Agência + app", "canal online ↔ físico"),
]


# ======================================================================= #
#  01 — cockpit do cooperado
# ======================================================================= #
def p01_cockpit(page):
    region = browser(page, "shopcoopera.com.br/  ·  minha conta")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    hero = [x, y, w, 132]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 20)
    T(page, [hx, hy, 240, 14], "SEUS PONTOS COOPERA",
      style=ts(10.5, 700, "faint", letter_spacing=1.2))
    T(page, [hx, hy + 18, 320, 40], "12.480 pts",
      style=ts(34, 800, "paper", letter_spacing=-1))
    T(page, [hx, hy + 64, 380, 14], "↘ 640 pts vencem em 38 dias · validade 24m",
      style=ts(12, 600, "redSft"))
    button(page, [hx + hw - 150, hy + 4, 150, 32], "Comprar pontos", "primary")
    button(page, [hx + hw - 150, hy + 44, 150, 32], "Virar cashback", "ghost")

    qy = y + 148
    acts = [("↑", "Juntar"), ("↓", "Usar"), ("$", "Cashback"), ("◈", "Cooperativa"),
            ("♥", "Doações")]
    for (g, t), cb in zip(acts, row([x, qy, w, 72], count=5, gap=12)):
        card(page, cb, fill="canvas")
        cx = cb[0] + cb[2] / 2
        icon(page, [cx - 16, cb[1] + 12, 32, 32], g, fill="paper", style="glyphR")
        T(page, [cb[0], cb[1] + 48, cb[2], 14], t, style="ctr")

    ry = qy + 88
    left, right = row([x, ry, w, body[3] - (ry - body[1]) - 18], gap=16,
                      weights=[1.7, 1])
    card(page, left)
    lx, ly, lw, _ = inset(left, 16)
    T(page, [lx, ly, lw - 80, 16], "Dá pra resgatar com seus pontos", style="h2")
    T(page, [lx + lw - 70, ly + 1, 70, 14], "Ver tudo ›", style="chipA")
    for cb in grid([lx, ly + 28, lw, left[3] - 60], cols=4, rows=2, gap=12):
        product(page, cb, "Produto", "8.000 pts")
    card(page, right)
    sx, sy, sw, _ = inset(right, 16)
    T(page, [sx, sy, sw, 16], "Movimentação", style="h2")
    rows = [("+ 240", "Compra Amazon", "good"), ("− 8.000", "Air Fryer", "red"),
            ("+ 90", "Centauro", "good"), ("− 2.500", "Cashback fatura", "red"),
            ("+ 1.200", "TokStok", "good")]
    ay = sy + 28
    for amt, lbl, tone in rows:
        circle(page, sx + 8, ay + 9, 4, fill=_TONE[tone][1])
        T(page, [sx + 22, ay, sw - 100, 14], lbl, style="td")
        T(page, [sx + sw - 90, ay, 90, 14], amt + " pts",
          style=dict(font_family=MONO, font_size=11, color=_TONE[tone][1],
                     align="right"))
        ay += 30


# ======================================================================= #
#  02 — cashback: 3 destinos (ponto vira dinheiro)
# ======================================================================= #
def p02_cashback(page):
    region = browser(page, "shopcoopera.com.br/cashback")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 18], "Transforme pontos em dinheiro", style="h1")
    T(page, [x, y + 24, 640, 14],
      "Diferencial do Coopera: o ponto pode virar real. Escolha o destino.",
      style="mut")

    # amount selector
    sel = [x, y + 52, w, 64]
    page.rect(sel, fill="canvas", radius=10)
    T(page, [sel[0] + 16, sel[1] + 12, 200, 13], "QUANTO RESGATAR", style="lbl")
    T(page, [sel[0] + 16, sel[1] + 28, 220, 26], "8.000 pts", style="kpi")
    T(page, [sel[0] + 240, sel[1] + 30, 200, 16], "≈ R$ 208,00", style="pts")
    progressbar(page, [sel[0] + 440, sel[1] + 30, w - 470, 10], 0.64)
    T(page, [sel[0] + 440, sel[1] + 46, 300, 13], "saldo 12.480 pts", style="tiny")

    dests = [("Desconto na fatura", "abate no cartão Sicoob", "imediato"),
             ("Crédito em conta", "cai na sua conta corrente", "1 dia útil"),
             ("Carteira digital", "saldo pra usar no app", "imediato")]
    for (ttl, sub, when), cb in zip(dests, row([x, y + 132, w, 196], count=3,
                                               gap=16)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 18)
        icon(page, [ix, iy, 40, 40], "$", fill="redSft", style="glyphR", radius=10)
        T(page, [ix + 52, iy + 4, iw - 52, 16], ttl, style="h2")
        T(page, [ix + 52, iy + 24, iw - 52, 14], sub, style="mut")
        badge(page, [ix, iy + 56, 30 + len(when) * 7, 20], when, "good")
        T(page, [ix, iy + 90, iw, 14], "VOCÊ RECEBE", style="lbl")
        T(page, [ix, iy + 106, iw, 24], "R$ 208,00", style="kpiR")
        button(page, [ix, cb[1] + cb[3] - 46, iw, 32], "Escolher", "ghost")

    # OR redeem for products
    alt = [x, y + 344, w, 84]
    page.rect(alt, fill="ink", radius=10)
    T(page, [alt[0] + 20, alt[1] + 18, 400, 16], "Ou troque por produtos no Shop",
      style=ts(14, 700, "paper"))
    T(page, [alt[0] + 20, alt[1] + 40, 480, 14],
      "250 mil itens · pague com pontos, pontos + cartão ou PIX",
      style=ts(12, 500, "faint"))
    button(page, [alt[0] + alt[2] - 180, alt[1] + 22, 160, 34], "Ir ao Shop ›",
           "primary")


# ======================================================================= #
#  03 — acúmulo guiado (parceiro → 45 dias → push)
# ======================================================================= #
def p03_earn(page):
    region = browser(page, "shopcoopera.com.br/juntar")
    body = site_header(page, region, active="Shopping")
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 18], "Junte pontos comprando nas parceiras", style="h1")
    T(page, [x, y + 24, 640, 14],
      "Torna visível o caminho: clicar → comprar → creditar em até 45 dias.",
      style="mut")

    # 3-step earn flow
    steps = [("1", "Ative a loja aqui", "clique pela Coopera p/ valer cashback"),
             ("2", "Compre no site da loja", "você é redirecionado, paga normal"),
             ("3", "Pontos em até 45 dias", "push avisa quando creditar")]
    for (n, ttl, desc), cb in zip(steps, row([x, y + 52, w, 110], count=3,
                                             gap=16)):
        card(page, cb, fill="canvas")
        ix, iy, iw, _ = inset(cb, 16)
        circle(page, ix + 16, iy + 16, 16, fill="redSft")
        T(page, [ix, iy + 6, 34, 22], n, style="kpiR")
        T(page, [ix + 46, iy + 6, iw - 46, 16], ttl, style="h2")
        T(page, [ix, iy + 44, iw, 40], _wrap(desc, 34), style="mut")

    # pending tracker + partner rates
    T(page, [x, y + 184, 300, 14], "COMPRAS AGUARDANDO CRÉDITO", style="lbl")
    track = [("Amazon · R$ 320", 0.7, "faltam 12 dias"),
             ("Centauro · R$ 180", 0.3, "faltam 31 dias")]
    ty2 = y + 206
    for nm, frac, when in track:
        T(page, [x, ty2, 300, 14], nm, style="td")
        T(page, [x + w - 140, ty2, 140, 14], when, style="mut")
        progressbar(page, [x, ty2 + 20, w, 8], frac)
        ty2 += 42

    T(page, [x, y + 300, 300, 14], "MELHORES TAXAS AGORA", style="lbl")
    parts = [("TokStok", "8 pts/R$"), ("Nike", "6 pts/R$"), ("Amazon", "4 pts/R$"),
             ("Centauro", "10 pts/R$"), ("Electrolux", "5 pts/R$"),
             ("Netshoes", "7 pts/R$")]
    for (nm, rate), cb in zip(parts, grid([x, y + 322, w, body[3] - 322 - 16],
                                          cols=6, rows=1, gap=12)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 10)
        thumb(page, [ix, iy, iw, ih - 30], nm)
        badge(page, [ix, iy + ih - 24, iw, 20], rate, "red")


# ======================================================================= #
#  04 — extrato auditável (pontos sumiram?)
# ======================================================================= #
def p04_statement(page):
    region = browser(page, "shopcoopera.com.br/extrato")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Onde estão meus pontos", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Cada compra rastreada: pendente, creditada ou em análise — e contestável.",
      style="mut")
    alert = [x, y + 52, w, 46]
    page.rect(alert, fill="redSft", radius=8)
    page.rect([alert[0], alert[1], 4, alert[3]], fill="red", radius=2)
    T(page, [alert[0] + 18, alert[1] + 14, w - 200, 16],
      "⚠  Compra Amazon de R$ 320 ainda não pontuou (dia 33 de 45). No prazo.",
      style="h3")
    button(page, [alert[0] + w - 150, alert[1] + 9, 134, 28], "Acompanhar", "ghost")

    cols = ["Data", "Origem", "Valor", "Pontos", "Status"]
    cw = [1, 2.4, 1.1, 1.1, 1.3]
    tbl = [x, y + 112, w, body[3] - 112 - 16]
    page.rect([tbl[0], tbl[1], tbl[2], 34], fill="fill", radius=8)
    for cb, h in zip(row(tbl[:2] + [tbl[2], 34], weights=cw), cols):
        T(page, [cb[0] + 12, tbl[1] + 10, cb[2] - 12, 14], h, style="th")
    rows = [("14/jun", "Compra Amazon", "R$ 320", "+ 1.280", ("Pendente", "red")),
            ("10/jun", "Compra TokStok", "R$ 540", "+ 4.320", ("Creditado", "good")),
            ("08/jun", "Cashback fatura", "—", "− 2.500", ("Concluído", "good")),
            ("05/jun", "Compra Centauro", "R$ 180", "+ 1.800", ("Em análise", "muted")),
            ("01/jun", "Resgate Air Fryer", "—", "− 8.000", ("Concluído", "good")),
            ("28/mai", "Compra Nike", "R$ 410", "+ 2.460", ("Creditado", "good"))]
    ry = tbl[1] + 34
    for i, (d, o, v, p, (st, tone)) in enumerate(rows):
        if i % 2:
            page.rect([tbl[0], ry, tbl[2], 44], fill="rowalt")
        cells = row([tbl[0], ry, tbl[2], 44], weights=cw)
        T(page, [cells[0][0] + 12, ry + 15, cells[0][2], 14], d, style="td")
        T(page, [cells[1][0] + 12, ry + 15, cells[1][2], 14], o, style="td")
        T(page, [cells[2][0] + 12, ry + 15, cells[2][2], 14], v, style="mut")
        T(page, [cells[3][0] + 12, ry + 15, cells[3][2], 14], p,
          style=dict(font_family=MONO, font_size=11,
                     color="good" if "+" in p else "redDk"))
        badge(page, [cells[4][0] + 12, ry + 12, 30 + len(st) * 7, 20], st, tone)
        page.rect([tbl[0], ry + 44 - 1, tbl[2], 1], fill="line")
        ry += 44


# ======================================================================= #
#  05 — shop facetado (marketplace)
# ======================================================================= #
def p05_shop(page):
    region = browser(page, "shopcoopera.com.br/shopping")
    body = site_header(page, region, active="Shopping")
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 500, 18], "Shop Coopera — 250 mil itens", style="h1")
    T(page, [x, y + 24, 600, 14],
      "Marketplace com facetas claras e preço em pontos + reais visível.",
      style="mut")
    facet, results = row([x, y + 52, w, h - 52], gap=16, weights=[1, 3.4])
    card(page, facet, fill="canvas")
    fx, fy, fw, _ = inset(facet, 14)
    T(page, [fx, fy, fw, 13], "CATEGORIA", style="lbl")
    cats = [("Tudo", True), ("Eletrônicos", False), ("Casa", False),
            ("Esporte", False), ("Beleza", False), ("Agro", False),
            ("Saúde", False), ("Viagens", False)]
    cyy = fy + 22
    for label, on in cats:
        circle(page, fx + 7, cyy + 7, 6, fill="red" if on else "paper",
               stroke="faint")
        T(page, [fx + 22, cyy, fw - 22, 14], label, style="td" if on else "mut")
        cyy += 26
    T(page, [fx, cyy + 8, fw, 13], "PAGAR COM", style="lbl")
    for label in ["Só pontos", "Pontos + cartão", "PIX"]:
        page.rect([fx, cyy + 30, 14, 14], fill="paper", stroke="faint",
                  stroke_style=HAIR, radius=3)
        T(page, [fx + 22, cyy + 30, fw - 22, 14], label, style="mut")
        cyy += 26
    T(page, [fx, cyy + 16, fw, 13], "✓ cabe nos meus pontos", style="chipA")

    rx, ry, rw, rh = results
    pill(page, [rx, ry, 200, 28], "Relevância · Menos pontos ▾", fill="paper",
         stroke="line", style="chip", radius=8)
    T(page, [rx + rw - 150, ry + 7, 150, 14], "12.842 produtos", style="mut")
    for cb in grid([rx, ry + 40, rw, rh - 40], cols=4, rows=3, gap=12):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 12)
        thumb(page, [ix, iy, iw, ih - 44])
        T(page, [ix, iy + ih - 40, iw, 14], "Produto", style="h3")
        T(page, [ix, iy + ih - 22, iw - 50, 14], "8.000 pts", style="pts")
        T(page, [ix + iw - 48, iy + ih - 22, 48, 14], "+R$ 0", style="tiny")


# ======================================================================= #
#  06 — busca unificada
# ======================================================================= #
def p06_search(page):
    region = browser(page, "shopcoopera.com.br/busca?q=cafeteira")
    x, y, w, h = inset(region, 0)
    page.rect([x, y, w, 64], fill="ink")
    T(page, [x + 20, y + 22, 110, 20], "co coopera", style=ts(15, 800, "paper"))
    pill(page, [x + 150, y + 16, w - 340, 32], None, fill="paper", radius=8)
    T(page, [x + 166, y + 24, w - 380, 16], "cafeteira", style="td")
    T(page, [x + w - 300, y + 24, 60, 16], "⌕", style="glyphW")
    T(page, [x + w - 170, y + 22, 150, 16], "12.480 pts",
      style=ts(12, 700, "paper"))

    x, y = x + 18, y + 80
    w = w - 36
    facet, res = row([x, y, w, region[3] - 96], gap=16, weights=[1, 3.6])
    card(page, facet, fill="canvas")
    fx, fy, fw, _ = inset(facet, 14)
    T(page, [fx, fy, fw, 13], "RESULTADOS EM", style="lbl")
    kinds = [("Produtos", "412", True), ("Agro", "18", False),
             ("Saúde", "7", False), ("Viagens", "9", False),
             ("Cooperados", "23", False)]
    ky = fy + 22
    for lbl, n, on in kinds:
        if on:
            page.rect([fx - 4, ky - 4, fw + 8, 26], fill="redSft", radius=6)
        T(page, [fx, ky, fw - 40, 16], lbl, style="navA" if on else "mut")
        T(page, [fx + fw - 36, ky, 36, 16], n, style="chipA" if on else "tiny")
        ky += 30
    T(page, [fx, ky + 10, fw, 13], "PREÇO (PONTOS)", style="lbl")
    progressbar(page, [fx, ky + 32, fw, 6], 0.5, fill="bar")
    circle(page, fx + fw * 0.5, ky + 35, 7, fill="paper", stroke="red")
    T(page, [fx, ky + 46, fw, 13], "até 12.480 (seu saldo)", style="chipA")

    rx, ry, rw, rh = res
    T(page, [rx, ry, 400, 14],
      "412 resultados · ✓ só o que cabe no seu saldo", style="mut")
    tags = ["Produto", "Cooperado", "Produto", "Produto", "Agro", "Produto",
            "Produto", "Saúde", "Produto"]
    for tg, cb in zip(tags, grid([rx, ry + 24, rw, rh - 24], cols=3, rows=3,
                                 gap=12)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 12)
        thumb(page, [ix, iy, iw, ih - 42])
        badge(page, [ix, iy + 8, 24 + len(tg) * 6, 18], tg, "muted")
        T(page, [ix, iy + ih - 38, iw, 14], "Resultado", style="h3")
        T(page, [ix, iy + ih - 20, iw, 14], "8.000 pts", style="pts")


# ======================================================================= #
#  07 — checkout pontos + cartão + PIX
# ======================================================================= #
def p07_checkout(page):
    region = browser(page, "shopcoopera.com.br/checkout")
    x, y, w, _ = inset(region, 18)
    steps = ["Sacola", "Entrega", "Pagamento", "Pronto"]
    sx = x + 8
    for i, s in enumerate(steps):
        cur = i == 2
        done = i < 2
        circle(page, sx, y + 12, 13, fill="red" if (cur or done) else "fill",
               stroke="line")
        T(page, [sx - 13, y + 5, 26, 16], "✓" if done else str(i + 1),
          style="glyphW" if (cur or done) else "glyph")
        T(page, [sx + 22, y + 4, 110, 16], s, style="h3" if cur else "mut")
        if i < 3:
            page.rect([sx + 28 + len(s) * 7, y + 11, 80, 3],
                      fill="red" if done else "fill")
        sx += 28 + len(s) * 7 + 96
    page.rect([x, y + 40, w, 1], fill="line")

    main, side = row([x, y + 58, w, region[3] - 58 - 36], gap=18, weights=[2, 1])
    T(page, [main[0], main[1], 300, 18], "Como você quer pagar?", style="h1")
    pays = [("Só pontos", "8.000 pts", True),
            ("Pontos + cartão", "5.000 pts + R$ 78", False),
            ("PIX", "R$ 208,00 · à vista", False),
            ("Cartão Sicoob", "em até 10×", False)]
    iy = main[1] + 34
    for nm, sub, on in pays:
        lane = [main[0], iy, main[2], 60]
        card(page, lane, fill="redSft" if on else "paper",
             stroke="red" if on else "line")
        circle(page, lane[0] + 22, iy + 30, 9, fill="red" if on else "paper",
               stroke="faint")
        if on:
            circle(page, lane[0] + 22, iy + 30, 4, fill="paper")
        T(page, [lane[0] + 46, iy + 12, lane[2] - 200, 16], nm, style="h2")
        T(page, [lane[0] + 46, iy + 33, lane[2] - 200, 14], sub, style="mut")
        if nm == "PIX":
            badge(page, [lane[0] + lane[2] - 120, iy + 20, 100, 22],
                  "5% off à vista", "good")
        iy += 70

    card(page, side, fill="canvas")
    sxx, syy, sw, _ = inset(side, 18)
    T(page, [sxx, syy, sw, 16], "Resumo", style="h2")
    rows = [("Air Fryer 12L", "8.000 pts"), ("Frete", "grátis"),
            ("Seus pontos", "12.480 pts")]
    ry2 = syy + 30
    for k, v in rows:
        T(page, [sxx, ry2, sw - 120, 14], k, style="body")
        T(page, [sxx + sw - 120, ry2, 120, 14], v, style="right")
        ry2 += 26
    page.rect([sxx, ry2 + 4, sw, 1], fill="line")
    T(page, [sxx, ry2 + 16, sw, 14], "TOTAL", style="lbl")
    T(page, [sxx, ry2 + 32, sw, 22], "8.000 pts", style="kpiR")
    button(page, [sxx, ry2 + 68, sw, 42], "Finalizar resgate", "primary")
    T(page, [sxx, ry2 + 118, sw, 13], "🔒 pontos só debitados ao confirmar",
      style="tiny")


# ======================================================================= #
#  08 — minha cooperativa (identidade cooperativa)
# ======================================================================= #
def p08_coop(page):
    region = browser(page, "shopcoopera.com.br/minha-cooperativa")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    hero = [x, y, w, 120]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 20)
    T(page, [hx, hy, 240, 14], "VOCÊ É COOPERADO DA",
      style=ts(10.5, 700, "faint", letter_spacing=1.2))
    T(page, [hx, hy + 18, 420, 26], "Sicoob Credicitrus", style=ts(22, 800, "paper"))
    T(page, [hx, hy + 52, 480, 14],
      "Agência 4021 · cooperado desde 2019 · você é dono, não cliente.",
      style=ts(12, 500, "faint"))
    badge(page, [hx + hw - 120, hy, 120, 24], "PARTICIPE", "red")

    # the cooperative difference, in 3 cards
    diff = [("Sobras a receber", "R$ 1.240", "resultado distribuído a você"),
            ("Impacto local", "32 projetos", "na sua comunidade em 2026"),
            ("Sua voz", "Assembleia", "vote nas decisões da cooperativa")]
    for (ttl, big, sub), cb in zip(diff, row([x, y + 136, w, 130], count=3,
                                             gap=16)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 16)
        T(page, [ix, iy, iw, 13], ttl.upper(), style="lbl")
        T(page, [ix, iy + 18, iw, 26], big, style="kpiR")
        T(page, [ix, iy + 52, iw, 40], _wrap(sub, 32), style="mut")
        T(page, [ix, iy + 92, iw, 14], "Saiba mais ›", style="chipA")

    # points that strengthen the cooperative
    coop = [x, y + 282, w, body[3] - 282 - 18]
    card(page, coop, fill="canvas")
    cx, cyy, cw, _ = inset(coop, 18)
    T(page, [cx, cyy, cw, 16], "Seus pontos fortalecem o cooperativismo",
      style="h2")
    bullets = ["Comprar de outros cooperados gira a economia local",
               "Doar pontos apoia projetos votados em assembleia",
               "Quanto mais usa o Coopera, maiores as sobras do sistema"]
    by = cyy + 30
    for btxt in bullets:
        circle(page, cx + 6, by + 7, 5, fill="red")
        T(page, [cx + 18, by, cw - 18, 14], btxt, style="td")
        by += 26


# ======================================================================= #
#  09 — produtos dos cooperados (curadoria de origem)
# ======================================================================= #
def p09_cooperados(page):
    region = browser(page, "shopcoopera.com.br/produtos-cooperados")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 600, 18], "Produtos dos Cooperados", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Vitrine só de quem é cooperado: café, agro, artesanato — origem em destaque.",
      style="mut")
    # origin filter chips
    chips = ["Todos", "Café", "Agro", "Artesanato", "Alimentos", "Vinhos"]
    gx = x
    for i, c in enumerate(chips):
        gw = 28 + len(c) * 8
        pill(page, [gx, y + 52, gw, 30], c, fill="red" if i == 0 else "fill",
             style="btn" if i == 0 else "chip", radius=15)
        gx += gw + 10

    for cb in grid([x, y + 96, w, h - 96], cols=4, rows=2, gap=16):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 12)
        thumb(page, [ix, iy, iw, ih - 70])
        badge(page, [ix, iy + 8, 92, 20], "◈ Cooperado", "red")
        T(page, [ix, iy + ih - 64, iw, 16], "Produto do campo", style="h3")
        T(page, [ix, iy + ih - 44, iw, 13], "Coop. Credicitrus · SP", style="mut")
        T(page, [ix, iy + ih - 24, iw, 14], "1.200 pts · R$ 31", style="pts")


# ======================================================================= #
#  10 — navegue por experiência (verticais)
# ======================================================================= #
def p10_experiences(page):
    region = browser(page, "shopcoopera.com.br/")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 600, 18], "Navegue por experiência", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Quatro mundos como portas reais, não ícones soltos — cada um com sua busca.",
      style="mut")
    exps = [("Shopping", "▦", "250 mil produtos pra resgatar"),
            ("Agronegócio", "✦", "insumos, máquinas e crédito rural"),
            ("Saúde", "✚", "consultas, exames e farmácia"),
            ("Viagens", "✈", "passagens, hotéis e pacotes")]
    cells = grid([x, y + 56, w, h - 56], cols=2, rows=2, gap=16)
    for (ttl, g, sub), cb in zip(exps, cells):
        page.rect(cb, fill="ink", radius=12)
        ix, iy, iw, ih = inset(cb, 22)
        icon(page, [ix, iy, 44, 44], g, fill="red", style="glyphW", radius=12)
        T(page, [ix + 58, iy + 4, iw - 58, 20], ttl, style=ts(20, 800, "paper"))
        T(page, [ix + 58, iy + 30, iw - 58, 14], sub, style=ts(12, 500, "faint"))
        # mini search inside the world
        sb = [ix, iy + ih - 44, iw, 34]
        page.rect(sb, fill="paper", radius=8)
        T(page, [sb[0] + 12, sb[1] + 10, iw - 100, 14],
          "⌕  Buscar em " + ttl, style="place")
        button(page, [sb[0] + iw - 84, sb[1] + 4, 76, 26], "Entrar", "primary")


# ======================================================================= #
#  11 — Coopera no Super App (mobile)
# ======================================================================= #
def p11_mobile(page):
    phones = row([MX, TOP, MW, BODY_H], count=3, gap=28, pad=[10, 30])
    titles = ["Sicoob Super App", "Aba Coopera", "Usar pontos"]
    for ph, ttl in zip(phones, titles):
        px, py, pw, phh = ph
        phh = min(phh, 760)
        page.rect([px, py, pw, phh], fill="ink", radius=26)
        sc = inset([px, py, pw, phh], [12, 10])
        page.rect(sc, fill="paper", radius=16)
        sx, sy, sw, sh = sc
        T(page, [sx + 14, sy + 10, sw - 28, 12], "9:41", style="tiny")
        T(page, [sx + sw - 70, sy + 10, 56, 12], "●●●  ▮",
          style=dict(font_family=SANS, font_size=9, color="muted", align="right"))
        T(page, [sx + 14, sy + 28, 140, 18], "Sicoob", style="h2")
        T(page, [sx + sw - 96, sy + 30, 84, 14], "12.480 pts", style="pts")
        T(page, [sx + 14, sy + 56, sw, 12], ttl.upper(), style="lbl")
        if "Super App" in ttl:
            for i in range(3):
                yy = sy + 80 + i * 70
                card(page, [sx + 14, yy, sw - 28, 60], fill="canvas")
                icon(page, [sx + 24, yy + 14, 32, 32],
                     ["▤", "$", "co"][i], fill="paper",
                     style="glyphR" if i == 2 else "glyph")
                T(page, [sx + 66, yy + 14, sw - 90, 14],
                  ["Conta · Pix · Cartão", "Investir", "Coopera · pontos"][i],
                  style="h3")
                T(page, [sx + 66, yy + 34, sw - 90, 12],
                  ["seu dia a dia", "renda", "ganhe e troque"][i], style="mut")
        elif "Aba Coopera" in ttl:
            page.rect([sx + 14, sy + 78, sw - 28, 64], fill="ink", radius=12)
            T(page, [sx + 26, sy + 90, 120, 12], "PONTOS COOPERA",
              style=ts(9, 700, "faint", letter_spacing=1))
            T(page, [sx + 26, sy + 104, 160, 22], "12.480",
              style=ts(20, 800, "paper"))
            for cb in grid([sx + 14, sy + 156, sw - 28, 120], cols=2, rows=2,
                           gap=10):
                card(page, cb, fill="canvas")
                T(page, [cb[0], cb[1] + cb[3] / 2 - 8, cb[2], 16],
                  "▢", style="glyphR")
        else:
            page.rect([sx + 30, sy + 96, sw - 60, sw - 90], fill="canvas",
                      stroke="red", stroke_style=DASHR, radius=12)
            T(page, [sx, sy + 96 + (sw - 90) / 2 - 8, sw, 16],
              "trocar por R$ ou produto", style="glyph")
            for cb in row([sx + 14, sy + 120 + (sw - 90), sw - 28, 50], count=2,
                          gap=10):
                card(page, cb, fill="canvas")
        bar_y = sy + sh - 52
        page.rect([sx, bar_y, sw, 52], fill="paper")
        page.rect([sx, bar_y, sw, 1], fill="line")
        tabsl = [("⌂", "Início"), ("$", "Pix"), ("▤", "Cartões"),
                 ("co", "Coopera"), ("≡", "Mais")]
        for i, (g, lab) in enumerate(tabsl):
            cx = sx + sw * (i + 0.5) / 5
            on = (("Aba" in ttl and i == 3) or ("Usar" in ttl and i == 3)
                  or ("Super" in ttl and i == 0))
            T(page, [cx - 16, bar_y + 8, 32, 16], g,
              style="glyphR" if on else "glyph")
            T(page, [cx - 24, bar_y + 28, 48, 12], lab,
              style=ts(9, 700, "red" if on else "muted", align="center"))


# ======================================================================= #
#  12 — feed personalizado
# ======================================================================= #
def p12_feed(page):
    region = browser(page, "shopcoopera.com.br/  ·  pra você")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 400, 18], "Pra você, hoje", style="h1")
    T(page, [x, y + 24, 600, 14],
      "Ofertas, mais-vendidos e cooperados fixos → feed algorítmico de intenções.",
      style="mut")
    feed = [
        ("EXPIRA", "640 pts vencem em 38 dias", "Vire cashback agora", "red"),
        ("PERTO", "Faltam 1k p/ a Air Fryer", "Você olhou 2×", "muted"),
        ("AGRO", "Insumos com 10 pts/R$", "Combina com seu perfil", "red"),
        ("COOPERADO", "Café da Credicitrus", "Produtor perto de você", "muted"),
        ("CASHBACK", "Centauro 10 pts/R$", "Dobro neste fim de semana", "muted"),
        ("SAÚDE", "Consulta por pontos", "Rede credenciada", "muted"),
        ("DOAÇÃO", "Projeto local a 80%", "Ajude a fechar a meta", "red"),
        ("VIAGEM", "Gramado por 9k pts", "Alta no inverno", "muted"),
    ]
    cells = grid([x, y + 52, w, h - 52], cols=4, rows=2, gap=14)
    for (tag, ttl, sub, tone), cb in zip(feed, cells):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 14)
        badge(page, [ix, iy, 30 + len(tag) * 7, 18], tag, tone)
        thumb(page, [ix, iy + 26, iw, ih - 96])
        T(page, [ix, iy + ih - 64, iw, 16], _wrap(ttl, 22), style="h2")
        T(page, [ix, iy + ih - 26, iw, 14], sub, style="mut")
    T(page, [x, y + h - 6, w, 14],
      "↻ reordena por comportamento · cada card é uma intenção distinta",
      style="tiny")


# ======================================================================= #
#  13 — valor do ponto
# ======================================================================= #
def p13_value(page):
    region = browser(page, "shopcoopera.com.br/valor-dos-pontos")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    hero = [x, y, w, 96]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 20)
    T(page, [hx, hy, 360, 14], "SEUS 12.480 PTS VALEM, NO MELHOR USO",
      style=ts(10.5, 700, "faint", letter_spacing=1.2))
    T(page, [hx, hy + 18, 360, 34], "≈ R$ 374",
      style=ts(30, 800, "paper", letter_spacing=-1))
    T(page, [hx + hw - 240, hy + 6, 240, 14],
      "1 ponto rende mais ou menos\nconforme onde você troca.",
      style=ts(12, 500, "faint", line_height=1.4, align="right"))

    left, right = row([x, y + 112, w, body[3] - 112 - 18], gap=16, weights=[1.2, 1])
    card(page, left)
    lx, ly, lw, _ = inset(left, 16)
    T(page, [lx, ly, lw, 16], "Valor por ponto, por tipo de troca", style="h2")
    methods = [("Viagens", 3.4, 1.0, "melhor"), ("Produtos do Shop", 2.6, 0.76, ""),
               ("Produtos Cooperados", 2.6, 0.76, ""),
               ("Cashback em conta", 2.6, 0.76, ""),
               ("Desconto na fatura", 2.5, 0.73, "")]
    my = ly + 30
    for name, cents, frac, tag in methods:
        T(page, [lx, my, 220, 14], name, style="td")
        if tag:
            badge(page, [lx + 168, my - 1, 56, 18], tag, "good")
        T(page, [lx + lw - 70, my, 70, 14], f"{cents:.1f}¢", style="right")
        progressbar(page, [lx, my + 20, lw, 8], frac,
                    fill="good" if tag == "melhor" else "red")
        my += 44

    card(page, right)
    rx, ry, rw, _ = inset(right, 16)
    T(page, [rx, ry, rw, 16], "Melhores trocas pelo saldo", style="h2")
    best = [("Passagem SP→Gramado", "3,4¢/pt"), ("Diária pousada", "3,1¢/pt"),
            ("Café Cooperado", "2,8¢/pt"), ("Air Fryer 12L", "2,6¢/pt")]
    for (nm, v), cb in zip(best, [[rx, ry + 30 + i * 64, rw, 56] for i in range(4)]):
        card(page, cb, fill="canvas")
        thumb(page, [cb[0] + 10, cb[1] + 10, 56, 36])
        T(page, [cb[0] + 78, cb[1] + 12, cb[2] - 160, 16], nm, style="h3")
        badge(page, [cb[0] + cb[2] - 78, cb[1] + 18, 64, 20], v, "good")


# ======================================================================= #
#  14 — central de validade (24 meses)
# ======================================================================= #
def p14_expiry(page):
    region = browser(page, "shopcoopera.com.br/a-vencer")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Seus pontos a vencer", style="h1")
    T(page, [x, y + 24, 620, 14],
      "Validade de 24 meses não pode ser surpresa. Aqui você nunca perde.",
      style="mut")
    buckets = [("38 dias", "640 pts", 0.9, "red"),
               ("4 meses", "1.800 pts", 0.5, "red"),
               ("12 meses", "4.200 pts", 0.25, "muted"),
               ("> 18 meses", "5.840 pts", 0.05, "good")]
    for (when, amt, urg, tone), cb in zip(buckets,
                                          row([x, y + 52, w, 96], count=4, gap=14)):
        card(page, cb, fill="canvas")
        ix, iy, iw, _ = inset(cb, 14)
        circle(page, ix + 7, iy + 8, 6, fill=_TONE.get(tone, _TONE["muted"])[1])
        T(page, [ix + 20, iy, iw - 20, 14], "vence em " + when, style="mut")
        T(page, [ix, iy + 22, iw, 22], amt, style="kpiR" if tone == "red" else "kpi")
        progressbar(page, [ix, iy + 52, iw, 6], urg,
                    fill="red" if tone == "red" else "bar")
    T(page, [x, y + 168, 400, 14],
      "QUEIME OS 640 PTS QUE VENCEM EM 38 DIAS", style="lbl")
    micro = [("Cashback na conta", "640 pts"), ("Cupom farmácia", "300 pts"),
             ("Doar p/ projeto local", "200 pts"), ("Crédito celular", "500 pts"),
             ("Café Cooperado", "1.200 pts"), ("Desconto na fatura", "qualquer")]
    for (nm, pts), cb in zip(micro, grid([x, y + 190, w, body[3] - 190 - 16],
                                         cols=3, rows=2, gap=14)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 14)
        icon(page, [ix, iy, 36, 36], "↺", fill="redSft", style="glyphR")
        T(page, [ix + 48, iy + 2, iw - 48, 16], nm, style="h3")
        T(page, [ix + 48, iy + 22, iw - 48, 14], pts, style="pts")
        button(page, [ix, iy + ih - 30, iw, 28], "Trocar 1-clique", "primary")


# ======================================================================= #
#  15 — concierge IA
# ======================================================================= #
def p15_concierge(page):
    region = browser(page, "shopcoopera.com.br/assistente")
    x, y, w, h = inset(region, 0)
    page.rect([x, y, w, 52], fill="ink")
    icon(page, [x + 16, y + 12, 28, 28], "✦", fill="red", style="glyphW", radius=14)
    T(page, [x + 54, y + 16, 320, 20], "Assistente Coopera", style=ts(15, 800, "paper"))
    T(page, [x + w - 170, y + 18, 150, 16], "Saldo 12.480 pts",
      style=ts(12, 700, "paper"))

    chat, side = row([x, y + 52, w, region[3] - 52], gap=0, weights=[2.5, 1])
    cx, cy, cw, ch = inset(chat, 20)
    ub = [cx + cw - 380, cy, 380, 44]
    page.rect(ub, fill="redSft", radius=12)
    T(page, [ub[0] + 16, ub[1] + 14, ub[2] - 32, 16],
      "tenho 640 pts vencendo — qual o melhor uso?", style="td")
    ay = cy + 60
    page.rect([cx, ay, cw - 80, 48], fill="fill", radius=12)
    T(page, [cx + 16, ay + 9, cw - 120, 32],
      "Pelo seu perfil, cashback na conta rende mais. Posso também\nsugerir 3 "
      "produtos. O que prefere?", style="body")
    ay += 64
    picks = [("Cashback R$ 16,60 na conta", "640 pts"),
             ("Cupom farmácia", "300 pts"),
             ("Doar a projeto local", "200 pts")]
    for nm, pts in picks:
        chip = [cx, ay, cw - 80, 56]
        card(page, chip)
        icon(page, [chip[0] + 12, chip[1] + 12, 36, 32], "$", fill="redSft",
             style="glyphR")
        T(page, [chip[0] + 60, chip[1] + 12, 220, 16], nm, style="h3")
        T(page, [chip[0] + 60, chip[1] + 32, 160, 14], pts, style="pts")
        button(page, [chip[0] + chip[2] - 110, chip[1] + 14, 94, 28],
               "Fazer", "ghost")
        ay += 66
    comp = [cx, chat[1] + chat[3] - 70, cw, 44]
    page.rect(comp, fill="paper", stroke="line", stroke_style=HAIR, radius=22)
    T(page, [comp[0] + 18, comp[1] + 14, cw - 80, 16],
      "Pergunte sobre seus pontos, lojas, validade…", style="place")
    circle(page, comp[0] + cw - 24, comp[1] + 22, 16, fill="red")
    T(page, [comp[0] + cw - 40, comp[1] + 13, 32, 18], "↑", style="glyphW")
    page.rect(side, fill="canvas")
    sx, sy, sw, _ = inset(side, 16)
    T(page, [sx, sy, sw, 14], "ATALHOS", style="lbl")
    for i, q in enumerate(["O que vence primeiro?", "Melhor uso do saldo",
                           "Onde junto mais ponto?", "Status do meu resgate",
                           "Minhas sobras"]):
        pill(page, [sx, sy + 26 + i * 40, sw, 32], q, fill="paper", stroke="line",
             style="chip", radius=8)


# ======================================================================= #
#  16 — diretório de lojas parceiras
# ======================================================================= #
def p16_directory(page):
    region = browser(page, "shopcoopera.com.br/lojas-parceiras")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 500, 18], "Lojas parceiras", style="h1")
    T(page, [x, y + 24, 620, 14],
      "Onde juntar pontos: buscável e filtrável por taxa, não uma lista solta.",
      style="mut")
    facet, results = row([x, y + 52, w, h - 52], gap=16, weights=[1, 3.4])
    card(page, facet, fill="canvas")
    fx, fy, fw, _ = inset(facet, 14)
    T(page, [fx, fy, fw, 13], "CATEGORIA", style="lbl")
    cats = [("Tudo", True), ("Eletrônicos", False), ("Moda", False),
            ("Esporte", False), ("Casa", False), ("Beleza", False),
            ("Agro", False), ("Saúde", False)]
    cyy = fy + 22
    for label, on in cats:
        circle(page, fx + 7, cyy + 7, 6, fill="red" if on else "paper",
               stroke="faint")
        T(page, [fx + 22, cyy, fw - 22, 14], label, style="td" if on else "mut")
        cyy += 26
    T(page, [fx, cyy + 8, fw, 13], "ORDENAR · maior taxa", style="chipA")

    rx, ry, rw, rh = results
    pill(page, [rx, ry, 200, 28], "A–Z  ·  Mais pontos/R$ ▾", fill="paper",
         stroke="line", style="chip", radius=8)
    T(page, [rx + rw - 130, ry + 7, 130, 14], "96 parceiras", style="mut")
    names = ["TokStok", "Amazon", "Nike", "Centauro", "Beleza na Web",
             "Electrolux", "Netshoes", "Magalu", "Renner", "Natura",
             "Fast Shop", "Adidas"]
    for nm, cb in zip(names, grid([rx, ry + 40, rw, rh - 40], cols=4, rows=3,
                                  gap=12)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 12)
        thumb(page, [ix, iy, iw, ih - 30], nm)
        T(page, [ix, iy + ih - 24, iw - 50, 14], nm, style="h3")
        T(page, [ix + iw - 48, iy + ih - 24, 48, 14], "8 pt", style="chipA")


# ======================================================================= #
#  17 — doações & impacto (ESG / cooperativismo)
# ======================================================================= #
def p17_donate(page):
    region = browser(page, "shopcoopera.com.br/doacoes")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Doe pontos, gere impacto", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Cooperativismo é comunidade: pontos a vencer viram projeto local votado.",
      style="mut")
    causes = [("Educação no campo", "Escolas rurais", 0.72, "Coop. Credicitrus"),
              ("Saúde da comunidade", "Postos e exames", 0.54, "Coop. Cocred"),
              ("Reflorestar", "Mata ciliar", 0.38, "Coop. Coopjus"),
              ("Esporte jovem", "Escolinhas locais", 0.61, "Coop. Credicitrus")]
    for (ttl, sub, frac, who), cb in zip(causes,
                                         row([x, y + 56, w, 200], count=2,
                                             gap=16)[:2] +
                                         row([x, y + 268, w, 200], count=2,
                                             gap=16)[:2]):
        cb = [cb[0], cb[1], cb[2], 188]
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 16)
        thumb(page, [ix, iy, 110, 110], "foto")
        T(page, [ix + 126, iy, iw - 126, 16], ttl, style="h2")
        T(page, [ix + 126, iy + 22, iw - 126, 14], sub + " · " + who, style="mut")
        progressbar(page, [ix + 126, iy + 48, iw - 126, 10], frac, fill="good")
        T(page, [ix + 126, iy + 64, iw - 126, 14],
          f"{int(frac*100)}% da meta da assembleia", style="chipA")
        for j, amt in enumerate(["200 pts", "1.000 pts", "5.000 pts"]):
            pill(page, [ix + 126 + j * 92, iy + 88, 84, 28], amt, fill="fill",
                 style="chip", radius=8)
        button(page, [ix + 126, iy + 124, iw - 126, 30], "Doar agora", "primary")


# ======================================================================= #
#  18 — status de resgate (pós-compra / rastreio)
# ======================================================================= #
def p18_status(page):
    region = browser(page, "shopcoopera.com.br/meus-resgates/884213")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Status do resgate #884213", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Fim do ‘deu erro e sumiu’: cada resgate com etapa, prazo e protocolo.",
      style="mut")

    main, side = row([x, y + 56, w, body[3] - 56 - 18], gap=18, weights=[2, 1])
    card(page, main)
    mx, my, mw, _ = inset(main, 20)
    T(page, [mx, my, mw, 16], "Air Fryer Mondial 12L · 8.000 pts", style="h2")
    T(page, [mx, my + 22, mw, 14], "Resgatado em 14/jun · protocolo CPR-884213",
      style="mut")
    timeline = [("Pedido confirmado", "14/jun 10:02", True),
                ("Pontos debitados", "14/jun 10:02", True),
                ("Separado pelo parceiro", "15/jun 09:20", True),
                ("Em transporte", "previsto 18/jun", False),
                ("Entregue", "previsto 21/jun", False)]
    ty = my + 56
    for i, (lbl, when, done) in enumerate(timeline):
        circle(page, mx + 9, ty + 8, 7, fill="red" if done else "paper",
               stroke="faint")
        if done:
            circle(page, mx + 9, ty + 8, 3, fill="paper")
        if i < len(timeline) - 1:
            page.rect([mx + 8, ty + 16, 2, 34], fill="line")
        T(page, [mx + 30, ty, mw - 160, 16], lbl,
          style="h3" if done else "mut")
        T(page, [mx + mw - 150, ty, 150, 14], when, style="mut")
        ty += 50

    card(page, side, fill="canvas")
    sx, sy, sw, _ = inset(side, 18)
    T(page, [sx, sy, sw, 16], "Precisa de ajuda?", style="h2")
    for i, opt in enumerate(["Acompanhar transporte", "Falar no chat 24h",
                             "Cancelar e estornar pontos"]):
        b = [sx, sy + 32 + i * 50, sw, 40]
        button(page, b, opt, "ghost" if i else "primary")
    T(page, [sx, sy + 200, sw, 14], "GARANTIA COOPERA", style="lbl")
    T(page, [sx, sy + 220, sw, 40],
      _wrap("Falhou? pontos estornados na hora, automaticamente.", 30),
      style="body")


# ======================================================================= #
#  19 — como funciona (explainer)
# ======================================================================= #
def p19_explainer(page):
    region = browser(page, "shopcoopera.com.br/como-funciona")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 20], "Como o Coopera funciona", style="h1")
    T(page, [x, y + 26, 660, 14],
      "Sem jargão: você junta pontos e troca por produtos ou dinheiro.",
      style="mut")
    steps = [("1", "Junte", "Comprando nas parceiras pelo app — cashback de 3 a "
              "8 pontos por real."),
             ("2", "Acumule", "Pontos caem em até 45 dias e valem por 24 meses. "
              "A gente avisa antes de vencer."),
             ("3", "Use", "Troque por 250 mil produtos, viagens, ou vire "
              "dinheiro na sua conta.")]
    for (n, ttl, desc), cb in zip(steps, row([x, y + 56, w, 130], count=3,
                                             gap=16)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 18)
        circle(page, ix + 18, iy + 18, 18, fill="redSft")
        T(page, [ix, iy + 8, 36, 22], n, style="kpiR")
        T(page, [ix + 48, iy + 6, iw - 48, 18], ttl, style="h1")
        T(page, [ix, iy + 44, iw, 60], _wrap(desc, 40), style="body")

    earn, redeem = row([x, y + 202, w, body[3] - 202 - 60], gap=16, weights=[1, 1])
    for col, head, glyph, ways in [
            (earn, "Formas de GANHAR", "↑",
             ["Comprar nas 96 lojas parceiras", "Cartão de crédito Sicoob",
              "Comprar pontos", "Campanhas com pontos em dobro"]),
            (redeem, "Formas de USAR", "↓",
             ["Produtos e viagens no Shop", "Produtos dos Cooperados",
              "Cashback: conta, fatura ou carteira", "Doar a projetos locais"])]:
        card(page, col, fill="canvas")
        ix, iy, iw, _ = inset(col, 18)
        icon(page, [ix, iy, 34, 34], glyph, fill="redSft", style="glyphR")
        T(page, [ix + 46, iy + 7, iw - 46, 18], head, style="h2")
        wy = iy + 50
        for wtext in ways:
            circle(page, ix + 7, wy + 7, 5, fill="red")
            T(page, [ix + 22, wy, iw - 22, 14], wtext, style="td")
            wy += 34

    fy = body[1] + body[3] - 44
    T(page, [x, fy - 18, 200, 14], "DÚVIDAS FREQUENTES", style="lbl")
    fx = x
    for q in ["Em quanto tempo pontua?", "Quanto vale 1 ponto?",
              "Posso virar dinheiro?", "Meus pontos vencem?"]:
        qw = 24 + len(q) * 7
        pill(page, [fx, fy, qw, 28], q, fill="paper", stroke="line", style="chip",
             radius=8)
        fx += qw + 10


# ======================================================================= #
#  20 — agência + app (omnichannel cooperativo)
# ======================================================================= #
def p20_omni(page):
    region = browser(page, "shopcoopera.com.br/na-agencia")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 500, 18], "Coopera na sua agência Sicoob", style="h1")
    T(page, [x, y + 24, 660, 14],
      "O cooperativo é local: junte e use pontos no PA físico e com o gerente.",
      style="mut")
    passcol, near = row([x, y + 56, w, h - 56], gap=16, weights=[1, 1.4])
    page.rect(passcol, fill="ink", radius=14)
    pxx, pyy, pw, _ = inset(passcol, 22)
    T(page, [pxx, pyy, pw, 14], "CARTEIRA COOPERA",
      style=ts(10.5, 700, "faint", letter_spacing=1.4))
    T(page, [pxx, pyy + 20, pw, 18], "Pedro A. · Credicitrus",
      style=ts(16, 800, "paper"))
    T(page, [pxx, pyy + 48, pw, 24], "12.480 pts", style=ts(22, 800, "paper"))
    qr = [pxx, pyy + 92, 120, 120]
    page.rect(qr, fill="paper", radius=10)
    for gx in range(5):
        for gy in range(5):
            if (gx + gy) % 2 == 0:
                page.rect([qr[0] + 14 + gx * 18, qr[1] + 14 + gy * 18, 16, 16],
                          fill="ink", radius=2)
    T(page, [pxx + 140, pyy + 110, pw - 140, 14],
      "Mostre no caixa do PA\npara juntar ou usar\npontos na hora.",
      style=ts(12, 500, "faint", line_height=1.5))
    pill(page, [pxx, passcol[1] + passcol[3] - 56, pw, 34],
         "＋ Adicionar à Apple / Google Wallet", fill="ink", stroke="faint",
         style="btn", radius=8)

    card(page, near, fill="canvas")
    nx, ny, nw, _ = inset(near, 16)
    T(page, [nx, ny, nw - 90, 16], "Postos de atendimento perto", style="h2")
    T(page, [nx + nw - 86, ny + 1, 86, 14], "◉ Mapa", style="chipA")
    shops = [("PA Centro", "R. XV de Novembro, 200", "300 m", "atende Coopera"),
             ("Agência Sicoob 4021", "Av. Brasil, 1500", "1,2 km", "gerente"),
             ("PA Shopping", "Shopping Cidade", "2,0 km", "totem Coopera"),
             ("Coop. parceira", "R. do Comércio, 80", "2,8 km", "saque pontos")]
    for (nm, addr, dist, tag), cb in zip(shops,
                                         [[nx, ny + 32 + i * 62, nw, 54]
                                          for i in range(4)]):
        card(page, cb)
        icon(page, [cb[0] + 12, cb[1] + 11, 32, 32], "◈", fill="paper")
        T(page, [cb[0] + 56, cb[1] + 10, cb[2] - 210, 16], nm, style="h3")
        T(page, [cb[0] + 56, cb[1] + 30, cb[2] - 210, 14], addr, style="mut")
        T(page, [cb[0] + cb[2] - 150, cb[1] + 10, 60, 14], dist, style="td")
        badge(page, [cb[0] + cb[2] - 88, cb[1] + 16, 74, 20], tag, "good")


# ======================================================================= #
#  capstone — how AI helps across the whole cooperado journey
# ======================================================================= #
def ai_journey(b):
    page = b.page("21_ai_journey", canvas=CANVAS,
                  coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")
    page.rect([0, 0, W, 4], fill="red")
    T(page, [32, 26, 1100, 30], "IA na jornada — onde a inteligência atua",
      style=dict(font_family=SANS, font_size=26, font_weight=800, color="ink",
                 letter_spacing=-0.6))
    T(page, [32, 62, 1100, 18],
      "As 20 propostas, lidas pela ótica da IA: cada etapa da jornada do cooperado "
      "ganha uma capacidade. Os números são as propostas que a usam.", style="body")

    stages = [
        ("DESCOBRIR", "encontrar o que importa", "#", [
            ("Recomendação", "feed ordena por propensão e urgência", "12"),
            ("Busca semântica", "entende intenção, não palavra-chave", "06"),
            ("Curadoria", "experiência/vertical certa pra você", "10")]),
        ("JUNTAR", "ganhar sem fricção", "↑", [
            ("Reconciliação", "detecta compra que não pontuou", "04"),
            ("Previsão de crédito", "estima quando os 45 dias caem", "03"),
            ("Melhor taxa", "qual parceira rende mais agora", "16")]),
        ("DECIDIR", "ponto ou dinheiro?", "$", [
            ("Otimização", "destino de cashback que mais rende", "02"),
            ("Preço dinâmico", "valor-por-ponto em tempo real", "13"),
            ("Agente / LLM", "assistente entende e executa", "15")]),
        ("USAR", "resgatar sem erro", "↓", [
            ("Antifraude", "checa o resgate antes de debitar", "07"),
            ("Rastreio", "prevê atraso e estorna sozinho", "18"),
            ("Curadoria", "o micro-resgate certo pra vencer", "14")]),
        ("PERTENCER", "cooperar e ficar", "◈", [
            ("Propensão / churn", "prevê breakage e evasão", "14"),
            ("Match de causa", "projeto local que combina", "17"),
            ("Personalização", "minha cooperativa em destaque", "08")]),
    ]
    lanes = row([32, 130, W - 64, 560], count=5, gap=16)
    for (head, sub, glyph, caps), lane in zip(stages, lanes):
        lx, ly, lw, lh = lane
        card(page, lane, fill="paper")
        page.rect([lx, ly, lw, 64], fill="ink", radius=10)
        page.rect([lx, ly + 40, lw, 24], fill="ink")
        icon(page, [lx + 14, ly + 16, 30, 30], glyph, fill="red", style="glyphW",
             radius=8)
        T(page, [lx + 52, ly + 16, lw - 60, 16], head,
          style=ts(13, 800, "paper", letter_spacing=0.5))
        T(page, [lx + 52, ly + 36, lw - 60, 14], sub, style=ts(11, 500, "faint"))
        cyy = ly + 80
        for cap, desc, props in caps:
            ix = lx + 14
            iw = lw - 28
            T(page, [ix, cyy, iw - 44, 14], cap, style="h3")
            badge(page, [ix + iw - 40, cyy - 2, 40, 20], props, "red")
            T(page, [ix, cyy + 18, iw, 28], _wrap(desc, 26), style="mut")
            page.rect([ix, cyy + 56, iw, 1], fill="line")
            cyy += 68

    page.layer("flow")
    ay = 130 + 560 + 22
    for i in range(len(lanes)):
        lx, _, lw, _ = lanes[i]
        circle(page, lx + lw / 2, ay, 6, fill="red")
        if i < len(lanes) - 1:
            page.rect([lx + lw / 2, ay - 1, lanes[i + 1][0] - lx, 2], fill="bar")
    T(page, [32, ay + 28, 700, 14],
      "CAPACIDADES DE IA QUE O PROGRAMA PASSA A TER", style="lbl")
    legend = [
        ("Modelos de recomendação", "feed, vertical, micro-resgate, causa"),
        ("PLN / agentes (LLM)", "assistente, busca, explainer que conversa"),
        ("Previsão & propensão", "crédito em 45d, breakage, churn, atraso"),
        ("Antifraude & rastreio", "resgate sem erro, estorno automático"),
        ("Preço & otimização", "valor-por-ponto, melhor destino de cashback"),
    ]
    for (ttl, desc), cb in zip(legend, row([32, ay + 48, W - 64, 64], count=5,
                                           gap=16)):
        card(page, cb, fill="paper")
        ix, iy, iw, _ = inset(cb, 14)
        T(page, [ix, iy, iw, 14], ttl, style="h3")
        T(page, [ix, iy + 18, iw, 28], _wrap(desc, 30), style="mut")


# ======================================================================= #
#  build
# ======================================================================= #
CONCEPTS = [
    dict(n=1, key="01_cockpit", title="Cockpit do cooperado",
         axis="home centrada na conta",
         problem="O marketplace vende antes de mostrar quem é o cooperado: saldo, "
                 "validade e movimentação ficam invisíveis.",
         approach=["Saldo + validade 24m + pendências no topo",
                   "Ações rápidas: Juntar, Usar, Cashback, Cooperativa",
                   "‘Dá pra resgatar’ filtra pelo saldo real",
                   "Extrato de movimentação sempre à mão"],
         outcome="O cooperado entende seu valor em 1 olhada e age, em vez de "
                 "navegar uma loja genérica.",
         ai="IA prioriza o ‘dá pra resgatar’ por afinidade e prevê o que cabe no "
            "saldo — o painel se monta sozinho.",
         refactors="home  ·  /minha-conta",
         draw=p01_cockpit),
    dict(n=2, key="02_cashback", title="Cashback: 3 destinos",
         axis="ponto vira dinheiro",
         problem="O grande diferencial do Coopera — ponto vira real — fica "
                 "escondido; ninguém sabe que dá pra sacar.",
         approach=["Destaca: fatura, conta corrente ou carteira",
                   "Seletor de quanto resgatar, com valor em R$",
                   "Mostra prazo de cada destino",
                   "Produtos do Shop como alternativa"],
         outcome="O cooperado percebe que o ponto é dinheiro líquido e escolhe o "
                 "destino com clareza.",
         ai="IA recomenda o destino que mais rende pelo seu perfil e prevê o "
            "melhor momento de sacar.",
         refactors="resgate  ·  /cashback",
         draw=p02_cashback),
    dict(n=3, key="03_earn", title="Acúmulo guiado",
         axis="transparência do ganho",
         problem="Juntar é confuso: compra na parceira pelo app e o ponto só cai "
                 "em 45 dias, sem rastreio.",
         approach=["Fluxo 1-2-3: ative → compre → receba",
                   "Tracker de compras aguardando crédito",
                   "Prazo de 45 dias visível por compra",
                   "Melhores taxas de cashback agora"],
         outcome="O cooperado confia que vai pontuar e sabe exatamente quando — "
                 "menos ansiedade e suporte.",
         ai="IA estima a data provável do crédito e avisa se uma compra "
            "‘deveria ter pontuado’ e não pontuou.",
         refactors="juntar  ·  /juntar",
         draw=p03_earn),
    dict(n=4, key="04_statement", title="Extrato auditável",
         axis="confiança / rastreabilidade",
         problem="‘Meus pontos não aparecem / foram zerados’ é a reclamação nº 1. "
                 "Não há rastreio nem contestação.",
         approach=["Cada compra com status: pendente/creditado/análise",
                   "Alerta do que está dentro dos 45 dias",
                   "Contestação com protocolo",
                   "Extrato que parece um banco, não caixa-preta"],
         outcome="Resolve a dor que mais gera reclamação e reconstrói a confiança "
                 "no acúmulo de pontos.",
         ai="IA reconcilia compras × pontos e sinaliza anomalias antes do "
            "cooperado reclamar — auditoria automática.",
         refactors="extrato  ·  /extrato",
         draw=p04_statement),
    dict(n=5, key="05_shop", title="Shop facetado",
         axis="mecanismo de layout (facetas)",
         problem="São 250 mil itens sem facetas claras; achar o que cabe nos "
                 "pontos é difícil.",
         approach=["Facetas: categoria, forma de pagar, preço",
                   "Filtro ‘cabe nos meus pontos’",
                   "Preço em pontos + reais em cada card",
                   "Pague com pontos, pontos + cartão ou PIX"],
         outcome="Descoberta real no marketplace em vez de rolar uma vitrine "
                 "infinita sem filtro útil.",
         ai="IA ranqueia por ‘menos pontos pra você’ e aprende suas categorias "
            "preferidas a cada visita.",
         refactors="marketplace  ·  /shopping",
         draw=p05_shop),
    dict(n=6, key="06_search", title="Busca unificada",
         axis="IA orientada à busca",
         problem="A busca não cruza Shopping, Agro, Saúde, Viagens e Produtos "
                 "Cooperados num só lugar.",
         approach=["Busca dominante cobre todas as experiências",
                   "Facetas por tipo de resultado e por preço",
                   "Filtro ‘cabe no meu saldo’ por padrão",
                   "Resultados marcados por origem"],
         outcome="Uma caixa de busca resolve qualquer intenção; o saldo vira "
                 "filtro natural de relevância.",
         ai="Busca em linguagem natural com ranqueamento por valor-por-ponto: a "
            "IA interpreta a intenção, não só a palavra.",
         refactors="busca global  ·  /busca",
         draw=p06_search),
    dict(n=7, key="07_checkout", title="Checkout pontos + PIX",
         axis="fluxo / pagamento",
         problem="Resgatar dá erro de pagamento por dias; e o split pontos + "
                 "cartão + PIX não é claro.",
         approach=["Escolha clara: só pontos, pontos+cartão, PIX",
                   "Stepper sacola → entrega → pagamento",
                   "PIX com 5% à vista destacado",
                   "Pontos só debitados ao confirmar"],
         outcome="Resgate ganha a confiança de um e-commerce moderno e reduz o "
                 "abandono por erro.",
         ai="IA sugere o split ótimo de pontos + dinheiro e detecta erro/fraude "
            "antes de debitar.",
         refactors="resgate  ·  /checkout",
         draw=p07_checkout),
    dict(n=8, key="08_coop", title="Minha cooperativa",
         axis="identidade cooperativa",
         problem="O Coopera parece uma loja qualquer; o fato de o usuário ser "
                 "dono (cooperado) some por completo.",
         approach=["Mostra sua cooperativa singular e vínculo",
                   "Sobras a receber, impacto local, assembleia",
                   "Conecta pontos ao fortalecimento da coop.",
                   "Comprar de cooperados gira a economia local"],
         outcome="Ativa o diferencial único do Sicoob: pertencimento. Não é "
                 "cliente, é dono — e isso fideliza.",
         ai="IA personaliza o impacto local pelo seu perfil e projeta suas "
            "sobras conforme o uso do Coopera.",
         refactors="institucional  ·  /minha-cooperativa",
         draw=p08_coop),
    dict(n=9, key="09_cooperados", title="Produtos dos Cooperados",
         axis="curadoria / origem",
         problem="Os produtos feitos por cooperados ficam diluídos no catálogo "
                 "geral, sem valorizar a origem.",
         approach=["Vitrine exclusiva de produtos de cooperados",
                   "Filtro por origem: café, agro, artesanato",
                   "Selo ◈ Cooperado e cooperativa de origem",
                   "Preço em pontos + reais"],
         outcome="Valoriza a produção cooperativa e dá um motivo de compra que "
                 "nenhum marketplace comum tem.",
         ai="IA recomenda produtos de cooperados por afinidade e proximidade "
            "geográfica — apoio local com relevância.",
         refactors="marketplace  ·  /produtos-cooperados",
         draw=p09_cooperados),
    dict(n=10, key="10_experiences", title="Navegue por experiência",
         axis="IA por vertical",
         problem="‘Navegue por experiência’ existe, mas Shopping/Agro/Saúde/"
                 "Viagens são só ícones, sem profundidade.",
         approach=["Cada experiência vira um mundo com porta clara",
                   "Busca própria dentro de cada vertical",
                   "Agro e Saúde como verticais de 1ª classe",
                   "Entrada direta, sem passar pelo genérico"],
         outcome="Reflete quem é o cooperado (rural, saúde) e dá profundidade a "
                 "verticais hoje subaproveitadas.",
         ai="IA escolhe qual experiência abrir primeiro pelo seu perfil de "
            "cooperado (ex.: produtor rural → Agro).",
         refactors="home  ·  experiências",
         draw=p10_experiences),
    dict(n=11, key="11_mobile", title="Coopera no Super App",
         axis="fator de forma",
         problem="O acúmulo nasce no Sicoob Super App, mas o Coopera vive num "
                 "site à parte, desconectado do dia a dia.",
         approach=["Aba Coopera nativa no bottom-nav do app",
                   "Saldo e pontos a um toque do Pix/cartão",
                   "Usar pontos sem sair do app",
                   "Push de crédito e validade no lugar certo"],
         outcome="Experiência contínua: o cooperado já está no app do banco — o "
                 "Coopera mora ali, não num site distante.",
         ai="IA manda push preditivo (ponto a vencer, taxa em dobro) no momento "
            "certo, dentro do Super App.",
         refactors="Super App  ·  aba Coopera",
         draw=p11_mobile),
    dict(n=12, key="12_feed", title="Feed personalizado",
         axis="conteúdo algorítmico",
         problem="Ofertas, Mais-vendidos e Cooperados são fileiras fixas, iguais "
                 "pra todos, ignorando o comportamento.",
         approach=["Feed algorítmico substitui fileiras fixas",
                   "Cards de intenção: expira, perto, agro, doação",
                   "Reordena por comportamento e perfil",
                   "Cada card é uma ação distinta, não vitrine"],
         outcome="A home fala com cada cooperado: o ponto que vence, a meta perto, "
                 "o cooperado local que combina.",
         ai="O feed é a IA: um modelo de recomendação ordena cada card por "
            "propensão e urgência.",
         refactors="home editorial  ·  /pra-voce",
         draw=p12_feed),
    dict(n=13, key="13_value", title="Valor do ponto",
         axis="transparência de preço",
         problem="O cooperado não sabe quanto vale 1 ponto, então não percebe "
                 "quando faz uma troca ruim.",
         approach=["Mostra o saldo em R$ pelo melhor uso",
                   "Valor por ponto (¢/pt) em cada tipo de troca",
                   "Marca o ‘melhor valor’ explicitamente",
                   "Lista as melhores trocas pelo saldo"],
         outcome="Decisão informada: o cooperado extrai mais de cada ponto e "
                 "confia no programa.",
         ai="IA calcula o valor-por-ponto em tempo real e recomenda a troca que "
            "maximiza R$ por ponto.",
         refactors="catálogo  ·  /valor-dos-pontos",
         draw=p13_value),
    dict(n=14, key="14_expiry", title="Central de validade",
         axis="ciclo de vida / 24 meses",
         problem="Pontos vencem em 24 meses e o cooperado é pego de surpresa — "
                 "vira breakage e frustração.",
         approach=["Linha do tempo por data de vencimento",
                   "Sugestões de queima do tamanho do saldo",
                   "Micro-resgates e cashback em 1 clique",
                   "Nunca deixa perder por descuido"],
         outcome="Menos breakage e mais uso recorrente — o cooperado sente que a "
                 "cooperativa protege o valor dele.",
         ai="IA prevê a probabilidade de breakage e dispara o lembrete certo, na "
            "hora certa, com a melhor opção de queima.",
         refactors="validade  ·  /a-vencer",
         draw=p14_expiry),
    dict(n=15, key="15_concierge", title="Concierge IA",
         axis="interação conversacional",
         problem="Achar a melhor ação (sacar, trocar, doar) exige navegar muitas "
                 "telas; não há quem entenda o pedido.",
         approach=["Chat resolve em linguagem natural",
                   "Sugere a melhor opção pelo seu perfil",
                   "Executa a ação direto da conversa",
                   "Atalhos pras perguntas mais comuns"],
         outcome="A jornada vira diálogo: o cooperado pergunta, o Coopera "
                 "resolve — sem caçar em menus.",
         ai="É IA-nativa: um agente conversacional (LLM) com as ferramentas de "
            "saldo, catálogo, cashback e resgate plugadas.",
         refactors="suporte/descoberta  ·  /assistente",
         draw=p15_concierge),
    dict(n=16, key="16_directory", title="Diretório de parceiras",
         axis="descoberta de lojas",
         problem="As lojas parceiras viram uma lista sem busca nem ordenação por "
                 "taxa de cashback.",
         approach=["Página dedicada, buscável e filtrável",
                   "Facetas por categoria e maior taxa",
                   "Grade A–Z das 96 parceiras",
                   "Taxa de pontos/R$ visível em cada card"],
         outcome="Descoberta real de onde juntar mais pontos, em vez de uma lista "
                 "impossível de escanear.",
         ai="Busca semântica entende ‘loja de esporte com mais ponto’ e a IA "
            "reordena pelo seu padrão de compra.",
         refactors="parceiras  ·  /lojas-parceiras",
         draw=p16_directory),
    dict(n=17, key="17_donate", title="Doações & impacto",
         axis="propósito / ESG",
         problem="‘Doações’ existe no menu mas sem conexão com o cooperativismo "
                 "nem com projetos locais reais.",
         approach=["Causas com meta votada em assembleia",
                   "Projeto ligado à sua cooperativa singular",
                   "Micro-doação queima saldo a vencer",
                   "Mostra o impacto local concreto"],
         outcome="Une cooperativismo, propósito e anti-breakage: o ponto que ia "
                 "vencer vira impacto na comunidade.",
         ai="IA combina a causa ao seu perfil de valores e à sua região, e "
            "quantifica o impacto previsto da doação.",
         refactors="doações  ·  /doacoes",
         draw=p17_donate),
    dict(n=18, key="18_status", title="Status de resgate",
         axis="pós-compra / rastreio",
         problem="Depois do resgate, ‘deu erro e sumiu’: sem etapa, prazo ou "
                 "protocolo para acompanhar.",
         approach=["Timeline do pedido: confirmado → entregue",
                   "Protocolo e prazos visíveis",
                   "Ajuda e chat 24h no contexto",
                   "Garantia: falhou? estorna pontos na hora"],
         outcome="Acaba a insegurança do pós-resgate — a causa direta de muitas "
                 "reclamações no Reclame Aqui.",
         ai="IA prevê atraso na entrega e dispara o estorno automático de pontos "
            "quando um resgate falha.",
         refactors="resgate  ·  /meus-resgates",
         draw=p18_status),
    dict(n=19, key="19_explainer", title="Como funciona",
         axis="compreensão / clareza",
         problem="O programa tem regras (45 dias, 24 meses, cashback) que "
                 "ninguém explica de forma simples.",
         approach=["Explicação em 1-2-3, sem juridiquês",
                   "Colunas: formas de Ganhar × Usar",
                   "Deixa claro que ponto vira dinheiro",
                   "Dúvidas frequentes em destaque"],
         outcome="Ativação mais rápida de cooperados e menos suporte — todo "
                 "mundo entende o valor em 1 minuto.",
         ai="IA responde dúvidas em linguagem natural e adapta a explicação ao "
            "nível do cooperado — um FAQ que conversa.",
         refactors="onboarding  ·  /como-funciona",
         draw=p19_explainer),
    dict(n=20, key="20_omni", title="Agência + app",
         axis="canal online ↔ físico",
         problem="O cooperativismo é local e presencial, mas o Coopera é 100% "
                 "online, ignorando o PA e o gerente.",
         approach=["Carteira com QR pra usar no caixa do PA",
                   "Pass na Apple/Google Wallet",
                   "Postos de atendimento perto de você",
                   "Junte e use pontos presencialmente"],
         outcome="Experiência omnichannel fiel ao cooperativismo: do app ao "
                 "balcão da agência local.",
         ai="Geo-IA mostra o PA certo e prevê a próxima necessidade pra o gerente "
            "já chegar com a oferta de pontos.",
         refactors="todo o site  ·  /na-agencia",
         draw=p20_omni),
]


def build() -> DocumentBuilder:
    b = DocumentBuilder(
        title="Coopera — 20 refatorações + IA na jornada (wireframes)",
        profile="deck", lang="pt-BR")
    for name, value in COLORS.items():
        b.define_color(name, value)
    b.define_color("warm", "#33403B")  # dark track tone for progress on dark hero
    for name, style in STYLES.items():
        b.define_text_style(name, **style)
    index(b)
    for c in CONCEPTS:
        concept(b, **c)
    ai_journey(b)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in errors[:30]:
        print(f"  ERROR [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:30]:
        print(f"  warn  [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "fixtures", "coopera-refactor-wireframes.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
