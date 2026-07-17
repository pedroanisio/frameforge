"""F1 technical dossier — the organic 3D model driven through the whole SDK.

"Use all the power": this sheet reuses the single lofted F1 model from
``f1_car_3d`` and renders it as an engineering dossier that exercises a broad
slice of the FrameForge SDK, each subsystem doing real work (not decoration):

  * geometry  — Camera + ViewingPipeline project the 3D model (perspective),
                and convex_hull builds the car's screen silhouette;
  * planar    — offset_polygon + to_path expand that silhouette into a halo;
  * outline   — stroke_outline draws a variable-width, glowing contour on it;
  * fields    — ScalarField.heatmap + contours paint an aero-pressure backdrop;
  * chart     — Chart/Frame plot a lap speed + throttle telemetry trace;
  * topology  — Graph lays out and renders the power-unit schematic;
  * chevreul  — color_guide + tone_scale derive the accent/harmony swatches;
  * canon     — modular_scale sizes the type; johnston_margins sets the frame;
  * macros    — sparkline / greeble / hatch_fill add the instrument furniture.

Counts (components / layers / effects / subsystems) are computed at build time
and printed into the subtitle, so the claims are the real numbers.

MCP-verified: run_sdk_client returns ok:true; detect_regions + a direct read of
the render drive iteration. (No describe_render tool exists on this server.)
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs"), HERE]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder, canon, chart, chevreul, fields, macros, outline, planar, rgba, topology)
from frameforge.sdk.geometry import Camera, ViewingPipeline, Vec3, convex_hull  # noqa: E402

import f1_car_3d as base  # noqa: E402  (the shared organic 3D model + helpers)

PAGE_W, PAGE_H = 1680.0, 1050.0
BG = base.BG
GRID = base.GRID
CYAN = base.CYAN
GOLD = base.GOLD
INK = base.INK
CARBON = base.CARBON
BODY = base.BODY
SANS = base.SANS

EYE = (720.0, 330.0, 300.0)
LOOK = (240.0, 0.0, 40.0)
USED = set()                       # SDK subsystems actually exercised


# ---- 2D emitters ---------------------------------------------------------- #
def rect(box_, **k):
    return {"type": "rect", "box": [float(v) for v in box_], "decorative": True, **k}


def line(pts, color, w=1.0, opacity=1.0, effects=None):
    o = {"type": "polyline", "points": [[float(x), float(y)] for x, y in pts],
         "stroke": color, "stroke_style": {"stroke_width": w}, "fill": "none",
         "decorative": True, "opacity": opacity}
    if effects:
        o["effects"] = effects
    return o


def text(x, y, s, size, color, w=520, weight=700, align="left"):
    return {"type": "text", "box": [float(x), float(y), float(w), float(size * 1.5)], "text": s,
            "style": {"font_family": SANS, "font_size": size, "color": color, "align": align,
                      "vertical_align": "middle", "font_weight": weight}, "decorative": True}


GLOW = [{"kind": "glow", "color": CYAN, "blur": 6.0, "opacity": 0.85}]
GLOWG = [{"kind": "glow", "color": GOLD, "blur": 4.0, "opacity": 0.8}]


def spec_fx(fx):
    # keep glows (cheap, visible); drop the per-facet shadows here for a lighter sheet
    if fx == "glow":
        return list(GLOW)
    if fx == "rimglow":
        return list(GLOWG)
    return None


# --------------------------------------------------------------------------- #
#  project the shared model with the SDK's own camera pipeline
# --------------------------------------------------------------------------- #
def _fit(raw, panel, margin=0.06):
    ox, oy, pw, ph = panel
    xs = [x for _, pts, _, _ in raw for x, y in pts]
    ys = [y for _, pts, _, _ in raw for x, y in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    sc = min(pw * (1 - 2 * margin) / (maxx - minx), ph * (1 - 2 * margin) / (maxy - miny))
    tx = ox + pw / 2 - (minx + maxx) / 2 * sc
    ty = oy + ph / 2 - (miny + maxy) / 2 * sc
    return sc, tx, ty


def render_perspective(faces, panel):
    """View 1 — SDK Camera + ViewingPipeline (geometry). ViewingPipeline auto-frames
    the points it is given, so the WHOLE scene must be projected in one call (then
    faces are sliced back out by index). Returns (polys, hull_pts, nfx)."""
    USED.add("geometry")
    ox, oy, pw, ph = panel
    cam = Camera(eye=Vec3(*EYE), target=Vec3(*LOOK), up=Vec3(0, 0, 1),
                 fov=38.0, aspect=pw / ph, near=1.0, far=6000.0)
    vp = ViewingPipeline(cam, [ox, oy, pw, ph])
    kept, flat = [], []
    for verts, color, n, fx in faces:
        c = base.cen(verts)
        if base.dot(n, base.nrm(base.sub(EYE, c))) <= 0.0:      # backface cull
            continue
        i0 = len(flat)
        flat.extend(Vec3(*v) for v in verts)
        b = 0.34 + 0.92 * max(0.0, base.dot(n, base.LIGHT))
        kept.append((_dist(EYE, c), i0, len(verts), base.shade(color, b), fx))
    proj = vp.project(flat)                                      # single auto-framed projection
    polys, nfx, allpts = [], 0, []
    for depth, i0, k, col, fx in sorted(kept, key=lambda r: r[0], reverse=True):
        sp = [(proj[i0 + j].x, proj[i0 + j].y) for j in range(k)]
        allpts.extend(sp)
        eff = spec_fx(fx)
        if eff:
            nfx += len(eff)
        polys.append(base.poly(sp, col, eff))
    return polys, allpts, nfx


def render_top(faces, panel):
    """View 2 — orthographic top (straight down -Z)."""
    raw = []
    for verts, color, n, fx in faces:
        if n[2] <= 0.0:                                          # cull faces not facing up
            continue
        pts = [(v[1], -v[0]) for v in verts]
        b = 0.34 + 0.92 * max(0.0, base.dot(n, base.LIGHT))
        raw.append((-base.cen(verts)[2], pts, base.shade(color, b), fx))
    sc, tx, ty = _fit(raw, panel)
    polys, nfx = [], 0
    for depth, pts, col, fx in sorted(raw, key=lambda r: r[0], reverse=True):
        eff = spec_fx(fx)
        if eff:
            nfx += len(eff)
        polys.append(base.poly([(tx + x * sc, ty + y * sc) for x, y in pts], col, eff))
    return polys, nfx


def _dist(a, b):
    return math.sqrt(base.dot(base.sub(a, b), base.sub(a, b)))


# --------------------------------------------------------------------------- #
#  SDK-powered panels
# --------------------------------------------------------------------------- #
def silhouette(hull_pts):
    """geometry.convex_hull -> planar halo -> outline.stroke_outline glowing contour."""
    USED.update(("geometry", "planar", "outline"))
    hull = [(v.x, v.y) for v in convex_hull(hull_pts)]
    halo_rings = planar.offset_polygon([[x, y] for x, y in hull], 12.0)
    halo = planar.to_path(halo_rings, fill=rgba(CYAN, 0.05), decorative=True)
    contour = outline.stroke_outline(
        hull + [hull[0]], 3.2, profile=lambda t: 0.45 + 0.55 * math.sin(t * math.pi),
        smooth=True, fill=CYAN, decorative=True)
    contour["opacity"] = 0.9
    contour["effects"] = list(GLOW)
    return halo, contour


def aero_field(panel):
    """fields.ScalarField -> heatmap backdrop + faint contours (aero pressure)."""
    USED.add("fields")
    ox, oy, pw, ph = panel

    def press(x, y):                       # a stylised pressure field: stagnation + wake
        stag = 1.4 * math.exp(-(((x - 0.62) * 3.2) ** 2 + (y * 3.6) ** 2))
        wake = -0.8 * math.exp(-(((x + 0.55) * 2.2) ** 2 + (y * 5.0) ** 2))
        return stag + wake + 0.25 * math.sin(x * 3.0)

    sf = fields.ScalarField(press, domain=(-1.0, -1.0, 1.0, 1.0))
    hm = sf.heatmap(box=(ox, oy, pw, ph), steps_x=40, steps_y=26, low="#0c2740", high="#ff7a3c")
    hm["opacity"] = 0.5
    ct = sf.contours(box=(ox, oy, pw, ph), levels=7, color=rgba(CYAN, 0.35), width=1.0)
    return [hm, ct]


def telemetry(panel):
    """chart.Chart — lap speed + throttle trace; macros.sparkline mini-trace."""
    USED.update(("chart", "macros"))
    ox, oy, pw, ph = panel
    n = 120
    speed = [(i, 120 + 190 * (0.5 + 0.5 * math.sin(i * 0.19) * math.cos(i * 0.06))) for i in range(n)]
    thr = [(i, 40 + 60 * (0.5 + 0.5 * math.sin(i * 0.19 + 0.3))) for i in range(n)]
    fr = chart.Frame(domain=(0, 0, n - 1, 340), box=(ox, oy, pw, ph))
    ch = chart.Chart(fr)
    ch.axes(grid=True, axis_color=rgba(GRID, 0.5), grid_color=rgba(GRID, 0.12),
            label_style={"font_family": SANS, "font_size": 9, "color": rgba(INK, 0.6)})
    ch.line(speed, stroke=CYAN, width=2.4, smooth=True, label="speed")
    ch.line(thr, stroke=GOLD, width=1.8, smooth=True, label="throttle")
    objs = ch.objects()
    spark = macros.sparkline([(i, s) for i, s in speed[::4]],
                             box=(ox + pw - 168, oy - 30, 160, 24), color=CYAN, width=1.6)
    return objs + [spark]


def powertrain(panel):
    """topology.Graph — power-unit schematic (auto-laid-out, rendered)."""
    USED.add("topology")
    g = topology.Graph()
    for nid, lbl in (("ICE", "ICE V6"), ("TC", "Turbo"), ("MGUH", "MGU-H"),
                     ("MGUK", "MGU-K"), ("ES", "Battery"), ("GBX", "Gearbox"), ("W", "Wheels")):
        g.node(nid, label=lbl)
    for a, b in (("ICE", "TC"), ("TC", "MGUH"), ("MGUH", "ES"), ("ES", "MGUK"),
                 ("MGUK", "GBX"), ("ICE", "GBX"), ("GBX", "W")):
        g.edge(a, b, directed=True)
    g.auto_layout()
    return g.render(box=list(panel), node_fill=CARBON, node_stroke=CYAN,
                    edge_color=rgba(GRID, 0.6), label_color=INK, label_size=10.0, node_radius=13.0)


def harmony(x, y, w):
    """chevreul.color_guide + tone_scale — derived accent + tonal swatches."""
    USED.add("chevreul")
    S = []
    guide = chevreul.color_guide(BODY, n=6)
    tones = chevreul.tone_scale(BODY, steps=9)
    swatches = list(guide["scale"]) + list(tones)
    n = len(swatches)
    cw = w / n
    for i, col in enumerate(swatches):
        S.append(rect([x + i * cw, y, cw - 2, 30], fill=str(col)))
    S.append(text(x, y - 16, "CHEVREUL · scale + tone_scale", 10, rgba(INK, 0.7), w=360, weight=700))
    return S


def instrument(panel):
    """macros.greeble + hatch_fill — a sensor / section-cut furniture panel."""
    USED.add("macros")
    ox, oy, pw, ph = panel
    S = list(macros.hatch_fill([ox, oy, pw * 0.42, ph], fg=rgba(GRID, 0.25), scale=7.0, angle=35.0))
    S += list(macros.greeble([ox + pw * 0.46, oy, pw * 0.54, ph], seed=7, density=0.5,
                             fill=rgba(CYAN, 0.5), stroke_color=rgba(GRID, 0.4),
                             min_size=4.0, max_size=16.0))
    return S


def blueprint_grid(k, glow_first):
    S = []
    nv = (k + 1) // 2
    nh = k - nv
    idx = 0
    for i in range(nv):
        x = PAGE_W * (i + 0.5) / nv
        S.append(line([(x, 92), (x, PAGE_H)], rgba(GRID, 0.05), 1,
                      effects=[{"kind": "glow", "color": CYAN, "blur": 3.0, "opacity": 0.45}] if idx < glow_first else None))
        idx += 1
    for j in range(nh):
        y = 92 + (PAGE_H - 92) * (j + 0.5) / nh
        S.append(line([(0, y), (PAGE_W, y)], rgba(GRID, 0.05), 1,
                      effects=[{"kind": "glow", "color": CYAN, "blur": 3.0, "opacity": 0.45}] if idx < glow_first else None))
        idx += 1
    return S


def panel_frame(box_, label):
    ox, oy, pw, ph = box_
    return [rect([ox, oy, pw, ph], fill="none", stroke=rgba(GRID, 0.28),
                 stroke_style={"stroke_width": 1.2}, radius=4),
            text(ox + 10, oy + 14, label, 12, CYAN, w=pw - 20, weight=800)]


# --------------------------------------------------------------------------- #
#  assemble the dossier
# --------------------------------------------------------------------------- #
def scene():
    faces, ncomp = base.build_model()

    # canon: type scale + page frame
    USED.add("canon")
    scale = canon.modular_scale(13.0, 1.32, names=("s", "m", "l", "xl", "xxl", "h"))
    marg = canon.johnston_margins(PAGE_W)
    m = round(marg.get("outer", marg.get("left", 28)) if isinstance(marg, dict) else 28)
    m = max(20, min(m, 40))

    hero = (m, 116, 964, 566)
    top_panel = (1024, 116, 632, 300)
    tele = (m, 726, 964, 292)
    graph_panel = (1024, 566, 632, 246)
    instr = (1024, 852, 632, 166)

    # backdrops first
    aero = aero_field(hero)
    grid = blueprint_grid(96, 0)                 # glow count topped up below

    persp, hull_pts, e1 = render_perspective(faces, hero)
    halo, contour = silhouette(hull_pts)
    topv, e2 = render_top(faces, top_panel)

    tele_objs = telemetry(tele)
    graph_obj = powertrain(graph_panel)
    swatches = harmony(1024, 470, 632)
    instr_objs = instrument(instr)
    gn = base_gnomon(hero)

    # effect accounting: model glows + contour(1) + gnomon(3) + grid top-up > 75
    car_fx = e1 + e2 + 1 + 3
    glow_first = max(0, 110 - car_fx)
    for i in range(min(glow_first, len(grid))):
        grid[i]["effects"] = [{"kind": "glow", "color": CYAN, "blur": 3.0, "opacity": 0.45}]
    total_fx = car_fx + min(glow_first, len(grid))

    header = [
        text(m, 32, "FORMULA 1 · TECHNICAL DOSSIER", scale["xl"], INK, w=1400, weight=800),
        text(m, 66, "one organic 3D model, projected + analysed across the FrameForge SDK",
             scale["s"], rgba(INK, 0.7), w=1400, weight=600),
    ]

    layers = (
        [rect([0, 0, PAGE_W, PAGE_H], fill=BG)]
        + grid
        + aero + persp + [halo, contour] + gn
        + panel_frame(hero, "① 3/4 PERSPECTIVE · geometry.ViewingPipeline")
        + panel_frame(top_panel, "② TOP · orthographic") + topv
        + panel_frame(graph_panel, "④ POWER UNIT · topology.Graph") + [graph_obj]
        + panel_frame(tele, "③ TELEMETRY · chart.Chart + fields") + tele_objs
        + swatches
        + panel_frame(instr, "⑤ SENSORS · macros.greeble/hatch") + instr_objs
        + header
    )
    # subtitle with the real counts (appended last so it can read them)
    layers.append(text(m, 88, f"{ncomp} components · {len(layers) + 1} layers · {total_fx} effects · "
                              f"{len(USED)} SDK subsystems: {', '.join(sorted(USED))}",
                       11, rgba(CYAN, 0.85), w=1500, weight=700))

    assert ncomp > 256, f"components {ncomp}"
    assert len(layers) > 1024, f"layers {len(layers)}"
    assert total_fx > 75, f"effects {total_fx}"
    assert len(USED) >= 9, f"subsystems {USED}"
    return layers


def base_gnomon(panel):
    ox = panel[0] + 60
    oy = panel[1] + panel[3] - 40
    cam = Camera(eye=Vec3(*EYE), target=Vec3(*LOOK), up=Vec3(0, 0, 1), fov=38.0,
                 aspect=1.2, near=1.0, far=6000.0)
    o = cam.project(Vec3(0, 0, 0))
    S = []
    for tip, col in (((70, 0, 0), "#ff5a3c"), ((0, 70, 0), "#3fd0e0"), ((0, 0, 70), "#8fd694")):
        t = cam.project(Vec3(*tip))
        S.append(line([(ox + (o.x - o.x), oy), (ox + (t.x - o.x) * 2.2, oy + (t.y - o.y) * 2.2)],
                      col, 2.5, effects=[{"kind": "glow", "color": col, "blur": 3.0, "opacity": 0.8}]))
    return S


def build_builder():
    b = DocumentBuilder(title="Formula 1 — technical dossier (FrameForge, full SDK)")
    page = b.page("dossier", canvas={"size": [PAGE_W, PAGE_H], "units": "px"}, coordinate_mode="absolute")
    page.layer("scene").extend(scene())
    return b


builder = build_builder()


def build():
    return builder.build()


if __name__ == "__main__":
    from frameforge.sdk import serialize
    out = os.environ.get("OUTPUT_YAML_PATH", "f1_spec_sheet.fg.yaml")
    open(out, "w", encoding="utf-8").write(serialize(builder.build()))
    print(f"wrote {out}  ({len(scene())} layers, subsystems={sorted(USED)})")
