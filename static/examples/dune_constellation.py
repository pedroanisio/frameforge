"""dune_constellation.py — "The Proven Constellation".

A single portrait plate of the Dune #1 story graph, built on one mechanism:
a relationship's BRIGHTNESS is how far the text proves it. The one fully
DIRECT-grounded structure — the Emperor/Atreides/Harkonnen causal triangle —
burns as the plate's light source; that light fades through dashed WEAK to
dotted GAP into the unproven dark at the margins.

Encoding (grade never on hue alone — brightness + line pattern + label):
  DIRECT  bright solid filament, spice under-glow   (a retrieved sentence states it)
  WEAK    dim dashed                                (implied / both parties named)
  GAP     faint dotted — drawn as an absence        (expected, never surfaced)

A node's brightness tier is derived from its BEST incident edge, so the light
is data-honest. Star radius encodes salience (sqrt of merged NER mentions).
Paul is the lone blue star; Gurney Halleck is large but unlit (GAP tie).

Source: a doc-ray analysis of Frank Herbert's Dune, book 1 (entity_frequency
+ document_evidence). Render: run_sdk_client (to='pdf').
"""
import math
from frameforge.sdk import DocumentBuilder
from frameforge.sdk.paint import stroke, radial_gradient, linear_gradient

# ── closed palette: warm-monochrome + spice light + one blue visitor ──
D0, D1 = "#0A0805", "#15100A"          # ground gradient (desert night)
DUNE = "#20160C"
STAR = "#F2E7CE"                        # starlight / brightest ink
INK2, INK3, INK4 = "#C9B48C", "#6E634C", "#3A3327"   # dim / faint / ghost
SPICE = "#E8853A"                       # the light of certainty
GOLD = "#F5C98A"                        # lit warm core
BLUE = "#4E86A8"                        # Fremen
BLUEB = "#9FCBE0"                       # Paul (the singular blue star)
COOL = "#8FA0A6"                        # places
W, H = 1500, 2100

# fixed glow gradients — tier varies the circle's opacity, not the stop colours
# (keeps the palette census to the closed hue set instead of one rgba per node)
GLOW_GOLD = radial_gradient([(GOLD, 0.0, 0.5), (GOLD, 0.55, 0.16), (GOLD, 1.0, 0.0)])
GLOW_BLUE = radial_gradient([(BLUEB, 0.0, 0.5), (BLUEB, 0.55, 0.18), (BLUEB, 1.0, 0.0)])

# ── six-size modular scale, base 13 · ratio 1.333 ──
KCK, LBL, LBS, THS, BIG, HERO = 15, 17.3, 13, 23.1, 30.8, 97.2

