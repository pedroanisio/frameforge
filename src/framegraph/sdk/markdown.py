"""Document-level Markdown → a FrameGraph flow document.

The SDK already lowers *inline* Markdown (:func:`framegraph.sdk.macros.md` —
``**bold**``, `` `code` ``, links, ``$math$``). This module adds the document
level: :func:`from_markdown` converts a CommonMark/GFM-subset text into a
validated ``mode: flow`` page, so pagination, text fitting and list/table
layout come from the flow engine instead of hand-rolled geometry
(absorption issue #31; the sibling project's converter re-imagined for v2).

Coverage — hand-rolled line parser, no new dependency:

- headings ``#``–``######`` → ``heading`` flowables (H1 doubles as the
  document title when none is given);
- paragraphs → ``paragraph`` (inline forms via the existing ``md()``
  lowering — one inline parser, not two);
- ``-``/``*``/``+`` and ``1.`` lists → ``list`` (the model has no nested
  list: indented sub-items fold into their parent item as ``•``-marked
  continuation lines — a documented flattening);
- GFM pipe tables → ``table``;
- fenced code blocks → ``code`` (language-tagged);
- ``>`` block quotes → a ``block`` with ``role: blockquote``;
- image-only paragraphs ``![alt](src)`` → ``image``;
- thematic breaks (``---``/``***``/``___``) → ``page_break``;
- YAML front-matter (``title``/``lang``/``profile``/``canvas``/``master``);
- ```` ```framegraph ```` pattern directives degrade to a structured
  warning until the pattern bridge (#29) lands — never a silent drop.

The returned document has been through :func:`~framegraph.sdk.model
.validate_document` — converter output is untrusted until the schema says
otherwise (PALS's Law)::

    from framegraph.sdk import from_markdown
    doc = from_markdown(open("notes.md").read())

The CLI front door accepts ``.md`` inputs directly and routes them here.
"""
from __future__ import annotations

import re
from typing import Any

from framegraph.sdk.flow import FlowBuilder
from framegraph.sdk.model import HEAD_VERSION, validate_document

