"""Social-network mobile UI kit — FrameForge wireframe sheet.

One shared token set drives all 13 views; the hero and mini splash are the SAME
draw function at two scales; screens carry ids and are linked by labeled
connectors (navigation flow); dimensions + sticky notes annotate the sheet.
"""
import math
from frameforge.sdk import DocumentBuilder, rgba
from frameforge.sdk.paint import stroke

def S(w, c):
    return stroke(w, color=c)

W, H = 2880, 1400

# =========================== shared design tokens ===========================
TOK = {
    "ground":  "#F2D3AE",
    "ground2": "#F7E3C8",
    "slate":   "#3A5064",
    "slate2":  "#324557",
    "slate3":  "#2B3D4E",
    "cream":   "#F6E7CE",
    "peach":   "#EFB98A",
    "teal":    "#1F7A6D",
    "white":   "#FDF9F2",
    "ink":     "#22303C",
    "red":     "#D95440",
    "muted":   "#8FA0B0",
    "imgbg":   "#B7C1C9",
    "imgblue": "#4E7E9B",
    "line":    "#D9BE9A",
}
RAD = {"phone": 26, "screen": 16, "card": 8, "pill": 10}
SANS, SANSM, SANSSB = "Fira Sans", "Fira Sans Medium", "Fira Sans SemiBold"

def T(size, color, family=SANS, align=None, ls=None, upper=False, lh=None):
    st = {"font_family": family, "font_size": round(size * 2) / 2.0, "color": color}
    if align: st["text_align"] = align
    if ls: st["letter_spacing"] = ls
    if upper: st["text_transform"] = "uppercase"
    if lh: st["line_height"] = lh
    return st

doc = DocumentBuilder(title="Social network app - FrameForge wireframe kit", profile="diagram")
page = doc.page("sheet", canvas={"size": [W, H], "units": "px", "background": TOK["ground"]}, coordinate_mode="absolute")
bg   = page.layer("bg")
art  = page.layer("art")
anno = page.layer("anno", role="annotation")

def rr(layer, box, fill, radius=8, ow=0, oc=TOK["ink"], oid=None):
    kw = {"style": {"radius": radius}}
    if oid: kw["id"] = oid
    if ow:
        layer.rect(box, fill=fill, **S(ow, oc), **kw)
    else:
        layer.rect(box, fill=fill, **kw)

def bar(layer, x, y, w, h, c):
    rr(layer, [x, y, w, h], c, radius=h / 2.0)

# ---------------- glyph helpers (pure geometry icons) ----------------
def i_person(l, cx, cy, s, c):
    l.circle([cx, cy - s * 0.35], s * 0.32, fill=c)
    pts = [[cx + s * 0.62 * math.cos(math.radians(a)), cy + s * 0.55 + s * 0.62 * math.sin(math.radians(a))] for a in range(180, 361, 20)]
    l.polygon(pts, fill=c)

def i_heart(l, cx, cy, s, c):
    l.circle([cx - s * 0.3, cy - s * 0.2], s * 0.34, fill=c)
    l.circle([cx + s * 0.3, cy - s * 0.2], s * 0.34, fill=c)
    l.polygon([[cx - s * 0.6, cy - s * 0.05], [cx + s * 0.6, cy - s * 0.05], [cx, cy + s * 0.62]], fill=c)

def i_plus(l, cx, cy, s, c, w=2.4):
    l.line([cx - s * 0.55, cy], [cx + s * 0.55, cy], **S(w, c))
    l.line([cx, cy - s * 0.55], [cx, cy + s * 0.55], **S(w, c))

def i_search(l, cx, cy, s, c, w=2.2):
    l.circle([cx - s * 0.15, cy - s * 0.15], s * 0.4, fill="none", **S(w, c))
    l.line([cx + s * 0.18, cy + s * 0.18], [cx + s * 0.55, cy + s * 0.55], **S(w, c))

def i_menu(l, cx, cy, s, c, w=2.2):
    for dy in (-0.35, 0, 0.35):
        l.line([cx - s * 0.5, cy + s * dy], [cx + s * 0.5, cy + s * dy], **S(w, c))

def i_bell(l, cx, cy, s, c):
    pts = [[cx + s * 0.5 * math.cos(math.radians(a)), cy + s * 0.5 * math.sin(math.radians(a))] for a in range(180, 361, 20)]
    pts = [[cx - s * 0.55, cy + s * 0.35], [cx - s * 0.5, cy]] + pts + [[cx + s * 0.5, cy], [cx + s * 0.55, cy + s * 0.35]]
    l.polygon(pts, fill=c)
    l.circle([cx, cy + s * 0.5], s * 0.14, fill=c)

def i_gear(l, cx, cy, s, c):
    l.circle([cx, cy], s * 0.42, fill="none", **S(2.4, c))
    for a in range(0, 360, 60):
        l.line([cx + s * 0.42 * math.cos(math.radians(a)), cy + s * 0.42 * math.sin(math.radians(a))],
               [cx + s * 0.66 * math.cos(math.radians(a)), cy + s * 0.66 * math.sin(math.radians(a))], **S(2.4, c))

