#!/usr/bin/env python3
"""Psychedelic hyperrealist recoloration of ``canvas.svg`` as a FrameForge document.

The source is a hand-drawn isometric cube tessellation: ~3,600 pen strokes in a
single periwinkle ink (#7c74ff), packed as six embedded data-URI SVG layers.
This client rebuilds every stroke as a native FrameForge polyline and replaces
the monochrome ink with a *psychedelic coloration model*:

    hue        a spiral field — angle around the panel centre + radius drift,
               phase-shifted per source layer so overlapping hatching shimmers
    lightness  sinusoidal banding over radius (iridescent interference rings)
    ground     near-black indigo + three user-space radial nebula washes
    finish     Page.post bloom (neon halo) + seeded film grain (hyperreal noise
               floor) — raster-stage, applied by the PNG target

Deterministic: same input, same document.

    uv run python static/examples/psychedelic_canvas.py
    uv run python tooling/frameforge_render.py out/psychedelic_canvas/psychedelic_canvas.fg.yaml --to png --out out/psychedelic_canvas

AI-generated (Claude Opus 4.8 via Claude Code); geometry is sourced verbatim
from canvas.svg — only paint is synthesized.
"""
from __future__ import annotations

import colorsys
import math
import os
import re
import sys
import urllib.parse

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402

W = H = 1080
SOURCE = os.path.join(ROOT, "canvas.svg")
OUT_DIR = os.path.join(ROOT, "out", "psychedelic_canvas")

# Spiral field centre = optical centre of the drawn cube panel (canvas px).
CX, CY = 402.0, 516.0


# --------------------------------------------------------------------------- #
#  Source geometry: decode the six embedded SVG layers                         #
# --------------------------------------------------------------------------- #
def load_layers(path: str):
    """Yield (layer_index, sx, sy, [ [ (x,y), ... ], ... ]) in canvas coords."""
    src = open(path, encoding="utf-8").read()
    images = re.findall(
        r'<image x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"'
        r'[^>]*xlink:href="data:image/svg\+xml;charset=utf-8,([^"]+)"', src)
    layers = []
    for idx, (x, y, w, h, data) in enumerate(images):
        inner = urllib.parse.unquote(data)
        vb = re.search(r'viewBox="([^"]+)"', inner)
        vx, vy, vw, vh = (float(v) for v in vb.group(1).split())
        sx, sy = float(w) / vw, float(h) / vh
        ox, oy = float(x) - vx * sx, float(y) - vy * sy
        polys = []
        for pts_attr in re.findall(r'<polyline points="([^"]+)"', inner):
            pts = []
            for pair in pts_attr.split():
                px, py = pair.split(",")
                pts.append((ox + float(px) * sx, oy + float(py) * sy))
            if len(pts) >= 2:
                polys.append(pts)
        if polys:
            layers.append((idx, sx, sy, polys))
    return layers


def decimate(pts, tol=0.15):
    """Drop near-collinear interior points (perpendicular distance < tol px)."""
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p, a, b = pts[i], out[-1], pts[i + 1]
        # cheap local test against the chord (prev-kept -> next-source point)
        abx, aby = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(abx, aby)
        d = abs((p[0] - a[0]) * aby - (p[1] - a[1]) * abx) / norm if norm > 1e-9 else 0.0
        if d >= tol:
            out.append(p)
    out.append(pts[-1])
    return out


# --------------------------------------------------------------------------- #
#  Region detection: enclosed faces of the ink lattice                         #
# --------------------------------------------------------------------------- #
def _is_texture(pts) -> bool:
    """Long straight hatch/grid strokes — texture, not lattice structure."""
    x0, y0 = pts[0]
    x1, y1 = pts[-1]
    chord = math.hypot(x1 - x0, y1 - y0)
    arc = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
              for i in range(len(pts) - 1))
    if chord < 12 or arc <= 0 or chord / arc < 0.88:
        return False
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180
    if 115 <= ang <= 155:                                       # diagonal shading hatch
        return True
    return chord > 26 and (ang <= 8 or ang >= 172 or 82 <= ang <= 98)  # long grid texture


