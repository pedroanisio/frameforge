"""Authoring macros that lower to ordinary FrameGraph model fragments."""
from __future__ import annotations

import re
from random import Random
from typing import Any, Sequence

from framegraph.sdk.author import DocumentBuilder, Handle
from framegraph.sdk.geometry import Path
from framegraph.sdk.paint import hatch, stroke

_TOKEN_RE = re.compile(
    r"(`[^`]+`"                                  # `code`
    r"|\$[^$]+\$"                                # $math$
    r"|\{(?:ref|pageref|nameref|cite):[^}]+\}"   # {ref:id} {pageref:id} {nameref:id} {cite:key}
    r"|\[[^\]]+\]\([^)]+\))"                     # [label](href)
)


def theme(
    builder: DocumentBuilder,
    *,
    colors: dict[str, str] | None = None,
    text_styles: dict[str, dict[str, Any]] | None = None,
    styles: dict[str, dict[str, Any]] | None = None,
    stroke_styles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Handle]:
    """Define a batch of theme tokens and return their handles by name."""
    handles: dict[str, Handle] = {}
    for name, value in (colors or {}).items():
        handles[name] = builder.define_color(name, value)
    for name, value in (text_styles or {}).items():
        handles[name] = builder.define_text_style(name, **value)
    for name, value in (styles or {}).items():
        handles[name] = builder.define_style(name, **value)
    for name, value in (stroke_styles or {}).items():
        handles[name] = builder.define_stroke_style(name, **value)
    return handles


_REF_SHOW = {"ref": None, "pageref": "page", "nameref": "title"}


def md(text: str) -> list[Any]:
    """Lower a small Markdown inline subset to FrameGraph ``Inline`` values.

    Handles `` `code` ``, ``$math$`` and ``[label](href)`` links, plus a
    FrameGraph cross-reference/citation extension: ``{ref:id}`` (the target's
    number), ``{pageref:id}`` (its page), ``{nameref:id}`` (its title) and
    ``{cite:key}`` (a bibliography citation). See :func:`ref` / :func:`cite`."""
    out: list[Any] = []
    pos = 0
    for match in _TOKEN_RE.finditer(text):
        if match.start() > pos:
            out.append(text[pos : match.start()])
        token = match.group(0)
        if token.startswith("`"):
            out.append({"kind": "code", "text": token[1:-1]})
        elif token.startswith("$"):
            out.append({"kind": "math", "tex": token[1:-1]})
        elif token.startswith("{"):
            kind, _, target = token[1:-1].partition(":")
            if kind == "cite":
                out.append(cite(target))
            else:
                out.append(ref(target, show=_REF_SHOW[kind]))
        else:
            label, href = token[1:].split("](", 1)
            out.append({"kind": "link", "href": href[:-1], "content": [label]})
        pos = match.end()
    if pos < len(text):
        out.append(text[pos:])
    return [part for part in out if part != ""]


def ref(target: str, *, show: str | None = None) -> dict[str, Any]:
    """A cross-reference ``Inline`` to a labelled object (``id``).

    ``show`` selects what is rendered: ``None``/``"number"`` the target's number
    (LaTeX ``\\ref``), ``"page"`` its page (``\\pageref``), ``"title"`` its title
    (``\\nameref``), ``"label"`` its label. Renderers that resolve references
    substitute the live value; others fall back to the visible text."""
    inline: dict[str, Any] = {"kind": "ref", "target": str(target)}
    if show is not None:
        inline["show"] = show
    return inline


def cite(key: str | list[str], *, prefix: str | None = None,
         locator: str | None = None, mode: str | None = None) -> dict[str, Any]:
    """A bibliography citation ``Inline`` to one or more entry ``key``s.

    ``locator`` is a page/section pointer (``"p. 12"``); ``mode`` selects the
    style (``"parenthetical"``, ``"textual"``, …). Lowers to LaTeX ``\\cite``."""
    inline: dict[str, Any] = {"kind": "cite", "key": key}
    if prefix is not None:
        inline["prefix"] = prefix
    if locator is not None:
        inline["locator"] = locator
    if mode is not None:
        inline["mode"] = mode
    return inline


def paragraph(text: str, **fields: Any) -> dict[str, Any]:
    """Create a paragraph flow, using spans when Markdown inline forms appear."""
    spans = md(text)
    if len(spans) == 1 and isinstance(spans[0], str):
        return {"type": "paragraph", "text": spans[0], **fields}
    return {"type": "paragraph", "spans": spans, **fields}


def hatch_fill(
    box: Sequence[float],
    *,
    fg: str = "#64748b",
    bg: str | None = None,
    scale: float = 8.0,
    angle: float = 45.0,
    **fields: Any,
) -> list[dict[str, Any]]:
    """Return a hatch-filled rect object for procedural texture.

    The macro returns a list so it composes with :meth:`PageBuilder.extend` and
    can grow later without changing its call shape.
    """
    return [
        {
            "type": "rect",
            "box": list(box),
            "fill": hatch(fg=fg, bg=bg, scale=scale, angle=angle),
            **fields,
        }
    ]


def grid_lines(
    box: Sequence[float],
    *,
    cols: int = 0,
    rows: int = 0,
    color: str = "#cbd5e1",
    width: float = 1.0,
    **fields: Any,
) -> list[dict[str, Any]]:
    """Return evenly spaced guide/grid lines inside ``box``."""
    x, y, w, h = _box(box)
    style = stroke(width, color=color)
    style.update(fields)
    objects: list[dict[str, Any]] = []
    for i in range(1, max(0, int(cols))):
        xx = x + w * i / cols
        objects.append({"type": "line", "from": [xx, y], "to": [xx, y + h], **style})
    for i in range(1, max(0, int(rows))):
        yy = y + h * i / rows
        objects.append({"type": "line", "from": [x, yy], "to": [x + w, yy], **style})
    return objects


