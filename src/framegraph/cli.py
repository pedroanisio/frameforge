#!/usr/bin/env python3
"""framegraph.cli — the FrameGraph render front-door: choose a target, dispatch a backend.

The project ships several render paths; this is the single CLI over all of them.
``--list`` shows every target — what it produces, the optional dependency it
needs, and whether it is available *right now* — so you can choose how to render:

    python -m framegraph.cli <doc.fg.yaml> --to <target> [--out DIR]
    framegraph-render <doc.fg.yaml> --to pdf            # the installed entry point

Targets (see ``--list``):
  svg      vector SVG — the primary, dependency-free proxy
  png      raster PNG via headless Chromium (CSS fidelity)            [browser]
  pdf      vector PDF via CairoSVG (SVG→PDF, exact vector)            [pdfout]
  pdf-tex  typeset PDF via LaTeX/TikZ (TeX owns pagination + math)    [lua/pdflatex]
  tex      LaTeX/TikZ source (.tex, no compile)
  html     HTML/CSS (legacy; flow + gradient limits)

The core targets (svg, png, pdf, tex) render through the package itself — the
SVG proxy, the Chromium rasteriser, and the LaTeX transpiler. The two peripheral
targets (pdf-tex, html) shell out to the repo's tool scripts, so the package
never *imports* ``tooling`` (it ships self-contained; those targets simply report
unavailable where the scripts are absent).
"""
from __future__ import annotations

import argparse
import glob
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Optional

HERE = os.path.dirname(os.path.abspath(__file__))          # src/framegraph/
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
    from framegraph.sdk import parse, render_page_svgs
    base = os.path.dirname(os.path.abspath(path))
    svgs = render_page_svgs(parse(_read(path)), base_dir=base)
    return svgs[:pages] if pages else svgs


def _render_with_outline(path, pages):
    """Render like `_svgs` but keep the document dict and the heading map.

    Uses the same validate → normalize → Renderer path as the SDK's
    `render_page_svgs`, holding on to the Renderer so the flow renderer's
    per-page heading telemetry (`flow_headings`) can drive the PDF outline.
    Returns `(doc_dict, svgs, outline)` where each outline entry is
    `{"title", "level", "page"}` with a 0-based global SVG page index."""
    from framegraph.sdk import parse
    from framegraph.rendering.application.normalize import normalize_doc
    from framegraph.rendering.application.renderer import Renderer
    base = os.path.dirname(os.path.abspath(path))
    model = parse(_read(path))
    data = model if isinstance(model, dict) else model.model_dump(by_alias=True, exclude_none=True)
    doc = normalize_doc(data)
    renderer = Renderer(doc, base)
    svgs, outline = [], []
    for page in doc.get("pages", []):
        if not isinstance(page, dict):
            continue
        start = len(svgs)
        svgs.extend(renderer.render_page(page))
        for hd in renderer.flow_headings:
            outline.append({"title": hd["text"], "level": hd["level"],
                            "page": start + hd["page"] - 1})
    if pages:
        svgs = svgs[:pages]
        outline = [e for e in outline if e["page"] < len(svgs)]
    return doc, svgs, outline


def _can_import(*mods):
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception:
            return False
    return True


def _script(rel):
    return os.path.join(ROOT, rel)


# -- per-target render functions -------------------------------------------- #
def r_svg(path, out_dir, args):
    return [_write(os.path.join(out_dir, f"{args.stem}-{i}.svg"), svg)
            for i, svg in enumerate(_svgs(path, args.pages), 1)]


def r_pdf(path, out_dir, args):
    cairosvg = importlib.import_module("cairosvg")
    PdfWriter = importlib.import_module("pypdf").PdfWriter
    base = os.path.dirname(os.path.abspath(path))
    doc, svgs, outline = _render_with_outline(path, args.pages)
    writer, n, page_index = PdfWriter(), 0, {}
    for i, svg in enumerate(svgs, 1):
        try:
            pdf = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"),
                                   url=os.path.join(base, ""), unsafe=True)
        except Exception as exc:                                   # one bad page ≠ dead doc
            print(f"  ⚠ page {i}: SVG→PDF failed ({exc}); skipped", file=sys.stderr)
            continue
        writer.append(io.BytesIO(pdf))
        page_index[i - 1] = n                                      # svg index -> pdf page
        n += 1
    if n:
        _pdf_metadata(writer, doc)
        _pdf_outline(writer, outline, page_index)
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
    meta = {"/Producer": "FrameGraph proxy renderer (framegraph-render, CairoSVG+pypdf)"}
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


