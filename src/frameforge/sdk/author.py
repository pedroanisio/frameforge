"""Authoring builders for the Python SDK."""
from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path as FsPath
from typing import Any, Iterator

from frameforge.sdk.clip import normalize_clip
from frameforge.sdk.expand import ExpandOptions, expand
from frameforge.sdk.geometry import Mat3, Path as _GeomPath, Vec2
from frameforge.sdk.layout import Box
from frameforge.sdk.model import HEAD_VERSION, validate_document


@dataclass(frozen=True)
class Handle:
    """Nominal reference returned by definition helpers."""

    kind: str
    name: str

    def __str__(self) -> str:
        return self.name


class DocumentBuilder:
    """Small fluent builder that lowers directly to the authoritative model."""

    def __init__(
        self,
        *,
        title: str | None = None,
        profile: str | None = None,
        lang: str | None = None,
        version: str = HEAD_VERSION,
    ) -> None:
        self._doc: dict[str, Any] = {"dsl": "FrameForge", "version": version, "pages": []}
        if title is not None:
            self._doc["title"] = title
        if profile is not None:
            self._doc["profile"] = profile
        if lang is not None:
            self._doc["lang"] = lang

    def define_color(self, name: str, value: str) -> Handle:
        self._tokens("colors")[name] = value
        return Handle("color", name)

    def define_font(self, name: str, *, family: str, src: str | None = None, hash: str | None = None, **fields: Any) -> Handle:
        font: dict[str, Any] = {"family": family}
        if src is not None:
            font["src"] = src
        if hash is not None:
            font["hash"] = hash
        font.update(fields)
        self._tokens("fonts")[name] = font
        return Handle("font", name)

    def define_style(self, name: str, **style: Any) -> Handle:
        self._tokens("styles")[name] = _coerce_handles(style)
        return Handle("style", name)

    def define_text_style(self, name: str, **style: Any) -> Handle:
        self._tokens("text_styles")[name] = _coerce_handles(style)
        return Handle("text_style", name)

    def define_stroke_style(self, name: str, **style: Any) -> Handle:
        self._tokens("stroke_styles")[name] = _coerce_handles(style)
        return Handle("stroke_style", name)

    def define_asset(self, name: str, src: str, *, kind: str | None = None, hash: str | None = None, **fields: Any) -> Handle:
        asset: dict[str, Any] = {"src": src}
        if kind is not None:
            asset["kind"] = kind
        if hash is not None:
            asset["hash"] = hash
        asset.update(fields)
        self._defs("assets")[name] = asset
        return Handle("asset", name)

    def define_master(self, name: str, master: dict[str, Any]) -> Handle:
        self._defs("masters")[name] = _coerce_handles(master)
        return Handle("master", name)

    def master(self, name: str, canvas: str | dict[str, Any], **fields: Any) -> "MasterBuilder":
        """Define a page master and return its fluent :class:`MasterBuilder`.

        ``canvas`` is a preset name or a canvas object; regions, running
        header/footer content and the footnote area are added with builder
        calls. The returned builder is accepted directly by
        :meth:`page`/:meth:`flow`/:meth:`section` ``master=`` arguments.
        """
        master: dict[str, Any] = {"canvas": _coerce_handles(canvas)}
        master.update(_coerce_handles(fields))
        self._defs("masters")[name] = master
        return MasterBuilder(name, master)

    def define_counter(self, name: str, *, start: int | None = None,
                       reset_with: str | None = None, format: str | None = None) -> Handle:
        """Define a named counter (``defs.counters``) for numbering series."""
        counter: dict[str, Any] = {}
        if start is not None:
            counter["start"] = int(start)
        if reset_with is not None:
            counter["reset_with"] = str(reset_with)
        if format is not None:
            counter["format"] = format
        self._defs("counters")[name] = counter
        return Handle("counter", name)

    def define_target(
        self,
        name: str,
        canvas: str | dict[str, Any],
        *,
        adjustments: dict[str, Any] | None = None,
        font_scale: float | None = None,
        hide: list[str] | None = None,
        padding_delta: float | None = None,
    ) -> Handle:
        """Add a render target (multi-canvas output) with optional adjustments.

        ``font_scale``/``hide``/``padding_delta`` are sugar for the
        ``adjustments`` object; pass ``adjustments=`` directly for forward
        compatibility. Requested targets are checked by
        :func:`~frameforge.sdk.validate.validate_static_rules`.
        """
        adj: dict[str, Any] = dict(adjustments) if adjustments else {}
        if font_scale is not None:
            adj["font_scale"] = float(font_scale)
        if hide is not None:
            adj["hide"] = [str(object_id) for object_id in hide]
        if padding_delta is not None:
            adj["padding_delta"] = float(padding_delta)
        target: dict[str, Any] = {"name": name, "canvas": _coerce_handles(canvas)}
        if adj:
            target["adjustments"] = adj
        self._doc.setdefault("targets", []).append(target)
        return Handle("target", name)

    def describe(self, description: str) -> "DocumentBuilder":
        """Set the document's ``description`` (semantic summary for readers/agents)."""
        self._doc["description"] = str(description)
        return self

    def meta(self, **entries: Any) -> "DocumentBuilder":
        """Merge entries into the document-level ``meta`` mapping."""
        self._doc.setdefault("meta", {}).update(_coerce_handles(entries))
        return self

    def text_contract(self, **fields: Any) -> "DocumentBuilder":
        """Set the document-level text contract (``min_font_size``, ``overflow``,
        ``line_clamp``, ``text_overflow``)."""
        self._doc["text_contract"] = _coerce_handles(fields)
        return self

    def humanize(self, **fields: Any) -> "DocumentBuilder":
        """Set the document-level humanize 'hand' — a seeded, bounded imperfection
        applied to every object at :func:`~frameforge.sdk.expand.expand` time so a
        mechanically-perfect layout reads as hand-placed. Fields (all optional):
        ``seed``, ``roughen`` (geometry wobble), ``drift_deg`` (tilt), ``weight``
        (stroke), ``opacity`` (ink), ``grain`` (tension), ``enabled``. Deterministic:
        same doc + seed → identical output. Any object may override with its own
        ``humanize=`` field. See the ``Humanize`` model."""
        self._doc["humanize"] = _coerce_handles(fields)
        return self

    def define_symbol(self, name: str, *, box: list[Any], objects: list[dict[str, Any]], **fields: Any) -> Handle:
        symbol = {"box": box, "objects": _coerce_handles(objects)}
        symbol.update(_coerce_handles(fields))
        self._defs("symbols")[name] = symbol
        return Handle("symbol", name)

    @contextmanager
    def symbol(self, name: str, box: list[Any], **fields: Any) -> "Iterator[PageBuilder]":
        """Author a reusable symbol with normal ``PageBuilder`` calls.

        The yielded builder records objects in the symbol's local coordinates; on
        block exit they are installed under ``defs.symbols[name]``. Instances can
        then be placed with :meth:`PageBuilder.use` or :meth:`PageBuilder.use_at`.
        """
        sub = PageBuilder({"layers": []}).layer("_symbol")
        yield sub
        objects = sub._current_layer.get("objects", []) if sub._current_layer else []
        self.define_symbol(name, box=_coerce_handles(box), objects=objects, **fields)

    def define_component(self, name: str, spec: dict[str, Any]) -> Handle:
        self._defs("components")[name] = _coerce_handles(spec)
        return Handle("component", name)

    def page(
        self,
        id: str,
        *,
        canvas: str | dict[str, Any] | None = None,
        master: Handle | str | None = None,
        reading_order: list[str] | None = None,
        coordinate_mode: str | None = None,
        **fields: Any,
    ) -> "PageBuilder":
        """Append a page and return its builder.

        ``coordinate_mode`` ("absolute" or "flow") sets the page's
        ``rendering.coordinate_mode``; absolute is the natural choice for decks
        that place objects at explicit page coordinates. Extra ``fields``
        (``links``, ``notes``, ``meta``, ``semantic``, …) pass through to the
        page model. Everything is validated against the model at :meth:`build`
        time, not here.
        """
        page: dict[str, Any] = {"mode": "page", "id": id, "layers": []}
        if canvas is not None:
            page["canvas"] = _coerce_handles(canvas)
        if master is not None:
            page["master"] = _handle_name(master, {"master"}, "master")
        if reading_order is not None:
            page["reading_order"] = reading_order
        if coordinate_mode is not None:
            page["rendering"] = {"coordinate_mode": coordinate_mode}
        page.update(_coerce_handles(fields))
        self._doc["pages"].append(page)
        builder = PageBuilder(page)
        builder._document = self._doc
        return builder

    def flow(self, id: str, *, master: Handle | str, story: list[dict[str, Any]], **fields: Any) -> None:
        section: dict[str, Any] = {
            "mode": "flow",
            "id": id,
            "master": _handle_name(master, {"master"}, "master"),
            "story": _coerce_handles(story),
        }
        section.update(_coerce_handles(fields))
        self._doc["pages"].append(section)

    @contextmanager
    def section(self, id: str, *, master: Handle | str, **fields: Any):
        """Author a ``mode: flow`` section's story with typed builder calls.

        The context-manager entry symmetric to :meth:`page`: yields a
        :class:`~frameforge.sdk.flow.FlowBuilder`, and on block exit lowers its
        story through :meth:`flow`. Extra ``fields`` (``media``, ``lang``,
        ``links``, ``meta``, …) pass through to the flow section::

            with builder.section("chapter-1", master=body) as flow:
                flow.heading(1, "Chapter One")
                flow.para("Prose with **bold** inline forms.")
        """
        from frameforge.sdk.flow import FlowBuilder

        story = FlowBuilder()
        yield story
        self.flow(id, master=master, story=story.story(), **fields)

    def build_dict(self, *, expand_reuse: bool = True) -> dict[str, Any]:
        if expand_reuse:
            return expand(self._doc, opts=ExpandOptions(pin_assets=False)).document.model_dump(
                by_alias=True,
                exclude_none=True,
            )
        validate_document(self._doc)
        return _coerce_handles(self._doc)

    def build(self, *, expand_reuse: bool = True):
        if expand_reuse:
            return expand(self._doc, opts=ExpandOptions(pin_assets=False)).document
        return validate_document(self._doc)

    def write(
        self,
        path: str | FsPath,
        *,
        format: str = "yaml",
        validate: bool = True,
        fail_on_error: bool = False,
        expand_reuse: bool = True,
    ):
        """Build, optionally run static rules, and serialize the document to ``path``.

        Returns the validation report when ``validate`` is true; otherwise returns
        ``None``. Structural model validation always runs via :meth:`build`.
        With ``fail_on_error=True`` a failing report raises
        :class:`~frameforge.sdk.validate.StaticValidationError`, whose message
        lists *every* error with its JSON-pointer path and whose ``report``
        attribute carries the full :class:`ValidationReport` — so callers fix
        all issues in one round-trip instead of one per raise.
        """
        from frameforge.sdk.io import serialize
        from frameforge.sdk.validate import StaticValidationError, validate_static_rules

        doc = self.build(expand_reuse=expand_reuse)
        report = validate_static_rules(doc) if validate else None
        if report is not None and fail_on_error and not report.ok:
            raise StaticValidationError(report)
        out = FsPath(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(serialize(doc, format=format), encoding="utf-8")
        return report

    def _defs(self, key: str) -> dict[str, Any]:
        defs = self._doc.setdefault("defs", {})
        return defs.setdefault(key, {})

    def _tokens(self, key: str) -> dict[str, Any]:
        defs = self._doc.setdefault("defs", {})
        tokens = defs.setdefault("tokens", {})
        return tokens.setdefault(key, {})


class MasterBuilder:
    """Fluent builder for one ``defs.masters`` entry (a ``PageMaster``).

    Returned by :meth:`DocumentBuilder.master`; every call mutates the
    installed master in place and returns the builder for chaining. Pass the
    builder itself (or its :attr:`handle`) wherever a ``master=`` argument is
    accepted.
    """

    def __init__(self, name: str, master: dict[str, Any]) -> None:
        self._name = name
        self._master = master
        self.handle = Handle("master", name)

    def __str__(self) -> str:
        return self._name

    def margin(self, margin: list[Any]) -> "MasterBuilder":
        """Set the master's content margin (``[top, right, bottom, left]``)."""
        self._master["margin"] = _coerce_handles(margin)
        return self

    def fixed(self, objects: list[dict[str, Any]]) -> "MasterBuilder":
        """Append fixed chrome objects drawn on every page using this master."""
        self._master.setdefault("fixed", []).extend(
            _coerce_handles(obj) for obj in objects
        )
        return self

    def region(
        self,
        id: str,
        box: list[Any],
        *,
        columns: int | None = None,
        column_gap: Any = None,
        column_fill: str | None = None,
        next: str | None = None,
        **fields: Any,
    ) -> "MasterBuilder":
        """Append a flow region. ``next`` chains overflow into another region
        (cycles are rejected by :func:`validate_static_rules`)."""
        region: dict[str, Any] = {"id": str(id), "box": _coerce_handles(box)}
        if columns is not None:
            region["columns"] = int(columns)
        if column_gap is not None:
            region["column_gap"] = column_gap
        if column_fill is not None:
            region["column_fill"] = column_fill
        if next is not None:
            region["next"] = str(next)
        region.update(_coerce_handles(fields))
        self._master.setdefault("regions", []).append(region)
        return self

    def running_header(self, objects: list[dict[str, Any]]) -> "MasterBuilder":
        """Set the running header content (a list of visual objects)."""
        self._running()["header"] = [_coerce_handles(obj) for obj in objects]
        return self

    def running_footer(self, objects: list[dict[str, Any]]) -> "MasterBuilder":
        """Set the running footer content (a list of visual objects)."""
        self._running()["footer"] = [_coerce_handles(obj) for obj in objects]
        return self

    def page_number(self, value: Any = True) -> "MasterBuilder":
        """Enable the running page number (``True`` or a style dict)."""
        self._running()["page_number"] = _coerce_handles(value)
        return self

    def footnote_area(self, id: str, box: list[Any], **fields: Any) -> "MasterBuilder":
        """Set the footnote region (where ``footnote`` inlines are placed)."""
        area: dict[str, Any] = {"id": str(id), "box": _coerce_handles(box)}
        area.update(_coerce_handles(fields))
        self._master["footnote_area"] = area
        return self

    def _running(self) -> dict[str, Any]:
        return self._master.setdefault("running", {})


class StackBuilder:
    """Collect local children for a layout-native group."""

    def __init__(self, parent: "PageBuilder", box: list[Any], layout: dict[str, Any], fields: dict[str, Any]) -> None:
        self._parent = parent
        self._box = box
        self._layout = layout
        self._fields = fields
        self._children: list[dict[str, Any]] = []

    def add(self, obj: dict[str, Any]) -> "StackBuilder":
        self._children.append(_local_child(_coerce_handles(obj)))
        return self

    def extend(self, objects: list[dict[str, Any]]) -> "StackBuilder":
        for obj in objects:
            self.add(obj)
        return self

    def spacer(
        self,
        *,
        w: float = 0.0,
        h: float = 0.0,
        grow: float = 1.0,
        axis: str = "width",
    ) -> "StackBuilder":
        """Add an invisible fill/grow spacer."""
        sizing = {"grow": grow, axis: "fill"}
        return self.add({
            "type": "group",
            "box": [0, 0, w, h],
            "sizing": sizing,
            "decorative": True,
            "children": [],
        })

    def widget(self, obj: dict[str, Any]) -> "StackBuilder":
        return self.add(obj)

    def button(self, label: str, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import button

        return self.add(button(label, **fields))

    def badge(self, text: str, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import badge

        return self.add(badge(text, **fields))

    def pill(self, text: str | None = None, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import pill

        return self.add(pill(text, **fields))

    def avatar(self, initials: str | None = None, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import avatar

        return self.add(avatar(initials, **fields))

    def kpi(self, label: str, value: str, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import kpi

        return self.add(kpi(label, value, **fields))

    def field(self, label: str, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import field

        return self.add(field(label, **fields))

    def toggle(self, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import toggle

        return self.add(toggle(**fields))

    def tabs(self, items: list[str], **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import tabs

        return self.add(tabs(items, **fields))

    def progress(self, frac: float, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import progress

        return self.add(progress(frac, **fields))

    def divider(self, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import divider

        return self.add(divider(**fields))

    def checkbox(self, *, checked: bool = True, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import checkbox

        return self.add(checkbox(checked=checked, **fields))

    def radio(self, *, selected: bool = True, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import radio

        return self.add(radio(selected=selected, **fields))

    def slider(self, frac: float, **fields: Any) -> "StackBuilder":
        from frameforge.sdk.widgets import slider

        return self.add(slider(frac, **fields))

    def commit(self) -> PageBuilder:
        self._parent.group(self._children, box=self._box, layout=self._layout, **self._fields)
        return self._parent


class PageBuilder:
    """Builder for a single page's layers and visual objects."""

    def __init__(self, page: dict[str, Any]) -> None:
        self._page = page
        self._document: dict[str, Any] | None = None
        self._current_layer: dict[str, Any] | None = None
        self._decorative_depth = 0
        self._lettering_depth = 0

    def layer(self, id: str, **fields: Any) -> "PageBuilder":
        layer = {"id": id, "objects": []}
        layer.update(_coerce_handles(fields))
        self._page.setdefault("layers", []).append(layer)
        self._current_layer = layer
        return self

    def add(self, obj: dict[str, Any]) -> "PageBuilder":
        self._objects().append(_coerce_handles(self._stamp(obj)))
        return self

    def extend(self, objects: list[dict[str, Any]]) -> "PageBuilder":
        """Add many objects at once (e.g. the output of a Chart or a layout)."""
        objs = self._objects()
        objs.extend(_coerce_handles(self._stamp(obj)) for obj in objects)
        return self

    @contextmanager
    def stack(
        self,
        box: list[Any],
        *,
        kind: str,
        gap: float | int | str | None = None,
        pad: Any = None,
        align: str | None = None,
        justify: str | None = None,
        columns: int | None = None,
        row_gap: float | int | str | None = None,
        column_gap: float | int | str | None = None,
        **fields: Any,
    ) -> "Iterator[StackBuilder]":
        """Collect children into a layout-native group."""
        layout = _layout(kind, gap=gap, pad=pad, align=align, justify=justify,
                         columns=columns, row_gap=row_gap, column_gap=column_gap)
        stack = StackBuilder(self, box, layout, fields)
        yield stack
        stack.commit()

    def hstack(self, box: list[Any], *, gap: float | int | str | None = None,
               pad: Any = None, align: str | None = None,
               justify: str | None = None, **fields: Any):
        """Context manager for a row layout group."""
        return self.stack(box, kind="row", gap=gap, pad=pad, align=align,
                          justify=justify, **fields)

    def vstack(self, box: list[Any], *, gap: float | int | str | None = None,
               pad: Any = None, align: str | None = None,
               justify: str | None = None, **fields: Any):
        """Context manager for a column layout group."""
        return self.stack(box, kind="column", gap=gap, pad=pad, align=align,
                          justify=justify, **fields)

    def wrap(self, box: list[Any], *, gap: float | int | str | None = None,
             pad: Any = None, align: str | None = None,
             justify: str | None = None, row_gap: float | int | str | None = None,
             column_gap: float | int | str | None = None, **fields: Any):
        """Context manager for a wrapping row layout group."""
        return self.stack(box, kind="wrap", gap=gap, pad=pad, align=align,
                          justify=justify, row_gap=row_gap, column_gap=column_gap,
                          **fields)

    def grid_stack(self, box: list[Any], *, columns: int, gap: float | int | str | None = None,
                   pad: Any = None, align: str | None = None,
                   row_gap: float | int | str | None = None,
                   column_gap: float | int | str | None = None, **fields: Any):
        """Context manager for a grid layout group."""
        return self.stack(box, kind="grid", gap=gap, pad=pad, align=align,
                          columns=columns, row_gap=row_gap, column_gap=column_gap,
                          **fields)

    @contextmanager
    def bleed(self) -> "Iterator[PageBuilder]":
        """Mark every object added in this block ``decorative``.

        The static rules exempt ``decorative`` objects from both the containment
        SHOULD (an object may extend past the canvas) and the free-group overlap
        rule — so a full-bleed flourish, an SFX stamp or a speed-line burst stops
        needing a hand-written flag on every call::

            with layer.bleed():
                speed_lines(layer, cx, cy)   # all decorative; none flagged

        Already-set ``decorative`` values are left untouched. Blocks nest.
        """
        self._decorative_depth += 1
        try:
            yield self
        finally:
            self._decorative_depth -= 1

    @contextmanager
    def lettering(self) -> "Iterator[PageBuilder]":
        """Tag text added in this block as lettering (``meta.role = "lettering"``).

        The tabular-box-model heuristic flags ≥6 absolutely-placed text objects in
        a regular grid — true of any captioned/balloon-lettered page. Tagging the
        text as lettering declares the intent the heuristic is meant to catch the
        *absence* of, so freeform dialogue and captions validate without being
        rewritten as a grid group or TableObject::

            with layer.lettering():
                for cap, box in zip(captions, boxes):
                    layer.text(box, cap, style="caption")

        Only ``text`` objects are tagged; an existing ``meta`` is preserved.
        """
        self._lettering_depth += 1
        try:
            yield self
        finally:
            self._lettering_depth -= 1

    def _stamp(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Apply any active ``bleed()`` / ``lettering()`` intent to ``obj``."""
        if not isinstance(obj, dict):
            return obj
        if self._decorative_depth and "decorative" not in obj:
            obj = {**obj, "decorative": True}
        if self._lettering_depth and obj.get("type") == "text":
            meta = obj.get("meta")
            meta = dict(meta) if isinstance(meta, dict) else {}
            meta.setdefault("role", "lettering")
            obj = {**obj, "meta": meta}
        return obj

    def rect(self, box: list[Any], **fields: Any) -> "PageBuilder":
        return self.add({"type": "rect", "box": box, **fields})

    def text(self, box: list[Any], text: str | list[Any], **fields: Any) -> "PageBuilder":
        """Add a text object. ``text`` is a plain string, or a list of inlines
        (strings, :func:`~frameforge.sdk.macros.span` dicts, refs …) lowered to
        the model's ``spans`` form for per-span styling."""
        if isinstance(text, (list, tuple)):
            return self.add({"type": "text", "box": box, "spans": list(text), **fields})
        return self.add({"type": "text", "box": box, "text": text, **fields})

    def image(self, box: list[Any], src: Handle | str, **fields: Any) -> "PageBuilder":
        return self.add({"type": "image", "box": box, "src": _handle_name(src, {"asset"}, "src"), **fields})

    def line(self, start: list[float], end: list[float], **fields: Any) -> "PageBuilder":
        return self.add({"type": "line", "from": start, "to": end, **fields})

    def icon(self, box: list[Any], glyph: str, *, color: Any = None,
             font: str | None = None, size: float | None = None,
             **fields: Any) -> "PageBuilder":
        """Add an icon glyph (a single character/ligature drawn in ``box``)."""
        obj: dict[str, Any] = {"type": "icon", "box": box, "glyph": str(glyph)}
        if color is not None:
            obj["color"] = str(color)
        if font is not None:
            obj["font"] = font
        if size is not None:
            obj["size"] = float(size)
        obj.update(fields)
        return self.add(obj)

    def bullet_list(self, box: list[Any], items: list[Any], *,
                    marker: str | None = None, marker_color: Any = None,
                    gap: float | None = None, indent: float | None = None,
                    **fields: Any) -> "PageBuilder":
        """Add a positioned bullet list (the absolute-layout list primitive;
        for flow stories use :meth:`FlowBuilder.bullet`). ``items`` are strings
        or span dicts."""
        obj: dict[str, Any] = {"type": "bullet_list", "box": box, "items": list(items)}
        if marker is not None:
            obj["marker"] = marker
        if marker_color is not None:
            obj["marker_color"] = str(marker_color)
        if gap is not None:
            obj["gap"] = float(gap)
        if indent is not None:
            obj["indent"] = float(indent)
        obj.update(fields)
        return self.add(obj)

    def dimension(self, start: Any, end: Any, *, kind: str = "linear",
                  value: Any = None, text: str | None = None,
                  prefix: str | None = None, suffix: str | None = None,
                  offset: Any = None, arrows: str | None = None,
                  text_style: str | None = None, **fields: Any) -> "PageBuilder":
        """Add an anchored dimension annotation (measurement callout).

        ``start``/``end`` accept every model ``Anchor`` form: an object ``id``
        string, a point (``Vec2`` or ``[x, y]``), or ``{"ref": id, "port": name}``
        targeting a declared port. ``kind`` is ``linear``/``aligned``/
        ``angular``/``radial``/``diameter``; ``value="auto"`` lets the renderer
        measure, ``text`` overrides the label entirely.
        """
        obj: dict[str, Any] = {"type": "dimension", "kind": kind,
                               "from": _anchor(start), "to": _anchor(end)}
        if value is not None:
            obj["value"] = value
        if text is not None:
            obj["text"] = text
        if prefix is not None:
            obj["prefix"] = prefix
        if suffix is not None:
            obj["suffix"] = suffix
        if offset is not None:
            obj["offset"] = offset
        if arrows is not None:
            obj["arrows"] = arrows
        if text_style is not None:
            obj["text_style"] = text_style
        obj.update(fields)
        return self.add(obj)

    def connector(self, start: Any, end: Any, *,
                  route: Any = None, route_kind: str | None = None,
                  label: str | None = None, label_box: list[Any] | None = None,
                  label_style: Any = None,
                  arrow_start: Any = None, arrow_end: Any = None,
                  **fields: Any) -> "PageBuilder":
        """Add an anchored connector between two endpoints (typed at HEAD, §3.11).

        ``start``/``end`` accept every model ``ConnectorAnchor`` form: an object
        ``id`` string or :class:`Handle` (lowered to ``{"ref": id}`` — the target's
        box centre), a point (``Vec2`` or ``[x, y]`` — fixed page coordinates), or
        an endpoint dict such as ``{"ref": id, "port": name}`` /
        ``{"ref": id, "side": "east", "offset": 10}`` / ``{"point": [x, y]}``
        passed through as-is.

        ``route`` is an optional list of intermediate waypoints (page space, in
        order); ``route_kind`` the advisory hint (``straight`` / ``orthogonal`` /
        ``curved`` — the drawn geometry is always the point chain). ``label`` +
        ``label_box`` draw a boxed text label (``label_style`` a tokens key or an
        inline style). ``arrow_start``/``arrow_end`` markers merge into the inline
        ``stroke_style`` bundle — paint itself goes in ``stroke`` (e.g. via
        ``**stroke(...)``), matching the model's paint/geometry split.
        """
        obj: dict[str, Any] = {"type": "connector",
                               "from": _connector_endpoint(start),
                               "to": _connector_endpoint(end)}
        if route is not None or route_kind is not None:
            route_spec: dict[str, Any] = {}
            if route_kind is not None:
                route_spec["kind"] = str(route_kind)
            if route is not None:
                route_spec["points"] = _points(route)
            obj["route"] = route_spec
        if label is not None:
            if label_box is None:
                raise ValueError("connector(label=...) needs label_box=[x, y, w, h]")
            label_spec: dict[str, Any] = {"text": str(label), "box": list(label_box)}
            if label_style is not None:
                label_spec["style"] = (
                    _handle_name(label_style, {"style", "text_style"}, "label_style")
                    if isinstance(label_style, (str, Handle)) else label_style
                )
            obj["label"] = label_spec
        markers = {key: value for key, value in
                   (("arrow_start", arrow_start), ("arrow_end", arrow_end))
                   if value is not None}
        if markers:
            bundle = fields.get("stroke_style")
            if bundle is None:
                fields = {**fields, "stroke_style": markers}
            elif isinstance(bundle, dict):
                fields = {**fields, "stroke_style": {**bundle, **markers}}
            else:
                raise TypeError(
                    "connector(arrow_start/arrow_end=...) needs an inline stroke_style "
                    "dict; a stroke_style token cannot be extended in place — put the "
                    "arrow_* flags in the token instead"
                )
        obj.update(fields)
        return self.add(obj)

    def link(self, to: str, *, relation: str | None = None,
             label: str | None = None, external: bool | None = None) -> "PageBuilder":
        """Add a page-level navigation link (``page.links``) to another page id."""
        link: dict[str, Any] = {"to": str(to)}
        if relation is not None:
            link["relation"] = relation
        if label is not None:
            link["label"] = label
        if external is not None:
            link["external"] = external
        self._page.setdefault("links", []).append(link)
        return self

    def chart(
        self,
        box: Any,
        *,
        domain: tuple[float, float, float, float],
        x_scale: Any = "linear",
        y_scale: Any = "linear",
    ):
        """Return a :class:`~frameforge.sdk.Chart` mapped to ``box``.

        Finish with ``.add_to(page)`` or pass ``chart.objects()`` to
        :meth:`extend`.
        """
        from frameforge.sdk.chart import Chart
        from frameforge.sdk.draw import Frame

        return Chart(Frame(domain=domain, box=tuple(float(v) for v in box), x_scale=x_scale, y_scale=y_scale))

    def widget(self, obj: dict[str, Any]) -> "PageBuilder":
        """Add a prebuilt SDK widget object and return the page builder."""
        return self.add(obj)

    def badge(self, box: Any, text: str | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import badge

        return self.add(badge(box, text, **fields))

    def pill(self, box: Any, text: str | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import pill

        return self.add(pill(box, text, **fields))

    def button(self, box: Any, label: str | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import button

        return self.add(button(box, label, **fields))

    def avatar(self, box: Any, name: str | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import avatar

        return self.add(avatar(box, name, **fields))

    def kpi(self, box: Any, label: str, value: str | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import kpi

        return self.add(kpi(box, label, value, **fields))

    def field(self, box: Any, label: str | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import field

        return self.add(field(box, label, **fields))

    def toggle(self, box: Any = None, *, on: bool = False, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import toggle

        return self.add(toggle(box, on=on, **fields))

    def tabs(self, box: Any, items: list[str] | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import tabs

        return self.add(tabs(box, items, **fields))

    def progress(self, box: Any, value: float | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import progress

        return self.add(progress(box, value, **fields))

    def divider(self, box: Any = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import divider

        return self.add(divider(box, **fields))

    def checkbox(self, box: Any = None, *, checked: bool = True, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import checkbox

        return self.add(checkbox(box, checked=checked, **fields))

    def radio(self, box: Any = None, *, selected: bool = True, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import radio

        return self.add(radio(box, selected=selected, **fields))

    def slider(self, box: Any, frac: float | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import slider

        return self.add(slider(box, frac, **fields))

    def breadcrumb(self, box: Any, items: list[str] | None = None, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import breadcrumb

        return self.add(breadcrumb(box, items, **fields))

    def navbar(self, box: Any, items: list[str], **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import navbar

        return self.add(navbar(box, items, **fields))

    def dropdown(self, box: Any, items: list[str], **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import dropdown

        return self.add(dropdown(box, items, **fields))

    def image_placeholder(self, box: Any, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import image_placeholder

        return self.add(image_placeholder(box, **fields))

    def sticky_note(self, box: Any, text: str, **fields: Any) -> "PageBuilder":
        from frameforge.sdk.widgets import sticky_note

        return self.add(sticky_note(box, text, **fields))

    def card(self, box: Any, **fields: Any):
        """Add a card widget and return its :class:`~frameforge.sdk.Panel`."""
        from frameforge.sdk.widgets import card

        panel = card(box, **fields)
        self.add(panel.object)
        return panel

    def table(
        self,
        box: Any,
        columns: list[dict[str, Any]],
        rows: list[list[Any]],
        **fields: Any,
    ) -> "PageBuilder":
        from frameforge.sdk.widgets import table

        return self.add(table(box, columns, rows, **fields))

    def ellipse(self, center: Any, rx: float, ry: float, **fields: Any) -> "PageBuilder":
        """Add an ellipse centred at ``center`` (a ``Vec2`` or ``[x, y]``)."""
        return self.add({"type": "ellipse", "center": _point(center),
                         "rx": rx, "ry": ry, **fields})

    def circle(self, center: Any, r: float, **fields: Any) -> "PageBuilder":
        """Add a circle. Lowers to the canonical ``ellipse`` (rx == ry == r), so it
        never emits the deprecated ``circle`` alias."""
        return self.ellipse(center, r, r, **fields)

    def polyline(self, points: Any, *, closed: bool = False, smooth: bool = False,
                 **fields: Any) -> "PageBuilder":
        """Add a polyline through ``points`` (``Vec2`` values or ``[x, y]`` pairs).

        With ``smooth=True`` the points become control points of a Catmull-Rom
        spline lowered to a canonical ``path`` (the same smoothing ``Chart.line``
        uses), so an organic curve no longer has to be hand-built from béziers;
        ``closed`` then joins the final segment back to the start. The default
        (``smooth=False``) emits a straight-segment ``polyline``.
        """
        if smooth:
            geom = _GeomPath().through(_points(points))
            if closed:
                geom.close()
            return self.add(geom.object(**fields))
        obj: dict[str, Any] = {"type": "polyline", "points": _points(points)}
        if closed:
            obj["closed"] = True
        obj.update(fields)
        return self.add(obj)

    def polygon(self, points: Any, **fields: Any) -> "PageBuilder":
        """Add a filled polygon. Lowers to a canonical closed ``polyline``, so it
        never emits the deprecated ``polygon`` alias."""
        return self.polyline(points, closed=True, **fields)

    def path(self, d: Any, **fields: Any) -> "PageBuilder":
        """Add a path. ``d`` may be an SVG path string, a segment list, or a
        :class:`frameforge.sdk.Path` builder (whose geometry is lowered for you)."""
        if isinstance(d, _GeomPath):
            return self.add(d.object(**fields))
        return self.add({"type": "path", "d": d, **fields})

    def curve(
        self,
        start: Any,
        end: Any,
        *,
        control1: Any = None,
        control2: Any = None,
        type: str = "curve",
        **fields: Any,
    ) -> "PageBuilder":
        """Add a single cubic Bézier curve without hand-building a ``Path``.

        The authoritative model accepts the legacy ``curve``/``bezier`` object;
        this method exposes that surface directly for authors that need the
        object form. For new multi-segment geometry, prefer :meth:`path`.
        """
        obj: dict[str, Any] = {"type": type, "from": _point(start), "to": _point(end)}
        if control1 is not None:
            obj["control1"] = _point(control1)
        if control2 is not None:
            obj["control2"] = _point(control2)
        obj.update(fields)
        return self.add(obj)

    def arc(self, center: Any, r: float, start: float, end: float, *,
            ry: float | None = None, **fields: Any) -> "PageBuilder":
        """Add an open circular (or elliptical) arc, lowered to a canonical ``path``.

        Angles are degrees, clockwise-positive in FrameForge's Y-down page space
        with 0° at the +x axis (3 o'clock) — the same convention as
        :meth:`~frameforge.sdk.Mat3.rotate`. ``ry`` makes the arc elliptical
        (default ``ry == r``). Pass ``**stroke(...)`` to paint it; an arc carries no
        ``box``, so it is exempt from the containment rule. Removes the hand-rolled
        ``A``-command path used for rings, gauges and dials.
        """
        cx, cy = _point(center)
        ry = r if ry is None else ry
        sx, sy = _polar(cx, cy, r, ry, start)
        ex, ey = _polar(cx, cy, r, ry, end)
        large = abs(end - start) > 180
        sweep = end >= start
        geom = _GeomPath().move_to(sx, sy).arc_to(r, ry, 0.0, large, sweep, [ex, ey])
        return self.add(geom.object(**fields))

    def sector(self, center: Any, r: float, start: float, end: float, *,
               ry: float | None = None, **fields: Any) -> "PageBuilder":
        """Add a filled pie sector (wedge) from ``start`` to ``end`` degrees.

        Like :meth:`arc` but closed back through ``center``, so it takes a ``fill``.
        Angles follow the :meth:`arc` convention. Lowers to a canonical ``path``.
        """
        cx, cy = _point(center)
        ry = r if ry is None else ry
        sx, sy = _polar(cx, cy, r, ry, start)
        ex, ey = _polar(cx, cy, r, ry, end)
        large = abs(end - start) > 180
        sweep = end >= start
        geom = (_GeomPath().move_to(cx, cy).line_to(sx, sy)
                .arc_to(r, ry, 0.0, large, sweep, [ex, ey]).close())
        return self.add(geom.object(**fields))

    def ring(self, center: Any, r_outer: float, r_inner: float, **fields: Any) -> "PageBuilder":
        """Add a full annulus, lowered to an even-odd ``path``.

        The helper emits two closed subpaths and sets ``style.fill_rule`` to
        ``"evenodd"`` unless the caller already supplied one.
        """
        if r_inner <= 0 or r_outer <= 0 or r_inner >= r_outer:
            raise ValueError("ring needs 0 < r_inner < r_outer")
        cx, cy = _point(center)
        fill_rule = fields.pop("fill_rule", None)
        style = fields.get("style")
        if not (isinstance(style, dict) and style.get("fill_rule")):
            fields = _style_set(fields, "fill_rule", fill_rule or "evenodd", "fill_rule")
        return self.path(
            f"{_ring_subpath(cx, cy, r_outer, True)} {_ring_subpath(cx, cy, r_inner, False)}",
            **fields,
        )

    def regular_polygon(self, center: Any, r: float, sides: int, *,
                        rotation: float = 0.0, **fields: Any) -> "PageBuilder":
        """Add a regular ``sides``-gon of circumradius ``r``, lowered to a closed polyline.

        The first vertex sits at ``rotation`` degrees (0° = +x axis); pass
        ``rotation=-90`` to point a vertex straight up. Replaces the per-fixture
        ``cos``/``sin`` loops used to hand-build hexagons and triangles.
        """
        if sides < 3:
            raise ValueError(f"regular_polygon needs at least 3 sides; got {sides}")
        cx, cy = _point(center)
        pts = [_polar(cx, cy, r, r, rotation + i * 360.0 / sides) for i in range(sides)]
        return self.polygon(pts, **fields)

    def star(self, center: Any, r_outer: float, r_inner: float, points: int, *,
             rotation: float = -90.0, **fields: Any) -> "PageBuilder":
        """Add a ``points``-pointed star, lowered to a closed polyline.

        Vertices alternate between ``r_outer`` and ``r_inner``; the first (outer)
        point sits at ``rotation`` degrees, defaulting to straight up (``-90``).
        """
        if points < 2:
            raise ValueError(f"star needs at least 2 points; got {points}")
        cx, cy = _point(center)
        verts: list[list[float]] = []
        for i in range(points * 2):
            rr = r_outer if i % 2 == 0 else r_inner
            verts.append(_polar(cx, cy, rr, rr, rotation + i * 180.0 / points))
        return self.polygon(verts, **fields)

    def arrow(self, start: Any, end: Any, *, color: str = "#000000", width: float = 2.0,
              head: float = 9.0, head_width: float | None = None, **fields: Any) -> "PageBuilder":
        """Draw a vector from ``start`` to ``end`` with a filled arrowhead at ``end``.

        Emits a ``line`` (shortened to the arrowhead base so the shaft does not
        poke through the tip) plus a closed ``polyline`` head, both in ``color`` —
        so callers stop hand-rolling triangle polygons and mis-placing them.
        ``head`` is the head length in px; extra ``fields`` (e.g. an opacity, or a
        ``stroke_style`` with a dash) are merged onto the shaft line.
        """
        sx, sy = _point(start)
        ex, ey = _point(end)
        dx, dy = ex - sx, ey - sy
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / length, dy / length          # unit vector along the shaft
        px, py = -uy, ux                           # unit perpendicular
        hw = head * 0.6 if head_width is None else head_width
        bx, by = ex - ux * head, ey - uy * head    # arrowhead base, on the shaft
        stroke_style = {"stroke_width": width, **fields.pop("stroke_style", {})}
        self.line([sx, sy], [bx, by], stroke=color, stroke_style=stroke_style, **fields)
        self.polygon([[ex, ey], [bx + px * hw, by + py * hw], [bx - px * hw, by - py * hw]],
                     fill=color)
        return self

    def group(
        self,
        children: list[dict[str, Any]],
        *,
        transform: "Mat3 | list[Any] | None" = None,
        clip: Any = None,
        **fields: Any,
    ) -> "PageBuilder":
        """Add a group of ``children``.

        ``transform`` (a :class:`~frameforge.sdk.Mat3` or a list of transform
        functions) is lowered onto the group's ``style.transform`` so the whole
        group is placed/scaled/rotated as a unit. ``clip`` lowers onto
        ``style.clip_path`` so the group's contents are masked to a region — a box
        ``[x, y, w, h]``, a points list, a :class:`~frameforge.sdk.Path`, a clip
        dict from :mod:`frameforge.sdk.clip`, or a CSS string (see
        :func:`~frameforge.sdk.clip.normalize_clip`). See :meth:`frame` for
        authoring children in a local coordinate system.

        Note: a plain ``group`` defaults to ``free`` layout, which turns on the
        scoped non-overlap rule for its box-bearing children — use :meth:`bleed`
        (or ``decorative=True``) for intentionally overlapping art.
        """
        if transform is not None:
            fields = _transform_fields(transform, fields)
        if clip is not None:
            fields = _style_set(fields, "clip_path", normalize_clip(clip), "clip")
        return self.add({"type": "group", "children": children, **fields})

    def figure(self, source: Any, box: list[Any], **options: Any) -> "PageBuilder":
        """Import a live FrameForge figure page into this page.

        ``source`` may be a :class:`~frameforge.sdk.figure.FigureRef`, callable
        plate function, builder/document/dict, or ``.fg.yaml``/``.fg.json`` path.
        The selected source page is lowered to an ordinary transformed group, so
        its objects remain inspectable and editable after import.
        """
        from frameforge.sdk.figure import merge_figure_defs, place_figure

        placement = place_figure(source, box, **options)
        if self._document is not None:
            merge_figure_defs(self._document, placement.defs)
        return self.add(placement.group)

    def imported_figure(self, figure: Any, box: list[Any], **options: Any) -> "PageBuilder":
        """Place an extracted PDF/EPUB/image figure with provenance metadata.

        Use this for book-import pipelines that already have an image asset plus
        source locator, page/spine selector, source bounding box, caption, and
        confidence. For live FrameForge pages, use :meth:`figure`.
        """
        from frameforge.sdk.figure import place_imported_figure

        return self.add(place_imported_figure(figure, box, **options).group)

    @contextmanager
    def grouped(
        self,
        *,
        transform: "Mat3 | list[Any] | None" = None,
        clip: Any = None,
        **fields: Any,
    ) -> "Iterator[PageBuilder]":
        """Collect objects into one group when the block exits.

        This is the context-manager form of :meth:`group`: author children with
        normal ``PageBuilder`` calls, then lower them as one grouped object.
        """
        sub = PageBuilder({"layers": []}).layer("_group")
        yield sub
        children = sub._current_layer.get("objects", []) if sub._current_layer else []
        self.group(children, transform=transform, clip=clip, **fields)

    @contextmanager
    def local(self, box: list[Any], *, clip: Any = None, **fields: Any) -> "Iterator[PageBuilder]":
        """Collect local-coordinate children into a box-anchored group.

        Use this for panels, motifs and small diagrams that should be authored
        from ``[0, 0]`` without manually adding the panel origin to every child.
        The group carries ``box``; children remain local to that box.
        """
        sub = PageBuilder({"layers": []}).layer("_local")
        yield sub
        children = sub._current_layer.get("objects", []) if sub._current_layer else []
        self.group(children, box=box, clip=clip, **fields)

    def panel(self, box: list[Any], *, clip: Any = None, **fields: Any):
        """Alias for :meth:`local` when the grouped children form a panel."""
        return self.local(box, clip=clip, **fields)

    @contextmanager
    def frame(
        self,
        x: float = 0.0,
        y: float = 0.0,
        *,
        scale: float = 1.0,
        scale_y: float | None = None,
        flip: float = 1.0,
        rotate: float = 0.0,
        clip: Any = None,
    ) -> "Iterator[PageBuilder]":
        """Draw into a transformed group, authoring children at the local origin.

        Yields a detached :class:`PageBuilder` exposing the same primitives; on
        exit their objects are wrapped in a single group whose ``style.transform``
        places them — ``translate(x, y)`` then ``rotate(rotate)`` degrees then
        ``scale(flip * scale, scale_y or scale)``. Use it to stamp a reusable
        figure at a position, size and mirroring without threading coordinate
        math through every call::

            with layer.frame(600, 540, scale=1.5, flip=-1) as f:
                draw_whale(f)   # f.ellipse(...)/f.path(...) in local coordinates

        Frames nest: a frame opened on a yielded builder composes its transform
        with the parent's. An empty frame lowers to an empty (valid) group.
        """
        sy = scale if scale_y is None else scale_y
        matrix = Mat3.translate(x, y) @ Mat3.rotate(rotate) @ Mat3.scale(flip * scale, sy)
        sub = PageBuilder({"layers": []}).layer("_frame")
        yield sub
        children = sub._current_layer.get("objects", []) if sub._current_layer else []
        self.group(children, transform=matrix, clip=clip)

    def use(self, symbol: Handle | str, box: list[Any], **fields: Any) -> "PageBuilder":
        return self.add({"type": "use", "symbol": _handle_name(symbol, {"symbol"}, "symbol"), "box": box, **fields})

    def use_at(
        self,
        symbol: Handle | str,
        x: float,
        y: float,
        w: float,
        h: float,
        **fields: Any,
    ) -> "PageBuilder":
        """Place a symbol instance from scalar coordinates."""
        return self.use(symbol, [x, y, w, h], **fields)

    def component(self, component: Handle | str, box: list[Any], **fields: Any) -> "PageBuilder":
        return self.add(
            {
                "type": "component",
                "component": _handle_name(component, {"component"}, "component"),
                "box": box,
                **fields,
            }
        )

    def _objects(self) -> list[dict[str, Any]]:
        if self._current_layer is None:
            self.layer("main")
        assert self._current_layer is not None
        return self._current_layer.setdefault("objects", [])


def _point(value: Any) -> list[float]:
    """Coerce a ``Vec2`` or ``[x, y]`` sequence to a plain ``[x, y]`` list."""
    if isinstance(value, Vec2):
        return [value.x, value.y]
    return [float(value[0]), float(value[1])]


def _anchor(value: Any) -> Any:
    """Coerce a model ``Anchor``: id string, ``{ref, port}`` dict, or a point."""
    if isinstance(value, Handle):
        return value.name
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return dict(value)
    return _point(value)


def _connector_endpoint(value: Any) -> Any:
    """Coerce a model ``ConnectorAnchor``: unlike a dimension ``Anchor``, a bare id
    lowers to the endpoint form ``{"ref": id}`` (the connector endpoint model has
    no plain-string variant); dicts pass through; anything else is a point."""
    if isinstance(value, Handle):
        return {"ref": value.name}
    if isinstance(value, str):
        return {"ref": value}
    if isinstance(value, dict):
        return dict(value)
    return _point(value)


def _polar(cx: float, cy: float, rx: float, ry: float, degrees: float) -> list[float]:
    """Point on the ``(rx, ry)`` ellipse at ``degrees`` (0° = +x, clockwise in Y-down)."""
    rad = math.radians(degrees)
    return [cx + rx * math.cos(rad), cy + ry * math.sin(rad)]


def _ring_subpath(cx: float, cy: float, r: float, sweep: bool) -> str:
    flag = 1 if sweep else 0
    return (
        f"M {_fmt(cx + r)} {_fmt(cy)} "
        f"A {_fmt(r)} {_fmt(r)} 0 1 {flag} {_fmt(cx - r)} {_fmt(cy)} "
        f"A {_fmt(r)} {_fmt(r)} 0 1 {flag} {_fmt(cx + r)} {_fmt(cy)} Z"
    )


def _fmt(value: float) -> str:
    return f"{float(value):.6g}"


def _transform_fields(transform: Any, fields: dict[str, Any]) -> dict[str, Any]:
    """Merge ``transform`` (a ``Mat3`` or transform-fn list) into ``fields['style']``.

    ``style.transform`` is where the model carries an affine transform; a ``Mat3``
    lowers via its canonical ``matrix`` transform function. An existing inline
    style dict is preserved and its own transforms are kept ahead of these.
    """
    fns = transform if isinstance(transform, list) else [transform]
    lowered = [fn.transform_fn() if isinstance(fn, Mat3) else fn for fn in fns]
    style = fields.get("style")
    if style is None:
        merged: dict[str, Any] = {"transform": lowered}
    elif isinstance(style, dict):
        existing = style.get("transform")
        base = list(existing) if isinstance(existing, list) else ([existing] if existing else [])
        merged = {**style, "transform": base + lowered}
    elif isinstance(style, (str, Handle)):
        # A token-named style composes with inline additions through the model's
        # Style.class mechanism: the token is referenced by `class`, the inline
        # properties sit beside it, so themed groups can also be transformed.
        merged = {"class": _handle_name(style, {"style", "text_style"}, "style"),
                  "transform": lowered}
    else:
        raise TypeError(
            "group(transform=...) needs an inline style dict or a style token name"
        )
    return {**fields, "style": merged}


def _style_set(fields: dict[str, Any], key: str, value: Any, what: str) -> dict[str, Any]:
    """Set ``style[key] = value`` on ``fields``, preserving an inline style dict.

    Composes after :func:`_transform_fields`, so ``group(transform=..., clip=...)``
    keeps both. A style *token* composes through ``Style.class`` (the token is
    referenced by ``class`` next to the inline addition), mirroring
    :func:`_transform_fields`.
    """
    style = fields.get("style")
    if style is None:
        merged: dict[str, Any] = {key: value}
    elif isinstance(style, dict):
        merged = {**style, key: value}
    elif isinstance(style, (str, Handle)):
        merged = {"class": _handle_name(style, {"style", "text_style"}, "style"),
                  key: value}
    else:
        raise TypeError(f"group({what}=...) needs an inline style dict or a style token name")
    return {**fields, "style": merged}


def _points(values: Any) -> list[list[float]]:
    return [_point(v) for v in values]


def _layout(
    kind: str,
    *,
    gap: Any = None,
    pad: Any = None,
    align: str | None = None,
    justify: str | None = None,
    columns: int | None = None,
    row_gap: Any = None,
    column_gap: Any = None,
) -> dict[str, Any]:
    layout: dict[str, Any] = {"kind": kind}
    if gap is not None:
        layout["gap"] = gap
    if row_gap is not None:
        layout["row_gap"] = row_gap
    if column_gap is not None:
        layout["column_gap"] = column_gap
    if pad is not None:
        layout["padding"] = pad
    if columns is not None:
        layout["columns"] = columns
    if align is not None:
        layout["align"] = align
    if justify is not None:
        layout["justify"] = justify
    return _coerce_handles(layout)


def _local_child(obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return obj
    box = obj.get("box")
    if isinstance(box, list) and len(box) >= 4:
        return {**obj, "box": [0, 0, box[2], box[3]]}
    return obj


def _coerce_handles(value: Any, field: str | None = None) -> Any:
    if isinstance(value, Handle):
        _check_handle(value, _allowed_handle_kinds(field), field or "value")
        return value.name
    if isinstance(value, Box):
        return value.list()
    if isinstance(value, dict):
        return {k: _coerce_handles(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_handles(v, field) for v in value]
    if isinstance(value, tuple):
        return tuple(_coerce_handles(v, field) for v in value)
    return value


def _handle_name(value: Handle | str, allowed: set[str], field: str) -> str:
    if isinstance(value, Handle):
        _check_handle(value, allowed, field)
        return value.name
    return str(value)


def _check_handle(handle: Handle, allowed: set[str], field: str) -> None:
    if allowed and handle.kind not in allowed:
        expected = ", ".join(sorted(allowed))
        raise TypeError(f"{field} expects handle kind {expected}; got {handle.kind}")


def _allowed_handle_kinds(field: str | None) -> set[str]:
    if field == "master":
        return {"master"}
    if field in {"src", "asset"}:
        return {"asset"}
    if field in {"symbol"}:
        return {"symbol"}
    if field in {"component"}:
        return {"component"}
    if field == "style":
        return {"style", "text_style"}
    if field == "stroke_style":
        return {"stroke_style"}
    if field in {"fill", "stroke", "color", "marker_color"}:
        return {"color"}
    if field in {"font", "font_family"}:
        return {"font"}
    return set()


__all__ = ["DocumentBuilder", "Handle", "MasterBuilder", "PageBuilder", "StackBuilder"]
