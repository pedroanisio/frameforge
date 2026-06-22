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


__all__ = ["md", "paragraph", "theme"]
