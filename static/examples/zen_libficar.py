"""zen_libficar.py — "Zen e a arte de reColher" · A6 pocket book (the SDK way).

A super-polished, from-scratch edition. Craft after *The Letter & the Hue*:
a closed warm palette (one duty each), one Garalde serif with true small caps,
a modular type scale on a steady vertical rhythm, classical margins (foot widest),
front matter (epígrafe) and back matter (colofão), and plates balanced by the
steelyard. Geometry is authored as clean SDK primitives; the hand-drawn quality
is the SDK's own document-level ``humanize`` (``roughen``) — sketched at expand
time, the type left crisp.

Concept: reColher (pt-BR) · a partir de Libfy (en). Conceito de Pedro Anisio Silva.
A6 105×148 mm ≈ 397×559 px @96 dpi. Single file, content inline.
"""
from __future__ import annotations

import math
import os

from framegraph.sdk import DocumentBuilder, paint
from framegraph.sdk.macros import span

# ------------------------------------------------------------------ palette ---
PAPER = "#F3EEE4"   # warm ground
INK = "#211C16"     # warm near-black (never pure #000)
MUT = "#6E6656"     # the quiet second rank
HAIR = "#C9C1B0"    # faint rules, halos, rests
RED = "#A6442E"     # the one accent — the rubric; used as information, sparingly

GAR, SC, INTER = "EB Garamond", "EB Garamond SC", "Inter"
ts = paint.text_style

# Experimental page glow — a soft radial light at the page's heart, fading to the
# paper. Painted (see `glow`) as a circle far LARGER than the page, so its radial
# extent runs past the corners: the page shows only the smooth interior, with no
# clipped ellipse edge (TikZ confines a radial shading to its own shape, unlike SVG).
PAGE_BG = paint.radial_gradient([("#F8F3EA", 0.0), (PAPER, 1.0)], at="50% 50%", shape="circle")

# ----------------------------------------------------------- format + scale ---
W, H = 397, 559
ML, MR = 40, 357            # side margins (content width 317)
CX = (ML + MR) / 2          # 198.5
CW = MR - ML
FOOT = 524                  # foot rule / folio band (widest margin, per canon)

# modular scale, base 11 · ratio ~1.26
MICRO, TAG, KICK = 7.0, 8.0, 8.0
BODY, LEDE, SUB = 11.0, 13.5, 15.5
TITLE, HERO = 21.0, 33.0
LEAD = 15.5                 # body leading — the vertical unit

doc = DocumentBuilder(title="Zen e a arte de reColher", profile="book")
# Declare the concept's faces as font tokens (defs.tokens.fonts) so EVERY backend
# loads them by name — including the LaTeX / pdf-tex path, which registers each as
# a fontspec \newfontfamily instead of falling back to the DejaVu main font. The
# token names match the inline text-style families, so nothing else changes.
for _face in ("EB Garamond", "EB Garamond SC", "Inter"):
    doc.define_font(_face, family=_face)
# The hand — document level, the only authored scope. roughen sketches the drawn
# primitives; weight varies stroke pressure. Text/path/group stay crisp.
doc._doc["humanize"] = {"seed": 11, "roughen": 0.5, "weight": 0.14, "grain": 0.72}


# ------------------------------------------------------------------ helpers ---
def wrap(text, cpl):
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > cpl:
            out.append(line); line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


def T(page, x, baseline, s, size, *, color=INK, family=GAR, italic=False,
      weight=None, anchor="start", ls=None):
    """Baseline-anchored text (SVG-style y), so positions read as a designer's."""
    top = baseline - size * 0.80
    h = size * 1.5
    if anchor == "middle":
        box, align = [x - 180, top, 360, h], "center"
    elif anchor == "end":
        box, align = [x - 320, top, 320, h], "right"
    else:
        box, align = [x, top, MR + 30 - x, h], "left"
    page.text(box, s, style=ts(size, family=family, color=color, italic=italic or None,
                               weight=weight, align=align, letter_spacing=ls))