RANK = {"DIRECT": 3, "WEAK": 2, "GAP": 1}
EDGE = [  # (src, dst, grade, bow)
    ("P01", "P03", "DIRECT", 0.10), ("P01", "P02", "DIRECT", -0.10), ("P02", "P03", "DIRECT", 0.0),
    ("P02", "G05", "DIRECT", 0.10), ("P03", "G01", "DIRECT", 0.0), ("P05", "G01", "DIRECT", 0.0),
    ("P09", "P01", "DIRECT", 0.0), ("P07", "G01", "GAP", 0.0), ("P22", "G01", "WEAK", 0.0),
    ("P22", "G03", "WEAK", 0.22), ("P14", "G01", "GAP", 0.0), ("P13", "G02", "DIRECT", 0.0),
    ("G01", "G02", "DIRECT", 0.0), ("G02", "L01", "DIRECT", 0.10), ("P11", "P13", "WEAK", 0.0),
    ("P10", "G02", "WEAK", 0.0), ("P16", "G02", "GAP", 0.0), ("P20", "P13", "GAP", 0.0),
    ("P23", "G01", "DIRECT", -0.14), ("P23", "P13", "DIRECT", 0.10), ("G04", "P23", "DIRECT", 0.0),
    ("G04", "G02", "DIRECT", 0.16), ("P09", "G01", "WEAK", 0.14), ("P06", "L01", "DIRECT", 0.0),
    ("P19", "P23", "WEAK", 0.0), ("G03", "L01", "DIRECT", 0.0), ("P04", "G03", "DIRECT", 0.0),
    ("P12", "P08", "DIRECT", 0.0), ("P12", "P01", "GAP", 0.0), ("P08", "P01", "GAP", 0.0),
    ("P08", "P06", "GAP", 0.0), ("G05", "P02", "DIRECT", -0.16), ("P01", "G03", "DIRECT", 0.0),
]
# id: (x, y, mentions, family)   family: warm | fremen | place | paul
NODE = {
    "P23": (760, 566, 120, "warm"), "G01": (556, 980, 87, "warm"), "G02": (980, 980, 246, "warm"),
    "L01": (768, 872, 304, "place"), "P13": (1074, 742, 100, "warm"), "G04": (930, 690, 181, "warm"),
    "P03": (478, 806, 273, "warm"), "P05": (388, 1012, 384, "warm"), "G05": (322, 1204, 47, "warm"),
    "P02": (556, 1168, 755, "warm"), "P09": (662, 1030, 155, "warm"),
    "P22": (620, 656, 131, "warm"), "P19": (1180, 520, 52, "warm"), "P11": (1298, 812, 133, "warm"),
    "P10": (1256, 1006, 151, "warm"),
    "P07": (222, 726, 502, "warm"), "P14": (292, 1382, 93, "warm"), "P16": (1344, 1136, 76, "warm"),
    "P20": (1346, 636, 52, "warm"),
    "P01": (724, 1298, 1721, "paul"), "G03": (966, 1372, 488, "fremen"), "P04": (1132, 1300, 399, "fremen"),
    "P06": (892, 1176, 379, "fremen"), "P08": (1092, 1470, 257, "fremen"), "P12": (952, 1536, 116, "fremen"),
    "P15": (1230, 1500, 83, "fremen"), "P18": (404, 1330, 53, "fremen"),
    "G06": (1206, 360, 85, "warm"), "P17": (1372, 928, 53, "warm"), "P21": (1372, 1330, 36, "warm"),
    "L02": (206, 470, 40, "place"), "L03": (1360, 1210, 40, "place"),
}
LABEL = {
    "P01": "PAUL", "P02": "JESSICA", "P03": "DUKE LETO", "P05": "HAWAT", "P07": "GURNEY HALLECK",
    "P09": "YUEH", "P22": "DUNCAN IDAHO", "P14": "ALIA", "G01": "ATREIDES", "G02": "HARKONNEN",
    "P13": "BARON", "P11": "PITER", "P10": "FEYD-RAUTHA", "P16": "RABBAN", "P20": "NEFUD",
    "P23": "EMPEROR", "G04": "SARDAUKAR", "P19": "IRULAN", "P17": "FENRING", "G06": "SPACING GUILD",
    "G03": "FREMEN", "P04": "STILGAR", "P08": "CHANI", "P12": "JAMIS", "P15": "HARAH", "P06": "KYNES",
    "G05": "BENE GESSERIT", "L01": "ARRAKIS", "L02": "CALADAN", "L03": "GIEDI PRIME",
    "P18": "MAPES", "P21": "TUEK",
}
# a few labels read better placed above their node (dense lower field)
ABOVE = {"P12", "P08", "P15", "P04", "P21", "L03", "P16"}


