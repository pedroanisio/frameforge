"""StrokeResolver — object → SVG stroke attribute fragment.

Extracted from Renderer.stroke (tooling/render_fixtures.py). Implements the
HEAD P3 single form: paint comes from `stroke` (a colour/gradient), geometry
(`stroke_width`/`stroke_dasharray`/`stroke_linecap`/`stroke_linejoin`) from
`stroke_style` (a named token bundle or an inline dict); a legacy
`{color, width, dash}` bundle is still accepted.

It depends on two collaborators injected at construction (the ports the full
design names explicitly):

  * color_resolver  — a ColorResolver (pure colour deref)
  * paint_resolver  — a callable(value) -> SVG paint string. Today this is the
    SVG painter's gradient-emitting `Renderer.paint`, so a gradient stroke keeps
    its <defs> side effect and output stays byte-identical. Step 4 replaces it
    with a value-object PaintResolver and moves emission into the painter.

The fragment it returns (e.g. ' stroke="#000" stroke-width="1"') is still SVG;
the value-object Stroke + painter split is step 4.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import esc, fnum, num


class StrokeResolver:
    def __init__(self, stroke_styles, color_resolver, paint_resolver):
        self.stroke_styles = stroke_styles or {}
        self._color = color_resolver
        self._paint = paint_resolver

    def resolve(self, o):
        ssv = o.get("stroke_style")
        bundle = self.stroke_styles.get(ssv, {}) if isinstance(ssv, str) else (ssv or {})
        if not isinstance(bundle, dict):
            bundle = {}
        sv = o.get("stroke")
        if isinstance(sv, dict) and any(k in sv for k in ("color", "width", "dash")):
            legacy = dict(sv)
            legacy.update(bundle)
            bundle = legacy
            col = self._color.resolve(sv.get("color"))
        else:
            col = self._paint(sv) if sv is not None else None
        if col is None or col == "none":
            col = self._color.resolve(bundle.get("stroke") or bundle.get("color"))
        width = num(bundle.get("stroke_width", bundle.get("width")), None)
        dash = bundle.get("stroke_dasharray") or bundle.get("dash")
        dash = " ".join(fnum(num(d, 0)) for d in dash) if isinstance(dash, list) else None
        if col is None or col == "none":
            return ""
        if width is None:
            width = 1.0
        out = f' stroke="{esc(col)}" stroke-width="{fnum(width)}"'
        if dash:
            out += f' stroke-dasharray="{esc(dash)}"'
        cap = bundle.get("stroke_linecap"); join = bundle.get("stroke_linejoin")
        if cap:
            out += f' stroke-linecap="{esc(cap)}"'
        if join:
            out += f' stroke-linejoin="{esc(join)}"'
        opacity = o.get("stroke_opacity", bundle.get("opacity"))
        if opacity is not None:
            out += f' stroke-opacity="{fnum(num(opacity, 1))}"'
        return out
