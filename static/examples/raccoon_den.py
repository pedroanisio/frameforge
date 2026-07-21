"""Raccoon & badger late-night workbench — primitives-only scene, polish pass (v4).

Everything is geometry: smooth blobs are Catmull-Rom curves sampled into dense
polygons; glows are stacked translucent ellipses; the LED text is a 3x5 dot font.
"""
import math
from frameforge.sdk import DocumentBuilder, rgba
from frameforge.sdk.paint import stroke

def S(w, c):
    return stroke(w, color=c)

ROUND = {"stroke_linejoin": "round", "stroke_linecap": "round"}
W, H = 2000, 1119

# ---------- palette ----------
WALL   = "#262239"
WALL2  = "#1D1A2F"
INKC   = "#2B2640"
DESK   = "#EBD9D8"
DESKHI = "#F6E9E2"
DESKSH = "#CDB9D2"
DESKSH2= "#D9C4DC"
CHAIR  = "#7C7A9E"
CHAIRD = "#615E85"
CHAIRHI= "#9B98BC"
FUR    = "#E9E6EF"
FURSH  = "#BCB8CE"
MASK   = "#3A3552"
PAWD   = "#6E5C55"
SWEAT  = "#C9885A"
SWEATD = "#A96D42"
JACK   = "#8A8F6E"
JACKD  = "#6E7356"
CANC   = "#D9D6CF"
CANR   = "#C05A4A"
KBB    = "#4A4766"
KBD    = "#37344F"
KEYS   = "#585575"
KEYT   = "#6E6B92"
LEDBG  = "#343050"
LEDDOT = "#A8DCF2"
LEDDIM = "#5E7A9A"
BOTTLE = "#96602F"
LABEL  = "#C0683F"
CREAM  = "#EFE2CE"
MUG    = "#7A7D5A"
MUGD   = "#616447"
COFFEE = "#4A3527"
COOKIE = "#C9A067"
COOKD  = "#8F6B3C"
NUT    = "#D8B27E"
PAPER  = "#EDE6EA"
STICKY = "#E3D084"
STRIP  = "#DCD3E2"
SOCK   = "#3A3550"
REDS   = "#C0524A"
PCB    = "#5F8F72"
DENIM  = "#7C89A6"
DENIMD = "#63708C"
ORANGE = "#C86F45"
TAN    = "#C7A171"
TAND   = "#A5814F"
BROWN  = "#9A6B4C"
METAL  = "#C9C4D4"
RIM    = "#CFC8EE"
DARKOBJ= "#191627"
DARKOBJ2="#14121F"

doc = DocumentBuilder(title="Raccoon den - primitives recreation (polished)", profile="diagram")
page = doc.page("scene", canvas={"size": [W, H], "units": "px", "background": WALL}, coordinate_mode="absolute")
bg  = page.layer("bg")
art = page.layer("art")

def poly(layer, pts, fill, ow=3, oc=INKC):
    if ow:
        layer.polygon(pts, fill=fill, style=ROUND, **S(ow, oc))
    else:
        layer.polygon(pts, fill=fill)

def pline(layer, pts, w, c):
    layer.polyline(pts, style=ROUND, **S(w, c))

def F(ox, oy, deg):
    a = math.radians(deg)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -math.sin(a), math.cos(a)
    def pt(x, y):
        return [ox + ux * x + vx * y, oy + uy * x + vy * y]
    def q(x, y, w, h):
        return [pt(x, y), pt(x + w, y), pt(x + w, y + h), pt(x, y + h)]
    return pt, q

def smooth(pts, closed=True, k=8):
    """Catmull-Rom through pts, densely sampled -> visually smooth polygon."""
    P = [list(p) for p in pts]
    n = len(P)
    out = []
    def cr(p0, p1, p2, p3, t):
        t2 = t * t; t3 = t2 * t
        return [0.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t
                       + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2
                       + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3) for i in (0, 1)]
    if closed:
        for i in range(n):
            p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
            for j in range(k):
                out.append(cr(p0, p1, p2, p3, j / k))
    else:
        for i in range(n - 1):
            p0 = P[max(i - 1, 0)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(i + 2, n - 1)]
            for j in range(k):
                out.append(cr(p0, p1, p2, p3, j / k))
        out.append(P[-1])
    return out