def i_mail(l, cx, cy, s, c):
    l.rect([cx - s * 0.55, cy - s * 0.38, s * 1.1, s * 0.76], fill="none", **S(2, c))
    l.polyline([[cx - s * 0.55, cy - s * 0.38], [cx, cy + s * 0.05], [cx + s * 0.55, cy - s * 0.38]], **S(2, c))

def i_logout(l, cx, cy, s, c):
    l.polyline([[cx - s * 0.1, cy - s * 0.45], [cx - s * 0.55, cy - s * 0.45], [cx - s * 0.55, cy + s * 0.45], [cx - s * 0.1, cy + s * 0.45]], **S(2.2, c))
    l.line([cx - s * 0.2, cy], [cx + s * 0.5, cy], **S(2.2, c))
    l.polygon([[cx + s * 0.5, cy], [cx + s * 0.28, cy - s * 0.16], [cx + s * 0.28, cy + s * 0.16]], fill=c)

def i_play(l, cx, cy, s, c):
    l.polygon([[cx - s * 0.3, cy - s * 0.42], [cx + s * 0.45, cy], [cx - s * 0.3, cy + s * 0.42]], fill=c)

def i_phone(l, cx, cy, s, c):
    l.circle([cx - s * 0.28, cy + s * 0.28], s * 0.16, fill=c)
    l.circle([cx + s * 0.28, cy - s * 0.28], s * 0.16, fill=c)
    l.line([cx - s * 0.28, cy + s * 0.28], [cx + s * 0.28, cy - s * 0.28], **S(s * 0.3, c))

def i_cam(l, cx, cy, s, c):
    rr(l, [cx - s * 0.55, cy - s * 0.35, s * 0.82, s * 0.7], c, radius=2)
    l.polygon([[cx + s * 0.3, cy - s * 0.12], [cx + s * 0.58, cy - s * 0.3], [cx + s * 0.58, cy + s * 0.3], [cx + s * 0.3, cy + s * 0.12]], fill=c)

def i_mic(l, cx, cy, s, c):
    rr(l, [cx - s * 0.16, cy - s * 0.5, s * 0.32, s * 0.62], c, radius=s * 0.16)
    l.polyline([[cx - s * 0.34, cy], [cx - s * 0.3, cy + s * 0.3], [cx, cy + s * 0.42], [cx + s * 0.3, cy + s * 0.3], [cx + s * 0.34, cy]], **S(1.8, c))
    l.line([cx, cy + s * 0.42], [cx, cy + s * 0.6], **S(1.8, c))

def i_pin(l, cx, cy, s, c):
    l.circle([cx, cy - s * 0.15], s * 0.32, fill=c)
    l.polygon([[cx - s * 0.26, cy], [cx + s * 0.26, cy], [cx, cy + s * 0.55]], fill=c)
    l.circle([cx, cy - s * 0.15], s * 0.12, fill=TOK["cream"])

ICONS = {"person": i_person, "heart": i_heart, "plus": i_plus, "search": i_search, "menu": i_menu,
         "bell": i_bell, "gear": i_gear, "mail": i_mail, "logout": i_logout, "play": i_play,
         "phone": i_phone, "cam": i_cam, "mic": i_mic, "pin": i_pin}

# ---------------- shared UI components ----------------
def avatar_g(l, cx, cy, r, bgc=TOK["teal"], person=TOK["cream"], ring=None):
    if ring:
        l.circle([cx, cy], r + 2.5, fill="none", **S(2.2, ring))
    l.circle([cx, cy], r, fill=bgc)
    l.circle([cx, cy - r * 0.28], r * 0.34, fill=person)
    pts = [[cx + r * 0.62 * math.cos(math.radians(a)), cy + r * 0.78 + r * 0.62 * math.sin(math.radians(a))] for a in range(180, 361, 15)]
    l.polygon(pts, fill=person)

def img_ph(l, x, y, w, h):
    rr(l, [x, y, w, h], TOK["imgbg"], radius=4)
    l.polygon([[x + w * 0.07, y + h * 0.84], [x + w * 0.36, y + h * 0.36], [x + w * 0.56, y + h * 0.66],
               [x + w * 0.7, y + h * 0.5], [x + w * 0.93, y + h * 0.84]], fill=TOK["imgblue"])
    l.circle([x + w * 0.74, y + h * 0.26], min(w, h) * 0.09, fill=TOK["peach"])

def button_w(l, x, y, w, h, label, fill=TOK["peach"], txtc=TOK["ink"], sz=8.5):
    rr(l, [x, y, w, h], fill, radius=h / 2.0)
    l.text([x, y + (h - sz) / 2.0 - 1, w, sz + 4], label, style=T(sz, txtc, SANSSB, "center", 1.2, True))

def input_f(l, x, y, w, h, ph):
    rr(l, [x, y, w, h], TOK["white"], radius=5)
    l.text([x + 10, y + (h - 7.5) / 2.0 - 1, w - 20, 11], ph, style=T(7.5, TOK["muted"]))

def toggle_w(l, x, y, on=True):
    rr(l, [x, y, 26, 13], TOK["teal"] if on else TOK["muted"], radius=6.5)
    l.circle([x + (19 if on else 7), y + 6.5], 5, fill=TOK["white"])

