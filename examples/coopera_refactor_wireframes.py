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


AI_FORWARD = {4, 12, 15, 18}  # proposals where AI is the load-bearing mechanism

PROPOSALS = [
    (1, "Cockpit do dono", "propriedade / conta"),
    (2, "Carteira: pontos + sobras", "o que a coop devolve"),
    (3, "Minha cooperativa", "identidade cooperativa"),
    (4, "Assembleia digital", "governança / voz"),
    (5, "Impacto cooperativo", "ESG / comunidade"),
    (6, "Você é dono", "compreensão / pertencimento"),
    (7, "Cashback: 3 destinos", "ponto vira dinheiro"),
    (8, "Pix Coopera", "pagamento nativo (Pix)"),
    (9, "Coopera no Super App", "fator de forma"),
    (10, "Acúmulo guiado", "transparência do ganho"),
    (11, "Hub Agro", "vertical do cooperado"),
    (12, "Painel do produtor", "agro / safra"),
    (13, "Hub Saúde", "vertical do cooperado"),
    (14, "Produtos dos Cooperados", "economia cooperativa"),
    (15, "Economia local", "economia circular"),
    (16, "Doações votadas", "propósito / assembleia"),
    (17, "Extrato auditável", "confiança / rastreio"),
    (18, "Status de resgate", "pós-compra / garantia"),
    (19, "Checkout pontos + PIX", "fluxo / pagamento"),
    (20, "Agência + app", "canal online ↔ físico"),
]


# ======================================================================= #
#  01 — cockpit do cooperado
# ======================================================================= #
def p01_cockpit(page):
    region = browser(page, "shopcoopera.com.br/  ·  minha conta")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    # ownership-first hero: points + sobras + cooperative, side by side
    hero = [x, y, w, 132]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 22)
    stats = [("PONTOS COOPERA", "12.480 pts", "↘ 640 vencem em 38 dias"),
             ("SOBRAS A RECEBER", "R$ 1.240", "resultado distribuído a você"),
             ("SUA COOPERATIVA", "Credicitrus", "cooperado · você é dono")]
    sw3 = (hw - 168) / 3
    for i, (lbl, big, sub) in enumerate(stats):
        sx = hx + i * sw3
        if i:
            page.rect([sx - 16, hy + 4, 1, 80], fill="warm")
        T(page, [sx, hy, sw3 - 10, 14], lbl,
          style=ts(10, 700, "faint", letter_spacing=1.1))
        T(page, [sx, hy + 18, sw3 - 10, 30], big,
          style=ts(23, 800, "paper", letter_spacing=-0.6))
        T(page, [sx, hy + 54, sw3 - 10, 14], sub, style=ts(11, 500, "faint"))
    button(page, [hx + hw - 150, hy + 14, 150, 32], "Comprar pontos", "primary")
    button(page, [hx + hw - 150, hy + 54, 150, 32], "Virar cashback", "ghost")

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
#  cooperative-native pages (no Esfera analog)
# ======================================================================= #
def p_carteira(page):
    """Pontos + Sobras: a single 'what the cooperative gives back' wallet."""
    region = browser(page, "shopcoopera.com.br/carteira")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 18], "Sua carteira do cooperado", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Pontos e sobras juntos: tudo que a cooperativa devolve a você, num lugar.",
      style="mut")
    hero = [x, y + 52, w, 110]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 20)
    cols = [("PONTOS COOPERA", "12.480 pts", "≈ R$ 324"),
            ("SOBRAS A RECEBER", "R$ 1.240", "exercício 2025"),
            ("TOTAL DE VOLTA", "R$ 1.564", "no melhor uso")]
    for i, (lbl, big, sub) in enumerate(cols):
        sx = hx + i * (hw / 3)
        if i:
            page.rect([sx - 12, hy + 2, 1, 66], fill="warm")
        T(page, [sx, hy, hw / 3 - 16, 13], lbl,
          style=ts(10, 700, "faint", letter_spacing=1.1))
        T(page, [sx, hy + 16, hw / 3 - 16, 28],
          big, style=ts(24, 800, "red" if i == 2 else "paper", letter_spacing=-0.6))
        T(page, [sx, hy + 52, hw / 3 - 16, 14], sub, style=ts(11, 500, "faint"))

    use, hist = row([x, y + 178, w, body[3] - 178 - 18], gap=16, weights=[1, 1])
    card(page, use)
    ux, uy, uw, _ = inset(use, 18)
    T(page, [ux, uy, uw, 16], "O que fazer com cada um", style="h2")
    rows = [("Pontos → produtos", "no Shop ou cooperados"),
            ("Pontos → dinheiro", "fatura, conta ou carteira"),
            ("Sobras → sacar", "cai na conta corrente"),
            ("Sobras → reinvestir", "vira capital na cooperativa")]
    ry = uy + 30
    for ttl, sub in rows:
        icon(page, [ux, ry, 34, 34], "↦", fill="redSft", style="glyphR")
        T(page, [ux + 46, ry + 2, uw - 46, 16], ttl, style="h3")
        T(page, [ux + 46, ry + 20, uw - 46, 14], sub, style="mut")
        ry += 48
    card(page, hist, fill="canvas")
    hx2, hy2, hw2, _ = inset(hist, 18)
    T(page, [hx2, hy2, hw2, 16], "Histórico do que voltou", style="h2")
    items = [("+ R$ 1.240", "Sobras 2025", "good"), ("+ 1.280 pts", "TokStok", "good"),
             ("+ R$ 90", "Cashback conta", "good"), ("+ 2.460 pts", "Nike", "good"),
             ("+ R$ 620", "Sobras 2024", "good")]
    iy = hy2 + 30
    for amt, lbl, tone in items:
        circle(page, hx2 + 8, iy + 9, 4, fill=_TONE[tone][1])
        T(page, [hx2 + 22, iy, hw2 - 120, 14], lbl, style="td")
        T(page, [hx2 + hw2 - 110, iy, 110, 14], amt,
          style=dict(font_family=MONO, font_size=11, color="good", align="right"))
        iy += 32


