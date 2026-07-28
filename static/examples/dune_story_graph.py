"""dune_story_graph.py — a six-page visual essay of the Dune #1 story graph.

Source: a doc-ray story-graph analysis of Frank Herbert's *Dune* (book 1) —
32 coreference-resolved NER entities, 33 relationships, each edge carrying a
supporting sentence ordinal and a grounding grade (DIRECT / WEAK / GAP).

Design contract (typeface-and-colour skill):
  * rank (grade) is carried by TONE + LINE PATTERN + LABEL — never hue alone,
    so a GAP edge can never be mistaken for a stated fact.
  * closed palette: one warm desert ground, a parchment ink scale, one spice
    accent (the Imperium / emphasis) and a subdued Fremen-blue complement.
  * six-size modular scale (12 · ratio 1.333); EB Garamond SC display,
    EB Garamond body, IBM Plex Mono for counts and sentence citations.

Render:  ff-render, or the MCP run_sdk_client tool (to='pdf', max_pages=0).
"""
import math
from frameforge.sdk import DocumentBuilder
from frameforge.sdk.paint import stroke, radial_gradient, linear_gradient

GROUND, PANEL = "#141009", "#1D160D"
INK, INK_2, INK_3, INK_4 = "#EFE3CC", "#B8A889", "#7E7059", "#4C4133"
SPICE, BLUE, JADE, BLOOD = "#E8853A", "#5B93B5", "#63A088", "#C0555A"
W, H = 1600, 1000
XS, SM, MD, LG, XL, HERO = 12, 16, 21.3, 28.4, 37.9, 119.6
GAR, SC, MONO = "EB Garamond", "EB Garamond SC", "IBM Plex Mono"

GRADE = {
    "DIRECT": dict(w=2.3, dash=None, op=1.0, tone=INK),
    "WEAK":   dict(w=1.7, dash=[7, 5], op=0.66, tone=INK_2),
    "GAP":    dict(w=1.2, dash=[2, 6], op=0.34, tone=INK_4),
}


