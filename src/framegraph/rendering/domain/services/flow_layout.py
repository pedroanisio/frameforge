"""Backend-neutral flow layout — the single typographic authority for prose.

Owns the two decisions a rasterizer cannot make well for you: **where lines
break** and **where words hyphenate**. It does *not* hand-place glyphs — that is
the rasterizer's job with its own real metrics — so it never fights the renderer
over sub-pixel advances (the cause of uneven "river" gaps). A document therefore
has one set of line/hyphenation breaks (and thus one pagination) regardless of
backend (ADR-0003, extending ADR-0001's backend-neutral drawing up to layout);
each backend then justifies the given line with its own shaper.

Algorithms, not heuristics:

- **Line breaking** is Knuth & Plass total-fit — *Breaking Paragraphs into
  Lines*, Software: Practice and Experience 11(11):1119–1184 (1981) — which
  minimises the sum of squared line "badness" over the whole paragraph, so one
  bad break can never cascade into loose lines (the greedy/first-fit failure).
- **Hyphenation** is Liang's pattern method (via ``pyphen``; F. M. Liang,
  *Word Hy-phen-a-tion by Com-put-er*, Stanford, 1983), so slack that would open
  a river is absorbed by breaking a long word instead. Absent ``pyphen`` the
  engine still runs — it just cannot hyphenate.

Geometry (`content_box`) resolves the column from the page master: explicit
region box → master margin → the Johnston canon (inner 1½ / top 2 / outer 3 /
foot 4, mirrored recto/verso).

Pure and dependency-inverted: `measure` — ``(text, size, avg) -> width|None`` —
is injected; the output is a plain value tree of `LaidLine`s.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

Measure = Callable[[str, float, float], Optional[float]]

# Knuth–Plass demerit weights (line penalty, hyphen penalty, consecutive-hyphen).
_LINE_PENALTY = 10.0
_HYPHEN_PENALTY = 50.0
_DOUBLE_HYPHEN = 3000.0
_INF = float("inf")

# The canon proportions (mirror framegraph.sdk.canon.MARGIN_CANON; kept local to
# avoid a rendering→sdk dependency — test_flow_layout pins the two in agreement).
_INNER, _TOP, _OUTER, _FOOT = 1.5, 2.0, 3.0, 4.0

_DASH = "—–"                              # em / en dash — a break opportunity


# --------------------------------------------------------------------------- #
#  Positioned layout IR                                                        #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LaidLine:
    """One laid-out line: its ``text`` (with a trailing ``-`` when the line ends
    on a hyphenation break), the left ``indent`` (first-line indent), the
    vertical ``advance`` to the next baseline (constant leading = baseline grid),
    the justification target ``width`` (the column width available to this line),
    and whether it should be ``justify``-set (all but the last/short line)."""
    text: str
    indent: float
    advance: float
    width: float
    justify: bool


@dataclass(frozen=True)
class LaidParagraph:
    lines: tuple[LaidLine, ...] = ()
    space_after: float = 0.0


# --------------------------------------------------------------------------- #
#  Geometry — the single source of the column box                             #
# --------------------------------------------------------------------------- #
def content_box(master: Optional[dict], page_w: float, page_h: float,
                page_index: int, *, unit: Optional[float] = None
                ) -> tuple[float, float, float, float]:
    """The prose column ``(x, y, w, h)`` for one page.

    Priority: explicit master region ``box`` → master ``margin``
    (``[top, right, bottom, left]``) → the Johnston canon. ``page_index`` is
    1-based; odd pages are recto (inner margin left), even verso (mirrored) —
    which only affects the canon fallback and any asymmetric margin.
    """
    if master:
        regions = master.get("regions")
        if isinstance(regions, list) and regions:
            box = regions[0].get("box") if isinstance(regions[0], dict) else None
            if isinstance(box, (list, tuple)) and len(box) >= 4:
                return (box[0], box[1], box[2], box[3])
        margin = master.get("margin")
        if isinstance(margin, (list, tuple)) and len(margin) == 4:
            top, right, bottom, left = margin
            return (left, top, page_w - left - right, page_h - top - bottom)

    u = unit if unit is not None else page_w / 20.0
    inner, top, outer, foot = _INNER * u, _TOP * u, _OUTER * u, _FOOT * u
    recto = (page_index % 2) == 1
    x = inner if recto else outer
    return (x, top, page_w - inner - outer, page_h - top - foot)


# --------------------------------------------------------------------------- #
#  Hyphenation (Liang patterns via pyphen; optional)                          #
# --------------------------------------------------------------------------- #
_HYPH: object = "unset"


def _hyphenator():
    global _HYPH
    if _HYPH == "unset":
        try:
            import pyphen
            _HYPH = pyphen.Pyphen(lang="en_US")
        except Exception:
            _HYPH = None
    return _HYPH


def _syllables(word: str, hyph) -> list[str]:
    """Fragments a word may break into (Liang points); the whole word if it is
    short, non-alphabetic, or no hyphenator is present."""
    if hyph is None or len(word) < 6 or not word.isalpha():
        return [word]
    positions = hyph.positions(word)
    if not positions:
        return [word]
    frags, prev = [], 0
    for p in positions:
        frags.append(word[prev:p])
        prev = p
    frags.append(word[prev:])
    return frags


# --------------------------------------------------------------------------- #
#  Knuth–Plass line breaking                                                    #
# --------------------------------------------------------------------------- #
# An item is a tuple: ("box", w, text) | ("glue", w, stretch, shrink) |
#                     ("pen", w, cost, flagged)
def _build_items(text: str, mw: Callable[[str], float], space_w: float):
    stretch, shrink, hyph_w = space_w * 0.6, space_w * 0.35, mw("-")
    hyph = _hyphenator()
    items: list[tuple] = []
    for wi, word in enumerate(text.split()):
        if wi:
            items.append(("glue", space_w, stretch, shrink))
        parts = re.split(rf"(?<=[{_DASH}])", word)   # break after an em/en dash
        for pi, part in enumerate(parts):
            frags = _syllables(part, hyph)
            for fi, frag in enumerate(frags):
                if frag:
                    items.append(("box", mw(frag), frag))
                if fi < len(frags) - 1:
                    items.append(("pen", hyph_w, _HYPHEN_PENALTY, True))
            if pi < len(parts) - 1:
                items.append(("pen", 0.0, 0.0, False))   # dash break, no added hyphen
    return items


def _linebreak(items: list[tuple], target_first: float, target_rest: float,
               tolerance: float) -> Optional[list[str]]:
    """Total-fit break. Returns the list of line strings (trailing ``-`` on a
    hyphen break), or None if no feasible breaking exists at this tolerance."""
    n = len(items)
    W = [0.0] * (n + 1)
    Y = [0.0] * (n + 1)
    Z = [0.0] * (n + 1)
    for i, it in enumerate(items):
        w = y = z = 0.0
        if it[0] == "box":
            w = it[1]
        elif it[0] == "glue":
            w, y, z = it[1], it[2], it[3]
        W[i + 1], Y[i + 1], Z[i + 1] = W[i] + w, Y[i] + y, Z[i] + z

    def legal(i: int) -> bool:
        it = items[i]
        if it[0] == "glue":
            return i > 0 and items[i - 1][0] == "box"
        if it[0] == "pen":
            return it[2] < _INF
        return False

    breaks = [i for i in range(n) if legal(i)] + [n]     # n = forced final break
    # best[bp] = (total_demerits, prev_bp, line_no, flagged)
    best: dict[int, tuple] = {-1: (0.0, -1, 0, False)}
    for b in breaks:
        chosen = (_INF, None, None, None)
        for a in ([-1] + breaks):
            if a >= b:
                break
            node = best.get(a)
            if node is None:
                continue
            base, _, line_no_a, flagged_a = node
            start = a + 1
            is_pen_b = (b < n and items[b][0] == "pen")
            L = W[b] - W[start] + (items[b][1] if is_pen_b else 0.0)
            st_, sh_ = Y[b] - Y[start], Z[b] - Z[start]
            target = target_first if line_no_a == 0 else target_rest
            is_last = (b == n)
            if is_last:
                if L > target:
                    r = (target - L) / sh_ if sh_ > 0 else -_INF
                    if r < -1:
                        continue
                    badness = 100.0 * abs(r) ** 3
                else:
                    badness = 0.0                       # last line sets ragged (short is free)
                pen_cost, flagged_b = 0.0, False
            else:
                if L > target:
                    r = (target - L) / sh_ if sh_ > 0 else -_INF
                elif L < target:
                    r = (target - L) / st_ if st_ > 0 else _INF
                else:
                    r = 0.0
                if r < -1 or r > tolerance:
                    continue
                badness = 100.0 * abs(r) ** 3
                flagged_b = bool(is_pen_b and items[b][3])
                pen_cost = items[b][2] if is_pen_b else 0.0
            demerit = (_LINE_PENALTY + badness) ** 2 + (pen_cost if pen_cost > 0 else 0.0)
            if flagged_b and flagged_a:
                demerit += _DOUBLE_HYPHEN
            total = base + demerit
            if total < chosen[0]:
                chosen = (total, a, line_no_a + 1, flagged_b)
        if chosen[1] is not None:
            best[b] = chosen

    if n not in best:
        return None
    # reconstruct
    spans: list[tuple[int, int]] = []
    b = n
    while b != -1:
        _, a, _, _ = best[b]
        spans.append((a, b))
        b = a
    spans.reverse()
    lines: list[str] = []
    for a, b in spans:
        parts: list[str] = []
        for i in range(a + 1, b):
            it = items[i]
            if it[0] == "box":
                parts.append(it[2])
            elif it[0] == "glue":
                parts.append(" ")
        text = "".join(parts).strip()
        if b < n and items[b][0] == "pen" and items[b][3]:
            text += "-"
        lines.append(text)
    return lines


def _greedy_lines(text: str, mw: Callable[[str], float], space_w: float,
                  width: float, first_indent: float) -> list[str]:
    """First-fit fallback (used for non-justified alignment and as a safety net)."""
    words = text.split()
    lines, cur = [], []
    cur_w = 0.0
    for word in words:
        ww = mw(word)
        avail = width - (first_indent if not lines else 0.0)
        add = ww if not cur else cur_w + space_w + ww
        if cur and add > avail:
            lines.append(" ".join(cur))
            cur, cur_w = [word], ww
        else:
            cur.append(word)
            cur_w = add
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]


# --------------------------------------------------------------------------- #
#  Paragraph layout                                                            #
# --------------------------------------------------------------------------- #
def layout_paragraph(text: str, *, size: float, avg: float, lh: float,
                     width: float, measure: Measure, align: str = "justify",
                     first_line_indent: float = 0.0,
                     space_after: float = 0.0) -> LaidParagraph:
    """Break ``text`` to ``width`` and return its laid-out lines.

    ``align="justify"`` uses Knuth–Plass + hyphenation and marks every line but
    the last as ``justify`` (the painter stretches those to their ``width`` with
    its own metrics). Any other alignment uses first-fit and leaves lines natural.
    ``first_line_indent`` shifts and narrows the first line only. Vertical advance
    is constant leading (``size * lh``).
    """
    def mw(s: str) -> float:
        w = measure(s, size, avg)
        return float(w) if w is not None else len(s) * size * avg

    if not text.split():
        return LaidParagraph((), space_after)

    space_w = mw(" ") or size * avg * 0.5
    tf, tr = width - first_line_indent, width

    line_texts: Optional[list[str]] = None
    if align == "justify":
        items = _build_items(text, mw, space_w)
        line_texts = (_linebreak(items, tf, tr, tolerance=3.0)
                      or _linebreak(items, tf, tr, tolerance=_INF))
    if line_texts is None:
        line_texts = _greedy_lines(text, mw, space_w, width, first_line_indent)

    advance = size * lh
    last = len(line_texts) - 1
    lines = tuple(
        LaidLine(
            text=txt,
            indent=first_line_indent if i == 0 else 0.0,
            advance=advance,
            width=width - (first_line_indent if i == 0 else 0.0),
            justify=(align == "justify" and i != last and bool(txt)),
        )
        for i, txt in enumerate(line_texts)
    )
    return LaidParagraph(lines, space_after)


__all__ = [
    "LaidLine",
    "LaidParagraph",
    "Measure",
    "content_box",
    "layout_paragraph",
]