def p_assembleia(page):
    """Digital assembly — one cooperado, one vote on where Coopera invests."""
    region = browser(page, "shopcoopera.com.br/assembleia")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 18], "Assembleia digital — sua voz decide", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Você é dono: 1 cooperado = 1 voto. Decida onde o Coopera investe e doa.",
      style="mut")

    main, side = row([x, y + 56, w, body[3] - 56 - 18], gap=16, weights=[2, 1])
    card(page, main)
    mx, my, mw, _ = inset(main, 20)
    badge(page, [mx, my, 84, 22], "PAUTA ABERTA", "red")
    T(page, [mx + 96, my + 2, mw - 96, 16], "Encerra em 4 dias · 1.284 votos",
      style="mut")
    T(page, [mx, my + 36, mw, 18],
      "Para onde direcionar o fundo de pontos doados deste trimestre?", style="h2")
    opts = [("Educação no campo", 0.46, True),
            ("Saúde da comunidade", 0.31, False),
            ("Reflorestar nascentes", 0.23, False)]
    oy = my + 70
    for ttl, frac, sel in opts:
        circle(page, mx + 10, oy + 10, 9, fill="red" if sel else "paper",
               stroke="faint")
        if sel:
            circle(page, mx + 10, oy + 10, 4, fill="paper")
        T(page, [mx + 32, oy, mw - 120, 16], ttl, style="h3")
        T(page, [mx + mw - 60, oy, 60, 16], f"{int(frac*100)}%", style="right")
        progressbar(page, [mx + 32, oy + 22, mw - 32, 8], frac)
        oy += 50
    button(page, [mx, oy + 6, 160, 36], "Confirmar voto", "primary")
    T(page, [mx + 176, oy + 16, mw - 176, 14],
      "transparente e auditável", style="mut")

    card(page, side, fill="canvas")
    sx, sy, sw, _ = inset(side, 16)
    T(page, [sx, sy, sw, 16], "Outras pautas", style="h2")
    pautas = [("Novos parceiros locais", "Aberta", "red"),
              ("Calendário de safra", "Aberta", "red"),
              ("Prestação de contas 2025", "Encerrada", "good"),
              ("Taxa de adesão", "Encerrada", "good")]
    py = sy + 30
    for ttl, st, tone in pautas:
        T(page, [sx, py, sw - 80, 28], _wrap(ttl, 26), style="td")
        badge(page, [sx + sw - 74, py, 74, 20], st, tone)
        page.rect([sx, py + 36, sw, 1], fill="line")
        py += 48


