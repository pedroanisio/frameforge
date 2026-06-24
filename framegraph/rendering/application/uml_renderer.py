"""UML / annotation-glyph sub-renderer (the out-of-core "UML zoo").

Drawing routines for the out-of-core-profile UML object family — class boxes,
lifelines, activation bars, actors, legends, chip rows, marker glyphs —
extracted from the Renderer (SRP, codebase-standards.md §13) to keep this niche
surface out of the core orchestrator.

These routines need the rendering context (the painter and the builder's
shape/text primitives), so they depend on the `RenderContext` port (ADR 0001
slice 3a) — a named, mockable contract injected as ``self._ctx`` — rather than
reaching into the concrete Renderer.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import esc, fnum, is_point, num
from framegraph.rendering.domain.ports import RenderContext


class UmlRenderer:
    def __init__(self, ctx: "RenderContext"):
        self._ctx = ctx

    def box(self, o, style, fill):
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            self._ctx.note_skip()
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        p = self._ctx.painter
        fill = fill if fill not in (None, "") else "#fff"
        stroke = self._ctx.shape_stroke(o, style) or ' stroke="#777" stroke-width="1"'
        radius = 10 if o.get("type") == "uml.action" else self._ctx.shape_radius(o, style)
        out = [p.rect(x, y, w, h, fill, stroke, radius=radius)]

        title_rows = []
        stereotype = o.get("stereotype")
        if stereotype:
            title_rows.append(f"<<{stereotype}>>")
        if o.get("kind") and o.get("type") == "uml.node_box":
            title_rows.append(f"<<{o.get('kind')}>>")
        title_rows.append(str(o.get("name") or o.get("label") or o.get("id") or o.get("type")))

        base = {"family": "sans-serif", "size": 11, "weight": "normal",
                "italic": False, "color": "#222", "align": "center", "lh": 1.1}
        cy = y + 5
        for i, text in enumerate(title_rows):
            st = {**base, "size": 10 if text.startswith("<<") else 12,
                  "weight": "bold" if i == len(title_rows) - 1 else "normal",
                  "italic": bool(o.get("abstract")) and i == len(title_rows) - 1}
            row_h = st["size"] * 1.35
            out.append(p.text_tag(x + 5, cy, max(1, w - 10), row_h,
                                  self._ctx.ellipsize(text, max(1, w - 10), st["size"], 0.58),
                                  st, vcenter=True))
            cy += row_h

        def add_separator():
            out.append(p.line(x, cy + 3, x + w, cy + 3, ' stroke="#999" stroke-width="1"'))

        def add_body_rows(rows):
            nonlocal cy
            if not rows:
                return
            add_separator()
            cy += 7
            row_st = {**base, "size": 10, "align": "left", "lh": 1.05}
            for row in rows:
                if cy + row_st["size"] * 1.3 > y + h - 3:
                    break
                out.append(p.text_tag(x + 7, cy, max(1, w - 14), row_st["size"] * 1.25,
                                      self._ctx.ellipsize(row, max(1, w - 14), row_st["size"], 0.55),
                                      row_st, vcenter=False))
                cy += row_st["size"] * 1.25

        add_body_rows(self.box_attribute_rows(o))
        add_body_rows(self.box_operation_rows(o))
        return p.group("".join(out))

    def box_attribute_rows(self, o):
        t = o.get("type")
        if t == "uml.state_box":
            rows = []
            if o.get("entry"):
                rows.append(f"entry / {o.get('entry')}")
            if o.get("do"):
                rows.append(f"do / {o.get('do')}")
            return rows
        if t == "uml.component_box":
            rows = []
            provided = o.get("provided_interfaces") or []
            required = o.get("required_interfaces") or []
            if provided:
                rows.append("provides: " + ", ".join(map(str, provided)))
            if required:
                rows.append("requires: " + ", ".join(map(str, required)))
            return rows
        attrs = o.get("attributes") or []
        rows = []
        for attr in attrs:
            if not isinstance(attr, dict):
                rows.append(str(attr))
                continue
            prefix = attr.get("visibility") or ""
            name = attr.get("name") or attr.get("label") or ""
            typ = attr.get("type")
            mult = attr.get("multiplicity")
            default = attr.get("default")
            row = f"{prefix}{name}"
            if typ:
                row += f": {typ}"
            if mult:
                row += f" [{mult}]"
            if default is not None:
                row += f" = {default}"
            if attr.get("readonly"):
                row += " {readOnly}"
            rows.append(row)
        return rows

    def box_operation_rows(self, o):
        ops = o.get("operations") or []
        rows = []
        for op in ops:
            if not isinstance(op, dict):
                rows.append(str(op))
                continue
            prefix = op.get("visibility") or ""
            name = op.get("name") or op.get("label") or ""
            params = op.get("params") or op.get("parameters") or []
            if isinstance(params, list):
                params = ", ".join(p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in params)
            ret = op.get("return_type") or op.get("returns")
            row = f"{prefix}{name}({params})"
            if ret:
                row += f": {ret}"
            rows.append(row)
        return rows

    def lifeline(self, o, style):
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            self._ctx.note_skip()
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        head_h = max(18, min(h, num(o.get("head_height"), 42) or 42))
        p = self._ctx.painter
        stroke = self._ctx.shape_stroke(o, style) or ' stroke="#555" stroke-width="1"'
        fill = self._ctx.shape_fill(o, style) or "#fff"
        cx = x + w / 2
        out = [
            p.rect(x, y, w, head_h, fill, stroke, radius=self._ctx.shape_radius(o, style)),
            p.line(cx, y + head_h, cx, y + h, ' stroke="#555" stroke-width="1" stroke-dasharray="5 5"'),
        ]
        if o.get("actor"):
            out.extend(self.actor_glyph(cx, y + head_h / 2 - 2, min(18, head_h * 0.42), "#333"))
        label_x = x + (22 if o.get("actor") else 5)
        label_w = max(1, w - (27 if o.get("actor") else 10))
        st = {"family": "sans-serif", "size": 11, "weight": "bold",
              "italic": False, "color": "#222", "align": "center", "lh": 1.1}
        rows = [str(o.get("name") or o.get("id") or "")]
        if o.get("type_name"):
            rows.append(str(o.get("type_name")))
        row_h = min(head_h / max(1, len(rows)), 15)
        start_y = y + max(3, (head_h - row_h * len(rows)) / 2)
        for i, row in enumerate(rows):
            row_st = {**st, "size": 10 if i else 11, "weight": "normal" if i else "bold"}
            out.append(p.text_tag(label_x, start_y + i * row_h, label_w, row_h,
                                  self._ctx.ellipsize(row, label_w, row_st["size"], 0.56),
                                  row_st, vcenter=True))
        return p.group("".join(out))

    def actor_glyph(self, cx, cy, size, color):
        p = self._ctx.painter
        r = size * 0.22
        head_y = cy - size * 0.42
        body_top = cy - size * 0.16
        body_bottom = cy + size * 0.32
        arm_y = cy + size * 0.02
        stroke = f' stroke="{esc(color)}" stroke-width="1.1" fill="none"'
        return [
            p.circle(cx, head_y, r, "none", f' stroke="{esc(color)}" stroke-width="1.1"'),
            p.line(cx, body_top, cx, body_bottom, stroke),
            p.line(cx - size * 0.32, arm_y, cx + size * 0.32, arm_y, stroke),
            p.line(cx, body_bottom, cx - size * 0.28, cy + size * 0.62, stroke),
            p.line(cx, body_bottom, cx + size * 0.28, cy + size * 0.62, stroke),
        ]

    def activation_bar(self, o, style, fill):
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            self._ctx.note_skip()
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        fill = fill if fill not in (None, "") else "#fff"
        stroke = self._ctx.shape_stroke(o, style) or ' stroke="#555" stroke-width="1"'
        return self._ctx.painter.rect(x, y, w, h, fill, stroke)

    def glyph_box(self, o, style):
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            self._ctx.note_skip()
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        t = o.get("type")
        p = self._ctx.painter
        color = self._ctx.color(o.get("color") or o.get("stroke") or "ink") or "#222"
        stroke = self._ctx.shape_stroke(o, style) or f' stroke="{esc(color)}" stroke-width="1.2"'
        cx, cy = x + w / 2, y + h / 2
        out = []
        if t == "uml.actor":
            out.extend(self.actor_glyph(cx, y + h * 0.42, min(w * 0.62, h * 0.55), color))
            name = o.get("name")
            if name:
                st = {"family": "sans-serif", "size": 10, "weight": "normal",
                      "italic": False, "color": color, "align": "center", "lh": 1.0}
                out.append(p.text_tag(x, y + h - 18, w, 14, str(name), st, vcenter=True))
        elif t == "uml.lollipop":
            r = max(2, min(w, h) / 2 - 2)
            out.append(p.circle(cx, cy, r, "#fff", stroke))
            if o.get("name"):
                st = {"family": "sans-serif", "size": 9, "weight": "normal",
                      "italic": False, "color": color, "align": "center", "lh": 1.0}
                out.append(p.text_tag(x, y + h, max(w, 48), 12, str(o.get("name")), st, vcenter=True))
        elif t == "uml.socket":
            r = max(2, min(w, h) / 2 - 2)
            d = f"M {fnum(cx + r)} {fnum(cy - r)} A {fnum(r)} {fnum(r)} 0 0 0 {fnum(cx + r)} {fnum(cy + r)}"
            out.append(p.path(d, "none", stroke))
            if o.get("name"):
                st = {"family": "sans-serif", "size": 9, "weight": "normal",
                      "italic": False, "color": color, "align": "center", "lh": 1.0}
                out.append(p.text_tag(x - max(w, 48), y + h, max(w, 64), 12, str(o.get("name")), st, vcenter=True))
        else:
            kind = o.get("kind")
            if kind == "decision":
                pts = f"{fnum(cx)},{fnum(y)} {fnum(x + w)},{fnum(cy)} {fnum(cx)},{fnum(y + h)} {fnum(x)},{fnum(cy)}"
                out.append(p.poly("polygon", pts, "#fff", stroke))
                if o.get("name"):
                    st = {"family": "sans-serif", "size": 10, "weight": "normal",
                          "italic": False, "color": color, "align": "center", "lh": 1.0}
                    out.append(p.text_tag(x + 4, y + h / 2 - 6, max(1, w - 8), 12, str(o.get("name")), st, vcenter=True))
            elif kind == "final":
                r = max(2, min(w, h) / 2 - 1)
                out.append(p.circle(cx, cy, r, "none", stroke))
                out.append(p.circle(cx, cy, max(1, r - 4), color, ""))
            else:
                r = max(2, min(w, h) / 2 - 1)
                out.append(p.circle(cx, cy, r, color, stroke))
        return p.group("".join(out))

    def legend(self, o):
        out = []
        for item in o.get("items") or []:
            if not isinstance(item, dict):
                continue
            sample = item.get("sample")
            if isinstance(sample, dict):
                sample_obj = dict(sample)
                if sample_obj.get("type") == "rounded_rect":
                    sample_obj["type"] = "rect"
                out.append(self._ctx.obj(sample_obj))
            label = item.get("label")
            if isinstance(label, dict) and isinstance(label.get("box"), list):
                bx = label["box"]
                out.append(self._ctx.render_text(num(bx[0], 0), num(bx[1], 0), num(bx[2], 0), num(bx[3], 0),
                                            label.get("text", ""), self._ctx.text_style(label.get("style"))))
        return self._ctx.painter.group("".join(out))

    def chip_row(self, o):
        origin = o.get("origin") or o.get("position")
        if not is_point(origin):
            self._ctx.note_skip()
            return ""
        p = self._ctx.painter
        x, y = num(origin[0], 0), num(origin[1], 0)
        gap = num(o.get("gap"), 6) or 0
        height = num(o.get("height"), 18) or 18
        fill = self._ctx.color(o.get("fill") or "paper") or "#fff"
        stroke = self._ctx.color(o.get("stroke") or "rule") or "#d0d0d0"
        color = self._ctx.color(o.get("color") or "text_muted") or "#555"
        st = {"family": "sans-serif", "size": max(9, min(12, height - 5)), "weight": "normal",
              "italic": False, "color": color, "align": "center", "lh": 1.0}
        out = []
        cursor = x
        for item in o.get("items") or []:
            if not isinstance(item, dict):
                item = {"text": str(item)}
            text = item.get("text") or item.get("label") or ""
            width = num(item.get("width"), None)
            if width is None:
                width = max(height * 1.6, self._ctx.measure(text, st["size"], 0.58) + 14)
            item_fill = self._ctx.color(item.get("fill")) or fill
            item_stroke = self._ctx.color(item.get("stroke")) or stroke
            item_color = self._ctx.color(item.get("color")) or color
            item_st = {**st, "color": item_color}
            out.append(p.rect(cursor, y, width, height, item_fill,
                              f' stroke="{esc(item_stroke)}" stroke-width="1"', radius=height / 2))
            out.append(p.text_tag(cursor, y, width, height, text, item_st, vcenter=True))
            cursor += width + gap
        return p.group("".join(out)) if out else ""

    def marker_glyph(self, o):
        pos = o.get("position") or o.get("origin")
        if not is_point(pos):
            self._ctx.note_skip()
            return ""
        size = num(o.get("size"), None)
        if size is None:
            meta = o.get("meta") if isinstance(o.get("meta"), dict) else {}
            migration = meta.get("_fg1_migration") if isinstance(meta.get("_fg1_migration"), dict) else {}
            size = num(migration.get("size"), 12) or 12
        x, y = num(pos[0], 0), num(pos[1], 0)
        half = size / 2
        color = self._ctx.color(o.get("color") or o.get("stroke") or "ink") or "#111"
        fill = color if "filled" in str(o.get("kind") or "") else "none"
        points = (
            f"{fnum(x)},{fnum(y - half)} {fnum(x + half)},{fnum(y)} "
            f"{fnum(x)},{fnum(y + half)} {fnum(x - half)},{fnum(y)}"
        )
        return self._ctx.painter.poly("polygon", points, fill,
                                  f' stroke="{esc(color)}" stroke-width="1.4"')
