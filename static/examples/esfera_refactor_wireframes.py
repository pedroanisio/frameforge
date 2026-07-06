#!/usr/bin/env python3
"""Twenty distinct refactor proposals for the Esfera (Santander) rewards website
— composed as low-fidelity wireframes with the FrameGraph Python SDK, plus an
"AI na jornada" capstone mapping AI capabilities across the funnel.

Grounded in the *live* site (esfera.com.vc, probed June 2026 via Playwright): a
shop-first home that interleaves earning (Juntar pontos / cashback) and redeeming
(Trocar pontos), a header mega-menu crammed with dozens of partner logos, a red
points-tier strip (1.000–30.000 pts), best-sellers, partner cashback, exclusive
discounts and "Experiências" — with no personal points cockpit, no tier/status,
and travel buried as a category.

Each of the 10 proposals re-shapes that IA along a DIFFERENT real axis (not a
reskin): account-centric home, earn/redeem mode split, goal planning, faceted
partner directory, unified search, a promoted travel vertical, a redemption
checkout flow, gamified status, a mobile bottom-nav shell, and an algorithmic
feed. Every page pairs a concept rail (problem → approach → outcome) with a
minimal grayscale wireframe; one red accent marks the new/active idea.

Run from the repository root::

    uv run python examples/esfera_refactor_wireframes.py
"""
from __future__ import annotations

import os
import sys
import textwrap

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
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

# ---- frame + palette (wireframe: grayscale + one Esfera-red accent) -------- #
W, H = 1440, 980
RAIL_X, RAIL_W = 32, 366          # concept-explanation rail
MX = 430                          # mockup region left edge
MW = W - MX - 32                  # mockup region width
TOP = 86                          # below the deck band
BODY_H = H - TOP - 32
CANVAS = {"size": [W, H], "units": "px"}

COLORS = {
    "paper":  "#FFFFFF",
    "canvas": "#F4F5F7",
    "rail":   "#FBFAF9",
    "ink":    "#191613",
    "sub":    "#55585E",
    "muted":  "#9499A1",
    "faint":  "#BCC1C8",
    "fill":   "#EEF0F2",
    "fill2":  "#E3E6EA",
    "bar":    "#CBD0D6",
    "barlt":  "#DFE3E8",
    "line":   "#D8DCE1",
    "rowalt": "#F7F8FA",
    # single accent — Santander / Esfera red, used sparingly to mark the new idea
    "red":    "#E30613",
    "redSft": "#FCE7E8",
    "redDk":  "#9F161E",
    "good":   "#3F7A52",
    "goodSft":"#E6F1EA",
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
    # wireframe component text
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
#  component vocabulary
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


# ---- a tiny browser frame so each mock reads as "a page" ------------------ #
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
    return [x, y + 34, w, h - 34]          # inner content region


def site_header(page, region, *, active="Pontos", search="O que você procura?"):
    """The reusable Esfera top chrome inside a browser content region."""
    x, y, w, _ = region
    page.rect([x, y, w, 78], fill="paper")
    page.rect([x, y + 78, w, 1], fill="line")
    icon(page, [x + 18, y + 14, 24, 24], "◉", fill="red", style="glyphW", radius=12)
    T(page, [x + 50, y + 18, 110, 18], "Esfera", style="logo")
    util = ["Dia a dia", "Trocar", "Juntar", "Ajuda", "Entrar"]
    ux = x + w - 24
    for t in reversed(util):
        tw = 14 + len(t) * 6.6
        ux -= tw + 8
        T(page, [ux, y + 12, tw, 14], t, style="mut")
    circle(page, x + w - 30, y + 19, 9, fill="fill", stroke="line")
    # primary tabs + search
    tabs(page, [x + 50, y + 40, 220, 32], ["Pontos", "Descontos"],
         active=0 if active == "Pontos" else 1)
    pill(page, [x + 300, y + 42, w - 340, 28], None, fill="canvas", stroke="line",
         radius=8)
    T(page, [x + 314, y + 49, w - 380, 14], "⌕  " + search, style="place")
    return [x, y + 78, w, region[3] - 78]


# ======================================================================= #
#  concept scaffold — rail (problem→approach→outcome) + deck band
# ======================================================================= #
PALETTE_AXES = {}


def concept(b, *, n, key, title, axis, problem, approach, outcome, refactors,
            ai, draw):
    page = b.page(key, canvas=CANVAS, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")

    # deck band
    page.rect([0, 0, W, 4], fill="red")
    T(page, [32, 22, 400, 18], "Esfera · Reframe", style="band")
    T(page, [32, 44, 400, 14],
              "Refatorações distintas do site de recompensas", style="bandMut")
    T(page, [W - 432, 22, 400, 16],
              f"PROPOSTA {n:02d} / 20", style="bandR")
    T(page, [W - 432, 44, 400, 14], "Wireframe · baixa fidelidade",
              style=dict(font_family=MONO, font_size=11, color="muted", align="right"))

    # ---- concept rail ---- #
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
    # axis chip
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

    # ---- AI-on-the-journey callout (threaded through every proposal) ---- #
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

    # footer: what it restructures
    page.rect([rx, rail[1] + rail[3] - 64, rw, 1], fill="line")
    T(page, [rx, rail[1] + rail[3] - 50, rw, 13], "REFATORA", style="lbl")
    T(page, [rx, rail[1] + rail[3] - 32, rw, 14], refactors, style="foot")

    # ---- the wireframe mockup ---- #
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
#  00 — index / current-state teardown + proposal map
# ======================================================================= #
def index(b):
    page = b.page("00_index", canvas=CANVAS, coordinate_mode="absolute").layer("bg")
    page.rect([0, 0, W, H], fill="canvas")
    page.rect([0, 0, W, 4], fill="red")
    T(page, [32, 26, 1000, 30], "Esfera — 20 refatorações do site de recompensas",
              style=dict(font_family=SANS, font_size=26, font_weight=800,
                         color="ink", letter_spacing=-0.6))
    T(page, [32, 62, 1000, 18],
              "Cada proposta reestrutura a arquitetura de informação por um eixo "
              "diferente — não é re-skin. Wireframe de baixa fidelidade.",
              style="body")
    pill(page, [32, 92, 168, 24], "ANÁLISE · esfera.com.vc", fill="redSft",
         style="chipA")
    pill(page, [208, 92, 180, 24], "Sondado via Playwright", fill="fill",
         style="chip")
    pill(page, [396, 92, 230, 24], "Pesquisa loyalty UX 2026", fill="fill",
         style="chip")

    # ---- left: as-is teardown + research-grounded principles ---- #
    page.layer("asis")
    tear = [32, 130, 384, H - 130 - 40]
    card(page, tear, fill="paper")
    tx, ty, tw, _ = inset(tear, 20)
    T(page, [tx, ty, tw, 16], "COMO É HOJE", style="lbl")
    T(page, [tx, ty + 20, tw, 20], "Home orientada à loja", style="h1")
    asis = [
        ("Mega-menu", "dezenas de logos no cabeçalho"),
        ("Juntar × Trocar", "ganhar e gastar misturados"),
        ("Sem painel", "saldo, validade e nível invisíveis"),
        ("Valor opaco", "não se sabe quanto vale 1 ponto"),
        ("Pontos não pontuam", "dor nº 1 no Reclame Aqui"),
        ("Viagens escondida", "enterrada em ‘Categorias’"),
    ]
    iy = ty + 48
    for k, v in asis:
        page.rect([tx, iy, 4, 28], fill="red", radius=2)
        T(page, [tx + 14, iy, tw - 14, 14], k, style="h3")
        T(page, [tx + 14, iy + 15, tw - 14, 13], _wrap(v, 44), style="mut")
        iy += 38
    # research principles strip
    page.rect([tx, iy + 4, tw, 1], fill="line")
    T(page, [tx, iy + 16, tw, 14], "PRINCÍPIOS (PESQUISA 2026)", style="lbl")
    princ = [
        "Resgate sem atrito (1 clique)",
        "Valor do ponto sempre visível",
        "Combater breakage (~30% vence)",
        "Micro-resgates criam hábito",
        "Hiper-personalização por IA",
        "Gamificação com base comportamental",
    ]
    py = iy + 38
    for p in princ:
        circle(page, tx + 6, py + 6, 5, fill="red")
        T(page, [tx + 18, py, tw - 18, 14], p, style="td")
        py += 26

    # ---- right: 20-proposal map (2 cols × 10 rows, compact) ---- #
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
            # AI marker on AI-forward proposals
            if num in AI_FORWARD:
                badge(page, [cb[0] + cb[2] - 52, cb[1] + rh / 2 - 10, 40, 20],
                      "✦ IA", "red")


AI_FORWARD = {5, 10, 13, 15}  # proposals where AI is the load-bearing mechanism

PROPOSALS = [
    (1, "Cockpit de pontos", "home centrada na conta"),
    (2, "Modo Juntar ⇄ Trocar", "modelo de navegação"),
    (3, "Planejador por metas", "tarefa / aspiração"),
    (4, "Diretório de parceiros", "layout (facetas)"),
    (5, "Busca unificada", "IA orientada à busca"),
    (6, "Hub de Viagens", "profundidade de vertical"),
    (7, "Carrinho de resgate", "fluxo / checkout"),
    (8, "Níveis & missões", "gamificação / status"),
    (9, "Mobile bottom-nav", "fator de forma"),
    (10, "Feed personalizado", "conteúdo algorítmico"),
    (11, "Valor do ponto", "transparência de preço"),
    (12, "Central de validade", "ciclo de vida / breakage"),
    (13, "Extrato auditável", "confiança / rastreio"),
    (14, "Esfera+ assinatura", "modelo de negócio"),
    (15, "Concierge IA", "interação conversacional"),
    (16, "Micro-resgates", "gratificação imediata"),
    (17, "Doar pontos", "propósito / valores"),
    (18, "Esfera na loja", "canal online ↔ offline"),
    (19, "Surpresa & desafios", "recompensa variável"),
    (20, "Como funciona", "compreensão / clareza"),
]


# ======================================================================= #
#  01 — points-first cockpit home
# ======================================================================= #
def p01_cockpit(page):
    region = browser(page, "esfera.com.vc/  ·  conta")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)

    # balance hero
    hero = [x, y, w, 132]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 20)
    T(page, [hx, hy, 200, 14],
              "SEU SALDO", style=dict(font_family=SANS, font_size=10.5,
                                      font_weight=700, color="faint",
                                      letter_spacing=1.2))
    T(page, [hx, hy + 18, 300, 40], "48.250 pts",
              style=ts(34, 800, "paper", letter_spacing=-1))
    T(page, [hx, hy + 64, 360, 14],
              "↘ 1.200 pts expiram em 21 dias",
              style=ts(12, 600, "redSft"))
    button(page, [hx + hw - 150, hy + 4, 150, 32], "Comprar pontos", "primary")
    button(page, [hx + hw - 150, hy + 44, 150, 32], "Transferir", "ghost")

    # quick-actions row
    qy = y + 148
    acts = [("↑", "Juntar"), ("↓", "Trocar"), ("✈", "Viagens"), ("%", "Descontos"),
            ("★", "Experiências")]
    for (g, t), cb in zip(acts, row([x, qy, w, 72], count=5, gap=12)):
        card(page, cb, fill="canvas")
        cx = cb[0] + cb[2] / 2
        icon(page, [cx - 16, cb[1] + 12, 32, 32], g, fill="paper", style="glyphR")
        T(page, [cb[0], cb[1] + 48, cb[2], 14], t, style="ctr")

    # two cards: ready to redeem + activity
    ry = qy + 88
    left, right = row([x, ry, w, body[3] - (ry - body[1]) - 18], gap=16,
                      weights=[1.7, 1])
    card(page, left)
    lx, ly, lw, _ = inset(left, 16)
    T(page, [lx, ly, lw - 80, 16], "Pronto pra resgatar com seu saldo", style="h2")
    T(page, [lx + lw - 70, ly + 1, 70, 14], "Ver tudo ›", style="chipA")
    for cb in grid([lx, ly + 28, lw, left[3] - 60], cols=4, rows=2, gap=12):
        product(page, cb, "Produto", "12.000 pts")

    card(page, right)
    sx, sy, sw, _ = inset(right, 16)
    T(page, [sx, sy, sw, 16], "Atividade", style="h2")
    rows = [("+ 320", "Compra Magalu", "good"), ("− 12.000", "Gift Outback", "red"),
            ("+ 1.500", "Transferência", "good"), ("+ 90", "Cashback Renner", "good"),
            ("− 2.000", "Desconto Petz", "red")]
    ay = sy + 28
    for amt, lbl, tone in rows:
        circle(page, sx + 8, ay + 9, 4, fill=_TONE[tone][1])
        T(page, [sx + 22, ay, sw - 100, 14], lbl, style="td")
        T(page, [sx + sw - 90, ay, 90, 14], amt + " pts",
                  style=dict(font_family=MONO, font_size=11, color=_TONE[tone][1],
                             align="right"))
        ay += 30


