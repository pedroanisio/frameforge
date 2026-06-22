"""LayoutEngine — arrange a group's children for `Group.layout` (pure).

Ported from the legacy renderer's `_layout_stack` / `_layout_grid`
(framegraph/renderers/layout.py) and adapted to the v2 `Layout` model
(models L359: kind row/column/grid/free, gap/row_gap/column_gap, padding Box,
columns, align). The proxy previously ignored `Layout` entirely — children of a
row/column/grid group rendered at their authored boxes, so children authored at
(0,0) (the common case, e.g. the wordle tile rows) overlapped.

`arrange` returns a local-frame top-left (x, y) for each child (relative to the
group's own origin, matching how the builder renders children inside the group's
translate). It **repositions only — it does not resize children**: each child
keeps its authored width/height, so per-box text-fit (and the overflow gate) is
unchanged. That is a deliberate proxy limitation (§13 honest scope): the legacy
grid stretched children to the cell; this packs them at cell origins instead.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import num


class LayoutEngine:
    def arrange(self, width: float, height: float, children, layout) -> list[tuple[float, float]]:
        """Return one (x, y) per child in the group's local frame.

        Only `kind` in {row, column, grid} arranges; anything else returns the
        children's own origins (i.e. leaves them in place)."""
        kind = layout.get("kind")
        sizes = [self._size(c) for c in children]
        if kind not in ("row", "column", "grid"):
            return [self._origin(c) for c in children]

        pad_t, pad_r, pad_b, pad_l = self._padding(layout.get("padding"))
        x0, y0 = pad_l, pad_t
        avail_w = max(0.0, width - pad_l - pad_r)
        avail_h = max(0.0, height - pad_t - pad_b)
        gap = num(layout.get("gap"), 0) or 0
        col_gap = num(layout.get("column_gap"), gap)
        row_gap = num(layout.get("row_gap"), gap)
        align = layout.get("align") or "start"

        out: list[tuple[float, float]] = []
        if kind == "row":
            x = x0
            for cw, ch in sizes:
                out.append((x, self._cross(y0, avail_h, ch, align)))
                x += cw + col_gap
        elif kind == "column":
            y = y0
            for cw, ch in sizes:
                out.append((self._cross(x0, avail_w, cw, align), y))
                y += ch + row_gap
        else:  # grid: left-to-right, top-to-bottom into `columns` columns
            columns = max(1, int(num(layout.get("columns"), 1) or 1))
            rows = max(1, (len(children) + columns - 1) // columns)
            cell_w = max(0.0, (avail_w - (columns - 1) * col_gap) / columns)
            cell_h = max(0.0, (avail_h - (rows - 1) * row_gap) / rows)
            for i, _ in enumerate(sizes):
                col, row = i % columns, i // columns
                out.append((x0 + col * (cell_w + col_gap), y0 + row * (cell_h + row_gap)))
        return out

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
        return start                      # start / stretch (proxy does not resize)

    @staticmethod
    def _padding(p) -> tuple[float, float, float, float]:
        if p is None:
            return (0.0, 0.0, 0.0, 0.0)
        if isinstance(p, (int, float)) and not isinstance(p, bool):
            v = float(p)
            return (v, v, v, v)
        if isinstance(p, (list, tuple)):
            vals = [num(v, 0) or 0 for v in p]
            if len(vals) == 4:                       # CSS order: top, right, bottom, left
                return (vals[0], vals[1], vals[2], vals[3])
            if len(vals) == 2:                       # [vertical, horizontal]
                return (vals[0], vals[1], vals[0], vals[1])
            if len(vals) == 1:
                return (vals[0], vals[0], vals[0], vals[0])
        return (0.0, 0.0, 0.0, 0.0)
