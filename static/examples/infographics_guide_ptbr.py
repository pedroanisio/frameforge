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

doc = DocumentBuilder(title="Infográficos que impressionam", profile="report")

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

def scaffold(pid, kicker_text, page_no, footer_note="INFOGRÁFICOS QUE IMPRESSIONAM"):
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

def card(m, box, title, body, face=PAPER, bar=MUTED, title_style=None):
    x, y, w, h = box
    m.rect([x, y, w, h], fill=face)
    m.rect([x, y, 8, h], fill=bar)
    m.text([x + 26, y + 22, w - 44, 34], title, style=title_style or ST_CARDT)
    m.text([x + 26, y + 64, w - 44, h - 84], body, style=ST_BODY)

def action_strip(m, items, y=None, title="AGORA É A SUA VEZ"):
    """The closing do-this rail: an ink mass above the footer."""
    y = y if y is not None else H - 264
    m.rect([MX, y, CW, 168], fill=INK)
    m.text([MX + 30, y + 24, 500, 30], title, style=ST_INVT)
    step_w = (CW - 60) / len(items)
    for i, item in enumerate(items):
        x = MX + 30 + i * step_w
        m.circle([x + 12, y + 84], 12, fill=ACCENT)
        m.text([x + 34, y + 66, step_w - 44, 94], item, style=ST_INV)

def mark_no(m, x, y, s=26):
    m.line([x, y], [x + s, y + s], **_stroke(5, color=ACCENT))
    m.line([x + s, y], [x, y + s], **_stroke(5, color=ACCENT))

def mark_yes(m, x, y, s=28):
    m.polyline([[x, y + s * 0.5], [x + s * 0.36, y + s * 0.92], [x + s, y + s * 0.08]],
               **_stroke(5, color=ACCENT2))

def challenge(m, y, q):
    """Design-challenge callout: one accent-ruled question."""
    m.line([MX, y], [MX, y + 134], **_stroke(5, color=ACCENT))
    m.text([MX + 26, y, 250, 24], "DESAFIO DE DESIGN", style=ST_KICK)
    m.text([MX + 26, y + 30, 700, 104], q, style=ST_BODYM)


# ================================================================ page 1 ----
# Cover: title mass upper-left, an abstract infographic column answering right.
m = scaffold("p01", None, 1, footer_note="UM GUIA PRÁTICO EM DEZ PASSOS")
m.rect([0, 0, W, 14], fill=ACCENT)
m.text([MX, 200, 340, 26], "UM GUIA PRÁTICO EM DEZ PASSOS", style=ST_KICK)
m.text([MX, 250, 760, 420], "Infográficos\nque\nimpressionam", style=ST_COVER)
m.text([MX, 620, 620, 130],
       "Da primeira pergunta sobre o público ao dia de publicar: um método "
       "completo para transformar dados e ideias em uma história visual "
       "clara.", style=ST_LEAD)
m.line([MX, 790], [MX + 620, 790], **_stroke(3, color=INK))
m.text([MX, 816, 620, 60],
       "Mensagem · História visual · Produção · Revisão · Publicação",
       style=ST_BODYM)
# Cover motif: a tall abstract infographic (donut, bars, pictograms, spark).
cx, cw = 880, 250
m.rect([cx - 30, 200, cw + 60, 1240], fill=PANEL)
m.ring([cx + cw / 2, 330], 78, 46, fill=ACCENT2)
m.sector([cx + cw / 2, 330], 78, -90, 30, fill=ACCENT)
m.circle([cx + cw / 2, 330], 46, fill=PANEL)
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
m.text([cx + 8, 1247, 220, 28], "CHAMADA PARA AÇÃO", style=ST_FOOT)

# ================================================================ page 2 ----
m = scaffold("p02", "O MÉTODO", 2)
m.text([MX, 150, CW, 60], "Dez passos, três movimentos", style=ST_H1)
m.text([MX, 224, 900, 148],
       "Um infográfico se desenha de trás para frente, a partir do leitor. "
       "O método vai da mensagem à história visual e à produção — cada "
       "passo alimenta o seguinte, e toda decisão posterior responde aos "
       "três primeiros.",
       style=ST_LEAD)
part_data = [
    ("PARTE I — CONSTRUA UMA MENSAGEM PODEROSA", ACCENT,
     [("1", "Identifique seu público", "o QUEM"),
      ("2", "Defina o propósito", "o PORQUÊ"),
      ("3", "Crie a história", "o QUÊ")]),
    ("PARTE II — DESENHE UMA HISTÓRIA VISUAL", ACCENT2,
     [("4", "Escolha dados e visuais", "evidências"),
      ("5", "Selecione o layout", "o palco"),
      ("6", "Defina o estilo", "cor · tipo · fluxo"),
      ("7", "Esboce as ideias", "esboços baratos")]),
    ("PARTE III — DÊ VIDA AO PROJETO", INK,
     [("8", "Monte o infográfico", "construção"),
      ("9", "Revise com método", "quatro lentes"),
      ("10", "Ajuste, finalize, publique", "lançamento")]),
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
m.text([MX, y + 6, 720, 66],
       "Regra de checagem: ao fim de cada parte, releia a frase do propósito. "
       "Se um elemento da página já não serve a ela, ele sai.",
       style=ST_BODYM)

# ================================================================ page 3 ----
m = scaffold("p03", "FUNDAMENTOS", 3)
m.text([MX, 150, CW, 60], "Por que infográficos funcionam", style=ST_H1)
m.text([MX, 224, 620, 176],
       "Um infográfico conta uma história com dados. Ele organiza o "
       "conteúdo em blocos visuais fáceis de consumir — melhora a "
       "compreensão e puxa conversa em torno da história que conta.", style=ST_LEAD)
for i, (t, b) in enumerate([
        ("Ele comprime", "Uma página carrega o que um relatório diria em "
         "dez — o leitor percebe a estrutura antes de ler uma palavra."),
        ("Ele circula", "Uma única imagem percorre sites, newsletters e "
         "redes sociais — alcançando públicos que um relatório nunca "
         "alcançaria."),
        ("Ele persuade", "Unir evidência e narrativa engaja julgamento e "
         "atenção: os dados conquistam confiança; o design, tempo.")]):
    x, w = col(0, 2)
    x = MX + i * (w + GUT) if False else col(i * 2, 2)[0]
    card(m, [x, 410, w, 244], t, b)
# Anatomy of the form, labelled.
m.text([MX, 672, 500, 40], "Anatomia do formato", style=ST_H3)
ax, ay, aw, ah = MX, 720, 360, 700
m.rect([ax, ay, aw, ah], fill=PAPER)
m.rect([ax, ay, aw, 74], fill=INK)
m.text([ax + 20, ay + 24, aw - 40, 30], "TÍTULO QUE ATRAI", style=ST_FOOT)
m.rect([ax + 20, ay + 96, aw - 40, 56], fill=PANEL)
m.rect([ax + 20, ay + 172, aw - 40, 120], fill=ACCENT)
m.text([ax + 40, ay + 216, aw - 80, 40], "MENSAGEM CENTRAL", style=ST_FOOT)
for i in range(3):
    m.rect([ax + 20 + i * ((aw - 40 - 24) / 3 + 12),
            ay + 316, (aw - 40 - 24) / 3, 130], fill=PANEL)
m.rect([ax + 20, ay + 470, aw - 40, 90], fill=PANEL)
m.rect([ax + 20, ay + 584, aw - 40, 64], fill=ACCENT2)
m.text([ax + 40, ay + 604, aw - 80, 28], "CHAMADA PARA AÇÃO", style=ST_FOOT)
labels = [
    ("Um título que fisga o público para o qual foi escrito", ay + 26),
    ("Uma introdução que prepara o terreno — o que o leitor precisa "
     "para acompanhar o resto", ay + 110),
    ("A única mensagem que todo o resto existe para sustentar", ay + 220),
    ("Evidências em blocos: gráficos, matrizes de ícones, ilustrações — "
     "cada uma amarrada à mensagem", ay + 360),
    ("Uma conclusão que fecha o ciclo do propósito", ay + 495),
    ("Uma chamada que diz ao leitor o que fazer em seguida", ay + 600)]
for text, ly in labels:
    m.line([ax + aw + 14, ly + 12], [ax + aw + 44, ly + 12],
           **_stroke(2, color=ACCENT))
    m.text([ax + aw + 56, ly, W - MX - ax - aw - 60, 78], text, style=ST_BODY)

# ================================================================ page 4 ----
m = scaffold("p04", "PARTE I — CONSTRUA UMA MENSAGEM PODEROSA", 4)
y = step_head(m, "1", "Identifique seu público",
              "Toda escolha que vem depois — dados, layout, cor, canal — "
              "pertence ao leitor, não a você. Dê nome a ele primeiro.")
m.text([MX, y, 460, 34], "Perguntas de partida", style=ST_H3)
for i, q in enumerate([
        "QUEM são as partes interessadas nesta história?",
        "O QUE elas precisam descobrir nela?",
        "COMO vão encontrá-la — impressa ou na tela do celular?",
        "ONDE ela vai alcançá-las: relatório, site, feed?"]):
    m.circle([MX + 14, y + 66 + i * 68], 5, fill=ACCENT)
    m.text([MX + 38, y + 50 + i * 68, 440, 62], q, style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 490, 34], "O que cada leitor precisa", style=ST_H3)