# ======================================================================= #
#  02 — earn ⇄ redeem mode shell
# ======================================================================= #
def p02_modes(page):
    region = browser(page, "esfera.com.vc/  ·  alterna modo")
    x, y, w, _ = inset(region, 18)
    # a big mode switch replaces the Pontos/Descontos tabs
    T(page, [x, y, 300, 18], "◉ Esfera", style="logo")
    seg = [x + w / 2 - 220, y - 4, 440, 40]
    page.rect(seg, fill="fill", radius=20)
    page.rect([seg[0], seg[1], seg[2] / 2, seg[3]], fill="red", radius=20)
    T(page, [seg[0], seg[1] + 12, seg[2] / 2, 16], "↑  JUNTAR pontos",
              style="btn")
    T(page, [seg[0] + seg[2] / 2, seg[1] + 12, seg[2] / 2, 16], "↓  TROCAR pontos",
              style=ts(12, 700, "sub", align="center"))
    T(page, [x + w - 120, y, 120, 16], "Saldo 48.250", style="pts")
    page.rect([x, y + 50, w, 1], fill="line")

    # split: the chosen mode fills the canvas, the other is a peeking drawer
    main = [x, y + 66, w - 150, region[3] - 66 - 36]
    T(page, [main[0], main[1], 400, 18], "Modo JUNTAR — como ganhar pontos",
              style="h1")
    T(page, [main[0], main[1] + 24, 500, 14],
              "Tudo que aumenta seu saldo, em um só lugar.", style="mut")
    lanes = [("Comprar nas parceiras", "cashback em pontos · 1–8 pts/R$"),
             ("Transferir do banco", "bônus de até 120%"),
             ("Comprar pontos", "a partir de R$ 30"),
             ("Cartão Santander", "pontos por gasto recorrente")]
    ly = main[1] + 52
    for ttl, sub in lanes:
        lane = [main[0], ly, main[2], 64]
        card(page, lane, fill="canvas")
        icon(page, [lane[0] + 14, ly + 16, 32, 32], "↑", fill="paper", style="glyphR")
        T(page, [lane[0] + 60, ly + 14, lane[2] - 200, 16], ttl, style="h2")
        T(page, [lane[0] + 60, ly + 34, lane[2] - 200, 14], sub, style="mut")
        button(page, [lane[0] + lane[2] - 130, ly + 18, 112, 28], "Explorar", "ghost")
        ly += 76

    # the other mode as a thin peeking drawer on the right
    drawer = [x + w - 130, y + 66, 130, region[3] - 66 - 36]
    page.rect(drawer, fill="ink", radius=12)
    page.rect([drawer[0], drawer[1], 26, drawer[3]], fill="ink", radius=12)
    T(page, [drawer[0] + 16, drawer[1] + 20, 100, 200], "↓\n\nT\nR\nO\nC\nA\nR",
              style=ts(13, 800, "paper", line_height=1.5))
    T(page, [drawer[0] + 44, drawer[1] + drawer[3] - 40, 80, 30],
              "deslize\n‹", style=ts(10, 600, "faint", line_height=1.3))


# ======================================================================= #
#  03 — goal-based aspiration planner
# ======================================================================= #
def p03_goals(page):
    region = browser(page, "esfera.com.vc/minhas-metas")
    body = site_header(page, region, search="Qual é o seu próximo objetivo?")
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 20], "O que você quer conquistar?", style="h1")
    T(page, [x, y + 26, 600, 14],
              "Escolha uma meta — a Esfera traça o caminho de pontos.", style="mut")

    # goal chips
    goals = ["✈ Viagem", "📱 iPhone", "🎧 Fone", "🏨 Hotel", "🎟 Show", "+ Criar meta"]
    gx = x
    for i, gtxt in enumerate(goals):
        gw = 30 + len(gtxt) * 8
        pill(page, [gx, y + 54, gw, 30], gtxt,
             fill="red" if i == 0 else "fill",
             style="btn" if i == 0 else "chip", radius=15)
        gx += gw + 10

    # selected goal: progress + paths
    card(page, [x, y + 100, w, 150], fill="canvas")
    gx, gy, gw, _ = inset([x, y + 100, w, 150], 20)
    thumb(page, [gx, gy, 150, 110], "viagem")
    T(page, [gx + 168, gy, gw - 168, 18], "Meta: Viagem a Lisboa", style="h1")
    T(page, [gx + 168, gy + 26, gw - 168, 14],
              "Passagem ida e volta ≈ 90.000 pts", style="mut")
    T(page, [gx + 168, gy + 50, 200, 14], "Você tem 48.250 pts (54%)", style="pts")
    progressbar(page, [gx + 168, gy + 70, gw - 168, 12], 0.54)
    T(page, [gx + 168, gy + 92, gw - 168, 14],
              "Faltam 41.750 pts — chegue lá mais rápido:", style="h3")

    # fastest earn paths
    T(page, [x, y + 268, 300, 14], "CAMINHOS MAIS RÁPIDOS", style="lbl")
    paths = [("Transferir 30k do banco", "+72.000 pts c/ 120% bônus", "atalho"),
             ("Comprar nas parceiras", "≈ 6 semanas no ritmo atual", "constante"),
             ("Comprar pontos", "41.750 pts ≈ R$ 1.090", "imediato")]
    for (ttl, sub, tag), cb in zip(paths, row([x, y + 290, w, 96], count=3, gap=14)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 16)
        badge(page, [ix, iy, 30 + len(tag) * 7, 18], tag, "red")
        T(page, [ix, iy + 28, iw, 16], ttl, style="h2")
        T(page, [ix, iy + 48, iw, 14], sub, style="mut")


# ======================================================================= #
#  04 — faceted partner directory (kills the mega-menu)
# ======================================================================= #
def p04_directory(page):
    region = browser(page, "esfera.com.vc/parceiros")
    body = site_header(page, region, search="Buscar parceiro…")
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 500, 18], "Diretório de parceiros", style="h1")
    T(page, [x, y + 24, 600, 14],
              "Substitui o mega-menu: 180+ lojas, buscáveis e filtráveis.",
              style="mut")

    facet, results = row([x, y + 52, w, h - 52], gap=16, weights=[1, 3.4])
    # facet rail
    card(page, facet, fill="canvas")
    fx, fy, fw, _ = inset(facet, 14)
    T(page, [fx, fy, fw, 13], "CATEGORIA", style="lbl")
    cats = [("Tudo", True), ("Eletrônicos", False), ("Moda", False),
            ("Casa", False), ("Beleza", False), ("Mercado", False),
            ("Vinhos", False), ("Viagem", False)]
    cyy = fy + 22
    for label, on in cats:
        circle(page, fx + 7, cyy + 7, 6, fill="red" if on else "paper",
               stroke="faint")
        T(page, [fx + 22, cyy, fw - 22, 14], label,
                  style="td" if on else "mut")
        cyy += 26
    T(page, [fx, cyy + 8, fw, 13], "TIPO DE GANHO", style="lbl")
    for label in ["Cashback em pontos", "Desconto %", "Pontos por compra"]:
        page.rect([fx, cyy + 30, 14, 14], fill="paper", stroke="faint",
                  stroke_style=HAIR, radius=3)
        T(page, [fx + 22, cyy + 30, fw - 22, 14], label, style="mut")
        cyy += 26
    T(page, [fx, cyy + 16, fw, 13], "ORDENAR · maior taxa", style="chipA")

    # results: sort bar + A–Z grid
    rx, ry, rw, rh = results
    pill(page, [rx, ry, 200, 28], "A–Z  ·  Maior cashback ▾", fill="paper",
         stroke="line", style="chip", radius=8)
    T(page, [rx + rw - 140, ry + 7, 140, 14], "184 parceiros", style="mut")
    names = ["Magalu", "Casas Bahia", "Amazon", "Natura", "Renner", "Fast Shop",
             "Petz", "Drogasil", "Nike", "Adidas", "Extra", "Boticário"]
    for nm, cb in zip(names, grid([rx, ry + 40, rw, rh - 40], cols=4, rows=3,
                                  gap=12)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 12)
        thumb(page, [ix, iy, iw, ih - 30], nm)
        T(page, [ix, iy + ih - 24, iw - 40, 14], nm, style="h3")
        T(page, [ix + iw - 40, iy + ih - 24, 40, 14], "5 pt", style="chipA")


