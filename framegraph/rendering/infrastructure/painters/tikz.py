"""TikzPainter — a TikZ/LaTeX backend implementing the ScenePainter port.

The second adapter for the backend-neutral rendering seam (ADR 0001 slice 3b-5):
the same `Renderer` builder that drives `SvgPainter` can drive this to emit TikZ
instead, consuming the neutral value objects (`Stroke`, `Markers`, colour/`none`
fills) directly — the concrete payoff of neutralizing the painter parameters in
3b-2/3b-3. The page picture opens with `[x=1pt,y=-1pt]` so FrameGraph page space
(top-left origin, +y down) maps straight onto TikZ coordinates, matching the
existing `latex/` transpiler's convention; the hex→xcolor conversion is shared with
that transpiler (`latex.tikz.color_expr`).

Coverage: the geometry primitives (`rect`/`ellipse`/`circle`/`line`/`poly`),
grouping (`group`/`opacity_group`/`transform_group`), images, clip scoping
(`clip_rect`/`clip_ellipse`/`clip_polygon`/`clip_wrap`), the page wrapper
(`new_page`/`document`), and the `Stroke`/`Markers`/transform-op → TikZ formatters
(3b-5a + 3b-5b). Still to come in 3b-5c: SVG path data (`path`, `clip_path_d`),
text (`text_tag`/`text_block`/`text_runs`, which need the document's font macros),
and the SVG-shaped def+ref handle methods (gradient/filter/marker/embedded_svg/
image_pattern). Until complete the adapter is intentionally NOT wired into the
render path (the `latex/` fork still owns LaTeX output).
"""
from __future__ import annotations

import math

from framegraph.rendering.domain.geometry import fnum, num
from framegraph.rendering.infrastructure.latex.tikz import color_expr


class TikzPainter:
    def __init__(self):
        self._defs: list[str] = []          # reserved for gradient/marker defs (3b-5b)
        self._clips: dict[str, str] = {}     # clip id -> TikZ geometry

    # ---- per-page backend state ------------------------------------------- #
    def new_page(self):
        self._defs = []
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
    def _path(opts, geom):
        return f"\\path[{','.join(opts)}] {geom};\n" if opts else f"\\path {geom};\n"

    @staticmethod
    def _draw(opts, geom):
        return f"\\draw[{','.join(opts)}] {geom};\n" if opts else f"\\draw {geom};\n"

    # ---- primitives ------------------------------------------------------- #
    def rect(self, x, y, w, h, fill, stroke, radius=0, fill_opacity=None):
        opts = self._fill_opts(fill, fill_opacity) + self._stroke_opts(stroke)
        if radius:
            opts.append(f"rounded corners={fnum(radius)}pt")
        geom = f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})"
        return self._path(opts, geom)

    def ellipse(self, cx, cy, rx, ry, fill, stroke, fill_opacity=None):
        opts = self._fill_opts(fill, fill_opacity) + self._stroke_opts(stroke)
        geom = f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx)}pt and {fnum(ry)}pt)"
        return self._path(opts, geom)

    def circle(self, cx, cy, r, fill, stroke, fill_opacity=None):
        opts = self._fill_opts(fill, fill_opacity) + self._stroke_opts(stroke)
        geom = f"({fnum(cx)},{fnum(cy)}) circle ({fnum(r)}pt)"
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
            opts = self._fill_opts(fill, fill_opacity, fill_rule) + self._stroke_opts(stroke)
        else:
            opts = self._stroke_opts(stroke)
        tip = self._marker_tip(markers)
        if tip:
            opts.insert(0, tip)
        return self._draw(opts, chain)

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
        (StyleValues.transform_ops) into TikZ scope options."""
        opts = self._transform_opts(transform)
        if not opts:
            return inner
        return f"\\begin{{scope}}[{','.join(opts)}]\n{inner}\\end{{scope}}\n"

    @staticmethod
    def _transform_opts(ops):
        """Neutral transform ops -> TikZ scope options. SVG and TikZ differ here:
        SVG joins `fn(args)`, TikZ uses keyed scope options (shift/rotate/scale/
        slant/cm) and skew takes a tangent, not an angle."""
        opts = []
        for fn, args in ops:
            if fn == "raw":
                if args and args[0]:
                    opts.append(args[0])        # SVG-syntax passthrough (not valid TikZ)
            elif fn == "rotate":
                if len(args) >= 3:
                    opts.append(f"rotate around={{{args[0]}:({args[1]},{args[2]})}}")
                elif args:
                    opts.append(f"rotate={args[0]}")
            elif fn == "translate":
                x = args[0] if args else "0"
                y = args[1] if len(args) > 1 else "0"
                opts.append(f"shift={{({x},{y})}}")
            elif fn == "scale":
                sx = args[0] if args else "1"
                sy = args[1] if len(args) > 1 else sx
                opts.append(f"xscale={sx}")
                opts.append(f"yscale={sy}")
            elif fn == "skewX" and args:
                opts.append(f"xslant={fnum(math.tan(math.radians(num(args[0], 0))))}")
            elif fn == "skewY" and args:
                opts.append(f"yslant={fnum(math.tan(math.radians(num(args[0], 0))))}")
            elif fn == "matrix" and len(args) >= 6:
                opts.append(f"cm={{{args[0]},{args[1]},{args[2]},{args[3]},({args[4]},{args[5]})}}")
        return opts

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

    def clip_wrap(self, inner, clip_id):
        geom = self._clips.get(clip_id, "")
        if not geom:
            return inner
        return f"\\begin{{scope}}\n\\clip {geom};\n{inner}\\end{{scope}}\n"

    # ---- document --------------------------------------------------------- #
    def document(self, w, h, body):
        """Assemble a page's TikZ picture (the LaTeX preamble/scaffold is the
        `latex/` transpiler's job, not the painter's)."""
        return ("\\noindent\\begin{tikzpicture}[x=1pt,y=-1pt]\n"
                f"\\path[use as bounding box] (0,0) rectangle ({fnum(w)},{fnum(h)});\n"
                f"{body}"
                "\\end{tikzpicture}\n")
