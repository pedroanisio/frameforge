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

import math
import re

from framegraph.rendering.domain.geometry import fnum, is_point, num
from framegraph.rendering.domain.services.effect_resolver import EffectResolver

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


def _grad_pct(v, default):
    """A gradient stop `position` ("58%", 0.58, 58) to a 0-1 fraction."""
    if v is None:
        return default
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return v / 100.0 if v > 1 else float(v)
    s = str(v).strip()
    pct = s.endswith("%")
    try:
        f = float(s.rstrip("%"))
    except ValueError:
        return default
    return f / 100.0 if (pct or f > 1) else f


def _grad_angle(v, default=180.0):
    """A CSS gradient `angle` ("90deg", 155) to degrees (0=up, 90=right, 180=down)."""
    if v is None or isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().lower().replace("deg", "").strip())
    except ValueError:
        return default


def _grad_orientation(angle):
    """CSS angle to (axis, reversed): which way the stops run across the box."""
    a = angle % 360
    if 45 <= a < 135:
        return "h", False          # right: stop 0 at the left edge
    if 225 <= a < 315:
        return "h", True           # left
    if 135 <= a < 225:
        return "v", False          # bottom: stop 0 at the top edge
    return "v", True               # top


class FigureTikz:
    def __init__(self, color_resolver, text_style_resolver, stroke_styles=None, asset_path=None, font_macro=None):
        self._color = color_resolver
        self._ts = text_style_resolver
        self._stroke_styles = stroke_styles or {}
        self._effect = EffectResolver(color_resolver)
        self._asset_path = asset_path
        self._font_macro = font_macro
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
        if self._is_hidden(o):
            return ""
        t = o.get("type")
        fn = getattr(self, f"_draw_{t.replace('.', '_')}", None) if isinstance(t, str) else None
        if fn is None:
            self.skipped += 1
            return ""
        try:
            body = fn(o)
            body = body + self._side_borders(o) if body else ""
            body = self._clip_scope(o, body) if body else ""
            return self._wrap_object(o, body) if body else ""
        except Exception:
            self.skipped += 1
            return ""

    def _is_hidden(self, o):
        style = self._style_dict(o)
        visibility = o.get("visibility", style.get("visibility"))
        display = o.get("display", style.get("display"))
        hidden = visibility is not None and str(visibility).strip().lower() in ("hidden", "collapse")
        no_display = display is not None and str(display).strip().lower() == "none"
        return hidden or no_display

    def _style_dict(self, o):
        return self._resolve_style_ref(o.get("style"))

    def _resolve_style_ref(self, ref, _seen=None):
        _seen = set() if _seen is None else set(_seen)
        text_styles = getattr(self._ts, "text_styles", {}) or {}
        styles = getattr(self._ts, "styles", {}) or {}
        if isinstance(ref, str):
            if ref in _seen:
                return {}
            _seen.add(ref)
            return self._resolve_style_ref(text_styles.get(ref) or styles.get(ref) or {}, _seen)
        if not isinstance(ref, dict):
            return {}
        cls = ref.get("class") or ref.get("class_")
        merged = {}
        for name in ([cls] if isinstance(cls, str) else (cls or [])):
            merged.update(self._resolve_style_ref(name, _seen))
        merged.update(ref)
        return merged

    def _wrap_object(self, o, body):
        opts = []
        style = self._style_dict(o)
        isolation = o.get("isolation")
        if isolation in (None, "auto"):
            isolation = style.get("isolation")
        if str(isolation or "").strip().lower() == "isolate":
            opts.append("transparency group")
        blend_mode = self._blend_mode(style.get("mix_blend_mode") or self._css_decl(style, "mix-blend-mode"))
        if blend_mode:
            opts.append(f"blend mode={blend_mode}")
        opacity = o.get("opacity")
        if opacity in (None, 1):
            opacity = style.get("opacity")
        if opacity in (None, 1):
            opacity = self._opacity_filter_value(self._css_decl(style, "opacity"))
        filter_opacity = self._filter_opacity(style.get("filter"), self._css_decl(style, "filter"))
        if filter_opacity is not None:
            opacity = num(opacity, 1) * filter_opacity
        if opacity not in (None, 1):
            opts.append(f"opacity={fnum(num(opacity, 1))}")
        transform = self._tikz_transform(o)
        if transform:
            opts += transform
        return f"\\begin{{scope}}[{','.join(opts)}]\n{body}\\end{{scope}}\n" if opts else body

    @staticmethod
    def _blend_mode(value):
        if value in (None, False, "normal", ""):
            return None
        mode = str(value).strip().lower().replace("_", "-")
        allowed = {
            "multiply", "screen", "overlay", "darken", "lighten", "color-dodge",
            "color-burn", "hard-light", "soft-light", "difference", "exclusion",
            "hue", "saturation", "color", "luminosity",
        }
        return mode.replace("-", " ") if mode in allowed else None

    def _filter_opacity(self, *values):
        opacities = []
        for value in values:
            if value in (None, False, "none", ""):
                continue
            if isinstance(value, str):
                for raw in re.findall(r"opacity\(\s*([^)]+?)\s*\)", value, flags=re.I):
                    parsed = self._opacity_filter_value(raw)
                    if parsed is not None:
                        opacities.append(parsed)
                continue
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, dict):
                    name = item.get("fn") or item.get("kind") or item.get("name")
                    if str(name or "").strip().lower() != "opacity":
                        continue
                    parsed = self._opacity_filter_value(item.get("value", 1))
                    if parsed is not None:
                        opacities.append(parsed)
                else:
                    parsed = self._opacity_filter_value(item)
                    if parsed is not None:
                        opacities.append(parsed)
        if not opacities:
            return None
        opacity = 1.0
        for value in opacities:
            opacity *= value
        return opacity

    @staticmethod
    def _css_decl(style, name):
        if not isinstance(style, dict):
            return None
        css = style.get("css")
        if not isinstance(css, str):
            return None
        target = name.strip().lower()
        for decl in css.split(";"):
            if ":" not in decl:
                continue
            key, value = decl.split(":", 1)
            if key.strip().lower() == target:
                value = value.strip()
                return value or None
        return None

    @staticmethod
    def _opacity_filter_value(value):
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            raw = float(value)
        elif isinstance(value, str):
            s = value.strip()
            is_percent = s.endswith("%")
            try:
                raw = float(s.rstrip("%"))
            except ValueError:
                return None
            if is_percent:
                raw /= 100.0
        else:
            return None
        return max(0.0, min(raw, 1.0))

    def _clip_scope(self, o, body):
        geom = self._clip_geom(o)
        if not geom:
            return body
        return f"\\begin{{scope}}\n\\clip {geom};\n{body}\\end{{scope}}\n"

    def _clip_geom(self, o):
        spec = o.get("clip")
        style = self._style_dict(o)
        if spec in (None, False, "none"):
            spec = style.get("clip_path")
        if spec in (None, False, "none"):
            css_clip = self._css_decl(style, "clip-path")
            if css_clip:
                return self._css_clip_geom(o, css_clip)
        if spec in (None, False, "none"):
            return None
        shape, args = None, {}
        if isinstance(spec, str):
            shape = spec
        elif isinstance(spec, dict):
            shape = spec.get("shape") or spec.get("kind") or spec.get("type")
            args = spec.get("args") if isinstance(spec.get("args"), dict) else spec
        if not shape:
            return None
        shape = str(shape).replace("_", "-")
        box = self._box(o)
        if shape in ("ellipse", "circle"):
            center = args.get("center") if isinstance(args, dict) else None
            if is_point(center):
                cx, cy = num(center[0], 0), num(center[1], 0)
            elif box:
                cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
            else:
                return None
            if shape == "circle":
                r = num(args.get("r"), None) if isinstance(args, dict) else None
                if r is None and box:
                    r = min(box[2], box[3]) / 2
                return f"({fnum(cx)},{fnum(cy)}) circle ({fnum(r or 0)}pt)"
            rx = num(args.get("rx"), None) if isinstance(args, dict) else None
            ry = num(args.get("ry"), None) if isinstance(args, dict) else None
            if (rx is None or ry is None) and box:
                rx, ry = box[2] / 2, box[3] / 2
            return f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx or 0)}pt and {fnum(ry or 0)}pt)"
        if shape in ("rect", "inset"):
            if not box:
                return None
            x, y, w, h = box
            if shape == "inset" and isinstance(args, dict):
                top = num(args.get("top"), 0) or 0
                right = num(args.get("right"), 0) or 0
                bottom = num(args.get("bottom"), 0) or 0
                left = num(args.get("left"), 0) or 0
                x, y, w, h = x + left, y + top, max(w - left - right, 0), max(h - top - bottom, 0)
            return f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})"
        if shape == "polygon" and isinstance(args, dict):
            pts = [(num(p[0], 0), num(p[1], 0)) for p in args.get("points", []) if is_point(p)]
            if len(pts) < 3:
                return None
            return " -- ".join(f"({fnum(x)},{fnum(y)})" for x, y in pts) + " -- cycle"
        if shape == "path" and isinstance(args, dict):
            return self._path_d(args.get("d")) or None
        return None

    def _css_clip_geom(self, o, spec):
        box = self._box(o)
        if not box or not isinstance(spec, str):
            return None
        x, y, w, h = box
        s = spec.strip()
        m = re.match(r"^circle\(\s*([^)]*?)\s*\)$", s, flags=re.I)
        if m:
            body = m.group(1)
            radius_part, _, center_part = body.partition(" at ")
            cx, cy = self._css_clip_center(center_part, box)
            r = self._css_clip_length(radius_part.strip() or "50%", min(w, h))
            return f"({fnum(cx)},{fnum(cy)}) circle ({fnum(r)}pt)"
        m = re.match(r"^ellipse\(\s*([^)]*?)\s*\)$", s, flags=re.I)
        if m:
            body = m.group(1)
            radii_part, _, center_part = body.partition(" at ")
            radii = radii_part.split()
            rx = self._css_clip_length(radii[0] if radii else "50%", w)
            ry = self._css_clip_length(radii[1] if len(radii) > 1 else "50%", h)
            cx, cy = self._css_clip_center(center_part, box)
            return f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx)}pt and {fnum(ry)}pt)"
        m = re.match(r"^inset\(\s*([^)]*?)\s*\)$", s, flags=re.I)
        if m:
            body = m.group(1).split(" round ", 1)[0].strip()
            parts = body.split() or ["0"]
            top, right, bottom, left = self._css_edges(parts, w, h)
            return f"({fnum(x + left)},{fnum(y + top)}) rectangle ({fnum(x + w - right)},{fnum(y + h - bottom)})"
        m = re.match(r"^polygon\(\s*([^)]*?)\s*\)$", s, flags=re.I)
        if m:
            pts = []
            for pair in m.group(1).split(","):
                vals = pair.strip().split()
                if len(vals) < 2:
                    continue
                px = x + self._css_clip_length(vals[0], w)
                py = y + self._css_clip_length(vals[1], h)
                pts.append((px, py))
            if len(pts) >= 3:
                return " -- ".join(f"({fnum(px)},{fnum(py)})" for px, py in pts) + " -- cycle"
        return None

    def _css_clip_center(self, value, box):
        x, y, w, h = box
        parts = value.split() if isinstance(value, str) and value.strip() else ["50%", "50%"]
        cx = x + self._css_clip_length(parts[0], w)
        cy = y + self._css_clip_length(parts[1] if len(parts) > 1 else "50%", h)
        return cx, cy

    @staticmethod
    def _css_clip_length(value, size):
        if value is None:
            return 0.0
        s = str(value).strip().lower()
        if s.endswith("%"):
            try:
                return size * float(s[:-1]) / 100.0
            except ValueError:
                return 0.0
        return num(s, 0) or 0.0

    def _css_edges(self, parts, w, h):
        vals = list(parts)
        if len(vals) == 1:
            vals *= 4
        elif len(vals) == 2:
            vals = [vals[0], vals[1], vals[0], vals[1]]
        elif len(vals) == 3:
            vals = [vals[0], vals[1], vals[2], vals[1]]
        else:
            vals = vals[:4]
        return (
            self._css_clip_length(vals[0], h),
            self._css_clip_length(vals[1], w),
            self._css_clip_length(vals[2], h),
            self._css_clip_length(vals[3], w),
        )

    def _tikz_transform(self, o):
        style = self._style_dict(o)
        value = style.get("transform")
        if not value:
            value = self._css_decl(style, "transform")
        if not value or value == "none":
            return []
        if isinstance(value, str) and "(" not in value:
            return [value.replace("deg", "")]
        if isinstance(value, str):
            value = self._css_transform_items(value)
        items = value if isinstance(value, list) else [value]
        origin = style.get("transform_origin")
        if origin is None:
            origin = self._css_decl(style, "transform-origin")
        ox, oy = self._transform_origin(origin, o.get("box"))
        opts = []
        for item in items:
            if isinstance(item, str):
                opts.append(item.replace("deg", ""))
                continue
            if not isinstance(item, dict):
                continue
            fn = item.get("fn") or item.get("kind") or item.get("name")
            args = item.get("args") or []
            vals = [self._transform_arg(v) for v in args]
            if fn == "rotate" and vals:
                opts.append(f"rotate around={{{vals[0]}:({fnum(ox)},{fnum(oy)})}}" if ox is not None else f"rotate={vals[0]}")
            elif fn == "translate":
                x = vals[0] if vals else "0"
                y = vals[1] if len(vals) > 1 else "0"
                opts.append(f"shift={{({x},{y})}}")
            elif fn == "translate_x" and vals:
                opts.append(f"shift={{({vals[0]},0)}}")
            elif fn == "translate_y" and vals:
                opts.append(f"shift={{(0,{vals[0]})}}")
            elif fn == "scale" and vals:
                sx, sy = vals[0], vals[1] if len(vals) > 1 else vals[0]
                opts += self._origin_opts([f"xscale={sx}", f"yscale={sy}"], ox, oy)
            elif fn == "scale_x" and vals:
                opts += self._origin_opts([f"xscale={vals[0]}"], ox, oy)
            elif fn == "scale_y" and vals:
                opts += self._origin_opts([f"yscale={vals[0]}"], ox, oy)
            elif fn == "skew_x" and vals:
                opts += self._origin_opts([f"xslant={self._tan_arg(vals[0])}"], ox, oy)
            elif fn == "skew_y" and vals:
                opts += self._origin_opts([f"yslant={self._tan_arg(vals[0])}"], ox, oy)
            elif fn == "skew" and vals:
                opts += self._origin_opts([f"xslant={self._tan_arg(vals[0])}"], ox, oy)
                if len(vals) > 1:
                    opts += self._origin_opts([f"yslant={self._tan_arg(vals[1])}"], ox, oy)
            elif fn == "matrix" and len(vals) >= 6:
                opts.append(f"cm={{{vals[0]},{vals[1]},{vals[2]},{vals[3]},({vals[4]},{vals[5]})}}")
        return opts

    @staticmethod
    def _css_transform_items(value):
        out = []
        for match in re.finditer(r"([A-Za-z][\w-]*)\(([^()]*)\)", str(value)):
            name = match.group(1).strip().lower().replace("-", "_")
            args = [part for part in re.split(r"\s*,\s*|\s+", match.group(2).strip()) if part]
            aliases = {
                "translatex": "translate_x",
                "translate_x": "translate_x",
                "translatey": "translate_y",
                "translate_y": "translate_y",
                "scalex": "scale_x",
                "scale_x": "scale_x",
                "scaley": "scale_y",
                "scale_y": "scale_y",
                "skewx": "skew_x",
                "skew_x": "skew_x",
                "skewy": "skew_y",
                "skew_y": "skew_y",
            }
            out.append({"fn": aliases.get(name, name), "args": args})
        return out

    @staticmethod
    def _origin_opts(opts, ox, oy):
        if ox is None:
            return opts
        return [f"shift={{({fnum(ox)},{fnum(oy)})}}"] + opts + [f"shift={{({fnum(-ox)},{fnum(-oy)})}}"]

    @staticmethod
    def _transform_arg(value):
        n = num(value, None)
        return fnum(n) if n is not None else str(value).replace("deg", "")

    @staticmethod
    def _tan_arg(value):
        n = num(value, None)
        if n is None:
            try:
                n = float(str(value).replace("deg", ""))
            except ValueError:
                return str(value).replace("deg", "")
        return fnum(math.tan(math.radians(n)))

    @staticmethod
    def _transform_origin(origin, box):
        box_ok = isinstance(box, list) and len(box) >= 4
        if box_ok:
            x, y, w, h = num(box[0], 0), num(box[1], 0), num(box[2], 0), num(box[3], 0)
        if isinstance(origin, (list, tuple)) and len(origin) >= 2:
            return num(origin[0], 0), num(origin[1], 0)
        if isinstance(origin, str):
            vals = origin.replace(",", " ").split()
            if len(vals) >= 2 and not any("%" in v for v in vals[:2]):
                first, second = vals[0].lower(), vals[1].lower()
                keywords = {"left", "center", "right", "top", "bottom"}
                if first in keywords or second in keywords:
                    return FigureTikz._keyword_origin(vals, (x, y, w, h)) if box_ok else (None, None)
                return num(vals[0], 0), num(vals[1], 0)
            if vals and box_ok:
                return FigureTikz._keyword_origin(vals, (x, y, w, h))
        if box_ok:
            return x + w / 2, y + h / 2
        return None, None

    @staticmethod
    def _keyword_origin(vals, box):
        x, y, w, h = box
        horiz, vert = "center", "center"
        for raw in vals:
            value = raw.lower()
            if value in ("left", "center", "right"):
                horiz = value
            if value in ("top", "center", "bottom"):
                vert = value
        ox = x if horiz == "left" else x + w if horiz == "right" else x + w / 2
        oy = y if vert == "top" else y + h if vert == "bottom" else y + h / 2
        return ox, oy

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
    def _paint_opacity(self, o, key, fallback=None):
        value = o.get(key)
        if value is None:
            value = self._style_dict(o).get(key)
        return num(value, fallback) if value is not None else fallback

    def _fill_opts(self, o):
        style = self._style_dict(o)
        fill = self._fill_value(o, style)
        expr, op = color_expr(self._color.resolve(fill))
        op = self._paint_opacity(o, "fill_opacity", op)
        opts = []
        if expr is not None:
            opts.append(f"fill={expr}")
            if op is not None:
                opts.append(f"fill opacity={fnum(op)}")
            rule = self._fill_rule(o)
            if rule:
                opts.append(rule)
        return opts

    @staticmethod
    def _fill_value(o, style):
        if "fill" in o:
            return o.get("fill")
        if "fill" in style:
            return style.get("fill")
        if "background_color" in style:
            return style.get("background_color")
        return None

    def _fill_rule(self, o):
        value = o.get("fill_rule")
        if value is None:
            value = self._style_dict(o).get("fill_rule")
        if value is None:
            return None
        norm = str(value).strip().replace("_", "-").replace(" ", "-").lower()
        if norm in ("evenodd", "even-odd"):
            return "even odd rule"
        return None

    def _stroke_opts(self, o, default_color=None):
        style = self._style_dict(o)
        sv = o.get("stroke") if "stroke" in o else style.get("stroke")
        bundle = self._stroke_bundle(o)
        legacy = self._legacy_stroke_bundle(o)
        col = self._color.resolve(legacy.get("color")) if legacy else (
            self._color.resolve(sv) if isinstance(sv, (str, dict)) else None
        )
        if not col or col == "none":
            col = self._color.resolve(bundle.get("stroke") or bundle.get("color"))
        opts, tip = [], self._arrow_tip(bundle)
        if (not col or col == "none") and not tip:
            return opts
        col = col if (col and col != "none") else (default_color or "#000000")
        expr, op = color_expr(col)
        op = self._paint_opacity(o, "stroke_opacity", op)
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
            dashoffset = bundle.get("stroke_dashoffset")
            if dashoffset is not None:
                opts.append(f"dash phase={fnum(num(dashoffset, 0))}pt")
        cap = bundle.get("stroke_linecap")
        if cap in ("round", "butt", "square"):
            opts.append("line cap=" + ("rect" if cap == "square" else cap))
        join = bundle.get("stroke_linejoin")
        if join in ("miter", "round", "bevel"):
            opts.append("line join=" + join)
        miter = bundle.get("stroke_miterlimit")
        if miter is not None:
            opts.append(f"miter limit={fnum(num(miter, 4))}")
        if tip:
            opts.insert(0, tip)
        return opts

    def _stroke_bundle(self, o):
        style = self._style_dict(o)
        border = None
        if not any(k in o for k in ("stroke", "stroke_style")):
            border = self._border_bundle(style.get("border"))
        ssv = o.get("stroke_style")
        if ssv is None:
            ssv = style.get("stroke_style")
        bundle = self._stroke_styles.get(ssv, {}) if isinstance(ssv, str) else (ssv or {})
        if not isinstance(bundle, dict):
            bundle = {}
        legacy = self._legacy_stroke_bundle(o)
        direct = dict(border or {})
        style_keys = (
            "stroke", "color", "stroke_width", "width", "stroke_dasharray", "dash",
            "stroke_dashoffset", "stroke_linecap", "stroke_linejoin",
            "stroke_miterlimit", "paint_order", "vector_effect", "opacity",
            "arrow_start", "arrow_end",
        )
        if border:
            style_keys = ("paint_order", "vector_effect", "opacity", "arrow_start", "arrow_end")
        direct = {
            **direct,
            **{
                key: style[key]
                for key in style_keys
                if key in style and not (key == "stroke" and self._is_legacy_stroke(style[key]))
            },
        }
        if legacy:
            direct.update(legacy)
        direct.update(bundle)
        return direct

    def _border_bundle(self, border):
        border = self._border_dict(border)
        if not border or border.get("style") in ("none", "hidden"):
            return {}
        out = {"color": border.get("color"), "width": border.get("width", 1)}
        if border.get("style") == "dashed":
            out["dash"] = [4, 4]
        elif border.get("style") == "dotted":
            out["dash"] = [1, 3]
        return out

    def _border_opts(self, border):
        bundle = self._border_bundle(border)
        if not bundle:
            return []
        col = self._color.resolve(bundle.get("color")) or "#000000"
        expr, op = color_expr(col)
        if expr is None:
            return []
        opts = ["fill=none", f"draw={expr}", f"line width={fnum(num(bundle.get('width'), 1) or 1)}pt"]
        if op is not None:
            opts.append(f"draw opacity={fnum(op)}")
        dash = bundle.get("dash")
        if isinstance(dash, list) and dash:
            parts = []
            for i, d in enumerate(dash):
                parts.append(("off " if i % 2 else "on ") + fnum(num(d, 0)) + "pt")
            opts.append("dash pattern=" + " ".join(parts))
        return opts

    @staticmethod
    def _border_dict(border):
        if isinstance(border, dict):
            return border
        if not isinstance(border, str):
            return {}
        styles = {"none", "hidden", "solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset"}
        out, colors = {}, []
        for part in border.split():
            if part in styles:
                out["style"] = part
            elif num(part, None) is not None:
                out["width"] = part
            else:
                colors.append(part)
        if colors:
            out["color"] = colors[-1]
        return out

    @staticmethod
    def _is_legacy_stroke(value):
        return isinstance(value, dict) and any(k in value for k in ("color", "width", "dash"))

    def _legacy_stroke_bundle(self, o):
        value = o.get("stroke") if "stroke" in o else self._style_dict(o).get("stroke")
        return value if self._is_legacy_stroke(value) else None

    def _stroke_width(self, o):
        bundle = self._stroke_bundle(o)
        width = num(bundle.get("stroke_width", bundle.get("width")), None)
        return width if width is not None else 1

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

    def _painted_path(self, o, geom, extra_opts=None, default_stroke=None):
        extra_opts = extra_opts or []
        fill = self._fill_opts(o)
        stroke = self._stroke_opts(o, default_color=default_stroke)
        if self._paint_order(o).startswith("stroke fill") and fill and stroke:
            return self._path(stroke + extra_opts, geom) + self._path(fill + extra_opts, geom)
        return self._path(fill + stroke + extra_opts, geom)

    def _paint_order(self, o):
        value = o.get("paint_order")
        if value is None:
            value = self._stroke_bundle(o).get("paint_order")
        return str(value or "").strip().lower()

    def _effect_specs(self, o):
        specs = []
        for kind in ("glow", "shadow"):
            params = self._effect.resolve(o.get(kind), kind)
            if params is not None:
                specs.append((kind, params))
        style = self._style_dict(o)
        for kind, params in self._effect.style_effects(style):
            if kind == "shadow":
                specs.append((kind, params))
        specs.extend(("shadow", params) for params in self._css_drop_shadow_specs(self._css_decl(style, "filter")))
        return specs

    def _css_drop_shadow_specs(self, value):
        if not isinstance(value, str):
            return []
        out = []
        for body in self._css_function_bodies(value, "drop-shadow"):
            params = self._css_shadow_params(body)
            if params:
                out.append(params)
        return out

    @staticmethod
    def _css_function_bodies(value, name):
        out = []
        pattern = re.compile(re.escape(name) + r"\s*\(", flags=re.I)
        for match in pattern.finditer(str(value)):
            depth = 1
            start = match.end()
            i = start
            while i < len(value) and depth:
                ch = value[i]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                i += 1
            if depth == 0:
                out.append(value[start:i - 1].strip())
        return out

    @staticmethod
    def _css_split_top_level(value, sep=","):
        s = str(value)
        out = []
        start = 0
        depth = 0
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")" and depth:
                depth -= 1
            elif ch == sep and depth == 0:
                part = s[start:i].strip()
                if part:
                    out.append(part)
                start = i + 1
        tail = s[start:].strip()
        if tail:
            out.append(tail)
        return out

    def _css_shadow_params(self, body):
        color_match = re.search(r"(rgba?\([^)]*\)|#[0-9A-Fa-f]{3,8})", body)
        color, opacity = "#000000", 0.25
        if color_match:
            color, opacity = self._css_color_opacity(color_match.group(1))
            body = (body[:color_match.start()] + body[color_match.end():]).strip()
        parts = [p for p in body.split() if p]
        if len(parts) < 2:
            return None
        rest = parts[2:]
        blur = 0
        if rest:
            parsed_blur = num(rest[0], None)
            if parsed_blur is not None:
                blur = parsed_blur
                rest = rest[1:]
        if rest and not color_match:
            color = " ".join(rest)
        return {
            "dx": num(parts[0], 0),
            "dy": num(parts[1], 0),
            "blur": blur,
            "color": color,
            "opacity": opacity,
        }

    @staticmethod
    def _css_color_opacity(value):
        s = str(value).strip()
        hex_rgb = _parse_hex(s)
        if hex_rgb:
            r, g, b, a = hex_rgb
            return f"#{r:02x}{g:02x}{b:02x}", 0.25 if a is None else a
        m = re.match(r"rgba?\(\s*([^)]+?)\s*\)$", s, flags=re.I)
        if not m:
            return s, 0.25
        parts = [p.strip() for p in m.group(1).split(",")]
        if len(parts) < 3:
            return "#000000", 0.25
        try:
            r, g, b = (max(0, min(255, int(float(parts[i])))) for i in range(3))
        except ValueError:
            return "#000000", 0.25
        opacity = 0.25
        if len(parts) > 3:
            try:
                opacity = max(0.0, min(1.0, float(parts[3])))
            except ValueError:
                opacity = 0.25
        return f"#{r:02x}{g:02x}{b:02x}", opacity

    @staticmethod
    def _css_shadow_has_explicit_opacity(value):
        s = str(value)
        if re.search(r"rgba\(", s, flags=re.I):
            return True
        return re.search(r"#[0-9A-Fa-f]{8}\b", s) is not None

    def _effect_opts(self, kind, params):
        expr, _ = color_expr(params.get("color") or ("#000000" if kind == "shadow" else "#FFD700"))
        if expr is None:
            return []
        opacity = num(params.get("opacity"), 0.14 if kind == "shadow" else 0.55)
        return [f"fill={expr}", f"fill opacity={fnum(opacity)}"]

    def _rect_effects(self, o, x, y, w, h, r=0):
        out = []
        for kind, params in self._effect_specs(o):
            if kind == "glow":
                spread = max(1, num(params.get("blur"), 4) / 2)
                gx, gy = x - spread, y - spread
                gw, gh = w + 2 * spread, h + 2 * spread
                rr = r + spread if r else 0
            else:
                gx = x + num(params.get("dx"), 0)
                gy = y + num(params.get("dy"), 2)
                gw, gh, rr = w, h, r
            opts = self._effect_opts(kind, params)
            if rr:
                opts.append(f"rounded corners={fnum(rr)}pt")
            geom = f"({fnum(gx)},{fnum(gy)}) rectangle ({fnum(gx + gw)},{fnum(gy + gh)})"
            out.append(self._path(opts, geom))
        return "".join(out)

    def _rect_outline(self, o, x, y, w, h, r=0):
        style = self._style_dict(o)
        opts = self._border_opts(style.get("outline"))
        if not opts:
            return ""
        offset = num(style.get("outline_offset"), 0) or 0
        rr = max(0, r + offset)
        if rr:
            opts.append(f"rounded corners={fnum(rr)}pt")
        ox, oy = x - offset, y - offset
        geom = f"({fnum(ox)},{fnum(oy)}) rectangle ({fnum(ox + w + 2 * offset)},{fnum(oy + h + 2 * offset)})"
        return self._path(opts, geom)

    def _side_borders(self, o):
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        sides = (
            ("border_top", (x, y, x + w, y)),
            ("border_right", (x + w, y, x + w, y + h)),
            ("border_bottom", (x, y + h, x + w, y + h)),
            ("border_left", (x, y, x, y + h)),
        )
        out = []
        style = self._style_dict(o)
        for key, (x1, y1, x2, y2) in sides:
            border = style.get(key)
            if not isinstance(border, dict):
                continue
            opts = self._border_opts(border)
            if opts:
                geom = f"({fnum(x1)},{fnum(y1)}) -- ({fnum(x2)},{fnum(y2)})"
                out.append(self._path(opts, geom))
        return "".join(out)

    def _ellipse_effects(self, o, cx, cy, rx, ry):
        out = []
        for kind, params in self._effect_specs(o):
            if kind == "glow":
                spread = max(1, num(params.get("blur"), 4) / 2)
                ex, ey = cx, cy
                erx, ery = rx + spread, ry + spread
            else:
                ex = cx + num(params.get("dx"), 0)
                ey = cy + num(params.get("dy"), 2)
                erx, ery = rx, ry
            geom = f"({fnum(ex)},{fnum(ey)}) ellipse ({fnum(erx)}pt and {fnum(ery)}pt)"
            out.append(self._path(self._effect_opts(kind, params), geom))
        return "".join(out)

    def _draw_rect(self, o) -> str:
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        style = self._style_dict(o)
        r = num(o.get("radius", o.get("rx", style.get("border_radius", style.get("radius")))), 0) or 0
        effects = self._rect_effects(o, x, y, w, h, r)
        grad = self._gradient_rect(o.get("fill"), x, y, w, h)
        if grad:
            # gradient fill, then the (optional) outline drawn over it.
            stroke = self._stroke_opts(o)
            geom = f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})"
            return effects + grad + (self._path(stroke, geom) if stroke else "") + self._rect_outline(o, x, y, w, h, r)
        extra = []
        if r:
            extra.append(f"rounded corners={fnum(r)}pt")
        geom = f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})"
        return effects + self._painted_path(o, geom, extra) + self._rect_outline(o, x, y, w, h, r)

    def _gradient_rect(self, fill, x, y, w, h):
        """A linear-gradient rect fill to piecewise TikZ `\\shade` segments.

        `ColorResolver` collapses a paint object to its first stop, so a
        multi-stop gradient would otherwise render as a flat block. TikZ has no
        native multi-stop axis shading, so each consecutive stop pair is drawn as
        its own two-color `\\shade` rectangle along the gradient axis; adjacent
        segments share an endpoint color, so the result reads as one continuous
        gradient. Falls back to `None` (solid fill) for non-linear paints or any
        stop whose color is not opaque hex (e.g. an `rgba(...,0)` fade)."""
        if not isinstance(fill, dict) or str(fill.get("kind")) not in ("linear", "linear-gradient"):
            return None
        raw = fill.get("stops")
        if not isinstance(raw, list) or len(raw) < 2 or w <= 0 or h <= 0:
            return None
        stops = []
        for i, s in enumerate(raw):
            if not isinstance(s, dict):
                return None
            resolved = self._color.resolve(s.get("color"))
            if not _parse_hex(resolved):       # transparent / non-hex: bail to solid
                return None
            expr, _op = color_expr(resolved)
            stops.append((_grad_pct(s.get("position"), i / (len(raw) - 1)), expr))
        stops.sort(key=lambda s: s[0])
        axis, reverse = _grad_orientation(_grad_angle(fill.get("angle")))
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

    def _draw_ellipse(self, o) -> str:
        c = o.get("center") or [0, 0]
        cx, cy = num(c[0], 0), num(c[1], 0)
        rx, ry = num(o.get("rx"), 0), num(o.get("ry"), 0)
        box = o.get("box")
        if not rx and isinstance(box, list) and len(box) >= 4:
            cx, cy = num(box[0], 0) + num(box[2], 0) / 2, num(box[1], 0) + num(box[3], 0) / 2
            rx, ry = num(box[2], 0) / 2, num(box[3], 0) / 2
        geom = f"({fnum(cx)},{fnum(cy)}) ellipse ({fnum(rx)}pt and {fnum(ry)}pt)"
        return self._ellipse_effects(o, cx, cy, rx, ry) + self._painted_path(o, geom)

    def _draw_circle(self, o) -> str:
        c = o.get("center") or [0, 0]
        r = num(o.get("r"), 0)
        cx, cy = num(c[0], 0), num(c[1], 0)
        geom = f"({fnum(cx)},{fnum(cy)}) circle ({fnum(r)}pt)"
        return self._ellipse_effects(o, cx, cy, r, r) + self._painted_path(o, geom)

    def _draw_line(self, o) -> str:
        fr, to = o.get("from"), o.get("to")
        if not (is_point(fr) and is_point(to)):
            return ""
        grad = self._gradient_stroke_line(o, fr, to)
        if grad:
            return grad
        opts = self._stroke_opts(o, default_color="#000000")
        geom = f"({fnum(num(fr[0], 0))},{fnum(num(fr[1], 0))}) -- ({fnum(num(to[0], 0))},{fnum(num(to[1], 0))})"
        return f"\\draw[{','.join(opts)}] {geom};\n" if opts else f"\\draw {geom};\n"

    def _gradient_stroke_line(self, o, fr, to):
        """Render a linear-gradient stroke for straight horizontal/vertical lines.

        TikZ cannot apply a multi-stop color ramp directly to a stroked path. For
        axis-aligned fixture lines, we approximate the stroke as adjacent shaded
        rectangles with the same thickness as the stroke. Other paths fall back
        to the normal solid-stroke path.
        """
        stroke = o.get("stroke")
        if not isinstance(stroke, dict) or str(stroke.get("kind")) not in ("linear", "linear-gradient"):
            return None
        x0, y0 = num(fr[0], 0), num(fr[1], 0)
        x1, y1 = num(to[0], 0), num(to[1], 0)
        width = self._stroke_width(o)
        if width <= 0:
            return ""
        if abs(y1 - y0) < 1e-9 and abs(x1 - x0) > 1e-9:
            x, y = min(x0, x1), y0 - width / 2
            w, h = abs(x1 - x0), width
        elif abs(x1 - x0) < 1e-9 and abs(y1 - y0) > 1e-9:
            x, y = x0 - width / 2, min(y0, y1)
            w, h = width, abs(y1 - y0)
        else:
            return None
        return self._gradient_rect(stroke, x, y, w, h)

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
        chain = " -- ".join(f"({fnum(x)},{fnum(y)})" for x, y in pts) + " -- cycle"
        return self._painted_path(o, chain)

    def _draw_path(self, o) -> str:
        geom = self._path_d(o.get("d"))
        if not geom:
            return ""
        return self._painted_path(o, geom)

    def _draw_curve(self, o) -> str:
        fr, to = o.get("from"), o.get("to")
        if not (is_point(fr) and is_point(to)):
            return ""
        c1 = o.get("control1") or o.get("c1") or fr
        c2 = o.get("control2") or o.get("c2") or to
        if not (is_point(c1) and is_point(c2)):
            return ""
        geom = (
            f"({fnum(num(fr[0], 0))},{fnum(num(fr[1], 0))}) .. controls "
            f"({fnum(num(c1[0], 0))},{fnum(num(c1[1], 0))}) and "
            f"({fnum(num(c2[0], 0))},{fnum(num(c2[1], 0))}) .. "
            f"({fnum(num(to[0], 0))},{fnum(num(to[1], 0))})"
        )
        return self._painted_path(o, geom, default_stroke="#000000")

    def _draw_bezier(self, o) -> str:
        return self._draw_curve(o)

    def _path_d(self, d):
        if isinstance(d, list):
            return self._path_segments(d)
        if not isinstance(d, str):
            return ""
        tokens = re.findall(r"[MmLlHhVvCcZz]|-?\d+(?:\.\d+)?", d.replace(",", " "))
        out, cmd, cur, start, i = [], None, (0.0, 0.0), (0.0, 0.0), 0

        def point(relative=False):
            nonlocal i, cur
            if i + 1 >= len(tokens):
                return None
            x, y = num(tokens[i], None), num(tokens[i + 1], None)
            i += 2
            if x is None or y is None:
                return None
            if relative:
                x, y = cur[0] + x, cur[1] + y
            cur = (x, y)
            return cur

        while i < len(tokens):
            if re.match(r"^[A-Za-z]$", tokens[i]):
                cmd = tokens[i]
                i += 1
            if cmd is None:
                break
            rel = cmd.islower()
            c = cmd.upper()
            if c == "M":
                p = point(rel)
                if p is None:
                    break
                start = p
                out.append(f"({fnum(p[0])},{fnum(p[1])})")
                cmd = "l" if rel else "L"
            elif c == "L":
                p = point(rel)
                if p is None:
                    break
                out.append(f"-- ({fnum(p[0])},{fnum(p[1])})")
            elif c == "H":
                x = num(tokens[i], None) if i < len(tokens) else None
                i += 1
                if x is None:
                    break
                cur = ((cur[0] + x) if rel else x, cur[1])
                out.append(f"-- ({fnum(cur[0])},{fnum(cur[1])})")
            elif c == "V":
                y = num(tokens[i], None) if i < len(tokens) else None
                i += 1
                if y is None:
                    break
                cur = (cur[0], (cur[1] + y) if rel else y)
                out.append(f"-- ({fnum(cur[0])},{fnum(cur[1])})")
            elif c == "C":
                vals = [num(tokens[i + j], None) for j in range(6)] if i + 5 < len(tokens) else []
                i += 6
                if len(vals) != 6 or any(v is None for v in vals):
                    break
                x1, y1, x2, y2, x, y = vals
                if rel:
                    x1, y1, x2, y2, x, y = cur[0] + x1, cur[1] + y1, cur[0] + x2, cur[1] + y2, cur[0] + x, cur[1] + y
                cur = (x, y)
                out.append(
                    f".. controls ({fnum(x1)},{fnum(y1)}) and ({fnum(x2)},{fnum(y2)}) .. ({fnum(x)},{fnum(y)})"
                )
            elif c == "Z":
                cur = start
                out.append("-- cycle")
            else:
                break
        return " ".join(out)

    def _path_segments(self, segments):
        out = []
        for seg in segments:
            if not isinstance(seg, list) or not seg:
                continue
            cmd = str(seg[0]).upper()
            vals = [num(v, None) for v in seg[1:]]
            if cmd == "M" and len(vals) >= 2:
                out.append(f"({fnum(vals[0])},{fnum(vals[1])})")
            elif cmd == "L" and len(vals) >= 2:
                out.append(f"-- ({fnum(vals[0])},{fnum(vals[1])})")
            elif cmd == "C" and len(vals) >= 6:
                out.append(
                    f".. controls ({fnum(vals[0])},{fnum(vals[1])}) and ({fnum(vals[2])},{fnum(vals[3])}) "
                    f".. ({fnum(vals[4])},{fnum(vals[5])})"
                )
            elif cmd == "Z":
                out.append("-- cycle")
        return " ".join(out)

    # -- text -------------------------------------------------------------- #
    def _font(self, st):
        size = st.get("size", 12) or 12
        macro = self._font_macro(st.get("family")) if self._font_macro else ""
        font = macro + f"\\fontsize{{{fnum(size)}}}{{{fnum(size * 1.12)}}}\\selectfont"
        if st.get("bold"):
            font += "\\bfseries"
        if st.get("italic"):
            font += "\\itshape"
        if st.get("font_variant_caps") == "small-caps":
            font += "\\scshape"
        for feature in self._numeric_font_features(st.get("font_variant_numeric")):
            font += f"\\addfontfeatures{{Numbers={feature}}}"
        for feature in self._ligature_font_features(st.get("font_variant_ligatures")):
            font += f"\\addfontfeatures{{Ligatures={feature}}}"
        kerning = st.get("font_kerning")
        if kerning == "none":
            font += "\\addfontfeatures{Kerning=Off}"
        elif kerning == "normal":
            font += "\\addfontfeatures{Kerning=On}"
        stretch = self._font_stretch_factor(st.get("font_stretch"))
        if stretch is not None:
            font += f"\\addfontfeatures{{FakeStretch={fnum(stretch)}}}"
        raw_features = self._raw_font_features(st.get("font_feature_settings"))
        if raw_features:
            font += f"\\addfontfeatures{{RawFeature={{{raw_features}}}}}"
        axis_features = self._variation_axis_features(st.get("font_variation_settings"))
        if axis_features:
            font += "\\addfontfeatures{RawFeature={+axis={" + axis_features + "}}}"
        letter_space = self._letter_space_amount(st.get("letter_spacing"))
        if letter_space is not None:
            font += f"\\addfontfeatures{{LetterSpace={fnum(letter_space)}}}"
        return font

    def _css_text_style(self, st):
        if not isinstance(st, dict) or not isinstance(st.get("css"), str):
            return st
        out = dict(st)
        for css_name, key in (
            ("letter-spacing", "letter_spacing"),
            ("word-spacing", "word_spacing"),
            ("font-stretch", "font_stretch"),
            ("font-feature-settings", "font_feature_settings"),
            ("font-variant-numeric", "font_variant_numeric"),
            ("fill", "text_fill"),
            ("stroke", "text_stroke"),
            ("stroke-width", "text_stroke_width"),
        ):
            if out.get(key) is None:
                value = self._css_decl(out, css_name)
                if value is not None:
                    out[key] = value
        if self._css_decl(out, "font-size") is not None:
            out["size"] = num(self._css_decl(out, "font-size"), out.get("size", 12))
        weight = self._css_decl(out, "font-weight")
        if weight is not None and out.get("weight") in (None, "normal"):
            out["weight"] = weight
            out["bold"] = str(weight).strip().lower() == "bold" or (num(weight, 0) or 0) >= 600
        return out

    @staticmethod
    def _letter_space_amount(value):
        if value is None:
            return None
        amount = num(value, None)
        if amount in (None, 0):
            return None
        return amount

    @staticmethod
    def _numeric_font_features(value):
        if not value:
            return []
        mapping = {
            "tabular-nums": "Monospaced",
            "proportional-nums": "Proportional",
            "oldstyle-nums": "OldStyle",
            "lining-nums": "Lining",
            "slashed-zero": "SlashedZero",
        }
        tokens = str(value).replace(",", " ").split()
        return [mapping[token] for token in tokens if token in mapping]

    @staticmethod
    def _ligature_font_features(value):
        if not value:
            return []
        raw = str(value).strip()
        if raw == "none":
            return ["NoCommon"]
        mapping = {
            "common-ligatures": "Common",
            "no-common-ligatures": "NoCommon",
            "discretionary-ligatures": "Rare",
            "no-discretionary-ligatures": "NoRare",
            "historical-ligatures": "Historic",
            "no-historical-ligatures": "NoHistoric",
            "contextual": "Contextual",
            "no-contextual": "NoContextual",
        }
        tokens = raw.replace(",", " ").split()
        return [mapping[token] for token in tokens if token in mapping]

    @staticmethod
    def _raw_font_features(value):
        if not value or not isinstance(value, str):
            return ""
        features = []
        for tag, flag in re.findall(r'"([A-Za-z0-9]{4})"\s+(-?\d+(?:\.\d+)?)', value):
            enabled = num(flag, 0) != 0
            features.append(("+" if enabled else "-") + tag)
        return ",".join(features)

    @staticmethod
    def _variation_axis_features(value):
        if not value or not isinstance(value, str):
            return ""
        axes = []
        for tag, amount in re.findall(r'"([A-Za-z0-9]{4})"\s+(-?\d+(?:\.\d+)?)', value):
            axes.append(f"{tag}={fnum(num(amount, 0))}")
        return ",".join(axes)

    @staticmethod
    def _font_stretch_factor(value):
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0.01, num(value, 100) / 100)
        raw = str(value).strip().lower()
        named = {
            "ultra-condensed": 0.5,
            "extra-condensed": 0.625,
            "condensed": 0.75,
            "semi-condensed": 0.875,
            "normal": 1,
            "semi-expanded": 1.125,
            "expanded": 1.25,
            "extra-expanded": 1.5,
            "ultra-expanded": 2,
        }
        if raw in named:
            return None if named[raw] == 1 else named[raw]
        if raw.endswith("%"):
            return max(0.01, num(raw[:-1], 100) / 100)
        return None

    def _text_opts(self, st, anchor, width, align):
        opts = [
            f"anchor={anchor}",
            "inner sep=0pt",
            f"font={self._font(st)}",
        ]
        if self._wrap_text_enabled(st):
            opts.extend([
                f"text width={fnum(max(width, 1))}pt",
                f"align={align}",
            ])
        fill = st.get("text_fill")
        text_color = st.get("text_stroke") if str(fill or "").strip().lower() == "none" and st.get("text_stroke") else st.get("color")
        cexpr, op = color_expr(text_color)
        if cexpr:
            opts.append(f"text={cexpr}")
        if op is not None:
            opts.append(f"text opacity={fnum(op)}")
        opts.extend(self._writing_mode_opts(st))
        return opts

    @staticmethod
    def _wrap_text_enabled(st):
        if not isinstance(st, dict):
            return True
        if st.get("nowrap") is True:
            return False
        value = st.get("text_wrap")
        if value is None and "wrap" in st:
            value = "wrap" if st.get("wrap") else "nowrap"
        return str(value or "wrap").strip().lower() != "nowrap"

    @staticmethod
    def _writing_mode_opts(st):
        mode = str(st.get("writing_mode") or "").strip().lower() if isinstance(st, dict) else ""
        if mode == "vertical-rl":
            return ["rotate=-90"]
        if mode == "vertical-lr":
            return ["rotate=90"]
        return []

    def _text_shadow_specs(self, st):
        value = st.get("text_shadow") if isinstance(st, dict) else None
        from_css = False
        if not value and isinstance(st, dict):
            value = self._css_decl(st, "text-shadow")
            from_css = value is not None
        if not value:
            return []
        specs = []
        if isinstance(value, dict):
            values = [value]
        elif isinstance(value, list):
            values = value
        else:
            values = self._css_split_top_level(value)
        for raw in values:
            if isinstance(raw, dict):
                dx = num(raw.get("dx", raw.get("offset_x")), None)
                dy = num(raw.get("dy", raw.get("offset_y")), None)
                blur = num(raw.get("blur"), 0)
                color = raw.get("color", "#000000")
                opacity = raw.get("opacity")
            else:
                params = self._css_shadow_params(str(raw))
                if not params:
                    continue
                dx, dy = num(params.get("dx"), None), num(params.get("dy"), None)
                blur = num(params.get("blur"), 0)
                color = params.get("color", "#000000")
                opacity = params.get("opacity")
                if not from_css and not self._css_shadow_has_explicit_opacity(raw):
                    opacity = None
            if dx is None or dy is None:
                continue
            expr, op = color_expr(color)
            if expr:
                specs.append({"dx": dx, "dy": dy, "blur": blur or 0, "expr": expr, "opacity": op if op is not None else opacity})
        return specs

    @staticmethod
    def _transform_text(content, transform):
        text = str(content)
        if transform == "uppercase":
            return text.upper()
        if transform == "lowercase":
            return text.lower()
        if transform == "capitalize":
            return " ".join(word[:1].upper() + word[1:] for word in text.split(" "))
        return text

    def _text_node(self, st, anchor, width, align, x, y, content):
        opts = self._text_opts(st, anchor, width, align)
        body = self._format_text(st, content)
        return f"\\node[{','.join(opts)}] at ({fnum(x)},{fnum(y)}) {{{body}}};\n"

    def _format_text(self, st, content):
        content = self._transform_text(content, st.get("text_transform"))
        content = self._clamp_text(st, content)
        escaped = self._break_text(st, content)
        escaped = self._tab_text(st, escaped)
        escaped = self._white_space_text(st, escaped)
        escaped = self._indent_text(st, escaped)
        escaped = self._space_text(st, escaped)
        escaped = self._hyphen_text(st, escaped)
        escaped = self._direction_text(st, escaped)
        escaped = self._unicode_bidi_text(st, escaped)
        escaped = self._hanging_punctuation_text(st, escaped)
        escaped = self._text_align_last_text(st, escaped)
        return self._text_paint_text(st, self._decorate_text(st, escaped))

    @staticmethod
    def _text_paint_text(st, content):
        fill = str(st.get("text_fill") or "").strip().lower() if isinstance(st, dict) else ""
        if fill != "none" or not st.get("text_stroke"):
            return content
        width = max(0.01, num(st.get("text_stroke_width"), 1) or 1)
        return f"\\pdfliteral direct {{1 Tr {fnum(width)} w}}{content}\\pdfliteral direct {{0 Tr}}"

    @staticmethod
    def _clamp_text(st, content):
        text = str(content)
        if not isinstance(st, dict):
            return text
        limit = num(st.get("max_lines"), None)
        if limit is None or limit <= 0:
            return text
        lines = text.splitlines()
        if len(lines) <= int(limit):
            return text
        kept = lines[:int(limit)]
        if str(st.get("text_overflow") or "").strip().lower() == "ellipsis" and kept:
            kept[-1] += "\u2026"
        return "\n".join(kept)

    @staticmethod
    def _break_text(st, content):
        if not isinstance(st, dict):
            return ltx_escape(content)
        word_break = str(st.get("word_break") or "").strip().lower()
        overflow_wrap = str(st.get("overflow_wrap") or "").strip().lower()
        if word_break not in ("break-all", "break-word") and overflow_wrap not in ("anywhere", "break-word"):
            return ltx_escape(content)
        return r"\allowbreak{}".join(ltx_escape(ch) for ch in str(content))

    @staticmethod
    def _tab_text(st, content):
        if "\t" not in content or not isinstance(st, dict):
            return content
        size = num(st.get("size"), 12) or 12
        avg = num(st.get("avg"), 0.52) or 0.52
        count = num(st.get("tab_size"), 8)
        if count is None or count <= 0:
            count = 8
        return content.replace("\t", f"\\hspace*{{{fnum(count * size * avg)}pt}}")

    @staticmethod
    def _white_space_text(st, content):
        if not isinstance(st, dict):
            return content
        mode = str(st.get("white_space") or "").strip().lower()
        if mode in ("pre", "pre-wrap", "pre-line", "break-spaces"):
            content = content.replace("\n", r"\\")
        if mode in ("pre", "pre-wrap", "break-spaces"):
            content = content.replace(" ", r"\ ")
        return content

    @staticmethod
    def _indent_text(st, content):
        indent = num(st.get("text_indent"), None) if isinstance(st, dict) else None
        if indent in (None, 0):
            return content
        return f"\\hspace*{{{fnum(indent)}pt}}{content}"

    @staticmethod
    def _space_text(st, content):
        spacing = num(st.get("word_spacing"), None) if isinstance(st, dict) else None
        if spacing in (None, 0):
            return content
        return f"{{\\spaceskip={fnum(spacing)}pt {content}}}"

    @staticmethod
    def _hyphen_text(st, content):
        if not isinstance(st, dict):
            return content
        commands = []
        hyphens = str(st.get("hyphens") or "").strip().lower()
        if hyphens == "none":
            commands.extend(["\\hyphenpenalty=10000\\relax", "\\exhyphenpenalty=10000\\relax"])
        elif hyphens == "manual":
            commands.append("\\hyphenpenalty=10000\\relax")
        limits = str(st.get("hyphenate_limit_chars") or "").split()
        if len(limits) == 3:
            before, after = num(limits[1], None), num(limits[2], None)
            if before is not None:
                commands.append(f"\\lefthyphenmin={int(before)}\\relax")
            if after is not None:
                commands.append(f"\\righthyphenmin={int(after)}\\relax")
        marker = st.get("hyphenate_character")
        if isinstance(marker, str) and marker:
            commands.append(f"\\hyphenchar\\font={ord(marker[0])}\\relax")
        if not commands:
            return content
        return "{" + "".join(commands) + " " + content + "}"

    @staticmethod
    def _direction_text(st, content):
        if not isinstance(st, dict):
            return content
        direction = str(st.get("direction") or "").strip().lower()
        if direction == "rtl":
            return "{\\ifdefined\\textdir\\textdir TRT\\fi " + content + "}"
        if direction == "ltr":
            return "{\\ifdefined\\textdir\\textdir TLT\\fi " + content + "}"
        return content

    @staticmethod
    def _unicode_bidi_text(st, content):
        if not isinstance(st, dict):
            return content
        value = str(st.get("unicode_bidi") or "").strip().lower()
        direction = str(st.get("direction") or "").strip().lower()
        dir_token = "TRT" if direction == "rtl" else "TLT"
        if value in ("embed", "isolate", "plaintext"):
            return "{\\ifdefined\\textdir\\textdir " + dir_token + "\\fi " + content + "}"
        if value in ("bidi-override", "isolate-override"):
            return (
                "{\\ifdefined\\beginR\\beginR\\else\\ifdefined\\beginL\\beginL\\fi\\fi "
                + content +
                "\\ifdefined\\endR\\endR\\else\\ifdefined\\endL\\endL\\fi\\fi}"
            )
        return content

    @staticmethod
    def _hanging_punctuation_text(st, content):
        if not isinstance(st, dict):
            return content
        value = str(st.get("hanging_punctuation") or "").strip().lower()
        if value == "none":
            return "{\\ifdefined\\microtypesetup\\microtypesetup{protrusion=false}\\fi " + content + "}"
        if value in ("first", "last", "allow-end", "force-end"):
            return "{\\ifdefined\\microtypesetup\\microtypesetup{protrusion=true}\\fi " + content + "}"
        return content

    @staticmethod
    def _text_align_last_text(st, content):
        if not isinstance(st, dict):
            return content
        value = str(st.get("text_align_last") or "").strip().lower()
        if value in ("left", "start"):
            return "{\\leftskip=0pt\\rightskip=0pt plus 1fil\\parfillskip=0pt " + content + "}"
        if value in ("right", "end"):
            return "{\\leftskip=0pt plus 1fil\\rightskip=0pt\\parfillskip=0pt " + content + "}"
        if value == "center":
            return (
                "{\\leftskip=0pt plus 1fil\\rightskip=0pt plus 1fil"
                "\\parfillskip=0pt " + content + "}"
            )
        if value == "justify":
            return "{\\parfillskip=0pt " + content + "}"
        return content

    @staticmethod
    def _decorate_text(st, content):
        deco = st.get("text_decoration") if isinstance(st, dict) else None
        line = deco.get("line") if isinstance(deco, dict) else deco
        if isinstance(line, (list, tuple, set)):
            lines = {str(v).strip().lower() for v in line}
        else:
            lines = set(str(line or "").replace(",", " ").split())
        if "underline" in lines:
            command = "uwave" if "wavy" in lines else "uuline" if "double" in lines else "underline"
            content = f"\\{command}{{{content}}}"
        if "overline" in lines:
            content = f"\\overline{{\\mbox{{{content}}}}}"
        if "line-through" in lines:
            content = f"\\sout{{{content}}}"
        return content

    def _text_shadow_nodes(self, st, anchor, width, align, x, y, content):
        out = []
        for spec in self._text_shadow_specs(st):
            shadow_st = dict(st)
            shadow_st["color"] = spec["expr"]
            opts = self._text_opts(shadow_st, anchor, width, align)
            opacity = spec.get("opacity")
            if opacity is None:
                opacity = 0.45 if spec.get("blur") else None
            if opacity is not None:
                opts.append(f"text opacity={fnum(opacity)}")
            body = self._format_text(st, content)
            out.append(
                f"\\node[{','.join(opts)}] at "
                f"({fnum(x + spec['dx'])},{fnum(y + spec['dy'])}) {{{body}}};\n"
            )
        return "".join(out)

    @staticmethod
    def _text_y(st, y, h):
        size = st.get("size", 12) or 12
        valign = str(st.get("valign") or "").strip().lower()
        if valign in ("top", "text-top", "super"):
            return y + size / 2
        if valign in ("bottom", "text-bottom", "sub"):
            return y + max(0, h - size / 2)
        return y + h / 2

    def _draw_text_spans(self, o, x, y, w, h, base_st, anchor, align):
        spans = [sp for sp in (o.get("spans") or []) if isinstance(sp, (str, dict))]
        if not spans:
            return ""
        start_x = x + w / 2 if anchor == "center" else x + w if anchor == "east" else x
        cursor = start_x
        ay = self._text_y(base_st, y, h)
        out = []
        for sp in spans:
            text = sp if isinstance(sp, str) else sp.get("text", "")
            if text is None or text == "":
                continue
            st = self._ts.resolve(sp.get("style")) if isinstance(sp, dict) and sp.get("style") else base_st
            st = self._css_text_style(st)
            run_w = max(len(str(text)) * (st.get("size", 12) or 12) * (st.get("avg", 0.52) or 0.52), 1)
            if anchor == "center":
                # Multi-run centered text is placed from the left edge so run order
                # remains readable; exact centering requires real shaping metrics.
                node_x = x + (cursor - start_x)
            elif anchor == "east":
                node_x = cursor - run_w
                cursor -= run_w
            else:
                node_x = cursor
                cursor += run_w
            out.append(self._text_shadow_nodes(st, "west", run_w, "flush left", node_x, ay, text))
            out.append(self._text_node(st, "west", run_w, "flush left", node_x, ay, text))
        return "".join(out)

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
        st = self._css_text_style(self._ts.resolve(o.get("style")))
        align = st.get("align") or "left"
        if align in ("center", "middle"):
            ax, anchor, talign = x + w / 2, "center", "center"
        elif align in ("right", "end"):
            ax, anchor, talign = x + w, "east", "flush right"
        else:
            ax, anchor, talign = x, "west", "flush left"
        ay = self._text_y(st, y, h)
        if isinstance(o.get("spans"), list):
            span_body = self._draw_text_spans(o, x, y, w, h, st, anchor, talign)
            if span_body:
                return span_body
        return (
            self._text_shadow_nodes(st, anchor, w, talign, ax, ay, content)
            + self._text_node(st, anchor, w, talign, ax, ay, content)
        )

    def _draw_icon(self, o) -> str:
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        size = num(o.get("size"), min(w, h)) or min(w, h) or 12
        color, _ = color_expr(self._color.resolve(o.get("color") or "#000000"))
        opts = ["anchor=center", "inner sep=0pt", f"font=\\fontsize{{{fnum(size)}}}{{{fnum(size)}}}\\selectfont"]
        if color:
            opts.append(f"text={color}")
        return f"\\node[{','.join(opts)}] at ({fnum(x + w / 2)},{fnum(y + h / 2)}) {{{ltx_escape(o.get('glyph') or '')}}};\n"

    def _draw_bullet_list(self, o) -> str:
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ""
        x, y, w, _h = (num(v, 0) for v in box[:4])
        st = self._ts.resolve(o.get("style"))
        size = st.get("size", 12) or 12
        gap = num(o.get("gap"), size * 1.35) or size * 1.35
        indent = num(o.get("indent"), size * 1.2) or size * 1.2
        marker = o.get("marker") or "*"
        out = []
        for idx, item in enumerate(o.get("items") or []):
            text = item.get("text") if isinstance(item, dict) else item
            yy = y + size + idx * gap
            out.append(
                f"\\node[anchor=west,inner sep=0pt,font=\\fontsize{{{fnum(size)}}}{{{fnum(size * 1.2)}}}\\selectfont] "
                f"at ({fnum(x)},{fnum(yy)}) {{{ltx_escape(marker)}}};\n"
            )
            out.append(
                f"\\node[anchor=west,inner sep=0pt,text width={fnum(max(w - indent, 1))}pt,"
                f"font=\\fontsize{{{fnum(size)}}}{{{fnum(size * 1.2)}}}\\selectfont] "
                f"at ({fnum(x + indent)},{fnum(yy)}) {{{ltx_escape(text)}}};\n"
            )
        return "".join(out)

    def _draw_dimension(self, o) -> str:
        fr, to = o.get("from"), o.get("to")
        if not (is_point(fr) and is_point(to)):
            return ""
        x1, y1, x2, y2 = num(fr[0], 0), num(fr[1], 0), num(to[0], 0), num(to[1], 0)
        opts = self._stroke_opts(o, default_color="#000000")
        arrow = o.get("arrows") or "both"
        if arrow == "both":
            opts.insert(0, "<->")
        elif arrow == "first":
            opts.insert(0, "<-")
        elif arrow == "second":
            opts.insert(0, "->")
        label = o.get("text")
        if label is None:
            value = o.get("value")
            if value == "auto" or value is None:
                value = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                label = fnum(value)
            else:
                label = fnum(value)
            label = f"{o.get('prefix') or ''}{label}{o.get('suffix') or ''}"
        midx, midy = (x1 + x2) / 2, (y1 + y2) / 2
        return (
            f"\\draw[{','.join(opts)}] ({fnum(x1)},{fnum(y1)}) -- ({fnum(x2)},{fnum(y2)});\n"
            f"\\node[fill=white,inner sep=1pt,font=\\scriptsize] at ({fnum(midx)},{fnum(midy)}) {{{ltx_escape(label)}}};\n"
        )

    def _draw_table(self, o) -> str:
        box = o.get("box")
        rows = [r for r in (o.get("rows") or []) if isinstance(r, list)]
        if not rows or not (isinstance(box, list) and len(box) >= 4):
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        nrow = len(rows)
        ncol = max([len(r) for r in rows] + [1])
        cw, rh = w / ncol if ncol else w, h / nrow if nrow else h
        out = [f"\\draw ({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"]
        for c in range(1, ncol):
            xx = x + c * cw
            out.append(f"\\draw ({fnum(xx)},{fnum(y)}) -- ({fnum(xx)},{fnum(y + h)});\n")
        for r in range(1, nrow):
            yy = y + r * rh
            out.append(f"\\draw ({fnum(x)},{fnum(yy)}) -- ({fnum(x + w)},{fnum(yy)});\n")
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                text = cell.get("content") if isinstance(cell, dict) else cell
                out.append(
                    f"\\node[anchor=center,inner sep=1pt,font=\\scriptsize,text width={fnum(max(cw - 2, 1))}pt,align=center] "
                    f"at ({fnum(x + c * cw + cw / 2)},{fnum(y + r * rh + rh / 2)}) {{{ltx_escape(text)}}};\n"
                )
        return "".join(out)

    def _draw_image(self, o) -> str:
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        path = self._asset_path(o.get("src")) if self._asset_path else None
        if path:
            opts = [f"width={fnum(w)}pt", f"height={fnum(h)}pt"]
            if o.get("preserve_aspect_ratio") is not False:
                opts.append("keepaspectratio")
            return (
                f"\\node[anchor=center,inner sep=0pt] at ({fnum(x + w / 2)},{fnum(y + h / 2)}) "
                f"{{\\includegraphics[{','.join(opts)}]{{\\detokenize{{{path}}}}}}};\n"
            )
        label = o.get("alt") or o.get("actual_text") or o.get("label") or o.get("src") or "image"
        return (
            f"\\path[draw={{rgb,255:red,153;green,153;blue,153}},fill={{rgb,255:red,245;green,245;blue,245}}] "
            f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"
            f"\\node[anchor=center,inner sep=1pt,font=\\scriptsize,text width={fnum(max(w - 4, 1))}pt,align=center] "
            f"at ({fnum(x + w / 2)},{fnum(y + h / 2)}) {{{ltx_escape(label)}}};\n"
        )

    def _box(self, o):
        box = o.get("box")
        if isinstance(box, list) and len(box) >= 4:
            return tuple(num(v, 0) for v in box[:4])
        return None

    def _draw_component(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        fill, _ = color_expr(self._color.resolve(o.get("fill") or "#ffffff"))
        stroke = self._stroke_opts(o, default_color="#777777")
        opts = [f"fill={fill}"] if fill else []
        opts += stroke or ["draw={rgb,255:red,119;green,119;blue,119}", "line width=1pt"]
        radius = num(o.get("radius"), 4) or 0
        if radius:
            opts.append(f"rounded corners={fnum(radius)}pt")
        title = o.get("title") or o.get("name") or o.get("component") or "component"
        body = o.get("body") or o.get("label")
        out = [self._path(opts, f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})")]
        out.append(
            f"\\node[anchor=north,inner sep=2pt,font=\\scriptsize\\bfseries,text width={fnum(max(w - 6, 1))}pt,align=center] "
            f"at ({fnum(x + w / 2)},{fnum(y + 3)}) {{{ltx_escape(title)}}};\n"
        )
        if body:
            out.append(
                f"\\node[anchor=center,inner sep=2pt,font=\\scriptsize,text width={fnum(max(w - 8, 1))}pt,align=center] "
                f"at ({fnum(x + w / 2)},{fnum(y + h * 0.62)}) {{{ltx_escape(body)}}};\n"
            )
        return "".join(out)

    def _draw_use(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        label = o.get("label") or o.get("symbol") or "symbol"
        return (
            f"\\path[draw={{rgb,255:red,153;green,153;blue,153}},dash pattern=on 3pt off 2pt] "
            f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"
            f"\\node[anchor=center,inner sep=1pt,font=\\scriptsize,text width={fnum(max(w - 4, 1))}pt,align=center] "
            f"at ({fnum(x + w / 2)},{fnum(y + h / 2)}) {{{ltx_escape(label)}}};\n"
        )

    def _anchor_point(self, value):
        if is_point(value):
            return num(value[0], 0), num(value[1], 0)
        if isinstance(value, dict):
            for key in ("point", "position", "at", "center"):
                if is_point(value.get(key)):
                    return num(value[key][0], 0), num(value[key][1], 0)
            if all(k in value for k in ("x", "y")):
                return num(value.get("x"), 0), num(value.get("y"), 0)
        return None

    def _draw_connector(self, o) -> str:
        fr, to = self._anchor_point(o.get("from")), self._anchor_point(o.get("to"))
        if not (fr and to):
            return ""
        opts = self._stroke_opts(o, default_color="#000000") or ["draw={rgb,255:red,0;green,0;blue,0}", "line width=1pt"]
        if not any(opt in ("->", "<-", "<->") for opt in opts):
            opts.insert(0, "->")
        route = o.get("route") if isinstance(o.get("route"), list) else []
        pts = [fr] + [self._anchor_point(p) for p in route] + [to]
        pts = [p for p in pts if p]
        chain = " -- ".join(f"({fnum(x)},{fnum(y)})" for x, y in pts)
        out = [f"\\draw[{','.join(opts)}] {chain};\n"]
        if o.get("label"):
            mid = pts[len(pts) // 2]
            out.append(f"\\node[fill=white,inner sep=1pt,font=\\scriptsize] at ({fnum(mid[0])},{fnum(mid[1])}) {{{ltx_escape(o.get('label'))}}};\n")
        return "".join(out)

    def _draw_legend(self, o) -> str:
        box = self._box(o)
        x, y, w, _h = box if box else (0, 0, 120, 18)
        out = []
        cursor = x
        for item in o.get("items") or []:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            if isinstance(label, dict):
                label = label.get("text")
            label = label or ""
            color, _ = color_expr(self._color.resolve(item.get("color") or "#666666"))
            marker = item.get("marker") or "square"
            if marker == "line":
                out.append(f"\\draw[draw={color},line width=1pt] ({fnum(cursor)},{fnum(y + 6)}) -- ({fnum(cursor + 10)},{fnum(y + 6)});\n")
            else:
                out.append(f"\\path[fill={color},draw={color}] ({fnum(cursor)},{fnum(y + 2)}) rectangle ({fnum(cursor + 8)},{fnum(y + 10)});\n")
            out.append(f"\\node[anchor=west,inner sep=0pt,font=\\scriptsize] at ({fnum(cursor + 12)},{fnum(y + 6)}) {{{ltx_escape(label)}}};\n")
            cursor += min(max(len(str(label)) * 5 + 24, 34), max(w, 34))
        return "".join(out)

    def _draw_chip_row(self, o) -> str:
        origin = o.get("origin") or o.get("position")
        box = self._box(o)
        if is_point(origin):
            x, y = num(origin[0], 0), num(origin[1], 0)
        elif box:
            x, y = box[0], box[1]
        else:
            return ""
        height = num(o.get("height"), 18) or 18
        gap = num(o.get("gap"), 6) or 0
        fill, _ = color_expr(self._color.resolve(o.get("fill") or "#ffffff"))
        stroke, _ = color_expr(self._color.resolve(o.get("stroke") or "#cccccc"))
        out, cursor = [], x
        for item in o.get("items") or []:
            text = item.get("text") if isinstance(item, dict) else str(item)
            width = num(item.get("width"), None) if isinstance(item, dict) else None
            width = width or max(height * 1.8, len(str(text)) * 5 + 14)
            out.append(
                f"\\path[fill={fill},draw={stroke},rounded corners={fnum(height / 2)}pt] "
                f"({fnum(cursor)},{fnum(y)}) rectangle ({fnum(cursor + width)},{fnum(y + height)});\n"
            )
            out.append(f"\\node[anchor=center,inner sep=1pt,font=\\scriptsize] at ({fnum(cursor + width / 2)},{fnum(y + height / 2)}) {{{ltx_escape(text)}}};\n")
            cursor += width + gap
        return "".join(out)

    def _chart_values(self, o):
        data = o.get("data")
        if isinstance(data, list):
            vals = []
            for item in data:
                if isinstance(item, dict):
                    vals.append(num(item.get("value") or item.get("y"), None))
                else:
                    vals.append(num(item, None))
            return [v for v in vals if v is not None]
        if isinstance(data, dict):
            if isinstance(data.get("values"), list):
                return [v for v in (num(x, None) for x in data["values"]) if v is not None]
            series = data.get("series")
            if isinstance(series, list) and series:
                first = series[0]
                vals = first.get("values") if isinstance(first, dict) else first
                if isinstance(vals, list):
                    return [v for v in (num(x.get("value") if isinstance(x, dict) else x, None) for x in vals) if v is not None]
        return []

    def _draw_bar_chart(self, o) -> str:
        box = self._box(o)
        values = self._chart_values(o)
        if not (box and values):
            return ""
        x, y, w, h = box
        maxv = max(max(values), 1)
        gap = 3
        bw = max((w - gap * (len(values) + 1)) / len(values), 1)
        style = o.get("style") if isinstance(o.get("style"), dict) else {}
        fill, _ = color_expr(self._color.resolve(style.get("fill") or "#6699cc"))
        out = [f"\\draw[draw={{rgb,255:red,170;green,170;blue,170}}] ({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"]
        for i, value in enumerate(values):
            bh = h * value / maxv
            x0 = x + gap + i * (bw + gap)
            out.append(f"\\path[fill={fill}] ({fnum(x0)},{fnum(y + h - bh)}) rectangle ({fnum(x0 + bw)},{fnum(y + h)});\n")
        return "".join(out)

    def _draw_line_chart(self, o) -> str:
        box = self._box(o)
        values = self._chart_values(o)
        if not (box and len(values) >= 2):
            return ""
        x, y, w, h = box
        maxv, minv = max(values), min(values)
        span = max(maxv - minv, 1)
        pts = []
        for i, value in enumerate(values):
            xx = x + (w * i / (len(values) - 1))
            yy = y + h - ((value - minv) / span) * h
            pts.append((xx, yy))
        chain = " -- ".join(f"({fnum(px)},{fnum(py)})" for px, py in pts)
        return (
            f"\\draw[draw={{rgb,255:red,170;green,170;blue,170}}] ({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"
            f"\\draw[draw={{rgb,255:red,51;green,102;blue,170}},line width=1.2pt] {chain};\n"
        )

    def _draw_uml_box_like(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        t = o.get("type")
        radius = 9 if t == "uml.action" else 2
        opts = ["fill={rgb,255:red,255;green,255;blue,255}", "draw={rgb,255:red,85;green,85;blue,85}", "line width=1pt"]
        if radius:
            opts.append(f"rounded corners={fnum(radius)}pt")
        rows = []
        if o.get("stereotype"):
            rows.append(f"<<{o.get('stereotype')}>>")
        elif t == "uml.node_box" and o.get("kind"):
            rows.append(f"<<{o.get('kind')}>>")
        rows.append(o.get("name") or o.get("label") or t)
        for value in (o.get("entry"), o.get("do"), o.get("exit")):
            if value:
                rows.append(str(value))
        for item in (o.get("attributes") or [])[:2]:
            rows.append(item.get("name") if isinstance(item, dict) else str(item))
        for item in (o.get("operations") or [])[:2]:
            rows.append((item.get("name") + "()") if isinstance(item, dict) and item.get("name") else str(item))
        if t == "uml.component_box":
            if o.get("provided_interfaces"):
                rows.append("provides: " + ", ".join(map(str, o.get("provided_interfaces") or [])))
            if o.get("required_interfaces"):
                rows.append("requires: " + ", ".join(map(str, o.get("required_interfaces") or [])))
        out = [self._path(opts, f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)})")]
        row_h = min(13, h / max(len(rows), 1))
        for idx, row in enumerate(rows):
            weight = "\\bfseries" if idx == (1 if rows and str(rows[0]).startswith("<<") else 0) else ""
            out.append(
                f"\\node[anchor=north,inner sep=1pt,font=\\scriptsize{weight},text width={fnum(max(w - 6, 1))}pt,align=center] "
                f"at ({fnum(x + w / 2)},{fnum(y + 3 + idx * row_h)}) {{{ltx_escape(row)}}};\n"
            )
        return "".join(out)

    def _draw_uml_classifier_box(self, o) -> str:
        return self._draw_uml_box_like(o)

    def _draw_uml_component_box(self, o) -> str:
        return self._draw_uml_box_like(o)

    def _draw_uml_state_box(self, o) -> str:
        return self._draw_uml_box_like(o)

    def _draw_uml_action(self, o) -> str:
        return self._draw_uml_box_like(o)

    def _draw_uml_artifact_box(self, o) -> str:
        return self._draw_uml_box_like(o)

    def _draw_uml_node_box(self, o) -> str:
        return self._draw_uml_box_like(o)

    def _draw_uml_lifeline(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        head_h = min(max(num(o.get("head_height"), 28) or 28, 18), h)
        cx = x + w / 2
        name = o.get("name") or o.get("id") or "lifeline"
        type_name = o.get("type_name")
        label = f"{name}: {type_name}" if type_name else str(name)
        return (
            f"\\path[fill={{rgb,255:red,255;green,255;blue,255}},draw={{rgb,255:red,85;green,85;blue,85}}] "
            f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + head_h)});\n"
            f"\\draw[dash pattern=on 4pt off 3pt,draw={{rgb,255:red,85;green,85;blue,85}}] ({fnum(cx)},{fnum(y + head_h)}) -- ({fnum(cx)},{fnum(y + h)});\n"
            f"\\node[anchor=center,inner sep=1pt,font=\\scriptsize,text width={fnum(max(w - 4, 1))}pt,align=center] "
            f"at ({fnum(cx)},{fnum(y + head_h / 2)}) {{{ltx_escape(label)}}};\n"
        )

    def _draw_uml_activation_bar(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        return (
            f"\\path[fill={{rgb,255:red,255;green,255;blue,255}},draw={{rgb,255:red,85;green,85;blue,85}}] "
            f"({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"
        )

    def _actor_glyph(self, cx, cy, size):
        r = size * 0.18
        return (
            f"\\draw ({fnum(cx)},{fnum(cy - size * 0.34)}) circle ({fnum(r)}pt);\n"
            f"\\draw ({fnum(cx)},{fnum(cy - size * 0.16)}) -- ({fnum(cx)},{fnum(cy + size * 0.28)});\n"
            f"\\draw ({fnum(cx - size * 0.28)},{fnum(cy)}) -- ({fnum(cx + size * 0.28)},{fnum(cy)});\n"
            f"\\draw ({fnum(cx)},{fnum(cy + size * 0.28)}) -- ({fnum(cx - size * 0.22)},{fnum(cy + size * 0.58)});\n"
            f"\\draw ({fnum(cx)},{fnum(cy + size * 0.28)}) -- ({fnum(cx + size * 0.22)},{fnum(cy + size * 0.58)});\n"
        )

    def _draw_uml_actor(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        size = min(w, h) * 0.72
        cx, cy = x + w / 2, y + h * 0.42
        out = [self._actor_glyph(cx, cy, size)]
        if o.get("name"):
            out.append(f"\\node[anchor=north,inner sep=1pt,font=\\scriptsize] at ({fnum(cx)},{fnum(y + h - 12)}) {{{ltx_escape(o.get('name'))}}};\n")
        return "".join(out)

    def _draw_uml_lollipop(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        cx, cy, r = x + w / 2, y + h / 2, max(2, min(w, h) / 2 - 2)
        out = [f"\\draw[fill=white] ({fnum(cx)},{fnum(cy)}) circle ({fnum(r)}pt);\n"]
        if o.get("name"):
            out.append(f"\\node[anchor=north,inner sep=1pt,font=\\scriptsize] at ({fnum(cx)},{fnum(y + h)}) {{{ltx_escape(o.get('name'))}}};\n")
        return "".join(out)

    def _draw_uml_socket(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        cx, cy, r = x + w / 2, y + h / 2, max(2, min(w, h) / 2 - 2)
        out = [f"\\draw ({fnum(cx + r)},{fnum(cy - r)}) arc[start angle=-90,end angle=90,radius={fnum(r)}pt];\n"]
        if o.get("name"):
            out.append(f"\\node[anchor=north,inner sep=1pt,font=\\scriptsize] at ({fnum(cx)},{fnum(y + h)}) {{{ltx_escape(o.get('name'))}}};\n")
        return "".join(out)

    def _draw_uml_activity_node(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        cx, cy = x + w / 2, y + h / 2
        kind = o.get("kind")
        if kind == "decision":
            out = [self._path(["fill=white", "draw={rgb,255:red,85;green,85;blue,85}"],
                              f"({fnum(cx)},{fnum(y)}) -- ({fnum(x + w)},{fnum(cy)}) -- ({fnum(cx)},{fnum(y + h)}) -- ({fnum(x)},{fnum(cy)}) -- cycle")]
        elif kind in ("fork", "join"):
            out = [f"\\path[fill={{rgb,255:red,85;green,85;blue,85}}] ({fnum(x)},{fnum(cy - 2)}) rectangle ({fnum(x + w)},{fnum(cy + 2)});\n"]
        else:
            out = [f"\\draw[fill={{rgb,255:red,85;green,85;blue,85}}] ({fnum(cx)},{fnum(cy)}) circle ({fnum(max(3, min(w, h) / 4))}pt);\n"]
        if o.get("name"):
            out.append(f"\\node[anchor=center,inner sep=1pt,font=\\scriptsize] at ({fnum(cx)},{fnum(cy)}) {{{ltx_escape(o.get('name'))}}};\n")
        return "".join(out)

    def _draw_uml_pseudostate(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        cx, cy, r = x + w / 2, y + h / 2, max(2, min(w, h) / 2 - 1)
        if o.get("kind") == "final":
            return f"\\draw ({fnum(cx)},{fnum(cy)}) circle ({fnum(r)}pt);\n\\path[fill={{rgb,255:red,85;green,85;blue,85}}] ({fnum(cx)},{fnum(cy)}) circle ({fnum(max(1, r - 4))}pt);\n"
        return f"\\path[fill={{rgb,255:red,85;green,85;blue,85}}] ({fnum(cx)},{fnum(cy)}) circle ({fnum(r)}pt);\n"

    def _draw_uml_marker_glyph(self, o) -> str:
        pos = o.get("position") or o.get("origin")
        if not is_point(pos):
            return ""
        x, y = num(pos[0], 0), num(pos[1], 0)
        size = num(o.get("size"), 12) or 12
        half = size / 2
        color, _ = color_expr(self._color.resolve(o.get("color") or "#000000"))
        kind = str(o.get("kind") or "")
        if "triangle" in kind or "arrow" in kind:
            geom = f"({fnum(x - half)},{fnum(y - half)}) -- ({fnum(x + half)},{fnum(y)}) -- ({fnum(x - half)},{fnum(y + half)}) -- cycle"
        else:
            geom = f"({fnum(x)},{fnum(y - half)}) -- ({fnum(x + half)},{fnum(y)}) -- ({fnum(x)},{fnum(y + half)}) -- ({fnum(x - half)},{fnum(y)}) -- cycle"
        opts = [f"draw={color}", "line width=1pt"]
        opts.append(f"fill={color}" if "filled" in kind else "fill=white")
        return self._path(opts, geom)

    def _draw_uml_fragment_frame(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        kind = o.get("kind") or "fragment"
        return (
            f"\\path[draw={{rgb,255:red,85;green,85;blue,85}}] ({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"
            f"\\node[anchor=north west,inner sep=2pt,font=\\scriptsize\\bfseries] at ({fnum(x)},{fnum(y)}) {{{ltx_escape(kind)}}};\n"
        )

    def _draw_uml_swimlane(self, o) -> str:
        return self._draw_uml_fragment_frame({**o, "kind": o.get("name") or "swimlane"})

    def _draw_uml_timing_lane(self, o) -> str:
        box = self._box(o)
        if not box:
            return ""
        x, y, w, h = box
        states = o.get("states") if isinstance(o.get("states"), list) else []
        out = [f"\\path[draw={{rgb,255:red,85;green,85;blue,85}}] ({fnum(x)},{fnum(y)}) rectangle ({fnum(x + w)},{fnum(y + h)});\n"]
        out.append(f"\\node[anchor=west,inner sep=1pt,font=\\scriptsize\\bfseries] at ({fnum(x + 3)},{fnum(y + 8)}) {{{ltx_escape(o.get('name') or 'timing')}}};\n")
        if states:
            step = w / max(len(states), 1)
            for idx, state in enumerate(states):
                out.append(f"\\node[anchor=center,inner sep=1pt,font=\\scriptsize] at ({fnum(x + step * (idx + 0.5))},{fnum(y + h / 2)}) {{{ltx_escape(state)}}};\n")
        return "".join(out)
