"""CSS/SVG style-value builder (domain service).

Pure translation of the FrameGraph style surface into CSS / SVG attribute value
strings — the `filter` / `backdrop-filter`, `drop-shadow`, `transform`, and
`<length>` builders extracted from the monolithic ``Renderer`` (DDD step:
decompose the god-object toward SRP — codebase-standards.md §13).

The only non-pure input is a shadow's colour token, resolved through an injected
``color_resolver(token) -> value`` callable, so the domain layer stays free of
the colour-resolver implementation (dependency inversion). Behaviour is identical
to the methods it replaces; the painter-coupled `_with_*` wrappers and clip
registration stay on the Renderer.
"""
from __future__ import annotations

from typing import Callable, Optional

from framegraph.rendering.domain.geometry import fnum, num


class StyleValues:
    """Build CSS/SVG value strings (filter, shadow, transform, length) from the
    style surface. `color_resolver` resolves a shadow's colour token."""

    _SVG_BACKED = {"blur", "drop_shadow", "turbulence", "displacement_map",
                   "diffuse_lighting", "specular_lighting"}
    _SVG_ONLY = {"turbulence", "displacement_map", "diffuse_lighting", "specular_lighting"}
    _UNITLESS = {"brightness", "contrast", "grayscale", "invert", "opacity", "saturate", "sepia"}

    def __init__(self, color_resolver: Optional[Callable] = None):
        self._color = color_resolver or (lambda _c: None)

    # ---- filter / backdrop-filter / drop-shadow ----
    def filter_value(self, value, *, svg_only: bool = True):
        if isinstance(value, str):
            return value.strip() if value.strip() and value.strip() != "none" else ""
        if not isinstance(value, list):
            return ""
        parts = []
        for item in value:
            if not isinstance(item, dict):
                continue
            fn = item.get("fn") or item.get("kind") or item.get("name")
            if not fn:
                continue
            if not svg_only and fn in self._SVG_BACKED:
                continue
            if svg_only and fn in self._SVG_ONLY:
                continue
            css_fn = "hue-rotate" if fn == "hue_rotate" else fn.replace("_", "-")
            if fn == "drop_shadow":
                shadow = self.shadow_value(item.get("shadow"))
                if shadow:
                    parts.append(f"drop-shadow({shadow})")
            else:
                val = item.get("value")
                if val is not None:
                    parts.append(f"{css_fn}({self.filter_arg(fn, val)})")
        return " ".join(parts)

    def filter_arg(self, fn, value):
        if fn in self._UNITLESS:
            return str(value)
        if fn == "hue_rotate":
            return str(value)
        return self.length(value)

    def shadow_value(self, value):
        if isinstance(value, str):
            return value.strip()
        if not isinstance(value, dict):
            return ""
        x = self.length(value.get("offset_x", value.get("x", 0)))
        y = self.length(value.get("offset_y", value.get("y", 0)))
        blur = self.length(value.get("blur", 0))
        color = self._color(value.get("color")) or value.get("color")
        return " ".join(str(v) for v in (x, y, blur, color) if v)

    @staticmethod
    def length(value):
        n = num(value, None)
        return f"{fnum(n)}px" if n is not None else str(value)

    # ---- transform ----
    def svg_transform(self, value, origin, box):
        if not value or value == "none":
            return ""
        if isinstance(value, str):
            return value.replace("deg", "")
        items = value if isinstance(value, list) else [value]
        ox, oy = self.transform_origin(origin, box)
        parts = []
        for item in items:
            if isinstance(item, str):
                parts.append(item.replace("deg", ""))
                continue
            if not isinstance(item, dict):
                continue
            fn = item.get("fn") or item.get("kind") or item.get("name")
            args = item.get("args") or []
            vals = [self.transform_arg(v) for v in args]
            if fn == "rotate" and vals:
                parts.append(f"rotate({vals[0]} {fnum(ox)} {fnum(oy)})" if ox is not None else f"rotate({vals[0]})")
            elif fn == "translate":
                parts.append(f"translate({' '.join(vals)})")
            elif fn == "translate_x" and vals:
                parts.append(f"translate({vals[0]} 0)")
            elif fn == "translate_y" and vals:
                parts.append(f"translate(0 {vals[0]})")
            elif fn == "scale":
                parts.append(self.origin_transform(f"scale({' '.join(vals)})", ox, oy))
            elif fn == "scale_x" and vals:
                parts.append(self.origin_transform(f"scale({vals[0]} 1)", ox, oy))
            elif fn == "scale_y" and vals:
                parts.append(self.origin_transform(f"scale(1 {vals[0]})", ox, oy))
            elif fn == "skew_x" and vals:
                parts.append(self.origin_transform(f"skewX({vals[0]})", ox, oy))
            elif fn == "skew_y" and vals:
                parts.append(self.origin_transform(f"skewY({vals[0]})", ox, oy))
            elif fn == "skew" and vals:
                parts.append(self.origin_transform(f"skewX({vals[0]})", ox, oy))
                if len(vals) > 1:
                    parts.append(self.origin_transform(f"skewY({vals[1]})", ox, oy))
            elif fn == "matrix" and vals:
                parts.append(f"matrix({' '.join(vals)})")
        return " ".join(p for p in parts if p)

    def transform_origin(self, origin, box):
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
    def transform_arg(value):
        n = num(value, None)
        return fnum(n) if n is not None else str(value).replace("deg", "")

    @staticmethod
    def origin_transform(transform, ox, oy):
        if ox is None:
            return transform
        return f"translate({fnum(ox)} {fnum(oy)}) {transform} translate({fnum(-ox)} {fnum(-oy)})"
