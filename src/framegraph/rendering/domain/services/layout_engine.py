"""LayoutEngine — arrange a group's children for ``Group.layout``.

The engine is intentionally pure and backend-agnostic. It computes local-frame
boxes for direct group children; renderers can then translate and, when needed,
override the child box extent without mutating the source document.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import num


class LayoutEngine:
    def arrange(self, width: float, height: float, children, layout) -> list[tuple[float, float, float, float]]:
        """Return one arranged ``(x, y, w, h)`` per direct child."""
        kind = layout.get("kind")
        sizes = [self._size(c) for c in children]
        if kind not in ("row", "column", "grid", "wrap"):
            return [(*self._origin(c), *size) for c, size in zip(children, sizes)]

        pad_t, pad_r, pad_b, pad_l = self._padding(layout.get("padding"))
        x0, y0 = pad_l, pad_t
        avail_w = max(0.0, width - pad_l - pad_r)
        avail_h = max(0.0, height - pad_t - pad_b)
        gap = num(layout.get("gap"), 0) or 0
        col_gap = num(layout.get("column_gap"), gap)
        row_gap = num(layout.get("row_gap"), gap)
        align = layout.get("align") or "start"
        justify = layout.get("justify") or "start"

        if kind == "row":
            return self._line(
                children, sizes, x0, y0, avail_w, avail_h, axis="row",
                gap=col_gap, align=align, justify=justify,
            )
        if kind == "column":
            return self._line(
                children, sizes, x0, y0, avail_h, avail_w, axis="column",
                gap=row_gap, align=align, justify=justify,
            )
        if kind == "wrap":
            return self._wrap(children, sizes, x0, y0, avail_w, col_gap, row_gap, align, justify)
        return self._grid(children, sizes, x0, y0, avail_w, avail_h, col_gap, row_gap, align, layout)

    def _line(
        self,
        children,
        sizes: list[tuple[float, float]],
        main_start: float,
        cross_start: float,
        main_extent: float,
        cross_extent: float,
        *,
        axis: str,
        gap: float,
        align: str,
        justify: str,
    ) -> list[tuple[float, float, float, float]]:
        fixed = 0.0
        grow_total = 0.0
        main_sizes: list[float] = []
        cross_sizes: list[float] = []
        fill_main: list[bool] = []
        main_key = "width" if axis == "row" else "height"
        for child, (cw, ch) in zip(children, sizes):
            sizing = self._sizing(child)
            is_fill = sizing.get(main_key) == "fill"
            main = cw if axis == "row" else ch
            cross = ch if axis == "row" else cw
            if is_fill:
                grow_total += max(0.0, num(sizing.get("grow"), 1) or 1)
            else:
                fixed += main
            main_sizes.append(main)
            cross_sizes.append(cross)
            fill_main.append(is_fill)

        gaps = gap * max(0, len(children) - 1)
        free = max(0.0, main_extent - fixed - gaps)
        if grow_total:
            for i, child in enumerate(children):
                if fill_main[i]:
                    weight = max(0.0, num(self._sizing(child).get("grow"), 1) or 1)
                    main_sizes[i] = free * weight / grow_total

        used = sum(main_sizes) + gaps
        offset, actual_gap = self._justify(main_extent, used, gap, len(children), justify)
        pos = main_start + offset
        out: list[tuple[float, float, float, float]] = []
        for i, child in enumerate(children):
            main = main_sizes[i]
            cross = self._cross_size(child, cross_sizes[i], cross_extent, axis, align)
            cross_pos = cross_start + self._cross(0, cross_extent, cross, align)
            if axis == "row":
                out.append((pos, cross_pos, main, cross))
            else:
                out.append((cross_pos, pos, cross, main))
            pos += main + actual_gap
        return out

    def _grid(
        self,
        children,
        sizes: list[tuple[float, float]],
        x0: float,
        y0: float,
        avail_w: float,
        avail_h: float,
        col_gap: float,
        row_gap: float,
        align: str,
        layout,
    ) -> list[tuple[float, float, float, float]]:
        columns = max(1, int(num(layout.get("columns"), 1) or 1))
        # Pass 1 — occupancy placement (§3.6e grid_span). Each child claims a
        # cs×rs block at the next free row-major slot; neighbours flow around it.
        # With every span [1, 1] this reproduces the plain (i%columns, i//columns)
        # fill exactly, so span-free grids — every current fixture — are unmoved.
        occupied: set[tuple[int, int]] = set()
        placements: list[tuple[int, int, int, int]] = []
        cursor = 0
        max_row = 0
        for child in children:
            cs, rs = self._grid_span(child, columns)
            pos = cursor
            limit = (max_row + rs + len(children) + 2) * columns
            while pos <= limit:
                col, row = pos % columns, pos // columns
                if col + cs > columns:
                    pos = (row + 1) * columns  # a wide block cannot straddle the edge
                    continue
                if all((col + dc, row + dr) not in occupied
                       for dc in range(cs) for dr in range(rs)):
                    break
                pos += 1
            col, row = pos % columns, pos // columns
            for dc in range(cs):
                for dr in range(rs):
                    occupied.add((col + dc, row + dr))
            placements.append((col, row, cs, rs))
            max_row = max(max_row, row + rs - 1)
            cursor = pos + 1
        rows = max(1, max_row + 1)
        cell_w = max(0.0, (avail_w - (columns - 1) * col_gap) / columns)
        cell_h = max(0.0, (avail_h - (rows - 1) * row_gap) / rows)
        out: list[tuple[float, float, float, float]] = []
        for (col, row, cs, rs), (cw, ch), child in zip(placements, sizes, children):
            span_w = cs * cell_w + (cs - 1) * col_gap
            span_h = rs * cell_h + (rs - 1) * row_gap
            aw = span_w if self._fill_width(child) else cw
            ah = span_h if self._fill_height(child) or align == "stretch" else ch
            out.append((
                x0 + col * (cell_w + col_gap),
                y0 + row * (cell_h + row_gap) + self._cross(0, span_h, ah, align),
                aw,
                ah,
            ))
        return out

    def _wrap(
        self,
        children,
        sizes: list[tuple[float, float]],
        x0: float,
        y0: float,
        avail_w: float,
        col_gap: float,
        row_gap: float,
        align: str,
        justify: str,
    ) -> list[tuple[float, float, float, float]]:
        rows: list[list[tuple[int, float, float]]] = [[]]
        row_w = 0.0
        for i, (cw, ch) in enumerate(sizes):
            add = cw if not rows[-1] else cw + col_gap
            if rows[-1] and row_w + add > avail_w:
                rows.append([])
                row_w = 0.0
                add = cw
            rows[-1].append((i, cw, ch))
            row_w += add

        out: list[tuple[float, float, float, float] | None] = [None] * len(children)
        y = y0
        for row in rows:
            row_h = max((ch for _, _, ch in row), default=0.0)
            used = sum(cw for _, cw, _ in row) + col_gap * max(0, len(row) - 1)
            offset, actual_gap = self._justify(avail_w, used, col_gap, len(row), justify)
            x = x0 + offset
            for i, cw, ch in row:
                ah = row_h if self._fill_height(children[i]) or align == "stretch" else ch
                out[i] = (x, y + self._cross(0, row_h, ah, align), cw, ah)
                x += cw + actual_gap
            y += row_h + row_gap
        return [box or (0.0, 0.0, 0.0, 0.0) for box in out]

    # ---- helpers ---------------------------------------------------------- #
    @staticmethod
    def _size(child) -> tuple[float, float]:
        box = child.get("box") if isinstance(child, dict) else None
        if isinstance(box, list) and len(box) >= 4:
            return (num(box[2], 0) or 0, num(box[3], 0) or 0)
        return (0.0, 0.0)

    @staticmethod
    def _origin(child) -> tuple[float, float]:
        box = child.get("box") if isinstance(child, dict) else None
        if isinstance(box, list) and len(box) >= 2:
            return (num(box[0], 0) or 0, num(box[1], 0) or 0)
        return (0.0, 0.0)

    @staticmethod
    def _cross(start: float, extent: float, child_extent: float, align: str) -> float:
        if align == "center":
            return start + (extent - child_extent) / 2
        if align == "end":
            return start + extent - child_extent
        return start

    @staticmethod
    def _justify(extent: float, used: float, gap: float, count: int, justify: str) -> tuple[float, float]:
        free = max(0.0, extent - used)
        if justify == "center":
            return free / 2, gap
        if justify == "end":
            return free, gap
        if justify == "space-between" and count > 1:
            return 0.0, gap + free / (count - 1)
        if justify == "space-around" and count:
            extra = free / count
            return extra / 2, gap + extra
        if justify == "space-evenly" and count:
            extra = free / (count + 1)
            return extra, gap + extra
        return 0.0, gap

    @classmethod
    def _cross_size(cls, child, current: float, extent: float, axis: str, align: str) -> float:
        if align == "stretch":
            return extent
        if axis == "row" and cls._fill_height(child):
            return extent
        if axis == "column" and cls._fill_width(child):
            return extent
        return current

    @staticmethod
    def _grid_span(child, columns: int) -> tuple[int, int]:
        """`[column_span, row_span]` for a grid child (§3.6e), defaulting to
        `(1, 1)`. The column span is clamped to the grid width."""
        span = child.get("grid_span") if isinstance(child, dict) else None
        if not (isinstance(span, (list, tuple)) and len(span) == 2):
            return 1, 1
        cs = max(1, min(int(span[0]), columns))
        rs = max(1, int(span[1]))
        return cs, rs

    @staticmethod
    def _sizing(child) -> dict:
        sizing = child.get("sizing") if isinstance(child, dict) else {}
        return sizing if isinstance(sizing, dict) else {}

    @classmethod
    def _fill_width(cls, child) -> bool:
        return cls._sizing(child).get("width") == "fill"

    @classmethod
    def _fill_height(cls, child) -> bool:
        return cls._sizing(child).get("height") == "fill"

    @staticmethod
    def _padding(p) -> tuple[float, float, float, float]:
        if p is None:
            return (0.0, 0.0, 0.0, 0.0)
        if isinstance(p, (int, float)) and not isinstance(p, bool):
            v = float(p)
            return (v, v, v, v)
        if isinstance(p, (list, tuple)):
            vals = [num(v, 0) or 0 for v in p]
            if len(vals) == 4:
                return (vals[0], vals[1], vals[2], vals[3])
            if len(vals) == 2:
                return (vals[0], vals[1], vals[0], vals[1])
            if len(vals) == 1:
                return (vals[0], vals[0], vals[0], vals[0])
        return (0.0, 0.0, 0.0, 0.0)
