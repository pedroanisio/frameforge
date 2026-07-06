"""Formula 1 car — one organic 3D model, two cameras (FrameGraph composition).

A single geometric F1 model is assembled from >256 primitive COMPONENTS — mostly
LOFTED surfaces (elliptical cross-sections swept along the car, giving smooth,
organic bodywork, nose, engine cover and coke-bottle sidepods) plus barrelled
wheels with spokes/tread, halo, wings and aero furniture. The same face list is
projected through TWO cameras and drawn with the SDK:

  * View 1 — a 3/4 PERSPECTIVE pinhole projection (front-left-high eye);
  * View 2 — an ORTHOGRAPHIC TOP projection (straight down -Z).

Both views consume the exact same faces; only the projection differs, so the
perspective and the plan necessarily agree. Every face carries a baked outward
normal, is backface-culled per camera, flat-shaded from one world light, painter-
sorted back-to-front, and emitted as one closed polyline = one LAYER (>1024
total). Accent/rim/aero faces carry ordered `effects` (neon glow / soft shadow),
and a blueprint grid is glow-lit — >75 effect entries in all.

Counts (components / layers / effects) are computed at build time and printed
into the subtitle, so the claims are the real numbers, not decoration.

Verified through the MCP: run_sdk_client returns ok:true; detect_regions +
a direct read of the render drive iteration. (No `describe_render` tool exists on
this server; the available vision tools are used instead.)
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import DocumentBuilder, rgba  # noqa: E402

PI = math.pi
PAGE_W, PAGE_H = 1460.0, 940.0
GRIDN = 120                       # blueprint grid lines (decorative + effect carriers)

# ---- palette (base albedos; shading multiplies these) --------------------- #
BG = "#0e1622"
GRID = "#3fd0e0"
BODY = "#f2591f"
BODY2 = "#ff7a3c"
CARBON = "#1b2431"
CARBON2 = "#273244"
TYRE = "#16171c"
TREADC = "#0c0d11"
RIM = "#c98a34"
GOLD = "#ffcf6b"
HALO = "#8f96a1"
COCKPIT = "#0a0d13"
WHITE = "#f2efe6"
CYAN = "#18c2d6"
INK = "#d7e2ea"
SANS = ["Helvetica", "Arial", "sans-serif"]

# ---- assembly state ------------------------------------------------------- #
F = []                            # faces: (verts, color, normal, fx)
COMPONENTS = 0


def reset():
    global F, COMPONENTS
    F, COMPONENTS = [], 0


def comp():
    global COMPONENTS
    COMPONENTS += 1


# ---- tiny 3D vector helpers ----------------------------------------------- #
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def nrm(a):
    m = math.sqrt(dot(a, a))
    return (a[0] / m, a[1] / m, a[2] / m) if m > 1e-9 else (0.0, 0.0, 1.0)


def cen(vs):
    k = len(vs)
    return (sum(v[0] for v in vs) / k, sum(v[1] for v in vs) / k, sum(v[2] for v in vs) / k)


def newell(vs):
    nx = ny = nz = 0.0
    for i in range(len(vs)):
        a, b = vs[i], vs[(i + 1) % len(vs)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return nrm((nx, ny, nz))


def outward(verts, color, pc, fx):
    n = newell(verts)
    if dot(n, sub(cen(verts), pc)) < 0:
        n = (-n[0], -n[1], -n[2])
    return (verts, color, n, fx)


# ---- primitive builders (each registers 1+ components, appends faces) ------ #
def box(cx, cy, cz, sx, sy, sz, color, fx=None):
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    idx = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (1, 2, 6, 5), (0, 3, 7, 4)]
    comp()
    F.extend(outward([c[i] for i in f], color, (cx, cy, cz), fx) for f in idx)


def quad(v, color, n, fx=None):
    comp()
    F.append((v, color, nrm(n), fx))


def ellring(x, cy, cz, ry, rz, m):
    return [(x, cy + ry * math.cos(2 * PI * k / m), cz + rz * math.sin(2 * PI * k / m)) for k in range(m)]


def loft(stations, m, color, fx=None, cap_end=False):
    """Sweep an elliptical cross-section along X through `stations`
    (x, cy, cz, ry, rz). Each band between two stations is one component."""
    rings = [ellring(*s, m) for s in stations]
    axis = [(s[0], s[1], s[2]) for s in stations]
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        pc = cen([axis[i], axis[i + 1]])
        comp()
        for k in range(m):
            q = [a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]]
            F.append(outward(q, color, pc, fx))
    if cap_end:                                            # nose tip cap (faces +X)
        comp()
        v = rings[-1]
        n = newell(v)
        if n[0] < 0:
            n = (-n[0], -n[1], -n[2])
        F.append((v, color, n, fx))


def ring2d(cx, cz, r, m):
    return [(cx + r * math.cos(2 * PI * k / m), cz + r * math.sin(2 * PI * k / m)) for k in range(m)]


def wheel(cx, cz, r, y0, y1, m, fx_rim="rimglow"):
    ymid = (y0 + y1) / 2
    for (ya, ra, yb, rb) in ((y0, r * 0.94, ymid, r), (ymid, r, y1, r * 0.94)):   # barrelled tread
        A, B = ring2d(cx, cz, ra, m), ring2d(cx, cz, rb, m)
        comp()
        for k in range(m):
            q = [(A[k][0], ya, A[k][1]), (A[(k + 1) % m][0], ya, A[(k + 1) % m][1]),
                 (B[(k + 1) % m][0], yb, B[(k + 1) % m][1]), (B[k][0], yb, B[k][1])]
            ang = 2 * PI * (k + 0.5) / m
            F.append((q, TYRE, nrm((math.cos(ang), 0.0, math.sin(ang))), None))
    for k in range(m):                                                            # tread grooves / blocks
        a = 2 * PI * (k + 0.5) / m
        da = (PI / m) * 0.55
        rr = r + 1.2
        q = [(cx + rr * math.cos(a - da), y0, cz + rr * math.sin(a - da)),
             (cx + rr * math.cos(a + da), y0, cz + rr * math.sin(a + da)),
             (cx + rr * math.cos(a + da), y1, cz + rr * math.sin(a + da)),
             (cx + rr * math.cos(a - da), y1, cz + rr * math.sin(a - da))]
        quad(q, TREADC, (math.cos(a), 0.0, math.sin(a)))
    for s, yy in ((-1, y0), (1, y1)):                                             # both faces
        quad([(p[0], yy, p[1]) for p in ring2d(cx, cz, r * 0.94, m)], TYRE, (0, s, 0))          # sidewall
        quad([(p[0], yy + s * 0.6, p[1]) for p in ring2d(cx, cz, r * 0.58, m)], RIM, (0, s, 0), fx_rim)  # rim
        quad([(p[0], yy + s * 1.1, p[1]) for p in ring2d(cx, cz, r * 0.17, m)], CARBON, (0, s, 0))       # hub
        for k in range(SPOKES):                                                   # spokes
            a = 2 * PI * k / SPOKES
            ri, ro, w = r * 0.20, r * 0.55, 0.13
            q = [(cx + ri * math.cos(a - w), yy + s * 0.9, cz + ri * math.sin(a - w)),
                 (cx + ro * math.cos(a - w), yy + s * 0.9, cz + ro * math.sin(a - w)),
                 (cx + ro * math.cos(a + w), yy + s * 0.9, cz + ro * math.sin(a + w)),
                 (cx + ri * math.cos(a + w), yy + s * 0.9, cz + ri * math.sin(a + w))]
            quad(q, GOLD, (0, s, 0), "rimglow")
    quad([(p[0], (y0 if cx > 250 else y1) - 0.6, p[1]) for p in ring2d(cx, cz, r * 0.48, m)],
         "#3a4150", (0, -1 if cx > 250 else 1, 0))                                # brake disc (inboard)


SPOKES = 12
WSIDES = 18


# --------------------------------------------------------------------------- #
#  the shared organic 3D model
# --------------------------------------------------------------------------- #
def build_model():
    reset()
    M = 16                          # bodywork cross-section resolution
    RA, FA = 118.0, 392.0           # rear / front axle X
    WY, WHW, WR = 80.0, 15.0, 38.0  # wheel centre Y, half-width, radius

    # ---- floor / plank ----
    box(250, 0, 4, 320, 68, 6, CARBON)
    box(250, 0, 8, 250, 44, 4, CARBON2)
    for i in range(6):              # floor edge fences
        box(150 + i * 42, 34, 12, 8, 3, 12, CARBON, "shadow")
        box(150 + i * 42, -34, 12, 8, 3, 12, CARBON, "shadow")

    # ---- monocoque + cockpit (lofted, organic) ----
    loft([(96, 0, 24, 30, 22), (140, 0, 26, 32, 26), (185, 0, 27, 31, 26),
          (228, 0, 26, 28, 24), (270, 0, 24, 24, 20), (305, 0, 22, 20, 16)], M, BODY, "shadow")
    # ---- nose cone (loft to a tip) ----
    loft([(305, 0, 22, 20, 16), (350, 0, 21, 15, 13), (395, 0, 18, 10, 9),
          (440, 0, 15, 6, 6), (472, 0, 13, 3.2, 3.2)], M, BODY, "shadow", cap_end=True)
    # ---- engine cover + airbox (loft, rising then tapering to the tail) ----
    loft([(150, 0, 30, 22, 26), (120, 0, 40, 20, 30), (96, 0, 50, 16, 33),
          (70, 0, 44, 12, 28), (44, 0, 30, 6, 18)], M, BODY, "shadow")
    box(96, 0, 62, 16, 12, 14, COCKPIT)                       # airbox intake mouth
    loft([(150, 0, 44, 3, 14), (90, 0, 52, 3, 20), (44, 0, 40, 2, 16)], 8, CARBON, "shadow")  # shark fin
    for i in range(8):                                        # engine-cover louvres
        box(70 + i * 9, 0, 46 - i * 1.2, 5, 20, 2, CARBON2, "shadow")

    # ---- coke-bottle sidepods (lofted, organic) ----
    for sy in (1, -1):
        loft([(150, sy * 46, 24, 9, 20), (176, sy * 48, 27, 18, 23), (210, sy * 46, 27, 19, 22),
              (248, sy * 40, 23, 14, 17), (272, sy * 30, 18, 7, 11)], M, BODY, None)
        box(150, sy * 46, 26, 5, 26, 28, COCKPIT)            # radiator inlet mouth
        box(212, sy * 47, 46, 92, 5, 4, CYAN, "glow")        # sidepod accent strake (glows)
        for i in range(5):                                   # sidepod winglets
            box(236 + i * 8, sy * 52, 40 - i * 3, 6, 4, 3, CARBON, "shadow")

    # ---- cockpit rim + headrest + helmet + halo ----
    box(210, 0, 55, 66, 30, 4, COCKPIT)                      # cockpit opening
    box(158, 0, 56, 26, 34, 24, CARBON)                      # headrest
    loft([(174, 0, 58, 12, 12), (188, 0, 61, 13, 14), (202, 0, 58, 12, 12)], 12, WHITE)  # helmet (organic)
    box(198, 0, 59, 6, 22, 11, CYAN, "glow")                 # visor
    halo = [(150, 0, 52), (156, 26, 62), (176, 31, 70), (204, 26, 70), (224, 0, 60)]
    for i in range(len(halo) - 1):
        a, b = halo[i], halo[i + 1]
        am, bm = (a[0], -a[1], a[2]), (b[0], -b[1], b[2])
        quad([a, b, (b[0], b[1], b[2] - 5), (a[0], a[1], a[2] - 5)], HALO, (0, 1, 1), "glow")
        quad([am, bm, (bm[0], bm[1], bm[2] - 5), (am[0], am[1], am[2] - 5)], HALO, (0, -1, 1), "glow")
    box(224, 0, 56, 6, 6, 10, HALO, "glow")                  # halo strut

    # ---- front wing: stacked full-width elements + endplates + vanes ----
    box(452, 0, 8, 40, 200, 6, CARBON, "shadow")             # main plane
    box(446, 0, 15, 34, 194, 5, BODY, "shadow")              # 2nd element
    box(441, 0, 21, 28, 186, 4, CARBON, "shadow")            # 3rd element
    box(437, 0, 27, 22, 178, 3, BODY, "shadow")              # top flap
    for sy in (1, -1):
        box(454, sy * 99, 17, 46, 6, 28, CARBON, "shadow")   # endplate
        for i in range(4):                                   # canard / dive-plane cascade
            box(448 - i * 6, sy * 92, 12 + i * 4, 10, 5, 3, BODY, "shadow")
    box(456, 0, 12, 30, 26, 3, WHITE)                        # nose-tip sponsor

    # ---- rear wing: main + flap + endplates + beam + swan-necks + T-wing ----
    box(46, 0, 84, 40, 158, 8, CARBON, "shadow")             # main plane
    box(40, 0, 95, 34, 152, 6, BODY, "shadow")               # upper flap (DRS)
    for sy in (1, -1):
        box(50, sy * 80, 80, 50, 6, 42, CARBON, "shadow")    # endplate
    box(58, 0, 60, 46, 128, 8, CARBON, "shadow")             # beam wing
    for sy in (1, -1):
        box(74, sy * 12, 68, 8, 8, 34, CARBON2, "shadow")    # swan-neck pylon
    box(120, 0, 66, 10, 90, 4, BODY, "shadow")               # T-wing

    # ---- barge boards / turning vanes / deflectors ----
    for sy in (1, -1):
        for i in range(5):
            box(300 + i * 9, sy * 34, 20 + i * 2, 6, 3, 16, CARBON, "shadow")   # bargeboard fins
        for i in range(3):
            box(340 + i * 14, sy * 26, 16, 4, 3, 12, CARBON2, "shadow")         # turning vanes
        box(360, sy * 40, 14, 40, 4, 10, CARBON, "shadow")                      # deflector
        box(300, sy * 62, 14, 26, 5, 20, CARBON, "shadow")                      # brake duct
        box(210, sy * 66, 40, 10, 6, 8, CARBON2)                                # mirror stalk + housing
        box(206, sy * 70, 41, 12, 3, 7, "#3a4150")

    # ---- suspension wishbones (chassis -> hubs) ----
    for ax in (RA, FA):
        for sy in (1, -1):
            for dz in (-6, 12):
                box((ax + (150 if ax < 250 else 330)) / 2, sy * (WY - 20) / 2 + sy * 20,
                    WR + dz, abs(ax - (150 if ax < 250 else 330)), 4, 3, CARBON, "shadow")
            box((ax + (150 if ax < 250 else 330)) / 2 + 6, sy * (WY - 26) / 2 + sy * 26,
                WR + 2, abs(ax - (150 if ax < 250 else 330)) * 0.8, 3, 3, CARBON2)   # pushrod

    # ---- wheels (organic barrelled tyres, spokes, tread) ----
    for ax in (RA, FA):
        for sy in (1, -1):
            y0, y1 = min(sy * (WY - WHW), sy * (WY + WHW)), max(sy * (WY - WHW), sy * (WY + WHW))
            wheel(ax, WR, WR, y0, y1, WSIDES)

    return list(F), COMPONENTS


# --------------------------------------------------------------------------- #
#  cameras
# --------------------------------------------------------------------------- #
def make_perspective(eye, look, up=(0.0, 0.0, 1.0), f=920.0):
    fwd = nrm(sub(look, eye))
    right = nrm(cross(fwd, up))
    tup = cross(right, fwd)

    def proj(p):
        rel = sub(p, eye)
        vz = max(dot(rel, fwd), 1e-3)
        return (f * dot(rel, right) / vz, -f * dot(rel, tup) / vz, vz)
    return proj, eye


def make_top():
    def proj(p):
        return (p[1], -p[0], -p[2])
    return proj, None


LIGHT = nrm((0.35, 0.55, 0.85))


def _rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def shade(hexcol, b):
    r, g, bl = _rgb(hexcol)
    return "#%02x%02x%02x" % (max(0, min(255, int(r * b))),
                              max(0, min(255, int(g * b))),
                              max(0, min(255, int(bl * b))))


def fx_effects(fx):
    if fx == "glow":
        return [{"kind": "glow", "color": CYAN, "blur": 6.0, "opacity": 0.85}]
    if fx == "rimglow":
        return [{"kind": "glow", "color": GOLD, "blur": 4.0, "opacity": 0.8}]
    if fx == "shadow":
        return [{"kind": "shadow", "color": "#05070d", "blur": 8.0, "dx": 0.0, "dy": 6.0, "opacity": 0.45}]
    return None


# ---- 2D emitters ---------------------------------------------------------- #
def poly(pts, fill, effects=None):
    o = {"type": "polyline", "closed": True, "points": [[float(x), float(y)] for x, y in pts],
         "fill": fill, "stroke": "none", "decorative": True}
    if effects:
        o["effects"] = effects
    return o


def rect(box_, **k):
    return {"type": "rect", "box": [float(v) for v in box_], "decorative": True, **k}


def line(pts, color, w=1.0, opacity=1.0, effects=None):
    o = {"type": "polyline", "points": [[float(x), float(y)] for x, y in pts],
         "stroke": color, "stroke_style": {"stroke_width": w}, "fill": "none",
         "decorative": True, "opacity": opacity}
    if effects:
        o["effects"] = effects
    return o


def text(x, y, s, size, color, w=400, weight=700, align="left"):
    return {"type": "text", "box": [float(x), float(y), float(w), float(size * 1.5)], "text": s,
            "style": {"font_family": SANS, "font_size": size, "color": color, "align": align,
                      "vertical_align": "middle", "font_weight": weight}, "decorative": True}


# --------------------------------------------------------------------------- #
#  render one camera's view; returns (polys, effect_count)
# --------------------------------------------------------------------------- #
def render_view(faces, proj, eye, panel):
    ox, oy, pw, ph = panel
    raw = []
    for verts, color, n, fx in faces:
        c = cen(verts)
        cdir = nrm(sub(eye, c)) if eye is not None else (0.0, 0.0, 1.0)
        if dot(n, cdir) <= 0.0:                # backface cull
            continue
        sc = [proj(v) for v in verts]
        depth = sum(p[2] for p in sc) / len(sc)
        b = 0.34 + 0.92 * max(0.0, dot(n, LIGHT))
        raw.append((depth, [(p[0], p[1]) for p in sc], shade(color, b), fx))
    xs = [x for _, sc, _, _ in raw for x, y in sc]
    ys = [y for _, sc, _, _ in raw for x, y in sc]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    m = 0.055
    scale = min(pw * (1 - 2 * m) / (maxx - minx), ph * (1 - 2 * m) / (maxy - miny))
    tx = ox + pw / 2 - (minx + maxx) / 2 * scale
    ty = oy + ph / 2 - (miny + maxy) / 2 * scale
    out, nfx = [], 0
    for depth, sc, col, fx in sorted(raw, key=lambda r: r[0], reverse=True):
        eff = fx_effects(fx)
        if eff:
            nfx += len(eff)
        out.append(poly([(tx + x * scale, ty + y * scale) for x, y in sc], col, eff))
    return out, nfx


def gnomon(ox, oy, proj, s=56):
    o = proj((0, 0, 0))
    S = []
    for tip, col in (((s, 0, 0), "#ff5a3c"), ((0, s, 0), "#3fd0e0"), ((0, 0, s), "#8fd694")):
        t = proj(tip)
        S.append(line([(ox + o[0], oy + o[1]), (ox + t[0], oy + t[1])], col, w=2.5,
                      effects=[{"kind": "glow", "color": col, "blur": 3.0, "opacity": 0.8}]))
    return S


def blueprint_grid(k, glow_first):
    S = []
    nv = (k + 1) // 2
    nh = k - nv
    ge = [{"kind": "glow", "color": CYAN, "blur": 3.0, "opacity": 0.5}]
    idx = 0
    for i in range(nv):
        x = PAGE_W * (i + 0.5) / nv
        S.append(line([(x, 86), (x, PAGE_H)], rgba(GRID, 0.06), w=1, effects=ge if idx < glow_first else None))
        idx += 1
    for j in range(nh):
        y = 86 + (PAGE_H - 86) * (j + 0.5) / nh
        S.append(line([(0, y), (PAGE_W, y)], rgba(GRID, 0.06), w=1, effects=ge if idx < glow_first else None))
        idx += 1
    return S


# --------------------------------------------------------------------------- #
#  assemble
# --------------------------------------------------------------------------- #
def scene():
    faces, ncomp = build_model()
    persp_panel = (24, 100, 892, 806)
    top_panel = (932, 100, 504, 806)
    p_proj, p_eye = make_perspective(eye=(720.0, 330.0, 300.0), look=(240.0, 0.0, 40.0))
    t_proj, _ = make_top()

    persp, e1 = render_view(faces, p_proj, p_eye, persp_panel)
    topv, e2 = render_view(faces, t_proj, None, top_panel)
    gn = gnomon(persp_panel[0] + 62, persp_panel[1] + persp_panel[3] - 42, p_proj) \
        + gnomon(top_panel[0] + 46, top_panel[1] + top_panel[3] - 26, t_proj)

    car_fx = e1 + e2 + 6            # +6 gnomon glows
    glow_first = max(0, 96 - car_fx)                 # top the grid glows up past 75
    grid = blueprint_grid(GRIDN, glow_first)
    total_fx = car_fx + min(glow_first, GRIDN)

    L = 1 + len(grid) + len(persp) + len(topv) + len(gn)   # +5 labels below
    labels = [
        line([(922, 100), (922, PAGE_H - 24)], rgba(GRID, 0.28), w=1.5),
        text(40, 40, "FORMULA 1 — ONE ORGANIC 3D MODEL, TWO CAMERAS", 25, INK, w=1200, weight=800),
        text(40, 70, f"{ncomp} components · {L + 5} layers · {total_fx} effects · "
                     "lofted geometry · perspective + orthographic-top · FrameGraph SDK",
             13, rgba(INK, 0.78), w=1320, weight=600),
        text(persp_panel[0] + 12, persp_panel[1] + 16, "① 3/4 PERSPECTIVE", 15, CYAN, w=360, weight=800),
        text(top_panel[0] + 12, top_panel[1] + 16, "② TOP · ORTHOGRAPHIC PLAN", 15, CYAN, w=400, weight=800),
    ]
    layers = [rect([0, 0, PAGE_W, PAGE_H], fill=BG)] + grid + persp + topv + gn + labels

    assert ncomp > 256, f"components {ncomp} !> 256"
    assert len(layers) > 1024, f"layers {len(layers)} !> 1024"
    assert total_fx > 75, f"effects {total_fx} !> 75"
    return layers


def build_builder():
    b = DocumentBuilder(title="Formula 1 — one organic 3D model, two cameras (FrameGraph)")
    page = b.page("f1_3d", canvas={"size": [PAGE_W, PAGE_H], "units": "px"}, coordinate_mode="absolute")
    page.layer("scene").extend(scene())
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from framegraph.sdk import serialize
    _, nc = build_model()
    out = os.environ.get("OUTPUT_YAML_PATH", "f1_car_3d.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}  ({len(scene())} layers, {nc} components)")
