#!/usr/bin/env python3
"""`render_latex.py --engine pdflatex` must compile real FrameForge documents.

`to_pdflatex` swaps the fontspec/lualatex preamble for a pdflatex one. On its own
that is not enough: the SDK's plate labels and formulas emit non-ASCII maths/box
glyphs (Σ, →, ‖, √, •, ■, subscripts) that inputenc+textcomp do not define, so
pdflatex aborts with "Unicode character … not set up". The rewrite now injects a
newunicodechar map for them.

Renderer-only import (the `frameforge` package must win) — evict a models-module
shadow first, per test_render_cli.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling import render_latex as CLI  # noqa: E402

SAMPLE = (
    "\\documentclass{article}\n"
    "\\usepackage{fontspec}\n"
    "\\setmainfont{DejaVu Sans}\n"
    "\\begin{document}\n"
    "\\node{font=\\bfseries\\addfontfeatures{LetterSpace=2.2}} {label};\n"
    "Body with Σ → ‖ √ • ■ and dᵢⱼ.\n"
    "\\end{document}\n"
)


def test_to_pdflatex_swaps_preamble_and_drops_fontspec_only_constructs():
    out = CLI.to_pdflatex(SAMPLE)
    assert "fontspec" not in out
    assert "\\usepackage[utf8]{inputenc}" in out
    assert "\\usepackage[T1]{fontenc}" in out
    assert "\\renewcommand{\\familydefault}{\\sfdefault}" in out
    assert "\\setmainfont" not in out
    assert "\\addfontfeatures" not in out          # no inline pdflatex equivalent


def test_to_pdflatex_maps_maths_and_box_glyphs_via_newunicodechar():
    out = CLI.to_pdflatex(SAMPLE)
    assert "\\usepackage{newunicodechar}" in out
    assert "\\newunicodechar{Σ}{\\ensuremath{\\Sigma}}" in out
    assert "\\newunicodechar{→}{\\ensuremath{\\rightarrow}}" in out
    assert "\\newunicodechar{‖}{\\ensuremath{\\|}}" in out
    assert "\\newunicodechar{√}{\\ensuremath{\\surd}}" in out
    assert "\\newunicodechar{•}{\\textbullet}" in out
    assert "\\newunicodechar{■}{\\ensuremath{\\blacksquare}}" in out
    assert "\\newunicodechar{ᵢ}{\\ensuremath{{}_{i}}}" in out


def test_no_non_ascii_glyph_in_sample_is_left_unmapped():
    out = CLI.to_pdflatex(SAMPLE)
    body = out.split("\\begin{document}", 1)[1]
    for ch in set(body):
        if ord(ch) > 127:
            assert ch in CLI._PDFLATEX_GLYPHS, f"glyph U+{ord(ch):04X} {ch!r} unmapped"