def p_impacto(page):
    """ESG dashboard — the community impact your points & cooperative created."""
    region = browser(page, "shopcoopera.com.br/impacto")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 18], "O impacto da sua cooperativa", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Onde seus pontos e suas sobras viraram comunidade — em números.",
      style="mut")
    kpis = [("Projetos apoiados", "32", "na sua região"),
            ("Devolvido à comunidade", "R$ 1,2 mi", "em 2026"),
            ("Cooperados ativos", "48 mil", "na Credicitrus"),
            ("Sua contribuição", "R$ 64", "em doações de pontos")]
    for (lbl, big, sub), cb in zip(kpis, row([x, y + 56, w, 100], count=4, gap=14)):
        card(page, cb, fill="canvas")
        ix, iy, iw, _ = inset(cb, 16)
        T(page, [ix, iy, iw, 13], lbl.upper(), style="lbl")
        T(page, [ix, iy + 18, iw, 26], big, style="kpiR")
        T(page, [ix, iy + 52, iw, 14], sub, style="mut")

    left, right = row([x, y + 172, w, body[3] - 172 - 18], gap=16, weights=[1.4, 1])
    card(page, left)
    lx, ly, lw, _ = inset(left, 18)
    T(page, [lx, ly, lw, 16], "Projetos que seus pontos ajudaram", style="h2")
    projs = [("Escola rural · Ribeirão", 0.9), ("Posto de saúde · Centro", 0.7),
             ("Mata ciliar · Rio Pardo", 0.5), ("Escolinha de futebol", 0.8)]
    py = ly + 30
    for ttl, frac in projs:
        T(page, [lx, py, lw - 60, 14], ttl, style="td")
        T(page, [lx + lw - 56, py, 56, 14], f"{int(frac*100)}%", style="right")
        progressbar(page, [lx, py + 20, lw, 8], frac, fill="good")
        py += 44
    card(page, right, fill="ink")
    rx, ry, rw, _ = inset(right, 18)
    T(page, [rx, ry, rw, 14], "PRINCÍPIO COOPERATIVO",
      style=ts(10.5, 700, "faint", letter_spacing=1.1))
    T(page, [rx, ry + 22, rw, 60],
      _wrap("O que você gasta no Coopera volta como sobras e como projeto na "
            "sua própria comunidade.", 30),
      style=ts(15, 700, "paper", line_height=1.4))
    T(page, [rx, ry + 120, rw, 14], "Interesse pela comunidade · 7º princípio",
      style="chipA")


def p_educacao(page):
    """Cooperativism-first onboarding — you're an owner, not a customer."""
    region = browser(page, "shopcoopera.com.br/sou-dono")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 20], "Você é dono, não cliente", style="h1")
    T(page, [x, y + 26, 660, 14],
      "Antes do programa de pontos: entenda o que é ser cooperado do Sicoob.",
      style="mut")
    steps = [("1", "Cooperativismo", "Você é sócio da cooperativa — e participa "
              "dos resultados dela."),
             ("2", "Sobras", "O que a cooperativa lucra volta pra você como "
              "sobras, todo ano."),
             ("3", "Coopera", "O programa devolve ainda mais: pontos viram "
              "produtos ou dinheiro.")]
    for (n, ttl, desc), cb in zip(steps, row([x, y + 56, w, 130], count=3,
                                             gap=16)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 18)
        circle(page, ix + 18, iy + 18, 18, fill="redSft")
        T(page, [ix, iy + 8, 36, 22], n, style="kpiR")
        T(page, [ix + 48, iy + 6, iw - 48, 18], ttl, style="h1")
        T(page, [ix, iy + 44, iw, 60], _wrap(desc, 40), style="body")

    bank, coop = row([x, y + 202, w, body[3] - 202 - 18], gap=16, weights=[1, 1])
    card(page, bank, fill="canvas")
    bx, by, bw, _ = inset(bank, 18)
    T(page, [bx, by, bw, 16], "Banco comum", style="h2")
    for i, t in enumerate(["Você é cliente", "Lucro vai pro acionista",
                           "Decisão é de cima", "Pontos só viram produto"]):
        T(page, [bx, by + 34 + i * 30, bw, 14], "✕  " + t, style="mut")
    card(page, coop, stroke="red")
    cx, cyy, cw, _ = inset(coop, 18)
    T(page, [cx, cyy, cw, 16], "Cooperativa (você aqui)", style="h2")
    for i, t in enumerate(["Você é dono", "Sobras voltam pra você",
                           "1 cooperado = 1 voto", "Pontos viram dinheiro"]):
        circle(page, cx + 6, cyy + 41 + i * 30, 5, fill="red")
        T(page, [cx + 18, cyy + 34 + i * 30, cw - 18, 14], t, style="td")