def blob(layer, ctrl, fill, ow=3, oc=INKC, k=8):
    poly(layer, smooth(ctrl, True, k), fill, ow, oc)

def wisp(layer, ctrl, w, c, k=8):
    pline(layer, smooth(ctrl, False, k), w, c)

# =============================================== wall: vignette + soft waves
bg.polygon([[0, 0], [W, 0], [W, 60], [0, 130]], fill=rgba("#100E1C", 0.35))
bg.polygon([[0, 980], [860, 1010], [820, 1119], [0, 1119]], fill=rgba("#100E1C", 0.35))
for sx, sy, ln, ph in [(60, 130, 300, 0), (330, 70, 190, 1), (120, 315, 240, 0), (430, 258, 160, 1),
                       (200, 485, 340, 0), (60, 635, 200, 1), (380, 575, 240, 0), (150, 815, 280, 1),
                       (480, 775, 180, 0), (300, 965, 300, 1), (620, 365, 220, 0), (700, 158, 180, 1),
                       (760, 915, 190, 0), (560, 1055, 240, 1)]:
    ctrl = [[sx + i * ln / 4.0, sy + (4 if (i + ph) % 2 else -4)] for i in range(5)]
    wisp(bg, ctrl, 3, rgba(WALL2, 0.9))

# top-left shelf silhouette + hanging plug (smooth cord)
poly(bg, [[0, 0], [225, 0], [150, 62], [0, 98]], DARKOBJ2, 3)
wisp(bg, [[168, 30], [250, 68], [330, 90], [388, 118]], 4, DARKOBJ2)
ptp, qtp = F(392, 120, 32)
poly(bg, qtp(0, -14, 46, 28), DARKOBJ, 3)
pline(bg, [ptp(46, -7), ptp(62, -7)], 3, WALL2)
pline(bg, [ptp(46, 7), ptp(62, 7)], 3, WALL2)

# left-edge silhouettes
poly(bg, [[0, 555], [108, 575], [96, 890], [0, 878]], DARKOBJ, 3)
pline(bg, [[10, 600], [95, 615]], 2, WALL2)
poly(bg, [[0, 902], [92, 918], [80, 1119], [0, 1119]], DARKOBJ2, 3)
bg.circle([48, 1012], 28, fill="none", **S(2.5, "#2A2740"))

# =============================================== badger torso (waist sits behind desk)
poly(art, [[1382, 0], [1990, 0], [1998, 400], [1830, 372], [1640, 330],
           [1470, 318], [1398, 280], [1372, 130]], JACK, 4)
poly(art, [[1790, 60], [1930, 30], [1985, 380], [1830, 368]], JACKD, 0)
wisp(art, [[1522, 300], [1558, 190], [1552, 86]], 3, JACKD)
wisp(art, [[1712, 310], [1744, 196], [1736, 96]], 3, JACKD)
pline(art, [[1600, 322], [1598, 384]], 3, JACKD)

# =============================================== desk
poly(art, [[1128, 312], [1300, 250], [1470, 220], [1700, 228], [2000, 268],
           [2000, 1119], [858, 1119], [978, 660]], DESK, 4)
poly(art, [[1128, 312], [1210, 282], [1080, 660], [960, 1020], [900, 1119],
           [858, 1119], [978, 660]], DESKSH2, 0)
poly(art, [[1300, 250], [1470, 220], [1700, 228], [1660, 260], [1350, 268]], DESKSH2, 0)
# layered warm light pool
art.ellipse([1560, 610], 430, 210, fill=rgba(DESKHI, 0.55))
art.ellipse([1540, 600], 300, 150, fill=rgba("#FAF0E6", 0.45))
# stray specks
for dx, dy in [(1210, 500), (1500, 430), (1750, 640), (1350, 520), (1600, 760)]:
    art.circle([dx, dy], 2, fill=rgba(DESKSH, 0.8))

# =============================================== badger head (leaning over the desk edge)
blob(art, [[1490, 238], [1560, 266], [1660, 272], [1716, 252], [1700, 298],
           [1600, 318], [1500, 292]], JACKD, 3.5)
blob(art, [[1524, 268], [1600, 288], [1562, 302], [1512, 286]], JACK, 2)
blob(art, [[1508, 100], [1552, 38], [1640, 20], [1714, 50], [1744, 130],
           [1716, 210], [1652, 262], [1592, 268], [1532, 232]], FUR, 4)
