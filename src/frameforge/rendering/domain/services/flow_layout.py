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

# The canon proportions (mirror frameforge.sdk.canon.MARGIN_CANON; kept local to
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
    start: int = 0          # [start,end) char span of this line in the source text
    end: int = 0            # (lets a caller re-slice styled runs onto the line)


@dataclass(frozen=True)
class LaidParagraph:
    lines: tuple[LaidLine, ...] = ()
    space_after: float = 0.0


# --------------------------------------------------------------------------- #
#  Geometry — the single source of the column box                             #
# --------------------------------------------------------------------------- #
def _num(v, default: float = 0.0) -> float:
    """Coerce a Length (number or leading-numeric string like '72px') to float."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.match(r"\s*(-?\d+(?:\.\d+)?)", v)
        if m:
            return float(m.group(1))
    return float(default)


def content_box(master: Optional[dict], page_w: float, page_h: float,
                page_index: int, *, unit: Optional[float] = None
                ) -> tuple[float, float, float, float]:
    """The prose column ``(x, y, w, h)`` for one page.

    Priority: explicit master region ``box`` → master ``margin``
    (``[top, right, bottom, left]``) → the Johnston canon. ``page_index`` is
    1-based; odd pages are recto (inner margin left), even verso (mirrored) —
    which only affects the canon fallback and any asymmetric margin.
    """
    recto = (page_index % 2) == 1
    if master:
        regions = master.get("regions")
        if isinstance(regions, list) and regions:
            box = regions[0].get("box") if isinstance(regions[0], dict) else None
            if isinstance(box, (list, tuple)) and len(box) >= 4:
                return tuple(_num(box[i]) for i in range(4))    # coerce Length → float
        margin = master.get("margin")
        if isinstance(margin, (list, tuple)) and len(margin) == 4:
            top, right, bottom, left = (_num(m) for m in margin)
            x = left if recto else right         # mirror an asymmetric margin on verso
            return (x, top, max(1.0, page_w - left - right), max(1.0, page_h - top - bottom))

    u = unit if unit is not None else page_w / 20.0
    inner, top, outer, foot = _INNER * u, _TOP * u, _OUTER * u, _FOOT * u
    x = inner if recto else outer
    return (x, top, max(1.0, page_w - inner - outer), max(1.0, page_h - top - foot))


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
    first = True
    for m in re.finditer(r"\S+", text):          # finditer keeps each word's offset
        word, off = m.group(), m.start()
        if not first:
            items.append(("glue", space_w, stretch, shrink))
        first = False
        parts = re.split(rf"(?<=[{_DASH}])", word)   # break after an em/en dash
        for pi, part in enumerate(parts):
            frags = _syllables(part, hyph)
            for fi, frag in enumerate(frags):
                if frag:                          # box = (kind, width, text, start, end)
                    items.append(("box", mw(frag), frag, off, off + len(frag)))
                off += len(frag)
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
                if L > target and sh_ > 0:
                    r = (target - L) / sh_
                    if r < -1:
                        continue
                    badness = 100.0 * abs(r) ** 3
                elif L > target:                   # unbreakable, wider than the column
                    badness = 1e5 + (L - target)   # allowed (overflow), heavily penalised
                else:
                    badness = 0.0                  # short last line sets ragged (free)
                pen_cost, flagged_b = 0.0, False
            else:
                if L > target and sh_ > 0:
                    r = (target - L) / sh_
                    if r < -1:                     # multi-word line over-compresses: skip
                        continue
                    badness = 100.0 * abs(r) ** 3
                elif L < target and st_ > 0:
                    r = (target - L) / st_
                    if r > tolerance:              # too loose: skip (a hyphen may serve)
                        continue
                    badness = 100.0 * abs(r) ** 3
                elif L == target:
                    badness = 0.0
                elif L > target:
                    # a single unbreakable box WIDER than the column: allow it (overflow)
                    # so one long token never forces the paragraph back to greedy.
                    badness = 1e5 + (L - target)
                elif tolerance >= _INF:
                    # a lone word NARROWER than the column with nothing to stretch: only
                    # the last-resort (infinite-tolerance) pass accepts it.
                    badness = 1e5 + (target - L)
                else:
                    continue                       # infeasible now → KP combines words
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
    lines: list[tuple[str, int, int]] = []
    for a, b in spans:
        parts: list[str] = []
        boxes: list[tuple] = []
        for i in range(a + 1, b):
            it = items[i]
            if it[0] == "box":
                parts.append(it[2])
                boxes.append(it)
            elif it[0] == "glue":
                parts.append(" ")
        text = "".join(parts).strip()
        if b < n and items[b][0] == "pen" and items[b][3]:
            text += "-"
        start = boxes[0][3] if boxes else 0
        end = boxes[-1][4] if boxes else 0
        lines.append((text, start, end))
    return lines


def _greedy_lines(text: str, mw: Callable[[str], float], space_w: float,
                  width: float, first_indent: float) -> list[tuple[str, int, int]]:
    """First-fit fallback (non-justified alignment and KP safety net). Returns
    ``(line_text, start, end)`` so offsets are available on every path."""
    lines: list[list] = []
    cur: list = []
    cur_w = 0.0
    for m in re.finditer(r"\S+", text):
        ww = mw(m.group())
        avail = width - (first_indent if not lines else 0.0)
        add = ww if not cur else cur_w + space_w + ww
        if cur and add > avail:
            lines.append(cur)
            cur, cur_w = [m], ww
        else:
            cur.append(m)
            cur_w = add
    if cur:
        lines.append(cur)
    return [(" ".join(m.group() for m in g), g[0].start(), g[-1].end())
            for g in lines] or [("", 0, 0)]


def slice_runs(runs, start: int, end: int):
    """Sub-runs of ``runs`` — ``[(text, style), …]`` concatenating to the source
    text — covering chars ``[start, end)``, splitting any run that straddles a
    boundary. Lets a caller re-apply inline styles (bold/italic/links) to one
    laid-out line for span-aware justification."""
    out, pos = [], 0
    for text, style in runs:
        rstart, rend = pos, pos + len(text)
        pos = rend
        lo, hi = max(rstart, start), min(rend, end)
        if lo < hi:
            out.append((text[lo - rstart:hi - rstart], style))
    return out


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

    line_texts: Optional[list[tuple[str, int, int]]] = None
    if align == "justify":
        items = _build_items(text, mw, space_w)
        line_texts = (_linebreak(items, tf, tr, tolerance=3.0)
                      or _linebreak(items, tf, tr, tolerance=_INF))
    if line_texts is None:
        line_texts = _greedy_lines(text, mw, space_w, width, first_line_indent)

    advance = size * lh
    last = len(line_texts) - 1
    out = []
    for i, (txt, start, end) in enumerate(line_texts):
        ind = first_line_indent if i == 0 else 0.0
        w_i = width - ind
        # Justify a line only if it has interior word gaps AND already fills a fair
        # part of the column — never stretch a lone/underfull word to full width
        # (that is the cavernous "p r o m p t i n g" letterspacing defect).
        do_justify = (align == "justify" and i != last and bool(txt)
                      and (" " in txt.strip()) and mw(txt) >= 0.5 * w_i)
        out.append(LaidLine(txt, ind, advance, w_i, do_justify, start, end))
    return LaidParagraph(tuple(out), space_after)


__all__ = [
    "LaidLine",
    "LaidParagraph",
    "Measure",
    "content_box",
    "layout_paragraph",
    "slice_runs",
]
