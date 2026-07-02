#!/usr/bin/env python3
"""Animate an ingested SVG into a video clip (mp4 / gif).

Pipeline, per frame: ingest the SVG once → recolour every fill by a hue that
advances with time and a value keyed to the path's luminance → wrap the drawing
in a ``place_region`` group transformed (a gentle rotate-pendulum + zoom breathing)
→ render to FrameGraph SVG → rasterise to PNG with CairoSVG → ffmpeg stitches the
PNGs into a clip. The loop is seamless (every animated quantity is periodic over
the frame count).

Only geometry + solid fills are animated, because the CairoSVG rasteriser renders
those faithfully without a browser; browser-only CSS paint (blur/hue-rotate filters,
blend modes) is deliberately avoided so every frame is reproducible.

Run::

    uv run python examples/animate_svg.py --svg dkss_multipass_report.svg \\
        --out out/anim/dkss --frames 48 --fps 24 --gif

Requires ffmpeg on PATH and CairoSVG (the `mcp`/`pdfout` dependency group).
"""
from __future__ import annotations

import argparse
import colorsys
import math
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, Mat3, place_region, render_page_svgs  # noqa: E402
from framegraph.rendering.infrastructure.cairo import rasterize_svg_cairo  # noqa: E402
from framegraph.vision.infrastructure.svg_import import svg_to_objects  # noqa: E402

_NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _luminance(hex_color: str) -> float | None:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def _hex(r: float, g: float, b: float) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v * 255))) for v in (r, g, b))


def _viewbox(svg_path: str) -> tuple[float, float]:
    head = open(svg_path, encoding="utf-8").read(600)
    m = re.search(r'viewBox="([^"]+)"', head)
    if m:
        p = [float(x) for x in _NUM.findall(m.group(1))]
        if len(p) == 4:
            return p[2], p[3]
    w = re.search(r'width="([\d.]+)', head)
    h = re.search(r'height="([\d.]+)', head)
    return (float(w.group(1)) if w else 1000.0, float(h.group(1)) if h else 1000.0)


def _recolor(objs, lums, phase, saturation):
    """A hue-cycling, luminance-aware palette for one frame."""
    out = []
    for obj, lum in zip(objs, lums):
        no = dict(obj)
        if lum is not None:
            hue = (phase + 0.12 * lum) % 1.0
            value = 0.16 + 0.80 * lum
            no["fill"] = _hex(*colorsys.hsv_to_rgb(hue, saturation, value))
        out.append(no)
    return out