wisp(art, [[1528, 70], [1584, 34], [1650, 26]], 2.5, rgba(RIM, 0.85))
blob(art, [[1508, 96], [1526, 58], [1556, 86], [1536, 112]], FUR, 3.5)
blob(art, [[1520, 90], [1531, 72], [1544, 88], [1533, 99]], MASK, 0)
blob(art, [[1702, 80], [1730, 58], [1748, 98], [1722, 114]], FUR, 3.5)
blob(art, [[1715, 84], [1730, 73], [1739, 95], [1725, 103]], MASK, 0)
blob(art, [[1560, 44], [1584, 38], [1596, 150], [1596, 226], [1574, 224], [1558, 150]], MASK, 0)
blob(art, [[1650, 32], [1674, 38], [1688, 150], [1676, 224], [1656, 226], [1652, 150]], MASK, 0)
art.circle([1584, 158], 9, fill="#16131F")
art.circle([1587, 154], 2.5, fill=FUR)
pline(art, [[1576, 168], [1592, 169]], 2, FURSH)
art.circle([1666, 162], 9, fill="#16131F")
art.circle([1669, 158], 2.5, fill=FUR)
pline(art, [[1658, 172], [1674, 173]], 2, FURSH)
blob(art, [[1566, 230], [1656, 234], [1646, 272], [1584, 270]], FURSH, 0)
blob(art, [[1590, 244], [1650, 248], [1642, 292], [1598, 288]], "#221E33", 3)
art.circle([1608, 258], 3.5, fill=rgba(FUR, 0.5))
pline(art, [[1646, 258], [1735, 278]], 4.5, CREAM)
art.circle([1741, 280], 5, fill=ORANGE, **S(2, INKC))

# =============================================== on-desk, far side
blob(art, [[1900, 258], [2000, 246], [2004, 436], [1912, 446], [1882, 348]], TAN, 3.5)
art.ellipse([1913, 350], 30, 88, fill=TAND, **S(3, INKC))
art.ellipse([1913, 350], 14, 44, fill=TAN, **S(2, INKC))
wisp(art, [[1940, 268], [1952, 352], [1938, 428]], 2.5, TAND)
blob(art, [[1928, 476], [2002, 458], [2002, 598], [1944, 610]], BROWN, 3.5)
art.ellipse([1943, 540], 22, 66, fill="#7E5238", **S(3, INKC))
wisp(art, [[1962, 480], [1974, 540], [1960, 600]], 2, "#7E5238")

# laptop + clothes
art.ellipse([1810, 560], 175, 27, fill=rgba(DESKSH, 0.85))
poly(art, [[1618, 470], [1948, 392], [1996, 476], [1668, 560]], "#55516E", 3.5)
poly(art, [[1668, 560], [1996, 476], [1996, 494], [1672, 578]], KBD, 3.5)
pline(art, [[1640, 476], [1930, 406]], 2, rgba(RIM, 0.5))
art.circle([1902, 462], 21, fill="#D2703E", **S(2.5, INKC))
art.circle([1902, 462], 9, fill="#E8935F", **S(1.5, INKC))
ptt, qtt = F(1846, 500, -13)
poly(art, qtt(0, 0, 52, 26), PAPER, 2.5)
for i in range(3):
    pline(art, [ptt(8 + i * 14, 6), ptt(12 + i * 14, 20)], 2, INKC)
poly(art, [[1636, 388], [1888, 330], [1918, 402], [1680, 462]], DENIM, 3.5)
wisp(art, [[1660, 420], [1890, 366]], 2.5, DENIMD)
art.line([1700, 434], [1740, 424], style={"stroke_dasharray": [4, 4]}, **S(1.8, DENIMD))
poly(art, [[1668, 372], [1812, 340], [1830, 384], [1690, 416]], ORANGE, 3)
wisp(art, [[1700, 380], [1800, 356]], 2, "#A5552F")
poly(art, [[1794, 396], [1856, 380], [1866, 408], [1806, 424]], "#8F3B34", 3)
wisp(art, [[1622, 520], [1560, 542], [1512, 530], [1470, 506]], 4, INKC)

