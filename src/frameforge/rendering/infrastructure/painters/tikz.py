"""TikzPainter — a TikZ/LaTeX backend implementing the ScenePainter port.

The second adapter for the backend-neutral rendering seam (ADR 0001 slice 3b-5):
the same `Renderer` builder that drives `SvgPainter` can drive this to emit TikZ
instead, consuming the neutral value objects (`Stroke`, `Markers`, colour/`none`
fills) directly — the concrete payoff of neutralizing the painter parameters in
3b-2/3b-3. The page picture opens with `[x=1pt,y=-1pt]` so FrameForge page space
(top-left origin, +y down) maps straight onto TikZ coordinates, matching the
existing `latex/` transpiler's convention; the hex→xcolor conversion is shared with
that transpiler (`latex.tikz.color_expr`).

Coverage: the geometry primitives (`rect`/`ellipse`/`circle`/`line`/`poly`/`path`),
grouping (`group`/`opacity_group`/`transform_group`), images, clip scoping
(`clip_rect`/`clip_ellipse`/`clip_polygon`/`clip_path_d`/`clip_wrap`), gradient
fills (`gradient` returns a `GradientPaint` handle the fill-bearing primitives
render inline as `\\shade`), single-box text (`text_tag` → a `\\node`, with the
font family resolved through a threaded `font_macro`), the page wrapper
(`new_page`/`document`), and the `Stroke`/`Markers`/transform-op/path-data → TikZ
formatters (SVG path data via the shared `tikz_path` module), and the SVG-specific
handle methods as honest TikZ fallbacks (`filter`/`embedded_svg`/`image_pattern`/
`marker`). The adapter now implements the whole `ScenePainter` port **except
`text_block`/`text_runs`**, which still receive a pre-formatted SVG style *string*
(a leak 3b-3's text audit missed) and need that param neutralized to a style dict
— plus the SVG-baseline→TikZ-anchor positioning rework — before they can render
correctly; best done with a LaTeX engine to validate. The CSS text-feature tail,
gradient-on-path, and full radial-centre CSS parsing are also follow-ups. Until
complete the adapter is intentionally NOT wired into the render path (the `latex/`
fork still owns LaTeX output).
"""
from __future__ import annotations

import math
import re

from frameforge.rendering.domain.geometry import fnum, is_point, num
from frameforge.rendering.domain.services.paint_resolver import GradientPaint
from frameforge.rendering.infrastructure.painters.tikz_path import path_data
from frameforge.rendering.infrastructure.latex.tikz import (
    _grad_direction, _grad_orientation, _grad_pct, _parse_hex,
    _user_grad_point, color_expr, ltx_escape,
)