for i, (who, want) in enumerate([
        ("Financiadores", "evidências de custo-efetividade e resultados"),
        ("Gestores", "estatísticas amplas para agir e citar"),
        ("Equipe local", "números que motivam o trabalho diário"),
        ("Público geral", "uma história que dispensa contexto prévio")]):
    cy = y + 52 + i * 96
    m.rect([x2, cy, W - MX - x2, 84], fill=PAPER)
    m.rect([x2, cy, 8, 84], fill=MUTED)
    m.text([x2 + 24, cy + 14, 220, 30], who, style=ST_CARDT)
    m.text([x2 + 24, cy + 48, W - MX - x2 - 40, 30], want, style=ST_BODYM)
challenge(m, y + 500,
          "Vários públicos ao mesmo tempo? Desenhe para o principal e "
          "verifique se nada confunde ativamente os demais.")
action_strip(m, [
    "Escreva uma frase nomeando seu público principal.",
    "Liste três coisas que ele já sabe.",
    "Decida em que tela ou suporte ele vai encontrar a peça."], y=y + 640)

# ================================================================ page 5 ----
m = scaffold("p05", "PARTE I — CONSTRUA UMA MENSAGEM PODEROSA", 5)
y = step_head(m, "2", "Defina o propósito",
              "O porquê. Ter clareza absoluta de propósito — e cobrar de cada "
              "decisão posterior que responda a ele — é o que torna um "
              "infográfico uma ferramenta poderosa de comunicação.")
hub_x, hub_y, hub_r = W / 2, y + 300, 118
for ang, label in [(-150, "História"), (-90, "Dados"), (-30, "Layout"),
                   (30, "Design"), (90, "Esboço"), (150, "Difusão")]:
    import math
    ex = hub_x + math.cos(math.radians(ang)) * 300
    ey = hub_y + math.sin(math.radians(ang)) * 210
    m.line([hub_x, hub_y], [ex, ey], **_stroke(2, color=MUTED))
    m.circle([ex, ey], 56, fill=PAPER)
    m.circle([ex, ey], 56, fill="none", **_stroke(2.5, color=INK))
    m.text([ex - 62, ey - 14, 124, 28], label, style=ST_CARDT_C)
m.circle([hub_x, hub_y], hub_r, fill=ACCENT)
m.text([hub_x - 90, hub_y - 30, 180, 60], "PROPÓSITO", style=ST_WHITET_C)
m.text([MX, y + 560, 700, 92],
       "Cada raio responde ao centro: quando um gráfico, uma cor ou um canal "
       "não sabe dizer a que parte do propósito serve, é decoração.",
       style=ST_BODYM)
for i, (tag, txt, tint) in enumerate([
        ("UM PROPÓSITO QUE FUNCIONA", "“Este infográfico existe para que "
         "gestores escolares adotem a nova lista de verificação.”", ACCENT2),
        ("VAGO DEMAIS PARA GUIAR O DESIGN", "“Este infográfico existe para "
         "que as pessoas conheçam nosso estudo.”", ACCENT)]):
    ex_x = MX + i * (CW / 2 + 11)
    m.rect([ex_x, y + 680, CW / 2 - 11, 170], fill=PAPER)
    m.rect([ex_x, y + 680, 8, 170], fill=tint)
    m.text([ex_x + 24, y + 698, CW / 2 - 60, 24], tag, style=ST_KICK2)
    m.text([ex_x + 24, y + 730, CW / 2 - 60, 104], txt, style=ST_BODY)
challenge(m, y + 880,
          "Parte de um estudo maior? O propósito do infográfico é mais "
          "estreito que o do estudo — um achado bem contado, não todos.")
action_strip(m, [
    "Complete: “Este infográfico existe para que ___ faça ___.”",
    "Deixe a frase à vista, ao lado da tela.",
    "Confronte cada decisão posterior com ela."], y=y + 1020)

# ================================================================ page 6 ----
m = scaffold("p06", "PARTE I — CONSTRUA UMA MENSAGEM PODEROSA", 6)
y = step_head(m, "3", "Crie a história",
              "O quê. Uma história não é subproduto de encher a página de "
              "imagens bonitas — ela se decide aqui, antes de existir "
              "qualquer visual.")
