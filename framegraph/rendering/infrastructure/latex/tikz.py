"""tikz — FrameGraph figure object graph → TikZ, plus LaTeX text/colour helpers.

`FigureTikz.render(object)` returns the *body* of a `tikzpicture` (no wrapper); the
document builder opens the picture with `[x=1pt,y=-1pt]` so FrameGraph page-space
(top-left origin, +y down) maps directly and these emitters need no per-call flip.

Only the primitives the fixtures actually compose figures from are handled
faithfully — rect / ellipse / circle / line / polyline / polygon / text / group
(symbol `use` is pre-expanded to `group` by `normalize_doc`). Anything else is
counted in `.skipped` and dropped, mirroring the SVG proxy's tolerance.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import fnum, is_point, num

# ---- LaTeX text escaping --------------------------------------------------- #
# Order matters: backslash first, then the brace/special set. Unicode (Greek,
# ½/⅔, −, ×, ℏ, superscripts …) passes through verbatim — the document selects a
# broad-coverage Unicode font (DejaVu Sans) via fontspec so it renders.
_LTX = [
    ("\\", r"\textbackslash{}"), ("{", r"\{"), ("}", r"\}"),
    ("$", r"\$"), ("&", r"\&"), ("#", r"\#"), ("%", r"\%"),
    ("_", r"\_"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
]


def ltx_escape(s) -> str:
    out = "" if s is None else str(s)
    for a, b in _LTX:
        out = out.replace(a, b)
    return out


def ltx_url_escape(s) -> str:
    """Escape a URL for hyperref's mandatory argument."""
    return ltx_escape(s)


