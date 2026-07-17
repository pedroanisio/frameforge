"""Pure scalar / geometry helpers for the rendering domain.

Extracted verbatim from tooling/render_fixtures.py (DDD migration, step 2).
These are value-level coercion/formatting primitives with no backend or I/O
dependency, so they belong in the dependency-free domain core.
"""
from __future__ import annotations

import html


def num(v, default=None):
    """Coerce a Length-ish value to a float (pt/px treated 1:1; %/fr give default)."""
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s.endswith(("%", "fr")):
            return default
        for u in ("px", "pt", "pc", "mm", "cm", "in", "em", "rem", "deg"):
            if s.endswith(u):
                s = s[: -len(u)]
                break
        try:
            return float(s)
        except ValueError:
            return default
    return default


def fnum(x):
    """Compact float formatting for SVG attributes."""
    f = float(x)
    return str(int(f)) if f == int(f) else f"{f:.3f}".rstrip("0").rstrip(".")


def fnum_precise(x):
    """High-precision float formatting for MULTIPLICATIVE SVG values.

    `fnum`'s 3-decimal quantization (error ≤ 5e-4) is harmless on plain
    coordinates but is amplified by coordinate extent when the value is a
    multiplier (transform scale/matrix terms, figure fit scales): 5e-4 × a
    3840 px extent ≈ 2 px at 4K. Nine significant digits keep that worst
    case below 1e-5 px. Additive companion — `fnum` call sites keep their
    existing (byte-stable) output."""
    f = float(x)
    return str(int(f)) if f == int(f) else f"{f:.9g}"


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def is_point(v):
    return isinstance(v, (list, tuple)) and len(v) == 2 and all(
        isinstance(c, (int, float)) and not isinstance(c, bool) for c in v
    )