def p_pix(page):
    """Pix Coopera — pay any Pix with points, round up change to earn."""
    region = browser(page, "app Sicoob · Pix Coopera")
    x, y, w, h = inset(region, 0)
    # phone-style Pix screen on the left, explainer on the right
    ph = [x + 40, y + 24, 320, region[3] - 48]
    page.rect(ph, fill="ink", radius=26)
    sc = inset(ph, [14, 12])
    page.rect(sc, fill="paper", radius=16)
    sx, sy, sw, sh = sc
    T(page, [sx + 14, sy + 14, sw - 28, 14], "Pix", style="h2")
    T(page, [sx + sw - 90, sy + 14, 78, 14], "12.480 pts", style="pts")
    T(page, [sx + 14, sy + 44, sw - 28, 13], "VALOR", style="lbl")
    T(page, [sx + 14, sy + 60, sw - 28, 30], "R$ 48,00", style="kpi")
    # pay-with-points toggle
    tg = [sx + 14, sy + 104, sw - 28, 54]
    page.rect(tg, fill="redSft", radius=10)
    T(page, [sx + 26, sy + 116, sw - 120, 16], "Pagar com pontos", style="h3")
    T(page, [sx + 26, sy + 134, sw - 120, 13], "1.846 pts = R$ 48,00", style="chipA")
    pill(page, [sx + sw - 78, sy + 120, 50, 24], None, fill="red", radius=12)
    circle(page, sx + sw - 40, sy + 132, 9, fill="paper")
    # round-up earn
    ru = [sx + 14, sy + 174, sw - 28, 50]
    card(page, ru, fill="canvas")
    T(page, [sx + 26, sy + 184, sw - 60, 14], "Arredondar e juntar pontos",
      style="h3")
    T(page, [sx + 26, sy + 202, sw - 60, 13], "troco de R$ 0,00 → +pontos",
      style="mut")
    button(page, [sx + 14, sy + sh - 56, sw - 28, 40], "Confirmar Pix", "primary")

    # right: why this matters
    rx = x + 410
    rw = region[0] + region[2] - rx - 30
    T(page, [rx, y + 40, rw, 18], "O Pix do dia a dia vira pontos", style="h1")
    T(page, [rx, y + 68, rw, 40],
      _wrap("O cooperado usa Pix o tempo todo no Super App. Aqui ele também "
            "paga COM pontos e ganha pontos no troco.", 52), style="body")
    feats = [("Pagar com pontos", "qualquer Pix abatido do saldo"),
             ("Arredondar o troco", "centavos viram pontos, sem esforço"),
             ("Sem sair do app", "nasce onde o cooperado já está")]
    fy = y + 130
    for ttl, sub in feats:
        icon(page, [rx, fy, 36, 36], "$", fill="redSft", style="glyphR")
        T(page, [rx + 48, fy + 2, rw - 48, 16], ttl, style="h2")
        T(page, [rx + 48, fy + 22, rw - 48, 14], sub, style="mut")
        fy += 56


def p_agro(page):
    """Agro hub — Sicoob's rural backbone as a first-class vertical."""
    region = browser(page, "shopcoopera.com.br/agronegocio")
    body = site_header(page, region, active="Agronegócio")
    x, y, w, _ = inset(body, 18)
    hero = [x, y, w, 92]
    page.rect(hero, fill="ink", radius=12)
    T(page, [x + 20, y + 22, 400, 20], "Agro Coopera", style=ts(20, 800, "paper"))
    T(page, [x + 20, y + 50, 520, 14],
      "Insumos, máquinas e crédito rural — pontos no ritmo da sua safra.",
      style=ts(12, 500, "faint"))
    button(page, [x + w - 200, y + 28, 180, 36], "Falar com gerente agro",
           "primary")

    tiles = [("Insumos", "sementes, defensivos"), ("Máquinas", "tratores, peças"),
             ("Crédito rural", "custeio e investimento"),
             ("Seguro agrícola", "proteja a safra")]
    for (ttl, sub), cb in zip(tiles, row([x, y + 108, w, 96], count=4, gap=14)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 16)
        icon(page, [ix, iy, 36, 36], "✦", fill="redSft", style="glyphR")
        T(page, [ix, iy + 44, iw, 16], ttl, style="h2")
        T(page, [ix, iy + 64, iw, 14], sub, style="mut")

    # safra calendar strip
    T(page, [x, y + 220, 300, 14], "CALENDÁRIO DA SAFRA · MILHO", style="lbl")
    phases = [("Plantio", "set–out", True), ("Tratos", "nov–jan", True),
              ("Colheita", "fev–abr", False), ("Comercialização", "mai–jun", False)]
    cal = row([x, y + 242, w, 60], count=4, gap=10)
    for (ph, when, on), cb in zip(phases, cal):
        card(page, cb, fill="redSft" if on else "canvas")
        T(page, [cb[0] + 14, cb[1] + 12, cb[2] - 28, 14], ph,
          style="h3" if on else "mut")
        T(page, [cb[0] + 14, cb[1] + 32, cb[2] - 28, 13], when, style="mut")

    T(page, [x, y + 318, 300, 14], "OFERTAS COM PONTO EM DOBRO", style="lbl")
    for cb in grid([x, y + 340, w, body[3] - 340 - 16], cols=4, rows=1, gap=14):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 12)
        thumb(page, [ix, iy, iw, ih - 40], "insumo")
        T(page, [ix, iy + ih - 36, iw, 14], "Insumo agro", style="h3")
        T(page, [ix, iy + ih - 18, iw, 14], "10 pts/R$", style="pts")


