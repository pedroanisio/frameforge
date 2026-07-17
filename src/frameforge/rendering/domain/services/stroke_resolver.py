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

`fields(o)` resolves to a backend-neutral `Stroke` value object; `format_attr`
renders it to the SVG fragment (e.g. ' stroke="#000" stroke-width="1"'), and the
back-compat `resolve(o)` is just `format_attr(fields(o))` (ADR 0001 slice 3b-2).
Consumers can move from the string `resolve` to the neutral `fields` so a non-SVG
backend can format the stroke itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from frameforge.rendering.domain.geometry import esc, fnum, num


@dataclass(frozen=True)
class Stroke:
    """A resolved stroke as a backend-neutral value object (not SVG text).

    Holds the already-dereferenced colour and the raw geometry values; a backend
    formats it (the SVG backend via `StrokeResolver.format_attr`, to the exact
    same bytes the resolver used to return directly). `None` means "no stroke".
    """
    color: str
    width: Optional[float] = None
    dash: Optional[str] = None
    dashoffset: object = None
    linecap: Optional[str] = None
    linejoin: Optional[str] = None
    miterlimit: object = None
    paint_order: Optional[str] = None
    vector_effect: Optional[str] = None
    opacity: object = None


@dataclass(frozen=True)
class Markers:
    """Arrowheads requested for an open shape, as a backend-neutral value object.

    `start`/`end` are marker kinds (`bool | str`: True = default filled triangle, a
    string is a marker-kind ref) or a falsy value for "no arrowhead at that end";
    `color` is the solid arrowhead colour. The backend draws/registers its own
    arrowheads from this (the SVG backend via `SvgPainter` marker `<defs>`)."""
    color: str
    start: object = None
    end: object = None


class StrokeResolver:
    def __init__(self, stroke_styles, color_resolver, paint_resolver):
        self.stroke_styles = stroke_styles or {}
        self._color = color_resolver
        self._paint = paint_resolver

    def resolve(self, o):
        """SVG stroke attribute fragment (back-compat string form)."""
        return self.format_attr(self.fields(o))

    def fields(self, o) -> Optional[Stroke]:
        """Resolve an object's stroke to a neutral `Stroke` value object (or None
        for no stroke). The colour is dereferenced; geometry is raw."""
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
            return None
        if width is None:
            width = 1.0
        return Stroke(
            color=col, width=width, dash=dash,
            dashoffset=bundle.get("stroke_dashoffset"),
            linecap=bundle.get("stroke_linecap"),
            linejoin=bundle.get("stroke_linejoin"),
            miterlimit=bundle.get("stroke_miterlimit"),
            paint_order=bundle.get("paint_order"),
            vector_effect=bundle.get("vector_effect"),
            opacity=o.get("stroke_opacity", bundle.get("opacity")),
        )

    @staticmethod
    def format_attr(stroke: Optional[Stroke]) -> str:
        """Format a `Stroke` to the SVG attribute fragment — the exact bytes the
        resolver used to return inline (the SVG backend's stroke formatter)."""
        if stroke is None:
            return ""
        out = f' stroke="{esc(stroke.color)}"'
        if stroke.width is not None:
            out += f' stroke-width="{fnum(stroke.width)}"'
        if stroke.dash:
            out += f' stroke-dasharray="{esc(stroke.dash)}"'
        if stroke.dashoffset is not None:
            out += f' stroke-dashoffset="{fnum(num(stroke.dashoffset, 0))}"'
        if stroke.linecap:
            out += f' stroke-linecap="{esc(stroke.linecap)}"'
        if stroke.linejoin:
            out += f' stroke-linejoin="{esc(stroke.linejoin)}"'
        if stroke.miterlimit is not None:
            out += f' stroke-miterlimit="{fnum(num(stroke.miterlimit, 4))}"'
        if stroke.paint_order:
            out += f' paint-order="{esc(stroke.paint_order)}"'
        if stroke.vector_effect:
            out += f' vector-effect="{esc(stroke.vector_effect)}"'
        if stroke.opacity is not None:
            out += f' stroke-opacity="{fnum(num(stroke.opacity, 1))}"'
        return out

    def arrow_spec(self, o) -> dict | None:
        """Arrowheads declared on the object's `stroke_style`, or None.

        Per the v2 single form, stroke geometry (incl. arrows) lives in
        `stroke_style` (a named bundle or inline dict). `arrow_start`/`arrow_end`
        are `bool | str`: True selects the default filled triangle, a string is a
        marker-kind ref. Returns {'start': kind|None, 'end': kind|None, 'color':
        solid colour} so the builder can register/attach markers; None when no
        arrow is requested."""
        ssv = o.get("stroke_style")
        bundle = self.stroke_styles.get(ssv, {}) if isinstance(ssv, str) else (ssv or {})
        if not isinstance(bundle, dict):
            bundle = {}
        sv = o.get("stroke")
        # A legacy inline-geometry stroke may carry arrow_* (pre-P3); merge as resolve() does.
        if isinstance(sv, dict) and any(k in sv for k in ("color", "width", "dash")):
            merged = dict(sv)
            merged.update(bundle)
            bundle = merged
        start = self._arrow_kind(bundle.get("arrow_start"))
        end = self._arrow_kind(bundle.get("arrow_end"))
        if start is None and end is None:
            return None
        col = self._color.resolve(sv) if isinstance(sv, str) else None
        if col is None or col == "none":
            col = self._color.resolve(bundle.get("stroke") or bundle.get("color"))
        if col is None or col == "none":
            col = "#000"
        return {"start": start, "end": end, "color": col}

    @staticmethod
    def _arrow_kind(v) -> str | None:
        if v is True:
            return "filled_triangle"
        if isinstance(v, str) and v:
            return v
        return None
