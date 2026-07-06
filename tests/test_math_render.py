#!/usr/bin/env python3
"""Unit tests for the extracted math services.

- math_text: TeX -> Unicode transliteration (domain).
- MathSvgRenderer._fallback: deterministic SVG fragment when Node/MathJax is
  unavailable (infrastructure). The subprocess path is covered in
  test_flow_figure_render.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.rendering.domain.services.math_text import math_text  # noqa: E402
from framegraph.rendering.infrastructure.math_svg import MathSvgRenderer, _strip_mathml  # noqa: E402


def test_math_text_transliterations():
    assert math_text(r"E_n(f) = 0") == "Eₙ(f) = 0"
    assert math_text(r"f \in \mathbb{P}_{2n-1}") == "f ∈ ℙ₂ₙ₋₁"
    assert math_text(r"\frac{1}{2}") == "½"
    assert math_text(r"x^2") == "x²"


def test_strip_mathml():
    assert _strip_mathml("<math><mi>x</mi></math>") == "x"
    assert _strip_mathml("") == "math"      # never empty (fallback sizing)


def test_fallback_is_deterministic_and_keyed():
    m = MathSvgRenderer(math_text)
    a = m._fallback("E = mc^2", "tex")
    b = m._fallback("E = mc^2", "tex")
    assert a == b                            # deterministic
    assert a["body"].startswith('<g data-mml-node="math">')
    assert a["viewBox"].startswith("0 0 ")
    assert a["width"] >= 48 and a["height"] == 24


def test_render_caches_per_instance():
    m = MathSvgRenderer(math_text, repo_root="/nonexistent")  # forces the fallback path
    r1 = m.render("a^2", "tex")
    r2 = m.render("a^2", "tex")
    assert r1 is r2                          # second call hits the per-instance cache
    assert ("tex", "a^2") in m._cache
