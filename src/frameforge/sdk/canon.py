"""Johnston's typographic canon — modular scale, margin canon, measure.

Codifies the practical rules of Edward Johnston, *Writing & Illuminating, &
Lettering* (London, 1906) — the foundation text of modern lettering education —
as small pure helpers for document authors:

- :func:`modular_scale` — sizes drawn from one ratio agree before they are
  used (uniformity, Johnston's fifth quality, applied to size).
- :func:`johnston_margins` / :func:`content_box` — the margin canon for a book
  opening: **inner 1½ · top 2 · outer 3 · foot 4** ("proportions … common in
  early MSS", ch. VI). Readers hold books by the foot; the two inner margins
  read as one gutter; centred text appears to sag, so the top tightens.
- :data:`MEASURE_MIN` / :data:`MEASURE_MAX` / :func:`measure_fits` — the
  45–75 characters-per-line comfort band for continuous reading.
- :func:`caps_tracking` — capitals want air: a letter-spacing amount for
  all-caps settings (lowercase wants none).

Example::

    from frameforge.sdk import canon

    sizes = canon.modular_scale(base=11.5, ratio=1.25)   # caption … cover
    box = canon.content_box(794, 1123, unit=40, side="recto")
    kicker_tracking = canon.caps_tracking(sizes["caption"])
"""
from __future__ import annotations

# Default rung names, small → large (the book-design register).
SCALE_NAMES: tuple[str, ...] = (
    "caption", "body", "lead", "h3", "h2", "h1", "display", "cover",
)

# Comfortable measure for continuous reading, in characters per line.
MEASURE_MIN: int = 45
MEASURE_MAX: int = 75

# The canonical margin proportions for a book opening (inner:top:outer:foot).
MARGIN_CANON: dict[str, float] = {"inner": 1.5, "top": 2.0, "outer": 3.0, "foot": 4.0}


def modular_scale(base: float, ratio: float = 1.25,
                  names: "list[str] | tuple[str, ...] | None" = None) -> dict[str, float]:
    """Named sizes as exact powers of one ratio: ``base * ratio**i``.

    Sizes chosen one by one drift; sizes drawn from a ratio agree before they
    are used — the same discipline a chord imposes on notes. The ratio is a
    voice: 1.2 quiet and bookish, 1.25 assertive, 1.333 editorial, 1.5
    poster-loud. What matters is that the whole document draws from one.
    """
    if base <= 0 or ratio <= 1:
        raise ValueError("modular_scale needs base > 0 and ratio > 1")
    rungs = tuple(names) if names is not None else SCALE_NAMES
    return {name: base * ratio ** i for i, name in enumerate(rungs)}


def johnston_margins(unit: float) -> dict[str, float]:
    """The margin canon scaled by one unit: inner 1½u, top 2u, outer 3u, foot 4u.

    The opening — not the page — is the design unit: the two inner margins
    combine to equal one outer, so a spread reads as one sheet with two
    columns. Choose ``unit`` from the page (a common start: ~1/20 of the page
    width) and the four margins follow.
    """
    if unit <= 0:
        raise ValueError("unit must be positive")
    return {name: proportion * unit for name, proportion in MARGIN_CANON.items()}


def content_box(page_w: float, page_h: float, unit: float,
                side: str = "recto") -> tuple[float, float, float, float]:
    """The text block ``(x, y, w, h)`` the margin canon leaves on one page.

    ``side="recto"`` puts the inner margin left (right-hand page);
    ``side="verso"`` mirrors it. Feed the result straight to a page layer as
    the prose column's box.
    """
    margins = johnston_margins(unit)
    if side == "recto":
        x = margins["inner"]
    elif side == "verso":
        x = margins["outer"]
    else:
        raise ValueError("side must be 'recto' or 'verso'")
    width = page_w - margins["inner"] - margins["outer"]
    height = page_h - margins["top"] - margins["foot"]
    if width <= 0 or height <= 0:
        raise ValueError("margin unit leaves no content area on this page")
    return (x, margins["top"], width, height)


def measure_fits(chars_per_line: float) -> bool:
    """True when a measure sits in the 45–75 characters-per-line comfort band."""
    return MEASURE_MIN <= chars_per_line <= MEASURE_MAX


def caps_tracking(font_size: float, percent: float = 6.0) -> float:
    """Letter-spacing (px) for an all-caps setting: capitals want air.

    Johnston's rule is qualitative — distinctiveness "necessitates sufficient
    interspaces", but sufficiency, not surplus. The default of 6% of the font
    size is a serviceable convention for kickers and labels; small letters
    want none (a word is a fitted thing).
    """
    if font_size <= 0:
        raise ValueError("font_size must be positive")
    return font_size * percent / 100.0


__all__ = [
    "MARGIN_CANON",
    "MEASURE_MAX",
    "MEASURE_MIN",
    "SCALE_NAMES",
    "caps_tracking",
    "content_box",
    "johnston_margins",
    "measure_fits",
    "modular_scale",
]
