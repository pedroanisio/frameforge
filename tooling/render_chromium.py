#!/usr/bin/env python3
"""Rasterize FrameGraph documents through headless Chromium.

This renderer reuses the repository SVG proxy to produce one full-page SVG per
FrameGraph page, then asks Chromium (via Playwright) to rasterize that SVG to
PNG. It is the fidelity path for browser-native paint semantics: CSS filters,
blend modes, backdrop filters, masks and SVG filters.

Setup:
    uv sync --group browser
    uv run playwright install chromium

Usage:
    uv run python tooling/render_chromium.py fixtures/filters.fg.yaml --out out/chromium
    uv run python tooling/render_chromium.py --all --max-pages 1
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.infrastructure.browser import (  # noqa: E402
    BrowserRendererUnavailable,
    rasterize_svgs,
)
from tooling.render_fixtures import Renderer, discover, stem_of, write_index  # noqa: E402


def render_doc(path: str, doc: dict, out_dir: str, *, max_pages: int = 0, scale: float = 1.0) -> list[str]:
    """Render one normalized document to PNGs and return paths relative to ``out_dir``."""
    stem = stem_of(path)
    doc_dir = os.path.join(out_dir, stem)
    os.makedirs(doc_dir, exist_ok=True)
    renderer = Renderer(doc, os.path.dirname(os.path.abspath(path)))
    svgs = []
    for page in doc.get("pages", []):
        if not isinstance(page, dict):
            continue
        for svg in renderer.render_page(page):
            svgs.append(svg)
            if max_pages and len(svgs) >= max_pages:
                break
        if max_pages and len(svgs) >= max_pages:
            break
    paths = rasterize_svgs(
        svgs,
        doc_dir,
        base_dir=os.path.dirname(os.path.abspath(path)),
        scale=scale,
    )
    rels = [f"{stem}/{p.name}" for p in paths]
    write_index(doc_dir, [(stem, "", [p.name for p in paths])], f"FrameGraph Chromium — {stem}", page_links=True)
    return rels


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="files / dirs / globs (default: all fixtures/)")
    ap.add_argument("--all", action="store_true", help="render every fixture under fixtures/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "chromium"), help="output dir")
    ap.add_argument("--max-pages", type=int, default=0, help="cap pages rendered per doc (0 = all)")
    ap.add_argument("--scale", type=float, default=1.0, help="Chromium device scale factor")
    ap.add_argument("--list", action="store_true", help="list discoverable docs and exit")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    docs = discover([] if args.all else args.paths)
    if args.list:
        for f, _ in docs:
            print(os.path.relpath(f, ROOT))
        print(f"\n{len(docs)} document(s).")
        return 0
    if not docs:
        print("No FrameGraph documents found. Try: render_chromium.py --all", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    index_entries = []
    total_pages = 0
    try:
        for path, doc in docs:
            thumbs = render_doc(path, doc, args.out, max_pages=args.max_pages, scale=args.scale)
            stem = stem_of(path)
            index_entries.append((stem, f"{stem}/index.html", thumbs))
            total_pages += len(thumbs)
            if not args.quiet:
                print(f"  {stem}: {len(thumbs)} page(s)")
    except BrowserRendererUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2

    write_index(args.out, index_entries, "FrameGraph fixtures — Chromium raster contact sheet")
    print(f"\nRendered {len(docs)} document(s), {total_pages} page(s) -> {args.out}")
    print(f"Open {os.path.join(args.out, 'index.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