def build():
    doc = DocumentBuilder(title="Dune — The Proven Constellation", profile="deck")

    def T(n, f, s, c, **k):
        return doc.define_text_style(n, font_family=f, font_size=s, color=c, **k)

    GAR, SC, MONO = "EB Garamond", "EB Garamond SC", "IBM Plex Mono"
    st_hero = T("hero", SC, HERO, STAR, align="center", letter_spacing=6)
    st_kick = T("kick", MONO, KCK, SPICE, align="center", letter_spacing=6)
    st_ths = T("ths", GAR, THS, INK2, align="center", italic=True, line_height=1.4)
    st_legH = T("legH", SC, BIG, STAR)
    st_leg = T("leg", MONO, LBS, INK2)
    st_legG = T("legG", GAR, LBL, INK3, italic=True)
    st_prov = T("prov", MONO, LBS, INK3)
    st_provS = T("provS", MONO, LBS, SPICE)
    st_disc = T("disc", GAR, LBL, INK3, italic=True, align="center", line_height=1.4)
    # node-label tiers
    tier_style = {
        3: {"warm": T("nl3w", SC, LBL, STAR, align="center"),
            "fremen": T("nl3f", SC, LBL, BLUEB, align="center"),
            "place": T("nl3p", SC, LBL, STAR, align="center"),
            "paul": T("nl3P", SC, LBL, BLUEB, align="center")},
        2: {"warm": T("nl2", SC, LBS, INK2, align="center")},
        1: {"warm": T("nl1", SC, LBS, INK3, align="center")},
        0: {"warm": T("nl0", MONO, LBS, INK3, align="center")},
    }

    def tstyle(tier, fam):
        row = tier_style[tier]
        return row.get(fam, row.get("warm", tier_style[0]["warm"]))

    # best incident edge tier per node
    best = {}
    for s, d, gr, _ in EDGE:
        for n in (s, d):
            best[n] = max(best.get(n, 0), RANK[gr])

    p = doc.page("plate", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")

    # ── ground ──
    p.layer("bg").rect([0, 0, W, H], fill=linear_gradient([(D0, 0.0), (D1, 0.55), (D0, 1.0)], angle=180))
    neb = p.layer("nebula")
    # the light source: spice nebula behind the causal triangle
    neb.circle([762, 820], 560, fill=radial_gradient([(SPICE, 0.0, 0.30), (SPICE, 0.5, 0.09), (SPICE, 1.0, 0.0)]))
    neb.circle([762, 820], 250, fill=radial_gradient([(GOLD, 0.0, 0.26), (SPICE, 0.7, 0.05), (SPICE, 1.0, 0.0)]))

    # ── deterministic faint starfield (atmosphere, not noise) ──
    sf = p.layer("starfield")
    for i in range(150):
        x = 70 + (i * 233) % (W - 140)
        y = 300 + (i * 151) % 1320
        r = 0.7 + (i % 3) * 0.5
        op = 0.09 + (i % 2) * 0.08
        sf.circle([x, y], r, fill=STAR, opacity=op)

    # ── dune horizon (low, subtle — this is Arrakis) ──
    dn = p.layer("dunes")

    def ridge(y0, amp, ph, fill, op=1.0):
        pts = [[x, y0 + amp * math.sin(x / 260.0 + ph) + amp * 0.3 * math.sin(x / 83.0 + ph * 2)] for x in range(-20, W + 40, 20)]
        pts += [[W + 40, H + 40], [-20, H + 40]]
        dn.polygon(pts, fill=fill, opacity=op)
    ridge(1662, 26, 0.5, DUNE, 0.9)
    ridge(1712, 22, 2.3, "#160F08")

    # ── filaments (edges) ──
    eL = p.layer("edges")

    def filament(a, b, grade, bow):
        (x1, y1, m1, _), (x2, y2, m2, _) = NODE[a], NODE[b]
        r1, r2 = radius(m1), radius(m2)
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        sx, sy = x1 + ux * (r1 + 4), y1 + uy * (r1 + 4)
        ex, ey = x2 - ux * (r2 + 4), y2 - uy * (r2 + 4)
        if abs(bow) > 0.01:
            mx, my = (sx + ex) / 2, (sy + ey) / 2
            cx, cy = mx - uy * bow * L * 0.5, my + ux * bow * L * 0.5
            ctrl = dict(control1=[cx, cy], control2=[cx, cy])
            draw = lambda **kw: eL.curve([sx, sy], [ex, ey], **ctrl, **kw)
        else:
            draw = lambda **kw: eL.line([sx, sy], [ex, ey], **kw)
        if grade == "DIRECT":
            draw(**stroke(6.0, color=SPICE, cap="round"), opacity=0.10)   # under-glow = lit
            draw(**stroke(1.5, color=STAR, cap="round"), opacity=0.85)
        elif grade == "WEAK":
            draw(**stroke(1.3, color=INK2, dash=[7, 6], cap="round"), opacity=0.5)
        else:  # GAP — an absence
            draw(**stroke(1.0, color=INK3, dash=[1.5, 7], cap="round"), opacity=0.34)

    for s, d, gr, bw in EDGE:
        filament(s, d, gr, bw)

    # ── stars (nodes) ──
    nL = p.layer("nodes")

    def core_of(fam, tier):
        if fam == "paul":
            return BLUEB
        if fam == "fremen":
            return BLUE if tier >= 3 else "#3C6478"
        if fam == "place":
            return COOL if tier >= 2 else INK3
        return {3: GOLD, 2: INK2, 1: INK3, 0: INK4}[tier]

    for nid, (x, y, m, fam) in NODE.items():
        tier = best.get(nid, 0)
        r = radius(m)
        gscale = {3: 0.85, 2: 0.42, 1: 0.24, 0: 0.20}[tier]
        grad = GLOW_BLUE if fam == "paul" else GLOW_GOLD
        nL.circle([x, y], r * 2.7, fill=grad, opacity=gscale)
        col = core_of(fam, tier)
        nL.circle([x, y], r, fill=col)
        nL.circle([x, y], max(1.6, r * 0.32), fill=STAR, opacity=0.9 if tier >= 3 else 0.5)
        # diffraction glint on the two brightest loci (Paul, Emperor apex)
        if nid in ("P01", "P23"):
            gl = BLUEB if fam == "paul" else GOLD
            nL.star([x, y], r * 2.5, r * 0.18, 4, rotation=-90, fill=gl, opacity=0.55)
            nL.star([x, y], r * 1.7, r * 0.14, 4, rotation=-45, fill=gl, opacity=0.30)

    # ── labels (own layer, above the glow) ──
    lz = p.layer("labels")
    for nid, (x, y, m, fam) in NODE.items():
        tier = best.get(nid, 0)
        r = radius(m)
        stl = tstyle(tier, fam if tier in (0, 3) else "warm")
        if nid in ABOVE:
            ty = y - r - 26
        else:
            ty = y + r + 7
        bx = min(max(x - 150, 8), W - 308)          # keep the label box on-canvas
        lz.text([bx, ty, 300, 22], LABEL[nid], style=stl)

    # ── title (top) ──
    tt = p.layer("title")
    tt.text([0, 92, W, 22], "A  STORY  GRAPH  OF  BOOK  ONE", style=st_kick)
    tt.text([0, 120, W, 130], "DUNE", style=st_hero)
    tt.text([200, 258, W - 400, 44], "Every line is a claim the text makes; its brightness is how far the book proves it.", style=st_ths)

    # ── colophon: legend + provenance ──
    cz = p.layer("colophon")
    cz.line([110, 1834], [W - 110, 1834], **stroke(1.0, color=INK4))
    cz.text([110, 1852, 700, 34], "The grade of a line is its light", style=st_legH)
    rows = [("DIRECT", "DIRECT", "a retrieved sentence states it"),
            ("WEAK", "WEAK", "implied, or both parties named"),
            ("GAP", "GAP", "expected, never surfaced — an absence")]
    for i, (g, tag, gloss) in enumerate(rows):
        yy = 1918 + i * 34
        if g == "DIRECT":
            cz.line([120, yy], [188, yy], **stroke(6.0, color=SPICE, cap="round"), opacity=0.10)
            cz.line([120, yy], [188, yy], **stroke(1.5, color=STAR, cap="round"), opacity=0.85)
        elif g == "WEAK":
            cz.line([120, yy], [188, yy], **stroke(1.3, color=INK2, dash=[7, 6], cap="round"), opacity=0.5)
        else:
            cz.line([120, yy], [188, yy], **stroke(1.0, color=INK3, dash=[1.5, 7], cap="round"), opacity=0.34)
        cz.text([206, yy - 11, 96, 20], tag, style=T(f"lt{tag}", MONO, LBS, {"DIRECT": STAR, "WEAK": INK2, "GAP": INK3}[g], letter_spacing=1.6))
        cz.text([300, yy - 12, 440, 22], gloss, style=st_legG)
    # star-size + colour keys (two lines — the single line clipped its tail)
    cz.text([110, 2010, 780, 20], "star size ∝ √mentions   ·   the one blue star is Paul (Muad'Dib)", style=st_leg)
    cz.text([110, 2038, 780, 20], "large but unlit — Gurney Halleck: a major name whose Atreides tie is a GAP", style=st_leg)
    # provenance (right)
    px = 900
    cz.text([px, 1852, 500, 22], "32 entities · 33 relations", style=T("pv0", MONO, LBL, STAR))
    for i, (a, b) in enumerate([("20", "DIRECT"), ("6", "WEAK"), ("7", "GAP")]):
        cz.text([px, 1892 + i * 28, 90, 20], a, style=st_provS)
        cz.text([px + 54, 1892 + i * 28, 200, 20], b, style=st_prov)
    cz.text([px + 200, 1892, 400, 20], "coreference-resolved", style=st_prov)
    cz.text([px + 200, 1920, 400, 20], "doc-ray entity_frequency", style=st_prov)
    cz.text([px + 200, 1948, 400, 20], "+ document_evidence", style=st_prov)
    cz.text([px, 2028, 500, 22], "Dune · Frank Herbert · 1965 · book 1", style=st_prov)

    return doc


def radius(m):
    return max(9.0, min(34.0, 7.0 + math.sqrt(m) * 0.62))


if __name__ == "__main__":
    build().write(OUTPUT_YAML_PATH, fail_on_error=True)