seq = [("TÍTULO", "Um título que faz o leitor parar", ACCENT),
       ("INTRODUÇÃO", "O contexto de que a mensagem precisa", ACCENT2),
       ("MENSAGEM CENTRAL", "A única coisa que você precisa dizer", INK),
       ("CONCLUSÃO + AÇÃO", "Reforce o propósito; diga o que fazer", ACCENT2)]
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
m.text([MX, y + 268, 480, 34], "Títulos que rendem mais", style=ST_H3)
m.text([MX, y + 314, 470, 190],
       "Abra com o achado, não com o tema. “Implementação da política no "
       "ensino básico: lições aprendidas” diz o que o leitor vai levar e "
       "por que isso importa — um rótulo como “Resultados do estudo” não "
       "diz nada.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y + 268, 460, 34], "Uma mensagem, com fonte", style=ST_H3)
m.text([x2, y + 314, W - MX - x2, 150],
       "Desenvolva uma única mensagem central convincente e conclua com "
       "propósito. Cite as fontes no próprio gráfico — credibilidade "
       "também é design.", style=ST_BODY)
challenge(m, y + 510,
          "A história não cabe? Você tem duas mensagens — divida em "
          "dois infográficos em vez de borrar um.")
action_strip(m, [
    "Rascunhe título e mensagem central em frases simples.",
    "Escreva a introdução que alguém de fora precisaria.",
    "Escolha a ação que a conclusão vai pedir."], y=y + 650)


# ================================================================ page 7 ----
m = scaffold("p07", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 7)
y = step_head(m, "4a", "Escolha dados e visuais",
              "A partir da mensagem central, decida quais dados importam e "
              "como cada um será mostrado. Visual é evidência, não "
              "decoração.")
fams = [("Ícones", "Um conceito comprimido em símbolo; pinte e "
         "agrupe com consistência."),
        ("Fotografias", "Pessoas e lugares reais — licenciados e "
         "fiéis ao mundo do leitor."),
        ("Ilustrações", "Explicam o que a câmera não alcança: processos, "
         "sistemas, o que ainda não existe."),
        ("Gráficos", "Diagramas que sustentam os números por trás "
         "da mensagem.")]
sw = (CW - 3 * 22) / 4
for i, (t, b) in enumerate(fams):
    x = MX + i * (sw + 22)
    card(m, [x, y + 10, sw, 248], t, b)
m.text([MX, y + 290, 470, 34], "Matrizes de ícones", style=ST_H3)
m.text([MX, y + 334, 460, 190],
       "Leitores tendem a processar e lembrar melhor ícones em forma de "
       "pessoa do que círculos ou formas abstratas. Quando o dado é sobre "
       "pessoas, deixe que as marcas sejam pessoas — um símbolo por "
       "unidade, preenchendo até chegar ao número.", style=ST_BODY)
ax0 = MX + 530
m.rect([ax0 - 20, y + 290, W - MX - ax0 + 20, 190], fill=PAPER)
for r in range(2):
    for i in range(5):
        px, py = ax0 + i * 78, y + 316 + r * 84
        filled = (r * 5 + i) < 7
        c = ACCENT2 if filled else FAINT
        m.circle([px + 16, py + 10], 11, fill=c)
        m.rect([px + 6, py + 26, 20, 34], fill=c)
m.text([ax0, y + 492, 400, 26], "ex.: “7 em cada 10 concluíram o programa”",
       style=ST_SMALL)
m.text([MX, y + 540, 700, 110],
       "Dois deveres antes de publicar: os visuais precisam respeitar a "
       "cultura de quem os lê, e cada imagem, ícone e foto precisa ter a "
       "licença verificada.", style=ST_BODYM)
action_strip(m, [
    "Liste cada afirmação que a mensagem faz.",
    "Associe uma família visual a cada afirmação.",
    "Verifique licenças e adequação cultural agora, não no fim."], y=y + 700)

# ================================================================ page 8 ----
m = scaffold("p08", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 8)
y = step_head(m, "4b", "Escolha o gráfico certo",
              "Um gráfico, uma afirmação. Escolha o tipo de gráfico que revela "
              "o desenho da afirmação — e corte tudo de que ela não precisa.")
qw = (CW - 22) / 2
def chart_panel(x, y2, title, note):
    m.rect([x, y2, qw, 300], fill=PAPER)
    m.text([x + 24, y2 + 20, qw - 48, 30], title, style=ST_CARDT)
    m.text([x + 24, y2 + 244, qw - 48, 52], note, style=ST_SMALL)
    return x + 40, y2 + 80
bx, by = chart_panel(MX, y + 20, "Comparação — barras",
                     "Ordene as barras por valor; rotule direto na marca.")
for i, f in enumerate([1.0, 0.7, 0.55, 0.45]):
    bh = int(130 * f)
    m.rect([bx + i * 100, by + 140 - bh, 64, bh],
           fill=(ACCENT if f == 1.0 else ACCENT2))
    m.text([bx + i * 100, by + 116 - bh, 64, 22], str(int(f * 48)),
           style=ST_SMALL)
m.line([bx - 6, by + 140], [bx + 380, by + 140], **_stroke(2.5, color=INK))
lx, ly = chart_panel(MX + qw + 22, y + 20, "Tendência — linha",
                     "O tempo corre da esquerda para a direita; marque o ponto que importa.")
pts = [[lx + i * 72, ly + 130 - v] for i, v in
       enumerate([8, 46, 30, 78, 60, 122])]
m.polyline(pts, **_stroke(5, color=ACCENT2))
m.circle([pts[-1][0], pts[-1][1]], 9, fill=ACCENT)
m.line([lx - 6, ly + 140], [lx + 380, ly + 140], **_stroke(2.5, color=INK))
px_, py_ = chart_panel(MX, y + 360, "Parte de um todo — rosca",
                       "Poucas fatias, uma em destaque; porcentagens rotuladas.")
m.ring([px_ + 160, py_ + 70], 92, 54, fill=ACCENT2)
m.sector([px_ + 160, py_ + 70], 92, -90, 20, fill=ACCENT)
m.circle([px_ + 160, py_ + 70], 54, fill=PAPER)
m.text([px_ + 268, py_ - 10, 80, 24], "31%", style=ST_SMALL)
m.text([px_ + 10, py_ + 120, 80, 24], "69%", style=ST_SMALL)
sx, sy = chart_panel(MX + qw + 22, y + 360, "Relação — dispersão",
                     "Duas medidas por marca; deixe o agrupamento contar a história.")
import random
random.seed(7)
for _ in range(26):
    rx = sx + 20 + random.random() * 330
    ry = sy + 20 + (1 - (rx - sx - 20) / 360) * 110 + random.random() * 34
    m.circle([rx, ry], 6, fill=ACCENT2)
m.circle([sx + 320, sy + 34], 8, fill=ACCENT)
m.line([sx - 6, sy + 150], [sx + 374, sy + 150], **_stroke(2.5, color=INK))
m.text([MX, y + 700, CW, 34], "Depois, corte o excesso", style=ST_H3)
for i, tip in enumerate([
        "Corte linhas de grade, bordas e legendas que os rótulos já substituem.",
        "Vários tratamentos de fonte num só gráfico somam ruído, não ordem.",
        "Se um recurso não agrega valor visual — como uma seta de que "
        "ninguém precisa — apague-o."]):
    m.circle([MX + 14, y + 762 + i * 68], 5, fill=ACCENT)
    m.text([MX + 38, y + 746 + i * 68, 640, 64], tip, style=ST_BODY)
challenge(m, y + 950,
          "Em dúvida entre dois gráficos? Esboce os dois e mostre a um "
          "colega por três segundos cada — fique com o que ele conseguir "
          "repetir.")

# ================================================================ page 9 ----
m = scaffold("p09", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 9)
y = step_head(m, "5a", "Selecione o layout",
              "O layout é a interface com o público: o lugar onde ele encontra "
              "a peça define formato, tamanho e nível de interação.")
m.text([MX, y, 470, 34], "O formato segue o meio", style=ST_H3)
m.rect([MX, y + 54, 150, 240], fill=PAPER)
m.rect([MX, y + 54, 150, 34], fill=ACCENT2)
m.text([MX + 170, y + 54, 300, 120],
       "O vertical acompanha a rolagem da web e do celular — o padrão "
       "de feeds e páginas.", style=ST_BODY)
m.rect([MX, y + 330, 240, 150], fill=PAPER)
m.rect([MX, y + 330, 34, 150], fill=ACCENT2)
m.text([MX + 260, y + 330, 210, 150],
       "O horizontal serve a slides, telas e comparações lado a lado.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 460, 34], "A escada de interação", style=ST_H3)
for i, (t, b) in enumerate([
        ("Estático", "impresso e PDF — uma leitura fixa"),
        ("Clicável", "regiões levam a fontes e detalhes"),
        ("Animado", "o movimento revela a história em etapas"),
        ("Vídeo", "histórias de dados narradas para feeds"),
        ("Interativo", "o leitor explora o próprio caminho")]):
    cy = y + 50 + i * 88
    m.rect([x2, cy, W - MX - x2, 76], fill=PAPER)
    m.rect([x2, cy, 8, 76], fill=(ACCENT if i == 0 else MUTED))
    m.text([x2 + 24, cy + 12, 220, 28], t, style=ST_CARDT)
    m.text([x2 + 24, cy + 44, W - MX - x2 - 40, 26], b, style=ST_SMALL)
challenge(m, y + 540,
          "Vai virar pôster? Visuais de baixa resolução ficam serrilhados "
          "ao ampliar, e o respiro que parecia certo na tela pode virar "
          "vazio na parede — reveja os dois em escala real.")
action_strip(m, [
    "Nomeie a superfície principal: impresso, página, feed ou parede.",
    "Escolha a orientação pela superfície, não por hábito.",
    "Adote o menor nível de interação que sirva ao propósito."], y=y + 680)

# =============================================================== page 10 ----
m = scaffold("p10", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 10)
y = step_head(m, "5b", "O grid conduz o olhar",
              "Hierarquia é conduzir o leitor pela mão: grupos, colunas e "
              "níveis dizem onde começar e o que ler depois. O grid torna "
              "essa ordem repetível.")
grids = [("Manuscrito", "uma coluna de história contínua"),
         ("Multicoluna", "narrativas paralelas e comparações"),
         ("Modular", "cartões de blocos de mesmo peso"),
         ("Hierárquico", "zonas dimensionadas pela importância")]
sw = (CW - 3 * 22) / 4
for i, (t, b) in enumerate(grids):
    x = MX + i * (sw + 22)
    m.rect([x, y + 20, sw, 292], fill=PAPER)
    gx, gy, gw2 = x + 20, y + 40, sw - 40
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
    m.text([x + 20, y + 236, sw - 40, 30], t, style=ST_CARDT)
    m.text([x + 20, y + 270, sw - 40, 50], b, style=ST_SMALL)
m.text([MX, y + 352, 470, 34], "Equilibre os pesos visuais", style=ST_H3)
m.text([MX, y + 398, 460, 245],
       "Tudo na página atrai o olhar — o mais escuro, o maior ou o mais "
       "afastado do centro atrai com mais força. Equilibre como uma "
       "balança romana: um elemento pesado perto do eixo, compensado por "
       "um leve longe dele. Seções e respiro conduzem o olhar até a "
       "mensagem central.",
       style=ST_BODY)
bx0 = MX + 530
m.rect([bx0, y + 352, W - MX - bx0, 230], fill=PAPER)
fx = bx0 + (W - MX - bx0) / 2
m.line([fx, y + 382], [fx, y + 532], **_stroke(2, color=FAINT))
m.line([bx0 + 40, y + 532], [W - MX - 40, y + 532], **_stroke(3, color=INK))
m.rect([fx - 150, y + 442, 120, 90], fill=ACCENT)
m.rect([fx + 170, y + 496, 44, 36], fill=ACCENT2)
m.text([bx0 + 24, y + 592, W - MX - bx0 - 48, 50],
       "pesado perto do eixo · leve longe dele — repouso sem simetria",
       style=ST_SMALL)
challenge(m, y + 690,
          "Uma seção que ninguém lê? Ou está fora do grid, ou fora da "
          "mensagem, ou ambos — traga-a para o grid ou tire-a da peça.")
action_strip(m, [
    "Escolha a família de grid antes de posicionar qualquer coisa.",
    "Dê a cada seção uma zona do tamanho da sua importância.",
    "Aperte os olhos: uma massa focal compensada — não cinco gritando."], y=y + 830)

# =============================================================== page 11 ----
m = scaffold("p11", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 11)
y = step_head(m, "6a", "Cor com intenção",
              "Escolha um esquema que sirva ao público e à mensagem, dê a "
              "cada cor uma função e aplique tudo com consistência — cor "
              "é informação, não tinta.")
duties = [(GROUND, "FUNDO", "um papel só — o campo onde tudo assenta"),
          (INK, "TINTA", "quase-preto para o texto; nunca preto puro"),
          (MUTED, "NEUTRA", "cinzas da própria escala da tinta"),
          (ACCENT, "DESTAQUE", "um matiz, uma função: ênfase"),
          (ACCENT2, "SECUNDÁRIA", "a complementar, contida — dados")]
sw = (CW - 4 * 20) / 5
for i, (c, t, b) in enumerate(duties):
    x = MX + i * (sw + 20)
    m.rect([x, y + 10, sw, 96], fill=c)
    if c == GROUND:
        m.rect([x, y + 10, sw, 96], fill="none", **_stroke(2, color=FAINT))
    m.text([x, y + 122, sw, 24], t, style=ST_KICK2)
    m.text([x, y + 150, sw, 72], b, style=ST_SMALL)
m.text([MX, y + 250, 500, 34], "Dose como uma página", style=ST_H3)
m.rect([MX, y + 300, int(CW * 0.60), 44], fill=GROUND)
m.rect([MX, y + 300, int(CW * 0.60), 44], fill="none", **_stroke(2, color=FAINT))
m.rect([MX + int(CW * 0.60), y + 300, int(CW * 0.30), 44], fill=INK)
m.rect([MX + int(CW * 0.90), y + 300, CW - int(CW * 0.90), 44], fill=ACCENT)
m.text([MX, y + 354, CW, 26],
       "fundo ~60%   ·   texto e estrutura ~30%   ·   destaque ~10%",
       style=ST_SMALL)
m.text([MX, y + 420, 470, 34], "O teste do cinza", style=ST_H3)
m.text([MX, y + 464, 460, 156],
       "Tire a cor do design. Se a hierarquia ainda se lê em tons de "
       "cinza, ela foi construída em tom e sobreviverá à impressão, à "
       "projeção e a todos os olhares. Se ela se dissolver, confiou só "
       "no matiz.", style=ST_BODY)
gx0 = MX + 530
for k, (c1, c2, c3) in enumerate([(ACCENT, ACCENT2, PANEL),
                                  ("#6B6B6B", "#4A4A4A", "#DDDDDD")]):
    ox = gx0 + k * 240
    m.rect([ox, y + 420, 210, 170], fill=PAPER)
    m.rect([ox + 18, y + 438, 80, 60], fill=c1)
    m.rect([ox + 112, y + 438, 80, 100], fill=c2)
    m.rect([ox + 18, y + 512, 80, 60], fill=c3)
    m.text([ox + 18, y + 552, 174, 24],
           "em cores" if k == 0 else "em cinza — legível",
           style=ST_SMALL)
challenge(m, y + 660,
          "Precisa de um segundo destaque? Use o complementar do primeiro, "
          "contido — nunca os dois em força e área iguais.")
action_strip(m, [
    "Escolha o esquema; anote a função de cada cor ao lado da amostra.",
    "Aplique as cores aos elementos com consistência, na página toda.",
    "Imprima uma vez em cinza antes que alguém a veja em cores."], y=y + 800)

# =============================================================== page 12 ----
m = scaffold("p12", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 12)
y = step_head(m, "6b", "Tipografia em harmonia",
              "As fontes sustentam a leitura. Escolha poucas, dimensione por "
              "uma escala única e deixe o tamanho — não o enfeite — "
              "expressar a hierarquia.",)
m.text([MX, y, 470, 34], "Uma escada de corpos", style=ST_H3)
ladder = [("Display 51", S_H1, 700), ("Título 41", S_H2, 700),
          ("Subtítulo 33", S_H3, 650), ("Entrada 26", S_LEAD, 400),
          ("Texto 21", S_BODY, 400), ("Legenda 17", S_SMALL, 400)]
ly2 = y + 50
for label, size, wgt in ladder:
    stl = doc.define_text_style(f"lad{size}", font_family=DISPLAY if wgt >= 650
                                else SANS, font_size=size, color=INK,
                                font_weight=wgt)
    m.text([MX, ly2, 470, size + 14], label, style=stl)
    ly2 += size + 26
m.text([MX, ly2 + 8, 460, 116],
       "Cada nível está a um passo de escala do outro — perto o bastante "
       "para ser família, longe o bastante para ser hierarquia.", style=ST_BODYM)
x2 = MX + 530
m.text([x2, y, 490, 34], "Enfeite não é hierarquia", style=ST_H3)
m.rect([x2, y + 50, W - MX - x2, 150], fill=PAPER)
m.rect([x2, y + 50, 8, 150], fill=ACCENT)
mark_no(m, x2 + 28, y + 74)
m.text([x2 + 90, y + 74, W - MX - x2 - 110, 112],
       "Negrito, itálico E sublinhado na mesma linha são ruído visual "
       "— três sinais disputando a mesma função.", style=ST_BODY)
m.rect([x2, y + 220, W - MX - x2, 150], fill=PAPER)
m.rect([x2, y + 220, 8, 150], fill=ACCENT2)
mark_yes(m, x2 + 26, y + 240)
m.text([x2 + 90, y + 244, W - MX - x2 - 110, 112],
       "Use o corpo da fonte (e um único passo de peso) para hierarquizar "
       "— uma mudança, um significado.", style=ST_BODY)
m.text([x2, y + 410, 460, 34], "Regra de pareamento", style=ST_H3)
m.text([x2, y + 454, W - MX - x2, 156],
       "Uma fonte display para a estrutura, uma de texto para a leitura e "
       "uma mono para números, se os dados pedirem. Cada fonte a mais "
       "precisa merecer o lugar.", style=ST_BODY)
challenge(m, y + 640,
          "Tentado por uma fonte decorativa? Componha o título nela, "
          "aperte os olhos e pergunte se o público — não o designer — "
          "ganha algo.")
action_strip(m, [
    "Escolha primeiro a fonte de texto; a display vem depois.",
    "Monte a escada com uma razão só; apague corpos avulsos.",
    "Corte tratamentos duplos onde dois sinais cumprem a mesma função."], y=y + 780)

# =============================================================== page 13 ----
m = scaffold("p13", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 13)
y = step_head(m, "6c", "Fluxo e ponto focal",
              "Decida onde o olhar pousa primeiro e a rota que percorre "
              "depois — e faça cada recurso da página servir a essa rota.")
m.text([MX, y, 460, 34], "Dê uma rota ao olhar", style=ST_H3)
for k, (label, path_pts) in enumerate([
        ("Caminho em Z — telas e pôsteres",
         [[0, 0], [300, 0], [40, 170], [320, 190]]),
        ("Caminho em coluna — rolagem e celular",
         [[160, 0], [160, 90], [160, 190]])]):
    ox, oy = MX + k * 250, y + 60
    m.rect([ox, oy, 220, 230], fill=PAPER)
    pts = [[ox + 30 + px * 0.53, oy + 24 + py * 0.9] for px, py in path_pts]
    m.polyline(pts, **_stroke(4, color=ACCENT2))
    m.circle([pts[0][0], pts[0][1]], 9, fill=ACCENT)
    ex_, ey_ = pts[-1]
    dx_, dy_ = ex_ - pts[-2][0], ey_ - pts[-2][1]
    ln_ = (dx_ * dx_ + dy_ * dy_) ** 0.5 or 1.0
    ux_, uy_ = dx_ / ln_, dy_ / ln_
    m.polygon([[ex_ + ux_ * 16, ey_ + uy_ * 16],
               [ex_ - uy_ * 8, ey_ + ux_ * 8],
               [ex_ + uy_ * 8, ey_ - ux_ * 8]], fill=ACCENT2)
    m.text([ox + 12, oy + 240, 210, 68], label, style=ST_SMALL)
x2 = MX + 560
m.text([x2, y, 440, 34], "Um ponto focal", style=ST_H3)
m.rect([x2, y + 60, 420, 230], fill=PAPER)
m.rect([x2 + 30, y + 88, 200, 130], fill=ACCENT)
m.rect([x2 + 250, y + 96, 70, 40], fill=PANEL)
m.rect([x2 + 250, y + 150, 70, 40], fill=PANEL)
m.rect([x2 + 330, y + 96, 70, 94], fill=PANEL)
m.text([x2, y + 300, 440, 150],
       "O elemento maior, mais escuro e mais afastado do centro vence o "
       "primeiro olhar — entregue essa vitória, deliberadamente, à "
       "mensagem central.",
       style=ST_BODY)
m.text([MX, y + 470, 700, 130],
       "Recursos precisam merecer o lugar: uma seta que não guia ninguém é "
       "ruído fantasiado de recurso. Adicione um recurso só quando a rota falhar sem "
       "ele — e corte-o assim que deixar de agregar valor visual.", style=ST_BODYM)
challenge(m, y + 560,
          "Para onde o olhar vai primeiro? Mostre o esboço por três "
          "segundos; se a resposta não for a mensagem central, "
          "redistribua os pesos.")
action_strip(m, [
    "Marque no esboço o primeiro olhar e a rota pretendida.",
    "Dimensione o ponto focal e ajuste seu tom para que ele vença — uma vez.",
    "Audite cada seta, fio e caixa: fique só com o que funciona."], y=y + 700)


# =============================================================== page 14 ----
m = scaffold("p14", "PARTE II — DESENHE UMA HISTÓRIA VISUAL", 14)
y = step_head(m, "7", "Esboce as ideias",
              "Papel é o software de design mais barato que você vai ter. "
              "Esboce o layout antes de qualquer ferramenta renderizar um "
              "pixel.")
m.text([MX, y, 460, 34], "Primeiro, o esboço básico", style=ST_H3)
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
m.text([sk_x + 46, sk_y + 150, 200, 30], "mensagem", style=ST_SMALL)
x2 = MX + 530
m.text([x2, y, 490, 34], "Depois, o detalhe", style=ST_H3)
m.text([x2, y + 50, W - MX - x2, 200],
       "A primeira passada posiciona as seções da história no layout. "
       "A segunda acrescenta o título real, os visuais escolhidos e as "
       "marcas de fluxo — ainda no papel, ainda descartável. Vá do layout "
       "do passo 5 ao esboço básico e ao detalhado antes de abrir "
       "qualquer plataforma de design.", style=ST_BODY)
m.rect([x2, y + 290, W - MX - x2, 254], fill=PAPER)
m.rect([x2, y + 290, 8, 254], fill=MUTED)
m.text([x2 + 26, y + 310, W - MX - x2 - 52, 30], "Por que funciona",
       style=ST_CARDT)
m.text([x2 + 26, y + 352, W - MX - x2 - 52, 176],
       "Um esboço que se descarta em dez segundos convida à crítica "
       "honesta; um rascunho polido se defende. Itere onde iterar é mais "
       "barato — e ajuste o processo ao seu fluxo criativo.",
       style=ST_BODY)
challenge(m, y + 590,
          "O software está puxando você para os modelos dele? Esboce a "
          "história primeiro — e faça a ferramenta servir ao esboço, não "
          "o contrário.")
action_strip(m, [
    "Esboce as zonas do layout do passo 5 em cinco minutos.",
    "Redesenhe uma vez com título, visuais e fluxo marcados.",
    "Mostre a um leitor antes de abrir o software."], y=y + 730)

# =============================================================== page 15 ----
m = scaffold("p15", "PARTE III — DÊ VIDA AO PROJETO", 15)
y = step_head(m, "8a", "Montagem: plataforma e base",
              "Escolha uma plataforma que você domine e que sirva ao formato, "
              "defina a tela e assente a base antes de qualquer conteúdo.")
m.text([MX, y, 470, 34], "Arquivos que escalam bem", style=ST_H3)
vx, vy = MX, y + 54
m.rect([vx, vy, 220, 190], fill=PAPER)
m.polygon([[vx + 40, vy + 150], [vx + 110, vy + 30], [vx + 180, vy + 150]],
          fill="none", **_stroke(4, color=ACCENT2))
m.text([vx, vy + 198, 220, 48], "vetor — nítido em qualquer tamanho",
       style=ST_SMALL)
rx0, ry0 = MX + 240, y + 54
m.rect([rx0, ry0, 220, 190], fill=PAPER)
steps = [(60, 128), (80, 108), (100, 88), (120, 68), (140, 48), (160, 28)]
for sxx, syy in steps:
    m.rect([rx0 + sxx, ry0 + syy, 22, 22], fill=MUTED)
m.text([rx0, ry0 + 198, 220, 48], "bitmap — serrilha ao ampliar",
       style=ST_SMALL)
m.text([MX, y + 310, 460, 230],
       "Arte vetorial (como SVG) escala sem perdas e pode carregar "
       "interatividade; imagens bitmap servem à fotografia. Para "
       "impressão, entregue bitmaps a cerca de 300 dpi no tamanho final — "
       "abaixo de uns 150 dpi, conte com serrilhado visível.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 490, 34], "A base, em ordem", style=ST_H3)
for i, (t, b) in enumerate([
        ("Dimensione a tela", "defina as medidas finais antes de tudo"),
        ("Fundo", "a cor de fundo vem primeiro"),
        ("Seções", "as zonas do layout, desenhadas como regiões"),
        ("Marcas visuais", "fios e faixas que marcam a rota")]):
    cy = y + 50 + i * 92
    m.rect([x2, cy, W - MX - x2, 80], fill=PAPER)
    m.text([x2 + 20, cy + 12, 44, 44], str(i + 1), style=ST_H3)
    m.text([x2 + 76, cy + 14, 300, 28], t, style=ST_CARDT)
    m.text([x2 + 76, cy + 46, W - MX - x2 - 96, 26], b, style=ST_SMALL)
challenge(m, y + 580,
          "Em dúvida na plataforma? Canva e PowerPoint favorecem rapidez e "
          "familiaridade; o Illustrator, controle. Julgue por formato de "
          "saída, licença e curva de aprendizado — não por quantidade de "
          "recursos.")
action_strip(m, [
    "Defina o tamanho da tela pela superfície escolhida.",
    "Pinte fundo, depois seções, depois marcas — nessa ordem.",
    "Reúna cada visual no tipo de arquivo certo antes de montar."], y=y + 720)

# =============================================================== page 16 ----
m = scaffold("p16", "PARTE III — DÊ VIDA AO PROJETO", 16)
y = step_head(m, "8b", "Montagem: construa a página",
              "Traga visuais e texto de forma deliberada: construa linearmente "
              "pela história, ou de dentro para fora em torno do ponto "
              "focal — nunca tudo ao mesmo tempo, em toda parte.")
bx1, by1 = MX, y + 40
m.rect([bx1, by1, 470, 300], fill=PAPER)
m.text([bx1 + 24, by1 + 18, 430, 30], "Construa linearmente", style=ST_CARDT)
for i in range(4):
    zy = by1 + 64 + i * 54
    m.rect([bx1 + 24, zy, 330, 40], fill=PANEL)
    m.text([bx1 + 366, zy + 6, 40, 30], str(i + 1), style=ST_H3)
m.text([bx1, by1 + 306, 470, 50],
       "de cima para baixo, seção a seção — a ordem natural da rolagem",
       style=ST_SMALL)
bx2 = MX + 530
m.rect([bx2, by1, W - MX - bx2, 300], fill=PAPER)
m.text([bx2 + 24, by1 + 18, 400, 30], "Em torno do ponto focal",
       style=ST_CARDT)
m.rect([bx2 + 150, by1 + 90, 170, 110], fill=ACCENT)
m.text([bx2 + 168, by1 + 128, 140, 30], "1", style=ST_WHITET)
for lbl, px2, py2 in [("2", bx2 + 60, by1 + 70), ("3", bx2 + 350, by1 + 84),
                      ("4", bx2 + 66, by1 + 196), ("5", bx2 + 356, by1 + 210)]:
    m.rect([px2, py2, 64, 48], fill=PANEL)
    m.text([px2 + 22, py2 + 8, 30, 30], lbl, style=ST_H3)
m.text([bx2, by1 + 306, W - MX - bx2, 50],
       "a mensagem primeiro; todo o resto na órbita dela",
       style=ST_SMALL)
m.text([MX, y + 430, 470, 34], "Capriche nas partes", style=ST_H3)
for i, tip in enumerate([
        "Ícones: pinte com a paleta, depois sobreponha e agrupe para que "
        "se movam como um objeto só.",
        "Formas: construa visuais próprios a partir de formas simples "
        "antes de recorrer a bancos de imagens.",
        "Gráficos: formate-os nas cores e na tipografia da página — "
        "gráfico não é captura de tela."]):
    m.circle([MX + 14, y + 496 + i * 68], 5, fill=ACCENT)
    m.text([MX + 38, y + 478 + i * 68, 640, 64], tip, style=ST_BODY)
challenge(m, y + 700,
          "Colocou tudo e ainda parece carregado? Reconstrua linearmente: "
          "uma seção por vez, e pare quando a história estiver contada.")
action_strip(m, [
    "Escolha a ordem: linear ou do ponto focal para fora.",
    "Agrupe cada seção pronta antes de começar a próxima.",
    "Pare de montar assim que a história estiver completa."], y=y + 840)

# =============================================================== page 17 ----
m = scaffold("p17", "PARTE III — DÊ VIDA AO PROJETO", 17)
y = step_head(m, "8c", "Acessível é o mínimo",
              "Acessibilidade faz parte da montagem, não é remendo: se um "
              "leitor não consegue perceber a história, ela não foi "
              "contada.")
for i, (t, b) in enumerate([
        ("Contraste", "O texto precisa se erguer do fundo em tom — cheque "
         "a razão, não a impressão. Mínimos: texto 4,5:1; display 3:1."),
        ("Texto alternativo", "Toda imagem com significado carrega uma "
         "alternativa em texto que conta a mesma história ao leitor de "
         "tela."),
        ("Ordem de leitura", "A estrutura que quem enxerga vê é a ordem "
         "que a tecnologia assistiva precisa percorrer."),
        ("Nunca só o matiz", "Daltônicos perdem hierarquia codificada só "
         "no matiz — codifique-a também em tom, posição ou rótulo.")]):
    x = MX + (i % 2) * (CW / 2 + 11)
    cy = y + 20 + (i // 2) * 200
    card(m, [x, cy, CW / 2 - 11, 180], t, b)
m.text([MX, y + 450, 470, 34], "A legenda, duas vezes", style=ST_H3)
lx0, ly0 = MX, y + 500
m.rect([lx0, ly0, 470, 150], fill=PAPER)
m.rect([lx0, ly0, 8, 150], fill=ACCENT)
mark_no(m, lx0 + 26, ly0 + 24)
for j, c in enumerate(["#C24D2C", "#27584F", "#C2A22C"]):
    m.circle([lx0 + 110 + j * 110, ly0 + 46], 14, fill=c)
    m.text([lx0 + 132 + j * 110, ly0 + 34, 80, 24], "série", style=ST_SMALL)
m.text([lx0 + 24, ly0 + 92, 420, 52],
       "só o matiz muda — hierarquia perdida para até 1 a cada 12 leitores",
       style=ST_SMALL)
lx1 = MX + 530
m.rect([lx1, ly0, W - MX - lx1, 150], fill=PAPER)
m.rect([lx1, ly0, 8, 150], fill=ACCENT2)
mark_yes(m, lx1 + 26, ly0 + 22)
labels2 = [("A · escuro", INK), ("B · médio", MUTED), ("C · claro", FAINT)]
for j, (lb, c) in enumerate(labels2):
    m.circle([lx1 + 110 + j * 120, ly0 + 46], 14, fill=c)
    m.text([lx1 + 96 + j * 120, ly0 + 70, 110, 24], lb, style=ST_SMALL)
m.text([lx1 + 24, ly0 + 92, W - MX - lx1 - 48, 52],
       "tom + rótulo carregam a hierarquia; o matiz dá caráter",
       style=ST_SMALL)
m.text([MX, y + 690, 680, 110],
       "Depois, corte o excesso uma última vez: decoração que não carrega "
       "informação cobra um preço de todo leitor — e quem usa tecnologia "
       "assistiva paga duas vezes.", style=ST_BODYM)
challenge(m, y + 810,
          "Imprima o rascunho em tons de cinza e leia a um braço de "
          "distância: o que sumir estará só no matiz — conserte no tom.")
action_strip(m, [
    "Verifique a razão de contraste de cada par texto/fundo.",
    "Escreva texto alternativo que conte a história, não os pixels.",
    "Releia a página em tons de cinza antes de aprovar."], y=y + 950)

# =============================================================== page 18 ----
m = scaffold("p18", "PARTE III — DÊ VIDA AO PROJETO", 18)
y = step_head(m, "9", "Revise com quatro lentes",
              "Um rascunho é uma hipótese. Revise com método — lista na "
              "mão — antes que o público revise por você.")
lenses = [("HISTÓRIA", "O título fisga? A introdução prepara o terreno? Há "
           "exatamente uma mensagem central, e a conclusão reforça o "
           "propósito?"),
          ("CONTEÚDO", "Cada afirmação é precisa e tem fonte? Os dados são "
           "atuais, relevantes e representados com honestidade?"),
          ("DESIGN", "Cor, tipo, fluxo e ponto focal servem à mensagem? A "
           "hierarquia se lê com os olhos apertados?"),
          ("VISUAIS", "Cada visual é da família certa para a afirmação — e "
           "está licenciado, culturalmente adequado e sem excesso?")]
sw = (CW - 22) / 2
for i, (t, b) in enumerate(lenses):
    x = MX + (i % 2) * (sw + 22)
    cy = y + 20 + (i // 2) * 246
    m.rect([x, cy, sw, 226], fill=PAPER)
    m.rect([x, cy, sw, 12], fill=(ACCENT if i % 3 == 0 else ACCENT2))
    m.text([x + 26, cy + 30, sw - 52, 30], t, style=ST_KICK)
    m.text([x + 26, cy + 68, sw - 52, 150], b, style=ST_BODY)
m.text([MX, y + 534, 470, 34], "Dois ritmos de revisão", style=ST_H3)
m.text([MX, y + 578, 460, 186],
       "Faça revisões de relance para a primeira impressão — o teste dos "
       "três segundos — e revisões profundas para precisão e design. "
       "Elas acham defeitos diferentes; você precisa das duas.", style=ST_BODY)
x2 = MX + 530
m.text([x2, y + 534, 490, 34], "Como escolher revisores", style=ST_H3)
m.text([x2, y + 578, W - MX - x2, 150],
       "Inclua pessoas do público real, um especialista no conteúdo e "
       "alguém capaz de julgar a adequação cultural — é na revisão que "
       "essa dúvida se resolve.", style=ST_BODY)
challenge(m, y + 780,
          "Os revisores discordam? Pese o retorno à luz do propósito e do "
          "público — não de quem argumentou por mais tempo.")
action_strip(m, [
    "Rode o teste dos três segundos com um leitor novo.",
    "Percorra as quatro lentes de cima a baixo.",
    "Registre todos os achados antes de corrigir qualquer um."], y=y + 920)

# =============================================================== page 19 ----
m = scaffold("p19", "PARTE III — DÊ VIDA AO PROJETO", 19)
y = step_head(m, "10", "Ajuste, finalize, publique",
              "Itere com disciplina, finalize com intenção e coloque a "
              "peça onde o público já está.")
m.text([MX, y, 470, 34], "Ajuste à luz do propósito", style=ST_H3)
import math as _math
cx0, cy0, cr = MX + 220, y + 240, 150
for k in range(4):
    a0 = -90 + k * 90
    m.sector([cx0, cy0], cr, a0 + 6, a0 + 78,
             fill=(ACCENT2 if k % 2 else PANEL))
arc = [[cx0 + _math.cos(_math.radians(a)) * (cr + 16),
        cy0 + _math.sin(_math.radians(a)) * (cr + 16)]
       for a in range(-176, -105, 7)]
m.polyline(arc, **_stroke(3, color=MUTED))
ae = arc[-1]
m.polygon([[ae[0] + 16, ae[1] + 5], [ae[0] - 8, ae[1] + 9], [ae[0] - 2, ae[1] - 13]],
          fill=MUTED)
lblc = [("ajustar", 0), ("alinhar", 1), ("editar", 2), ("finalizar", 3)]
for t, k in lblc:
    ang = _math.radians(-48 + k * 90)
    lx2 = cx0 + _math.cos(ang) * (cr + 44) - 40
    ly2 = cy0 + _math.sin(ang) * (cr + 44) - 12
    m.text([lx2, ly2, 96, 24], t, style=ST_SMALL_C)
m.circle([cx0, cy0], 74, fill=ACCENT)
m.text([cx0 - 64, cy0 - 26, 128, 52], "PROPÓSITO", style=ST_WHITET_C)
m.text([MX, y + 430, 460, 150],
       "A cada mudança, confira se o infográfico ainda se alinha ao "
       "propósito e à mensagem central. Ajuste que se afasta do propósito "
       "não é polimento — é um gráfico novo, não planejado.",
       style=ST_BODY)
x2 = MX + 530
m.text([x2, y, 490, 34], "Vá aonde o público está", style=ST_H3)
for i, (t, b) in enumerate([
        ("Página própria", "um endereço-base para onde tudo aponta"),
        ("Redes sociais", "no tamanho do feed — 1080×1080 ou 1080×1920"),
        ("Dentro do relatório", "o gráfico onde a decisão acontece"),
        ("Newsletter", "a história entregue, não apenas disponível")]):
    cy2 = y + 50 + i * 96
    m.rect([x2, cy2, W - MX - x2, 84], fill=PAPER)
    m.rect([x2, cy2, 8, 84], fill=MUTED)
    m.text([x2 + 24, cy2 + 12, 340, 30], t, style=ST_CARDT)
    m.text([x2 + 24, cy2 + 48, W - MX - x2 - 44, 28], b, style=ST_SMALL)
challenge(m, y + 620,
          "Trabalha em equipe? Junte quem narra os dados a quem domina "
          "a técnica — é a mistura, não um lado só, que entrega o resultado.")
action_strip(m, [
    "Congele a mensagem; edite só o modo de contar.",
    "Exporte no tamanho e formato de cada canal.",
    "Publique e escute — o público termina a revisão."], y=y + 760)

# =============================================================== page 20 ----
m = scaffold("p20", None, 20, footer_note="INFOGRÁFICOS QUE IMPRESSIONAM")
m.rect([0, 0, W, 14], fill=ACCENT)
m.text([MX, 90, 400, 26], "O MÉTODO COMPLETO", style=ST_KICK)
m.text([MX, 130, CW, 60], "Dez passos, uma página", style=ST_H1)
steps20 = [
    ("1", "Público", "nomeie PARA QUEM é e onde ele encontra a peça"),
    ("2", "Propósito", "escreva POR QUE ela existe, em uma frase"),
    ("3", "História", "título · intro · uma mensagem · conclusão + ação"),
    ("4", "Dados e visuais", "uma família visual por afirmação, licenciada"),
    ("5", "Layout", "formato e orientação pela superfície"),
    ("6", "Estilo", "uma paleta, uma escada de corpos, um ponto focal"),
    ("7", "Esboço", "papel primeiro; itere onde é barato"),
    ("8", "Montagem", "base, depois seções, depois visuais"),
    ("9", "Revisão", "história · conteúdo · design · visuais"),
    ("10", "Publicação", "ajuste ao propósito; publique onde o leitor está")]
ty = 230
for n, t, b in steps20:
    m.rect([MX, ty, 54, 54], fill="none", **_stroke(3, color=INK))
    m.text([MX + 74, ty - 2, 90, 44], n, style=ST_H2)
    m.text([MX + 170, ty - 2, 300, 40], t, style=ST_CARDT)
    m.text([MX + 480, ty + 2, CW - 480, 44], b, style=ST_BODYM)
    ty += 96
m.rect([MX, ty + 20, CW, 170], fill=INK)
m.text([MX + 40, ty + 44, CW - 80, 64],
       "Estrutura em tom antes do matiz. Uma mensagem antes de muitos "
       "gráficos. O leitor antes de tudo.", style=ST_INV)
m.circle([MX + 52, ty + 140], 10, fill=ACCENT)
m.text([MX + 76, ty + 126, CW - 130, 30],
       "Agora escolha um conjunto de dados e rode a Parte I — hoje.", style=ST_INVT)
m.rect([MX, ty + 20, 10, 170], fill=ACCENT)

# ------------------------------------------------------------------ write ---
doc.write(globals().get("OUTPUT_YAML_PATH", "infographics_guide.yaml"),
          fail_on_error=True)
