"""Book composition — the semantic layer above pages (roadmap item 8).

``BookBuilder`` composes front matter and chapters/sections into ONE
validated ``mode: flow`` document, lowering through
:class:`~frameforge.sdk.flow.FlowBuilder`; the flow engine (ADR-0003)
paginates it deterministically. Numbering is computed HERE, at build time
(§A.0: the SDK computes, the document receives literal numbered text — no
renderer counter engine is assumed): chapters ``1``, ``2`` …, sections
``1.1``, ``1.2`` …, figures ``Figure 2.1`` numbered per chapter and folded
into their captions. Every chapter opens on a fresh page; figures keep
their caption on the same page (``keep_with_caption`` → ``break_inside:
avoid``) unless disabled per call.

    from frameforge.sdk import BookBuilder
    book = BookBuilder(title="Field Notes", author="A. Author")
    ch = book.chapter("Origins")
    ch.para("Prose flows and paginates…")
    sec = ch.section("Early days")
    sec.figure(plate_object, caption="The first plate")   # -> Figure 1.1
    doc = book.build()                                    # validated flow doc

Chapters and sections share one recording surface: ``section()`` emits the
numbered level-2 heading and returns the same builder, so prose keeps
appending to the chapter's story in order.
"""
from __future__ import annotations

from typing import Any

from frameforge.sdk.flow import FlowBuilder
from frameforge.sdk.humanize import apply_humanize
from frameforge.sdk.model import HEAD_VERSION, validate_document

__all__ = ["BookBuilder", "ChapterBuilder"]


class ChapterBuilder:
    """One chapter's story: a numbered heading, then any flowables.

    Every :class:`FlowBuilder` verb (``para``/``bullet``/``numbered``/
    ``code``/``math``/``table``/``image``/``spacer`` …) is available and
    appends in call order. :meth:`section` numbers a level-2 heading;
    :meth:`figure` numbers per chapter and folds the label into the
    caption.
    """

    def __init__(self, number: int, title: str, *, id: str | None = None):
        self.number = number
        self._sections = 0
        self._figures = 0
        self._flow = FlowBuilder()
        self._flow.heading(1, f"{number} · {title}",
                           id=id or f"ch-{number}",
                           break_before="page")

    def section(self, title: str, *, id: str | None = None) -> "ChapterBuilder":
        """A numbered section heading (``N.M · title``); returns the same
        builder — subsequent calls keep appending to this chapter."""
        self._sections += 1
        self._flow.heading(2, f"{self.number}.{self._sections} · {title}",
                           id=id or f"ch-{self.number}-s{self._sections}")
        return self

    def figure(self, object: dict[str, Any], *, caption: Any = None,
               keep_with_caption: bool = True, **fields: Any) -> "ChapterBuilder":
        """A chapter-numbered figure: ``Figure N.K`` prefixes the caption;
        by default the figure and its caption stay on one page. A boxless
        object (a computed path, a line) gets its size derived from the
        geometry — the flow engine must reserve real height, never zero."""
        self._figures += 1
        label = f"Figure {self.number}.{self._figures}"
        text = f"{label} — {caption}" if caption else label
        if keep_with_caption:
            fields.setdefault("break_inside", "avoid")
        if "box" not in object and "size" not in fields:
            bounds = _object_bounds(object)
            if bounds:
                fields["size"] = bounds
        self._flow.figure(object, caption=text, **fields)
        return self

    def __getattr__(self, name: str):
        # delegate the full FlowBuilder verb surface (para, bullet, code, …)
        verb = getattr(self._flow, name)

        def call(*args: Any, **kwargs: Any) -> "ChapterBuilder":
            verb(*args, **kwargs)
            return self

        return call

    def story(self) -> list[dict[str, Any]]:
        return self._flow.story()


class BookBuilder:
    """Front matter + chapters, lowered to one paginated flow document."""

    def __init__(self, *, title: str, author: str | None = None,
                 lang: str | None = None, master: str | None = None,
                 toc: bool = True):
        self.title = title
        self.author = author
        self.lang = lang
        self.master = master
        self._toc = toc
        self._chapters: list[ChapterBuilder] = []

    def chapter(self, title: str, *, id: str | None = None) -> ChapterBuilder:
        ch = ChapterBuilder(len(self._chapters) + 1, title, id=id)
        self._chapters.append(ch)
        return ch

    def build(self, *, validate: bool = True) -> dict[str, Any]:
        """The whole book as one validated ``mode: flow`` document."""
        front = FlowBuilder()
        # the title is front-matter DISPLAY, not a chapter: a styled block,
        # so the book never lists itself in its own contents
        front.para(self.title, style={"font_size": 34, "font_weight": 700,
                                      "line_height": 1.15})
        if self.author:
            front.para(self.author, style={"font_size": 14,
                                           "color": "#555555"})
        if self._toc:
            front.toc(levels=[1, 2], title="Contents", leader=".")
        story = front.story()
        for ch in self._chapters:
            story.extend(ch.story())

        section: dict[str, Any] = {"mode": "flow", "id": "book",
                                   "media": "paged",
                                   "master": self.master or "book",
                                   "story": story}
        doc: dict[str, Any] = {"dsl": "FrameForge", "version": HEAD_VERSION,
                               "title": self.title, "profile": "book",
                               "pages": [section]}
        if not self.master:
            # default book master: A5 portrait; margins resolve through the
            # flow engine's canon (explicit region -> margin -> Johnston)
            doc["defs"] = {"masters": {"book": {
                "canvas": {"preset": "A5", "orientation": "portrait"}}}}
        if self.lang:
            doc["lang"] = self.lang
        if self.author:
            doc["meta"] = {"author": self.author}
        doc = apply_humanize(doc)      # seeded hand on figures; identity if off
        if validate:
            validate_document(doc)
        return doc

def _object_bounds(obj: dict[str, Any]) -> list[float] | None:
    """[w, h] extent of a boxless object's geometry, when derivable."""
    pts: list[tuple[float, float]] = []
    for child in obj.get("children") or []:        # groups: recurse
        if isinstance(child, dict):
            b = child.get("box")
            if isinstance(b, (list, tuple)) and len(b) >= 4:
                pts.extend([(float(b[0]), float(b[1])),
                            (float(b[0]) + float(b[2]),
                             float(b[1]) + float(b[3]))])
                continue
            sub = _object_bounds(child)
            if sub:
                pts.append((sub[0], sub[1]))
    d = obj.get("d")
    if isinstance(d, (list, tuple)):
        for seg in d:
            if isinstance(seg, (list, tuple)) and len(seg) >= 3:
                coords = seg[1:]
                pts.extend((float(coords[i]), float(coords[i + 1]))
                           for i in range(0, len(coords) - 1, 2))
    for key in ("points",):
        for p in obj.get(key) or []:
            pts.append((float(p[0]), float(p[1])))
    for key in ("from", "to"):
        p = obj.get(key)
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            pts.append((float(p[0]), float(p[1])))
    if obj.get("center") is not None and obj.get("rx") is not None:
        cx, cy = obj["center"]
        rx, ry = obj["rx"], obj.get("ry", obj["rx"])
        pts.extend([(cx - rx, cy - ry), (cx + rx, cy + ry)])
    if not pts:
        return None
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return [max(xs), max(ys)]
