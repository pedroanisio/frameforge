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

from framegraph.rendering.domain.geometry import esc, fnum, num

# Arrowhead `<marker>` shapes. Kind names are the v2 marker refs the grammar
# allows for `arrow_start` / `arrow_end` (grammar/framegraph-v2-style.ebnf
# L190-191; glyph set in framegraph-v2.ebnf L631). Each entry is
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
    def __init__(self, color_resolver):
        self._color = color_resolver
        self._gid = 0
        self._defs = []          # per-page <defs> entries (gradients, clip paths, markers)
        self._markers: dict[tuple[str, str], str] = {}   # (kind, colour) -> marker id

    # ---- per-page backend state ------------------------------------------- #
    def new_page(self):
        self._defs = []
        self._markers = {}

    # ---- small attribute / style helpers ---------------------------------- #
    @staticmethod
    def fill_attr(fill, fill_opacity=None):
        """The SVG `fill` attribute for a resolved paint value (None ⇒ 'none')."""
        attr = f' fill="{esc(fill)}"' if fill is not None else ' fill="none"'
        if fill_opacity is not None:
            attr += f' fill-opacity="{fnum(num(fill_opacity, 1))}"'
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
            ("font_kerning", "font-kerning"),
            ("letter_spacing", "letter-spacing"),
            ("word_spacing", "word-spacing"),
            ("text_decoration", "text-decoration"),
            ("text_transform", "text-transform"),
        ):
            if st.get(key):
                style += f';{css_name}:{esc(st[key])}'
        if st.get("css"):
            style += ";" + esc(str(st["css"]).strip().rstrip(";"))
        return style

    # ---- paint registry (gradients + clips share the id counter) ---------- #
    def gradient(self, g):
        self._gid += 1
        gid = f"g{self._gid}"
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
        if kind == "radial" or kind == "conic":     # conic ≈ radial fallback
            self._defs.append(f'<radialGradient id="{gid}">{body}</radialGradient>')
        else:
            self._defs.append(f'<linearGradient id="{gid}">{body}</linearGradient>')
        return f"url(#{gid})"

    def clip_rect(self, x, y, w, h):
        self._gid += 1
        cid = f"clip{self._gid}"
        self._defs.append(f'<clipPath id="{cid}">'
                          f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}"/></clipPath>')
        return cid

    def clip_ellipse(self, cx, cy, rx, ry):
        self._gid += 1
        cid = f"clip{self._gid}"
        self._defs.append(f'<clipPath id="{cid}">'
                          f'<ellipse cx="{fnum(cx)}" cy="{fnum(cy)}" '
                          f'rx="{fnum(rx)}" ry="{fnum(ry)}"/></clipPath>')
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

    # ---- primitives ------------------------------------------------------- #
    def rect(self, x, y, w, h, fill, stroke, radius=0, fill_opacity=None):
        rr = f' rx="{fnum(radius)}"' if radius else ""
        return (f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" '
                f'height="{fnum(h)}"{rr}{self.fill_attr(fill, fill_opacity)}{stroke}/>')

    def ellipse(self, cx, cy, rx, ry, fill, stroke, fill_opacity=None):
        return (f'<ellipse cx="{fnum(cx)}" cy="{fnum(cy)}" rx="{fnum(rx)}" '
                f'ry="{fnum(ry)}"{self.fill_attr(fill, fill_opacity)}{stroke}/>')

    def circle(self, cx, cy, r, fill, stroke, fill_opacity=None):
        return (f'<circle cx="{fnum(cx)}" cy="{fnum(cy)}" r="{fnum(r)}"'
                f'{self.fill_attr(fill, fill_opacity)}{stroke}/>')

    def line(self, x1, y1, x2, y2, stroke):
        return (f'<line x1="{fnum(x1)}" y1="{fnum(y1)}" '
                f'x2="{fnum(x2)}" y2="{fnum(y2)}"{stroke}/>')

    def poly(self, tag, points, fill, stroke, fill_opacity=None):
        return f'<{tag} points="{points}"{self.fill_attr(fill, fill_opacity)}{stroke}/>'

    def path(self, d, fill, stroke, fill_opacity=None):
        return f'<path d="{esc(d)}"{self.fill_attr(fill, fill_opacity)}{stroke}/>'

    def image(self, x, y, w, h, href, preserve_aspect_ratio="xMidYMid meet"):
        return (f'<image x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
                f'href="{esc(href)}" preserveAspectRatio="{esc(preserve_aspect_ratio)}"/>')

    def text_tag(self, x, y, w, h, content, st, vcenter=None):
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
        style = self.font_style(st, st["size"])
        return (f'<text x="{fnum(tx)}" y="{fnum(ty)}" text-anchor="{a}"{baseline} '
                f'style="{style}">{esc(content)}</text>')

    def text_block(self, base_y, anchor, style, lines, tx, line_dy):
        spans = "".join(
            f'<tspan x="{fnum(tx)}"' + (f' dy="{fnum(line_dy)}"' if i else "") + f'>{esc(ln)}</tspan>'
            for i, ln in enumerate(lines))
        return f'<text y="{fnum(base_y)}" text-anchor="{anchor}" style="{style}">{spans}</text>'

    # ---- grouping / document ---------------------------------------------- #
    def group(self, inner, translate=None):
        if translate is not None:
            tx, ty = translate
            return f'<g transform="translate({fnum(tx)},{fnum(ty)})">{inner}</g>'
        return f"<g>{inner}</g>"

    def opacity_group(self, inner, opacity):
        return f'<g opacity="{fnum(opacity)}">{inner}</g>'

    def document(self, w, h, body):
        defs = f"<defs>{''.join(self._defs)}</defs>" if self._defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fnum(w)}" height="{fnum(h)}" '
                f'viewBox="0 0 {fnum(w)} {fnum(h)}">'
                f'<rect width="100%" height="100%" fill="white"/>{defs}{body}</svg>\n')
