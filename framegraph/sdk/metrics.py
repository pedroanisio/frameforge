"""Author-time text measurement for the FrameGraph SDK.

These helpers answer the question an author repeatedly needs when placing text
in absolute boxes: *how wide is this string, where will it wrap, and how tall is
the wrapped block?* — so box heights can be computed instead of guessed.

When ``fontTools`` is available (install the ``metrics`` dependency-group) the
width comes from the real glyph advances of the font ``fc-match`` resolves, the
same file the rasterizer draws with — see
:mod:`framegraph.rendering.infrastructure.font_metrics`. Otherwise it falls back
to the proxy renderer's per-character ``avg`` estimate (0.52 proportional / 0.60
monospace, ×1.04 bold), so the functions are always defined and deterministic.

``font_family`` accepts either a CSS family string (``"Fira Mono, monospace"``)
or a stack list (``["Fira Mono", "DejaVu Sans Mono", "monospace"]``) — the same
shapes the builders accept — and the whole chain is handed to ``fc-match``.
"""
from __future__ import annotations

from typing import Sequence

from framegraph.rendering.infrastructure import font_metrics as _fm

__all__ = ["measure_text", "wrap_text", "text_height"]

FontFamily = str | Sequence[str]


def _chain(font_family: FontFamily) -> str:
    """Render a family (string or stack list) as a CSS font-family chain."""
    if isinstance(font_family, str):
        return font_family
    return ", ".join(str(f) for f in font_family)


def _first(font_family: FontFamily) -> str:
    """First concrete-or-generic name in the family, for the mono heuristic."""
    if isinstance(font_family, str):
        parts = [p.strip().strip("'\"") for p in font_family.split(",") if p.strip()]
        return parts[0] if parts else ""
    return str(font_family[0]) if len(font_family) else ""


def _avg(font_family: FontFamily, bold: bool) -> float:
    """Per-character advance ratio matching ``TextStyleResolver``'s estimate."""
    avg = 0.60 if "mono" in _first(font_family).lower() else 0.52
    return avg * 1.04 if bold else avg


def measure_text(
    text: str,
    *,
    font_family: FontFamily,
    font_size: float,
    bold: bool = False,
) -> float:
    """Return the rendered width of ``text`` in pixels.

    Uses real font metrics when available, else the ``avg`` estimate. Always
    returns a number (0.0 for empty text).
    """
    s = str(text)
    real = _fm.measure_text(s, _chain(font_family), float(font_size), bool(bold))
    if real is not None:
        return real
    return len(s) * float(font_size) * _avg(font_family, bold)


def wrap_text(
    text: str,
    *,
    width: float,
    font_family: FontFamily,
    font_size: float,
    bold: bool = False,
) -> list[str]:
    """Greedily word-wrap ``text`` to ``width`` pixels, returning the lines.

    Over-long single tokens are hard-broken so no returned line exceeds
    ``width``. A non-positive ``width`` returns the text unwrapped.
    """
    width = float(width)
    s = str(text)
    if width <= 0:
        return [s]

    def w(part: str) -> float:
        return measure_text(part, font_family=font_family, font_size=font_size, bold=bold)

    out: list[str] = []
    cur = ""
    for word in s.split():
        while w(word) > width:                       # hard-break an over-long token
            take = 1
            while take < len(word) and w(word[: take + 1]) <= width:
                take += 1
            if cur:
                out.append(cur)
                cur = ""
            out.append(word[:take])
            word = word[take:]
            if not word:
                break
        if not word:
            continue
        cand = (cur + " " + word).strip()
        if cur and w(cand) > width:
            out.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out or [""]


def text_height(
    text: str,
    *,
    width: float,
    font_family: FontFamily,
    font_size: float,
    line_height: float = 1.25,
    bold: bool = False,
) -> float:
    """Return the total height (px) of ``text`` wrapped to ``width``.

    Equals ``len(wrap_text(...)) * font_size * line_height`` — the number an
    author needs to size a text box's height to its content.
    """
    lines = wrap_text(text, width=width, font_family=font_family,
                      font_size=font_size, bold=bold)
    return len(lines) * float(font_size) * float(line_height)