def p_safra(page):
    """Producer cockpit — agribusiness dashboard for the rural cooperado."""
    region = browser(page, "shopcoopera.com.br/produtor")
    body = site_header(page, region, active="Agronegócio")
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 18], "Painel do produtor", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Coopera fala a língua de quem planta: safra, crédito e pontos por insumo.",
      style="mut")
    kpis = [("Área plantada", "320 ha", "milho · safra 25/26"),
            ("Crédito disponível", "R$ 184 mil", "custeio aprovado"),
            ("Pontos da safra", "42.800 pts", "em insumos este ciclo")]
    for (lbl, big, sub), cb in zip(kpis, row([x, y + 56, w, 100], count=3, gap=14)):
        card(page, cb, fill="canvas")
        ix, iy, iw, _ = inset(cb, 16)
        T(page, [ix, iy, iw, 13], lbl.upper(), style="lbl")
        T(page, [ix, iy + 18, iw, 26], big, style="kpiR")
        T(page, [ix, iy + 52, iw, 14], sub, style="mut")

    left, right = row([x, y + 172, w, body[3] - 172 - 18], gap=16, weights=[1.5, 1])
    card(page, left)
    lx, ly, lw, _ = inset(left, 18)
    T(page, [lx, ly, lw, 16], "Linha da safra 25/26", style="h2")
    events = [("Custeio liberado", "set · R$ 184 mil", True),
              ("Compra de sementes", "set · +12.000 pts", True),
              ("Defensivos", "nov · +18.400 pts", True),
              ("Colheita prevista", "mar · estimada", False),
              ("Venda à cooperativa", "abr · +bônus pts", False)]
    ey = ly + 30
    for i, (lbl, when, done) in enumerate(events):
        circle(page, lx + 9, ey + 8, 7, fill="red" if done else "paper",
               stroke="faint")
        if done:
            circle(page, lx + 9, ey + 8, 3, fill="paper")
        if i < len(events) - 1:
            page.rect([lx + 8, ey + 16, 2, 30], fill="line")
        T(page, [lx + 30, ey, lw - 170, 16], lbl, style="h3" if done else "mut")
        T(page, [lx + lw - 160, ey, 160, 14], when, style="mut")
        ey += 46
    card(page, right, fill="ink")
    rx, ry, rw, _ = inset(right, 18)
    T(page, [rx, ry, rw, 14], "CRÉDITO + COOPERA",
      style=ts(10.5, 700, "faint", letter_spacing=1.1))
    T(page, [rx, ry + 22, rw, 60],
      _wrap("Cada insumo financiado pela cooperativa rende pontos — que voltam "
            "como desconto na próxima safra.", 30),
      style=ts(15, 700, "paper", line_height=1.4))
    button(page, [rx, ry + 140, rw, 36], "Simular próxima safra", "primary")


def p_saude(page):
    """Saúde hub — health vertical for the cooperado."""
    region = browser(page, "shopcoopera.com.br/saude")
    body = site_header(page, region, active="Saúde")
    x, y, w, _ = inset(body, 18)
    hero = [x, y, w, 92]
    page.rect(hero, fill="ink", radius=12)
    T(page, [x + 20, y + 22, 400, 20], "Saúde Coopera", style=ts(20, 800, "paper"))
    T(page, [x + 20, y + 50, 540, 14],
      "Consultas, exames e farmácia — cuidando do cooperado e da família.",
      style=ts(12, 500, "faint"))
    button(page, [x + w - 180, y + 28, 160, 36], "Agendar agora", "primary")

    tiles = [("Consultas", "presencial ou online"), ("Exames", "rede credenciada"),
             ("Farmácia", "desconto + pontos"), ("Telemedicina", "24h pelo app")]
    for (ttl, sub), cb in zip(tiles, row([x, y + 108, w, 100], count=4, gap=14)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 16)
        icon(page, [ix, iy, 36, 36], "✚", fill="redSft", style="glyphR")
        T(page, [ix, iy + 46, iw, 16], ttl, style="h2")
        T(page, [ix, iy + 66, iw, 14], sub, style="mut")

    book, near = row([x, y + 224, w, body[3] - 224 - 18], gap=16, weights=[1.3, 1])
    card(page, book)
    bx, by, bw, _ = inset(book, 18)
    T(page, [bx, by, bw, 16], "Agendar consulta com pontos", style="h2")
    field(page, [bx, by + 30, bw, 54], "Especialidade", "Clínico geral",
          kind="select")
    fr = row([bx, by + 96, bw, 54], count=2, gap=12)
    field(page, fr[0], "Data", "18/jun", kind="select")
    field(page, fr[1], "Pagar com", "2.000 pts", kind="select")
    button(page, [bx, by + 162, bw, 38], "Confirmar agendamento", "primary")
    card(page, near, fill="canvas")
    nx, ny, nw, _ = inset(near, 16)
    T(page, [nx, ny, nw, 16], "Rede perto de você", style="h2")
    for i, (nm, dist) in enumerate([("Clínica Central", "800 m"),
                                    ("Lab. Vida", "1,2 km"),
                                    ("Farmácia Coop.", "300 m")]):
        cb = [nx, ny + 32 + i * 52, nw, 44]
        card(page, cb)
        icon(page, [cb[0] + 10, cb[1] + 8, 28, 28], "✚", fill="paper")
        T(page, [cb[0] + 48, cb[1] + 8, cb[2] - 110, 16], nm, style="h3")
        T(page, [cb[0] + cb[2] - 60, cb[1] + 14, 52, 14], dist, style="td")