def r_png(path, out_dir, args):
    from framegraph.rendering.infrastructure.browser import rasterize_svgs
    base = os.path.dirname(os.path.abspath(path))
    paths = rasterize_svgs(_svgs(path, args.pages), out_dir, base_dir=base,
                           prefix=args.stem, scale=args.scale)
    return [str(p) for p in paths]


def r_tex(path, out_dir, args):
    from framegraph.rendering.infrastructure.latex import transpile
    return [_write(os.path.join(out_dir, f"{args.stem}.tex"), transpile(_load_dict(path)))]


def r_pdf_tex(path, out_dir, args):
    before = set(glob.glob(os.path.join(out_dir, "*.pdf")))
    subprocess.run([sys.executable, _script("tooling/render_latex.py"), path,
                    "--out", out_dir, "--engine", args.engine], check=True)
    new = sorted(set(glob.glob(os.path.join(out_dir, "*.pdf"))) - before)
    return new


def r_html(path, out_dir, args):
    out = os.path.join(out_dir, f"{args.stem}.html")
    subprocess.run([sys.executable, _script("framegraph_to_html.py"), path, "-o", out], check=True)
    return [out]


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
                      lambda: None if (os.path.exists(_script("tooling/render_latex.py"))
                                       and (shutil.which("lualatex") or shutil.which("pdflatex")))
                      else "needs tooling/render_latex.py + lualatex/pdflatex on PATH", r_pdf_tex),
    "tex": Target("source", "LaTeX/TikZ source (.tex, no compile)", _ok, r_tex),
    "html": Target("web", "HTML/CSS (legacy; flow + gradient limits)",
                   lambda: None if os.path.exists(_script("framegraph_to_html.py"))
                   else "needs framegraph_to_html.py", r_html),
}


# -- CLI -------------------------------------------------------------------- #
def print_targets():
    print("FrameGraph render targets — choose one with --to <name>:\n")
    for name, t in TARGETS.items():
        reason = t.check()
        state = "✓ available" if reason is None else f"✗ {reason}"
        print(f"  {name:<8} {t.kind:<8} {t.blurb}")
        print(f"  {'':<8} {'':<8} {state}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="framegraph-render", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="a FrameGraph .fg.yaml / .json document")
    ap.add_argument("--to", choices=list(TARGETS), metavar="TARGET",
                    help="render target (see --list)")
    ap.add_argument("--list", action="store_true",
                    help="list targets + live availability and exit")
    ap.add_argument("--out", default=None, help="output directory (default: out/render-cli)")
    ap.add_argument("--pages", type=int, default=0, help="render only the first N pages (0 = all)")
    ap.add_argument("--scale", type=float, default=2.0, help="raster scale factor (png)")
    ap.add_argument("--real-metrics", action="store_true",
                    help="wrap text with real font metrics (fontTools + fc-match) "
                         "instead of the per-char estimate; sets FRAMEGRAPH_REAL_METRICS "
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
        # the flag reaches the sdk render path AND subprocess targets (pdf-tex,
        # html) without threading a parameter through every signature.
        os.environ["FRAMEGRAPH_REAL_METRICS"] = "1"

    args.stem = os.path.splitext(os.path.basename(args.input))[0]
    out_dir = args.out or os.path.join(ROOT, "out", "render-cli")
    os.makedirs(out_dir, exist_ok=True)
    if args.input.lower().endswith((".md", ".markdown")):
        # Markdown front door (issue #31): convert to a flow document first.
        # The intermediate .fg.yaml is written next to the render output — it
        # is the real, editable artifact the conversion produced.
        from framegraph.sdk import from_markdown, serialize
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