class TikzPainter:
    #: TikZ has no post-draw filter primitive: shadow/glow/blur cannot be
    #: composited here, so the Renderer emits an unsupported-effect warning
    #: per dropped effect instead of losing it silently (#44 / #53).
    supports_filters = False

    def __init__(self, color_resolver=None, font_macro=None):
        # Threaded context for the two methods that need more than geometry:
        # `color_resolver` resolves gradient stop colours; `font_macro` maps a
        # resolved font family to its LaTeX `\newfontfamily` macro (the document
        # scaffold owns the registry). The Renderer supplies both when it drives
        # this backend (3b-5c); without them gradients/fonts degrade gracefully.
        self._color = color_resolver
        self._font_macro = font_macro
        self._clips: dict[str, str] = {}     # clip id -> TikZ geometry

    # ---- per-page backend state ------------------------------------------- #
    def new_page(self):
        self._clips = {}

    # ---- neutral value-object formatters (the TikZ side of the seam) ------ #
    @staticmethod
    def _fill_opts(fill, fill_opacity=None, fill_rule=None):
        """A resolved fill paint → TikZ `fill=` options. Gradient `url(#…)` fills
        are deferred to 3b-5b (the gradient handle method), so they add no fill."""
        if fill is None or fill == "none" or str(fill).startswith("url("):
            return []
        expr, alpha = color_expr(fill)
        if expr is None:
            return []
        opts = [f"fill={expr}"]
        op = fill_opacity if fill_opacity is not None else alpha
        if op is not None:
            opts.append(f"fill opacity={fnum(num(op, 1))}")
        if fill_rule in ("evenodd", "even-odd"):
            opts.append("even odd rule")
        return opts

    @staticmethod
    def _stroke_opts(stroke):
        """A neutral `Stroke` value object → TikZ draw options."""
        if stroke is None:
            return []
        expr, alpha = color_expr(stroke.color)
        if expr is None:
            return []
        opts = [f"draw={expr}"]
        op = stroke.opacity if stroke.opacity is not None else alpha
        if op is not None:
            opts.append(f"draw opacity={fnum(num(op, 1))}")
        opts.append(f"line width={fnum(stroke.width if stroke.width is not None else 1)}pt")
        if stroke.dash:
            seq = [num(d, 0) for d in str(stroke.dash).split()]
            parts = ["on " + fnum(seq[0]) + "pt"]
            for i, d in enumerate(seq[1:], start=1):
                parts.append(("off " if i % 2 else "on ") + fnum(d) + "pt")
            opts.append("dash pattern=" + " ".join(parts))
            if stroke.dashoffset is not None:
                opts.append(f"dash phase={fnum(num(stroke.dashoffset, 0))}pt")
        if stroke.linecap in ("round", "butt", "square"):
            opts.append("line cap=" + ("rect" if stroke.linecap == "square" else stroke.linecap))
        if stroke.linejoin in ("miter", "round", "bevel"):
            opts.append("line join=" + stroke.linejoin)
        if stroke.miterlimit is not None:
            opts.append(f"miter limit={fnum(num(stroke.miterlimit, 4))}")
        return opts

    @staticmethod
    def _marker_tip(markers):
        """A neutral `Markers` value object → a TikZ arrow-tip spec (or '')."""
        if markers is None:
            return ""
        start, end = bool(markers.start), bool(markers.end)
        if start and end:
            return "<->"
        if end:
            return "->"
        if start:
            return "<-"
        return ""

    @staticmethod
    def a11y_wrap(inner, obj):
        """SVG wraps objects in an accessibility `<g role/aria-*>`; TikZ/PDF carries
        no such per-object structure here, so this is a passthrough."""
        return inner

    @staticmethod
    def anchor(align):
        """Neutral align → text-anchor enum (shared convention with SvgPainter); the
        text methods map it to TikZ base-anchors."""
        return {"center": "middle", "right": "end", "end": "middle"}.get(align, "start")

    def style_group(self, inner, attrs, raw=""):
        """CSS compositing wrapper. TikZ supports `opacity` and `visibility:hidden`;
        blend-modes/backdrop/CSS filters/clip-path have no TikZ equivalent and pass
        through (documented fidelity gap)."""
        if attrs.get("visibility") in ("hidden", "collapse"):
            return ""
        opacity = attrs.get("opacity")
        if opacity not in (None, "1", 1):
            return f"\\begin{{scope}}[opacity={opacity}]\n{inner}\\end{{scope}}\n"
        return inner

    # ---- backend-specific handle methods (TikZ fallbacks) ----------------- #
    # These encode SVG's <defs>+url(#id) / <filter> model, which TikZ does not
    # share. Each degrades honestly so a wired TikZ render still produces valid,
    # content-preserving output; full-fidelity equivalents are 3b-5c+ follow-ups.
    def marker(self, color, kind="filled_triangle"):
        # Unused by the builder: arrowheads flow through the neutral Markers value
        # object to line/poly (`_marker_tip`). Present only for port completeness.
        return ""

    def filter_effect(self, kind, params):
        # TikZ has no <filter>; shadow/glow are per-shape there, not a post-wrap.
        return "tikz-filter-noop"

    def filter_wrap(self, inner, filter_id):
        return inner                          # content renders without the filter

    def image_pattern(self, href, x, y, w, h, preserve_aspect_ratio="xMidYMid slice"):
        # An image fill-pattern has no direct TikZ fill; the shape renders unfilled
        # (the background image is dropped). A clipped \includegraphics is a follow-up.
        return None

    def embedded_svg(self, x, y, w, h, *, viewbox, color, title, body):
        # Foreign SVG (e.g. a MathJax render) cannot embed in TikZ; fall back to the
        # accessible title text so the content is not lost.
        cexpr, _ = color_expr(color)
        text_opt = f",text={cexpr}" if cexpr else ""
        return (f"\\node[anchor=center,inner sep=0pt,align=center{text_opt}] at "
                f"({fnum(x + w / 2)},{fnum(y + h / 2)}) {{{ltx_escape(title)}}};\n")

    # ---- gradients (the painter's gradient handle is the GradientPaint VO) - #
    def gradient(self, g):
        """Return this backend's gradient handle: the neutral `GradientPaint` value
        object. Unlike SVG (which registers a `<defs>` entry and returns a url),
        TikZ gradients are shape-coupled, so the spec is carried to the primitive
        and rendered inline as `\\shade` there."""
        return GradientPaint(g)

    def _gradient_stops(self, spec):
        raw = spec.get("stops")
        if not isinstance(raw, list) or len(raw) < 2:
            return None
        stops = []
        for i, s in enumerate(raw):
            if not isinstance(s, dict):
                return None
            resolved = self._color.resolve(s.get("color")) if self._color else s.get("color")
            if not _parse_hex(resolved):        # transparent / non-hex: bail to solid
                return None
            expr, _op = color_expr(resolved)
            stops.append((_grad_pct(s.get("position"), i / (len(raw) - 1)), expr))
        stops.sort(key=lambda s: s[0])
        return stops

    def _first_stop_color(self, spec):
        """Solid fallback colour (the first stop) for an unsupported gradient."""
        raw = spec.get("stops")
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            c = self._color.resolve(raw[0].get("color")) if self._color else raw[0].get("color")
            return c
        return None

    def _gradient_shade(self, spec, x, y, w, h):
        """A linear/radial gradient over the box (x,y,w,h) → `\\shade` primitives,
        or None if unsupported (caller falls back to a solid fill). Ported from the
        latex/ transpiler's proven `_gradient_rect`/`_radial_gradient_rect`."""
        if not isinstance(spec, dict) or w <= 0 or h <= 0:
            return None
        kind = str(spec.get("kind"))
        stops = self._gradient_stops(spec)
        if stops is None:
            return None
        if kind in ("radial", "radial-gradient", "conic"):
            radius = spec.get("radius")
            user_at = _user_grad_point(spec.get("at")) if kind != "conic" else None
            if (user_at is not None and isinstance(radius, (int, float))
                    and not isinstance(radius, bool) and radius > 0):
                # A1 user-space radial: page coordinates map 1:1 (exact, circular).
                cx, cy = user_at
                rx = ry = float(radius)
            else:
                cx, cy = self._radial_center(spec.get("at"), x, y, w, h)
                rx = max(abs(cx - x), abs(x + w - cx))
                ry = max(abs(cy - y), abs(y + h - cy))
                if str(spec.get("shape") or "ellipse").strip().lower() == "circle":
                    rx = ry = max(rx, ry)
            clip = f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})"
            out = []
            for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
                if p1 <= p0:
                    continue
                geom = f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx * p1)}pt and {fnum(ry * p1)}pt)"
                out.insert(0, f"\\shade[inner color={c0},outer color={c1}] {geom};\n")
            return (f"\\begin{{scope}}\n\\clip {clip};\n{''.join(out)}\\end{{scope}}\n"
                    if out else None)
        if kind not in ("linear", "linear-gradient"):
            return None
        axis, reverse = _grad_orientation(_grad_direction(spec))
        if reverse:
            stops = [(1.0 - p, c) for p, c in reversed(stops)]
        out = []
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p1 <= p0:
                continue
            if axis == "h":
                geom = (f"({fnum(x + p0 * w)},{fnum(y)}) rectangle "
                        f"({fnum(x + p1 * w)},{fnum(y + h)})")
                out.append(f"\\shade[left color={c0},right color={c1}] {geom};\n")
            else:
                geom = (f"({fnum(x)},{fnum(y + p0 * h)}) rectangle "
                        f"({fnum(x + w)},{fnum(y + p1 * h)})")
                out.append(f"\\shade[top color={c0},bottom color={c1}] {geom};\n")
        return "".join(out) or None

    @staticmethod
    def _radial_center(value, x, y, w, h):
        if is_point(value):
            return x + num(value[0], 0), y + num(value[1], 0)
        return x + w / 2, y + h / 2       # full CSS-keyword centres land in 3b-5c

    @staticmethod
    def _points_bbox(pts):
        xs, ys = [], []
        for p in pts:
            a, _, b = p.partition(",")
            xs.append(num(a, 0))
            ys.append(num(b, 0))
        if not xs:
            return 0.0, 0.0, 0.0, 0.0
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)

    def _gradient_or_clip(self, spec, geom, x, y, w, h, stroke):
        """Emit a gradient fill for a non-rect shape: `\\shade` over the bbox clipped
        to the shape geometry, then the stroke. Falls back to a solid first stop."""
        shade = self._gradient_shade(spec, x, y, w, h)
        stroke_opts = self._stroke_opts(stroke)
        if shade is None:
            return self._path(self._fill_opts(self._first_stop_color(spec)) + stroke_opts, geom)
        body = f"\\begin{{scope}}\n\\clip {geom};\n{shade}\\end{{scope}}\n"
        return body + (self._path(stroke_opts, geom) if stroke_opts else "")

    @staticmethod
    def _path(opts, geom):
        return f"\\path[{','.join(opts)}] {geom};\n" if opts else f"\\path {geom};\n"

    @staticmethod
    def _draw(opts, geom):
        return f"\\draw[{','.join(opts)}] {geom};\n" if opts else f"\\draw {geom};\n"

    # ---- primitives ------------------------------------------------------- #
    def rect(self, x, y, w, h, fill, stroke, radius=0, fill_opacity=None):
        geom = f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})"
        if isinstance(fill, GradientPaint):
            shade = self._gradient_shade(fill.spec, x, y, w, h)
            if shade is not None:
                stroke_opts = self._stroke_opts(stroke)
                return shade + (self._path(stroke_opts, geom) if stroke_opts else "")
            fill = self._first_stop_color(fill.spec)   # solid fallback
        opts = self._fill_opts(fill, fill_opacity) + self._stroke_opts(stroke)
        if radius:
            opts.append(f"rounded corners={fnum(radius)}pt")
        return self._path(opts, geom)

    def ellipse(self, cx, cy, rx, ry, fill, stroke, fill_opacity=None):
        geom = f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx)}pt and {fnum(ry)}pt)"
        if isinstance(fill, GradientPaint):
            return self._gradient_or_clip(fill.spec, geom, cx - rx, cy - ry, rx * 2, ry * 2, stroke)
        opts = self._fill_opts(fill, fill_opacity) + self._stroke_opts(stroke)
        return self._path(opts, geom)

    def circle(self, cx, cy, r, fill, stroke, fill_opacity=None):
        geom = f"({fnum(cx)},{fnum(cy)}) circle ({fnum(r)}pt)"
        if isinstance(fill, GradientPaint):
            return self._gradient_or_clip(fill.spec, geom, cx - r, cy - r, r * 2, r * 2, stroke)
        opts = self._fill_opts(fill, fill_opacity) + self._stroke_opts(stroke)
        return self._path(opts, geom)

    def line(self, x1, y1, x2, y2, stroke, markers=None, extra=""):
        opts = self._stroke_opts(stroke)
        tip = self._marker_tip(markers)
        if tip:
            opts.insert(0, tip)
        geom = f"({fnum(x1)},{fnum(y1)}) -- ({fnum(x2)},{fnum(y2)})"
        return self._draw(opts, geom)

    def poly(self, tag, points, fill, stroke, fill_opacity=None, fill_rule=None,
             markers=None, extra=""):
        pts = [p for p in points.split() if "," in p]
        chain = " -- ".join(f"({p})" for p in pts)
        closed = tag == "polygon"
        if closed:
            chain += " -- cycle"
            if isinstance(fill, GradientPaint):
                bx, by, bw, bh = self._points_bbox(pts)
                return self._gradient_or_clip(fill.spec, chain, bx, by, bw, bh, stroke)
            opts = self._fill_opts(fill, fill_opacity, fill_rule) + self._stroke_opts(stroke)
        else:
            opts = self._stroke_opts(stroke)
        tip = self._marker_tip(markers)
        if tip:
            opts.insert(0, tip)
        return self._draw(opts, chain)

    def path(self, d, fill, stroke, fill_opacity=None, fill_rule=None, markers=None, extra=""):
        geom = path_data(d)
        if not geom:
            return ""
        if isinstance(fill, GradientPaint):
            # gradient-on-path needs a path bbox to shade; solid first-stop for now
            fill = self._first_stop_color(fill.spec)
        opts = self._fill_opts(fill, fill_opacity, fill_rule) + self._stroke_opts(stroke)
        tip = self._marker_tip(markers)
        if tip:                          # arrows need a drawing op
            opts.insert(0, tip)
            return self._draw(opts, geom)
        return self._path(opts, geom)

    # ---- grouping --------------------------------------------------------- #
    def group(self, inner, translate=None):
        if translate:
            tx, ty = translate
            return (f"\\begin{{scope}}[shift={{({fnum(tx)},{fnum(ty)})}}]\n"
                    f"{inner}\\end{{scope}}\n")
        return inner

    def opacity_group(self, inner, opacity):
        return f"\\begin{{scope}}[opacity={fnum(num(opacity, 1))}]\n{inner}\\end{{scope}}\n"

    def transform_group(self, inner, transform):
        """Wrap content in a TikZ scope formatting the neutral transform op list
        (StyleValues.transform_ops) into TikZ scope options.

        `transform shape` is REQUIRED: a bare TikZ scope transform moves the
        anchor coordinates of `\\node`s but leaves the glyphs at their original
        size/orientation, so scaled/rotated text renders untransformed (issue
        #53). With it the whole shape — text included — obeys the scope."""
        opts = self._transform_opts(transform)
        if not opts:
            return inner
        return (f"\\begin{{scope}}[transform shape,{','.join(opts)}]\n"
                f"{inner}\\end{{scope}}\n")

    @classmethod
    def _transform_opts(cls, ops):
        """Neutral transform ops -> TikZ scope options. SVG and TikZ differ here:
        SVG joins `fn(args)`, TikZ uses keyed scope options (shift/rotate/scale/
        slant/cm) and skew takes a tangent, not an angle.

        A `raw` op carries an SVG-syntax transform STRING (the neutral layer keeps
        string transforms raw so the SVG backend stays byte-identical); TikZ cannot
        consume SVG syntax, so parse it into `fn(args)` and format each the same
        way as the structured ops (issue #53 — invalid `scale(0.5)` was emitted
        verbatim and silently ignored by the TeX engine)."""
        opts = []
        for fn, args in ops:
            if fn == "raw":
                for pfn, pargs in cls._parse_svg_transform(args[0] if args else ""):
                    opts.extend(cls._tikz_opt(pfn, pargs))
            else:
                opts.extend(cls._tikz_opt(fn, args))
        return opts

    @staticmethod
    def _parse_svg_transform(text):
        """`scale(0.5) rotate(30) translate(8, 6)` -> [(fn, [args...]), ...].
        Comma/space-separated args; a trailing 'deg' is already stripped upstream."""
        out = []
        for m in re.finditer(r"([a-zA-Z]+)\s*\(([^)]*)\)", str(text or "")):
            fn = m.group(1)
            args = [a for a in re.split(r"[,\s]+", m.group(2).strip()) if a]
            out.append((fn, args))
        return out

    @staticmethod
    def _tikz_opt(fn, args):
        """One transform function -> TikZ scope option strings."""
        if fn == "rotate":
            if len(args) >= 3:
                return [f"rotate around={{{args[0]}:({args[1]},{args[2]})}}"]
            return [f"rotate={args[0]}"] if args else []
        if fn in ("translate", "translateX", "translateY"):
            if fn == "translateX":
                x, y = (args[0] if args else "0"), "0"
            elif fn == "translateY":
                x, y = "0", (args[0] if args else "0")
            else:
                x = args[0] if args else "0"
                y = args[1] if len(args) > 1 else "0"
            return [f"shift={{({x},{y})}}"]
        if fn in ("scale", "scaleX", "scaleY"):
            if fn == "scaleX":
                sx, sy = (args[0] if args else "1"), "1"
            elif fn == "scaleY":
                sx, sy = "1", (args[0] if args else "1")
            else:
                sx = args[0] if args else "1"
                sy = args[1] if len(args) > 1 else sx
            return [f"xscale={sx}", f"yscale={sy}"]
        if fn == "skewX" and args:
            return [f"xslant={fnum(math.tan(math.radians(num(args[0], 0))))}"]
        if fn == "skewY" and args:
            return [f"yslant={fnum(math.tan(math.radians(num(args[0], 0))))}"]
        if fn == "matrix" and len(args) >= 6:
            return [f"cm={{{args[0]},{args[1]},{args[2]},{args[3]},"
                    f"({args[4]},{args[5]})}}"]
        return []

    # ---- image ------------------------------------------------------------ #
    def image(self, x, y, w, h, href, preserve_aspect_ratio="xMidYMid meet"):
        opts = [f"width={fnum(w)}pt", f"height={fnum(h)}pt"]
        if preserve_aspect_ratio != "none":
            opts.append("keepaspectratio")
        return (f"\\node[anchor=center,inner sep=0pt] at "
                f"({fnum(x + w / 2)},{fnum(y + h / 2)}) "
                f"{{\\includegraphics[{','.join(opts)}]{{\\detokenize{{{href}}}}}}};\n")

    # ---- clipping (id -> geometry registry; clip_wrap emits the scope) ----- #
    def _register_clip(self, geom):
        cid = f"clip{len(self._clips) + 1}"
        self._clips[cid] = geom
        return cid

    def clip_rect(self, x, y, w, h):
        return self._register_clip(
            f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})")

    def clip_ellipse(self, cx, cy, rx, ry):
        return self._register_clip(
            f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx)}pt and {fnum(ry)}pt)")

    def clip_polygon(self, points):
        pts = [p for p in points.split() if "," in p]
        return self._register_clip(" -- ".join(f"({p})" for p in pts) + " -- cycle")

    def clip_path_d(self, d):
        return self._register_clip(path_data(d))

    def clip_wrap(self, inner, clip_id):
        geom = self._clips.get(clip_id, "")
        if not geom:
            return inner
        return f"\\begin{{scope}}\n\\clip {geom};\n{inner}\\end{{scope}}\n"

    # ---- text (needs the threaded font-macro context) --------------------- #
    def _font(self, st):
        """The resolved style dict (`family`/`size`/`weight`/`italic`) → a LaTeX
        font command, prefixed with the family's `\\newfontfamily` macro when the
        document supplied a `font_macro` resolver. The long tail of CSS font
        features (variants/features/letter-spacing) is 3b-5c follow-up."""
        size = num(st.get("size"), 12) or 12
        family = st.get("family")
        macro = self._font_macro(family) if (self._font_macro and family) else ""
        font = macro + f"\\fontsize{{{fnum(size)}}}{{{fnum(size * 1.12)}}}\\selectfont"
        weight = st.get("weight")
        if str(weight).strip().lower() == "bold" or (num(weight, 0) or 0) >= 600:
            font += "\\bfseries"
        if st.get("italic"):
            font += "\\itshape"
        return font

    @staticmethod
    def _text_y(st, y, h):
        size = num(st.get("size"), 12) or 12
        valign = str(st.get("valign") or "").strip().lower()
        if valign in ("top", "text-top", "super"):
            return y + size / 2
        if valign in ("bottom", "text-bottom", "sub"):
            return y + max(0, h - size / 2)
        return y + h / 2

    def text_tag(self, x, y, w, h, content, st, vcenter=None, text_len=None):
        """A single text box → a TikZ `\\node` (anchor + font + colour), following
        the proven latex/ convention: vertical-centred via `_text_y`, horizontal
        anchor from `align`. Multi-line/spans (`text_block`/`text_runs`) and the
        CSS text-feature tail are 3b-5c follow-up."""
        if content is None or content == "":
            return ""
        align = str(st.get("align") or "left").strip().lower()
        if align in ("center", "middle"):
            ax, anchor, talign = x + w / 2, "center", "center"
        elif align in ("right", "end"):
            ax, anchor, talign = x + w, "east", "flush right"
        else:
            ax, anchor, talign = x, "west", "flush left"
        ay = self._text_y(st, y, h)
        opts = [f"anchor={anchor}", "inner sep=0pt", f"font={self._font(st)}",
                f"text width={fnum(max(w, 1))}pt", f"align={talign}"]
        cexpr, op = color_expr(st.get("color"))
        if cexpr:
            opts.append(f"text={cexpr}")
        if op is not None:
            opts.append(f"text opacity={fnum(op)}")
        return f"\\node[{','.join(opts)}] at ({fnum(ax)},{fnum(ay)}) {{{ltx_escape(content)}}};\n"

    @staticmethod
    def _base_anchor(anchor):
        # SVG text-anchor enum -> TikZ baseline anchor (so the baseline lands on the
        # builder-computed y, matching the SVG baseline model).
        return {"middle": "base", "end": "base east"}.get(anchor, "base west")

    def text_block(self, base_y, anchor, st, size, lines, tx, line_dy, justify_width=None,
                   justifies=None, baseline=None):
        """Multi-line text: one `\\node` per line on the baseline grid (base_y +
        i·line_dy). Structurally implemented; visual baseline/leading fidelity is
        pending a LaTeX-engine validation pass (none in this environment)."""
        # `baseline` set (a centred single line seated on the box centre, the SVG
        # dominant-baseline path) → anchor the node on its vertical `mid` instead
        # of the baseline so the number centres in TikZ too.
        va = self._base_anchor(anchor)
        if baseline:
            va = va.replace("base", "mid")
        opts = [f"anchor={va}", "inner sep=0pt", f"font={self._font(st)}"]
        cexpr, op = color_expr(st.get("color"))
        if cexpr:
            opts.append(f"text={cexpr}")
        if op is not None:
            opts.append(f"text opacity={fnum(op)}")
        opt_str = ",".join(opts)
        return "".join(
            f"\\node[{opt_str}] at ({fnum(tx)},{fnum(base_y + i * line_dy)}) {{{ltx_escape(ln)}}};\n"
            for i, ln in enumerate(lines))

    def text_runs(self, base_y, anchor, tx, base_st, size, runs, text_len=None, baseline=None):
        """A single baseline of inline styled runs (rich `text.spans`) as one node
        whose body concatenates per-run font/colour groups. Structurally
        implemented; inline-flow fidelity pending LaTeX-engine validation."""
        va = self._base_anchor(anchor).replace("base", "mid") if baseline else self._base_anchor(anchor)
        opts = [f"anchor={va}", "inner sep=0pt", f"font={self._font(base_st)}"]
        body = []
        for text, run_st in runs:
            cexpr, _op = color_expr(run_st.get("color"))
            color = f"\\color{{{cexpr}}}" if cexpr else ""
            body.append(f"{{{self._font(run_st)}{color}{ltx_escape(text)}}}")
        return f"\\node[{','.join(opts)}] at ({fnum(tx)},{fnum(base_y)}) {{{''.join(body)}}};\n"

    # ---- document --------------------------------------------------------- #
    def document(self, w, h, body, lang=None, title=None, desc=None,
                 background=None):
        """Assemble a page's TikZ picture (the LaTeX preamble/scaffold is the
        `latex/` transpiler's job, not the painter's). `lang`/`title`/`desc` are
        SVG-root a11y attributes with no TikZ equivalent — ignored. `background`
        paints an authored page fill behind the content; absent, the page keeps
        the surrounding LaTeX paper (this painter never injected white)."""
        bg = ""
        if background:
            opts = self._fill_opts(background)
            if opts:
                bg = (f"\\path[{','.join(opts)}] "
                      f"(0,0) rectangle ({fnum(w)},{fnum(h)});\n")
        return ("\\noindent\\begin{tikzpicture}[x=1pt,y=-1pt]\n"
                f"\\path[use as bounding box] (0,0) rectangle ({fnum(w)},{fnum(h)});\n"
                f"{bg}{body}"
                "\\end{tikzpicture}\n")