# ======================================================================= #
#  05 — unified marketplace search
# ======================================================================= #
def p05_search(page):
    region = browser(page, "esfera.com.vc/busca?q=cafeteira")
    x, y, w, h = inset(region, 0)
    # prominent search bar replaces the chrome
    page.rect([x, y, w, 64], fill="ink")
    T(page, [x + 20, y + 22, 90, 20], "◉ Esfera", style=ts(15, 800, "paper"))
    pill(page, [x + 130, y + 16, w - 320, 32], None, fill="paper", radius=8)
    T(page, [x + 146, y + 24, w - 360, 16], "cafeteira", style="td")
    T(page, [x + w - 300, y + 24, 60, 16], "⌕", style="glyphW")
    T(page, [x + w - 170, y + 22, 150, 16], "Saldo 48.250 pts",
              style=ts(12, 700, "paper"))

    x, y = x + 18, y + 80
    w = w - 36
    facet, res = row([x, y, w, region[3] - 96], gap=16, weights=[1, 3.6])
    # facets across ALL inventory types
    card(page, facet, fill="canvas")
    fx, fy, fw, _ = inset(facet, 14)
    T(page, [fx, fy, fw, 13], "RESULTADOS EM", style="lbl")
    kinds = [("Produtos", "248", True), ("Viagens", "12", False),
             ("Experiências", "9", False), ("Gift cards", "31", False),
             ("Descontos", "54", False)]
    ky = fy + 22
    for lbl, n, on in kinds:
        if on:
            page.rect([fx - 4, ky - 4, fw + 8, 26], fill="redSft", radius=6)
        T(page, [fx, ky, fw - 40, 16], lbl, style="navA" if on else "mut")
        T(page, [fx + fw - 36, ky, 36, 16], n,
                  style="chipA" if on else "tiny")
        ky += 30
    T(page, [fx, ky + 10, fw, 13], "PREÇO (PONTOS)", style="lbl")
    progressbar(page, [fx, ky + 32, fw, 6], 0.5, fill="bar")
    circle(page, fx + fw * 0.5, ky + 35, 7, fill="paper", stroke="red")
    T(page, [fx, ky + 46, fw, 13], "até 48.250 (seu saldo)", style="chipA")
    T(page, [fx, ky + 74, fw, 13], "MARCA", style="lbl")
    for t in ["Mondial", "Philco", "Britânia"]:
        page.rect([fx, ky + 96, 14, 14], fill="paper", stroke="faint",
                  stroke_style=HAIR, radius=3)
        T(page, [fx + 22, ky + 96, fw, 14], t, style="mut")
        ky += 26

    # mixed result grid (type-tagged)
    rx, ry, rw, rh = res
    T(page, [rx, ry, 400, 14],
              "248 resultados · ✓ só o que cabe no seu saldo", style="mut")
    tags = ["Produto", "Viagem", "Gift", "Produto", "Experiência", "Produto",
            "Produto", "Gift", "Produto"]
    for tg, cb in zip(tags, grid([rx, ry + 24, rw, rh - 24], cols=3, rows=3,
                                 gap=12)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 12)
        thumb(page, [ix, iy, iw, ih - 42])
        badge(page, [ix, iy + 8, 24 + len(tg) * 6, 18], tg, "muted")
        T(page, [ix, iy + ih - 38, iw, 14], "Resultado", style="h3")
        T(page, [ix, iy + ih - 20, iw, 14], "12.000 pts", style="pts")


# ======================================================================= #
#  06 — travel hub vertical
# ======================================================================= #
def p06_travel(page):
    region = browser(page, "viagens.esfera.com.vc")
    x, y, w, _ = inset(region, 0)
    # travel sub-brand header
    page.rect([x, y, w, 60], fill="paper")
    page.rect([x, y + 60, w, 1], fill="line")
    T(page, [x + 20, y + 20, 220, 20], "Esfera ✈ Viagens", style="logo")
    for i, t in enumerate(["Passagens", "Hotéis", "Pacotes", "Carros", "Ônibus"]):
        T(page, [x + 230 + i * 92, y + 22, 90, 14], t,
                  style="navA" if i == 0 else "nav")
    T(page, [x + w - 150, y + 22, 130, 14], "48.250 pts", style="pts")

    # search hero (the booking widget — the whole point of the vertical)
    hero = [x, y + 60, w, 180]
    page.rect(hero, fill="canvas")
    thumb(page, [x, y + 60, w, 180], fill="fill2")
    panel = [x + 40, y + 96, w - 80, 108]
    card(page, panel, fill="paper")
    px, py, pw, _ = inset(panel, 16)
    T(page, [px, py, 300, 16], "Para onde vamos?", style="h2")
    cols = row([px, py + 26, pw - 130, 56], count=4, gap=10)
    for cb, lab, val in zip(cols, ["Origem", "Destino", "Datas", "Pessoas"],
                            ["GRU São Paulo", "LIS Lisboa", "12–22 set", "1 adulto"]):
        field(page, cb, lab, val)
    button(page, [px + pw - 116, py + 42, 116, 40], "Buscar", "primary")

    # results preview: flight rows w/ points + cash split
    ry = y + 260
    T(page, [x + 20, ry, 400, 16], "Voos · resgate com pontos + dinheiro",
              style="h2")
    flights = [("GRU → LIS", "TAP · direto · 11h", "90.000 pts", "ou R$ 1.180"),
               ("GRU → LIS", "LATAM · 1 parada", "78.000 pts", "+ R$ 240"),
               ("GRU → LIS", "Azul · 1 parada", "64.000 pts", "+ R$ 690")]
    fy = ry + 28
    for route, info, pts, cash in flights:
        lane = [x + 20, fy, w - 40, 56]
        card(page, lane)
        T(page, [lane[0] + 16, fy + 10, 160, 16], route, style="h2")
        T(page, [lane[0] + 16, fy + 32, 240, 14], info, style="mut")
        T(page, [lane[0] + lane[2] - 320, fy + 18, 150, 16], pts, style="pts")
        T(page, [lane[0] + lane[2] - 320, fy + 36, 150, 13], cash, style="mut")
        button(page, [lane[0] + lane[2] - 130, fy + 14, 112, 28], "Selecionar",
               "ghost")
        fy += 66


# ======================================================================= #
#  07 — redemption cart & checkout flow
# ======================================================================= #
def p07_checkout(page):
    region = browser(page, "esfera.com.vc/resgate/checkout")
    x, y, w, _ = inset(region, 18)
    # stepper
    steps = ["Carrinho", "Revisão", "Pagamento", "Pronto"]
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
    # line items
    T(page, [main[0], main[1], 300, 18], "Seu resgate (3 itens)", style="h1")
    items = [("Air Fryer Mondial 12L", "36.000 pts"),
             ("Gift Card Outback R$100", "10.000 pts"),
             ("Voucher Uber R$50", "5.000 pts")]
    iy = main[1] + 34
    for nm, pts in items:
        lane = [main[0], iy, main[2], 72]
        card(page, lane)
        thumb(page, [lane[0] + 12, iy + 12, 70, 48])
        T(page, [lane[0] + 96, iy + 14, lane[2] - 260, 16], nm, style="h2")
        T(page, [lane[0] + 96, iy + 36, 200, 14], "Entrega digital · imediata",
                  style="mut")
        T(page, [lane[0] + lane[2] - 150, iy + 26, 130, 16], pts, style="pts")
        T(page, [lane[0] + lane[2] - 150, iy + 46, 130, 13], "Remover",
                  style=ts(11, 600, "muted", align="right"))
        iy += 82

    # order summary w/ points+cash split slider
    card(page, side, fill="canvas")
    sxx, syy, sw, _ = inset(side, 18)
    T(page, [sxx, syy, sw, 16], "Resumo", style="h2")
    rows = [("Subtotal", "51.000 pts"), ("Seu saldo", "48.250 pts"),
            ("Faltam", "2.750 pts")]
    ry2 = syy + 30
    for k, v in rows:
        T(page, [sxx, ry2, sw - 120, 14], k, style="body")
        T(page, [sxx + sw - 120, ry2, 120, 14], v, style="right")
        ry2 += 26
    page.rect([sxx, ry2 + 4, sw, 1], fill="line")
    T(page, [sxx, ry2 + 16, sw, 14], "COMPLETAR COM DINHEIRO", style="lbl")
    progressbar(page, [sxx, ry2 + 38, sw, 12], 0.82)
    circle(page, sxx + sw * 0.82, ry2 + 44, 9, fill="paper", stroke="red")
    T(page, [sxx, ry2 + 58, sw, 14], "48.250 pts  +  R$ 71,50", style="pts")
    button(page, [sxx, ry2 + 88, sw, 42], "Finalizar resgate", "primary")
    T(page, [sxx, ry2 + 138, sw, 13], "🔒 pontos só debitados ao confirmar",
              style="tiny")


