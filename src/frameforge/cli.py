#!/usr/bin/env python3
"""frameforge.cli — the FrameForge render front-door: choose a target, dispatch a backend.

The project ships several render paths; this is the single CLI over all of them.
``--list`` shows every target — what it produces, the optional dependency it
needs, and whether it is available *right now* — so you can choose how to render:

    python -m frameforge.cli <doc.fg.yaml> --to <target> [--out DIR]
    frameforge-render <doc.fg.yaml> --to pdf            # the installed entry point

Targets (see ``--list``):
  svg      vector SVG — the primary, dependency-free proxy
  png      raster PNG via headless Chromium (CSS fidelity)            [browser]
  pdf      vector PDF via CairoSVG (SVG→PDF, exact vector)            [pdfout]
  pdf-tex  typeset PDF via LaTeX/TikZ (TeX owns pagination + math)    [lua/pdflatex]
  tex      LaTeX/TikZ source (.tex, no compile)
  html     HTML/CSS (legacy; flow + gradient limits)

Every target renders *through the package*, in-process. The core targets (svg,
png, pdf, tex) go through the SVG proxy / Chromium rasteriser / LaTeX transpiler;
the html and pdf-tex targets go through the `DocumentRenderer` output port
(``frameforge.rendering.domain.ports``) and its backends
(``frameforge.rendering.infrastructure.backends``). Nothing here shells out to a
script in ``tooling/``; a backend that needs an external *binary* (a TeX engine)
reports unavailable when it is absent.
"""
from __future__ import annotations

import argparse
import importlib
import io
import json
import os
import sys
from dataclasses import dataclass
from typing import Callable, Optional

HERE = os.path.dirname(os.path.abspath(__file__))          # src/frameforge/
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))    # repo root (src layout)


@dataclass
class Target:
    kind: str                                  # vector | raster | typeset | source | web
    blurb: str
    check: Callable[[], Optional[str]]         # None if available, else why not
    fn: Callable                               # (path, out_dir, args) -> list[str]


# -- shared helpers --------------------------------------------------------- #
def _write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _read(path):
    return open(path, encoding="utf-8").read()


def _load_dict(path):
    text = _read(path)
    return json.loads(text) if path.endswith(".json") else importlib.import_module("yaml").safe_load(text)


def _svgs(path, pages):
    from frameforge.sdk import parse, render_page_svgs
    base = os.path.dirname(os.path.abspath(path))
    svgs = render_page_svgs(parse(_read(path)), base_dir=base)
    return svgs[:pages] if pages else svgs


def _render_with_outline(path, pages):
    """Render like `_svgs` but keep the document dict and the heading map.

    Uses the same validate → normalize → Renderer path as the SDK's
    `render_page_svgs`, holding on to the Renderer so the flow renderer's
    per-page heading telemetry (`flow_headings`) can drive the PDF outline.
    Returns `(doc_dict, svgs, outline, links)` where each outline entry is
    `{"title", "level", "page"}` and each link is `{"page", "rect", "target_page"}`,
    all with 0-based global SVG page indices."""
    from frameforge.sdk import parse
    from frameforge.rendering.application.normalize import normalize_doc
    from frameforge.rendering.application.renderer import Renderer
    base = os.path.dirname(os.path.abspath(path))
    model = parse(_read(path))
    data = model if isinstance(model, dict) else model.model_dump(by_alias=True, exclude_none=True)
    doc = normalize_doc(data)
    renderer = Renderer(doc, base)
    svgs, outline, links = [], [], []
    for page in doc.get("pages", []):
        if not isinstance(page, dict):
            continue
        start = len(svgs)
        svgs.extend(renderer.render_page(page))
        for hd in renderer.flow_headings:
            outline.append({"title": hd["text"], "level": hd["level"],
                            "page": start + hd["page"] - 1})
        for lk in renderer.flow_links:
            links.append({"page": start + lk["page"] - 1, "rect": lk["rect"],
                          "target_page": start + lk["target"] - 1})
    if pages:
        svgs = svgs[:pages]
        outline = [e for e in outline if e["page"] < len(svgs)]
        links = [lk for lk in links
                 if lk["page"] < len(svgs) and lk["target_page"] < len(svgs)]
    return doc, svgs, outline, links