def logo_bubble(l, cx, cy, s, c=TOK["peach"]):
    rr(l, [cx - s * 0.75, cy - s * 0.62, s * 1.5, s * 1.1], c, radius=s * 0.42)
    l.polygon([[cx - s * 0.3, cy + s * 0.44], [cx + s * 0.05, cy + s * 0.44], [cx - s * 0.38, cy + s * 0.85]], fill=c)
    for i in (-1, 0, 1):
        l.circle([cx + i * s * 0.34, cy - s * 0.07], s * 0.11, fill=TOK["slate"])

def notif_dot(l, cx, cy, n=None, r=5.5):
    l.circle([cx, cy], r, fill=TOK["red"])
    if n:
        l.text([cx - r, cy - 4, 2 * r, 8], n, style=T(6.5, TOK["white"], SANSSB, "center"))

# ---------------- phone chrome ----------------
def status_bar(l, x, y, w, light=TOK["cream"]):
    for i in range(3):
        l.rect([x + 10 + i * 5, y + 8 - i * 2.4, 3.4, 4 + i * 2.4], fill=light)
    l.text([x, y + 2, w, 10], "10:30 AM", style=T(7, light, SANSM, "center", 0.6))
    l.text([x + w - 62, y + 2.5, 34, 9], "100%", style=T(6.5, light, SANS, "right"))
    rr(l, [x + w - 26, y + 3.5, 16, 8], "none", radius=2, ow=1.2, oc=light)
    l.rect([x + w - 24.4, y + 5.1, (16 - 3.2) * 0.9, 4.8], fill=light)
    l.rect([x + w - 9, y + 5.5, 2, 4], fill=light)

def bottom_nav(l, x, y, w, active=None):
    rr(l, [x, y, w, 34], TOK["slate3"], radius=0)
    names = ["person", "heart", "plus", "search", "menu"]
    step = w / 5.0
    for i, nm in enumerate(names):
        c = TOK["peach"] if nm == active else TOK["cream"]
        ICONS[nm](l, x + step * (i + 0.5), y + 17, 9, c)

SCREENS = {}

def screen(sid, x, y, w, h, nav=None):
    art.rect([x - 5, y - 5, w + 10, h + 10], fill=TOK["ground2"], style={"radius": RAD["screen"] + 5})
    rr(art, [x, y, w, h], TOK["slate"], radius=RAD["screen"], ow=2.5, oc=TOK["ink"], oid=sid)
    status_bar(art, x, y + 2, w)
    if nav is not None:
        bottom_nav(art, x + 2, y + h - 36, w - 4, active=nav)
    SCREENS[sid] = [x, y, w, h]
    return [x + 14, y + 26, w - 28, h - (70 if nav is not None else 40)]

# =========================== screen content builders ===========================
def draw_splash(l, b, s=1.0, hero=False):
    x, y, w, h = b
    cx = x + w / 2.0
    logo_bubble(l, cx, y + h * (0.30 if hero else 0.34), 46 * s)
    l.text([x, y + h * (0.10 if hero else 0.08), w, 30 * s], "Social Network",
           style=T(19 * s, TOK["cream"], SANSSB, "center"))
    l.text([x, y + h * 0.52, w, 16 * s], "mobile app", style=T(11 * s, TOK["peach"], SANSM, "center", 1.5))
    l.text([x + w * 0.1, y + h * 0.62, w * 0.8, 30 * s],
           "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor",
           style=T(6.8 * s, TOK["muted"], SANS, "center", None, False, 1.4))
    button_w(l, x + w * 0.16, y + h * 0.82, w * 0.68, 24 * s, "Get started", sz=8 * s)

def draw_signup(l, b):
    x, y, w, h = b
    rr(l, [x - 14, y + 6, w + 28, 44], TOK["cream"], radius=0)
    l.text([x, y + 14, w, 26], "Lorem ipsum dolor sit amet", style=T(10.5, TOK["ink"], SANSSB, "center", None, False, 1.25))
    fy = y + 70
    for ph in ["Lorem Name", "Lorem Name", "Lorem Number", "Password"]:
        input_f(l, x + 8, fy, w - 16, 28, ph)
        fy += 42
    toggle_w(l, x + 8, fy + 4, on=True)
    l.text([x + 42, fy + 3, w - 50, 16], "Lorem ipsum dolor sit amet, consectetuer", style=T(6, TOK["muted"], SANS, None, None, False, 1.3))
    button_w(l, x + w * 0.18, fy + 34, w * 0.64, 28, "Sign up")
    l.text([x, fy + 78, w, 10], "or continue with", style=T(6.5, TOK["muted"], SANS, "center"))
    for i in range(3):
        cxx = x + w / 2.0 + (i - 1) * 44
        l.circle([cxx, fy + 110], 13, fill="none", **S(1.5, TOK["peach"]))
        l.circle([cxx, fy + 110], 5, fill=TOK["peach"])
    l.text([x, y + h - 14, w, 10], "Lorem ipsum dolor sit amet adipiscing", style=T(6, TOK["muted"], SANS, "center"))