def detect_regions(layers, *, scale=2.0, seal_px=3.0, min_area=200.0, max_area=22000.0):
    """Fillable face polygons enclosed by the STRUCTURAL ink, in canvas coords.

    Texture strokes (diagonal shading hatch, long straight grid lines) are
    excluded from the mask — they subdivide faces into slivers; the lattice
    edges remain. The free space is then labelled and the components whose
    size/solidity say "cube face" (not background, not pinhole) are traced.
    Deterministic: pure geometry in, sorted polygons out.
    """
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw

    w, h = int(W * scale), int(H * scale)
    mask = Image.new("L", (w, h), 255)
    dr = ImageDraw.Draw(mask)
    lw = max(1, round(seal_px * scale / 2.0))
    for _, _, _, polys in layers:
        for pts in polys:
            if _is_texture(pts):
                continue
            dr.line([(x * scale, y * scale) for x, y in pts], fill=0, width=lw)
    free = (np.asarray(mask) > 127).astype(np.uint8)

    n, lab, stats, cent = cv2.connectedComponentsWithStats(free, connectivity=4)
    regions = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        a = area / (scale * scale)
        if not (min_area <= a <= max_area):
            continue
        if x == 0 or y == 0 or x + bw >= w or y + bh >= h:      # touches border
            continue
        comp = (lab[y:y + bh, x:x + bw] == i).astype(np.uint8)
        cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        hull = cv2.convexHull(c)
        ha = cv2.contourArea(hull)
        if ha <= 0 or cv2.contourArea(c) / ha < 0.6:            # ragged leak, not a face
            continue
        c = cv2.approxPolyDP(c, 1.2 * scale, True)
        if len(c) < 3:
            continue
        poly = [((x + px) / scale, (y + py) / scale) for px, py in c[:, 0, :].tolist()]
        regions.append((a, (cent[i][0] / scale, cent[i][1] / scale), poly))
    regions.sort(key=lambda r: (round(r[1][1], 1), round(r[1][0], 1)))
    return regions