# =============================================== badger arm + can
blob(art, [[1408, 62], [1516, 42], [1526, 150], [1480, 252], [1420, 262], [1396, 168]], JACK, 4)
wisp(art, [[1424, 122], [1478, 112]], 3, JACKD)
pline(art, [[1436, 236], [1508, 228]], 3, JACKD)
art.ellipse([1476, 344], 54, 13, fill=rgba(DESKSH, 0.9))
ptc, qc = F(1436, 210, 8)
poly(art, qc(0, 0, 74, 128), CANC, 3.5)
art.ellipse([ptc(37, 4)[0], ptc(37, 4)[1]], 36, 12, fill="#B9B6AE", **S(3, INKC))
poly(art, qc(4, 52, 66, 40), CANR, 0)
art.circle([ptc(37, 72)[0], ptc(37, 72)[1]], 15, fill=CREAM, **S(2, INKC))
pline(art, [ptc(12, 10), ptc(12, 120)], 3, rgba("#FFFFFF", 0.55))
blob(art, [[1440, 240], [1506, 232], [1512, 264], [1476, 290], [1440, 282]], FURSH, 3)
pline(art, [[1456, 244], [1460, 280]], 2, INKC)
pline(art, [[1476, 240], [1480, 278]], 2, INKC)
# right paw + screwdriver
blob(art, [[1788, 332], [1846, 322], [1864, 356], [1822, 378], [1786, 366]], FURSH, 3)
pline(art, [[1810, 344], [1868, 318]], 5, METAL)
poly(art, [[1862, 312], [1896, 296], [1904, 312], [1870, 328]], ORANGE, 2.5)

# =============================================== keyboard (two-tone keys)
kx, ky, kang = 1240, 575, -9.2
ptk, qk = F(kx, ky, kang)
poly(art, qk(-4, 137, 660, 18), rgba(DESKSH, 0.9), 0)
poly(art, qk(0, 0, 655, 115), KBB, 4)
poly(art, qk(0, 115, 655, 22), KBD, 3)
for r in range(4):
    for c in range(13):
        poly(art, qk(18 + c * 48, 12 + r * 25, 41, 19), KEYS, 2)
        poly(art, qk(20 + c * 48, 13 + r * 25, 37, 13), KEYT, 0)
wisp(art, [ptk(650, 20), ptk(700, -20), [1900, 445], [1948, 470]], 4, INKC)
pline(art, [ptk(60, -14), ptk(118, -22)], 4, CREAM)
ck = ptk(132, -24)
art.circle([ck[0], ck[1]], 14, fill="#8FBF8A", **S(2.5, INKC))
art.circle([ck[0] - 4, ck[1] - 4], 4, fill=rgba("#FFFFFF", 0.6))

# =============================================== LED matrix board (with glow)
lx, ly, lang = 1470, 772, -12.5
ptl, ql = F(lx, ly, lang)
poly(art, ql(-6, 96, 380, 18), rgba(DESKSH, 0.9), 0)
poly(art, ql(0, 0, 372, 96), LEDBG, 4)
poly(art, ql(6, 6, 360, 84), "none", 1.5, "#4A4570")
FONT = {
    "R": ["110", "101", "110", "101", "101"],
    "E": ["111", "100", "110", "100", "111"],
    "S": ["011", "100", "010", "001", "110"],
    "C": ["011", "100", "100", "100", "011"],
    "U": ["101", "101", "101", "101", "111"],
    "A": ["010", "101", "111", "101", "101"],
    "O": ["010", "101", "101", "101", "010"],
    "N": ["101", "111", "111", "101", "101"],
}
def led_line(text, x0, y0, cell=8.2):
    cx = x0
    for ch in text:
        for rr, rowbits in enumerate(FONT[ch]):
            for cc, b in enumerate(rowbits):
                if b == "1":
                    p = ptl(cx + cc * cell, y0 + rr * cell)
                    art.circle([p[0], p[1]], 6, fill=rgba(LEDDOT, 0.22))
                    art.circle([p[0], p[1]], 2.9, fill=LEDDOT)
        cx += 4 * cell
led_line("RESCUE", 92, 6)
led_line("RACCOON", 80, 55)
for dx, dy in [(30, 24), (348, 70), (20, 76)]:
    p = ptl(dx, dy)
    art.circle([p[0], p[1]], 2.4, fill=LEDDIM)