def cap(page, x, baseline, s, size, *, color=INK, anchor="start", ls=0.4):
    T(page, x, baseline, s, size, color=color, family=SC, anchor=anchor, ls=ls)


def para(page, x, baseline, text, *, size=BODY, lead=LEAD, color=INK, italic=False,
         anchor="start", cpl=54):
    lines = wrap(text, cpl) if isinstance(text, str) else text
    for i, ln in enumerate(lines):
        T(page, x, baseline + i * lead, ln, size, color=color, italic=italic, anchor=anchor)
    return baseline + len(lines) * lead


def rule(page, x1, y, x2, *, color=HAIR, w=0.8):
    page.line([x1, round(y, 2)], [x2, round(y, 2)], **paint.stroke(w, color=color))


def arc(cx, cy, r, a0, a1, n=44):
    return [[round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), 2),
             round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 2)]
            for i in range(n + 1)]


def stroke_line(page, pts, *, color=RED, w=1.6):
    page.polyline(pts, **paint.stroke(w, color=color, cap="round", join="round"))


def head(page, pts, *, color=RED, size=7.5):
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    ang = math.atan2(y2 - y1, x2 - x1)
    a, b = ang + math.radians(151), ang - math.radians(151)
    page.polygon([[round(x2, 2), round(y2, 2)],
                  [round(x2 + size * math.cos(a), 2), round(y2 + size * math.sin(a), 2)],
                  [round(x2 + size * math.cos(b), 2), round(y2 + size * math.sin(b), 2)]],
                 fill=color)


def disk(page, cx, cy, r, *, stroke=INK, w=1.2, fill=PAPER):
    page.circle([round(cx, 2), round(cy, 2)], r, fill=fill, **paint.stroke(w, color=stroke))


def ell(page, cx, cy, rx, ry, *, stroke=INK, w=1.2, fill=PAPER):
    if w:
        page.ellipse([round(cx, 2), round(cy, 2)], round(rx, 2), round(ry, 2),
                     fill=fill, **paint.stroke(w, color=stroke))
    else:
        page.ellipse([round(cx, 2), round(cy, 2)], round(rx, 2), round(ry, 2), fill=fill)


def legend(p, x, y, term, gloss):
    """A key entry: garden term (small caps) · library gloss (Inter grey)."""
    p.text([x + 16, y - 7, 155, 12],
           [span(term, font=SC, color=INK, letter_spacing=0.3),
            span("  ·  ", font=INTER, color=RED),
            span(gloss, font=INTER, color=MUT, letter_spacing=0.1)],
           style=ts(8.5, family=INTER, color=MUT))


def leg_stone(p, x, y):
    ell(p, x, y, 4.4, 3.0, stroke=INK, w=0.9, fill="#E7DFD0")


def leg_moss(p, x, y):
    for dx, dy in [(-2.4, -1.0), (0.6, -2.3), (-0.6, 1.4), (2.5, 0.2)]:
        ell(p, x + dx, y + dy, 0.85, 0.85, stroke=MUT, w=0, fill=MUT)


def leg_rake(p, x, y):
    for i in range(3):
        p.line([x - 4.6, y - 2.4 + i * 2.4], [x + 4.6, y - 2.4 + i * 2.4], **paint.stroke(0.7, color=MUT))


def leg_border(p, x, y):
    p.rect([x - 4.6, y - 3.2, 9.2, 6.4], **paint.stroke(0.9, color=INK))


