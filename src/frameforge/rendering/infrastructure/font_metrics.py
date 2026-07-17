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
``frameforge/_font_metrics.py`` capability.

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

__all__ = [
    "FontMetrics",
    "clear_cache",
    "first_concrete_family",
    "get_font_metrics",
    "measure_text",
    "resolve_family_name",
    "resolve_report",
]


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
    """Reset the metrics + family-name caches. Test-only helper."""
    _CACHE.clear()
    _FAMILY_CACHE.clear()


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


def _fc_query(target: str, weight: str) -> tuple[str | None, str | None]:
    """``(resolved_family, file)`` fontconfig returns for ``target``."""
    try:
        r = subprocess.run(
            ["fc-match", "-f", "%{family}\t%{file}", f"{target}:weight={weight}"],
            capture_output=True, text=True, timeout=2.0, check=False)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None, None
    fam, _, path = r.stdout.strip().partition("\t")
    return (fam.strip() or None), (path.strip() or None)


def _family_tokens(name: str) -> set[str]:
    return set(name.lower().replace("-", " ").split())


def _is_real_match(requested: str, resolved: str | None) -> bool:
    """True when fontconfig actually *has* ``requested`` — its tokens are a subset
    of the resolved family — versus a fuzzy fallback to an unrelated face
    (``fc-match 'Charter'`` → ``'Noto Sans'``, which a browser would reject and
    fall through on)."""
    return bool(resolved) and _family_tokens(requested) <= _family_tokens(resolved)


def _resolve_font_file(font_family: str, bold: bool) -> str | None:
    """Resolve a CSS font-family chain to a file path **the way a browser does**:
    walk the chain, and for each concrete name accept fontconfig's result only if
    it is a real match (not a fuzzy fallback); otherwise fall through to the next
    entry. Generic families take fontconfig's class default (as the browser does).
    Returns ``None`` (→ average-glyph estimate) when nothing resolves — a caller
    that measures at that point is measuring a *different* font than the rasterizer
    will draw, so :func:`resolve_report` flags it.
    """
    if shutil.which("fc-match") is None:
        return None
    weight = "bold" if bold else "regular"
    for fam in _split_family_chain(font_family):
        resolved_fam, path = _fc_query(fam, weight)
        if not path or not os.path.isfile(path):
            continue
        if fam.lower() in _GENERIC_FAMILIES or _is_real_match(fam, resolved_fam):
            return path
        # fontconfig fuzzy-fell-back for this concrete name → try the next entry
    return None


def resolve_report(font_family: str, bold: bool = False) -> tuple[str | None, bool, str | None]:
    """``(resolved_family, matched, requested_concrete)``.

    ``matched`` is **False** when every concrete family in the chain is missing
    (fontconfig fuzzy-fell-back or only a generic remains) — i.e. the layout font
    is NOT what was asked for, so measuring it here will disagree with whatever the
    rasterizer draws. That is the measure-time≠render-time hazard; the renderer
    turns a False here into a loud font-substitution warning."""
    requested = first_concrete_family(font_family or "")
    if requested is None:
        return (None, True, None)              # generic-only: system default by design
    if shutil.which("fc-match") is None:
        return (None, False, requested)
    weight = "bold" if bold else "regular"
    for fam in _split_family_chain(font_family):
        if fam.lower() in _GENERIC_FAMILIES:
            break
        resolved_fam, path = _fc_query(fam, weight)
        if path and os.path.isfile(path) and _is_real_match(fam, resolved_fam):
            return (resolved_fam, True, requested)
    return (resolve_family_name(font_family), False, requested)


def first_concrete_family(font_family: str) -> str | None:
    """The first non-generic name in a CSS font-family chain, or ``None`` when
    the chain is empty or generic-only (generic families resolve to a system
    default *by design*, so they are not substitution candidates)."""
    for candidate in _split_family_chain(font_family or ""):
        if candidate.lower() not in _GENERIC_FAMILIES:
            return candidate
    return None


# family-name resolution cache (independent of the metrics cache: it answers
# "what face will fontconfig actually draw?", not "what are its advances?").
_FAMILY_CACHE: dict[str, str | None] = {}


def resolve_family_name(font_family: str) -> str | None:
    """The family name fontconfig resolves a CSS chain's first concrete entry to
    (``fc-match -f %{family}``), or ``None`` when unverifiable (no ``fc-match``,
    generic-only chain, or fc-match failure).

    This is the missing-font feedback primitive: when the returned name differs
    from the requested family, the rasterizer will silently substitute another
    face — surface that to the author instead of letting pixel diffs reveal it."""
    target = first_concrete_family(font_family or "")
    if target is None:
        return None
    if target in _FAMILY_CACHE:
        return _FAMILY_CACHE[target]
    resolved: str | None = None
    if shutil.which("fc-match") is not None:
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{family}", target],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            resolved = result.stdout.strip() or None
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            resolved = None
    _FAMILY_CACHE[target] = resolved
    return resolved


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