p = ptl(356, 10)
art.circle([p[0], p[1]], 3, fill=REDS)
wisp(art, [ptl(-4, 70), [1418, 880], [1396, 906]], 3.5, INKC)

# sticky note near board
pts_n, qs_n = F(1560, 900, 8)
poly(art, qs_n(0, 0, 58, 52), STICKY, 2.5)
wisp(art, [pts_n(10, 16), pts_n(46, 14)], 2, TAND)
wisp(art, [pts_n(10, 28), pts_n(40, 26)], 2, TAND)

# =============================================== desk objects (near side)
# crumpled receipt
blob(art, [[1176, 700], [1238, 680], [1294, 700], [1282, 758], [1220, 780], [1168, 748]], PAPER, 3, k=4)
wisp(art, [[1200, 706], [1244, 744]], 2, "#C9BFCB")
for i in range(4):
    pline(art, [[1192 + i * 6, 716 + i * 12], [1216 + i * 6, 712 + i * 12]], 1.6, "#B9AFC0")
# paper sheet under typing arm
poly(art, [[1210, 690], [1320, 668], [1344, 736], [1232, 760]], PAPER, 3)
for i in range(3):
    pline(art, [[1230 + i * 4, 704 + i * 16], [1304 + i * 4, 690 + i * 16]], 1.8, "#B9AFC0")

# mug with coffee + steam
art.ellipse([1384, 850], 52, 14, fill=rgba(DESKSH, 0.9))
poly(art, [[1334, 748], [1424, 742], [1430, 838], [1340, 844]], MUG, 3.5)
art.ellipse([1379, 748], 46, 15, fill=MUGD, **S(3, INKC))
art.ellipse([1379, 750], 36, 11, fill=COFFEE)
art.circle([1442, 792], 20, fill="none", **S(7, MUG))
art.circle([1442, 792], 20, fill="none", **S(2.5, INKC))
poly(art, [[1424, 764], [1434, 762], [1436, 824], [1426, 826]], MUG, 0)
wisp(art, [[1366, 726], [1358, 700], [1370, 676], [1362, 652]], 2.5, rgba(RIM, 0.55))
wisp(art, [[1394, 722], [1402, 700], [1392, 678]], 2.5, rgba(RIM, 0.4))

# waffle cookies (grid clipped to true chords)
for ccx, ccy, r in [(1268, 806, 33), (1326, 844, 30)]:
    art.circle([ccx, ccy], r, fill=COOKIE, **S(3, INKC))
    for off in (-12, 0, 12):
        half = math.sqrt(max(r * r - off * off, 0)) - 4
        pline(art, [[ccx - half, ccy + off], [ccx + half, ccy + off]], 2, COOKD)
        pline(art, [[ccx + off, ccy - half], [ccx + off, ccy + half]], 2, COOKD)
art.circle([1300, 826], 2.5, fill=COOKD)
art.circle([1246, 840], 2.5, fill=COOKD)

# peanuts: two-lobe shells
for nx, ny, na in [(962, 906, 20), (1002, 938, -15), (1052, 900, 40), (1106, 956, 0),
                   (1162, 916, -30), (1042, 986, 15), (988, 1012, -40), (1212, 972, 25)]:
    ptn, _ = F(nx, ny, na)
    a1 = ptn(-7, 0); a2 = ptn(7, 0)
    art.ellipse([a1[0], a1[1]], 9, 7.5, fill=NUT, **S(2.2, INKC))
    art.ellipse([a2[0], a2[1]], 9, 7.5, fill=NUT, **S(2.2, INKC))
    pline(art, [ptn(-3, -5), ptn(-3, 5)], 1.4, TAND)
for dx, dy in [(1090, 900), (1140, 980), (1010, 960), (1230, 930), (968, 1050)]:
    art.circle([dx, dy], 3, fill=TAND)
ptr, qr = F(1012, 894, 28)
poly(art, qr(0, 0, 34, 18), REDS, 2.5)