# ======================================================================= #
#  08 — tiered status & missions
# ======================================================================= #
def p08_status(page):
    region = browser(page, "esfera.com.vc/meu-nivel")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)

    # tier ladder hero
    hero = [x, y, w, 150]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 20)
    T(page, [hx, hy, 200, 14], "SEU NÍVEL",
              style=ts(10.5, 700, "faint", letter_spacing=1.2))
    T(page, [hx, hy + 18, 300, 30], "Prata", style=ts(28, 800, "paper"))
    T(page, [hx, hy + 56, 360, 14],
              "Faltam 8.000 pts no mês para Ouro", style=ts(12, 600, "redSft"))
    progressbar(page, [hx, hy + 78, hw - 220, 12], 0.6, track="warm" if False else "sub")
    tiers = ["Bronze", "Prata", "Ouro", "Black"]
    tx = hx + hw - 200
    for i, t in enumerate(tiers):
        on = i == 1
        circle(page, tx + i * 50, hy + 24, 13, fill="red" if on else "sub",
               stroke=None)
        T(page, [tx + i * 50 - 24, hy + 44, 48, 12], t,
                  style=ts(10, 700, "paper" if on else "faint", align="center"))
        if i < 3:
            page.rect([tx + i * 50 + 14, hy + 22, 22, 3], fill="sub")

    # perks per tier + missions
    perks, missions = row([x, y + 166, w, body[3] - 166 - 18], gap=16, weights=[1, 1])
    card(page, perks)
    pxx, pyy, pw, _ = inset(perks, 16)
    T(page, [pxx, pyy, pw, 16], "Benefícios por nível", style="h2")
    rows = [("Bônus de transferência", "20%", "40%", "60%"),
            ("Cashback extra", "—", "1pt", "2pt"),
            ("Frete em resgates", "—", "✓", "✓"),
            ("Gerente Esfera", "—", "—", "✓")]
    cols = row([pxx, pyy + 26, pw, 14], weights=[2, 1, 1, 1])
    for cb, lab in zip(cols, ["", "Prata", "Ouro", "Black"]):
        T(page, [cb[0], cb[1], cb[2], 14], lab, style="th")
    gy = pyy + 48
    for r in rows:
        cols = row([pxx, gy, pw, 18], weights=[2, 1, 1, 1])
        T(page, [cols[0][0], gy, cols[0][2], 14], r[0], style="td")
        for cb, v in zip(cols[1:], r[1:]):
            T(page, [cb[0], gy, cb[2], 14], v,
                      style=ts(12, 700, "red" if v not in ("—",) else "muted"))
        page.rect([pxx, gy + 24, pw, 1], fill="line")
        gy += 32

    card(page, missions)
    mxx, myy, mw, _ = inset(missions, 16)
    T(page, [mxx, myy, mw, 16], "Missões desta semana", style="h2")
    T(page, [mxx + mw - 80, myy + 1, 80, 14], "🔥 3 dias", style="chipA")
    ms = [("Compre em 2 parceiras", 0.5, "+500 pts"),
          ("Transfira 10k do banco", 0.0, "+1.000 pts"),
          ("Resgate 1 experiência", 1.0, "✓ feito"),
          ("Complete o perfil", 0.7, "+200 pts")]
    my = myy + 30
    for ttl, frac, rew in ms:
        T(page, [mxx, my, mw - 90, 14], ttl, style="td")
        T(page, [mxx + mw - 86, my, 86, 14], rew, style="chipA")
        progressbar(page, [mxx, my + 20, mw, 8], frac,
                    fill="good" if frac >= 1 else "red")
        my += 44


# ======================================================================= #
#  09 — mobile-first bottom-nav app shell
# ======================================================================= #
def p09_mobile(page):
    # three phones side by side inside the mock region
    phones = row([MX, TOP, MW, BODY_H], count=3, gap=28, pad=[10, 30])
    titles = ["Home / feed", "Juntar (scan)", "Conta / saldo"]
    for ph, ttl in zip(phones, titles):
        px, py, pw, phh = ph
        phh = min(phh, 760)
        page.rect([px, py, pw, phh], fill="ink", radius=26)
        sc = inset([px, py, pw, phh], [12, 10])
        page.rect(sc, fill="paper", radius=16)
        sx, sy, sw, sh = sc
        # status + header
        T(page, [sx + 14, sy + 10, sw - 28, 12], "9:41", style="tiny")
        T(page, [sx + sw - 70, sy + 10, 56, 12], "●●●  ▮",
          style=dict(font_family=SANS, font_size=9, color="muted", align="right"))
        T(page, [sx + 14, sy + 28, 120, 18], "◉ Esfera", style="h2")
        T(page, [sx + sw - 90, sy + 30, 78, 14], "48.250", style="pts")
        page.rect([sx + 14, sy + 54, sw - 28, 30], fill="fill", radius=8)
        T(page, [sx + 26, sy + 61, sw - 60, 14], "⌕  Buscar", style="place")
        T(page, [sx + 14, sy + 96, sw, 12], ttl.upper(), style="lbl")
        # body content sketch
        if "feed" in ttl:
            yy = sy + 116
            for _ in range(3):
                card(page, [sx + 14, yy, sw - 28, 96], fill="canvas")
                thumb(page, [sx + 22, yy + 8, sw - 44, 52])
                bars(page, [sx + 22, yy + 70, sw - 80, 0], n=1, h=8, last=1)
                yy += 106
        elif "scan" in ttl:
            page.rect([sx + 30, sy + 120, sw - 60, sw - 60], fill="canvas",
                      stroke="red", stroke_style=DASHR, radius=12)
            T(page, [sx, sy + 120 + (sw - 60) / 2 - 8, sw, 16],
                      "⛶ aponte p/ nota", style="glyph")
            for cb in row([sx + 14, sy + 140 + (sw - 60), sw - 28, 56], count=2,
                          gap=10):
                card(page, cb, fill="canvas")
        else:
            page.rect([sx + 14, sy + 116, sw - 28, 80], fill="ink", radius=12)
            T(page, [sx + 26, sy + 128, 120, 12], "SALDO",
                      style=ts(9, 700, "faint", letter_spacing=1))
            T(page, [sx + 26, sy + 142, 160, 24], "48.250 pts",
                      style=ts(20, 800, "paper"))
            for i in range(3):
                yy = sy + 210 + i * 44
                circle(page, sx + 26, yy + 8, 5, fill="red")
                T(page, [sx + 42, yy, sw - 70, 14], "Movimentação", style="td")
        # bottom tab bar
        bar_y = sy + sh - 52
        page.rect([sx, bar_y, sw, 52], fill="paper")
        page.rect([sx, bar_y, sw, 1], fill="line")
        tabsl = [("⌂", "Início"), ("↑", "Juntar"), ("↓", "Trocar"),
                 ("✈", "Viagens"), ("◉", "Conta")]
        for i, (g, lab) in enumerate(tabsl):
            cx = sx + sw * (i + 0.5) / 5
            on = (("feed" in ttl and i == 0) or ("scan" in ttl and i == 1)
                  or ("Conta" in ttl and i == 4))
            T(page, [cx - 16, bar_y + 8, 32, 16], g,
                      style="glyphR" if on else "glyph")
            T(page, [cx - 24, bar_y + 28, 48, 12], lab,
                      style=ts(9, 700, "red" if on else "muted", align="center"))