def build():  # noqa: C901 — one composer per section; splitting hurts readability
    doc = DocumentBuilder(title="Dune #1 — Story Graph", profile="deck")

    def T(n, f, s, c, **kw):
        return doc.define_text_style(n, font_family=f, font_size=s, color=c, **kw)

    st_hero = T("hero", SC, HERO, INK); st_h1 = T("h1", SC, XL, INK)
    st_kick = T("kick", MONO, XS, SPICE, letter_spacing=3.4)
    st_body = T("body", GAR, MD, INK_2, line_height=1.5)
    st_lead = T("lead", GAR, LG, INK, line_height=1.4)
    st_cite = T("cite", MONO, XS, INK_3); st_citS = T("citS", MONO, XS, SPICE)
    st_citB = T("citB", MONO, XS, BLUE)
    st_nodeL = T("nodeL", SC, SM, INK, align="center")
    st_nodeS = T("nodeS", SC, XS, INK_2, align="center")
    st_cnt = T("cnt", MONO, XS, INK_3, align="center")
    st_num = T("num", MONO, LG, SPICE); st_lab = T("lab", MONO, XS, INK_3, letter_spacing=2.2)
    st_note = T("note", GAR, SM, INK_3, italic=True, line_height=1.45)
    st_quote = T("quote", GAR, LG, INK, italic=True, line_height=1.35)
    st_barN = T("barN", MONO, XS, INK_2)

    def edge(lay, a, b, grade, ra=0, rb=0, arrow=True, bow=0.0):
        (x1, y1), (x2, y2) = a, b
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        sx, sy = x1 + ux * ra, y1 + uy * ra
        ex, ey = x2 - ux * (rb + (7 if arrow else 0)), y2 - uy * (rb + (7 if arrow else 0))
        g = GRADE[grade]
        if abs(bow) > 0.01:
            mx, my = (sx + ex) / 2, (sy + ey) / 2
            cx, cy = mx - uy * bow * L * 0.5, my + ux * bow * L * 0.5
            lay.curve([sx, sy], [ex, ey], control1=[cx, cy], control2=[cx, cy],
                      **stroke(g["w"], color=g["tone"], dash=g["dash"], cap="round"), opacity=g["op"])
        else:
            lay.line([sx, sy], [ex, ey], **stroke(g["w"], color=g["tone"], dash=g["dash"], cap="round"), opacity=g["op"])
        if arrow:
            ax, ay = x2 - ux * rb, y2 - uy * rb
            px, py = -uy, ux; s = 7.0
            lay.polygon([[ax, ay], [ax - ux * s + px * s * 0.45, ay - uy * s + py * s * 0.45],
                         [ax - ux * s - px * s * 0.45, ay - uy * s - py * s * 0.45]], fill=g["tone"], opacity=g["op"])

    def cap(lay, x, top, label, sub, count, wide=230):
        lay.text([x - wide / 2, top, wide, 21], label, style=st_nodeL); off = top + 21
        if sub is not None:
            lay.text([x - wide / 2, off, wide, 17], sub, style=st_nodeS); off += 17
        if count is not None:
            lay.text([x - wide / 2, off, wide, 16], str(count), style=st_cnt)

    def node(lay, x, y, r, hue, label, sub=None, count=None):
        lay.circle([x, y], r + 13, fill=hue, opacity=0.09)
        lay.circle([x, y], r, fill=hue, opacity=0.20)
        lay.circle([x, y], r, fill="none", **stroke(1.8, color=hue))
        lay.circle([x, y], max(2.0, r * 0.16), fill=hue)
        cap(lay, x, y + r + 6, label, sub, count)

    def hexnode(lay, x, y, r, hue, label, sub=None, count=None):
        pts = [[x + r * math.cos(math.radians(60 * i - 90)), y + r * math.sin(math.radians(60 * i - 90))] for i in range(6)]
        lay.polygon(pts, fill=hue, opacity=0.14)
        lay.polygon(pts, fill="none", **stroke(2.0, color=hue))
        cap(lay, x, y + r + 6, label, sub, count, 250)

    def dmnd(lay, x, y, r, hue, label, sub=None, count=None):
        d = [[x, y - r], [x + r, y], [x, y + r], [x - r, y]]
        lay.polygon(d, fill=hue, opacity=0.15)
        lay.polygon(d, fill="none", **stroke(2.0, color=hue))
        cap(lay, x, y + r + 7, label, sub, count)

    def rule(lay, x, y, w, color=INK_4, op=1.0):
        lay.line([x, y], [x + w, y], **stroke(1.0, color=color), opacity=op)

    def frame(p, kicker, title, n):
        p.layer("bg").rect([0, 0, W, H], fill=GROUND)
        t = p.layer("frame")
        t.text([84, 42, 900, 24], kicker, style=st_kick)
        t.text([84, 70, 1200, 60], title, style=st_h1)
        rule(t, 84, 148, W - 168, INK_4)
        t.text([W - 190, 42, 106, 24], f"{n:02d}", style=st_lab)
        return t

    # 1 · COVER
    p1 = doc.page("cover", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    p1.layer("bg").rect([0, 0, W, H], fill=GROUND)
    sky = p1.layer("sky")
    sky.rect([0, 0, W, 780], fill=linear_gradient([("#0E0B06", 0.0), ("#1C1409", 0.60), ("#3E2711", 1.0)], angle=180))
    sky.circle([W * 0.62, 762], 270, fill=radial_gradient([(SPICE, 0.0, 0.46), (SPICE, 0.55, 0.11), (SPICE, 1.0, 0.0)]))
    sky.circle([W * 0.62, 762], 78, fill=radial_gradient([("#FFD9A6", 0.0, 1.0), (SPICE, 0.72, 0.85), (SPICE, 1.0, 0.0)]))
    sky.circle([1318, 176], 34, fill=INK_2, opacity=0.15)
    sky.circle([1318, 176], 34, fill="none", **stroke(1.2, color=INK_2), opacity=0.32)
    sky.circle([1400, 132], 17, fill=INK_2, opacity=0.10)
    con = p1.layer("constellation")
    CST = [(190, 175), (268, 232), (352, 184), (300, 300), (196, 270), (430, 260), (1120, 202), (1186, 270),
           (1060, 288), (1240, 176), (700, 120), (786, 166), (872, 116), (600, 206), (940, 220), (520, 150)]
    for i in range(len(CST) - 1):
        if i % 3 != 2:
            con.line(list(CST[i]), list(CST[i + 1]), **stroke(0.8, color=INK_2), opacity=0.13)
    for c in CST:
        con.circle(list(c), 2.6, fill=INK_2, opacity=0.34)
    dn = p1.layer("dunes")

    def ridge(y0, amp, ph, fill, op=1.0):
        pts = [[x, y0 + amp * math.sin(x / 300.0 + ph) + amp * 0.35 * math.sin(x / 97.0 + ph * 2)] for x in range(-20, W + 40, 20)]
        pts += [[W + 40, H + 40], [-20, H + 40]]
        dn.polygon(pts, fill=fill, opacity=op)
    ridge(772, 26, 0.4, "#4A2E13", 0.95); ridge(842, 30, 2.1, "#33200E")
    ridge(918, 24, 4.2, "#22150A"); ridge(972, 18, 5.6, "#160E06")
    ttl = p1.layer("title")
    ttl.text([84, 236, 1000, 164], "DUNE", style=st_hero)
    ttl.text([88, 406, 1000, 26], "A STORY GRAPH OF BOOK ONE", style=st_kick)
    rule(ttl, 88, 444, 470, SPICE)
    ttl.text([88, 462, 640, 150], "Thirty-two entities. Thirty-three relationships. Every edge carries the sentence that supports it — and a grade saying how far that support actually reaches.", style=st_body)
    for i, (v, l) in enumerate([("32", "VERTICES"), ("33", "EDGES"), ("20", "DIRECT"), ("6", "WEAK"), ("7", "GAP")]):
        x = 88 + i * 124
        ttl.text([x, 616, 150, 40], v, style=st_num)
        ttl.text([x + 2, 660, 150, 20], l, style=st_lab)
    rule(ttl, 88, 700, 700, INK_4)
    ttl.text([88, 712, 820, 22], "Frank Herbert · 416 pp · 18,128 sentences · 256,800 tokens", style=st_cite)
    ttl.text([88, 734, 820, 22], "Nodes: doc-ray entity_frequency · Edges: document_evidence retrieval", style=st_cite)
    ttl.text([88, 790, 760, 90], "Nothing here should be taken for granted. GAP edges are canonical relations the retrieval did not surface; they are drawn as absences, not facts.", style=st_note)

    # 2 · GRAPH
    p2 = doc.page("graph", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    frame(p2, "G = (V, E)  ·  COREFERENCE-RESOLVED", "The Story Graph", 2)
    fl = p2.layer("fields")

    def field(cx, cy, rx, ry, hue, name, sub, key):
        fl.ellipse([cx, cy], rx, ry, fill=hue, opacity=0.05)
        fl.ellipse([cx, cy], rx, ry, fill="none", **stroke(1.0, color=hue, dash=[3, 7]), opacity=0.34)
        fl.text([cx - 230, cy - ry - 34, 460, 20], name, style=T(f"f{key}", MONO, XS, hue, align="center", letter_spacing=3.0))
        fl.text([cx - 230, cy - ry - 14, 460, 18], sub, style=T(f"fs{key}", GAR, SM, INK_3, align="center", italic=True))
    field(300, 516, 238, 196, JADE, "HOUSE ATREIDES", "the protagonist cluster", "a")
    field(1320, 500, 208, 186, BLOOD, "HOUSE HARKONNEN", "the antagonist cluster", "h")
    field(846, 254, 340, 86, SPICE, "THE IMPERIUM", "the concealed third force", "i")
    field(846, 762, 290, 110, BLUE, "THE FREMEN", "the transformation", "f")
    N = {"G06": (586, 238, 17, SPICE), "P19": (716, 282, 15, SPICE), "P23": (866, 232, 22, SPICE),
         "G04": (1010, 286, 21, SPICE), "P17": (1136, 232, 15, SPICE), "L02": (104, 278, 14, INK_2),
         "P07": (178, 404, 21, JADE), "P03": (340, 388, 20, JADE), "P22": (462, 330, 16, JADE),
         "G01": (252, 504, 24, JADE), "P09": (470, 458, 16, JADE), "P02": (372, 556, 25, JADE),
         "P05": (120, 610, 19, JADE), "G05": (340, 672, 16, JADE), "P14": (150, 712, 14, JADE),
         "P01": (600, 660, 34, JADE), "L01": (846, 470, 30, INK_2), "G03": (846, 706, 23, BLUE),
         "P06": (600, 806, 20, BLUE), "P04": (716, 808, 21, BLUE), "P12": (846, 832, 16, BLUE),
         "P08": (986, 796, 19, BLUE), "P15": (1104, 714, 15, BLUE), "P16": (1206, 368, 14, BLOOD),
         "P13": (1330, 342, 18, BLOOD), "P11": (1462, 410, 16, BLOOD), "G02": (1320, 502, 25, BLOOD),
         "P10": (1462, 570, 17, BLOOD), "P20": (1200, 588, 13, BLOOD), "L03": (1470, 700, 14, INK_2)}
    LBL = {"P01": ("PAUL", "Muad'Dib · Usul", 1721), "P02": ("JESSICA", None, 755), "P03": ("DUKE LETO", None, 273),
           "P05": ("HAWAT", "Master of Assassins", 384), "P07": ("GURNEY HALLECK", None, 502),
           "P09": ("YUEH", "the traitor", 155), "P22": ("DUNCAN IDAHO", None, 131), "P14": ("ALIA", None, 93),
           "G01": ("ATREIDES", None, 87), "G02": ("HARKONNEN", None, 246), "P13": ("BARON", "Vladimir", 100),
           "P11": ("PITER", "mentat", 133), "P10": ("FEYD-RAUTHA", None, 151), "P16": ("RABBAN", None, 76),
           "P20": ("NEFUD", None, 52), "P23": ("EMPEROR", "Shaddam IV", None), "G04": ("SARDAUKAR", None, 181),
           "P19": ("IRULAN", "chronicler", 52), "P17": ("FENRING", None, 53), "G06": ("SPACING GUILD", None, 85),
           "G03": ("FREMEN", None, 488), "P04": ("STILGAR", "naib", 399), "P08": ("CHANI", None, 257),
           "P12": ("JAMIS", None, 116), "P15": ("HARAH", None, 83), "P06": ("KYNES", "Liet", 379),
           "G05": ("BENE GESSERIT", None, 47), "L01": ("ARRAKIS", "Dune", 304), "L02": ("CALADAN", None, None),
           "L03": ("GIEDI PRIME", None, None)}
    E = [("P01", "P03", "DIRECT", 0.10), ("P01", "P02", "DIRECT", -0.10), ("P02", "P03", "DIRECT", 0.0),
         ("P02", "G05", "DIRECT", 0.0), ("P03", "G01", "DIRECT", 0.0), ("P05", "G01", "DIRECT", 0.0),
         ("P09", "P01", "DIRECT", 0.0), ("P07", "G01", "GAP", 0.0), ("P22", "G01", "WEAK", 0.0),
         ("P22", "G03", "WEAK", 0.30), ("P14", "G01", "GAP", 0.0), ("P13", "G02", "DIRECT", 0.0),
         ("G01", "G02", "DIRECT", -0.18), ("G02", "L01", "DIRECT", 0.10), ("P11", "P13", "WEAK", 0.0),
         ("P10", "G02", "WEAK", 0.0), ("P16", "G02", "GAP", 0.0), ("P20", "P13", "GAP", 0.0),
         ("P23", "G01", "DIRECT", -0.12), ("P23", "P13", "DIRECT", 0.12), ("G04", "P23", "DIRECT", 0.0),
         ("G04", "G02", "DIRECT", 0.20), ("P09", "G01", "WEAK", 0.18), ("P06", "L01", "DIRECT", 0.0),
         ("P19", "P23", "WEAK", 0.0), ("G03", "L01", "DIRECT", 0.0), ("P04", "G03", "DIRECT", 0.0),
         ("P12", "P08", "DIRECT", 0.0), ("P12", "P01", "GAP", 0.0), ("P08", "P01", "GAP", 0.0),
         ("P08", "P06", "GAP", 0.0), ("G05", "P02", "DIRECT", -0.18), ("P01", "G03", "DIRECT", 0.14)]
    eL = p2.layer("edges")
    for s, d, gr, bw in E:
        (x1, y1, r1, _), (x2, y2, r2, _) = N[s], N[d]
        edge(eL, (x1, y1), (x2, y2), gr, ra=r1 + 3, rb=r2 + 3, bow=bw)
    nL = p2.layer("nodes")
    for nid, (x, y, r, hue) in N.items():
        lb, sb, ct = LBL[nid]
        (hexnode if nid[0] == "G" else dmnd if nid[0] == "L" else node)(nL, x, y, r, hue, lb, sb, ct)
    lg = p2.layer("legend")
    lg.rect([84, 906, 1432, 70], fill=PANEL)
    lg.rect([84, 906, 1432, 70], fill="none", **stroke(1.0, color=INK_4))
    for i, (gr, desc) in enumerate([("DIRECT", "a retrieved sentence states it"),
                                    ("WEAK", "implied, or both parties named"),
                                    ("GAP", "expected, not surfaced — unproven")]):
        lx = 108 + i * 396; gs = GRADE[gr]
        lg.line([lx, 940], [lx + 52, 940], **stroke(gs["w"], color=gs["tone"], dash=gs["dash"], cap="round"), opacity=gs["op"])
        lg.text([lx + 64, 926, 110, 20], gr, style=T(f"lg{gr}", MONO, XS, gs["tone"], letter_spacing=2.0))
        lg.text([lx + 64, 946, 300, 20], desc, style=st_note)
    lg.text([1300, 924, 206, 20], "○ person  ⬡ group  ◇ place", style=st_cite)
    lg.text([1300, 948, 206, 20], "radius ∝ √mentions", style=st_cite)

    # 3 · TRIANGLE
    p3 = doc.page("triangle", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    t3 = frame(p3, "THE PIVOT  ·  EVERY EDGE DIRECT-GROUNDED", "The Concealed Third Force", 3)
    t3.text([84, 178, 1150, 110], "Two houses in open enmity; a third power arranging the collision. This triangle is the causal engine of book one, and it is the only cluster in the graph whose every edge is DIRECT.", style=st_lead)
    TRI = {"A": (392, 632, JADE, "HOUSE ATREIDES", "granted Arrakis in fief-complete"),
           "H": (1208, 632, BLOOD, "HOUSE HARKONNEN", "held Arrakis eighty years"),
           "E": (800, 376, SPICE, "PADISHAH EMPEROR", "Shaddam IV · and the Sardaukar")}
    tl = p3.layer("tri")
    for k, (x, y, hue, name, sub) in TRI.items():
        tl.circle([x, y], 104, fill=hue, opacity=0.05)
        tl.circle([x, y], 78, fill=hue, opacity=0.14)
        tl.circle([x, y], 78, fill="none", **stroke(2.4, color=hue))
        tl.text([x - 220, y + 96, 440, 32], name, style=T(f"tn{k}", SC, MD, INK, align="center"))
        tl.text([x - 220, y + 128, 440, 22], sub, style=T(f"ts{k}", GAR, SM, INK_3, align="center", italic=True))

    def tri_edge(a, b, label, cite, side=1):
        (x1, y1, *_), (x2, y2, *_) = TRI[a], TRI[b]
        edge(tl, (x1, y1), (x2, y2), "DIRECT", ra=82, rb=82)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1
        lx, ly = mx + (-dy / L) * 44 * side, my + (dx / L) * 44 * side
        tl.text([lx - 190, ly - 24, 380, 24], label, style=T(f"te{a}{b}", MONO, XS, INK, align="center"))
        tl.text([lx - 190, ly + 2, 380, 22], cite, style=T(f"tc{a}{b}", MONO, XS, SPICE, align="center"))
    tri_edge("A", "H", "MORTAL ENEMY OF", "s34 · E12", side=1)
    tri_edge("E", "A", "GRANTS FIEF", "s35 · E18", side=-1)
    tri_edge("E", "H", "SECRETLY ALLIES", "s436 · E19", side=1)
    t3.text([84, 830, 700, 110], "“The Padishah Emperor believes he’s given the Duke your spice planet.”", style=st_quote)
    t3.text([84, 944, 700, 22], "sentence 436 — the mechanism, stated outright", style=st_citS)
    t3.text([856, 830, 660, 110], "Two legions of Sardaukar, disguised in Harkonnen livery, close the trap: the Imperium strikes while appearing never to have moved.", style=st_body)
    t3.text([856, 944, 660, 22], "s681 · E21 — SARDAUKAR attack_disguised_as HARKONNEN", style=st_citS)

    # 4 · SALIENCE
    p4 = doc.page("salience", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    f4 = frame(p4, "ENTITY FREQUENCY  ·  DOCUMENT-SCOPED", "Who the Book Is About", 4)
    f4.text([84, 178, 1180, 80], "Merged NER counts, linear scale. One protagonist is named more than twice as often as anyone else — salience before interpretation.", style=st_lead)
    BARS = [("PAUL", 1721, JADE), ("JESSICA", 755, JADE), ("GURNEY HALLECK", 502, JADE), ("FREMEN", 488, BLUE),
            ("STILGAR", 399, BLUE), ("HAWAT", 384, JADE), ("KYNES", 379, BLUE), ("ARRAKIS", 304, INK_2),
            ("DUKE LETO", 273, JADE), ("CHANI", 257, BLUE), ("HARKONNEN", 246, BLOOD), ("SARDAUKAR", 181, SPICE),
            ("YUEH", 155, JADE), ("FEYD-RAUTHA", 151, BLOOD), ("PITER", 133, BLOOD), ("DUNCAN IDAHO", 131, JADE),
            ("JAMIS", 116, BLUE), ("BARON", 100, BLOOD), ("ALIA", 93, JADE), ("SPACING GUILD", 85, SPICE)]
    bl = p4.layer("bars"); BW, MAXV = 418, 1721
    for i, (nm, v, hue) in enumerate(BARS):
        col = i // 10; row = i % 10; x0 = 84 + col * 760; y0 = 300 + row * 62
        bl.text([x0, y0 - 9, 200, 22], nm, style=T(f"bl{i}", SC, SM, INK, align="right"))
        bl.rect([x0 + 214, y0 - 7, BW, 16], fill=INK_4, opacity=0.35)
        bl.rect([x0 + 214, y0 - 7, max(3, BW * v / MAXV), 16], fill=hue, opacity=0.85)
        bl.text([x0 + 214 + BW + 12, y0 - 8, 72, 20], str(v), style=st_barN)
    f4.text([84, 918, 1180, 60], "Counts are pre-coreference artifacts: pronouns and “the Duke” are not included, so these approximate salience — they are not exact mention totals.", style=st_note)

    # 5 · NER DEFECTS
    p5 = doc.page("ner", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    f5 = frame(p5, "TAGGER DEFECTS  ·  WHY RAW COUNTS MISLEAD", "One Entity, Four Machines", 5)
    f5.text([84, 178, 1180, 80], "The tagger fractures single entities across incompatible types. Raw NER lists ~50 rows; the resolved graph has 32. Each defect below is a merge, not a judgement call.", style=st_lead)
    FRAG = [("Duncan Idaho", [("Idaho", "GPE", 96), ("Duncan", "PERSON", 35)], 131, "a man read as a U.S. state"),
            ("Arrakis", [("Arrakis", "LOC", 121), ("Arrakis", "GPE", 90), ("Arrakis", "PERSON", 49), ("Arrakis", "NORP", 44)], 304, "one planet, four entity types"),
            ("Fremen", [("Fremen", "NORP", 361), ("Fremen", "PERSON", 85), ("Fremen", "ORG", 42)], 488, "a people read three ways"),
            ("Gurney Halleck", [("Gurney", "PERSON", 294), ("Halleck", "PERSON", 159), ("Gurney Halleck", "PERSON", 49)], 502, "one man, three surface forms")]
    nl5 = p5.layer("frag")
    for i, (name, parts, total, note) in enumerate(FRAG):
        y = 316 + i * 156
        nl5.text([84, y - 56, 440, 26], name.upper(), style=T(f"fn{i}", SC, MD, INK))
        nl5.text([84, y - 24, 440, 22], note, style=st_note)
        x = 560
        for j, (tok, typ, cnt) in enumerate(parts):
            bw2 = 118
            nl5.rect([x, y - 34, bw2, 68], fill=BLOOD, opacity=0.10)
            nl5.rect([x, y - 34, bw2, 68], fill="none", **stroke(1.0, color=BLOOD, dash=[3, 4]), opacity=0.55)
            nl5.text([x, y - 30, bw2, 20], tok, style=T(f"ft{i}{j}", SC, XS, INK, align="center"))
            nl5.text([x, y - 9, bw2, 18], typ, style=T(f"fy{i}{j}", MONO, XS, BLOOD, align="center"))
            nl5.text([x, y + 11, bw2, 18], str(cnt), style=T(f"fc{i}{j}", MONO, XS, INK_3, align="center"))
            x += bw2 + 12
        ax = x + 6
        nl5.line([ax, y], [ax + 42, y], **stroke(1.6, color=SPICE), opacity=0.9)
        nl5.polygon([[ax + 52, y], [ax + 40, y - 6], [ax + 40, y + 6]], fill=SPICE)
        nl5.rect([ax + 66, y - 34, 152, 68], fill=JADE, opacity=0.14)
        nl5.rect([ax + 66, y - 34, 152, 68], fill="none", **stroke(1.6, color=JADE))
        nl5.text([ax + 66, y - 24, 152, 20], "RESOLVED", style=T(f"fr{i}", MONO, XS, JADE, align="center", letter_spacing=1.6))
        nl5.text([ax + 66, y - 1, 152, 26], str(total), style=T(f"fv{i}", MONO, MD, INK, align="center"))
        if i < 3:
            rule(nl5, 84, y + 82, W - 168, INK_4, 0.6)
    f5.text([84, 930, 1180, 40], "Also excluded: CARDINAL tokens (“one”, “two”, “half”) and one UNKNOWN (“system”) — not story entities.", style=st_note)

    # 6 · LIMITS
    p6 = doc.page("limits", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    f6 = frame(p6, "WHAT THIS GRAPH DOES NOT PROVE", "Seven Absences", 6)
    f6.text([84, 178, 1180, 80], "These are canonical Dune relationships the retrieval did not surface from book one. They are listed so the model is complete — and marked so it is never mistaken for evidence.", style=st_lead)
    GAPS = [("E08", "GURNEY HALLECK", "serves", "HOUSE ATREIDES", "role appears in Dune #3, s775 — not book 1"),
            ("E10", "ALIA", "relation", "HOUSE ATREIDES", "NER token present; no relational passage"),
            ("E16", "RABBAN", "relation", "HOUSE HARKONNEN", "NER token present; no relational passage"),
            ("E17", "NEFUD", "officer_under", "BARON", "role INFERRED from title alone"),
            ("E28", "JAMIS", "duels", "PAUL", "both placed in the sietch (s10299); duel not surfaced"),
            ("E29", "CHANI", "consort_of", "PAUL", "stated in Dune #3 s672; not in book 1"),
            ("E30", "CHANI", "daughter_of", "KYNES", "canonical; retrieval silent")]
    gl = p6.layer("gaps")
    for i, (eid, src, rel, dst, why) in enumerate(GAPS):
        y = 300 + i * 88
        gl.rect([84, y - 30, 1432, 68], fill=PANEL, opacity=0.55)
        gl.text([108, y - 16, 70, 22], eid, style=T(f"ge{i}", MONO, XS, INK_4, letter_spacing=1.4))
        gl.text([186, y - 18, 250, 26], src, style=T(f"gs{i}", SC, SM, INK_2))
        gl.text([430, y - 34, 200, 20], rel, style=T(f"gr{i}", MONO, XS, INK_3, align="center"))
        edge(gl, (450, y - 8), (610, y - 8), "GAP", arrow=True)
        gl.text([640, y - 18, 260, 26], dst, style=T(f"gd{i}", SC, SM, INK_2))
        gl.text([920, y - 16, 580, 22], why, style=st_note)
    gl.text([84, 928, 1432, 40], "Closing them needs targeted retrieval — document_evidence focused on “Jamis duel crysknife”, “Chani Kynes daughter”, “Kwisatz Haderach breeding”.", style=st_citB)

    return doc


if __name__ == "__main__":
    build().write(OUTPUT_YAML_PATH, fail_on_error=True)