# soldering iron with warm tip + smoke
pti, qi = F(1232, 976, -20)
poly(art, qi(0, -14, 100, 28), "#4A4E6E", 3.5)
pline(art, [pti(20, -14), pti(20, 14)], 2.5, INKC)
pline(art, [pti(36, -14), pti(36, 14)], 2.5, INKC)
pline(art, [pti(100, 0), pti(178, -8)], 6, METAL)
pline(art, [pti(178, -8), pti(196, -10)], 3.5, "#8A8598")
tip = pti(198, -10)
art.circle([tip[0], tip[1]], 4, fill=rgba("#E88A4A", 0.85))
wisp(art, [[tip[0] + 4, tip[1] - 6], [tip[0] + 14, tip[1] - 26], [tip[0] + 6, tip[1] - 44]], 2, rgba(RIM, 0.5))
for i in range(5):
    cci = pti(-14 - i * 13, 4 + (i % 2) * 6)
    art.circle([cci[0], cci[1]], 9, fill="none", **S(3, INKC))
wisp(art, [[1160, 1006], [1090, 1050], [1020, 1078], [960, 1119]], 4, INKC)

# PCB with silk lines
ptpcb, qpcb = F(1374, 902, -16)
poly(art, qpcb(0, 0, 128, 62), PCB, 3.5)
poly(art, qpcb(16, 14, 30, 20), "#2E2B44", 2)
poly(art, qpcb(58, 30, 24, 16), "#2E2B44", 2)
poly(art, qpcb(62, 8, 16, 10), "#2E2B44", 2)
wisp(art, [ptpcb(10, 50), ptpcb(50, 50), ptpcb(54, 40)], 1.4, rgba("#DDEBD9", 0.6))
for i in range(5):
    p = ptpcb(96 + (i % 2) * 10, 10 + i * 9)
    art.circle([p[0], p[1]], 2.6, fill="#D9C468")
wisp(art, [ptpcb(128, 30), [1548, 960], [1568, 1000]], 3, "#8F3B34")
wisp(art, [ptpcb(128, 44), [1540, 986], [1552, 1016]], 3, INKC)

# power strip
pst, qst = F(1430, 1006, -13)
poly(art, qst(-4, 74, 372, 16), rgba(DESKSH, 0.9), 0)
poly(art, qst(0, 0, 360, 74), STRIP, 3.5)
pline(art, [pst(8, 8), pst(352, 8)], 2, rgba("#FFFFFF", 0.5))
for i in range(4):
    poly(art, qst(20 + i * 78, 14, 56, 46), SOCK, 2.5)
    if i != 1:
        p1 = pst(20 + i * 78 + 18, 37)
        p2 = pst(20 + i * 78 + 38, 37)
        art.circle([p1[0], p1[1]], 4.5, fill=STRIP)
        art.circle([p2[0], p2[1]], 4.5, fill=STRIP)
poly(art, qst(330, 22, 22, 30), REDS, 2.5)
pled = pst(320, 12)
art.circle([pled[0], pled[1]], 3, fill="#E8A44A")
poly(art, qst(94, -6, 46, 40), "#221E33", 3)
wisp(art, [pst(117, -6), pst(130, -60), [1620, 880]], 4.5, INKC)
wisp(art, [pst(0, 50), [1380, 1080], [1330, 1119]], 5, INKC)

# power brick
ptbr, qbr = F(1300, 1040, -8)
poly(art, qbr(0, 0, 112, 62), "#221E33", 3.5)
pline(art, [ptbr(8, 10), ptbr(104, 10)], 2, rgba("#FFFFFF", 0.25))
wisp(art, [ptbr(0, 30), [1250, 1080], [1200, 1119]], 4, INKC)
wisp(art, [ptbr(112, 20), [1440, 1035]], 3.5, INKC)

# coiled cable + tangles
art.circle([1912, 706], 40, fill="none", **S(5, INKC))
art.circle([1912, 706], 26, fill="none", **S(5, INKC))
wisp(art, [[1950, 720], [1990, 780], [1970, 850], [1912, 880]], 5, INKC)
wisp(art, [[1800, 900], [1900, 930], [1980, 990]], 4, INKC)
wisp(art, [[1740, 1010], [1830, 1060], [1920, 1080]], 4, INKC)

# mesh roll
poly(art, [[1856, 946], [2000, 918], [2000, 1119], [1880, 1119]], TAN, 3.5)
for i in range(5):
    pline(art, [[1866 + i * 28, 950 - i * 4], [1900 + i * 24, 1119]], 2, TAND)
for i in range(4):
    pline(art, [[1856, 986 + i * 34], [2000, 952 + i * 34]], 2, TAND)

