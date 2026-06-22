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


class SvgPainter:
    def __init__(self, color_resolver):
        self._color = color_resolver
        self._gid = 0
        self._defs = []          # per-page <defs> entries (gradients, clip paths)

    # ---- per-page backend state ------------------------------------------- #
    def new_page(self):
        self._defs = []

    # ---- small attribute / style helpers ---------------------------------- #
    @staticmethod
    def fill_attr(fill):
        """The SVG `fill` attribute for a resolved paint value (None ⇒ 'none')."""
        return f' fill="{esc(fill)}"' if fill is not None else ' fill="none"'

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

    def clip_wrap(self, inner, clip_id):
        return f'<g clip-path="url(#{clip_id})">{inner}</g>'

    # ---- primitives ------------------------------------------------------- #
    def rect(self, x, y, w, h, fill, stroke, radius=0):
        rr = f' rx="{fnum(radius)}"' if radius else ""
        return (f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" '
                f'height="{fnum(h)}"{rr}{self.fill_attr(fill)}{stroke}/>')

    def ellipse(self, cx, cy, rx, ry, fill, stroke):
        return (f'<ellipse cx="{fnum(cx)}" cy="{fnum(cy)}" rx="{fnum(rx)}" '
                f'ry="{fnum(ry)}"{self.fill_attr(fill)}{stroke}/>')

    def circle(self, cx, cy, r, fill, stroke):
        return f'<circle cx="{fnum(cx)}" cy="{fnum(cy)}" r="{fnum(r)}"{self.fill_attr(fill)}{stroke}/>'

    def line(self, x1, y1, x2, y2, stroke):
        return (f'<line x1="{fnum(x1)}" y1="{fnum(y1)}" '
                f'x2="{fnum(x2)}" y2="{fnum(y2)}"{stroke}/>')

    def poly(self, tag, points, fill, stroke):
        return f'<{tag} points="{points}"{self.fill_attr(fill)}{stroke}/>'

    def path(self, d, fill, stroke):
        return f'<path d="{esc(d)}"{self.fill_attr(fill)}{stroke}/>'

    def image(self, x, y, w, h, href):
        return (f'<image x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
                f'href="{esc(href)}" preserveAspectRatio="xMidYMid meet"/>')

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