def _can_import(*mods):
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception:
            return False
    return True


def _write_payload(path, payload):
    """Write one artifact payload — text (`str`) or binary (`bytes`) — to `path`."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if isinstance(payload, (bytes, bytearray)):
        with open(path, "wb") as fh:
            fh.write(payload)
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(payload)
    return path


def _render_via_port(target, path, out_dir, args, options=None):
    """Render `path` through the DocumentRenderer port and write the artifact.

    The CLI is the driving adapter: it parses the document, calls the backend's
    `render`, and owns all disk I/O — so html/pdf-tex reach a renderer in-process
    through the port, never via a subprocess to one of our own scripts."""
    from frameforge.rendering.infrastructure.backends import get_backend
    backend = get_backend(target)
    doc = _load_dict(path)
    art = backend.render(doc, base_dir=os.path.dirname(os.path.abspath(path)),
                         options=options)
    if art.one_file_per_page and len(art.pages) > 1:
        return [_write_payload(os.path.join(out_dir, f"{args.stem}-{i}.{art.extension}"), p)
                for i, p in enumerate(art.pages, 1)]
    payload = art.pages[0] if art.pages else ""
    out = getattr(args, "single", None) or os.path.join(out_dir, f"{args.stem}.{art.extension}")
    return [_write_payload(out, payload)]


def _port_check(target):
    """Availability probe for a port-backed target: delegate to the backend."""
    from frameforge.rendering.infrastructure.backends import get_backend
    return get_backend(target).available()


# -- per-target render functions -------------------------------------------- #
def r_svg(path, out_dir, args):
    return [_write(os.path.join(out_dir, f"{args.stem}-{i}.svg"), svg)
            for i, svg in enumerate(_svgs(path, args.pages), 1)]


def r_pdf(path, out_dir, args):
    cairosvg = importlib.import_module("cairosvg")
    PdfWriter = importlib.import_module("pypdf").PdfWriter
    base = os.path.dirname(os.path.abspath(path))
    doc, svgs, outline, links = _render_with_outline(path, args.pages)
    writer, n, page_index = PdfWriter(), 0, {}
    for i, svg in enumerate(svgs, 1):
        try:
            pdf = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"),
                                   url=os.path.join(base, ""), unsafe=True,
                                   dpi=96)   # pin CSS px→pt: 1 px unit = 0.75 pt (DIM-7)
        except Exception as exc:                                   # one bad page ≠ dead doc
            print(f"  ⚠ page {i}: SVG→PDF failed ({exc}); skipped", file=sys.stderr)
            continue
        writer.append(io.BytesIO(pdf))
        page_index[i - 1] = n                                      # svg index -> pdf page
        n += 1
    if n:
        _pdf_metadata(writer, doc)
        _pdf_outline(writer, outline, page_index)
        _pdf_links(writer, links, page_index)
    out = args.single or os.path.join(out_dir, f"{args.stem}.pdf")
    if n:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "wb") as fh:
            writer.write(fh)
    writer.close()
    return [out] if n else []


def _pdf_metadata(writer, doc):
    """Carry the document's identity into the PDF Info dict + catalog /Lang."""
    from pypdf.generic import NameObject, TextStringObject
    meta = {"/Producer": "FrameForge proxy renderer (frameforge-render, CairoSVG+pypdf)"}
    if doc.get("title"):
        meta["/Title"] = str(doc["title"])
    if doc.get("description"):
        meta["/Subject"] = str(doc["description"])
    writer.add_metadata(meta)
    if doc.get("lang"):
        writer.root_object[NameObject("/Lang")] = TextStringObject(str(doc["lang"]))