# ======================================================================= #
#  10 — personalized recommendation feed
# ======================================================================= #
def p10_feed(page):
    region = browser(page, "esfera.com.vc/  ·  feed pra você")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 400, 18], "Pra você, hoje", style="h1")
    T(page, [x, y + 24, 600, 14],
              "Ordem editorial fixa → feed algorítmico de cards mistos.",
              style="mut")

    # a masonry-ish feed: tagged cards of different intents
    feed = [
        ("EXPIRA", "1.200 pts vencem em 21 dias", "Resgate algo agora", "red"),
        ("PERTO", "Faltam 2k p/ a Air Fryer", "Você olhou 3×", "muted"),
        ("BÔNUS", "Transfira hoje: +120%", "Só até domingo", "red"),
        ("CASHBACK", "Magalu 8 pts/R$", "Dobro neste fim de semana", "muted"),
        ("MISSÃO", "Compre em 2 lojas", "+500 pts · 1 restante", "muted"),
        ("VIAGEM", "Lisboa por 64k pts", "Combina com sua meta", "red"),
        ("NÍVEL", "8k pts p/ Ouro", "Cashback extra te espera", "muted"),
        ("EXPERIÊNCIA", "Jantar-show -30%", "Perto de você", "muted"),
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
#  11 — points-value transparency ("quanto vale meu ponto")
# ======================================================================= #
def p11_value(page):
    region = browser(page, "esfera.com.vc/valor-dos-pontos")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    hero = [x, y, w, 96]
    page.rect(hero, fill="ink", radius=12)
    hx, hy, hw, _ = inset(hero, 20)
    T(page, [hx, hy, 360, 14], "SEUS 48.250 PTS VALEM, NO MELHOR USO",
      style=ts(10.5, 700, "faint", letter_spacing=1.2))
    T(page, [hx, hy + 18, 360, 34], "≈ R$ 1.496",
      style=ts(30, 800, "paper", letter_spacing=-1))
    T(page, [hx + hw - 230, hy + 6, 230, 14],
      "Cada ponto rende mais ou menos\nconforme onde você troca.",
      style=ts(12, 500, "faint", line_height=1.4, align="right"))

    left, right = row([x, y + 112, w, body[3] - 112 - 18], gap=16, weights=[1.2, 1])
    card(page, left)
    lx, ly, lw, _ = inset(left, 16)
    T(page, [lx, ly, lw, 16], "Valor por ponto, por tipo de troca", style="h2")
    methods = [("Viagens", 3.1, 1.0, "melhor"), ("Experiências", 2.4, 0.77, ""),
               ("Produtos", 2.6, 0.84, ""), ("Gift cards", 2.0, 0.65, ""),
               ("Desconto na fatura", 1.0, 0.32, "pior")]
    my = ly + 30
    for name, cents, frac, tag in methods:
        T(page, [lx, my, 200, 14], name, style="td")
        if tag:
            badge(page, [lx + 150, my - 1, 56, 18], tag,
                  "good" if tag == "melhor" else "red")
        T(page, [lx + lw - 70, my, 70, 14], f"{cents:.1f}¢", style="right")
        progressbar(page, [lx, my + 20, lw, 8], frac,
                    fill="good" if tag == "melhor" else
                    ("muted" if tag == "pior" else "red"))
        my += 44

    card(page, right)
    rx, ry, rw, _ = inset(right, 16)
    T(page, [rx, ry, rw, 16], "Melhores trocas pelo seu saldo", style="h2")
    best = [("Passagem GRU→LIS", "3,1¢/pt"), ("Diária hotel 5★", "2,9¢/pt"),
            ("Jantar-show", "2,6¢/pt"), ("Air Fryer 12L", "2,5¢/pt")]
    for (nm, v), cb in zip(best, [[rx, ry + 30 + i * 64, rw, 56] for i in range(4)]):
        card(page, cb, fill="canvas")
        thumb(page, [cb[0] + 10, cb[1] + 10, 56, 36])
        T(page, [cb[0] + 78, cb[1] + 12, cb[2] - 160, 16], nm, style="h3")
        badge(page, [cb[0] + cb[2] - 78, cb[1] + 18, 64, 20], v, "good")


# ======================================================================= #
#  12 — expiring-points rescue center (anti-breakage)
# ======================================================================= #
def p12_expiry(page):
    region = browser(page, "esfera.com.vc/a-vencer")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Seus pontos a vencer", style="h1")
    T(page, [x, y + 24, 600, 14],
      "30% dos pontos viram pó por validade. Aqui você nunca perde.", style="mut")

    # urgency timeline
    buckets = [("21 dias", "1.200 pts", 0.9, "red"),
               ("60 dias", "3.000 pts", 0.5, "red"),
               ("6 meses", "9.500 pts", 0.25, "muted"),
               ("Sem prazo", "34.550 pts", 0.05, "good")]
    for (when, amt, urg, tone), cb in zip(buckets,
                                          row([x, y + 52, w, 96], count=4, gap=14)):
        card(page, cb, fill="canvas")
        ix, iy, iw, _ = inset(cb, 14)
        circle(page, ix + 7, iy + 8, 6, fill=_TONE.get(tone, _TONE["muted"])[1])
        T(page, [ix + 20, iy, iw - 20, 14], "vence em " + when, style="mut")
        T(page, [ix, iy + 22, iw, 22], amt, style="kpiR" if tone == "red" else "kpi")
        progressbar(page, [ix, iy + 52, iw, 6], urg,
                    fill="red" if tone == "red" else "bar")

    # rescue suggestions sized to the soonest bucket
    T(page, [x, y + 168, 400, 14],
      "QUEIME OS 1.200 PTS QUE VENCEM EM 21 DIAS", style="lbl")
    micro = [("Voucher Uber R$5", "500 pts"), ("Cupom Drogasil", "300 pts"),
             ("Doar p/ ONG", "200 pts"), ("Crédito Spotify", "1.000 pts"),
             ("Gift Shopee R$10", "1.000 pts"), ("Desconto fatura", "qualquer")]
    for (nm, pts), cb in zip(micro, grid([x, y + 190, w, body[3] - 190 - 16],
                                         cols=3, rows=2, gap=14)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 14)
        icon(page, [ix, iy, 36, 36], "↺", fill="redSft", style="glyphR")
        T(page, [ix + 48, iy + 2, iw - 48, 16], nm, style="h3")
        T(page, [ix + 48, iy + 22, iw - 48, 14], pts, style="pts")
        button(page, [ix, iy + ih - 30, iw, 28], "Trocar 1-clique", "primary")


# ======================================================================= #
#  13 — auditable earning statement ("onde estão meus pontos")
# ======================================================================= #
def p13_statement(page):
    region = browser(page, "esfera.com.vc/extrato")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Onde estão meus pontos", style="h1")
    T(page, [x, y + 24, 640, 14],
      "Cada compra rastreada: pendente, creditada ou em análise — e contestável.",
      style="mut")

    # pending alert (the #1 Reclame Aqui complaint)
    alert = [x, y + 52, w, 46]
    page.rect(alert, fill="redSft", radius=8)
    page.rect([alert[0], alert[1], 4, alert[3]], fill="red", radius=2)
    T(page, [alert[0] + 18, alert[1] + 14, w - 200, 16],
      "⚠  Compra Magalu de R$ 320 ainda não pontuou (12 dias). Prazo: 30 dias.",
      style="h3")
    button(page, [alert[0] + w - 150, alert[1] + 9, 134, 28], "Contestar", "ghost")

    # statement table
    cols = ["Data", "Origem", "Valor", "Pontos", "Status"]
    cw = [1, 2.4, 1.1, 1.1, 1.3]
    tbl = [x, y + 112, w, body[3] - 112 - 16]
    page.rect([tbl[0], tbl[1], tbl[2], 34], fill="fill", radius=8)
    for cb, h in zip(row(tbl[:2] + [tbl[2], 34], weights=cw), cols):
        T(page, [cb[0] + 12, tbl[1] + 10, cb[2] - 12, 14], h, style="th")
    rows = [("14/jun", "Compra Magalu", "R$ 320", "+ 320", ("Pendente", "red")),
            ("12/jun", "Transferência banco", "—", "+ 30.000", ("Creditado", "good")),
            ("10/jun", "Cashback Renner", "R$ 90", "+ 90", ("Creditado", "good")),
            ("07/jun", "Compra Amazon", "R$ 540", "+ 540", ("Em análise", "muted")),
            ("03/jun", "Resgate Air Fryer", "—", "− 36.000", ("Concluído", "good")),
            ("01/jun", "Compra Fast Shop", "R$ 210", "+ 210", ("Creditado", "good"))]
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
#  14 — Esfera+ paid membership (benefit stacking)
# ======================================================================= #
def p14_membership(page):
    region = browser(page, "esfera.com.vc/esfera-mais")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Esfera+ — vale a pena assinar?", style="h1")
    T(page, [x, y + 24, 600, 14],
      "Modelo Prime: uma assinatura que empilha benefícios em todo o programa.",
      style="mut")

    plans = row([x, y + 56, w, body[3] - 56 - 16], gap=20, weights=[1, 1])
    perks = [
        ("Bônus de transferência", "20%", "até 60%"),
        ("Cashback nas parceiras", "1×", "2×"),
        ("Frete grátis em resgates", "—", "✓"),
        ("Validade dos pontos", "12 meses", "nunca expira"),
        ("Acesso antecipado a ofertas", "—", "✓"),
        ("Concierge de viagens", "—", "✓"),
    ]
    for idx, (pb, head, price, accent) in enumerate([
            (plans[0], "Grátis", "R$ 0", False),
            (plans[1], "Esfera+", "R$ 19/mês", True)]):
        card(page, pb, fill="ink" if accent else "paper",
             stroke="red" if accent else "line")
        px, py, pw, _ = inset(pb, 22)
        ink = "paper" if accent else "ink"
        if accent:
            badge(page, [px + pw - 90, py, 90, 22], "RECOMENDADO", "red")
        T(page, [px, py, pw, 22], head,
          style=ts(20, 800, ink, letter_spacing=-0.4))
        T(page, [px, py + 28, pw, 26], price,
          style=ts(24, 800, "red" if not accent else "paper"))
        gy = py + 70
        for label, free_v, plus_v in perks:
            val = plus_v if accent else free_v
            on = val not in ("—",)
            T(page, [px, gy, pw - 70, 14], label,
              style=ts(12, 500, ink if on else ("faint" if accent else "muted")))
            T(page, [px + pw - 90, gy, 90, 14], val,
              style=ts(12, 700, "red" if (accent and on) else
                       ("good" if on else "muted"), align="right"))
            page.rect([px, gy + 22, pw, 1],
                      fill="warm" if accent else "line")
            gy += 34
        button(page, [px, pb[1] + pb[3] - 56, pw, 40],
               "Assinar Esfera+" if accent else "Continuar grátis",
               "primary" if accent else "ghost")


# ======================================================================= #
#  15 — conversational AI concierge
# ======================================================================= #
def p15_concierge(page):
    region = browser(page, "esfera.com.vc/concierge")
    x, y, w, h = inset(region, 0)
    page.rect([x, y, w, 52], fill="ink")
    icon(page, [x + 16, y + 12, 28, 28], "✦", fill="red", style="glyphW", radius=14)
    T(page, [x + 54, y + 16, 300, 20], "Concierge Esfera", style=ts(15, 800, "paper"))
    T(page, [x + w - 170, y + 18, 150, 16], "Saldo 48.250 pts",
      style=ts(12, 700, "paper"))

    chat, side = row([x, y + 52, w, region[3] - 52], gap=0, weights=[2.5, 1])
    cx, cy, cw, ch = inset(chat, 20)
    # user bubble
    ub = [cx + cw - 360, cy, 360, 44]
    page.rect(ub, fill="redSft", radius=12)
    T(page, [ub[0] + 16, ub[1] + 14, ub[2] - 32, 16],
      "quero um presente de aniversário até 12 mil pontos", style="td")
    # assistant bubble + inline product chips
    ay = cy + 60
    page.rect([cx, ay, cw - 80, 48], fill="fill", radius=12)
    T(page, [cx + 16, ay + 9, cw - 120, 32],
      "Achei 3 opções com ótimo valor por ponto. Quer que eu já\nadicione ao "
      "carrinho?", style="body")
    ay += 64
    picks = [("Fone JBL", "11.000 pts"), ("Kindle", "12.000 pts"),
             ("Gift Outback R$120", "9.800 pts")]
    for nm, pts in picks:
        chip = [cx, ay, cw - 80, 56]
        card(page, chip)
        thumb(page, [chip[0] + 10, chip[1] + 10, 56, 36])
        T(page, [chip[0] + 78, chip[1] + 12, 200, 16], nm, style="h3")
        T(page, [chip[0] + 78, chip[1] + 32, 160, 14], pts, style="pts")
        button(page, [chip[0] + chip[2] - 120, chip[1] + 14, 104, 28],
               "Adicionar", "ghost")
        ay += 66
    # composer
    comp = [cx, chat[1] + chat[3] - 70, cw, 44]
    page.rect(comp, fill="paper", stroke="line", stroke_style=HAIR, radius=22)
    T(page, [comp[0] + 18, comp[1] + 14, cw - 80, 16],
      "Pergunte qualquer coisa sobre seus pontos…", style="place")
    circle(page, comp[0] + cw - 24, comp[1] + 22, 16, fill="red")
    T(page, [comp[0] + cw - 40, comp[1] + 13, 32, 18], "↑", style="glyphW")
    # quick intents
    page.rect(side, fill="canvas")
    sx, sy, sw, _ = inset(side, 16)
    T(page, [sx, sy, sw, 14], "ATALHOS", style="lbl")
    for i, q in enumerate(["O que vence primeiro?", "Quanto pra Lisboa?",
                           "Melhor uso do saldo", "Resgatar gift card",
                           "Comparar 2 produtos"]):
        pill(page, [sx, sy + 26 + i * 40, sw, 32], q, fill="paper", stroke="line",
             style="chip", radius=8)


# ======================================================================= #
#  16 — micro-redemptions & instant rewards
# ======================================================================= #
def p16_micro(page):
    region = browser(page, "esfera.com.vc/troca-rapida")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 18], "Troca rápida — resgate em 1 toque", style="h1")
    T(page, [x, y + 24, 640, 14],
      "Poucos pontos, entrega instantânea. Resgatar vira hábito, não evento raro.",
      style="mut")
    pill(page, [x, y + 52, 150, 26], "✓ entrega na hora", fill="goodSft",
         style=dict(font_family=SANS, font_size=11, font_weight=700, color="good"))
    pill(page, [x + 160, y + 52, 150, 26], "a partir de 200 pts", fill="fill",
         style="chip")

    items = [("Uber", "R$ 5", "500 pts"), ("Spotify", "1 mês", "1.000 pts"),
             ("iFood", "R$ 10", "1.000 pts"), ("Doação", "R$ 2", "200 pts"),
             ("Shopee", "R$ 10", "1.000 pts"), ("PlayStation", "R$ 20", "2.000 pts"),
             ("Cupom Drogasil", "15%", "300 pts"), ("Crédito celular", "R$ 15",
              "1.500 pts")]
    for (brand, denom, pts), cb in zip(items, grid([x, y + 92, w,
                                                    body[3] - 92 - 16],
                                                   cols=4, rows=2, gap=14)):
        card(page, cb)
        ix, iy, iw, ih = inset(cb, 14)
        thumb(page, [ix, iy, iw, ih - 70], brand)
        T(page, [ix, iy + ih - 64, iw, 16], brand + " · " + denom, style="h3")
        T(page, [ix, iy + ih - 44, iw, 14], pts, style="pts")
        button(page, [ix, iy + ih - 26, iw, 26], "Trocar agora", "primary")