def draw_profile(l, b):
    x, y, w, h = b
    avatar_g(l, x + 26, y + 26, 20, ring=TOK["peach"])
    l.text([x + 56, y + 12, w - 60, 12], "Lorem Name", style=T(9.5, TOK["cream"], SANSSB))
    bar(l, x + 56, y + 28, 70, 4, TOK["muted"])
    bar(l, x + 56, y + 38, 96, 4, rgba(TOK["muted"], 0.6))
    button_w(l, x + 4, y + 58, w * 0.42, 20, "Edit", fill=TOK["peach"], sz=7)
    button_w(l, x + w * 0.52, y + 58, w * 0.44, 20, "Lorem", fill=TOK["teal"], txtc=TOK["cream"], sz=7)
    rows = [("mail", "Lorem ipsum", "1"), ("bell", "Dolor sit", "3"), ("person", "Amet lorem", None),
            ("heart", "Ipsum dolor", None), ("gear", "Sit amet", None), ("logout", "Log out", None)]
    ry = y + 96
    for ic, lab, n in rows:
        ICONS[ic](l, x + 16, ry + 9, 7.5, TOK["peach"])
        l.text([x + 34, ry + 3, w - 80, 11], lab, style=T(8, TOK["cream"], SANSM))
        if n:
            notif_dot(l, x + w - 16, ry + 9, n)
        l.line([x + 4, ry + 24], [x + w - 4, ry + 24], **S(0.8, rgba(TOK["muted"], 0.35)))
        ry += 36
    l.text([x, y + h - 14, w, 9], "v2.0.0 · Lorem ipsum", style=T(6, TOK["muted"], SANS, "center"))

def draw_messages(l, b):
    x, y, w, h = b
    l.text([x, y + 6, w, 12], "Messages", style=T(10, TOK["cream"], SANSSB))
    cols = [TOK["peach"], TOK["red"], TOK["teal"], "#7B5EA6"]
    for i, c in enumerate(cols):
        cxx = x + 24 + i * (w - 46) / 3.0
        avatar_g(l, cxx, y + 40, 14, bgc=c, ring=TOK["peach"])
        l.text([cxx - 22, y + 58, 44, 8], "Lorem N.", style=T(5.8, TOK["muted"], SANS, "center"))
    l.line([x, y + 74], [x + w, y + 74], **S(1, rgba(TOK["muted"], 0.4)))
    l.text([x + 4, y + 80, w * 0.5, 10], "Lorem Name", style=T(7.5, TOK["cream"], SANSSB))
    l.text([x + w * 0.5, y + 80, w * 0.5 - 4, 10], "Lorem Nams", style=T(7.5, TOK["peach"], SANSM, "right"))
    ry = y + 98
    times = ["5:06", "5:06", "2:30", "1:12", "Mon"]
    cols2 = [TOK["teal"], "#7B5EA6", TOK["peach"], TOK["teal"], "#7B5EA6"]
    for i in range(5):
        avatar_g(l, x + 18, ry + 13, 13, bgc=cols2[i])
        l.text([x + 40, ry + 2, w - 100, 10], "Lorem Name", style=T(8, TOK["cream"], SANSSB))
        bar(l, x + 40, ry + 16, w - 110, 3.5, rgba(TOK["muted"], 0.75))
        l.text([x + w - 34, ry + 3, 30, 9], times[i], style=T(6.2, TOK["muted"], SANS, "right"))
        if i in (0, 3):
            notif_dot(l, x + w - 12, ry + 16, None, 4)
        l.line([x + 4, ry + 32], [x + w - 4, ry + 32], **S(0.8, rgba(TOK["muted"], 0.3)))
        ry += 42

