"""Story (``mode: flow``) builders that lower to the model's ``Flowable`` union.

:class:`FlowBuilder` gives every Flowable type — paragraph, heading, list,
spacer, page/column breaks, table, image, figure, block, keep_together, code,
math, toc and bibliography — a typed helper that emits the plain dict the
authoritative model validates. It composes with
:meth:`~frameforge.sdk.DocumentBuilder.section` (the context-manager entry,
symmetric to :meth:`~frameforge.sdk.DocumentBuilder.page`) or standalone via
:meth:`story` + :meth:`~frameforge.sdk.DocumentBuilder.flow`.

Inline Markdown (``**bold**``, ``*italic*``, `` `code` ``, ``$math$``, links and
``{ref:…}`` cross-references) is lowered through :func:`frameforge.sdk.macros.md`
wherever prose is accepted, so story text is rich by default.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from frameforge.sdk.author import Handle, _coerce_handles, _handle_name
from frameforge.sdk.macros import md


class FlowBuilder:
    """Collect ``Flowable`` story items for a ``mode: flow`` section.

    Helpers return the builder for chaining; :meth:`block` and
    :meth:`keep_together` are context managers yielding a nested builder whose
    story becomes the container's children.
    """

    def __init__(self) -> None:
        self._story: list[dict[str, Any]] = []

    # ---- assembly ------------------------------------------------------- #
    def add(self, flowable: dict[str, Any]) -> "FlowBuilder":
        """Append a prebuilt flowable dict (the raw escape hatch)."""
        self._story.append(_coerce_handles(flowable))
        return self

    def extend(self, flowables: list[dict[str, Any]]) -> "FlowBuilder":
        for flowable in flowables:
            self.add(flowable)
        return self

    def story(self) -> list[dict[str, Any]]:
        """Return the collected story (for :meth:`DocumentBuilder.flow`)."""
        return list(self._story)

    # ---- prose ----------------------------------------------------------- #
    def heading(self, level: int, text: str, *, id: str | None = None,
                **fields: Any) -> "FlowBuilder":
        """A section heading (``level`` 1 = chapter). ``id`` makes it a
        ``{ref:id}``/TOC target."""
        obj: dict[str, Any] = {"type": "heading", "level": int(level), "text": str(text)}
        if id is not None:
            obj["id"] = str(id)
        obj.update(fields)
        return self.add(obj)

    def para(self, content: Any, **fields: Any) -> "FlowBuilder":
        """A paragraph. ``content`` is a string (Markdown inline forms are
        lowered to spans via :func:`~frameforge.sdk.macros.md`) or a prepared
        inline list (strings, :func:`~frameforge.sdk.macros.span` dicts, …)."""
        if isinstance(content, (list, tuple)):
            return self.add({"type": "paragraph", "spans": list(content), **fields})
        spans = md(str(content))
        if len(spans) == 1 and isinstance(spans[0], str):
            return self.add({"type": "paragraph", "text": spans[0], **fields})
        return self.add({"type": "paragraph", "spans": spans, **fields})

    def bullet(self, items: list[Any], *, marker: str | None = None,
               **fields: Any) -> "FlowBuilder":
        """An unordered list. String items pass through Markdown inline lowering."""
        return self._list(items, ordered=None, marker=marker, **fields)

    def numbered(self, items: list[Any], **fields: Any) -> "FlowBuilder":
        """An ordered list. String items pass through Markdown inline lowering."""
        return self._list(items, ordered=True, **fields)

    def _list(self, items: list[Any], *, ordered: bool | None,
              marker: str | None = None, **fields: Any) -> "FlowBuilder":
        obj: dict[str, Any] = {"type": "list", "items": [_list_item(i) for i in items]}
        if ordered is not None:
            obj["ordered"] = ordered
        if marker is not None:
            obj["marker"] = marker
        obj.update(fields)
        return self.add(obj)

    # ---- media & display content ----------------------------------------- #
    def image(self, src: Handle | str, *, alt: str | None = None,
              caption: Any = None, credit: Any = None, width: Any = None,
              height: Any = None, **fields: Any) -> "FlowBuilder":
        """An image flowable. ``src`` is an asset handle/name or a path/URL."""
        obj: dict[str, Any] = {"type": "image", "src": _handle_name(src, {"asset"}, "src")}
        _set_optional(obj, alt=alt, caption=caption, credit=credit,
                      width=width, height=height)
        obj.update(fields)
        return self.add(obj)

    def figure(self, object: dict[str, Any], *, caption: Any = None,
               credit: Any = None, alt: str | None = None, id: str | None = None,
               size: Any = None, align: str | None = None,
               **fields: Any) -> "FlowBuilder":
        """A numbered figure wrapping one visual ``object`` (any page primitive)."""
        obj: dict[str, Any] = {"type": "figure", "object": _coerce_handles(object)}
        _set_optional(obj, caption=caption, credit=credit, alt=alt, id=id,
                      size=size, align=align)
        obj.update(fields)
        return self.add(obj)

    def code(self, source: str, language: str | None = None, *,
             line_numbers: bool | None = None, **fields: Any) -> "FlowBuilder":
        """A code listing (monospace block), optionally language-tagged."""
        obj: dict[str, Any] = {"type": "code", "source": str(source)}
        _set_optional(obj, language=language, line_numbers=line_numbers)
        obj.update(fields)
        return self.add(obj)

    def math(self, tex: str | None = None, *, mathml: str | None = None,
             alt: str | None = None, id: str | None = None,
             **fields: Any) -> "FlowBuilder":
        """A display equation (TeX and/or MathML; ``alt`` is the a11y fallback)."""
        obj: dict[str, Any] = {"type": "math"}
        _set_optional(obj, tex=tex, mathml=mathml, alt=alt, id=id)
        obj.update(fields)
        return self.add(obj)

    def table(self, columns: list[Any], rows: list[list[Any]], *,
              header: bool = True, caption: Any = None,
              **fields: Any) -> "FlowBuilder":
        """A table flowable. ``columns`` items are label strings or
        ``{"label", "width", "align"}`` mappings (the :func:`widgets.table`
        convention); ``header=True`` emits the column labels as a header row."""
        labels: list[str] = []
        specs: list[Any] = []
        for col in columns:
            if isinstance(col, dict):
                labels.append(str(col.get("label", "")))
                spec = {k: col[k] for k in ("label", "width", "align") if k in col}
                specs.append(spec or "")
            else:
                labels.append(str(col))
                specs.append(str(col))
        obj: dict[str, Any] = {"type": "table", "rows": [list(r) for r in rows],
                               "columns": specs}
        if header:
            obj["header"] = labels
        _set_optional(obj, caption=caption)
        obj.update(fields)
        return self.add(obj)

    # ---- generated content ------------------------------------------------ #
    def toc(self, *, of: str | None = None, levels: list[int] | None = None,
            title: str | None = None, leader: str | None = None,
            **fields: Any) -> "FlowBuilder":
        """A generated table of contents (``of``: headings/figures/tables/…)."""
        obj: dict[str, Any] = {"type": "toc"}
        _set_optional(obj, of=of, levels=levels, title=title, leader=leader)
        obj.update(fields)
        return self.add(obj)

    def bibliography(self, *, title: str | None = None, source: str | None = None,
                     csl: str | None = None, entries: list[dict] | None = None,
                     **fields: Any) -> "FlowBuilder":
        """A generated bibliography (pairs with ``{cite:key}`` inlines)."""
        obj: dict[str, Any] = {"type": "bibliography"}
        _set_optional(obj, title=title, source=source, csl=csl, entries=entries)
        obj.update(fields)
        return self.add(obj)

    # ---- spacing & breaks -------------------------------------------------- #
    def spacer(self, height: Any = None) -> "FlowBuilder":
        """Vertical whitespace (``height`` is a Length; renderer default if omitted)."""
        obj: dict[str, Any] = {"type": "spacer"}
        _set_optional(obj, height=height)
        return self.add(obj)

    def page_break(self) -> "FlowBuilder":
        return self.add({"type": "page_break"})

    def column_break(self) -> "FlowBuilder":
        return self.add({"type": "column_break"})

    # ---- containers --------------------------------------------------------- #
    @contextmanager
    def block(self, **fields: Any) -> "Iterator[FlowBuilder]":
        """Collect children into a styled ``block`` container (role, fill,
        stroke, padding … pass through as fields)."""
        sub = FlowBuilder()
        yield sub
        self.add({"type": "block", "children": sub.story(), **fields})

    @contextmanager
    def keep_together(self, **fields: Any) -> "Iterator[FlowBuilder]":
        """Collect children that must not be split across a page/column break."""
        sub = FlowBuilder()
        yield sub
        self.add({"type": "keep_together", "children": sub.story(), **fields})


def _list_item(item: Any) -> Any:
    """Lower one list item: dicts/paragraph-lists pass through; strings get
    Markdown inline lowering (plain strings stay plain)."""
    if isinstance(item, dict):
        return item
    if isinstance(item, (list, tuple)):
        return list(item)
    spans = md(str(item))
    if len(spans) == 1 and isinstance(spans[0], str):
        return spans[0]
    return {"spans": spans}


def _set_optional(obj: dict[str, Any], **fields: Any) -> None:
    for key, value in fields.items():
        if value is not None:
            obj[key] = value


__all__ = ["FlowBuilder"]
