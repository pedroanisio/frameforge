"""SvgPainter — the SVG backend (a ScenePainter adapter).

All SVG string construction extracted verbatim from the monolithic Renderer in
tooling/render_fixtures.py (DDD migration, step 4): the per-page <defs>/id state,
gradient + clip registration, every element constructor (rect/ellipse/circle/
line/poly/path/image/text), grouping, and document assembly.

The builder (Renderer) now holds one of these and emits by calling its methods,
in the same document order as before — so the gradient/clip id sequence and the
exact byte output are unchanged. Colour-token dereference is delegated to the
injected ColorResolver (needed to emit gradient stops); no other token/style
knowledge lives here.
"""
from __future__ import annotations

import math

from frameforge.rendering.domain.geometry import esc, fnum, num
from frameforge.rendering.domain.services.stroke_resolver import StrokeResolver

# Arrowhead `<marker>` shapes. Kind names are the v2 marker refs the grammar
# allows for `arrow_start` / `arrow_end` (grammar/frameforge-v2-style.ebnf
# L190-191; glyph set in frameforge-v2.ebnf L631). Each entry is
# (path_d, viewBox, markerWidth, markerHeight, refX, refY, mode):
#   mode "fill"   — colour fill (solid arrowhead)
#   mode "hollow" — white fill + colour stroke (UML generalization/aggregation)
#   mode "open"   — colour stroke, no fill (open V)
_MARKER_SHAPES: dict[str, tuple[str, str, float, float, float, float, str]] = {
    "filled_triangle": ("M0,0 L8,2.5 L0,5 Z", "0 0 8 5", 8, 5, 8, 2.5, "fill"),
    "hollow_triangle": ("M0,0 L10,5 L0,10 Z", "0 0 10 10", 10, 10, 10, 5, "hollow"),
    "filled_diamond": ("M0,5 L6,0 L12,5 L6,10 Z", "0 0 12 10", 12, 10, 12, 5, "fill"),
    "hollow_diamond": ("M0,5 L6,0 L12,5 L6,10 Z", "0 0 12 10", 12, 10, 12, 5, "hollow"),
    "open_arrow": ("M0,0 L10,5 L0,10", "0 0 10 10", 10, 10, 10, 5, "open"),
}
_DEFAULT_MARKER = "filled_triangle"