# --------------------------------------------------------------------------- #
#  Psychedelic coloration model                                                #
# --------------------------------------------------------------------------- #
def stroke_color(pts, phase_deg: float) -> str:
    """Spiral-field hue + iridescent lightness banding at the stroke centroid."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    dx, dy = cx - CX, cy - CY
    r = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    hue = (ang + r * 0.55 + phase_deg) % 360.0
    light = 0.58 + 0.14 * math.sin(r / 26.0)
    rgb = colorsys.hls_to_rgb(hue / 360.0, light, 0.92)
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in rgb)


def face_paint(centroid) -> tuple[str, float]:
    """Translucent face fill from the same spiral field, hue-offset +150°."""
    dx, dy = centroid[0] - CX, centroid[1] - CY
    r = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    hue = (ang + r * 0.55 + 150.0) % 360.0
    light = 0.52 + 0.10 * math.sin(r / 26.0 + 1.7)
    rgb = colorsys.hls_to_rgb(hue / 360.0, light, 1.0)
    color = "#%02x%02x%02x" % tuple(round(c * 255) for c in rgb)
    opacity = 0.44 + 0.14 * math.sin(r / 41.0)          # breathing translucency
    return color, round(opacity, 3)


def keep_face(centroid, fraction=0.62) -> bool:
    """Deterministic 'some': hash the centroid, keep ~fraction of the faces."""
    import hashlib
    key = f"{centroid[0]:.0f},{centroid[1]:.0f}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:2], "big") / 65535.0 < fraction


def radial(at, radius, stops):
    return {"kind": "radial", "at": list(at), "radius": radius,
            "stops": [{"color": c, "position": f"{p:g}%", "opacity": o} for c, p, o in stops]}


# --------------------------------------------------------------------------- #
#  Document                                                                    #
# --------------------------------------------------------------------------- #
def build():
    layers = load_layers(SOURCE)
    n_strokes = sum(len(p) for _, _, _, p in layers)
    n_pts_src = sum(len(pts) for _, _, _, polys in layers for pts in polys)

    b = DocumentBuilder(title="canvas — psychedelic hyperrealist recoloration")
    page = b.page(
        "art",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
        post={
            "bloom": {"radius": 9.0, "strength": 0.6, "threshold": 0.5},
            "grain": {"amount": 0.035, "seed": 7, "monochrome": True},
        },
        notes="Geometry sourced verbatim from canvas.svg; paint synthesized "
              "(spiral hue field, per-layer phase, radial nebula ground, "
              "raster bloom + grain).",
    )

    # -- ground: deep space + nebula washes -------------------------------- #
    bg = page.layer("00_ground")
    bg.add({"type": "rect", "id": "ground", "box": [0, 0, W, H],
            "fill": "#050208", "decorative": True})
    bg.add({"type": "rect", "id": "nebula_core", "box": [0, 0, W, H],
            "decorative": True,
            "fill": radial((CX, CY), 640, [
                ("#3d1160", 0, 0.95), ("#241047", 45, 0.55), ("#0b0316", 100, 0.0)])})
    bg.add({"type": "rect", "id": "nebula_cyan", "box": [0, 0, W, H],
            "decorative": True,
            "fill": radial((980, 160), 520, [
                ("#0a4d5d", 0, 0.55), ("#083344", 55, 0.25), ("#050208", 100, 0.0)])})
    bg.add({"type": "rect", "id": "nebula_ember", "box": [0, 0, W, H],
            "decorative": True,
            "fill": radial((120, 980), 560, [
                ("#5d1a3a", 0, 0.5), ("#3a1030", 55, 0.25), ("#050208", 100, 0.0)])})

    # -- region fills: enclosed lattice faces, translucent psychedelic ------- #
    regions = detect_regions(layers)
    fills = page.layer("05_region_fills")
    n_filled = 0
    for j, (area, centroid, poly) in enumerate(regions):
        if not keep_face(centroid):
            continue
        color, op = face_paint(centroid)
        fills.add({
            "type": "polyline",
            "id": f"face_{j}",
            "points": [[round(x, 2), round(y, 2)] for x, y in poly],
            "closed": True,
            "fill": color,
            "decorative": True,
            "style": {"opacity": op, "mix_blend_mode": "screen"},
        })
        n_filled += 1

    # -- ink: every source stroke, psychedelically recolored ---------------- #
    n_pts_kept = 0
    for idx, sx, sy, polys in layers:
        phase = idx * 24.0                       # per-layer hue phase shift
        width = round(max(1.05, 1.9 * (sx + sy) / 2.0), 2)
        ink = page.layer(f"1{idx}_ink_l{idx}")
        for k, pts in enumerate(polys):
            pts = decimate(pts)
            n_pts_kept += len(pts)
            ink.add({
                "type": "polyline",
                "id": f"s{idx}_{k}",
                "points": [[round(x, 2), round(y, 2)] for x, y in pts],
                "stroke": stroke_color(pts, phase),
                "decorative": True,
                "style": {"stroke_width": width, "stroke_linecap": "round",
                          "stroke_linejoin": "round", "opacity": 0.88},
            })

    # -- vignette: hyperrealist edge falloff -------------------------------- #
    vg = page.layer("90_vignette")
    vg.add({"type": "rect", "id": "vignette", "box": [0, 0, W, H],
            "decorative": True,
            "fill": radial((W / 2, H / 2), 860, [
                ("#000000", 0, 0.0), ("#000000", 62, 0.0), ("#000000", 100, 0.55)])})

    doc = b.build()

    os.makedirs(OUT_DIR, exist_ok=True)
    import yaml
    data = doc.model_dump(mode="json", by_alias=True, exclude_none=True)
    yaml_path = os.path.join(OUT_DIR, "psychedelic_canvas.fg.yaml")
    with open(yaml_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=None, width=1000)

    svg = render_page_svgs(doc)[0]
    svg_path = os.path.join(OUT_DIR, "psychedelic_canvas.svg")
    with open(svg_path, "w", encoding="utf-8") as fh:
        fh.write(svg)

    print(f"[source] {len(layers)} layers, {n_strokes} strokes, "
          f"{n_pts_src} pts -> {n_pts_kept} kept ({100 * n_pts_kept / n_pts_src:.0f}%)")
    print(f"[regions] {len(regions)} faces detected, {n_filled} filled "
          f"({100 * n_filled / max(1, len(regions)):.0f}%)")
    print(f"[write] {yaml_path}")
    print(f"[write] {svg_path}  ({len(svg) // 1024} KiB)")
    ok = svg.startswith("<svg") and n_strokes > 3000
    print(f"\nVERDICT: {'psychedelic recoloration built' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(build())
