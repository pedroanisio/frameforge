"""TeX -> Unicode text fallback (domain service).

A small, dependency-free transliteration of the fixture math vocabulary to
readable Unicode, extracted verbatim from the Renderer (SRP — codebase-standards
§13). NOT a TeX engine; it lets rendered docs show readable equations when
KaTeX/MathJax/matplotlib are unavailable.
"""
from __future__ import annotations

import re


def math_text(tex):
    """Dependency-free display fallback for flow math.

    This is intentionally small, not a TeX engine. It covers the fixture math
    vocabulary so rendered docs show readable equations instead of raw
    backslash commands when KaTeX/MathJax/matplotlib are not available.
    """
    s = str(tex or "")
    replacements = {
        r"\left": "", r"\right": "", r"\,": " ", r"\;": " ",
        r"\times": "×", r"\hbar": "ℏ", r"\mu": "μ", r"\nu": "ν",
        r"\psi": "ψ", r"\phi": "φ", r"\alpha": "α", r"\beta": "β",
        r"\gamma": "γ", r"\rho": "ρ", r"\mathcal{L}": "ℒ", r"\slashed{D}": "D̸",
        r"\text{h.c.}": "h.c.", r"\bar{\psi}": "ψ̄",
        r"\in": "∈", r"\approx": "≈", r"\le": "≤", r"\ge": "≥",
        r"\arctan": "arctan", r"\max": "max",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    s = re.sub(r"\\mathbb\{([^{}]+)\}", lambda m: "".join({
        "P": "ℙ", "R": "ℝ", "C": "ℂ", "Z": "ℤ", "N": "ℕ", "Q": "ℚ",
    }.get(ch, ch) for ch in m.group(1)), s)

    frac_map = {
        ("1", "2"): "½", ("3", "2"): "3⁄2", ("1", "4"): "¼",
        ("3", "4"): "¾", (r"\sqrt{3}", "2"): "√3⁄2",
        (r"\sqrt{15}", "2"): "√15⁄2",
    }

    def frac_repl(m):
        a, b = m.group(1).strip(), m.group(2).strip()
        a = a.replace(r"\sqrt{", "√").replace("}", "")
        return frac_map.get((m.group(1).strip(), m.group(2).strip()), f"{a}⁄{b}")

    s = re.sub(r"\\t?frac\{([^{}]+(?:\{[^{}]+\}[^{}]*)?)\}\{([^{}]+)\}", frac_repl, s)
    s = re.sub(r"\\sqrt\{([^{}]+)\}", r"√\1", s)

    supers = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
    subs = str.maketrans("0123456789+-=()abcdefghijklmnopqrstuvwxyz",
                         "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐᵦ꜀ᑯₑբ₉ₕᵢⱼₖₗₘₙₒₚ૧ᵣₛₜᵤᵥwₓᵧ₂")

    def script_repl(trans):
        return lambda m: m.group(1).translate(trans)

    s = re.sub(r"\^\{([^{}]+)\}", script_repl(supers), s)
    s = re.sub(r"_\{([^{}]+)\}", script_repl(subs), s)
    s = re.sub(r"\^([A-Za-z0-9])", script_repl(supers), s)
    s = re.sub(r"_([A-Za-z0-9])", script_repl(subs), s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\\([A-Za-z]+)", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()
