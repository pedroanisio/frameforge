"""Formula 1 car — one 3D model, two cameras (512-layer FrameGraph composition).

A single geometric F1 model (built from 3D boxes / frustums / cylinders in world
space) is projected through TWO cameras and drawn with the FrameGraph SDK:

  * View 1 — a 3/4 PERSPECTIVE camera (pinhole projection, front-left-high eye);
  * View 2 — an ORTHOGRAPHIC TOP projection (looking straight down -Z).

Both views share the exact same face list; only the projection differs. Each
face is flat-shaded from one world light (Lambert), painter-sorted back-to-front,
and emitted as one polygon = one layer. The document is exactly 512 layers
(asserted at build): 1 background + a blueprint grid solved to fill the budget +
the two projected models + view labels / gnomons / titles.

Nothing here is hand-drawn in 2D: the silhouette of each view is a consequence
of the 3D geometry and the camera, so the perspective and the plan agree.

Verified through the MCP: run_sdk_client returns ok:true; detect_regions +
visual read drive iteration.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import DocumentBuilder, rgba  # noqa: E402

PAGE_W, PAGE_H = 1440.0, 900.0
TARGET_LAYERS = 512

# ---- palette (base albedos; shading multiplies these) --------------------- #
BG = "#0e1622"
GRID = "#3fd0e0"
BODY = "#f2591f"
BODY2 = "#ff7a3c"
CARBON = "#1b2431"
TYRE = "#15161a"
RIM = "#c98a34"
HALO = "#8f96a1"
COCKPIT = "#0a0d13"
WHITE = "#f2efe6"
CYAN = "#18c2d6"
INK = "#d7e2ea"
SANS = ["Helvetica", "Arial", "sans-serif"]


# ---- tiny 3D vector helpers ----------------------------------------------- #
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    m = math.sqrt(dot(a, a))
    return (a[0] / m, a[1] / m, a[2] / m) if m > 1e-9 else (0.0, 0.0, 1.0)


def centroid(vs):
    n = len(vs)
    return (sum(v[0] for v in vs) / n, sum(v[1] for v in vs) / n, sum(v[2] for v in vs) / n)


def neg(a):
    return (-a[0], -a[1], -a[2])


def face_normal(vs):                       # Newell's method (robust for quads)
    nx = ny = nz = 0.0
    for i in range(len(vs)):
        a, b = vs[i], vs[(i + 1) % len(vs)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return norm((nx, ny, nz))


def mkface(verts, color, pc):
    """One face with its normal oriented OUTWARD (away from the primitive centre pc)."""
    n = face_normal(verts)
    if dot(n, sub(centroid(verts), pc)) < 0:
        n = neg(n)
    return (verts, color, n)


def orient(faces, pc):
    return [mkface(v, c, pc) for v, c in faces]


# ---- solid primitives -> lists of (verts, base_color) faces --------------- #
# World axes:  +X = forward (toward the nose),  +Y = left,  +Z = up.  Ground z=0.
def box(cx, cy, cz, sx, sy, sz, color):
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    idx = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (1, 2, 6, 5), (0, 3, 7, 4)]
    return orient([([c[i] for i in f], color) for f in idx], (cx, cy, cz))


def frustum_x(x0, x1, yh0, yh1, zb0, zt0, zb1, zt1, color):
    """A box whose cross-section (in Y,Z) differs at the two X stations x0,x1."""
    a = [(x0, -yh0, zb0), (x0, yh0, zb0), (x0, yh0, zt0), (x0, -yh0, zt0)]
    b = [(x1, -yh1, zb1), (x1, yh1, zb1), (x1, yh1, zt1), (x1, -yh1, zt1)]
    faces = [a, b,
             [a[0], a[1], b[1], b[0]],      # bottom
             [a[3], a[2], b[2], b[3]],      # top
             [a[0], a[3], b[3], b[0]],      # -Y side
             [a[1], a[2], b[2], b[1]]]      # +Y side
    return orient([(f, color) for f in faces], centroid(a + b))


def wheel(cx, cz, r, y0, y1, n, tyre, rim):
    """Cylinder about Y (an upright wheel): n tread quads, and on each face a black
    sidewall disc with an inset bronze rim + dark hub (so it reads as tyre, not coin)."""
    def ring(rr):
        return [(cx + rr * math.cos(2 * math.pi * k / n), cz + rr * math.sin(2 * math.pi * k / n))
                for k in range(n)]
    tread = ring(r)
    faces = []
    for k in range(n):                                        # tyre tread band
        a, b = tread[k], tread[(k + 1) % n]
        faces.append(([(a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1])], tyre))
    for s, yy in ((-1, y0), (1, y1)):                         # both wheel faces
        faces.append(([(p[0], yy, p[1]) for p in tread], tyre))                 # sidewall
        faces.append(([(p[0], yy + s * 0.5, p[1]) for p in ring(r * 0.60)], rim))   # rim
        faces.append(([(p[0], yy + s * 1.0, p[1]) for p in ring(r * 0.26)], CARBON))  # hub nut
    return orient(faces, (cx, (y0 + y1) / 2, cz))


# --------------------------------------------------------------------------- #
#  the shared 3D model
# --------------------------------------------------------------------------- #
def build_model():
    F = []
    RA, FA = 118.0, 388.0          # rear / front axle X
    WY, WHW = 78.0, 15.0           # wheel centre Y, half-width
    WR = 37.0                      # wheel radius
    # ---- floor / plank ----
    F += box(250, 0, 4, 300, 66, 6, CARBON)
    F += box(250, 0, 8, 250, 40, 4, "#232d3c")
    # ---- survival cell / cockpit tub ----
    F += frustum_x(150, 300, 30, 20, 10, 54, 10, 40, BODY)
    # ---- engine cover + airbox + shark fin (rear body) ----
    F += frustum_x(70, 175, 10, 24, 12, 44, 10, 66, BODY)     # cover
    F += frustum_x(150, 190, 12, 10, 60, 84, 40, 60, BODY2)   # airbox hump
    F += box(172, 0, 74, 14, 12, 12, COCKPIT)                 # airbox intake mouth
    F += frustum_x(40, 150, 3, 9, 40, 70, 12, 46, CARBON)     # shark fin (thin, tall, tapering)
    # ---- nose cone (drops to the front-wing mount) ----
    F += frustum_x(300, 470, 20, 6, 12, 40, 6, 20, BODY)
    # ---- sidepods (left + right) with radiator inlets ----
    for sy in (+1, -1):
        F += frustum_x(150, 262, 34 * 0 + 0, 0, 0, 0, 0, 0, BODY) if False else []
        F += box(206, sy * 44, 26, 116, 34, 40, BODY)
        F += box(150, sy * 44, 26, 6, 30, 30, COCKPIT)        # inlet face
        F += box(210, sy * 44, 47, 96, 8, 4, CYAN)            # sidepod accent strake
    # ---- cockpit opening + headrest + helmet ----
    F += box(210, 0, 55, 70, 30, 4, COCKPIT)                  # cockpit rim (dark opening)
    F += box(158, 0, 58, 26, 34, 26, CARBON)                  # headrest / roll structure
    F += box(188, 0, 60, 26, 22, 22, WHITE)                   # driver helmet
    F += box(196, 0, 58, 6, 22, 10, CYAN)                     # helmet visor band
    # ---- halo (titanium hoop over the cockpit, as a ribbon of quads) ----
    halo = [(150, 0, 52), (156, 26, 62), (176, 30, 70), (204, 26, 70), (224, 0, 60)]
    hpc = (180, 0, 50)
    for i in range(len(halo) - 1):
        a, b = halo[i], halo[i + 1]
        am = (a[0], -a[1], a[2])
        bm = (b[0], -b[1], b[2])
        F.append(mkface([a, b, (b[0], b[1], b[2] - 5), (a[0], a[1], a[2] - 5)], HALO, hpc))   # left rail
        F.append(mkface([am, bm, (bm[0], bm[1], bm[2] - 5), (am[0], am[1], am[2] - 5)], HALO, hpc))  # right rail
    F += box(224, 0, 56, 6, 6, 10, HALO)                     # halo front strut
    # ---- front wing: stacked full-width elements + endplates ----
    F += box(448, 0, 8, 40, 196, 6, CARBON)                  # main plane
    F += box(442, 0, 15, 34, 190, 5, BODY)                   # 2nd element
    F += box(438, 0, 21, 28, 184, 4, CARBON)                 # top flap
    for sy in (+1, -1):
        F += box(452, sy * 97, 16, 44, 6, 26, CARBON)        # endplate
    F += box(455, 0, 12, 30, 24, 3, WHITE)                   # nose-tip sponsor
    # ---- rear wing: main + flap + endplates + beam + swan-neck ----
    F += box(46, 0, 82, 40, 150, 8, CARBON)                  # main plane
    F += box(40, 0, 92, 34, 146, 6, BODY)                    # upper flap (DRS)
    for sy in (+1, -1):
        F += box(50, sy * 76, 78, 48, 6, 40, CARBON)         # endplate
    F += box(58, 0, 60, 44, 120, 8, CARBON)                  # beam wing
    F += box(74, 0, 66, 8, 10, 34, "#232d3c")               # swan-neck pylon
    # ---- suspension wishbones (thin boxes chassis -> hubs) ----
    for ax, xin in ((RA, 150), (FA, 320)):
        for sy in (+1, -1):
            for dz in (-8, 10):
                F += box((ax + xin) / 2, sy * (WY - 24) / 2 + sy * 24, WR + dz * 0 + 34,
                         abs(ax - xin), 5, 4, CARBON)
    # ---- wheels (4 upright cylinders) ----
    for ax in (RA, FA):
        for sy in (+1, -1):
            y0, y1 = sy * (WY - WHW), sy * (WY + WHW)
            lo, hi = min(y0, y1), max(y0, y1)
            F += wheel(ax, WR, WR, lo, hi, 16, TYRE, RIM)
    return F


# --------------------------------------------------------------------------- #
#  cameras: project a world point -> (screen_x, screen_y, depth)
# --------------------------------------------------------------------------- #
def make_perspective(eye, look, up=(0.0, 0.0, 1.0), f=900.0):
    fwd = norm(sub(look, eye))
    right = norm(cross(fwd, up))
    tup = cross(right, fwd)

    def proj(p):
        rel = sub(p, eye)
        vz = max(dot(rel, fwd), 1e-3)
        return (f * dot(rel, right) / vz, -f * dot(rel, tup) / vz, vz)
    return proj, eye


def make_top():                            # orthographic, straight down; length vertical, nose up
    def proj(p):
        return (p[1], -p[0], -p[2])        # screen x = +Y (width), screen y = -X (nose up), depth = -Z
    return proj, None


# ---- shading ------------------------------------------------------------- #
LIGHT = norm((0.35, 0.55, 0.85))


def _rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def shade(hexcol, b):
    r, g, bl = _rgb(hexcol)
    return "#%02x%02x%02x" % (max(0, min(255, int(r * b))),
                              max(0, min(255, int(g * b))),
                              max(0, min(255, int(bl * b))))


# ---- primitive 2D emitters ------------------------------------------------ #
def poly(pts, fill, opacity=1.0):
    return {"type": "polyline", "closed": True, "points": [[float(x), float(y)] for x, y in pts],
            "fill": fill, "stroke": "none", "decorative": True, "opacity": opacity}


def rect(box_, **k):
    return {"type": "rect", "box": [float(v) for v in box_], "decorative": True, **k}


def line(pts, color, w=1.0, opacity=1.0):
    return {"type": "polyline", "points": [[float(x), float(y)] for x, y in pts],
            "stroke": color, "stroke_style": {"stroke_width": w}, "fill": "none",
            "decorative": True, "opacity": opacity}


def text(x, y, s, size, color, w=400, weight=700, align="left"):
    st = {"font_family": SANS, "font_size": size, "color": color, "align": align,
          "vertical_align": "middle", "font_weight": weight}
    return {"type": "text", "box": [float(x), float(y), float(w), float(size * 1.5)],
            "text": s, "style": st, "decorative": True}


# --------------------------------------------------------------------------- #
#  render one camera's view of the shared model into a screen panel
# --------------------------------------------------------------------------- #
def render_view(faces, proj, eye, panel):
    ox, oy, pw, ph = panel
    raw = []                               # (depth, [(sx,sy)..], shaded_color)
    for verts, color, n in faces:
        cen = centroid(verts)
        cdir = norm(sub(eye, cen)) if eye is not None else (0.0, 0.0, 1.0)
        if dot(n, cdir) <= 0.0:            # backface cull: skip faces turned away from this camera
            continue
        sc = [proj(v) for v in verts]
        depth = sum(p[2] for p in sc) / len(sc)
        b = 0.34 + 0.90 * max(0.0, dot(n, LIGHT))
        raw.append((depth, [(p[0], p[1]) for p in sc], shade(color, b)))
    xs = [x for _, sc, _ in raw for x, y in sc]
    ys = [y for _, sc, _ in raw for x, y in sc]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    m = 0.06
    scale = min(pw * (1 - 2 * m) / (maxx - minx), ph * (1 - 2 * m) / (maxy - miny))
    tx = ox + pw / 2 - (minx + maxx) / 2 * scale
    ty = oy + ph / 2 - (miny + maxy) / 2 * scale
    out = []
    for depth, sc, col in sorted(raw, key=lambda r: r[0], reverse=True):
        out.append(poly([(tx + x * scale, ty + y * scale) for x, y in sc], col))
    return out


def gnomon(ox, oy, proj, eye, s=54):
    """A small XYZ axis indicator projected with the same camera (technical cue)."""
    O = (0, 0, 0)
    axes = [((s, 0, 0), "#ff5a3c"), ((0, s, 0), "#3fd0e0"), ((0, 0, s), "#8fd694")]
    o2 = proj(O)
    S = []
    for tip, col in axes:
        t2 = proj(tip)
        S.append(line([(ox + o2[0] * 0 + o2[0], oy + o2[1]), (ox + t2[0], oy + t2[1])], col, w=2.5))
    return S


# --------------------------------------------------------------------------- #
#  assemble the 512-layer document
# --------------------------------------------------------------------------- #
def blueprint_grid(k):
    """Exactly k faint grid lines (a CAD backdrop) — fills the layer budget."""
    S = []
    nv = (k + 1) // 2
    nh = k - nv
    for i in range(nv):
        x = PAGE_W * (i + 0.5) / nv
        S.append(line([(x, 84), (x, PAGE_H)], rgba(GRID, 0.055), w=1))
    for j in range(nh):
        y = 84 + (PAGE_H - 84) * (j + 0.5) / nh
        S.append(line([(0, y), (PAGE_W, y)], rgba(GRID, 0.055), w=1))
    return S


def scene():
    faces = build_model()

    persp_panel = (24, 96, 872, 780)
    top_panel = (912, 96, 504, 780)

    p_proj, p_eye = make_perspective(eye=(720.0, 330.0, 300.0), look=(240.0, 0.0, 40.0), f=900.0)
    t_proj, t_eye = make_top()

    persp = render_view(faces, p_proj, p_eye, persp_panel)
    topv = render_view(faces, t_proj, t_eye, top_panel)

    # gnomons drawn in each panel corner (same cameras)
    gn = (gnomon(persp_panel[0] + 60, persp_panel[1] + persp_panel[3] - 40, p_proj, p_eye)
          + gnomon(top_panel[0] + 44, top_panel[1] + top_panel[3] - 24, t_proj, t_eye))

    labels = [
        line([(902, 96), (902, PAGE_H - 24)], rgba(GRID, 0.25), w=1.5),          # panel divider
        text(40, 40, "FORMULA 1 — ONE 3D MODEL, TWO CAMERAS", 26, INK, w=1000, weight=800),
        text(40, 70, "512 layers · shared geometry · perspective + orthographic-top projection · FrameGraph SDK",
             13, rgba(INK, 0.75), w=1100, weight=600),
        text(persp_panel[0] + 12, persp_panel[1] + 16, "① 3/4 PERSPECTIVE", 15, CYAN, w=360, weight=800),
        text(top_panel[0] + 12, top_panel[1] + 16, "② TOP · ORTHOGRAPHIC PLAN", 15, CYAN, w=380, weight=800),
    ]

    fixed = [rect([0, 0, PAGE_W, PAGE_H], fill=BG)] + persp + topv + gn + labels
    k = TARGET_LAYERS - len(fixed)
    if k < 0:
        raise ValueError(f"model already emits {len(fixed)} layers > {TARGET_LAYERS}")
    layers = ([fixed[0]] + blueprint_grid(k) + fixed[1:])
    assert len(layers) == TARGET_LAYERS, f"{len(layers)} != {TARGET_LAYERS}"
    return layers


def build_builder():
    b = DocumentBuilder(title="Formula 1 — one 3D model, two cameras (FrameGraph)")
    page = b.page("f1_3d", canvas={"size": [PAGE_W, PAGE_H], "units": "px"}, coordinate_mode="absolute")
    page.layer("scene").extend(scene())
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from framegraph.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "f1_car_3d.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}  ({len(scene())} layers)")
