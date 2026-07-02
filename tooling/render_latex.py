#!/usr/bin/env python3
"""render_latex.py — the LaTeX/TikZ render engine CLI (a peer to render_fixtures.py).

Transpiles FrameGraph v2 documents to native LaTeX (TeX owns pagination,
justification, hyphenation, microtype, and real math for flow docs) with figures
and page-mode documents emitted as vector TikZ, then compiles to PDF. The TeX
engine is auto-selected (``--engine auto``): `lualatex` when its OpenType font
loader (luaotfload) is present, else `pdflatex` — for which `to_pdflatex`
rewrites the fontspec preamble and maps the document's non-ASCII glyphs through
newunicodechar so the same document compiles under either engine. Design tokens
are honoured (sizes / `ink` colour / sans body).

Usage:
    uv run python tooling/render_latex.py fixtures/standard-model.fg.yaml --out /tmp/sm_latex --png
    uv run python tooling/render_latex.py --all
    uv run python tooling/render_latex.py --list
    uv run python tooling/render_latex.py fixtures/standard-model.fg.yaml --tex-only
    uv run python tooling/render_latex.py fixtures/standard-model.fg.yaml --engine pdflatex
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402

EXTS = (".json", ".yaml", ".yml")


def discover(paths):
    out = []
    for p in (paths or [FIXTURES]):
        cand = glob.glob(p, recursive=True) or ([p] if os.path.exists(p) else [])
        for c in cand:
            if os.path.isdir(c):
                for root, _, files in os.walk(c):
                    out += [os.path.join(root, f) for f in files if f.endswith(EXTS)]
            elif c.endswith(EXTS):
                out.append(c)
    docs = []
    for f in sorted(set(out)):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("dsl") == "FrameGraph" and d.get("pages"):
            docs.append((f, d))
    return docs


def _has_luaotfload():
    """lualatex needs luaotfload (the OpenType font loader) for fontspec; some
    minimal/Debian TeX installs ship lualatex without it, so fontspec cannot load."""
    try:
        proc = subprocess.run(["kpsewhich", "luaotfload-main.lua"],
                              capture_output=True, text=True)
        return proc.returncode == 0 and proc.stdout.strip() != ""
    except Exception:
        return False


def pick_engine(preferred="auto"):
    """Resolve the TeX engine. ``auto`` prefers lualatex (full Unicode fonts via
    fontspec) when luaotfload is present, else falls back to the more widely
    available pdflatex. Returns the engine name, or ``None`` if none is usable."""
    if preferred in ("lualatex", "pdflatex"):
        return preferred if shutil.which(preferred) else None
    if shutil.which("lualatex") and _has_luaotfload():
        return "lualatex"
    if shutil.which("pdflatex"):
        return "pdflatex"
    return "lualatex" if shutil.which("lualatex") else None


# fontspec/lualatex-only constructs the transpiler emits, and their pdflatex swaps.
_FONTSPEC_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{fontspec\}")
_SETMAINFONT_RE = re.compile(r"\\setmainfont\{[^}]*\}")
_ADDFONTFEAT_RE = re.compile(r"\\addfontfeatures\s*\{[^}]*\}")

# lualatex reads Unicode natively; pdflatex does not. inputenc+textcomp cover the
# typographic glyphs, but NOT the maths / box-drawing glyphs that plate labels and
# formulas emit (Σ, →, ‖, √, •, ■, subscripts, …). Map them to TeX via
# newunicodechar — the maths ones through \ensuremath, using the amsmath/amssymb
# the transpiler already loads. Without this, pdflatex aborts on the first such
# glyph ("Unicode character … not set up for use with LaTeX").
_PDFLATEX_GLYPHS = {
    "—": r"\textemdash", "–": r"\textendash", "…": r"\textellipsis",
    "§": r"\S", "·": r"\textperiodcentered", "•": r"\textbullet",
    "“": r"\textquotedblleft", "”": r"\textquotedblright",
    "‘": r"\textquoteleft", "’": r"\textquoteright",
    "²": r"\textsuperscript{2}", "³": r"\textsuperscript{3}",
    "°": r"\textdegree", "ü": "\\\"u",
    "×": r"\ensuremath{\times}", "−": r"\ensuremath{-}", "±": r"\ensuremath{\pm}",
    "→": r"\ensuremath{\rightarrow}", "←": r"\ensuremath{\leftarrow}",
    "↑": r"\ensuremath{\uparrow}", "↓": r"\ensuremath{\downarrow}",
    "≈": r"\ensuremath{\approx}", "≤": r"\ensuremath{\leq}",
    "≥": r"\ensuremath{\geq}", "≠": r"\ensuremath{\neq}",
    "∞": r"\ensuremath{\infty}", "‖": r"\ensuremath{\|}", "√": r"\ensuremath{\surd}",
    "Σ": r"\ensuremath{\Sigma}", "Δ": r"\ensuremath{\Delta}", "Π": r"\ensuremath{\Pi}",
    "α": r"\ensuremath{\alpha}", "β": r"\ensuremath{\beta}", "γ": r"\ensuremath{\gamma}",
    "θ": r"\ensuremath{\theta}", "λ": r"\ensuremath{\lambda}", "μ": r"\ensuremath{\mu}",
    "π": r"\ensuremath{\pi}", "σ": r"\ensuremath{\sigma}", "φ": r"\ensuremath{\phi}",
    "ω": r"\ensuremath{\omega}",
    "■": r"\ensuremath{\blacksquare}", "▪": r"\ensuremath{\blacksquare}",
    "●": r"\ensuremath{\bullet}",
    "ᵢ": r"\ensuremath{{}_{i}}", "ⱼ": r"\ensuremath{{}_{j}}",
}
_PDFLATEX_UNICHARS = "\\usepackage{newunicodechar}\n" + "".join(
    f"\\newunicodechar{{{g}}}{{{c}}}\n" for g, c in _PDFLATEX_GLYPHS.items())
_PDFLATEX_FONTS = (
    "\\usepackage[utf8]{inputenc}\n"
    "\\usepackage[T1]{fontenc}\n"
    "\\usepackage{lmodern}\n"
    "\\usepackage{textcomp}\n"
    + _PDFLATEX_UNICHARS.rstrip("\n")
)


def to_pdflatex(tex):
    """Rewrite a fontspec/lualatex document so pdflatex can compile it.

    Swaps the Unicode-font preamble for inputenc + fontenc + lmodern (a clean
    sans default), teaches pdflatex the non-ASCII glyphs the document uses via
    newunicodechar, and drops fontspec-only ``\\addfontfeatures`` letter-spacing,
    which has no inline pdflatex equivalent. The TikZ body is engine-agnostic and
    is left untouched, so the vector output is identical bar the body font."""
    tex = _FONTSPEC_RE.sub(lambda m: _PDFLATEX_FONTS, tex, count=1)
    tex = _SETMAINFONT_RE.sub(
        lambda m: "\\renewcommand{\\familydefault}{\\sfdefault}", tex, count=1)
    tex = _ADDFONTFEAT_RE.sub(lambda m: "", tex)
    return tex


def compile_tex(tex_path, engine="lualatex", quiet=True, passes=2):
    """Run the TeX ``engine`` (N passes) in the tex file's directory. Returns the PDF path or None."""
    out_dir = os.path.dirname(tex_path)
    name = os.path.basename(tex_path)
    cmd = [engine, "-interaction=nonstopmode", "-halt-on-error", name]
    log = ""
    for _ in range(passes):
        proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)
        log = proc.stdout + proc.stderr
        if proc.returncode != 0:
            if not quiet:
                tail = "\n".join(log.splitlines()[-25:])
                print(f"  ! {engine} failed for {name}:\n{tail}", file=sys.stderr)
            return None
    pdf = os.path.splitext(tex_path)[0] + ".pdf"
    return pdf if os.path.exists(pdf) else None