class SvgPainter:
    #: This backend composites shadow/glow/blur via SVG `<filter>` chains, so
    #: an effect is really rendered (the Renderer emits no unsupported-effect
    #: warning). Backends that cannot (TikZ) set this False so the loss is
    #: reported, never silent (#44 / #53).
    supports_filters = True

    def __init__(self, color_resolver, warn=None):
        self._color = color_resolver
        # Optional structured-warning sink: `warn(kind, message, **details)`.
        # The Renderer injects its diagnostics recorder; a bare painter stays
        # silent (None) so the adapter remains usable standalone.
        self._warn = warn
        self._gid = 0
        self._defs = []          # per-page <defs> entries (gradients, clip paths, markers, filters)
        self._ids: set[str] = set()                      # def ids allocated on this page
        self._markers: dict[tuple[str, str], str] = {}   # (kind, colour) -> marker id
        self._filters: dict[tuple, str] = {}             # effect signature -> filter id

    # ---- per-page backend state ------------------------------------------- #
    def new_page(self):
        self._defs = []
        self._ids = set()
        self._markers = {}
        self._filters = {}

    def has_def_id(self, def_id: str) -> bool:
        """True when this page has already allocated a `<defs>` entry with `def_id`.

        Used by the builder to flag string `mask`/`url(#...)` references that
        point at nothing (silent no-ops in the rendered SVG)."""
        return def_id in self._ids

    def _note_warning(self, kind, message, **details):
        if self._warn is not None:
            self._warn(kind, message, **details)

    # ---- small attribute / style helpers ---------------------------------- #
    @staticmethod
    def fill_attr(fill, fill_opacity=None, fill_rule=None):
        """The SVG `fill` attribute for a resolved paint value (None ⇒ 'none')."""
        attr = f' fill="{esc(fill)}"' if fill is not None else ' fill="none"'
        if fill_opacity is not None:
            attr += f' fill-opacity="{fnum(num(fill_opacity, 1))}"'
        if fill_rule:
            attr += f' fill-rule="{esc(fill_rule)}"'
        return attr

    @staticmethod
    def anchor(align):
        return {"center": "middle", "right": "end", "end": "middle"}.get(align, "start")

    @staticmethod
    def font_style(st, size):
        style = f'font-family:{esc(st["family"])};font-size:{fnum(size)}px;fill:{esc(st["color"])}'
        if str(st["weight"]) not in ("normal", "400"):
            style += f';font-weight:{esc(st["weight"])}'
        if st["italic"]:
            style += ";font-style:italic"
        for key, css_name in (
            ("font_stretch", "font-stretch"),
            ("font_variant", "font-variant"),
            ("font_variant_caps", "font-variant-caps"),
            ("font_variant_numeric", "font-variant-numeric"),
            ("font_variant_ligatures", "font-variant-ligatures"),
            ("font_feature_settings", "font-feature-settings"),
            ("font_variation_settings", "font-variation-settings"),
            ("font_kerning", "font-kerning"),
            ("letter_spacing", "letter-spacing"),
            ("word_spacing", "word-spacing"),
            ("text_align_last", "text-align-last"),
            ("text_indent", "text-indent"),
            ("text_decoration", "text-decoration"),
            ("text_transform", "text-transform"),
            ("text_shadow", "text-shadow"),
            ("white_space", "white-space"),
            ("word_break", "word-break"),
            ("overflow_wrap", "overflow-wrap"),
            ("hyphens", "hyphens"),
            ("hanging_punctuation", "hanging-punctuation"),
            ("hyphenate_character", "hyphenate-character"),
            ("hyphenate_limit_chars", "hyphenate-limit-chars"),
            ("tab_size", "tab-size"),
            ("writing_mode", "writing-mode"),
            ("direction", "direction"),
            ("unicode_bidi", "unicode-bidi"),
        ):
            if st.get(key):
                style += f';{css_name}:{esc(st[key])}'
        if st.get("css"):
            style += ";" + esc(str(st["css"]).strip().rstrip(";"))
        return style

    # ---- paint registry (gradients + clips share the id counter) ---------- #
    @staticmethod
    def _angle_deg(value):
        """A CSS Angle ("<n>deg|rad|grad|turn" or a bare number = degrees) to
        degrees, or None when absent/unparseable."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip().lower()
        for unit, factor in (("deg", 1.0), ("grad", 0.9), ("rad", 180.0 / math.pi),
                             ("turn", 360.0)):
            if s.endswith(unit):
                try:
                    return float(s[: -len(unit)].strip()) * factor
                except ValueError:
                    return None
        try:
            return float(s)
        except ValueError:
            return None

    _AT_KEYWORDS = {"left": ("x", 0.0), "right": ("x", 1.0), "top": ("y", 0.0),
                    "bottom": ("y", 1.0), "center": (None, 0.5)}

    @classmethod
    def _radial_center(cls, at):
        """A Gradient `at` (keywords, "x% y%", or a point) to (cx, cy) unit
        fractions of the bounding box, or None when absent/unparseable."""
        if at is None:
            return None
        if isinstance(at, (list, tuple)) and len(at) >= 2:
            vals = [num(v, None) for v in at[:2]]
            if any(v is None for v in vals):
                return None
            return tuple(v / 100.0 if v > 1 else float(v) for v in vals)
        if not isinstance(at, str):
            return None
        cx = cy = None
        for token in at.strip().lower().split():
            if token in cls._AT_KEYWORDS:
                axis, frac = cls._AT_KEYWORDS[token]
                if axis == "x" or (axis is None and cx is None):
                    cx = frac
                elif axis == "y" or axis is None:
                    cy = frac
            elif token.endswith("%"):
                v = num(token[:-1], None)
                if v is None:
                    return None
                if cx is None:
                    cx = v / 100.0
                elif cy is None:
                    cy = v / 100.0
            else:
                return None
        if cx is None and cy is None:
            return None
        return (0.5 if cx is None else cx, 0.5 if cy is None else cy)

    def _gradient_geometry(self, g, kind):
        """The geometry attribute string for one gradient spec (possibly "").

        * linear `angle` → x1/y1/x2/y2 (CSS convention: 0 = up, 90 = right,
          180 = down; the gradient line runs through the box centre). This is a
          centre-line mapping, not the CSS corner-projection — exact for the
          axis-aligned angles and a close approximation for diagonals.
        * radial/conic `at` → cx/cy (+ fx/fy focus at the same point).
        * `repeating` → spreadMethod="repeat".

        A spec with none of those fields returns "" so its emitted bytes are
        identical to the pre-geometry renderer (golden protection)."""
        attrs = ""
        if kind == "linear":
            angle = self._angle_deg(g.get("angle"))
            if angle is not None:
                rad = math.radians(angle % 360.0)
                dx, dy = math.sin(rad), -math.cos(rad)
                pct = lambda v: fnum(round(v, 3))  # noqa: E731 — local formatter
                attrs += (f' x1="{pct(50 - 50 * dx)}%" y1="{pct(50 - 50 * dy)}%"'
                          f' x2="{pct(50 + 50 * dx)}%" y2="{pct(50 + 50 * dy)}%"')
        else:
            center = self._radial_center(g.get("at"))
            if center is not None:
                cx, cy = (fnum(round(v * 100, 3)) for v in center)
                attrs += f' cx="{cx}%" cy="{cy}%" fx="{cx}%" fy="{cy}%"'
        if g.get("repeating"):
            attrs += ' spreadMethod="repeat"'
        return attrs

    def gradient(self, g):
        self._gid += 1
        gid = f"g{self._gid}"
        self._ids.add(gid)
        kind = g.get("kind")
        stops = []
        n = max(1, len(g.get("stops", [])))
        for i, st in enumerate(g.get("stops", [])):
            off = st.get("position")
            o = num(off)
            if o is None and isinstance(off, str) and off.strip().endswith("%"):
                o = num(off.strip()[:-1])
            if o is None:
                o = i / (n - 1) * 100 if n > 1 else 0
            col = self._color.resolve(st.get("color")) or "#000"
            stops.append(f'<stop offset="{fnum(o)}%" stop-color="{esc(col)}"/>')
        body = "".join(stops)
        geo = self._gradient_geometry(g, kind)
        if kind == "radial" or kind == "conic":     # conic ≈ radial fallback
            if kind == "conic":
                self._note_warning(
                    "gradient_conic_fallback",
                    "conic gradient approximated as a radial gradient in the SVG proxy "
                    "(no native SVG conic primitive); verify against the raster",
                )
            self._defs.append(f'<radialGradient id="{gid}"{geo}>{body}</radialGradient>')
        else:
            self._defs.append(f'<linearGradient id="{gid}"{geo}>{body}</linearGradient>')
        return f"url(#{gid})"

    # Pattern tile geometry per kind: which primitives one `spacing`-sized tile
    # draws (lines centred in the tile so tile-edge clipping never halves them),
    # and the default rotation. The SDK's `hatch()` passes angle=45 explicitly;
    # these defaults mirror it for raw model dicts.
    _PATTERN_DEFAULT_ANGLE = {"hatch": 45.0, "cross_hatch": 45.0, "dots": 0.0, "grid": 0.0}

    def pattern(self, spec):
        """Register a tiled `<pattern>` def for a Pattern paint
        (`kind: pattern`, `pattern: hatch|cross_hatch|dots|grid`) and return its
        `url(#...)` fill value. Honours the model fields: `spacing` sizes the
        tile, `angle` rotates it (patternTransform), `stroke` draws the motif,
        `background` fills the tile behind it."""
        self._gid += 1
        pid = f"pat{self._gid}"
        self._ids.add(pid)
        kind = spec.get("pattern")
        s = num(spec.get("spacing"), None) or 8.0
        fg = self._color.resolve(spec.get("stroke")) or "#333333"
        bg = self._color.resolve(spec.get("background"))
        angle = self._angle_deg(spec.get("angle"))
        if angle is None:
            angle = self._PATTERN_DEFAULT_ANGLE.get(kind, 0.0)
        half, size = fnum(s / 2), fnum(s)
        body = ""
        if bg and bg != "none":
            body += f'<rect width="{size}" height="{size}" fill="{esc(bg)}"/>'
        line_v = (f'<line x1="{half}" y1="0" x2="{half}" y2="{size}" '
                  f'stroke="{esc(fg)}" stroke-width="1"/>')
        line_h = (f'<line x1="0" y1="{half}" x2="{size}" y2="{half}" '
                  f'stroke="{esc(fg)}" stroke-width="1"/>')
        if kind == "hatch":
            body += line_v
        elif kind in ("cross_hatch", "grid"):
            body += line_v + line_h
        elif kind == "dots":
            r = max(0.75, s * 0.15)
            body += f'<circle cx="{half}" cy="{half}" r="{fnum(r)}" fill="{esc(fg)}"/>'
        else:                       # unknown pattern arm: background-only tile
            self._note_warning("pattern_unknown", f"unknown pattern kind {kind!r}; "
                               "tile renders background only")
        transform = f' patternTransform="rotate({fnum(angle)})"' if angle % 360 else ""
        self._defs.append(
            f'<pattern id="{pid}" patternUnits="userSpaceOnUse" '
            f'width="{size}" height="{size}"{transform}>{body}</pattern>'
        )
        return f"url(#{pid})"

    def mask_def(self, body):
        """Register a generated `<mask>` def (luminance mask) and return its id."""
        self._gid += 1
        mid = f"mask{self._gid}"
        self._ids.add(mid)
        self._defs.append(f'<mask id="{mid}">{body}</mask>')
        return mid

    def image_pattern(self, href, x, y, w, h, preserve_aspect_ratio="xMidYMid slice"):
        self._gid += 1
        pid = f"pat{self._gid}"
        self._ids.add(pid)
        self._defs.append(
            f'<pattern id="{pid}" patternUnits="userSpaceOnUse" '
            f'x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}">'
            f'<image x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
            f'href="{esc(href)}" preserveAspectRatio="{esc(preserve_aspect_ratio)}"/>'
            f'</pattern>'
        )
        return f"url(#{pid})"

    def clip_rect(self, x, y, w, h):
        self._gid += 1
        cid = f"clip{self._gid}"
        self._ids.add(cid)
        self._defs.append(f'<clipPath id="{cid}">'
                          f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}"/></clipPath>')
        return cid

    def clip_ellipse(self, cx, cy, rx, ry):
        self._gid += 1
        cid = f"clip{self._gid}"
        self._ids.add(cid)
        self._defs.append(f'<clipPath id="{cid}">'
                          f'<ellipse cx="{fnum(cx)}" cy="{fnum(cy)}" '
                          f'rx="{fnum(rx)}" ry="{fnum(ry)}"/></clipPath>')
        return cid

    def clip_polygon(self, points):
        self._gid += 1
        cid = f"clip{self._gid}"
        self._ids.add(cid)
        pts = " ".join(f"{fnum(x)},{fnum(y)}" for x, y in points)
        self._defs.append(f'<clipPath id="{cid}"><polygon points="{esc(pts)}"/></clipPath>')
        return cid

    def clip_path_d(self, d):
        self._gid += 1
        cid = f"clip{self._gid}"
        self._ids.add(cid)
        self._defs.append(f'<clipPath id="{cid}"><path d="{esc(d)}"/></clipPath>')
        return cid

    def clip_wrap(self, inner, clip_id):
        return f'<g clip-path="url(#{clip_id})">{inner}</g>'

    def marker(self, color: str, kind: str = _DEFAULT_MARKER) -> str:
        """Register an arrowhead `<marker>` for (kind, colour); return its id.

        Deduped per page by (kind, colour): repeated calls reuse one `<defs>`
        entry. Unknown kinds fall back to the default filled triangle. This is
        additive — no marker is registered unless a stroke requests an arrow."""
        if kind not in _MARKER_SHAPES:
            kind = _DEFAULT_MARKER
        key = (kind, color)
        mid = self._markers.get(key)
        if mid is not None:
            return mid
        mid = f"ah{len(self._markers) + 1}"
        self._ids.add(mid)
        self._markers[key] = mid
        self._defs.append(self._marker_def(mid, color, kind))
        return mid

    @staticmethod
    def _marker_def(mid: str, color: str, kind: str) -> str:
        d, vb, mw, mh, refx, refy, mode = _MARKER_SHAPES[kind]
        if mode == "hollow":
            paint = f'fill="#FFFFFF" stroke="{esc(color)}" stroke-width="1"'
        elif mode == "open":
            paint = f'fill="none" stroke="{esc(color)}" stroke-width="1.5"'
        else:
            paint = f'fill="{esc(color)}"'
        return (f'<marker id="{esc(mid)}" viewBox="{vb}" markerWidth="{fnum(mw)}" '
                f'markerHeight="{fnum(mh)}" refX="{fnum(refx)}" refY="{fnum(refy)}" '
                f'orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
                f'<path d="{d}" {paint}/></marker>')

    def filter_effect(self, kind: str, params: dict) -> str:
        """Register a shadow/glow `<filter>` for params; return its id (deduped).

        Additive — only called for objects/styles that declare supported effects."""
        if kind in {"turbulence", "displacement_map", "diffuse_lighting", "specular_lighting"}:
            key = (kind, tuple(sorted((k, str(v)) for k, v in params.items())))
            fid = self._filters.get(key)
            if fid is not None:
                return fid
            fid = f"fx{len(self._filters) + 1}"
            self._ids.add(fid)
            self._filters[key] = fid
            self._defs.append(self._filter_def(fid, kind, params))
            return fid
        if kind == "blur":
            blur = fnum(num(params.get("blur"), 0))
            key = ("blur", blur)
            fid = self._filters.get(key)
            if fid is not None:
                return fid
            fid = f"fx{len(self._filters) + 1}"
            self._ids.add(fid)
            self._filters[key] = fid
            self._defs.append(self._filter_def(fid, kind, params))
            return fid
        color = params.get("color") or ("#000000" if kind == "shadow" else "#FFD700")
        blur = fnum(num(params.get("blur"), 4))
        opacity = fnum(num(params.get("opacity"), 0.14 if kind == "shadow" else 0.55))
        if kind == "shadow":
            dx = fnum(num(params.get("dx"), 0))
            dy = fnum(num(params.get("dy"), 2))
            key = ("shadow", dx, dy, blur, color, opacity)
        else:
            key = ("glow", blur, color, opacity)
        fid = self._filters.get(key)
        if fid is not None:
            return fid
        fid = f"fx{len(self._filters) + 1}"
        self._ids.add(fid)
        self._filters[key] = fid
        self._defs.append(self._filter_def(fid, kind, params))
        return fid

    def filter_wrap(self, inner: str, filter_id: str) -> str:
        return f'<g filter="url(#{filter_id})">{inner}</g>'

    @staticmethod
    def format_transform(ops) -> str:
        """Format a neutral transform op list (StyleValues.transform_ops) to an SVG
        transform string — `fn(arg arg ...)` joined by spaces; `raw` passes through."""
        parts = []
        for fn, args in ops:
            s = (args[0] if args else "") if fn == "raw" else f"{fn}({' '.join(args)})"
            if s:
                parts.append(s)
        return " ".join(parts)

    def transform_group(self, inner: str, transform) -> str:
        return f'<g transform="{esc(self.format_transform(transform))}">{inner}</g>'

    def embedded_svg(self, x, y, w, h, *, viewbox, color, title, body) -> str:
        """Embed a foreign SVG fragment (e.g. a MathJax render) as a sized,
        titled `<svg>` element. Backend-specific: a non-SVG backend would
        implement this differently (or fall back)."""
        return (f'<svg x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" '
                f'height="{fnum(h)}" viewBox="{esc(viewbox)}" '
                f'preserveAspectRatio="xMidYMid meet" role="img" focusable="false" '
                f'color="{color}" data-frameforge-math="true">'
                f'<title>{esc(title)}</title>{body}</svg>')

    @staticmethod
    def metadata_group(inner: str, attrs: dict[str, str]) -> str:
        """Wrap ``inner`` in a ``<g>`` carrying non-visual metadata attributes
        (e.g. ``data-reading-order``). Purely structural: no paint effect."""
        rendered = "".join(f' {name}="{esc(str(value))}"'
                           for name, value in attrs.items() if value)
        return f"<g{rendered}>{inner}</g>" if rendered else inner

    @staticmethod
    def style_group(inner: str, attrs: dict[str, str], raw: str = "") -> str:
        # `raw` carries the bounded `css` escape (§8.4) for non-text objects, which
        # have no inline style of their own; text emits its css via font_style().
        style = ";".join(f"{name}:{value}" for name, value in attrs.items() if value)
        if raw:
            raw = str(raw).strip().rstrip(";")
            style = f"{style};{raw}" if style else raw
        return f'<g style="{esc(style)}">{inner}</g>' if style else inner

    @staticmethod
    def _filter_def(fid: str, kind: str, p: dict) -> str:
        if kind == "turbulence":
            return SvgPainter._turbulence_filter_def(fid, p)
        if kind == "displacement_map":
            return SvgPainter._displacement_filter_def(fid, p)
        if kind == "diffuse_lighting":
            return SvgPainter._lighting_filter_def(fid, p, specular=False)
        if kind == "specular_lighting":
            return SvgPainter._lighting_filter_def(fid, p, specular=True)
        if kind == "blur":
            blur = fnum(num(p.get("blur"), 0))
            return (f'<filter id="{esc(fid)}" x="-20%" y="-20%" width="140%" height="140%">'
                    f'<feGaussianBlur in="SourceGraphic" stdDeviation="{blur}"/>'
                    f'</filter>')
        color = p.get("color") or ("#000000" if kind == "shadow" else "#FFD700")
        blur = fnum(num(p.get("blur"), 4))
        if kind == "shadow":
            dx = fnum(num(p.get("dx"), 0))
            dy = fnum(num(p.get("dy"), 2))
            opacity = fnum(num(p.get("opacity"), 0.14))
            # Region padded so the offset blur is not clipped at the edges.
            return (f'<filter id="{esc(fid)}" x="-20%" y="-20%" width="140%" height="140%">'
                    f'<feGaussianBlur in="SourceAlpha" stdDeviation="{blur}"/>'
                    f'<feOffset dx="{dx}" dy="{dy}" result="off"/>'
                    f'<feFlood flood-color="{esc(color)}" flood-opacity="{opacity}"/>'
                    f'<feComposite in2="off" operator="in" result="shadow"/>'
                    f'<feMerge><feMergeNode in="shadow"/><feMergeNode in="SourceGraphic"/></feMerge>'
                    f'</filter>')
        opacity = fnum(num(p.get("opacity"), 0.55))
        return (f'<filter id="{esc(fid)}" x="-50%" y="-50%" width="200%" height="200%">'
                f'<feGaussianBlur in="SourceAlpha" stdDeviation="{blur}"/>'
                f'<feFlood flood-color="{esc(color)}" flood-opacity="{opacity}"/>'
                f'<feComposite in2="SourceAlpha" operator="in" result="glow"/>'
                f'<feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge>'
                f'</filter>')

    @staticmethod
    def _turbulence_filter_def(fid: str, p: dict) -> str:
        base = SvgPainter._base_frequency(p.get("base_frequency", p.get("value", 0.035)))
        octaves = int(num(p.get("num_octaves"), 2) or 2)
        seed = int(num(p.get("seed"), 0) or 0)
        noise_type = p.get("type") or "fractalNoise"
        stitch = p.get("stitch_tiles") or "noStitch"
        opacity = fnum(num(p.get("opacity"), 0.35))
        return (f'<filter id="{esc(fid)}" x="-20%" y="-20%" width="140%" height="140%">'
                f'<feTurbulence type="{esc(noise_type)}" baseFrequency="{esc(base)}" '
                f'numOctaves="{octaves}" seed="{seed}" stitchTiles="{esc(stitch)}" result="noise"/>'
                f'<feComponentTransfer in="noise" result="texture">'
                f'<feFuncA type="linear" slope="{opacity}"/></feComponentTransfer>'
                f'<feBlend in="SourceGraphic" in2="texture" mode="{esc(p.get("mode") or "multiply")}"/>'
                f'</filter>')

    @staticmethod
    def _displacement_filter_def(fid: str, p: dict) -> str:
        base = SvgPainter._base_frequency(p.get("base_frequency", 0.035))
        octaves = int(num(p.get("num_octaves"), 2) or 2)
        seed = int(num(p.get("seed"), 0) or 0)
        scale = fnum(num(p.get("scale", p.get("value")), 12))
        return (f'<filter id="{esc(fid)}" x="-20%" y="-20%" width="140%" height="140%">'
                f'<feTurbulence type="{esc(p.get("type") or "fractalNoise")}" baseFrequency="{esc(base)}" '
                f'numOctaves="{octaves}" seed="{seed}" result="noise"/>'
                f'<feDisplacementMap in="SourceGraphic" in2="noise" scale="{scale}" '
                f'xChannelSelector="{esc(p.get("x_channel") or "R")}" '
                f'yChannelSelector="{esc(p.get("y_channel") or "G")}"/>'
                f'</filter>')

    @staticmethod
    def _lighting_filter_def(fid: str, p: dict, *, specular: bool) -> str:
        surface = fnum(num(p.get("surface_scale"), 2))
        color = p.get("lighting_color") or "#ffffff"
        light = SvgPainter._light_node(p)
        if specular:
            constant = fnum(num(p.get("specular_constant"), 0.8))
            exponent = fnum(num(p.get("specular_exponent"), 20))
            primitive = (f'<feSpecularLighting in="SourceAlpha" surfaceScale="{surface}" '
                         f'specularConstant="{constant}" specularExponent="{exponent}" '
                         f'lighting-color="{esc(color)}" result="light">{light}</feSpecularLighting>'
                         f'<feComposite in="light" in2="SourceAlpha" operator="in" result="spec"/>'
                         f'<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="spec"/></feMerge>')
        else:
            constant = fnum(num(p.get("diffuse_constant"), p.get("value", 1)))
            primitive = (f'<feDiffuseLighting in="SourceAlpha" surfaceScale="{surface}" '
                         f'diffuseConstant="{constant}" lighting-color="{esc(color)}" '
                         f'result="light">{light}</feDiffuseLighting>'
                         f'<feComposite in="light" in2="SourceGraphic" operator="arithmetic" '
                         f'k1="1" k2="0" k3="0" k4="0"/>')
        return f'<filter id="{esc(fid)}" x="-30%" y="-30%" width="160%" height="160%">{primitive}</filter>'

    @staticmethod
    def _light_node(p: dict) -> str:
        if p.get("x") is not None or p.get("y") is not None or p.get("z") is not None:
            attrs = (
                f'x="{fnum(num(p.get("x"), 0))}" '
                f'y="{fnum(num(p.get("y"), 0))}" '
                f'z="{fnum(num(p.get("z"), 80))}"'
            )
            if p.get("points_at_x") is not None or p.get("points_at_y") is not None or p.get("points_at_z") is not None:
                attrs += (
                    f' pointsAtX="{fnum(num(p.get("points_at_x"), 0))}"'
                    f' pointsAtY="{fnum(num(p.get("points_at_y"), 0))}"'
                    f' pointsAtZ="{fnum(num(p.get("points_at_z"), 0))}"'
                )
                return f"<feSpotLight {attrs}/>"
            return f"<fePointLight {attrs}/>"
        return (f'<feDistantLight azimuth="{fnum(num(p.get("azimuth"), 225))}" '
                f'elevation="{fnum(num(p.get("elevation"), 45))}"/>')

    @staticmethod
    def _base_frequency(value) -> str:
        if isinstance(value, (list, tuple)):
            return " ".join(fnum(num(v, 0.035)) for v in value[:2])
        n = num(value, None)
        return fnum(n) if n is not None else str(value)

    # ---- primitives ------------------------------------------------------- #
    @staticmethod
    def _stroke(stroke):
        """Format a neutral `Stroke` value object (or None) to an SVG fragment."""
        return StrokeResolver.format_attr(stroke)

    def _marker_attrs(self, markers):
        """Format a neutral `Markers` value object (or None) to SVG marker-ref
        attributes, registering the needed `<marker>` defs in document order."""
        if markers is None:
            return ""
        out = ""
        if markers.start:
            out += f' marker-start="url(#{self.marker(markers.color, markers.start)})"'
        if markers.end:
            out += f' marker-end="url(#{self.marker(markers.color, markers.end)})"'
        return out

    def rect(self, x, y, w, h, fill, stroke, radius=0, fill_opacity=None):
        rr = f' rx="{fnum(radius)}"' if radius else ""
        return (f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" '
                f'height="{fnum(h)}"{rr}{self.fill_attr(fill, fill_opacity)}{self._stroke(stroke)}/>')

    def ellipse(self, cx, cy, rx, ry, fill, stroke, fill_opacity=None):
        return (f'<ellipse cx="{fnum(cx)}" cy="{fnum(cy)}" rx="{fnum(rx)}" '
                f'ry="{fnum(ry)}"{self.fill_attr(fill, fill_opacity)}{self._stroke(stroke)}/>')

    def circle(self, cx, cy, r, fill, stroke, fill_opacity=None):
        return (f'<circle cx="{fnum(cx)}" cy="{fnum(cy)}" r="{fnum(r)}"'
                f'{self.fill_attr(fill, fill_opacity)}{self._stroke(stroke)}/>')

    def line(self, x1, y1, x2, y2, stroke, markers=None, extra=""):
        return (f'<line x1="{fnum(x1)}" y1="{fnum(y1)}" '
                f'x2="{fnum(x2)}" y2="{fnum(y2)}"{self._stroke(stroke)}'
                f'{self._marker_attrs(markers)}{extra}/>')

    def poly(self, tag, points, fill, stroke, fill_opacity=None, fill_rule=None,
             markers=None, extra=""):
        return (f'<{tag} points="{points}"{self.fill_attr(fill, fill_opacity, fill_rule)}'
                f'{self._stroke(stroke)}{self._marker_attrs(markers)}{extra}/>')

    def path(self, d, fill, stroke, fill_opacity=None, fill_rule=None,
             markers=None, extra=""):
        return (f'<path d="{esc(d)}"{self.fill_attr(fill, fill_opacity, fill_rule)}'
                f'{self._stroke(stroke)}{self._marker_attrs(markers)}{extra}/>')

    def image(self, x, y, w, h, href, preserve_aspect_ratio="xMidYMid meet"):
        return (f'<image x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
                f'href="{esc(href)}" preserveAspectRatio="{esc(preserve_aspect_ratio)}"/>')

    def text_tag(self, x, y, w, h, content, st, vcenter=None, text_len=None):
        if content is None or content == "":
            return ""
        a = self.anchor(st["align"])
        tx = x + (w / 2 if a == "middle" else (w if a == "end" else 0))
        if vcenter is None:
            vcenter = h <= st["size"] * 2.4            # heuristic: small box ⇒ centre
        if vcenter:
            ty = y + h / 2
            baseline = ' dominant-baseline="central"'
        else:
            ty = y + st["size"] * 0.92
            baseline = ""
        # Justify a left-set line to a target length: a compliant shaper (browser/
        # PDF) distributes the slack across spaces with its own metrics (ADR-0003).
        fit = (f' textLength="{fnum(text_len)}" lengthAdjust="spacing"'
               if text_len is not None and a == "start" else "")
        style = self.font_style(st, st["size"])
        return (f'<text x="{fnum(tx)}" y="{fnum(ty)}" text-anchor="{a}"{baseline}'
                f'{fit} style="{style}">{esc(content)}</text>')

    def text_block(self, base_y, anchor, st, size, lines, tx, line_dy,
                   justify_width=None, justifies=None, baseline=None):
        style = self.font_style(st, size)
        dom = f' dominant-baseline="{baseline}"' if baseline else ""
        n = len(lines)
        # `justify_width` set → flush the lines `justifies[i]` marks (default: all
        # but the last) to the column via textLength; None → unchanged.
        def flush(i, ln):
            if justify_width is None or not ln.strip():
                return False
            return justifies[i] if (justifies is not None and i < len(justifies)) else i < n - 1
        def span(i, ln):
            dy = f' dy="{fnum(line_dy)}"' if i else ""
            fit = (f' textLength="{fnum(justify_width)}" lengthAdjust="spacing"'
                   if flush(i, ln) else "")
            return f'<tspan x="{fnum(tx)}"{dy}{fit}>{esc(ln)}</tspan>'
        spans = "".join(span(i, ln) for i, ln in enumerate(lines))
        return f'<text y="{fnum(base_y)}" text-anchor="{anchor}"{dom} style="{style}">{spans}</text>'

    def text_runs(self, base_y, anchor, tx, base_st, size, runs, text_len=None, baseline=None):
        """A single baseline of inline styled runs (rich `text.spans`).

        `runs` is a list of (text, run_style_dict) pairs — the neutral style dicts;
        this backend formats each at `size`. The first run carries the anchor x; the
        rest flow inline. Each run's style overrides the base. A run style carrying
        the reserved `link_href` key (a LinkInline span) gets its tspan wrapped in
        an SVG `<a href>` so the link is real in every SVG consumer. `text_len` set
        (span-aware justification) flushes the whole line to that length."""
        base_style = self.font_style(base_st, size)
        segs = []
        for i, (text, run_st) in enumerate(runs):
            xa = f' x="{fnum(tx)}"' if i == 0 else ""
            seg = f'<tspan{xa} style="{self.font_style(run_st, size)}">{esc(text)}</tspan>'
            href = run_st.get("link_href")
            if href:
                seg = f'<a href="{esc(href)}">{seg}</a>'
            segs.append(seg)
        fit = (f' textLength="{fnum(text_len)}" lengthAdjust="spacing"'
               if text_len is not None and anchor == "start" else "")
        dom = f' dominant-baseline="{baseline}"' if baseline else ""
        return (f'<text y="{fnum(base_y)}" text-anchor="{anchor}"{fit}{dom} '
                f'style="{base_style}">{"".join(segs)}</text>')

    def text_line_runs(self, x, y, w, h, groups, st):
        """One flow-text line as href-aware inline runs.

        `groups` is a list of (text, href_or_None) pairs whose texts concatenate
        to the full line (the caller keeps the separating spaces inside the
        texts). Linked groups are wrapped in `<a href>`; positioning matches
        `text_tag`'s non-centred path so unlinked flow lines stay byte-identical
        through the plain `text_tag` route."""
        if not groups:
            return ""
        a = self.anchor(st["align"])
        tx = x + (w / 2 if a == "middle" else (w if a == "end" else 0))
        ty = y + st["size"] * 0.92
        style = self.font_style(st, st["size"])
        segs = []
        for text, href in groups:
            seg = f"<tspan>{esc(text)}</tspan>"
            if href:
                seg = f'<a href="{esc(href)}">{seg}</a>'
            segs.append(seg)
        return (f'<text x="{fnum(tx)}" y="{fnum(ty)}" text-anchor="{a}" '
                f'style="{style}">{"".join(segs)}</text>')

    def link_wrap(self, inner, href, title=None):
        """Wrap one object's SVG in an `<a href>` (SVG2 `href`; consumed by both
        the Chromium rasteriser and CairoSVG's PDF link annotations). `title`
        becomes a child `<title>` (tooltip/AT label) — no xlink namespace, which
        the emitted document does not declare."""
        if not inner or not href:
            return inner
        t = f"<title>{esc(title)}</title>" if title else ""
        return f'<a href="{esc(href)}">{t}{inner}</a>'

    # ---- grouping / document ---------------------------------------------- #
    def group(self, inner, translate=None):
        if translate is not None:
            tx, ty = translate
            return f'<g transform="translate({fnum(tx)},{fnum(ty)})">{inner}</g>'
        return f"<g>{inner}</g>"

    def opacity_group(self, inner, opacity):
        return f'<g opacity="{fnum(opacity)}">{inner}</g>'

    @staticmethod
    def a11y_wrap(svg, obj):
        """Wrap one object's SVG with accessibility markup when it carries any.

        Additive and minimal: objects with no accessibility semantics are returned
        byte-for-byte unchanged. `decorative` nodes become `aria-hidden`; any
        object with `role`, `alt`, or `actual_text` gets a semantic group. `alt`
        is the short label; `actual_text` is the verbatim content."""
        if not svg or not isinstance(obj, dict):
            return svg
        if obj.get("decorative"):
            return f'<g aria-hidden="true">{svg}</g>'
        role = obj.get("role")
        alt, actual = obj.get("alt"), obj.get("actual_text")
        if role or alt or actual:
            semantic_role = role or "img"
            title = f"<title>{esc(alt)}</title>" if alt else ""
            desc = f"<desc>{esc(actual)}</desc>" if actual else ""
            label = f' aria-label="{esc(alt)}"' if alt else ""
            return f'<g role="{esc(semantic_role)}"{label}>{title}{desc}{svg}</g>'
        return svg

    def document(self, w, h, body, lang=None, title=None, desc=None,
                 background=None):
        """Assemble the page `<svg>`. `lang`/`title`/`desc` are the document-level
        accessibility surface; each is omitted when absent, so a document without
        them renders byte-for-byte as before. `background` is the resolved
        CanvasObject.background; absent, the documented `white` fallback holds
        (ADR-0006's one sanctioned page-paint constant — kept byte-identical)."""
        defs = f"<defs>{''.join(self._defs)}</defs>" if self._defs else ""
        lang_attr = f' xml:lang="{esc(lang)}"' if lang else ""
        meta = ((f"<title>{esc(title)}</title>" if title else "")
                + (f"<desc>{esc(desc)}</desc>" if desc else ""))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fnum(w)}" height="{fnum(h)}" '
                f'viewBox="0 0 {fnum(w)} {fnum(h)}"{lang_attr}>'
                f'{meta}<rect width="100%" height="100%" fill="{esc(background) if background else "white"}"/>'
                f'{defs}{body}</svg>\n')
