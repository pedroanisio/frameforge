#!/usr/bin/env python3
"""
render_pdf.py — combine a FrameGraph document's SVG pages into one PDF.

This reuses the repository SVG proxy (``tooling/render_fixtures.py``) to solve
each FrameGraph page to a standalone SVG, converts every page to a *vector* PDF
page with CairoSVG, and stitches them together with pypdf — one multi-page PDF
per document. PDF page size follows each SVG's canvas (width/height), so mixed
page sizes within a document are preserved.

It is the same SANITY-CHECK altitude as render_fixtures.py: CairoSVG paints
ordinary SVG, so browser-native effects (CSS filters, blend modes, backdrop
filters, SVG masks) are approximated, not guaranteed. For pixel-faithful effect
rendering, rasterize with tooling/render_chromium.py instead.

Setup (optional dependency group):
    uv sync --group pdfout      # CairoSVG + pypdf
    # or one-off, no sync:
    uv run --group pdfout python tooling/render_pdf.py fixtures/<doc>.fg.yaml

Usage:
    python3 tooling/render_pdf.py fixtures/inova-partners-whitepaper.fg.yaml
    python3 tooling/render_pdf.py 'fixtures/*.fg.yaml' --out out/pdf
    python3 tooling/render_pdf.py --all --max-pages 3
    python3 tooling/render_pdf.py fixtures/deck.fg.yaml --single book.pdf
    python3 tooling/render_pdf.py --list

By default one ``<stem>.pdf`` is written per document under --out (out/pdf/).
Pass --single FILE to merge every page of every selected document into a single
combined PDF instead.
"""
from __future__ import annotations

import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from tooling.render_fixtures import Renderer, discover, stem_of  # noqa: E402


class _MissingDependency(RuntimeError):
    """Raised when the optional CairoSVG / pypdf stack is unavailable."""


def _load_backends():
    """Import CairoSVG + pypdf lazily, with an actionable error if absent."""
    try:
        import cairosvg  # noqa: F401
        from pypdf import PdfWriter  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise _MissingDependency(
            "render_pdf needs CairoSVG and pypdf. Install them with "
            "`uv sync --group pdfout` (or `uv run --group pdfout python "
            "tooling/render_pdf.py ...`)."
        ) from exc
    return cairosvg, PdfWriter


def page_svgs(path, doc, *, max_pages=0, real_metrics=False):
    """Yield one solved SVG string per rendered page of ``doc``."""
    renderer = Renderer(
        doc, os.path.dirname(os.path.abspath(path)), real_metrics=real_metrics
    )
    count = 0
    for page in doc.get("pages", []):
        if not isinstance(page, dict):
            continue
        for svg in renderer.render_page(page):
            yield svg
            count += 1
            if max_pages and count >= max_pages:
                return


def svg_to_pdf_bytes(cairosvg, svg, *, base_dir):
    """Convert one SVG string to a single-page PDF (bytes).

    ``base_dir`` is passed as the resolution root so relative image hrefs in the
    SVG resolve against the document's directory; ``unsafe=True`` permits reading
    those local asset files.
    """
    url = (os.path.join(base_dir, "") if base_dir else None)
    return cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), url=url, unsafe=True)


def write_pdf(cairosvg, PdfWriter, svgs, out_path, *, base_dir, quiet=False):
    """Merge an iterable of SVG strings into one PDF at ``out_path``.

    Returns the number of pages written. Pages that fail to convert are skipped
    with a warning rather than aborting the whole document.
    """
    writer = PdfWriter()
    pages = 0
    for i, svg in enumerate(svgs, 1):
        try:
            pdf_bytes = svg_to_pdf_bytes(cairosvg, svg, base_dir=base_dir)
        except Exception as exc:  # noqa: BLE001 - one bad page must not kill the doc
            if not quiet:
                print(f"    ⚠ page {i}: SVG->PDF failed ({exc}); skipped",
                      file=sys.stderr)
            continue
        writer.append(io.BytesIO(pdf_bytes))
        pages += 1
    if not pages:
        writer.close()
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as fh:
        writer.write(fh)
    writer.close()
    return pages


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("paths", nargs="*",
                    help="files / dirs / globs (default: all fixtures/)")
    ap.add_argument("--all", action="store_true",
                    help="render every fixture under fixtures/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "pdf"),
                    help="output dir for per-document PDFs (default: out/pdf)")
    ap.add_argument("--single", metavar="FILE", default=None,
                    help="merge every page of every selected document into one "
                         "combined PDF at FILE instead of one PDF per document")
    ap.add_argument("--max-pages", type=int, default=0,
                    help="cap pages rendered per doc (0 = all)")
    ap.add_argument("--real-metrics", action="store_true",
                    help="wrap/fit text using real font advances (needs "
                         "fontTools) instead of the per-character estimate")
    ap.add_argument("--list", action="store_true",
                    help="list discoverable docs and exit")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    docs = discover([] if args.all else args.paths)
    if args.list:
        for f, _ in docs:
            print(os.path.relpath(f, ROOT))
        print(f"\n{len(docs)} document(s).")
        return 0
    if not docs:
        print("No FrameGraph documents found. Try: render_pdf.py --all",
              file=sys.stderr)
        return 1

    try:
        cairosvg, PdfWriter = _load_backends()
    except _MissingDependency as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.single:
        writer = PdfWriter()
        total = 0
        for f, doc in docs:
            stem = stem_of(f)
            base_dir = os.path.dirname(os.path.abspath(f))
            svgs = page_svgs(f, doc, max_pages=args.max_pages,
                             real_metrics=args.real_metrics)
            doc_pages = 0
            for i, svg in enumerate(svgs, 1):
                try:
                    pdf_bytes = svg_to_pdf_bytes(cairosvg, svg, base_dir=base_dir)
                except Exception as exc:  # noqa: BLE001
                    if not args.quiet:
                        print(f"  {stem} page {i}: SVG->PDF failed ({exc}); "
                              "skipped", file=sys.stderr)
                    continue
                writer.append(io.BytesIO(pdf_bytes))
                doc_pages += 1
            total += doc_pages
            if not args.quiet:
                print(f"  {stem}: {doc_pages} page(s)")
        if not total:
            print("No pages converted.", file=sys.stderr)
            writer.close()
            return 1
        os.makedirs(os.path.dirname(os.path.abspath(args.single)) or ".",
                    exist_ok=True)
        with open(args.single, "wb") as fh:
            writer.write(fh)
        writer.close()
        print(f"\nWrote {total} page(s) from {len(docs)} document(s) -> "
              f"{args.single}")
        return 0

    os.makedirs(args.out, exist_ok=True)
    total_pages, written = 0, 0
    for f, doc in docs:
        stem = stem_of(f)
        base_dir = os.path.dirname(os.path.abspath(f))
        out_path = os.path.join(args.out, f"{stem}.pdf")
        svgs = page_svgs(f, doc, max_pages=args.max_pages,
                         real_metrics=args.real_metrics)
        pages = write_pdf(cairosvg, PdfWriter, svgs, out_path,
                          base_dir=base_dir, quiet=args.quiet)
        if pages:
            written += 1
            total_pages += pages
            if not args.quiet:
                print(f"  {stem}: {pages} page(s) -> "
                      f"{os.path.relpath(out_path, ROOT)}")
        elif not args.quiet:
            print(f"  {stem}: no pages converted; skipped", file=sys.stderr)

    print(f"\nWrote {written}/{len(docs)} document(s), {total_pages} page(s) "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
