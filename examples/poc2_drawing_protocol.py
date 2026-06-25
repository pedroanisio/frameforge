"""POC-02 — feasibility experiment for the layered drawing protocol.

Tests the three load-bearing claims with REAL execution, not prose:
  1. perspective-as-math : one 3D construction, projected through different cameras
  2. style-as-grammar    : the same construction re-skinned by a StyleProfile
  3. measurable gate     : detect + auto-correct a proportion defect numerically

A tiny 3D vector engine (pinhole projection + painter's sort + lambert shading)
drives a blocky mascot built in head-units. Rendered through FrameGraph's own
engine. Output: a cameras x styles matrix + a gate before/after panel.
"""
import copy
import math
import sys
import os
sys.path.insert(0, os.environ.get("FG_ROOT", "."))
from framegraph.sdk import DocumentBuilder, render_page_svgs

# ---------- tiny 3D ---------------------------------------------------------- #
def roty(p, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return (x * c + z * s, y, -x * s + z * c)

def rotx(p, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return (x, y * c - z * s, y * s + z * c)

def project(p, cam):
    p = rotx(roty(p, cam["yaw"]), cam["pitch"])
    x, y, z = p[0], p[1], p[2] + cam["dist"]
    z = max(0.05, z)
    f = cam["f"]
    return (cam["cx"] + cam["s"] * f * x / z, cam["cy"] + cam["s"] * f * y / z), z

def nrot(n, cam):  # rotate a normal the same way (no translation)
    return rotx(roty(n, cam["yaw"]), cam["pitch"])

# ---------- colour ---------------------------------------------------------- #
def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
def hs(t): return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in t)
def lerp(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
def shade(base, f, lo=0.45, hi=1.18):
    b = hx(base)
    if f < 0.5:
        return hs(lerp([v * lo for v in b], b, f / 0.5))
    return hs(lerp(b, [min(255, v * hi) for v in b], (f - 0.5) / 0.5))

# ---------- construction (a blocky mascot, in head-units) ------------------- #
# Each part: (center, half-size, palette-role). Head is 1.0 unit tall by design.
def build_mascot(head_scale=1.0):
    H = 1.0
    return [
        ((0, -2.3 * H, 0), (0.55 * H * head_scale, 0.55 * H * head_scale, 0.5 * H * head_scale), "head"),
        ((0, -1.0 * H, 0), (0.85 * H, 0.95 * H, 0.55 * H), "body"),
        ((-1.15 * H, -1.05 * H, 0), (0.28 * H, 0.8 * H, 0.28 * H), "limb"),
        ((1.15 * H, -1.05 * H, 0), (0.28 * H, 0.8 * H, 0.28 * H), "limb"),
        ((-0.45 * H, 0.55 * H, 0), (0.32 * H, 0.75 * H, 0.32 * H), "limb"),
        ((0.45 * H, 0.55 * H, 0), (0.32 * H, 0.75 * H, 0.32 * H), "limb"),
    ]

# box -> 6 faces (corners CCW) + outward normal
def box_faces(center, hs_):
    cx, cy, cz = center
    hx_, hy_, hz_ = hs_
    c = [(cx + sx * hx_, cy + sy * hy_, cz + sz * hz_)
         for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    # index: bit0=x,bit1=y,bit2=z
    def idx(x, y, z):
        return x * 4 + y * 2 + z
    faces = [
        ([idx(1,0,0), idx(1,1,0), idx(1,1,1), idx(1,0,1)], (1, 0, 0)),
        ([idx(0,0,0), idx(0,0,1), idx(0,1,1), idx(0,1,0)], (-1, 0, 0)),
        ([idx(0,1,0), idx(0,1,1), idx(1,1,1), idx(1,1,0)], (0, 1, 0)),
        ([idx(0,0,0), idx(1,0,0), idx(1,0,1), idx(0,0,1)], (0, -1, 0)),
        ([idx(0,0,1), idx(1,0,1), idx(1,1,1), idx(0,1,1)], (0, 0, 1)),
        ([idx(0,0,0), idx(0,1,0), idx(1,1,0), idx(1,0,0)], (0, 0, -1)),
    ]
    return [([c[i] for i in f], n) for f, n in faces]

PALETTE = {"head": "#8B5CF6", "body": "#6D28D9", "limb": "#22D3EE"}
LIGHT = (-0.5, -0.7, 0.5)
LN = math.sqrt(sum(v * v for v in LIGHT))
LIGHT = tuple(v / LN for v in LIGHT)

# ---------- render one mascot into a layer, given camera + style ------------ #
def draw_mascot(L, parts, cam, style):
    polys = []  # (avgdepth, points2d, role, normal_rot)
    for center, hsz, role in parts:
        for corners, n in box_faces(center, hsz):
            pts = []
            zsum = 0
            for p in corners:
                (sx, sy), z = project(p, cam)
                pts.append([sx, sy])
                zsum += z
            polys.append((zsum / 4, pts, role, nrot(n, cam)))
    polys.sort(key=lambda t: -t[0])  # painter's: far first
    for _, pts, role, n in polys:
        nn = math.sqrt(sum(v * v for v in n)) or 1
        lam = max(0.0, sum((n[i] / nn) * LIGHT[i] for i in range(3)))
        base = PALETTE[role]
        if style["mode"] == "cel":
            f = 0.35 if lam < 0.35 else (0.62 if lam < 0.75 else 0.95)
            L.polygon(pts, fill=shade(base, f),
                      **({} if style["line"] == 0 else
                         {"stroke": style["ink"], "stroke_style": {"stroke_width": style["line"]}}))
        elif style["mode"] == "soft":
            L.polygon(pts, fill=shade(base, 0.3 + 0.7 * lam))
        elif style["mode"] == "blueprint":
            L.add({"type": "polygon", "points": pts, "fill": style["bg"],
                   "stroke": style["ink"], "stroke_style": {"stroke_width": style["line"]},
                   "opacity": 0.5})

# ---------- the measurable gate --------------------------------------------- #
def measure_head_units(parts, cam):
    """Projected total-height / projected head-height = stylization head-units."""
    ys, head_ys = [], []
    for center, hsz, role in parts:
        for corners, _ in box_faces(center, hsz):
            for p in corners:
                (sx, sy), _ = project(p, cam)
                ys.append(sy)
                if role == "head":
                    head_ys.append(sy)
    total = max(ys) - min(ys)
    head = max(head_ys) - min(head_ys)
    return total / head if head else 0.0

def gate_fix_proportion(parts, cam, target_units, tol=0.12, max_iter=6):
    """Iterate to a fixed point: head-units is a COUPLED metric (the head is part of
    the total height), so a single proportional fix under-converges. The protocol's
    'refine until the checklist passes' is therefore load-bearing, not optional."""
    cur = copy.deepcopy(parts)
    obs0 = measure_head_units(cur, cam)
    history = [obs0]
    iters = 0
    while iters < max_iter:
        obs = measure_head_units(cur, cam)
        if abs(obs - target_units) <= tol:
            break
        factor = obs / target_units            # head too big -> obs<target -> factor<1 -> shrink
        for i, (c, hsz, role) in enumerate(cur):
            if role == "head":
                cur[i] = (c, (hsz[0] * factor, hsz[1] * factor, hsz[2] * factor), role)
        iters += 1
        history.append(measure_head_units(cur, cam))
    final = measure_head_units(cur, cam)
    return cur, obs0, final, history, abs(final - target_units) <= tol

# ---------- styles & cameras ------------------------------------------------ #
STYLES = {
    "flat-cel": {"mode": "cel", "line": 2.0, "ink": "#241B4A"},
    "blueprint": {"mode": "blueprint", "line": 1.6, "ink": "#7DE3FF", "bg": "#0B2A6B"},
}
def cam(cx, cy, yaw, pitch, s=1.0):
    return {"cx": cx, "cy": cy, "yaw": math.radians(yaw), "pitch": math.radians(pitch),
            "dist": 9.0, "f": 6.0, "s": s * 32}
CAMERAS = {"three-quarter": (35, -12), "low-angle": (18, 22), "top-down": (8, 60)}

W, H = 1280, 880

def txt(s, sz, col, **k):
    return {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": sz,
            "font_weight": 700, "color": col, **k}

b = DocumentBuilder(title="POC-02 drawing protocol feasibility", profile="deck")

# ---- Page 1: cameras x styles matrix from ONE construction ----------------- #
p = b.page("matrix", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
L = p.layer("main")
L.rect([0, 0, W, H], fill="#F5F4FB")
L.text([40, 28, 1200, 30], "POC-02 — one 3D construction → any camera × any style",
        style=txt("x", 24, "#1E2440"))
L.text([40, 60, 1200, 24],
        "same build_mascot() · 3 cameras (perspective=math) · 2 styles (style=grammar)",
        style={**txt("x", 14, "#7A7FA0"), "font_weight": 500})
cams = list(CAMERAS.items())
styles = list(STYLES.items())
cw, ch = 380, 330
x0, y0 = 80, 130
parts = build_mascot()
for ci, (cname, (yaw, pitch)) in enumerate(cams):
    for si, (sname, st) in enumerate(styles):
        px = x0 + ci * (cw + 10)
        py = y0 + si * (ch + 30)
        if st["mode"] == "blueprint":
            L.rect([px, py, cw, ch], fill="#0B2A6B", radius=14)
            for gx in range(px, px + cw, 28):
                L.add({"type": "line", "from": [gx, py], "to": [gx, py + ch],
                       "stroke": "#1E4DA0", "stroke_style": {"stroke_width": 0.6}})
        else:
            L.rect([px, py, cw, ch], fill="#FFFFFF", radius=14,
                   shadow={"dx": 0, "dy": 10, "blur": 26, "color": "#5B3FA8", "opacity": 0.12})
        c = cam(px + cw / 2, py + ch / 2 + 30, yaw, pitch)
        draw_mascot(L, parts, c, st)
        lab = "#BFE6FF" if st["mode"] == "blueprint" else "#241B4A"
        L.text([px + 14, py + 12, cw - 28, 20], f"{cname}  ·  {sname}", style=txt("x", 13, lab))

# ---- Page 2: the measurable gate (defect -> detect -> auto-fix) ------------ #
p2 = b.page("gate", canvas={"size": [W, 520], "units": "px"}, coordinate_mode="absolute")
G = p2.layer("main")
G.rect([0, 0, W, 520], fill="#F5F4FB")
G.text([40, 28, 1200, 30], "Measurable gate: detect + auto-correct a proportion defect",
        style=txt("x", 22, "#1E2440"))
TARGET = measure_head_units(build_mascot(1.0), cam(0, 0, 35, -12))  # spec head-units
bad = build_mascot(head_scale=1.7)                                   # injected defect
gcam = cam(0, 0, 35, -12)
fixed, obs, obs2, history, ok = gate_fix_proportion(bad, gcam, TARGET)
panels = [("1 · defect (head x1.7)", bad, obs, "#FFFFFF"),
          (f"2 · gate iterated {len(history)-1}x -> fixed", fixed, obs2, "#FFFFFF")]
for i, (lab, prt, val, bg) in enumerate(panels):
    px = 120 + i * 520
    G.rect([px, 110, 460, 360], fill=bg, radius=14,
           shadow={"dx": 0, "dy": 10, "blur": 26, "color": "#5B3FA8", "opacity": 0.12})
    draw_mascot(G, prt, cam(px + 230, 330, 35, -12), STYLES["flat-cel"])
    G.text([px + 16, 122, 430, 20], lab, style=txt("x", 14, "#241B4A"))
    G.text([px + 16, 440, 430, 20], f"head-units = {val:.2f}  (target {TARGET:.2f})",
           style={**txt("x", 13, "#16A34A" if abs(val-TARGET) <= 0.12 else "#C23B3B"),
                  "font_weight": 700})
G.text([40, 486, 1200, 22],
        "gate trace: " + " -> ".join(f"{h:.2f}" for h in history) +
        f"  target {TARGET:.2f}  ({'PASS' if ok else 'FAIL'})",
        style={**txt("x", 14, "#1E2440"), "font_weight": 600})

doc = b.build()
out = sys.argv[1] if len(sys.argv) > 1 else "out/poc2"
os.makedirs(out, exist_ok=True)
for i, svg in enumerate(render_page_svgs(doc), 1):
    open(f"{out}/poc2_p{i}.svg", "w").write(svg)
print(f"target_head_units={TARGET:.3f} defect_obs={obs:.3f} after_fix={obs2:.3f} pass={ok}")
print("rendered", len(render_page_svgs(doc)), "pages")