def _pdf_outline(writer, outline, page_index):
    """Build PDF bookmarks from the flow headings (level-nested, in order).

    `page_index` maps global SVG page index -> written PDF page (pages whose
    SVG→PDF conversion failed are absent and their headings are skipped)."""
    stack = []                                    # [(level, outline item ref)]
    for entry in outline:
        target = page_index.get(entry["page"])
        if target is None:
            continue
        while stack and stack[-1][0] >= entry["level"]:
            stack.pop()
        parent = stack[-1][1] if stack else None
        ref = writer.add_outline_item(entry["title"], target, parent=parent)
        stack.append((entry["level"], ref))


def _pdf_links(writer, links, page_index):
    """Add internal GoTo link annotations so the TOC is navigable (was a dead
    list). `links` carry svg-space rects `[x,y,w,h]` (top-left origin, px);
    CairoSVG rasterises at 96 dpi so 1 px = 0.75 pt, and svg-y flips against the
    page's own height. `page_index` maps global SVG index → written PDF page."""
    try:
        from pypdf.annotations import Link
        from pypdf.generic import ArrayObject, NumberObject
    except Exception:                                        # older pypdf: skip silently
        return
    scale = 0.75                                             # 96 dpi: svg px → pt
    no_border = ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)])
    for lk in links:
        src, tgt = page_index.get(lk["page"]), page_index.get(lk["target_page"])
        if src is None or tgt is None:
            continue
        ph = float(writer.pages[src].mediabox.height)
        x, y, w, h = (float(v) for v in lk["rect"])
        rect = (x * scale, ph - (y + h) * scale, (x + w) * scale, ph - y * scale)
        annotation = Link(rect=rect, target_page_index=tgt, border=no_border)
        writer.add_annotation(page_number=src, annotation=annotation)


def r_png(path, out_dir, args):
    from frameforge.rendering.infrastructure.browser import rasterize_svgs
    base = os.path.dirname(os.path.abspath(path))
    paths = rasterize_svgs(_svgs(path, args.pages), out_dir, base_dir=base,
                           prefix=args.stem, scale=args.scale)
    return [str(p) for p in paths]


def r_tex(path, out_dir, args):
    from frameforge.rendering.infrastructure.latex import transpile
    return [_write(os.path.join(out_dir, f"{args.stem}.tex"), transpile(_load_dict(path)))]


def r_pdf_tex(path, out_dir, args):
    return _render_via_port("pdf-tex", path, out_dir, args, options={"engine": args.engine})


def r_html(path, out_dir, args):
    return _render_via_port("html", path, out_dir, args)


def r_audit(path, out_dir, args):
    """Design-token + feature-usage audit: renders the doc to SVG, then reads
    every visual token off the emitted SVG and every feature off a generic model
    walk (drift-proof — see frameforge.rendering.application.audit). Writes a
    JSON report + a human Markdown summary and prints a one-line verdict."""
    from frameforge.rendering.application.audit import (
        audit_document, render_markdown, summary_line)
    report = audit_document(_load_dict(path), list(_svgs(path, args.pages)))
    md = render_markdown(report, title=os.path.basename(path))
    print(summary_line(report))
    for flag in report["health"]:
        print(f"  [{flag['level']}] {flag['code']}: {flag['message']}")
    return [
        _write(os.path.join(out_dir, f"{args.stem}.audit.json"),
               json.dumps(report, indent=2, ensure_ascii=False)),
        _write(os.path.join(out_dir, f"{args.stem}.audit.md"), md),
    ]


# -- registry --------------------------------------------------------------- #
def _ok():
    return None