def _frame_doc(objs, lums, w, h, t, *, sway, zoom, sat, bg):
    """Build one frame: recoloured drawing under a rotate-pendulum + zoom breathing."""
    phase_angle = sway * math.sin(2 * math.pi * t)
    scale = 1.0 + zoom * (0.5 - 0.5 * math.cos(2 * math.pi * t))   # 1.0 -> 1+zoom -> 1.0
    transform = Mat3.rotate(phase_angle) @ Mat3.scale(scale)
    colored = _recolor(objs, lums, t, sat)
    b = DocumentBuilder(title="frame", lang="en")
    p = b.page("f", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    p.rect([0, 0, w, h], fill=bg)
    p.add(place_region(colored, [0, 0, w, h], [0, 0, w, h], transform=transform, clip=True))
    return b.build()


def _frame_construct(objs, order, w, h, count, prev, *, bg, edge, edge_w):
    """Reveal ``objs`` up to ``count`` (in ``order``); the batch since ``prev`` gets an edge."""
    b = DocumentBuilder(title="frame", lang="en")
    p = b.page("f", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    p.rect([0, 0, w, h], fill=bg)
    lyr = p.layer("ink")
    with lyr.bleed():
        for rank in range(count):
            o = dict(objs[order[rank]])
            if rank >= prev:                         # freshly drawn this frame → active edge
                o["stroke"] = edge
                o["stroke_style"] = {"stroke_width": edge_w}
            lyr.add(o)
    return b.build()


def _reveal_order(objs, lums, how):
    """Index order in which patches appear: document / large-first / dark-first."""
    idx = list(range(len(objs)))
    if how == "area":
        def area(o):
            n = [float(x) for x in _NUM.findall(o.get("d", ""))]
            xs, ys = n[0::2], n[1::2]
            return (max(xs) - min(xs)) * (max(ys) - min(ys)) if xs else 0.0
        idx.sort(key=lambda i: area(objs[i]), reverse=True)
    elif how == "luma":
        idx.sort(key=lambda i: (lums[i] if lums[i] is not None else 1.0))
    return idx


def _encode_mp4(frames_glob_dir: str, fps: int, out_mp4: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
         "-i", os.path.join(frames_glob_dir, "f%04d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", out_mp4],
        check=True,
    )


def _encode_gif(frames_glob_dir: str, fps: int, width: int, out_gif: str) -> None:
    pattern = os.path.join(frames_glob_dir, "f%04d.png")
    palette = os.path.join(frames_glob_dir, "_palette.png")
    vf = f"fps={fps},scale={width}:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", pattern,
                    "-vf", vf + ",palettegen", palette], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", pattern, "-i", palette,
                    "-lavfi", vf + " [x];[x][1:v]paletteuse", "-loop", "0", out_gif], check=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--svg", required=True, help="source .svg (path relative to repo root or absolute)")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "anim", "clip"),
                    help="output basename (writes <out>.mp4 and, with --gif, <out>.gif)")
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--scale", type=float, default=1.0, help="raster scale (1.0 = source px)")
    ap.add_argument("--sway", type=float, default=7.0, help="rotation pendulum amplitude (deg)")
    ap.add_argument("--zoom", type=float, default=0.08, help="zoom-breathing amplitude (fraction)")
    ap.add_argument("--sat", type=float, default=0.55, help="colour saturation (0..1)")
    ap.add_argument("--bg", default="#0a0a12", help="background colour")
    ap.add_argument("--gif", action="store_true", help="also emit a GIF")
    ap.add_argument("--gif-width", type=int, default=360)
    ap.add_argument("--mode", choices=("transform", "construct"), default="transform")
    ap.add_argument("--order", choices=("doc", "area", "luma"), default="doc",
                    help="construct mode: order patches appear in")
    ap.add_argument("--edge", default="#ff3d81", help="construct mode: active-front edge colour")
    ap.add_argument("--edge-width", type=float, default=0.8)
    ap.add_argument("--bg-construct", default="#ffffff", help="construct mode background")
    ap.add_argument("--hold", type=int, default=12, help="construct mode: frames to hold the finished image")
    args = ap.parse_args(argv)

    svg_path = args.svg if os.path.isabs(args.svg) else os.path.join(ROOT, args.svg)
    if not os.path.exists(svg_path):
        ap.error(f"svg not found: {svg_path}")
    if shutil.which("ffmpeg") is None:
        ap.error("ffmpeg not found on PATH")

    objs = svg_to_objects(svg_path)
    lums = [_luminance(o["fill"]) if isinstance(o.get("fill"), str) and o["fill"].startswith("#") else None
            for o in objs]
    w, h = _viewbox(svg_path)
    print(f"ingested {len(objs)} objects · canvas {int(w)}x{int(h)} · {args.frames} frames @ {args.fps}fps")

    out_dir = os.path.dirname(os.path.abspath(args.out)) or "."
    os.makedirs(out_dir, exist_ok=True)
    frames_dir = os.path.abspath(args.out) + "_frames"
    if os.path.isdir(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    def _save(idx, model):
        svg = render_page_svgs(model)[0]
        rasterize_svg_cairo(svg, os.path.join(frames_dir, f"f{idx:04d}.png"), scale=args.scale)

    if args.mode == "construct":
        order = _reveal_order(objs, lums, args.order)
        n = len(objs)
        prev = 0
        for i in range(args.frames):
            count = round(n * (i + 1) / args.frames)
            _save(i, _frame_construct(objs, order, w, h, count, prev,
                                      bg=args.bg_construct, edge=args.edge, edge_w=args.edge_width))
            prev = count
            if (i + 1) % 12 == 0 or i + 1 == args.frames:
                print(f"  built {count}/{n} patches  (frame {i + 1}/{args.frames})")
        last = os.path.join(frames_dir, f"f{args.frames - 1:04d}.png")
        _save(args.frames - 1, _frame_construct(objs, order, w, h, n, n,           # final, no edge
                                                bg=args.bg_construct, edge="none", edge_w=0))
        for hwhich in range(args.hold):                                            # hold the finished image
            shutil.copyfile(last, os.path.join(frames_dir, f"f{args.frames + hwhich:04d}.png"))
    else:
        for i in range(args.frames):
            t = i / args.frames                              # 0..1, periodic
            _save(i, _frame_doc(objs, lums, w, h, t, sway=args.sway, zoom=args.zoom, sat=args.sat, bg=args.bg))
            if (i + 1) % 12 == 0 or i + 1 == args.frames:
                print(f"  rendered {i + 1}/{args.frames}")

    out_mp4 = os.path.abspath(args.out) + ".mp4"
    _encode_mp4(frames_dir, args.fps, out_mp4)
    print("wrote", os.path.relpath(out_mp4, ROOT))
    if args.gif:
        out_gif = os.path.abspath(args.out) + ".gif"
        _encode_gif(frames_dir, args.fps, args.gif_width, out_gif)
        print("wrote", os.path.relpath(out_gif, ROOT))
    shutil.rmtree(frames_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