# A4 in pt with a uniform margin — the default master a converted document
# flows into; override wholesale via ``master=``.
_DEFAULT_MASTER = {
    "canvas": {"preset": "A4"},
    "regions": [{"id": "body", "box": [48, 48, 499.5, 746.25]}],
}

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^(```+|~~~+)\s*([\w-]*)\s*$")
_HR = re.compile(r"^ {0,3}((-\s*){3,}|(\*\s*){3,}|(_\s*){3,})$")
_ULIST = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_OLIST = re.compile(r"^(\s*)\d{1,9}[.)]\s+(.*)$")
_IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _front_matter(lines: list[str]) -> tuple[dict[str, Any], int]:
    if not lines or lines[0].strip() != "---":
        return {}, 0
    for end in range(1, len(lines)):
        if lines[end].strip() in ("---", "..."):
            import yaml
            try:
                meta = yaml.safe_load("\n".join(lines[1:end])) or {}
            except yaml.YAMLError:
                return {}, 0
            return (meta if isinstance(meta, dict) else {}), end + 1
    return {}, 0


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _flush_list(fb: FlowBuilder, items: list[str], ordered: bool) -> None:
    if not items:
        return
    (fb.numbered if ordered else fb.bullet)(items)


def from_markdown(
    text: str,
    *,
    title: str | None = None,
    lang: str | None = None,
    profile: str | None = None,
    master: dict[str, Any] | None = None,
    page_id: str = "doc",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Convert a Markdown document to a validated FrameGraph flow document.

    Explicit keyword arguments win over front-matter; the title falls back to
    the first H1. ``warnings`` (optional list) receives one message per
    construct that degrades — today the ```` ```framegraph ```` directive.
    Raises :class:`pydantic.ValidationError` if the conversion is not
    schema-legal (it is validated before it is returned).
    """
    sink = warnings if warnings is not None else []
    lines = text.splitlines()
    meta, start = _front_matter(lines)
    lines = lines[start:]

    fb = FlowBuilder()
    first_h1: str | None = None
    para: list[str] = []
    items: list[str] = []
    items_ordered = False
    quote: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            joined = " ".join(part.strip() for part in para).strip()
            if joined:
                fb.para(joined)
            para = []

    def flush_items() -> None:
        nonlocal items
        _flush_list(fb, items, items_ordered)
        items = []

    def flush_quote() -> None:
        nonlocal quote
        if quote:
            inner = FlowBuilder()
            for chunk in re.split(r"\n\s*\n", "\n".join(quote)):
                chunk = " ".join(chunk.split()).strip()
                if chunk:
                    inner.para(chunk)
            fb.add({"type": "block", "role": "blockquote",
                    "padding": [0, 0, 0, 18], "children": inner.story()})
            quote = []

    def flush_all() -> None:
        flush_para()
        flush_items()
        flush_quote()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        fence = _FENCE.match(stripped)
        if fence:
            flush_all()
            marker, language = fence.group(1)[:3], fence.group(2) or None
            body: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(marker):
                body.append(lines[i])
                i += 1
            i += 1  # closing fence (or EOF)
            if language == "framegraph":
                sink.append(
                    "```framegraph pattern directive skipped — pattern-composed "
                    "blocks arrive with the fill/render bridge (#29); the "
                    "directive body was not converted")
            else:
                fb.code("\n".join(body), language)
            continue

        if not stripped:
            flush_all()
            i += 1
            continue

        if _HR.match(stripped):
            flush_all()
            fb.page_break()
            i += 1
            continue

        heading = _HEADING.match(stripped)
        if heading:
            flush_all()
            level, htext = len(heading.group(1)), heading.group(2)
            if level == 1 and first_h1 is None:
                first_h1 = htext
            fb.heading(level, htext)
            i += 1
            continue

        if stripped.startswith(">"):
            flush_para(), flush_items()
            quote.append(stripped.lstrip(">").strip())
            i += 1
            continue
        if quote:
            flush_quote()

        image = _IMAGE.match(stripped)
        if image:
            flush_all()
            fb.image(image.group(2), alt=image.group(1) or None)
            i += 1
            continue

        if "|" in stripped and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            flush_all()
            columns = _split_row(stripped)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            fb.table(columns, rows)
            continue

        ul, ol = _ULIST.match(line), _OLIST.match(line)
        if ul or ol:
            flush_para(), flush_quote()
            indent = len((ul or ol).group(1))
            itext = (ul or ol).group(2).strip()
            ordered = bool(ol)
            if indent and items:
                # the model has no nested list: fold sub-items into the parent
                # item as marked continuation lines (documented flattening)
                items[-1] = f"{items[-1]}\n• {itext}"
            else:
                if items and ordered != items_ordered:
                    flush_items()
                items_ordered = ordered
                items.append(itext)
            i += 1
            continue

        if items and (line.startswith("  ") or line.startswith("\t")):
            items[-1] = f"{items[-1]} {stripped}"   # lazy continuation of an item
            i += 1
            continue
        flush_items()

        para.append(stripped)
        i += 1

    flush_all()

    resolved_title = title or meta.get("title") or first_h1
    doc: dict[str, Any] = {"dsl": "FrameGraph", "version": HEAD_VERSION}
    if resolved_title:
        doc["title"] = str(resolved_title)
    if lang or meta.get("lang"):
        doc["lang"] = str(lang or meta["lang"])
    if profile or meta.get("profile"):
        doc["profile"] = str(profile or meta["profile"])
    doc["defs"] = {"masters": {"doc": master or meta.get("master") or dict(_DEFAULT_MASTER)}}
    doc["pages"] = [{"mode": "flow", "id": page_id, "master": "doc", "story": fb.story()}]

    validate_document(doc)   # PALS: converter output is unverified until here
    return doc


__all__ = ["from_markdown"]
