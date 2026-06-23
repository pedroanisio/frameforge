"""A thin charting helper that lowers to FrameGraph primitives.

:class:`Chart` decorates a :class:`framegraph.sdk.draw.Frame` (a data-domain →
page-box mapping) with the boilerplate a technical deck repeats on every plot:
axis spines, ticks, gridlines, data series, and a legend. Every method appends
ordinary FrameGraph objects (``line`` / ``polyline`` / ``path`` / ``rect`` /
``text``); :meth:`objects` returns them for ``PageBuilder.extend``.

**Honest scope (§13).** This is a *lowering helper*, not a charting engine. It
does no statistics, no scale inference, and no automatic "nice" ticking — you
pass the tick values and the data, it emits shapes. FrameGraph's non-goals
explicitly exclude a general-purpose scientific-charting replacement; this stays
on the authoring side of that line by only translating coordinates you provide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from framegraph.sdk.draw import Frame
from framegraph.sdk.geometry import Path

Point = Sequence[float]
Style = dict[str, Any]

_AXIS_COLOR = "#C4D0DD"
_LABEL_STYLE: Style = {
    "font_family": ["Inter", "Helvetica Neue", "Arial", "sans-serif"],
    "font_size": 11,
    "font_weight": 600,
    "color": "#6B7A90",
}


@dataclass
class Chart:
    """Accumulates chart objects over a :class:`Frame`. Methods chain."""

    frame: Frame
    _objects: list[dict[str, Any]] = field(default_factory=list)
    _legend: list[tuple[str, str]] = field(default_factory=list)

    # ---- structure -------------------------------------------------------- #
    def axes(
        self,
        *,
        x_ticks: Sequence[float] = (),
        y_ticks: Sequence[float] = (),
        x_format: Callable[[float], str] = str,
        y_format: Callable[[float], str] = str,
        grid: bool = False,
        axis_color: str = _AXIS_COLOR,
        grid_color: str | None = None,
        label_style: Style | None = None,
        tick_len: float = 5.0,
        label_gap: float = 9.0,
    ) -> "Chart":
        """Draw L-shaped axes with ticks, labels, and optional gridlines."""
        bx, by, bw, bh = self._plot()
        x1, y1 = bx + bw, by + bh
        lbl = {**_LABEL_STYLE, **(label_style or {})}
        gcol = grid_color or "#EAF0F6"
        self._line((bx, by), (bx, y1), axis_color, 1.2)      # y spine
        self._line((bx, y1), (x1, y1), axis_color, 1.2)      # x spine
        for xv in x_ticks:
            px = self.frame.point(xv, self.frame.domain[1]).x
            if grid:
                self._line((px, by), (px, y1), gcol, 0.8)
            self._line((px, y1), (px, y1 + tick_len), axis_color, 1.2)
            self._text([px - 30, y1 + label_gap, 60, 16], x_format(xv),
                       {**lbl, "align": "center"})
        for yv in y_ticks:
            py = self.frame.point(self.frame.domain[0], yv).y
            if grid:
                self._line((bx, py), (x1, py), gcol, 0.8)
            self._line((bx - tick_len, py), (bx, py), axis_color, 1.2)
            self._text([bx - 58, py - 8, 48, 16], y_format(yv),
                       {**lbl, "align": "right"})
        return self

    # ---- series ----------------------------------------------------------- #
    def line(
        self,
        points: Sequence[Point],
        *,
        stroke: str = "#333333",
        width: float = 2.0,
        smooth: bool = False,
        label: str | None = None,
        dash: Sequence[float] | None = None,
    ) -> "Chart":
        """Plot a polyline (or a smooth Catmull-Rom path) through data points."""
        mapped = [self.frame.point(float(x), float(y)) for x, y in points]
        ss: dict[str, Any] = {"stroke_width": width}
        if dash is not None:
            ss["stroke_dasharray"] = list(dash)
        if smooth and len(mapped) >= 2:
            path = Path().move_to(mapped[0].x, mapped[0].y).through(mapped[1:])
            self._objects.append(path.object(stroke=stroke, fill="none", stroke_style=ss))
        else:
            self._objects.append({
                "type": "polyline",
                "points": [[p.x, p.y] for p in mapped],
                "stroke": stroke,
                "stroke_style": ss,
            })
        if label:
            self._legend.append((label, stroke))
        return self

    def bars(
        self,
        points: Sequence[Point],
        *,
        baseline: float = 0.0,
        width: float = 14.0,
        fill: str = "#333333",
        radius: float | None = None,
        label: str | None = None,
    ) -> "Chart":
        """Draw a vertical bar from ``baseline`` to each data point."""
        for x, y in points:
            top = self.frame.point(float(x), float(y))
            base = self.frame.point(float(x), baseline)
            y0, h = (top.y, base.y - top.y) if base.y >= top.y else (base.y, top.y - base.y)
            rect: dict[str, Any] = {
                "type": "rect",
                "box": [top.x - width / 2, y0, width, h],
                "fill": fill,
            }
            if radius is not None:
                rect["radius"] = radius
            self._objects.append(rect)
        if label:
            self._legend.append((label, fill))
        return self

    def marker(self, x: float, y: float, *, r: float = 4.0, fill: str = "#333333") -> "Chart":
        """Place a dot at a data point (e.g. to flag a maximum)."""
        p = self.frame.point(float(x), float(y))
        self._objects.append({"type": "ellipse", "center": [p.x, p.y], "rx": r, "ry": r, "fill": fill})
        return self

    # ---- legend ----------------------------------------------------------- #
    def legend(
        self,
        entries: Sequence[tuple[str, str]] | None = None,
        *,
        at: str | Point = "tr",
        swatch: float = 12.0,
        gap: float = 8.0,
        pitch: float = 26.0,
        label_style: Style | None = None,
    ) -> "Chart":
        """Render a horizontal legend; defaults to the labelled series so far.

        ``at`` is a corner ("tl", "tr", "bl", "br") of the plot box or an explicit
        ``(x, y)`` top-left anchor.
        """
        items = list(entries) if entries is not None else list(self._legend)
        if not items:
            return self
        lbl = {**_LABEL_STYLE, "font_size": 11, **(label_style or {})}
        x, y = self._anchor(at, items, swatch, gap, pitch)
        cx = x
        for text, color in items:
            self._objects.append({"type": "rect", "box": [cx, y, swatch, swatch],
                                  "fill": color, "radius": 3})
            self._text([cx + swatch + gap, y - 1, max(40.0, pitch + len(text) * 6), 16],
                       text, lbl)
            cx += swatch + gap + len(text) * 6.2 + pitch * 0.4
        return self

    def objects(self) -> list[dict[str, Any]]:
        """Return the accumulated chart objects (order = draw order)."""
        return self._objects

    def add_to(self, page: Any) -> Any:
        """Append this chart's objects to a page/layer builder and return it."""
        return page.extend(self.objects())

    # ---- internals -------------------------------------------------------- #
    def _plot(self) -> tuple[float, float, float, float]:
        bx, by, bw, bh = self.frame.box
        return (float(bx), float(by), float(bw), float(bh))

    def _line(self, a: Point, b: Point, color: str, width: float) -> None:
        self._objects.append({
            "type": "line",
            "from": [float(a[0]), float(a[1])],
            "to": [float(b[0]), float(b[1])],
            "stroke": color,
            "stroke_style": {"stroke_width": width},
        })

    def _text(self, box: list[float], text: str, style: Style) -> None:
        self._objects.append({"type": "text", "box": box, "text": text, "style": style})

    def _anchor(self, at: str | Point, items: list[tuple[str, str]],
                swatch: float, gap: float, pitch: float) -> tuple[float, float]:
        if not isinstance(at, str):
            return (float(at[0]), float(at[1]))
        bx, by, bw, bh = self._plot()
        width = sum(swatch + gap + len(t) * 6.2 + pitch * 0.4 for t, _ in items)
        pad = 12.0
        x = bx + pad if at.endswith("l") else bx + bw - width - pad
        y = by + pad if at.startswith("t") else by + bh - swatch - pad
        return (x, y)


__all__ = ["Chart"]
