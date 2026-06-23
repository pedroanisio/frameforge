"""Authoring builders for the Python SDK."""
from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path as FsPath
from typing import Any, Iterator

from framegraph.sdk.clip import normalize_clip
from framegraph.sdk.expand import ExpandOptions, expand
from framegraph.sdk.geometry import Mat3, Path as _GeomPath, Vec2
from framegraph.sdk.layout import Box
from framegraph.sdk.model import HEAD_VERSION, validate_document


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
        self._doc: dict[str, Any] = {"dsl": "FrameGraph", "version": version, "pages": []}
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

    def define_symbol(self, name: str, *, box: list[Any], objects: list[dict[str, Any]], **fields: Any) -> Handle:
        symbol = {"box": box, "objects": _coerce_handles(objects)}
        symbol.update(_coerce_handles(fields))
        self._defs("symbols")[name] = symbol
        return Handle("symbol", name)

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
    ) -> "PageBuilder":
        """Append a page and return its builder.

        ``coordinate_mode`` ("absolute" or "flow") sets the page's
        ``rendering.coordinate_mode``; absolute is the natural choice for decks
        that place objects at explicit page coordinates. The value is validated
        against the model at :meth:`build` time, not here.
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
        self._doc["pages"].append(page)
        return PageBuilder(page)

    def flow(self, id: str, *, master: Handle | str, story: list[dict[str, Any]], **fields: Any) -> None:
        section: dict[str, Any] = {
            "mode": "flow",
            "id": id,
            "master": _handle_name(master, {"master"}, "master"),
            "story": _coerce_handles(story),
        }
        section.update(_coerce_handles(fields))
        self._doc["pages"].append(section)

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
        """
        from framegraph.sdk.io import serialize
        from framegraph.sdk.validate import validate_static_rules

        doc = self.build(expand_reuse=expand_reuse)
        report = validate_static_rules(doc) if validate else None
        if report is not None and fail_on_error and not report.ok:
            errors = [issue for issue in report.issues if issue.severity == "error"]
            detail = errors[0].message if errors else "static validation failed"
            raise ValueError(detail)
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


class PageBuilder:
    """Builder for a single page's layers and visual objects."""

    def __init__(self, page: dict[str, Any]) -> None:
        self._page = page
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

    def text(self, box: list[Any], text: str, **fields: Any) -> "PageBuilder":
        return self.add({"type": "text", "box": box, "text": text, **fields})

    def image(self, box: list[Any], src: Handle | str, **fields: Any) -> "PageBuilder":
        return self.add({"type": "image", "box": box, "src": _handle_name(src, {"asset"}, "src"), **fields})

    def line(self, start: list[float], end: list[float], **fields: Any) -> "PageBuilder":
        return self.add({"type": "line", "from": start, "to": end, **fields})

    def chart(
        self,
        box: Any,
        *,
        domain: tuple[float, float, float, float],
        x_scale: Any = "linear",
        y_scale: Any = "linear",
    ):
        """Return a :class:`~framegraph.sdk.Chart` mapped to ``box``.

        Finish with ``.add_to(page)`` or pass ``chart.objects()`` to
        :meth:`extend`.
        """
        from framegraph.sdk.chart import Chart
        from framegraph.sdk.draw import Frame

        return Chart(Frame(domain=domain, box=tuple(float(v) for v in box), x_scale=x_scale, y_scale=y_scale))

    def widget(self, obj: dict[str, Any]) -> "PageBuilder":
        """Add a prebuilt SDK widget object and return the page builder."""
        return self.add(obj)

    def badge(self, box: Any, text: str, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import badge

        return self.add(badge(box, text, **fields))

    def pill(self, box: Any, text: str | None = None, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import pill

        return self.add(pill(box, text, **fields))

    def button(self, box: Any, label: str, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import button

        return self.add(button(box, label, **fields))

    def avatar(self, box: Any, name: str, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import avatar

        return self.add(avatar(box, name, **fields))

    def kpi(self, box: Any, label: str, value: str, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import kpi

        return self.add(kpi(box, label, value, **fields))

    def field(self, box: Any, label: str, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import field

        return self.add(field(box, label, **fields))

    def toggle(self, box: Any, *, on: bool = False, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import toggle

        return self.add(toggle(box, on=on, **fields))

    def tabs(self, box: Any, items: list[str], **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import tabs

        return self.add(tabs(box, items, **fields))

    def progress(self, box: Any, value: float, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import progress

        return self.add(progress(box, value, **fields))

    def divider(self, box: Any, **fields: Any) -> "PageBuilder":
        from framegraph.sdk.widgets import divider

        return self.add(divider(box, **fields))

    def card(self, box: Any, **fields: Any):
        """Add a card widget and return its :class:`~framegraph.sdk.Panel`."""
        from framegraph.sdk.widgets import card

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
        from framegraph.sdk.widgets import table

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
        :class:`framegraph.sdk.Path` builder (whose geometry is lowered for you)."""
        if isinstance(d, _GeomPath):
            return self.add(d.object(**fields))
        return self.add({"type": "path", "d": d, **fields})

    def arc(self, center: Any, r: float, start: float, end: float, *,
            ry: float | None = None, **fields: Any) -> "PageBuilder":
        """Add an open circular (or elliptical) arc, lowered to a canonical ``path``.

        Angles are degrees, clockwise-positive in FrameGraph's Y-down page space
        with 0° at the +x axis (3 o'clock) — the same convention as
        :meth:`~framegraph.sdk.Mat3.rotate`. ``ry`` makes the arc elliptical
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

        ``transform`` (a :class:`~framegraph.sdk.Mat3` or a list of transform
        functions) is lowered onto the group's ``style.transform`` so the whole
        group is placed/scaled/rotated as a unit. ``clip`` lowers onto
        ``style.clip_path`` so the group's contents are masked to a region — a box
        ``[x, y, w, h]``, a points list, a :class:`~framegraph.sdk.Path`, a clip
        dict from :mod:`framegraph.sdk.clip`, or a CSS string (see
        :func:`~framegraph.sdk.clip.normalize_clip`). See :meth:`frame` for
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
    else:
        raise TypeError(
            "group(transform=...) needs an inline style dict, not a style reference"
        )
    return {**fields, "style": merged}


def _style_set(fields: dict[str, Any], key: str, value: Any, what: str) -> dict[str, Any]:
    """Set ``style[key] = value`` on ``fields``, preserving an inline style dict.

    Composes after :func:`_transform_fields`, so ``group(transform=..., clip=...)``
    keeps both. A style *reference* (a token name) cannot carry an inline addition,
    so that is rejected with the same discipline as ``transform``.
    """
    style = fields.get("style")
    if style is None:
        merged: dict[str, Any] = {key: value}
    elif isinstance(style, dict):
        merged = {**style, key: value}
    else:
        raise TypeError(f"group({what}=...) needs an inline style dict, not a style reference")
    return {**fields, "style": merged}


def _points(values: Any) -> list[list[float]]:
    return [_point(v) for v in values]


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


__all__ = ["DocumentBuilder", "Handle", "PageBuilder"]
