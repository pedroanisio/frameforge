"""Scalar- and vector-field helpers: sample a function over a domain and lower
it to a single FrameGraph group.

* :class:`VectorField` — a grid of arrows for ``(x, y) -> (u, v)`` flow.
* :class:`ScalarField` — ``(x, y) -> value`` rendered as filled-cell
  :meth:`~ScalarField.heatmap` and/or marching-squares :meth:`~ScalarField.contours`.

Both map a data ``domain`` into a box with Y flipped (domain-up is screen-up) and
emit children local to the group box, so the geometric audit (which does not
recurse into groups) stays silent.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Sequence


@dataclass(frozen=True)
class VectorField:
    """A 2D vector field sampled on a regular grid and drawn as arrows."""

    fn: Callable[[float, float], Sequence[float]]
    domain: tuple[float, float, float, float] = (-1.0, -1.0, 1.0, 1.0)

    def render(
        self,
        *,
        box: Sequence[float],
        steps_x: int = 14,
        steps_y: int = 14,
        color: str = "#334155",
        warm: str | None = None,
        width: float = 1.4,
        head: float = 5.0,
        id: str | None = None,
    ) -> dict[str, object]:
        xmin, ymin, xmax, ymax = self.domain
        bw, bh = float(box[2]), float(box[3])
        cell = min(bw / (steps_x + 1), bh / (steps_y + 1))
        arrow_len = cell * 0.78
        samples = []
        max_mag = 1e-9
        for j in range(steps_y + 1):
            for i in range(steps_x + 1):
                dx = xmin + (xmax - xmin) * i / steps_x
                dy = ymin + (ymax - ymin) * j / steps_y
                u, v = self.fn(dx, dy)
                mag = math.hypot(u, v)
                max_mag = max(max_mag, mag)
                px = (bw - steps_x * cell) / 2 + i * cell
                py = (bh - steps_y * cell) / 2 + (steps_y - j) * cell  # Y flip
                samples.append((px, py, float(u), float(v), mag))
        children: list[dict[str, object]] = []
        for px, py, u, v, mag in samples:
            if mag < 1e-9:
                continue
            ux, uy = u / mag, -v / mag  # screen Y is down → flip v
            half = arrow_len / 2 * min(1.0, 0.35 + 0.65 * mag / max_mag)
            sx, sy = px - ux * half, py - uy * half
            ex, ey = px + ux * half, py + uy * half
            col = _mix(color, warm, mag / max_mag) if warm else color
            children.append({"type": "polyline", "points": [[sx, sy], [ex, ey]],
                             "stroke": col, "stroke_style": {"stroke_width": width}})
            children.append(_arrow_head(ex, ey, ux, uy, head, col))
        group: dict[str, object] = {"type": "group", "box": list(box), "children": children}
        if id is not None:
            group["id"] = id
        return group


@dataclass(frozen=True)
class ScalarField:
    """A 2D scalar field; render as a heatmap and/or contour lines."""

    fn: Callable[[float, float], float]
    domain: tuple[float, float, float, float] = (-1.0, -1.0, 1.0, 1.0)

    def _sample(self, steps_x: int, steps_y: int) -> tuple[list[list[float]], float, float]:
        xmin, ymin, xmax, ymax = self.domain
        grid: list[list[float]] = []
        lo, hi = math.inf, -math.inf
        for j in range(steps_y + 1):
            row: list[float] = []
            for i in range(steps_x + 1):
                dx = xmin + (xmax - xmin) * i / steps_x
                dy = ymin + (ymax - ymin) * j / steps_y
                val = float(self.fn(dx, dy))
                row.append(val)
                lo, hi = min(lo, val), max(hi, val)
            grid.append(row)
        return grid, lo, hi

    def heatmap(
        self,
        *,
        box: Sequence[float],
        steps_x: int = 28,
        steps_y: int = 22,
        low: str = "#0b3866",
        high: str = "#fde047",
        id: str | None = None,
    ) -> dict[str, object]:
        grid, lo, hi = self._sample(steps_x, steps_y)
        bw, bh = float(box[2]), float(box[3])
        cw, ch = bw / steps_x, bh / steps_y
        span = (hi - lo) or 1.0
        children: list[dict[str, object]] = []
        for j in range(steps_y):
            for i in range(steps_x):
                # cell centre value; Y flipped so domain-up is screen-up
                val = (grid[j][i] + grid[j + 1][i] + grid[j][i + 1] + grid[j + 1][i + 1]) / 4
                t = (val - lo) / span
                x = i * cw
                y = bh - (j + 1) * ch
                children.append({"type": "rect", "box": [x, y, cw + 0.6, ch + 0.6],
                                 "fill": _mix(low, high, t), "decorative": True})
        group: dict[str, object] = {"type": "group", "box": list(box), "children": children}
        if id is not None:
            group["id"] = id
        return group

    def contours(
        self,
        *,
        box: Sequence[float],
        levels: Sequence[float] | int = 8,
        steps_x: int = 48,
        steps_y: int = 40,
        color: str = "#0f172a",
        width: float = 1.2,
        id: str | None = None,
    ) -> dict[str, object]:
        """Marching-squares iso-lines at each level (auto-spaced if ``levels`` is an int)."""
        grid, lo, hi = self._sample(steps_x, steps_y)
        if isinstance(levels, int):
            n = max(1, levels)
            level_values = [lo + (hi - lo) * (k + 0.5) / n for k in range(n)]
        else:
            level_values = list(levels)
        bw, bh = float(box[2]), float(box[3])
        cw, ch = bw / steps_x, bh / steps_y

        def pt(i: float, j: float) -> list[float]:
            return [i * cw, bh - j * ch]  # Y flip

        children: list[dict[str, object]] = []
        for lv in level_values:
            for j in range(steps_y):
                for i in range(steps_x):
                    corners = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
                    for a, b in _marching_segments(corners, lv):
                        p0 = _edge_point(i, j, a, lv, corners, pt)
                        p1 = _edge_point(i, j, b, lv, corners, pt)
                        children.append({"type": "polyline", "points": [p0, p1],
                                         "stroke": color, "stroke_style": {"stroke_width": width}})
        group: dict[str, object] = {"type": "group", "box": list(box), "children": children}
        if id is not None:
            group["id"] = id
        return group


# Marching-squares edge order: 0=bottom,1=right,2=top,3=left of the cell.
_EDGE_CORNERS = {0: (0, 1), 1: (1, 2), 2: (2, 3), 3: (3, 0)}
_CASE_EDGES = {
    1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 5: [(3, 2), (0, 1)],
    6: [(0, 2)], 7: [(3, 2)], 8: [(2, 3)], 9: [(0, 3)], 10: [(0, 1), (2, 3)],
    11: [(0, 2)], 12: [(1, 3)], 13: [(0, 1)], 14: [(0, 3)],
}


def _marching_segments(corners: Sequence[float], level: float) -> list[tuple[int, int]]:
    idx = sum((1 << k) for k, c in enumerate(corners) if c >= level)
    if idx in (0, 15):
        return []
    return _CASE_EDGES.get(idx, [])


def _edge_point(i: int, j: int, edge: int, level: float, corners: Sequence[float],
                pt: Callable[[float, float], list[float]]) -> list[float]:
    ca, cb = _EDGE_CORNERS[edge]
    va, vb = corners[ca], corners[cb]
    t = 0.5 if abs(vb - va) < 1e-12 else (level - va) / (vb - va)
    t = max(0.0, min(1.0, t))
    # corner (i,j) local offsets, matching corners=[BL, BR, TR, TL]
    coords = {0: (i, j), 1: (i + 1, j), 2: (i + 1, j + 1), 3: (i, j + 1)}
    ax, aj = coords[ca]
    bx, bj = coords[cb]
    return pt(ax + (bx - ax) * t, aj + (bj - aj) * t)


def _arrow_head(ex: float, ey: float, ux: float, uy: float, size: float, color: str) -> dict[str, object]:
    px, py = -uy, ux
    bx, by = ex - ux * size, ey - uy * size
    hw = size * 0.5
    return {"type": "polyline", "closed": True, "fill": color, "stroke": color,
            "points": [[ex, ey], [bx + px * hw, by + py * hw], [bx - px * hw, by - py * hw]]}


def _mix(c0: str, c1: str | None, t: float) -> str:
    if c1 is None:
        return c0
    t = max(0.0, min(1.0, t))
    a = _hex(c0)
    b = _hex(c1)
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))


def _hex(c: str) -> tuple[int, int, int]:
    s = c.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


__all__ = ["ScalarField", "VectorField"]
