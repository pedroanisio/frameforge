"""Application-layer rendering orchestrator (the `Renderer` use-case).

Turns a FrameGraph document (a plain dict, already YAML/JSON-parsed) into the
per-page SVG output, by walking it in z-order and driving the domain resolvers
(colour/paint/stroke/effect/text-style/canvas), the layout engine, and the
`SvgPainter` adapter. Relocated out of the monolithic `tooling/render_fixtures.py`
(DDD step: populate the application layer); behaviour and byte output are
unchanged.

Decomposition in progress (codebase-standards.md §13): text fitting, CSS/SVG
value building, and math->SVG rendering are extracted to injected services
(`TextFitter`, `StyleValues`, `MathSvgRenderer`). The remaining concrete
infrastructure coupling is the directly-constructed `SvgPainter`, slated to
become backend-neutral. `tooling/render_fixtures.py` re-exports `Renderer` for
backward compatibility.
"""
from __future__ import annotations

import copy
import math
import os
import re

from framegraph.rendering.domain.geometry import (
    fnum, is_point, num,
)
from framegraph.rendering.domain.services.canvas_resolver import CanvasResolver
from framegraph.rendering.domain.services.paint_resolver import ColorResolver
from framegraph.rendering.domain.services.effect_resolver import EffectResolver
from framegraph.rendering.domain.services.stroke_resolver import Markers, Stroke, StrokeResolver
from framegraph.rendering.domain.services.layout_engine import LayoutEngine
from framegraph.rendering.domain.services.table_layout import resolve_column_widths
from framegraph.rendering.domain.services.math_text import math_text
from framegraph.rendering.domain.services.style_values import StyleValues
from framegraph.rendering.domain.services.text_fitter import TextFitter
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver
from framegraph.rendering.application.dimension_renderer import DimensionRenderer
from framegraph.rendering.application.render_context import RendererContext
from framegraph.rendering.application.table_renderer import TableRenderer
from framegraph.rendering.application.uml_renderer import UmlRenderer
from framegraph.rendering.infrastructure.math_svg import MathSvgRenderer
from framegraph.rendering.infrastructure.painters.svg import SvgPainter


