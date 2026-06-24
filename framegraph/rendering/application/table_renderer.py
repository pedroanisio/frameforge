"""Table sub-renderer (TableObject / table-flow drawing).

The table-drawing routines extracted from the Renderer (SRP, codebase-standards
§13). Depends on the `RenderContext` port (ADR 0001 slice 3a) — injected as
``self._ctx`` — for the painter and the builder's text/paint/style primitives,
not the concrete Renderer.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import num
from framegraph.rendering.domain.ports import RenderContext
from framegraph.rendering.domain.services.table_layout import resolve_column_widths


class TableRenderer:
    def __init__(self, ctx: "RenderContext"):
        self._ctx = ctx

    def draw(self, o, box):
        p = self._ctx.painter
        x0, y0, w, h = (num(v, 0) for v in box[:4])
        style = self._ctx.style_dict(o.get("style"))
        cols = o.get("columns") or []
        header = o.get("header")
        rows = o.get("rows") or []
        visual = ([("h", header)] if header else []) + [("b", r) for r in rows]
        nrow = max(1, len(visual))
        ncol = max(1, len(cols) or (max((len(r) for _, r in visual), default=1)))
        cw = resolve_column_widths(cols, ncol, w)
        colx = [x0 + sum(cw[:k]) for k in range(ncol)]
        rh = h / nrow                          # nominal row height (font sizing + even fallback)
        # Honour the v2 row_height / header_height fields; else split evenly. The
        # even case keeps total_h == h exactly so untouched tables stay byte-identical.
        rh_body = num(o.get("row_height"), None)
        rh_head = num(o.get("header_height"), None)
        if rh_body is None and rh_head is None:
            heights, total_h = [rh] * nrow, h
        else:
            heights = [(rh_head if (kind == "h" and rh_head is not None)
                        else rh_body if rh_body is not None else rh)
                       for kind, _ in visual]
            total_h = sum(heights)
        rowy = [y0 + sum(heights[:i]) for i in range(nrow)]
        grid_stroke = self._ctx.shape_stroke(o, style) or ' stroke="#bbb"'
        header_fill = self._ctx.paint(style.get("header_fill")) if "header_fill" in style else "#3b6ea5"
        padding = max(0, num(o.get("cell_padding"), 4) or 0)
        out = [p.rect(x0, y0, w, total_h, "white", grid_stroke)]
        st_h = {"family": "sans-serif", "size": min(13, rh * 0.5), "weight": "bold",
                "italic": False, "color": "#fff", "align": "left", "lh": 1.2}
        st_c = {**st_h, "weight": "normal", "color": "#222"}
        if style.get("header_text"):
            st_h = {**st_h, **self._ctx.text_style(style.get("header_text"))}
        if style.get("cell_text"):
            st_c = {**st_c, **self._ctx.text_style(style.get("cell_text"))}
        for ri, (kind, row) in enumerate(visual):
            ry, row_h = rowy[ri], heights[ri]
            if kind == "h":
                out.append(p.rect(x0, ry, w, row_h, header_fill, ""))
            elif o.get("zebra") and (ri % 2):
                out.append(p.rect(x0, ry, w, row_h, "#f4f6f9", ""))
            for ci in range(ncol):
                cell = row[ci] if ci < len(row) else ""
                txt = cell.get("content", "") if isinstance(cell, dict) else ("" if cell is None else str(cell))
                col = cols[ci] if ci < len(cols) and isinstance(cols[ci], dict) else {}
                st = st_h if kind == "h" else st_c
                if col.get("align"):
                    st = {**st, "align": col.get("align")}
                out.append(self.cell_text(colx[ci] + padding, ry,
                                           max(0, cw[ci] - 2 * padding), row_h, txt, st))
            out.append(p.line(x0, ry, x0 + w, ry, grid_stroke))
        for cx in colx[1:]:
            out.append(p.line(cx, y0, cx, y0 + total_h, grid_stroke))
        return "".join(out)

    def cell_text(self, x, y, w, h, txt, st):
        """Render a table cell's text: one vcentred line (byte-identical to the
        previous text_tag), or — when it would exceed the cell width — wrapped to
        multiple lines, clamped to the row and clipped to the cell. Uses text_tag
        (no overflow telemetry), so it is neutral to the overflow gate."""
        if txt is None or txt == "":
            return ""
        size, lh = st["size"], st.get("lh", 1.2)
        avg = st.get("avg") or 0.52
        lines = self._ctx.wrap_words(txt, w, size, avg, st) if w > 0 else [txt]
        if len(lines) <= 1:
            return self._ctx.painter.text_tag(x, y, w, h, txt, st, vcenter=True)
        cap = max(1, int(h / (size * lh))) if (h > 0 and size > 0) else len(lines)
        lines = lines[:cap]
        top = y + max(0, (h - len(lines) * size * lh) / 2)
        body = "".join(
            self._ctx.painter.text_tag(x, top + i * size * lh, w, size * lh, ln, st, vcenter=False)
            for i, ln in enumerate(lines))
        return self._ctx.painter.clip_wrap(body, self._ctx.painter.clip_rect(x, y, w, h))

    # ---- page / flow ------------------------------------------------------- #