# ======================================================================= #
#  17 — donate points / social impact
# ======================================================================= #
def p17_donate(page):
    region = browser(page, "esfera.com.vc/doar")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Doe seus pontos", style="h1")
    T(page, [x, y + 24, 640, 14],
      "Pontos que vencem viram impacto. Micro-doação queima saldo e gera valor.",
      style="mut")

    causes = [("Educação", "Bolsas p/ jovens", 0.72, "1,2 mi pts"),
              ("Combate à fome", "Cestas básicas", 0.54, "860 mil pts"),
              ("Saúde infantil", "Hospitais", 0.38, "540 mil pts"),
              ("Clima", "Reflorestamento", 0.61, "910 mil pts")]
    for (ttl, sub, frac, raised), cb in zip(causes,
                                            row([x, y + 56, w, 200], count=2,
                                                gap=16)[:2] +
                                            row([x, y + 268, w, 200], count=2,
                                                gap=16)[:2]):
        cb = [cb[0], cb[1], cb[2], 188]
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 16)
        thumb(page, [ix, iy, 110, 110], "foto")
        T(page, [ix + 126, iy, iw - 126, 16], ttl, style="h2")
        T(page, [ix + 126, iy + 22, iw - 126, 14], sub, style="mut")
        progressbar(page, [ix + 126, iy + 48, iw - 126, 10], frac, fill="good")
        T(page, [ix + 126, iy + 64, iw - 126, 14],
          f"{int(frac*100)}% · {raised} arrecadados", style="chipA")
        for j, amt in enumerate(["200 pts", "1.000 pts", "5.000 pts"]):
            pill(page, [ix + 126 + j * 92, iy + 88, 84, 28], amt, fill="fill",
                 style="chip", radius=8)
        button(page, [ix + 126, iy + 124, iw - 126, 30], "Doar agora", "primary")


# ======================================================================= #
#  18 — omnichannel in-store (wallet pass + near me)
# ======================================================================= #
def p18_omni(page):
    region = browser(page, "esfera.com.vc/na-loja")
    body = site_header(page, region)
    x, y, w, h = inset(body, 18)
    T(page, [x, y, 500, 18], "Esfera na loja física", style="h1")
    T(page, [x, y + 24, 640, 14],
      "Ganhe e use pontos no balcão: carteira digital + ofertas perto de você.",
      style="mut")

    passcol, near = row([x, y + 56, w, h - 56], gap=16, weights=[1, 1.4])
    # wallet pass
    page.rect(passcol, fill="ink", radius=14)
    pxx, pyy, pw, _ = inset(passcol, 22)
    T(page, [pxx, pyy, pw, 14], "CARTEIRA ESFERA",
      style=ts(10.5, 700, "faint", letter_spacing=1.4))
    T(page, [pxx, pyy + 20, pw, 18], "Pedro A. · Prata",
      style=ts(16, 800, "paper"))
    T(page, [pxx, pyy + 48, pw, 24], "48.250 pts",
      style=ts(22, 800, "paper"))
    # QR placeholder
    qr = [pxx, pyy + 92, 120, 120]
    page.rect(qr, fill="paper", radius=10)
    for gx in range(5):
        for gy in range(5):
            if (gx + gy) % 2 == 0:
                page.rect([qr[0] + 14 + gx * 18, qr[1] + 14 + gy * 18, 16, 16],
                          fill="ink", radius=2)
    T(page, [pxx + 140, pyy + 110, pw - 140, 14],
      "Mostre no caixa para\njuntar ou usar pontos\nna hora.",
      style=ts(12, 500, "faint", line_height=1.5))
    pill(page, [pxx, passcol[1] + passcol[3] - 56, pw, 34],
         "＋ Adicionar à Apple / Google Wallet", fill="warm", style="btn",
         radius=8)

    # near-me list
    card(page, near, fill="canvas")
    nx, ny, nw, _ = inset(near, 16)
    T(page, [nx, ny, nw - 90, 16], "Parceiros perto de você", style="h2")
    T(page, [nx + nw - 86, ny + 1, 86, 14], "◉ Mapa", style="chipA")
    shops = [("Drogasil", "Av. Paulista, 900", "120 m", "3% em pts"),
             ("Casas Bahia", "Shopping Center 3", "450 m", "1 pt/R$"),
             ("Petz", "R. Augusta, 1200", "800 m", "5% em pts"),
             ("Fast Shop", "Shopping Pátio", "1,1 km", "2 pt/R$")]
    for (nm, addr, dist, rate), cb in zip(shops,
                                          [[nx, ny + 32 + i * 62, nw, 54]
                                           for i in range(4)]):
        card(page, cb)
        icon(page, [cb[0] + 12, cb[1] + 11, 32, 32], "▤", fill="paper")
        T(page, [cb[0] + 56, cb[1] + 10, cb[2] - 200, 16], nm, style="h3")
        T(page, [cb[0] + 56, cb[1] + 30, cb[2] - 200, 14], addr, style="mut")
        T(page, [cb[0] + cb[2] - 140, cb[1] + 10, 60, 14], dist, style="td")
        badge(page, [cb[0] + cb[2] - 78, cb[1] + 16, 64, 20], rate, "good")


# ======================================================================= #
#  19 — surprise & challenges (variable reward)
# ======================================================================= #
def p19_surprise(page):
    region = browser(page, "esfera.com.vc/jogar")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 500, 18], "Gire, jogue e ganhe", style="h1")
    T(page, [x, y + 24, 640, 14],
      "Recompensa variável: o que mais fideliza é a surpresa, não só o previsível.",
      style="mut")

    spin, box = row([x, y + 56, w, 250], gap=16, weights=[1, 1])
    # spin wheel
    card(page, spin, fill="ink")
    scx, scy = spin[0] + 150, spin[1] + spin[3] / 2
    for r, fl in [(96, "warm"), (72, "red"), (48, "warm"), (10, "paper")]:
        circle(page, scx, scy, r, fill=fl)
    for ang in range(0, 360, 45):
        import math as _m
        T(page, [scx + int(60 * _m.cos(_m.radians(ang))) - 20,
                 scy + int(60 * _m.sin(_m.radians(ang))) - 8, 40, 16],
          "100", style=ts(10, 700, "paper", align="center"))
    T(page, [scx - 10, scy - 110, 20, 16], "▼", style="glyphR")
    T(page, [spin[0] + 300, scy - 50, spin[2] - 320, 18], "Giro diário grátis",
      style=ts(16, 800, "paper"))
    T(page, [spin[0] + 300, scy - 24, spin[2] - 320, 14],
      "Pontos, cupons ou um\nprêmio surpresa por dia.",
      style=ts(12, 500, "faint", line_height=1.4))
    button(page, [spin[0] + 300, scy + 24, 150, 38], "Girar agora", "primary")

    # mystery box
    card(page, box)
    bxx, byy, bw, _ = inset(box, 18)
    T(page, [bxx, byy, bw, 16], "Caixa surpresa", style="h2")
    for cb in row([bxx, byy + 30, bw, 130], count=3, gap=14):
        ghost(page, cb, "?", radius=12)
        T(page, [cb[0], cb[1] + cb[3] / 2 - 14, cb[2], 28], "🎁",
          style=ts(24, 700, "muted", align="center"))
    T(page, [bxx, byy + 168, bw, 14], "Abra 1 por semana ao bater uma missão",
      style="mut")

    # seasonal challenge ladder
    T(page, [x, y + 322, 400, 14], "DESAFIO DE INVERNO · 4 SEMANAS", style="lbl")
    steps = [("Semana 1", "Compre em 1 parceira", "✓", True),
             ("Semana 2", "Transfira pontos", "✓", True),
             ("Semana 3", "Resgate algo", "agora", False),
             ("Semana 4", "Indique um amigo", "🔒", False)]
    for (wk, task, state, done), cb in zip(steps,
                                           row([x, y + 344, w, 92], count=4,
                                               gap=14)):
        card(page, cb, fill="canvas" if not done else "goodSft")
        ix, iy, iw, _ = inset(cb, 14)
        T(page, [ix, iy, iw, 14], wk, style="lbl")
        T(page, [ix, iy + 20, iw, 30], task, style="h3")
        badge(page, [ix, iy + 52, 30 + len(state) * 8, 20], state,
              "good" if done else ("red" if state == "agora" else "muted"))


# ======================================================================= #
#  20 — plain-language explainer ("como funciona")
# ======================================================================= #
def p20_explainer(page):
    region = browser(page, "esfera.com.vc/como-funciona")
    body = site_header(page, region)
    x, y, w, _ = inset(body, 18)
    T(page, [x, y, 600, 20], "Como a Esfera funciona", style="h1")
    T(page, [x, y + 26, 640, 14],
      "Sem jargão: você junta pontos e troca por coisas. Só isso.", style="mut")

    # 1-2-3 steps
    steps = [("1", "Junte", "Comprando nas parceiras, transferindo do banco "
              "ou usando o cartão Santander."),
             ("2", "Acumule", "Seus pontos ficam na conta. A gente avisa antes "
              "de qualquer um vencer."),
             ("3", "Troque", "Por produtos, viagens, gift cards, descontos ou "
              "doações — do seu jeito.")]
    for (n, ttl, desc), cb in zip(steps, row([x, y + 56, w, 130], count=3,
                                             gap=16)):
        card(page, cb)
        ix, iy, iw, _ = inset(cb, 18)
        circle(page, ix + 18, iy + 18, 18, fill="redSft")
        T(page, [ix, iy + 8, 36, 22], n, style="kpiR")
        T(page, [ix + 48, iy + 6, iw - 48, 18], ttl, style="h1")
        T(page, [ix, iy + 44, iw, 60], _wrap(desc, 40), style="body")

    # two columns: ganhar vs trocar in plain language
    earn, redeem = row([x, y + 202, w, body[3] - 202 - 60], gap=16, weights=[1, 1])
    for col, head, glyph, ways in [
            (earn, "Formas de GANHAR", "↑",
             ["Comprar em 180+ lojas parceiras", "Transferir pontos do banco",
              "Gastar no cartão de crédito", "Cashback em promoções"]),
            (redeem, "Formas de TROCAR", "↓",
             ["Produtos e eletrônicos", "Viagens (voos, hotéis, carros)",
              "Gift cards e cupons", "Descontos na fatura · doações"])]:
        card(page, col, fill="canvas")
        ix, iy, iw, _ = inset(col, 18)
        icon(page, [ix, iy, 34, 34], glyph, fill="redSft", style="glyphR")
        T(page, [ix + 46, iy + 7, iw - 46, 18], head, style="h2")
        wy = iy + 50
        for wtext in ways:
            circle(page, ix + 7, wy + 7, 5, fill="red")
            T(page, [ix + 22, wy, iw - 22, 14], wtext, style="td")
            wy += 34

    # FAQ chips
    fy = body[1] + body[3] - 44
    T(page, [x, fy - 18, 200, 14], "DÚVIDAS FREQUENTES", style="lbl")
    fx = x
    for q in ["Meus pontos vencem?", "Quanto vale 1 ponto?", "Como cancelo?",
              "Posso juntar com a família?"]:
        qw = 24 + len(q) * 7
        pill(page, [fx, fy, qw, 28], q, fill="paper", stroke="line", style="chip",
             radius=8)
        fx += qw + 10