def greeble(
    box: Sequence[float],
    *,
    seed: int = 0,
    density: float = 0.25,
    fill: str = "#94a3b8",
    stroke_color: str | None = None,
    min_size: float = 4.0,
    max_size: float = 18.0,
    **fields: Any,
) -> list[dict[str, Any]]:
    """Return deterministic small rect details inside ``box``.

    ``density`` is intentionally coarse: it scales object count by area while
    keeping fixtures stable and bounded.
    """
    x, y, w, h = _box(box)
    rng = Random(seed)
    count = max(1, min(160, int((w * h / 1200.0) * max(0.05, density))))
    objects: list[dict[str, Any]] = []
    for _ in range(count):
        rw = rng.uniform(min_size, max_size)
        rh = rng.uniform(min_size, max_size)
        obj: dict[str, Any] = {
            "type": "rect",
            "box": [
                rng.uniform(x, max(x, x + w - rw)),
                rng.uniform(y, max(y, y + h - rh)),
                rw,
                rh,
            ],
            "fill": fill,
            **fields,
        }
        if stroke_color is not None:
            obj.update(stroke(1, color=stroke_color))
        objects.append(obj)
    return objects


def sparkline(
    points: Sequence[Sequence[float]],
    box: Sequence[float],
    *,
    color: str = "#2563eb",
    width: float = 2.0,
    smooth: bool = True,
    **fields: Any,
) -> dict[str, Any]:
    """Map data points into ``box`` and return a line/path object."""
    pts = [tuple(float(v) for v in p[:2]) for p in points]
    if len(pts) < 2:
        raise ValueError("sparkline needs at least two points")
    x, y, w, h = _box(box)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    dx = x1 - x0 or 1.0
    dy = y1 - y0 or 1.0
    mapped = [[x + (px - x0) / dx * w, y + h - (py - y0) / dy * h] for px, py in pts]
    style = {"fill": "none", **stroke(width, color=color), **fields}
    if smooth:
        return Path().through(mapped).object(**style)
    return {"type": "polyline", "points": mapped, **style}


# Classic lorem-ipsum word pool and the canonical opening clause.
_LOREM_WORDS = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua enim ad minim veniam quis nostrud "
    "exercitation ullamco laboris nisi aliquip ex ea commodo consequat duis aute "
    "irure in reprehenderit voluptate velit esse cillum eu fugiat nulla pariatur "
    "excepteur sint occaecat cupidatat non proident sunt culpa qui officia deserunt "
    "mollit anim id est laborum"
).split()
_LOREM_OPENER = "lorem ipsum dolor sit amet consectetur adipiscing elit".split()
# Varying sentence lengths so output reads like prose, not a fixed grid.
_LOREM_SENT_LENS = (8, 12, 6, 14, 9, 11, 7, 13, 10)


def _lorem_sentence(words: list[str]) -> str:
    """Join words into one capitalised, period-terminated sentence with a comma."""
    words = list(words)
    if len(words) >= 6:
        i = len(words) * 3 // 5
        words[i] = words[i] + ","
    text = " ".join(words)
    return text[:1].upper() + text[1:] + "."


def lorem(sentences: int = 3, *, words: int | None = None,
          start: bool = True, offset: int = 0) -> str:
    """Return deterministic lorem-ipsum filler text.

    By default returns ``sentences`` sentences of varying length. Pass ``words``
    to instead return exactly that many words as one capitalised, period-ended
    string. ``start`` opens with the canonical "Lorem ipsum dolor sit amet …".
    ``offset`` rotates the word stream so repeated calls can differ. The output
    is purely a function of the arguments (no RNG), so fixtures and golden
    renders stay stable. See :func:`lorem_paragraphs` for multi-paragraph text.
    """
    pool = _LOREM_WORDS
    if words is not None:
        n = max(1, int(words))
        if start:
            tail = [pool[(offset + i) % len(pool)]
                    for i in range(max(0, n - len(_LOREM_OPENER)))]
            picked = (_LOREM_OPENER + tail)[:n]
        else:
            picked = [pool[(offset + i) % len(pool)] for i in range(n)]
        return _lorem_sentence(picked)

    out: list[str] = []
    idx = offset
    for s in range(max(1, int(sentences))):
        length = _LOREM_SENT_LENS[(s + offset) % len(_LOREM_SENT_LENS)]
        if s == 0 and start:
            picked = list(_LOREM_OPENER)
        else:
            picked = [pool[(idx + i) % len(pool)] for i in range(length)]
            idx += length
        out.append(_lorem_sentence(picked))
    return " ".join(out)


def lorem_paragraphs(count: int = 1, *, sentences: int = 4, start: bool = True) -> list[str]:
    """Return ``count`` lorem-ipsum paragraphs as a list of strings.

    Each paragraph is rotated so they differ; only the first opens with the
    canonical "Lorem ipsum …" when ``start`` is true. Handy for filling a
    ``mode: flow`` story or several text boxes.
    """
    return [
        lorem(sentences=sentences, start=(start and i == 0), offset=i * 7)
        for i in range(max(1, int(count)))
    ]


def _box(box: Sequence[float]) -> tuple[float, float, float, float]:
    if len(box) != 4:
        raise ValueError(f"box must have four values; got {box!r}")
    return tuple(float(v) for v in box)  # type: ignore[return-value]


__all__ = [
    "cite",
    "greeble",
    "grid_lines",
    "hatch_fill",
    "lorem",
    "lorem_paragraphs",
    "md",
    "paragraph",
    "ref",
    "sparkline",
    "theme",
]