def enso(page, cx, cy, r, *, wmin=1.3, wmax=4.6, gap_deg=50, gap_at=30, color=INK, wob=1.1):
    """A calligraphic brush ensō: thin → swelling → thin, a gap, a faint hand
    wobble in the radius. Reads as a single drawn breath (and the SDK loop)."""
    a0, a1 = gap_at + gap_deg / 2, gap_at - gap_deg / 2 + 360
    n, prev = 52, None
    for i in range(n + 1):
        u = i / n
        a = math.radians(a0 + (a1 - a0) * u)
        rr = r + wob * math.sin(u * math.pi * 3.0)
        pt = [round(cx + rr * math.cos(a), 2), round(cy + rr * math.sin(a), 2)]
        if prev is not None:
            w = wmin + (wmax - wmin) * (math.sin(u * math.pi) ** 0.7)
            page.polyline([prev, pt], **paint.stroke(round(w, 2), color=color, cap="round", join="round"))
        prev = pt


def folio(page, n):
    T(page, CX, FOOT + 12, f"·  {n}  ·", MICRO, color=MUT, family=INTER, anchor="middle", ls=1.0)


def running_head(page, label):
    cap(page, ML, 58, label, TAG, color=MUT, ls=1.2)
    rule(page, ML, 68, MR, color=HAIR, w=0.7)


def section_head(page, num, kicker, title, lede):
    T(page, ML, 62, num, TITLE, color=RED, weight=700)
    cap(page, ML + 26, 60, kicker, TAG, color=MUT, ls=1.0)
    T(page, ML, 104, title, TITLE, weight=700)
    y = para(page, ML, 128, lede, size=LEDE, lead=17, color=MUT, italic=True, cpl=44)
    rule(page, ML, y - 4, MR, color=MUT, w=0.9)
    return y - 4