# --------------------------------------------------------------------------- #
#  the renderer                                                               #
# --------------------------------------------------------------------------- #
class Renderer:

    def __init__(self, doc, base_dir, *, real_metrics=False):
        self.doc = doc if isinstance(doc, dict) else {}
        self.base_dir = base_dir
        # Opt-in: when True (and fontTools resolves the family) text width comes
        # from real glyph advances instead of the per-char `avg` estimate. OFF by
        # default so render_page()/golden output stays byte-identical (§8).
        self.real_metrics = bool(real_metrics)
        # Text fitting (measure/wrap/ellipsize) is a domain service; inject the
        # infra font-metrics provider only when real_metrics is on (estimate mode
        # otherwise), keeping the domain free of the infra import.
        if self.real_metrics:
            from framegraph.rendering.infrastructure.font_metrics import get_font_metrics
            self._fit = TextFitter(get_font_metrics)
        else:
            self._fit = TextFitter(None)
        defs = self.doc.get("defs") or {}
        tok = defs.get("tokens") or {}
        self.colors = tok.get("colors") or {}
        self.text_styles = tok.get("text_styles") or {}
        self.styles = tok.get("styles") or {}
        self.stroke_styles = tok.get("stroke_styles") or {}
        self.assets = defs.get("assets") or {}
        self.masters = defs.get("masters") or {}
        self.doc_contract = self.doc.get("text_contract") or {}
        self.contract = {}       # effective per-page text contract (set in render_page)
        self.skipped = 0
        # text-fit telemetry (asserted by --check-overflow)
        self.tstats = dict(total=0, naive_overflow=0, shrunk=0, wrapped=0,
                           clipped=0, contained=0, visible_overflow=0, uncontained=0)
        # ---- domain resolvers + SVG painter (DDD steps 3–4) ----------------- #
        # Token/style/canvas resolution are pure domain services. ALL SVG string
        # construction + the per-page <defs>/gradient-id state now lives in the
        # SvgPainter (a ScenePainter adapter); this Renderer is the *builder*
        # that walks the document in z-order and emits via the painter. The
        # stroke resolver is handed `self.paint` so a gradient stroke still
        # allocates its <defs> entry in document order (byte-identical ids).
        self._color = ColorResolver(self.colors)
        self._painter = SvgPainter(self._color)
        self._text_style = TextStyleResolver(self.text_styles, self.styles, self._color)
        self._canvas = CanvasResolver(self.masters)
        self._stroke = StrokeResolver(self.stroke_styles, self._color, self.paint)
        self._effect = EffectResolver(self._color)
        self._css = StyleValues(self.color)   # CSS/SVG value builder (filter/shadow/transform)
        self._math = MathSvgRenderer(math_text)   # math -> SVG adapter (node MathJax + fallback)
        self._uml = UmlRenderer(RendererContext(self))   # out-of-core UML sub-renderer
        self._dim = DimensionRenderer(RendererContext(self))   # dimension-annotation sub-renderer
        self._table_r = TableRenderer(RendererContext(self))   # table sub-renderer
        self._layout = LayoutEngine()
        self._object_index = {}

    # ---- colour / paint ---------------------------------------------------- #
    def color(self, c, depth=0):
        return self._color.resolve(c, depth)

    def paint(self, p, depth=0):
        """Return an SVG fill/stroke value: a colour, 'none', or url(#grad).

        Gradient *emission* (the <defs> entry + id) lives on the painter now;
        this routes a gradient paint to it and a colour to the resolver."""
        if isinstance(p, dict) and p.get("stops") and p.get("kind") in ("linear", "radial", "conic"):
            return self._painter.gradient(p)
        return self.color(p, depth)

    # ---- stroke (HEAD P3: paint in `stroke`, geometry in `stroke_style`) --- #
    def stroke(self, o):
        return self._stroke.fields(o)

    def _arrow_markers(self, o):
        """Resolve an open shape's arrowheads to a neutral `Markers` (or None).

        Reads `arrow_start`/`arrow_end` off the resolved `stroke_style`; the backend
        draws/registers its own arrowheads from the returned value object. Additive:
        returns None unless the stroke requests an arrow."""
        spec = self._stroke.arrow_spec(o)
        if not spec:
            return None
        return Markers(color=spec["color"], start=spec["start"], end=spec["end"])

    # ---- text style resolution -------------------------------------------- #
    def text_style(self, ref):
        return self._text_style.resolve(ref)

    # ---- text measurement / fitting --------------------------------------- #
    # Default path: a per-character `avg` estimate (no font metrics). When the
    # `real_metrics` opt-in is set AND fontTools resolves the family, width is
    # taken from real glyph advances instead. The opt-in is OFF by default, so
    # the estimate path below is reached unchanged and output is byte-identical.
    # Text fitting is delegated to the TextFitter domain service (SRP). These
    # thin wrappers preserve the call sites and the tested `Renderer.measure`/
    # `wrap_words` surface (tests/test_font_metrics.py).
    def measure(self, s, size, avg, st=None):
        return self._fit.measure(s, size, avg, st)

    def wrap_words(self, text, w, size, avg, st=None):
        return self._fit.wrap_words(text, w, size, avg, st)

    def ellipsize(self, s, w, size, avg, st=None):
        return self._fit.ellipsize(s, w, size, avg, st)

    # anchor() / text_tag() / clip_rect() emission moved to the SvgPainter
    # (step 4); the builder calls self._painter.* for them.

    def _span_runs(self, spans, base_st, size):
        """Resolve `text.spans` to (text, run_style) pairs for one styled line.

        Mirrors the flatten used for fit (str | dict's `text`), so the run texts
        concatenate to the fitted line; each run's style comes from the span's own
        `style` (else the base), rendered at the fitted size."""
        runs = []
        for sp in spans:
            if isinstance(sp, dict):
                if sp.get("kind") == "math" and (sp.get("tex") is not None or sp.get("latex") is not None):
                    text = math_text(sp.get("tex") if sp.get("tex") is not None else sp.get("latex"))
                else:
                    text = sp.get("text", "")
                sty = self.text_style(sp["style"]) if sp.get("style") else base_st
            else:
                text, sty = (sp if isinstance(sp, str) else str(sp)), base_st
            text = self._transform_text(str(text), base_st.get("text_transform"))
            runs.append((text, self._painter.font_style(sty, size)))
        return runs

    def render_text(self, x, y, w, h, content, st, spans=None):
        """Render a text object honouring the FrameGraph text-fit contract:
        wrap-to-box (default), `shrink_to_fit` (down to min_font_size), `clip`/
        `hidden`, `text_overflow: ellipsis`, `line_clamp`/`max_lines`, plus a
        hard clip-path safety net so contained text can never spill its box."""
        self.tstats["total"] += 1
        if content is None or content == "":
            return ""
        content = self._transform_text(str(content), st.get("text_transform"))
        size, avg, lh = st["size"], st["avg"], st["lh"]
        # Default unspecified text to `clip`: no fixture ever requests `visible`,
        # and an authoring box is a containment constraint, so the proxy contains
        # by default (wrap first, then clip the remainder) rather than spilling.
        overflow = st["overflow"] or self.contract.get("overflow") or "clip"
        min_fs = st["min_font_size"] or num(self.contract.get("min_font_size")) or size * 0.5
        text_ovf = st["text_overflow"] or self.contract.get("text_overflow")
        max_lines = st["max_lines"] or self.contract.get("line_clamp")
        do_wrap = w > 0 and not st["nowrap"]
        contained_policy = overflow in ("clip", "hidden", "scroll", "auto", "shrink_to_fit")

        # would the naive (single-line, no fit) render have spilled? (the reported bug)
        if self.measure(content, size, avg, st) > w + 0.5 or size * lh > h + 0.5:
            self.tstats["naive_overflow"] += 1

        def layout(sz):
            return self.wrap_words(content, w, sz, avg, st) if do_wrap else [content]

        lines = layout(size)
        if len(lines) > 1:
            self.tstats["wrapped"] += 1
        if overflow == "shrink_to_fit":
            start = size
            while size > min_fs:
                lines = layout(size)
                too_tall = len(lines) * size * lh > h + 0.5
                too_wide = max((self.measure(ln, size, avg, st) for ln in lines), default=0) > w + 0.5
                if not too_tall and not too_wide:
                    break
                size = max(min_fs, size - 1)
            lines = layout(size)
            if size < start:
                self.tstats["shrunk"] += 1

        clipped = False
        # clamp number of lines to box height (non-visible policies) and/or max_lines
        caps = [n for n in (max_lines, (int(h // (size * lh)) if (h > 0 and contained_policy) else None)) if n]
        cap = min(caps) if caps else None
        if cap is not None and len(lines) > max(1, cap):
            lines = lines[: max(1, cap)]
            clipped = True
            if text_ovf == "ellipsis":
                lines[-1] = self.ellipsize(lines[-1], w, size, avg, st)
        # single unwrapped line wider than the box
        if not do_wrap and self.measure(lines[0], size, avg, st) > w + 0.5:
            if text_ovf == "ellipsis":
                lines[0] = self.ellipsize(lines[0], w, size, avg, st)
            clipped = True

        # vertical placement
        total_h = len(lines) * size * lh
        va = st["valign"]
        if va in ("top", "text-top", "super"):
            top = y
        elif va in ("bottom", "text-bottom", "sub"):
            top = y + max(0, h - total_h)
        elif va in ("middle", "central", "center", "baseline"):
            top = y + max(0, (h - total_h) / 2)
        else:
            top = y if (len(lines) > 1 or h > size * 2.4) else y + max(0, (h - total_h) / 2)
        base = top + size * 0.82

        a = self._painter.anchor(st["align"])
        tx = x + (w / 2 if a == "middle" else (w if a == "end" else 0))
        style = self._painter.font_style(st, size)
        # Rich `text.spans`: when the fitted text is a single, untruncated line,
        # emit per-run styled tspans (the common inline-emphasis case). Wrapped or
        # truncated span text falls back to the flattened single-style line.
        if spans and len(lines) == 1 and lines[0] == content:
            el = self._painter.text_runs(base, a, tx, style, self._span_runs(spans, st, size))
        else:
            el = self._painter.text_block(base, a, style, lines, tx, size * lh)

        # telemetry: is it visually contained?
        widest = max((self.measure(ln, size, avg, st) for ln in lines), default=0)
        fits = widest <= w + 0.5 and len(lines) * size * lh <= h + 0.5
        if contained_policy:
            if clipped or not fits:                  # clip only when something exceeds the box
                self.tstats["clipped"] += 1
                el = self._painter.clip_wrap(el, self._painter.clip_rect(x, y, w, h))
            else:
                self.tstats["contained"] += 1
        elif fits:
            self.tstats["contained"] += 1
        else:
            # explicit overflow:visible long text — permitted to spill, but flagged
            self.tstats["visible_overflow"] += 1
            self.tstats["uncontained"] += 1
        return el

    @staticmethod
    def _transform_text(content, transform):
        if transform == "uppercase":
            return content.upper()
        if transform == "lowercase":
            return content.lower()
        if transform == "capitalize":
            return content.title()
        return content

    def obj(self, o):
        if not isinstance(o, dict):
            return ""
        try:
            inner = self._obj(o)
            if inner:
                inner = self._with_side_borders(o, self._style_dict(o.get("style")), inner)
                inner = self._with_outline(o, self._style_dict(o.get("style")), inner)
                inner = self._with_style_clip(o, self._style_dict(o.get("style")), inner)
                inner = self._with_effects(o, self._style_dict(o.get("style")), inner)
                inner = self._with_transform(o, self._style_dict(o.get("style")), inner)
                inner = self._with_style_compositing(o, self._style_dict(o.get("style")), inner)
            opacity = o.get("opacity")
            if inner and opacity not in (None, 1):
                inner = self._painter.opacity_group(inner, num(opacity, 1))
            return self._painter.a11y_wrap(inner, o)
        except Exception:                              # never let one object kill a page
            self.skipped += 1
            return ""

    def _with_side_borders(self, o, style, svg):
        box = o.get("box")
        if not isinstance(box, list) or len(box) < 4:
            return svg
        x, y, w, h = (num(v, 0) for v in box[:4])
        sides = (
            ("border_top", (x, y, x + w, y)),
            ("border_right", (x + w, y, x + w, y + h)),
            ("border_bottom", (x, y + h, x + w, y + h)),
            ("border_left", (x, y, x, y + h)),
        )
        lines = []
        for key, (x1, y1, x2, y2) in sides:
            border = style.get(key)
            if isinstance(border, dict):
                stroke = self._border_stroke(border)
                if stroke:
                    lines.append(self._painter.line(x1, y1, x2, y2, stroke))
        return svg + "".join(lines)

    def _with_outline(self, o, style, svg):
        outline = style.get("outline")
        box = o.get("box")
        if not isinstance(outline, dict) or not isinstance(box, list) or len(box) < 4:
            return svg
        stroke = self._border_stroke(outline)
        if not stroke:
            return svg
        x, y, w, h = (num(v, 0) for v in box[:4])
        offset = num(style.get("outline_offset"), 0) or 0
        radius = max(0, self._shape_radius(o, style) + offset)
        outline_rect = self._painter.rect(
            x - offset, y - offset, w + 2 * offset, h + 2 * offset, None, stroke, radius=radius
        )
        return svg + outline_rect

    def _with_effects(self, o, style, svg):
        """Wrap an object's SVG in effect filter group(s) if it declares them.

        Additive: emits nothing unless `shadow`/`glow` is present, so effect-free
        fixtures are byte-identical. Object effects wrap before supported style
        effects so authored style filters apply to the fully drawn primitive."""
        for kind in ("glow", "shadow"):
            params = self._effect.resolve(o.get(kind), kind)
            if params is not None:
                svg = self._painter.filter_wrap(svg, self._painter.filter_effect(kind, params))
        for kind, params in self._effect.style_effects(style):
            svg = self._painter.filter_wrap(svg, self._painter.filter_effect(kind, params))
        return svg

    def _with_transform(self, o, style, svg):
        ops = self._css.transform_ops(style.get("transform"), style.get("transform_origin"), o.get("box"))
        return self._painter.transform_group(svg, ops) if ops else svg

    def _with_style_compositing(self, o, style, svg):
        attrs = {}
        visibility = style.get("visibility")
        if visibility in ("hidden", "collapse"):
            attrs["visibility"] = visibility
        blend = style.get("mix_blend_mode")
        if blend and blend != "normal":
            attrs["mix-blend-mode"] = blend
        isolation = style.get("isolation")
        if isolation and isolation != "auto":
            attrs["isolation"] = isolation
        opacity = style.get("opacity")
        if opacity not in (None, 1):
            attrs["opacity"] = fnum(num(opacity, 1))
        clip = style.get("clip_path")
        if isinstance(clip, str) and clip.strip():
            attrs["clip-path"] = clip.strip()
        backdrop = self._css.filter_value(style.get("backdrop_filter"))
        if backdrop:
            attrs["backdrop-filter"] = backdrop
        css_filter = self._css.filter_value(style.get("filter"), svg_only=False)
        if css_filter:
            attrs["filter"] = css_filter
        bg_blend = style.get("background_blend_mode")
        if bg_blend and bg_blend != "normal":
            attrs["background-blend-mode"] = bg_blend
        for key, css_name in (
            ("background_position", "background-position"),
            ("background_repeat", "background-repeat"),
            ("background_clip", "background-clip"),
            ("background_origin", "background-origin"),
        ):
            val = style.get(key)
            if val:
                attrs[css_name] = str(val)
        mask = style.get("mask")
        if isinstance(mask, str) and mask.strip() and mask.strip() != "none":
            attrs["mask"] = mask.strip()
        z_index = style.get("z_index")
        if z_index is not None:
            attrs["z-index"] = str(z_index)
        transform_box = style.get("transform_box")
        if transform_box:
            attrs["transform-box"] = transform_box
        perspective = style.get("perspective")
        if perspective and perspective != "none":
            attrs["perspective"] = self._css.length(perspective)
        # The bounded `css` escape (§8.4) on a non-text object: text emits its css
        # inline via font_style(); shapes carry it on the compositing <g> wrapper.
        css = style.get("css")
        raw = css if (css and o.get("type") != "text") else ""
        return self._painter.style_group(svg, attrs, raw)

    def _with_style_clip(self, o, style, svg):
        clip = style.get("clip_path")
        if not isinstance(clip, dict):
            return svg
        cid = self._style_clip_id(clip, o.get("box"))
        return self._painter.clip_wrap(svg, cid) if cid else svg

    def _style_clip_id(self, clip, box):
        shape = clip.get("shape")
        args = clip.get("args") or {}
        if shape == "inset" and isinstance(box, list) and len(box) >= 4:
            x, y, w, h = (num(v, 0) for v in box[:4])
            if isinstance(args.get("box"), list) and len(args["box"]) >= 4:
                x, y, w, h = (num(v, 0) for v in args["box"][:4])
            else:
                top = num(args.get("top"), 0) or 0
                right = num(args.get("right"), top) or 0
                bottom = num(args.get("bottom"), top) or 0
                left = num(args.get("left"), right) or 0
                x, y, w, h = x + left, y + top, max(0, w - left - right), max(0, h - top - bottom)
            return self._painter.clip_rect(x, y, w, h)
        if shape == "circle":
            center = args.get("center")
            radius = num(args.get("r", args.get("radius")), None)
            if center is None and isinstance(box, list) and len(box) >= 4:
                x, y, w, h = (num(v, 0) for v in box[:4])
                center = [x + w / 2, y + h / 2]
                radius = min(w, h) / 2 if radius is None else radius
            if is_point(center) and radius is not None:
                return self._painter.clip_ellipse(center[0], center[1], radius, radius)
        if shape == "ellipse":
            center = args.get("center")
            rx = num(args.get("rx"), None)
            ry = num(args.get("ry"), None)
            if center is None and isinstance(box, list) and len(box) >= 4:
                x, y, w, h = (num(v, 0) for v in box[:4])
                center = [x + w / 2, y + h / 2]
                rx = w / 2 if rx is None else rx
                ry = h / 2 if ry is None else ry
            if is_point(center) and rx is not None and ry is not None:
                return self._painter.clip_ellipse(center[0], center[1], rx, ry)
        if shape == "polygon":
            pts = [tuple(num(v, 0) for v in pt[:2]) for pt in args.get("points", []) if is_point(pt)]
            return self._painter.clip_polygon(pts) if pts else None
        if shape == "path":
            d = args.get("d")
            if isinstance(d, str) and d.strip():
                return self._painter.clip_path_d(d)
        return None

    def _group_children(self, o):
        """Render a group's children, arranging them when the group declares a
        row/column/grid `layout` (else children keep their authored boxes).

        Arrangement repositions each child via a translate group. Children with
        fill sizing get their direct box extent overridden for this render pass;
        the source document is not mutated. Children render in the group's local
        frame; the group's own box-origin translate is applied by the caller."""
        children = o.get("children") or []
        layout = o.get("layout") or {}
        box = o.get("box")
        if not (layout.get("kind") in ("row", "column", "grid", "wrap")
                and isinstance(box, list) and len(box) >= 4):
            return "".join(self.obj(ch) for ch in children)
        p = self._painter
        positions = self._layout.arrange(num(box[2], 0), num(box[3], 0), children, layout)
        parts = []
        for ch, (tx, ty, tw, th) in zip(children, positions):
            child = self._layout_child(ch, tw, th)
            csvg = self.obj(child)
            if not csvg:
                continue
            cb = ch.get("box") if isinstance(ch, dict) else None
            ox = num(cb[0], 0) or 0 if isinstance(cb, list) and len(cb) >= 2 else 0
            oy = num(cb[1], 0) or 0 if isinstance(cb, list) and len(cb) >= 2 else 0
            dx, dy = tx - ox, ty - oy
            parts.append(p.group(csvg, translate=(dx, dy)) if (dx or dy) else csvg)
        return "".join(parts)

    @staticmethod
    def _layout_child(ch, width, height):
        if not isinstance(ch, dict):
            return ch
        box = ch.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ch
        if (num(box[2], 0), num(box[3], 0)) == (width, height):
            return ch
        child = copy.deepcopy(ch)
        child["box"] = [box[0], box[1], width, height]
        return child

    def _obj(self, o):
        p = self._painter
        t = o.get("type")
        box = o.get("box")
        style = self._style_dict(o.get("style"))
        # Resolve fill up-front for every object (even box-less ones): a gradient
        # fill must allocate its <defs> id here, before stroke, to keep ids stable.
        fill = self._shape_fill(o, style)
        fill_opacity = o.get("fill_opacity", style.get("fill_opacity"))
        fill_rule = o.get("fill_rule", style.get("fill_rule"))

        if t == "rect" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            r = self._shape_radius(o, style)
            return p.rect(x, y, w, h, fill, self._shape_stroke(o, style), radius=r, fill_opacity=fill_opacity)

        if t == "ellipse":
            c = o.get("center") or [0, 0]
            cx, cy = num(c[0], 0), num(c[1], 0)
            rx, ry = num(o.get("rx"), 0), num(o.get("ry"), 0)
            if not rx and box:
                cx, cy, rx, ry = box[0] + box[2] / 2, box[1] + box[3] / 2, box[2] / 2, box[3] / 2
            return p.ellipse(cx, cy, rx, ry, fill, self._shape_stroke(o, style), fill_opacity=fill_opacity)

        if t == "circle":
            c = o.get("center") or [0, 0]
            r = num(o.get("r"), 0)
            return p.circle(num(c[0], 0), num(c[1], 0), r, fill, self._shape_stroke(o, style), fill_opacity=fill_opacity)

        if t == "line":
            fr, to = o.get("from"), o.get("to")
            if is_point(fr) and is_point(to):
                stk = self._shape_stroke(o, style) or Stroke(color="#000", width=1)
                return p.line(fr[0], fr[1], to[0], to[1], stk, markers=self._arrow_markers(o))
            return ""

        if t in ("polyline", "polygon"):
            pts = o.get("points") or []
            ptstr = " ".join(f"{fnum(num(pt[0],0))},{fnum(num(pt[1],0))}" for pt in pts if is_point(pt))
            if not ptstr:
                return ""
            closed = t == "polygon" or o.get("closed")
            tag = "polygon" if closed else "polyline"
            return p.poly(tag, ptstr, fill if closed else None,
                          self._shape_stroke(o, style),
                          fill_opacity=fill_opacity if closed else None,
                          fill_rule=fill_rule if closed else None,
                          markers=self._arrow_markers(o))

        if t == "path":
            d = o.get("d")
            if isinstance(d, list):
                d = " ".join(str(seg[0]) + " " + " ".join(fnum(num(n, 0)) for n in seg[1:])
                             if isinstance(seg, list) else str(seg) for seg in d)
            if not isinstance(d, str) or not d.strip():
                return ""
            return p.path(d, fill, self._shape_stroke(o, style),
                          fill_opacity=fill_opacity, fill_rule=fill_rule,
                          markers=self._arrow_markers(o))

        if t in ("curve", "bezier"):
            fr, to = o.get("from"), o.get("to")
            c1 = o.get("control1") or o.get("c1") or fr
            c2 = o.get("control2") or o.get("c2") or c1
            if not (is_point(fr) and is_point(to) and is_point(c1) and is_point(c2)):
                return ""
            d = (
                f"M {fnum(num(fr[0], 0))} {fnum(num(fr[1], 0))} "
                f"C {fnum(num(c1[0], 0))} {fnum(num(c1[1], 0))} "
                f"{fnum(num(c2[0], 0))} {fnum(num(c2[1], 0))} "
                f"{fnum(num(to[0], 0))} {fnum(num(to[1], 0))}"
            )
            return p.path(d, fill, self._shape_stroke(o, style),
                          fill_opacity=fill_opacity, fill_rule=fill_rule,
                          markers=self._arrow_markers(o))

        if t == "dimension":
            return self._dim.draw(o, style)

        if t == "connector":
            return self._connector(o, style)

        if t == "text" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            content = o.get("text")
            spans = o.get("spans")
            if content is None and spans:
                content = "".join(s if isinstance(s, str) else s.get("text", "")
                                  for s in spans)
            return self.render_text(x, y, w, h, content, self.text_style(o.get("style")), spans=spans)

        if t == "bullet_list" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            st = self.text_style(o.get("style"))
            marker = o.get("marker", "•")
            gap = num(o.get("gap"), None) or st["size"] * 1.5
            mc = self.color(o.get("marker_color")) or st["color"]
            indent = st["size"] * 1.1
            line_h = st["size"] * st["lh"]
            # Wrap each item to the width remaining right of the marker so long
            # items don't run off the box; `nowrap` keeps the legacy single-line
            # behaviour. The text width must stay positive for narrow boxes.
            text_w = max(1.0, w - indent)
            do_wrap = text_w > 0 and not st.get("nowrap")
            out = []
            cy = y + st["size"]
            for it in o.get("items", []):
                txt = it if isinstance(it, str) else (it.get("text", "") if isinstance(it, dict) else str(it))
                lines = self.wrap_words(txt, text_w, st["size"], st["avg"], st) if do_wrap else [txt]
                out.append(p.text_tag(x, cy - st["size"], st["size"] + 4, st["size"] + 4,
                                      marker, {**st, "color": mc}, vcenter=False))
                for i, ln in enumerate(lines):
                    out.append(p.text_tag(x + indent, cy - st["size"] + i * line_h, w, st["size"] + 4,
                                          ln, st, vcenter=False))
                # Advance past every wrapped line, and never less than one line —
                # `gap` is the inter-item pitch (default a comfortable 1.5x), but a
                # too-small authored gap must not let items overlap, so floor the
                # single-line step at the line height.
                cy += max(gap, line_h) + (len(lines) - 1) * line_h
            return "".join(out)

        if t == "chip_row":
            return self._uml.chip_row(o)

        if t == "uml.marker_glyph":
            return self._uml.marker_glyph(o)

        if t == "component" and box:
            return self._component(o, style)

        if t == "container" and box:
            return self._group_children(o)

        if t == "legend" and box:
            return self._uml.legend(o)

        if t in ("uml.actor", "uml.socket", "uml.lollipop", "uml.activity_node", "uml.pseudostate") and box:
            return self._uml.glyph_box(o, style)

        if t == "uml.lifeline" and box:
            return self._uml.lifeline(o, style)

        if t == "uml.activation_bar" and box:
            return self._uml.activation_bar(o, style, fill)

        if t in {
            "uml.classifier_box",
            "uml.component_box",
            "uml.state_box",
            "uml.action",
            "uml.artifact_box",
            "uml.node_box",
        } and box:
            return self._uml.box(o, style, fill)

        if t == "icon" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            col = self.color(o.get("color")) or "#444"
            sz = num(o.get("size"), None) or min(w, h) * 0.8
            st = {"family": "sans-serif", "size": sz, "weight": "normal",
                  "italic": False, "color": col, "align": "center", "lh": 1.2}
            return p.text_tag(x, y, w, h, o.get("glyph", "▢"), st, vcenter=True)

        if t == "image" and box:
            return self._image(o, box)

        if t == "table" and box:
            return self._table_r.draw(o, box)

        if t == "group":
            inner = self._group_children(o)
            bx = o.get("box")
            if is_point(bx[:2]) if isinstance(bx, list) and len(bx) >= 2 else False:
                # only translate when the group declares an origin box (P1 nesting)
                return p.group(inner, translate=(num(bx[0], 0), num(bx[1], 0)))
            return p.group(inner)

        # unknown / out-of-profile object → labelled placeholder iff it has a box
        if box and all(isinstance(v, (int, float)) for v in box[:4]):
            x, y, w, h = box[:4]
            st = {"family": "monospace", "size": 11, "weight": "normal",
                  "italic": True, "color": "#999", "align": "center", "lh": 1.2}
            return (p.rect(x, y, w, h, "#f3f3f3", Stroke(color="#ccc", dash="3 3"))
                    + p.text_tag(x, y, w, h, f"?{t}", st, vcenter=True))
        self.skipped += 1
        return ""

    def _index_objects(self, page):
        index = {}

        def visit(o, offset=(0, 0)):
            if not isinstance(o, dict):
                return
            local = dict(o)
            box = local.get("box")
            if isinstance(box, list) and len(box) >= 4:
                local["box"] = [num(box[0], 0) + offset[0], num(box[1], 0) + offset[1],
                                num(box[2], 0), num(box[3], 0)]
            if local.get("id") and local.get("id") not in index:
                index[local["id"]] = local
            child_offset = offset
            if o.get("type") == "group" and isinstance(box, list) and len(box) >= 2:
                child_offset = (offset[0] + num(box[0], 0), offset[1] + num(box[1], 0))
            for child in o.get("children") or []:
                visit(child, child_offset)

        for layer in page.get("layers") or []:
            for obj in layer.get("objects") or []:
                visit(obj)
        return index

    def _anchor_ref(self, ref):
        if is_point(ref):
            return num(ref[0], 0), num(ref[1], 0)
        if not isinstance(ref, dict):
            return None
        if is_point(ref.get("point")):
            p = ref.get("point")
            return num(p[0], 0), num(p[1], 0)
        obj_id = ref.get("object") or ref.get("ref")
        obj = self._object_index.get(obj_id)
        box = obj.get("box") if isinstance(obj, dict) else None
        if not (isinstance(box, list) and len(box) >= 4):
            return None
        ports = obj.get("ports") or {}
        port = ref.get("port")
        if port in ports and is_point(ports[port]):
            p = ports[port]
            return num(p[0], 0), num(p[1], 0)
        x, y, w, h = (num(v, 0) for v in box[:4])
        side = ref.get("side") or port
        offset = num(ref.get("offset"), 0) or 0
        if side == "north":
            return x + w / 2 + offset, y
        if side == "south":
            return x + w / 2 + offset, y + h
        if side == "east":
            return x + w, y + h / 2 + offset
        if side == "west":
            return x, y + h / 2 + offset
        return x + w / 2, y + h / 2

    def _connector(self, o, style):
        p = self._painter
        start = self._anchor_ref(o.get("from"))
        end = self._anchor_ref(o.get("to"))
        if start is None or end is None:
            self.skipped += 1
            return ""
        route = o.get("route") or {}
        points = route.get("points") if isinstance(route, dict) else None
        pts = [start] + [(num(pt[0], 0), num(pt[1], 0)) for pt in (points or []) if is_point(pt)] + [end]
        stroke = self._shape_stroke(o, style) or Stroke(color="#000", width=1)
        markers = self._arrow_markers(o)
        if len(pts) == 2:
            body = p.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1], stroke, markers=markers)
        else:
            ptstr = " ".join(f"{fnum(x)},{fnum(y)}" for x, y in pts)
            body = p.poly("polyline", ptstr, None, stroke, markers=markers)
        label = o.get("label")
        if isinstance(label, dict) and isinstance(label.get("box"), list):
            bx = label["box"]
            st = self.text_style(label.get("style"))
            body += self.render_text(num(bx[0], 0), num(bx[1], 0), num(bx[2], 0), num(bx[3], 0),
                                     label.get("text", ""), st)
        return body

    def _style_dict(self, ref, _seen=None):
        _seen = set() if _seen is None else set(_seen)
        if isinstance(ref, str):
            if ref in _seen:
                return {}
            _seen.add(ref)
            return self._style_dict(self.text_styles.get(ref) or self.styles.get(ref) or {}, _seen)
        if not isinstance(ref, dict):
            return {}
        cls = ref.get("class") or ref.get("class_")
        merged = {}
        for name in ([cls] if isinstance(cls, str) else (cls or [])):
            merged.update(self._style_dict(name, _seen))
        merged.update(ref)
        return merged

    def _shape_fill(self, o, style):
        if "fill" in o:
            return self.paint(o.get("fill"))
        if "fill" in style:
            return self.paint(style.get("fill"))
        if "background_image" in style:
            paint = self._background_paint(style.get("background_image"), o.get("box"), style)
            if paint is not None:
                return paint
        if "background" in style:
            paint = self._background_paint(style.get("background"), o.get("box"), style)
            if paint is not None:
                return paint
        if "background_color" in style:
            return self.paint(style.get("background_color"))
        return None

    def _background_paint(self, value, box=None, style=None):
        if isinstance(value, list):
            for item in value:
                paint = self._background_paint(item, box, style)
                if paint is not None:
                    return paint
            return None
        if isinstance(value, dict):
            image = value.get("image")
            if image is not None:
                paint = self._background_paint(image, box, {**(style or {}), **value})
                if paint is not None:
                    return paint
            if value.get("stops") and value.get("kind") in ("linear", "radial", "conic"):
                return self.paint(value)
            if "url" in value:
                return self._background_image_pattern(value.get("url"), box, style or {})
            if "color" in value:
                return self.paint(value.get("color"))
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith(("url(", "http://", "https://", "data:")):
                return self._background_image_pattern(stripped, box, style or {})
            if stripped in self.assets:
                return self._background_image_pattern(stripped, box, style or {})
            return self.paint(stripped)
        return None

    def _background_image_pattern(self, src, box, style):
        if not isinstance(box, list) or len(box) < 4:
            return None
        href = self._background_image_href(src)
        if not href:
            return None
        x, y, w, h = (num(v, 0) for v in box[:4])
        preserve = self._background_preserve_aspect_ratio(style.get("background_size"))
        return self._painter.image_pattern(href, x, y, w, h, preserve)

    def _background_image_href(self, src):
        if isinstance(src, dict):
            src = src.get("url") or src.get("src") or src.get("path")
        if not isinstance(src, str):
            return None
        s = src.strip()
        if s.startswith("url(") and s.endswith(")"):
            s = s[4:-1].strip().strip("'\"")
        if s.startswith(("data:", "http://", "https://", "file://")):
            return s
        return self._image_href(s)

    @staticmethod
    def _background_preserve_aspect_ratio(size):
        if size == "contain":
            return "xMidYMid meet"
        if size in (None, "auto", "cover"):
            return "xMidYMid slice"
        return "none"

    def _shape_radius(self, o, style):
        val = o.get("radius", o.get("rx", style.get("border_radius", style.get("radius"))))
        if isinstance(val, list):
            val = val[0] if val else 0
        return num(val, 0) or 0

    def _shape_stroke(self, o, style):
        """Resolve an object's stroke to a neutral `Stroke` (or None)."""
        if any(k in o for k in ("stroke", "stroke_style")):
            return self.stroke(o)
        border = style.get("border")
        if isinstance(border, (dict, str)):
            return self._border_stroke(border)
        if any(k in style for k in ("stroke", "stroke_width", "stroke_dasharray", "stroke_linecap", "stroke_linejoin")):
            return self.stroke({"stroke": style.get("stroke"), "stroke_style": style})
        return None

    def _component(self, o, style):
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            self.skipped += 1
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        p = self._painter
        spec = self._component_spec(o)
        render_o = {**spec, **o}
        comp_style = self._style_dict(render_o.get("style"))
        comp_style.update(style or {})
        geometry = spec.get("geometry") if isinstance(spec.get("geometry"), dict) else {}
        radius = num(render_o.get("radius", geometry.get("radius")), 0) or 0
        fill = self._shape_fill(render_o, comp_style) or "#fff"
        stroke = self._shape_stroke(render_o, comp_style) or Stroke(color="#bbb", width=1)
        out = [p.rect(x, y, w, h, fill, stroke, radius=radius)]

        layout = spec.get("internal_layout") if isinstance(spec.get("internal_layout"), dict) else {}
        slots = (
            ("title", o.get("title"), {"box_offset": [0, 6, "100%", 18], "style": "heading"}),
            ("body", o.get("body"), {"box_offset": [8, 26, "calc(100% - 16)", "calc(100% - 30)"], "style": "body"}),
        )
        for slot, value, fallback in slots:
            if value is None or value == "":
                continue
            slot_layout = layout.get(slot) if isinstance(layout.get(slot), dict) else {}
            slot_layout = {**fallback, **slot_layout}
            sx, sy, sw, sh = self._component_slot_box(x, y, w, h, slot_layout.get("box_offset"))
            if sw <= 0 or sh <= 0:
                continue
            text_style = self.text_style(slot_layout.get("style"))
            out.append(self.render_text(sx, sy, sw, sh, value, text_style))
        return p.group("".join(out))

    def _component_spec(self, o):
        comps = (self.doc.get("defs") or {}).get("components") or {}
        spec = comps.get(o.get("component"))
        if not isinstance(spec, dict):
            return {}
        merged = {
            k: v for k, v in spec.items()
            if k not in ("variants", "slots")
        }
        variants = spec.get("variants") if isinstance(spec.get("variants"), dict) else {}
        variant = variants.get(o.get("variant"))
        if isinstance(variant, dict):
            merged.update(variant)
        return merged

    def _component_slot_box(self, x, y, w, h, offset):
        if not (isinstance(offset, list) and len(offset) >= 4):
            offset = [0, 0, w, h]
        ox = self._component_length(offset[0], w)
        oy = self._component_length(offset[1], h)
        ow = self._component_length(offset[2], w)
        oh = self._component_length(offset[3], h)
        return x + ox, y + oy, ow, oh

    def _component_length(self, value, total):
        if isinstance(value, (int, float)):
            return num(value, 0)
        if not isinstance(value, str):
            return num(value, 0)
        s = value.strip()
        if s.endswith("%"):
            return total * (num(s[:-1], 0) / 100)
        if s.startswith("calc(") and s.endswith(")"):
            inner = s[5:-1].strip()
            if inner.startswith("100%"):
                rest = inner[4:].strip()
                if rest.startswith("-"):
                    return total - num(rest[1:].strip(), 0)
                if rest.startswith("+"):
                    return total + num(rest[1:].strip(), 0)
                return total
        return num(s, 0)

    def _border_stroke(self, border):
        border = self._border_dict(border)
        if not border:
            return None
        if border.get("style") in ("none", "hidden"):
            return None
        col = self.color(border.get("color")) or "#000"
        width = num(border.get("width"), 1) or 1
        dash = None
        if border.get("style") in ("dashed", "dotted"):
            dash = "4 4" if border.get("style") == "dashed" else "1 3"
        return Stroke(color=col, width=width, dash=dash)

    @staticmethod
    def _border_dict(border):
        if isinstance(border, dict):
            return border
        if not isinstance(border, str):
            return {}
        styles = {"none", "hidden", "solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset"}
        out = {}
        colors = []
        for part in border.split():
            if part in styles:
                out["style"] = part
            elif num(part, None) is not None:
                out["width"] = part
            else:
                colors.append(part)
        if colors:
            out["color"] = " ".join(colors)
        return out

    def _image(self, o, box):
        p = self._painter
        x, y, w, h = (num(v, 0) for v in box[:4])
        src = o.get("src", "")
        href = self._image_href(src)
        clip_id = self._image_clip_id(o.get("clip"), x, y, w, h)
        preserve = self._image_preserve_aspect_ratio(o.get("preserve_aspect_ratio"))

        if href:
            image = p.image(x, y, w, h, href, preserve)
            return p.clip_wrap(image, clip_id) if clip_id else image
        label = o.get("label") or os.path.basename(str(src)) or "image"
        st = {"family": "sans-serif", "size": 11, "weight": "normal", "italic": False,
              "color": "#888", "align": "center", "lh": 1.2}
        placeholder = (p.rect(x, y, w, h, "#eee", Stroke(color="#bbb"))
                       + p.line(x, y, x + w, y + h, Stroke(color="#ccc"))
                       + p.line(x + w, y, x, y + h, Stroke(color="#ccc"))
                       + p.text_tag(x, y + h / 2 - 8, w, 16, "▣ " + str(label), st, vcenter=True))
        return p.clip_wrap(placeholder, clip_id) if clip_id else placeholder

    def _image_href(self, src):
        asset = self.assets.get(src)
        href = None
        if isinstance(asset, dict):
            href = asset.get("data") or asset.get("url")
            path = asset.get("src") or asset.get("path")
        else:
            path = asset if asset else src

        if href:
            return str(href)
        if not path:
            return None
        path = str(path)
        if path.startswith(("data:", "http://", "https://", "file://")):
            return path
        if not os.path.isabs(path):
            path = os.path.normpath(os.path.join(self.base_dir, path))
        if os.path.exists(path):
            return "file://" + path
        return None

    def _image_clip_id(self, clip, x, y, w, h):
        shape = clip
        if isinstance(clip, dict):
            shape = clip.get("shape") or clip.get("type")
        if isinstance(shape, str) and shape.lower() in ("ellipse", "circle", "oval"):
            return self._painter.clip_ellipse(x + w / 2, y + h / 2, w / 2, h / 2)
        return None

    @staticmethod
    def _image_preserve_aspect_ratio(value):
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "xMidYMid meet"

    def canvas_wh(self, page):
        return self._canvas.resolve(page)

    def render_page(self, page):
        """Return a list of SVG strings (1 for page-mode, N for paginated flow)."""
        self._painter.new_page()
        self.contract = {**self.doc_contract, **((page.get("rendering") or {}).get("text") or {})}
        w, h = self.canvas_wh(page)
        if page.get("mode") == "flow":
            return self._render_flow(page, w, h)
        self._object_index = self._index_objects(page)
        body = self._render_page_body(page)
        return [self._painter.document(w, h, body,
                                       lang=self.doc.get("lang"), title=self.doc.get("title"),
                                       desc=self.doc.get("description"))]

    def _render_page_body(self, page):
        ordered = page.get("reading_order")
        if isinstance(ordered, list):
            return self._render_page_body_in_reading_order(page, ordered)

        body = []
        for layer in sorted(page.get("layers") or [], key=lambda L: L.get("z", 0)):
            lo = layer.get("opacity")
            inner = "".join(self.obj(o) for o in (layer.get("objects") or []))
            body.append(self._painter.opacity_group(inner, lo) if lo not in (None, 1) else inner)
        return "".join(body)

    def _render_page_body_in_reading_order(self, page, reading_order):
        top_level = []
        first_by_id = {}
        for layer in sorted(page.get("layers") or [], key=lambda L: L.get("z", 0)):
            lo = layer.get("opacity")
            for index, obj in enumerate(layer.get("objects") or []):
                if not isinstance(obj, dict):
                    continue
                entry = (obj, lo, index)
                top_level.append(entry)
                oid = obj.get("id")
                if oid is not None and oid not in first_by_id:
                    first_by_id[oid] = entry

        used = set()
        pieces = []
        for oid in reading_order:
            entry = first_by_id.get(oid)
            if entry is None:
                continue
            used.add(id(entry[0]))
            pieces.append(self._render_page_object_entry(entry))
        for entry in top_level:
            if id(entry[0]) not in used:
                pieces.append(self._render_page_object_entry(entry))
        return "".join(pieces)

    def _render_page_object_entry(self, entry):
        obj, layer_opacity, _index = entry
        rendered = self.obj(obj)
        if rendered and layer_opacity not in (None, 1):
            rendered = self._painter.opacity_group(rendered, layer_opacity)
        return rendered

    def _render_flow(self, page, w, h):
        p = self._painter
        margin = 56
        x, top, bottom = margin, margin, h - margin
        usable = w - 2 * margin
        pages, body, cy = [], [], top

        def flush():
            if body:
                pages.append(p.document(w, h, "".join(body)))

        def newpage():
            nonlocal body, cy
            flush()
            p.new_page()
            body, cy = [], top

        def wrap(text, size):
            cpl = max(8, int(usable / (size * 0.52)))
            words, lines, cur = str(text).split(), [], ""
            for word in words:
                if cur and len(cur) + 1 + len(word) > cpl:
                    lines.append(cur); cur = word
                else:
                    cur = (cur + " " + word).strip()
            if cur:
                lines.append(cur)
            return lines or [""]

        def text_of(value):
            if value is None:
                return ""
            if isinstance(value, (str, int, float)):
                return str(value)
            if isinstance(value, list):
                return "".join(text_of(item) for item in value)
            if not isinstance(value, dict):
                return str(value)
            if value.get("text") is not None:
                return str(value.get("text"))
            if isinstance(value.get("content"), list):      # LinkInline / FootnoteInline inline content
                return "".join(text_of(item) for item in value.get("content") or [])
            if value.get("tex") is not None:                # inline math fallback
                return math_text(value.get("tex"))
            if value.get("latex") is not None:
                return math_text(value.get("latex"))
            if isinstance(value.get("spans"), list):
                return "".join(text_of(span) for span in value.get("spans") or [])
            if isinstance(value.get("children"), list):
                return "\n".join(text_of(child) for child in value.get("children") or [])
            return ""

        def emit(text, st, indent=0, gap_after=6):
            nonlocal cy
            for ln in wrap(text, st["size"]):
                if cy + st["size"] > bottom:
                    newpage()
                body.append(p.text_tag(x + indent, cy, usable - indent, st["size"] * st["lh"],
                                       ln, st, vcenter=False))
                cy += st["size"] * st["lh"]
            cy += gap_after

        def emit_table(fl):
            nonlocal cy
            header = fl.get("header") if isinstance(fl.get("header"), list) else []
            rows = fl.get("rows") if isinstance(fl.get("rows"), list) else []
            if not header and not rows:
                return
            col_count = max(len(header), *(len(r) for r in rows if isinstance(r, list)), 1)
            col_w = usable / col_count
            row_h = 18
            font_size = 6.5 if col_count > 6 else 8
            cell_st = {**base, "family": "sans-serif", "size": font_size, "lh": 1.1}
            head_st = {**cell_st, "weight": "bold", "color": "#222"}

            def emit_row(values, st, fill):
                nonlocal cy
                if cy + row_h > bottom:
                    newpage()
                for idx in range(col_count):
                    tx = x + idx * col_w
                    value = values[idx] if idx < len(values) else ""
                    body.append(p.rect(tx, cy, col_w, row_h, fill, Stroke(color="#d8d8d8", width=0.5)))
                    body.append(p.text_tag(tx + 3, cy + 3, col_w - 6, row_h - 6, text_of(value), st, vcenter=False))
                cy += row_h

            caption = text_of(fl.get("caption"))
            if caption:
                emit(caption, {**base, "family": "sans-serif", "size": 9, "weight": "bold"}, gap_after=4)
            if header:
                emit_row(header, head_st, "#f1f3f5")
            for idx, row in enumerate(rows):
                emit_row(row if isinstance(row, list) else [row], cell_st, "#ffffff" if idx % 2 == 0 else "#fafafa")
            cy += 10

        def emit_math(fl):
            nonlocal cy
            input_kind = "tex" if fl.get("tex") is not None else "mathml" if fl.get("mathml") is not None else "tex"
            source = fl.get("tex") if fl.get("tex") is not None else fl.get("mathml") if fl.get("mathml") is not None else text_of(fl)
            rendered = self._math.render(source, input_kind)
            if rendered:
                math_color = "#111"
                math_body = str(rendered.get("body")).replace("currentColor", math_color)
                natural_w = max(1.0, num(rendered.get("width"), 120))
                natural_h = max(1.0, num(rendered.get("height"), 24))
                scale = min(1.0, usable / natural_w)
                draw_w = natural_w * scale
                draw_h = natural_h * scale
                if cy + draw_h > bottom:
                    newpage()
                mx = x + (usable - draw_w) / 2
                title = fl.get("alt") or fl.get("aria_label") or "math expression"
                body.append(p.embedded_svg(
                    mx, cy, draw_w, draw_h,
                    viewbox=rendered.get("viewBox"), color=math_color,
                    title=title, body=math_body,
                ))
                cy += draw_h + 12
                return

            text = math_text(source)
            st = {**base, "family": "serif", "size": 13, "color": "#111", "align": "center", "lh": 1.25}
            for ln in str(text).splitlines() or [""]:
                emit(ln, st, gap_after=1)
            cy += 8

        def emit_flow(fl):
            nonlocal cy
            ft = fl.get("type")
            stref = self.text_style(fl.get("style")) if fl.get("style") else None
            if ft == "heading":
                sz = max(15, 30 - 3 * (fl.get("level", 1) - 1))
                emit(text_of(fl), {**base, "size": sz, "weight": "bold",
                                  **({"color": stref["color"]} if stref else {})}, gap_after=10)
            elif ft == "paragraph":
                emit(text_of(fl), stref or base)
            elif ft == "list":
                ordered = bool(fl.get("ordered"))
                for idx, it in enumerate(fl.get("items", []), start=1):
                    bullet = f"{idx}. " if ordered else "• "
                    emit(bullet + text_of(it), base, indent=16, gap_after=2)
                cy += 6
            elif ft in ("block", "keep_together"):
                children = fl.get("children") if isinstance(fl.get("children"), list) else []
                for child in children:
                    if isinstance(child, dict):
                        emit_flow(child)
                cy += 4
            elif ft == "table":
                emit_table(fl)
            elif ft == "math":
                emit_math(fl)
            elif ft == "code":
                text = fl.get("code") or fl.get("source") or text_of(fl)
                mono = {**base, "family": "monospace", "size": 10, "color": "#333"}
                for ln in str(text).splitlines() or [""]:
                    emit(ln, mono, gap_after=1)
                cy += 8
            elif ft == "spacer":
                cy += num(fl.get("height"), 12) or 12
            elif ft in ("page_break", "column_break"):
                newpage()
            elif ft == "figure" and isinstance(fl.get("object"), dict):
                emit_figure(fl)
            else:
                text = text_of(fl)
                if text:
                    emit(text, stref or base)

        def emit_figure(fl):
            nonlocal cy
            # Draw the figure's actual geometry (the "drawing"), not a stub.
            ob = fl["object"]
            obox = ob.get("box") if isinstance(ob.get("box"), list) else None
            size = fl.get("size") if isinstance(fl.get("size"), list) else None
            fw = (num(size[0], 0) if size and len(size) >= 2
                  else num(obox[2], usable) if obox and len(obox) >= 4 else usable)
            fh = (num(size[1], 0) if size and len(size) >= 2
                  else num(obox[3], 0) if obox and len(obox) >= 4 else 0)
            scale = min(1.0, usable / fw) if fw else 1.0
            draw_h = (fh or 0) * scale
            if cy + draw_h > bottom and cy > top:        # keep a figure whole
                newpage()
            inner = self.obj(ob)
            if inner:
                ox = num(obox[0], 0) if obox and len(obox) >= 2 else 0
                oy = num(obox[1], 0) if obox and len(obox) >= 2 else 0
                tx, ty = x - ox * scale, cy - oy * scale
                if scale != 1.0:
                    body.append(p.transform_group(
                        inner, [("translate", [fnum(tx), fnum(ty)]), ("scale", [fnum(scale)])]))
                else:
                    body.append(p.group(inner, translate=(tx, ty)) if (tx or ty) else inner)
                cy += draw_h + 6
            cap = fl.get("caption")
            captxt = cap if isinstance(cap, str) else (cap.get("text", "") if isinstance(cap, dict) else "")
            if captxt:
                emit(captxt, {**base, "size": 10, "italic": True, "color": "#666",
                              "align": "center"}, gap_after=12)
            else:
                cy += 8

        base = {"family": "serif", "size": 12, "weight": "normal", "italic": False,
                "color": "#1c1c1c", "align": "left", "lh": 1.4}
        for fl in page.get("story") or []:
            if not isinstance(fl, dict):
                continue
            emit_flow(fl)
        flush()
        return pages or [p.document(w, h, "")]


# --------------------------------------------------------------------------- #
#  driver                                                                     #
# --------------------------------------------------------------------------- #
