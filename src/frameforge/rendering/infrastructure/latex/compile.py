"""In-process LaTeX/TikZ → PDF compilation (a driven infrastructure adapter).

Moved here from ``tooling/render_latex.py`` so the render pipeline reaches PDF
compilation *through the package* — the `PdfTexDocumentRenderer`
(`DocumentRenderer` port) — instead of the CLI shelling out to a script. The
only shelling that remains is to the external TeX *binary* (``lualatex`` /
``pdflatex``) and, for the standalone tool, poppler's ``pdftoppm`` — genuine
external programs, which is exactly what an infrastructure adapter wraps.

`render_latex.py` now imports its engine/rewrite/compile helpers from here, so
there is a single source of truth for the TeX orchestration.
"""
from __future__ import annotations

import functools
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Optional

from frameforge.rendering.infrastructure.latex import transpile


# --------------------------------------------------------------------------- #
# Engine selection                                                             #
# --------------------------------------------------------------------------- #
def _has_luaotfload() -> bool:
    """lualatex needs luaotfload (the OpenType font loader) for fontspec; some
    minimal/Debian TeX installs ship lualatex without it, so fontspec cannot load."""
    try:
        proc = subprocess.run(["kpsewhich", "luaotfload-main.lua"],
                              capture_output=True, text=True)
        return proc.returncode == 0 and proc.stdout.strip() != ""
    except Exception:
        return False


@functools.lru_cache(maxsize=None)
def _engine_runs(engine: str) -> bool:
    """True only when ``<engine> --version`` actually EXECUTES (rc 0).

    Presence on PATH is not enough: a TeX binary can be installed yet crash on
    launch (a mismatched shared lib / broken ``ld.so`` returns rc 127 before it
    reads any input). Auto-selection consults this so it falls back to a working
    engine instead of picking a corpse. Cached — the probe is per-process cheap
    but not free."""
    try:
        proc = subprocess.run([engine, "--version"], capture_output=True,
                              text=True, timeout=20)
        return proc.returncode == 0
    except Exception:
        return False


def pick_engine(preferred: str = "auto") -> Optional[str]:
    """Resolve the TeX engine. ``auto`` prefers lualatex (full Unicode fonts via
    fontspec) when luaotfload is present AND the binary actually runs, else
    falls back to the more widely available pdflatex. An EXPLICIT choice is
    respected (returned when on PATH) — the caller owns that decision and its
    failure. Returns the engine name, or ``None`` if none is usable."""
    if preferred in ("lualatex", "pdflatex"):
        return preferred if shutil.which(preferred) else None
    if shutil.which("lualatex") and _has_luaotfload() and _engine_runs("lualatex"):
        return "lualatex"
    if shutil.which("pdflatex") and _engine_runs("pdflatex"):
        return "pdflatex"
    return None


def engine_available(preferred: str = "auto") -> bool:
    """True when a usable TeX engine is on PATH for the given preference."""
    return pick_engine(preferred) is not None


# --------------------------------------------------------------------------- #
# pdflatex fallback rewrite                                                    #
# --------------------------------------------------------------------------- #
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


def to_pdflatex(tex: str) -> str:
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


# --------------------------------------------------------------------------- #
# Compilation (invokes the external TeX binary)                               #
# --------------------------------------------------------------------------- #
def compile_tex(tex_path: str, engine: str = "lualatex",
                quiet: bool = True, passes: int = 2,
                log_sink: Optional[list] = None) -> Optional[str]:
    """Run the TeX ``engine`` (N passes) in the tex file's directory.

    Returns the PDF path or None on failure. On failure the last ~25 log lines
    are appended to ``log_sink`` (when given) so a caller can surface the real
    cause — an engine that crashes on launch (``ld.so`` assertion) or a genuine
    TeX error — instead of a blank 'failed'."""
    out_dir = os.path.dirname(tex_path)
    name = os.path.basename(tex_path)
    cmd = [engine, "-interaction=nonstopmode", "-halt-on-error", name]
    log = ""
    for _ in range(passes):
        proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)
        log = proc.stdout + proc.stderr
        if proc.returncode != 0:
            tail = "\n".join(log.splitlines()[-25:]).strip()
            if log_sink is not None:
                log_sink.append(tail)
            if not quiet:
                print(f"  ! {engine} failed for {name}:\n{tail}", file=sys.stderr)
            return None
    pdf = os.path.splitext(tex_path)[0] + ".pdf"
    return pdf if os.path.exists(pdf) else None


def rasterize(pdf_path: str, dpi: int = 130) -> list[str]:
    """Rasterize a PDF to per-page PNGs with poppler's pdftoppm. Returns the PNGs."""
    base = os.path.splitext(pdf_path)[0]
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf_path, base],
                   capture_output=True, text=True)
    return sorted(glob.glob(base + "-*.png"))


# --------------------------------------------------------------------------- #
# One-shot: document dict → PDF bytes (the port's building block)             #
# --------------------------------------------------------------------------- #
def compile_document(document: Mapping[str, Any], *, engine: str = "auto",
                     asset_base: Optional[str] = None, quiet: bool = True) -> bytes:
    """Transpile `document` and compile it to PDF **bytes** with an external TeX engine.

    Compiles in a scratch temp dir (so no `.tex`/`.aux`/`.log` litter escapes) and
    returns the resulting PDF's bytes; the caller owns where they land. Raises
    `RuntimeError` when no engine is available or the compile fails — the caller
    (the backend / CLI) surfaces that as an unavailable/failed target."""
    eng = pick_engine(engine)
    if eng is None:
        raise RuntimeError("no TeX engine found — install TeX Live (lualatex or pdflatex)")
    tex = transpile(document, asset_base=asset_base)
    if eng == "pdflatex":
        tex = to_pdflatex(tex)
    with tempfile.TemporaryDirectory(prefix="fg-pdftex-") as work:
        tex_path = os.path.join(work, "doc.tex")
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(tex)
        sink: list = []
        pdf_path = compile_tex(tex_path, engine=eng, quiet=quiet, log_sink=sink)
        if not pdf_path:
            detail = ("\n" + sink[0]) if sink else ""
            raise RuntimeError(f"{eng} failed to compile the document{detail}")
        with open(pdf_path, "rb") as fh:
            return fh.read()