def new_page(pid, bg=PAPER):
    p = doc.page(pid, canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    p.layer("paper")
    p.rect([-12, -12, W + 24, H + 24], fill=bg)   # oversized: roughen's wobble clipped off-page
    p.layer("art")
    p.layer("ink")
    return p


def art(p):
    p._current_layer = p._page["layers"][1]   # the "art" layer (below ink)
    return p


def ink(p):
    p._current_layer = p._page["layers"][2]
    return p


def glow(p, *, R=470, cy=None):
    """Paint PAGE_BG as a circle much larger than the page, on the paper layer
    above the flat base. Its edge (R=470) sits beyond the farthest page corner
    (~370 from centre), so only the smooth interior shows — never a clipped edge."""
    p._current_layer = p._page["layers"][0]
    p.circle([CX, round(H * 0.44 if cy is None else cy, 1)], R, fill=PAGE_BG)
    p._current_layer = p._page["layers"][2]
    return p


# ==================================================================== 1 · capa
def p1():
    p = new_page("capa")
    ink(p)
    cap(p, CX, 96, "uma pequena reflexão sobre cultivar capacidades", KICK, color=MUT, anchor="middle", ls=1.6)
    T(p, CX, 150, "Zen e a arte de", SUB, color=MUT, italic=True, anchor="middle")
    T(p, CX, 196, "reColher", HERO, weight=700, anchor="middle")
    art(p)
    enso(p, CX, 320, 74, wmin=1.4, wmax=5.0, wob=1.2)
    ink(p)
    cap(p, CX, 424, "A capacidade se compõe", 9, color=RED, anchor="middle", ls=1.8)
    T(p, CX, 470, "conceito · Pedro Anisio Silva", 10.5, color=MUT, italic=True, anchor="middle")
    T(p, CX, 488, "*Libfiy - en_US", 10.5, color=MUT, italic=True, anchor="middle")
    cap(p, CX, 512, "FrameGraph · EB Garamond & Inter", MICRO, color=MUT, anchor="middle", ls=1.2)


# =============================================================== 2 · epígrafe
def p2():
    p = new_page("epigrafe")
    ink(p)
    T(p, CX, 250, "Toda obra, ao terminar,", LEDE, color=INK, italic=True, anchor="middle")
    T(p, CX, 270, "deixa mais do que a obra.", LEDE, color=INK, italic=True, anchor="middle")
    T(p, CX, 306, "— o que ela deixa é capacidade.", 11, color=MUT, italic=True, anchor="middle")
    art(p)
    enso(p, CX, 372, 12, wmin=0.7, wmax=2.0, gap_deg=60, wob=0.4, color=RED)
    ink(p)
    folio(p, 2)


# ============================================================= 3 · I · o ciclo
def p3():
    p = new_page("ciclo")
    glow(p)
    ink(p)
    y0 = section_head(p, "I", "A definição · os juros compostos da capacidade", "reColher",
                      "Colher outra vez: nem tudo na obra precisa terminar com ela.")
    R, ccx, ccy, r = 74, CX, 326, 27
    top = (ccx, ccy - R)
    right = (ccx + R * math.cos(math.radians(30)), ccy + R * 0.5)
    left = (ccx - R * math.cos(math.radians(30)), ccy + R * 0.5)
    art(p)
    for a0, a1 in [(-66, 26), (54, 126), (154, 246)]:
        a = arc(ccx, ccy, R, a0, a1); stroke_line(p, a, w=1.6); head(p, a)
    disk(p, *top, r)
    disk(p, *right, r, stroke=RED, w=1.5)
    disk(p, *left, r)
    ink(p)
    cap(p, top[0], top[1] + 3.4, "Obra", 9.5, anchor="middle")
    T(p, top[0], top[1] - r - 11, "obra concluída ou em curso", TAG, color=MUT, family=INTER, anchor="middle", ls=0.1)
    cap(p, right[0], right[1] + 3.4, "reColher", 9.5, color=RED, anchor="middle")
    T(p, right[0] + 20, right[1] + r + 15, "colher capacidade reutilizável", TAG, color=MUT, family=INTER, anchor="middle", ls=0.1)
    cap(p, left[0], left[1] + 3.4, "Biblioteca", 9.5, anchor="middle")
    T(p, left[0] - 20, left[1] + r + 15, "partes curadas + saber-fazer", TAG, color=MUT, family=INTER, anchor="middle", ls=0.1)
    cap(p, ccx, ccy - 2, "A capacidade", TAG, color=RED, anchor="middle", ls=1.2)
    cap(p, ccx, ccy + 11, "se compõe", TAG, color=RED, anchor="middle", ls=1.2)
    T(p, left[0] - r - 6, ccy - R + 8, "acelera", 8.5, color=RED, italic=True, anchor="end")
    T(p, CX, 448, "O ciclo inteiro cabe numa volta:", 11, color=MUT, italic=True, anchor="middle")
    T(p, CX, 466, "construir, colher, guardar — construir de novo.", 11, color=MUT, italic=True, anchor="middle")
    folio(p, 3)


# ========================================================= 4 · I · o texto
def p4():
    p = new_page("def-texto")
    ink(p)
    running_head(p, "I · A definição")
    from framegraph.sdk.macros import span
    p.text([ML, 96 - BODY * 0.8, CW, LEAD * 1.5],
           [span("Recolher", font=SC, color=RED, letter_spacing=0.3),
            span(" é a prática de extrair capacidade reutilizável", font=GAR, color=INK)],
           style=ts(BODY, family=GAR, color=INK))
    y = para(p, ML, 96 + LEAD, "do trabalho construtivo — concluído ou ainda em curso.", cpl=54)
    y = para(p, ML, y + 12, "Seu fruto é uma biblioteca: um sistema curado e anotado de "
             "elementos reutilizáveis, das partes concretas — componentes, agregados, "
             "ativos — ao saber-fazer: padrões, receitas, decisões e seus porquês.", cpl=54)
    y = para(p, ML, y + 12, "Uma biblioteca acelera toda construção futura; e porque o que "
             "nasce dela herda sua estrutura, esse trabalho é, por sua vez, mais fácil de "
             "recolher.", cpl=54)
    T(p, CX, y + 60, "Assim, a capacidade se compõe.", LEDE, color=RED, italic=True, anchor="middle")
    folio(p, 4)


# ============================================================ 5 · II · o jardim
def p5():
    p = new_page("jardim-plano")
    ink(p)
    section_head(p, "II", "O jardim · antes do gesto, o lugar", "O jardim seco",
                 "A biblioteca não é depósito; é um jardim que se visita.")
    para(p, ML, 190, "Chega-se pelo caminho de pedras — e cada pedra sob os pés é uma obra "
         "que você já concluiu. O jardim não é a montanha: é a montanha tornada tratável. "
         "Pedras escolhidas, musgo que cresce devagar, cascalho penteado em linhas claras.", cpl=54)
    gx, gy, gw, gh = ML, 300, CW, 158
    art(p)
    page_hbox(p, gx, gy, gw, gh)
    for i in range(1, 11):
        rule(p, gx + 10, gy + i * gh / 11, gx + gw - 10)
    s1, s2, s3 = (gx + 84, gy + 60), (gx + 226, gy + 100), (gx + 156, gy + 126)
    for (sx, sy), rr in [(s1, 22), (s2, 26), (s3, 13)]:
        for k in (9, 17, 25):
            ell(p, sx, sy, rr + k, (rr + k) * 0.60, stroke=HAIR, w=0.7)
    ell(p, s1[0], s1[1], 22, 14)
    ell(p, s2[0], s2[1], 26, 16, stroke=RED, w=1.4)
    ell(p, s3[0], s3[1], 13, 8)
    for dx, dy in [(-6, -3), (0, 2), (5, -2), (-2, -7), (8, 3), (3, 7)]:
        ell(p, s1[0] + dx + 36, s1[1] + dy - 25, 1.6, 1.6, stroke=MUT, w=0, fill=MUT)
    # legend key — a garden-element glyph, its small-caps name, and the library gloss
    col2 = gx + 162
    r1, r2 = gy + gh + 20, gy + gh + 37
    art(p)
    leg_stone(p, gx + 4, r1 - 3); leg_moss(p, col2 + 4, r1 - 3)
    leg_rake(p, gx + 4, r2 - 3); leg_border(p, col2 + 4, r2 - 3)
    ink(p)
    legend(p, gx, r1, "pedra", "componente")
    legend(p, col2, r1, "musgo", "saber-fazer")
    legend(p, gx, r2, "ancinho", "curadoria")
    legend(p, col2, r2, "borda", "escopo")
    folio(p, 5)


def page_hbox(p, x, y, bw, bh, *, stroke=INK, w=1.2):
    p.rect([x, y, bw, bh], **paint.stroke(w, color=stroke))


# ========================================================= 6 · II · o texto
def p6():
    p = new_page("jardim-texto")
    ink(p)
    running_head(p, "II · O jardim")
    y = para(p, ML, 100, "Ninguém entra num jardim por acaso; ele existe para ser revisitado. "
             "Uma biblioteca também: pequena o bastante para caber no olhar, viva o bastante "
             "para valer a volta.", cpl=54)
    T(p, CX, y + 46, "O jardim não guarda a montanha;", LEDE, color=RED, italic=True, anchor="middle")
    T(p, CX, y + 66, "guarda o essencial dela.", LEDE, color=RED, italic=True, anchor="middle")
    art(p)
    for yy in (356, 368, 380):
        rule(p, 130, yy, 267)
    ell(p, CX, 368, 15, 9)
    ink(p)
    folio(p, 6)


# ============================================================ 7 · III · prática
def p7():
    p = new_page("pratica")
    ink(p)
    section_head(p, "III", "A prática · o que significa fazer", "Cinco gestos",
                 "Recolher não é uma fase; é um modo de terminar.")
    gest = [("01", "Notar", "Perceber, no meio da obra, o que pede para viver mais de uma vez."),
            ("02", "Extrair", "Separar a parte do todo sem ferir nem a parte, nem o todo."),
            ("03", "Nomear", "Dar um nome que ensina o uso. Nomear é compreender."),
            ("04", "Anotar", "Registrar o contexto: quando serve, quando não — e por quê."),
            ("05", "Aparar", "Podar, versionar, aposentar. O jardim fica pequeno para permanecer vivo.")]
    y = 202
    for num, name, desc in gest:
        T(p, ML, y, num, 13, color=RED)
        cap(p, ML + 34, y, name, 11)
        y2 = para(p, ML + 108, y, desc, cpl=34, lead=14.5)
        y = max(y + 14.5, y2) + 12
        if num != "05":
            rule(p, ML, y - 15, MR)
    T(p, CX, y + 10, "Repetidos, os gestos deixam de ser tarefa — e viram atenção.", 11,
      color=RED, italic=True, anchor="middle")
    ly = y + 42
    art(p)
    rule(p, 128, ly, 268)
    for i in range(5):
        disk(p, 128 + i * 35, ly, 3.4, stroke=(RED if i == 4 else INK))
    ink(p)
    folio(p, 7)


# =========================================================== 8 · IV · o prefixo
def p8():
    p = new_page("prefixo")
    ink(p)
    section_head(p, "IV", "O prefixo · o que o jardim torna barato", "A família do re-",
                 "Um jardim existe para que o re- custe pouco.")
    cx, cy = CX, 314
    stems = ["colher", "parar", "olhar", "refletir", "pensar", "imaginar", "significar",
             "encontrar", "planejar", "desenhar", "cortar", "modelar", "fundir", "construir",
             "criar", "unir", "utilizar", "aproveitar", "ciclar", "anotar", "surgir"]
    n = len(stems)
    art(p)
    for i, s in enumerate(stems):
        a = math.radians(-90 + i * 360 / n)
        rl = 82 if i % 2 == 0 else 108
        hot = s == "colher"
        x1, y1 = cx + 40 * math.cos(a), cy + 40 * math.sin(a)
        x2, y2 = cx + (rl - 8) * math.cos(a), cy + (rl - 8) * math.sin(a)
        p.line([round(x1, 1), round(y1, 1)], [round(x2, 1), round(y2, 1)],
               **paint.stroke(1.2 if hot else 0.6, color=(RED if hot else MUT)))
    disk(p, cx, cy, 32, stroke=RED, w=1.5)
    ink(p)
    for i, s in enumerate(stems):
        a = math.radians(-90 + i * 360 / n)
        rl = 82 if i % 2 == 0 else 108
        hot = s == "colher"
        lx, ly = cx + rl * math.cos(a), cy + rl * math.sin(a)
        anch = "start" if math.cos(a) > 0.35 else ("end" if math.cos(a) < -0.35 else "middle")
        T(p, round(lx, 1), round(ly + 3.2, 1), s, 8.5, color=(RED if hot else INK), anchor=anch)
    T(p, cx, cy + 6, "re-", 18, color=RED, weight=700, anchor="middle")
    T(p, CX, 470, "reparar: consertar — e também notar. No jardim, o mesmo gesto.", 10,
      color=MUT, italic=True, anchor="middle")
    T(p, CX, 494, "No jardim, todo verbo aceita o re-.", 11.5, color=RED, italic=True, anchor="middle")
    folio(p, 8)


# ============================================================== 9 · V · na obra
def p9():
    p = new_page("na-obra")
    ink(p)
    section_head(p, "V", "Na obra · o que o jardim devolve ao trabalho", "Na obra",
                 "Quem parte de um jardim nunca parte do zero.")
    items = [("Velocidade", "começa-se do meio, não do zero: as partes já existem, prontas ao uso."),
             ("Coerência", "partes do mesmo jardim combinam entre si — a obra herda estrutura, não acaso."),
             ("Herança", "o que nasce da biblioteca já nasce fácil de recolher: cada obra devolve algo.")]
    y = 190
    for name, desc in items:
        T(p, ML, y, name + " —", 11, color=RED, italic=True)
        y = para(p, ML + 72, y, desc, cpl=40, lead=14.5) + 8
    bx, by, bw = 100, 452, 26
    heights, labels = [88, 60, 43, 31], ["1ª obra", "2ª", "3ª", "4ª"]
    tops = []
    art(p)
    for i, hh in enumerate(heights):
        x = bx + i * 52
        page_hbox(p, x, by - hh, bw, hh)
        tops.append((x + bw / 2, by - hh - 7))
    stroke_line(p, tops, w=1.5); head(p, tops)
    rule(p, bx - 12, by, bx + 3 * 52 + bw + 12, color=MUT, w=0.9)
    ink(p)
    for i, lb in enumerate(labels):
        T(p, bx + i * 52 + bw / 2, by + 13, lb, TAG, color=MUT, family=INTER, anchor="middle", ls=0.1)
    T(p, bx - 12, by - 104, "custo de começar", TAG, color=MUT, family=INTER, ls=0.1)
    T(p, MR, by - 96, "cada volta encurta a próxima", TAG, color=RED, italic=True, anchor="end")
    T(p, CX, 500, "Juros compostos — de capacidade.", LEDE, color=RED, italic=True, anchor="middle")
    folio(p, 9)


# ============================================================= 10 · VI · a mente
def p10():
    p = new_page("na-mente")
    ink(p)
    section_head(p, "VI", "Na mente · o que o jardim devolve a quem cultiva", "Na mente",
                 "O jardim que você apara também apara você.")
    items = [("Desapego", "quem guarda a capacidade pode soltar o artefato — terminar deixa de doer."),
             ("Clareza", "nomear é compreender; anotar é compreender duas vezes."),
             ("Calma", "a mente que confia no jardim não carrega o pomar inteiro na cabeça."),
             ("Atenção", "o olho treinado vê, em toda obra, a semente do reutilizável.")]
    y = 190
    for name, desc in items:
        T(p, ML, y, name + " —", 11, color=RED, italic=True)
        y = para(p, ML + 66, y, desc, cpl=42, lead=14.5) + 7
    rule(p, ML, y, MR)
    y = para(p, ML, y + 22, "No fim, recolher é menos sobre as partes do que sobre uma maneira "
             "de trabalhar: terminar deixando o caminho mais curto para quem vem depois — "
             "inclusive você.", cpl=54)
    T(p, CX, y + 26, "Assim, a capacidade se compõe.", LEDE, color=RED, italic=True, anchor="middle")
    folio(p, 10)


# =============================================================== 11 · colofão
def p11():
    p = new_page("colofao")
    art(p)
    enso(p, CX, 232, 22, wmin=0.8, wmax=2.4, gap_deg=54, wob=0.6, color=RED)
    ink(p)
    T(p, CX, 300, "A capacidade se compõe.", LEDE, color=RED, italic=True, anchor="middle")
    T(p, CX, 322, "— e, com ela, quem a cultiva.", 11, color=MUT, italic=True, anchor="middle")
    rule(p, CX - 60, 402, CX + 60, color=HAIR, w=0.8)
    cap(p, CX, 424, "Zen e a arte de reColher", 9, color=INK, anchor="middle", ls=1.2)
    T(p, CX, 446, "um conceito de Pedro Anisio Silva, a partir de Libfy", 9.5, color=MUT, italic=True, anchor="middle")
    T(p, CX, 466, "composto em FrameGraph v2.3.0", 9.5, color=MUT, italic=True, anchor="middle")
    cap(p, CX, 490, "EB Garamond & Inter · SDK primitives · humanize", MICRO, color=MUT, anchor="middle", ls=1.0)


for _fn in (p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11):
    _fn()


def build():
    return doc


if __name__ == "__main__":
    out = os.environ.get("OUTPUT_YAML_PATH", "zen_recolher.fg.yaml")
    doc.write(out, fail_on_error=True)
    print("wrote", out)
