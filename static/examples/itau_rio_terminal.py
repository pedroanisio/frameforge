"""Itaú · Rio Terminal — a client-facing UI/UX proposal, authored with the
FrameGraph SDK. Concept using Itaú-inspired colours (orange + blue); not an
official Itaú asset. Every symbol (chevrons, checks, dots, bars, charts, the
brand mark) is drawn as vector geometry so the render is crisp and tofu-free."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framegraph.sdk import DocumentBuilder, Mat3, PageBuilder, render_pages_with_stats
from framegraph.sdk.paint import linear_gradient, radial_gradient, rgba
from framegraph.sdk.macros import span
from itau_logo import GLYPHS as _GLYPHS, SQUIRCLE as _SQUIRCLE   # authentic reconstructed mark

OUT = os.environ.get("ITAU_OUT", ".")
W, H = 1600, 900

# ---- Itaú-inspired brand (orange aligned to the logo's true #FF6200) ----
ORANGE = "#FF6200"; ORANGE_HI = "#FF8A2B"; ORANGE_DK = "#C24A00"
BLUE = "#0A4FA6"; BLUE_HI = "#2E7BE0"; NAVY = "#001A4D"; NAVY2 = "#00112E"

DISP, UI, MONO = "Space Grotesk", "Inter", "Space Mono"

DARK = dict(
    bg="#0B0E16", surf="#111827", bar="#0C111D", line="#222C42", line2="#33415E",
    fg="#E8EBF4", mut="#93A0BA", faint="#59647E", sel="#16203400",
    grn="#48D07E", yel="#ECC14A", red="#FF5C51", cyn="#49C6DB", mag="#B58BF2", blu="#5C93FF",
    orange=ORANGE, orange_hi=ORANGE_HI, blue=BLUE_HI,
)
LIGHT = dict(
    bg="#ECE7DE", surf="#FFFFFF", bar="#F6F2EB", line="#E4DCCE", line2="#D6CCBA",
    fg="#1B2430", mut="#5A6575", faint="#93A0B0", sel="#FBEEDD",
    grn="#1E9E57", yel="#B27C15", red="#D4483E", cyn="#0E93A6", mag="#7C4FD0", blu="#2E6FD6",
    orange="#D9660A", orange_hi=ORANGE, blue=BLUE,
)

b = DocumentBuilder(title="Itaú · Rio Terminal — UI/UX Proposal", profile="deck", lang="pt-BR")
for f in (DISP, UI, MONO):
    b.define_font(f, family=f)


# --------------------------------------------------------------------------- #
# primitives                                                                   #
# --------------------------------------------------------------------------- #
def page(pid, bg):
    pg = b.page(pid, canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    p = pg.layer("main")
    p.rect([0, 0, W, H], fill=bg)
    return p


def T(p, x, y, s, *, size=14, color="#000", font=UI, weight=None, align=None,
      w=1400, spacing=None, italic=False, h=None):
    st = {"font_family": font, "font_size": size, "color": color}
    if weight: st["font_weight"] = weight
    if align: st["text_align"] = align
    if spacing is not None: st["letter_spacing"] = spacing
    if italic: st["font_style"] = "italic"
    p.text([x, y, w, h or size * 1.5], s, style=st)


def runs(p, x, y, parts, *, size=15, font=MONO, w=1400, h=26):
    """One mono line from (text, color[, weight]) tuples."""
    sp = []
    for t in parts:
        c = t[1] if len(t) > 1 else None
        wt = t[2] if len(t) > 2 else None
        sp.append(span(t[0], color=c, size=size, font=font, **({"bold": True} if wt == "b" else {})))
    p.text([x, y, w, h], sp, style={"font_family": font, "font_size": size})


def chevron(p, x, y, s, color):
    p.path([("M", x, y), ("L", x + s * 0.62, y + s * 0.5), ("L", x, y + s)],
           fill="none", stroke=color, stroke_style={"stroke_width": max(1.6, s * 0.17),
           "stroke_linecap": "round", "stroke_linejoin": "round"})


def check(p, cx, cy, r, color):
    p.path([("M", cx - r * 0.55, cy + r * 0.02), ("L", cx - r * 0.12, cy + r * 0.5),
            ("L", cx + r * 0.62, cy - r * 0.5)],
           fill="none", stroke=color, stroke_style={"stroke_width": max(1.6, r * 0.34),
           "stroke_linecap": "round", "stroke_linejoin": "round"})


def dot(p, cx, cy, r, color, ring=None):
    if ring:
        p.circle([cx, cy], r + 2.4, fill="none", stroke=ring, stroke_style={"stroke_width": 1})
    p.circle([cx, cy], r, fill=color)


def tri(p, cx, cy, s, color, up=True):
    d = 1 if up else -1
    p.polygon([[cx, cy - d * s], [cx - s, cy + d * s * 0.7], [cx + s, cy + d * s * 0.7]], fill=color)


def progress(p, x, y, w, h, frac, fg, bg):
    p.rect([x, y, w, h], fill=bg, radius=h / 2)
    if frac > 0:
        p.rect([x, y, max(h, w * frac), h], fill=fg, radius=h / 2)


def bars(p, x, y, w, h, values, color, gap=3):
    n = len(values)
    bw = (w - gap * (n - 1)) / n
    mx = max(values) or 1
    for i, v in enumerate(values):
        bh = max(2, h * (v / mx))
        p.rect([x + i * (bw + gap), y + h - bh, bw, bh], fill=color, radius=1.5)


def itau_logo(p, x, y, s):
    """The authentic Itaú mark (paths from itau_logo.py) placed at (x, y), box ≈ s.

    The 1024-unit paths are drawn once into a detached layer, then dropped in via a
    group whose transform scales-then-translates them — so the real trademark is
    reused at any size, from the 52 px CTA seal down to the 14 px theming chips."""
    g = PageBuilder({"layers": []}).layer("_logo")
    g.path(_SQUIRCLE, fill=ORANGE)
    g.circle([165.73, 478.8], 42.0, fill="#FFFFFF")
    for d in _GLYPHS:
        g.path(d, fill="#FFFFFF", style={"fill_rule": "evenodd"})
    sc = s / 1024.0
    p.group(g._current_layer.get("objects", []),
            transform=Mat3.translate(x, y) @ Mat3.scale(sc, sc))   # scale, then translate


def window_shell(p, x, y, w, h, th, *, r=14):
    p.rect([x, y, w, h], fill=th["surf"], radius=r, stroke=th["line"],
           stroke_style={"stroke_width": 1},
           shadow={"dx": 0, "dy": 30, "blur": 70, "color": "#00000073"})


# --------------------------------------------------------------------------- #
# the reusable realistic terminal                                              #
# --------------------------------------------------------------------------- #
TW, TH = 1360, 664
TB, SB = 46, 32                      # titlebar / statusbar height


def chrome(p, ox, oy, w, h, th, *, r=14, sub="terminal", tabs=None, active=0,
           gpu="GPU · Sugarloaf", status_mode="NORMAL", status_segs=None, status_right=None):
    """Window shell + titlebar + status bar; returns the inner body box (x,y,w,h)."""
    surf, line, fg, mut = th["surf"], th["line"], th["fg"], th["mut"]
    window_shell(p, ox, oy, w, h, th, r=r)
    # titlebar
    p.rect([ox, oy, w, TB], fill=th["bar"], radius=r)
    p.rect([ox, oy + TB - r, w, r], fill=th["bar"])
    p.line([ox, oy + TB], [ox + w, oy + TB], stroke=line, stroke_style={"stroke_width": 1})
    itau_logo(p, ox + 16, oy + 10, 25)
    T(p, ox + 50, oy + 14, "itaú", size=15, color=fg, font=DISP, weight=700)
    T(p, ox + 84, oy + 14, sub, size=15, color=mut, font=DISP, weight=500)
    tx = ox + 210
    for i, (name, live) in enumerate(tabs or []):
        actv = (i == active)
        tw = 20 + len(name) * 8.6
        if actv:
            p.rect([tx, oy + 9, tw, TB - 18], fill=surf, radius=8, stroke=th["line2"],
                   stroke_style={"stroke_width": 1})
            p.rect([tx + 10, oy + 11, 3, TB - 22], fill=th["orange"], radius=2)
        if live:
            dot(p, tx + tw - 12, oy + TB / 2, 2.6, th["grn"])
        T(p, tx + 18, oy + 14, name, size=13, color=fg if actv else mut, font=UI,
          weight=600 if actv else 500)
        tx += tw + 8
    for i, c in enumerate((th["faint"], th["faint"], th["orange"])):
        p.circle([ox + w - 22 - i * 22, oy + TB / 2], 5.5, fill="none", stroke=c,
                 stroke_style={"stroke_width": 1.4})
    if gpu:
        T(p, ox + w - 210, oy + 15, gpu, size=11.5, color=th["blu"], font=MONO)
    # status bar
    sby = oy + h - SB
    p.rect([ox, sby, w, SB], fill=th["bar"])
    p.rect([ox, sby, w, SB - r], fill=th["bar"])
    p.rect([ox, sby + SB - r, w, r], fill=th["bar"], radius=r)
    p.line([ox, sby], [ox + w, sby], stroke=line, stroke_style={"stroke_width": 1})
    p.rect([ox, sby, 96, SB], fill=th["orange"])
    p.rect([ox, sby + SB - r, 96, r], fill=th["orange"], radius=r)
    p.rect([ox, sby + SB - r, r, r], fill=th["orange"])
    T(p, ox + 20, sby + 8, status_mode, size=12, color="#FFFFFF", font=UI, weight=700, spacing="0.08em")
    stx = ox + 118
    for txt, c in (status_segs or [("itau-ops", mut), ("main", th["mag"]), ("prod", th["cyn"])]):
        T(p, stx, sby + 8, txt, size=12.5, color=c, font=MONO)
        stx += 20 + len(txt) * 8.4
    for txt, c, off in (status_right or [("GPU 120 fps · 1.9 ms", th["blu"], 250), ("14:22", mut, 66)]):
        T(p, ox + w - off, sby + 8, txt, size=12.5, color=c, font=MONO)
    return ox, oy + TB, w, h - TB - SB


def terminal(p, ox, oy, th, *, r=14):
    surf, line, fg, mut, faint = th["surf"], th["line"], th["fg"], th["mut"], th["faint"]
    bx, by, bw, bh = chrome(p, ox, oy, TW, TH, th, r=r, sub="terminal",
        tabs=[("pix-gateway", True), ("auth-core", False), ("ledger", False), ("logs", False)],
        status_segs=[("itau-ops", mut), ("main", th["mag"]), ("prod", th["cyn"])])
    LW = 812
    # left pane bg
    p.rect([bx + 1, by, LW - 1, bh], fill=th["bg"])
    p.line([bx + LW, by], [bx + LW, by + bh], stroke=line, stroke_style={"stroke_width": 1})

    # ============ LEFT: deploy session ============
    lx = bx + 22
    y = by + 20
    ROW = 25

    def prompt(yy, branch_ok=True):
        T(p, lx, yy, "~/itau/ops", size=14.5, color=th["blu"], font=MONO)
        T(p, lx + 108, yy, "git:", size=14.5, color=faint, font=MONO)
        T(p, lx + 142, yy, "main", size=14.5, color=th["mag"], font=MONO)
        check(p, lx + 196, yy + 12, 6, th["grn"])
        chevron(p, lx, yy + ROW + 5, 12, th["orange"])

    bright, dim = ("#E6EAF5", "#B2BDD2") if th is DARK else ("#232E3C", "#6B7789")
    faint = "#77859E" if th is DARK else "#93A0B0"
    CW = 15 * 0.6
    prompt(y)
    runs(p, lx + 20, y + ROW, [("itau", th["orange"], "b"), (" deploy ", bright),
                               ("pix-gateway ", fg, "b"), ("--env ", dim), ("prod", th["cyn"])])
    y += ROW * 2 + 6
    out = [
        [("→ ", th["cyn"]), ("resolve  ", dim), ("manifest", bright), (" · 42 objects · ", dim), ("ok", th["grn"])],
        [("→ ", th["cyn"]), ("build    ", dim), ("rust 1.84", bright), (" · musl · ", dim), ("sha256:a3f9c2", th["yel"])],
        [("→ ", th["cyn"]), ("scan     ", dim), ("0 CVE", th["grn"]), (" · cosign verified", bright)],
    ]
    for r_ in out:
        runs(p, lx + 20, y, r_)
        y += ROW
    # rollout progress
    T(p, lx + 20, y, "rollout", size=15, color=dim, font=MONO)
    progress(p, lx + 130, y + 8, 236, 9, 0.72, th["orange"], th["line"])
    T(p, lx + 380, y, "72%", size=15, color=bright, font=MONO)
    T(p, lx + 436, y, "3/5 pods", size=15, color=dim, font=MONO)
    y += ROW
    check(p, lx + 25, y + 13, 6, th["grn"])
    runs(p, lx + 42, y, [("health   ", dim), ("200 OK", th["grn"]), (" · p99 ", dim), ("3.1ms", bright)])
    y += ROW
    check(p, lx + 25, y + 13, 6, th["grn"])
    runs(p, lx + 42, y, [("deployed ", fg, "b"), ("rev a3f9c2", th["yel"]), (" · ", dim),
                         ("0 downtime", th["grn"]), (" · 2.4s", dim)])
    y += ROW + 12
    prompt(y)
    runs(p, lx + 20, y + ROW, [("itau", th["orange"], "b"), (" pix watch ", bright), ("--live", dim)])
    y += ROW * 2
    tail = [
        ("14:22:07", "in", "R$ 1.240,00", "2.1ms"),
        ("14:22:07", "out", "R$ 89,90", "1.8ms"),
        ("14:22:08", "in", "R$ 15.000,00", "3.0ms"),
        ("14:22:08", "in", "R$ 320,50", "2.2ms"),
        ("14:22:09", "out", "R$ 4.780,00", "2.6ms"),
    ]
    for t, dirn, amt, ms in tail:
        col = th["blu"] if dirn == "in" else th["cyn"]
        runs(p, lx + 20, y, [(t + "  ", faint), (("pix." + dirn).ljust(8), col),
                             (amt.ljust(14), bright), ("ok ", th["grn"]), (ms, dim)])
        y += ROW - 2
    dot(p, lx + 23, y + 9, 4, th["grn"])
    T(p, lx + 38, y, "streaming · 3.190 msg/s", size=13.5, color=dim, font=MONO)

    # ============ RIGHT COLUMN ============
    rx = bx + LW + 1
    rw = TW - LW - 1
    rmid = by + int(bh * 0.52)
    p.rect([rx, by, rw, bh], fill=th["surf"])
    p.line([rx, rmid], [rx + rw, rmid], stroke=line, stroke_style={"stroke_width": 1})

    # ---- top card: PIX throughput ----
    px = rx + 22
    T(p, px, by + 18, "PIX · THROUGHPUT", size=11.5, color=mut, font=UI, weight=700, spacing="0.12em")
    dot(p, rx + rw - 30, by + 25, 3.5, th["grn"])
    T(p, rx + rw - 96, by + 18, "live", size=11.5, color=th["grn"], font=UI, weight=600)
    T(p, px, by + 38, "18,420", size=40, color=fg, font=DISP, weight=700)
    T(p, px + 168, by + 62, "tps", size=15, color=mut, font=UI)
    tri(p, px + 214, by + 58, 5, th["grn"], up=True)
    T(p, px + 226, by + 52, "4.2%", size=13.5, color=th["grn"], font=UI, weight=600)
    bars(p, px, by + 96, rw - 44, 46,
         [12, 15, 13, 18, 22, 19, 24, 21, 27, 25, 31, 28, 34, 30, 33, 29, 36, 40, 37, 42],
         th["orange"])
    p.line([px, by + 150], [rx + rw - 22, by + 150], stroke=th["line"], stroke_style={"stroke_width": 1})
    stats = [("p99", "2.9ms", th["fg"]), ("erro", "0.01%", th["grn"]), ("auth", "128k/s", th["blu"])]
    sw = (rw - 44) / 3
    for i, (k, v, c) in enumerate(stats):
        T(p, px + i * sw, by + 162, k, size=11, color=faint, font=UI, weight=600, spacing="0.08em")
        T(p, px + i * sw, by + 178, v, size=17, color=c, font=MONO, weight=700)

    # ---- bottom card: services ----
    sx = rx + 22
    sy = rmid + 18
    T(p, sx, sy, "SERVIÇOS", size=11.5, color=mut, font=UI, weight=700, spacing="0.12em")
    T(p, rx + rw - 78, sy, "5 up", size=11.5, color=th["grn"], font=UI, weight=600)
    sy += 26
    svc = [("pix-gateway", "18.4k/s", th["grn"], "live"),
           ("auth-core", "128k/s", th["grn"], "live"),
           ("ledger-write", "42.0k/s", th["grn"], "live"),
           ("fraud-score", "9.1k/s", th["yel"], "warm"),
           ("statement-api", "5.6k/s", th["grn"], "live")]
    for name, thr, c, stt in svc:
        dot(p, sx + 4, sy + 9, 4, c)
        T(p, sx + 16, sy, name, size=13.5, color=fg, font=MONO)
        T(p, sx + 190, sy, thr, size=13.5, color=mut, font=MONO, align="left")
        T(p, rx + rw - 60, sy, stt, size=12, color=c, font=UI, weight=600)
        sy += 27


# --------------------------------------------------------------------------- #
# PAGE 1 · cover                                                                #
# --------------------------------------------------------------------------- #
def cover():
    p = page("cover", NAVY2)
    p.rect([0, 0, W, H], fill=linear_gradient([("#02122E", "0%"), (NAVY2, "55%"), ("#0A0A12", "100%")], angle=155))
    p.rect([0, 0, W, H], fill=radial_gradient([(rgba(ORANGE, 0.20), "0%"), (rgba(ORANGE, 0.0), "60%")], at="82% 6%"))
    p.rect([0, 0, W, H], fill=radial_gradient([(rgba(BLUE_HI, 0.16), "0%"), (rgba(BLUE_HI, 0.0), "55%")], at="6% 96%"))
    # top brand row
    itau_logo(p, 96, 72, 38)
    T(p, 148, 80, "itaú", size=22, color="#FFFFFF", font=DISP, weight=700)
    T(p, 184, 80, "· engineering", size=22, color="#8FA6C8", font=DISP, weight=400)
    T(p, W - 360, 82, "UI/UX PROPOSAL · CONFIDENTIAL", size=12.5, color="#7C93B8", font=UI,
      weight=600, spacing="0.16em", align="right", w=264)
    # headline
    T(p, 92, 232, "PROPOSTA DE INTERFACE", size=15, color=ORANGE_HI, font=UI, weight=700, spacing="0.34em")
    T(p, 88, 258, "The bank's", size=104, color="#FFFFFF", font=DISP, weight=700, w=1400, h=118)
    T(p, 88, 360, "command line,", size=104, color="#FFFFFF", font=DISP, weight=700, w=1400, h=118)
    p.text([88, 462, 1400, 118], [span("re", color="#FFFFFF", font=DISP, size=104),
                                   span("imagined", color=ORANGE, font=DISP, size=104)],
           style={"font_family": DISP, "font_weight": 700, "font_size": 104})
    T(p, 96, 606, "A modern terminal for Itaú operations — GPU-rendered, memory-safe, "
      "audit-ready.", size=21, color="#C4D2E6", font=UI, w=740, h=64)
    T(p, 96, 684, "Powered by Rust · Rio (Sugarloaf).", size=21, color="#8FA6C8", font=UI, w=760)
    # meta chips
    cy = 762
    for i, (k, v) in enumerate([("RENDERER", "Rust · Rio"), ("SURFACE", "Ops · Dev · Suporte"),
                                ("STATUS", "Concept v1")]):
        cxp = 96 + i * 220
        p.rect([cxp, cy, 200, 74], fill="#0C1730", radius=12,
               stroke="#1E2C4A", stroke_style={"stroke_width": 1})
        T(p, cxp + 18, cy + 16, k, size=11, color="#6E86AC", font=UI, weight=700, spacing="0.14em")
        T(p, cxp + 18, cy + 38, v, size=18, color="#FFFFFF", font=DISP, weight=600)
    # peeking terminal on the right
    terminal(p, W - 640, 300, DARK)
    T(p, W - 360, H - 46, "Rendered by FrameGraph · SDK", size=12.5, color="#5E7396",
      font=MONO, align="right", w=264)


# --------------------------------------------------------------------------- #
# PAGE 2 · hero (dark terminal)                                                 #
# --------------------------------------------------------------------------- #
def hero(th=DARK, pid="hero", label="TEMA ESCURO · OPERAÇÕES", bg=None):
    p = page(pid, bg or "#080B12")
    if th is DARK:
        p.rect([0, 0, W, H], fill=radial_gradient([("#0E1626", "0%"), ("#080B12", "70%")], at="50% 0%"))
        p.rect([0, 0, W, H], fill=radial_gradient([(rgba(ORANGE, 0.10), "0%"), (rgba(ORANGE, 0.0), "55%")], at="88% 92%"))
    T(p, 120, 58, label, size=13, color=th["orange"] if th is DARK else ORANGE_DK,
      font=UI, weight=700, spacing="0.28em")
    T(p, 120, 82, "Itaú Terminal", size=34, color=th["fg"] if th is DARK else "#12203A",
      font=DISP, weight=700)
    T(p, W - 520, 76, "Uma sessão de deploy real: build Rust, rollout, e o painel PIX ao vivo — "
      "tudo em uma superfície.", size=14.5, color="#8DA0BE" if th is DARK else "#5A6575",
      font=UI, align="right", w=400, h=52)
    terminal(p, (W - TW) / 2, 150, th)


def light():
    hero(LIGHT, "light", "TEMA CLARO · MESMA SUPERFÍCIE", bg="#E4DED3")


# --------------------------------------------------------------------------- #
# PAGE 3 · anatomy (annotated)                                                  #
# --------------------------------------------------------------------------- #
def anatomy():
    th = DARK
    p = page("anatomy", "#080B12")
    p.rect([0, 0, W, H], fill=radial_gradient([("#0E1626", "0%"), ("#080B12", "74%")], at="50% 0%"))
    T(p, 120, 66, "ANATOMIA", size=13, color=ORANGE_HI, font=UI, weight=700, spacing="0.28em")
    T(p, 120, 90, "Uma superfície, seis sistemas", size=32, color="#EEF2FB", font=DISP, weight=700)
    fg, mut, line, faint = th["fg"], th["mut"], th["line"], th["faint"]

    def i_tabs(px, py, pw, ph):
        p.rect([px + 12, py + 14, pw - 24, ph - 26], fill="#0B0E16", radius=8, stroke=line, stroke_style={"stroke_width": 1})
        for k in range(3):
            p.rect([px + 22 + k * 40, py + 22, 34, 12], fill=th["surf"] if k else rgba(th["orange"], 0.25), radius=4)
        p.line([px + pw / 2, py + 40], [px + pw / 2, py + ph - 16], stroke=line, stroke_style={"stroke_width": 1})
        for k in range(3):
            p.rect([px + 22, py + 48 + k * 12, 60, 4], fill=th["line2"], radius=2)
            p.rect([px + pw / 2 + 12, py + 48 + k * 12, 60, 4], fill=th["line2"], radius=2)

    def i_gpu(px, py, pw, ph):
        cx, cy = px + pw / 2, py + ph / 2 - 4
        p.rect([cx - 30, cy - 30, 60, 60], fill=radial_gradient([(rgba(th["orange"], 0.5), "0%"), (rgba(th["orange"], 0.0), "80%")], at="50% 50%"))
        p.rect([cx - 22, cy - 22, 44, 44], fill="#0B0E16", radius=8, stroke=th["orange"], stroke_style={"stroke_width": 1.6})
        for k in range(4):
            p.rect([cx - 14 + k * 9, cy - 30, 4, 8], fill=th["orange"], radius=1)
            p.rect([cx - 14 + k * 9, cy + 22, 4, 8], fill=th["orange"], radius=1)
        T(p, cx - 30, cy - 8, "120", size=17, color=fg, font=DISP, weight=700, w=60, align="center")
        T(p, cx - 30, cy + 12, "fps", size=10, color=mut, font=UI, w=60, align="center")

    def i_prompt(px, py, pw, ph):
        chevron(p, px + 20, py + 20, 12, th["orange"])
        p.rect([px + 40, py + 24, 90, 6], fill=fg, radius=3)
        p.rect([px + 138, py + 24, 40, 6], fill=th["cyn"], radius=3)
        p.rect([px + 40, py + 40, pw - 100, ph - 54], fill=th["surf"], radius=8, stroke=th["line2"], stroke_style={"stroke_width": 1})
        for k in range(3):
            p.rect([px + 52, py + 50 + k * 13, 6, 6], fill=th["orange"] if k == 0 else faint, radius=3)
            p.rect([px + 66, py + 50 + k * 13, 70 - k * 12, 5], fill=th["line2"] if k else fg, radius=2)

    def i_pix(px, py, pw, ph):
        bars(p, px + 20, py + 40, pw - 40, ph - 54, [6, 9, 7, 12, 10, 14, 12, 16, 15, 19, 17, 21], th["orange"])
        T(p, px + 20, py + 14, "18.4k", size=20, color=fg, font=DISP, weight=700)
        tri(p, px + 108, py + 24, 4, th["grn"], up=True)
        T(p, px + 118, py + 16, "4.2%", size=12, color=th["grn"], font=UI, weight=600)

    def i_health(px, py, pw, ph):
        cols = [th["grn"], th["grn"], th["yel"], th["grn"]]
        for k in range(4):
            dot(p, px + 26, py + 20 + k * 18, 4, cols[k])
            p.rect([px + 38, py + 17 + k * 18, 80, 5], fill=th["line2"], radius=2)
            p.rect([px + pw - 60, py + 16 + k * 18, 34, 7], fill=rgba(cols[k], 0.18), radius=3)

    def i_theme(px, py, pw, ph):
        for j, (bg, bar) in enumerate([("#0B0E16", th["orange"]), ("#ECE7DE", th["orange"])]):
            sxx = px + 22 + j * ((pw - 60) / 2 + 16)
            p.rect([sxx, py + 16, (pw - 60) / 2, ph - 30], fill=bg, radius=8, stroke=line, stroke_style={"stroke_width": 1})
            p.rect([sxx, py + 16, (pw - 60) / 2, 12], fill=bar, radius=8)
            p.rect([sxx, py + 22, (pw - 60) / 2, 6], fill=bar)
            for k in range(3):
                p.rect([sxx + 10, py + 36 + k * 12, 46 - k * 10, 4], fill="#33415E" if j == 0 else "#C9BEA9", radius=2)

    feats = [
        (1, "Abas & splits", "Sessões prod e staging lado a lado, em splits nativos do Rio.", i_tabs),
        (2, "GPU · Sugarloaf", "Renderização por GPU: 120 fps constantes, input abaixo de 2 ms.", i_gpu),
        (3, "Prompt tipado", "itau-cli com autocompletar, validação e histórico pesquisável.", i_prompt),
        (4, "Painel PIX ao vivo", "Throughput, p99 e taxa de erro sempre no campo de visão.", i_pix),
        (5, "Saúde auditável", "Status cor-coded por serviço e trilha de scrollback assinada.", i_health),
        (6, "Temas Itaú", "Um documento, dois temas — troca por token, sem re-desenhar.", i_theme),
    ]
    cw, ch, gap = 436, 276, 26
    for i, (n, title, desc, illus) in enumerate(feats):
        x = 120 + (i % 3) * (cw + gap)
        y = 176 + (i // 3) * (ch + 24)
        p.rect([x, y, cw, ch], fill=th["surf"], radius=16, stroke=line, stroke_style={"stroke_width": 1})
        p.rect([x + 20, y + 20, cw - 40, 104], fill="#0C111C", radius=10, stroke=line, stroke_style={"stroke_width": 1})
        illus(x + 20, y + 20, cw - 40, 104)
        dot(p, x + 36, y + 152, 13, th["orange"])
        T(p, x + 31.5, y + 143.5, str(n), size=14, color="#FFFFFF", font=DISP, weight=700, w=20, align="center")
        T(p, x + 60, y + 143, title, size=19, color=fg, font=DISP, weight=700)
        T(p, x + 24, y + 182, desc, size=13.5, color="#93A0BA", font=UI, w=cw - 44, h=48)


# --------------------------------------------------------------------------- #
# PAGE 4 · design system                                                        #
# --------------------------------------------------------------------------- #
def system():
    p = page("system", "#0B0F1A")
    T(p, 120, 66, "SISTEMA DE DESIGN", size=13, color=ORANGE_HI, font=UI, weight=700, spacing="0.28em")
    T(p, 120, 90, "Tokens & tipografia", size=32, color="#EEF2FB", font=DISP, weight=700)

    # palette
    T(p, 120, 170, "MARCA", size=12, color="#7C8CA8", font=UI, weight=700, spacing="0.14em")
    brand = [("Itaú Orange", ORANGE), ("Orange Hi", ORANGE_HI), ("Itaú Blue", BLUE),
             ("Blue Hi", BLUE_HI), ("Navy", NAVY)]
    for i, (name, c) in enumerate(brand):
        x = 120 + i * 150
        p.rect([x, 196, 132, 92], fill=c, radius=12)
        T(p, x + 2, 296, name, size=13, color="#D6DEEC", font=UI, weight=600)
        T(p, x + 2, 314, c.upper(), size=12, color="#6E7E9A", font=MONO)

    T(p, 120, 372, "TERMINAL · ANSI", size=12, color="#7C8CA8", font=UI, weight=700, spacing="0.14em")
    ansi = [("bg", DARK["bg"]), ("surface", DARK["surf"]), ("fg", DARK["fg"]), ("green", DARK["grn"]),
            ("yellow", DARK["yel"]), ("red", DARK["red"]), ("cyan", DARK["cyn"]), ("blue", DARK["blu"]),
            ("magenta", DARK["mag"]), ("orange", DARK["orange"])]
    for i, (name, c) in enumerate(ansi):
        x = 120 + i * 92
        p.rect([x, 398, 78, 56], fill=c, radius=9, stroke="#232C42", stroke_style={"stroke_width": 1})
        T(p, x + 2, 460, name, size=11.5, color="#9AA6BD", font=MONO)

    # typography specimens
    T(p, 120, 526, "TIPOGRAFIA", size=12, color="#7C8CA8", font=UI, weight=700, spacing="0.14em")
    specs = [("Space Grotesk", DISP, "Display · títulos", 700),
             ("Inter", UI, "UI · corpo e rótulos", 500),
             ("Space Mono", MONO, "Mono · terminal e código", 400)]
    for i, (name, fam, role, wt) in enumerate(specs):
        y = 558 + i * 92
        T(p, 120, y, "Aa", size=52, color="#EEF2FB", font=fam, weight=wt, w=120)
        T(p, 210, y + 6, name, size=22, color="#EEF2FB", font=fam, weight=700)
        T(p, 210, y + 40, role, size=14, color="#8DA0BE", font=UI)
        T(p, 470, y + 6, "ITAÚ pix ledger 0123456789 → { }", size=20, color="#C4D2E6", font=fam, weight=wt, w=760)

    # right: a mini light terminal card as a swatch of "theming"
    p.rect([1080, 170, 400, 300], fill="#111827", radius=14,
           stroke="#222C42", stroke_style={"stroke_width": 1})
    T(p, 1104, 190, "MESMO DOC · DOIS TEMAS", size=11, color="#7C8CA8", font=UI, weight=700, spacing="0.12em")
    p.rect([1104, 218, 168, 230], fill=DARK["bg"], radius=10, stroke="#222C42", stroke_style={"stroke_width": 1})
    p.rect([1288, 218, 168, 230], fill=LIGHT["bg"], radius=10, stroke="#D6CCBA", stroke_style={"stroke_width": 1})
    for xx, th in ((1104, DARK), (1288, LIGHT)):
        p.rect([xx, 218, 168, 26], fill=th["bar"], radius=10)
        p.rect([xx, 236, 168, 8], fill=th["bar"])
        itau_logo(p, xx + 10, 224, 14)
        for k in range(6):
            p.rect([xx + 14, 258 + k * 26, 90 + (k % 3) * 30, 6], fill=th["line2"], radius=3)
            dot(p, xx + 150, 261 + k * 26, 3, [th["grn"], th["yel"], th["orange"]][k % 3])
    T(p, 1104, 462, "Um tema por token — troca sem re-desenhar.", size=12.5, color="#8DA0BE", font=UI, w=380)


# --------------------------------------------------------------------------- #
# PAGE 5 · performance + roadmap + close                                        #
# --------------------------------------------------------------------------- #
def perform():
    p = page("close", NAVY2)
    p.rect([0, 0, W, H], fill=linear_gradient([("#02122E", "0%"), (NAVY2, "60%"), ("#080A10", "100%")], angle=150))
    p.rect([0, 0, W, H], fill=radial_gradient([(rgba(ORANGE, 0.14), "0%"), (rgba(ORANGE, 0.0), "50%")], at="90% 12%"))
    T(p, 120, 70, "POR QUE RUST · RIO", size=13, color=ORANGE_HI, font=UI, weight=700, spacing="0.28em")
    T(p, 118, 96, "Fast, safe, auditável", size=40, color="#FFFFFF", font=DISP, weight=700)

    # metric bars vs legacy
    metrics = [("Render", "120 fps", 1.0, "legado 18 fps", 0.15),
               ("Input latency", "1.9 ms", 0.92, "legado 22 ms", 0.55, True),
               ("Cold start", "180 ms", 0.88, "legado 3.4 s", 0.62, True),
               ("Memória", "84 MB", 0.9, "legado 210 MB", 0.5, True)]
    by = 210
    for m in metrics:
        name, val = m[0], m[1]
        good = m[2]
        T(p, 120, by, name, size=15, color="#C4D2E6", font=UI, weight=600, w=220)
        p.rect([340, by + 3, 620, 16], fill="#0E1B36", radius=8)
        p.rect([340, by + 3, 620 * good, 16], fill=linear_gradient([(ORANGE, "0%"), (ORANGE_HI, "100%")], angle=90), radius=8)
        T(p, 980, by - 1, val, size=17, color="#FFFFFF", font=DISP, weight=700, w=160)
        T(p, 340, by + 26, m[3], size=12, color="#6E86AC", font=MONO)
        by += 74

    # right rail: pillars
    rx = 1120
    T(p, rx, 200, "GARANTIAS", size=12, color="#6E86AC", font=UI, weight=700, spacing="0.14em")
    pill = [("Memory-safe", "sem classes inteiras de CVE", DARK["grn"]),
            ("Zero-downtime", "rollout observável, reversível", ORANGE_HI),
            ("Scrollback auditável", "trilha assinada, LGPD-ready", BLUE_HI)]
    for i, (t, s, c) in enumerate(pill):
        y = 232 + i * 92
        p.rect([rx, y, 360, 76], fill="#0C1730", radius=12, stroke="#1E2C4A", stroke_style={"stroke_width": 1})
        p.rect([rx, y + 14, 4, 48], fill=c, radius=2)
        T(p, rx + 22, y + 14, t, size=16.5, color="#FFFFFF", font=DISP, weight=600)
        T(p, rx + 22, y + 40, s, size=13, color="#9BB0CE", font=UI, w=320)

    # roadmap timeline
    T(p, 120, 566, "ROADMAP", size=12, color="#6E86AC", font=UI, weight=700, spacing="0.14em")
    p.line([140, 616], [1460, 616], stroke="#22345A", stroke_style={"stroke_width": 2})
    phases = [("Fase 1", "Piloto ops · tema Itaú", 0.0),
              ("Fase 2", "itau-cli + painéis PIX", 0.28),
              ("Fase 3", "Splits, palette, plugins", 0.56),
              ("Fase 4", "Rollout · 400 estações", 0.84)]
    for name, sub, f in phases:
        x = 140 + 1320 * f
        dot(p, x, 616, 8, ORANGE if f == 0 else "#0C1730", ring=ORANGE)
        if f == 0:
            dot(p, x, 616, 8, ORANGE)
        T(p, x - 4, 636, name, size=15, color="#FFFFFF", font=DISP, weight=600, w=240)
        T(p, x - 4, 660, sub, size=12.5, color="#8DA0BE", font=UI, w=300)

    # CTA footer
    p.rect([120, 738, 1360, 96], fill=linear_gradient([("#10233F", "0%"), ("#0A1730", "100%")], angle=100),
           radius=16, stroke="#20345C", stroke_style={"stroke_width": 1})
    itau_logo(p, 148, 758, 52)
    T(p, 218, 758, "Vamos construir o terminal do Itaú.", size=24, color="#FFFFFF", font=DISP, weight=700)
    T(p, 210, 792, "Protótipo navegável em 2 sprints · rendered by FrameGraph.", size=14.5, color="#9BB0CE", font=UI)
    p.rect([1230, 764, 218, 44], fill=ORANGE, radius=10)
    T(p, 1230, 776, "Aprovar piloto  →", size=15.5, color="#FFFFFF", font=UI, weight=700, w=218, align="center")


# --------------------------------------------------------------------------- #
# PAGE · CORE banking today — the 3270 green screen                             #
# --------------------------------------------------------------------------- #
def core_legacy():
    p = page("core-legacy", "#04060B")
    T(p, 120, 58, "CORE BANKING · HOJE", size=13, color="#46C36B", font=UI, weight=700, spacing="0.28em")
    T(p, 118, 82, "40 anos de COBOL. Ainda no núcleo.", size=32, color="#EAF3FF", font=DISP, weight=700)
    T(p, W - 560, 76, "Emulação 3270 · CICS · mapas BMS. Rígido, decorado, "
      "uma transação por tela.", size=14.5, color="#7E8CA6", font=UI, align="right", w=440, h=52)

    gx, gy, gw, gh = 240, 172, 1120, 590
    G, GD, WH, TQ, YE, RD = "#3CE072", "#2E9E54", "#DAFFE7", "#57E6D6", "#ECD456", "#FF7A6B"
    p.rect([gx, gy, gw, gh], fill="#0A0B0C", radius=14, stroke="#1C2A20",
           stroke_style={"stroke_width": 1}, shadow={"dx": 0, "dy": 30, "blur": 70, "color": "#00000085"})
    p.rect([gx, gy, gw, 38], fill="#0E120E", radius=14)
    p.rect([gx, gy + 24, gw, 14], fill="#0E120E")
    p.line([gx, gy + 38], [gx + gw, gy + 38], stroke="#1C2A20", stroke_style={"stroke_width": 1})
    dot(p, gx + 20, gy + 19, 5, GD)
    T(p, gx + 38, gy + 11, "3270   ·   CICS PRODA   ·   LU TCP00042", size=13, color="#6FB98A", font=MONO)
    T(p, gx + gw - 150, gy + 11, "SSCP  24 x 80", size=12.5, color="#3F6B50", font=MONO)
    # screen + phosphor glow + scanlines
    sx, sy, sw, sh = gx + 2, gy + 40, gw - 4, gh - 42
    p.rect([sx, sy, sw, sh], fill="#03130A")
    p.rect([sx, sy, sw, sh], fill=radial_gradient([(rgba("#25E060", 0.12), "0%"),
           (rgba("#25E060", 0.0), "72%")], at="50% 42%"))
    yy = sy
    while yy < sy + sh:
        p.rect([sx, yy, sw, 1], fill=rgba("#000000", 0.17))
        yy += 4

    ax, ay, SZ, RH = sx + 46, sy + 30, 16.5, 27

    def ml(row, x, s, c, size=SZ):
        T(p, x, ay + row * RH, s, size=size, color=c, font=MONO)

    def rule(row):
        p.rect([ax, ay + row * RH + 11, sw - 92, 1.4], fill=GD)

    C = ax + 150                                   # value column (left group)
    ml(0, ax, "CONSULTA DE CONTA CORRENTE", WH)
    ml(0, sx + sw - 210, "ACIN", TQ)
    ml(0, sx + sw - 130, "PRODA", TQ)
    rule(1)
    ml(2, ax, "AGENCIA. . :", GD); ml(2, C, "0298", WH)
    ml(2, ax + 470, "CONTA . . :", GD); ml(2, ax + 590, "01234567-8", WH)
    ml(4, ax, "TITULAR. . :", GD); ml(4, C, "MARIA S. OLIVEIRA", WH)
    ml(5, ax, "CPF . . . :", GD); ml(5, C, "***.456.789-**", WH)
    ml(5, ax + 470, "ABERTURA:", GD); ml(5, ax + 590, "12/03/2009", WH)
    ml(6, ax, "PRODUTO. . :", GD); ml(6, C, "CONTA CORRENTE", WH)
    ml(6, ax + 470, "SITUACAO:", GD); ml(6, ax + 590, "ATIVA", G)
    ml(8, ax, "SALDO DISP :", GD); ml(8, C, "R$      12.480,55", WH, size=17.5)
    ml(9, ax, "SALDO BLOQ :", GD); ml(9, C, "R$         320,00", WH)
    ml(10, ax, "LIMITE LIS :", GD); ml(10, C, "R$       5.000,00", WH)
    ml(12, ax, "ULT MOVTO  :", GD); ml(12, C, "21/05/2026   PIX RECEBIDO      R$ 1.240,00", WH)
    rule(13)
    ml(14, ax, "TRANSACAO ACEITA  —  EIBRESP 0", TQ)
    ml(15.4, ax, "PF3=SAIR   PF5=EXTRATO   PF7=VOLTA   PF8=AVANCA   ENTER=CONFIRMAR", YE, size=15)
    p.rect([C + 190, ay + 4 * RH + 2, 11, 19], fill=G)   # block cursor

    pains = ["Teclas de função decoradas", "Sem busca ou contexto",
             "1 transação por tela", "Treinamento longo · erro humano"]
    for i, s in enumerate(pains):
        x = 240 + i * 285
        dot(p, x + 5, 800, 3.5, RD)
        T(p, x + 18, 792, s, size=13.5, color="#93A0B0", font=UI, w=270)


# --------------------------------------------------------------------------- #
# PAGE · CORE banking modernised — same COBOL, modern face                      #
# --------------------------------------------------------------------------- #
def core_modern():
    th = DARK
    p = page("core-modern", "#080B12")
    p.rect([0, 0, W, H], fill=radial_gradient([("#0E1626", "0%"), ("#080B12", "72%")], at="50% 0%"))
    p.rect([0, 0, W, H], fill=radial_gradient([(rgba(ORANGE, 0.09), "0%"), (rgba(ORANGE, 0.0), "55%")], at="86% 90%"))
    T(p, 120, 54, "CORE BANKING · REVESTIDO", size=13, color=ORANGE_HI, font=UI, weight=700, spacing="0.28em")
    T(p, 120, 78, "O mesmo COBOL. Uma face moderna.", size=32, color="#EEF2FB", font=DISP, weight=700)
    T(p, W - 520, 74, "O terminal fala 3270 com o CICS e mostra moderno — o núcleo "
      "não muda uma linha.", size=14.5, color="#8DA0BE", font=UI, align="right", w=400, h=52)

    ox, oy = (W - TW) / 2, 158
    bx, by, bw, bh = chrome(p, ox, oy, TW, TH, th, sub="core",
        tabs=[("core · ACIN", True), ("pix-gateway", False), ("extrato", False)], active=0,
        gpu="CICS · PRODA", status_mode="CICS",
        status_segs=[("region PRODA", th["mut"]), ("txn ACIN", th["cyn"]), ("COBOL", th["mag"])],
        status_right=[("EIBRESP 0 · 12 ms", th["grn"], 210), ("14:22", th["mut"], 66)])
    fg, mut, line = th["fg"], th["mut"], th["line"]
    dim = "#9BA7BE"

    LW = 884
    p.rect([bx + 1, by, LW - 1, bh], fill=th["bg"])
    p.line([bx + LW, by], [bx + LW, by + bh], stroke=line, stroke_style={"stroke_width": 1})
    lx = bx + 30
    # command that opened the map
    chevron(p, lx, by + 26, 12, th["orange"])
    runs(p, lx + 20, by + 20, [("itau", th["orange"], "b"), (" core open ", fg),
                               ("ACIN ", fg, "b"), ("--conta ", dim), ("01234567-8", th["cyn"])])
    # account header
    hy = by + 66
    T(p, lx, hy, "Conta Corrente", size=15, color=mut, font=UI, weight=600)
    T(p, lx, hy + 18, "01234567-8", size=30, color=fg, font=DISP, weight=700)
    p.rect([lx + 232, hy + 24, 78, 26], fill=rgba(th["blu"], 0.16), radius=13)
    T(p, lx + 232, hy + 28, "ag. 0298", size=12.5, color=th["blu"], font=MONO, w=78, align="center")
    p.rect([lx + 320, hy + 24, 74, 26], fill=rgba(th["grn"], 0.16), radius=13)
    dot(p, lx + 336, hy + 37, 3.5, th["grn"])
    T(p, lx + 346, hy + 28, "ATIVA", size=12, color=th["grn"], font=UI, weight=700)
    p.line([lx, hy + 66], [bx + LW - 26, hy + 66], stroke=line, stroke_style={"stroke_width": 1})

    # field grid 2 x 2
    fields = [("TITULAR", "Maria S. Oliveira"), ("CPF", "***.456.789-**"),
              ("PRODUTO", "Conta Corrente"), ("ABERTURA", "12/03/2009")]
    for i, (k, v) in enumerate(fields):
        fx = lx + (i % 2) * 420
        fy = hy + 88 + (i // 2) * 50
        T(p, fx, fy, k, size=11, color=th["faint"], font=UI, weight=700, spacing="0.1em")
        T(p, fx, fy + 16, v, size=16, color=fg, font=MONO)

    # balance cards
    T(p, lx, hy + 200, "SALDOS", size=11, color=th["faint"], font=UI, weight=700, spacing="0.14em")
    cards = [("SALDO DISPONÍVEL", "R$ 12.480,55", th["orange"], True),
             ("SALDO BLOQUEADO", "R$ 320,00", fg, False),
             ("LIMITE (LIS)", "R$ 5.000,00", fg, False)]
    cw = (LW - 60 - 24) / 3
    for i, (k, v, c, big) in enumerate(cards):
        cx = lx + i * (cw + 12)
        cyy = hy + 222
        p.rect([cx, cyy, cw, 88], fill=th["surf"], radius=12, stroke=line, stroke_style={"stroke_width": 1})
        if big:
            p.rect([cx, cyy, 3, 88], fill=th["orange"], radius=2)
        T(p, cx + 18, cyy + 16, k, size=11, color=mut, font=UI, weight=700, spacing="0.06em")
        T(p, cx + 18, cyy + 38, v, size=23 if big else 20, color=c, font=DISP, weight=700)
    # last movement
    my = hy + 336
    dot(p, lx + 5, my + 8, 4, th["grn"])
    runs(p, lx + 18, my, [("último ", mut), ("PIX recebido", "#E6EAF5", "b"), ("  ·  21/05  ·  ", dim),
                          ("R$ 1.240,00", th["grn"], "b")], size=14.5)

    # PF-key chip bar
    py = by + bh - 52
    p.line([lx - 30, py - 10], [bx + LW - 26, py - 10], stroke=line, stroke_style={"stroke_width": 1})
    pfs = [("F3", "Sair"), ("F5", "Extrato"), ("F7", "Volta"), ("F8", "Avança"), ("↵", "Confirmar")]
    px = lx
    for key, lab in pfs:
        kw = 30 + len(lab) * 8.2
        p.rect([px, py, kw, 30], fill=th["surf"], radius=8, stroke=th["line2"], stroke_style={"stroke_width": 1})
        p.rect([px + 6, py + 6, 20, 18], fill=rgba(th["orange"], 0.16), radius=5)
        T(p, px + 6, py + 8, key, size=11.5, color=th["orange"], font=MONO, weight=700, w=20, align="center")
        T(p, px + 32, py + 7, lab, size=13, color=fg, font=UI)
        px += kw + 10

    # ===== right rail: the CICS bridge =====
    rx = bx + LW + 1
    rw = TW - LW - 1
    p.rect([rx, by, rw, bh], fill=th["surf"])
    qx = rx + 26
    T(p, qx, by + 22, "PONTE CICS", size=11.5, color=mut, font=UI, weight=700, spacing="0.12em")
    dot(p, rx + rw - 30, by + 29, 3.5, th["grn"])
    T(p, rx + rw - 92, by + 22, "conectado", size=11.5, color=th["grn"], font=UI, weight=600)
    rows = [("region", "PRODA"), ("programa", "ACCTINQ.cbl"), ("transação", "ACIN"),
            ("EIBRESP", "0  (OK)"), ("commarea", "512 bytes"), ("tempo", "12 ms"),
            ("chamadas", "3.4k / s")]
    ry = by + 54
    for k, v in rows:
        T(p, qx, ry, k, size=13, color=dim, font=UI)
        T(p, qx, ry, v, size=13.5, color=fg if "EIBRESP" not in k else th["grn"],
          font=MONO, align="right", w=rw - 52)
        ry += 30
    # untouched-core badge
    p.rect([qx, ry + 8, rw - 52, 66], fill=rgba(th["grn"], 0.08), radius=12,
           stroke=rgba(th["grn"], 0.35), stroke_style={"stroke_width": 1})
    check(p, qx + 22, ry + 41, 8, th["grn"])
    T(p, qx + 40, ry + 24, "Núcleo intocado", size=15.5, color=fg, font=DISP, weight=600)
    T(p, qx + 40, ry + 47, "0 linhas de COBOL reescritas", size=12.5, color=dim, font=UI, w=260)
    # antes -> depois
    ay2 = ry + 100
    T(p, qx, ay2, "ANTES  →  DEPOIS", size=11, color=th["faint"], font=UI, weight=700, spacing="0.1em")
    p.rect([qx, ay2 + 22, 96, 60], fill="#03130A", radius=8, stroke="#1C2A20", stroke_style={"stroke_width": 1})
    for k in range(4):
        p.rect([qx + 10, ay2 + 32 + k * 11, 60 - k * 8, 3], fill="#2E9E54", radius=1)
    chevron(p, qx + 118, ay2 + 42, 14, th["orange"])
    p.rect([qx + 150, ay2 + 22, rw - 52 - 150, 60], fill=th["bg"], radius=8, stroke=line, stroke_style={"stroke_width": 1})
    itau_logo(p, qx + 162, ay2 + 32, 15)
    for k in range(3):
        p.rect([qx + 182, ay2 + 34 + k * 12, 90 - k * 20, 4], fill=th["line2"], radius=2)
        dot(p, rx + rw - 46, ay2 + 36 + k * 12, 2.6, [th["orange"], th["grn"], th["blu"]][k])


for fn in (cover, hero, core_legacy, core_modern, anatomy, light, system, perform):
    fn()

if __name__ == "__main__":
    import sys
    # Emit the document as a .fg.yaml (like the other cookbook clients), so it can
    # be rendered with the FrameGraph CLI: `python -m framegraph.cli <out> --to png`.
    out = os.environ.get("OUTPUT_YAML_PATH", "itau-rio-terminal.fg.yaml")
    b.write(out, fail_on_error=True)
    print("wrote", out)

    if "--render" in sys.argv:      # optional local preview (SVG/PNG next to the yaml)
        import cairosvg
        svgs, _ = render_pages_with_stats(b.build_dict())
        for i, svg in enumerate(svgs, 1):
            cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/itau-{i}.png",
                             output_width=W, output_height=H)
        print("rendered", len(svgs), "png ->", OUT)
