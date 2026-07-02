"""Rebuild every demo/ raster as a FrameGraph file — auto-routed vector ingest.

Each raster is classified (line-art vs colour illustration) and ingested with the
mode that suits it, then emitted as a native-size FrameGraph document:

  * line-art  → ``outline`` strokes on a white ground  (the drawing as editable lines)
  * colour    → ``region`` posterised colour fills      (the picture as editable shapes)

The result is a real ``*.fg.yaml`` per image (validatable, restyle-able, composable)
plus a contact-sheet gallery. The same files render through the FrameGraph MCP
(``run_sdk_client`` imports this module's ``doc``; ``render_framegraph_yaml`` takes any
emitted YAML; ``propose_from_image`` is the MCP-native vision lane over the same images).

Run (needs the vision group):
    uv run --group vision python examples/demo_rebuild.py --out out/demo_rebuild
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get("FG_ROOT", ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framegraph.sdk import DocumentBuilder, render_page_svgs, validate_static_rules  # noqa: E402
from framegraph.vision.infrastructure.vectorize import raster_to_objects  # noqa: E402
from poc3_ingest_compose import place, restyle_strokes  # noqa: E402

FONT = ["Inter", "Helvetica", "Arial", "sans-serif"]
DEMO = os.path.join(ROOT, "demo")
_RASTER = (".jpeg", ".jpg", ".png", ".webp")

# Per-route ingest parameters.
_PARAMS = {
    "lineart":      dict(modes=("outline",), colors=8,  detail=0.0016, min_area=22.0, max_dim=1500),
    "illustration": dict(modes=("region",),  colors=20, detail=0.0032, min_area=44.0, max_dim=1300),
}


def classify(path: str, max_dim: int = 700) -> str:
    """Route a raster: high white fraction + few colours + thin ink → line-art."""
    import cv2
    import numpy as np
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return "illustration"
    h, w = img.shape[:2]
    s = max_dim / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    white = float((g >= 235).mean())
    dark = float((g <= 90).mean())
    colors = len(np.unique((img >> 4).reshape(-1, 3), axis=0))
    return "lineart" if (white >= 0.45 and colors < 2200 and dark < 0.22) else "illustration"


def _load_path(path: str) -> str | None:
    """Return a cv2-readable path; convert an .avif/.webp via Pillow if needed."""
    import cv2
    if cv2.imread(path, cv2.IMREAD_COLOR) is not None:
        return path
    try:                                          # last resort: Pillow → PNG in scratch
        from PIL import Image
        out = os.path.join(SCRATCH, os.path.splitext(os.path.basename(path))[0] + ".png")
        Image.open(path).convert("RGB").save(out)
        return out if cv2.imread(out, cv2.IMREAD_COLOR) is not None else None
    except Exception:
        return None


SCRATCH = os.path.join(ROOT, "out", "demo_rebuild", "_conv")


def build_one(path: str):
    """Ingest one raster into a native-size FrameGraph rebuild."""
    route = classify(path)
    p = _PARAMS[route]
    by_mode, w, h = {}, None, None
    for mode in p["modes"]:
        objs, w, h = raster_to_objects(path, mode=mode, colors=p["colors"], detail=p["detail"],
                                       min_area=p["min_area"], max_dim=p["max_dim"])
        by_mode[mode] = objs
    b = DocumentBuilder(title=os.path.basename(path))
    page = b.page("rebuilt", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    if route == "lineart":
        page.rect([0, 0, w, h], fill="#FFFFFF")           # ground for the ink
    for mode in p["modes"]:
        layer = page.layer(mode)
        objs = by_mode[mode]
        if route == "lineart":
            objs = restyle_strokes(objs, stroke="#141A24", width=1.1)
        for o in objs:
            layer.add(o)
    n = sum(len(v) for v in by_mode.values())
    return b, route, (w, h), n


def _demo_rasters() -> list[str]:
    return sorted(f for f in glob.glob(os.path.join(DEMO, "*"))
                  if f.lower().endswith(_RASTER) or f.lower().endswith(".avif"))


def build_gallery(paths: Sequence[str], *, cols: int = 4, cell=(360, 300), gmax_dim: int = 480):
    """Contact sheet: every rebuild placed in a grid (one MCP-renderable doc)."""
    cw, ch, pad, top = cell[0], cell[1], 20, 52
    n = len(paths)
    rows = (n + cols - 1) // cols
    W = cols * cw + (cols + 1) * pad
    H = top + rows * ch + (rows + 1) * pad
    b = DocumentBuilder(title="demo-rebuild-gallery")
    page = b.page("gallery", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.add({"type": "text", "box": [pad, 16, W - 2 * pad, 28],
              "text": f"demo/ rebuilt as FrameGraph — {n} rasters, auto-routed (line-art→outline · colour→region)",
              "style": {"font_family": FONT, "font_size": 18, "font_weight": 800, "color": "#F2F5FA"}})
    for i, path in enumerate(paths):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = top + pad + r * (ch + pad)
        page.add({"type": "rect", "box": [x, y, cw, ch], "fill": "#FFFFFF", "radius": 8})
        route = classify(path)
        p = dict(_PARAMS[route]); p["max_dim"] = gmax_dim
        try:
            objs, w, h = raster_to_objects(path, mode=p["modes"][0], colors=p["colors"],
                                           detail=p["detail"], min_area=p["min_area"], max_dim=gmax_dim)
        except Exception:
            objs, w, h = [], gmax_dim, gmax_dim
        if route == "lineart":
            objs = restyle_strokes(objs, stroke="#141A24", width=1.0)
        lay = page.layer(f"cell{i}")
        for o in place(objs, [x + 8, y + 30, cw - 16, ch - 40], (w, h)):
            lay.add(o)
        tag = "outline" if route == "lineart" else "region"
        lay.add({"type": "text", "box": [x + 10, y + 8, cw - 20, 18],
                 "text": f"{os.path.basename(path)[:30]}  · {tag}",
                 "style": {"font_family": FONT, "font_size": 11, "font_weight": 700,
                           "color": "#1F6FEB" if route == "lineart" else "#C2143B"}})
    return b


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "demo_rebuild"))
    ap.add_argument("--no-gallery", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)

    paths = _demo_rasters()
    print(f"rebuilding {len(paths)} demo rasters → {args.out}")
    print(f"  {'file':<46}{'route':>13}{'objs':>7}{'canvas':>13}  validate")
    ok_all = True
    for path in paths:
        usable = _load_path(path)
        if usable is None:
            print(f"  {os.path.basename(path)[:44]:<46}{'(unreadable)':>13}")
            continue
        b, route, (w, h), n = build_one(usable)
        report = validate_static_rules(b.build())
        ok_all = ok_all and report.ok
        name = os.path.splitext(os.path.basename(path))[0][:60]
        b.write(os.path.join(args.out, f"{name}.fg.yaml"))
        with open(os.path.join(args.out, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(render_page_svgs(b.build())[0])
        print(f"  {os.path.basename(path)[:44]:<46}{route:>13}{n:>7}{f'{w}x{h}':>13}  "
              f"{'clean' if report.ok else str(len(report.issues)) + ' issue(s)'}")

    if not args.no_gallery:
        gal = build_gallery([p for p in paths if _load_path(p)])
        grep = validate_static_rules(gal.build())
        gal.write(os.path.join(args.out, "gallery.fg.yaml"))
        with open(os.path.join(args.out, "gallery.svg"), "w", encoding="utf-8") as fh:
            fh.write(render_page_svgs(gal.build())[0])
        print(f"  gallery.fg.yaml + gallery.svg  validate: {'clean' if grep.ok else 'issues'}")
    print(f"\nVERDICT: {'all rebuilt + validated clean' if ok_all else 'some pages had validation issues'}")
    return 0 if ok_all else 1


# Module-level doc for the MCP `run_sdk_client` import path: a fast 4-up sample.
def _sample_doc():
    picks = [
        "Gemini_Generated_Image_1h4no51h4no51h4n.jpeg",   # colour cityscape
        "51f60860-ddb4-414d-8f48-e11831b839e7.jpeg",      # grayscale teamwork scene
        "ChatGPT Image Jun 25, 2026, 01_21_30 PM.png",    # character turnaround
        "Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg",   # office line-art
    ]
    paths = [os.path.join(DEMO, p) for p in picks if os.path.exists(os.path.join(DEMO, p))]
    return build_gallery(paths or _demo_rasters()[:4], cols=2, cell=(440, 320), gmax_dim=560)


doc = _sample_doc()


if __name__ == "__main__":
    sys.exit(main())
