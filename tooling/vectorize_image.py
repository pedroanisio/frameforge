#!/usr/bin/env python3
"""CLI: a raster image → a layered FrameGraph vector base.

Wraps the ingestion front-end (``framegraph.vision.infrastructure.vectorize``)
into a one-shot "drop a raster, get an editable FrameGraph document" command. The
result is layered — a ``region`` fill base, an ``outline`` line layer, and an OCR
``text`` layer — so each can be edited or restyled independently.

    uv run --group vision python tooling/vectorize_image.py demo/scene.jpeg \
        --out out/scene.fg.yaml --modes region,outline --colors 14

Needs the optional ``vision`` group (OpenCV; Tesseract for the OCR layer).
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from framegraph.sdk import DocumentBuilder  # noqa: E402
from framegraph.vision.infrastructure.vectorize import (  # noqa: E402
    ocr_text_objects,
    raster_to_objects,
)


def build_document(image, *, modes=("region",), colors=12, detail=0.004,
                   min_area=60.0, max_dim=1100, ocr=True, title=None):
    """Build a layered FrameGraph DocumentBuilder from a raster image."""
    builder = DocumentBuilder(title=title or os.path.basename(str(image)))
    layers: list[tuple[str, list]] = []
    w = h = None
    for mode in modes:
        objs, w, h = raster_to_objects(image, mode=mode, colors=colors, detail=detail,
                                       min_area=min_area, max_dim=max_dim)
        layers.append((mode, objs))
    text = ocr_text_objects(image, max_dim=max_dim) if ocr else []
    if w is None:
        from framegraph.vision.infrastructure.vectorize import image_size
        w, h = image_size(image)
    page = builder.page("traced", canvas={"size": [w, h], "units": "px"},
                        coordinate_mode="absolute")
    for mode, objs in layers:
        layer = page.layer(mode)
        for o in objs:
            layer.add(o)
    if text:
        layer = page.layer("text")
        for o in text:
            layer.add(o)
    n_obj = sum(len(objs) for _, objs in layers) + len(text)
    return builder, len(text), n_obj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="source raster (png/jpg/...)")
    ap.add_argument("--out", default=None, help="write FrameGraph YAML here")
    ap.add_argument("--svg-out", default=None, help="also render the first page to this SVG")
    ap.add_argument("--modes", default="region", help="comma list: region,outline")
    ap.add_argument("--colors", type=int, default=12, help="region: quantised colour count")
    ap.add_argument("--detail", type=float, default=0.004, help="approxPolyDP epsilon fraction")
    ap.add_argument("--min-area", type=float, default=60.0, help="drop contours below this area")
    ap.add_argument("--max-dim", type=int, default=1100, help="downscale longest side to this")
    ap.add_argument("--no-ocr", action="store_true", help="skip the OCR text layer")
    args = ap.parse_args(argv)

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    builder, n_text, n_obj = build_document(args.image, modes=modes, colors=args.colors,
                                            detail=args.detail, min_area=args.min_area,
                                            max_dim=args.max_dim, ocr=not args.no_ocr)
    n_layers = len(modes) + (1 if n_text else 0)
    print(f"traced {args.image}: {n_obj} objects across {n_layers} layer(s) "
          f"({', '.join(modes)}{', text' if n_text else ''})")
    if args.out:
        builder.write(args.out)
        print(f"  wrote {args.out}")
    if args.svg_out:
        from framegraph.sdk import render_page_svgs
        os.makedirs(os.path.dirname(os.path.abspath(args.svg_out)), exist_ok=True)
        with open(args.svg_out, "w", encoding="utf-8") as fh:
            fh.write(render_page_svgs(builder.build())[0])
        print(f"  wrote {args.svg_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