# stray sticks
pline(art, [[1240, 548], [1298, 532]], 3.5, CREAM)
pline(art, [[1430, 398], [1482, 380]], 3.5, CREAM)
art.circle([1489, 378], 8, fill="#C97A8F", **S(2, INKC))
art.circle([1486, 375], 2.5, fill=rgba("#FFFFFF", 0.6))

# =============================================== chair (smooth)
ptch, qch = F(1010, 430, -35)
back_ctrl = [ptch(-190, -255), ptch(0, -278), ptch(190, -255), ptch(202, 0), ptch(190, 225),
             ptch(0, 240), ptch(-190, 225), ptch(-202, 0)]
blob(art, back_ctrl, CHAIR, 4.5, k=8)
cush_ctrl = [ptch(-146, -208), ptch(0, -226), ptch(146, -208), ptch(154, 0), ptch(146, 178),
             ptch(0, 192), ptch(-146, 178), ptch(-154, 0)]
blob(art, cush_ctrl, CHAIRD, 3)
blob(art, [ptch(-146, -208), ptch(-60, -222), ptch(-70, 0), ptch(-58, 178),
           ptch(-146, 178), ptch(-154, 0)], CHAIRHI, 0)
wisp(art, [ptch(-60, -220), ptch(-52, 0), ptch(-60, 180)], 2.5, CHAIR)
blob(art, [[858, 642], [1000, 650], [1120, 664], [1152, 782], [1010, 800], [905, 795]], CHAIRD, 4)
blob(art, [[868, 700], [1002, 716], [1012, 776], [878, 764]], "#4E4B70", 3.5)

# =============================================== raccoon tail (ringed, draped left)
tail_pts = smooth([[1005, 802], [948, 878], [892, 958], [854, 1038], [844, 1098]], False, 10)
art.polyline(tail_pts, style=ROUND, **S(52, INKC))
art.polyline(tail_pts, style=ROUND, **S(44, FURSH))
nT = len(tail_pts)
for a, b in [(int(nT * 0.22), int(nT * 0.36)), (int(nT * 0.52), int(nT * 0.66)), (int(nT * 0.82), nT - 1)]:
    art.polyline(tail_pts[a:b], style=ROUND, **S(44, MASK))

# =============================================== bottle
art.ellipse([1030, 858], 72, 14, fill=rgba(DESKSH, 0.9))
ptb, qb = F(940, 680, 52)
poly(art, qb(0, -11, 30, 22), "#3A3550", 3)
pline(art, [ptb(10, -11), ptb(10, 11)], 1.6, "#54506E")
poly(art, qb(28, -14, 62, 28), BOTTLE, 3.5)
blob(art, [ptb(86, -32), ptb(146, -40), ptb(202, -38), ptb(206, 36), ptb(146, 42), ptb(88, 30)], BOTTLE, 3.5, k=6)
poly(art, qb(110, -36, 52, 74), LABEL, 2.5)
cb = ptb(136, 0)
art.circle([cb[0], cb[1]], 15, fill=CREAM, **S(2, INKC))
pline(art, [ptb(118, 22), ptb(152, 24)], 1.6, "#8F4F30")
wisp(art, [ptb(40, -22), ptb(92, -26), ptb(190, -30)], 4, rgba("#E8B878", 0.75))

# =============================================== raccoon (smooth)
# torso
blob(art, [[970, 530], [1060, 468], [1170, 458], [1262, 502], [1292, 600],
           [1268, 748], [1205, 815], [1090, 820], [1044, 732], [1012, 640]], SWEAT, 4)
blob(art, [[972, 530], [1040, 490], [1028, 632], [1012, 640], [988, 580]], SWEATD, 0)
wisp(art, [[1062, 518], [1052, 640]], 3, SWEATD)
wisp(art, [[1230, 545], [1246, 660]], 3, SWEATD)
wisp(art, [[1002, 560], [986, 640], [1000, 706]], 2.5, rgba(RIM, 0.7))
# collar ridge
wisp(art, [[1130, 470], [1190, 462], [1246, 486]], 3.5, SWEATD)
# typing arm + paw with fingers
blob(art, [[1228, 560], [1310, 598], [1374, 632], [1352, 686], [1262, 664], [1212, 638]], SWEAT, 4)
blob(art, [[1312, 620], [1344, 632], [1336, 668], [1304, 658]], SWEATD, 0)
blob(art, [[1358, 634], [1416, 626], [1440, 658], [1408, 692], [1366, 684]], PAWD, 3)
pline(art, [[1384, 638], [1392, 684]], 2, INKC)
pline(art, [[1406, 632], [1414, 680]], 2, INKC)
pline(art, [[1428, 648], [1444, 668]], 2, INKC)
# head
blob(art, [[1096, 300], [1140, 230], [1214, 206], [1290, 234], [1338, 300],
           [1354, 438], [1294, 460], [1212, 444], [1128, 408], [1080, 352]], FUR, 4)