TARGETS: dict[str, Target] = {
    "svg": Target("vector", "vector SVG — the primary, dependency-free proxy", _ok, r_svg),
    "png": Target("raster", "raster PNG via headless Chromium (CSS fidelity)",
                  lambda: None if _can_import("playwright") else
                  "needs playwright + chromium (uv sync --group browser; playwright install chromium)",
                  r_png),
    "pdf": Target("vector", "vector PDF via CairoSVG (SVG→PDF, exact vector)",
                  lambda: None if _can_import("cairosvg", "pypdf") else
                  "needs CairoSVG + pypdf (uv sync --group pdfout)", r_pdf),
    "pdf-tex": Target("typeset", "typeset PDF via LaTeX/TikZ (TeX owns pagination + math)",
                      lambda: _port_check("pdf-tex"), r_pdf_tex),
    "tex": Target("source", "LaTeX/TikZ source (.tex, no compile)", _ok, r_tex),
    "html": Target("web", "HTML/CSS (semantic; flow + gradient limits)",
                   lambda: _port_check("html"), r_html),
    "audit": Target("report", "design-token + feature-usage audit (JSON + Markdown; "
                    "drift-proof — read off the emitted SVG + model)", _ok, r_audit),
}


# -- CLI -------------------------------------------------------------------- #
def print_targets():
    print("FrameForge render targets — choose one with --to <name>:\n")
    for name, t in TARGETS.items():
        reason = t.check()
        state = "✓ available" if reason is None else f"✗ {reason}"
        print(f"  {name:<8} {t.kind:<8} {t.blurb}")
        print(f"  {'':<8} {'':<8} {state}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="frameforge-render", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="a FrameForge .fg.yaml / .json document")
    ap.add_argument("--to", choices=list(TARGETS), metavar="TARGET",
                    help="render target (see --list)")
    ap.add_argument("--list", action="store_true",
                    help="list targets + live availability and exit")
    ap.add_argument("--out", default=None, help="output directory (default: out/render-cli)")
    ap.add_argument("--pages", type=int, default=0, help="render only the first N pages (0 = all)")
    ap.add_argument("--scale", type=float, default=2.0,
                    help="raster device-pixel scale (png): PNG size = round(canvas px × scale)")
    ap.add_argument("--real-metrics", action="store_true",
                    help="wrap text with real font metrics (fontTools + fc-match) "
                         "instead of the per-char estimate; sets FRAMEFORGE_REAL_METRICS "
                         "so every backend in this run inherits it")
    ap.add_argument("--engine", choices=["auto", "lualatex", "pdflatex"], default="auto",
                    help="TeX engine for pdf-tex")
    ap.add_argument("--single", metavar="FILE", default=None, help="combined output file path (pdf)")
    args = ap.parse_args(argv)

    if args.list or not args.to:
        print_targets()
        if args.input and not args.to:
            print("Choose a target with --to <name>.")
        return 0

    if not args.input:
        print("error: an input document is required (got --to but no input)", file=sys.stderr)
        return 2

    reason = TARGETS[args.to].check()
    if reason is not None:
        print(f"target '{args.to}' is not available: {reason}", file=sys.stderr)
        return 3

    if args.real_metrics:
        # The renderer reads this when its real_metrics arg is left at None, so
        # the flag reaches the sdk render path AND the port backends (pdf-tex,
        # html) without threading a parameter through every signature.
        os.environ["FRAMEFORGE_REAL_METRICS"] = "1"

    args.stem = os.path.splitext(os.path.basename(args.input))[0]
    out_dir = args.out or os.path.join(ROOT, "out", "render-cli")
    os.makedirs(out_dir, exist_ok=True)
    if args.input.lower().endswith((".md", ".markdown")):
        # Markdown front door (issue #31): convert to a flow document first.
        # The intermediate .fg.yaml is written next to the render output — it
        # is the real, editable artifact the conversion produced.
        from frameforge.sdk import from_markdown, serialize
        notes: list = []
        doc = from_markdown(_read(args.input), warnings=notes)
        for note in notes:
            print(f"  ⚠ {note}", file=sys.stderr)
        converted = os.path.join(out_dir, f"{args.stem}.fg.yaml")
        _write(converted, serialize(doc))
        print(f"  {converted}   (converted from Markdown)")
        args.input = converted
    written = TARGETS[args.to].fn(args.input, out_dir, args)
    for p in written:
        print(f"  {p}")
    print(f"{args.to}: wrote {len(written)} file(s) to {out_dir}")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
