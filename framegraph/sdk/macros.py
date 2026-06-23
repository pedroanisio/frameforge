"""Authoring macros that lower to ordinary FrameGraph model fragments."""
from __future__ import annotations

import re
from typing import Any

from framegraph.sdk.author import DocumentBuilder, Handle

_TOKEN_RE = re.compile(r"(`[^`]+`|\$[^$]+\$|\[[^\]]+\]\([^)]+\))")


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


def md(text: str) -> list[Any]:
    """Lower a small Markdown inline subset to FrameGraph ``Inline`` values."""
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
        else:
            label, href = token[1:].split("](", 1)
            out.append({"kind": "link", "href": href[:-1], "content": [label]})
        pos = match.end()
    if pos < len(text):
        out.append(text[pos:])
    return [part for part in out if part != ""]


def paragraph(text: str, **fields: Any) -> dict[str, Any]:
    """Create a paragraph flow, using spans when Markdown inline forms appear."""
    spans = md(text)
    if len(spans) == 1 and isinstance(spans[0], str):
        return {"type": "paragraph", "text": spans[0], **fields}
    return {"type": "paragraph", "spans": spans, **fields}


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


__all__ = ["lorem", "lorem_paragraphs", "md", "paragraph", "theme"]