def _parse_hex(s):
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s.startswith("#"):
        return None
    h = s[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        return None
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255.0 if len(h) == 8 else None
    except ValueError:
        return None
    return r, g, b, a


def color_expr(resolved):
    """A resolved paint (hex / 'none' / xcolor name / None) → (tikz-colour-expr, opacity).

    Hex `#RRGGBB[AA]` → an inline xcolor `{rgb,255:…}` expression (no preamble
    coordination needed) plus an optional 0–1 opacity decoded from the alpha byte
    (every translucent overlay region in the fixtures is an 8-digit hex)."""
    if resolved is None or resolved == "none":
        return None, None
    rgb = _parse_hex(resolved)
    if rgb:
        r, g, b, a = rgb
        return f"{{rgb,255:red,{r};green,{g};blue,{b}}}", a
    return str(resolved), None     # a bare xcolor name (white/black/…)


class FigureTikz:
    def __init__(self, color_resolver, text_style_resolver, stroke_styles=None):
        self._color = color_resolver
        self._ts = text_style_resolver
        self._stroke_styles = stroke_styles or {}
        self.skipped = 0

    # -- entry ------------------------------------------------------------- #
    def render(self, obj) -> str:
        if not isinstance(obj, dict):
            return ""
        return self._draw(obj)

    def _children(self, objs):
        # Document order already matches z in the fixtures; a stable sort by z
        # makes it robust without reordering equal-z siblings.
        kids = [o for o in (objs or []) if isinstance(o, dict)]
        return sorted(kids, key=lambda o: num(o.get("z"), 0) or 0)

    def _draw(self, o) -> str:
        t = o.get("type")
        fn = getattr(self, f"_draw_{t}", None) if isinstance(t, str) else None
        if fn is None:
            self.skipped += 1
            return ""
        try:
            return fn(o)
        except Exception:
            self.skipped += 1
            return ""

    # -- grouping ---------------------------------------------------------- #
    def _draw_group(self, o) -> str:
        body = "".join(self._draw(ch) for ch in self._children(o.get("children")))
        box = o.get("box")
        if is_point(box[:2]) if isinstance(box, list) and len(box) >= 2 else False:
            dx, dy = num(box[0], 0), num(box[1], 0)
            if dx or dy:
                return f"\\begin{{scope}}[shift={{({fnum(dx)},{fnum(dy)})}}]\n{body}\\end{{scope}}\n"
        return body

    def _draw_container(self, o) -> str:        # alias used by some fixtures
        return self._draw_group(o)

    # -- shapes ------------------------------------------------------------ #
    def _fill_opts(self, o):
        expr, op = color_expr(self._color.resolve(o.get("fill")))
        opts = []
        if expr is not None:
            opts.append(f"fill={expr}")
            if op is not None:
                opts.append(f"fill opacity={fnum(op)}")
        return opts

    def _stroke_opts(self, o, default_color=None):
        sv, ssv = o.get("stroke"), o.get("stroke_style")
        bundle = self._stroke_styles.get(ssv, {}) if isinstance(ssv, str) else (ssv or {})
        if not isinstance(bundle, dict):
            bundle = {}
        col = self._color.resolve(sv) if isinstance(sv, str) else None
        if not col or col == "none":
            col = self._color.resolve(bundle.get("stroke") or bundle.get("color"))
        opts, tip = [], self._arrow_tip(bundle)
        if (not col or col == "none") and not tip:
            return opts
        col = col if (col and col != "none") else (default_color or "#000000")
        expr, op = color_expr(col)
        opts.append(f"draw={expr}")
        if op is not None:
            opts.append(f"draw opacity={fnum(op)}")
        width = num(bundle.get("stroke_width", bundle.get("width")), None)
        opts.append(f"line width={fnum(width if width is not None else 1)}pt")
        dash = bundle.get("stroke_dasharray") or bundle.get("dash")
        if isinstance(dash, list) and dash:
            seq = [num(d, 0) for d in dash]
            parts = ["on " + fnum(seq[0]) + "pt"]
            for i, d in enumerate(seq[1:], start=1):
                parts.append(("off " if i % 2 else "on ") + fnum(d) + "pt")
            opts.append("dash pattern=" + " ".join(parts))
        cap = bundle.get("stroke_linecap")
        if cap in ("round", "butt", "square"):
            opts.append("line cap=" + ("rect" if cap == "square" else cap))
        if tip:
            opts.insert(0, tip)
        return opts

    @staticmethod
    def _arrow_tip(bundle):
        def on(v):
            return v is True or (isinstance(v, str) and v)
        s, e = on(bundle.get("arrow_start")), on(bundle.get("arrow_end"))
        if s and e:
            return "<->"
        if e:
            return "->"
        if s:
            return "<-"
        return ""

    @staticmethod
    def _path(opts, geom):
        cmd = "\\path" if not any(o for o in opts) else "\\path"
        return f"{cmd}[{','.join(opts)}] {geom};\n" if opts else f"\\path {geom};\n"

    def _draw_rect(self, o) -> str:
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        opts = self._fill_opts(o) + self._stroke_opts(o)
        r = num(o.get("radius"), 0) or 0
        if r:
            opts.append(f"rounded corners={fnum(r)}pt")
        geom = f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})"
        return self._path(opts, geom)

    def _draw_ellipse(self, o) -> str:
        c = o.get("center") or [0, 0]
        cx, cy = num(c[0], 0), num(c[1], 0)
        rx, ry = num(o.get("rx"), 0), num(o.get("ry"), 0)
        box = o.get("box")
        if not rx and isinstance(box, list) and len(box) >= 4:
            cx, cy = num(box[0], 0) + num(box[2], 0) / 2, num(box[1], 0) + num(box[3], 0) / 2
            rx, ry = num(box[2], 0) / 2, num(box[3], 0) / 2
        opts = self._fill_opts(o) + self._stroke_opts(o)
        geom = f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx)}pt and {fnum(ry)}pt)"
        return self._path(opts, geom)

    def _draw_circle(self, o) -> str:
        c = o.get("center") or [0, 0]
        r = num(o.get("r"), 0)
        opts = self._fill_opts(o) + self._stroke_opts(o)
        geom = f"({fnum(num(c[0], 0))},{fnum(num(c[1], 0))}) circle ({fnum(r)}pt)"
        return self._path(opts, geom)

    def _draw_line(self, o) -> str:
        fr, to = o.get("from"), o.get("to")
        if not (is_point(fr) and is_point(to)):
            return ""
        opts = self._stroke_opts(o, default_color="#000000")
        geom = f"({fnum(num(fr[0], 0))},{fnum(num(fr[1], 0))}) -- ({fnum(num(to[0], 0))},{fnum(num(to[1], 0))})"
        return f"\\draw[{','.join(opts)}] {geom};\n" if opts else f"\\draw {geom};\n"

    def _poly_points(self, o):
        return [(num(p[0], 0), num(p[1], 0)) for p in (o.get("points") or []) if is_point(p)]

    def _draw_polyline(self, o) -> str:
        pts = self._poly_points(o)
        if not pts:
            return ""
        opts = self._stroke_opts(o, default_color="#000000")
        if o.get("closed"):
            opts = self._fill_opts(o) + opts
        chain = " -- ".join(f"({fnum(x)},{fnum(y)})" for x, y in pts)
        if o.get("closed"):
            chain += " -- cycle"
        return f"\\draw[{','.join(opts)}] {chain};\n" if opts else f"\\draw {chain};\n"

    def _draw_polygon(self, o) -> str:
        pts = self._poly_points(o)
        if not pts:
            return ""
        opts = self._fill_opts(o) + self._stroke_opts(o)
        chain = " -- ".join(f"({fnum(x)},{fnum(y)})" for x, y in pts) + " -- cycle"
        return self._path(opts, chain)

    # -- text -------------------------------------------------------------- #
    def _draw_text(self, o) -> str:
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ""
        content = o.get("text")
        if content is None and isinstance(o.get("spans"), list):
            content = "".join(s if isinstance(s, str) else (s.get("text", "") if isinstance(s, dict) else "")
                              for s in o["spans"])
        if content is None or content == "":
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        st = self._ts.resolve(o.get("style"))
        align = st.get("align") or "left"
        if align in ("center", "middle"):
            ax, anchor, talign = x + w / 2, "center", "center"
        elif align in ("right", "end"):
            ax, anchor, talign = x + w, "east", "flush right"
        else:
            ax, anchor, talign = x, "west", "flush left"
        ay = y + h / 2
        size = st.get("size", 12) or 12
        font = f"\\fontsize{{{fnum(size)}}}{{{fnum(size * 1.12)}}}\\selectfont"
        if st.get("bold"):
            font += "\\bfseries"
        if st.get("italic"):
            font += "\\itshape"
        opts = [f"anchor={anchor}", "inner sep=0pt", f"text width={fnum(max(w, 1))}pt",
                f"align={talign}", f"font={font}"]
        cexpr, _ = color_expr(st.get("color"))
        if cexpr:
            opts.append(f"text={cexpr}")
        return f"\\node[{','.join(opts)}] at ({fnum(ax)},{fnum(ay)}) {{{ltx_escape(content)}}};\n"