# ======================================================================= #
#  build
# ======================================================================= #
CONCEPTS = [
    dict(n=1, key="01_cockpit", title="Cockpit de pontos",
         axis="home centrada na conta",
         problem="A home vende produtos antes de mostrar quem é o cliente: saldo, "
                 "validade e nível ficam invisíveis.",
         approach=["Saldo + validade + nível no topo, como um painel",
                   "Ações rápidas: Juntar, Trocar, Viagens, Descontos",
                   "‘Pronto pra resgatar’ filtra pelo saldo real",
                   "Extrato de movimentação sempre à mão"],
         outcome="O cliente entende seu valor em 1 olhada e age — em vez de "
                 "navegar uma vitrine genérica.",
         ai="IA prevê quais resgates cabem no saldo e ranqueia o ‘pronto pra "
            "resgatar’ por afinidade — o painel se monta sozinho.",
         refactors="home  ·  /conta  ·  header",
         draw=p01_cockpit),
    dict(n=2, key="02_modes", title="Modo Juntar ⇄ Trocar",
         axis="modelo de navegação",
         problem="Ganhar e resgatar pontos estão misturados na mesma página, "
                 "competindo pela atenção.",
         approach=["Um seletor global separa os dois modos",
                   "Modo ativo ocupa a tela inteira, focado",
                   "O outro modo fica como gaveta acessível",
                   "Cada modo tem suas próprias ‘pistas’ de ação"],
         outcome="Intenção clara a cada sessão: ‘vim ganhar’ ou ‘vim gastar’ — "
                 "menos ruído, menos decisão.",
         ai="IA detecta a intenção da sessão (histórico, hora, saldo) e já abre "
            "no modo certo — Juntar ou Trocar — sem o cliente escolher.",
         refactors="IA global  ·  navegação primária",
         draw=p02_modes),
    dict(n=3, key="03_goals", title="Planejador por metas",
         axis="modelo de tarefa / aspiração",
         problem="Pontos são abstratos; o cliente não sabe o que faltam para "
                 "algo que ele realmente quer.",
         approach=["Cliente escolhe uma meta concreta (viagem, gadget)",
                   "Mostra progresso: ‘54% — faltam 41.750 pts’",
                   "Sugere caminhos mais rápidos pra fechar a meta",
                   "Liga ganho e resgate por um objetivo único"],
         outcome="Transforma saldo em propósito e cria um motivo recorrente "
                 "pra voltar e juntar mais.",
         ai="IA estima a data provável de conquista no ritmo atual e simula o "
            "caminho mais barato em pontos — um co-piloto da meta.",
         refactors="home  ·  /minhas-metas",
         draw=p03_goals),
    dict(n=4, key="04_directory", title="Diretório de parceiros",
         axis="mecanismo de layout (facetas)",
         problem="O mega-menu empilha dezenas de logos no cabeçalho — impossível "
                 "achar uma loja específica.",
         approach=["Header enxuto; parceiros viram uma página dedicada",
                   "Facetas: categoria, tipo de ganho, ordenar",
                   "Busca + grade A–Z de 180+ lojas",
                   "Taxa de cashback visível em cada card"],
         outcome="Descoberta real de parceiros em vez de um menu impossível de "
                 "escanear visualmente.",
         ai="Busca semântica entende ‘loja de eletrônico com mais ponto’ e a IA "
            "reordena o diretório pelo seu padrão de compra.",
         refactors="header / mega-menu  ·  /parceiros",
         draw=p04_directory),
    dict(n=5, key="05_search", title="Busca unificada",
         axis="IA orientada à busca",
         problem="A busca é genérica e não cruza produtos, viagens, experiências "
                 "e gift cards num só lugar.",
         approach=["Busca dominante cobre todo o inventário",
                   "Facetas por tipo de resultado e por preço",
                   "Filtro ‘cabe no meu saldo’ por padrão",
                   "Resultados mistos marcados por tipo"],
         outcome="Uma caixa de busca resolve qualquer intenção; o saldo vira "
                 "filtro natural de relevância.",
         ai="Busca em linguagem natural com ranqueamento por valor-por-ponto: a "
            "IA interpreta a intenção, não só casa palavras-chave.",
         refactors="busca global  ·  /busca",
         draw=p05_search),
    dict(n=6, key="06_travel", title="Hub de Viagens",
         axis="profundidade de vertical",
         problem="Viagens — alto valor por ponto — está escondida dentro de "
                 "‘Categorias’, sem ferramenta de busca.",
         approach=["Sub-marca Esfera Viagens com header próprio",
                   "Widget de busca (origem/destino/datas) no topo",
                   "Resultados com resgate pontos + dinheiro",
                   "Passagens, hotéis, pacotes, carros, ônibus"],
         outcome="Trata viagem como o produto-âncora que é, com a profundidade "
                 "de uma OTA de verdade.",
         ai="IA monta roteiros e alerta quando a tarifa em pontos está barata "
            "(‘compre agora’), prevendo a melhor janela de resgate.",
         refactors="categoria Viagens  ·  viagens.esfera",
         draw=p06_travel),
    dict(n=7, key="07_checkout", title="Carrinho de resgate",
         axis="fluxo / checkout",
         problem="Resgatar é item-a-item; não dá pra juntar resgates nem "
                 "completar pontos com dinheiro de forma clara.",
         approach=["Carrinho com vários itens e um checkout",
                   "Stepper: carrinho → revisão → pagamento",
                   "Slider divide pontos + dinheiro ao vivo",
                   "Pontos só debitados ao confirmar"],
         outcome="Resgate ganha a confiança e a clareza de um e-commerce "
                 "moderno, reduzindo abandono.",
         ai="IA sugere a divisão ótima de pontos + dinheiro e detecta fraude/erro "
            "antes de debitar — checkout que se defende sozinho.",
         refactors="resgate  ·  /resgate/checkout",
         draw=p07_checkout),
    dict(n=8, key="08_status", title="Níveis & missões",
         axis="gamificação / status",
         problem="A faixa de níveis (1.000–30.000 pts) não explica benefício "
                 "nem dá um caminho de progressão.",
         approach=["Escada de níveis: Bronze→Prata→Ouro→Black",
                   "Benefícios comparados por nível, lado a lado",
                   "Missões semanais com recompensa e progresso",
                   "Sequência (streak) incentiva o hábito"],
         outcome="Engajamento recorrente: o cliente sobe de nível e volta pelas "
                 "missões, não só pela compra.",
         ai="IA gera missões personalizadas e calibra a dificuldade pelo perfil "
            "— próximas o bastante pra engajar, sem parecer impossível.",
         refactors="faixa de níveis  ·  /meu-nivel",
         draw=p08_status),
    dict(n=9, key="09_mobile", title="Mobile bottom-nav",
         axis="fator de forma",
         problem="A home desktop densa não cabe no celular, onde está a maior "
                 "parte do tráfego de loyalty.",
         approach=["Shell mobile com bottom-nav de 5 abas",
                   "Feed em cards de toque único",
                   "Atalho ‘Juntar’ por scan de nota/QR",
                   "Conta e saldo a um toque"],
         outcome="Experiência nativa de celular: rápida, com o polegar, em vez "
                 "de uma página desktop comprimida.",
         ai="OCR/visão lê a nota fiscal no scan e credita pontos; notificações "
            "preditivas chegam na hora certa pelo comportamento.",
         refactors="todo o site  ·  shell mobile",
         draw=p09_mobile),
    dict(n=10, key="10_feed", title="Feed personalizado",
         axis="conteúdo algorítmico",
         problem="As fileiras da home são editoriais e fixas, iguais para todos, "
                 "ignorando o comportamento do cliente.",
         approach=["Feed algorítmico substitui fileiras fixas",
                   "Cards de intenção: expira, perto, bônus, missão",
                   "Reordena por comportamento e contexto",
                   "Cada card é uma ação distinta, não só vitrine"],
         outcome="A home fala com cada cliente: mostra o ponto que vence, a meta "
                 "perto, o bônus que importa agora.",
         ai="O feed é a IA: modelo de recomendação ordena cada card por propensão "
            "e urgência — o motor inteiro é aprendizado de máquina.",
         refactors="home editorial  ·  feed /pra-voce",
         draw=p10_feed),
    dict(n=11, key="11_value", title="Valor do ponto",
         axis="transparência de preço",
         problem="O cliente não sabe quanto vale 1 ponto, então não percebe quando "
                 "faz uma troca ruim (ex.: desconto na fatura).",
         approach=["Mostra o saldo em R$ pelo melhor uso",
                   "Valor por ponto (¢/pt) em cada tipo de troca",
                   "Marca ‘melhor’ e ‘pior’ valor explicitamente",
                   "Lista as melhores trocas pelo seu saldo"],
         outcome="Decisão informada: o cliente extrai mais de cada ponto e "
                 "confia que a Esfera não o subestima.",
         ai="IA calcula o valor-por-ponto em tempo real (preço dinâmico) e "
            "recomenda a troca que maximiza R$ por ponto.",
         refactors="catálogo  ·  /valor-dos-pontos",
         draw=p11_value),
    dict(n=12, key="12_expiry", title="Central de validade",
         axis="ciclo de vida / anti-breakage",
         problem="~30% dos pontos vencem sem uso. A validade é uma surpresa "
                 "ruim, não um aviso útil.",
         approach=["Linha do tempo de pontos por data de vencimento",
                   "Sugestões de queima do tamanho do saldo a vencer",
                   "Micro-resgates de poucos pontos em 1 clique",
                   "Nunca deixa o cliente perder por descuido"],
         outcome="Menos breakage e mais resgates frequentes — o cliente sente "
                 "que a marca protege o valor dele.",
         ai="IA prevê a probabilidade de breakage por cliente e dispara o "
            "lembrete certo, na hora certa, com a oferta de queima ideal.",
         refactors="validade  ·  /a-vencer",
         draw=p12_expiry),
    dict(n=13, key="13_statement", title="Extrato auditável",
         axis="confiança / rastreabilidade",
         problem="‘Comprei e não pontuou’ é a reclamação nº 1. Não há "
                 "rastreio de pendências nem como contestar.",
         approach=["Cada compra com status: pendente/creditado/análise",
                   "Alerta proativo de pontos que não caíram",
                   "Contestação em 1 clique, com prazo visível",
                   "Extrato que parece um banco, não uma caixa-preta"],
         outcome="Resolve a dor que mais gera reclamação no Reclame Aqui e "
                 "reconstrói a confiança no acúmulo.",
         ai="IA reconcilia compras × pontos e sinaliza anomalias (‘deveria ter "
            "pontuado’) antes do cliente reclamar — auditoria automática.",
         refactors="extrato  ·  /extrato",
         draw=p13_statement),
    dict(n=14, key="14_membership", title="Esfera+ (assinatura)",
         axis="modelo de negócio",
         problem="Todo benefício é igual pra todos; não há um motor de receita "
                 "recorrente nem fidelização premium.",
         approach=["Plano pago empilha benefícios (modelo Prime)",
                   "Comparação clara Grátis × Esfera+",
                   "Bônus maior, frete grátis, sem validade",
                   "Concierge e acesso antecipado a ofertas"],
         outcome="Cria receita recorrente e um laço premium — quem assina usa "
                 "mais e fica mais.",
         ai="IA personaliza a oferta de assinatura (preço/benefício) e prevê "
            "churn para reter assinantes com o incentivo certo.",
         refactors="benefícios  ·  /esfera-mais",
         draw=p14_membership),
    dict(n=15, key="15_concierge", title="Concierge IA",
         axis="modalidade de interação",
         problem="Achar a troca certa exige navegar muitas telas; não há quem "
                 "‘entenda’ o pedido do cliente.",
         approach=["Chat resolve em linguagem natural",
                   "Sugere itens com bom valor por ponto inline",
                   "Adiciona ao carrinho direto da conversa",
                   "Atalhos pras perguntas mais comuns"],
         outcome="A jornada vira diálogo: o cliente pede, a Esfera resolve — "
                 "sem caçar em menus.",
         ai="É IA-nativa: um agente conversacional (LLM) com as ferramentas de "
            "saldo, catálogo e resgate plugadas — entende, planeja e executa.",
         refactors="suporte/descoberta  ·  /concierge",
         draw=p15_concierge),
    dict(n=16, key="16_micro", title="Micro-resgates",
         axis="granularidade / gratificação imediata",
         problem="Resgate é um evento raro de alto custo; faltam trocas pequenas "
                 "e instantâneas que criem hábito.",
         approach=["Catálogo de poucos pontos, entrega na hora",
                   "Vouchers, cupons, doações, créditos digitais",
                   "Resgate em 1 toque, sem checkout longo",
                   "A partir de 200 pts"],
         outcome="Resgatar vira rotina — e redeemers dão muito menos churn que "
                 "quem nunca troca.",
         ai="IA escolhe os micro-resgates certos pra cada cliente e o momento "
            "de oferecê-los, transformando saldo parado em hábito.",
         refactors="resgate  ·  /troca-rapida",
         draw=p16_micro),
    dict(n=17, key="17_donate", title="Doar pontos",
         axis="propósito / valores",
         problem="Pontos a vencer não têm saída com significado; falta uma "
                 "ponte entre fidelidade e impacto social.",
         approach=["Causas com meta coletiva e progresso",
                   "Micro-doação queima saldo pequeno",
                   "Mostra o impacto concreto de cada doação",
                   "Alternativa nobre ao ponto que ia vencer"],
         outcome="Marca com propósito e menos breakage: o cliente sente que "
                 "fez o bem com o que sobrava.",
         ai="IA combina a causa ao perfil de valores do cliente e quantifica o "
            "impacto previsto da doação, elevando a conversão.",
         refactors="resgate  ·  /doar",
         draw=p17_donate),
    dict(n=18, key="18_omni", title="Esfera na loja",
         axis="canal (online ↔ offline)",
         problem="Tudo é online; na loja física o cliente não junta nem usa "
                 "pontos com facilidade.",
         approach=["Carteira digital com QR no caixa",
                   "Pass na Apple/Google Wallet",
                   "Ofertas de parceiros perto de você",
                   "Junta e resgata no balcão, na hora"],
         outcome="Experiência omnichannel: o programa segue o cliente do app "
                 "ao caixa da loja.",
         ai="Geo-IA dispara ofertas quando você está perto de um parceiro e "
            "prevê a próxima compra física pra pré-carregar o cupom.",
         refactors="todo o site  ·  /na-loja",
         draw=p18_omni),
    dict(n=19, key="19_surprise", title="Surpresa & desafios",
         axis="recompensa variável (gamificação)",
         problem="A recompensa é 100% previsível; falta o gancho emocional da "
                 "surpresa que mais fideliza.",
         approach=["Giro diário grátis (pontos, cupom, prêmio)",
                   "Caixa surpresa ao bater missões",
                   "Desafio sazonal de 4 semanas",
                   "Reforço variável, não badge cosmético"],
         outcome="Engajamento emocional e visitas recorrentes — o cliente volta "
                 "pela expectativa, não só pela compra.",
         ai="IA calibra a recompensa variável por usuário (quando e quanto "
            "surpreender) pra maximizar retorno sem inflar custo.",
         refactors="engajamento  ·  /jogar",
         draw=p19_surprise),
    dict(n=20, key="20_explainer", title="Como funciona",
         axis="compreensão / clareza",
         problem="O programa é cheio de jargão e regras; novos clientes não "
                 "entendem como juntar e trocar.",
         approach=["Explicação em 1-2-3, sem juridiquês",
                   "Duas colunas: formas de Ganhar × Trocar",
                   "Linguagem simples e direta",
                   "Dúvidas frequentes em destaque"],
         outcome="Ativação mais rápida de novos clientes e menos suporte — "
                 "todo mundo entende o valor em 1 minuto.",
         ai="IA responde dúvidas em linguagem natural e adapta a explicação ao "
            "nível do cliente — um FAQ que conversa, não uma parede de texto.",
         refactors="onboarding  ·  /como-funciona",
         draw=p20_explainer),
]