def draw_chat(l, b):
    x, y, w, h = b
    avatar_g(l, x + 16, y + 14, 12)
    l.text([x + 34, y + 4, w - 40, 10], "Lorem Name", style=T(8.5, TOK["cream"], SANSSB))
    bar(l, x + 34, y + 18, 56, 3.5, TOK["muted"])
    l.line([x, y + 30], [x + w, y + 30], **S(1, rgba(TOK["muted"], 0.4)))
    def bubble(bx, by, bw, bh, mine):
        rr(l, [bx, by, bw, bh], TOK["teal"] if mine else TOK["cream"], radius=7)
        for i in range(max(1, int(bh // 12))):
            bar(l, bx + 8, by + 7 + i * 9, bw - 16 - (6 if i else 0), 3.2, rgba(TOK["cream"], 0.75) if mine else "#9AA8B5")
    bubble(x + 4, y + 44, w * 0.58, 30, False)
    l.text([x, y + 84, w, 8], "11:15 Today", style=T(5.8, TOK["muted"], SANS, "center"))
    bubble(x + w * 0.38 - 4, y + 100, w * 0.62, 22, True)
    bubble(x + 4, y + 132, w * 0.5, 22, False)
    bubble(x + w * 0.3 - 4, y + 164, w * 0.7, 40, True)
    avatar_g(l, x + 12, y + 174, 10, bgc="#7B5EA6")
    bubble(x + 4, y + 216, w * 0.55, 28, False)
    bubble(x + w * 0.42 - 4, y + 254, w * 0.58, 22, True)
    l.text([x, y + 288, w, 8], "11:42", style=T(5.8, TOK["muted"], SANS, "center"))
    rr(l, [x + 4, y + h - 24, w - 34, 20], TOK["white"], radius=10)
    l.text([x + 14, y + h - 18.5, w - 52, 9], "Type the text...", style=T(6.8, TOK["muted"]))
    l.circle([x + w - 14, y + h - 14], 10, fill=TOK["peach"])
    l.polygon([[x + w - 18, y + h - 19], [x + w - 8, y + h - 14], [x + w - 18, y + h - 9]], fill=TOK["ink"])

def draw_contacts(l, b):
    x, y, w, h = b
    rr(l, [x + 4, y + 6, w - 8, 22], TOK["white"], radius=11)
    l.text([x + 16, y + 11, w - 50, 10], "Search...", style=T(7, TOK["muted"]))
    i_search(l, x + w - 22, y + 17, 6, TOK["muted"])
    hdr = ["Lorem", "Ipsum", "Dolor"]
    for i, hh in enumerate(hdr):
        l.text([x + 8 + i * (w - 16) / 3.0, y + 36, (w - 16) / 3.0, 9], hh + "  v", style=T(6.5, TOK["peach"], SANSSB, None, 0.8, True))
    l.line([x, y + 50], [x + w, y + 50], **S(1, rgba(TOK["muted"], 0.4)))
    ry = y + 58
    for i in range(6):
        avatar_g(l, x + 18, ry + 15, 13, bgc=[TOK["teal"], TOK["peach"], "#7B5EA6", TOK["teal"], TOK["peach"], "#7B5EA6"][i])
        l.text([x + 40, ry + 2, w - 100, 10], "Lorem Name", style=T(8, TOK["cream"], SANSSB))
        l.text([x + 40, ry + 15, w - 110, 8], "22 y.o.", style=T(6, TOK["muted"]))
        i_mail(l, x + w - 42, ry + 10, 6, TOK["peach"])
        i_person(l, x + w - 20, ry + 10, 6, TOK["peach"])
        i_plus(l, x + w - 12, ry + 7, 3, TOK["peach"], 1.4)
        if i == 0:
            notif_dot(l, x + w - 34, ry + 3, None, 3.5)
        l.line([x + 4, ry + 32], [x + w - 4, ry + 32], **S(0.8, rgba(TOK["muted"], 0.3)))
        ry += 40

def draw_feed(l, b):
    x, y, w, h = b
    def post_head(py, name="Dolor Sit", verb="posted new photo"):
        avatar_g(l, x + 14, py + 10, 10, bgc=TOK["teal"])
        l.text([x + 30, py + 2, w - 36, 9], name, style=T(7.5, TOK["cream"], SANSSB))
        l.text([x + 30, py + 12, w - 36, 8], verb, style=T(5.8, TOK["muted"]))
    post_head(y + 6)
    img_ph(l, x + 4, y + 28, w * 0.46, 52)
    for i in range(5):
        bar(l, x + w * 0.5 + 4, y + 32 + i * 9, w * 0.46 - (8 if i % 2 else 0), 3.2, rgba(TOK["muted"], 0.8))
    l.line([x, y + 92], [x + w, y + 92], **S(1, rgba(TOK["muted"], 0.35)))
    post_head(y + 100, verb="added new friends")
    avatar_g(l, x + 24, y + 138, 13, bgc=TOK["peach"])
    avatar_g(l, x + 58, y + 138, 13, bgc="#7B5EA6")
    notif_dot(l, x + 70, y + 128, None, 4.5)
    l.text([x + 12, y + 154, 40, 8], "Dolor Sit", style=T(5.8, TOK["muted"], SANS, "center"))
    l.text([x + 44, y + 154, 40, 8], "Dolor Sit", style=T(5.8, TOK["muted"], SANS, "center"))
    l.line([x, y + 168], [x + w, y + 168], **S(1, rgba(TOK["muted"], 0.35)))
    post_head(y + 176, verb="posted new video")
    img_ph(l, x + 4, y + 198, w * 0.46, 52)
    l.circle([x + 4 + w * 0.23, y + 224], 12, fill=TOK["white"])
    i_play(l, x + 6 + w * 0.23, y + 224, 8, TOK["red"])
    for i in range(5):
        bar(l, x + w * 0.5 + 4, y + 202 + i * 9, w * 0.46 - (10 if i % 2 else 0), 3.2, rgba(TOK["muted"], 0.8))

def draw_profile_grid(l, b):
    x, y, w, h = b
    avatar_g(l, x + w / 2.0, y + 20, 16, ring=TOK["peach"])
    l.text([x, y + 40, w, 11], "Lorem ipsum", style=T(9.5, TOK["cream"], SANSSB, "center"))
    i_pin(l, x + w * 0.36, y + 58, 5, TOK["peach"])
    l.text([x + w * 0.42, y + 53, 60, 9], "Dolor sit", style=T(6.5, TOK["muted"]))
    stats = [("56", "Lorem"), ("104", "Ipsum"), ("32", "Dolor")]
    for i, (n, lab) in enumerate(stats):
        sx = x + 14 + i * (w - 28) / 3.0
        l.text([sx, y + 68, (w - 28) / 3.0, 12], n, style=T(10, TOK["peach"], SANSSB, "center"))
        l.text([sx, y + 82, (w - 28) / 3.0, 8], lab, style=T(5.8, TOK["muted"], SANS, "center", 0.8, True))
    button_w(l, x + 14, y + 94, w * 0.4 - 14, 16, "Lorem ipsum", fill=TOK["peach"], sz=5.5)
    button_w(l, x + w * 0.48, y + 94, w * 0.4 - 6, 16, "Lorem ipsum", fill=TOK["teal"], txtc=TOK["cream"], sz=5.5)
    tabs = ["Lorem", "Ipsum", "Dolor"]
    for i, tb in enumerate(tabs):
        tx = x + 4 + i * (w - 8) / 3.0
        l.text([tx, y + 120, (w - 8) / 3.0, 9], tb, style=T(6.5, TOK["peach"] if i == 0 else TOK["muted"], SANSM, "center", 1, True))
    l.line([x + 4, y + 133], [x + 4 + (w - 8) / 3.0, y + 133], **S(2, TOK["peach"]))
    gy = y + 140
    cell = (w - 8 - 8) / 3.0
    for r in range(3):
        for c in range(3):
            img_ph(l, x + 4 + c * (cell + 4), gy + r * (cell * 0.72 + 4), cell, cell * 0.72)

def draw_groups(l, b):
    x, y, w, h = b
    l.text([x, y + 4, w, 12], "Groups", style=T(10, TOK["cream"], SANSSB))
    rr(l, [x + 4, y + 22, w - 8, 20], TOK["white"], radius=10)
    l.text([x + 14, y + 27, w - 40, 9], "Search...", style=T(6.8, TOK["muted"]))
    i_search(l, x + w - 20, y + 32, 5.5, TOK["muted"])
    l.text([x + 4, y + 52, w, 10], "Popular Groups", style=T(7.5, TOK["cream"], SANSSB))
    cw = (w - 8 - 10) / 2.0
    gy = y + 68
    for r in range(2):
        for c in range(2):
            gx = x + 4 + c * (cw + 10)
            gyy = gy + r * (cw * 1.12 + 12)
            rr(l, [gx, gyy, cw, cw * 1.12], TOK["slate2"], radius=8, ow=1, oc=rgba(TOK["muted"], 0.4))
            img_ph(l, gx + 8, gyy + 8, cw - 16, cw * 0.58)
            l.text([gx, gyy + cw * 0.72, cw, 9], "Lorem Name", style=T(6.8, TOK["cream"], SANSSB, "center"))
            l.text([gx, gyy + cw * 0.72 + 12, cw, 8], "2k members", style=T(5.5, TOK["muted"], SANS, "center"))
    button_w(l, x + w * 0.24, gy + 2 * (cw * 1.12 + 12) + 8, w * 0.52, 22, "See all", fill=TOK["teal"], txtc=TOK["cream"], sz=7)

def draw_post(l, b):
    x, y, w, h = b
    avatar_g(l, x + 14, y + 12, 11, ring=TOK["peach"])
    l.text([x + 32, y + 3, w - 40, 9], "Lorem ipsum", style=T(8, TOK["cream"], SANSSB))
    l.text([x + 32, y + 14, w - 40, 8], "Lorem ipsum dolor sit amet", style=T(5.8, TOK["muted"]))
    img_ph(l, x + 4, y + 32, w - 8, h * 0.5)
    ay = y + 40 + h * 0.5
    i_heart(l, x + 14, ay, 7, TOK["red"])
    l.text([x + 24, ay - 5, 24, 9], "14", style=T(7, TOK["cream"], SANSM))
    i_mail(l, x + 54, ay, 6.5, TOK["cream"])
    l.text([x + 66, ay - 5, 20, 9], "2", style=T(7, TOK["cream"], SANSM))
    i_menu(l, x + w - 22, ay, 6.5, TOK["peach"])
    avatar_g(l, x + 14, ay + 24, 10, bgc="#7B5EA6")
    l.text([x + 30, ay + 15, w - 36, 9], "Dolor Sit", style=T(7, TOK["cream"], SANSSB))
    rr(l, [x + 4, ay + 34, w - 8, 26], TOK["cream"], radius=6)
    l.text([x + 12, ay + 39, w - 60, 9], "Lorem ipsum dolor sit amet, elit, sed", style=T(6, TOK["slate"]))
    for i in range(3):
        i_heart(l, x + 14 + i * 11, ay + 53, 4, TOK["red"])
    avatar_g(l, x + 14, ay + 76, 10, bgc=TOK["teal"])
    bar(l, x + 30, ay + 70, w - 60, 3.2, rgba(TOK["muted"], 0.8))
    bar(l, x + 30, ay + 78, w - 90, 3.2, rgba(TOK["muted"], 0.6))

def draw_settings(l, b):
    x, y, w, h = b
    rows = [("Lorem ipsum", True), ("Dolor sit amet", False), ("Consectetuer adipiscing", True),
            ("Lorem ipsum", False), ("Sed do eiusmod", True)]
    ry = y + 8
    for lab, on in rows:
        l.text([x + 6, ry, w - 60, 10], lab, style=T(7.5, TOK["cream"], SANSSB))
        bar(l, x + 6, ry + 12, w - 80, 3, rgba(TOK["muted"], 0.7))
        bar(l, x + 6, ry + 19, w - 96, 3, rgba(TOK["muted"], 0.5))
        toggle_w(l, x + w - 34, ry + 4, on)
        l.line([x + 2, ry + 36], [x + w - 2, ry + 36], **S(0.8, rgba(TOK["muted"], 0.3)))
        ry += 46
    button_w(l, x + w * 0.2, ry + 8, w * 0.6, 24, "Sign up")
    l.text([x, ry + 40, w, 16], "Lorem ipsum dolor sit amet consectetuer adipiscing", style=T(5.8, TOK["muted"], SANS, "center", None, False, 1.35))

def draw_call(l, b):
    x, y, w, h = b
    l.text([x, y + 14, w, 14], "Lorem Ipsum", style=T(12, TOK["cream"], SANSSB, "center"))
    l.text([x, y + 32, w, 10], "incoming call...", style=T(7.5, TOK["peach"], SANSM, "center", 1))
    l.circle([x + w / 2.0, y + h * 0.4, ], 40, fill="none", **S(2, rgba(TOK["peach"], 0.5)))
    avatar_g(l, x + w / 2.0, y + h * 0.4, 34, bgc=TOK["peach"], person=TOK["slate"])
    bx = x + w / 2.0
    by = y + h * 0.66
    for i, (ic, c) in enumerate([("mic", TOK["peach"]), ("plus", TOK["peach"]), ("phone", TOK["peach"])]):
        cxx = bx + (i - 1) * 44
        l.circle([cxx, by], 16, fill=c)
        ICONS[ic](l, cxx, by, 8, TOK["slate"])
    l.text([x + w * 0.08, y + h * 0.78, w * 0.84, 30],
           "Lorem ipsum dolor sit labore do consectetur adipiscing elit sed do tempor incididunt ut al dolor magna",
           style=T(6, TOK["muted"], SANS, "center", None, False, 1.4))

# =========================== sheet layout ===========================
# corner tag
bg.polygon([[0, 0], [120, 0], [0, 120]], fill=TOK["peach"])
bg.text([8, 34, 96, 14], "FF UI KIT", style=T(10, TOK["ink"], SANSSB, None, 1.5, True))

# ---- hero phone (shares draw_splash with the mini) ----
HX, HY, HW, HH = 130, 130, 430, 880
art.rect([HX + 14, HY + 20, HW, HH], fill=rgba("#B98A5E", 0.35), style={"radius": 40})
rr(art, [HX, HY, HW, HH], "#1E2A35", radius=40, ow=3, oc=TOK["ink"], oid="scr-hero")
for i in range(2):
    art.rect([HX - 4, HY + 180 + i * 70, 4, 44], fill="#1E2A35")
rr(art, [HX + 16, HY + 16, HW - 32, HH - 32], TOK["slate"], radius=26)
rr(art, [HX + HW / 2 - 40, HY + 26, 80, 8], "#141C24", radius=4)
art.circle([HX + HW / 2 + 56, HY + 30], 4, fill="#141C24")
status_bar(art, HX + 24, HY + 40, HW - 48)
draw_splash(art, [HX + 40, HY + 90, HW - 80, HH - 160], s=1.7, hero=True)

# ---- 12 mini screens ----
GRID = [
    ("splash",   "01 · Splash",        draw_splash,      None),
    ("signup",   "02 · Sign up",       draw_signup,      None),
    ("profile",  "03 · Profile menu",  draw_profile,     "person"),
    ("messages", "04 · Messages",      draw_messages,    "heart"),
    ("chat",     "05 · Chat",          draw_chat,        "heart"),
    ("contacts", "06 · Contacts",      draw_contacts,    "search"),
    ("feed",     "07 · Feed",          draw_feed,        "person"),
    ("grid",     "08 · Profile grid",  draw_profile_grid,"person"),
    ("groups",   "09 · Groups",        draw_groups,      "search"),
    ("post",     "10 · Post detail",   draw_post,        "heart"),
    ("settings", "11 · Settings",      draw_settings,    "menu"),
    ("call",     "12 · Incoming call", draw_call,        None),
]
SW, SH, GX0, GAPX = 300, 580, 640, 52
ROWY = [110, 745]
for idx, (key, label, fn, nav) in enumerate(GRID):
    col, row = idx % 6, idx // 6
    sx = GX0 + col * (SW + GAPX)
    sy = ROWY[row]
    body = screen("scr-" + key, sx, sy, SW, SH, nav=nav)
    if fn is draw_splash:
        fn(art, body, s=0.95)
    else:
        fn(art, body)
    anno.text([sx, sy + SH + 14, SW, 12], label, style=T(9, "#7A5A38", SANSSB, "center", 1.6, True))

# =========================== annotations ===========================
def sticky(x, y, w, h, text, ang=-3):
    ptn, qn = (lambda a: (None, None))(0)
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    def rot(px, py):
        return [x + (px * ca - py * sa), y + (px * sa + py * ca)]
    anno.polygon([rot(0, 0), rot(w, 0), rot(w, h - 12), rot(w - 12, h), rot(0, h)], fill="#F2E29B", **S(1.5, "#C9B36A"))
    anno.polygon([rot(w - 12, h), rot(w, h - 12), rot(w - 12, h - 12)], fill="#D9C87E")
    anno.text([x + 10, y + 8, w - 20, h - 16], text, style=T(8.5, "#5A4A22", SANSM, None, None, False, 1.35))

sticky(600, 30, 300, 56, "One token set drives every view: palette, type scale, radii, chrome.")
sticky(2470, 30, 290, 56, "Screens are linked objects — connectors trace the navigation flow.", 2)

def dim_annot(x1, y1, x2, y2, label):
    anno.line([x1, y1 - 6], [x1, y1 + 6], **S(1.5, "#7A5A38"))
    anno.line([x2, y2 - 6], [x2, y2 + 6], **S(1.5, "#7A5A38"))
    anno.line([x1, y1], [x2, y2], **S(1.2, "#7A5A38"))
    anno.text([min(x1, x2), y1 - 18, abs(x2 - x1), 12], label, style=T(8.5, "#7A5A38", SANSM, "center"))

dim_annot(HX, HY + HH + 46, HX + HW, HY + HH + 46, "430 px")
dim_annot(GX0 + SW + GAPX, 82, GX0 + 2 * SW + GAPX, 82, "300 px")

# =========================== link navigation (connectors) ===========================
def flow(a, b, label, color=TOK["teal"], route=None):
    try:
        kw = {"label": label, "arrow_end": True}
        if route:
            kw["route"] = route
        page.connector({"ref": "scr-" + a, "side": "right"}, {"ref": "scr-" + b, "side": "left"}, **S(2.4, color), **kw)
        return
    except Exception:
        pass
    ax, ay, aw, ah = SCREENS["scr-" + a]
    bx, by, bw, bh = SCREENS["scr-" + b]
    p1 = [ax + aw + 6, ay + ah / 2.0]
    p2 = [bx - 6, by + bh / 2.0]
    anno.line(p1, p2, **S(2.4, color))
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    L = 8
    anno.polygon([[p2[0], p2[1]],
                  [p2[0] + L * math.cos(ang + 2.6), p2[1] + L * math.sin(ang + 2.6)],
                  [p2[0] + L * math.cos(ang - 2.6), p2[1] + L * math.sin(ang - 2.6)]], fill=color)
    mx, my = (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0
    anno.text([mx - 40, my - 16, 80, 11], label, style=T(7.5, color, SANSSB, "center", 0.8, True))

flow("splash", "signup", "start")
flow("signup", "profile", "create")
flow("messages", "chat", "open")
flow("groups", "post", "open")
flow("settings", "call", "ring")

# hero -> first mini (routed link)
try:
    page.connector({"ref": "scr-hero", "side": "right"}, {"ref": "scr-splash", "side": "left"},
                   label="1:1 shared view", arrow_end=True, **S(2.4, "#B4713F"))
except Exception:
    hx2 = HX + HW + 6
    anno.line([hx2, HY + 200], [GX0 - 8, ROWY[0] + 290], **S(2.4, "#B4713F"))
    anno.polygon([[GX0 - 6, ROWY[0] + 290], [GX0 - 16, ROWY[0] + 284], [GX0 - 16, ROWY[0] + 296]], fill="#B4713F")
    anno.text([hx2 + 6, HY + 176, 120, 12], "1:1 shared view", style=T(7.5, "#B4713F", SANSSB, None, 0.8, True))

# =========================== token legend ===========================
LGX, LGY, LGW, LGH = 130, 1080, 430, 250
rr(anno, [LGX, LGY, LGW, LGH], TOK["ground2"], radius=12, ow=1.5, oc=TOK["line"])
anno.text([LGX + 18, LGY + 14, LGW - 36, 14], "Shared design tokens", style=T(11, "#7A5A38", SANSSB, None, 1.4, True))
swatches = [("slate", "3A5064"), ("cream", "F6E7CE"), ("peach", "EFB98A"), ("teal", "1F7A6D"), ("red", "D95440"), ("ink", "22303C")]
for i, (name, hexv) in enumerate(swatches):
    sx = LGX + 18 + i * 68
    rr(anno, [sx, LGY + 40, 26, 26], TOK[name], radius=6, ow=1, oc=rgba(TOK["ink"], 0.3))
    anno.text([sx - 8, LGY + 70, 44, 9], name, style=T(7, "#7A5A38", SANSM, "center"))
    anno.text([sx - 8, LGY + 80, 44, 8], hexv, style=T(6, "#A5814F", SANS, "center"))
anno.text([LGX + 18, LGY + 100, 200, 22], "Aa 19 — Heading", style=T(13, TOK["ink"], SANSSB))
anno.text([LGX + 18, LGY + 126, 200, 14], "Aa 9 — Body / labels", style=T(9, TOK["ink"], SANS))
anno.text([LGX + 18, LGY + 144, 200, 12], "Aa 7 — Captions, meta", style=T(7, "#7A5A38", SANS))
button_w(anno, LGX + 250, LGY + 104, 130, 24, "Button")
toggle_w(anno, LGX + 250, LGY + 140, True)
toggle_w(anno, LGX + 286, LGY + 140, False)
avatar_g(anno, LGX + 348, LGY + 146, 13)
notif_dot(anno, LGX + 380, LGY + 140, "3")
anno.text([LGX + 18, LGY + 172, LGW - 36, 60],
          "Radii: phone 26 · screen 16 · card 8 · pill 10.  Chrome (status bar, bottom nav), avatars, "
          "placeholders and buttons are single helpers reused by all thirteen views.",
          style=T(7.5, "#7A5A38", SANS, None, None, False, 1.45))

# footer
anno.text([W - 700, H - 36, 640, 14],
          "FrameForge wireframe — 13 linked views · shared tokens · connector navigation · generated with the SDK",
          style=T(9, "#7A5A38", SANSM, "right"))

doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
