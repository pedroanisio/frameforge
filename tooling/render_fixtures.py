#!/usr/bin/env python3
"""
render_fixtures.py — a dependency-free SVG proxy renderer for FrameGraph v2 docs.

Renders ALL or ANY document under fixtures/ (or any path you pass) to SVG, one
file per page, plus a browsable index.html contact sheet. Unlike the matplotlib
proxy in render_fg_doc.py, this needs only the standard library + PyYAML, so it
runs in a bare environment, and it tolerates the full fixture variety:

  * canvas from explicit `size`, a `preset`, or inherited from a master
  * `page` layers AND `flow` sections (naive vertical text flow, paginated)
  * the core object set: rect / ellipse / circle / line / polyline / polygon /
    path / text / bullet_list / icon / image / table / group
  * HEAD stroke single-form (paint in `stroke`, geometry in `stroke_style`)
  * token colour deref, CSS-named *and* legacy shorthand text styles,
    linear/radial gradient fills (conic ≈ first stop)

This is a SANITY-CHECK proxy, not a conformant renderer: no real text shaping or
line-breaking metrics, fonts are the browser's generic families, out-of-profile
objects and missing image assets become labelled placeholders. Geometry,
positions, colours and z-order are honoured.

Usage:
    python3 tooling/render_fixtures.py                       # render every fixture -> out/render/
    python3 tooling/render_fixtures.py --all
    python3 tooling/render_fixtures.py fixtures/b1/mckinsey-7s.fg.json
    python3 tooling/render_fixtures.py 'fixtures/*.fg.yaml'  # globs ok (quote them)
    python3 tooling/render_fixtures.py fixtures/b1 --out /tmp/r --max-pages 3
    python3 tooling/render_fixtures.py --list                # just list discoverable docs

Open out/render/index.html in a browser to see the contact sheet.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FIXTURES = os.path.join(ROOT, "fixtures")

# DDD migration (steps 2–3): the pure scalar helpers and the token/style/canvas/
# stroke resolvers now live in framegraph.rendering.domain; the Renderer below
# delegates to them. SVG output is unchanged — this is a pure relocation.
sys.path.insert(0, ROOT)
from framegraph.rendering.domain.geometry import (  # noqa: E402
    esc, fnum, is_point, num,
)
from framegraph.rendering.domain.services.canvas_resolver import (  # noqa: E402
    CanvasResolver,
)
from framegraph.rendering.domain.services.paint_resolver import (  # noqa: E402
    ColorResolver,
)
from framegraph.rendering.domain.services.effect_resolver import (  # noqa: E402
    EffectResolver,
)
from framegraph.rendering.domain.services.stroke_resolver import (  # noqa: E402
    StrokeResolver,
)
from framegraph.rendering.domain.services.table_layout import (  # noqa: E402
    resolve_column_widths,
)
from framegraph.rendering.domain.services.text_style_resolver import (  # noqa: E402
    TextStyleResolver,
)
from framegraph.rendering.infrastructure.painters.svg import (  # noqa: E402
    SvgPainter,
)


# --------------------------------------------------------------------------- #
#  small helpers: num / fnum / esc / is_point are imported from               #
#  framegraph.rendering.domain.geometry (DDD migration step 2).               #
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  the renderer                                                               #
# --------------------------------------------------------------------------- #
class Renderer:
    def __init__(self, doc, base_dir):
        self.doc = doc if isinstance(doc, dict) else {}
        self.base_dir = base_dir
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
        return self._stroke.resolve(o)

    def _arrow_attrs(self, o):
        """SVG marker attrs for an open shape's arrowheads, or '' if none.

        Reads `arrow_start`/`arrow_end` off the resolved `stroke_style`, registers
        the needed `<marker>`s with the painter (deduped), and returns e.g.
        ' marker-start="url(#ah1)" marker-end="url(#ah1)"'. Additive: emits nothing
        unless the stroke requests an arrow, so arrow-free fixtures are unchanged."""
        spec = self._stroke.arrow_spec(o)
        if not spec:
            return ""
        out = ""
        if spec["start"]:
            out += f' marker-start="url(#{self._painter.marker(spec["color"], spec["start"])})"'
        if spec["end"]:
            out += f' marker-end="url(#{self._painter.marker(spec["color"], spec["end"])})"'
        return out

    # ---- text style resolution -------------------------------------------- #
    def text_style(self, ref):
        return self._text_style.resolve(ref)

    # ---- text measurement / fitting (estimated; no font metrics here) ------ #
    def measure(self, s, size, avg):
        return len(s) * size * avg

    def wrap_words(self, text, w, size, avg):
        maxc = max(1, int(w / (size * avg)))
        out, cur = [], ""
        for word in str(text).split():
            while len(word) > maxc:                  # hard-break an over-long token
                if cur:
                    out.append(cur); cur = ""
                out.append(word[:maxc]); word = word[maxc:]
            if cur and len(cur) + 1 + len(word) > maxc:
                out.append(cur); cur = word
            else:
                cur = (cur + " " + word).strip()
        if cur:
            out.append(cur)
        return out or [""]

    def ellipsize(self, s, w, size, avg):
        maxc = max(0, int(w / (size * avg)))
        if len(s) <= maxc:
            return s
        return (s[: max(0, maxc - 1)].rstrip() + "…") if maxc else "…"

    # anchor() / text_tag() / clip_rect() emission moved to the SvgPainter
    # (step 4); the builder calls self._painter.* for them.

    def render_text(self, x, y, w, h, content, st):
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
        if self.measure(content, size, avg) > w + 0.5 or size * lh > h + 0.5:
            self.tstats["naive_overflow"] += 1

        def layout(sz):
            return self.wrap_words(content, w, sz, avg) if do_wrap else [content]

        lines = layout(size)
        if len(lines) > 1:
            self.tstats["wrapped"] += 1
        if overflow == "shrink_to_fit":
            start = size
            while size > min_fs:
                lines = layout(size)
                too_tall = len(lines) * size * lh > h + 0.5
                too_wide = max((self.measure(ln, size, avg) for ln in lines), default=0) > w + 0.5
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
                lines[-1] = self.ellipsize(lines[-1], w, size, avg)
        # single unwrapped line wider than the box
        if not do_wrap and self.measure(lines[0], size, avg) > w + 0.5:
            if text_ovf == "ellipsis":
                lines[0] = self.ellipsize(lines[0], w, size, avg)
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
        el = self._painter.text_block(base, a, style, lines, tx, size * lh)

        # telemetry: is it visually contained?
        widest = max((self.measure(ln, size, avg) for ln in lines), default=0)
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

    # ---- per-object dispatch ---------------------------------------------- #
    def obj(self, o):
        if not isinstance(o, dict):
            return ""
        try:
            inner = self._obj(o)
            if inner:
                inner = self._with_outline(o, self._style_dict(o.get("style")), inner)
                inner = self._with_effects(o, self._style_dict(o.get("style")), inner)
                inner = self._with_transform(o, self._style_dict(o.get("style")), inner)
            opacity = o.get("opacity")
            if inner and opacity not in (None, 1):
                return self._painter.opacity_group(inner, num(opacity, 1))
            return inner
        except Exception:                              # never let one object kill a page
            self.skipped += 1
            return ""

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
        transform = self._svg_transform(style.get("transform"), style.get("transform_origin"), o.get("box"))
        return self._painter.transform_group(svg, transform) if transform else svg

    def _svg_transform(self, value, origin, box):
        if not value or value == "none":
            return ""
        if isinstance(value, str):
            return value.replace("deg", "")
        items = value if isinstance(value, list) else [value]
        ox, oy = self._transform_origin(origin, box)
        parts = []
        for item in items:
            if isinstance(item, str):
                parts.append(item.replace("deg", ""))
                continue
            if not isinstance(item, dict):
                continue
            fn = item.get("fn") or item.get("kind") or item.get("name")
            args = item.get("args") or []
            vals = [self._transform_arg(v) for v in args]
            if fn == "rotate" and vals:
                parts.append(f"rotate({vals[0]} {fnum(ox)} {fnum(oy)})" if ox is not None else f"rotate({vals[0]})")
            elif fn == "translate":
                parts.append(f"translate({' '.join(vals)})")
            elif fn == "translate_x" and vals:
                parts.append(f"translate({vals[0]} 0)")
            elif fn == "translate_y" and vals:
                parts.append(f"translate(0 {vals[0]})")
            elif fn == "scale":
                parts.append(self._origin_transform(f"scale({' '.join(vals)})", ox, oy))
            elif fn == "scale_x" and vals:
                parts.append(self._origin_transform(f"scale({vals[0]} 1)", ox, oy))
            elif fn == "scale_y" and vals:
                parts.append(self._origin_transform(f"scale(1 {vals[0]})", ox, oy))
            elif fn == "skew_x" and vals:
                parts.append(self._origin_transform(f"skewX({vals[0]})", ox, oy))
            elif fn == "skew_y" and vals:
                parts.append(self._origin_transform(f"skewY({vals[0]})", ox, oy))
            elif fn == "skew" and vals:
                parts.append(self._origin_transform(f"skewX({vals[0]})", ox, oy))
                if len(vals) > 1:
                    parts.append(self._origin_transform(f"skewY({vals[1]})", ox, oy))
            elif fn == "matrix" and vals:
                parts.append(f"matrix({' '.join(vals)})")
        return " ".join(p for p in parts if p)

    def _transform_origin(self, origin, box):
        if isinstance(origin, (list, tuple)) and len(origin) >= 2:
            return num(origin[0], 0), num(origin[1], 0)
        if isinstance(origin, str):
            vals = origin.replace(",", " ").split()
            if len(vals) >= 2 and not any("%" in v for v in vals[:2]):
                return num(vals[0], 0), num(vals[1], 0)
        if isinstance(box, list) and len(box) >= 4:
            return num(box[0], 0) + num(box[2], 0) / 2, num(box[1], 0) + num(box[3], 0) / 2
        return None, None

    @staticmethod
    def _transform_arg(value):
        n = num(value, None)
        return fnum(n) if n is not None else str(value).replace("deg", "")

    @staticmethod
    def _origin_transform(transform, ox, oy):
        if ox is None:
            return transform
        return f"translate({fnum(ox)} {fnum(oy)}) {transform} translate({fnum(-ox)} {fnum(-oy)})"

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
                stk = self._shape_stroke(o, style) or ' stroke="#000" stroke-width="1"'
                return p.line(fr[0], fr[1], to[0], to[1], stk + self._arrow_attrs(o))
            return ""

        if t in ("polyline", "polygon"):
            pts = o.get("points") or []
            ptstr = " ".join(f"{fnum(num(pt[0],0))},{fnum(num(pt[1],0))}" for pt in pts if is_point(pt))
            if not ptstr:
                return ""
            closed = t == "polygon" or o.get("closed")
            tag = "polygon" if closed else "polyline"
            return p.poly(tag, ptstr, fill if closed else None,
                          self._shape_stroke(o, style) + self._arrow_attrs(o),
                          fill_opacity=fill_opacity if closed else None,
                          fill_rule=fill_rule if closed else None)

        if t == "path":
            d = o.get("d")
            if isinstance(d, list):
                d = " ".join(str(seg[0]) + " " + " ".join(fnum(num(n, 0)) for n in seg[1:])
                             if isinstance(seg, list) else str(seg) for seg in d)
            if not isinstance(d, str) or not d.strip():
                return ""
            return p.path(d, fill, self._shape_stroke(o, style) + self._arrow_attrs(o),
                          fill_opacity=fill_opacity, fill_rule=fill_rule)

        if t == "text" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            content = o.get("text")
            if content is None and o.get("spans"):
                content = "".join(s if isinstance(s, str) else s.get("text", "")
                                  for s in o["spans"])
            return self.render_text(x, y, w, h, content, self.text_style(o.get("style")))

        if t == "bullet_list" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            st = self.text_style(o.get("style"))
            marker = o.get("marker", "•")
            gap = num(o.get("gap"), None) or st["size"] * 1.5
            mc = self.color(o.get("marker_color")) or st["color"]
            out = []
            cy = y + st["size"]
            for it in o.get("items", []):
                txt = it if isinstance(it, str) else (it.get("text", "") if isinstance(it, dict) else str(it))
                out.append(p.text_tag(x, cy - st["size"], st["size"] + 4, st["size"] + 4,
                                      marker, {**st, "color": mc}, vcenter=False))
                out.append(p.text_tag(x + st["size"] * 1.1, cy - st["size"], w, st["size"] + 4,
                                      txt, st, vcenter=False))
                cy += gap
            return "".join(out)

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
            return self._table(o, box)

        if t == "group":
            inner = "".join(self.obj(ch) for ch in (o.get("children") or []))
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
            return (p.rect(x, y, w, h, "#f3f3f3", ' stroke="#ccc" stroke-dasharray="3 3"')
                    + p.text_tag(x, y, w, h, f"?{t}", st, vcenter=True))
        self.skipped += 1
        return ""

    def _style_dict(self, ref):
        if isinstance(ref, str):
            return dict(self.text_styles.get(ref) or self.styles.get(ref) or {})
        if not isinstance(ref, dict):
            return {}
        cls = ref.get("class") or ref.get("class_")
        merged = {}
        for name in ([cls] if isinstance(cls, str) else (cls or [])):
            merged.update(self.text_styles.get(name) or self.styles.get(name) or {})
        merged.update(ref)
        return merged

    def _shape_fill(self, o, style):
        if "fill" in o:
            return self.paint(o.get("fill"))
        for key in ("fill", "background_color", "background"):
            if key in style:
                return self.paint(style.get(key))
        return None

    def _shape_radius(self, o, style):
        val = o.get("radius", o.get("rx", style.get("border_radius", style.get("radius"))))
        if isinstance(val, list):
            val = val[0] if val else 0
        return num(val, 0) or 0

    def _shape_stroke(self, o, style):
        if any(k in o for k in ("stroke", "stroke_style")):
            return self.stroke(o)
        border = style.get("border")
        if isinstance(border, dict):
            return self._border_stroke(border)
        if any(k in style for k in ("stroke", "stroke_width", "stroke_dasharray", "stroke_linecap", "stroke_linejoin")):
            return self.stroke({"stroke": style.get("stroke"), "stroke_style": style})
        return ""

    def _border_stroke(self, border):
        if border.get("style") in ("none", "hidden"):
            return ""
        col = self.color(border.get("color")) or "#000"
        width = num(border.get("width"), 1) or 1
        out = f' stroke="{esc(col)}" stroke-width="{fnum(width)}"'
        if border.get("style") in ("dashed", "dotted"):
            dash = "4 4" if border.get("style") == "dashed" else "1 3"
            out += f' stroke-dasharray="{dash}"'
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
        placeholder = (p.rect(x, y, w, h, "#eee", ' stroke="#bbb"')
                       + p.line(x, y, x + w, y + h, ' stroke="#ccc"')
                       + p.line(x + w, y, x, y + h, ' stroke="#ccc"')
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

    def _table(self, o, box):
        p = self._painter
        x0, y0, w, h = (num(v, 0) for v in box[:4])
        style = self._style_dict(o.get("style"))
        cols = o.get("columns") or []
        header = o.get("header")
        rows = o.get("rows") or []
        visual = ([("h", header)] if header else []) + [("b", r) for r in rows]
        nrow = max(1, len(visual))
        ncol = max(1, len(cols) or (max((len(r) for _, r in visual), default=1)))
        cw = resolve_column_widths(cols, ncol, w)
        colx = [x0 + sum(cw[:k]) for k in range(ncol)]
        rh = h / nrow
        grid_stroke = self._shape_stroke(o, style) or ' stroke="#bbb"'
        row_stroke = grid_stroke
        col_stroke = grid_stroke
        header_fill = self.paint(style.get("header_fill")) if "header_fill" in style else "#3b6ea5"
        padding = max(0, num(o.get("cell_padding"), 4) or 0)
        out = [p.rect(x0, y0, w, h, "white", grid_stroke)]
        st_h = {"family": "sans-serif", "size": min(13, rh * 0.5), "weight": "bold",
                "italic": False, "color": "#fff", "align": "left", "lh": 1.2}
        st_c = {**st_h, "weight": "normal", "color": "#222"}
        if style.get("header_text"):
            st_h = {**st_h, **self.text_style(style.get("header_text"))}
        if style.get("cell_text"):
            st_c = {**st_c, **self.text_style(style.get("cell_text"))}
        for ri, (kind, row) in enumerate(visual):
            ry = y0 + ri * rh
            if kind == "h":
                out.append(p.rect(x0, ry, w, rh, header_fill, ""))
            elif o.get("zebra") and (ri % 2):
                out.append(p.rect(x0, ry, w, rh, "#f4f6f9", ""))
            for ci in range(ncol):
                cell = row[ci] if ci < len(row) else ""
                txt = cell.get("content", "") if isinstance(cell, dict) else ("" if cell is None else str(cell))
                col = cols[ci] if ci < len(cols) and isinstance(cols[ci], dict) else {}
                st = st_h if kind == "h" else st_c
                if col.get("align"):
                    st = {**st, "align": col.get("align")}
                out.append(p.text_tag(colx[ci] + padding, ry, max(0, cw[ci] - 2 * padding), rh, txt, st, vcenter=True))
            out.append(p.line(x0, ry, x0 + w, ry, row_stroke))
        for cx in colx[1:]:
            out.append(p.line(cx, y0, cx, y0 + h, col_stroke))
        return "".join(out)

    # ---- page / flow ------------------------------------------------------- #
    def canvas_wh(self, page):
        return self._canvas.resolve(page)

    def render_page(self, page):
        """Return a list of SVG strings (1 for page-mode, N for paginated flow)."""
        self._painter.new_page()
        self.contract = {**self.doc_contract, **((page.get("rendering") or {}).get("text") or {})}
        w, h = self.canvas_wh(page)
        if page.get("mode") == "flow":
            return self._render_flow(page, w, h)
        body = []
        for layer in sorted(page.get("layers") or [], key=lambda L: L.get("z", 0)):
            lo = layer.get("opacity")
            inner = "".join(self.obj(o) for o in (layer.get("objects") or []))
            body.append(self._painter.opacity_group(inner, lo) if lo not in (None, 1) else inner)
        return [self._painter.document(w, h, "".join(body))]

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

        def emit(text, st, indent=0, gap_after=6):
            nonlocal cy
            for ln in wrap(text, st["size"]):
                if cy + st["size"] > bottom:
                    newpage()
                body.append(p.text_tag(x + indent, cy, usable - indent, st["size"] * st["lh"],
                                       ln, st, vcenter=False))
                cy += st["size"] * st["lh"]
            cy += gap_after

        base = {"family": "serif", "size": 12, "weight": "normal", "italic": False,
                "color": "#1c1c1c", "align": "left", "lh": 1.4}
        for fl in page.get("story") or []:
            if not isinstance(fl, dict):
                continue
            ft = fl.get("type")
            stref = self.text_style(fl.get("style")) if fl.get("style") else None
            if ft == "heading":
                sz = max(15, 30 - 3 * (fl.get("level", 1) - 1))
                emit(fl.get("text", ""), {**base, "size": sz, "weight": "bold",
                                          **({"color": stref["color"]} if stref else {})}, gap_after=10)
            elif ft == "paragraph":
                txt = fl.get("text")
                if txt is None and fl.get("spans"):
                    txt = "".join(s if isinstance(s, str) else s.get("text", "") for s in fl["spans"])
                emit(txt or "", stref or base)
            elif ft == "list":
                for it in fl.get("items", []):
                    txt = it if isinstance(it, str) else (it.get("text", "") if isinstance(it, dict) else str(it))
                    emit("• " + str(txt), base, indent=16, gap_after=2)
                cy += 6
            elif ft == "spacer":
                cy += num(fl.get("height"), 12) or 12
            elif ft in ("page_break", "column_break"):
                newpage()
            else:                                      # table/figure/image/code/math/toc/...
                if cy + 26 > bottom:
                    newpage()
                ph = {**base, "family": "monospace", "size": 11, "italic": True, "color": "#999"}
                body.append(p.rect(x, cy, usable, 22, "#f5f5f5", ' stroke="#ddd" stroke-dasharray="3 3"'))
                body.append(p.text_tag(x + 6, cy, usable, 22, f"[{ft}]", ph, vcenter=True))
                cy += 30
        flush()
        return pages or [p.document(w, h, "")]


# --------------------------------------------------------------------------- #
#  driver                                                                     #
# --------------------------------------------------------------------------- #
def discover(paths):
    """Expand args (files / dirs / globs) into a sorted list of FrameGraph docs."""
    exts = (".json", ".yaml", ".yml")
    out = []
    if not paths:
        paths = [FIXTURES]
    for p in paths:
        cand = glob.glob(p, recursive=True) or ([p] if os.path.exists(p) else [])
        for c in cand:
            if os.path.isdir(c):
                for root, _, files in os.walk(c):
                    out += [os.path.join(root, f) for f in files if f.endswith(exts)]
            elif c.endswith(exts):
                out.append(c)
    seen, docs = set(), []
    for f in sorted(set(out)):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("dsl") == "FrameGraph" and d.get("pages"):
            rp = os.path.relpath(f, ROOT)
            if rp not in seen:
                seen.add(rp); docs.append((f, d))
    return docs


def stem_of(path):
    # keep the extension so docusign.fg.json and docusign.fg.yaml stay distinct
    rel = os.path.relpath(path, FIXTURES) if path.startswith(FIXTURES) else os.path.basename(path)
    return rel.replace(os.sep, "_")


def write_index(out_dir, entries, title, page_links=False):
    cards = []
    for name, link, thumbs in entries:
        if page_links:
            imgs = "".join(
                f'<a href="{esc(t)}"><img src="{esc(t)}" loading="lazy" '
                f'style="width:200px;border:1px solid #ccc;margin:4px;background:#fff"></a>'
                for t in thumbs)
            cards.append(f'<section><h2>{esc(name)} '
                         f'<small style="color:#888">({len(thumbs)} page(s))</small></h2>{imgs}</section>')
        else:
            first = f'<img src="{esc(thumbs[0])}" loading="lazy" style="width:240px;border:1px solid #ccc;background:#fff">' if thumbs else ""
            cards.append(f'<a href="{esc(link)}" style="text-decoration:none;color:inherit">'
                         f'<figure style="display:inline-block;margin:8px;vertical-align:top">'
                         f'{first}<figcaption style="font:13px sans-serif;max-width:240px">{esc(name)} '
                         f'<span style="color:#888">({len(thumbs)}p)</span></figcaption></figure></a>')
    body = "".join(cards)
    doc = (f'<!doctype html><meta charset="utf-8"><title>{esc(title)}</title>'
           f'<body style="font:14px sans-serif;margin:24px;background:#fafafa">'
           f'<h1>{esc(title)}</h1>{body}</body>')
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="files / dirs / globs (default: all fixtures/)")
    ap.add_argument("--all", action="store_true", help="render every fixture under fixtures/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "render"), help="output dir")
    ap.add_argument("--max-pages", type=int, default=0, help="cap pages rendered per doc (0 = all)")
    ap.add_argument("--list", action="store_true", help="list discoverable docs and exit")
    ap.add_argument("--check-overflow", action="store_true",
                    help="render, then assert no text visually overflows a containing box (exit 1 on failure)")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    docs = discover([] if args.all else args.paths)
    if args.list:
        for f, _ in docs:
            print(os.path.relpath(f, ROOT))
        print(f"\n{len(docs)} document(s).")
        return 0
    if not docs:
        print("No FrameGraph documents found. Try: render_fixtures.py --all", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    index_entries, total_pages = [], 0
    agg = {}
    for f, doc in docs:
        stem = stem_of(f)
        doc_dir = os.path.join(args.out, stem)
        os.makedirs(doc_dir, exist_ok=True)
        r = Renderer(doc, os.path.dirname(os.path.abspath(f)))
        svgs, thumbs = [], []
        for page in doc.get("pages", []):
            if not isinstance(page, dict):
                continue
            for s in r.render_page(page):
                svgs.append(s)
                if args.max_pages and len(svgs) >= args.max_pages:
                    break
            if args.max_pages and len(svgs) >= args.max_pages:
                break
        for i, s in enumerate(svgs, 1):
            fn = f"p{i:03d}.svg"
            with open(os.path.join(doc_dir, fn), "w", encoding="utf-8") as fh:
                fh.write(s)
            thumbs.append(f"{stem}/{fn}")
        write_index(doc_dir, [(stem, "", [f"p{i:03d}.svg" for i in range(1, len(svgs) + 1)])],
                    f"FrameGraph proxy — {stem}", page_links=True)
        index_entries.append((stem, f"{stem}/index.html", thumbs))
        total_pages += len(svgs)
        for k, v in r.tstats.items():
            agg[k] = agg.get(k, 0) + v
        if not args.quiet:
            note = f" ({r.skipped} skipped)" if r.skipped else ""
            ov = f"  ⚠ {r.tstats['uncontained']} text overflow" if r.tstats["uncontained"] else ""
            print(f"  {stem}: {len(svgs)} page(s){note}{ov}")

    write_index(args.out, index_entries, "FrameGraph fixtures — SVG proxy contact sheet")
    print(f"\nRendered {len(docs)} document(s), {total_pages} page(s) -> {args.out}")
    print(f"Open {os.path.join(args.out, 'index.html')}")

    if args.check_overflow:
        print("\n=== text-fit overflow check ===")
        print(f"  text objects ............................ {agg.get('total',0)}")
        print(f"  would overflow naively (1-line, no fit) . {agg.get('naive_overflow',0)}   <- the reported bug")
        print(f"  fixed by wrap ........................... {agg.get('wrapped',0)}")
        print(f"  fixed by shrink_to_fit .................. {agg.get('shrunk',0)}")
        print(f"  contained by clip/ellipsis net ......... {agg.get('clipped',0)}")
        print(f"  fit without change ...................... {agg.get('contained',0)}")
        print(f"  overflow:visible (permitted to spill) .. {agg.get('visible_overflow',0)}")
        bad = agg.get("uncontained", 0) - agg.get("visible_overflow", 0)  # contained-policy spill (must be 0)
        print(f"  text spilling a CONTAINING box .......... {bad}   (must be 0)")
        ok = bad == 0
        print(f"\n  RESULT: {'PASS' if ok else 'FAIL'} — "
              f"{'every box-contained text fits or is clipped to its box' if ok else 'some contained text still overflows'}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
