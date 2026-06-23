"""Real-font advance-width metrics for accurate text wrapping (optional).

The proxy renderer's default text model estimates rendered width from a single
per-character advance ratio (``TextStyleResolver`` emits ``avg`` — 0.52 for
proportional families, 0.60 for monospace; ×1.04 when bold). That estimate is
calibrated for narrow Helvetica-class fonts; when the rasterizer (cairosvg →
Pango → fontconfig) actually resolves a *wider* installed family (DejaVu Sans on
most Linux distros, Fira Sans on this tree), the real per-glyph advances are
systematically wider, so wrap points chosen from the estimate push past the box
at render time and an author has to hand-tune box heights.

This module reads the **real** glyph-advance widths from the font file
fontconfig would resolve for a given CSS font-family, aligning the layout view
with what the rasterizer draws. It is the v2 port of the legacy
``framegraph/_font_metrics.py`` capability.

**Optional + graceful.** ``fontTools`` is not a core dependency (§2/§13: the core
SVG renderer stays dependency-free). If ``fontTools`` is unavailable, ``fc-match``
is missing, or the resolved font fails to parse, :func:`measure_text` returns
``None`` and every caller falls back to the ``avg`` estimate — so behaviour is
*byte-identical* to today unless a caller has both installed ``fontTools`` and
opted in. Install via the ``metrics`` dependency-group (``uv sync --group
metrics``); ``fontTools`` is already present in the locked graph.

Public surface
--------------

- :class:`FontMetrics` — frozen container of per-codepoint em-unit advances.
- :func:`measure_text` — family → metrics → pixel width (``None`` on miss).
- :func:`get_font_metrics` — resolve + load + cache; ``None`` on failure.
- :func:`clear_cache` — drop cached metrics (test-only helper).

The module-level cache keys on ``(font_family, bold)`` tuples; each entry loads
exactly one TTF/OTF file. Documents typically declare two families (sans + mono)
× two weights, so the cache is small and lookup is cheap.
"""
from __future__ import annotations

import os
import shutil
import subprocess

__all__ = ["FontMetrics", "measure_text", "get_font_metrics", "clear_cache"]


class FontMetrics:
    """Cached glyph-advance widths for one (font-file, weight) pair.

    ``advance_widths_em`` maps Unicode codepoints to advance widths in em units
    (font design units / unitsPerEm). Multiplying by the font size in pixels
    yields pixel width. Codepoints absent from the font ``cmap`` fall back to
    ``default_em`` — the mean of the present advances, a robust proxy for the
    width of a missing-glyph (.notdef) box.
    """

    __slots__ = ("advance_widths_em", "default_em", "source_path")

    def __init__(
        self,
        advance_widths_em: dict[int, float],
        default_em: float,
        source_path: str,
    ) -> None:
        """Store the per-codepoint advance widths, fallback em, and source path."""
        self.advance_widths_em = advance_widths_em
        self.default_em = default_em
        self.source_path = source_path

    def width(self, text: str, font_size: float) -> float:
        """Return rendered width of ``text`` at ``font_size`` pixels."""
        widths = self.advance_widths_em
        default = self.default_em
        return sum(widths.get(ord(c), default) for c in text) * font_size


# Module-level cache. Keyed on (font_family_chain, bold) to keep sans-bold and
# sans-regular distinct (they often live in separate files with materially
# different advance widths).
_CACHE: dict[tuple[str, bool], FontMetrics | None] = {}


def clear_cache() -> None:
    """Reset the metrics cache. Test-only helper."""
    _CACHE.clear()


def _split_family_chain(font_family: str) -> list[str]:
    """Parse a CSS font-family string into ordered, unquoted candidates.

    ``"'DejaVu Sans', Helvetica, sans-serif"`` →
    ``["DejaVu Sans", "Helvetica", "sans-serif"]``.
    """
    out: list[str] = []
    for part in font_family.split(","):
        s = part.strip().strip("'\"").strip()
        if s:
            out.append(s)
    return out


_GENERIC_FAMILIES = {"sans-serif", "serif", "monospace", "system-ui", "cursive", "fantasy"}


def _resolve_font_file(font_family: str, bold: bool) -> str | None:
    """Resolve the first concrete name in a CSS font-family chain to a file path.

    Uses ``fc-match`` (fontconfig) so the resolved file matches what the
    rasterizer (cairosvg via Pango) will pick. Returns ``None`` when:

    * the system has no ``fc-match`` binary,
    * the chain contains only generic family names, or
    * the resolved path does not exist on disk.

    The first concrete (non-generic) name is queried; if all entries are
    generic, the first one is queried so fontconfig returns its system default
    for that family class.
    """
    if shutil.which("fc-match") is None:
        return None
    candidates = _split_family_chain(font_family)
    if not candidates:
        return None
    concrete = [c for c in candidates if c.lower() not in _GENERIC_FAMILIES]
    target = concrete[0] if concrete else candidates[0]
    weight = "bold" if bold else "regular"
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", f"{target}:weight={weight}"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    path = result.stdout.strip()
    if path and os.path.isfile(path):
        return path
    return None


def _load_font_metrics(font_path: str) -> FontMetrics | None:
    """Read advance widths from a TTF/OTF file via ``fontTools``.

    Returns ``None`` when ``fontTools`` is not installed or the file fails to
    parse — callers fall back to the ``avg`` estimate.
    """
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    try:
        font = TTFont(font_path, fontNumber=0, lazy=True)
        units_per_em = int(font["head"].unitsPerEm)
        if units_per_em <= 0:
            return None
        cmap = font.getBestCmap()
        hmtx = font["hmtx"].metrics
        advance_widths_em: dict[int, float] = {}
        for codepoint, glyph_name in cmap.items():
            entry = hmtx.get(glyph_name)
            if entry is None:
                continue
            adv = float(entry[0])
            advance_widths_em[codepoint] = adv / units_per_em
    except Exception:
        return None
    if not advance_widths_em:
        return None
    default_em = sum(advance_widths_em.values()) / len(advance_widths_em)
    return FontMetrics(
        advance_widths_em=advance_widths_em,
        default_em=default_em,
        source_path=font_path,
    )


def get_font_metrics(font_family: str, bold: bool) -> FontMetrics | None:
    """Resolve, load, and cache metrics for a CSS font-family chain.

    Returns ``None`` when fontconfig or ``fontTools`` are unavailable, or when no
    entry in the chain resolves to a parseable font file. The result (including
    ``None`` failures) is cached so retries are cheap.
    """
    if not font_family:
        return None
    key = (font_family, bool(bold))
    if key in _CACHE:
        return _CACHE[key]
    path = _resolve_font_file(font_family, bold)
    if not path:
        _CACHE[key] = None
        return None
    metrics = _load_font_metrics(path)
    _CACHE[key] = metrics
    return metrics


def measure_text(text: str, font_family: str, font_size: float, bold: bool) -> float | None:
    """Return rendered text width using real font metrics, or ``None`` on miss.

    Convenience wrapper for callers that don't need to keep the
    :class:`FontMetrics` object around.
    """
    metrics = get_font_metrics(font_family, bold)
    if metrics is None:
        return None
    return metrics.width(text, font_size)