def rasterize(pdf_path, dpi=130):
    base = os.path.splitext(pdf_path)[0]
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf_path, base],
                   capture_output=True, text=True)
    return sorted(glob.glob(base + "-*.png"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render FrameGraph docs to LaTeX/TikZ + PDF.")
    ap.add_argument("paths", nargs="*", help="files / dirs / globs (default: all fixtures/)")
    ap.add_argument("--all", action="store_true", help="render every fixture under fixtures/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "latex"), help="output dir")
    ap.add_argument("--png", action="store_true", help="also rasterize each PDF to PNG (pdftoppm)")
    ap.add_argument("--tex-only", action="store_true", help="write .tex but do not compile")
    ap.add_argument("--engine", choices=["auto", "lualatex", "pdflatex"], default="auto",
                    help="TeX engine (default: auto — lualatex if luaotfload is present, "
                         "else pdflatex)")
    ap.add_argument("--list", action="store_true", help="list discoverable FrameGraph docs and exit")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    paths = [] if args.all else args.paths
    docs = discover(paths if paths else None)
    if args.list:
        for f, _ in docs:
            print(os.path.relpath(f, ROOT))
        return 0
    if not docs:
        print("no FrameGraph documents found", file=sys.stderr)
        return 1
    engine = pick_engine(args.engine)
    if not args.tex_only and engine is None:
        print("no TeX engine found — install TeX Live (lualatex or pdflatex) or pass --tex-only",
              file=sys.stderr)
        return 2
    if not args.tex_only and not args.quiet:
        print(f"  engine: {engine}")

    os.makedirs(args.out, exist_ok=True)
    n_pdf = 0
    for f, doc in docs:
        name = os.path.splitext(os.path.basename(f))[0].replace(".fg", "")
        tex_path = os.path.join(args.out, name + ".tex")
        try:
            tex = transpile(doc, asset_base=os.path.dirname(os.path.abspath(f)))
        except Exception as exc:                       # never let one doc kill the batch
            print(f"  ! transpile failed for {name}: {exc}", file=sys.stderr)
            continue
        if engine == "pdflatex":
            tex = to_pdflatex(tex)
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(tex)
        if not args.quiet:
            print(f"  {name}.tex")
        if args.tex_only:
            continue
        pdf = compile_tex(tex_path, engine=engine, quiet=args.quiet)
        if pdf:
            n_pdf += 1
            msg = f"  {os.path.relpath(pdf, ROOT)}"
            if args.png:
                pngs = rasterize(pdf)
                msg += f"  (+{len(pngs)} png)"
            if not args.quiet:
                print(msg)
        elif args.quiet:
            print(f"  ! compile failed: {name}", file=sys.stderr)

    print(f"\nWrote {len(docs)} .tex, compiled {n_pdf} PDF(s) -> {os.path.relpath(args.out, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
