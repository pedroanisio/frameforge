"""A thin charting helper that lowers to FrameForge primitives.

:class:`Chart` decorates a :class:`frameforge.sdk.draw.Frame` (a data-domain →
page-box mapping) with the boilerplate a technical deck repeats on every plot:
axis spines, ticks, gridlines, data series, and a legend. Every method appends
ordinary FrameForge objects (``line`` / ``polyline`` / ``path`` / ``rect`` /
``text``); :meth:`objects` returns them for ``PageBuilder.extend``.

**Honest scope (§13).** This is a *lowering helper*, not a charting engine. It
does no statistics, no scale inference, and no automatic "nice" ticking — you
pass the tick values and the data, it emits shapes. FrameForge's non-goals
explicitly exclude a general-purpose scientific-charting replacement; this stays
on the authoring side of that line by only translating coordinates you provide.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from frameforge.sdk.draw import Frame
from frameforge.sdk.geometry import Path

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

    def scatter(
        self,
        points: Sequence[Point],
        *,
        r: float = 3.5,
        fill: str = "#333333",
        label: str | None = None,
    ) -> "Chart":
        """Place a dot (radius ``r`` px) at each data point."""
        for x, y in points:
            p = self.frame.point(float(x), float(y))
            self._objects.append(
                {"type": "ellipse", "center": [p.x, p.y], "rx": r, "ry": r, "fill": fill})
        if label:
            self._legend.append((label, fill))
        return self

    def area(
        self,
        points: Sequence[Point],
        *,
        baseline: float = 0.0,
        fill: str = "#33333333",
        stroke: str | None = None,
        width: float = 2.0,
        label: str | None = None,
    ) -> "Chart":
        """Fill the region between a series and ``baseline`` (a closed polyline).

        The polygon walks the mapped data points, then drops to ``baseline`` under
        the last and first x values to close. ``stroke`` optionally re-draws the
        series' top edge as an open polyline (the area fill has no outline).
        """
        if len(points) < 2:
            raise ValueError("area needs >= 2 points")
        mapped = [self.frame.point(float(x), float(y)) for x, y in points]
        base_first = self.frame.point(float(points[0][0]), baseline)
        base_last = self.frame.point(float(points[-1][0]), baseline)
        poly = [[p.x, p.y] for p in mapped]
        poly += [[base_last.x, base_last.y], [base_first.x, base_first.y]]
        self._objects.append(
            {"type": "polyline", "points": poly, "closed": True, "fill": fill})
        if stroke:
            self._objects.append({
                "type": "polyline",
                "points": [[p.x, p.y] for p in mapped],
                "stroke": stroke,
                "stroke_style": {"stroke_width": width},
            })
        if label:
            self._legend.append((label, fill))
        return self

    def pie(
        self,
        values: Sequence[float],
        *,
        colors: Sequence[str],
        labels: Sequence[str] | None = None,
        center: Point | None = None,
        r: float | None = None,
        inner_ratio: float = 0.0,
        start_angle: float = -90.0,
    ) -> "Chart":
        """Draw a pie (or, with ``inner_ratio`` > 0, a donut) inside the plot box.

        ``values`` are relative weights (non-negative; normalised to 360°) and
        slice ``i`` fills with ``colors[i % len(colors)]``. A part-to-whole chart
        has no x/y mapping, so the Frame's data domain is ignored: the pie sits at
        ``center`` (default: the plot box centre) with radius ``r`` (default: the
        largest circle the box holds). Angles follow the SDK convention (0° = +x,
        clockwise-positive in Y-down page space), starting at 12 o'clock. Each
        slice lowers to one closed ``path`` sector; ``labels`` register legend
        entries (finish with :meth:`legend`).
        """
        vals = [float(v) for v in values]
        if not vals:
            raise ValueError("pie needs a non-empty values list")
        if any(v < 0 for v in vals):
            raise ValueError("pie values must be non-negative")
        total = sum(vals)
        if total <= 0:
            raise ValueError("pie values must sum to > 0")
        if not colors:
            raise ValueError("pie needs at least one colour")
        if not 0.0 <= inner_ratio < 1.0:
            raise ValueError("inner_ratio must be in [0, 1)")
        bx, by, bw, bh = self._plot()
        cx, cy = ((float(center[0]), float(center[1])) if center is not None
                  else (bx + bw / 2.0, by + bh / 2.0))
        radius = float(r) if r is not None else min(bw, bh) / 2.0
        angle = float(start_angle)
        for i, v in enumerate(vals):
            sweep = 360.0 * v / total
            color = str(colors[i % len(colors)])
            if v > 0:
                self._objects.append(
                    _sector(cx, cy, radius, angle, angle + sweep,
                            inner_ratio=inner_ratio, fill=color))
            if labels is not None and i < len(labels) and labels[i]:
                self._legend.append((str(labels[i]), color))
            angle += sweep
        return self

    def donut(self, values: Sequence[float], *, inner_ratio: float = 0.55,
              **kwargs: Any) -> "Chart":
        """A pie with a hole: :meth:`pie` with ``inner_ratio`` (default 0.55)."""
        return self.pie(values, inner_ratio=inner_ratio, **kwargs)

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


# ---- pie/donut sector lowering (module-level pure helpers) ------------------ #
def _polar(cx: float, cy: float, r: float, degrees: float) -> tuple[float, float]:
    """Point on the circle at ``degrees`` (0° = +x, clockwise-positive in Y-down)."""
    rad = math.radians(degrees)
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def _ring_d(cx: float, cy: float, r: float) -> str:
    """A full circle as two 180° arcs (SVG cannot draw a 360° arc in one command)."""
    return (f"M {cx + r:.6g} {cy:.6g} A {r:.6g} {r:.6g} 0 1 1 {cx - r:.6g} {cy:.6g} "
            f"A {r:.6g} {r:.6g} 0 1 1 {cx + r:.6g} {cy:.6g} Z")


def _sector(cx: float, cy: float, r: float, a0: float, a1: float, *,
            inner_ratio: float, fill: str) -> dict[str, Any]:
    """One pie/donut slice from ``a0`` to ``a1`` degrees as a closed ``path`` dict.

    A full-circle slice (a single 100% value) degenerates: it becomes an
    ``ellipse`` (solid) or an even-odd two-circle ring path (donut), because a
    360° SVG arc between coincident endpoints would collapse to nothing.
    """
    sweep = a1 - a0
    if sweep >= 360.0 - 1e-9:
        if inner_ratio > 0:
            d = f"{_ring_d(cx, cy, r)} {_ring_d(cx, cy, r * inner_ratio)}"
            return {"type": "path", "d": d, "fill": fill, "style": {"fill_rule": "evenodd"}}
        return {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": fill}
    large = abs(sweep) > 180.0
    clockwise = sweep >= 0
    ox0, oy0 = _polar(cx, cy, r, a0)
    ox1, oy1 = _polar(cx, cy, r, a1)
    if inner_ratio <= 0:
        geom = (Path().move_to(cx, cy).line_to(ox0, oy0)
                .arc_to(r, r, 0.0, large, clockwise, [ox1, oy1]).close())
    else:
        ri = r * inner_ratio
        ix0, iy0 = _polar(cx, cy, ri, a0)
        ix1, iy1 = _polar(cx, cy, ri, a1)
        geom = (Path().move_to(ox0, oy0)
                .arc_to(r, r, 0.0, large, clockwise, [ox1, oy1])
                .line_to(ix1, iy1)
                .arc_to(ri, ri, 0.0, large, not clockwise, [ix0, iy0])
                .close())
    return geom.object(fill=fill)


__all__ = ["Chart"]