def p_economia(page):
    """Local economy — buy from nearby cooperados, value stays in the region."""
    region = browser(page, "shopcoopera.com.br/economia-local")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 600, 18], "Economia que volta pra sua região", style="h1")
    T(page, [x, y + 24, 660, 14],
      "Comprar de cooperados perto gira a economia local — e ainda rende pontos.",
      style="mut")
    mapcol, listcol = row([x, y + 56, w, h - 56], gap=16, weights=[1.2, 1])
    # map placeholder with pins
    page.rect(mapcol, fill="canvas", stroke="line", stroke_style=HAIR, radius=12)
    mx, my, mw, mh = mapcol
    for px, py in [(0.3, 0.3), (0.6, 0.45), (0.45, 0.65), (0.75, 0.7), (0.2, 0.6)]:
        cxp, cyp = mx + mw * px, my + mh * py
        circle(page, cxp, cyp, 10, fill="red")
        circle(page, cxp, cyp, 4, fill="paper")
    pill(page, [mx + 16, my + 16, 200, 28], "◉ Cooperados num raio de 20 km",
         fill="paper", stroke="line", style="chip", radius=8)
    # circular-economy callout
    cc = [mx + 16, my + mh - 70, mw - 32, 54]
    page.rect(cc, fill="ink", radius=10)
    T(page, [cc[0] + 16, cc[1] + 10, cc[2] - 32, 14],
      "Comprando aqui, 70% do valor fica na sua cidade",
      style=ts(13, 700, "paper"))
    T(page, [cc[0] + 16, cc[1] + 30, cc[2] - 32, 13],
      "economia circular cooperativa", style=ts(11, 500, "faint"))

    card(page, listcol)
    lx, ly, lw, _ = inset(listcol, 16)
    T(page, [lx, ly, lw, 16], "Produtores perto de você", style="h2")
    prods = [("Café do Sítio Boa Vista", "Cooperado · 4 km", "1.200 pts"),
             ("Mel da Serra", "Cooperado · 8 km", "600 pts"),
             ("Queijo Artesanal", "Cooperado · 12 km", "900 pts"),
             ("Hortaliças Orgânicas", "Cooperado · 6 km", "400 pts")]
    py = ly + 30
    for nm, who, pts in prods:
        cb = [lx, py, lw, 64]
        card(page, cb, fill="canvas")
        thumb(page, [cb[0] + 10, cb[1] + 10, 54, 44], "foto")
        T(page, [cb[0] + 76, cb[1] + 12, cb[2] - 90, 16], nm, style="h3")
        T(page, [cb[0] + 76, cb[1] + 32, cb[2] - 180, 14], who, style="mut")
        T(page, [cb[0] + cb[2] - 92, cb[1] + 33, 84, 14], pts, style="pts")
        py += 74


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
            ("Curadoria por vertical", "Agro ou Saúde certo pra você", "11"),
            ("Match local", "cooperados perto que combinam", "15"),
            ("Recomendação", "produtos de cooperados por afinidade", "14")]),
        ("JUNTAR", "ganhar sem fricção", "↑", [
            ("Reconciliação", "detecta compra que não pontuou", "10"),
            ("Pix inteligente", "arredonda o troco e credita", "08"),
            ("Push preditivo", "no Super App, na hora certa", "09")]),
        ("DECIDIR", "ponto, dinheiro ou sobras?", "$", [
            ("Otimização", "melhor destino de cashback", "07"),
            ("Carteira unificada", "pontos + sobras no melhor uso", "02"),
            ("Previsão de safra", "crédito e insumo no ciclo certo", "12")]),
        ("USAR", "resgatar sem erro", "↓", [
            ("Antifraude", "checa o resgate antes de debitar", "19"),
            ("Rastreio", "prevê atraso e estorna sozinho", "18"),
            ("Auditoria", "reconcilia e contesta sozinho", "17")]),
        ("PERTENCER", "cooperar e ficar", "◈", [
            ("Síntese de assembleia", "resume pautas e projeta impacto", "04"),
            ("Match de causa", "projeto local que combina", "16"),
            ("Personalização", "minha cooperativa em destaque", "03")]),
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
    dict(n=1, key="01_cockpit", title="Cockpit do dono",
         axis="propriedade / conta do dono",
         problem="O marketplace vende antes de mostrar quem é o cooperado — e "
                 "esconde que ele é dono, com pontos E sobras.",
         approach=["Hero com pontos, sobras e sua cooperativa juntos",
                   "Ações rápidas: Juntar, Usar, Cashback, Cooperativa",
                   "‘Dá pra resgatar’ filtra pelo saldo real",
                   "Movimentação de pontos e sobras à mão"],
         outcome="O cooperado vê seu valor de dono em 1 olhada — não é cliente "
                 "de loja, é sócio com retorno.",
         ai="IA prioriza o ‘dá pra resgatar’ por afinidade e projeta o retorno "
            "total (pontos + sobras) no melhor uso.",
         refactors="home  ·  /minha-conta",
         draw=p01_cockpit),
    dict(n=2, key="02_carteira", title="Carteira: pontos + sobras",
         axis="tudo que a cooperativa devolve",
         problem="Pontos e sobras vivem em mundos separados; o cooperado não vê o "
                 "total que a cooperativa devolve a ele.",
         approach=["Carteira única: pontos, sobras e total em R$",
                   "O que fazer com cada um, lado a lado",
                   "Sobras: sacar ou reinvestir como capital",
                   "Histórico unificado do que voltou"],
         outcome="Materializa o diferencial cooperativo: o retorno não é só "
                 "ponto, é dinheiro de dono — num lugar só.",
         ai="IA recomenda o melhor uso combinado de pontos + sobras e projeta o "
            "retorno do reinvestimento na cooperativa.",
         refactors="conta  ·  /carteira",
         draw=p_carteira),
    dict(n=3, key="03_coop", title="Minha cooperativa",
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
    dict(n=4, key="04_assembleia", title="Assembleia digital",
         axis="governança / sua voz",
         problem="A maior força do cooperativismo — decidir junto — está ausente "
                 "do programa; o cooperado não tem voz no Coopera.",
         approach=["1 cooperado = 1 voto, direto na plataforma",
                   "Vote onde o fundo de pontos doados vai",
                   "Pautas abertas e encerradas, transparentes",
                   "Prestação de contas auditável"],
         outcome="Transforma um programa de pontos em exercício de cooperativismo "
                 "real — engajamento que loja nenhuma replica.",
         ai="IA resume pautas longas em linguagem simples e projeta o impacto de "
            "cada opção antes do voto.",
         refactors="governança  ·  /assembleia",
         draw=p_assembleia),
    dict(n=5, key="05_impacto", title="Impacto cooperativo",
         axis="ESG / comunidade",
         problem="O cooperado não vê que seus pontos e sobras viram comunidade — "
                 "o impacto social fica invisível.",
         approach=["KPIs: projetos, R$ devolvido, cooperados, CO2",
                   "Projetos locais que seus pontos ajudaram",
                   "Liga gasto no Coopera a impacto na região",
                   "Reforça o 7º princípio: interesse pela comunidade"],
         outcome="Dá propósito ao programa e reduz breakage: usar pontos vira um "
                 "ato com impacto local visível.",
         ai="IA quantifica seu impacto individual e recomenda onde sua próxima "
            "doação de pontos rende mais para a comunidade.",
         refactors="institucional  ·  /impacto",
         draw=p_impacto),
    dict(n=6, key="06_educacao", title="Você é dono",
         axis="compreensão / pertencimento",
         problem="Cooperado não sabe o que é cooperativismo nem como sobras e "
                 "Coopera se conectam — entra como ‘cliente’.",
         approach=["Explica cooperativismo em 1-2-3, sem jargão",
                   "Liga sobras (anual) ao Coopera (contínuo)",
                   "Comparação clara: banco comum × cooperativa",
                   "Deixa explícito: ponto vira dinheiro"],
         outcome="Ativação mais rápida e fidelidade emocional: o cooperado "
                 "entende que é dono, não cliente.",
         ai="IA adapta a explicação ao perfil (urbano, produtor rural) e "
            "responde dúvidas sobre ser cooperado em linguagem natural.",
         refactors="onboarding  ·  /sou-dono",
         draw=p_educacao),
    dict(n=7, key="07_cashback", title="Cashback: 3 destinos",
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
    dict(n=8, key="08_pix", title="Pix Coopera",
         axis="pagamento nativo (Pix)",
         problem="O cooperado usa Pix o tempo todo no app, mas isso não conversa "
                 "com os pontos — duas experiências separadas.",
         approach=["Pagar qualquer Pix com pontos do saldo",
                   "Arredondar o troco do Pix e juntar pontos",
                   "Tudo dentro do Super App, sem fricção",
                   "Pontos no dia a dia, não só em compras grandes"],
         outcome="O hábito mais brasileiro vira motor de pontos — acúmulo e "
                 "resgate contínuos, no fluxo que já existe.",
         ai="IA sugere quando pagar com pontos vale mais que reais e ativa o "
            "arredondamento inteligente do troco.",
         refactors="Super App  ·  Pix",
         draw=p_pix),
    dict(n=9, key="09_superapp", title="Coopera no Super App",
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
    dict(n=10, key="10_earn", title="Acúmulo guiado",
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
    dict(n=11, key="11_agro", title="Hub Agro",
         axis="vertical do cooperado (agro)",
         problem="Agronegócio é o coração do Sicoob, mas no Coopera é só um ícone "
                 "— sem insumos, crédito rural ou safra.",
         approach=["Vertical Agro de 1ª classe: insumos, máquinas",
                   "Crédito rural e seguro agrícola integrados",
                   "Calendário de safra orienta a navegação",
                   "Ofertas de insumo com ponto em dobro"],
         outcome="Fala com quem sustenta a cooperativa — o produtor rural — em "
                 "vez de tratá-lo como comprador genérico.",
         ai="IA recomenda insumos pela cultura e fase da safra e prevê a melhor "
            "janela de compra de cada item.",
         refactors="experiência Agro  ·  /agronegocio",
         draw=p_agro),
    dict(n=12, key="12_safra", title="Painel do produtor",
         axis="agro / ciclo da safra",
         problem="O produtor rural não tem um Coopera que entenda safra, crédito "
                 "e os pontos gerados pelos insumos do ciclo.",
         approach=["Cockpit: área, crédito e pontos da safra",
                   "Linha do tempo do plantio à venda",
                   "Pontos por insumo financiado pela coop.",
                   "Simula a próxima safra com crédito + pontos"],
         outcome="Coopera vira ferramenta de gestão do produtor, não só "
                 "marketplace — fidelidade no core do Sicoob.",
         ai="IA projeta crédito e pontos do próximo ciclo e antecipa quando cada "
            "insumo será necessário na safra.",
         refactors="experiência Agro  ·  /produtor",
         draw=p_safra),
    dict(n=13, key="13_saude", title="Hub Saúde",
         axis="vertical do cooperado (saúde)",
         problem="Saúde aparece em ‘experiências’ mas sem profundidade: faltam "
                 "consultas, exames e farmácia com pontos.",
         approach=["Vertical Saúde: consultas, exames, farmácia",
                   "Agendamento pagando com pontos",
                   "Telemedicina 24h pelo app",
                   "Rede credenciada perto de você"],
         outcome="Cuida do cooperado e da família — benefício de saúde que "
                 "aprofunda o vínculo além de comprar produto.",
         ai="IA sugere a especialidade pelos sintomas descritos e encontra o "
            "horário/credenciado ideal por proximidade.",
         refactors="experiência Saúde  ·  /saude",
         draw=p_saude),
    dict(n=14, key="14_cooperados", title="Produtos dos Cooperados",
         axis="economia cooperativa",
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
    dict(n=15, key="15_economia", title="Economia local",
         axis="economia circular local",
         problem="Comprar no Coopera parece igual a comprar em qualquer e-commerce "
                 "— some o efeito de girar a economia da região.",
         approach=["Mapa de cooperados num raio perto de você",
                   "Mostra quanto do valor fica na sua cidade",
                   "Produtores locais com origem e distância",
                   "Pontos por comprar de quem é da região"],
         outcome="Transforma consumo em pertencimento territorial — comprar vira "
                 "fortalecer a própria comunidade.",
         ai="IA conecta sua demanda a cooperados próximos e prevê o impacto "
            "econômico local de cada compra.",
         refactors="marketplace  ·  /economia-local",
         draw=p_economia),
    dict(n=16, key="16_doacoes", title="Doações votadas",
         axis="propósito / assembleia",
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
    dict(n=17, key="17_statement", title="Extrato auditável",
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
    dict(n=18, key="18_status", title="Status de resgate",
         axis="pós-compra / garantia",
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
    dict(n=19, key="19_checkout", title="Checkout pontos + PIX",
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