# ======================================================================= #
#  capstone — how AI helps across the whole user journey
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
      "As 20 propostas, lidas pela ótica da IA: cada etapa da jornada ganha uma "
      "capacidade. Os números são as propostas que a usam.", style="body")

    # five journey stages as lanes
    stages = [
        ("DESCOBRIR", "encontrar o que importa", "#", [
            ("Recomendação", "feed ordena por propensão e urgência", "10"),
            ("Busca semântica", "entende intenção, não palavra-chave", "05"),
            ("Reordenar vitrine", "diretório por padrão de compra", "04")]),
        ("JUNTAR", "ganhar sem fricção", "↑", [
            ("Visão / OCR", "lê a nota fiscal no scan e credita", "09"),
            ("Geolocalização", "oferta quando passa na loja", "18"),
            ("Reconciliação", "detecta compra que não pontuou", "13")]),
        ("PLANEJAR", "decidir com clareza", "◎", [
            ("Previsão", "data provável de bater a meta", "03"),
            ("Janela de preço", "avisa tarifa de viagem barata", "06"),
            ("Agente / LLM", "concierge entende, planeja, executa", "15")]),
        ("TROCAR", "resgatar pelo melhor valor", "↓", [
            ("Preço dinâmico", "valor-por-ponto em tempo real", "11"),
            ("Otimização", "split ótimo de pontos + dinheiro", "07"),
            ("Curadoria", "o micro-resgate certo pra você", "16")]),
        ("RETER", "voltar e ficar", "★", [
            ("Propensão / churn", "prevê breakage e evasão", "12"),
            ("Calibragem", "missões e surpresa no ponto certo", "19"),
            ("Personalização", "oferta de assinatura e causa", "14")]),
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

    # journey arrow connecting the lanes
    page.layer("flow")
    ay = 130 + 560 + 22
    for i in range(len(lanes)):
        lx, _, lw, _ = lanes[i]
        circle(page, lx + lw / 2, ay, 6, fill="red")
        if i < len(lanes) - 1:
            page.rect([lx + lw / 2, ay - 1, lanes[i + 1][0] - lx, 2], fill="bar")
    # bottom: AI capability legend
    T(page, [32, ay + 28, 600, 14],
      "CAPACIDADES DE IA QUE O PROGRAMA PASSA A TER", style="lbl")
    legend = [
        ("Modelos de recomendação", "feed, vitrine, micro-resgate, causa"),
        ("PLN / agentes (LLM)", "concierge, busca, explainer que conversa"),
        ("Visão computacional / OCR", "leitura de nota fiscal no celular"),
        ("Previsão & propensão", "breakage, churn, data de meta, fraude"),
        ("Preço & otimização", "valor-por-ponto, split pontos+R$, geo-oferta"),
    ]
    for (ttl, desc), cb in zip(legend, row([32, ay + 48, W - 64, 64], count=5,
                                           gap=16)):
        card(page, cb, fill="paper")
        ix, iy, iw, _ = inset(cb, 14)
        T(page, [ix, iy, iw, 14], ttl, style="h3")
        T(page, [ix, iy + 18, iw, 28], _wrap(desc, 30), style="mut")


def build() -> DocumentBuilder:
    b = DocumentBuilder(
        title="Esfera — 20 refatorações + IA na jornada (wireframes)",
        profile="deck", lang="pt-BR")
    for name, value in COLORS.items():
        b.define_color(name, value)
    # an extra ink-track tone for dark progress on dark hero
    b.define_color("warm", "#4A4F57")
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
    out = os.path.join(ROOT, "tests", "fixtures", "esfera-refactor-wireframes.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
