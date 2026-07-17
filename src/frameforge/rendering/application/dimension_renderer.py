"""Dimension-annotation sub-renderer (P3 §3.10 composite dimensions).

Drawing routines for `dimension` objects — linear / aligned / angular / radial /
diameter callouts with extension lines, arrows, and a measured label — extracted
from the Renderer (SRP, codebase-standards.md §13).

Like UmlRenderer these are context-dependent drawing routines (they use the
painter and the builder's stroke/text primitives), so they depend on the
`RenderContext` port (ADR 0001 slice 3a) — a named, mockable contract injected
as ``self._ctx`` — rather than reaching into the concrete Renderer.
"""
from __future__ import annotations

import math

from frameforge.rendering.domain.geometry import fnum, is_point, num
from frameforge.rendering.domain.ports import RenderContext
from frameforge.rendering.domain.services.stroke_resolver import Stroke


class DimensionRenderer:
    def __init__(self, ctx: "RenderContext"):
        self._ctx = ctx

    def draw(self, o, style):
        kind = o.get("kind")
        fr = self.point_anchor(o.get("from"))
        to = self.point_anchor(o.get("to"))
        if fr is None or to is None:
            self._ctx.note_skip()
            return ""
        if kind in ("radial", "diameter"):
            return self.radial(o, style, fr, to, diameter=kind == "diameter")
        if kind not in ("linear", "aligned"):
            self._ctx.note_skip()
            return ""
        return self.linear(o, style, fr, to)

    @staticmethod
    def point_anchor(anchor):
        if is_point(anchor):
            return num(anchor[0], 0), num(anchor[1], 0)
        return None

    def stroke(self, o, style):
        return self._ctx.shape_stroke(o, style) or Stroke(color="#000", width=1)

    def arrows(self, o, start=True, end=True):
        arrows = o.get("arrows") or "both"
        if arrows == "none":
            start = end = False
        elif arrows == "first":
            end = False
        elif arrows == "second":
            start = False
        elif arrows != "both":
            start = end = False
        if not (start or end):
            return None
        marker_o = dict(o)
        ssv = o.get("stroke_style")
        bundle = dict(self._ctx.stroke_styles.get(ssv) or {}) if isinstance(ssv, str) else dict(ssv or {})
        if start:
            bundle["arrow_start"] = bundle.get("arrow_start") or True
        if end:
            bundle["arrow_end"] = bundle.get("arrow_end") or True
        marker_o["stroke_style"] = bundle
        marker_o["stroke"] = marker_o.get("stroke") or bundle.get("stroke") or bundle.get("color") or "#000"
        return self._ctx.arrow_markers(marker_o)

    def label(self, o, distance):
        if o.get("text") is not None:
            return str(o.get("text"))
        value = o.get("value")
        measured = distance if value in (None, "auto") else num(value, distance)
        label = fnum(measured)
        return f"{o.get('prefix') or ''}{label}{o.get('suffix') or ''}"

    def text(self, o):
        st = self._ctx.text_style(o.get("text_style") or o.get("style"))
        return {**st, "align": "center"}

    def linear(self, o, style, fr, to):
        x1, y1 = fr
        x2, y2 = to
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist <= 0:
            return ""
        off = num(o.get("offset"), 12) or 0
        nx, ny = -dy / dist, dx / dist
        ax, ay = x1 + nx * off, y1 + ny * off
        bx, by = x2 + nx * off, y2 + ny * off
        stroke = self.stroke(o, style)
        body = [
            self._ctx.painter.line(x1, y1, ax, ay, stroke),
            self._ctx.painter.line(x2, y2, bx, by, stroke),
            self._ctx.painter.line(ax, ay, bx, by, stroke, markers=self.arrows(o)),
        ]
        label = self.label(o, dist)
        st = self.text(o)
        midx, midy = (ax + bx) / 2, (ay + by) / 2
        body.append(self._ctx.painter.text_tag(midx - 40, midy - st["size"] * 0.7, 80, st["size"] * 1.4, label, st, vcenter=True))
        return self._ctx.painter.group("".join(body))

    def radial(self, o, style, fr, to, diameter=False):
        px, py = fr
        cx, cy = to
        dx, dy = px - cx, py - cy
        radius = math.hypot(dx, dy)
        if radius <= 0:
            return ""
        if diameter:
            ax, ay = cx - dx, cy - dy
            bx, by = px, py
            distance = radius * 2
        else:
            ax, ay = cx, cy
            bx, by = px, py
            distance = radius
        stroke = self.stroke(o, style)
        label = self.label(o, distance)
        st = self.text(o)
        midx, midy = (ax + bx) / 2, (ay + by) / 2
        return self._ctx.painter.group(
            self._ctx.painter.line(ax, ay, bx, by, stroke, markers=self.arrows(o, start=diameter, end=True))
            + self._ctx.painter.text_tag(midx - 40, midy - st["size"] * 1.5, 80, st["size"] * 1.4, label, st, vcenter=True)
        )
