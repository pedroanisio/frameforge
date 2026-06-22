"""TextStyleResolver — text-style reference → resolved style dict (pure).

Extracted from Renderer.text_style (tooling/render_fixtures.py). Resolves a
style ref (a tokens key, an inline dict, or a `class` composition) and the
legacy/CSS shorthand sugar into the flat dict the renderer consumes
(`family`, `size`, `bold`, `lh`, `avg`, the text-fit contract surface, …).

The returned dict IS the ResolvedTextStyle value object for now; promoting it to
a frozen dataclass is deferred to step 4 so the renderer's `st["..."]` access
sites stay untouched and SVG output stays byte-identical.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import num

# Generic-family map (FrameGraph font roles → browser generic families).
FONT_MAP = {"sans": "sans-serif", "serif": "serif", "mono": "monospace",
            "monospace": "monospace", "sans-serif": "sans-serif"}


class TextStyleResolver:
    def __init__(self, text_styles, styles, color_resolver):
        self.text_styles = text_styles or {}
        self.styles = styles or {}
        self._color = color_resolver

    def resolve(self, ref):
        st = {}
        if isinstance(ref, str):
            st = self.text_styles.get(ref) or self.styles.get(ref) or {}
        elif isinstance(ref, dict):
            st = ref
        cls = st.get("class") or st.get("class_")
        merged = {}
        for name in ([cls] if isinstance(cls, str) else (cls or [])):
            merged.update(self.text_styles.get(name) or self.styles.get(name) or {})
        merged.update(st)
        fam = merged.get("font_family") or merged.get("font") or "sans"
        if isinstance(fam, list):
            fam = fam[0] if fam else "sans"
        family = FONT_MAP.get(str(fam), str(fam))
        size = num(merged.get("font_size") or merged.get("size"), 14) or 14
        weight = merged.get("font_weight") or merged.get("weight")
        if weight is None and merged.get("bold"):
            weight = 700
        if weight is None:
            weight = "normal"
        bold = str(weight) in ("bold", "600", "700", "800", "900") or (isinstance(weight, int) and weight >= 600)
        # line-height: a ratio (<=4) or an absolute length ("68px") → ratio
        lhv = merged.get("line_height")
        if isinstance(lhv, str):
            n = num(lhv)
            lh = (n / size) if (n and size) else 1.25
        elif isinstance(lhv, (int, float)) and not isinstance(lhv, bool):
            lh = lhv if lhv <= 4 else lhv / size
        else:
            lh = 1.25
        # per-char advance estimate (no real shaping available) — used for fit + the check
        avg = 0.60 if "mono" in family else 0.52
        if bold:
            avg *= 1.04
        tw = merged.get("text_wrap")
        return {
            "family": family, "size": size, "weight": weight, "bold": bold,
            "italic": bool(merged.get("italic")) or merged.get("font_style") == "italic",
            "color": self._color.resolve(merged.get("color")) or "#1c1c1c",
            "align": merged.get("text_align") or merged.get("align") or "left",
            "lh": lh, "avg": avg,
            # ---- directly renderable CSS text surface ----
            "letter_spacing": self._css_length(merged.get("letter_spacing")),
            "word_spacing": self._css_length(merged.get("word_spacing")),
            "text_decoration": self._text_decoration(merged.get("text_decoration")),
            "text_transform": merged.get("text_transform"),
            "font_variant": merged.get("font_variant"),
            "font_variant_caps": merged.get("font_variant_caps"),
            "font_variant_numeric": merged.get("font_variant_numeric"),
            "font_kerning": merged.get("font_kerning"),
            "font_stretch": merged.get("font_stretch"),
            "css": merged.get("css"),
            # ---- text-fit contract surface ----
            "overflow": merged.get("overflow"),
            "min_font_size": num(merged.get("min_font_size")),
            "text_overflow": merged.get("text_overflow"),
            "max_lines": merged.get("line_clamp") or merged.get("max_lines"),
            "valign": merged.get("vertical_align"),
            "nowrap": merged.get("white_space") == "nowrap" or tw == "nowrap" or merged.get("wrap") is False,
        }

    @staticmethod
    def _css_length(v):
        if v is None:
            return None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f"{v}px"
        return str(v)

    def _text_decoration(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if not isinstance(value, dict):
            return None
        line = value.get("line")
        if isinstance(line, list):
            line = " ".join(str(x) for x in line)
        parts = [str(x) for x in (line, value.get("style")) if x]
        color = self._color.resolve(value.get("color"))
        if color:
            parts.append(color)
        thickness = self._css_length(value.get("thickness"))
        if thickness:
            parts.append(thickness)
        return " ".join(parts) if parts else None