# cheek fluff (kept jagged on purpose)
poly(art, [[1080, 352], [1128, 408], [1104, 416], [1124, 442], [1088, 440], [1058, 396]], FUR, 3.5)
# crown patch + rim light
blob(art, [[1122, 252], [1200, 212], [1272, 232], [1240, 264], [1150, 282]], FURSH, 0)
wisp(art, [[1108, 300], [1150, 240], [1214, 214]], 2.5, rgba(RIM, 0.85))
# ears
blob(art, [[1126, 246], [1150, 184], [1196, 226]], FUR, 3.5, k=6)
blob(art, [[1142, 232], [1157, 202], [1180, 222]], MASK, 0, k=6)
blob(art, [[1252, 224], [1286, 180], [1320, 234]], FUR, 3.5, k=6)
blob(art, [[1268, 216], [1288, 194], [1306, 224]], MASK, 0, k=6)
# two mask patches with a fur gap at the bridge
blob(art, [[1168, 306], [1224, 296], [1240, 324], [1220, 354], [1176, 346], [1158, 326]], MASK, 0)
blob(art, [[1268, 308], [1326, 324], [1350, 366], [1300, 388], [1262, 354], [1258, 330]], MASK, 0)
# brow ticks
pline(art, [[1198, 282], [1216, 276]], 2.5, FURSH)
pline(art, [[1276, 288], [1294, 296]], 2.5, FURSH)
# eyes
art.circle([1204, 328], 9.5, fill="#16131F")
art.circle([1208, 324], 3, fill=FUR)
art.circle([1300, 352], 9.5, fill="#16131F")
art.circle([1304, 348], 3, fill=FUR)
# muzzle + nose + mouth + whisker dots
blob(art, [[1290, 394], [1348, 414], [1354, 440], [1308, 450]], FURSH, 0)
blob(art, [[1324, 424], [1358, 432], [1352, 462], [1318, 454]], "#221E33", 3, k=6)
art.circle([1332, 434], 2.5, fill=rgba(FUR, 0.5))
wisp(art, [[1330, 462], [1318, 470], [1304, 468]], 2, MASK)
for wd in [(1284, 428), (1292, 440), (1278, 416)]:
    art.circle([wd[0], wd[1]], 1.6, fill=FURSH)
# pointing arm + paw with index finger
blob(art, [[1262, 540], [1330, 490], [1392, 460], [1414, 500], [1350, 540], [1292, 578]], SWEAT, 4)
wisp(art, [[1330, 500], [1352, 520]], 2.5, SWEATD)
blob(art, [[1400, 434], [1454, 416], [1482, 442], [1450, 478], [1408, 480]], PAWD, 3)
pline(art, [[1462, 424], [1498, 434]], 6, PAWD)
pline(art, [[1428, 466], [1440, 448]], 2, INKC)

# =============================================== foreground gloved arm (smooth)
blob(art, [[868, 1119], [944, 1018], [1028, 958], [1110, 934], [1162, 962],
           [1120, 1022], [1008, 1119]], "#5A5F7E", 4)
wisp(art, [[960, 1030], [1020, 990]], 2.5, "#4A4E6E")
blob(art, [[1080, 942], [1150, 916], [1198, 936], [1178, 978], [1110, 992], [1070, 972]], "#4A4E6E", 3.5)
pline(art, [[1120, 940], [1130, 984]], 2, INKC)
pline(art, [[1148, 932], [1158, 976]], 2, INKC)
pline(art, [[1178, 944], [1240, 930]], 2.5, METAL)
pline(art, [[1180, 950], [1238, 940]], 2.5, METAL)

# foreground corner vignette
art.polygon([[0, 1040], [220, 1080], [160, 1119], [0, 1119]], fill=rgba("#0E0C18", 0.4))

doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
