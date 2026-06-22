#!/usr/bin/env python3
"""render_latex.py — the LaTeX/TikZ render engine CLI (a peer to render_fixtures.py).

Transpiles FrameGraph v2 *flow* documents to native LaTeX (TeX owns pagination,
justification, hyphenation, microtype, and real math) with figures emitted as vector
TikZ, then compiles with `lualatex`. Design tokens are honoured (sizes / `ink` colour /
sans body via fontspec).

Usage:
    uv run python tooling/render_latex.py fixtures/standard-model.fg.yaml --out /tmp/sm_latex --png
    uv run python tooling/render_latex.py --all
    uv run python tooling/render_latex.py --list
    uv run python tooling/render_latex.py fixtures/standard-model.fg.yaml --tex-only
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FIXTURES = os.path.join(ROOT, "fixtures")
sys.path.insert(0, ROOT)

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
            if any(isinstance(p, dict) and p.get("mode") == "flow" for p in d["pages"]):
                docs.append((f, d))
    return docs


def compile_tex(tex_path, quiet=True, passes=2):
    """Run lualatex (N passes) in the tex file's directory. Returns the PDF path or None."""
    out_dir = os.path.dirname(tex_path)
    name = os.path.basename(tex_path)
    cmd = ["lualatex", "-interaction=nonstopmode", "-halt-on-error", name]
    log = ""
    for _ in range(passes):
        proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)
        log = proc.stdout + proc.stderr
        if proc.returncode != 0:
            if not quiet:
                tail = "\n".join(log.splitlines()[-25:])
                print(f"  ! lualatex failed for {name}:\n{tail}", file=sys.stderr)
            return None
    pdf = os.path.splitext(tex_path)[0] + ".pdf"
    return pdf if os.path.exists(pdf) else None


def rasterize(pdf_path, dpi=130):
    base = os.path.splitext(pdf_path)[0]
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf_path, base],
                   capture_output=True, text=True)
    return sorted(glob.glob(base + "-*.png"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render FrameGraph flow docs to LaTeX/TikZ + PDF.")
    ap.add_argument("paths", nargs="*", help="files / dirs / globs (default: all fixtures/)")
    ap.add_argument("--all", action="store_true", help="render every flow fixture under fixtures/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "latex"), help="output dir")
    ap.add_argument("--png", action="store_true", help="also rasterize each PDF to PNG (pdftoppm)")
    ap.add_argument("--tex-only", action="store_true", help="write .tex but do not compile")
    ap.add_argument("--list", action="store_true", help="list discoverable flow docs and exit")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    paths = [] if args.all else args.paths
    docs = discover(paths if paths else None)
    if args.list:
        for f, _ in docs:
            print(os.path.relpath(f, ROOT))
        return 0
    if not docs:
        print("no FrameGraph flow documents found", file=sys.stderr)
        return 1
    if not args.tex_only and not shutil.which("lualatex"):
        print("lualatex not found — install TeX Live (texlive-luatex) or pass --tex-only",
              file=sys.stderr)
        return 2

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
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(tex)
        if not args.quiet:
            print(f"  {name}.tex")
        if args.tex_only:
            continue
        pdf = compile_tex(tex_path, quiet=args.quiet)
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
